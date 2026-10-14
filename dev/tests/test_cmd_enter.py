"""BL-274 (sprint-ui-sweep): ⌘↵ (Ctrl+Enter) saves and closes every editor in the peek's place, through one handler that
editors register with (CMDENTER): the milestone editor (#mvPeek), the work-item peek and the project panel, plus Movement's
rebaseline form. Each does what its Save button does: the same checks and messages; a change that needs an answer focuses
that field and stays open; with nothing pending it closes. Plain Enter in a text area still adds a line.

A real browser against the real live server, on milestone_data's project.

Run: python3 dev/tests/test_cmd_enter.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
import milestone_data  # noqa: E402
from milestone_data import d  # noqa: E402

META = 4
KEY = "creaite.cockpit.milestones.view"


class Case(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        milestone_data.load(v)

    def setUp(self):
        super().setUp()
        self.b.eval(f"localStorage.setItem('{KEY}','int'); MVAUD='int'; S.autoApply=true")

    def until(self, fn, seconds=20):
        end = time.time() + seconds
        while time.time() < end:
            if fn():
                return True
            time.sleep(0.2)
        return False

    def ms(self, mid):
        return next(m for m in self.v.rows("milestones") if m["id"] == mid)

    def page(self, view="plan"):
        self.b.eval(f"mvOpenPage('ABC','{view}')")
        self.b.wait("VIEW==='milestones'&&document.querySelector('#v-milestones .mv-card')")

    def edit(self, mid):
        self.page()
        self.b.click(f'#v-milestones .mv-prow[data-mvedit="{mid}"]')
        self.b.wait(f"MV.peek==='{mid}'&&!document.getElementById('mvPeek').hidden&&document.getElementById('mvName')")

    def open_(self):
        return self.b.eval("!document.getElementById('mvPeek').hidden")

    def first_open(self):
        return next(m for m in self.v.rows("milestones") if m["project"] == "ABC" and m["status"] not in ("Done", "Cancelled"))


class MilestoneEditor(Case):
    def test_a_typed_name_is_saved_and_the_editor_closes(self):
        b = self.b
        m = self.first_open()
        self.edit(m["id"])
        b.eval("const n=document.getElementById('mvName'); n.focus(); n.select()")
        b.type("Renamed by command enter")
        b.key("Enter", META)
        self.assertTrue(self.until(lambda: self.ms(m["id"])["name"] == "Renamed by command enter"))
        b.wait("document.getElementById('mvPeek').hidden")

    def test_a_forecast_waiting_for_its_reason_focuses_the_reason(self):
        b = self.b
        m = self.first_open()
        self.edit(m["id"])
        b.eval(f"mvDatePicked('mvFc','{d(60)}')")
        b.wait("document.getElementById('mvFcWhy')")
        b.eval("document.getElementById('mvName').focus()")
        b.key("Enter", META)
        b.wait("document.activeElement&&document.activeElement.id==='mvFcWhy'")
        self.assertTrue(self.open_(), "it stays open")
        self.assertIn("why", b.eval("document.getElementById('mvDtErr').textContent").lower())
        b.type("Vendor slipped a week")
        b.key("Enter", META)
        self.assertTrue(self.until(lambda: self.ms(m["id"])["forecast_date"] == d(60)))
        b.wait("document.getElementById('mvPeek').hidden")

    def test_nothing_pending_just_closes(self):
        b = self.b
        self.edit(self.first_open()["id"])
        b.key("Enter", META)
        b.wait("document.getElementById('mvPeek').hidden")

    def test_enter_in_the_description_adds_a_line(self):
        b = self.b
        self.edit(self.first_open()["id"])
        b.eval("const t=document.getElementById('mvDesc'); t.focus(); t.value='one'; t.setSelectionRange(3,3)")
        b.key("Enter")
        self.assertTrue(self.open_())
        self.assertIn("\n", b.eval("document.getElementById('mvDesc').value"))

    def test_add_milestone_creates_it_or_says_what_is_missing(self):
        b = self.b
        self.page()
        b.click("#mvAdd")
        b.wait("MV.add&&document.getElementById('mvACreate')")
        b.key("Enter", META)                                        # no name: Create's own check, focused, still open
        b.wait("/Name the milestone/.test(document.getElementById('mvAddErr').textContent)")
        self.assertEqual(b.eval("document.activeElement.id"), "mvName")
        self.assertTrue(self.open_())
        b.type("Cutover rehearsal")
        b.key("Enter", META)
        self.assertTrue(self.until(lambda: any(x["name"] == "Cutover rehearsal" for x in self.v.rows("milestones"))))
        b.wait("document.getElementById('mvPeek').hidden")

    def test_the_save_buttons_show_the_key(self):
        b = self.b
        self.page()
        b.click("#mvAdd")
        b.wait("document.getElementById('mvACreate')")
        self.assertTrue(b.eval("document.getElementById('mvACreate').dataset.key.endsWith('↵')"))

    def test_one_handler_with_every_editor_registered(self):
        self.assertEqual(sorted(self.b.eval("CMDENTER.map(x=>x.name)")),
                         ["decide", "milestone", "panel", "peek", "rebaseline", "sneak"])


class Rebaseline(Case):
    def test_a_rebaseline_without_who_agreed_focuses_that_field(self):
        b = self.b
        m = self.first_open()
        self.page("move")
        b.eval(f"MV.sel='{m['id']}'; MV.rb={{id:'{m['id']}',date:'{d(90)}',why:'',with:[]}}; renderMilestones()")
        b.wait("document.getElementById('mvRbWhy')")
        b.eval("document.getElementById('mvRbWhy').focus()")
        b.key("Enter", META)
        b.wait("/who agreed/.test(document.getElementById('mvRbErr').textContent)")
        self.assertEqual(b.eval("document.activeElement.id"), "mvRbAdd")


class OtherEditors(Case):
    def test_the_peek_closes_with_nothing_to_apply(self):
        b = self.b
        b.eval("go('work')")
        b.wait("document.querySelector('#workTbl tbody tr[data-row] a.rowid')")
        b.click("#workTbl tbody tr[data-row] a.rowid")
        b.wait("pkOn()")
        b.key("Enter", META)
        b.wait("!pkOn()")

    def test_the_project_panel_saves_health_and_closes(self):
        b = self.b
        b.eval("go('cockpit','ABC')")
        b.wait("document.querySelector('#v-cockpit [data-edproj]')")
        b.click("#v-cockpit [data-edproj]")
        b.wait("CUR&&EDITING&&document.getElementById('f_reason')")
        self.assertTrue(b.eval("document.getElementById('pSave').dataset.key.endsWith('↵')"))
        b.eval("const r=document.getElementById('f_reason'); r.focus(); r.value='Checked by command enter'; r.dispatchEvent(new Event('input',{bubbles:true}))")
        b.key("Enter", META)
        b.wait("!document.getElementById('panel').classList.contains('on')")
        self.assertTrue(self.until(lambda: any("Checked by command enter" in str(p.get("health_reason") or "") for p in self.v.rows("projects"))))


if __name__ == "__main__":
    unittest.main()
