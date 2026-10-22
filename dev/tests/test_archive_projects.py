"""BL-09, #252: archive and restore whole projects into 99 Archive/ (the old _Archive and zz Archive are still read for one release).

Run: python3 dev/tests/test_archive_projects.py     (quick tier: no Chrome)

What is covered here (the parts that need no schema change):
- all three names (99 Archive, _Archive, zz Archive) are never listed, indexed, read or written; ask creaite can't read, write
  or move anything in any of them, whatever the operation, and filechange.py can't move a folder or file into one;
- reach.archive_move_problem is the one exception: whole-folder archive and restore only, never a file, never
  outside the projects folder, never onto something that exists; tracker.py's `move` file operation is refused without it;
- Health says nothing about old archive folder names, propose.py has no rename command, and a project made from a skeleton that
  still holds _Archive or zz Archive gets 99 Archive (no migration: Alan renames his own folders);
- the update adds 99 Archive to a saved never_index and removes or renames nothing;
- paths.resolve maps an archived project's stored projects/<folder>/… into 99 Archive/<folder>/… (stored paths never change).
Everything is fictional and temporary (a fake home and OneDrive root; see test_onedrive_projects.py).
Old-name restore, move back and the dual reading are in test_archive_99.py.
"""
import json
import shutil
import sqlite3
import subprocess
import sys
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_onedrive_projects import OneDriveCase, touch  # noqa: E402
from test_tracker import Vault  # noqa: E402

NEW, OLDS = "99 Archive", ("_Archive", "zz Archive")


class OneDriveArchive(OneDriveCase):
    """With the projects in a OneDrive-style root: engagements with no archive folder yet."""

    def setUp(self):
        super().setUp()
        for code in ("ABC", "DEF"):                     # the engagements as they start: no archive folder yet
            shutil.rmtree(self.eng(code, NEW))

    def run_script(self, script, *args, ok=True):
        r = self.v.run(*args, script=script, ok=ok)
        return r

    def stage(self, spec, name="spec.json"):
        f = self.v.root / "system/staging/drafts" / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(spec), encoding="utf-8")
        return self.run_script("propose.py", "stage", str(f))

    # ── all three names are skipped, by everything ──
    def test_all_three_names_are_never_listed_or_indexed(self):
        for name in (NEW, *OLDS):
            touch(self.eng("ABC", name, f"{name} plan.docx"))
        touch(self.eng("ABC", "03 Delivery", "Design", "Plan.docx"))
        o = self.py("import paths, tracker; print(json.dumps([[str(f) for f in paths.document_files('ABC')], "
                    "[str(f) for f, _, _ in tracker.index_files()], paths.never_index(), paths.skipped_names(), paths.never_index_patterns()]))")
        for listed in (o[0], o[1]):
            self.assertTrue(any(s.endswith("Plan.docx") and "Design" in s for s in listed))
            self.assertFalse(any(f"/{n}/" in s for s in listed for n in (NEW, *OLDS)), listed)
        self.assertEqual(o[2], ["99 Archive", "_Archive", "zz Archive", "_Templates", "99 System"])   # the new default, old names added
        self.assertEqual(o[3], o[2])                                # skipped whatever the setting says
        self.assertEqual(o[4], ["**/99 Archive/**", "**/_Archive/**", "**/_Templates/**", "**/99 System/**"])   # zz Archive: guarded, not named

    def test_ask_creaite_can_never_read_write_or_move_anything_there(self):
        for name in (NEW, *OLDS):
            f = touch(self.eng("ABC", name, "old.md"))
            for op in ("read", "create", "change", "move", "delete"):
                with self.subTest(name=name, op=op):
                    got = self.py(f"import reach; print(json.dumps(reach.classify({str(f)!r}, {op!r})))")
                    self.assertEqual(got[0], "never")
            top = self.root / NEW / "Example Programme" / "a.md"
            self.assertEqual(self.py(f"import reach; print(json.dumps(reach.classify({str(top)!r}, 'create')))")[0], "never")
        note = touch(self.eng("ABC", "03 Delivery", "Design", "a.md"))
        r = self.run_script("filechange.py", "move", str(note), str(self.eng("ABC", NEW, "a.md")), "--why", "x", ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertTrue(note.exists() and not self.eng("ABC", NEW, "a.md").exists())

    # ── the one exception: reach.archive_move_problem ──
    def test_only_whole_folder_moves_into_or_out_of_archive(self):
        touch(self.eng("ABC", "zz Archive", "x.md"))
        touch(self.root / NEW / "Old Engagement" / "y.md")
        cases = {   # (from, to, kind): allowed?
            ("projects/Example Programme", "projects/99 Archive/Example Programme", "archive"): True,
            ("projects/99 Archive/Old Engagement", "projects/Old Engagement", "restore"): True,
            ("projects/Example Programme", "projects/99 Archive/Example Programme", "restore"): False,       # the wrong kind
            ("projects/Example Programme/02 Meetings", "projects/99 Archive/02 Meetings", "archive"): False,  # not a project folder
            ("projects/Example Programme/zz Archive/x.md", "projects/99 Archive/x.md", "archive"): False,     # a file, inside
            ("projects/Example Programme", "projects/99 Archive/Old Engagement", "archive"): False,           # onto one that exists
            ("projects/_Templates", "projects/99 Archive/_Templates", "archive"): False,
            ("projects/_portfolio", "projects/99 Archive/Portfolio", "archive"): False,
            ("projects/Example Programme", "projects/../Example Programme", "archive"): False,
            ("projects/Example Programme", "projects/99 Archive/Example Programme", "delete"): False,
            ("projects/Example Programme/99 Archive", "projects/Example Programme/Other", "archive"): False,
        }
        for (a, b, kind), ok in cases.items():
            with self.subTest(a=a, b=b, kind=kind):
                why = self.py(f"import reach; print(json.dumps(reach.archive_move_problem({a!r}, {b!r}, {kind!r})))")
                self.assertEqual(why is None, ok, why)

    def test_a_move_without_its_kind_or_outside_the_shapes_is_refused_by_apply(self):
        touch(self.eng("ABC", "zz Archive", "x.md"))
        for blk in ({"file_ops": [{"op": "move", "from": "projects/Example Programme/zz Archive",
                                   "to": "projects/Example Programme/99 Archive"}]},                       # no "archive" kind
                    {"archive": "rename", "file_ops": [{"op": "move", "from": "projects/Example Programme/02 Meetings",
                                                        "to": "projects/Example Programme/99 Archive"}]}):
            with self.subTest(blk=blk):
                p = self.v.propose("move", [], file_changes={"title": "x", "file_changes_decision": "approved", **blk})
                r = self.v.run("apply", ok=False)
                self.assertNotEqual(r.returncode, 0)
                self.assertIn("move:", r.stdout)
                self.assertTrue(self.eng("ABC", "zz Archive").is_dir())
                p.unlink()

    # ── Health: nothing about old archive folder names; no rename command (Alan, 20-10-2026) ──
    def doctor(self):
        r = self.v.run("--read-only", "--json", script="doctor.py", ok=False)
        return {c["id"]: c for c in json.loads(r.stdout.strip().splitlines()[-1])["checks"]}

    def test_health_does_not_mention_old_archive_folders_and_there_is_no_rename_command(self):
        touch(self.eng("ABC", "zz Archive", "Old plan.docx"), "plan")
        touch(self.eng("DEF", "_Archive", "Notes", "n.md"), "n")
        checks = self.doctor()
        self.assertNotIn("old_archive_folders", checks)
        self.assertNotIn("skeleton_archive", checks)
        self.assertFalse(any("Archive" in c["detail"] and "rename" in c["detail"].lower() for c in checks.values()), checks)
        r = self.run_script("propose.py", "old-archives", ok=False)
        self.assertNotEqual(r.returncode, 0)                            # an unknown command: nothing is renamed for Alan
        self.assertEqual(self.eng("ABC", "zz Archive", "Old plan.docx").read_text(), "plan")
        self.assertEqual(self.eng("DEF", "_Archive", "Notes", "n.md").read_text(), "n")
        h = self.py("import health_fixes; print(json.dumps(sorted(health_fixes.FIXES)))")
        self.assertNotIn("old_archive", h)

    # ── the skeleton ──
    def test_a_skeleton_holding_an_old_archive_name_gives_a_new_project_99_archive(self):
        for old in OLDS:
            sk = self.root / "_Templates/_Skeleton"
            (sk / "99 Archive").rename(sk / old) if (sk / "99 Archive").exists() else None
            with self.subTest(old=old):
                spec = json.loads(self.run_script("propose.py", "new-project", "--code", "GHI", "--name", "Growth Hub").stdout)
                paths_made = [o.get("path") or o.get("to") for o in spec["file_changes"]["file_ops"]]
                self.assertIn("projects/Growth Hub/99 Archive", paths_made)
                self.assertFalse(any(o in p.split("/") for p in paths_made for o in OLDS), paths_made)
                self.assertTrue((sk / old).is_dir())                    # creaite never writes in _Templates
                self.assertNotIn("skeleton_archive", self.doctor())      # and Health has no complaint about it
                (sk / old).rename(sk / "99 Archive")

    # ── stored paths never change ──
    def test_an_archived_projects_stored_paths_resolve_into_archive(self):
        f = touch(self.eng("DEF", "02 Meetings", "Minutes", "2026-10-01 Steering.docx"))
        stored = "projects/Digital Enablement/02 Meetings/Minutes/2026-10-01 Steering.docx"
        (self.root / NEW).mkdir()
        self.eng("DEF").rename(self.root / NEW / "Digital Enablement")
        o = self.py(f"import paths, reach; print(json.dumps([str(paths.resolve({stored!r})), "
                    f"str(paths.resolve({stored!r}, archived=False)), reach.classify({stored!r}, 'read')]))")
        self.assertEqual(o[0], str(self.root / NEW / "Digital Enablement" / "02 Meetings/Minutes/2026-10-01 Steering.docx"))
        self.assertEqual(o[1], str(f))                                      # where it was; not there now
        self.assertEqual(o[2][0], "never")                                  # ask creaite still can't read it


class VaultArchive(unittest.TestCase):
    """With the projects in the vault: projects/99 Archive (and the old names) is never a project."""

    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        self.abc = next(d for d in (self.v.root / "projects").iterdir() if d.name.startswith("ABC "))

    def tearDown(self):
        self.v.cleanup()

    def test_projects_archive_is_never_a_project_folder(self):
        for name in (NEW, *OLDS):
            touch(self.v.root / "projects" / name / "OLD Old Project" / "minutes" / "m.md")
        src = f"import sys, json; sys.path.insert(0, {str(self.v.root / 'system/scripts')!r}); import paths\n" \
              "print(json.dumps([c for c, _ in paths.project_folders()]))"
        r = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True)
        self.assertEqual(json.loads(r.stdout), ["ABC", "_portfolio"])


class UpdateAddsTheSetting(unittest.TestCase):
    """The update adds 99 Archive to a saved locations.never_index and removes or renames nothing (#252)."""

    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        self.cfg = self.v.root / "system/config/settings.json"

    def tearDown(self):
        self.v.cleanup()

    def migrate(self, settings):
        src = (f"import sys, json; sys.path.insert(0, {str(self.v.root / 'system/scripts')!r}); import update\n"
               f"text, added = update.merged_changes('system/config/settings.json', {settings!r}, "
               f"open({str(self.v.root / 'system/templates/settings-defaults.json')!r}).read())\n"
               "print(json.dumps([json.loads(text), added, update.migration_note()]))")
        r = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_99_archive_is_added_and_nothing_is_renamed_or_removed(self):
        data = json.loads(self.cfg.read_text())
        data["locations"] = {"projects_root": "~/x", "never_index": ["zz Archive", "_Archive", "_Templates", "Private", "99 System"],
                             "offsite_backup": "_Portfolio/99 System/creaite backups"}
        data.setdefault("dashboard", {})["palette"] = "creaite"
        after, added, note = self.migrate(json.dumps(data))
        self.assertEqual(after["locations"]["never_index"], ["99 Archive", "zz Archive", "_Archive", "_Templates", "Private", "99 System"])
        self.assertIn("locations.never_index", added)
        self.assertIn("99 Archive is added", note)
        self.assertIn("No folder is renamed", note)
        self.assertEqual(after["locations"]["projects_root"], "~/x")
        again, added2, _ = self.migrate(json.dumps(after))
        self.assertEqual(again["locations"]["never_index"], after["locations"]["never_index"])
        self.assertNotIn("locations.never_index", added2)                  # nothing the second time

    def test_an_older_list_gets_99_system_and_99_archive(self):
        data = json.loads(self.cfg.read_text())
        data["locations"] = {"never_index": ["zz Archive", "_Templates"]}
        after, added, note = self.migrate(json.dumps(data))
        self.assertEqual(after["locations"]["never_index"], ["99 Archive", "zz Archive", "_Templates", "99 System"])
        self.assertEqual(added.count("locations.never_index"), 1)
        self.assertIn("99 System is added", note)

    def test_tidy_adds_it_in_a_vault_and_logs_the_old_value(self):
        data = json.loads(self.cfg.read_text())
        data["locations"] = {"never_index": ["_Archive", "_Templates", "99 System"]}
        self.cfg.write_text(json.dumps(data, indent=2))
        self.v.run("tidy", script="update.py")
        self.assertEqual(json.loads(self.cfg.read_text())["locations"]["never_index"], ["99 Archive", "_Archive", "_Templates", "99 System"])
        log = [json.loads(ln) for ln in (self.v.root / "system/config/settings-log.jsonl").read_text().splitlines()]
        row = next(r for r in log if r["key"] == "locations.never_index")
        self.assertEqual(row["old"], ["_Archive", "_Templates", "99 System"])


# ── Part 2: archive and restore a whole project (the archived flags, BL-09 schema) ─────────────────────────────────────────

def items_for_abc(src):
    """An open and a closed action, a closed risk, a made decision and a planned milestone for ABC, from one source file."""
    a = {"project": "ABC", "owner": "Alan Carter", "raised": "2026-10-01", "source": src}
    return [{"n": 1, "op": "new", "table": "actions", "values": {**a, "description": "Send revised SOW to client"}},
            {"n": 2, "op": "new", "table": "actions", "values": {**a, "description": "Book the zebrafish workshop",
                                                                   "status": "Closed", "closed": "2026-10-02"}},
            {"n": 3, "op": "new", "table": "raid", "values": {**a, "type": "Risk", "description": "Data access may slip",
                                                                "status": "Closed", "closed": "2026-10-03"}},
            {"n": 4, "op": "new", "table": "decisions", "values": {"project": "ABC", "decision": "Go with the pilot",
                                                                     "date": "2026-10-01", "status": "Made", "source": src}}]


class ArchiveRestore(unittest.TestCase):
    """Archive and restore with the projects in the vault: the folder, the register, the items and search round-trip exactly."""

    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        self.scripts = self.v.root / "system/scripts"
        self.abc = next(d for d in (self.v.root / "projects").iterdir() if d.name.startswith("ABC "))
        self.mins = touch(self.abc / "minutes" / "2026-10-01 Steering.md", "Steering. We discussed the quokka migration plan.\n")
        src = f"projects/{self.abc.name}/minutes/2026-10-01 Steering.md"
        items = [dict(i, match="strong", flags=[], decision="approved") for i in items_for_abc(src)]
        self.v.propose("seed", items)
        self.v.run("apply")
        self.reg = paths_of(self.v.root)["register"]

    def tearDown(self):
        self.v.cleanup()

    def py(self, code):
        src = f"import sys, json; sys.path.insert(0, {str(self.scripts)!r})\n{code}"
        r = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True, cwd=self.v.root)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def state(self):
        """Every data row, the register, the project's files and what search finds: what must round-trip exactly."""
        rows = {t: self.v.rows(t) for t in ("projects", "actions", "raid", "decisions", "milestones", "workstreams")}
        files = sorted(str(f.relative_to(self.v.root)) for f in (self.v.root / "projects").rglob("*") if f.is_file())
        return rows, self.reg.read_text(encoding="utf-8"), files, self.found("quokka"), self.found("zebrafish")

    def found(self, word):
        out = self.v.run("query", word, script="search.py").stdout
        groups = json.loads(out)["groups"]
        return {g: sorted((r.get("id") or r.get("path") or r.get("title"), r.get("archived", False), r.get("meta", ""))
                          for r in rs) for g, rs in groups.items() if rs}

    def stage(self, *args):
        spec = self.v.run(*args, script="propose.py").stdout
        f = self.v.root / "system/staging/drafts/a.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(spec, encoding="utf-8")
        return self.v.run("stage", str(f), script="propose.py").stdout

    def archive(self):
        out = self.stage("archive", "ABC", "--cancel-open")
        self.v.run("apply")
        return out

    def test_open_items_are_listed_and_nothing_is_archived_with_one_open(self):
        r = self.v.run("archive", "ABC", script="propose.py", ok=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("1 open item(s): ABC-A-001 Send revised SOW to client", r.stderr)
        self.assertIn("Cancel them all and archive (--cancel-open), or stop", r.stderr)
        listed = json.loads(self.v.run("archive", "ABC", "--open", script="propose.py").stdout)
        self.assertEqual([(o["table"], o["id"]) for o in listed["open"]], [("actions", "ABC-A-001")])
        bad = {"items": [{"n": 1, "op": "archive", "table": "projects", "id": "ABC", "decision": "approved"}]}   # no folder move
        self.v.propose("bad", bad["items"])
        r = self.v.run("apply", ok=False)
        self.assertIn("Held in Review, not applied: proposed-bad.json item 1: Example Programme has 1 open item(s)", r.stdout)  # #280
        self.assertEqual(self.v.rows("projects")[0]["archived"], 0)

    def test_archive_then_undo_round_trips_exactly(self):
        before = self.state()
        preview = self.archive()
        self.assertIn("ABC-A-001 · Status: Open → Cancelled", preview)
        self.assertIn("Archive Example Programme (ABC)", preview)
        self.assertIn(f"Move folder projects/{self.abc.name}/ → projects/99 Archive/{self.abc.name}/", preview)
        moved = self.v.root / "projects" / "99 Archive" / self.abc.name
        self.assertTrue(moved.is_dir() and not self.abc.exists())                    # the folder, whole
        reg = self.reg.read_text(encoding="utf-8")
        projects = reg.split("## Projects")[1].split("## ")[0]
        self.assertNotIn("| ABC |", projects)                                        # the row left Projects…
        self.assertRegex(reg.split("## Retired codes")[1], r"\| ABC \| Example Programme \| \d\d-\d\d-\d{4} \(archived\) \|")
        p = self.v.rows("projects")[0]
        self.assertEqual((p["active"], p["archived"]), (0, 1))
        for t in ("actions", "raid", "decisions"):
            self.assertTrue(all(r["archived"] == 1 for r in self.v.rows(t)), t)       # every item flagged
        self.assertEqual(self.v.rows("actions")[0]["status"], "Cancelled")
        self.v.run("undo")
        self.assertEqual(self.state(), before)                                       # rows, register, files, search

    def test_archived_items_leave_the_views_and_stay_searchable(self):
        self.archive()
        o = self.py("import sqlite3, tracker, paths, build_dashboard\n"
                    "con = tracker.hide_archived(sqlite3.connect(f'file:{paths.DB}?mode=ro', uri=True))\n"
                    "d = build_dashboard.collect()\n"
                    "print(json.dumps([con.execute('SELECT count(*) FROM actions').fetchone()[0], "
                    "con.execute('SELECT count(*) FROM main.actions').fetchone()[0], len(d['actions']), len(d['raid']), "
                    "[p['code'] for p in d['projects']], d['project_states'], d['settings']['showArchived']]))")
        self.assertEqual(o[:4], [0, 2, 0, 0])                                        # hidden, never deleted
        self.assertEqual(o[4], [])
        self.assertEqual(o[5], [{"code": "ABC", "name": "Example Programme", "state": "archived"}])
        self.assertFalse(o[6])
        self.v.run("export", script="excel_sync.py")
        x = self.py("import paths; from openpyxl import load_workbook\n"
                    "wb = load_workbook(paths.EXCEL_VIEW)\n"
                    "print(json.dumps([[c.value for c in r][0] for r in wb['Actions'].iter_rows(min_row=2) if r[0].value]))")
        self.assertEqual(x, [])                                                      # the Excel export leaves them out too
        items = self.found("zebrafish")["items"]
        self.assertEqual(items, [("ABC-A-002", True, "Closed · Alan Carter · Archived")])   # still found, marked Archived
        self.assertNotIn("meetings", self.found("quokka"))                            # its files in 99 Archive aren't indexed
        stored = f"projects/{self.abc.name}/minutes/2026-10-01 Steering.md"
        o = self.py(f"import reach, paths; print(json.dumps([reach.classify({stored!r}, 'read')[0], "
                    f"paths.resolve({stored!r}).is_file()]))")
        self.assertEqual(o, ["never", True])                                         # the link still opens; ask creaite can't read it
        cfg = self.v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text())
        data.setdefault("dashboard", {})["show_archived"] = True
        cfg.write_text(json.dumps(data, indent=2))
        o = self.py("import build_dashboard; d = build_dashboard.collect(); print(json.dumps([len(d['actions']), d['settings']['showArchived']]))")
        self.assertEqual(o, [2, True])                                               # Show archived brings them back

    def test_an_archived_project_takes_no_new_items_and_its_code_is_never_reused(self):
        self.archive()
        src = f"projects/{self.abc.name}/minutes/2026-10-01 Steering.md"
        self.v.propose("late", [{"n": 1, "op": "new", "table": "actions", "match": "strong", "flags": [], "decision": "approved",
                                 "values": {"project": "ABC", "description": "x", "raised": "2026-10-05", "source": src}}])
        r = self.v.run("apply", ok=False)
        self.assertIn("archived: restore it first", r.stdout)
        r = self.v.run("new-project", "--code", "ABC", "--name", "Again", script="propose.py", ok=False)
        self.assertIn("already used", r.stdout + r.stderr)
        r = self.v.propose("flag", [{"n": 1, "op": "update", "table": "projects", "id": "ABC", "changes": {"archived": 0},
                                     "match": "strong", "flags": [], "decision": "approved"}])
        self.assertIn("archived is set only by archiving or restoring", self.v.run("apply", ok=False).stdout)

    def test_restore_reverses_each_step_and_round_trips_exactly(self):
        self.v.propose("close", [{"n": 1, "op": "update", "table": "actions", "id": "ABC-A-001", "changes": {"status": "Closed"},
                                  "match": "strong", "flags": [], "decision": "approved"}])
        self.v.run("apply")
        before = self.state()
        out = self.stage("archive", "ABC")                                           # nothing open: no --cancel-open needed
        self.assertNotIn("Cancelled", out)
        self.v.run("apply")
        out = self.stage("restore", "ABC")
        self.assertIn("Restore Example Programme (ABC): its items live again, the project active", out)
        self.v.run("apply")
        self.assertEqual(self.state(), before)                                       # folder, register, items, search
        self.v.run("undo")                                                           # the restore undone: archived again
        self.assertEqual(self.v.rows("projects")[0]["archived"], 1)
        self.assertTrue((self.v.root / "projects/99 Archive" / self.abc.name).is_dir())

    def test_restore_never_overwrites_a_folder_that_took_its_name(self):
        self.archive()
        touch(self.abc / "new.md")                                                   # a folder of the same name, made since
        self.stage("restore", "ABC")
        self.v.run("apply")
        back = self.v.root / "projects" / f"{self.abc.name} 2"
        self.assertTrue((back / "minutes" / "2026-10-01 Steering.md").is_file())
        self.assertTrue((self.abc / "new.md").is_file())
        self.assertIn(f"| {self.abc.name} 2 |", self.reg.read_text(encoding="utf-8"))


def paths_of(root):
    return {"register": root / "projects/_portfolio/project-register.md"}


class ArchiveInOneDrive(OneDriveCase):
    """With the projects in a OneDrive root: the engagement folder goes to <root>/99 Archive and back, the register in code order."""

    def test_archive_and_restore_an_engagement(self):
        reg = self.root / "_Portfolio" / "project-register.md"
        before = (reg.read_text(encoding="utf-8"), sorted(str(p) for p in self.eng("ABC").rglob("*")))
        for args in (("archive", "ABC"), ("restore", "ABC")):
            f = self.v.root / "system/staging/drafts/a.json"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(self.v.run(*args, script="propose.py").stdout)
            self.v.run("stage", str(f), script="propose.py")
            self.v.run("apply")
            if args[0] == "archive":
                self.assertTrue((self.root / "99 Archive" / "Example Programme" / "CLAUDE.md").is_file())
                self.assertFalse(self.eng("ABC").exists())
                o = self.py("import paths; print(json.dumps([c for c, _ in paths.project_folders()]))")
                self.assertEqual(o, ["DEF", "_portfolio"])
        self.assertEqual((reg.read_text(encoding="utf-8"), sorted(str(p) for p in self.eng("ABC").rglob("*"))), before)


class Migration(unittest.TestCase):
    """What runs on Alan's vault at the update: tracker.py migrate on a database made with the schema before BL-09 (dev/tests/pinned/schema-before-bl09.sql),
    with sample rows in every table, adds `archived` (0) to projects and the six item tables, keeps every row, and the projects
    CHECK then refuses an archived project that is still active."""

    FLAGGED = ("projects", "milestones", "workstreams", "actions", "raid", "decisions", "promises")
    SAMPLE = [
        ("milestones", "id, project, name, source", ("ABC-M-001", "ABC", "Go-live", "s")),
        ("workstreams", "id, project, name, created, source", ("ABC-W-001", "ABC", "Data", "2026-10-01", "s")),
        ("actions", "id, project, description, raised, source, milestone", ("ABC-A-001", "ABC", "Send SOW", "2026-10-01", "s", "ABC-M-001")),
        ("raid", "id, project, type, description, raised, source", ("ABC-001", "ABC", "Risk", "Data may slip", "2026-10-01", "s")),
        ("decisions", "id, project, decision, date, status, source", ("ABC-D-001", "ABC", "Pilot first", "2026-10-01", "Made", "s")),
        ("promises", "id, project, promised_by, promised_to, description, raised, source",
         ("ABC-P-001", "ABC", "Alan Carter", "Jane Doe", "Send the deck", "2026-10-01", "s")),
        ("links", "from_item, to_item, source", ("ABC-001", "ABC-A-001", "s")),
        ("labels", "name, colour", ("Board", "grey")),
        ("item_labels", "item_id, label", ("ABC-A-001", "Board")),
        ("updates", "week_ending, project, health, summary", ("2026-10-02", "ABC", "On track", "Fine")),
        ("applies", "proposals, file_ops", ("[]", "[]")),
        ("change_log", "apply_id, tbl, item_id, field, new_value, via", (1, "actions", "ABC-A-001", "status", "Open", "cx-edit")),
        ("rejected", "fingerprint, via", ("abc123", "cx-edit")),
    ]

    def dump(self, db):
        with closing(sqlite3.connect(db)) as con:
            con.row_factory = sqlite3.Row
            tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
                                                "AND name NOT LIKE 'vault_search%' ORDER BY name")]
            return {t: [dict(r) for r in con.execute(f"SELECT * FROM {t} ORDER BY 1")] for t in tables}

    def test_migrate_adds_the_flags_keeps_every_row_and_the_check_holds(self):
        v = Vault()
        self.addCleanup(v.cleanup)
        old = (Path(__file__).resolve().parent / "pinned" / "schema-before-bl09.sql").read_text(encoding="utf-8")
        self.assertNotIn("archived", old)        # the schema before BL-09 (main's, kept as a fixture: CI has no origin/main)
        schema = v.root / "system/scripts/schema.sql"
        new = schema.read_text(encoding="utf-8")
        schema.write_text(old, encoding="utf-8")
        v.run("init")
        db = v.root / "system/tracker.db"
        with closing(sqlite3.connect(db)) as con:
            for t, cols, vals in self.SAMPLE:
                con.execute(f"INSERT INTO {t} ({cols}) VALUES ({', '.join('?' * len(vals))})", vals)
            con.commit()
        before = self.dump(db)
        for t in before:
            self.assertTrue(before[t], f"{t} has a sample row")                       # every table holds something
        schema.write_text(new, encoding="utf-8")                                      # the update brings the new schema
        self.assertIn("Migrated", v.run("migrate").stdout)
        after = self.dump(db)
        self.assertEqual(sorted(after), sorted(before))
        for t in before:
            got = [{k: x for k, x in r.items() if not (k == "archived" and t in self.FLAGGED)} for r in after[t]]
            self.assertEqual(got, before[t], t)                                       # every row, every value kept
        for t in self.FLAGGED:
            self.assertTrue(after[t] and all(r["archived"] == 0 for r in after[t]), t)
        for t in set(before) - set(self.FLAGGED):
            self.assertTrue(all("archived" not in r for r in after[t]), t)
        with closing(sqlite3.connect(db)) as con:
            with self.assertRaises(sqlite3.IntegrityError):                           # archived and still active: refused
                con.execute("UPDATE projects SET archived = 1 WHERE code = 'ABC'")
            con.execute("UPDATE projects SET active = 0, archived = 1 WHERE code = 'ABC'")   # archived means closed: allowed
            con.rollback()
        self.assertIn("Schema is up to date", v.run("migrate").stdout)              # nothing the second time
        self.assertEqual(self.dump(db), after)


class ArchiveRoutes(unittest.TestCase):
    """Settings › Projects' Archive and Restore: POST /api/project/archive puts the change on the approval card; open items first."""

    @classmethod
    def setUpClass(cls):
        import re
        import time
        import urllib.request
        from test_health_fixes import free_port
        cls.v = Vault()
        cls.v.run("init")
        abc = next(d for d in (cls.v.root / "projects").iterdir() if d.name.startswith("ABC "))
        cls.abc = abc
        src = f"projects/{abc.name}/minutes/2026-10-01 Steering.md"
        touch(abc / "minutes" / "2026-10-01 Steering.md")
        cls.v.propose("seed", [dict(i, match="strong", flags=[], decision="approved") for i in items_for_abc(src)])
        cls.v.run("apply")
        cls.port = free_port()
        cls.base = f"http://127.0.0.1:{cls.port}"
        import os
        cls.proc = subprocess.Popen([sys.executable, str(cls.v.root / "system/scripts/live_server.py")],
                                    env={**os.environ, "CREAITE_PORT": str(cls.port)},
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                urllib.request.urlopen(cls.base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        page = urllib.request.urlopen(cls.base + "/").read().decode()
        cls.token = json.loads(re.search(r'id="data">(.*?)</script>', page, re.S).group(1).replace("<\\/", "</"))["token"]

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)
        cls.v.cleanup()

    def post(self, path, body):
        import urllib.error
        import urllib.request
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            with e:
                return {"status": e.code, **json.loads(e.read() or b"{}")}

    def test_archive_lists_open_items_then_the_card_archives_and_restore_brings_it_back(self):
        self.assertEqual(self.post("/api/project/archive", {"code": "abc; rm", "action": "archive"})["status"], 400)
        got = self.post("/api/project/archive", {"code": "ABC", "action": "archive"})
        self.assertFalse(got["ok"])
        self.assertEqual([o["id"] for o in got["open"]], ["ABC-A-001"])            # Cancel them all and archive, or Stop
        self.assertEqual(self.v.rows("projects")[0]["archived"], 0)
        got = self.post("/api/project/archive", {"code": "ABC", "action": "archive", "cancel_open": True})
        self.assertTrue(got["ok"] and got["card"], got)
        self.assertEqual(self.v.rows("projects")[0]["archived"], 0)                 # nothing changes before Approve
        card = self.post("/api/edit/pending", {})["card"]
        self.assertIn("ABC-A-001 · Status: Open → Cancelled", card["lines"])
        done = self.post("/api/edit/approve", {"card": card["card"]})
        self.assertTrue(done["ok"], done)
        self.assertEqual(self.v.rows("projects")[0]["archived"], 1)
        self.assertTrue((self.v.root / "projects/99 Archive" / self.abc.name).is_dir())
        got = self.post("/api/project/archive", {"code": "ABC", "action": "restore"})
        self.assertTrue(got["ok"], got)
        card = self.post("/api/edit/pending", {})["card"]
        self.assertTrue(self.post("/api/edit/approve", {"card": card["card"]})["ok"])
        p = self.v.rows("projects")[0]
        self.assertEqual((p["active"], p["archived"]), (1, 0))
        self.assertTrue(self.abc.is_dir())


if __name__ == "__main__":
    unittest.main()
