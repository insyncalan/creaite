"""#193: the dashboard's style.css keeps to the design tokens (font size --fs-*, radius --r-*, line height --lh-*, z-index --z-*).

A literal that equals a token's value must be the token. The few literals left off the scale (they would change the
rendering if moved to a neighbouring token) are listed below with a reason and a ceiling: a new one, or one more use of
an old one, fails. Lower a ceiling when a use is removed. The BL-325 scale block itself (the definitions) is skipped.

Run: python3 dev/tests/test_style_tokens.py     (quick tier: no Chrome, no vault)
"""
import re
import sys
import unittest
from collections import Counter
from pathlib import Path

CSS = Path(__file__).resolve().parents[2] / "system" / "templates" / "dashboard" / "style.css"

# Off-scale literals kept on purpose: value -> (ceiling, reason).
FONT_SIZES = {
    "9.5px": (2, "micro badge text, between 10 and 12"),
    "10.5px": (4, "small caps labels; 10 or 12 would change the look"),
    "11px": (25, "the dense table/meta size; no token between 10 and 12 (a scale decision for later)"),
    "12.5px": (9, "body of compact rows; between 12 and 13"),
    "15px": (2, "between 14 and 16"),
    "19px": (1, "one heading, between 18 and 22"),
    "20px": (1, "one heading, between 18 and 22"),
    "24px": (1, "one heading, between 22 and 34"),
    "26px": (2, "stat numbers, between 22 and 34"),
}
RADII = {
    "6px": (11, "control corners, between --r-sm and --r-md"),
    "10px": (7, "popover corners (--ctl-r-lg is 10px for the search bar only)"),
    "7px": (4, "inner corners of 8px boxes with a 1px border"),
    "2px": (4, "hairline marks and bars"),
    "3px": (2, "small marks"),
    "0 3px 3px 0": (1, "the side tab's right edge"),
}
LINE_HEIGHTS = {
    "0": (1, "collapses an inline icon holder"),
    "1.1": (2, "display numbers"), "1.14": (1, "one label"), "1.2": (1, "one heading"), "1.3": (1, "one heading"),
    "1.35": (1, "one block"), "1.45": (1, "one block"), "1.65": (1, "long-form help text"),
    "17px": (1, "one row"), "25px": (1, "one row"), "30px": (1, "one row"),
}
Z_ALLOWED = {"auto", "calc(var(--z-sticky,2) + 1)", "var(--z-tip,200)", "var(--z-pop-over,30)"}

FS_ON = {"10px", "12px", "13px", "14px", "16px", "18px", "22px", "34px"}
R_ON = {"4px", "8px", "12px", "16px", "999px"}
LH_ON = {"1", "1.25", "1.4", "1.5", "14px", "16px", "18px", "20px", "22px", "24px", "28px"}


def body():
    s = CSS.read_text()
    a = s.index("/* ===== BL-325 scale")
    b = s.index("/* ===== end BL-325 scale")
    return s[:a] + s[b:]


def values(prop, text):
    return re.findall(r"(?<![\w-])%s:\s*([^;}]*?)\s*(?=[;}]|!important)" % re.escape(prop), text)


class StyleTokens(unittest.TestCase):
    def setUp(self):
        self.css = body()

    def ceilings(self, prop, allowed, on_scale):
        used = Counter(v for v in values(prop, self.css) if "var(" not in v)
        for v, n in used.items():
            if prop == "border-radius":
                parts = v.split()
                if any(p in on_scale for p in parts):
                    self.fail("%s: %s uses an on-scale value; write the token" % (prop, v))
            elif v in on_scale:
                self.fail("%s:%s equals a token; write the token (%d uses)" % (prop, v, n))
            if v in ("50%",) or not re.fullmatch(r"[\d. ]+(px)?( [\d.]+(px)?)*", v) or (v == "0" and prop != "line-height"):
                continue   # keywords, em/%/calc (the listed exceptions) and a zero radius
            if v not in allowed:
                self.fail("%s:%s is a new literal; use a token or add it to the allow-list with a reason" % (prop, v))
            self.assertLessEqual(n, allowed[v][0], "%s:%s used %d times, ceiling %d" % (prop, v, n, allowed[v][0]))

    def test_font_size(self):
        self.ceilings("font-size", FONT_SIZES, FS_ON)

    def test_radius(self):
        self.ceilings("border-radius", RADII, R_ON)

    def test_line_height(self):
        self.ceilings("line-height", LINE_HEIGHTS, LH_ON)

    def test_z_index(self):
        for v in values("z-index", self.css):
            self.assertTrue(v in Z_ALLOWED or re.fullmatch(r"var\(--z-[a-z0-9-]+\)", v),
                            "z-index:%s is a raw number; add a --z-* layer" % v)

    def test_headings_use_tokens(self):
        """#193: the page title and section heading sizes are --fs-h1 and --fs-h2 on the base rules."""
        self.assertIn("h1{font:500 var(--fs-h1)/var(--lh-h1)", self.css)
        self.assertIn("h2{font:500 var(--fs-h2)/var(--lh-h2)", self.css)
        self.assertNotIn("font-size:15px;line-height:var(--lh-24)", self.css)

    def test_one_field_one_chip(self):
        """#193: one field rule and one chip rule; a context does not draw its own height, radius or ground again."""
        n = len(re.findall(r"(?m)^\.chip,\.vchip\{", self.css))
        self.assertEqual(n, 1, "one chip definition")
        for ctx in (".prepmeta .chip{", ".shape .chip{", ".pp .chip{", ".rp .chip{", ".rp-cockcard .chip{"):
            self.assertNotIn(ctx, self.css, ctx + " is a second chip style")
        self.assertRegex(self.css, r"\.wbulk select[^{]*\{height:var\(--ctl-h\);border:1px solid var\(--line\);border-radius:var\(--ctl-r\)")
        for pat in (r"\.fpl input\{[^}]*height:\d", r"\.handbar input\[type=text\]\{[^}]*height:\d",
                    r"\.linkpop input\{[^}]*height:\d", r"\.fsel\{height:36px"):
            self.assertNotRegex(self.css, pat, "a context draws its own field/button size: " + pat)

    def test_tokens_defined(self):
        s = CSS.read_text()
        for name in set(re.findall(r"var\((--(?:lh|z)-[a-z0-9-]+)\)", s)):
            self.assertRegex(s, r"(?<![\w)-])%s:" % re.escape(name), name + " is read but not defined")


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]], verbosity=1)
