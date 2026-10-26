"""#375 E1, slice S3: tests for `system/scripts/calendar_gateway.py` (the one read path for calendar.json).

Run: python3 dev/tests/test_calendar_gateway.py      (quick tier: plain code)

invite_filter is built by another slice, so the tests inject a tiny stand-in through `calendar_gateway.FILTER` (drops a line with a
URL or a run of 7+ digits) and a stand-in for the short fields through `SHORT`. Fictional data only.
Mutants (each must turn a test red): stamp ignored (every row filtered / every row trusted), a read that writes, cache key without the
mtime, a view that leaks the body for `day`, an unknown purpose that does not raise.
"""
import json
import os
import re
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parents[1] / "system" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import calendar_gateway as G  # noqa: E402

LINK = "Join: https://meet.example.test/j/123456789?pwd=Zx81"


def stand_in(text):
    keep = [ln for ln in text.split("\n") if not re.search(r"https?://|\d{7,}", ln)]
    return "\n".join(keep)


def short_stand_in(row):
    return {k: row[k] for k in ("id", "start", "end", "all_day", "title", "where", "teams", "private", "organiser", "sensitivity",
                                "organiser_email", "recurrence", "attendees", "attachments") if k in row}


def ev(i="e1", body=None, **kw):
    row = {"id": i, "start": "10:00", "end": "11:00", "all_day": False, "title": "Budget review", "where": "Room 204", "teams": True,
           "private": False, "organiser": "Mia Hale", "sensitivity": "normal", "organiser_email": "mia.hale@example.test",
           "recurrence": "weekly", "body": body if body is not None else f"Agenda: budget\n{LINK}\nRisks and plan",
           "attendees": [{"name": "Omar Reyes", "email": "omar@example.test", "type": "required", "response": "accepted"}],
           "attachments": ["budget.xlsx"]}
    row.update(kw)
    return row


class Base(unittest.TestCase):
    def setUp(self):
        self._f, self._s = G.FILTER, G.SHORT
        G.FILTER, G.SHORT = stand_in, short_stand_in
        G.clear_cache()
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "calendar.json"

    def tearDown(self):
        G.FILTER, G.SHORT = self._f, self._s
        G.clear_cache()
        self.tmp.cleanup()

    def save(self, days, **top):
        self.path.write_text(json.dumps({"fetched": "2026-10-26T07:00", "to": "2026-11-01", "days": days, **top}), encoding="utf-8")


class Purposes(Base):
    def setUp(self):
        super().setUp()
        self.save({"2026-10-26": [ev(clean=1)]})

    def test_closed_set(self):
        self.assertEqual(set(G.purpose_names()), {"meta", "day", "intake", "prep_rank", "prep_panel", "prep_page", "agenda", "shape"})

    def test_unknown_purpose_raises_not_oserror_or_valueerror(self):
        for p in ("bogus", "", None, "DAY"):
            with self.assertRaises(G.UnknownPurpose):
                G.read(p, self.path)
            with self.assertRaises(G.UnknownPurpose):
                G.view(ev(), p)
        self.assertFalse(issubclass(G.UnknownPurpose, (OSError, ValueError)))

    def test_shape_of_read(self):
        cal = G.read("day", self.path)
        self.assertEqual(set(cal), {"fetched", "to", "days"})
        self.assertEqual(cal["fetched"], "2026-10-26T07:00")

    def test_meta_has_ids_only(self):
        row = G.read("meta", self.path)["days"]["2026-10-26"][0]
        self.assertEqual(row, {"id": "e1"})

    def test_day_has_no_body_or_attachments(self):
        row = G.read("day", self.path)["days"]["2026-10-26"][0]
        self.assertNotIn("body", row)
        self.assertNotIn("attachments", row)
        self.assertNotIn("organiser_email", row)
        self.assertEqual(row["attendees"], [{"name": "Omar Reyes", "type": "required", "response": "accepted"}])
        self.assertEqual(row["title"], "Budget review")
        self.assertEqual(row["recurrence"], "weekly")

    def test_fields_per_purpose(self):
        expect = {
            "prep_rank": ({"body", "attachments", "attendees"}, {"organiser_email"}),
            "prep_panel": ({"body", "attachments", "attendees", "organiser_email"}, set()),
            "prep_page": ({"body", "attachments"}, {"organiser_email"}),
            "agenda": ({"body", "where"}, {"attachments", "organiser_email"}),
            "shape": ({"body"}, {"attachments", "attendees", "where", "organiser", "organiser_email", "recurrence", "teams"}),
        }
        for purpose, (has, hasnt) in expect.items():
            row = G.read(purpose, self.path)["days"]["2026-10-26"][0]
            for k in has:
                self.assertIn(k, row, (purpose, k))
            for k in hasnt:
                self.assertNotIn(k, row, (purpose, k))

    def test_only_the_readers_that_match_or_write_to_people_get_an_address(self):
        """The follow-up email's To list (agenda), Intake's and Prep's project match by email domain (intake, prep_panel) need the
        attendees' addresses, as the 2.6.8 read gave them; every other purpose gives name, type and response only."""
        who = {"name": "Omar Reyes", "email": "omar@client.example", "type": "required", "response": "accepted"}
        e = ev(clean=1, attendees=[who])
        for purpose in G.purpose_names():
            got = G.view(e, purpose).get("attendees")
            if purpose in ("agenda", "intake", "prep_panel"):
                self.assertEqual(got, [who], purpose)
            elif got is not None:
                self.assertNotIn("email", got[0], purpose)
        for sens in ("private", "confidential"):
            for purpose in G.purpose_names():
                self.assertNotIn("@", json.dumps(G.view({**e, "sensitivity": sens}, purpose)), (sens, purpose))

    def test_view_returns_new_objects(self):
        e = ev(clean=1)
        v = G.view(e, "prep_panel")
        v["attachments"].append("x")
        v["attendees"][0]["name"] = "changed"
        self.assertEqual(e["attachments"], ["budget.xlsx"])
        self.assertEqual(e["attendees"][0]["name"], "Omar Reyes")

    def test_body_length_whole_lines(self):
        body = "\n".join(f"Line {i:03d} " + "x" * 40 for i in range(100))
        for purpose, limit in (("prep_rank", 1500), ("agenda", 1500), ("shape", 600)):
            out = G.view(ev(body=body), purpose)["body"]
            self.assertLessEqual(len(out), limit, purpose)
            self.assertTrue(set(out.split("\n")) <= set(body.split("\n")), purpose)       # whole lines, unedited
            self.assertEqual(out.split("\n"), body.split("\n")[:len(out.split("\n"))])    # in order, a prefix
        self.assertGreater(len(G.view(ev(body=body), "prep_page")["body"]), 1000)

    def test_a_line_over_the_cap_ends_the_body(self):
        out = G.view(ev(body="short\n" + "y" * 700 + "\nafter"), "shape")["body"]
        self.assertEqual(out, "short")

    def test_confidential_and_private_keep_only_the_head(self):
        for kw, title in ((dict(sensitivity="confidential"), "Budget review"), (dict(private=True), "Busy"),
                          (dict(sensitivity="strange"), "Budget review"), (dict(sensitivity="Personal"), "Busy")):
            for purpose in ("day", "prep_panel", "agenda", "shape"):
                row = G.view(ev(**kw), purpose)
                for k in ("body", "attachments", "attendees", "organiser_email", "where", "recurrence"):
                    self.assertNotIn(k, row, (kw, purpose, k))
                self.assertEqual(row["title"], title)
                self.assertNotEqual(row["sensitivity"], "normal")


class Stamp(Base):
    def test_clean_row_filters_and_stamps(self):
        out = G.clean_row(ev())
        self.assertEqual(out["clean"], G.CLEAN)
        self.assertNotIn("meet.example.test", out["body"])
        self.assertIn("Risks and plan", out["body"])
        self.assertEqual(G.clean_row(out), out)                                         # a cleaned row cleans to itself

    def test_clean_row_keeps_only_row_keys(self):
        out = G.clean_row({**ev(), "joinUrl": "https://x.test/j/1", "description": "d"})
        self.assertEqual(set(out) - set(G.ROW_KEYS), {"clean"})

    def test_clean_row_confidential_has_no_body(self):
        out = G.clean_row(ev(sensitivity="confidential"))
        self.assertNotIn("body", out)
        self.assertEqual(out["clean"], G.CLEAN)

    def test_stamp_row_leaves_a_stamped_row(self):
        row = ev(clean=G.CLEAN)
        self.assertEqual(G.stamp_row(row), row)
        self.assertIsNot(G.stamp_row(row), row)

    def test_stamp_rows_and_calendar(self):
        days = {"2026-10-26": [ev("a"), ev("b", clean=1), "junk"], "2026-10-27": "junk"}
        out = G.stamp_rows(days)
        self.assertEqual(list(out), ["2026-10-26"])
        self.assertTrue(all(r["clean"] == G.CLEAN for r in out["2026-10-26"]))
        self.assertEqual(len(out["2026-10-26"]), 2)
        cal = G.stamp_calendar({"fetched": "f", "to": "t", "days": days, "junk": 1})
        self.assertEqual(cal["clean"], G.CLEAN)
        self.assertEqual(set(cal), {"fetched", "to", "days", "clean"})

    def test_bool_and_low_stamps_do_not_count(self):
        for bad in (True, 0, "1", None, -1):
            self.assertFalse(G.is_stamped({"clean": bad}), bad)
        self.assertTrue(G.is_stamped({"clean": G.CLEAN}))
        self.assertTrue(G.is_stamped({"clean": G.CLEAN + 1}))

    def test_lock_is_taken_and_released(self):
        old, G.LOCK = G.LOCK, Path(self.tmp.name) / "cal.lock"
        try:
            with G.lock(1) as got:
                self.assertTrue(got)
                with G.lock(0.1) as again:
                    self.assertFalse(again)
            with G.lock(1) as got:
                self.assertTrue(got)
        finally:
            G.LOCK = old


class InMemoryFilter(Base):
    def test_unstamped_row_is_filtered_on_read(self):
        self.save({"2026-10-26": [ev()]})
        body = G.read("prep_panel", self.path)["days"]["2026-10-26"][0]["body"]
        self.assertNotIn("meet.example.test", body)
        self.assertNotIn("123456789", body)
        self.assertEqual(body, "Agenda: budget\nRisks and plan")

    def test_stamped_row_is_served_as_stored(self):
        stored = f"Agenda: budget\n{LINK}"                       # the stand-in would drop the second line: it must not run
        self.save({"2026-10-26": [ev(body=stored, clean=1)]})
        self.assertEqual(G.read("prep_panel", self.path)["days"]["2026-10-26"][0]["body"], stored)

    def test_mixed_rows(self):
        self.save({"2026-10-26": [ev("a"), ev("b", body=f"kept\n{LINK}", clean=1)], "2026-10-27": [ev("c", clean=0)]})
        cal = G.read("agenda", self.path)["days"]
        self.assertNotIn("meet.example", cal["2026-10-26"][0]["body"])
        self.assertIn("meet.example", cal["2026-10-26"][1]["body"])
        self.assertNotIn("meet.example", cal["2026-10-27"][0]["body"])

    def test_no_write_on_read(self):
        self.save({"2026-10-26": [ev(), ev("b", clean=1)]})
        before_bytes, st = self.path.read_bytes(), self.path.stat()
        old = time.time() - 5000
        os.utime(self.path, (old, old))
        st = self.path.stat()
        for purpose in G.purpose_names():
            G.read(purpose, self.path)
        after = self.path.stat()
        self.assertEqual(self.path.read_bytes(), before_bytes)
        self.assertEqual((after.st_mtime_ns, after.st_ino, after.st_size), (st.st_mtime_ns, st.st_ino, st.st_size))
        self.assertEqual(sorted(p.name for p in self.path.parent.iterdir()), ["calendar.json"])      # no temp, no lock file

    def test_unstamped_secret_in_a_short_field_goes_through_short_hook(self):
        G.SHORT = lambda row: {**short_stand_in(row), "title": "Meeting"}
        self.save({"2026-10-26": [ev(title="Pin 4417 call")]})
        self.assertEqual(G.read("day", self.path)["days"]["2026-10-26"][0]["title"], "Meeting")

    def test_filter_missing_or_failing_serves_no_body(self):
        self.save({"2026-10-26": [ev()]})
        def boom(_t):
            raise RuntimeError("x")
        for fn in (boom, lambda t: None, lambda t: 5):
            G.FILTER = fn
            G.clear_cache()
            row = G.read("prep_panel", self.path)["days"]["2026-10-26"][0]
            self.assertNotIn("body", row)
            self.assertEqual(row["title"], "Budget review")

    def test_default_filter_missing_serves_no_body(self):
        G.FILTER = None
        if "invite_filter" in sys.modules or (SCRIPTS / "invite_filter.py").exists():
            self.skipTest("invite_filter is built: the lazy default works")
        self.save({"2026-10-26": [ev()]})
        self.assertNotIn("body", G.read("prep_panel", self.path)["days"]["2026-10-26"][0])

    def test_filter_runs_on_a_cut_body(self):
        seen = []
        G.FILTER = lambda t: seen.append(len(t)) or t
        self.save({"2026-10-26": [ev(body="a\n" * 30000)]})
        G.read("agenda", self.path)
        self.assertEqual(seen, [G.BODY_MAX])


class Cache(Base):
    def test_hit_does_not_reread_or_refilter(self):
        calls = []
        G.FILTER = lambda t: calls.append(1) or t
        self.save({"2026-10-26": [ev()]})
        G.read("agenda", self.path)
        G.read("prep_page", self.path)
        G.read("day", self.path)
        self.assertEqual(len(calls), 1)

    def test_change_of_content_misses(self):
        self.save({"2026-10-26": [ev(body="one")]})
        self.assertEqual(G.read("agenda", self.path)["days"]["2026-10-26"][0]["body"], "one")
        self.save({"2026-10-26": [ev(body="two")]})          # same size, new mtime
        os.utime(self.path, ns=(1, self.path.stat().st_mtime_ns + 10))
        self.assertEqual(G.read("agenda", self.path)["days"]["2026-10-26"][0]["body"], "two")

    def test_same_size_same_mtime_new_inode_misses(self):
        self.save({"2026-10-26": [ev(body="one")]})
        st = self.path.stat()
        G.read("agenda", self.path)
        other = self.path.with_name("other.json")
        other.write_text(self.path.read_text().replace("one", "two"), encoding="utf-8")
        os.utime(other, ns=(st.st_atime_ns, st.st_mtime_ns))
        os.replace(other, self.path)
        self.assertEqual(G.read("agenda", self.path)["days"]["2026-10-26"][0]["body"], "two")

    def test_filter_swap_misses(self):
        self.save({"2026-10-26": [ev(body="a\nb")]})
        self.assertEqual(G.read("agenda", self.path)["days"]["2026-10-26"][0]["body"], "a\nb")
        G.FILTER = lambda t: "only"
        self.assertEqual(G.read("agenda", self.path)["days"]["2026-10-26"][0]["body"], "only")

    def test_results_are_independent_copies(self):
        self.save({"2026-10-26": [ev(clean=1)]})
        a = G.read("prep_panel", self.path)
        a["days"]["2026-10-26"][0]["attachments"].append("x")
        a["days"]["2026-10-26"].clear()
        b = G.read("prep_panel", self.path)
        self.assertEqual(b["days"]["2026-10-26"][0]["attachments"], ["budget.xlsx"])

    def test_file_changed_while_reading_is_not_cached(self):
        self.save({"2026-10-26": [ev(body="one")]})
        real = Path.read_text
        state = {"n": 0}

        def racing(p, *a, **k):
            text = real(p, *a, **k)
            if p == self.path and state["n"] == 0:
                state["n"] = 1
                self.save({"2026-10-26": [ev(body="two")]})
                os.utime(self.path, ns=(1, self.path.stat().st_mtime_ns + 99))
            return text
        Path.read_text = racing
        try:
            first = G.read("agenda", self.path)
        finally:
            Path.read_text = real
        self.assertEqual(first["days"]["2026-10-26"][0]["body"], "one")
        self.assertEqual(G.read("agenda", self.path)["days"]["2026-10-26"][0]["body"], "two")


class Files(Base):
    def test_missing_file_raises_oserror(self):
        with self.assertRaises(OSError):
            G.read("day", self.path)

    def test_corrupt_file_raises_valueerror(self):
        for text in ("{not json", "", "\x00\x01"):
            self.path.write_text(text, encoding="utf-8")
            G.clear_cache()
            with self.assertRaises(ValueError):
                G.read("day", self.path)

    def test_odd_shapes_give_the_same_shape(self):
        for data in ([], "x", 5, None, {"days": []}, {"days": "x"}, {"days": {"bad": [ev()], "2026-10-26": "x", "2026-10-27": ["s", 1, None]}},
                     {"fetched": 5, "to": None, "days": {}}):
            self.path.write_text(json.dumps(data), encoding="utf-8")
            G.clear_cache()
            cal = G.read("day", self.path)
            self.assertIsInstance(cal["days"], dict)
            self.assertNotIn("bad", cal["days"])
            self.assertTrue(all(isinstance(r, list) for r in cal["days"].values()))
            self.assertTrue(all(isinstance(cal.get(k, ""), str) for k in ("fetched", "to")))

    def test_default_path_is_paths_calendar(self):
        import paths
        old = paths.CALENDAR
        paths.CALENDAR = self.path
        try:
            self.save({"2026-10-26": [ev(clean=1)]})
            self.assertEqual(G.read("meta")["days"]["2026-10-26"], [{"id": "e1"}])
        finally:
            paths.CALENDAR = old

    def test_matches_read_calendar_shape(self):
        import invite_clean
        self.save({"2026-10-26": [ev(body="Agenda: budget")]})
        mine, theirs = G.read("prep_panel", self.path), invite_clean.read_calendar(self.path)
        self.assertEqual(set(mine), set(theirs))
        self.assertEqual(list(mine["days"]), list(theirs["days"]))
        for k, v in mine["days"]["2026-10-26"][0].items():
            if k != "attendees":
                self.assertEqual(v, theirs["days"]["2026-10-26"][0][k], k)


class Timing(Base):
    def test_a_large_calendar_reads_fast_and_hits_the_cache(self):
        days = {f"2026-11-{d:02d}": [ev(f"e{d}-{i}", body="Agenda line\n" * 50) for i in range(8)] for d in range(1, 29)}
        self.save(days)
        t0 = time.perf_counter()
        G.read("agenda", self.path)
        cold = time.perf_counter() - t0
        t0 = time.perf_counter()
        for _ in range(20):
            G.read("day", self.path)
        warm = (time.perf_counter() - t0) / 20
        self.assertLess(cold, 5.0)
        self.assertLess(warm, 1.0)

    def test_hostile_body_is_cut_before_the_filter(self):
        self.save({"2026-10-26": [ev(body="x " * 2_000_000)]})
        t0 = time.perf_counter()
        G.read("agenda", self.path)
        self.assertLess(time.perf_counter() - t0, 5.0)


class Mutants(Base):
    """Each mutation of the module must be caught by the tests above (checked here by running the contract against a patched copy)."""

    def run_with(self, patch, check):
        saved = {k: getattr(G, k) for k in patch}
        for k, v in patch.items():
            setattr(G, k, v)
        G.clear_cache()
        try:
            return check()
        finally:
            for k, v in saved.items():
                setattr(G, k, v)
            G.clear_cache()

    def test_trusting_every_row_is_seen(self):
        self.save({"2026-10-26": [ev()]})
        leaked = self.run_with({"is_stamped": lambda r: True},
                               lambda: "meet.example" in G.read("agenda", self.path)["days"]["2026-10-26"][0]["body"])
        self.assertTrue(leaked)                                 # the mutant leaks, so test_unstamped_row_is_filtered_on_read would fail

    def test_filtering_every_row_is_seen(self):
        self.save({"2026-10-26": [ev(body=f"kept\n{LINK}", clean=1)]})
        changed = self.run_with({"is_stamped": lambda r: False},
                                lambda: "meet.example" not in G.read("agenda", self.path)["days"]["2026-10-26"][0]["body"])
        self.assertTrue(changed)                                # so test_stamped_row_is_served_as_stored would fail

    def test_view_without_the_field_limit_is_seen(self):
        wide = {k: v for k, v in G.PURPOSES.items()}
        wide["day"] = wide["agenda"]
        row = self.run_with({"PURPOSES": wide}, lambda: G.view(ev(clean=1), "day"))
        self.assertIn("body", row)                              # so test_day_has_no_body_or_attachments would fail

    def test_a_cache_without_the_mtime_is_seen(self):
        self.save({"2026-10-26": [ev(body="one")]})
        G.read("agenda", self.path)
        key = str(self.path)
        sig, cal = G._CACHE[key]
        G._CACHE[key] = ((0, sig[1], sig[2], *sig[3:]), cal)
        self.save({"2026-10-26": [ev(body="two")]})
        self.assertEqual(G.read("agenda", self.path)["days"]["2026-10-26"][0]["body"], "two")

    def test_a_reading_gateway_that_writes_would_change_bytes(self):
        # the no-write test compares bytes, mtime and the folder listing; a mutant that rewrites trips all three
        self.save({"2026-10-26": [ev()]})
        before = self.path.read_bytes()
        self.path.write_text(json.dumps(G.stamp_calendar(json.loads(before))), encoding="utf-8")
        self.assertNotEqual(self.path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
