"""#252: the archive folder is called 99 Archive (from _Archive and zz Archive; Alan, 20-10-2026).

Run: python3 dev/tests/test_archive_folder_99.py     (quick tier: no Chrome)

What is covered:
- the names: paths.ARCHIVE is 99 Archive, the old names are _Archive and zz Archive, and the defaults say 99 Archive;
- for one release all three names are never listed, indexed, read or written, and ask creaite can't touch any of them; the deny
  patterns name 99 Archive and _Archive (never zz Archive, as BL-09 agreed);
- the name in use at a place (paths.archive_name): 99 Archive, unless only the old _Archive is there, so a vault that hasn't been
  renamed keeps one archive folder per place and the rename never has to merge two;
- stored paths never change: an archived project, an archived report and a deleted note resolve under each of the three names,
  and after Health's rename a path recorded under _Archive resolves into the 99 Archive beside it (never the folder itself);
- the moves: a project archive, the 12-month reports move and Delete note go into 99 Archive in a new engagement and into the old
  _Archive where that is the folder in use; a new project made from a skeleton that still says _Archive gets 99 Archive;
- Health: doctor names the folders still called _Archive or zz Archive, Health's fix is "Rename to 99 Archive" on the approval
  card (propose.py old-archives), the portfolio's archive is included, and two old folders in one place are never merged;
- the update renames the saved never_index value only (no folder moves at update time).
GuardedMoves needs the guarded diffs in dev/proposals/archive-folder-99/ (reach.py's archive_move_problem, live_server.py's
existing_project_folder); the other classes need only the ordinary code. Everything is fictional and temporary.
"""
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_onedrive_projects import OneDriveCase, touch  # noqa: E402
from test_tracker import Vault  # noqa: E402

NEW, LEGACY, ZZ = "99 Archive", "_Archive", "zz Archive"
REPO = Path(__file__).resolve().parents[2]
NOTE = "---\ntitle: Sandbox plan\n---\nThe wombat sandbox.\n"


class Case(OneDriveCase):
    """The OneDrive-style vault, with helpers. Its engagements start as today's do: each holding an _Archive (the old name)."""

    def staged_apply(self, spec, name="spec.json"):
        f = self.v.root / "system/staging/drafts" / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(spec), encoding="utf-8")
        self.v.run("stage", str(f), script="propose.py")
        self.v.run("apply")

    def fresh(self, code):
        """Make engagement `code` as a new vault has it: no archive folder yet."""
        shutil.rmtree(self.eng(code, LEGACY))

    def doctor(self):
        r = self.v.run("--read-only", "--json", script="doctor.py", ok=False)
        return {c["id"]: c for c in json.loads(r.stdout.strip().splitlines()[-1])["checks"]}


class Names(Case):
    def test_the_constants_and_the_defaults_say_99_archive(self):
        o = self.py("import paths; print(json.dumps([paths.ARCHIVE, list(paths.OLD_ARCHIVES), list(paths.ARCHIVE_NAMES), "
                    "paths.LOCATION_DEFAULTS['never_index']]))")
        self.assertEqual(o, [NEW, [LEGACY, ZZ], [NEW, LEGACY, ZZ], [NEW, "_Templates", "99 System"]])
        defaults = json.loads((REPO / "system/templates/settings-defaults.json").read_text(encoding="utf-8"))
        self.assertEqual(defaults["locations"]["never_index"], [NEW, "_Templates", "99 System"])

    def test_all_three_names_are_skipped_and_never_for_ask_creaite(self):
        for name in (NEW, LEGACY, ZZ):
            f = touch(self.eng("ABC", name, "Old plan.docx"))
            for op in ("read", "create", "change", "move", "delete"):
                with self.subTest(name=name, op=op):
                    self.assertEqual(self.py(f"import reach; print(json.dumps(reach.classify({str(f)!r}, {op!r})))")[0], "never")
        touch(self.eng("ABC", "03 Delivery", "Design", "Plan.docx"))
        o = self.py("import paths, tracker; print(json.dumps([[str(f) for f in paths.document_files('ABC')], "
                    "[str(f) for f, _, _ in tracker.index_files()], paths.skipped_names(), paths.never_index_patterns()]))")
        for listed in o[:2]:
            self.assertTrue(any(s.endswith("Plan.docx") and "Design" in s for s in listed))
            self.assertFalse(any(f"/{n}/" in s for s in listed for n in (NEW, LEGACY, ZZ)), listed)
        self.assertTrue({NEW, LEGACY, ZZ} <= set(o[2]))
        self.assertIn(f"**/{NEW}/**", o[3])
        self.assertIn(f"**/{LEGACY}/**", o[3])                   # the old name stays on the deny lists while vaults hold one
        self.assertFalse(any(ZZ in g for g in o[3]), o[3])       # never zz Archive (BL-09, Alan 14-10-2026)

    def test_the_name_in_use_at_each_place(self):
        self.fresh("ABC")
        touch(self.eng("DEF", ZZ, "z.md"))
        q = "import paths; print(json.dumps([paths.archive_name(paths.projects_root() / n) for n in {names!r}] + [paths.archive_dir().name]))"
        names = ["Example Programme", "Digital Enablement"]
        self.assertEqual(self.py(q.format(names=names)), [NEW, LEGACY, NEW])     # new: 99 Archive; old: the _Archive it has
        (self.eng("DEF", NEW)).mkdir()
        (self.root / LEGACY).mkdir()
        self.assertEqual(self.py(q.format(names=names)), [NEW, NEW, LEGACY])     # both there: 99 Archive; root: its _Archive
        shutil.rmtree(self.eng("DEF", LEGACY))
        shutil.rmtree(self.eng("DEF", NEW))
        self.assertEqual(self.py(q.format(names=names))[1], NEW)                 # only zz Archive: never a destination


class StoredPaths(Case):
    def test_an_archived_project_resolves_under_each_name(self):
        stored = "projects/Digital Enablement/02 Meetings/Minutes/2026-10-01 Steering.docx"
        touch(self.eng("DEF", "02 Meetings", "Minutes", "2026-10-01 Steering.docx"))
        for name in (NEW, LEGACY, ZZ):
            with self.subTest(name=name):
                (self.root / name).mkdir()
                self.eng("DEF").rename(self.root / name / "Digital Enablement")
                got = self.py(f"import paths; print(json.dumps(str(paths.resolve({stored!r}))))")
                self.assertEqual(got, str(self.root / name / "Digital Enablement/02 Meetings/Minutes/2026-10-01 Steering.docx"))
                (self.root / name / "Digital Enablement").rename(self.eng("DEF"))
                (self.root / name).rmdir()

    def test_an_archived_report_resolves_under_each_name(self):
        stored = "projects/Example Programme/02 Meetings/Minutes/2025-01-01 Steering.docx"
        for name in (NEW, LEGACY, ZZ):
            with self.subTest(name=name):
                f = touch(self.eng("ABC", name, "02 Meetings", "Minutes", "2025-01-01 Steering.docx"))
                self.assertEqual(self.py(f"import paths; print(json.dumps(str(paths.resolve({stored!r}))))"), str(f))
                f.unlink()

    def test_after_the_rename_old_stored_paths_resolve_into_99_archive(self):
        note = touch(self.eng("ABC", LEGACY, "08 Notes", "Sandbox plan.md"), NOTE)
        touch(self.root / LEGACY / "Old Engagement" / "CLAUDE.md")
        self.eng("ABC", LEGACY).rename(self.eng("ABC", NEW))
        (self.root / LEGACY).rename(self.root / NEW)
        stored = "projects/Example Programme/_Archive/08 Notes/Sandbox plan.md"
        o = self.py(f"import paths; print(json.dumps([str(paths.resolve({stored!r})), str(paths.resolve({stored!r}, archived=False)), "
                    "str(paths.resolve('projects/_Archive/Old Engagement', archived=False)), "
                    "str(paths.resolve('projects/Example Programme/_Archive', archived=False))]))")
        self.assertEqual(o[0], str(self.eng("ABC", NEW, "08 Notes", "Sandbox plan.md")))
        self.assertEqual(o[1], o[0])
        self.assertEqual(o[2], str(self.root / NEW / "Old Engagement"))
        self.assertEqual(o[3], str(self.eng("ABC", LEGACY)))         # the folder itself is never mapped (undo names it)
        self.assertFalse(note.exists())


class Moves(Case):
    def test_delete_note_and_the_reports_move_go_to_the_folder_in_use(self):
        self.fresh("ABC")
        for code in ("ABC", "DEF"):
            touch(self.eng(code, "08 Notes", "Sandbox plan.md"), NOTE)
            touch(self.eng(code, "02 Meetings", "Minutes", "2024-01-01 Steering.docx"))
        o = self.py("import archive, datetime; print(json.dumps([[archive.note_delete_spec(p)[0]['file_changes']['file_ops'][0]['to'] "
                    "for p in ('projects/Example Programme/08 Notes/Sandbox plan.md', 'projects/Digital Enablement/08 Notes/Sandbox plan.md')], "
                    "sorted(r['to'] for r in archive.due_reports(on=datetime.date(2026, 10, 20)))]))")
        self.assertEqual(o[0], ["projects/Example Programme/99 Archive/08 Notes/Sandbox plan.md",
                                "projects/Digital Enablement/_Archive/08 Notes/Sandbox plan.md"])
        self.assertEqual(o[1], ["projects/Digital Enablement/_Archive/02 Meetings/Minutes/2024-01-01 Steering.docx",
                                "projects/Example Programme/99 Archive/02 Meetings/Minutes/2024-01-01 Steering.docx"])

    def test_a_project_archive_goes_into_99_archive_or_the_old_one_in_use(self):
        spec = json.loads(self.v.run("archive", "ABC", "--cancel-open", script="propose.py").stdout)
        self.assertEqual(spec["file_changes"]["file_ops"][0]["to"], "projects/99 Archive/Example Programme")
        (self.root / LEGACY).mkdir()
        spec = json.loads(self.v.run("archive", "ABC", "--cancel-open", script="propose.py").stdout)
        self.assertEqual(spec["file_changes"]["file_ops"][0]["to"], "projects/_Archive/Example Programme")

    def test_a_skeleton_that_still_says_archive_makes_99_archive(self):
        c = self.doctor()["skeleton_archive"]
        self.assertEqual(c["status"], "warn")
        self.assertIn("_Templates/_Skeleton still holds _Archive", c["detail"])
        self.assertIn("rename it to 99 Archive", c["detail"])
        spec = json.loads(self.v.run("new-project", "--code", "GHI", "--name", "Growth Hub", script="propose.py").stdout)
        made = [o.get("path") or o.get("to") for o in spec["file_changes"]["file_ops"]]
        self.assertIn("projects/Growth Hub/99 Archive", made)
        self.assertFalse(any(LEGACY in p or ZZ in p for p in made), made)
        (self.root / "_Templates/_Skeleton" / LEGACY).rename(self.root / "_Templates/_Skeleton" / NEW)
        self.assertEqual(self.doctor()["skeleton_archive"]["status"], "pass")


class Health(Case):
    def test_health_names_the_old_folders_and_offers_the_rename_on_the_card(self):
        touch(self.root / "_Portfolio" / LEGACY / "08 Notes" / "p.md")
        c = self.doctor()["old_archive_folders"]
        self.assertEqual(c["status"], "warn")
        self.assertIn("still called _Archive", c["detail"])
        self.assertIn("projects/Example Programme/_Archive", c["detail"])
        h = self.py(f"import health; print(json.dumps(health.health({{'checks': [{json.dumps(c)}]}})['problems'][0]))")
        self.assertEqual(h["title"], "Archive folders not yet called 99 Archive")
        self.assertEqual((h["fix"]["id"], h["fix"]["built"]), ("old_archive", True))
        self.assertEqual(h["fix"]["command"], "system/scripts/run propose.py old-archives")
        o = self.py("import health_fixes; print(json.dumps([health_fixes.FIXES['old_archive']['button'], "
                    "health_fixes.FIXES['old_archive'].get('card')]))")
        self.assertEqual(o, ["Rename to 99 Archive", True])                     # on the approval card: never silent
        spec = json.loads(self.v.run("old-archives", script="propose.py").stdout)
        self.assertEqual(spec["file_changes"]["archive"], "rename")
        self.assertEqual(spec["file_changes"]["title"], "Rename 3 archive folders to 99 Archive")
        self.assertEqual(sorted((o["from"], o["to"]) for o in spec["file_changes"]["file_ops"]), [
            ("projects/Digital Enablement/_Archive", "projects/Digital Enablement/99 Archive"),
            ("projects/Example Programme/_Archive", "projects/Example Programme/99 Archive"),
            ("projects/_portfolio/_Archive", "projects/_portfolio/99 Archive")])

    def test_two_old_folders_in_one_place_are_never_merged(self):
        touch(self.eng("ABC", ZZ, "z.md"))
        touch(self.eng("DEF", NEW, "n.md"))
        r = self.v.run("old-archives", script="propose.py")
        ops = [(o["from"], o["to"]) for o in json.loads(r.stdout)["file_changes"]["file_ops"]]
        self.assertEqual(ops, [("projects/Example Programme/_Archive", "projects/Example Programme/99 Archive")])
        self.assertIn("Left as it is: projects/Example Programme/zz Archive", r.stderr)
        self.assertIn("Left as it is: projects/Digital Enablement/_Archive", r.stderr)

    def test_no_old_folders_nothing_to_rename(self):
        for code in ("ABC", "DEF"):
            self.eng(code, LEGACY).rename(self.eng(code, NEW))
        r = self.v.run("old-archives", script="propose.py", ok=False)
        self.assertEqual((r.returncode, r.stdout.strip()), (1, ""))
        self.assertEqual(self.doctor()["old_archive_folders"]["status"], "pass")


class Update(unittest.TestCase):
    def test_the_update_renames_the_saved_value_only(self):
        src = f"import sys, json; sys.path.insert(0, {str(REPO / 'system/scripts')!r}); import update\n" \
              "s = {'locations': {'never_index': ['_Archive', '_Templates', 'zz Archive', 'Private', '99 System']}}\n" \
              "a = update.rename_archive_folder(s); b = update.rename_archive_folder(s)\n" \
              "print(json.dumps([a, b, s['locations']['never_index'], update.migration_note()]))"
        r = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        a, b, saved, note = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual((a, b), (["locations.never_index"], []))
        self.assertEqual(saved, [NEW, "_Templates", "Private", "99 System"])
        self.assertIn("No folder is renamed", note)


class GuardedMoves(Case):
    """Needs reach.py's diff (archive_move_problem knows 99 Archive and the old names)."""

    def why(self, a, b, kind):
        return self.py(f"import reach; print(json.dumps(reach.archive_move_problem({a!r}, {b!r}, {kind!r})))")

    def test_the_shapes(self):
        self.fresh("ABC")
        touch(self.eng("ABC", "02 Meetings", "Minutes", "2024-01-01 Steering.docx"))
        touch(self.eng("ABC", "08 Notes", "Sandbox plan.md"), NOTE)
        touch(self.eng("DEF", "02 Meetings", "Minutes", "2024-01-01 Steering.docx"))
        touch(self.eng("DEF", LEGACY, "02 Meetings", "Minutes", "2023-01-01 Steering.docx"))
        touch(self.root / "_Portfolio" / LEGACY / "x.md")
        e, d = "projects/Example Programme", "projects/Digital Enablement"
        cases = {
            (e, "projects/99 Archive/Example Programme", "archive"): True,           # no root archive yet: 99 Archive
            (e, "projects/_Archive/Example Programme", "archive"): False,            # never a new _Archive
            (f"{d}/_Archive", f"{d}/99 Archive", "rename"): True,
            (f"{d}/_Archive", f"{d}/_Archive2", "rename"): False,
            ("projects/_portfolio/_Archive", "projects/_portfolio/99 Archive", "rename"): True,   # the portfolio's too
            (f"{e}/02 Meetings/Minutes/2024-01-01 Steering.docx",
             f"{e}/99 Archive/02 Meetings/Minutes/2024-01-01 Steering.docx", "reports"): True,
            (f"{e}/02 Meetings/Minutes/2024-01-01 Steering.docx",
             f"{e}/_Archive/02 Meetings/Minutes/2024-01-01 Steering.docx", "reports"): False,     # not the folder in use
            (f"{d}/02 Meetings/Minutes/2024-01-01 Steering.docx",
             f"{d}/_Archive/02 Meetings/Minutes/2024-01-01 Steering.docx", "reports"): True,      # the old one, in use
            (f"{d}/_Archive/02 Meetings/Minutes/2023-01-01 Steering.docx",
             f"{d}/02 Meetings/Minutes/2023-01-01 Steering.docx", "reports_back"): True,
            (f"{e}/08 Notes/Sandbox plan.md", f"{e}/99 Archive/08 Notes/Sandbox plan.md", "notes"): True,
        }
        for (a, b, kind), ok in cases.items():
            with self.subTest(a=a, b=b, kind=kind):
                why = self.why(a, b, kind)
                self.assertEqual(why is None, ok, why)
        for name in (NEW, LEGACY, ZZ):                                               # restore from any of the three
            with self.subTest(restore=name):
                touch(self.root / name / "Old Engagement" / "CLAUDE.md")
                self.assertIsNone(self.why(f"projects/{name}/Old Engagement", "projects/Old Engagement", "restore"))
                shutil.rmtree(self.root / name)

    def test_the_rename_applies_and_undoes_and_links_keep_working(self):
        touch(self.eng("ABC", LEGACY, "02 Meetings", "Minutes", "2024-01-01 Steering.docx"), "minutes")
        touch(self.eng("DEF", ZZ, "z.md"), "z")
        spec = json.loads(self.v.run("old-archives", script="propose.py").stdout)
        self.staged_apply(spec)
        self.assertFalse(self.eng("ABC", LEGACY).exists())
        self.assertEqual(self.eng("ABC", NEW, "02 Meetings", "Minutes", "2024-01-01 Steering.docx").read_text(), "minutes")
        self.assertTrue(self.eng("DEF", ZZ).is_dir())                                # the _Archive beside it was renamed first
        stored = "projects/Example Programme/02 Meetings/Minutes/2024-01-01 Steering.docx"
        self.assertEqual(self.py(f"import paths; print(json.dumps(str(paths.resolve({stored!r}))))"),
                         str(self.eng("ABC", NEW, "02 Meetings", "Minutes", "2024-01-01 Steering.docx")))
        self.v.run("undo")
        self.assertEqual(self.eng("ABC", LEGACY, "02 Meetings", "Minutes", "2024-01-01 Steering.docx").read_text(), "minutes")
        self.assertFalse(self.eng("ABC", NEW).exists())

    def test_archive_and_restore_a_project_through_99_archive(self):
        self.staged_apply(json.loads(self.v.run("archive", "ABC", "--cancel-open", script="propose.py").stdout), "a.json")
        self.assertTrue((self.root / NEW / "Example Programme" / "02 Meetings").is_dir())
        self.assertFalse(self.eng("ABC").exists())
        self.staged_apply(json.loads(self.v.run("restore", "ABC", script="propose.py").stdout), "r.json")
        self.assertTrue(self.eng("ABC", "02 Meetings").is_dir())

    def test_a_restore_after_the_root_rename(self):
        (self.root / LEGACY).mkdir()                                                 # a vault archiving into _Archive
        self.staged_apply(json.loads(self.v.run("archive", "ABC", "--cancel-open", script="propose.py").stdout), "a.json")
        self.assertTrue((self.root / LEGACY / "Example Programme").is_dir())
        (self.root / LEGACY).rename(self.root / NEW)                                 # as Health's rename leaves it
        self.staged_apply(json.loads(self.v.run("restore", "ABC", script="propose.py").stdout), "r.json")
        self.assertTrue(self.eng("ABC", "02 Meetings").is_dir())

    def test_the_12_month_reports_move_into_99_archive(self):
        self.fresh("ABC")
        touch(self.eng("ABC", "02 Meetings", "Minutes", "2024-01-01 Steering.docx"), "old")
        r = subprocess.run([sys.executable, str(self.v.root / "system/scripts/archive.py"), "reports"], capture_output=True,
                           text=True, cwd=self.v.root, env={**__import__("os").environ, "CREAITE_NOW": "2026-10-20 09:00"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.staged_apply(json.loads(r.stdout))
        self.assertEqual(self.eng("ABC", NEW, "02 Meetings", "Minutes", "2024-01-01 Steering.docx").read_text(), "old")


class VaultLayout(unittest.TestCase):
    """The projects in the vault: projects/99 Archive is never a project folder."""

    def setUp(self):
        self.v = Vault()
        self.v.run("init")

    def tearDown(self):
        self.v.cleanup()

    def py(self, code):
        src = f"import sys, json; sys.path.insert(0, {str(self.v.root / 'system/scripts')!r})\n{code}"
        r = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True, cwd=self.v.root)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def test_99_archive_is_never_a_project(self):
        for name in (NEW, LEGACY, ZZ):
            touch(self.v.root / "projects" / name / "OLD Old Project" / "minutes" / "m.md")
        self.assertEqual(self.py("import paths; print(json.dumps([c for c, _ in paths.project_folders()]))"), ["ABC", "_portfolio"])

    def test_live_server_never_takes_99_archive_for_a_project(self):          # GuardedMoves' companion: live_server.py's diff
        (self.v.root / "projects" / NEW).mkdir()
        cfg = self.v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text(encoding="utf-8"))
        data["locations"] = {"projects_root": "", "never_index": ["_Templates"]}      # a list emptied by hand: still skipped
        cfg.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self.assertFalse(self.py("import live_server; print(json.dumps(live_server.existing_project_folder('99 Archive')))"))


if __name__ == "__main__":
    unittest.main()
