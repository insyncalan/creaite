#!/usr/bin/env python3
"""Phase C of the repo migration: dev/BACKLOG.md onto the private board, and back again.

The board is the plan's home after the migration (`dev/REPOMIGRATION.md`, Phase C, steps 11 to 15): the private repo
`insyncalan/creaite-plan` holds one issue per open backlog item and one milestone per release (plus Unscheduled), and a
private user-level GitHub Project, "creaite plan", linked to that repo, holds the fields Priority, State, Release, Size
and Team. Standard library only, Python 3.9 or later; every GitHub call goes through the `gh` command line tool, which
must be signed in as the board's owner with the `project` scope (`gh auth refresh -s project`).

Commands (run from the repository root):

    python3 dev/tools/board_import.py plan                # dev/BACKLOG.md -> dev/tools/board-plan.json (the dry run to review)
    python3 dev/tools/board_import.py apply --dry-run     # prints every write it would make; reads the board to skip what exists
    python3 dev/tools/board_import.py apply               # the real import (milestones, project, fields, views, issues, values)
    python3 dev/tools/board_import.py export              # the board -> dev/BACKLOG.md (read-only queries)
    python3 dev/tools/board_import.py export --from-plan --out /tmp/x.md   # the same rendering, from board-plan.json

`apply` is idempotent and can be stopped and run again: a milestone, label, field or view with the same name, the project
with the same title, an issue whose title starts with "BL-NNN " and a field value already set are all skipped. It pauses
after every write (`--pause`, default 1 second) to stay under GitHub's secondary rate limits, and waits a minute and retries
when GitHub says a request came too quickly. It never closes, edits or deletes an issue, and never removes a field.

Plan rules (each derived value carries its reason and a strength, strong, medium or weak, in board-plan.json):
- **Open items** are the rows of the Summary's tables (the release groups, Not scheduled, On hold and After the trial), plus
  any item that has only a detailed write-up and is not shipped (BL-255: its report-only half shipped in v1.9.0, its
  enforcing half is open). Shipped groups (v1.9.0 to v1.9.3) have no table, and their leftover write-ups (BL-319 to BL-323)
  are skipped because the history section maps them to their FRs.
- **Release:** the group's version; Not scheduled, On hold and After the trial are Unscheduled.
- **State:** On hold group -> On hold; After the trial and Not scheduled -> Idea; in a release, the text decides ("on hold",
  "needs decision", "being built" / "built on `branch`", "ready for a sprint"), else Ready (weak). The release plans in
  `dev/sprints/` (v1.9.4, v1.9.5, v2.0.0) and the on-hold v2.1.0 plan (branch `dev-v210-sprint-plan`) then override the
  state and team where they say who builds what (`SPRINT_EVIDENCE`, medium).
- **Priority:** "Priority Urgent|High|Normal|Low" or "low/high priority" in the row, else in the write-up; else Normal.
- **Size:** the row's Size; "M (was S)" -> M. S–M and M–L keep their own options (see SIZE_OPTIONS).
- **Team:** Team Cap / Team Stark / Team 1 / Team 2 in the row, else SPRINT_EVIDENCE, else Unassigned. A write-up's
  "directly to Team 1" says who Alan told, not who builds, so it is not used.

Views. The GraphQL API can create a view (`createProjectV2View`: name and layout) and set its filter
(`updateProjectV2View`), and `apply` does both, but the view configuration input holds only the visible fields: grouping a
table and choosing a board's column field cannot be set by API. After `apply`, on github.com (the project, each view's
menu):
  1. **By release** (table): View options › Group by › Release. Optionally Sort by › Priority.
  2. **By state** (board): View options › Column by › State (a new board defaults to the built-in Status field).
     Hide the built-in Status field from the views, since State replaces it.
  3. **Needs decision** (table): its filter `state:"Needs decision"` is set by `apply`; check it shows, then Save.
  Each change shows "Save" at the top of the view; press it, or the view reverts.

After the import (step 15): `export` rewrites dev/BACKLOG.md from the board with a read-only header, and pull requests in
the code repo close plan items with "closes insyncalan/creaite-plan#N".
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKLOG = ROOT / "dev" / "BACKLOG.md"
PLAN = ROOT / "dev" / "tools" / "board-plan.json"

OWNER = "insyncalan"
REPO = "insyncalan/creaite-plan"
PROJECT_TITLE = "creaite plan"
UNSCHEDULED = "Unscheduled"
DEFECT_LABEL = "bug"  # exists on the repo already

PRIORITY_OPTIONS = [("Urgent", "RED"), ("High", "ORANGE"), ("Normal", "GRAY"), ("Low", "BLUE")]
STATE_OPTIONS = [("Idea", "GRAY"), ("Needs decision", "PINK"), ("Ready", "BLUE"), ("Building", "YELLOW"),
                 ("In review", "PURPLE"), ("Shipped", "GREEN"), ("On hold", "ORANGE"), ("Dropped", "RED")]
SIZE_OPTIONS = [("XS", "GRAY"), ("S", "BLUE"), ("S–M", "BLUE"), ("M", "GREEN"), ("M–L", "YELLOW"),
                ("L", "ORANGE"), ("XL", "RED")]
SIZE_MAP = {"M (was S)": "M", "S-M": "S–M", "M-L": "M–L"}
TEAM_OPTIONS = [("Team Cap", "BLUE"), ("Team Stark", "RED"), ("Both", "PURPLE"), ("Unassigned", "GRAY")]
VIEWS = [
    {"name": "By release", "layout": "TABLE_LAYOUT", "filter": None, "manual": "Group by › Release"},
    {"name": "By state", "layout": "BOARD_LAYOUT", "filter": None, "manual": "Column by › State"},
    {"name": "Needs decision", "layout": "TABLE_LAYOUT", "filter": 'state:"Needs decision"', "manual": "none (filter set by apply)"},
]

# Who builds what and how far it has got, from the release plans (Alan, 15-10-2026). Medium evidence: the plans are
# newer than the backlog's Plan column. v2.1.0's comes from the on-hold branch dev-v210-sprint-plan (not yet merged).
_V194 = "dev/sprints/v194-release.md: 'Everything in it is already built'; integration, checks and the cut remain"
_V195 = "dev/sprints/v195-release.md"
_V210 = "dev-v210-sprint-plan:dev/sprints/v210-reporting.md (on hold, not merged)"
SPRINT_EVIDENCE = {
    "BL-09": {"state": ("In review", _V194), "team": ("Team Cap", "v194-release.md: 'Team Cap: check BL-09 on the release'")},
    "BL-304": {"state": ("In review", _V194)},
    "BL-326": {"state": ("In review", _V194), "team": ("Team Stark", "v194-release.md: 'Team Stark: merge v195-run-chat-bl330 … It carries BL-330 and BL-326'")},
    "BL-327": {"state": ("In review", _V194), "team": ("Team Cap", "v194-release.md: Team Cap fixes test_fast_save, which BL-327's change broke")},
    "BL-328": {"state": ("In review", _V194)},
    "BL-329": {"state": ("In review", _V194)},
    "BL-330": {"state": ("In review", _V194), "team": ("Team Stark", "v194-release.md: Team Stark merges BL-330 and BL-326")},
    "BL-324": {"state": ("Building", _V195 + ": built on v195-design-scale, held in v195-vip-conversations; to be brought level"), "team": ("Team Stark", _V195 + ": Team Stark's branch")},
    "BL-325": {"state": ("Building", _V195 + ": built on v195-design-scale, held in v195-vip-conversations; to be brought level"), "team": ("Team Stark", _V195 + ": Team Stark's branch")},
    "BL-333": {"state": ("Building", _V195 + ": built on v195-design-scale, held in v195-vip-conversations; to be brought level"), "team": ("Team Stark", _V195 + ": Team Stark's branch")},
    "BL-334": {"state": ("Building", _V195 + ": built on v195-vip-conversations; to be brought level"), "team": ("Team Stark", _V195 + ": Team Stark's branch")},
    "BL-10": {"state": ("Building", _V195 + ": built on v195-archiving; to be brought level, plus the BL-323 follow-up"), "team": ("Team Cap", _V195 + ": Team Cap's branch")},
    "BL-03": {"state": ("Building", _V195 + ": built on v195-archiving; to be brought level, plus the BL-323 follow-up"), "team": ("Team Cap", _V195 + ": Team Cap's branch")},
    "BL-331": {"state": ("Building", _V195 + ": built on v196-move-back, put on top of v195-archiving"), "team": ("Team Cap", _V195 + ": Team Cap")},
    "BL-316": {"state": ("Building", _V195 + ": 'frozen partway on v195-consistency'; split by screen"), "team": ("Both", _V195 + ": Team Stark the shared test and five screens, Team Cap five screens")},
    "BL-301": {"state": ("Building", "dev/sprints/v200-notes-release.md: 'Ship Notes, all five parts, as built'; branches v20-base, v20-capture"), "team": ("Both", "v200-notes-release.md: work split between Team Cap and Team Stark")},
    "BL-335": {"team": ("Team Cap", _V210 + ": Team Cap, reports")},
    "BL-336": {"team": ("Team Cap", _V210 + ": Team Cap, P8 the client view")},
    "BL-337": {"team": ("Team Stark", _V210 + ": Team Stark, P9 the reporting space")},
    "BL-338": {"team": ("Team Stark", _V210 + ": Team Stark, P4 and P7 the minutes")},
    "BL-339": {"team": ("Team Stark", _V210 + ": Team Stark, P10 retire the meeting hub")},
}
# Shipped items whose write-ups linger below the Summary; the history section maps them to their FRs.
SHIPPED_WRITEUPS = {"BL-319", "BL-320", "BL-321", "BL-322", "BL-323"}

ID_RE = re.compile(r"BL-\d+")
GROUP_RE = re.compile(r"^### (v\d+\.\d+\.\d+|Not scheduled|On hold|After the trial)\b(.*)$")
DETAIL_RE = re.compile(r"^### (BL-\d+) — (.+?)\s*$")
VERSION_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")


def release_key(name):
    m = VERSION_RE.match(name)
    return (0, tuple(int(x) for x in m.groups())) if m else (1, (0, 0, 0))


def strip_md(text):
    text = re.sub(r"\*\*|`", "", text)
    return re.sub(r"\s+", " ", text).strip()


# ----------------------------------------------------------------------------------------------------------- plan


def parse_backlog(text):
    """The Summary's rows by group, and the detailed write-ups, with their line numbers."""
    lines = text.splitlines()
    rows, details = [], {}
    in_summary, group, group_heading = False, None, None
    for n, line in enumerate(lines, 1):
        if line.startswith("## "):
            in_summary = line.strip() == "## Summary"
            group = None
            continue
        if in_summary:
            g = GROUP_RE.match(line)
            if g:
                group, group_heading = g.group(1), line[4:].strip()
                continue
            if group and line.startswith("| BL-"):
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if len(cells) < 5:
                    raise SystemExit("line %d: a Summary row with %d cells, expected 5" % (n, len(cells)))
                if len(cells) > 5:  # a stray "|" in the Plan column
                    cells = cells[:4] + [" | ".join(cells[4:])]
                rows.append({"id": cells[0], "item": cells[1], "source": cells[2], "size": cells[3], "plan": cells[4],
                             "group": group, "group_heading": group_heading, "line": n, "raw": line})
    # Write-ups: from each "### BL-NNN — Title" to the next ### or ## heading.
    starts = [(i, DETAIL_RE.match(l)) for i, l in enumerate(lines) if DETAIL_RE.match(l)]
    for i, m in starts:
        j = i + 1
        while j < len(lines) and not (lines[j].startswith("### ") or lines[j].startswith("## ")):
            j += 1
        body = "\n".join(lines[i + 1:j]).strip("\n")
        if m.group(1) in details:
            details[m.group(1)]["duplicate_lines"].append(i + 1)
        else:
            details[m.group(1)] = {"title": m.group(2), "body": body, "line": i + 1, "duplicate_lines": []}
    return rows, details


def first_match(patterns, *texts):
    for label, text in texts:
        for value, rx in patterns:
            m = re.search(rx, text, re.I)
            if m:
                return value, label, m.group(0)
    return None


STATE_PATTERNS = [
    ("On hold", r"\bon hold\b"),
    ("Needs decision", r"\bneeds (?:a )?decision\b|\bundecided\b"),
    ("Building", r"\bbeing built\b|\bstarted building\b|\bbuilt on `[^`]+`"),
    ("Ready", r"\bready for a sprint\b"),
]
PRIORITY_PATTERNS = [
    ("Urgent", r"\bPriority:? Urgent\b|\burgent priority\b"),
    ("High", r"\bPriority:? High\b|\bhigh priority\b"),
    ("Low", r"\bPriority:? Low\b|\blow priority\b"),
    ("Normal", r"\bPriority:? Normal\b"),
]
TEAM_PATTERNS = [("Team Cap", r"\bTeam (?:Cap|1)\b"), ("Team Stark", r"\bTeam (?:Stark|2)\b")]


def derive(item_id, row, detail):
    row_text = row["raw"] if row else ""
    detail_text = detail["body"] if detail else ""
    group = row["group"] if row else None
    ev = {}

    # Release
    if row and VERSION_RE.match(group):
        ev["release"] = (group, "Summary group '%s' (line %d)" % (row["group_heading"], row["line"]), "strong")
    elif row:
        ev["release"] = (UNSCHEDULED, "Summary group '%s' is not a release" % row["group_heading"], "strong")
    else:
        ev["release"] = (UNSCHEDULED, "no Summary row; write-up only", "weak")

    # State
    if row and group == "On hold":
        ev["state"] = ("On hold", "Summary group 'On hold'", "strong")
    elif row and group in ("Not scheduled", "After the trial"):
        ev["state"] = ("Idea", "Summary group '%s'" % group, "strong")
    elif row:
        # The row's Plan column decides; the Item column's text is description, not status.
        hit = first_match(STATE_PATTERNS, ("row Plan", row["plan"]))
        if hit:
            ev["state"] = (hit[0], "%s says '%s'" % (hit[1], hit[2]), "strong")
        else:
            # The write-up is not scanned: it names other items' states ("BL-317's page (on hold)").
            ev["state"] = ("Ready", "in a release, no status words in the row's Plan: default", "weak")
    else:
        if re.search(r"when Alan decides", detail_text):
            ev["state"] = ("Needs decision", "write-up says 'follows … when Alan decides'", "weak")
        else:
            ev["state"] = ("Idea", "write-up only: default", "weak")

    # Priority
    hit = first_match(PRIORITY_PATTERNS, ("row", row_text))
    if hit:
        ev["priority"] = (hit[0], "row says '%s'" % hit[2], "strong")
    else:
        hit = first_match(PRIORITY_PATTERNS, ("write-up", detail_text))
        if hit:
            ev["priority"] = (hit[0], "write-up says '%s'" % hit[2], "medium")
        else:
            ev["priority"] = ("Normal", "no priority stated: default", "default")

    # Size
    raw_size = row["size"] if row else ""
    size = SIZE_MAP.get(raw_size, raw_size)
    if size in dict(SIZE_OPTIONS):
        ev["size"] = (size, "row Size '%s'" % raw_size, "strong" if size == raw_size else "medium")
    else:
        ev["size"] = (None, "no Size in the backlog" if not raw_size else "unknown Size '%s'" % raw_size, "weak")

    # Team: the row only (Source "directly to Team 1" is who was told, so only a builder phrase counts)
    hit = first_match(TEAM_PATTERNS, ("row Plan", row["plan"] if row else ""))
    if hit:
        ev["team"] = (hit[0], "row Plan says '%s'" % hit[2], "strong")
    else:
        ev["team"] = ("Unassigned", "no team named as builder: default", "default")

    # The release plans override state and team.
    for key, (value, reason) in SPRINT_EVIDENCE.get(item_id, {}).items():
        if key == "team" and ev["team"][2] == "strong" and ev["team"][0] != value:
            ev["team"] = (ev["team"][0], ev["team"][1] + "; NOTE sprint plan says %s (%s)" % (value, reason), "weak")
            continue
        prior = ev[key]
        ev[key] = (value, reason + ("" if prior[0] == value else " (backlog alone gave %s: %s)" % (prior[0], prior[1])), "medium")
    return ev


def make_title(item_id, row, detail):
    if detail:
        t = strip_md(detail["title"])
    else:
        item = row["item"]
        m = re.match(r"\*\*(.+?)\*\*", item)
        t = strip_md(m.group(1) if m else item).rstrip(":.")
    t = re.sub(r"^Technical:\s*", "", t)
    if len(t) > 110:
        t = t[:107].rsplit(" ", 1)[0] + "…"
    return "%s %s" % (item_id, t)


def make_body(item_id, row, detail):
    parts = ["<!-- creaite-plan %s: imported from dev/BACKLOG.md -->" % item_id, "<!-- summary -->"]
    if row:
        parts += ["**Backlog summary** (%s)" % row["group_heading"], "",
                  "| ID | Item | Source | Size | Plan |", "|----|------|--------|------|------|", row["raw"]]
    else:
        parts += ["**Backlog summary:** none (this item had only a detailed write-up in dev/BACKLOG.md)."]
    parts += ["<!-- /summary -->", "", "<!-- write-up -->"]
    parts += [detail["body"] if detail else "_No detailed write-up in the backlog; the summary above is the whole item._"]
    parts += ["<!-- /write-up -->"]
    return "\n".join(parts) + "\n"


def build_plan():
    text = BACKLOG.read_text(encoding="utf-8")
    rows, details = parse_backlog(text)
    problems = []
    seen = {}
    for r in rows:
        if r["id"] in seen:
            problems.append("duplicate Summary row %s (lines %d and %d)" % (r["id"], seen[r["id"]], r["line"]))
        seen[r["id"]] = r["line"]
    for k, d in details.items():
        if d["duplicate_lines"]:
            problems.append("duplicate write-up %s (lines %d and %s)" % (k, d["line"], d["duplicate_lines"]))
    by_id = {}
    for r in rows:
        by_id.setdefault(r["id"], r)
    ids = list(by_id)
    skipped = []
    for k in details:
        if k in by_id:
            continue
        if k in SHIPPED_WRITEUPS:
            skipped.append({"id": k, "line": details[k]["line"], "why": "shipped (mapped to an FR in 'Moved into scope'); write-up left over"})
        else:
            ids.append(k)
            problems.append("%s has a write-up (line %d) but no Summary row; imported as Unscheduled" % (k, details[k]["line"]))

    items = []
    for item_id in ids:
        row, detail = by_id.get(item_id), details.get(item_id)
        ev = derive(item_id, row, detail)
        body = make_body(item_id, row, detail)
        if len(body) > 65000:
            problems.append("%s body is %d characters, over GitHub's 65536 limit" % (item_id, len(body)))
        defect = bool(re.search(r"\*\*Defect\b", row["item"] if row else "") or (detail and detail["title"].startswith("Defect")))
        items.append({
            "id": item_id,
            "title": make_title(item_id, row, detail),
            "release": ev["release"][0],
            "priority": ev["priority"][0],
            "state": ev["state"][0],
            "size": ev["size"][0],
            "team": ev["team"][0],
            "labels": [DEFECT_LABEL] if defect else [],
            "source_line": row["line"] if row else None,
            "writeup_line": detail["line"] if detail else None,
            "evidence": {k: {"value": v[0], "reason": v[1], "strength": v[2]} for k, v in ev.items()},
            "body": body,
        })

    releases = sorted({i["release"] for i in items if i["release"] != UNSCHEDULED}, key=release_key)
    group_headings = {r["group"]: r["group_heading"] for r in rows}
    milestones = [{"title": v, "description": "creaite " + group_headings.get(v, v)} for v in releases]
    milestones.append({"title": UNSCHEDULED, "description": "Open items in no release: Not scheduled, On hold and After the trial"})
    fields = [
        {"name": "Priority", "options": [{"name": n, "color": c} for n, c in PRIORITY_OPTIONS]},
        {"name": "State", "options": [{"name": n, "color": c} for n, c in STATE_OPTIONS]},
        {"name": "Release", "options": [{"name": v, "color": "BLUE"} for v in releases] + [{"name": UNSCHEDULED, "color": "GRAY"}]},
        {"name": "Size", "options": [{"name": n, "color": c} for n, c in SIZE_OPTIONS]},
        {"name": "Team", "options": [{"name": n, "color": c} for n, c in TEAM_OPTIONS]},
    ]

    def count(key):
        out = {}
        for i in items:
            out[i[key] or "(none)"] = out.get(i[key] or "(none)", 0) + 1
        return out

    weak = [{"id": i["id"], "field": k, "value": e["value"], "reason": e["reason"]}
            for i in items for k, e in i["evidence"].items() if e["strength"] == "weak"]
    for i in items:
        if not i["release"]:
            problems.append("%s has no release" % i["id"])
    plan = {
        "about": "Dry run of the Phase C board import, made by dev/tools/board_import.py plan from dev/BACKLOG.md. Review it, then run apply --dry-run.",
        "owner": OWNER, "repo": REPO, "project_title": PROJECT_TITLE,
        "size_mapping": {"options": [n for n, _ in SIZE_OPTIONS], "mapped": SIZE_MAP,
                         "note": "S–M and M–L are kept as their own options, between their neighbours, rather than rounded"},
        "milestones": milestones,
        "labels": [{"name": DEFECT_LABEL, "note": "already on the repo; put on items the backlog calls a Defect"}],
        "fields": fields,
        "views": VIEWS,
        "checks": {
            "items": len(items),
            "per_release": {k: count("release")[k] for k in [m["title"] for m in milestones] if k in count("release")},
            "per_state": count("state"), "per_priority": count("priority"), "per_team": count("team"), "per_size": count("size"),
            "weak_evidence": weak,
            "problems": problems,
            "skipped_writeups": skipped,
        },
        "items": items,
    }
    return plan


def cmd_plan(args):
    plan = build_plan()
    PLAN.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    c = plan["checks"]
    print("wrote %s: %d milestones, %d items" % (PLAN.relative_to(ROOT), len(plan["milestones"]), c["items"]))
    for k in ("per_release", "per_state", "per_priority", "per_team", "per_size"):
        print("  %-13s %s" % (k, ", ".join("%s %d" % kv for kv in c[k].items())))
    print("  weak evidence (%d):" % len(c["weak_evidence"]))
    for w in c["weak_evidence"]:
        print("    %-7s %-8s = %-14s %s" % (w["id"], w["field"], w["value"], w["reason"]))
    print("  problems (%d):" % len(c["problems"]))
    for p in c["problems"]:
        print("    " + p)
    for s in c["skipped_writeups"]:
        print("  skipped write-up %s (line %d): %s" % (s["id"], s["line"], s["why"]))
    return 0


# ------------------------------------------------------------------------------------------------------- gh helpers


class GH:
    def __init__(self, dry_run, pause):
        self.dry_run, self.pause, self.writes = dry_run, pause, 0

    @staticmethod
    def show(cmd):
        out = []
        for c in cmd:
            out.append(c if re.match(r"^[\w@%+=:,./<>-]+$", c) else "'" + c.replace("'", "'\\''") + "'")
        return " ".join(out)

    def read(self, cmd):
        """A read-only gh call; runs in a dry run too."""
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode:
            raise SystemExit("gh read failed: %s\n%s" % (self.show(cmd), r.stderr.strip()))
        return r.stdout

    def write(self, cmd, stdin=None, placeholder=""):
        self.writes += 1
        if self.dry_run:
            print("  [dry-run] " + self.show(cmd) + (" < body" if stdin is not None else ""))
            return placeholder
        for attempt in range(4):
            r = subprocess.run(cmd, capture_output=True, text=True, input=stdin)
            if r.returncode == 0:
                time.sleep(self.pause)
                return r.stdout
            err = r.stderr.lower()
            if "secondary rate limit" in err or "too quickly" in err or "abuse" in err:
                print("  rate limited; waiting 60 s (attempt %d)" % (attempt + 1))
                time.sleep(60)
                continue
            raise SystemExit("gh write failed: %s\n%s" % (self.show(cmd), r.stderr.strip()))
        raise SystemExit("gh write still rate limited after 4 attempts: " + self.show(cmd))

    def graphql(self, query, write=False, placeholder=None, **variables):
        cmd = ["gh", "api", "graphql", "-f", "query=" + " ".join(query.split())]
        for k, v in variables.items():
            cmd += (["-F", "%s=%s" % (k, v)] if isinstance(v, int) else ["-f", "%s=%s" % (k, v)])
        if write:
            out = self.write(cmd, placeholder="")
            return json.loads(out) if out else placeholder
        return json.loads(self.read(cmd))


Q_PROJECT = """query($owner: String!) { user(login: $owner) { id projectsV2(first: 100) { nodes { id number title public
  repositories(first: 20) { nodes { nameWithOwner } }
  views(first: 50) { nodes { id name layout filter } }
  fields(first: 50) { nodes { ... on ProjectV2FieldCommon { id name dataType }
    ... on ProjectV2SingleSelectField { options { id name } } } } } } } }"""

Q_ITEMS = """query($id: ID!, $after: String) { node(id: $id) { ... on ProjectV2 { items(first: 100, after: $after) {
  pageInfo { hasNextPage endCursor }
  nodes { id content { ... on Issue { id number url title } }
    fieldValues(first: 30) { nodes { ... on ProjectV2ItemFieldSingleSelectValue { name optionId
      field { ... on ProjectV2SingleSelectField { name } } } } } } } } } }"""


def find_project(gh):
    data = gh.graphql(Q_PROJECT, owner=OWNER)["data"]["user"]
    for p in data["projectsV2"]["nodes"]:
        if p["title"] == PROJECT_TITLE:
            return data["id"], p
    return data["id"], None


def project_items(gh, project_id):
    out, after = {}, None
    while True:
        kw = {"id": project_id}
        if after:
            kw["after"] = after
        page = gh.graphql(Q_ITEMS, **kw)["data"]["node"]["items"]
        for n in page["nodes"]:
            c = n.get("content") or {}
            if c.get("url"):
                vals = {v["field"]["name"]: v["name"] for v in n["fieldValues"]["nodes"] if v and v.get("field")}
                out[c["url"]] = {"item_id": n["id"], "values": vals}
        if not page["pageInfo"]["hasNextPage"]:
            return out
        after = page["pageInfo"]["endCursor"]


def list_issues(gh, with_body=False):
    fields = "id,number,title,url,state,milestone,labels" + (",body" if with_body else "")
    return json.loads(gh.read(["gh", "issue", "list", "-R", REPO, "--state", "all", "--limit", "2000", "--json", fields]))


def issue_by_bl(issues):
    out = {}
    for i in issues:
        m = re.match(r"^(BL-\d+) ", i["title"])
        if m:
            out.setdefault(m.group(1), i)
    return out


# ------------------------------------------------------------------------------------------------------------ apply


def cmd_apply(args):
    if not PLAN.exists():
        raise SystemExit("no %s: run plan first" % PLAN.relative_to(ROOT))
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    gh = GH(args.dry_run, args.pause)
    only = set(args.only.split(",")) if args.only else None
    items = [i for i in plan["items"] if not only or i["id"] in only]
    print("%s %d items onto %s and the project '%s'" % ("DRY RUN:" if args.dry_run else "Applying", len(items), REPO, PROJECT_TITLE))

    # 1. Labels
    have = {l["name"] for l in json.loads(gh.read(["gh", "label", "list", "-R", REPO, "--limit", "200", "--json", "name"]))}
    for lab in plan["labels"]:
        if lab["name"] not in have:
            gh.write(["gh", "label", "create", lab["name"], "-R", REPO])
    # 2. Milestones
    print("milestones")
    existing = {m["title"]: m for m in json.loads(gh.read(["gh", "api", "repos/%s/milestones?state=all&per_page=100" % REPO]))}
    for m in plan["milestones"]:
        if m["title"] in existing:
            print("  exists: " + m["title"])
            continue
        gh.write(["gh", "api", "-X", "POST", "repos/%s/milestones" % REPO, "-f", "title=" + m["title"],
                  "-f", "description=" + m["description"], "-f", "state=open"])
    # 3. Project
    print("project")
    owner_id, proj = find_project(gh)
    if proj:
        print("  exists: #%d %s" % (proj["number"], proj["title"]))
    else:
        out = gh.write(["gh", "project", "create", "--owner", OWNER, "--title", PROJECT_TITLE, "--format", "json"])
        if out:
            _, proj = find_project(gh)
        else:
            proj = {"id": "<PROJECT_ID>", "number": "<N>", "public": False, "repositories": {"nodes": []},
                    "views": {"nodes": []}, "fields": {"nodes": []}}
    if proj.get("public"):
        gh.write(["gh", "project", "edit", str(proj["number"]), "--owner", OWNER, "--visibility", "PRIVATE"])
    if REPO not in [r["nameWithOwner"] for r in proj["repositories"]["nodes"]]:
        repo_id = json.loads(gh.read(["gh", "api", "repos/" + REPO]))["node_id"]
        gh.graphql("""mutation($p: ID!, $r: ID!) { linkProjectV2ToRepository(input: {projectId: $p, repositoryId: $r}) { clientMutationId } }""",
                   write=True, p=proj["id"], r=repo_id)
    else:
        print("  linked to " + REPO)
    # 4. Fields
    print("fields")
    fields = {f["name"]: f for f in proj["fields"]["nodes"] if f}
    created = False
    for f in plan["fields"]:
        if f["name"] in fields:
            names = {o["name"] for o in fields[f["name"]].get("options") or []}
            missing = [o["name"] for o in f["options"] if o["name"] not in names]
            print("  exists: %s%s" % (f["name"], (" (MISSING OPTIONS, add by hand: %s)" % ", ".join(missing)) if missing else ""))
            continue
        opts = ", ".join('{name: %s, color: %s, description: ""}' % (json.dumps(o["name"], ensure_ascii=False), o["color"]) for o in f["options"])
        gh.graphql("""mutation($p: ID!, $n: String!) { createProjectV2Field(input: {projectId: $p, dataType: SINGLE_SELECT, name: $n,
                   singleSelectOptions: [%s]}) { projectV2Field { ... on ProjectV2SingleSelectField { id } } } }""" % opts,
                   write=True, p=proj["id"], n=f["name"])
        created = True
    # 5. Views
    print("views")
    views = {v["name"]: v for v in proj["views"]["nodes"]}
    for v in plan["views"]:
        view = views.get(v["name"])
        if view:
            print("  exists: " + v["name"])
        else:
            res = gh.graphql("""mutation($p: ID!, $n: String!) { createProjectV2View(input: {projectId: $p, name: $n, layout: %s}) {
                             projectV2View { id } } }""" % v["layout"], write=True, placeholder={}, p=proj["id"], n=v["name"])
            vid = (((res or {}).get("data") or {}).get("createProjectV2View") or {}).get("projectV2View", {}).get("id", "<VIEW_ID>")
            view = {"id": vid, "filter": None}
        if v["filter"] and view.get("filter") != v["filter"]:
            gh.graphql("""mutation($v: ID!, $f: String!) { updateProjectV2View(input: {viewId: $v, filter: $f}) { projectV2View { id } } }""",
                       write=True, v=view["id"], f=v["filter"])
        print("  by hand: %s: %s" % (v["name"], v["manual"]))
    if created and not args.dry_run:
        _, proj = find_project(gh)
        fields = {f["name"]: f for f in proj["fields"]["nodes"] if f}
    # 6. Issues
    print("issues")
    by_bl = issue_by_bl(list_issues(gh))
    tmp = Path(tempfile.mkdtemp(prefix="board-import-"))
    for it in items:
        if it["id"] in by_bl:
            print("  exists: #%d %s" % (by_bl[it["id"]]["number"], by_bl[it["id"]]["title"]))
            continue
        body = tmp / ("%s.md" % it["id"])
        body.write_text(it["body"], encoding="utf-8")
        cmd = ["gh", "issue", "create", "-R", REPO, "--title", it["title"], "--body-file", str(body), "--milestone", it["release"]]
        for lab in it["labels"]:
            cmd += ["--label", lab]
        out = gh.write(cmd, placeholder="")
        if out:
            url = out.strip().splitlines()[-1]
            node = json.loads(gh.read(["gh", "issue", "view", url, "--json", "id,number,title,url"]))
            by_bl[it["id"]] = node
    # 7. Project items and their field values
    print("project items and fields")
    in_project = project_items(gh, proj["id"]) if not str(proj["id"]).startswith("<") else {}
    for it in items:
        issue = by_bl.get(it["id"], {"id": "<ISSUE_ID:%s>" % it["id"], "url": "<URL:%s>" % it["id"]})
        entry = in_project.get(issue["url"])
        if entry:
            item_id, current = entry["item_id"], entry["values"]
        else:
            res = gh.graphql("""mutation($p: ID!, $c: ID!) { addProjectV2ItemById(input: {projectId: $p, contentId: $c}) { item { id } } }""",
                             write=True, placeholder={}, p=proj["id"], c=issue["id"])
            item_id = (((res or {}).get("data") or {}).get("addProjectV2ItemById") or {}).get("item", {}).get("id", "<ITEM_ID:%s>" % it["id"])
            current = {}
        for fname in ("Priority", "State", "Release", "Size", "Team"):
            value = it[fname.lower()]
            if not value or current.get(fname) == value:
                continue
            f = fields.get(fname)
            fid = f["id"] if f else "<FIELD_ID:%s>" % fname
            oid = next((o["id"] for o in (f or {}).get("options") or [] if o["name"] == value), "<OPTION_ID:%s=%s>" % (fname, value))
            if not args.dry_run and (fid.startswith("<") or oid.startswith("<")):
                raise SystemExit("%s: no field or option %s=%s on the project" % (it["id"], fname, value))
            gh.graphql("""mutation($p: ID!, $i: ID!, $f: ID!, $o: String!) { updateProjectV2ItemFieldValue(input: {projectId: $p,
                       itemId: $i, fieldId: $f, value: {singleSelectOptionId: $o}}) { projectV2Item { id } } }""",
                       write=True, p=proj["id"], i=item_id, f=fid, o=oid)
    print("%s %d writes" % ("would make" if args.dry_run else "made", gh.writes))
    print("Then by hand on github.com: the views' grouping and column field (see this script's docstring), and hide Status.")
    return 0


# ----------------------------------------------------------------------------------------------------------- export

HEADER = """# Backlog

> **Read-only export of the board on insyncalan/creaite-plan; edit the board, not this file.**
> Made by `python3 dev/tools/board_import.py export`. One issue per open item; a pull request in the code repo closes one
> with "closes insyncalan/creaite-plan#N". Sizes are rough: XS an hour or two, S under a day, M one to three days, L more,
> XL a sprint on its own.
"""


def section(body, name):
    m = re.search(r"<!-- %s -->\n(.*?)\n<!-- /%s -->" % (name, name), body or "", re.S)
    return m.group(1).strip() if m else None


def render(records):
    """records: id, title, body, release, state, priority, size, team, ref (issue number or None), open."""
    out = [HEADER, "## Summary", ""]
    open_recs = [r for r in records if r["open"]]
    releases = sorted({r["release"] or UNSCHEDULED for r in open_recs}, key=release_key)
    num = lambda r: int(ID_RE.search(r["id"]).group(0)[3:])
    for rel in releases:
        group = sorted([r for r in open_recs if (r["release"] or UNSCHEDULED) == rel], key=num)
        out += ["### " + rel, "", "| ID | Item | Size | State | Priority | Team | Issue |", "|----|------|------|-------|----------|------|-------|"]
        for r in group:
            summ = section(r["body"], "summary") or ""
            row = next((l for l in summ.splitlines() if l.startswith("| " + r["id"] + " ")), None)
            item = [c.strip() for c in row.strip().strip("|").split("|")][1] if row else r["title"][len(r["id"]) + 1:]
            ref = "#%s" % r["ref"] if r["ref"] else ""
            out.append("| %s | %s | %s | %s | %s | %s | %s |" % (r["id"], item, r["size"] or "", r["state"] or "",
                                                                 r["priority"] or "", r["team"] or "", ref))
        out.append("")
    out += ["## Write-ups", ""]
    for r in sorted(open_recs, key=num):
        out += ["### %s — %s" % (r["id"], r["title"][len(r["id"]) + 1:]), ""]
        summ = section(r["body"], "summary")
        plan_row = next((l for l in (summ or "").splitlines() if l.startswith("| " + r["id"] + " ")), None)
        if plan_row:
            out += ["**Plan (as imported):** " + [c.strip() for c in plan_row.strip().strip("|").split("|")][4], ""]
        wu = section(r["body"], "write-up")
        out += [wu if wu is not None else (r["body"] or "").strip(), ""]
    closed = sorted([r for r in records if not r["open"]], key=num)
    if closed:
        out += ["## Closed on the board", ""] + ["- %s (#%s, %s)" % (r["title"], r["ref"], r["state"] or "closed") for r in closed] + [""]
    return "\n".join(out).rstrip() + "\n"


def cmd_export(args):
    if args.from_plan:
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        records = [dict(i, ref=None, open=True) for i in plan["items"]]
    else:
        gh = GH(dry_run=True, pause=0)
        issues = issue_by_bl(list_issues(gh, with_body=True))
        _, proj = find_project(gh)
        values = project_items(gh, proj["id"]) if proj else {}
        records = []
        for bl, i in issues.items():
            v = values.get(i["url"], {}).get("values", {})
            records.append({"id": bl, "title": i["title"], "body": i.get("body") or "",
                            "release": v.get("Release") or (i.get("milestone") or {}).get("title") or UNSCHEDULED,
                            "state": v.get("State"), "priority": v.get("Priority"), "size": v.get("Size"), "team": v.get("Team"),
                            "ref": i["number"], "open": i["state"] == "OPEN"})
    text = render(records)
    target = Path(args.out) if args.out else BACKLOG
    target.write_text(text, encoding="utf-8")
    print("wrote %s: %d items (%d open)" % (target, len(records), sum(r["open"] for r in records)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("plan", help="dev/BACKLOG.md -> dev/tools/board-plan.json")
    a = sub.add_parser("apply", help="board-plan.json -> the board (idempotent)")
    a.add_argument("--dry-run", action="store_true", help="print every write; only read-only gh calls run")
    a.add_argument("--pause", type=float, default=1.0, help="seconds to wait after each write (default 1)")
    a.add_argument("--only", help="comma-separated BL ids to import (for a trial run)")
    e = sub.add_parser("export", help="the board -> dev/BACKLOG.md (read-only)")
    e.add_argument("--from-plan", action="store_true", help="render from board-plan.json instead of the board")
    e.add_argument("--out", help="write here instead of dev/BACKLOG.md")
    args = ap.parse_args(argv)
    return {"plan": cmd_plan, "apply": cmd_apply, "export": cmd_export}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
