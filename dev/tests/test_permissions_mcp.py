"""F3 (review #116): no allow rule for an MCP server other than Microsoft 365's reading tools, nor for a built-in tool that acts
outside the laptop, is written whatever is approved: not by the one card (settings_problem), not by a permission edit
(validate_edit), not by a PERMISSION: line from a run. Doctor flags one already in .claude/settings.json.

Run: python3 dev/tests/test_permissions_mcp.py
"""
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import REPO, Vault  # noqa: E402

sys.path.insert(0, str(REPO / "system" / "scripts"))
import permissions as P  # noqa: E402

M365 = "mcp__claude_ai_Microsoft_365__"
ACCEPTED = [M365 + t for t in P.M365_READ] + ["Bash(system/scripts/run report.py adhoc *)", "Write(inbox/notes/**)", "Read(**)"]
REFUSED = ["mcp__claude_ai_Todoist", "mcp__claude_ai_Todoist__*", "mcp__claude_ai_Todoist__add-tasks",
           "mcp__claude_ai_Todoist__find-tasks", "mcp__claude_ai_Claude_Docs", "mcp__claude_ai_Claude_Docs__delete",
           "mcp__claude_ai_Claude_Docs__update", "mcp__claude_ai_Slides_AI", "mcp__claude_ai_Slides_AI__generate_presentation",
           "mcp__claude_ai_Linear", "mcp__claude_ai_Linear__create_issue", "mcp__some_new_server", "mcp__some_new_server__*",
           "mcp__claude-vscode__getDiagnostics", "MCP__claude_ai_Todoist", "mcp__claude_ai_Microsoft_365",
           M365 + "outlook_send_mail", M365 + "sharepoint_delete_item", M365 + "a_new_tool"] + \
          list(P.ACTING_BUILTINS) + list(P.WRITING_BUILTINS) + \
          ["Monitor(*)", "SendMessage(*)", "NotebookEdit(projects/**)"]

# Claude Code 2.1.300's default built-in tool list, from a probe (Jarvis, 15-10-2026). To refresh it after a CLI update, start
# `claude -p` from a scratch folder outside the vault with no --tools and ask it to list its tool names (or read the stream-json
# `init` event's "tools" field), then paste the built-in names here (not the mcp__ ones) and sort each new name into
# P.ACTING_BUILTINS, P.WRITING_BUILTINS or LEFT_OUT below, with its reason.
CLI_BUILTINS_2_1_300 = (
    "Task", "Artifact", "ArtifactComments", "ArtifactData", "Bash", "CronCreate", "CronDelete", "CronList", "DesignSync", "Edit",
    "EnterWorktree", "ExitWorktree", "ListAgents", "ListMcpResourcesTool", "Monitor", "NotebookEdit", "PushNotification", "Read",
    "ReadMcpResourceDirTool", "ReadMcpResourceTool", "RemoteTrigger", "ReportFindings", "ScheduleWakeup", "SendMessage", "Skill",
    "TaskStop", "ToolSearch", "WebFetch", "WebSearch", "Workflow", "Write")
LEFT_OUT = {
    "Task", "Bash", "Edit", "Read", "Write", "Skill",   # creaite's own runs use them; their allow rules have their own checks
    "ToolSearch",                                       # only loads deferred tools' schemas
    "WebFetch",                                         # reading a web page is outside content; .claude/settings.json denies it
    "ListAgents", "ListMcpResourcesTool", "ReadMcpResourceTool", "ReadMcpResourceDirTool",   # read only
    "ReportFindings",                                   # hands a report back to the caller; nothing leaves the laptop
    "WebSearch",                                        # approvable on the one card (BL-141); each run's --tools decides it
}


def with_rule(rule):
    before = json.loads((REPO / ".claude" / "settings.json").read_text(encoding="utf-8"))
    after = json.loads(json.dumps(before))
    after["permissions"]["allow"].append(rule)
    return before, after


class Table(unittest.TestCase):
    def test_accepted_rules(self):
        for rule in ACCEPTED:
            self.assertIsNone(P.rule_refusal(rule), rule)
            self.assertIsNone(P.settings_problem("claude", *with_rule(rule)), rule)
        for rule in ACCEPTED[:len(P.M365_READ)]:
            self.assertIsNone(P.broad_rule(rule), rule)
            self.assertIsNone(P.validate_edit("settings", *with_rule(rule)), rule)

    def test_refused_rules(self):
        for rule in REFUSED:
            self.assertTrue(P.rule_refusal(rule), rule)
            self.assertIn("is refused", P.settings_problem("claude", *with_rule(rule)) or "", rule)
            self.assertTrue(P.broad_rule(rule), rule)
            self.assertIn("is refused", P.validate_edit("settings", *with_rule(rule)) or "", rule)

    def test_reasons_are_plain(self):
        self.assertIn("another connector", P.rule_refusal("mcp__claude_ai_Todoist"))
        self.assertIn("Monitor acts outside the laptop", P.rule_refusal("Monitor"))
        self.assertIn("sends, deletes or changes", P.rule_refusal(M365 + "outlook_send_mail"))

    def test_the_shipped_files_still_validate(self):
        for name in (".claude/settings.json",):
            data = json.loads((REPO / name).read_text(encoding="utf-8"))
            self.assertIsNone(P.settings_problem("claude", data, data))
            self.assertEqual([r for r in data["permissions"].get("allow", []) if P.rule_refusal(r)], [])

    def test_constants_are_pinned(self):
        self.assertEqual(P.MCP_SAFE, ())
        self.assertEqual(P.ACTING_BUILTINS, (
            "EnterWorktree", "ExitWorktree", "RemoteTrigger", "Workflow", "Monitor", "PushNotification", "SendMessage",
            "CronCreate", "CronDelete", "CronList", "ScheduleWakeup", "DesignSync", "Artifact", "ArtifactComments", "ArtifactData",
            "TaskStop"))
        self.assertEqual(P.WRITING_BUILTINS, ("NotebookEdit",))
        self.assertEqual(P.NON_M365_MCP_DENY, ("mcp__claude_ai_Todoist", "mcp__claude_ai_Claude_Docs", "mcp__claude_ai_Slides_AI",
                                               "mcp__claude_ai_Linear", "mcp__claude-vscode"))
        self.assertEqual(P.run_deny_extras(), list(P.NON_M365_MCP_DENY) + list(P.ACTING_BUILTINS) + list(P.WRITING_BUILTINS))

    def test_refused_builtins_match_the_cli_list(self):
        refused = P.ACTING_BUILTINS + P.WRITING_BUILTINS
        self.assertEqual(sorted(set(refused)), sorted(refused), "a name is listed twice")
        self.assertEqual([n for n in refused if n not in CLI_BUILTINS_2_1_300], [], "not a Claude Code 2.1.300 tool name")
        self.assertEqual(LEFT_OUT & set(refused), set())
        self.assertEqual(set(refused), set(CLI_BUILTINS_2_1_300) - LEFT_OUT,
                         "every CLI built-in is either refused or deliberately left out")
        for name in LEFT_OUT:                                   # left out: no refusal from the connector check
            self.assertIsNone(P.tool_problem(name), name)


class PermissionCard(unittest.TestCase):
    """A PERMISSION: line from a run (perhaps injected through mail) never becomes an item on the card."""

    def ask(self, rule):
        import live_server
        events = []

        class Stub:
            denied_raw = []

            def emit(self, kind, **kw):
                events.append((kind, kw))

        p = re.match(r"PERMISSION:\s*(.+?)\s*\|\s*(.+)", f"PERMISSION: {rule} | to keep your tasks in step")
        return live_server.Run._permission(Stub(), p), events

    def test_smuggled_rules_are_refused(self):
        for rule in ("mcp__claude_ai_Todoist", "mcp__claude_ai_Claude_Docs__delete", "Monitor", "mcp__claude_ai_Linear__*",
                     M365 + "outlook_send_mail"):
            item, events = self.ask(rule)
            self.assertIsNone(item, rule)
            self.assertEqual(events[-1][0], "permission", rule)
            self.assertFalse(events[-1][1]["ok"], rule)
            self.assertNotEqual(events[-1][1]["state"], "addable", rule)

    def test_add_rule_content_refuses(self):
        for rule in ("mcp__claude_ai_Todoist", "ArtifactData", "mcp__claude_ai_Slides_AI__generate_presentation"):
            text, _, why = P.add_rule_content(rule)
            self.assertIsNone(text, rule)
            self.assertTrue(why, rule)


class Doctor(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        self.addCleanup(self.v.cleanup)
        self.file = self.v.root / ".claude" / "settings.json"

    def line(self):
        out = subprocess.run([sys.executable, str(self.v.root / "system/scripts/doctor.py")], cwd=self.v.root,
                             capture_output=True, text=True).stdout
        return next(line for line in out.splitlines() if "Assistant permissions" in line)

    def test_doctor_flags_another_connector_or_an_acting_builtin(self):
        self.assertNotIn("broader than creaite asks for", self.line())
        for rule, why in (("mcp__claude_ai_Todoist", "another connector"), ("Monitor", "acts outside the laptop")):
            data = json.loads(self.file.read_text())
            data["permissions"]["allow"].append(rule)
            self.file.write_text(json.dumps(data))
            line = self.line()
            self.assertIn("broader than creaite asks for", line)
            self.assertIn(why, line)
            data["permissions"]["allow"].remove(rule)
            self.file.write_text(json.dumps(data))


if __name__ == "__main__":
    unittest.main()
