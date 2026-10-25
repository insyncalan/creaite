"""#368 (release 2.6.8): the client-safe "I sent it" recognition reads seven shapes, fails closed, and each shape's handling is
proved needed by a mutant. Fictional names only.

Failure that matters: a sent line NOT recognised (false negative) lets Alan's chase log into a client text or an email (a leak). A
line wrongly recognised (false positive) only strikes a line or holds a draft. The code leans to recognising.

Run: python3 dev/tests/test_sent_shapes_368.py     (quick tier: no Chrome, no model)
"""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
import linktext  # noqa: E402
import edit_ai  # noqa: E402

SHAPES = {
    "lower case": "17-10-2026: chased Sara Example by email.",
    "upper case BY": "17-10-2026: CHASED SARA EXAMPLE BY EMAIL.",
    "non-breaking hyphens": "17‑10‑2026: Chased Sara Example by email.",
    "full-width colon": "17-10-2026： Chased Sara Example by email.",
    "name over two lines": "17-10-2026: Chased Sara\nExample by email.",
    "bullet and ISO date": "- 2026-10-17: Emailed Tom Reid by message asking for an update.",
    "run into a sentence": "Waiting on the vendor. 17-10-2026: Asked Chris Dunn for a decision by email.",
}
# text that looks alike but is not an "I sent it" line
NEGATIVES = [
    "We chased the supplier last week by email.",
    "17-10-2026: Supplier answered by email",
    "17-10-2026 Chased Sara by email",                    # no colon after the date
    "Chased Sara Example by email yesterday",             # no date
    "17-10-2026: Chased Sara Example and she replied.",   # no \"by email|message\"
    "The client asked by email on 17-10-2026 for the plan.",
    "17-10-2026: Meeting held; actions sent by email later.",   # not Chased/Emailed/Asked first
]


class Shapes(unittest.TestCase):
    def test_every_shape_is_recognised(self):
        for name, line in SHAPES.items():
            self.assertTrue(linktext.sent_has("Note\n" + line + "\nend"), name)

    def test_every_shape_is_stripped_and_the_rest_kept(self):
        for name, line in SHAPES.items():
            out = linktext.sent_strip("Keep this\n" + line + "\nand this")
            low = out.lower()
            for bit in ("chased", "emailed", "asked", "by email", "by message", "sara", "tom", "chris"):
                self.assertNotIn(bit, low, (name, out))
            self.assertTrue(out.startswith("Keep this") and out.endswith("and this"), (name, out))

    def test_look_alike_text_is_not_a_sent_line(self):
        for t in NEGATIVES:
            self.assertFalse(linktext.sent_has(t), t)
            self.assertEqual(linktext.sent_strip(t), t, t)

    def test_html_and_crlf_still_read(self):
        self.assertTrue(linktext.sent_has("<p>17-10-2026: Chased Sara by email.</p>"))
        self.assertEqual(linktext.sent_strip("Waiting\r\n17-10-2026: Chased Sara by email.\r\nNext"), "Waiting\nNext")

    def test_the_guarded_check_reads_the_shapes_too(self):
        # client_leak calls linktext.sent_has on the text it checks; the shapes must reach it through that one function
        for name, line in SHAPES.items():
            self.assertTrue(linktext.sent_has(line), name)


class Mutants(unittest.TestCase):
    """Take away one shape's handling: its test case must then fail (so the case really tests that handling)."""

    def with_mutant(self, shape, **patch):
        old = {k: getattr(linktext, k) for k in patch}
        for k, v in patch.items():
            setattr(linktext, k, v)
        try:
            return linktext.sent_has("Note\n" + SHAPES[shape])
        finally:
            for k, v in old.items():
                setattr(linktext, k, v)

    def test_case_mutant(self):
        m = re.compile(linktext.SENT_LINE.pattern)            # no re.I
        self.assertTrue(linktext.sent_has("Note\n" + SHAPES["upper case BY"]))
        self.assertFalse(self.with_mutant("upper case BY", SENT_LINE=m))
        self.assertFalse(self.with_mutant("lower case", SENT_LINE=re.compile(linktext.SENT_LINE.pattern.replace("chased", "Chased"))))

    def test_normalisation_mutant(self):
        plain = lambda t: linktext._sent_norm(t)              # no edit_ai.normal
        for shape in ("non-breaking hyphens", "full-width colon"):
            self.assertTrue(linktext.sent_has("Note\n" + SHAPES[shape]), shape)
            self.assertFalse(self.with_mutant(shape, _sent_form=plain), shape)

    def test_two_line_name_mutant(self):
        one_line = re.compile(linktext.SENT_LINE.pattern.replace("(?:[^%s]*?(?:\\r\\n|[%s])[ \\t]*)?" % (linktext._NL, linktext._NL), ""))
        self.assertNotEqual(one_line.pattern, linktext.SENT_LINE.pattern, "the mutant must change the pattern")
        self.assertTrue(linktext.sent_has("Note\n" + SHAPES["name over two lines"]))
        self.assertFalse(self.with_mutant("name over two lines", SENT_LINE=one_line))

    def test_iso_date_and_bullet_mutant(self):
        no_iso = re.compile(linktext.SENT_LINE.pattern.replace(linktext._SENT_DATE, r"\d{2}\s*-\s*\d{2}\s*-\s*\d{4}"), re.I)
        self.assertNotEqual(no_iso.pattern, linktext.SENT_LINE.pattern)
        self.assertFalse(self.with_mutant("bullet and ISO date", SENT_LINE=no_iso))

    def test_run_in_mutant(self):
        anchored = re.compile(r"^[ \t]*" + linktext.SENT_LINE.pattern, re.I | re.M)      # only at a line's start
        self.assertFalse(self.with_mutant("run into a sentence", SENT_LINE=anchored))

    def test_edit_ai_normal_is_what_reads_the_hyphens(self):
        self.assertIn("-", edit_ai.normal("17‑10‑2026"))


if __name__ == "__main__":
    unittest.main()
