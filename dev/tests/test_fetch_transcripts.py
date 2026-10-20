"""#250 (#181 C2): fetch meeting transcripts as they appear, as a sweep step.

Run: python3 dev/tests/test_fetch_transcripts.py
Microsoft 365 is never called: the reads a sweep makes are stubbed with fixture results (fictional meetings), saved where Claude
Code saves a large tool result (a tool-results folder under ~/.claude, with HOME pointed at a temporary folder), or handed to the
live server's observer. TZ is UTC so a transcript's creation time and the calendar's local times line up.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_meetings import week_calendar  # noqa: E402
from test_tracker import REPO, Vault  # noqa: E402
from test_transcripts import DAY, NOW, VTT, event, transcript_result  # noqa: E402

sys.path.insert(0, str(REPO / "system" / "scripts"))
import permissions  # noqa: E402
import transcripts as T  # noqa: E402

URI = event()["meetingTranscriptUrl"]
HELP = ("Off: creaite fetches a transcript when you press Process. On: each sweep fetches the transcripts of meetings that have "
        "ended, so they are ready when you open Intake. It only reads: no AI runs and nothing is written to the tracker. "
        "Confidential meetings are never fetched.")                      # the brief's wording (181-c2 brief, The setting)


def result_at(hm, day=DAY, subject="ABC Steering", contents=(VTT,)):
    """A transcript read's result whose transcripts were created at `hm` (UTC) on `day`."""
    r = transcript_result(contents)
    r["meeting"]["subject"] = subject
    for t in r["transcripts"]:
        t["createdDateTime"] = f"{day}T{hm}:30Z"
    return r


def edit_calendar(v, fn, day=DAY):
    """Change the saved calendar's rows on `day` in place."""
    p = v.root / "system/staging/calendar.json"
    c = json.loads(p.read_text())
    for ev in c["days"].setdefault(day, []):
        fn(ev)
    p.write_text(json.dumps(c))


def add_row(v, row, day=DAY):
    p = v.root / "system/staging/calendar.json"
    c = json.loads(p.read_text())
    c["days"].setdefault(day, []).append({"all_day": False, "teams": True, "sensitivity": "normal", **row})
    p.write_text(json.dumps(c))


class Fetch(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.cleanup)
        self.v.run("init")
        week_calendar(self.v)
        # a sweep writes a sensitivity for every row that isn't private (sweep.invite_details); the fixture didn't
        edit_calendar(self.v, lambda ev: ev.setdefault("sensitivity", "normal") if not ev.get("private") else None)
        self.home = Path(tempfile.mkdtemp())
        self.spool = self.home / ".claude" / "projects" / "vault" / "session-1"          # where Claude Code saves a large result
        self.spool.mkdir(parents=True)
        env = {k: v for k, v in os.environ.items() if k != "CREAITE_TOOL_RESULTS"}
        self.env = {**env, "CREAITE_NOW": NOW, "HOME": str(self.home), "TZ": "UTC"}
        self.before = self.v.snapshot()[0]

    def set_on(self, on=True):
        cfg = self.v.root / "system/config/settings.json"
        d = json.loads(cfg.read_text())
        d.setdefault("sweep", {})["fetch_transcripts"] = on
        cfg.write_text(json.dumps(d))

    def sweep(self, *args):
        r = subprocess.run([sys.executable, str(self.v.root / "system/scripts/sweep.py"), *args], cwd=self.v.root,
                           capture_output=True, text=True, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        return r.stdout

    def saved_result(self, name="mcp-read_resource-1.txt", result=None):
        p = self.spool / "tool-results" / name
        p.parent.mkdir(exist_ok=True)
        p.write_text(json.dumps([{"type": "text", "text": json.dumps(result or result_at("09:05"))}]), encoding="utf-8")
        return p

    def record(self, *facts):
        f = self.v.root / "system/staging/drafts/transcripts.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({"results": list(facts)}))
        return json.loads(self.sweep("transcripts", "record", str(f)))

    def fact(self, eid="ev-1", **kw):
        return {"id": eid, "online": True, "uri": URI, "count": 1, "error": None, **kw}

    def inbox(self):
        return sorted(p.name for p in (self.v.root / "inbox").iterdir() if p.suffix in (".vtt", ".txt"))

    def state(self):
        return json.loads((self.v.root / "system/staging/transcripts.json").read_text())["checked"]

    def tracker_untouched(self):
        self.assertEqual(self.v.snapshot()[0], self.before)                       # nothing reached the tracker
        self.assertEqual(list((self.v.root / "system/staging").glob("proposed-*.json")), [])   # and nothing was staged

    # ── off by default, and off means nothing happens ──
    def test_the_setting_is_off_by_default(self):
        defaults = json.loads((REPO / "system/templates/settings-defaults.json").read_text())
        self.assertIs(defaults["sweep"]["fetch_transcripts"], False)
        self.assertIs(json.loads((REPO / "system/config/settings.json").read_text())["sweep"]["fetch_transcripts"], False)
        import settings_catalogue
        self.assertEqual(settings_catalogue.CATALOGUE["sweep.fetch_transcripts"][1], "Fetch transcripts as they appear")
        self.assertFalse(T.fetch_on({"sweep": {}}))                                # a vault without the key: off
        self.assertFalse(T.fetch_on({"sweep": {"fetch_transcripts": "yes"}}))     # only exactly true turns it on

    def test_off_nothing_is_fetched(self):
        todo = json.loads(self.sweep("transcripts", "todo"))
        self.assertFalse(todo["fetch_transcripts"])
        self.assertTrue(all("fetch" not in m for m in todo["look_up"]))
        out = self.record(self.fact(result_file=str(self.saved_result())))
        self.assertEqual(out["recorded"], {"ev-1": "available"})                  # the status is kept, as today
        self.assertNotIn("fetch", out)
        self.assertEqual(self.inbox(), [])                                         # fetched on Process only
        self.assertNotIn("fetched", self.state()["ev-1"])
        self.assertFalse((self.v.root / "system/staging/sweep-fetched.json").exists())
        self.assertNotIn("Fetched", self.sweep("done", "--started", NOW, "--normal"))
        self.tracker_untouched()

    # ── on: fetched once, into inbox/, as Load writes it ──
    def test_on_an_ended_meeting_is_fetched_once(self):
        self.set_on()
        todo = json.loads(self.sweep("transcripts", "todo"))
        self.assertTrue(todo["fetch_transcripts"])
        listed = {m["id"]: m for m in todo["look_up"]}
        self.assertTrue(listed["ev-1"]["fetch"])
        out = self.record(self.fact(result_file=str(self.saved_result())))
        self.assertEqual(out["fetch"], {"ev-1": "fetched"})
        files = self.inbox()
        self.assertEqual(files, [f"{DAY} ABC Steering.vtt"])
        text = (self.v.root / "inbox" / files[0]).read_text(encoding="utf-8")
        self.assertIn("Event ID: ev-1", text)                                      # Intake reads it as loaded
        self.assertIn("UAT starts 12-11-2026", text)                               # every word, from Microsoft 365's own result
        kept = (self.v.root / "system/staging/transcripts.json").read_text()
        self.assertNotIn("WEBVTT", kept)                                           # transcripts.json: status, URL and dates only
        self.assertNotIn("Welcome", kept)
        self.assertEqual(set(self.state()["ev-1"]) - set(T.KEEP), set())
        self.assertTrue(self.state()["ev-1"]["fetched"])
        self.assertIn("Fetched 1 transcript", self.sweep("done", "--started", NOW, "--normal"))
        # a second sweep: not listed for a fetch again, and a second record doesn't fetch it again
        again = {m["id"]: m for m in json.loads(self.sweep("transcripts", "todo"))["look_up"]}
        self.assertNotIn("ev-1", again)
        out = self.record(self.fact(result_file=str(self.saved_result("mcp-read_resource-2.txt"))))
        self.assertNotIn("fetch", out)
        self.assertEqual(self.inbox(), files)
        self.assertNotIn("Fetched", self.sweep("done", "--started", NOW, "--normal"))
        # a later look-up keeps when it was fetched
        code = ("import sys; sys.path.insert(0,'system/scripts'); import transcripts as T; "
                "T.keep('ev-1', {'status':'available','uri':'meeting-transcript:///x','count':1})")
        subprocess.run([sys.executable, "-c", code], cwd=self.v.root, check=True, env=self.env)
        self.assertTrue(self.state()["ev-1"]["fetched"])
        self.tracker_untouched()

    def test_confidential_meetings_are_never_fetched(self):
        self.set_on()
        cal_p = self.v.root / "system/staging/calendar.json"
        cal = json.loads(cal_p.read_text())
        for ev in cal["days"][DAY]:
            if ev.get("id") == "ev-1":
                ev["sensitivity"] = "confidential"
        cal_p.write_text(json.dumps(cal))
        listed = {m["id"]: m for m in json.loads(self.sweep("transcripts", "todo"))["look_up"]}
        self.assertFalse(listed["ev-1"]["fetch"])                                  # its status is still looked up
        self.assertTrue(listed["ev-2"]["fetch"])                                   # and nothing else is skipped
        out = self.record(self.fact(result_file=str(self.saved_result())))
        self.assertNotIn("fetch", out)
        self.assertEqual(self.inbox(), [])

    def test_processed_cleared_and_loaded_meetings_are_left_alone(self):
        self.set_on()
        with open(self.v.root / "system/processed.txt", "a") as f:
            f.write(f"{DAY} | calendar:ev-1 | projects/x | 1\n")
        (self.v.root / "inbox" / "Already.vtt").write_text(T.tidy_vtt(VTT, {"title": "Weekly sync 12", "day": DAY, "id": "ev-2"}))
        listed = {m["id"]: m for m in json.loads(self.sweep("transcripts", "todo"))["look_up"]}
        self.assertNotIn("ev-1", listed)
        self.assertFalse(listed.get("ev-2", {}).get("fetch", False))
        out = self.record(self.fact(result_file=str(self.saved_result())), self.fact("ev-2", result_file=str(self.saved_result("b.txt"))))
        self.assertNotIn("fetch", out)
        self.assertEqual(self.inbox(), ["Already.vtt"])

    def test_a_failure_is_reported_and_tried_next_time(self):
        self.set_on()
        out = self.record(self.fact(count=None, error="other"))
        self.assertEqual(out["fetch"], {"ev-1": "failed"})
        self.assertEqual(self.inbox(), [])
        said = self.sweep("done", "--started", NOW, "--normal")
        self.assertIn("Fetched 0 transcripts", said)
        self.assertIn("couldn't be reached", said)
        self.assertTrue(json.loads(self.sweep("transcripts", "todo"))["look_up"][0]["fetch"])

    def test_an_inline_result_is_left_for_process_and_stamped_so_it_is_not_read_again(self):
        self.set_on()
        out = self.record(self.fact())                                             # no saved file: never re-typed
        self.assertEqual(out["fetch"], {"ev-1": "left"})
        self.assertEqual(self.inbox(), [])
        self.assertTrue(self.state()["ev-1"]["left"])                              # a time, never text (MEDIUM 7)
        self.assertEqual(set(self.state()["ev-1"]) - set(T.KEEP), set())
        self.assertIn("1 left to fetch on Process", self.sweep("done", "--started", NOW, "--normal"))
        again = {m["id"]: m for m in json.loads(self.sweep("transcripts", "todo"))["look_up"]}
        self.assertNotIn("ev-1", again)                                            # not re-listed every sweep
        self.assertNotIn("fetch", self.record(self.fact(result_file=str(self.saved_result()))))
        self.assertEqual(self.inbox(), [])                                         # Process fetches it, as today

    def test_a_file_outside_claude_codes_tool_results_is_never_read(self):
        self.set_on()
        elsewhere = Path(tempfile.mkdtemp()) / "x.txt"
        elsewhere.write_text(json.dumps(result_at("09:05")))
        under_home = self.home / ".claude" / "projects" / "vault" / "notes.txt"   # in ~/.claude, not a tool-results folder
        under_home.write_text(json.dumps([{"type": "text", "text": json.dumps(result_at("09:05"))}]))
        for f in (elsewhere, under_home):
            with self.subTest(f=f.name):
                self.assertIsNone(self.in_process(f"T.result_file_text({str(f)!r})"))
        out = self.record(self.fact(result_file=str(under_home)))
        self.assertEqual(out["fetch"], {"ev-1": "left"})
        self.assertEqual(self.inbox(), [])

    # ── review findings (#250 NOT READY) ──
    def in_process(self, expr, setup=""):
        """Evaluate `expr` in a Python started in the vault with the test's HOME and clock; its value as JSON."""
        code = "\n".join(("import json, sys; sys.path.insert(0,'system/scripts'); import transcripts as T", setup,
                          f"print(json.dumps({expr}))"))
        r = subprocess.run([sys.executable, "-c", code], cwd=self.v.root, capture_output=True, text=True, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def assert_not_fetched(self, eid, result):
        """The meeting isn't listed for a fetch, and a record that hands it a result tied to it fetches nothing."""
        listed = {m["id"]: m for m in json.loads(self.sweep("transcripts", "todo"))["look_up"]}
        self.assertFalse(listed.get(eid, {}).get("fetch", False))
        out = self.record(self.fact(eid, result_file=str(self.saved_result(f"{eid}.txt", result))))
        self.assertNotEqual(out.get("fetch", {}).get(eid), "fetched")
        self.assertEqual(self.inbox(), [])

    def test_high1_a_confidential_meetings_result_is_never_written_under_another_meetings_name(self):
        self.set_on()
        edit_calendar(self.v, lambda ev: ev.update(sensitivity="confidential") if ev.get("id") == "ev-1" else None)
        secret = result_at("09:05", contents=("WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n<v A>CONFIDENTIAL-HR-TEXT</v>\n",))
        conf = self.saved_result("conf.txt", secret)
        out = self.record(self.fact("ev-2", result_file=str(conf)))                # Claude puts ev-1's result under ev-2
        self.assertEqual(out["fetch"], {"ev-2": "not tied"})
        self.assertEqual(self.inbox(), [])
        # and when the times fit ev-2 but a confidential meeting overlaps it, it can't be told whose it is: refused
        add_row(self.v, {"id": "ev-6", "start": "15:00", "end": "15:30", "title": "HR case", "sensitivity": "confidential"})
        overlap = self.saved_result("overlap.txt", result_at("15:05", subject="Weekly sync 12"))
        self.reset("ev-2")
        self.assertEqual(self.record(self.fact("ev-2", result_file=str(overlap)))["fetch"], {"ev-2": "not tied"})
        self.assertEqual(self.inbox(), [])

    def reset(self, eid):
        """Forget what the fetch stamped for one meeting (as if a new sweep saw it first)."""
        p = self.v.root / "system/staging/transcripts.json"
        if not p.exists():
            return
        d = json.loads(p.read_text())
        d["checked"].pop(eid, None)
        p.write_text(json.dumps(d))

    def test_high1_a_result_is_tied_by_its_times_and_its_subject(self):
        self.set_on()
        cases = {"before the meeting": result_at("07:00"), "another subject": result_at("09:05", subject="Board pay review"),
                 "no creation time": {**result_at("09:05"), "transcripts": [{"id": "t", "content": VTT}]}}
        for why, res in cases.items():
            with self.subTest(why):
                self.reset("ev-1")
                out = self.record(self.fact(result_file=str(self.saved_result(f"{len(why)}.txt", res))))
                self.assertEqual(out["fetch"], {"ev-1": "not tied"})
                self.assertEqual(self.inbox(), [])
        self.reset("ev-1")
        self.assertEqual(self.record(self.fact(result_file=str(self.saved_result())))["fetch"], {"ev-1": "fetched"})

    def test_high2_a_missing_or_unknown_sensitivity_is_treated_as_confidential(self):
        self.set_on()
        for value in (None, "", "secret-ish"):
            with self.subTest(value=value):
                edit_calendar(self.v, lambda ev, value=value: (ev.pop("sensitivity", None) if value is None
                                                               else ev.update(sensitivity=value)) if ev.get("id") == "ev-1" else None)
                self.reset("ev-1")
                self.assert_not_fetched("ev-1", result_at("09:05"))
        self.assertTrue(T.confidential({"title": "x"}))                            # fail closed
        self.assertFalse(T.confidential({"sensitivity": "Normal"}))

    def test_high2_the_observer_honours_the_event_reads_sensitivity(self):
        self.set_on()
        ev = {**event(), "sensitivity": "confidential"}                            # the calendar row says normal
        steps = [("calendar:///events/ev-1", ev), (URI, transcript_result())]
        code = ("import json, sys; sys.path.insert(0,'system/scripts'); import transcripts as T; j = T.SweepFetch(); "
                f"steps = json.loads({json.dumps(json.dumps(steps))}); "
                "[j.observe(T.M365 + 'read_resource', {'uri': u}, json.dumps(r)) for u, r in steps]; print(json.dumps(j.outcomes))")
        r = subprocess.run([sys.executable, "-c", code], cwd=self.v.root, capture_output=True, text=True, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotEqual(json.loads(r.stdout).get("ev-1"), "fetched")
        self.assertEqual(self.inbox(), [])

    def test_medium3_a_long_multibyte_title_is_named_within_150_bytes(self):
        self.set_on()
        edit_calendar(self.v, lambda ev: ev.update(title="\U0001F600" * 140) if ev.get("id") == "ev-1" else None)
        out = self.record(self.fact(result_file=str(self.saved_result(result=result_at("09:05", subject="\U0001F600" * 140)))))
        self.assertEqual(out["fetch"], {"ev-1": "fetched"})
        name = self.inbox()[0]
        self.assertLessEqual(len(Path(name).stem.encode("utf-8")), 150)
        self.assertTrue(name.startswith(DAY))
        self.assertEqual(name.encode("utf-8").decode("utf-8"), name)                # never half a character
        self.assertEqual(T.file_stem(DAY, "é" * 200).encode("utf-8")[-2:], "é".encode("utf-8"))

    def test_medium3_a_meeting_that_cant_be_saved_doesnt_stop_the_others_or_retry_for_ever(self):
        self.set_on()
        f = self.v.root / "system/staging/drafts/transcripts.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({"results": [self.fact(result_file=str(self.saved_result())),
                                             self.fact("ev-2", result_file=str(self.saved_result("b.txt", result_at("15:05", subject="Weekly sync 12"))))]}))
        broken = ("orig = T.Job.write; "
                  "T.Job.write = lambda self, at, label: (_ for _ in ()).throw(OSError(36, 'File name too long')) "
                  "if self.id == 'ev-1' else orig(self, at, label)")
        for n in range(T.FETCH_TRIES + 1):
            got = self.in_process(f"T.fetch_after_record(json.load(open({str(f)!r}))['results'], "
                                  "{'ev-1': 'available', 'ev-2': 'available'})", broken)
            if n == 0:
                self.assertEqual(got, {"ev-1": "error", "ev-2": "fetched"})       # ev-2 still fetched
            elif n < T.FETCH_TRIES:
                self.assertEqual(got, {"ev-1": "error"})
            else:
                self.assertEqual(got, {})                                        # tried FETCH_TRIES times: left for Process
        self.assertEqual(self.state()["ev-1"]["fetch_tries"], T.FETCH_TRIES)
        self.assertEqual(self.inbox(), [f"{DAY} Weekly sync 12.vtt"])
        said = self.sweep("done", "--started", NOW, "--normal")
        self.assertIn("Fetched 1 transcript", said)
        self.assertIn("1 couldn't be saved", said)
        log = "".join(p.read_text() for p in (self.v.root / "system/logs").glob("debug-*.log"))
        self.assertIn("transcripts 1 fetched, 0 failed, 0 left, 1 not saved", log)  # counts only, never a title
        self.assertNotIn("Weekly sync", log)

    def test_medium6_a_saved_result_that_points_elsewhere_is_not_followed(self):
        self.set_on()
        other = self.spool / "tool-results" / "big.json"                          # even a trusted place is never followed
        other.parent.mkdir(exist_ok=True)
        other.write_text(json.dumps([{"type": "text", "text": json.dumps(result_at("09:05"))}]))
        hop = self.spool / "tool-results" / "hop.txt"
        hop.write_text(f"Output too large. Full output saved to: {other}")
        self.assertEqual(self.record(self.fact(result_file=str(hop)))["fetch"], {"ev-1": "left"})
        self.assertEqual(self.inbox(), [])

    def test_medium6_the_spooled_reader_has_the_same_folder_and_size_rules(self):
        inside = self.saved_result()
        loose = self.home / ".claude" / "loose.txt"
        loose.write_text(inside.read_text())
        self.assertIsNotNone(self.in_process(f"T.read_spooled('saved to {inside}')"))
        self.assertIsNone(self.in_process(f"T.read_spooled('saved to {loose}')"))      # ~/.claude but not tool-results
        self.assertIsNone(self.in_process(f"T.read_spooled('saved to {inside}')", "T.RESULT_FILE_MAX = 10"))
        self.assertIsNone(self.in_process(f"T.result_file_text({str(inside)!r})", "T.RESULT_FILE_MAX = 10"))
        self.assertIsNotNone(self.in_process(f"T.result_file_text({str(inside)!r})"))

    def test_binary_and_symlinked_result_files_are_refused(self):
        self.set_on()
        b = self.spool / "tool-results" / "bin.txt"
        b.parent.mkdir(exist_ok=True)
        b.write_bytes(b"\xff\xfe\x00" * 100)
        outside = Path(tempfile.mkdtemp()) / "outside.txt"
        outside.write_text(json.dumps([{"type": "text", "text": json.dumps(result_at("09:05"))}]))
        link = self.spool / "tool-results" / "l.txt"
        link.symlink_to(outside)
        dotdot = Path(str(self.spool / "tool-results") + "/.." * 30 + str(outside))     # climbs out to /
        for f in (b, link, dotdot):
            with self.subTest(f=f.name):
                self.reset("ev-1")
                self.assertEqual(self.record(self.fact(result_file=str(f)))["fetch"], {"ev-1": "left"})
        self.assertEqual(self.inbox(), [])

    def test_low8_the_test_variable_trusts_no_folder(self):
        d = Path(tempfile.mkdtemp())
        f = d / "tool-results" / "x.txt"
        f.parent.mkdir()
        f.write_text(json.dumps([{"type": "text", "text": json.dumps(result_at("09:05"))}]))
        self.assertIsNone(self.in_process(f"T.result_file_text({str(f)!r})", f"import os; os.environ['CREAITE_TOOL_RESULTS'] = {str(d)!r}"))
        self.assertEqual([str(p) for p in self.in_process("[str(p) for p in T.spool_roots()]")], [str(self.home / ".claude")])

    def test_low9_the_catalogue_help_is_the_briefs_wording(self):
        import settings_catalogue
        self.assertEqual(settings_catalogue.CATALOGUE["sweep.fetch_transcripts"][2], HELP)
        self.assertIn(HELP, (REPO / "system/templates/dashboard/src/settings.js").read_text())

    # ── every eligibility rule, each on its own (mutation survivors in the review) ──
    def test_a_fetched_meeting_isnt_fetched_again_even_when_its_file_is_gone(self):
        self.set_on()
        self.assertEqual(self.record(self.fact(result_file=str(self.saved_result())))["fetch"], {"ev-1": "fetched"})
        for n in self.inbox():
            (self.v.root / "inbox" / n).unlink()
        self.assert_not_fetched("ev-1", result_at("09:05"))

    def test_private_meetings_are_never_fetched(self):
        self.set_on()
        edit_calendar(self.v, lambda ev: ev.update(private=True) if ev.get("id") == "ev-1" else None)   # sensitivity still normal
        self.assert_not_fetched("ev-1", result_at("09:05"))

    def test_meetings_not_ended_are_never_fetched(self):
        self.set_on()
        today = NOW[:10]
        add_row(self.v, {"id": "ev-late", "start": "23:00", "end": "23:55", "title": "Late call"}, day=today)
        self.assert_not_fetched("ev-late", result_at("23:05", day=today, subject="Late call"))

    def test_the_observer_never_fetches_a_meeting_not_ended(self):
        self.set_on()                                    # todo and record never offer one; the observer sees every read
        today = NOW[:10]
        add_row(self.v, {"id": "ev-late", "start": "23:00", "end": "23:55", "title": "Late call"}, day=today)
        late_uri = URI.replace(DAY, today) + "&late=1"
        ev = {**event("ev-late"), "meetingTranscriptUrl": late_uri}
        steps = [("calendar:///events/ev-late", ev), (late_uri, result_at("23:05", day=today, subject="Late call"))]
        code = ("import json, sys; sys.path.insert(0,'system/scripts'); import transcripts as T; j = T.SweepFetch(); "
                f"steps = json.loads({json.dumps(json.dumps(steps))}); "
                "[j.observe(T.M365 + 'read_resource', {'uri': u}, json.dumps(r)) for u, r in steps]; print(json.dumps(j.outcomes))")
        r = subprocess.run([sys.executable, "-c", code], cwd=self.v.root, capture_output=True, text=True, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), {})
        self.assertEqual(self.inbox(), [])

    def test_meetings_outside_the_window_are_never_fetched(self):
        self.set_on()
        sunday = (__import__("datetime").date.fromisoformat(DAY) - __import__("datetime").timedelta(days=1)).isoformat()
        edit_calendar(self.v, lambda ev: ev.setdefault("sensitivity", "normal"), day=sunday)
        self.assert_not_fetched("ev-0", result_at("10:05", day=sunday, subject="Last Sunday"))

    def test_cleared_meetings_are_never_fetched(self):
        self.set_on()
        code = (f"import sys; sys.path.insert(0,'system/scripts'); import build_dashboard as b; "
                f"b.clear_meetings([{{'key':'ev-2','day':'{DAY}','start':'15:00','title':'x'}}])")
        subprocess.run([sys.executable, "-c", code], cwd=self.v.root, check=True, env=self.env)
        self.assert_not_fetched("ev-2", result_at("15:05", subject="Weekly sync 12"))

    def test_meetings_in_review_are_never_fetched(self):
        self.set_on()
        (self.v.root / "system/staging/proposed-test.json").write_text(json.dumps(
            {"meeting": {"key": "calendar:ev-1", "title": "ABC Steering", "date": DAY}, "items": []}))
        listed = {m["id"]: m for m in json.loads(self.sweep("transcripts", "todo"))["look_up"]}
        self.assertFalse(listed.get("ev-1", {}).get("fetch", False))
        out = self.record(self.fact(result_file=str(self.saved_result())))
        self.assertNotEqual(out.get("fetch", {}).get("ev-1"), "fetched")
        self.assertEqual(self.inbox(), [])

    def test_the_observer_refuses_a_transcript_from_another_day(self):
        self.set_on()
        far = transcript_result()
        far["transcripts"][0]["createdDateTime"] = "2020-01-01T08:00:30Z"
        steps = [("calendar:///events/ev-1", event()), (URI, far)]
        code = ("import json, sys; sys.path.insert(0,'system/scripts'); import transcripts as T; j = T.SweepFetch(); "
                f"steps = json.loads({json.dumps(json.dumps(steps))}); "
                "[j.observe(T.M365 + 'read_resource', {'uri': u}, json.dumps(r)) for u, r in steps]; print(json.dumps(j.outcomes))")
        r = subprocess.run([sys.executable, "-c", code], cwd=self.v.root, capture_output=True, text=True, env=self.env)
        self.assertEqual(json.loads(r.stdout), {"ev-1": "another meeting"})
        self.assertEqual(self.inbox(), [])

    # ── the live server's copy of a sweep run's reads ──
    def observe(self):
        steps = [("calendar:///events/ev-1", event()), (URI, transcript_result())]
        code = ("import json, sys; sys.path.insert(0,'system/scripts'); import transcripts as T; j = T.SweepFetch(); "
                f"steps = json.loads({json.dumps(json.dumps(steps))}); "
                "[j.observe(T.M365 + 'read_resource', {'uri': u}, json.dumps(r)) for u, r in steps]; "
                "j.observe(T.M365 + 'outlook_send_mail', {}, '{}'); print(json.dumps(j.outcomes))")
        r = subprocess.run([sys.executable, "-c", code], cwd=self.v.root, capture_output=True, text=True, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_the_servers_observer_fetches_only_when_on(self):
        self.assertEqual(self.observe(), {})
        self.assertEqual(self.inbox(), [])
        self.set_on()
        self.assertEqual(self.observe(), {"ev-1": "fetched"})
        self.assertEqual(self.inbox(), [f"{DAY} ABC Steering.vtt"])
        self.assertEqual(self.observe(), {})                                       # a repeat run: not fetched again
        self.assertIn("Fetched 1 transcript", self.sweep("done", "--started", NOW, "--normal"))
        self.tracker_untouched()


class Guard(unittest.TestCase):
    """Read only: the fetch uses Microsoft 365 reading tools only, and the sweep run's tool list holds no action tool."""

    def test_the_fetch_tools_are_reading_tools(self):
        self.assertEqual(set(T.FETCH_TOOLS), {"mcp__claude_ai_Microsoft_365__outlook_calendar_search",
                                              "mcp__claude_ai_Microsoft_365__read_resource"})
        self.assertTrue(set(T.FETCH_TOOLS) <= set(permissions.m365_read_tools()))
        self.assertFalse(set(T.FETCH_TOOLS) & set(permissions.m365_action_tools()))

    def test_the_sweep_runs_tool_list_has_no_write_tool(self):
        import live_server
        tools = live_server.KIND_TOOLS["sweep"]
        self.assertTrue(set(T.FETCH_TOOLS) <= set(tools))                         # nothing new needs allowing
        actions = set(permissions.m365_action_tools())
        self.assertFalse(actions & set(tools))
        self.assertFalse([t for t in tools if t.startswith("mcp__") and t not in permissions.m365_read_tools()])
        self.assertTrue(actions <= set(live_server.DENY_TOOLS))                    # and every action stays denied
        self.assertFalse([t for t in tools if t.startswith(("Write(", "Edit(")) and "system/staging/drafts/" not in t])


if __name__ == "__main__":
    unittest.main()
