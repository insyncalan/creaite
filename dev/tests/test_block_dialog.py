"""BL-256: the Dialog building block (dev/COMPONENTS.md §3), first used by Close the day (BL-295). A modal on the native <dialog>:
named by its heading, Esc asks its owner to close it, focus goes back to whatever opened it, a scrim click closes it only when
nothing is typed, and its text is escaped. (Focus to the first control is checked through Close the day, test_close_day_card.)
BL-316: a dialog opened by old code (`open` left out): openDialog opens it at once with focus where asked, Esc and the scrim
close it (not once something is typed), focus goes back, and the Prep popup's swap to modeless and back is not a close.

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


# BL-316: a dialog opened by old code: drawn once with `open` left out, opened by openDialog() and closed by Esc, the scrim or close().
OPENED = """(()=>{ const box=document.createElement('div'); box.id='dlgFix2'; document.body.prepend(box);
  const opener=document.createElement('button'); opener.id='dlgOpener2'; opener.textContent='Open'; document.body.prepend(opener);
  window.__closed=0;
  mount(Dialog,{id:'fxOld',ariaLabel:'Search or jump to',onClose:()=>window.__closed++},box);
  const d=document.getElementById('fxOld');                     // its fields, as old code fills a drawn dialog by id
  ['fxA','fxB'].forEach(id=>{ const i=document.createElement('input'); i.id=id; i.setAttribute('aria-label',id); d.append(i); });
  opener.focus(); return true; })()"""


class DialogOpenedByOldCode(LiveBrowserCase):
    shared_server = True        # it only reads

    def setUp(self):
        super().setUp()
        self.b.eval(OPENED)

    def click_scrim(self):
        for kind in ("mousePressed", "mouseReleased"):
            self.b.call("Input.dispatchMouseEvent", type=kind, x=5, y=5, button="left", clickCount=1)

    def test_open_dialog_opens_it_at_once_named_by_its_label_with_focus_where_asked(self):
        b = self.b
        self.assertTrue(b.eval("openDialog('fxOld',{focus:'#fxB'}).open"))       # at once, as showModal() was
        self.assertTrue(b.eval("document.getElementById('fxOld').matches(':modal')"))
        self.assertEqual(b.eval("document.getElementById('fxOld').getAttribute('aria-label')"), "Search or jump to")
        self.assertEqual(b.eval("document.activeElement.id"), "fxB")
        b.eval("closeDialog('fxOld'); true")
        b.wait("window.__closed===1")
        b.wait("document.activeElement && document.activeElement.id==='dlgOpener2'")
        b.eval("openDialog('fxOld'); true")                                       # no field given: the first control
        self.assertEqual(b.eval("document.activeElement.id"), "fxA")

    def test_esc_closes_it_and_focus_goes_back(self):
        b = self.b
        b.eval("openDialog('fxOld'); true")
        b.key("Escape")
        b.wait("!document.getElementById('fxOld').open")
        b.wait("window.__closed===1")
        b.wait("document.activeElement && document.activeElement.id==='dlgOpener2'")

    def test_a_scrim_click_closes_it_unless_something_was_typed_since_it_opened(self):
        b = self.b
        b.eval("openDialog('fxOld'); true")
        b.type("x")                                                              # typed in the first field
        self.click_scrim()
        b.pump(0.1)
        self.assertTrue(b.eval("document.getElementById('fxOld').open"))
        b.eval("closeDialog('fxOld'); true")
        b.wait("window.__closed===1")
        b.eval("openDialog('fxOld'); true")                                       # opened again: nothing typed yet
        self.click_scrim()
        b.wait("!document.getElementById('fxOld').open")

    def test_a_swap_to_modeless_and_back_is_not_a_close(self):
        b = self.b
        b.eval("openDialog('fxOld'); true")
        b.eval("(()=>{ const d=document.getElementById('fxOld'); d.close(); openDialog(d,{modal:false,focus:false}); return true; })()")
        b.pump(0.1)
        self.assertTrue(b.eval("document.getElementById('fxOld').open && !document.getElementById('fxOld').matches(':modal')"))
        b.eval("(()=>{ const d=document.getElementById('fxOld'); d.close(); openDialog(d,{focus:false}); return true; })()")
        b.pump(0.1)
        self.assertTrue(b.eval("document.getElementById('fxOld').matches(':modal')"))
        self.assertEqual(b.eval("window.__closed"), 0)                            # neither close was a close
        b.key("Escape")
        b.wait("window.__closed===1")
        b.wait("document.activeElement && document.activeElement.id==='dlgOpener2'")   # the first opener, kept through the swap


if __name__ == "__main__":
    unittest.main()
