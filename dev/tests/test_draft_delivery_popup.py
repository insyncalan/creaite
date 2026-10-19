"""#183 (2.6): Draft email delivery in the page: the Draft email popup with Create drafts in Outlook off and on, and the
Settings › Essentials › Draft email card with its Outlook access Check. At 1400 and 900 wide.

Run: python3 dev/tests/test_draft_delivery_popup.py   (needs Google Chrome; skipped otherwise)
The real live server in a throwaway vault with fictional data. The draft route (POST /api/email/draft) and the access route are
Jarvis's guarded live_server.py change (dev/proposals/draft-delivery/), so the page's api is stood in for on those two paths only:
nothing reaches Microsoft 365 and nothing is ever sent.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_drafts_email import EmailCase  # noqa: E402

LINK = "https://outlook.office365.com/owa/?ItemID=AAMk1"
OFF_SUB = "Nothing is sent: copy it and paste it into Outlook"
ON_SUB = "Nothing is sent: creaite puts a draft in your Outlook Drafts folder, for you to check and send"
HELP = ("Off: creaite builds the email and you copy and paste it into Outlook. On: creaite puts it in your Outlook Drafts folder, "
        "ready for you to check and send. It never sends anything. Turn it off if you can't write to Outlook.")


def stub_routes(b, draft, access=None):
    """Answer /api/email/draft (noting each body) and /api/email/outlook-access in this page; every other call goes to the server."""
    b.eval(f"""(()=>{{ const real=window.__realApi||window.api; window.__realApi=real; window.__dd=[];
      window.api=async(p,body)=>{{ if(p==='/api/email/draft'){{ __dd.push(JSON.parse(JSON.stringify(body))); return {json.dumps(draft)}; }}
        if(p==='/api/email/outlook-access') return {json.dumps(access or {"ok": True, "can": True, "at": "10:42"})};
        return real(p,body); }}; }})()""")


class PopupCase(EmailCase):
    def setUp(self):
        super().setUp()
        self.b.eval("window.__clip=[]; navigator.clipboard.write=async items=>{ for(const it of items) __clip.push(await (await it.getType('text/html')).text()); };"
                    "navigator.clipboard.writeText=async t=>{ __clip.push(t); };")

    def outlook(self, on):
        self.b.eval(f"S.outlookDrafts={'true' if on else 'false'}")

    def open_chase(self):
        b = self.b
        b.eval("openDraftEmail('Sara Example','chase')")
        b.wait("document.getElementById('deDlg')&&document.getElementById('deDlg').open")
        b.eval("document.querySelectorAll('#deInc [data-deit]').forEach(i=>{ if(!i.checked) i.click(); })")

    def buttons(self):
        return self.b.eval("[...document.querySelectorAll('#deActs button')].map(x=>x.textContent.trim())")

    def fits(self):
        """The popup's content never scrolls sideways at this width."""
        self.assertTrue(self.b.eval("(()=>{ const d=document.getElementById('deDlg'); return d.scrollWidth<=d.clientWidth+1; })()"))
        self.assertTrue(self.b.eval("document.documentElement.scrollWidth<=innerWidth"))


class Popup(PopupCase):
    def test_off_is_todays_popup(self):
        b = self.b
        self.assertFalse(b.eval("S.outlookDrafts===true"))                 # off by default: the vault's settings have no switch on
        self.open_chase()
        self.assertEqual(b.eval("document.getElementById('deSub').textContent"), OFF_SUB)
        self.assertEqual(self.buttons(), ["Copy email", "Copy as plain text", "I sent it", "Close"])
        self.assertEqual(b.eval("document.querySelector('#deActs .primary').id"), "deCopyHtml")
        self.assertIn("Press I sent it after you send it", b.eval("document.querySelector('.dechase').textContent"))
        self.assertTrue(b.eval("document.getElementById('deStat').hidden"))
        self.fits()
        self.assertEqual(b.errors, [])

    def test_on_offers_create_draft_first_keeps_the_copies_and_drops_i_sent_it(self):
        b = self.b
        self.outlook(True)
        self.open_chase()
        self.assertEqual(b.eval("document.getElementById('deSub').textContent"), ON_SUB)
        self.assertEqual(self.buttons(), ["Create draft in Outlook", "Copy email", "Copy as plain text", "Close"])
        self.assertEqual(b.eval("document.querySelector('#deActs .primary').id"), "deMake")
        self.assertFalse(b.eval("!!document.getElementById('deSent')"))
        self.assertIn("The reminder steps up when the draft is created", b.eval("document.querySelector('.dechase').textContent"))
        self.fits()

    def test_the_draft_body_is_the_previews_html_and_the_copys_html(self):
        b = self.b
        self.outlook(True)
        self.open_chase()
        stub_routes(b, {"ok": True, "web_link": LINK, "chased": ["ABC-A-006"], "no_recipient": True})
        b.click("#deCopyHtml")
        b.wait("__clip.length===1")
        b.click("#deMake")
        b.wait("!!document.getElementById('deMade')")
        sent = b.eval("__dd.find(x=>x.action==='create')")
        self.assertEqual(sent["html"], b.eval("deHtml()"))
        self.assertEqual(sent["html"], b.eval("__clip[0]"))                 # what is on screen is what lands in Outlook
        self.assertIn("<table", sent["html"])
        self.assertEqual(sent["subject"], b.eval("document.getElementById('deSubj').value"))
        self.assertEqual((sent["to"], sent["mode"]), ("sara.example@client.com", "chase"))
        self.assertIn("ABC-A-006", sent["ids"])

    def test_after_the_draft_is_made_the_button_reads_draft_created_and_the_chase_is_recorded(self):
        b = self.b
        self.outlook(True)
        self.open_chase()
        stub_routes(b, {"ok": True, "web_link": LINK, "chased": ["ABC-A-006"], "no_recipient": False,
                        "chases": {"ABC-A-006": {"n": 1, "last": "2026-10-19"}}})
        b.click("#deMake")
        b.wait("!!document.getElementById('deMade')")
        self.assertEqual(self.buttons()[0], "Draft created")
        self.assertTrue(b.eval("document.getElementById('deMade').disabled"))
        stat = b.eval("document.getElementById('deStat').textContent")
        self.assertIn("Draft created in Outlook (your Drafts folder). Open it there to check and send. Open in Outlook", stat)
        self.assertIn("Chase recorded: drafted today, 1 item.", stat)
        self.assertEqual(b.eval("document.querySelector('#deStat a').href"), LINK)
        self.assertEqual(b.eval("SA().chases['ABC-A-006'].n"), 1)            # recorded without I sent it
        self.assertEqual(b.eval("__dd.filter(x=>x.action==='create').length"), 1)

    def test_a_refusal_keeps_the_email_records_nothing_and_offers_copy_it_instead(self):
        b = self.b
        self.outlook(True)
        self.open_chase()
        before = b.eval("deHtml()")
        stub_routes(b, {"ok": False, "reason": "you don't have permission to write to this mailbox"})
        b.click("#deMake")
        b.wait("!document.getElementById('deStat').hidden")
        self.assertEqual(b.eval("document.getElementById('deStat').textContent"),
                         "Outlook would not create the draft (you don't have permission to write to this mailbox). Nothing was sent and "
                         "nothing was recorded. The email is still here: Copy it instead or turn the setting off in Settings › Essentials › "
                         "Draft email.")
        self.assertTrue(b.eval("document.getElementById('deDlg').open"))
        self.assertEqual(b.eval("deHtml()"), before)
        self.assertFalse(b.eval("document.getElementById('deMake').disabled"))
        self.assertIsNone(self.chases_file())
        b.click("#deFallback")
        b.wait("__clip.length===1")
        self.assertEqual(b.eval("__clip[0]"), before)

    def test_no_address_on_record_says_so_and_still_offers_the_draft(self):
        b = self.b
        b.eval("(()=>{ const x=PERS().find(y=>y.name==='Sara Example'); if(x.p) x.p.email=''; })()")   # no address on record
        self.open_chase()
        self.assertEqual(b.eval("document.getElementById('deTo').textContent"),
                         "No email address on record for Sara Example. Add the address when you paste it into Outlook.")
        b.eval("document.getElementById('deDlg').close()")
        self.outlook(True)
        self.open_chase()
        self.assertEqual(b.eval("document.getElementById('deTo').textContent"),
                         "No email address on record for Sara Example. The draft is still created, with nothing in To: add the "
                         "address in Outlook.")
        stub_routes(b, {"ok": True, "web_link": LINK, "chased": ["ABC-A-006"], "no_recipient": True})
        b.click("#deMake")
        b.wait("!!document.getElementById('deMade')")
        self.assertEqual(b.eval("__dd[0].to"), "")
        self.assertIn("It has no recipient yet: add the address in Outlook.", b.eval("document.getElementById('deStat').textContent"))

    def test_a_copy_with_the_setting_on_leaves_the_references_for_the_sweep(self):
        b = self.b
        self.outlook(True)
        self.open_chase()
        stub_routes(b, {"ok": True})
        b.click("#deCopyText")
        b.wait("__dd.length===1")
        self.assertEqual(b.eval("__dd[0].action"), "copied")
        self.outlook(False)
        b.eval("document.getElementById('deDlg').close()")
        self.open_chase()
        stub_routes(b, {"ok": True})
        b.click("#deCopyText")
        b.wait("__clip.length>=2")
        self.assertEqual(b.eval("__dd.length"), 0)                          # off: a copy writes nothing, as today


class Popup900(Popup):
    width = 900


class EssentialsCard(PopupCase):
    def open_settings(self):
        b = self.b
        b.eval("go('settings','essentials')")
        b.wait("!!document.querySelector('#set-essentials [data-ess=\"Draft email\"] .srow')")

    def test_the_draft_email_card_is_second_with_its_words_and_off(self):
        b = self.b
        self.open_settings()
        self.assertEqual(b.eval("[...document.querySelectorAll('#set-essentials [data-ess] h2')].map(h=>h.textContent)")[:3],
                         ["You", "Draft email", "Your day"])
        row = "document.querySelector('[data-keys=\"draft_email.outlook_drafts\"]')"
        self.assertEqual(b.eval(f"{row}.querySelector('span[id]').textContent"), "Create drafts in Outlook")
        self.assertEqual(b.eval(f"{row}.querySelector('small').textContent"), HELP)
        self.assertFalse(b.eval(f"{row}.querySelector('input[type=checkbox]').checked"))
        self.assertEqual(b.eval("document.querySelector('#ddAcc span[id]').textContent"), "Outlook access")
        self.assertEqual(b.eval("document.getElementById('ddCheck').textContent"), "Check")

    def test_check_says_yes_with_the_time_or_no_and_turns_the_setting_off(self):
        b = self.b
        self.open_settings()
        box = "document.querySelector('[data-keys=\"draft_email.outlook_drafts\"] input')"
        b.eval(f"{box}.click()")
        b.wait("S.outlookDrafts===true")
        stub_routes(b, {"ok": True}, {"ok": True, "can": True, "at": "10:42"})
        b.click("#ddCheck")
        b.wait("document.getElementById('ddRes').textContent.includes('checked')")
        self.assertEqual(b.eval("document.getElementById('ddRes').textContent"), "You can create drafts in Outlook (checked 10:42).")
        stub_routes(b, {"ok": True}, {"ok": True, "can": False, "at": "10:43"})
        b.click("#ddCheck")
        b.wait("S.outlookDrafts===false")
        self.assertEqual(b.eval("document.getElementById('ddRes').textContent"),
                         "Outlook says you can't write here, so drafts stay copy and paste.")
        settings = json.loads((self.v.root / "system/config/settings.json").read_text())
        self.assertIs(settings["draft_email"]["outlook_drafts"], False)


class EssentialsCard900(EssentialsCard):
    width = 900


if __name__ == "__main__":
    unittest.main()
