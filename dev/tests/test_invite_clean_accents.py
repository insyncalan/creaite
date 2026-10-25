"""2.6.8 review: an accent or combining mark on a label letter must not hide the label.

Run: python3 dev/tests/test_invite_clean_accents.py      (quick tier: plain code, about 20 seconds)

skeleton() used NFKC, which COMPOSES "e" + U+0301, so the later mark-strip found nothing: "Pásscode: 1234", "Piń: 1234", "Passwörd hunter"
kept their value. Now NFKD, every Mn / Me mark removed (kana voicing marks kept), NFC. Only the matching copy is changed; the text that is
kept is never altered.

- REVIEWER: the exact strings of the review, as a title (scrub) and as a body (invite_text), same line and next line.
- SWEEP: every combining mark U+0300 to U+036F on the first, a middle and the last letter of labels, and a seeded sample (seed 232) of
  precomposed Latin letters (Latin-1, Extended-A/B, Additional) that decompose to the label's letters, in every position; same line,
  <td>, <li> and next line.
- TIMING: 2000-character runs of combining marks on and round every label, each under LIMIT inside the 5 s alarm.
- KEPT: the text that stays keeps its accents. CONTROLS: what ordinary words lose (NOTES-2.6.8.md).
- MUTANTS: NFKC restored; the mark strip removed; the markdown-link reading removed.
All values are made up.
"""
import importlib.util
import random
import sys
import unicodedata
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parents[1] / "system" / "scripts"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SCRIPTS))
import invite_clean as I  # noqa: E402
from test_invite_clean_timing import ALARM, timed  # noqa: E402,F401

LIMIT = 0.2
# (text, value) as a title; every one must come back without the value
REVIEWER_TITLES = [("Pásscode: 1234", "1234"), ("Piń: 1234", "1234"), ("Passcodé: hunter", "hunter"),
                   ("Passwörd hunter", "hunter"), ("Pàssword hunter", "hunter"), ("Sécret hunter", "hunter"),
                   ("Passcodě: hunter", "hunter"), ("Passcodė: hunter", "hunter"), ("Passcodȩ: hunter", "hunter"),
                   ("Påsscode: hunter", "hunter"), ("Passcodé: 4417", "4417"), ("ṔIN: 4417", "4417")]
REVIEWER_BODIES = [("PIŃ\nkqzxyw\nok", "kqzxyw"), ("Tokeń\nabcdef\nok", "abcdef"), ("[Passcode](http://x.example.invalid)\nhunter\nok", "hunter"),
                   ("[Meeting ID](http://x.example.invalid): 987 654 321", "987 654 321"), ("Pásscode:\nhunter\nok", "hunter")]
OTHER_ALPHABETS = [("パスコード: 4417", "4417"), ("비밀번호: 4417", "4417"), ("Пароль: 4417", "4417"),
                   ("密码: 4417", "4417"), ("パスワード: 4417", "4417")]
CORES = ["Passcode", "PIN", "Password", "Meeting ID", "Pass code", "Host key", "Access code", "Webinar ID", "Pw", "Pswd", "Token", "Secret",
         "OTP", "Code", "API key", "Key", "Access", "Pwd", "Join code", "Zoom ID"]
MARKS = [chr(c) for c in range(0x300, 0x370)]


def precomposed():
    """{base letter: [precomposed Latin characters that decompose to that letter plus marks only]}."""
    out = {}
    for cp in [*range(0xC0, 0x250), *range(0x1E00, 0x1F00)]:
        ch = chr(cp)
        d = unicodedata.normalize("NFD", ch)
        if len(d) > 1 and d[0].isascii() and d[0].isalpha() and all(unicodedata.category(c) == "Mn" for c in d[1:]):
            out.setdefault(d[0], []).append(ch)
    return out


PRE = precomposed()


def variants(core):
    """The label with one letter changed: every mark on the first, middle and last letter, and a seeded sample of precomposed letters."""
    rnd = random.Random(232 + len(core))
    letters = [i for i, c in enumerate(core) if c.isalpha()]
    spots = {letters[0], letters[len(letters) // 2], letters[-1]}
    out = [core[:i + 1] + m + core[i + 1:] for i in sorted(spots) for m in (MARKS if core in CORES[:8] else rnd.sample(MARKS, 16))]
    for i in letters:
        pool = PRE.get(core[i].lower(), [])
        for ch in rnd.sample(pool, min(len(pool), 6)):
            out.append(core[:i] + (ch.upper() if core[i].isupper() and ch.upper() != ch else ch) + core[i + 1:])
    return out


def sweep_survivors(mod):
    n, bad = 0, []
    for core in CORES:
        for label in variants(core):
            for v in ("hunter", "4417"):
                cases = [("scrub", mod.scrub(label + ": " + v, 140)),
                         ("td", mod.invite_text("<td>" + label + ":</td><td>" + v + "</td>")),
                         ("li", mod.invite_text("<ul><li>" + label + ":</li><li>" + v + "</li></ul>")),
                         ("next", mod.invite_text("Agenda: budget\n" + label + ":\n" + v + "\nEnd"))]
                for kind, out in cases:
                    n += 1
                    if v in out:
                        bad.append((kind, label, v))
    return n, bad


class Reviewer(unittest.TestCase):
    def test_titles(self):
        for text, v in REVIEWER_TITLES:
            self.assertNotIn(v, I.scrub(text, 140), text)
            self.assertNotIn(v, I.invite_text("Agenda: budget\n" + text + "\nEnd"), text)

    def test_bodies(self):
        for text, v in REVIEWER_BODIES:
            self.assertNotIn(v, I.invite_text("Agenda: budget\n" + text + "\nEnd"), text)
        self.assertNotIn("987", I.scrub("[Meeting ID](http://x.example.invalid): 987 654 321", 140))

    def test_other_alphabets_still_match(self):
        for text, v in OTHER_ALPHABETS:
            self.assertNotIn(v, I.scrub(text, 140), text)
            self.assertNotIn(v, I.invite_text(text), text)


class Sweep(unittest.TestCase):
    def test_every_mark_and_precomposed_letter_in_every_label(self):
        n, bad = sweep_survivors(I)
        self.assertGreater(n, 15000)
        self.assertEqual(bad[:8], [], f"{len(bad)} of {n} combinations leak")


class Kept(unittest.TestCase):
    def test_kept_text_keeps_its_accents(self):
        for t in ("Café résumé review", "Zoë's naïve plan", "Übersicht für München"):
            self.assertEqual(I.scrub(t, 140), t)
            self.assertEqual(I.invite_text("Agenda: " + t + "\nEnd"), "Agenda: " + t + "\nEnd")
        out = I.invite_text("Agenda: café\nPasscode: 4417\nThanks à tous\nEnd")
        self.assertIn("café", out)
        self.assertIn("Thanks à tous", out)

    def test_controls_what_ordinary_words_lose(self):
        """A word that differs from a label only by its accents IS the label (fail closed): see NOTES-2.6.8.md."""
        self.assertEqual(I.scrub("Passwörter", 140), "Passwörter")                # a different word
        self.assertEqual(I.scrub("Códe review", 140), "Códe review")              # an allowed phrase
        self.assertEqual(I.scrub("Piñ pad", 140), "Piñ pad")
        self.assertEqual(I.scrub("Códe sprint", 140), "")                               # lost, like "Code sprint"
        self.assertEqual(I.scrub("Piñ board", 140), "")
        self.assertEqual(I.scrub("Tokén of appreciation", 140), "")


class Timing(unittest.TestCase):
    def test_long_runs_of_combining_marks(self):
        slow, n = [], 0
        mark = "́"
        for core in CORES:
            texts = [core + mark * 2000 + ": 4417", core[0] + mark * 500 + core[1:] + ": 4417", (mark * 2000).join(core) + ": 4417",
                     mark * 2000 + core, core + "̧́̈" * 700]
            for text in texts:
                for fn, args in ((I.scrub, (text, 140)), (I.invite_text, (text,)), (I.is_secret, (text,)),
                                 (I.invite_text, ("<td>" + text + "</td><td>x</td>",))):
                    took, _out = timed(fn, *args)
                    n += 1
                    if took > LIMIT:
                        slow.append((round(took, 3), core, len(text)))
        self.assertGreaterEqual(n, 400)
        self.assertEqual(slow[:5], [])


class Mutants(unittest.TestCase):
    def mutated(self, old, new):
        src = (SCRIPTS / "invite_clean.py").read_text(encoding="utf-8")
        self.assertIn(old, src)
        spec = importlib.util.spec_from_loader("invite_clean_accent_mutant", loader=None)
        mod = importlib.util.module_from_spec(spec)
        mod.__file__ = str(SCRIPTS / "invite_clean.py")
        exec(compile(src.replace(old, new, 1), "invite_clean_accent_mutant", "exec"), mod.__dict__)
        return mod

    def leaks(self, mod):
        return [t for t, v in REVIEWER_TITLES if v in mod.scrub(t, 140)] + [t for t, v in REVIEWER_BODIES
                                                                              if v in mod.invite_text("Agenda: budget\n" + t + "\nEnd")]

    def test_nfkc_restored(self):
        m = self.mutated('d = unicodedata.normalize("NFKD", _bounded(normal(text)))', "d = normal(text)")
        self.assertTrue(self.leaks(m))
        self.assertTrue(sweep_survivors(m)[1])

    def test_mark_strip_removed(self):
        m = self.mutated('(unicodedata.category(c) not in ("Mn", "Me", "Mc") or c in _KEEP_MARKS)', "True")
        self.assertTrue(self.leaks(m))

    def test_markdown_link_reading_removed(self):
        m = self.mutated("bases = ([linked] if linked != s else []) + [s]", "bases = [s]")
        self.assertIn("[Passcode](http://x.example.invalid)\nhunter\nok", [t for t, v in REVIEWER_BODIES if v in m.invite_text("Agenda: budget\n" + t + "\nEnd")])

    def test_kana_marks_dropped_breaks_japanese(self):
        m = self.mutated('_KEEP_MARKS = ("\\u3099", "\\u309a")', "_KEEP_MARKS = ()")
        self.assertIn("4417", m.scrub(OTHER_ALPHABETS[0][0], 140))


if __name__ == "__main__":
    unittest.main()
