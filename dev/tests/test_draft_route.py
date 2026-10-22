"""#183 (2.6): the live server's Draft email routes (POST /api/email/draft, /api/email/outlook-access), with live_server.diff applied.

The routes exist once the guarded diff (dev/proposals/draft-delivery/live_server.diff) is applied; until then `load` applies it to the
throwaway vault's copy of live_server.py (never to this tree), so the same checks run in both states.
Run: python3 dev/tests/test_draft_route.py   (needs Google Chrome; skipped otherwise)
A stand-in `claude` (never a real model or Microsoft 365 call) answers in the stream-json shape: it calls the create-draft tool with
the arguments in its prompt and gives a fixed tool result (made, or refused, as its .mode file says), and keeps its argv.
"""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
for up in HERE.parents:                       # run from dev/tests/ or from dev/proposals/draft-delivery/
    if (up / "dev" / "tests" / "live_browser.py").exists():
        sys.path.insert(0, str(up / "dev" / "tests"))
        sys.path.insert(0, str(up / "system" / "scripts"))
        break
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import d, populate  # noqa: E402
from test_tracker import action  # noqa: E402

PROPOSAL = HERE.parent.parent / "dev/proposals/draft-delivery/live_server.diff"

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
    out({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t1", "name": "%s", "input": a}]}})
    res = ({"type": "tool_result", "tool_use_id": "t1", "content": json.dumps({"id": "AAMk1", "webLink": "https://outlook.office365.com/owa/?ItemID=AAMk1"})}
           if mode == "made" else {"type": "tool_result", "tool_use_id": "t1", "is_error": True, "content": "ErrorAccessDenied: Access is denied."})
    out({"type": "user", "message": {"content": [res]}})
out({"type": "result", "result": "{\"ok\": true}"})
''' % CREATE
HTML = '<div style="color:#1a1a1a;"><p>Hi Sara,</p><table><tbody><tr><td>ABC-A-006</td></tr></tbody></table></div>'


class Route(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        populate(v)
        if "/api/email/draft" not in (v.root / "system/scripts/live_server.py").read_text():
            subprocess.run(["git", "apply", str(PROPOSAL)], cwd=v.root, check=True)       # the guarded diff, on the throwaway copy only
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
        self.assertEqual(allowed, [CREATE, "ToolSearch"])
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
        for args, allowed in ((draft, [CREATE, "ToolSearch"]), (access, [SCOPES, "ToolSearch"])):
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
