"""H5 / #218: the one editor's gate for the text section's profile (the Notes profile on a report).

Run: python3 dev/tests/test_report_text_section_gate.py   (the browser layers need Google Chrome; skipped otherwise)

A report's text section is the one editor with `features: "notes"` and the Notes writer (headings `#` to `###`, no head shift), its own
chrome profile `textsection`. Three layers:
  * the profile: its bar is Notes' bar tool for tool, its `/` menu has Notes' blocks and none of the pickers a report can't host
    (note, person, work item, the templates), and the sheet gives the editor `features: "notes"` with no head shift;
  * the round-trip gate (dev/tools/tiptap_roundtrip.py) on the cases written for it (dev/tiptap/hard-cases.json and stable-cases.json,
    names ending (#218)/(#218) ...), on the vendored module: a text using every element comes back byte for byte, and the same
    elements made by the bar's own commands are written the same way twice more;
  * the same text through the dashboard's own wrapper (`creaiteEditor`, in the built page): given back unchanged as it came, and,
    once touched and put back, written by the exact writer to the same bytes.
If it fails, a report's text section may not use the editor (and the sheet must go back to plain Markdown text) until it passes.
"""
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(REPO / "dev" / "tools"))
import cdp  # noqa: E402
import tiptap  # noqa: E402
import tiptap_roundtrip as gate  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_report_text_section_ui import RICH  # noqa: E402

SRC = REPO / "system" / "templates" / "dashboard" / "src"
PROFILES = (SRC / "core" / "editorProfiles.js").read_text(encoding="utf-8")
SHEETTEXT = (SRC / "components" / "report" / "SheetText.jsx").read_text(encoding="utf-8")


def line_of(profile):
    """The `tools: [...]` line of an ED_PROFILES entry."""
    m = re.search(rf"^  {profile}: \{{ tip: \"[^\n]*\",\n\s+tools: (\[[^\]]*\])", PROFILES, re.M)
    assert m, profile
    return m.group(1)


class Profile(unittest.TestCase):
    def test_the_bar_is_notes_bar_tool_for_tool(self):
        self.assertEqual(line_of("textsection"), line_of("notes"))

    def test_the_slash_menu_has_notes_blocks_and_none_of_the_pickers_or_templates(self):
        m = re.search(r"^  textsection: (\[[^\]]*\])", PROFILES, re.M)
        rows = re.findall(r'"([^"]+)"', m.group(1))
        notes = re.findall(r'"([^"]+)"', re.search(r"^  notes: (\[[^\]]*\])", PROFILES, re.M | re.S).group(1))
        for want in ("text", "h1", "h2", "h3", "ul", "ol", "task", "quote", "codeblock", "table", "image", "link"):
            self.assertIn(want, rows)
        for never in ("item", "person", "note") + tuple(r for r in notes if r.startswith("tpl:")):
            self.assertNotIn(never, rows)
        self.assertTrue(set(rows) <= set(notes), "nothing a report's menu has is missing from Notes'")

    def test_the_sheet_gives_a_text_section_the_notes_feature_set_and_no_head_shift(self):
        m = re.search(r"creaiteEditor\(el, text \? \{([^}]*)\}", SHEETTEXT)
        self.assertIsNotNone(m)
        self.assertIn('features: "notes"', m.group(1))
        self.assertNotIn("headShift", m.group(1))


@unittest.skipUnless(cdp.chrome_path(), "needs Google Chrome")
class Gate(unittest.TestCase):
    def test_the_cases_written_for_the_text_section_round_trip_on_the_vendored_module(self):
        cases = [c for c in gate.corpus(("hard", "stable")) if "#218" in c.source or "(#218)" in c.source or "text section" in c.source]
        self.assertGreaterEqual(len(cases), 2, [c.source for c in cases])
        self.assertEqual({c.group for c in cases}, {"hard", "stable"})
        results = gate.run(cases, gate.vendored_js(), "exact", tiptap.PINNED)
        lines, failed = gate.report(results)
        self.assertEqual(failed, 0, "\n".join(x for x in lines if not x.startswith("PASS")))


class Wrapper(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        populate(v)

    def test_a_text_section_text_is_given_back_as_it_came_and_written_to_the_same_bytes_once_touched(self):
        b = self.b
        out = b.eval("""(md => { const el = document.createElement('div'); document.body.appendChild(el);
          const h = creaiteEditor(el, {features: 'notes', markdown: md}); const same = h.value();
          const ed = h.editor, v = ed.view; let p = null; ed.state.doc.descendants((n, pos) => { if (p === null && n.isText) p = pos; });
          v.dispatch(v.state.tr.insertText('x', p)); v.dispatch(v.state.tr.delete(p, p + 1));
          const r = {same, touched: h.touched(), written: h.value()}; h.destroy(); el.remove(); return r; })(%s)""" % __import__("json").dumps(RICH.rstrip("\n")))
        self.assertEqual(out["same"], RICH.rstrip("\n"))
        self.assertTrue(out["touched"])
        self.assertEqual(out["written"], RICH.rstrip("\n"), "the exact writer writes the text it was given")


if __name__ == "__main__":
    unittest.main()
