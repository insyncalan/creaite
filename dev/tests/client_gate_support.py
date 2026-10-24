"""#127: the client gate on every client path (Team Stark's review of #123). The data is fictional.

Shared fixture and helpers for test_client_gate.py, test_client_gate_reviews.py and test_client_gate_late.py (split by class so
each file stays well under the file timeout). Not a test file.
1. The ✦ on a report section takes its audience from the report the request names (edit_ai.document_audience, as /api/edit/ai's
   place), never from the page's claim; no report named is refused.
2. A Word client report and the client-safe steerco one-pager get the whole gate at approval (client_leak.plain_findings: items
   by ID, wording, the internal health reason or a marker, names), and so does an approval from Excel; cx-document refuses a client
   audience.
3. client_leak.text_findings finds an ID however it is written, and milestones, promises and another project's items too.
4. A people register that is missing or can't be read fails closed, with a plain message.
Each marker is checked both ways: missing from client output, present where the internal path should have it.
"""
import json
import os
import sqlite3
import subprocess
import sys
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_reports as R  # noqa: E402  (its fixture: populate, ReportVault, NOW, new, edit_docx)
import vault_clone  # noqa: E402

HEAD = "import sys, json; sys.path.insert(0, 'system/scripts')\nimport client_leak, creaite_doc, drafts, edit_ai, report_doc\n"
INTERNAL_ID, MIXED_ID, MILESTONE_ID, PROMISE_ID, OTHER_ID = "ABC-A-004", "abc-a-004", "ABC-M-001", "ABC-P-001", "DEF-A-001"
PERSON = "Quentin Marlow"                                    # owns only an open internal action
REASON = "ZEBRAINTERNAL vendor is failing to deliver the build on time"
DOC = {"kind": "client", "code": "ABC", "week_ending": "2026-10-09", "client": ""}
WEEKLY_DOC = {"kind": "weekly", "code": "ABC", "week_ending": "2026-10-09"}
SECTION = {"kind": "report-section", "code": "ABC", "section": "summary", "heading": "Summary", "action": "polish",
           "text": "Phase two can start once the paperwork is signed."}


class Base(unittest.TestCase):
    """The seeded vault is built once per class (setUpClass) and each test works on its own clone of it (vault_clone: copy-on-write
    where the file system has it), so a test still changes only its own vault. Set CREAITE_NO_CLONE=1 to build one per test as before."""
    template = None

    @classmethod
    def build(cls):
        """One fully seeded vault (what every test's setUp used to make)."""
        v = R.ReportVault()
        R.populate(v)
        v.propose("def", [{"n": 1, "op": "new", "table": "projects", "match": "strong", "flags": [], "decision": "approved",
                           "values": {"code": "DEF", "name": "Other Programme"}}])
        v.run("apply")
        v.propose("seed127", [
            R.new("actions", 1, project="DEF", description="Migrate the other ledger", owner="Jane Doe (Example Client Ltd)",
                  raised="2026-10-01", client_visible=1, client_message=R.CLIENT_MSG, source="s"),      # client-visible, but DEF's
            R.new("actions", 2, project="ABC", description="Line up the quiet audit", owner=PERSON, raised="2026-10-01",
                  source="s")])
        v.run("apply")
        with closing(sqlite3.connect(v.root / "system/tracker.db")) as con:   # a test vault: set directly
            con.execute("INSERT INTO promises (id, project, promised_by, promised_to, description, raised, source) "
                        "VALUES (?, 'ABC', 'Alan Carter', 'Jane Doe', 'Send the pricing sheet', '2026-10-01', 's')", (PROMISE_ID,))
            con.execute("UPDATE projects SET health = 'Off track', health_reason = ? WHERE code = 'ABC'", (REASON,))
            con.commit()
            ids = {r[0] for r in con.execute("SELECT id FROM actions WHERE project = 'DEF'")}
        assert ids == {OTHER_ID}, ids
        return v

    @classmethod
    def setUpClass(cls):
        cls.template = None if os.environ.get("CREAITE_NO_CLONE") else cls.build()

    @classmethod
    def tearDownClass(cls):
        if cls.template is not None:
            cls.template.cleanup()
            cls.template = None

    def setUp(self):
        if self.template is None:
            self.v = self.build()
            return
        self.v = R.ReportVault.__new__(R.ReportVault)           # a Vault around the clone's folder (its __init__ would make a new vault)
        self.v.root = vault_clone.clone(self.template.root)

    def tearDown(self):
        self.v.cleanup()

    def py(self, code):
        r = subprocess.run([sys.executable, "-c", HEAD + code], cwd=self.v.root, env={**os.environ, "CREAITE_NOW": R.NOW},
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def findings(self, summary, kind="client"):
        make = "report_doc.client_doc('ABC')" if kind == "client" else "report_doc.weekly_doc('ABC')"
        return self.py(f"d = {make}\nnext(s for s in d['sections'] if s['id'] == 'summary')['text'] = {summary!r}\n"
                       "print(json.dumps(client_leak.findings(d)))")

    def ctx(self, req):
        return self.py(f"print(json.dumps(drafts.context({req!r}), ensure_ascii=False))")

    def assert_linear(self, out, again=None):
        """Each {name: [seconds at size n, seconds at 4n]} grows linearly (#127 round 6: growth, not wall-clock seconds, so a loaded
        machine doesn't fail it): 4n takes under 8 times n (linear is about 4, quadratic 16) or under a second, and under 30 s.
        again (2.5.3 gate): when a run looks too slow, measure once more and keep each size's fastest time, so one stall on a
        loaded runner doesn't fail it; the bound is the same, and real quadratic growth (16 times) fails both runs."""
        slow = [n for n, (small, large) in out.items() if large >= max(8 * small, 1.0) or large >= 30.0]
        if slow and again is not None:
            more = again()
            out = {n: [min(a, b) for a, b in zip(v, more[n])] for n, v in out.items()}
        for name, (small, large) in out.items():
            self.assertLess(large, 30.0, name)
            self.assertLess(large, max(8 * small, 1.0), (name, small, large))


# The timing tests' prelude: took(run) is the best of two runs, so one slow moment under load doesn't count.
TIMER = ("import time\ndef took(run):\n    best = None\n    for _ in range(2):\n        t0 = time.perf_counter(); run()\n"
         "        best = min(best, time.perf_counter() - t0) if best is not None else time.perf_counter() - t0\n    return best\n")
TOO_LONG = "a link address too long to check"        # the gate's plain finding for an address it cannot read (test_client_gate_reviews and _late)
