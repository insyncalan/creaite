"""v2.6.1 minutes view: gaps left when test_v210 c52, c54, c55 and c56 were retired (#268), in a real browser on the real live
server (LiveBrowserCase; no Claude runs). Fictional demo data only (the steering committee of test_minutes_editor).

- Leak: an item marked Sensitive never reaches the follow-up email: not in the draft the Export menu opens (the Internal version,
  the only one the menu offers since #268), and not in the Distributed version the server can build (`/api/minutes/followup`
  with version "distributed", `minutes_record.followup_facts`). Nothing is sent.
- Deadline popover: the four quick picks show the exact dates worked out from the meeting's day (Friday, next week, next
  Wednesday, end of month; computed here in plain Python by date_words, not by the page); words that can't be read say so and
  set nothing.
- Popups: the deadline popover, a check and the approve popup close on Esc and on a click outside, focus goes back to the
  button that opened them, and Esc goes no further (the view stays and the typed words are not lost).
- An owner who isn't in the people register: since #266 the row and the approve popup say "Pat Unknown needs details"
  (the retired c55 wording "isn't in the people register" is gone from the product).

Run: python3 dev/tests/test_minutes_view_v261.py      (Chrome tier; skipped without Chrome)
"""
import json
import subprocess
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402
import test_minutes_editor as me  # noqa: E402
import date_words  # noqa: E402

ROW = "#v-minutes tr.mi[data-n='%d']"
SECRET_DECISION = "The pilot stays on the lighthouse site"
SECRET_ACTION = "Book the UAT test environment"
OPEN_ACTION = "Send the revised SOW to the client"


def dmy(iso):
    return date.fromisoformat(iso).strftime("%d-%m-%Y")


class MinutesViewV261(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        populate(v)
        cls.proposal = me.stage_meeting(v)
        p = v.root / "system/staging" / cls.proposal
        data = json.loads(p.read_text(encoding="utf-8"))
        for i in data["items"]:                                   # a Sensitive decision and a Sensitive action
            if i["n"] in (2, 4):
                i["flags"] = ["sensitive"]
        p.write_text(json.dumps(data), encoding="utf-8")
        subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, 'system/scripts'); import minutes_record; "
                        f"minutes_record.change({me.DRAFT!r}, {{'op': 'deadline', 'n': 1, 'words': 'Friday'}})"],
                       cwd=v.root, capture_output=True, text=True, check=True)       # any change re-reads the staged items

    def setUp(self):
        super().setUp()
        self.b.eval(f"go('minutes',{{file:{json.dumps(self.proposal)}}})")
        self.b.wait("document.querySelector('#v-minutes tr.mi')", 15)
        self.b.pump(0.3)

    def ev(self, js):
        return self.b.eval(js)

    def facts(self, version):
        r = subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts'); import minutes_record; "
                            f"print(json.dumps(minutes_record.followup_facts({me.DRAFT!r}, {version!r})))"],
                           cwd=self.v.root, capture_output=True, text=True, check=True)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def staged(self, n):
        data = json.loads((self.v.root / "system/staging" / self.proposal).read_text(encoding="utf-8"))
        return next(i for i in data["items"] if i["n"] == n)

    def wait_saved(self, js):
        self.b.wait(js, 15)
        self.b.pump(0.3)

    def click_outside(self):
        self.b.click("#v-minutes .sheet-zv")
        self.b.pump(0.2)

    # ── 1. leak: a Sensitive item stays out of the follow-up email ──
    def test_01_the_sensitive_items_are_marked_in_the_record(self):
        self.assertEqual(self.ev("document.querySelectorAll('#v-minutes .mnsens').length"), 2, "the two marked rows carry the tag")

    def open_followup(self, label):
        b = self.b
        b.click("#v-minutes [data-mnexport]")
        b.wait("document.querySelector('#v-minutes .ddmenu.on')")
        b.eval("[...document.querySelectorAll('#v-minutes .ddmenu.on [role=menuitem]')].find(x=>x.textContent.includes(%s)).click()" % json.dumps(label))
        b.wait("document.getElementById('deDlg') && document.getElementById('deDlg').open && document.querySelector('#dePrev').textContent.length>20", 15)
        b.pump(0.4)
        return (self.ev("document.getElementById('deDlg').textContent + ' ' + document.querySelector('#deSubj').value"),
                self.ev("document.querySelector('#deSubj').value"))

    def test_02_the_default_follow_up_email_is_the_distributed_version_with_no_sensitive_item(self):
        whole, subject = self.open_followup("Draft the follow-up email")
        self.assertNotIn("[Internal]", subject, "the default is not the Internal version")
        self.assertNotIn(SECRET_DECISION, whole, "a Sensitive decision never reaches the default draft")
        self.assertNotIn(SECRET_ACTION, whole, "a Sensitive action never reaches the default draft")
        self.assertIn(OPEN_ACTION, whole, "the unmarked action is there (the draft is not empty)")
        self.assertEqual(self.ev("DE.version"), "distributed")

    def test_02b_the_internal_follow_up_is_a_deliberate_choice_marked_internal_with_sensitive_items_unticked(self):
        whole, subject = self.open_followup("Draft an Internal follow-up email")
        self.assertIn("[Internal]", subject, "the Internal follow-up is marked [Internal]")
        self.assertIn(SECRET_DECISION, whole, "Internal keeps a Sensitive decision, by design (offered)")
        self.assertIn(SECRET_ACTION, whole, "Internal keeps a Sensitive action, by design (offered)")
        picked = self.ev("DE.items.filter(i=>DE.picked.has(i.k+':'+i.id)).map(i=>i.t)")
        self.assertNotIn(SECRET_DECISION, picked, "nothing Sensitive starts ticked")
        self.assertNotIn(SECRET_ACTION, picked, "nothing Sensitive starts ticked")
        self.assertIn(OPEN_ACTION, picked)

    def test_02c_deBarred_honours_sensitive_even_when_client_visible(self):
        self.assertTrue(self.ev("deBarred({t:'x',client:true,sens:true,src:''})"))
        self.assertFalse(self.ev("deBarred({t:'x',client:true,sens:false,src:''})"))
        self.assertFalse(self.ev("deBarred({t:'x',sens:true,src:''},false)"), "an own-domain address (the update email) may keep it")

    def test_03_the_server_builds_internal_with_both_and_distributed_with_neither(self):
        """Internal (marked internal) keeps both Sensitive items by design; only Distributed withholds: the leak guard."""
        for version in ("internal", "distributed"):
            with self.subTest(version=version):
                f = self.facts(version)
                words = [i["t"] for i in f["items"]]
                self.assertIn(OPEN_ACTION, words, f"{version}: the unmarked action")
                if version == "internal":
                    self.assertTrue(f["marked_internal"], "internal: marked internal")
                    self.assertIn(SECRET_DECISION, words, "internal: a Sensitive decision is kept")
                    self.assertIn(SECRET_ACTION, words, "internal: a Sensitive action is kept")
                else:
                    self.assertFalse(f["marked_internal"])
                    text = json.dumps(f, ensure_ascii=False)
                    self.assertNotIn(SECRET_DECISION, text, "distributed: a Sensitive decision")
                    self.assertNotIn(SECRET_ACTION, text, "distributed: a Sensitive action")

    # ── 2. deadline popover ──
    def test_04_quick_picks_show_their_exact_dates_and_unreadable_words_say_so(self):
        b = self.b
        day = me.DAY
        sel = ROW % 3 + " .mndue"
        want = {"Friday": date_words.deadline("Friday", day), "Next week": date_words.deadline("next week", day),
                "Next Wednesday": date_words.deadline("next wednesday", day), "End of month": date_words.deadline("end of month", day)}
        self.assertTrue(all(want.values()), want)
        b.click(sel)
        b.wait("document.querySelector('.mndl')")
        quick = self.ev("[...document.querySelectorAll('.mndl [data-quick]')].map(x=>[x.dataset.quick, x.getAttribute('aria-label')])")
        self.assertEqual([q[0] for q in quick], ["Friday", "next week", "next wednesday", "end of month", "not set"])
        for (word, label), (name, iso) in zip(quick[:4], want.items()):
            self.assertTrue(label.startswith(name + ": "), label)
            self.assertIn(date_words.said(iso).split()[0], label, f"{name}: the weekday")
            self.assertIn(dmy(iso), label, f"{name}: exactly {dmy(iso)}")
        b.click(".mndl [data-quick='next wednesday']")
        self.wait_saved(f"document.querySelector({json.dumps(sel)}).textContent==={json.dumps(dmy(want['Next Wednesday']))}")
        self.assertEqual(self.staged(3)["values"]["due_date"], want["Next Wednesday"], "the staged item moved with the row")
        b.click(sel)
        b.wait("document.querySelector('.mndl')")
        b.click(".mndl [data-quick='end of month']")
        self.wait_saved(f"document.querySelector({json.dumps(sel)}).textContent==={json.dumps(dmy(want['End of month']))}")
        self.assertEqual(self.staged(3)["values"]["due_date"], want["End of month"])
        # words that can't be read say so, and Enter sets nothing
        b.click(sel)
        b.wait("document.querySelector('.mndl')")
        b.eval("document.getElementById('mnDlWords').focus()")
        b.type("whenever it suits")
        b.pump(0.3)
        said = self.ev("document.getElementById('mnDlSaid').textContent")
        self.assertIn("Not a date creaite can read", said)
        self.assertTrue(self.ev("document.getElementById('mnDlSaid').classList.contains('bad')"), "marked as a problem")
        b.key("Enter")
        b.pump(0.5)
        self.assertEqual(self.staged(3)["values"]["due_date"], want["End of month"], "unreadable words set nothing")
        self.assertTrue(self.ev("!!document.querySelector('.mndl')"), "the popover stays open")

    # ── 3. popups close on Esc and on a click outside ──
    def test_05_popups_close_on_esc_and_outside_with_focus_back_and_esc_goes_no_further(self):
        b = self.b
        openers = {"deadline": ROW % 1 + " .mndue", "check": ROW % 2 + " .mnrow2 .mncheck"}
        for name, sel in openers.items():
            for how in ("esc", "outside"):
                with self.subTest(popup=name, close=how):
                    b.click(sel)
                    b.wait("document.querySelector('#v-minutes .mnpop')")
                    self.assertTrue(self.ev("document.querySelector('#v-minutes .mnpop').contains(document.activeElement)"), "focus moves in")
                    hash_before = self.ev("location.hash")
                    if how == "esc":
                        b.key("Escape")
                        b.pump(0.2)
                        self.assertTrue(self.ev(f"document.activeElement===document.querySelector({json.dumps(sel)})"), "focus back on its button")
                    else:
                        self.click_outside()
                    self.assertFalse(self.ev("!!document.querySelector('#v-minutes .mnpop')"), f"{name} closed by {how}")
                    self.assertEqual(self.ev("VIEW"), "minutes", "Esc goes no further: the view stays")
                    self.assertEqual(self.ev("location.hash"), hash_before)
        for how in ("esc", "outside"):
            with self.subTest(popup="approve", close=how):
                b.click("#mnApproveBtn")
                b.wait("document.getElementById('mnApprove').open")
                if how == "esc":
                    b.key("Escape")
                else:
                    x, y = self.ev("(()=>{const r=document.getElementById('mnApprove').getBoundingClientRect(); return [r.left-20, r.top+20]})()")
                    for kind in ("mousePressed", "mouseReleased"):
                        b.call("Input.dispatchMouseEvent", type=kind, x=x, y=y, button="left", clickCount=1)
                b.pump(0.3)
                self.assertFalse(self.ev("document.getElementById('mnApprove').open"))
                self.assertEqual(self.ev("document.activeElement.id"), "mnApproveBtn", "focus back on Approve minutes")
                self.assertEqual(self.ev("VIEW"), "minutes")
                self.assertEqual(self.staged(3)["decision"], "pending", "closing approved nothing")

    def test_06_esc_in_the_deadline_words_closes_only_the_popover(self):
        b = self.b
        sel = ROW % 1 + " .mndue"
        was = self.staged(1)["values"].get("due_date")
        b.click(sel)
        b.wait("document.querySelector('.mndl')")
        b.eval("document.getElementById('mnDlWords').focus()")
        b.type("in 2 weeks")
        b.key("Escape")
        b.pump(0.3)
        self.assertFalse(self.ev("!!document.querySelector('.mndl')"))
        self.assertEqual(self.staged(1)["values"].get("due_date"), was, "Esc sets nothing")
        self.assertEqual(self.ev("VIEW"), "minutes")

    # ── 4. the check's wording for a name the people register doesn't know ──
    def test_07_the_check_says_what_is_wrong_with_the_unknown_owner(self):
        b = self.b
        row = self.ev(f"document.querySelector(\"{ROW % 3} .mnrow2\").textContent")
        self.assertIn("Pat Unknown needs details", row, "the row says what is wrong with the name the register doesn't know")
        self.assertNotIn("Sara Example needs details", self.ev("document.querySelector('#v-minutes .page').textContent"))
        self.assertNotIn("people register", self.ev("document.querySelector('#v-minutes .page').textContent"), "#266's wording, not the old one")
        b.click("#mnApproveBtn")
        b.wait("document.getElementById('mnApprove').open")
        self.assertIn("Pat Unknown needs details", self.ev("document.querySelector('#mnApprove .mnap-l').textContent"), "and so does the approve popup")
        b.key("Escape")
        b.pump(0.2)


if __name__ == "__main__":
    unittest.main()
