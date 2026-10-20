"""BL-09 in the page: archiving a project that still has open items asks first, in #parchDlg (the Dialog block, BL-316).

The project settings' Archive (Archive and close; Settings › Projects and register's until the Settings line) on a
project with open items, once its own Archive? is answered: the live server answers with the items, and the page
opens #parchDlg, "<name> has n open items", with Stop and "Cancel them all and archive". Checked with real keys and clicks:
- focus goes into the dialog (Stop, its first control) and comes back to the Archive button when it closes;
- Stop, Esc and a click on the scrim each close it with "Stopped: nothing was archived", and nothing is staged: no approval
  card, the project not archived, its items still open;
- "Cancel them all and archive" asks again with cancel_open, as release-194's hand-made dialog did: the change goes on the
  approval card in ask creaite (each open item Open → Cancelled), and nothing changes before Approve.

Run: python3 dev/tests/test_archive_ask_browser.py   (needs Google Chrome; skipped otherwise)
"""
import json
import re
import sys
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

ARCHIVE = "#psArchive"            # the project settings' Archive… (#247); it asks first (#psArchiveYes), then the server
YES = "#psArchiveYes"
OPEN = "document.getElementById('parchDlg')?.open"


class ArchiveAsk(LiveBrowserCase):
    """One vault and server per test: Cancel them all and archive puts a change on the card."""
    quiet_jobs = False        # exercises backups or archiving: keeps the shipped settings

    def post(self, path, body):
        html = urllib.request.urlopen(self.base + "/").read().decode()
        token = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": token})
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())

    def open_items(self):
        """ABC's open items, as the server lists them for the dialog (a read: nothing is staged)."""
        got = self.post("/api/project/archive", {"code": "ABC", "action": "archive"})
        self.assertFalse(got["ok"])
        return [o["id"] for o in got["open"]]

    def archived(self):
        return [p["archived"] for p in self.v.rows("projects") if p["code"] == "ABC"]

    def ask(self):
        """ABC's settings › Archive and close: focus Archive…, press Enter, then Enter on its Archive: the dialog opens. Its heading."""
        b = self.b
        b.eval("go('psettings','ABC')")
        b.wait(f"!!document.querySelector({json.dumps(ARCHIVE)})", 15)
        for sel in (ARCHIVE, YES):
            b.wait(f"!!document.querySelector({json.dumps(sel)})", 15)
            self.assertTrue(b.eval(f"(()=>{{ const e=document.querySelector({json.dumps(sel)}); e.scrollIntoView({{block:'center'}}); e.focus(); return document.activeElement===e; }})()"))
            b.key("Enter")
        b.wait(OPEN, 30)
        b.pump(0.2)
        return b.eval("document.getElementById('parchH').textContent")

    def assert_focus_in_dialog(self):
        self.assertTrue(self.b.eval("document.getElementById('parchDlg').contains(document.activeElement)"))
        self.assertEqual(self.b.eval("document.activeElement.textContent"), "Stop")      # its first control

    def assert_stopped(self):
        b = self.b
        b.wait(f"!{OPEN}", 10)
        b.wait("/Stopped: nothing was archived/.test(document.getElementById('snackT').textContent)", 10)
        self.assertTrue(b.eval(f"document.activeElement===document.querySelector({json.dumps(ARCHIVE)})"),
                        "focus goes back to the Archive button")
        self.assertIsNone(self.post("/api/edit/pending", {}).get("card"), "nothing is staged")
        self.assertEqual(self.archived(), [0])

    def test_it_names_the_project_and_its_open_items(self):
        before = self.open_items()
        self.assertTrue(before, "the sample has open items in ABC")
        head = self.ask()
        n = len(before)
        self.assertEqual(head, f"Example Programme has {n} open item{'' if n == 1 else 's'}")
        b = self.b
        self.assertEqual(b.eval("document.getElementById('parchDlg').getAttribute('aria-labelledby')"), "parchH")
        self.assertTrue(b.eval("document.querySelector('#parchDlg:modal')") is not None)
        listed = b.eval("[...document.querySelectorAll('#parchDlg .parchlist li b')].map(x=>x.textContent)")
        self.assertEqual(sorted(listed), sorted(before))
        self.assertEqual(b.eval("[...document.querySelectorAll('#parchDlg .acts button')].map(x=>x.textContent)"),
                         ["Stop", "Cancel them all and archive"])
        self.assert_focus_in_dialog()

    def test_stop_esc_and_the_scrim_each_stop_with_nothing_archived(self):
        b = self.b
        before = self.open_items()
        for how in ("stop", "esc", "scrim"):
            with self.subTest(how):
                self.ask()
                self.assert_focus_in_dialog()
                if how == "stop":
                    b.key("Enter")                                    # Stop has focus
                elif how == "esc":
                    b.key("Escape")
                else:                                                 # a real click on the scrim, outside the dialog's box
                    b.call("Input.dispatchMouseEvent", type="mouseMoved", x=5, y=5, button="none")
                    for kind in ("mousePressed", "mouseReleased"):
                        b.call("Input.dispatchMouseEvent", type=kind, x=5, y=5, button="left", clickCount=1)
                self.assert_stopped()
                self.assertEqual(self.open_items(), before)
                b.eval("document.getElementById('snackT').textContent=''")

    def test_cancel_them_all_and_archive_puts_the_change_on_the_card(self):
        b = self.b
        before = self.open_items()
        self.ask()
        b.click('#parchDlg [data-a="go"]')
        b.wait(f"!{OPEN}", 10)
        b.wait("/On the approval card/.test(document.getElementById('snackT').textContent)", 60)
        card = self.post("/api/edit/pending", {})["card"]
        self.assertTrue(card and card["card"], card)
        for i in before:                                              # each open item cancelled (a milestone from Planned)
            self.assertTrue(any(re.fullmatch(rf"{i} · Status: \w+ → Cancelled", ln) for ln in card["lines"]), (i, card["lines"]))
        self.assertTrue(any(ln.startswith("Archive Example Programme (ABC)") for ln in card["lines"]))
        b.wait(f"!!document.querySelector('#chLog [data-ecard={json.dumps(card['card'])}]')", 30)   # the card, in ask creaite
        self.assertEqual(self.archived(), [0])   # nothing before Approve
        self.assertEqual(self.open_items(), before)


if __name__ == "__main__":
    unittest.main()
