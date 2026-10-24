"""2.6.2: the guarded follow-wording changes (propose.py, live_server.py). Copy to dev/tests/ when the two diffs are applied.
The register's Follow column is read (the older VIP column too); the check's lines and prompt say "follow"; the rule in the
prompts keeps its enforcing sentence ("never call or label a person a VIP").

Run: python3 dev/tests/test_follow_guarded_262.py     (quick tier: no Chrome, no vault)
"""
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "system" / "scripts"))
sys.path.insert(0, str(REPO / "system" / "scripts" / "vendor"))
import propose  # noqa: E402

WORD = re.compile(r"\bVIPs?\b")


class Guarded(unittest.TestCase):
    def test_follow_column_read_and_the_old_one(self):
        self.assertEqual(propose.person_vip({"extra": {"Follow": "yes"}}), "yes")
        self.assertEqual(propose.person_vip({"extra": {"VIP": "management"}}), "management")
        self.assertEqual(propose.person_vip({"extra": {"Follow": "", "VIP": "yes"}}), "yes")
        self.assertEqual(propose.person_vip({"extra": {"Follow": "no"}}), "")
        self.assertEqual(propose.person_vip({"extra": {}}), "")

    def test_server_lines_and_prompts(self):
        s = (REPO / "system/scripts/live_server.py").read_text(encoding="utf-8")
        self.assertIn("the follow check didn't finish:", s)
        self.assertIn('f"Follow check: {len(new)}', s)
        self.assertIn("the follow check failed", s)
        self.assertIn('VIP_PROMPT = ("creaite follow check.', s)
        self.assertIn("never call or label a person a VIP", s)
        self.assertNotIn('f"VIP check:', s)
        self.assertNotIn("{datetime.now():%H:%M} the VIP check", s)
        self.assertNotIn("skipped: no VIPs", s)


if __name__ == "__main__":
    unittest.main()
