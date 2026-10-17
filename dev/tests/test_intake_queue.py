"""#179, Intake step 1: one queue, one decision per row, fewer buttons. A real Chrome against the real live server, desktop width only.

The clock is fixed (CREAITE_NOW for the server, pin_page_clock for the page): Friday 16-10-2026 17:30, so every age is the same on every
run. The calendar is fictional. The processing run is a stand-in that the test holds open and lets go, so "in the background" is seen
while it happens. Microsoft 365 is never called.

Run: python3 dev/tests/test_intake_queue.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase, pin_page_clock  # noqa: E402
from test_dashboard import populate  # noqa: E402

NOW = "2026-10-16 17:30"            # a Friday; the 12th is 4 days back (amber), the 14th 2 days (quiet)

CAL = {"fetched": "2026-10-16 07:00", "days": {
    "2026-10-12": [{"id": "ev-a", "start": "15:00", "end": "16:00", "all_day": False, "title": "Example Programme steering", "where": "Teams", "teams": True, "private": False, "organiser": "Priya Nair"}],
    "2026-10-13": [{"id": "ev-e", "start": "11:00", "end": "12:00", "all_day": False, "title": "Data owners workshop", "where": "Teams", "teams": True, "private": False, "organiser": "Lena Park"},
                   {"id": "ev-f", "start": "09:30", "end": "10:00", "all_day": False, "title": "Risk review", "where": "Teams", "teams": True, "private": False, "organiser": "Priya Nair"}],
    "2026-10-14": [{"id": "ev-b", "start": "10:30", "end": "11:00", "all_day": False, "title": "Vendor onboarding check-in", "where": "Teams", "teams": True, "private": False, "organiser": "Sam Okoro"}],
    "2026-10-15": [{"id": "ev-c", "start": "14:00", "end": "15:00", "all_day": False, "title": "Budget walk-through", "where": "Room 4", "teams": True, "private": False, "organiser": "Priya Nair"},
                   {"id": "ev-d", "start": "16:00", "end": "16:30", "all_day": False, "title": "Supplier call", "where": "Teams", "teams": True, "private": False, "organiser": "Sam Okoro"}],
    "2026-10-16": [{"id": "ev-g", "start": "18:00", "end": "19:00", "all_day": False, "title": "Later today", "where": "Teams", "teams": True, "private": False, "organiser": True}]}}

READY = ["Example Programme steering", "Vendor onboarding check-in", "Budget walk-through"]      # transcripts available, not processed
WAITING = ["Data owners workshop", "Supplier call"]                                                # not transcribed, none
STEER_VTT = "WEBVTT\n\nNOTE\nEvent ID: ev-a\n\n00:00:01.000 --> 00:00:05.000\nWelcome\n"


class Case(LiveBrowserCase):
    width, height = 1500, 1000

    @classmethod
    def load(cls, v):
        populate(v)
        (v.root / "system/staging/calendar.json").write_text(json.dumps(CAL))
        chk = lambda s, **k: {"status": s, "checked": "2026-10-16 07:00", **k}  # noqa: E731
        (v.root / "system/staging/transcripts.json").write_text(json.dumps({"version": 1, "checked": {
            "ev-a": chk("available", uri="meeting-transcript:///a", count=1), "ev-b": chk("available", uri="meeting-transcript:///b", count=1),
            "ev-c": chk("available", uri="meeting-transcript:///c", count=1), "ev-d": chk("none"), "ev-e": chk("not_transcribed", uri="meeting-transcript:///e", count=0),
            "ev-f": chk("available", uri="meeting-transcript:///f", count=1)}}))
        (v.root / "system/processed.txt").write_text("2026-10-13 | calendar:ev-f | projects/x | 1\n")
        (v.root / "inbox" / "2026-10-12 Example Programme steering.vtt").write_text(STEER_VTT)        # ev-a's transcript is loaded already

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": NOW}

    def setUp(self):
        super().setUp()
        pin_page_clock(self.b, NOW)
        self.assertEqual(self.b.eval("TODAY"), "2026-10-16")
        self.b.eval("localStorage.removeItem('creaite-intake-later'); localStorage.removeItem('creaite-intake-reasons')")
        self.open_intake()

    def open_intake(self):
        self.b.eval("go('inbox')")
        self.b.wait("document.querySelector('#mtgBody .inrow')")

    # what the page shows
    def groups(self):
        return self.b.eval("[...document.querySelectorAll('#mtgBody .ingrp h2')].map(h=>h.textContent)")

    def titles(self, group):
        return self.b.eval(f"[...document.querySelectorAll('#mtgBody .inrow[data-g=\"{group}\"] .int')].map(x=>x.textContent.trim())")

    def buttons(self, mid):
        return self.b.eval(f"[...document.querySelectorAll('#mtgBody [data-mid=\"{mid}\"] .inact button')].map(x=>x.textContent.trim())")

    def row(self, mid):
        return f'#mtgBody [data-mid="{mid}"]'

    def label(self):
        return self.b.eval("document.getElementById('inAll').textContent")

    def n_files(self):
        return self.b.eval("uploadedFiles().filter(f=>f.state==='new').length")


class Queue(Case):
    shared_server = True

    def test_one_queue_groups(self):
        """Ready, Upload files, Waiting, Done recently in that order; Later only once a row is in it; a group with no rows is not drawn."""
        self.assertEqual(self.groups(), ["Ready", "Upload files", "Waiting", "Done recently"])
        self.assertEqual(sorted(self.titles("ready")), sorted(READY))
        self.assertEqual(sorted(self.titles("waiting")), sorted(WAITING))
        self.assertEqual(sorted(self.titles("done")), ["Copy of filed.vtt", "Risk review"])        # a processed meeting and an already-filed file
        self.assertNotIn("Later today", self.b.eval("document.getElementById('mtgBody').textContent"))      # it has not ended yet
        self.assertGreaterEqual(len(self.titles("files")), 1)                                                # the dropped files are rows in the same list
        self.b.eval("localStorage.setItem('creaite-intake-later', JSON.stringify({'ev-b':'available'})); renderInbox()")
        self.assertEqual(self.groups(), ["Ready", "Upload files", "Waiting", "Later", "Done recently"])
        self.assertEqual(self.titles("later"), ["Vendor onboarding check-in"])
        self.b.eval("localStorage.removeItem('creaite-intake-later'); D.meetings.rows=[]; D.inbox=[]; renderInbox()")
        self.assertEqual(self.groups(), ["Upload files"])                                                    # empty groups are not drawn; the drop target stays

    def test_three_actions_per_ready_row(self):
        for mid in ("ev-a", "ev-b", "ev-c"):
            self.assertEqual(self.buttons(mid), ["Process", "Not needed", "Later"], mid)
        for mid in ("ev-d", "ev-e"):
            self.assertEqual(self.buttons(mid), ["Not needed"], mid)                                         # a waiting row has only Not needed
        self.assertEqual(self.b.eval(f"getComputedStyle(document.querySelector('{self.row('ev-a')} [data-ia=process]')).backgroundColor!==getComputedStyle(document.querySelector('{self.row('ev-a')} [data-ia=not]')).backgroundColor"), True)   # Process is the primary

    def test_removed_controls_are_gone(self):
        text = self.b.eval("document.getElementById('v-inbox').innerText")
        for gone in ("Select new", "Select with transcripts", "Process selected", "Load into inbox", "Clear day"):
            self.assertNotIn(gone, text)
        self.assertEqual(self.b.eval("['mtgNew','mtgTx','mtgLoad','mtgGo','inboxNew','inboxGo'].filter(i=>document.getElementById(i))"), [])
        self.assertEqual(self.b.eval("document.querySelectorAll('#mtgBody table, #mtgBody th, #inboxTbl').length"), 0)       # no nine-column table
        self.assertNotRegex(text, r"(?i)inbox")                                                              # not in any button, state or line of the page
        self.assertEqual(self.b.eval("[...document.querySelectorAll('#v-inbox button, #v-inbox [title], #v-inbox [aria-label]')].filter(x=>/inbox/i.test(x.textContent+x.title+(x.getAttribute('aria-label')||'')+(x.dataset.tip||''))).length"), 0)

    def test_process_all_ready_count_and_disabled(self):
        n = len(READY) + self.n_files()
        self.assertEqual(self.label(), f"Process all ready ({n})")
        self.assertFalse(self.b.eval("document.getElementById('inAll').disabled"))
        got = self.b.eval("""(()=>{ D.meetings.rows=[]; D.inbox=[]; renderInbox(); const e=document.getElementById('inAll');
          return [e.textContent, e.disabled, parseFloat(getComputedStyle(e).opacity), e.classList.contains('off')]; })()""")   # one step: a background reload cannot slip in
        self.assertEqual(got[:2], ["Process all ready (0)", True])
        self.assertLess(got[2], 1)                                                                            # and it looks disabled
        self.assertTrue(got[3])

    def test_age_is_quiet_and_an_outlier_follows_reviews_rule(self):
        """#177's rule, shared: an outlier is more than twice the stale setting, and none is marked when every ready row is old."""
        age = lambda mid: self.b.eval(f"(e=>[e.textContent,e.classList.contains('old'),getComputedStyle(e).color])(document.querySelector('{self.row(mid)} .inage'))")  # noqa: E731
        self.assertEqual([age(m)[1] for m in ("ev-a", "ev-b", "ev-c")], [False, False, False])         # the default 7 days: 4 days is not an outlier
        self.b.eval("S.staleDays=1; renderInbox()")                                                      # twice 1 is 2: 4 days is, 2 and 1 are not
        self.assertEqual([age(m)[1] for m in ("ev-a", "ev-b", "ev-c")], [True, False, False])
        self.assertNotEqual(age("ev-a")[2], age("ev-b")[2])                                              # amber against quiet
        self.b.eval("D.inbox=[]; D.meetings.rows=D.meetings.rows.filter(r=>r.id==='ev-a'); renderInbox()")   # every ready row is past the setting
        self.assertFalse(age("ev-a")[1])                                                                 # a banner's job in Review; here nothing is marked

    def test_intake_and_review_word_an_age_the_same(self):
        """One helper: the age text on a row is Review's for the same number of days."""
        for mid, n in (("ev-a", 4), ("ev-b", 2), ("ev-c", 1)):
            self.assertEqual(self.b.eval(f"document.querySelector('{self.row(mid)} .inage').textContent"),
                             self.b.eval(f"rvAgeText({{age:{n}}})"))
        self.assertEqual(self.b.eval("[0,1,2,12].map(n=>[ageWords(n),rvAgeText({age:n})])"),
                         [["today", "today"], ["1 day", "1 day"], ["2 days", "2 days"], ["12 days", "12 days"]])
        self.assertEqual(self.b.eval("[ageOutlier(15,false),ageOutlier(14,false),ageOutlier(15,true)]"), [True, False, False])

    def test_quiet_buttons_outside_intake_keep_their_style(self):
        """The Intake-only quiet style must not reach other pages' .btn.quiet (the sidebar dialog's Reset, for one)."""
        got = self.b.eval("""(()=>{ const b=document.createElement('button'); b.className='btn quiet'; document.getElementById('v-today').appendChild(b);
          const t=document.createElement('i'); t.style.color='var(--accent)'; document.body.appendChild(t);
          const out=[getComputedStyle(b).color,getComputedStyle(t).color]; b.remove(); t.remove(); return out; })()""")
        self.assertEqual(got[0], got[1])                                                                 # accent text, as the global rule has it
        inside = self.b.eval("getComputedStyle(document.querySelector('#mtgBody .indtb')).color")
        self.assertNotEqual(inside, got[1])                                                              # Intake's own is muted

    def test_details_holds_organiser_and_where(self):
        row = self.row("ev-c")
        self.assertEqual(self.b.eval("[...document.querySelectorAll('#mtgBody th')].length"), 0)             # neither is a column
        self.assertNotIn("Priya Nair", self.b.eval(f"document.querySelector('{row}').innerText"))
        self.assertNotIn("Room 4", self.b.eval(f"document.querySelector('{row}').innerText"))
        self.b.click(f"{row} [data-ia=det]")
        self.b.wait(f"document.querySelector('{row} .indet')")
        det = self.b.eval(f"document.querySelector('{row} .indet').innerText")
        self.assertIn("Organiser: Priya Nair", det)
        self.assertIn("Where:", det)
        self.assertEqual(self.b.eval(f"document.querySelector('{row} [data-ia=det]').getAttribute('aria-expanded')"), "true")

    def test_empty_state_and_live_server_line(self):
        live = "need creaite running in live mode"
        self.assertEqual(self.b.eval("document.getElementById('v-inbox').innerText").count(live), 1)         # said once, in one quiet line
        self.assertEqual(self.b.eval("[...document.querySelectorAll('#v-inbox button, #v-inbox [title], #v-inbox [data-tip]')].filter(x=>/live server|live mode/i.test((x.title||'')+(x.dataset.tip||'')+(x.getAttribute('aria-label')||''))).length"), 0)   # never a button's tooltip
        self.b.eval("D.meetings.rows=D.meetings.rows.filter(r=>r.processed||r.draft); D.inbox=[]; renderInbox()")
        self.assertIn("Nothing ready. A meeting appears here when its transcript arrives.", self.b.eval("document.getElementById('mtgBody').innerText"))
        self.b.eval("D.meetings.rows=[]; D.inbox=[]; renderInbox()")
        self.assertIn("Nothing here yet. Meetings appear when they end, and transcripts as they arrive.", self.b.eval("document.getElementById('mtgBody').innerText"))
        self.assertNotIn("How Intake works", self.b.eval("document.getElementById('v-inbox').innerText"))   # no link until Help has the page
        self.assertEqual(self.b.eval("document.getElementById('v-inbox').innerText").count(live), 1)

    def test_badge_matches_today(self):
        """One count, one meaning: the rail badge, the page and Today's rows are the same ready list."""
        n = len(READY) + self.n_files()
        self.assertEqual(self.b.eval("document.getElementById('inboxBadge').textContent"), str(n))
        self.assertIn(f"{n} ready", self.b.eval("document.getElementById('inSub').textContent"))
        self.b.eval("go('today')")
        self.b.wait("document.querySelector('#tdList')")
        today = self.b.eval("toDecideRows().filter(r=>r.kind==='transcript').length")
        self.assertEqual(today, n)
        self.assertEqual(self.b.eval("readyCount()"), n)
        self.b.eval("localStorage.setItem('creaite-intake-later', JSON.stringify({'ev-b':'available'}))")     # set aside: out of both
        self.assertEqual(self.b.eval("toDecideRows().filter(r=>r.kind==='transcript').length"), n - 1)
        self.assertEqual(self.b.eval("readyCount()"), n - 1)

    def test_keys_match_review(self):
        b = self.b
        cur = lambda: b.eval("document.querySelector('#mtgBody .inrow.sel').dataset.ik")  # noqa: E731
        first = cur()
        self.assertEqual(first, b.eval("document.querySelector('#mtgBody .inrow[data-g=ready]').dataset.ik"))
        b.eval("document.activeElement&&document.activeElement.blur()")
        b.key("ArrowDown")
        second = cur()
        self.assertNotEqual(first, second)
        b.key("ArrowUp")
        self.assertEqual(cur(), first)
        self.assertGreater(float(b.eval("parseFloat(getComputedStyle(document.querySelector('#mtgBody .inrow.sel')).outlineWidth)")), 0)   # the focus ring
        b.key("N")                                                                                               # N: the reasons menu, not a note
        b.wait("document.getElementById('inNotMenu')")
        self.assertFalse(b.eval("document.getElementById('captureDrawer')&&document.getElementById('captureDrawer').open"))
        b.key("Escape")                                                                                          # Esc closes the menu
        b.wait("!document.getElementById('inNotMenu')")
        self.assertEqual(b.eval("document.activeElement.dataset.ia"), "not")


class Moves(Case):
    """Tests that change data get their own server."""

    def pick(self, mid, reason):
        self.b.click(f"{self.row(mid)} [data-ia=not]")
        self.b.wait("document.getElementById('inNotMenu')")
        self.assertEqual(self.b.eval("[...document.querySelectorAll('#inNotMenu [role=menuitem]')].map(x=>x.textContent.trim())"),
                         ["Informal chat", "No decisions", "Duplicate of another meeting", "Other"])
        self.b.eval("[...document.querySelectorAll('#inNotMenu [role=menuitem]')].find(x=>x.textContent.trim()==%s).click()" % json.dumps(reason))

    def cleared(self):
        p = self.v.root / "system/staging/intake-cleared.json"
        return sorted(e["key"] for e in json.loads(p.read_text())["cleared"]) if p.exists() else []

    def test_not_needed_asks_for_a_reason_and_undoes(self):
        b = self.b
        before = len(self.titles("ready"))
        b.eval("document.getElementById('snackT').textContent=''")
        self.pick("ev-b", "Informal chat")
        b.wait("!document.querySelector('#mtgBody [data-mid=\"ev-b\"]')", 20)                                  # the row leaves the queue
        self.assertEqual(len(self.titles("ready")), before - 1)
        self.assertEqual(self.cleared(), ["ev-b"])                                                           # the existing clear route and record
        b.wait("/Not needed: Informal chat/.test(document.getElementById('snackT').textContent)", 20)
        b.click("#mtgBody .mtgcleared .clrlink")                                                             # the Cleared list names the reason
        b.wait("document.querySelector('#mtgBody .mtgclrlist')")
        self.assertIn("Informal chat", b.eval("document.querySelector('#mtgBody .clrrow').innerText"))
        b.click("#snackU")                                                                                   # Undo
        b.wait("document.querySelector('#mtgBody [data-mid=\"ev-b\"]')", 20)
        self.assertEqual(self.cleared(), [])
        self.pick("ev-c", "Duplicate of another meeting")                                                    # and again, put back from the Cleared list
        b.wait("!document.querySelector('#mtgBody [data-mid=\"ev-c\"]')", 20)
        b.click("#mtgBody .mtgcleared .clrlink")
        b.wait("document.querySelector('#mtgBody .mtgclrlist')")
        b.click('#mtgBody .mtgclr[data-clr="restore"]')
        b.wait("document.querySelector('#mtgBody [data-mid=\"ev-c\"]')", 20)
        self.assertEqual(self.cleared(), [])

    def test_later_survives_reload_and_returns(self):
        b = self.b
        b.click(f"{self.row('ev-a')} [data-ia=later]")
        b.wait("document.querySelector('#mtgBody .inrow[data-g=later][data-mid=\"ev-a\"]')")
        self.assertNotIn("Example Programme steering", self.titles("ready"))
        self.assertEqual(self.titles("later"), ["Example Programme steering"])
        self.assertEqual(self.buttons("ev-a"), ["Back to Ready", "Not needed"])
        self.assertEqual(self.label(), f"Process all ready ({len(READY) - 1 + self.n_files()})")              # a set-aside row is not processed with the rest
        b.reload("typeof go==='function' && LIVE")
        self.open_intake()
        self.assertEqual(self.titles("later"), ["Example Programme steering"])                               # survives a reload
        b.click(f"{self.row('ev-a')} [data-ia=unlater]")
        b.wait("document.querySelector('#mtgBody .inrow[data-g=ready][data-mid=\"ev-a\"]')")
        # a meeting set aside while it had no transcript comes back to Ready when one arrives
        b.eval("localStorage.setItem('creaite-intake-later', JSON.stringify({'ev-d':''})); renderInbox()")
        self.assertEqual(self.titles("later"), ["Supplier call"])
        b.eval("D.meetings.rows.find(r=>r.id==='ev-d').transcript='available'; renderInbox()")
        self.assertIn("Supplier call", self.titles("ready"))
        self.assertEqual(b.eval("JSON.parse(localStorage.getItem('creaite-intake-later')||'{}')['ev-d']"), None)

    def test_upload_files_become_rows(self):
        b = self.b
        n0, rows0 = len(READY) + self.n_files(), len(self.titles("files"))
        b.eval("""(()=>{ const dt=new DataTransfer(); dt.items.add(new File(["WEBVTT\\n\\n00:00:01.000 --> 00:00:03.000\\nHi\\n"],"Dropped notes.vtt"));
          document.querySelector('#mtgBody .int').dispatchEvent(new DragEvent('drop',{dataTransfer:dt,bubbles:true,cancelable:true})); })()""")   # a drop on a row: anywhere on the page
        b.wait("[...document.querySelectorAll('#mtgBody .inrow[data-g=files] .int')].some(x=>x.textContent.trim()==='Dropped notes.vtt')", 20)
        self.assertEqual(len(self.titles("files")), rows0 + 1)
        self.assertTrue((self.v.root / "inbox" / "Dropped notes.vtt").exists())
        sel = '#mtgBody .inrow[data-inf$="Dropped notes.vtt"]'
        self.assertEqual(b.eval(f"[...document.querySelectorAll('{sel} .inact button')].map(x=>x.textContent.trim())"), ["Process", "Not needed", "Later"])
        self.assertEqual(self.label(), f"Process all ready ({n0 + 1})")
        self.assertEqual(b.eval("document.getElementById('inboxBadge').textContent"), str(n0 + 1))
        b.click(f"{sel} [data-ia=later]")                                                                    # Later works on a file too
        b.wait("document.querySelector('#mtgBody .inrow[data-g=later][data-inf$=\"Dropped notes.vtt\"]')")
        self.assertEqual(self.label(), f"Process all ready ({n0})")

    HOLD = """askLive=async(q,c)=>{ window.ASKED.push(q); if(!/^process /.test(q)) return;
        RUN={id:'t',ctl:new AbortController()}; setRunning(true);
        await new Promise(r=>{ window.REL=r; }); RUN=null; setRunning(false);
        await api("/api/fs",{op:"write",path:"system/staging/proposed-test-mtg.json",text:JSON.stringify({created:"2026-10-16T09:00:00",source_run:"cx-minutes",files:[],items:[],meeting:{key:"calendar:ev-a",title:"Example Programme steering",date:"2026-10-12",projects:["ABC"],draft:null,transcript:null,minutes_decision:"pending",file_ops:[]}})}); }; window.ASKED=[];"""

    # every ready meeting is loaded (an upload carrying its event ID) and gets a draft; calls are recorded in order
    STUBS = """window.CALLS=[]; window.b64=s=>btoa(unescape(encodeURIComponent(s)));
        jobLive=async(url,body)=>{ CALLS.push('load:'+body.id); const m=D.meetings.rows.find(r=>r.id===body.id);
          await api("/api/inbox/upload",{name:m.day+" "+m.title+".vtt",data:b64("WEBVTT\\n\\nNOTE\\nEvent ID: "+body.id+"\\n\\n00:00:01.000 --> 00:00:02.000\\nHi\\n")}); };
        askLive=async(q)=>{ CALLS.push('ask:'+q); const m=D.meetings.rows.find(r=>q.includes(r.title));
          if(m) await api("/api/fs",{op:"write",path:"system/staging/proposed-test-"+m.id+".json",text:JSON.stringify({created:"2026-10-16T09:00:00",source_run:"cx-minutes",files:[],items:[],meeting:{key:"calendar:"+m.id,title:m.title,date:m.day,projects:["ABC"],draft:null,transcript:null,minutes_decision:"pending",file_ops:[]}})}); };"""

    def test_process_runs_in_background(self):
        b = self.b
        b.eval(self.HOLD)
        b.eval("closeChat()")
        b.click(f"{self.row('ev-a')} [data-ia=process]")
        b.wait(f"/Processing/.test(document.querySelector('{self.row('ev-a')} .instate').innerText)", 20)
        self.assertFalse(b.eval("document.getElementById('chat').classList.contains('on')"))                  # ask creaite did not open by itself
        self.assertEqual(self.b.eval(f"document.querySelectorAll('{self.row('ev-a')} .inprog').length"), 1)  # progress is on the row
        self.assertEqual(self.buttons("ev-a"), ["Processing"])
        self.assertTrue(b.eval("!!RUN"))                                                                      # a run is active (the engine is busy)...
        self.assertTrue(b.eval(f"document.querySelector('{self.row('ev-b')} [data-ia=process]').disabled"))   # ...so other rows wait, one run at a time
        self.assertTrue(b.eval("document.getElementById('inAll').disabled"))
        b.eval("openChat()")                                                                                  # and ask creaite is free to use meanwhile
        b.wait("document.getElementById('chat').classList.contains('on')")
        b.eval("document.getElementById('chIn').focus()")
        b.type("hello there")
        b.key("Enter")
        b.wait("ASKED.includes('hello there')", 20)
        self.assertTrue(b.eval(f"document.querySelector('{self.row('ev-a')}').classList.contains('run')"))    # still running
        b.eval("closeChat(); REL()")                                                                          # the run ends
        b.wait("document.querySelector('#mtgBody .inrow[data-g=done][data-mid=\"ev-a\"]')", 30)
        done = b.eval("document.querySelector('#mtgBody .inrow[data-g=done][data-mid=\"ev-a\"]').innerText")
        self.assertIn("Draft ready in Review", done)
        self.assertEqual(self.buttons("ev-a"), ["Open Review"])
        b.click(f"{self.row('ev-a')} [data-ia=review]")
        b.wait("VIEW==='review'")

    def test_process_all_ready_attempts_every_ready_row_and_leaves_none_in_ready(self):
        b = self.b
        b.eval(self.STUBS)
        b.eval("closeChat()")
        order = b.eval("readyList().map(r=>r.kind==='m'?r.m.id:'file')")
        self.assertEqual(sorted(order), ["ev-a", "ev-b", "ev-c", "file", "file"])
        b.click("#inAll")
        b.wait("!document.querySelector('#mtgBody .inrow[data-g=ready]') && CALLS.filter(c=>c.startsWith('ask:')).length>=4", 60)
        self.assertFalse(b.eval("document.getElementById('chat').classList.contains('on')"))
        calls = b.eval("CALLS")
        asked = [c for c in calls if c.startswith("ask:")]
        self.assertEqual(len(asked), 4)                                                                       # every meeting once, then the files once
        titles = {"ev-a": "Example Programme steering", "ev-b": "Vendor onboarding check-in", "ev-c": "Budget walk-through"}
        meetings = [m for m in order if m != "file"]
        for m, c in zip(meetings, asked):
            self.assertIn(titles[m], c)                                                                      # in the list's order, none dropped
        self.assertIn("ABC weekly sync.vtt", asked[3])
        self.assertIn("Recording.vtt", asked[3])
        self.assertEqual(sorted(c for c in calls if c.startswith("load:")), ["load:ev-b", "load:ev-c"])      # ev-a was loaded already
        self.assertEqual(b.eval("document.querySelectorAll('#mtgBody .inrow[data-g=ready]').length"), 0)     # none is left in Ready
        self.assertTrue(all(m in self.titles("done") for m in titles.values()))

    def test_stop_stops_the_batch(self):
        b = self.b
        b.eval(self.STUBS + """ askLive=async(q)=>{ CALLS.push('ask:'+q); RUN={id:'t',ctl:new AbortController()}; await stopAsk(); RUN=null; };""")
        b.click("#inAll")
        b.wait("CALLS.some(c=>c.startsWith('ask:'))", 30)
        b.wait("!RUN && !Object.values(MRUN).some(v=>v==='processing'||v==='loading')", 30)
        b.pump(1.0)
        calls = b.eval("CALLS")
        self.assertEqual([c for c in calls if c.startswith("ask:")][1:], [])                                  # nothing more started after Stop
        self.assertEqual(len([c for c in calls if c.startswith("load:")]), 1)                                 # not even a second load
        self.assertGreaterEqual(b.eval("document.querySelectorAll('#mtgBody .inrow[data-g=ready]').length"), 2)  # the others wait, unprocessed

    def test_a_row_stays_busy_between_the_load_and_the_process(self):
        b = self.b
        b.eval(self.STUBS + """ askLive=async(q)=>{ CALLS.push('ask:'+q); RUN={id:'t',ctl:new AbortController()}; await new Promise(r=>{ window.REL=r; }); RUN=null; };
          window.SEEN=[]; window.POLL=setInterval(()=>SEEN.push(!!document.querySelector('#mtgBody [data-mid="ev-b"] [data-ia=process]')),2);""")
        b.click(f"{self.row('ev-b')} [data-ia=process]")
        b.wait("CALLS.some(c=>c.startsWith('ask:'))", 30)
        b.eval("clearInterval(POLL); REL()")
        seen = b.eval("SEEN")
        first_gone = seen.index(False)
        self.assertNotIn(True, seen[first_gone:])                                                             # Process never came back before it ended

    def test_enter_processes_and_h_sets_later(self):
        b = self.b
        b.eval(self.HOLD)
        b.eval("document.activeElement&&document.activeElement.blur()")
        b.key("H")
        b.wait("document.querySelector('#mtgBody .inrow[data-g=later]')")
        self.assertEqual(self.titles("later"), ["Budget walk-through"])                                       # H: the cursor row (the first ready one)
        b.key("ArrowDown")                                                                                    # after H the cursor is on the next row (ev-b)
        self.assertEqual(b.eval("document.querySelector('#mtgBody .inrow.sel').dataset.mid"), "ev-a")
        b.key("Enter")                                                                                        # Enter: Process on the cursor row
        b.wait(f"document.querySelector('{self.row('ev-a')}').classList.contains('run')", 20)
        b.wait("ASKED.some(q=>/^process inbox\\/.*steering/.test(q))", 20)
        b.eval("REL()")

    def test_a_loaded_transcript_always_has_a_row(self):
        """Process loaded it and failed, and its meeting has left the calendar window: it is a row of its own, counted once."""
        b = self.b
        (self.v.root / "inbox" / "2026-09-01 Old call.vtt").write_text("WEBVTT\n\nNOTE\nEvent ID: ev-old\n\n00:00:01.000 --> 00:00:02.000\nHi\n")
        (self.v.root / "inbox" / "2026-09-01 Old call - chat.txt").write_text("Event ID: ev-old\n\n[08:01] Sara: hi\n")
        n0 = b.eval("readyCount()")
        b.eval("reloadData()")
        b.wait("(D.inbox||[]).some(f=>f.event==='ev-old')", 20)
        self.assertEqual(b.eval("readyCount()"), n0 + 1)                                                      # the chat companion is not a second one
        self.assertIn("2026-09-01 Old call.vtt", self.titles("files"))
        self.assertNotIn("2026-09-01 Old call - chat.txt", self.titles("files"))
        self.assertIn("Loaded transcript", b.eval("document.querySelector('#mtgBody .inrow[data-inf$=\"Old call.vtt\"]').innerText"))
        self.assertEqual(b.eval("document.getElementById('inboxBadge').textContent"), str(n0 + 1))
        self.assertEqual(b.eval("document.getElementById('inAll').textContent"), f"Process all ready ({n0 + 1})")
        b.eval("go('today')")
        b.wait("document.querySelector('#tdList')")
        self.assertEqual(b.eval("toDecideRows().filter(r=>r.kind==='transcript').length"), n0 + 1)

    def test_today_file_row_says_when_ask_creaite_is_busy(self):
        b = self.b
        b.eval("go('today')")
        b.wait("document.querySelector('#tdList')")
        b.eval("document.getElementById('snackT').textContent=''; RUN={id:'x'}")
        b.eval("tdAct({kind:'transcript',key:'tf',path:(readyList().find(r=>r.kind==='f')).f.path},{id:'process'},null)")
        b.wait("/busy/.test(document.getElementById('snackT').textContent)", 10)
        b.eval("RUN=null")

    def test_focus_stays_and_progress_is_announced(self):
        b = self.b
        row = self.row("ev-b")
        b.eval(f"document.querySelector('{row} [data-ia=det]').focus()")
        b.key("Enter")
        b.wait(f"document.querySelector('{row} .indet')")
        self.assertEqual(b.eval("[document.activeElement.dataset.ia, document.activeElement.closest('.inrow').dataset.mid]"), ["det", "ev-b"])
        b.eval(f"document.querySelector('{row} [data-ia=later]').focus()")
        b.key("Enter")
        b.wait("document.querySelector('#mtgBody .inrow[data-g=later][data-mid=\"ev-b\"]')")
        self.assertEqual(b.eval("document.activeElement.closest('.inrow').dataset.mid"), "ev-b")              # the row moved; focus went with it
        b.click(f"{self.row('ev-c')} [data-ia=not]")
        b.wait("document.getElementById('inNotMenu')")
        b.eval("[...document.querySelectorAll('#inNotMenu [role=menuitem]')][0].click()")
        b.wait("!document.querySelector('#mtgBody [data-mid=\"ev-c\"]')", 20)
        self.assertTrue(b.eval("!!document.activeElement.closest('#mtgBody')"))                               # focus is in the list, not lost to the page
        b.eval(self.HOLD)
        b.click(f"{self.row('ev-a')} [data-ia=process]")
        b.wait(f"document.querySelector('{self.row('ev-a')} .instate')", 20)
        b.eval(f"window.KEPT=document.querySelector('{self.row('ev-a')} .instate'); renderInbox()")
        self.assertTrue(b.eval(f"document.querySelector('{self.row('ev-a')} .instate')===KEPT"))              # the same live region, text updated in place
        b.eval("REL()")


if __name__ == "__main__":
    unittest.main()
