"""#232-A5 (v2.6.0): file rows on the Intake page, in a real browser against the live server (the locked mockup, 19-10-2026).
A file added with Add files shows when it was added and its likely project, its size, what it is (a transcript, someone else's minutes,
or not sure) with the link that switches it, and a button that says what Process will do (Make minutes, Find work items); a file that is
not sure asks first (Transcript or Minutes). The choice is remembered in this browser. Process all ready leaves out a private or
confidential meeting and a file that is not sure, and says how many (counts only). The Board and Two panes use the same words.

Run: python3 dev/tests/test_intake_review_files.py   (needs Google Chrome; skipped otherwise)
"""
import json
import os
import shutil
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
from ir_intake_support import DAY, IntakeBase  # noqa: E402

VTT = "ABC weekly sync.vtt"
MIN = "Supplier workshop minutes (from Sam Okoro).docx"
NOT = "Plan.docx"
FILES = {VTT: "WEBVTT\n\n00:00:01.000 --> 00:00:05.000\nHi\n", MIN: "minutes " * 40, NOT: "plan " * 40}


class FileRows(IntakeBase):
    shared_server = True

    def setUp(self):
        for name, text in FILES.items():
            f = self.v.root / "inbox" / name
            f.write_text(text)
            t = __import__("datetime").datetime(2026, 10, 5, 12, 0).timestamp()
            os.utime(f, (t, t))
        super().setUp()
        self.b.eval("try{ localStorage.removeItem('creaite-ir-filekind') }catch(e){}; irFileKinds.value={}; irTick.value++")
        self.b.wait(f"!!{self.row(NOT)}")

    def tearDown(self):
        for name in (*FILES, "Again.vtt"):
            (self.v.root / "inbox" / name).unlink(missing_ok=True)
        for f in (self.v.root / "projects").glob("*/transcripts/Again.vtt"):
            f.unlink(missing_ok=True)
        super().tearDown()

    def text(self, title):
        return self.b.eval(f"{self.row(title)}.innerText")

    def buttons(self, title):
        return self.b.eval(f"[...{self.row(title)}.querySelectorAll('.iracts [data-ira]')].map(x=>x.dataset.ira+':'+x.textContent.trim())")

    # -- the rows
    def test_a_transcript_file_row(self):
        t = self.text(VTT)
        self.assertIn("Added today · Likely project: Example Programme", t)              # the project by its name
        self.assertIn("File ready · .vtt · 1 KB", t)
        self.assertIn("Transcript · It will be turned into minutes, then checked for work items.", t)
        self.assertIn("It is minutes", t)
        self.assertEqual(self.buttons(VTT)[0], "process:Make minutes")
        self.assertNotRegex(t, r"\bABC\b(?! weekly)")                                      # never its code, apart from the file's own name
        self.assertEqual(self.b.eval(f"{self.row(VTT)}.querySelector('.tag.warn')"), None)

    def test_a_minutes_file_row(self):
        t = self.text(MIN)
        self.assertIn(".docx · 1 KB", t)
        self.assertIn("Minutes · Written by someone else: it will be checked for work items, and no new minutes are drafted.", t)
        self.assertIn("It is a transcript", t)
        self.assertEqual(self.buttons(MIN)[0], "process:Find work items")
        self.assertIn("Likely project: Not sure", t)

    def test_a_file_that_is_not_sure_asks_before_it_can_be_processed(self):
        b = self.b
        t = self.text(NOT)
        self.assertIn("Not sure · Is this a transcript or minutes?", t)
        self.assertEqual(self.buttons(NOT)[:2], ["ft:Transcript", "ft:Minutes"])
        self.assertFalse(b.eval(f"!!{self.row(NOT)}.querySelector('[data-ira=process]')"))
        self.assertEqual(b.eval(f"{self.row(NOT)}.querySelector('.tag.warn').textContent"), "Not sure")
        self.stage_stub()
        b.eval("(m=>irProcess(m))(D.intake_review.meetings.find(m=>m.title==='%s'))" % NOT)                    # Enter on the row does the same
        b.wait(f"/Say whether it is a transcript or minutes first/.test({self.row(NOT)}.innerText)")
        self.assertEqual(b.eval("ASKED.length"), 0)

    def test_the_switch_changes_the_button_word_and_survives_a_reload(self):
        b = self.b
        b.click(self.sel(VTT, ' [data-ira="ftype"]'))
        b.wait(f"{self.row(VTT)}.querySelector('[data-ira=process]').textContent==='Find work items'")
        self.assertIn("Minutes · Written by someone else", self.text(VTT))
        self.assertEqual(json.loads(b.eval("localStorage.getItem('creaite-ir-filekind')")), {f"inbox/{VTT}": "minutes"})
        b.reload("typeof go==='function' && LIVE")
        b.eval("go('intake-review')")
        b.wait(f"!!{self.row(VTT)}")
        self.assertEqual(self.buttons(VTT)[0], "process:Find work items")
        b.click(self.sel(VTT, ' [data-ira="ftype"]'))                                       # and back
        b.wait(f"{self.row(VTT)}.querySelector('[data-ira=process]').textContent==='Make minutes'")

    def test_choosing_a_type_makes_the_file_ready_and_counts_it(self):
        b = self.b
        c = b.eval("irLiveCounts()")
        self.assertEqual(c["need_type"], 1)
        self.assertEqual(c["badge"], c["ready"] + c["to_approve"])
        self.assertIn("1 need a type", b.eval("document.querySelector('[data-irstage=arrived] .icsub').textContent"))
        b.click(self.sel(NOT, ' [data-ira="ft"][data-t="minutes"]'))
        b.wait(f"{self.row(NOT)}.querySelector('[data-ira=process]').textContent==='Find work items'")
        c2 = b.eval("irLiveCounts()")
        self.assertEqual((c2["ready"], c2["need_type"], c2["badge"]), (c["ready"] + 1, 0, c["badge"] + 1))
        self.assertNotIn("need a type", b.eval("document.querySelector('[data-irstage=arrived] .icsub').textContent"))

    # -- Process
    def test_process_sends_the_command_that_fits_the_kind_and_the_row_says_what_it_is_doing(self):
        b = self.b
        self.stage_stub()
        b.eval("GATE=new Promise(r=>{ window.RELEASE=r; }); 0")
        b.click(self.sel(MIN, ' [data-ira="process"]'))
        b.wait(f"{self.row(MIN)}.dataset.state==='running'")
        self.assertIn("Reading for work items", self.text(MIN))
        self.assertEqual(b.eval(f"{self.row(MIN)}.querySelector('.icprog').getAttribute('aria-label')"), "Reading for work items")
        b.eval("RELEASE()")
        b.wait("irBusy.value.length===0", 30)
        b.eval("GATE=new Promise(r=>{ window.RELEASE=r; }); 0")
        b.click(self.sel(VTT, ' [data-ira="process"]'))
        b.wait(f"{self.row(VTT)}.dataset.state==='running'")
        self.assertIn("Drafting in the background", self.text(VTT))
        b.eval("RELEASE()")
        b.wait("irBusy.value.length===0", 30)
        self.assertEqual([q for q, _ in b.eval("ASKED")],
                         [f"process inbox/{MIN} as minutes by someone else", f"process inbox/{VTT}"])
        self.assertIn("minutes by someone else", b.eval("ASKED[0][1]"))
        self.assertNotIn("as minutes", b.eval("ASKED[1][0]"))

    def test_process_all_ready_skips_private_confidential_and_unsure_and_says_how_many(self):
        b = self.b
        self.stage_stub()
        label = lambda: b.eval("document.querySelector('[data-ira=processall]').textContent")  # noqa: E731
        self.assertEqual(label(), "Process all ready (4)")                          # ABC Steering, Weekly sync 12, the transcript and the minutes
        self.assertEqual(b.eval("document.querySelector('[data-irleft]').textContent"),
                         "1 left out of Process all ready: private, confidential or not sure what it is.")       # Plan.docx
        self.patch("Weekly sync 12", confidential=True, p=None)
        self.patch("ABC Steering", private=True)
        b.wait("document.querySelector('[data-ira=processall]').textContent==='Process all ready (2)'")
        note = b.eval("document.querySelector('[data-irleft]').textContent")
        self.assertIn("3 left out", note)
        self.assertNotIn("Weekly sync", note)                                          # counts only: a confidential meeting is never named
        self.assertIn("3 left out", b.eval("document.querySelector('[data-ira=processall]').title"))
        b.click('[data-ira="processall"]')
        b.wait("irBusy.value.length===0 && ASKED.length===2", 40)
        self.assertEqual(sorted(q for q, _ in b.eval("ASKED")),
                         sorted([f"process inbox/{MIN} as minutes by someone else", f"process inbox/{VTT}"]))
        b.wait("/3 left out/.test(document.getElementById('snackT').textContent)")
        snack = b.eval("document.getElementById('snackT').textContent")
        self.assertNotIn("Weekly sync", snack)
        self.assertNotIn("Steering", snack)

    def test_an_explicit_process_on_a_confidential_row_still_works(self):
        b = self.b
        self.stage_stub()
        self.patch("Weekly sync 12", confidential=True, p=None)
        b.wait(f"!!{self.row('Weekly sync 12')}.querySelector('[data-ira=process]')")
        b.click(self.sel("Weekly sync 12", ' [data-ira="process"]'))
        b.wait("ASKED.length===1 && irBusy.value.length===0", 30)
        self.assertEqual(b.eval("ASKED[0][0]"), f"process inbox/{DAY} Weekly sync 12.vtt")

    # -- the other views
    def test_the_board_and_two_panes_use_the_same_words(self):
        b = self.b
        b.eval("document.querySelector('[data-irview=board]').click()")
        b.wait(f"!!document.querySelector('[data-ircol=arrived] [data-irm=\"' + D.intake_review.meetings.find(m=>m.title==='{VTT}').id + '\"]')")
        card = lambda title: b.eval(f"document.querySelector('[data-ircol=arrived] [data-irm=\"' + D.intake_review.meetings.find(m=>m.title==={json.dumps(title)}).id + '\"]').innerText")  # noqa: E731
        t = card(VTT)
        for words in ("Added today · Likely project: Example Programme", "File ready · .vtt · 1 KB", "Transcript · It will be turned into minutes", "Make minutes"):
            self.assertIn(words, t)
        n = card(NOT)
        self.assertIn("Not sure · Is this a transcript or minutes?", n)
        self.assertIn("Transcript", n)
        self.assertIn("Minutes", n)
        b.eval("document.querySelector('[data-irview=two]').click()")
        mid = b.eval(f"D.intake_review.meetings.find(m=>m.title==={json.dumps(MIN)}).id")
        b.wait(f"!!document.querySelector('[data-irm=\"{mid}\"]')")
        b.eval(f"document.querySelector('[data-irm=\"{mid}\"]').click()")
        b.wait(f"document.querySelector('[data-irdet]').dataset.irdet==={json.dumps(mid)}")
        d = b.eval("document.querySelector('[data-irdet]').innerText")
        for words in ("Added today · Likely project: Not sure", "File ready · .docx · 1 KB", "Minutes · Written by someone else", "Find work items"):
            self.assertIn(words, d)
        b.eval("document.querySelector('[data-irview=list]').click()")

    # -- a copy already filed
    def test_a_file_already_filed_is_a_done_row_with_remove_and_undo(self):
        b = self.b
        text = "WEBVTT\n\n00:00:01.000 --> 00:00:05.000\nAgain\n"
        folder = next((self.v.root / "projects").glob("ABC*")) / "transcripts"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "Again.vtt").write_text(text)
        f = self.v.root / "inbox" / "Again.vtt"
        f.write_text(text)
        t = __import__("datetime").datetime(2026, 10, 5, 12, 0).timestamp()
        os.utime(f, (t, t))
        b.eval("reloadData().then(()=>irTick.value++)")
        b.wait(f"!!{self.row('Again.vtt')}")
        r = self.text("Again.vtt")
        self.assertIn("Already processed", r)
        self.assertEqual(b.eval(f"{self.row('Again.vtt')}.dataset.stage"), "approved")
        self.assertEqual(self.buttons("Again.vtt"), ["removefile:Remove"])
        self.assertIn("Done", r)
        b.click(self.sel("Again.vtt", ' [data-ira="removefile"]'))
        b.wait("!D.intake_review.meetings.some(m=>m.title==='Again.vtt')", 20)
        self.assertFalse(f.exists())
        b.wait("/Removed Again.vtt/.test(document.getElementById('snackT').textContent)")
        b.click("#snackU")
        b.wait("D.intake_review.meetings.some(m=>m.title==='Again.vtt' && m.already)", 20)
        self.assertTrue(f.exists())


if __name__ == "__main__":
    unittest.main()
