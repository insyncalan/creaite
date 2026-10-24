"""#328: one plain-code matcher for a calendar meeting: which project it is about, how sure that is, and why.

No AI, no network, no writes. It reads the meeting's title and its attendees' addresses and the project register's rows
(capture.register), and answers {p, level, reason, cands}:

- level "matched": a code, a project name or a Teams channel in the title, or the series Alan chose before (a code in the
  title always beats that memory; when they disagree the answer is "unsure" with both projects as candidates);
- level "likely": medium signals agree on one project (an alias, a stakeholder named in the title, an attendee's address listed
  as a sender, an attendee's email domain listed for the project, two or more keywords);
- level "unsure": nothing, one keyword, or signals pointing at different projects (then `cands` lists them, at most three).

Addresses only count, never display names (a name in an invite can be anything). Alan's own domains and a word in a project's
Exclude column never count. A confidential meeting is matched on its title alone: pass no attendees. Reasons are fixed
sentences that name projects (by the register's name) and never an address, a domain or a person.
"""
import re

import capture

MAX_CANDS = 3


def _addresses(attendees):
    """Lower-case addresses of the attendees (dicts with "email", or plain strings); other text is ignored."""
    out = set()
    for a in attendees or []:
        raw = a.get("email") if isinstance(a, dict) else a
        m = re.fullmatch(r"\s*<?([^<>@\s]+@[^<>@\s]+\.[^<>@\s]+)>?\s*", str(raw or "")[:200])
        if m:
            out.add(m.group(1).lower())
    return out


def _title_signals(p, title, low, shared, first_names):
    """(strong, medium, weak) for a project from the title; None when its Exclude word rules it out."""
    sig = capture._signals(p, title, low, shared, first_names)         # noqa: SLF001  the register's own signal rules
    if sig is None:
        return None
    strong, medium, weak = sig
    named = [m for m in medium if p["name"] and m == p["name"]]            # the project's full name is strong
    return strong + named, [m for m in medium if m not in named], weak


def _people_signals(p, addrs, own, shared_domains):
    """Medium signals from attendee addresses: a sender listed for this project, or an email domain listed for it (not
    Alan's own, not one another project lists too)."""
    out = [a for a in addrs if a in p["senders"] and a.split("@")[-1] not in own]
    out += [a for a in addrs if a.split("@")[-1] in p["domains"] and a.split("@")[-1] not in own
            and a.split("@")[-1] not in shared_domains]
    return out


def _cands(codes, names):
    return sorted(codes)[:MAX_CANDS]


def match_meeting(title, attendees, rows, remembered_code=None, own_domains=(), shared=frozenset(), confidential=False):
    """{p, level, reason, cands} for one meeting. `rows` is capture.register()["projects"] (only active projects should be
    passed); `remembered_code` the project Alan chose for this series before; `attendees` is ignored for a confidential
    meeting."""
    title = str(title or "")
    low = title.lower()
    own = {str(d).lower().lstrip("@") for d in own_domains or []}
    addrs = set() if confidential else _addresses(attendees)
    names = {r["code"]: r["name"] or r["code"] for r in rows}
    first_names = capture._first_names(rows, shared)                          # noqa: SLF001
    all_domains = [d for r in rows for d in set(r["domains"])]
    shared_domains = {d for d in all_domains if all_domains.count(d) > 1}      # a domain two projects list is no evidence
    strong, medium, weak = {}, {}, {}
    for r in rows:
        sig = _title_signals(r, title, low, shared, first_names)
        if sig is None:
            continue                                                         # the Exclude column rules it out
        s, m, w = sig
        m = m + _people_signals(r, addrs, own, shared_domains)
        if s:
            strong[r["code"]] = s
        elif m:
            medium[r["code"]] = m
        elif w:
            weak[r["code"]] = w
    codes = {r["code"] for r in rows}
    mem = remembered_code if remembered_code in codes else None
    if len(strong) > 1 or (strong and mem and mem not in strong):
        both = set(strong) | ({mem} if mem else set())
        return _unsure(both, names, "Two projects fit")
    if strong:
        (code,) = strong
        return {"p": code, "level": "matched", "reason": "Named in the title", "cands": [code]}
    if mem:
        return {"p": mem, "level": "matched", "reason": "You chose this for the series before", "cands": [mem]}
    if len(medium) > 1:
        return _unsure(set(medium), names, "Two projects fit")
    if medium:
        (code,) = medium
        return {"p": code, "level": "likely", "reason": "Fits the project's register entry", "cands": [code]}
    if weak:
        return {"p": None, "level": "unsure", "cands": _cands(weak, names),
                "reason": "Only a single word points to a project: not enough to guess"}
    return {"p": None, "level": "unsure", "reason": "Nothing in the meeting names a project", "cands": []}


def _unsure(codes, names, lead):
    ordered = _cands(codes, names)
    return {"p": None, "level": "unsure", "cands": ordered,
            "reason": lead + ": " + " or ".join(names[c] for c in ordered)}


PUBLIC_DOMAINS = {"gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "live.com", "yahoo.com", "icloud.com", "me.com",
                  "aol.com", "proton.me", "protonmail.com"}


def offer_signal(attendees, rows, own_domains=(), confidential=False):
    """The one concrete signal worth offering to remember after Alan picks a project for a meeting: the email domain of an
    attendee that no project lists yet (never Alan's own, a public mail provider or a confidential meeting's), else None.
    {"kind": "domain", "value": "client.example"}. propose.learn_check still has the last word."""
    if confidential:
        return None
    own = {str(d).lower().lstrip("@") for d in own_domains or []}
    listed = {d for r in rows for d in r["domains"]}
    counts = {}
    for a in _addresses(attendees):
        d = a.split("@")[-1]
        if d not in own and d not in listed and d not in PUBLIC_DOMAINS:
            counts[d] = counts.get(d, 0) + 1
    if not counts:
        return None
    return {"kind": "domain", "value": sorted(counts, key=lambda d: (-counts[d], d))[0]}
