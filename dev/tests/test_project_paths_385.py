"""#385 phase 1: a project's own folder (locations.project_paths), the core in paths.py and its checks on save.

Run: python3 dev/tests/test_project_paths_385.py

Everything here is fictional and temporary: a fake home folder, the OneDrive-style projects folder of test_onedrive_projects
(ABC in "Example Programme", DEF in "Digital Enablement"), and ABC moved to a folder of its own outside it
(~/Work/Acme/Programme: its last part is not the register's folder name, so the archive slot's name is checked too). DEF stays
in the projects folder. Never touches a real OneDrive.
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
from test_onedrive_projects import ENGAGEMENTS, OneDriveCase, touch  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
BASE_COMMIT = "a62fbb0a"           # origin/main when #385 started: paths.py as it was, for the unchanged-behaviour check
ABC, DEF = ENGAGEMENTS["ABC"], ENGAGEMENTS["DEF"]
OWN = "~/Work/Acme/Programme"
MIN = "02 Meetings/Minutes"

# What every probe prints: rel and resolve for a set of real files and stored paths, and the per-project helpers.
PROBE = r"""
import paths
real = json.loads(sys.argv[1]) if len(sys.argv) > 1 else []
stored = json.loads(sys.argv[2]) if len(sys.argv) > 2 else []
def rel(p):
    try:
        return paths.rel(__import__('pathlib').Path(p))
    except ValueError:
        return "ERR"
out = {"rel": [rel(p) for p in real], "resolve": [str(paths.resolve(s)) for s in stored],
       "dirs": {c: str(paths.project_dir(c)) for c in ("ABC", "DEF")},
       "folders": [[c, str(d)] for c, d in paths.project_folders()],
       "allowed": [str(x) for x in paths.allowed_roots()],
       "tool": [paths.tool_pattern("%s/02 Meetings/x" % n) for n in ("Example Programme", "Digital Enablement")]
               + [paths.tool_pattern("_portfolio/x")]}
print(json.dumps(out))
"""


class MappedCase(OneDriveCase):
    """OneDriveCase with ABC's folder moved to ~/Work/Acme/Programme and mapped there."""

    def setUp(self):
        super().setUp()
        self.own = self.home / "Work" / "Acme" / "Programme"
        self.own.parent.mkdir(parents=True)
        shutil.move(str(self.eng("ABC")), str(self.own))
        self.map({ABC: OWN})

    def map(self, mapping, **extra):
        cfg = self.v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text())
        data["locations"] = dict(data["locations"], project_paths=mapping, **extra)
        cfg.write_text(json.dumps(data, indent=2))

    def probe(self, real=(), stored=(), scripts=None):
        """PROBE run in the vault (or in `scripts`, a scripts folder of the same vault), as JSON."""
        scripts = scripts or self.v.root / "system/scripts"
        src = f"import sys, json; sys.path.insert(0, {str(scripts)!r})\n{PROBE}"
        r = subprocess.run([sys.executable, "-c", src, json.dumps([str(p) for p in real]), json.dumps(list(stored))],
                           capture_output=True, text=True, cwd=tempfile.gettempdir())
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def problem(self, name, value, mapping=None, env=None, **loc):
        """paths.project_mapping_problem for `name` -> `value` in this vault's locations (plus `loc`), or None."""
        mapping = {name: value} if mapping is None else mapping
        code = f"""import paths
loc = dict(paths.locations(), **{json.dumps(loc)}); loc['project_paths'] = {json.dumps(mapping)}
print(json.dumps(paths.project_mapping_problem({json.dumps(name)}, {json.dumps(value)}, loc)))"""
        src = f"import sys, json; sys.path.insert(0, {str(self.v.root / 'system/scripts')!r})\n{code}"
        r = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True, cwd=tempfile.gettempdir(),
                           env=dict(os.environ, **(env or {})))
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])


class RoundTrip(MappedCase):
    """rel and resolve are each other's inverse for mapped and unmapped projects, the portfolio and archived projects."""

    def test_files_in_mapped_and_unmapped_projects_and_the_portfolio(self):
        files = [self.own / MIN / "2026-10-01 Steering.docx", self.eng("DEF", MIN, "2026-10-01 Review.docx"),
                 self.root / "_Portfolio" / MIN / "2026-10-02 Portfolio.docx", self.own / "CLAUDE.md"]
        for f in files:
            touch(f)
        want = [f"projects/{ABC}/{MIN}/2026-10-01 Steering.docx", f"projects/{DEF}/{MIN}/2026-10-01 Review.docx",
                f"projects/_portfolio/{MIN}/2026-10-02 Portfolio.docx", f"projects/{ABC}/CLAUDE.md"]
        o = self.probe(files, want)
        self.assertEqual(o["rel"], want)
        self.assertEqual(o["resolve"], [str(f) for f in files])

    def test_a_file_not_there_yet_round_trips_too(self):
        f = self.own / "08 Notes" / "2026-10-03 New note.md"          # not created: a new file's own path
        o = self.probe([f], [f"projects/{ABC}/08 Notes/2026-10-03 New note.md"])
        self.assertEqual(o["rel"], [f"projects/{ABC}/08 Notes/2026-10-03 New note.md"])
        self.assertEqual(o["resolve"], [str(f)])

    def test_the_stored_name_is_matched_as_macos_matches_names(self):
        o = self.probe([], [f"projects/{ABC.lower()}/CLAUDE.md"])
        self.assertEqual(o["resolve"], [str(self.own / "CLAUDE.md")])

    def test_an_archived_mapped_project_is_beside_its_own_folder(self):
        f = self.own / MIN / "2026-10-01 Steering.docx"
        touch(f)
        slot = self.home / "Work" / "Acme" / "99 Archive" / ABC         # named for the register's folder, not the folder's own name
        slot.parent.mkdir()
        shutil.move(str(self.own), str(slot))
        stored = f"projects/{ABC}/{MIN}/2026-10-01 Steering.docx"
        o = self.probe([slot / MIN / "2026-10-01 Steering.docx"], [stored, f"projects/99 Archive/{ABC}/{MIN}/2026-10-01 Steering.docx"])
        self.assertEqual(o["resolve"], [str(slot / MIN / "2026-10-01 Steering.docx")] * 2)      # the old link still opens
        self.assertEqual(o["rel"], [f"projects/99 Archive/{ABC}/{MIN}/2026-10-01 Steering.docx"])   # as in the projects root
        s = self.py(f"import paths; print(json.dumps([str(paths.archive_slot({ABC!r})), str(paths.archive_dir({ABC!r})), "
                    f"str(paths.archive_dir({DEF!r})), str(paths.archive_dir()), paths.archive_slot({DEF!r})]))")
        self.assertEqual(s, [str(slot), str(slot.parent), str(self.root / "99 Archive"), str(self.root / "99 Archive"), None])

    def test_an_archived_mapped_project_in_an_old_archive_name_still_opens(self):
        slot = self.home / "Work" / "Acme" / "_Archive" / ABC
        slot.parent.mkdir()
        shutil.move(str(self.own), str(slot))
        o = self.probe([], [f"projects/{ABC}/CLAUDE.md"])
        self.assertEqual(o["resolve"], [str(slot / "CLAUDE.md")])

    def test_an_archived_unmapped_project_is_as_before(self):
        f = self.eng("DEF", MIN, "2026-10-01 Review.docx")
        touch(f)
        (self.root / "99 Archive").mkdir(exist_ok=True)
        shutil.move(str(self.eng("DEF")), str(self.root / "99 Archive" / DEF))
        moved = self.root / "99 Archive" / DEF / MIN / "2026-10-01 Review.docx"
        o = self.probe([moved], [f"projects/{DEF}/{MIN}/2026-10-01 Review.docx"])
        self.assertEqual(o["resolve"], [str(moved)])
        self.assertEqual(o["rel"], [f"projects/99 Archive/{DEF}/{MIN}/2026-10-01 Review.docx"])

    def test_a_report_in_a_mapped_projects_own_archive_keeps_its_stored_path(self):
        old = self.own / "99 Archive" / MIN / "2025-01-01 Old steering.docx"      # BL-03, inside the project
        touch(old)
        o = self.probe([old], [f"projects/{ABC}/{MIN}/2025-01-01 Old steering.docx"])
        self.assertEqual(o["resolve"], [str(old)])
        self.assertEqual(o["rel"], [f"projects/{ABC}/99 Archive/{MIN}/2025-01-01 Old steering.docx"])


class Helpers(MappedCase):
    """project_dir, project_folders, allowed_roots, tool_pattern, base_of, project_area and the notes helpers."""

    def test_project_dir_folders_and_allowed_roots_include_the_mapped_one(self):
        o = self.probe()
        self.assertEqual(o["dirs"], {"ABC": str(self.own), "DEF": str(self.eng("DEF"))})
        self.assertEqual(o["folders"], [["ABC", str(self.own)], ["DEF", str(self.eng("DEF"))], ["_portfolio", str(self.root / "_Portfolio")]])
        self.assertEqual(o["allowed"][1:], [str(self.root), str(self.own)])          # never the folder's parent or its archive slot
        self.assertEqual(o["tool"], ["~/Work/Acme/Programme/02 Meetings/x",
                                     f"~/Library/CloudStorage/OneDrive-TestCo/Documents/Engagements/{DEF}/02 Meetings/x",
                                     "~/Library/CloudStorage/OneDrive-TestCo/Documents/Engagements/_Portfolio/x"])

    def test_folder_kinds_base_of_area_and_patterns(self):
        touch(self.own / MIN / "a.docx")
        o = self.py(f"""import paths
from pathlib import Path
own, root = Path({str(self.own)!r}), Path({str(self.root)!r})
print(json.dumps([str(paths.folder('ABC', 'minutes')), str(paths.base_of(own / 'x' / 'y')), str(paths.base_of(root / 'x')),
                  str(paths.base_of(root / '_Portfolio' / 'x')), paths.base_of(own.parent / '99 Archive' / 'x'),
                  list(paths.parts_below_base(own / '99 Archive' / 'x')[1]), list(paths.project_area(own / '{MIN}' / 'a.docx')),
                  paths.project_path_problem(str(own / '99 Archive' / 'x')), paths.tool_patterns('**/99 Archive/**'),
                  paths.project_paths(), paths.missing_project_paths()]))""")
        self.assertEqual(o[0], str(self.own / MIN))
        self.assertEqual(o[1:4], [str(self.own), str(self.root), str(self.root / "_Portfolio")])
        self.assertIsNone(o[4])
        self.assertEqual(o[5], ["99 Archive", "x"])
        self.assertEqual(o[6], ["ABC", ["02 Meetings", "Minutes", "a.docx"]])
        self.assertIn("99 Archive", o[7])                                          # never read or written, in a mapped one too
        self.assertEqual(o[8], ["~/Library/CloudStorage/OneDrive-TestCo/Documents/Engagements/**/99 Archive/**",
                                "~/Work/Acme/Programme/**/99 Archive/**"])
        self.assertEqual(o[9], {ABC: OWN})
        self.assertEqual(o[10], [])

    def test_mapped_notes_are_known_to_the_notes_checks(self):
        touch(self.own / "08 Notes" / "2026-10-03 A note.md")
        o = self.py(f"""import paths
from pathlib import Path
own = Path({str(self.own)!r})
print(json.dumps([paths.in_mapped_notes(own / '08 Notes' / 'n.md'), paths.in_mapped_notes(own / '99 Archive' / '08 Notes' / 'n.md'),
                  paths.in_mapped_notes(own / 'Other' / 'n.md'),
                  paths.in_mapped_notes(own.parent / '99 Archive' / {ABC!r} / '08 Notes' / 'n.md'),
                  paths.in_mapped_notes(own.parent / '99 Archive' / {ABC!r} / '08 Notes' / 'n.md', archived=True),
                  paths.is_note(own / '08 Notes' / '2026-10-03 A note.md'),
                  paths.locations_change_problem(paths.locations(), dict(paths.locations(), folders=dict(paths.locations()['folders'], notes='09 Notes')))]))""")
        self.assertEqual(o[:6], [True, True, False, False, True, True])
        self.assertIn("08 Notes", o[6])                    # renaming the notes folder while a mapped project has notes: refused

    def test_without_a_projects_folder_the_mapping_is_ignored(self):
        o = self.py("import paths; print(json.dumps([{k: str(v) for k, v in paths.project_roots().items()}, paths.external()]))")
        self.assertEqual(o, [{ABC: str(self.own)}, True])
        self.map({ABC: OWN}, projects_root="")
        o = self.py("import paths; print(json.dumps([{k: str(v) for k, v in paths.project_roots().items()}, paths.project_paths(), paths.external(), "
                    "str(paths.resolve('projects/Example Programme/x'))]))")
        self.assertEqual(o[:3] + [os.path.realpath(o[3])], [{}, {}, False, os.path.realpath(self.v.root / "projects/Example Programme/x")])      # macOS: /private/var is /var


class Unmounted(MappedCase):
    """A mapped folder that isn't there is reported, never created and never silently dropped."""

    def test_reported_and_not_created(self):
        shutil.rmtree(self.own)
        o = self.py("import paths; print(json.dumps([paths.missing_project_paths(), [c for c, _ in paths.project_folders()], "
                    "str(paths.project_dir('ABC'))]))")
        self.assertEqual(o[0], [{"code": "ABC", "folder": ABC, "path": OWN}])
        self.assertEqual(o[1], ["DEF", "_portfolio"])
        self.assertEqual(o[2], str(self.own))
        r = subprocess.run([sys.executable, str(self.v.root / "system/scripts/doctor.py"), "--read-only", "--json"],
                           capture_output=True, text=True, cwd=tempfile.gettempdir())
        checks = {c["id"]: c for c in json.loads(r.stdout)["checks"]}
        own = checks["project_paths_present"]
        self.assertEqual(own["status"], "warn")
        self.assertIn(f"{ABC} ({OWN})", own["detail"])
        self.assertIn("Nothing is lost", own["detail"])
        self.assertNotIn("ABC", checks["project_folders_present"]["detail"])       # said once, by its own check
        self.assertNotIn(ABC, checks["project_folders_present"]["detail"])
        self.assertFalse(self.own.exists())                          # never created
        self.assertFalse(self.own.parent.joinpath("99 Archive").exists())

    def test_fine_when_there(self):
        r = subprocess.run([sys.executable, str(self.v.root / "system/scripts/doctor.py"), "--read-only", "--json"],
                           capture_output=True, text=True, cwd=tempfile.gettempdir())
        own = {c["id"]: c for c in json.loads(r.stdout)["checks"]}["project_paths_present"]
        self.assertEqual((own["status"], own["detail"]), ("pass", "1 project in a folder of its own, all reachable"))

    def test_health_has_plain_words_for_it(self):
        o = self.py("import health; print(json.dumps(health.PLAIN['project_paths_present']))")
        self.assertEqual(o, ["A project's own folder can't be reached", "manual"])


class Refusals(MappedCase):
    """Every refusal on save (paths.project_mapping_problem, through locations_change_problem)."""

    def assertRefused(self, why, *words):
        self.assertIsNotNone(why)
        self.assertTrue(why.startswith("Not saved:"), why)
        for w in words:
            self.assertIn(w, why)

    def test_the_mapping_in_place_is_accepted(self):
        self.assertIsNone(self.problem(ABC, OWN))
        self.assertIsNone(self.problem(ABC, "~/Library/CloudStorage/OneDrive-TestCo/Clients/Programme"))
        self.assertIsNone(self.problem(ABC, ABC))                          # relative: the projects folder's own one, by its name
        self.assertIsNone(self.problem(ABC, "~/Work/Not there yet"))       # a folder not made yet may be saved (Health says so)

    def test_two_projects_on_one_path(self):
        self.assertRefused(self.problem(ABC, OWN, {ABC: OWN, DEF: OWN}), "same folder", DEF)

    def test_two_projects_on_one_path_ignoring_case_and_unicode_form(self):
        self.assertRefused(self.problem(ABC, OWN, {ABC: OWN, DEF: OWN.lower()}), "same folder")
        nfc, nfd = "~/Work/Caf\u00e9", "~/Work/Cafe\u0301"
        self.assertRefused(self.problem(ABC, nfc, {ABC: nfc, DEF: nfd}), "same folder")

    def test_one_inside_another_either_way(self):
        self.assertRefused(self.problem(ABC, OWN, {ABC: OWN, DEF: OWN + "/Sub"}), "inside", DEF)
        self.assertRefused(self.problem(ABC, OWN, {ABC: OWN, DEF: "~/Work/Acme"}), "inside", DEF)

    def test_inside_the_projects_folder_under_another_name(self):
        # Jarvis, 26-10-2026: allowed (relative or with ~), unless it is another registered project's folder or the portfolio
        self.assertIsNone(self.problem(ABC, f"Clients/{ABC}"))
        self.assertIsNone(self.problem(ABC, "~/Library/CloudStorage/OneDrive-TestCo/Documents/Engagements/Other"))
        self.assertRefused(self.problem(ABC, DEF), "inside", DEF)                          # DEF's own folder there
        self.assertRefused(self.problem(ABC, f"{DEF}/Sub"), "inside", DEF)
        self.assertRefused(self.problem(ABC, "_Portfolio/Programme"), "portfolio")

    def test_holding_the_projects_folder(self):
        self.assertRefused(self.problem(ABC, "~/Library/CloudStorage/OneDrive-TestCo/Documents"), "holds the projects folder")

    def test_inside_the_creaite_folder_or_system(self):
        env = {"HOME": str(self.v.root.parent)}                         # a home that holds the vault, for this check only
        for sub in ("", "/system", "/system/staging/x", "/projects/x"):
            self.assertRefused(self.problem(ABC, f"~/{self.v.root.name}{sub}", env=env), "creaite folder")

    def test_under_99_archive_templates_or_99_system(self):
        for name in ("99 Archive", "_Templates", "99 System", "_Archive", "zz Archive", "99 archive"):
            self.assertRefused(self.problem(ABC, f"~/Work/{name}/Programme"), "never reads or writes")
            self.assertRefused(self.problem(ABC, f"~/Work/{name}"), "never reads or writes")

    def test_outside_home_or_not_written_with_a_tilde(self):
        self.assertRefused(self.problem(ABC, "/srv/Programme"), "written with ~")
        self.assertRefused(self.problem(ABC, str(self.own)), "written with ~")
        self.assertRefused(self.problem(ABC, "~otheruser/Programme"), "written with ~")
        self.assertRefused(self.problem(ABC, "~"), "home folder itself")
        self.assertRefused(self.problem(ABC, "~/"), "home folder itself")
        outside = Path(tempfile.mkdtemp(prefix="creaite-out-"))
        try:                                                   # relative to a projects folder that is outside the home folder
            self.assertRefused(self.problem(ABC, ABC, projects_root=str(outside)), "inside your home folder")
        finally:
            shutil.rmtree(outside)

    def test_on_the_never_list_or_holding_a_place_on_it(self):
        self.assertRefused(self.problem(ABC, "~/.ssh/Programme"), "never touches", "secrets")
        self.assertRefused(self.problem(ABC, "~/.config"), "never touches")               # holds ~/.config/gh
        self.assertRefused(self.problem(ABC, "~/.local/bin/x"), "never touches")

    def test_library_outside_cloud_storage(self):
        self.assertRefused(self.problem(ABC, "~/Library/Mobile Documents/Programme"), "Library")
        self.assertRefused(self.problem(ABC, "~/Library/Keychains"), "Library")
        self.assertRefused(self.problem(ABC, "~/library/Programme"), "Library")             # case ignored

    def test_dot_dot(self):
        self.assertRefused(self.problem(ABC, "~/Work/Acme/../Acme/Programme"), "..")
        self.assertRefused(self.problem(ABC, f"../{ABC}"), "..")

    def test_a_symlink(self):
        (self.home / "Links").mkdir()
        os.symlink(self.own, self.home / "Links" / "Programme")
        self.assertRefused(self.problem(ABC, "~/Links/Programme"), "symlink")
        os.symlink(self.home / "Work", self.home / "WorkLink")
        self.assertRefused(self.problem(ABC, "~/WorkLink/Acme/Programme"), "symlink")    # a link part way down
        o = self.py("import paths; print(json.dumps(paths.project_path_stored('~/Links/Programme')))")
        self.assertEqual(o, OWN)                                         # stored as the real place, with ~

    def test_bad_names_and_values(self):
        self.assertRefused(self.problem("_Portfolio", "~/Work/P"), "isn't a project's folder name")
        self.assertRefused(self.problem("99 Archive", "~/Work/P"), "isn't a project's folder name")
        self.assertRefused(self.problem("a/b", "~/Work/P"), "isn't a project's folder name")
        self.assertRefused(self.problem(ABC, "  "), "empty")
        self.assertRefused(self.problem(ABC, OWN, projects_root=""), "projects folder set first")

    def test_through_the_settings_save(self):
        o = self.py(f"""import paths
old = paths.locations()
print(json.dumps([paths.locations_change_problem(old, dict(old, project_paths={{{ABC!r}: {OWN!r}, {DEF!r}: {OWN!r}}})),
                  paths.locations_change_problem(old, dict(old, project_paths='~/x')),
                  paths.locations_change_problem(old, dict(old, project_paths={{{DEF!r}: '~/Work/Other'}})),
                  paths.locations_change_problem(old, dict(old)),
                  paths.locations_change_problem(old, dict(old, projects_root=''))]))""")
        self.assertIn("same folder", o[0])
        self.assertIn("must be an object", o[1])
        self.assertIsNone(o[2])
        self.assertIsNone(o[3])                                            # unchanged: not checked again
        self.assertIn("projects folder set first", o[4])                  # clearing the projects folder would hide ABC


class Unchanged(MappedCase):
    """Unmapped projects behave exactly as before #385 (paths.py at BASE_COMMIT, on the same vault)."""

    def old_scripts(self):
        r = subprocess.run(["git", "-C", str(REPO), "show", f"{BASE_COMMIT}:system/scripts/paths.py"], capture_output=True, text=True)
        if r.returncode != 0:
            self.skipTest(f"git show {BASE_COMMIT} isn't available here")
        d = self.v.root / "system" / "scripts_main"           # parents[2] is still the vault
        d.mkdir()
        (d / "paths.py").write_text(r.stdout, encoding="utf-8")
        return d

    def test_no_mapping_is_byte_identical(self):
        shutil.move(str(self.own), str(self.eng("ABC")))
        self.map({})
        files = [self.eng("ABC", MIN, "a.docx"), self.eng("DEF", MIN, "b.docx"), self.root / "_Portfolio" / "x.md",
                 self.root / "99 Archive" / "Z" / "y.md", self.v.root / "inbox" / "i.docx"]
        for f in files:
            touch(f)
        stored = [f"projects/{ABC}/{MIN}/a.docx", f"projects/{DEF}/x", "projects/_portfolio/x.md", "projects/99 Archive/Z/y.md",
                  "projects/Z/y.md", "inbox/i.docx", "system/staging/drafts/d.json"]
        self.assertEqual(self.probe(files, stored), self.probe(files, stored, scripts=self.old_scripts()))

    def test_unmapped_projects_beside_a_mapped_one_are_unchanged(self):
        files = [self.eng("DEF", MIN, "b.docx"), self.root / "_Portfolio" / MIN / "p.docx", self.v.root / "inbox" / "i.docx"]
        for f in files:
            touch(f)
        stored = [f"projects/{DEF}/{MIN}/b.docx", "projects/_portfolio/x.md", "inbox/i.docx", "projects/Other/x"]
        new, old = self.probe(files, stored), self.probe(files, stored, scripts=self.old_scripts())
        self.assertEqual(new["rel"], old["rel"])
        self.assertEqual(new["resolve"], old["resolve"])
        self.assertEqual(new["dirs"]["DEF"], old["dirs"]["DEF"])
        self.assertEqual(new["tool"][1:], old["tool"][1:])
        self.assertEqual([f for f in new["folders"] if f[0] != "ABC"], old["folders"])     # the old engine can't see ABC


class Mutants(MappedCase):
    """Each piece of the mapping, taken out, is caught by the round trip."""

    TEXT = (REPO / "system/scripts/paths.py").read_text(encoding="utf-8")

    def mutate(self, old, new):
        self.assertIn(old, self.TEXT)
        (self.v.root / "system/scripts/paths.py").write_text(self.TEXT.replace(old, new), encoding="utf-8")

    def round_trip(self):
        files = [self.own / MIN / "a.docx", self.root / "_Portfolio" / MIN / "p.docx"]
        for f in files:
            touch(f)
        want = [f"projects/{ABC}/{MIN}/a.docx", f"projects/_portfolio/{MIN}/p.docx"]
        o = self.probe(files, want)
        return o["rel"] == want and o["resolve"] == [str(f) for f in files]

    def test_the_round_trip_holds_unmutated(self):
        self.assertTrue(self.round_trip())

    def test_longest_match_off(self):
        self.mutate("key=lambda x: -len(x[0].parts))", "key=lambda x: len(x[0].parts))")
        self.assertFalse(self.round_trip())

    def test_mapping_ignored_in_rel(self):
        self.mutate("bases = _bases(roots) if roots else", "bases = _bases({}) if roots else")
        self.assertFalse(self.round_trip())

    def test_mapping_ignored_in_resolve(self):
        self.mutate("mapped = _resolve_mapped(s, archived)", "mapped = None")
        self.assertFalse(self.round_trip())

    def test_archive_slot_named_for_the_folder_on_disk(self):
        want = str(self.home / "Work" / "Acme" / "99 Archive" / ABC)
        check = f"import paths; print(json.dumps(str(paths.archive_slot({ABC!r}))))"
        self.assertEqual(self.py(check), want)                              # the check passes on the real code
        self.mutate("return roots[k].parent / ARCHIVE / k if k else None", "return roots[k].parent / ARCHIVE / roots[k].name if k else None")
        self.assertNotEqual(self.py(check), want)                           # and catches the mutant

    def test_no_symlink_check(self):
        (self.home / "Links").mkdir()
        os.symlink(self.own, self.home / "Links" / "Programme")
        self.assertIsNotNone(self.problem(ABC, "~/Links/Programme"))
        self.mutate("        if os.path.islink(here):\n", "        if False:\n")
        self.assertIsNone(self.problem(ABC, "~/Links/Programme"))


if __name__ == "__main__":
    unittest.main()
