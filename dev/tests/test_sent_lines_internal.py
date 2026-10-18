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
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
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

    def test_every_shape_is_recognised_and_stripped(self):
        import linktext
        shapes = {
            "lower case": CHASE.replace("Chased", "chased"), "no-break space": "17-10-2026:\u00a0Chased Sara Example by email (reminder 1).",
            "bullet": "- " + CHASE, "star bullet": "* " + EMAILED, "iso date": "2026-10-17: Chased Sara Example by email (reminder 1).",
            "zero-width": "17-10-2026:\u200b Chased Sara Example by email (reminder 1).",
        }
        for name, line in shapes.items():
            self.assertTrue(linktext.sent_has(line), name)
            self.assertEqual(linktext.sent_strip("Waiting on the vendor\n" + line), "Waiting on the vendor", name)
        self.assertEqual(linktext.sent_strip("Waiting. " + CHASE), "Waiting.")                    # run into a sentence
        self.assertEqual(linktext.sent_strip("<p>Waiting</p><p>" + CHASE + "</p>"), "Waiting")    # HTML
        self.assertEqual(linktext.sent_strip("Waiting\r\n" + CHASE + "\r\nNext"), "Waiting\nNext")   # CRLF leaves no blank line
        self.assertEqual(linktext.sent_strip("a\n\nb"), "a\n\nb")

    def test_ordinary_text_is_not_a_sent_line(self):
        import linktext
        for t in ("We chased the supplier last week", "We chased the supplier last week by email.", "Chased Sara by email yesterday",
                  "17-10-2026: Supplier answered by email", "Asked for a decision by email", "17-10-2026 Chased Sara by email"):
            self.assertFalse(linktext.sent_has(t), t)
            self.assertEqual(linktext.sent_strip(t), t)

    def test_the_client_check_flags_every_shape(self):
        for line in ("- " + CHASE, CHASE.replace("Chased", "chased"), "Waiting. " + CHASE, "<p>" + CHASE + "</p>",
                     "2026-10-17: Chased Sara Example by email (reminder 1).", "17-10-2026:\u00a0Chased Sara by email.", "a\r\n" + CHASE):
            found = self.py(f"""import client_leak
con = sqlite3.connect('system/tracker.db'); con.row_factory = sqlite3.Row
print(json.dumps(client_leak.text_findings(con, 'ABC', {line!r})))""")
            self.assertTrue([f for f in found if "chase" in f.lower()], (line, found))

    def test_a_chase_pane_never_carries_the_log_to_the_recipient(self):
        f = self.py("""import drafts
ids = [r[0] for r in sqlite3.connect('system/tracker.db').execute("SELECT id FROM actions WHERE description LIKE 'Share the Northgate%'")]
print(json.dumps(drafts.chase_facts(ids[0])))""")
        self.assertNotIn("Chased", json.dumps(f))
        self.assertIn("Waiting on the vendor", f["update"])
        d = self.py("""import drafts
con = sqlite3.connect('system/tracker.db')
ids = [r[0] for r in con.execute("SELECT id FROM decisions")]
print(json.dumps(drafts.chase_facts(ids[0])))""")
        self.assertNotIn("Asked", json.dumps(d))
        r = self.py("""import drafts
con = sqlite3.connect('system/tracker.db')
ids = [r[0] for r in con.execute("SELECT id FROM raid")]
print(json.dumps(drafts.chase_facts(ids[0])))""")
        self.assertNotIn("Emailed", r["response"])
        self.assertIn("Agree dates with the supplier", r["response"])
        rec = self.py("""import sqlite3
con = sqlite3.connect('system/tracker.db'); print(json.dumps([r[0] for r in con.execute("SELECT response_action FROM raid")]))""")
        self.assertIn("Emailed Tom", rec[0])                                                       # the tracker keeps it

    def sheet(self, audience):
        return self.py(f"""import status_facts, report
print(json.dumps(status_facts.facts('ABC', '2026-10-01', '2026-10-18', {audience!r})['text']))""")

    def test_steering_and_sponsor_sheets_leave_the_log_out_and_internal_keeps_it(self):
        for aud in ("steering", "sponsor"):
            t = self.sheet(aud)
            self.assertNotIn("Emailed Tom", t, aud)
            self.assertIn("Agree dates with the supplier", t, aud)
        self.assertIn("Emailed Tom", self.sheet("internal"))
        ctx = self.py("""import report
print(json.dumps(report.current_context('ABC', '2026-10-01', '2026-10-18', audience='steering')))""")
        self.assertNotIn("Emailed Tom", ctx)


if __name__ == "__main__":
    unittest.main()
