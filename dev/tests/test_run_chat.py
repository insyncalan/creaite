"""BL-326 (v1.9.5): ask creaite shows the ask, the activity and the outcome of a run creaite starts itself, never its machine text.

A Prep page, Generate (Current state) and Make it executive, the AI drafts (Draft agenda, Shape this meeting, Polish and the rest),
a meeting's transcript check or load and Close the day's catch-up sweep are runs creaite starts itself. Wherever ask creaite shows
one it shows exactly three things:
- the ask: one plain line, as if Alan had typed it (the run's label: "Prep page for ABC weekly, Wednesday 14th October 09:00");
- the activity: the working line and "✓ n steps", each step in plain words ("Searching mail", "Reading the tracker");
- the closure: one line with the outcome and a link ("Saved the prep page in Example Programme › agendas · Open"), or what
  went wrong and what to do; the same for success, failure and Stop.
Never the prompt, JSON, HTML or a tool's raw output. The chat history keeps the plain lines only (the day's own chat,
runs-YYYY-MM-DD), never the prompt; the debug log keeps the run record (IDs and counts). A chat Alan types is unchanged.

The stand-in Claude below makes three tool calls (a file read, a creaite script, a Microsoft 365 mail search) whose raw results are
JSON, then replies with JSON and HTML, so anything machine-made that reached the panel would show.

Server side: the real routes (through a stand-in handler) start each kind of run against the stand-in Claude in a throwaway vault.
Browser: the panel draws a Prep page run (success, failure, Stop), a draft and a transcript check with only the three things.

Run: python3 dev/tests/test_run_chat.py   (the browser tests need Google Chrome; skipped otherwise)
"""
import json
import subprocess
import sys
import threading
import time
import unittest
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_tracker import Vault  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
TODAY = date.today().isoformat()

FAKE = r'''#!/usr/bin/env python3
import json, os, sys, time
args = sys.argv[1:]
p = args[args.index("-p") + 1]
mode = (open("fake_mode.txt").read().strip() if os.path.exists("fake_mode.txt") else "ok")
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init", "session_id": "sess-run"})
calls = [("t1", "Read", {"file_path": "projects/ABC Example Programme/CLAUDE.md"}),
         ("t2", "Bash", {"command": "system/scripts/run tracker.py read ABC --json"}),
         ("t3", "mcp__claude_ai_Microsoft_365__outlook_email_search", {"query": "subject:\"Northgate\" {env}"})]
for i, (cid, name, inp) in enumerate(calls):
    out({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": cid, "name": name, "input": inp}]}})
    out({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": cid, "is_error": False,
                                                  "content": json.dumps({"value": [{"raw": "<b>raw</b>"}]})}]}})
    if mode == "slow" and i == 0:
        time.sleep(30)
if mode == "fail":
    sys.stderr.write('Error: {"type": "api_error", "message": "<html>overloaded</html>"}\n')
    sys.exit(1)
if p.startswith("creaite prep page"):
    text = json.dumps({"about": "The weekly ABC check-in.", "item_reasons": {}, "notes": [], "questions": [], "m365": "searched"})
elif p.startswith("Write the client messaging"):
    text = ("What it is: Access to your data for testing is late.\nWhat it means for you: Testing may start later.\n"
            "What is being done: The team is raising it with your leadership.\nREMOVED:\n- nothing")
else:
    text = '{"title": "Raise data access"} <div class="x">HTML from the model</div>'
out({"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}})
out({"type": "result", "result": text, "session_id": "sess-run"})
'''

MEETING = {"id": "t1", "start": "09:00", "end": "10:00", "title": "ABC weekly", "where": "Teams", "teams": True,
           "organiser": "Jane Doe", "all_day": False, "private": False, "sensitivity": "normal",
           "body": "Agenda: test licences; UAT readiness", "attendees": []}

HARNESS = r'''
import json, sys, threading, time
from datetime import datetime
sys.path.insert(0, "system/scripts")
import live_server as L

class H:
    """A stand-in request handler: the routes answer through it, and following a run returns the run."""
    exec_options, exec_request = L.Handler.exec_options, L.Handler.exec_request
    def send(self, code, body):
        raise SystemExit(f"route refused: {code} {body}")
    def follow(self, run, *a, **k):
        return run
    def numbered(self):
        return False

def mode(m):
    open("fake_mode.txt", "w").write(m)

def wait(run):
    with run.cond:
        run.cond.wait_for(lambda: run.done, timeout=60)
    run.seen = True
    return run

def start(name):
    h = H()
    if name == "prep":
        return L.prep_page_route(h, {"key": "09:00|ABC weekly"})
    if name == "current":
        return L.Handler.generate(h, {"code": "ABC"})
    if name == "rewrite":
        return L.Handler.current_rewrite(h, {"code": "ABC", "text": "ABC is on track."})
    if name == "draft":
        return L.draft_route(h, {"kind": "client", "id": "ABC-A-001"})
    if name == "agenda":
        return L.draft_route(h, {"kind": "agenda", "key": "09:00|ABC weekly"})
    if name == "check":
        return L.Handler.transcript_run(h, {"id": "t1"}, "check")
    if name == "load":
        return L.Handler.transcript_run(h, {"id": "t1"}, "load")
    if name == "sweep":
        return L.RUNS[L.start_catchup(datetime.now())["run"]["id"]]
    raise SystemExit(name)

out = {}
for name, m in json.loads(sys.argv[1]):
    mode(m)
    run = start(name)
    if m == "slow":
        for _ in range(300):
            if run.steps:
                break
            time.sleep(0.05)
        run.request_stop()
    wait(run)
    out[f"{name}/{m}"] = {"summary": run.summary(), "events": run.events, "prompt": run.message}
mode("ok")
print(json.dumps(out))
'''


def load(v):
    from test_dashboard import populate
    populate(v)
    (v.root / "system/staging/calendar.json").write_text(json.dumps({"fetched": f"{TODAY} 07:00", "days": {TODAY: [MEETING]}}))
    fake = v.root / "fake_claude.py"
    fake.write_text(FAKE)
    fake.chmod(0o755)


MACHINE = ("{", "}", "<", ">", "system/scripts", "mcp__", "tracker.py", "Running ", "creaite prep page", "JSON", "raw")


class Server(unittest.TestCase):
    """Every kind of run creaite starts, through its real route, against the stand-in Claude."""
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        cls.addClassCleanup(cls.v.cleanup)
        load(cls.v)
        runs = [("prep", "ok"), ("prep", "fail"), ("prep", "slow"), ("current", "ok"), ("rewrite", "ok"), ("draft", "ok"),
                ("draft", "fail"), ("agenda", "ok"), ("check", "ok"), ("load", "ok"), ("sweep", "ok"), ("sweep", "slow")]
        r = subprocess.run([sys.executable, "-c", HARNESS, json.dumps(runs)], cwd=cls.v.root, capture_output=True, text=True,
                           timeout=600, env={**__import__("os").environ, "CREAITE_CLAUDE": str(cls.v.root / "fake_claude.py")})
        if r.returncode:
            raise AssertionError(r.stderr[-3000:])
        cls.got = json.loads(r.stdout.strip().splitlines()[-1])

    def clean(self, text, what):
        for bad in MACHINE:
            self.assertNotIn(bad, text, f"{what}: machine text {bad!r} in {text!r}")

    def test_each_run_shows_only_the_ask_the_steps_and_the_closure(self):
        for name, run in self.got.items():
            with self.subTest(name):
                s, evs = run["summary"], run["events"]
                self.assertTrue(s["plain"])
                self.assertNotEqual(s["message"], run["prompt"])
                self.clean(s["message"], "the ask")
                steps = [e["label"] for e in evs if e["type"] == "step"]
                self.assertTrue(steps, evs)
                for label in steps:
                    self.clean(label, "a step")
                closures = [e for e in evs if e["type"] == "closure"]
                self.assertEqual(len(closures), 1, evs)
                self.clean(closures[0]["line"], "the closure")
                self.assertEqual(evs[-1]["type"], "done")
                self.assertEqual(evs[-2]["type"], "closure")         # the closure is the last thing before done
                self.assertIsNone(evs[-1]["chat"])                   # never the panel's chat
                self.assertIsNone(evs[-1]["session"])
                href = closures[0].get("href")
                self.assertTrue(href is None or href.startswith("#"), href)

    def test_the_asks_are_plain_lines(self):
        ask = {k: v["summary"]["message"] for k, v in self.got.items()}
        self.assertRegex(ask["prep/ok"], r"^Prep page for ABC weekly, \w+day \d+(st|nd|rd|th) \w+ 09:00$")
        self.assertEqual(ask["current/ok"], "Draft the current state for Example Programme")
        self.assertEqual(ask["rewrite/ok"], "Make the current state for Example Programme executive")
        self.assertEqual(ask["draft/ok"], "Draft client wording for ABC-A-001")
        self.assertRegex(ask["agenda/ok"], r"^Draft the agenda and invite text for ABC weekly, \w+day .* 09:00$")
        self.assertEqual(ask["check/ok"], f"Check the transcript of “ABC weekly” ({TODAY[8:]}-{TODAY[5:7]}-{TODAY[:4]} at 09:00)")
        self.assertTrue(ask["load/ok"].startswith("Load the transcript of “ABC weekly”"))
        self.assertEqual(ask["sweep/ok"], "Catch-up sweep: mail and Teams since the last sweep")

    def test_the_steps_are_in_plain_words(self):
        steps = [e["label"] for e in self.got["prep/ok"]["events"] if e["type"] == "step"]
        self.assertEqual(steps, ["Reading the project's memory", "Reading the tracker", "Searching mail"])

    def test_the_closures(self):
        line = lambda k: next(e for e in self.got[k]["events"] if e["type"] == "closure")    # noqa: E731
        ok = line("prep/ok")
        self.assertTrue(ok["ok"])
        self.assertEqual(ok["line"], "Saved the prep page in Example Programme › agendas")
        self.assertEqual(ok["link"], "Open")
        self.assertTrue(ok["href"].startswith("#prep=" + TODAY), ok)
        self.assertTrue((self.v.root / f"projects/ABC Example Programme/agendas/{TODAY} Prep - ABC weekly.html").exists())
        fail = line("prep/fail")
        self.assertFalse(fail["ok"])
        self.assertTrue(fail["line"].startswith("Couldn't finish:"), fail)
        self.assertIn("Try again", fail["line"])
        stop = line("prep/slow")
        self.assertFalse(stop["ok"])
        self.assertEqual(stop["line"], "Stopped: no prep page was written. Press Prep page to start again.")
        self.assertTrue(line("sweep/slow")["line"].startswith("Stopped:"))
        self.assertEqual(line("current/ok")["href"], "#cockpit=ABC")
        self.assertEqual(line("draft/ok")["line"], "Drafted the client wording for ABC-A-001: check it before you use it")
        self.assertEqual(line("draft/ok")["href"], "#item=ABC-A-001")
        self.assertTrue(line("draft/fail")["line"].startswith("Couldn't finish:"))
        self.assertEqual(line("sweep/ok")["href"], "#review")
        self.assertTrue(line("check/ok")["line"])                       # the transcript job's own plain outcome

    def test_the_feature_still_gets_its_reply(self):
        # the draft's own pane reads the reply (text) and its "draft" event; ask creaite never draws them
        evs = self.got["draft/ok"]["events"]
        self.assertTrue(any(e["type"] == "draft" and e.get("ok") for e in evs), evs)
        self.assertTrue(any(e["type"] == "text" for e in evs))

    def test_the_history_keeps_the_plain_lines_never_the_prompt(self):
        f = self.v.root / f"system/staging/ask/runs-{TODAY}.json"
        rec = json.loads(f.read_text(encoding="utf-8"))
        raw = f.read_text(encoding="utf-8")
        self.assertTrue(rec["title"].startswith("Runs creaite started"))
        self.assertIsNone(rec.get("session"))
        for run in self.got.values():
            if len(run["prompt"]) > 20:                        # the catch-up sweep's prompt is the one word "sweep"
                self.assertNotIn(run["prompt"][:60], raw)
        for bad in ("creaite prep page", "Raise data access", "HTML from the model", "<", "system/scripts", "mcp__"):
            self.assertNotIn(bad, raw)
        yours = [m for m in rec["messages"] if m["who"] == "you"]
        replies = [m for m in rec["messages"] if m["who"] == "creaite"]
        self.assertEqual(len(yours), len(self.got))
        self.assertTrue(all(m.get("plain") for m in replies))
        self.assertEqual({m["text"] for m in yours}, {r["summary"]["message"] for r in self.got.values()})
        closures = {next(e["line"] for e in r["events"] if e["type"] == "closure") for r in self.got.values()}
        self.assertEqual({m["text"] for m in replies}, closures)

    def test_the_debug_log_keeps_the_run_record_without_text(self):
        logs = list((self.v.root / "system/logs").glob("debug-*.log"))
        text = "".join(p.read_text(encoding="utf-8") for p in logs)
        prep = self.got["prep/ok"]["summary"]["id"]
        self.assertIn(f"{prep} prep started: prompt", text)
        self.assertIn(f"{prep} prep ended ok: 3 steps, reply", text)
        for bad in ("creaite prep page", "The weekly ABC check-in", "Raise data access"):
            self.assertNotIn(bad, text)


class PlainParts(unittest.TestCase):
    """The pieces in plain code: the step words, the drafts' lines."""

    def test_plain_steps(self):
        sys.path.insert(0, str(REPO / "system/scripts"))
        import live_server as L
        cases = [("Bash", {"command": "system/scripts/run prep_page.py context x"}, "Reading the meeting's context"),
                 ("Bash", {"command": "rm -rf /"}, "Running a creaite step"),
                 ("Read", {"file_path": "projects/ABC/minutes/2026-10-01 Steering.docx"}, "Reading 2026-10-01 Steering.docx"),
                 ("Read", {"file_path": "system/staging/drafts/x.json"}, "Reading creaite's own notes"),
                 ("mcp__claude_ai_Microsoft_365__teams_list_channel_messages", {}, "Reading Teams channels"),
                 ("mcp__claude_ai_Microsoft_365__read_resource", {"uri": "x"}, "Reading a meeting, a message or a chat"),
                 ("WebFetch", {"url": "https://example.com"}, "Reading a web page"),
                 ("Glob", {"pattern": "**/*"}, "Searching the vault"), ("Mystery", {}, "Working")]
        for name, inp, words in cases:
            self.assertEqual(L.plain_step(name, inp), words)

    def test_every_draft_kind_has_a_plain_ask_and_closure(self):
        sys.path.insert(0, str(REPO / "system/scripts"))
        import drafts
        for kind in drafts.KINDS:
            with self.subTest(kind):
                lines = drafts.run_lines({"kind": kind, "id": "ABC-A-001", "code": "ABC", "key": "09:00|ABC weekly",
                                          "ids": ["ABC-A-001"], "form": "email"})
                self.assertIn(kind, drafts.RUN_LINES)
                for k in ("ask", "done"):
                    self.assertTrue(lines[k])
                    self.assertNotRegex(lines[k], r"[{}<>]")


class Panel(LiveBrowserCase):
    """The panel draws a run creaite started with exactly the ask, the steps and the closure."""
    width, height = 1400, 900

    @classmethod
    def load(cls, v):
        load(v)

    @classmethod
    def server_env(cls):
        return {"CREAITE_CLAUDE": str(cls.v.root / "fake_claude.py")}

    def token(self):
        return self.b.eval("D.token")

    def post(self, path, body, stream=False):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token()})
        with urllib.request.urlopen(req, timeout=90) as r:
            return [json.loads(x.decode()[6:]) for x in r if x.decode().startswith("data: ")] if stream else json.loads(r.read())

    def mode(self, m):
        (self.v.root / "fake_mode.txt").write_text(m)

    def started_elsewhere(self, path, body):
        """Start a run as its own feature would (a Prep page button), reading its stream in the background."""
        t = threading.Thread(target=lambda: self.post(path, body, stream=True), daemon=True)
        t.start()
        for _ in range(200):
            r = self.post("/api/ask/running", {})
            if r.get("run"):
                return r["run"], t
            time.sleep(0.05)
        self.fail("the run didn't start")

    def drawn(self):
        b = self.b
        b.wait("document.querySelector('#chLog .runend')", 60)
        return {"text": b.eval("document.getElementById('chLog').textContent"),
                "shown": b.eval("document.getElementById('chLog').innerText"),
                "you": b.eval("[...document.querySelectorAll('#chLog .msg.u')].map(m=>m.textContent)"),
                "replies": b.eval("[...document.querySelectorAll('#chLog .msg.a')].map(m=>m.className+'|'+m.textContent)"),
                "steps": b.eval("[...document.querySelectorAll('#chLog .step.steps summary')].map(s=>s.textContent)")}

    def three_things(self, d, ask, closure):
        self.assertEqual(d["you"], [ask])
        self.assertEqual(len(d["replies"]), 1, d)                          # the closure, and nothing Claude said
        self.assertIn("runend", d["replies"][0])
        self.assertIn(closure, d["replies"][0])
        self.assertEqual(len(d["steps"]), 1, d)
        self.assertRegex(d["steps"][0], r"✓ \d+ steps?")
        for bad in MACHINE:
            self.assertNotIn(bad, d["text"], d["text"])

    def test_a_prep_page_run_success(self):
        self.mode("ok")
        run, t = self.started_elsewhere("/api/prep/page", {"key": "09:00|ABC weekly"})
        self.assertTrue(run["plain"])
        t.join(60)
        self.b.eval("openChat(); reattach()")
        d = self.drawn()
        self.three_things(d, run["message"], "Saved the prep page in Example Programme › agendas")
        self.assertTrue(d["you"][0].startswith("Prep page for ABC weekly, "))
        href = self.b.eval("document.querySelector('#chLog .runend a[data-runhref]').getAttribute('href')")
        self.assertTrue(href.startswith("#prep="), href)
        self.b.eval("document.querySelector('#chLog .runend a[data-runhref]').click()")
        self.b.wait("location.hash.startsWith('#prep=')", 10)

    def test_a_prep_page_run_that_fails(self):
        self.mode("fail")
        run, t = self.started_elsewhere("/api/prep/page", {"key": "09:00|ABC weekly"})
        t.join(60)
        self.b.eval("openChat(); reattach()")
        d = self.drawn()
        self.three_things(d, run["message"], "Couldn't finish: Claude Code stopped with a problem. Try again")
        self.assertNotIn("overloaded", d["text"])

    def test_a_prep_page_run_that_is_stopped(self):
        self.mode("slow")
        run, t = self.started_elsewhere("/api/prep/page", {"key": "09:00|ABC weekly"})
        self.b.eval("openChat(); reattach()")
        self.b.wait("RUN&&document.querySelector('#chLog .step.steps')", 20)
        self.b.eval("stopAsk()")
        d = self.drawn()
        self.three_things(d, run["message"], "Stopped: no prep page was written. Press Prep page to start again.")

    def test_a_draft_run(self):
        self.mode("ok")
        run, t = self.started_elsewhere("/api/draft", {"kind": "client", "id": "ABC-A-001"})
        t.join(60)
        self.b.eval("openChat(); reattach()")
        d = self.drawn()
        self.three_things(d, "Draft client wording for ABC-A-001",
                          "Drafted the client wording for ABC-A-001: check it before you use it")
        self.assertNotIn("Access to your data", d["text"])                    # the draft itself stays in its own pane

    def test_a_transcript_check_in_the_panel(self):
        self.mode("ok")
        self.b.eval("openChat(); checkMeeting(MTG().find(m=>m.id==='t1'))", wait=False)
        d = self.drawn()
        self.assertEqual(len(d["you"]), 1)
        self.assertTrue(d["you"][0].startswith("Check the transcript of “ABC weekly”"))
        self.assertEqual(len(d["replies"]), 1, d)
        for bad in MACHINE:
            self.assertNotIn(bad, d["text"], d["text"])

    def test_the_history_draws_the_plain_lines(self):
        self.mode("ok")
        _, t = self.started_elsewhere("/api/prep/page", {"key": "09:00|ABC weekly"})
        t.join(60)
        self.post("/api/ask/ack", {"run": self.post("/api/ask/running", {})["run"]["id"]})
        self.b.eval(f"openChat(); loadChat('runs-{TODAY}')")
        d = self.drawn()
        self.assertTrue(d["you"][-1].startswith("Prep page for ABC weekly, "))
        self.assertIn("Saved the prep page in Example Programme › agendas", d["replies"][-1])
        for bad in MACHINE:
            self.assertNotIn(bad, d["text"], d["text"])

    def test_a_chat_alan_types_is_unchanged(self):
        self.mode("ok")
        self.b.eval("openChat(); $('#chIn').value='How is ABC?'; send()", wait=False)
        self.b.wait("[...document.querySelectorAll('#chLog .msg.a')].some(m=>m.textContent.includes('Raise data access'))", 30)
        self.assertFalse(self.b.eval("!!document.querySelector('#chLog .runend')"))


if __name__ == "__main__":
    unittest.main()
