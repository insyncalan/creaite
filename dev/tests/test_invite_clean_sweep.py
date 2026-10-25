"""2.6.8 generic sweep: no secret survives however the labels are strung together.

Run: python3 dev/tests/test_invite_clean_sweep.py      (quick tier: plain code, a few seconds)

Findings in this area came one at a time (two labels in a row, blank lines between, table cells). This test strings the label forms of
invite_clean together instead: for every single form and every PAIR of forms, and a seeded sample (seed 232) of TRIPLES, joined by one
line break, then by three and by six blank lines, and as bare <td> / <li> fragments, and as one line for scrub, followed by a value
('hunter', 'swordfish', 'xk7q'), the value never survives invite_text or scrub. The forms are the covered ones; the labels that are
documented limits (Key, Access, Login, Credentials, Pass, Codice, Codigo, Sifre, Parola, a value before its label; see NOT_COVERED in
test_invite_clean_bare.py and NOTES-2.6.8.md) are not in the lists. Mutant: a label alone no longer counts the labels in a row.
"""
import importlib.util
import itertools
import random
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parents[1] / "system" / "scripts"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SCRIPTS))
import invite_clean as I  # noqa: E402

ALONE = ["Passcode:", "Passcode", "PIN:", "Password:", "Meeting ID:", "Host key:", "Access code:", "Dial-in code:", "Pwd:", "Passphrase:",
         "Conference ID:", "Join code:", "Key:"]
SEPARATED = ["Password -", "Pw:", "Pswd =", "Token –", "Secret |", "API key /", "PIN (", "Code —"]
PHRASES = ["Password reset", "PIN entry", "Code review", "Token refresh", "Secret manager", "OTP setup", "Password reset for", "Code of",
           "API key rotation", "Password change request"]
FORMS = ALONE + SEPARATED + PHRASES
VALUES = ["hunter", "swordfish", "xk7q"]
GAPS = ["\n", "\n" * 4, "\n" * 7]
TRIPLES = 300


def combos():
    singles = [(f,) for f in FORMS]
    pairs = list(itertools.product(FORMS, repeat=2))
    triples = random.Random(232).sample(list(itertools.product(FORMS, repeat=3)), TRIPLES)
    return singles + pairs + triples


COMBOS = combos()


def survivors(mod):
    """(how many combinations were tried, the ones whose value survived)."""
    n, bad = 0, []
    for forms in COMBOS:
        for v in VALUES:
            fill = ["123 456"] * max(sum(f in ALONE for f in forms) - 1, 0)       # a label alone has a value of its own: the last is v
            cases = [("lines", g, mod.invite_text("Agenda: budget\n" + g.join(forms) + g + g.join([*fill, v]) + "\nEnd")) for g in GAPS]
            cases.append(("td", "", mod.invite_text("<td>" + "</td><td>".join(forms) + "</td><td>" + "</td><td>".join([*fill, v]) + "</td>")))
            cases.append(("td-rows", "", mod.invite_text("<table>" + "".join(f"<tr><td>{f}</td></tr>" for f in (*forms, *fill, v)) + "</table>")))
            cases.append(("li", "", mod.invite_text("<ul><li>" + "</li><li>".join(forms) + "</li><li>" + "</li><li>".join([*fill, v]) + "</li></ul>")))
            cases.append(("field", "", mod.scrub(" ".join(forms) + " " + v, 140)))
            for kind, gap, out in cases:
                n += 1
                if v in out:
                    bad.append((kind, len(gap), forms, v))
    return n, bad


def separators():
    """Every character of BARE_SEPARATORS' own list, the words that may follow a label, and a seeded sample (seed 232) of Unicode
    punctuation and symbols (categories P* and S*) that are not sentence ends."""
    import unicodedata
    fixed = ["-", "\u2013", "\u2014", ":", "=", "#", "(", "[", "/", "|", "~", "\u2192", ":-", "is", "is:", "are", "- -", "::", "\u2022", "*", ">"]
    def stays(c):                                   # a symbol that NFKC turns into a letter or digit (a Kangxi radical) is a word, not a separator
        n = unicodedata.normalize("NFKC", c)
        return len(n) == 1 and unicodedata.category(n)[0] in "PS" and n not in ".,;!?"
    pool = [c for c in map(chr, range(0x21, 0x3000)) if unicodedata.category(c)[0] in "PS" and stays(c)]
    return fixed + random.Random(232).sample(pool, 40)


SEPS = separators()
SENTENCE_ENDS = [".", "!", "?", "\u2026", ",", ";", "..", "?!", "!!!"]


def sentence_end_runs():
    """A separator with 1 to 3 sentence-end marks before, after and between ('.:', ':!', '?:.', ': .', ...'), and the ellipsis forms."""
    out = ["...", "\u2026", ". . .", "....", ": .", ": . !", "- .", "\u2013 ?"]
    rnd = random.Random(232)
    for sep in [":", "-", "\u2013", "=", "|", "/", "(", "#", "\u2192", "~"]:
        for _ in range(6):
            pre = "".join(rnd.choice(SENTENCE_ENDS) for _ in range(rnd.randint(0, 2)))[:3]
            post = "".join(rnd.choice(SENTENCE_ENDS) for _ in range(rnd.randint(0, 2)))[:3]
            out.append(pre + sep + post)
        out += ["." + sep, sep + ".", "?" + sep, sep + "!", "." + sep + "!"]
    return out


SEPS = SEPS + sentence_end_runs()


def label_sep_survivors(mod):
    n, bad = 0, []
    labels = [f for f in ALONE if f.endswith(":")]
    for label, sep in itertools.product(labels, SEPS):
        form = label[:-1] + " " + sep
        for v in VALUES:
            for gap in GAPS:
                cases = [("lines", mod.invite_text("Agenda: budget\n" + form + gap + v + "\nok\nEnd")),
                         ("td", mod.invite_text("<td>" + form + "</td><td>" + v + "</td>")),
                         ("li", mod.invite_text("<ul><li>" + form + "</li><li>" + v + "</li></ul>"))]
                for kind, out in cases:
                    n += 1
                    if v in out:
                        bad.append((kind, form, len(gap), v))
    return n, bad


class Sweep(unittest.TestCase):
    def test_every_label_with_every_separator(self):
        n, bad = label_sep_survivors(I)
        self.assertGreater(n, 5000)
        self.assertEqual(bad[:8], [], f"{len(bad)} of {n} combinations leak")

    def test_the_separator_sweep_sees_a_narrow_class(self):
        """Mutant: the separator class reduced back to [:=#] leaks."""
        src = (SCRIPTS / "invite_clean.py").read_text(encoding="utf-8")
        old = 'BARE_SEPARATORS = r"[^\\w\\s.,;!?]"'
        self.assertIn(old, src)
        spec = importlib.util.spec_from_loader("invite_clean_narrow", loader=None)
        mod = importlib.util.module_from_spec(spec)
        mod.__file__ = str(SCRIPTS / "invite_clean.py")
        exec(compile(src.replace(old, 'BARE_SEPARATORS = r"[:=#]"', 1), "invite_clean_narrow", "exec"), mod.__dict__)
        _n, bad = label_sep_survivors(mod)
        self.assertTrue(bad)


    def test_no_value_survives_any_string_of_labels(self):
        n, bad = survivors(I)
        self.assertGreater(n, 20000)
        self.assertEqual(bad[:8], [], f"{len(bad)} of {n} combinations leak")

    def test_the_sweep_sees_a_leak(self):
        """Mutant: labels in a row no longer add up (a stand-alone label is one value long again): the sweep finds leaks."""
        src = (SCRIPTS / "invite_clean.py").read_text(encoding="utf-8")
        old = "            pending += 1                       # \"Meeting ID:\" then \"Passcode:\": a label never uses up another's value"
        self.assertIn(old, src)
        spec = importlib.util.spec_from_loader("invite_clean_sweep_mutant", loader=None)
        mod = importlib.util.module_from_spec(spec)
        mod.__file__ = str(SCRIPTS / "invite_clean.py")
        exec(compile(src.replace(old, "            pending = 1", 1), "invite_clean_sweep_mutant", "exec"), mod.__dict__)
        _n, bad = survivors(mod)
        self.assertTrue(bad)


if __name__ == "__main__":
    unittest.main()
