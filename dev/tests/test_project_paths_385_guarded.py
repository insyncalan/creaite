"""#385 phase 3: the guarded diffs for a project's own folder (locations.project_paths), tested on a throwaway vault.

GUARDED: tracker.py, reach.py, permissions.py and live_server.py are guarded, so their changes are four diff files for Alan's
approval (dev/proposals/385/385-<file>.diff), never edits in the tree. Each test copies the vault's guarded files with the diffs
applied (to the tree's file; when a diff applies only to the 2.6.9 file, to that file from origin/v269-chain); a diff that is
already in the tree is taken as it is. A diff that can't be applied skips the tests with a "GUARDED: … not in the tree" reason,
never silently. Every behaviour has a mutant: the diff's key line taken out, and the test shows the behaviour goes.

Everything is fictional and temporary: a fake home folder, the OneDrive-style projects folder of test_onedrive_projects, and ABC
(Example Programme) mapped to ~/Work/Acme/Programme (MappedCase of test_project_paths_385). DEF stays in the projects folder.

Run: python3 dev/tests/test_project_paths_385_guarded.py
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
from test_onedrive_projects import touch  # noqa: E402
from test_project_paths_385 import ABC, DEF, MIN, OWN, MappedCase  # noqa: E402

os.environ["PYTHONDONTWRITEBYTECODE"] = "1"         # a mutant may keep a file's size and second: never a stale .pyc
REPO = Path(__file__).resolve().parents[2]
PROPOSALS = REPO / "dev" / "proposals" / "385"
DIFFS = {"tracker.py": "385-tracker.diff", "reach.py": "385-reach.diff", "permissions.py": "385-permissions.diff",
         "live_server.py": "385-live_server.diff"}
V269 = "origin/v269-chain"
NOTES = "08 Notes"


def _apply(text, diff, reverse=False, check_only=False):
    """(ok, patched text) of `diff` applied to one file's `text`, in a scratch folder (the tree is never touched)."""
    d = Path(tempfile.mkdtemp(prefix="creaite-385g-"))
    try:
        f = d / "system" / "scripts" / diff["name"]
        f.parent.mkdir(parents=True)
        f.write_text(text, encoding="utf-8")
        args = ["git", "apply", *(["-R"] if reverse else []), *(["--check"] if check_only else []), str(diff["path"])]
        r = subprocess.run(args, cwd=d, capture_output=True, text=True)
        return r.returncode == 0, f.read_text(encoding="utf-8")
    finally:
        shutil.rmtree(d, True)


def _patched():
    """({file: patched text}, {file: where it was cut}, skip reason or None)."""
    out, base = {}, {}
    for name, diff_name in DIFFS.items():
        diff = {"name": name, "path": PROPOSALS / diff_name}
        if not diff["path"].is_file():
            return {}, {}, f"GUARDED: dev/proposals/385/{diff_name} not in the tree"
        tree = (REPO / "system" / "scripts" / name).read_text(encoding="utf-8")
        ok, text = _apply(tree, diff)
        if ok:
            out[name], base[name] = text, "tree"
            continue
        if _apply(tree, diff, reverse=True, check_only=True)[0]:      # landed already
            out[name], base[name] = tree, "landed"
            continue
        r = subprocess.run(["git", "show", f"{V269}:system/scripts/{name}"], cwd=REPO, capture_output=True, text=True)
        ok, text = _apply(r.stdout, diff) if r.returncode == 0 else (False, "")
        if not ok:
            return {}, {}, f"GUARDED: dev/proposals/385/{diff_name} not in the tree (and it applies to neither the tree nor {V269})"
        out[name], base[name] = text, V269
    return out, base, None


PATCHED, BASE, SKIP = _patched()
SAFE_CHECK = "    if b is not None and not b.is_dir():\n"                  # tracker._missing_base_check: safe_path, every purpose
UNDO_CHECK = "            elif _missing_base(p) is not None:    # #385: a drive or OneDrive not connected: never made on the laptop's disk\n"
needs_diffs = unittest.skipIf(SKIP is not None, SKIP or "")


PATHS = (REPO / "system" / "scripts" / "paths.py").read_text(encoding="utf-8")


def paths_mutant(old, new):
    """{"paths.py": the tree's paths.py (an ordinary file) with `old` (there exactly once) replaced by `new`}."""
    assert PATHS.count(old) == 1, f"paths.py: the mutant's line is not there exactly once: {old!r}"
    return {"paths.py": PATHS.replace(old, new)}


def mutant(name, old, new=""):
    """{name: the patched file with `old` (the diff's key line, which must be there exactly once) replaced by `new`}."""
    text = PATCHED[name]
    assert text.count(old) == 1, f"{name}: the mutant's line is not there exactly once: {old!r}"
    return {name: text.replace(old, new)}


@needs_diffs
class GuardedCase(MappedCase):
    """MappedCase with the four guarded files patched in the vault (and, per test, a mutant of one)."""

    def setUp(self):
        super().setUp()
        self.install()

    def install(self, overrides=None):
        scripts = self.v.root / "system" / "scripts"
        for name, text in {**PATCHED, "paths.py": PATHS, **(overrides or {})}.items():
            (scripts / name).write_text(text, encoding="utf-8")
        shutil.rmtree(scripts / "__pycache__", ignore_errors=True)

    def both(self, code, mutated):
        """`code`'s JSON with the diffs, then with the mutant `mutated` (and the diffs put back afterwards)."""
        good = self.py(code)
        self.install(mutated)
        try:
            bad = self.py(code)
        finally:
            self.install()
        return good, bad

    def slot(self):
        return self.home / "Work" / "Acme" / "99 Archive" / ABC


class SafePath(GuardedCase):
    """tracker.safe_path: never a write into a mapped project's 99 Archive or _Templates (the hole below the projects root only)."""

    CODE = f"""import tracker
out = []
for s, why in [({ABC!r} + '/99 Archive/x.md', 'write'), ({ABC!r} + '/99 archive/x.md', 'write'), ({ABC!r} + '/_Templates/x.md', 'write'),
               ({ABC!r} + '/99 System/x.md', 'write'), ({ABC!r} + '/{NOTES}/x.md', 'write'), ({DEF!r} + '/99 Archive/x.md', 'write'),
               ({ABC!r} + '/99 Archive', 'mkdir')]:
    try:
        out.append(str(tracker.safe_path('projects/' + s, why)))
    except tracker.Invalid as e:
        out.append('REFUSED ' + str(e))
print(json.dumps(out))"""

    def test_skipped_names_under_a_mapped_folder_are_refused_and_a_write_there_is_allowed(self):
        good, bad = self.both(self.CODE, mutant("tracker.py", "    for base in [paths.projects_root(), *paths.project_roots().values()]:",
                                                 "    for base in [paths.projects_root()]:"))
        for got in good[:4]:
            self.assertTrue(got.startswith("REFUSED") and "never written by creaite" in got, got)
        self.assertEqual(good[4], str(self.own / NOTES / "x.md"))            # an ordinary write in the mapped folder
        self.assertTrue(good[5].startswith("REFUSED"))                       # the projects root as before
        self.assertEqual(good[6], str(self.own / "99 Archive"))              # the skeleton's own empty 99 Archive may be made
        self.assertFalse(any(x.startswith("REFUSED") for x in bad[:4]), bad)  # mutant: the hole is back
        self.assertTrue(bad[5].startswith("REFUSED"))


class NeverVerdict(GuardedCase):
    """reach.classify (_never_verdict): never under a mapped folder's 99 Archive, _Templates, 99 System, or its archive slot."""

    def code(self):
        own, slot = self.own, self.slot()
        return f"""import reach
cases = [({str(own / '99 Archive' / 'x.md')!r}, 'create'), ({str(own / '99 archive' / 'x.md')!r}, 'read'),
         ({str(own / '_Templates' / 'x.md')!r}, 'create'), ({str(slot / 'CLAUDE.md')!r}, 'read'),
         ({str(own / NOTES / 'x.md')!r}, 'create'), ({str(own / 'CLAUDE.md')!r}, 'read')]
print(json.dumps([reach.classify(p, op)[0] for p, op in cases]))""".replace("NOTES", repr(NOTES))

    def test_the_skipped_names_are_never_under_a_mapped_folder_too(self):
        touch(self.slot() / "CLAUDE.md")
        good, bad = self.both(self.code(), mutant(
            "reach.py", "    out = [x for b in [paths.projects_root(), *all_mapped().values()] for x in (folded_under(p, Path(os.path.realpath(b))) or ())]",
            "    out = [x for b in [paths.projects_root()] for x in (folded_under(p, Path(os.path.realpath(b))) or ())]"))
        self.assertEqual(good[:4], ["never"] * 4)
        self.assertEqual(good[4:], ["ordinary", "ordinary"])
        self.assertNotEqual(bad[:3], ["never"] * 3)                           # mutant: P/99 Archive is reachable again

    def test_the_archive_slot_beside_a_mapped_folder_is_never(self):
        touch(self.slot() / "CLAUDE.md")
        good, bad = self.both(self.code(), mutant("reach.py", "                out.append(below[0])\n", "                pass\n"))
        self.assertEqual(good[3], "never")
        self.assertNotEqual(bad[3], "never")


class Roots(GuardedCase):
    """reach.roots: exactly the mapped folders of registered projects, never their parent, a slot or an archived entry."""

    CODE = "import reach; print(json.dumps([[n, str(r)] for n, r in reach.roots()]))"

    def test_reach_is_exactly_the_mapped_folders(self):
        gone = self.home / "Work" / "Old" / "Programme"                      # mapped, but not in the register (archived)
        gone.mkdir(parents=True)
        self.map({ABC: OWN, "Old Programme": "~/Work/Old/Programme"})
        good, bad = self.both(self.CODE, mutant("reach.py", '        out += [("projects", p) for p in mapped_roots()]\n'))
        self.assertEqual(good, [["vault", os.path.realpath(self.v.root)], ["projects", str(self.root)], ["projects", str(self.own)],
                                ["home", str(self.home)]])
        self.assertNotIn(["projects", str(self.own)], bad)

    def test_the_guard_hook_and_the_live_server_agree(self):
        o = self.py("""import reach, live_server, os
print(json.dumps({"roots": sorted(str(r) for n, r in reach.roots() if n == "projects"),
                  "extra": sorted(os.path.realpath(d) for d in live_server.extra_dirs()),
                  "reach_dirs": sorted(os.path.realpath(d) for d in live_server.reach_dirs())}))""")
        self.assertEqual(o["roots"], o["extra"])
        self.assertEqual(o["reach_dirs"], sorted(o["extra"] + [str(self.home)]))
        self.install(mutant("live_server.py", " + [str(p) for p in reach.mapped_roots()]"))
        o = self.py("import reach, live_server; print(json.dumps([sorted(str(r) for n, r in reach.roots() if n == 'projects'), live_server.extra_dirs()]))")
        self.assertNotEqual(sorted(o[0]), sorted(o[1]))                    # mutant: the run's --add-dir misses the mapped folder

    def hook(self, tool, inp):
        r = subprocess.run([sys.executable, str(self.v.root / "system/scripts/reach.py"), "hook", "--run", "r-385", "--mode", "ask"],
                           cwd=self.v.root, input=json.dumps({"tool_name": tool, "tool_input": inp}), capture_output=True,
                           text=True, timeout=60)
        return r.returncode, r.stderr

    def test_the_hook_refuses_a_mapped_folders_99_archive_and_lets_its_files_be_read(self):
        touch(self.own / "99 Archive" / "old.md")
        touch(self.own / "CLAUDE.md", "# ABC\n")
        self.py("import reach, live_server; reach.start_run('r-385', 'ask', live_server.OUTSIDE_CONTENT); print(1)")
        code, err = self.hook("Read", {"file_path": str(self.own / "99 Archive" / "old.md")})
        self.assertEqual(code, 2)
        self.assertIn("99 Archive is never read or written", err)
        self.assertEqual(self.hook("Read", {"file_path": str(self.own / "CLAUDE.md")})[0], 0)
        self.install(mutant("reach.py", "    below = skipped_below(p)", "    below = []"))
        self.assertEqual(self.hook("Read", {"file_path": str(self.own / "99 Archive" / "old.md")})[0], 0)   # mutant: let through


class ArchiveMoves(GuardedCase):
    """An archive moves the mapped folder into exactly its slot (and a restore back); any other place outside the roots is refused."""

    def move(self, src, dst, kind):
        return self.py(f"""import tracker
try:
    tracker.check_move({{"op": "move", "from": {src!r}, "to": {dst!r}}}, {{"archive": {kind!r}}})
    print(json.dumps(None))
except tracker.Invalid as e:
    print(json.dumps(str(e)))""")

    def test_archive_into_the_slot_restore_and_undo(self):
        touch(self.own / MIN / "2026-10-01 Steering.docx")
        src, dst = f"projects/{ABC}", f"projects/99 Archive/{ABC}"
        self.assertIsNone(self.move(src, dst, "archive"))
        o = self.py(f"""import tracker
done, report = [], []
tracker._op_move(None, {{"op": "move", "from": {src!r}, "to": {dst!r}}}, {{"archive": "archive"}}, done)
print(json.dumps(done))""")
        self.assertTrue((self.slot() / MIN / "2026-10-01 Steering.docx").is_file())
        self.assertFalse(self.own.exists())
        self.assertIsNone(o[0]["made"])                                       # the slot's 99 Archive has no stored path
        self.assertIsNone(self.move(dst, src, "restore"))
        self.py(f"""import tracker
report = []
tracker._reverse_move(json.loads({json.dumps(json.dumps(o[0]))}), report)
print(json.dumps(report))""")
        self.assertTrue((self.own / MIN / "2026-10-01 Steering.docx").is_file())    # undo: back in its own folder

    def test_the_move_shape_is_measured_from_the_mapped_folder(self):
        src, dst = f"projects/{ABC}", f"projects/99 Archive/{ABC}"
        code = f"import reach; print(json.dumps(reach.archive_move_problem({src!r}, {dst!r}, 'archive')))"
        good, bad = self.both(code, mutant("reach.py", "    for k, own in all_mapped().items():", "    for k, own in {}.items():"))
        self.assertIsNone(good)
        self.assertIn("stays inside the projects folder", bad)               # mutant: as before #385, refused

    def test_any_other_place_outside_the_roots_is_refused(self):
        elsewhere = self.home / "Elsewhere"
        elsewhere.mkdir()
        (self.home / "Work" / "Acme" / "99 Archive").symlink_to(elsewhere)  # the slot's folder is a link: never followed
        self.assertIsNotNone(self.move(f"projects/{ABC}", f"projects/99 Archive/{ABC}", "archive"))
        self.assertIsNotNone(self.move(f"projects/{ABC}", f"projects/_Archive/{ABC}", "archive"))   # an old name: only a restore

    def test_tracker_allows_exactly_the_slot(self):
        code = f"""import tracker
print(json.dumps([tracker._outside_end_problem('projects/{ABC}', 'projects/99 Archive/{ABC}', 'archive'),
                  tracker._outside_end_problem('projects/99 Archive/{ABC}', 'projects/{ABC}', 'restore'),
                  tracker._outside_end_problem('projects/_Archive/{ABC}', 'projects/{ABC}', 'restore'),
                  tracker._outside_end_problem('projects/{DEF}', 'projects/99 Archive/{DEF}', 'archive'),
                  tracker._outside_end_problem('projects/{ABC}/{MIN}/a.docx', 'projects/99 Archive/{ABC}/a.docx', 'reports'),
                  tracker._outside_end_problem('projects/{DEF}', 'projects/99 Archive/{ABC}', 'archive')]))"""
        good, bad = self.both(code, mutant(
            "tracker.py", "    if real(own_end) != real(mapping[k]) or real(slot_end) not in {real(x) for x in places}:\n        return refused\n"))
        self.assertEqual(good[:4], [None] * 4)
        self.assertIn("isn't a project's own archive place", good[4])         # a report never leaves for the slot
        self.assertIn("isn't a project's own archive place", good[5])         # another folder into ABC's slot
        self.assertIsNone(bad[5])                                             # mutant: let through


class MkdirAndCopy(GuardedCase):
    """_op_mkdir never creates a mapped folder that isn't there; a copy may read from a mapped folder."""

    MKDIR = f"""import tracker
try:
    done = []
    tracker._op_mkdir(None, {{"op": "mkdir", "path": "projects/{ABC}/02 Meetings/New"}}, {{}}, done)
    print(json.dumps(done))
except (tracker.Invalid, OSError) as e:
    print(json.dumps(type(e).__name__ + ": " + str(e)))"""

    def test_a_missing_mapped_folder_is_never_created(self):
        shutil.move(str(self.own), str(self.home / "Unmounted"))
        good, bad = self.both(self.MKDIR, mutant("tracker.py", SAFE_CHECK, "    if False:\n"))
        self.assertIn("never creates it", good)
        self.assertFalse(self.own.exists())
        self.assertNotIn("never creates it", str(bad))                        # mutant: tried (and failed on its own)
        self.assertFalse(self.own.exists())

    def test_a_write_never_creates_a_missing_mapped_folder(self):
        """Cap's MEDIUM 2: _op_write's mkdir(parents=True) would make the whole folder on the laptop's own disk."""
        shutil.move(str(self.own), str(self.home / "Unmounted"))
        code = f"""import tracker
try:
    done = []
    tracker._op_write(None, {{"op": "write", "path": "projects/{ABC}/{NOTES}/2026-10-26 Note.md", "content": "x"}}, {{}}, done)
    print(json.dumps(done))
except (tracker.Invalid, OSError) as e:
    print(json.dumps(type(e).__name__ + ": " + str(e)))"""
        good = self.py(code)
        self.assertIn("never creates it", str(good))
        self.assertFalse(self.own.exists())
        self.install(mutant("tracker.py", SAFE_CHECK, "    if False:\n"))
        try:
            bad = self.py(code)
        finally:
            self.install()
        self.assertIsInstance(bad, list, bad)                                 # mutant: written, and the folder made
        self.assertTrue((self.own / NOTES / "2026-10-26 Note.md").is_file())

    def test_the_portfolio_may_be_made_inside_a_projects_folder_that_is_there(self):
        port = Path(self.py("import paths; print(json.dumps(str(paths.portfolio_dir())))"))
        shutil.rmtree(port, ignore_errors=True)
        code = """import tracker
try:
    done = []
    tracker._op_write(None, {"op": "write", "path": "projects/_portfolio/2026-10-26 Note.md", "content": "x"}, {}, done)
    print(json.dumps("written"))
except (tracker.Invalid, OSError) as e:
    print(json.dumps(type(e).__name__ + ": " + str(e)))"""
        self.assertEqual(self.py(code), "written")
        self.assertTrue((port / "2026-10-26 Note.md").is_file())
        shutil.rmtree(port)
        root = port.parent
        shutil.move(str(root), str(self.home / "Unmounted root"))
        self.assertIn("never creates it", self.py(code))                    # the projects folder itself gone: refused
        self.assertFalse(root.exists())

    def test_an_undo_never_restores_into_a_missing_mapped_folder(self):
        touch(self.own / NOTES / "a.md", "a\n")
        kept = self.v.root / "system" / "backups" / "files" / "1" / "a.md"
        touch(kept, "a\n")
        (self.own / NOTES / "a.md").unlink()
        shutil.move(str(self.own), str(self.home / "Unmounted"))
        rec = {"op": "remove", "path": f"projects/{ABC}/{NOTES}/a.md", "kept": "system/backups/files/1/a.md"}
        code = f"""import tracker
report = []
tracker.reverse_file_ops([{rec!r}], report)
print(json.dumps(report))"""
        good = self.py(code)
        self.assertTrue(any("isn't there" in x for x in good), good)
        self.assertFalse(self.own.exists())
        self.install(mutant("tracker.py", UNDO_CHECK, "            elif False:\n"))
        try:
            bad = self.py(code)
        finally:
            self.install()
        self.assertTrue((self.own / NOTES / "a.md").is_file(), bad)          # mutant: restored, and the folder made

    def test_a_mkdir_in_a_mapped_folder_that_is_there(self):
        o = self.py(self.MKDIR)
        self.assertEqual(o, [{"op": "mkdir", "created": [f"projects/{ABC}/02 Meetings/New"]}])

    def test_a_copy_source_in_a_mapped_folder(self):
        touch(self.own / "CLAUDE.md", "# ABC\n")
        code = f"""import tracker
try:
    with tracker.CopySource('projects/{ABC}/CLAUDE.md') as s:
        print(json.dumps("ok"))
except tracker.Invalid as e:
    print(json.dumps(str(e)))"""
        good, bad = self.both(code, mutant(
            "tracker.py", "        bases += [(p, Path(os.path.realpath(p))) for p in paths.project_roots().values()]     # #385: a project's own folder\n"))
        self.assertEqual(good, "ok")
        self.assertIn("outside your creaite folder", bad)


class Notes(GuardedCase):
    """Delete note and Move back in a mapped folder: the notes guard knows its notes (and deleted ones), and the move's shape fits."""

    def test_a_mapped_projects_deleted_notes_are_notes(self):
        touch(self.own / NOTES / "Plan.md", "plan\n")
        code = f"""import tracker
print(json.dumps([tracker.in_notes_folder('projects/{ABC}/{NOTES}/Plan.md'),
                  tracker.in_notes_folder('projects/{ABC}/99 Archive/{NOTES}/Plan.md', archived=True),
                  tracker.in_notes_folder('projects/99 Archive/{ABC}/{NOTES}/Plan.md', archived=True),
                  tracker.in_notes_folder('projects/{ABC}/Other/Plan.md', archived=True)]))"""
        good, bad = self.both(code, mutant(
            "tracker.py", "    return paths.in_mapped_notes(c, archived=archived)", "    return False"))
        self.assertEqual(good, [True, True, True, False])
        self.assertEqual(bad[1:3], [False, False])                             # mutant: a deleted note there is unguarded

    def test_delete_note_and_move_back_shapes(self):
        touch(self.own / NOTES / "Plan.md", "plan\n")
        a, b = f"projects/{ABC}/{NOTES}/Plan.md", f"projects/{ABC}/99 Archive/{NOTES}/Plan.md"
        code = f"import reach; print(json.dumps(reach.archive_move_problem({a!r}, {b!r}, 'notes')))"
        good, bad = self.both(code, mutant("reach.py", "    for k, own in all_mapped().items():", "    for k, own in {}.items():"))
        self.assertIsNone(good)
        self.assertIsNotNone(bad)
        touch(self.own / "99 Archive" / NOTES / "Plan.md", "plan\n")
        (self.own / NOTES / "Plan.md").unlink()
        self.assertIsNone(self.py(f"import reach; print(json.dumps(reach.archive_move_problem({b!r}, {a!r}, 'notes_back')))"))


class Permissions(GuardedCase):
    """permissions: the card's settings route checks every project's own folder; additionalDirectories takes the mapped ones."""

    def config_problem(self, mapping):
        return f"""import permissions, paths
before = json.loads(paths.SETTINGS.read_text())
after = json.loads(json.dumps(before)); after['locations']['project_paths'] = {json.dumps(mapping)}
before['locations'].pop('project_paths', None)
print(json.dumps(permissions.settings_problem('config', before, after)))"""

    def test_a_bad_mapping_is_refused_on_the_card_route(self):
        bad_map = {ABC: "~/Work/Acme/Programme/../Programme"}
        good, bad = self.both(self.config_problem(bad_map), mutant(
            "permissions.py", "        return paths.project_paths_problem(before_loc, after_loc)\n", "        return None\n"))
        self.assertIn("..", good)
        self.assertIsNone(bad)
        for m in ({ABC: "~/.ssh/x"}, {ABC: "~/Library/Preferences/x"}, {ABC: OWN, DEF: OWN + "/Sub"}, {ABC: OWN, DEF: OWN}):
            self.assertIsNotNone(self.py(self.config_problem(m)), m)
        self.assertIsNone(self.py(self.config_problem({ABC: OWN})))

    def test_additional_directories_take_the_mapped_folder_and_nothing_wider(self):
        code = """import permissions
print(json.dumps([permissions.preview('settings add dir ~/Work/Acme/Programme').get('ok'),
                  permissions.preview('settings add dir ~/Work/Acme').get('ok'),
                  permissions.preview('settings add dir ~/Library/CloudStorage/OneDrive-TestCo/Documents/Engagements').get('ok'),
                  permissions.broad_rule('Edit(~/Work/Acme/Programme/**)'), permissions.broad_rule('Edit(~/Work/Acme/**)'),
                  permissions.project_dirs()]))"""
        good, bad = self.both(code, mutant("permissions.py", "    for name, p in paths._loc_project_roots(loc).items():",
                                           "    for name, p in {}.items():"))
        self.assertEqual(good[:3], [True, False, True])
        self.assertIsNone(good[3])
        self.assertIsNotNone(good[4])
        self.assertEqual(good[5], ["~/Library/CloudStorage/OneDrive-TestCo/Documents/Engagements", OWN])
        self.assertEqual(bad[:2], [False, False])                              # mutant: the mapped folder is refused
        self.assertIsNotNone(bad[3])

    def test_a_key_spelled_another_way_still_brings_its_folder_and_a_refused_one_never(self):
        """_loc_project_roots hands back the register's spelling; the saved key may differ in case (macOS compares names so)."""
        code = """import permissions, paths
s = json.loads(paths.SETTINGS.read_text())
out = []
for m in (MAPS):
    s['locations']['project_paths'] = m
    out.append(permissions.project_dirs(s['locations']))
print(json.dumps(out))""".replace("MAPS", json.dumps([{ABC.lower(): OWN}, {ABC: "~/.ssh/x"}]))
        got = self.py(code)
        self.assertIn(OWN, got[0])                                            # was dropped when the lookup used the saved key
        self.assertEqual(len(got[1]), 1, got[1])                              # refused on read: only the projects root

    def test_projects_root_command_adds_every_folder(self):
        self.v.run("projects-root", "--why", "read the project documents", script="permissions.py")
        dirs = json.loads((self.v.root / ".claude/settings.json").read_text())["permissions"]["additionalDirectories"]
        self.assertIn(OWN, dirs)
        self.assertIn("~/Library/CloudStorage/OneDrive-TestCo/Documents/Engagements", dirs)
        self.v.run("undo", script="permissions.py")                           # one at a time: the last folder goes first
        dirs = json.loads((self.v.root / ".claude/settings.json").read_text())["permissions"]["additionalDirectories"]
        self.assertNotIn(OWN, dirs)


class OneCard(GuardedCase):
    """Cap's LOW 4: project_paths and additionalDirectories change together, on one card or in one page save."""

    def setUp(self):
        super().setUp()
        self.with_map = json.loads((self.v.root / "system/config/settings.json").read_text())
        self.map({})                                                          # saved without the mapping: the change adds it

    def card(self):
        draft = self.v.root / "system/staging/drafts/settings-new.json"
        draft.parent.mkdir(parents=True, exist_ok=True)
        draft.write_text(json.dumps(self.with_map, indent=2) + "\n", encoding="utf-8")
        return """import live_server, filechange, types
filechange.REQUESTS.mkdir(parents=True, exist_ok=True)
(filechange.REQUESTS / "r-385-1.json").write_text(json.dumps({"op": "edit", "path": "system/config/settings.json",
    "from": "system/staging/drafts/settings-new.json", "why": "ABC's own folder"}))
run = types.SimpleNamespace(id="r-385", was_marked=False, chat=None, session=None, emit=lambda *a, **k: None)
card = live_server.build_card(run)
c = live_server.CARDS[card]
out = []
for it in c["items"]:
    data = json.loads(it["_change"]["data"].decode("utf-8"))
    out.append([it["path"], (data.get("permissions") or {}).get("additionalDirectories")])
print(json.dumps({"items": out, "refused": c["refused"]}))"""

    def test_the_settings_change_brings_its_folder_onto_the_same_card(self):
        good, bad = self.both(self.card(), mutant(
            "live_server.py", "    n = card_dirs(items, refused, n, run.was_marked)     # #385: settings.json's project folders and their permission, one card\n"))
        self.assertEqual([p for p, _ in good["items"]], ["system/config/settings.json", ".claude/settings.json"], good)
        self.assertIn(OWN, good["items"][1][1])
        self.assertEqual([p for p, _ in bad["items"]], ["system/config/settings.json"])   # mutant: they drift apart

    def test_a_page_save_writes_the_matching_folder_too(self):
        text = json.dumps(self.with_map, indent=2) + "\n"
        code = f"""import live_server, paths
class H:
    sent = None
    def send(self, code, body):
        self.sent = (code, body)
h = H()
live_server.Handler.fs_save(h, "write", paths.SETTINGS, "system/config/settings.json", {{"text": {text!r}}})
print(json.dumps([h.sent[1], json.loads(paths.CLAUDE_SETTINGS.read_text())["permissions"].get("additionalDirectories", [])]))"""
        good = self.py(code)
        self.assertTrue(good[0]["ok"])
        self.assertEqual(good[0].get("dirs"), [OWN])
        self.assertIn(OWN, good[1])
        self.map({})
        settings = json.loads((self.v.root / ".claude/settings.json").read_text())
        settings["permissions"]["additionalDirectories"] = [d for d in settings["permissions"].get("additionalDirectories", []) if d != OWN]
        (self.v.root / ".claude/settings.json").write_text(json.dumps(settings, indent=2))
        self.install(mutant("live_server.py", "        if before_loc is not None:                 # #385: the matching additionalDirectories, in this same save\n",
                            "        if False:\n"))
        bad = self.py(code)
        self.assertNotIn(OWN, bad[1])                                          # mutant: settings saved, the folder not


class DenyTools(GuardedCase):
    """The live server's deny list covers a mapped folder's 99 Archive (and the other skipped names)."""

    def test_deny_tools_cover_a_mapped_folders_99_archive(self):
        code = "import live_server; print(json.dumps(live_server.deny_tools()))"
        good, bad = self.both(code, mutant("live_server.py", "for pat in paths.tool_patterns(g)", "for pat in [paths.tool_pattern(g)]"))
        for t in ("Read", "Edit", "Write"):
            self.assertIn(f"{t}({OWN}/**/99 Archive/**)", good)
            self.assertIn(f"{t}({OWN}/**/_Templates/**)", good)
        self.assertIn("Read(~/Library/CloudStorage/OneDrive-TestCo/Documents/Engagements/**/99 Archive/**)", good)
        self.assertNotIn(f"Read({OWN}/**/99 Archive/**)", bad)


class Unmapped(GuardedCase):
    """With no project_paths, the diffs change nothing: the same verdicts as the guarded files without them."""

    def test_same_answers_without_a_mapping(self):
        self.map({})
        code = f"""import reach, tracker, live_server, permissions
root = {str(self.root)!r}
out = [[n, str(r)] for n, r in reach.roots()] + [reach.classify(root + '/{DEF}/99 Archive/x.md', 'create')[0],
       reach.classify(root + '/{DEF}/CLAUDE.md', 'read')[0], live_server.extra_dirs(), live_server.deny_tools()[-6:],
       reach.archive_move_problem('projects/{DEF}', 'projects/99 Archive/{DEF}', 'archive'), permissions.project_dirs()]
print(json.dumps(out))"""
        patched = self.py(code)
        scripts = self.v.root / "system" / "scripts"
        for name in DIFFS:
            text = (REPO / "system" / "scripts" / name).read_text(encoding="utf-8")
            if BASE.get(name) == V269:
                text = subprocess.run(["git", "show", f"{V269}:system/scripts/{name}"], cwd=REPO, capture_output=True, text=True).stdout
            (scripts / name).write_text(text, encoding="utf-8")
        before = self.py(code.replace(", permissions.project_dirs()]", ", None]"))
        self.assertEqual(patched[:-1], before[:-1])
        self.assertEqual(patched[-1], ["~/Library/CloudStorage/OneDrive-TestCo/Documents/Engagements"])


# ===== Cap's Full review of #385 =====
HIDDEN = ("~/.config/git", "~/.ipython/profile_default/startup", "~/.config/autostart", "~/.config/systemd", "~/.oh-my-zsh/custom")
NFC, NFD = "Société", "Société"


class HiddenFolders(GuardedCase):
    """MEDIUM 1: a hidden folder (where things run on their own) is never a project's folder, so never ordinary to ask creaite."""

    def code(self):
        return """import reach, permissions, paths
s = json.loads(paths.SETTINGS.read_text()); before = json.loads(json.dumps(s)); before['locations'].pop('project_paths')
print(json.dumps([reach.classify(V + '/x.cfg', 'create')[0], permissions.settings_problem('config', before, s)]))"""

    def test_each_hidden_folder_is_refused_and_stays_out_of_reach(self):
        for v in HIDDEN:
            (self.home / v[2:]).mkdir(parents=True, exist_ok=True)
            self.map({ABC: v})
            code = self.code().replace("V + ", repr(str(self.home / v[2:])) + " + ")
            good, bad = self.both(code, paths_mutant("    if hidden:                                   # Cap's MEDIUM 1",
                                                     "    if False:                                   # Cap's MEDIUM 1"))
            self.assertNotEqual(good[0], "ordinary", v)
            self.assertIn("hidden folder", good[1] or "", v)
            self.assertEqual(bad[0], "ordinary", v)                           # mutant: ~/.config/git/x.cfg is ask creaite's to write
            self.assertIsNone(bad[1], v)


class UnicodeForm(GuardedCase):
    """MEDIUM 2: reach compares names as macOS does (case and Unicode form), as tracker does: an NFD spelling of a mapped
    folder's 99 Archive, or of its archive slot, is never, like the NFC one; a move is measured from it the same way."""

    def setUp(self):
        super().setUp()
        accented = self.home / "Work" / NFC / "Programme"
        accented.parent.mkdir(parents=True)
        shutil.move(str(self.own), str(accented))
        self.own = accented
        self.map({ABC: f"~/Work/{NFC}/Programme"})
        touch(self.home / "Work" / NFC / "99 Archive" / ABC / "CLAUDE.md")

    def code(self):
        cases = []
        for form in (NFC, NFD):
            base = str(self.home / "Work" / form)
            cases += [(base + "/Programme/99 Archive/x.md", "create"), (base + "/Programme/99 Archive/x.md", "read"),
                      (base + f"/99 Archive/{ABC}/CLAUDE.md", "read")]
        return f"""import reach
from pathlib import Path
print(json.dumps([[reach.classify(p, op)[0] for p, op in {cases!r}],
                  reach._move_parts(Path({str(self.home / "Work" / NFD / "Programme" / "08 Notes")!r}))]))"""

    def test_nfd_and_nfc_spellings_agree(self):
        good, bad = self.both(self.code(), mutant(
            "reach.py", "    a, b = [paths._fold(x) for x in Path(p).parts], [paths._fold(x) for x in Path(base).parts]",
            "    a, b = [x.lower() for x in Path(p).parts], [x.lower() for x in Path(base).parts]"))
        self.assertEqual(good[0], ["never"] * 6)
        self.assertEqual(good[1], [ABC, "08 Notes"])                          # measured from the mapped folder
        self.assertEqual(bad[0][:3], ["never"] * 3)
        self.assertNotIn("never", bad[0][3:])                                 # mutant: the NFD spelling gets through
        self.assertNotEqual(bad[1], [ABC, "08 Notes"])


class DroppedSlot(GuardedCase):
    """LOW 2: a mapping dropped on read (its folder replaced by a symlink) keeps its archive slot never."""

    def test_the_slot_stays_never(self):
        touch(self.slot() / "CLAUDE.md")
        elsewhere = self.home / "Elsewhere" / "Programme"
        elsewhere.parent.mkdir()
        shutil.move(str(self.own), str(elsewhere))
        self.own.symlink_to(elsewhere)
        code = f"""import reach, paths
print(json.dumps([sorted(paths.project_roots()), reach.classify({str(self.slot() / 'CLAUDE.md')!r}, 'read')[0]]))"""
        good, bad = self.both(code, mutant("reach.py", "    for own in [*all_mapped().values(), *raw.values()]:",
                                           "    for own in [*all_mapped().values()]:"))
        self.assertEqual(good, [[], "never"])                                 # dropped, and its slot still never
        self.assertNotEqual(bad[1], "never")                                  # mutant: the slot's archive is reachable


class NulByte(GuardedCase):
    """LOW 5 in reach: a NUL byte in a hand-edited value is dropped from _loc_raw_roots too, so skipped_below never raises."""

    def test_reach_still_answers(self):
        self.map({ABC: OWN, DEF: "~/Work/Dig\0ital"})
        code = f"""import reach
try:
    print(json.dumps(reach.classify({str(self.own / 'CLAUDE.md')!r}, 'read')[0]))
except ValueError as e:
    print(json.dumps(str(e)))"""
        good, bad = self.both(code, paths_mutant(' and "\\0" not in value\n', "\n"))
        self.assertEqual(good, "ordinary")
        self.assertIn("null byte", bad)                                       # mutant: every check raises


class StackOn292And261(unittest.TestCase):
    """MEDIUM 3: test_minutes_by_others_filing's scratch (which test_tracker_inode_hold uses) reverses the landed #292 wording
    diff, the #261 inode-hold diff and #232 E1 on a copy of tracker.py. With 385-tracker.diff in tracker.py those must still
    reverse: 385's safe_path and check_move hunks leave the #292 hunks' context lines as they are."""

    OLD = "7be09928"                       # the 385-tracker.diff before Cap's Full review: its safe_path hunk broke #292's -R

    def reverse_all(self, tracker_text):
        d = Path(tempfile.mkdtemp(prefix="creaite-385s-"))
        try:
            f = d / "system" / "scripts" / "tracker.py"
            f.parent.mkdir(parents=True)
            f.write_text(tracker_text, encoding="utf-8")
            steps = [["git", "apply", "-R", str(REPO / "dev/proposals/292-tracker/tracker.diff")],
                     ["patch", "-p1", "-s", "-R", "-i", str(REPO / "dev/proposals/261-inode-gap/tracker-inode.py.diff")],
                     ["patch", "-p0", "-s", "-R", "-i", str(REPO / "dev/proposals/intake-232/E1-tracker.rebased-on-280.diff")]]
            for args in steps:
                r = subprocess.run(args, cwd=d, capture_output=True, text=True)
                if r.returncode != 0:
                    return f"{args[0]} {Path(args[-1]).name}: {r.stdout}{r.stderr}"
            return None
        finally:
            shutil.rmtree(d, True)

    def patched_by(self, diff_text):
        """V269's tracker.py (the base the diffs are cut against, with #292, #261 and E1 in) with `diff_text` applied."""
        r = subprocess.run(["git", "show", f"{V269}:system/scripts/tracker.py"], cwd=REPO, capture_output=True, text=True)
        if r.returncode != 0:
            self.skipTest(f"{V269} not in this clone")
        tree = r.stdout
        with tempfile.NamedTemporaryFile("w", suffix=".diff", delete=False) as fh:
            fh.write(diff_text)
        try:
            ok, text = _apply(tree, {"name": "tracker.py", "path": Path(fh.name)})
        finally:
            os.unlink(fh.name)
        self.assertTrue(ok)
        return text

    @needs_diffs
    def test_the_older_tracker_diffs_still_reverse_with_385_in(self):
        self.assertIsNone(self.reverse_all(PATCHED["tracker.py"]))

    def test_the_diff_before_the_review_broke_them(self):
        r = subprocess.run(["git", "show", f"{self.OLD}:dev/proposals/385/385-tracker.diff"], cwd=REPO, capture_output=True, text=True)
        if r.returncode != 0:
            self.skipTest(f"{self.OLD} not in this clone")
        why = self.reverse_all(self.patched_by(r.stdout)) or ""
        self.assertTrue(why.startswith("git tracker.diff") and "patch failed" in why, why)     # the #292 wording diff's -R


class MappedEnds(GuardedCase):
    """LOW 1: an archive or a restore with a mapped project at either end goes exactly to or from its slot, even in reach."""

    CODE = f"""import tracker
out = []
for s, d, k in [('projects/{ABC}', 'projects/99 Archive/Zeta', 'archive'), ('projects/99 Archive/Zeta', 'projects/{ABC}', 'restore'),
                ('projects/{ABC}', 'projects/99 Archive/{ABC}', 'archive'), ('projects/{DEF}', 'projects/99 Archive/{DEF}', 'archive')]:
    out.append(tracker._outside_end_problem(s, d, k))
try:
    tracker.check_move({{"op": "move", "from": 'projects/{ABC}', "to": 'projects/99 Archive/Zeta'}}, {{"archive": "archive"}})
    out.append(None)
except tracker.Invalid as e:
    out.append(str(e))
print(json.dumps(out))"""

    def test_only_its_own_slot(self):
        good, bad = self.both(self.CODE, mutant("tracker.py", "    if not _mapped_end(src, dst, a, b, kind, mapping) and \\\n",
                                                "    if True and \\\n"))
        self.assertIn("isn't a project's own archive place", good[0] or "")
        self.assertIn("isn't a project's own archive place", good[1] or "")
        self.assertEqual(good[2:4], [None, None])
        self.assertIsNotNone(good[4])
        self.assertEqual(bad[:2], [None, None])                               # mutant: ABC archived under another name


class UndoMissingBase(GuardedCase):
    """LOW 3: an undo of a write or a draft status line into a mapped folder that isn't there skips, as a remove does."""

    def code(self, rec):
        return f"""import tracker
report = []
try:
    tracker.reverse_file_ops([{rec!r}], report)
    print(json.dumps(report))
except OSError as e:
    print(json.dumps(type(e).__name__))"""

    def check(self, rec, line):
        touch(self.v.root / "system" / "backups" / "files" / "1" / "a.md", "a\n")
        shutil.move(str(self.own), str(self.home / "Unmounted"))
        good, bad = self.both(self.code(rec), mutant("tracker.py", line, line.replace("elif ", "elif False and ", 1)))
        self.assertTrue(isinstance(good, list) and any("isn't there" in x for x in good), good)
        self.assertFalse(self.own.exists())
        self.assertEqual(bad, "FileNotFoundError")                            # mutant: it raises (or would make the folder)

    def test_a_write(self):
        self.check({"op": "write", "path": f"projects/{ABC}/{NOTES}/a.md", "hash": "0", "previous": "a\n"},
                   '            elif rec["previous"] is not None and _missing_base(p) is not None:    # #385 (Cap\'s LOW 3): as a remove\n')

    def test_a_status_line(self):
        self.check({"op": "status", "path": f"projects/{ABC}/{NOTES}/a.md", "hash": "0", "previous": "system/backups/files/1/a.md"},
                   "            elif _missing_base(p) is not None:    # #385 (Cap's LOW 3): never made on the laptop's disk\n")


class AdditionalDirs(GuardedCase):
    """MEDIUM 4: additionalDirectories never takes a never-list folder or the home folder; on a card that changes locations, a
    .claude/settings.json change adds only the card's own folders. LOW 7: projects-root numbers by next_id. LOW 8: a failed second
    write says so; a folder no longer honoured is taken out on a sync."""

    PROBLEM = """import permissions, paths
s = json.loads(paths.CLAUDE_SETTINGS.read_text())
out = []
for d in DIRS:
    a = json.loads(json.dumps(s)); a.setdefault('permissions', {}).setdefault('additionalDirectories', []).append(d)
    out.append(permissions.settings_problem('claude', s, a))
print(json.dumps(out))"""

    def test_never_list_and_home_refused_whatever_the_card(self):
        code = self.PROBLEM.replace("DIRS", json.dumps(["~/.ssh", "~", str(self.home), "~/Library", OWN]))
        good, bad = self.both(code, mutant(
            "permissions.py", "        if d not in (bp.get(\"additionalDirectories\") or []) and never_folder(d):     # #385 (Cap's Full review, MEDIUM 4)\n",
            "        if False:\n"))
        self.assertTrue(all(x for x in good[:4]), good)
        self.assertIsNone(good[4])
        self.assertEqual(bad[:4], [None] * 4)                                 # mutant: ~/.ssh and ~ on approval

    def card(self, extra):
        with_map = json.loads((self.v.root / "system/config/settings.json").read_text())
        self.map({})
        drafts = self.v.root / "system/staging/drafts"
        drafts.mkdir(parents=True, exist_ok=True)
        (drafts / "settings-new.json").write_text(json.dumps(with_map, indent=2) + "\n", encoding="utf-8")
        claude = json.loads((self.v.root / ".claude/settings.json").read_text())
        claude.setdefault("permissions", {}).setdefault("additionalDirectories", []).append(extra)
        (drafts / "claude-new.json").write_text(json.dumps(claude, indent=2) + "\n", encoding="utf-8")
        return """import live_server, filechange, types
filechange.REQUESTS.mkdir(parents=True, exist_ok=True)
(filechange.REQUESTS / "r-385-1.json").write_text(json.dumps({"op": "edit", "path": "system/config/settings.json",
    "from": "system/staging/drafts/settings-new.json", "why": "ABC's own folder"}))
(filechange.REQUESTS / "r-385-2.json").write_text(json.dumps({"op": "edit", "path": ".claude/settings.json",
    "from": "system/staging/drafts/claude-new.json", "why": "a folder"}))
emitted = {}
run = types.SimpleNamespace(id="r-385", was_marked=False, chat=None, session=None, emit=lambda *a, **k: emitted.update(k))
card = live_server.build_card(run)
c = live_server.CARDS[card] if card else {"items": [], "refused": emitted.get("refused", [])}
out = []
for it in c["items"]:
    data = json.loads(it["_change"]["data"].decode("utf-8"))
    out.append([it["path"], (data.get("permissions") or {}).get("additionalDirectories")])
print(json.dumps({"items": out, "refused": c["refused"]}))"""

    def test_a_card_with_a_locations_change_adds_only_its_own_folders(self):
        (self.home / "Work" / "Other").mkdir(parents=True)
        good, bad = self.both(self.card("~/Work/Other"), mutant("live_server.py", "    if wider:", "    if False:"))
        self.assertEqual(good["items"], [], good)                             # neither offered
        self.assertTrue(any("isn't the projects folder or a project's own folder" in r for r in good["refused"]), good)
        self.assertIn("~/Work/Other", [d for _, ds in bad["items"] for d in (ds or [])])   # mutant: it rides along

    def test_ask_creaites_own_ssh_never_rides_along(self):
        got = self.py(self.card("~/.ssh"))
        self.assertNotIn("~/.ssh", [d for _, ds in got["items"] for d in (ds or [])], got)

    def test_projects_root_numbers_never_repeat(self):
        lines = "".join(json.dumps({"id": i, "op": op, "kind": "dir", "rule": f"~/Work/R{i}"}) + "\n"
                        for i, op in ((1, "add"), (2, "add"), (3, "remove"), (4, "remove")))
        code = f"""import permissions, paths
paths.PERMISSIONS_LOG.parent.mkdir(parents=True, exist_ok=True)
paths.PERMISSIONS_LOG.write_text({lines!r})
s = json.loads(paths.CLAUDE_SETTINGS.read_text()); s.setdefault('permissions', {{}})['additionalDirectories'] = []
paths.CLAUDE_SETTINGS.write_text(json.dumps(s))
permissions.cmd_projects_root('read the project documents', 'test')
print(json.dumps([e['id'] for e in permissions.log_entries()]))"""
        good, bad = self.both(code, mutant(
            "permissions.py", "    n = next_id()                                  # #385 (Cap's LOW 7): never a number already used\n",
            "    n = len([e for e in log_entries() if e.get(\"op\") == \"add\"]) + 1\n"))
        self.assertEqual(len(good), len(set(good)), good)
        self.assertNotEqual(len(bad), len(set(bad)), bad)                     # mutant: 3 and 4 again

    def test_a_failed_second_write_is_the_saves_answer(self):
        with_map = json.loads((self.v.root / "system/config/settings.json").read_text())
        self.map({})
        text = json.dumps(with_map, indent=2) + "\n"
        code = f"""import live_server, paths
class H:
    sent = None
    def send(self, code, body):
        self.sent = (code, body)
paths.CLAUDE_SETTINGS.write_text("{{ not json")
h = H()
live_server.Handler.fs_save(h, "write", paths.SETTINGS, "system/config/settings.json", {{"text": {text!r}}})
print(json.dumps(h.sent[1]))"""
        good, bad = self.both(code, mutant(
            "live_server.py", "            return self.send(200, {\"ok\": \"message\" not in follow, **follow})     # Cap's LOW 8: a failed second write says so\n",
            "            return self.send(200, {\"ok\": True, **follow})\n"))
        self.assertFalse(good["ok"])
        self.assertIn("weren't updated to match", good["message"])
        self.assertTrue(bad["ok"])                                            # mutant: ok, and the two have drifted apart

    def test_a_folder_no_longer_honoured_is_taken_out_on_a_sync(self):
        claude = json.loads((self.v.root / ".claude/settings.json").read_text())
        claude.setdefault("permissions", {})["additionalDirectories"] = ["~/Library/CloudStorage/OneDrive-TestCo/Documents/Engagements", OWN]
        (self.v.root / ".claude/settings.json").write_text(json.dumps(claude, indent=2))
        elsewhere = self.home / "Elsewhere" / "Programme"
        elsewhere.parent.mkdir()
        shutil.move(str(self.own), str(elsewhere))
        self.own.symlink_to(elsewhere)                                       # dropped on read: no longer ABC's folder
        code = """import permissions, paths
loc = paths.locations()
print(json.dumps([permissions.sync_project_dirs(loc, dict(loc, portfolio=loc.get('portfolio')), 'test'),
                  json.loads(paths.CLAUDE_SETTINGS.read_text())['permissions']['additionalDirectories']]))"""
        good, bad = self.both(code, mutant(
            "permissions.py", "    old = project_dirs(before_loc)[1:] + _own_folder_dirs(before_loc) + _own_folder_dirs(after_loc)    # Cap's LOW 8\n",
            "    old = project_dirs(before_loc)[1:]\n"))
        self.assertEqual(good[0], [OWN])
        self.assertNotIn(OWN, good[1])
        self.assertEqual(bad[0], [])                                          # mutant: the symlink's target stays readable

    def test_an_archived_projects_folder_is_taken_out_on_a_sync(self):
        claude = json.loads((self.v.root / ".claude/settings.json").read_text())
        claude.setdefault("permissions", {})["additionalDirectories"] = [OWN]
        (self.v.root / ".claude/settings.json").write_text(json.dumps(claude, indent=2))
        reg = self.root / "_Portfolio" / "project-register.md"
        reg.write_text("\n".join(ln for ln in reg.read_text().splitlines() if not ln.startswith("| ABC |")) + "\n")
        got = self.py("""import permissions, paths
loc = paths.locations()
print(json.dumps(permissions.sync_project_dirs(loc, loc, 'test')))""")
        self.assertEqual(got, [OWN])


class SaveIfUnchanged(GuardedCase):
    """LOW 6: the page's expect_text write of settings.json gets the notes-folder check and the matching additionalDirectories."""

    def code(self, text):
        return f"""import live_server, paths
s = json.loads(paths.SETTINGS.read_text()); s['locations']['project_paths'] = {{}}
paths.SETTINGS.write_text(json.dumps(s, indent=2))
c = json.loads(paths.CLAUDE_SETTINGS.read_text()); c.setdefault('permissions', {{}})['additionalDirectories'] = []
paths.CLAUDE_SETTINGS.write_text(json.dumps(c, indent=2))
class H:
    sent = None
    def send(self, code, body):
        self.sent = (code, body)
h = H()
live_server.Handler.fs_write_if_unchanged(h, paths.SETTINGS, "system/config/settings.json", {{"text": {text!r}}},
                                          paths.SETTINGS.read_text(encoding="utf-8"))
print(json.dumps([h.sent[1], json.loads(paths.CLAUDE_SETTINGS.read_text())["permissions"].get("additionalDirectories", [])]))"""

    def test_the_folder_follows(self):
        with_map = json.loads((self.v.root / "system/config/settings.json").read_text())
        self.map({})
        good, bad = self.both(self.code(json.dumps(with_map, indent=2) + "\n"), mutant(
            "live_server.py", "        if before_loc is not None:                 # #385 (Cap's LOW 6): the matching additionalDirectories, in this same save\n",
            "        if False:\n"))
        self.assertTrue(good[0]["ok"])
        self.assertIn(OWN, good[1])
        self.assertNotIn(OWN, bad[1])                                         # mutant: saved, the folder not

    def test_a_notes_folder_clash_is_never_saved(self):
        s = json.loads((self.v.root / "system/config/settings.json").read_text())
        folders = s["locations"].setdefault("folders", {})
        minutes = folders.get("minutes") or "02 Meetings/Minutes"
        s["locations"]["folders"] = dict(folders, minutes=minutes, notes=minutes)
        good, bad = self.both(self.code(json.dumps(s, indent=2) + "\n"), mutant(
            "live_server.py", "        if clash:\n            return self.send(200, {\"ok\": False, \"message\": clash})\n        before_loc",
            "        if False:\n            return self.send(200, {\"ok\": False, \"message\": clash})\n        before_loc"))
        self.assertFalse(good[0]["ok"])
        self.assertTrue(bad[0]["ok"])                                         # mutant: the clash is saved


if __name__ == "__main__":
    unittest.main()
