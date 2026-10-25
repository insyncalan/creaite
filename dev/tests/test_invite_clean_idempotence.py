"""2.6.8 (#369 H1): cleaning a text twice is cleaning it once.

Run: python3 dev/tests/test_invite_clean_idempotence.py      (quick tier: plain code and a throwaway vault, about 15 seconds)

invite_text once ate three more lines after a line ending "password reset" on EVERY clean (8 lines, then 5, then 2), and
sweep.keep_held_past_days cleans every held row on every calendar save. Design (invite_clean._Reader): a finished label phrase opens a
window of three lines only when it LEADS its line ("Password reset", not "IT update: password reset"); and a kept label line whose window
removed any line is itself removed (a tombstone), so a later pass finds no label to open a window on. The value lines still go on the
FIRST pass. Over-removal: a leading "Password reset" / "Code of conduct" line and the next three lines with text.

Team Cap's standing property test is test_calendar_clean_idempotence.py (35 tests); this file adds the sweeps and the mutants:
- AGENDA: Cap's 8-line example, a leading-phrase example, after 1, 2 and 5 passes.
- SWEEP: every single label form and every pair of forms (test_invite_clean_sweep.FORMS), joined by 1, 4 and 7 line breaks, with agenda
  lines before and after and a value, through invite_text, scrub, clean_row and clean_calendar: clean(clean(x)) == clean(x).
- ROWS: rescrub_calendar twice, keep_held_past_days twice, on a calendar full of those bodies.
- MUTANTS: the tombstone removed; the leading-phrase rule removed.
All values are made up.
"""
import importlib.util
import json
import random
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parents[1] / "system" / "scripts"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SCRIPTS))
import invite_clean as I  # noqa: E402
from test_invite_clean_sweep import FORMS  # noqa: E402

AGENDA = "Agenda\n1. IT update: password reset\n2. Budget review\n3. Hiring\n4. Vendors\n5. Risks\n6. Milestones\n7. AOB"
LEADING = "Agenda\nPassword reset\nBudget review\nHiring\nVendors\nRisks\nMilestones\nAOB"
CONDUCT = "Code of conduct\nA\nB\nC\nD\nE"
BEFORE = "Agenda\n1. Welcome\n2. Budget review"
AFTER = "3. Hiring\n4. Vendors\n5. Risks\n6. Milestones"


def passes(fn, x, n=5):
    out = [x]
    for _ in range(n):
        out.append(fn(out[-1]))
    return out


class Agenda(unittest.TestCase):
    def test_a_line_ending_in_the_phrase_opens_nothing(self):
        self.assertEqual(I.invite_text(AGENDA), AGENDA)                                  # all 8 lines, as in 2.6.7

    def test_stable_after_one_two_and_five_passes(self):
        for body in (AGENDA, LEADING, CONDUCT, "Password reset\nBudget review\nHiring\nVendors\nRisks"):
            seen = passes(I.invite_text, body)
            self.assertEqual(seen[1], seen[2], body)
            self.assertEqual(seen[1], seen[5], body)

    def test_the_leading_phrase_costs_exactly_what_the_notes_say(self):
        """Unmarked one- or two-word lines within three lines of a leading heading look like a value and go with it; later lines stay."""
        once = I.invite_text(LEADING)
        self.assertEqual(once, "Agenda\nRisks\nMilestones\nAOB")
        self.assertEqual(I.invite_text(AGENDA.replace("IT update: password reset", "Password reset")), "Agenda\n"
                         "2. Budget review\n3. Hiring\n4. Vendors\n5. Risks\n6. Milestones\n7. AOB".replace("2. Budget review\n3. Hiring\n4. Vendors\n", "1. Password reset\n2. Budget review\n3. Hiring\n4. Vendors\n"))

    def test_the_value_still_goes_on_the_first_pass(self):
        for body in ("Password reset\nhunter", "Password reset\nthe plan\nhunter", "Code of conduct\nrollout\nupdate\nxk7q"):
            self.assertNotIn(body.split("\n")[-1], I.invite_text("Agenda\n" + body), body)


def corpus():
    out = []
    for f in FORMS:
        for gap in ("\n", "\n" * 4, "\n" * 7):
            out.append(BEFORE + "\n" + f + gap + "hunter\n" + AFTER)
    for a in FORMS[::2]:
        for b in FORMS[1::3]:
            out.append(BEFORE + "\n" + a + "\n" + b + "\n4417\n" + AFTER)
    return out


CORPUS = corpus()


def row(body, title="Sync"):
    return {"id": "e1", "start": "09:00", "end": "10:00", "title": title, "where": "Room", "organiser": "Pat", "sensitivity": "normal",
            "teams": True, "body": body, "attendees": [{"name": "Sam", "email": "s@x.example"}]}


class Sweep(unittest.TestCase):
    def test_invite_text_is_idempotent_over_the_label_strings(self):
        bad = [b for b in CORPUS if I.invite_text(I.invite_text(b)) != I.invite_text(b)]
        self.assertEqual((len(bad), bad[:1]), (0, []), f"{len(bad)} of {len(CORPUS)} bodies change on a second clean")

    def test_scrub_rows_and_calendars_are_idempotent(self):
        for b in CORPUS[::7]:
            self.assertEqual(I.scrub(I.scrub(b, 140), 140), I.scrub(b, 140))
            r = I.clean_row(row(b, b[:60]))
            self.assertEqual(I.clean_row(r), r)
        cal = {"fetched": "x", "to": "y", "days": {"2026-10-26": [row(b) for b in CORPUS[::11]]}}
        once = I.clean_calendar(cal)
        self.assertEqual(I.clean_calendar(once), once)

    def test_the_sweep_is_not_trivial(self):
        self.assertGreater(len(CORPUS), 150)
        self.assertTrue(any(I.invite_text(b) != b for b in CORPUS))                       # it does remove things


class Rows(unittest.TestCase):
    def test_rescrub_twice_and_held_rows_twice(self):
        from test_tracker import Vault
        import subprocess
        v = Vault()
        self.addCleanup(v.cleanup)
        cal = v.root / "system/staging/calendar.json"
        cal.parent.mkdir(parents=True, exist_ok=True)
        data = {"fetched": "2026-10-25 08:00", "to": "2026-10-30",
                "days": {"2026-10-24": [row(b) for b in CORPUS[:30]], "2026-10-26": [row(AGENDA), row(LEADING), row(CONDUCT)]}}
        cal.write_text(json.dumps(data), encoding="utf-8")
        code = ("import sys, json; sys.path.insert(0, 'system/scripts')\nimport sweep, paths\n"
                "a = sweep.rescrub_calendar(); one = paths.CALENDAR.read_bytes(); b = sweep.rescrub_calendar(); two = paths.CALENDAR.read_bytes()\n"
                "days = json.loads(two)['days']; k1 = sweep.keep_held_past_days({}, '2026-10-01', '2026-10-25'); "
                "k2 = sweep.keep_held_past_days(k1, '2026-10-01', '2026-10-25')\n"
                "print(json.dumps([b, one == two, k1 == k2]))")
        r = subprocess.run([sys.executable, "-c", code], cwd=v.root, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr[-400:])
        changed_second, same_bytes, same_held = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual((changed_second, same_bytes, same_held), (0, True, True))


AGENDA_LINES = ["Budget review", "Hiring plan", "Vendors", "Risks", "Milestones", "AOB", "Roadmap update", "Q3 forecast", "Next steps",
                "1. Welcome", "2. Budget review", "3. Supplier terms", "Notes: bring laptops", "Café opening hours"]
STOP_LABELS = ["Meeting ID.", "Zoom ID!", "Key,", "Conference ID?", "Webinar ID;", "Meeting ID\u2026"]
ALONE_LABELS = ["Passcode:", "Meeting ID:", "PIN -", "Password \u2013", "Host key:", "Access code is"]
REMOVED = ["https://teams.microsoft.com/l/meetup-join/19%3ameeting_abcDEF", "https://example.zoom.us/j/81234567890?pwd=abc", "Passcode: abcd",
           "Dial-in: +44 20 7946 0958,,55123987#", "Join Microsoft Teams Meeting"]
FUZZ_BODIES = 40000


def fuzz_body(rnd, n):
    """(body, values): units of [label, 0 to 2 removed lines, value] among agenda lines. The values must not survive the first pass."""
    lines, values = [], []
    for _ in range(rnd.randint(2, 7)):
        pick = rnd.random()
        if pick < 0.45:
            lines.append(rnd.choice(AGENDA_LINES))
        elif pick < 0.7:
            lines += [rnd.choice(STOP_LABELS), *rnd.sample(REMOVED, rnd.randint(0, 2)), f"{rnd.randint(1000, 9999)} {n:05d}"]
            values.append(lines[-1])
        elif pick < 0.9:
            lines += [rnd.choice(ALONE_LABELS), *(["_____"] if rnd.random() < 0.2 else []), f"zq{n:05d}x"]
            values.append(lines[-1])
        else:
            lines.append(rnd.choice(["Password reset", "Code of conduct", "IT update: password reset"]))
        lines += [""] * rnd.choice((0, 0, 1, 3))
    return "\n".join(lines), [v for v in values if v.strip("_")]


class Fuzz(unittest.TestCase):
    def test_forty_thousand_bodies_reach_a_fixed_point_with_no_value_after_pass_one(self):
        rnd = random.Random(369)
        bad_fixed, bad_value = [], []
        for n in range(FUZZ_BODIES):
            body, values = fuzz_body(rnd, n)
            once = I.invite_text(body)
            if I.invite_text(once) != once:
                bad_fixed.append(body)
            if any(v in once for v in values):
                bad_value.append(body)
        self.assertEqual((len(bad_fixed), bad_fixed[:1]), (0, []), f"{len(bad_fixed)} bodies are not a fixed point after one pass")
        self.assertEqual((len(bad_value), bad_value[:1]), (0, []), f"{len(bad_value)} bodies keep a value after one pass")

    def test_the_reviewers_examples(self):
        for body, values in (("Meeting ID.\nhttps://teams.microsoft.com/l/meetup-join/x\n1234", ["1234"]), ("Meeting ID.\nPasscode: abc\n1234", ["1234"]),
                             ("Key,\nPasscode: abc\n1. Intro", ["Intro"]), ("Zoom ID!\nDial-in: +44 20 7946 0958,,1234#\n55 66", ["55 66"]),
                             ("Passcode:\n_____\nZQ7742", ["ZQ7742"]), ("Passcode:\n\u2500\u2500\u2500\n\u2022 ZQ7742", ["ZQ7742"]),
                             ("Passcode:\n=====\n.....\n-----\n|||||\nZQ7742", ["ZQ7742"])):
            once = I.invite_text(body)
            self.assertEqual(I.invite_text(once), once, body)
            for v in values:
                self.assertNotIn(v, once, body)

    def test_the_fuzz_is_not_trivial(self):
        rnd = random.Random(369)
        sample = [fuzz_body(rnd, n) for n in range(300)]
        self.assertTrue(any(len(v) >= 2 for _b, v in sample))
        self.assertTrue(any(I.invite_text(b) != b for b, _v in sample))


class Mutants(unittest.TestCase):
    def mutated(self, old, new):
        src = (SCRIPTS / "invite_clean.py").read_text(encoding="utf-8")
        self.assertIn(old, src)
        spec = importlib.util.spec_from_loader("invite_clean_idem_mutant", loader=None)
        mod = importlib.util.module_from_spec(spec)
        mod.__file__ = str(SCRIPTS / "invite_clean.py")
        exec(compile(src.replace(old, new, 1), "invite_clean_idem_mutant", "exec"), mod.__dict__)
        return mod

    def test_without_the_heading_tombstone_pass_two_removes_more(self):
        """A heading whose window removed a line must go with it: kept, the lines past the first window shift into a later pass."""
        body = "Agenda\nPassword reset\nhunter\nHere is a plan for you\nHere is more text now\nvalue1x"
        once = I.invite_text(body)
        self.assertEqual(I.invite_text(once), once)
        m = self.mutated("                self.kept[window[1]] = None    # a line of the heading's window", "                pass    # a line of the heading's window")
        self.assertNotEqual(m.invite_text(m.invite_text(body)), m.invite_text(body))

    def test_without_the_hard_window_tombstone_pass_two_removes_more(self):
        body = "Agenda\nPassword reset for\nsome text here today\nmore text here today\nthird text here today\nfourth text here today"
        once = I.invite_text(body)
        self.assertEqual(I.invite_text(once), once)
        m = self.mutated("                self.kept[at] = None", "                pass")
        self.assertNotEqual(m.invite_text(m.invite_text(body)), m.invite_text(body))

    def test_digit_wait_dropped_by_a_removed_line_leaks_and_is_not_a_fixed_point(self):
        m = self.mutated("self.digit_wait = _ends_on_key_and_stop(ln) or bool(consumed and self.digit_wait and not value)", "self.digit_wait = _ends_on_key_and_stop(ln)")
        body = "Meeting ID.\nPasscode: abc\n1234"
        once = m.invite_text(body)
        self.assertIn("1234", once)                                       # the value stays after pass 1...
        self.assertNotEqual(m.invite_text(once), once)                    # ...and pass 2 removes it

    def test_a_line_of_underscores_is_content_in_the_mutant(self):
        m = self.mutated('not re.search(r"[^\\W_]", ln))', 'not re.search(r"\\w", ln))')
        self.assertIn("ZQ7742", m.invite_text("Passcode:\n_____\nZQ7742"))

    def test_without_the_leading_rule_a_line_ending_in_the_phrase_opens_a_window(self):
        m = self.mutated("return not _PROSE.search(before) and len(before.split()) <= 3", "return True")
        body = "Agenda\nIT update: password reset\nBudget review\nHiring\nVendors"
        self.assertEqual(I.invite_text(body), body)
        self.assertNotEqual(m.invite_text(body), body)

    def test_the_two_exact_cases_of_cap(self):
        for body, gone in (("Meeting ID.\nPasscode:\n4417\n987 654 321", ["4417", "987 654 321"]),
                           ("Meeting ID.\nhttps://teams.microsoft.com/l/meetup-join/x\n1234", ["1234"]),
                           ("Meeting ID.\nPasscode: abc\n1234", ["1234"]), ("Key,\nPasscode: abc\n1. Intro", ["Intro"])):
            once = I.invite_text(body)
            self.assertEqual(I.invite_text(once), once, body)
            for v in gone:
                self.assertNotIn(v, once, body)


if __name__ == "__main__":
    unittest.main()
