"""The Current state pane marker inside another HTML comment is text, not a split (Alan, 13-10-2026).

Run: python3 dev/tests/test_pane_marker.py   (the page test needs Google Chrome; it is skipped otherwise)

The project template's guidance comment quotes the marker `<!-- creaite: second pane -->`, so the splitters cut every new
project's Current state through that comment. Only a marker outside every comment splits the panes now, in both splitters:
docx_tools.pane_markers (the Word reports, Generate, approval) and paneMarkers in the dashboard's panel.js.
"""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "system" / "scripts"))
import docx_tools as dt  # noqa: E402
import report  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402

MARKER = dt.PANE_MARKER
TEMPLATE = (ROOT / "system/templates/project-CLAUDE-template.md").read_text(encoding="utf-8")
GUIDE = report.saved_current(TEMPLATE)          # the template's Current state as saved: its guidance comment

# (text, (left, right)): the same table drives the Python and the page checks
CASES = [
    ("Only left.", ("Only left.", "")),
    (f"Left.\n\n{MARKER}\n\nRight.", ("Left.", "Right.")),
    (f"Left.\n\n{MARKER}\n\nRight.\n\n{MARKER}\n\nMore", ("Left.", "Right.\n\nMore")),
    (GUIDE, (GUIDE, "")),                                                                     # the template: one pane, whole
    (f"{GUIDE}\n\nMy left.\n\n{MARKER}\n\nMy right.", (f"{GUIDE}\n\nMy left.", "My right.")),   # and a real marker after it
    (f"<!-- a note\n{MARKER}\n-->\n\nLeft.", (f"<!-- a note\n{MARKER}\n-->\n\nLeft.", "")),     # a quoted marker on its own line
    (f"Left. <!-- see `{MARKER}` -->\n\n{MARKER}\n\nRight <!-- `{MARKER}` -->.",
     (f"Left. <!-- see `{MARKER}` -->", f"Right <!-- `{MARKER}` -->.")),                     # a quoted one in the right pane stays
    (f"Left -->\n\n{MARKER}\n\nRight.", ("Left -->", "Right.")),                               # a stray close doesn't hide a marker
]


class PythonSplitter(unittest.TestCase):
    def test_a_marker_inside_another_comment_is_ignored(self):
        self.assertEqual(dt.pane_markers(GUIDE), [])
        self.assertIn(MARKER, GUIDE)                                                             # the template does quote it
        self.assertEqual(dt.split_panes(GUIDE), (GUIDE, ""))
        self.assertEqual(dt.one_message(GUIDE), GUIDE)

    def test_the_table(self):
        for text, want in CASES:
            with self.subTest(text=text[:40]):
                self.assertEqual(dt.split_panes(text), want)

    def test_a_normal_marker_still_splits(self):
        self.assertEqual(dt.pane_markers(f"A\n\n{MARKER}\n\nB"), [3])
        self.assertEqual(dt.pane_lines(f"A\n\n{MARKER}\n\nB"), {2})

    def test_split_then_join_is_byte_identical(self):
        texts = [f"Left.\n\n{MARKER}\n\nRight.", f"{MARKER}\n\nRight only.", "Left only.", GUIDE,
                 f"{GUIDE}\n\nMy left.\n\n{MARKER}\n\nMy right.", "### Head\n\n- a\n  - b\n\n> quote\n\n![x](images/x.png)",
                 f"Left. <!-- see `{MARKER}` -->\n\n{MARKER}\n\nRight <!-- `{MARKER}` -->."]
        for t in texts:
            with self.subTest(text=t[:40]):
                self.assertEqual(dt.join_panes(*dt.split_panes(t)), t)
                self.assertEqual(dt.md_normalise(t), t)                                         # canonical texts stay as they are

    def test_readers_keep_a_quoted_marker_as_text(self):
        kinds = [k for k, _ in dt.md_blocks(f"<!-- a note\n{MARKER}\n-->\n\nLeft.", panes=True)]
        self.assertNotIn("pane", kinds)
        self.assertEqual([k for k, _ in dt.md_blocks(f"A\n{MARKER}\nB", panes=True)], ["p", "pane", "p"])
        quoted = f"<!-- a note\n{MARKER}\n-->"
        self.assertEqual(dt.md_normalise(quoted), f"<!-- a note {MARKER} -->")                # a paragraph, never popped as a marker
        entries = report.current_entries(Path("."), f"<!-- a note\n{MARKER}\n-->\n\nLeft.")
        self.assertEqual(len(entries), 1)
        self.assertIn(MARKER, entries[0]["md"])                                                  # the Word report keeps the comment whole

    def test_a_template_section_keeps_its_comment_when_a_report_rewrites_it(self):
        out = report.replace_current(TEMPLATE, "Things are fine.")
        self.assertIn("Things are fine.", out)
        self.assertEqual(out.count(MARKER), 0)                                                   # no right pane is invented from the comment

    def test_a_text_with_only_a_quoted_marker_keeps_the_right_pane(self):
        md = f"# X\n\n## Current state\n\nOld.\n\n{MARKER}\n\nMy notes.\n\n## Next\n"
        out = report.replace_current(md, f"New <!-- `{MARKER}` -->.")
        self.assertIn("My notes.", out)


class PageSplitter(LiveBrowserCase):
    """The dashboard's splitter agrees with docx_tools on every case, and a new project's Current state is one pane."""

    shared_server = True

    @classmethod
    def load(cls, v):
        populate(v)
        mem = next((v.root / "projects").glob("ABC */CLAUDE.md"))
        text = mem.read_text()
        head = text[:text.index("## Current state")]
        mem.write_text(head + "## Current state\n\n" + TEMPLATE.split("## Current state\n", 1)[1].split("\n## ", 1)[0].strip() + "\n")
        v.run(script="build_dashboard.py")

    def test_the_page_splits_exactly_as_python_does(self):
        got = self.b.eval(f"{json.dumps([t for t, _ in CASES])}.map(t=>CREAITE.splitPanes(t))")
        self.assertEqual([tuple(x) for x in got], [w for _, w in CASES])
        js = self.b.eval(f"{json.dumps([t for t, _ in CASES])}.map(t=>CREAITE.paneMarkers(t))")
        self.assertEqual(js, [dt.pane_markers(t) for t, _ in CASES])
        one = [t for t, _ in CASES if len(dt.pane_markers(t)) <= 1]                              # one real marker or none
        rt = self.b.eval(f"{json.dumps(one)}.map(t=>CREAITE.joinPanes(...CREAITE.splitPanes(t))===t)")
        self.assertEqual(len(one), len(CASES) - 1)
        self.assertTrue(all(rt))
        kinds = self.b.eval(f"CREAITE.mdBlocks({json.dumps(chr(10).join(['<!-- a note', MARKER, '-->']))}).map(b=>b[0])")
        self.assertEqual(kinds, ["p"])

    def test_a_template_current_state_is_one_pane(self):
        b = self.b
        b.eval("go('cockpit','ABC')")
        b.wait("document.querySelector('#v-cockpit .curcard')")
        cur = b.eval("P.find(p=>p.code==='ABC').current")
        self.assertIn(MARKER, cur)                                                                # the guidance, marker quoted inside
        self.assertEqual(b.eval("CREAITE.splitPanes(P.find(p=>p.code==='ABC').current)[1]"), "")
        self.assertEqual(b.eval("document.querySelectorAll('.curpanes.solo').length"), 1)          # no right pane
        self.assertFalse(re.search(r"^`?\s*is the left pane", b.eval("document.querySelector('.curpane[data-pane=\"2\"]').textContent").strip()))


if __name__ == "__main__":
    unittest.main()
