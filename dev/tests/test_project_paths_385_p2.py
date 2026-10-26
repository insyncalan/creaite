"""#385 phase 2: the ordinary callers of a project's own folder (locations.project_paths), and the read-time rules.

Run: python3 dev/tests/test_project_paths_385_p2.py

Fictional and temporary throughout: test_project_paths_385's fake home and OneDrive projects folder (ABC "Example Programme" moved
to ~/Work/Acme/Programme and mapped there; DEF "Digital Enablement" in the projects folder). Covers: fail closed on read (an entry
that breaks the rules is never used, and Health says so); an archived project's entry is out of project_roots but its stored paths
still resolve to its archive slot; a relative mapping inside the projects folder under another name (Jarvis, 26-10-2026); the
archive and restore specs (propose.py) and, once dev/proposals/385's tracker diff is in, archive -> restore -> undo through
tracker.py apply; Inbox's filed transcripts from a mapped folder; the page's own_folders data (Today's line, Project settings);
Health's archived projects; doctor's permissions check accepting exactly a mapped folder; the undo-update warning in cx-setup;
search keys unchanged for unmapped projects. Mutants: the fail-closed read, the archived-out-of-roots rule, and the
"inside another registered project" refusal.
"""
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_onedrive_projects import touch  # noqa: E402
from test_project_paths_385 import ABC, DEF, MIN, OWN, REPO, MappedCase  # noqa: E402

TRACKER = (REPO / "system/scripts/tracker.py").read_text(encoding="utf-8")
TRACKER_PATCHED = "archive_slot" in TRACKER or "parts_below_base" in TRACKER
needs_tracker = unittest.skipUnless(TRACKER_PATCHED, "GUARDED: needs dev/proposals/385 tracker diff")
TRANS = "02 Meetings/Transcripts"


class FailClosed(MappedCase):
    """An entry that breaks the rules on saving (a hand-edited settings.json, a folder that has since become a shortcut) is
    never used: not in project_roots, allowed_roots or resolve, and doctor says so in plain words."""

    def state(self):
        return self.py("import paths; print(json.dumps([sorted(paths.project_roots()), [str(x) for x in paths.allowed_roots()], "
                       f"str(paths.resolve('projects/{ABC}/CLAUDE.md')), paths.dropped_project_paths()]))")

    def test_a_good_entry_is_used(self):
        roots, allowed, res, dropped = self.state()
        self.assertEqual(roots, [ABC])
        self.assertIn(str(self.own), allowed)
        self.assertEqual(res, str(self.own / "CLAUDE.md"))
        self.assertEqual(dropped, [])

    def test_a_symlink_is_dropped(self):
        (self.home / "Links").mkdir()
        os.symlink(self.own, self.home / "Links" / "Programme")
        self.map({ABC: "~/Links/Programme"})
        roots, allowed, res, dropped = self.state()
        self.assertEqual(roots, [])
        self.assertFalse(any("Links" in a or "Acme" in a for a in allowed))
        self.assertEqual(res, str(self.root / ABC / "CLAUDE.md"))          # as if it were in the projects folder
        self.assertEqual([d["folder"] for d in dropped], [ABC])
        self.assertIn("symlink", dropped[0]["why"])
        self.assertFalse(dropped[0]["why"].startswith("Not saved"))

    def test_outside_home_never_list_dot_dot_and_overlaps_are_dropped(self):
        for value in ("/etc/x", "~/../elsewhere", "~/.ssh/keys", "~/Library/Preferences/x"):
            self.map({ABC: value})
            self.assertEqual(self.state()[0], [], value)
        self.map({ABC: OWN, DEF: OWN + "/Sub"})                            # nested: neither is used
        self.assertEqual(self.state()[0], [])

    def test_doctor_reports_it_in_plain_words(self):
        (self.home / "Links").mkdir()
        os.symlink(self.own, self.home / "Links" / "Programme")
        self.map({ABC: "~/Links/Programme"})
        status, detail = self.py("import doctor; print(json.dumps(doctor.project_paths_present()))")
        self.assertIsNone(status)
        self.assertIn("not used", detail)
        self.assertIn(ABC, detail)

    def test_the_page_data_names_the_project(self):
        (self.home / "Links").mkdir()
        os.symlink(self.own, self.home / "Links" / "Programme")
        self.map({ABC: "~/Links/Programme"})
        o = self.py("import build_dashboard as bd, paths; print(json.dumps(bd.own_folders({c: paths.project_dir(c) for c in ('ABC','DEF')})))")
        self.assertEqual([d["code"] for d in o["dropped"]], ["ABC"])
        self.assertEqual(o["paths"], {})


class RunTimeBadValues(MappedCase):
    """Cap's review of phase 1, MEDIUM 1: bad values written straight into settings.json are dropped where the value is read
    (_loc_project_roots), so nothing reaches outside home or takes over the archive."""

    PROBE = ("import paths; loc = paths.locations(); print(json.dumps([sorted(paths._loc_project_roots(loc)), "
             "[str(x) for x in paths.allowed_roots()], str(paths.resolve('projects/99 Archive/Old Mill/x')), "
             "[d['folder'] for d in paths.dropped_project_paths()]]))")

    def test_a_value_above_home_is_dropped(self):
        self.map({ABC: OWN, "Vale Programme": "~/../../../"})
        roots, allowed, _, dropped = self.py(self.PROBE)
        self.assertEqual(roots, [ABC])
        self.assertTrue(all(a.startswith(str(self.home)) or a.startswith(str(self.v.root.resolve())) for a in allowed), allowed)
        self.assertEqual(dropped, ["Vale Programme"])

    def test_a_key_named_99_archive_is_dropped(self):
        (self.home / "A" / "Vale").mkdir(parents=True)
        self.map({ABC: OWN, "99 Archive": "~/A/Vale"})
        roots, _, res, dropped = self.py(self.PROBE)
        self.assertEqual(roots, [ABC])
        self.assertEqual(res, str(self.root / "99 Archive" / "Old Mill" / "x"))       # never into ~/A/Vale
        self.assertEqual(dropped, ["99 Archive"])

    def test_a_folder_directly_in_home_is_refused(self):
        self.assertIsNotNone(self.problem(ABC, "~/Programme"))                    # Cap's LOW 4: its slot would be ~/99 Archive
        self.assertIsNotNone(self.problem(ABC, "~/Library/CloudStorage"))
        self.assertIsNone(self.problem(ABC, "~/Work/Programme"))

    def test_the_key_takes_the_registers_spelling(self):
        self.map({ABC.lower(): OWN})                                              # Cap's LOW 5
        touch(self.own / "CLAUDE.md")
        o = self.py(f"import paths; print(json.dumps([sorted(paths.project_roots()), paths.rel(paths.Path({str(self.own / 'CLAUDE.md')!r})), paths.project_paths()]))")
        self.assertEqual(o, [[ABC], f"projects/{ABC}/CLAUDE.md", {ABC: OWN}])

    def test_only_a_registered_project_gets_a_new_place(self):
        # Cap's LOW 6: through the settings save (locations_change_problem); an archived project's kept entry stays saveable
        code = ("import paths; old = paths.locations(); new = dict(old, project_paths=dict(old['project_paths'], **{n: v})); "
                "print(json.dumps(paths.locations_change_problem(old, new)))")
        why = self.py(code.replace("**{n: v}", "**{'Old Mill': '~/Work/Mill'}"))
        self.assertIn("isn't a project in the register", why)
        self.assertIsNone(self.py(code.replace("**{n: v}", f"**{{{DEF!r}: '~/Work/Digital'}}")))
        self.map({ABC: OWN, "Old Mill": "~/Work/Mill"})                           # kept on archive: changing another is fine
        self.assertIsNone(self.py(code.replace("**{n: v}", f"**{{{DEF!r}: '~/Work/Digital'}}")))

    def test_a_prep_page_never_creates_a_missing_own_folder(self):
        shutil.rmtree(self.own)
        o = self.py("import paths; print(json.dumps([paths.unreachable_own_folder(paths.folder('ABC', 'agendas') / 'x.html'), "
                    "paths.unreachable_own_folder(paths.folder('DEF', 'agendas') / 'x.html')]))")
        self.assertEqual(o, [OWN, None])
        src = (REPO / "system/scripts/prep_page.py").read_text(encoding="utf-8")
        for fn in ("def save(ctx, page):", "def save_agenda("):
            body = src[src.index(fn):]
            self.assertLess(body.index("unreachable_own_folder("), body.index(".mkdir(parents=True"), fn)
        self.assertFalse(self.own.exists())


class Archived(MappedCase):
    """Cap's LOW 1: an archived project's entry (kept on archive) is out of project_roots and reach; its stored paths resolve to
    the archive slot beside its own folder."""

    def archive_by_hand(self):
        touch(self.own / MIN / "2026-10-01 Steering.docx")
        slot = self.home / "Work" / "Acme" / "99 Archive" / ABC
        slot.parent.mkdir()
        shutil.move(str(self.own), str(slot))
        reg = self.root / "_Portfolio" / "project-register.md"
        reg.write_text("\n".join(ln for ln in reg.read_text().splitlines() if not ln.startswith("| ABC |")) + "\n")
        return slot

    def test_out_of_roots_but_resolving_to_the_slot(self):
        slot = self.archive_by_hand()
        o = self.py("import paths; print(json.dumps([sorted(paths.project_roots()), [str(x) for x in paths.allowed_roots()], "
                    f"str(paths.resolve('projects/{ABC}/{MIN}/2026-10-01 Steering.docx')), "
                    f"str(paths.resolve('projects/99 Archive/{ABC}/CLAUDE.md')), sorted(paths.mapped_project_paths()), "
                    f"paths.project_paths(), str(paths.archive_slot({ABC!r})), "
                    f"paths.base_of({str(slot / 'CLAUDE.md')!r}), paths.tool_patterns('**/99 Archive/**')]))")
        roots, allowed, res, res2, mapped, live, s, base, pats = o
        self.assertEqual(roots, [])
        self.assertFalse(any("Acme" in a for a in allowed))
        self.assertEqual(res, str(slot / MIN / "2026-10-01 Steering.docx"))
        self.assertEqual(res2, str(slot / "CLAUDE.md"))
        self.assertEqual(mapped, [ABC])
        self.assertEqual(live, {})
        self.assertEqual(s, str(slot))
        self.assertIsNone(base)                       # the slot is never a base
        self.assertEqual(len(pats), 1)                # no pattern under the archived project's old place

    def test_the_page_lists_it_for_the_undo_warning(self):
        self.archive_by_hand()
        o = self.py("import build_dashboard as bd; print(json.dumps(bd.own_folders({})))")
        self.assertEqual(o["archived"], [ABC])
        self.assertEqual(o["paths"], {})


class RelativeInsideTheRoot(MappedCase):
    """Jarvis, 26-10-2026: a relative mapping inside the projects folder under another name works, and no other project's files
    go to it."""

    def setUp(self):
        super().setUp()
        self.inner = self.root / "Clients" / "Vale"
        self.inner.parent.mkdir()
        shutil.move(str(self.own), str(self.inner))
        self.map({ABC: "Clients/Vale"})

    def test_it_round_trips(self):
        f = touch(self.inner / MIN / "2026-10-01 Steering.docx")
        g = touch(self.eng("DEF", MIN, "2026-10-01 Review.docx"))
        want = [f"projects/{ABC}/{MIN}/2026-10-01 Steering.docx", f"projects/{DEF}/{MIN}/2026-10-01 Review.docx"]
        o = self.probe([f, g], want)
        self.assertEqual(o["rel"], want)
        self.assertEqual(o["resolve"], [str(f), str(g)])
        self.assertEqual(o["folders"], [["ABC", str(self.inner)], ["DEF", str(self.eng("DEF"))], ["_portfolio", str(self.root / "_Portfolio")]])
        s = self.py(f"import paths; print(json.dumps([str(paths.archive_slot({ABC!r})), sorted(paths.project_roots()), paths.dropped_project_paths()]))")
        self.assertEqual(s, [str(self.root / "Clients" / "99 Archive" / ABC), [ABC], []])

    def test_inside_another_registered_projects_folder_is_still_refused(self):
        self.assertIsNotNone(self.problem(ABC, f"{DEF}/Vale"))
        self.map({ABC: f"{DEF}/Vale"})
        self.assertEqual(self.py("import paths; print(json.dumps(sorted(paths.project_roots())))"), [])


class ArchiveSpec(MappedCase):
    """propose.py archive and restore for a mapped project: exactly the slot beside it, never a numbered name."""

    def spec(self, *args, ok=True):
        r = self.v.run(*args, script="propose.py", ok=ok)
        return json.loads(r.stdout) if ok else r

    def test_archive_goes_to_exactly_the_slot(self):
        s = self.spec("archive", "ABC", "--cancel-open")
        move = s["file_changes"]["file_ops"][0]
        self.assertEqual(move, {"op": "move", "from": f"projects/{ABC}", "to": f"projects/99 Archive/{ABC}"})
        self.assertEqual(s["items"][-1]["folder"], {"from": f"projects/{ABC}", "to": f"projects/99 Archive/{ABC}"})
        o = self.py(f"import paths; print(json.dumps([str(paths.resolve('projects/{ABC}', archived=False)), "
                    f"str(paths.resolve('projects/99 Archive/{ABC}', archived=False))]))")
        self.assertEqual(o, [str(self.own), str(self.home / "Work" / "Acme" / "99 Archive" / ABC)])

    def test_a_taken_slot_is_refused_not_numbered(self):
        for name in ("99 Archive", "_Archive"):
            (self.home / "Work" / "Acme" / name / ABC).mkdir(parents=True)
            r = self.spec("archive", "ABC", "--cancel-open", ok=False)
            self.assertNotEqual(r.returncode, 0, name)
            self.assertIn("already a folder called", r.stderr + r.stdout)
            shutil.rmtree(self.home / "Work" / "Acme" / name)

    def test_an_unmapped_project_is_as_before(self):
        self.map({})
        shutil.move(str(self.own), str(self.eng("ABC")))
        s = self.spec("archive", "ABC", "--cancel-open")
        self.assertEqual(s["file_changes"]["file_ops"][0]["to"], f"projects/99 Archive/{ABC}")
        (self.root / "99 Archive" / ABC).mkdir(parents=True)
        self.assertEqual(self.spec("archive", "ABC", "--cancel-open")["file_changes"]["file_ops"][0]["to"],
                         f"projects/99 Archive/{ABC} 2")


class ArchiveRestoreUndo(MappedCase):
    """archive -> restore -> undo for a mapped project through propose.py and tracker.py apply (tracker's move checks are
    guarded: dev/proposals/385's tracker diff)."""

    def stage_and_apply(self, *args):
        spec = self.v.run(*args, script="propose.py").stdout
        f = self.v.root / "system/staging/drafts/a.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(spec, encoding="utf-8")
        self.v.run("stage", str(f), script="propose.py")
        self.v.run("apply")

    @needs_tracker
    def test_the_round_trip(self):
        touch(self.own / MIN / "2026-10-01 Steering.docx", "Steering.")
        slot = self.home / "Work" / "Acme" / "99 Archive" / ABC
        self.stage_and_apply("archive", "ABC", "--cancel-open")
        self.assertTrue(slot.is_dir())
        self.assertFalse(self.own.exists())
        self.assertFalse((self.root / "99 Archive" / ABC).exists())
        self.assertEqual(self.py("import paths; print(json.dumps(sorted(paths.project_roots())))"), [])
        lines = self.py("import health; print(json.dumps(health.archived_lines()))")
        self.assertEqual(len(lines), 1)
        self.assertIn("~/Work/Acme/99 Archive/" + ABC, lines[0])
        self.stage_and_apply("restore", "ABC")
        self.assertEqual((self.own / MIN / "2026-10-01 Steering.docx").read_text(), "Steering.")
        self.assertFalse(slot.exists())
        self.v.run("undo")
        self.assertTrue(slot.is_dir())
        self.assertFalse(self.own.exists())

    def test_restore_spec_goes_back_into_its_own_folder(self):
        """The restore spec alone, from a history written as archive would write it (no guarded code runs)."""
        self.restore_history()
        s = json.loads(self.v.run("restore", "ABC", script="propose.py").stdout)
        self.assertEqual(s["file_changes"]["file_ops"][0], {"op": "move", "from": f"projects/99 Archive/{ABC}", "to": f"projects/{ABC}"})

    def test_restore_is_refused_when_its_own_folder_is_back(self):
        self.restore_history()
        self.own.mkdir(parents=True)
        r = self.v.run("restore", "ABC", script="propose.py", ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("is there again already", r.stderr + r.stdout)

    def restore_history(self):
        """ABC archived by hand: folder in its slot, register row out, and the tracker's archive record as apply leaves it."""
        slot = self.home / "Work" / "Acme" / "99 Archive" / ABC
        slot.parent.mkdir()
        shutil.move(str(self.own), str(slot))
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            con.execute("INSERT INTO applies (at, proposals) VALUES ('2026-10-20 09:00', '[\"proposed-archive.json\"]')")
            aid = con.execute("SELECT max(apply_id) FROM applies").fetchone()[0]
            for field, old, new in (("archived", "0", "1"), ("active", "1", "0"),
                                    ("folder", None, json.dumps({"from": f"projects/{ABC}", "to": f"projects/99 Archive/{ABC}"})),
                                    ("register_row", None, f"| ABC | Example Programme | {ABC} | Example |  |  |  |  |  |  |")):
                con.execute("INSERT INTO change_log (at, apply_id, tbl, item_id, field, old_value, new_value, op, via) "
                            "VALUES ('2026-10-20 09:00', ?, 'projects', 'ABC', ?, ?, ?, 'update', 'proposed-archive.json')",
                            (aid, field, old, new))
            con.execute("UPDATE projects SET archived = 1, active = 0 WHERE code = 'ABC'")
            con.commit()


class Callers(MappedCase):
    """The ordinary callers that assumed one root."""

    def test_inbox_knows_a_transcript_filed_in_a_mapped_folder(self):
        body = "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nhello\n"
        touch(self.own / TRANS / "Weekly-20261001.vtt", body)
        touch(self.eng("DEF", TRANS, "Review-20261002.vtt"), body + "def\n")
        touch(self.v.root / "inbox" / "Weekly-20261001.vtt", body)
        touch(self.v.root / "inbox" / "Review copy-20261002.vtt", body + "def\n")
        o = self.py("import build_dashboard as bd, paths; print(json.dumps([[str(f) for f in bd.filed_transcripts()], "
                    "{r['name']: r['state'] for r in bd.inbox([{'code': 'ABC'}, {'code': 'DEF'}])}]))")
        self.assertEqual(sorted(o[0]), sorted([str(self.own / TRANS / "Weekly-20261001.vtt"), str(self.eng("DEF", TRANS, "Review-20261002.vtt"))]))
        self.assertEqual(o[1], {"Weekly-20261001.vtt": "processed", "Review copy-20261002.vtt": "processed"})

    def test_page_data_folders_where_and_missing(self):
        code = "import build_dashboard as bd, paths; f={c: paths.project_dir(c) for c in ('ABC','DEF')}; " \
               "print(json.dumps([{c: paths.stored_folder(c, d) for c, d in f.items()}, bd.own_folders(f)]))"
        names, o = self.py(code)
        self.assertEqual(names, {"ABC": ABC, "DEF": DEF})            # the stored name, not the real folder's ("Programme")
        self.assertEqual(o["where"]["ABC"], OWN)
        self.assertTrue(o["where"]["DEF"].startswith("~/Library/CloudStorage/"))
        self.assertEqual(o["paths"], {"ABC": OWN})
        self.assertEqual(o["missing"], [])
        shutil.move(str(self.own), str(self.home / "Elsewhere"))       # unmounted, or moved by hand
        names, o = self.py(code)
        self.assertEqual(o["missing"], [{"code": "ABC", "path": OWN}])
        self.assertFalse(self.own.exists())                            # never created

    def test_minutes_folder_of_a_mapped_project(self):
        f = touch(self.own / MIN / "2026-10-01 Steering.docx")
        o = self.py(f"import minutes, os; print(json.dumps(minutes._in_minutes_folder('projects/{ABC}/{MIN}/2026-10-01 Steering.docx', "
                    f"os.path.realpath({str(f)!r}), 'ABC')))")
        self.assertTrue(o)

    def test_search_keys_unchanged_for_unmapped_projects(self):
        touch(self.eng("DEF", MIN, "2026-10-03 Design review.docx"))
        touch(self.own / MIN / "2026-10-01 Steering.docx")
        o = self.py("import tracker, paths; print(json.dumps(sorted(paths.rel(f) for f, k, c in tracker.index_files() if k == 'minutes')))")
        self.assertEqual(o, sorted([f"projects/{DEF}/{MIN}/2026-10-03 Design review.docx", f"projects/{ABC}/{MIN}/2026-10-01 Steering.docx"]))

    def test_doctor_accepts_exactly_the_mapped_folder_in_additional_directories(self):
        cs = self.v.root / ".claude/settings.json"
        data = json.loads(cs.read_text())
        root = json.loads((self.v.root / "system/config/settings.json").read_text())["locations"]["projects_root"]
        data.setdefault("permissions", {})["additionalDirectories"] = [root, OWN]
        cs.write_text(json.dumps(data, indent=2))
        status, detail = self.py("import doctor; print(json.dumps(doctor.assistant_permissions()))")
        self.assertNotIn("additionalDirectories", detail)
        data["permissions"]["additionalDirectories"] = [root, "~/Work/Acme"]          # the parent: wider
        cs.write_text(json.dumps(data, indent=2))
        status, detail = self.py("import doctor; print(json.dumps(doctor.assistant_permissions()))")
        self.assertIn("additionalDirectories ~/Work/Acme", detail)

    def test_doctor_names_each_folder_a_terminal_session_cant_read(self):
        cs = self.v.root / ".claude/settings.json"
        data = json.loads(cs.read_text())
        root = json.loads((self.v.root / "system/config/settings.json").read_text())["locations"]["projects_root"]
        ask = "import doctor; print(json.dumps(doctor.assistant_permissions()))"
        data.setdefault("permissions", {})["additionalDirectories"] = [root]
        cs.write_text(json.dumps(data, indent=2))
        perm = self.v.root / "system/scripts/permissions.py"
        if not self.py("import permissions; print(json.dumps(hasattr(permissions, 'project_dirs')))"):
            status, detail = self.py(ask)
            self.assertIsNone(status)
            self.assertIn(f"a project's own folder ({OWN})", detail)      # the permissions diff isn't in this tree: said so
            self.assertIn("can't add it for you", detail)
            self.assertNotIn(root + " from", detail)
            perm.write_text(perm.read_text(encoding="utf-8") + "\n\ndef project_dirs(loc=None):\n    return []\n",
                            encoding="utf-8")                           # as if the permissions diff had landed
        status, detail = self.py(ask)
        self.assertIn(f"can't read {OWN} from a Terminal session yet", detail)
        self.assertIn("adds it", detail)
        data["permissions"]["additionalDirectories"] = []
        cs.write_text(json.dumps(data, indent=2))
        status, detail = self.py(ask)
        self.assertIn(f"can't read {root}, {OWN} from", detail)
        self.assertIn("adds them", detail)
        data["permissions"]["additionalDirectories"] = [root, OWN]
        cs.write_text(json.dumps(data, indent=2))
        self.assertEqual(self.py(ask)[0], True)

    def test_settings_catalogue_has_the_map(self):
        o = self.py("import settings_catalogue as s; d = s.flatten(s.defaults()); "
                    "print(json.dumps([d.get('locations.project_paths'), 'locations.project_paths' in s.CATALOGUE, "
                    "'locations.project_paths' in s.FIXED]))")
        self.assertEqual(o, [{}, True, True])


class HealthArchived(MappedCase):
    def test_lines_in_plain_words(self):
        o = self.py("import health; print(json.dumps(health.archived_lines([{'code': 'ABC', 'name': 'Example Programme', "
                    "'where': '~/Work/Acme/99 Archive/Example Programme', 'own': True, 'there': True}, {'code': 'DEF', "
                    "'name': 'Digital Enablement', 'where': '~/x/99 Archive/Digital Enablement', 'own': False, 'there': False}, "
                    "{'code': 'GHI', 'name': 'Growth Hub', 'where': '', 'own': False, 'there': False}])))")
        self.assertEqual(o[0], "Example Programme: ~/Work/Acme/99 Archive/Example Programme (beside its own folder)")
        self.assertIn("isn't there now", o[1])
        self.assertIn("isn't in the history", o[2])
        for ln in o:
            self.assertNotIn("ABC", ln)                                # projects by name (BL-101)

    def test_a_mapped_archived_project_is_listed_beside_its_folder(self):
        """Archived with the folder in its slot (the history as apply writes it): Health lists where it is."""
        ArchiveRestoreUndo.restore_history(self)
        o = self.py("import health; print(json.dumps([health.archived_projects(), health.health({'checks': []}, [])['archived']]))")
        rows, lines = o
        self.assertEqual([(r["code"], r["own"], r["there"]) for r in rows], [("ABC", True, True)])
        self.assertEqual(lines, [f"Example Programme: ~/Work/Acme/99 Archive/{ABC} (beside its own folder)"])


class UndoWarning(unittest.TestCase):
    def test_cx_setup_warns_before_undoing_to_an_engine_without_the_setting(self):
        text = (REPO / ".claude/skills/cx-setup/SKILL.md").read_text(encoding="utf-8")
        line = next(ln for ln in text.splitlines() if ln.startswith('- **"undo update"**'))
        self.assertIn("locations.project_paths", line)
        self.assertIn("2.6.10", line)
        self.assertLess(line.index("drop out of view"), line.index("update.py undo"))
        paths_py = (REPO / "system/scripts/paths.py").read_text(encoding="utf-8")
        self.assertIn('PROJECT_PATHS_SINCE = "2.6.10"', paths_py)

    def test_the_dashboard_warns_before_calling_the_route(self):
        js = (REPO / "system/templates/dashboard/src/settings.js").read_text(encoding="utf-8")
        undo = js[js.index("export async function updUndo"):]
        armed = undo[:undo.index("/api/update/undo")]
        self.assertIn("undoOwnFoldersWarning(", armed)                   # said when armed, before the route


class Mutants(MappedCase):
    """The read-time rules, each taken out, are caught."""

    TEXT = (REPO / "system/scripts/paths.py").read_text(encoding="utf-8")

    def mutate(self, old, new):
        self.assertIn(old, self.TEXT)
        (self.v.root / "system/scripts/paths.py").write_text(self.TEXT.replace(old, new, 1), encoding="utf-8")

    def symlinked_roots(self):
        (self.home / "Links").mkdir(exist_ok=True)
        if not (self.home / "Links" / "Programme").exists():
            os.symlink(self.own, self.home / "Links" / "Programme")
        self.map({ABC: "~/Links/Programme"})
        return self.py("import paths; print(json.dumps(sorted(paths.project_roots())))")

    def test_fail_closed_unmutated(self):
        self.assertEqual(self.symlinked_roots(), [])

    def test_fail_closed_off(self):
        self.mutate("            if why is None and name in raw:", "            if name in raw:")
        self.assertEqual(self.symlinked_roots(), [ABC])

    def archived_roots(self):
        Archived.archive_by_hand(self)
        return self.py("import paths; print(json.dumps(sorted(paths.project_roots())))")

    def test_archived_out_unmutated(self):
        self.assertEqual(self.archived_roots(), [])

    def test_archived_out_off(self):
        self.mutate("return {k: p for k, p in _mapping().items() if _registered(k)}", "return dict(_mapping())")
        self.assertEqual(self.archived_roots(), [ABC])

    def bad_roots(self):
        self.map({ABC: OWN, "Vale Programme": "~/../../../", "99 Archive": "~/A/Vale"})
        return self.py("import paths; print(json.dumps(sorted(paths._loc_project_roots(paths.locations()))))")

    def test_read_time_drop_unmutated(self):
        self.assertEqual(self.bad_roots(), [ABC])

    def test_read_time_drop_off_in_loc_project_roots(self):
        self.mutate("    return _loc_honoured(loc)[0]\n\n\ndef _raw_name_ok", "    return _loc_raw_roots(loc)\n\n\ndef _raw_name_ok")
        self.assertEqual(self.bad_roots(), sorted([ABC, "Vale Programme", "99 Archive"]))

    def test_home_parent_refusal_off(self):
        self.assertIsNotNone(self.problem(ABC, "~/Programme"))
        self.mutate("    if len(parts) == 1 or parts == [\"library\", \"cloudstorage\"]:", "    if False:")
        self.assertIsNone(self.problem(ABC, "~/Programme"))

    def test_registered_only_off(self):
        code = ("import paths; old = paths.locations(); new = dict(old, project_paths=dict(old['project_paths'], **{'Old Mill': "
                "'~/Work/Mill'})); print(json.dumps(paths.locations_change_problem(old, new)))")
        self.assertIsNotNone(self.py(code))
        self.mutate("if was.get(name) != value and not _registered(name):", "if False:")
        self.assertIsNone(self.py(code))

    def test_inside_another_registered_project_off(self):
        self.assertIsNotNone(self.problem(ABC, f"{DEF}/Vale"))
        self.mutate("        if _below_or_same(f, o) or _below_or_same(o, f):\n            return f\"is inside {other}'s",
                    "        if False:\n            return f\"is inside {other}'s")
        self.assertIsNone(self.problem(ABC, f"{DEF}/Vale"))


class RecodeMapped(MappedCase):
    """propose.py recode on a project in a folder of its own: the code and name change, the register's folder name never does
    (it is what locations.project_paths is keyed by, and a recode never writes settings, BL-141)."""

    GUARD = "    if own and folder and paths._fold(folder) != paths._fold(old_folder):\n"

    def staged(self):
        return sorted(p.name for p in (self.v.root / "system/staging").glob("proposed-*.json"))

    def test_a_new_folder_name_is_refused_and_nothing_is_staged(self):
        before = self.staged()
        r = self.v.run("recode", "ABC", "XPL", "--folder", "Example Plus", script="propose.py", ok=False)
        self.assertNotEqual(r.returncode, 0)
        out = r.stdout + r.stderr
        self.assertIn("in a folder of its own (" + OWN + ")", out)
        self.assertIn("run it again without --folder", out)
        self.assertEqual(self.staged(), before)

    def test_mutant_without_the_refusal_the_message_misleads(self):
        script = self.v.root / "system/scripts/propose.py"
        text = script.read_text(encoding="utf-8")
        self.assertEqual(text.count(self.GUARD), 1, "the recode refusal moved: update GUARD")
        script.write_text(text.replace(self.GUARD, "    if False:\n", 1), encoding="utf-8")
        r = self.v.run("recode", "ABC", "XPL", "--folder", "Example Plus", script="propose.py", ok=False)
        self.assertNotIn("folder of its own", r.stdout + r.stderr)
        self.assertIn("doesn't exist", r.stdout + r.stderr)                  # as before: told to rename a folder it can't see

    def test_code_and_name_change_and_the_memory_in_its_own_folder_follows(self):
        out = self.v.run("recode", "ABC", "XPL", "--name", "Example Plus", script="propose.py").stdout
        self.assertIn("is how creaite knows the project's own folder", out)
        self.assertNotIn("then recode with --folder", out)                    # never sent towards the refusal
        self.v.run("apply")
        self.assertTrue((self.own / "CLAUDE.md").read_text(encoding="utf-8").startswith("# XPL — Example Plus"))
        self.assertEqual(self.py("import paths; print(json.dumps(sorted(paths.project_roots())))"), [ABC])   # still mapped


HIDDEN = ("~/.config/git", "~/.ipython/profile_default/startup", "~/.config/autostart", "~/.config/systemd", "~/.oh-my-zsh/custom")


class CapFullReview(MappedCase):
    """Cap's Full review of #385, the paths.py findings: each rule, and its mutant (the rule taken out) caught."""

    mutate = Mutants.mutate
    TEXT = Mutants.TEXT

    def hidden(self):
        """For each of HIDDEN (made, as on a real laptop): [the save-time refusal, the settings save's refusal, honoured on read]."""
        out = []
        for v in HIDDEN:
            (self.home / v[2:]).mkdir(parents=True, exist_ok=True)
            self.map({ABC: v})
            out.append(self.py(f"""import paths
old = dict(paths.locations()); old.pop('project_paths')
print(json.dumps([paths.project_mapping_problem({ABC!r}, {v!r}, paths.locations()),
                  paths.locations_change_problem(old, paths.locations()), sorted(paths.project_roots())]))"""))
        return out

    def test_medium_1_a_hidden_folder_is_never_a_projects_folder(self):
        for v, (why, change, roots) in zip(HIDDEN, self.hidden()):
            self.assertIn("hidden folder", why or "", v)
            self.assertIn("hidden folder", change or "", v)
            self.assertEqual(roots, [], v)                                         # dropped on read (fail closed)

    def test_medium_1_mutant(self):
        self.mutate("    if hidden:                                   # Cap's MEDIUM 1", "    if False:                                   # Cap's MEDIUM 1")
        got = self.hidden()
        self.assertTrue(all(why is None and roots == [ABC] for why, _, roots in got), got)   # mutant: every one honoured

    TWICE = {ABC: OWN, ABC.upper(): "~/Work/Other/Programme"}
    NFC, NFD = "Société Programme", "Société Programme"

    def twice(self):
        (self.home / "Work" / "Other" / "Programme").mkdir(parents=True)
        self.map(self.TWICE)
        return [self.problem(ABC, OWN, mapping=self.TWICE), self.problem(self.NFC, "~/Work/S", mapping={self.NFC: "~/Work/S", self.NFD: "~/Work/T"}),
                self.py("import paths; print(json.dumps(sorted(paths.project_roots())))")]

    def test_low_4_two_keys_for_one_folder_name_are_refused(self):
        case, form, roots = self.twice()
        self.assertIn("in the list twice", case or "")
        self.assertIn("in the list twice", form or "")                            # NFC and NFD spellings: one name on macOS
        self.assertEqual(roots, [])                                               # neither honoured on read

    def test_low_4_mutant(self):
        self.mutate("    if sum(1 for k in m if isinstance(k, str) and _fold(k) == _fold(name)) > 1:", "    if False:")
        case, form, roots = self.twice()
        self.assertIsNone(case)
        self.assertEqual(roots, [ABC])                                            # mutant: both kept, one under the other's name

    NUL = "import paths; print(json.dumps([sorted(paths.project_roots()), str(paths.resolve('projects/' + ABC + '/CLAUDE.md'))]))"

    def test_low_5_a_nul_byte_drops_that_entry_only(self):
        self.map({ABC: OWN, DEF: "~/Work/Dig\0ital"})
        self.assertEqual(self.py(self.NUL.replace("ABC", repr(ABC))), [[ABC], str(self.own / "CLAUDE.md")])
        self.assertIn("no folder name can have", self.problem(DEF, "~/Work/Dig\0ital") or "")

    def test_low_5_mutant(self):
        self.mutate('    if "\\0" in v:                                   # Cap\'s LOW 5', '    if False:                                   # Cap\'s LOW 5')
        self.map({ABC: OWN, DEF: "~/Work/Dig\0ital"})
        r = subprocess.run([sys.executable, "-c", f"import sys, json; sys.path.insert(0, 'system/scripts'); {self.NUL.replace('ABC', repr(ABC))}"],
                           cwd=self.v.root, capture_output=True, text=True)
        self.assertIn("embedded null byte", r.stderr)                             # mutant: every project's resolve raises


if __name__ == "__main__":
    unittest.main()
