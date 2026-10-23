"""#312: Your profile. Your own people-register entry, read and edited in Settings, asked for once on Today's Getting started.

- the source: one module (src/profile.js), no database, schema or server change, no real names or addresses;
- the card (Chrome): shows the register's details for the person who is "you", Edit my details writes the register entry
  through the same form and save as any person (so Undo works), the name is the identity.name setting and nothing is added to
  the shared register's columns;
- first run (Chrome): About you is asked once, Not now is remembered and the Settings card stays;
- the email is a label: nothing in the page reads it to grant or change anything.

Run: python3 dev/tests/test_profile_312.py   (the browser part needs Google Chrome; skipped otherwise)
"""
import json
import re
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_project_settings_v2 import Base  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "system/templates/dashboard/src"


class Source(unittest.TestCase):
    def test_one_module_with_no_server_or_schema_reach(self):
        t = (SRC / "profile.js").read_text()
        self.assertNotIn("/api/", t, "the profile adds no route of its own")
        self.assertNotRegex(t, r"localStorage|sessionStorage", "the asked flag goes through the page's store")
        self.assertNotRegex(t, r"\bVIP\b|vip")
        self.assertIn("identity.name", t)

    def test_the_email_is_never_read_to_decide_anything(self):
        t = (SRC / "profile.js").read_text()
        for word in ("permission", "access", "allow", "admin", "token", "auth"):
            for ln in t.splitlines():
                if re.search(rf"\b{word}", ln, re.I):
                    self.assertTrue(ln.lstrip().startswith(("//", "/*", "*")) or "doesn't" in ln or "label" in ln, ln)

    def test_no_real_addresses(self):
        t = (SRC / "profile.js").read_text()
        self.assertEqual(re.findall(r"[\w.+-]+@[\w-]+\.\w+", t), [])


class Card(Base):
    shared_server = False

    def open_card(self, me):
        b = self.b
        b.eval(f"S.me={me!r}; S.meSet=true; window.__asked=[]; window.__yes=true; window.confirm=m=>{{ __asked.push(m); return __yes; }}")
        b.eval("go('settings','profile')")
        b.wait("!!document.querySelector('#profileCard')", 20)
        time.sleep(0.6)

    def count(self, text):
        return sum(1 for ln in self.register.splitlines() if ln.startswith(f"| {text} |"))

    def fill_and_save(self, email):
        b = self.b
        self.tap("#pfEdit")
        b.wait("document.getElementById('personDlg').open")
        b.eval(f"document.getElementById('pd_email').value={email!r}")
        self.tap("#pdSave")
        self.applied()

    def test_a_name_with_a_bar_is_one_row_however_often_it_is_saved(self):          # M1
        b = self.b
        self.open_card("Kai | Example")
        self.fill_and_save("kai@example.test")
        b.eval("go('settings','profile')")
        b.wait("!!document.querySelector('#profileCard')", 20)
        self.fill_and_save("kai2@example.test")
        self.assertEqual(self.count("Kai / Example"), 1)
        self.assertNotIn("Kai | Example", self.register)

    def test_a_name_that_is_already_someone_asks_whose_row_it_is_before_anything_is_edited(self):   # M2
        b = self.b
        self.open_card("Sara Example")
        b.eval("__yes=false")
        before = self.register
        self.tap("#pfEdit")
        time.sleep(0.8)
        self.assertFalse(b.eval("document.getElementById('personDlg').open"))
        asked = b.eval("__asked")
        self.assertEqual(len(asked), 1)
        self.assertIn("Sara Example", asked[0])
        self.assertIn("sara@example.com", asked[0])
        self.assertEqual(self.register, before)
        b.eval("__yes=true")                                                       # yes: it is edited, and it is not asked again
        self.tap("#pfEdit")
        b.wait("document.getElementById('personDlg').open")
        b.eval("document.getElementById('pdCancel')&&document.getElementById('pdCancel').click()")
        self.assertEqual(b.eval("profileEntry().name"), "Sara Example")

    def test_a_missing_name_never_writes_the_placeholder(self):                  # L1
        b = self.b
        self.open_card("Alan Carter")
        b.eval("S.meSet=false; profileRedraw()")
        self.assertTrue(b.eval("document.querySelector('#pfEdit').disabled"))
        self.assertEqual(b.eval("document.querySelector('#pfName').value"), "")
        self.assertEqual(b.eval("profileDetails().name"), "")
        self.assertFalse(b.eval("profileSave({email:'me@example.test',aliases:[],org:'',role:''})"))
        self.assertNotIn("Alan Carter", self.register)

    def test_the_address_is_the_key_once_there_is_one(self):                     # L2
        b = self.b
        self.open_card("Sara Alias")                                              # no row of that name: the address finds Sara's row
        n = self.count("Sara Example")
        self.assertTrue(b.eval("profileSave({email:'SARA@example.com',aliases:['Sara'],org:'',role:'Lead'})"))
        self.applied()
        self.assertEqual(self.count("Sara Example"), n)
        self.assertEqual(self.count("Sara Alias"), 0)
        self.assertIn("Lead", self.register)
        self.assertEqual(b.eval("emailKey(' A@B.test; c@d.test ')"), "a@b.test")
        cfg = json.loads((self.v.root / "system/config/settings.json").read_text())
        self.assertNotIn("sara@example.com", json.dumps(cfg), "which person is you stays a name on this computer")

    def test_it_shows_the_register_entry_for_you(self):
        self.open_card("Sara Example")
        b = self.b
        self.assertEqual(b.eval("document.querySelector('#pfName').value"), "Sara Example")
        self.assertIn("@", b.eval("document.querySelector('#pfEmail').textContent"))
        self.assertRegex(b.eval("document.querySelector('#pfNote').textContent"), r"label only")
        self.assertRegex(b.eval("document.querySelector('#pfNote').textContent"), r"not in the shared register")

    def test_edit_my_details_writes_the_register_entry_and_nothing_else(self):
        self.open_card("Sara Example")
        b = self.b
        before_cols = self.register.splitlines()
        self.tap("#pfEdit")
        b.wait("document.getElementById('personDlg').open")
        self.assertTrue(b.eval("document.getElementById('pd_name').readOnly"))
        b.eval("document.getElementById('pd_role').value='Delivery lead'; document.getElementById('pd_aliases').value='Sara, SE'")
        self.tap("#pdSave")
        self.applied()
        line = [ln for ln in self.register.splitlines() if ln.startswith("| Sara Example")][0]
        self.assertIn("Delivery lead", line)
        self.assertIn("SE", line)
        head = [ln for ln in self.register.splitlines() if ln.startswith("| Full name")][0]
        old = [ln for ln in before_cols if ln.startswith("| Full name")][0]
        new_cols = set(c.strip() for c in head.strip("|").split("|")) - set(c.strip() for c in old.strip("|").split("|"))
        self.assertLessEqual(new_cols, {"Labels", "Follow"}, "no column for you in the shared file (Labels and Follow are the register's own)")
        b.wait("document.querySelector('#pfRole') && document.querySelector('#pfRole').textContent==='Delivery lead'")

    def test_someone_not_in_the_register_is_added_by_the_same_form(self):
        self.open_card("Zoe Example")
        b = self.b
        self.assertIn("Add my details", b.eval("document.querySelector('#pfEdit').textContent"))
        self.tap("#pfEdit")
        b.wait("document.getElementById('personDlg').open")
        b.eval("document.getElementById('pd_email').value='zoe@example.test'")
        self.tap("#pdSave")
        self.applied()
        self.assertRegex(self.register, r"\| Zoe Example \|[^\n]*zoe@example\.test")

    def colleague_address(self, me, email, yes):
        b = self.b
        self.open_card(me)
        b.eval(f"__yes={'true' if yes else 'false'}")
        self.tap("#pfEdit")
        b.wait("document.getElementById('personDlg').open")
        b.eval(f"document.getElementById('pd_email').value={email!r}")
        self.tap("#pdSave")
        time.sleep(1.0)

    def sara_line(self):
        return [ln for ln in self.register.splitlines() if ln.startswith("| Sara Example")][0]

    def test_a_colleagues_address_with_yes_keeps_her_details_and_finishes_your_profile(self):   # #312 review 1
        b = self.b
        before = self.sara_line()
        self.colleague_address("Zoe Example", "sara@example.com", True)
        self.applied()
        asked = b.eval("__asked")
        self.assertEqual(len(asked), 1)
        self.assertIn("keeps everything already there", asked[0])
        self.assertIn("Zoe Example", asked[0])
        line = self.sara_line()
        for kept in ("sara@example.com", "Sara", "SE", "Example Client Ltd", "Delivery lead"):
            self.assertIn(kept, line)
        self.assertIn("Zoe Example", line, "your name is added to her aliases")
        self.assertNotEqual(line, before)
        self.assertEqual(self.count("Zoe Example"), 0, "no second row")
        self.assertEqual(b.eval("profileEntry().name"), "Sara Example")
        self.assertTrue(b.eval("profileDone()"))

    def test_a_colleagues_address_with_no_changes_nothing(self):                     # #312 review 1
        b = self.b
        before = self.register
        self.colleague_address("Zoe Example", "sara@example.com", False)
        self.assertEqual(len(b.eval("__asked")), 1)
        self.assertEqual(self.register, before)
        self.assertFalse(b.eval("profileDone()"))

    def test_an_alias_is_you_so_no_second_row_is_made(self):                          # #312 review 2
        b = self.b
        self.open_card("SE")
        self.assertEqual(b.eval("profileEntry().name"), "Sara Example")
        self.assertEqual(b.eval("profileDetails().role"), "Delivery lead")
        self.assertTrue(b.eval("profileSave({email:'sara@example.com',aliases:['Sara','SE'],org:'',role:'Lead'})"))
        self.applied()
        self.assertEqual(self.count("SE"), 0)
        self.assertEqual(self.count("Sara Example"), 1)
        self.assertIn("Lead", self.sara_line())

    def test_a_second_address_of_a_colleague_is_checked_too(self):                   # #312 review 3
        b = self.b
        self.open_card("Zoe Example")
        b.eval("shared.REG.find(p=>p.name==='Sara Example').email='sara@example.com; sara.two@example.com'; __yes=false")
        before = self.register
        self.tap("#pfEdit")
        b.wait("document.getElementById('personDlg').open")
        b.eval("document.getElementById('pd_email').value='SARA.TWO@example.com'")
        self.tap("#pdSave")
        time.sleep(1.0)
        self.assertEqual(len(b.eval("__asked")), 1)
        self.assertIn("Sara Example", b.eval("__asked")[0])
        self.assertEqual(self.register, before)

    def test_the_name_is_the_identity_setting_on_this_computer(self):
        self.open_card("Sara Example")
        b = self.b
        b.eval("document.querySelector('#pfName').value='Sara Example-Jones'")
        self.tap("#pfNameSave")
        b.wait("S.me==='Sara Example-Jones'", 15)
        cfg = json.loads((self.v.root / "system/config/settings.json").read_text())
        self.assertEqual(cfg["identity"]["name"], "Sara Example-Jones")
        self.assertNotIn("Example-Jones", self.register, "which person is you is not in the shared register")

    def test_the_address_opens_it_and_it_fits_at_900(self):
        b = self.b
        b.eval("go('settings','about-you')")
        b.wait("!!document.querySelector('#profileCard')", 20)
        self.assertTrue(b.eval("document.querySelector('#profileCard').scrollWidth<=document.documentElement.clientWidth"))


class FirstRun(Base):
    def test_about_you_is_asked_once_and_not_now_is_remembered(self):
        b = self.b
        b.eval("try{localStorage.removeItem('creaite-profile-asked')}catch(e){}; S.me='Zoe Example'; S.meSet=true; go('today')")
        b.eval("localStorage.removeItem('creaite-setup')")
        due = b.eval("profileQuestionDue()")
        self.assertTrue(due)
        self.assertIn("About you", b.eval("profileQuestionHtml()"))
        b.eval("document.dispatchEvent(new Event('x'))")
        b.eval("(()=>{ const d=document.createElement('button'); d.dataset.pfq='no'; document.body.append(d); d.click(); })()")
        b.wait("!profileQuestionDue()", 10)
        self.assertEqual(b.eval("profileQuestionHtml()"), "")
        b.eval("go('settings','profile')")
        b.wait("!!document.querySelector('#profileCard')", 20)

    def test_it_is_not_asked_when_the_details_are_in(self):
        self.b.eval("S.me='Sara Example'; try{localStorage.removeItem('creaite-profile-asked')}catch(e){}")
        self.assertTrue(self.b.eval("profileDone()"))
        self.assertFalse(self.b.eval("profileQuestionDue()"))


if __name__ == "__main__":
    unittest.main()
