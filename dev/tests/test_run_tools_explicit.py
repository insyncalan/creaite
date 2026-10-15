"""Every run kind names its built-in tools (F2, #116 review): `--tools` is an allow list per kind, never left out.

A run started with no `--tools` gets every built-in tool in the installed Claude Code, including ones that run headless with no
permission prompt and that neither the guard hook nor a deny list looks at (EnterWorktree, RemoteTrigger, CronCreate, Monitor,
SendMessage, Workflow…). So each kind's `--tools` is pinned here, a new kind without an entry fails the test, and the built-ins no
kind needs are denied by name in every run as well (EVERY_RUN_DENIES: F3's permissions.run_deny_extras() plus F2_ONLY_DENIES).
A kind that calls an MCP tool lists ToolSearch (`--tools ""` hides deferred MCP tools; #116, Alan's live check). F4: Search's
answer also has `--strict-mcp-config`. The VIP check keeps main's command line (its own branch changes it).

Each kind is started through the run engine with a stand-in `claude` (CREAITE_CLAUDE) that records its argv; nothing calls Claude.

Run: python3 dev/tests/test_run_tools_explicit.py
"""
import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system/scripts"))
from test_tracker import Vault  # noqa: E402

SERVER = Path(__file__).resolve().parents[2] / "system/scripts/live_server.py"
CHAT = "Read,Grep,Glob,Bash,Write,Edit,Skill,Task,ToolSearch"
SWEEP = "Read,Grep,Glob,Bash,Write,Edit,Skill,ToolSearch"
HELD = "Read,Grep,Glob,Bash,ToolSearch"
# kind (as started) | expected --tools | --strict-mcp-config | notes
TABLE = [
    ("ask", CHAT, False, "a chat: the guard hook checks every call; skills (cx-*, docx) need Skill; Task kept (a chat may delegate)"),
    ("confirmed", CHAT, False, "a confirmed request: a chat's tools, plus the write rules"),
    ("typed sweep", SWEEP, False, "BL-309: cx-sweep under the hook's sweep mode; writes its input files in drafts"),
    ("sweep", SWEEP, False, "BL-295: Close the day's catch-up sweep"),
    ("prep", HELD, False, "held: files and creaite's read scripts; the server writes the page"),
    ("generate", HELD, False, "held: Current state, AI drafts, Shape"),
    ("check", HELD, False, "held: a transcript check"),
    ("load", HELD, False, "held: a transcript load"),
    ("narrow", "ToolSearch", False, "the draft-from-a-message run (`only`): Microsoft 365 reading only; ToolSearch reaches them"),
    ("search", "Read,Grep,Glob", True, "F4: no MCP at all"),
    ("edit-ai", "", True, "BL-301 D: no tools, no MCP"),
    ("shape-closed", "", False, "BL-286: no tools (every reading MCP tool denied by name)"),
    ("notes-find", "", False, "BL-301 E: no tools (every reading MCP tool denied by name)"),
]
DANGEROUS = ["EnterWorktree", "ExitWorktree", "RemoteTrigger", "Workflow", "Monitor", "PushNotification", "SendMessage",
             "CronCreate", "CronDelete", "CronList", "ScheduleWakeup", "DesignSync", "Artifact", "ArtifactComments", "ArtifactData",
             "NotebookEdit"]

# F2's own list before it imported F3's (2cb7c795): the union must stay these plus F3's other-connector entries.
PREVIOUS_NEVER_BUILTINS = ["EnterWorktree", "ExitWorktree", "RemoteTrigger", "Workflow", "Monitor", "PushNotification",
                           "SendMessage", "CronCreate", "CronDelete", "CronList", "ScheduleWakeup", "DesignSync", "Artifact",
                           "ArtifactComments", "ArtifactData", "NotebookEdit", "TaskStop", "ListAgents", "ReportFindings",
                           "ListMcpResourcesTool", "ReadMcpResourceTool", "ReadMcpResourceDirTool"]

FAKE = r'''#!/usr/bin/env python3
import json, sys
open(__file__ + ".calls", "a", encoding="utf-8").write(json.dumps(sys.argv[1:]) + "\n")
print(json.dumps({"type": "system", "subtype": "init", "session_id": "sess-t"}), flush=True)
print(json.dumps({"type": "result", "result": "{}", "session_id": "sess-t"}), flush=True)
'''

RUNS = r'''
import json, sys, time
sys.path.insert(0, "system/scripts")
import live_server as L
starts = [("ask", {}), ("confirmed", {"confirmed": "Close ABC-A-001"}), ("typed sweep", {"sweep": True}), ("sweep", {"kind": "sweep"}),
          ("prep", {"kind": "prep"}), ("generate", {"kind": "generate"}), ("check", {"kind": "check"}), ("load", {"kind": "load"}),
          ("narrow", {"kind": "generate", "only": L.ALERT_DRAFT_TOOLS}), ("search", {"kind": "search"}),
          ("edit-ai", {"kind": "edit-ai"}), ("shape-closed", {"kind": "shape-closed"}), ("notes-find", {"kind": "notes-find"})]
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


def started_kinds():
    """Every kind the server starts a Run with, read from its source: kind="…" literals (both arms of a conditional), `kind=mode`
    (a transcript's check or load), and the default (a chat, "ask"). Any other non-literal kind fails, so a new one is seen."""
    src = SERVER.read_text(encoding="utf-8")
    kinds = {"ask"}
    for call in re.findall(r"\bRun\((.*?)\)\n", src, re.S):
        m = re.search(r"\bkind=([^,]+?)(?:,|$)", call)
        if not m:
            continue
        val = m.group(1).strip()
        lits = re.findall(r'"([a-z-]+)"', val)
        if lits:
            kinds.update(lits)
        elif val == "mode":
            kinds.update(("check", "load"))
        else:
            raise AssertionError(f"a Run started with kind={val}: add it to this test and give it a KIND_ARGS entry")
    return kinds


class Table(unittest.TestCase):
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

    def test_each_kind_names_its_built_ins(self):
        self.assertEqual(sorted(self.calls), sorted(k for k, *_ in TABLE))
        for kind, tools, strict, note in TABLE:
            a = self.calls[kind]
            self.assertEqual(flag(a, "--tools"), tools, f"{kind}: {note}")
            self.assertEqual("--strict-mcp-config" in a[:a.index("--")], strict, f"{kind}: {note}")

    def test_no_dangerous_built_in_is_allowed_and_each_is_denied(self):
        for kind, *_ in TABLE:
            a = self.calls[kind]
            allowed, denied = flag(a, "--allowedTools").split(","), flag(a, "--disallowedTools").split(",")
            tools = flag(a, "--tools").split(",")
            for t in DANGEROUS:
                self.assertNotIn(t, allowed, kind)
                self.assertNotIn(t, tools, kind)
                self.assertIn(t, denied, kind)

    def test_prompt_still_last(self):
        for kind, *_ in TABLE:
            a = self.calls[kind]
            self.assertEqual(a.count("--"), 1, kind)
            self.assertEqual(a.index("--"), len(a) - 2, kind)


class Constants(unittest.TestCase):
    def test_every_started_kind_has_an_explicit_tools_entry(self):
        import live_server as L
        kinds = started_kinds()
        self.assertTrue({"ask", "sweep", "prep", "generate", "check", "load", "search", "edit-ai", "shape-closed",
                         "notes-find"} <= kinds, kinds)
        for k in kinds | set(L.KIND_TOOLS) | set(L.GUARDED_KINDS) | set(L.TOOLLESS_KINDS):
            self.assertIn(k, L.KIND_ARGS, f"run kind {k!r} has no explicit --tools (KIND_ARGS)")
            self.assertEqual(L.KIND_ARGS[k][0], "--tools", k)

    def test_an_unknown_kind_fails_closed(self):
        import live_server as L
        self.assertEqual(L.run_args("some-new-kind"), ["--tools", ""])
        self.assertEqual(L.run_args("generate", None, L.ALERT_DRAFT_TOOLS), ["--tools", "ToolSearch"])
        self.assertEqual(L.run_args("ask", None, L.ALERT_DRAFT_TOOLS), L.KIND_ARGS["ask"])   # a chat is never narrowed

    def test_every_run_denies_cover_the_dangerous_names(self):
        import live_server as L
        for t in DANGEROUS:
            self.assertIn(t, L.EVERY_RUN_DENIES)
        for k in L.KIND_ARGS:                                             # no kind's list names one
            self.assertFalse(set(L.KIND_ARGS[k][1].split(",")) & set(L.EVERY_RUN_DENIES), k)
        self.assertEqual(L.vip_deny(), L.DENY_TOOLS + [t for t in L.VIP_BUILTIN_DENIES if t not in L.DENY_TOOLS])   # main's, unchanged

    def test_the_deny_list_is_f3s_shared_list_plus_f2s_own(self):
        import live_server as L
        import permissions as P
        self.assertEqual(len(L.EVERY_RUN_DENIES), len(set(L.EVERY_RUN_DENIES)), "a name appears twice")
        self.assertEqual(L.EVERY_RUN_DENIES[:len(P.run_deny_extras())], P.run_deny_extras())      # imported, not copied
        self.assertFalse(set(L.F2_ONLY_DENIES) & set(P.run_deny_extras()), "an F2-only name is in F3's list already")
        self.assertEqual(set(L.EVERY_RUN_DENIES), set(PREVIOUS_NEVER_BUILTINS) | set(P.NON_M365_MCP_DENY))

    def test_a_kind_that_calls_mcp_tools_lists_toolsearch(self):
        import live_server as L
        for kind, tools, strict, note in TABLE:
            if kind in ("edit-ai", "shape-closed", "notes-find") or strict:   # no MCP tool at all
                continue
            self.assertIn("ToolSearch", tools.split(","), f"{kind}: {note}")
        for k, args in L.KIND_ARGS.items():
            if args[1] == "":
                self.assertTrue(k in L.TOOLLESS_KINDS or "--strict-mcp-config" in args
                                or not any(t.startswith("mcp__") for t in L.run_policy(k, None)[0]), k)


if __name__ == "__main__":
    unittest.main()
