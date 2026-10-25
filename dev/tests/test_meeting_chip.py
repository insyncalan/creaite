"""#328: the match chip in Calendar import (source and built page; no browser).

Run: python3 dev/tests/test_meeting_chip.py
Words, icon and colour all present; not drawn for private or confidential meetings; the learn offer is one line with a button and
is not asked twice; choosing a project files, loads and reads nothing; no VIP word.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "system/templates/dashboard"
rows = (SRC / "src/components/intakeReview/rows.jsx").read_text()
views = (SRC / "src/components/intakeReview/views.jsx").read_text()
acts = (SRC / "src/components/intakeReview/actions.js").read_text()
css = (SRC / "style.css").read_text()
built = (ROOT / "system/templates/dashboard.html").read_text()


class Chip(unittest.TestCase):
    def test_words_icons_and_colours(self):
        for w in ("Matched", "Likely", "Not sure"):
            self.assertIn(f'"{w}"', rows)
        for ic in ("m" + k for k in ("Tick", "Tilde", "Ask")):
            self.assertIn(ic, rows)
            self.assertIn(ic, (SRC / "src/components/intakeReview/icons.js").read_text())
        for lv in ("matched", "likely", "unsure"):
            self.assertIn(f'data-irmatch="{lv}"', css)

    def test_shown_in_list_board_and_two_panes(self):
        self.assertEqual(rows.count("<MatchChip m={m} />"), 1)
        self.assertEqual(views.count("<MatchChip m="), 2)

    def test_hidden_for_private_confidential_and_files(self):
        guard = re.search(r"export function MatchChip.*?\n  const lv", rows, re.S).group(0)
        for w in ("m.private", "m.confidential", 'm.src === "upload"', "!m.level"):
            self.assertIn(w, guard)

    def test_candidates_only_when_unsure_at_most_three_from_server(self):
        self.assertIn('lv === "unsure" && m.cands', rows)

    def test_offer_is_one_line_one_button_asked_once(self):
        self.assertIn("data-irofferyes", rows)
        self.assertIn("offerAsked().includes", acts)
        self.assertIn('"/api/learn"', acts)

    def test_choosing_writes_only_the_series_memory(self):
        body = acts.split("export async function irChooseProject")[1].split("/** Yes to the offer")[0]
        for bad in ("irProcess", "mtgProcessFile", "api(", "uploadInboxFile"):
            self.assertNotIn(bad, body)
        self.assertIn('"prep.series"', body)

    def test_built_page_has_it_and_no_vip(self):
        for w in ("data-irmatch", "irChooseProject", "mchip"):
            self.assertIn(w, built)
        self.assertNotIn("VIP", (rows + acts).replace("VIPs", ""))

    def test_css_uses_tokens_only(self):
        block = css.split("#328 Intake")[1]
        self.assertNotRegex(block, r"#[0-9A-Fa-f]{3,6}\b")


if __name__ == "__main__":
    unittest.main()
