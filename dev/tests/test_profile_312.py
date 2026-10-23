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
        b.eval(f"S.me={me!r}; S.meSet=true")
        b.eval("go('settings','profile')")
        b.wait("!!document.querySelector('#profileCard')", 20)
        time.sleep(0.6)

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
        self.assertLessEqual(new_cols, {"Labels"}, "no column for you in the shared file (Labels is the register's own)")
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
