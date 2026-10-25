"""#375 option (c) (2.6.9): invite_filter.filter_text_with_scrub = html/blocks -> anchor layer + shape gate -> the 2.6.8 scrub as the
body label layer. Pins: the scrub's output is mapped back to the converted lines (subset up to blank lines), idempotence, the fixtures'
planted secrets gone, the gateway default, and the Zoom div-br-div paragraph break. Fictional data only."""
import json
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "system" / "scripts"))
import calendar_gateway as G  # noqa: E402
import invite_blocks as B  # noqa: E402
import invite_filter as F  # noqa: E402

FIX = ROOT / "dev" / "tests" / "fixtures" / "invites"
BODIES = [
    "Agenda\nPassword for the room - Teams\n477 638 386 738\nMilestones\nVendors\nPIN to follow:\n\nswordfish\nNext steps",
    "<p>Agenda</p><table><tr><td>Passcode</td><td>ZQ7742</td></tr><tr><td>Vendors</td><td>14-10-2026</td></tr></table>",
    "Budget review\nJoin: https://teams.example.org/l/meetup-join/19abc\nMeeting ID: 987 654 321\nPasscode: hunter2\nAOB",
    "Pin the roadmap\nPassword reset rollout\nCode of conduct refresh\nRoom 204\n",
    "Line one\r\nLine two\r\nPIN: 4417\r\nLine four",
]


class Scrub(unittest.TestCase):
    def test_subset_up_to_blank_lines(self):
        for b in BODIES:
            conv = set(B.to_lines(b) if B.looks_like_html(b) else b.replace("\r\n", "\n").split("\n"))
            for ln in F.filter_text_with_scrub(b).split("\n"):
                self.assertTrue(ln == "" or ln in conv, (b, ln))

    def test_idempotent(self):
        for b in BODIES:
            once = F.filter_text_with_scrub(b)
            self.assertEqual(F.filter_text_with_scrub(once), once, b)

    def test_idempotent_on_random_joins(self):
        r = random.Random(375)
        parts = [x for b in BODIES for x in b.split("\n")] + ["", "Room 204", "Passcode:", "hunter2", "https://x.example.org/a"]
        for _ in range(300):
            t = "\n".join(r.choice(parts) for _ in range(r.randint(1, 12)))
            once = F.filter_text_with_scrub(t)
            self.assertEqual(F.filter_text_with_scrub(once), once, t)

    def test_fixture_secrets_gone(self):
        n = 0
        for j in sorted(FIX.glob("*.json")):
            meta = json.loads(j.read_text())
            src = [p for p in (j.with_suffix(".html"), j.with_suffix(".txt")) if p.exists()]
            if not src or not meta.get("planted_secrets"):
                continue
            out = F.filter_text_with_scrub(src[0].read_text())
            n += 1
            for s in meta["planted_secrets"]:
                self.assertNotIn(s, out, j.name)
        self.assertGreater(n, 10)

    def test_negative_agenda_lines_with_a_blank_free_body(self):
        out = F.filter_text_with_scrub("Welcome\nBudget 1,200,000 approved\nRoom 204 booked\nAOB").split("\n")
        self.assertEqual(out, ["Welcome", "Budget 1,200,000 approved", "Room 204 booked", "AOB"])

    def test_gateway_default_is_the_composition(self):
        self.assertIn("filter_text_with_scrub", Path(G.__file__).read_text())

    def test_zoom_div_br_div_is_a_paragraph_break(self):
        self.assertEqual(B.to_lines("<div>a</div><br><div>b</div>"), ["a", "", "b"])
        self.assertEqual(B.to_lines("<div>a</div><div></div><br><div>b</div>"), ["a", "", "b"])
        self.assertEqual(B.to_lines("<br><div>a</div>"), ["a"])
        self.assertEqual(B.to_lines("<div>a<br>b</div>"), ["a", "b"])


if __name__ == "__main__":
    unittest.main()
