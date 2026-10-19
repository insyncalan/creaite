"""BL-155, as changed by BL-175 (sprint-peek): the Keys chip is gone from Work and Review; the keys still work and Help lists
them; the hint lines stay in the page, hidden. A real browser against the real live server.

Run: python3 dev/tests/test_keys_chip.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

SHOWN = "(sel=>{ const e=document.querySelector(sel); return !!(e&&e.offsetParent&&getComputedStyle(e).opacity!=='0'); })"


class KeysChip(LiveBrowserCase):
    """BL-175 (sprint-peek): the chip is gone from Work and Review. The keys still work, the hint lines stay in the page but are
    hidden, and Help's keyboard table lists every key."""
    def shown(self, sel):
        return self.b.eval(f"{SHOWN}({sel!r})")

    def test_the_chip_is_gone_and_the_keys_still_work(self):
        b = self.b
        b.eval("go('work')")
        b.wait("document.querySelector('#workTbl tbody tr[data-row]')")
        self.assertEqual(b.eval("document.querySelectorAll('.keyschip,#wKeys,#rvKeys').length"), 0)
        self.assertFalse(self.shown("#whintList"))                           # the line stays in the page, hidden
        self.assertTrue(b.eval("!!document.getElementById('whintList')"))
        b.eval("document.activeElement&&document.activeElement.blur()")
        b.key("j")
        b.wait("HLC!=null", 5)                                                 # J still moves the cursor
        b.eval("go('review',null,{legacy:true})")
        b.wait("document.querySelector('#reviewBody tr[data-n]')")
        self.assertEqual(b.eval("document.querySelectorAll('.keyschip').length"), 0)
        self.assertFalse(self.shown("#rvHint"))
        before = b.eval("RSEL")
        b.key("j")
        b.wait(f"RSEL!=={before}", 5)

    def test_help_lists_the_keys(self):
        help_md = (Path(__file__).resolve().parents[2] / "system/templates/help.md").read_text(encoding="utf-8")
        self.assertNotIn("**Keys** chip", help_md)
        self.assertIn("Work's and Review's keys are all in this table", help_md)
        for row in ("| Space |", "| J / K |", "| A / R / X |", "| D |", "| F |", "| Cmd/Ctrl + Enter |"):
            self.assertIn(row, help_md)


if __name__ == "__main__":
    unittest.main()
