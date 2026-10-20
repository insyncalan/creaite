"""#265: Calendar import's Refresh is its own run kind. Pressing Refresh is Alan's go-ahead to read his Outlook calendar and save
it for Intake and Today, and the run is fenced to that: the sweep's calendar steps only.

Run: python3 dev/tests/test_calendar_refresh.py      (quick tier: no Chrome; one live server with a stand-in Claude)

- calendar_refresh.py (plain code): the fixed prompt (no request text in it), the label, the precheck (the development
  repository, the calendar source off), the outcome and closure; the usage monitor's kind "calendar" and its label.
- The guard hook's mode "calendar" (reach.py, a guarded diff in dev/proposals/calendar-refresh/): it may read the calendar
  (outlook_calendar_search, read_resource), write calendar.json and transcripts.json in drafts and run the five sweep.py calendar
  commands; it refuses every record command, proposal staging (sweep.py stage, minutes.py stage, propose.py), filechange.py, the
  sweep's lock, done and VIP steps, any other Microsoft 365 tool, the web, any other write or read, a link, and any other tool.
- Through the live server (a guarded diff): POST /api/calendar/refresh runs the kind "calendar" under the hook's mode "calendar",
  saves the calendar with the real sweep.py calendar and records the transcripts, stages nothing and applies nothing; in that same
  run the real hook refuses the record. Token, Host and Origin are checked; a second run while one is going is a 409; the
  calendar source off or the development repository is a 400; the usage line's kind is "calendar". A model-worded message (the
  refresh's own prompt, or a forged kind) is a plain chat, and "refresh calendar" typed in the panel is still BL-309's sweep.

The tests that need the guarded diffs are expected failures until they are applied (APPLIED below); they pass with them.
"""
import inspect
import json
import os
import re
import subprocess
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "system" / "scripts"))
from test_tracker import Vault  # noqa: E402

APPLIED = "def calendar_gate" in (REPO / "system/scripts/reach.py").read_text(encoding="utf-8") and \
    "/api/calendar/refresh" in (REPO / "system/scripts/live_server.py").read_text(encoding="utf-8")
needs_diff = (lambda f: f) if APPLIED else unittest.expectedFailure      # fail first: passes once the guarded diffs are applied

SPEC = "system/staging/drafts/calendar.json"
FACTS = "system/staging/drafts/transcripts.json"


def in_vault(v, code, arg=None):
    """Run Python `code` in the vault (paths.ROOT is the vault there); its JSON output."""
    r = subprocess.run([sys.executable, "-c", "import json, sys; sys.path.insert(0, 'system/scripts')\n" + code],
                       input=json.dumps(arg), cwd=v.root, capture_output=True, text=True, timeout=120)
    if r.returncode:
        raise AssertionError(r.stderr)
    return json.loads(r.stdout)


class Helpers(unittest.TestCase):
    """calendar_refresh.py: plain code, in a throwaway vault."""

    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        cls.v.run("init")

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def test_the_prompt_is_fixed_and_takes_nothing_from_the_request(self):
        import calendar_refresh as cr
        self.assertEqual(list(inspect.signature(cr.build_prompt).parameters), [])      # nothing can be passed in
        p = cr.build_prompt()
        self.assertEqual(p, cr.build_prompt())
        for c in cr.COMMANDS:
            self.assertIn(f"`{c}`", p)                                                   # each command exactly as the hook allows it
        self.assertEqual(cr.COMMANDS, ("system/scripts/run sweep.py calendar-window",
                                       f"system/scripts/run sweep.py calendar {SPEC}",
                                       "system/scripts/run sweep.py transcripts todo",
                                       f"system/scripts/run sweep.py transcripts record {FACTS}"))
        for word in ("stage", "apply", "CONFIRM", "propose.py", "minutes.py", "filechange.py"):
            self.assertNotIn(word, p.replace("no proposals", ""))
        self.assertIn("no mail, no Teams, no proposals", p)
        self.assertEqual(cr.label(), "Refresh the calendar")
        self.assertEqual((cr.KIND, cr.MODE, cr.USAGE_LABEL), ("calendar", "calendar", "Calendar refresh"))

    def test_precheck_refuses_the_development_repository_and_a_calendar_source_that_is_off(self):
        import calendar_refresh as cr
        self.assertIsNone(cr.precheck({"sweep": {"sources": {"calendar": True}}}, root=self.v.root))
        self.assertIsNone(cr.precheck({}, root=self.v.root))                             # on unless it is turned off
        self.assertIn("off in Settings", cr.precheck({"sweep": {"sources": {"calendar": False}}}, root=self.v.root))
        (self.v.root / ".creaite-dev").write_text("")
        try:
            self.assertIn("development repository", cr.precheck({}, root=self.v.root))
        finally:
            (self.v.root / ".creaite-dev").unlink()

    def test_the_outcome_counts_what_was_saved(self):
        code = ("import calendar_refresh as cr, paths, time\n"
                "t = time.time(); before = cr.outcome(t); line0 = cr.closure_line(before)\n"
                "paths.CALENDAR.write_text(json.dumps({'fetched': '2026-10-20 09:00', 'days': {'2026-10-20': [{'title': 'A'}, "
                "{'title': 'B'}], '2026-10-21': [{'title': 'C'}]}}))\n"
                "mid = cr.outcome(t); line1 = cr.closure_line(mid)\n"
                "paths.TRANSCRIPTS.write_text('{}'); after = cr.outcome(t)\n"
                "ev = []\n"
                "class R: started = t\n"
                "R.emit = staticmethod(lambda k, **d: ev.append([k, d]))\n"
                "print(json.dumps([before, line0, mid, line1, after, cr.closer()(R()), ev, cr.outcome(t + 100)]))")
        before, line0, mid, line1, after, closure, ev, later = in_vault(self.v, code)
        self.assertEqual(before, {"saved": False, "meetings": 0, "days": 0, "transcripts": False})
        self.assertIn("The calendar was not saved", line0)
        self.assertEqual(mid, {"saved": True, "meetings": 3, "days": 2, "transcripts": False})
        self.assertEqual(line1, "Calendar saved: 3 meetings over 2 days. Transcripts weren't checked this time.")
        self.assertTrue(after["transcripts"])
        self.assertEqual(closure, {"ok": True, "line": "Calendar saved: 3 meetings over 2 days.", "href": "#inbox", "link": "Intake"})
        self.assertEqual(ev, [["calendar", after]])                                       # counts only, never a title
        self.assertFalse(later["saved"])                                                  # an older save isn't this run's

    def test_the_usage_monitor_has_the_kind_and_its_label(self):
        import usage_log
        self.assertIn("calendar", usage_log.KINDS)
        self.assertEqual(usage_log.line_for("calendar")["kind"], "calendar")
        panel = next((REPO / "system/templates/dashboard/src/components/activity").glob("Usage*.jsx")).read_text(encoding="utf-8")
        self.assertIn('calendar: "Calendar refresh"', panel)


class Fence(unittest.TestCase):
    """The guard hook's mode "calendar", as Claude Code calls it (reach.decide), in a throwaway vault."""

    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        cls.v.run("init")
        drafts = cls.v.root / "system/staging/drafts"
        drafts.mkdir(parents=True, exist_ok=True)
        (drafts / "sweep.json").write_text('{"items": []}')
        (drafts / "other.json").write_text("{}")
        (drafts / "minutes.html").write_text("<p>Another meeting's minutes, waiting in Review</p>")
        (cls.v.root / "inbox").mkdir(exist_ok=True)
        (cls.v.root / "inbox/x.vtt").write_text("WEBVTT\n")
        elsewhere = cls.v.root / "projects/elsewhere.json"
        elsewhere.write_text("{}")
        (cls.v.root / "system/staging/proposed-x.json").write_text('{"items": []}\n')

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def decide(self, calls, mode="calendar"):
        """{name: allowed} for each (tool, input), with the run record the server writes for the run."""
        code = ("import reach; a = json.loads(sys.stdin.read()); reach.start_run('c-1', a['mode'], {}, None); "
                "print(json.dumps({k: reach.decide(t, i, a['mode'], 'c-1', True)[0] for k, (t, i) in a['calls'].items()}))")
        return in_vault(self.v, code, {"mode": mode, "calls": calls})

    def run_(self, words):
        return ("Bash", {"command": "system/scripts/run " + words})

    def test_the_calendar_steps_pass(self):
        """What the calendar refresh needs gets through (in mode "calendar" with the diffs, and under a plain chat's rules today)."""
        root = str(self.v.root)
        got = self.decide({
            "window": self.run_("sweep.py calendar-window"), "save": self.run_(f"sweep.py calendar {SPEC}"),
            "todo": self.run_("sweep.py transcripts todo"), "show": self.run_("sweep.py transcripts show"),
            "record": self.run_(f"sweep.py transcripts record {FACTS}"),
            "python3_form": ("Bash", {"command": f"python3 system/scripts/sweep.py calendar {SPEC}"}),
            "write_spec": ("Write", {"file_path": f"{root}/{SPEC}"}), "write_facts": ("Write", {"file_path": f"{root}/{FACTS}"}),
            "edit_spec_relative": ("Edit", {"file_path": SPEC}),
            "read_skill": ("Read", {"file_path": f"{root}/.claude/skills/cx-sweep/SKILL.md"}),
            "read_spec": ("Read", {"file_path": f"{root}/{SPEC}"}),
            "calendar_search": ("mcp__claude_ai_Microsoft_365__outlook_calendar_search", {"query": "x"}),
            "read_resource": ("mcp__claude_ai_Microsoft_365__read_resource", {"uri": "x"}),
            "tool_search": ("ToolSearch", {"query": "select:x"})})
        for name, ok in got.items():
            with self.subTest(name):
                self.assertTrue(ok, name)

    @needs_diff
    def test_everything_else_is_refused(self):
        root = str(self.v.root)
        link = self.v.root / "system/staging/drafts/link.json"
        if not link.exists():
            link.symlink_to(self.v.root / "projects/elsewhere.json")
        got = self.decide({
            # the record, staging and the rest of the sweep
            "apply": self.run_("tracker.py apply"), "undo": self.run_("tracker.py undo"), "read_tracker": self.run_("tracker.py read actions"),
            "approve": self.run_("review.py approve 1"), "reject": self.run_("review.py reject 1"), "bulk": self.run_("review.py bulk ABC"),
            "propose_stage": self.run_("propose.py stage system/staging/drafts/other.json"),
            "people_map": self.run_("propose.py people map system/staging/drafts/sweep.json"),
            "minutes_stage": self.run_("minutes.py stage system/staging/drafts/other.json"),
            "sweep_stage": self.run_("sweep.py stage system/staging/drafts/sweep.json"),
            "sweep_lock": self.run_("sweep.py lock"), "sweep_unlock": self.run_("sweep.py unlock"),
            "sweep_done": self.run_("sweep.py done --started '2026-10-20 09:00' --normal"),
            "sweep_fail": self.run_("sweep.py fail --message x"),
            "vip_record": self.run_("sweep.py vip record system/staging/drafts/other.json"), "vip_seen": self.run_("sweep.py vip seen --all"),
            "ignore": self.run_("sweep.py ignore system/staging/drafts/other.json"),
            "filechange": self.run_("filechange.py delete inbox/x.vtt --why x"),
            "report": self.run_("report.py adhoc system/staging/drafts/other.json"),
            "dashboard": self.run_("build_dashboard.py"), "search_enrich": self.run_("search.py enrich set x"),
            "transcripts_direct": self.run_(f"transcripts.py record {FACTS}"),
            # the calendar commands with any other input, or more words
            "other_spec": self.run_("sweep.py calendar system/staging/drafts/other.json"),
            "spec_elsewhere": self.run_("sweep.py calendar projects/elsewhere.json"),
            "spec_dotdot": self.run_("sweep.py calendar system/staging/drafts/../drafts/calendar.json"),
            "spec_link": self.run_("sweep.py calendar system/staging/drafts/link.json"),
            "facts_other": self.run_("sweep.py transcripts record system/staging/drafts/other.json"),
            "window_days": self.run_("sweep.py window --days 7"), "extra_word": self.run_("sweep.py calendar-window --x"),
            "shell": ("Bash", {"command": "rm inbox/x.vtt"}), "two": ("Bash", {"command": "system/scripts/run sweep.py calendar-window; ls"}),
            # writes and reads anywhere else
            "write_other_draft": ("Write", {"file_path": f"{root}/system/staging/drafts/other.json"}),
            "write_minutes_draft": ("Write", {"file_path": f"{root}/system/staging/drafts/minutes.html"}),
            "write_link": ("Write", {"file_path": f"{root}/system/staging/drafts/link.json"}),
            "write_proposal": ("Write", {"file_path": f"{root}/system/staging/proposed-y.json"}),
            "write_calendar_itself": ("Write", {"file_path": f"{root}/system/staging/calendar.json"}),
            "write_root": ("Write", {"file_path": f"{root}/CLAUDE.md"}), "edit_inbox": ("Edit", {"file_path": f"{root}/inbox/x.vtt"}),
            "settings": ("Write", {"file_path": f"{root}/.claude/settings.json"}),
            "multi_edit": ("MultiEdit", {"file_path": f"{root}/{SPEC}"}),
            "read_claude_md": ("Read", {"file_path": f"{root}/CLAUDE.md"}), "read_inbox": ("Read", {"file_path": f"{root}/inbox/x.vtt"}),
            "read_settings": ("Read", {"file_path": f"{root}/system/config/settings.json"}),
            "grep": ("Grep", {"pattern": "x"}), "glob": ("Glob", {"pattern": "**/*.json"}), "skill": ("Skill", {"skill": "cx-sweep"}),
            # other tools: the web, the rest of Microsoft 365, subagents
            "web": ("WebFetch", {"url": "https://example.invalid"}), "search_web": ("WebSearch", {"query": "x"}),
            "mail": ("mcp__claude_ai_Microsoft_365__outlook_email_search", {"query": "x"}),
            "teams": ("mcp__claude_ai_Microsoft_365__chat_message_search", {"query": "x"}),
            "sharepoint": ("mcp__claude_ai_Microsoft_365__sharepoint_search", {"query": "x"}),
            "send": ("mcp__claude_ai_Microsoft_365__outlook_send_mail", {}),
            "change_event": ("mcp__claude_ai_Microsoft_365__outlook_update_event", {}),
            "other_connector": ("mcp__claude_ai_Todoist__add_task", {}), "task": ("Task", {}), "agent": ("Agent", {})})
        for name, ok in got.items():
            with self.subTest(name):
                self.assertFalse(ok, name)

    def test_the_typed_sweep_and_a_plain_chat_are_unchanged(self):
        """Mode "sweep" (a typed "refresh calendar", BL-309) still saves the calendar; a plain chat still can't stage proposals
        unconfirmed through propose.py or apply."""
        sweep = self.decide({"save": self.run_(f"sweep.py calendar {SPEC}"),
                             "apply": self.run_("tracker.py apply")}, mode="sweep")
        self.assertEqual(sweep, {"save": True, "apply": False})
        ask = self.decide({"apply": self.run_("tracker.py apply"),
                           "propose_stage": self.run_("propose.py stage system/staging/drafts/other.json")}, mode="ask")
        self.assertEqual(ask, {"apply": False, "propose_stage": False})


# The stand-in Claude for the server tests. For a calendar run (the hook's --mode calendar) it asks the run's own hook about a set
# of calls (exactly as Claude Code would, from --settings) and records each verdict, then does the calendar steps as cx-sweep's
# step 8 and 8b say: the window, calendar.json in drafts and the real sweep.py calendar, the transcripts todo, transcripts.json in
# drafts and the real transcripts record. A run whose message is "slow" waits a few seconds first (for the 409). Any other run
# records its arguments and answers "Plain chat.".
FAKE = r'''#!/usr/bin/env python3
import json, subprocess, sys, time
from datetime import date
from pathlib import Path
args = sys.argv[1:]
prompt = args[args.index("--") + 1] if "--" in args else ""
root = Path.cwd()
settings = args[args.index("--settings") + 1] if "--settings" in args else ""
verdicts, said, results = {}, [], []
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init", "session_id": "sess-c"})
def hook(tool, inp):
    cmd = json.loads(settings)["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    return subprocess.run(cmd, shell=True, cwd=root, input=json.dumps({"tool_name": tool, "tool_input": inp}),
                          capture_output=True, text=True, timeout=60).returncode
def bash(i, command):
    out({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": f"t{i}", "name": "Bash", "input": {"command": command}}]}})
    if hook("Bash", {"command": command}):
        out({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": f"t{i}", "is_error": True, "content": "refused"}]}})
        results.append([command, "refused"])
        return ""
    r = subprocess.run([sys.executable, "system/scripts/" + command.split()[1], *command.split()[2:]], cwd=root,
                       capture_output=True, text=True)
    out({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": f"t{i}", "is_error": r.returncode != 0,
                                                  "content": r.stdout + r.stderr}]}})
    results.append([command, r.returncode])
    return r.stdout
def write(rel, data):
    f = root / rel
    if hook("Write", {"file_path": str(f)}) == 0:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(data))
        return True
    return False
if prompt == "slow":
    time.sleep(4)
if "--mode calendar" in settings:
    calls = {"apply": ("Bash", {"command": "system/scripts/run tracker.py apply"}),
             "undo": ("Bash", {"command": "system/scripts/run tracker.py undo"}),
             "approve": ("Bash", {"command": "system/scripts/run review.py approve 1"}),
             "sweep_stage": ("Bash", {"command": "system/scripts/run sweep.py stage system/staging/drafts/x.json"}),
             "minutes_stage": ("Bash", {"command": "system/scripts/run minutes.py stage system/staging/drafts/x.json"}),
             "propose_stage": ("Bash", {"command": "system/scripts/run propose.py stage system/staging/drafts/x.json"}),
             "filechange": ("Bash", {"command": "system/scripts/run filechange.py delete inbox/x.vtt --why x"}),
             "write_staging": ("Write", {"file_path": str(root / "system/staging/proposed-x.json")}),
             "write_other_draft": ("Write", {"file_path": str(root / "system/staging/drafts/x.json")}),
             "write_root": ("Write", {"file_path": str(root / "CLAUDE.md")}),
             "mail": ("mcp__claude_ai_Microsoft_365__outlook_email_search", {"query": "x"}),
             "calendar_search": ("mcp__claude_ai_Microsoft_365__outlook_calendar_search", {"query": "x"}),
             "write_spec": ("Write", {"file_path": str(root / "system/staging/drafts/calendar.json")})}
    verdicts = {k: hook(t, i) for k, (t, i) in calls.items()}
    today = date.today().isoformat()
    bash(0, "system/scripts/run sweep.py calendar-window")
    if write("system/staging/drafts/calendar.json", {"days": {today: [
            {"id": "ev-r1", "start": "23:00", "end": "23:30", "title": "Pilot readiness review", "where": "Teams", "teams": True,
             "organiser": True, "sensitivity": "normal"},
            {"id": "ev-r2", "start": "23:30", "end": "23:45", "title": "Supplier checkpoint", "where": "Room 2", "teams": False,
             "organiser": "Jane Doe", "sensitivity": "normal"}]}}):
        said.append(bash(1, "system/scripts/run sweep.py calendar system/staging/drafts/calendar.json").strip())
    bash(2, "system/scripts/run sweep.py transcripts todo")
    if write("system/staging/drafts/transcripts.json", {"results": [{"id": "ev-r2", "online": False, "uri": None, "count": None,
                                                                    "error": None}]}):
        bash(3, "system/scripts/run sweep.py transcripts record system/staging/drafts/transcripts.json")
else:
    said = ["Plain chat. I've read the calendar.\nCONFIRM: Save the calendar | Saves it"]
with (root / "fake-calls.jsonl").open("a") as fh:
    fh.write(json.dumps({"prompt": prompt, "args": args, "verdicts": verdicts, "results": results}) + "\n")
text = "\n".join(s for s in said if s) or "Done."
out({"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}})
out({"type": "result", "result": text, "session_id": "sess-c", "num_turns": 3, "usage": {"input_tokens": 10, "output_tokens": 5}})
'''


class ThroughTheServer(unittest.TestCase):
    """The live server with the stand-in Claude: Refresh saves the calendar, and nothing else."""

    @classmethod
    def setUpClass(cls):
        from test_dashboard import populate
        from test_live_server import free_port
        cls.v = v = Vault()
        populate(v)
        fake = v.root / "fake_claude.py"
        fake.write_text(FAKE)
        fake.chmod(0o755)
        cfg = v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text(encoding="utf-8"))
        data.setdefault("backups", {})["daily"] = False
        data.setdefault("vip", {})["enabled"] = False
        cfg.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        cls.port = free_port()
        cls.base = f"http://127.0.0.1:{cls.port}"
        cls.proc = subprocess.Popen([sys.executable, str(v.root / "system/scripts/live_server.py")], cwd=v.root,
                                    env={**os.environ, "CREAITE_PORT": str(cls.port), "CREAITE_CLAUDE": str(fake)},
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(300):
            try:
                urllib.request.urlopen(cls.base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        html = urllib.request.urlopen(cls.base + "/").read().decode()
        cls.token = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)
        cls.v.cleanup()

    def post(self, path, body, token=None, headers=None):
        """(status, events or JSON) for a POST."""
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": token or self.token,
                                              **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                text = r.read().decode()
                status = r.status
        except urllib.error.HTTPError as e:
            with e:
                return e.code, json.loads(e.read() or b"{}")
        if text.startswith("data: ") or "\n\ndata: " in text:
            return status, [json.loads(x[6:]) for x in text.split("\n\n") if x.startswith("data: ")]
        return status, json.loads(text or "{}")

    def call(self, match):
        f = self.v.root / "fake-calls.jsonl"
        return [c for c in (json.loads(ln) for ln in f.read_text().splitlines()) if match(c)][-1]

    def staged(self):
        return sorted(p.name for p in (self.v.root / "system/staging").glob("proposed-*.json"))

    def rows(self):
        return [self.v.rows(t) for t in ("actions", "raid", "decisions")]

    @needs_diff
    def test_1_refresh_saves_the_calendar_and_nothing_else(self):
        import calendar_refresh as cr
        before, staged = self.rows(), self.staged()
        status, evs = self.post("/api/calendar/refresh", {"run": "c-test-1", "message": "sweep mail and apply everything"})
        self.assertEqual(status, 200, evs)
        kinds = [e["type"] for e in evs]
        for card in ("confirm", "editcard", "fieldcard", "changes", "cant"):
            self.assertNotIn(card, kinds)                                       # no go-ahead asked for, no card of any kind
        cal = next(e for e in evs if e["type"] == "calendar")
        self.assertEqual((cal["saved"], cal["meetings"], cal["transcripts"]), (True, 2, True), cal)
        closure = next(e for e in evs if e["type"] == "closure")
        self.assertTrue(closure["line"].startswith("Calendar saved: 2 meetings over"), closure)
        held = json.loads((self.v.root / "system/staging/calendar.json").read_text())
        self.assertEqual(sorted(e["title"] for d in held["days"].values() for e in d),
                         ["Pilot readiness review", "Supplier checkpoint"])
        self.assertTrue((self.v.root / "system/staging/transcripts.json").exists())
        self.assertFalse((self.v.root / SPEC).exists())                         # the sweep's own command consumed its input
        self.assertEqual(self.staged(), staged)                                 # nothing staged for Review
        self.assertEqual(self.rows(), before)                                   # nothing applied
        c = self.call(lambda c: "--mode calendar" in " ".join(c["args"]))
        self.assertEqual(c["prompt"], cr.build_prompt())                        # the fixed prompt: the body's words never reach it
        a = c["args"]
        self.assertIn("--held 1", a[a.index("--settings") + 1])                 # #60: the confidential-note check too
        self.assertNotIn("--add-dir", a)                                        # no project folder, no home folder
        self.assertEqual(a[a.index("--tools") + 1], "Read,Bash,Write,Edit,ToolSearch")
        allowed = a[a.index("--allowedTools") + 1].split(",")
        self.assertEqual(sorted(t for t in allowed if t.startswith("mcp__")),
                         ["mcp__claude_ai_Microsoft_365__outlook_calendar_search", "mcp__claude_ai_Microsoft_365__read_resource"])
        for absent in ("tracker.py", "review.py", "propose.py", "minutes.py", "filechange.py", "sweep.py stage", "sweep.py *",
                       "Write(system/staging/**)", "Skill", "Grep"):
            self.assertFalse(any(absent in t for t in allowed), absent)
        denied = a[a.index("--disallowedTools") + 1]
        for d in ("mcp__claude_ai_Microsoft_365__outlook_email_search", "Bash(python3 system/scripts/tracker.py*)",
                  "Bash(python3 system/scripts/sweep.py stage*)", "WebFetch"):
            self.assertIn(d, denied)
        self.assertIn("#265", a[a.index("--append-system-prompt") + 1])
        v = c["verdicts"]
        for allowed_call in ("calendar_search", "write_spec"):
            self.assertEqual(v[allowed_call], 0, allowed_call)
        for refused in ("apply", "undo", "approve", "sweep_stage", "minutes_stage", "propose_stage", "filechange", "write_staging",
                        "write_other_draft", "write_root", "mail"):
            self.assertEqual(v[refused], 2, refused)                            # the record and everything else stay out of reach
        self.assertEqual([r for _, r in c["results"]], [0, 0, 0, 0])            # the four calendar steps ran
        usage = [json.loads(x) for x in (self.v.root / "system/staging/run-usage.jsonl").read_text().splitlines()]
        self.assertEqual((usage[-1]["kind"], usage[-1]["label"]), ("calendar", "calendar"))     # Activity › Usage: its own kind

    @needs_diff
    def test_2_only_this_pages_own_requests(self):
        for headers, token in (({}, "forged"), ({"Host": "evil.example"}, None), ({"Origin": "https://evil.example"}, None),
                               ({"Sec-Fetch-Site": "cross-site"}, None)):
            with self.subTest(headers=headers, token=token):
                status, got = self.post("/api/calendar/refresh", {}, token=token, headers=headers)
                self.assertEqual(status, 403, got)
        status, got = self.post("/api/calendar/refresh", {"run": "c-own-1"}, headers={"Origin": self.base})
        self.assertEqual(status, 200, got)                                       # the page's own Origin is fine

    @needs_diff
    def test_3_one_run_at_a_time(self):
        first = threading.Thread(target=self.post, args=("/api/ask", {"message": "slow"}))
        first.start()
        try:
            for _ in range(100):
                status, running = self.post("/api/ask/running", {})
                if running.get("run") and not running["run"].get("done"):
                    break
                time.sleep(0.05)
            status, got = self.post("/api/calendar/refresh", {})
            self.assertEqual(status, 409, got)
            self.assertTrue(got.get("busy"))
        finally:
            first.join(timeout=60)

    @needs_diff
    def test_4_not_when_the_calendar_is_off_or_in_the_development_repository(self):
        cfg = self.v.root / "system/config/settings.json"
        keep = cfg.read_text(encoding="utf-8")
        data = json.loads(keep)
        data.setdefault("sweep", {}).setdefault("sources", {})["calendar"] = False
        cfg.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        try:
            status, got = self.post("/api/calendar/refresh", {})
            self.assertEqual(status, 400, got)
            self.assertIn("off in Settings", got["message"])
        finally:
            cfg.write_text(keep, encoding="utf-8")
        dev = self.v.root / ".creaite-dev"
        dev.write_text("")
        try:
            status, got = self.post("/api/calendar/refresh", {})
            self.assertEqual(status, 400, got)
            self.assertIn("development repository", got["message"])
        finally:
            dev.unlink()

    def test_5_a_model_worded_message_stays_a_plain_chat(self):
        """An ordinary ask message stays unconfirmed, whatever it carries; "refresh calendar" typed is still BL-309's sweep."""
        import calendar_refresh as cr
        for body in ({"message": cr.build_prompt()}, {"message": "refresh the calendar for Intake", "kind": "calendar",
                                                        "mode": "calendar"}):
            with self.subTest(body["message"][:30]):
                status, evs = self.post("/api/ask", body)
                self.assertEqual(status, 200, evs)
                c = self.call(lambda c, m=body["message"]: c["prompt"] == m)
                a = c["args"]
                self.assertIn("--mode ask", a[a.index("--settings") + 1])
                self.assertNotIn("#265", a[a.index("--append-system-prompt") + 1])
                self.assertEqual(c["verdicts"], {})
        status, evs = self.post("/api/ask", {"message": "refresh calendar"})
        self.assertEqual(status, 200, evs)
        a = self.call(lambda c: c["prompt"] == "refresh calendar")["args"]
        self.assertIn("--mode sweep", a[a.index("--settings") + 1])              # BL-309, unchanged


if __name__ == "__main__":
    unittest.main(verbosity=2)
