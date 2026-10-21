"""#232 (Team Cap's review, LOW): Intake's rows, Today's day line and the Prep brief read a meeting's sensitivity through the
sweep's fail-closed invite_clean.sensitivity, never by comparing the raw value with "confidential". An older saved row with
"personal", "Private" or an odd value is then shown as private or confidential (title and times only), never in full.

Run: python3 dev/tests/test_meeting_sensitivity_rows.py      (quick tier: plain code)
"""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "system" / "scripts"))
import build_dashboard as b  # noqa: E402

LOOK = {"today": "2026-10-21", "hm": "12:00", "projects": [], "remembered": {}, "by_id": {}, "by_time": {}, "pages": {}, "hot": set(), "names": {}}


class Sensitivity(unittest.TestCase):
    def day(self, **ev):
        return b.day_meeting({"title": "Board prep", "start": "13:00", "end": "14:00", "where": "Room 1", **ev}, "2026-10-21", LOOK)

    def test_the_day_line_fails_closed(self):
        for raw, private, conf in (("personal", True, False), ("Private", True, False), ("Confidential", False, True),
                                   ("secret-ish", False, True), ("normal", False, False), (None, False, False)):
            with self.subTest(raw):
                m = self.day(**({"sensitivity": raw} if raw is not None else {}))
                self.assertEqual((m["private"], m["confidential"]), (private, conf))
                if private:
                    self.assertEqual(m["title"], "Busy")
                if private or conf:
                    self.assertNotIn("where", m)                       # title and times only

    def test_the_prep_brief_fails_closed(self):
        self.assertTrue(b.prep_invite({"sensitivity": "personal", "body": "x"})["confidential"])
        self.assertTrue(b.prep_invite({"sensitivity": "CONFIDENTIAL", "body": "x"})["confidential"])
        self.assertNotIn("confidential", b.prep_invite({"sensitivity": "normal", "body": "x"}))

    def test_intake_rows_read_it_through_invite_clean(self):
        src = (REPO / "system/scripts/build_dashboard.py").read_text(encoding="utf-8")
        body = src[src.index("def inbox_meetings"):src.index("def ", src.index("def inbox_meetings") + 10)]
        self.assertIn("invite_clean.sensitivity(ev)", body)
        self.assertNotIn('== "confidential"', body.replace('sens == "confidential"', ""))


if __name__ == "__main__":
    unittest.main(verbosity=1)
