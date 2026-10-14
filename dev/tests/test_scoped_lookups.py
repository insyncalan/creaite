"""BL-302 and BL-303 (fix-v18-typecheck-bugs), two defects BL-231's type check found. A real browser against the real live server.

- BL-303: the peek's popups looked up their own parts with $(sel, el) and $$(sel, el), but $ and $$ ignored `el` and searched
  the whole page. They now take an optional root (core/dom.js), so a popup finds only its own parts, even when the page has
  a matching element elsewhere (a decoy below, put ahead of the popup in the page's order or after it).
- BL-302: Settings' old list manager called savePeople, removed by BL-55. Its people branch is gone: a data-mg button for
  people is ignored, never a ReferenceError.

Run: python3 dev/tests/test_scoped_lookups.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_peek_fixes import FixCase  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from split_dashboard import readable_page  # noqa: E402

DECOY = ("(()=>{ const d=document.createElement('div'); d.id='decoy';"
         " d.innerHTML='<input class=\"pkq\"><button class=\"pkopt\">Decoy</button><div class=\"pkerr\"></div>';"
         " document.body.prepend(d); })()")
IN_POP = "!!(document.activeElement&&document.activeElement.closest('.pkpop'))"


class ScopedLookups(FixCase):
    """BL-303: each popup lookup stays inside the popup."""

    def test_the_helpers_take_a_root(self):
        b = self.b
        b.eval(DECOY)
        b.eval("(()=>{ const s=document.createElement('section'); s.id='inner'; s.innerHTML='<i class=\"pkq\"></i><i class=\"pkq\"></i>'; document.body.appendChild(s); })()")
        self.assertEqual(b.eval("$('.pkq').tagName"), "INPUT")                                       # no root: the page
        self.assertEqual(b.eval("$('.pkq',document.getElementById('inner')).tagName"), "I")          # a root: only inside it
        self.assertEqual(b.eval("$$('.pkq').length"), 3)
        self.assertEqual(b.eval("$$('.pkq',document.getElementById('inner')).length"), 2)
        self.assertEqual(b.eval("$('.none',document.getElementById('inner'))"), None)

    def test_a_searchable_list_uses_its_own_search_box_and_options(self):
        b = self.b
        self.open()
        b.eval(DECOY)
        self.chip("o")
        self.assertTrue(b.eval("document.activeElement===document.querySelector('.pkpop .pkq')"))   # its own box has focus
        self.assertEqual(self.typed("Zed Quill")[0], "New person “Zed Quill”…")                      # and filters as typed
        b.eval("document.querySelector('.pkpop .pkq').dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowDown',bubbles:true}))")
        self.assertTrue(b.eval(IN_POP))                                                              # an option in the popup
        self.assertTrue(b.eval("document.activeElement.classList.contains('pkopt')"))
        b.eval("document.activeElement.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowUp',bubbles:true}))")
        self.assertTrue(b.eval("document.activeElement===document.querySelector('.pkpop .pkq')"))   # back up to its own box
        self.assertEqual(b.eval("document.querySelector('#decoy .pkq').value"), "")
        self.assertEqual(b.errors, [])

    def test_a_bad_date_is_explained_in_its_own_popup(self):
        b = self.b
        self.open()
        b.eval(DECOY)
        b.click('#panel [data-pkp="due"]')
        b.wait("document.querySelector('.pkpop .pkdt')")
        self.assertTrue(b.eval(IN_POP))                                                              # a day in the popup
        b.click(".pkpop .pkdt")
        b.type("the 45th")
        b.key("Enter")
        self.assertIn("Use DD-MM-YYYY", b.eval("document.querySelector('.pkpop .pkerr').textContent"))
        self.assertEqual(b.eval("document.querySelector('#decoy .pkerr').textContent"), "")
        self.assertEqual(b.errors, [])

    def test_the_new_workstream_form_reads_only_its_own_fields(self):
        b = self.b
        self.open()
        b.eval("PK.det[pkCid()]=true; pkDraw()")
        self.chip("ws")
        self.typed("Reporting")
        self.option("Add “Reporting”")
        b.wait("document.querySelector('.pkws')")
        # a field of the same kind elsewhere on the page (as the edit panel's own New workstream box has), after the form
        b.eval("(()=>{ const i=document.createElement('input'); i.id='decoyWs'; i.dataset.wsn='name'; i.value='Decoy'; document.body.appendChild(i); })()")
        b.eval("document.querySelector('.pkws [data-wsn=\"name\"]').value=''; document.querySelector('.pkws [data-wsf=\"add\"]').click()")
        self.assertEqual(b.eval("document.querySelector('.pkws .pkerr').textContent"), "Give the workstream a name.")
        b.pump(0.3)
        self.assertEqual(b.eval("PKS.length"), 0)
        self.assertNotIn("Decoy", b.eval("wsFor('ABC')"))
        self.assertEqual(b.errors, [])

    def test_no_lookup_in_the_panel_passes_a_root_the_helpers_ignore(self):
        src = readable_page()
        self.assertNotIn("a latent BUG (BL-231 step 3)", src)
        self.assertNotIn("a latent BUG found by BL-231 step 3", src)


class OldListManager(FixCase):
    """BL-302: the old list manager's people branch called savePeople, defined nowhere since BL-55."""

    def test_a_people_button_on_the_old_manager_is_ignored_not_an_error(self):
        b = self.b
        b.eval("go('settings')")
        b.wait("VIEW==='settings'&&document.getElementById('settingsBody').children.length")
        hidden = b.eval("JSON.stringify(D.people||{})")
        b.eval("(()=>{ const x=document.createElement('button'); x.id='oldMg'; x.dataset.mg='hide'; x.dataset.kind='people'; x.dataset.n='Sara Example';"
               " document.getElementById('settingsBody').appendChild(x); x.click(); })()")
        b.pump(0.3)
        self.assertEqual(b.errors, [])
        self.assertEqual(b.eval("JSON.stringify(D.people||{})"), hidden)


if __name__ == "__main__":
    unittest.main()
