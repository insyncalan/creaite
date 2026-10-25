"""2.6.8 (#369) seeded fuzz for the invite scrub: HTML tables, nested lists, blockquotes, markdown tables, mixed Teams/Zoom/Webex
invites, qualified labels, soft headings with dates and times, accents and confusables.

Run: python3 dev/tests/test_invite_clean_fuzz_html.py            (5,000 bodies per generator, 8 generators)
     FUZZ_FULL=1 python3 dev/tests/test_invite_clean_fuzz_html.py   (200,000 bodies in total, 25,000 per generator)
     FUZZ_SEED=n sets the seed (default 369).

Two properties for every body:
  (a) idempotence: invite_text(invite_text(x)) == invite_text(x);
  (b) no planted secret survives: digits of 4 or more, grouped digits, hex, mixed letter-and-digit tokens and word-only values under a
      HARD label are absent from the output. A word-only value under a SOFT heading is the accepted limit (option B): planted, never checked.
Known leaks of the commit this was written against (bfb65603) (and the other open classes found by the fuzz) are recognised by classify(): the body is still run, but
a leak of such a class does not fail the file. Remove a class from classify() when it is fixed. Everything else must pass. All values are made up.
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

SEED = int(os.environ.get("FUZZ_SEED", "369"))
FULL = os.environ.get("FUZZ_FULL") == "1"
PER = 25000 if FULL else 5000

HARD = ["Passcode", "PIN", "Password", "Access code", "Meeting ID", "Host key", "Phone Conference ID", "Conference ID",
        "Access Code", "Meeting Passcode", "Teams PIN", "Zoom Passcode", "Webex Access Code", "Host Key"]
QUAL = ["Passcode required", "PIN below", "Passcode (required)", "Access code - Teams", "Passcode is", "Password for the room",
        "PIN to follow"]
SOFT = ["Password reset", "Code review", "Dress code", "Code of conduct", "Token refresh", "Secret Santa"]
FILL = ["Agenda", "Welcome and apologies", "Budget review", "Hiring update", "Vendors", "Risks and issues", "Milestones", "AOB",
        "Join the meeting now", "Questions for the team", "Notes from last time", "Next steps"]
WORDS = ["swordfish", "hunter", "falcon", "marmalade", "kestrel", "pumpkin", "oatmeal", "bluebird", "tangerine", "walrus"]
DATES = ["14-10-2026", "2026-10-14", "Wednesday 14 October", "14 Oct 2026", "Oct 14", "Tuesday 3rd November"]
TIMES = ["10:00", "09:30-10:30", "14:00 BST", "3pm", "10:00 - 11:00", "Wed 12:15"]
DIAL = ["+44 20 7946 0958", "+1 202 555 0143", "+353 1 555 0199", "+61 2 5550 0111"]
SECRET_KINDS = ["digits", "grouped", "hex", "mixed", "word"]
CYR = {"a": "а", "e": "е", "o": "о", "p": "р", "c": "с", "s": "ѕ", "i": "і"}
ACC = {"a": "á", "e": "é", "o": "ö", "i": "í", "s": "š", "n": "ñ"}


def secret(r, kinds=SECRET_KINDS):
    k = r.choice(kinds)
    if k == "digits":
        return r.choice("123456789") + "".join(r.choice("0123456789") for _ in range(r.randint(3, 8))), k
    if k == "grouped":
        return " ".join(r.choice("123456789") + "".join(r.choice("0123456789") for _ in range(2)) for _ in range(r.randint(2, 4))), k
    if k == "hex":
        return "".join(r.choice("0123456789abcdef") for _ in range(r.randint(8, 16))) + "f", k
    if k == "mixed":
        return r.choice(["hunter", "ZQ", "kx", "Tb"]) + str(r.randint(10, 9999)) + r.choice(["", "x", "Q"]), k
    return r.choice(WORDS) + r.choice(["", "", "", "r", "s"]), k


def filler(r, n=None):
    return [r.choice(FILL) for _ in range(r.randint(0, 3) if n is None else n)]


def disguise(r, label):
    """Accents and confusables on some letters of the label."""
    m = r.randint(0, 3)
    if m == 0:
        return label
    table = CYR if m <= 2 else ACC
    return "".join(table[c.lower()] if c.lower() in table and r.random() < 0.5 else c for c in label)


class Body:
    def __init__(self):
        self.items = []         # (value, label, tag): values that must be gone, with the label (undisguised) and the layout tag
        self.soft = []          # planted, accepted limit

    @property
    def secrets(self):
        return [i[0] for i in self.items]

    def hard(self, r, kinds=SECRET_KINDS, label="", tag=""):
        v, _ = secret(r, kinds)
        self.items.append((v, label, tag))
        return v

    def soft_value(self, r):
        v, k = secret(r)
        if k == "word":
            self.soft.append(v)
        else:
            self.items.append((v, "<soft>", ""))
        return v


def wrap(r, html):
    return "<html><body>" + html + "</body></html>" if r.random() < 0.3 else html


def g_html_table(r):
    b = Body()
    rows = []
    for _ in range(r.randint(1, 4)):
        base = r.choice(HARD + QUAL[:2] if r.random() < 0.8 else FILL)
        lab = disguise(r, base) if r.random() < 0.2 else base
        cell = r.choice(["td", "th"])
        if base in FILL:
            rows.append(f"<tr><{cell}>{lab}</{cell}><td>{r.choice(DATES + TIMES)}</td></tr>")
            continue
        shape = r.randint(0, 3)
        v = b.hard(r, label=base, tag="thead" if shape == 2 else "")
        sep = r.choice(["", ":", ""])
        if shape == 0:
            rows.append(f"<tr><{cell}>{lab}{sep}</{cell}><td>{v}</td></tr>")
        elif shape == 1:
            rows.append(f"<tr><{cell}>{lab}{sep}</{cell}></tr><tr><td>{v}</td></tr>")
        elif shape == 2:
            rows.append(f"<tr><th>{lab}</th><th>Other</th></tr><tr><td>{v}</td><td>{r.choice(FILL)}</td></tr>")
        else:
            rows.append(f"<tr><td><b>{lab}</b>{sep}</td><td><span>{v}</span></td></tr>")
    body = "<p>" + r.choice(FILL) + "</p><table>" + "".join(rows) + "</table><p>" + r.choice(FILL) + "</p>"
    return wrap(r, body), b


def g_nested_lists(r):
    b = Body()

    def lst(depth):
        tag = r.choice(["ul", "ol"])
        items = []
        for _ in range(r.randint(1, 3)):
            if r.random() < 0.5:
                lab = r.choice(HARD)
                v = b.hard(r, label=lab)
                if r.random() < 0.15:
                    lab = disguise(r, lab)
                form = r.randint(0, 3)
                if form == 0:
                    items.append(f"<li>{lab}: {v}</li>")
                elif form == 1:
                    items.append(f"<li>{lab}:<ul><li>{v}</li></ul></li>")
                elif form == 2:
                    items.append(f"<li>{lab}</li><li>{v}</li>")
                else:
                    items.append(f"<li>{lab}<ol><li>{v}</li></ol></li>")
            elif depth < 3 and r.random() < 0.5:
                items.append(f"<li>{r.choice(FILL)}{lst(depth + 1)}</li>")
            else:
                items.append(f"<li>{r.choice(FILL)}</li>")
        return f"<{tag}>" + "".join(items) + f"</{tag}>"
    return wrap(r, "<p>" + r.choice(FILL) + "</p>" + lst(1)), b


def g_blockquote(r):
    b = Body()
    parts = []
    for _ in range(r.randint(1, 3)):
        lab = r.choice(HARD + QUAL)
        v = b.hard(r, label=lab)
        sep = r.choice([":", " ", "\n", ": ", " - "])
        inner = f"{lab}{sep}{v}" if r.random() < 0.7 else f"{lab}<br>{v}"
        mode = r.randint(0, 2)
        if mode == 0:
            parts.append(f"<blockquote>{inner}</blockquote>")
        elif mode == 1:
            parts.append(f"<blockquote><blockquote><p>{lab}</p><p>{v}</p></blockquote></blockquote>")
        else:
            parts.append("\n".join("> " + x for x in inner.replace("<br>", "\n").split("\n")))
        parts.append(r.choice(FILL))
    return wrap(r, "\n".join(parts)), b


def g_md_table(r):
    b = Body()
    lines = []
    for _ in range(r.randint(1, 3)):
        w = r.choice([2, 3])
        lines.append("| " + " | ".join(["Item", "Detail", "Notes"][:w]) + " |")
        lines.append("|" + "|".join(["---"] * w) + "|")
        for _ in range(r.randint(1, 3)):
            lab = r.choice(HARD + QUAL[:3] + FILL)
            if lab in FILL:
                lines.append("| " + " | ".join([lab, r.choice(DATES + TIMES), ""][:w]) + " |")
                continue
            v = b.hard(r, label=lab)
            form = r.randint(0, 2)
            if form == 0:
                cells = [lab, v, "x"][:w]
            elif form == 1:
                cells = [lab + ":", v, ""][:w]
            else:
                lines.append("| " + " | ".join([lab] + [""] * (w - 1)) + " |")
                cells = [v] + [""] * (w - 1)
            lines.append("| " + " | ".join(cells) + " |")
        lines += [r.choice(FILL), ""]
    return "\n".join(lines), b


def g_mixed_invite(r):
    b = Body()
    prov = r.choice(["teams", "zoom", "webex"])
    L = filler(r, 2)
    hexs = "".join(r.choice("abcdef0123456789") for _ in range(12))
    if prov == "teams":
        L += ["Microsoft Teams meeting", "Join: https://teams.microsoft.com/l/meetup-join/19%3ameeting_" + hexs,
              "Meeting ID: " + b.hard(r, ["grouped", "digits"]), "Passcode: " + b.hard(r, ["word", "mixed", "digits"]),
              "Dial in: " + r.choice(DIAL) + ",," + b.hard(r, ["digits"]) + "#",
              "Phone Conference ID: " + b.hard(r, ["grouped", "digits"]) + "#"]
        if r.random() < 0.5:
            L.append("Need help? https://aka.ms/JoinTeamsMeeting")
    elif prov == "zoom":
        L += ["Join Zoom Meeting", "https://example.zoom.us/j/" + hexs + "?pwd=" + hexs[::-1], "",
              "Meeting ID: " + b.hard(r, ["grouped"]), "Passcode: " + b.hard(r, ["word", "digits", "mixed"]), "One tap mobile",
              r.choice(DIAL) + ",,,*" + b.hard(r, ["digits"]) + "#"]
    else:
        L += ["Join Webex meeting", "https://example.webex.com/meet/room", "Meeting number (access code): " + b.hard(r, ["grouped"]),
              "Meeting password: " + b.hard(r, ["word", "mixed"]), "Host key: " + b.hard(r, ["digits"]), "Join by phone",
              r.choice(DIAL) + " Access code: " + b.hard(r, ["digits"])]
    style = r.randint(0, 3)
    out = []
    for ln in L:
        plain = "http" not in ln and ": " in ln
        if style == 1 and plain:
            ln = ln.replace(": ", ":\n", 1)
        elif style == 2:
            ln = "<p>" + ln + "</p>" if "http" not in ln else '<a href="' + ln.split()[-1] + '">join</a>'
        elif style == 3 and plain:
            lab, val = ln.split(": ", 1)
            ln = f"<tr><td>{lab}</td><td>{val}</td></tr>"
        out.append(ln)
    body = "\n".join(out + filler(r, 1))
    if style == 3:
        body = "<table>" + body.replace("\n", "") + "</table>"
    return body, b


def g_qualified(r):
    b = Body()
    L = filler(r, 1)
    for _ in range(r.randint(1, 3)):
        q = r.choice(QUAL)
        form = r.randint(0, 4)
        prov = r.choice(["Teams", "Zoom"])
        v = b.hard(r, label=q + (" - " + prov if form == 3 else ""), tag="enter" if form == 4 else "")
        sep = r.choice([":", ""])
        if form == 0:
            L += [q + sep, v]
        elif form == 1:
            L += [q + sep + " " + v]
        elif form == 2:
            L += [q + sep, "", v]
        elif form == 3:
            L += [q + " - " + prov, v]
        else:
            L += [q + sep, "Please enter", v]
        L += filler(r, r.randint(0, 2))
    return "\n".join(L), b


def g_soft_dates(r):
    b = Body()
    L = filler(r, 1)
    for _ in range(r.randint(1, 3)):
        L.append(r.choice(SOFT))
        for _ in range(r.randint(0, 2)):
            L.append(r.choice(DATES + TIMES))
        L.append(b.soft_value(r) if r.random() < 0.7 else r.choice(FILL))
        L += filler(r, r.randint(0, 2))
    body = "\n".join(L)
    if r.random() < 0.3:
        body = "<ul>" + "".join(f"<li>{x}</li>" for x in L) + "</ul>"
    return body, b


def g_accents(r):
    b = Body()
    L = filler(r, 1)
    for _ in range(r.randint(1, 3)):
        base = r.choice(HARD + QUAL)
        v = b.hard(r, label=base)
        lab = disguise(r, base)
        if r.random() < 0.3:
            lab = "​".join(lab) if r.random() < 0.3 else lab.replace(" ", " ")
        form = r.randint(0, 3)
        if form == 0:
            L.append(f"{lab}: {v}")
        elif form == 1:
            L += [lab, v]
        elif form == 2:
            L.append(f"<p>{lab}</p><p>{v}</p>")
        else:
            L.append(f"{lab.upper()}: {v}")
        L += filler(r, r.randint(0, 1))
    return "\n".join(L), b


GENERATORS = [("html_table", g_html_table), ("nested_lists", g_nested_lists), ("blockquote", g_blockquote), ("md_table", g_md_table),
              ("mixed_invite", g_mixed_invite), ("qualified", g_qualified), ("soft_dates", g_soft_dates), ("accents", g_accents)]


A_LABELS = (QUAL[0], QUAL[1], QUAL[3])


def classify(item):
    """The open class of a leaked planted value, or "" (a new failure). Remove a class when the scrub is fixed (bfb65603 leaks all four)."""
    v, label, tag = item
    if label == "<soft>":
        return "E soft heading + 1-2 letter token with 1-2 digits (Tb28, ZQ27)" if re.fullmatch(r"[A-Za-z]{1,6}\d{1,2}[A-Za-z]?", v) else ""
    if label.endswith("ID") and v.isalpha():
        return "F word-only value after an ID label (Meeting ID bluebird): the documented limit in NOTES-2.6.8"
    if tag == "thead" and not re.search(r"\d{3,}", v):
        return "D word-only or short mixed value in a multi-word row below a header-row label (limit; E1 closes it in 2.6.9)"
    return ""


def check(body, bd):
    """[(property, item or None)] for every property this body breaks."""
    once = I.invite_text(body)
    bad = []
    if I.invite_text(once) != once:
        bad.append(("idempotence", None))
    low = once.lower()
    for it in bd.items:
        if it[0].lower() in low:
            bad.append(("leak", it))
    return bad


def cases(name, gen, n, seed=SEED):
    r = random.Random(f"{seed}-{name}")
    for _ in range(n):
        body, bd = gen(r)
        # a planted value that also occurs as ordinary text elsewhere in the body (a date, say) cannot be checked
        bd.items = [i for i in bd.items if i[0].lower() not in body.lower().replace(i[0].lower(), "", 1)]
        yield body, bd


class Fuzz(unittest.TestCase):
    pass


def make(name, gen):
    def t(self):
        broken = {"idempotence": [], "leak": []}
        for body, bd in cases(name, gen, PER):
            for p, it in check(body, bd):
                if p == "leak" and classify(it):
                    continue                    # open and listed in FUZZ-FINDINGS.md
                broken[p].append(body)
        for p, bs in broken.items():
            self.assertFalse(bs, f"{name}: {len(bs)} bodies break {p}; first:\n{(bs[0] if bs else '')!r}")
    return t


for _n, _g in GENERATORS:
    setattr(Fuzz, "test_" + _n, make(_n, _g))

if __name__ == "__main__":
    unittest.main(verbosity=2)
