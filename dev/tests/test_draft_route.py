"""#183 (2.6): the live server's Draft email routes (POST /api/email/draft, /api/email/outlook-access). The 2.6.3 release carries them.

Run: python3 dev/tests/test_draft_route.py   (needs Google Chrome; skipped otherwise)
A stand-in `claude` (never a real model or Microsoft 365 call) answers in the stream-json shape: it calls the create-draft tool with
the arguments in its prompt and gives a fixed tool result (made, or refused, as its .mode file says), and keeps its argv.
"""
import json
import os
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
for up in HERE.parents:                       # found from any depth
    if (up / "dev" / "tests" / "live_browser.py").exists():
        sys.path.insert(0, str(up / "dev" / "tests"))
        sys.path.insert(0, str(up / "system" / "scripts"))
        break
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import d, populate  # noqa: E402
from test_tracker import action  # noqa: E402

START = os.getcwd()                        # restored after the class: every test's vault is removed with the folder we sit in
CREATE = "mcp__claude_ai_Microsoft_365__outlook_create_draft"
M365 = "mcp__claude_ai_Microsoft_365__"
SCOPES = M365 + "get_granted_scopes"
FAKE = r'''#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
here = os.path.abspath(__file__)
open(here + ".argv", "a", encoding="utf-8").write(json.dumps(args) + "\n")
open(here + ".cwd", "a", encoding="utf-8").write(os.getcwd() + "\n")
p = args[args.index("--") + 1]
mode = open(here + ".mode").read().strip() if os.path.exists(here + ".mode") else "made"
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init"})
if "access check" in p:
    out({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "a1", "name": "mcp__claude_ai_Microsoft_365__get_granted_scopes", "input": {}}]}})
    scopes = ["User.Read", "Mail.Read"] + (["Mail.ReadWrite"] if mode == "made" else [])
    out({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "a1", "content": json.dumps(scopes)}]}})
else:
    start = p.index("these arguments, copied byte for byte, the body unchanged: ") + len("these arguments, copied byte for byte, the body unchanged: ")
    a = json.loads(p[start:p.index("\nThen reply")])
    if mode == "inject":
        a = dict(a, bcc=["x@example.com"])          # a model driven by injected text
    hook = None
    if "--settings" in args:                          # Cap's M1: run the run's own PreToolUse hook as Claude Code would, before the tool
        import subprocess
        hook = json.loads(args[args.index("--settings") + 1])["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    def call(i, name, inp):
        out({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": i, "name": name, "input": inp}]}})
        ev = json.dumps({"tool_name": name, "tool_input": inp})
        h = subprocess.run(hook, shell=True, input=ev, capture_output=True, text=True) if hook else None
        if h is not None and mode == "nodecision":
            h.stdout = ""                              # a hook that returns no decision
        if h is not None and h.returncode == 2:
            return {"type": "tool_result", "tool_use_id": i, "is_error": True, "content": h.stderr}
        allow = name in args[args.index("--allowedTools") + 1].split(",")      # Claude Code: the allow list, or a hook's allow decision
        if not allow and h is not None and h.returncode == 0 and h.stdout.strip():
            try:
                allow = json.loads(h.stdout)["hookSpecificOutput"]["permissionDecision"] == "allow"
            except (ValueError, KeyError, TypeError):
                allow = False
        if not allow:                                 # headless default-deny: nothing is made
            return {"type": "tool_result", "tool_use_id": i, "is_error": True, "content": "permission denied"}
        open(here + ".made", "a").write("1\n")
        return ({"type": "tool_result", "tool_use_id": i, "content": json.dumps({"id": "AAMk1", "webLink": "https://outlook.office365.com/owa/?ItemID=AAMk1"})}
                if mode in ("made", "inject", "twice", "nodecision") else {"type": "tool_result", "tool_use_id": i, "is_error": True, "content": "ErrorAccessDenied: Access is denied."})
    res = [call("t1", "%s", a)] + ([call("t2", "%s", a)] if mode == "twice" else [])
    out({"type": "user", "message": {"content": res}})
out({"type": "result", "result": "{\"ok\": true}"})
''' % (CREATE, CREATE)
HTML = '<div style="color:#1a1a1a;"><p>Hi Sara,</p><table><tbody><tr><td>ABC-A-006</td></tr></tbody></table></div>'


class Route(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        populate(v)
        os.chdir(v.root)                       # #183 review L-c: the server starts in the vault, as launch.py starts it
        cls.addClassCleanup(os.chdir, START)
        v.propose("chase", [action(20, owner="Sara Example", due_date=d(-4), description="Send the test plan")])
        v.run("apply")
        f = v.root / "system/config/settings.json"
        s = json.loads(f.read_text())
        s["draft_email"] = {"outlook_drafts": True}
        f.write_text(json.dumps(s, indent=2))
        cls.fake = v.root / "fake_claude.py"
        cls.fake.write_text(FAKE)
        cls.fake.chmod(0o755)

    @classmethod
    def server_env(cls):
        return {"CREAITE_CLAUDE": str(cls.fake)}

    def post(self, path, body, token=True):
        return self.b.eval("""(async()=>{ const r=await fetch(%s,{method:'POST',headers:{'Content-Type':'application/json',
            'X-Creaite-Token':%s},body:JSON.stringify(%s)}); return {status:r.status, j:await r.json()}; })()"""
                           % (json.dumps(path), "D.token" if token else "''", json.dumps(body)))

    def body(self, **o):
        return {"action": "create", "to": "sara@example.com", "subject": "ABC-A-006 · Overdue: a quick reminder", "html": HTML,
                "ids": ["ABC-A-006"], "mode": "chase", "name": "Sara Example", **o}

    def mode(self, m):
        Path(str(self.fake) + ".mode").write_text(m)

    def argv(self):
        p = Path(str(self.fake) + ".argv")
        return [json.loads(ln) for ln in p.read_text().splitlines()] if p.exists() else []

    def cwds(self):
        p = Path(str(self.fake) + ".cwd")
        return [Path(ln).resolve() for ln in p.read_text().splitlines()] if p.exists() else []

    def made(self):
        p = Path(str(self.fake) + ".made")
        return len(p.read_text().splitlines()) if p.exists() else 0

    def test_the_hook_refuses_an_injected_bcc_and_a_second_draft_before_anything_is_made(self):
        """Cap's M1: the run is started with its own PreToolUse hook (--settings); an injected Bcc is refused before the tool runs
        (nothing made, nothing recorded), and a second create is refused though the first went through."""
        self.mode("inject")
        before, n = self.staging("chases.json"), self.made()
        r = self.post("/api/email/draft", self.body(ids=["ABC-A-020"]))
        self.assertFalse(r["j"]["ok"])
        self.assertFalse(r["j"]["made"])
        self.assertIn("nothing was made", r["j"]["reason"])
        self.assertEqual(self.made(), n)                                         # the tool never ran
        self.assertEqual(self.staging("chases.json"), before)
        self.mode("twice")
        r = self.post("/api/email/draft", self.body())
        self.assertFalse(r["j"]["ok"])
        self.assertEqual(self.made(), n + 1)                                     # one draft, the second refused by the hook
        self.assertTrue(r["j"]["made"])
        self.assertIn("delete it unsent", r["j"]["reason"])

    def test_with_no_hook_the_create_tool_is_not_allowed_and_nothing_is_made(self):
        """Fail closed: the create tool is not in --allowedTools, so a run that gets no hook cannot make the draft (the stand-in
        applies headless default-deny)."""
        self.mode("made")
        n = self.made()
        import subprocess
        p = subprocess.run([str(self.fake), "-p", "--allowedTools", "ToolSearch", "--",
                            "x these arguments, copied byte for byte, the body unchanged: {}\nThen reply"], capture_output=True, text=True)
        self.assertEqual(self.made(), n)
        self.assertIn("permission denied", p.stdout)

    def test_a_hook_that_gives_no_decision_makes_nothing(self):
        self.mode("nodecision")
        n, before = self.made(), self.staging("chases.json")
        r = self.post("/api/email/draft", self.body(ids=["ABC-A-020"]))
        self.assertFalse(r["j"]["ok"])
        self.assertEqual(self.made(), n)
        self.assertEqual(self.staging("chases.json"), before)

    def test_the_run_carries_a_hook_over_every_tool_and_its_request_file_is_removed_after(self):
        self.mode("made")
        self.assertTrue(self.post("/api/email/draft", self.body())["j"]["ok"])
        args = self.argv()[-1]
        hooks = json.loads(args[args.index("--settings") + 1])["hooks"]["PreToolUse"]
        self.assertEqual(hooks[0]["matcher"], "*")
        cmd = hooks[0]["hooks"][0]["command"]
        self.assertIn("draft_delivery.py hook ", cmd)
        self.assertFalse(Path(cmd.split()[-1].strip("'")).exists())             # removed when the run ended
        self.mode("made")
        self.post("/api/email/outlook-access", {})
        self.assertNotIn("--settings", self.argv()[-1])                           # the access run has no write tool: no hook

    def staging(self, name):
        p = self.v.root / "system/staging" / name
        return json.loads(p.read_text()) if p.exists() else None

    def test_a_draft_is_made_with_create_draft_only_and_the_chase_recorded(self):
        self.mode("made")
        r = self.post("/api/email/draft", self.body())
        self.assertEqual(r["status"], 200)
        self.assertTrue(r["j"]["ok"], r)
        self.assertEqual(r["j"]["web_link"], "https://outlook.office365.com/owa/?ItemID=AAMk1")
        self.assertEqual(r["j"]["chased"], ["ABC-A-006"])
        args = self.argv()[-1]
        allowed = args[args.index("--allowedTools") + 1].split(",")
        denied = args[args.index("--disallowedTools") + 1].split(",")
        self.assertEqual(allowed, ["ToolSearch"])                                 # the hook is the only path to the create tool
        self.assertNotIn(CREATE, denied)
        for t in ("outlook_send_draft", "outlook_send_mail", "outlook_update_draft", "Bash", "Write", "Edit", "Read"):
            self.assertIn(t if t[0].isupper() else "mcp__claude_ai_Microsoft_365__" + t, denied)
        self.assertNotIn("--dangerously-skip-permissions", args)
        self.assertEqual(self.staging("chases.json")["chases"][-1]["ids"], ["ABC-A-006"])
        self.assertEqual(len(self.staging("drafted.json")["drafted"]), 1)

    def test_neither_run_can_read_microsoft_365_and_neither_loads_the_vaults_context(self):
        """#183 review M1: the draft run denies every Microsoft 365 reading tool (mail, Teams, SharePoint) so a prompt injection in
        an email can't read one thing and put it in a draft; the access run denies all of them but get_granted_scopes. Neither
        loads a setting source (so none of the vault's allow rules, CLAUDE.md or session-start rule), neither starts in the vault,
        and ToolSearch is the only built-in."""
        import permissions
        self.mode("made")
        self.assertTrue(self.post("/api/email/draft", self.body())["j"]["ok"])
        self.assertTrue(self.post("/api/email/outlook-access", {})["j"]["can"])
        draft, access = self.argv()[-2:]
        for args, allowed in ((draft, ["ToolSearch"]), (access, [SCOPES, "ToolSearch"])):
            self.assertEqual(args[args.index("--allowedTools") + 1].split(","), allowed)
            denied = args[args.index("--disallowedTools") + 1].split(",")
            self.assertIn(M365 + "outlook_email_search", denied)                  # the reader a prompt injection would use
            for name in permissions.M365_READ:
                with self.subTest(tool=name, allowed=allowed):
                    (self.assertNotIn if M365 + name in allowed else self.assertIn)(M365 + name, denied)
            self.assertEqual(args[args.index("--setting-sources") + 1], "")
            self.assertEqual(args[args.index("--tools") + 1], "ToolSearch")
            self.assertIn("--no-session-persistence", args)
        for cwd in self.cwds()[-2:]:                                      # the server itself runs in the vault (load), the run does not
            self.assertNotEqual(cwd, self.v.root.resolve())
            self.assertNotIn(self.v.root.resolve(), cwd.parents)

    def test_a_copy_is_never_refused_for_markup_but_a_draft_is(self):
        """#183 review L1, through the route: the body carries the action, so a copy skips Outlook's markup check."""
        bad = '<p><span>x</span></p>'
        n = len(self.argv())
        self.assertTrue(self.post("/api/email/draft", self.body(action="copied", html=bad))["j"]["ok"])
        r = self.post("/api/email/draft", self.body(action="create", html=bad))
        self.assertFalse(r["j"]["ok"])
        self.assertIn("formatting Outlook won't take", r["j"]["reason"])
        self.assertEqual(len(self.argv()), n)                                     # refused before any run

    def test_a_refusal_records_nothing(self):
        self.mode("refused")
        before = self.staging("chases.json")
        r = self.post("/api/email/draft", self.body(ids=["ABC-A-020"]))
        self.assertFalse(r["j"]["ok"])
        self.assertEqual(r["j"]["reason"], "you don't have permission to write to this mailbox")
        self.assertEqual(self.staging("chases.json"), before)

    def test_off_refuses_before_any_run_and_no_token_is_refused(self):
        f = self.v.root / "system/config/settings.json"
        s = json.loads(f.read_text())
        s["draft_email"]["outlook_drafts"] = False
        f.write_text(json.dumps(s, indent=2))
        try:
            n = len(self.argv())
            r = self.post("/api/email/draft", self.body())
            self.assertFalse(r["j"]["ok"])
            self.assertIn("off in Settings", r["j"]["reason"])
            self.assertEqual(len(self.argv()), n)
        finally:
            s["draft_email"]["outlook_drafts"] = True
            f.write_text(json.dumps(s, indent=2))
        self.assertEqual(self.post("/api/email/draft", self.body(), token=False)["status"], 403)

    def test_a_copy_keeps_references_only(self):
        r = self.post("/api/email/draft", self.body(action="copied"))
        self.assertTrue(r["j"]["ok"])
        text = (self.v.root / "system/staging/drafted.json").read_text()
        self.assertNotIn("sara@example.com", text)
        self.assertNotIn("Overdue", text)

    def test_the_access_check_reads_the_granted_scopes_only(self):
        self.mode("made")
        r = self.post("/api/email/outlook-access", {})
        self.assertTrue(r["j"]["can"])
        args = self.argv()[-1]
        self.assertEqual(args[args.index("--allowedTools") + 1].split(","),
                         ["mcp__claude_ai_Microsoft_365__get_granted_scopes", "ToolSearch"])
        self.assertIn(CREATE, args[args.index("--disallowedTools") + 1].split(","))
        self.mode("refused")
        self.assertFalse(self.post("/api/email/outlook-access", {})["j"]["can"])


if __name__ == "__main__":
    unittest.main()
