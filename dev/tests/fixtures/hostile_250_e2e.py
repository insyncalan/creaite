"""#250: the fetch end to end through the sweep's wired path, one confidential meeting at a time (fictional data; Microsoft 365 is never called).

Cap's independent review of G3 (26-10-2026) reported 13 cases of which 7 wrote a confidential transcript into inbox/. His harness file was not
posted; these 13 are rebuilt from his description on #250 (slice B's H1, H2, M1, M2, M3, a tied confidential twin matched by ID, the answered
flag) and run SweepFetch with its default calendar rule (transcript_hold), as the live server does. Microsoft 365 is hostile: it hands back the
confidential meeting's text (ev-1, 09:00-10:00) whatever URL is read. A case FAILS when that text reaches inbox/. Imported by
dev/tests/test_hostile_250.py; runnable alone: python3 dev/tests/fixtures/hostile_250_e2e.py
"""
import json
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hostile_250_final as H  # noqa: E402
from test_fetch_transcripts import result_at  # noqa: E402

BASE, SECRET, LEGIT = H.BASE, H.SECRET, H.LEGIT
YESTERDAY = (date.fromisoformat(H.DAY) - timedelta(days=1)).isoformat()


class E2E(H.Base):
    def calendar(self, fn):
        cal = self.v.root / "system/staging/calendar.json"
        c = json.loads(cal.read_text())
        fn(c)
        cal.write_text(json.dumps(c))

    def secret_at(self, hm, day=H.DAY, created=True):
        r = result_at(hm, day=day, contents=H.vtt(SECRET))
        if not created:
            for t in r["transcripts"]:
                t.pop("createdDateTime", None)
        return r

    def ev2(self):
        return self.ev("ev-2", BASE)

    def held(self, label, steps, answered=True):
        out = self.obs(steps, answered=answered)
        files = {p.name: p.read_text(errors="replace") for p in (self.v.root / "inbox").iterdir() if p.is_file()}
        self.assertEqual([n for n, t in files.items() if SECRET in t], [], f"{label}: confidential text written to inbox/ ({out})")
        return out

    # 1  the original order-c HIGH: ev-1 is in the saved calendar only, the run reads ev-2
    def test_01_order_c(self):
        self.held("order c", [self.ev2(), (BASE, self.secret_at("09:05"), False)])

    # 2  M1: no created time
    def test_02_m1_created_missing(self):
        self.held("M1", [self.ev2(), (BASE, self.secret_at("09:05", created=False), False)])

    # 3  M1: a tied confidential twin at the same times and title, N matched by ID, no created time
    def test_03_m1_tied_twin_no_created(self):
        self.calendar(lambda c: [e.update(start="09:00", end="10:00", title="ABC Steering") for e in c["days"][H.DAY] if e["id"] == "ev-2"])
        self.held("tied twin", [self.ev2(), (BASE, self.secret_at("09:05", created=False), False)])

    # 4  tied twin with a created time inside both windows
    def test_04_tied_twin_with_created(self):
        self.calendar(lambda c: [e.update(start="09:00", end="10:00", title="ABC Steering") for e in c["days"][H.DAY] if e["id"] == "ev-2"])
        self.held("tied twin, created", [self.ev2(), (BASE, self.secret_at("09:05"), False)])

    # 5  H1: the confidential meeting was never saved (private events are dropped by default)
    def test_05_h1_never_saved(self):
        self.calendar(lambda c: c["days"].__setitem__(H.DAY, [e for e in c["days"][H.DAY] if e["id"] != "ev-1"]))
        self.held("H1", [self.ev2(), (BASE, self.secret_at("09:05"), False)])

    # 6  H2: the confidential row is on another day (a series lists every occurrence)
    def test_06_h2_other_day(self):
        self.calendar(lambda c: c["days"].__setitem__(YESTERDAY, [{"id": "ev-9", "start": "08:00", "end": "09:00", "all_day": False,
                                                                      "teams": True, "title": "Weekly sync 12", "sensitivity": "confidential"}]))
        self.held("H2", [self.ev2(), (BASE, self.secret_at("08:05", day=YESTERDAY), False)])

    # 7  M2: an all-day confidential row
    def test_07_m2_all_day(self):
        self.calendar(lambda c: c["days"][H.DAY].append({"id": "ev-8", "start": "", "end": "", "all_day": True, "teams": False,
                                                          "title": "Offsite", "sensitivity": "confidential"}))
        self.calendar(lambda c: c["days"].__setitem__(H.DAY, [e for e in c["days"][H.DAY] if e["id"] != "ev-1"]))
        self.held("M2", [self.ev2(), (BASE, self.secret_at("15:05"), False)])

    # 8  M3: the confidential row has no sensitivity key (an older save)
    def test_08_m3_unstamped(self):
        self.calendar(lambda c: [e.pop("sensitivity", None) or e.update(confidential=False) for e in c["days"][H.DAY] if e["id"] == "ev-1"])
        self.held("M3", [self.ev2(), (BASE, self.secret_at("09:05"), False)])

    # 9  the live read says confidential while the saved calendar says normal
    def test_09_live_confidential_saved_normal(self):
        self.calendar(lambda c: [e.update(sensitivity="normal") for e in c["days"][H.DAY]])
        self.held("stale save", [self.ev("ev-2", BASE, conf=True), (BASE, self.secret_at("15:05"), False)])

    # 10 exit 0 with no answer: the server calls finish(answered=False) for a run that ended without its answer; nothing is written
    def test_10_not_answered_writes_nothing(self):
        out = self.held("not answered", [self.ev2(), (BASE, result_at("15:05", contents=H.vtt(LEGIT)), False)], answered=False)
        self.assertFalse(any(LEGIT in p.read_text(errors="replace") for p in (self.v.root / "inbox").iterdir() if p.is_file()), out)

    # 11 control: a normal meeting whose transcript was made inside its own window is fetched
    def test_11_control_fetched(self):
        out, leaked, files, _ = self.go([self.ev2(), (BASE, result_at("15:05", contents=H.vtt(LEGIT)), False)])
        self.assertEqual(out, {"ev-2": "fetched"})
        self.assertTrue(any(LEGIT in t for t in files.values()))

    # 12 control: the same, the confidential row never saved at all and nothing overlaps
    def test_12_control_no_confidential_anywhere(self):
        self.calendar(lambda c: c["days"].__setitem__(H.DAY, [e for e in c["days"][H.DAY] if e["id"] != "ev-1"]))
        out, leaked, files, _ = self.go([self.ev2(), (BASE, result_at("15:05", contents=H.vtt(LEGIT)), False)])
        self.assertEqual(out, {"ev-2": "fetched"})

    # 13 a transcript read of a URL no event of the run named is never fetched
    def test_13_unnamed_url(self):
        self.held("unnamed", [(BASE, self.secret_at("15:05"), False)])


for _k in list(vars(H.F.Fetch)):
    if _k.startswith("test_"):
        setattr(E2E, _k, None)
del _k

if __name__ == "__main__":
    unittest.main(verbosity=1)
