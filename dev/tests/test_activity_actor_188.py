"""#188: Activity never shows the engine's command name (cx-edit) as the actor.

Run: python3 dev/tests/test_activity_actor_188.py
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "system" / "scripts"))
import build_dashboard  # noqa: E402


class ActorWording(unittest.TestCase):
    def test_cx_edit_reads_you_by_hand(self):
        self.assertEqual(build_dashboard.BY["cx-edit"], "You, by hand")

    def test_no_actor_names_a_command(self):
        for text in build_dashboard.BY.values():
            self.assertNotIn("cx-", text)
            self.assertNotIn(" via ", text)

    def test_dashboard_unchanged(self):
        self.assertEqual(build_dashboard.BY["dashboard"], "You, in the dashboard")


if __name__ == "__main__":
    unittest.main()
