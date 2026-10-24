"""#339 part A: lighter runs. The two guarded patches (dev/proposals/339/*.diff) apply to live_server.py, and with them a typed
"refresh calendar" starts the small "calendar" kind and a sweep's --add-dir leaves out the home folder.

Run: python3 dev/tests/test_lighter_runs_339.py      (quick tier)
Structure checks read live_server.py as text. Tests that need the patches run on a throwaway copy with them applied (nothing in this
tree is touched) and are GUARDED skips once the tree has them (they then run on the tree itself).
"""
import importlib.util
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LIVE = REPO / "system/scripts/live_server.py"
DIFFS = sorted((REPO / "dev/proposals/339").glob("*.diff"))
LANDED = "def panel_calendar" in LIVE.read_text(encoding="utf-8")


def patched_copy(test):
    """A throwaway live_server.py with the 339 diffs applied (or a plain copy once they have landed)."""
    d = Path(tempfile.mkdtemp(prefix="p339-"))
    test.addCleanup(shutil.rmtree, d, True)
    (d / "system/scripts").mkdir(parents=True)
    shutil.copy2(LIVE, d / "system/scripts/live_server.py")
    subprocess.run(["git", "init", "-q"], cwd=d, capture_output=True)
    if not LANDED:
        for f in DIFFS:
            r = subprocess.run(["git", "apply", str(f)], cwd=d, capture_output=True, text=True)
            test.assertEqual(r.returncode, 0, f"{f.name}: {r.stderr}")
    return d / "system/scripts/live_server.py"


class Structure(unittest.TestCase):
    """Pieces that need no guarded change."""

    def setUp(self):
        self.src = LIVE.read_text(encoding="utf-8")

    def test_sweep_and_calendar_kinds_exist(self):
        self.assertIn('KIND_ARGS["calendar"]', self.src)
        self.assertIn('KIND_ARGS["sweep"]', self.src)
        self.assertIn("def panel_sweep(", self.src)

    def test_calendar_kind_reads_no_project_file(self):
        self.assertRegex(self.src, r'policy == "calendar"[^\n]*\n\s+return \[\]')

    def test_calendar_words_are_in_the_sweep_recogniser(self):
        self.assertIn("refresh (?:the |my )?calendar", self.src)

    def test_patches_are_guarded_only_and_short(self):
        self.assertTrue(DIFFS)
        for f in DIFFS:
            text = f.read_text(encoding="utf-8")
            self.assertEqual(set(re.findall(r"^diff --git a/(\S+)", text, re.M)), {"system/scripts/live_server.py"})
            self.assertFalse([ln for ln in text.splitlines() if ln.startswith("+") and len(ln) > 141])


@unittest.skipIf(LANDED, "GUARDED: the patches have landed; Patched runs on the tree")
class PatchesApply(unittest.TestCase):
    def test_each_applies_alone_and_together(self):
        for f in DIFFS:
            d = Path(tempfile.mkdtemp(prefix="p339-"))
            self.addCleanup(shutil.rmtree, d, True)
            (d / "system/scripts").mkdir(parents=True)
            shutil.copy2(LIVE, d / "system/scripts/live_server.py")
            subprocess.run(["git", "init", "-q"], cwd=d, capture_output=True)
            r = subprocess.run(["git", "apply", "--check", str(f)], cwd=d, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f"{f.name}: {r.stderr}")
        patched_copy(self)


class Patched(unittest.TestCase):
    """GUARDED: need the patches (applied to a throwaway copy while they are not in the tree)."""

    @classmethod
    def setUpClass(cls):
        d = Path(tempfile.mkdtemp(prefix="p339m-"))
        cls._d = d
        (d / "system/scripts").mkdir(parents=True)
        shutil.copy2(LIVE, d / "system/scripts/live_server.py")
        subprocess.run(["git", "init", "-q"], cwd=d, capture_output=True)
        if not LANDED:
            for f in DIFFS:
                subprocess.run(["git", "apply", str(f)], cwd=d, capture_output=True, check=True)
        cls.path = d / "system/scripts/live_server.py"
        cls.src = cls.path.read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._d, True)

    def fn(self):
        """panel_calendar, run from its own source text (the module itself needs the whole server)."""
        m = re.search(r"^PANEL_CALENDAR_WORDS = .*?\n\n\ndef panel_calendar.*?\n\n\n", self.src, re.S | re.M)
        self.assertTrue(m)
        ns = {"re": re}
        exec(m.group(0), ns)
        return ns["panel_calendar"]

    def test_calendar_words(self):
        f = self.fn()
        for ok in ("refresh calendar", "Refresh the calendar", "please refresh my calendar now.", "refresh my calendar please!"):
            self.assertTrue(f(ok), ok)
        for no in ("refresh calendar and apply", "sweep", "refresh calendar for ABC", "refreshing calendar", "x" * 80):
            self.assertFalse(f(no), no)
        self.assertFalse(f("refresh calendar", images=["a.png"]))
        self.assertFalse(f("refresh calendar", confirmed="Add action"))

    def test_ask_routes_calendar_to_its_kind(self):
        self.assertRegex(self.src, r'kind="calendar",\s*\n\s+label=calendar_refresh\.label\(\)')
        self.assertIn("calendar_refresh.precheck()", self.src)
        self.assertIn("sweep_running()", self.src)

    def test_sweep_run_dirs_leave_out_the_home_folder(self):
        self.assertIn('policy not in ("process", "reextract", "sweep")', self.src)


if __name__ == "__main__":
    unittest.main()
