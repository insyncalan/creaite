"""#375 E1, slice S1b SPEC TESTS for `invite_filter.drop_labelled_values` (the second layer on the body). Written before the code.

Run: python3 dev/tests/test_invite_filter_labels_spec.py      (quick tier: plain code)

Skipped with "invite_filter not built yet" until `system/scripts/invite_filter.py` exists (and, for the S1b classes, until it has
`drop_labelled_values`: "drop_labelled_values not built yet"). Fictional data only.

API under test (PLAN.md section 1, rule 7):
  drop_labelled_values(lines) -> list[int]      the KEPT indices, ascending (despite the name); `keep_indices` calls it last.

The rule, nothing else: a line whose skeleton (NFKC, invisible characters removed) holds a HARD LABEL from a fixed list, then a
separator (`: = - \\u2013 \\u2014 >`, the word `is`, or end of line), then a VALUE, goes. The labels:
  passcode, pass code, password, pwd, pin, otp, secret, token, api key, access code, meeting id, conference id, webinar id, host key
  and the provider-prefixed forms ("Zoom passcode", "Teams meeting ID", "Dial-in PIN", "Phone conference ID", ...).
A VALUE is: a token containing a digit, or a hex run of 6+, or a mixed letters-and-digits token (first token after the separator).
Same line, or (label ends the line, value absent) the NEXT NON-BLANK line, and only that one line.
NOT in the rule: soft-heading windows, word-only values ("Passcode: tuesday"), qualifier phrases ("Passcode for the room: 4417"),
glued labels, tombstones. A date or a time is never a value ("Password reset: 14-11-2026" cannot occur, but "Token refresh at 14:00",
"Lunch at 12:30" stay).

Mutant hooks for the builder (each must turn at least one test red; wire them in the mutation slice, S6):
  MUTANT-L1  rule off (drop_labelled_values returns every index)                     -> Positives, NextLine red
  MUTANT-L2  value shape widened to any word                                         -> Negatives.test_word_only_values_stay red
  MUTANT-L3  label matched anywhere inside a word ("Opinion: 4417", "Spinning")      -> Negatives.test_label_inside_a_word red
  MUTANT-L4  label list gains 'code' / 'key' / 'id' alone                            -> Negatives.test_near_miss_headings red
  MUTANT-L5  next line looked at even when a line separates them / two lines dropped -> NextLine red
  MUTANT-L6  soft-heading window added ('Joining details' drops its next 3 lines)    -> Negatives.test_soft_headings_have_no_window red
  MUTANT-L7  dates and times counted as values                                       -> Negatives.test_dates_and_times_stay red
  MUTANT-L8  successor decided on the ORIGINAL neighbours, not on what is left        -> Idempotent.test_exposed_successor red
  MUTANT-L9  an edit of the kept lines (strip, case)                                  -> Subset red
"""
import itertools
import random
import re
import signal
import sys
import time
import unicodedata
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parents[1] / "system" / "scripts"
sys.path.insert(0, str(SCRIPTS))


def _load():
    try:
        import invite_filter
        return invite_filter
    except ModuleNotFoundError as e:
        if e.name == "invite_filter":
            return None
        raise


F = _load()
needs_filter = unittest.skipUnless(F is not None, "invite_filter not built yet")
needs_labels = unittest.skipUnless(F is not None and hasattr(F, "drop_labelled_values"), "drop_labelled_values not built yet"
                                   if F is not None else "invite_filter not built yet")


def calibrate():
    best = 1e9
    text = "Budget review with the team and the plan for next week\n" * 40
    for _ in range(7):
        t0 = time.perf_counter()
        sum(1 for ln in text.split("\n") if re.search(r"\d{7}", ln))
        unicodedata.normalize("NFKC", text)
        best = min(best, time.perf_counter() - t0)
    return max(1.0, best / 0.0002)


SCALE = calibrate()
LIMIT = 0.5 * SCALE
ALARM = 5.0 * SCALE


def timed(fn, *args):
    def stop(*_a):
        raise TimeoutError("took more than %s s" % ALARM)
    old = signal.signal(signal.SIGALRM, stop)
    signal.setitimer(signal.ITIMER_REAL, ALARM)
    t0 = time.time()
    try:
        out = fn(*args)
        return time.time() - t0, out
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


def kept(lines):
    return [lines[i] for i in F.drop_labelled_values(lines)]


HARD_LABELS = ["passcode", "pass code", "password", "pwd", "pin", "otp", "secret", "token", "api key", "access code", "meeting id",
               "conference id", "webinar id", "host key"]
PREFIXED = ["Zoom passcode", "Teams meeting ID", "Webex access code", "Dial-in PIN", "Phone conference ID", "Google Meet PIN",
            "Zoom webinar ID", "Teams passcode", "Webex host key", "Conference dial-in PIN"]
SEPARATORS = [": ", ":", " = ", " - ", " – ", " — ", " > ", " is "]
VALUES = ["4417", "123456", "987 654 321", "a1b2c3", "aB3dE5", "x7Kp29Qz", "deadbeef01", "9", "A1"]


def cases_of(label):
    """The label in the capitalisations an invite uses."""
    return {label, label.upper(), label.title(), label.capitalize()}


# ---------------------------------------------------------------- positives

@needs_labels
class Positives(unittest.TestCase):
    def test_every_label_every_separator_every_value_on_the_same_line(self):
        for label, sep, value in itertools.product(HARD_LABELS, SEPARATORS, VALUES):
            line = f"{label.capitalize()}{sep}{value}"
            with self.subTest(line=line):
                self.assertEqual(kept(["Before", line, "After"]), ["Before", "After"])

    def test_capitalisation(self):
        for label in HARD_LABELS:
            for form in cases_of(label):
                with self.subTest(form=form):
                    self.assertEqual(kept([f"{form}: 4417"]), [])

    def test_provider_prefixed_forms(self):
        for label, sep in itertools.product(PREFIXED, [": ", " is ", " – "]):
            line = f"{label}{sep}4417"
            with self.subTest(line=line):
                self.assertEqual(kept(["Before", line, "After"]), ["Before", "After"])

    def test_label_with_markup_and_decoration_is_the_same_line(self):
        """Skeleton is decided on NFKC without invisible characters; the label may carry them."""
        for line in ["Pass​code: 4417", "PASSCODE: 4417", "Ｐｉｎ: 4417", "Meeting ID: 123 456 789"]:
            with self.subTest(line=line):
                self.assertEqual(kept(["Before", line, "After"]), ["Before", "After"])

    def test_other_script_digits_are_digits(self):
        for line in ["Passcode: ٤١١٧", "PIN: ４４１７", "Password: ४४१७"]:
            self.assertEqual(kept(["Before", line, "After"]), ["Before", "After"], line)

    def test_value_followed_by_more_words_on_the_same_line(self):
        self.assertEqual(kept(["Passcode: 4417 (expires tonight)"]), [])
        self.assertEqual(kept(["PIN is 4417, please keep it safe"]), [])

    def test_leading_text_before_the_label(self):
        self.assertEqual(kept(["Your meeting ID: 123 456 789"]), [])
        self.assertEqual(kept(["- Passcode: 4417"]), [])
        self.assertEqual(kept(["* PIN: 4417"]), [])
        self.assertEqual(kept(["Join with Passcode: aB3dE5"]), [])

    def test_two_labels_one_line(self):
        self.assertEqual(kept(["Meeting ID: 123 456 789 Passcode: aB3dE5"]), [])


@needs_labels
class NextLine(unittest.TestCase):
    """The label ends the line (a separator or not): the next NON-BLANK line goes when it is value-shaped, and only that line."""

    def test_label_then_value(self):
        for label, sep in itertools.product(HARD_LABELS, ["", ":", " -", " –", " >", " ="]):
            for value in ("4417", "aB3dE5", "987 654 321", "x7Kp29Qz"):
                lines = ["Before", f"{label.capitalize()}{sep}", value, "After"]
                with self.subTest(label=label, sep=sep, value=value):
                    self.assertEqual(kept(lines), ["Before", "After"])

    def test_blank_lines_between_are_skipped_and_kept(self):
        self.assertEqual(kept(["Before", "Passcode:", "", "", "4417", "After"]), ["Before", "", "", "After"])

    def test_only_one_line_goes(self):
        self.assertEqual(kept(["Passcode:", "4417", "5588", "After"]), ["5588", "After"])
        self.assertEqual(kept(["Passcode:", "4417", "Room 204"]), ["Room 204"])

    def test_next_line_not_value_shaped_keeps_both(self):
        for nxt in ["Please ask the organiser", "tuesday", "Next steps", "Lunch at 12:30", "12-11-2026", "14:00", "Room"]:
            with self.subTest(nxt=nxt):
                self.assertEqual(kept(["Passcode:", nxt]), ["Passcode:", nxt])

    def test_label_at_the_end_of_the_input(self):
        self.assertEqual(kept(["Agenda", "Passcode:"]), ["Agenda", "Passcode:"])
        self.assertEqual(kept(["Agenda", "Passcode:", "", ""]), ["Agenda", "Passcode:", "", ""])

    def test_a_label_with_a_value_on_its_own_line_takes_nothing_further(self):
        self.assertEqual(kept(["Passcode: 4417", "5588"]), ["5588"])

    def test_two_label_pairs(self):
        self.assertEqual(kept(["Meeting ID:", "123 456 789", "Passcode:", "aB3dE5", "Thanks"]), ["Thanks"])


# ---------------------------------------------------------------- negatives

@needs_labels
class Negatives(unittest.TestCase):
    def assertAllStay(self, lines):
        for ln in lines:
            with self.subTest(line=ln):
                self.assertEqual(kept(["Before", ln, "After"]), ["Before", ln, "After"])

    def test_near_miss_headings(self):
        self.assertAllStay(["Password reset", "Pin the roadmap", "Code of conduct", "Token refresh", "Key milestones", "Secret santa on Friday",
                            "Pin the roadmap by 12-11-2026", "Password policy review", "Token refresh at 14:00", "Code review at 10:30",
                            "Key decisions: go ahead", "Access control review", "Meeting notes", "Meeting ID card holders", "Host the next call"])

    def test_dates_and_times_stay(self):
        self.assertAllStay(["Lunch at 12:30", "Meeting on 12-11-2026 at 14:00", "Review: 14:00", "Deadline: 2026-11-12",
                            "Token refresh: 10.11.2026", "Starts 01-12-2026", "Phase 2 from 15:30 to 16:00", "Room 204", "Sprint 14"])

    def test_dates_and_times_under_a_label_stay(self):
        for label in ("Passcode", "PIN", "Token", "Password", "Meeting ID"):
            for value in ("12:30", "14-11-2026", "2026-11-14", "10.11.2026", "14:00-15:00"):
                with self.subTest(label=label, value=value):
                    self.assertEqual(kept([f"{label}: {value}"]), [f"{label}: {value}"])
                    self.assertEqual(kept([f"{label}:", value]), [f"{label}:", value])

    def test_word_only_values_stay(self):
        """Residual by decision: a word-only secret is not seen ('Code word: kqZxyw')."""
        self.assertAllStay(["Passcode: tuesday", "Password: hunter", "PIN: none", "Token: pending", "Meeting ID: TBC", "Secret: kqZxyw",
                            "Passcode: please ask the organiser", "Code word: kqZxyw", "Passcode:", "PIN - to follow"])

    def test_label_inside_a_word(self):
        self.assertAllStay(["Opinion: 4417", "Spinning: 4417", "Tokenised: a1b2c3", "Secretary: 4417", "Pinned: 4417", "Pinnacle: 4417",
                            "Hotpot: 4417"])

    def test_soft_headings_have_no_window(self):
        self.assertAllStay(["Joining details", "Security notes", "Access", "Dial-in", "Login information", "Credentials"])
        for head in ("Joining details", "Security notes", "Login information", "Credentials", "Dial-in details:"):
            with self.subTest(head=head):
                self.assertEqual(kept([head, "4417", "aB3dE5"]), [head, "4417", "aB3dE5"])

    def test_qualifier_phrases_are_out_of_scope(self):
        """Design pin: no qualifier phrases ('Passcode for the room: 4417' stays, a known residual)."""
        self.assertAllStay(["Passcode for the room: 4417", "Passcode (optional): 4417", "PIN to enter the building is 4417"])

    def test_no_glued_label_rule(self):
        self.assertAllStay(["Passcode4417", "PIN4417", "Tokenx9"])

    def test_label_without_a_value_stays_when_the_next_line_is_prose(self):
        self.assertEqual(kept(["Password:", "Choose a long one"]), ["Password:", "Choose a long one"])

    def test_ordinary_prose_is_untouched(self):
        prose = ["Review the budget for next quarter", "Agenda item 3: supplier update", "Budget 1,200,000 approved last year",
                 "Windows 11 upgrade plan", "Lunch at 12:30", "Version 2.6.9 release notes", "Ext 4417 for the front desk", "Next steps and owners"]
        self.assertEqual(kept(prose), prose)


# ---------------------------------------------------------------- P1, P2, timing

POOL = (["Review the budget", "Lunch at 12:30", "Room 204", "Password reset", "Pin the roadmap", "Code of conduct", "Token refresh", "Key milestones",
         "Opinion: 4417", "", "", "12-11-2026", "14:00", "Next steps", "tuesday", "Please ask the organiser", "Joining details"]
        + [f"{l.capitalize()}{s}{v}" for l in HARD_LABELS[:6] for s in (": ", " is ") for v in ("4417", "tuesday", "aB3dE5")]
        + [l.capitalize() + s for l in HARD_LABELS for s in (":", "")]
        + ["4417", "aB3dE5", "987 654 321", "x7Kp29Qz", "deadbeef01"])


@needs_labels
class Subset(unittest.TestCase):
    """P1: kept indices ascending and unique; the kept lines are the input lines unchanged."""

    def test_generated(self):
        rnd = random.Random(375)
        for n in range(1500):
            lines = [rnd.choice(POOL) for _ in range(rnd.randint(1, 25))]
            idx = F.drop_labelled_values(lines)
            with self.subTest(body=n):
                self.assertEqual(idx, sorted(set(idx)))
                self.assertTrue(all(0 <= i < len(lines) for i in idx))
                self.assertEqual([lines[i] for i in idx], kept(lines))

    def test_kept_lines_are_not_rewritten(self):
        lines = ["  Padded  ", "Café — “quoted”", "UPPER lower", "Passcode: 4417", "tab\tsep"]
        self.assertEqual(kept(lines), [lines[0], lines[1], lines[2], lines[4]])

    def test_input_not_mutated(self):
        lines = ["Passcode:", "4417", "Next"]
        before = list(lines)
        F.drop_labelled_values(lines)
        self.assertEqual(lines, before)

    def test_empty(self):
        self.assertEqual(F.drop_labelled_values([]), [])
        self.assertEqual(F.drop_labelled_values([""]), [0])


@needs_labels
class Idempotent(unittest.TestCase):
    """P2: the pair rule is idempotent: running it on its own output changes nothing."""

    def test_generated(self):
        rnd = random.Random(376)
        for n in range(2000):
            lines = [rnd.choice(POOL) for _ in range(rnd.randint(1, 25))]
            once = kept(lines)
            with self.subTest(body=n):
                self.assertEqual(kept(once), once, lines)

    def test_exposed_successor(self):
        """A kept label whose successor is later removed must not expose a new value-shaped successor on the next pass.
        'Passcode:' is followed by 'Pin: 4417' (removed as a label with its value), which exposes '5588' under 'Passcode:'. Either pass one
        drops '5588' too, or pass two must keep it: what is pinned here is that the result is stable (see the report's ambiguity 3)."""
        for lines in (["Passcode:", "Pin: 4417", "5588", "After"], ["Passcode:", "", "Pin:", "4417", "5588"], ["Token", "Secret: x9", "aB3dE5"]):
            once = kept(lines)
            self.assertEqual(kept(once), once, lines)

    def test_filter_wide_idempotence_with_the_second_layer(self):
        """Through keep_lines (anchor layer, shape gate, then this layer)."""
        rnd = random.Random(377)
        extra = ["https://meet.example.test/j/1", "________", "Dial ,,123456789#", "aB3dE5x9"]
        for n in range(1000):
            lines = [rnd.choice(POOL + extra) for _ in range(rnd.randint(1, 25))]
            once = F.keep_lines(lines)
            with self.subTest(body=n):
                self.assertEqual(F.keep_lines(once), once, lines)
                self.assertEqual([lines[i] for i in F.keep_indices(lines)], once)


@needs_labels
class SecondLayerIsLast(unittest.TestCase):
    def test_keep_indices_calls_it_last(self):
        """With the second layer on, keep_indices is the second layer applied to what the anchor layer left; off, the anchor layer alone."""
        lines = ["Agenda", "", "Passcode: 4417", "", "Dial ,,123456789#", "", "Closing"]     # blank line: else Closing is in the dropped block
        on = F.keep_lines(lines, second_layer=True)
        off = F.keep_lines(lines, second_layer=False)
        self.assertNotIn("Passcode: 4417", on)
        self.assertIn("Passcode: 4417", off)
        self.assertNotIn("Dial ,,123456789#", off)
        self.assertEqual([x for x in on if x], ["Agenda", "Closing"])


@needs_labels
class Timing(unittest.TestCase):
    def test_hostile_inputs(self):
        bodies = {
            "labels-same-line": ["Passcode: " * 2000], "label-lines": ["Passcode:"] * 5000, "label-blank-lines": ["Passcode:", *([""] * 20000)],
            "separators": ["Passcode" + ": " * 10000], "dots": ["Password" + "." * 20000], "dot-space": ["Password " + ". " * 10000],
            "words": ["word " * 4000], "pin-run": ["pin " * 5000], "alternating": ["Passcode:", "4417"] * 5000, "dashes": ["PIN" + " - " * 7000],
            "long-token": ["Token: " + "a1" * 10000], "hex": ["Token: " + "deadbeef" * 2500],
        }
        slow = []
        for name, lines in bodies.items():
            took, _ = timed(F.drop_labelled_values, lines)
            if took > LIMIT:
                slow.append((round(took, 3), name))
        self.assertEqual(slow, [], f"over {LIMIT} s")

    def test_seeded_fuzz(self):
        rnd = random.Random(375)
        atoms = HARD_LABELS + [":", " ", "-", "–", "is", "4417", "a1b2", ".", "\n", "x", "_", "​"]
        slow = []
        for _ in range(1500):
            text = "".join(rnd.choice(atoms) * rnd.randint(1, 20) for _ in range(rnd.randint(5, 60)))[:400]
            took, _ = timed(F.drop_labelled_values, text.split("\n"))
            if took > LIMIT:
                slow.append((round(took, 3), text[:60]))
        self.assertEqual(slow[:5], [])

    def test_linear_growth(self):
        base = ["Review the budget", "Passcode:", "4417", "", "Password reset", "Token: tuesday"] * 100
        t1 = min(timed(F.drop_labelled_values, base)[0] for _ in range(3))
        t10 = min(timed(F.drop_labelled_values, base * 10)[0] for _ in range(3))
        self.assertLess(t10, max(t1 * 40, 0.05 * SCALE))


if __name__ == "__main__":
    unittest.main()
