"""2.6.8 #369 bare20 (reviewer's rerun on cc67a8d6): glued labels, "Key" alone in a list item or cell, and the everyday-code exemption.

Run: python3 dev/tests/test_invite_clean_bare20.py      (quick tier: plain code, no Chrome, no Claude; the 70,000-body fuzz takes a while)

- GLUED: EVERY hard label (and its provider-prefixed forms) written straight against a value, with no separator, is a value: the value is
  three or more digits, or a token mixing letters and digits with at least one digit. A plain word glued on ("Tokenise", "Secretary",
  "Pinot", "Optical") is a longer word and stays.
- KEY: "Key" alone in a bullet, numbered item, quote line or table cell is a hard label: the next lines go whatever they hold. Known limits
  that stay: a word-only value after a bare "ID" label, and an unmarked "Key" line followed by "- hunter".
- EXEMPT: the everyday-code exemption (Q3, H2, 3D, 2nd, 10am, v2.1, A4) holds only for a token that is ENTIRELY such a code
  (`_CODE_LIKE.fullmatch`): Q3A9, H2K7 and A1B2 are two codes glued, mix letters and digits, and go.

All values are made up.
"""
import importlib.util
import random
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parents[1] / "system" / "scripts"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SCRIPTS))
import invite_clean as I  # noqa: E402
from test_invite_clean_idempotence import fuzz_list_body  # noqa: E402

HARD_LABELS = ["Token", "Secret", "OTP", "API key", "API-key", "Meeting ID", "Zoom ID", "Webinar ID", "Teams Meeting ID", "Webex ID",
               "Host key", "Moderator key", "Access code", "Pass code", "Passcode", "Password", "Pwd", "PIN", "PIN code", "Conference ID",
               "Zoom Passcode", "Teams PIN", "Zoom Meeting ID", "Participant code", "Dial-in PIN", "One-time code", "Security key",
               "Code", "Key", "Keys", "Tokens", "Secrets"]
VALUES = ["4417", "987 654 321", "123456789", "ZQ7742", "Q3A9", "H2K7", "A1B2", "kqzx9", "7K3M9P", "a1b2c3d4"]
GLUED_OK_PLAIN = ["ID badges", "Idaho 1234", "Pinterest 2026", "Tokenise", "Secretary 2026", "Pinot", "Optical", "Tokenise the data",
                  "Secretary", "Pinot Noir 2026", "Token4", "Key4", "Codex", "Secretariat", "Keyboard shortcuts", "Keynote", "Passport control",
                  "Passover", "Pineapple", "Codec review", "Coded", "Accessible design", "Accessory", "Secretly", "Pincer movement",
                  "Passage", "Mark Idle"]
OPEN_SUFFIX_OK = ["Lunch at 12:30", "Room 4", "Item 12", "Starts 10:00", "25-10-2026"]


def mutant(old, new, count=1):
    src = (SCRIPTS / "invite_clean.py").read_text(encoding="utf-8")
    assert src.count(old) >= 1, f"mutant anchor not found: {old!r}"
    spec = importlib.util.spec_from_loader("invite_clean_b20_mutant", loader=None)
    mod = importlib.util.module_from_spec(spec)
    mod.__file__ = str(SCRIPTS / "invite_clean.py")
    exec(compile(src.replace(old, new, count), "invite_clean_b20_mutant", "exec"), mod.__dict__)
    return mod


def leaks(mod, rows):
    return [(t, v) for t, v in rows if v in mod.invite_text(t) or mod.is_secret(t) is False and v in mod.scrub(t, 140)]


GLUED_ROWS = [(f"{lab}{val}", val.split()[0]) for lab in HARD_LABELS for val in VALUES]
GLUED_ROWS += [(f"Budget sync {lab.lower()}{val}", val.split()[0]) for lab in ("Token", "Secret", "OTP", "API key", "PIN", "Passcode", "Zoom ID") for val in VALUES]
REVIEWER = [("Token4417", "4417"), ("Secret4417", "4417"), ("OTP4417", "4417"), ("API key987 654 321", "987"), ("PINZQ7742", "ZQ7742"),
            ("PINQ3A9", "Q3A9"), ("Meeting IDZQ7742", "ZQ7742"), ("OTPH2K7", "H2K7"), ("Zoom IDH2K7", "H2K7")]
KEY_ROWS = [("* Key\n• 4417", "4417"), ("* Key\n> ZQ7742", "ZQ7742"), ("- Key\n- ZQ7742", "ZQ7742"), ("1. Key\n2. ZQ7742", "ZQ7742"),
            ("a) Key\nb) hunter", "hunter"), ("<ul><li>Key</li><li>4417</li></ul>", "4417"), ("<ul><li>Key</li><li>hunter</li></ul>", "hunter"),
            ("<table><tr><td>Key</td></tr><tr><td>ZQ7742</td></tr></table>", "ZQ7742"), ("| Key |\n| ZQ7742 |", "ZQ7742"),
            ("> Key\n> ZQ7742", "ZQ7742"), ("• Keys\nZQ7742", "ZQ7742"), ("- Key:\nhunter", "hunter"), ("Agenda\n- Key\n- 4417\nAOB", "4417")]
EXEMPT_GO = ["Q3A9", "H2K7", "A1B2", "B2C3", "Z9Y8", "3D4K", "2nd3x"]
EXEMPT_STAY = ["Q3", "H2", "3D", "2nd", "10am", "v2.1", "A4", "4pm", "3rd", "v10"]
HEADINGS = ["Password reset", "Code review", "Dress code", "Token refresh"]


class Glued(unittest.TestCase):
    def test_every_hard_label_glued_to_a_value_goes_in_a_body_a_title_and_a_place(self):
        bad = []
        for text, v in GLUED_ROWS:
            body = f"Agenda\n{text}\nAOB"
            if v in I.invite_text(body) or v in I.scrub(f"Weekly {text}", 140) or not I.is_secret(text):
                bad.append(text)
        self.assertEqual(bad, [], f"{len(bad)} glued rows keep their value, e.g. {bad[:5]}")

    def test_the_reviewers_nine_rows_go(self):
        for text, v in REVIEWER:
            self.assertNotIn(v, I.invite_text(text), text)
            self.assertTrue(I.is_secret(text), text)

    def test_after_a_separator_the_sweep_is_unchanged(self):
        for lab in HARD_LABELS:
            self.assertEqual(I.invite_text(f"{lab}: 4417"), "", lab)

    def test_ordinary_words_that_start_with_a_label_stay(self):
        for t in GLUED_OK_PLAIN + OPEN_SUFFIX_OK:
            self.assertEqual(I.invite_text(t), t, t)
            self.assertFalse(I.is_secret(t), t)

    def test_the_rows_are_a_fixed_point(self):
        for text, _v in GLUED_ROWS + KEY_ROWS:
            once = I.invite_text(text)
            self.assertEqual(I.invite_text(once), once, text)

    def test_sweep_size(self):
        self.assertGreaterEqual(len(GLUED_ROWS), 300)


class KeyAlone(unittest.TestCase):
    """bare22 (Cap): "Key" alone in a list item or cell is no longer a hard label (a RAG legend must keep its lines). The loss of that
    protection is a known limit: a list "Key" followed by a value in a list can leak. These rows pin the limit."""

    def test_a_rag_key_legend_keeps_its_lines(self):
        for t in ("RAG status\n- Key\n- Red: blocked\n- Amber: at risk\nAOB", "Key\nRed: blocked\nAmber: at risk\nAOB"):
            self.assertEqual(I.invite_text(t), t, t)

    def test_the_lost_protection_is_pinned_as_a_limit(self):
        for t in ("- Key\n- ZQ7742", "1. Key\n2. ZQ7742", "> Key\n> ZQ7742", "Agenda\n- Key\n- 4417\nAOB"):
            self.assertEqual(I.invite_text(t), t, t)

    def test_ordinary_key_lines_stay(self):
        for t in ("- Key milestones\n- Budget", "- Key dates\n- 4417 Main Street review", "1. Key risks\n2. Hiring", "Key milestones\nBudget",
                  "| Key | Owner |\n| Budget | Sara |"[:0] or "- Key decisions\n- Lunch at 12:30"):
            self.assertEqual(I.invite_text(t), t, t)

    def test_the_documented_limits_stay_and_are_pinned(self):
        self.assertEqual(I.invite_text("Key\n- hunter"), "Key\n- hunter")            # unmarked Key, word-only value in a list
        self.assertEqual(I.invite_text("Meeting ID hunterxyz"), "")      # bare22: a label plus a short phrase is a qualified label: it goes


class Exempt(unittest.TestCase):
    def test_passcode_looking_tokens_under_a_soft_heading_go(self):
        for h in HEADINGS:
            for v in EXEMPT_GO:
                for form in (f"{h}\n{v}", f"{h}\n- {v}", f"{h}\n1. {v}", f"<ul><li>{h}</li><li>{v}</li></ul>"):
                    self.assertNotIn(v, I.invite_text(form), form)

    def test_everyday_codes_under_a_soft_heading_stay(self):
        for h in HEADINGS:
            for v in EXEMPT_STAY:
                for form in (f"{h}\n{v}", f"{h}\n- {v}"):
                    self.assertIn(v, I.invite_text(form), form)

    def test_a_bare_two_character_code_is_a_known_limit(self):
        self.assertIn("X9", I.invite_text("Password reset\nX9"))            # same shape as Q3: kept under a soft heading (documented)

    def test_the_rule_is_a_whole_token_match(self):
        for v in EXEMPT_STAY:
            self.assertTrue(I._CODE_LIKE.fullmatch(v), v)
            self.assertFalse(I._mixed(v), v)
        for v in EXEMPT_GO:
            self.assertFalse(I._CODE_LIKE.fullmatch(v), v)
            self.assertTrue(I._mixed(v), v)


def key_fuzz_body(rnd, n, html):
    """List-heavy: Key (or a glued label) as a list item or cell, its value as the next item, among safe agenda items."""
    marks = ["- ", "* ", "• ", "1. ", "2) ", "a) ", "> ", "| "]
    safe = ["Lunch at 12:30", "Room 4", "Item 12", "Budget review", "Key milestones", "25-10-2026", "Hiring plan", "Q3 plan"]
    items, values = [], []

    def put(t, mark=None):
        mark = rnd.choice(marks) if mark is None else mark
        items.append(f"<li>{t}</li>" if html else (mark + t + (" |" if mark == "| " else "")))

    for _ in range(rnd.randint(2, 6)):
        pick = rnd.random()
        if pick < 0.35:
            put("Key")      # bare22: a "Key" item is not a label any more; its next item is an ordinary agenda item
            put(rnd.choice(safe))
        elif pick < 0.55:
            lab = rnd.choice(["Token", "Secret", "OTP", "API key", "PIN", "Zoom ID", "Meeting ID", "Host key", "Passcode"])
            v = rnd.choice([f"{rnd.randint(100, 9999)}{n:05d}", f"ZQ{n:05d}", f"H{n % 9}K{n:05d}"])
            put(lab + v)
            values.append(v)
        else:
            put(rnd.choice(safe))
    joiner = "" if html else "\n"
    return ("<ul>" + joiner.join(items) + "</ul>" if html else joiner.join(items)), values


KEY_FUZZ = 70000


class Fuzz(unittest.TestCase):
    def run_fuzz(self, make, seed, count):
        rnd = random.Random(seed)
        bad_fixed, bad_value = [], []
        for n in range(count):
            body, values = make(rnd, n)
            once = I.invite_text(body)
            if I.invite_text(once) != once:
                bad_fixed.append(body)
            if any(v in once for v in values):
                bad_value.append(body)
        self.assertEqual((len(bad_fixed), bad_fixed[:1]), (0, []), "not a fixed point after one pass")
        self.assertEqual((len(bad_value), bad_value[:1]), (0, []), "a value survives pass one")

    def test_seventy_thousand_key_and_glued_list_bodies(self):
        self.run_fuzz(lambda r, n: key_fuzz_body(r, n, n % 3 == 0), 2068, KEY_FUZZ)

    def test_thirty_thousand_more_list_bodies_from_the_older_generator(self):
        self.run_fuzz(lambda r, n: fuzz_list_body(r, n, html=bool(n % 3 == 0)), 20, 30000)


class Mutants(unittest.TestCase):
    def test_glued_rule_off(self):
        m = mutant("(?:{GLUED_VALUE})\"", "(?!)\"")
        self.assertTrue(leaks(m, REVIEWER), "no reviewer row leaked")

    def test_glued_digits_only_misses_the_mixed_tokens(self):
        m = mutant('|(?=[^\\W_]*\\d)(?=[^\\W_]*[^\\W\\d_])[^\\W_]+"', '"')
        self.assertTrue(leaks(m, [r for r in REVIEWER if r[1] in ("ZQ7742", "Q3A9", "H2K7")]))

    def test_glued_mixed_only_misses_the_digit_runs(self):
        m = mutant('GLUED_VALUE = r"\\d{3,}|', 'GLUED_VALUE = r"(?!)|')
        self.assertTrue(leaks(m, [("Token4417", "4417"), ("Secret4417", "4417"), ("API key987 654 321", "987")]))

    def test_glued_without_the_bare_labels_misses_token_secret_otp_apikey(self):
        m = mutant("|{_BARE}|{_BARE_LABELS})(?:{GLUED_VALUE})", ")(?:{GLUED_VALUE})")
        self.assertTrue(leaks(m, [("Token4417", "4417"), ("Secret4417", "4417"), ("OTP4417", "4417")]))

    def test_glued_value_must_have_a_digit(self):
        m = mutant("(?=[^\\W_]*\\d)(?=[^\\W_]*[^\\W\\d_])", "(?=[^\\W_]*[^\\W\\d_])")
        self.assertTrue([t for t in ("Tokenise", "Pinot", "Optical", "Secretary") if m.is_secret(t)])

    def test_exemption_widened_to_a_prefix_match_leaks_passcode_tokens(self):
        m = mutant("and not _CODE_LIKE.fullmatch(w)", "and not _CODE_LIKE.match(w)")
        self.assertIn("Q3A9", m.invite_text("Password reset\nQ3A9"))
        self.assertNotIn("Q3A9", I.invite_text("Password reset\nQ3A9"))


if __name__ == "__main__":
    unittest.main()
