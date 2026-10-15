"""BL-106: the Generate options, the notes under a draft and "Make it executive", in a real browser against the real live server.

Run: python3 dev/tests/test_status_live_browser.py   (needs Google Chrome; skipped otherwise)
Claude is a stand-in (see test_status_live.py): it prints a fixed reply and records the prompt it was given.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from live_browser import LiveBrowserCase  # noqa: E402
from test_status_live import FAKE  # noqa: E402


class ExecBrowser(LiveBrowserCase):
    shared_server = True

    @classmethod
    def load(cls, v):
        super().load(v)
        cls.fake = v.root / "fake_claude.py"
        cls.fake.write_text(FAKE)
        cls.fake.chmod(0o755)

    @classmethod
    def server_env(cls):
        return {"CREAITE_CLAUDE": str(cls.fake), "CREAITE_NOW": "2026-10-09 13:00"}

    def prompt(self):
        return Path(str(self.fake) + ".prompt").read_text(encoding="utf-8")

    def open_dialog(self):
        b = self.b
        b.eval("go('cockpit','ABC')")
        b.wait("document.querySelector('#v-cockpit .curcard [data-gen]')")
        b.click("#v-cockpit .curcard [data-gen]")
        b.wait("document.getElementById('genDlg').open")

    def open_editor(self, html):
        b = self.b
        b.eval("go('cockpit','ABC')")
        b.wait("document.querySelector('#v-cockpit .curcard [data-edcur]')")
        b.click("#v-cockpit .curcard [data-edcur]")
        b.wait("document.getElementById('curEd')")
        b.eval(f"document.getElementById('curEd').innerHTML={json.dumps(html)}")

    def editor_text(self):
        return self.b.eval("document.getElementById('curEd').innerText.trim()")

    # ── the dialog ──
    def test_the_dialog_offers_audience_and_length_with_internal_and_standard_chosen(self):
        self.open_dialog()
        b = self.b
        self.assertEqual(b.eval("[...document.querySelectorAll('#genAud [aria-pressed=true]')].map(x=>x.dataset.ga)"), ["internal"])
        self.assertEqual(b.eval("[...document.querySelectorAll('#genLen [aria-pressed=true]')].map(x=>x.dataset.gl)"), ["standard"])
        self.assertEqual(b.eval("[...document.querySelectorAll('#genLen [data-gl]')].map(x=>x.textContent)"), ["Short", "Standard", "Fuller"])

    def test_client_safe_says_what_it_uses_and_leaves_the_sources_out(self):
        self.open_dialog()
        b = self.b
        b.click("#genAud [data-ga=client]")
        self.assertIn("client-visible", b.eval("document.getElementById('genAudNote').textContent"))
        self.assertTrue(b.eval("[...document.querySelectorAll('#genSrc input')].every(i=>i.disabled)"))
        b.click("#genAud [data-ga=internal]")
        self.assertFalse(b.eval("[...document.querySelectorAll('#genSrc input')].some(i=>i.disabled)"))

    def test_the_choice_is_sent_and_remembered(self):
        self.open_dialog()
        b = self.b
        b.click("#genAud [data-ga=client]")
        b.click("#genLen [data-gl=short]")
        b.click("#genGo")
        b.wait("document.getElementById('curEd') && document.getElementById('genNotes') && !document.querySelector('#genNotes button[data-chk]:only-child')", 30)
        p = self.prompt()
        self.assertIn("Audience: client-safe.", p)
        self.assertIn("Length: Short, about 40 words.", p)
        self.assertEqual(b.eval("[localStorage.getItem('creaite-gen-aud'), localStorage.getItem('creaite-gen-len')]"), ['"client"', '"short"'])
        self.assertIn("UAT data is late", self.editor_text())

    # ── the notes ──
    def test_a_draft_gets_notes_and_the_facts_it_was_written_from(self):
        self.open_dialog()
        b = self.b
        b.click("#genGo")
        b.wait("document.querySelectorAll('#genNotes li').length>0", 30)
        notes = b.eval("[...document.querySelectorAll('#genNotes li')].map(x=>x.textContent).join(' | ')")
        self.assertIn("No date or number in the text", notes)            # the stand-in's reply has none, and the facts do
        self.assertIn("Notes on this draft", b.eval("document.getElementById('genNotes').textContent"))
        self.assertTrue(b.eval("!document.getElementById('genFacts').hidden"))
        self.assertIn("Position", b.eval("document.getElementById('genFacts').textContent"))
        self.assertTrue(b.eval("!document.querySelector('[data-cure=save]').disabled"))                     # never blocking

    def test_check_again_reads_the_editor(self):
        self.open_editor("<p>Progress is good.</p><p>ABC-A-001 is overdue.</p>")
        b = self.b
        b.click("#genNotes [data-chk]")
        b.wait("document.querySelectorAll('#genNotes li').length>0", 20)
        notes = b.eval("document.getElementById('genNotes').textContent")
        self.assertIn("Item numbers in the text", notes)
        self.assertIn("doesn't say on track, at risk or off track", notes)

    # ── Make it executive ──
    def test_make_it_executive_shows_a_draft_and_changes_nothing_until_it_is_used(self):
        self.open_editor("<p>Go-live is 20-11-2026.</p>")
        b = self.b
        b.click("#curAi button[aria-haspopup]")   # BL-301 D: Make it executive is an option of AI ▾
        b.wait("document.querySelector('#curAi [data-exec]')")
        b.click("#curAi [data-exec]")
        b.wait("document.querySelector('#genRewrite .rwbody') && document.querySelectorAll('#genRewrite .rwnotes li').length>0", 30)
        self.assertEqual(self.editor_text(), "Go-live is 20-11-2026.")                                      # unchanged
        self.assertIn("On track for 20-11-2026.", b.eval("document.querySelector('#genRewrite .rwbody').innerText"))
        self.assertIn("16-10-2026", b.eval("document.querySelector('#genRewrite .rwnotes').innerText"))   # a date the text didn't have
        self.assertIn("Go-live is 20-11-2026.", self.prompt())                                           # Alan's text went to Claude
        b.click("[data-rw=discard]")
        self.assertFalse(b.eval("!!document.getElementById('genRewrite')"))
        self.assertEqual(self.editor_text(), "Go-live is 20-11-2026.")

    def test_using_the_executive_version_replaces_the_text_and_checks_it(self):
        self.open_editor("<p>Go-live is 20-11-2026.</p>")
        b = self.b
        b.click("#curAi button[aria-haspopup]")   # BL-301 D: Make it executive is an option of AI ▾
        b.wait("document.querySelector('#curAi [data-exec]')")
        b.click("#curAi [data-exec]")
        b.wait("document.querySelector('#genRewrite .rwnotes')", 30)
        b.click("[data-rw=use]")
        self.assertIn("On track for 20-11-2026.", self.editor_text())
        self.assertFalse(b.eval("!!document.getElementById('genRewrite')"))
        self.assertTrue(b.eval("CURED.dirty"))
        b.wait("document.querySelector('#genNotes') && !CURED.checking && CURED.notes !== null", 20)

    def test_make_it_executive_needs_some_text(self):
        self.open_editor("<p><br></p>")
        self.b.click("#curAi button[aria-haspopup]")   # BL-301 D: Make it executive is an option of AI ▾
        self.b.wait("document.querySelector('#curAi [data-exec]')")
        self.b.click("#curAi [data-exec]")
        self.b.wait("document.getElementById('snack').classList.contains('on')")
        self.assertIn("Write something first", self.b.eval("document.getElementById('snack').textContent"))
        self.assertFalse(self.b.eval("!!document.getElementById('genRewrite')"))


if __name__ == "__main__":
    unittest.main()
