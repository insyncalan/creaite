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
import shutil
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
        self.assertEqual(o[1], [str(self.eng('ABC', NEW))])          # the engagement's own (from the template)

    def test_the_notes_places_include_every_archive_name(self):
        for name in ALL:
            touch(self.eng("ABC", name, "08 Notes", f"{name}.md"))
        got = self.py("import paths; print(json.dumps([str(p) for p in paths.notes_places(paths.projects_root(), '08 Notes')]))")
        for name in ALL:
            self.assertIn(str(self.eng("ABC", name, "08 Notes")), got)


class AfterAHandRename(OneDriveCase):
    """From Stark's test_archive_folder_99 (merged): Alan renames the archive folders to 99 Archive himself; a path recorded under
    the old name opens the file in the renamed folder, for a deleted note, an archived project and the portfolio's archive."""

    def test_old_stored_paths_resolve_into_the_renamed_folder(self):
        shutil.rmtree(self.eng("ABC", NEW))
        note = touch(self.eng("ABC", NEW, "08 Notes", "Sandbox plan.md"), "---\ntitle: Sandbox plan\n---\nThe wombat sandbox.\n")
        touch(self.root / NEW / "Old Engagement" / "CLAUDE.md")
        touch(self.root / "_Portfolio" / NEW / "08 Notes" / "p.md")
        for old in OLDS:
            with self.subTest(old=old):
                q = [f"projects/Example Programme/{old}/08 Notes/Sandbox plan.md", f"projects/{old}/Old Engagement/CLAUDE.md",
                     f"projects/_portfolio/{old}/08 Notes/p.md"]
                got = self.py("import paths; print(json.dumps([[str(paths.resolve(p, archived=a)) for a in (True, False)] for p in %r]))" % (q,))
                self.assertEqual(got[0], [str(note)] * 2)
                self.assertEqual(got[1], [str(self.root / NEW / "Old Engagement" / "CLAUDE.md")] * 2)
                self.assertEqual(got[2], [str(self.root / "_Portfolio" / NEW / "08 Notes" / "p.md")] * 2)


class AlwaysTheNewName(OneDriveCase):
    """Alan's rule (via Jarvis, 20-10-2026): a new archive ALWAYS goes into 99 Archive, in every place, even where an old _Archive
    still exists; the old folders are read for one release and nothing is written into them."""

    def test_delete_note_and_the_reports_move_write_only_to_99_archive(self):
        for code in ("ABC", "DEF"):
            shutil.rmtree(self.eng(code, NEW))                                  # the template's own: the places start without one
            touch(self.eng(code, "08 Notes", "Plan.md"), "---\ntitle: Plan\n---\nBody\n")
            touch(self.eng(code, "02 Meetings", "Minutes", "2024-01-05 Steering.docx"))
        touch(self.eng("ABC", "_Archive", "08 Notes", "Other.md"))             # ABC still has the old _Archive, DEF has none
        touch(self.eng("DEF", "zz Archive", "z.md"))                           # DEF has a zz Archive
        got = self.py("import archive, datetime; print(json.dumps([[archive.note_delete_spec(p)[0]['file_changes']['file_ops'][0]['to'] "
                      "for p in ('projects/Example Programme/08 Notes/Plan.md', 'projects/Digital Enablement/08 Notes/Plan.md')], "
                      "sorted(r['to'] for r in archive.due_reports(on=datetime.date(2026, 10, 20)))]))")
        self.assertEqual(got[0], ["projects/Example Programme/99 Archive/08 Notes/Plan.md",
                                  "projects/Digital Enablement/99 Archive/08 Notes/Plan.md"])
        self.assertEqual(got[1], ["projects/Digital Enablement/99 Archive/02 Meetings/Minutes/2024-01-05 Steering.docx",
                                  "projects/Example Programme/99 Archive/02 Meetings/Minutes/2024-01-05 Steering.docx"])

    def test_a_project_archive_goes_to_99_archive_beside_an_old_folder(self):
        spec = lambda: json.loads(self.v.run("archive", "ABC", "--cancel-open", script="propose.py").stdout)["file_changes"]["file_ops"][0]["to"]  # noqa: E731
        for old in OLDS:
            (self.root / old).mkdir()
            self.assertEqual(spec(), "projects/99 Archive/Example Programme", old)
        touch(self.root / "_Archive" / "Example Programme" / "x.md")
        self.assertEqual(spec(), "projects/99 Archive/Example Programme 2")       # a name taken in the old folder is numbered
        (self.root / NEW).mkdir()
        self.assertEqual(spec(), "projects/99 Archive/Example Programme 2")       # both there: still 99 Archive

    def test_the_note_name_is_numbered_across_all_three_folders(self):
        """N1: with an old folder holding the same name the new note is numbered in 99 Archive, and the guard accepts it."""
        shutil.rmtree(self.eng("ABC", NEW))
        touch(self.eng("ABC", "08 Notes", "Plan.md"), "---\ntitle: Plan\n---\nBody\n")
        touch(self.eng("ABC", "_Archive", "08 Notes", "Plan.md"))
        touch(self.eng("ABC", "zz Archive", "08 Notes", "Plan-2.md"))
        op = self.py("import archive; print(json.dumps(archive.note_delete_spec('projects/Example Programme/08 Notes/Plan.md')[0]['file_changes']['file_ops'][0]))")
        self.assertEqual(op["to"], "projects/Example Programme/99 Archive/08 Notes/Plan-3.md")
        why = self.py(f"import reach; print(json.dumps(reach.archive_move_problem({op['from']!r}, {op['to']!r}, 'notes')))")
        self.assertIsNone(why)


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
        got = self.py("import archive; print(json.dumps([(d['from'], d['to']) for d in archive.due_reports(__import__('datetime').date(2026, 10, 20))]))")
        self.assertEqual(got, [["projects/Example Programme/02 Meetings/Minutes/2024-01-05 Steering.docx",
                                "projects/Example Programme/99 Archive/02 Meetings/Minutes/2024-01-05 Steering.docx"]])

    def test_delete_note_moves_into_99_archive(self):
        notes = touch(self.eng("ABC", "08 Notes", "Plan.md"), "---\ntitle: Plan\n---\nBody\n")
        spec = self.py("import archive; print(json.dumps(archive.note_delete_spec('projects/Example Programme/08 Notes/Plan.md')))")
        ops = spec[0]["file_changes"]["file_ops"]
        self.assertEqual(ops[0]["to"], "projects/Example Programme/99 Archive/08 Notes/Plan.md")
        self.assertTrue(notes.exists())

    def test_delete_note_numbers_its_name_across_all_three_archives(self):
        """N1: an old archive already holds a deleted note of that name: the new one is numbered in 99 Archive, never followed to the
        old file, and the shape check accepts it."""
        notes = touch(self.eng("ABC", "08 Notes", "Plan.md"), "---\ntitle: Plan\n---\nBody\n")
        stored = "projects/Example Programme/08 Notes/Plan.md"
        taken = []
        for name in (*OLDS, NEW):
            touch(self.eng("ABC", name, "08 Notes", "Plan.md" if not taken else f"Plan-{len(taken) + 1}.md"))
            taken.append(name)
            spec = self.py(f"import archive; print(json.dumps(archive.note_delete_spec({stored!r})))")[0]
            op = spec["file_changes"]["file_ops"][0]
            want = f"projects/Example Programme/99 Archive/08 Notes/Plan-{len(taken) + 1}.md"
            self.assertEqual(op["to"], want, name)
            why = self.py(f"import reach; print(json.dumps(reach.archive_move_problem({op['from']!r}, {op['to']!r}, 'notes')))")
            self.assertIsNone(why, (name, why))
        self.assertTrue(notes.exists())

    def test_the_reports_move_skips_a_name_taken_in_any_of_the_three(self):
        for i, name in enumerate(ALL):
            f = f"2024-0{i + 1}-05 Steering.docx"
            touch(self.eng("ABC", "02 Meetings", "Minutes", f))
            touch(self.eng("ABC", name, "02 Meetings", "Minutes", f))
        got = self.py("import archive; print(json.dumps([d['from'] for d in archive.due_reports(__import__('datetime').date(2026, 10, 20))]))")
        self.assertEqual(got, [])

    def test_a_new_project_gets_99_archive_from_a_skeleton_with_either_old_name(self):
        sk = self.root / "_Templates" / "_Skeleton"
        for old in (*OLDS, "_ARCHIVE", "zz archive", "99 archive"):         # exact names and lower or upper case (F3)
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
            (self.eng("ABC", name, f)).unlink()
            touch(self.eng("ABC", f))                              # forward: the original is there, the archive copy is not
            self.assertEqual(self.problem(a, b, "reports") is None, name == NEW, name)
            (self.eng("ABC", f)).unlink()

    def test_notes_go_into_the_new_name_and_come_back_from_any(self):
        f = "08 Notes/Plan.md"
        for name in ALL:
            touch(self.eng("ABC", name, f))
            a, b = f"projects/Example Programme/{f}", f"projects/Example Programme/{name}/{f}"
            self.assertIsNone(self.problem(b, a, "notes_back"), name)
            (self.eng("ABC", name, f)).unlink()
            touch(self.eng("ABC", f))                              # forward: the original is there, the archive copy is not
            self.assertEqual(self.problem(a, b, "notes") is None, name == NEW, name)
            (self.eng("ABC", f)).unlink()

    def test_a_place_that_still_has_an_old_folder_gets_new_items_in_99_archive(self):
        """The decision in the README: new archives go to 99 Archive always (this proposal); not to the old folder in use."""
        f = "02 Meetings/Minutes/2024-01-05 Steering.docx"
        for name in OLDS:
            touch(self.eng("ABC", f))
            touch(self.eng("ABC", name, "02 Meetings", "Minutes", "2023-01-05 Older.docx"))       # the place still has the old folder
            a = f"projects/Example Programme/{f}"
            self.assertIsNone(self.problem(a, f"projects/Example Programme/99 Archive/{f}", "reports"), name)
            self.assertIsNotNone(self.problem(a, f"projects/Example Programme/{name}/{f}", "reports"), name)
            self.eng("ABC", name, "02 Meetings", "Minutes", "2023-01-05 Older.docx").unlink()
            self.eng("ABC", f).unlink()

    def test_the_portfolio_has_the_same_shapes(self):
        f = "02 Meetings/Minutes/2024-01-05 Portfolio review.docx"
        touch(self.root / "_Portfolio" / f)
        a = f"projects/_portfolio/{f}"
        self.assertIsNone(self.problem(a, f"projects/_portfolio/99 Archive/{f}", "reports"))
        self.assertIsNotNone(self.problem(a, f"projects/_portfolio/_Archive/{f}", "reports"))
        (self.root / "_Portfolio" / f).unlink()
        touch(self.root / "_Portfolio" / "_Archive" / f)
        self.assertIsNone(self.problem(f"projects/_portfolio/_Archive/{f}", a, "reports_back"))

    def test_the_permission_refusal_names_the_folder_that_was_hit(self):
        for name in ALL + ("99 archive",):
            why = self.py("import permissions; print(json.dumps(permissions._path_rule_refused('Write', 'projects/Example Programme/%s/**')))" % name)
            self.assertIn(f"{name} is never read or written by creaite", why or "", name)
        self.assertIsNone(self.py("import permissions; print(json.dumps(permissions._path_rule_refused('Write', 'projects/Example Programme/99 Archivement/**')))"))

    def test_the_rename_kind_is_gone(self):
        touch(self.eng("ABC", "zz Archive", "x.md"))
        for new in ("99 Archive", "_Archive"):
            why = self.problem("projects/Example Programme/zz Archive", f"projects/Example Programme/{new}", "rename")
            self.assertIn("an archive or a restore", why)
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
        for n in ("99 Archive", "_Archive", "zz Archive"):
            (self.v.root / "projects" / n).mkdir(exist_ok=True)
        cfg = self.v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text(encoding="utf-8"))
        data["locations"] = {"projects_root": "", "never_index": ["_Templates"]}      # a list emptied by hand: still skipped
        cfg.write_text(json.dumps(data, indent=2), encoding="utf-8")
        got = subprocess_json(self.v, "import live_server as L; print(json.dumps([L.existing_project_folder(n) for n in "
                                      "('99 Archive', '99 archive', '_Archive', 'zz Archive')]))")
        self.assertEqual(got, [False, False, False, False])


# ── F1 (Opus review): Alan renames his archive folders by hand, and the apply records keep the old name ───────────────────

import test_archive_move_back as mb  # noqa: E402

PORT = f"projects/_portfolio/{mb.PORTFOLIO}"


def rewrite_records(root, old, new):
    """What an earlier release left behind: the apply records and the project's archive history name `old` where a later
    archive says `new`."""
    with closing(sqlite3.connect(root / "system/tracker.db")) as con:
        con.execute("UPDATE applies SET file_ops = REPLACE(file_ops, ?, ?)", (old, new))
        con.execute("UPDATE change_log SET new_value = REPLACE(new_value, ?, ?) WHERE field = 'folder'", (old, new))
        con.commit()


class HandRenamed(unittest.TestCase):
    """Files › Archived, Move back, Undo, a project Restore and tracker.check_move still find a file the archive moved when the
    archive folder was renamed by hand: old record + new folder, new record + old folder, and both folders there. Each with the
    old name `_Archive` and with `zz Archive`."""

    run_at, py, files, spec = mb.MoveBack.run_at, mb.MoveBack.py, mb.MoveBack.files, mb.MoveBack.spec
    stage_from_guard, apply_as_card = mb.MoveBack.stage_from_guard, mb.MoveBack.apply_as_card

    v = None

    def make(self):
        self.v = Vault()
        self.v.run("init")
        self.abc = mb.archive_old_files(self.v.root)
        self.base = f"projects/{self.abc.name}"
        self.pf = self.v.root / "projects/_portfolio"

    def tearDown(self):
        if self.v:
            self.v.cleanup()
            self.v = None

    def rename(self, how, old):
        """Put the vault in one of the three states. Returns whether a file is now in an OLD-named folder."""
        if how == "old_record_new_folder":
            rewrite_records(self.v.root, NEW, old)
            return False
        for base in (self.abc, self.pf):
            (base / NEW).rename(base / old)
        if how == "both":
            rewrite_records(self.v.root, NEW, old)
            (self.abc / NEW).mkdir()
        return True

    def each(self, test):
        for old in OLDS:
            for how in ("old_record_new_folder", "new_record_old_folder", "both"):
                with self.subTest(old=old, how=how):
                    self.make()
                    try:
                        in_old = self.rename(how, old)
                        if in_old and not PATCHED:
                            continue                   # a move out of an old name is the guarded diff's
                        test(old, in_old)
                    finally:
                        self.tearDown()

    def test_files_archived_lists_and_opens_every_file(self):
        def check(old, in_old):
            listed, archived = self.files()
            want = {f"{self.base}/{f}" for f in mb.DUE} | {PORT}
            self.assertEqual({a["path"] for a in archived}, want)
            for a in archived:
                self.assertTrue(Path(self.py(f"import paths; print(json.dumps(str(paths.resolve({a['at']!r}))))")).is_file(), a)
        self.each(check)

    def test_move_back_works(self):
        def check(old, in_old):
            stored = f"{self.base}/{mb.DUE[0]}"
            spec, why = self.spec(stored)
            self.assertIsNone(why)
            r = self.stage_from_guard(spec)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.apply_as_card(r)
            self.assertTrue((self.abc / mb.DUE[0]).is_file())
            self.assertEqual(self.spec(stored)[0], None)         # nothing left to move back
        self.each(check)

    def test_undo_of_the_archive_puts_every_file_back(self):
        def check(old, in_old):
            self.run_at("undo", script="tracker.py")
            for f in mb.DUE:
                self.assertTrue((self.abc / f).is_file(), f)
            self.assertTrue((self.pf / mb.PORTFOLIO).is_file())
        self.each(check)

    @needs_diff
    def test_check_move_compares_the_names_as_equals(self):
        def check(old, in_old):
            at = self.files()[1][0]["at"]
            original = next(a["path"] for a in self.files()[1] if a["at"] == at)
            recorded = at.replace(NEW, old) if NEW in at else at.replace(old, NEW)
            for src in (at, recorded):                    # the name the record has, or the one the folder has
                code = self.py("import tracker\n"
                               f"try:\n    tracker.check_move({{'from': {src!r}, 'to': {original!r}}}, {{'archive': 'reports_back'}})\n"
                               "    print(json.dumps('ok'))\n"
                               "except tracker.Invalid as e:\n    print(json.dumps(str(e)))")
                self.assertEqual(code, "ok", (src, code))
        self.each(check)


class FollowRules(unittest.TestCase):
    """Round 3 (Opus review): the record is cleared by a Move back whichever names it and the folder have (N2), a symlinked archive
    folder or a `..` is never followed (N3), 99 Archive wins over an old name, and a follow never leaves the engagement."""

    run_at, py, files, spec = mb.MoveBack.run_at, mb.MoveBack.py, mb.MoveBack.files, mb.MoveBack.spec
    stage_from_guard, apply_as_card = mb.MoveBack.stage_from_guard, mb.MoveBack.apply_as_card

    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        self.abc = mb.archive_old_files(self.v.root)
        self.base = f"projects/{self.abc.name}"
        self.pf = self.v.root / "projects/_portfolio"
        self.other = self.v.root / "projects" / "ZZZ Other"
        self.addCleanup(self.v.cleanup)

    def follow(self, stored):
        return self.py(f"import paths; print(json.dumps([paths.follow_stored({stored!r}), str(paths.resolve({stored!r}))]))")

    def check_move(self, src, dst, kind):
        return self.py("import tracker\n"
                       f"try:\n    tracker.check_move({{'from': {src!r}, 'to': {dst!r}}}, {{'archive': {kind!r}}})\n"
                       "    print(json.dumps('ok'))\n"
                       "except tracker.Invalid as e:\n    print(json.dumps(str(e)))")

    def test_a_move_back_clears_the_record_in_all_four_combinations(self):
        """N2: the record said one name, the folder had another, when the file was moved back; the archive record must be gone
        (a file Alan later puts under that name in the archive folder is not listed as archived)."""
        stored = f"{self.base}/{mb.DUE[0]}"
        for old in OLDS:
            for how in ("new_new", "old_record_new_folder", "new_record_old_folder", "both"):
                with self.subTest(old=old, how=how):
                    self.setUp()                                    # a fresh vault each time (cleaned up at the end)
                    folder = NEW
                    if how == "old_record_new_folder":
                        rewrite_records(self.v.root, NEW, old)
                    elif how in ("new_record_old_folder", "both"):
                        if not PATCHED:
                            continue
                        for b in (self.abc, self.pf):
                            (b / NEW).rename(b / old)
                        folder = old
                        if how == "both":
                            rewrite_records(self.v.root, NEW, old)
                            (self.abc / NEW).mkdir()
                    spec, why = self.spec(stored)
                    self.assertIsNone(why)
                    r = self.stage_from_guard(spec)
                    self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                    self.apply_as_card(r)
                    (self.abc / mb.DUE[0]).rename(self.abc / "minutes" / "elsewhere.md")
                    touch(self.abc / folder / mb.DUE[0], "a different file Alan put there\n")
                    ghost = [a["at"] for a in self.files()[1] if a["path"] == stored]
                    self.assertEqual(ghost, [])
                    self.assertIsNone(self.spec(stored)[0])

    def test_dotdot_is_never_followed(self):
        touch(self.other / "secret.md", "s\n")
        for tail in ("_Archive/../../ZZZ Other/secret.md", "_Archive/../_Archive/../../ZZZ Other/secret.md", "99 Archive/../../ZZZ Other/secret.md"):
            stored = f"{self.base}/{tail}"
            self.assertEqual(self.follow(stored)[0], stored)
            self.assertIsNone(self.spec(stored)[0])

    def test_a_follow_never_leaves_the_engagement(self):
        touch(self.other / NEW / "minutes" / "2025-09-30 Steering committee.md", "other engagement's\n")
        (self.abc / NEW).rename(self.abc / "moved away")
        got = self.follow(f"{self.base}/_Archive/minutes/2025-09-30 Steering committee.md")
        self.assertNotIn("ZZZ Other", got[1])
        self.assertEqual(got[0], f"{self.base}/_Archive/minutes/2025-09-30 Steering committee.md")

    def test_a_symlinked_archive_folder_is_not_followed_or_listed(self):
        touch(self.other / NEW / mb.DUE[0], "other engagement's minutes\n")
        rewrite_records(self.v.root, NEW, "_Archive")
        (self.abc / NEW).rename(self.abc / "moved-away")
        os.symlink(self.other / NEW, self.abc / NEW)
        stored = f"{self.base}/_Archive/{mb.DUE[0]}"
        self.assertEqual(self.follow(stored)[0], stored)                 # the symlink is skipped: nothing to follow to
        self.assertEqual([a["at"] for a in self.files()[1] if a["p"] == "ABC" and a["path"] == f"{self.base}/{mb.DUE[0]}"], [])
        self.assertIsNone(self.spec(f"{self.base}/{mb.DUE[0]}")[0])

    def test_99_archive_wins_when_two_archive_folders_hold_the_same_stored_path(self):
        rewrite_records(self.v.root, NEW, "zz Archive")                  # the record names a folder that is no longer there
        touch(self.abc / "_Archive" / mb.DUE[0], "the older copy\n")
        stored = f"{self.base}/zz Archive/{mb.DUE[0]}"
        self.assertEqual(self.follow(stored)[0], f"{self.base}/{NEW}/{mb.DUE[0]}")
        at = next(a["at"] for a in self.files()[1] if a["path"] == f"{self.base}/{mb.DUE[0]}")
        self.assertEqual(at, f"{self.base}/{NEW}/{mb.DUE[0]}")

    def test_both_present_the_recorded_name_wins_when_it_is_there(self):
        rewrite_records(self.v.root, NEW, "_Archive")
        (self.abc / NEW).rename(self.abc / "_Archive")
        touch(self.abc / NEW / mb.DUE[0], "a different file Alan put there\n")
        at = [a["at"] for a in self.files()[1] if a["path"] == f"{self.base}/{mb.DUE[0]}"]
        self.assertEqual(at, [f"{self.base}/_Archive/{mb.DUE[0]}"])

    @needs_diff
    def test_a_restore_whose_followed_form_is_no_archive_folder_is_refused(self):
        for src in (f"projects/zz Archive/{self.abc.name}", f"projects/_Archive/{self.abc.name}"):
            self.assertNotEqual(self.check_move(src, f"projects/{self.abc.name} 2", "restore"), "ok")


class HandRenamedProject(unittest.TestCase):
    """Restore project and Undo of the archive, with the project's archive folder renamed by hand after the archive."""

    def make(self):
        self.v = Vault()
        self.v.run("init")
        self.abc = next(d for d in (self.v.root / "projects").iterdir() if d.name.startswith("ABC "))
        touch(self.abc / "minutes" / "m.md", "m\n")
        self.stage_and_apply("archive", "ABC")

    def stage_and_apply(self, *args):
        spec = self.v.run(*args, script="propose.py").stdout
        f = self.v.root / "system/staging/drafts/a.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(spec, encoding="utf-8")
        self.v.run("stage", str(f), script="propose.py")
        self.v.run("apply")

    def scenes(self, test):
        proj = None
        for old in OLDS:
            for how in ("old_record_new_folder", "new_record_old_folder"):
                with self.subTest(old=old, how=how):
                    if how == "new_record_old_folder" and not PATCHED:
                        continue                           # a restore out of an old name is the guarded diff's
                    self.make()
                    try:
                        proj = self.v.root / "projects"
                        if how == "old_record_new_folder":
                            rewrite_records(self.v.root, NEW, old)
                        else:
                            (proj / NEW).rename(proj / old)
                        test()
                    finally:
                        self.v.cleanup()

    def test_restore_follows_the_folder_wherever_it_is_called(self):
        def check():
            self.stage_and_apply("restore", "ABC")
            self.assertEqual((self.abc / "minutes" / "m.md").read_text(), "m\n")
            self.assertEqual(self.v.rows("projects")[0]["archived"], 0)
        self.scenes(check)

    def test_undo_of_the_archive_follows_it_too(self):
        def check():
            self.v.run("undo")
            self.assertEqual((self.abc / "minutes" / "m.md").read_text(), "m\n")
            self.assertEqual(self.v.rows("projects")[0]["archived"], 0)
        self.scenes(check)


class OldNamesAreStillSkipped(OneDriveCase):
    """Test gap (Opus review): zz Archive and _Archive stay skipped for one release even when a saved never_index lacks them."""

    def test_a_saved_list_without_the_old_names_still_skips_them(self):
        cfg = self.v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text())
        data["locations"]["never_index"] = ["_Templates", "99 System"]            # as an older release saved it
        cfg.write_text(json.dumps(data))
        for name in ALL:
            touch(self.eng("ABC", name, f"{name} plan.docx"))
        touch(self.eng("ABC", "03 Delivery", "Design", "Plan.docx"))
        o = self.py("import paths, tracker, reach\n"
                    "print(json.dumps([paths.skipped_names(), [str(f) for f in paths.document_files('ABC')], "
                    "[str(f) for f, _, _ in tracker.index_files()], "
                    f"[reach.classify(str(paths.project_dir('ABC') / n / 'x.md'), 'read')[0] for n in {list(ALL)!r}], "
                    "[paths.project_path_problem(f'projects/Example Programme/{n}/x.md') for n in %r]]))" % (list(ALL),))
        for n in ALL:
            self.assertIn(n, o[0])
        for listed in (o[1], o[2]):
            self.assertTrue(any(s.endswith("Plan.docx") and "Design" in s for s in listed))
            self.assertFalse(any(f"/{n}/" in s for s in listed for n in ALL), listed)
        self.assertEqual(o[3], ["never", "never", "never"])
        self.assertTrue(all(o[4]), o[4])                                  # a project file under any of the three is refused


def subprocess_json(v, code):
    import subprocess
    src = f"import sys, json; sys.path.insert(0, {str(v.root / 'system/scripts')!r})\n{code}"
    r = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True, cwd=v.root)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout.strip().splitlines()[-1])


if __name__ == "__main__":
    unittest.main()
