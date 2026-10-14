"""BL-42 phase 3 and BL-104 in the browser (Sprint 4b): Calendar Import shows what the sweep found for each meeting, highlights the
meetings with a transcript, and loads them through the run engine. A real browser against the real live server; the run is a
stand-in `claude` replaying fixture tool results (dev/tests/test_transcripts.py), so Microsoft 365 is never called.

Run: python3 dev/tests/test_transcripts_ui.py   (needs Google Chrome; skipped otherwise)
"""
import json
import re
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase, pin_page_clock, theme_names  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_meetings import week_calendar  # noqa: E402
from test_transcripts import DAY, NOW, STUB, route_steps, event, read, transcript_result  # noqa: E402


class Case(LiveBrowserCase):
    width, height = 1500, 1000

    @classmethod
    def load(cls, v):
        populate(v)
        week_calendar(v)
        cal = json.loads((v.root / "system/staging/calendar.json").read_text())
        cal["days"][DAY] += [{"id": "ev-room", "start": "13:00", "end": "14:00", "title": "Room 4 workshop", "teams": False, "all_day": False},
                             {"id": "ev-done", "start": "16:00", "end": "17:00", "title": "Vendor review", "teams": True, "all_day": False}]
        (v.root / "system/staging/calendar.json").write_text(json.dumps(cal))
        (v.root / "system/processed.txt").write_text(f"{DAY} | calendar:ev-done | projects/x | 1\n")
        now = f"{date.today().isoformat()} 07:00"
        (v.root / "system/staging/transcripts.json").write_text(json.dumps({"version": 1, "checked": {
            "ev-1": {"status": "available", "uri": "meeting-transcript:///a", "count": 1, "checked": now},
            "ev-2": {"status": "not_transcribed", "uri": "meeting-transcript:///b", "count": 0, "checked": now},
            "ev-room": {"status": "none", "checked": now},
            "ev-done": {"status": "available", "uri": "meeting-transcript:///c", "count": 1, "checked": now}}}))
        fake = v.root / "fake_claude.py"
        fake.write_text(STUB)
        fake.chmod(0o755)

    @classmethod
    def server_env(cls):
        return {"CREAITE_CLAUDE": str(cls.v.root / "fake_claude.py"), "CREAITE_NOW": NOW}

    def setUp(self):
        super().setUp()
        pin_page_clock(self.b, NOW)            # the page's clock too: on a Monday DAY is today, and its meetings must be over

    def script(self, steps):
        (self.v.root / "stub_script.json").write_text(json.dumps(steps))

    def open_intake(self):
        b = self.b
        b.eval("go('inbox')")
        b.wait("document.querySelector('#mtgBody tr[data-mid]')")
        return b

    def row(self, eid):
        return f'#mtgBody tr[data-mid="{eid}"]'

    def classes(self, eid):
        return self.b.eval(f"document.querySelector('{self.row(eid)}').className")

    def inbox(self):
        """What a load wrote: the sample files populate() puts in the inbox are left out."""
        return sorted(p.name for p in (self.v.root / "inbox").iterdir() if p.name.startswith(DAY))


class Highlight(Case):
    shared_server = True

    def test_a_transcript_that_is_not_processed_stands_out(self):
        self.open_intake()
        self.assertIn("mtgtx", self.classes("ev-1"))
        self.assertEqual(self.b.eval(f"document.querySelector('{self.row('ev-1')} .txbadge').textContent"), "Transcript")      # words, not only colour
        self.assertIn("Transcript available", self.b.eval(f"document.querySelector('{self.row('ev-1')}').cells[7].innerText"))
        bar = self.b.eval(f"getComputedStyle(document.querySelector('{self.row('ev-1')} td')).boxShadow")
        self.assertIn("inset", bar)                                                                                                # the accent bar
        plain = self.b.eval(f"getComputedStyle(document.querySelector('{self.row('ev-2')} td')).backgroundColor")
        tint = self.b.eval(f"getComputedStyle(document.querySelector('{self.row('ev-1')} td')).backgroundColor")
        self.assertNotEqual(plain, tint)

    def test_the_others_are_muted_and_a_processed_one_is_quiet(self):
        self.open_intake()
        for eid, label in (("ev-2", "Not transcribed"), ("ev-room", "No transcript")):
            self.assertIn("mtgmute", self.classes(eid), eid)
            self.assertNotIn("mtgtx", self.classes(eid))
            self.assertIn(label, self.b.eval(f"document.querySelector('{self.row(eid)}').cells[7].innerText"))
        self.assertIn("mtgdone", self.classes("ev-done"))                         # processed: quiet, even though a transcript exists
        self.assertNotIn("mtgtx", self.classes("ev-done"))
        self.assertEqual(self.b.eval(f"document.querySelectorAll('{self.row('ev-done')} .txbadge').length"), 0)
        self.assertIn("Already processed", self.b.eval(f"document.querySelector('{self.row('ev-done')}').cells[6].innerText"))

    def test_the_chip_shows_only_meetings_with_transcripts_and_all_brings_the_rest_back(self):
        b = self.open_intake()
        every = b.eval("document.querySelectorAll('#mtgBody tr[data-mid]').length")
        self.assertEqual(b.eval("document.querySelector('#mtgChips [data-show=tx]').textContent"), "With transcripts · 1")
        b.click('#mtgChips [data-show="tx"]')
        b.wait("document.querySelectorAll('#mtgBody tr[data-mid]').length===1")
        self.assertEqual(b.eval("document.querySelector('#mtgBody tr[data-mid]').dataset.mid"), "ev-1")
        self.assertEqual(b.eval("document.querySelector('#mtgChips [data-show=tx]').getAttribute('aria-pressed')"), "true")
        self.assertEqual(b.eval("document.querySelector('#mtgBody .mtgclr').textContent"), "Clear day · 1")       # only what is listed
        b.click('#mtgChips [data-show="all"]')
        b.wait(f"document.querySelectorAll('#mtgBody tr[data-mid]').length==={every}")

    def test_select_with_transcripts_ticks_only_those_and_enables_the_load_buttons(self):
        b = self.open_intake()
        b.click("#mtgTx")
        self.assertEqual(b.eval("[...MSEL]"), ["ev-1"])
        self.assertEqual(b.eval("document.getElementById('mtgLoad').textContent"), "Load 1 into inbox")
        self.assertIsNone(b.eval("document.getElementById('mtgLoadGo')"))                 # BL-119: Load and process is gone
        self.assertEqual(b.eval("document.getElementById('mtgGo').textContent"), "Process 1 selected")
        self.assertFalse(b.eval("document.getElementById('mtgLoad').disabled"))
        # a ticked row keeps its own, stronger look
        ticked = b.eval(f"getComputedStyle(document.querySelector('{self.row('ev-1')} td')).backgroundColor")
        b.click("#mtgTx")
        b.eval("MSEL.clear(); renderMeetings()")
        unticked = b.eval(f"getComputedStyle(document.querySelector('{self.row('ev-1')} td')).backgroundColor")
        self.assertNotEqual(ticked, unticked)

    def test_loading_is_refused_for_meetings_without_a_transcript(self):
        b = self.open_intake()
        b.eval("MSEL.add('ev-2'); MSEL.add('ev-room'); renderMeetings()")
        self.assertTrue(b.eval("document.getElementById('mtgLoad').disabled"))     # Not transcribed, No transcript: nothing to load

    def test_the_tint_reads_in_every_theme_and_mode(self):
        b = self.open_intake()

        def rgb(text):
            nums = [float(x) for x in re.findall(r"[\d.]+", text)[:3]]
            return [n * 255 if text.startswith("color(") else n for n in nums]

        def lum(c):
            f = lambda v: (v / 255) / 12.92 if v / 255 <= 0.03928 else (((v / 255) + 0.055) / 1.055) ** 2.4  # noqa: E731
            return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])
        for palette in theme_names():
            for mode in ("Light", "Dark"):
                b.eval(f"S.palette={palette!r}; S.theme={mode!r}; applyTheme()")
                b.pump(0.3)
                bg, ink = b.eval(f"(()=>{{ const td=document.querySelector('{self.row('ev-1')} .title'), c=getComputedStyle(td); return [c.backgroundColor, c.color]; }})()")
                a, c = lum(rgb(bg)), lum(rgb(ink))
                ratio = (max(a, c) + 0.05) / (min(a, c) + 0.05)
                self.assertGreaterEqual(ratio, 4.5, (palette, mode, bg, ink, ratio))


class Loading(Case):
    def test_load_into_inbox_writes_the_files_and_the_row_says_loaded(self):
        b = self.open_intake()
        self.script(route_steps())
        b.click("#mtgTx")
        b.click("#mtgLoad")
        b.wait("/Loaded/.test(document.querySelector('#mtgBody tr[data-mid=\"ev-1\"]').cells[7].innerText)", 30)
        stem = f"{DAY} ABC Steering"
        self.assertEqual(self.inbox(), [f"{stem} - chat.txt", f"{stem}.vtt"])
        self.assertIn("Event ID: ev-1", (self.v.root / "inbox" / f"{stem}.vtt").read_text())
        self.assertFalse(b.eval("RUN"))                                              # the run engine is free again
        self.assertEqual(json.loads((self.v.root / "system/staging/transcripts.json").read_text())["checked"]["ev-1"]["status"], "available")
        self.assertEqual(b.eval("document.getElementById('mtgLoad').disabled"), True)    # nothing ticked any more
        self.assertIn("Loaded", b.eval("document.getElementById('chLog').textContent"))

    def test_process_selected_loads_then_hands_the_file_to_the_minutes_run(self):
        """BL-119: the one Process button does what Load and process did."""
        b = self.open_intake()
        self.script(route_steps(chat=False))
        b.click("#mtgTx")
        b.click("#mtgGo")
        b.wait("/Couldn.t|Draft ready/.test(document.querySelector('#mtgBody tr[data-mid=\"ev-1\"]').cells[6].innerText)", 40)
        seen = json.loads((self.v.root / "fake_seen.json").read_text())
        self.assertEqual(seen["prompt"], f"process inbox/{DAY} ABC Steering.vtt")        # the file the server wrote, never a re-typed transcript
        self.assertEqual(self.inbox(), [f"{DAY} ABC Steering.vtt"])

    def test_rows_without_a_transcript_are_skipped_with_the_reason_and_the_others_carry_on(self):
        b = self.open_intake()
        self.script(route_steps(chat=False))
        b.eval("['ev-room','ev-2','ev-1'].forEach(id=>MSEL.add(id)); renderMeetings()")
        self.assertEqual(b.eval("document.getElementById('mtgGo').textContent"), "Process 3 selected")
        b.click("#mtgGo")
        b.wait("/Couldn.t|Draft ready/.test(document.querySelector('#mtgBody tr[data-mid=\"ev-1\"]').cells[6].innerText)", 40)
        state = lambda eid: b.eval(f"document.querySelector('{self.row(eid)}').cells[6].innerText")  # noqa: E731
        self.assertIn("Skipped", state("ev-room"))
        self.assertIn("No transcript for this meeting", state("ev-room"))
        self.assertIn("Skipped", state("ev-2"))
        self.assertIn("Not transcribed yet", state("ev-2"))
        seen = json.loads((self.v.root / "fake_seen.json").read_text())
        self.assertEqual(seen["prompt"], f"process inbox/{DAY} ABC Steering.vtt")        # only the loadable one ran; Claude never looked for the others
        self.assertEqual(self.inbox(), [f"{DAY} ABC Steering.vtt"])

    def test_only_skipped_rows_run_nothing_and_open_nothing(self):
        b = self.open_intake()
        before = b.eval("document.getElementById('chLog').children.length")
        b.eval("MSEL.add('ev-room'); renderMeetings()")
        b.click("#mtgGo")
        b.wait("/Skipped/.test(document.querySelector('#mtgBody tr[data-mid=\"ev-room\"]').cells[6].innerText)")
        self.assertEqual(self.inbox(), [])
        self.assertFalse(b.eval("RUN"))
        self.assertEqual(b.eval("document.getElementById('chLog').children.length"), before)         # no chat messages were started

    def test_check_again_updates_the_row_and_loads_nothing(self):
        b = self.open_intake()
        self.assertIn("mtgmute", self.classes("ev-2"))
        steps = route_steps(ev=event(eid="ev-2"), tr=read(event(eid="ev-2")["meetingTranscriptUrl"], transcript_result()), chat=False)
        for s in steps:
            s["input"] = json.loads(json.dumps(s["input"]).replace("ABC Steering", "Weekly sync 12"))
        self.script(steps)
        b.click(f'{self.row("ev-2")} .mtgchk')
        b.wait("/Transcript available/.test(document.querySelector('#mtgBody tr[data-mid=\"ev-2\"]').cells[7].innerText)", 30)
        self.assertIn("mtgtx", self.classes("ev-2"))
        self.assertEqual(self.inbox(), [])
        self.assertIn("Transcript available", b.eval(f"document.querySelector('{self.row('ev-2')}').cells[7].innerText"))

    def test_the_load_button_waits_while_ask_creaite_is_busy(self):
        b = self.open_intake()
        b.eval("MSEL.add('ev-1'); RUN={id:'x'}; renderMeetings()")
        self.assertTrue(b.eval("document.getElementById('mtgLoad').disabled"))
        self.assertIn("busy", b.eval("document.getElementById('mtgLoad').title"))
        b.eval("RUN=null; renderMeetings()")
        self.assertFalse(b.eval("document.getElementById('mtgLoad').disabled"))


class UploadList(Case):
    """BL-137: Upload Files lists only uploaded files; a file Calendar Import loaded is known by its recorded event ID and its state,
    Preview and Remove are on its meeting row."""

    def stage(self, processed=False):
        inbox = self.v.root / "inbox"
        stem = f"{DAY} ABC Steering"
        (inbox / f"{stem}.vtt").write_text("WEBVTT\n\nNOTE\nEvent ID: ev-1\n\n00:00:01.000 --> 00:00:05.000\nHello there\n", encoding="utf-8")
        (inbox / f"{stem} - chat.txt").write_text("Event ID: ev-1\n\n[08:01] Sara: hello\n", encoding="utf-8")
        (inbox / "My own notes.vtt").write_text("WEBVTT\n\n00:00:01.000 --> 00:00:05.000\nUploaded by hand\n", encoding="utf-8")
        if processed:
            with open(self.v.root / "system/processed.txt", "a", encoding="utf-8") as f:
                f.write(f"{DAY} | calendar:ev-1 | projects/x | 1\n")
        b = self.open_intake()
        b.eval("reloadData().then(()=>{ renderInbox(); renderMeetings(); })")
        b.pump(1.0)
        return b

    SAMPLE = ["ABC weekly sync.vtt", "Copy of filed.vtt", "Recording.vtt"]            # the files populate() leaves in the inbox, all uploads

    def uploads(self):
        return self.b.eval("[...document.querySelectorAll('#inboxTbl tbody tr[data-inf]')].map(r=>r.querySelector('.title').textContent.trim())")

    def test_a_loaded_file_is_never_listed_under_upload_files(self):
        b = self.stage()
        self.assertEqual(sorted(self.uploads()), sorted(self.SAMPLE + ["My own notes.vtt"]))     # the transcript and its chat are not there; the uploads are
        self.assertNotIn("ABC Steering", b.eval("document.getElementById('inboxTbl').textContent"))
        self.assertNotIn("From calendar", b.eval("document.getElementById('inboxTbl').textContent"))
        row = b.eval("document.querySelector('#mtgBody tr[data-mid=\"ev-1\"]').innerText")
        self.assertIn("Loaded", row)                                                          # its state is on the meeting row
        rows = b.eval("(D.inbox||[]).map(f=>[f.name,f.uploaded,!!f.event])")
        self.assertIn(["My own notes.vtt", True, False], rows)
        self.assertIn([f"{DAY} ABC Steering.vtt", False, True], rows)                         # marked as loaded in the data

    def test_the_badge_still_counts_a_waiting_loaded_transcript_but_select_new_and_process_never_include_it(self):
        b = self.stage()
        before = b.eval("[...(D.inbox||[])].filter(f=>f.state==='new').length")
        self.assertEqual(b.eval("document.getElementById('inboxBadge').textContent"), str(before))   # the loaded transcript waits too
        self.assertTrue(b.eval("(D.inbox||[]).some(f=>f.event&&f.state==='new')"))
        b.click("#inboxNew")
        picked = b.eval("[...INSEL]")
        self.assertIn("inbox/My own notes.vtt", picked)
        self.assertFalse([p for p in picked if "ABC Steering" in p])                         # a loaded file is never ticked
        self.assertEqual(b.eval("document.getElementById('inboxGo').textContent"), f"Process {len(picked)} selected")

    def test_preview_and_remove_are_on_the_meeting_row_and_undo_brings_both_files_back(self):
        b = self.stage()
        own = b.eval("document.querySelectorAll('#inboxTbl [data-inprev], #inboxTbl [data-inrm]').length")
        self.assertEqual(own, 2 * len(self.SAMPLE + ["My own notes.vtt"]))                      # the uploads keep their own Preview and Remove
        b.click('#mtgBody tr[data-mid="ev-1"] [data-mprev]')
        b.wait("document.getElementById('inPrev').open")
        self.assertIn("Hello there", b.eval("document.getElementById('inPrevText').textContent"))
        b.eval("document.getElementById('inPrev').close()")
        b.click('#mtgBody tr[data-mid="ev-1"] [data-mrm]')
        b.wait("/Removed the loaded transcript/.test(document.getElementById('snackT').textContent)", 20)   # the message, before it fades
        b.wait("!document.querySelector('#mtgBody tr[data-mid=\"ev-1\"] [data-mrm]')", 20)
        self.assertEqual(self.inbox(), [])                                                    # the transcript and its chat are both out of the inbox
        b.click("#snackU")                                                                     # one Undo puts both back
        b.wait("document.querySelector('#mtgBody tr[data-mid=\"ev-1\"] [data-mrm]')", 20)
        self.assertEqual(self.inbox(), [f"{DAY} ABC Steering - chat.txt", f"{DAY} ABC Steering.vtt"])
        self.assertIn("My own notes.vtt", self.uploads())
        self.assertFalse([n for n in self.uploads() if "ABC Steering" in n])

    def test_a_processed_meeting_shows_already_processed_and_offers_no_remove(self):
        b = self.stage(processed=True)
        self.assertEqual(sorted(self.uploads()), sorted(self.SAMPLE + ["My own notes.vtt"]))
        row = b.eval("document.querySelector('#mtgBody tr[data-mid=\"ev-1\"]').innerText")
        self.assertIn("Already processed", row)
        self.assertEqual(b.eval("document.querySelectorAll('#mtgBody tr[data-mid=\"ev-1\"] [data-mrm]').length"), 0)
        self.assertEqual(b.eval("document.querySelectorAll('#mtgBody tr[data-mid=\"ev-1\"] [data-mprev]').length"), 1)    # it can still be read


if __name__ == "__main__":
    unittest.main()
