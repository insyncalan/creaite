"""E1 D, fix5: HTML breaks inside and between labels and values; the filter's result is a fixed point (Cap's re-check 3)."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "system" / "scripts"))
sys.path.insert(0, str(HERE))
import breakfuzz_gen as G  # noqa: E402
import invite_filter as F  # noqa: E402


def D(t):
    return F.filter_text_with_scrub(t)


class Idempotence(unittest.TestCase):
    def test_fuzz_fixed_point(self):
        bad = [b for b in G.bodies(2000) if D(D(b)) != D(b)]
        self.assertEqual(bad[:3], [])

    def test_known_shapes_fixed_point(self):
        for t in ["<p>PIN:<br/>Decisions log   824</p>", "<li>mupiwoc 824 \x85 Teams</li><div>PIN:<br>Welcome</div>",
                  "<td>Risks and issues   770</td><div>swordfish   a6ad063a9</div>"]:
            self.assertEqual(D(D(t)), D(t), t)

    def test_rounds_bound_and_mutant(self):
        self.assertEqual(F.FIXED_POINT_ROUNDS, 4)
        old = F._raw_first
        try:
            n = [0]

            def never(x):          # a filter that never settles is served as ""
                n[0] += 1
                return x + "x"
            F._raw_first = never
            self.assertEqual(F._fixed_point("a"), "")
        finally:
            F._raw_first = old


class BreakInsideLabel(unittest.TestCase):
    def test_closed_cases_stay_closed(self):
        for t in ["<p>Zoom passcode:</p><p>Decisions \x85log</p><p>mupiwoc</p>", "<p>Host \x0bkey (organiser only):</p><p>770</p>",
                  "<ul><li>Mot de \x0cpasse:  gusos58#</li></ul>", "<ul><li>Secret for the vendor portal</li><li>a6ad063a9</li></ul>"]:
            self.assertEqual(D(t), "", t)


if __name__ == "__main__":
    unittest.main()
