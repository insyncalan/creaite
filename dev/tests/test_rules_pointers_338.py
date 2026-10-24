"""#338 N4: every pointer in the slimmed rules to creaite-reference.md names something real.

Useful only after v263-338 merges: the reference file (system/templates/creaite-reference.md) and the slimmed rules exist only on that
branch, so on any other tree the file-based tests skip with a message. The checks:
  1. the rules name the reference file by its real path, and that file exists;
  2. a pointer that names a heading (in quotes, backticks or after a ">" or the single guillemet) names a real `##` heading of the reference;
  3. every `##` heading of the rules, except the two that stay whole in the rules, has a heading of the same name in the reference.
The extractor and the checks are also tried on synthetic text (always run), so a pointer to a heading that is not there is caught.

Run: python3 dev/tests/test_rules_pointers_338.py
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RULES = ROOT / "system" / "creaite-rules.md"
REFERENCE = ROOT / "system" / "templates" / "creaite-reference.md"
REF_PATH = "system/templates/creaite-reference.md"
WHOLE_IN_RULES = {"creaite rules", "Non-negotiables"}         # headings that are not moved to the reference
SKIP = f"{REF_PATH} is absent: this test is useful only on the v263-338 tree (or after it merges)"


def headings(text) -> list:
    """The `##` headings of a Markdown text, without the marks."""
    return [m.group(1).strip() for m in re.finditer(r"^#{1,2} (.+)$", text, re.M)]


def pointer_lines(text) -> list:
    """The lines that point at the reference file (they say 'reference')."""
    return [ln for ln in text.splitlines() if re.search(r"\breference\b|creaite-reference", ln, re.I)]


def named_headings(line) -> list:
    """Heading names a pointer line gives after the word 'reference': a quoted, backticked or guillemet-marked name (a file path or a
    command in backticks is not a heading name and is left out)."""
    tail = re.split(r"reference", line, maxsplit=1, flags=re.I)[-1] if re.search(r"reference", line, re.I) else ""
    names = re.findall(r"[“\"]([^”\"]{3,60})[”\"]|›\s*([A-Z][^.;:`|)]{2,60})", tail)
    return [(a or b).strip() for a, b in names]


def problems(rules, reference) -> list:
    """What is wrong with the rules' pointers, as plain sentences (an empty list is clean)."""
    out = []
    if REF_PATH not in rules:
        out.append(f"the rules never name {REF_PATH}")
    ref = {h.lower() for h in headings(reference)}
    for ln in pointer_lines(rules):
        for name in named_headings(ln):
            if name.lower() not in ref:
                out.append(f"pointer names a heading that is not in the reference: {name}")
    for h in headings(rules):
        if h not in WHOLE_IN_RULES and h.lower() not in ref:
            out.append(f"rules section without a reference section of the same name: {h}")
    return out


class Extractor(unittest.TestCase):
    RULES = ("# creaite rules\n\nSee `system/templates/creaite-reference.md`.\n\n## Folder map\n\nThe long cell is in the reference "
             "file (“Folder map”).\n\n## Updates\n\nx\n")
    REF = "# creaite reference\n\n## Folder map\n\n## Updates\n"

    def test_clean(self):
        self.assertEqual(problems(self.RULES, self.REF), [])

    def test_named_heading_that_is_missing_is_caught(self):
        bad = self.RULES.replace("Folder map”)", "Folder maps”)")
        self.assertTrue(any("Folder maps" in p for p in problems(bad, self.REF)))

    def test_section_missing_from_reference_is_caught(self):
        self.assertTrue(any("Updates" in p for p in problems(self.RULES, self.REF.replace("## Updates\n", ""))))

    def test_missing_path_is_caught(self):
        self.assertTrue(any("never name" in p for p in problems(self.RULES.replace(REF_PATH, "x"), self.REF)))

    def test_a_path_in_backticks_is_not_a_heading(self):
        self.assertEqual(named_headings("tiers in the reference file `schema.sql`"), [])

    def test_guillemet_pointer(self):
        self.assertEqual(named_headings("in the reference › Retention."), ["Retention"])


@unittest.skipUnless(REFERENCE.is_file(), SKIP)
class RealTree(unittest.TestCase):
    def test_pointers_are_real(self):
        self.assertEqual(problems(RULES.read_text(encoding="utf-8"), REFERENCE.read_text(encoding="utf-8")), [])

    def test_reference_is_not_empty(self):
        self.assertGreaterEqual(len(headings(REFERENCE.read_text(encoding="utf-8"))), 5)


if __name__ == "__main__":
    unittest.main()
