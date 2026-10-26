"""#250: Cap's hostile cases for the confidential-transcript hold, as tests, and a mutant for each rule added to close them.

Run: python3 dev/tests/test_hostile_250.py      (about 25 s: the cases run in three processes at once)

- CASES: the 125-case script (dev/tests/fixtures/hostile_250_final.py, the source of the cases) and the 13 end-to-end cases
  (dev/tests/fixtures/hostile_250_e2e.py) must pass. Fictional data; Microsoft 365 is never called.
- MUTANTS: each rule that closes a case is removed in turn from a throwaway vault's copy of transcripts.py or transcript_hold.py, and the
  case that rule closes must fail.
"""
import io
import subprocess
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIX = HERE / "fixtures"
sys.path.insert(0, str(FIX))
sys.path.insert(0, str(HERE))
import hostile_250_e2e as E  # noqa: E402
import hostile_250_final as H  # noqa: E402
from test_fetch_transcripts import result_at  # noqa: E402

GROUPS = [(FIX / "hostile_250_final.py", ["Spelling"]), (FIX / "hostile_250_final.py", ["N1", "Three"]),
          (FIX / "hostile_250_final.py", ["Order", "Hidden"]), (FIX / "hostile_250_e2e.py", [])]


def run_group(group):
    script, names = group
    r = subprocess.run([sys.executable, str(script), *names], capture_output=True, text=True)
    return script.name, names, r.returncode, "\n".join(r.stderr.strip().splitlines()[-25:])


class Cases(unittest.TestCase):
    def test_all_cases_pass(self):
        with ThreadPoolExecutor(len(GROUPS)) as pool:
            results = list(pool.map(run_group, GROUPS))
        bad = [f"{n} {names}: exit {code}\n{tail}" for n, names, code, tail in results if code != 0]
        self.assertEqual(bad, [], "\n\n".join(bad))


# ── mutants ──
def mutated(cls, method, script, old, new, also=()):
    """Run one case of the fixture in a vault whose copy of `script` has `old` replaced by `new` (and each of `also`, a list of
    (script, old, new): the other rules that would close the same case, switched off so this one is tested alone); True when the case failed."""
    class M(cls):
        def setUp(self):
            super().setUp()
            for sc, a, b in [(script, old, new), *also]:
                p = self.v.root / "system" / "scripts" / sc
                text = p.read_text(encoding="utf-8")
                assert a in text, f"{sc}: pattern not found: {a!r}"
                p.write_text(text.replace(a, b, 1), encoding="utf-8")
    res = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(M(method))
    return not res.wasSuccessful()


class Series(H.Base):
    """Three events name one meeting (ev-1 confidential, so its key is blocked), ev-2 and ev-3 at different times: which one a
    transcript belongs to is decided only by when it was made."""
    def calendar_fix(self):
        import json
        cal = self.v.root / "system/staging/calendar.json"
        c = json.loads(cal.read_text())
        for e in c["days"][H.DAY]:
            if e["id"] == "ev-3":
                e.update(start="15:20", end="16:00")
            if e["id"] == "ev-2":
                e.update(start="15:00", end="15:30")
        cal.write_text(json.dumps(c))

    def run_two_normal(self, made):
        """ev-2 15:00-15:30 and ev-3 15:20-16:00 (both normal) and the confidential ev-1: a transcript made at `made`."""
        self.calendar_fix()
        w2 = H.BASE.replace("T08:00:00Z", "T15:00:00Z").replace("T09:00:00Z", "T15:30:00Z")
        w3 = H.BASE.replace("T08:00:00Z", "T15:20:00Z").replace("T09:00:00Z", "T16:00:00Z")
        r = result_at(made, contents=H.vtt(H.LEGIT))
        return self.go([self.ev("ev-1", H.BASE, conf=True), self.ev("ev-2", w2), self.ev("ev-3", w3), (w2, r, False)])

    def test_two_windows_hold(self):
        out, leaked, files, _ = self.run_two_normal("15:25")
        self.assertFalse(any(H.LEGIT in t for t in files.values()), f"a transcript made in two meetings' windows was attributed ({out})")

    def test_one_window_opens(self):
        out, leaked, files, _ = self.run_two_normal("15:00")
        self.assertTrue(any(H.LEGIT in t for t in files.values()), out)

    def test_two_transcripts_in_two_windows_hold(self):
        self.calendar_fix()
        w2 = H.BASE.replace("T08:00:00Z", "T15:00:00Z").replace("T09:00:00Z", "T15:30:00Z")
        w3 = H.BASE.replace("T08:00:00Z", "T15:20:00Z").replace("T09:00:00Z", "T16:00:00Z")
        r = result_at("15:00", contents=H.vtt(H.LEGIT) + H.vtt(H.LEGIT))
        r["transcripts"][1]["createdDateTime"] = f"{H.DAY}T15:50:30Z"
        out, leaked, files, _ = self.go([self.ev("ev-1", H.BASE, conf=True), self.ev("ev-2", w2), self.ev("ev-3", w3), (w2, r, False)])
        self.assertFalse(any(H.LEGIT in t for t in files.values()), f"transcripts made in two different meetings were written ({out})")


for _k in list(vars(H.F.Fetch)):
    if _k.startswith("test_"):
        setattr(Series, _k, None)
del _k


class Mutants(unittest.TestCase):
    SF = "transcripts.py"
    TH = "transcript_hold.py"
    # (name, script, old, new, class, method): removing the rule must make the case fail
    OWN = ("transcript_hold.py", "if not no_time and not _own_window(found, created, tz):", "if False:")      # the other closer of most cases
    NOTIME = ("transcripts.py", 'if not (t or {}).get("created"):', "if False:")
    OVERLAP = ("transcript_hold.py", "if made is not None and made_day == d and s - 15 <= _minutes(made) < e:", "if False:")
    CASES = [
        ("resolve picks nobody (Hidden: case-only join ids)", SF, "        mk = meeting_key(uri)\n        cands =",
         "        return None\n        mk = meeting_key(uri)\n        cands =", H.Hidden, "test_case_only_join_ids"),
        ("resolve picks nobody (Hidden: another occurrence)", SF, "        mk = meeting_key(uri)\n        cands =",
         "        return None\n        mk = meeting_key(uri)\n        cands =", H.Hidden, "test_other_occurrence_of_a_series"),
        ("settle never asks resolve", SF, "if eid is None and self.named:", "if False:", H.Hidden, "test_case_only_join_ids"),
        ("two windows: the first is taken", SF, "if len(hit) != 1 or (inside not in (None, hit[0])):",
         "if not hit or (inside not in (None, hit[0])):", Series, "test_two_windows_hold"),
        ("two transcripts: the last is taken", SF, "if len(hit) != 1 or (inside not in (None, hit[0])):",
         "if len(hit) != 1:", Series, "test_two_transcripts_in_two_windows_hold", [OWN]),
        ("a transcript with no created time is fetched (M1)", SF, 'if not (t or {}).get("created"):', "if False:",
         E.E2E, "test_02_m1_created_missing"),
        ("the saved calendar is read through invite_clean (M3)", TH, "return json.load(f)",
         "import invite_clean; return invite_clean.read_calendar(path or paths.CALENDAR)", E.E2E, "test_08_m3_unstamped", [OWN, OVERLAP]),
        ("a closed all-day row holds nothing (M2)", TH, 'if _verdict(r) != "private":', "if False:", E.E2E, "test_07_m2_all_day"),
        ("the transcript's own day is not compared (H2)", TH, "if d not in (day, made_day) or", "if d != day or",
         E.E2E, "test_06_h2_other_day", [OWN]),
        ("no created time: the event's own times are not compared (tied twin)", TH, "not by_id or no_time)", "not by_id)",
         E.E2E, "test_03_m1_tied_twin_no_created", [OWN, NOTIME]),
        ("created time not tied to the matched meeting's window (H1)", TH,
         "if not no_time and not _own_window(found, created, tz):", "if False:", E.E2E, "test_05_h1_never_saved"),
    ]

    def test_each_mutant_fails_its_case(self):
        with ThreadPoolExecutor(6) as pool:
            ran = list(pool.map(lambda c: (c[0], mutated(c[4], c[5], c[1], c[2], c[3], c[6] if len(c) > 6 else ())), self.CASES))
        self.assertEqual([n for n, failed in ran if not failed], [], "these rules can be removed and the case still passes")

    def test_order_c_needs_one_of_two_rules(self):
        """Order c (the confidential meeting saved but never read) is closed twice: the overlap with the closed meeting and the
        matched meeting's own window. Either alone is enough; both removed leaks."""
        one = ("if made is not None and made_day == d and s - 15 <= _minutes(made) < e:", "if False:")
        two = ("if not no_time and not _own_window(found, created, tz):", "if False:")

        class Both(H.Order):
            def setUp(self):
                super().setUp()
                p = self.v.root / "system/scripts/transcript_hold.py"
                t = p.read_text(encoding="utf-8")
                for a, b in (one, two):
                    assert a in t
                    t = t.replace(a, b, 1)
                p.write_text(t, encoding="utf-8")
        res = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(Both("test_c_ev1_never_read_in_this_run"))
        self.assertFalse(res.wasSuccessful())
        self.assertFalse(mutated(H.Order, "test_c_ev1_never_read_in_this_run", self.TH, *one))
        self.assertFalse(mutated(H.Order, "test_c_ev1_never_read_in_this_run", self.TH, *two))


if __name__ == "__main__":
    unittest.main(verbosity=1)
