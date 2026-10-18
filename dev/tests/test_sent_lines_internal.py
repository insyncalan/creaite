"""#153 (Alan, 17-10-2026): the dated lines "I sent it" writes (Chased / Emailed / Asked <name> by email or message) are INTERNAL.

They sit in an item's Latest update (action), Response (risk) or Reasoning (decision). No client path may carry them: the client wording
context (report.client_item_context), the client report's facts (report_doc.client_facts) and the client text check
(client_leak.text_findings, which the client sheet's reply check uses) all leave them out. The rest of the field is kept.

Run: python3 dev/tests/test_sent_lines_internal.py     (quick tier: no Chrome, no model)
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import Vault  # noqa: E402

SRC = "projects/ABC Example Programme/minutes/2026-10-01 Steering.docx — Actions"
CHASE = "17-10-2026: Chased Sara Example by email (reminder 1); reply asked for by 19-10-2026."
EMAILED = "17-10-2026: Emailed Tom Reid by message asking for an update."
ASKED = "17-10-2026: Asked Chris Dunn for a decision by email; reply asked for by 20-10-2026."
SHORT = "17-10-2026: Chased Sara Example by email."


def new(n, table, **values):
    return {"n": n, "op": "new", "table": table, "values": values, "match": "strong", "flags": [], "decision": "approved"}


class SentLinesAreInternal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = v = Vault()
        v.run("init")
        v.propose("setup", [
            new(1, "actions", project="ABC", description="Share the Northgate UAT plan", owner="Tom Reid", due_date="2026-10-17",
                raised="2026-10-01", source=SRC, client_visible=1, latest_update=CHASE + "\nWaiting on the vendor",
                client_message="What it is: the UAT plan\nWhat it means for you: testing can start\nWhat is being done: it is being shared"),
            new(2, "raid", project="ABC", type="Risk", description="Test environment is not ready", owner="Tom Reid", impact="High",
                likelihood="Medium", response_action=EMAILED + "\nAgree dates with the supplier", raised="2026-10-01", source=SRC),
            new(3, "decisions", project="ABC", decision="Which four use cases go into Phase 2", made_by="Chris Dunn", status="Pending",
                needed_by="2026-10-23", reasoning=ASKED + "\nThe budget fits four", source=SRC),
            new(4, "actions", project="ABC", description="Only a log line here", owner="Tom Reid", raised="2026-10-01", source=SRC,
                latest_update=SHORT),
        ])
        v.run("apply")

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def py(self, code):
        r = subprocess.run([sys.executable, "-c", "import sys, json, sqlite3\nsys.path.insert(0, 'system/scripts')\n" + code],
                           cwd=self.v.root, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def context(self, n):
        return self.py(f"""import report, tracker
con = sqlite3.connect('system/tracker.db'); con.row_factory = sqlite3.Row
ids = {{r[0]: r[1] for r in con.execute("SELECT id, description FROM actions UNION ALL SELECT id, description FROM raid UNION ALL SELECT id, decision FROM decisions")}}
item = sorted(ids)[{n}]
print(json.dumps(report.client_item_context(con, item)))""")

    def test_the_client_wording_context_leaves_the_sent_lines_out_and_keeps_the_rest(self):
        texts = {c["id"]: c["text"] for c in (self.context(i) for i in range(4))}
        self.assertEqual(len(texts), 4)
        blob = "\n".join(texts.values())
        for bit in ("Chased", "Emailed", "Asked Chris", "by email", "by message", "reply asked for", "reminder"):
            self.assertNotIn(bit, blob, bit)
        self.assertIn("Waiting on the vendor", blob)
        self.assertIn("Agree dates with the supplier", blob)
        self.assertIn("The budget fits four", blob)
        only = next(t for t in texts.values() if t.startswith("Only a log line here"))
        self.assertEqual(only.strip(), "Only a log line here")                                   # the short form goes too

    def test_the_client_check_flags_a_sent_line_in_a_client_text(self):
        for line in (CHASE, EMAILED, ASKED, SHORT):
            found = self.py(f"""import client_leak
con = sqlite3.connect('system/tracker.db'); con.row_factory = sqlite3.Row
print(json.dumps(client_leak.text_findings(con, 'ABC', {line!r})))""")
            self.assertTrue([f for f in found if "chase" in f.lower() or "sent" in f.lower()], (line, found))

    def test_the_client_facts_never_read_the_update_field(self):
        facts = self.py("""import report_doc
print(json.dumps(report_doc.client_facts('ABC'), default=str))""")
        self.assertNotIn("Chased", json.dumps(facts))
        self.assertNotIn("Waiting on the vendor", json.dumps(facts))


if __name__ == "__main__":
    unittest.main()
