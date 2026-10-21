"""#232 (v2.6) with 2.5.3's routes: the one Intake page's Process runs Process's own run kind (#264, POST /api/intake/process,
through processLive) and its Refresh the calendar's (#265, POST /api/calendar/refresh, through calendarLive); neither sends an ask
creaite message (askLive) or opens its panel. Process shows the run's step and a Stop on the running row; a question the run could
not answer comes back on the row as "Needs you" with "ask creaite about this", which fills the panel's box and sends nothing. A
project goes with the file only when Alan chose it (#264 S6). Refresh says "Refreshing…" with the run's step, its icon is Stop while
it runs, and the closure is said once. Someone else's minutes (Find work items) still go through ask creaite until the Process guard
accepts them (dev/proposals/intake-232/ROUTES.md).

Run: python3 dev/tests/test_intake_review_routes.py   (needs Google Chrome; skipped otherwise).
"""
import json
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ir_intake_support import DAY, GATE, IntakeBase  # noqa: E402

STEERING = f"inbox/{DAY} ABC Steering.vtt"


class Routes(IntakeBase):
    shared_server = True

    def stub(self):
        self.b.eval(GATE)
        self.b.eval("window.SNACKS=[]; if(!window.SNACKO){ window.SNACKO=snack; snack=function(m){ SNACKS.push(String(m)); return SNACKO.apply(this,arguments); }; } 0")

    def chat_open(self):
        return self.b.eval("(c=>!!c && (c.classList.contains('on') || !c.hidden && c.offsetParent!==null))(document.getElementById('chat'))")

    def test_process_goes_through_its_own_route_not_ask_creaite(self):
        b = self.b
        self.stub()
        b.click(self.sel("ABC Steering", " [data-ira=process]"))
        b.wait(f"{self.row('ABC Steering')}.dataset.stage==='drafted'", 30)
        self.assertEqual(b.eval("PROC"), [[{"path": STEERING}]])
        self.assertEqual(b.eval("CHAT"), [], "Process sent an ask creaite message")
        self.assertFalse(self.chat_open())
        b.wait("SNACKS.includes('Staged for Review.')", 10)

    def test_a_project_goes_with_the_file_only_when_alan_chose_it(self):
        b = self.b
        self.assertEqual(b.eval("""[{p:'ABC',how:'remembered'},{p:'ABC',how:'matched'},{p:'_portfolio',how:'portfolio'},{p:'_portfolio',how:'remembered'},{p:null,how:'unsure'}]
          .map(m=>mtgProcessFile(m,'inbox/x.vtt'))"""),
                         [{"path": "inbox/x.vtt", "project": "ABC"}, {"path": "inbox/x.vtt"}, {"path": "inbox/x.vtt"},
                          {"path": "inbox/x.vtt", "project": "_portfolio"}, {"path": "inbox/x.vtt"}])
        self.stub()
        b.eval("D.meetings.rows.find(m=>m.id==='ev-1').how='remembered'; D.meetings.rows.find(m=>m.id==='ev-1').p='ABC'; 0")
        b.click(self.sel("ABC Steering", " [data-ira=process]"))
        b.wait("PROC.length===1 && irBusy.value.length===0", 30)
        self.assertEqual(b.eval("PROC[0]"), [{"path": STEERING, "project": "ABC"}])

    def test_the_running_row_shows_the_step_and_stop_stops_that_run(self):
        b = self.b
        self.stub()
        b.eval("window.GATE=new Promise(r=>{ window.RELEASE=r; }); window.STOPS=[]; window.REALAPI=api; api=(u,o)=>{ if(u==='/api/ask/stop') STOPS.push(o.run); return REALAPI(u,o); }; 0")
        b.click(self.sel("ABC Steering", " [data-ira=process]"))
        b.wait(f"{self.row('ABC Steering')}.dataset.state==='running'")
        b.wait(f"/Reading the transcript/.test({self.row('ABC Steering')}.innerText)")
        self.assertTrue(b.eval(f"!!{self.row('ABC Steering')}.querySelector('[data-ira=stop]')"))
        b.click(self.sel("ABC Steering", " [data-ira=stop]"))
        b.wait("STOPS.length===1")
        self.assertEqual(b.eval("STOPS"), ["i-test-1"])
        b.eval("RELEASE(); 0")
        b.wait("irBusy.value.length===0", 30)
        self.assertFalse(b.eval(f"/Reading the transcript/.test({self.row('ABC Steering')}.innerText)"), "the step stayed after the run")

    def test_a_question_comes_back_on_the_row_with_ask_creaite_about_this(self):
        b = self.b
        self.stub()
        b.eval("""window.PROCESS_RESULT=files=>({ok:true,files:files.map(f=>({path:f.path,state:'needs',question:'Which project is this for?'})),staged:0,needs:1}); 0""")
        b.click(self.sel("ABC Steering", " [data-ira=process]"))
        b.wait(f"!!{self.row('ABC Steering')}.querySelector('[data-ira=askabout]')", 30)
        self.assertIn("Needs you: Which project is this for?", b.eval(f"{self.row('ABC Steering')}.querySelector('.irnote').innerText"))
        self.assertEqual(b.eval("CHAT"), [])
        before = b.eval("document.querySelectorAll('#chLog .msg.u').length")
        b.click(self.sel("ABC Steering", " [data-ira=askabout]"))
        b.wait("document.getElementById('chIn').value.includes('Which project is this for?')")
        self.assertIn("ABC Steering", b.eval("document.getElementById('chIn').value"))
        time.sleep(0.3)
        self.assertEqual(b.eval("document.querySelectorAll('#chLog .msg.u').length"), before, "the question was sent by itself")
        self.assertEqual(b.eval("CHAT"), [])

    def test_find_work_items_still_goes_through_ask_creaite_until_the_guard_takes_it(self):
        """Someone else's minutes: the Process guard stages only a transcript today, so this one stays an ask creaite run (ROUTES.md)."""
        b = self.b
        self.stub()
        self.assertTrue(b.eval("typeof irCanStop==='function'"))
        b.eval("irSetFileKind({path:'inbox/x.docx',size:1,day:'2026-10-05'},'minutes'); 0")
        self.assertFalse(b.eval("irCanStop({id:'z',src:'upload',path:'inbox/x.docx',size:1,day:'2026-10-05'})"))

    def test_refresh_runs_its_own_route_with_the_step_and_stop_and_never_ask_creaite(self):
        b = self.b
        self.stub()
        path = self.v.root / "system/staging/calendar.json"
        cal = json.loads(path.read_text())
        self.addCleanup(path.write_text, json.dumps(cal))
        b.eval("window.GATE=new Promise(r=>{ window.RELEASE=r; }); window.STOPS=[]; window.REALAPI=api; api=(u,o)=>{ if(u==='/api/ask/stop') STOPS.push(o.run); return REALAPI(u,o); }; 0")
        said0 = b.eval("document.querySelectorAll('#chLog .msg.u').length")
        b.click("#icRef")
        b.wait("CAL.length===1 && document.querySelector('[data-ircalread]').textContent.includes('Reading the calendar')")
        self.assertIn("Refreshing…", b.eval("document.querySelector('[data-ircalread]').textContent"))
        ref = b.eval("(e=>({label:e.getAttribute('aria-label'),disabled:e.disabled,icon:e.querySelector('svg').dataset.iric}))(document.querySelector('#icRef'))")
        self.assertEqual(ref, {"label": "Stop the refresh", "disabled": False, "icon": "stop"})
        b.click("#icRef")
        b.wait("STOPS.length===1")
        self.assertEqual(b.eval("STOPS"), ["c-test-1"])
        self.assertEqual(b.eval("CAL.length"), 1, "Stop started another refresh")
        path.write_text(json.dumps({**cal, "fetched": f"{DAY} 10:42"}))
        b.eval("RELEASE(); 0")
        b.wait("irRefreshing.value===false && document.querySelector('#irSub').textContent.includes('Calendar read 10:42')", 30)
        b.wait("SNACKS.includes('Calendar saved: 3 meetings over 2 days.')", 10)
        self.assertEqual(b.eval("(e=>[e.getAttribute('aria-label'),e.querySelector('svg').dataset.iric])(document.querySelector('#icRef'))"),
                         ["Refresh the calendar", "refresh"])
        self.assertEqual(b.eval("CHAT"), [])
        self.assertEqual(b.eval("document.querySelectorAll('#chLog .msg.u').length"), said0)
        self.assertFalse(self.chat_open())

    def test_todays_refresh_calendar_uses_the_same_route(self):
        b = self.b
        self.stub()
        b.eval("irRefreshCalendar(); 0")
        b.wait("CAL.length===1 && irRefreshing.value===false", 30)
        self.assertEqual(b.eval("CHAT"), [])


if __name__ == "__main__":
    unittest.main()
