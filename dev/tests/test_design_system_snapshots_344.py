"""#344: the design-system snapshot tool makes no Review page and regenerates gallery.html and blank.html from the same shell as the pages.

Run: python3 dev/tests/test_design_system_snapshots_344.py   (needs Google Chrome; one tool run, about 15 seconds)
"""
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "dev" / "tools" / "design_system_snapshots.py"


def shell_of(html):
    """The rail's markup, which comes from the one shell and so must be the same in every file."""
    m = re.search(r'<nav class="rail".*?</nav>', html, re.S)
    return re.sub(r"\s+", " ", m.group(0)) if m else ""


class SnapshotTool(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name)
        (cls.out / "pages").mkdir()
        (cls.out / "pages" / "review.html").write_text("stale")  # a leftover from an older run
        r = subprocess.run([sys.executable, str(TOOL), "--repo", str(ROOT), "--out", str(cls.out)], capture_output=True, text=True, timeout=300)
        assert r.returncode == 0, r.stdout[-800:] + r.stderr[-800:]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_no_review_page(self):
        self.assertFalse((self.out / "pages" / "review.html").exists())
        self.assertFalse((self.out / "shots" / "review-light.png").exists())
        self.assertNotIn("go('review')", TOOL.read_text())

    def test_blank_is_the_shell_with_an_empty_page(self):
        s = (self.out / "blank.html").read_text()
        self.assertIn("A blank page in the real app shell", s)
        self.assertIn('href="style.snapshot.css"', s)
        self.assertIn("Page title", s)
        self.assertEqual(shell_of(s), shell_of((self.out / "pages" / "files.html").read_text()))

    def test_gallery_is_the_same_shell_with_the_curated_sections(self):
        s = (self.out / "gallery.html").read_text()
        self.assertIn("<h1>Design system gallery</h1>", s)
        self.assertIn('class="dsg"', s)
        self.assertIn("function tok()", s)
        self.assertNotIn("{commit}", s)
        commit = re.search(r"commit ([0-9a-f]{7,})", s).group(1)
        self.assertIn("commit " + commit + " (VERSION file", s)
        self.assertEqual(shell_of(s), shell_of((self.out / "blank.html").read_text()))


if __name__ == "__main__":
    unittest.main()
