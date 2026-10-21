"""insyncalan/creaite-plan#286 (Alan, 21-10-2026): every work item type icon names its type on hover.

Wherever a work item's type icon is drawn (the shared ico() helper: Work, Review, search, the project and person pages; and the
Week ahead's kind icon on Today), it carries the app's one tooltip (data-tip) naming the type, "Action", "Decision", "Risk",
"Issue", "Assumption", "Dependency" (and "Milestone"), with the accessible name in step (role="img", aria-label the same words)
and no native title beside it (two tooltips would show). The peek shows the type in words, not as an icon.
Milestones everywhere (Alan, 21-10-2026): search, the Dependencies card's milestone headers, the Week ahead (through the helper) and
the Milestones page's own markers (Plan strip, also on the project page's card; Movement's forecast and original-date marks),
whose tooltip and name start "Milestone: " and then say which one, its state and date.

Run: python3 dev/tests/test_type_icon_tip.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
import build_dashboard as bd  # noqa: E402
from datetime import date  # noqa: E402

WORDS = ["Action", "Decision", "Risk", "Issue", "Assumption", "Dependency", "Milestone"]
# every type icon on the page: [tooltip, name, role, title, svg hidden]
ICONS = """(sel=>[...document.querySelectorAll(sel)].filter(e=>e.getClientRects().length).map(e=>[e.dataset.tip||null,e.getAttribute('aria-label'),
  e.getAttribute('role'),e.getAttribute('title'),(e.querySelector('svg')||{getAttribute:()=>null}).getAttribute('aria-hidden')]))"""


class TypeIconTip(LiveBrowserCase):
    shared_server = True

    def named(self, sel):
        got = self.b.eval(f"{ICONS}({sel!r})")
        self.assertTrue(got, sel)
        for tip, name, role, title, hid in got:
            self.assertIn(tip, WORDS, sel)
            self.assertEqual((name, role, title, hid), (tip, "img", None, "true"), sel)
        return {g[0] for g in got}

    def test_the_helper_names_all_six_types(self):
        b = self.b
        for k, w in (("action", "Action"), ("decision", "Decision"), ("Risk", "Risk"), ("Issue", "Issue"),
                     ("Assumption", "Assumption"), ("Dependency", "Dependency"), ("milestone", "Milestone")):
            h = b.eval(f"ico({k!r})")
            self.assertIn(f'data-tip="{w}"', h)
            self.assertIn(f'aria-label="{w}"', h)
            self.assertIn('role="img"', h)
            self.assertNotIn("title=", h)
        for k, w in (("risk", "Risk"), ("issue", "Issue"), ("assumption", "Assumption"), ("dependency", "Dependency"), ("action", "Action"), ("decision", "Decision")):
            self.assertIn(f'data-tip="{w}"', b.eval(f"searchIco({k!r})"))     # search results
        self.assertIn('data-tip="Milestone"', b.eval("searchIco('milestone')"))  # search: a milestone result
        self.assertEqual(b.eval("[typeWord('actions'),typeWord('decisions'),typeWord('raid',{type:'Issue'}),typeWord('raid',{}),typeWord('milestone')]"),
                         ["Action", "Decision", "Issue", "Risk", "Milestone"])

    def test_work_and_review_rows(self):
        b = self.b
        b.eval("go('work')")
        for tab, want in (("actions", {"Action"}), ("raid", None), ("decisions", {"Decision"})):
            b.click(f'#wtabs [data-t="{tab}"]')
            b.wait(f"WT==={tab!r}")
            b.pump(0.2)
            seen = self.named("#workTbl .ki")
            if want:
                self.assertEqual(seen, want, tab)
            else:
                self.assertTrue(seen <= {"Risk", "Issue", "Assumption", "Dependency"} and len(seen) >= 2, seen)
        b.eval("go('review')")
        b.pump(0.3)
        if b.eval("document.querySelectorAll('#reviewBody .ki').length"):
            self.named("#reviewBody .ki")

    def test_hover_shows_the_type(self):
        b = self.b
        b.eval("go('work')")
        b.click('#wtabs [data-t="actions"]')
        b.wait("WT==='actions'")
        b.pump(0.2)
        b.eval("document.querySelector('#workTbl .ki').scrollIntoView({block:'center'})")
        p = b.box("#workTbl .ki")
        b.call("Input.dispatchMouseEvent", type="mouseMoved", x=p["x"], y=p["y"], button="none")
        b.wait("(()=>{ const t=document.getElementById('tip'); return !!(t&&t.classList.contains('on')); })()", 5)
        self.assertEqual(b.eval("document.getElementById('tip').textContent"), "Action")
        b.call("Input.dispatchMouseEvent", type="mouseMoved", x=5, y=880, button="none")

    def test_the_week_ahead_kind_icon_on_today(self):
        b = self.b
        b.eval("""D.week={from:TODAY,to:pkAdd(TODAY,5),days:[{date:pkAdd(TODAY,1),dow:"",weekend:false,meetings:[],items:[
            {kind:"actions",id:"ABC-A-901",p:"ABC",t:"Theirs",o:"Omar Ali"},
            {kind:"decisions",id:"ABC-D-909",p:"ABC",t:"Pick a vendor",o:"Omar Ali"},
            {kind:"raid",id:"ABC-R-909",p:"ABC",t:"A risk",o:"Omar Ali",type:"Risk"},
            {kind:"raid",id:"ABC-R-910",p:"ABC",t:"An issue",o:"Omar Ali",type:"Issue"},
            {kind:"raid",id:"ABC-R-911",p:"ABC",t:"An assumption",o:"Omar Ali",type:"Assumption"},
            {kind:"raid",id:"ABC-R-912",p:"ABC",t:"A dependency",o:"Omar Ali",type:"Dependency"},
            {kind:"milestone",id:"ABC-M-001",p:"ABC",t:"UAT",slip:true}]}],undated:[],further:[]}; go('today'); renderToday()""")
        b.wait("document.querySelector('#weekList .wkic')")
        b.eval("EXPAND.add('wk'+pkAdd(TODAY,1)); renderToday()")
        b.wait("document.querySelectorAll('#weekList .wkic').length>=7")
        self.assertEqual(b.eval(f"{ICONS}('#weekList .wkic').map(x=>x[0])"),
                         ["Action", "Decision", "Risk", "Issue", "Assumption", "Dependency", "Milestone"])
        self.named("#weekList .wkic")
        b.eval("""D.week.days=[]; D.week.undated=[{kind:"raid",id:"ABC-R-920",p:"ABC",t:"Undated issue",o:"Omar Ali",pr:"Urgent",type:"Issue"}];
            D.week.further=[{date:pkAdd(TODAY,10),kind:"raid",id:"ABC-R-921",p:"ABC",t:"Later dependency",o:"Omar Ali",pr:"High",type:"Dependency"}];
            D.week.further_to=pkAdd(TODAY,20); renderToday()""")
        b.wait("document.querySelectorAll('#weekList .wkic').length===2")
        self.assertEqual(b.eval(f"{ICONS}('#weekList .wkic').map(x=>x[0])"), ["Issue", "Dependency"])   # Urgent with no date; Further ahead

    def milestone_marks(self, sel):
        got = self.b.eval(f"[...document.querySelectorAll({sel!r})].map(e=>[e.dataset.tip||'',e.getAttribute('aria-label')||'',e.getAttribute('title')])")
        self.assertTrue(got, sel)
        for tip, name, title in got:
            self.assertTrue(tip.startswith("Milestone: ") and len(tip) > 11, (sel, tip))
            self.assertEqual((name, title), (tip, None), sel)

    def test_milestones_on_the_project_page_and_the_milestones_page(self):
        b = self.b
        b.eval("MVAUD='int'; try{ localStorage.setItem('creaite.cockpit.milestones.view','int'); }catch(e){}")   # the internal view: every milestone
        b.eval("go('cockpit','ABC')")
        b.wait("document.querySelector('#mvCard .mv-mk')")
        self.milestone_marks("#mvCard .mv-mk")                                          # the project page's milestones card (Plan strip)
        b.eval("mvOpenPage('ABC','plan')")
        b.wait("VIEW==='milestones'&&document.querySelector('#v-milestones .mv-mk')")
        self.milestone_marks("#v-milestones .mv-mk")                                    # the Milestones page: Plan
        if b.eval("!!document.querySelector('#v-milestones .mv-ghost')"):
            self.milestone_marks("#v-milestones .mv-ghost")                             # a slipped milestone's expected date
        b.eval("mvOpenPage('ABC','move')")
        b.wait("document.querySelector('#v-milestones .mv-track .fc')")
        self.milestone_marks("#v-milestones .mv-track .fc")                             # Movement: the forecast mark
        if b.eval("!!document.querySelector('#v-milestones .mv-track .orig')"):
            self.milestone_marks("#v-milestones .mv-track .orig")                       # Movement: the original date
        b.eval("try{ localStorage.removeItem('creaite.cockpit.milestones.view'); }catch(e){} go('today')")


class WeekAheadTypeData(unittest.TestCase):
    """The Week ahead's data carries a RAID item's type in every group (dated days, Urgent with no date, Further ahead),
    so each row's icon can name it (Cap's review of #286)."""

    def test_undated_and_further_rows_carry_the_type(self):
        raid = [{"id": "ABC-R-001", "p": "ABC", "t": "Undated", "o": "Omar Ali", "st": "Open", "due": None, "pr": "Urgent", "type": "Issue"},
                {"id": "ABC-R-002", "p": "ABC", "t": "Later", "o": "Omar Ali", "st": "Open", "due": "2026-10-20", "pr": "High", "type": "Dependency"},
                {"id": "ABC-R-003", "p": "ABC", "t": "This week", "o": "Omar Ali", "st": "Open", "due": "2026-10-07", "pr": "High", "type": "Assumption"}]
        w = bd.week_ahead(date(2026, 10, 5), [], raid, [], [], {}, None)
        self.assertEqual([(i["id"], i.get("type")) for i in w["undated"]], [("ABC-R-001", "Issue")])          # Urgent, with no date
        self.assertEqual([(i["id"], i.get("type")) for i in w["further"]], [("ABC-R-002", "Dependency")])     # Further ahead
        self.assertEqual([(i["id"], i.get("type")) for d in w["days"] for i in d["items"]], [("ABC-R-003", "Assumption")])


if __name__ == "__main__":
    unittest.main()
