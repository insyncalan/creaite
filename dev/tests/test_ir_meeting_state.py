"""#325/#323: a meeting's state is defined once (src/core/irFold.js irMeetingState), run under Node. The chip, the stage boxes'
counts and the Group by / filter all read it, so they agree: waiting for the transcript, transcript ready, suggestions to check, done."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

FOLD = Path(__file__).resolve().parents[2] / "system/templates/dashboard/src/core/irFold.js"
G = lambda needs, routine: {"needs": needs, "routine": routine}  # noqa: E731
MODEL = {"meetings": [
    {"id": "a", "stage": "arrived", "state": "waiting", "groups": G([], [])},
    {"id": "b", "stage": "arrived", "state": "ready", "groups": G([], [])},
    {"id": "c", "stage": "drafted", "state": "proposals", "groups": G([1], [2])},
    {"id": "d", "stage": "drafted", "state": "proposals", "groups": G([], [3])},
    {"id": "e", "stage": "approved", "state": "done", "groups": G([], [])}],
    "mail": G([], []), "other": G([], []), "later": [], "not_needed": [], "counts": {}}
SCRIPT = """
const f = await import(%s); const M = %s; const d = s => n => s.includes(n);
const out = {};
out.states = M.meetings.map(m => f.irStateOf(m, () => false));
out.afterDecided = M.meetings.map(m => f.irStateOf(m, d([3])));
out.counts = f.irCounts(M, () => false); out.countsAfter = f.irCounts(M, d([3]));
const byState = {}; for (const m of M.meetings) { const s = f.irStateOf(m, d([3])); byState[s] = (byState[s] || 0) + 1; }
out.byState = byState; out.sc = f.irStateCounts(M, d([3])); out.chip = f.IR_STATE_CHIP;
console.log(JSON.stringify(out));
"""


@unittest.skipUnless(shutil.which("node"), "needs Node")
class MeetingStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        r = subprocess.run(["node", "--input-type=module", "-e", SCRIPT % (json.dumps(FOLD.as_uri()), json.dumps(MODEL))], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        cls.o = json.loads(r.stdout)

    def test_each_meeting_has_exactly_one_state(self):
        self.assertEqual(self.o["states"], ["waiting", "ready", "check", "check", "done"])

    def test_a_meeting_with_every_suggestion_decided_is_done(self):
        self.assertEqual(self.o["afterDecided"], ["waiting", "ready", "check", "done", "done"])

    def test_stage_boxes_agree_with_the_states(self):
        c, a = self.o["counts"], self.o["countsAfter"]
        self.assertEqual((c["arrived"], c["drafted"], c["approved"]), (2, 2, 1))
        self.assertEqual((a["arrived"], a["drafted"], a["approved"]), (2, 1, 2))
        by = self.o["byState"]
        self.assertEqual(self.o["sc"], {"waiting": 1, "ready": 1, "check": 1, "done": 2})
        self.assertEqual(by["waiting"] + by.get("ready", 0), a["arrived"])
        self.assertEqual(by["check"], a["drafted"])
        self.assertEqual(by["done"], a["approved"])

    def test_the_chip_words(self):
        self.assertEqual(self.o["chip"], {"waiting": "Waiting for the transcript", "check": "Suggestions to check", "done": "Done"})


if __name__ == "__main__":
    unittest.main()
