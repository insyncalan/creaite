"""#119: one backup per editing session. filechange.perform's `session` over a throwaway vault.

Run: python3 dev/tests/test_notes_autosave_backups.py

  - N saves with one session make one backup folder and N log lines, each with the session's backup and the text from before it;
  - a new session, another file, more than 5 minutes idle, or a change in between (outside creaite, or through filechange) each
    make a new backup; so does a save without a session (as before), and a token naming another file;
  - Undo of the session's latest save puts back the text from before the session in one step and undoes its earlier saves with
    it; Undo of a save that isn't the latest still refuses, as before;
  - never joined: a change Alan approved on the card, a settings file, and a save while an ask creaite run is in progress
    (marked by outside content, where the note's change needs approval, or not marked): each has its own backup and no session;
  - the log keeps a hash of the token, never the token;
  - #175 (M2): a session ends 30 minutes after its first save (SESSION_MAX_AGE), and a session whose first save isn't in the log is
    never joined; Undo then goes back one session at a time; (L3) a session's backup changed since is never reused, and _backup
    never joins a settings file even when called as joinable.
"""
import json
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


class SessionBackups(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        for rel in (NOTE, OTHER):
            p = self.v.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("---\ntitle: Plan\n---\nbefore\n", encoding="utf-8")

    def tearDown(self):
        self.v.cleanup()

    # ── helpers ──
    def py(self, code):
        """Run Python with the vault's scripts first on the path; returns what it prints last, as JSON."""
        src = f"import sys, json; sys.path.insert(0, {str(self.v.root / 'system/scripts')!r})\nimport filechange, reach\n{code}"
        r = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True, cwd=tempfile.gettempdir())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def save(self, text, session="s-0001-abcd", path=NOTE, via="dashboard"):
        ch = {"op": "edit", "path": path, "data": text.encode(), "why": WHY}
        if session is not None:
            ch["session"] = f"{path}:{session}" if not session.startswith("raw:") else session[4:]
        code, msg = self.py(f"print(json.dumps(filechange.perform({ch!r}, via={via!r})))")
        self.assertEqual(code, 0, msg)
        return msg

    def approved(self, ch):
        """A sensitive change made the way the live server makes it after Alan's Approve: a one-time approval in this process."""
        return self.py(f"ch = {ch!r}\ntok = reach.APPROVALS.issue(filechange.fingerprint(ch))\n"
                       "print(json.dumps(filechange.perform(ch, tok, 'dashboard')))")

    def log(self):
        p = self.v.root / "system/config/files-log.jsonl"
        return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []

    def edits(self, path=NOTE):
        return [e for e in self.log() if e.get("op") == "edit" and e.get("path") == path]

    def folders(self):
        d = self.v.root / "system/backups/files/changes"
        return sorted(x.name for x in d.iterdir()) if d.is_dir() else []

    def text(self, path=NOTE):
        return (self.v.root / path).read_text(encoding="utf-8")

    def undo(self, *n):
        return self.v.run("undo", *map(str, n), script="filechange.py", ok=False)

    def age_last(self, minutes):
        """Make the log's last line `minutes` older, as if the page had been idle."""
        p = self.v.root / "system/config/files-log.jsonl"
        rows = self.log()
        rows[-1]["at"] = (datetime.now() - timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")
        p.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")

    def age(self, index, minutes):
        """Make the log's line `index` `minutes` old."""
        p = self.v.root / "system/config/files-log.jsonl"
        rows = self.log()
        rows[index]["at"] = (datetime.now() - timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")
        p.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")

    # ── one session, one backup ──
    def test_n_saves_in_one_session_make_one_backup_and_n_log_lines(self):
        original = self.text()
        for i in range(5):
            self.save(f"---\ntitle: Plan\n---\ntyped {i}\n")
        es = self.edits()
        self.assertEqual(len(es), 5)
        self.assertEqual(len(self.folders()), 1, self.folders())
        self.assertEqual({e["backup"] for e in es}, {es[0]["backup"]})
        self.assertEqual({e["before"] for e in es}, {es[0]["before"]})
        self.assertEqual(len({e["after"] for e in es}), 5)
        self.assertEqual((self.v.root / es[0]["backup"]).read_text(encoding="utf-8"), original)
        self.assertEqual(self.text(), "---\ntitle: Plan\n---\ntyped 4\n")
        self.assertTrue(all(len(e["session"]) == 16 for e in es))
        self.assertNotIn("s-0001-abcd", (self.v.root / "system/config/files-log.jsonl").read_text(), "the token is never logged")

    def test_a_save_without_a_session_is_backed_up_on_its_own(self):
        for i in range(3):
            self.save(f"plain {i}\n", session=None)
        self.assertEqual(len(self.folders()), 3)
        self.assertTrue(all("session" not in e for e in self.edits()))

    def test_a_new_session_another_file_or_a_bad_token_makes_a_new_backup(self):
        self.save("a\n")
        self.save("b\n", session="s-0002-abcd")
        self.assertEqual(len(self.folders()), 2)
        self.save("c\n", session="s-0002-abcd", path=OTHER)        # the same id on another file is another session
        self.assertEqual(len(self.folders()), 3)
        self.save("d\n", session=f"raw:{OTHER}:s-0002-abcd")      # a token naming another file: no session at all
        self.save("e\n", session=f"raw:{OTHER}:s-0002-abcd")
        self.assertEqual(len(self.folders()), 5)
        self.assertNotIn("session", self.edits()[-1])
        self.save("f\n", session="s-0002-abcd", via="cli")         # another route
        self.assertEqual(len(self.folders()), 6)

    def test_five_minutes_idle_makes_a_new_backup(self):
        self.save("a\n")
        self.age_last(4)
        self.save("b\n")
        self.assertEqual(len(self.folders()), 1)
        self.age_last(6)
        self.save("c\n")
        self.assertEqual(len(self.folders()), 2)

    def test_a_change_in_between_makes_a_new_backup(self):
        self.save("a\n")
        (self.v.root / NOTE).write_text("typed in Finder\n", encoding="utf-8")
        self.save("b\n")
        self.assertEqual(len(self.folders()), 2)
        es = self.edits()
        self.assertEqual((self.v.root / es[-1]["backup"]).read_text(), "typed in Finder\n")
        self.save("c\n", session="s-9999-abcd")                    # another session's save in between
        self.save("d\n")
        self.assertEqual(len(self.folders()), 4)
        self.assertEqual(self.undo().returncode, 0)                # an undo in between
        self.save("e\n")
        self.assertEqual(len(self.folders()), 5)

    # ── Undo ──
    def test_undo_after_a_session_restores_the_text_from_before_it_in_one_step(self):
        self.save("first\n", session="s-0000-zzzz")               # an earlier session, its own backup
        before_session = self.text()
        for i in range(4):
            self.save(f"typed {i}\n")
        r = self.undo()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.text(), before_session)
        self.assertIn("earlier saves of its editing session", r.stdout)
        undone = {e["undoes"] for e in self.log() if e.get("op") == "undo"}
        self.assertEqual(undone, {e["id"] for e in self.edits()[1:]})
        r = self.undo()                                            # the next undo is the earlier session's, as before
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.text(), "---\ntitle: Plan\n---\nbefore\n")

    def test_undo_of_a_save_that_is_not_the_latest_still_refuses(self):
        for i in range(3):
            self.save(f"typed {i}\n")
        middle = self.edits()[1]["id"]
        r = self.undo(middle)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("has been changed since", r.stdout)
        self.assertEqual(self.text(), "typed 2\n")

    # ── never joined ──
    def test_a_change_approved_on_the_card_is_never_joined(self):
        self.save("a\n")
        rel = f"{ABC}/transcripts/2026-10-01 Steering.md"            # someone else's file: needs Alan's approval
        p = self.v.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("transcript\n", encoding="utf-8")
        for i in range(2):
            ch = {"op": "edit", "path": rel, "data": f"fixed {i}\n".encode(), "why": "fix a name", "session": f"{rel}:s-0001-abcd"}
            refused = self.py(f"print(json.dumps(filechange.perform({ch!r}, None, 'dashboard')))")
            self.assertEqual(refused[0], 3, refused)                # without the approval: needs approval, nothing joined
            code, msg = self.approved(ch)
            self.assertEqual(code, 0, msg)
        es = self.edits(rel)
        self.assertEqual(len(es), 2)
        self.assertTrue(all(e.get("approved") and "session" not in e for e in es))
        self.assertEqual(len({e["backup"] for e in es}), 2, "each approved change has its own backup")
        self.assertEqual(len(self.folders()), 3)

    def test_a_settings_file_is_never_joined(self):
        rel = "system/config/settings.json"
        cfg = json.loads((self.v.root / rel).read_text())
        for i in range(2):
            cfg["stale_days"] = 10 + i
            ch = {"op": "edit", "path": rel, "data": json.dumps(cfg, indent=2).encode(), "why": "a setting",
                  "session": f"{rel}:s-0001-abcd"}
            code, msg = self.approved(ch)
            self.assertEqual(code, 0, msg)
        es = self.edits(rel)
        self.assertEqual(len(es), 2)
        self.assertTrue(all("session" not in e for e in es))
        self.assertEqual(len({e["backup"] for e in es}), 2)

    def write_run(self, marked):
        guard = self.v.root / "system/guard"
        guard.mkdir(parents=True, exist_ok=True)
        (guard / "run.json").write_text(json.dumps({"run": "r-test", "mode": "chat", "marked": ["used outlook_email_search"]
                                                    if marked else []}), encoding="utf-8")

    def test_a_save_in_a_run_marked_by_outside_content_is_never_joined(self):
        self.save("a\n")
        self.write_run(marked=True)
        ch = {"op": "edit", "path": NOTE, "data": b"b\n", "why": WHY, "session": f"{NOTE}:s-0001-abcd"}
        code, _msg = self.py(f"print(json.dumps(filechange.perform({ch!r}, None, 'dashboard')))")
        self.assertEqual(code, 3, "after outside content a note's change waits on the card")
        code, msg = self.approved(ch)
        self.assertEqual(code, 0, msg)
        self.assertEqual(len(self.folders()), 2)
        self.assertNotIn("session", self.edits()[-1])

    def test_a_save_while_a_run_is_in_progress_is_never_joined(self):
        self.save("a\n")
        self.write_run(marked=False)
        self.save("b\n")
        self.save("c\n")
        self.assertEqual(len(self.folders()), 3)
        self.assertTrue(all("session" not in e for e in self.edits()[1:]))


class SessionCap(SessionBackups):
    """#175: one Undo puts back at most about 30 minutes of typing (M2 of Team Cap's #119 review); L3's two gaps."""
    def test_a_session_ends_thirty_minutes_after_its_first_save(self):
        self.save("a\n")
        self.save("b\n")
        self.age(0, 29)                                             # first save 29 minutes ago, the last one just now
        self.age(1, 1)
        self.save("c\n")
        self.assertEqual(len(self.folders()), 1, "under 30 minutes: still one session")
        self.age(0, 31)                                             # first save over 30 minutes ago, saves never 5 minutes apart
        self.age(1, 2)
        self.age(2, 1)
        self.save("d\n")
        self.assertEqual(len(self.folders()), 2, "over 30 minutes from the first save: a new session")
        es = self.edits()
        self.assertEqual((self.v.root / es[-1]["backup"]).read_text(encoding="utf-8"), "c\n", "the new session's backup")
        self.save("e\n")
        self.assertEqual(len(self.folders()), 2, "the new session goes on as one")
        self.assertEqual(self.edits()[-1]["backup"], es[-1]["backup"])

    def test_undo_goes_back_one_capped_session_at_a_time(self):
        original = self.text()
        self.save("a\n")
        self.save("b\n")
        self.age(0, 31)
        self.age(1, 1)
        self.save("c\n")
        self.save("d\n")
        self.assertEqual(len(self.folders()), 2)
        r = self.undo()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.text(), "b\n", "one Undo puts back only the newer session")
        r = self.undo()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.text(), original, "the next Undo puts back the older session")
        self.assertIn("Nothing to undo", self.undo().stdout)

    def test_a_session_whose_first_save_is_not_in_the_log_is_never_joined(self):
        self.save("a\n")
        self.save("b\n")
        p = self.v.root / "system/config/files-log.jsonl"
        p.write_text("".join(json.dumps(r) + "\n" for r in self.log()[1:]), encoding="utf-8")
        self.save("c\n")
        self.assertEqual(len(self.folders()), 2)

    def test_a_session_backup_changed_since_is_never_reused(self):
        self.save("a\n")
        (self.v.root / self.edits()[0]["backup"]).write_text("tampered\n", encoding="utf-8")
        self.save("b\n")
        self.assertEqual(len(self.folders()), 2)
        self.assertNotEqual(self.edits()[-1]["backup"], self.edits()[0]["backup"])

    def test_backup_never_joins_a_settings_file_even_when_called_as_joinable(self):
        rel = "system/config/settings.json"
        out = self.py(f"t = filechange.resolve({rel!r})\nb1 = {{'via': 'dashboard'}}\nb2 = {{'via': 'dashboard'}}\n"
                      f"ch = {{'op': 'edit', 'path': {rel!r}, 'session': {rel + ':s-0001-abcd'!r}}}\n"
                      "k1 = filechange._backup(ch, t, b1, 901, joinable=True)\nk2 = filechange._backup(ch, t, b2, 902, joinable=True)\n"
                      "print(json.dumps([str(k1) != str(k2), 'session' in b1, 'session' in b2]))")
        self.assertEqual(out, [True, False, False])


def load_tests(loader, tests, pattern):
    """Each class's own tests once: SessionCap inherits SessionBackups' helpers, not its tests."""
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(SessionBackups))
    suite.addTests(SessionCap(n) for n in loader.getTestCaseNames(SessionCap) if n in SessionCap.__dict__)
    return suite


if __name__ == "__main__":
    unittest.main()
