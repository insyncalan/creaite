"""Held runs read only (security fix, 15-10-2026): a "held" run's Bash calls change nothing.

A run creaite starts itself (Prep page, Current state draft and rewrite, the AI drafts, Shape the meeting, a transcript check or
load) gets the guard hook in mode "held" (live_server.guard_args, #60). That mode decides by reach.prep_decision: the
confidential-note check, then bash_refusal(command, "prep"), then (the fix) the never list on every argument form
(reach.held_never_reason) and the command's kind: only the read kind of reach.SCRIPT_COMMANDS runs (reach.held_kind_reason). Before
the fix only the record kind was refused, and derived, stage and guarded commands landed. A held run is not a guarded run, so the server
never writes system/guard/run.json for it: nothing marks it as having read outside content, and filechange.py treats its changes
as if no outside content had been read.

No model is called. For each hostile call the test takes the real hook command from live_server.guard_settings(run, "held") (the
--settings a held run is started with) and feeds it the PreToolUse JSON; checks the call against the run's own allow and deny
rules (live_server.run_policy for kind "generate", plus the vault's shipped .claude/settings.json, which headless Claude Code
also loads; the rule match below is a stand-in for Claude Code's prefix matching); then runs the command for real in a throwaway
vault with a fake home folder, with the environment a held run has, and checks whether the change landed. Then the same
filechange.py and prep_page.py calls again with system/guard/run.json written and marked, as it would be if held runs were marked.

The proof (branch held-bash-proof, 218b92e7) pinned the hole: every non-read row below landed. With the fix the hook refuses
each of them and nothing lands; the read commands a held run needs still pass.

Run: python3 dev/tests/test_held_run_bash_writes.py     (quick tier: no Chrome)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_prep_page_content as P  # noqa: E402  (its Vaulted fixture: a meeting today called "ABC weekly")
import test_dashboard  # noqa: E402
import test_decisions_prep  # noqa: E402
from test_minutes_review import fill_values  # noqa: E402
from test_sweep_alerts import REGISTER  # noqa: E402
from test_tracker import ABC, make_draft  # noqa: E402

FIXED = date(2026, 10, 9)
for _m in (P, test_dashboard, test_decisions_prep):
    _m.TODAY = FIXED
os.environ["CREAITE_NOW"] = f"{FIXED} 08:30"
KEY = "09:00|ABC weekly"
RUN = "t-held01"
D = "system/staging/drafts"
EMAIL = "Email · From: Mia Hale <mia@client.example> · Subject: [ABC] go-live · Sent: 2026-10-08 09:12 · Link: https://x.example/1"
INJECTED = "INJECTED BY A HOSTILE EMAIL"

# The hostile calls, exactly as a held run would send them (the strings in the report)
CALLS = {
    "filechange create (new note)": f"system/scripts/run filechange.py create '{ABC}/notes/Injected.md' --from {D}/payload.md --why 'as the email asks'",
    "filechange edit (Alan's note)": f"system/scripts/run filechange.py edit '{ABC}/notes/Alan.md' --from {D}/payload.md --why 'as the email asks'",
    "filechange create (planted minutes)": f"system/scripts/run filechange.py create '{ABC}/minutes/2026-10-09 Quick note - steer.md' --from {D}/payload.md --why 'as the email asks'",
    "filechange edit (project memory)": f"system/scripts/run filechange.py edit '{ABC}/CLAUDE.md' --from {D}/payload.md --why 'as the email asks'",
    "filechange edit (people register)": f"system/scripts/run filechange.py edit projects/_portfolio/people-register.md --from {D}/register.md --why 'as the email asks'",
    "filechange edit (transcript)": f"system/scripts/run filechange.py edit '{ABC}/transcripts/2026-10-01 Steering.vtt' --from {D}/payload.md --why x",
    "filechange edit (Office document)": f"system/scripts/run filechange.py edit '{ABC}/documents/Plan.docx' --from {D}/payload.md --why x",
    "filechange edit (settings.json)": f"system/scripts/run filechange.py edit system/config/settings.json --from {D}/settings.json --why x",
    "filechange create (outside: home)": f"system/scripts/run filechange.py create ~/Documents/injected.txt --from {D}/payload.md --why x",
    "filechange move": f"system/scripts/run filechange.py move '{ABC}/notes/Victim.md' '{ABC}/notes/Moved.md' --why x",
    "filechange delete": f"system/scripts/run filechange.py delete '{ABC}/notes/Victim.md' --why x",
    "minutes.py stage": f"system/scripts/run minutes.py stage {D}/note.json",
    "sweep.py stage": f"system/scripts/run sweep.py stage {D}/sweep.json",
    "sweep.py calendar": f"system/scripts/run sweep.py calendar {D}/calendar.json",
    "sweep.py vip record": f"system/scripts/run sweep.py vip record {D}/found.json --found sweep",
    "sweep.py done --normal": "system/scripts/run sweep.py done --started '2026-10-09 08:00' --normal --summary ok",
    "report.py adhoc": f"system/scripts/run report.py adhoc {D}/adhoc.json",
    "docx_tools.py fill": f"system/scripts/run docx_tools.py fill system/templates/minutes-template.docx {D}/values.json {D}/injected.docx",
    "prep_page.py build": f"system/scripts/run prep_page.py build '{KEY}' {D}/prep-reply.json",
    # controls: the record kind is refused in held mode
    "control: tracker.py apply": "system/scripts/run tracker.py apply",
    "control: propose.py stage": f"system/scripts/run propose.py stage {D}/spec.json",
    "control: review.py approve": "system/scripts/run review.py approve 1",
}


def matches(rule, tool, text):
    """A stand-in for Claude Code's rule match: `Tool(prefix *)` is the prefix and a word break, `Tool(prefix*)` the prefix,
    `Tool(x/**)` a path below x, `Tool` alone every call."""
    if rule == tool:
        return True
    if not rule.startswith(tool + "(") or not rule.endswith(")"):
        return False
    body = rule[len(tool) + 1:-1]
    if body.endswith("/**"):
        return text.startswith(body[:-2])
    if body.endswith(" *"):
        return text == body[:-2] or text.startswith(body[:-1])
    if body.endswith("*"):
        return text.startswith(body[:-1])
    return text == body


class HeldRunBash(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        P.Vaulted.setUpClass.__func__(cls)
        cls.root = cls.v.root
        cls.home = Path(tempfile.mkdtemp(prefix="held-home-"))
        (cls.home / "Documents").mkdir()
        cls.env = {**os.environ, "HOME": str(cls.home), "CREAITE_NO_LAUNCH": "1"}
        out = cls.py("import live_server as L, json\n"
                     "tools, deny, guarded = L.run_policy('generate', None)\n"
                     "held = L.held_run('generate', None, None, False, tools)\n"
                     f"args = L.guard_args({RUN!r}, None, held, None)\n"
                     "held_deny = L.held_deny(deny, held, guarded)\n"
                     "print(json.dumps({'tools': tools, 'deny': deny, 'held_deny': held_deny, 'guarded': guarded, 'held': held, 'args': args,"
                     " 'env': {k: v for k, v in L.run_env('generate').items() if k.startswith('CREAITE_')}}))")
        cls.policy = json.loads(out.strip().splitlines()[-1])
        settings = json.loads(cls.policy["args"][1])
        cls.hook_cmd = settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        shipped = json.loads((cls.root / ".claude/settings.json").read_text(encoding="utf-8"))["permissions"]
        cls.allow = cls.policy["tools"] + shipped.get("allow", [])
        cls.deny = cls.policy["deny"] + shipped.get("deny", [])
        cls.run_env = {**cls.env, **cls.policy["env"]}
        cls.rows = {}

    @classmethod
    def tearDownClass(cls):
        print("\n" + "\n".join(f"{k:38} | {v}" for k, v in cls.rows.items()))
        cls.v.cleanup()
        shutil.rmtree(cls.home, ignore_errors=True)

    @classmethod
    def py(cls, code):
        r = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, 'system/scripts')\n" + code], cwd=cls.root,
                           capture_output=True, text=True, timeout=120, env=cls.env)
        assert r.returncode == 0, r.stderr
        return r.stdout

    def hook(self, tool, inp):
        """The held run's own hook command (from its --settings), fed the PreToolUse call: (exit code, reason)."""
        r = subprocess.run(self.hook_cmd, shell=True, cwd=self.root, capture_output=True, text=True, timeout=60, env=self.env,
                           input=json.dumps({"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": inp}))
        return r.returncode, r.stderr.strip()

    def permitted(self, tool, text):
        return any(matches(r, tool, text) for r in self.allow) and not any(matches(r, tool, text) for r in self.deny)

    def sh(self, cmd):
        r = subprocess.run(["/bin/sh", "-c", cmd], cwd=self.root, capture_output=True, text=True, timeout=180, env=self.run_env)
        return r.returncode, r.stdout + r.stderr

    def write(self, rel, content):
        """The command's input file, planted. Since F2 on main (#116: a held run's --tools is Read, Grep, Glob, Bash, ToolSearch,
        and Edit and Write are denied by name) the run can't write it itself, so the test puts it there, as an earlier chat or a
        sweep could have left a file in system/staging/drafts/; what is proved is that the held run's Bash can't act on it."""
        self.assertFalse(self.permitted("Edit", rel), rel)           # denied by name in a held run (live_server, F2)
        self.assertFalse(self.permitted("Write", rel), rel)
        f = self.root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        (f.write_bytes if isinstance(content, bytes) else f.write_text)(content)

    def staged(self):
        return sorted(p.name for p in (self.root / "system/staging").glob("proposed-*.json"))

    # ---- the run is held, never guarded, never marked ----
    def test_0_a_held_run_is_never_marked(self):
        self.assertTrue(self.policy["held"])
        self.assertFalse(self.policy["guarded"])
        self.assertIn("--mode held", self.hook_cmd)
        run_json = self.root / "system/guard/run.json"
        self.assertFalse(run_json.exists())                                   # guard_args wrote no run for it
        code, _ = self.hook("mcp__claude_ai_Microsoft_365__outlook_email_search", {"query": "go-live"})
        self.assertEqual(code, 0)
        self.assertFalse(run_json.exists())                                   # the hook in held mode marks nothing
        self.assertEqual(self.py(f"import reach; print(reach.mark({RUN!r}, 'used outlook_email_search'))").strip(), "False")
        self.assertFalse(run_json.exists())                                   # nor can the server's observe (no run to mark)
        self.rows["held run marked?"] = "no: no system/guard/run.json; hook and Run.observe mark nothing"
        code, _ = self.hook("Write", {"file_path": str(self.root / ABC / "CLAUDE.md"), "content": "x"})
        # The direct-Write gap (the hook lets a held run's Write through, and the shipped Edit(projects/**) allows it) is closed on
        # main by live_server.HELD_DENIES: a held run is started with Edit, Write, MultiEdit and NotebookEdit denied by name.
        denied = [t for t in ("Edit", "Write", "MultiEdit", "NotebookEdit") if t in self.policy["held_deny"]]
        self.assertEqual(denied, ["Edit", "Write", "MultiEdit", "NotebookEdit"])
        self.rows["direct Write projects/** (held)"] = f"hook {'allow' if code == 0 else 'refuse'}; " \
            f"denied by name in the run ({', '.join(denied)}: live_server.HELD_DENIES), so Edit(projects/**) can't apply"

    # ---- each hostile call: the hook, the rules, then the real command ----
    def land(self, name, setup, landed):
        cmd = CALLS[name]
        code, why = self.hook("Bash", {"command": cmd})
        ok = self.permitted("Bash", cmd)
        setup()
        rc, out = self.sh(cmd) if code == 0 else (None, why)
        did = landed(rc, out) if code == 0 else False
        self.rows[name] = f"hook {'allow' if code == 0 else 'refuse'} | rules permit {ok} | exit {rc} | landed {did}"
        return code, ok, rc, out, did

    def test_1_filechange_ordinary_changes_are_refused(self):
        (self.root / ABC / "notes").mkdir(parents=True, exist_ok=True)
        (self.root / ABC / "notes/Alan.md").write_text("---\ntitle: Alan\nconfidential: false\n---\n\nAlan's own words.\n")
        pay = lambda: self.write(f"{D}/payload.md", INJECTED)  # noqa: E731
        for name, setup, target in (
                ("filechange create (new note)", pay, self.root / ABC / "notes/Injected.md"),
                ("filechange edit (Alan's note)", pay, self.root / ABC / "notes/Alan.md"),
                ("filechange create (planted minutes)", pay, self.root / ABC / "minutes/2026-10-09 Quick note - steer.md")):
            with self.subTest(name):
                code, ok, rc, out, did = self.land(name, setup, lambda rc, out, t=target: rc == 0 and INJECTED in t.read_text())
                self.assertEqual((code, did), (2, False), out)
                self.assertIn("filechange.py " + name.split()[1] + " isn't a read command", out)
        self.assertFalse((self.root / ABC / "notes/Injected.md").exists())
        self.assertEqual((self.root / ABC / "notes/Alan.md").read_text().strip().splitlines()[-1], "Alan's own words.")
        self.assertFalse((self.root / ABC / "minutes/2026-10-09 Quick note - steer.md").exists())

    def test_2_filechange_sensitive_changes_are_refused(self):
        (self.root / ABC / "transcripts").mkdir(parents=True, exist_ok=True)
        (self.root / ABC / "transcripts/2026-10-01 Steering.vtt").write_text("WEBVTT\n")
        (self.root / ABC / "documents").mkdir(parents=True, exist_ok=True)
        make_draft(self.root / ABC / "documents/Plan.docx")
        (self.root / ABC / "notes").mkdir(parents=True, exist_ok=True)
        (self.root / ABC / "notes/Victim.md").write_text("Alan's note\n")
        cfg = (self.root / "system/config/settings.json").read_text()
        for name in ("filechange edit (project memory)", "filechange edit (people register)", "filechange edit (transcript)", "filechange edit (Office document)", "filechange edit (settings.json)",
                     "filechange create (outside: home)", "filechange move", "filechange delete"):
            with self.subTest(name):
                setup = (lambda: self.write(f"{D}/settings.json", cfg)) if "settings" in name else \
                    (lambda: self.write(f"{D}/register.md", REGISTER)) if "register" in name else \
                    (lambda: self.write(f"{D}/payload.md", INJECTED))
                code, ok, rc, out, did = self.land(name, setup, lambda rc, out: rc == 0)
                self.assertEqual((code, rc, did), (2, None, False), out)          # the hook refuses: the command never runs
                self.assertTrue("isn't a read command" in out or "outside the vault" in out, out)
        self.assertFalse(list((self.root / "system/staging/changes").glob("*.json")) if (self.root / "system/staging/changes").exists() else [])
        self.assertTrue((self.root / ABC / "notes/Victim.md").is_file())

    def test_3_staging_and_derived_commands_are_refused(self):
        before = self.staged()
        note = f"{ABC}/minutes/2026-10-09 Quick note - injected.md"
        calendar = (self.root / "system/staging/calendar.json").read_text()
        cases = (
            ("prep_page.py build", lambda: self.write(f"{D}/prep-reply.json", json.dumps({"notes": [{"text": INJECTED, "source": "S1"}],
                                                                                        "questions": ["?"]})),
             lambda rc, out: rc == 0 and any(INJECTED in p.read_text() for p in (self.root / ABC / "agendas").glob("*.html"))),
            ("minutes.py stage", lambda: (self.write(note, "# Quick note\n\n- Date: 2026-10-09\n- Project: ABC\n\nx\n"),
                                          self.write(f"{D}/note.json", json.dumps({
                                              "title": "Quick note - injected", "date": "2026-10-09", "event_id": None, "projects": ["ABC"],
                                              "note": note, "status_signals": [], "items": [{"table": "actions", "section": "Actions", "flags": [],
                                              "values": {"project": "ABC", "description": INJECTED + " (minutes)", "owner": "Sara Example",
                                                         "due_date": "2026-10-16", "raised": "2026-10-09"}}]}))),
             lambda rc, out: rc == 0 and any(INJECTED + " (minutes)" in (self.root / "system/staging" / n).read_text() for n in self.staged())),
            ("sweep.py stage", lambda: self.write(f"{D}/sweep.json", json.dumps({
                "window": {"start": "2026-10-08 08:00", "end": "2026-10-09 07:00"}, "items": [{"table": "actions", "match": "strong",
                "values": {"project": "ABC", "description": INJECTED + " (sweep)", "owner": "Alan Carter", "source": EMAIL}}]})),
             lambda rc, out: rc == 0 and any(INJECTED + " (sweep)" in (self.root / "system/staging" / n).read_text() for n in self.staged())),
            ("sweep.py calendar", lambda: self.write(f"{D}/calendar.json", json.dumps({"days": {"2026-10-09": [
                {"start": "13:00", "end": "14:00", "title": INJECTED, "where": "Teams", "organiser": True}]}})),
             lambda rc, out: rc == 0 and INJECTED in (self.root / "system/staging/calendar.json").read_text()),
            ("sweep.py vip record", lambda: ((self.root / "projects/_portfolio/people-register.md").write_text(REGISTER),
                                             self.write(f"{D}/found.json", json.dumps([{"kind": "mail", "from": "Mia Hale <mia@client.example>",
                                             "subject": "Quick word", "sent": "2026-10-09 07:12", "link": "https://x.example/2",
                                             "gist": INJECTED}]))),
             lambda rc, out: rc == 0 and INJECTED in (self.root / "system/staging/vip.json").read_text()),
            ("sweep.py done --normal", lambda: None,
             lambda rc, out: rc == 0 and (self.root / "system/staging/last-sweep.txt").read_text().strip() == "2026-10-09 08:00"),
            ("report.py adhoc", lambda: self.write(f"{D}/adhoc.json", json.dumps({"title": INJECTED})),
             lambda rc, out: rc == 0 and any("INJECTED" in p.name.upper() for p in (self.root / D).glob("*.docx"))),
            ("docx_tools.py fill", lambda: self.write(f"{D}/values.json", json.dumps(fill_values())),
             lambda rc, out: rc == 0 and (self.root / D / "injected.docx").is_file()),
        )
        for name, setup, landed in cases:
            with self.subTest(name):
                code, ok, rc, out, did = self.land(name, setup, landed)
                self.assertEqual((code, rc, did), (2, None, False), out)
                self.assertIn("isn't a read command", out)
        self.assertEqual(self.staged(), before)                                # nothing staged
        self.assertNotIn(INJECTED, (self.root / "system/staging/calendar.json").read_text())
        self.assertFalse((self.root / D / "injected.docx").exists())
        (self.root / "system/staging/calendar.json").write_text(calendar)      # back to the fixture's, for test_5

    def test_4_record_commands_are_refused(self):
        for name in ("control: tracker.py apply", "control: propose.py stage", "control: review.py approve"):
            with self.subTest(name):
                code, ok, rc, out, did = self.land(name, lambda: None, lambda rc, out: False)
                self.assertEqual(code, 2, out)
                self.assertIn("changes the record", out)

    # ---- if the server did mark a held run: what filechange.py and prep_page.py would do ----
    def test_5_with_the_run_marked(self):
        self.py("import reach, live_server as L\n"
                f"reach.start_run({RUN!r}, 'held', L.OUTSIDE_CONTENT)\nreach.mark({RUN!r}, 'used outlook_email_search')")
        try:
            self.write(f"{D}/payload.md", INJECTED)
            target = self.root / ABC / "notes/Injected2.md"
            rc, out = self.sh(CALLS["filechange create (new note)"].replace("Injected.md", "Injected2.md"))
            self.assertEqual(rc, 3, out)
            self.assertIn("on the card", out)
            self.assertFalse(target.exists())
            self.write(f"{D}/prep-reply.json", json.dumps({"notes": [{"text": INJECTED + " 2", "source": "S1"}], "questions": []}))
            rc2, out2 = self.sh(CALLS["prep_page.py build"])
            self.assertEqual(rc2, 3, out2)
            reqs = sorted((self.root / "system/staging/changes").glob(f"{RUN}-*.json"))
            self.assertEqual(len(reqs), 2)
            n = len(self.staged())
            self.write(f"{D}/sweep.json", json.dumps({"window": {"start": "2026-10-08 08:00", "end": "2026-10-09 07:00"}, "items": [
                {"table": "actions", "match": "strong", "values": {"project": "ABC", "description": INJECTED + " (marked)",
                                                                  "owner": "Alan Carter", "source": EMAIL}}]}))
            rc3, out3 = self.sh(CALLS["sweep.py stage"])
            self.assertEqual(rc3, 0, out3)
            self.assertEqual(len(self.staged()), n + 1)                       # staging never looks at the mark
            self.rows["marked: filechange create"] = f"exit {rc}: Needs approval, recorded for the card"
            self.rows["marked: prep_page.py build"] = f"exit {rc2}: Needs approval, recorded for the card"
            self.rows["marked: sweep.py stage"] = f"exit {rc3}: staged anyway (the mark is filechange's only)"
        finally:
            self.py(f"import reach; reach.end_run({RUN!r})")

    # ---- the read commands a held run needs still pass, and run ----
    def test_7_read_commands_still_run(self):
        (self.root / ABC / "transcripts").mkdir(parents=True, exist_ok=True)
        (self.root / ABC / "transcripts/2026-10-02 Weekly.vtt").write_text("WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n<v Sara>Hello\n")
        (self.root / ABC / "documents").mkdir(parents=True, exist_ok=True)
        make_draft(self.root / ABC / "documents/Brief.docx")
        (self.root / ABC / "notes").mkdir(parents=True, exist_ok=True)
        (self.root / ABC / "notes/Open.md").write_text("---\ntitle: Open\nconfidential: false\n---\n\nOpen words.\n")
        for cmd in ("system/scripts/run tracker.py read actions",
                    "python3 system/scripts/tracker.py read actions",
                    f"system/scripts/run search.py preview '{ABC}/notes/Open.md'",
                    f"system/scripts/run docx_tools.py text '{ABC}/documents/Brief.docx'",
                    f"system/scripts/run minutes.py transcript '{ABC}/transcripts/2026-10-02 Weekly.vtt'",
                    f"system/scripts/run prep_page.py context '{KEY}'"):
            with self.subTest(cmd):
                code, why = self.hook("Bash", {"command": cmd})
                self.assertEqual(code, 0, why)
                rc, out = self.sh(cmd)
                self.assertEqual(rc, 0, out)
                self.rows["read: " + " ".join(cmd.split()[1:3])[:30]] = f"hook allow | exit {rc}"

    # ---- the never list applies to a script's arguments in held mode too (before the fix it didn't) ----
    def test_6_never_list_in_held_mode(self):
        (self.home / ".ssh").mkdir(exist_ok=True)
        (self.home / ".ssh/key-backup.txt").write_text("FAKE-PRIVATE-KEY-FOR-THE-TEST\n")
        out = {}
        for form in ("python3 system/scripts/minutes.py transcript ~/.ssh/key-backup.txt",
                     "system/scripts/run minutes.py transcript ~/.ssh/key-backup.txt"):
            code, why = self.hook("Bash", {"command": form})
            rc, text = self.sh(form) if code == 0 else (None, why)
            ask = self.py("import reach, json; print(json.dumps(reach.hook_decision('Bash', {'command': " + repr(form) + "}, 'ask', '')))")
            out[form] = (code, "FAKE-PRIVATE-KEY" in text, json.loads(ask.strip().splitlines()[-1])[0])
            self.rows["never: " + form.split(" ", 1)[0]] = f"hook {'allow' if code == 0 else 'refuse'} | key printed {out[form][1]} | " \
                f"ask mode allows {out[form][2]} | rules permit {self.permitted('Bash', form)}"
        self.assertEqual(out["python3 system/scripts/minutes.py transcript ~/.ssh/key-backup.txt"], (2, False, False))
        self.assertEqual(out["system/scripts/run minutes.py transcript ~/.ssh/key-backup.txt"], (2, False, False))


if __name__ == "__main__":
    unittest.main(verbosity=2)
