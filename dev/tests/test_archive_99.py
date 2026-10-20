"""#252: the archive folder is called "99 Archive"; _Archive and zz Archive are still read for one release (Alan, 20-10-2026).

Run: python3 dev/tests/test_archive_99.py     (quick tier: no Chrome)

Two parts.
ORDINARY (always run): paths.py, archive.py, propose.py, locations.py, update.py and Health, with the projects in a fake OneDrive:
- resolve maps a stored path into an archived project's or an engagement's own archive folder under all three names, and stored
  paths never change; when two archive folders hold things, both are read, 99 Archive first;
- a folder called 99 Archivement, "99 Archive " (a trailing space) or 99 archive (case: macOS) is judged by its whole name, as
  macOS judges it: the first two are not the archive, the third is;
- a new archive move (archive project, the monthly reports move, Delete note) goes to 99 Archive only, and a project name taken in
  an old archive folder is numbered, never shared;
- no migration: nothing is renamed, and Health says nothing about old names.
GUARDED (run only with dev/proposals/archive-99/guarded.diff applied: reach.ARCHIVE99): the move rules in reach.py and tracker.py
accept the old names as the source of a restore or a move back, never as the destination of a new move; the rename kind is gone; a
whole-name comparison; and a project archived by an earlier release (in _Archive) can be restored. With the diff missing these skip
(ARCHIVE99_UNPATCHED=1 says so on purpose); apply the diff to a scratch copy to run them.
Everything is fictional and temporary.
"""
import json
import os
import sqlite3
import sys
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_onedrive_projects import OneDriveCase, touch  # noqa: E402
from test_tracker import Vault  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
NEW, OLDS = "99 Archive", ("_Archive", "zz Archive")
ALL = (NEW, *OLDS)
PATCHED = "ARCHIVE99" in (REPO / "system/scripts/reach.py").read_text(encoding="utf-8")
needs_diff = unittest.skipUnless(PATCHED and os.environ.get("ARCHIVE99_UNPATCHED") != "1",
                                 "the guarded diff (dev/proposals/archive-99/guarded.diff) is not applied")
STORED_MIN = "projects/Digital Enablement/02 Meetings/Minutes/2026-10-01 Steering.docx"


class Names(OneDriveCase):
    """The names, as paths.py judges them."""

    def test_the_constants(self):
        o = self.py("import paths; print(json.dumps([paths.ARCHIVE, list(paths.OLD_ARCHIVES), list(paths.archive_names()), "
                    "paths.locations()['never_index'], paths.LOCATION_DEFAULTS['never_index']]))")
        self.assertEqual(o[0], "99 Archive")
        self.assertEqual(o[1], ["_Archive", "zz Archive"])
        self.assertEqual(o[2], ["99 Archive", "_Archive", "zz Archive"])
        self.assertEqual(o[4], ["99 Archive", "_Archive", "zz Archive", "_Templates", "99 System"])

    def test_whole_names_only_and_case_as_macos_has_it(self):
        o = self.py("import paths; names = ['99 Archive', '_Archive', 'zz Archive', '99 archive', '_ARCHIVE', 'ZZ archive', "
                    "'99 Archivement', '99 Archive ', ' 99 Archive', '99  Archive', 'Archive', '99 Archive.old', '999 Archive']\n"
                    "print(json.dumps({n: [paths.is_archive_name(n), paths.is_skipped(n)] for n in names}))")
        for n in ("99 Archive", "_Archive", "zz Archive", "99 archive", "_ARCHIVE", "ZZ archive"):
            self.assertEqual(o[n], [True, True], n)
        for n in ("99 Archivement", "99 Archive ", " 99 Archive", "99  Archive", "Archive", "99 Archive.old", "999 Archive"):
            self.assertEqual(o[n], [False, False], n)                   # a look-alike is an ordinary folder

    def test_a_look_alike_folder_is_an_engagement_and_is_not_mapped(self):
        for n in ("99 Archivement", "99 Archive "):
            with self.subTest(name=n):
                touch(self.root / n / "02 Meetings" / "Minutes" / "x.docx")
                got = self.py("import locations, paths\n"
                              "print(json.dumps([locations.engagements(paths.projects_root()), "
                              f"str(paths.archived_path(paths.projects_root() / {n!r} / 'a.docx'))]))")
                self.assertIn(n, got[0])
                self.assertEqual(got[1], str(self.root / n / "a.docx"))

    def test_an_upper_or_lower_case_archive_is_the_archive(self):
        touch(self.root / "99 archive" / "Old Engagement" / "02 Meetings" / "Minutes" / "x.docx")
        o = self.py("import locations, paths; print(json.dumps([locations.engagements(paths.projects_root()), "
                    "[c for c, _ in paths.project_folders()]]))")
        self.assertFalse({"99 archive", "99 Archive"} & set(o[0]), o)


class Resolve(OneDriveCase):
    """Stored paths never change; an archived project or file opens from whichever archive folder holds it."""

    def move_project(self, into):
        (self.root / into).mkdir(exist_ok=True)
        self.eng("DEF").rename(self.root / into / "Digital Enablement")

    def test_an_archived_project_resolves_under_each_name(self):
        for name in ALL:
            with self.subTest(name=name):
                f = touch(self.eng("DEF", "02 Meetings", "Minutes", "2026-10-01 Steering.docx"))
                self.move_project(name)
                o = self.py(f"import paths; print(json.dumps([str(paths.resolve({STORED_MIN!r})), str(paths.resolve({STORED_MIN!r}, archived=False)), "
                            f"paths.rel(paths.resolve({STORED_MIN!r}))]))")
                self.assertEqual(o[0], str(self.root / name / "Digital Enablement" / "02 Meetings/Minutes/2026-10-01 Steering.docx"))
                self.assertEqual(o[1], str(f))                         # the stored path itself is never rewritten
                self.assertEqual(o[2], f"projects/{name}/Digital Enablement/02 Meetings/Minutes/2026-10-01 Steering.docx")
                (self.root / name / "Digital Enablement").rename(self.eng("DEF"))
                (self.root / name).rmdir()

    def test_an_engagements_own_archive_resolves_a_moved_report_under_each_name(self):
        stored = "projects/Example Programme/04 Reporting/Weekly/2025-01-10 Weekly.docx"
        for name in ALL:
            with self.subTest(name=name):
                f = touch(self.eng("ABC", name, "04 Reporting", "Weekly", "2025-01-10 Weekly.docx"))
                got = self.py(f"import paths; print(json.dumps(str(paths.resolve({stored!r}))))")
                self.assertEqual(got, str(f))
                f.unlink()

    def test_a_deleted_note_in_any_archive_is_not_mapped(self):
        stored = "projects/Example Programme/08 Notes/Plan.md"
        for name in ALL:
            with self.subTest(name=name):
                f = touch(self.eng("ABC", name, "08 Notes", "Plan.md"))
                got = self.py(f"import paths; print(json.dumps(str(paths.resolve({stored!r}))))")
                self.assertEqual(got, str(self.eng("ABC", "08 Notes", "Plan.md")))   # #124: reached only by Move back
                f.unlink()

    def test_with_two_archive_folders_both_are_read_and_99_archive_wins(self):
        touch(self.root / NEW / "Alpha" / "02 Meetings" / "Minutes" / "a.docx", "new alpha")
        touch(self.root / "_Archive" / "Beta" / "02 Meetings" / "Minutes" / "b.docx", "old beta")
        touch(self.root / "_Archive" / "Alpha" / "02 Meetings" / "Minutes" / "a.docx", "old alpha")
        touch(self.root / "zz Archive" / "Gamma" / "02 Meetings" / "Minutes" / "c.docx", "older gamma")
        for stored, want in (("projects/Alpha/02 Meetings/Minutes/a.docx", self.root / NEW / "Alpha"),
                             ("projects/Beta/02 Meetings/Minutes/b.docx", self.root / "_Archive" / "Beta"),
                             ("projects/Gamma/02 Meetings/Minutes/c.docx", self.root / "zz Archive" / "Gamma")):
            got = self.py(f"import paths; print(json.dumps(str(paths.resolve({stored!r}))))")
            self.assertTrue(got.startswith(str(want)), (stored, got))
        o = self.py("import paths; print(json.dumps([[str(d) for d in paths.archive_dirs(paths.projects_root())], "
                    "[str(d) for d in paths.archive_dirs(paths.projects_root() / 'Example Programme')]]))")
        self.assertEqual(o[0], [str(self.root / NEW), str(self.root / "_Archive"), str(self.root / "zz Archive")])
        self.assertEqual(o[1], [])

    def test_the_notes_places_include_every_archive_name(self):
        for name in ALL:
            touch(self.eng("ABC", name, "08 Notes", f"{name}.md"))
        got = self.py("import paths; print(json.dumps([str(p) for p in paths.notes_places(paths.projects_root(), '08 Notes')]))")
        for name in ALL:
            self.assertIn(str(self.eng("ABC", name, "08 Notes")), got)


class NewMovesGoToTheNewName(OneDriveCase):
    def test_a_project_archive_goes_to_99_archive_and_a_taken_name_is_numbered_across_all_three(self):
        o = self.py("import propose, paths\n"
                    "print(json.dumps([str(paths.archive_dir()), propose.free_folder([paths.archive_dir(), *paths.archive_dirs(paths.projects_root())], 'Example Programme')]))")
        self.assertEqual(o, [str(self.root / NEW), "Example Programme"])
        for name, want in ((NEW, "Example Programme 2"), ("_Archive", "Example Programme 2"), ("zz Archive", "Example Programme 2")):
            with self.subTest(name=name):
                (self.root / name / "Example Programme").mkdir(parents=True)
                got = self.py("import propose, paths\nprint(json.dumps(propose.free_folder([paths.archive_dir(), *paths.archive_dirs(paths.projects_root())], 'Example Programme')))")
                self.assertEqual(got, want)
                (self.root / name / "Example Programme").rmdir()
                if name != NEW:
                    (self.root / name).rmdir()

    def test_the_monthly_reports_move_goes_to_99_archive_and_leaves_a_file_already_in_an_old_one(self):
        touch(self.eng("ABC", "02 Meetings", "Minutes", "2024-01-05 Steering.docx"))
        touch(self.eng("ABC", "02 Meetings", "Minutes", "2024-02-05 Board.docx"))
        touch(self.eng("ABC", "_Archive", "02 Meetings", "Minutes", "2024-02-05 Board.docx"))     # already there, under the old name
        got = self.py("import archive; print(json.dumps([(d['from'], d['to']) for d in archive.due_reports('2026-10-20')]))")
        self.assertEqual(got, [["projects/Example Programme/02 Meetings/Minutes/2024-01-05 Steering.docx",
                                "projects/Example Programme/99 Archive/02 Meetings/Minutes/2024-01-05 Steering.docx"]])

    def test_delete_note_moves_into_99_archive(self):
        notes = touch(self.eng("ABC", "08 Notes", "Plan.md"), "---\ntitle: Plan\n---\nBody\n")
        spec = self.py("import archive; print(json.dumps(archive.note_delete_spec('projects/Example Programme/08 Notes/Plan.md')))")
        ops = spec[0]["file_changes"]["file_ops"]
        self.assertEqual(ops[0]["to"], "projects/Example Programme/99 Archive/08 Notes/Plan.md")
        self.assertTrue(notes.exists())

    def test_a_new_project_gets_99_archive_from_a_skeleton_with_either_old_name(self):
        sk = self.root / "_Templates" / "_Skeleton"
        for old in OLDS:
            (sk / NEW).rename(sk / old)
            spec = json.loads(self.v.run("new-project", "--code", "GHI", "--name", "Growth Hub", script="propose.py").stdout)
            made = [o.get("path") or o.get("to") for o in spec["file_changes"]["file_ops"]]
            self.assertIn("projects/Growth Hub/99 Archive", made, old)
            self.assertFalse(any(part in OLDS for p in made for part in p.split("/")), made)
            (sk / old).rename(sk / NEW)


class NoMigrationNoOffer(OneDriveCase):
    def test_old_folders_stay_as_they_are_and_nothing_mentions_them(self):
        touch(self.eng("ABC", "zz Archive", "a.md"), "a")
        touch(self.eng("DEF", "_Archive", "b.md"), "b")
        r = self.v.run("--read-only", "--json", script="doctor.py", ok=False)
        checks = {c["id"]: c for c in json.loads(r.stdout.strip().splitlines()[-1])["checks"]}
        self.assertFalse({"old_archive_folders", "skeleton_archive"} & set(checks))
        self.assertFalse(any("zz Archive" in c["detail"] or "_Archive" in c["detail"] for c in checks.values()), checks)
        self.assertEqual(self.py("import health_fixes; print(json.dumps('old_archive' in health_fixes.FIXES))"), False)
        self.assertEqual((self.eng("ABC", "zz Archive", "a.md")).read_text(), "a")
        self.assertEqual((self.eng("DEF", "_Archive", "b.md")).read_text(), "b")
        self.assertNotEqual(self.v.run("old-archives", script="propose.py", ok=False).returncode, 0)


# ── the guarded part ────────────────────────────────────────────────────────────────────────────────────────────────────

@needs_diff
class MoveRules(OneDriveCase):
    """reach.archive_move_problem and tracker.check_move with the guarded diff applied."""

    def problem(self, a, b, kind):
        return self.py(f"import reach; print(json.dumps(reach.archive_move_problem({a!r}, {b!r}, {kind!r})))")

    def test_a_restore_comes_from_any_of_the_three_names_and_an_archive_goes_only_to_the_new_one(self):
        for name in ALL:
            touch(self.root / name / "Old Engagement" / "y.md")
            self.assertIsNone(self.problem(f"projects/{name}/Old Engagement", "projects/Old Engagement", "restore"), name)
        for name in OLDS:
            self.assertIsNotNone(self.problem("projects/Example Programme", f"projects/{name}/Example Programme", "archive"), name)
        self.assertIsNone(self.problem("projects/Example Programme", "projects/99 Archive/Example Programme", "archive"))

    def test_look_alikes_are_not_the_archive(self):
        for name in ("99 Archivement", "99 Archive.old", "Archive"):
            touch(self.root / name / "Old Engagement" / "y.md")
            self.assertIsNotNone(self.problem(f"projects/{name}/Old Engagement", "projects/Old Engagement", "restore"), name)
            self.assertIsNotNone(self.problem("projects/Example Programme", f"projects/{name}/Example Programme", "archive"), name)

    def test_reports_go_into_the_new_name_and_come_back_from_any(self):
        f = "02 Meetings/Minutes/2024-01-05 Steering.docx"
        for name in ALL:
            touch(self.eng("ABC", name, f))
            a, b = f"projects/Example Programme/{f}", f"projects/Example Programme/{name}/{f}"
            self.assertIsNone(self.problem(b, a, "reports_back"), name)
            self.assertEqual(self.problem(a, b, "reports") is None, name == NEW, name)
            (self.eng("ABC", name, f)).unlink()

    def test_notes_go_into_the_new_name_and_come_back_from_any(self):
        f = "08 Notes/Plan.md"
        for name in ALL:
            touch(self.eng("ABC", name, f))
            a, b = f"projects/Example Programme/{f}", f"projects/Example Programme/{name}/{f}"
            self.assertIsNone(self.problem(b, a, "notes_back"), name)
            self.assertEqual(self.problem(a, b, "notes") is None, name == NEW, name)
            (self.eng("ABC", name, f)).unlink()

    def test_the_rename_kind_is_gone(self):
        touch(self.eng("ABC", "zz Archive", "x.md"))
        for new in ("99 Archive", "_Archive"):
            why = self.problem("projects/Example Programme/zz Archive", f"projects/Example Programme/{new}", "rename")
            self.assertIn("archive, a restore", why)
        p = self.v.propose("rename", [], file_changes={"title": "x", "file_changes_decision": "approved", "archive": "rename",
                                                        "file_ops": [{"op": "move", "from": "projects/Example Programme/zz Archive",
                                                                      "to": "projects/Example Programme/99 Archive"}]})
        r = self.v.run("apply", ok=False)
        self.assertNotEqual(r.returncode, 0)                    # tracker.py apply: no such kind of move any more
        self.assertIn("move:", r.stdout)
        self.assertTrue(self.eng("ABC", "zz Archive").is_dir())
        p.unlink()
        got = self.py("import reach; print(json.dumps(list(reach.ARCHIVE_MOVES)))")
        self.assertEqual(got, ["archive", "restore", "reports", "reports_back", "notes", "notes_back"])


@needs_diff
class RestoreFromAnOldArchive(unittest.TestCase):
    """A project archived by an earlier release sits in projects/_Archive and its history says so: restore still works, and the
    new archive goes to 99 Archive."""

    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        self.abc = next(d for d in (self.v.root / "projects").iterdir() if d.name.startswith("ABC "))
        self.name = self.abc.name
        touch(self.abc / "minutes" / "2026-10-01 Steering.md", "Steering.\n")

    def tearDown(self):
        self.v.cleanup()

    def stage_and_apply(self, *args):
        spec = self.v.run(*args, script="propose.py").stdout
        f = self.v.root / "system/staging/drafts/a.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(spec, encoding="utf-8")
        self.v.run("stage", str(f), script="propose.py")
        self.v.run("apply")

    def test_archive_goes_to_99_archive_then_an_old_name_restore_works_with_undo(self):
        self.stage_and_apply("archive", "ABC")
        self.assertTrue((self.v.root / "projects" / NEW / self.name).is_dir())
        for old in OLDS:                                       # as an earlier release left it
            (self.v.root / "projects" / NEW).rename(self.v.root / "projects" / old)
            with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
                con.execute("UPDATE change_log SET new_value = REPLACE(new_value, ?, ?) WHERE field = 'folder'", (NEW, old))
                con.commit()
            self.stage_and_apply("restore", "ABC")
            self.assertEqual((self.abc / "minutes" / "2026-10-01 Steering.md").read_text(), "Steering.\n", old)
            self.assertEqual(self.v.rows("projects")[0]["archived"], 0)
            self.v.run("undo")                                  # put it back into the old archive folder, exactly
            self.assertTrue((self.v.root / "projects" / old / self.name).is_dir(), old)
            self.assertFalse(self.abc.exists())
            (self.v.root / "projects" / old).rename(self.v.root / "projects" / NEW)
            with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
                con.execute("UPDATE change_log SET new_value = REPLACE(new_value, ?, ?) WHERE field = 'folder'", (old, NEW))
                con.commit()

    def test_the_live_server_does_not_treat_the_archive_as_a_project_folder(self):
        got = subprocess_json(self.v, "import live_server as L; print(json.dumps([L.existing_project_folder(n) for n in "
                                      "('99 Archive', '99 archive', '_Archive', 'zz Archive')]))")
        self.assertEqual(got, [False, False, False, False])


def subprocess_json(v, code):
    import subprocess
    src = f"import sys, json; sys.path.insert(0, {str(v.root / 'system/scripts')!r})\n{code}"
    r = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True, cwd=v.root)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout.strip().splitlines()[-1])


if __name__ == "__main__":
    unittest.main()
