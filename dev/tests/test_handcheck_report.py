"""#212: dev/tools/handcheck_report.py, the reading and summary half of `handcheck.py all`. No browser, no vault: sheets and
test modules are small texts in a throwaway folder.

Run: python3 dev/tests/test_handcheck_report.py   (quick tier)
"""
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tools"))
import handcheck_report as hr  # noqa: E402

SHEET = """# Hand checks for creaite 2.9.0

## Setup

1. Not a check: a setup step.

## Checks

### Group

1. First check.
   - Test: `test_x.py::test_a`; scriptable.
2. Second check, only a person can say.
   - Test: no test found; judgement.
3. Third check, needs the real Claude.
   - The wording is **live only**.
4. Fourth check with nothing said about it.
   - Test: no test found.
5. Fifth check, tested and also judgement.
   - judgement.

## v2.9.1 (patch)

6. A patch check.
   - Test: no test found.

## Results

| # | Check | Pass | Fail | Notes |
| 1 | First | [ ] | [ ] | |
"""

MODULE = '''
from hcbase import phase2

class A:
    def test_c01_first(self): pass
    def test_c05_fifth(self): pass
    @phase2()
    def test_c04_later(self): pass
    def test_c07_not_in_the_sheet(self): pass

class B:
    def test_c01_again(self): pass
'''


class Releases(unittest.TestCase):
    def test_names_and_order(self):
        self.assertEqual(hr.module_release("test_v232"), "v2.3.2")
        self.assertEqual(hr.module_release("test_v195"), "v1.9.5")
        self.assertIsNone(hr.module_release("test_v2x"))
        self.assertEqual(hr.module_name("2.3.2"), "test_v232")
        self.assertLess(hr.vkey("v2.3.4"), hr.vkey("v2.10.0"))

    def test_discovery_and_selection(self):
        with tempfile.TemporaryDirectory() as d:
            for n in ("test_v220", "test_v2310", "test_v232", "test_v195", "hcbase", "sheet"):
                (Path(d) / f"{n}.py").write_text("")
            avail = hr.releases(d)
            self.assertEqual(avail, ["v1.9.5", "v2.2.0", "v2.3.2", "v2.3.10"])
            self.assertEqual(hr.select(avail, "v2.2.0", "v2.3.2"), ["v2.2.0", "v2.3.2"])
            self.assertEqual(hr.select(avail, "v2.3.0"), ["v2.3.2", "v2.3.10"])
            self.assertEqual(hr.select(avail, "v2.2.0", None, {"v2.3.2": None}), ["v2.3.2"])

    def test_only(self):
        avail = ["v2.3.2", "v2.3.3"]
        self.assertEqual(hr.parse_only("v2.3.2,2.3.3:1+2", avail), ({"v2.3.2": None, "v2.3.3": {1, 2}}, None))
        self.assertIsNotNone(hr.parse_only("1,2", avail)[1])          # bare numbers mean nothing across releases
        self.assertIsNotNone(hr.parse_only("v9.9.9", avail)[1])
        self.assertEqual(hr.parse_only("", avail), ({}, None))


class Sheets(unittest.TestCase):
    def test_checks_by_release_and_other_sections_skipped(self):
        got = hr.parse_sheet(SHEET, "v2.9.0")
        self.assertEqual(sorted(got), ["v2.9.0", "v2.9.1"])
        self.assertEqual(sorted(got["v2.9.0"]), [1, 2, 3, 4, 5])      # the Setup list and the Results table are not checks
        self.assertEqual(sorted(got["v2.9.1"]), [6])
        self.assertIn("scriptable", got["v2.9.0"][1])

    def test_tags(self):
        got = hr.parse_sheet(SHEET, "v2.9.0")["v2.9.0"]
        self.assertEqual(hr.tag_of(got[1]), None)
        self.assertEqual(hr.tag_of(got[2]), "judgement")
        self.assertEqual(hr.tag_of(got[3]), "live")
        self.assertEqual(hr.tag_of(got[4]), None)

    def test_missing_sheet_is_none_and_a_patch_is_found_in_the_dot_zero_sheet(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(hr.sheet_checks("v2.9.0", sheets=d), (None, None))
            (Path(d) / "v2.9.0.md").write_text(SHEET)
            checks, src = hr.sheet_checks("v2.9.1", sheets=d)
            self.assertEqual(sorted(checks), [6])
            self.assertTrue(src.endswith("v2.9.0.md"))


class Coverage(unittest.TestCase):
    def test_gaps_are_untested_and_untagged(self):
        with tempfile.TemporaryDirectory() as d:
            m = Path(d) / "test_v290.py"
            m.write_text(MODULE)
            tests = hr.scan_tests(m)
        self.assertEqual(tests, {1: True, 4: False, 5: True, 7: True})      # 4 is phase 2: it does not run
        sheet = hr.parse_sheet(SHEET, "v2.9.0")["v2.9.0"]
        cov = hr.coverage(sheet, tests)
        self.assertEqual(cov, {"tested": [1, 5], "judgement": [2], "live": [3], "gaps": [4]})
        # the module's own tags count too
        self.assertEqual(hr.coverage(sheet, tests, {4: "live"})["gaps"], [])
        self.assertEqual(hr.module_tags(type("M", (), {"KIND": {1: "judgement", 2: "scriptable"}, "LIVE_ONLY": {3: "why"}})),
                         {1: "judgement", 3: "live"})


class Summary(unittest.TestCase):
    OUT = {1: ("pass", "auto (scriptable): "), 2: ("fail", "auto (scriptable): expected 3 rows, got 2"),
           3: ("judgement", "judgement: on the screenshot sheet"), 4: ("live", "live only: needs Word"), 5: ("skip", "phase 2")}

    def test_counts(self):
        cov = {"tested": [1], "judgement": [7, 8], "live": [9], "gaps": []}
        self.assertEqual(hr.counts_of(self.OUT), {"pass": 1, "fail": 1, "judgement": 1, "live": 1, "skipped": 1})
        self.assertEqual(hr.counts_of(self.OUT, cov), {"pass": 1, "fail": 1, "judgement": 3, "live": 2, "skipped": 1})

    def test_one_screen(self):
        cov = {"tested": [1], "judgement": [], "live": [], "gaps": [11, 12]}
        text = "\n".join(hr.summary("v2.9.0", self.OUT, cov, 125, None, "dev/handchecks/v2.9.0.md"))
        self.assertIn("pass 1  fail 1  judgement-only 1  live-only 1  skipped 1", text)
        self.assertIn("FAIL 2: expected 3 rows, got 2", text)          # the 'auto (kind):' prefix is gone
        self.assertIn("GAP, no test and no tag: 11, 12", text)
        self.assertIn("(2 min)", text)
        self.assertIn("coverage: no sheet", "\n".join(hr.summary("v2.9.0", self.OUT, None)))
        self.assertIn("NOT RUN", hr.summary("v2.9.0", {}, None, None, "no result written")[0])

    def test_a_reason_drops_unittests_rules_and_the_prefix(self):
        self.assertEqual(hr.one_line("auto (scriptable): f.py::t: ----------\nRan 0 tests in 0.000s\n\nNO TESTS RAN"),
                         "t: Ran 0 tests in 0.000s NO TESTS RAN")
        self.assertEqual(len(hr.one_line("x" * 500, 40)), 40)

    def test_table(self):
        c = hr.counts_of(self.OUT)
        rows = hr.table([("v2.9.0", c, [11], 5, None), ("v2.9.1", c, None, 5, None), ("v2.9.2", None, None, None, "boom")])
        text = "\n".join(rows)
        self.assertIn("11", rows[2])
        self.assertIn("sheet missing", rows[3])
        self.assertIn("not run: boom", text)

    def test_list_lines_need_no_run(self):
        cov = {"tested": [1], "judgement": [2], "live": [], "gaps": [4]}
        text = "\n".join(hr.list_lines("v2.9.0", {1: True, 4: False}, cov, {2: "judgement"}, "dev/handchecks/v2.9.0.md"))
        self.assertIn("1 test(s) to run, 1 marked phase 2", text)
        self.assertIn("GAP, no test and no tag: 4", text)
        self.assertIn("judgement-only, no test: 2", text)


if __name__ == "__main__":
    unittest.main()
