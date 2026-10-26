"""Cap's hostile cases for #250 (the confidential-transcript hold in transcripts.SweepFetch), kept as a test. Fictional data only.

The hostile assumption: Microsoft 365 returns the confidential meeting's transcript (ev-1's) for ANY spelling of its URL. A case fails
when that text lands in inbox/. Classes: N1 (8 spellings x 2 event-read orders x 2 read forms), Three (ev-1 confidential, ev-2 and ev-3
normal, every order, every read form), Spelling (34 more ways of writing the meeting, both orders) and Order (the transcript read comes
before the confidential event is read: the fetch waits for the end of the run, SweepFetch.finish()).
Not here, by design: Cap's Hidden class (case-only join ids and another occurrence of a series are held back, a fail-safe over-hold
that contradicts the upper-case-path cases above) and Order c (the confidential event is never read in the run, so its URL is unknown).

Run: python3 dev/tests/test_fetch_transcripts_hostile.py     (about 90 seconds)
"""
import itertools
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_fetch_transcripts as F  # noqa: E402
from test_fetch_transcripts import add_row, edit_calendar, event, result_at  # noqa: E402

SECRET = "CONFIDENTIAL-HR-TEXT"
LEGIT = "ORDINARY-SYNC-TEXT"
DAY = F.DAY
WIN = f"?start={DAY}T08:00:00Z&end={DAY}T09:00:00Z"
P = "meeting-transcript:///events/"
BASE = P + "b64joinurl" + WIN                       # the fixture's own URL: event("ev-1")["meetingTranscriptUrl"]
assert event("ev-1")["meetingTranscriptUrl"] == BASE


def vtt(text):
    return ("WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n<v A>" + text + "</v>\n",)


class Base(F.Fetch):
    def setUp(self):
        super().setUp()
        self.set_on()
        # ev-1 confidential in the saved calendar too; ev-3 made a normal Teams meeting on the same day
        edit_calendar(self.v, lambda ev: ev.update(sensitivity="confidential") if ev.get("id") == "ev-1" else None)
        cal = self.v.root / "system/staging/calendar.json"
        c = json.loads(cal.read_text())
        for d in c["days"]:
            c["days"][d] = [e for e in c["days"][d] if e.get("id") != "ev-3"]
        cal.write_text(json.dumps(c))
        add_row(self.v, {"id": "ev-3", "start": "11:00", "end": "11:30", "title": "Budget review", "organiser": "Kim Example"})

    def ev(self, eid, url, conf=False):
        e = {**event(eid), "meetingTranscriptUrl": url}
        if conf:
            e["sensitivity"] = "confidential"
        return (f"calendar:///events/{eid}", e, False)

    def go(self, steps):
        out = self.obs(steps)
        inbox = self.v.root / "inbox"
        files = {p.name: p.read_text(errors="replace") for p in inbox.iterdir() if p.is_file()}
        leaked = sorted(n for n, t in files.items() if SECRET in t)
        tally = self.v.root / "system/staging/sweep-fetched.json"
        return out, leaked, files, (tally.read_text() if tally.exists() else None)

    def check(self, label, steps):
        out, leaked, files, tally = self.go(steps)
        heads = {n: [ln for ln in files[n].splitlines() if ln.startswith(("Meeting:", "Event ID:", "Organiser:"))] for n in leaked}
        self.assertEqual(leaked, [], f"{label}: confidential text written to inbox/ as {leaked} {heads}")


def secret():
    return result_at("09:05", contents=vtt(SECRET))


# ── N1: the original 32 ──
N1_FORMS = {
    "exact": lambda u: u,
    "upper-case path": lambda u: u.replace("b64joinurl", "B64JOINURL"),
    "upper-case scheme": lambda u: u.replace("meeting-transcript:", "MEETING-TRANSCRIPT:", 1),
    "trailing slash": lambda u: u.replace("b64joinurl?", "b64joinurl/?"),
    "extra query": lambda u: u + "&x=1",
    "fragment": lambda u: u + "#f",
    "percent-encoded": lambda u: u.replace("b64joinurl", "b64%6Aoinurl"),
    "other window": lambda u: u.replace("T08:00:00Z", "T15:00:00Z").replace("T09:00:00Z", "T15:30:00Z"),
}


class N1(Base):
    pass


for i, (name, fn) in enumerate(N1_FORMS.items()):
    for order in ("AB", "BA"):
        for who in ("A", "B"):
            def t(self, name=name, fn=fn, order=order, who=who):
                a, b = BASE, fn(BASE)
                ea, eb = self.ev("ev-1", a, conf=True), self.ev("ev-2", b)
                steps = [ea, eb] if order == "AB" else [eb, ea]
                self.check(f"N1 {name} | {order} | read {who}", [*steps, (b if who == "B" else a, secret(), False)])
            setattr(N1, f"test_{i}_{order}_{who}", t)


# ── Three: ev-1 confidential, ev-2 and ev-3 normal, every event-read order, every read form ──
THREE = {"ev-1": (BASE, True),
         "ev-2": (BASE.replace("T08:00:00Z", "T15:00:00Z").replace("T09:00:00Z", "T15:30:00Z"), False),   # own window
         "ev-3": (P + "B64JoinUrl/" + WIN + "&tenant=x#f", False)}                                        # case, slash, param


class Three(Base):
    pass


for n, perm in enumerate(itertools.permutations(THREE)):
    for reader in THREE:
        def t(self, perm=perm, reader=reader):
            steps = [self.ev(e, THREE[e][0], THREE[e][1]) for e in perm]
            self.check(f"Three {'>'.join(perm)} | read {reader}'s form", [*steps, (THREE[reader][0], secret(), False)])
        setattr(Three, f"test_{n}_{reader}", t)


# ── Spelling: one more way of writing ev-1's meeting in ev-2's event (A = ev-1's form, B = ev-2's form; B is read) ──
def enc(s):
    return "".join(f"%{ord(c):02X}" for c in s)


SPELLINGS = {
    "%2F for the slash": (BASE, BASE.replace("/events/", "/events%2F")),
    "%2f for the slash": (BASE, BASE.replace("/events/", "/events%2f")),
    "%7E for a tilde": (BASE.replace("b64joinurl", "b64~joinurl"), BASE.replace("b64joinurl", "b64%7Ejoinurl")),
    "%7e for a tilde": (BASE.replace("b64joinurl", "b64~joinurl"), BASE.replace("b64joinurl", "b64%7ejoinurl")),
    "every char percent-encoded": (BASE, BASE.replace("b64joinurl", enc("b64joinurl"))),
    "double-encoded letter %256A": (BASE, BASE.replace("b64joinurl", "b64%256Aoinurl")),
    "double-encoded slash %252F": (BASE, BASE.replace("/events/", "/events%252F")),
    "missing netloc (//events/)": (BASE, BASE.replace(":///events/", "://events/")),
    "missing netloc, held side": (BASE.replace(":///events/", "://events/"), BASE),
    "IDNA host xn--": (BASE, BASE.replace(":///events/", "://xn--vnts-9raa/events/")),
    "unicode host": (BASE, BASE.replace(":///events/", "://événts/events/")),
    "userinfo and port in authority": (BASE, BASE.replace(":///events/", "://u:p@h:443/events/")),
    "userinfo and port, path form": (BASE, BASE.replace(":///events/", ":///u:p@h:443/events/")),
    "Kelvin sign K in join id": (BASE.replace("b64joinurl", "kjoinurl"), BASE.replace("b64joinurl", "Kjoinurl")),
    "fullwidth letter in join id": (BASE, BASE.replace("b64joinurl", "ｂ６４joinurl")),
    "backslash path": (BASE, BASE.replace("/events/", "/events\\")),
    "dot segment /./": (BASE, BASE.replace("/events/", "/events/./")),
    "dot-dot segment /x/../": (BASE, BASE.replace("/events/", "/events/x/../")),
    "empty path, both": (P[:-len("events/")] + WIN, P[:-len("events/")] + WIN.replace("08:00", "15:00")),
    "trailing ?": (BASE, BASE.split("?")[0] + "?"),
    "trailing #": (BASE, BASE.split("?")[0] + "#"),
    "space inside": (BASE, BASE.replace("b64joinurl", "b64join url")),
    "%20 vs space": (BASE.replace("b64joinurl", "b64join%20url"), BASE.replace("b64joinurl", "b64join url")),
    "newline inside": (BASE, BASE.replace("b64joinurl", "b64join\nurl")),
    "tab inside": (BASE, BASE.replace("b64joinurl", "b64join\turl")),
    "join id in other case": (BASE, BASE.replace("b64joinurl", "B64JoinURL")),
    "query reordered": (BASE, P + "b64joinurl" + f"?end={DAY}T09:00:00Z&start={DAY}T08:00:00Z"),
    "query keys upper-case": (BASE, BASE.replace("start=", "START=").replace("end=", "END=")),
    "query dropped": (BASE, BASE.split("?")[0]),
    "';' path params": (BASE, BASE.replace("b64joinurl", "b64joinurl;x=1")),
    "base64 padding %3D vs =": (BASE.replace("b64joinurl", "b64joinurl%3D%3D"), BASE.replace("b64joinurl", "b64joinurl==")),
    "base64 padding dropped": (BASE.replace("b64joinurl", "b64joinurl=="), BASE),
    "base64 vs base64url": (BASE.replace("b64joinurl", "b64%2Bjoin%2Furl"), BASE.replace("b64joinurl", "b64-join_url")),
    "%00 appended": (BASE, BASE.replace("b64joinurl", "b64joinurl%00")),
}


class Spelling(Base):
    pass


for i, (name, (a, b)) in enumerate(SPELLINGS.items()):
    for order in ("AB", "BA"):
        def t(self, name=name, a=a, b=b, order=order):
            ea, eb = self.ev("ev-1", a, conf=True), self.ev("ev-2", b)
            steps = [ea, eb] if order == "AB" else [eb, ea]
            self.check(f"Spelling {name} | {order} | read B {b!r}", [*steps, (b, secret(), False)])
        setattr(Spelling, f"test_{i:02d}_{order}", t)


# ── Order: the transcript read comes before the confidential event is read (the sweep reads meeting by meeting) ──
class Order(Base):
    def test_a_ev2_then_its_transcript_then_ev1_same_url(self):
        self.check("Order ev-2, read U, then ev-1 (same U)", [self.ev("ev-2", BASE), (BASE, secret(), False),
                                                                 self.ev("ev-1", BASE, conf=True)])

    def test_b_ev2_then_its_transcript_then_ev1_other_window(self):
        b = BASE.replace("T08:00:00Z", "T15:00:00Z").replace("T09:00:00Z", "T15:30:00Z")
        self.check("Order ev-2 (own window), read it, then ev-1", [self.ev("ev-2", b), (b, secret(), False),
                                                                   self.ev("ev-1", BASE, conf=True)])

    def test_d_ev1_first_control(self):
        self.check("Order control: ev-1 first", [self.ev("ev-1", BASE, conf=True), self.ev("ev-2", BASE), (BASE, secret(), False)])


# drop the inherited Fetch tests
for k in list(vars(F.Fetch)):
    if k.startswith("test_"):
        for _cls in (Base, N1, Three, Spelling, Order):
            setattr(_cls, k, None)
del _cls  # a module-level TestCase name would be collected twice


if __name__ == "__main__":
    unittest.main(verbosity=1)

