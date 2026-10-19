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
from live_browser import LiveBrowserCase, pin_page_clock  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_meetings import week_calendar  # noqa: E402

NOW = "2026-10-05 18:00"            # a Monday evening: every meeting of the week so far has ended
DAY = "2026-10-05"
GATE = r"""window.ASKED=[]; window.LOADED=[]; window.GATE=null; window.OPENED=[];
jobLive=async(url,body)=>{ window.LOADED.push([url,body.id]);
  const f=D.meetings.rows.find(m=>m.id===body.id);
  await api('/api/fs',{op:'write',path:'inbox/'+f.day+' '+f.title+'.vtt',text:'WEBVTT\n\nNOTE\nEvent ID: '+body.id+'\n\n00:00:01.000 --> 00:00:05.000\nHello\n'}); };
askLive=async(q,c)=>{ window.ASKED.push([q,c]); if(window.GATE) await window.GATE;
  const m=D.meetings.rows.find(x=>q.includes(x.title));
  if(m) await api('/api/fs',{op:'write',path:'system/staging/proposed-test-'+m.id+'.json',text:JSON.stringify({created:'2026-10-05T18:00:00',source_run:'cx-minutes',files:[],items:[],meeting:{key:'calendar:'+m.id,title:m.title,date:m.day,projects:['ABC'],draft:null,transcript:null,minutes_decision:'pending',file_ops:[]}})}); };"""


class IntakeSide(LiveBrowserCase):
    shared_server = True
    width, height = 1400, 1000

    @classmethod
    def load(cls, v):
        populate(v)
        week_calendar(v, today=__import__("datetime").date(2026, 10, 5))
        # ev-1 has its transcript in the inbox (loaded); ev-2's transcript exists but is not loaded; ev-3 (Busy) has none yet
        (v.root / "inbox" / f"{DAY} ABC Steering.vtt").write_text("WEBVTT\n\nNOTE\nEvent ID: ev-1\n\n00:00:01.000 --> 00:00:05.000\nHello\n")
        (v.root / "system/staging/transcripts.json").write_text(json.dumps({"version": 1, "checked": {
            "ev-1": {"status": "available", "uri": "meeting-transcript:///a", "count": 1, "checked": f"{DAY} 07:00"},
            "ev-2": {"status": "available", "uri": "meeting-transcript:///b", "count": 1, "checked": f"{DAY} 07:00"}}}))

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": NOW}

    def setUp(self):
        super().setUp()
        root = self.v.root
        for p in (root / "system/staging/intake-cleared.json", *root.glob("system/staging/proposed-test-*.json"),
                  root / "inbox" / f"{DAY} Weekly sync 12.vtt", root / "inbox" / "Dropped notes.vtt"):
            p.unlink(missing_ok=True)
        pin_page_clock(self.b, NOW)
        self.b.eval("irSetView('list'); irStage.value='all'; irOpen.value=null; irBusy.value=[]")
        self.b.eval("reloadData().then(()=>go('intake-review'))")
        self.b.wait("VIEW==='intake-review' && !!document.querySelector('#v-intake-review [data-irm]')")

    # -- helpers
    def row(self, title):
        return f"document.querySelector('#v-intake-review [data-irm=\"' + D.intake_review.meetings.find(m=>m.title===" + json.dumps(title) + ").id + '\"]')"

    def sel(self, title, suffix=""):
        mid = self.b.eval("D.intake_review.meetings.find(m=>m.title===" + json.dumps(title) + ").id")
        return f'#v-intake-review [data-irm="{mid}"]{suffix}'

    def cleared(self):
        p = self.v.root / "system/staging/intake-cleared.json"
        return json.loads(p.read_text())["cleared"] if p.exists() else []

    def stage_stub(self):
        self.b.eval(GATE)

    def key(self, title, k):
        self.b.eval(f"(()=>{{ const r={self.row(title)}; r.focus(); r.dispatchEvent(new KeyboardEvent('keydown',{{key:{json.dumps(k)},bubbles:true}})); }})()")

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
        b.eval("GATE=new Promise(r=>{ window.RELEASE=r; })")
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
        b.eval("D.intake_review.meetings.find(m=>m.title==='Busy').state='ready'; D.intake_review.meetings.find(m=>m.title==='Busy').stage='arrived'; irTick.value++")
        b.click(self.sel("Busy", ' [data-ira="process"]'))
        b.wait(f"/Not a Teams meeting/.test({self.row('Busy')}.innerText)")              # the sweep's reason, on its row

    def test_board_process_moves_the_card(self):
        b = self.b
        self.stage_stub()
        b.eval("document.querySelector('[data-irview=board]').click()")
        b.wait("!!document.querySelector('[data-ircol=arrived] [data-irm]')")
        card = lambda col: b.eval(f"[...document.querySelectorAll('[data-ircol={col}] .t')].map(x=>x.textContent)")  # noqa: E731
        self.assertIn("ABC Steering", card("arrived"))
        b.eval("GATE=new Promise(r=>{ window.RELEASE=r; })")
        b.click(self.sel("ABC Steering", ' [data-ira="process"]'))
        b.wait("!!document.querySelector('[data-ircol=arrived] .icprog')")               # progress on the card, still in Arrived
        b.eval("RELEASE()")
        b.wait("[...document.querySelectorAll('[data-ircol=drafted] .t')].some(x=>x.textContent==='ABC Steering')", 30)
        self.assertNotIn("ABC Steering", card("arrived"))

    def test_process_all_ready_goes_one_after_another(self):
        b = self.b
        self.stage_stub()
        label = b.eval("document.querySelector('[data-ira=processall]').textContent")
        self.assertEqual(label, "Process all ready (2)")
        b.click('[data-ira="processall"]')
        b.wait("document.querySelector('[data-ira=processall]').textContent==='Process all ready (0)'", 40)
        self.assertEqual(sorted(q for q, _ in b.eval("ASKED")), sorted([f"process inbox/{DAY} ABC Steering.vtt", f"process inbox/{DAY} Weekly sync 12.vtt"]))
        self.assertTrue(b.eval("document.querySelector('[data-ira=processall]').disabled"))

    # -- Later and Not needed
    def test_h_hides_and_transcript_brings_back(self):
        b = self.b
        self.key("ABC Steering", "h")                                                    # its transcript is already here: Later keeps it away
        b.wait("!D.intake_review.meetings.some(m=>m.title==='ABC Steering')", 20)
        self.assertEqual([(e["key"], e.get("kind"), e.get("seen")) for e in self.cleared()], [("ev-1", "later", True)])
        b.eval("document.querySelector('[data-irfold=later]').click()")
        b.wait("document.querySelector('[data-irsec=later]').textContent.includes('ABC Steering')")
        b.click('[data-irsec=later] [data-ira="restore"]')                              # Restore brings it back by hand
        b.wait("D.intake_review.meetings.some(m=>m.title==='ABC Steering')", 20)
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
        self.assertFalse(b.eval("D.intake_review.meetings.some(m=>m.title==='ABC Steering')"))
        b.eval("document.querySelector('[data-irfold=not_needed]').click()")
        b.wait("document.querySelector('[data-irsec=not_needed]').textContent.includes('Informal chat')")
        b.wait("/Not needed/.test(document.getElementById('snackT').textContent)")
        b.click("#snackU")                                                                 # Undo
        b.wait("D.intake_review.meetings.some(m=>m.title==='ABC Steering')", 20)
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
        b.click('[data-irsec=not_needed] [data-ira="restore"]')
        b.wait("D.intake_review.meetings.some(m=>m.title==='Dropped notes.vtt')", 20)

    # -- upload
    def test_drop_files_anywhere_become_rows(self):
        b = self.b
        b.eval("""(()=>{ const dt=new DataTransfer(); dt.items.add(new File(['WEBVTT\\n\\n00:00:01.000 --> 00:00:05.000\\nHi\\n'],'Dropped notes.vtt'));
          document.querySelector('#v-intake-review h1').dispatchEvent(new DragEvent('drop',{dataTransfer:dt,bubbles:true,cancelable:true})); })()""")
        b.wait("D.intake_review.meetings.some(m=>m.title==='Dropped notes.vtt' && m.src==='upload')", 30)
        self.assertTrue((self.v.root / "inbox" / "Dropped notes.vtt").exists())
        self.assertEqual(b.eval(f"[...{self.row('Dropped notes.vtt')}.querySelectorAll('[data-ira]')].map(x=>x.dataset.ira)"), ["process", "later", "notneeded"])
        self.assertTrue(b.eval("!!document.querySelector('#v-intake-review [data-irpick]')"))        # and a button to choose files

    # -- age and stale (from test_review_age)
    def test_age_and_stale_are_on_the_meeting_row(self):
        b = self.b
        b.eval("D.intake_review.meetings.find(m=>m.title==='ABC Steering').age=3; D.intake_review.meetings.find(m=>m.title==='ABC Steering').stale=false; "
               "D.intake_review.meetings.find(m=>m.title==='Weekly sync 12').age=20; D.intake_review.meetings.find(m=>m.title==='Weekly sync 12').stale=true; irTick.value++")
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
