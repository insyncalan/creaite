"""BL-145: the ask creaite message box grows with what is typed. A real browser against the real live server.

Run: python3 dev/tests/test_chat_box.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase, theme_names  # noqa: E402

PALETTES = theme_names()   # every theme (BL-40: nine in 1.5.1)
SHIFT = 8

GEO = """(()=>{ const el=$('#chIn'), r=el.getBoundingClientRect(), c=$('#chat').getBoundingClientRect(), s=$('#chSend').getBoundingClientRect(),
  a=$('#chAttach').getBoundingClientRect(), m=$('#acMenu').getBoundingClientRect();
  return {h:r.height, top:r.top, bottom:r.bottom, left:r.left, right:r.right, chatH:c.height, chatTop:c.top, sh:el.scrollHeight, ch:el.clientHeight,
    st:el.scrollTop, ov:getComputedStyle(el).overflowY, resize:getComputedStyle(el).resize, sendTop:s.top, sendBottom:s.bottom,
    attTop:a.top, attBottom:a.bottom, menuTop:m.top, menuBottom:m.bottom, menuHidden:$('#acMenu').hidden}; })()"""


class ChatBox(LiveBrowserCase):
    shared_server = True
    width, height = 1400, 900

    def open(self):
        b = self.b
        b.eval("openChat()")
        b.pump(0.3)
        b.eval("$('#chIn').value=''; $('#chIn').focus()")
        b.pump(0.1)
        return b

    def geo(self):
        return self.b.eval(GEO)

    def lines(self, n):
        """n lines typed with Shift+Enter, as a person would."""
        b = self.b
        for i in range(n):
            if i:
                b.key("Enter", SHIFT)
            b.type(f"line {i + 1}")
        b.pump(0.1)

    def one_row(self):
        b = self.open()
        return self.geo()["h"], b

    def test_three_and_six_lines_grow_the_box_and_thirty_stop_at_the_maximum(self):
        row, b = self.one_row()
        self.assertEqual(self.geo()["resize"], "none")                      # the drag handle stays off
        self.lines(3)
        g3 = self.geo()
        self.assertGreater(g3["h"], row + 20)
        self.assertLessEqual(g3["sh"], g3["ch"] + 1)                        # all three lines show, nothing to scroll
        self.assertEqual(g3["ov"], "hidden")
        self.assertEqual(b.eval("$('#chIn').value.split('\\n').length"), 3)  # Shift+Enter made new lines, nothing was sent
        self.assertEqual(b.eval("document.querySelectorAll('#chLog .msg.u').length"), 0)
        b.key("Enter", SHIFT)
        self.lines(3)
        g6 = self.geo()
        self.assertGreater(g6["h"], g3["h"] + 30)
        self.assertLessEqual(g6["sh"], g6["ch"] + 1)
        for _ in range(24):
            b.key("Enter", SHIFT)
            b.type("more")
        b.pump(0.1)
        g30 = self.geo()
        mx = min(g30["chatH"], 900) * 0.5
        self.assertLessEqual(g30["h"], mx + 1)                              # about half the panel, no more
        self.assertGreater(g30["h"], mx - 2)
        self.assertGreater(g30["sh"], g30["ch"])                            # it scrolls inside
        self.assertEqual(g30["ov"], "auto")
        self.assertGreaterEqual(g30["st"] + g30["ch"], g30["sh"] - 2)       # with the cursor (at the end) in view
        for _ in range(60):                                                 # deleting back shrinks it again
            b.key("Backspace")
        b.pump(0.1)
        self.assertLess(self.geo()["h"], g30["h"])

    def test_pasting_grows_it_at_once(self):
        row, b = self.one_row()
        b.call("Input.insertText", text="\n".join(f"pasted line {i}" for i in range(8)))
        g = self.b.eval(GEO)                                                # no pump: the height is set by the input event itself
        self.assertGreater(g["h"], row + 80)
        self.assertLessEqual(g["sh"], g["ch"] + 1)
        long = "A long paragraph that wraps across several lines of the box without any line breaks at all. " * 6
        b.eval("$('#chIn').value=''")
        b.call("Input.insertText", text=long)
        g = self.geo()
        self.assertGreater(g["h"], row + 40)                                # wrapped lines count
        self.assertLessEqual(g["sh"], g["ch"] + 1)

    def test_sending_or_clearing_returns_it_to_one_row(self):
        row, b = self.one_row()
        self.lines(5)
        self.assertGreater(self.geo()["h"], row + 40)
        b.eval("send=((orig)=>function(t){ const v=(t??$('#chIn').value); window.SENT=v; $('#chIn').value=''; })(send)")
        b.key("Enter")                                                      # Enter still sends
        b.pump(0.1)
        self.assertIn("line 5", b.eval("window.SENT"))
        self.assertAlmostEqual(self.geo()["h"], row, delta=1)
        self.lines(5)
        b.eval("document.execCommand('selectAll')")                        # select all, then delete: emptied by hand
        b.key("Backspace")
        b.pump(0.1)
        self.assertEqual(b.eval("$('#chIn').value"), "")
        self.assertAlmostEqual(self.geo()["h"], row, delta=1)

    def test_reopening_with_a_draft_and_resizing_the_panel_recalculate(self):
        row, b = self.one_row()
        self.lines(6)
        h6 = self.geo()["h"]
        b.eval("closeChat()")
        b.pump(0.1)
        b.eval("openChat()")
        b.pump(0.3)
        self.assertAlmostEqual(self.geo()["h"], h6, delta=1)                # the draft is kept and the height is right
        b.eval("$('#chIn').value=''")
        b.call("Input.insertText", text="word " * 60)                       # wraps: the panel's width matters
        b.pump(0.1)
        b.eval("setChatWidth(800,false)")
        b.pump(0.2)
        wide = self.geo()
        b.eval("setChatWidth(360,false)")
        b.pump(0.2)
        narrow = self.geo()
        self.assertGreater(narrow["h"], wide["h"])
        self.assertLessEqual(narrow["sh"], narrow["ch"] + 1)
        b.resize(1400, 500)                                                 # a short window: the maximum follows it
        b.eval("$('#chIn').value=Array.from({length:40},(_, i)=>'l'+i).join('\\n')")
        b.pump(0.1)
        g = self.geo()
        self.assertLessEqual(g["h"], 250 + 1)
        self.assertGreaterEqual(g["top"], g["chatTop"])
        b.eval(f"setChatWidth({420},false)")

    def test_send_and_the_suggestions_stay_in_place(self):
        row, b = self.one_row()
        g1 = self.geo()
        self.lines(8)
        g = self.geo()
        self.assertAlmostEqual(g["bottom"] - g["sendBottom"], g1["bottom"] - g1["sendBottom"], delta=1)    # Send on the bottom edge
        self.assertAlmostEqual(g["bottom"] - g["attBottom"], g1["bottom"] - g1["attBottom"], delta=1)      # and attach
        self.assertGreater(g["sendTop"], g["top"] + 40)
        b.eval("$('#chIn').value=''")
        b.type("/")
        b.pump(0.2)
        m = self.geo()
        self.assertFalse(m["menuHidden"])
        self.assertLessEqual(m["menuBottom"], m["top"] + 6)                 # attached above the box, not covered by it
        self.assertGreaterEqual(m["menuTop"], m["chatTop"])
        b.call("Input.insertText", text="\n" * 20)                          # a tall box: the list still fits above it
        b.eval("AC.items=acItems('/'); acDraw()")
        b.pump(0.2)
        m = self.geo()
        if not m["menuHidden"]:
            self.assertLessEqual(m["menuBottom"], m["top"] + 6)
            self.assertGreaterEqual(m["menuTop"], m["chatTop"] - 1)

    def test_every_theme_light_and_dark(self):
        b = self.open()
        for pal in PALETTES:
            for mode in ("Light", "Dark"):
                b.eval(f"S.palette={pal!r}; S.theme={mode!r}; applyTheme(); $('#chIn').value=''")
                b.pump(0.1)
                one = self.geo()
                self.assertLessEqual(one["sendBottom"], one["bottom"] + 0.5, (pal, mode))
                self.assertGreaterEqual(one["sendTop"], one["top"] - 0.5, (pal, mode))
                b.eval("$('#chIn').value='a\\nb\\nc\\nd'")
                b.pump(0.1)
                g = self.geo()
                self.assertGreater(g["h"], one["h"] + 30, (pal, mode))
                self.assertLessEqual(g["sh"], g["ch"] + 1, (pal, mode))
                self.assertAlmostEqual(g["bottom"] - g["sendBottom"], one["bottom"] - one["sendBottom"], delta=1, msg=(pal, mode))
        b.eval("S.palette='creaite'; S.theme='System'; applyTheme(); $('#chIn').value=''")


class ChatBoxMotion(LiveBrowserCase):
    shared_server = True
    reduced_motion = False
    width, height = 1400, 900

    def test_the_height_changes_at_once_in_every_motion_setting(self):
        b = self.b
        b.eval("openChat()")
        b.pump(0.3)
        for m in ("Full", "Reduce", "System"):
            b.eval(f"S.motion={m!r}; applyMotion(); $('#chIn').value=''")
            self.assertNotIn("height", b.eval("getComputedStyle($('#chIn')).transitionProperty"), m)   # BL-136: height never animates
            b.eval("$('#chIn').value='a\\nb\\nc\\nd\\ne'")
            self.assertGreater(b.eval("$('#chIn').getBoundingClientRect().height"), 90, m)              # no frame waited for
        b.eval("S.motion='System'; applyMotion(); $('#chIn').value=''")


if __name__ == "__main__":
    unittest.main()
