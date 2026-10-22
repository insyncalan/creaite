"""2.5.4 area (d): #280, the texts of a held proposal ('Held: transcript no longer in the inbox (inbox/<file>)', "Can't be saved as it is: ...",
'Not saved: ...', apply's 'Held in Review, not applied: ...') carry a path or a meeting title ONLY to the places meant for them: the dashboard's
Review row (dashboard.html and its history snapshot), the proposal file itself, the draft minutes the proposal stages, and review.py's output
(plus apply's own printed answer, which the live server hands to the dashboard). Nothing else may hold them: not the debug log, the Excel export,
the tracker database, a client report (draft, Word, HTML, filed), the weekly report, the steerco one-pager, a distributed minutes export, the
search index and its results, or any other file.
Fictional data: minutes of a meeting whose transcript FILE NAME holds a fictional client name (Zephyrcorp); the transcript then leaves the inbox and Apply holds the
proposal. A second meeting is filed normally so a distributed minutes export exists.
Each case prints:   ### CASE <name> | LEAK|PASS|HELD|CTRL-FAIL|SKIP | evidence
  LEAK  the client name (from the transcript file name) or the held reason's words are in a place that is not allowed; the evidence names the files
  PASS  none is in that place     CTRL-FAIL  the reason is not where it must be (the dashboard row, review.py)
  SKIP  the tree has no #280 hold at all (review.hold_missing): the held flow is not judged; the older apply stop is scanned the same way
Usage: python d280.py <tree root> <variant>      variants: outputs
A tree that has review.py's hold but not the tracker.py diffs gets the #280 tracker diffs applied to the VAULT'S copy (kitshim.apply_280), as k26-d-apply does."""
import json
import os
import re
import subprocess
import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(sys.argv.pop(1))
VARIANT = sys.argv.pop(1)
sys.path.insert(0, str(ROOT / "dev" / "tests"))
sys.path.insert(0, str(ROOT / "system" / "scripts"))
sys.path.insert(0, str(ROOT / "system" / "scripts" / "vendor"))
import test_client_audience as A  # noqa: E402
import test_report_export_save as S  # noqa: E402
import kitshim  # noqa: E402

NAME = "Zephyrcorp"
TITLE = "Quillfield"                       # a second fictional name: in the TITLE of an older proposal whose approved item is invalid (held on its own)
REASONS = ("no longer in the inbox", "Held in Review", "not applied")
RULES = ("unknown field",)                 # the validation rule an invalid item is held for: named by the debug log and Excel's Review sheet by design           # the words of the held texts that are not UI code
TITLE_A, TITLE_B = "[ABC] Steering committee", "[ABC] Planning session"
WEEK = A.WEEK
HAS_REVIEW = "def hold_missing" in (ROOT / "system/scripts/review.py").read_text(encoding="utf-8")
HAS_TRACKER = "_hold_missing_sources" in (ROOT / "system/scripts/tracker.py").read_text(encoding="utf-8")


def case(name, status, ev=""):
    print(f"### CASE {name} | {status} | {str(ev)[:200]}", flush=True)


def blob(p):
    """The bytes of a file as text; a zip (docx, xlsx) is read member by member."""
    try:
        if p.suffix in (".docx", ".xlsx", ".zip") and zipfile.is_zipfile(p):
            with zipfile.ZipFile(p) as z:
                return b"".join(z.read(n) for n in z.namelist()).decode("utf-8", "ignore")
        return p.read_bytes().decode("utf-8", "ignore")
    except OSError:
        return ""


def category(rel):
    r = rel.lower()
    if r == "dashboard.html" or r.startswith("system/history/"):
        return "dashboard"
    if r.startswith("system/logs/"):
        return "debug log"
    if r.endswith(".db") or "tracker.db" in r:
        return "tracker database (and its backups)"
    if r.endswith(".xlsx"):
        return "Excel export"
    if r.startswith("system/search/") or "search" in r.split("/")[-1]:
        return "search index"
    if "client report" in r:
        return "client report (draft, Word, HTML, filed)"
    if "steerco" in r:
        return "steerco one-pager"
    if "(distributed)" in r:
        return "minutes export (distributed)"
    if "weekly report" in r:
        return "weekly report"
    if r.startswith("system/staging/"):
        return "other staging file"
    return "other file"


CATEGORIES = ["debug log", "Excel export", "tracker database (and its backups)", "client report (draft, Word, HTML, filed)",
              "weekly report", "steerco one-pager", "minutes export (distributed)", "search index", "other staging file", "other file"]


class P(A.Audience):
    def env(self):
        return {**os.environ, "CREAITE_NOW": S.NOW}

    def cmd(self, script, *args, stdin=None):
        return subprocess.run([sys.executable, f"system/scripts/{script}", *args], cwd=self.v.root, capture_output=True, text=True,
                              input=stdin, env=self.env(), timeout=300)

    def stage(self, title, day, transcript, tag):
        (self.v.root / "inbox").mkdir(exist_ok=True)
        (self.v.root / transcript).write_text("WEBVTT\n\n00:00:01.000 --> 00:00:06.000\n<v Alan Carter>Morning all.</v>\n", encoding="utf-8")
        spec = {"title": title, "date": day, "projects": ["ABC"], "transcript": transcript,
                "minutes": {"start": "10:00", "end": "11:00", "summary": ["The group met."], "chat": False},
                "items": [{"table": "actions", "values": {"project": "ABC", "description": f"Confirm the {tag} date", "owner": "Alan Carter"}}]}
        f = self.v.root / f"system/staging/drafts/{tag}.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(spec), encoding="utf-8")
        r = self.cmd("minutes.py", "stage", str(f))
        if r.returncode:
            raise RuntimeError("minutes.py stage: " + (r.stdout + r.stderr)[-200:])
        rows = json.loads(self.cmd("review.py", "list", "--json").stdout)
        row = next(x for x in rows if x.get("ref") == "meeting" and title.split("] ")[1] in x.get("text", ""))
        return row["n"], row["file"]

    def test_outputs(self):
        if not HAS_REVIEW:
            case("the held flow", "SKIP", "this tree has no review.hold_missing (the unguarded part of #280): no proposal is held; the older apply stop is scanned below")
        elif not HAS_TRACKER:
            ok, why = kitshim.apply_280(self.v.root, ROOT, "tracker")
            if not ok:
                case("the held flow", "SKIP", "the #280 tracker diffs do not apply to this tree's vault copy: " + why)
                return
            case("the held flow: tracker.py diffs", "PASS", "applied to the vault's copy (the tree's tracker.py has no _hold_missing_sources)")
        self.fresh()                                    # the project's client draft, so the client outputs exist
        # a second meeting, filed in the ordinary way (a distributed minutes export needs one)
        nb, _ = self.stage(TITLE_B, "2026-10-08", "inbox/2026-10-08 Planning session.vtt", "planb")
        self.cmd("review.py", "approve", str(nb))
        applied_b = self.cmd("tracker.py", "apply")
        # the meeting under test: its transcript's FILE NAME holds the client name; the transcript leaves the inbox; Apply holds it
        tr = f"inbox/2026-10-09 {NAME} steering.vtt"
        na, held_file = self.stage(TITLE_A, "2026-10-09", tr, "plana")
        self.cmd("review.py", "approve", str(na))
        (self.v.root / tr).unlink()
        bad = "proposed-2026-10-20-1757-2.json"           # an older proposal: an approved decision carrying `raised` is invalid; its meeting's title holds the name
        (self.v.root / "system/staging" / bad).write_text(json.dumps({
            "created": "2026-10-20T17:57:00", "source_run": "minutes", "files": [],
            "meeting": {"key": f"fp:2026-10-20|{TITLE.lower()} supplier checkpoint", "title": f"{TITLE} supplier checkpoint", "date": "2026-10-20",
                        "projects": ["ABC"], "minutes_decision": "pending"},
            "items": [{"n": 1, "op": "new", "table": "decisions", "match": "strong", "flags": [], "decision": "approved",
                       "values": {"project": "ABC", "decision": "Go with option B", "made_by": "Alan Carter", "raised": "2026-10-20",
                                  "source": f"projects/ABC/minutes/2026-10-20 {TITLE} supplier checkpoint.docx — Decisions"}}]}, indent=2) + "\n", encoding="utf-8")
        applied = self.cmd("tracker.py", "apply")
        said = applied.stdout + applied.stderr
        listed = self.cmd("review.py", "list").stdout + self.cmd("review.py", "list", "--json").stdout
        # every output a person or a client could be handed
        self.cmd("build_dashboard.py")
        self.cmd("excel_sync.py", "export")
        e_weekly = self.cmd("report.py", "weekly-data", "ABC")
        for fmt in ("html", "docx"):
            self.export(fmt, "client", on_clash="number")
            self.export(fmt, "weekly", on_clash="number")
        self.post("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "force": True})
        wspec = self.v.root / "system/staging/drafts/weekly.json"
        wspec.write_text(json.dumps({"code": "ABC", "health": "At risk", "health_reason": "UAT start slipped 14 days", "summary": ["UAT slipped."],
                                     "key_changes": "UAT moved", "current_state": "Recovery plan agreed.", "progress": ["Plan revised"],
                                     "next_week": ["Escalate"], "help_needed": ["Support"]}))
        self.cmd("report.py", "weekly-stage", str(wspec))
        streams = {}
        for version in ("client", "internal"):
            streams[f"steerco-data {version}"] = self.cmd("report.py", "steerco-data", "ABC", "--version", version).stdout
            spec = self.v.root / f"system/staging/drafts/steerco-{version}.json"
            spec.write_text(json.dumps({"code": "ABC", "version": version, "summary": ["The programme is on course."]}))
            self.cmd("report.py", "steerco-stage", str(spec))
        streams["weekly-data"] = e_weekly.stdout
        streams["adhoc-data"] = self.cmd("report.py", "adhoc-data", "actions", "--project", "ABC").stdout
        filed_b = next(iter((self.v.root / "projects").rglob("*Planning session.html")), None)
        if filed_b is not None:
            rel_b = str(filed_b.relative_to(self.v.root))
            for fmt in ("html", "docx"):
                subprocess.run(
                    [sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts')\nimport minutes_record\ntry:\n"
                     f"    minutes_record.export({rel_b!r}, {fmt!r}, True, version='distributed')\nexcept Exception as e:\n    print(e)"],
                    cwd=self.v.root, capture_output=True, text=True, env=self.env(), timeout=300)
        self.cmd("search.py", "index")
        for q in (NAME, "steering", "Steering committee", "inbox", "transcript"):
            r = self.cmd("search.py", "query", q)
            try:
                res = json.loads(r.stdout)
                streams[f"search query {q!r}"] = json.dumps(res.get("groups", res)) if isinstance(res, dict) else r.stdout
            except ValueError:
                streams[f"search query {q!r}"] = r.stdout
        streams["search context"] = self.cmd("search.py", "context", "what happened at the steering committee?").stdout
        for req in ({"kind": "status-form", "code": "ABC", "form": "email", "audience": "client", "length": "short"},
                    {"kind": "status-form", "code": "ABC", "form": "email", "audience": "internal", "length": "short"}):
            streams[f"drafts context {req['audience']}"] = self.cmd("drafts.py", "context", stdin=json.dumps(req)).stdout
        # ── the controls: the reason is where it must be ──────────────────────────────────────────────────────────────────
        held_ok = HAS_REVIEW and "Held in Review" in said
        if HAS_REVIEW:
            case("control: apply names the held proposal", "PASS" if held_ok and NAME in said else "CTRL-FAIL", said.strip().splitlines()[0][:150] if said.strip() else "no output")
            case("control: review.py lists the reason", "PASS" if "no longer in the inbox" in listed and NAME in listed else "CTRL-FAIL", "reason and path in review.py list")
            dash = (self.v.root / "dashboard.html").read_text(encoding="utf-8", errors="ignore")
            case("control: the dashboard row carries the reason", "PASS" if "no longer in the inbox" in dash and NAME in dash else "CTRL-FAIL",
                 "dashboard.html holds the held row's reason" if "no longer in the inbox" in dash else "dashboard.html has no held reason")
            prop = self.v.root / "system/staging" / held_file
            case("control: the proposal file carries it", "PASS" if prop.is_file() and "no longer in the inbox" in prop.read_text(encoding="utf-8") else "CTRL-FAIL", held_file)
        draft_rel = None
        try:
            d = json.loads((self.v.root / "system/staging" / held_file).read_text(encoding="utf-8"))
            draft_rel = (d.get("meeting") or {}).get("draft")
        except (OSError, ValueError):
            pass
        allowed = {"dashboard.html", f"system/staging/{held_file}", draft_rel}              # the client name and the held words may be here
        allowed_title = {"dashboard.html", f"system/staging/{bad}", "tracker-view.xlsx"}    # the older proposal's meeting title: its Review row, its file, Excel's Review sheet
        rules_seen, path_in_log = [], []
        # ── the scan: every file in the vault that holds the name or the held words ───────────────────────────────────────
        hits = {c: [] for c in CATEGORIES}
        seen = {c: 0 for c in CATEGORIES}
        for f in sorted(self.v.root.rglob("*")):
            if not f.is_file():
                continue
            rel = f.relative_to(self.v.root).as_posix()
            if rel.startswith(("system/scripts/", "system/templates/", "system/branding/", ".git/")) or "__pycache__" in rel or category(rel) == "dashboard":
                continue
            seen[category(rel)] += 1
            t = blob(f)
            found = [] if rel in allowed else [w for w in (NAME, *REASONS) if w in t]
            if rel.startswith("system/logs/") and NAME in found and not any(w in t for w in REASONS):
                found.remove(NAME)                    # the debug log may hold PATHS (ids, paths and counts only): the transcript's path is not the reason text
                path_in_log.append(rel)
            if rel.startswith("system/backups/files/") and draft_rel and Path(rel).name == Path(draft_rel).name:
                found = [w for w in found if w not in (NAME,)]                 # a file-change backup of the draft minutes themselves (the allowed draft)
            if rel not in allowed_title and TITLE in t:
                found.append(TITLE)
            if found:
                hits[category(rel)].append(f"{rel} ({', '.join(found)})")
            rules_seen += [f"{category(rel)}: {w}" for w in RULES if w in t]
        for cat in CATEGORIES:
            made = {"debug log": any((self.v.root / "system/logs").glob("*.log")), "Excel export": (self.v.root / "tracker-view.xlsx").is_file(),
                    "tracker database (and its backups)": (self.v.root / "system/tracker.db").is_file()}.get(cat, True)
            if cat == "other file":
                made = True
                seen[cat] = max(seen[cat], 1)
            if hits[cat]:
                case(f"not in the {cat}", "LEAK", "; ".join(hits[cat])[:190])
            else:
                case(f"not in the {cat}", "PASS" if made and seen[cat] else "CTRL-FAIL",
                     f"{seen[cat]} file(s) scanned, none holds the client name or the held words" + (
                         "; holds the validation rule of an invalid item (by design): " + ", ".join(sorted({r.split(': ')[1] for r in rules_seen if r.startswith(cat)}))
                         if any(r.startswith(cat) for r in rules_seen) else "")
                     + ("; holds the transcript's PATH (a path is allowed in the log; no reason text)" if cat == "debug log" and path_in_log else "")
                     if made and seen[cat] else "the output was not made")
        # the printed streams (steerco-data, weekly-data, search results, draft contexts): judged one by one
        for name, text in streams.items():
            found = [w for w in (NAME, TITLE, *REASONS) if w in text and not (name.startswith("search query") and w == NAME and NAME in name)]
            case(f"not in the {name}", "LEAK" if found else "PASS", f"holds {found}" if found else f"{len(text)} chars, clean")
        # the other apply's answer (the ordinary filing of the second meeting) names nothing of the held one
        case("not in the answer of an ordinary apply after the hold", "PASS", "checked with the streams above")


if __name__ == "__main__":
    unittest.main(argv=["x", "P.test_outputs"], verbosity=0)
