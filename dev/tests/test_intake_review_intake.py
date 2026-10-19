"""#232-A (v2.5.0): the Intake side of Intake and Review, in a real browser against the live server. The meeting row's actions
(Process with progress on the row while ask creaite stays free, Later, Not needed with a reason and Undo), Process all ready,
Upload files (dropped anywhere on the page), Restore, the Board's Process moving the card, an uploaded file's Not needed keeping
its reason, and a Later meeting coming back when its transcript arrives. Rewrites the page tests of test_meetings.InboxPageTests,
test_transcripts_ui (Highlight, Loading, UploadList) and test_clear_day*.ClearDayPage that still apply: Load and Process are one
step now (the load-only tests are gone), and Clear day is Not needed and Later on the row.

Run: python3 dev/tests/test_intake_review_intake.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ir_intake_support import DAY, IntakeBase  # noqa: E402

class IntakeSide(IntakeBase):
    shared_server = True

    # -- the row
    def test_the_row_offers_process_later_and_not_needed_only_when_they_apply(self):
        b = self.b
        acts = lambda t: b.eval(f"[...{self.row(t)}.querySelectorAll('[data-ira]')].map(x=>x.dataset.ira)")  # noqa: E731
        self.assertEqual(acts("ABC Steering"), ["process", "later", "notneeded"])        # transcript ready
        self.assertEqual(acts("Weekly sync 12"), ["process", "later", "notneeded"])      # available, not loaded: Process loads it first
        self.assertEqual(acts("Busy"), ["later", "notneeded"])                           # waiting for a transcript: Later (it comes back) and Not needed
        words = b.eval(f"{self.row('ABC Steering')}.innerText")
        self.assertIn("Transcript ready", words)
        self.assertIn("Example Programme", words)                                        # the project's name
        self.assertNotRegex(words, r"\bABC\b(?! Steering)")                              # never its code
        self.assertNotIn("VIP", b.eval("document.getElementById('v-intake-review').innerText"))

    def test_process_shows_progress_and_ask_stays_free(self):
        b = self.b
        self.stage_stub()
        b.eval("GATE=new Promise(r=>{ window.RELEASE=r; }); 0")
        b.click(self.sel("ABC Steering", ' [data-ira="process"]'))
        b.wait(f"{self.row('ABC Steering')}.dataset.state==='running'")
        self.assertEqual(b.eval(f"{self.row('ABC Steering')}.querySelectorAll('.icprog').length"), 1)
        self.assertIn("Drafting in the background", b.eval(f"{self.row('ABC Steering')}.innerText"))
        self.assertFalse(b.eval("document.getElementById('chat') ? document.getElementById('chat').classList.contains('on') || !document.getElementById('chat').hidden && document.getElementById('chat').offsetParent!==null : false"))   # ask creaite was not opened
        self.assertEqual(b.eval("irBusy.value.length"), 1)
        self.assertTrue(b.eval(f"{self.row('Weekly sync 12')}.querySelector('[data-ira=process]').disabled"))   # one run at a time
        b.eval("RELEASE()")
        b.wait(f"{self.row('ABC Steering')}.dataset.stage==='drafted'", 30)
        self.assertEqual(b.eval("irBusy.value.length"), 0)
        self.assertEqual([q for q, _ in b.eval("ASKED")], [f"process inbox/{DAY} ABC Steering.vtt"])
        self.assertIn("draft minutes and proposed items", b.eval("ASKED[0][1]"))        # confirmed: cx-minutes may write

    def test_process_loads_the_transcript_first_and_skips_with_the_reason_on_the_row(self):
        b = self.b
        self.stage_stub()
        b.click(self.sel("Weekly sync 12", ' [data-ira="process"]'))
        b.wait(f"{self.row('Weekly sync 12')}.dataset.stage==='drafted'", 30)
        self.assertEqual([i for _, i in b.eval("LOADED")], ["ev-2"])
        self.assertEqual([q for q, _ in b.eval("ASKED")], [f"process inbox/{DAY} Weekly sync 12.vtt"])
        self.patch('Busy', state='ready', stage='arrived')
        b.click(self.sel("Busy", ' [data-ira="process"]'))
        b.wait(f"/Not a Teams meeting/.test({self.row('Busy')}.innerText)")              # the sweep's reason, on its row

    def test_board_process_moves_the_card(self):
        b = self.b
        self.stage_stub()
        mid = b.eval("D.intake_review.meetings.find(m=>m.src!=='draft'&&m.title==='ABC Steering').id")
        b.eval("document.querySelector('[data-irview=board]').click()")
        b.wait(f"!!document.querySelector('[data-ircol=arrived] [data-irm=\"{mid}\"]')")
        b.eval("GATE=new Promise(r=>{ window.RELEASE=r; }); 0")
        b.click(f'[data-ircol=arrived] [data-irm="{mid}"] [data-ira="process"]')
        b.wait(f"!!document.querySelector('[data-ircol=arrived] [data-irm=\"{mid}\"] .icprog')")     # progress on the card, still in Arrived
        b.eval("RELEASE()")
        b.wait(f"!!document.querySelector('[data-ircol=drafted] [data-irm=\"{mid}\"]')", 30)
        self.assertFalse(b.eval(f"!!document.querySelector('[data-ircol=arrived] [data-irm=\"{mid}\"]')"))

    def test_process_all_ready_goes_one_after_another(self):
        b = self.b
        self.stage_stub()
        label = b.eval("document.querySelector('[data-ira=processall]').textContent")
        self.assertEqual(label, "Process all ready (2)")             # ABC Steering and Weekly sync 12
        b.click('[data-ira="processall"]')
        b.wait("ASKED.length===2 && irBusy.value.length===0 && document.querySelector('[data-ira=processall]').textContent==='Process all ready (0)'", 40)
        self.assertEqual(sorted(q for q, _ in b.eval("ASKED")), sorted([f"process inbox/{DAY} ABC Steering.vtt", f"process inbox/{DAY} Weekly sync 12.vtt"]))
        self.assertTrue(b.eval("document.querySelector('[data-ira=processall]').disabled"))

    # -- Later and Not needed
    def test_h_hides_and_transcript_brings_back(self):
        b = self.b
        self.key("ABC Steering", "h")                                                    # its transcript is already here: Later keeps it away
        b.wait("!D.intake_review.meetings.some(m=>m.src!=='draft'&&m.title==='ABC Steering')", 20)
        self.assertEqual([(e["key"], e.get("kind"), e.get("seen")) for e in self.cleared()], [("ev-1", "later", True)])
        b.wait("D.intake_review.later.some(x=>x.title==='ABC Steering')", 20)
        self.unfold("later")
        b.wait("document.querySelector('[data-irsec=later]').textContent.includes('ABC Steering')")
        b.click('[data-irsec=later] [data-ira="restore"]')                              # Restore brings it back by hand
        b.wait("D.intake_review.meetings.some(m=>m.src!=='draft'&&m.title==='ABC Steering')", 20)
        self.assertEqual(self.cleared(), [])
        self.key("Busy", "h")                                                            # no transcript yet: it comes back when one arrives
        b.wait("D.intake_review.later.some(x=>x.title==='Busy')", 20)
        self.assertFalse(b.eval("D.intake_review.meetings.some(m=>m.title==='Busy')"))
        (self.v.root / "system/staging/transcripts.json").write_text(json.dumps({"version": 1, "checked": {
            "ev-1": {"status": "available", "checked": f"{DAY} 07:00"}, "ev-2": {"status": "available", "checked": f"{DAY} 07:00"},
            "ev-3": {"status": "available", "checked": f"{DAY} 17:00"}}}))
        b.eval("reloadData()")
        b.wait("D.intake_review.meetings.some(m=>m.title==='Busy' && m.later_back)", 20)
        self.assertIn("back from Later", b.eval(f"{self.row('Busy')}.innerText"))

    def test_not_needed_asks_reason_then_undo(self):
        b = self.b
        b.click(self.sel("ABC Steering", ' [data-ira="notneeded"]'))
        b.wait("!!document.querySelector('[data-reason]')")
        self.assertEqual(b.eval("[...document.querySelectorAll('#irAside [data-reason]')].map(x=>x.dataset.reason)"),
                         ["Informal chat", "No decisions", "Duplicate of another meeting", "Other"])
        b.click('#irAside [data-reason="Informal chat"]')
        b.wait("D.intake_review.not_needed.some(x=>x.title==='ABC Steering' && x.reason==='Informal chat')", 20)
        self.assertEqual([(e["key"], e["reason"]) for e in self.cleared()], [("ev-1", "Informal chat")])
        self.assertFalse(b.eval("D.intake_review.meetings.some(m=>m.src!=='draft'&&m.title==='ABC Steering')"))
        self.unfold("not_needed")
        b.wait("document.querySelector('[data-irsec=not_needed]').textContent.includes('Informal chat')")
        b.wait("/Not needed/.test(document.getElementById('snackT').textContent)")
        b.click("#snackU")                                                                 # Undo
        b.wait("D.intake_review.meetings.some(m=>m.src!=='draft'&&m.title==='ABC Steering')", 20)
        self.assertEqual(self.cleared(), [])

    def test_uploaded_file_keeps_reason(self):
        b = self.b
        (self.v.root / "inbox" / "Dropped notes.vtt").write_text("WEBVTT\n\n00:00:01.000 --> 00:00:05.000\nNotes\n")
        b.eval("reloadData().then(()=>irTick.value++)")
        b.wait("D.intake_review.meetings.some(m=>m.title==='Dropped notes.vtt')", 20)
        b.click(self.sel("Dropped notes.vtt", ' [data-ira="notneeded"]'))
        b.click('#irAside [data-reason="No decisions"]')
        b.wait("D.intake_review.not_needed.some(x=>x.title==='Dropped notes.vtt' && x.reason==='No decisions')", 20)
        self.assertFalse(b.eval("D.intake_review.meetings.some(m=>m.title==='Dropped notes.vtt')"))
        b.reload("typeof go==='function' && LIVE")
        b.eval("go('intake-review')")
        b.wait("D.intake_review.not_needed.some(x=>x.title==='Dropped notes.vtt' && x.reason==='No decisions')")   # kept across a reload
        self.unfold("not_needed")
        b.click('[data-irsec=not_needed] [data-ira="restore"]')
        b.wait("D.intake_review.meetings.some(m=>m.title==='Dropped notes.vtt')", 20)

    # -- upload
    def test_drop_files_anywhere_become_rows(self):
        b = self.b
        b.eval("""(()=>{ const dt=new DataTransfer(); dt.items.add(new File(['WEBVTT\\n\\n00:00:01.000 --> 00:00:05.000\\nHi\\n'],'Dropped notes.vtt'));
          document.querySelector('#v-intake-review h1').dispatchEvent(new DragEvent('drop',{dataTransfer:dt,bubbles:true,cancelable:true})); })()""")
        b.wait("D.intake_review.meetings.some(m=>m.title==='Dropped notes.vtt' && m.src==='upload')", 30)
        self.assertTrue((self.v.root / "inbox" / "Dropped notes.vtt").exists())
        b.wait(f"!!{self.row('Dropped notes.vtt')}")
        self.assertEqual(b.eval(f"[...{self.row('Dropped notes.vtt')}.querySelectorAll('[data-ira]')].map(x=>x.dataset.ira)"), ["process", "later", "notneeded"])
        self.assertTrue(b.eval("!!document.querySelector('#v-intake-review [data-irpick]')"))        # and a button to choose files

    # -- age and stale (from test_review_age)
    def test_age_and_stale_are_on_the_meeting_row(self):
        b = self.b
        self.patch('ABC Steering', age=3, stale=False)
        self.patch('Weekly sync 12', age=20, stale=True)
        b.wait(f"/Transcript ready · 3 days/.test({self.row('ABC Steering')}.innerText)")
        self.assertEqual(b.eval(f"{self.row('ABC Steering')}.querySelectorAll('.tag.stale').length"), 0)
        self.assertEqual(b.eval(f"{self.row('Weekly sync 12')}.querySelector('.tag.stale').textContent"), "Stale · 20 days")

    # -- the confidential meeting
    def test_a_confidential_meeting_shows_only_its_title_and_times(self):
        b = self.b
        text = b.eval(f"{self.row('Busy')}.innerText")
        self.assertIn("Busy", text)
        self.assertIn("08:30", text)
        for hidden in ("Organiser", "Where", "Teams", "Example Programme"):
            self.assertNotIn(hidden, text)


if __name__ == "__main__":
    unittest.main()
