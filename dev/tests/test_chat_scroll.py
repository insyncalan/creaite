"""BL-120: ask creaite keeps your place when a live update arrives. A real browser against the real live server.

Run: python3 dev/tests/test_chat_scroll.py   (needs Google Chrome; skipped otherwise)
"""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import TEST_PALETTES, LiveBrowserCase  # noqa: E402

PALETTES = TEST_PALETTES   # creaite and Cursor only (live_browser.TEST_PALETTES)


class ChatScroll(LiveBrowserCase):
    shared_server = True
    width, height = 1400, 900

    def thread(self, n=40):
        """A long thread, opened: the chat is at the bottom, as after any reply."""
        b = self.b
        b.eval("openChat()")
        b.pump(1.2)                                                    # let the greeting finish typing in
        b.eval(f"$('#chLog').innerHTML=''; for(let i=0;i<{n};i++) addEl(i%2?'msg a':'msg u','Line '+i+' of a long conversation, long enough to fill the log with something to scroll through.', null);")
        b.pump(0.2)
        return b

    def top(self):
        return self.b.eval("$('#chLog').scrollTop")

    def at_bottom(self):
        return self.b.eval("$('#chLog').scrollHeight-$('#chLog').scrollTop-$('#chLog').clientHeight<=2")

    def scroll_up(self, to=200):
        self.b.eval(f"$('#chLog').scrollTop={to}")
        self.b.pump(0.2)                                              # the scroll event is handled on the next frame

    def jump(self):
        return self.b.eval("(()=>{ const j=document.getElementById('chJump'); return {hidden:j.hidden, text:j.textContent}; })()")

    def test_at_the_bottom_new_content_keeps_following(self):
        b = self.thread()
        self.assertTrue(self.at_bottom())
        b.eval("addEl('step','✓ A step'); addEl('msg a','A reply')")
        self.assertTrue(self.at_bottom())
        self.assertTrue(self.jump()["hidden"])

    def test_within_a_few_pixels_of_the_bottom_still_follows(self):
        b = self.thread()
        b.eval("$('#chLog').scrollTop=$('#chLog').scrollHeight-$('#chLog').clientHeight-6")
        b.pump(0.2)
        b.eval("addEl('msg a','Another')")
        self.assertTrue(self.at_bottom())

    def test_scrolled_up_nothing_moves_the_view_and_the_button_appears(self):
        b = self.thread()
        self.scroll_up(200)
        before = self.top()
        self.assertAlmostEqual(before, 200, delta=2)
        self.assertTrue(self.jump()["hidden"])                         # nothing has arrived yet
        b.eval("addEl('step','✓ Reading the tracker'); addEl('step','<span class=\"spin\"></span>Working…')")        # a step
        self.assertEqual(self.top(), before)
        b.eval("(async()=>{ await sayMd('A **finished** reply, long enough to matter.'); })()")                        # the reply
        b.pump(0.3)
        self.assertEqual(self.top(), before)
        b.eval("stampMsg($('#chLog .msg.a:last-of-type'), nowIso())")                                                   # its time stamp
        self.assertEqual(self.top(), before)
        b.eval("addEl('msg a','x'); say('Some words typed in', null)")                                                  # text typed in
        b.pump(0.5)
        self.assertEqual(self.top(), before)
        j = self.jump()
        self.assertFalse(j["hidden"])
        self.assertEqual(j["text"], "↓ New activity")

    def test_the_label_says_a_run_is_still_going(self):
        b = self.thread()
        self.scroll_up()
        b.eval("RUN={id:'x'}; addEl('step','✓ Step')")
        self.assertEqual(self.jump()["text"], "↓ Latest · still working")
        b.eval("RUN=null")

    def test_the_button_scrolls_to_the_latest_and_resumes_following(self):
        b = self.thread()
        self.scroll_up()
        b.eval("addEl('msg a','New below')")
        b.click("#chJump")
        b.pump(0.2)
        self.assertTrue(self.at_bottom())
        self.assertTrue(self.jump()["hidden"])
        b.eval("addEl('msg a','And after pressing it')")
        self.assertTrue(self.at_bottom())                              # following again

    def test_scrolling_back_down_resumes_following_and_hides_the_button(self):
        b = self.thread()
        self.scroll_up()
        b.eval("addEl('msg a','New below')")
        self.assertFalse(self.jump()["hidden"])
        b.eval("$('#chLog').scrollTop=$('#chLog').scrollHeight")
        b.pump(0.2)
        self.assertTrue(self.jump()["hidden"])
        b.eval("addEl('msg a','Followed')")
        self.assertTrue(self.at_bottom())

    def test_alans_own_actions_go_to_the_bottom(self):
        b = self.thread()
        self.scroll_up()
        b.eval("addEl('msg u','Alan sends a message')")                # sending
        self.assertTrue(self.at_bottom())
        self.assertTrue(self.jump()["hidden"])
        self.scroll_up()
        b.eval("newChat()")                                            # a new chat: the greeting is the first line
        b.pump(0.8)
        self.assertTrue(self.at_bottom())
        self.assertTrue(self.jump()["hidden"])
        self.thread()
        self.scroll_up()
        b.eval("$('#chLog').innerHTML=''; for(let i=0;i<40;i++) addEl('msg a','Reopened '+i, null)")   # a chat opened from History starts empty, then fills
        b.pump(0.2)
        self.assertTrue(self.at_bottom())

    def test_at_the_bottom_a_change_in_height_never_shows_the_button(self):
        """BL-311: the Edit button moving, a step in the fold, the working line and a smaller panel aren't Alan scrolling away."""
        b = self.thread()
        b.eval("addEl('msg u','Can you update the owner of FAL-A-010?'); RUN={id:'x'}")
        b.pump(0.2)
        b.eval("window._g=stepGroup(null,'Reading the tracker'); window._g.querySelector('details').open=true; working()")
        b.pump(0.3)
        for i in range(6):                                             # the fold grows without a new line, then something else arrives
            b.eval(f"stepGroup(window._g,'Step {i} '+'with a long label '.repeat(8))")
            b.pump(0.1)
        b.eval("$('#chLog').style.maxHeight='300px'")                  # the panel gets shorter (the composer grows)
        b.pump(0.3)
        b.eval("[...$$('#chLog .msg.u')].pop().insertAdjacentHTML('beforeend','<div style=\"height:60px\"></div>')")
        b.pump(0.3)
        b.eval("addEl('step','✓ Another step')")
        b.pump(0.2)
        self.assertTrue(self.at_bottom())
        self.assertTrue(self.jump()["hidden"], self.jump())
        b.eval("RUN=null; $('#chLog').style.maxHeight=''")

    def test_the_button_is_a_real_button_the_keyboard_reaches(self):
        b = self.thread()
        self.scroll_up()
        b.eval("addEl('msg a','New below')")
        self.assertEqual(b.eval("document.getElementById('chJump').tagName"), "BUTTON")
        b.eval("document.getElementById('chJump').focus()")
        self.assertTrue(b.eval("document.activeElement.id==='chJump'"))
        b.call("Input.dispatchKeyEvent", type="keyDown", key="Enter", code="Enter", windowsVirtualKeyCode=13, text="\r")
        b.call("Input.dispatchKeyEvent", type="keyUp", key="Enter", code="Enter", windowsVirtualKeyCode=13)
        b.pump(0.3)
        self.assertTrue(self.at_bottom())

    def test_the_button_reads_in_every_theme_and_mode(self):
        b = self.thread()
        self.scroll_up()
        b.eval("addEl('msg a','New below')")

        def rgb(text):
            nums = [float(x) for x in re.findall(r"[\d.]+", text)[:3]]
            return [n * 255 if text.startswith("color(") else n for n in nums]

        def lum(c):
            f = lambda v: (v / 255) / 12.92 if v / 255 <= 0.03928 else (((v / 255) + 0.055) / 1.055) ** 2.4  # noqa: E731
            return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])
        for palette in PALETTES:
            for mode in ("Light", "Dark"):
                b.eval(f"S.palette={palette!r}; S.theme={mode!r}; applyTheme()")
                b.pump(0.3)
                self.assertFalse(self.jump()["hidden"], (palette, mode))
                bg, ink = b.eval("(()=>{ const c=getComputedStyle(document.getElementById('chJump')); return [c.backgroundColor, c.color]; })()")
                a, c = lum(rgb(bg)), lum(rgb(ink))
                ratio = (max(a, c) + 0.05) / (min(a, c) + 0.05)
                self.assertGreaterEqual(ratio, 4.5, (palette, mode, bg, ink, ratio))
        # and it sits over the foot of the log, inside the chat panel
        box = b.eval("(()=>{ const j=document.getElementById('chJump').getBoundingClientRect(), l=document.getElementById('chLog').getBoundingClientRect(); return {jb:j.bottom, lb:l.bottom, jl:j.left, ll:l.left, jr:j.right, lr:l.right}; })()")
        self.assertLessEqual(box["jb"], box["lb"] + 1)
        self.assertGreaterEqual(box["jl"], box["ll"])
        self.assertLessEqual(box["jr"], box["lr"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
