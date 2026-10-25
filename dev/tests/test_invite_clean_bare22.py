"""2.6.8 #369 bare22 (reviewer's two digit leaks on bfb65603): (1) after a hard label's stop-label ("Meeting ID.") a date-shaped line is a
value whatever its validity; a bare time is not; dates stay exempt only under soft headings. (2) the "Meeting ID." wait survives a kept
finished phrase that a later soft window removes, so the result is a fixed point in one pass.

Run: python3 dev/tests/test_invite_clean_bare22.py      (quick tier: plain code; the fuzz takes a while)

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
from test_invite_clean_bare21 import fuzz_mixed  # noqa: E402

STOPS = ["Meeting ID.", "Key,", "Zoom ID!", "Bring your staff ID.", "Webinar ID;", "Host key.", "PIN."]
DATES = ["12-11-2026", "12-11-26", "29-02-2025", "01-01-2000", "12-12-2012", "31-12-1999", "01-02-1900", "11-12-2026 10:00", "31-02-2026",
         "12-31-2026", "2026-11-12", "12/11/2026", "12.11.2026", "12.11.26"]
KEEP_AFTER_STOP = ["Lunch at 12:30", "12:30", "Room 4", "Item 12", "Budget review", "Q3 forecast"]
SOFT = ["Password reset", "Code review", "Dress code", "Token refresh", "Code freeze"]


def mutant(old, new, count=1):
    src = (SCRIPTS / "invite_clean.py").read_text(encoding="utf-8")
    assert src.count(old) >= 1, f"mutant anchor not found: {old!r}"
    spec = importlib.util.spec_from_loader("invite_clean_b22_mutant", loader=None)
    mod = importlib.util.module_from_spec(spec)
    mod.__file__ = str(SCRIPTS / "invite_clean.py")
    exec(compile(src.replace(old, new, count), "invite_clean_b22_mutant", "exec"), mod.__dict__)
    return mod


def layouts(stop, value):
    return [f"{stop}\n{value}\nAOB", f"Agenda\n{stop}\n\n\n{value}\nAOB", f"- {stop}\n- {value}\nAOB", f"{stop}\nhttps://example.org/j/1\n{value}\nAOB",
            f"<ul><li>{stop}</li><li>{value}</li></ul>\nAOB"]


ROWS = [(b, d) for s in STOPS for d in DATES for b in layouts(s, d)]


class DateAfterStopLabel(unittest.TestCase):
    def test_every_date_shape_after_a_stop_label_goes(self):
        bad = [(b, d) for b, d in ROWS if d in I.invite_text(b)]
        self.assertEqual(bad[:3], [], f"{len(bad)} of {len(ROWS)} rows keep the date")

    def test_the_agenda_line_after_stays(self):
        for s in STOPS:
            self.assertEqual(I.invite_text(f"{s}\n12-11-2026\nAOB"), "AOB", s)

    def test_reviewers_rows(self):
        for d in DATES:
            self.assertNotIn(d, I.invite_text(f"Meeting ID.\n{d}"), d)
            self.assertNotIn(d, I.invite_text(f"Meeting ID. {d}"), d)

    def test_honest_negatives_survive(self):
        for k in KEEP_AFTER_STOP:
            self.assertIn(k, I.invite_text(f"Bring your staff ID.\n{k}"), k)
        self.assertEqual(I.invite_text("Welcome\n12-11-2026\nAOB"), "Welcome\n12-11-2026\nAOB")
        self.assertEqual(I.invite_text("Bring your badge.\n12-11-2026"), "Bring your badge.\n12-11-2026")

    def test_dates_still_exempt_under_soft_headings(self):
        for h in SOFT:
            for d in ("12-11-2026", "12 Nov 2026", "12:30"):
                self.assertIn(d, I.invite_text(f"{h}\n{d}"), (h, d))

    def test_mutant_date_rule_off(self):
        m = mutant("(id_number(ln) or _date_ish(ln))", "id_number(ln)")
        self.assertTrue([1 for b, d in ROWS if d in m.invite_text(b)])


class LongWait(unittest.TestCase):
    BODY = "Join with ID, \nReview the code of conduct\n<span>OTP!</b>1234\nPassphrase - Item 1\nPassword policy(staff\n123456"

    def test_reviewers_body_is_a_fixed_point_with_no_value(self):
        once = I.invite_text(self.BODY)
        self.assertEqual(once, "")
        self.assertEqual(I.invite_text(once), once)

    def test_many_removed_lines_between(self):
        for k in range(0, 12):
            junk = "\n".join(f"Password policy({i}" for i in range(k))
            body = f"Meeting ID.\n{junk}\n987654\nAOB"
            once = I.invite_text(body)
            self.assertNotIn("987654", once, k)
            self.assertEqual(I.invite_text(once), once, k)

    def test_with_a_soft_heading_between(self):
        for h in SOFT:
            body = f"Join with ID,\n{h}\n4417\nPassphrase - Item 1\nPassword policy(staff\n123456"
            once = I.invite_text(body)
            self.assertNotIn("4417", once)
            self.assertEqual(I.invite_text(once), once, h)

    def test_instruction_lines_do_not_end_the_wait(self):
        for stop in STOPS:
            for v in ("4417", "12-11-2026", "ZQ7742"):
                once = I.invite_text(f"{stop}\nPlease enter\nPlease enter\n{v}\nAOB")
                self.assertEqual(once, "AOB", (stop, v))
        self.assertIn("Lunch at 12:30", I.invite_text("Bring your staff ID.\nPlease enter\nLunch at 12:30"))

    def test_mutant_wait_dies_on_an_instruction(self):
        m = mutant("(consumed or kind == \"leads\" or weak)", "(consumed or kind == \"leads\")")
        self.assertNotEqual(m.invite_text("Meeting ID.\nPlease enter\n4417"), "")

    def test_mutant_wait_dies_on_a_heading(self):
        m = mutant('(consumed or kind == "leads" or weak) and self.digit_wait', "(consumed or weak) and self.digit_wait")
        once = m.invite_text(self.BODY)
        self.assertNotEqual(m.invite_text(once), once)


WIDE = ["Passcode required:", "Passcode required", "PIN below:", "PIN below", "Access code - Teams", "Access code \u2013 Teams", "Password for new starters",
        "Passcode (Teams) for dial-in:", "Meeting ID for the quarterly review", "Token for the build", "PIN for the card reader",
        "Host key if you are the organiser", "Passcode - see the invite email"]
VALS = ["4417", "987 654 321", "ZQ7742", "hunter", "a1b2c3d4e5", "12-11-2026", "Fri 12 Nov", "1. 4417", "- hunter"]
SENTENCES = ["IT will issue on day one", "Ask the service desk if you are stuck", "Plan the budget for next year"]


class WideNet(unittest.TestCase):
    """Cap: any hard label plus a short phrase stands alone; a hard window removes only value-looking lines (1-2 tokens, numbers, dates,
    hex, mixed letters and digits); a sentence of three or more plain words stays."""

    def test_cap_probe_forms_take_their_value(self):
        bad = [(lab, v) for lab in WIDE for v in VALS for body in (f"{lab}\n{v}\nAOB", f"{lab}\n\n{v}\nAOB", f"- {lab}\n- {v}\nAOB",
               f"<ul><li>{lab}</li><li>{v}</li></ul>") if v.lstrip("-1. ") in I.invite_text(body)]
        self.assertEqual(bad[:3], [])

    def test_a_sentence_below_a_label_stays(self):
        for lab in WIDE:
            for sent in SENTENCES:
                out = I.invite_text(f"{lab}\n{sent}\nAOB")
                self.assertIn(sent, out, (lab, sent))
                self.assertNotIn(lab, out)

    def test_a_value_after_a_sentence_still_goes(self):
        for lab in WIDE:
            for v in ("4417", "ZQ7742", "12-11-2026"):
                self.assertNotIn(v, I.invite_text(f"{lab}\nIT will issue on day one\n{v}\nAOB"), (lab, v))

    def test_capes_agenda_loss_rows(self):
        self.assertEqual(I.invite_text("Password for new starters\nIT will issue on day one\nAOB").split("\n")[0], "IT will issue on day one")
        self.assertEqual(I.invite_text("RAG status\n- Key\n- Red: blocked\n- Amber: at risk\nAOB"), "RAG status\n- Key\n- Red: blocked\n- Amber: at risk\nAOB")

    def test_soft_headings_are_not_qualified_labels(self):
        for h in SOFT:
            self.assertEqual(I.invite_text(f"{h}\nAOB\nNext"), f"{h}\nAOB\nNext")

    def test_a_digit_in_the_phrase_is_a_same_line_value(self):
        for body in ("Passcode required 4417", "PIN below 4417", "Access code - Teams 4417"):
            self.assertEqual(I.invite_text(body + "\nAOB"), "AOB", body)

    def test_provider_suffix_forms_class_b(self):
        for lab in ("Passcode is - Zoom", "PIN to follow - Teams", "Passcode (required) - Zoom", "Access code - Teams:", "Access code - Teams"):
            for v in ("86864", "ZQ6717", "hunter"):
                self.assertEqual(I.invite_text(f"{lab}\n{v}\nAOB"), "AOB", (lab, v))

    def test_header_row_label_class_d(self):
        for body in ("<tr><th>Passcode</th><th>Other</th></tr><tr><td>4417</td><td>x</td></tr>",
                     "<tr><th>Room</th><th>Passcode</th></tr><tr><td>A</td><td>hunter</td></tr>"):
            self.assertEqual(I.invite_text(body), "", body)
        for body in ("| Passcode | Other |\n|---|---|\n| 4417 | x |", "| Passcode | Other |\n|---|---|\n| hunter | x |"):
            self.assertNotIn("4417", I.invite_text(body))
            self.assertNotIn("hunter", I.invite_text(body))

    def test_mutant_window_takes_every_line(self):
        m = mutant("valueish = dropped or _valueish(ln)", "valueish = True")
        self.assertNotIn("IT will issue on day one", m.invite_text("Password for new starters\nIT will issue on day one\nAOB"))

    def test_mutant_no_wide_phrase(self):
        m = mutant('_QPHRASE = rf"', '_QPHRASE = rf"(?!)')
        self.assertIn("4417", m.invite_text("Passcode required:\n4417"))

    def test_mutant_soft_phrases_qualified(self):
        m = mutant("(?!{_SOFT_RUN}){_QUAL}", "{_QUAL}")
        self.assertNotEqual(m.invite_text("Password reset\n12-11-2026\nAOB"), "Password reset\n12-11-2026\nAOB")

    def test_mutant_month_dates_not_values(self):
        m = mutant("_looks_like_value(ln) or _date_ish(rest)", "_looks_like_value(ln)")
        self.assertIn("Fri 12 Nov", m.invite_text("Passcode:\nFri 12 Nov"))


def fuzz_stop(rnd, n):
    """Stop-labels, soft headings and removed junk, then a number, a date or a time among agenda lines."""
    lines, values = [], []
    junk = ["Password policy(staff", "Passphrase - Item 1", "<span>OTP!</b>1234", "https://example.org/j/1", "Review the code of conduct", "Please enter", ""]
    for _ in range(rnd.randint(2, 7)):
        pick = rnd.random()
        if pick < 0.4:
            lines.append(rnd.choice(["", "- ", "1. "]) + rnd.choice(STOPS))
            run_ = [rnd.choice(junk) for _k in range(rnd.randint(0, 6))]
            seen = 0
            for j in run_:
                seen += j == "Please enter"
                lines.append("Password policy(staff" if (j == "Please enter" and seen > 4) else j)      # a fifth instruction line is the stated limit
            v = rnd.choice([f"{rnd.randint(1000, 9999)}{n:05d}", rnd.choice(DATES), f"ZQ{n:05d}", f"{rnd.randint(100, 999)} {rnd.randint(100, 999)} {n:03d}"])
            lines.append(v)
            values.append(v)
        elif pick < 0.6:
            lines.append(rnd.choice(SOFT))
            lines.append(rnd.choice(["AOB", "12:30", "15 Nov 2026", "Next steps"]))
        else:
            lines.append(rnd.choice(["Budget review", "Hiring plan", "Q3 forecast", "AOB", "Lunch at 12:30", "Room 4", "Item 12"]))
    return "\n".join(lines), values


def fuzz_wide(rnd, n):
    """Wide-net labels (any short phrase), sentences, values of every shape, list markers, blank lines and soft headings."""
    marks = ["", "", "- ", "1. ", "* ", "a) "]
    lines, values = [], []
    for _ in range(rnd.randint(2, 7)):
        pick = rnd.random()
        if pick < 0.4:
            lines.append(rnd.choice(marks) + rnd.choice(WIDE + STOPS))
            for _k in range(rnd.randint(0, 3)):
                lines.append(rnd.choice(["", "Please enter", rnd.choice(SENTENCES), "Review the code of conduct"]))
            v = rnd.choice([f"{rnd.randint(1000, 9999)}{n:05d}", f"ZQ{n:05d}", f"zq{n:05d}x", rnd.choice(DATES), "Fri 1 Nov 2030",
                            f"{rnd.randint(100, 999)} {rnd.randint(100, 999)} {n:03d}"])
            lines.append(rnd.choice(marks) + v)
            values.append(v)
        elif pick < 0.55:
            lines.append(rnd.choice(SOFT))
            lines.append(rnd.choice(["AOB", "12:30", "15 Nov 2026", "Next steps"]))
        else:
            lines.append(rnd.choice(["Budget review", "Hiring plan", "Q3 forecast", "AOB", "Lunch at 12:30", "Room 4", rnd.choice(SENTENCES)]))
    return "\n".join(lines), values


def run(make, seed, count):
    rnd = random.Random(seed)
    bad_fixed, bad_value = [], []
    for n in range(count):
        body, values = make(rnd, n)
        once = I.invite_text(body)
        if I.invite_text(once) != once:
            bad_fixed.append(body)
        if any(v in once for v in values):
            bad_value.append(body)
    return bad_fixed, bad_value


class Fuzz(unittest.TestCase):
    def check(self, make, seed, count):
        bf, bv = run(make, seed, count)
        self.assertEqual((len(bf), bf[:1]), (0, []), "not a fixed point after one pass")
        self.assertEqual((len(bv), bv[:1]), (0, []), "a value survives pass one")

    def test_wide_net_bodies(self):
        self.check(fuzz_wide, 2369, 40000)

    def test_stop_label_bodies(self):
        self.check(fuzz_stop, 2269, 40000)

    def test_mixed_bodies_other_seeds(self):
        for seed in (11, 12):
            self.check(lambda r, n: fuzz_mixed(r, n)[:2], seed, 30000)


if __name__ == "__main__":
    unittest.main()
