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

    @staticmethod
    def inbox_src(src=None):
        """The text of inbox_meetings and the helpers it was split into (#328: _inbox_row reads the sensitivity, _inbox_match decides
        the project): a test of what the Intake rows do reads all of them, so moving the call between them is fine and removing it is not."""
        src = src if src is not None else (REPO / "system/scripts/build_dashboard.py").read_text(encoding="utf-8")
        parts = []
        for name in ("inbox_meetings", "_inbox_row", "_inbox_match"):
            at = src.index(f"def {name}(")
            parts.append(src[at:src.index("\ndef ", at + 10)])
        return "\n".join(parts)

    def test_intake_rows_read_it_through_invite_clean(self):
        body = self.inbox_src()
        self.assertIn("invite_clean.sensitivity(ev)", body)
        self.assertNotIn('== "confidential"', body.replace('sens == "confidential"', ""))

    def test_removing_the_call_from_the_helper_fails_the_check(self):
        """Mutant: with the sensitivity call gone from the helpers, the same check must fail."""
        src = (REPO / "system/scripts/build_dashboard.py").read_text(encoding="utf-8")
        mutant = src.replace("sens = invite_clean.sensitivity(ev)", "sens = 'normal'")
        self.assertNotEqual(mutant, src)
        self.assertNotIn("invite_clean.sensitivity(ev)", self.inbox_src(mutant))


if __name__ == "__main__":
    unittest.main(verbosity=1)
