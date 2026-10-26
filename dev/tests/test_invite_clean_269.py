"""2.6.9 scrub (#369 follow-ups H2, H4, qualified separators, label-word agenda lines): rows, a 40,000-body seeded generator and an
agenda-survival measurement for invite_clean. All values are made up.

Run: python3 dev/tests/test_invite_clean_269.py            (5,000 bodies per generator, about a minute)
     FUZZ_FULL=1 python3 dev/tests/test_invite_clean_269.py   (40,000 bodies per generator)
     FUZZ_SEED=n sets the seed (default 269).

What is pinned, and what stays a measured limit, is in dev/proposals/bare/NOTES-2.6.9-scrub.md.

Properties of every generated body: (a) invite_text(invite_text(x)) == invite_text(x); (b) no planted number survives (the planted values
all hold digits); (c) in a same-line shape the ordinary lines around the label all survive (nothing is eaten); (d) a title or place made
of the same line is scrubbed to "".
"""
import os
import random
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "system" / "scripts"))
import invite_clean as I  # noqa: E402

SEED = int(os.environ.get("FUZZ_SEED", "269"))
FULL = os.environ.get("FUZZ_FULL") == "1"
PER = 40000 if FULL else 5000

ID_LABELS = ["Meeting ID", "Meeting number", "Webinar ID", "Conference ID", "Zoom ID", "Teams meeting ID", "Join ID", "Event number",
             "Session ID", "Meeting No.", "Zoom Meeting ID", "Webex meeting number"]
QUALS = ["below", "required", "if asked", "if prompted", "to join", "for Teams", "for Zoom", "for the call", "for dial-in",
         "for the weekly sync", "(Teams)", "(organiser only)", "(Zoom) for guests", "to follow", "for the room", "is"]
SAME_SEPS = ["", " ", "-", "–", "—", "=", "→", ">", "|", "\t", " is ", " was ", "(", ":", ": ", " - "]
PROVIDERS = ["Zoom", "Teams", "Webex", "Skype", "Meet", "GoToMeeting", "BlueJeans", "Microsoft Teams", "Google Meet", "Whereby"]
PROV_SEPS = ["", " ", ":", ": ", "-", "–", "—", "=", "→", " - ", "(", "|", " | ", "#"]
NEXT_QUALS = ["required", "below", "for dial-in", "for the weekly 1:1", "for Teams", "to join", "if asked", "(Teams)", "- Zoom",
              "/ dial-in", "for the call"]
NEXT_LABELS = ["Passcode", "PIN", "Password", "Access code", "Meeting ID", "Host key", "Webinar ID", "Conference ID", "Meeting number"]
NEXT_ENDS = ["", ":", ",", ";", "/", "-", "–", ".", " |", ":", "→"]
FILL = ["Agenda", "Welcome and apologies", "Budget review", "Hiring update", "Vendors", "Risks and issues", "Milestones", "AOB",
        "Questions for the team", "Notes from last time", "Next steps", "Sprint demo", "Supplier contract renewal"]


def digits(r, kind=None):
    k = kind or r.choice(["long", "grouped9", "grouped10", "grouped11", "dashed", "plain6"])
    d = lambda n: "".join(r.choice("0123456789") for _ in range(n))
    first = lambda: r.choice("123456789")
    if k == "long":
        return first() + d(r.randint(8, 10))
    if k == "grouped9":
        return " ".join(first() + d(2) if i == 0 else d(3) for i in range(3))
    if k == "grouped10":
        return first() + d(2) + " " + d(4) + " " + d(4)
    if k == "grouped11":
        return first() + d(3) + " " + d(3) + " " + d(3) + " " + d(2)
    if k == "dashed":
        return first() + d(2) + "-" + d(3) + "-" + d(4)
    return first() + d(r.randint(5, 6))


def fill(r, n):
    return [r.choice(FILL) for _ in range(n)]


def g_same_line(r):
    """H2: a qualified ID label, a qualifier, a separator (or none) and the number on ONE line. H4: a provider and a number."""
    out, secrets, ordinary = [], [], fill(r, r.randint(1, 3))
    for _ in range(r.randint(1, 2)):
        v = digits(r)
        if r.random() < 0.5:
            line = r.choice(ID_LABELS) + " " + r.choice(QUALS) + r.choice(SAME_SEPS) + v
        else:
            line = r.choice(PROVIDERS) + r.choice(PROV_SEPS) + v
        if r.random() < 0.3:
            line = r.choice(["Join ", "Call: ", "Dial ", ""]) + line
        secrets.append(v)
        out.append(line)
    lines = ordinary[:1] + out + ordinary[1:]
    r.shuffle(lines) if r.random() < 0.3 else None
    body = "\n".join(lines)
    if r.random() < 0.25:
        body = "".join(f"<p>{x}</p>" for x in lines)
    return body, secrets, ordinary, out


def g_next_line(r):
    """The qualified-separator shapes: a label, a qualifier, any separator or none, the value on a line of its own."""
    lines, secrets, ordinary = fill(r, r.randint(0, 2)), [], []
    for _ in range(r.randint(1, 2)):
        v = digits(r)
        label, qual, end = r.choice(NEXT_LABELS), r.choice(NEXT_QUALS), r.choice(NEXT_ENDS)
        head = label + " " + qual + end if not qual.startswith("/") else label + " " + qual + end
        if r.random() < 0.2:
            head = label + ", " + qual + end
        lines.append(head)
        if r.random() < 0.2:
            lines.append("")
        lines.append(v)
        secrets.append(v)
        lines += fill(r, r.randint(0, 2))
    body = "\n".join(lines)
    if r.random() < 0.25:
        body = "".join(f"<p>{x}</p>" for x in lines)
    return body, secrets, ordinary, []


def g_eaters(r):
    """Agendas with label-word lines (Pin board, Token budget, ... ) mixed with ordinary lines and numbers planted at most three lines
    below one: the number must go (idempotently) and the ordinary lines below must stay."""
    heads = ["Pin board", "Token budget", "Pin the roadmap", "Secret Santa party", "Password reset \u2013 ABC", "Code review \u2013 ABC",
             "Token refresh", "Password reset", "Code of conduct"]
    lines, secrets, keep = fill(r, r.randint(0, 2)), [], []
    for _ in range(r.randint(1, 3)):
        lines.append(r.choice(heads))
        for _ in range(r.randint(0, 2)):
            x = r.choice(["Training dates", "Sign-off", "Reporting line", "Lunch at 12:30", "Go/no-go", "Q3 forecast"])
            lines.append(x)
            keep.append(x)
        if r.random() < 0.6:
            v = digits(r, r.choice(["long", "grouped9", "plain6"]))
            lines.append(v)
            secrets.append(v)
        lines += fill(r, r.randint(0, 2))
    if r.random() < 0.3:
        lines = [f"{n}. {x}" for n, x in enumerate(lines, 1)]
    body = "\n".join(lines)
    if r.random() < 0.25:
        body = "<ul>" + "".join(f"<li>{x}</li>" for x in lines) + "</ul>"
    return body, secrets, keep, []


GENERATORS = [("same_line", g_same_line), ("next_line", g_next_line), ("eaters", g_eaters)]


def digits_of(s):
    return re.sub(r"\D", "", s)


def check(body, secrets, ordinary, same):
    """[(property, detail)] for every property this body breaks."""
    once = I.invite_text(body)
    bad = []
    if I.invite_text(once) != once:
        bad.append(("idempotence", body))
    flat = re.sub(r"[\s\-]+", "", once)
    for v in secrets:
        if v in once or re.sub(r"[\s\-]+", "", v) in flat:
            bad.append(("leak", v))
    lost = [o for o in ordinary if o not in once]
    if lost:
        bad.append(("eaten", lost[0]))
    if same:
        for line in same:
            if I.scrub(line, 140):
                bad.append(("field", line))
    return bad


def cases(name, gen, n, seed=SEED):
    r = random.Random(f"{seed}-{name}")
    for _ in range(n):
        yield gen(r)


def run(name, gen, n=PER, seed=SEED):
    """{property: [first bodies]} for n bodies."""
    broken = {"idempotence": [], "leak": [], "eaten": [], "field": []}
    for body, secrets, ordinary, same in cases(name, gen, n, seed):
        for p, d in check(body, secrets, ordinary, same):
            broken[p].append((body, d))
    return broken


# ---- agenda survival: 200 ordinary lines, placed in agendas of 5 lines in four layouts ----
TRAPS = ["Pin board", "Token budget", "Dress code for visitors", "Cost code changes", "Pin the roadmap", "Password reset rollout",
         "Access code rollout", "Secret Santa party", "Code of conduct refresh", "Key milestones", "Zip code lookup", "Code sprint",
         "Password reset", "Code review", "Token refresh", "Passcode policy review", "Meeting ID badges", "API key rotation",
         "Password reset \u2013 ABC", "Code review \u2013 ABC", "Token refresh \u2013 ABC", "Password for the HR portal", "Zoom licences renewal", "Teams adoption plan", "Webex retirement", "Meet the new starters", "Teams 2026 roadmap",
         "Zoom 2026 budget", "Meeting number of attendees", "Meeting ID card replacement"]
ORDINARY = ["Welcome and apologies", "Budget review", "Hiring update", "Vendors", "Risks and issues", "Milestones", "AOB", "Sprint demo",
            "Supplier contract renewal", "Lunch at 12:30", "Room 4", "Item 12", "Q3 forecast", "Go/no-go", "Sign-off", "Reporting line",
            "Training dates", "Security review", "Data migration", "Release plan", "Customer feedback", "Test results", "Roadmap update",
            "Resourcing", "Governance", "Dependencies", "Change requests", "Lessons learned", "Quarter close", "Demo day",
            "Procurement", "Legal review", "Comms plan", "Onboarding", "Retro", "Capacity", "Estimates", "Architecture decision",
            "Stakeholder map", "Next steps"]


def agenda_set(seed=SEED):
    """200 lines: every trap line and ordinary line, repeated with different neighbours; [(body, [lines that must be kept])]."""
    r = random.Random(f"agenda-{seed}")
    pool = [*TRAPS, *ORDINARY] * 3
    r.shuffle(pool)
    pool = pool[:200]
    out = []
    for i in range(0, len(pool), 5):
        lines = pool[i:i + 5]
        layout = (i // 5) % 4
        if layout == 0:
            body = "Agenda\n" + "\n".join(f"{n}. {x}" for n, x in enumerate(lines, 1))
        elif layout == 1:
            body = "Agenda\n" + "\n".join(lines)
        elif layout == 2:
            body = "Agenda\n" + "\n".join(f"- {x}" for x in lines)
        else:
            body = "<ul>" + "".join(f"<li>{x}</li>" for x in lines) + "</ul>"
        out.append((body, lines))
    return out


def agenda_kept(seed=SEED):
    """(lines kept, lines in total, [lost lines]) over the agenda set."""
    kept = total = 0
    lost = []
    for body, lines in agenda_set(seed):
        once = I.invite_text(body)
        have = {re.sub(r"^(?:\d+\.|-)\s+", "", x) for x in once.split("\n")}
        for x in lines:
            total += 1
            if x in have:
                kept += 1
            else:
                lost.append(x)
    return kept, total, lost


# ---- rows and mutants ----
SCRIPTS = HERE.parents[1] / "system" / "scripts"


def mutant(old, new):
    import importlib.util
    src = (SCRIPTS / "invite_clean.py").read_text(encoding="utf-8")
    assert old in src, old
    spec = importlib.util.spec_from_loader("invite_clean_269m", loader=None)
    mod = importlib.util.module_from_spec(spec)
    mod.__dict__["__file__"] = str(SCRIPTS / "invite_clean.py")
    exec(compile(src.replace(old, new, 1), "invite_clean_269m", "exec"), mod.__dict__)
    return mod


H2_ROWS = ["Meeting ID below: 345 678 912 345", "Meeting ID required: 345 678 912 345", "Meeting ID for the weekly sync 345 678 912 345",
           "Meeting ID (Teams) 987 654 321", "Meeting ID if asked 987654321", "Meeting number to join - 482915", "Webinar ID for Zoom = 987 654 321",
           "Meeting ID for Teams \u2192 345 678 912", "Meeting ID to join > 345-678-912", "Meeting ID required | 987 654 321",
           "Meeting ID required\t987 654 321", "Meeting ID is 987 654 321", "Meeting ID was 987 654 321", "Conference ID (organiser only) 4829157",
           "Webex meeting number below 2552 123 4567", "Meeting ID for the call (Teams) \u2014 345 678 912 345"]
H4_ROWS = ["Zoom 482 915 7731", "Teams 123 456 789", "Webex 2552 123 4567", "Zoom: 855 1234 5678", "Steering (Teams 345 678 912 345)",
           "Zoom-482-915-7731", "Teams \u2013 345 678 912 345", "Webex meeting 2552 123 4567", "Skype 482915", "Google Meet 345 678 912",
           "Join Zoom 482 915 7731 now", "Zoom \u2192 855 1234 5678"]
STAY = ["Teams 2026 roadmap", "Zoom 2026 budget", "Teams 365 licences", "Q3 2026 Teams rollout", "Meet 12 Nov 2026", "Zoom 2026-11-12",
        "Meeting number of attendees 12", "Meeting ID card renewal 2026", "Meet the team 12:30", "Webex retirement plan", "Room 4",
        "Teams adoption plan 2026", "Zoom licences: 40"]
SEPARATORS = [("Passcode, for dial-in:", "4417"), ("PIN for the weekly 1:1:", "4417"), ("Meeting ID / dial-in", "987 654 321"),
              ("PIN for dial-in;", "Abc4417"), ("Meeting ID, (Teams)", "686339850"), ("Password, - Zoom,", "982-251-4652"),
              ("Meeting number required.", "4019154"), ("Access code for Teams\u2192", "345-453-7812"), ("PIN is was", "4417")]
EATERS = ["Pin board", "Token budget", "Pin the roadmap", "Secret Santa party", "Password reset \u2013 ABC", "Code review \u2013 ABC"]


class Rows(unittest.TestCase):
    def test_h2_a_qualified_id_with_its_number_on_the_line_goes(self):
        for t in H2_ROWS:
            self.assertEqual(I.invite_text("Agenda\n" + t + "\nAOB"), "Agenda\nAOB", t)
            self.assertEqual(I.scrub(t, 140), "", t)

    def test_h4_a_provider_and_a_number_goes(self):
        for t in H4_ROWS:
            self.assertEqual(I.invite_text("Agenda\n" + t + "\nAOB"), "Agenda\nAOB", t)
            self.assertEqual(I.scrub(t, 140), "", t)

    def test_ordinary_lines_with_a_provider_or_a_short_number_stay(self):
        for t in STAY:
            self.assertEqual(I.invite_text("Agenda\n" + t + "\nAOB"), "Agenda\n" + t + "\nAOB", t)

    def test_qualified_labels_with_any_separator_take_the_next_line(self):
        for head, v in SEPARATORS:
            for body in (f"{head}\n{v}\nAOB", f"<p>{head}</p><p>{v}</p><p>AOB</p>", f"<ul><li>{head}</li><li>{v}</li></ul>\nAOB"):
                out = I.invite_text(body)
                self.assertNotIn(v, out, body)
                self.assertTrue(out.endswith("AOB"), body)

    def test_label_word_agenda_lines_no_longer_take_the_lines_below(self):
        tail = ["Training dates", "Sign-off", "Reporting line", "AOB"]
        for h in EATERS:
            for lines in (["Agenda", h, *tail], ["Agenda", h, *[f"{i}. {x}" for i, x in enumerate(tail, 1)]]):
                out = I.invite_text("\n".join(lines))
                self.assertEqual([x for x in tail if x not in out], [], h)
            self.assertEqual(I.invite_text("Agenda\n" + h + "\nBudget review"), "Agenda\n" + h + "\nBudget review" if h.endswith("ABC") else "Agenda\nBudget review", h)

    def test_a_number_under_such_a_line_still_goes(self):
        for h in EATERS:
            for v in ("4417", "987 654 321", "ZQ7742"):
                self.assertNotIn(v, I.invite_text(f"Agenda\n{h}\n{v}\nAOB"), (h, v))

    def test_instruction_words_keep_the_hard_rule(self):
        for h in ("PIN below", "Token for the build", "OTP to follow", "Secret is", "PIN number", "PIN (Teams)", "Token - Zoom"):
            self.assertEqual(I.invite_text(f"Agenda\n{h}\nhunter\nAOB"), "Agenda\nAOB", h)

    def test_the_agenda_set_keeps_at_least_this_many_lines(self):
        kept, total, _ = agenda_kept()
        self.assertEqual(total, 200)
        self.assertGreaterEqual(kept, 135)

    def test_idempotent_on_every_row(self):
        for t in [*H2_ROWS, *H4_ROWS, *STAY, *EATERS]:
            for body in (t, "Agenda\n" + t + "\nBudget\n4417\nAOB"):
                once = I.invite_text(body)
                self.assertEqual(I.invite_text(once), once, body)


class Mutants(unittest.TestCase):
    def test_without_the_same_line_rule_h2_and_h4_leak(self):
        m = mutant("SAME_LINE_NUMBER = re.compile(", "SAME_LINE_NUMBER = re.compile(r'(?!)' + ")
        leaked = [t for t in [*H2_ROWS, *H4_ROWS] if m.invite_text("Agenda\n" + t + "\nAOB") != "Agenda\nAOB"]
        self.assertGreaterEqual(len(leaked), 8)          # the rest are also caught by older rules (a dial-in word, "ID is")

    def test_without_the_provider_half_h4_leaks(self):
        m = mutant("|(?<![\\w-])(?:{_PROVIDER_WORD})", "|(?!)(?:{_PROVIDER_WORD})")
        self.assertTrue([t for t in H4_ROWS if "9" in m.invite_text(t) or "123" in m.invite_text(t)])

    def test_a_year_rule_that_takes_any_digits_eats_the_stay_rows(self):
        m = mutant("(?:\\d{6,}|\\d{3,}[ -]\\d{3,}", "(?:\\d{3,}|\\d{3,}[ -]\\d{3,}")
        self.assertTrue([t for t in STAY if m.invite_text(t) != t])

    def test_without_the_comma_slash_and_semicolon_lead_the_separators_leak(self):
        m = mutant("(?:\\s*[,/;]){{1,2}}\\s*(?:{_QDASH}\\s+)?|", "")
        self.assertTrue([1 for head, v in SEPARATORS if v in m.invite_text(f"{head}\n{v}\nAOB")])

    def test_without_the_trailing_mark_the_sentence_end_leaks(self):
        m = mutant("(?:\\s*[.,;!?]+)?(?:{_ALONE_TAIL})?{_QUIET}$", "(?:{_ALONE_TAIL})?{_QUIET}$")
        self.assertIn("4019154", m.invite_text("Meeting number required.\n4019154\nAOB"))

    def test_without_the_one_to_one_rule_it_leaks(self):
        m = mutant('_ONE_TO_ONE = re.compile(r"(?<![\\w:])1:1(?!\\w|:\\d)")', '_ONE_TO_ONE = re.compile(r"(?!)")')
        self.assertIn("4417", m.invite_text("PIN for the weekly 1:1:\n4417\nAOB"))

    def test_without_the_soft_qualified_rule_the_agenda_is_eaten(self):
        m = mutant("    if _soft_qualified(line):\n        return False", "    if False:\n        return False")
        self.assertNotIn("Training dates", m.invite_text("Agenda\nPin board\nTraining dates\nSign-off\nAOB"))

    def test_without_the_soft_window_a_number_below_pin_board_leaks(self):
        m = mutant("        if self.soft_qualified:\n", "        if False:\n")
        self.assertIn("4417", m.invite_text("Agenda\nPin board\n4417\nAOB"))

    def test_without_the_instruction_words_pin_below_leaks(self):
        m = mutant('_INSTR = ("for|to|of|is|are|was|were|if|when|via|by|from|with|in|on|at|as|per|and|or|below|', '_INSTR = ("zzzz|below|')
        self.assertIn("hunter", m.invite_text("PIN to follow\nhunter\nAOB"))

    def test_without_the_project_code_suffix_the_heading_is_removed(self):
        m = mutant('r"(?:\\s*[-\\u2013\\u2014|]\\s*(?-i:[A-Z][A-Z0-9]{1,6}))?[\\s.,;!?*_~`]*$")', 'r"[\\s.,;!?*_~`]*$")')
        self.assertNotIn("Training dates", m.invite_text("Agenda\nPassword reset \u2013 ABC\nTraining dates\nSign-off\nAOB"))


class Fuzz(unittest.TestCase):
    pass


def make(name, gen):
    def t(self):
        broken = run(name, gen)
        for p, bs in broken.items():
            self.assertFalse(bs, f"{name}: {len(bs)} bodies break {p}; first:\n{(bs[0] if bs else '')!r}")
    return t


for _n, _g in GENERATORS:
    setattr(Fuzz, "test_" + _n, make(_n, _g))

if __name__ == "__main__":
    unittest.main(verbosity=2)
