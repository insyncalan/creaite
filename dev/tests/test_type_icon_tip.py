"""insyncalan/creaite-plan#286 (Alan, 21-10-2026): every work item type icon names its type on hover.

Wherever a work item's type icon is drawn (the shared ico() helper: Work, Review, search, the project and person pages; and the
Week ahead's kind icon on Today), it carries the app's one tooltip (data-tip) naming the type, "Action", "Decision", "Risk",
"Issue", "Assumption", "Dependency" (and "Milestone"), with the accessible name in step (role="img", aria-label the same words)
and no native title beside it (two tooltips would show). The peek shows the type in words, not as an icon.

Run: python3 dev/tests/test_type_icon_tip.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

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


if __name__ == "__main__":
    unittest.main()
