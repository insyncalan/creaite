"""#232 C3 (v2.6.0): the Intake page reads in every palette, light and dark (the port of test_review_age's Themes class, whose banner went
with the old Review page). Measured as drawn: each visible match's text colour against the first opaque background behind it, every
ancestor's opacity multiplied in (handchecks/measure.py's paint_contrast).

Over the Review side's fixture (intake_review_support): one open meeting with its routine group and the items that need a decision,
and the mail and Teams section.
- the words of a meeting, a stage box and a proposal (title, change line, source, quote): 4.5:1 (WCAG 1.4.3);
- a pill and a tag (the kind, Routine, Stale): 3:1, the bar for a labelled mark.

Run: python3 dev/tests/test_intake_review_themes.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import intake_review_support as S  # noqa: E402
from live_browser import TEST_PALETTES, LiveBrowserCase  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent / "handchecks"))
from measure import paint_contrast  # noqa: E402

TEXT = {"meeting title": "#v-intake-review tr[data-irm] td.title b",
        "proposal title": "#v-intake-review tr.irprop .icttl",
        "proposal source": "#v-intake-review tr.irprop .icsrc",
        "stage box": "#v-intake-review [data-irstage]",
        "sub line": "#v-intake-review #irSub",
        "heading": "#v-intake-review h1"}
MARKS = {"kind pill": "#v-intake-review tr.irprop .ickind",
         "routine tag": "#v-intake-review tr.irprop .icroutine"}
HELD = set()        # (kind, palette, mode) held for a decision, not fixed


class Themes(LiveBrowserCase):
    shared_server = True
    width, height = 1400, 1000

    @classmethod
    def load(cls, v):
        S.load(v)

    def measure(self, sels, bar):
        b = self.b
        S.open_meeting(b)
        low, n = [], 0
        try:
            for p in TEST_PALETTES:
                for m in ("light", "dark"):
                    b.eval(f"document.documentElement.dataset.palette={json.dumps(p)}; document.documentElement.dataset.theme={json.dumps(m)}")
                    b.pump(0.05)
                    for kind, sel in sels.items():
                        rows = paint_contrast(b, sel)
                        self.assertTrue(rows, f"{kind}: nothing measured in {p} {m}")
                        n += len(rows)
                        low += [f"{kind} {p} {m}: {r['text']!r} {r['ratio']}:1 < {bar}" for r in rows
                                if r["ratio"] < bar and (kind, p, m) not in HELD]
        finally:
            b.eval("applyTheme()")
        self.assertGreater(n, 40)
        return low

    def test_words_are_readable_in_every_palette_light_and_dark(self):
        self.assertEqual(self.measure(TEXT, 4.5), [])

    def test_pills_and_tags_are_readable_in_every_palette_light_and_dark(self):
        self.assertEqual(self.measure(MARKS, 3.0), [])


if __name__ == "__main__":
    unittest.main()
