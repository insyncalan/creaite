"""#122 step A: Current state's three heading levels round-trip through the project CLAUDE.md's `## Current state` section.

Run: python3 dev/tests/test_current_headings.py

The dashboard's editor has Heading 1 to 3. Current state's text is read to the next `## ` line (build_dashboard.memory,
report.saved_current, report.replace_current), so the levels are stored `###`, `####` and `#####` (Alan, 15-10-2026), and a
`## ` line must never come out of the editor. Word reads the same three (docx_tools). The editor's own side (the mapping both
ways, the toolbar writing them, a paste) is test_editor_bar.
"""
import itertools
import re
import sys
import tempfile
import time
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

    # ----- #134 (independent review): a list whose first item is empty, marks that nest, a quote that holds blocks -----
    @staticmethod
    def base_md_blocks(md):
        """prep_page.md_blocks as it was before #134 (commit 0fdbe4a), for lists, paragraphs and headings: the behaviour the refactor must keep."""
        t = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", str(md or ""))
        t = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", t)
        blocks, st = [], {"para": [], "lst": None}

        def flush():
            if st["para"]:
                blocks.append(("p", " ".join(st["para"])))
            if st["lst"]:
                blocks.append(st["lst"])
            st["para"], st["lst"] = [], None

        def item(line, bullet, number):
            kind = "ul" if bullet else "ol"
            if st["para"] or (st["lst"] and st["lst"][0] != kind):
                flush()
            st["lst"] = st["lst"] or (kind, [])
            st["lst"][1].append((bullet or number).group(1).strip())

        def other(line, head):
            if head:
                flush()
                blocks.append(("p", f"**{head.group(1).strip().strip('*')}**"))
            elif st["lst"] and line[:1].isspace():
                st["lst"][1][-1] += " " + line.strip()
            else:
                if st["lst"]:
                    flush()
                st["para"].append(line.strip())
        for line in t.splitlines():
            bullet, number = re.match(r"\s*[-*•]\s+(.*)", line), re.match(r"\s*\d+[.)]\s+(.*)", line)
            if not line.strip():
                flush()
            elif bullet or number:
                item(line, bullet, number)
            else:
                other(line, re.match(r"\s*#+\s*(.*)", line))
        flush()
        return blocks

    def test_a_list_whose_first_item_is_empty_does_not_crash_and_keeps_its_items(self):
        import prep_page
        import creaite_doc
        for md in ("- \n  x", "1. \n  x", "* \n\tx", "- a\n- \n  x", "- \n- \n  x", "1) \n   x\n2) y"):
            with self.subTest(md=md):
                self.assertEqual(prep_page.md_blocks(md), self.base_md_blocks(md))
                creaite_doc.md_html(md)                                       # the HTML and PDF export, and the Prep page
        self.assertEqual(prep_page.md_blocks("- a\n- \n  x"), [("ul", ["a", "x".rjust(2)])])

    def test_lists_paragraphs_and_headings_read_as_before_for_every_short_mix_of_lines(self):
        import prep_page
        lines = ["- a", "- ", "-", "* b", "• c", "1. d", "2) ", "  x", "\ty", "", "text", "# h", "### H *", "  - n", "plain two", "1.x"]
        for n in (1, 2, 3, 4):
            for combo in itertools.product(lines, repeat=n):
                md = "\n".join(combo)
                self.assertEqual(prep_page.md_blocks(md), self.base_md_blocks(md), repr(md))

    # every mark the bar writes, in every order it can be nested (bold **, italic _ or *, strikethrough ~~)
    WRAPS = (("bold", "**"), ("italic", "_"), ("italic", "*"), ("strike", "~~"))

    def nestings(self):
        """(set of marks, Markdown) for x wrapped in every ordered pair and triple of marks, and each mark alone."""
        for size in (1, 2, 3):
            for combo in itertools.permutations(self.WRAPS, size):
                names = [n for n, _ in combo]
                if len(set(names)) < size:
                    continue
                inner = "x"
                for _, w in reversed(combo):
                    inner = w + inner + w
                yield set(names), f"a {inner} b"

    def test_marks_nest_in_word_with_no_marker_left_over(self):
        para = '<w:p><w:r><w:rPr/><w:t>{{TEXT}}</w:t></w:r></w:p>'
        n = 0
        for marks, md in self.nestings():
            with self.subTest(md=md):
                n += 1
                runs = dt.md_runs(md)
                self.assertEqual("".join(r[0] for r in runs), "a x b")
                x = next(r for r in runs if r[0] == "x")
                self.assertEqual({"bold": x[1], "italic": x[2], "strike": x[3]}, {m: m in marks for m in ("bold", "italic", "strike")})
                xml = dt.md_paras(para, "TEXT", md)
                for mark in ("**", "_", "~~", "`"):
                    self.assertNotIn(mark, "".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", xml)))
                self.assertEqual("<w:strike/>" in xml, "strike" in marks)
        self.assertGreater(n, 25)

    def test_marks_nest_in_html_and_pdf_the_same_way(self):
        import creaite_doc
        for marks, md in self.nestings():
            with self.subTest(md=md):
                html = creaite_doc.md_html(md)
                self.assertEqual(re.sub(r"<[^>]+>", "", html), "<p>a x b</p>".replace("<p>", "").replace("</p>", ""))
                for mark in ("**", "_", "~~", "`", "*"):
                    self.assertNotIn(mark, html)
                tags = {"bold": "strong", "italic": "em", "strike": "s"}
                inner = re.search(r"((?:<(?:strong|em|s)>)+)x((?:</(?:strong|em|s)>)+)", html)
                self.assertIsNotNone(inner, html)
                self.assertEqual(set(re.findall(r"<(\w+)>", inner.group(1))), {tags[m] for m in marks})

    def test_a_pair_of_marks_inside_a_longer_sentence_and_beside_each_other(self):
        import creaite_doc
        for md, want in (("~~a **b** c~~", "<p><s>a </s><strong><s>b</s></strong><s> c</s></p>"),
                         ("**a** and _b_ and ~~c~~", "<p><strong>a</strong> and <em>b</em> and <s>c</s></p>"),
                         ("**`x`** y", "<p><strong>x</strong> y</p>"), ("snake_case and 5 * 3", "<p>snake_case and 5  3</p>")):
            with self.subTest(md=md):
                self.assertEqual(creaite_doc.md_html(md), want)
        self.assertEqual(dt.plain("[**a** b](http://u.example) z"), "a b (http://u.example) z")       # the address follows the link's last words once
        self.assertEqual([r[4] for r in dt.md_runs("[**a** b](http://u.example) z")], [None, "http://u.example", None])

    def test_reading_marks_takes_time_in_proportion_to_the_text_even_for_text_made_of_openers(self):
        import prep_page
        for unit in ("*a ", "_a ", "~~a ", "**a ", "[", "[a ", "`a ", "**_~~a ", "*a _b ", "[a](http://x ", "*a* "):
            with self.subTest(unit=unit):
                text = unit * 30000
                started = time.perf_counter()
                dt.md_runs(text)
                prep_page.md_inline(text)
                self.assertLess(time.perf_counter() - started, 3.0)

    def test_a_quote_can_hold_headings_and_lists_and_both_exports_draw_them_inside_it(self):
        import creaite_doc
        import prep_page
        md = "> #### Inside\n> - one\n> - two\n>\n> closing words"
        self.assertEqual(dt.md_blocks(md), [("qb", [("h2", "Inside"), ("list", [(0, False, "one"), (0, False, "two")]), ("p", "closing words")])])
        para = '<w:p><w:r><w:rPr/><w:t>{{TEXT}}</w:t></w:r></w:p>'
        xml = dt.md_paras(para, "TEXT", md)
        shown = "\n".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", xml))
        for mark in ("#", ">", "- one"):
            self.assertNotIn(mark, shown)
        self.assertEqual(dt.md_lines(md), ["Inside", "• one", "• two", "closing words"])
        self.assertIn('w:left="927"', xml)                                                # a list item in a quote: the quote's indent and its own
        self.assertEqual(xml.count("<w:i/>"), xml.count("<w:r>"), "everything in the quote is italic")
        html = creaite_doc.md_html(md)
        self.assertEqual(html, "<blockquote><p><strong>Inside</strong></p><ul><li>one</li><li>two</li></ul><p>closing words</p></blockquote>")
        self.assertEqual(prep_page.blocks_html(prep_page.md_blocks("> - a")), "<blockquote><ul><li>a</li></ul></blockquote>")
        self.assertEqual(dt.md_normalise(md), "> #### Inside\n>\n> - one\n> - two\n>\n> closing words")
        self.assertEqual(dt.md_normalise(dt.md_normalise(md)), dt.md_normalise(md))             # stored text is stable
        self.assertEqual(dt.md_blocks("> a\n> b"), [("q", "a b")])                               # a plain quote is as it was

    def test_the_prep_page_styles_a_quote_and_the_state_summary_leaves_quotes_out_of_the_points(self):
        import prep_page
        self.assertIn("blockquote{", prep_page.CSS)
        import creaite_doc
        self.assertIn("blockquote{", creaite_doc.CSS)                                     # the Word-like rule for a quote in HTML and PDF
        head, points, n = prep_page.state_parts("Headline\n\n> a quote\n\n- one\n- two")
        self.assertEqual((head, points, n), ("Headline", ["one", "two"], 2))
        self.assertEqual(prep_page.state_parts("Headline\n\n> a quote\n\nPara")[1:], (["a quote", "Para"], 2))
        self.assertEqual(prep_page.state_parts("Headline\n\n> - a\n\n- one")[1:], (["one"], 1))


if __name__ == "__main__":
    unittest.main()
