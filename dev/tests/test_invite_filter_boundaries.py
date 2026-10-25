"""#375 2.6.9 item 7 (block boundaries the scrub removes are put back for the anchor layer: an HTML Meet agenda survives).
Fictional data only. Run: python3 dev/tests/test_invite_filter_labels_x.py"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
import invite_filter as F  # noqa: E402


def D(text):
    return F.filter_text_with_scrub(text)


class Boundaries(unittest.TestCase):
    MEET = ("Join with Google Meet\nhttps://meet.example.test/abc-defg-hij\nJoin by phone\n(GB) +44 20 7946 0001 PIN: 123 456 789#")
    AGENDA = ["Agenda", "1. Budget review 12-11-2026", "2. Milestones 14:00-15:30", "3. Room 204 booking", "4. Risks and mitigations"]

    def test_meet_html_keeps_the_agenda(self):
        rule = "_" * 60
        block = rule + "\n" + self.MEET + "\n" + rule
        agenda = "\n".join(self.AGENDA)
        for parts in ([block, agenda], [agenda, block], [agenda, "Please read the pre-read.", block, "Minutes will follow."]):
            text = "\n\n".join(parts)
            html = "<html><body>" + "".join("<p>%s</p>" % "<br>".join(b.splitlines()) for b in text.split("\n\n")) + "</body></html>"
            out = D(html).split("\n")
            for ln in self.AGENDA:
                self.assertIn(ln, out)
            self.assertNotIn("meet.example.test", "\n".join(out))
            self.assertNotIn("123 456", "\n".join(out))

    def test_idempotent(self):
        text = "<p>Agenda<br>1. Budget</p><p>____<br>" + self.MEET.replace("\n", "<br>") + "<br>____</p>"
        once = D(text)
        self.assertEqual(D(once), once)


if __name__ == "__main__":
    unittest.main()
