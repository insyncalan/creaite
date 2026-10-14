"""BL-273: the Stage wordmark's outlining tool (dev/tools/outline_wordmark.py) and its committed output.

The committed JSON and preview parse, and every path is non-empty (standard library only). The tool itself runs against a
stand-in font built with fontTools (skipped without fontTools); the tests never contact the network.

Run: python3 dev/tests/test_outline_wordmark.py
"""
import json
import re
import sys
import tempfile
import unittest
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "dev" / "tools"))
import outline_wordmark as ow  # noqa: E402

LOGO = ROOT / "dev" / "reference" / "logo"
HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
SVG = "{http://www.w3.org/2000/svg}"


def no_network(*a, **k):
    raise AssertionError("a test contacted the network")


def stand_in_font():
    """A tiny TrueType font with a square for each letter of "creaite", 600 units wide like Plex Mono."""
    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    chars = sorted(set(ow.TEXT))
    names = [".notdef"] + chars
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(names)
    fb.setupCharacterMap({ord(c): c for c in chars})
    glyphs = {}
    for n in names:
        pen = TTGlyphPen(None)
        pen.moveTo((60, 0))
        pen.lineTo((60, 500))
        pen.lineTo((540, 500))
        pen.lineTo((540, 0))
        pen.closePath()
        glyphs[n] = pen.glyph()
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics({n: (600, 60) for n in names})
    fb.setupHorizontalHeader(ascent=1025, descent=-275)
    fb.setupNameTable({"familyName": "Stand In", "styleName": "Regular"})
    fb.setupOS2(sTypoAscender=1025, sTypoDescender=-275, sCapHeight=698, sxHeight=516)
    fb.setupPost()
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "stand-in.ttf"
        fb.save(str(p))
        return p.read_bytes()


def check_record(case, record):
    """The record holds a non-empty path per letter of the word, a whole-word path, a view box and metrics."""
    case.assertEqual(record["text"], "creaite")
    case.assertEqual([g["char"] for g in record["glyphs"]], list("creaite"))
    for g in record["glyphs"]:
        case.assertTrue(g["d"].strip().startswith("M"), g["char"])
    case.assertTrue(record["d"].strip())
    case.assertEqual(len(record["viewBox"]), 4)
    case.assertGreater(record["viewBox"][2], 0)
    case.assertGreater(record["advance"], 0)
    for k in ("unitsPerEm", "ascent", "descent", "capHeight", "xHeight"):
        case.assertIn(k, record["metrics"])


def check_preview(case, text):
    """The preview is SVG with the word and the bar (BL-308: no dashed draft), coloured only by theme tokens."""
    root = ET.fromstring(text)
    case.assertEqual(root.tag, SVG + "svg")
    paths = root.findall(SVG + "path")
    case.assertEqual(len(paths), 1)
    case.assertTrue(all(p.get("d").strip() for p in paths))
    case.assertNotIn("stroke-dasharray", text)
    case.assertIn("var(--ink", paths[0].get("style"))
    case.assertIn("var(--accent", root.find(SVG + "rect").get("style"))
    case.assertIsNone(HEX.search(text), "a hard-coded colour")


class Committed(unittest.TestCase):
    """The files in dev/reference/logo/ parse and every path is non-empty."""

    def test_json(self):
        record = json.loads((LOGO / "wordmark-paths.json").read_text(encoding="utf-8"))
        check_record(self, record)
        self.assertEqual(record["font"]["sha256"], ow.SHA256)

    def test_preview(self):
        check_preview(self, (LOGO / "wordmark-preview.svg").read_text(encoding="utf-8"))

    def test_licence_and_no_font_committed(self):
        self.assertIn("SIL OPEN FONT LICENSE Version 1.1", (LOGO / "OFL.txt").read_text(encoding="utf-8"))
        fonts = [p for ext in ("ttf", "otf", "woff", "woff2", "zip") for p in (ROOT / "dev").rglob(f"*.{ext}")]
        self.assertEqual([p for p in fonts if "plex" in p.name.lower()], [])


class Tool(unittest.TestCase):
    """The tool outlines a stand-in font; no download."""

    @classmethod
    def setUpClass(cls):
        try:
            import fontTools  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("fontTools not installed (development only)") from None

    def test_outline_and_write(self):
        with mock.patch.object(urllib.request, "urlopen", no_network), tempfile.TemporaryDirectory() as tmp:
            record = ow.build(stand_in_font(), {"family": "Stand In"})
            check_record(self, record)
            self.assertEqual([g["x"] for g in record["glyphs"]][:3], [0.0, 35.2, 70.4])   # 600 units at 62 px, less 2
            js, svg = ow.write(record, tmp)
            check_record(self, json.loads(js.read_text(encoding="utf-8")))
            check_preview(self, svg.read_text(encoding="utf-8"))



class Fetch(unittest.TestCase):
    """A zip whose SHA-256 is not the pinned release's is refused (standard library only)."""

    def test_wrong_checksum_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            z = Path(tmp) / "ibm-plex-mono.zip"
            z.write_bytes(b"not the release")
            with self.assertRaises(SystemExit):
                ow.fetch(z)


if __name__ == "__main__":
    unittest.main()
