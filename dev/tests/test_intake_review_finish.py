"""#232-A finishing (v2.5.1): what the review of p250-a and the brief asked for beyond test_intake_review_harden.py. Check again on a
waiting row, the Later tooltip, the Restore wording, a drop on the ask panel left alone, the Process guard (twice, Enter, and
while ask creaite works), and a confidential meeting end to end in the built model. Real Chrome against the live server (support:
ir_harden_support.py); the model class has no browser.

Run: CREAITE_BROWSER_SLOTS=4 python3 dev/tests/test_intake_review_finish.py
"""
import json
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
from clear_day_support import ClearData, MONDAY  # noqa: E402
from ir_harden_support import IrHardenCase  # noqa: E402
from test_meetings import page_data  # noqa: E402


class Finish(IrHardenCase):
    def key(self, title, k):
        self.b.eval("(()=>{ const r=document.querySelector(%s); r.focus(); r.dispatchEvent(new KeyboardEvent('keydown',{key:%s,bubbles:true,cancelable:true})); })()"
                    % (json.dumps(self.sel(title)), json.dumps(k)))

    def mid(self, title):
        return self.b.eval("D.intake_review.meetings.find(m=>m.title===%s).id" % json.dumps(title))

    # ---- Check again
    def test_a_waiting_teams_meeting_says_what_the_sweep_found_and_offers_check_again(self):
        self.assertIn("Not transcribed", self.text("Weekly sync 12"))
        self.assertEqual(self.buttons("Weekly sync 12"), ["later", "check", "notneeded"])
        self.assertEqual(self.buttons("Busy"), ["later", "notneeded"], "a private meeting has nothing to look up")

    def test_check_again_looks_the_transcript_up_without_opening_the_ask_panel_and_the_row_turns_ready(self):
        b = self.b
        b.eval("window.CHECKED=[]; window.HOLD=new Promise(r=>{window.LET=r}); jobLive=async(u,body)=>{ CHECKED.push([u,body.id]); await HOLD; }; 0")
        b.click(self.sel("Weekly sync 12", " [data-ira=check]"))
        b.wait("irChecking.value.length===1")
        self.assertIn("Checking", self.text("Weekly sync 12"))
        self.assertTrue(b.eval("document.querySelector(%s).disabled" % json.dumps(self.sel("ABC Steering", " [data-ira=process]"))), "one run at a time")
        self.set_transcripts(self.v, {"ev-1": "available", "ev-6": "available", "ev-7": "available", "ev-2": "available"})
        b.eval("LET(); 0")
        b.wait("irChecking.value.length===0 && D.intake_review.meetings.find(m=>m.key==='ev-2').state==='ready'", 20)
        self.assertEqual(b.eval("CHECKED"), [["/api/transcripts/check", "ev-2"]])
        self.assertNotIn("check", self.buttons("Weekly sync 12"))
        self.assertFalse(b.eval("document.getElementById('chat').classList.contains('on')"))

    # ---- Later tooltip
    def test_the_later_tooltip_tells_the_truth_for_each_kind_of_row(self):
        tip = lambda t: self.b.eval("document.querySelector(%s).title" % json.dumps(self.sel(t, " [data-ira=later]")))  # noqa: E731
        self.assertIn("until its transcript arrives", tip("Weekly sync 12"))
        for ready in ("ABC Steering", "Vendor check-in"):
            self.assertIn("restore", tip(ready))
            self.assertNotIn("until its transcript arrives", tip(ready))

    # ---- Restore wording
    def test_restore_says_file_for_a_file_and_meeting_for_a_meeting(self):
        b = self.b
        self.upload("2026-10-05 Snooze me too.txt")
        b.click(self.sel("2026-10-05 Snooze me too.txt", " [data-ira=later]"))
        b.wait("D.intake_review.later.some(x=>x.title.includes('Snooze me too'))", 20)
        b.eval("document.querySelector('[data-irfold=later]').click()")
        b.wait("document.querySelector('[data-irsec=later]').innerText.includes('Snooze me too')")
        b.eval("document.querySelector('[data-irsec=later] [data-ira=restore]').click()")
        b.wait("/Restored 1 file$/.test(document.getElementById('snackT').textContent)", 20)
        b.click(self.sel("Weekly sync 12", " [data-ira=notneeded]"))
        b.click("#irAside [data-reason='Other']")
        b.wait("D.intake_review.not_needed.some(x=>x.key==='ev-2')", 20)
        b.click("#snackU")
        b.wait("/Restored 1 meeting$/.test(document.getElementById('snackT').textContent)", 20)

    # ---- a drop on the ask panel
    def test_a_file_dropped_on_the_ask_panel_is_not_also_uploaded(self):
        b = self.b
        b.eval("openChat(); 0")
        b.eval("""(()=>{ const dt=new DataTransfer(); dt.items.add(new File(["WEBVTT\\n\\nHello\\n"],"on-the-panel.vtt"));
          document.querySelector('#chat').dispatchEvent(new DragEvent('drop',{dataTransfer:dt,bubbles:true,cancelable:true})); })()""")
        time.sleep(0.6)
        self.assertFalse((self.v.root / "inbox" / "on-the-panel.vtt").exists())
        self.assertFalse(b.eval("(D.inbox||[]).some(f=>f.name==='on-the-panel.vtt')"))

    def test_a_drop_something_else_already_took_is_not_uploaded(self):
        b = self.b
        b.eval("""(()=>{ const stop=e=>e.preventDefault(); const h=document.querySelector('#v-intake-review h1'); h.addEventListener('drop',stop);
          const dt=new DataTransfer(); dt.items.add(new File(["WEBVTT\\n\\nHello\\n"],"taken.vtt"));
          h.dispatchEvent(new DragEvent('drop',{dataTransfer:dt,bubbles:true,cancelable:true})); })()""")
        time.sleep(0.6)
        self.assertFalse((self.v.root / "inbox" / "taken.vtt").exists())

    # ---- the Process guard
    def test_process_called_twice_at_once_starts_one_run(self):
        b = self.b
        b.eval("window.GATE=new Promise(r=>{window.OPEN=r}); 0")
        b.eval("(()=>{ const m=D.intake_review.meetings.find(x=>x.title==='ABC Steering'); irProcess(m); irProcess(m); })()")
        time.sleep(0.5)
        self.assertEqual(b.eval("ASKED.length"), 1)
        b.eval("OPEN(); 0")
        b.wait("irBusy.value.length===0", 30)

    def test_enter_on_a_row_that_is_running_starts_nothing_more(self):
        b = self.b
        b.eval("window.GATE=new Promise(r=>{window.OPEN=r}); 0")
        b.click(self.sel("ABC Steering", " [data-ira=process]"))
        b.wait("irBusy.value.length===1")
        self.key("ABC Steering", "Enter")
        self.key("ABC Steering", "Enter")
        time.sleep(0.5)
        self.assertEqual(b.eval("ASKED.length"), 1)
        b.eval("OPEN(); 0")
        b.wait("irBusy.value.length===0", 30)

    def test_process_does_nothing_while_ask_creaite_is_working(self):
        b = self.b
        b.eval("shared.RUN={id:'x'}; setRunning(true); 0")
        try:
            self.assertFalse(b.eval("irProcess(D.intake_review.meetings.find(x=>x.title==='ABC Steering')).then(x=>x)"))
            self.assertEqual(b.eval("ASKED.length"), 0)
            self.assertEqual(b.eval("irBusy.value.length"), 0)
        finally:
            b.eval("shared.RUN=null; setRunning(false); 0")

    def test_process_does_nothing_while_a_transcript_check_runs(self):
        b = self.b
        b.eval("irSetChecking('x', true); 0")
        try:
            self.assertFalse(b.eval("irProcess(D.intake_review.meetings.find(x=>x.title==='ABC Steering')).then(x=>x)"))
            self.assertEqual(b.eval("ASKED.length"), 0)
        finally:
            b.eval("irSetChecking('x', false); 0")

    # ---- the confidential meeting on every view
    def test_a_row_flagged_confidential_names_no_project_whatever_the_model_carries(self):
        """Defence in depth: the server sends no project for a confidential meeting, and the page does not show one if a model has it."""
        b = self.b
        b.eval("""(()=>{ D.intake_review={...D.intake_review, meetings: D.intake_review.meetings.map(m=>m.title==='ABC Steering'?{...m,p:'ABC',confidential:true}:m)}; irSel.value=null; irTick.value++; })()""")
        for view in ("list", "board", "two"):
            b.eval("irSetView(%s)" % json.dumps(view))
            b.wait("!!document.querySelector('[data-irv=%s]')" % view)
            if view == "two":
                b.eval("irSel.value=D.intake_review.meetings.find(m=>m.title==='ABC Steering').id")
            b.wait("document.getElementById('v-intake-review').innerText.includes('ABC Steering')")
            shown = b.eval("[...document.querySelectorAll('#v-intake-review [data-irm],#v-intake-review [data-irdet]')].filter(x=>x.innerText.includes('ABC Steering')).map(x=>x.innerText).join(' ')")
            self.assertNotIn("Example Programme", shown, view)
        b.eval("irSetView('list'); irSel.value=null; 0")
        b.eval("""(()=>{ D.intake_review={...D.intake_review, meetings: D.intake_review.meetings.map(m=>m.title==='ABC Steering'?{...m,confidential:false}:m)}; irTick.value++; })()""")
        b.wait("document.getElementById('v-intake-review').innerText.includes('Example Programme')")      # and the same row names it when it is not

    def test_a_confidential_meeting_keeps_only_title_and_times_after_a_run_too(self):
        b = self.b
        b.click(self.sel("ABC Board matters", " [data-ira=process]"))
        b.wait("D.intake_review.meetings.find(m=>m.title==='ABC Board matters').stage==='drafted'", 30)
        txt = self.text("ABC Board matters")
        self.assertIn("12:00", txt)
        self.assertNotIn("Example Programme", txt)


class ConfidentialModel(ClearData, unittest.TestCase):
    """The built page data: the calendar's sensitivity reaches the row, and the row carries no project."""
    NOW = MONDAY

    def test_the_calendar_sensitivity_reaches_the_meeting_row_and_hides_its_project(self):
        f = self.v.root / "system/staging/calendar.json"
        cal = json.loads(f.read_text())
        cal["days"][str(self.mon)].append({"id": "ev-7", "start": "12:00", "end": "12:30", "title": "ABC Board matters", "teams": True,
                                      "sensitivity": "confidential"})
        f.write_text(json.dumps(cal))
        self.v.run(script="build_dashboard.py")
        d = page_data(self.v)
        row = next(r for r in d["meetings"]["rows"] if r["id"] == "ev-7")
        self.assertIs(row["confidential"], True)
        ev = next(r for r in d["intake_review"]["meetings"] if r["key"] == "ev-7")
        self.assertIs(ev["confidential"], True)
        self.assertIsNone(ev["p"], "a confidential meeting names no project")
        other = next(r for r in d["intake_review"]["meetings"] if r["key"] == "ev-1")
        self.assertIs(other["confidential"], False)
        self.assertIsNotNone(other["p"])


if __name__ == "__main__":
    unittest.main()
