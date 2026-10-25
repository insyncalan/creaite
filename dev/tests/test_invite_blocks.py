"""#375 E1, slice S2: `system/scripts/invite_blocks.py` (an invite body as text lines with the block structure kept).

Run: python3 dev/tests/test_invite_blocks.py      (quick tier: plain code, a few seconds)

Pins: the expected lines of every fixture in dev/tests/fixtures/invites/ (27 fictional bodies, each with <name>.json holding
expected_lines, planted_secrets and must_keep); idempotence of to_lines on its own text output (fixtures, a seeded fuzz of 600 bodies,
the decoded-entity case); the output rules; that a label and its value (same cell, next cell, next row, header row and the first cell
of the next row, a definition list, a <br> in a cell) land in ONE block while unrelated blocks are separated by a blank line; dropped
content (script, style, comments, hidden); a markdown table staying together; 1 MB hostile inputs under a 5 second alarm; and mutants
(each cutting rule turned wrong must turn the checks red).
"""
import json
import random
import signal
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "system" / "scripts"))
import invite_blocks as B  # noqa: E402

FIX = HERE / "fixtures" / "invites"


def read(path):
    with open(str(path), encoding="utf-8", newline="") as fh:
        return fh.read()


def fixtures():
    out = {}
    for meta in sorted(FIX.glob("*.json")):
        src = [p for p in FIX.glob(meta.stem + ".*") if p.suffix in (".html", ".txt")]
        assert len(src) == 1, meta
        out[meta.stem] = (read(src[0]), json.loads(meta.read_text(encoding="utf-8")))
    return out


def block_of(lines, needle):
    """Index of the block holding the first line equal to needle (blocks counted in order), or None."""
    idx = 0
    for line in lines:
        if line == "":
            idx += 1
        elif line == needle or needle in line.split(" | "):
            return idx
    return None


def together(lines, a, b):
    ia, ib = block_of(lines, a), block_of(lines, b)
    return ia is not None and ia == ib


def apart(lines, a, b):
    ia, ib = block_of(lines, a), block_of(lines, b)
    return ia is not None and ib is not None and ia != ib


# (fixture, kind, first line, second line)
LAYOUTS = [
    ("label_next_cell", "together", "Meeting ID", "873 555 210"),
    ("label_next_cell", "together", "Passcode", "kT7mW3"),
    ("label_next_cell", "together", "Meeting ID", "kT7mW3"),
    ("header_row_passcode", "together", "Passcode", "Zx81pQ44"),
    ("header_row_passcode", "together", "Other", "See the wiki page"),
    ("label_same_cell_br", "together", "Passcode", "mR4tY81x"),
    ("dialin_table", "together", "PIN", "7745 2210#"),
    ("dialin_table", "together", "Country", "+44 20 7946 0001"),
    ("dialin_table", "together", "Germany", "+49 30 1234 5678"),
    ("dialin_es", "together", "ID de la reunión:", "612 740 118"),
    ("webex", "together", "Meeting password:", "Qw8rTy2z"),
    ("webex", "together", "Meeting number (access code):", "2551 880 1234"),
    ("definition_list", "together", "Passcode", "vB6nM3"),
    ("broken_html", "together", "Passcode", "jH2kL9"),
    ("broken_html", "together", "Dial-in", "+44 20 7946 0909"),
    ("nested_lists", "together", "Scope", "Owner: Mei Tan"),
    ("nested_lists", "together", "Join details", "Code: 3390 2258"),
    ("layout_nested_tables", "together", "Passcode", "8841 0362"),
    ("layout_nested_tables", "together", "Join", "https://rooms.example.org/r/board"),
    ("teams_classic", "together", "Or call in (audio only)", "Phone Conference ID: 482 017 33#"),
    ("markdown_table", "together", "| Passcode | 774120 |", "| Dial-in | +44 20 7946 0555 |"),
    ("markdown_table", "together", "| Demo: billing export | Lena Ortiz |", "| Demo: audit log | Ravi Menon |"),
    ("teams_new", "together", "Meeting ID: 312 445 901 22", "Passcode: aB3dE9"),
    ("zoom_html", "together", "Meeting ID: 998 8776 6554", "Passcode: 551203"),
    ("layout_nested_tables", "apart", "Programme board", "Agenda"),
    ("layout_nested_tables", "apart", "2. Funding", "Join"),
    ("teams_new", "apart", "Agenda for the budget review", "Meeting ID: 312 445 901 22"),
    ("teams_new", "apart", "Please read the finance pack before we meet.", "Passcode: aB3dE9"),
    ("teams_classic", "apart", "Weekly delivery sync. Topics: milestones, vendor update.", "Video ID: 117 604 118 3"),
    ("outlook_footer", "apart", "Supplier QBR. Agenda attached.", "Please confirm attendance."),
    ("nested_lists", "apart", "Release readiness check.", "Scope"),
    ("nested_lists", "apart", "Code: 3390 2258", "Open actions"),
    ("dialin_table", "apart", "Thank you for joining.", "PIN"),
    ("blockquote_reply", "apart", "Moving this to Thursday; same agenda as below.", "Passcode: pQ92xD"),
    ("zoom_text", "apart", "Quarterly planning workshop - please bring your team goals.", "Meeting ID: 812 3456 7890"),
]


def all_failures():
    """Every check that depends on the cutting rules, as a list of failure strings (empty = all pass). The mutants run this."""
    bad = []
    fx = fixtures()
    for name, (body, meta) in fx.items():
        lines = B.to_lines(body)
        if lines != meta["expected_lines"]:
            bad.append("expected " + name)
        if B.to_lines("\n".join(lines)) != lines:
            bad.append("idempotent " + name)
    for name, kind, a, b in LAYOUTS:
        lines = B.to_lines(fx[name][0])
        if not (together if kind == "together" else apart)(lines, a, b):
            bad.append("%s %s: %r / %r" % (kind, name, a, b))
    return bad


class Fixtures(unittest.TestCase):
    def test_enough_fixtures(self):
        fx = fixtures()
        self.assertGreaterEqual(len(fx), 24)
        for name, (_body, meta) in fx.items():
            self.assertEqual(set(meta), {"expected_lines", "planted_secrets", "must_keep"}, name)
            self.assertTrue(meta["planted_secrets"], name)
            self.assertTrue(meta["must_keep"], name)
        kinds = " ".join(fx)
        for provider in ("teams_new", "teams_classic", "zoom", "webex", "google_meet", "dialin_table", "header_row_passcode",
                         "nested_lists", "blockquote", "markdown_table", "accents"):
            self.assertIn(provider, kinds)

    def test_expected_lines(self):
        for name, (body, meta) in fixtures().items():
            with self.subTest(name):
                self.assertEqual(B.to_lines(body), meta["expected_lines"])

    def test_must_keep_lines_are_in_the_lines(self):
        for name, (body, meta) in fixtures().items():
            lines = B.to_lines(body)
            for keep in meta["must_keep"]:
                with self.subTest(name=name, line=keep):
                    self.assertIsNotNone(block_of(lines, keep), lines)

    def test_hidden_and_script_secrets_are_dropped_here(self):
        # everything else planted is for the filter (invite_filter) to remove; only markup and hidden content go in to_lines
        gone = {"entities_and_hidden": ("4455667788", "5566778899"), "outlook_footer": ("99887766",), "broken_html": ("1234567890",)}
        fx = fixtures()
        for name, secrets in gone.items():
            text = "\n".join(B.to_lines(fx[name][0]))
            for secret in secrets:
                self.assertIn(secret, fx[name][0])
                self.assertNotIn(secret, text, name)


class Layouts(unittest.TestCase):
    def test_label_value_togetherness_and_separation(self):
        fx = fixtures()
        for name, kind, a, b in LAYOUTS:
            lines = B.to_lines(fx[name][0])
            with self.subTest(name=name, kind=kind, a=a, b=b):
                self.assertIsNotNone(block_of(lines, a), lines)
                self.assertIsNotNone(block_of(lines, b), lines)
                self.assertTrue((together if kind == "together" else apart)(lines, a, b), lines)

    def test_every_row_of_a_data_table_is_one_line(self):
        lines = B.to_lines("<table><tr><td>a</td><td>b</td></tr><tr><td>c</td><td>d</td></tr><tr><td>e</td><td>f</td></tr></table>")
        self.assertEqual(lines, ["a | b", "c | d", "e | f"])

    def test_layout_table_is_cut_per_cell(self):
        lines = B.to_lines("<table><tr><td><p>one</p><p>two</p></td><td>three</td></tr></table>")
        self.assertEqual(lines, ["one", "", "two", "", "three"])

    def test_nested_table_makes_the_outer_a_layout_table(self):
        lines = B.to_lines("<table><tr><td>x</td><td><table><tr><td>y</td><td>z</td></tr></table></td></tr></table>")
        self.assertEqual(lines, ["x", "", "y | z"])

    def test_single_cell_table_is_layout(self):
        self.assertEqual(B.to_lines("<table><tr><td><p>a</p><p>b</p></td></tr></table>"), ["a", "", "b"])

    def test_br_run_ends_the_block_single_br_does_not(self):
        self.assertEqual(B.to_lines("<div>a<br>b<br><br>c</div>"), ["a", "b", "", "c"])
        self.assertEqual(B.to_lines("<div>a<br><br><br><br>b</div>"), ["a", "", "b"])

    def test_paragraphs_headings_quotes_are_blocks_divs_and_items_are_lines(self):
        self.assertEqual(B.to_lines("<h2>H</h2><p>p1</p><p>p2</p>"), ["H", "", "p1", "", "p2"])
        self.assertEqual(B.to_lines("<div>d1</div><div>d2</div>"), ["d1", "d2"])
        self.assertEqual(B.to_lines("<blockquote>q</blockquote>after"), ["q", "", "after"])
        self.assertEqual(B.to_lines("<ul><li>i1<ul><li>i2</li></ul></li><li>i3</li></ul>"), ["i1", "i2", "i3"])

    def test_hr_is_a_divider_line(self):
        self.assertEqual(B.to_lines("a<hr>b"), ["a", "", B.DIVIDER, "", "b"])

    def test_markdown_table_stays_together_and_blank_runs_collapse(self):
        lines = B.to_lines("| a | b |\n|---|---|\n| 1 | 2 |\n\n\n\n| x | y |\n")
        self.assertEqual(lines, ["| a | b |", "|---|---|", "| 1 | 2 |", "", "| x | y |"])

    def test_inline_tags_do_not_split_words(self):
        self.assertEqual(B.to_lines("<p>Pass<b>code</b>: <span>12</span><span>34</span></p>"), ["Passcode: 1234"])


class Dropped(unittest.TestCase):
    def test_script_style_comment_head_hidden_are_gone(self):
        html = ("<html><head><title>T</title><style>p{x:y}</style></head><body><!-- c --><script>var s='SECRET1';</script>"
                "<p>keep</p><div style='display:none'>H1</div><span hidden>H2</span><p style=\"mso-hide:all\">H3</p>"
                "<div style=\"Visibility : Hidden\">H4</div></body></html>")
        self.assertEqual(B.to_lines(html), ["keep"])

    def test_unclosed_script_swallows_the_rest(self):
        self.assertEqual(B.to_lines("<p>a</p><script>never closed <p>b</p>"), ["a"])

    def test_entities_are_decoded_and_control_characters_go(self):
        lines = B.to_lines("<p>A&amp;B&nbsp;&nbsp;C&#x41;\x01\x07 D\ttab</p>")
        self.assertEqual(lines, ["A&B CA D tab"])


class Rules(unittest.TestCase):
    def check_rules(self, lines):
        self.assertTrue(not lines or (lines[0] != "" and lines[-1] != ""))
        for i, line in enumerate(lines):
            self.assertEqual(line, line.strip())
            self.assertNotIn("\n", line)
            self.assertFalse(any(ord(c) < 32 or ord(c) == 127 for c in line), repr(line))
            if line == "":
                self.assertNotEqual(lines[i - 1], "")

    def test_output_rules_on_fixtures_and_fuzz(self):
        for _name, (body, _meta) in fixtures().items():
            self.check_rules(B.to_lines(body))
        for body in fuzz_bodies(300, 11):
            self.check_rules(B.to_lines(body))

    def test_empty_and_odd_inputs(self):
        for value in ("", None, "   \n\n  ", "<p></p>", "<>", "<", "a < b", 12, b"x"):
            self.assertIsInstance(B.to_lines(value), list)
        self.assertEqual(B.to_lines(""), [])
        self.assertEqual(B.to_lines("   \n\n  "), [])
        self.assertEqual(B.to_lines("a < b and c > d"), ["a < b and c > d"])
        self.assertEqual(B.to_lines("<me@example.org> wrote:"), ["<me@example.org> wrote:"])

    def test_looks_like_html(self):
        for yes in ("<p>x</p>", "<DIV>", "x<br/>y", "<!-- c -->", "<!DOCTYPE html>", "<table><tr><td>", "<o:p></o:p>"):
            self.assertTrue(B.looks_like_html(yes), yes)
        for no in ("", "plain text", "a < b", "<me@example.org>", "1 <2 and 3> 0", "<notatag>", "| a | b |"):
            self.assertFalse(B.looks_like_html(no), no)

    def test_decoded_entity_is_not_html_on_a_second_pass(self):
        lines = B.to_lines("<p>&lt;div&gt;Passcode: 1&lt;/div&gt;</p>")
        self.assertFalse(B.looks_like_html("\n".join(lines)))
        self.assertEqual(B.to_lines("\n".join(lines)), lines)

    def test_plain_text_passes_through_line_by_line(self):
        self.assertEqual(B.to_lines("a\r\n b \r\n\r\n\r\n\t\r\nc\x0bd"), ["a", "b", "", "c", "d"])

    def test_blocks_helper(self):
        self.assertEqual(B.blocks("<div>a</div><div>b</div><p>c</p>"), [["a", "b"], ["c"]])
        self.assertEqual(B.blocks(""), [])


def fuzz_bodies(n, seed):
    rnd = random.Random(seed)
    tags = ["p", "div", "table", "tr", "td", "th", "ul", "ol", "li", "br", "span", "b", "blockquote", "h2", "pre", "hr", "script",
            "style", "o:p", "x-unknown", "a href='https://example.org/x'", "font"]
    words = ["Passcode", "4417 8812", "agenda", "&amp;", "&lt;p&gt;", "&nbsp;", "+44 20 7946 0000", "ok", "<", ">", "\n", "Café", "​"]
    out = []
    for _ in range(n):
        parts = []
        for _ in range(rnd.randint(1, 40)):
            r = rnd.random()
            tag = rnd.choice(tags)
            if r < 0.35:
                parts.append("<%s>" % tag)
            elif r < 0.6:
                parts.append("</%s>" % tag.split()[0])
            else:
                parts.append(rnd.choice(words))
        out.append("".join(parts))
    return out


class Idempotence(unittest.TestCase):
    def test_fixtures(self):
        for name, (body, _meta) in fixtures().items():
            lines = B.to_lines(body)
            with self.subTest(name):
                self.assertEqual(B.to_lines("\n".join(lines)), lines)

    def test_fuzz(self):
        for body in fuzz_bodies(600, 375):
            lines = B.to_lines(body)
            self.assertEqual(B.to_lines("\n".join(lines)), lines, body)

    def test_deterministic(self):
        for body in fuzz_bodies(100, 5):
            self.assertEqual(B.to_lines(body), B.to_lines(body))


ALARM = 5


def timed(fn, *args):
    def stop(*_a):
        raise TimeoutError("took more than %s s" % ALARM)
    old = signal.signal(signal.SIGALRM, stop)
    signal.setitimer(signal.ITIMER_REAL, ALARM)
    t0 = time.time()
    try:
        out = fn(*args)
        return time.time() - t0, out
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


MB = 1000000


def hostile():
    unit = lambda s: (s * (MB // len(s) + 1))[:MB]  # noqa: E731
    yield "paragraphs", unit("<p>Passcode: 4417 8812 and some more words here</p>")
    yield "table cells", "<table>" + unit("<tr><td>a</td><td>b</td></tr>") + "</table>"
    yield "nested divs", unit("<div>") + "x"
    yield "nested tables", unit("<table><tr><td>")
    yield "nested lists", unit("<ul><li>")
    yield "unclosed lt", unit("<")
    yield "unclosed tag", unit("<a ")
    yield "unclosed comment", unit("<!-- ")
    yield "unclosed attribute", "<a href='" + unit("x ")
    yield "many br", unit("<br>")
    yield "many entities", unit("&amp;&#x41;&nbsp;&bogus;")
    yield "one long line", unit("word ")
    yield "plain lines", unit("Passcode: 4417 8812\n")
    yield "blank lines", unit("\n \n")
    yield "markers", unit("</p></div></td></tr></table>")
    yield "implied closes", unit("<p><li><td><tr>")
    yield "script", "<script>" + unit("<p>x</p>")
    yield "hidden", unit("<div style='display:none'>x</div>")


class Timing(unittest.TestCase):
    def test_one_megabyte_inputs(self):
        for name, body in hostile():
            with self.subTest(name):
                took, lines = timed(B.to_lines, body)
                self.assertIsInstance(lines, list)
                self.assertLess(took, ALARM, name)

    def test_two_megabytes_are_cut_not_slower(self):
        body = "<p>word </p>" * 400000
        took, lines = timed(B.to_lines, body)
        self.assertLess(took, ALARM)

    def test_linear_growth(self):
        unit = "<table><tr><td>Passcode</td><td>4417</td></tr></table><p>text</p><ul><li>a<li>b</ul>"
        small = min(timed(B.to_lines, unit * 800)[0] for _ in range(3))
        big = min(timed(B.to_lines, unit * 8000)[0] for _ in range(3))
        self.assertLess(big, max(small, 0.01) * 40)


class Mutants(unittest.TestCase):
    def test_unmutated_is_clean(self):
        self.assertEqual(all_failures(), [])

    def red(self, label, *patches):
        for p in patches:
            p.start()
        try:
            bad = all_failures()
        finally:
            mock.patch.stopall()
        self.assertTrue(bad, "mutant %s stayed green" % label)

    def test_m1_every_table_is_layout(self):
        self.red("m1", mock.patch.object(B, "_is_layout", lambda t: True))

    def test_m2_no_table_is_layout(self):
        self.red("m2", mock.patch.object(B, "_is_layout", lambda t: False))

    def test_m3_rows_are_cut(self):
        orig = B._render_row

        def cut(row, em):
            orig(row, em)
            em.line_break()
            em.want_blank = True
        self.red("m3", mock.patch.object(B, "_render_row", cut))

    def test_m4_cells_are_cut(self):
        def cut(row, em):
            for cell in row.kids:
                if not isinstance(cell, str) and cell.tag in B.CELLS:
                    for x in B._cell_lines(cell):
                        em.line_break()
                        em.text(x)
                        em.line_break()
                    em.want_blank = True
        self.red("m4", mock.patch.object(B, "_render_row", cut))

    def test_m5_blocks_are_never_cut(self):
        self.red("m5", mock.patch.object(B._Emit, "block_break", B._Emit.line_break))

    def test_m6_br_is_ignored(self):
        self.red("m6", mock.patch.object(B._Emit, "br", lambda self: None))

    def test_m7_lists_cut_nested_items(self):
        self.red("m7", mock.patch.object(B, "LISTS", frozenset()))

    def test_m8_tags_not_neutralised(self):
        self.red("m8", mock.patch.object(B, "_neutralise", lambda line: line))

    def test_m9_hidden_not_dropped(self):
        self.red("m9", mock.patch.object(B, "_is_hidden", lambda attrs: False))

    def test_m10_script_not_dropped(self):
        self.red("m10", mock.patch.object(B, "DROP", frozenset()))

    def test_m11_divs_are_blocks(self):
        # a div that cuts a block breaks the "same block" layouts built from divs
        orig = B._render

        def render(node, em):
            if node.tag == "div":
                em.block_break()
                B._render_kids(node, em)
                em.block_break()
            else:
                orig(node, em)
        self.red("m11", mock.patch.object(B, "_render", render))

    def test_m12_no_blank_collapse(self):
        self.red("m12", mock.patch.object(B, "_plain_lines", lambda text: text.split("\n")))


if __name__ == "__main__":
    unittest.main()
