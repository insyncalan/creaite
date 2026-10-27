"""#363: dev/tools/branch_report.py on a fixture repo (Stark's review). A throwaway origin with one branch per case, cloned, so the
branches are origin/*: a patch cherry-picked into main, a squash merge, branches held by a live, an old and a recent branch, same-tip
twins and unique old work; and worktrees that are dirty, detached, locked and prunable. Read-only on the fixture; nothing real is
touched.

Run: python3 dev/tests/test_branch_report_363.py      (quick tier: git only)
"""
import contextlib
import datetime
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "dev" / "tools"))
import branch_report as B  # noqa: E402

TODAY = datetime.date(2026, 10, 27)
OLD, NEW = "2026-10-01T10:00:00", "2026-10-26T10:00:00"


def run(cwd, *args, when=OLD):
    env = {**os.environ, "GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when, "GIT_AUTHOR_NAME": "Test Person",
           "GIT_AUTHOR_EMAIL": "test@example.test", "GIT_COMMITTER_NAME": "Test Person", "GIT_COMMITTER_EMAIL": "test@example.test"}
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, env=env)
    assert r.returncode == 0, (args, r.stdout, r.stderr)
    return r.stdout.strip()


def commit(cwd, name, text, when=OLD):
    (Path(cwd) / name).write_text(text, encoding="utf-8")
    run(cwd, "add", "--", name, when=when)
    run(cwd, "commit", "-q", "-m", f"{name}: {text.strip()}", when=when)


class Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        o = cls.tmp / "origin"
        o.mkdir()
        run(o, "init", "-q", "-b", "main")
        commit(o, "base.txt", "base\n")
        # a patch cherry-picked into main: every commit's patch is there
        run(o, "checkout", "-q", "-b", "picked")
        commit(o, "p.txt", "picked\n")
        pick = run(o, "rev-parse", "HEAD")
        run(o, "checkout", "-q", "main")
        commit(o, "m1.txt", "main moves on\n")
        run(o, "cherry-pick", pick)
        # a squash merge: the commits differ, main holds the whole diff
        run(o, "checkout", "-q", "-b", "squashed", "main~2")
        commit(o, "s.txt", "one\n")
        commit(o, "s.txt", "one\ntwo\n")
        run(o, "checkout", "-q", "main")
        run(o, "merge", "-q", "--squash", "squashed")
        run(o, "commit", "-q", "-m", "squash")
        # held by a live line (kept): delete
        run(o, "checkout", "-q", "-b", "inner-live", "main")
        commit(o, "i.txt", "inner\n")
        run(o, "checkout", "-q", "-b", "v2610-holder")
        commit(o, "h.txt", "holder\n")
        # held by an old branch (owner decides): delete if kept
        run(o, "checkout", "-q", "-b", "inner-old", "main")
        commit(o, "j.txt", "inner old\n")
        run(o, "checkout", "-q", "-b", "holder-old")
        commit(o, "k.txt", "holder old\n")
        # held by a branch kept only for being recent (Stark's dev-test-speed case): delete if kept
        run(o, "checkout", "-q", "-b", "inner-recent", "main")
        commit(o, "r.txt", "inner recent\n")
        run(o, "checkout", "-q", "-b", "holder-recent")
        commit(o, "q.txt", "holder recent\n", when=NEW)
        # same-tip twins, and unique old work
        run(o, "checkout", "-q", "-b", "twin-a", "main")
        commit(o, "t.txt", "twin\n")
        run(o, "branch", "twin-b")
        run(o, "checkout", "-q", "-b", "unique-old", "main")
        commit(o, "u.txt", "unique\n")
        run(o, "checkout", "-q", "main")
        cls.clone = cls.tmp / "clone"
        run(cls.tmp, "clone", "-q", str(o), str(cls.clone))
        cwd = os.getcwd()
        try:
            os.chdir(cls.clone)
            cls.rows = {r["branch"]: r for r in B.classify(B.facts(pr={}), today=TODAY)}
        finally:
            os.chdir(cwd)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def suggest(self, b):
        return self.rows[b]["suggest"]

    def test_a_cherry_picked_patch_is_in_main(self):
        self.assertEqual(self.rows["picked"]["commits_not_in_main"], 0)
        self.assertEqual(self.suggest("picked"), "delete")

    def test_a_squash_merge_is_in_main_by_its_whole_diff(self):
        r = self.rows["squashed"]
        self.assertGreater(r["commits_not_in_main"], 0)                   # git cherry can't see a squash
        self.assertTrue(r["change_already_in_main"])
        self.assertEqual(self.suggest("squashed"), "delete")

    def test_held_by_a_kept_live_line_is_delete(self):
        self.assertIn("v2610-holder", self.rows["inner-live"]["held_by"])
        self.assertEqual(self.suggest("v2610-holder"), "keep")
        self.assertEqual(self.suggest("inner-live"), "delete")

    def test_held_by_an_owner_decides_branch_is_delete_if_kept(self):
        self.assertEqual(self.suggest("holder-old"), "owner decides")
        self.assertEqual(self.suggest("inner-old"), "delete if kept")

    def test_held_by_a_branch_kept_only_for_being_recent_is_delete_if_kept(self):
        self.assertEqual(self.suggest("holder-recent"), "keep")
        self.assertEqual(self.suggest("inner-recent"), "delete if kept")

    def test_same_tip_twins_name_each_other_and_neither_is_deleted_for_it(self):
        a, b = self.rows["twin-a"], self.rows["twin-b"]
        self.assertEqual((a["same_tip_as"], b["same_tip_as"]), (["twin-b"], ["twin-a"]))
        self.assertEqual((a["suggest"], b["suggest"]), ("owner decides", "owner decides"))
        self.assertIn("the same commit as twin-b", a["why"])

    def test_unique_old_work_is_the_owners_call(self):
        self.assertEqual(self.suggest("unique-old"), "owner decides")

    def test_only_remote_branches_are_reported_and_main_is_not(self):
        self.assertNotIn("main", self.rows)
        run(self.clone, "branch", "local-only")
        cwd = os.getcwd()
        try:
            os.chdir(self.clone)
            names = {r["branch"] for r in B.facts(pr={})}
        finally:
            os.chdir(cwd)
        self.assertNotIn("local-only", names)

    def test_the_table_shows_dates_as_dd_mm_yyyy_and_escapes_bars(self):
        rows = [dict(self.rows["unique-old"], why="a | b")]
        table = B.markdown(rows)
        self.assertIn("| 01-10-2026 |", table)
        self.assertIn("a \\| b", table)

    def test_worktrees_dirty_detached_locked_and_prunable_are_all_shown(self):
        c = self.clone
        dirty, detached, locked, gone = (self.tmp / n for n in ("wt-dirty", "wt-detached", "wt-locked", "wt-gone"))
        run(c, "worktree", "add", "-q", str(dirty), "-b", "wt-dirty-branch", "origin/unique-old")
        (dirty / "u.txt").write_text("changed\n", encoding="utf-8")
        run(c, "worktree", "add", "-q", "--detach", str(detached), "origin/twin-a")
        (detached / "new.txt").write_text("new\n", encoding="utf-8")
        run(c, "worktree", "add", "-q", str(locked), "-b", "wt-locked-branch")
        run(c, "worktree", "lock", "--reason", "kept on purpose", str(locked))
        run(c, "worktree", "add", "-q", str(gone), "-b", "wt-gone-branch")
        shutil.rmtree(gone)
        clean = self.tmp / "wt-clean"
        run(c, "worktree", "add", "-q", str(clean), "-b", "wt-clean-branch")
        buf, cwd = io.StringIO(), os.getcwd()
        try:
            os.chdir(c)
            with contextlib.redirect_stdout(buf):
                B.worktrees()
        finally:
            os.chdir(cwd)
        text = buf.getvalue()
        self.assertIn("wt-dirty-branch", text)
        self.assertIn("M 1", text)
        self.assertIn("(detached)", text)
        self.assertIn("?? 1", text)
        self.assertIn("locked (kept on purpose)", text)
        self.assertIn("prunable", text)                                   # never skipped silently
        self.assertNotIn(str(clean), text)                                # a clean worktree isn't listed


if __name__ == "__main__":
    unittest.main()
