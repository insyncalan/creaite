"""Tests for BL-276: saved emails (.eml) in search.

Run: python3 dev/tests/test_search_eml.py
Each test builds a throwaway vault (test_tracker.Vault) and runs the real scripts there.
"""
import json
import subprocess
import sys
import unittest
from email.message import EmailMessage
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_search import put  # noqa: E402
from test_tracker import ABC, Vault  # noqa: E402


def email_bytes(kind):
    """A saved email (.eml) of one kind: multipart with a base64 plain body, an HTML alternative and attachments;
    HTML only, quoted-printable; or malformed."""
    if kind == "malformed":
        return (b"From: =?utf-8?b?broken\nSubject: Half a message about quarterly forecasting\nContent-Type: multipart/mixed; "
                b"boundary=\"zzz\"\n\n--zzz\nContent-Type: text/plain; charset=nonsense-charset\n"
                b"Content-Transfer-Encoding: base64\n\n!!!not base64!!!\n")
    m = EmailMessage()
    m["From"] = "Mia Hale <mia@client.example>"
    m["To"] = "Alan Carter <alan@example.com>"
    m["Cc"] = "Omar Haddad <omar@example.com>"
    m["Date"] = "Tue, 13 Oct 2026 09:30:00 +0400"
    if kind == "html":
        m["Subject"] = "Steering pack review"
        m.set_content("<html><body><style>p {color: red}</style><p>The steering committee wants the "
                      "<b>procurement</b> timeline&nbsp;redrawn.</p></body></html>", subtype="html", cte="quoted-printable")
        return m.as_bytes()
    m["Subject"] = "Budget reallocation for phase two"
    m.set_content("The hyperscaler credits arrive in November, so the pilot moves.", cte="base64")
    m.add_alternative("<p>The hyperscaler credits arrive in November.</p>", subtype="html")
    m.add_attachment(b"PK\x03\x04 not really a spreadsheet", maintype="application",
                     subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename="Budget v2 forecast.xlsx")
    m.add_attachment(b"%PDF-1.4 sow", maintype="application", subtype="pdf", filename="Signed SOW.pdf")
    return m.as_bytes()


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.v.run("init")

    def tearDown(self):
        self.v.cleanup()

    def query(self, text):
        """The paths a search finds."""
        return [h["path"] for h in json.loads(self.v.run("query", text).stdout)]

    def py(self, code, *flags):
        """Run Python in the vault with tracker imported; returns stdout."""
        r = subprocess.run([sys.executable, *flags, "-c", "import sys, json; sys.path.insert(0, 'system/scripts'); "
                            "import tracker\n" + code], cwd=self.v.root, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def debug_on(self):
        """Turn the debug log's level to debug in this vault."""
        f = self.v.root / "system/config/settings.json"
        s = json.loads(f.read_text(encoding="utf-8"))
        s.setdefault("logging", {})["level"] = "debug"
        f.write_text(json.dumps(s), encoding="utf-8")

    def debug_log(self):
        """Everything in this vault's debug log."""
        return "".join(f.read_text(encoding="utf-8") for f in sorted((self.v.root / "system/logs").glob("debug-*.log")))


class EmailTests(Base):
    def test_saved_emails_are_found_by_body_subject_sender_and_attachment(self):
        put(self.v, f"{ABC}/documents/2026-10-13 Budget.eml", email_bytes("multipart"))
        put(self.v, f"{ABC}/documents/Steering.eml", email_bytes("html"))
        self.assertIn("Indexed 2 file(s)", self.v.run("index").stdout)
        budget, steering = f"{ABC}/documents/2026-10-13 Budget.eml", f"{ABC}/documents/Steering.eml"
        self.assertEqual(self.query("hyperscaler"), [budget])                                   # base64 body
        self.assertEqual(self.query("reallocation"), [budget])                                  # subject
        self.assertEqual(sorted(self.query("mia@client.example")), sorted([budget, steering]))  # sender
        self.assertEqual(self.query("forecast"), [budget])                                      # an attachment's name
        self.assertEqual(self.query("procurement"), [steering])                                 # HTML only, tags gone
        self.assertEqual(self.query("color"), [])                                               # its style isn't text

    def test_the_text_has_headers_body_and_attachment_names_only(self):
        put(self.v, f"{ABC}/documents/Budget.eml", email_bytes("multipart"))
        text = self.py(f"from pathlib import Path\nprint(tracker.text_of(Path('{ABC}/documents/Budget.eml')))")
        lines = text.strip().split("\n")
        self.assertEqual(lines[0], "From: Mia Hale <mia@client.example>")
        self.assertEqual([ln.split(":")[0] for ln in lines[:5]], ["From", "To", "Cc", "Date", "Subject"])
        self.assertIn("The hyperscaler credits arrive in November, so the pilot moves.", lines)  # the plain part
        self.assertEqual(lines[-1], "Attachments: Budget v2 forecast.xlsx, Signed SOW.pdf")
        self.assertNotIn("not really a spreadsheet", text)                                       # contents aren't read

    def test_a_malformed_email_gives_what_could_be_read_without_error(self):
        self.debug_on()
        put(self.v, f"{ABC}/documents/Broken.eml", email_bytes("malformed"))
        put(self.v, f"{ABC}/documents/Empty.eml", b"")
        r = self.v.run("index")
        self.assertIn("Indexed 2 file(s)", r.stdout)
        self.assertEqual(self.query("forecasting"), [f"{ABC}/documents/Broken.eml"])
        self.assertEqual(self.query("Empty"), [f"{ABC}/documents/Empty.eml"])
        self.assertNotIn("forecasting", self.debug_log())

    def test_the_index_is_rebuilt_once_for_the_new_readers(self):
        self.py("tracker.build_index()")
        stamp = self.v.root / "system/search/index-built.json"
        old = json.loads(stamp.read_text(encoding="utf-8"))
        self.assertEqual(old.get("readers"), int(self.py("print(tracker.INDEX_READERS)")))     # 2, then 3 with BL-275
        old.pop("readers")                                                                      # an index from 1.8
        stamp.write_text(json.dumps(old), encoding="utf-8")
        self.assertEqual(json.loads(self.py("print(json.dumps(tracker.index_state()))")), [True, "file readers changed"])
        self.py("tracker.build_index()")
        self.assertEqual(json.loads(self.py("print(json.dumps(tracker.index_state()))")), [False, ""])


if __name__ == "__main__":
    unittest.main()
