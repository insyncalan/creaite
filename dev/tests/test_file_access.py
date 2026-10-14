"""BL-93: creaite reads every project document, creates files when asked, and changes an existing file only through filechange.py.

Run: python3 dev/tests/test_file_access.py
A fictional OneDrive-style projects root under a fake home (as in test_onedrive_projects.py); nothing real is touched.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_onedrive_projects import OneDriveCase, ROOT_SETTING, touch  # noqa: E402

ROOT_PATTERN = ROOT_SETTING


class FileChangeTests(OneDriveCase):
    def fc(self, *args, ok=True):
        r = self.v.run(*args, script="filechange.py", ok=False)
        if ok:
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def stage(self, name, text="new text\n"):
        return touch(self.v.root / "system/staging" / name, text)

    def check(self, path, *flags):
        return json.loads(self.fc("check", path, *flags).stdout)

    P = "projects/Example Programme/04 Reporting/Steerco"

    def test_a_new_file_is_created_in_a_mapped_folder(self):
        self.stage("pack.md")
        r = self.fc("create", f"{self.P}/2026-10-08 Steerco pack.md", "--from", "system/staging/pack.md", "--why", "Steerco pack for Alan")
        self.assertIn("Created", r.stdout)
        self.assertEqual((self.eng("ABC", "04 Reporting", "Steerco", "2026-10-08 Steerco pack.md")).read_text(), "new text\n")

    def test_creating_never_overwrites_a_name_clash_gets_a_number(self):
        existing = touch(self.eng("ABC", "04 Reporting", "Steerco", "pack.md"), "mine")
        self.stage("pack.md")
        self.fc("create", f"{self.P}/pack.md", "--from", "system/staging/pack.md")
        self.fc("create", f"{self.P}/pack.md", "--from", "system/staging/pack.md")
        self.assertEqual(existing.read_text(), "mine")
        self.assertTrue(existing.with_name("pack (2).md").exists())
        self.assertTrue(existing.with_name("pack (3).md").exists())

    def test_refused_places(self):
        # BL-141: reach.py decides; never is refused, and outside the projects folder needs Alan's approval on the card
        for path, why in ((f"projects/Example Programme/zz Archive/old.md", "zz Archive"),
                          (f"projects/_Templates/x.md", "_Templates is never read or written"),
                          (f"projects/Example Programme/_Templates/x.md", "_Templates"),
                          (f"projects/Example Programme/../../outside.md", "needs approval: it is outside the vault and the projects folder"),
                          ("/etc/passwd", "part of the operating system"),
                          ("system/scripts/tracker.py", "their own commands"),
                          ("system/tracker.db", "their own commands")):
            c = self.check(path)
            self.assertFalse(c["ok"], path)
            self.assertIn(why, c["reason"], path)

    def test_from_must_be_in_staging(self):
        outside = touch(self.home / "evil.md", "x")
        r = self.fc("create", f"{self.P}/a.md", "--from", str(outside), ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(self.eng("ABC", "04 Reporting", "Steerco", "a.md").exists())

    def test_edit_saves_the_earlier_version_logs_and_undoes(self):
        f = touch(self.eng("ABC", "03 Delivery", "Design", "plan.md"), "old\n")
        self.stage("plan.md", "better\n")
        r = self.fc("edit", "projects/Example Programme/03 Delivery/Design/plan.md", "--from", "system/staging/plan.md", "--why", "fix the date")
        self.assertIn("Changed", r.stdout)
        self.assertEqual(f.read_text(), "better\n")
        saved = list((self.v.root / "system/backups/files/changes").rglob("plan.md"))
        self.assertEqual([p.read_text() for p in saved], ["old\n"])
        log = [json.loads(x) for x in (self.v.root / "system/config/files-log.jsonl").read_text().splitlines()]
        self.assertEqual((log[0]["op"], log[0]["why"]), ("edit", "fix the date"))
        self.assertIn("plan.md", self.fc("list").stdout)
        self.fc("undo")
        self.assertEqual(f.read_text(), "old\n")
        self.assertIn("(undone)", self.fc("list").stdout)

    def test_edit_needs_an_existing_file_and_a_reason(self):
        self.stage("x.md")
        self.assertFalse(self.check(f"{self.P}/none.md", "--edit")["ok"])
        touch(self.eng("ABC", "04 Reporting", "Steerco", "e.md"))
        r = self.fc("edit", f"{self.P}/e.md", "--from", "system/staging/x.md", ok=False)
        self.assertNotEqual(r.returncode, 0)

    def test_undo_leaves_a_file_alone_if_it_changed_since(self):
        f = touch(self.eng("ABC", "03 Delivery", "Design", "p.md"), "old\n")
        self.stage("p.md", "new\n")
        self.fc("edit", "projects/Example Programme/03 Delivery/Design/p.md", "--from", "system/staging/p.md", "--why", "x")
        f.write_text("Alan edited this\n")
        r = self.fc("undo", ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(f.read_text(), "Alan edited this\n")

    def test_undo_of_a_create_removes_it_only_if_untouched(self):
        self.stage("c.md")
        self.fc("create", f"{self.P}/c.md", "--from", "system/staging/c.md")
        self.fc("undo")
        self.assertFalse(self.eng("ABC", "04 Reporting", "Steerco", "c.md").exists())

    def approved(self, change):
        """Make a sensitive change the way the live server does after Alan's Approve: an approval issued in this process."""
        return self.py("import reach, filechange\n"
                       f"ch = {change!r}\n"
                       "tok = reach.APPROVALS.issue(filechange.fingerprint(ch))\n"
                       "print(json.dumps(filechange.perform(ch, tok, 'dashboard')))")

    def test_move_and_delete_keep_a_way_back(self):
        f = touch(self.eng("ABC", "03 Delivery", "Design", "m.md"), "keep\n")
        base = "projects/Example Programme/03 Delivery/Design"
        r = self.fc("move", f"{base}/m.md", f"{base}/Renamed/m2.md", "--why", "tidy", ok=False)   # BL-141: a move is sensitive
        self.assertEqual(r.returncode, 3, r.stdout)
        self.assertIn("Needs approval", r.stdout)
        self.assertTrue(f.exists())
        self.assertEqual(self.approved({"op": "move", "path": f"{base}/m.md", "to": f"{base}/Renamed/m2.md", "why": "tidy"})[0], 0)
        moved = self.eng("ABC", "03 Delivery", "Design", "Renamed", "m2.md")
        self.assertTrue(moved.exists() and not f.exists())
        self.fc("undo")
        self.assertTrue(f.exists() and not moved.exists())
        self.assertFalse(moved.parent.exists())                 # the folder it made is gone again
        self.assertEqual(self.fc("delete", f"{base}/m.md", "--why", "obsolete", ok=False).returncode, 3)
        self.assertTrue(f.exists())
        self.assertEqual(self.approved({"op": "delete", "path": f"{base}/m.md", "why": "obsolete"})[0], 0)
        self.assertFalse(f.exists())
        self.fc("undo")
        self.assertEqual(f.read_text(), "keep\n")

    def test_move_never_overwrites(self):
        base = "projects/Example Programme/03 Delivery/Design"
        touch(self.eng("ABC", "03 Delivery", "Design", "a.md"), "a")
        b = touch(self.eng("ABC", "03 Delivery", "Design", "b.md"), "b")
        r = self.fc("move", f"{base}/a.md", f"{base}/b.md", "--why", "x", ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(b.read_text(), "b")

    def test_nothing_moves_into_zz_archive(self):
        base = "projects/Example Programme"
        touch(self.eng("ABC", "03 Delivery", "Design", "a.md"), "a")
        r = self.fc("move", f"{base}/03 Delivery/Design/a.md", f"{base}/zz Archive/a.md", "--why", "x", ok=False)
        self.assertNotEqual(r.returncode, 0)


class ProjectPermissionTests(OneDriveCase):
    """permissions.py accepts projects/<folder>/… and nothing wider; the rule is written in the form Claude Code needs."""

    def perm(self, *args, ok=True):
        return self.v.run(*args, script="permissions.py", ok=ok)

    def checked(self, rule):
        return json.loads(self.perm("check", rule).stdout)

    def settings(self):
        return json.loads((self.v.root / ".claude/settings.json").read_text())["permissions"]

    def test_only_a_named_project_folder_is_accepted(self):
        self.assertTrue(self.checked("Write(projects/Example Programme/04 Reporting/Steerco/**)")["ok"])
        for rule, why in (("Write(projects/**)", "name the project folder"), ("Edit(projects/*/04 Reporting/**)", "name the project folder"),
                          ("Write(projects/Example Programme/zz Archive/**)", "zz Archive"),
                          ("Write(projects/Example Programme/_Templates/**)", "_Templates"),
                          ("Write(~/Documents/**)", "inside the vault"), ("Write(//Users/x/**)", "inside the vault"),
                          ("Write(projects/../system/scripts/x.py)", "inside the vault")):
            r = self.checked(rule)
            self.assertFalse(r["ok"], rule)
            self.assertIn(why, r["reason"], rule)

    def test_an_external_projects_rule_is_written_home_relative_and_undone(self):
        before = self.settings()["allow"]
        self.perm("apply", "Write(projects/Example Programme/04 Reporting/Steerco/**)", "--why", "file Steerco packs")
        added = [r for r in self.settings()["allow"] if r not in before]
        self.assertEqual(added, [f"Write({ROOT_PATTERN}/Example Programme/04 Reporting/Steerco/**)"])
        self.assertFalse(self.checked("Write(projects/Example Programme/04 Reporting/Steerco/**)")["ok"])      # now covered
        self.assertIn(added[0], self.perm("list").stdout + json.dumps(self.settings()))
        self.perm("undo")
        self.assertEqual(self.settings()["allow"], before)

    def test_projects_root_is_added_as_a_directory_once_and_undone(self):
        self.perm("projects-root", "--why", "read the project documents")
        self.assertEqual(self.settings()["additionalDirectories"], [ROOT_PATTERN])
        r = self.perm("projects-root", "--why", "again", ok=False)
        self.assertNotEqual(r.returncode, 0)
        listing = json.loads(self.perm("list", "--json").stdout)
        self.assertEqual(listing["directories"], [ROOT_PATTERN])
        self.assertEqual(listing["changes"][0]["kind"], "dir")
        self.perm("undo")
        self.assertEqual(self.settings().get("additionalDirectories", []), [])

    def test_doctor_flags_a_broader_rule_and_a_missing_directory(self):
        doc = lambda: self.v.run(script="doctor.py", ok=False).stdout
        self.assertIn("WARN  Assistant permissions", doc())                 # external, folder not yet readable
        self.assertIn("permissions.py projects-root", doc())
        self.perm("projects-root", "--why", "read the project documents")
        self.assertIn("PASS  Assistant permissions", doc())
        f = self.v.root / ".claude/settings.json"
        data = json.loads(f.read_text())
        data["permissions"]["allow"].append("Write(*)")
        data["permissions"]["additionalDirectories"].append("/Users/someone")
        f.write_text(json.dumps(data))
        out = doc()
        self.assertIn("WARN  Assistant permissions", out)
        self.assertIn("Write(*)", out)
        self.assertIn("/Users/someone", out)

    def test_doctor_reports_a_read_only_mapped_folder(self):
        import os
        d = self.eng("ABC", "04 Reporting", "Steerco")
        os.chmod(d, 0o555)
        try:
            self.assertIn("Steerco is read-only", self.v.run(script="doctor.py", ok=False).stdout)
        finally:
            os.chmod(d, 0o755)
        import shutil
        shutil.rmtree(d)
        self.assertIn("Steerco isn't there", self.v.run(script="doctor.py", ok=False).stdout)


class AssistantRunTests(OneDriveCase):
    """The headless run is told about the projects root and denied the folders creaite never touches."""

    def test_the_run_gets_the_root_and_the_deny_list(self):
        o = self.py("""import live_server as L
print(json.dumps({'dirs': L.extra_dirs(), 'deny': L.deny_tools(), 'read': L.READ_TOOLS, 'write': L.WRITE_TOOLS}))""")
        self.assertEqual(o["dirs"], [str(self.root)])
        for tool in ("Read", "Edit", "Write"):
            self.assertIn(f"{tool}({ROOT_PATTERN}/**/zz Archive/**)", o["deny"])
            self.assertIn(f"{tool}({ROOT_PATTERN}/**/_Templates/**)", o["deny"])
            self.assertIn(f"{tool}({ROOT_PATTERN}/**/99 System/**)", o["deny"])            # BL-112: creaite's own folder (the backups)
        self.assertIn("Bash(python3 system/scripts/filechange.py *)", o["write"])
        self.assertNotIn("Bash(python3 system/scripts/filechange.py *)", o["read"])        # only a confirmed run may write
        self.assertIn("Bash(python3 system/scripts/filechange.py check *)", o["read"])
        self.assertFalse([t for t in o["read"] if t.startswith(("Edit", "Write"))])

    def test_inside_the_vault_there_is_no_extra_folder(self):
        v = __import__("test_tracker").Vault()
        try:
            src = f"import sys, json; sys.path.insert(0, {str(v.root / 'system/scripts')!r})\nimport live_server as L; print(json.dumps([L.extra_dirs(), [d for d in L.deny_tools() if d.startswith('Write(projects/**/')]]))"
            r = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True, cwd=tempfile.gettempdir())
            self.assertEqual(json.loads(r.stdout.strip().splitlines()[-1]), [[], ["Write(projects/**/zz Archive/**)", "Write(projects/**/_Templates/**)", "Write(projects/**/99 System/**)"]])
        finally:
            v.cleanup()


class VaultEditTests(OneDriveCase):
    """BL-96: the vault files the panel may edit, one at a time; and the ones it never may."""

    def fc(self, *args, ok=True):
        r = self.v.run(*args, script="filechange.py", ok=False)
        if ok:
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def stage(self, text="changed\n"):
        return touch(self.v.root / "system/staging/new.txt", text)

    def check(self, path, *flags):
        return json.loads(self.fc("check", path, *flags).stdout)

    def test_the_named_vault_files_can_be_edited_with_a_backup_and_undo(self):
        for rel in ("inbox/note.txt", "system/staging/drafts/d.md", "README.md",                    # BL-141: ordinary, at once
                    "system/templates/help.md", ".claude/skills/cx-edit/SKILL.md", "projects/_portfolio/PORTFOLIO.md"):
            f = self.v.root / rel if not rel.startswith("projects/") else self.root / "_Portfolio" / "PORTFOLIO.md"
            if not f.exists():
                touch(f, "old\n")
            before = f.read_bytes()
            self.stage()
            self.fc("edit", rel, "--from", "system/staging/new.txt", "--why", "Alan asked")
            self.assertEqual(f.read_text(), "changed\n", rel)
            self.fc("undo")
            self.assertEqual(f.read_bytes(), before, rel)

    def approved(self, change):
        return FileChangeTests.approved(self, change)

    def test_a_project_memory_file_can_be_edited(self):
        rel = "projects/Example Programme/CLAUDE.md"
        self.stage("# new memory\n")
        r = self.fc("edit", rel, "--from", "system/staging/new.txt", "--why", "add a line", ok=False)    # BL-141: sensitive (kind 1)
        self.assertEqual(r.returncode, 3, r.stdout)
        self.assertNotEqual(self.eng("ABC", "CLAUDE.md").read_text(), "# new memory\n")
        self.assertEqual(self.approved({"op": "edit", "path": rel, "data": b"# new memory\n", "why": "add a line"})[0], 0)
        self.assertEqual(self.eng("ABC", "CLAUDE.md").read_text(), "# new memory\n")
        for rel in ("CLAUDE.md", "system/config/schedules.md"):
            touch(self.v.root / rel, "old\n") if not (self.v.root / rel).exists() else None
            self.stage()
            self.assertEqual(self.fc("edit", rel, "--from", "system/staging/new.txt", "--why", "x", ok=False).returncode, 3, rel)

    def test_the_record_the_engine_and_generated_files_are_refused(self):
        for rel, why in (("system/tracker.db", "their own commands"), ("tracker-view.xlsx", "generated"), ("dashboard.html", "generated"),
                         ("system/history/2026-10-01.html", "own record"), ("system/scripts/schema.sql", "their own commands"),
                         ("system/scripts/paths.py", "their own commands"), ("system/scripts/tracker.py", "their own commands"),
                         ("system/creaite-rules.md", "their own commands"), ("VERSION", "their own commands"),
                         ("system/releases/creaite-1.0.0.zip", "their own commands"),
                         ("system/backups/x.json", "own record"), ("system/processed.txt", "own record"),
                         ("system/staging/run-log.txt", "own record"), ("system/staging/proposed-x.json", "own record")):   # BL-141: never
            c = self.check(rel, "--edit")
            self.assertFalse(c["ok"], rel)
            self.assertIn(why, c["reason"], rel)
            self.stage()
            r = self.fc("edit", rel, "--from", "system/staging/new.txt", "--why", "x", ok=False)
            self.assertNotEqual(r.returncode, 0, rel)

    def test_the_permission_files_point_to_the_confirmed_route(self):
        for rel in (".claude/settings.json", ".claude/settings.local.json", "system/config/settings.json"):   # BL-141: the card
            touch(self.v.root / rel, "{}") if not (self.v.root / rel).exists() else None
            c = self.check(rel, "--edit")
            self.assertEqual((c["ok"], c["kind"]), (False, "sensitive"), rel)
            self.assertIn("needs approval", c["reason"])
        c = self.check("system/scripts/permissions.py", "--edit")
        self.assertEqual((c["ok"], c["kind"]), (False, "never"))

    def test_a_link_cannot_lead_out_of_the_allowed_files(self):
        link = self.v.root / "inbox" / "sneaky.md"
        link.symlink_to(self.v.root / ".claude" / "settings.json")
        self.stage("{}")
        r = self.fc("edit", "inbox/sneaky.md", "--from", "system/staging/new.txt", "--why", "x", ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("allow", (self.v.root / ".claude/settings.json").read_text())      # untouched
        outside = self.home / "outside.md"
        touch(outside, "o")
        (self.v.root / "inbox" / "out.md").symlink_to(outside)
        r = self.fc("edit", "inbox/out.md", "--from", "system/staging/new.txt", "--why", "x", ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(outside.read_text(), "o")

    def test_a_link_inside_a_project_folder_cannot_reach_the_engine_or_the_database(self):
        design = self.eng("ABC", "03 Delivery", "Design")
        for name, target in (("engine.md", self.v.root / "system/scripts/tracker.py"), ("perm.md", self.v.root / ".claude/settings.json"),
                             ("db.md", self.v.root / "system/tracker.db")):
            target.parent.mkdir(parents=True, exist_ok=True)
            target.touch()
            before = target.read_bytes()
            (design / name).symlink_to(target)
            self.stage("hijack\n")
            r = self.fc("edit", f"projects/Example Programme/03 Delivery/Design/{name}", "--from", "system/staging/new.txt", "--why", "x", ok=False)
            self.assertNotEqual(r.returncode, 0, name)
            self.assertEqual(target.read_bytes(), before, name)
            r = self.fc("delete", f"projects/Example Programme/03 Delivery/Design/{name}", "--why", "x", ok=False)
            self.assertNotEqual(r.returncode, 0, name)
            self.assertTrue(target.exists(), name)

    def test_nothing_is_created_in_the_vault_and_move_delete_are_for_projects_only(self):
        # BL-141: creating in the vault is ordinary now; a delete or a move anywhere needs Alan's approval
        self.stage()
        r = self.fc("create", "inbox/brand-new.md", "--from", "system/staging/new.txt", ok=False)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertTrue((self.v.root / "inbox/brand-new.md").exists())
        touch(self.v.root / "inbox/a.md", "a")
        self.assertNotEqual(self.fc("delete", "inbox/a.md", "--why", "x", ok=False).returncode, 0)
        self.assertNotEqual(self.fc("move", "inbox/a.md", "inbox/b.md", "--why", "x", ok=False).returncode, 0)
        self.assertTrue((self.v.root / "inbox/a.md").exists())


if __name__ == "__main__":
    unittest.main()
