"""Tests for permissions.py (BL-75): the one safe way to widen what ask creaite may do.

Run: python3 dev/tests/test_permissions.py
Each test builds a throwaway vault (test_tracker.Vault) and runs the real script there.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import Vault  # noqa: E402


class PermissionsTests(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.file = self.v.root / ".claude/settings.json"
        self.before = self.file.read_text(encoding="utf-8")

    def tearDown(self):
        self.v.cleanup()

    def run_(self, *args, ok=True):
        return self.v.run(*args, script="permissions.py", ok=ok)

    def check(self, rule):
        return json.loads(self.run_("check", rule).stdout)

    def allow(self):
        return json.loads(self.file.read_text(encoding="utf-8"))["permissions"]["allow"]

    def test_narrow_rules_are_accepted(self):
        for rule in ("Write(inbox/notes/**)", "Write(projects/ABC Example Programme/reports/**)", "Write(system/search/index.json)",
                     "Bash(python3 system/scripts/update.py install *)", "Bash(python system/scripts/update.py undo)"):
            r = self.check(rule)
            self.assertEqual((r["ok"], r["reason"], r["covered"]), (True, "", None), rule)

    def test_refused_rules_say_why(self):
        for rule, why in (("Bash(node build.js)", "must run one creaite script"),
                          ("Bash(*)", "Bash on its own runs any command"),                     # BL-140: the true reason
                          ("Bash(python3 *)", "interpreter or shell, which runs anything"),
                          ("Bash(python3 -c print(1))", "shell characters"),
                          ("Bash(python3 system/scripts/report.py * && rm -rf /)", "shell characters"),
                          ("Bash(python3 system/scripts/permissions.py apply *)", "never allowed to the panel"),
                          ("Bash(python3 system/scripts/nope.py *)", "doesn't exist"),
                          ("Bash(curl https://example.com)", "must run one creaite script"),
                          ("Edit(.claude/settings.json)", "rules are only for"),
                          ("Edit(**)", "rules are only for"),
                          ("Edit(/tmp/x)", "inside the vault"),
                          ("Write(~/x)", "inside the vault"),
                          ("Write(projects/../.claude/settings.json)", "inside the vault"),
                          ("Edit(projects/x/.claude/settings.json)", "engine, the database"),
                          ("Write(system/staging/../scripts/x.py)", "inside the vault"),
                          ("Edit(system/scripts/tracker.py)", "rules are only for"),
                          ("Write(system/tracker.db)", "rules are only for"),
                          ("Read(**)", "only adds Bash, Edit and Write"),
                          ("WebFetch", "only adds Bash, Edit and Write"),
                          ("mcp__claude_ai_Microsoft_365__outlook_send_mail", "only adds Bash, Edit and Write"),
                          ("", "only adds Bash, Edit and Write")):
            r = self.check(rule)
            self.assertFalse(r["ok"], rule)
            self.assertIn(why, r["reason"], rule)

    def test_a_rule_already_granted_or_denied_is_not_added(self):
        r = self.check("Bash(python3 system/scripts/report.py adhoc *)")                      # covered by report.py *
        self.assertEqual((r["ok"], r["reason"], r["covered"]), (False, "already allowed", "Bash(python3 system/scripts/report.py *)"))
        r = self.check("Edit(system/staging/drafts/**)")
        self.assertEqual((r["ok"], r["covered"]), (False, "Edit(system/staging/**)"))
        data = json.loads(self.before)
        data["permissions"]["deny"].append("Write(inbox/private/**)")
        self.file.write_text(json.dumps(data))
        r = self.check("Write(inbox/private/**)")
        self.assertEqual((r["ok"], r["reason"]), (False, "it is denied by the rule Write(inbox/private/**)"))

    def test_apply_adds_the_rule_with_a_backup_and_a_log(self):
        rule = "Write(system/search/**)"
        out = self.run_("apply", rule, "--why", "Write search summaries", "--via", "dashboard").stdout
        self.assertIn(f"Added {rule}", out)
        self.assertEqual(self.allow()[-1], rule)
        data, old = json.loads(self.file.read_text()), json.loads(self.before)
        self.assertEqual({k: v for k, v in data.items() if k != "permissions"}, {k: v for k, v in old.items() if k != "permissions"})
        self.assertEqual(data["permissions"]["deny"], old["permissions"]["deny"])             # nothing else touched
        self.assertEqual(data["permissions"]["allow"], old["permissions"]["allow"] + [rule])
        backups = list((self.v.root / "system/backups").glob("claude-settings-*.json"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), self.before)                                   # the file as it was
        entry = json.loads((self.v.root / "system/config/permissions-log.jsonl").read_text().splitlines()[-1])
        self.assertEqual((entry["op"], entry["rule"], entry["why"], entry["via"], entry["id"]), ("add", rule, "Write search summaries", "dashboard", 1))
        line = json.loads((self.v.root / "system/config/settings-log.jsonl").read_text().splitlines()[-1])
        self.assertEqual((line["key"], line["old"], line["new"]), ("claude_permissions.allow", None, rule))

    def test_apply_refuses_what_check_refuses_and_needs_a_reason(self):
        r = self.run_("apply", "Bash(node x.js)", "--why", "needed", ok=False)
        self.assertIn("Not added:", r.stdout)
        self.assertEqual(self.file.read_text(), self.before)
        r = self.run_("apply", "Write(system/search/**)", ok=False)
        self.assertIn("say why the rule is needed", r.stderr)
        r = self.run_("apply", "Write(system/search/**)", "--why", "x" * 400, ok=False)
        self.assertEqual(self.file.read_text(), self.before)
        self.assertFalse((self.v.root / "system/config/permissions-log.jsonl").exists())
        self.assertEqual(list((self.v.root / "system/backups").glob("claude-settings-*")), [])

    def test_a_rule_is_added_once(self):
        self.run_("apply", "Write(system/search/**)", "--why", "a")
        out = self.run_("apply", "Write(system/search/**)", "--why", "a", ok=False).stdout
        self.assertIn("Not added: already allowed", out)
        self.assertEqual(self.allow().count("Write(system/search/**)"), 1)

    def test_undo_removes_only_that_rule_and_keeps_what_alan_added_since(self):
        self.run_("apply", "Write(system/search/**)", "--why", "first")
        self.run_("apply", "Write(inbox/notes/**)", "--why", "second")
        data = json.loads(self.file.read_text())                                              # Alan edits by hand afterwards
        data["permissions"]["allow"].append("Bash(git status)")
        self.file.write_text(json.dumps(data, indent=2))
        out = self.run_("undo").stdout
        self.assertIn("Removed Write(inbox/notes/**)", out)
        self.assertIn("Bash(git status)", self.allow())
        self.assertIn("Write(system/search/**)", self.allow())
        self.assertNotIn("Write(inbox/notes/**)", self.allow())
        self.run_("undo")
        self.assertNotIn("Write(system/search/**)", self.allow())
        self.assertIn("Nothing to undo.", self.run_("undo").stdout)
        entries = [json.loads(x) for x in (self.v.root / "system/config/permissions-log.jsonl").read_text().splitlines()]
        self.assertEqual([(e["op"], e.get("undoes")) for e in entries], [("add", None), ("add", None), ("undo", 2), ("undo", 1)])
        self.assertGreaterEqual(len(list((self.v.root / "system/backups").glob("claude-settings-*.json"))), 1)

    def test_undo_when_alan_already_removed_the_rule(self):
        self.run_("apply", "Write(system/search/**)", "--why", "a")
        data = json.loads(self.file.read_text())
        data["permissions"]["allow"].remove("Write(system/search/**)")
        self.file.write_text(json.dumps(data))
        self.assertIn("was already gone", self.run_("undo").stdout)
        self.assertIn("Nothing to undo.", self.run_("undo").stdout)

    def test_list(self):
        self.run_("apply", "Write(system/search/**)", "--why", "summaries")
        self.run_("undo")
        data = json.loads(self.run_("list", "--json").stdout)
        self.assertEqual([(c["rule"], c["undone"]) for c in data["changes"]], [("Write(system/search/**)", True)])
        self.assertIn("(undone) Write(system/search/**) — summaries [cli]", self.run_("list").stdout)

    def test_the_vaults_own_rules_keep_the_panel_out_of_claude_settings(self):
        deny = json.loads(self.before)["permissions"]["deny"]
        for rule in ("Edit(.claude/settings.json)", "Edit(.claude/settings.local.json)",
                     "Bash(python3 system/scripts/permissions.py *)", "Bash(python system/scripts/permissions.py *)"):
            self.assertIn(rule, deny)
        self.assertNotIn("Write(.claude/settings.json)", deny)               # retired in v1.2.0: it warned on every run and Edit(...) covers file edits
        self.assertNotIn("Write(.claude/settings.local.json)", deny)


class PermissionEditTests(unittest.TestCase):
    """BL-96: each edit of a permission file is its own confirmed change: exact, backed up, logged and undoable."""

    def setUp(self):
        self.v = Vault()
        self.settings = self.v.root / ".claude/settings.json"
        self.local = self.v.root / ".claude/settings.local.json"
        self.config = self.v.root / "system/config/settings.json"
        self.before = self.settings.read_text(encoding="utf-8")

    def tearDown(self):
        self.v.cleanup()

    def run_(self, *args, ok=True):
        return self.v.run(*args, script="permissions.py", ok=ok)

    def preview(self, spec):
        return json.loads(self.run_("preview", spec).stdout)

    def edit(self, spec, why="Alan asked", ok=True):
        return self.run_("edit", spec, "--why", why, ok=ok)

    def lists(self, f=None):
        return json.loads((f or self.settings).read_text(encoding="utf-8"))["permissions"]

    def test_add_and_remove_an_allow_rule_in_each_file_and_undo(self):
        rule = "Write(inbox/notes/**)"
        pv = self.preview(f"settings add allow {rule}")
        self.assertEqual((pv["ok"], pv["summary"]), (True, f"Add {rule} to .claude/settings.json › permissions.allow"))
        self.edit(f"settings add allow {rule}")
        self.assertIn(rule, self.lists()["allow"])
        self.edit(f"local add allow {rule}")                              # the local file is made if it isn't there
        self.assertEqual(self.lists(self.local)["allow"], [rule])
        self.edit(f"settings remove allow {rule}")
        self.assertNotIn(rule, self.lists()["allow"])
        for _ in range(3):
            self.run_("undo")
        self.assertEqual(self.settings.read_text(encoding="utf-8"), self.before)
        self.assertEqual(self.lists(self.local).get("allow", []), [])
        data = json.loads(self.run_("list", "--json").stdout)
        self.assertEqual([(c["op"], c["file"], c["undone"]) for c in data["changes"]],
                         [("add", "settings", True), ("add", "local", True), ("remove", "settings", True)])
        backups = list((self.v.root / "system/backups").glob("claude-settings*.json"))
        self.assertGreaterEqual(len(backups), 2)

    def test_blanket_and_unsafe_edits_are_refused_with_a_reason(self):
        for spec, why in (("settings add allow Write(*)", "rules are only for"), ("settings add allow Edit(.claude/settings.json)", "rules are only for"),
                          ("settings add allow Bash", "Bash on its own runs any command"), ("settings add allow Bash(node x.js)", "must run one creaite script"),
                          ("local add allow Write(~/**)", "inside the vault"), ("settings add allow Write(projects/**)", "name the project folder"),
                          ("settings add allow bypassPermissions", "skip-permissions"),
                          ("settings add dir /Users/someone", "only folder outside the vault"),
                          ("settings remove allow Write(inbox/none/**)", "isn't in"),
                          ("settings remove deny Edit(.claude/settings.json)", "keeps the panel out"),
                          ("settings remove deny WebFetch", "keeps the panel out"),
                          ("settings add allow Write(inbox/x/**) extra", "only adds Bash, Edit and Write rules")):
            pv = self.preview(spec)
            self.assertFalse(pv["ok"], spec)
            self.assertIn(why, pv["reason"], spec)
            r = self.edit(spec, ok=False)
            self.assertNotEqual(r.returncode, 0, spec)
        self.assertEqual(self.settings.read_text(encoding="utf-8"), self.before)
        self.assertFalse(self.local.exists())

    def test_a_deny_entry_can_be_added_and_removed_and_a_folder_only_if_it_is_the_projects_root(self):
        self.edit("settings add deny Edit(inbox/secret/**)")
        self.assertIn("Edit(inbox/secret/**)", self.lists()["deny"])
        self.edit("settings remove deny Edit(inbox/secret/**)")
        self.assertNotIn("Edit(inbox/secret/**)", self.lists()["deny"])
        self.assertFalse(self.preview("settings add dir ~/Library/CloudStorage/OneDrive-X/Engagements")["ok"])    # no projects root set

    def test_a_setting_changes_one_key_at_a_time_and_undoes(self):
        old = json.loads(self.config.read_text())["sweep"]["due_from"]
        pv = self.preview('config set sweep.due_from "06:30"')
        self.assertEqual(pv["summary"], f'Change sweep.due_from in system/config/settings.json: "{old}" → "06:30"')
        self.edit('config set sweep.due_from "06:30"')
        self.assertEqual(json.loads(self.config.read_text())["sweep"]["due_from"], "06:30")
        log = [json.loads(x) for x in (self.v.root / "system/config/settings-log.jsonl").read_text().splitlines()]
        self.assertEqual((log[-1]["key"], log[-1]["new"]), ("sweep.due_from", "06:30"))
        self.assertTrue(list((self.v.root / "system/backups").glob("settings-*.json")))
        self.run_("undo")
        self.assertEqual(json.loads(self.config.read_text())["sweep"]["due_from"], old)

    def test_settings_edits_are_checked(self):
        for spec, why in (('config set sweep "x"', "one setting at a time"), ('config set nope.key 1', "isn't a setting"),
                          ('config set sweep.due_from 5', "holds str"), ('config set sweep.due_from "x', "must be JSON"),
                          ('config set permissions.allow []', "isn't a setting creaite changes"),
                          ('config set sweep.due_from "07:00"', "is already")):
            pv = self.preview(spec)
            self.assertFalse(pv["ok"], spec)
            self.assertIn(why, pv["reason"], spec)

    def test_undo_leaves_a_setting_alone_if_it_changed_since(self):
        self.edit('config set sweep.due_from "06:30"')
        data = json.loads(self.config.read_text())
        data["sweep"]["due_from"] = "05:00"
        self.config.write_text(json.dumps(data))
        r = self.run_("undo", ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(json.loads(self.config.read_text())["sweep"]["due_from"], "05:00")

    def staged_script(self, transform=lambda t: t):
        src = (self.v.root / "system/scripts/permissions.py").read_text(encoding="utf-8")
        f = self.v.root / "system/staging/permissions-new.py"
        f.write_text(transform(src), encoding="utf-8")
        return "script system/staging/permissions-new.py"

    def test_permissions_py_is_replaced_only_by_a_file_that_compiles_and_passes_the_self_test(self):
        spec = self.staged_script(lambda t: t.replace("Anything else (a blanket", "Anything else, anything (a blanket"))
        pv = self.preview(spec)
        self.assertTrue(pv["ok"], pv)
        self.assertIn("passes the self-test", pv["summary"])
        self.assertTrue(any("anything" in line for line in pv["diff"]))
        self.edit(spec)
        self.assertIn("Anything else, anything", (self.v.root / "system/scripts/permissions.py").read_text())
        self.run_("undo")
        self.assertNotIn("Anything else, anything", (self.v.root / "system/scripts/permissions.py").read_text())

    def test_a_broken_or_too_permissive_permissions_py_is_refused(self):
        spec = self.staged_script(lambda t: t + "\nthis is not python (\n")
        self.assertIn("doesn't compile", self.preview(spec)["reason"])
        spec = self.staged_script(lambda t: t.replace("def check(rule, settings=None):", "def check(rule, settings=None):\n    return True, '', None\n\n\ndef _unused(rule, settings=None):"))
        pv = self.preview(spec)
        self.assertFalse(pv["ok"])
        self.assertIn("must refuse", pv["reason"])
        before = (self.v.root / "system/scripts/permissions.py").read_text()
        self.assertNotEqual(self.edit(spec, ok=False).returncode, 0)
        self.assertEqual((self.v.root / "system/scripts/permissions.py").read_text(), before)
        self.assertFalse(self.preview("script system/staging/../../evil.py")["ok"])
        self.assertFalse(self.preview("script inbox/permissions-new.py")["ok"])

    def test_every_change_is_listed(self):
        self.edit("settings add allow Write(inbox/notes/**)")
        self.edit('config set sweep.due_from "06:30"')
        out = self.run_("list").stdout
        self.assertIn("Write(inbox/notes/**)", out)
        self.assertIn('sweep.due_from = "06:30"', out)


if __name__ == "__main__":
    unittest.main()
