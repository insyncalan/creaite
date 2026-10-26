"""#375 E1 adversarial pass 2 (final, 2.6.9 stack): fresh seeded generators; orphans, single anchors, encodings, markup labels, wrapped URLs,
repeated and long bodies, dial lists, provider-unknown invites; the gateway round trip; the quadratic looks_like_html.

Run: python3 dev/tests/test_e1_adversarial2.py            1,000 bodies per generator (about a minute)
     ADV_FULL=1 python3 dev/tests/test_e1_adversarial2.py 10,000 per generator
     python3 dev/tests/test_e1_adversarial2.py --report   per-generator tables used in dev/proposals/375/ADVERSARIAL-2.md

None of the generators of test_e1_adversarial.py (13) or test_invite_clean_fuzz_html.py (8) is reused. Fictional data only.
Per generator, on the default composition D ("C": invite_filter.filter_text_with_scrub) and the 2.6.8 scrub alone ("old": invite_clean.invite_text):
  idempotence C(C(x)) == C(x); planted secrets that survive (full = whole value in one line, split = only across lines);
  planted ordinary lines lost ("keepers"); time. The generator tests assert what holds today (no exception, idempotence ratchet,
  leak and loss ratchets: counts for the default seed may only go down). Each finding is also a minimal test marked expectedFailure
  with the reason: when a fix lands it turns into an "unexpected success", the signal to remove the marker and lower the ratchet.
"""
import json
import math
import os
import random
import re
import sys
import tempfile
import time
import unicodedata
import unittest
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parents[1] / "system" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import calendar_gateway as G  # noqa: E402
import invite_blocks as B  # noqa: E402
import invite_clean as IC  # noqa: E402
import invite_filter as F  # noqa: E402

N = 10000 if os.environ.get("ADV_FULL") else 1000


def C(text):
    return F.filter_text_with_scrub(text)


def OLD(text):
    return IC.invite_text(text)


# ================================================================================ measuring

def compact(s):
    s = unicodedata.normalize("NFKC", s)
    out = []
    for ch in s:
        if ch.isdecimal():
            out.append(str(unicodedata.decimal(ch)))
        elif ch.isalnum() and ch.isascii():
            out.append(ch.lower())
    return "".join(out)


class Body:
    """text, secrets [compact strings], keepers [text], tag."""

    def __init__(self, text, secrets=(), keepers=(), tag="", dims=None, kinds=None):
        self.text, self.secrets, self.keepers, self.tag = text, [compact(s) for s in secrets], list(keepers), tag
        self.dims = dims or {}              # name -> value, for breakdown()
        self.kinds = kinds or {}            # keeper text -> kind (for the lost-by-kind breakdown)
        self.leaked = []                    # filled by measure: the indices of the secrets that survived
        self.lost_keepers = []              # filled by measure


class Stat:
    def __init__(self):
        self.n = 0
        self.errors = Counter()
        self.nonidem = 0
        self.nonidem_example = None
        self.secrets = 0
        self.leaks = Counter()          # (tag, kind) -> count
        self.leak_example = {}
        self.keepers = 0
        self.lost = Counter()           # tag -> lost keepers
        self.lost_example = {}
        self.whole_lost = Counter()     # tag -> bodies where every keeper was lost (the whole agenda went)
        self.bodies_by_tag = Counter()
        self.seconds = 0.0
        self.worst = 0.0

    @property
    def leak_total(self):
        return sum(self.leaks.values())

    @property
    def lost_total(self):
        return sum(self.lost.values())


def _idem(fn, out, b, st):
    try:
        if fn(out) != out:
            st.nonidem += 1
            st.nonidem_example = st.nonidem_example if st.nonidem_example is not None and len(st.nonidem_example) <= len(b.text) else b.text
    except Exception as e:  # noqa: BLE001
        st.errors["idem:" + type(e).__name__] += 1


def _score_secrets(st, b, lines, allc, record):
    for si, s in enumerate(b.secrets):
        st.secrets += 1
        kind = "full" if any(s in x for x in lines) else ("split" if s in allc else None)
        if not kind:
            continue
        if record:
            b.leaked.append(si)
        st.leaks[(b.tag, kind)] += 1
        k = (b.tag, kind)
        if k not in st.leak_example or len(b.text) < len(st.leak_example[k]):
            st.leak_example[k] = b.text


def _score_keepers(st, b, allc, record):
    lost = 0
    for k in b.keepers:
        st.keepers += 1
        if compact(k) in allc:
            continue
        lost += 1
        if record:
            b.lost_keepers.append(k)
        st.lost[b.tag] += 1
        if b.tag not in st.lost_example or len(b.text) < len(st.lost_example[b.tag][0]):
            st.lost_example[b.tag] = (b.text, k)
    if b.keepers and lost == len(b.keepers):
        st.whole_lost[b.tag] += 1


def _run_one(fn, b, st, check_idem):
    t = time.perf_counter()
    try:
        out = fn(b.text)
    except Exception as e:  # noqa: BLE001
        st.errors[type(e).__name__] += 1
        return None
    d = time.perf_counter() - t
    st.seconds += d
    st.worst = max(st.worst, d)
    if check_idem:
        _idem(fn, out, b, st)
    return out


def measure(fn, bodies, check_idem=True, record=True):
    st = Stat()
    for b in bodies:
        if record:
            b.leaked, b.lost_keepers = [], []
        st.n += 1
        st.bodies_by_tag[b.tag] += 1
        out = _run_one(fn, b, st, check_idem)
        if out is None:
            continue
        lines = [compact(x) for x in out.split("\n")]
        allc = "".join(lines)
        _score_secrets(st, b, lines, allc, record)
        _score_keepers(st, b, allc, record)
    return st


def breakdown(bodies, dim):
    """{value: (bodies, secrets, secrets leaked, keepers, keepers lost)} by one dimension (needs measure() to have run on the bodies)."""
    out = defaultdict(lambda: [0, 0, 0, 0, 0])
    for b in bodies:
        v = b.dims.get(dim)
        if v is None:
            continue
        r = out[v]
        r[0] += 1
        r[1] += len(b.secrets)
        r[2] += len(b.leaked)
        r[3] += len(b.keepers)
        r[4] += len(b.lost_keepers)
    return dict(out)


def lost_by_kind(bodies):
    out = defaultdict(lambda: [0, 0])
    for b in bodies:
        for k in b.keepers:
            kind = b.kinds.get(k)
            if kind:
                out[kind][0] += 1
                out[kind][1] += k in b.lost_keepers
    return dict(out)


def run_gen(gen, n, seed):
    rng = random.Random(seed)
    return [gen(rng) for _ in range(n)]


# ================================================================================ rendering

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _j(blocks, sep):
    return sep.join("\n".join(b) for b in blocks)


def _html(blocks, wrap):
    return "<html><body>" + "".join(wrap % esc(x) for b in blocks for x in b) + "</body></html>"


_LAYOUTS = {
    "plain": lambda bl: _j(bl, "\n\n"),
    "plain2": lambda bl: _j(bl, "\n\n\n"),
    "tight": lambda bl: _j(bl, "\n"),
    "html_p": lambda bl: _html(bl, "<p>%s</p>"),
    "html_br": lambda bl: "<html><body>" + "".join("<p>%s</p>" % "<br>".join(esc(x) for x in b) for b in bl) + "</body></html>",
    "html_li": lambda bl: "<html><body><ul>" + "".join("<li>%s</li>" % esc(x) for b in bl for x in b) + "</ul></body></html>",
    "html_div": lambda bl: _html(bl, "<div>%s</div>"),
    "html_table": lambda bl: "<table>" + "".join("<tr><td>%s</td></tr>" % esc(x) for b in bl for x in b) + "</table>",
}


def render(blocks, layout):
    """blocks: list of lists of lines. layouts: plain, plain2 (two blank lines), html_p (one <p> per line), html_br (one <p> per block, <br>
    inside), html_li, html_div, html_table (one <tr><td> per line)."""
    if layout not in _LAYOUTS:
        raise ValueError(layout)
    return _LAYOUTS[layout](blocks)


LAYOUTS = ("plain", "plain2", "tight", "html_p", "html_br", "html_li", "html_div", "html_table")

AGENDA = ["Q3 budget review", "Hiring plan for the platform team", "Vendor shortlist and next steps", "Risks and mitigations",
          "Roadmap: onboarding flow", "Customer pilot feedback", "Decision on the data migration", "Any other business"]


def agenda(rng, k):
    items = rng.sample(AGENDA, k)
    return ["%d. %s" % (i + 1, x) for i, x in enumerate(items)]


def digits(rng, n):
    return "".join(rng.choice("0123456789") for _ in range(n))


def alnum(rng, n):
    while True:
        s = "".join(rng.choice("abcdefghjkmnpqrstuvwxyz23456789") for _ in range(n))
        if any(c.isdigit() for c in s) and any(c.isalpha() for c in s):
            return s


# ================================================================================ generators

LISTED_ID = ["Meeting ID", "Meeting ID:", "Conference ID", "Webinar ID"]
HEAD_BLOCKS = {
    "id7": lambda r: ["Meeting ID: %s %s %s" % (digits(r, 3), digits(r, 3), digits(r, 3))],
    "id_label_value": lambda r: ["Meeting ID:", "%s %s %s" % (digits(r, 3), digits(r, 3), digits(r, 4))],
    "dial": lambda r: ["Dial-in: +44 20 7946 0%s" % digits(r, 3)],
    "url": lambda r: ["Join: https://meet.example.test/j/%s" % digits(r, 9)],
}
ORPHAN_SHAPES = {
    "pin4": lambda r: digits(r, 4),
    "pin6": lambda r: digits(r, 6),
    "pin8": lambda r: digits(r, 8),
    "alnum6": lambda r: alnum(r, 6),
    "alnum8": lambda r: alnum(r, 8),
    "pin_spaced": lambda r: "%s %s" % (digits(r, 3), digits(r, 3)),
    "pin_hash": lambda r: digits(r, 6) + "#",
    "pin_label": lambda r: "PIN " + digits(r, 5),      # a listed word: control, should always go
    "word_pin": lambda r: "Ref " + digits(r, 5),
}
ORPH_KEEPERS = {
    "agenda": lambda r: "Agenda item: " + r.choice(AGENDA),
    "room": lambda r: "Room %d" % r.choice((204, 1204, 3071)),
    "year": lambda r: "Budget %d" % r.choice((2026, 2027)),
    "ticket": lambda r: "Ticket INC%d follow-up" % r.choice((1234, 98765)),
    "floor": lambda r: "Floor %d" % r.choice((12, 3)),
    "short_code": lambda r: "Plan Q3x" + str(r.choice((7, 9))),
    "date": lambda r: "26 Oct 2026",
    "time": lambda r: "14:00-15:30",
    "ext": lambda r: "Ext 4417 for help",
}
SEPS = ("blank", "blank2", "divider", "divider_blank", "tight", "list", "html_p", "html_table_after")


def _orphan_text(sep, pre, post, hb, vals):
    if sep in ("blank", "blank2", "divider", "divider_blank", "tight"):
        return _orphan_plain(sep, pre, post, hb, vals)
    if sep == "list":
        return pre + "\n\n" + "\n".join(hb) + "\n" + "\n".join("- " + v for v in vals) + "\n\n" + "\n\n".join(post)
    if sep == "html_p":
        return render([[pre], hb] + [[v] for v in vals] + [[p] for p in post], "html_p")
    # html_table_after: the label block is a table, the orphans follow as paragraphs
    cells = "".join("<tr><td>%s</td></tr>" % esc(x) for x in hb)
    return ("<p>%s</p><table>%s</table>" % (esc(pre), cells) + "".join("<p>%s</p>" % esc(v) for v in vals) +
            "".join("<p>%s</p>" % esc(p) for p in post))


def _orphan_plain(sep, pre, post, hb, vals):
    if sep == "divider":
        return pre + "\n\n" + "\n".join(hb) + "\n________\n" + "\n\n".join(vals) + "\n\n" + "\n\n".join(post)
    if sep == "divider_blank":
        return pre + "\n\n" + "\n".join(hb) + "\n\n________\n\n" + "\n\n".join(vals) + "\n\n" + "\n\n".join(post)
    blocks = [[pre], hb] + [[v] for v in vals] + [[p] for p in post]
    return render(blocks, {"blank": "plain", "blank2": "plain2", "tight": "tight"}[sep])


def gen_orphans(rng):
    """Class A: after a block dropped for its anchor, 1 to 3 value-only blocks (a secret each) and then ordinary lines."""
    head = rng.choice(sorted(HEAD_BLOCKS))
    sep = rng.choice(SEPS)
    n_or = rng.choice((1, 1, 2, 2, 3))
    shapes = [rng.choice(sorted(ORPHAN_SHAPES)) for _ in range(n_or)]
    vals = [ORPHAN_SHAPES[s](rng) for s in shapes]
    secrets = [v for v, s in zip(vals, shapes) if s != "word_pin"]
    kp = [rng.choice(sorted(ORPH_KEEPERS)) for _ in range(rng.choice((1, 2)))]
    keepers = ["Subject: weekly sync"] + [ORPH_KEEPERS[k](rng) for k in kp]
    hb = HEAD_BLOCKS[head](rng)
    tag = "%s/n%d/%s" % (sep, n_or, "+".join(kp))
    ags = ["Agenda for the weekly sync"]
    # keepers[0] before, the rest after the orphans
    pre, post = keepers[0], keepers[1:]
    text = _orphan_text(sep, pre, post, hb, vals)
    del ags
    kinds = dict(zip(keepers[1:], kp))
    return Body(text, secrets, keepers, tag, dims={"sep": sep, "n": n_or, "shape0": shapes[0], "head": head,
                                                    "sep+shape0": "%s/%s" % (sep, shapes[0])}, kinds=kinds)


ANCHORS = {
    "url_plain": ("Spec: https://wiki.example.test/team/spec", False),
    "url_inline": ("Read https://wiki.example.test/team/spec before the call", False),
    "url_query": ("Read https://wiki.example.test/page?id=77 first", False),
    "host_only": ("Notes at wiki.example.test/team/notes", False),
    "www_only": ("Our site: www.example.test", False),
    "phone_e164": ("Ring Pat on +44 20 7946 0958 re budget", False),
    "phone_local": ("Call 020 7946 0958 for access", False),
    "phone_short": ("Ext 4417 for help", False),
    "mailto": ("Questions to mia.hale@example.test", False),
    "ics_url": ("URL:https://teams.example.test/l/meetup-join/19%3ameeting_abc/0", False),
    "ics_loc": ("LOCATION:Room 204, Level 2", False),
    "ics_teams": ("X-MICROSOFT-SKYPETEAMSMEETINGURL:https://teams.example.test/l/meetup-join/19%3ameeting_abc/0?context=x", False),
    "sip": ("Join by video system: 123456789@meet.example.test", True),
    "sig_dial": ("Direct dial: +44 20 7946 0958", False),
}


def gen_single_anchor(rng):
    """An agenda with exactly ONE anchor line (a link, a phone number, an ICS-style line): does the whole agenda go, or only the line?"""
    kind = rng.choice(sorted(ANCHORS))
    line, secret = ANCHORS[kind]
    layout = rng.choice(LAYOUTS)
    ag = agenda(rng, rng.choice((2, 3, 5)))
    pos = rng.randrange(len(ag) + 1)
    items = ag[:pos] + [line] + ag[pos:]
    if rng.random() < 0.5:
        blocks = [["Agenda"], items]
    else:
        blocks = [["Agenda"]] + [[x] for x in items] if layout in ("html_p", "html_li", "html_div", "html_table") else [["Agenda"], items]
    secrets = [re.sub(r"\D", "", line)] if secret else []
    return Body(render(blocks, layout), secrets, ["Agenda"] + ag, "%s/%s" % (kind, layout), dims={"kind": kind, "layout": layout})


PROVIDERS = {
    "teams": ("Join Microsoft Teams Meeting", "https://teams.example.test/l/meetup-join/19%3ameeting_{a}%40thread.v2/0?context=%7b%22Tid%22%3a%22{a}%22%7d"),
    "zoom": ("Join Zoom Meeting", "https://zoom.example.test/j/{d9}?pwd={a}"),
    "webex": ("Join Webex meeting", "https://acme.webex.example.test/acme/j.php?MTID=m{a}"),
    "meet": ("Join with Google Meet", "https://meet.example.test/{m}"),
    "gotomeeting": ("Join the meeting now", "https://global.gotomeeting.example.test/join/{d9}"),
    "unknown": ("Join the call", "https://conf.example.test/room/{a}?token={a}"),
}


def gen_provider_one_line(rng):
    """Provider bodies with one ICS-style or join line only, a note or an agenda around it."""
    name = rng.choice(sorted(PROVIDERS))
    head, url = PROVIDERS[name]
    a = alnum(rng, 10)
    d9 = digits(rng, 9)
    m = "%s-%s-%s" % (alnum(rng, 3), alnum(rng, 4), alnum(rng, 3))
    u = url.format(a=a, d9=d9, m=m)
    form = rng.choice(("bare", "label", "ics", "angle", "md"))
    line = {"bare": u, "label": "%s: %s" % (head, u), "ics": "X-JOIN-URL:" + u, "angle": "%s <%s>" % (head, u),
            "md": "[%s](%s)" % (head, u)}[form]
    layout = rng.choice(("plain", "tight", "html_p", "html_br"))
    ag = agenda(rng, 3)
    where = rng.choice(("before", "after", "middle"))
    blocks = {"before": [[line], ["Agenda"] + ag], "after": [["Agenda"] + ag, [line]],
              "middle": [["Agenda", ag[0]], [line], ag[1:]]}[where]
    secrets = [x for x in (d9, a, m) if x in u]
    return Body(render(blocks, layout), secrets, ["Agenda"] + ag, "%s/%s/%s" % (name, form, layout))


def _wrap_crlf(t):
    return t.replace("\n", "\r\n")


ENCODINGS = {
    "crlf": _wrap_crlf,
    "cr": lambda t: t.replace("\n", "\r"),
    "nel": lambda t: t.replace("\n", "\x85"),
    "u2028": lambda t: t.replace("\n", "\u2028"),
    "u2029": lambda t: t.replace("\n", "\u2029"),
    "vt_ff": lambda t: t.replace("\n", "\x0b", 1).replace("\n", "\x0c"),
    "bom": lambda t: "\ufeff" + t,
    "utf16_as_latin1": lambda t: t.encode("utf-16-le").decode("latin-1"),
    "utf16_bom_as_latin1": lambda t: t.encode("utf-16").decode("latin-1"),
    "utf16_as_utf8_replace": lambda t: t.encode("utf-16-le").decode("utf-8", "replace"),
    "mojibake": lambda t: t.encode("utf-8").decode("latin-1"),
    "qp": lambda t: t.replace("=", "=3D").replace("\n", "=0A=\n"),
    "qp_softbreak": lambda t: re.sub(r"(Pass)(code)", r"\1=\n\2", t),
    "numeric_entities": lambda t: "".join("&#%d;" % ord(c) if c.isalpha() and ord(c) % 3 == 0 else c for c in t),
    "nbsp_all": lambda t: t.replace(" ", "\u00a0"),
    "tabs": lambda t: t.replace(": ", ":\t"),
}


def gen_encodings(rng):
    pin = digits(rng, rng.choice((4, 6)))
    ag = agenda(rng, 3)
    lines = ["Agenda"] + ag + ["", "Passcode: " + pin, "", "Thanks"]
    kind = rng.choice(sorted(ENCODINGS))
    html = rng.random() < 0.25 and kind in ("bom", "crlf", "nbsp_all", "numeric_entities", "tabs", "mojibake", "qp")
    base = render([["Agenda"] + ag, ["Passcode: " + pin], ["Thanks"]], "html_br" if html else "plain")
    text = ENCODINGS[kind](base)
    del lines
    return Body(text, [pin], ["Agenda"] + ag + ["Thanks"], "%s%s" % (kind, "/html" if html else ""), dims={"enc": kind})


def gen_label_markup(rng):
    pin = digits(rng, rng.choice((4, 6)))
    label = rng.choice(("Passcode", "Password", "Meeting ID", "PIN", "Access code", "Conference ID"))
    if label in ("Meeting ID", "Conference ID"):
        pin = "%s %s %s" % (digits(rng, 3), digits(rng, 3), digits(rng, 3))
    forms = {
        "bold": "**%s:** {v}", "bold_inside": "**%s**: {v}", "italic": "_%s:_ {v}", "code": "`%s`: {v}", "strike": "~~%s~~ {v}",
        "link": "[%s](https://x.example.test/a): {v}", "html_b": "<b>%s</b>: {v}", "html_a": "<a href='https://x.example.test'>%s</a>: {v}",
        "emoji": "\U0001f512 %s: {v} \U0001f512", "emoji_mid": "%s \U0001f511 {v}", "rlm": "\u200f%s\u200f: {v}",
        "rlo": "\u202e%s\u202c: {v}", "fullwidth_colon": "%s\uff1a {v}", "soft_hyphen": "%s: {v}", "zwj": "%s: {v}",
        "arabic_colon": "%s\u061b {v}", "nbsp": "%s:\u00a0{v}", "bullet": "\u2022 %s: {v}", "quote": "> %s: {v}", "table_cells": "|%s|{v}|",
        "bidi_isolate": "\u2067%s\u2069: {v}", "dotted": "%s....... {v}", "upper": "%s: {v}", "spaced": "%s : {v}",
        "caps_spaced": "%s : {v}", "no_space": "%s:{v}", "equals": "%s={v}", "dash": "%s - {v}", "parens": "(%s: {v})",
    }
    kind = rng.choice(sorted(forms))
    lab = label
    if kind == "soft_hyphen":
        lab = label[:3] + "\u00ad" + label[3:]
    if kind == "zwj":
        lab = label[:3] + "\u200d" + label[3:]
    if kind == "upper":
        lab = label.upper()
    if kind == "caps_spaced":
        lab = " ".join(label.upper().replace(" ", ""))
    line = forms[kind].replace("%s", lab).replace("{v}", pin)
    where = rng.choice(("same", "next_line", "next_block"))
    ag = agenda(rng, 3)
    if kind.startswith("html"):
        t = "<p>Agenda</p>" + "".join("<p>%s</p>" % esc(x) for x in ag) + "<p>%s</p>" % line
        if where != "same":
            t = t.replace(": " + pin, "")
            t += "<p>%s</p>" % pin
    else:
        if where == "same":
            t = "\n".join(["Agenda"] + ag) + "\n\n" + line
        else:
            t = "\n".join(["Agenda"] + ag) + "\n\n" + line.replace(pin, "").rstrip() + ("\n" if where == "next_line" else "\n\n") + pin
    return Body(t, [pin], ["Agenda"] + ag, "%s/%s" % (kind, where), dims={"kind": kind, "where": where, "label": label})


def gen_safelinks(rng):
    """Outlook Safe Links and tracker wrappers around a join URL that carries a passcode in its query."""
    from urllib.parse import quote
    pw = rng.choice((digits(rng, 6), digits(rng, 8), alnum(rng, 8)))
    key = rng.choice(("passcode", "pwd", "p", "pin", "password", "code", "access", "k"))
    inner = "https://teams.example.test/l/meetup-join/abc?%s=%s&x=1" % (key, pw)
    wrap = rng.choice(("safelink", "safelink2", "proofpoint", "tracker", "plain"))
    if wrap == "safelink":
        u = "https://eur01.safelinks.protection.example.test/?url=%s&data=05%%7C01%%7Cmia.hale%%40example.test&sdata=abc123&reserved=0" % quote(inner, safe="")
    elif wrap == "safelink2":
        u = "https://eur01.safelinks.protection.example.test/?url=%s&data=05" % quote(quote(inner, safe=""), safe="")
    elif wrap == "proofpoint":
        u = "https://urldefense.example.test/v3/__%s__;!!abc$" % inner
    elif wrap == "tracker":
        u = "https://click.example.test/track?u=%s&r=77" % quote(inner, safe="")
    else:
        u = inner
    form = rng.choice(("bare", "label", "html_a", "html_text"))
    ag = agenda(rng, 3)
    if form == "html_a":
        t = "<p>Agenda</p>" + "".join("<p>%s</p>" % esc(x) for x in ag) + "<p><a href=\"%s\">Join the meeting</a></p>" % esc(u)
    elif form == "html_text":
        t = "<p>Agenda</p>" + "".join("<p>%s</p>" % esc(x) for x in ag) + "<p><a href=\"https://x.example.test\">%s</a></p>" % esc(u)
    elif form == "label":
        t = "\n".join(["Agenda"] + ag) + "\n\nJoin: " + u
    else:
        t = "\n".join(["Agenda"] + ag) + "\n\n" + u
    return Body(t, [pw] if len(pw) >= 4 else [], ["Agenda"] + ag, "%s/%s/%s" % (wrap, key, form))


def gen_repeated(rng):
    """The calendar body pasted twice or thrice (reply chains; recurring series): once with a join block, once with a different PIN."""
    pin1, pin2 = digits(rng, 6), digits(rng, 6)
    ag = agenda(rng, 3)
    one = lambda p: ["Agenda"] + ag + ["", "Meeting ID: %s %s %s" % (digits(rng, 3), digits(rng, 3), digits(rng, 3)), "Passcode: " + p, "", "Thanks"]  # noqa: E731
    sep = rng.choice(("\n\n", "\n________\n", "\n\n-----Original Message-----\n", "\n\n> "))
    n = rng.choice((2, 3))
    pins = [pin1, pin2, pin1][:n]
    text = sep.join("\n".join(one(p)) for p in pins)
    return Body(text, pins, ["Agenda"] + ag + ["Thanks"], "x%d/%s" % (n, repr(sep)[1:6]))


def gen_numbered_long(rng):
    """A long agenda 1..K (K up to 100) with one join block somewhere; the join block must go, the numbered items must stay."""
    k = rng.choice((10, 30, 60, 100))
    items = ["%d. %s %d" % (i + 1, rng.choice(AGENDA), i + 1) for i in range(k)]
    pos = rng.randrange(k)
    pin = digits(rng, 6)
    join = ["Meeting ID: %s %s %s" % (digits(rng, 3), digits(rng, 3), digits(rng, 3)), "Passcode: " + pin]
    layout = rng.choice(("plain", "tight", "html_p", "html_li"))
    blocks = [items[:pos], join, items[pos:]] if layout in ("plain", "tight") else [[x] for x in items[:pos]] + [join] + [[x] for x in items[pos:]]
    keepers = rng.sample(items, min(8, len(items)))
    return Body(render(blocks, layout), [pin], keepers, "k%d/%s" % (k, layout), dims={"k": k, "layout": layout})


def gen_tz_and_dial(rng):
    """Time-zone lists and dial-in lists per country (3 to 30 numbers): the whole dial list should go, the zone list and the agenda stay."""
    ag = agenda(rng, 3)
    zones = ["%02d:%02d %s" % (rng.randrange(24), rng.choice((0, 30)), c) for c in rng.sample(["London", "Paris", "New York", "Tokyo", "Sydney", "Dubai"], 4)]
    nd = rng.choice((3, 8, 15, 30))
    cc = ["+%d" % rng.choice((1, 33, 44, 49, 61, 81, 971)) for _ in range(nd)]
    style = rng.choice(("e164", "paren", "dots", "toll", "pin_after"))
    nums = []
    for c in cc:
        if style == "e164":
            nums.append("%s %s %s" % (c, digits(rng, 3), digits(rng, 4)))
        elif style == "paren":
            nums.append("%s (%s) %s-%s" % (c, digits(rng, 2), digits(rng, 3), digits(rng, 4)))
        elif style == "dots":
            nums.append("%s.%s.%s" % (c, digits(rng, 3), digits(rng, 5)))
        elif style == "toll":
            nums.append("Toll free %s 800 %s" % (c, digits(rng, 6)))
        else:
            nums.append("%s %s,,%s#" % (c, digits(rng, 8), digits(rng, 8)))
    cty = ["UK", "France", "Germany", "USA", "Japan", "Australia", "UAE", "Canada"]
    dial = ["Dial in by country:"] + ["%s (%s)" % (x, cty[i % len(cty)]) for i, x in enumerate(nums)]
    layout = rng.choice(("plain", "tight", "html_p", "html_br", "html_table"))
    blocks = [["Agenda"] + ag, ["Time zones:"] + zones, dial, ["Thanks"]] if layout in ("plain", "tight", "html_br") \
        else [[x] for x in ["Agenda"] + ag + ["Time zones:"] + zones] + [[x] for x in dial] + [["Thanks"]]
    secrets = [re.sub(r"\D", "", x)[-8:] for x in nums if len(re.sub(r"\D", "", x)) >= 8][:3]
    return Body(render(blocks, layout), secrets, ["Agenda"] + ag + zones + ["Thanks"], "n%d/%s/%s" % (nd, style, layout))


UNKNOWN_LANG = [("Zugangscode", "de"), ("Code d'acc\u00e8s", "fr"), ("Toegangscode", "nl"), ("\u041f\u0430\u0440\u043e\u043b\u044c", "ru"),
                ("\u30d1\u30b9\u30b3\u30fc\u30c9", "ja"), ("Passcode", "en"), ("Kod dost\u0119pu", "pl"), ("Conference PIN", "en"),
                ("Room key", "en"), ("Door code", "en"), ("Secret", "en"), ("Gate code", "en")]


def gen_provider_unknown(rng):
    """An invite from a conferencing product the filter has never seen: a house-style block with a code behind a label, in a language or not."""
    lab, lang = rng.choice(UNKNOWN_LANG)
    pin = digits(rng, rng.choice((4, 6, 8)))
    ag = agenda(rng, 3)
    sty = rng.choice(("inline", "stacked", "table", "para"))
    host = "https://bridge.example.test/r/%s" % alnum(rng, 8)
    if sty == "inline":
        blocks = [["Agenda"] + ag, ["Link: " + host, "%s: %s" % (lab, pin)], ["Thanks"]]
        t = render(blocks, rng.choice(("plain", "html_br")))
    elif sty == "stacked":
        t = render([["Agenda"] + ag, ["Link: " + host], [lab], [pin], ["Thanks"]], rng.choice(("plain", "html_p")))
    elif sty == "table":
        t = "<p>Agenda</p>" + "".join("<p>%s</p>" % esc(x) for x in ag) + "<table><tr><td>%s</td><td>%s</td></tr></table><p>Thanks</p>" % (lab, pin)
    else:
        t = "\n".join(["Agenda"] + ag) + "\n\nTo get in, ask for the %s %s at the desk.\n\nThanks" % (lab.lower(), pin)
    return Body(t, [pin], ["Agenda"] + ag + ["Thanks"], "%s/%s" % (lang, sty), dims={"lang": lang, "style": sty, "label": lab})


GENERATORS = {
    "orphans": (gen_orphans, 101), "single_anchor": (gen_single_anchor, 102), "provider_one_line": (gen_provider_one_line, 103),
    "encodings": (gen_encodings, 104), "label_markup": (gen_label_markup, 105), "safelinks": (gen_safelinks, 106),
    "repeated": (gen_repeated, 107), "numbered_long": (gen_numbered_long, 108), "tz_and_dial": (gen_tz_and_dial, 109),
    "provider_unknown": (gen_provider_unknown, 110),
}


def measure_all(n=None):
    n = n or N
    res = {}
    for name, (gen, seed) in GENERATORS.items():
        bodies = run_gen(gen, n, seed)
        res[name] = (measure(C, bodies), measure(OLD, bodies, check_idem=False, record=False), bodies)
    return res


def print_report(res):
    for name, (c, o, _b) in res.items():
        print("\n## %s  (n=%d)" % (name, c.n))
        print("  C   : idem-fail %d  errors %s  secrets %d  leaks %d (%s)  keepers %d  lost %d  whole-agenda-lost %d  %.2fs worst %.3fs"
              % (c.nonidem, dict(c.errors), c.secrets, c.leak_total, dict(Counter({k[1]: v for k, v in c.leaks.items()})), c.keepers,
                 c.lost_total, sum(c.whole_lost.values()), c.seconds, c.worst))
        print("  old : secrets %d  leaks %d  keepers %d  lost %d  %.2fs" % (o.secrets, o.leak_total, o.keepers, o.lost_total, o.seconds))
        for st in (c,):
            top = sorted(st.leaks.items(), key=lambda kv: -kv[1])[:6]
            for (tag, kind), cnt in top:
                print("    leak %-40s %-5s %4d  e.g. %r" % (tag, kind, cnt, st.leak_example[(tag, kind)][:110]))
            top = sorted(st.lost.items(), key=lambda kv: -kv[1])[:6]
            for tag, cnt in top:
                print("    lost %-40s %4d of %d bodies (whole %d) e.g. %r" % (tag, cnt, st.bodies_by_tag[tag], st.whole_lost[tag],
                                                                              st.lost_example[tag][0][:110]))


# ================================================================================ generator tests (ratchets)

GEN_N = 400     # bodies per generator in the unit tests (the --report run uses N)
# Ratchets: upper bounds for the default seeds at GEN_N = 400 (measured; lower them when a fix lands).
# name: (max C leaks, max C lost keepers, max non-idempotent).  Old scrub for comparison: leaks 479/28/15/0/8/0/0/0/0/39, lost 0 everywhere
# except encodings (480, the same).
RATCHET = {
    "orphans": (4, 72, 0), "single_anchor": (0, 75, 0), "provider_one_line": (0, 0, 0), "encodings": (0, 0, 0),
    "label_markup": (0, 0, 0), "safelinks": (0, 0, 0), "repeated": (0, 0, 0), "numbered_long": (0, 615, 0), "tz_and_dial": (0, 0, 0),
    "provider_unknown": (0, 4, 0),
}


class Generators(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = measure_all(GEN_N)

    def test_no_exceptions(self):
        for name, (c, o, _b) in self.res.items():
            self.assertEqual(dict(c.errors), {}, name)
            self.assertEqual(dict(o.errors), {}, name)

    def test_ratchets(self):
        bad = []
        for name, (c, _o, _b) in self.res.items():
            if name not in RATCHET:
                continue
            ml, mk, mi = RATCHET[name]
            if c.leak_total > ml:
                bad.append((name, "leaks", c.leak_total, ml))
            if c.lost_total > mk:
                bad.append((name, "lost", c.lost_total, mk))
            if c.nonidem > mi:
                bad.append((name, "nonidem", c.nonidem, mi))
        self.assertEqual(bad, [])

    def test_never_slow(self):
        for name, (c, _o, _b) in self.res.items():
            self.assertLess(c.worst, 1.0, name)


# ================================================================================ minimal findings (expectedFailure)

def kept(text):
    return [x for x in C(text).split("\n") if x.strip()]


def has(text, needle):
    return needle in C(text)


class OrphanFindings(unittest.TestCase):
    """Class A: orphan values after a label block that was dropped whole."""

    def test_O1_value_after_divider_leaks(self):
        """The orphan rule stops at a divider ('________'), so a PIN set under a rule line survives. (MED: uncommon layout.)"""
        t = "Hi\n\nMeeting ID: 412 889 330\n________\n8825\n\nQ3 budget review\n"
        self.assertNotIn("8825", C(t))

    def test_O2_second_orphan_after_unlisted_label_leaks(self):
        """A PIN behind a label the scrub does not list (es 'Clave'), then a second short value: the label line itself survives and the
        second value leaks (the label block and the first value go, the chain counts the label)."""
        t = "ID de la reuni\u00f3n:\n\n901 917 930 4\n\nClave\n\n8825\n\n7731\n\nAgenda item 1: budget\nAgenda item 2: hiring\n"
        out = C(t)
        self.assertNotIn("8825", out)
        self.assertNotIn("7731", out)

    def test_O3_orphan_rule_takes_an_ordinary_agenda_line(self):
        """Over-take: a short ordinary line holding one letter-digit token ('Ticket INC1234 follow-up') after a dropped block is
        taken as an orphan, and the line after it is lost as the second orphan. (MED: data loss.)"""
        t = "Dial-in: +44 20 7946 0000\n\nINC1234\n\nTicket INC1234 follow-up\n"
        self.assertIn("follow-up", C(t))

    def test_O4_room_number_after_join_block_is_lost(self):
        """'Room 1204' (4 digits, 9 characters) after a dropped join block is taken for a PIN. (MED.)"""
        t = "Meeting ID: 412 889 330\n\nRoom 1204\n\nBudget 2026\n"
        self.assertIn("Room 1204", C(t))

    def test_O5_two_orphans_then_agenda_survives(self):
        t = "Meeting ID: 412 889 330\n\n8825\n\n7731\n\nAgenda: Q3 budget review\n"
        out = C(t)
        self.assertNotIn("8825", out)
        self.assertNotIn("7731", out)
        self.assertIn("Q3 budget review", out)

    def test_O6_third_orphan_is_not_taken(self):
        """The chain stops at two: a third value-only block is kept (documented limit; a third secret leaks, not asserted as a defect)."""
        t = "Meeting ID: 412 889 330\n\n1111\n\n2222\n\n3333\n"
        self.assertIn("3333", C(t))

    def test_O7_orphan_inside_list_and_after_html_table(self):
        self.assertNotIn("8825", C("Join info\n- Clave de acceso\n- 8825\n- Q3 budget review\n"))
        t = "<p>x</p><table><tr><td>Meeting ID</td><td>412 889 330</td></tr></table><p>Q3 budget review</p>"
        self.assertIn("Q3 budget review", C(t))


class AnchorFindings(unittest.TestCase):
    """Agendas with exactly one link or one phone number."""

    def test_A1_one_link_in_a_contiguous_agenda_drops_the_whole_agenda(self):
        """'2. Read https://wiki.example.test/spec first' in a contiguous agenda: the URL is a strong anchor, so the BLOCK goes (every
        agenda line). The old scrub keeps all four lines. (MED, the largest data loss found: any plain-text agenda with a link.)"""
        t = "Agenda\n1. Welcome\n2. Read https://wiki.example.test/spec first\n3. Close\n"
        self.assertIn("1. Welcome", C(t))
        self.assertIn("3. Close", C(t))

    def test_A2_bare_host_path_drops_the_whole_agenda(self):
        t = "Agenda\n1. Welcome\n2. Read wiki.example.test/spec\n3. Close\n"
        self.assertIn("1. Welcome", C(t))

    def test_A3_www_host_drops_the_whole_agenda(self):
        t = "Agenda\n1. Welcome\n2. Read www.example.test first\n3. Close\n"
        self.assertIn("3. Close", C(t))

    def test_A4_angle_bracket_link_under_agenda_drops_it(self):
        t = "Agenda\n1. Welcome\n2. Close\nSee <https://wiki.example.test/spec>"
        self.assertIn("2. Close", C(t))

    def test_A13_plain_link_costs_its_own_line_only(self):
        """Fix of finding 3: a link with no session (no digits, no passcode query) goes alone; the agenda around it stays."""
        for line in ("Read https://wiki.example.test/spec first", "Read wiki.example.test/spec first", "Our site: www.example.test",
                     "See <https://wiki.example.test/spec>", "Read https://wiki.example.test/2026/plan first"):
            out = C("Agenda\n1. Welcome\n" + line + "\n3. Close\n")
            self.assertEqual(out, "Agenda\n1. Welcome\n3. Close", line)

    def test_A14_a_link_that_carries_a_session_still_takes_its_block(self):
        """The whole-block drop stays for a link the scrub leaves alone but that holds a long mixed token; the others the scrub removes
        itself (the link never reaches the anchor layer), so the agenda stays and the link and its secret are gone."""
        out = C("Agenda\n1. Welcome\nNotes https://x.example.test/r/q4mkeu4nzz9wq2rt7\n3. Close\n")
        self.assertNotIn("Welcome", out)
        for line in ("Join https://zoom.example.test/j/91234567890", "Notes https://x.example.test/room?pwd=abcDEF",
                     "Notes https://x.example.test/a?token=zz", "Notes https://teams.example.test/l/meetup-join/19%3ameeting_abc/0",
                     "Notes https://x.example.test/p?id=4417"):
            out = C("Agenda\n1. Welcome\n" + line + "\n3. Close\n")
            self.assertNotIn("example.test", out, line)

    def test_A15_bare_meet_link_under_the_agenda_goes_alone(self):
        out = C("Agenda\n1. Welcome\n2. Close\nhttps://meet.example.test/abc-defg-hij")
        self.assertEqual(out, "Agenda\n1. Welcome\n2. Close")

    def test_A5_one_phone_number_drops_only_its_line(self):
        t = "Agenda\n1. Welcome\n2. Call Pat on +44 20 7946 0958 re budget\n3. Close\n"
        out = C(t)
        self.assertIn("1. Welcome", out)
        self.assertIn("3. Close", out)
        self.assertNotIn("7946", out)

    def test_A6_one_link_with_query_drops_only_its_line(self):
        out = C("Agenda\n1. Welcome\n2. Read https://wiki.example.test/spec?id=77 first\n3. Close")
        self.assertIn("1. Welcome", out)
        self.assertIn("3. Close", out)

    def test_A7_link_in_its_own_block_goes_alone(self):
        out = C("Agenda\n1. Welcome\n2. Close\n\nSpec: https://wiki.example.test/spec\n\nThanks")
        self.assertIn("2. Close", out)
        self.assertIn("Thanks", out)

    def test_A8_html_list_with_anchor_text_link_keeps_the_text(self):
        out = C("<p>Agenda</p><ul><li>Welcome</li><li>Read <a href='https://wiki.example.test/spec'>the spec</a></li><li>Close</li></ul>")
        self.assertIn("Read the spec", out)

    @unittest.expectedFailure
    def test_A9_html_paragraph_with_visible_link_is_lost_with_its_neighbours(self):
        """HTML <p>Spec: <a>https://...</a></p> directly under 'Agenda' (no blank line from the converter): 'Agenda' is kept, but a
        wiki link is not a join secret; the line goes (acceptable) and the old scrub keeps it. Recorded: the line loss only."""
        t = "<p>Agenda</p><p>Spec: <a href='https://wiki.example.test/spec'>https://wiki.example.test/spec</a></p><p>Thanks</p>"
        self.assertIn("wiki.example.test/spec", C(t))

    def test_A10_teams_ics_line_alone_goes_and_agenda_stays(self):
        t = ("Agenda\n1. Welcome\n2. Close\n\nX-MICROSOFT-SKYPETEAMSMEETINGURL:https://teams.example.test/l/meetup-join/19%3ameeting_abc/0"
             "?context=x\n")
        self.assertEqual(C(t), "Agenda\n1. Welcome\n2. Close")

    def test_A11_signature_dial_in_goes_signature_name_stays(self):
        out = C("Thanks,\nMia Hale\nProgramme Manager\nDirect dial: +44 20 7946 0958\n\nPS bring the budget pack.")
        self.assertIn("Mia Hale", out)
        self.assertNotIn("7946", out)

    def test_A12_zoom_one_line_goes_agenda_stays(self):
        out = C("Agenda\n1. Welcome\n\nJoin Zoom Meeting https://zoom.example.test/j/91234567890?pwd=abcDEF123\n\n2. Budget\n")
        self.assertIn("2. Budget", out)
        self.assertNotIn("91234567890", out)
        self.assertNotIn("abcDEF123", out)


class MoreOrphanFindings(unittest.TestCase):
    """The orphan rule never sees a value that sits directly under the line the scrub removed (D: the scrub runs first, so the anchor layer has
    no dropped block to attach the orphan to) and judges one token at a time."""

    def test_O8_four_digit_value_directly_under_the_id_line_leaks_in_html(self):
        """HIGH-candidate: <p>Meeting ID: ...</p><p>8825</p> (also <div> and <br>, and plain text with no blank line). 4-digit values only:
        6 or more digits go by the bare-PIN rule, a blank line by _without_orphans. Old scrub leaks it too."""
        t = "<p>Meeting ID: 412 889 330</p><p>8825</p><p>Agenda: budget</p>"
        self.assertNotIn("8825", C(t))

    def test_O9_four_digit_value_directly_under_the_id_line_leaks_in_plain_text(self):
        t = "Subject: x\n\nMeeting ID: 412 889 330\n8825\n\nAgenda: budget"
        self.assertNotIn("8825", C(t))

    def test_O10_spaced_three_plus_three_value_leaks_even_after_a_blank_line(self):
        """'984 522' (a spaced 6-digit PIN): _orphan_value judges one token, and 984 and 522 are 3 digits each. Leaks in every layout."""
        t = "Meeting ID: 412 889 330\n\n984 522\n\nAgenda: x"
        self.assertNotIn("984 522", C(t))

    def test_O11_list_marker_hides_the_orphan(self):
        """'- 4076' under the ID line: every shape leaks in list layout (55 percent of the generated orphans)."""
        t = "Meeting ID: 526 903 470\n- 4076\n\nAgenda: x"
        self.assertNotIn("4076", C(t))

    def test_O12_ext_line_is_taken_for_an_orphan(self):
        """'Ext 4417 for help' (17 characters, 4 tokens, one 4-digit token) after a dropped join block is always taken. 'Room 1204' about
        60 percent of the time, 'Ticket INC1234 follow-up' about 40 percent (random 4-digit rooms)."""
        t = "Subject: x\n\nMeeting ID: 412 889 330\n\nExt 4417 for help\n\nThanks"
        self.assertIn("Ext 4417 for help", C(t))

    def test_O13_value_after_a_stacked_unlisted_label_in_english_leaks(self):
        """'Room key' is not a listed label: <p>Room key</p><p>7118</p> leaks the value (7 percent of the 'Room key' provider-unknown bodies)."""
        t = "<p>Agenda</p><p>Link: https://bridge.example.test/r/q4mkeu4n</p><p>Room key</p><p>7118</p><p>Thanks</p>"
        self.assertNotIn("7118", C(t))

    def test_O14_polish_label_with_pin_in_a_sentence_leaks(self):
        """'kod dost\u0119pu' is not a listed label; in a sentence ('ask for the kod dostepu 7118 at the desk') or a table cell it leaks.
        As 'Kod dost\u0119pu: 7118' on its own line it is caught."""
        t = "Agenda\n\nTo get in, ask for the kod dost\u0119pu 7118 at the desk.\n\nThanks"
        self.assertNotIn("7118", C(t))

    def test_O16_spaced_letters_label_variants(self):
        for t in ("Agenda\n\nP A S S C O D E :\n\n6960", "Agenda\n\nP I N 8825 x", "Agenda\n\nA C C E S S C O D E : 4417", "Agenda\n\nM E E T I N G  I D : 412 889 330"):
            self.assertEqual(C(t), "Agenda", t)
        keep = "Agenda\nOption A B C D is best\nPlan B"
        self.assertEqual(C(keep), keep)

    def test_O17_long_label_without_a_separator_in_a_sentence(self):
        self.assertNotIn("4417", C("Agenda\n\nSee the codigo de acceso 4417-b9 in the mail\n\nThanks"))
        self.assertIn("5 on the list", C("Agenda\n1. Budget number 5 on the list\n2. Close"))

    def test_O15_letter_spaced_label_leaks(self):
        """'P A S S W O R D : 4330' (letters spaced out): the label is not recognised. LOW: needs an author who does it on purpose."""
        self.assertNotIn("4330", C("Agenda: x\n\nP A S S W O R D : 4330"))


class PlainEncodingFindings(unittest.TestCase):
    def test_E1_unicode_line_separators_in_plain_text_lose_the_neighbours(self):
        """U+2028 / U+2029 / NEL are not line breaks to the plain-text path (the HTML path splits them), so an agenda joined with them is
        one line, and a Passcode in it takes the lot. Safe (nothing leaks), a loss for ordinary text. (LOW.)"""
        t = "Agenda budget\u2028Passcode: 8825\u2028Thanks all"
        out = C(t)
        self.assertNotIn("8825", out)
        self.assertIn("Agenda budget", out)

    def test_E2_utf16_misdecoded_as_latin1_does_not_leak_a_plain_pin(self):
        t = "Passcode: 8825\nAgenda budget".encode("utf-16-le").decode("latin-1")
        out = C(t)
        self.assertNotIn("8825", compact(out))
        self.assertEqual(compact(out), compact(out))

    def test_E3_base64_of_a_passcode_is_dropped_by_the_shape_gate(self):
        self.assertNotIn("UGFzc2NvZGU6", C("UGFzc2NvZGU6IDg4MjU= \n\nagenda"))


class LabelMarkupFindings(unittest.TestCase):
    @unittest.expectedFailure
    def test_M1_hebrew_label_pin_leaks(self):
        """An unlisted-language label (Hebrew 'access code') with a 4-digit PIN: same class as finding 1 of pass 1; also under RLE/PDF marks."""
        t = "\u202b\u05e7\u05d5\u05d3 \u05d2\u05d9\u05e9\u05d4\u202c: 8825\n\nagenda"
        self.assertNotIn("8825", C(t))


class LongAgendaFindings(unittest.TestCase):
    def test_N1_cap_ends_a_long_numbered_agenda_at_1500_characters(self):
        """Documented cap, recorded here because it is where long agendas lose data: items 1..100 keep only what fits 1,500 characters."""
        items = ["%d. Item number %d for discussion" % (i, i) for i in range(1, 101)]
        out = C("\n".join(items))
        self.assertLessEqual(len(out), 1500)
        self.assertTrue(out.startswith("1. Item number 1 "))
        self.assertNotIn("100. Item", out)

    def test_N2_dial_list_of_thirty_numbers_goes_and_agenda_stays(self):
        nums = ["+%d %d %d" % (40 + i, 200 + i, 3000 + i * 7) for i in range(30)]
        t = "Agenda\n1. Budget\n\nDial in by country:\n" + "\n".join("%s (C%d)" % (n, i) for i, n in enumerate(nums)) + "\n\n2. Hiring"
        out = C(t)
        self.assertIn("1. Budget", out)
        self.assertIn("2. Hiring", out)
        self.assertNotIn("+40", out)


class SafeLinkFindings(unittest.TestCase):
    def test_S1_safelink_with_passcode_in_query_is_removed_whole_line(self):
        t = ("See https://eur01.safelinks.protection.example.test/?url=https%3A%2F%2Fteams.example.test%2Fl%2Fmeetup-join%2Fabc"
             "%3Fpasscode%3D4417&data=05%7C01&sdata=x\n\nAgenda: budget")
        out = C(t)
        self.assertNotIn("4417", out)
        self.assertIn("Agenda: budget", out)


# ================================================================================ looks_like_html: quadratic

def _fit_exponent(sizes, times):
    """Least-squares slope of log(time) on log(size)."""
    xs, ys = [math.log(s) for s in sizes], [math.log(max(t, 1e-7)) for t in times]
    k = len(xs)
    return (k * sum(x * y for x, y in zip(xs, ys)) - sum(xs) * sum(ys)) / (k * sum(x * x for x in xs) - sum(xs) ** 2)


def linear_looks_like_html(text):
    """The proposed fix, for comparison and for the test: find the last '>' once; a tag start after it cannot be closed, so stop."""
    if not text:
        return False
    if len(text) > B.MAX_INPUT:
        text = text[:B.MAX_INPUT]
    last_gt = text.rfind(">")
    i = text.find("<")
    while i != -1:
        if text.startswith("<!--", i) or text[i + 1:i + 9].lower() == "!doctype":
            return True
        if i < last_gt and B._tag_at(text, i):
            return True
        i = text.find("<", i + 1)
    return False


QUAD_INPUTS = {
    "open_tags_no_gt": lambda n: "<b " * (n // 3),
    "words_then_open_tag": lambda n: "a <" * (n // 3),
    "div_no_gt": lambda n: "<div" * (n // 4),
    "lt_only": lambda n: "<" * n,
    "comment_openers": lambda n: "<!-" * (n // 3),
    "tag_prefixes": lambda n: "<bx " * (n // 4),
}


def growth(fn, make, sizes=(5000, 10000, 20000, 40000, 80000, 160000, 320000, 640000, 1000000, 1000000), reps=1):
    times = []
    for s in sizes:
        t = make(s)
        best = 9e9
        for _ in range(reps):
            a = time.perf_counter()
            fn(t)
            best = min(best, time.perf_counter() - a)
        times.append(best)
    return sizes, times


class LooksLikeHtml(unittest.TestCase):
    def test_fix_agrees_with_current_on_samples(self):
        samples = ["", "a < b", "<b>x</b>", "<b x", "x <br", "<!-- c", "<!DOCTYPE html>", "<p>a</p> <b", "1 < 2 > 1", "<b <i>", "text<br/>",
                   "<div", "<div>", "< b>", "a<b", "<style>x</style>", "<o:p>", "<foo>"]
        for s in samples:
            self.assertEqual(linear_looks_like_html(s), B.looks_like_html(s), repr(s))
        rng = random.Random(7)
        for _ in range(3000):
            s = "".join(rng.choice(["<", ">", "b", "div", " ", "/", "!--", "a", "<br", "\n"]) for _ in range(rng.randrange(1, 30)))
            self.assertEqual(linear_looks_like_html(s), B.looks_like_html(s), repr(s))

    def test_agrees_with_the_function_before_the_fix(self):
        """The 2.6.8 / 6ce15ff9 looks_like_html, copied here, and the linear one answer alike on 6,000 random strings and the hand cases."""
        def old(text):
            if not text:
                return False
            if len(text) > B.MAX_INPUT:
                text = text[:B.MAX_INPUT]
            i = text.find("<")
            while i != -1:
                if text.startswith("<!--", i) or text[i + 1:i + 9].lower() == "!doctype":
                    return True
                if B._tag_at(text, i) and text.find(">", i) != -1:
                    return True
                i = text.find("<", i + 1)
            return False
        rng = random.Random(11)
        for s in ["", "a < b", "<b>x</b>", "<b x", "x <br", "<!-- c", "<!DOCTYPE html>", "<p>a</p> <b", "1 < 2 > 1", "<b <i>", "<div", "< b>"]:
            self.assertEqual(B.looks_like_html(s), old(s), repr(s))
        for _ in range(6000):
            s = "".join(rng.choice(["<", ">", "b", "div", " ", "/", "!--", "a", "<br", "\n", "<p", "p>"]) for _ in range(rng.randrange(1, 40)))
            self.assertEqual(B.looks_like_html(s), old(s), repr(s))

    def test_fix_is_linear(self):
        for name, make in QUAD_INPUTS.items():
            sizes, times = growth(linear_looks_like_html, make, sizes=(100000, 200000, 400000, 800000), reps=2)
            self.assertLess(_fit_exponent(sizes, times), 1.3, (name, times))

    def test_L1_looks_like_html_is_quadratic_on_unclosed_tags(self):
        """Every '<b ' makes text.find('>', i) scan to the end of the text when no '>' follows: O(n * number of '<'). 1,000,000 characters of
        '<b ' take about 3 s (about 5 ms at the gateway's 20,000 cap, so no production hang, but a 1 MB body or any caller of
        invite_blocks.to_lines / blocks without the 20 KB cut pays it). Fix: find the last '>' once (see linear_looks_like_html)."""
        t = "<b " * (1000000 // 3)
        a = time.perf_counter()
        B.looks_like_html(t)
        d = time.perf_counter() - a
        self.assertLess(d, 0.5, d)
        for name, make in QUAD_INPUTS.items():
            sizes, times = growth(B.looks_like_html, make, sizes=(100000, 200000, 400000, 800000), reps=2)
            self.assertLess(_fit_exponent(sizes, times), 1.3, (name, times))


# ================================================================================ gateway invariants over the generated bodies

def _row(i, body, **kw):
    r = {"id": "e%d" % i, "start": "10:00", "end": "11:00", "all_day": False, "title": "Budget review", "where": "Room 204", "teams": True,
         "private": False, "organiser": "Mia Hale", "sensitivity": "normal", "organiser_email": "mia.hale@example.test",
         "recurrence": "weekly", "body": body, "attendees": [{"name": "Omar Reyes", "type": "required", "response": "accepted"}],
         "attachments": ["plan.docx"]}
    r.update(kw)
    return r


class GatewayRoundTrip(unittest.TestCase):
    """Writer -> reader -> second filter. The filter output is what the sweep stores; readers and drafts read it back."""

    @classmethod
    def setUpClass(cls):
        cls.bodies = []
        for gen, seed in GENERATORS.values():
            cls.bodies += run_gen(gen, 60, seed + 1000)

    def test_stamp_row_is_idempotent(self):
        bad = 0
        for i, b in enumerate(self.bodies):
            r = G.clean_row(_row(i, b.text))
            if G.stamp_row(r) != r or G.clean_row(r) != r:
                bad += 1
        self.assertEqual(bad, 0)

    def test_stored_body_refilters_to_itself(self):
        """filter_body(stored body) == stored body: the second pass of any reader that filters again changes nothing."""
        bad = [b.text for i, b in enumerate(self.bodies) if G.filter_body(G.clean_row(_row(i, b.text)).get("body", "")) != G.clean_row(_row(i, b.text)).get("body", "")]
        self.assertEqual(len(bad), 0, bad[:1])

    def test_read_never_writes_and_serves_the_stored_body(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "calendar.json"
            rows_raw = [_row(i, b.text) for i, b in enumerate(self.bodies[:120])]
            stamped = [G.clean_row(r) for r in rows_raw[:60]]
            cal = {"fetched": "2026-10-26T08:00", "to": "2026-11-02", "days": {"2026-10-26": rows_raw[60:] , "2026-10-27": stamped}}
            p.write_text(json.dumps(cal), encoding="utf-8")
            before = (p.read_bytes(), p.stat().st_mtime_ns, sorted(os.listdir(d)))
            G.clear_cache()
            for purpose in G.purpose_names():
                got = G.read(purpose, p)
            after = (p.read_bytes(), p.stat().st_mtime_ns, sorted(os.listdir(d)))
            self.assertEqual(before, after)
            got = G.read("agenda", p)
            for r, s in zip(got["days"]["2026-10-27"], stamped):
                self.assertEqual(r.get("body", ""), s.get("body", ""))
            # unstamped rows are served exactly as the writer would store them
            for r, raw in zip(got["days"]["2026-10-26"], rows_raw[60:]):
                self.assertEqual(r.get("body", ""), G.clean_row(raw).get("body", ""))

    def test_secrets_never_survive_the_round_trip_that_c_removes(self):
        """What C removes stays removed after the gateway's cap and a second filter (the read path adds no new leak)."""
        leaks_c = leaks_rt = 0
        for i, b in enumerate(self.bodies):
            c_out = C(b.text)
            rt = G.clean_row(_row(i, b.text)).get("body", "")
            allc = "".join(compact(x) for x in c_out.split("\n"))
            allr = "".join(compact(x) for x in rt.split("\n"))
            for s in b.secrets:
                if s in allc:
                    leaks_c += 1
                if s in allr:
                    leaks_rt += 1
        self.assertLessEqual(leaks_rt, leaks_c)


if __name__ == "__main__":
    if "--report" in sys.argv:
        sys.argv.remove("--report")
        print_report(measure_all())
        print("\n## looks_like_html growth (10 sizes, seconds)")
        for name, make in QUAD_INPUTS.items():
            sizes, times = growth(B.looks_like_html, make)
            print("  %-22s exponent %.2f  t(1MB)=%.3fs   fix: %.3fs" % (name, _fit_exponent(sizes[-6:], times[-6:]), times[-1],
                                                                       growth(linear_looks_like_html, make, sizes=(1000000,))[1][0]))
    else:
        unittest.main()
