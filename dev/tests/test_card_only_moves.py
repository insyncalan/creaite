"""#124 F3: only Approve on the live server's own card moves a note, moves it back, or moves an archived report back.

Run: python3 dev/tests/test_card_only_moves.py      (one live server over a throwaway vault; no Chrome)

The mover enforces it (Jarvis's ruling, 16-10-2026): tracker._op_move refuses a move of kind "notes", "notes_back" or
"reports_back" (reach.CARD_ONLY_MOVES) unless the live server wrote its marker in system/guard/ on Approve
(live_server.card_moves_allowed: reach.card_move_marker, naming the card's own proposal file and its SHA-256, under
reach.CARD_MOVE_SECONDS old). What is covered:
- a proposal written by hand into staging (the page's /api/fs, or a file from Terminal) is refused by /api/apply and by
  tracker.py apply, for each of the three kinds: nothing moves and the reason is said;
- Approve on the card still moves the file (Delete note, Move back for a note and for a report), and no marker is left
  afterwards, when the apply succeeds, fails or raises;
- a marker for another move, a stale one, one in the future, a symlink, a folder, one naming another proposal or another
  version of it, and no proposal at all never unlock the move;
- Undo still brings a note back (no marker needed); "reports" (BL-03), "archive", "restore" and "rename" (BL-09) are not card
  only and need no marker;
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
from test_tracker import ABC  # noqa: E402

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

    def assert_refused_both_ways(self, kind, src, dst, there, gone):
        self.hand(kind, src, dst)
        r = self.post("/api/apply", {})
        self.assertFalse(r["ok"], r)
        self.assertIn(REFUSED, r["message"])
        self.assertTrue(there.is_file())
        self.assertFalse(gone.exists())
        self.hand(kind, src, dst, via="file")                                      # Terminal (or another session)
        r = self.run_at("tracker.py", "apply", f"proposed-2026-10-16-hand-{kind}.json")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn(REFUSED, r.stdout)
        self.assertTrue(there.is_file())
        self.assertFalse(gone.exists())
        self.assertEqual(self.markers(), [])

    def test_a_a_hand_staged_note_delete_is_refused(self):
        self.new("Hand delete")
        src, dst = f"{ABC}/notes/Hand delete.md", f"{ABC}/_Archive/notes/Hand delete.md"
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
        src, dst = f"{ABC}/_Archive/notes/Hand back.md", f"{ABC}/notes/Hand back.md"
        self.assert_refused_both_ways("notes_back", src, dst, self.archive() / "Hand back.md", self.folder() / "Hand back.md")
        self.assertTrue(self.post("/api/files/move-back", {"path": dst})["ok"])       # Move back on the card still works
        card = self.post("/api/edit/pending", {})["card"]
        self.assertTrue(self.post("/api/edit/approve", {"card": card["card"]})["ok"])
        self.assertTrue((self.folder() / "Hand back.md").is_file())
        self.assertEqual(self.markers(), [])

    def test_c_a_hand_staged_report_move_back_is_refused(self):
        abc = archive_old_files(self.v.root)                                          # "reports": applied with no marker
        self.assertTrue((abc / "_Archive" / DUE[1]).is_file())
        stored = f"projects/{abc.name}/{DUE[1]}"
        src = f"projects/{abc.name}/_Archive/{DUE[1]}"
        self.assert_refused_both_ways("reports_back", src, stored, abc / "_Archive" / DUE[1], abc / DUE[1])
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
            f"src, dst = {f'{ABC}/notes/Marker.md'!r}, {f'{ABC}/_Archive/notes/Marker.md'!r}\n"
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
            "prop.unlink(); other.unlink()\n"
            "print(json.dumps(out))")
        self.assertIn(REFUSED, got["none"])
        self.assertIsNone(got["exact"])                                                # only this one
        for k in ("no_proposal", "other_proposal", "bound_elsewhere", "other_version", "other_move", "other_kind", "stale",
                  "future", "symlink", "folder", "garbled"):
            self.assertIn(REFUSED, got[k] or "", k)
        self.assertEqual(got["free"], {"reports": None, "archive": None, "restore": None, "rename": None})

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
