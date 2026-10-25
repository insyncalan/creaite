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
# fix5 (client-safe review): the shapes that got through the strip and the check before, each read now
SHAPES = [
    "17-10-2026: chased Sara by email.",                                   # lower case
    "17-10-2026: CHASED SARA BY EMAIL",                                    # upper case
    "17-10-2026:  Chased Sara  by  email.",                                # double spaces
    "17-10-2026:\u00a0Chased Sara by\u00a0email.",                         # no-break spaces
    "17-10-2026: Cha\u200bsed Sara by em\u200bail.",                        # zero-width spaces inside words
    "- 17-10-2026: Chased Sara by email.",                                 # a bullet
    "Waiting on vendor. 17-10-2026: Chased Sara by email.",                # run into a sentence
    "<p>17-10-2026: Chased Sara by email.</p>",                            # HTML
    "Waiting\u202817-10-2026: Chased Sara by email.\u2028Next",             # U+2028 line separators
    "17\u201110\u20112026: Chased Sara by email.",                          # non-breaking hyphens in the date
    "17-10-2026\uff1a Chased Sara by email.",                              # a full-width colon
    "17-10-2026: Chased Sara\nExample by email.",                          # a line break inside the name
]
# ordinary client prose that only uses the words: never flagged
BENIGN = [
    "We chased the supplier for the revised plan and it arrived on 17-10-2026.",
    "The steering group asked for a short update by email next week.",
    "Sara asked whether the test environment will be ready by 20-10-2026.",
    "Testing is chased daily so that the go-live date holds.",
    "Feedback was emailed to the project team on Friday.",
    "Users asked by message for clearer training material; it is being prepared.",
    "On 17-10-2026 the team chased the open defects and closed four of them.",
    "Next review: 24-10-2026. The client asked that the agenda be shared by email.",
    "The budget question was asked at the last meeting and answered by email the same day.",
    "Progress: the vendor emailed the signed contract, and nothing is outstanding.",
]


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
            new(5, "actions", project="ABC", description="Agree the room", owner="Tom Reid", raised="2026-10-01", source=SRC,
                latest_update="Room is booked. 17\u201110\u20112026\uff1a  chased TOM\u00a0Reid by email (reminder 2)."),
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
        texts = {c["id"]: c["text"] for c in (self.context(i) for i in range(5))}
        self.assertEqual(len(texts), 5)
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

    def findings(self, texts):
        return self.py(f"""import client_leak
con = sqlite3.connect('system/tracker.db'); con.row_factory = sqlite3.Row
print(json.dumps([client_leak.text_findings(con, 'ABC', t) for t in {texts!r}]))""")

    def test_fix5_the_check_reads_every_shape_of_a_sent_line(self):
        for line, found in zip(SHAPES, self.findings(SHAPES)):
            self.assertTrue([f for f in found if "chase log" in f], (line, found))

    def test_fix5_the_strip_takes_every_shape_out_and_keeps_the_rest(self):
        got = self.py(f"""import linktext
print(json.dumps([linktext.sent_strip("Keep this\\n" + t + "\\nand this") for t in {SHAPES!r}]))""")
        for line, out in zip(SHAPES, got):
            low = out.lower()
            for bit in ("chased", "sara", "by email"):
                self.assertNotIn(bit, low, (line, out))
            self.assertTrue(out.startswith("Keep this") and out.endswith("and this"), (line, out))

    def test_fix5_ordinary_prose_with_the_words_is_not_flagged(self):
        for line, found in zip(BENIGN, self.findings(BENIGN)):
            self.assertEqual(found, [], line)
        got = self.py(f"""import linktext
print(json.dumps([linktext.sent_strip(t) for t in {BENIGN!r}]))""")
        self.assertEqual(got, BENIGN)

    def test_fix5_the_client_wording_context_strips_a_run_in_lower_case_line(self):
        texts = [self.context(i)["text"] for i in range(5)]
        mixed = next(t for t in texts if t.startswith("Agree the room"))
        self.assertNotIn("chased", mixed.lower())
        self.assertIn("Room is booked.", mixed)

    def test_the_client_facts_never_read_the_update_field(self):
        facts = self.py("""import report_doc
print(json.dumps(report_doc.client_facts('ABC'), default=str))""")
        self.assertNotIn("Chased", json.dumps(facts))
        self.assertNotIn("Waiting on the vendor", json.dumps(facts))


if __name__ == "__main__":
    unittest.main()
