"""BL-316 / #89: the Undo half of the shared behaviour test, in files of their own so they run in parallel with the keys half
(dev/tests/test_shared_behaviour.py, _b and _c; the parts share no state). Part a is here and part b is test_shared_undo_b.py
(UNDO_PARTS in test_shared_behaviour.py lists the screens of each; 218 s and 266 s measured where the whole took 473 s). Nothing in
it changed when it moved: the class, its helper and the script are the same, and they use the same Driver, screens and probe.

**Undo:** in a sample vault of its own (this one changes data) each menu and list is opened once more and an item chosen
(down, Enter); when that saves a change, the message at the foot (or, in the peek, its staging bar's Undo last) must offer Undo
(and Undo is pressed, so the next control sees the sample as it was).

SB_REPORT=1 prints each result; SB_ONLY=today,work runs only those screens.

Run: python3 dev/tests/test_shared_undo.py   (needs Google Chrome)
"""
import os
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "tools"))
import test_ui_sweep as us  # noqa: E402
from test_shared_behaviour import UNDO_PARTS, VIEW_ONLY, Driver, judge, screen_area  # noqa: E402


def undo_group(name):
    """Openers that differ only by the item they act on are one group: the Undo check chooses from the first of each."""
    return re.sub(r"\b[A-Z][A-Z0-9]{2,6}-[A-Z]+-\d+\b", "", name.split(":")[0]).strip()


class Undo(Driver):
    """BL-316: a change made from a menu or a list offers Undo (a sample vault of its own: this one changes data). The helper and
    the script for one part of the screens (UNDO_PARTS); the test classes are SharedUndo here and SharedUndoB in test_shared_undo_b.py."""

    def pick(self, i, o):
        """Open, ↓, Enter. What it got wrong when it saved a change (no Undo on offer), or None when nothing was saved
        (a filter, a view, a page, a dialog that asks first) or the control was left alone."""
        b = self.b
        if o["kind"] == "dialog" or any(x in o["sig"] for x in VIEW_ONLY) or not b.eval(f"SB.focus({i})"):
            return None
        self.press("Enter", 0.4)
        if not self.state(i)["open"]:
            return None
        w0 = b.eval("SB.writes().writes")
        self.press("ArrowDown", 0.2)
        self.press("Enter", 1.0)
        if b.eval("SB.writes().writes") == w0:
            return None                              # nothing saved (a filter, a view, a page): nothing to undo
        for _ in range(8):
            u = b.eval("SB.undo()")
            if u:
                b.eval(f"document.querySelector({u!r}).click()")         # put the sample back for the next control
                b.pump(1.0)
                return []
            if b.eval(f"SB.state({i}).modal"):
                return None                          # it asks first: the change is the dialog's, not the menu's
            b.pump(0.25)
        return ["a change is saved with no Undo"]

    def run_part(self, part):
        report = os.environ.get("SB_REPORT")
        want = set(os.environ["SB_ONLY"].split(",")) if os.environ.get("SB_ONLY") else None
        only = [s for s in UNDO_PARTS[part] if want is None or s in want]
        found = set()
        for name in only:
            done = set()

            def once(i, o, done=done):
                g = (o["sig"], undo_group(o["name"]))
                if g in done:
                    return None
                done.add(g)
                return self.pick(i, o)
            for o, bad in self.each_opener(name, once):
                if bad is None:
                    continue
                if report:
                    print(f"undo {name:16} {o['kind']:8} {o['sig'][:48]:48} {o['name'][:40]:40} {'; '.join(bad) or 'ok'}")
                if bad:
                    found.add((screen_area(name), f"undo: {name} {o['sig']} “{undo_group(o['name'])}”: {'; '.join(bad)}"))
        msg = judge("undo", found, set(only))
        self.assertFalse(msg, "\n".join(msg))


class SharedUndo(Undo, us.UiSweepCase):
    """Part a of the Undo check (the other is test_shared_undo_b.py)."""

    def test_a_change_from_a_menu_or_list_offers_undo(self):
        self.run_part("a")


if __name__ == "__main__":
    unittest.main()
