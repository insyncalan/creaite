"""A run in mode "held" has no file writers: Edit, Write, MultiEdit and NotebookEdit are denied by name.

The runs creaite starts itself that may read files (Prep page "prep", Current state's draft and rewrite, the AI drafts and Shape
the meeting "generate", a transcript's "check" and "load") read outside content and write nothing themselves (the server writes
from their reply or tool results), so the vault's .claude/settings.json allow rules (Edit projects/**, Edit
system/config/settings.json, Edit system/staging/**, Edit inbox/**) must never apply in them. Each kind is started through the
run engine with a stand-in `claude` (CREAITE_CLAUDE) that records its argv; nothing calls Claude. Unchanged, and checked: ask
creaite, a confirmed request, a typed sweep, Close the day's sweep (it writes its input files in system/staging/drafts/), the
narrowed draft-from-a-message run, Search's answer, and the confidential-note hook in mode "held".

Run: python3 dev/tests/test_held_edit_deny.py
"""
import fnmatch
import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import ABC, Vault  # noqa: E402

WRITERS = ["Edit", "Write", "MultiEdit", "NotebookEdit"]
CHAT_WRITERS = ["Edit", "Write", "MultiEdit"]     # F2: NotebookEdit is denied in every run (NEVER_BUILTINS); no kind uses it
HELD = ["prep", "generate", "check", "load"]
TARGETS = [f"{ABC}/notes.md", f"{ABC}/minutes/2026-10-01 Steering.docx", "system/config/settings.json",
           "system/staging/proposed-x.json", "system/staging/drafts/x.json", "inbox/forward.txt"]

FAKE = r'''#!/usr/bin/env python3
import json, sys
open(__file__ + ".calls", "a", encoding="utf-8").write(json.dumps(sys.argv[1:]) + "\n")
print(json.dumps({"type": "system", "subtype": "init", "session_id": "sess-h"}), flush=True)
print(json.dumps({"type": "result", "result": "{}", "session_id": "sess-h"}), flush=True)
'''

RUNS = r'''
import json, sys, time
sys.path.insert(0, "system/scripts")
import live_server as L
starts = [("prep", {"kind": "prep"}), ("generate", {"kind": "generate"}), ("check", {"kind": "check"}), ("load", {"kind": "load"}),
          ("ask", {}), ("confirmed", {"confirmed": "Close ABC-A-001"}), ("typed sweep", {"sweep": True}),
          ("sweep", {"kind": "sweep"}), ("narrow", {"kind": "generate", "only": L.ALERT_DRAFT_TOOLS}), ("search", {"kind": "search"})]
for name, kw in starts:
    confirmed = kw.pop("confirmed", None)
    r = L.Run("r-" + name.replace(" ", "-"), "sweep" if kw.get("sweep") else "Look.", None, None, confirmed, **kw)
    for _ in range(600):
        if r.done:
            break
        time.sleep(0.1)
print(json.dumps([n for n, _ in starts]))
'''


def flag(args, name):
    before = args[:args.index("--")]
    assert before.count(name) == 1, f"{name} appears {before.count(name)} times"
    return before[before.index(name) + 1]


def ruled(tool, path, rules):
    """True when a rule list names this tool on this path: the bare tool, or Tool(pattern) matching it (** spans folders)."""
    for r in rules:
        if r == tool:
            return True
        m = re.fullmatch(rf"{tool}\((.+)\)", r)
        if m and fnmatch.fnmatch(path, m.group(1).replace("**", "*")):
            return True
    return False


class HeldRuns(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = v = Vault()
        fake = v.root / "fake_claude.py"
        fake.write_text(FAKE)
        fake.chmod(0o755)
        env = {**{k: x for k, x in os.environ.items() if k != "CREAITE_RUN_KIND"}, "CREAITE_CLAUDE": str(fake)}
        r = subprocess.run([sys.executable, "-c", RUNS], cwd=v.root, env=env, capture_output=True, text=True, timeout=300)
        assert r.returncode == 0, r.stderr[-2000:]
        names = json.loads(r.stdout.strip().splitlines()[-1])
        cls.calls = dict(zip(names, [json.loads(x) for x in Path(str(fake) + ".calls").read_text().splitlines()]))

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def deny(self, name):
        return flag(self.calls[name], "--disallowedTools").split(",")

    def allow(self, name):
        return flag(self.calls[name], "--allowedTools").split(",")

    def mode(self, name):
        a = self.calls[name]
        if "--settings" not in a:
            return None
        cmd = json.loads(flag(a, "--settings"))["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        return re.search(r"--mode (\S+)", cmd).group(1)

    def test_held_kinds_deny_every_file_writer_everywhere(self):
        for kind in HELD:
            self.assertEqual(self.mode(kind), "held", kind)
            deny = self.deny(kind)
            for t in WRITERS:
                self.assertIn(t, deny, kind)
                for p in TARGETS:                                     # (a) projects, (b) settings.json, (c) staging, inbox
                    self.assertTrue(ruled(t, p, deny), f"{kind} {t} {p}")
                    self.assertFalse(ruled(t, p, self.allow(kind)), f"{kind} {t} {p} allowed")

    def test_held_kinds_still_read(self):
        for kind in HELD:
            allow, deny = self.allow(kind), self.deny(kind)
            for t in ("Read", "Grep", "Glob"):
                self.assertIn(t, allow, kind)
                self.assertNotIn(t, deny, kind)
            self.assertIn("Bash(system/scripts/run search.py query *)", allow, kind)
            self.assertIn("Bash(system/scripts/run docx_tools.py text *)", allow, kind)
            self.assertIn("mcp__claude_ai_Microsoft_365__read_resource", allow, kind)
            self.assertNotIn("Bash", deny, kind)

    def test_close_the_day_sweep_keeps_its_drafts_writes(self):
        self.assertEqual(self.mode("sweep"), "sweep")
        deny, allow = self.deny("sweep"), self.allow("sweep")
        for t in CHAT_WRITERS:
            self.assertNotIn(t, deny)
        self.assertIn("Write(system/staging/drafts/**)", allow)

    def test_ask_creaite_and_the_rest_unchanged(self):
        self.assertIn("Write(system/staging/drafts/**)", self.allow("ask"))
        self.assertIn("Write(system/staging/**)", self.allow("confirmed"))
        for name in ("ask", "confirmed", "typed sweep"):                # search denies its writers itself (run-search-tools-fix)
            self.assertFalse(set(CHAT_WRITERS) & set(self.deny(name)), name)
        self.assertNotIn("MultiEdit", self.deny("narrow"))           # its own ONLY_DENIES, as before
        self.assertIsNone(self.mode("narrow"))

    def test_the_function(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system/scripts"))
        import live_server as L
        self.assertEqual(L.HELD_DENIES, WRITERS)
        self.assertEqual(L.held_deny(["x"], True, False), ["x"] + WRITERS)
        self.assertEqual(L.held_deny(["x"], True, True), ["x"])      # a guarded run with --held 1: its hook's mode decides
        self.assertEqual(L.held_deny(["x"], False, False), ["x"])
        self.assertEqual(L.held_deny(["Edit", "x"], True, False), ["Edit", "x", "Write", "MultiEdit", "NotebookEdit"])


if __name__ == "__main__":
    unittest.main()
