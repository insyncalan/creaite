"""#341 (release 2.6.5): plain structure checks for the look-and-feel items no other test measures.

Reads the source (the stylesheet, the dashboard's JS and the built page) and asserts on its text; it starts no browser.
Run: python3 dev/tests/test_v265_341_structure.py
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DASH = ROOT / "system" / "templates" / "dashboard"
CSS = (DASH / "style.css").read_text(encoding="utf-8")
FILES_JS = (DASH / "src" / "files.js").read_text(encoding="utf-8")
WORK_JS = (DASH / "src" / "work.js").read_text(encoding="utf-8")
SHELL = (DASH / "shell.html").read_text(encoding="utf-8")
BUILT = (ROOT / "system" / "templates" / "dashboard.html").read_text(encoding="utf-8")


def rule(text, selector_start):
    """The declaration block of the first rule whose selector starts with the given text."""
    i = text.index(selector_start)
    return text[text.index("{", i) + 1:text.index("}", i)]


class CockpitColumns(unittest.TestCase):
    def test_right_column_is_two_fifths(self):
        decl = rule(CSS, ".cock{display:grid")
        self.assertIn("grid-template-columns:minmax(0,3fr) minmax(0,2fr)", decl)
        self.assertNotIn("2fr 1fr", decl)

    def test_cards_fill_their_column(self):
        # the columns may shrink below their content, so a wide card never pushes the right column out
        self.assertIn("minmax(0,3fr)", CSS)
        self.assertIn("minmax(0,2fr)", CSS)

    def test_stacks_to_one_column_on_narrow_screens(self):
        self.assertRegex(CSS, r"@media \(max-width:1100px\)\{\.cock\{grid-template-columns:1fr\}")

    def test_built_page_carries_the_same_rule(self):
        self.assertIn("grid-template-columns:minmax(0,3fr) minmax(0,2fr)", BUILT)


class FilesViewRadios(unittest.TestCase):
    def test_view_chips_are_gone(self):
        self.assertNotIn('id="fquick"', SHELL)
        self.assertNotIn("#fquick", FILES_JS)
        self.assertNotIn('class="vchip" data-q', FILES_JS)

    def test_filter_has_the_four_views(self):
        self.assertIn('["all","All files"],["latest","Latest reports"],["week","This week\'s meetings"],["archived","Archived"]', FILES_JS)
        self.assertIn('name="fsView"', FILES_JS)
        self.assertIn("<legend>View</legend>", FILES_JS)

    def test_choosing_a_view_clears_the_folder(self):
        i = FILES_JS.index('name==="fsView"')
        handler = FILES_JS[i:FILES_JS.index("\n", i)]
        self.assertIn('shared.FSEL={p:"All",f:"All",sub:"",quick:e.target.value}', handler)
        self.assertIn("renderFiles()", handler)

    def test_a_view_counts_in_filter_and_has_a_chip_to_remove(self):
        self.assertIn('(shared.FSEL.quick!=="all"?1:0)', FILES_JS)
        self.assertIn('[["view",', FILES_JS)
        self.assertIn('if(k==="view") shared.FSEL={...shared.FSEL,quick:"all"}', FILES_JS)

    def test_clear_returns_to_all_files(self):
        self.assertIn('shared.FSEL={...shared.FSEL,quick:"all"}; fmDraw()', FILES_JS)


class WorkWordsKept(unittest.TestCase):
    def test_no_glyphs_before_the_title(self):
        self.assertNotIn("peekMarkHtml({st})", WORK_JS)
        self.assertNotIn("peekMarkHtml({pr})", WORK_JS)
        self.assertNotRegex(CSS, r"#workTbl td\.title \.wkm svg")

    def test_status_and_priority_words_stay_for_screen_readers(self):
        m = re.search(r"export function wkMarksHtml\(t,x\)\{(.*?)\n(?=export )", WORK_JS, re.S)
        self.assertTrue(m)
        body = m.group(1)
        self.assertIn('<span class="vh">', body)
        self.assertIn("${esc(st)}", body)
        self.assertIn("priority", body)
        self.assertNotIn("<svg", body)

    def test_the_wrapper_takes_no_room(self):
        self.assertIn("#workTbl td.title .wkm{display:contents}", CSS)


class PeopleFit(unittest.TestCase):
    def test_minimum_widths_leave_room_for_the_wider_heading(self):
        """The "Risks and issues" heading is a word wider than "RAID"; the People column minimums were trimmed (Name 100, Organisation 104,
        Role 84 at 900 px) so the table fits its box on a wide fallback font. Project stays 90 (about nine letters)."""
        self.assertIn("[data-col=org]{min-width:104px}", CSS)
        self.assertIn("[data-col=role]{min-width:84px}", CSS)
        self.assertIn("[data-col=proj]{min-width:90px}", CSS)
        self.assertIn("#v-people #peopleTbl td.title{min-width:100px}", CSS)


class AudienceSwitch(unittest.TestCase):
    def test_quieter_than_the_view_switch(self):
        self.assertIn('class="mv-seg aud" role="group" aria-label="Audience"', (DASH / "src" / "milestones.js").read_text(encoding="utf-8"))
        small = rule(CSS, ".mv-seg.aud button{")
        self.assertIn("height:var(--ctl-h-sm)", small)       # 26 px, above the 24 px target floor
        pressed = rule(CSS, '.mv-seg.aud button[aria-pressed="true"]')
        self.assertIn("background:var(--accent-soft)", pressed)    # a soft fill, not the dark one of the view switch
        self.assertNotIn("background:var(--ink)", pressed)


class NoSideTabs(unittest.TestCase):
    def test_no_thick_one_sided_borders_are_left(self):
        left = re.findall(r"border-left:\s*(\d+)px\s+solid", CSS)
        thick = [n for n in left if int(n) >= 3]
        self.assertEqual(thick, ["3"], "only the A4 preview's quote may keep a 3 px edge")

    def test_inset_side_bars_are_gone(self):
        bars = re.findall(r"box-shadow:inset (\d+)px 0 0", CSS)
        self.assertEqual([n for n in bars if int(n) >= 2], ["3"], "only the column drop marker may keep a side bar")

    def test_the_three_icons_exist(self):
        for name in ("--ic-info", "--ic-alert", "--ic-quote"):
            self.assertIn(name + ":url(", CSS)


class ReviewAndSettings(unittest.TestCase):
    def test_what_changes_line_is_14px(self):
        self.assertIn("font-size:var(--fs-md)", rule(CSS, "#v-intake-review .icchg{"))

    def test_settings_help_card_is_gone(self):
        self.assertNotIn("Help and documentation", SHELL)

    def test_search_ask_button_has_its_label(self):
        self.assertIn("#vsAskBtn .asklab{display:inline}", CSS)


if __name__ == "__main__":
    unittest.main()
