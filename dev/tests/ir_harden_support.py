"""Shared fixture for the hardening tests against Team Cap's p250-a (test_intake_review_harden.py). A real live server in a throwaway vault, a fictional calendar
for the pinned week, and the run engine stubbed in the page (what the old tests did for Process selected): jobLive records a
transcript load and saves the file, askLive records the process request and leaves a draft waiting in Review, as cx-minutes would.

The meetings (Monday 05-10-2026, the pinned day, 18:00 so all have ended):
  ev-1 ABC Steering 09:00        transcript available, already loaded in the inbox   -> ready
  ev-2 Weekly sync 12 15:00      sweep says Not transcribed                          -> waiting
  ev-3 Busy 08:30                private                                             -> waiting
  ev-6 Vendor check-in 16:00     transcript available, not loaded yet                -> ready (Process loads it first)
  ev-7 ABC Board matters 12:00       confidential, transcript available                  -> ready
"""
import base64
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase, pin_page_clock  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_meetings import week_calendar  # noqa: E402

NOW = "2026-10-05 18:00"
DAY = "2026-10-05"

STUBS = r"""
window.LOADED=[]; window.ASKED=[]; window.GATE=null;
const item=(t)=>({n:1,op:"new",table:"actions",values:{project:"ABC",description:t,owner:"Sara Example",raised:"2026-10-05",source:"Minutes"},match:"strong",flags:[],decision:"pending"});
jobLive=async(url,body)=>{ LOADED.push([url,body.id]);
  if(url==="/api/transcripts/load"){ const t="WEBVTT\n\nEvent ID: "+body.id+"\n\n00:00:01.000 --> 00:00:05.000\nHello\n";
    await api("/api/inbox/upload",{name:"2026-10-05 "+body.id+".vtt",data:btoa(t)}); } };
askLive=async(q,c)=>{ ASKED.push([q,c]); if(window.GATE) await window.GATE;
  const id=(q.match(/ev-\d+/)||[])[0]||(/Steering/.test(q)?"ev-1":"");
  if(id) await api("/api/fs",{op:"write",path:"system/staging/proposed-test-"+id+".json",text:JSON.stringify({created:"2026-10-05T09:00:00",source_run:"cx-minutes",files:[],items:[item("Do the thing for "+id)],
    meeting:{key:"calendar:"+id,title:"Stub",date:"2026-10-05",projects:["ABC"],draft:null,transcript:null,minutes_decision:"pending",file_ops:[]}})}); };
"""


class IrHardenCase(LiveBrowserCase):
    width, height = 1400, 1000

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": NOW}

    @classmethod
    def load(cls, v):
        populate(v)
        week_calendar(v, today=date(2026, 10, 5))
        f = v.root / "system/staging/calendar.json"
        cal = json.loads(f.read_text())
        cal["days"][DAY] += [{"id": "ev-6", "start": "16:00", "end": "16:30", "title": "Vendor check-in", "teams": True},
                             {"id": "ev-7", "start": "12:00", "end": "12:30", "title": "ABC Board matters", "teams": True,
                              "sensitivity": "confidential"}]
        f.write_text(json.dumps(cal))
        cls.set_transcripts(v, {"ev-1": "available", "ev-6": "available", "ev-7": "available", "ev-2": "not_transcribed"})
        (v.root / "inbox" / f"{DAY} ABC Steering.vtt").write_text("WEBVTT\n\nEvent ID: ev-1\n\n00:00:01.000 --> 00:00:05.000\nHello\n")

    @staticmethod
    def set_transcripts(v, status):
        (v.root / "system/staging/transcripts.json").write_text(json.dumps(
            {"checked": {k: {"status": s, "checked": f"{DAY} 17:00"} for k, s in status.items()}}))

    def setUp(self):
        super().setUp()
        pin_page_clock(self.b, NOW)
        self.b.eval("try{ localStorage.removeItem('creaite-ir-view'); }catch(e){} irSetView('list'); go('intake-review')")
        self.b.wait("!!document.querySelector('#v-intake-review [data-irm]')")
        self.b.eval(STUBS)

    # ---- helpers ----
    def row(self, title):
        """The id of the row whose title starts with `title`."""
        return self.b.eval("(t=>{ const r=[...document.querySelectorAll('#v-intake-review [data-irv=list] [data-irm]')].find(x=>x.querySelector('.icmeethd').textContent.trim().startsWith(t)); return r?r.dataset.irm:null; })(%s)" % json.dumps(title))

    def sel(self, title, extra=""):
        rid = self.row(title)
        self.assertIsNotNone(rid, f"no row for {title}")
        return f"#v-intake-review [data-irv=list] [data-irm={rid}]{extra}"

    def titles(self):
        return self.b.eval("[...document.querySelectorAll('#v-intake-review [data-irv=list] [data-irm] .icmeethd')].map(t=>t.textContent.trim())")

    def buttons(self, title):
        return self.b.eval("[...document.querySelectorAll(%s + ' [data-ira]')].map(x=>x.dataset.ira)" % json.dumps(self.sel(title)))

    def text(self, title):
        return self.b.eval("document.querySelector(%s).innerText" % json.dumps(self.sel(title)))

    def cleared(self):
        p = self.v.root / "system/staging/intake-cleared.json"
        return json.loads(p.read_text())["cleared"] if p.exists() else []

    def snack(self):
        return self.b.eval("document.getElementById('snackT').textContent")

    def upload(self, name, text="WEBVTT\n\nHello\n"):
        data = base64.b64encode(text.encode()).decode()
        self.b.eval("api('/api/inbox/upload',{name:%s,data:%s}).then(()=>reloadData())" % (json.dumps(name), json.dumps(data)))
        self.b.wait("(D.inbox||[]).some(f=>f.name==%s)" % json.dumps(name))
        self.b.eval("go('intake-review')")
