"""BL-172 (sprint-polish-2): tests remove the throwaway vaults they make, and the runner names a file that doesn't.

Run: python3 dev/tests/test_vault_cleanup.py
Each case runs a small test file of its own in a subprocess with its own CREAITE_TEST_TAG, then looks only for vaults
with that tag, so it never sees (or touches) a vault another run is using.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
import uuid
from contextlib import redirect_stdout
from pathlib import Path

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS.parent / "tools"))
import run_tests  # noqa: E402

TMP = Path(tempfile.gettempdir())


def run_file(body, tag):
    """Run a test file made of `body` from a folder of its own, with this tag; returns the vaults left with the tag."""
    d = Path(tempfile.mkdtemp(prefix="creaite-hyg-"))
    try:
        f = d / "test_probe.py"
        f.write_text(f"import sys\nsys.path.insert(0, {str(TESTS)!r})\n" + textwrap.dedent(body))
        subprocess.run([sys.executable, str(f)], cwd=d, capture_output=True, text=True, timeout=120,
                       env={**os.environ, "CREAITE_TEST_TAG": tag})
    finally:
        shutil.rmtree(d, ignore_errors=True)
    return sorted(TMP.glob(f"creaite-test-{tag}-*"))


class VaultsAreRemoved(unittest.TestCase):
    def tag(self):
        t = "hyg" + uuid.uuid4().hex[:10]
        self.addCleanup(lambda: [shutil.rmtree(p, ignore_errors=True) for p in TMP.glob(f"creaite-test-{t}-*")])
        return t

    def test_the_vault_carries_the_files_tag(self):
        t = self.tag()
        left = run_file("""
            import os, sys
            from test_tracker import make_vault
            v = make_vault(); print(v); os._exit(0)      # skips every cleanup: the vault stays, named with the tag
        """, t)
        self.assertEqual(len(left), 1)

    def test_a_setup_that_fails_still_removes_its_vault(self):
        t = self.tag()
        left = run_file("""
            import unittest
            from test_tracker import Vault
            class T(unittest.TestCase):
                def setUp(self):
                    self.v = Vault()
                    raise RuntimeError("set-up failed before tearDown was due")
                def tearDown(self):
                    self.v.cleanup()
                def test_x(self):
                    pass
            unittest.main()
        """, t)
        self.assertEqual(left, [])

    def test_a_live_browser_case_whose_start_fails_removes_its_vault(self):
        t = self.tag()
        left = run_file("""
            import unittest
            from live_browser import LiveBrowserCase
            class T(LiveBrowserCase):
                @classmethod
                def load(cls, v):
                    raise RuntimeError("loading the data failed")
                def test_x(self):
                    pass
            class Shared(T):
                shared_server = True
            unittest.main()
        """, t)
        self.assertEqual(left, [])

    def test_a_clean_test_leaves_nothing(self):
        t = self.tag()
        left = run_file("""
            import unittest
            from test_tracker import Vault
            class T(unittest.TestCase):
                def test_x(self):
                    v = Vault(); v.run("init"); v.cleanup()
            unittest.main()
        """, t)
        self.assertEqual(left, [])


class RunnerNamesALeak(unittest.TestCase):
    def test_the_runner_warns_removes_its_own_and_nothing_else(self):
        d = Path(tempfile.mkdtemp(prefix="creaite-hyg-"))
        self.addCleanup(shutil.rmtree, d, True)
        name = "hyg" + uuid.uuid4().hex[:10]
        leaky, clean = f"test_{name}leaky.py", f"test_{name}clean.py"
        (d / leaky).write_text("import os, tempfile\ntempfile.mkdtemp(prefix='creaite-test-' + os.environ['CREAITE_TEST_TAG'] + '-')\n")
        (d / clean).write_text("pass\n")
        other = Path(tempfile.mkdtemp(prefix=f"creaite-test-{name}other-"))    # stands for a vault another run is using
        self.addCleanup(lambda: [shutil.rmtree(p, ignore_errors=True) for p in TMP.glob(f"creaite-test-{name}*")])
        saved = run_tests.TESTS, run_tests.TIMES
        run_tests.TESTS, run_tests.TIMES = d, d / ".durations"
        try:
            out = io.StringIO()
            with redirect_stdout(out):
                code = run_tests.main([name])
        finally:
            run_tests.TESTS, run_tests.TIMES = saved
        text = out.getvalue()
        self.assertEqual(code, 0, text)                                            # a warning, not a failure
        self.assertIn(f"WARN  {leaky} left 1 vault behind", text)
        self.assertNotIn(f"WARN  {clean}", text)
        self.assertIn(f"Vaults left behind (now removed): 1 by {leaky}.", text)   # BL-246: named, then removed with the file's folder
        self.assertTrue(other.exists())                                            # never deletes what it didn't make
        self.assertEqual(len(list(TMP.glob(f"creaite-test-{name}leaky-*"))), 0)    # made in the file's own TMPDIR, gone with it


if __name__ == "__main__":
    unittest.main()
