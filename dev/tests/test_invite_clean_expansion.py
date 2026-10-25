"""2.6.8 review: a hostile invite cannot make the cleaning slow by what its characters expand to.

Run: python3 dev/tests/test_invite_clean_expansion.py      (quick tier: plain code, about 15 seconds)

NFKC / NFKD turn one character into several (U+FDFA into 18 letters, a circled number into "(1)"); a body of 40,000 of them took seconds,
and clean_row / clean_calendar run on every read. Now a character whose NFKC or NFKD form is longer than MAX_EXPANSION (4) is a space
BEFORE any expansion (never a cut of the text: a label after it still matches), so a text is at most 4 times as long as it was, and a
2000-character line at most 8000. No label letter expands to more than 3 (checked below for every label).

- LETTERS: every character of every label list expands to at most MAX_EXPANSION, and the non-Latin labels still match.
- TIMING: U+FDFA, U+2474, U+33AF, U+FB03 as 2000-character lines (under LIMIT) and as 40,000 / 60,000 repetitions (under BIG, which is
  also at most 3 times what the same number of plain characters costs), through scrub, invite_text, is_secret, clean_row, clean_calendar,
  inside the 5 s alarm.
- MUTANT: the replacement before the expansion removed: the alarm trips.
"""
import importlib.util
import sys
import time
import unicodedata
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parents[1] / "system" / "scripts"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SCRIPTS))
import invite_clean as I  # noqa: E402
import test_invite_clean_timing as T  # noqa: E402

LIMIT = 0.2          # a 2000-character line
BIG = 1.5            # 40,000 characters of a body (RAW_MAX is 60,000): the plain-ASCII equivalent already costs about 0.3 s
CHARS = ["ﷺ", "⑴", "㎯", "ﬃ", "㎒", "שּׁ"]


def paths_of(mod, text):
    row = {"id": "e", "start": "09:00", "end": "10:00", "title": text[:300], "where": text[:80], "organiser": text[:80], "sensitivity": "normal",
           "body": text, "attendees": [{"name": text[:80], "email": "a@b.example"}], "attachments": [text[:80]]}
    return [("scrub", mod.scrub, (text, 140)), ("invite_text", mod.invite_text, (text,)), ("is_secret", mod.is_secret, (text,)),
            ("clean_row", mod.clean_row, (row,)), ("clean_calendar", mod.clean_calendar, ({"days": {"2026-10-26": [row]}},))]


class Letters(unittest.TestCase):
    def test_no_label_letter_expands_far(self):
        chars = {c for c in I._OTHER_ALPHABETS if not c.isascii()}
        chars |= {c for c in "".join(w for _l, ok in I.BARE_NEXT for w in ok) if not c.isascii()}
        for c in sorted(chars):
            for form in ("NFKC", "NFKD"):
                self.assertLessEqual(len(unicodedata.normalize(form, c)), I.MAX_EXPANSION, f"{c!r} {form}")
        self.assertEqual(I._unit("ﬃ"), "ﬃ")                           # ffi: 3, kept
        self.assertEqual(I._unit("⑴"), "⑴")                           # (1): 3, kept
        self.assertEqual(I._unit("ﷺ"), " ")                                # 18: a space

    def test_non_latin_labels_still_match(self):
        for text, v in (("パスコード: 4417", "4417"), ("비밀번호: 4417", "4417"),
                        ("Пароль: 4417", "4417"), ("密码: 4417", "4417"),
                        ("كلمة المرور: 4417", "4417"),
                        ("ﬃé Passcode: 4417", "4417"), ("ﷺ Passcode: 4417", "4417")):
            self.assertNotIn(v, I.scrub(text, 140), text)
            self.assertNotIn(v, I.invite_text(text), text)


class Timing(unittest.TestCase):
    def test_hostile_expansion(self):
        slow, n = [], 0
        for ch in CHARS:
            for text, limit in ((ch * 2000, LIMIT), (ch * 40000, BIG)):
                for name, fn, args in paths_of(I, text):
                    took, _out = T.timed(fn, *args)
                    n += 1
                    if took > limit:
                        slow.append((round(took, 3), name, hex(ord(ch)), len(text)))
        self.assertGreaterEqual(n, 60)
        self.assertEqual(slow[:6], [])

    def test_mixed_with_labels_and_lines(self):
        slow = []
        for ch in CHARS:
            text = "\n".join(("Passcode: " + ch * 150) for _ in range(300))
            for name, fn, args in paths_of(I, text):
                took, _out = T.timed(fn, *args)
                if took > BIG:
                    slow.append((round(took, 3), name, hex(ord(ch))))
        self.assertEqual(slow[:6], [])


class Mutant(unittest.TestCase):
    def test_no_replacement_before_the_expansion_trips_the_alarm(self):
        src = (SCRIPTS / "invite_clean.py").read_text(encoding="utf-8")
        old = 'return text if text.isascii() else "".join(map(_unit, text))'
        self.assertIn(old, src)
        spec = importlib.util.spec_from_loader("invite_clean_expansion_mutant", loader=None)
        mod = importlib.util.module_from_spec(spec)
        mod.__file__ = str(SCRIPTS / "invite_clean.py")
        exec(compile(src.replace(old, "return text", 1), "invite_clean_expansion_mutant", "exec"), mod.__dict__)
        keep, T.ALARM = T.ALARM, 1.0
        try:
            t0 = time.time()
            with self.assertRaises(TimeoutError):
                T.timed(mod.invite_text, "ﷺ" * 60000)
            self.assertLess(time.time() - t0, 3.0)
        finally:
            T.ALARM = keep


if __name__ == "__main__":
    unittest.main()
