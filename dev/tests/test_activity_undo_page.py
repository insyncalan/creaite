"""BL-164: Activity's type icons, search and filters, and undoing several past changes, part 2 of 3 (the Activity page, entries and search; the fixture is in activity_undo_support.py).

Run: python3 dev/tests/test_activity_undo_page.py   (the browser tests need Google Chrome; skipped otherwise)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from activity_undo_support import (  # noqa: E402
    ActivityBase,
    META,
    SHIFT,
)


class ActivityPage(ActivityBase):
    """The page: icons, search, chips and selecting."""

    def test_each_entry_has_its_type_icon_and_name(self):
        b = self.b
        self.go_activity()
        icons = b.eval("""[...document.querySelectorAll('#actTbl tbody tr .acticon')].map(s=>[s.getAttribute('aria-label'),s.dataset.tip,!!s.querySelector('svg')])""")
        names = {x[0] for x in icons}
        self.assertTrue({"Action", "Risk"} <= names, names)
        self.assertTrue(all(x[0] == x[1] and x[2] for x in icons))
        # every kind has an icon and a name
        kinds = b.eval("ACTKINDS.map(k=>[k[0],k[1],!!ICONS[k[2]]])")
        self.assertTrue(all(k[2] for k in kinds), kinds)
        self.assertEqual([k[1] for k in kinds][:3], ["Action", "Risk", "Issue"])

    def test_search_by_id_text_project_person_and_date_with_the_count_and_clear(self):
        b = self.b
        self.go_activity()
        total = b.eval("document.querySelectorAll('#actTbl tbody tr').length")
        self.assertEqual(self.count(), f"{total} of {total}")
        b.eval("document.getElementById('actQ').focus()")
        b.type("ABC-A-002")
        b.wait("document.querySelectorAll('#actTbl tbody tr').length<" + str(total))
        self.assertTrue(all("ABC-A-002" in r for r in self.rows()), self.rows())
        self.assertRegex(self.count(), rf"^\d+ of {total}$")
        for q, must in (("uat room", "Book the UAT room"), ("example programme", "ABC-"), ("omar", "Omar Ali"),
                        ("sara", "Sara Example")):          # a project matches by its name; its lines carry its code
            b.eval(f"document.getElementById('actQ').value={json.dumps(q)}; document.getElementById('actQ').dispatchEvent(new Event('input',{{bubbles:true}}))")
            self.assertTrue(self.rows() and all(must.lower() in r.lower() for r in self.rows()), (q, self.rows()))
        when = b.eval("fd(ACT[0].at.slice(0,10))")
        b.eval(f"document.getElementById('actQ').value={json.dumps(when)}; document.getElementById('actQ').dispatchEvent(new Event('input',{{bubbles:true}}))")
        self.assertTrue(self.rows())
        b.eval("document.getElementById('actQ').value='zzzz nothing'; document.getElementById('actQ').dispatchEvent(new Event('input',{bubbles:true}))")
        empty = b.eval("document.getElementById('actTbl').textContent")
        self.assertIn("zzzz nothing", empty)                                                  # says what was searched
        b.click("#actTbl [data-actclear]")
        self.assertEqual(self.count(), f"{total} of {total}")
        self.assertEqual(b.eval("document.getElementById('actQ').value"), "")

    def test_slash_focuses_the_search_only_on_activity(self):
        b = self.b
        self.go_activity()
        b.eval("document.activeElement.blur()")
        b.key("/")
        self.assertEqual(b.eval("document.activeElement.id"), "actQ")
        self.assertFalse(b.eval("document.getElementById('chat').classList.contains('on')"))
        b.eval("go('today')")
        b.eval("document.activeElement.blur()")
        b.key("/")
        b.wait("document.getElementById('chat').classList.contains('on')")                  # elsewhere / is still ask creaite

    def test_type_chips_dates_and_the_address_round_trip(self):
        b = self.b
        self.go_activity()
        # BL-316: Kind is the FilterBar block's list (was a row of toggles)
        b.click("#actFunnel")                                      # #229: the kind filter is the funnel's field list
        b.wait("!!document.querySelector('#actPick [role=option]')")
        b.click('#actPick [role=option]:has(input[value="Risk"])')
        b.wait("(shared.ACTF.types||[]).includes('Risk')")
        self.assertTrue(all("ABC-004" in r for r in self.rows()), self.rows())
        self.assertEqual(b.eval("document.querySelector('#actPick [role=option]:has(input[value=\"Risk\"])').getAttribute('aria-selected')"), "true")
        b.key("Escape")
        b.eval("document.getElementById('actQ').value='data'; document.getElementById('actQ').dispatchEvent(new Event('input',{bubbles:true}))")
        self.assertIn("q=data", b.eval("location.hash"))
        self.assertIn("type=Risk", b.eval("location.hash"))
        h = b.eval("location.hash")
        # open an item and come back: the filters are kept
        b.click('#actTbl a[data-open]')
        b.wait("document.getElementById('panel').classList.contains('on')")
        b.key("Escape")
        b.wait("!document.getElementById('panel').classList.contains('on')")
        self.assertEqual(b.eval("document.getElementById('actQ').value"), "data")
        # leave and come back with Back
        b.eval("go('today')")
        b.eval("history.back()")
        b.wait("VIEW==='activity'")
        b.wait("document.getElementById('actQ').value==='data'")
        self.assertTrue(all("ABC-004" in r for r in self.rows()))
        # a fresh load of the address
        b.goto(self.base + "/" + h)
        b.wait("typeof go==='function' && LIVE && VIEW==='activity'")
        b.wait("document.getElementById('actQ').value==='data'")
        self.assertTrue(all("ABC-004" in r for r in self.rows()))
        # dates: from after everything shows nothing, and says so
        b.eval("ACTF={}; renderActivity()")
        b.click("#actFunnel")                                    # the funnel's picker: When is two date boxes
        b.click('#actPick .fpf[data-fpk="when"]')
        b.wait("!!document.querySelector('#actPick input[data-when=from]')")
        b.eval("const i=document.querySelector('#actPick input[data-when=from]'); i.value='01-01-2099'; i.dispatchEvent(new Event('change',{bubbles:true}))")
        self.assertIn("Nothing matches", b.eval("document.getElementById('actTbl').textContent"))
        self.assertIn("from=2099-01-01", b.eval("location.hash"))

    def test_selecting_with_cmd_ctrl_shift_and_esc(self):
        b = self.b
        self.go_activity()
        rows = b.eval("[...document.querySelectorAll('#actTbl tbody tr[data-row]')].map(t=>t.dataset.row)")
        self.assertGreaterEqual(len(rows), 5)
        cell = lambda r: f'#actTbl tr[data-row="{r}"] td.actwhen'  # noqa: E731
        b.click(cell(rows[1]))
        self.assertEqual(self.sel_rows(), [rows[1]])
        b.click(cell(rows[3]), modifiers=META)
        self.assertEqual(self.sel_rows(), [rows[1], rows[3]])
        # Ctrl-click (Windows): on a Mac Chrome turns a real Ctrl-click into a right click, so the event is sent directly
        b.eval(f"document.querySelector('{cell(rows[3])}').dispatchEvent(new MouseEvent('click',{{bubbles:true,cancelable:true,ctrlKey:true}}))")
        self.assertEqual(self.sel_rows(), [rows[1]])
        b.click(cell(rows[1]))                                                        # the anchor is the last row clicked (BL-122)
        b.click(cell(rows[4]), modifiers=SHIFT)
        self.assertEqual(self.sel_rows(), rows[1:5])
        self.assertIn("4 selected", b.eval("document.getElementById('actBar').textContent"))
        self.assertTrue(all(b.eval(f"document.querySelector('#actTbl tr[data-row=\"{r}\"] input[type=checkbox]').checked") for r in rows[1:5]))
        b.click(f'#actTbl tr[data-row="{rows[0]}"] input[type=checkbox]')                      # a tick adds
        self.assertEqual(len(self.sel_rows()), 5)
        b.key("Escape")
        self.assertEqual(self.sel_rows(), [])
        self.assertTrue(b.eval("document.getElementById('actBar').hidden"))
        self.assertEqual(b.eval("VIEW"), "activity")



if __name__ == "__main__":
    unittest.main()
