"""2.6.8 gate fixes H1 and H3 (Banner's pass on bare22, #369).

H1: a hard label plus a qualifier made only of listed words ("Passcode for the call", "PIN for the session"), the value on the next
line, is a label alone: the value goes. "Password reset" and "Password policy review" stay soft phrases; ordinary agenda lines stay.
H3: a SIP / H.323 dial address (8+ digits, optionally "..passcode", before the @) is a join link, also as mailto: or in angle brackets.
Mutants restore each bug and the rows must then leak.

Run: python3 dev/tests/test_invite_clean_h1h3.py
"""
import importlib.util
import itertools
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "system/scripts"
sys.path.insert(0, str(SCRIPTS))
import invite_clean as I  # noqa: E402

LABELS = ("Passcode", "PIN", "Password", "Access code", "Meeting ID")
QUALIFIERS = ("for the call", "for the session", "for the sync", "for the review", "for the training", "for the workshop")
VALUES = ("482915", "4417", "345 678 912 345")
SIP = ("Join by SIP\n• 85512345678@zoomcrc.com", "85512345678..482915@zoomcrc.com", "123456789@t.plcm.vc",
       "<mailto:85512345678@zoomcrc.com>", "<85512345678@zoomcrc.com>", "mailto:123456789@t.plcm.vc", "85512345678@pexip.me",
       "85512345678@sip.example.org")


def mutant(old, new):
    src = (SCRIPTS / "invite_clean.py").read_text(encoding="utf-8")
    assert old in src, old
    spec = importlib.util.spec_from_loader("invite_clean_h", loader=None)
    mod = importlib.util.module_from_spec(spec)
    mod.__dict__["__file__"] = str(SCRIPTS / "invite_clean.py")
    exec(compile(src.replace(old, new, 1), "invite_clean_h", "exec"), mod.__dict__)
    return mod


def bodies():
    for lab, q, v in itertools.product(LABELS, QUALIFIERS, VALUES):
        yield f"{lab} {q}\n{v}", v
        yield f"<p>{lab} {q}</p><p>{v}</p>", v
        yield f"<ul><li>{lab} {q}</li><li>{v}</li></ul>", v


def leaks(mod):
    return [b for b, v in bodies() if v in mod.invite_text(b).replace("•", "")]


class H1(unittest.TestCase):
    def test_a_qualified_hard_label_removes_the_next_line(self):
        self.assertEqual(leaks(I), [])

    def test_soft_phrases_and_agenda_lines_stay(self):
        for t in ("Password reset", "Password policy review", "Code review", "Meeting ID changes", "Agenda\nPassword reset process\nNext steps"):
            self.assertEqual(I.invite_text(t), t, t)

    def test_mutant_restoring_the_old_lookahead_leaks(self):
        m = mutant('_SOFT_FIRST = "|".join(sorted(BARE_LISTED - set(BARE_FUNCTION)))', '_SOFT_FIRST = "|".join(sorted(BARE_LISTED))')
        self.assertNotEqual(leaks(m), [])


class H3(unittest.TestCase):
    def test_a_sip_address_is_removed(self):
        for t in SIP:
            out = I.invite_text("Call:\n" + t + "\nEnd")
            self.assertNotRegex(out, r"\d{8,}", t)
            self.assertTrue(I.is_secret(t), t)

    def test_ordinary_addresses_stay(self):
        for a in ("pin.sharma@example.org", "sara.khan@client.com", "omar2@example.org", "a1234567@client.com"):
            self.assertTrue(I.safe_address(a), a)
        self.assertFalse(I.safe_address("85512345678@zoomcrc.com"))
        self.assertEqual(I.invite_text("Ask sara.khan@client.com"), "Ask sara.khan@client.com")

    def test_mutant_without_the_sip_rule_leaks(self):
        m = mutant('SIPADDR = re.compile(r"(?<![\\w.-])\\d{8,}(?:\\.\\.\\d+)?@[\\w-]", re.I)', 'SIPADDR = re.compile(r"(?!)")')
        leaked = [t for t in SIP if "85512345678" in m.invite_text(t) or "123456789" in m.invite_text(t)]
        self.assertNotEqual(leaked, [])


if __name__ == "__main__":
    unittest.main()
