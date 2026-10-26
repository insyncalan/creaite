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


GENERATORS = [("same_line", g_same_line), ("next_line", g_next_line)]


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
    if same:
        lost = [o for o in ordinary if o not in once.split("\n")]
        if lost:
            bad.append(("eaten", lost[0]))
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
