"""BL-42 phase 3 and BL-104 in the browser (Sprint 4b), reshaped by #179: Intake shows what the sweep found for each meeting (a meeting
with a transcript is a Ready row, the others wait) and Process loads the transcript through the run engine, then processes it. A real browser against the real live server; the run is a
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
from live_browser import TEST_PALETTES, LiveBrowserCase, pin_page_clock  # noqa: E402
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
        b.wait("document.querySelector('#mtgBody .inrow[data-mid]')")
        return b

    def row(self, eid):
        return f'#mtgBody .inrow[data-mid="{eid}"]'

    def group(self, eid):
        return self.b.eval(f"document.querySelector('{self.row(eid)}').dataset.g")

    def text(self, eid):
        return self.b.eval(f"document.querySelector('{self.row(eid)}').innerText")

    def state(self, eid):
        return self.b.eval(f"(document.querySelector('{self.row(eid)} .instate')||{{innerText:''}}).innerText")

    def inbox(self):
        """What a load wrote: the sample files populate() puts in the inbox are left out."""
        return sorted(p.name for p in (self.v.root / "inbox").iterdir() if p.name.startswith(DAY))


class Highlight(Case):
    shared_server = True

    def test_a_meeting_with_a_transcript_is_a_ready_row_and_says_so(self):
        self.open_intake()
        self.assertEqual(self.group("ev-1"), "ready")
        self.assertIn("Transcript ready", self.text("ev-1"))                                       # words, not only colour
        self.assertEqual(self.b.eval(f"document.querySelectorAll('{self.row('ev-1')} [data-ia]:not([data-ia=det])').length"), 3)

    def test_the_others_wait_and_a_processed_one_is_done(self):
        self.open_intake()
        for eid, label in (("ev-2", "Not transcribed"), ("ev-room", "No transcript")):
            self.assertEqual(self.group(eid), "waiting", eid)
            self.assertIn("Waiting for transcript", self.text(eid))
            self.assertIn(label, self.text(eid))
        self.assertEqual(self.group("ev-done"), "done")                                             # processed: quiet, even though a transcript exists
        self.assertIn("Already processed", self.text("ev-done"))
        self.assertNotIn("Transcript ready", self.text("ev-done"))

    def test_a_waiting_row_has_no_process_button(self):
        b = self.open_intake()
        for eid in ("ev-2", "ev-room"):
            self.assertEqual(b.eval(f"document.querySelectorAll('{self.row(eid)} [data-ia=process]').length"), 0, eid)    # nothing to load

    def test_the_row_reads_in_every_theme_and_mode(self):
        b = self.open_intake()

        def rgb(text):
            nums = [float(x) for x in re.findall(r"[\d.]+", text)[:3]]
            return [n * 255 if text.startswith("color(") else n for n in nums]

        def lum(c):
            f = lambda v: (v / 255) / 12.92 if v / 255 <= 0.03928 else (((v / 255) + 0.055) / 1.055) ** 2.4  # noqa: E731
            return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])

        def ratio(fg, bg):
            a, c = lum(rgb(fg)), lum(rgb(bg))
            return (max(a, c) + 0.05) / (min(a, c) + 0.05)
        b.eval(f"document.querySelector('{self.row('ev-1')} .inage').classList.add('old')")      # the amber age
        for palette in TEST_PALETTES:
            for mode in ("Light", "Dark"):
                b.eval(f"S.palette={palette!r}; S.theme={mode!r}; applyTheme()")
                b.pump(0.3)
                got = b.eval(f"""(()=>{{ const r=document.querySelector('{self.row('ev-1')}'), q=s=>getComputedStyle(r.querySelector(s));
                  return {{surface:getComputedStyle(r).backgroundColor, title:q('.int').color, age:q('.inage').color,
                           chip:q('.inchip').color, chipbg:q('.inchip').backgroundColor}}; }})()""")
                self.assertGreaterEqual(ratio(got["title"], got["surface"]), 4.5, (palette, mode, "title", got))
                self.assertGreaterEqual(ratio(got["age"], got["surface"]), 4.5, (palette, mode, "amber age", got))
                self.assertGreaterEqual(ratio(got["chip"], got["chipbg"]), 4.5, (palette, mode, "chip", got))


class Loading(Case):
    def test_process_loads_then_hands_the_file_to_the_minutes_run(self):
        """BL-119, #179: Process does what Load into inbox and Process did, in one step; the transcript and its chat are saved first."""
        b = self.open_intake()
        self.script(route_steps())
        b.click(f"{self.row('ev-1')} [data-ia=process]")
        b.wait("/Couldn.t|Draft ready/.test((document.querySelector('#mtgBody [data-mid=\"ev-1\"] .instate')||{innerText:''}).innerText)", 40)
        seen = json.loads((self.v.root / "fake_seen.json").read_text())
        self.assertEqual(seen["prompt"], f"process inbox/{DAY} ABC Steering.vtt")        # the file the server wrote, never a re-typed transcript
        stem = f"{DAY} ABC Steering"
        self.assertEqual(self.inbox(), [f"{stem} - chat.txt", f"{stem}.vtt"])
        self.assertIn("Event ID: ev-1", (self.v.root / "inbox" / f"{stem}.vtt").read_text())
        self.assertEqual(json.loads((self.v.root / "system/staging/transcripts.json").read_text())["checked"]["ev-1"]["status"], "available")
        self.assertFalse(b.eval("RUN"))                                                  # the run engine is free again
        self.assertFalse(b.eval("document.getElementById('chat').classList.contains('on')"))   # and ask creaite never opened

    def test_rows_without_a_transcript_are_skipped_with_the_reason_and_the_others_carry_on(self):
        """The same path from the palette's "process meeting" action, which can pick any ended meeting."""
        b = self.open_intake()
        self.script(route_steps(chat=False))
        b.eval("['ev-room','ev-2','ev-1'].forEach(id=>MSEL.add(id)); processMeetings()")
        b.wait("/Couldn.t|Draft ready/.test((document.querySelector('#mtgBody [data-mid=\"ev-1\"] .instate')||{innerText:''}).innerText)", 40)
        self.assertIn("Skipped", self.state("ev-room"))
        self.assertIn("No transcript for this meeting", self.state("ev-room"))
        self.assertIn("Skipped", self.state("ev-2"))
        self.assertIn("Not transcribed yet", self.state("ev-2"))
        seen = json.loads((self.v.root / "fake_seen.json").read_text())
        self.assertEqual(seen["prompt"], f"process inbox/{DAY} ABC Steering.vtt")        # only the loadable one ran; Claude never looked for the others
        self.assertEqual(self.inbox(), [f"{DAY} ABC Steering.vtt"])

    def test_only_skipped_rows_run_nothing_and_open_nothing(self):
        b = self.open_intake()
        before = b.eval("document.getElementById('chLog').children.length")
        b.eval("MSEL.add('ev-room'); processMeetings()")
        b.wait("/Skipped/.test(document.querySelector('#mtgBody [data-mid=\"ev-room\"] .instate').innerText)")
        self.assertEqual(self.inbox(), [])
        self.assertFalse(b.eval("RUN"))
        self.assertEqual(b.eval("document.getElementById('chLog').children.length"), before)         # no chat messages were started

    def test_check_again_updates_the_row_and_loads_nothing(self):
        b = self.open_intake()
        self.assertEqual(self.group("ev-2"), "waiting")
        steps = route_steps(ev=event(eid="ev-2"), tr=read(event(eid="ev-2")["meetingTranscriptUrl"], transcript_result()), chat=False)
        for s in steps:
            s["input"] = json.loads(json.dumps(s["input"]).replace("ABC Steering", "Weekly sync 12"))
        self.script(steps)
        b.click(f'{self.row("ev-2")} [data-ia=det]')                                       # Check again is under Details
        b.click(f'{self.row("ev-2")} .mtgchk')
        b.wait("document.querySelector('#mtgBody [data-mid=\"ev-2\"][data-g=ready]')", 30)
        self.assertIn("Transcript ready", self.text("ev-2"))
        self.assertEqual(self.inbox(), [])

    def test_process_waits_while_ask_creaite_is_busy(self):
        b = self.open_intake()
        b.eval("RUN={id:'x'}; renderMeetings()")
        self.assertTrue(b.eval(f"document.querySelector('{self.row('ev-1')} [data-ia=process]').disabled"))
        self.assertTrue(b.eval("document.getElementById('inAll').disabled"))
        b.eval("RUN=null; renderMeetings()")
        self.assertFalse(b.eval(f"document.querySelector('{self.row('ev-1')} [data-ia=process]').disabled"))


class UploadList(Case):
    """BL-137: Upload files lists only uploaded files; a file Calendar import loaded is known by its recorded event ID and its state,
    Preview and Remove are on its meeting row (#179: under Details)."""

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
        b.eval("reloadData().then(()=>{ renderInbox(); })")
        b.pump(1.0)
        return b

    SAMPLE = ["ABC weekly sync.vtt", "Copy of filed.vtt", "Recording.vtt"]            # the files populate() leaves in the inbox, all uploads

    def uploads(self):
        return self.b.eval("[...document.querySelectorAll('#mtgBody .inrow[data-inf] .int')].map(r=>r.textContent.trim())")

    def test_a_loaded_file_is_never_listed_under_upload_files(self):
        b = self.stage()
        self.assertEqual(sorted(self.uploads()), sorted(self.SAMPLE + ["My own notes.vtt"]))     # the transcript and its chat are not there; the uploads are
        self.assertEqual(b.eval("document.querySelectorAll('#mtgBody .inrow[data-g=files][data-inf*=\"ABC Steering\"]').length"), 0)
        self.assertIn("Transcript ready", self.text("ev-1"))                                    # its state is on the meeting row
        rows = b.eval("(D.inbox||[]).map(f=>[f.name,f.uploaded,!!f.event])")
        self.assertIn(["My own notes.vtt", True, False], rows)
        self.assertIn([f"{DAY} ABC Steering.vtt", False, True], rows)                         # marked as loaded in the data

    def test_the_badge_counts_a_waiting_loaded_transcript_once_and_process_all_never_takes_it_as_a_file(self):
        b = self.stage()
        ready = b.eval("readyList().map(r=>r.kind+':'+(r.kind==='m'?r.m.id:r.f.name))")
        self.assertIn("m:ev-1", ready)                                                         # the loaded transcript waits, as its meeting
        self.assertFalse([x for x in ready if x.startswith("f:") and "ABC Steering" in x])      # never also as a file
        self.assertEqual(b.eval("document.getElementById('inboxBadge').textContent"), str(len(ready)))
        self.assertEqual(b.eval("document.getElementById('inAll').textContent"), f"Process all ready ({len(ready)})")

    def test_preview_and_remove_are_on_the_meeting_row_and_undo_brings_both_files_back(self):
        b = self.stage()
        b.eval("uploadedFiles().forEach(f=>INDET.add(f.path)); renderInbox()")
        own = b.eval("document.querySelectorAll('#mtgBody [data-inprev], #mtgBody [data-inrm]').length")
        self.assertEqual(own, 2 * len(self.SAMPLE + ["My own notes.vtt"]))                      # the uploads keep their own Preview and Remove
        b.click(f'{self.row("ev-1")} [data-ia=det]')
        b.click(f'{self.row("ev-1")} [data-mprev]')
        b.wait("document.getElementById('inPrev').open")
        self.assertIn("Hello there", b.eval("document.getElementById('inPrevText').textContent"))
        b.eval("document.getElementById('inPrev').close()")
        b.click(f'{self.row("ev-1")} [data-mrm]')
        b.wait("/Removed the loaded transcript/.test(document.getElementById('snackT').textContent)", 20)   # the message, before it fades
        b.wait("!document.querySelector('#mtgBody [data-mid=\"ev-1\"] [data-mrm]')", 20)
        self.assertEqual(self.inbox(), [])                                                    # the transcript and its chat are both out of the inbox
        b.click("#snackU")                                                                     # one Undo puts both back
        b.wait("D.inbox.some(f=>f.event==='ev-1')", 20)
        self.assertEqual(self.inbox(), [f"{DAY} ABC Steering - chat.txt", f"{DAY} ABC Steering.vtt"])
        self.assertIn("My own notes.vtt", self.uploads())
        self.assertFalse([n for n in self.uploads() if "ABC Steering" in n])

    def test_a_processed_meeting_shows_already_processed_and_offers_no_remove(self):
        b = self.stage(processed=True)
        self.assertEqual(sorted(self.uploads()), sorted(self.SAMPLE + ["My own notes.vtt"]))
        self.assertEqual(self.group("ev-1"), "done")
        self.assertIn("Already processed", self.text("ev-1"))
        b.click(f'{self.row("ev-1")} [data-ia=det]')
        self.assertEqual(b.eval(f"document.querySelectorAll('{self.row('ev-1')} [data-mrm]').length"), 0)
        self.assertEqual(b.eval(f"document.querySelectorAll('{self.row('ev-1')} [data-mprev]').length"), 1)    # it can still be read


if __name__ == "__main__":
    unittest.main()
