"""BL-306: a change Alan confirms in ask creaite is applied once. The v1.7.0 hand check: "change the owner of FAL-A-010" → the model
asked with CONFIRM: (not BL-258's CHANGE: card) → Go ahead → the confirmed run staged the change with propose.py and stopped, so it
then needed "apply" and a second confirmation. The live server now applies what a confirmed run staged when the run ends.

The real live server with a stand-in `claude` that, like the hand check, asks with CONFIRM: and, once confirmed, stages the change by
running the real `propose.py stage` and reporting its output as a Bash tool result.

- auto-apply on: Go ahead → applied at once, the chat names the item with its before → after and the apply, and Undo reverses it
  with nothing left in Review; another approved proposal already waiting is not applied with it;
- auto-apply off: it stays staged, and the chat says so;
- BL-267 holds: a run Alan hasn't confirmed that reports a staged change gets nothing applied;
- in the browser: the confirm card's Go ahead → "Applied: …" with Undo, the dashboard's data updates, Undo puts it back.

Run: python3 dev/tests/test_ask_confirmed_apply.py   (the browser test needs Google Chrome; skipped otherwise)
"""
import json
import re
import subprocess
import sys
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

FAKE = r'''#!/usr/bin/env python3
import json, os, subprocess, sys
args = sys.argv[1:]
message = args[args.index("-p") + 1].split("\n")[0]
system = args[args.index("--append-system-prompt") + 1] if "--append-system-prompt" in args else ""
confirmed = system.startswith("Alan has confirmed")
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init", "session_id": "sess-conf"})


def stage(words):
    spec = {"items": [{"op": "update", "table": "actions", "id": words[1], "changes": {words[2]: " ".join(words[3:])}}]}
    os.makedirs("system/staging/drafts", exist_ok=True)
    with open("system/staging/drafts/owner.json", "w") as f:
        json.dump(spec, f)
    cmd = "system/scripts/run propose.py stage system/staging/drafts/owner.json"
    r = subprocess.run([sys.executable, "system/scripts/propose.py", "stage", "system/staging/drafts/owner.json"],
                       capture_output=True, text=True)
    out({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": cmd}}]}})
    out({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1", "is_error": r.returncode != 0,
                                                  "content": r.stdout + r.stderr}]}})


if message.startswith("Go ahead: ") and confirmed:          # Go ahead: change <ID> <field> <value>
    stage(message[len("Go ahead: "):].split())
    text = "Staged and approved; it'll be written at your next apply."
elif message.startswith("change"):                           # asks with CONFIRM:, as in the hand check
    text = "That changes " + message.split()[1] + ".\nCONFIRM: " + message + " | Sets it in the tracker"
elif message.startswith("sneak"):                            # an unconfirmed run that reports a staged change
    stage(["change"] + message.split()[1:])
    text = "Staged."
else:
    text = "Nothing to change."
out({"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}})
out({"type": "result", "result": text, "session_id": "sess-conf"})
'''


def load_fake(v):
    from test_dashboard import populate
    populate(v)
    fake = v.root / "fake_claude.py"
    fake.write_text(FAKE)
    fake.chmod(0o755)


class ConfirmedApplyServer(unittest.TestCase):
    """The server's side, over HTTP (no browser)."""

    @classmethod
    def setUpClass(cls):
        cls.addClassCleanup(cls.stop_server)
        cls.start_server()

    load = classmethod(lambda cls, v: load_fake(v))
    server_env = classmethod(lambda cls: {"CREAITE_CLAUDE": str(cls.v.root / "fake_claude.py")})
    start_server = classmethod(LiveBrowserCase.start_server.__func__)
    stop_server = classmethod(LiveBrowserCase.stop_server.__func__)

    def token(self):
        html = urllib.request.urlopen(self.base + "/").read().decode()
        return json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]

    def post(self, path, body, stream=False):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token()})
        try:
            r = urllib.request.urlopen(req, timeout=90)
        except urllib.error.HTTPError as e:
            return json.loads(e.read() or b"{}")
        if stream:
            return [json.loads(x.decode()[6:]) for x in r if x.decode().startswith("data: ")]
        return json.loads(r.read())

    def action(self, aid):
        r = subprocess.run([sys.executable, str(self.v.root / "system/scripts/tracker.py"), "read", "actions", "--id", aid],
                           capture_output=True, text=True, cwd=self.v.root)
        return json.loads(r.stdout)[0]

    def staged(self):
        return sorted(p.name for p in (self.v.root / "system/staging").glob("proposed-*.json"))

    def go_ahead(self, change):
        """Ask for the change (a CONFIRM card), then Go ahead as the page does; the confirmed run's events."""
        evs = self.post("/api/ask", {"message": change}, stream=True)
        conf = [e for e in evs if e["type"] == "confirm"]
        self.assertEqual(len(conf), 1, evs)
        return self.post("/api/ask", {"message": f"Go ahead: {conf[0]['title']}", "confirmed": conf[0]["title"]}, stream=True)

    def set_auto_apply(self, on):
        f = self.v.root / "system/config/settings.json"
        s = json.loads(f.read_text())
        s.setdefault("dashboard", {})["auto_apply"] = on
        f.write_text(json.dumps(s, indent=2))

    def test_go_ahead_applies_the_change_once_and_undo_leaves_nothing_in_review(self):
        before, was = self.staged(), self.action("ABC-A-001")["priority"]
        evs = self.go_ahead("change ABC-A-001 priority High")
        applied = [e for e in evs if e["type"] == "applied"]
        self.assertEqual(len(applied), 1, evs)
        a = applied[0]
        self.assertTrue(a["ok"], a)
        self.assertEqual(a["ids"], ["ABC-A-001"])
        self.assertIn(f"ABC-A-001 · Priority: {was} → High", a["message"])
        self.assertNotIn("meanwhile", a["message"])
        self.assertIn(f"(apply {a['apply_id']})", a["message"])
        self.assertTrue(a["message"].startswith("Applied: "))
        self.assertEqual(self.action("ABC-A-001")["priority"], "High")
        self.assertEqual(self.staged(), before)                                   # nothing waits for an apply
        u = self.post("/api/undo", {"apply_id": a["apply_id"]})
        self.assertTrue(u["ok"], u)
        self.assertEqual(self.action("ABC-A-001")["priority"], was)
        self.assertEqual(self.staged(), before)                                   # BL-289: nothing back in Review

    def test_another_approved_proposal_waiting_is_not_applied_with_it(self):
        other = self.v.root / "system/staging/proposed-2026-10-12-090000-edit.json"
        other.write_text(json.dumps({"source_run": "cx-edit", "files": [], "items": [
            {"n": 1, "op": "update", "table": "actions", "id": "ABC-A-002", "changes": {"owner": "Alan Carter"},
             "match": "strong", "flags": [], "decision": "approved"}]}))
        try:
            evs = self.go_ahead("change ABC-A-001 priority Low")
            a = [e for e in evs if e["type"] == "applied"][0]
            self.assertTrue(a["ok"], a)
            self.assertEqual(self.action("ABC-A-001")["priority"], "Low")
            self.assertEqual(self.action("ABC-A-002")["owner"], "Sara Example")   # it waits for its own apply
            self.assertTrue(other.exists())
            self.post("/api/undo", {"apply_id": a["apply_id"]})
        finally:
            other.unlink(missing_ok=True)

    def test_with_auto_apply_off_it_stays_staged_and_says_so(self):
        before, was = set(self.staged()), self.action("ABC-A-001")["priority"]
        self.set_auto_apply(False)
        try:
            evs = self.go_ahead("change ABC-A-001 priority High")
        finally:
            self.set_auto_apply(True)
        applied = [e for e in evs if e["type"] == "applied"]
        self.assertEqual(len(applied), 1, evs)
        self.assertFalse(applied[0]["ok"])
        self.assertIn("auto-apply is off", applied[0]["message"])
        self.assertEqual(self.action("ABC-A-001")["priority"], was)
        new = set(self.staged()) - before
        self.assertEqual(len(new), 1)
        (self.v.root / "system/staging" / new.pop()).unlink()

    def test_a_run_alan_has_not_confirmed_gets_nothing_applied(self):
        """BL-267 holds: only a confirmed run's staging is applied (here a stand-in that stages without the guard)."""
        before, was = set(self.staged()), self.action("ABC-A-001")["priority"]
        evs = self.post("/api/ask", {"message": "sneak ABC-A-001 priority Low"}, stream=True)
        self.assertEqual([e for e in evs if e["type"] == "applied"], [])
        self.assertEqual(self.action("ABC-A-001")["priority"], was)
        new = set(self.staged()) - before
        self.assertEqual(len(new), 1)                                             # left for Alan in Review
        (self.v.root / "system/staging" / new.pop()).unlink()

    def test_the_prompts_and_cx_edit_say_the_server_applies_it(self):
        src = (self.v.root / "system/scripts/live_server.py").read_text()
        self.assertIn("never ask for it with CONFIRM: (BL-306)", src)
        self.assertIn("the server applies it once when you finish", src)
        skill = (Path(__file__).resolve().parents[2] / ".claude/skills/cx-edit/SKILL.md").read_text()
        self.assertIn("In a confirmed ask creaite run", skill)


class ConfirmedApplyBrowser(LiveBrowserCase):
    width, height = 1400, 900

    @classmethod
    def load(cls, v):
        load_fake(v)

    @classmethod
    def server_env(cls):
        return {"CREAITE_CLAUDE": str(cls.v.root / "fake_claude.py")}

    def test_go_ahead_shows_applied_with_undo_and_the_dashboard_updates(self):
        b = self.b
        b.eval("openChat(); $('#chIn').value='change ABC-A-001 status Closed'; send()", wait=False)
        b.wait("[...document.querySelectorAll('#chLog .confirm button.primary')].some(x=>x.textContent==='Go ahead')", 20)
        b.eval("[...document.querySelectorAll('#chLog .confirm button.primary')].find(x=>x.textContent==='Go ahead').click(); 1")
        b.wait("[...document.querySelectorAll('#chLog .msg.a')].some(m=>m.textContent.includes('Applied: ABC-A-001 · Status: Open → Closed'))", 30)
        b.wait("A.find(x=>x.id==='ABC-A-001').st==='Closed'", 20)
        b.click("#chLog [data-edundo]")
        b.wait("A.find(x=>x.id==='ABC-A-001').st==='Open'", 20)


if __name__ == "__main__":
    unittest.main()
