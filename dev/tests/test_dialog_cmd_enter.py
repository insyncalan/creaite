"""#101 (ux): ⌘↵ (Ctrl+↵ off a Mac) presses the primary button of every dialog, by default, through the shared Dialog component.

Table-driven: each row opens one dialog, fills it, presses ⌘↵ and says which button must have been pressed (a spy on clicks
records it; nothing else runs). A required field left empty must not be saved (the button's own check shows its message), a
disabled button is never pressed, composition is ignored, a Cancel button is not a save, and Esc and Cancel still close.
Dialogs that opt out (cmdEnter={false}) are listed, and ⌘↵ presses nothing in them.

A real browser against the real live server.
Run: python3 dev/tests/test_dialog_cmd_enter.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

META = 4
RAILOPEN = "(()=>{const b=document.createElement('button');b.dataset.railcust='1';document.body.appendChild(b);b.click();b.remove();})()"
SPY = """window.__hits=[]; if(!window.__spy){ window.__spy=1; document.addEventListener('click',e=>{ const b=e.target.closest&&e.target.closest('button'); if(b&&window.__arm){ window.__hits.push(b.id||b.dataset.cdnext||b.textContent); if(b.closest('dialog')&&b.closest('form')) e.preventDefault(); } },true); }
window.__arm=true;"""

# id of the dialog, JS that opens it, JS that fills it validly, the button that ⌘↵ must press, JS that leaves a required field empty (or None)
ROWS = [
    ("boardDlg", "boardAsk({title:'Due date for ABC-A-001',hint:'x',date:'2030-01-01'})", None, "bdOk", None),
    ("boardDlg", "boardAsk({title:'Clear it?',hint:'x',clear:true})", None, "bdOk", None),
    ("personDlg", "askPerson({typed:''})", "document.getElementById('pd_name').value='Mia Hale'", "pdSave",
     "document.getElementById('pd_name').value=''"),
    ("genDlg", "(()=>{ shared.RUN=null; openDialog('genDlg'); })()", None, "genGo", None),
    ("railCust", RAILOPEN, None, "railCustDone", None),
]
OPT_OUT = ["cmdk", "inPrev", "searchPrev", "llDlg", "rvDlg", "deDlg", "prepDlg", "actDlg", "parchDlg"]


# Every dialog the page has, and what ⌘↵ does in it (the issue asks the test to list them all).
SAVES = {"boardDlg": "Move / Clear date / Withdraw", "personDlg": "Save", "genDlg": "Generate", "railCust": "Done",
         "newNoteDlg": "Make the note (the form's own submit; shared handler presses it)", "closeDlg": "Next / Close the day"}
# Not <dialog>s, and already ⌘↵ users through the page's one CMDENTER handler (core/fields.js; test_cmd_enter.py): the work-item peek,
# the project panel and its forms, the milestone editor, Movement's rebaseline form. The minutes view, the Chat, the Draft email's
# composer and the capture drawer keep their own ⌘↵ (send / finish) and are untouched.
EXEMPT = {"cmdk": "search box; its own ⌘↵ stages the highlighted command", "inPrev": "preview; the only button is Close",
          "searchPrev": "preview; the only button is Close", "llDlg": "Compare: a three-way choice (Merge / Keep as new) that must be clicked on purpose",
          "rvDlg": "bulk Approve (guarded; BL-133 preview before a large approval)", "deDlg": "draft email: nothing to save, Copy only",
          "prepDlg": "Prep popup: nothing to save", "actDlg": "Undo changes: destructive, clicked on purpose",
          "parchDlg": "Cancel them all and archive: destructive, clicked on purpose"}


class Cases(LiveBrowserCase):
    shared_server = True

    def open_(self, dlg, js):
        b = self.b
        b.eval(SPY)
        b.eval(f"window.__p=({js})", wait=False)
        b.wait(f"document.getElementById('{dlg}')&&document.getElementById('{dlg}').open")
        b.eval("window.__hits=[]")

    def hits(self):
        return self.b.eval("window.__hits")

    def shut(self, dlg):
        self.b.eval(f"window.__arm=false;(()=>{{const d=document.getElementById('{dlg}'); if(d&&d.open) d.close();}})()")
        self.b.wait(f"!document.getElementById('{dlg}').open")

    def test_every_dialog_is_listed(self):
        """Dialogs are drawn at load or on first use; those found at load, plus the ones the table names, must all be listed."""
        found = set(self.b.eval("[...document.querySelectorAll('dialog')].map(d=>d.id).filter(Boolean)"))
        listed = set(SAVES) | set(EXEMPT)
        self.assertEqual(sorted(found - listed), [], "a dialog with no entry: say whether ⌘↵ saves in it or why it is exempt")

    def test_table(self):
        for dlg, opener, fill, button, empty in ROWS:
            with self.subTest(dialog=dlg, opener=opener[:30]):
                self.open_(dlg, opener)
                if fill:
                    self.b.eval(fill)
                self.b.eval(f"document.querySelector('#{dlg} input,#{dlg} textarea,#{dlg} select')?.focus()")
                self.b.key("Enter", META)
                if self.b.eval(f"document.getElementById('{dlg}').open") and not self.hits():
                    self.fail(f"⌘↵ pressed nothing in {dlg}")
                if self.hits():
                    self.assertEqual(self.hits(), [button], f"⌘↵ in {dlg}")
                else:                                  # the date field's own Enter already saved (and closed)
                    self.assertFalse(self.b.eval(f"document.getElementById('{dlg}').open"))
                self.shut(dlg)

    def test_a_required_field_left_empty_is_not_saved(self):
        for dlg, opener, fill, button, empty in ROWS:
            if not empty:
                continue
            with self.subTest(dialog=dlg):
                self.open_(dlg, opener)
                self.b.eval(empty)
                self.b.eval(f"document.querySelector('#{dlg} input')?.focus()")
                self.b.key("Enter", META)
                self.assertTrue(self.b.eval(f"document.getElementById('{dlg}').open"), "stays open")
                self.assertTrue(self.b.eval("document.getElementById('pdErr').textContent.length>0"), "the button's own message")
                self.shut(dlg)

    def test_a_disabled_primary_is_never_pressed(self):
        self.open_("railCust", RAILOPEN)
        self.b.eval("document.getElementById('railCustIcons').focus(); document.getElementById('railCustDone').disabled=true")
        self.b.key("Enter", META)
        self.assertEqual(self.hits(), [])
        self.shut("railCust")

    def test_composition_and_plain_enter_and_cancel_do_nothing(self):
        self.open_("railCust", RAILOPEN)
        self.b.eval("""(()=>{ const d=document.getElementById('railCust'); d.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',metaKey:true,bubbles:true,isComposing:true})); })()""")
        self.assertEqual(self.hits(), [], "IME composition")
        self.b.eval("document.getElementById('railCustIcons').focus()")
        self.b.key("Enter")
        self.assertEqual(self.hits(), [], "plain Enter")
        self.b.eval("document.getElementById('railCustCancel').focus()")
        self.b.key("Enter", META)
        self.assertEqual([h for h in self.hits() if h == "railCustDone"], [], "from the Cancel button")
        self.shut("railCust")

    def test_multiline_field_saves_instead_of_adding_a_line(self):
        self.open_("genDlg", "openDialog('genDlg')")
        self.b.eval("const t=document.getElementById('genNote'); t.value='abc'; t.focus(); t.setSelectionRange(3,3)")
        self.b.key("Enter", META)
        self.assertEqual(self.hits(), ["genGo"])
        self.assertEqual(self.b.eval("document.getElementById('genNote').value"), "abc")
        self.shut("genDlg")

    def test_esc_still_closes(self):
        self.open_("boardDlg", "boardAsk({title:'x',hint:'',date:'2030-01-01'})")
        self.b.key("Escape")
        self.b.wait("!document.getElementById('boardDlg').open")
        self.assertEqual(self.b.eval("window.__hits.length"), 0)

    def test_opted_out_dialogs_press_nothing(self):
        b = self.b
        b.eval(SPY)
        for dlg in OPT_OUT:
            el = b.eval(f"!!document.getElementById('{dlg}')")
            if not el:
                continue                      # made on first use
            b.eval(f"window.__hits=[]; document.getElementById('{dlg}').showModal()")
            b.eval(f"(()=>{{const d=document.getElementById('{dlg}'); d.dispatchEvent(new KeyboardEvent('keydown',{{key:'Enter',metaKey:true,bubbles:true}}));}})()")
            self.assertEqual(self.hits(), [], dlg)
            b.eval(f"window.__arm=false; document.getElementById('{dlg}').close()")
            b.eval("window.__arm=true")


if __name__ == "__main__":
    unittest.main()
