"""#89: run_tests.py --shard I/N splits the test files so that every file runs in exactly one shard, and the failed files
of the last run start first.

Run: python3 dev/tests/test_run_tests_shard.py   (quick tier)
"""
import argparse
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tools"))
import run_support as support  # noqa: E402
import run_tests  # noqa: E402


def everything():
    return sorted(run_tests.TESTS.glob("test_*.py"))


class ShardCoversEveryFileOnce(unittest.TestCase):
    def check(self, files, n):
        seen = []
        for i in range(1, n + 1):
            seen += [f.name for f in run_tests.shard(files, i, n)]
        self.assertEqual(sorted(seen), sorted(f.name for f in files), f"{n} shards: each file exactly once")
        self.assertEqual(len(seen), len(set(seen)))

    def test_all_files_for_several_counts(self):
        files = everything()
        self.assertGreater(len(files), 100)
        for n in (1, 2, 3, 4, 7):
            self.check(files, n)

    def test_the_quick_tier_too(self):
        quick = [f for f in everything() if not support.is_chrome(f)]
        self.assertTrue(quick)
        self.check(quick, 3)

    def test_more_shards_than_files(self):
        files = everything()[:2]
        self.check(files, 5)

    def test_the_split_is_stable_and_ignores_the_order_given(self):
        files = everything()
        again = run_tests.shard(list(reversed(files)), 2, 3)
        self.assertEqual([f.name for f in run_tests.shard(files, 2, 3)], [f.name for f in again])

    def test_balanced_by_the_times(self):
        files = [Path(f"test_{c}.py") for c in "abcdef"]
        w = {"test_a.py": 100, "test_b.py": 60, "test_c.py": 50, "test_d.py": 50, "test_e.py": 20, "test_f.py": 10}
        totals = [sum(w[f.name] for f in run_tests.shard(files, i, 2, w)) for i in (1, 2)]
        self.assertEqual(sum(totals), 290)
        self.assertLessEqual(abs(totals[0] - totals[1]), 10)

    def test_without_times_it_is_still_a_split_by_name(self):
        files = [Path(f"test_{c}.py") for c in "abcd"]
        self.assertEqual([f.name for f in run_tests.shard(files, 1, 2, {})], ["test_a.py", "test_c.py"])
        self.assertEqual([f.name for f in run_tests.shard(files, 2, 2, {})], ["test_b.py", "test_d.py"])

    def test_the_committed_times_name_real_files(self):
        names = {f.name for f in everything()}
        listed = set(run_tests.shard_weights())
        self.assertFalse(listed - names, "shard_times.txt names a test file that doesn't exist")


class ShardArgument(unittest.TestCase):
    def test_good_and_bad(self):
        self.assertEqual(run_tests.shard_arg("2/3"), (2, 3))
        for bad in ("0/3", "4/3", "3", "a/b", "1/0", ""):
            with self.assertRaises(argparse.ArgumentTypeError, msg=bad):
                run_tests.shard_arg(bad)


class FailedFirst(unittest.TestCase):
    def test_failed_files_start_first_and_a_partial_run_keeps_the_rest(self):
        with tempfile.TemporaryDirectory() as d:
            old, run_tests.LAST_FAILED = run_tests.LAST_FAILED, Path(d) / ".last-failed"
            old_times, run_tests.TIMES = run_tests.TIMES, Path(d) / ".durations"
            try:
                files = [Path(f"test_{c}.py") for c in "abc"]
                run_tests.remember_failed(["test_a.py", "test_b.py", "test_c.py"], ["test_c.py"])
                run_tests.slowest_first(files)
                self.assertEqual(files[0].name, "test_c.py")
                run_tests.remember_failed(["test_a.py"], ["test_a.py"])        # a partial run
                self.assertEqual(run_tests.last_failed(), {"test_a.py", "test_c.py"})
                run_tests.remember_failed(["test_c.py"], [])                   # c passes now
                self.assertEqual(run_tests.last_failed(), {"test_a.py"})
            finally:
                run_tests.LAST_FAILED, run_tests.TIMES = old, old_times


if __name__ == "__main__":
    unittest.main()
