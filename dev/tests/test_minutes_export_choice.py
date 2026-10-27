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

    def hold_back_if_asked(self, wait=5):
        """#329: the Review these lines before sharing box, if it opens: every line held back with its item, then Export again."""
        try:
            self.b.wait("(document.getElementById('mnShare')||{}).open", wait)
        except Exception:
            return []
        lines = self.b.eval("[...document.querySelectorAll('#mnShare [data-share-key]')].map(li=>li.querySelector('div').textContent)")
        self.assertEqual(self.b.eval("document.getElementById('mnShareH').textContent"), "Review these lines before sharing")
        self.assertTrue(self.b.eval("document.getElementById('mnShareGo').disabled"), "Export again waits for every answer")
        self.b.eval("document.querySelectorAll('#mnShare [data-share=hold]').forEach(b=>b.click())")
        self.b.pump(0.3)
        self.b.click("#mnShareGo")
        self.b.pump(1.5)
        return lines

    def open_menu(self):
        # click_until (BL-327): under a loaded suite the press can land and the menu still not open (CI 27-10: focus on #mnExport,
        # no .ddmenu.on after the wait); press again only while it is closed, so a second press can't close it.
        self.b.click_until("#v-minutes [data-mnexport]", "!!document.querySelector('#v-minutes .ddmenu.on')", timeout=15)

    def pick(self, label):
        self.open_menu()
        self.b.eval("[...document.querySelectorAll('#v-minutes .ddmenu.on [role=menuitem]')].find(x=>x.querySelector('b').textContent===%s).click()"
                    % json.dumps(label))
        self.b.pump(1.5)

    def files(self):
        return set(self.v.root.rglob("*.html")) | set(self.v.root.rglob("*.docx")) | set(self.v.root.rglob("*.pdf"))

    def export_done(self, label):
        """Pick one export entry and wait until the server has answered its request (so the file is written: the route is
        synchronous under the server's lock). A fixed pause raced a slow export (a PDF through Chrome on a busy machine): the
        check ran before the file existed, or took the previous export's late file for this one."""
        self.b.eval("""(()=>{ if(!window.__expWrapped){ window.__expWrapped=true; window.__exp={sent:0,done:0}; const f=window.fetch;
            window.fetch=function(u,o){ const x=/api\\/minutes\\/export/.test(String(u)); if(x) window.__exp.sent++;
              const p=f.apply(this,arguments); if(x) p.then(r=>r.clone().text()).catch(()=>{}).then(()=>{ window.__exp.done++; }); return p; }; }
            window.__exp.base=window.__exp.done; })()""")
        self.pick(label)
        self.b.wait("window.__exp.sent>window.__exp.base && window.__exp.done>window.__exp.base && window.__exp.done===window.__exp.sent", 90)

    def test_1_the_menu_says_shareable_and_internal_in_plain_words(self):
        self.open_menu()
        heads = self.ev("[...document.querySelectorAll('#v-minutes .ddmenu.on .fsec2')].map(x=>x.textContent)")
        self.assertEqual(heads, ["Shareable: for sending", "Internal: colleagues only"])
        lines = self.ev("[...document.querySelectorAll('#v-minutes .ddmenu.on [role=menuitem]')].map(x=>[x.querySelector('b').textContent, x.textContent, x.getAttribute('aria-disabled'), x.getAttribute('data-tip')])")
        for name, whole, dis, tip in lines[:3]:
            self.assertEqual((dis, tip), ("true", "Approve the minutes first"), f"{name}: Shareable file is disabled on a draft, with its reason")
            self.assertIn("the lines held back with them left out", whole)      # #329: such lines are asked about first
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
        self.assertEqual(self.hold_back_if_asked(15), ["The committee reviewed the SOW and the pilot site.", "The pilot stays on the lighthouse site."],
                         "#329: the lines that describe the Sensitive decision are asked about first")
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
                    self.export_done(label + suffix)
                    if ver == "distributed" and self.hold_back_if_asked(2):      # #329: answered once (test_2 answers on the draft)
                        self.b.wait("window.__exp.sent>=window.__exp.base+2 && window.__exp.done===window.__exp.sent", 90)
                    new = [f for f in self.files() - before if f.suffix == "." + fmt]
                    self.assertEqual(len(new), 1, f"{label}{suffix} made one {fmt} file: {new}")
                    text = export_text(self.v.root, new[0], fmt)
                    self.assertIn(KEPT, text, "the unmarked action is there (the file is not empty)")
                    # The fixture's Updates repeat the Sensitive decision's words as a plain line. #329: the Shareable file holds it
                    # back with the decision (answered in the box), so Shareable is checked in the whole text; Internal keeps the
                    # decision in its own section.
                    decisions = text[text.index("Decisions") if "Decisions" in text else text.upper().index("DECISIONS"):]
                    decisions = decisions[:decisions.upper().index("RISKS")]
                    for s, where in ((SECRETS[0], text if ver == "distributed" else decisions), (SECRETS[1], text)):
                        if ver == "distributed":
                            self.assertNotIn(s, where, f"Shareable {fmt} must not hold the Sensitive item {s!r}")
                        else:
                            self.assertIn(s, where, f"Internal {fmt} keeps {s!r}, by design")
                    if ver == "distributed":
                        self.assertIn("(shareable)", new[0].name)

if __name__ == "__main__":
    unittest.main()
