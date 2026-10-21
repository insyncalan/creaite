"""BL-141 part 1: reach.py, the one place that decides what ask creaite may touch. classify(path, operation) is ordinary,
sensitive or never, with a reason. One test per row of the never list, each kind of sensitive change, the ordinary cases,
symlink and `..` escapes, the home folder outside the vault, and a name in another case.

Run: python3 dev/tests/test_reach.py
A temporary home folder and temporary vaults only; nothing real is read or changed.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_onedrive_projects import OneDriveCase, touch  # noqa: E402
from test_tracker import REPO, Vault  # noqa: E402

sys.path.insert(0, str(REPO / "system" / "scripts"))
import reach as REACH  # noqa: E402  (the table only; every verdict below comes from the vault's own copy, run with HOME set)


class Reach(unittest.TestCase):
    """The default layout: projects inside the vault; a fake home folder beside it."""

    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix="creaite-home-")).resolve()
        self.v = Vault()
        self.root = self.v.root.resolve()
        self.env = {**os.environ, "HOME": str(self.home)}

    def tearDown(self):
        self.v.cleanup()
        shutil.rmtree(self.home, ignore_errors=True)

    def classify(self, cases, marked=False, count=0):
        """[(path, op)] -> [(kind, reason)], from the vault's own reach.py with HOME set to the fake home."""
        src = (f"import sys, json; sys.path.insert(0, {str(self.root / 'system/scripts')!r}); import reach\n"
               f"print(json.dumps([reach.classify(p, o, marked={marked}, count={count}) for p, o in {cases!r}]))")
        r = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True, cwd=tempfile.gettempdir(), env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return [tuple(x) for x in json.loads(r.stdout.strip().splitlines()[-1])]

    def one(self, path, op, **kw):
        return self.classify([(str(path), op)], **kw)[0]

    # ── the never list: one test per row ──
    def test_every_row_of_the_never_list(self):
        cases, want = [], []
        for base, pattern, ops, reason in REACH.NEVER:
            concrete = pattern.replace("*1password*", "2BUA8C4S2C.com.1password").replace("tracker.db*", "tracker.db")
            if base == "home":
                path = self.home / concrete
            elif base == "vault":
                path = self.root / concrete
            else:
                path = Path(concrete)
            op = "read" if ops == "all" else "change"
            cases.append((str(path / "inside.txt") if base != "vault" or "." not in Path(concrete).name else str(path), op))
            want.append((pattern, reason))
        got = self.classify(cases)
        for (pattern, reason), (path, op), (kind, why) in zip(want, cases, got):
            self.assertEqual(kind, "never", f"{pattern} ({path}, {op})")
            if not pattern.startswith("/"):
                self.assertEqual(why, reason, pattern)
            else:
                self.assertIn(why, (reason, "it is outside the vault, the projects folder and your home folder"), pattern)

    def test_secrets_are_refused_for_writing_too_and_records_only_for_writing(self):
        (kind, _), = self.classify([(str(self.home / ".ssh/id_rsa"), "create")])
        self.assertEqual(kind, "never")
        for rel in ("system/scripts/tracker.py", "system/tracker.db", "system/creaite-rules.md", "VERSION", "system/backups/x.db"):
            self.assertEqual(self.one(self.root / rel, "read")[0], "ordinary", rel)              # readable (CLAUDE.md imports the rules)
            for op in ("create", "change", "move", "delete"):
                self.assertEqual(self.one(self.root / rel, op)[0], "never", f"{rel} {op}")

    def test_the_database_the_engine_and_the_rules_stay_behind_their_commands(self):
        for rel in ("system/tracker.db", "system/tracker.db-wal", "system/scripts/schema.sql", "system/scripts/paths.py",
                    "system/scripts/reach.py", "system/creaite-rules.md", "VERSION", "system/releases/creaite-1.3.0.zip"):
            kind, why = self.one(self.root / rel, "change")
            self.assertEqual(kind, "never", rel)
            self.assertIn("their own commands", why, rel)

    def test_outside_the_vault_and_the_home_folder_is_never(self):
        outside = Path(tempfile.mkdtemp(prefix="creaite-outside-")).resolve()
        try:
            for op in ("read", "create"):
                kind, why = self.one(outside / "x.txt", op)
                self.assertEqual(kind, "never")
                self.assertIn("outside the vault, the projects folder and your home folder", why)
            self.assertEqual(self.one("/etc/hosts", "read"), ("never", REACH.SYSTEM))
            self.assertEqual(self.one("/usr/bin/python3", "change")[0], "never")
        finally:
            shutil.rmtree(outside, ignore_errors=True)

    # ── sensitive: each kind ──
    def test_kind_1_permission_and_settings_files(self):
        for path in (self.root / ".claude/settings.json", self.root / ".claude/settings.local.json", self.root / "system/config/settings.json",
                     self.root / "system/config/schedules.md", self.root / "system/templates/settings-defaults.json",
                     self.root / "projects/_portfolio/people-register.md", self.root / "projects/_portfolio/project-register.md",
                     self.root / "projects/ABC Example Programme/CLAUDE.md", self.root / "CLAUDE.md", self.root / ".mcp.json",
                     self.home / ".claude/settings.json"):
            kind, why = self.one(path, "change")
            self.assertEqual(kind, "sensitive", path)
            self.assertIn("changes what ask creaite may do", why, path)
        self.assertEqual(self.one(self.root / ".claude/skills/cx-edit/SKILL.md", "change")[0], "ordinary")    # skills are not settings
        self.assertEqual(self.one(self.root / "system/config/settings.json", "read")[0], "ordinary")          # reading is open

    def test_kind_2_outside_the_vault_and_the_projects_folder(self):
        for op in ("create", "change"):
            kind, why = self.one(self.home / "Documents/plan.md", op)
            self.assertEqual(kind, "sensitive", op)
            self.assertEqual(why, "it is outside the vault and the projects folder")
        self.assertEqual(self.one(self.home / "Documents/plan.md", "read"), ("ordinary", ""))

    def test_kind_3_deletes_moves_and_more_than_ten_files(self):
        note = touch(self.root / "projects/ABC Example Programme/notes/today.md", "notes\n")
        self.assertEqual(self.one(note, "change"), ("ordinary", ""))
        self.assertEqual(self.one(note, "delete")[0], "sensitive")
        self.assertIn("moves or renames", self.one(note, "move")[1])
        self.assertEqual(self.one(note, "change", count=9)[0], "ordinary")
        kind, why = self.one(note, "change", count=10)
        self.assertEqual(kind, "sensitive")
        self.assertIn("more than 10", why)

    def test_kind_4_another_persons_file(self):
        p = self.root / "projects/ABC Example Programme"
        sent = touch(p / "reports/2026-10-02 Weekly report.docx", b"PK")
        said = touch(p / "transcripts/2026-10-01 Steering.vtt", "WEBVTT\n")
        sow = touch(p / "documents/SOW.docx", b"PK")
        mine = touch(p / "documents/my notes.md", "notes\n")
        for f in (sent, said):
            kind, why = self.one(f, "change")
            self.assertEqual(kind, "sensitive", f)
            self.assertIn("may have been sent, or another person's words", why)
        self.assertIn("may be another person's", self.one(sow, "change")[1])
        self.assertEqual(self.one(mine, "change"), ("ordinary", ""))
        self.assertEqual(self.one(p / "reports/2026-10-09 Weekly report.docx", "create"), ("ordinary", ""))   # a new one is ordinary

    def test_kind_5_a_marked_run_may_change_only_drafts_and_staging(self):
        note = touch(self.root / "projects/ABC Example Programme/notes/today.md", "notes\n")
        kind, why = self.one(note, "change", marked=True)
        self.assertEqual(kind, "sensitive")
        self.assertIn("read outside content", why)
        self.assertEqual(self.one(self.root / "system/staging/drafts/spec.json", "create", marked=True), ("ordinary", ""))
        self.assertEqual(self.one(self.root / "system/staging/work.md", "create", marked=True), ("ordinary", ""))
        self.assertEqual(self.one(self.root / "inbox/note.md", "create", marked=True)[0], "sensitive")

    def test_ordinary_cases(self):
        for path, op in ((self.root / "projects/ABC Example Programme/notes/new.md", "create"), (self.root / "inbox/a.md", "create"),
                         (self.root / "system/staging/drafts/x.json", "create"), (self.root / "system/templates/help.md", "change"),
                         (self.home / "Documents/plan.md", "read"), (self.root / "projects/ABC Example Programme/CLAUDE.md", "read")):
            self.assertEqual(self.one(path, op), ("ordinary", ""), f"{path} {op}")

    # ── escapes and spellings ──
    def test_a_symlink_is_judged_by_where_it_points(self):
        (self.home / ".ssh").mkdir()
        touch(self.home / ".ssh/id_rsa", "secret")
        link = self.root / "inbox/innocent.txt"
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(self.home / ".ssh/id_rsa")
        self.assertEqual(self.one(link, "read"), ("never", REACH.SECRET))
        dlink = self.root / "inbox/eng"
        dlink.symlink_to(self.root / "system/scripts")
        self.assertEqual(self.one(dlink / "tracker.py", "change")[0], "never")

    def test_dotdot_is_resolved_first(self):
        self.assertEqual(self.one("inbox/../system/scripts/tracker.py", "change")[0], "never")
        self.assertEqual(self.one(str(self.home / "Documents/../.ssh/config"), "read"), ("never", REACH.SECRET))
        self.assertEqual(self.one("projects/../.claude/settings.json", "change")[0], "sensitive")

    def test_a_path_in_the_home_folder_outside_the_vault(self):
        self.assertEqual(self.one("~/Documents/plan.md", "read"), ("ordinary", ""))
        self.assertEqual(self.one("~/Documents/plan.md", "create")[0], "sensitive")
        self.assertEqual(self.one("~/.aws/credentials", "read")[0], "never")

    def test_names_in_another_case_are_the_same_place(self):
        self.assertEqual(self.one(self.root / ".CLAUDE/Settings.json", "change")[0], "sensitive")
        self.assertEqual(self.one(self.home / ".SSH/id_rsa", "read")[0], "never")
        self.assertEqual(self.one(self.root / "System/Scripts/tracker.py", "change")[0], "never")
        self.assertEqual(self.one(self.home / "library/keychains/login.keychain-db", "read")[0], "never")

    def test_operations_are_checked(self):
        src = f"import sys; sys.path.insert(0, {str(self.root / 'system/scripts')!r}); import reach; reach.classify('x', 'wipe')"
        r = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True, env=self.env)
        self.assertNotEqual(r.returncode, 0)


class ReachOneDrive(OneDriveCase):
    """With the projects in a OneDrive folder under the home folder: the projects root is in reach as the vault is."""

    def kind(self, path, op, **kw):
        return self.py(f"import reach; print(json.dumps(reach.classify({str(path)!r}, {op!r}, marked={kw.get('marked', False)})))")

    def test_project_files_are_in_reach_like_the_vault(self):
        eng = self.root / "Example Programme"
        note = touch(eng / "03 Delivery/Design/notes.md", "notes\n")
        self.assertEqual(self.kind(note, "change"), ["ordinary", ""])
        self.assertEqual(self.kind(eng / "03 Delivery/Design/new.md", "create"), ["ordinary", ""])
        self.assertEqual(self.kind("projects/Example Programme/03 Delivery/Design/new.md", "create"), ["ordinary", ""])   # a stored path
        said = touch(eng / "02 Meetings/Transcripts/2026-10-01 Steering.vtt", "WEBVTT\n")
        self.assertEqual(self.kind(said, "change")[0], "sensitive")
        self.assertEqual(self.kind(eng / "99 Archive/old.md", "read"), ["never", "99 Archive is never read or written by creaite"])
        self.assertEqual(self.kind(eng / "CLAUDE.md", "change")[0], "sensitive")

    def test_a_note_is_what_notes_note_of_accepts(self):
        """BL-301 (Alan, 15-10-2026): reach.is_note, the notes exemption from outside content (reach.read_reason), is notes.note_of on the real path;
        reading a note marks nothing, while its pictures, a subfolder and a transcript still do. Changing a note is unchanged."""
        eng, notes = self.root / "Example Programme", self.root / "Example Programme/08 Notes"
        cases = {str(touch(notes / "Kickoff.md", "x")): True, str(touch(self.root / "_Portfolio/08 Notes/Themes.md", "x")): True,
                 str(touch(notes / "_images/a.png", "x")): False, str(touch(notes / "_images/a.md", "x")): False,
                 str(touch(notes / "Old/b.md", "x")): False, str(touch(notes / "c.txt", "x")): False,
                 str(touch(eng / "03 Delivery/Design/d.md", "x")): False,
                 str(touch(eng / "02 Meetings/Transcripts/t.vtt", "WEBVTT\n")): False}
        got = self.py("import reach, notes\n"
                      f"ps = {list(cases)!r}\n"
                      "print(json.dumps([[reach.is_note(reach.real(p)), notes.note_of(p) is not None] for p in ps]))")
        self.assertEqual(got, [[want, want] for want in cases.values()])
        table = {"folders": ["inbox", "transcripts", "documents"], "outside_vault": True, "notes_exempt": True}
        got = self.py("import reach\n"
                      f"t = {table!r}\n"
                      f"ps = {list(cases)!r}\n"
                      "print(json.dumps([reach.read_reason(p, t) for p in ps]))")
        self.assertEqual(got, [None, None, "read a project document", "read a project document", "read a project document",
                               "read a project document", "read a project document", "read a transcript"])
        self.assertEqual(self.kind(notes / "Kickoff.md", "change"), ["ordinary", ""])
        self.assertEqual(self.kind(notes / "Kickoff.md", "change", marked=True)[0], "sensitive")

    def test_the_rest_of_the_home_folder_is_outside_the_projects(self):
        self.assertEqual(self.kind(self.home / "Documents/x.md", "create"), ["sensitive", "it is outside the vault and the projects folder"])


if __name__ == "__main__":
    unittest.main()
