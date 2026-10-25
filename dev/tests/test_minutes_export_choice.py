"""#330 the minutes' Export offers Shareable and Internal, in a real browser on the real live server (LiveBrowserCase; no Claude runs).
Fictional demo data only (the steering committee of test_minutes_editor, with a Sensitive decision and a Sensitive action).

What Shareable guarantees: the file made by the menu's Shareable Word, PDF and HTML is the minutes' distributed version
(minutes_record.distributed_of, via /api/minutes/export with version "distributed"), so it never holds a Sensitive item row, a
partner-only or excluded one, or an Internal-only line. Internal keeps them, by design, and is marked Internal. The Shareable
entries come first, under their own heading, and the follow-up email sits with them. This test proves it on the files the menu
makes (the page text, the Word paragraphs and the PDF text), and by the request each menu entry sends. Nothing is sent.

Run: python3 dev/tests/test_minutes_export_choice.py      (Chrome tier; skipped without Chrome)
"""
import json
import subprocess
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402
import test_minutes_editor as me  # noqa: E402
from handchecks.test_v210 import export_text  # noqa: E402

SECRETS = ("The pilot stays on the lighthouse site", "Book the UAT test environment")
KEPT = "Send the revised SOW to the client"
FMT = {"Word": "docx", "PDF": "pdf", "HTML": "html"}


class MinutesExportChoice(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        populate(v)
        cls.proposal = me.stage_meeting(v)
        p = v.root / "system/staging" / cls.proposal
        data = json.loads(p.read_text(encoding="utf-8"))
        for i in data["items"]:
            if i["n"] in (2, 4):
                i["flags"] = ["sensitive"]
        p.write_text(json.dumps(data), encoding="utf-8")
        subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, 'system/scripts'); import minutes_record; "
                        f"minutes_record.change({me.DRAFT!r}, {{'op': 'deadline', 'n': 1, 'words': 'Friday'}})"],
                       cwd=v.root, capture_output=True, text=True, check=True)

    def setUp(self):
        super().setUp()
        self.b.eval(f"go('minutes',{{file:{json.dumps(self.proposal)}}})")
        self.b.wait("document.querySelector('#v-minutes tr.mi')", 15)
        self.b.pump(0.3)

    def ev(self, js):
        return self.b.eval(js)

    def approve_boxes(self):
        """Approve minutes: the confirm box if it opens, then #324's File the minutes box (each only if it opens)."""
        for box, go in (("mnApprove", "#mnApproveGo"), ("mnFiling", "#mnFilingGo")):
            try:
                self.b.wait(f"(document.getElementById('{box}')||{{}}).open", 5)
            except Exception:
                continue
            self.b.click(go)
            self.b.pump(0.7)

    def open_menu(self):
        self.b.click("#v-minutes [data-mnexport]")
        self.b.wait("document.querySelector('#v-minutes .ddmenu.on')")

    def pick(self, label):
        self.open_menu()
        self.b.eval("[...document.querySelectorAll('#v-minutes .ddmenu.on [role=menuitem]')].find(x=>x.querySelector('b').textContent===%s).click()"
                    % json.dumps(label))
        self.b.pump(1.5)

    def files(self):
        return set(self.v.root.rglob("*.html")) | set(self.v.root.rglob("*.docx")) | set(self.v.root.rglob("*.pdf"))

    def wait_new(self, before, fmt, seconds=30):
        """The new files of one format. The export is written some time after the click, longer on a busy machine, so poll for
        it instead of trusting one fixed pause (the test failed under load with an empty list, and passed alone)."""
        end = time.time() + seconds
        while True:
            new = [f for f in self.files() - before if f.suffix == "." + fmt]
            if new or time.time() > end:
                return new
            self.b.pump(0.5)

    def test_1_the_menu_says_shareable_and_internal_in_plain_words(self):
        self.open_menu()
        heads = self.ev("[...document.querySelectorAll('#v-minutes .ddmenu.on .fsec2')].map(x=>x.textContent)")
        self.assertEqual(heads, ["Shareable: for sending", "Internal: colleagues only"])
        lines = self.ev("[...document.querySelectorAll('#v-minutes .ddmenu.on [role=menuitem]')].map(x=>[x.querySelector('b').textContent, x.textContent, x.getAttribute('aria-disabled'), x.getAttribute('data-tip')])")
        for name, whole, dis, tip in lines[:3]:
            self.assertEqual((dis, tip), ("true", "Approve the minutes first"), f"{name}: Shareable file is disabled on a draft, with its reason")
            self.assertIn("check the Updates text", whole)
            self.assertNotIn("No Sensitive or Internal-only", whole, "no claim wider than the item rows")
        self.assertIsNone(lines[3][2], "the Shareable email works on a draft (existing behaviour)")
        self.assertEqual(lines[3][3], "Draft: check before sending", "with a tip, not a disable")
        names = self.ev("[...document.querySelectorAll('#v-minutes .ddmenu.on [role=menuitem] b')].map(x=>x.textContent)")
        self.assertEqual(names, ["Word", "PDF", "HTML", "Draft the follow-up email",
                                 "Word (Internal)", "PDF (Internal)", "HTML (Internal)", "Draft an Internal follow-up email"],
                         "Shareable first, with the follow-up email; Internal after")
        self.b.key("Escape")

    def test_2_the_shareable_follow_up_is_the_default_pairing(self):
        self.open_menu()
        self.b.eval("[...document.querySelectorAll('#v-minutes .ddmenu.on [role=menuitem]')].find(x=>x.querySelector('b').textContent==='Draft the follow-up email').click()")
        self.b.wait("document.getElementById('deDlg') && document.getElementById('deDlg').open && document.querySelector('#dePrev').textContent.length>20", 15)
        self.assertEqual(self.ev("DE.version"), "distributed")
        words = self.ev("document.getElementById('deDlg').textContent")
        self.assertIn("Shareable follow-up", words)
        self.assertIn("From the Shareable version", words)
        self.assertNotIn("Distributed", words)


    def test_3_shareable_waits_for_approval_then_holds_no_sensitive_item_and_internal_does(self):
        for label in FMT:                        # a draft: the Shareable entries are disabled, so nothing is asked and no file made
            before = self.files()
            self.pick(label)
            self.b.key("Escape")
            self.assertEqual(self.files(), before, "no Shareable file from a draft")
        self.b.click("#mnApproveBtn")
        self.b.pump(0.5)
        self.approve_boxes()
        self.b.wait("document.querySelector('#v-minutes .sheet-status') && !/Draft/i.test(document.getElementById('mnApproveBtn')?document.getElementById('mnApproveBtn').textContent:'')", 20)
        self.b.pump(1)
        for label, fmt in FMT.items():
            for ver, suffix in (("distributed", ""), ("internal", " (Internal)")):
                with self.subTest(format=fmt, version=ver):
                    before = self.files()
                    self.pick(label + suffix)
                    new = self.wait_new(before, fmt)
                    self.assertEqual(len(new), 1, f"{label}{suffix} made one {fmt} file: {new}")
                    text = export_text(self.v.root, new[0], fmt)
                    self.assertIn(KEPT, text, "the unmarked action is there (the file is not empty)")
                    # The fixture's Updates summary repeats the Sensitive decision's words as a plain line; that line is not an
                    # item row (only a line marked Internal only is withheld), so the decision is checked in its own section.
                    decisions = text[text.index("Decisions") if "Decisions" in text else text.upper().index("DECISIONS"):]
                    decisions = decisions[:decisions.upper().index("RISKS")]
                    for s, where in ((SECRETS[0], decisions), (SECRETS[1], text)):
                        if ver == "distributed":
                            self.assertNotIn(s, where, f"Shareable {fmt} must not hold the Sensitive item {s!r}")
                        else:
                            self.assertIn(s, where, f"Internal {fmt} keeps {s!r}, by design")
                    if ver == "distributed":
                        self.assertIn("(shareable)", new[0].name)

if __name__ == "__main__":
    unittest.main()
