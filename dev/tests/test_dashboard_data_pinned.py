"""BL-229 wave 2 (v1.7.0): pin build_dashboard's review_queue, flow_data and hub_record (through meeting_hub) before they are
split. The sample vault (test_dashboard.populate) at a fixed date, plus what reaches their branches, goes through
build_dashboard.collect, and the dashboard's "review", "hub" and "flow" data are compared with dev/tests/pinned/dashboard_data.json.

- review: minutes (with coverage, and one whose draft has gone), a report and file changes waiting; new actions, risks and
  decisions; updates (a field, a meeting's update with its why, a project's health, a milestone); an item needing a project, a
  possible match, flags (conflict, no owner, date from the file, new workstream), signals, guessed fields, a suggested
  workstream, an item moved from another proposal, a likely duplicate, and wording only approved on its own.
- hub: calendar meetings before, during and after the day's clock (Teams or not, private and all-day left out), transcript
  statuses (available, not transcribed, loaded), a prep page, staged minutes, applied minutes whose items are now tracker
  rows (one due soon, one promised by someone else), a quick note, processed.txt's filed meetings, a carried point.
- flow: weeks of opened, closed and cancelled actions and risks, due dates moved (and one move undone), milestone forecasts
  moved, a week from a saved snapshot, ageing buckets.

Fixed: the sample vault's dates (TODAY), the scripts' clock (CREAITE_NOW), the change log's times. Masked: the vault path and
each proposal's age (review.age reads the real clock).

Run: python3 dev/tests/test_dashboard_data_pinned.py          (quick tier: no Chrome)
Record (only before the split, or for a reviewed change): CREAITE_PIN_RECORD=1 python3 dev/tests/test_dashboard_data_pinned.py
"""
import json
import os
import re
import sqlite3
import subprocess
import sys
import unittest
from contextlib import closing
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_dashboard  # noqa: E402
from test_tracker import ABC, Vault, action, make_draft  # noqa: E402

FIXED = date(2026, 10, 9)                               # a Friday, as in test_snapshots and test_prep_context_pinned
NOW = f"{FIXED} 11:30"
test_dashboard.TODAY = FIXED
os.environ["CREAITE_NOW"] = NOW                       # this file's day is its own, whatever clock the run is pinned to (#178)
PINNED = Path(__file__).resolve().parent / "pinned" / "dashboard_data.json"
RECORD = os.environ.get("CREAITE_PIN_RECORD") == "1"
d = test_dashboard.d
SRC = f"{ABC}/minutes/{d(-5)} Steering.docx — Actions"


def new(table, n, decision="pending", **v):
    return {"n": n, "op": "new", "table": table, "values": {"source": SRC, **v}, "match": "strong", "flags": [],
            "decision": decision}


def history(v):
    """A week later: due dates moved, a milestone forecast moved twice, an action closed, one cancelled, a risk closed; and
    an apply that was undone (its move never happened). The change log's times are set to fixed days, apply by apply."""
    con = sqlite3.connect(v.root / "system/tracker.db")
    with closing(con):
        ids = {r[0]: r[1] for r in con.execute("SELECT description, id FROM actions")}
        rids = {r[0]: r[1] for r in con.execute("SELECT description, id FROM raid")}
    for name, items in (
            ("move1", [{"n": 1, "op": "update", "table": "actions", "id": ids["Book UAT environment"],
                        "changes": {"due_date": d(3)}, "based_on": None, "decision": "approved"},
                       {"n": 2, "op": "update", "table": "milestones", "id": "ABC-M-001",
                        "changes": {"forecast_date": d(17)}, "decision": "approved"},
                       action(3, description="Write the cut-over plan", raised=d(-12), due_date=d(-6), source=SRC),
                       action(4, description="Send the risk log", raised=d(-11), due_date=d(-2), source=SRC)]),
            ("move2", [{"n": 1, "op": "update", "table": "milestones", "id": "ABC-M-001",
                        "changes": {"forecast_date": d(24)}, "decision": "approved"},
                       {"n": 2, "op": "update", "table": "raid", "id": rids["Test licences not ordered"],
                        "changes": {"status": "Closed", "closed": d(-2)}, "decision": "approved"}])):
        v.propose(name, items)
        v.run("apply")
    with closing(sqlite3.connect(v.root / "system/tracker.db")) as con:
        ids = {r[0]: r[1] for r in con.execute("SELECT description, id FROM actions")}
    v.propose("close", [{"n": 1, "op": "update", "table": "actions", "id": ids["Write the cut-over plan"],
                         "changes": {"status": "Closed", "closed": d(-3)}, "decision": "approved"},
                        {"n": 2, "op": "update", "table": "actions", "id": ids["Send the risk log"],
                         "changes": {"status": "Cancelled", "closed": d(-1)}, "decision": "approved"}])
    v.run("apply")
    v.propose("undone", [{"n": 1, "op": "update", "table": "actions", "id": ids["Escalate data access to the client CIO"],
                          "changes": {"due_date": d(30)}, "decision": "approved"}])
    v.run("apply")
    v.run("undo")
    with closing(sqlite3.connect(v.root / "system/tracker.db")) as con:
        days = {1: -40, 2: -16, 3: -9, 4: -4, 5: -2}
        for apply_id, back in days.items():
            day = (FIXED + timedelta(days=back)).isoformat()
            con.execute("UPDATE change_log SET at = ? || ' 10:00:00.000' WHERE apply_id = ?", (day, apply_id))
            con.execute("UPDATE applies SET at = ? || ' 10:00:00.000' WHERE apply_id = ?", (day, apply_id))
        con.execute("UPDATE applies SET undone_at = ? WHERE undone_at IS NOT NULL", (f"{d(-2)} 11:00:00.000",))
        con.commit()
    hist = v.root / "system/history"
    hist.mkdir(parents=True, exist_ok=True)
    (hist / f"flow-{d(-12)}.json").write_text(json.dumps({"date": d(-12), "projects": {"ABC": {"overdue": 7, "open": 9}}}))


def review_world(v):
    """Pending proposals that reach every branch of review_queue."""
    for rel in ("system/staging/drafts/Weekly report.docx", "system/staging/drafts/Design minutes.docx"):
        make_draft(v.root / rel)
    v.propose("report", [], report={"kind": "weekly", "project": "ABC", "title": "Weekly report",
                                    "draft": "system/staging/drafts/Weekly report.docx", "report_decision": "pending"})
    v.propose("files", [], file_changes={"title": "Add to ABC memory", "project": "ABC", "file_changes_decision": "pending",
                                          "file_ops": [{"op": "write", "path": f"{ABC}/CLAUDE.md", "text": "x"}]})
    v.propose("design", [new("actions", 1, project="ABC", description="Share the design pack", owner="Omar Haddad",
                             due_date=d(4), raised=d(-1))],
              meeting={"key": "calendar:e5", "title": "ABC Design review", "date": d(-1), "projects": ["ABC"],
                       "draft": "system/staging/drafts/Design minutes.docx", "minutes_decision": "pending",
                       "coverage": [{"point": "Design sign-off", "verdict": "Discussed"},
                                    {"point": "Budget", "verdict": "Not discussed"}],
                       "file_ops": [{"op": "copy", "from": "draft", "to": f"{ABC}/minutes/{d(-1)} ABC Design review.docx"}]})
    v.propose("gone", [], meeting={"key": "fp:gone", "title": "ABC Lost minutes", "date": d(-2), "projects": ["ABC"],
                                   "draft": "system/staging/drafts/Not there.docx", "transcript": "inbox/Recording.vtt",
                                   "minutes_decision": "pending", "file_ops": []})
    with closing(sqlite3.connect(v.root / "system/tracker.db")) as con:
        ids = {r[0]: r[1] for r in con.execute("SELECT description, id FROM actions")}
        dec = con.execute("SELECT id, updated_at FROM decisions").fetchone()
    items = [
        new("actions", 1, project="ABC", description="Book the UAT environment for the client", owner="Sara Example",
            due_date=d(6), priority="High", client_visible=1, client_message="We are booking UAT", workstream="Build"),
        new("raid", 2, project="ABC", type="Issue", description="Masked data incomplete", owner="Omar Haddad",
            impact="High", likelihood="Medium", response_action="Ask the client", due_date=d(8)),
        new("decisions", 3, project="ABC", decision="Use vendor A", made_by="Jane Doe", date=d(-1), reasoning="Cheaper",
            options="A or B", revisit=d(60)),
        new("decisions", 4, project="ABC", decision="Agree the cut-over weekend", status="Pending", needed_by=d(9)),
        {"n": 5, "op": "update", "table": "actions", "id": ids["Book UAT environment"], "changes": {"owner": "Omar Haddad"},
         "decision": "pending", "match": "strong", "flags": ["conflict"], "source": SRC},
        {"n": 6, "op": "update", "table": "actions", "id": ids["Escalate data access to the client CIO"],
         "changes": {"status": "Delayed", "latest_update": "CIO away"}, "why": "the CIO is away", "decision": "pending",
         "match": "strong", "flags": [], "source": SRC},
        {"n": 7, "op": "update", "table": "projects", "id": "ABC", "changes": {"health": "At risk", "health_reason": "UAT"},
         "decision": "pending", "match": "strong", "flags": []},
        {"n": 8, "op": "update", "table": "milestones", "id": "ABC-M-001", "changes": {"forecast_date": d(31)},
         "decision": "pending", "match": "strong", "flags": []},
        {"n": 9, "op": "update", "table": "decisions", "id": dec[0], "changes": {"client_message": "We moved go-live"},
         "based_on": dec[1], "decision": "pending", "match": "strong", "flags": []},
        {**new("actions", 10, description="Find a venue", raised=d(0)), "match": "unresolved"},
        {**new("actions", 11, project="DEF", description="Confirm the pilot users", owner="TBC", raised=d(0)),
         "flags": ["no-owner", "no-due-date"]},
        {**new("actions", 12, project="ABC", description="Print the plan", owner="Alan Carter", raised=d(0)),
         "flags": ["date-from-file"]},
        {**new("raid", 13, project="ABC", type="Risk", description="Vendor capacity", workstream="Vendors", raised=d(0)),
         "flags": ["new-workstream"], "ws_suggest": {"name": "Vendors", "keywords": ["vendor"]}},
        {**new("actions", 14, project="DEF", description="Send the pilot pack", owner="Omar Ali", raised=d(0)),
         "match": "possible", "signals": [{"kind": "domain", "value": "def.example"}, {"kind": "sender", "value": ""}]},
        {**new("actions", 15, project="ABC", description="Draft the test plan", owner="Omar Haddad", raised=d(0)),
         "inferred": {"owner": "Omar said he would"}, "moved_from": "proposed-pending.json"},
        new("actions", 16, project="ABC", description="Escalate data access to the client CIO now", owner="Alan Carter",
            raised=d(0)),
        {**new("actions", 17, project="ABC", description="Already decided", raised=d(0)), "decision": "approved"},
        {**new("actions", 18, project="ABC", description="Already applied", raised=d(0)), "applied": True},
    ]
    v.propose("mixed", items)


def hub_world(v):
    """The calendar, transcripts, a prep page, applied minutes, a quick note, processed.txt and a carried point."""
    cal = {"saved": f"{FIXED} 07:00", "days": {
        FIXED.isoformat(): [
            {"id": "e1", "start": "09:00", "end": "10:00", "title": "ABC weekly", "where": "Teams", "teams": True, "organiser": True},
            {"id": "e4", "start": "11:00", "end": "12:00", "title": "DEF pilot check-in", "where": "Room 2", "teams": False},
            {"id": "e6", "start": "15:00", "end": "16:00", "title": "ABC Steering committee", "where": "Teams", "teams": True},
            {"id": "e7", "start": "13:00", "end": "14:00", "title": "Doctor", "private": True},
            {"id": "e8", "start": "", "end": "", "title": "Holiday", "all_day": True}],
        d(-1): [{"id": "e5", "start": "10:00", "end": "11:00", "title": "ABC Design review", "where": "Teams", "teams": True},
                {"id": "e2", "start": "14:00", "end": "15:00", "title": "ABC Vendor sync", "where": "Teams", "teams": True}],
        d(-2): [{"id": "e3", "start": "09:00", "end": "09:30", "title": "DEF stand-up", "where": "Teams", "teams": True},
                {"id": "e9", "start": "16:00", "end": "17:00", "title": "ABC Data call", "where": "Teams", "teams": True}],
        d(-3): [{"id": "e10", "start": "10:00", "end": "11:00", "title": "ABC Kick-off", "where": "Teams", "teams": True}]}}
    (v.root / "system/staging/calendar.json").write_text(json.dumps(cal), encoding="utf-8")
    (v.root / "system/staging/transcripts.json").write_text(json.dumps({"checked": {
        "e2": {"status": "not_transcribed"}, "e3": {"status": "available"}, "e9": {"status": "no_access"}}}), encoding="utf-8")
    page = v.root / ABC / "agendas" / f"{FIXED} Prep - ABC weekly.html"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text("<p>prep</p>", encoding="utf-8")
    (v.root / "system/staging/prep-pages.json").write_text(json.dumps({f"{ABC}/agendas/{FIXED} Prep - ABC weekly.html": {
        "sha": "x", "key": "09:00|ABC weekly", "day": FIXED.isoformat(), "at": f"{FIXED} 08:00"}}), encoding="utf-8")
    make_draft(v.root / "system/staging/drafts/Kick-off minutes.docx")
    with closing(sqlite3.connect(v.root / "system/tracker.db")) as con:
        risk = con.execute("SELECT id FROM raid WHERE description LIKE 'Data access%'").fetchone()[0]
    v.propose("kickoff", [action(1, description="Send the kick-off pack", owner="Sara Example (Example Co)", raised=d(-3),
                                 due_date=d(2), source=SRC),
                          action(2, description="Book the next kick-off", owner="Alan Carter", raised=d(-3), due_date=d(20),
                                 source=SRC),
                          {**new("actions", 3, project="ABC", description="Order pizza", raised=d(-3)), "decision": "rejected"},
                          {"n": 4, "op": "update", "table": "raid", "id": risk, "changes": {"impact": "Medium"},
                           "decision": "approved", "match": "strong", "flags": [], "source": SRC}],
              meeting={"key": "calendar:e10", "title": "ABC Kick-off", "date": d(-3), "projects": ["ABC"],
                       "draft": "system/staging/drafts/Kick-off minutes.docx", "minutes_decision": "approved",
                       "file_ops": [{"op": "copy", "from": "draft", "to": f"{ABC}/minutes/{d(-3)} ABC Kick-off.docx"},
                                    {"op": "remove", "path": "system/staging/drafts/Kick-off minutes.docx"}]})
    v.run("apply")
    # tracker.py dates the processed.txt line it just wrote with the real day; the fixed world applied it on FIXED
    proc = v.root / "system/processed.txt"
    proc.write_text(proc.read_text(encoding="utf-8").replace(f"{date.today()} | calendar:e10 |", f"{FIXED} | calendar:e10 |"),
                    encoding="utf-8")
    note = f"{ABC}/minutes/{d(-1)} Quick note - catch-up.md"
    (v.root / note).write_text("# Quick note\n", encoding="utf-8")
    v.propose("note", [new("actions", 1, project="ABC", description="Send the note", owner="Sara Example", raised=d(-1))],
              meeting={"key": "fp:quick note - catch-up", "title": "Quick note - catch-up", "date": d(-1), "projects": ["ABC"],
                       "note": note, "kind": "quick note", "minutes_decision": "approved", "file_ops": []})
    with open(v.root / "system/processed.txt", "a", encoding="utf-8") as f:
        f.write(f"{d(-6)} | fp:older | {ABC}/minutes/{d(-6)} ABC Older sync.docx; {ABC}/transcripts/{d(-6)} ABC Older sync.vtt | 2\n")
        f.write(f"{d(-4)} | fp:quick note - stand-in | not filed | 0\n")
        f.write(f"{d(-90)} | fp:ancient | {ABC}/minutes/{d(-90)} Ancient.docx | 1\n")
    (v.root / "system/staging/carried.json").write_text(json.dumps({"points": [
        {"key": "calendar:e5", "point": "Budget", "series": "abc design review", "day": d(-1)}]}), encoding="utf-8")


HARNESS = r'''
import json, sys
from datetime import datetime
sys.path.insert(0, "system/scripts")
import build_dashboard as B
data = B.collect(B.clock())
print(json.dumps({k: data[k] for k in ("review", "hub", "flow")}, indent=1, sort_keys=True, ensure_ascii=False))
'''


class Pinned(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        test_dashboard.populate(cls.v)
        history(cls.v)
        hub_world(cls.v)
        review_world(cls.v)

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def test_review_hub_and_flow(self):
        r = subprocess.run([sys.executable, "-c", HARNESS], cwd=self.v.root, capture_output=True, text=True, timeout=300,
                           env={**os.environ, "CREAITE_NOW": NOW, "TZ": "UTC"})
        self.assertEqual(r.returncode, 0, r.stderr[-3000:])
        text = r.stdout.replace(str(self.v.root.resolve()), "<VAULT>").replace(str(self.v.root), "<VAULT>")
        text = re.sub(r'"age": -?\d+', '"age": "<AGE>"', text)
        text = re.sub(r'"stale": (true|false)', '"stale": "<STALE>"', text)
        if RECORD:
            PINNED.write_text(text, encoding="utf-8")
        self.assertEqual(text, PINNED.read_text(encoding="utf-8"), "review_queue, meeting_hub or flow_data changed")


if __name__ == "__main__":
    unittest.main()
