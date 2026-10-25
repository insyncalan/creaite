"""#375 E1 (2.6.9 item 1): ordinary numbers must not cost a block under the anchor layer's digit-run rule.

The shape table (invite_filter.SHAPES) names every number shape that is set aside before the 7-digit rule runs. This file tests
each shape (positives that must be set aside, negatives that must still anchor), a mutant per shape, the dial strings and ids that
must STILL be anchors, the lone-token gate, the six provider generators (leak 0), and, on a seeded 20,000-body number-heavy
generator, the subset and idempotence laws. `python3 dev/tests/test_invite_filter_numbers.py --report` prints the loss table
(agenda_isolated, 32 formats, the measure behind finding 4 of dev/proposals/375/ADVERSARIAL.md). All data is fictional.
"""
import random
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
import invite_filter as F  # noqa: E402

N_PROP = 20000

PLAIN = ["Welcome and apologies", "Review of last month's actions", "Hiring update for the platform team", "Vendor contract renewal",
         "Risks and issues log", "Demo of the new dashboard", "Any other business", "Next steps and owners"]

# ordinary agenda content with numbers; each (tag, line maker). None of it is a secret, all of it must survive.
AGENDA_FORMATS = [
    ("time24", lambda r: "Start at %02d:%02d" % (r.randint(8, 17), r.choice([0, 15, 30, 45]))),
    ("time_range_colon", lambda r: "Slot %02d:00-%02d:30" % (r.randint(8, 15), r.randint(9, 17))),
    ("time_range_dot", lambda r: "Slot %02d.00 - %02d.30" % (r.randint(8, 12), r.randint(13, 17))),
    ("time_range_compact", lambda r: "Slot %02d00-%02d30" % (r.randint(8, 12), r.randint(13, 17))),
    ("year", lambda r: "Plan for %d" % r.randint(2024, 2030)),
    ("year_range_dash", lambda r: "Budget %d-%d" % (2026, 2027)),
    ("year_range_spaced", lambda r: "Budget %d - %d" % (2026, 2027)),
    ("money_comma", lambda r: "Budget: £%s,%03d,%03d" % (r.randint(1, 9), r.randint(0, 999), r.randint(0, 999))),
    ("money_dot", lambda r: "Budget: %d.%03d.%03d €" % (r.randint(1, 9), r.randint(0, 999), r.randint(0, 999))),
    ("money_space", lambda r: "Budget: %d %03d %03d kr" % (r.randint(1, 9), r.randint(0, 999), r.randint(0, 999))),
    ("money_plain7", lambda r: "Budget: £%d" % r.randint(1000000, 9999999)),
    ("money_plain5", lambda r: "Spend so far: £%d" % r.randint(10000, 99999)),
    ("headcount", lambda r: "Headcount %d to %d" % (r.randint(10, 99), r.randint(100, 999))),
    ("room", lambda r: "Room %d.%02d" % (r.randint(1, 9), r.randint(1, 40))),
    ("room_floor", lambda r: "Floor %d, Room %d" % (r.randint(1, 9), r.randint(100, 999))),
    ("version", lambda r: "Release v%d.%d.%d" % (r.randint(1, 9), r.randint(0, 20), r.randint(0, 20))),
    ("version4", lambda r: "Build %d.%d.%d.%d" % (r.randint(1, 9), r.randint(0, 20), r.randint(0, 20), r.randint(1000, 99999))),
    ("iso_date", lambda r: "Deadline 2026-11-%02d" % r.randint(1, 28)),
    ("dot_date", lambda r: "Deadline %02d.11.2026" % r.randint(1, 28)),
    ("long_date", lambda r: "Deadline %d November 2026" % r.randint(1, 28)),
    ("date_time", lambda r: "Cut-over 2026-11-%02d 22:00" % r.randint(1, 28)),
    ("compact_date", lambda r: "Snapshot 2026%02d%02d" % (r.randint(1, 12), r.randint(1, 28))),
    ("numbering", lambda r: "%d.%d.%d Risk review" % (r.randint(1, 9), r.randint(1, 9), r.randint(1, 9))),
    ("po_number", lambda r: "PO %d" % r.randint(4500000000, 4599999999)),
    ("ticket", lambda r: "Ticket INC%07d" % r.randint(1, 9999999)),
    ("jira", lambda r: "Ref PLAT-%d" % r.randint(100, 9999)),
    ("percent", lambda r: "Utilisation %d.%d%%" % (r.randint(50, 99), r.randint(0, 9))),
    ("postcode", lambda r: "Venue: 1 Example Street, SW1A %dAA" % r.randint(1, 9)),
    ("zip", lambda r: "Venue: Example Plaza, %05d Berlin" % r.randint(10000, 99999)),
    ("room_phone", lambda r: "Room phone %d-%04d" % (r.randint(1, 9), r.randint(0, 9999))),
    ("fy_range", lambda r: "FY%d/%d targets" % (26, 27)),
    ("plain_words", lambda r: r.choice(PLAIN)),
]
# not in the 32 above: three numbers in a row ("Counts: 752 637 814") is the shape of a 3+3+3 meeting id and stays an anchor.


def kept(text):
    return F.filter_text_with_scrub(text)


def lost_lines(lines, text=None):
    out = set((text if text is not None else kept("\n\n".join(lines))).split("\n"))
    return [x for x in lines if x not in out]


def measure_isolated(n=3000, seed=7):
    """Per format and in total: ordinary lines (each alone in its block) the default filter loses."""
    rng = random.Random(seed)
    per = {t: [0, 0] for t, _ in AGENDA_FORMATS}
    for _ in range(n):
        picks = [rng.choice(AGENDA_FORMATS) for _ in range(rng.randint(3, 6))]
        lines = [mk(rng) for _, mk in picks]
        lost = set(lost_lines(lines))
        for (t, _), ln in zip(picks, lines):
            per[t][0] += 1
            per[t][1] += ln in lost
    return per


def measure_list(n=3000, seed=8):
    """A numbered agenda block with one number line among ordinary ones: (trigger lines lost, neighbour lines lost, lines)."""
    rng = random.Random(seed)
    trig = neigh = tot = 0
    for _ in range(n):
        t, mk = rng.choice(AGENDA_FORMATS)
        special = mk(rng)
        lines = ["Agenda"] + ["%d. %s" % (i + 1, rng.choice(PLAIN)) for i in range(rng.randint(2, 5))]
        lines.insert(rng.randint(1, len(lines)), special)
        out = set(kept("Hello.\n\n" + "\n".join(lines)).split("\n"))
        for x in lines:
            tot += 1
            if x not in out:
                if x == special:
                    trig += 1
                else:
                    neigh += 1
    return trig, neigh, tot


def report():
    per = measure_isolated()
    n = sum(v[0] for v in per.values())
    lost = sum(v[1] for v in per.values())
    print("agenda_isolated: %d of %d lines lost (%.1f%%)" % (lost, n, 100.0 * lost / n))
    bad = [(t, v) for t, v in per.items() if v[1]]
    print("formats lost: %d of %d" % (sum(1 for _, v in bad if v[1] == v[0]), len(per)))
    for t, v in bad:
        print("  %-20s %d of %d" % (t, v[1], v[0]))
    print("agenda_list (trigger lost, neighbours lost, lines): %s" % (measure_list(),))


# ======================================================================================== shapes

SHAPE_NAMES = [s[0] for s in F.SHAPES] if hasattr(F, "SHAPES") else []


def anchored(line):
    return F._has_anchor(F._skeleton(line))


# (shape, positives: set aside, no anchor; negatives: still an anchor)
SHAPE_CASES = {
    "compact_date": (["Snapshot 20261112", "20261112T140000Z", "Due 20260131"],
                     ["Code 20261312", "Code 20261132", "Code 18501112", "Code 202611121"]),
    "time_range": (["Slot 14.00 - 15.30", "Slot 14.00-15.30", "Slot 9.00 - 12.15", "Slot 14:00-15:30"],
                   ["Code 14.60 - 15.30 5555", "Code 25.00 - 26.30 5555", "Code 14.00-15.30-1234"]),
    "time_range_compact": (["Slot 1400-1530", "Slot 0900 - 1215"], ["Code 1730-1530", "Code 2575-2650", "Code 1400-1530-123", "Code 123-456-789"]),
    "year_range": (["Budget 2026-2027", "Budget 2026 - 2027", "Budget 2025 – 2028", "Plan 1999-2001"],
                   ["Code 2027-2026", "Code 2026-2099", "Code 2026-20271", "Code 2026-2027-81"]),
    "money": (["Budget: £1250000", "Budget: 1.250.000 €", "Budget: 1 250 000 kr", "Budget: $1,250,000", "Cost €12345678", "Budget: 1250000 EUR",
               "Budget 3 400 000 usd", "Budget £1.250.000,50"],
              ["Meeting ID 1250000", "Dial 1 250 000", "Code 1.250.000", "ID 123 456 789 kr9"]),
    "build_number": (["Build 3.14.2.1007", "Build 3.14.2.1007.5", "Release 12.4.0.88231"],
                     ["Call +44.20.7946.0958", "Call 44.20.7946.0958", "Call 12.345.678.901", "Call 3.14.02.1007"]),
    "po_ticket": (["PO 4500123456", "PO no. 4500123456", "Ticket INC0012345", "Invoice #20261234", "Order: 100234567",
                   "Req REQ0012345"],
                  ["Meeting ID 4500123456", "ID9876543", "ref 1234567", "ref-1234567", "Code 1234567", "PIN 4500123456", "Phone 4500123456", "Conf1234567", "Dial: 4500123456"]),
}
# real dial strings, ids and plain long numbers: every one must STILL be an anchor
MUST_ANCHOR = ["123 4567 8901", "123-456-789", "+1 555 010 0199", "987654321#", "412 889 330 22", "+44 20 7946 0958", "752 637 814",
               "Meeting ID: 412 889 330", "+44 20 7946 0958,,123456789#", "Call +44 7700 900123", "1234567", "Conference 987 654 321 0",
               "555.010.0199", "Budget: 1250000"]


class ShapeTable(unittest.TestCase):
    def test_table_has_a_name_and_a_reason_each(self):
        self.assertGreaterEqual(len(F.SHAPES), 6)
        names = [s[0] for s in F.SHAPES]
        self.assertEqual(len(names), len(set(names)))
        for s in F.SHAPES:
            self.assertEqual(len(s), 4)
            self.assertTrue(s[3].strip(), s[0])
        self.assertEqual(set(SHAPE_CASES) | {"date"}, set(names))

    def test_positives_are_not_anchors(self):
        for name, (pos, _) in SHAPE_CASES.items():
            for p in pos:
                self.assertFalse(anchored(p), (name, p))

    def test_negatives_are_anchors(self):
        for name, (_, neg) in SHAPE_CASES.items():
            for p in neg:
                self.assertTrue(anchored(p), (name, p))

    def test_dial_strings_and_ids_stay_anchors(self):
        for p in MUST_ANCHOR:
            self.assertTrue(anchored(p), p)

    def test_each_positive_survives_the_whole_filter(self):
        for name, (pos, _) in SHAPE_CASES.items():
            for p in pos:
                self.assertEqual(kept("Hello.\n\n" + p + "\nSecond line."), "Hello.\n\n" + p + "\nSecond line.", (name, p))

    def test_a_label_still_removes_a_shape_looking_secret(self):
        for t in ["Meeting ID: 2026-2027", "Passcode: 20261112", "Meeting ID: 14.00 - 15.30", "Passcode: INC0012345", "PIN: 3.14.2.1007",
                  "Meeting ID: 1.250.000"]:
            out = kept("Intro.\n\n" + t + "\n\nOutro.")
            self.assertNotIn(t, out)
            self.assertIn("Outro.", out)

    def test_a_number_line_next_to_a_dial_string_goes_with_the_block(self):
        self.assertEqual(F.keep_lines(["Slot 14.00 - 15.30", "+44 20 7946 0958"], second_layer=False), [])

    def test_shape_does_not_hide_a_second_run(self):
        self.assertTrue(anchored("Budget 2026-2027 id 4412 8890 1"))
        self.assertTrue(anchored("PO 4500123456 and 987654321"))


class Mutants(unittest.TestCase):
    """Each shape's matcher is exercised: with that shape removed from the table the positives anchor again (the tests would fail)."""

    def test_mutant_per_shape(self):
        orig = F.SHAPES
        try:
            for i, (name, _) in enumerate((s[:2] for s in orig)):
                if name == "date":
                    continue
                F.SHAPES = tuple(s for j, s in enumerate(orig) if j != i)
                self.assertTrue(any(anchored(p) for p in SHAPE_CASES[name][0]), "removing %s changes nothing" % name)
        finally:
            F.SHAPES = orig

    def test_mutant_no_shapes_at_all_loses_blocks(self):
        orig = F.SHAPES
        try:
            F.SHAPES = ()
            self.assertEqual(kept("Agenda\n1. Welcome\n2. Budget: £1250000\n3. Next steps"), "")
        finally:
            F.SHAPES = orig

    def test_mutant_validators_reject_bad_values(self):
        for bad in ("Code 2027-2026", "Code 1730-1530", "Code 20261312", "Call 12.345.678.901"):
            self.assertTrue(anchored(bad), bad)


class LoneToken(unittest.TestCase):
    """The shape gate on a lone token: a bare 5+ digit line stays dropped (PIN safety); ordinary id-like words are kept."""

    def test_bare_digits_stay_dropped(self):
        for t in ["125000", "20000", "90210", "12345", "8825"[:0] or "123456"]:
            self.assertEqual(kept("Status.\n\n" + t + "\n\nBye."), "Status.\n\nBye.", t)

    def test_four_digits_stay(self):
        self.assertIn("2026", kept("Status.\n\n2026\n\nBye."))

    def test_grouped_and_unit_bearing_stay(self):
        for t in ["125,000", "125.000", "£125000", "125000 EUR", "125000 kr", "2026-2027", "14.00-15.30"]:
            self.assertIn(t, kept("Status.\n\n" + t + "\n\nBye."), t)

    def test_ordinary_prefixed_ids_stay(self):
        for t in ["Room204", "Q42026", "Level4", "INC001", "INC0012345", "Floor12", "Sprint14", "FY2026"]:
            self.assertIn(t, kept("Status.\n\n" + t + "\n\nBye."), t)

    def test_other_alnum_tokens_stay_dropped(self):
        for t in ["Summer2026", "xk9Pq27a", "abc12345", "Pass1234", "Pin8825", "Token99"]:
            self.assertNotIn(t, kept("Status.\n\n" + t + "\n\nBye."), t)

    def test_table_cells(self):
        html = "<p>Status.</p><table><tr><td>Design</td><td>%s</td><td>Mia Hale</td></tr></table>"
        for cell, keep in [("125000", False), ("Room204", True), ("Q42026", True), ("Level4", True), ("INC001", True), ("20000", False),
                           ("2026", True), ("14:00", True)]:
            self.assertEqual(cell in F.filter_text(html % cell, second_layer=False), keep, cell)
            self.assertIn(cell, kept(html % cell))      # the default order (D) reads the row as one line: no cell is judged alone


# ======================================================================================== providers, properties

class Providers(unittest.TestCase):
    TEMPLATES = {
        "teams": ["Microsoft Teams Need help?", "Join the meeting now", "Meeting ID: {id}", "Passcode: {pc}", "Dial in by phone",
                  "+44 20 7946 0958,,{conf}# United Kingdom, London", "Phone conference ID: {conf}#", "Video ID: {vid}"],
        "zoom": ["Join Zoom Meeting", "https://zoom.example.test/j/{idraw}?pwd={pw}", "Meeting ID: {id}", "Passcode: {pc}", "One tap mobile",
                 "+442034815240,,{idraw}#,,,,*{pc}# United Kingdom", "Dial by your location", "• +44 203 481 5240 United Kingdom"],
        "webex": ["Join meeting", "Meeting number (access code): {id}", "Meeting password: {pw8}", "+1-415-655-0001 US Toll", "Access code: {id}"],
        "meet": ["Join with Google Meet", "meet.example.test/abc-defg-hij", "Or dial: (GB) +44 20 7946 0958 PIN: {conf}#"],
        "bluejeans": ["Join the meeting", "Meeting ID {idraw}", "Participant Passcode {pc}", "Dial-in: +1 555 010 4477"],
        "gotomeeting": ["Access Code: {id3}", "Phone: +1 (555) 010-4477"],
    }

    def test_six_providers_leak_nothing_and_keep_the_note(self):
        rng = random.Random(11)
        leaks = 0
        for _ in range(600):
            for tpl in self.TEMPLATES.values():
                d = "".join(rng.choice("0123456789") for _ in range(9))
                ctx = dict(id="%s %s %s" % (d[:3], d[3:6], d[6:]), idraw=d, id3="%s-%s-%s" % (d[:3], d[3:6], d[6:]), pc="%06d" % rng.randint(0, 999999),
                           conf=str(rng.randint(10 ** 8, 10 ** 9 - 1)), vid="%d" % rng.randint(10 ** 9, 10 ** 10 - 1), pw="ab%dXyz" % rng.randint(100, 999),
                           pw8="Qw%dzxcv" % rng.randint(10, 99))
                body = "Budget 2026 - 2027 agreed.\n\nSlot 14.00 - 15.30\n\n________\n" + "\n".join(x.format(**ctx) for x in tpl) + "\n________\n\nSee you there."
                out = kept(body)
                digs = [v for k, v in ctx.items() if k in ("idraw", "conf", "vid") and v in re.sub(r"[\s-]", "", out)]
                leaks += bool(digs) or ctx["pc"] in out
                self.assertIn("Slot 14.00 - 15.30", out)
                self.assertIn("See you there.", out)
        self.assertEqual(leaks, 0)


def number_body(rng):
    parts = []
    for _ in range(rng.randint(2, 6)):
        t, mk = rng.choice(AGENDA_FORMATS)
        k = rng.random()
        if k < 0.55:
            parts.append(mk(rng))
        elif k < 0.7:
            parts.append("Meeting ID: %s" % " ".join(str(rng.randint(100, 999)) for _ in range(3)))
        elif k < 0.8:
            parts.append(rng.choice(["+44 20 7946 0958", "123 4567 8901", "987654321#", "752 637 814", "1234567", "Passcode: 4417", "125000"]))
        elif k < 0.9:
            parts.append(" ".join(mk(rng) for _ in range(2)))
        else:
            parts.append(rng.choice(["", "_____", "Thanks,"]))
    sep = rng.choice(["\n", "\n\n", "\n"])
    return sep.join(parts)


class Properties(unittest.TestCase):
    def test_subset_and_idempotent_on_20000_bodies(self):
        rng = random.Random(375)
        for _ in range(N_PROP):
            body = number_body(rng)
            lines = body.split("\n")
            keep = F.keep_lines(lines, second_layer=False)
            it = iter(lines)
            self.assertTrue(all(any(x == y for y in it) for x in keep), body)
            again = F.keep_lines(keep, second_layer=False)
            self.assertEqual(F._tidy_blanks(again), F._tidy_blanks(keep), body)
            out = kept(body)
            self.assertEqual(kept(out), out, body)

    def test_shapes_only_ever_keep_more_never_less_than_no_shapes(self):
        rng = random.Random(376)
        orig = F.SHAPES
        for _ in range(3000):
            lines = number_body(rng).split("\n")
            with_shapes = set(F.keep_indices(lines, second_layer=False))
            try:
                F.SHAPES = ()
                without = set(F.keep_indices(lines, second_layer=False))
            finally:
                F.SHAPES = orig
            self.assertTrue(without <= with_shapes, lines)


class Losses(unittest.TestCase):
    def test_no_number_format_is_lost(self):
        per = measure_isolated(1500)
        lost = {t: v for t, v in per.items() if v[1]}
        self.assertEqual(lost, {})

    def test_agenda_list_keeps_neighbours(self):
        trig, neigh, tot = measure_list(1000)
        self.assertEqual((trig, neigh), (0, 0))


if __name__ == "__main__":
    if "--report" in sys.argv:
        report()
    else:
        unittest.main()
