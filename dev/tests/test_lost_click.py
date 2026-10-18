"""insyncalan/creaite-plan#85: a click is not lost while the page redraws its data.

Run: python3 dev/tests/test_lost_click.py   (needs Google Chrome; skipped otherwise)
A real mouse press on a Work row, then the list is redrawn (as a data refresh does, BL-327's boot refresh, BL-253's events),
then the real release. The browser sends the click to the nearest ancestor the two share when the pressed node has gone, so
the row's handler used to see no row and the click was lost. The click must act on the row by its key (data-row).
Also: a plain click still selects once (and is the browser's own click, not a made one), a press on one row released on another
is not a click on either, a made click is delivered once even if the browser also sends one, and the click after it (Enter on a
focused button) is not swallowed.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

ROW = '#workTbl tr[data-row="ABC-A-002"] td[data-f="due"]'   # a cell that stays clear of the collapsed rail at 900 px
REDRAW = "renderWork()"
# counts every click that reaches a handler registered after the page's own (so the swallow has already run): the row, or the probe button
COUNT = """window.__clicks=[]; document.addEventListener("click",e=>{ if(e.target.closest&&(e.target.closest('[data-row="ABC-A-002"]')||e.target.closest("#probeBtn")))
  window.__clicks.push((e.isTrusted?"trusted":"made")+":"+(e.target.id||(e.target.matches("tr")?"row":"cell"))); },true)"""
PROBE = """(()=>{ const b=document.createElement("button"); b.id="probeBtn"; b.textContent="probe"; b.style.cssText="position:fixed;left:4px;bottom:4px;z-index:99999";
  document.body.appendChild(b); b.focus(); return document.activeElement===b; })()"""
# the page's own click handlers run after this one (a capture listener on window runs first), so it sees every click the browser sends, swallowed or not
TRUSTED = "window.__trusted=[]; window.addEventListener('click',e=>{ if(e.isTrusted) window.__trusted.push(e.target.id||e.target.tagName) },true)"
MODS = """window.__mods=[]; document.addEventListener("click",e=>{ if(!e.isTrusted&&e.target.closest&&e.target.closest('[data-row="ABC-A-002"]'))
  window.__mods.push([e.ctrlKey,e.shiftKey,e.altKey,e.metaKey].map(Number).join("")); },true)"""
REPLACE_CELL = "(()=>{ const t=document.querySelector(%r); t.replaceWith(t.cloneNode(true)); })()" % ROW   # the row stays, the pressed cell is replaced
REINSERT_ROW = "(()=>{ const r=document.querySelector(%r).closest('tr'), p=r.parentNode, n=r.nextSibling; r.remove(); p.insertBefore(r,n); })()" % ROW   # a keyed reorder
HOLD = "window.__held=[]; window.__st=window.setTimeout; window.setTimeout=(f,t)=>{ window.__held.push(f); return 0 }"
RELEASE_HELD = "window.setTimeout=window.__st; const h=window.__held; window.__held=[]; h.forEach(f=>f())"


class LostClick(LiveBrowserCase):
    width, height = 1640, 1000

    def open_list(self):
        b = self.b
        b.eval("WT='actions'; go('work')")
        b.wait("document.querySelector('#workTbl tr[data-row]')")
        b.click('#wlay [data-lay="list"]')
        b.eval("setOf('st').clear(); workChanged()")
        b.wait("document.querySelector(%r)" % ROW)
        b.eval("HL.clear(); hlPaint()")
        return b

    def press_redraw_release(self, redraw=REDRAW):
        b = self.b
        pos = b.box(ROW)
        for kind in ("mouseMoved", "mousePressed"):
            b.call("Input.dispatchMouseEvent", type=kind, x=pos["x"], y=pos["y"], button="left", buttons=1, clickCount=1)
        b.eval("window.__old=document.querySelector(%r)" % ROW)
        b.eval(redraw)
        gone = b.eval("!document.contains(window.__old)")
        b.call("Input.dispatchMouseEvent", type="mouseReleased", x=pos["x"], y=pos["y"], button="left", buttons=0, clickCount=1)
        b.pump(0.1)
        return gone

    def press(self, pos, modifiers=0):
        for kind in ("mouseMoved", "mousePressed"):
            self.b.call("Input.dispatchMouseEvent", type=kind, x=pos["x"], y=pos["y"], button="left", buttons=1, clickCount=1, modifiers=modifiers)

    def release(self, pos, modifiers=0):
        self.b.call("Input.dispatchMouseEvent", type="mouseReleased", x=pos["x"], y=pos["y"], button="left", buttons=0, clickCount=1, modifiers=modifiers)
        self.b.pump(0.1)

    def test_click_during_redraw_lands_on_the_row(self):
        b = self.open_list()
        self.assertTrue(self.press_redraw_release(), "the redraw should replace the pressed row")
        self.assertTrue(b.eval("HL.has('ABC-A-002')"), "the click on the row was lost by the redraw")

    def test_click_during_a_second_redraw_still_lands_once(self):
        b = self.open_list()
        self.press_redraw_release(REDRAW + ";" + REDRAW)
        self.assertEqual(b.eval("[...HL.keys()]"), ["ABC-A-002"])

    def test_plain_click_unchanged(self):
        b = self.open_list()
        b.click(ROW)
        self.assertEqual(b.eval("[...HL.keys()]"), ["ABC-A-002"])

    def test_press_on_one_row_release_on_another_is_not_a_click(self):
        b = self.open_list()
        other_id = b.eval("[...document.querySelectorAll('#workTbl tr[data-row]')].map(r=>r.dataset.row).find(i=>i!=='ABC-A-002')")
        other = '#workTbl tr[data-row="%s"] td[data-f="due"]' % other_id
        a, o = b.box(ROW), b.box(other)
        # the release really is over the other row, at this width (not behind the rail or off the table)
        self.assertEqual(b.eval("document.elementFromPoint(%f,%f).closest('[data-row]').dataset.row" % (o["x"], o["y"])), other_id)
        self.assertNotEqual(a["y"], o["y"])
        b.call("Input.dispatchMouseEvent", type="mouseMoved", x=a["x"], y=a["y"], button="none")
        b.call("Input.dispatchMouseEvent", type="mousePressed", x=a["x"], y=a["y"], button="left", buttons=1, clickCount=1)
        b.call("Input.dispatchMouseEvent", type="mouseMoved", x=o["x"], y=o["y"], button="left", buttons=1)
        b.eval(REDRAW)
        b.eval(COUNT)
        b.call("Input.dispatchMouseEvent", type="mouseReleased", x=o["x"], y=o["y"], button="left", buttons=0, clickCount=1)
        b.pump(0.1)
        self.assertEqual(b.eval("[...HL.keys()]"), [])
        self.assertEqual(b.eval("window.__clicks"), [])

    def test_plain_click_is_the_browsers_own_one_click(self):
        b = self.open_list()
        b.eval(COUNT)
        b.click(ROW)
        b.pump(0.1)
        self.assertEqual(b.eval("window.__clicks"), ["trusted:cell"], "a click on a live row must reach its handlers once, as the browser sent it")

    def test_a_click_made_for_a_lost_one_is_delivered_once_and_a_browser_click_with_it_is_swallowed(self):
        b = self.open_list()
        pos = b.box(ROW)
        for kind in ("mouseMoved", "mousePressed"):
            b.call("Input.dispatchMouseEvent", type=kind, x=pos["x"], y=pos["y"], button="left", buttons=1, clickCount=1)
        b.eval("window.__old=document.querySelector(%r)" % ROW)
        b.eval(REDRAW)
        self.assertTrue(b.eval("!document.contains(window.__old)"))
        b.eval(COUNT)
        b.eval(HOLD)                 # keep the made click waiting, as if the browser's own click arrived first
        b.call("Input.dispatchMouseEvent", type="mouseReleased", x=pos["x"], y=pos["y"], button="left", buttons=0, clickCount=1)
        self.assertTrue(b.eval(PROBE))
        b.key("Enter")               # a trusted click, standing in for one the browser sends with the release (Chrome here sends none)
        self.assertEqual(b.eval("window.__clicks"), [], "the browser's click must be swallowed while a made one is due")
        b.eval(RELEASE_HELD)
        b.pump(0.1)
        self.assertEqual(b.eval("window.__clicks"), ["made:cell"])
        self.assertEqual(b.eval("[...HL.keys()]"), ["ABC-A-002"])

    def test_the_click_after_a_made_one_is_not_swallowed(self):
        """Enter on a focused button after a recovered lost click used to be swallowed (the flag was never cleared)."""
        b = self.open_list()
        self.assertTrue(self.press_redraw_release())
        self.assertTrue(b.eval("HL.has('ABC-A-002')"))
        b.eval(COUNT)
        self.assertTrue(b.eval(PROBE))
        b.key("Enter")
        self.assertEqual(b.eval("window.__clicks"), ["trusted:probeBtn"], "Enter on a focused button was swallowed")
        b.eval("window.__clicks=[]")
        b.call("Input.dispatchKeyEvent", type="keyDown", key=" ", code="Space", windowsVirtualKeyCode=32, text=" ")
        b.call("Input.dispatchKeyEvent", type="keyUp", key=" ", code="Space", windowsVirtualKeyCode=32)
        b.pump(0.1)
        self.assertEqual(b.eval("window.__clicks"), ["trusted:probeBtn"], "Space on a focused button was swallowed")

    def test_press_on_one_cell_release_on_another_of_the_same_row_clicks_the_row(self):
        b = self.open_list()
        other = '#workTbl tr[data-row="ABC-A-002"] td[data-f="t"]'
        a, o = b.box(ROW), b.box(other)
        self.assertNotEqual(a["x"], o["x"])
        self.assertEqual(b.eval("document.elementFromPoint(%f,%f).closest('[data-row]').dataset.row" % (o["x"], o["y"])), "ABC-A-002")
        b.call("Input.dispatchMouseEvent", type="mouseMoved", x=a["x"], y=a["y"], button="none")
        b.call("Input.dispatchMouseEvent", type="mousePressed", x=a["x"], y=a["y"], button="left", buttons=1, clickCount=1)
        b.call("Input.dispatchMouseEvent", type="mouseMoved", x=o["x"], y=o["y"], button="left", buttons=1)
        b.eval(REDRAW)
        b.eval(COUNT)
        b.call("Input.dispatchMouseEvent", type="mouseReleased", x=o["x"], y=o["y"], button="left", buttons=0, clickCount=1)
        b.pump(0.1)
        self.assertEqual(b.eval("window.__clicks"), ["made:row"], "the click should land on the row, where the browser would put it, not on the release cell")

    def test_the_pressed_cell_replaced_inside_a_row_that_stays_is_still_a_click(self):
        b = self.open_list()
        pos = b.box(ROW)
        b.eval(TRUSTED)
        b.eval(COUNT)
        self.press(pos)
        b.eval(REPLACE_CELL)
        self.assertTrue(b.eval("document.querySelector(%r).closest('tr').isConnected" % ROW), "the row should stay")
        self.release(pos)
        self.assertEqual(b.eval("window.__trusted"), [], "the browser sends no click here; if it does, this case needs no help")
        self.assertEqual(b.eval("window.__clicks"), ["made:cell"])
        self.assertEqual(b.eval("[...HL.keys()]"), ["ABC-A-002"])

    def test_the_row_taken_out_and_put_back_is_still_a_click(self):
        b = self.open_list()
        pos = b.box(ROW)
        b.eval(TRUSTED)
        b.eval(COUNT)
        self.press(pos)
        b.eval(REINSERT_ROW)
        self.assertTrue(b.eval("document.querySelector(%r).isConnected" % ROW))
        self.release(pos)
        self.assertEqual(b.eval("window.__trusted"), [], "the browser sends no click here; if it does, this case needs no help")
        self.assertEqual(b.eval("window.__clicks"), ["made:cell"])
        self.assertEqual(b.eval("[...HL.keys()]"), ["ABC-A-002"])

    def test_a_context_menu_press_is_no_click(self):
        """Ctrl+click on a Mac is a context menu, and the browser sends no click for it."""
        b = self.open_list()
        pos = b.box(ROW)
        b.eval(COUNT)
        self.press(pos)
        b.eval("document.querySelector(%r).dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true}))" % ROW)
        b.eval("HL.clear(); hlPaint()")   # the row's own context menu handler selects the row; only a click after it would count here
        b.eval(REDRAW)
        self.release(pos)
        self.assertEqual(b.eval("window.__clicks"), [])
        self.assertEqual(b.eval("[...HL.keys()]"), [])

    def test_a_second_redraw_before_the_made_click_is_sent_still_lands_once(self):
        b = self.open_list()
        pos = b.box(ROW)
        self.press(pos)
        b.eval(REDRAW)
        b.eval(COUNT)
        b.eval(HOLD)                 # the made click waits ...
        b.call("Input.dispatchMouseEvent", type="mouseReleased", x=pos["x"], y=pos["y"], button="left", buttons=0, clickCount=1)
        b.eval("window.__old=document.querySelector(%r)" % ROW)
        b.eval(REDRAW)               # ... and the page redraws again before it goes out
        self.assertTrue(b.eval("!document.contains(window.__old)"))
        b.eval(RELEASE_HELD)
        b.pump(0.1)
        self.assertEqual(b.eval("window.__clicks"), ["made:cell"])
        self.assertEqual(b.eval("[...HL.keys()]"), ["ABC-A-002"])

    def test_a_new_press_clears_a_made_click_still_waiting(self):
        """If the flag of an earlier made click were left set, the next plain click would be swallowed."""
        b = self.open_list()
        pos = b.box(ROW)
        self.press(pos)
        b.eval(REDRAW)
        b.eval(HOLD)
        b.call("Input.dispatchMouseEvent", type="mouseReleased", x=pos["x"], y=pos["y"], button="left", buttons=0, clickCount=1)
        b.eval("window.setTimeout=window.__st; window.__held=[]")   # the made click never goes out, so only a new press can clear the flag
        b.eval("HL.clear(); hlPaint()")
        b.eval(COUNT)
        b.click(ROW)
        b.pump(0.1)
        self.assertEqual(b.eval("window.__clicks"), ["trusted:cell"], "the click after a new press was swallowed")
        self.assertEqual(b.eval("[...HL.keys()]"), ["ABC-A-002"])

    def test_the_made_click_keeps_the_modifier_keys(self):
        b = self.open_list()
        b.eval(MODS)
        for mods, want in ((8, "0100"), (4, "0001"), (1, "0010"), (2, "1000")):    # shift, meta, alt, ctrl (CDP: Alt 1, Ctrl 2, Meta 4, Shift 8)
            with self.subTest(modifiers=mods):
                b.eval("HL.clear(); hlPaint()")
                b.eval("window.__mods=[]")
                pos = b.box(ROW)
                self.press(pos)
                b.eval(REDRAW)
                self.release(pos, modifiers=mods)
                self.assertEqual(b.eval("window.__mods"), [want])


class LostClick900(LostClick):
    """The same at 900 px wide (desktop and 900 only)."""
    width = 900


if __name__ == "__main__":
    unittest.main()
