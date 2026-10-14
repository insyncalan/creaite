"""Sprint 4b item 1b: ask creaite is the "big boss" for reading: every Microsoft 365 reading tool, every vault file and every
creaite script's read commands, with no prompt. Writing stays confirmed in the panel, and Microsoft 365 actions (send, delete,
change) stay off. Checked through the flags the live server gives the headless run (a stand-in `claude` records them).

Run: python3 dev/tests/test_ask_access.py
"""
import json
import os
import re
import subprocess
import sys
import time
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_dashboard import populate  # noqa: E402
from test_live_server import free_port  # noqa: E402
from test_tracker import REPO, Vault  # noqa: E402

sys.path.insert(0, str(REPO / "system" / "scripts"))
import permissions as P  # noqa: E402

M365 = "mcp__claude_ai_Microsoft_365__"
FAKE = r'''#!/usr/bin/env python3
import json, sys
from pathlib import Path
args = sys.argv[1:]
here = Path(__file__).resolve().parent
(here / "fake_seen.json").write_text(json.dumps({"allowed": args[args.index("--allowedTools") + 1].split(","),
    "disallowed": args[args.index("--disallowedTools") + 1].split(","), "prompt": args[args.index("--append-system-prompt") + 1]}))
print(json.dumps({"type": "system", "subtype": "init", "session_id": "s-1"}), flush=True)
print(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "Done."}]}}), flush=True)
print(json.dumps({"type": "result", "session_id": "s-1", "result": "Done."}), flush=True)
'''


class AskAccess(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = v = Vault()
        populate(v)
        fake = v.root / "fake_claude.py"
        fake.write_text(FAKE)
        fake.chmod(0o755)
        port = free_port()
        cls.base = f"http://127.0.0.1:{port}"
        cls.proc = subprocess.Popen([sys.executable, str(v.root / "system/scripts/live_server.py")],
                                    env={**os.environ, "CREAITE_PORT": str(port), "CREAITE_CLAUDE": str(fake)},
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
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

    def ask(self, message, **extra):
        (self.v.root / "fake_seen.json").unlink(missing_ok=True)
        req = urllib.request.Request(self.base + "/api/ask", data=json.dumps({"message": message, **extra}).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        with urllib.request.urlopen(req, timeout=60) as r:
            r.read()
        return json.loads((self.v.root / "fake_seen.json").read_text())

    def test_every_microsoft_365_reading_tool_is_allowed_for_a_plain_question(self):
        seen = self.ask("what is on my calendar tomorrow?")
        for tool in P.M365_READ:
            self.assertIn(M365 + tool, seen["allowed"], tool)
        for tool in ("read_resource", "teams_list_chats", "sharepoint_search", "search_people", "outlook_calendar_search", "outlook_email_search"):
            self.assertIn(M365 + tool, seen["allowed"])
        self.assertEqual([t for t in seen["allowed"] if t.startswith(M365) and t[len(M365):] not in P.M365_READ], [])    # nothing but readers

    def test_vault_files_and_every_scripts_read_commands_are_allowed(self):
        seen = self.ask("what is in the minutes folder?")
        for rule in ("Read", "Grep", "Glob", "Bash(python3 system/scripts/minutes.py expected *)", "Bash(python3 system/scripts/minutes.py filedate *)",
                     "Bash(python3 system/scripts/report.py current-context *)", "Bash(python3 system/scripts/sweep.py calendar-window*)",
                     "Bash(python3 system/scripts/search.py context *)", "Bash(python3 system/scripts/propose.py people list*)",
                     "Bash(python3 system/scripts/locations.py check *)", "Bash(python3 system/scripts/prep_page.py context *)",
                     "Bash(python3 system/scripts/tracker.py read *)", "Bash(python3 system/scripts/doctor.py*)"):
            self.assertIn(rule, seen["allowed"], rule)

    def test_writing_is_not_allowed_until_alan_confirms_it(self):
        plain = self.ask("tidy the actions")
        for rule in ("Bash(python3 system/scripts/tracker.py apply*)", "Bash(python3 system/scripts/tracker.py undo*)", "Write(system/staging/**)"):
            self.assertNotIn(rule, plain["allowed"], rule)
        confirmed = self.ask("Go ahead: apply", confirmed="Apply the approved items")
        for rule in ("Bash(python3 system/scripts/tracker.py apply*)", "Write(system/staging/**)"):
            self.assertIn(rule, confirmed["allowed"], rule)
        for tool in P.M365_READ:                                                  # the confirmed run reads everything too
            self.assertIn(M365 + tool, confirmed["allowed"])
        self.assertIn("one line: CONFIRM", plain["prompt"].replace("exactly one line: ", "one line: "))

    def test_microsoft_365_actions_are_refused_for_every_kind_of_run(self):
        for seen in (self.ask("send Sara an email"), self.ask("Go ahead: send it", confirmed="Send the email")):
            for tool in P.M365_ACTIONS:
                self.assertIn(M365 + tool, seen["disallowed"], tool)
                self.assertNotIn(M365 + tool, seen["allowed"], tool)
            for tool in P.M365_READ:
                self.assertNotIn(M365 + tool, seen["disallowed"], tool)
        for name in ("outlook_send_mail", "outlook_delete_event", "teams_send_chat_message", "sharepoint_delete_item", "outlook_update_event"):
            self.assertIn(name, P.M365_ACTIONS)

    def test_the_prompt_says_what_may_be_read_and_what_may_not_be_changed(self):
        prompt = self.ask("hello")["prompt"]
        self.assertIn("You may read all of Microsoft 365", prompt)
        self.assertIn("Never send, delete or change anything in Microsoft 365", prompt)

    def test_tool_lists_do_not_overlap_and_cover_the_connector(self):
        self.assertEqual(set(P.M365_READ) & set(P.M365_ACTIONS), set())
        self.assertTrue(all(t.islower() for t in P.M365_READ + P.M365_ACTIONS))


class VaultRulesAndDoctor(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        self.addCleanup(self.v.cleanup)

    def settings(self):
        return json.loads((self.v.root / ".claude" / "settings.json").read_text())

    def doctor_line(self):
        out = subprocess.run([sys.executable, str(self.v.root / "system/scripts/doctor.py")], cwd=self.v.root, capture_output=True, text=True).stdout
        return next(line for line in out.splitlines() if "Assistant permissions" in line)

    def test_the_vaults_allow_list_has_the_readers_and_never_an_action(self):
        allow = self.settings()["permissions"]["allow"]
        for tool in P.M365_READ:
            self.assertIn(M365 + tool, allow)
        self.assertEqual([r for r in allow if r.startswith(M365) and r[len(M365):] in P.M365_ACTIONS], [])

    def test_doctor_does_not_call_the_readers_too_broad(self):
        self.assertNotIn("broader than creaite asks for", self.doctor_line())

    def test_doctor_flags_an_action_or_the_whole_connector(self):
        for rule, why in ((M365 + "outlook_send_mail", "sends, deletes or changes"), ("mcp__claude_ai_Microsoft_365", "every Microsoft 365 tool")):
            data = self.settings()
            data["permissions"]["allow"].append(rule)
            (self.v.root / ".claude" / "settings.json").write_text(json.dumps(data))
            line = self.doctor_line()
            self.assertIn("broader than creaite asks for", line)
            self.assertIn(why, line)
            data["permissions"]["allow"].remove(rule)
            (self.v.root / ".claude" / "settings.json").write_text(json.dumps(data))

    def test_the_rule_checker_accepts_readers_and_refuses_the_rest(self):
        self.assertIsNone(P.broad_rule(M365 + "read_resource"))
        self.assertIn("sends, deletes or changes", P.broad_rule(M365 + "teams_send_chat_message"))
        self.assertIn("every Microsoft 365 tool", P.broad_rule("mcp__claude_ai_Microsoft_365"))
        self.assertIn("hasn't checked", P.broad_rule(M365 + "a_new_tool"))


if __name__ == "__main__":
    unittest.main()
