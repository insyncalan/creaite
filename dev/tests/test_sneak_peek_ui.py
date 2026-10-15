"""BL-322 (v193-sneak-peek-ui): Sneak peek, the screen, in Chrome against the real live server (POST /api/sneak/read, plain
code, no model call; dev/sprints/BL-322-contract.md). From the mockup (dev/mockups/sneak-peek-mockup.html):
- opening: `//` outside a field opens the box over the bottom of the peek; one `/` still opens ask creaite after its short wait;
  neither inside a field; the sparkle in the peek's top bar (left of Draft chase) and the "// Change this item in words" foot line
  open it too; Esc closes it and leaves the peek open; ↑ in the empty box brings back the last instruction;
- a plain change on each kind of item (an action, a risk, a decision, a milestone) through the peek's save path, applied at once,
  with Undo straight after;
- the confirm list (amber) is never made with plain Enter, only ⌘⏎ or a click; closing an action offers a closing update;
- a name that matches two people asks which; a refusal says where to go and changes nothing;
- with AI drafts off the Claude part says why and the plain part still works; "chase …, firmer" opens Draft chase in that tone;
- the box says "VIP" nowhere (BL-288).

Run: python3 dev/tests/test_sneak_peek_ui.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import drafts_fake  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import new  # noqa: E402
from test_draft_chase import REGISTER  # noqa: E402
from test_tracker import ABC, action  # noqa: E402

NOW = "2026-10-14 09:00"          # a Wednesday: "Friday" is 16-10-2026
CMD = 4                           # the Command modifier for b.key (⌘⏎)
PEOPLE = REGISTER.rstrip("\n") + "\n| Sam Patel | sam.patel@brightwater.example | Sam | Brightwater | Analyst |  |  |  |\n" \
                                 "| Sam Okafor | sam.okafor@example.com | Sam | Northgate | Test lead |  |  |  |\n"


def seed(v):
    """Someone else's open action, a risk, a pending decision and a milestone, all in ABC."""
    v.run("init")
    (v.root / "projects/_portfolio/people-register.md").write_text(PEOPLE)
    v.propose("seed", [
        action(1, description="Share the UAT plan", owner="Sara Example", due_date="2026-10-09", priority="High", raised="2026-10-05",
               latest_update="Plan in draft, waiting on the test environment dates",
               source=f"{ABC}/minutes/2026-10-05 Weekly.docx — Actions"),
        new("raid", 2, project="ABC", type="Risk", description="The test environment isn't ready for UAT", owner="Sara Example",
            impact="High", likelihood="Medium", status="Open", due_date="2026-10-23", raised="2026-10-07",
            response_action="Agree the environment dates at Thursday's call", source="Alan (cx-edit), 2026-10-07"),
        new("decisions", 3, project="ABC", decision="Which use cases go into phase 2", made_by="Jane Doe", status="Pending",
            needed_by="2026-10-15", source="Alan (cx-edit), 2026-10-06"),
        new("milestones", 4, project="ABC", name="UAT complete", baseline_date="2026-10-30", forecast_date="2026-11-06",
            owner="Sara Example", source="Alan (cx-edit)"),
    ])
    v.run("apply")


class Case(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        seed(v)
        cls.act = v.rows("actions")[0]["id"]
        cls.risk = v.rows("raid")[0]["id"]
        cls.dec = v.rows("decisions")[0]["id"]
        cls.ms = v.rows("milestones")[0]["id"]

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": NOW}

    def open(self, id_, k="actions"):
        b = self.b
        b.eval(f"WT={k!r}; go('work')")
        b.eval(f"openRecord({k!r},{id_!r})")
        b.wait(f"CUR&&CUR.id==={id_!r}&&document.getElementById('panel').classList.contains('peek')")
        b.pump(0.2)

    def open_ms(self):
        b = self.b
        b.eval("mvOpenPage('ABC','plan')")
        b.wait("VIEW==='milestones'&&document.querySelector('#v-milestones .mv-card')")
        b.eval(f"mvEdOpen({self.ms!r})")
        b.wait(f"MV.peek==={self.ms!r}&&document.getElementById('mvSneakBtn')")

    def box(self, how="sparkle"):
        """Open the box (by the sparkle, the foot line or //) and wait for its input to have focus."""
        b = self.b
        if how == "slashes":
            b.eval("document.activeElement.blur()")
            b.key("/")
            b.key("/")
        elif how == "hint":
            b.click("#pkSneakHintBtn")
        else:
            b.click("#pkSneakBtn" if b.eval("!!document.getElementById('pkSneakBtn')&&!document.getElementById('pkSneakBtn').hidden"
                                            "&&document.getElementById('panel').classList.contains('on')") else "#mvSneakBtn")
        b.wait("document.activeElement&&document.activeElement.id==='spIn'")

    def say(self, text, wait="#spCard"):
        """Type the words and wait for the card the server's reading draws."""
        b = self.b
        b.eval("(()=>{ const i=document.getElementById('spIn'); i.focus(); })()")
        b.type(text)
        if wait:
            b.wait(f"document.querySelector({wait!r})", timeout=15)

    def done(self):
        self.b.wait("document.querySelector('.sp-done #spUndo')", timeout=30)

    def out(self):
        return self.b.eval("document.getElementById('spOut').innerText")

    def row(self, table, id_):
        return next(r for r in self.v.rows(table) if r["id"] == id_)


class Opening(Case):
    shared_server = True

    def test_the_sparkle_sits_left_of_draft_chase_and_the_foot_line_is_there(self):
        b = self.b
        self.open(self.act)
        o = b.eval("""(()=>{ const s=document.getElementById('pkSneakBtn'); return {next:s.nextElementSibling.id, hidden:s.hidden,
          label:s.getAttribute('aria-label'), key:s.dataset.key, icon:s.querySelector('svg').dataset.icn,
          hint:!document.getElementById('pkSneakHint').hidden, words:document.getElementById('pkSneakHintBtn').textContent}; })()""")
        words = o.pop("words")
        self.assertEqual(o, {"next": "pkChaseBtn", "hidden": False, "label": "Sneak peek: change this item in words", "key": "//",
                             "icon": "sneak", "hint": True})
        self.assertEqual(words.replace(" ", ""), "//Changethisiteminwords")

    def test_not_for_a_proposal_or_a_new_item(self):
        b = self.b
        b.eval("openNew('actions')")
        b.wait("CUR&&CUR.mode==='new'")
        self.assertTrue(b.eval("document.getElementById('pkSneakBtn').hidden&&document.getElementById('pkSneakHint').hidden"))
        b.eval("document.activeElement.blur()")
        b.key("/")
        b.key("/")
        b.pump(0.5)
        self.assertFalse(b.eval("!!document.getElementById('spIn')"), "// does nothing without an item")

    def test_two_slashes_open_it_and_one_slash_still_opens_ask_creaite(self):
        b = self.b
        self.open(self.act)
        self.box("slashes")
        self.assertFalse(b.eval("document.getElementById('chat').classList.contains('on')"))
        self.assertTrue(b.eval("document.getElementById('panel').classList.contains('sp-open')"))
        b.key("Escape")
        self.assertFalse(b.eval("!!document.getElementById('spIn')"))
        self.assertTrue(b.eval("document.getElementById('panel').classList.contains('on')"), "Esc closes the box, not the peek")
        b.eval("document.activeElement.blur()")
        b.key("/")
        self.assertFalse(b.eval("document.getElementById('chat').classList.contains('on')"), "it waits for a second slash first")
        b.wait("document.getElementById('chat').classList.contains('on')", timeout=3)
        self.assertFalse(b.eval("!!document.getElementById('spIn')"))
        b.eval("closeChat()")

    def test_neither_fires_inside_a_field(self):
        b = self.b
        self.open(self.act)
        b.click("#pkTitle")
        b.key("/")
        b.key("/")
        b.pump(0.6)
        self.assertFalse(b.eval("!!document.getElementById('spIn')"))
        self.assertFalse(b.eval("document.getElementById('chat').classList.contains('on')"))
        b.key("Escape")

    def test_the_foot_line_opens_it_esc_closes_and_focus_returns(self):
        b = self.b
        self.open(self.act)
        self.box("hint")
        self.assertEqual(b.eval("document.getElementById('spBox').getAttribute('role')"), "dialog")
        self.assertEqual(b.eval("document.querySelector('label[for=spIn]').textContent"), f"Change {self.act} in words")
        self.assertTrue(b.eval("document.getElementById('pkSneakHint').hidden"), "the foot line steps aside while the box is open")
        b.key("Escape")
        self.assertFalse(b.eval("!!document.getElementById('spIn')"))
        self.assertEqual(b.eval("document.activeElement.id"), "pkSneakHintBtn")
        self.box("sparkle")
        self.assertEqual(b.eval("document.getElementById('pkSneakBtn').getAttribute('aria-pressed')"), "true")
        b.click("#pkSneakBtn")
        self.assertFalse(b.eval("!!document.getElementById('spIn')"), "a second press closes it")

    def test_the_peek_keeps_room_for_the_box(self):
        b = self.b
        self.open(self.act)
        self.box()
        b.pump(0.3)
        pad = b.eval("parseFloat(getComputedStyle(document.getElementById('pkScroll')).paddingBottom)")
        h = b.eval("document.getElementById('spBox').offsetHeight")
        self.assertGreaterEqual(pad, h, "the scroll area can bring everything above the box")
        b.key("Escape")


class Changes(Case):
    def test_an_action_owner_due_date_and_priority_with_undo(self):
        b = self.b
        self.open(self.act)
        self.box()
        self.say("owner to Tom and due Friday")
        card = self.out()
        self.assertIn("Understood in plain code", card)
        self.assertIn("Tom Reid", card)
        self.assertIn("16-10-2026", card)
        self.assertTrue(b.eval("document.querySelectorAll('#spOut .sp-mark').length>=1"), "what was understood is marked")
        b.key("Enter")
        self.done()
        r = self.row("actions", self.act)
        self.assertEqual((r["owner"], r["due_date"]), ("Tom Reid", "2026-10-16"))
        self.assertTrue(b.eval(f"A.find(x=>x.id==={self.act!r}).o==='Tom Reid'"), "the peek shows it")
        self.assertEqual(b.eval("document.getElementById('spIn').value"), "")
        b.click("#spUndo")
        b.wait("/Undone/.test(document.getElementById('spOut').innerText)", timeout=30)
        r = self.row("actions", self.act)
        self.assertEqual((r["owner"], r["due_date"]), ("Sara Example", "2026-10-09"))
        self.say("priority urgent")
        b.key("Enter")
        self.done()
        self.assertEqual(self.row("actions", self.act)["priority"], "Urgent")
        # ↑ in the empty box brings back the last instruction
        b.key("ArrowUp")
        self.assertEqual(b.eval("document.getElementById('spIn').value"), "priority urgent")

    def test_closing_an_action_offers_a_closing_update(self):
        b = self.b
        self.open(self.act)
        self.box()
        self.say("close it")
        self.assertTrue(b.eval("!!document.getElementById('spClose')"), "an optional closing update")
        b.click("#spClose")
        b.type("Plan shared with the client")
        b.key("Enter")
        self.done()
        r = self.row("actions", self.act)
        self.assertEqual(r["status"], "Closed")
        self.assertIn("Plan shared with the client", r["latest_update"] or "")

    def test_a_risk_impact_shows_the_worked_out_priority(self):
        b = self.b
        self.open(self.risk, "raid")
        self.box()
        self.say("impact low")
        self.assertIn("Priority", self.out())
        self.assertIn("worked out", self.out())
        b.key("Enter")
        self.done()
        self.assertEqual(self.row("raid", self.risk)["impact"], "Low")

    def test_a_decision_needed_by_and_revisit(self):
        b = self.b
        self.open(self.dec, "decisions")
        self.box()
        self.say("needed by 20-10")
        b.key("Enter")
        self.done()
        self.assertEqual(self.row("decisions", self.dec)["needed_by"], "2026-10-20")
        self.say("revisit if adoption falls below 60%")
        b.key("Enter")
        self.done()
        self.assertIn("adoption falls below 60%", self.row("decisions", self.dec)["revisit"] or "")

    def test_a_milestone_forecast_in_the_milestone_editor(self):
        b = self.b
        self.open_ms()
        self.assertTrue(b.eval("!document.getElementById('mvSneakHint').hidden"))
        self.box()
        self.say("forecast to 13-11")
        b.key("Enter")
        self.done()
        self.assertEqual(self.row("milestones", self.ms)["forecast_date"], "2026-11-13")
        self.assertTrue(b.eval("!!document.getElementById('spIn')"), "the box survives the editor's redraw")
        b.key("Escape")
        self.assertFalse(b.eval("!!document.getElementById('spIn')"))
        self.assertTrue(b.eval("!document.getElementById('mvPeek').hidden"), "Esc closes the box, not the editor")


class MoreFields(Case):
    def test_an_update_a_label_and_a_word_taken_back_out_on_an_action(self):
        b = self.b
        self.open(self.act)
        self.box()
        self.say("owner to Tom and due Friday")
        n = b.eval("document.querySelectorAll('#spOut .sp-mark').length")
        b.eval("document.querySelector('#spOut .sp-mark').click()")          # take "owner to Tom" back out
        b.wait(f"document.querySelectorAll('#spOut .sp-mark').length<{n}", timeout=15)
        b.wait("!/Owner/.test(document.getElementById('spOut').innerText)", timeout=15)   # the read of what is left
        self.assertNotIn("Tom", b.eval("document.getElementById('spIn').value"))
        self.assertNotIn("Tom", self.out())
        b.eval("(()=>{ const i=document.getElementById('spIn'); i.value=''; i.dispatchEvent(new Event('input',{bubbles:true})); })()")
        self.say("add an update: Northgate confirmed the dates")
        b.key("Enter")
        self.done()
        self.assertIn("Northgate confirmed the dates", self.row("actions", self.act)["latest_update"] or "")
        self.say("label it Sensitive")
        b.key("Enter")
        self.done()
        self.assertTrue(b.eval(f"(A.find(x=>x.id==={self.act!r}).labels||[]).join(',').includes('Sensitive')")
                        or "Sensitive" in json.dumps(self.v.rows("item_labels")))

    def test_a_risk_likelihood_and_response(self):
        b = self.b
        self.open(self.risk, "raid")
        self.box()
        self.say("likelihood high, response: Escalate to the test lead")
        b.key("Enter")
        self.done()
        r = self.row("raid", self.risk)
        self.assertEqual((r["likelihood"], r["response_action"]), ("High", "Escalate to the test lead"))

    def test_a_decision_maker_and_a_milestone_owner(self):
        b = self.b
        self.open(self.dec, "decisions")
        self.box()
        self.say("decision maker to Omar")
        b.key("Enter")
        self.done()
        self.assertEqual(self.row("decisions", self.dec)["made_by"], "Omar Ali")
        b.key("Escape")
        b.eval("closePanel()")
        self.open_ms()
        self.box()
        self.say("owner to Tom")
        b.key("Enter")
        self.done()
        self.assertEqual(self.row("milestones", self.ms)["owner"], "Tom Reid")

    def test_a_follow_on_action_and_its_link_with_one_undo(self):
        b = self.b
        self.open(self.act)
        self.box()
        self.say("add an action for Tom to confirm the test dates, due Friday")
        self.assertIn("New action", self.out())
        self.assertIn("ID given when applied", self.out())
        before = len(self.v.rows("actions"))
        b.key("Enter")
        self.done()
        acts = self.v.rows("actions")
        self.assertEqual(len(acts), before + 1)
        new_ = next(r for r in acts if r["description"].lower().startswith("confirm the test dates"))
        self.assertEqual((new_["owner"], new_["due_date"]), ("Tom Reid", "2026-10-16"))
        self.assertTrue(any(l["from_item"] == new_["id"] and l["to_item"] == self.act for l in self.v.rows("links")))
        b.click("#spUndo")
        b.wait("/Undone/.test(document.getElementById('spOut').innerText)", timeout=30)
        self.assertEqual(len([r for r in self.v.rows("actions") if r["status"] != "Cancelled" and r["id"] == new_["id"]]), 0)
        self.assertFalse(any(l["from_item"] == new_["id"] for l in self.v.rows("links")))

    def test_a_milestone_state_needs_a_confirm(self):
        b = self.b
        self.open_ms()
        self.box()
        self.say("state at risk because the environment is late")
        self.assertTrue(b.eval("document.getElementById('spCard').classList.contains('warn')"))
        b.key("Enter")
        b.pump(1)
        self.assertFalse(b.eval("!!document.querySelector('.sp-done')"))
        b.key("Enter", CMD)
        self.done()
        self.assertEqual((self.row("milestones", self.ms)["state"] or "").lower().replace(" ", ""), "atrisk")


class Confirm(Case):
    def test_plain_enter_never_makes_a_confirm_but_cmd_enter_does(self):
        b = self.b
        self.open(self.act)
        self.box()
        self.say("cancel it")
        self.assertTrue(b.eval("document.getElementById('spCard').classList.contains('warn')"), "amber")
        self.assertTrue(b.eval("!!document.getElementById('spNeed')"))
        b.key("Enter")
        b.pump(1.5)
        self.assertEqual(self.row("actions", self.act)["status"], "Open", "plain Enter doesn't make it")
        self.assertFalse(b.eval("!!document.querySelector('.sp-done')"))
        b.key("Enter", CMD)
        self.done()
        self.assertEqual(self.row("actions", self.act)["status"], "Cancelled")

    def test_a_click_makes_a_confirm(self):
        b = self.b
        self.open(self.risk, "raid")
        self.box()
        self.say("this has happened")
        self.assertTrue(b.eval("document.getElementById('spCard').classList.contains('warn')"))
        b.click("#spMake")
        self.done()
        self.assertEqual(self.row("raid", self.risk)["type"], "Issue")


class Answers(Case):
    shared_server = True

    def test_a_name_that_matches_two_people_asks_which(self):
        b = self.b
        self.open(self.act)
        self.box()
        self.say("owner to Sam", wait="#spChoices")
        names = b.eval("[...document.querySelectorAll('#spChoices .pick button')].map(x=>x.textContent)")
        self.assertEqual(len(names), 2)
        self.assertTrue(any("Sam Patel" in n for n in names) and any("Sam Okafor" in n for n in names))
        b.eval("[...document.querySelectorAll('#spChoices .pick button')].find(x=>x.textContent.includes('Sam Okafor')).click()")
        b.wait("document.getElementById('spCard')&&document.getElementById('spCard').innerText.includes('Sam Okafor')", timeout=15)
        self.assertEqual(self.row("actions", self.act)["owner"], "Sara Example", "nothing changes until Enter")
        b.key("Escape")

    def test_a_refusal_points_elsewhere_and_changes_nothing(self):
        b = self.b
        before = self.row("actions", self.act)
        self.open(self.act)
        self.box()
        self.say("email Sara about this", wait="#spRefused")
        self.assertEqual(b.eval("document.querySelector('#spRefused [data-point]').dataset.point"), "draft_chase")
        b.key("Enter")
        b.pump(1)
        self.assertEqual(self.row("actions", self.act), before)
        b.click("#spRefused [data-point]")
        b.wait("!document.getElementById('pkChase').hidden", timeout=10)
        self.assertFalse(b.eval("!!document.getElementById('spIn')"))
        b.key("Escape")

    def test_quick_facts_are_read_only(self):
        b = self.b
        self.open(self.act)
        self.box()
        self.say("where did this come from?", wait="#spFacts")
        self.assertIn("read only", self.out())
        b.key("Escape")

    def test_chase_with_the_tone_set_opens_draft_chase(self):
        b = self.b
        self.open(self.act)
        self.box()
        self.say("chase Sara, firmer", wait="#spChase")
        b.key("Enter")
        b.wait("document.querySelector('#chSubj')", timeout=20)
        self.assertEqual(b.eval("[...document.querySelectorAll('[data-tone]')].map(x=>x.getAttribute('aria-pressed'))"), ["false", "false", "true"])
        b.key("Escape")

class PeoplePicker(Case):
    """`@` in the box: a short list from the people register, filtered as you type; ↑ ↓, Enter, Tab or a click picks; Esc closes
    the list only. A combobox and a listbox for screen readers; no VIP label."""

    def list_(self):
        return self.b.eval("[...document.querySelectorAll('#spPeople [role=option]')].map(o=>o.querySelector('.nm').textContent)")

    def test_typing_at_lists_people_and_the_keys_pick_one(self):
        b = self.b
        self.open(self.act)
        self.box()
        b.type("owner to @sa")
        b.wait("!document.getElementById('spPeople').hidden")
        names = self.list_()
        self.assertEqual(set(names), {"Sam Patel", "Sam Okafor", "Sara Example"})
        o = b.eval("""(()=>{ const i=document.getElementById('spIn'), l=document.getElementById('spPeople');
          return {role:i.getAttribute('role'), exp:i.getAttribute('aria-expanded'), ctl:i.getAttribute('aria-controls'),
            act:i.getAttribute('aria-activedescendant'), lrole:l.getAttribute('role'), label:l.getAttribute('aria-label'),
            sel:[...l.querySelectorAll('[role=option]')].map(x=>x.getAttribute('aria-selected')), focus:document.activeElement.id}; })()""")
        self.assertEqual((o["role"], o["exp"], o["ctl"], o["act"], o["lrole"], o["label"], o["focus"]),
                         ("combobox", "true", "spPeople", "spP0", "listbox", "People", "spIn"))
        self.assertEqual(o["sel"], ["true", "false", "false"])
        b.type("m")                                                         # filtered as you type
        b.wait("document.querySelectorAll('#spPeople [role=option]').length===2")
        b.key("ArrowDown")
        self.assertEqual(b.eval("document.getElementById('spIn').getAttribute('aria-activedescendant')"), "spP1")
        b.key("ArrowDown")                                                  # wraps
        self.assertEqual(b.eval("document.getElementById('spIn').getAttribute('aria-activedescendant')"), "spP0")
        b.key("ArrowUp")
        chosen = self.list_()[1]
        b.key("Enter")
        self.assertEqual(b.eval("document.getElementById('spIn').value"), f"owner to @{chosen} ")
        self.assertTrue(b.eval("document.getElementById('spPeople').hidden"))
        self.assertEqual(b.eval("document.getElementById('spIn').getAttribute('aria-expanded')"), "false")
        b.wait("document.getElementById('spCard')", timeout=15)
        self.assertIn(chosen, self.out())
        b.key("Enter")
        self.done()
        self.assertEqual(self.row("actions", self.act)["owner"], chosen)

    def test_esc_closes_the_list_only_and_a_click_picks(self):
        b = self.b
        self.open(self.act)
        self.box()
        b.type("owner to @to")
        b.wait("!document.getElementById('spPeople').hidden")
        b.key("Escape")
        self.assertTrue(b.eval("document.getElementById('spPeople').hidden"))
        self.assertTrue(b.eval("!!document.getElementById('spIn')"), "the box stays open")
        b.key("Backspace")
        b.type("o")
        b.wait("!document.getElementById('spPeople').hidden")
        b.eval("document.querySelector('#spPeople [role=option]').dispatchEvent(new MouseEvent('mousedown',{bubbles:true,cancelable:true}))")
        b.wait("document.getElementById('spIn').value==='owner to @Tom Reid '")
        self.assertEqual(b.eval("document.activeElement.id"), "spIn")

    def test_no_match_says_so_and_tab_picks(self):
        b = self.b
        self.open(self.act)
        self.box()
        b.type("@zzz")
        b.wait("document.getElementById('spNoMatch')")
        self.assertTrue(b.eval("document.getElementById('spPeople').hidden"))
        b.eval("(()=>{ const i=document.getElementById('spIn'); i.value=''; i.dispatchEvent(new Event('input',{bubbles:true})); })()")
        b.type("@om")
        b.wait("!document.getElementById('spPeople').hidden")
        b.key("Tab")
        self.assertEqual(b.eval("document.getElementById('spIn').value"), "@Omar Ali ")

class Flash(Case):
    """After a change the changed field is highlighted for a moment; with motion it fades, under reduced motion it holds still."""
    reduced_motion = False

    def test_the_changed_field_fades_and_the_highlight_goes(self):
        b = self.b
        self.open(self.act)
        self.box()
        self.say("priority urgent")
        b.key("Enter")
        self.done()
        b.wait("document.querySelector('[data-pkp=\"pr\"].sp-flash')", timeout=5)
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('[data-pkp=\"pr\"]')).animationName"), "sp-flash")
        self.assertFalse(b.eval("!!document.querySelector('[data-pkp=\"o\"].sp-flash')"), "only the changed field")
        b.wait("!document.querySelector('.sp-flash')", timeout=5)

    def test_a_milestone_forecast_flashes_in_the_editor(self):
        b = self.b
        self.open_ms()
        self.box()
        self.say("forecast to 13-11")
        b.key("Enter")
        self.done()
        b.wait("document.querySelector('#mvFc.sp-flash')", timeout=5)


class FlashReduced(Case):
    reduced_motion = True

    def test_under_reduced_motion_the_highlight_is_static(self):
        b = self.b
        self.open(self.act)
        self.box()
        self.say("due Friday")
        b.key("Enter")
        self.done()
        b.wait("document.querySelector('[data-pkp=\"due\"].sp-flash')", timeout=5)
        o = b.eval("""(()=>{ const s=getComputedStyle(document.querySelector('[data-pkp="due"].sp-flash'));
          return {name:s.animationName, bg:s.backgroundColor, running:document.getAnimations().filter(a=>a.playState==='running').length}; })()""")
        self.assertEqual(o["name"], "none")
        self.assertNotIn(o["bg"], ("rgba(0, 0, 0, 0)", "transparent"))
        self.assertEqual(o["running"], 0)
        b.wait("!document.querySelector('.sp-flash')", timeout=5)


class DraftsOn(Case):
    """Claude's part through /api/draft, with the stand-in Claude (drafts_fake.py): Yours beside Drafted, Use this or Keep mine."""
    @classmethod
    def load(cls, v):
        super().load(v)
        cls.fake = drafts_fake.install(v)

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": NOW, "CREAITE_CLAUDE": str(cls.fake)}

    def test_keep_mine_then_use_this_for_a_client_message(self):
        b = self.b
        self.open(self.act)
        self.box()
        self.say("write a client message", wait="#spDraft")
        b.key("Enter")
        b.wait("document.getElementById('spUse')", timeout=30)
        self.assertIn("Written by Claude", self.out())
        self.assertIn("Yours", self.out())
        b.click("#spKeep")
        b.wait("/Kept yours/.test(document.getElementById('spOut').innerText)")
        self.assertNotIn("Access to your data", self.row("actions", self.act)["client_message"] or "", "Keep mine changes nothing")
        self.say("write a client message", wait="#spDraft")
        b.click("#spDraft")
        b.wait("document.getElementById('spUse')", timeout=30)
        b.key("Enter")                                                       # Enter is Use this
        self.done()
        self.assertIn("Access to your data", self.row("actions", self.act)["client_message"] or "")


class DraftsOff(Case):
    @classmethod
    def load(cls, v):
        super().load(v)
        p = v.root / "system/config/settings.json"
        s = json.loads(p.read_text())
        s.setdefault("drafting", {}).update({"client": False, "update": False, "thinking": False})
        p.write_text(json.dumps(s, indent=2))

    def test_the_claude_part_says_why_and_the_plain_part_still_works(self):
        b = self.b
        self.open(self.act)
        self.box()
        self.say("write a client message", wait="#spClaude")
        self.assertTrue(b.eval("!!document.getElementById('spOff')"))
        self.assertIn("off", b.eval("document.getElementById('spOff').textContent").lower())
        self.assertFalse(b.eval("!!document.getElementById('spDraft')"))
        b.eval("(()=>{ const i=document.getElementById('spIn'); i.value=''; i.dispatchEvent(new Event('input',{bubbles:true})); })()")
        self.say("due Friday")
        b.key("Enter")
        self.done()
        self.assertEqual(self.row("actions", self.act)["due_date"], "2026-10-16")


if __name__ == "__main__":
    unittest.main()
