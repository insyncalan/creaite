"""BL-162: click the Current state card's title on a project page and rename it, in a real browser against the real live server.

Run: python3 dev/tests/test_current_state_title.py   (needs Google Chrome; skipped otherwise)

The title is a label for the dashboard only, kept per project as "- **Current state title:** <words>" in the project's CLAUDE.md
beside the client-report rhythm. The "## Current state" section keeps its name, so the reports and Generate still find it.
Saving follows setRhythm: a backup in system/backups/files/, a line in settings-log.jsonl, and Undo in the snack.
"""
import json
import os
import re
import sys
import unittest
from pathlib import Path

os.environ.setdefault("CREAITE_NO_LAUNCH", "1")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

LINE = re.compile(r"^- \*\*Current state title:\*\*[^\n]*$", re.M)


class CurrentStateTitle(LiveBrowserCase):
    width, height = 1280, 900

    # ── helpers ──
    def memory(self, code="ABC"):
        return next((self.v.root / "projects").glob(f"{code} */CLAUDE.md"))

    def section(self, code="ABC"):
        return re.search(r"^## Current state\n.*?(?=^## |\Z)", self.memory(code).read_text(), re.M | re.S).group(0)

    def open_page(self, code="ABC"):
        b = self.b
        b.eval(f"go('cockpit','{code}')")
        b.wait("document.querySelector('#v-cockpit .curcard h2 .cstbtn')")

    def heading(self):
        return self.b.eval("document.querySelector('#v-cockpit .curcard>h2').textContent.trim()")

    def rename(self, words, code="ABC", how="Enter"):
        b = self.b
        self.open_page(code)
        b.click("#v-cockpit .cstbtn")
        b.wait("document.activeElement&&document.activeElement.classList.contains('cstin')")
        b.key("Backspace")
        if words:
            b.type(words)
        if how == "Enter":
            b.key("Enter")
        else:
            b.eval("document.activeElement.blur()")
        b.wait("document.querySelector('#v-cockpit .curcard>h2 .cstbtn')")
        b.wait("!document.getElementById('snack').textContent.includes('Saving')")

    def log(self):
        p = self.v.root / "system/config/settings-log.jsonl"
        return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []

    # ── tests ──
    def test_rename_saves_the_line_beside_the_rhythm_and_logs_it(self):
        before_section = self.section()
        self.rename("Where we are")
        self.assertEqual(self.heading(), "Where we are")
        text = self.memory().read_text()
        self.assertIn("- **Client report rhythm:** fortnightly\n- **Current state title:** Where we are\n", text)
        self.assertEqual(self.section(), before_section)                       # the section, its words and its images untouched
        self.assertIn("![Delivery plan](images/plan.png)", self.section())
        backups = list((self.v.root / "system/backups/files").glob("ABC-CLAUDE-*.md"))
        self.assertEqual(len(backups), 1)
        self.assertNotIn("Current state title", backups[0].read_text())
        last = self.log()[-1]
        self.assertEqual((last["key"], last["old"], last["new"]), ("current_state_title.ABC", "Current state", "Where we are"))
        # the page built afresh reads it back (build_dashboard.memory)
        self.b.reload(wait_for="typeof go==='function' && LIVE")
        self.open_page()
        self.assertEqual(self.heading(), "Where we are")

    def test_leaving_the_box_saves_too(self):
        self.rename("Status", how="blur")
        self.assertEqual(self.heading(), "Status")
        self.assertIn("**Current state title:** Status", self.memory().read_text())

    def test_escape_cancels(self):
        b = self.b
        before = self.memory().read_text()
        self.open_page()
        b.click("#v-cockpit .cstbtn")
        b.wait("document.activeElement&&document.activeElement.classList.contains('cstin')")
        b.type("Something else")
        b.key("Escape")
        b.wait("document.querySelector('#v-cockpit .curcard>h2 .cstbtn')")
        self.assertEqual(self.heading(), "Current state")
        self.assertEqual(self.memory().read_text(), before)
        self.assertTrue(b.eval("document.activeElement.classList.contains('cstbtn')"))      # focus back on the title
        self.assertEqual(b.eval("VIEW"), "cockpit")                                          # Esc did nothing else

    def test_empty_or_default_puts_the_default_back_and_removes_the_line(self):
        self.rename("Where we are")
        self.rename("")
        self.assertEqual(self.heading(), "Current state")
        self.assertIsNone(LINE.search(self.memory().read_text()))
        self.rename("Where we are")
        self.rename("current state")                                          # the default words, in any case
        self.assertEqual(self.heading(), "Current state")
        self.assertIsNone(LINE.search(self.memory().read_text()))

    def test_forty_characters_at_most(self):
        b = self.b
        self.open_page()
        b.click("#v-cockpit .cstbtn")
        self.assertEqual(b.eval("document.activeElement.maxLength"), 40)
        self.assertEqual(b.eval("document.activeElement.getAttribute('aria-label')"), "Title of this card")
        b.key("Escape")
        # a longer value (pasted, or set some other way) is cut to 40 on save, and the builder caps a hand-edited line too
        self.rename("x" * 39)
        b.eval("csSave('ABC','" + "y" * 55 + "')")
        b.wait("csTitle('ABC').length===40")
        self.assertEqual(LINE.search(self.memory().read_text()).group(0), "- **Current state title:** " + "y" * 40)
        sys.path.insert(0, str(self.v.root / "system/scripts"))
        import build_dashboard
        self.assertEqual(build_dashboard.cs_title("- **Current state title:** **" + "z" * 50 + "**"), "z" * 40)
        self.assertEqual(build_dashboard.cs_title("- **Current state title:**   "), "Current state")
        self.assertEqual(build_dashboard.cs_title("nothing here"), "Current state")

    def test_undo_restores_the_file(self):
        b = self.b
        before = self.memory().read_text()
        self.rename("Where we are")
        b.wait("document.getElementById('snack').classList.contains('on')")
        b.click("#snackU")
        b.wait("csTitle('ABC')==='Current state'")
        b.wait("document.querySelector('#v-cockpit .curcard>h2').textContent.trim()==='Current state'")
        self.assertEqual(self.memory().read_text(), before)
        last = self.log()[-1]
        self.assertEqual((last["old"], last["new"]), ("Where we are", "Current state"))

    def test_a_second_project_keeps_its_own_title(self):
        (self.v.root / "projects/DEF Digital Enablement/CLAUDE.md").write_text("# DEF — Digital Enablement\n\n## Brief\n\n- **Objective:** a pilot.\n")
        self.rename("Where we are", "ABC")
        self.rename("Status", "DEF")
        self.open_page("ABC")
        self.assertEqual(self.heading(), "Where we are")
        self.open_page("DEF")
        self.assertEqual(self.heading(), "Status")
        self.assertIn("**Current state title:** Where we are", self.memory("ABC").read_text())
        self.assertIn("**Current state title:** Status", self.memory("DEF").read_text())

    def test_the_line_is_added_when_missing(self):
        """No rhythm line: the title goes directly above ## Current state; the section is untouched."""
        p = self.memory()
        p.write_text(p.read_text().replace("- **Client report rhythm:** fortnightly\n", ""))
        before_section = self.section()
        self.rename("Where we are")
        text = p.read_text()
        self.assertIn("- **Current state title:** Where we are\n\n## Current state\n", text)
        self.assertEqual(self.section(), before_section)
        self.rename("Status")                                                  # an existing line is replaced, never repeated
        self.assertEqual(len(LINE.findall(p.read_text())), 1)

    def test_reports_and_generate_still_find_the_section(self):
        self.rename("Where we are")
        sys.path.insert(0, str(self.v.root / "system/scripts"))
        os.chdir(self.v.root)
        import importlib
        import paths
        importlib.reload(paths)
        import build_dashboard
        import report
        md = self.memory().read_text()
        self.assertIn("Build is two weeks behind", report.saved_current(md))           # the weekly report's reader
        mem = build_dashboard.memory(self.memory().parent)                                # what Generate drafts from
        self.assertIn("Build is two weeks behind", mem["current"])
        self.assertEqual(mem["cstitle"], "Where we are")
        imgs = report.memory_images(self.memory().parent)
        self.assertEqual([i["caption"] for i in imgs], ["Delivery plan"])

    def test_the_heading_stays_a_heading_and_the_dialog_and_editor_use_the_title(self):
        b = self.b
        self.rename("Where we are")
        self.assertEqual(b.eval("document.querySelector('#v-cockpit .curcard .cstbtn').parentElement.tagName"), "H2")
        self.assertEqual(b.eval("document.querySelector('#v-cockpit .cstbtn').dataset.tip"), "Rename this title")
        self.assertEqual(b.eval("document.querySelector('#v-cockpit .curcard').getAttribute('aria-labelledby')"), "csHead")
        b.eval("openGen('ABC')")
        self.assertEqual(b.eval("document.querySelector('#genDlg h2').textContent"), "Generate: Where we are")
        b.eval("document.getElementById('genDlg').close()")
        b.click("#v-cockpit .curcard [data-edcur]")
        b.wait("document.getElementById('curEd')")
        self.assertEqual(b.eval("document.getElementById('curEd').getAttribute('aria-label')"), "Where we are, left pane")
        # while the editor is open, the title is plain text (one thing at a time)
        self.assertFalse(b.eval("!!document.querySelector('#v-cockpit .cstbtn')"))
        self.assertEqual(self.heading(), "Where we are")

    def test_keyboard_only(self):
        b = self.b
        self.open_page()
        b.eval("document.querySelector('#v-cockpit .cstbtn').focus()")
        b.key("Enter")
        b.wait("document.activeElement&&document.activeElement.classList.contains('cstin')")
        self.assertTrue(b.eval("document.activeElement.selectionStart===0&&document.activeElement.selectionEnd===13"))  # the words selected
        b.type("Where we are")
        b.key("Enter")
        b.wait("document.activeElement&&document.activeElement.classList.contains('cstbtn')")
        self.assertEqual(self.heading(), "Where we are")
        self.assertIn("**Current state title:** Where we are", self.memory().read_text())


if __name__ == "__main__":
    unittest.main()
