"""Sprint 5 item 2 (BL-53): decisions needed, in the dashboard, against the real live server in a real browser.

Run: python3 dev/tests/test_decisions_dashboard.py   (needs Google Chrome; skipped otherwise)

A pending decision has a decision maker, a needed-by date and no date until it is made. These tests click through
Work, Today, the project page, a person's page, the detail panel and the Draft email as a person does.
"""
import json
import sys
import time
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase, pin_page_clock  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_tracker import ABC  # noqa: E402

# The clock is pinned (CREAITE_NOW for the live server, pin_page_clock for the page) to a Thursday, so the dates below never fall
# on a weekend and BL-181's weekend warning stays out of these tests whatever the real weekday.
TODAY = date(2026, 10, 8)
NOW = f"{TODAY.isoformat()} 09:00"


def d(n, today=None):
    return ((today or TODAY) + timedelta(days=n)).isoformat()


def shown(iso):
    return f"{iso[8:10]}-{iso[5:7]}-{iso[0:4]}"


def dec(n, src, **v):
    return {"n": n, "op": "new", "table": "decisions", "match": "strong", "flags": [], "decision": "approved",
            "values": {"project": "ABC", "source": src, **v}}


def load(v, today=None):
    """The decisions, dated from `today`: the real date when not given, for the other files that share this data on the real
    clock; this file and test_decisions_board pass the pinned TODAY."""
    today = today or date.today()
    d_ = lambda n: d(n, today)  # noqa: E731
    src = f"{ABC}/minutes/{d_(-5)} Steering.docx — Decisions"
    dec_ = lambda n, **v: dec(n, src, **v)  # noqa: E731
    populate(v)                       # ABC-D-005 (made) is already there
    v.propose("dec", [
        dec_(1, decision="Extend the pilot by two weeks", status="Pending", made_by="Sara Example", needed_by=d_(-3)),
        dec_(2, decision="Choose the UAT venue", status="Pending", made_by="Alan Carter", needed_by=d_(5)),
        dec_(3, project="DEF", decision="Approve the pilot budget", status="Pending", made_by="Omar Ali"),
        dec_(4, decision="Use masked data for UAT", date=d_(-8), made_by="Jane Doe", revisit=d_(-1), replaces="ABC-D-005",
            reasoning="Production data isn't available", options="Masked; synthetic"),
    ])
    v.run("apply")


class DecisionCase(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        load(v, TODAY)

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": NOW}

    def setUp(self):
        super().setUp()
        pin_page_clock(self.b, NOW)

    def row(self, id_):
        return next(r for r in self.v.rows("decisions") if r["id"] == id_)

    def open_decisions(self, view=None):
        b = self.b
        b.eval("WT='decisions'; go('work')")
        b.wait("document.querySelector('#workTbl tbody tr[data-row], #workTbl .empty')")
        if view:
            b.click(f'#wviews [data-wv="{view}"]')
            b.wait(f"WVIEW==='{view}'")
        return self

    def ids(self):
        return self.b.eval("[...document.querySelectorAll('#workTbl tbody tr[data-row]')].map(r=>r.dataset.row)")

    def open_panel(self, id_):
        b = self.b
        self.open_decisions()
        sel = f'#workTbl tr[data-row="{id_}"] a.rowid'
        b.wait("(s=>{ const t=document.querySelector(s); if(!t) return false; const r=t.getBoundingClientRect(), e=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2); return !!(e&&(t===e||t.contains(e)||e.contains(t))); })(%s)" % json.dumps(sel), 10)   # a closing panel may still cover it
        for attempt in (1, 2):                                   # under heavy load a click can land while the list redraws: once more
            b.click(sel)                                         # BL-122: the ID opens it; a click elsewhere only highlights
            try:
                b.wait("document.getElementById('panel').classList.contains('on')", 10)
                break
            except TimeoutError:
                if attempt == 2:
                    raise
        b.wait(f"CUR&&CUR.id==='{id_}'")
        self.settle()

    def settle(self):
        """Wait for the panel to stop sliding or widening, so a click lands where the button is."""
        last = -1
        for _ in range(40):
            w = self.b.eval("document.getElementById('panel').getBoundingClientRect().width")
            if w > 300 and w == last:
                return
            last = w
            time.sleep(0.08)

    # ===== BL-176 (sprint-peek): the peek's chips, lists and staging =====
    def chip(self, field):
        self.b.click(f'#panel [data-pkp="{field}"]')
        self.b.wait("document.querySelector('.pkpop')")

    def options(self):
        return self.b.eval("[...document.querySelectorAll('.pkpop .pkopt')].map(o=>[o.querySelector('span').firstChild.textContent, o.getAttribute('aria-disabled')==='true'])")

    def pick(self, field, label):
        self.chip(field)
        self.b.eval(f"[...document.querySelectorAll('.pkpop .pkopt')].find(o=>o.querySelector('span').firstChild.textContent==={label!r}).click()")

    def apply(self, n):
        self.b.wait(f"PKS.length==={n}", 10)
        self.b.click("#pkApply")
        self.b.wait("PKS.length===0&&/Applied/.test(document.getElementById('snackT').textContent)", 20)

    def details(self):
        if self.b.eval("document.getElementById('pkDetT').getAttribute('aria-expanded')") != "true":
            self.b.click("#pkDetT")
        return self.b.eval("document.getElementById('pkDet').textContent")

    def set_field(self, field, value):
        self.b.eval(f"(()=>{{ const e=document.getElementById('f_{field}'); e.value={value!r}; e.dispatchEvent(new Event('input',{{bubbles:true}})); e.dispatchEvent(new Event('change',{{bubbles:true}})); }})()")

    def saved(self):
        self.b.wait("/saved and applied/.test(document.getElementById('snackT').textContent)", 15)


class ReadingTests(DecisionCase):
    shared_server = True            # nothing here changes data

    def test_the_data_carries_status_needed_by_and_the_rest(self):
        got = {x["id"]: x for x in self.b.eval("DEC")}
        self.assertEqual((got["ABC-D-006"]["st"], got["ABC-D-006"]["due"], got["ABC-D-006"]["date"], got["ABC-D-006"]["by"]),
                         ("Pending", d(-3), "", "Sara Example"))
        self.assertEqual((got["ABC-D-005"]["st"], got["ABC-D-005"]["rby"]), ("Made", "ABC-D-008"))     # replaced by the later one
        self.assertEqual((got["ABC-D-008"]["why"], got["ABC-D-008"]["opts"], got["ABC-D-008"]["replaces"]),
                         ("Production data isn't available", "Masked; synthetic", "ABC-D-005"))

    def test_the_pending_view_lists_only_pending_with_the_latest_first(self):
        self.open_decisions("pending")
        self.assertEqual(self.ids(), ["ABC-D-006", "ABC-D-007", "DEF-D-002"])        # late, then soonest, then no date
        self.assertEqual(self.b.eval("document.querySelector('#workTbl tr[data-row=\"ABC-D-006\"] td[data-f=due]').classList.contains('late')"), True)
        self.assertEqual(self.b.eval("document.querySelector('#workTbl tr[data-row=\"ABC-D-007\"] td[data-f=due]').classList.contains('late')"), False)
        self.assertEqual(self.b.eval("[...document.querySelectorAll('#workTbl thead th')].map(t=>t.dataset.col)"),
                         ["t", "st", "by", "due", "date", "src"])
        self.assertEqual(self.b.errors, [])

    def test_the_overdue_view_and_the_status_filter(self):
        self.open_decisions("overdue")
        self.assertEqual(self.ids(), ["ABC-D-006"])
        self.open_decisions("all")
        self.assertEqual(sorted(self.ids()), ["ABC-D-005", "ABC-D-006", "ABC-D-007", "ABC-D-008", "DEF-D-002"])

    def test_a_decision_needed_is_in_the_new_menu_only_on_the_decisions_tab(self):
        """BL-159: one New button with a menu on Decisions (Record a decision, Ask for a decision); a plain tile elsewhere."""
        self.open_decisions()
        self.assertFalse(self.b.eval("!!document.getElementById('newDecNeeded')"))
        self.assertEqual(self.b.eval("document.getElementById('newBtn').getAttribute('aria-haspopup')"), "menu")
        self.b.click('#wtabs button[data-t="actions"]')
        self.b.wait("WT==='actions'")
        self.assertIsNone(self.b.eval("document.getElementById('newBtn').getAttribute('aria-haspopup')"))

    def test_the_overdue_decision_is_an_early_warning(self):
        warns = [w for w in self.b.eval("D.warnings") if w["k"] == "decisions"]
        self.assertEqual([(w["id"], w["sig"]) for w in warns], [("ABC-D-006", "decision_overdue")])
        self.assertIn("3 days late", warns[0]["text"])
        self.assertIn("Sara Example", warns[0]["text"])
        self.open_decisions("pending")
        self.assertTrue(self.b.eval("!!document.querySelector('#workTbl tr[data-row=\"ABC-D-006\"] .wflag')"))
        self.assertFalse(self.b.eval("!!document.querySelector('#workTbl tr[data-row=\"ABC-D-007\"] .wflag')"))

    def test_today_says_how_many_wait_on_others_and_how_many_are_yours(self):
        self.b.eval("go('today')")
        self.b.wait("document.querySelector('#attnList li')")
        text = self.b.eval("[...document.querySelectorAll('#attnList li')].map(l=>l.textContent)")
        line = next(t for t in text if "waiting on others" in t)
        self.assertIn("2 decisions waiting on others, 1 for you, 1 late", line)
        self.assertIn("Extend the pilot by two weeks", line)
        self.assertIn("3 days late", line)

    def test_a_revisit_date_that_has_come_is_a_reminder(self):
        self.b.eval("go('today')")
        self.b.wait("document.querySelector('#attnList li')")
        text = self.b.eval("[...document.querySelectorAll('#attnList li')].map(l=>l.textContent)")
        self.assertTrue(any("ABC-D-008 is due to be revisited" in t for t in text), text)
        self.assertEqual([r["id"] for r in self.b.eval("REMINDERS") if r["id"].startswith("revisit:")], [f"revisit:ABC-D-008:{d(-1)}"])

    def test_the_project_page_has_a_decisions_needed_card(self):
        self.b.eval("go('cockpit','ABC')")
        self.b.wait("document.getElementById('decCard')")
        card = self.b.eval("document.getElementById('decCard').textContent")
        self.assertIn("Extend the pilot by two weeks", card)
        self.assertIn("Choose the UAT venue", card)
        self.assertNotIn("Approve the pilot budget", card)                            # DEF's
        self.assertIn("asked of you", card)
        self.assertIn("From Sara Example".lower(), card.lower())
        self.assertIn("To revisit", card)
        self.assertIn("ABC-D-008", card)
        self.b.eval("go('cockpit','DEF')")
        self.b.wait("document.getElementById('decCard')")
        self.assertIn("Approve the pilot budget", self.b.eval("document.getElementById('decCard').textContent"))
        self.assertIn("no date needed by", self.b.eval("document.getElementById('decCard').textContent"))

    def test_recent_decisions_on_the_project_page_leave_out_pending_ones(self):
        self.b.eval("go('cockpit','ABC')")
        self.b.wait("document.getElementById('decCard')")
        recent = self.b.eval("[...document.querySelectorAll('.card')].find(c=>/Recent decisions/.test(c.textContent)).textContent")
        self.assertNotIn("Choose the UAT venue", recent)

    def test_a_persons_page_lists_the_decisions_we_wait_on_from_them(self):
        self.b.eval("go('person','Sara Example')")
        self.b.wait("document.getElementById('decWaiting')")
        text = self.b.eval("document.getElementById('decWaiting').textContent")
        self.assertIn("waiting on from Sara", text)
        self.assertIn("Extend the pilot by two weeks", text)
        self.assertIn("3 days late", text)
        self.assertNotIn("Choose the UAT venue", text)                                # Alan's own

    def test_the_draft_email_asks_for_the_decisions(self):
        self.b.eval("go('person','Sara Example')")
        self.b.wait("document.getElementById('ppEmail')")
        self.b.click("#ppEmail")
        self.b.wait("document.getElementById('dePrev')&&document.getElementById('dePrev').innerHTML.length>50")
        self.assertEqual(self.b.eval("DE.items.filter(i=>i.k==='decisions').map(i=>i.id)"), ["ABC-D-006"])       # offered...
        self.assertNotIn("Decision needed", self.b.eval("document.getElementById('dePrev').innerText"))          # ...but Sara is outside our domains and it isn't client-visible, so unticked
        self.assertIn("internal", self.b.eval("document.querySelector('[data-deit=\"decisions:ABC-D-006\"]').closest('label').textContent"))
        self.b.click('[data-deit="decisions:ABC-D-006"]')                                                          # ticked on purpose
        self.b.wait("/Decision needed/.test(document.getElementById('dePrev').innerText)")
        html = self.b.eval("document.getElementById('dePrev').innerText")
        self.assertIn("Decision needed: Extend the pilot by two weeks", html)
        self.assertIn("could you let me know what you have decided", html)

    def test_the_draft_email_builder_leaves_the_text_alone_without_decisions(self):
        out = self.b.eval("""(()=>{ const items=[{k:"actions",id:"ABC-A-001",p:"ABC",t:"Send the SOW",due:null,pr:"High"}];
          const o=draftEmail({name:"Sara Example",email:"",items,includeUpdate:false,replyBy:"",now:new Date(),today:TODAY,dueSoon:7,names:{ABC:"Example"},from:"Alan"});
          return {text:o.text, html:o.html}; })()""")
        self.assertNotIn("decision", out["text"].lower())
        self.assertNotIn("decision", out["html"].lower())

    def test_the_panel_offers_record_and_withdraw_only_on_a_pending_decision(self):
        """BL-176: Status records or withdraws a pending decision; a made one can't go back to pending (disabled, with why)."""
        self.open_panel("ABC-D-006")
        self.chip("st")
        self.assertEqual(self.options(), [["Pending", False], ["Made", False], ["Withdrawn", False]])
        self.b.key("Escape")
        self.b.click("#pkMore")
        self.b.wait("document.querySelector('.pkpop')")
        self.assertEqual(self.options()[0], ["Mark as made", False])
        self.b.key("Escape")
        self.b.eval("closePanel()")
        self.open_panel("ABC-D-008")
        self.chip("st")
        self.assertEqual(self.options()[0], ["Pending", True])
        self.b.key("Escape")
        self.assertIn("Production data isn't available", self.b.eval("document.getElementById('pkDesc').textContent"))   # Reasoning
        text = self.details()
        self.assertIn("Masked; synthetic", text)
        self.assertIn("ABC-D-005", text)                                              # Replaces
        self.b.eval("closePanel()")
        self.open_panel("ABC-D-005")
        text = self.details()
        self.assertIn("Replaced by", text)
        self.assertIn("ABC-D-008", text)

    def test_the_early_warning_setting_is_listed(self):
        self.assertIn("decision_overdue", self.b.eval("WSIG.map(s=>s[0])"))
        self.assertEqual(self.b.eval("D.warn_settings.decision_overdue"), {"on": True, "days": 1})


class WritingTests(DecisionCase):
    def test_record_the_decision_opens_the_form_filled_in_and_keeps_the_same_record(self):
        """BL-176: Status › Made stages Made with today's date on the same record; Apply writes it."""
        self.open_panel("ABC-D-006")
        self.pick("st", "Made")
        self.b.wait("PKS.length===1", 10)
        self.assertEqual(self.b.eval("PKS[0].patch"), {"st": "Made", "date": TODAY.isoformat()})
        self.assertIn(shown(TODAY.isoformat()), self.b.eval("document.querySelector('#panel [data-pkp=\"date\"]').textContent"))
        self.assertEqual(self.row("ABC-D-006")["status"], "Pending")                  # staged, not applied
        self.apply(1)
        row = self.row("ABC-D-006")
        self.assertEqual((row["status"], row["date"], row["made_by"], row["decision"]),
                         ("Made", TODAY.isoformat(), "Sara Example", "Extend the pilot by two weeks"))
        self.assertEqual(len(self.v.rows("decisions")), 5)                            # no new record
        self.assertEqual(self.b.errors, [])

    def test_a_made_decision_without_its_date_is_refused_in_the_form(self):
        """BL-176: a made decision's Date made can't be cleared."""
        self.open_panel("ABC-D-008")
        before = self.row("ABC-D-008")["date"]
        self.chip("date")
        self.b.eval("[...document.querySelectorAll('.pkpop .mini')].find(b=>b.textContent==='Clear').click()")
        self.b.wait("document.getElementById('pkNote').textContent.length>0", 5)
        self.assertIn("needs the date", self.b.eval("document.getElementById('pkNote').textContent"))
        self.assertEqual(self.b.eval("PKS.length"), 0)
        self.assertEqual(self.row("ABC-D-008")["date"], before)

    def test_cancelling_the_record_form_leaves_it_pending(self):
        """BL-176: Undo last takes the staged Made back, and the decision stays pending."""
        self.open_panel("ABC-D-006")
        self.pick("st", "Made")
        self.b.wait("PKS.length===1", 10)
        self.b.click("#pkUndo")
        self.b.wait("PKS.length===0", 10)
        self.assertEqual(self.b.eval("DEC.find(x=>x.id==='ABC-D-006').st"), "Pending")
        self.assertIn("Pending", self.b.eval("document.getElementById('pkProps').textContent"))
        self.assertEqual(self.row("ABC-D-006")["status"], "Pending")

    def test_withdraw_asks_to_confirm_then_closes_it_without_a_decision(self):
        """BL-176: Status › Withdrawn is staged; nothing changes until Apply, which closes it without a decision."""
        self.open_panel("ABC-D-007")
        self.pick("st", "Withdrawn")
        self.b.wait("PKS.length===1", 10)
        self.assertEqual(self.row("ABC-D-007")["status"], "Pending")                  # staged isn't applied
        self.apply(1)
        row = self.row("ABC-D-007")
        self.assertEqual((row["status"], row["date"]), ("Withdrawn", None))
        self.assertEqual(self.b.eval("DEC.find(x=>x.id==='ABC-D-007').st"), "Withdrawn")
        self.assertNotIn("ABC-D-007", self.b.eval("decPending().map(x=>x.id)"))

    def text_field(self, sel, value):
        """BL-179: a new decision's text is the peek's own (title, Source, Reasoning): type it and leave the field."""
        self.b.eval(f"(()=>{{ const t=document.querySelector({sel!r}); t.focus(); t.textContent={value!r}; t.blur(); }})()")
        self.b.eval("pkQuiet().then(()=>true)")

    def test_a_decision_needed_is_raised_from_the_work_page(self):
        self.open_decisions()
        self.b.click("#newBtn")                                              # BL-159: the New menu's Ask for a decision
        self.b.click('#newMenu [data-newd="needed"]')
        self.b.wait("CUR&&CUR.mode==='new'&&document.activeElement.id==='pkTitle'")   # BL-179: the empty peek
        self.assertEqual(self.b.eval("CUR.draft.st"), "Pending")
        self.assertEqual(self.b.eval("CUR.draft.date"), "")
        self.b.eval("pkCommit('decisions',CUR.nid,{p:'ABC'},'Project','','')")
        self.pick("o", "Sara Example")
        self.b.eval(f"pkCommit('decisions',CUR.nid,{{due:{d(9)!r}}},'Needed by','','')")
        self.text_field("#pkSrcIn", "Steering committee, 08-10")
        self.text_field("#pkDesc", "The client freeze starts the week after")
        self.text_field("#pkTitle", "Confirm the go-live weekend")            # the title with a project: staged
        self.apply(1)
        row = next(r for r in self.v.rows("decisions") if r["decision"] == "Confirm the go-live weekend")
        self.assertEqual((row["status"], row["date"], row["made_by"], row["needed_by"], row["reasoning"]),
                         ("Pending", None, "Sara Example", d(9), "The client freeze starts the week after"))
        self.assertIn("recorded by", row["source"])

    def test_a_new_made_decision_still_needs_its_date_and_source(self):
        self.open_decisions()
        self.b.click("#newBtn")                                              # BL-159: the New menu's Record a decision
        self.b.click('#newMenu [data-newd="made"]')
        self.b.wait("CUR&&CUR.mode==='new'&&document.activeElement.id==='pkTitle'")
        self.assertEqual(self.b.eval("[CUR.draft.st, CUR.draft.date]"), ["Made", TODAY.isoformat()])
        self.b.eval("pkCommit('decisions',CUR.nid,{p:'ABC'},'Project','','')")
        self.text_field("#pkTitle", "Move the review to Tuesday")
        self.assertIn("Record where", self.b.eval("document.getElementById('pkNote').textContent"))
        self.assertEqual(self.b.eval("PKS.length"), 0)
        self.b.eval("pkSetDate('decisions',CUR.nid,'')")                          # a made decision keeps its date
        self.assertEqual(self.b.eval("CUR.draft.date"), TODAY.isoformat())
        self.text_field("#pkSrcIn", "Email from Jane")
        self.apply(1)
        row = next(r for r in self.v.rows("decisions") if r["decision"] == "Move the review to Tuesday")
        self.assertEqual((row["status"], row["date"]), ("Made", TODAY.isoformat()))

    def test_saving_a_made_decision_back_to_pending_is_refused(self):
        self.open_panel("ABC-D-005")
        self.chip("st")
        self.assertEqual(self.options()[0], ["Pending", True])                       # BL-176: disabled, with why
        self.assertIn("can't go back to pending", self.b.eval("document.querySelector('.pkpop .pkopt .h').textContent"))
        self.b.key("Escape")
        self.b.eval("pkSetStatus('decisions','ABC-D-005','Pending')")                  # and refused if asked anyway
        self.assertIn("can't go back to pending", self.b.eval("document.getElementById('pkNote').textContent"))
        self.assertEqual(self.b.eval("PKS.length"), 0)

    def test_choosing_pending_clears_the_date_and_edits_the_reasoning(self):
        self.open_panel("ABC-D-006")
        self.b.click("#pkDesc")                                                       # BL-176: the reasoning is the free text
        self.b.eval("(()=>{ const d=document.getElementById('pkDesc'); d.textContent='Sara asked for more time'; d.blur(); })()")
        self.b.wait("PKS.length===1", 10)
        self.details()
        self.b.click('#pkDet [data-pkf="revisit"]')
        self.b.eval("(()=>{ const d=document.querySelector('#pkDet [data-pkf=\"revisit\"]'); d.textContent='revisit if adoption falls below 60%'; d.blur(); })()")
        self.apply(2)
        row = self.row("ABC-D-006")
        self.assertEqual((row["status"], row["reasoning"], row["revisit"]),
                         ("Pending", "Sara asked for more time", "revisit if adoption falls below 60%"))

if __name__ == "__main__":
    unittest.main()
