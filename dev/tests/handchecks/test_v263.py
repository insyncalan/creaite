"""creaite 2.6.3's hand checks that need no browser: is each guarded change of the release in this tree? (Draft.) One check per change,
`test_cNN_...`. The page behaviour is covered by the branches' own tests (test_minutes_export_choice, test_minutes_filing_ui,
test_fresh_ask_327, test_review_expect_routes, test_autostart_race and the rest) and by the sheet dev/handchecks/v2.6.3.md.

   1 #327 B   ask creaite starts fresh sessions by default; `continue` carries the thread on
   2 #324      File the minutes: the approve route settles a taken name before it files
   3 expect    the review route refuses a decision that does not say which item it means
   4 lows      draft_delivery.py is on the guarded list
   5 #331      the Word minutes read the When and attendees lines of the page's header
   6 #338      the rules file is at most half its old size (only if Alan approves it; an expected failure otherwise)

A check that needs a guarded change this tree does not have is an EXPECTED FAILURE (the convention test_v262.py uses): it is red for the
right reason and turns into an unexpected success (flagged) the moment the change is in.

Run (from the repository root):  python3 dev/tests/handchecks/test_v263.py
"""
import os
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
REPO = HERE.parents[2]
SCRIPTS = REPO / "system/scripts"

try:
    from hcbase import NOTES        # read by handcheck.py
    NOTES.clear()
except ImportError:                 # standalone without the helpers
    NOTES = {}


def _src(rel):
    p = REPO / rel
    return p.read_text(encoding="utf-8") if p.is_file() else ""


HAS = {
    "fresh": "fresh_session" in _src("system/scripts/live_server.py"),
    "filing": "minutes_destination" in _src("system/scripts/live_server.py"),
    "expect": "didn't say which item it meant" in _src("system/scripts/live_server.py"),
    "guardlist": '"draft_delivery.py"' in _src("dev/tests/guarded_chain.py"),
    "header": "Attendees" in _src("system/scripts/creaite_doc.py") and "When" in _src("system/scripts/creaite_doc.py"),
    "rules": os.path.isfile(REPO / "system/templates/creaite-reference.md"),
}
WHERE = {"fresh": "dev/proposals/327b/live_server.diff", "filing": "dev/proposals/324/live_server.diff",
         "expect": "dev/proposals/expect-mandatory/live_server.diff", "guardlist": "dev/proposals/draft-delivery-guarded",
         "header": "origin/v263-331", "rules": "dev/proposals/338 (only if Alan approves)"}


def needs(key):
    """An expected failure while this tree lacks the change, a plain check once it has it."""
    def wrap(fn):
        if HAS[key] or os.environ.get("CREAITE_HC_SHOW_XFAIL"):
            return fn
        fn.__doc__ = (fn.__doc__ or "") + f" [expected failure: {WHERE[key]} is not in this tree]"
        return unittest.expectedFailure(fn)
    return wrap


KIND = {n: "scriptable" for n in range(1, 7)}
LIVE_ONLY = {}
NOTES = {}


class Present263(unittest.TestCase):
    @needs("fresh")
    def test_c01_fresh_sessions(self):
        """A new ask is fresh unless the request says `continue` or is a confirmation."""
        s = _src("system/scripts/live_server.py")
        self.assertIn("fresh_session", s)
        self.assertIn("carry_over", s)

    @needs("filing")
    def test_c02_filing_settles_a_taken_name(self):
        """The approve route settles the filed name (and the transcript's) before it files."""
        self.assertIn("settle(", _src("system/scripts/live_server.py"))
        self.assertTrue((SCRIPTS / "minutes_destination.py").is_file())

    @needs("expect")
    def test_c03_expect_is_required(self):
        """A review decision that does not say which item it means is refused with the reload message."""
        self.assertIn("Reload the page and try again", _src("system/scripts/live_server.py"))

    @needs("guardlist")
    def test_c04_draft_delivery_is_guarded(self):
        """draft_delivery.py is on the guarded list."""
        self.assertTrue(HAS["guardlist"])

    @needs("header")
    def test_c05_word_header(self):
        """The Word minutes' title block reads the When and attendees lines (and the project name)."""
        s = _src("system/scripts/creaite_doc.py")
        self.assertIn("Attendees", s)
        self.assertIn("When", s)

    @needs("rules")
    def test_c06_rules_slimmed(self):
        """Only if approved: the rules file is at most half its old size and the reference file exists."""
        self.assertLessEqual(len(_src("system/scripts/../creaite-rules.md").encode()), 33000)


if __name__ == "__main__":
    unittest.main()
