"""#203, the page half: the sparkle that suggests a project's health and its reason, in a real browser against the real live server.

Run: python3 dev/tests/test_health_suggest.py   (needs Google Chrome; skipped otherwise)

The plain half (drafts.py's kind "health", field "suggest") is built apart. This test stubs its reply at the draft route with a double
that follows the contract: {health, reason, differs, current: {health, reason}, evidence: [{ref, text}], audience}. The fetch for
/api/draft with field "suggest" is answered in the page with one "draft" event, as the live server streams it; every other request
(the counts, the save) is the real server's. The cases: the sparkle is present and named; a suggestion shows its evidence with item
IDs as links; a difference is flagged in plain words; Use fills the fields and saves nothing; Save saves once; Reject clears and
counts; Esc closes and gives the focus back to the sparkle; the empty and error states.
"""
import json
import sqlite3
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_reports as R  # noqa: E402  (its fictional fixture and fixed clock, for the client sheet)
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402

REPLY = {"health": "At risk", "reason": "Two actions are overdue and UAT start has slipped.", "differs": True,
         "current": {"health": "On track", "reason": "Delivery is on plan."},
         "evidence": [{"ref": "ABC-A-001", "text": "is overdue"}, {"ref": "ABC-M-001", "text": "forecast later than agreed"}],
         "audience": "internal"}

STUB = """(()=>{ const f=window.fetch, st=window.__hs={calls:[],posts:[],reply:%s,nothing:'',fail:false,delay:0};
  window.fetch=function(u,o){ const url=String(u);
    if(o&&o.method==='POST') st.posts.push(url);
    if(url==='/api/draft'&&o&&o.body){ const body=JSON.parse(o.body);
      if(body.field==='suggest'){ st.calls.push(body);
        const ev=st.fail?[{type:'error',message:'The model did not answer'},{type:'draft',ok:false,message:'No draft came back'},{type:'done'}]
          :st.nothing?null:[{type:'draft',ok:true,...st.reply},{type:'done'}];
        if(!ev) return Promise.resolve(new Response(JSON.stringify({ok:true,nothing:st.nothing}),{headers:{'Content-Type':'application/json'}}));
        const resp=new Response(ev.map(e=>'data: '+JSON.stringify(e)+'\\n\\n').join(''),{headers:{'Content-Type':'text/event-stream'}});
        return new Promise(r=>setTimeout(()=>r(resp),st.delay)); } }
    return f.apply(this,arguments); }; })()"""


class HealthSuggest(LiveBrowserCase):
    def health(self):
        con = sqlite3.connect(self.v.root / "system/tracker.db")
        try:
            return con.execute("SELECT health, health_reason FROM projects WHERE code='ABC'").fetchone()
        finally:
            con.close()

    def open_form(self, reply=None):
        b = self.b
        b.eval("go('cockpit','ABC'); openProject('ABC','health')")
        b.wait("document.querySelector('#pFields [data-hsuggest]')")
        b.eval(STUB % json.dumps(reply or REPLY))
        b.eval("document.getElementById('f_health').value='On track'; document.getElementById('f_health').dispatchEvent(new Event('change'))")

    def suggest(self, reply=None):
        b = self.b
        self.open_form(reply)
        b.click("#pFields [data-hsuggest]")
        b.wait("document.querySelector('#hSug .drcard')", 15)

    def test_the_sparkle_is_plain_named_and_sits_right_of_the_label(self):
        b = self.b
        self.open_form()
        self.assertEqual(b.eval("document.querySelector('#pFields [data-hsuggest]').getAttribute('aria-label')"), "Suggest health and reason")
        self.assertEqual(b.eval("document.querySelector('#pFields [data-hsuggest]').tagName"), "BUTTON")
        self.assertEqual(b.eval("document.querySelector('#pFields [data-hsuggest]').textContent.trim()"), "")          # plain: no label
        self.assertEqual(b.eval("document.querySelector('#pFields [data-hsuggest]').closest('dt').textContent.trim()"), "Health")
        self.assertTrue(b.eval("!!document.querySelector('#pFields [data-hsuggest] svg')"))
        self.assertEqual(b.eval("document.querySelectorAll('#pFields [data-hsuggest]').length"), 1)                    # not on the reason
        self.assertEqual(b.errors, [])

    def test_the_request_is_the_health_kind_with_the_suggest_field_and_no_save(self):
        b = self.b
        before = self.health()
        self.suggest()
        self.assertEqual(b.eval("window.__hs.calls"), [{"kind": "health", "field": "suggest", "code": "ABC", "audience": "internal", "run": b.eval("window.__hs.calls[0].run")}])
        self.assertEqual(self.health(), before)
        self.assertEqual(b.errors, [])

    def test_the_suggestion_shows_the_health_the_reason_and_the_evidence_with_linked_ids(self):
        b = self.b
        self.suggest()
        card = b.eval("document.querySelector('#hSug .drcard').innerText")
        self.assertIn("At risk", card)
        self.assertEqual(b.eval("document.getElementById('hsgReason').value"), REPLY["reason"])
        self.assertEqual(b.eval("[...document.querySelectorAll('#hSug .hsg-why li')].map(l=>l.textContent.trim())"),
                         ["ABC-A-001 is overdue", "ABC-M-001 forecast later than agreed"])
        self.assertEqual(b.eval("[...document.querySelectorAll('#hSug .hsg-why a')].map(a=>a.dataset.open)"), ["actions:ABC-A-001"])   # a milestone is not an item
        self.assertEqual(b.eval("[...document.querySelectorAll('#hSug [data-hsdo]')].map(x=>x.textContent)"), ["Reject", "Use", "Save"])
        self.assertEqual(b.errors, [])

    def test_a_difference_is_flagged_in_plain_words_and_agreement_is_not(self):
        b = self.b
        self.suggest()
        self.assertEqual(b.eval("document.querySelector('#hSug .hsg-diff').textContent"), "The facts suggest At risk, you have On track.")
        b.click("#hSug [data-hsdo=reject]")
        self.suggest({**REPLY, "health": "On track", "differs": False, "evidence": []})
        self.assertFalse(b.eval("document.querySelector('#hSug .hsg-diff')"))
        self.assertIn("agrees with you", b.eval("document.querySelector('#hSug .drhead').innerText"))

    def test_use_fills_both_fields_and_saves_nothing(self):
        b = self.b
        before = self.health()
        self.suggest()
        b.click("#hSug [data-hsdo=use]")
        b.wait("document.getElementById('f_reason').value===window.__hs.reply.reason")
        self.assertEqual(b.eval("document.getElementById('f_health').value"), "At risk")
        self.assertFalse(b.eval("document.querySelector('#hSug .drcard')"))
        self.assertEqual(b.eval("window.__hs.posts.filter(u=>!/draft|pulse|ask.ack/.test(u))"), [])          # nothing is staged or applied
        self.assertEqual(self.health(), before)
        self.assertEqual(b.errors, [])

    def test_the_card_save_uses_it_and_saves_once(self):
        b = self.b
        self.suggest()
        b.eval("document.getElementById('hsgReason').value+=' Edited.'; document.getElementById('hsgReason').dispatchEvent(new Event('input',{bubbles:true}))")
        b.click("#hSug [data-hsdo=save]")
        b.wait("!document.getElementById('panel').classList.contains('on')")
        for _ in range(60):
            if self.health()[0] == "At risk":
                break
            time.sleep(0.25)
        self.assertEqual(self.health(), ("At risk", REPLY["reason"] + " Edited."))
        self.assertEqual(len(self.saves()), 1, self.saves())                                                              # one save, not two
        self.counted_event("edited", 1)                                                                                         # counted when saved, once
        self.assertEqual(b.errors, [])

    def saves(self):
        """The applies the page sent: a save stages with /api/fs and applies once with /api/apply."""
        return self.b.eval("window.__hs.posts.filter(u=>u==='/api/apply')")

    def counted_event(self, event, n):
        for _ in range(40):
            if self.stats_reason().get(event, 0) >= n:
                break
            time.sleep(0.25)
        time.sleep(0.5)
        self.assertEqual(self.stats_reason().get(event, 0), n)

    def test_a_real_double_press_of_the_card_save_saves_once(self):
        b = self.b
        self.suggest()
        b.eval("(()=>{ const x=document.querySelector('#hSug [data-hsdo=save]'); x.click(); x.click(); })()")
        b.wait("!document.getElementById('panel').classList.contains('on')")
        for _ in range(60):
            if self.health()[0] == "At risk":
                break
            time.sleep(0.25)
        time.sleep(1)
        self.assertEqual(self.health(), ("At risk", REPLY["reason"]))
        self.assertEqual(len(self.saves()), 1, self.saves())
        self.assertEqual(b.errors, [])

    def test_save_while_the_suggestion_is_loading_saves_once_and_the_late_answer_changes_nothing(self):
        b = self.b
        self.open_form()
        b.eval("window.__hs.delay=1200")
        b.click("#pFields [data-hsuggest]")
        b.eval("(()=>{ const r=document.getElementById('f_reason'); r.value='Written while it loaded.'; r.dispatchEvent(new Event('input',{bubbles:true})); })()")
        b.click("#pSave")
        b.wait("!document.getElementById('panel').classList.contains('on')")
        time.sleep(2)                                                                                                     # the late answer arrives
        for _ in range(40):
            if self.health()[1] == "Written while it loaded.":
                break
            time.sleep(0.25)
        self.assertEqual(self.health()[1], "Written while it loaded.")
        self.assertEqual(len(self.saves()), 1, self.saves())
        self.assertFalse(b.eval("!!document.querySelector('#hSug .drcard')"))
        self.assertEqual(b.errors, [])

    def test_use_counts_only_when_the_form_is_saved_not_when_it_is_cancelled(self):
        b = self.b
        self.suggest()
        b.click("#hSug [data-hsdo=use]")
        b.click("#pCancel")
        time.sleep(1)
        self.assertEqual((self.stats_reason().get("used", 0), self.stats_reason().get("edited", 0)), (0, 0))
        self.suggest()
        b.click("#hSug [data-hsdo=use]")
        b.eval("document.getElementById('pSave').click()")                                                                # the run badge covers the button
        self.counted_event("used", 1)

    def test_use_keeps_a_reason_alan_wrote_while_the_suggestion_was_loading(self):
        b = self.b
        before = self.health()
        self.open_form()
        b.eval("window.__hs.delay=800")
        b.click("#pFields [data-hsuggest]")
        b.eval("(()=>{ const r=document.getElementById('f_reason'); r.value='Alan wrote this.'; r.dispatchEvent(new Event('input',{bubbles:true})); })()")
        b.wait("document.querySelector('#hSug .drcard')", 15)
        b.click("#hSug [data-hsdo=use]")
        b.wait("document.getElementById('f_health').value==='At risk'")
        self.assertEqual(b.eval("document.getElementById('f_reason').value"), "Alan wrote this.")                       # not overwritten silently
        self.assertEqual(self.health(), before)

    def test_reject_clears_and_counts_and_esc_does_the_same_and_returns_focus(self):
        b = self.b
        self.suggest()
        b.click("#hSug [data-hsdo=reject]")
        self.assertFalse(b.eval("document.querySelector('#hSug .drcard')"))
        self.counted(1)
        self.suggest_again()
        b.click("#hSug [data-hsdo=reject]")
        self.counted(2)
        self.suggest_again()
        b.eval("document.querySelector('#hSug [data-hsdo=use]').focus()")
        b.key("Escape")
        b.wait("!document.querySelector('#hSug .drcard')")
        self.assertTrue(b.eval("document.getElementById('panel').classList.contains('on')"))                              # Esc closed the card, not the form
        self.assertTrue(b.eval("document.activeElement&&document.activeElement.hasAttribute('data-hsuggest')"))
        self.counted(3)
        self.assertEqual(b.errors, [])

    def suggest_again(self):
        self.b.click("#pFields [data-hsuggest]")
        self.b.wait("document.querySelector('#hSug .drcard')", 15)

    def counted(self, n):
        """Wait for the server to hold n rejections (one count is written before the next is sent: the file is read and written whole)."""
        for _ in range(40):
            if self.stats_reason().get("rejected", 0) >= n:
                return
            time.sleep(0.25)
        self.assertGreaterEqual(self.stats_reason().get("rejected", 0), n)

    def stats_reason(self):
        p = self.v.root / "system/staging/draft-stats.json"
        return (json.loads(p.read_text()).get("reason") or {}) if p.exists() else {}

    def test_nothing_to_go_on_and_a_failure_show_plainly_and_change_nothing(self):
        b = self.b
        before = self.health()
        self.open_form()
        b.eval("window.__hs.nothing='The tracker holds nothing to base a health on yet.'")
        b.click("#pFields [data-hsuggest]")
        b.wait("document.querySelector('#hSug .drnone')")
        self.assertIn("nothing to base a health on", b.eval("document.querySelector('#hSug .drnone').innerText"))
        b.eval("window.__hs.nothing=''; window.__hs.fail=true")
        b.click("#pFields [data-hsuggest]")
        b.wait("!document.querySelector('#hSug .drnone')&&!document.querySelector('#hSug .drstatus')")
        self.assertFalse(b.eval("document.querySelector('#hSug .drcard')"))
        self.assertEqual(self.health(), before)


class ReportRow:
    """What the weekly report's health row and the client sheet's share: the sparkle beside the heading, then the draft under it."""

    section = "#v-weekly section[data-id=health]"
    spark = "h2 .sheet-spark"                  # the weekly row's heading is hidden: its ✦ sits right of the flag

    def open_report(self):
        raise NotImplementedError

    def suggest(self, reply=None):
        b = self.b
        self.open_report()
        b.eval(STUB % json.dumps(reply or REPLY))
        b.click(f"{self.section} .sheet-spark")
        b.wait(f"document.querySelector('{self.section} .sheet-redraft [data-hflag]')", 15)

    def test_the_sparkle_is_by_the_heading_and_named(self):
        self.open_report()
        sp = f"{self.section} {self.spark}"
        self.assertEqual(self.b.eval(f"document.querySelector('{sp}').getAttribute('aria-label')"), "Suggest health and reason")
        self.assertEqual(self.b.eval(f"document.querySelector('{sp}').tagName"), "BUTTON")
        self.assertEqual(self.b.eval(f"document.querySelector('{sp}').textContent.trim()"), "")
        self.assertEqual(self.b.eval(f"document.querySelectorAll('{self.section} .sheet-spark').length"), 1)

    def test_it_shows_the_flag_the_difference_and_the_evidence_with_linked_ids(self):
        b = self.b
        self.suggest()
        self.assertEqual(b.eval(f"document.querySelector('{self.section} [data-hflag]').textContent"), "At risk")
        self.assertEqual(b.eval(f"document.querySelector('{self.section} .sheet-hdiff').textContent"), f"The facts suggest At risk, you have {self.shown_flag()}.")
        self.assertEqual(b.eval(f"[...document.querySelectorAll('{self.section} .sheet-hwhy li')].map(l=>l.textContent.trim())"),
                         ["ABC-A-001 is overdue", "ABC-M-001 forecast later than agreed"])
        self.assertEqual(b.eval(f"[...document.querySelectorAll('{self.section} .sheet-hwhy button')].map(x=>x.textContent)"), ["ABC-A-001", "ABC-M-001"])
        self.assertEqual(b.eval(f"[...document.querySelectorAll('{self.section} .sheet-rdb button')].map(x=>x.textContent)"), ["Reject", "Use"])
        self.assertEqual(b.errors, [])

    flag_sel = ".wr-flag"

    def shown_flag(self):
        """The flag the sheet shows, in the tracker's words (the page draws it in capitals)."""
        t = self.b.eval(f"document.querySelector('{self.section} {self.flag_sel}').textContent").lower()
        return next(h for h in ("On track", "At risk", "Off track") if h.lower() == t)

    def test_the_difference_is_measured_against_the_flag_the_sheet_shows(self):
        b = self.b
        self.open_report()
        flag = self.shown_flag()
        other = next(h for h in ("On track", "At risk", "Off track") if h != flag)
        tracker = next(h for h in ("On track", "At risk", "Off track") if h not in (flag, other))             # what projects.health says: not the sheet's flag
        b.eval(STUB % json.dumps({**REPLY, "health": other, "differs": False, "current": {"health": tracker, "reason": ""}}))
        b.click(f"{self.section} .sheet-spark")
        b.wait(f"document.querySelector('{self.section} .sheet-redraft [data-hflag]')", 15)
        self.assertEqual(b.eval(f"document.querySelector('{self.section} .sheet-hdiff').textContent"), f"The facts suggest {other}, you have {flag}.")
        b.click(f"{self.section} .sheet-rdb button")
        b.wait(f"!document.querySelector('{self.section} .sheet-redraft')")
        b.eval(STUB % json.dumps({**REPLY, "health": flag, "differs": True, "current": {"health": tracker, "reason": ""}}))
        b.click(f"{self.section} .sheet-spark")
        b.wait(f"document.querySelector('{self.section} .sheet-redraft [data-hflag]')", 15)
        self.assertFalse(b.eval(f"!!document.querySelector('{self.section} .sheet-hdiff')"))                      # it agrees with the sheet

    def test_reject_changes_nothing_and_counts_and_esc_gives_the_focus_back(self):
        b = self.b
        self.suggest()
        b.click(f"{self.section} .sheet-rdb button")
        b.wait(f"!document.querySelector('{self.section} .sheet-redraft')")
        self.assertTrue(b.eval(f"document.activeElement===document.querySelector('{self.section} .sheet-spark')"))
        self.counted(1)
        self.suggest_again()
        b.eval(f"document.querySelector('{self.section} .sheet-redraft').focus()")
        b.key("Escape")
        b.wait(f"!document.querySelector('{self.section} .sheet-redraft')")
        self.assertTrue(b.eval(f"document.activeElement===document.querySelector('{self.section} .sheet-spark')"))
        self.counted(2)

    def counted(self, n):
        """Wait for the server to hold n rejections (the file is read and written whole, so one count goes at a time)."""
        for _ in range(40):
            if self.reason_stats().get("rejected", 0) >= n:
                return
            time.sleep(0.25)
        self.assertGreaterEqual(self.reason_stats().get("rejected", 0), n)

    def suggest_again(self):
        self.b.click(f"{self.section} .sheet-spark")
        self.b.wait(f"document.querySelector('{self.section} .sheet-redraft [data-hflag]')", 15)

    def reason_stats(self):
        p = self.v.root / "system/staging/draft-stats.json"
        return (json.loads(p.read_text()).get("reason") or {}) if p.exists() else {}


class WeeklyHealthRow(ReportRow, LiveBrowserCase):
    spark = ".wr-hcol .sheet-spark"

    @classmethod
    def load(cls, v):
        populate(v)

    def open_report(self):
        self.b.eval("go('weekly',{code:'ABC'})")
        self.b.wait("document.querySelector('#v-weekly section[data-id=health] .wr-flag')", 20)

    def test_the_request_is_internal_and_use_changes_the_flag_and_reason_in_the_report(self):
        b = self.b
        self.suggest()
        call = b.eval("window.__hs.calls[0]")
        self.assertEqual((call["kind"], call["field"], call["code"], call["audience"], "to" in call), ("health", "suggest", "ABC", "internal", False))
        b.click(f"{self.section} .sheet-rdb .primary")
        b.wait(f"!document.querySelector('{self.section} .sheet-redraft')")
        self.assertEqual(b.eval(f"document.querySelector('{self.section} .wr-flag').textContent"), "AT RISK")
        self.assertIn(REPLY["reason"], b.eval(f"document.querySelector('{self.section} .wr-why').innerText"))
        self.assertEqual(b.errors, [])


class ClientHealthRow(ReportRow, LiveBrowserCase):
    section = "#v-clientreport section[data-id=health]"
    flag_sel = ".crflag"

    @classmethod
    def load(cls, v):
        R.populate(v)

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": R.NOW, "CREAITE_NO_LAUNCH": "1"}

    def open_report(self):
        self.b.eval("go('clientreport',{code:'ABC',week:'2026-10-09'})")
        self.b.wait("document.querySelector('#v-clientreport .crhealth')", 20)

    def test_the_client_sheet_asks_for_the_client_audience_and_use_sets_the_client_flag(self):
        b = self.b
        self.suggest({**REPLY, "audience": "client", "health": "Off track"})
        call = b.eval("window.__hs.calls[0]")
        self.assertEqual((call["kind"], call["field"], call["code"], call["audience"]), ("health", "suggest", "ABC", "client"))
        b.click(f"{self.section} .sheet-rdb .primary")
        b.wait(f"!document.querySelector('{self.section} .sheet-redraft')")
        self.assertEqual(b.eval(f"document.querySelector('{self.section} .crflag').textContent"), "OFF TRACK")
        self.assertTrue(b.eval("!!document.querySelector('#v-clientreport [data-crdif]')"))          # it differs from the internal flag, and says so
        # the reason the flag differs is Alan's to write: Use records the difference but does not invent the reason
        b.click("#v-clientreport [data-crflag]")
        b.wait("document.getElementById('crWhy')")
        self.assertEqual(b.eval("document.getElementById('crWhy').value"), "")
        self.assertTrue(b.eval("document.querySelector('[data-crhsave]').disabled"))
        self.assertEqual(b.errors, [])


if __name__ == "__main__":
    unittest.main()
