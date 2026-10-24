"""#232-A hardening (v2.5.0), written against Team Cap's p250-a: what the brief, the locked mockup and Alan's answers ask for that
the branch's own test_intake_review_intake.py does not pin, plus hostile inputs. Each test says what it expects; a failure is a
finding for the review, not a change to this file. Real Chrome against the live server (support: ir_harden_support.py).

Run: CREAITE_BROWSER_SLOTS=6 python3 dev/tests/test_intake_review_harden.py
"""
import json
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ir_harden_support import DAY, IrHardenCase  # noqa: E402

HOSTILE = "<img src=x onerror=window.PWNED=1> & \"quotes\""


class Base(IrHardenCase):
    @classmethod
    def load(cls, v):
        super().load(v)
        f = v.root / "system/staging/calendar.json"
        cal = json.loads(f.read_text())
        cal["days"][DAY] += [{"id": "ev-8", "start": "17:00", "end": "17:15", "title": HOSTILE, "teams": True},
                             {"id": "ev-9", "start": "17:30", "end": "17:45", "title": "Busy", "private": True, "teams": True}]
        f.write_text(json.dumps(cal))
        cls.set_transcripts(v, {"ev-1": "available", "ev-6": "available", "ev-7": "available", "ev-2": "not_transcribed",
                                "ev-9": "available"})

    def acts(self, title):
        return self.b.eval("(t=>{ const r=[...document.querySelectorAll('#v-intake-review [data-irv=list] [data-irm]')].find(x=>x.querySelector('.icmeethd').textContent.trim().startsWith(t)); return r?[...r.querySelectorAll('[data-ira]')].map(x=>x.dataset.ira):null; })(%s)" % json.dumps(title))

    def key(self, title, k):
        self.b.eval("(()=>{ const r=document.querySelector(%s); r.focus(); r.dispatchEvent(new KeyboardEvent('keydown',{key:%s,bubbles:true,cancelable:true})); })()"
                    % (json.dumps(self.sel(title)), json.dumps(k)))


class Findings(Base):
    def test_a_confidential_meeting_shows_title_and_times_only(self):
        """The brief and the standing rule: sensitivity=confidential in the calendar -> no project on the row (Busy covers private only)."""
        txt = self.text("ABC Board matters")
        self.assertIn("12:00", txt)
        self.assertNotIn("Example Programme", txt)
        self.assertNotIn("Teams", txt)

    def test_a_confidential_meeting_is_not_named_by_project_on_the_board_or_two_panes(self):
        for view in ("board", "two"):
            self.b.eval("irSetView(%s)" % json.dumps(view))
            self.b.wait("!!document.querySelector('[data-irv=%s]')" % view)
            if view == "two":
                self.b.eval("irSel.value=D.intake_review.meetings.find(m=>m.title==='ABC Board matters').id")
            self.b.wait("document.getElementById('v-intake-review').innerText.includes('ABC Board matters')")
            cards = self.b.eval("[...document.querySelectorAll('#v-intake-review [data-irm],#v-intake-review [data-irdet]')].filter(x=>x.innerText.includes('ABC Board matters')).map(x=>x.innerText).join(' ')")
            self.assertNotIn("Example Programme", cards, view)

    def test_n_and_h_do_nothing_on_a_row_that_is_being_processed(self):
        b = self.b
        b.eval("window.GATE=new Promise(r=>{window.OPEN=r}); 0")
        b.click(self.sel("ABC Steering", " [data-ira=process]"))
        b.wait("document.querySelector(%s).dataset.state==='running'" % json.dumps(self.sel("ABC Steering")))
        self.key("ABC Steering", "h")
        self.key("ABC Steering", "n")
        time.sleep(0.4)
        self.assertEqual(self.cleared(), [], "a meeting being drafted was set aside")
        self.assertFalse(b.eval("!!document.querySelector('#irAside')"))
        b.eval("window.OPEN(); 0")
        b.wait("document.querySelector(%s).dataset.stage==='drafted'" % json.dumps(self.sel("ABC Steering")), 30)

    def test_process_all_ready_leaves_a_private_meeting_alone(self):
        """Select new left a private meeting out; Process all ready should too (a 'Busy' row has nothing to process by name)."""
        b = self.b
        b.click("#v-intake-review [data-ira=processall]")
        b.wait("irBusy.value.length===0 && ASKED.length>=3", 60)
        self.assertFalse([q for q, _ in b.eval("ASKED")] and any("ev-9" in q for q, _ in b.eval("ASKED")))
        busy = b.eval("D.intake_review.meetings.find(m=>m.key==='ev-9').stage")
        self.assertEqual(busy, "arrived")

    def test_a_buttons_busy_state_follows_ask_creaite_without_another_redraw(self):
        """Process is disabled while ask creaite runs and enabled again when it ends, with no other redraw in between."""
        b = self.b
        b.eval("shared.RUN={id:'x'}; setRunning(true); 0")          # what ask.js does when a run starts and ends
        b.wait("document.querySelector(%s).disabled" % json.dumps(self.sel("ABC Steering", " [data-ira=process]")), 8)
        b.eval("shared.RUN=null; setRunning(false); 0")
        b.wait("!document.querySelector(%s).disabled" % json.dumps(self.sel("ABC Steering", " [data-ira=process]")), 8)

    def test_a_processed_upload_that_leaves_the_inbox_is_not_reported_as_failed(self):
        b = self.b
        self.upload("2026-10-05 Gone after.txt")
        b.eval("""askLive=async(q,c)=>{ ASKED.push([q,c]);
          const f=D.inbox.find(x=>x.name==='2026-10-05 Gone after.txt'); await api('/api/inbox/remove',{path:f.path}); }""")
        b.click(self.sel("2026-10-05 Gone after.txt", " [data-ira=process]"))
        b.wait("ASKED.length===1 && irBusy.value.length===0", 30)
        time.sleep(0.4)
        self.assertEqual(b.eval("JSON.stringify(irNotes.value)"), "{}", "a file that was filed away got a failure note")

    def test_a_double_click_on_process_starts_one_run(self):
        b = self.b
        b.eval("window.GATE=new Promise(r=>{window.OPEN=r}); 0")
        b.eval("(()=>{ const x=document.querySelector(%s); x.click(); x.click(); })()" % json.dumps(self.sel("ABC Steering", " [data-ira=process]")))
        time.sleep(0.4)
        self.assertEqual(b.eval("ASKED.length"), 1)
        b.eval("window.OPEN(); 0")
        b.wait("irBusy.value.length===0", 30)

    def test_esc_closes_the_reasons_menu_and_sets_nothing_aside(self):
        b = self.b
        b.click(self.sel("Weekly sync 12", " [data-ira=notneeded]"))
        b.wait("!!document.querySelector('#irAside [data-reason]')")
        b.eval("document.activeElement.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}))")
        b.wait("!document.querySelector('#irAside')")
        self.assertEqual(self.cleared(), [])
        self.assertEqual(b.eval("document.activeElement.dataset.ira"), "notneeded")        # focus back where it was

    def test_n_on_a_drafted_or_waiting_less_row_offers_nothing_it_should_not(self):
        b = self.b
        b.eval("window.GATE=null")
        sel = self.sel("ABC Steering", " [data-ira=process]")
        b.eval("document.querySelector(%s).scrollIntoView({block:'center'}); 0" % json.dumps(sel))      # #340: the Arrived rows come after the work to decide, below the first screen
        self.assertTrue(b.eval("(x=>{ const r=x.getBoundingClientRect(); return x.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)); })(document.querySelector(%s))" % json.dumps(sel)),
                        "something sits over the Process button")
        b.click(sel)
        b.wait("ASKED.length===1", 20)
        b.wait("document.querySelector(%s).dataset.stage!=='arrived'" % json.dumps(self.sel("ABC Steering")), 30)
        self.key("ABC Steering", "n")
        self.key("ABC Steering", "h")
        time.sleep(0.4)
        self.assertFalse(b.eval("!!document.querySelector('#irAside')"))
        self.assertEqual(self.cleared(), [])

    def test_later_on_an_uploaded_file_lists_it_and_restore_brings_it_back(self):
        b = self.b
        self.upload("2026-10-05 Snooze me.txt")
        b.click(self.sel("2026-10-05 Snooze me.txt", " [data-ira=later]"))
        b.wait("!D.intake_review.meetings.some(m=>m.title==='2026-10-05 Snooze me.txt')", 20)
        self.assertTrue(b.eval("D.intake_review.later.some(x=>x.title.includes('Snooze me'))"), "the model does not list the file under Later: " + b.eval("JSON.stringify(D.intake_review.later)+JSON.stringify(D.intake_review.not_needed)"))
        b.eval("document.querySelector('[data-irfold=later]').click()")             # (the snack bar sits over it at the foot of the page)
        try:
            b.wait("document.querySelector('[data-irsec=later]').innerText.includes('Snooze me')", 5)
        except TimeoutError:
            self.fail("cleared file: " + json.dumps(self.cleared()) + " | Later section shows: " + b.eval("document.querySelector('[data-irsec=later]').innerText.replace(/\\n/g,' / ') + ' | folded=' + JSON.stringify(irFolded.value) + ' | later=' + JSON.stringify(D.intake_review.later)"))
        b.eval("document.querySelector('[data-irsec=later] [data-ira=restore]').click()")
        b.wait("D.intake_review.meetings.some(m=>m.title==='2026-10-05 Snooze me.txt')", 20)
        self.assertEqual(self.cleared(), [])


class Hostile(Base):
    def test_a_meeting_title_with_markup_is_text(self):
        b = self.b
        self.assertIn("<img src=x", b.eval("document.getElementById('v-intake-review').innerText"))
        self.assertIsNone(b.eval("window.PWNED || null"))
        self.assertEqual(b.eval("document.querySelectorAll('#v-intake-review img').length"), 0)

    def test_the_hostile_title_survives_not_needed_and_the_lists_as_text(self):
        b = self.b
        b.click(self.sel(HOSTILE[:20], " [data-ira=notneeded]"))
        b.click("#irAside [data-reason='Other']")
        b.wait("D.intake_review.not_needed.some(x=>x.key==='ev-8')", 20)
        b.click("[data-irfold=not_needed]")
        self.assertEqual(b.eval("document.querySelectorAll('#v-intake-review img').length"), 0)
        self.assertIsNone(b.eval("window.PWNED || null"))

    def test_a_reason_outside_the_four_is_refused_by_the_page_and_the_route(self):
        b = self.b
        before = self.cleared()
        r = b.eval("irNotNeeded(D.intake_review.meetings.find(m=>m.key==='ev-2'),'Because I said so').then(x=>x)")
        self.assertFalse(r)
        self.assertEqual(self.cleared(), before)
        res = b.eval("api('/api/intake/clear',{op:'clear',items:[{key:'ev-2',day:'2026-10-05',start:'15:00',title:'x',reason:'Because I said so'}]}).then(x=>x.ok)")
        self.assertFalse(res)
        res = b.eval("api('/api/intake/clear',{op:'clear',items:[{key:'ev-2',day:'2026-10-05',start:'15:00',title:'x',kind:'later',reason:'Other'}]}).then(x=>x.ok)")
        self.assertFalse(res, "a Later entry with a Not needed reason")
        self.assertEqual(self.cleared(), before)

    def test_a_long_note_and_title_are_cut_by_the_store(self):
        b = self.b
        b.eval("api('/api/intake/clear',{op:'clear',items:[{key:'ev-2',day:'2026-10-05',start:'15:00',title:'T'.repeat(500),reason:'Other',note:'N'.repeat(900)}]})")
        b.wait("true")
        e = [x for x in self.cleared() if x["key"] == "ev-2"][0]
        self.assertLessEqual(len(e["note"]), 200)
        self.assertLessEqual(len(e["title"]), 200)

    def test_a_wrong_file_type_is_refused_and_nothing_is_uploaded(self):
        b = self.b
        b.eval("""(()=>{ const dt=new DataTransfer(); dt.items.add(new File(["x"],"evil.exe"));
          document.querySelector('#v-intake-review h1').dispatchEvent(new DragEvent('drop',{dataTransfer:dt,bubbles:true,cancelable:true})); })()""")
        b.wait("/evil\\.exe: .*not this kind/.test((document.querySelector('[data-iraddfail]')||{}).innerText||'')")   # #307: named, with why, kept on the page
        self.assertFalse((self.v.root / "inbox" / "evil.exe").exists())

    def test_a_drop_on_another_page_uploads_nothing(self):
        b = self.b
        b.eval("go('today')")
        b.eval("""(()=>{ const dt=new DataTransfer(); dt.items.add(new File(["WEBVTT"],"stray.vtt"));
          document.body.dispatchEvent(new DragEvent('drop',{dataTransfer:dt,bubbles:true,cancelable:true})); })()""")
        time.sleep(0.4)
        self.assertFalse((self.v.root / "inbox" / "stray.vtt").exists())

    def test_a_path_like_file_name_cannot_leave_the_inbox(self):
        b = self.b
        b.eval("""(()=>{ const dt=new DataTransfer(); dt.items.add(new File(["WEBVTT"],"../../escape.vtt"));
          document.querySelector('#v-intake-review h1').dispatchEvent(new DragEvent('drop',{dataTransfer:dt,bubbles:true,cancelable:true})); })()""")
        time.sleep(0.4)
        self.assertFalse((self.v.root.parent / "escape.vtt").exists())
        self.assertFalse((self.v.root / "escape.vtt").exists())

    def test_the_debug_log_holds_no_meeting_titles(self):
        b = self.b
        b.click(self.sel("Weekly sync 12", " [data-ira=notneeded]"))
        b.click("#irAside [data-reason='Other']")
        b.wait("D.intake_review.not_needed.some(x=>x.key==='ev-2')", 20)
        text = "\n".join(p.read_text(errors="replace") for p in (self.v.root / "system/logs").glob("debug-*.log"))
        self.assertNotIn("Weekly sync 12", text)


if __name__ == "__main__":
    unittest.main()
