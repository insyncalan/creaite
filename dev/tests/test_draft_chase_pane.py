"""BL-298 (v19-draft-chase): the Draft email pane in the work-item peek, in Chrome, against the real live server
(/api/chase/pane and /api/chases, drafts.py: no model call). From the mockup (dev/mockups/draft-chase-mockup.html): the
envelope left of Copy link (key C) on an open item only; the pane inside the peek, Back and Esc returning to the item; the three
modes (someone else's item: a chase; Alan's own: a request for help with a recipient he picks; a pending decision); the controls
in order with their defaults; the preview following what he types, in the email's fixed colours whatever the theme; Copy for
Outlook (HTML with a plain-text fallback, on a stubbed clipboard), Copy as text, and I sent it stepping the next one up. Nobody
is labelled a VIP (BL-288).

Run: python3 dev/tests/test_draft_chase_pane.py   (needs Google Chrome; skipped otherwise)
"""
import json
import re
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import drafts_fake  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import new  # noqa: E402
from test_draft_chase import NOW, REGISTER  # noqa: E402
from test_tracker import ABC, action  # noqa: E402

# A clipboard that keeps what is put on it, each type as text (the headless browser's own needs a permission).
CLIPBOARD = """(()=>{ window.CLIP=[]; Object.defineProperty(navigator,'clipboard',{configurable:true,value:{
  write: async items=>{ for(const it of items){ const o={}; for(const t of it.types) o[t]=await (await it.getType(t)).text(); CLIP.push(o); } },
  writeText: async t=>{ CLIP.push({'text/plain':t}); } }}); })()"""


def seed(v):
    """Alan's own action, someone else's overdue action, a pending decision, a closed action, a made decision, a proposal."""
    v.run("init")
    (v.root / "projects/_portfolio/people-register.md").write_text(REGISTER)
    src = f"{ABC}/minutes/2026-10-12 Alan x Tom catch up.docx — Actions"
    v.propose("seed", [
        action(1, description="Reach out to Dana on back-to-back commercials", due_date="2026-10-19", raised="2026-10-12",
               latest_update="12-10-2026: Tom asked for the commercials to mirror the Kestrel Group terms", source=src),
        action(2, description="Share the UAT plan", owner="Sara Example", due_date="2026-10-09", priority="High", raised="2026-10-05",
               latest_update="Plan in draft, waiting on the test environment dates",
               source="Email · From: Omar Ali <omar@def.example> · Subject: UAT plan · Sent: 2026-10-05 10:00"),
        new("decisions", 4, project="ABC", decision="Which use cases go into phase 2", made_by="Jane Doe", status="Pending",
            needed_by="2026-10-15", source="Alan (cx-edit), 2026-10-06"),
        action(5, description="Old thing", raised="2026-10-01", status="Closed", closed="2026-10-02"),
        new("decisions", 6, project="ABC", decision="Go with the cloud pilot", made_by="Jane Doe", status="Made", date="2026-10-02",
            source="Alan (cx-edit), 2026-10-02"),
    ])
    v.run("apply")
    v.propose("waiting", [{**action(7, description="A proposed action", raised="2026-10-12"), "decision": "pending"}])     # stays pending: a proposal
    (v.root / "system/staging/calendar.json").write_text(json.dumps({"days": {"2026-10-12": [
        {"id": "e1", "start": "10:00", "end": "10:30", "title": "Alan x Tom catch up", "attendees": [
            {"name": "Tom Reid", "email": "tom.r@example.com"}, {"name": "Alan Carter", "email": "alan@brightwater.example"},
            {"name": "Sara Example", "email": ""}]}]}}))


class ChaseCase(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        seed(v)
        ids = {r["description"]: r["id"] for r in v.rows("actions")}
        cls.mine, cls.theirs, cls.closed = (ids["Reach out to Dana on back-to-back commercials"], ids["Share the UAT plan"], ids["Old thing"])
        decs = {r["decision"]: r["id"] for r in v.rows("decisions")}
        cls.decision, cls.made = decs["Which use cases go into phase 2"], decs["Go with the cloud pilot"]

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": NOW}

    def open(self, id_, k="actions"):
        b = self.b
        b.eval(f"WT={k!r}; go('work')")
        b.eval(f"openRecord({k!r},{id_!r})")
        b.wait(f"CUR&&CUR.id==={id_!r}&&document.getElementById('panel').classList.contains('peek')")
        b.pump(0.2)

    def chase(self, id_, k="actions"):
        """Open the item, then its Draft email with the envelope; wait for the drafted email."""
        self.open(id_, k)
        self.b.click("#pkChaseBtn")
        self.b.wait("document.querySelector('#chSubj')", timeout=20)

    def pane_text(self):
        return self.b.eval("document.getElementById('pkChase').innerText")

    def subject(self):
        return self.b.eval("document.getElementById('chSubj').textContent")

    def mail(self):
        return self.b.eval("document.getElementById('chMail').innerText")

    def until_mail(self, words, timeout=10):
        self.b.wait(f"document.getElementById('chMail')&&document.getElementById('chMail').innerText.includes({words!r})", timeout=timeout)


class TheIcon(ChaseCase):
    shared_server = True

    def test_it_sits_left_of_copy_link_with_its_name_and_key(self):
        b = self.b
        self.open(self.theirs)
        o = b.eval("(()=>{ const c=document.getElementById('pkChaseBtn'); return {next:c.nextElementSibling.id, hidden:c.hidden,"
                   " label:c.getAttribute('aria-label'), key:c.dataset.key, pressed:c.getAttribute('aria-pressed'),"
                   " icon:c.querySelector('svg').dataset.icn}; })()")
        self.assertEqual(o, {"next": "pkLink", "hidden": False, "label": "Draft email", "key": "C", "pressed": "false", "icon": "chase"})

    def test_shown_for_open_items_and_a_pending_decision_hidden_otherwise(self):
        b = self.b
        for id_, k, shown in ((self.theirs, "actions", True), (self.mine, "actions", True), (self.decision, "decisions", True),
                              (self.closed, "actions", False), (self.made, "decisions", False)):
            with self.subTest(item=id_):
                self.open(id_, k)
                self.assertEqual(b.eval("!document.getElementById('pkChaseBtn').hidden"), shown)
        b.eval("closePanel()")
        b.eval("openProposal(REV.find(r=>r.rec&&r.rec.t==='A proposed action').n)")
        b.wait("CUR&&CUR.mode==='proposal'")
        self.assertTrue(b.eval("document.getElementById('pkChaseBtn').hidden"), "never for a proposal")
        b.eval("closePanel()")
        b.eval("openNew('actions')")
        b.wait("CUR&&CUR.mode==='new'")
        self.assertTrue(b.eval("document.getElementById('pkChaseBtn').hidden"), "never for a new item")

    def test_c_opens_it_inside_the_peek_and_back_and_esc_return_to_the_item(self):
        b = self.b
        self.open(self.theirs)
        b.eval("document.activeElement.blur()")
        b.key("c")
        b.wait("document.querySelector('#chSubj')", timeout=20)
        self.assertTrue(b.eval("document.getElementById('pkScroll').hidden&&!document.getElementById('pkChase').hidden"))
        self.assertEqual(b.eval("document.getElementById('pkChaseBtn').getAttribute('aria-pressed')"), "true")
        self.assertTrue(b.eval("document.getElementById('panel').classList.contains('on')"), "the peek stays open beside Work")
        self.assertEqual(b.eval("document.activeElement.getAttribute('aria-label')"), "Back to the item")
        b.click('#pkChase button[aria-label="Back to the item"]')
        self.assertTrue(b.eval("!document.getElementById('pkScroll').hidden&&document.getElementById('pkChase').hidden"))
        self.assertEqual(b.eval("document.activeElement.id"), "pkChaseBtn")
        b.click("#pkChaseBtn")
        b.wait("document.querySelector('#chSubj')", timeout=20)
        b.key("Escape")
        self.assertTrue(b.eval("document.getElementById('pkChase').hidden&&document.getElementById('panel').classList.contains('on')"),
                        "the first Esc goes back to the item, not out of the peek")

    def test_c_while_typing_types_and_another_item_puts_the_item_back(self):
        b = self.b
        self.open(self.theirs)
        b.click("#pkTitle")
        b.key("c")
        self.assertTrue(b.eval("document.getElementById('pkChase').hidden"), "C in a text field is a letter")
        b.key("Escape")
        b.eval("document.activeElement.blur()")
        b.click("#pkChaseBtn")
        b.wait("document.querySelector('#chSubj')", timeout=20)
        self.open(self.mine)
        self.assertTrue(b.eval("document.getElementById('pkChase').hidden&&!document.getElementById('pkScroll').hidden"))


class Modes(ChaseCase):
    shared_server = True

    def test_someone_elses_item_chases_its_owner_with_the_defaults(self):
        b = self.b
        self.chase(self.theirs)
        o = b.eval("""(()=>{ const p=document.getElementById('pkChase'); return {tag:p.querySelector('.ch-mode .tag').textContent,
          line:p.querySelector('.ch-mode div').textContent, bold:p.querySelector('.ch-mode b').textContent,
          chip:p.querySelector('.ch-chip').textContent, sugg:p.querySelectorAll('.ch-sugg').length, need:!!p.querySelector('#chNeed'),
          reply:p.querySelector('#chReplyBy').value, tone:[...p.querySelectorAll('[data-tone]')].map(x=>x.textContent+':'+x.getAttribute('aria-pressed')),
          inc:p.querySelector('#chIncUpd').checked, buttons:[...p.querySelectorAll('.ch-acts button')].map(x=>x.textContent),
          order:[...p.querySelectorAll('.ch-mode,.ch-f,.ch-row2,.ch-inc,.ch-mailwrap,.ch-pol,.ch-acts')].map(x=>x.className.split(' ')[0])}; })()""")
        self.assertEqual((o["tag"], o["line"]), ("Chase", "Chasing Sara, who owns it. Not chased before: a first reminder."))
        self.assertEqual(o["bold"], "Chasing Sara")
        self.assertEqual((o["chip"], o["sugg"], o["need"]), ("Sara Example", 0, False))
        self.assertIn("sara.example@client.com", self.pane_text())
        self.assertEqual(o["reply"], "2026-10-15")                                   # two working days after Tuesday 13-10-2026
        self.assertEqual(o["tone"], ["First:true", "Second:false", "Firmer:false"])
        self.assertTrue(o["inc"])
        self.assertEqual(o["buttons"], ["Copy as text", "I sent it", "Copy for Outlook"])          # Polish has its own row (option A)
        self.assertEqual(o["order"], ["ch-mode", "ch-f", "ch-row2", "ch-f", "ch-f", "ch-inc", "ch-mailwrap", "ch-pol", "ch-acts"])
        self.assertEqual(self.subject(), "[ABC] Reminder: Share the UAT plan")
        m = self.mail()
        self.assertRegex(m, r"^Good (morning|afternoon|evening), Sara,")
        self.assertIn("A quick reminder about the item below, which is now past its due date.", m)     # singular (Alan, 13-10-2026)
        self.assertIn("Could you let me know where it stands", m)
        self.assertIn("Thursday 15-10-2026", m)
        self.assertIn("Latest update: Plan in draft", m)
        self.assertIn("4 days overdue", m)
        self.assertEqual(b.eval("(()=>{ const s=[...document.querySelectorAll('#chMail span')].find(x=>x.textContent==='4 days overdue');"
                                " return getComputedStyle(s).color+' '+getComputedStyle(s).fontWeight; })()"), "rgb(179, 38, 30) 700")
        self.assertTrue(m.rstrip().endswith("Kind regards,\nAlan"))
        self.assertNotIn("vip", self.pane_text().lower())

    def test_the_preview_follows_the_tone_the_date_and_the_latest_update(self):
        b = self.b
        self.chase(self.theirs)
        b.click('[data-tone="2"]')
        b.wait("document.getElementById('chSubj').textContent.includes('Overdue, reply needed')")
        self.assertEqual(b.eval("[...document.querySelectorAll('[data-tone]')].map(x=>x.getAttribute('aria-pressed'))"), ["false", "false", "true"])
        self.assertIn("This item is now well overdue", self.mail())
        b.eval("(()=>{ const i=document.getElementById('chReplyBy'); i.value='2026-10-20'; i.dispatchEvent(new Event('input',{bubbles:true})); })()")
        self.until_mail("Tuesday 20-10-2026")
        b.click("#chIncUpd")
        b.wait("!document.getElementById('chMail').innerText.includes('Latest update')")

    def test_alans_own_item_asks_for_help_and_he_picks_who(self):
        b = self.b
        self.chase(self.mine)
        p = self.pane_text()
        self.assertIn("Yours", p)
        self.assertIn("This action is yours, so this asks for help rather than chasing.", p)
        self.assertEqual(b.eval("document.querySelector('.ch-chip').textContent"), "Dana Okoye")
        sugg = b.eval("[...document.querySelectorAll('.ch-sugg button')].map(x=>x.textContent)")
        self.assertEqual(sugg[:3], ["Dana Okoye named in the item", "Tom Reid named in the item", "Sara Example at the meeting"])
        self.assertIn("Jane Doe project stakeholder", sugg)
        self.assertEqual(sugg[-1], "+ Anyone")
        self.assertEqual(self.subject(), "[ABC] Your help with back-to-back commercials")
        m = self.mail()
        self.assertIn("I've been asked to follow up with you on the back-to-back commercials, to get", m)
        self.assertIn(f"The action is with me ({self.mine}), and I need your help to close it.", m)
        self.assertIn("What I need from you:", m)
        self.assertIn("Owner: Alan Carter", m)
        self.assertIn("If someone else is better placed to help, a name would be just as useful.", m)
        self.assertTrue(m.rstrip().endswith("Thank you,\nAlan"))
        # the outcome and the need are his words, and the preview follows them as he types
        b.click("#chNeed")
        b.eval("document.getElementById('chNeed').select()")
        b.type("Your sign-off on the terms.")
        self.until_mail("What I need from you: Your sign-off on the terms.")
        b.click("#chOutcome")
        b.eval("document.getElementById('chOutcome').select()")
        b.type("the Northgate commercials agreed")
        self.until_mail("to get the Northgate commercials agreed.")
        self.assertEqual(b.eval("getComputedStyle([...document.querySelectorAll('#chMail p')].find(x=>x.textContent.startsWith('What I need')))"
                                ".backgroundColor"), "rgb(247, 243, 227)")
        # a suggestion, then anyone from the register
        b.eval("[...document.querySelectorAll('.ch-sugg button')].find(x=>x.textContent.startsWith('Tom')).click()")
        b.wait("document.querySelector('.ch-chip').textContent==='Tom Reid'")
        self.until_mail(", Tom,")
        self.assertIn("tom.r@example.com", self.pane_text())
        self.assertEqual(b.eval("[...document.querySelectorAll('.ch-sugg button')].find(x=>x.textContent.startsWith('Tom')).getAttribute('aria-pressed')"), "true")
        b.eval("[...document.querySelectorAll('.ch-sugg button')].find(x=>x.textContent==='+ Anyone').click()")
        b.wait("document.getElementById('chAnyone')")
        people = b.eval("[...document.querySelectorAll('#chAnyone button')].map(x=>x.textContent)")
        self.assertFalse(any(x.startswith("Alan Carter") or x.startswith("Quiet Person") for x in people), people)
        b.click("#chAnyone input")
        b.type("omar")
        b.wait("[...document.querySelectorAll('#chAnyone button')].length===1")
        b.click("#chAnyone button")
        b.wait("document.querySelector('.ch-chip').textContent==='Omar Ali'")
        self.until_mail(", Omar,")
        self.assertNotIn("vip", self.pane_text().lower())

    def test_a_pending_decision_asks_its_decision_maker(self):
        b = self.b
        self.chase(self.decision, "decisions")
        self.assertEqual(b.eval("document.querySelector('.ch-mode .tag').textContent"), "Decision")
        self.assertEqual(b.eval("document.querySelector('.ch-mode b').textContent"), "Asking Jane for the decision")
        self.assertEqual(b.eval("document.querySelector('.ch-chip').textContent"), "Jane Doe")
        self.assertEqual(self.subject(), "[ABC] Decision needed: Which use cases go into phase 2")
        m = self.mail()
        self.assertIn("Decision needed: Which use cases go into phase 2", m)
        self.assertIn("Needed by", m)
        self.assertIn("Could you let me have the decision, or tell me what you need to make it, by Thursday 15-10-2026?", m)
        self.assertTrue(m.rstrip().endswith("Thank you,\nAlan"))
        b.click('[data-tone="1"]')
        b.wait("document.getElementById('chSubj').textContent.startsWith('[ABC] Second reminder: decision needed')")
        self.assertNotIn("vip", self.pane_text().lower())                              # Jane is a VIP in the register: never said

    def test_the_email_keeps_its_own_colours_in_the_dark_theme(self):
        b = self.b
        b.eval("document.documentElement.setAttribute('data-theme','dark')")
        self.chase(self.theirs)
        o = b.eval("(()=>{ const m=document.getElementById('chMail'), p=m.querySelector('p'); return {bg:getComputedStyle(m).backgroundColor,"
                   " ink:getComputedStyle(p).color, font:getComputedStyle(p).fontFamily, pane:getComputedStyle(document.querySelector('.ch-mode')).backgroundColor}; })()")
        self.assertEqual((o["bg"], o["ink"]), ("rgb(255, 255, 255)", "rgb(30, 31, 30)"))
        self.assertIn("Calibri", o["font"])
        self.assertNotEqual(o["pane"], "rgb(238, 241, 243)", "the pane itself follows the theme")


class Copying(ChaseCase):
    shared_server = True

    def test_copy_for_outlook_puts_styled_html_and_the_plain_text_on_the_clipboard(self):
        b = self.b
        self.chase(self.theirs)
        b.eval(CLIPBOARD)
        b.click("#chCopyHtml")
        b.wait("CLIP.length===1")
        clip = b.eval("CLIP[0]")
        self.assertEqual(sorted(clip), ["text/html", "text/plain"])
        o = b.eval("""(()=>{ const d=new DOMParser().parseFromString(CLIP[0]['text/html'],'text/html'),
          all=[...d.body.querySelectorAll('*')].filter(e=>e.tagName!=='TBODY');
          return {noStyle:all.filter(e=>!e.getAttribute('style')&&e.tagName!=='BR').map(e=>e.tagName),
            classes:all.filter(e=>e.hasAttribute('class')||e.hasAttribute('id')).length,
            vars:/var\\(|flex|grid|<img|<style|class=/i.test(CLIP[0]['text/html']), table:d.querySelector('table').getAttribute('cellpadding'),
            border:d.querySelector('table').getAttribute('border'), text:d.body.textContent}; })()""")
        self.assertEqual((o["noStyle"], o["classes"], o["vars"]), ([], 0, False))   # Outlook-plain, like the Draft email
        self.assertEqual((o["table"], o["border"]), ("6", "0"))
        self.assertIn("A quick reminder about the item below", o["text"])
        self.assertIn("A quick reminder about the item below", clip["text/plain"])
        self.assertIn("Share the UAT plan", clip["text/plain"])
        self.assertEqual(b.eval("document.querySelector('.ch-said').textContent"), "Copied. Paste into a new Outlook email.")
        self.assertFalse((self.v.root / "system/staging/chases.json").exists(), "copying records nothing")

    def test_copy_as_text_gives_the_subject_and_the_email(self):
        b = self.b
        self.chase(self.theirs)
        b.eval(CLIPBOARD)
        b.click("#chCopyText")
        b.wait("CLIP.length===1")
        text = b.eval("CLIP[0]['text/plain']")
        self.assertTrue(text.startswith("[ABC] Reminder: Share the UAT plan\n\nGood "), text[:80])
        self.assertIn("  |  High", text)
        self.assertEqual(b.eval("document.querySelector('.ch-said').textContent"), "Copied as plain text.")

    def test_a_refused_clipboard_selects_the_email_and_says_so(self):
        b = self.b
        self.chase(self.theirs)
        b.eval("Object.defineProperty(navigator,'clipboard',{configurable:true,value:{write:()=>Promise.reject(new Error('no')),writeText:()=>Promise.reject(new Error('no'))}})")
        b.click("#chCopyHtml")
        b.wait("document.querySelector('.ch-said.fail')")
        self.assertIn("the email is selected", b.eval("document.querySelector('.ch-said').textContent"))
        self.assertIn("A quick reminder", b.eval("String(getSelection())"))


    def test_polish_follows_the_ai_drafts_switch(self):
        b = self.b
        self.chase(self.theirs)
        b.eval("S.drafting={...(S.drafting||{}),email:false}")
        b.click("#chPolish")
        b.wait("document.querySelector('.ch-said.fail')")
        self.assertIn("is off in Settings › Advanced › AI drafts", b.eval("document.querySelector('.ch-said').textContent"))
        self.assertIn("A quick reminder", self.mail(), "the drafted opening stays")


class Polish(ChaseCase):
    """Polish in the pane (Alan, 13-10-2026, option A; dev/mockups/draft-chase-polish-mockup.html), against a stand-in Claude
    (drafts_fake.py): one row under the email in the pane's own Tone, Yours beside Polished, nothing changed until Use this."""
    shared_server = True

    @classmethod
    def load(cls, v):
        super().load(v)
        cls.fake = drafts_fake.install(v)

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": NOW, "CREAITE_CLAUDE": str(cls.fake)}

    def stat(self, event, n):
        p = self.v.root / "system/staging/draft-stats.json"
        for _ in range(50):
            if p.exists() and (json.loads(p.read_text()).get("email") or {}).get(event, 0) >= n:
                return
            time.sleep(0.1)
        self.fail(f"email {event} not counted {n}: {p.read_text() if p.exists() else 'no stats'}")

    def polish(self):
        self.b.click("#chPolish")
        self.b.wait("document.querySelector('#pkChase .ch-card')", timeout=30)

    def test_one_row_under_the_email_in_the_panes_own_tone(self):
        b = self.b
        self.chase(self.theirs)
        self.assertEqual(b.eval("document.querySelector('#pkChase .ch-pol .sub').textContent"),
                         "Reword the opening paragraph in the First tone. The table, subject and addresses stay as they are.")
        self.assertEqual(b.eval("document.getElementById('chPolish').textContent"), "Polish the wording")
        order = "(a,c)=>!!(document.querySelector(a).compareDocumentPosition(document.querySelector(c))&Node.DOCUMENT_POSITION_FOLLOWING)"
        self.assertTrue(b.eval(f"({order})('#pkChase .ch-mailwrap','#pkChase .ch-pol')"), "under the email")
        self.assertTrue(b.eval(f"({order})('#pkChase .ch-pol','#chCopyHtml')"), "above the buttons")
        self.assertEqual(b.eval("document.querySelectorAll('#pkChase [data-detone]').length"), 0)     # no Warm, Neutral, Firm chips
        b.click('#pkChase [data-tone="2"]')
        b.wait("document.querySelector('#pkChase .ch-pol .sub').textContent.includes('Firmer tone')")
        self.chase(self.mine)
        self.assertEqual(b.eval("document.querySelector('#pkChase .ch-pol .sub').textContent"),
                         "Reword the opening, and suggest the two lines above, in the First tone.")

    def test_ai_drafts_off_greys_the_button_and_says_why(self):
        b = self.b
        try:
            b.eval("S.drafting={...(S.drafting||{}),email:false}")
            self.chase(self.theirs)
            self.assertEqual(b.eval("document.getElementById('chPolish').getAttribute('aria-disabled')"), "true")
            self.assertIn("is off in Settings › Advanced › AI drafts", b.eval("document.getElementById('chPolWhy').textContent"))
            b.click("#chPolish")
            b.pump(0.3)
            self.assertIsNone(b.eval("document.querySelector('#pkChase .ch-card,#pkChase .drstatus')"))
            self.assertIn("A quick reminder", self.mail(), "the drafted opening stays")
        finally:
            b.eval("S.drafting={...(S.drafting||{}),email:true}")

    def test_someone_elses_item_rewords_the_opening_only_and_use_this_puts_it_in(self):
        b = self.b
        self.chase(self.theirs)
        self.polish()
        p = drafts_fake.prompt(self.fake)
        self.assertTrue(p.startswith("Polish the cover paragraph"), p[:80])
        self.assertIn("in a warm tone", p)                                   # First → warm
        self.assertIn("A quick reminder about the item below", p)
        for never in ("Share the UAT plan", "sara", "[ABC]", "09-10-2026"):
            self.assertNotIn(never, p)                                       # the table, subject and addresses never go to the model
        self.assertEqual(b.eval("[...document.querySelectorAll('#pkChase .ch-cmp')].map(x=>x.dataset.part)"), ["opening"])
        self.assertIn("Nothing changes until you press Use this.", b.eval("document.querySelector('#pkChase .ch-card').textContent"))
        self.assertIn("A quick reminder", self.mail(), "nothing changes until Use this")
        self.assertIsNone(b.eval("document.getElementById('chPolished')"))
        b.click("#chUseThis")
        self.until_mail("A gentle nudge on the items below")
        self.assertIn(self.theirs, self.mail(), "the table stays")
        self.assertEqual(b.eval("document.getElementById('chPolished').textContent"), "Polished")
        self.assertTrue(self.subject().startswith("[ABC] Reminder"), "the subject stays")
        self.assertEqual(b.eval("document.getElementById('chPolish').textContent"), "Polish again")
        self.stat("used", 1)
        # the tone changes: the polished wording goes, and says so
        b.click('#pkChase [data-tone="1"]')
        self.until_mail("I'm following up on my earlier note")
        self.assertEqual(b.eval("document.querySelector('.ch-said').textContent"),
                         "Tone changed, so the polished wording was dropped. Polish again if you want it.")
        self.assertIsNone(b.eval("document.getElementById('chPolished')"))
        # Keep mine changes nothing and counts a rejection
        self.polish()
        self.assertIn("in a neutral tone", drafts_fake.prompt(self.fake))  # Second → neutral
        b.click("#chKeepMine")
        b.wait("!document.querySelector('#pkChase .ch-card')")
        self.assertIn("I'm following up on my earlier note", self.mail())
        self.stat("rejected", 1)

    def test_alans_own_item_suggests_the_two_lines_and_editing_one_drops_it(self):
        b = self.b
        self.chase(self.mine)
        b.eval("(e=>{ e.value='the commercials agreed'; e.dispatchEvent(new Event('input',{bubbles:true})); })(document.getElementById('chOutcome'))")
        self.until_mail("to get the commercials agreed")
        self.polish()
        p = drafts_fake.prompt(self.fake)
        self.assertTrue(p.startswith("Polish the opening of a request for help"), p[:80])
        self.assertIn("To get … done, as Alan has it: the commercials agreed", p)
        self.assertIn("Reach out to Dana on back-to-back commercials", p)
        for never in ("[ABC]", "dana.o@example.com", "Your help with", "Could you let me know by"):
            self.assertNotIn(never, p)
        self.assertEqual(b.eval("[...document.querySelectorAll('#pkChase .ch-cmp')].map(x=>x.dataset.part)"), ["opening", "outcome", "need"])
        self.assertIn("the Northgate commercials agreed on the Kestrel Group terms", b.eval("document.querySelector('#pkChase [data-part=outcome] .new').textContent"))
        self.assertEqual(b.eval("document.getElementById('chOutcome').value"), "the commercials agreed", "nothing changes until Use this")
        b.click("#chUseThis")
        self.until_mail("I'm picking up the back-to-back commercials and need your input to close them.")
        self.assertEqual(b.eval("document.getElementById('chOutcome').value"), "the Northgate commercials agreed on the Kestrel Group terms")
        self.assertEqual(b.eval("document.getElementById('chNeed').value"), "Tell me whether the Northgate terms can mirror the Kestrel Group contract.")
        self.assertIn("What I need from you: Tell me whether the Northgate terms can mirror the Kestrel Group contract.", self.mail())
        self.assertEqual(b.eval("document.getElementById('chPolished').textContent"), "Polished")
        # editing To get … done drops the polished opening; the email goes back to the standard wording with his words
        b.eval("(e=>{ e.value='the terms signed'; e.dispatchEvent(new Event('input',{bubbles:true})); })(document.getElementById('chOutcome'))")
        self.until_mail("to get the terms signed")
        self.assertNotIn("I'm picking up", self.mail())
        self.assertIsNone(b.eval("document.getElementById('chPolished')"))
        self.assertEqual(b.errors, [])


class ISentIt(ChaseCase):
    """v2.3.0 #153: I sent it records the chase (chases.json), stages a dated Latest update and returns to the item. The staging,
    the Undo and the wording are tested in test_sent_it_person_menu.py; here only the record and the step up."""
    shared_server = True

    def test_it_records_the_chase_and_the_next_one_steps_up(self):
        b = self.b
        self.chase(self.theirs)
        b.click("#chSent")
        b.wait("document.getElementById('pkChase').hidden")                          # back on the open item
        recs = json.loads((self.v.root / "system/staging/chases.json").read_text())["chases"]
        self.assertEqual([(r["ids"], r["mode"]) for r in recs], [([self.theirs], "chase")])
        self.assertEqual(sorted(recs[0]), ["date", "ids", "mode"])                    # references only, never text
        self.assertEqual(b.eval(f"SA().chases[{self.theirs!r}].n"), 1)
        self.assertTrue(b.eval("!document.getElementById('pkScroll').hidden"))
        b.click("#pkChaseBtn")
        b.wait("document.getElementById('chSubj')&&document.getElementById('chSubj').textContent.startsWith('[ABC] Second reminder')")
        self.assertEqual(b.eval("[...document.querySelectorAll('[data-tone]')].map(x=>x.getAttribute('aria-pressed'))"), ["false", "true", "false"])
        # Alan's own item is recorded as help
        self.chase(self.mine)
        b.click("#chSent")
        b.wait("document.getElementById('pkChase').hidden")
        recs = json.loads((self.v.root / "system/staging/chases.json").read_text())["chases"]
        self.assertEqual((recs[-1]["ids"], recs[-1]["mode"]), ([self.mine], "help"))
        self.assertTrue(re.fullmatch(r"\d{4}-\d{2}-\d{2}", recs[-1]["date"]))


if __name__ == "__main__":
    unittest.main()
