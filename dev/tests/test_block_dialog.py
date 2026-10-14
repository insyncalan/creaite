"""BL-256: the Dialog building block (dev/COMPONENTS.md §3), first used by Close the day (BL-295). A modal on the native <dialog>:
named by its heading, Esc asks its owner to close it, focus goes back to whatever opened it, a scrim click closes it only when
nothing is typed, and its text is escaped. (Focus to the first control is checked through Close the day, test_close_day_card.)

Run: python3 dev/tests/test_block_dialog.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

# A fixture: an opener button and a box; draw(open, dirty) mounts the Dialog as its owner would, and onClose redraws it closed.
MOUNT = """(()=>{ const box=document.createElement('div'); box.id='dlgFix'; document.body.prepend(box);
  const opener=document.createElement('button'); opener.id='dlgOpener'; opener.textContent='Open'; document.body.prepend(opener);
  window.__closes=0;
  window.__draw=(open,dirty)=>mount(Dialog,{open,dirty,labelledBy:'fxH',id:'fxDlg',class:'fxdlg',children:'<b>Hello</b>',
    onClose:()=>{ window.__closes++; window.__draw(false,dirty); }},box);
  opener.focus(); window.__draw(true,false); return true; })()"""


class DialogBlock(LiveBrowserCase):
    shared_server = True        # it only reads

    def setUp(self):
        super().setUp()
        self.b.eval(MOUNT)
        self.b.wait("document.getElementById('fxDlg').open")

    def test_it_opens_modal_and_is_named_by_its_heading(self):
        b = self.b
        self.assertEqual(b.eval("document.getElementById('fxDlg').getAttribute('aria-labelledby')"), "fxH")
        self.assertEqual(b.eval("document.getElementById('fxDlg').className"), "fxdlg")
        self.assertTrue(b.eval("document.getElementById('fxDlg').matches(':modal')"))

    def test_esc_asks_the_owner_and_focus_goes_back(self):
        b = self.b
        b.key("Escape")
        b.wait("!document.getElementById('fxDlg').open")
        self.assertEqual(b.eval("window.__closes"), 1)
        b.wait("document.activeElement && document.activeElement.id==='dlgOpener'")

    def test_a_scrim_click_closes_only_when_nothing_is_typed(self):
        b = self.b
        b.eval("window.__draw(true,true); true")                              # dirty: something typed
        for kind in ("mousePressed", "mouseReleased"):
            b.call("Input.dispatchMouseEvent", type=kind, x=5, y=5, button="left", clickCount=1)
        b.pump(0.1)
        self.assertTrue(b.eval("document.getElementById('fxDlg').open"))
        self.assertEqual(b.eval("window.__closes"), 0)
        b.eval("window.__draw(true,false); true")
        for kind in ("mousePressed", "mouseReleased"):
            b.call("Input.dispatchMouseEvent", type=kind, x=5, y=5, button="left", clickCount=1)
        b.wait("!document.getElementById('fxDlg').open")
        self.assertEqual(b.eval("window.__closes"), 1)

    def test_its_text_is_escaped(self):
        b = self.b
        self.assertEqual(b.eval("document.getElementById('fxDlg').textContent"), "<b>Hello</b>")
        self.assertIsNone(b.eval("document.querySelector('#fxDlg b')"))


if __name__ == "__main__":
    unittest.main()
