"""creaite 2.4.0's hand checks for #229 (dev/handchecks/v2.4.0-229.md), automated: each runs the test it names.

Run them all, fill the Results table and make the screenshot sheet:  python3 dev/tools/handcheck.py v2.4.0-229 --no-sheet
Run this file on its own:                                             python3 dev/tests/handchecks/test_v240_229.py

One method per check, `test_cNN_…`, its docstring quoting the check. Desktop (1400 px) only. How the row looks is judgement on
the screenshot sheet; the tests assert one meta line, the tooltip, the peek, the marks, and Activity's missing Kind button and the funnel's kind filter.
"""
import re
import subprocess
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hcbase import NOTES, only  # noqa: E402,F401  (NOTES: read by handcheck.py)

TESTS = Path(__file__).resolve().parents[1]

KIND = {1: "scriptable", 2: "scriptable"}
LIVE_ONLY = {}

# Check number: the tests its text names, "file::test" (files in dev/tests/)
CHECKS = {
    1: ["test_review_meta_229.py::test_a_row_has_exactly_one_meta_line", "test_review_meta_229.py::test_detail_on_hover_and_in_the_peek_and_marks_stay"],
    2: ["test_activity_kind_229.py::test_no_kind_button_and_the_funnel_filters_by_kind", "test_activity_even_browser.py::test_search_and_funnel_are_even"],
}

_RESULTS = {}      # "file::test": (ok, note)


def run_ref(ref):
    """One named test in its own process. Passes only when it ran at least one test and none failed or was skipped."""
    f, name = ref.split("::")
    try:
        r = subprocess.run([sys.executable, "-m", "unittest", "-k", name, f[:-3]], cwd=TESTS, capture_output=True, text=True,
                           timeout=900)
    except subprocess.TimeoutExpired:
        return False, f"{ref}: timed out after 900 s"
    out = r.stdout + r.stderr
    ran = re.search(r"Ran (\d+) test", out)
    n = int(ran.group(1)) if ran else 0
    if r.returncode == 0 and n >= 1 and "skipped" not in out:
        return True, f"{n} test(s) in {f}"
    why = "skipped (no Chrome?)" if r.returncode == 0 and n >= 1 else next(
        (ln for ln in reversed(out.strip().splitlines()) if re.match(r"(\w*Error|AssertionError|FAILED|Error)", ln)), out.strip()[-200:])
    return False, f"{ref}: {why}"[:300]


def setUpModule():
    """Run every named test the selected checks need, before the checks report them."""
    want = {r for n, refs in CHECKS.items() if not only() or n in only() for r in refs}
    with ThreadPoolExecutor(2) as pool:
        for ref, res in zip(sorted(want), pool.map(run_ref, sorted(want))):
            _RESULTS[ref] = res


class Wrapped(unittest.TestCase):
    """Checks that run the tests they name."""

    def setUp(self):
        n = int(self._testMethodName[6:8])
        if only() and n not in only():
            self.skipTest("not in --only")

    def named(self, n):
        bad = [_RESULTS[r][1] for r in CHECKS[n] if not _RESULTS[r][0]]
        if bad:
            self.fail("; ".join(bad))
        NOTES[n] = f"ran {', '.join(r.split('::')[1] for r in CHECKS[n])}"[:280]

    def test_c01_a_review_row_has_one_meta_line(self):
        """1. Review: each row has one line of meta (kind, reason, source); the item's detail shows on hover and in the peek; "approve individually" and conflict marks stay on the row."""
        self.named(1)

    def test_c02_activity_has_no_kind_button(self):
        """2. Activity: no Kind button beside the filter icon; the funnel's list filters by kind, with its applied chip; every row keeps its tick box."""
        self.named(2)


if __name__ == "__main__":
    unittest.main()
