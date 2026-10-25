"""#375 E1, slice S1 SPEC TESTS for `system/scripts/invite_filter.py` (the anchor-based block drop). Written before the code.

Run: python3 dev/tests/test_invite_filter_spec.py      (quick tier: plain code)

The module does not exist yet, so it is imported lazily and every class is skipped with "invite_filter not built yet" until it does;
the file passes today as skips. The builder (S1) makes these pass without editing them; a change to a test needs Jarvis.

API under test (dev/proposals/375/PLAN.md, section 1):
  keep_indices(lines, *, second_layer=True) -> list[int]   ascending indices of kept input lines.
      SPEC (not in the plan, stated here): `second_layer` is a keyword argument. True (the default) calls
      `drop_labelled_values` last (S1b); False runs only the anchor layer and the shape gate. The label-blind tests rely on it.
  keep_lines(lines)  == [lines[i] for i in keep_indices(lines)]   never edited, never new
  filter_text(text)  == split on "\\n", keep_lines, join with "\\n", then the CAP (1,500 characters, whole lines only)
  CAP == 1500

Properties pinned: P1 the output lines are a byte-for-byte subsequence of the input; P2 idempotent; P3 timing (relative bounds as in
test_invite_clean_timing.py, 5 s alarm); anchors drop the whole block (consecutive non-blank lines) or the whole divider-bounded region;
ordinary text survives; no label word is consulted; the cap cuts whole lines only; a corpus of 30 fictional invites; a seeded generator
(2,000 bodies) for P1/P2 and "no planted digit run of 7+ survives". Fictional data only.

Assumption stated by the spec (the plan is silent): a divider line also ends the block before it, so a line directly above a divider
(no blank line between) is not in the divider's region and is not dropped with it.

How the tests compare: blank lines and divider lines are ignored when comparing a result with the expected agenda text (the plan does not
say whether a dropped region's divider or the blank lines around a dropped block are kept; see the report's ambiguity list).

Mutant hooks for the builder (check by hand or in the mutation slice, S6; each must turn at least one test red):
  MUTANT-A  anchors off (never drop on an anchor)                      -> Anchors, Corpus, Generated red
  MUTANT-B  drop only the anchor LINE, not its block                   -> Blocks, Corpus red
  MUTANT-C  regions off (a divider bounds nothing)                     -> Regions, Corpus red
  MUTANT-D  a label word list consulted (e.g. 'passcode' needed)       -> LabelBlind red
  MUTANT-E  digits tested with \\d on the raw text, not Nd + NFKC      -> UnicodeDigits red
  MUTANT-F  cap cuts mid-line                                          -> Cap red
  MUTANT-G  output line rewritten (strip, case, NFKC)                  -> Subset, Generated red
  MUTANT-H  second_layer ignored (always on or always off)             -> LabelBlind.test_second_layer_toggle red
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
    except ModuleNotFoundError as e:       # only "the module is not there yet"; a broken import inside it must fail loudly
        if e.name == "invite_filter":
            return None
        raise


F = _load()
needs_filter = unittest.skipUnless(F is not None, "invite_filter not built yet")


# ---------------------------------------------------------------- helpers (independent oracles; no use of the module under test)

def calibrate():
    """How much slower than the reference machine this one is (1.0 or more): the best of 7 runs of a fixed plain-text job."""
    text = "Budget review with the team and the plan for next week\n" * 40
    best = 1e9
    for _ in range(7):
        t0 = time.perf_counter()
        sum(1 for ln in text.split("\n") if re.search(r"\d{7}", ln))
        unicodedata.normalize("NFKC", text)
        best = min(best, time.perf_counter() - t0)
    return max(1.0, best / 0.0002)


SCALE = calibrate()
LIMIT = 0.5 * SCALE          # seconds per 20,000-character body
ALARM = 5.0 * SCALE          # seconds for anything, including a 1 MB hostile input


def timed(fn, *args, **kw):
    """(elapsed seconds, result); raises TimeoutError after ALARM seconds."""
    def stop(*_a):
        raise TimeoutError("took more than %s s" % ALARM)
    old = signal.signal(signal.SIGALRM, stop)
    signal.setitimer(signal.ITIMER_REAL, ALARM)
    t0 = time.time()
    try:
        out = fn(*args, **kw)
        return time.time() - t0, out
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


DIVIDER = re.compile(r"^\s*(?:[_\-=*~#.─-╿—–]\s*){3,}$")


def is_blank(line):
    return not line.strip()


def is_divider(line):
    return bool(DIVIDER.match(line))


def content(lines):
    """The lines that carry text: no blank lines, no divider lines."""
    return [ln for ln in lines if not is_blank(ln) and not is_divider(ln)]


def nd_run(line):
    """Longest run of consecutive Unicode decimal digits (category Nd), ignoring invisible (Cf) characters."""
    best = cur = 0
    for ch in line:
        c = unicodedata.category(ch)
        if c == "Cf":
            continue
        if c == "Nd":
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def digits(rnd, n, script):
    base = {"ascii": 0x30, "fullwidth": 0xFF10, "arabic": 0x660, "devanagari": 0x966, "bold": 0x1D7CE}[script]
    return "".join(chr(base + rnd.randint(0, 9)) for _ in range(n))


SCRIPTS_USED = ["ascii", "fullwidth", "arabic", "devanagari", "bold"]


def run(lines, **kw):
    return F.keep_lines(lines, **kw) if kw else F.keep_lines(lines)


# ---------------------------------------------------------------- 1. P1 and P2 on hand-made input

PROSE = [
    "Review the budget for next quarter", "Action owners to confirm the dates", "Room 204 on the second floor",
    "Agenda item 3: supplier update", "Meeting on 12-11-2026 at 14:00", "Budget 1,200,000 approved last year",
    "Windows 11 upgrade plan", "Please bring the Model X200 samples", "Lunch at 12:30", "Next steps and owners",
    "Risks: supplier delay of 2 weeks", "Phase 2 starts 01-12-2026", "Ext 4417 for the front desk", "See the roadmap document",
    "Sprint 14 demo", "Version 2.6.9 release notes", "Floor 3, meeting room B", "Attendees: Alex Rowe, Sam Hale",
]


@needs_filter
class Subset(unittest.TestCase):
    """P1: the output is a byte-for-byte subsequence of the input, in order; keep_lines is exactly keep_indices applied."""

    def sample(self):
        return ["Agenda", "", "  Indented line with trailing space  ", "Café review — “quoted”", "UPPER lower MiXeD",
                "tab\tseparated", "", "Call +44 20 7946 0000", "", "https://meet.example.test/j/abc", "", "Closing remarks"]

    def test_indices_ascending_unique_in_range(self):
        lines = self.sample()
        idx = F.keep_indices(lines)
        self.assertEqual(idx, sorted(set(idx)))
        self.assertTrue(all(0 <= i < len(lines) for i in idx))

    def test_keep_lines_is_keep_indices_applied(self):
        lines = self.sample()
        self.assertEqual(F.keep_lines(lines), [lines[i] for i in F.keep_indices(lines)])

    def test_kept_lines_are_unchanged(self):
        lines = self.sample()
        for ln in F.keep_lines(lines):
            self.assertIn(ln, lines)
        self.assertIn("  Indented line with trailing space  ", F.keep_lines(lines))       # no strip
        self.assertIn("Café review — “quoted”", F.keep_lines(lines))   # no normalisation

    def test_input_not_mutated(self):
        lines = self.sample()
        before = list(lines)
        F.keep_indices(lines)
        F.keep_lines(lines)
        self.assertEqual(lines, before)

    def test_empty_and_blank_input(self):
        self.assertEqual(F.keep_indices([]), [])
        self.assertEqual(F.keep_lines([]), [])
        self.assertEqual(F.filter_text(""), "")
        self.assertEqual(content(F.keep_lines(["", "   ", ""])), [])

    def test_filter_text_matches_keep_lines_below_the_cap(self):
        text = "\n".join(self.sample())
        self.assertEqual(F.filter_text(text), "\n".join(F.keep_lines(text.split("\n"))))

    def test_ordinary_text_is_untouched(self):
        self.assertEqual(F.keep_lines(PROSE), PROSE)


@needs_filter
class Idempotent(unittest.TestCase):
    """P2: filter(filter(x)) == filter(x), for the lines API and the text API (the cap included)."""

    def test_fixed_inputs(self):
        samples = [
            PROSE,
            PROSE + ["", "Join: https://meet.example.test/j/1", "Passcode: 4417", ""] + PROSE,
            ["________", "Dial +44 20 7946 0000,,123456789#", "________", "Agenda", "________"],
            ["Passcode:", "aB3dE5x", "5588", "Pin", "4417"],
        ]
        for lines in samples:
            once = F.keep_lines(lines)
            self.assertEqual(F.keep_lines(once), once, lines)
            self.assertEqual(F.filter_text(F.filter_text("\n".join(lines))), F.filter_text("\n".join(lines)))


# ---------------------------------------------------------------- 2. anchors drop the whole block

URL_LINES = [
    "https://meet.example.test/j/abc-defg-hij", "http://example.test/join", "www.example.test/meeting", "meet.example.test/abc-defg-hij",
    "teams.example.test/l/meetup-join/19%3ameeting_abc", "tel:+441234567890", "tel:+44-20-7946-0000", "sip:room12@example.test",
    "msteams://example.test/l/meetup-join", "zoommtg://example.test/join?confno=abc", "HTTPS://MEET.EXAMPLE.TEST/J/ABC",
]
DIAL_LINES = [
    ",,123456789#", "+44 20 7946 0000,,123456789# United Kingdom", "123456789#", "Dial 0044 20 7946 0000 then 987654321#", "dial: ,,,,12345#",
]
DIGIT_RUN_LINES = [
    "1234567", "12345678", "ID 4417891203", "ref 1234567 end", "00000000", "+442079460000", "+1 415 555 0100", "+44 20 7946 0000",
    "07700 900 123 456",
]
GROUP_LINES = [
    "987 654 321", "987-654-321", "987.654.321", "987 - 654 - 321", "Call 123 456 789 now", "123  456  789",
]


def agenda_around(block):
    """A block between two ordinary blocks, separated by blank lines."""
    return ["Agenda for Tuesday", "Review the budget", "", *block, "", "Next steps", "Owners to confirm dates"]


KEPT_AROUND = ["Agenda for Tuesday", "Review the budget", "Next steps", "Owners to confirm dates"]


@needs_filter
class Anchors(unittest.TestCase):
    def check(self, group):
        for ln in group:
            with self.subTest(line=ln):
                self.assertEqual(content(run(agenda_around([ln]))), KEPT_AROUND)

    def test_links(self):
        self.check(URL_LINES)

    def test_dial_strings(self):
        self.check(DIAL_LINES)

    def test_digit_runs_of_seven_or_more(self):
        self.check(DIGIT_RUN_LINES)

    def test_three_three_three_groups(self):
        self.check(GROUP_LINES)

    def test_six_digits_alone_is_not_an_anchor(self):
        for ln in ["Ref 123456", "Budget 123456", "Room 204", "Ext 4417"]:
            self.assertIn(ln, run(agenda_around([ln])), ln)

    def test_anchor_inside_a_longer_sentence_still_drops_the_line(self):
        self.check(["To join the call, dial 987654321 and wait", "Open https://meet.example.test/j/1 to join the room"])


@needs_filter
class UnicodeDigits(unittest.TestCase):
    """Digits are decided by Unicode category Nd after NFKC, not by \\d on the raw text; invisible characters are removed first."""

    def test_other_scripts_count(self):
        rnd = random.Random(375)
        for script in SCRIPTS_USED:
            for n in (7, 9, 12):
                ln = "Code " + digits(rnd, n, script)
                with self.subTest(script=script, n=n):
                    self.assertEqual(content(run(agenda_around([ln]))), KEPT_AROUND)

    def test_other_scripts_in_three_three_three(self):
        rnd = random.Random(376)
        for script in SCRIPTS_USED:
            for sep in (" ", "-", ".", " ", "–"):
                ln = sep.join(digits(rnd, 3, script) for _ in range(3))
                with self.subTest(script=script, sep=repr(sep)):
                    self.assertEqual(content(run(agenda_around([ln]))), KEPT_AROUND)

    def test_zero_width_characters_between_digits(self):
        for zw in ("​", "‌", "‍", "⁠", "﻿", "­"):
            ln = zw.join("12345678")
            with self.subTest(zw=repr(zw)):
                self.assertEqual(content(run(agenda_around([ln]))), KEPT_AROUND)

    def test_fullwidth_url_and_dial(self):
        self.assertEqual(content(run(agenda_around(["ｈｔｔｐｓ：//meet.example.test/j/1"]))), KEPT_AROUND)
        self.assertEqual(content(run(agenda_around(["，，１２３４５６７８９＃"]))), KEPT_AROUND)

    def test_short_other_script_numbers_survive(self):
        rnd = random.Random(377)
        for script in SCRIPTS_USED:
            ln = "Room " + digits(rnd, 3, script)
            self.assertIn(ln, run(agenda_around([ln])))


# ---------------------------------------------------------------- 3. blocks and regions

@needs_filter
class Blocks(unittest.TestCase):
    """A block is the consecutive non-blank lines. One anchor drops all of them; nothing outside the block changes."""

    def test_whole_block_goes(self):
        block = ["Join the meeting", "Meeting room details", "https://meet.example.test/j/1", "Thank you"]
        self.assertEqual(content(run(agenda_around(block))), KEPT_AROUND)

    def test_neighbouring_blocks_are_unaffected(self):
        lines = ["Block one line A", "Block one line B", "", "Join: https://meet.example.test/j/1", "More words here", "",
                 "Block three line A", "Block three line B"]
        self.assertEqual(content(run(lines)), ["Block one line A", "Block one line B", "Block three line A", "Block three line B"])

    def test_anchor_at_the_start_and_end_of_a_block(self):
        self.assertEqual(content(run(agenda_around(["https://meet.example.test/j/1", "words", "more words"]))), KEPT_AROUND)
        self.assertEqual(content(run(agenda_around(["words", "more words", "https://meet.example.test/j/1"]))), KEPT_AROUND)

    def test_whitespace_only_line_separates_blocks(self):
        lines = ["Keep me", "   ", "Drop me 12345678"]
        self.assertEqual(content(run(lines)), ["Keep me"])

    def test_block_without_anchor_is_kept_whole(self):
        block = ["Join the room on the second floor", "Bring a laptop", "Room 204"]
        self.assertEqual(content(run(agenda_around(block))), KEPT_AROUND[:2] + block + KEPT_AROUND[2:])

    def test_locality(self):
        """P4 flavour: adding or moving unrelated blocks does not change which of a block's lines survive."""
        a = ["Alpha line", "Alpha second line"]
        b = ["Beta line", "Join https://meet.example.test/j/1"]
        c = ["Gamma line"]
        for order in itertools.permutations([a, b, c]):
            lines = []
            for blk in order:
                lines += blk + [""]
            self.assertEqual(sorted(content(run(lines))), sorted(a + c))


@needs_filter
class Regions(unittest.TestCase):
    """A divider line (3+ of _ - = box-drawing, also '- - -') starts a region that ends at the next divider or the end; a region
    holding a strong anchor is dropped whole, every block in it."""

    DIVIDERS = ["________________________", "--------------------", "====================", "────────",
                "- - - - - -", "---", "___"]

    def test_region_goes_with_all_its_blocks(self):
        for div in self.DIVIDERS:
            lines = ["Agenda for Tuesday", "Review the budget", div, "Microsoft Teams meeting", "", "Need help?", "", "Join: https://meet.example.test/j/1",
                     "", "Reset the settings in the app", div, "Closing words"]
            with self.subTest(divider=div):
                kept = content(run(lines))
                self.assertEqual(kept, ["Agenda for Tuesday", "Review the budget", "Closing words"])

    def test_region_without_an_anchor_is_kept(self):
        lines = ["Top", "________", "Notes", "", "More notes", "________", "Bottom"]
        self.assertEqual(content(run(lines)), ["Top", "Notes", "More notes", "Bottom"])

    def test_two_regions_decided_separately(self):
        lines = ["Top", "________", "Join https://meet.example.test/j/1", "Words in region one", "________", "Plain region two", "Still two"]
        self.assertEqual(content(run(lines)), ["Top", "Plain region two", "Still two"])

    def test_region_runs_to_the_end(self):
        lines = ["Top", "________", "Words", "", "Dial ,,123456789#", "", "More words"]
        self.assertEqual(content(run(lines)), ["Top"])

    def test_text_before_the_first_divider_is_not_in_a_region(self):
        lines = ["Before the divider", "", "Another", "________", "Dial 987654321"]
        self.assertEqual(content(run(lines)), ["Before the divider", "Another"])

    def test_a_short_rule_is_not_a_divider(self):
        """Two marks are not a divider: '--' or '__' between words must not open a region."""
        lines = ["Top", "--", "Words after a short rule", "", "Join https://meet.example.test/j/1"]
        self.assertEqual(content(run(lines)), ["Top", "--", "Words after a short rule"])


# ---------------------------------------------------------------- 4. keeps

@needs_filter
class Keeps(unittest.TestCase):
    CASES = [
        "Agenda: review the plan and the budget", "Meeting on 12-11-2026 at 14:00", "2026-11-12 14:00 to 15:30", "10.11.2026", "Thursday 15th October",
        "Room 204", "Room B-12, floor 3", "Ext 4417", "Budget 1,200,000", "Windows 11 upgrade", "Model X200 samples", "iPhone 15 Pro rollout",
        "Q4 2026 planning", "Sprint 14", "Version 2.6.9", "12:30 lunch", "Call at 9", "Phase 2 starts 01-12-2026", "Invoice INV-2041 to be paid",
        "Team of 25 people, 3 sites", "Price list v3", "Section 4.2.1 of the contract", "Decision: go ahead",
    ]

    def test_each_survives_alone_and_in_context(self):
        for ln in self.CASES:
            with self.subTest(line=ln):
                self.assertIn(ln, run([ln]))
                self.assertIn(ln, run(agenda_around([ln])))

    def test_all_together(self):
        self.assertEqual(run(self.CASES), self.CASES)


# ---------------------------------------------------------------- 5. label-blind

@needs_filter
class LabelBlind(unittest.TestCase):
    """No label word is consulted by the anchor layer. The decisive test: replace every label word with a random string; the
    block must still go. And a block with a label word but no anchor is kept by the anchor layer (second layer off)."""

    def test_random_label_words_make_no_difference(self):
        rnd = random.Random(378)
        for _ in range(300):
            label = "".join(rnd.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(rnd.randint(3, 12)))
            value = digits(rnd, rnd.randint(7, 12), "ascii")
            block = [f"{label.capitalize()}: {value}"]
            with self.subTest(label=label):
                self.assertEqual(content(run(agenda_around(block), second_layer=False)), KEPT_AROUND)

    def test_label_word_swap_gives_the_same_result(self):
        rnd = random.Random(379)
        for label in ["Passcode", "Meeting ID", "Password", "PIN", "Access code", "Zorp", "Quux frobnicate", ""]:
            value = digits(rnd, 9, "ascii")
            lines = agenda_around([f"{label} {value}".strip(), "Details follow"])
            self.assertEqual(content(run(lines, second_layer=False)), KEPT_AROUND, label)

    def test_label_word_without_anchor_is_kept_by_the_anchor_layer(self):
        for ln in ["Passcode: tuesday", "Passcode: 4417", "Password: a1", "PIN: 12", "Meeting ID: TBC", "Access code: 5588", "Token: x"]:
            with self.subTest(line=ln):
                self.assertIn(ln, run(agenda_around([ln]), second_layer=False))

    def test_second_layer_toggle(self):
        """second_layer=True (the default) drops 'Passcode: 4417'; second_layer=False keeps it. Same lines, same call otherwise."""
        lines = agenda_around(["Passcode: 4417"])
        self.assertIn("Passcode: 4417", F.keep_lines(lines, second_layer=False))
        self.assertNotIn("Passcode: 4417", F.keep_lines(lines, second_layer=True))
        self.assertEqual(F.keep_indices(lines), F.keep_indices(lines, second_layer=True))     # the default is on
        self.assertEqual(F.keep_lines(lines, second_layer=True), [lines[i] for i in F.keep_indices(lines, second_layer=True)])

    def test_anchor_layer_alone_is_a_subset_of_both(self):
        """Turning the second layer on only ever removes more lines."""
        rnd = random.Random(380)
        for _ in range(100):
            lines = [rnd.choice(PROSE + ["Passcode: 4417", "Pin", "4417", "https://meet.example.test/j/1", "", "________"]) for _ in range(12)]
            self.assertTrue(set(F.keep_indices(lines)) <= set(F.keep_indices(lines, second_layer=False)))


# ---------------------------------------------------------------- 6. the cap

@needs_filter
class Cap(unittest.TestCase):
    def lines(self, n, width=40):
        return [f"Line {i:03d} " + "w" * (width - 9) + f" {i % 7}" for i in range(n)]

    def test_constant(self):
        self.assertEqual(F.CAP, 1500)

    def test_whole_lines_only_and_within_the_cap(self):
        src = self.lines(100)
        out = F.filter_text("\n".join(src))
        self.assertLessEqual(len(out), 1500)
        got = out.split("\n")
        self.assertEqual(got, F.keep_lines(src)[:len(got)])                     # a prefix of the kept lines, none cut
        nxt = F.keep_lines(src)[len(got)]
        self.assertGreater(len(out) + 1 + len(nxt), 1500)                       # the next line would not have fitted

    def test_a_line_that_would_cross_drops_the_rest_too(self):
        short = ["Short line number %d here" % i for i in range(5)]
        crossing = "x " * 800                                                   # 1,600 characters of words
        tail = ["Tail one", "Tail two"]
        out = F.filter_text("\n".join(short + [crossing] + tail))
        self.assertEqual(out.split("\n"), short)                                # not the tail: still a subset in order, cut at the crossing line

    def test_below_the_cap_nothing_is_lost(self):
        src = self.lines(20)
        self.assertEqual(F.filter_text("\n".join(src)), "\n".join(src))

    def test_exactly_at_the_cap_fits(self):
        src = ["a " * 99 + "a"] * 7 + ["b" * 99 + " c"]                          # seven lines of 199 characters, then one of 101
        out = F.filter_text("\n".join(src))
        self.assertLessEqual(len(out), 1500)
        self.assertEqual(out.split("\n"), src[:len(out.split("\n"))])

    def test_no_mid_line_cut_with_multibyte_text(self):
        src = ["éèê " * 20 + str(i) for i in range(60)]
        out = F.filter_text("\n".join(src))
        self.assertLessEqual(len(out), 1500)
        self.assertEqual(out.split("\n"), src[:len(out.split("\n"))])

    def test_idempotent_after_the_cap(self):
        out = F.filter_text("\n".join(self.lines(100)))
        self.assertEqual(F.filter_text(out), out)


# ---------------------------------------------------------------- 7. timing (P3)

@needs_filter
class Timing(unittest.TestCase):
    def test_hostile_bodies_of_20000_characters(self):
        bodies = {
            "dots": ["." * 20000], "dot-space": [". " * 10000], "dash-space": ["- " * 10000], "digit-space": ["1 " * 10000],
            "digit-dash": ["12-" * 6666], "many-short-lines": ["a"] * 10000, "many-blank": [""] * 20000, "dividers": ["_" * 40] * 500,
            "words": ["word " * 4000], "mixed-token": ["a1" * 10000], "slashes": ["/" * 20000], "colons": [": " * 10000],
            "labels": ["Passcode: " * 2000], "label-lines": ["Passcode:"] * 2000, "urls": ["http://a.test/" * 1400],
            "zero-width": ["​".join("12345") * 3000],
        }
        slow = []
        for name, lines in bodies.items():
            took, _ = timed(F.keep_indices, lines)
            if took > LIMIT:
                slow.append((round(took, 3), name))
        self.assertEqual(slow, [], f"over {LIMIT} s")

    def test_one_megabyte_input_through_filter_text(self):
        for name, text in (("prose", ("Review the budget for next quarter\n" * 30000)[:1_000_000]), ("digits", "1 2 3 " * 170000),
                           ("one line", "ab " * 340000), ("passcode", "Passcode: x\n" * 80000)):
            took, out = timed(F.filter_text, text)
            self.assertLessEqual(len(out), 1500, name)

    def test_linear_growth(self):
        """Ten times the input must not take a hundred times as long (relative, so a slow machine passes)."""
        base = ["Review the budget for next quarter", "Passcode: tuesday", "", "Join https://meet.example.test/j/1"] * 100
        t1 = min(timed(F.keep_indices, base)[0] for _ in range(3))
        t10 = min(timed(F.keep_indices, base * 10)[0] for _ in range(3))
        self.assertLess(t10, max(t1 * 40, 0.05 * SCALE))


# ---------------------------------------------------------------- 8. the corpus: 30 realistic fictional invites

NAMES = ["Alex Rowe", "Sam Hale", "Priya Nair", "Jordan Lee", "Mia Torres", "Omar Haddad"]
TOPICS = [
    ("Supplier onboarding review", ["Purpose: agree the onboarding plan for the three new suppliers", "Please read the draft contract before the call",
                                     "Agenda: 1. Timeline 2. Owners 3. Open risks"]),
    ("Quarterly budget check-in", ["We will walk through the Q4 forecast and the open purchase orders", "Finance lead to present slide 4 first",
                                    "Room 204 is booked for people in the office"]),
    ("Migration cutover planning", ["Goal: confirm the cutover weekend of 21-11-2026", "Bring the rollback checklist", "Decision needed on the freeze date"]),
    ("Design review: new onboarding flow", ["Review the three prototypes and pick one", "Feedback form is in the shared folder", "Timebox: 45 minutes"]),
    ("Weekly programme stand-up", ["Round the table: blockers and asks", "Release 2.6.9 scope check", "AOB"]),
    ("Customer workshop prep", ["Agree the demo script and who speaks", "Sam to bring the Model X200 units", "Lunch at 12:30 for the team"]),
]


def teams(i, topic, body):
    d = 100000000 + i * 7919 * 13
    return [
        "Hi all,", *body, "",
        "________________________________________________________________________________",
        "Microsoft Teams meeting",
        f"Join: https://teams.example.test/l/meetup-join/19%3ameeting_{i:04d}abc@thread.v2/0",
        f"Meeting ID: {str(d)[:3]} {str(d)[3:6]} {str(d)[6:9]} {i:03d}",
        f"Passcode: aB{i}dE5",
        "",
        "________________________________________________________________________________",
        "Dial in by phone",
        f"+44 20 7946 0{i:03d},,{d}# United Kingdom, London",
        "Find a local number",
        f"Phone conference ID: {str(d)[:3]} {str(d)[3:6]} {str(d)[6:9]}#",
        "For organisers: Meeting options | Reset dial-in PIN",
        "________________________________________________________________________________",
    ], ["Hi all,", *body]


def zoom(i, topic, body):
    d = 98700000000 + i * 1237
    return [
        f"{NAMES[i % 6]} is inviting you to a scheduled Zoom meeting.", "",
        f"Topic: {topic}", "Time: Nov 12, 2026 14:00 London", "",
        *body, "",
        "Join Zoom Meeting", f"https://zoom.example.test/j/{d}?pwd=Zm9vYmFy{i}", "",
        f"Meeting ID: {str(d)[:3]} {str(d)[3:7]} {str(d)[7:]}", f"Passcode: {100000 + i * 37}", "---",
        "One tap mobile", f"+442039010001,,{d}# UK", f"+14155550100,,{d}# US", "---",
        "Dial by your location", "+44 203 901 0001 UK", "Find your local number: https://zoom.example.test/u/abc",
    ], [f"{NAMES[i % 6]} is inviting you to a scheduled Zoom meeting.", f"Topic: {topic}", "Time: Nov 12, 2026 14:00 London", *body]


def webex(i, topic, body):
    return [
        *body, "",
        "Join meeting", f"https://webex.example.test/meet/{NAMES[i % 6].lower().replace(' ', '.')}", "",
        "Join by phone", f"+1-415-555-0{100 + i} US Toll", f"Access code: 255{i:02d} 123 4567", "",
        "Can't join the meeting?", "Contact support at https://help.example.test/webex",
    ], body


def meet(i, topic, body):
    return [
        f"{topic}", *body, "",
        "Join with Google Meet", f"https://meet.example.test/abc-{i:02d}fg-hij", "",
        "Join by phone", f"(GB) +44 20 7946 0{i:03d} PIN: {123456000 + i}#", "More phone numbers",
        f"https://tel.meet.example.test/abc-{i:02d}fg-hij?pin=1234567{i:03d}",
    ], [f"{topic}", *body]


PROVIDERS = [teams, zoom, webex, meet]


def corpus():
    out = []
    for i in range(30):
        topic, body = TOPICS[i % len(TOPICS)]
        lines, expected = PROVIDERS[i % 4](i, topic, body)
        out.append((f"{PROVIDERS[i % 4].__name__}-{i:02d}", lines, expected))
    return out


@needs_filter
class Corpus(unittest.TestCase):
    def test_thirty_invites(self):
        c = corpus()
        self.assertEqual(len(c), 30)
        for name, lines, expected in c:
            with self.subTest(invite=name):
                got = run(lines)
                self.assertEqual(content(got), expected)
                for ln in got:
                    self.assertLess(nd_run(ln), 7, ln)
                    self.assertNotRegex(ln, r"https?://|tel:|sip:")
                self.assertEqual(run(got), got)                                  # P2 on each
                it = [lines[i] for i in F.keep_indices(lines)]
                self.assertEqual(it, got)                                        # P1

    def test_prose_kept_rate(self):
        """Every non-boilerplate line of the corpus survives (the plan asks for >= 95% on the prose corpus; here it is 100%)."""
        kept = total = 0
        for _name, lines, expected in corpus():
            got = set(content(run(lines)))
            total += len(expected)
            kept += sum(1 for e in expected if e in got)
        self.assertEqual(kept, total)

    def test_corpus_text_api(self):
        for name, lines, _e in corpus():
            out = F.filter_text("\n".join(lines))
            self.assertLessEqual(len(out), 1500)
            self.assertEqual(F.filter_text(out), out, name)


# ---------------------------------------------------------------- 9. the seeded generator (2,000 bodies)

LABEL_WORDS = ["Passcode", "Password", "PIN", "Token", "Meeting ID", "Access code", "Secret", "Host key", "Code", "Pin", "Key"]
SEPS = [": ", " = ", " - ", " – ", " is ", " ", ":\n"]
DIVS = ["________", "--------", "========", "────", "- - - -", "---"]


def plant(rnd):
    n = rnd.randint(7, 14)
    script = rnd.choice(SCRIPTS_USED)
    run_ = digits(rnd, n, script)
    if rnd.random() < 0.15:
        run_ = rnd.choice(["​", "⁠", "﻿"]).join(run_)
    return rnd.choice(["{}", "Code {}", "Call {} now", ",,{}#", "ID: {}", "+{}", "ref-{}", "{} #", "{}{}"]).replace("{}{}", run_ + "x").replace("{}", run_)


def body(rnd, planted):
    lines = []
    for _ in range(rnd.randint(3, 30)):
        k = rnd.random()
        if k < 0.50:
            lines.append(rnd.choice(PROSE))
        elif k < 0.60:
            lines.append("")
        elif k < 0.67:
            lines.append(rnd.choice(DIVS))
        elif k < 0.80:
            lines.append(rnd.choice(LABEL_WORDS) + rnd.choice(SEPS).rstrip("\n") + rnd.choice(["4417", "tuesday", "aB3dE5", "12:30", "", "x7Kp29Qz"]))
        elif k < 0.85:
            lines.append(rnd.choice(LABEL_WORDS) + rnd.choice([":", ""]))
            lines.append(rnd.choice(["4417", "reset", "12-11-2026", "a1b2c3", "Next item"]))
        elif k < 0.90:
            lines.append(rnd.choice(["https://meet.example.test/j/1", "tel:+441234567", "sip:room1@example.test", "987 654 321"]))
        else:
            ln = plant(rnd)
            planted.append(ln)
            lines.append(ln)
    return lines


@needs_filter
class Generated(unittest.TestCase):
    N = 2000

    def test_p1_p2_and_no_planted_run_survives(self):
        rnd = random.Random(375)
        for n in range(self.N):
            planted = []
            lines = body(rnd, planted)
            for kw in ({}, {"second_layer": False}):
                idx = F.keep_indices(lines, **kw)
                with self.subTest(body=n, kw=kw):
                    self.assertEqual(idx, sorted(set(idx)))                       # P1 ascending, unique
                    self.assertTrue(all(0 <= i < len(lines) for i in idx))
                    out = [lines[i] for i in idx]                                  # P1 subset, byte for byte, in order
                    self.assertEqual(F.keep_lines(lines, **kw), out)
                    self.assertEqual(F.keep_lines(out, **kw), out)                 # P2
                    for ln in out:                                                 # P3 no planted run of 7+ survives
                        self.assertLess(nd_run(ln), 7, ln)
            # (the text API too, on every 20th body, to keep the run quick)
            if n % 20 == 0:
                text = "\n".join(lines)
                once = F.filter_text(text)
                self.assertEqual(F.filter_text(once), once)
                self.assertLessEqual(len(once), 1500)

    def test_a_planted_run_goes_wherever_it_sits(self):
        """Plant one run in a random place among 40 ordinary lines, with random dividers and blanks around it."""
        rnd = random.Random(381)
        for n in range(300):
            lines = [rnd.choice(PROSE) for _ in range(40)]
            for _ in range(rnd.randint(0, 4)):
                lines.insert(rnd.randint(0, len(lines)), rnd.choice(["", rnd.choice(DIVS)]))
            ln = plant(rnd)
            lines.insert(rnd.randint(0, len(lines)), ln)
            out = F.keep_lines(lines, second_layer=False)
            self.assertNotIn(ln, out, n)
            self.assertTrue(all(nd_run(x) < 7 for x in out))


if __name__ == "__main__":
    unittest.main()
