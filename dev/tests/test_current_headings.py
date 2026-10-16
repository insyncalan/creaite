"""#122 step A: Current state's three heading levels round-trip through the project CLAUDE.md's `## Current state` section.

Run: python3 dev/tests/test_current_headings.py

The dashboard's editor has Heading 1 to 3. Current state's text is read to the next `## ` line (build_dashboard.memory,
report.saved_current, report.replace_current), so the levels are stored `###`, `####` and `#####` (Alan, 15-10-2026), and a
`## ` line must never come out of the editor. Word reads the same three (docx_tools). The editor's own side (the mapping both
ways, the toolbar writing them, a paste) is test_editor_bar.
"""
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "system" / "scripts"))
import build_dashboard  # noqa: E402
import docx_tools as dt  # noqa: E402
import report  # noqa: E402

STATE = "### Top\n\nFirst paragraph with **bold**.\n\n#### Middle\n\n- a bullet\n  - nested\n\n##### Low\n\n> a quote\n\nLast line."
FILE = f"# ABC\n\n**Client / partner:** Falcon\n\n## Current state\n\n{STATE}\n\n## Milestones\n\nGo-live 2026-12-01.\n\n## Notes\n\nKept.\n"


class Headings(unittest.TestCase):
    def test_the_three_levels_are_blocks_of_their_own(self):
        kinds = [k for k, _ in dt.md_blocks(STATE)]
        self.assertEqual([k for k in kinds if k.startswith("h")], ["h", "h2", "h3"])
        self.assertEqual(dt.md_blocks("#### Two")[0], ("h2", "Two"))
        self.assertEqual(dt.md_blocks("##### Three")[0], ("h3", "Three"))
        self.assertEqual(dt.md_blocks("###### Six")[0][0], "p")          # deeper than the editor's third level is just text

    def test_normalising_keeps_them_and_is_stable(self):
        self.assertEqual(dt.md_normalise(STATE), STATE)
        self.assertEqual(dt.md_normalise(dt.md_normalise(STATE)), STATE)
        self.assertEqual(dt.join_panes(*dt.split_panes(STATE)), STATE)

    def test_the_section_reader_and_writer_keep_the_next_section(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "CLAUDE.md").write_text(FILE, encoding="utf-8")
            self.assertEqual(build_dashboard.memory(folder)["current"], STATE)                       # the dashboard's reader
            self.assertEqual(report.saved_current(FILE), STATE)                                      # the reports' reader
            new = "### Renamed\n\nText.\n\n#### Sub\n\n##### Sub-sub\n\nMore."
            out = report.replace_current(FILE, new)                                                  # a save
            self.assertEqual(report.saved_current(out), new)
            self.assertEqual(re.findall(r"(?m)^## (.*)$", out), ["Current state", "Milestones", "Notes"])
            self.assertIn("Go-live 2026-12-01.", out)
            self.assertIn("Kept.", out)
            (folder / "CLAUDE.md").write_text(out, encoding="utf-8")
            self.assertEqual(build_dashboard.memory(folder)["current"], new)

    def test_a_level_two_heading_would_cut_the_section_which_is_why_it_is_never_stored(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "CLAUDE.md").write_text(FILE.replace("#### Middle", "## Middle"), encoding="utf-8")
            self.assertEqual(build_dashboard.memory(folder)["current"], "### Top\n\nFirst paragraph with **bold**.")   # the cut

    def test_word_shows_each_level_as_text_in_three_weights_and_no_hash(self):
        para = '<w:p><w:r><w:rPr><w:b/></w:rPr><w:t>{{CURRENT}}</w:t></w:r></w:p>'
        xml = dt.md_paras(para, "CURRENT", "### A\n\n#### B\n\n##### C\n\ntext")
        runs = re.findall(r"<w:r>(.*?)</w:r>", xml)
        self.assertEqual([re.search(r"<w:t[^>]*>(.*?)</w:t>", r).group(1) for r in runs], ["A", "B", "C", "text"])
        self.assertNotIn("#", xml)
        self.assertIn("<w:b/>", runs[1])
        self.assertNotIn("<w:i/>", runs[1])
        self.assertIn("<w:b/><w:i/>", runs[2])                          # the third level: bold italic
        self.assertNotIn("<w:b/>", runs[3])


if __name__ == "__main__":
    unittest.main()
