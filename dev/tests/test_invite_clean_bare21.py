"""2.6.8 #369 bare21 (Team Cap's verdict on bare19): a QUALIFIED hard label takes the next lines as its value, and dates and times are exempt
under a SOFT heading (not under a hard label).

Run: python3 dev/tests/test_invite_clean_bare21.py      (quick tier: plain code; the 40,000-body mixed fuzz takes a while)

- QUALIFIED: a hard label, then a qualifier that starts with a function word and has at most four more words ("for dial-in", "to join",
  "for the weekly call") and/or a bracketed group ("(Teams)", "(organiser only)"), then a separator or the end of the line: the next lines are
  the value, as for an unqualified label. "Passcode policy review" (no function word right after the label) behaves as before.
- DATES: under a soft heading ("Code freeze", "Password reset") a plausible date or time is an agenda line and stays; any other number goes.
  A date after "Passcode:" still goes.

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

QUALIFIED = ["Passcode for dial-in:", "Passcode for dial-in", "Passcode (Teams)", "Passcode (Teams):", "Meeting ID (Teams)", "Meeting ID (Teams):",
             "Meeting ID for the weekly call", "Meeting ID for the weekly call:", "PIN to join:", "PIN to join", "Password for the portal -",
             "Password for the portal:", "Host key (organiser only)", "Host key (organiser only):", "Access code for guests",
             "Access code for guests:", "Passcode (Teams) for dial-in:", "Zoom ID for the Friday review call", "Pass code to enter the room =",
             "Webinar ID (public)", "Meeting ID for the all hands call"]
VALUES = ["4417", "987 654 321", "ZQ7742", "hunter", "12-11-2026", "2026-11-12", "12 Nov 2026", "14:00", "9am-5pm"]
SOFT = ["Password reset", "Code review", "Dress code", "Token refresh", "Code freeze"]
EXEMPT = ["12-11-2026", "2026-11-12", "12/11/2026", "12.11.2026", "12 Nov 2026", "12 November 2026", "Nov 12", "12:30", "12:30-13:00",
          "9am-5pm", "12:30–13:00", "14 Nov 2026 14:00", "November 12, 2026", "Fri 12 Nov", "09:00-17:30", "9:30 am", "12th November 2026"]
STILL_GO = ["4417", "987 654 321", "ZQ7742", "123456789", "12 Nov 4417", "987-65-4321", "Q3A9", "14:00 4417", "a1b2c3d4", "12:30 ZQ7742",
            "Nov 12 hunter2"]
NEGATIVES = ["Passcode policy review", "Password reset rollout plan", "Meeting ID badges", "Pin the roadmap", "Code of conduct refresh",
             "Access review for the quarter"]


def mutant(old, new, count=1):
    src = (SCRIPTS / "invite_clean.py").read_text(encoding="utf-8")
    assert src.count(old) >= 1, f"mutant anchor not found: {old!r}"
    spec = importlib.util.spec_from_loader("invite_clean_b21_mutant", loader=None)
    mod = importlib.util.module_from_spec(spec)
    mod.__file__ = str(SCRIPTS / "invite_clean.py")
    exec(compile(src.replace(old, new, count), "invite_clean_b21_mutant", "exec"), mod.__dict__)
    return mod


def layouts(label, value):
    """(body, the value that must go) in every layout: next line, blank lines, an instruction between, bullets, numbers, <li>, a table."""
    return [
        (f"{label}\n{value}\nAOB", value), (f"Agenda\n{label}\n\n\n{value}\nAOB", value), (f"{label}\nPlease enter\n{value}\nAOB", value),
        (f"- {label}\n- {value}\nAOB", value), (f"1. {label}\n2. {value}\nAOB", value), (f"a) {label}\nb) {value}\nAOB", value),
        (f"<ul><li>{label}</li><li>{value}</li></ul>\nAOB", value), (f"<table><tr><td>{label}</td></tr><tr><td>{value}</td></tr></table>\nAOB", value),
        (f"* {label}\n• {value}\nAOB", value), (f"> {label}\n> {value}\nAOB", value), (f"**{label}**\n{value}\nAOB", value),
    ]


def leaks(mod, rows):
    return [(b, v) for b, v in rows if v in mod.invite_text(b)]


ALL_QUALIFIED_ROWS = [r for lab in QUALIFIED for val in VALUES for r in layouts(lab, val)]


class Qualified(unittest.TestCase):
    def test_every_qualified_label_takes_its_value_in_every_layout(self):
        bad = [(b, v) for b, v in leaks(I, ALL_QUALIFIED_ROWS)]
        self.assertEqual(bad[:3], [], f"{len(bad)} of {len(ALL_QUALIFIED_ROWS)} rows keep their value")

    def test_the_agenda_line_after_the_value_stays(self):
        for lab in QUALIFIED:
            self.assertEqual(I.invite_text(f"{lab}\n4417\nAOB"), "AOB", lab)

    def test_capes_rows(self):
        for body, want in (("Passcode for dial-in:\n4417", ""), ("Meeting ID (Teams)\n987 654 321", ""), ("Passcode (Teams)\nhunter", ""),
                           ("Host key (organiser only)\nZQ7742", "")):
            self.assertEqual(I.invite_text(body), want, body)

    def test_two_labels_in_a_row_take_two_values(self):
        self.assertEqual(I.invite_text("Meeting ID (Teams)\nPasscode for dial-in:\n987 654 321\n4417\nAOB"), "AOB")
        self.assertEqual(I.invite_text("Meeting ID (Teams)\nPasscode (Teams)\n987\n4417\nAOB"), "AOB")

    def test_the_value_on_the_same_line_goes(self):
        for body in ("Meeting ID (Teams) 987 654 321", "Meeting ID for the weekly call: 987 654 321", "Passcode for dial-in 4417",
                     "PIN to join: hunter", "Host key (organiser only): ZQ7742"):
            self.assertEqual(I.invite_text(body + "\nAOB"), "AOB", body)

    def test_negatives_behave_as_before(self):
        for neg in NEGATIVES:
            out = I.invite_text(f"{neg}\nAOB\nNext item")
            # bare22: a label plus a short phrase is a qualified label whose window removes a 1-2 token line (here AOB); a sentence stays
            self.assertIn("Next item", out, (neg, out))

    def test_a_label_word_with_a_non_function_word_is_not_qualified(self):
        self.assertEqual(I.invite_text("Passcode policy review\nAOB\nNext"), "AOB\nNext")

    def test_the_value_four_lines_below_a_qualified_label_with_text_between_stays_as_for_an_unqualified_label(self):
        plain = I.invite_text("Passcode:\nA\nB\nC\nD")
        qual = I.invite_text("Passcode for dial-in:\nA\nB\nC\nD")
        self.assertEqual(qual, plain)

    def test_idempotent_on_every_row(self):
        for body, _v in ALL_QUALIFIED_ROWS:
            once = I.invite_text(body)
            self.assertEqual(I.invite_text(once), once, body)

    def test_a_title_with_a_qualified_label_and_no_value_is_not_changed(self):
        self.assertEqual(I.scrub("Meeting ID for the weekly call", 140), "Meeting ID for the weekly call")


class Dates(unittest.TestCase):
    def test_dates_and_times_stay_under_a_soft_heading(self):
        for h in SOFT:
            for d in EXEMPT:
                body = f"{h}\n{d}\nAOB"
                self.assertEqual(I.invite_text(body), body, body)
                body = f"{h}\n- {d}\n1. {d}\nAOB"
                self.assertEqual(I.invite_text(body), body, body)

    def test_other_numbers_still_go_under_a_soft_heading(self):
        for h in SOFT:
            for v in STILL_GO:
                out = I.invite_text(f"{h}\n{v}\nAOB")
                self.assertNotIn(v, out, (h, v))
                self.assertIn("AOB", out)

    def test_a_date_after_a_hard_label_still_goes(self):
        for lab in ("Passcode:", "PIN", "Meeting ID:", "Password -", "Passcode for dial-in:", "Host key (organiser only)"):
            for d in EXEMPT:
                out = I.invite_text(f"{lab}\n{d}\nAOB")
                self.assertNotIn(d, out, (lab, d))

    def test_a_date_shaped_passcode_on_the_label_line_goes(self):
        for body in ("Passcode: 12-11-2026", "Passcode 12-11-2026", "PIN: 2026-11-12", "Meeting ID: 12 Nov 2026"):
            self.assertEqual(I.invite_text(body + "\nAOB"), "AOB", body)

    def test_a_date_beside_a_value_does_not_save_the_value(self):
        self.assertNotIn("4417", I.invite_text("Code freeze\n12-11-2026 4417\nAOB"))
        self.assertNotIn("4417", I.invite_text("Code freeze\n4417 14:00\nAOB"))

    def test_a_date_line_does_not_take_the_heading_with_it(self):
        self.assertEqual(I.invite_text("Code freeze\n12-11-2026\n12:30\nAOB"), "Code freeze\n12-11-2026\n12:30\nAOB")

    def test_a_value_after_a_date_still_removes_the_value_and_the_heading_only(self):
        out = I.invite_text("Code freeze\n12-11-2026\n4417\nAOB")
        self.assertEqual(out, "12-11-2026\nAOB")


class StopLabelNumbers(unittest.TestCase):
    NUMS = ["987-65-4321", "123-45-6789", "1234-56-7890", "987 654 321", "4417", "55 66 77 88"]

    def test_number_shaped_values_after_every_hard_label_go(self):
        for lab in ("Meeting ID.", "Zoom ID!", "Key,", "Conference ID?", "Passcode:", "PIN", "Passcode for dial-in:", "Meeting ID (Teams)",
                    "Access code.", "Webinar ID;"):
            for v in self.NUMS:
                for body in (f"{lab}\n{v}\nAOB", f"{lab}\n- {v}\nAOB", f"{lab}\nhttps://teams.microsoft.com/l/meetup-join/x\n{v}\nAOB"):
                    self.assertNotIn(v, I.invite_text(body), body)

    def test_a_bare_time_after_a_stop_label_stays_but_a_date_goes(self):
        for v in ("12:30", "Lunch at 12:30"):
            self.assertIn(v, I.invite_text(f"Bring your staff ID.\n{v}\nAOB"), v)
        for v in ("25-10-2026", "2026-10-25", "12 Nov 2026"):      # bare22: dates are exempt only under soft headings
            self.assertNotIn(v, I.invite_text(f"Bring your staff ID.\n{v}\nAOB"), v)

    def test_a_real_date_after_a_colon_label_goes(self):
        for v in ("25-10-2026", "12:30"):
            self.assertNotIn(v, I.invite_text(f"Passcode:\n{v}\nAOB"))


def fuzz_mixed(rnd, n, with_values=True):
    """Dates, times and qualified labels among agenda lines. Returns (body, values, exempt): values must not survive pass one."""
    lines, values, exempt = [], [], []
    marks = ["", "", "- ", "1. ", "* ", "a) "]
    for _ in range(rnd.randint(2, 7)):
        pick = rnd.random()
        if pick < 0.25 and with_values:
            lab = rnd.choice(QUALIFIED)
            lines.append(rnd.choice(marks) + lab)
            if rnd.random() < 0.3:
                lines.append(rnd.choice(["Please enter", "", ""]))
            v = rnd.choice([f"{rnd.randint(1000, 9999)}{n:05d}", f"ZQ{n:05d}", f"{rnd.randint(100, 999)} {rnd.randint(100, 999)} {n:03d}",
                            f"{1 + n % 28:02d}-{1 + n % 12:02d}-19{10 + n % 90}", f"zq{n:05d}x"])
            lines.append(rnd.choice(marks) + v)
            values.append(v)
        elif pick < 0.55:
            lines.append(rnd.choice(["Password reset", "Code review", "Code freeze", "Dress code"]))
            for _k in range(rnd.randint(1, 2)):
                d = rnd.choice([f"{rnd.randint(1, 28):02d}-{rnd.randint(1, 12):02d}-2026", f"2027-{rnd.randint(1, 12):02d}-{rnd.randint(1, 28):02d}",
                                f"{rnd.randint(1, 28)} Nov 2026", f"Nov {rnd.randint(1, 28)}", f"{rnd.randint(0, 23):02d}:{rnd.randint(0, 59):02d}",
                                f"{rnd.randint(1, 12)}am-{rnd.randint(1, 12)}pm", f"{rnd.randint(1, 23):02d}:30–14:00", "14 Nov 2026 14:00"])
                lines.append(rnd.choice(marks) + d)
                exempt.append(d)
            if with_values and rnd.random() < 0.4:
                v = rnd.choice([f"{rnd.randint(1000, 9999)}{n:05d}", f"ZQ{n:05d}"])
                lines.append(rnd.choice(marks[:4]) + v)
                values.append(v)
        else:
            lines.append(rnd.choice(["Budget review", "Hiring plan", "Q3 forecast", "AOB", "Lunch at 12:30", "Room 4", "Item 12",
                                     rnd.choice(NEGATIVES) if with_values else "Next steps"]))
        if rnd.random() < 0.15:
            lines.append("")
    return "\n".join(lines), values, exempt


class Fuzz(unittest.TestCase):
    def test_forty_thousand_mixed_bodies(self):
        rnd = random.Random(2169)
        bad_fixed, bad_value = [], []
        for n in range(40000):
            body, values, _e = fuzz_mixed(rnd, n)
            once = I.invite_text(body)
            if I.invite_text(once) != once:
                bad_fixed.append(body)
            if any(v in once for v in values):
                bad_value.append(body)
        self.assertEqual((len(bad_fixed), bad_fixed[:1]), (0, []), "not a fixed point after one pass")
        self.assertEqual((len(bad_value), bad_value[:1]), (0, []), "a value survives pass one")

    def test_value_free_mixed_bodies_keep_every_date_and_time(self):
        rnd = random.Random(77)
        lost = []
        for n in range(8000):
            body, _v, exempt = fuzz_mixed(rnd, n, with_values=False)
            once = I.invite_text(body)
            if any(e not in once for e in exempt):
                lost.append(body)
        self.assertEqual(lost[:1], [], f"{len(lost)} bodies lost a date or a time")


class Mutants(unittest.TestCase):
    def test_qualified_rule_off(self):
        m = mutant("|{QUALIFIED_ALONE}\", re.I)", "\", re.I)")
        self.assertTrue(leaks(m, ALL_QUALIFIED_ROWS))

    def test_no_bracketed_group(self):
        m = mutant('_QBRACKET = r"\\s*[(\\[](?!', '_QBRACKET = r"(?!)[(\\[](?!')
        got = leaks(m, [r for r in ALL_QUALIFIED_ROWS if "(" in r[0]])
        self.assertTrue(got)
        self.assertFalse(leaks(m, [r for r in ALL_QUALIFIED_ROWS if "(" not in r[0].split("\n")[0] and "for dial-in" in r[0]][:5]))

    def test_no_phrase_qualifier(self):
        m = mutant('_QPHRASE = rf"', '_QPHRASE = rf"(?!)')
        self.assertTrue(leaks(m, [("Passcode for dial-in:\n4417", "4417"), ("PIN to join:\n4417", "4417")]))

    def test_qualifier_limited_to_zero_extra_words(self):
        m = mutant("{_QWORD}){{0,4}}", "{_QWORD}){{0,0}}")
        self.assertTrue(leaks(m, [("Meeting ID for the weekly call\n987 654 321", "987")]))

    def test_qualifier_limited_to_three_extra_words(self):
        m = mutant("{_QWORD}){{0,4}}", "{_QWORD}){{0,3}}")
        self.assertTrue(leaks(m, [("Meeting ID for the all hands call\n987 654 321", "987")]))

    def test_finished_soft_phrase_is_not_a_qualified_label(self):
        m = mutant("(?!{_SOFT_RUN}){_QUAL}", "{_QUAL}")
        self.assertNotIn("12-11-2026", m.invite_text("Password reset\n12-11-2026\nAOB"))
        self.assertIn("12-11-2026", I.invite_text("Password reset\n12-11-2026\nAOB"))

    def test_qualifier_without_the_end_anchor_eats_sentences(self):
        m = mutant("{_QUAL}(?:\\s*[.,;!?]+)?(?:{_ALONE_TAIL})?{_QUIET}$\"", "{_QUAL}(?:\\s*[.,;!?]+)?(?:{_ALONE_TAIL})?{_QUIET}\"")
        self.assertNotEqual(m.invite_text("Passcode for staff is set by the admin team\nAOB"), "AOB")

    def test_dates_not_exempt(self):
        m = mutant("looks = not taken and not label and _looks_like_value(ln, dates_ok=True)",
                   "looks = not taken and not label and _looks_like_value(ln, dates_ok=False)")
        self.assertNotEqual(m.invite_text("Code freeze\n12-11-2026\nAOB"), "Code freeze\n12-11-2026\nAOB")

    def test_numeric_dates_not_exempt(self):
        m = mutant("rf\"(?<![\\d:.])(?:{_YEAR}{_SEP}", "rf\"(?!)(?:{_YEAR}{_SEP}")
        for d in ("12-11-2026", "2026-11-12", "12/11/2026", "12.11.2026"):
            self.assertNotEqual(m.invite_text(f"Code freeze\n{d}\nAOB"), f"Code freeze\n{d}\nAOB", d)

    def test_month_names_not_exempt(self):
        m = mutant("rf\"|(?<![\\w])(?:{_DAY}(?:st|nd|rd|th)?", "rf\"|(?!)(?:{_DAY}(?:st|nd|rd|th)?")
        self.assertNotEqual(m.invite_text("Code freeze\n12 Nov 2026\nAOB"), "Code freeze\n12 Nov 2026\nAOB")

    def test_times_not_exempt(self):
        m = mutant("|(?<![\\d:.])(?:{_TIME})(?![\\d:])", "|(?!)")
        for d in ("12:30", "9am-5pm", "12:30-13:00"):
            self.assertNotEqual(m.invite_text(f"Code freeze\n{d}\nAOB"), f"Code freeze\n{d}\nAOB", d)

    def test_exemption_that_takes_every_number_leaks(self):
        m = mutant("rest = _SOFT_DATE_TIME.sub(\" \", rest)", "rest = re.sub(r\"[\\d:.\\-/ ]+\", \" \", rest)")
        self.assertIn("4417", m.invite_text("Code freeze\n4417\nAOB"))
        self.assertNotIn("4417", I.invite_text("Code freeze\n4417\nAOB"))

    def test_invalid_dates_not_taken_out(self):
        self.assertNotIn("987-65-4321", I.invite_text("Code freeze\n987-65-4321\nAOB"))
        m = mutant("(?:{_YEAR}{_SEP}{_MON}{_SEP}{_DAY}|{_DAY}{_SEP}{_MON}{_SEP}{_Y2}|{_MON}{_SEP}{_DAY}{_SEP}{_Y2})",
                   "(?:\\d{{1,4}}{_SEP}\\d{{1,2}}{_SEP}\\d{{1,4}})")
        self.assertIn("987-65-4321", m.invite_text("Code freeze\n987-65-4321\nAOB"))

    def test_hard_label_dates_exempted_by_the_weak_phrase_leak(self):
        m = mutant("and not _looks_like_value(ln)", "and not _looks_like_value(ln, dates_ok=True)")
        self.assertNotEqual(m.invite_text("Passcode:\n14 Nov 2026 14:00\nAOB"), "AOB")      # the date is read as an instruction: AOB is taken as the value
        self.assertEqual(I.invite_text("Passcode:\n14 Nov 2026 14:00\nAOB"), "AOB")


if __name__ == "__main__":
    unittest.main()
