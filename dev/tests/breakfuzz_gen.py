"""Seeded generator of HTML invite bodies with breaks inside and between labels and values (E1 D, fix5). All values made up."""
import random

LABELS = ["Conference ID:", "Passcode:", "Meeting ID", "PIN:", "Host key (organiser only):", "Mot de passe:", "Zoom passcode:",
          "Secret for the vendor portal", "Access code"]
FILL = ["Vendors", "Agenda", "Decisions log", "Budget review", "Teams", "Welcome", "Risks and issues"]
VALUES = ["824", "770", "8825", "412889", "gusos58#", "a6ad063a9", "mupiwoc", "984 522", "swordfish"]
ODD = ["\x0b", "\x0c", "\x85", " ", " "]
WRAP = [("<p>", "</p>"), ("<li>", "</li>"), ("<td>", "</td>"), ("<div>", "</div>")]


def _piece(r):
    k = r.random()
    if k < .4:
        return r.choice(LABELS)
    if k < .7:
        return r.choice(FILL)
    return r.choice(VALUES)


def _glue(r):
    return r.choice(["<br>", "<br/>", "<br />", " ", "", r.choice(ODD), " " + r.choice(ODD) + " "])


def body(seed):
    r = random.Random(seed)
    parts = []
    for _ in range(r.randint(1, 4)):
        o, c = r.choice(WRAP)
        text = _piece(r)
        for _ in range(r.randint(0, 3)):
            text += _glue(r) + _piece(r)
        if r.random() < .25:
            text = r.choice(LABELS) + _glue(r) + r.choice(FILL) + _glue(r) + r.choice(VALUES)
        parts.append(o + text + c)
    html = "".join(parts)
    if r.random() < .3:
        html = "<ul>" + html + "</ul>"
    return html


def bodies(n, seed=375):
    return [body(seed * 100003 + i) for i in range(n)]
