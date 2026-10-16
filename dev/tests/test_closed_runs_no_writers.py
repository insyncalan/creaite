"""Shape the meeting for a confidential meeting ("shape-closed") and Find updates ("notes-find") have no file writers either.

Both runs only reply (BL-286, BL-301): an empty allow list and every reading tool denied, as before, and now Edit, Write,
MultiEdit and NotebookEdit denied by name too, so the vault's .claude/settings.json allow rules (Edit projects/**, Edit
system/config/settings.json, Edit system/staging/**, Edit inbox/**) can't apply. Started through the run engine with a stand-in
`claude` (CREAITE_CLAUDE) that records its argv; nothing calls Claude.

Run: python3 dev/tests/test_closed_runs_no_writers.py
"""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import Vault  # noqa: E402

WRITERS = ["Edit", "Write", "MultiEdit", "NotebookEdit"]
READERS = ["Read", "Grep", "Glob", "Bash", "WebFetch", "WebSearch", "mcp__claude_ai_Microsoft_365__read_resource"]
KINDS = ["shape-closed", "notes-find"]

FAKE = r'''#!/usr/bin/env python3
import json, sys
open(__file__ + ".calls", "a", encoding="utf-8").write(json.dumps(sys.argv[1:]) + "\n")
print(json.dumps({"type": "system", "subtype": "init", "session_id": "sess-c"}), flush=True)
print(json.dumps({"type": "result", "result": "{}", "session_id": "sess-c"}), flush=True)
'''

RUNS = r'''
import json, sys, time
sys.path.insert(0, "system/scripts")
import live_server as L
for kind in %r:
    r = L.Run("r-" + kind, "Look.", None, None, None, kind=kind)
    for _ in range(600):
        if r.done:
            break
        time.sleep(0.1)
''' % (KINDS,)


def flag(args, name):
    before = args[:args.index("--")]
    assert before.count(name) == 1, f"{name} appears {before.count(name)} times"
    return before[before.index(name) + 1]


class ClosedRuns(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = v = Vault()
        fake = v.root / "fake_claude.py"
        fake.write_text(FAKE)
        fake.chmod(0o755)
        env = {**os.environ, "CREAITE_CLAUDE": str(fake)}
        r = subprocess.run([sys.executable, "-c", RUNS], cwd=v.root, env=env, capture_output=True, text=True, timeout=300)
        assert r.returncode == 0, r.stderr[-2000:]
        cls.calls = dict(zip(KINDS, [json.loads(x) for x in Path(str(fake) + ".calls").read_text().splitlines()]))

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def test_no_writer_and_no_reader(self):
        for kind in KINDS:
            a = self.calls[kind]
            self.assertEqual(flag(a, "--allowedTools"), "", kind)
            deny = flag(a, "--disallowedTools").split(",")
            for t in WRITERS + READERS:
                self.assertIn(t, deny, f"{kind} {t}")

    def test_no_hook_and_no_skips(self):
        for kind in KINDS:
            a = self.calls[kind]
            self.assertNotIn("--settings", a, kind)               # no file tools: no hook, as before (#60)
            self.assertNotIn("--dangerously-skip-permissions", a)
            self.assertNotIn("--permission-mode", a)

    def test_the_lists(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system/scripts"))
        import live_server as L
        self.assertEqual(L.KIND_DENIES["notes-find"], L.KIND_DENIES["shape-closed"])
        self.assertEqual(L.KIND_TOOLS["shape-closed"], [])
        self.assertEqual(L.KIND_TOOLS["notes-find"], [])
        self.assertNotIn("Edit", L.KIND_DENIES.get("generate", []))   # other kinds unchanged here (F2 denies Edit in generate only
        self.assertIn("Edit", L.run_policy("generate", None)[1])       # because its --tools doesn't name it)
        self.assertNotIn("Edit", L.run_policy("ask", None)[1])


if __name__ == "__main__":
    unittest.main()
