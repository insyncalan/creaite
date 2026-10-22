"""#280 follow-up (Cap's 2.5.4 review): the guarded diffs that call review.py and review.py's side of them go together.

Run: python3 dev/tests/test_held_pair.py      (reads the source; no vault)

dev/proposals/280/tracker-held.py.diff makes tracker.py's apply call review.hold_missing (imported inside _hold_missing_sources,
so a tracker.py without review.py's half would only fail at the first apply, with an AttributeError). live_server-held.py.diff
sends `reject N --discard` and `approve N --without-transcript` to review.py. review.py is not guarded and reaches a line by a
merge, the guarded diffs by `git apply`: this test fails when one half is there without the other, in either direction for the
tracker pair, so the pair can't be applied apart silently.
"""
import ast
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "system/scripts"


def source(name):
    return (SCRIPTS / name).read_text(encoding="utf-8")


def defines(name, func):
    """Whether system/scripts/<name> defines a top-level function `func`."""
    return any(isinstance(n, ast.FunctionDef) and n.name == func for n in ast.parse(source(name)).body)


class HeldPair(unittest.TestCase):
    def test_tracker_calls_hold_missing_only_with_review_defining_it(self):
        calls = "review.hold_missing(" in source("tracker.py")
        if calls:
            self.assertTrue(defines("review.py", "hold_missing"),
                            "tracker.py calls review.hold_missing (tracker-held.py.diff) but review.py lacks it: merge the "
                            "2.5.4 review.py with it (dev/proposals/280/README.md, third round)")

    def test_review_hold_missing_is_used_once_tracker_has_taken_the_diff(self):
        """The other way round: review.py's hold_missing with a tracker.py that never calls it means tracker-held.py.diff is owed
        (Review would say minutes are held while Apply still stops on them). Only when tracker.py has taken the first #280 diff."""
        t = source("tracker.py")
        if defines("review.py", "hold_missing") and "#280" in t:
            self.assertIn("review.hold_missing(", t, "review.py has hold_missing but tracker.py doesn't call it: apply "
                          "dev/proposals/280/tracker-held.py.diff")

    def test_live_server_review_modes_are_known_to_review(self):
        ls, rv = source("live_server.py"), source("review.py")
        if '"--discard"' in ls:
            self.assertIn('"--discard"', rv, "live_server.py sends reject N --discard (live_server-held.py.diff); review.py lacks it")
            self.assertTrue(defines("review.py", "cmd_discard"))
        if '"without-transcript"' in ls:
            self.assertIn('"--without-transcript"', rv, "live_server.py sends --without-transcript; review.py lacks it")


if __name__ == "__main__":
    unittest.main()
