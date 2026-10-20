"""#238 delta (v2.5.3): Your reviews on Activity › Usage, plain code (usage_reviews.py). Fictional notes, fixed dates.

Each note is {date, saw, decided} only: one line each, at most 200 characters, any other field dropped. The CSV quotes every
cell, doubles quotes, shows dates as DD-MM-YYYY and puts an apostrophe before a cell a spreadsheet would read as a formula.

Run: python3 dev/tests/test_usage_reviews.py
"""
import json
import shutil
import sys
import tempfile
import threading
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "system" / "scripts"))
import usage_report  # noqa: E402
import usage_reviews as ur  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="creaite-urev-"))
        self.file = self.root / "system" / "staging" / "usage-reviews.jsonl"

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def lines(self):
        return [json.loads(x) for x in self.file.read_text(encoding="utf-8").splitlines()]


class Clean(Base):
    def test_the_file_is_in_staging_and_named_as_planned(self):
        self.assertEqual(ur.review_file(self.root), self.file)
        self.assertEqual(ur.review_file().name, "usage-reviews.jsonl")
        self.assertEqual(ur.review_file().parent.name, "staging")

    def test_a_note_keeps_only_date_saw_and_decided(self):
        rec, why = ur.clean({"date": "2026-10-12", "saw": "Start load about 21,000 tokens a run", "decided": "Trim the rules file first",
                             "name": "Jane Example", "path": "projects/ABC Example/notes/x.md", "project": "ABC", "html": "<b>x</b>"})
        self.assertIsNone(why)
        self.assertEqual(rec, {"date": "2026-10-12", "saw": "Start load about 21,000 tokens a run", "decided": "Trim the rules file first"})

    def test_each_text_is_one_line(self):
        rec, _ = ur.clean({"date": "2026-10-12", "saw": "first line\nsecond\r\nthird\tfourth   fifth", "decided": "  a \n b  "})
        self.assertEqual(rec["saw"], "first line second third fourth fifth")
        self.assertEqual(rec["decided"], "a b")

    def test_each_text_is_at_most_200_characters(self):
        rec, _ = ur.clean({"date": "2026-10-12", "saw": "x" * 500, "decided": "é" * 201})
        self.assertEqual((len(rec["saw"]), len(rec["decided"])), (200, 200))

    def test_a_text_that_is_not_a_string_is_empty(self):
        rec, _ = ur.clean({"date": "2026-10-12", "saw": {"nested": "Jane Example"}, "decided": "Keep watching"})
        self.assertEqual(rec, {"date": "2026-10-12", "saw": "", "decided": "Keep watching"})

    def test_refusals(self):
        for req, word in ((None, "date"), ([], "date"), ({"saw": "x"}, "date"), ({"date": "12-10-2026", "saw": "x"}, "DD-MM-YYYY"),
                          ({"date": "2026-02-30", "saw": "x"}, "DD-MM-YYYY"), ({"date": "2026-10-12T09:00", "saw": "x"}, "DD-MM-YYYY"),
                          ({"date": "2026-10-12", "saw": " \n ", "decided": ""}, "saw or what you decided")):
            rec, why = ur.clean(req)
            self.assertIsNone(rec, req)
            self.assertIn(word, why, req)


class Store(Base):
    def test_add_appends_one_line_and_answers_with_every_note(self):
        notes, why = ur.add({"date": "2026-10-12", "saw": "Start load about 21,000 tokens", "decided": "Trim the rules file"}, self.root)
        self.assertIsNone(why)
        notes, _ = ur.add({"date": "2026-10-19", "saw": "Cost up 117% on last week", "decided": "", "extra": "dropped"}, self.root)
        self.assertEqual([n["date"] for n in notes], ["2026-10-12", "2026-10-19"])
        self.assertEqual(self.lines()[1], {"date": "2026-10-19", "saw": "Cost up 117% on last week", "decided": ""})
        self.assertEqual(len(self.file.read_text(encoding="utf-8").splitlines()), 2)

    def test_a_refused_note_writes_nothing(self):
        notes, why = ur.add({"date": "nope", "saw": "x"}, self.root)
        self.assertIsNone(notes)
        self.assertTrue(why)
        self.assertFalse(self.file.exists())

    def test_load_skips_broken_lines_and_drops_other_fields(self):
        self.file.parent.mkdir(parents=True)
        self.file.write_text("\n".join([
            "not json", '{"date": "2026-10-12"', "[1,2]", json.dumps({"date": "bad", "saw": "x"}),
            json.dumps({"date": "2026-10-12", "saw": "Line one\nline two", "decided": "y" * 300, "note": "Jane Example", "path": "/Users/x"}),
            json.dumps({"date": "2026-10-13", "saw": "", "decided": ""}),
        ]) + "\n", encoding="utf-8")
        notes = ur.load(self.root)
        self.assertEqual(notes, [{"date": "2026-10-12", "saw": "Line one line two", "decided": "y" * 200}])
        self.assertNotIn("Jane", json.dumps(notes))

    def test_no_file_and_an_unreadable_file_are_empty(self):
        self.assertEqual(ur.load(self.root), [])
        self.file.parent.mkdir(parents=True)
        self.file.write_bytes(b"\xff\xfe\x00 not text")
        self.assertEqual(ur.load(self.root), [])

    def test_json_report_carries_the_notes_and_whether_saving_works(self):
        ur.add({"date": "2026-10-12", "saw": "Start load about 21,000 tokens", "decided": "Trim the rules file"}, self.root)
        got = usage_report.json_report(usage_file=self.root / "none.jsonl", context_file=self.root / "none2.jsonl", reviews_root=self.root)
        self.assertEqual(got["reviews"], [{"date": "2026-10-12", "saw": "Start load about 21,000 tokens", "decided": "Trim the rules file"}])
        self.assertIs(got["reviews_save"], ur.REGISTERED)


class Csv(unittest.TestCase):
    NOTES = [{"date": "2026-10-12", "saw": "Start load about 21,000 tokens", "decided": "Trim the rules file first"},
             {"date": "2026-10-19", "saw": 'He said "too much"', "decided": "Watch, then decide"}]

    def test_header_newest_first_dates_shown_and_crlf(self):
        self.assertEqual(ur.csv_text(self.NOTES),
                         '"Date","What you saw","What you decided"\r\n'
                         '"19-10-2026","He said ""too much""","Watch, then decide"\r\n'
                         '"12-10-2026","Start load about 21,000 tokens","Trim the rules file first"\r\n')

    def test_no_notes_is_the_header_alone(self):
        self.assertEqual(ur.csv_text([]), '"Date","What you saw","What you decided"\r\n')

    def test_quotes_commas_and_newlines_stay_in_their_cell(self):
        self.assertEqual(ur.csv_cell('a "b", c\nd'), '"a ""b"", c\nd"')

    def test_formula_cells_are_neutralised(self):
        for s in ("=HYPERLINK(\"http://example.invalid\")", "+1+1", "-2+3", "@SUM(A1)", "\tx", "\rx"):
            cell = ur.csv_cell(s)
            self.assertTrue(cell.startswith("\"'"), cell)
        self.assertEqual(ur.csv_cell("=1+1"), "\"'=1+1\"")
        self.assertEqual(ur.csv_cell("Cost up 117%"), '"Cost up 117%"')
        self.assertEqual(ur.csv_cell("19-10-2026"), '"19-10-2026"')     # a date cell starts with a digit: unchanged

    def test_a_formula_note_round_trips_through_add_and_csv(self):
        root = Path(tempfile.mkdtemp(prefix="creaite-urev-"))
        try:
            notes, _ = ur.add({"date": "2026-10-19", "saw": "=cmd|' /C calc'!A0", "decided": "@risk"}, root)
            self.assertIn("\"'=cmd|' /C calc'!A0\",\"'@risk\"", ur.csv_text(notes))
        finally:
            shutil.rmtree(root, ignore_errors=True)


class Route(Base):
    """routes(lock): the handler the live server registers. A stand-in handler records what it was sent."""

    class Handler:
        def __init__(self):
            self.sent = []

        def send(self, code, body):
            self.sent.append((code, body))

    def setUp(self):
        super().setUp()
        self._was = ur.REGISTERED
        self._file = ur.review_file
        ur.review_file = lambda root=None: self.file             # the route writes into this test's own folder
        ur.REGISTERED = False

    def tearDown(self):
        ur.review_file = self._file
        ur.REGISTERED = self._was
        super().tearDown()

    def test_registering_marks_saving_as_possible(self):
        table = ur.routes(threading.Lock())
        self.assertEqual(list(table), ["/api/usage/review"])
        self.assertTrue(ur.REGISTERED)

    def test_the_route_saves_and_answers_with_every_note(self):
        lock = threading.Lock()
        route = ur.routes(lock)["/api/usage/review"]
        h = self.Handler()
        route(h, {"date": "2026-10-19", "saw": "Cost up", "decided": "Watch", "who": "Jane Example"})
        self.assertEqual(h.sent, [(200, {"ok": True, "reviews": [{"date": "2026-10-19", "saw": "Cost up", "decided": "Watch"}]})])
        self.assertFalse(lock.locked())
        route(h, {"date": "x"})
        self.assertEqual(h.sent[-1][1]["ok"], False)
        self.assertEqual(len(self.lines()), 1)

    def test_a_busy_lock_saves_nothing(self):
        class Busy:
            def acquire(self, timeout=None):
                return False

            def release(self):
                raise AssertionError("released a lock it never held")
        h = self.Handler()
        ur.routes(Busy())["/api/usage/review"](h, {"date": "2026-10-19", "saw": "x"})
        self.assertTrue(h.sent[0][1]["busy"])
        self.assertFalse(self.file.exists())


if __name__ == "__main__":
    unittest.main()
