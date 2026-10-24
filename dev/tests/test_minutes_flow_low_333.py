"""#333: the minutes flow's low-severity findings that are plain page code.

The figure check does not fire when the transcript says "20th of November" and the page shows 20-11-2026 (it still fires when the
day or month is not said); the transcript pane says "1 turn", not "1 turns"; another project's item is marked as a possible
duplicate only on a close match (see test_smart_updates).

Run: python3 dev/tests/test_minutes_flow_low_333.py      (needs node)
"""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "system/templates/dashboard/src/components/minutes"


def figures(text, said):
    js = (SRC / "minutesDoc.js").read_text(encoding="utf-8")
    a = js.index("const FIGURE =")
    b = js.index("\n}\n", js.index("export function figuresMissing")) + 3
    code = js[a:b].replace("export function", "function")
    out = subprocess.run(["node", "-e", code + f"\nconsole.log(JSON.stringify(figuresMissing({json.dumps(text)}, {json.dumps(said)})))"],
                         capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


@unittest.skipUnless(shutil.which("node"), "needs node")
class Figures(unittest.TestCase):
    def test_a_date_said_in_words_is_not_a_missing_figure(self):
        self.assertEqual(figures("Send the pack by 20-11-2026", "I'll send it by the 20th of November"), [])
        self.assertEqual(figures("Send the pack by 20-11-2026", "by November 20"), [])

    def test_a_date_not_said_is_one_figure(self):
        self.assertEqual(figures("Send the pack by 20-11-2026", "by the 21st of November"), ["20-11-2026"])
        self.assertEqual(figures("Send the pack by 20-11-2026", "sometime soon"), ["20-11-2026"])

    def test_other_figures_are_still_checked(self):
        self.assertEqual(figures("Budget 45 by 20-11-2026", "40, the 20th of November"), ["45"])


class Turns(unittest.TestCase):
    def test_one_turn_is_singular(self):
        t = (SRC / "TranscriptPane.jsx").read_text(encoding="utf-8")
        self.assertIn('turn${tr.turns.length === 1 ? "" : "s"}', t)
        self.assertNotIn("`${tr.turns.length} turns`", t)


if __name__ == "__main__":
    unittest.main()
