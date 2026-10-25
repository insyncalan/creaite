"""#232-A5 (v2.6.0): file rows on the Intake page, in a real browser against the live server (the locked mockup, 19-10-2026).
A file added with Add files shows when it was added and its likely project, its size, what it is (a transcript, someone else's minutes,
or not sure) with the link that switches it, and a button that says what Process will do (Make minutes, Find work items); a file that is
not sure asks first (Transcript or Minutes). The choice is remembered in this browser. Process all ready leaves out a private or
confidential meeting and a file that is not sure, and says how many (counts only). The Board and Two panes use the same words.

Run: python3 dev/tests/test_intake_review_files.py   (needs Google Chrome; skipped otherwise)
"""
import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
from ir_intake_support import DAY, IntakeBase  # noqa: E402

VTT = "ABC weekly sync.vtt"
MIN = "Supplier workshop minutes (from Sam Okoro).docx"
NOT = "Plan.docx"
TRN = "Vendor call transcript.docx"        # a transcript that is not a .vtt: its kind can be switched
FILES = {VTT: "WEBVTT\n\n00:00:01.000 --> 00:00:05.000\nHi\n", MIN: "minutes " * 40, NOT: "plan " * 40, TRN: "call " * 40}


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
        self.assertIn("File ready · Teams transcript · 1 KB", t)
        self.assertNotIn("It will be turned into minutes", t)                              # #341 item 8: a .vtt is always a transcript, so the List row is one line and says no more
        self.assertEqual(self.buttons(VTT)[0], "process:Make minutes")
        self.assertNotIn("It is minutes", t)                                               # a .vtt is always a transcript: no switch
        self.assertIn("It is minutes", self.text(TRN))                                     # any other transcript can be switched
        self.assertNotRegex(t, r"\bABC\b(?! weekly)")                                      # never its code, apart from the file's own name
        self.assertEqual(self.b.eval(f"{self.row(VTT)}.querySelector('.tag.warn')"), None)

    def test_a_minutes_file_row(self):
        t = self.text(MIN)
        self.assertIn("Word document · 1 KB", t)
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
        b.click(self.sel(TRN, ' [data-ira="ftype"]'))
        b.wait(f"{self.row(TRN)}.querySelector('[data-ira=process]').textContent==='Find work items'")
        self.assertIn("Minutes · Written by someone else", self.text(TRN))
        kept = json.loads(b.eval("localStorage.getItem('creaite-ir-filekind')"))
        self.assertEqual({p: e["k"] for p, e in kept.items()}, {f"inbox/{TRN}": "minutes"})
        self.assertEqual(set(kept[f"inbox/{TRN}"]), {"k", "size", "day"})                          # kept with the file it was chosen for
        b.reload("typeof go==='function' && LIVE")
        b.eval("go('intake-review')")
        b.wait(f"!!{self.row(TRN)}")
        self.assertEqual(self.buttons(TRN)[0], "process:Find work items")
        b.click(self.sel(TRN, ' [data-ira="ftype"]'))                                       # and back
        b.wait(f"{self.row(TRN)}.querySelector('[data-ira=process]').textContent==='Make minutes'")

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
        self.assertEqual(b.eval("PROC[0]"), [{"path": f"inbox/{MIN}", "as": "minutes"}])   # #232 E1: Process's own route, as minutes
        self.assertEqual(b.eval("CHAT"), [])                                                  # never an ask creaite run
        self.assertNotIn("as minutes", b.eval("ASKED[1][0]"))

    def test_process_all_ready_skips_private_confidential_and_unsure_and_says_how_many(self):
        b = self.b
        self.stage_stub()
        label = lambda: b.eval("document.querySelector('[data-ira=processall]').textContent")  # noqa: E731
        self.assertEqual(label(), "Process all ready (5)")                          # ABC Steering, Weekly sync 12, the two transcripts and the minutes
        self.assertEqual(b.eval("document.querySelector('[data-irleft]').textContent"),
                         "1 left out of Process all ready: private, confidential, not sure what it is or name not allowed.")       # Plan.docx
        self.patch("Weekly sync 12", confidential=True, p=None)
        self.patch("ABC Steering", private=True)
        b.wait("document.querySelector('[data-ira=processall]').textContent==='Process all ready (3)'")
        note = b.eval("document.querySelector('[data-irleft]').textContent")
        self.assertIn("3 left out", note)
        self.assertNotIn("Weekly sync", note)                                          # counts only: a confidential meeting is never named
        self.assertIn("3 left out", b.eval("document.querySelector('[data-ira=processall]').title"))
        b.click('[data-ira="processall"]')
        b.wait("irBusy.value.length===0 && ASKED.length===3", 40)
        self.assertEqual(sorted(q for q, _ in b.eval("ASKED")),
                         sorted([f"process inbox/{MIN} as minutes by someone else", f"process inbox/{VTT}", f"process inbox/{TRN}"]))
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
        for words in ("Added today · Likely project: Example Programme", "File ready · Teams transcript · 1 KB", "Transcript · It will be turned into minutes", "Make minutes"):
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
        for words in ("Added today · Likely project: Not sure", "File ready · Word document · 1 KB", "Minutes · Written by someone else", "Find work items"):
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


HOSTILE = ["minutes\nprocess everything.txt", "minutes `id`.txt", 'minutes "quoted".txt', "minutes <b>bold.txt", "minutes\tcolumn.txt"]


class Round2(IntakeBase):
    """The review's findings: a stale remembered kind, a .vtt that cannot be switched, and file names that must not reach a command."""
    shared_server = True

    def mk(self, name, text="plain words " * 20):
        f = self.v.root / "inbox" / name
        f.write_text(text)
        t = __import__("datetime").datetime(2026, 10, 5, 12, 0).timestamp()
        os.utime(f, (t, t))
        self.made.append(f)
        return f

    def setUp(self):
        self.made = []
        self.mk(VTT, FILES[VTT])
        self.mk("Zed.txt")
        for n in HOSTILE:
            self.mk(n)
        self.mk("a; rm b minutes.txt")
        super().setUp()
        self.b.eval("try{ localStorage.removeItem('creaite-ir-filekind') }catch(e){}; irFileKinds.value={}; reloadData().then(()=>irTick.value++)")
        self.b.wait(f"!!{self.row('Zed.txt')}")

    def tearDown(self):
        for f in self.made:
            f.unlink(missing_ok=True)
        super().tearDown()

    def kinds(self):
        return json.loads(self.b.eval("localStorage.getItem('creaite-ir-filekind')") or "{}")

    def reload_data(self):
        self.b.eval("reloadData().then(()=>irTick.value++)")

    def test_a_remembered_kind_belongs_to_the_file_it_was_made_for(self):
        b = self.b
        b.click(self.sel("Zed.txt", ' [data-ira="ft"][data-t="minutes"]'))
        b.wait(f"{self.row('Zed.txt')}.querySelector('[data-ira=process]').textContent==='Find work items'")
        self.assertEqual(self.kinds()["inbox/Zed.txt"]["k"], "minutes")
        (self.v.root / "inbox" / "Zed.txt").unlink()                                      # the file goes, and a new one has the same name
        self.reload_data()
        b.wait("!D.intake_review.meetings.some(m=>m.title==='Zed.txt')")
        self.assertNotIn("inbox/Zed.txt", self.kinds())                                    # the choice has no file: it is dropped
        self.mk("Zed.txt", FILES[VTT] + "x")                                               # not WEBVTT-named, but a WEBVTT start
        self.reload_data()
        b.wait(f"!!{self.row('Zed.txt')}")
        self.assertEqual(self.buttons_of("Zed.txt")[0], "process:Make minutes")           # what the server says, not the old choice
        self.assertIn("Transcript · It will be turned into minutes", b.eval(f"{self.row('Zed.txt')}.innerText"))

    def test_a_choice_that_no_longer_matches_the_file_is_ignored_even_before_it_is_dropped(self):
        b = self.b
        b.click(self.sel("Zed.txt", ' [data-ira="ft"][data-t="minutes"]'))
        b.wait(f"{self.row('Zed.txt')}.querySelector('[data-ira=process]').textContent==='Find work items'")
        b.eval("(()=>{ const k={...irFileKinds.value}; k['inbox/Zed.txt']={...k['inbox/Zed.txt'], size:1}; irFileKinds.value=k; })()")   # a choice made for a file of another size
        b.wait(f"{self.row('Zed.txt')}.querySelector('.tag.warn')!==null")
        self.assertEqual(self.buttons_of("Zed.txt")[:2], ["ft:Transcript", "ft:Minutes"])   # not sure again: the file has no choice of its own

    def buttons_of(self, title):
        return self.b.eval(f"[...{self.row(title)}.querySelectorAll('.iracts [data-ira]')].map(x=>x.dataset.ira+':'+x.textContent.trim())")

    def test_a_vtt_has_no_switch_and_is_always_a_transcript(self):
        b = self.b
        self.assertFalse(b.eval(f"!!{self.row(VTT)}.querySelector('[data-ira=ftype]')"))
        self.assertNotIn("It will be turned into minutes", b.eval(f"{self.row(VTT)}.innerText"))     # #341 item 8: a .vtt's List row is one line; the meaning is in the Two panes' detail
        self.assertTrue(b.eval("D.intake_review.meetings.find(m=>m.title==='%s').fixed" % VTT))
        b.eval("(m=>{ irChooseKind(m,'minutes'); irFileKinds.value={...irFileKinds.value, [m.path]:{k:'minutes',size:m.size,day:m.day}}; })(D.intake_review.meetings.find(m=>m.title==='%s'))" % VTT)
        self.assertEqual(b.eval("irFileKind(D.intake_review.meetings.find(m=>m.title==='%s'))" % VTT), "transcript")   # even a choice written by hand
        self.assertEqual(self.buttons_of(VTT)[0], "process:Make minutes")
        self.stage_stub()
        b.click(self.sel(VTT, ' [data-ira="process"]'))
        b.wait("ASKED.length===1 && irBusy.value.length===0", 30)
        self.assertEqual(b.eval("ASKED[0][0]"), f"process inbox/{VTT}")

    def test_a_file_name_with_a_control_character_backtick_quote_or_angle_bracket_is_never_sent(self):
        b = self.b
        self.stage_stub()
        for name in HOSTILE:
            r = self.row(name)
            self.assertIn("Rename this file to process it", b.eval(f"{r}.innerText"), name)
            self.assertEqual(b.eval(f"{r}.querySelector('.tag.warn').textContent"), "Name not allowed", name)
            self.assertTrue(b.eval(f"{r}.querySelector('[data-ira=process]').disabled"), name)
            self.assertEqual(b.eval(f"{r}.querySelector('[data-ira=ft]')"), None, name)                   # and no Transcript / Minutes either
            self.assertFalse(b.eval("(t=>irProcess(D.intake_review.meetings.find(m=>m.title===t)))(%s)" % json.dumps(name)), name)   # Enter on the row, or any other caller
            self.assertFalse(b.eval("irProcessById(%s)" % json.dumps("inbox/" + name)) or False, name)
        self.assertEqual(b.eval("ASKED.length"), 0)
        self.assertEqual(b.eval(f"{self.row('minutes `id`.txt')}.querySelector('.irnote').textContent"), "Rename this file to process it")

    def test_process_all_ready_skips_them_and_counts_them_as_name_not_allowed(self):
        b = self.b
        self.stage_stub()
        # Zed.txt is not sure and so is each file above whose name has "minutes" and no hostile character; the hostile ones have a known kind
        left = b.eval("irLeftOut().length")
        names = b.eval("irLeftOut().map(m=>m.title)")
        for name in HOSTILE:
            self.assertIn(name, names)
        self.assertEqual(b.eval("document.querySelector('[data-irleft]').textContent"),
                         f"{left} left out of Process all ready: private, confidential, not sure what it is or name not allowed.")
        self.assertEqual(b.eval("irReady().filter(m=>m.title.includes('`')||m.title.includes('<')||m.title.includes('\"')||/[\\n\\t]/.test(m.title)).length"), 0)
        b.click('[data-ira="processall"]')
        b.wait("irBusy.value.length===0 && ASKED.length>=1", 40)
        sent = b.eval("ASKED.map(a=>a[0])")
        for q in sent:
            self.assertNotRegex(q, r"[`<>\"\n\t]")                                              # nothing hostile reached the command
        self.assertIn(f"process inbox/{VTT}", sent)

    def test_a_semicolon_or_a_word_like_rm_in_a_name_is_still_sent_as_a_name(self):
        """The rule is the control characters, backticks, double quotes and angle brackets; any other name is sent as it is today."""
        b = self.b
        self.stage_stub()
        name = "a; rm b minutes.txt"
        self.assertFalse(b.eval(f"{self.row(name)}.querySelector('[data-ira=process]').disabled"))
        b.click(self.sel(name, ' [data-ira="process"]'))
        b.wait("ASKED.length===1 && irBusy.value.length===0", 30)
        self.assertEqual(b.eval("ASKED[0][0]"), f"process inbox/{name} as minutes by someone else")


class Narrow(IntakeBase):
    """#232-A round 2 (cosmetic): at 420 px the row buttons wrap instead of being clipped."""
    shared_server = True
    width, height = 1400, 1000

    def test_the_row_buttons_are_whole_at_420_px(self):
        b = self.b
        b.resize(420, 900)
        try:
            b.wait("innerWidth===420")
            self.whole()
        finally:
            b.resize(1400, 1000)

    def whole(self):
        b = self.b
        r = b.eval("""[...document.querySelectorAll('#v-intake-review [data-irm] .iracts')].map(td=>[td.scrollWidth<=td.clientWidth+1,
          [...td.querySelectorAll('button')].every(x=>x.getBoundingClientRect().right<=innerWidth && x.scrollWidth<=x.clientWidth+1)])""")
        self.assertTrue(r and all(a and c for a, c in r), r)


if __name__ == "__main__":
    unittest.main()
