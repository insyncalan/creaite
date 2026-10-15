"""ask creaite's permission requests (BL-75): the live server's side and the panel's card in headless Chrome.

Run: python3 dev/tests/test_permission_panel.py   (the Chrome part needs Google Chrome; skipped otherwise)
The server runs in a throwaway vault with a stand-in `claude` (CREAITE_CLAUDE) that prints Claude Code's stream-json
format, so no real Claude call is made.
"""
import json
import os
import re
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_dashboard import CHROME, populate  # noqa: E402
from test_live_server import free_port  # noqa: E402
from test_tracker import Vault  # noqa: E402

FAKE_CLAUDE = r'''#!/usr/bin/env python3
import json, sys
args = sys.argv[1:]
message = args[args.index("--") + 1]
allowed = args[args.index("--allowedTools") + 1].split(",")
disallowed = args[args.index("--disallowedTools") + 1].split(",")
system = args[args.index("--append-system-prompt") + 1]
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init", "session_id": "sess-perm-1"})
result = {"type": "result", "session_id": "sess-perm-1"}
if "echo flags" in message:
    text = "FLAGS " + json.dumps({"allowed": allowed, "disallowed": disallowed,
                                  "prompt": [w for w in ("PERMISSION:", "cx-document", "CONFIRM:", "/tmp") if w in system]})
elif "need permission" in message:
    text = "I can't save the summaries yet.\nPERMISSION: Write(system/search/**) | to save search summaries"
elif "need edit" in message:
    text = ("I'll add the rule.\nPERMISSION-EDIT: settings add allow Write(inbox/notes/**) | to keep notes in the inbox")
elif "two edits" in message:
    text = ("Two changes.\nPERMISSION-EDIT: settings add allow Write(inbox/notes/**) | to keep notes in the inbox\n"
            "PERMISSION-EDIT: config set sweep.due_from \"06:30\" | Alan wants the sweep earlier")
elif "bad edit" in message:
    text = "PERMISSION-EDIT: settings add allow Write(*) | everything"
elif "bad permission" in message:
    text = "PERMISSION: Bash(node build.js) | to build the document"
elif "colon allowed" in message:                                           # BL-140: the old prefix form of an allowed script
    text = "PERMISSION: Bash(python3 system/scripts/propose.py:*) | to stage the edit"
    result["permission_denials"] = [{"tool_name": "Bash", "tool_input": {"command": "cd /v && python3 system/scripts/propose.py stage - <<'EOF'"}}]
elif "colon new" in message:
    text = "PERMISSION: Bash(python3 system/scripts/locations.py:*) | to check the folders"
elif "colon perms" in message:
    text = "PERMISSION: Bash(python3 system/scripts/permissions.py:*) | to add a rule"
elif "colon interp" in message:
    text = "PERMISSION: Bash(python3:*) | to run a script"
elif "bare bash" in message:
    text = "PERMISSION: Bash | to run things"
elif "already allowed" in message:
    text = "PERMISSION: Bash(python3 system/scripts/report.py adhoc *) | to build"
elif "was refused" in message:
    text = "That failed."
    result["permission_denials"] = [{"tool_name": "Write", "tool_input": {"file_path": "/tmp/build.js"}}]
elif "make a document" in message:
    text = "I'd build the register.\nCONFIRM: Build the actions register | Writes a Word draft in system/staging/drafts/"
else:
    text = "Done."
out({"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}})
out({**result, "result": text})
'''


def events(resp):
    out = []
    for raw in resp:
        line = raw.decode().strip()
        if line.startswith("data: "):
            out.append(json.loads(line[6:]))
    return out


class PermissionPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = v = Vault()
        populate(v)
        fake = v.root / "fake_claude.py"
        fake.write_text(FAKE_CLAUDE)
        fake.chmod(0o755)
        cls.port = free_port()
        cls.base = f"http://127.0.0.1:{cls.port}"
        cls.env = {**os.environ, "CREAITE_PORT": str(cls.port), "CREAITE_CLAUDE": str(fake)}
        cls.proc = subprocess.Popen([sys.executable, str(v.root / "system/scripts/live_server.py")], env=cls.env,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            try:
                urllib.request.urlopen(cls.base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        html = urllib.request.urlopen(cls.base + "/").read().decode()
        cls.token = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]
        cls.settings = v.root / ".claude/settings.json"
        cls.original = cls.settings.read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)
        cls.v.cleanup()

    def setUp(self):
        self.settings.write_text(self.original, encoding="utf-8")
        for f in ("system/config/permissions-log.jsonl", "system/config/settings-log.jsonl"):
            (self.v.root / f).unlink(missing_ok=True)
        for f in (self.v.root / "system/backups").glob("*settings-*.json"):
            f.unlink()

    def post(self, path, body):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def ask(self, message, **extra):
        req = urllib.request.Request(self.base + "/api/ask", data=json.dumps({"message": message, **extra}).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        with urllib.request.urlopen(req, timeout=60) as r:
            return events(r)

    def allow(self):
        return json.loads(self.settings.read_text(encoding="utf-8"))["permissions"]["allow"]

    def test_a_run_asks_for_a_rule_and_the_panel_is_told_exactly_which(self):
        # BL-141: a Write rule can't help ask creaite (it changes files through filechange.py), so it is explained, not offered
        ev = self.ask("need permission")
        perm = next(e for e in ev if e["type"] == "permission")
        self.assertEqual((perm["rule"], perm["why"], perm["ok"], perm["state"]), ("Write(system/search/**)", "to save search summaries", False, "refused"))
        self.assertIn("doesn't need it: it changes files through filechange.py", perm["reason"])
        shown = " ".join(e["text"] for e in ev if e["type"] == "text")
        self.assertIn("I can't save the summaries yet.", shown)
        self.assertNotIn("PERMISSION", shown)                                                  # the protocol line isn't chat text
        self.assertFalse([e for e in ev if e["type"] == "changes"])
        self.assertEqual(self.allow(), json.loads(self.original)["permissions"]["allow"])      # asking changes nothing

    def test_a_rule_creaite_wont_add_is_explained_and_cant_be_applied(self):
        perm = next(e for e in self.ask("bad permission") if e["type"] == "permission")
        self.assertEqual((perm["ok"], perm["rule"], perm["state"]), (False, "Bash(node build.js)", "refused"))
        self.assertIn("must run one creaite script", perm["reason"])
        self.assertEqual(self.post("/api/permissions/apply", {"rule": "Bash(node build.js)"})[0], 404)   # BL-141: no route round the card
        perm = next(e for e in self.ask("already allowed") if e["type"] == "permission")
        self.assertEqual((perm["ok"], perm["covered"], perm["state"]), (False, "Bash(python3 system/scripts/report.py *)", "allowed"))
        self.assertNotIn("Bash(node build.js)", self.allow())

    # ===== BL-140 (sprint-admin) =====
    def test_the_colon_form_of_an_allowed_script_is_already_allowed_not_refused(self):
        ev = self.ask("colon allowed")
        perm = next(e for e in ev if e["type"] == "permission")
        self.assertEqual((perm["ok"], perm["state"], perm["rule"], perm["covered"]),
                         (False, "allowed", "Bash(python3 system/scripts/propose.py *)", "Bash(python3 system/scripts/propose.py *)"))
        self.assertEqual(perm["asked"], "Bash(python3 system/scripts/propose.py:*)")
        self.assertNotIn("must run one creaite script", perm["reason"])
        self.assertEqual(perm["refused"], ["propose.py with a cd … && prefix, a heredoc"])          # what was refused, by its shape
        self.assertFalse([e for e in ev if e["type"] == "changes"])

    def test_the_colon_form_of_a_new_creaite_script_is_added_in_the_proper_form(self):
        card = next(e for e in self.ask("colon new") if e["type"] == "changes")                 # BL-141: an item on the one card
        self.assertEqual(card["items"][0]["title"], "Allow Bash(python3 system/scripts/locations.py *)")
        r = self.post("/api/changes/approve", {"card": card["card"]})[1]
        self.assertTrue(r["ok"], r)
        self.assertEqual(self.allow()[-1], "Bash(python3 system/scripts/locations.py *)")
        self.assertFalse([a for a in self.allow() if a.endswith(":*)")])

    def test_permissions_py_an_interpreter_and_a_bare_bash_are_refused_with_the_right_reason(self):
        cases = {"colon perms": "permissions.py is never allowed to the panel",
                 "colon interp": "python3 with a wildcard is an interpreter or shell, which runs anything",
                 "bare bash": "Bash on its own runs any command"}
        for message, reason in cases.items():
            ev = self.ask(message)
            perm = next(e for e in ev if e["type"] == "permission")
            self.assertEqual((perm["ok"], perm["state"]), (False, "out_of_bounds"), message)
            self.assertIn(reason, perm["reason"], message)
            self.assertFalse([e for e in ev if e["type"] == "changes"], message)
        self.assertEqual(self.allow(), json.loads(self.original)["permissions"]["allow"])

    def test_approving_applies_it_once_with_a_backup_and_a_log(self):
        card = next(e for e in self.ask("colon new") if e["type"] == "changes")
        r = self.post("/api/changes/approve", {"card": card["card"]})[1]
        self.assertTrue(r["ok"], r)
        entry = json.loads((self.v.root / "system/config/files-log.jsonl").read_text().splitlines()[-1])
        self.assertEqual((entry["path"], entry["why"], entry["approved"]), (".claude/settings.json", "to check the folders", True))
        self.assertTrue((self.v.root / entry["backup"]).exists())                                    # backed up first
        again = self.post("/api/changes/approve", {"card": card["card"]})[1]
        self.assertFalse(again["ok"])                                                           # one approval, one change
        self.assertEqual(self.allow().count("Bash(python3 system/scripts/locations.py *)"), 1)

    def test_the_page_cannot_apply_a_rule_no_run_asked_for(self):
        self.assertEqual(self.post("/api/permissions/apply", {"rule": "Write(inbox/notes/**)"})[0], 404)
        self.assertEqual(self.post("/api/permissions/edit", {"edit": "settings add allow Write(inbox/notes/**)"})[0], 404)
        self.assertFalse(self.post("/api/changes/approve", {"card": "c-nobodymadethis1"})[1]["ok"])
        self.assertEqual(self.allow(), json.loads(self.original)["permissions"]["allow"])

    def test_undo_takes_it_out(self):
        card = next(e for e in self.ask("colon new") if e["type"] == "changes")
        self.post("/api/changes/approve", {"card": card["card"]})
        entry = json.loads((self.v.root / "system/config/files-log.jsonl").read_text().splitlines()[-1])
        r = self.post("/api/changes/undo", {"id": entry["id"]})[1]
        self.assertTrue(r["ok"], r)
        self.assertNotIn("Bash(python3 system/scripts/locations.py *)", self.allow())
        self.assertIn("Nothing to undo", self.post("/api/permissions/undo", {})[1]["message"])     # the old route still answers

    def test_the_old_permission_file_lines_no_longer_make_cards(self):
        for message in ("need edit", "two edits", "bad edit"):
            ev = self.ask(message)
            self.assertFalse([e for e in ev if e["type"] in ("permission_edit", "permission_file")], message)
            self.assertNotIn("PERMISSION", " ".join(e["text"] for e in ev if e["type"] == "text"))
        self.assertEqual(self.allow(), json.loads(self.original)["permissions"]["allow"])
        self.assertEqual(self.post("/api/ask", {"message": "Go ahead", "confirmed": "x", "permfile": ".claude/settings.json"})[0], 400)

    def test_a_refused_tool_is_shown(self):
        ev = self.ask("it was refused")
        denied = next(e for e in ev if e["type"] == "denied")
        self.assertIn("/tmp/build.js", denied["tools"][0])

    def test_the_panel_cannot_reach_its_own_settings_and_knows_the_protocol(self):
        flags = json.loads(next(e["text"] for e in self.ask("echo flags") if e["type"] == "text").replace("FLAGS ", ""))
        for rule in ("Edit(.claude/settings.json)", "Write(.claude/settings.json)", "Bash(python3 system/scripts/permissions.py*)"):
            self.assertIn(rule, flags["disallowed"])
        self.assertFalse([a for a in flags["allowed"] if "permissions.py" in a or ".claude" in a])
        self.assertIn("Bash(python3 system/scripts/report.py adhoc-data*)", flags["allowed"])    # it may look before it builds
        self.assertEqual(flags["prompt"], ["PERMISSION:", "cx-document", "CONFIRM:", "/tmp"])
        conf = self.ask("make a document of open actions")                                       # building a document is confirmed
        self.assertEqual(next(e for e in conf if e["type"] == "confirm")["title"], "Build the actions register")
        confirmed = json.loads(next(e["text"] for e in self.ask("echo flags", confirmed="Build the actions register") if e["type"] == "text").replace("FLAGS ", ""))
        self.assertIn("Bash(python3 system/scripts/report.py *)", confirmed["allowed"])
        self.assertFalse([a for a in confirmed["allowed"] if "permissions.py" in a])             # not even when confirmed


SCRIPT = r"""
<script>
(async()=>{ const out={errors:[]}, wait=ms=>new Promise(r=>setTimeout(r,ms)), sent=[];
  const real=window.fetch; window.fetch=async(u,o)=>{ if(u!=="/api/ask") return real(u,o); const body=JSON.parse(o.body); sent.push(body.message);
    const stream=new ReadableStream({start(c){ const enc=new TextEncoder(), send=e=>c.enqueue(enc.encode("data: "+JSON.stringify(e)+"\n\n"));
      send({type:"text",text:"I can't do that yet."}); if(window.__perm&&!/already allowed, so no rule/.test(body.message)) send(window.__perm);
      send({type:"done",session:"sess-perm-1",chat:"sess-perm-1",run:body.run}); c.close(); }});
    return new Response(stream,{status:200,headers:{"Content-Type":"text/event-stream"}}); };
  const until=async(f,n=60)=>{ for(let i=0;i<n&&!f();i++) await wait(100); };
  try{
    await checkLive(); out.live=LIVE&&viaServer(); openChat();
    // a rule creaite won't add is explained and not offered
    window.__perm=window.__permBad; await send("build it with node");
    await wait(300); out.refusedCard=!document.querySelector("#chLog .confirm"); out.refusedText=[...document.querySelectorAll("#chLog .msg.a")].pop().textContent;
    // BL-140: the true reason for each state; Terminal only when out of bounds; Try again only when already allowed
    out.info={allowed:permissionInfoText({rule:"Bash(python3 system/scripts/propose.py *)",asked:"Bash(python3 system/scripts/propose.py:*)",covered:"Bash(python3 system/scripts/propose.py *)",state:"allowed",refused:["propose.py with a pipe"]}),
      refused:permissionInfoText({rule:"Bash(node build.js)",reason:"node build.js is not a creaite script",state:"refused"}),
      oob:permissionInfoText({rule:"Bash",reason:"Bash on its own runs any command: creaite never adds it",state:"out_of_bounds"})};
    window.__perm=window.__permAllowed; await until(()=>!BUSY); sent.length=0; await send("stage the edit");
    await wait(300); const lastA=[...document.querySelectorAll("#chLog .msg.a")].pop();
    out.allowedCard=[!document.querySelector("#chLog .confirm"), lastA.textContent, [...lastA.querySelectorAll("button:not(.msgcopy)")].map(b=>b.textContent)];   // BL-148: every reply also has Copy
    lastA.querySelector("button").click(); await until(()=>sent.length>1&&!BUSY); out.retry=sent.slice();
  }catch(e){ out.errors.push(String(e&&e.stack||e)); }
  const pre=document.createElement("pre"); pre.id="result"; pre.textContent=JSON.stringify(out); document.body.appendChild(pre); })();
</script>
"""


@unittest.skipUnless(CHROME.exists(), "Google Chrome not installed")
class PermissionCardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = v = Vault()
        populate(v)
        fake = v.root / "fake_claude.py"
        fake.write_text(FAKE_CLAUDE)
        fake.chmod(0o755)
        bad = {"type": "permission", "rule": "Bash(node build.js)", "why": "to build", "ok": False, "covered": None, "state": "refused",
               "reason": "node build.js is not a creaite script: a Bash rule must run one creaite script"}
        allowed = {"type": "permission", "rule": "Bash(python3 system/scripts/propose.py *)", "asked": "Bash(python3 system/scripts/propose.py:*)",
                   "why": "to stage", "ok": False, "covered": "Bash(python3 system/scripts/propose.py *)", "state": "allowed", "reason": "already allowed",
                   "refused": ["propose.py with a pipe"]}
        inject = v.root / "inject.html"
        inject.write_text(f"<script>window.__permBad={json.dumps(bad)};window.__permAllowed={json.dumps(allowed)};</script>" + SCRIPT)
        port = free_port()
        env = {**os.environ, "CREAITE_PORT": str(port), "CREAITE_CLAUDE": str(fake), "CREAITE_TEST_INJECT": str(inject)}
        server = subprocess.Popen([sys.executable, str(v.root / "system/scripts/live_server.py")], env=env,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            base = f"http://127.0.0.1:{port}"
            for _ in range(50):
                try:
                    urllib.request.urlopen(base + "/health", timeout=1)
                    break
                except OSError:
                    time.sleep(0.1)
            html = urllib.request.urlopen(base + "/").read().decode()
            token = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]
            sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
            from cdp import Browser
            try:                                         # a real browser that waits for the result, not a fixed virtual-time budget (steady under load)
                with Browser() as b:
                    b.goto(base + "/", wait_for="!!document.getElementById('result')", timeout=240)
                    out = b.eval("document.getElementById('result').outerHTML").encode()
            except (TimeoutError, RuntimeError):
                out = b""
        finally:
            server.terminate()
            server.wait(timeout=10)
        m = re.search(r'<pre id="result">(.*?)</pre>', out.decode("utf-8", "ignore"), re.S)
        assert m, "the page didn't finish the scripted steps"
        cls.r = json.loads(m.group(1).replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&amp;", "&"))

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def test_no_script_errors(self):
        self.assertEqual(self.r["errors"], [])
        self.assertTrue(self.r["live"])

    def test_a_refused_rule_is_only_explained(self):
        r = self.r
        self.assertTrue(r["refusedCard"])                                                        # BL-141: no card for a rule never added
        self.assertIn("which creaite won't add: node build.js is not a creaite script", r["refusedText"])
        self.assertNotIn("Terminal", r["refusedText"])                                          # BL-140: not out of bounds, so no Terminal line

    def test_bl140_each_state_says_what_is_true(self):
        info = self.r["info"]
        self.assertIn("is already allowed by Bash(python3 system/scripts/propose.py *)", info["allowed"])
        self.assertIn("propose.py with a pipe", info["allowed"])
        self.assertNotIn("Terminal", info["allowed"])
        self.assertNotIn("Terminal", info["refused"])
        self.assertIn("edit .claude/settings.json yourself in Terminal", info["oob"])
        no_card, text, buttons = self.r["allowedCard"]
        self.assertTrue(no_card)                                                                 # information, not a card to approve
        self.assertIn("Nothing to add", text)
        self.assertNotIn("Terminal", text)
        self.assertEqual(buttons, ["Try again"])
        self.assertEqual(len(self.r["retry"]), 2)
        self.assertIn("is already allowed, so no rule is needed. Run the script on its own", self.r["retry"][1])


if __name__ == "__main__":
    unittest.main()
