"""BL-342 step 0: dev/tools/vip_probe.py, the read-only live probe.

Run: python3 dev/tests/test_vip_probe.py
A throwaway vault with fictional people and a stand-in `claude` (CREAITE_CLAUDE); never Microsoft 365. Covers: the command line
(--model, the read tools only, no write tool, `--` before the prompt), the output (ids, dates, counts and cost only; none of
the stand-in's message text, subjects, names or addresses), the verdict, the refusals, and that the script writes nothing
(a source check, and the vault is byte-for-byte the same afterwards).
"""
import ast
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PROBE = REPO / "dev" / "tools" / "vip_probe.py"
sys.path.insert(0, str(HERE))
from test_sweep_alerts import vip_vault  # noqa: E402

SECRET = "SECRET MESSAGE TEXT"
STAND_IN = r'''#!/usr/bin/env python3
import json, os, sys
argv = sys.argv[1:]
with open(os.environ["STANDIN_LOG"], "a") as f:
    f.write(json.dumps(argv) + "\n")
prompt = argv[-1]
model = argv[argv.index("--model") + 1] if "--model" in argv else ""
usage = {"input_tokens": 3000, "cache_creation_input_tokens": 20000, "cache_read_input_tokens": 40000, "output_tokens": 600}
if "probe, facts" in prompt:
    body = {"connected": True, "mail": [{"message_id": "AAMk-m1", "conversation_id": "AAQk-c1"}],
            "teams": [{"chat_id": "19:chat-falcon@thread.v2"}], "sent_items": {"searched": True, "results": 2},
            "subject": "Subject: SECRET MESSAGE TEXT", "note": "SECRET MESSAGE TEXT from Mia Hale <mia@client.example>"}
    text = "Here you go: " + json.dumps(body)
else:
    rows = [{"kind": "teams", "conversation": "19:chat-falcon@thread.v2", "msg": "1760000000001", "last": "2026-10-14 16:40",
             "subject": "SECRET MESSAGE TEXT", "people": ["Mia Hale <mia@client.example>"], "summary": "SECRET MESSAGE TEXT"},
            {"kind": "mail", "conversation": "AAQk-c1", "msg": "AAMk-m1", "last": "2026-10-14 09:05", "title": "SECRET MESSAGE TEXT"}]
    if model == "haiku" and os.environ.get("HAIKU_WRONG"):
        rows[1]["last"] = "2026-10-13 09:05"
    if os.environ.get("NONE_FOUND"):
        rows = []
    text = json.dumps(rows)
print(json.dumps({"result": text, "usage": usage, "total_cost_usd": 0.5}))
'''


def tree(root):
    """Every file under the vault with its hash, so any write at all shows."""
    return {f.relative_to(root).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest()
            for f in sorted(Path(root).rglob("*")) if f.is_file()}


class Probe(unittest.TestCase):
    def setUp(self):
        self.v = vip_vault()
        self.tmp = tempfile.mkdtemp()
        self.log = Path(self.tmp) / "calls.jsonl"
        self.claude = Path(self.tmp) / "claude"
        self.claude.write_text(STAND_IN)
        self.claude.chmod(self.claude.stat().st_mode | stat.S_IEXEC)

    def tearDown(self):
        self.v.cleanup()

    def probe(self, vault=None, **env):
        e = {**os.environ, "CREAITE_CLAUDE": str(self.claude), "STANDIN_LOG": str(self.log), **env}
        return subprocess.run([sys.executable, str(PROBE), "--vault", str(vault or self.v.root)], capture_output=True, text=True,
                              cwd=self.tmp, env=e)

    def calls(self):
        return [json.loads(x) for x in self.log.read_text().splitlines()]

    def test_the_command_line_is_read_only_with_a_model_and_the_prompt_after_dashes(self):
        r = self.probe()
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        calls = self.calls()
        self.assertEqual(len(calls), 3)                                      # facts, stage 1 on Haiku, stage 1 on Sonnet
        self.assertEqual([c[c.index("--model") + 1] for c in calls], ["sonnet", "haiku", "sonnet"])
        source = (REPO / "system/scripts/live_server.py").read_text()
        vip_tools = ast.literal_eval(re.search(r"^VIP_TOOLS = (\[.*?\])", source, re.S | re.M).group(1))
        for c in calls:
            self.assertEqual(c[0], "-p")
            self.assertEqual(c[-2], "--")                                    # nothing in the prompt is read as an option
            self.assertEqual(c[c.index("--allowedTools") + 1].split(","), vip_tools)   # the follow check's own read list
            self.assertEqual(sum(1 for x in c if x == "--allowedTools"), 1)
            deny = c[c.index("--disallowedTools") + 1].split(",")
            for w in ("Bash", "Write", "Edit", "WebFetch", M365 + "outlook_send_mail", M365 + "outlook_delete_event",
                      M365 + "teams_send_chat_message"):
                self.assertIn(w, deny)
            self.assertFalse(set(deny) & set(vip_tools))
            self.assertNotIn(c[-1], c[:-1])

    def test_the_deny_list_covers_every_action_tool_the_servers_own_list_denies(self):
        sys.path.insert(0, str(REPO / "system/scripts"))
        import permissions
        self.probe()
        deny = set(self.calls()[0][self.calls()[0].index("--disallowedTools") + 1].split(","))
        self.assertTrue(set(permissions.m365_action_tools()) <= deny)

    def test_output_is_ids_dates_counts_and_cost_only(self):
        r = self.probe()
        out = r.stdout
        for banned in (SECRET, "Mia", "client.example", "Subject", "Falcon go-live", "Here you go", "summary"):
            self.assertNotIn(banned, out)
        self.assertEqual(r.stderr, "")
        self.assertRegex(out, r"yes\s+\(i\) read_resource on a mail returns its conversation ID: messages 1 of 1; ids AAQk-c1")
        self.assertRegex(out, r"yes\s+\(ii\) Teams search results carry the chat ID: results 1 of 1")
        self.assertRegex(out, r"yes\s+\(iii\) Sent Items can be searched by subject: 2 results")
        self.assertIn("19:chat-falcon@thread.v2  last 2026-10-14 16:40", out)
        self.assertIn("AAQk-c1  last 2026-10-14 09:05", out)
        self.assertRegex(out, r"Stage 1 on haiku: 2 thread\(s\), cost \$0\.\d{4}")
        self.assertIn("Haiku matches Sonnet on 2 of 2 IDs and dates", out)
        self.assertIn("Haiku is fine for stage 1", out)

    def test_haiku_getting_a_date_wrong_recommends_sonnet(self):
        out = self.probe(HAIKU_WRONG="1").stdout
        self.assertIn("Haiku matches Sonnet on 1 of 3 IDs and dates", out)
        self.assertIn("use Sonnet for stage 1", out)

    def test_nothing_found_says_so_and_does_not_recommend(self):
        out = self.probe(NONE_FOUND="1").stdout
        self.assertIn("Haiku matches Sonnet on 0 of 0", out)
        self.assertNotIn("is fine for stage 1", out)

    def test_haiku_costs_a_twentieth_of_sonnet_on_the_same_usage(self):
        out = self.probe().stdout
        h, s = (float(x) for x in re.findall(r"Cost per check: Haiku \$([\d.]+), Sonnet \$([\d.]+)", out)[0])
        self.assertAlmostEqual(h, 0.0035 + 0.00, delta=0.0006)      # 3000 in, 20000 write, 40000 read, 600 out at Haiku prices
        self.assertGreater(s / h, 15)

    def test_the_vault_is_unchanged_afterwards(self):
        before = tree(self.v.root)
        self.probe()
        self.assertEqual(tree(self.v.root), before)                  # no file, no staging, no vip.json, no log, no __pycache__

    def test_refuses_in_the_development_repository(self):
        (self.v.root / ".creaite-dev").write_text("")
        r = self.probe()
        self.assertEqual(r.returncode, 2)
        self.assertIn("development repository", r.stdout)
        self.assertFalse(self.log.exists())                          # claude never started

    def test_refuses_when_nobody_is_followed(self):
        p = self.v.root / "projects/_portfolio/people-register.md"
        p.write_text(p.read_text().replace("| client |", "| |").replace("| management |", "| |"))
        r = self.probe()
        self.assertEqual(r.returncode, 2)
        self.assertIn("Nothing to probe", r.stdout)
        self.assertFalse(self.log.exists())

    def test_says_plainly_when_microsoft_365_is_not_connected(self):
        bad = Path(self.tmp) / "claude-off"
        bad.write_text("#!/bin/sh\necho '{\"result\": \"I have no Microsoft 365 tools.\", \"is_error\": false}'\n")
        bad.chmod(0o755)
        r = self.probe(CREAITE_CLAUDE=str(bad))
        self.assertIn("Microsoft 365 does not look connected", r.stdout)


M365 = "mcp__claude_ai_Microsoft_365__"


class Source(unittest.TestCase):
    """The script's code writes nothing: no open for writing, no writer, no tracker or sweep write function, no live_server edit."""

    def setUp(self):
        self.src = PROBE.read_text()
        self.tree = ast.parse(self.src)

    def test_no_file_is_opened_for_writing(self):
        for n in ast.walk(self.tree):
            if isinstance(n, ast.Call):
                name = ast.unparse(n.func)
                if name in ("open", "io.open", "os.open", "Path.open") or name.endswith(".open"):
                    modes = [a.value for a in n.args[1:2] if isinstance(a, ast.Constant)] + \
                            [k.value.value for k in n.keywords if k.arg == "mode" and isinstance(k.value, ast.Constant)]
                    self.assertFalse([m for m in modes if any(c in str(m) for c in "wax+")], ast.unparse(n))
                self.assertNotIn(name.rsplit(".", 1)[-1], {"write", "write_text", "write_bytes", "mkdir", "touch", "unlink", "rename",
                                                           "replace", "rmtree", "copy", "copy2", "copyfile", "move", "remove",
                                                           "dump", "writelines", "makedirs", "symlink_to"}, name)

    def test_no_tracker_sweep_or_other_writer_is_imported_or_called(self):
        imported = {a.name for n in ast.walk(self.tree) if isinstance(n, ast.Import) for a in n.names}
        imported |= {n.module for n in ast.walk(self.tree) if isinstance(n, ast.ImportFrom)}
        self.assertFalse(imported & {"tracker", "sweep", "filechange", "review", "excel_sync", "live_server", "report", "update",
                                     "sqlite3", "shutil_write"}, imported)
        for word in ("tracker.apply", "vip_record", "sweep.", "staging", "vip.json", "filechange", "sqlite3"):
            code = re.sub(r'"""[\s\S]*?"""|#.*', "", self.src)
            self.assertNotIn(word, code, word)

    def test_it_agrees_with_the_follow_checks_tool_list_and_live_server_is_untouched(self):
        server = (REPO / "system/scripts/live_server.py").read_text()
        vip_tools = ast.literal_eval(re.search(r"^VIP_TOOLS = (\[.*?\])", server, re.S | re.M).group(1))
        sys.path.insert(0, str(REPO / "dev/tools"))
        import vip_probe
        self.assertEqual(vip_probe.PROBE_TOOLS, vip_tools)
        out = subprocess.run(["git", "-C", str(REPO), "diff", "--name-only", "origin/main", "HEAD"], capture_output=True, text=True).stdout
        self.assertNotIn("live_server.py", out)

    def test_the_header_lists_what_it_reads_and_that_it_writes_nothing(self):
        head = self.src.split('"""')[1]
        self.assertIn("WHAT IT READS", head)
        self.assertIn("WHAT IT WRITES: nothing", head)

    def test_the_word_that_labels_a_followed_person_is_not_in_what_it_prints_or_sends(self):
        self.assertNotIn("VIP", re.sub(r'"""[\s\S]*?"""|#.*', "", self.src).replace("VIP_TOOLS", ""))


if __name__ == "__main__":
    unittest.main()
