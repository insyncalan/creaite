"""#128: a note's file is removed, written or copied by an apply only with the live server's card marker.

Run: python3 dev/tests/test_notes_card_only_ops.py      (one live server over a throwaway vault, and OneDrive-style vaults; no Chrome)

#124 made moves of notes card only. A proposal written into staging by hand (the page's /api/fs, or a file from Terminal) could
still remove a note, write over it, or copy it elsewhere and remove the original. tracker.card_op_problem now refuses a remove, a
write, or a copy whose source is at or below any notes folder unless live_server.card_moves_allowed wrote its marker on Approve
of the card's own proposal (tracker.card_marks), bound to that proposal's bytes and removed afterwards. Covered:
- a hand-staged remove: /api/apply leaves it in staging and says why; tracker.py apply naming it is refused before the backup;
  Approve on the card removes it (the marker exists only during that apply) and the same proposal again is refused;
- copy then remove, and a write over a note, refused; the same ops on a file outside the notes folder apply (control);
- the Notes tab still creates, saves, renames and deletes (no marker involved; the delete is #124's card);
- `..`, a symlink to a note or to the notes folder, a hard link, case variants, a subfolder and the portfolio's notes are all
  inside; a minutes file, an inbox file and the _Archive are not;
- locations.folders.notes on, inside or around a minutes or reports folder: refused by propose.py setting and the page's
  settings save, and with such a mapping a "reports" move of a file in it is refused by the mover.
Everything is fictional and temporary.
"""
import json
import os
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_card_only_moves  # noqa: E402
from test_onedrive_projects import OneDriveCase, touch  # noqa: E402
from test_tracker import ABC  # noqa: E402

IN_NOTES = "is in a notes folder: a note is changed through the Notes tab, or by Approve on the live server's approval card"


class NoteOps(test_card_only_moves.CardOnlyMoves):
    def hand(self, ops, via="fs", name="ops"):
        """A proposal written into staging by hand, approved, with these file operations."""
        spec = {"source_run": "dashboard", "applied_on_card": True, "items": [],
                "file_changes": {"title": "by hand", "file_changes_decision": "approved", "file_ops": ops}}
        rel = f"system/staging/proposed-2026-10-16-hand-{name}.json"
        if via == "fs":
            self.assertEqual(self.post("/api/fs", {"op": "write", "path": rel, "text": json.dumps(spec)}), {"ok": True})
        else:
            (self.v.root / rel).write_text(json.dumps(spec), encoding="utf-8")
        self.addCleanup(lambda: (self.v.root / rel).unlink(missing_ok=True))
        return rel

    def markers(self):
        g = self.v.root / "system/guard"
        return sorted(f.name for f in g.glob("move-*")) if g.is_dir() else []

    def backups(self):
        return sorted(f.name for f in (self.v.root / "system/backups").glob("tracker-*-apply*.db"))

    def refused_both_ways(self, ops, first, name):
        """Refused by a full /api/apply (left in staging) and by tracker.py apply naming it (before the backup)."""
        rel = self.hand(ops, name=name)
        before = self.backups()
        r = self.post("/api/apply", {})
        self.assertTrue(r["ok"], r)
        self.assertIn(f"Left in staging, not applied: {Path(rel).name} file_changes_decision: {first}", r["message"])
        self.assertTrue((self.v.root / rel).is_file())
        self.hand(ops, via="file", name=name)
        r = self.run_at("tracker.py", "apply", Path(rel).name)
        self.assertNotEqual(r.returncode, 0, r.stdout)
        self.assertIn("Apply stopped. Nothing was written.", r.stdout)
        self.assertIn(first, r.stdout)
        self.assertEqual(self.backups(), before)
        self.assertEqual(self.markers(), [])

    def test_a_a_hand_staged_remove_is_refused_and_the_card_removes_once(self):
        self.new("Remove me")
        rel = f"{ABC}/notes/Remove me.md"
        note = self.folder() / "Remove me.md"
        text = note.read_text()
        self.refused_both_ways([{"op": "remove", "path": rel}], f"remove: {rel} {IN_NOTES}", "remove")
        self.assertEqual(note.read_text(), text)
        got = self.py_json(                                       # the card: Approve writes the marker, the apply removes it
            "import live_server as ls, paths, tracker\n"
            f"spec = {{'items': [], 'file_changes': {{'title': 'Remove a note', 'file_ops': [{{'op': 'remove', 'path': {rel!r}}}]}}}}\n"
            "card, why = ls.server_edit_card('t', json.dumps(spec).encode('utf-8'))\n"
            "seen, real = [], ls.run\n"
            "def run(script, *args):\n"
            "    if script == 'tracker.py' and args and args[0] == 'apply':\n"
            "        seen.append([args[1], (paths.STAGING / args[1]).read_bytes().decode(), sorted(m.name for m in paths.GUARD.glob('move-*'))])\n"
            "    return real(script, *args)\n"
            "ls.run = run\n"
            "out = ls.edit_apply(ls.EDITS[card['card']])\n"
            "print(json.dumps([why, out.get('ok'), out.get('message'), seen, sorted(m.name for m in paths.GUARD.glob('move-*'))]))")
        why, ok, message, seen, after = got
        self.assertIsNone(why)
        self.assertTrue(ok, message)
        self.assertFalse(note.exists())                                          # removed on the card
        self.assertEqual(len(seen), 1)
        self.assertEqual(len(seen[0][2]), 1)                                     # one marker during the apply
        self.assertEqual(after, [])                                              # and none after
        name, raw = seen[0][0], seen[0][1]
        note.write_text(text)                                                    # the same bytes again, same name: refused
        (self.v.root / "system/staging" / name).write_text(raw, encoding="utf-8")
        self.addCleanup(lambda: (self.v.root / "system/staging" / name).unlink(missing_ok=True))
        r = self.run_at("tracker.py", "apply", name)
        self.assertNotEqual(r.returncode, 0, r.stdout)
        self.assertIn(f"remove: {rel} {IN_NOTES}", r.stdout)
        self.assertEqual(note.read_text(), text)

    def test_b_copy_then_remove_and_a_write_over_a_note_are_refused(self):
        self.new("Keep me")
        rel = f"{ABC}/notes/Keep me.md"
        note = self.folder() / "Keep me.md"
        text = note.read_text()
        self.refused_both_ways([{"op": "copy", "from": rel, "to": "inbox/Keep me.md"}, {"op": "remove", "path": rel}],
                               f"copy: {rel} {IN_NOTES}", "copy")
        self.assertFalse((self.v.root / "inbox/Keep me.md").exists())
        self.refused_both_ways([{"op": "write", "path": rel, "content": "gone\n", "previous": text}], f"write: {rel} {IN_NOTES}",
                               "write")
        self.assertEqual(note.read_text(), text)
        plain = self.v.root / "inbox/Plain.md"                                   # control: the same ops elsewhere apply
        plain.write_text("plain\n")
        self.hand([{"op": "copy", "from": "inbox/Plain.md", "to": "inbox/Plain copy.md"}, {"op": "remove", "path": "inbox/Plain.md"},
                   {"op": "write", "path": "inbox/New.md", "content": "new\n"}], via="file", name="ctl")
        r = self.run_at("tracker.py", "apply", "proposed-2026-10-16-hand-ctl.json")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertFalse(plain.exists())
        self.assertEqual((self.v.root / "inbox/Plain copy.md").read_text(), "plain\n")
        self.assertEqual((self.v.root / "inbox/New.md").read_text(), "new\n")
        self.assertEqual(note.read_text(), text)

    def test_c_the_notes_tab_still_creates_saves_renames_and_deletes(self):
        r = self.new("Tab note")
        rel = r["note"]["path"]
        s = self.post("/api/notes/save", {"path": rel, "body": "Autosaved.\n", "base": r["base"]})
        self.assertTrue(s["ok"], s)
        s = self.post("/api/notes/save", {"path": rel, "changes": {"title": "Tab note renamed"}, "base": s["base"]})
        self.assertTrue(s["ok"], s)
        m = self.post("/api/notes/rename", {"path": rel, "base": s["base"], "old": "Tab note"})
        self.assertTrue(m["ok"], m)
        self.assertTrue(m["renamed"])
        self.assertIn("Autosaved.", (self.v.root / m["note"]["path"]).read_text())
        d = self.post("/api/notes/delete", {"path": m["note"]["path"], "base": m["base"]})
        self.assertTrue(d["ok"], d)
        done = self.post("/api/edit/approve", {"card": d["card"]["card"]})
        self.assertTrue(done["ok"], done)
        self.assertTrue((self.archive() / "Tab note renamed.md").is_file())
        self.assertEqual(self.markers(), [])

    def test_d_path_tricks_are_inside_the_notes_folder(self):
        self.new("Tricky")
        note = self.folder() / "Tricky.md"
        text = note.read_text()
        inbox = self.v.root / "inbox"
        os.symlink(note, inbox / "link.md")
        os.symlink(self.folder(), inbox / "notes-dir")
        os.link(note, inbox / "hard.md")
        (self.folder() / "sub").mkdir()
        touch(self.folder() / "sub" / "Deep.md", "deep\n")
        touch(self.folder() / "_images" / "pic.png", b"\x89PNG\r\n\x1a\n")
        (self.v.root / "inbox/Plain.md").write_text("plain\n")
        self.addCleanup(lambda: [(inbox / n).unlink(missing_ok=True) for n in ("link.md", "notes-dir", "hard.md", "Plain.md")])
        folder = ABC.split("/", 1)[1]
        cases = {"dotdot": f"{ABC}/minutes/../notes/Tricky.md", "upper": f"{ABC}/NOTES/Tricky.md", "mixed": f"{ABC}/Notes/TRICKY.md",
                 "project_case": f"projects/{folder.upper()}/notes/Tricky.md", "symlink": "inbox/link.md",
                 "symlinked_folder": "inbox/notes-dir/Tricky.md", "sub": f"{ABC}/notes/sub/Deep.md",
                 "images": f"{ABC}/notes/_images/pic.png", "portfolio": "projects/_portfolio/notes/Thought.md",
                 "plain": "inbox/Plain.md", "minutes": f"{ABC}/minutes/x.docx", "archive": f"{ABC}/_Archive/notes/Tricky.md",
                 "hard_remove": "inbox/hard.md"}
        got = self.py_json(
            "import tracker\n"
            f"c = {json.dumps(cases)}\n"
            "out = {k: tracker.in_notes_folder(v) for k, v in c.items()}\n"
            "out['hard_write'] = tracker.in_notes_folder('inbox/hard.md', links=True)\n"
            "print(json.dumps(out))")
        for k in ("dotdot", "upper", "mixed", "project_case", "symlink", "symlinked_folder", "sub", "images", "portfolio",
                  "hard_write"):
            self.assertTrue(got[k], k)
        for k in ("plain", "minutes", "archive", "hard_remove"):
            self.assertFalse(got[k], k)
        # end to end: removing a symlink to a note would remove the note itself (safe_path follows it); a write through a hard
        # link would change it
        self.refused_both_ways([{"op": "remove", "path": "inbox/link.md"}], f"remove: inbox/link.md {IN_NOTES}", "link")
        self.refused_both_ways([{"op": "write", "path": "inbox/hard.md", "content": "x\n", "previous": text}],
                               f"write: inbox/hard.md {IN_NOTES}", "hard")
        self.refused_both_ways([{"op": "remove", "path": f"{ABC}/NOTES/../notes/sub/Deep.md"}],
                               f"remove: {ABC}/NOTES/../notes/sub/Deep.md {IN_NOTES}", "deep")
        self.assertEqual(note.read_text(), text)
        self.assertTrue((self.folder() / "sub" / "Deep.md").is_file())


class NotesMapping(OneDriveCase):
    """locations.folders.notes must be a folder of its own (#124 doctor check, #128 refused where it is saved and used)."""

    def test_e_the_clash_check(self):
        got = self.py(
            "import paths\n"
            "f = paths.locations()['folders']\n"
            "c = {'own': '08 Notes', 'minutes': f['minutes'], 'minutes_case': f['minutes'].upper(), 'reports_parent': '04 Reporting',\n"
            "     'in_minutes': f['minutes'] + '/Notes', 'slash': f['weekly_reports'] + '/', 'dot': '.'}\n"
            "print(json.dumps({k: paths.notes_folder_clash({**f, 'notes': v}) for k, v in c.items()}))")
        self.assertEqual(got["own"], [])
        for k in ("minutes", "minutes_case", "reports_parent", "in_minutes", "slash", "dot"):
            self.assertTrue(got[k], k)
        self.assertIn("minutes", " ".join(got["minutes"]))
        self.assertIn("weekly_reports", " ".join(got["reports_parent"]))

    def test_e_propose_setting_and_the_page_save_refuse_a_clash(self):
        cfg = self.v.root / "system/config/settings.json"
        before = cfg.read_text()
        r = self.v.run("setting", "locations.folders.minutes", "08 notes", script="propose.py", ok=False)   # notes: 08 Notes
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Not saved: the notes folder would also be the minutes (08 notes) folder", r.stdout + r.stderr)
        self.assertEqual(cfg.read_text(), before)
        self.v.run("setting", "locations.folders.minutes", "02 Meetings/Minutes 2", script="propose.py")   # control: no clash
        self.assertEqual(json.loads(cfg.read_text())["locations"]["folders"]["minutes"], "02 Meetings/Minutes 2")
        data = json.loads(cfg.read_text())
        clash = json.dumps({**data, "locations": {**data["locations"], "folders": {**data["locations"]["folders"], "notes": "04 Reporting"}}})
        other = json.dumps({**data, "logging": {**(data.get("logging") or {}), "level": "debug"}})
        got = self.py(
            "import live_server as ls, paths\n"
            f"print(json.dumps([ls.settings_notes_clash(paths.SETTINGS, {clash!r}), ls.settings_notes_clash(paths.SETTINGS, {other!r})]))")
        self.assertIn("Not saved: the notes folder would also be the", got[0])
        self.assertIsNone(got[1])                                                # another setting saves

    def test_e_the_mover_refuses_a_reports_move_of_a_file_in_a_shared_folder(self):
        cfg = self.v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text())
        weekly = data["locations"]["folders"]["weekly_reports"]
        report = touch(self.eng("ABC", weekly, "2025-01-03 Weekly report.docx"), b"PK")
        eng = self.eng("ABC").name
        fop = {"op": "move", "from": f"projects/{eng}/{weekly}/{report.name}", "to": f"projects/{eng}/_Archive/{weekly}/{report.name}"}
        code = f"import tracker\nprint(json.dumps(tracker.card_move_problem({fop!r}, {{'archive': 'reports'}}, None)))"
        self.assertIsNone(self.py(code))                                         # control: notes in a folder of their own
        data["locations"]["folders"]["notes"] = weekly                           # saved by hand, past the refusals
        cfg.write_text(json.dumps(data, indent=2))
        self.assertIn("is in a notes folder: a note is moved only by Delete note or Move back", self.py(code) or "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
