"""creaite 2.3.2's hand checks (dev/handchecks/v2.3.2.md), automated: each runs the test it names.

Run them all, fill the Results table and make the screenshot sheet:  python3 dev/tools/handcheck.py v2.3.2
Run this file on its own:                                             python3 dev/tests/handchecks/test_v232.py

One method per check, `test_cNN_…`, its docstring quoting the check. Desktop (1400 px) only. Real Chrome tests that already
exist for these three defects (#215, #213, #214).
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

KIND = {1: "scriptable", 2: "scriptable", 3: "scriptable"}
LIVE_ONLY = {}

# Check number: the tests its text names, "file::test" (files in dev/tests/)
CHECKS = {
    1: ["test_today_days_ui.py::test_215_no_hover_card_is_left_open_after_prep_and_back"],
    2: ["test_portfolio_table.py::test_213_evidence_text_follows_its_column_width"],
    3: ["test_rail_states.py::test_more_has_no_labels_switch_and_the_dialog_offers_it_beside_icons_only"],
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

    def test_c01_hover_card_gone_after_prep(self):
        """1. Hover a meeting on Today, choose Prep, then go back to Today: no hover card, peek or popup is left open."""
        self.named(1)

    def test_c02_evidence_column_follows(self):
        """2. Today's Portfolio table: drag the Evidence column wider and narrower: its text wraps to the new width and the width is kept after a reload."""
        self.named(2)

    def test_c03_more_menu_without_the_duplicate(self):
        """3. The rail's More menu does not list "Labels when collapsed"; Customise sidebar still has it and it works."""
        self.named(3)


if __name__ == "__main__":
    unittest.main()
