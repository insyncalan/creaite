"""BL-316 / #89: part b of the Undo check (a change from a menu or a list offers Undo). Part a is test_shared_undo.py; the screens
of each are UNDO_PARTS in test_shared_behaviour.py, and each part has a sample vault of its own (this check changes data), so the
two run side by side (about 230 s each where the whole took about 470 s). Nothing in the script changed.

Run: python3 dev/tests/test_shared_undo_b.py   (needs Google Chrome; SB_REPORT=1 and SB_ONLY=today,work as there)
"""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "tools"))
import test_shared_undo as tsu  # noqa: E402
import test_ui_sweep as us  # noqa: E402


class SharedUndoB(tsu.Undo, us.UiSweepCase):
    """Part b of the Undo check."""

    def test_a_change_from_a_menu_or_list_offers_undo(self):
        self.run_part("b")


if __name__ == "__main__":
    unittest.main()
