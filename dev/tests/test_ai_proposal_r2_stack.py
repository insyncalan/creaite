"""#132 round 2 (proposal, not applied): the diffs stack on round 1, and at the default settings no launch moves.

Run: python3 dev/tests/test_ai_proposal_r2_stack.py

Done when:
- round 2's six diffs apply, in order, on round 1 with G1c and without it;
- at the default settings every claude -p launch (G3's thirteen cases: command, cwd, the environment creaite adds and the run's
  steps) is byte for byte round 1's, except Search's answer, whose deny list only gains S1's Read rules; the launch tables are
  round 1's but for that one list.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ai_proposal_support as S  # noqa: E402
from test_ai_proposal_g3_run_model import CAPTURE, TABLES  # noqa: E402


class Stack(unittest.TestCase):
    def test_round_two_applies_with_and_without_g1c(self):
        with_g1c = S.vault2(*S.R2_ALL, r1=("g1-key-store", "g1c-never-list-held-runs", "g2-model-list", "g3-chosen-model",
                                           "g5-confidential-only-claude"))
        without = S.vault2(*S.R2_ALL)
        for root in (with_g1c, without):
            src = (root / "system" / "scripts" / "live_server.py").read_text(encoding="utf-8")
            if not S.UNPATCHED:
                self.assertIn("# ===== #132 G4 (proposal)", src)
                self.assertIn("KIND_DENIES[\"search\"] += never_read_denies()", src)

    def test_default_launches_are_round_ones(self):
        r1 = S.vault2()                                       # round 1 only (all but G1c)
        r2 = S.vault2(*S.R2_ALL)
        before, after = S.run_py(r1, CAPTURE % json.dumps({})), S.run_py(r2, CAPTURE % json.dumps({}))
        self.assertEqual(sorted(after), sorted(before))
        for name in before:
            if name == "search":
                continue
            self.assertEqual(after[name], before[name], f"{name}: the launch changed at the default settings")
        b, a = before["search"]["cmd"], after["search"]["cmd"]
        i = b.index("--disallowedTools")
        self.assertEqual(a[:i + 1] + a[i + 2:], b[:i + 1] + b[i + 2:], "Search: only its deny list differs")
        da, db = a[i + 1].split(","), b[i + 1].split(",")
        self.assertEqual([x for x in da if x in db], db, "every rule it had, in the same order")
        self.assertTrue(all(x.startswith("Read(") for x in set(da) - set(db)), "S1 adds Read rules only")
        self.assertIn("Read(~/Library/Keychains/**)", da)
        tb, ta = S.run_py(r1, TABLES), S.run_py(r2, TABLES)
        tb["KIND_DENIES"].pop("search"), ta["KIND_DENIES"].pop("search")
        tb["policy"].pop("search"), ta["policy"].pop("search")
        self.assertEqual(ta, tb)


if __name__ == "__main__":
    unittest.main()
