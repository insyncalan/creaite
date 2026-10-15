"""BL-146: every multi-line field grows to show what is typed, through the one shared helper (autoGrow, made from BL-145's chFit).
A real browser against the real live server: the edit panel's Action and Latest update, Quick capture's notes and Generate's
"Steer it" grow at three, six and thirty lines, stop at about 60% of the window with an inner scroll, shrink back, and are
right after a paste and when a record is opened with long text already in it.

Run: python3 dev/tests/test_autosize_fields.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from split_dashboard import readable_page  # noqa: E402

SHIFT = 8
GEO = """(sel=>{ const el=document.querySelector(sel); return {h:el.getBoundingClientRect().height, sh:el.scrollHeight, ch:el.clientHeight,
  ov:getComputedStyle(el).overflowY, resize:getComputedStyle(el).resize, st:el.scrollTop}; })"""


class AutosizeFields(LiveBrowserCase):
    shared_server = True
    width, height = 1400, 900

    def setUp(self):
        super().setUp()
        # BL-327: the shared server's data is soon older than PAGE_FRESH, so each load re-reads /api/data after its first paint;
        # under load that reload redrew the open editor mid-test (a hand-dragged 260px box came back at its automatic 78px)
        self.b.wait("PULSE.reloads===0 && !PULSE.busy && !EVS.timer", 30)

    def geo(self, sel):
        return self.b.eval(f"{GEO}({sel!r})")

    def fill(self, sel, n):
        """Replace the box's text with n lines, as a paste would (one input event)."""
        b = self.b
        b.eval(f"(()=>{{ const el=document.querySelector({sel!r}); el.focus(); el.select(); }})()")
        b.call("Input.insertText", text="\n".join(f"line {i + 1}" for i in range(n)))
        return self.geo(sel)

    def grows_and_stops(self, sel, allow_drag=True):
        b = self.b
        one = self.fill(sel, 1)
        g3 = self.fill(sel, 3)
        self.assertGreaterEqual(g3["h"], one["h"], sel)
        self.assertLessEqual(g3["sh"], g3["ch"] + 1, sel)                   # all three lines show
        g6 = self.fill(sel, 6)
        self.assertGreater(g6["h"], g3["h"] + 30, sel)
        self.assertLessEqual(g6["sh"], g6["ch"] + 1, sel)
        self.assertEqual(g6["ov"], "hidden", sel)
        g30 = self.fill(sel, 30)
        cap = int(b.eval("window.innerHeight") * 0.6)
        self.assertLessEqual(g30["h"], cap + 1, sel)                        # 60% of the window, no more
        self.assertGreater(g30["h"], cap - 3, sel)
        self.assertGreater(g30["sh"], g30["ch"], sel)                       # then it scrolls inside
        self.assertEqual(g30["ov"], "auto", sel)
        self.assertGreaterEqual(g30["st"] + g30["ch"], g30["sh"] - 2, sel)  # with the cursor (at the end) in view
        for _ in range(30 * 7):                                             # deleting back shrinks it again
            b.key("Backspace")
        b.pump(0.1)
        back = self.geo(sel)
        self.assertLessEqual(back["h"], g3["h"] + 1, sel)
        if allow_drag:
            self.assertIn(back["resize"], ("vertical", "both"), sel)        # the drag handle stays

    def test_edit_panel_action_and_latest_update(self):
        b = self.b
        b.eval("go('work')")
        b.pump(0.2)
        b.eval("mvOpenPage('ABC','plan','ABC-M-001')")                      # BL-186: the milestone editor's text box
        b.wait("document.getElementById('mvDesc')")
        self.grows_and_stops("#mvDesc")
        b.eval("mvEdClose(true); EDITING=false; closePanel(); openProject('ABC','health')")   # and project health's reason
        b.pump(0.3)
        self.grows_and_stops("#f_reason")

    def test_quick_capture_and_steer_it(self):
        b = self.b
        b.eval("openCapture()")
        b.pump(0.3)
        self.grows_and_stops("#qcNotes")
        b.eval("$('#qcNotes').value=''")
        b.eval("go('projects'); openGen('ABC')")
        b.pump(0.4)
        if not b.eval("$('#genDlg').open"):
            self.skipTest("Generate did not open in this vault")
        self.grows_and_stops("#genNote", allow_drag=False)
        b.eval("$('#genDlg').close()")

    def test_a_value_set_by_code_and_a_record_opened_with_long_text(self):
        b = self.b
        b.eval("go('work')")
        b.pump(0.2)
        long = "\\n".join(f"existing line {i}" for i in range(9))
        b.eval("mvOpenPage('ABC','plan','ABC-M-001')")                      # BL-186: the milestone editor, given long text as it opens
        b.wait("document.getElementById('mvDesc')")
        b.eval(f"$('#mvDesc').value='{long}'")
        b.pump(0.3)
        g = self.geo("#mvDesc")
        self.assertLessEqual(g["sh"], g["ch"] + 1)
        self.assertGreater(g["h"], 9 * 16)
        b.eval("$('#mvDesc').value='short'")                                 # code sets the value: re-measured at once
        self.assertLess(self.geo("#mvDesc")["h"], g["h"] - 60)
        b.eval("$('#mvDesc').value='" + long + "'")
        self.assertAlmostEqual(self.geo("#mvDesc")["h"], g["h"], delta=1)

    def test_a_wrapped_paste_and_a_width_change(self):
        b = self.b
        b.eval("go('work')")
        b.pump(0.2)
        b.eval("mvOpenPage('ABC','plan','ABC-M-001')")                      # BL-186: the milestone editor's text box
        b.wait("document.getElementById('mvDesc')")
        b.eval("$('#mvDesc').focus(); $('#mvDesc').select()")
        b.call("Input.insertText", text="A long paragraph that wraps over several lines of the box, with no line breaks. " * 5)
        g = self.geo("#mvDesc")                                              # no pump: set by the input event itself
        self.assertLessEqual(g["sh"], g["ch"] + 1)
        self.assertGreater(g["h"], 70)
        b.resize(1100, 900)                                                 # a narrower panel wraps more lines
        b.pump(0.4)
        g2 = self.geo("#mvDesc")
        self.assertLessEqual(g2["sh"], g2["ch"] + 1)

    def test_a_height_dragged_by_hand_is_kept(self):
        b = self.b
        b.eval("go('work')")
        b.pump(0.2)
        b.eval("mvOpenPage('ABC','plan','ABC-M-001')")                      # BL-186: the milestone editor's text box
        b.wait("document.getElementById('mvDesc')")
        b.wait("document.getElementById('mvDesc').dataset.ag")              # fitted once (the next frame), as before any real drag
        self.fill("#mvDesc", 2)
        b.eval("$('#mvDesc').style.height='260px'")                          # as the drag handle does
        b.pump(0.3)
        b.key("Backspace")
        b.pump(0.1)
        self.assertGreaterEqual(self.geo("#mvDesc")["h"], 258)

    def test_one_helper(self):
        src = readable_page()      # BL-231: the source; the bundle reprints the code
        self.assertEqual(src.count("function autoGrow("), 1)
        self.assertIn("autoGrow(el,Math.floor(", src)                       # the chat box uses the same helper
        self.assertEqual(src.count('el.style.height="auto"'), 1)            # one place measures


if __name__ == "__main__":
    unittest.main()
