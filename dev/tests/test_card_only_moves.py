"""#124 F3: only Approve on the live server's own card moves a note, moves it back, or moves an archived report back.

Run: python3 dev/tests/test_card_only_moves.py      (one live server over a throwaway vault; no Chrome)

The mover enforces it (Jarvis's ruling, 16-10-2026): tracker._op_move refuses a move of kind "notes", "notes_back" or
"reports_back" (reach.CARD_ONLY_MOVES) unless the live server wrote its marker in system/guard/ on Approve
(live_server.card_moves_allowed: reach.card_move_marker, naming the card's own proposal file and its SHA-256, under
reach.CARD_MOVE_SECONDS old). What is covered:
- a proposal written by hand into staging (the page's /api/fs, or a file from Terminal), for each of the three kinds: a full
  apply (/api/apply) leaves it in staging and says which file, and the rest still applies (a crash's leftover never stops
  an Apply); tracker.py apply naming it is refused in the dry run, before the backup; nothing moves and the reason is said;
- the card's preview and stage (propose.py check) need no marker;
- Approve on the card still moves the file (Delete note, Move back for a note and for a report), and no marker is left
  afterwards, when the apply succeeds, fails or raises;
- the card's own proposal rewritten under the same name with other bytes before its apply (end to end) never moves;
- a marker for another move, a stale one, one in the future, a symlink, a folder, one naming another proposal or another
  version of it, and no proposal at all never unlock the move;
- Undo still brings a note back (no marker needed); "reports" (BL-03), "archive", "restore" and "rename" (BL-09) are not card
  only and need no marker, but never move a file in a notes folder (#128);
- reach.CARD_ONLY_MOVES are propose.SERVER_CARD_ONLY's kinds; the page and ask creaite can't write system/guard/move-*.
Everything is fictional and temporary.
"""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_notes_delete  # noqa: E402
from test_archive_move_back import DUE, archive_old_files  # noqa: E402
from test_tracker import ABC, action  # noqa: E402

REFUSED = "is moved only by Approve on the live server's approval card"


class CardOnlyMoves(test_notes_delete.NotesDelete):
    pass


for _name in [n for n in dir(test_notes_delete.NotesDelete) if n.startswith("test_")]:
    setattr(CardOnlyMoves, _name, None)                  # NotesDelete's own tests run in their own file


class CardOnly(CardOnlyMoves):
    def hand(self, kind, src, dst, via="fs"):
        """A proposal written into staging by hand: through the page's /api/fs (as any page script could) or as a file."""
        spec = {"source_run": "dashboard", "applied_on_card": True, "items": [],
                "file_changes": {"title": "by hand", "archive": kind, "file_changes_decision": "approved",
                                 "file_ops": [{"op": "move", "from": src, "to": dst}]}}
        rel = f"system/staging/proposed-2026-10-16-hand-{kind}.json"
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

    def assert_refused_both_ways(self, kind, src, dst, there, gone):
        rel = self.hand(kind, src, dst)
        name = Path(rel).name
        before = self.backups()
        r = self.post("/api/apply", {})                                            # a full apply leaves it in staging
        self.assertTrue(r["ok"], r)
        self.assertIn(f"Left in staging, not applied: {name} file_changes_decision: move: {src} {REFUSED}", r["message"])
        self.assertTrue((self.v.root / rel).is_file())
        self.assertTrue(there.is_file())
        self.assertFalse(gone.exists())
        self.assertEqual(self.backups(), before)                                   # nothing else to apply: no backup
        self.hand(kind, src, dst, via="file")                                      # Terminal (or another session), by name
        r = self.run_at("tracker.py", "apply", name)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Apply stopped. Nothing was written.", r.stdout)            # refused in the dry run
        self.assertIn(f"{name} file_changes_decision: move: {src} {REFUSED}", r.stdout)
        self.assertEqual(self.backups(), before)                                   # before the backup
        self.assertTrue(there.is_file())
        self.assertFalse(gone.exists())
        self.assertEqual(self.markers(), [])

    def test_a_a_hand_staged_note_delete_is_refused(self):
        self.new("Hand delete")
        src, dst = f"{ABC}/notes/Hand delete.md", f"{ABC}/99 Archive/notes/Hand delete.md"
        self.assert_refused_both_ways("notes", src, dst, self.folder() / "Hand delete.md", self.archive() / "Hand delete.md")
        d = self.delete(self.post("/api/notes/get", {"path": src}))                   # the card still moves it
        done = self.post("/api/edit/approve", {"card": d["card"]["card"]})
        self.assertTrue(done["ok"], done)
        self.assertTrue((self.archive() / "Hand delete.md").is_file())
        self.assertEqual(self.markers(), [])                                           # nothing left on success
        u = self.post("/api/undo", {"apply_id": done["apply_id"]})                    # Undo needs no marker
        self.assertTrue(u["ok"], u)
        self.assertTrue((self.folder() / "Hand delete.md").is_file())

    def test_b_a_hand_staged_note_move_back_is_refused(self):
        r = self.new("Hand back")
        self.assertTrue(self.post("/api/edit/approve", {"card": self.delete(r)["card"]["card"]})["ok"])
        src, dst = f"{ABC}/99 Archive/notes/Hand back.md", f"{ABC}/notes/Hand back.md"
        self.assert_refused_both_ways("notes_back", src, dst, self.archive() / "Hand back.md", self.folder() / "Hand back.md")
        self.assertTrue(self.post("/api/files/move-back", {"path": dst})["ok"])       # Move back on the card still works
        card = self.post("/api/edit/pending", {})["card"]
        self.assertTrue(self.post("/api/edit/approve", {"card": card["card"]})["ok"])
        self.assertTrue((self.folder() / "Hand back.md").is_file())
        self.assertEqual(self.markers(), [])

    def test_c_a_hand_staged_report_move_back_is_refused(self):
        abc = archive_old_files(self.v.root)                                          # "reports": applied with no marker
        self.assertTrue((abc / "99 Archive" / DUE[1]).is_file())
        stored = f"projects/{abc.name}/{DUE[1]}"
        src = f"projects/{abc.name}/99 Archive/{DUE[1]}"
        self.assert_refused_both_ways("reports_back", src, stored, abc / "99 Archive" / DUE[1], abc / DUE[1])
        self.assertTrue(self.post("/api/files/move-back", {"path": stored})["ok"])   # Move back on the card still works
        card = self.post("/api/edit/pending", {})["card"]
        self.assertTrue(self.post("/api/edit/approve", {"card": card["card"]})["ok"])
        self.assertTrue((abc / DUE[1]).is_file())
        self.assertEqual(self.markers(), [])

    def test_d_no_marker_left_when_the_apply_fails_or_raises(self):
        r = self.new("Fails")
        d = self.delete(r)
        (self.archive()).mkdir(parents=True, exist_ok=True)
        (self.archive() / "Fails.md").write_text("taken after the card went up")    # the apply's own check refuses
        got = self.post("/api/edit/approve", {"card": d["card"]["card"]})
        self.assertFalse(got["ok"], got)
        self.assertEqual(self.markers(), [])
        self.assertTrue((self.folder() / "Fails.md").is_file())
        (self.archive() / "Fails.md").unlink()
        got = self.py_json(
            "import pathlib, archive, live_server as ls, paths\n"
            f"rel = {f'{ABC}/notes/Fails.md'!r}\n"
            "spec, why = archive.note_delete_spec(rel)\n"
            "card, why = ls.server_edit_card('t', json.dumps(spec).encode('utf-8'))\n"
            "seen, real = [], ls.run\n"
            "def run(script, *args):\n"
            "    if script == 'tracker.py' and args and args[0] == 'apply':\n"
            "        seen.append(sorted(f.name for f in paths.GUARD.glob('move-*')))\n"
            "        raise RuntimeError('the apply blew up')\n"
            "    return real(script, *args)\n"
            "ls.run = run\n"
            "try:\n"
            "    ls.edit_apply(ls.EDITS[card['card']]); raised = None\n"
            "except RuntimeError as e:\n"
            "    raised = str(e)\n"
            "print(json.dumps([seen, raised, sorted(f.name for f in paths.GUARD.glob('move-*'))]))")
        seen, raised, after = got
        self.assertEqual(len(seen), 1)
        self.assertEqual(len(seen[0]), 1)                                              # one marker while the apply ran
        self.assertEqual(raised, "the apply blew up")
        self.assertEqual(after, [])                                                    # and gone after it raised
        self.assertTrue((self.folder() / "Fails.md").is_file())

    def test_e_only_the_exact_fresh_marker_unlocks(self):
        self.new("Marker")
        got = self.py_json(
            "import hashlib, os, pathlib, time, reach, tracker, paths\n"
            f"src, dst = {f'{ABC}/notes/Marker.md'!r}, {f'{ABC}/99 Archive/notes/Marker.md'!r}\n"
            "fop, blk = {'op': 'move', 'from': src, 'to': dst}, {'archive': 'notes'}\n"
            "prop = paths.STAGING / 'proposed-2026-10-16-marker.json'\n"
            "prop.write_text(json.dumps({'items': [], 'file_changes': {**blk, 'file_ops': [fop]}}))\n"
            "other = paths.STAGING / 'proposed-2026-10-16-other.json'; other.write_text(prop.read_text())\n"
            "sha = hashlib.sha256(prop.read_bytes()).hexdigest()\n"
            "m = reach.card_move_marker('notes', src, dst); paths.GUARD.mkdir(parents=True, exist_ok=True)\n"
            "def put(body=None, name='proposed-2026-10-16-marker.json'):\n"
            "    m.unlink(missing_ok=True); m.write_text(json.dumps(body or {'proposal': name, 'sha256': sha}))\n"
            "def p(f=prop, b=blk, o=fop): return tracker.card_move_problem(o, b, f)\n"
            "out = {}\n"
            "out['none'] = p()\n"
            "put(); out['exact'] = p()\n"
            "out['no_proposal'] = p(None)\n"
            "out['other_proposal'] = p(other)\n"
            "put(name='proposed-2026-10-16-other.json'); out['bound_elsewhere'] = p()\n"
            "put({'proposal': prop.name, 'sha256': '0' * 64}); out['other_version'] = p()\n"
            "put(); out['other_move'] = p(o={'op': 'move', 'from': src, 'to': dst.replace('Marker', 'Marker-2')})\n"
            "out['other_kind'] = p(b={'archive': 'notes_back'})\n"
            "t = time.time() - reach.CARD_MOVE_SECONDS - 5; os.utime(m, (t, t)); out['stale'] = p()\n"
            "t = time.time() + 120; os.utime(m, (t, t)); out['future'] = p()\n"
            "real = paths.GUARD / 'real'; put(); m.rename(real); os.symlink(real, m); out['symlink'] = p()\n"
            "m.unlink(); real.unlink(); m.mkdir(); out['folder'] = p(); m.rmdir()\n"
            "put('not json'); m.write_text('not json'); out['garbled'] = p()\n"
            "m.unlink()\n"
            "out['free'] = {k: tracker.card_move_problem(fop, {'archive': k}, None) for k in ('reports', 'archive', 'restore', 'rename')}\n"
            "mins = {'op': 'move', 'from': src.replace('/notes/', '/minutes/'), 'to': dst.replace('/notes/', '/minutes/')}\n"
            "out['free_elsewhere'] = {k: tracker.card_move_problem(mins, {'archive': k}, None) for k in ('reports', 'archive', 'restore', 'rename')}\n"
            "prop.unlink(); other.unlink()\n"
            "print(json.dumps(out))")
        self.assertIn(REFUSED, got["none"])
        self.assertIsNone(got["exact"])                                                # only this one
        for k in ("no_proposal", "other_proposal", "bound_elsewhere", "other_version", "other_move", "other_kind", "stale",
                  "future", "symlink", "folder", "garbled"):
            self.assertIn(REFUSED, got[k] or "", k)
        self.assertEqual(got["free_elsewhere"], {"reports": None, "archive": None, "restore": None, "rename": None})
        for k, why in got["free"].items():                                            # #128: never a note, by any other kind
            self.assertIn("is in a notes folder: a note is moved only by Delete note or Move back", why or "", k)

    def test_g_a_leftover_never_stops_a_full_apply(self):
        """An Approve that stopped before its apply finished (a crash) leaves an approved card-only proposal in staging with no
        marker: a full Apply leaves it there, says which file, and applies the rest; named, it is refused before the backup."""
        self.new("Leftover")
        src, dst = f"{ABC}/notes/Leftover.md", f"{ABC}/99 Archive/notes/Leftover.md"
        left = Path(self.hand("notes", src, dst, via="file")).name
        normal = self.v.root / "system/staging/proposed-2026-10-16-normal.json"
        normal.write_text(json.dumps({"source_run": "dashboard", "items": [action(1, description="Send the plan")]}),
                          encoding="utf-8")
        before = self.backups()
        r = self.post("/api/apply", {})
        self.assertTrue(r["ok"], r)
        self.assertIn(f"Left in staging, not applied: {left} file_changes_decision: move: {src} {REFUSED}", r["message"])
        self.assertFalse(normal.exists())                                              # the normal one applied
        self.assertEqual(len(self.backups()), len(before) + 1)
        self.assertTrue((self.v.root / "system/staging" / left).is_file())             # the leftover stays, unapplied
        self.assertTrue((self.folder() / "Leftover.md").is_file())
        self.assertFalse((self.archive() / "Leftover.md").exists())
        before = self.backups()
        r = self.post("/api/apply", {})                                                # again: still no failure, no backup
        self.assertTrue(r["ok"], r)
        self.assertIn(f"Left in staging, not applied: {left}", r["message"])
        self.assertEqual(self.backups(), before)
        d = self.delete(self.post("/api/notes/get", {"path": src}))                   # the card's own Approve still works
        done = self.post("/api/edit/approve", {"card": d["card"]["card"]})
        self.assertTrue(done["ok"], done)
        self.assertTrue((self.archive() / "Leftover.md").is_file())
        self.assertEqual(self.markers(), [])

    def test_h_the_card_preview_and_stage_need_no_marker(self):
        """check_file_op (propose.py check runs it for the card's preview and stage, before Approve) never asks for a marker;
        the card goes up with none written (and every Approve above stages its proposal before the marker exists)."""
        self.new("Previewed")
        got = self.py_json(
            "import archive, tracker\n"
            f"spec, why = archive.note_delete_spec({f'{ABC}/notes/Previewed.md'!r})\n"
            "fc = spec['file_changes']\n"
            "for op in fc['file_ops']: tracker.check_file_op(op, fc)\n"
            "print(json.dumps([why, len(fc['file_ops'])]))")
        self.assertEqual(got, [None, 1])
        d = self.delete(self.post("/api/notes/get", {"path": f"{ABC}/notes/Previewed.md"}))
        self.assertTrue(d["ok"], d)
        self.assertEqual(self.markers(), [])

    def test_i_the_same_name_with_other_bytes_never_moves(self):
        """End to end through edit_apply: the card's staged proposal rewritten under the same name just before tracker.py apply
        runs (the markers already written) is refused when its bytes differ, even saying the same move; identical bytes move."""
        def approve(name, rewrite):
            self.new(name)
            return self.py_json(
                "import archive, live_server as ls, paths\n"
                f"rel = {f'{ABC}/notes/{name}.md'!r}\n"
                "spec, why = archive.note_delete_spec(rel)\n"
                "card, why = ls.server_edit_card('t', json.dumps(spec).encode('utf-8'))\n"
                "seen, real = [], ls.run\n"
                "def run(script, *args):\n"
                "    if script == 'tracker.py' and args and args[0] == 'apply':\n"
                "        f = paths.STAGING / args[1]; raw = f.read_bytes()\n"
                "        seen.append(sorted(m.name for m in paths.GUARD.glob('move-*')))\n"
                f"        f.write_bytes({'json.dumps(json.loads(raw), indent=4).encode()' if rewrite == 'other' else 'raw'})\n"
                "        seen.append(f.read_bytes() == raw)\n"
                "    return real(script, *args)\n"
                "ls.run = run\n"
                "out = ls.edit_apply(ls.EDITS[card['card']])\n"
                "print(json.dumps([seen, out.get('ok'), out.get('message'), sorted(m.name for m in paths.GUARD.glob('move-*'))]))")
        seen, ok, message, after = approve("Other bytes", "other")
        self.assertEqual(len(seen[0]), 1)                                              # the marker was there for the apply
        self.assertFalse(seen[1])                                                      # and the bytes under the name changed
        self.assertFalse(ok, message)
        self.assertIn(REFUSED, message)
        self.assertTrue((self.folder() / "Other bytes.md").is_file())                 # the note stays
        self.assertFalse((self.archive() / "Other bytes.md").exists())
        self.assertEqual(after, [])
        seen, ok, message, after = approve("Same bytes", "same")
        self.assertEqual(len(seen[0]), 1)
        self.assertTrue(seen[1])
        self.assertTrue(ok, message)                                                   # identical bytes: it moves
        self.assertFalse((self.folder() / "Same bytes.md").exists())
        self.assertTrue((self.archive() / "Same bytes.md").is_file())
        self.assertEqual(after, [])

    def test_j_the_marker_binds_the_bytes_the_apply_loaded(self):
        """The SHA-256 compared is of the bytes the apply loaded (and so applies), not of a second read: a file swapped after
        the load, back to the card's bytes, is refused; the card's bytes loaded and then swapped are still the card's."""
        self.new("Loaded")
        got = self.py_json(
            "import hashlib, reach, tracker, paths\n"
            f"src, dst = {f'{ABC}/notes/Loaded.md'!r}, {f'{ABC}/99 Archive/notes/Loaded.md'!r}\n"
            "fop, blk = {'op': 'move', 'from': src, 'to': dst}, {'archive': 'notes'}\n"
            "prop = paths.STAGING / 'proposed-2026-10-16-loaded.json'\n"
            "card = json.dumps({'items': [], 'file_changes': {**blk, 'file_ops': [fop]}}).encode()\n"
            "other = card.replace(b'\"items\": []', b'\"items\": [], \"x\": 1')\n"
            "m = reach.card_move_marker('notes', src, dst); paths.GUARD.mkdir(parents=True, exist_ok=True)\n"
            "m.write_text(json.dumps({'proposal': prop.name, 'sha256': hashlib.sha256(card).hexdigest()}))\n"
            "def p(): return tracker.card_move_problem(fop, blk, prop)\n"
            "out = {}\n"
            "prop.write_bytes(other); tracker.load(prop, bind=True); prop.write_bytes(card); out['swapped_back'] = p()\n"
            "prop.write_bytes(card); tracker.load(prop, bind=True); prop.write_bytes(other); out['card_loaded'] = p()\n"
            "prop.write_bytes(other); tracker.load(prop); out['unbound_read'] = p()\n"
            "m.unlink(); prop.unlink(); tracker.READ_SHA.clear()\n"
            "print(json.dumps(out))")
        self.assertIn(REFUSED, got["swapped_back"] or "")
        self.assertIsNone(got["card_loaded"])
        self.assertIsNone(got["unbound_read"])                  # only the apply's own load binds (the last bound one: the card's)

    def test_k_the_guard_folder_is_private_and_never_a_symlink(self):
        """card_moves_allowed makes system/guard 0700 when it has to make it; with system/guard a symlink, Approve writes no
        marker (the note stays) and tracker refuses a marker reached through it."""
        self.new("Guarded")
        got = self.py_json(
            "import os, shutil, archive, live_server as ls, reach, tracker, paths\n"
            f"spec, why = archive.note_delete_spec({f'{ABC}/notes/Guarded.md'!r})\n"
            "fop = spec['file_changes']['file_ops'][0]\n"
            "prop = paths.STAGING / 'proposed-2026-10-16-guarded.json'; prop.write_text(json.dumps(spec))\n"
            "g, saved, elsewhere = paths.GUARD, paths.SYSTEM / 'guard-saved', paths.SYSTEM / 'elsewhere'\n"
            "had = g.exists()\n"
            "if had: g.rename(saved)\n"
            "try:\n"
            "    with ls.card_moves_allowed(prop.name):\n"
            "        mode = oct(g.stat().st_mode & 0o777); inside = len(list(g.glob('move-*')))\n"
            "    shutil.rmtree(g)\n"
            "    elsewhere.mkdir(); os.symlink(elsewhere, g)\n"
            "    card, why = ls.server_edit_card('t', json.dumps(spec).encode('utf-8'))\n"
            "    out = ls.edit_apply(ls.EDITS[card['card']])\n"
            "    left = sorted(f.name for f in elsewhere.iterdir())\n"
            "    m = reach.card_move_marker('notes', fop['from'], fop['to'])\n"
            "    m.write_text(json.dumps({'proposal': prop.name, 'sha256': tracker.file_hash(prop)}))     # right in every other way\n"
            "    t = tracker.card_move_problem(fop, {'archive': 'notes'}, prop)\n"
            "    m.unlink()\n"
            "finally:\n"
            "    if g.is_symlink(): g.unlink()\n"
            "    shutil.rmtree(elsewhere, ignore_errors=True)\n"
            "    if had: saved.rename(g)\n"
            "g.mkdir(mode=0o700, exist_ok=True); m.write_text(json.dumps({'proposal': prop.name, 'sha256': tracker.file_hash(prop)}))\n"
            "control = tracker.card_move_problem(fop, {'archive': 'notes'}, prop)            # the same marker, the real folder\n"
            "m.unlink(); prop.unlink()\n"
            "print(json.dumps([mode, inside, out.get('ok'), out.get('message'), left, t, control]))")
        mode, inside, ok, message, left, t, control = got
        self.assertIsNone(control)
        self.assertEqual((mode, inside), ("0o700", 1))
        self.assertFalse(ok, message)
        self.assertIn("the approval couldn't be recorded", message)
        self.assertEqual(left, [])                                                     # nothing written through the symlink
        self.assertIn(REFUSED, t or "")
        self.assertTrue((self.folder() / "Guarded.md").is_file())

    def test_f_the_lists_agree_and_nobody_else_writes_the_marker(self):
        got = self.py_json(
            "import propose, reach\n"
            "m = reach.paths.rel(reach.card_move_marker('notes', 'a', 'b'))\n"
            "print(json.dumps([list(reach.CARD_ONLY_MOVES), list(propose.SERVER_CARD_ONLY), m,\n"
            "                  {op: reach.classify(m, op)[0] for op in ('create', 'change', 'delete', 'move')}]))")
        card_only, server_only, marker, verdicts = got
        self.assertEqual(card_only, server_only)
        self.assertTrue(marker.startswith("system/guard/move-"), marker)
        self.assertEqual(set(verdicts.values()), {"never"})                           # ask creaite: never
        for op in ("write", "append", "upload", "remove"):                             # the page: no FS_RULES pattern for it
            r = self.post("/api/fs", {"op": op, "path": marker, "text": "{}", "data": ""})
            self.assertEqual(r.get("status"), 403, (op, r))
        self.assertFalse((self.v.root / marker).exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
