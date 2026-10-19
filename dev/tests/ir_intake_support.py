"""Shared set-up for the #232-A browser tests (test_intake_review_intake, _keys_intake, _rules): one live server on a pinned Monday
evening, a fixture week from test_meetings.week_calendar, transcripts for ev-1 (loaded in the inbox) and ev-2 (available, not
loaded), and stubs for the run engine (`stage_stub`) so Process loads and drafts without a real Claude."""
import json
import sys
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
  await api('/api/inbox/upload',{name:f.day+' '+f.title+'.vtt',data:btoa('WEBVTT\n\nNOTE\nEvent ID: '+body.id+'\n\n00:00:01.000 --> 00:00:05.000\nHello\n')}); };
askLive=async(q,c)=>{ window.ASKED.push([q,c]); if(window.GATE) await window.GATE;
  const m=D.meetings.rows.find(x=>q.includes(x.title));
  if(m) await api('/api/fs',{op:'write',path:'system/staging/proposed-test-'+m.id+'.json',text:JSON.stringify({created:'2026-10-05T18:00:00',source_run:'cx-minutes',files:[],items:[{n:1,op:'new',table:'actions',values:{project:'ABC',description:'Send the revised plan',owner:'Alan Carter',priority:'Medium',raised:'2026-10-05',source:'x'},match:'strong',flags:[],decision:'pending'}],meeting:{key:'calendar:'+m.id,title:m.title,date:m.day,projects:['ABC'],draft:null,transcript:null,minutes_decision:'pending',file_ops:[]}})}); };"""


class IntakeBase(LiveBrowserCase):
    """One live server and a fixture week (the Monday of 05-10-2026, evening): ev-1 transcript loaded, ev-2 available, ev-3 Busy."""
    shared_server = True
    width, height = 1400, 1000

    @classmethod
    def load(cls, v):
        populate(v)
        for f in (v.root / "inbox").glob("*"):
            f.unlink()                       # the sample's uploads would be ready rows too
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
        (root / "system/staging/transcripts.json").write_text(json.dumps({"version": 1, "checked": {
            "ev-1": {"status": "available", "uri": "meeting-transcript:///a", "count": 1, "checked": f"{DAY} 07:00"},
            "ev-2": {"status": "available", "uri": "meeting-transcript:///b", "count": 1, "checked": f"{DAY} 07:00"}}}))
        pin_page_clock(self.b, NOW)
        self.b.eval("irSetView('list'); irStage.value='all'; irOpen.value=null; irBusy.value=[]")
        self.b.eval("reloadData().then(()=>go('intake-review'))")
        self.b.wait("VIEW==='intake-review' && !!document.querySelector('#v-intake-review [data-irm]')")

    # -- helpers
    def row(self, title):
        return f"document.querySelector('#v-intake-review [data-irm=\"' + D.intake_review.meetings.find(m=>m.src!=='draft'&&m.title===" + json.dumps(title) + ").id + '\"]')"

    def sel(self, title, suffix=""):
        mid = self.b.eval("D.intake_review.meetings.find(m=>m.src!=='draft'&&m.title===" + json.dumps(title) + ").id")
        return f'#v-intake-review [data-irm="{mid}"]{suffix}'

    def cleared(self):
        p = self.v.root / "system/staging/intake-cleared.json"
        return json.loads(p.read_text())["cleared"] if p.exists() else []

    def patch(self, title, **fields):
        """Change one row of the model the page was given (new objects, so the page redraws) and redraw."""
        self.b.eval("(()=>{ const T=%s, P=%s; D.intake_review={...D.intake_review, meetings: D.intake_review.meetings.map(m=>m.src!=='draft'&&m.title===T?{...m,...P}:m)}; irTick.value++; })()"
                    % (json.dumps(title), json.dumps(fields)))

    def unfold(self, sec):
        """Show a folded section (Later, Not needed start folded)."""
        self.b.wait(f"!!document.querySelector('[data-irfold={sec}]')")
        if self.b.eval(f"document.querySelector('[data-irfold={sec}]').getAttribute('aria-expanded')") == "false":
            self.b.click(f"[data-irfold={sec}]")

    def stage_stub(self):
        self.b.eval(GATE)

    def key(self, title, k):
        self.b.eval(f"(()=>{{ const r={self.row(title)}; r.focus(); r.dispatchEvent(new KeyboardEvent('keydown',{{key:{json.dumps(k)},bubbles:true}})); }})()")
