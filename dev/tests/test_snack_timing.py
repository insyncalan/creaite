"""BL-215: the Undo message stays long enough and waits while you are on it; ⌘Z (Ctrl+Z) in Work undoes the last change.

Run: python3 dev/tests/test_snack_timing.py   (needs Google Chrome; skipped otherwise)
A real browser and server on the sample data. The timings are real: an Undo message is still there after 8 seconds and gone by
about 10; a plain one goes after 5; the pointer over it or focus in it holds it, leaving starts the full time again; Esc hides it.
"""
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

ON = "document.getElementById('snack').classList.contains('on')"


class SnackTiming(LiveBrowserCase):
    shared_server = True        # the timing tests change nothing; the Work test undoes its own change

    def setUp(self):
        super().setUp()
        self.b.call("Emulation.setFocusEmulationEnabled", enabled=True)   # focus events as in a window that has focus

    def show(self, undo=True, text="Saved"):
        self.b.eval(f"window.UNDONE=0; snack({text!r}{', ()=>{ window.UNDONE++; }' if undo else ''})")
        self.b.wait(ON)
        return time.monotonic()

    def gone_within(self, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if not self.b.eval(ON):
                return True
            self.b.pump(0.1)
        return False

    def still_on_for(self, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if not self.b.eval(ON):
                return False
            self.b.pump(0.2)
        return True

    def test_an_undo_message_stays_at_least_8_seconds_and_goes_by_itself(self):
        t0 = self.show()
        self.assertTrue(self.still_on_for(8.2))
        self.assertTrue(self.gone_within(4))
        self.assertGreaterEqual(time.monotonic() - t0, 9.5)
        self.assertTrue(self.b.eval("[...document.styleSheets].some(ss=>[...ss.cssRules].some(r=>/\\.snack\\.mtimer::after/.test(r.selectorText||'')&&r.style.animationDuration==='10s'))"))

    def test_a_plain_message_stays_5_seconds(self):
        t0 = self.show(undo=False, text="Checking…")
        self.assertTrue(self.still_on_for(4.5))
        self.assertTrue(self.gone_within(3))
        self.assertGreaterEqual(time.monotonic() - t0, 4.8)

    def test_the_pointer_over_it_holds_it_and_leaving_restarts_the_clock(self):
        b = self.b
        self.show()
        r = b.eval("(()=>{ const r=document.getElementById('snackT').getBoundingClientRect(); return [r.x+r.width/2, r.y+r.height/2]; })()")
        b.call("Input.dispatchMouseEvent", type="mouseMoved", x=r[0], y=r[1])
        b.wait("document.getElementById('snack').classList.contains('held')")
        self.assertTrue(self.still_on_for(12))                              # past the 10 seconds: held
        self.assertEqual(b.eval("getComputedStyle(document.getElementById('snack'),'::after').animationPlayState"), "paused")
        b.call("Input.dispatchMouseEvent", type="mouseMoved", x=5, y=5)       # leave
        b.wait("!document.getElementById('snack').classList.contains('held')")
        t_leave = time.monotonic()
        self.assertTrue(self.still_on_for(8))                               # the full time again, not what was left
        self.assertTrue(self.gone_within(4))
        self.assertGreaterEqual(time.monotonic() - t_leave, 9.5)

    def test_focus_inside_holds_it_and_esc_hides_it_and_returns_focus(self):
        b = self.b
        b.eval("go('work')")
        b.wait("VIEW==='work'")
        b.eval("document.querySelector('#wtabs [data-t]').focus()")
        self.show()
        b.eval("document.getElementById('snackU').focus()")                 # as Tab reaching it would
        b.wait("document.getElementById('snack').classList.contains('held')")
        self.assertTrue(self.still_on_for(11))
        b.key("Escape")
        b.wait(f"!{ON}")
        self.assertEqual(b.eval("window.UNDONE"), 0)                        # Esc hides; it doesn't undo
        self.assertTrue(b.eval("document.activeElement.matches('#wtabs [data-t]')"))     # focus back where it came from
        self.assertEqual(b.eval("document.getElementById('snack').getAttribute('role')"), "status")

    def test_esc_hides_it_when_nothing_else_is_open_but_leaves_it_for_an_open_layer(self):
        b = self.b
        b.eval("go('today')")
        b.wait("VIEW==='today'")
        self.show()
        b.eval("document.body.focus()")
        b.key("Escape")
        b.wait(f"!{ON}")
        self.show()
        b.eval("openChat()")
        b.wait("document.getElementById('chat').classList.contains('on')")
        b.key("Escape")                                                     # closes the chat, not the message
        b.wait("!document.getElementById('chat').classList.contains('on')")
        self.assertTrue(b.eval(ON))
        b.key("Escape")                                                     # now there's nothing else: the message goes
        b.wait(f"!{ON}")

    def test_cmd_z_in_work_undoes_the_last_change_not_in_a_text_field(self):
        b = self.b
        b.eval("go('work')")
        b.wait("VIEW==='work'&&document.querySelector('#workTbl tr[data-row]')")
        self.show()
        b.eval("document.getElementById('workQ').focus()")
        b.key("z", modifiers=4)                                             # ⌘ in a text field: the field's own undo
        b.pump(0.3)
        self.assertEqual(b.eval("window.UNDONE"), 0)
        b.eval("document.getElementById('workQ').blur(); document.querySelector('#workTbl tr[data-row]').focus()")
        b.key("z", modifiers=4)
        b.wait("window.UNDONE===1")
        self.assertFalse(b.eval(ON))
        b.key("z", modifiers=2)                                             # Ctrl+Z: nothing left to undo says so
        b.wait("/Nothing to undo/.test(document.getElementById('snackT').textContent)")
        self.assertEqual(b.eval("window.UNDONE"), 1)

    def test_cmd_z_undoes_a_real_change_in_work(self):
        b = self.b
        b.eval("S.autoApply=true; WT='actions'; go('work'); HTMLSelectElement.prototype.showPicker=function(){}")
        b.wait("document.querySelector('#workTbl tr[data-row=\"ABC-A-002\"]')")
        b.click('#wlay [data-lay="list"]')
        before = next(r for r in self.v.rows("actions") if r["id"] == "ABC-A-002")["priority"]
        new = "Low" if before != "Low" else "High"
        cell = '#workTbl tr[data-row="ABC-A-002"] td[data-f="pr"]'
        b.eval("document.getElementById('snackT').textContent=''")
        b.click(cell)
        b.wait(f"document.querySelector('{cell} select')")
        b.eval(f"""(()=>{{ const s=document.querySelector('{cell} select'); s.value={new!r}; s.dispatchEvent(new Event('change',{{bubbles:true}})); }})()""")
        b.wait("document.getElementById('snackT').textContent!==''", 30)
        self.assertTrue(self._until(lambda: next(r for r in self.v.rows("actions") if r["id"] == "ABC-A-002")["priority"] == new))
        b.eval("document.activeElement&&document.activeElement.blur()")
        b.key("z", modifiers=4)
        self.assertTrue(self._until(lambda: next(r for r in self.v.rows("actions") if r["id"] == "ABC-A-002")["priority"] == before))

    def _until(self, fn, seconds=30):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if fn():
                return True
            self.b.pump(0.2)
        return False


if __name__ == "__main__":
    unittest.main(verbosity=2)
