"""Every run kind names its built-in tools (F2, #116 review): `--tools` is an allow list per kind, never left out.

A run started with no `--tools` gets every built-in tool in the installed Claude Code, including ones that run headless with no
permission prompt and that neither the guard hook nor a deny list looks at (EnterWorktree, RemoteTrigger, CronCreate, Monitor,
SendMessage, Workflow…). So each kind's `--tools` is pinned here, a new kind without an entry fails the test, and the built-ins no
kind needs are denied by name in every run as well (builtin_denies: F3's permissions.run_deny_extras() plus every name in
permissions.KNOWN_BUILTINS, the one list, that the run's --tools doesn't name). No Task in a chat (#116 review).
A kind that calls an MCP tool lists ToolSearch (`--tools ""` hides deferred MCP tools; #116, Alan's live check). F4: Search's
answer also has `--strict-mcp-config`. The VIP check keeps main's command line; its deny list adds run_deny_extras() (#116 M1).

Each kind is started through the run engine with a stand-in `claude` (CREAITE_CLAUDE) that records its argv, its working folder
and its auto-memory switch; nothing calls Claude.
#126: the tool-less kinds start in an empty folder outside the vault, with `--setting-sources ""` and auto-memory off, so no
CLAUDE.md (the vault's or ~/.claude's) and no auto-memory reaches them; every kind with tools keeps the vault as its folder.

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
CHAT = "Read,Grep,Glob,Bash,Write,Edit,Skill,ToolSearch"
SWEEP = "Read,Grep,Glob,Bash,Write,Edit,Skill,ToolSearch"
HELD = "Read,Grep,Glob,Bash,ToolSearch"
# kind (as started) | expected --tools | --strict-mcp-config | notes
TABLE = [
    ("ask", CHAT, False, "a chat: the guard hook checks every call; skills (cx-*, docx) need Skill; no Task: nothing uses a subagent"),
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
    ("shape-closed", "", True, "BL-286: no tools, no MCP (#126 review)"),
    ("notes-find", "", True, "BL-301 E: no tools, no MCP (#126 review)"),
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
import json, os, sys
from pathlib import Path
open(__file__ + ".calls", "a", encoding="utf-8").write(json.dumps(sys.argv[1:]) + "\n")
cwd = os.getcwd()
up = [str(d) for d in [Path(cwd), *Path(cwd).parents] if (d / "CLAUDE.md").exists()]
open(__file__ + ".ctx", "a", encoding="utf-8").write(json.dumps({"cwd": os.path.realpath(cwd), "files": os.listdir(cwd),
    "claude_md": up, "no_memory": os.environ.get("CLAUDE_CODE_DISABLE_AUTO_MEMORY")}) + "\n")
print(json.dumps({"type": "system", "subtype": "init", "session_id": "sess-t"}), flush=True)
print(json.dumps({"type": "result", "result": "{}", "session_id": "sess-t"}), flush=True)
'''

RUNS = r'''
import json, sys, time
sys.path.insert(0, "system/scripts")
import live_server as L
L.NEUTRAL_CWD = None                                      # #126: this run makes its own neutral folder
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
        (v.root / "CLAUDE.md").write_text("Marker: the vault's own notes.\n")   # #126: a tool-less run never sees it
        drop = ("CREAITE_RUN_KIND", "CLAUDE_CODE_DISABLE_AUTO_MEMORY")
        env = {**{k: x for k, x in os.environ.items() if k not in drop}, "CREAITE_CLAUDE": str(fake)}
        r = subprocess.run([sys.executable, "-c", RUNS], cwd=v.root, env=env, capture_output=True, text=True, timeout=300)
        assert r.returncode == 0, r.stderr[-2000:]
        names = json.loads(r.stdout.strip().splitlines()[-1])
        cls.calls = dict(zip(names, [json.loads(x) for x in Path(str(fake) + ".calls").read_text().splitlines()]))
        cls.ctx = dict(zip(names, [json.loads(x) for x in Path(str(fake) + ".ctx").read_text().splitlines()]))
        cls.vault = os.path.realpath(v.root)
        import live_server
        cls.L = live_server

    @classmethod
    def tearDownClass(cls):
        for c in cls.ctx.values():                         # #126: the neutral folder the run made
            if os.path.basename(c["cwd"]).startswith("creaite-toolless-") and os.path.isdir(c["cwd"]):
                os.rmdir(c["cwd"])
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

    def test_each_run_denies_every_built_in_it_doesnt_name(self):
        import permissions as P
        for kind, tools, *_ in TABLE:
            denied = set(flag(self.calls[kind], "--disallowedTools").split(","))
            allowed = {t for t in tools.split(",") if t}
            self.assertTrue(set(P.run_deny_extras()) <= denied, kind)
            self.assertTrue(set(P.KNOWN_BUILTINS) - allowed <= denied, kind)
            self.assertFalse(allowed & denied, kind)                     # what --tools names is never denied as a whole

    def test_every_kind_denies_run_deny_extras_on_its_command_line(self):
        import permissions as P
        extras = P.run_deny_extras()
        self.assertTrue({"mcp__claude_ai_Todoist", "mcp__claude_ai_Claude_Docs", "mcp__claude_ai_Slides_AI",
                         "mcp__claude_ai_Linear", "mcp__claude-vscode"} <= set(extras))
        for kind, *_ in TABLE:                                           # #116 review M1: every started kind, 'only' included
            denied = flag(self.calls[kind], "--disallowedTools").split(",")
            for t in extras:
                self.assertIn(t, denied, f"{kind}: {t}")

    def test_no_kind_has_a_subagent(self):
        for kind, *_ in TABLE:                                           # #116 review L1: Task and Agent denied by name everywhere
            a = self.calls[kind]
            allowed, denied = flag(a, "--allowedTools").split(","), flag(a, "--disallowedTools").split(",")
            tools = flag(a, "--tools").split(",")
            for t in ("Task", "Agent"):
                self.assertIn(t, denied, kind)
                self.assertNotIn(t, tools, kind)
                self.assertFalse(any(x == t or x.startswith(t + "(") for x in allowed), kind)

    def test_tool_less_kinds_see_no_claude_md_and_no_memory(self):
        # #126: per kind, the launch's working folder and its context switches
        toolless = {"edit-ai", "shape-closed", "notes-find"}
        self.assertEqual(set(self.L.TOOLLESS_KINDS), toolless)
        for kind, *_ in TABLE:
            a, c = self.calls[kind], self.ctx[kind]
            before = a[:a.index("--")]
            if kind in toolless:
                self.assertEqual(flag(a, "--setting-sources"), "", kind)
                self.assertEqual(before.count("--no-session-persistence"), 1, kind)   # never resumed: nothing saved
                self.assertEqual(before.count("--strict-mcp-config"), 1, kind)        # no MCP server at all
                self.assertEqual(flag(a, "--model"), "sonnet", kind)                  # no settings files: the model named
                self.assertEqual(c["no_memory"], "1", kind)
                self.assertNotEqual(c["cwd"], self.vault, kind)
                self.assertFalse(c["cwd"].startswith(self.vault + os.sep), kind)
                self.assertEqual(c["files"], [], kind)                     # an empty folder of its own
                self.assertEqual(c["claude_md"], [], kind)                 # no CLAUDE.md in it or above it
                self.assertNotIn("--add-dir", before, kind)
            else:                                                          # the kinds with tools read the vault on purpose
                self.assertEqual(c["cwd"], self.vault, kind)
                self.assertNotIn("--setting-sources", before, kind)
                self.assertNotIn("--no-session-persistence", before, kind)
                self.assertNotIn("--model", before, kind)                             # the user's settings choose it
                self.assertIsNone(c["no_memory"], kind)

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

    def test_never_builtins_cover_the_dangerous_names(self):
        import live_server as L
        for t in DANGEROUS + ["Task", "Agent"]:
            self.assertIn(t, L.NEVER_BUILTINS)
        for k in L.KIND_ARGS:                                             # no kind's list names one
            self.assertFalse(set(L.KIND_ARGS[k][1].split(",")) & set(L.NEVER_BUILTINS), k)
        import permissions as P
        expected = list(L.DENY_TOOLS)                                     # #116 review M1: run_deny_extras() in the VIP check too
        for t in P.run_deny_extras() + L.VIP_BUILTIN_DENIES:
            if t not in expected:
                expected.append(t)
        self.assertEqual(L.vip_deny(), expected)

    def test_the_deny_lists_are_derived_from_the_one_list(self):
        import live_server as L
        import permissions as P
        self.assertEqual(L.KNOWN_BUILTINS, list(P.KNOWN_BUILTINS))
        self.assertEqual(L.NEVER_BUILTINS, [b for b in P.KNOWN_BUILTINS if not any(
            b in a[1].split(",") for a in [*L.KIND_ARGS.values(), L.NARROW_BUILTINS])])
        self.assertTrue(set(PREVIOUS_NEVER_BUILTINS) <= set(L.NEVER_BUILTINS))      # nothing F2 denied before is let in
        for kind, tools, *_ in TABLE:
            policy, kw = {"confirmed": ("ask", {"confirmed": "x"}), "typed sweep": ("ask", {}),
                          "narrow": ("generate", {"only": L.ALERT_DRAFT_TOOLS})}.get(kind, (kind, {}))
            d = L.builtin_denies(policy, kw.get("confirmed"), kw.get("only"))
            self.assertEqual(len(d), len(set(d)), f"{kind}: a name appears twice")
            self.assertEqual(d[:len(P.run_deny_extras())], P.run_deny_extras(), kind)          # F3's list, imported
            allowed = [t for t in tools.split(",") if t]
            self.assertEqual(set(d) - set(P.NON_M365_MCP_DENY), set(P.KNOWN_BUILTINS) - set(allowed), kind)
            self.assertTrue(set(d) <= set(L.run_policy(policy, kw.get("confirmed"), kw.get("only"))[1]), kind)

    def test_no_hand_written_list_names_an_unknown_built_in(self):
        import live_server as L
        import permissions as P
        lists = {"CHAT_BUILTINS": L.CHAT_BUILTINS, "SWEEP_BUILTINS": L.SWEEP_BUILTINS, "HELD_BUILTINS": L.HELD_BUILTINS,
                 "SEARCH_TOOLS": L.SEARCH_TOOLS, "ONLY_DENIES": L.ONLY_DENIES, "VIP_BUILTIN_ALLOWED": L.VIP_BUILTIN_ALLOWED,
                 "READ_TOOLS": L.READ_TOOLS, "WRITE_TOOLS": L.WRITE_TOOLS, "OPEN_TOOLS": L.OPEN_TOOLS, "DENY_TOOLS": L.DENY_TOOLS,
                 "ACTING_BUILTINS": P.ACTING_BUILTINS, "WRITING_BUILTINS": P.WRITING_BUILTINS,
                 **{f"KIND_TOOLS[{k}]": v for k, v in L.KIND_TOOLS.items()},
                 **{f"KIND_DENIES[{k}]": v for k, v in L.KIND_DENIES.items()},
                 **{f"KIND_ARGS[{k}]": a[1].split(",") for k, a in L.KIND_ARGS.items()}}
        for name, entries in lists.items():
            for e in entries:
                tool = re.match(r"^([A-Za-z_][\w-]*)", str(e))
                if not tool or tool.group(1).startswith("mcp__"):
                    continue
                self.assertIn(tool.group(1), P.KNOWN_BUILTINS, f"{name}: {e}")

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
