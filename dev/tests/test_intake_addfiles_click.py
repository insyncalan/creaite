"""#307 (v2.6.1): the Add files button on the Intake page opens the file chooser, and files chosen reach Intake with a plain message.

Run: python3 dev/tests/test_intake_addfiles_click.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ir_intake_support import IntakeBase  # noqa: E402


class AddFilesClick(IntakeBase):
    shared_server = True

    def test_a_real_click_reaches_the_file_input_and_is_not_cancelled(self):
        b = self.b
        b.eval("""window.INCLICKS=[]; window.addEventListener('click',e=>{ if(e.target&&e.target.type==='file') INCLICKS.push([e.defaultPrevented, e.isTrusted]); }); 0""")
        b.call("Page.enable")
        b.call("Page.setInterceptFileChooserDialog", enabled=True)
        b.click("[data-irpick]")
        b.pump(0.5)
        self.assertTrue([e for e in b.events if e.get("method") == "Page.fileChooserOpened"], "no file chooser opened")
        self.assertEqual(b.eval("INCLICKS.length"), 1, "the click never reached the file input")
        self.assertEqual(b.eval("document.querySelectorAll('body > input[type=file]').length"), 1)
        self.assertEqual(b.eval("INCLICKS[0][0]"), False, "something cancelled the input's click, so no chooser opens")

    def test_files_chosen_are_added_and_said_in_words(self):
        b = self.b
        f = self.v.root.parent / "Chosen minutes.txt"
        f.write_text("minutes " * 30)
        self.addCleanup(f.unlink, missing_ok=True)
        self.addCleanup((self.v.root / "inbox" / "Chosen minutes.txt").unlink, missing_ok=True)
        b.call("Page.enable")
        b.call("Page.setInterceptFileChooserDialog", enabled=True)       # the chooser stays open (headless would cancel it, which removes the input)
        b.click("[data-irpick]")
        b.set_files("body > input[type=file]", [f])
        b.wait("D.intake_review.meetings.some(m=>m.title==='Chosen minutes.txt')", 30)
        self.assertIn("1 file added to Intake", b.eval("document.body.innerText"))

    def test_failed_files_are_named_with_why_and_stay_until_dismissed(self):
        """#307 A4: a refused file is named with its reason on the page, not in a toast the next file replaces."""
        b = self.b
        bad, empty, good = (self.v.root.parent / n for n in ("notes.xlsx", "empty.vtt", "Kept minutes.txt"))
        bad.write_bytes(b"x" * 40)
        empty.write_bytes(b"")
        good.write_text("minutes " * 30)
        for f in (bad, empty, good):
            self.addCleanup(f.unlink, missing_ok=True)
        self.addCleanup((self.v.root / "inbox" / "Kept minutes.txt").unlink, missing_ok=True)
        b.call("Page.enable")
        b.call("Page.setInterceptFileChooserDialog", enabled=True)
        b.click("[data-irpick]")
        b.set_files("body > input[type=file]", [bad, empty, good])
        b.wait("D.intake_review.meetings.some(m=>m.title==='Kept minutes.txt')", 30)
        b.wait("document.querySelector('[data-iraddfail]')", 10)
        note = b.eval("document.querySelector('[data-iraddfail]').innerText")
        self.assertIn("2 files weren't added", note)
        self.assertIn("notes.xlsx:", note)                       # each failed file by name ...
        self.assertIn("empty.vtt:", note)
        self.assertIn("not this kind", note)                    # ... and why
        self.assertIn("empty", note.split("empty.vtt:")[1])
        for word in (".vtt,", "tracker", "live server", "staged"):
            self.assertNotIn(word, note)
        b.pump(7)                                                # longer than any toast
        self.assertIn("notes.xlsx:", b.eval("document.querySelector('[data-iraddfail]').innerText"), "the note vanished with the toast")
        b.click("[data-ira=dismissaddfail]")
        self.assertFalse(b.eval("!!document.querySelector('[data-iraddfail]')"))


if __name__ == "__main__":
    unittest.main()
