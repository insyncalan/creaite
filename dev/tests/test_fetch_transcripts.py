"""#250 (#181 C2): fetch meeting transcripts as they appear, as a sweep step.

Run: python3 dev/tests/test_fetch_transcripts.py
Microsoft 365 is never called: the reads a sweep makes are stubbed with fixture results (fictional meetings) and handed to the live
server's observer (transcripts.SweepFetch), the only path that fetches (option 2, Jarvis/Alan 23-10-2026: no script path writes
inbox/, so `record` refuses a `result_file`). TZ is UTC so a transcript's creation time and the calendar's local times line up.
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
HELP = ('Off: creaite fetches a transcript when you press Process. On: a mail and Teams check you ask for, and Close the day, also fetch the transcripts of meetings that have ended, so they are ready when you open Intake. The scheduled morning check and the check at the start of a session do not fetch. It only reads: no extra AI run and nothing is added to your project records. Confidential meetings are never fetched.'
        )   # the brief's wording (181-c2 brief, The setting)


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

    # ── the live server's observer: the only path that fetches (option 2, Jarvis/Alan 23-10-2026) ──
    def obs(self, steps, setup="", answered=True, hold="lambda event, live, created: (False, 'normal')"):
        """Run a SweepFetch in the vault over `steps` [(uri, payload, is_error)] of read_resource calls (and a send tool call, which it
        must ignore); its outcomes as JSON. `setup` runs first (a patch). `hold` is the stub calendar rule (slice B owns the real one;
        the default stub holds nothing). The run's counts and closure line are kept in self.counts and self.said."""
        code = "\n".join(("import json, sys; sys.path.insert(0,'system/scripts'); import transcripts as T", setup,
                          f"j = T.SweepFetch(hold={hold})",
                          f"steps = json.loads({json.dumps(json.dumps(steps))})",
                          "[j.observe(T.M365 + 'read_resource', {'uri': u}, json.dumps(r), e) for u, r, e in steps]",
                          "j.observe(T.M365 + 'outlook_send_mail', {}, '{}')",
                          f"c = j.finish({answered!r}); assert j.finish({answered!r}) == c      # the run's end; a second call changes nothing",
                          "print(json.dumps([j.outcomes, c, T.fetch_text(c)]))"))
        r = subprocess.run([sys.executable, "-c", code], cwd=self.v.root, capture_output=True, text=True, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        out, self.counts, self.said = json.loads(r.stdout.strip().splitlines()[-1])
        return out

    def read(self, eid="ev-1", result=None, **ev_kw):
        """The two reads a sweep run makes for one meeting: its event, then its transcript (a URL of its own)."""
        ev = {**event(eid), **ev_kw}
        ev["meetingTranscriptUrl"] = ev["meetingTranscriptUrl"].replace("?", f"-{eid}?", 1) + "&e=" + eid   # a meeting of its own: its own path
        return [(f"calendar:///events/{eid}", ev, False), (ev["meetingTranscriptUrl"], result or transcript_result(), False)]

    def assert_not_fetched(self, eid, result, **ev_kw):
        """The meeting isn't listed for a fetch, and the observer, handed its reads, fetches nothing."""
        listed = {m["id"]: m for m in json.loads(self.sweep("transcripts", "todo"))["look_up"]}
        self.assertFalse(listed.get(eid, {}).get("fetch", False))
        self.assertNotEqual(self.obs(self.read(eid, result, **ev_kw)).get(eid), "fetched")
        self.assertEqual(self.inbox(), [])

    def in_process(self, expr, setup=""):
        """Evaluate `expr` in a Python started in the vault with the test's HOME and clock; its value as JSON."""
        code = "\n".join(("import json, sys; sys.path.insert(0,'system/scripts'); import transcripts as T", setup,
                          f"print(json.dumps({expr}))"))
        r = subprocess.run([sys.executable, "-c", code], cwd=self.v.root, capture_output=True, text=True, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

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
        self.assertEqual(self.obs(self.read()), {})                                # the observer does nothing while it is off
        out = self.record(self.fact())
        self.assertEqual(out["recorded"], {"ev-1": "available"})                  # the status is kept, as today
        self.assertNotIn("fetch", out)
        self.assertEqual(self.inbox(), [])                                         # fetched on Process only
        self.assertNotIn("fetched", self.state()["ev-1"])
        self.assertFalse((self.v.root / "system/staging/sweep-fetched.json").exists())             # no tally file at all (settled in the server)
        self.assertEqual(self.said, "")                                            # off: nothing to say after the run
        self.tracker_untouched()

    # ── on: fetched once, into inbox/, as Load writes it ──
    def test_on_an_ended_meeting_is_fetched_once(self):
        self.set_on()
        todo = json.loads(self.sweep("transcripts", "todo"))
        self.assertTrue(todo["fetch_transcripts"])
        listed = {m["id"]: m for m in todo["look_up"]}
        self.assertTrue(listed["ev-1"]["fetch"])
        self.assertEqual(self.obs(self.read()), {"ev-1": "fetched"})
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
        self.assertEqual(self.said, "1 transcript fetched")
        # a second sweep: not listed for a fetch again, and a second observer run doesn't fetch it again
        again = {m["id"]: m for m in json.loads(self.sweep("transcripts", "todo"))["look_up"]}
        self.assertNotIn("ev-1", again)
        self.assertEqual(self.obs(self.read()), {})
        self.assertEqual(self.inbox(), files)
        self.assertEqual(self.said, "")
        # a later look-up keeps when it was fetched
        code = ("import sys; sys.path.insert(0,'system/scripts'); import transcripts as T; "
                "T.keep('ev-1', {'status':'available','uri':'meeting-transcript:///x','count':1})")
        subprocess.run([sys.executable, "-c", code], cwd=self.v.root, check=True, env=self.env)
        self.assertTrue(self.state()["ev-1"]["fetched"])
        self.tracker_untouched()

    def test_confidential_meetings_are_never_fetched(self):
        self.set_on()
        edit_calendar(self.v, lambda ev: ev.update(sensitivity="confidential") if ev.get("id") == "ev-1" else None)
        listed = {m["id"]: m for m in json.loads(self.sweep("transcripts", "todo"))["look_up"]}
        self.assertFalse(listed.get("ev-1", {}).get("fetch", False))               # a confidential row keeps teams=False: recorded "No transcript"
        self.assertTrue(listed["ev-2"]["fetch"])                                   # and nothing else is skipped
        self.assertEqual(self.obs(self.read()), {"ev-1": "held"})                  # shown as held, not silently dropped (Cap L1)
        self.assertEqual(self.counts["held"], 1)
        self.assertNotIn("ABC", self.said)                                         # the line never names the meeting
        self.assertNotIn("fetch", self.record(self.fact()))
        self.assertEqual(self.inbox(), [])

    def test_processed_cleared_and_loaded_meetings_are_left_alone(self):
        self.set_on()
        with open(self.v.root / "system/processed.txt", "a") as f:
            f.write(f"{DAY} | calendar:ev-1 | projects/x | 1\n")
        (self.v.root / "inbox" / "Already.vtt").write_text(T.tidy_vtt(VTT, {"title": "Weekly sync 12", "day": DAY, "id": "ev-2"}))
        listed = {m["id"]: m for m in json.loads(self.sweep("transcripts", "todo"))["look_up"]}
        self.assertNotIn("ev-1", listed)
        self.assertFalse(listed.get("ev-2", {}).get("fetch", False))
        self.assertEqual(self.obs(self.read("ev-1") + self.read("ev-2")), {})
        self.assertNotIn("fetch", self.record(self.fact(), self.fact("ev-2")))
        self.assertEqual(self.inbox(), ["Already.vtt"])

    def test_a_failure_is_reported_and_tried_next_time(self):
        self.set_on()
        steps = self.read()
        steps[1] = (steps[1][0], "Microsoft 365 error: connection dropped", True)
        self.assertEqual(self.obs(steps), {"ev-1": "failed"})
        self.assertEqual(self.inbox(), [])
        self.assertIn("0 transcripts fetched", self.said)
        self.assertIn("couldn't be reached", self.said)
        self.assertTrue(json.loads(self.sweep("transcripts", "todo"))["look_up"][0]["fetch"])

    # ── option 2: no script path writes inbox/ ──
    def test_record_never_fetches_stamps_or_follows_a_result_file(self):
        """`transcripts record` (and `sweep.py transcripts record`) with the setting on, handed a result file Claude Code saved: the
        key is not a fact field, so the fact is refused; nothing reaches inbox/ and no fetched or left stamp is made."""
        self.set_on()
        saved = self.saved_result()
        f = self.v.root / "system/staging/drafts/transcripts.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({"results": [self.fact(result_file=str(saved)), self.fact("ev-2")]}))
        out = json.loads(self.sweep("transcripts", "record", str(f)))
        self.assertEqual(out["refused"], ["ev-1"])
        self.assertEqual(out["recorded"], {"ev-2": "available"})
        self.assertNotIn("fetch", out)
        self.assertEqual(self.inbox(), [])
        self.assertNotIn("ev-1", self.state())
        for stamp in ("fetched", "left", "fetch_tries"):
            self.assertNotIn(stamp, self.state()["ev-2"])
        self.assertEqual(self.in_process("hasattr(T, 'fetch_after_record') or hasattr(T, 'result_file_text')"), False)

    def test_no_script_command_writes_into_the_inbox_even_with_the_setting_on(self):
        self.set_on()
        saved = self.saved_result()
        before = sorted(p.name for p in (self.v.root / "inbox").iterdir())
        f = self.v.root / "system/staging/drafts/transcripts.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({"results": [self.fact(), self.fact("ev-2", result_file=str(saved))]}))
        for args in (("transcripts", "todo"), ("transcripts", "record", str(f)), ("transcripts", "show"),
                     ("done", "--started", NOW, "--normal")):
            self.sweep(*args)
            r = subprocess.run([sys.executable, str(self.v.root / "system/scripts/transcripts.py"), *args[1:2]] + list(args[2:3]),
                               cwd=self.v.root, capture_output=True, text=True, env=self.env) if args[0] == "transcripts" else None
            self.assertTrue(r is None or r.returncode in (0, 1), r and r.stderr)
            self.assertEqual(sorted(p.name for p in (self.v.root / "inbox").iterdir()), before, args)
        # and in the code: only the observer reaches the fetch (and a fetch is the only thing besides Load that writes inbox/)
        src = (REPO / "system/scripts/transcripts.py").read_text()
        import ast
        tree = ast.parse(src)
        callers = {}
        for fn in ast.walk(tree):
            if isinstance(fn, ast.FunctionDef):
                for node in ast.walk(fn):
                    if isinstance(node, ast.Call):
                        name = getattr(node.func, "id", getattr(node.func, "attr", None))
                        if name in ("fetch_one", "mark_fetched"):
                            callers.setdefault(name, set()).add(fn.name)
        self.assertEqual(callers.get("fetch_one"), {"settle"})                     # SweepFetch.settle, nothing in main or record
        self.assertEqual(callers.get("mark_fetched"), {"fetch_one"})
        for other in (REPO / "system/scripts").glob("*.py"):
            if other.name != "transcripts.py":
                self.assertNotIn("fetch_one", other.read_text(), other.name)
        self.tracker_untouched()

    # ── review findings (#250 NOT READY) ──
    def test_the_observer_ties_a_transcript_only_to_the_event_that_named_it(self):
        self.set_on()
        edit_calendar(self.v, lambda ev: ev.update(sensitivity="confidential") if ev.get("id") == "ev-1" else None)
        secret = result_at("09:05", contents=("WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n<v A>CONFIDENTIAL-HR-TEXT</v>\n",))
        ev1, ev2 = self.read("ev-1", secret), self.read("ev-2")
        # ev-1's transcript read arrives under ev-2's name: the URL names ev-1, so it is ev-1's and held back
        self.assertNotIn("fetched", self.obs([ev1[0], ev2[0], (ev1[1][0], secret, False)]).values())      # held or left, shown in the counts; never written
        self.assertEqual(self.obs([(ev2[1][0], secret, False)]), {"uri:0": "left"})   # a transcript URL no event read named: left for Process
        self.assertEqual(self.inbox(), [])

    def test_high_a_recorded_transcript_url_never_ties_a_read_to_a_meeting(self):
        # Cap 23-10 HIGH: event_of fell back to the URL in transcripts.json, which Claude typed through `record`. Here ev-1 is
        # confidential (the calendar says normal, the event read would say otherwise) and a fact names ev-1's URL under ev-2.
        self.set_on()
        secret = result_at("09:05", contents=("WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n<v A>CONFIDENTIAL-HR-TEXT</v>\n",))
        ev1_url = self.read("ev-1")[1][0]
        for fact in (self.fact("ev-2", uri=ev1_url),                                    # the wrong meeting's URL
                     self.fact("ev-1", uri=ev1_url),                                    # the right one, but only as recorded
                     self.fact("ev-2", uri="meeting-transcript:///attacker-chosen")):   # a URL of the attacker's choosing
            with self.subTest(fact=fact["uri"][-24:] + fact["id"]):
                self.record(fact)
                self.assertNotIn("fetched", self.obs([(fact["uri"], secret, False)]).values())          # no event read in this run: refused      # held or left, shown in the counts; never written
                self.assertEqual(self.inbox(), [])
        # and with an event read in the run, a recorded URL for another meeting still does not bind: ev-2's read names its own URL
        self.record(self.fact("ev-2", uri=ev1_url))
        steps = [self.read("ev-2")[0], (ev1_url, secret, False)]
        self.assertNotIn("fetched", self.obs(steps).values())      # held or left, shown in the counts; never written
        self.assertEqual(self.inbox(), [])
        self.tracker_untouched()

    def test_medium_a_url_two_events_share_is_never_fetched_whatever_the_read_order(self):
        # Cap 23-10 N1: ev-1 confidential, ev-2 normal, both reads return the same transcript URL. Reading ev-1 then ev-2 then the
        # URL tied it to ev-2 (the later read overwrote the first) and put the confidential text in inbox/.
        self.set_on()
        edit_calendar(self.v, lambda ev: ev.update(sensitivity="confidential") if ev.get("id") == "ev-1" else None)
        secret = result_at("09:05", contents=("WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n<v A>CONFIDENTIAL-HR-TEXT</v>\n",))
        ev1 = self.read("ev-1", secret)
        ev2 = [("calendar:///events/ev-2", {**event("ev-2"), "meetingTranscriptUrl": ev1[1][0]}, False)]   # a duplicate invite
        for order in ((ev1[0], ev2[0]), (ev2[0], ev1[0])):
            with self.subTest(order=[o[0][-6:] for o in order]):
                self.assertNotIn("fetched", self.obs([*order, (ev1[1][0], secret, False)]).values())      # held or left, shown in the counts; never written
                self.assertEqual(self.inbox(), [])
        self.tracker_untouched()

    def test_medium_the_hold_holds_however_the_url_is_written(self):
        # Cap #250 MEDIUM: ev-1 confidential names U; ev-2 (normal) names U written another way: the same meeting. Whatever the order of
        # the reads, nothing is tied to ev-2 and nothing is fetched. The real URL carries the occurrence's start and end.
        self.set_on()
        edit_calendar(self.v, lambda ev: ev.update(sensitivity="confidential") if ev.get("id") == "ev-1" else None)
        secret = result_at("09:05", contents=("WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n<v A>CONFIDENTIAL-HR-TEXT</v>\n",))
        ev1 = self.read("ev-1", secret, sensitivity="confidential")
        u = ev1[1][0]
        base, _, query = u.partition("?")
        variants = {"upper path": base.upper().replace("MEETING-TRANSCRIPT", "meeting-transcript") + "?" + query,
                    "upper scheme": "MEETING-TRANSCRIPT" + u[len("meeting-transcript"):],
                    "trailing slash": base + "/?" + query, "extra query": u + "&extra=1", "fragment": u + "#frag",
                    "no query": base, "own window": base + "?start=2026-10-24T08:00:00Z&end=2026-10-24T09:00:00Z",
                    "percent-encoded": base.replace("-ev-1", "%2Dev%2D1") + "?" + query,
                    "double slash": base.replace("/events/", "//events/", 1) + "?" + query}
        for name, variant in variants.items():
            ev2 = ("calendar:///events/ev-2", {**event("ev-2"), "meetingTranscriptUrl": variant}, False)
            for order in ((ev1[0], ev2), (ev2, ev1[0])):
                for read_uri in (variant, u):
                    with self.subTest(variant=name, first=order[0][0][-4:], read=read_uri[-12:]):
                        self.assertNotIn("fetched", self.obs([*order, (read_uri, secret, False)]).values())      # held or left, shown in the counts; never written
                        self.assertEqual(self.inbox(), [])
        self.tracker_untouched()

    def test_two_normal_occurrences_of_one_meeting_keep_their_own_windows(self):
        """The block is for a held meeting. Two normal events with the same meeting path and their own windows are not mixed up."""
        f = T.SweepFetch()
        a = "meeting-transcript:///events/join1?start=2026-10-23T08:00:00Z&end=2026-10-23T09:00:00Z"
        b = "meeting-transcript:///events/join1?start=2026-10-24T08:00:00Z&end=2026-10-24T09:00:00Z"
        f.note_event({"sensitivity": "normal"}, {"id": "ev-a", "uri": a})
        f.note_event({"sensitivity": "normal"}, {"id": "ev-b", "uri": b})
        self.assertEqual((f.event_of(a), f.event_of(b), f.event_of(a.upper().replace("MEETING-TRANSCRIPT", "meeting-transcript"))),
                         ("ev-a", "ev-b", "ev-a"), "case and spelling of the URL do not matter; the window does")
        f.note_event({"sensitivity": "confidential"}, {"id": "ev-c", "uri": a + "&x=1"})
        self.assertEqual((f.event_of(a), f.event_of(b)), (None, None), "a held event blocks the whole meeting, either window")

    def test_the_observer_reads_only_the_exact_read_tool_and_never_overwrites_a_planted_link(self):
        self.set_on()
        steps = self.read("ev-1")
        code = ("j = T.SweepFetch(); import json; "
                "[j.observe('mcp__evil__read_resource', {'uri': u}, json.dumps(r), e) for u, r, e in json.loads(%r)]; print(json.dumps(j.outcomes))"
                % json.dumps(steps))
        r = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0,'system/scripts'); import transcripts as T\n" + code],
                           cwd=self.v.root, capture_output=True, text=True, env=self.env)
        self.assertEqual(json.loads(r.stdout.strip().splitlines()[-1]), {})
        self.assertEqual(self.inbox(), [])

    def test_high2_a_missing_or_unknown_sensitivity_is_treated_as_confidential(self):
        self.set_on()
        for value in ("secret-ish", "Restricted"):
            with self.subTest(value=value):
                edit_calendar(self.v, lambda ev, value=value: (ev.pop("sensitivity", None) if value is None
                                                               else ev.update(sensitivity=value)) if ev.get("id") == "ev-1" else None)
                self.assert_not_fetched("ev-1", result_at("09:05"))
        # main's calendar reader (invite_clean.clean_row) reads a missing or empty sensitivity as normal, as every other reader does;
        # the function itself still fails closed on a row without the key
        self.assertTrue(T.confidential({"title": "x"}))                            # fail closed
        self.assertFalse(T.confidential({"sensitivity": "Normal"}))

    def test_high2_the_observer_honours_the_event_reads_sensitivity(self):
        self.set_on()                                                              # the calendar row says normal
        steps = self.read("ev-1", sensitivity="confidential")
        self.assertNotEqual(self.obs(steps).get("ev-1"), "fetched")
        self.assertEqual(self.inbox(), [])

    def test_medium3_a_long_multibyte_title_is_named_within_150_bytes(self):
        self.set_on()
        edit_calendar(self.v, lambda ev: ev.update(title="\U0001F600" * 140) if ev.get("id") == "ev-1" else None)
        self.assertEqual(self.obs(self.read("ev-1", result_at("09:05", subject="\U0001F600" * 140), subject="\U0001F600" * 140)),
                         {"ev-1": "fetched"})
        name = self.inbox()[0]
        self.assertLessEqual(len(Path(name).stem.encode("utf-8")), 150)
        self.assertTrue(name.startswith(DAY))
        self.assertEqual(name.encode("utf-8").decode("utf-8"), name)                # never half a character
        self.assertEqual(T.file_stem(DAY, "é" * 200).encode("utf-8")[-2:], "é".encode("utf-8"))

    def test_medium3_a_meeting_that_cant_be_saved_doesnt_stop_the_others_or_retry_for_ever(self):
        self.set_on()
        steps = self.read("ev-1") + self.read("ev-2", result_at("15:05", subject="Weekly sync 12"))
        broken = ("orig = T.Job.write; "
                  "T.Job.write = lambda self, at, label: (_ for _ in ()).throw(OSError(36, 'File name too long')) "
                  "if self.id == 'ev-1' else orig(self, at, label)")
        for n in range(T.FETCH_TRIES + 1):
            got = self.obs(steps, broken)
            if n == 0:
                self.assertEqual(got, {"ev-1": "error", "ev-2": "fetched"})       # ev-2 still fetched
            elif n < T.FETCH_TRIES:
                self.assertEqual(got, {"ev-1": "error"})
            else:
                self.assertEqual(got, {})                                        # tried FETCH_TRIES times: left for Process
        self.assertEqual(self.state()["ev-1"]["fetch_tries"], T.FETCH_TRIES)
        self.assertEqual(self.inbox(), [f"{DAY} Weekly sync 12.vtt"])
        self.assertEqual(self.counts, {"fetched": 0, "held": 0, "failed": 0, "left": 0, "error": 0})   # the last run: ev-1 skipped (tried out)
        self.obs(steps[2:], broken)                                              # ev-2 again: already fetched, nothing new
        log = "".join(p.read_text() for p in (self.v.root / "system/logs").glob("debug-*.log"))
        self.assertIn("fetch: fetched 1, held 0, failed 0, left 0, error 1", log)   # counts only, never a title
        self.assertNotIn("Weekly sync", log)

    def test_medium6_the_spooled_reader_has_the_same_folder_and_size_rules(self):
        inside = self.saved_result()
        loose = self.home / ".claude" / "loose.txt"
        loose.write_text(inside.read_text())
        self.assertIsNotNone(self.in_process(f"T.read_spooled('saved to {inside}')"))
        self.assertIsNone(self.in_process(f"T.read_spooled('saved to {loose}')"))      # ~/.claude but not tool-results
        self.assertIsNone(self.in_process(f"T.read_spooled('saved to {inside}')", "T.RESULT_FILE_MAX = 10"))

    def test_low9_the_catalogue_help_is_the_briefs_wording(self):
        import settings_catalogue
        group, label, line, reason = settings_catalogue.CATALOGUE["sweep.fetch_transcripts"]
        self.assertEqual(label, "Fetch transcripts as they appear")
        self.assertEqual(reason, HELP)                                             # the brief's help text (plain words: "check")
        self.assertTrue(HELP.endswith(line))                                       # the one-line summary is its own words
        self.assertEqual(group, "Checking mail and Teams")                           # Advanced: not one of the Essentials rows
        self.assertNotIn("sweep.fetch_transcripts", {k for r in settings_catalogue.ESSENTIAL_ROWS for k in r[3]})

    # ── every eligibility rule, each on its own (mutation survivors in the review) ──
    def test_a_fetched_meeting_isnt_fetched_again_even_when_its_file_is_gone(self):
        self.set_on()
        self.assertEqual(self.obs(self.read()), {"ev-1": "fetched"})
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
        self.assert_not_fetched("ev-1", transcript_result())

    def test_the_observer_refuses_a_transcript_from_another_day(self):
        self.set_on()
        far = transcript_result()
        far["transcripts"][0]["createdDateTime"] = "2020-01-01T08:00:30Z"
        self.assertEqual(self.obs(self.read("ev-1", far)), {"ev-1": "another meeting"})
        self.assertEqual(self.inbox(), [])

    def test_the_servers_observer_fetches_only_when_on(self):
        self.assertEqual(self.obs(self.read()), {})
        self.assertEqual(self.inbox(), [])
        self.set_on()
        self.assertEqual(self.obs(self.read()), {"ev-1": "fetched"})
        self.assertEqual(self.inbox(), [f"{DAY} ABC Steering.vtt"])
        self.assertEqual(self.obs(self.read()), {})                                # a repeat run: not fetched again
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
