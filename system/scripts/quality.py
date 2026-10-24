"""creaite quality (BL-233, sprint-drafts-extraction): what you approve, edit and reject, by source and by item type, and how the AI
drafts are used. Read-only, in the style of status_facts.py: it reads what creaite already keeps and writes nothing.

  python3 system/scripts/quality.py [--weeks N] [--json]

Reads the proposals (system/staging/applied/*.json and the pending ones in system/staging/), the `rejected` table (BL-133's reasons),
BL-232's `as_proposed` (which fields an edit changed) and system/staging/draft-stats.json (each AI-draft feature: offered, used, edited,
rejected). Over a period (4 weeks by default, by the day each proposal was made) and the one before it, it counts:
  - extraction: approved as proposed, approved after an edit and rejected, by source (minutes, sweep mail, sweep Teams, dashboard) and
    by item type (action, risk, issue, decision, assumption or dependency, promise, update), with the reasons given for rejections;
  - edits: the fields changed most, and in which source; an edit made before BL-232 is "edited, field unknown", never guessed;
  - drafts: each AI-draft feature's offered, used, edited and rejected counts;
  - repeats (BL-297): how often a proposal was merged into, or retargeted at, an existing item, and how many of those nothing marked
    (with the item IDs of the misses).
Every figure is a count with the number it is out of ("11 of 192"), never a bare percentage, and nothing is rated for a group under
MIN_RATED (10). Counts about extraction and drafts only, never about a person (no owner, sender or name is read or shown; a reason in
Alan's own words is counted as "Other"); internal; no report, one-pager, client output or Excel export reads it. Nothing here writes
to tracker.db. Set CREAITE_NOW="YYYY-MM-DD HH:MM" to fix the clock (tests).
"""
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

MIN_RATED = 10
WEEKS = 4
SOURCES = (("minutes", "Minutes"), ("mail", "Sweep: mail"), ("teams", "Sweep: Teams"), ("dashboard", "Dashboard"))
TYPES = (("action", "Actions"), ("risk", "Risks"), ("issue", "Issues"), ("decision", "Decisions"),
         ("assumption", "Assumptions and dependencies"), ("promise", "Promises"),     # promises: BL-125 A, their precision
         ("update", "Updates to existing items"))
REASONS = ("Not an action", "Duplicate", "Chatter", "Already done", "Wrong project", "Doesn't need tracking", "For another team",
           "Not mine to track")          # BL-315: the seven reasons, and BL-133's "Not mine to track" so older rejects keep theirs
FIELD_LABELS = {"description": "Title", "decision": "Title", "owner": "Owner", "made_by": "Decision maker", "due_date": "Due date",
                "needed_by": "Needed by", "priority": "Priority", "workstream": "Workstream", "milestone": "Milestone", "type": "Type",
                "impact": "Impact", "likelihood": "Likelihood", "response_action": "Response", "status": "Status",
                "latest_update": "Latest update", "project": "Project", "client_visible": "Client-visible",
                "client_message": "Client messaging", "reasoning": "Reasoning", "options": "Options considered", "date": "Date",
                "promised_by": "Promised by", "promised_to": "Promised to"}


def today():
    """Today (CREAITE_NOW fixes it in tests)."""
    fixed = os.environ.get("CREAITE_NOW")
    return date.fromisoformat(fixed[:10]) if fixed else date.today()


def source_of(data, item):
    """Which extraction source an item came from, or None for one this measure leaves out (cx-edit, Excel, reports, AI drafts)."""
    run = data.get("source_run") or ""
    if run == "cx-minutes":
        return "minutes"
    if run == "cx-sweep":
        src = str((item.get("values") or {}).get("source") or item.get("source") or "")
        return "teams" if src.startswith("Teams") else "mail"
    return "dashboard" if run == "dashboard" else None


def type_of(item):
    """An item's type as Quality groups it."""
    if item.get("op") != "new":
        return "update"
    table, v = item.get("table"), item.get("values") or {}
    if table == "raid":
        return {"Risk": "risk", "Issue": "issue"}.get(v.get("type") or "Risk", "assumption")
    return {"actions": "action", "decisions": "decision", "promises": "promise"}.get(table)


def outcome(item):
    """approved (as proposed), edited (approved after an edit), rejected, or pending."""
    d = item.get("decision") or "pending"
    if d == "approved" and (item.get("as_proposed") or item.get("edited_in")):
        return "edited"
    return d if d in ("approved", "rejected") else "pending"


def changed_fields(item):
    """The fields an edit changed (BL-232's as_proposed against what was approved), or None when it was edited before BL-232."""
    before = item.get("as_proposed")
    if not isinstance(before, dict):
        return None
    after = item.get("values" if item.get("op") == "new" else "changes") or {}
    return sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k) and k not in ("source", "raised"))


def proposals():
    """Every proposal creaite keeps, applied and pending: (its day, its data)."""
    for folder in (paths.APPLIED, paths.STAGING):
        for p in sorted(folder.glob("proposed-*.json")):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue                    # a file being written or not JSON: left out of the counts, never guessed
            yield str(data.get("created") or p.name[9:19])[:10], data


def blank():
    """An empty tally: approved, edited, rejected, pending."""
    return {"approved": 0, "edited": 0, "rejected": 0, "pending": 0}


def tally(start, end):
    """The counts for proposals made from start to end (inclusive), by source and by type, with reasons and fields."""
    by_source, by_type = {k: blank() for k, _ in SOURCES}, {k: blank() for k, _ in TYPES}
    reasons, fields, unknown = {}, {}, {}
    for day, data in proposals():
        if not start <= day <= end:
            continue
        for item in data.get("items") or []:
            src, kind = source_of(data, item), type_of(item)
            if not src or not kind or not isinstance(item, dict):
                continue
            o = outcome(item)
            by_source[src][o] += 1
            by_type[kind][o] += 1
            if o == "rejected":
                r = item.get("reject_reason") or ""
                key = r if r in REASONS else "Other" if r else "No reason given"
                reasons[key] = reasons.get(key, 0) + 1
            if o == "edited":
                count_fields(item, src, fields, unknown)
    return {"by_source": by_source, "by_type": by_type, "reasons": reasons, "fields": fields, "unknown": unknown}


def count_fields(item, src, fields, unknown):
    """Add an edited item's changed fields (by source), or count it as "field unknown" when it was edited before BL-232."""
    changed = changed_fields(item)
    if changed is None:
        unknown[src] = unknown.get(src, 0) + 1
        return
    for f in changed:
        row = fields.setdefault(FIELD_LABELS.get(f, f.replace("_", " ").capitalize()), {})
        row[src] = row.get(src, 0) + 1


def figure(n, of):
    """A count out of its denominator, with a rate only when the group has MIN_RATED or more: {"n", "of", "text", "rated"}."""
    rated = of >= MIN_RATED
    text = f"{n} of {of}" + (f" ({round(100 * n / of)}%)" if rated and of else "")
    return {"n": n, "of": of, "text": text, "rated": rated}


def rows(groups, labels):
    """One row per group: decided (approved + edited + rejected), each outcome as a figure out of decided, and pending."""
    out = []
    for key, label in labels:
        g = groups[key]
        decided = g["approved"] + g["edited"] + g["rejected"]
        if not decided and not g["pending"]:
            continue
        out.append({"key": key, "label": label, "decided": decided, "pending": g["pending"], "rated": decided >= MIN_RATED,
                    "approved": figure(g["approved"], decided), "edited": figure(g["edited"], decided),
                    "rejected": figure(g["rejected"], decided)})
    return out


def drafts_rows():
    """Each AI-draft feature's counts from draft-stats.json: used, edited and rejected out of offered (counts only)."""
    try:
        stats = json.loads((paths.STAGING / "draft-stats.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        stats = {}
    try:
        import drafts
        labels = {**{f: v[0] for f, v in drafts.FEATURES.items()}, **getattr(drafts, "COUNTED", {})}   # BL-342 Part 5
    except ImportError:          # the drafts scaffold isn't installed: the features are named by their IDs
        labels = {}
    out = []
    for f in list(labels) + sorted(k for k in stats if k not in labels and not k.startswith("_")):
        c = stats.get(f) or {}
        offered = int(c.get("offered") or 0)
        out.append({"feature": f, "label": labels.get(f, f), "offered": offered, "rated": offered >= MIN_RATED,
                    **{e: figure(int(c.get(e) or 0), offered) for e in ("used", "edited", "rejected")}})
    return out


def share(t):
    """(approved without an edit, decided) over every source in a tally."""
    g = list(t["by_source"].values())
    return sum(x["approved"] for x in g), sum(x["approved"] + x["edited"] + x["rejected"] for x in g)


def moved(now, before):
    """One line on what moved since the previous period: the share approved without an edit, when both periods can be rated."""
    a, n = share(now)
    b, m = share(before)
    if n < MIN_RATED or m < MIN_RATED:
        return (f"Too few decided proposals to compare yet: {n} this period and {m} the one before (each needs {MIN_RATED}).")
    pa, pb = round(100 * a / n), round(100 * b / m)
    word = "up" if pa > pb else "down" if pa < pb else "unchanged"
    return (f"Approved without an edit: {a} of {n} ({pa}%) this period, {word} from {b} of {m} ({pb}%) the period before.")


def measure(weeks=WEEKS):
    """The Quality figures for the last `weeks` weeks and the period before them."""
    end = today()
    start = end - timedelta(weeks=weeks) + timedelta(days=1)
    prev_end, prev_start = start - timedelta(days=1), start - timedelta(weeks=weeks)
    now, before = tally(start.isoformat(), end.isoformat()), tally(prev_start.isoformat(), prev_end.isoformat())
    fields = sorted(({"field": f, "n": sum(by.values()), "by_source": by} for f, by in now["fields"].items()),
                    key=lambda r: (-r["n"], r["field"]))
    edited = sum(r["edited"] for r in now["by_source"].values())
    rejected = sum(r["rejected"] for r in now["by_source"].values())
    return {"period": {"from": start.isoformat(), "to": end.isoformat(), "weeks": weeks}, "min": MIN_RATED,
            "by_source": rows(now["by_source"], SOURCES), "by_type": rows(now["by_type"], TYPES),
            "reasons": [{"reason": k, **figure(v, rejected)} for k, v in sorted(now["reasons"].items(), key=lambda kv: -kv[1])],
            "fields": [{**r, **figure(r["n"], edited)} for r in fields[:8]],
            "unknown": {"n": sum(now["unknown"].values()), "of": edited}, "edited": edited,
            "drafts": drafts_rows(), "moved": moved(now, before), "duplicates": duplicates(start.isoformat(), end.isoformat()),
            "repeats": repeats(start.isoformat(), end.isoformat()), "source_labels": dict(SOURCES)}


def duplicates(start, end):
    """How many rejections in the period the tracker recorded as a duplicate of an existing item (BL-133's `rejected` table), out of
    all it recorded then. Read-only."""
    import sqlite3
    try:
        con = sqlite3.connect(f"file:{paths.DB}?mode=ro", uri=True)
        try:
            rows = con.execute("SELECT duplicate_of FROM rejected WHERE substr(rejected_at, 1, 10) BETWEEN ? AND ?",
                               (start, end)).fetchall()
        finally:
            con.close()
    except sqlite3.Error:        # no tracker yet, or an older one without the column: nothing to count
        rows = []
    return figure(sum(1 for r in rows if r[0]), len(rows))


# ===== BL-297 (sprint-smart-updates) ===== how often Alan points a proposal at an existing item himself: Merge (always on a "Looks
# like" mark, BL-221) and Update an existing item instead (review.py retarget, marked or not). A retarget onto an item nothing marked,
# or onto another item than the one marked, is a miss of the matching; its item ID is listed so the miss can be looked at. Counts and
# item IDs only, from the proposals (an undone merge or retarget leaves no trace, so it isn't counted).
def repeat_kind(item):
    """merged, on-mark, other-mark or unmarked for an item Alan merged or retargeted, else None."""
    note = item.get("retargeted")
    if isinstance(note, dict):
        return "on-mark" if note.get("marked") == note.get("to") else "other-mark" if note.get("marked") else "unmarked"
    return "merged" if item.get("op") == "update" and isinstance(item.get("merged_from"), dict) else None


def repeats(start, end):
    """Merges and retargets in the period: {merged, retargeted, total, unmarked (a figure out of total), other_mark, missed: [IDs]}."""
    c, missed = {"merged": 0, "on-mark": 0, "other-mark": 0, "unmarked": 0}, []
    for day, data in proposals():
        for item in (data.get("items") or []) if start <= day <= end else []:
            kind = repeat_kind(item) if isinstance(item, dict) else None
            if kind:
                c[kind] += 1
            if kind in ("other-mark", "unmarked"):
                missed.append(item["retargeted"]["to"])
    total = sum(c.values())
    return {"merged": c["merged"], "retargeted": total - c["merged"], "total": total, "unmarked": figure(c["unmarked"], total),
            "other_mark": c["other-mark"], "missed": sorted(set(missed))}
# ===== end BL-297 =====


# ===== BL-315 (v1.9.2) ===== Activity › What you rejected: the latest rejects, pending or applied, each named "<file>#<n>" so its
# reason can be changed, the reject undone or approved instead (review.py). The item's text and kind, never an owner or a sender.
def recent_rejects(limit=50):
    """The latest rejected items, newest first: [{key, file, ref, applied, project, table, kind, text, reason, duplicate_of, at, fp}]."""
    out = []
    for folder in (paths.APPLIED, paths.STAGING):
        for p in sorted(folder.glob("proposed-*.json")):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue                    # a file being written or not JSON: left out of the list, never guessed
            out += [reject_row(p.name, data, it) for it in data.get("items") or []
                    if isinstance(it, dict) and it.get("decision") == "rejected"]
    out.sort(key=lambda r: (r["at"], r["key"]), reverse=True)
    return out[:limit]


def reject_row(name, data, it):
    """One line of recent_rejects."""
    import build_dashboard
    v = it.get("values") or {}
    text = v.get("description") or v.get("decision") or v.get("summary") or v.get("name") or it.get("id") or ""
    return {"key": f"{name}#{it.get('n')}", "file": name, "ref": it.get("n"), "applied": bool(it.get("applied")),
            "project": v.get("project") or str(it.get("id") or "").split("-")[0], "table": it.get("table"),
            "kind": type_of(it), "text": str(text)[:300], "reason": it.get("reject_reason") or None,
            "duplicate_of": it.get("duplicate_of") or None,
            "at": str(it.get("rejected_at") or data.get("created") or name[9:19])[:19],
            "fp": build_dashboard.item_fp(it)}      # 2.6.4 (#345): Approve instead names the item it means
# ===== end BL-315 =====


def main(argv):
    """Print the measure, as text or JSON."""
    weeks = int(argv[argv.index("--weeks") + 1]) if "--weeks" in argv else WEEKS
    m = measure(weeks)
    if "--json" in argv:
        print(json.dumps(m, indent=1, ensure_ascii=False))
        return 0
    print(f"Quality, {m['period']['from']} to {m['period']['to']}. {m['moved']}")
    for part, title in (("by_source", "By source"), ("by_type", "By type")):
        print(f"\n{title}:")
        for r in m[part]:
            print(f"  {r['label']}: approved {r['approved']['text']}, edited {r['edited']['text']}, rejected {r['rejected']['text']}"
                  + ("" if r["rated"] else f" (not rated: fewer than {MIN_RATED})") + (f"; {r['pending']} pending" if r["pending"] else ""))
    r = m["repeats"]
    print(f"\nPointed at an existing item: {r['total']} (merged {r['merged']}, updated instead {r['retargeted']}); "
          f"not marked: {r['unmarked']['text']}" + (f"; missed: {', '.join(r['missed'])}" if r["missed"] else ""))
    print("\nAI drafts:")
    for r in m["drafts"]:
        print(f"  {r['label']}: offered {r['offered']}; used {r['used']['text']}, edited {r['edited']['text']}, "
              f"rejected {r['rejected']['text']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
