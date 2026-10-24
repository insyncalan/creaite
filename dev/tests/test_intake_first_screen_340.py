"""#340: the work to decide leads Intake. At 1400 and 900 px wide the first Approve (or, with none open, the first Check them) is inside
the first screen of the page scroller (section.view, not the window), the Arrived / Drafted / Approved / Show all strip is visible, and
the Arrived list comes after the work to decide. Group by, ticks and the right-click menu still work on the reordered list.

Run: python3 dev/tests/test_intake_first_screen_340.py   (needs Google Chrome; skipped otherwise)"""
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ir_intake_support import IntakeBase  # noqa: E402

FIRST = """(()=>{ const v=document.querySelector('#v-intake-review').closest('section.view')||document.querySelector('section.view.on'), vr=v.getBoundingClientRect();
  const ctl=document.querySelector('#v-intake-review tr.irprop [data-ira=approve]')||document.querySelector('#v-intake-review [data-ira=open]'), cr=ctl&&ctl.getBoundingClientRect();
  const strip=(document.querySelector('#v-intake-review [data-irstage=all]')||document.querySelector('#v-intake-review .icsum')||document.querySelector('#v-intake-review .iccol h2')).getBoundingClientRect();
  return {ctl: !!ctl, ctlBottom: cr?cr.bottom:null, viewBottom: Math.min(vr.bottom, innerHeight), stripBottom: strip.bottom, stripTop: strip.top, viewTop: vr.top, scroll: v.scrollHeight}; })()"""

FOLD = Path(__file__).resolve().parents[2] / "system/templates/dashboard/src/core/irFold.js"


@unittest.skipUnless(shutil.which("node"), "needs Node")
class TailAndCap(unittest.TestCase):
    """The pure rules, under Node: the waiting tail splits off and the work keeps Drafted, Approved, Arrived order; mail and Teams
    shows its first five (needs first) and says how many there are."""

    def run_js(self, body):
        script = f"const f = await import({json.dumps(FOLD.as_uri())}); const none = () => false; {body}"
        r = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_split_tail(self):
        out = self.run_js("""const L=[{id:'a',stage:'arrived',state:'waiting'},{id:'b',stage:'approved'},{id:'c',stage:'arrived',state:'ready'},{id:'d',stage:'drafted'},{id:'e',stage:'arrived',state:'waiting'}];
          const s=f.irSplitTail(L); console.log(JSON.stringify({work:s.work.map(m=>m.id),tail:s.tail.map(m=>m.id),fold:f.irIsFolded({}, 'waiting'),open:f.irIsFolded({waiting:false}, 'waiting')}));""")
        self.assertEqual(out, {"work": ["d", "b", "c"], "tail": ["a", "e"], "fold": True, "open": False})

    def test_cap_mail(self):
        out = self.run_js("""const g={needs:[1,2],routine:[3,4,5,6,7]}; const c=f.irCapGroups(g,none,null,5), d=f.irCapGroups(g,n=>n===1,null,5), small=f.irCapGroups({needs:[1],routine:[2]},none,null,5);
          console.log(JSON.stringify({c:c.groups,t:c.total,d:d.groups,dt:d.total,small:small.groups===undefined,cap:f.IR_MAIL_CAP}));""")
        self.assertEqual(out, {"c": {"needs": [1, 2], "routine": [3, 4, 5]}, "t": 7, "d": {"needs": [2], "routine": [3, 4, 5, 6]}, "dt": 6, "small": False, "cap": 5})


class FirstScreen(IntakeBase):
    shared_server = True

    def check(self, width):
        b = self.b
        self.fold()
        b.resize(width, 900)
        b.wait("!!document.querySelector('#v-intake-review [data-irstage=all]')")
        r = b.eval(FIRST)
        self.assertTrue(r["ctl"], r)
        self.assertLessEqual(r["ctlBottom"], r["viewBottom"], f"first approval below the first screen at {width}: {r}")
        self.assertGreaterEqual(r["stripTop"], r["viewTop"] - 1, r)
        self.assertLessEqual(r["stripBottom"], r["viewBottom"], r)

    def test_an_open_meetings_approve_is_in_the_first_screen(self):
        b = self.b
        b.eval("irOpen.value=D.intake_review.meetings.find(m=>m.stage==='drafted').id; 0")
        b.wait("!!document.querySelector('#v-intake-review tr.irprop [data-ira=approve]')")
        for w in (1400, 900):
            b.resize(w, 900)
            b.wait("!!document.querySelector('#v-intake-review [data-irstage=all]')")
            r = b.eval(FIRST)
            self.assertTrue(b.eval("!!document.querySelector('#v-intake-review tr.irprop [data-ira=approve]')"))
            self.assertLessEqual(r["ctlBottom"], r["viewBottom"], f"open Approve below the first screen at {w}: {r}")

    def test_first_approval_in_the_first_screen_at_1400(self):
        self.check(1400)

    def test_first_approval_in_the_first_screen_at_900(self):
        self.check(900)

    def test_arrived_rows_come_after_the_work_to_decide(self):
        b = self.b
        order = b.eval("[...document.querySelectorAll('#v-intake-review tr.irmeet')].map(r=>r.dataset.stage)")
        ranks = {"drafted": 0, "approved": 1, "arrived": 2}
        self.assertEqual(order, sorted(order, key=lambda s: ranks[s]))
        self.assertTrue(b.eval("(()=>{ const m=document.querySelector('#v-intake-review [data-irsec=mail]'), a=document.querySelector('#v-intake-review [data-irsec=waiting]'); return !a || !m || !!(m.compareDocumentPosition(a) & Node.DOCUMENT_POSITION_FOLLOWING); })()"))

    def fold(self):
        self.b.eval("irFolded.value={}; irStage.value='all'; 0")

    def view(self, v, width=1400):
        b = self.b
        b.eval(f"irOpen.value=null; document.querySelector('[data-irview={v}]').click(); 0")
        b.resize(width, 900)
        b.wait(f"irView.value==='{v}'")

    def test_the_waiting_tail_is_folded_and_shows_on_a_click(self):
        b = self.b
        self.fold()
        for v in ("list", "board", "two"):
            self.view(v)
            n = "document.querySelectorAll('#v-intake-review [data-irm]')"
            self.assertTrue(b.eval("!!document.querySelector('#v-intake-review [data-irsec=waiting]')"), v)
            folded = b.eval(f"{n}.length")
            b.click("#v-intake-review [data-irfold=waiting]")
            b.wait(f"{n}.length>{folded}")
            b.click("#v-intake-review [data-irfold=waiting]")
            b.wait(f"{n}.length==={folded}")

    def test_board_leads_with_work_and_the_open_suggestions_sit_above_it(self):
        b = self.b
        self.fold()
        self.view("board")
        self.assertEqual(b.eval("[...document.querySelectorAll('#v-intake-review .iccol')].map(c=>c.dataset.ircol)"), ["drafted", "approved", "arrived"])
        b.eval("irOpen.value=D.intake_review.meetings.find(m=>m.stage==='drafted').id; 0")
        b.wait("!!document.querySelector('#v-intake-review [data-irpart=open] tr.irprop')")
        self.assertTrue(b.eval("document.querySelector('#v-intake-review [data-irpart=open]').compareDocumentPosition(document.querySelector('#v-intake-review .icboard')) & Node.DOCUMENT_POSITION_FOLLOWING"))
        for w in (1400, 900):
            b.resize(w, 900)
            r = b.eval(FIRST)
            self.assertLessEqual(r["ctlBottom"], r["viewBottom"], f"board approval below the first screen at {w}: {r}")

    def test_board_and_two_panes_first_control_in_the_first_screen(self):
        self.fold()
        for v in ("board", "two"):
            for w in (1400, 900):
                self.view(v, w)
                r = self.b.eval(FIRST)
                self.assertLessEqual(r["stripBottom"], r["viewBottom"], (v, w, r))
                if v == "board":
                    self.assertTrue(r["ctl"], (v, w, r))
                    self.assertLessEqual(r["ctlBottom"], r["viewBottom"], (v, w, r))

    def test_two_panes_opens_on_the_work_and_does_not_open_a_meeting(self):
        b = self.b
        self.fold()
        self.view("two")
        self.assertEqual(b.eval("document.querySelector('#v-intake-review [data-irdet]').dataset.irdet"), b.eval("document.querySelector('#v-intake-review tr[data-irm]').dataset.irm"))
        self.assertTrue(b.eval("D.intake_review.meetings.find(m=>m.id===document.querySelector('#v-intake-review tr[data-irm]').dataset.irm).stage!=='arrived'"))
        self.assertTrue(b.eval("irOpen.value==null"))
        r = b.eval(FIRST)
        self.assertTrue(r["ctl"], r)
        self.assertLessEqual(r["ctlBottom"], r["viewBottom"], r)


if __name__ == "__main__":
    unittest.main()
