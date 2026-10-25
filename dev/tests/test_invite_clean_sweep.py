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
FINISHED = {"Password reset", "PIN entry", "Code review", "Token refresh", "Secret manager", "OTP setup", "API key rotation", "Password change request"}
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
            if forms[-1] in FINISHED and not any(c.isdigit() for c in v):
                continue           # KNOWN LIMIT (Alan's option B): a word-only secret right under a soft heading stays
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
    fixed = ["-", "\u2013", "\u2014", ":", "=", "#", "(", "[", "/", "|", "\u2192", ":-", "is", "is:", "are", "- -", "::", "\u2022", ">"]
    def stays(c):                                   # a symbol that NFKC turns into a letter or digit (a Kangxi radical) is a word, not a separator
        n = unicodedata.normalize("NFKC", c)
        return len(n) == 1 and unicodedata.category(n)[0] in "PS" and n not in ".,;!?"
    pool = [c for c in map(chr, range(0x21, 0x3000)) if unicodedata.category(c)[0] in "PS" and stays(c) and c not in "*~`"]      # (wrappers: decoration sweep)
    return fixed + random.Random(232).sample(pool, 40)


SEPS = separators()
SENTENCE_ENDS = [".", "!", "?", "\u2026", ",", ";", "..", "?!", "!!!"]


def sentence_end_runs():
    """A separator with 1 to 3 sentence-end marks before, after and between ('.:', ':!', '?:.', ': .', ...'), and the ellipsis forms."""
    out = ["...", "\u2026", ". . .", "....", ": .", ": . !", "- .", "\u2013 ?"]
    rnd = random.Random(232)
    for sep in [":", "-", "\u2013", "=", "|", "/", "(", "#", "\u2192"]:
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


CORES = ["Passcode", "PIN", "Password", "Meeting ID", "Pass code", "Host key", "Access code", "Webinar ID", "Pw", "Pswd", "Token", "Secret",
         "OTP", "Code", "API key", "Key", "Access", "Pwd", "Join code", "Zoom ID"]
WRAPPERS = ["_", "*", "~", "`"]
NEEDS_SEPARATOR = {"Key", "Access"}          # "Key hunter" alone is an ordinary phrase: documented limit; with a separator they are labels


def decorated_survivors(mod):
    """Labels wrapped in runs of 0 to 3 of each wrapper (_ * ~ `) on both sides, with a separator or not, a value on the same line or the next."""
    n, bad = 0, []
    for core, w, pre, suf in itertools.product(CORES, WRAPPERS, range(4), range(4)):
        if pre == 0 and suf == 0 and w != "_":
            continue
        label = w * pre + core + w * suf
        for tail in (":", " -", "") if core not in NEEDS_SEPARATOR else (":", " -"):
            for v in ("hunter", "4417"):
                if tail == "" and v == "hunter" and core in ("Meeting ID", "Webinar ID", "Zoom ID", "PIN"):
                    continue                     # "Meeting ID hunter": an ID word is not a value without a digit or a separator (documented)
                cases = [("scrub", mod.scrub(label + tail + " " + v, 140)),
                         ("line", mod.invite_text("Agenda: budget\n" + label + tail + " " + v + "\nEnd")),
                         ("td", mod.invite_text("<td>" + label + tail + "</td><td>" + v + "</td>"))]
                if tail:
                    cases += [("next", mod.invite_text("Agenda: budget\n" + label + tail + "\n" + v + "\nEnd")),
                              ("li", mod.invite_text("<ul><li>" + label + tail + "</li><li>" + v + "</li></ul>"))]
                for kind, out in cases:
                    n += 1
                    if v in out:
                        bad.append((kind, label + tail, v))
    return n, bad


def dashes():
    """Every dash-like character: all of Unicode category Pd, the minus sign and the non-breaking hyphen."""
    import unicodedata
    return [c for c in map(chr, range(0x20, 0x11000)) if unicodedata.category(c) == "Pd" or c in "\u2212\u2011\u2010"]


DASHES = dashes()
DASH_LABELS = ["Passcode", "Meeting ID", "Password", "Token", "PIN", "Pwd", "Access code", "API key", "Host key", "Webinar ID", "Secret", "Code",
               "Key", "Access", "Pass code", "Conf ID"]
DASH_VALUES = ["4417", "ZQ7742", "hunter", "987654321"]


def dash_survivors(mod):
    n, bad = 0, []
    for lab, d, v in itertools.product(DASH_LABELS, DASHES, DASH_VALUES):
        for form in (f"{lab}{d}{v}", f"{lab}{d} {v}", f"{lab} {d}{v}", f"{lab} {d} {v}"):
            cases = [("title", mod.scrub(form, 140)), ("body", mod.invite_text("Agenda: budget\n" + form + "\nEnd")),
                     ("td", mod.invite_text("<td>" + form + "</td>")), ("li", mod.invite_text("<ul><li>" + form + "</li></ul>"))]
            for kind, out in cases:
                n += 1
                if v in out:
                    bad.append((kind, form))
    return n, bad


PROVIDERS = ["Zoom", "Teams", "Webex", "Meet", "GoTo", "Skype", "Bluejeans"]
PROVIDER_LABELS = ["Passcode", "PIN", "ID", "Password", "Meeting ID"]
PROVIDER_VALUES = ["4417", "ZQ7742", "hunter", "987 654 321"]


def provider_survivors(mod):
    """A provider glued to a label: hyphenated, glued, camelCase, snake_case, spaced; with a colon, a space, a dash or on the next line; a
    digit, a mixed-case and a word value; in a title, a body, a table cell and a list item. "ID hunter" (an ID label and a plain word with no
    separator) is a known limit and is left out."""
    n, bad = 0, []
    for p, lab in itertools.product(PROVIDERS, PROVIDER_LABELS):
        words = lab.split()
        forms = [f"{p}-{lab}", f"{p}{''.join(words)}", f"{p}_{'_'.join(words)}", f"{p} {lab}", f"{p}-{''.join(words)}", f"{p.lower()}-{lab.lower()}"]
        for form, sep, v in itertools.product(forms, (": ", " ", "-", ":\n", " - "), PROVIDER_VALUES):
            if lab.endswith("ID") and sep == " " and v == "hunter":
                continue
            text = form + sep + v
            one_line = text.replace("\n", " ")
            cases = [mod.scrub(text, 140), mod.invite_text("Agenda\n" + text + "\nEnd"), mod.invite_text("<td>" + form + sep.replace("\n", " ") + "</td><td>" + v + "</td>")]
            if sep in (": ", ":\n", " - "):
                cases.append(mod.invite_text("<ul><li>" + form + sep.strip(" \n") + "</li><li>" + v + "</li></ul>"))
            n += len(cases)
            if any(v in c for c in cases):
                bad.append(one_line)
    return n, bad


class Sweep(unittest.TestCase):
    def test_provider_prefixed_labels(self):
        n, bad = provider_survivors(I)
        self.assertGreater(n, 12000)
        self.assertEqual(bad[:6], [], f"{len(bad)} of {n} combinations leak")

    def test_provider_sweep_sees_a_missing_split(self):
        """Mutant: the hyphen-before-a-label and camelCase reading removed."""
        src = (SCRIPTS / "invite_clean.py").read_text(encoding="utf-8")
        old = '    out = _CAMEL.sub(" ", _HYPHEN_LABEL.sub(" ", text))\n    return out if out != text else ""'
        self.assertIn(old, src)
        spec = importlib.util.spec_from_loader("invite_clean_nosplit", loader=None)
        mod = importlib.util.module_from_spec(spec)
        mod.__file__ = str(SCRIPTS / "invite_clean.py")
        exec(compile(src.replace(old, '    return ""', 1), "invite_clean_nosplit", "exec"), mod.__dict__)
        self.assertTrue(provider_survivors(mod)[1])

    def test_every_dash_glued_or_spaced_to_a_label(self):
        n, bad = dash_survivors(I)
        self.assertGreater(n, 15000)
        self.assertEqual(bad[:8], [], f"{len(bad)} of {n} combinations leak")

    def test_compound_words_stay(self):
        for t in ("Password-based login", "PIN-protected doors", "Code-review", "Key-account plan", "Token-based auth", "Secret-free zone"):
            self.assertEqual(I.scrub(t, 140), t, t)

    def test_the_dash_sweep_sees_a_missing_rule(self):
        """Mutant: the glued-dash rule removed."""
        src = (SCRIPTS / "invite_clean.py").read_text(encoding="utf-8")
        old = '-(?:[\\s-]+|(?!(?:{GLUE_OK})(?![\\w-])))[^\\W_]"'
        self.assertIn(old, src)
        spec = importlib.util.spec_from_loader("invite_clean_noglue", loader=None)
        mod = importlib.util.module_from_spec(spec)
        mod.__file__ = str(SCRIPTS / "invite_clean.py")
        exec(compile(src.replace(old, '-(?!)[^\\W_]"', 1), "invite_clean_noglue", "exec"), mod.__dict__)
        self.assertTrue(dash_survivors(mod)[1])

    def test_decorated_labels(self):
        n, bad = decorated_survivors(I)
        self.assertGreater(n, 15000)
        self.assertEqual(bad[:8], [], f"{len(bad)} of {n} combinations leak")

    def test_the_decoration_sweep_sees_a_missing_normalisation(self):
        """Mutant: the underscore / wrapper reading removed: the sweep finds leaks."""
        src = (SCRIPTS / "invite_clean.py").read_text(encoding="utf-8")
        old = '[_DECORATION.sub(" ", x) for x in bases if _DECORATION.search(x)] + split + bases'
        self.assertIn(old, src)
        spec = importlib.util.spec_from_loader("invite_clean_nodeco", loader=None)
        mod = importlib.util.module_from_spec(spec)
        mod.__file__ = str(SCRIPTS / "invite_clean.py")
        exec(compile(src.replace(old, "bases", 1), "invite_clean_nodeco", "exec"), mod.__dict__)
        _n, bad = decorated_survivors(mod)
        self.assertTrue(bad)


    def test_every_label_with_every_separator(self):
        n, bad = label_sep_survivors(I)
        self.assertGreater(n, 5000)
        self.assertEqual(bad[:8], [], f"{len(bad)} of {n} combinations leak")

    def test_the_separator_sweep_sees_a_narrow_class(self):
        """Mutant: the separator class reduced back to [:=#] leaks."""
        src = (SCRIPTS / "invite_clean.py").read_text(encoding="utf-8")
        old = 'BARE_SEPARATORS = r"[^\\w\\s.,;!?*~`]"'
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
        old = "        return pending + _label_count(ln)"
        self.assertIn(old, src)
        spec = importlib.util.spec_from_loader("invite_clean_sweep_mutant", loader=None)
        mod = importlib.util.module_from_spec(spec)
        mod.__file__ = str(SCRIPTS / "invite_clean.py")
        exec(compile(src.replace(old, "        return 1", 1), "invite_clean_sweep_mutant", "exec"), mod.__dict__)
        _n, bad = survivors(mod)
        self.assertTrue(bad)


if __name__ == "__main__":
    unittest.main()
