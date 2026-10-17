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

    # ----- #134: the checklist (Current state stores "- [ ] text" / "- [x] text"; Word shows a box glyph) -----
    TASKS = "#### Next steps\n\n- [ ] Book the room\n- [x] Send the pack\n  - [ ] Nested step\n\n- an ordinary bullet\n\n##### Later\n\n1. numbered"

    def test_a_checklist_is_kept_by_normalising_and_never_makes_a_level_two_line(self):
        self.assertEqual(dt.md_normalise(self.TASKS), self.TASKS.replace("\n\n- an ordinary", "\n- an ordinary"))
        self.assertEqual(dt.md_normalise(dt.md_normalise(self.TASKS)), dt.md_normalise(self.TASKS))
        self.assertIsNone(re.search(r"(?m)^#{1,2} ", dt.md_normalise(self.TASKS)))

    def test_word_shows_a_checklist_with_box_glyphs_and_no_brackets(self):
        lines = dt.md_lines(self.TASKS)
        self.assertEqual(lines, ["Next steps", "☐ Book the room", "☑ Send the pack", "☐ Nested step", "• an ordinary bullet", "Later", "1. numbered"])
        para = '<w:p><w:r><w:rPr/><w:t>{{CURRENT}}</w:t></w:r></w:p>'
        xml = dt.md_paras(para, "CURRENT", self.TASKS)
        texts = [t for t in re.findall(r"<w:t[^>]*>(.*?)</w:t>", xml)]
        self.assertIn("☐ ", texts)
        self.assertIn("☑ ", texts)
        self.assertIn("Book the room", texts)
        self.assertNotIn("[ ]", xml)
        self.assertNotIn("[x]", xml)
        self.assertNotIn("#", xml)

    def test_a_checklist_edited_in_word_comes_back_as_a_checklist(self):
        back = dt.md_from_lines(dt.md_lines(self.TASKS))
        self.assertIn("- [ ] Book the room\n- [x] Send the pack\n- [ ] Nested step", back)
        self.assertEqual(dt.md_lines(back)[1:4], ["☐ Book the room", "☑ Send the pack", "☐ Nested step"])

    def test_the_prep_page_shows_a_checklist_item_with_its_glyph(self):
        import prep_page
        blocks = prep_page.md_blocks("- [ ] one\n- [x] two\n- three")
        self.assertEqual(blocks, [("ul", ["☐ one", "☑ two", "three"])])

    # ----- #134 (review): what the report sheet's toolbar writes, as Word and HTML/PDF draw it -----
    SHEET = "### Big\n\n#### Mid\n\n##### Small\n\n> a quote\n> over two lines\n\nSome ~~gone~~ words and **bold** ones.\n\n- item ~~struck~~"

    def test_what_the_sheet_toolbar_writes_leaves_no_marker_in_word_or_html(self):
        import creaite_doc
        para = '<w:p><w:r><w:rPr/><w:t>{{TEXT}}</w:t></w:r></w:p>'
        word = "\n".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", dt.md_paras(para, "TEXT", self.SHEET)))
        html = creaite_doc.md_html(self.SHEET)
        for mark in ("#", ">", "~~"):
            self.assertNotIn(mark, word)
        for mark in ("#", "&gt;", "~~"):
            self.assertNotIn(mark, html)
        self.assertIn("<blockquote><p>a quote over two lines</p></blockquote>", html)
        self.assertIn("<s>gone</s>", html)
        self.assertIn("<s>struck</s>", html)
        self.assertIn("<strong>bold</strong>", html)
        self.assertIn("<w:strike/>", dt.md_paras(para, "TEXT", self.SHEET))
        self.assertEqual(dt.md_lines(self.SHEET)[3], "a quote over two lines")

    def test_a_level_one_or_two_line_is_what_word_cannot_draw_which_is_why_the_sheet_shifts_its_levels(self):
        # the sheet editor writes Heading 1 to 3 as ### #### ##### (headShift, as Current state does); a bare # or ## would show as text in Word
        para = '<w:p><w:r><w:rPr/><w:t>{{TEXT}}</w:t></w:r></w:p>'
        self.assertIn("# Big", "\n".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", dt.md_paras(para, "TEXT", "# Big"))))

    # ----- #134 (review): the checklist reads the same in Word and on the Prep page -----
    TASK_CASES = ["- [ ]", "- [x]", "- [X]", "- [ ] a", "- [x] a b", "* [ ] star", "1. [ ] a", "2) [x] b", "- [ ]a", "- plain", "- [] none", "- [y] no"]

    def test_word_and_prep_agree_on_every_checklist_shape(self):
        import prep_page
        for md in self.TASK_CASES:
            with self.subTest(md=md):
                word = dt.md_lines(md)[0]
                kind, items = prep_page.md_blocks(md)[0]
                glyph = word[:1] in "☐☑"
                shown = word if glyph else re.sub(r"^(?:• |\d+\. )", "", word)
                self.assertEqual(shown.strip(), items[0].strip())
                self.assertEqual(glyph, items[0][:1] in "☐☑")

    def test_an_empty_checklist_item_is_a_box_in_both_and_a_numbered_one_is_text_in_both(self):
        import prep_page
        self.assertEqual(dt.md_lines("- [ ]"), ["☐ "])
        self.assertEqual(prep_page.md_blocks("- [ ]"), [("ul", ["☐"])])
        self.assertEqual(dt.md_lines("1. [ ] a"), ["1. [ ] a"])
        self.assertEqual(prep_page.md_blocks("1. [ ] a"), [("ol", ["[ ] a"])])
        self.assertEqual(dt.md_from_lines(["☐ "]), "- [ ]")                      # an empty box edited in Word comes back as one


if __name__ == "__main__":
    unittest.main()
