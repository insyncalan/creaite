"""#250 slice B: the calendar hold (system/scripts/transcript_hold.py).

Run: python3 dev/tests/test_transcript_hold.py      (quick tier: pure code and throwaway files, no Chrome, no Claude)

- FIXTURE: dev/tests/fixtures/transcript_hold_hostile.json, every case: (held, reason) is exactly as written.
- ORDER: the plan's (a) a confidential event read first, (b) read second, (c) never read in the run (saved with teams false): the answer
  is the same in every order and without the live read.
- LIVE: the event read in the run can only add a hold.
- REASONS: only the fixed words; no title, ID or time of a closed meeting in a reason.
- PURE: the inputs are not changed, two calls agree, no file is opened by calendar_hold or same_meeting.
- READER: a missing, empty or corrupt calendar file holds; a good one is read through invite_clean.
- MUTANTS: each rule broken in turn makes the fixture fail.
- TIMING: a 500-row calendar is judged in milliseconds.
All values are made up.
"""
import builtins
import copy
import itertools
import json
import re
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parents[1] / "system" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import transcript_hold as H  # noqa: E402

FIXTURE = json.loads((HERE / "fixtures" / "transcript_hold_hostile.json").read_text(encoding="utf-8"))
SOURCE = (SCRIPTS / "transcript_hold.py").read_text(encoding="utf-8")


def tzinfo(name):
    if not name:
        return None
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(name)
    except Exception:
        return "missing"


def run_case(mod, c):
    tz = tzinfo(c.get("tz"))
    if tz == "missing":
        return None
    return mod.calendar_hold(copy.deepcopy(c["event"]), copy.deepcopy(c["calendar"]), live=copy.deepcopy(c.get("live")),
                             created=c.get("created"), tz=tz)


def failures(mod):
    out = []
    for c in FIXTURE:
        got = run_case(mod, c)
        if got is None:
            continue
        want = (c["held"], c.get("reason", H.NOT_HELD))
        if got != want:
            out.append((c["name"], got, want))
    return out


def mutant(old, new):
    """The module with `old` replaced by `new` in its source (must occur), as a throwaway module."""
    assert old in SOURCE, old
    ns = {"__name__": "transcript_hold_mutant"}
    exec(compile(SOURCE.replace(old, new, 1), "mutant", "exec"), ns)
    return type("M", (), ns)


class Fixture(unittest.TestCase):
    def test_size(self):
        self.assertGreaterEqual(len(FIXTURE), 125)
        self.assertEqual(len({c["name"] for c in FIXTURE}), len(FIXTURE), "names are unique")

    def test_every_case(self):
        self.assertEqual(failures(H), [])

    def test_the_fixture_has_held_and_open_cases(self):
        held = sum(1 for c in FIXTURE if c["held"])
        self.assertGreater(held, 60)
        self.assertGreater(len(FIXTURE) - held, 15)

    def test_reasons_are_the_fixed_words(self):
        for c in FIXTURE:
            got = run_case(H, c)
            if got:
                self.assertIn(got[1], H.REASONS + (H.NOT_HELD,), c["name"])
                self.assertEqual(got[0], got[1] != H.NOT_HELD, c["name"])


class Order(unittest.TestCase):
    """The plan's order cases. Two events of one Teams meeting, one confidential: whichever is judged first, each answer is the same."""
    CAL = {"days": {"2026-10-15": [
        {"id": "evC", "start": "09:00", "end": "10:00", "all_day": False, "title": "Board", "where": "", "teams": False,
         "private": False, "organiser": False, "sensitivity": "confidential"},
        {"id": "evN", "start": "09:00", "end": "10:00", "all_day": False, "title": "Board prep", "where": "", "teams": True,
         "private": False, "organiser": False, "sensitivity": "normal"}]}}
    C = {"id": "evC", "day": "2026-10-15", "start": "09:00", "end": "10:00", "title": "Board"}
    N = {"id": "evN", "day": "2026-10-15", "start": "09:00", "end": "10:00", "title": "Board prep"}

    def judge(self, order, live):
        return {k: H.calendar_hold(e, copy.deepcopy(self.CAL), live=live.get(k)) for k, e in order}

    def test_a_confidential_read_first(self):
        got = self.judge([("C", self.C), ("N", self.N)], {"C": {"sensitivity": "confidential"}, "N": {"sensitivity": "normal"}})
        self.assertEqual(got["C"], (True, "confidential"))
        self.assertEqual(got["N"], (True, "overlaps closed meeting"))     # 250 M1: tied to C at the same times, no created time: held

    def test_b_confidential_read_second(self):
        got = self.judge([("N", self.N), ("C", self.C)], {"C": {"sensitivity": "confidential"}, "N": {"sensitivity": "normal"}})
        self.assertEqual(got["C"], (True, "confidential"))
        self.assertEqual(got["N"], (True, "overlaps closed meeting"))     # 250 M1: tied to C at the same times, no created time: held

    def test_c_confidential_never_read_in_the_run(self):
        """H1: saved with teams false, never read: the saved calendar alone holds it."""
        got = self.judge([("C", self.C), ("N", self.N)], {"N": {"sensitivity": "normal"}})
        self.assertEqual(got["C"], (True, "confidential"))
        self.assertFalse(self.CAL["days"]["2026-10-15"][0]["teams"])

    def test_c_by_id_alone(self):
        self.assertEqual(H.calendar_hold("evC", self.CAL), (True, "confidential"))

    def test_every_order_agrees(self):
        live = {"C": {"sensitivity": "confidential"}, "N": {"sensitivity": "normal"}}
        base = self.judge([("C", self.C), ("N", self.N)], live)
        for order in itertools.permutations([("C", self.C), ("N", self.N)]):
            self.assertEqual(self.judge(list(order), live), base)

    def test_stopped_run_reads_nothing(self):
        """A run that stopped before any read: no live event at all; the saved calendar still holds the confidential one."""
        self.assertEqual(H.calendar_hold(self.C, self.CAL, live=None), (True, "confidential"))
        self.assertEqual(H.calendar_hold(self.N, self.CAL, live=None), (True, "overlaps closed meeting"))

    def test_same_meeting_not_by_title_or_time_alone(self):
        a = {"id": "", "day": "d", "start": "09:00", "end": "10:00", "title": "Board"}
        self.assertTrue(H.same_meeting({**a, "id": "x"}, {**a, "id": "x", "title": "Other", "start": "11:00"}))
        self.assertFalse(H.same_meeting({**a, "id": "x"}, {**a, "id": "y"}))
        self.assertTrue(H.same_meeting(a, dict(a)))
        self.assertFalse(H.same_meeting(a, {**a, "title": "Other"}))
        self.assertFalse(H.same_meeting(a, {**a, "start": "09:30"}))
        self.assertFalse(H.same_meeting(a, {**a, "day": "e"}))
        self.assertFalse(H.same_meeting({**a, "title": ""}, {**a, "title": ""}))
        self.assertFalse(H.same_meeting(None, a))


class Live(unittest.TestCase):
    CAL = Order.CAL

    def test_live_only_adds(self):
        for sens in ("normal", "confidential", "private", None, "", "Normal", 5, "restricted"):
            for ev in (Order.C, Order.N):
                base = H.calendar_hold(ev, self.CAL)
                got = H.calendar_hold(ev, self.CAL, live={"sensitivity": sens})
                if base[0]:
                    self.assertEqual(got, base, (sens, ev["id"]))
                else:
                    opens = isinstance(sens, str) and sens.strip().lower() == "normal"
                    self.assertEqual(got, (False, "normal") if opens else (True, "live event not normal"), (sens,))

    def test_live_normal_never_removes(self):
        for cal in (self.CAL, "corrupt", None, {"days": {}}):
            got = H.calendar_hold(Order.C, cal, live={"sensitivity": "normal"})
            self.assertTrue(got[0])


class Reasons(unittest.TestCase):
    def test_no_title_id_or_time_in_a_reason(self):
        secret = "ZEBRA-QUARTZ-7781"
        cal = {"days": {"2026-10-15": [{"id": secret + "id", "start": "09:17", "end": "10:43", "all_day": False, "title": secret,
                                        "sensitivity": "confidential", "private": False, "teams": False}]}}
        for ev in ({"id": secret + "id"}, {"id": "other", "day": "2026-10-15", "start": "09:17", "end": "10:43", "title": secret},
                   {"id": "x", "day": "2026-10-15", "start": "09:30", "end": "09:40", "title": "Plain"}, secret + "id"):
            held, reason = H.calendar_hold(ev, cal, created="2026-10-15T09:20:00")
            self.assertTrue(held)
            for bit in (secret, "09:17", "10:43", "zebra"):
                self.assertNotIn(bit.lower(), reason.lower())
            self.assertIn(reason, H.REASONS)

    def test_the_module_has_no_logging_or_printing(self):
        self.assertFalse(re.search(r"\b(print|debuglog|logging)\b", SOURCE.replace("`print", "")))


class Pure(unittest.TestCase):
    def test_inputs_unchanged_and_repeatable(self):
        for c in FIXTURE:
            ev, cal, live = copy.deepcopy(c["event"]), copy.deepcopy(c["calendar"]), copy.deepcopy(c.get("live"))
            tz = tzinfo(c.get("tz"))
            if tz == "missing":
                continue
            first = H.calendar_hold(ev, cal, live=live, created=c.get("created"), tz=tz)
            second = H.calendar_hold(ev, cal, live=live, created=c.get("created"), tz=tz)
            self.assertEqual(first, second, c["name"])
            self.assertEqual((ev, cal, live), (c["event"], c["calendar"], c.get("live")), c["name"])

    def test_no_io(self):
        real = builtins.open

        def refuse(*a, **k):
            raise AssertionError("opened a file")
        builtins.open = refuse
        try:
            for c in FIXTURE:
                run_case(H, c)
            H.same_meeting({"id": "a"}, {"id": "a"})
        finally:
            builtins.open = real

    def test_module_imports_nothing_that_reads(self):
        top = re.findall(r"^(?:import|from) (\w+)", SOURCE, re.M)
        self.assertEqual(sorted(set(top)), ["datetime", "re", "unicodedata"])


class Reader(unittest.TestCase):
    def test_files(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "calendar.json"
            self.assertIsNone(H.read_saved_calendar(p))                       # missing
            self.assertEqual(H.calendar_hold("evA", H.read_saved_calendar(p)), (True, "calendar unreadable"))
            for text in ("", "{", "[1,2", "null", "\x00\x01"):
                p.write_text(text, encoding="utf-8")
                self.assertTrue(H.hold_for("evA") is not None)
                self.assertTrue(H.calendar_hold("evA", H.read_saved_calendar(p))[0], text)
            good = {"days": {"2026-10-15": [{"id": "evA", "start": "09:00", "end": "10:00", "all_day": False, "title": "Plan",
                                             "teams": True, "private": False, "organiser": False, "sensitivity": "normal"}]}}
            p.write_text(json.dumps(good), encoding="utf-8")
            self.assertEqual(H.calendar_hold("evA", H.read_saved_calendar(p)), (False, "normal"))
            conf = json.loads(json.dumps(good))
            conf["days"]["2026-10-15"][0].update(sensitivity="Confidential", teams=False, body="x")
            p.write_text(json.dumps(conf), encoding="utf-8")
            self.assertEqual(H.calendar_hold("evA", H.read_saved_calendar(p)), (True, "confidential"))
            conf["days"]["2026-10-15"][0].pop("sensitivity")
            conf["days"]["2026-10-15"][0]["private"] = True
            p.write_text(json.dumps(conf), encoding="utf-8")
            self.assertEqual(H.calendar_hold("evA", H.read_saved_calendar(p)), (True, "private"))
            unstamped = json.loads(json.dumps(good))
            unstamped["days"]["2026-10-15"][0].pop("sensitivity")        # 250 M3: invite_clean would read this row as normal
            p.write_text(json.dumps(unstamped), encoding="utf-8")
            self.assertEqual(H.calendar_hold("evA", H.read_saved_calendar(p)), (True, "unknown sensitivity"))


class Mutants(unittest.TestCase):
    CASES = {
        "only private is closed": ('if v == "normal":', 'if v not in ("private", "personal"):'),
        "missing sensitivity opens": ('if not isinstance(raw, str):\n        return "unknown sensitivity"', 'if not isinstance(raw, str):\n        return NOT_HELD'),
        "private flag ignored": ('if row.get("private") not in (False, None, 0):', 'if False:'),
        "confidential flag ignored": ('if row.get("confidential") not in (False, None, 0):', 'if False:'),
        "live ignored": ('    live_reason = _live_hold(live)', '    live_reason = None'),
        "live can open": ('    if closed:\n        return True, _first(closed)',
                          '    if closed and not (isinstance(live, dict) and live.get("sensitivity") == "normal"):\n        return True, _first(closed)'),
        "title alone matches": ('and keys[0] == keys[1] and all(keys[0])', ''),
        "times alone match": ('return bool(ka) and ka == kb and', 'return keys[0] == keys[1] and all(keys[0]) and'),
        "not saved opens": ('return True, "not in saved calendar"', 'return False, NOT_HELD'),
        "ambiguous opens": ('if lookalike or len(verdicts) > 1:', 'if False:'),
        "look-alike ID ignored": ('return unicodedata.normalize("NFKC", unquote(id_text(value))).casefold().rstrip("=")', 'return id_text(value)'),
        "unreadable opens": ('    if rows is None or bad:', '    if False:'),
        "bad row opens": ('    if rows is None or bad:', '    if rows is None:'),
        "no event opens": ('        return True, "no event"', '        return False, NOT_HELD'),
        "lead time dropped": ('s - 15 <= _minutes(made)', 's <= _minutes(made)'),
        "end included": ('_minutes(made) < e', '_minutes(made) <= e'),
        "overlap ignored": ('if lo is not None and hi is not None and lo < e and s < hi:', 'if False:'),
        "bad created opens": ('        return "times unreadable"\n    day = ev["day"]', '        pass\n    day = ev["day"]'),
        "closed bad times open": ('    if s is None or e is None or e <= s:\n        return "times unreadable"', '    if s is None or e is None or e <= s:\n        return None'),
        "no created time: the event's own times decide (M1)": ('not by_id or no_time)', 'not by_id)'),
        "transcript's own day ignored (H2)": ('if d not in (day, made_day) or', 'if d != day or'),
        "closed all-day row holds nothing (M2)": ('if _verdict(r) != "private":', 'if False:'),
        "private all-day row holds (M2)": ('if _verdict(r) != "private":', 'if True:'),
        "own window skipped (H1)": ('if not no_time and not _own_window(found, created, tz):', 'if False:'),
        "own window: any day (H1)": ('or d != made_day or not (s - 15', 'or not (s - 15'),
        "own window: no lead time": ('not (s - 15 <= _minutes(made) < e)', 'not (s <= _minutes(made) < e)'),
        "own window: end included": ('not (s - 15 <= _minutes(made) < e)', 'not (s - 15 <= _minutes(made) <= e)'),
        "tz ignored": ('stamp = stamp.astimezone(tz) if tz is not None else stamp.astimezone()', 'stamp = stamp.replace(tzinfo=None)'),
        "ID compare loose": ('ids = [(d, r) for d, r in rows if ev["id"] and id_text(r.get("id")) == ev["id"]]',
                             'ids = [(d, r) for d, r in rows if ev["id"] and id_fold(r.get("id")) == id_fold(ev["id"])]'),
        "duplicates both counted": ('distinct[(d, id_text(r.get("id")), str(r.get("start")), str(r.get("end")), title_key(r.get("title")), _verdict(r))] = _verdict(r)',
                                    'distinct[id(r)] = _verdict(r)'),
        "id match checks times": ('not by_id or no_time)', 'True)'),
    }

    def test_each_mutant_fails_the_fixture_or_a_rule(self):
        survivors = []
        for name, (old, new) in self.CASES.items():
            if old not in SOURCE:
                survivors.append(name + " (pattern not found)")
                continue
            try:
                m = mutant(old, new)
                bad = failures(m)
            except Exception:
                bad = ["raised"]
            if not bad:
                survivors.append(name)
        self.assertEqual(survivors, [])

    def test_reader_mutant_fails(self):
        """M3: a reader through invite_clean (which calls a row with no sensitivity normal) is caught by the reader test."""
        old = "return json.load(f)"
        self.assertIn(old, SOURCE)
        m = mutant(old, "import invite_clean; return invite_clean.read_calendar(path or paths.CALENDAR)")
        row = {"id": "evA", "start": "09:00", "end": "10:00", "all_day": False, "title": "Plan", "teams": True, "private": False, "organiser": False}
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "calendar.json"
            p.write_text(json.dumps({"days": {"2026-10-15": [row]}}), encoding="utf-8")
            self.assertEqual(H.calendar_hold("evA", m.read_saved_calendar(p)), (False, "normal"))      # the mutant opens it ...
            self.assertEqual(H.calendar_hold("evA", H.read_saved_calendar(p)), (True, "unknown sensitivity"))     # ... the real reader holds


class Timing(unittest.TestCase):
    def test_large_calendar(self):
        rows = [{"id": f"e{i}", "start": f"{i % 20:02d}:00", "end": f"{i % 20:02d}:30", "all_day": False, "title": f"T{i}",
                 "sensitivity": "confidential" if i % 7 == 0 else "normal", "private": False} for i in range(500)]
        cal = {"days": {"2026-10-15": rows}}
        t = time.perf_counter()
        for i in range(200):
            H.calendar_hold({"id": f"e{i}", "day": "2026-10-15", "start": "09:00", "end": "09:30", "title": "x"}, cal)
        per = (time.perf_counter() - t) / 200
        self.assertLess(per, 0.02, f"{per * 1000:.1f} ms a call")

    def test_hostile_text_is_quick(self):
        evil = "%" * 5000 + "=" * 5000
        t = time.perf_counter()
        H.calendar_hold({"id": evil, "title": evil, "day": "2026-10-15", "start": "09:00", "end": "10:00"}, {"days": {"2026-10-15": [{"id": evil, "title": evil}]}})
        self.assertLess(time.perf_counter() - t, 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=1)
