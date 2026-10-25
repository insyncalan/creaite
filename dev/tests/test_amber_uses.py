"""#341 item 17: amber means "at risk" and nothing else. Reads the stylesheet and the sources and fails when a rule paints with
--warn or --warn-soft that is not on the list in dev/tests/amber-allowed.txt (Alan decides before a line is added there).
No browser. Run: python3 dev/tests/test_amber_uses.py"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSS = ROOT / "system/templates/dashboard/style.css"
ALLOWED = Path(__file__).with_name("amber-allowed.txt")
SRC_DIRS = [ROOT / "system/templates/dashboard/src", ROOT / "system/templates/dashboard/shell.html", ROOT / "system/scripts"]


def allowed():
    css, files = set(), set()
    for line in ALLOWED.read_text(encoding="utf-8").splitlines():
        if line.startswith("css: "):
            css.add(" ".join(line[5:].split()))
        elif line.startswith("file: "):
            files.add(line[6:].strip())
    return css, files


class AmberUses(unittest.TestCase):
    def test_only_the_listed_rules_paint_with_amber(self):
        text = CSS.read_text(encoding="utf-8")
        used = set()
        for m in re.finditer(r"([^{}]*)\{([^{}]*)\}", text):
            sel = " ".join(m.group(1).split("*/")[-1].split())
            if re.search(r"var\(--warn", m.group(2)):
                used.add(sel)
        css, _ = allowed()
        self.assertEqual(sorted(used - css), [], "a rule uses amber but is not on the list (amber is for At risk only)")
        self.assertEqual(sorted(css - used), [], "listed but no longer used: remove it from the list")

    def test_no_raw_amber_fallback(self):
        self.assertNotIn("B54708", CSS.read_text(encoding="utf-8"))

    def test_sources_outside_the_stylesheet_use_amber_only_where_listed(self):
        _, files = allowed()
        found = set()
        for base in SRC_DIRS:
            paths = [base] if base.is_file() else [p for p in base.rglob("*") if p.suffix in (".js", ".jsx", ".py")]
            for p in paths:
                if "node_modules" in p.parts:
                    continue
                if re.search(r"var\(--warn|--warnbg|\bwarnbg\b", p.read_text(encoding="utf-8", errors="ignore")):
                    found.add(str(p.relative_to(ROOT)))
        self.assertEqual(sorted(found - files), [], "a source names amber but is not on the list")

    def test_the_palettes_still_define_it(self):
        text = CSS.read_text(encoding="utf-8")
        self.assertGreaterEqual(len(re.findall(r"--warn:#", text)), 9)        # at risk keeps its colour in every palette


if __name__ == "__main__":
    unittest.main()
