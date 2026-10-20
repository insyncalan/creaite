"""BL-133 stage A: Review triage and mass change, in a real browser against the real live server (reduced by #232 C2: see the class).

Run: python3 dev/tests/test_review_triage.py   (needs Google Chrome; skipped otherwise)

The vault holds test_dashboard.populate's portfolio plus a mixed queue: three files of routine actions (four each), items that need a
project, a new risk, a new decision, a closing update, a conflict, and items from mail, Teams and the dashboard, some of them stale.
"""
import json
import os
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_tracker import action  # noqa: E402

MAIL = "Email · From: Priya Nair <priya.nair@client.example> · Subject: Data residency · Sent: 2026-10-08 09:00 · Link: https://outlook.office365.com/owa/?ItemID=x"
TEAMS = "Teams · Chat: Omar"


def pending(item):
    item = dict(item)
    item["decision"] = "pending"
    return item


def created(days_ago):
    fixed = os.environ.get("CREAITE_NOW")                                  # #177: days come from creaite's clock, never the real date
    now = datetime.strptime(fixed, "%Y-%m-%d %H:%M") if fixed else datetime.now()
    return (now - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:00")   # same time of day: whole days at any hour (09:00 read 0 days before 09:00)


def load_queue(v):
    for f in range(3):                                                  # twelve routine actions across three files
        items = [pending(action(i + 1, project="ABC" if (f + i) % 2 else "DEF", description=f"Batch {f} item {i}", owner="Sara Example",
                                due_date="2026-12-01", source=MAIL if f == 0 else TEAMS if f == 1 else "Dashboard (Alan), 2026-10-08"))
                 for i in range(4)]
        p = v.propose(f"2026-10-0{f + 1}-0900-batch{f}", items)
        data = json.loads(p.read_text())
        data["created"] = created(20 if f == 0 else 1)                 # the first file is stale
        p.write_text(json.dumps(data, indent=2))
    mixed = [
        pending({**action(1, description="Confirm data residency with legal", owner="Mia Hale", source=MAIL), "match": "possible"}),
        pending({**action(2, description="Send pilot invoice to finance", source=MAIL), "match": "possible"}),
        pending({"n": 3, "op": "new", "table": "raid", "match": "strong", "flags": [], "values": {"project": "ABC", "type": "Risk",
                 "description": "Scope creep from the pilot dataset", "owner": "Alan Carter", "impact": "High", "likelihood": "Medium", "source": TEAMS}}),
        pending({"n": 4, "op": "new", "table": "decisions", "match": "strong", "flags": [], "values": {"project": "ABC",
                 "decision": "Approve the revised timeline", "made_by": "Sara Example", "date": "2026-10-07", "source": TEAMS}}),
        pending({**action(5, description="A routine one with a conflict", source=TEAMS), "flags": ["conflict"]}),
        pending({"n": 6, "op": "update", "table": "actions", "id": "ABC-A-001", "match": "strong", "flags": [], "changes": {"status": "Closed"}, "source": TEAMS}),
        pending({"n": 7, "op": "update", "table": "projects", "id": "ABC", "match": "strong", "flags": [], "changes": {"health": "At risk", "health_reason": "Test"}, "source": TEAMS}),
    ]
    v.propose("2026-10-05-0900-mixed", mixed)


class Triage(LiveBrowserCase):
    """#232 C2: what is left of BL-133's triage on the one Intake page. The old Review page's select bar, select-all, shift range,
    filters, Display, preview and auto-advance went with the page (multi-select was not built, Q2); the bulk rule, one Undo and reject
    with a reason are test_intake_review_routine, _harden_b and _peek. What stays here is the fixture (`load_queue`, used by test_motion)
    and the property the bar proved first: a batch over several proposal files loses none."""
    width, height = 1500, 1100

    @classmethod
    def load(cls, v):
        populate(v)
        load_queue(v)

    def test_twelve_approvals_across_three_files_none_lost(self):
        b = self.b
        b.eval("go('intake-review')")
        b.wait("!!document.querySelector('#v-intake-review [data-irsec=other]') && !!document.querySelector('#v-intake-review [data-irsec=other]').parentElement.querySelector('tr.irprop')")
        ns = b.eval("REV.filter(r=>/^Batch /.test(r.rec.t)).map(r=>r.n)")
        self.assertEqual(len(ns), 12)
        self.assertEqual(b.eval("new Set(REV.filter(r=>/^Batch /.test(r.rec.t)).map(r=>r.file)).size"), 3)
        b.eval("document.querySelector('#v-intake-review [data-irsec=other]').parentElement.querySelector('[data-ira=routine]').click()")
        b.wait("!REV.some(r=>/^Batch /.test(r.rec.t)&&!r.done)", 30)
        for _ in range(60):
            made = [r["description"] for r in self.v.rows("actions") if r["description"].startswith("Batch ")]
            if len(made) == 12:
                break
            b.pump(0.5)
        self.assertEqual(len(made), 12, made)


if __name__ == "__main__":
    unittest.main()
