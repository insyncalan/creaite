"""#175: the Notes autosave follow-up, the server side. Over a throwaway vault; no browser, no live server process.

Run: python3 dev/tests/test_notes_175.py

  - Activity (M1): /api/changes/list shows one row per editing session (the same file, session and backup): its latest save, with
    `saves` and `first_at`; a save without a session, another session, a capped session's next one and an ask creaite change
    each keep their own row; the files log still has one line per save; the row's Restore (its button, the latest save's id)
    puts the file back as it was before the session began;
  - old note drafts (L1): retire_note_drafts moves only the Notes tab's old <16 hex>.json (and .json.tmp) drafts, regular files
    directly in system/staging/drafts/notes/, into one file-change backup with one "cleanup" line in the files log; the Capture
    drawer's capture-*.json, any other name, a subfolder, a symlink and a draft reach.confidential_places holds (a confidential
    note's, or one whose note is gone: fail closed) stay; nothing to do writes nothing; the clean-up is not a change Activity
    lists or Restore touches; a confidential draft stays where it is, byte for byte (Alan, 17-10-2026); the live server calls
    it at start-up, and a failure there is logged and never stops the server.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_tracker import ABC, Vault  # noqa: E402

NOTE = f"{ABC}/notes/Plan.md"
OTHER = f"{ABC}/notes/Other.md"
WHY = "a note saved in the Notes tab"
DRAFTS = "system/staging/drafts/notes"
HEX = "0123456789abcdef"


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        for rel in (NOTE, OTHER):
            p = self.v.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("---\ntitle: Plan\n---\nbefore\n", encoding="utf-8")

    def tearDown(self):
        self.v.cleanup()

    def py(self, code):
        src = (f"import sys, json; sys.path.insert(0, {str(self.v.root / 'system/scripts')!r})\nimport filechange, reach\n{code}")
        r = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True, cwd=tempfile.gettempdir())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def save(self, text, session="s-0001-abcd", path=NOTE, via="dashboard"):
        ch = {"op": "edit", "path": path, "data": text.encode(), "why": WHY}
        if session:
            ch["session"] = f"{path}:{session}"
        code, msg = self.py(f"print(json.dumps(filechange.perform({ch!r}, via={via!r})))")
        self.assertEqual(code, 0, msg)

    def log(self):
        p = self.v.root / "system/config/files-log.jsonl"
        return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []

    def age(self, index, minutes):
        p = self.v.root / "system/config/files-log.jsonl"
        rows = self.log()
        rows[index]["at"] = (datetime.now() - timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")
        p.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")

    def listed(self):
        """What /api/changes/list answers, from the route itself."""
        return self.py("import live_server\nclass H:\n    def send(self, code, body):\n        self.out = (code, body)\n"
                       "h = H()\nlive_server.changes_list_route(h, {})\nprint(json.dumps(h.out))")


class ActivityRows(Base):
    def test_one_row_per_editing_session_with_a_count(self):
        for i in range(5):
            self.save(f"a {i}\n")
        for i in range(3):
            self.save(f"b {i}\n", session="s-0002-abcd", path=OTHER)
        self.save("plain\n", session=None)
        self.assertEqual(len([e for e in self.log() if e.get("op") == "edit"]), 9, "the files log keeps one line per save")
        code, body = self.listed()
        self.assertEqual(code, 200)
        rows = body["changes"]
        self.assertEqual(len(rows), 3, rows)
        edits = [e for e in self.log() if e.get("op") == "edit"]
        self.assertEqual([r["id"] for r in rows], [edits[8]["id"], edits[7]["id"], edits[4]["id"]], "newest first, latest saves")
        self.assertEqual((rows[2]["saves"], rows[2]["first_at"]), (5, edits[0]["at"]))
        self.assertEqual((rows[1]["saves"], rows[1]["first_at"]), (3, edits[5]["at"]))
        self.assertNotIn("saves", rows[0], "a save without a session is a row of its own, as before")

    def test_a_capped_session_and_the_next_are_two_rows(self):
        self.save("a\n")
        self.save("b\n")
        self.age(0, 31)
        self.age(1, 1)
        self.save("c\n")
        rows = self.listed()[1]["changes"]
        self.assertEqual([r.get("saves") for r in rows], [1, 2])

    def test_the_row_restore_puts_back_the_file_as_before_the_session(self):
        for i in range(4):
            self.save(f"a {i}\n")
        row = self.listed()[1]["changes"][0]
        r = self.v.run("undo", str(row["id"]), script="filechange.py", ok=False)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual((self.v.root / NOTE).read_text(), "---\ntitle: Plan\n---\nbefore\n")
        rows = self.listed()[1]["changes"]
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["undone"])


class OldDrafts(Base):
    def setUp(self):
        super().setUp()
        self.d = self.v.root / DRAFTS
        self.d.mkdir(parents=True, exist_ok=True)
        self.old = {f"{HEX}.json": json.dumps({"path": NOTE, "body": "old typing", "changes": {}}),
                    f"{HEX[::-1]}.json": json.dumps({"path": OTHER, "body": "since deleted"}),
                    f"{HEX}.json.tmp": "{"}
        self.kept = {"capture-1a2b3c.json": json.dumps({"body": "the drawer"}), "other.json": "{}", "ABCDEF0123456789.json": "{}",
                     f"{'c' * 16}.json": json.dumps({"path": NOTE, "body": "secret typing", "changes": {"confidential": True}}),
                     f"{'d' * 16}.json": json.dumps({"path": f"{ABC}/notes/Gone.md", "body": "since deleted"}),
                     f"{HEX}0.json": "{}"}
        for name, text in {**self.old, **self.kept}.items():
            (self.d / name).write_text(text, encoding="utf-8")
        (self.d / "sub").mkdir()
        (self.d / "sub" / f"{'f' * 16}.json").write_text("{}", encoding="utf-8")
        os.symlink(self.v.root / NOTE, self.d / f"{'e' * 16}.json")

    def retire(self):
        return self.py("import live_server\nprint(json.dumps(live_server.retire_note_drafts()))")

    def test_only_the_old_note_drafts_are_moved_into_one_backup(self):
        self.save("an earlier change\n", session=None)
        self.assertEqual(self.retire(), 3)
        left = sorted(f.name for f in self.d.iterdir())
        self.assertEqual(left, sorted([*self.kept, "sub", f"{'e' * 16}.json"]))
        self.assertTrue((self.d / f"{'e' * 16}.json").is_symlink())
        self.assertEqual((self.v.root / NOTE).read_text(), "an earlier change\n", "a symlink's target is never touched")
        line = self.log()[-1]
        self.assertEqual((line["op"], line["path"], line["via"]), ("cleanup", DRAFTS, "server"))
        self.assertEqual(sorted(line["files"]), sorted(self.old))
        keep = self.v.root / line["backup"]
        self.assertTrue(re.fullmatch(r"system/backups/files/changes/\d{4}", line["backup"]))
        self.assertEqual({f.name: f.read_text() for f in keep.iterdir()}, self.old, "each draft is kept first, as it was")
        self.assertNotIn("old typing", (self.v.root / "system/config/files-log.jsonl").read_text(), "never the text")

    def test_nothing_to_do_writes_nothing(self):
        self.assertEqual(self.retire(), 3)
        before = (self.v.root / "system/config/files-log.jsonl").read_text()
        self.assertEqual(self.retire(), 0)
        self.assertEqual((self.v.root / "system/config/files-log.jsonl").read_text(), before)

    def test_the_cleanup_is_not_a_change_activity_lists_or_undo_touches(self):
        self.save("a\n", session=None)
        self.retire()
        self.assertEqual([r["op"] for r in self.listed()[1]["changes"]], ["edit"])
        r = self.v.run("undo", script="filechange.py", ok=False)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual((self.v.root / NOTE).read_text(), "---\ntitle: Plan\n---\nbefore\n", "Undo is the note's, as before")
        self.assertFalse((self.d / f"{HEX}.json").exists(), "the drafts are not put back")

    def test_a_confidential_notes_draft_stays_held_and_never_reaches_the_backups(self):
        places = lambda: self.py("print(json.dumps([str(p) for p in reach.confidential_places()]))")  # noqa: E731
        before = places()
        self.assertTrue(any(p.endswith(f"{'c' * 16}.json") for p in before), before)
        self.retire()
        after = places()
        for name in (f"{'c' * 16}.json", f"{'d' * 16}.json"):     # marked confidential; a note that is gone (fail closed)
            self.assertTrue((self.d / name).is_file(), name)
            self.assertEqual((self.d / name).read_text(encoding="utf-8"), self.kept[name], "left in place, never deleted")
            self.assertTrue(any(p.endswith(name) for p in after), after)
        backups = self.v.root / "system/backups/files/changes"
        self.assertNotIn("secret typing", "".join(f.read_text() for f in backups.rglob("*.json")))

    def test_the_live_server_clears_them_at_start_up(self):
        src = (self.v.root / "system/scripts/live_server.py").read_text(encoding="utf-8")
        main = src[src.index("\ndef main():"):src.index("\n    if LAUNCHED:", src.index("\ndef main():"))]
        self.assertIn("retire_note_drafts()", main)

    def test_a_failed_clean_up_is_logged_and_never_stops_the_server(self):
        out = self.py("import live_server\n"
                      "def boom(*a, **k):\n    raise OSError('disk')\n"
                      "filechange.retire_note_drafts = boom\n"
                      "print(json.dumps(live_server.retire_note_drafts()))")
        self.assertEqual(out, 0)
        self.assertTrue((self.d / f"{HEX}.json").is_file(), "the drafts stay until the next start")
        logs = "".join(f.read_text(encoding="utf-8") for f in (self.v.root / "system/logs").glob("debug-*.log"))
        self.assertIn("old note drafts not cleared (OSError)", logs)


if __name__ == "__main__":
    unittest.main()
