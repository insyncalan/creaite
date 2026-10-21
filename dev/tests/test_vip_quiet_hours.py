"""#97 step 1: quiet hours for the alert check (the check for messages from the people you follow, BL-342).

vip_schedule.py decides, in plain code, whether the live server's check may run now: not between vip.quiet_from and vip.quiet_to
(19:00 to 07:00) when vip.quiet_overnight is on, and not on the weekend days (work.weekend_days) when vip.quiet_weekend is on. The
first check after quiet time looks back to the last successful check (vip.json's last_check), so nothing is missed.

The unit tests are pure (a table of times). The wiring tests apply dev/proposals/quiet-hours/live_server.diff to a throwaway vault's own
copy of live_server.py (never committed; skipped once the diff is in the repo's live_server.py, which then runs as it is) and run the
real vip_check with a stand-in claude and a pinned clock (CREAITE_NOW). Fictional data only.

Run: python3 dev/tests/test_vip_quiet_hours.py     (quick tier: no Chrome)
"""
import json
import os
import subprocess
import sys
import time
import unittest
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "system" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vip_schedule as vs  # noqa: E402

PROPOSAL = REPO / "dev" / "proposals" / "quiet-hours" / "live_server.diff"


def at(text):
    return datetime.strptime(text, "%Y-%m-%d %H:%M")


def cfg(**vip):
    """A settings dict as settings.json holds it: the vip block given, the weekend Saturday and Sunday."""
    return {"vip": vip, "work": {"weekend_days": ["Saturday", "Sunday"]}}


# 19-10-2026 is a Monday, 23-10 a Friday, 24-10 a Saturday, 25-10 a Sunday.
DEFAULT_TABLE = [
    ("2026-10-20 06:59", True),        # weekday, before 07:00
    ("2026-10-20 07:00", False),       # the window ends at 07:00 exactly
    ("2026-10-20 12:00", False),
    ("2026-10-20 18:59", False),
    ("2026-10-20 19:00", True),        # starts at 19:00 exactly
    ("2026-10-20 23:59", True),
    ("2026-10-21 00:00", True),        # across midnight
    ("2026-10-23 18:59", False),       # Friday afternoon
    ("2026-10-23 19:00", True),
    ("2026-10-24 00:00", True),        # Saturday all day
    ("2026-10-24 12:00", True),
    ("2026-10-24 23:59", True),
    ("2026-10-25 12:00", True),        # Sunday all day
    ("2026-10-26 06:59", True),        # Monday morning, still overnight
    ("2026-10-26 07:00", False),
]


class QuietNow(unittest.TestCase):
    def test_the_defaults_over_a_table_of_times(self):
        for when, quiet in DEFAULT_TABLE:
            with self.subTest(when=when):
                self.assertIs(vs.quiet_now(cfg(), at(when)), quiet)

    def test_settings_written_out_match_the_defaults(self):
        written = cfg(quiet_overnight=True, quiet_from="19:00", quiet_to="07:00", quiet_weekend=True)
        for when, quiet in DEFAULT_TABLE:
            self.assertIs(vs.quiet_now(written, at(when)), quiet, when)

    def test_no_settings_at_all_reads_as_the_defaults(self):
        for s in ({}, {"vip": None}, {"vip": "on"}, {"vip": []}):
            self.assertTrue(vs.quiet_now(s, at("2026-10-20 22:00")), s)
            self.assertFalse(vs.quiet_now(s, at("2026-10-20 10:00")), s)
            self.assertTrue(vs.quiet_now(s, at("2026-10-24 10:00")), s)

    def test_overnight_off_restores_todays_behaviour_on_weekdays(self):
        s = cfg(quiet_overnight=False)
        for when in ("2026-10-20 06:59", "2026-10-20 19:00", "2026-10-20 23:59", "2026-10-21 03:00"):
            self.assertFalse(vs.quiet_now(s, at(when)), when)
        self.assertTrue(vs.quiet_now(s, at("2026-10-24 12:00")))        # the weekend is its own switch

    def test_weekend_off_runs_saturday_and_sunday_in_the_day(self):
        s = cfg(quiet_weekend=False)
        self.assertFalse(vs.quiet_now(s, at("2026-10-24 12:00")))
        self.assertFalse(vs.quiet_now(s, at("2026-10-25 07:00")))
        self.assertTrue(vs.quiet_now(s, at("2026-10-24 21:00")))        # overnight still applies at the weekend

    def test_both_off_is_never_quiet(self):
        s = cfg(quiet_overnight=False, quiet_weekend=False)
        for when, _ in DEFAULT_TABLE:
            self.assertFalse(vs.quiet_now(s, at(when)), when)

    def test_the_weekend_follows_work_weekend_days(self):
        s = {"vip": {}, "work": {"weekend_days": ["Friday", "Saturday"]}}
        self.assertTrue(vs.quiet_now(s, at("2026-10-23 12:00")))         # Friday
        self.assertFalse(vs.quiet_now(s, at("2026-10-25 12:00")))        # Sunday is a working day here

    def test_a_window_inside_one_day(self):
        s = cfg(quiet_from="01:00", quiet_to="05:30")
        self.assertFalse(vs.quiet_now(s, at("2026-10-20 00:59")))
        self.assertTrue(vs.quiet_now(s, at("2026-10-20 01:00")))
        self.assertTrue(vs.quiet_now(s, at("2026-10-20 05:29")))
        self.assertFalse(vs.quiet_now(s, at("2026-10-20 05:30")))
        self.assertFalse(vs.quiet_now(s, at("2026-10-20 22:00")))

    def test_another_window_crossing_midnight(self):
        s = cfg(quiet_from="22:30", quiet_to="06:15")
        self.assertFalse(vs.quiet_now(s, at("2026-10-20 22:29")))
        self.assertTrue(vs.quiet_now(s, at("2026-10-20 22:30")))
        self.assertTrue(vs.quiet_now(s, at("2026-10-21 06:14")))
        self.assertFalse(vs.quiet_now(s, at("2026-10-21 06:15")))

    def test_from_equal_to_to_means_no_overnight_window(self):
        s = cfg(quiet_from="07:00", quiet_to="07:00")
        for when in ("2026-10-20 06:59", "2026-10-20 07:00", "2026-10-20 23:00"):
            self.assertFalse(vs.quiet_now(s, at(when)), when)
        self.assertTrue(vs.quiet_now(s, at("2026-10-24 12:00")))

    def test_invalid_times_fall_back_to_the_defaults(self):
        for bad in ("7pm", "24:00", "19:60", "1900", "", None, 19, "19:00:00", " 19:00x", ["19:00"]):
            s = cfg(quiet_from=bad, quiet_to=bad)
            with self.subTest(bad=bad):
                self.assertTrue(vs.quiet_now(s, at("2026-10-20 19:00")))
                self.assertTrue(vs.quiet_now(s, at("2026-10-20 06:59")))
                self.assertFalse(vs.quiet_now(s, at("2026-10-20 07:00")))
        self.assertEqual(vs.quiet_settings(cfg(quiet_from=" 21:15 "))["from"], 21 * 60 + 15)   # outer spaces are fine

    def test_switches_read_from_hand_edits(self):
        for off in (False, "off", "false", "no", 0):
            self.assertFalse(vs.quiet_now(cfg(quiet_overnight=off), at("2026-10-20 22:00")), off)
        for on in (True, "on", None, "yes", "something odd"):
            self.assertTrue(vs.quiet_now(cfg(quiet_overnight=on), at("2026-10-20 22:00")), on)


class NextDue(unittest.TestCase):
    def test_quiet_ends_at_the_end_of_the_window(self):
        self.assertEqual(vs.quiet_ends(cfg(), at("2026-10-20 19:00")), at("2026-10-21 07:00"))
        self.assertEqual(vs.quiet_ends(cfg(), at("2026-10-21 03:10")), at("2026-10-21 07:00"))
        self.assertIsNone(vs.quiet_ends(cfg(), at("2026-10-21 09:00")))                       # not quiet

    def test_friday_evening_waits_for_monday_morning(self):
        self.assertEqual(vs.quiet_ends(cfg(), at("2026-10-23 19:30")), at("2026-10-26 07:00"))
        self.assertEqual(vs.quiet_ends(cfg(quiet_overnight=False), at("2026-10-24 10:00")), at("2026-10-26 00:00"))

    def test_every_day_a_weekend_day_never_ends(self):
        s = {"vip": {}, "work": {"weekend_days": [0, 1, 2, 3, 4, 5, 6]}}
        self.assertIsNone(vs.quiet_ends(s, at("2026-10-20 10:00")))

    def test_next_due_skips_quiet_time(self):
        self.assertEqual(vs.next_due(cfg(), at("2026-10-20 18:40"), 30), at("2026-10-21 07:00"))
        self.assertEqual(vs.next_due(cfg(), at("2026-10-20 10:00"), 30), at("2026-10-20 10:30"))
        self.assertEqual(vs.next_due(cfg(), at("2026-10-23 18:45"), 30), at("2026-10-26 07:00"))
        self.assertEqual(vs.next_due(cfg(quiet_overnight=False, quiet_weekend=False), at("2026-10-20 18:40"), 30),
                         at("2026-10-20 19:10"))

    def test_the_timer_waits_no_longer_than_its_interval_and_wakes_when_quiet_ends(self):
        # quiet: wake at the end of quiet time (plus a few seconds), never later than the usual interval, held cards ignored
        self.assertEqual(vs.timer_wait(30.0, cfg(), at("2026-10-21 06:50"), interval=1800), 10 * 60 + 5)
        self.assertEqual(vs.timer_wait(30.0, cfg(), at("2026-10-20 22:00"), interval=1800), 1800)
        # not quiet: the wait the server worked out, as it is
        self.assertEqual(vs.timer_wait(42.0, cfg(), at("2026-10-20 10:00"), interval=1800), 42.0)

    def test_the_week_has_108_quiet_hours_by_default(self):
        self.assertEqual(vs.weekly_quiet_hours(cfg()), 108)
        self.assertEqual(vs.weekly_quiet_hours(cfg(quiet_weekend=False)), 84)
        self.assertEqual(vs.weekly_quiet_hours(cfg(quiet_overnight=False)), 48)
        self.assertEqual(vs.weekly_quiet_hours(cfg(quiet_overnight=False, quiet_weekend=False)), 0)

    def test_checks_a_week_at_thirty_minutes(self):
        self.assertEqual(vs.weekly_checks(cfg(), 30), 120)            # 24 a day on five days
        self.assertEqual(vs.weekly_checks(cfg(quiet_overnight=False, quiet_weekend=False), 30), 336)


class LookBack(unittest.TestCase):
    def test_the_look_back_starts_at_the_last_successful_check(self):
        # Friday 18:30 was the last check; the first one after the weekend reads from there, not from now minus 30 minutes
        self.assertEqual(vs.look_back("2026-10-23 18:30", at("2026-10-22 07:00"), at("2026-10-26 07:00")), "2026-10-23 18:30")

    def test_no_check_yet_falls_back_to_the_last_sweep_then_now(self):
        self.assertEqual(vs.look_back(None, at("2026-10-26 06:10"), at("2026-10-26 07:00")), "2026-10-26 06:10")
        self.assertEqual(vs.look_back(None, None, at("2026-10-26 07:00")), "2026-10-26 07:00")


class DaylightSaving(unittest.TestCase):
    """Local wall-clock times decide quiet time; the wait in seconds is the real time between them."""

    def setUp(self):
        if not hasattr(time, "tzset"):
            self.skipTest("no tzset")
        self.old = os.environ.get("TZ")
        os.environ["TZ"] = "Europe/London"
        time.tzset()

    def tearDown(self):
        if self.old is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = self.old
        time.tzset()

    def test_clocks_going_back_add_an_hour_of_real_time(self):
        # UK clocks go back at 02:00 on Sunday 25-10-2026: Saturday 18:00 to Monday 07:00 is 37 wall hours, 38 real ones
        self.assertEqual(vs.seconds_between(at("2026-10-24 18:00"), at("2026-10-26 07:00")), 38 * 3600)
        self.assertEqual(vs.quiet_ends(cfg(), at("2026-10-25 01:30")), at("2026-10-26 07:00"))
        self.assertTrue(vs.quiet_now(cfg(quiet_weekend=False), at("2026-10-25 01:30")))


class SettingsAndCatalogue(unittest.TestCase):
    def test_the_defaults_file_holds_the_four_keys(self):
        d = json.loads((REPO / "system" / "templates" / "settings-defaults.json").read_text())["vip"]
        self.assertEqual({k: d[k] for k in ("quiet_overnight", "quiet_from", "quiet_to", "quiet_weekend")},
                         {"quiet_overnight": True, "quiet_from": "19:00", "quiet_to": "07:00", "quiet_weekend": True})
        self.assertEqual(vs.DEFAULTS, {k: d[k] for k in vs.DEFAULTS})

    def test_the_catalogue_rows_are_essentials_in_people_i_follow(self):
        import settings_catalogue as sc
        for k in ("vip.quiet_overnight", "vip.quiet_from", "vip.quiet_to", "vip.quiet_weekend"):
            self.assertEqual(sc.CATALOGUE[k][0], "People I follow", k)
            self.assertEqual(sc.tier_of(k), sc.ESSENTIALS, k)
        rows = {r[1]: r for r in sc.ESSENTIAL_ROWS}
        self.assertEqual(rows["Pause alert checks overnight"][3], ("vip.quiet_overnight", "vip.quiet_from", "vip.quiet_to"))
        self.assertEqual(rows["Pause alert checks on weekend days"][3], ("vip.quiet_weekend",))
        self.assertTrue(rows["Pause alert checks overnight"][2].startswith("No checks between these times."))
        for r in rows.values():
            self.assertNotRegex(" ".join(r[:3]), r"\bVIP\b")                                    # BL-288


def wired_vault():
    from test_sweep_alerts import check_since, vip_vault
    import shutil
    v = vip_vault()
    shutil.copy2(REPO / "system" / "scripts" / "vip_schedule.py", v.root / "system" / "scripts" / "vip_schedule.py")
    target = v.root / "system" / "scripts" / "live_server.py"
    if "vip_schedule" not in target.read_text(encoding="utf-8"):
        r = subprocess.run(["patch", "--no-backup-if-mismatch", "-p1", "-d", str(v.root), "-i", str(PROPOSAL)],
                           capture_output=True, text=True)
        assert r.returncode == 0 and "vip_schedule" in target.read_text(encoding="utf-8"), r.stdout + r.stderr
    check_since(v, "2026-10-23 18:30")                                        # the last check: Friday 18:30
    return v


FAKE = r"""#!/usr/bin/env python3
import json, sys
from pathlib import Path
here = Path(__file__).parent
with open(here / "calls.txt", "a") as f:
    f.write(sys.argv[-1].replace("\n", " ") + "\n")
print(json.dumps({"type": "result", "subtype": "success", "result": "[]", "total_cost_usd": 0.01, "num_turns": 1}))
"""


class Wiring(unittest.TestCase):
    """The proposal applied to a vault's own copy: no call to claude in quiet time, and the first call after it reads from the
    last check."""

    def setUp(self):
        self.v = wired_vault()
        self.fake = self.v.root / "fake_claude.py"
        self.fake.write_text(FAKE)
        self.fake.chmod(0o755)
        self.calls = self.v.root / "calls.txt"

    def tearDown(self):
        self.v.cleanup()

    def check(self, when):
        code = "import sys; sys.path.insert(0, 'system/scripts'); import live_server; print(live_server.vip_check())"
        r = subprocess.run([sys.executable, "-c", code], cwd=self.v.root, capture_output=True, text=True, timeout=120,
                           env={**os.environ, "CREAITE_CLAUDE": str(self.fake), "CREAITE_NOW": when, "CREAITE_TZ_OFFSET": "+01:00"})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout.strip().splitlines()[-1]

    def last_check(self):
        return json.loads((self.v.root / "system" / "staging" / "vip.json").read_text())["last_check"]

    def test_no_check_in_quiet_time(self):
        for when in ("2026-10-23 19:00", "2026-10-24 12:00", "2026-10-25 23:59", "2026-10-26 06:59"):
            self.assertEqual(self.check(when), "skipped: quiet hours", when)
        self.assertFalse(self.calls.exists())                                 # claude was never started
        self.assertEqual(self.last_check(), "2026-10-23 18:30")              # the look-back is kept

    def test_the_first_check_after_quiet_time_looks_back_to_the_last_check(self):
        self.check("2026-10-24 12:00")
        out = self.check("2026-10-26 07:00")
        self.assertNotIn("skipped", out)
        (prompt,) = self.calls.read_text().splitlines()
        self.assertIn("since 2026-10-23T18:30", prompt)                      # Friday's last check, not 06:30 on Monday
        self.assertEqual(self.last_check(), "2026-10-26 07:00")

    def test_the_settings_off_restore_todays_behaviour(self):
        s = json.loads((self.v.root / "system" / "config" / "settings.json").read_text())
        s.setdefault("vip", {}).update({"quiet_overnight": False, "quiet_weekend": False})
        (self.v.root / "system" / "config" / "settings.json").write_text(json.dumps(s))
        self.assertNotIn("skipped", self.check("2026-10-24 22:00"))
        self.assertEqual(len(self.calls.read_text().splitlines()), 1)

    def test_first_start_after_the_laptop_slept_through_the_weekend(self):
        # the server starts on Monday at 08:15: not quiet, so the start-up check runs and reads from Friday's last check
        code = ("import sys; sys.path.insert(0, 'system/scripts'); import live_server; print(live_server.vip_check('start-up'))")
        r = subprocess.run([sys.executable, "-c", code], cwd=self.v.root, capture_output=True, text=True, timeout=120,
                           env={**os.environ, "CREAITE_CLAUDE": str(self.fake), "CREAITE_NOW": "2026-10-26 08:15",
                                "CREAITE_TZ_OFFSET": "+01:00"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("since 2026-10-23T18:30", self.calls.read_text())

    def test_nothing_the_skip_prints_or_logs_says_vip(self):
        self.assertNotRegex(self.check("2026-10-24 12:00"), r"\bVIP\b")
        logs = self.v.root / "system" / "logs"
        text = "".join(f.read_text() for f in logs.glob("*.log")) if logs.exists() else ""
        self.assertNotIn("quiet", text.lower().replace("quiet_wait", ""))   # a skipped tick writes nothing to the debug log

    def test_the_diff_applies_to_the_repos_live_server(self):
        src = (REPO / "system" / "scripts" / "live_server.py").read_text(encoding="utf-8")
        if "vip_schedule" in src:
            self.skipTest("the diff is in live_server.py")
        r = subprocess.run(["git", "apply", "--check", str(PROPOSAL)], cwd=REPO, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main()
