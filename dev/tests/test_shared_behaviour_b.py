"""BL-316 / #89: part b of the keys test (the keys script, focus and Esc on every menu, picker and dialog, and every popup in the
code reached). Parts a, b and c run the screens of KEYS_PARTS in test_shared_behaviour.py, each in a sample vault of its own,
so the three run side by side (about 220 s each where the whole took about 650 s). Part a, the Chrome-less inventory tests and
the helpers (class Keys) are in test_shared_behaviour.py; nothing in the script changed: same methods, same screens, same probe.
What each part answers for in "unreached" is set by behaviour_witness.json (behaviour_witness.py writes it).

Run: python3 dev/tests/test_shared_behaviour_b.py   (needs Google Chrome; SB_REPORT=1 and SB_ONLY=today,work as there)
"""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "tools"))
import test_shared_behaviour as tsb  # noqa: E402
import test_ui_sweep as us  # noqa: E402


class SharedBehaviourB(tsb.Keys, us.UiSweepCase):
    """Part b of the keys test."""

    def test_every_menu_picker_and_dialog_answers_the_same_keys(self):
        self.run_part("b")


if __name__ == "__main__":
    unittest.main()
