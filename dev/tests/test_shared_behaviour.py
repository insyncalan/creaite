"""BL-316: one keyboard script on every menu, picker and dialog on every screen (dev/COMPONENTS.md §3).

Every visible control that opens a popup (it says so with aria-haspopup) is driven the same way, with real key presses:
focus it and press Enter: the popup opens, the control says so (aria-expanded) and focus goes into it; in a menu or a list,
↓ and ↑ move between its items; Esc closes it and focus is back on the control that opened it; opened again, Tab closes a
menu or a list. A dialog keeps Tab inside itself, so for a dialog only Enter and Esc are checked. Each screen is the
snapshot sample vault's (test_snapshots), at 1400 by 1000.

SB_REPORT=1 prints every opener's result as a table (the audit's raw data, dev/V195-CONSISTENCY-NOTE.md); SB_ONLY=today,work
runs only those screens.

Run: python3 dev/tests/test_shared_behaviour.py   (needs Google Chrome; skipped otherwise)
"""
import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_ui_sweep as us  # noqa: E402

PROBE = (Path(__file__).resolve().parent / "behaviour_probe.js").read_text(encoding="utf-8")

SCREENS = dict(us.SCREENS)
SCREENS.pop("cmdk", None)              # ⌘K is itself the dialog; its list is checked by test_cmdk
SCREENS["shell"] = ("go('today')", "!document.getElementById('v-today').hidden", ".shell")   # the sidebar and the top bar
us.SCREENS["shell"] = SCREENS["shell"]
ONLY = {"shell": ".rail,header.bar"}   # the shell's own controls, not the page inside it


def region_of(name, region):
    return ONLY.get(name, region)


class SharedBehaviour(us.UiSweepCase):
    """BL-316's shared behaviour test."""

    def press(self, key, wait=0.25):
        self.b.key(key)
        self.b.pump(wait)

    def state(self, i):
        return self.b.eval(f"SB.state({i})")

    def settle(self, name):
        """Close whatever the last control left open; go back to the screen when something is still open."""
        b = self.b
        for _ in range(2):
            if not b.eval("SB.popups().length"):
                break
            self.press("Escape", 0.15)
        if b.eval("SB.reset()"):
            self.goto(name)
            b.eval(PROBE + ";true")

    def opened(self, i):
        """Enter on opener i: (its state, what it got wrong), or (None, why) when nothing opened."""
        self.press("Enter", 0.4)
        s = self.state(i)
        if not s["open"] and not s["modal"]:
            return None, ["Enter opens nothing"]
        bad = []
        if s["expanded"] is not None and s["expanded"] != "true":
            bad.append(f"aria-expanded is {s['expanded']!r} when open")
        if not s["focusInPopup"]:
            bad.append(f"focus stays outside the popup ({s['active']})")
        return s, bad

    def arrows(self, i, s1):
        """↓ then ↑ inside a menu or a list: focus (or the active option) moves, and stays inside (a list of one has
        nowhere to move: focus only stays inside)."""
        self.press("ArrowDown")
        s2 = self.state(i)
        self.press("ArrowUp")
        s3 = self.state(i)
        if not s2["focusInPopup"] or not s3["focusInPopup"]:
            return ["↓ ↑ take focus out of the popup"]
        if s2["active"] == s1["active"] and s3["active"] == s1["active"] and s1["items"] > 1:
            return ["↓ ↑ move nothing"]
        return []

    def escape(self, i):
        """Esc: closed, focus back on the control, aria-expanded false. Returns (state, what it got wrong)."""
        self.press("Escape", 0.35)
        s = self.state(i)
        bad = []
        if s["open"] or s["modal"]:
            bad.append("Esc leaves it open")
        if not s["focusOnOpener"] and s["connected"]:
            bad.append(f"Esc doesn't return focus to the control ({s['active']})")
        if s["expanded"] not in (None, "false"):
            bad.append(f"aria-expanded is {s['expanded']!r} after Esc")
        return s, bad

    def tab_closes(self, i):
        """Opened again, Tab closes a menu or a list."""
        self.b.eval(f"SB.focus({i})")
        self.press("Enter", 0.4)
        if not self.state(i)["open"]:
            return []
        self.press("Tab", 0.3)
        return ["Tab leaves it open"] if self.state(i)["open"] else []

    def drive(self, i, kind):
        """The script for opener i: a list of what it got wrong (empty when it behaves)."""
        if not self.b.eval(f"SB.focus({i})"):
            return ["it can't take focus"]
        s1, bad = self.opened(i)
        if s1 is None:
            return bad
        dialog = kind == "dialog" or s1["modal"]
        if not dialog:
            bad += self.arrows(i, s1)
        s4, more = self.escape(i)
        bad += more
        if not dialog and s4["connected"] and not s4["open"]:
            bad += self.tab_closes(i)
        return bad

    def run_screen(self, name):
        go, ready, region = SCREENS[name]
        self.goto(name)
        b = self.b
        b.eval(PROBE + ";true")
        rows = b.eval(f"SB.openers({json.dumps(region_of(name, region))})")
        out = []
        for o in rows:
            again = b.eval(f"SB.openers({json.dumps(region_of(name, region))})")      # a redraw may have replaced the controls
            match = [x for x in again if x["sig"] == o["sig"] and x["name"] == o["name"]]
            if not match:
                continue
            i = match[0]["i"]
            bad = self.drive(i, o["kind"])
            out.append((o, bad))
            self.settle(name)
        return out

    def test_every_menu_picker_and_dialog_answers_the_same_keys(self):
        report = os.environ.get("SB_REPORT")
        failures = []
        only = os.environ.get("SB_ONLY", "").split(",") if os.environ.get("SB_ONLY") else list(SCREENS)
        for name in only:
            with self.subTest(name):
                rows = self.run_screen(name)
                for o, bad in rows:
                    if report:
                        print(f"{name:16} {o['kind']:8} {o['sig'][:48]:48} {o['name'][:40]:40} {'; '.join(bad) or 'ok'}")
                    if bad:
                        failures.append(f"{name}: {o['sig']} “{o['name']}”: {'; '.join(bad)}")
        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
