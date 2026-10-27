"""#375 E1, S1: extra tests for `system/scripts/invite_filter.py` beyond the two spec files.

Run: python3 dev/tests/test_invite_filter_props.py      (quick tier: plain code, about half a minute)

  Props     P1 subset, P2 idempotent, P3 no digit run of 7+ survives, P4 locality, on 50,000 seeded random bodies
  Decisions the decisions taken for the build: date shapes first, a divider ends the block above it, dividers and blank lines
            around a dropped block are kept, BODY_MAX is cut at a line end, the second layer's boundaries
  Shape     an independent character-class oracle for the shape gate
  Hostile   timing on inputs aimed at each regex (the spec files cover the generic ones)
Fictional data only.
"""
import random
import signal
import sys
import time
import unicodedata
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "system" / "scripts"))
import invite_filter as F    # noqa: E402

N = 50000


def nd_run(line):
    """Longest run of consecutive decimal digits (Nd), invisible characters ignored (independent of the module)."""
    best = cur = 0
    for ch in line:
        c = unicodedata.category(ch)
        if c == "Cf":
            continue
        cur = cur + 1 if c == "Nd" else 0
        best = max(best, cur)
    return best


WORDS = ["review", "budget", "plan", "Agenda", "Room", "team", "next", "steps", "owner", "Lunch", "at", "the", "supplier", "update", "Phase"]
ATOMS = [
    "Review the budget for next quarter", "Room 204", "Lunch at 12:30", "Meeting on 12-11-2026 at 14:00", "2026-11-12", "10.11.26",
    "Budget 1,200,000", "Version 2.6.9", "Passcode: 4417", "Passcode:", "Pin", "PIN is 4417", "Meeting ID:", "987 654 321", "4417",
    "aB3dE5x9", "deadbeef", "https://meet.example.test/j/1", "tel:+441234567", "Dial ,,123456789#", "1234567", "+44 20 7946 0000",
    "٤٤١٧٤٤١٧", "1​2​3​4​5​6​7", "Token refresh at 14:00", "Opinion: 4417",
    "", "", "", "________", "- - - -", "====", "───", "--", "Password reset: 4417", "Secret: x9", "token", "x7Kp29Qz",
]


def gen_body(rnd, atoms=ATOMS):
    """One random body: atoms from the pool and random word lines."""
    out = []
    for _ in range(rnd.randint(1, 30)):
        if rnd.random() < 0.3:
            out.append(" ".join(rnd.choice(WORDS) for _ in range(rnd.randint(1, 8))))
        else:
            out.append(rnd.choice(atoms))
    return out


class Props(unittest.TestCase):
    def test_p1_p2_p3_on_50000_bodies(self):
        rnd = random.Random(2026)
        for n in range(N):
            lines = gen_body(rnd)
            on = F.keep_indices(lines)
            off = F.keep_indices(lines, second_layer=False)
            self.assertEqual(on, sorted(set(on)), n)
            self.assertTrue(set(on) <= set(off), n)                                     # the second layer only removes
            for kw, idx in (({}, on), ({"second_layer": False}, off)):
                out = [lines[i] for i in idx]
                self.assertEqual(F.keep_lines(out, **kw), out, (n, lines))             # P2
                self.assertTrue(all(nd_run(x) < 7 for x in out), (n, lines))           # P3

    def test_p4_locality(self):
        """Shuffling blocks (blank-separated, no dividers, anchor layer only) keeps the same survivors."""
        atoms = [a for a in ATOMS if a and not F._is_divider(a)]
        rnd = random.Random(2027)
        for n in range(3000):
            blocks = [[rnd.choice(atoms) for _ in range(rnd.randint(1, 4))] for _ in range(rnd.randint(2, 6))]
            a = sorted(sum((F.keep_lines(b, second_layer=False) for b in blocks), []))
            rnd.shuffle(blocks)
            flat = []
            for b in blocks:
                flat += b + [""]
            b = sorted(x for x in F.keep_lines(flat, second_layer=False) if x)
            self.assertEqual(a, b, n)

    def test_text_api_idempotent_and_capped(self):
        rnd = random.Random(2028)
        for n in range(3000):
            lines = gen_body(rnd) * rnd.randint(1, 30)
            out = F.filter_text("\n".join(lines))
            self.assertLessEqual(len(out), F.CAP)
            self.assertEqual(F.filter_text(out), out, n)
            self.assertEqual(F.filter_text(out, second_layer=False), F.filter_text(out, second_layer=False))


class Decisions(unittest.TestCase):
    def kept(self, *lines):
        return [x for x in F.keep_lines(list(lines), second_layer=False) if x.strip()]

    def test_dates_stay_and_other_long_digit_runs_go(self):
        for ln in ("12-11-2026", "2026-11-12", "12.11.26", "Due 12-11-2026 14:00", "2026-11-12 14:00 to 15:30", "12/11/2026 and 13/11/2026"):
            self.assertEqual(self.kept("Keep", "", ln), ["Keep", ln], ln)
        for ln in ("12-11-2026-5551234", "5551234 2026-11-12", "99.99.9999 12", "40.13.2026 1234567"):
            self.assertEqual(self.kept("Keep", "", ln), ["Keep"], ln)

    def test_six_digits_and_commas(self):
        for ln in ("Ref 123456", "Budget 1,200,000", "Total 12,345,678", "1,2,3,4,5,6,7,8"):
            self.assertEqual(self.kept(ln), [ln], ln)

    def test_a_divider_ends_the_block_above_it(self):
        self.assertEqual(self.kept("Keep me", "________", "Call 12345678"), ["Keep me", "________"])
        self.assertEqual(self.kept("Keep me", "Call 12345678"), [])                        # no divider: one block

    def test_dividers_and_blanks_around_a_dropped_block_are_kept(self):
        lines = ["A", "", "________", "", "Dial 12345678", "", "________", "", "B"]
        self.assertEqual(F.keep_lines(lines, second_layer=False), ["A", "", "________", "", "", "________", "", "B"])

    def test_body_max_cut_is_at_a_line_end(self):
        import invite_clean
        self.assertEqual(F.BODY_MAX, invite_clean.BODY_MAX)
        line = "word " * 7 + "end"                                                        # 38 characters
        text = "\n".join([line] * 1000)
        out = F.filter_text(text)
        self.assertTrue(all(x == line for x in out.split("\n")))
        late = "\n".join(["ok"] * 9000) + "\nDial 12345678"                              # 27,000 characters; anchor after the cut
        self.assertEqual(F.filter_text(late), "\n".join(["ok"] * 9000)[:0] + F.filter_text("\n".join(["ok"] * 9000)))
        self.assertEqual(F.filter_text("x" * 30000), "")                                   # one huge line: nothing fits

    def test_second_layer_boundaries(self):
        kept = F.drop_labelled_values
        self.assertEqual(kept(["Opinion: 4417"]), [0])
        self.assertEqual(kept(["Password reset: 4417"]), [0])                              # the label must be last before the separator
        self.assertEqual(kept(["Reset the password: 4417"]), [])                           # ... and is, here
        self.assertEqual(kept(["Pin: tuesday 4417"]), [0])                                 # judged on the first token only
        self.assertEqual(kept(["Pin: 4417 tuesday"]), [])
        self.assertEqual(kept(["Passcode:", "________", "4417"]), [0, 1, 2])             # a divider line separates them
        self.assertEqual(kept(["Passcode: 12:30", "Pin: 2026-11-12"]), [0, 1])
        self.assertEqual(kept(["Token: deadbeef"]), [])                                    # a hex run of 6+ is a value
        self.assertEqual(kept(["Token: beef"]), [0])

    def test_label_must_start_at_a_word_and_be_a_hard_label(self):
        """Words that END in a label, and short labels that are not on the list ('code', 'key', 'id'), do not trigger the rule."""
        for ln in ("Spin: 4417", "Hotpin: 4417", "Taxtoken: 4417", "Product code: 4417", "Customer ID: 4417", "Room key: 4417",
                   "Hotkey: 4417", "Door code - 4417", "Order id is 4417"):
            self.assertEqual(F.drop_labelled_values([ln]), [0], ln)
            self.assertEqual(F.drop_labelled_values([ln.split(":")[0].split(" -")[0].split(" is")[0], "4417"]), [0, 1], ln)

    def test_chain_of_pairs_is_stable(self):
        lines = ["Passcode:", "Pin:", "4417", "5588", "Closing"]
        once = [lines[i] for i in F.drop_labelled_values(lines)]
        self.assertEqual(once, ["Closing"])
        self.assertEqual([once[i] for i in F.drop_labelled_values(once)], once)

    def test_confusable_letters_do_not_hide_a_label(self):
        self.assertEqual(F.drop_labelled_values(["Рassсode: 4417"]), [])        # Cyrillic Er and Es


class Shape(unittest.TestCase):
    """An independent character-class oracle for the shape gate (a lone token on a line, second layer off)."""

    @staticmethod
    def oracle_drops(tok):
        digits = sum(c.isdigit() for c in tok)
        letters = sum(c.isalpha() for c in tok)
        longest = cur = 0
        for c in tok:
            cur = cur + 1 if c.isdigit() else 0
            longest = max(longest, cur)
        if longest >= 7:                                                                    # the anchor layer, not the gate
            return True
        if letters == 0 and digits == len(tok):
            return len(tok) >= 5
        if digits and letters and digits + letters == len(tok):
            return len(tok) >= 6
        if letters == len(tok) and len(tok) >= 8:
            run = cur = 0
            for c in tok.lower():
                cur = 0 if c in "aeiouy" else cur + 1
                run = max(run, cur)
            return run >= 8
        return False

    def test_random_tokens_agree_with_the_oracle(self):
        rnd = random.Random(375)
        alphabets = ["0123456789", "0123456789abcdef", "abcdefghijklmnopqrstuvwxyz", "bcdfghjklmnpqrstvwxz", "aeiouy",
                     "abcXYZ0123", "AbCdEfGh1234"]
        for _ in range(20000):
            tok = "".join(rnd.choice(rnd.choice(alphabets)) for _ in range(rnd.randint(1, 14)))
            self.assertEqual(F.keep_lines([tok], second_layer=False) == [], self.oracle_drops(tok), tok)

    def test_the_gate_leaves_words_dates_and_short_numbers(self):
        for ln in ("Agenda", "tuesday", "Wednesday", "strengths", "2026", "4417", "12-11-2026", "14:00", "AOB", "Q4", "v2.6.9", "Room204x"[:5]):
            self.assertEqual(F.keep_lines([ln], second_layer=False), [ln], ln)

    def test_the_gate_drops_ids_and_blobs(self):
        for ln in ("aB3dE5", "x7Kp29Qz", "123456", "bcdfghjklm", "A1b2C3d4E5f6", "QUJD" * 100):
            self.assertEqual(F.keep_lines([ln], second_layer=False), [], ln)

    def test_cjk_and_accents_are_never_gated(self):
        for ln in ("会議の準備" * 60, "اجتماع" * 50, "Caféréunion", "2026年11月12日"):
            self.assertEqual(F.keep_lines([ln], second_layer=False), [ln])


class Hostile(unittest.TestCase):
    """Inputs aimed at each regex. Each must finish well inside the spec files' per-body limit."""

    def run_all(self, bodies):
        limit = 0.5
        for name, lines in bodies.items():
            signal.alarm(10)
            t0 = time.perf_counter()
            F.keep_indices(lines)
            took = time.perf_counter() - t0
            signal.alarm(0)
            self.assertLess(took, limit, name)

    def test_regex_killers(self):
        self.run_all({
            "dot-labels": ["a." * 10000], "dot-labels-slash": ["a." * 9990 + "b/"], "long-host": ["a" * 20000 + ".com/x"],
            "schemes": ["a" * 20000 + "://"], "scheme-dots": ["a.b+" * 5000], "pins-glued": ["pin:" * 5000], "pins-dash": ["pin-" * 5000],
            "is-words": ["is " * 6000], "commas": [",," * 10000], "hash": ["1#" * 10000], "date-like": ["1-1-1-" * 3300],
            "date-dots": ["12.11.2026." * 1800], "nd-mix": ["٤ " * 10000], "zw-labels": ["p​i​n:" * 3000],
            "cyrillic": ["рас" * 6000], "long-token-label": ["Pin: " + "9" * 19990], "tab-gaps": ["1\t" * 10000],
            "many-dividers": ["-"] * 3 * 3000, "alternating": ["Pin:", "", "4417", "Pin"] * 3000,
        })


if __name__ == "__main__":
    unittest.main()
