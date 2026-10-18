"""creaite 2.3.4's hand checks (dev/handchecks/v2.3.4.md), automated: each runs the test it names.

Run them all, fill the Results table and make the screenshot sheet:  python3 dev/tools/handcheck.py v2.3.4
Run this file on its own:                                             python3 dev/tests/handchecks/test_v234.py

One method per check, `test_cNN_…`, its docstring quoting the check. Desktop (1400 px) only. The look of the card is judgement on
the screenshot sheet; the tests assert the title text, widths and ellipsis, and the project links' colour, size, weight and click.
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
    1: ["test_notes_pinned_title_browser.py::test_pinned_titles"],
    2: ["test_people_projects_links_browser.py::test_projects_column_links"],
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

    def test_c01_a_pinned_notes_card_shows_its_title(self):
        """1. Notes: a pinned note's card shows its title, a long title ends in an ellipsis, also for a confidential pinned note."""
        self.named(1)

    def test_c02_people_project_names_read_as_links(self):
        """2. People: the project names in the Projects column are in the link colour, the table's text size and weight 500, and open the project."""
        self.named(2)


if __name__ == "__main__":
    unittest.main()
