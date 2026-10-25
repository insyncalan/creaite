"""#375 2.6.9 items 4 to 7 (label, signature, multi-line id, address and boundary rules around the frozen 2.6.8 scrub).
Fictional data only. Run: python3 dev/tests/test_invite_filter_labels_x.py"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
import invite_filter as F  # noqa: E402


def D(text):
    return F.filter_text_with_scrub(text)


class MultiLineId(unittest.TestCase):
    def test_one_group_per_line(self):
        for body in ("Meeting ID:\n412\n889\n330", "Hi.\n\n412\n889\n330\n\nBye.", "<div>412</div><div>889</div><div>330</div>"):
            out = D(body)
            for g in ("412", "889", "330"):
                self.assertNotIn(g, out, body)

    def test_ordinary_short_numbers_stay(self):
        self.assertEqual(D("Items\n\n12\n\nBye."), "Items\n\n12\n\nBye.")
        self.assertIn("2026", D("Plan\n2026\nBye."))

    def test_folded_ics_block_is_a_subset(self):
        out = D("Hello.\n\n123\n456\n789\n\nThanks.")
        self.assertEqual(out, "Hello.\n\nThanks.")


class AddressTokens(unittest.TestCase):
    def test_pin_in_address(self):
        for body in ("Join by SIP or mail: meet-8990@x.example.test", "mailto:join449038@bridge.example.test", "pin.1234@bridge.example.test"):
            out = D("Hello.\n\n" + body + "\n\nThanks.")
            self.assertNotIn("8990", out); self.assertNotIn("449038", out); self.assertNotIn("1234", out)
            self.assertIn("Thanks.", out)

    def test_plain_addresses_stay(self):
        out = D("Contact sara.khan@example.test or room-12@example.test")
        self.assertIn("sara.khan@example.test", out)

    def test_unlabelled_tokens(self):
        for tok in ("Summer2026!", "abc-defg-hij", "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.sflKxwRJSMeKKF2QT4",
                    "sk-live-4eC39HqLyjWDarjtT1zdp7dc"):
            self.assertEqual(D("Hello.\n\n" + tok + "\n\nBye."), "Hello.\n\nBye.", tok)

    def test_ordinary_tokens_stay(self):
        for tok in ("budget-review-2026-final.pdf", "Thanks!", "Q4-2026"):
            self.assertIn(tok, D("Hello.\n\n" + tok + "\n\nBye."))


class Signature(unittest.TestCase):
    def test_name_and_title_stay_number_goes(self):
        sig = "Please see the agenda.\n\nBest regards,\nMia Hale\nProgramme Manager\nExample Corp\nM: +44 7700 900123\nmia.hale@example.test"
        out = D(sig)
        self.assertNotIn("7700", out); self.assertNotIn("900123", out)
        for keep in ("Best regards,", "Mia Hale", "Programme Manager", "Example Corp", "mia.hale@example.test", "Please see the agenda."):
            self.assertIn(keep, out)

    def test_label_on_its_own_line_goes(self):
        out = D("Thanks,\nOmar Reyes\nMobile:\n+44 7700 900124\nExample Corp")
        self.assertNotIn("900124", out); self.assertIn("Omar Reyes", out)

    def test_join_block_without_signoff_loses_the_id(self):
        out = D("Hello.\n\nJoin now\nMeeting ID: 412 889 330 22\nSee you there\n\nBye.")
        self.assertNotIn("412", out)          # the scrub takes the labelled id line; the anchor layer takes the rest of a block that holds one
        self.assertIn("Bye.", out)


class HighOne(unittest.TestCase):
    def test_pin_behind_unlisted_label_after_id_block(self):
        for lab in ("Clave\n8825", "Hasło : 7679", "Åtkomstkod : 5885", "访问代码 | 4256", "Geçiş kodu\n5528", "Codice segreto\n4120"):
            out = D("Hello.\n\nMeeting ID: 412 889 330 22\n\n" + lab + "\n\nSee you Monday.")
            for d in ("8825", "7679", "5885", "4256", "5528", "4120"):
                self.assertNotIn(d, out, lab)
            self.assertIn("See you Monday.", out)

    def test_extended_label_alone(self):
        self.assertEqual(D("Hello.\n\nContraseña: 9021\n\nBye."), "Hello.\n\nBye.")
        self.assertEqual(D("Hello.\n\nPasswort\n3344\n\nBye."), "Hello.\n\nBye.")

    def test_short_block_after_nothing_stays(self):
        self.assertIn("Room 2026", D("Hello.\n\nRoom 2026\n\nBye."))


class HighTwo(unittest.TestCase):
    def test_codes_in_sentences(self):
        for line, num in (("Use 6802 to join", "6802"), ("Pass 4417", "4417"), ("Enter 551234 when prompted", "551234"),
                          ("Your access code is 4417", "4417")):
            self.assertNotIn(num, D("Hello.\n\n" + line + "\n\nThanks."), line)

    def test_ordinary_sentences_stay(self):
        for line in ("Use the 2026 template", "Enter room 204", "Pass the action list to Omar.", "Budget 1,200,000 approved",
                     "Join us at 14:00", "Use 4 desks"):
            self.assertIn(line, D("Hello.\n\n" + line + "\n\nThanks."), line)


if __name__ == "__main__":
    unittest.main()
