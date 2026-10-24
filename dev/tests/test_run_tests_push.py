"""Dev speed: `run_tests.py --push` is the run for an ordinary push: the quick tier plus what --changed reaches, never less than the
quick tier. Reads the file lists only (--list); nothing runs.

Run: python3 dev/tests/test_run_tests_push.py   (quick tier)
"""
import subprocess
import sys
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools" / "run_tests.py"


def listed(*args):
    r = subprocess.run([sys.executable, str(TOOL), *args, "--list"], capture_output=True, text=True)
    return r.returncode, [ln.split()[0] for ln in r.stdout.splitlines() if ln.startswith("test_")], r.stdout


class Push(unittest.TestCase):
    def test_push_always_includes_the_whole_quick_tier(self):
        code, push, _ = listed("--push", "HEAD")
        _, quick, _ = listed("--quick")
        self.assertEqual(code, 0)
        self.assertTrue(set(quick) <= set(push))

    def test_push_says_what_it_added_and_that_the_gate_runs_the_rest(self):
        _, _, out = listed("--push", "HEAD")
        self.assertIn("--push:", out)
        self.assertIn("release gate", out)

    def test_push_is_never_the_default(self):
        _, plain, _ = listed()
        _, quick, _ = listed("--quick")
        self.assertGreater(len(plain), len(quick))        # plain run_tests.py is still the full suite


if __name__ == "__main__":
    unittest.main()
