"""#232-B (release 2.6): the update proposal in the peek, the data and the pure rules; no browser.

B1  The row model: an update row carries the table of its target and, per change, the database column and the item's own text.
B2  core/irUpdate.js (run under Node): the one list of changes, as against the live row, that feeds the chips, the note and the
    "If approved" line; the line's words (B4); what a save writes (B3).
B3  The apply path: what a proposal edited in the peek carries, applied by tracker.py.

Run: python3 dev/tests/test_intake_review_update.py"""
import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_dashboard  # noqa: E402
from test_tracker import ABC, Vault, action  # noqa: E402

IRU = Path(__file__).resolve().parents[2] / "system/templates/dashboard/src/core/irUpdate.js"
SRC = f"{ABC}/minutes/2026-10-05 Steering.docx — Actions"

HARNESS = r'''
import json, sys
sys.path.insert(0, "system/scripts")
import build_dashboard as B
data = B.collect(B.clock())
print(json.dumps([r for r in data["review"] if r["kind"] == "update"], sort_keys=True))
'''


def update(n, table, item_id, changes, **k):
    return {"n": n, "op": "update", "table": table, "id": item_id, "changes": changes, "decision": "pending", "match": "strong",
            "flags": [], "source": SRC, **k}


class RowModel(unittest.TestCase):
    """B1: update_record adds `table`, the item's text and each change's database column."""

    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        test_dashboard.populate(cls.v)
        import sqlite3
        from contextlib import closing
        with closing(sqlite3.connect(cls.v.root / "system/tracker.db")) as con:
            cls.aid = con.execute("SELECT id FROM actions WHERE description = 'Book UAT environment'").fetchone()[0]
            cls.rid = con.execute("SELECT id FROM raid LIMIT 1").fetchone()[0]
        cls.v.propose("ups", [
            update(1, "actions", cls.aid, {"due_date": "2026-12-01", "latest_update": "Supplier confirmed"}, why="the supplier confirmed"),
            update(2, "raid", cls.rid, {"status": "Closed"}),
            update(3, "projects", "ABC", {"health": "At risk", "health_reason": "UAT"})])
        r = subprocess.run([sys.executable, "-c", HARNESS], cwd=cls.v.root, capture_output=True, text=True, timeout=300,
                           env={**os.environ, "CREAITE_NOW": "2026-10-09 11:30", "TZ": "UTC"})
        assert r.returncode == 0, r.stderr[-2000:]
        cls.rows = {x["rec"]["target"]: x["rec"] for x in json.loads(r.stdout.strip().splitlines()[-1])}

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def test_the_table_of_the_target_comes_from_the_server(self):
        self.assertEqual(self.rows[self.aid]["table"], "actions")
        self.assertEqual(self.rows[self.rid]["table"], "raid")
        self.assertEqual(self.rows["ABC"]["table"], "projects")

    def test_each_change_names_its_database_column(self):
        ch = self.rows[self.aid]["changes"]
        self.assertEqual([c["col"] for c in ch], ["due_date", "latest_update"])
        self.assertEqual([c["field"] for c in ch], ["due date", "latest update"])       # the words are unchanged
        self.assertEqual(self.rows[self.rid]["changes"][0]["col"], "status")
        self.assertEqual(self.rows["ABC"]["changes"][1]["col"], "health_reason")

    def test_the_items_own_text_is_there_for_the_line(self):
        self.assertEqual(self.rows[self.aid]["title"], "Book UAT environment")
        self.assertEqual(self.rows["ABC"]["title"], "Example Programme")


SERVER = Path(__file__).resolve().parents[2] / "system/templates/dashboard/src/core/server.js"

SCRIPT = """
const f = await import(%s); const out = {};
const live = {status: "Open", due_date: "2026-10-20", owner: "Sara Example", latest_update: "Waiting on the supplier.", client_visible: 0};
const changes = {due_date: "2026-10-23", latest_update: "The supplier confirmed a slot for 23 October."};
const now = f.irNowRow("actions", live, changes, {});
out.list = f.irUpdateList(live, now, Object.keys(changes));
out.changed = f.irChanged(out.list).map(c => c.col);
out.note = f.irNoteText("ABC-A-002", "Book UAT environment", f.irChanged(out.list));
out.if = f.irIfApproved(f.irChanged(out.list));
out.line = [f.irVerb([{col: "due_date", to: "x"}]), f.irLineHead("Updates", "ABC-A-002", "Book UAT environment"), ...f.irLineParts(out.list)];
// a stale `from` in the proposal makes no difference: only the live row counts
const same = f.irUpdateList(live, f.irNowRow("actions", live, {status: "Open", due_date: "2026-10-23"}, {}), ["status", "due_date"]);
out.same = same.map(c => [c.col, c.same]);
out.sameNote = f.irNoteText("ABC-A-002", "Book UAT environment", f.irChanged(same));
out.none = f.irNoteText("ABC-A-002", "Book UAT environment", f.irChanged(f.irUpdateList(live, live, [])));
// the closing line
const close = [{col: "status", from: "Open", to: "Closed"}];
out.close = [f.irVerb(close), f.irLineHead(f.irVerb(close), "ABC-A-014", "Draft the comms plan"), ...f.irLineParts(close)];
out.cancel = f.irVerb([{col: "status", from: "Open", to: "Cancelled"}]);
out.only = f.irLineParts([{col: "latest_update", from: "a", to: "b"}]);
out.three = f.irLineParts([{col: "status", from: "Open", to: "Delayed"}, {col: "due_date", from: "2026-10-01", to: "2026-10-09"}, {col: "latest_update", from: "", to: "x"}]);
// the client message text is never shown
out.cm = [f.irPhrase({col: "client_message", was: "secret", now: "secret two"}), f.irIfApproved([{col: "client_message", label: "Client messaging", was: "secret", now: "x"}])];
out.words = [f.irWord("due_date", "2026-10-23"), f.irWord("due_date", null), f.irWord("client_visible", 1), f.irWord("client_visible", 0), f.irWord("owner", "")];
// the save
const opened = {status: "Open", due_date: "2026-10-23", latest_update: changes.latest_update};
const save = (draft, ch = changes) => f.irSaveChanges("actions", ch, live, opened, draft);
out.untouched = save({status: "Open", due_date: "2026-10-23", latest_update: changes.latest_update});
out.dueEdited = save({status: "Open", due_date: "2026-10-27", latest_update: changes.latest_update});
out.dueBack = save({status: "Open", due_date: "2026-10-20", latest_update: changes.latest_update});
out.statusAdded = save({status: "Closed", due_date: "2026-10-23", latest_update: changes.latest_update});
out.updEmpty = save({status: "Open", due_date: "2026-10-23", latest_update: ""});
out.badDate = save({status: "Open", due_date: "27-10-2026", latest_update: changes.latest_update});
out.badStatus = save({status: "Made", due_date: "2026-10-23", latest_update: changes.latest_update});
out.nothing = f.irSaveChanges("actions", {due_date: "2026-10-23"}, live, {due_date: "2026-10-23"}, {due_date: "2026-10-20"});
out.owner = f.irSaveChanges("actions", {owner: "Omar Ali"}, live, {status: "Open"}, {status: "Open", owner: "Someone Else"});
out.raid = f.irSaveChanges("raid", {status: "Closed", impact: "Low"}, {status: "Open", impact: "High"}, {status: "Closed"}, {status: "Closed", impact: "High"});
out.raidUpd = f.irSaveChanges("raid", {status: "Closed"}, {status: "Open"}, {status: "Closed"}, {status: "Closed", latest_update: "x"});
out.raidDue = f.irSaveChanges("raid", {status: "Closed"}, {status: "Open", due_date: null}, {status: "Closed", due_date: null}, {status: "Closed", due_date: "2026-11-02"});
out.dec = f.irSaveChanges("decisions", {client_message: "x"}, {status: "Pending", date: null}, {status: "Pending"}, {status: "Made", date: "2026-10-12"});
out.decNoDate = f.irSaveChanges("decisions", {client_message: "x"}, {status: "Pending", date: null}, {status: "Pending"}, {status: "Made", date: ""});
out.ui = f.UI; out.editable = f.EDITABLE;
console.log(JSON.stringify(out));
"""


def node_run(script):
    r = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


@unittest.skipUnless(shutil.which("node"), "needs Node")
class PureRules(unittest.TestCase):
    """B2 and B4: core/irUpdate.js."""

    @classmethod
    def setUpClass(cls):
        cls.o = node_run(SCRIPT % json.dumps(IRU.as_uri()))

    def test_changed_is_against_the_live_row(self):
        o = self.o
        self.assertEqual(o["changed"], ["due_date", "latest_update"])
        self.assertEqual([c["was"] for c in o["list"]], ["2026-10-20", "Waiting on the supplier."])
        self.assertEqual(o["same"], [["status", True], ["due_date", False]])              # status already Open: plain, not a change
        self.assertIn("due date 20-10-2026 → 23-10-2026 and the latest update.", o["note"])
        self.assertNotIn("status", o["sameNote"])
        self.assertIn("Nothing changes", o["none"])

    def test_the_note_the_if_approved_line_and_the_row_line_come_from_the_one_list(self):
        o = self.o
        self.assertEqual(o["note"], "What changes if you approve: ABC-A-002 · Book UAT environment: due date 20-10-2026 → 23-10-2026 and the latest update. The rest of the item stays as it is.")
        self.assertEqual(o["if"], "Due date 20-10-2026 → 23-10-2026 · Latest update replaced")
        self.assertEqual(o["line"][1:], ["Updates ABC-A-002: Book UAT environment", "due 20-10-2026 → 23-10-2026 and the latest update"])

    def test_the_row_line_wording(self):
        o = self.o
        self.assertEqual(o["close"], ["Closes", "Closes ABC-A-014: Draft the comms plan", "status Open → Closed"])
        self.assertEqual(o["cancel"], "Cancels")
        self.assertEqual(o["only"], ["the latest update"])
        self.assertEqual(o["three"], ["status Open → Delayed", "due 01-10-2026 → 09-10-2026 and the latest update"])

    def test_client_message_text_is_never_shown(self):
        o = self.o
        self.assertEqual(o["cm"][0], {"label": "the client messaging", "delta": "", "text": True})
        self.assertNotIn("secret", json.dumps(o["cm"]))
        self.assertEqual(o["words"], ["23-10-2026", "—", "on", "off", "—"])

    def test_a_save_writes_only_the_columns_edited_and_leaves_the_rest(self):
        o = self.o
        self.assertEqual(o["untouched"]["changes"], {"due_date": "2026-10-23", "latest_update": "The supplier confirmed a slot for 23 October."})
        self.assertEqual(o["untouched"]["edited"], [])
        self.assertEqual(o["dueEdited"]["changes"]["due_date"], "2026-10-27")
        self.assertEqual(o["dueEdited"]["changes"]["latest_update"], "The supplier confirmed a slot for 23 October.")   # the other column unchanged
        self.assertNotIn("due_date", o["dueBack"]["changes"])                                  # back to the live value: left out
        self.assertEqual(o["statusAdded"]["changes"]["status"], "Closed")
        self.assertIsNone(o["updEmpty"]["changes"]["latest_update"])
        self.assertIn("not a date", o["badDate"]["error"])
        self.assertIn("Status must be", o["badStatus"]["error"])
        self.assertIn("Nothing would change", o["nothing"]["error"])

    def test_a_read_only_column_is_never_written_whatever_the_draft_says(self):
        o = self.o
        self.assertEqual(o["owner"]["changes"], {"owner": "Omar Ali"})                          # the draft's other owner is ignored
        self.assertEqual(o["raid"]["changes"], {"status": "Closed", "impact": "Low"})           # impact stays the proposal's
        self.assertEqual(o["raidUpd"]["changes"], {"status": "Closed"})                          # a RAID item has no latest update here
        self.assertEqual(o["raidDue"]["changes"], {"status": "Closed", "due_date": "2026-11-02"})
        self.assertEqual(o["dec"]["changes"], {"client_message": "x", "status": "Made", "date": "2026-10-12"})
        self.assertEqual(o["dec"]["edited"], ["status", "date"])
        self.assertEqual(o["decNoDate"]["changes"], {"client_message": "x", "status": "Made"})   # no date: the tracker will say so

    def test_the_editable_columns_exist_and_the_ui_keys_are_the_servers(self):
        """UI is the inverse of FIELD in core/server.js; EDITABLE names real columns of that table."""
        src = SERVER.read_text(encoding="utf-8")
        start = src.index("export const FIELD=")
        end = src.index("/** @returns", start)
        field = node_run("const FIELD=" + src[start + len("export const FIELD="):end].strip().rstrip(";").split("/*")[0].strip().rstrip(";") + ";console.log(JSON.stringify(FIELD))")
        for table, cols in field.items():
            self.assertEqual(self.o["ui"][table], {db: ui for ui, db in cols.items()}, table)
        for table, cols in self.o["editable"].items():
            self.assertTrue(set(cols) <= set(self.o["ui"][table]), table)


if __name__ == "__main__":
    unittest.main()
