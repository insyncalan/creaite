"""#344: the design-system snapshot tool makes no Review page and regenerates gallery.html and blank.html from the same shell as the pages.

The gallery's curated parts (its own <style>, the eight sections, the token script) are pinned: by name here, and byte for byte against
the committed dev/design-system/gallery.html, so dropping any of them fails. Two runs must write the same bytes.
Run: python3 dev/tests/test_design_system_snapshots_344.py   (the Chrome part needs Google Chrome; two tool runs, about 30 seconds)
"""
import importlib.util
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "dev" / "tools" / "design_system_snapshots.py"
SRC = ROOT / "dev" / "tools" / "design_system_gallery.html"
COMMITTED = ROOT / "dev" / "design-system"
sys.path.insert(0, str(ROOT / "dev" / "tests"))
from test_dashboard import CHROME  # noqa: E402

SECTIONS = ["Colour (tokens; flips with Alt+D)", "Type", "Radius, shadow, spacing", "Buttons", "Pills, tags, chips", "Fields",
            "Navigation", "Surfaces"]
MARKERS = {"Colour (tokens; flips with Alt+D)": 'class="swatches"', "Buttons": 'class="btn primary sm"', "Fields": 'class="switch"',
           "Navigation": 'class="tabs projtabs"', "Surfaces": 'class="card curcard edt"'}
RULES = [".dsg{", ".dsg h2{", ".dsrow{", ".dslab b{", ".dslab code{", ".dsspec{", ".swatches{", ".sw{", ".sw i{", ".sw b{", ".sw span{"]
STAMP = re.compile(r"commit [0-9a-f]{7,} \(VERSION file [^)]*\) on \d{4}-\d{2}-\d{2}")


def load_tool():
    """The tool as a module (for curated(), BLANK_BODY and TOGGLE); importing it runs nothing."""
    spec = importlib.util.spec_from_file_location("design_system_snapshots", TOOL)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def element(html, start):
    """The whole element that opens at index start, nested elements of the same tag included."""
    tag = re.match(r"<(\w+)", html[start:]).group(1)
    depth = 0
    for m in re.finditer(r"<(/?)%s\b[^>]*>" % tag, html[start:]):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            return html[start:start + m.end()]
    raise AssertionError("unclosed <%s> at %d" % (tag, start))


def sections(html):
    """Each curated gallery section, in order, as {heading: markup}."""
    return {m.group(1): element(html, m.start()) for m in re.finditer(r'<section class="dsg"><h2>([^<]*)', html)}


def vfiles(html):
    """The inner markup of the #v-files view."""
    m = re.search(r'<section class="view[^"]*" id="v-files"[^>]*>', html)
    return element(html, m.start())[m.end() - m.start():-len("</section>")]


def head_style(html):
    """The <style> blocks inside <head>."""
    return re.findall(r"<style>.*?</style>", html[html.index("<head>"):html.index("</head>")], re.S)


def shell_of(html):
    """The rail's markup, which comes from the one shell and so must be the same in every file."""
    m = re.search(r'<nav class="rail".*?</nav>', html, re.S)
    return re.sub(r"\s+", " ", m.group(0)) if m else ""


class CuratedSource(unittest.TestCase):
    """No Chrome needed: the curated source holds every part, and matches the committed gallery byte for byte."""

    def setUp(self):
        self.tool = load_tool()
        self.style, self.body, self.tail = self.tool.curated(SRC.read_text())
        self.main = (COMMITTED / "gallery.html").read_text()

    def test_every_section_in_order_with_its_content(self):
        got = sections(self.body)
        self.assertEqual(list(got), SECTIONS)
        for name, mark in MARKERS.items():
            self.assertIn(mark, got[name], name)

    def test_sections_match_the_committed_gallery(self):
        self.assertEqual(sections(self.body), sections(self.main))

    def test_style_holds_every_rule_and_matches_the_committed_head(self):
        for r in RULES:
            self.assertIn(r, self.style)
        self.assertEqual([self.style], head_style(self.main))

    def test_tail_is_the_token_script(self):
        self.assertIn("function tok()", self.tail)
        self.assertIn(self.tail, self.main)

    def test_a_missing_marker_is_refused(self):
        text = SRC.read_text()
        for broken in (text.replace("\n<!--HEAD-->\n", "\n"), text.replace("\n<!--TAIL-->\n", "\n"),
                       text.split("\n<!--HEAD-->\n", 1)[1].replace("\n<!--TAIL-->\n", "\n<!--HEAD-->\n", 1)):
            with self.assertRaises(ValueError):
                self.tool.curated(broken)


@unittest.skipUnless(CHROME.exists(), "Google Chrome not installed")
class SnapshotTool(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.outs = [Path(cls.tmp.name) / "a", Path(cls.tmp.name) / "b"]
        for out in cls.outs:
            (out / "pages").mkdir(parents=True)
            (out / "pages" / "review.html").write_text("stale")  # a leftover from an older run
            r = subprocess.run([sys.executable, str(TOOL), "--repo", str(ROOT), "--out", str(out)], capture_output=True, text=True,
                               timeout=300)
            assert r.returncode == 0, r.stdout[-800:] + r.stderr[-800:]
        cls.out = cls.outs[0]
        cls.gallery = (cls.out / "gallery.html").read_text()
        cls.blank = (cls.out / "blank.html").read_text()
        cls.main = (COMMITTED / "gallery.html").read_text()
        cls.tool = load_tool()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_two_runs_write_the_same_bytes(self):
        a, b = self.outs
        names = sorted(str(p.relative_to(a)) for p in a.rglob("*") if p.is_file() and p.suffix != ".png")
        self.assertEqual(names, sorted(str(p.relative_to(b)) for p in b.rglob("*") if p.is_file() and p.suffix != ".png"))
        for n in names:
            self.assertEqual((a / n).read_bytes(), (b / n).read_bytes(), n)
        self.assertNotIn("creaite-test-", self.gallery)

    def test_no_review_page(self):
        self.assertFalse((self.out / "pages" / "review.html").exists())
        self.assertFalse((self.out / "shots" / "review-light.png").exists())
        self.assertNotIn("go('review')", TOOL.read_text())

    def test_blank_is_the_shell_with_an_empty_page(self):
        self.assertIn("A blank page in the real app shell", self.blank)
        self.assertIn('href="style.snapshot.css"', self.blank)
        self.assertEqual(vfiles(self.blank), self.tool.BLANK_BODY)
        self.assertEqual(vfiles(self.blank), vfiles((COMMITTED / "blank.html").read_text()))
        self.assertEqual(shell_of(self.blank), shell_of((self.out / "pages" / "files.html").read_text()))

    def test_gallery_keeps_its_own_style_in_the_head(self):
        style = head_style(self.gallery)
        self.assertEqual(style, head_style(self.main))
        for r in RULES:
            self.assertIn(r, style[0])

    def test_gallery_keeps_every_curated_section(self):
        got = sections(vfiles(self.gallery))
        self.assertEqual(list(got), SECTIONS)
        self.assertEqual(got, sections(self.main))

    def test_gallery_curated_parts_match_the_committed_gallery(self):
        self.assertEqual(STAMP.sub("STAMP", vfiles(self.gallery)), STAMP.sub("STAMP", vfiles(self.main)))
        self.assertIn("function tok()", self.gallery)
        self.assertIn(self.tool.TOGGLE, self.gallery)

    def test_gallery_stamp_and_shell(self):
        s = self.gallery
        self.assertIn("<h1>Design system gallery</h1>", s)
        for k in ("{commit}", "{version}", "{taken}"):
            self.assertNotIn(k, s)
        version = (ROOT / "VERSION").read_text().strip()
        commit = re.search(r"commit ([0-9a-f]{7,})", s).group(1)
        self.assertIn("commit " + commit + " (VERSION file " + version + ")", s)
        self.assertEqual(shell_of(s), shell_of(self.blank))

    def test_pages_link_the_stylesheet_one_folder_up_and_toggle(self):
        for p in (self.out / "pages").glob("*.html"):
            s = p.read_text()
            self.assertIn('<link rel="stylesheet" href="../style.snapshot.css">', s, p.name)
            self.assertIn(self.tool.TOGGLE, s, p.name)
        self.assertTrue((self.out / "style.snapshot.css").exists())


if __name__ == "__main__":
    unittest.main()
