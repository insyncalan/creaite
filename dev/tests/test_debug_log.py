"""Tests for the debug log (BL-102 part 1): log.py, its setting, the doctor check and the session-start status line.

Run: python3 dev/tests/test_debug_log.py
Each test builds a throwaway vault (as test_tracker.py does) and runs the real log.py in it, with the clock fixed by
CREAITE_NOW, so nothing here touches the repository's own system/logs/.
"""
import json
import os
import shutil
import re
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import REPO, Vault  # noqa: E402

LINE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} (DEBUG|INFO |WARN |ERROR) \S+\s+\S")


class LogCase(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.root = self.v.root
        self.logs = self.root / "system" / "logs"

    def tearDown(self):
        self.v.cleanup()

    def py(self, code, now="2026-10-09 14:32", check=True):
        """Run a snippet in the vault with the clock fixed; it can use `log` and `paths`."""
        pre = f"import sys; sys.path.insert(0, {str(self.root / 'system' / 'scripts')!r}); import log, paths\n"
        env = {**os.environ}
        env.pop("CREAITE_NOW", None)
        if now:
            env["CREAITE_NOW"] = now
        r = subprocess.run([sys.executable, "-c", pre + code], capture_output=True, text=True, env=env,
                           cwd=tempfile.gettempdir())
        if check and r.returncode != 0:
            raise AssertionError(f"snippet failed:\n{r.stdout}\n{r.stderr}")
        return r

    def setting(self, **values):
        cfg = self.root / "system" / "config" / "settings.json"
        data = json.loads(cfg.read_text())
        data.setdefault("logging", {}).update(values)
        cfg.write_text(json.dumps(data, indent=2))

    def day(self, text="2026-10-09"):
        p = self.logs / f"debug-{text}.log"
        return p.read_text(encoding="utf-8").splitlines() if p.exists() else []


class Writing(LogCase):
    def test_an_entry_is_one_line_with_time_level_area_and_message(self):
        self.py("log.info('sweep', 'window 2026-10-02 to 2026-10-09, 41 searched')")
        lines = self.day()
        self.assertEqual(len(lines), 1)
        self.assertTrue(LINE.match(lines[0]), lines[0])
        self.assertTrue(lines[0].startswith("2026-10-09 14:32:00 INFO  sweep "))
        self.assertTrue(lines[0].endswith("window 2026-10-02 to 2026-10-09, 41 searched"))

    def test_newlines_become_spaces_and_a_long_message_is_cut(self):
        self.py("log.info('x', 'one\\ntwo\\r\\nthree'); log.info('x', 'a' * 900)")
        lines = self.day()
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].endswith("one two three"))
        self.assertLessEqual(len(lines[1].split(None, 4)[4]), 500)
        self.assertTrue(lines[1].endswith("…"))

    def test_a_traceback_is_indented_lines_under_its_entry(self):
        self.py("try:\n    1 / 0\nexcept Exception:\n    log.exception('tracker', 'apply failed')")
        lines = self.day()
        self.assertTrue(lines[0].startswith("2026-10-09 14:32:00 ERROR tracker"))
        self.assertIn("apply failed — ZeroDivisionError: division by zero", lines[0])
        self.assertTrue(len(lines) > 1 and all(ln.startswith("    ") for ln in lines[1:]))
        entries = self.py("print(len(log.entries()), log.entries()[0]['detail'][0][:9])").stdout.split()
        self.assertEqual(entries[0], "1")                      # the continuation lines belong to the one entry
        self.assertEqual(entries[1], "Traceback")

    def test_levels(self):
        self.py("log.debug('a', 'd'); log.info('a', 'i'); log.warn('a', 'w'); log.error('a', 'e')")
        self.assertEqual([ln.split()[2] for ln in self.day()], ["INFO", "WARN", "ERROR"])      # debug is hidden
        self.setting(level="debug")
        self.py("log.debug('a', 'd2')", now="2026-10-10 09:00")
        self.assertEqual(len(self.day("2026-10-10")), 1)
        self.setting(level="error")                                                            # not a valid level: info
        self.py("log.debug('a', 'd3'); log.info('a', 'i3'); log.warn('a', 'w3')", now="2026-10-11 09:00")
        self.assertEqual([ln.split()[2] for ln in self.day("2026-10-11")], ["INFO", "WARN"])

    def test_the_run_wrapper_logs_start_duration_exit_and_reraises(self):
        self.py("with log.run('tracker.py', 'apply'):\n    pass")
        self.assertTrue(self.day()[0].endswith("start apply"))
        self.assertRegex(self.day()[1], r"INFO  tracker\s+done in \d+\.\ds")
        r = self.py("with log.run('sweep.py', 'done'):\n    raise ValueError('boom')", now="2026-10-10 09:00", check=False)
        self.assertNotEqual(r.returncode, 0)                                                   # the error is not swallowed
        lines = self.day("2026-10-10")
        self.assertIn("ERROR sweep", lines[1])
        self.assertIn("ValueError: boom", lines[1])
        r = self.py("with log.run('session.py', 'start'):\n    raise SystemExit(3)", now="2026-10-11 09:00", check=False)
        self.assertEqual(r.returncode, 3)
        self.assertRegex(self.day("2026-10-11")[1], r"WARN\s+session\s+exit 3 after")

    def test_two_processes_writing_at_once_lose_no_lines(self):
        code = "for i in range(60): log.info('proc', 'worker %s line %s' % (sys.argv[1], i))"
        pre = f"import sys; sys.path.insert(0, {str(self.root / 'system' / 'scripts')!r}); import log, paths\n"
        env = {**os.environ, "CREAITE_NOW": "2026-10-09 14:32"}
        procs = [subprocess.Popen([sys.executable, "-c", pre + code, str(n)], env=env) for n in range(4)]
        for p in procs:
            self.assertEqual(p.wait(), 0)
        lines = self.day()
        self.assertEqual(len(lines), 240)
        self.assertTrue(all(LINE.match(ln) for ln in lines))
        for n in range(4):
            self.assertEqual(sum(f"worker {n} line" in ln for ln in lines), 60)


class Keeping(LogCase):
    def seed(self, *days):
        self.logs.mkdir(parents=True, exist_ok=True)
        for d in days:
            (self.logs / f"debug-{d}.log").write_text(f"{d} 09:00:00 INFO  old          kept?\n")

    def names(self):
        return sorted(p.name for p in self.logs.glob("debug-*.log"))

    def test_entries_on_different_days_go_to_different_files(self):
        self.py("log.info('a', 'one')", now="2026-10-08 23:59")
        self.py("log.info('a', 'two')", now="2026-10-09 00:01")
        self.assertEqual(self.names(), ["debug-2026-10-08.log", "debug-2026-10-09.log"])

    def test_the_first_entry_of_a_day_deletes_files_older_than_the_last_seven_days(self):
        today = date(2026, 10, 9)
        self.seed(*[(today - timedelta(days=n)).isoformat() for n in (9, 8, 7, 6, 3)])
        self.py("log.info('a', 'first of the day')")
        self.assertEqual(self.names(), ["debug-2026-10-03.log", "debug-2026-10-06.log", "debug-2026-10-09.log"])
        # 7 days old is gone, 6 days old stays: today and the six days before it are the seven kept

    def test_a_later_entry_the_same_day_does_not_scan_or_delete(self):
        self.py("log.info('a', 'first')")
        self.seed("2026-10-01")
        self.py("log.info('a', 'second')")
        self.assertIn("debug-2026-10-01.log", self.names())        # pruning is done when a day's file is created

    def test_prune_does_the_same_on_request(self):
        self.seed("2026-10-01", "2026-10-03", "2026-10-09")
        r = self.py("print(log.prune())")
        self.assertIn("debug-2026-10-01.log", r.stdout)
        self.assertEqual(self.names(), ["debug-2026-10-03.log", "debug-2026-10-09.log"])

    def test_keep_days_is_a_setting(self):
        self.setting(keep_days=2)
        self.seed("2026-10-07", "2026-10-08")
        self.py("log.info('a', 'x')")
        self.assertEqual(self.names(), ["debug-2026-10-08.log", "debug-2026-10-09.log"])

    def test_the_size_cap_stops_a_flood_with_one_notice(self):
        self.setting(max_mb=0.002)                              # about 2 KB
        self.py("for i in range(200): log.info('flood', 'line %s of a loop that must not fill the disk' % i)")
        lines = self.day()
        self.assertEqual(sum("log full for today" in ln for ln in lines), 1)
        self.assertLess(len("\n".join(lines)), 3000)
        self.assertTrue(lines[-1].endswith("later entries are not kept"))
        self.py("log.info('flood', 'tomorrow')", now="2026-10-10 09:00")
        self.assertEqual(len(self.day("2026-10-10")), 1)         # a new day starts again


class NeverRaises(LogCase):
    def test_a_logs_path_that_cannot_be_made_does_not_stop_the_caller(self):
        self.logs.parent.mkdir(parents=True, exist_ok=True)
        self.logs.write_text("a file where the folder should be")
        r = self.py("log.info('a', 'x'); log.error('a', 'y'); log.exception('a', 'z'); log.prune(); "
                    "print(log.files(), log.tail(), log.errors_since(), log.repeated())")
        self.assertEqual(r.stdout.strip(), "[] [] [] []")

    def test_a_read_only_folder_does_not_stop_the_caller(self):
        self.logs.mkdir(parents=True)
        self.logs.chmod(0o500)
        try:
            r = self.py("log.info('a', 'x'); print('carried on')")
            self.assertIn("carried on", r.stdout)
        finally:
            self.logs.chmod(0o700)

    def test_broken_settings_fall_back_to_the_defaults(self):
        (self.root / "system" / "config" / "settings.json").write_text("{ this is not json")
        self.py("log.info('a', 'still written'); log.debug('a', 'hidden')")
        self.assertEqual(len(self.day()), 1)

    def test_a_bad_value_in_the_settings_is_ignored(self):
        self.setting(max_mb="lots", keep_days=None)
        self.py("log.info('a', 'fine')")
        self.assertEqual(len(self.day()), 1)


class Reading(LogCase):
    def test_errors_since_counts_only_errors_inside_the_window(self):
        self.py("log.error('a', 'old one')", now="2026-10-07 09:00")
        self.py("log.error('a', 'yesterday')", now="2026-10-08 20:00")
        self.py("log.warn('a', 'a warning'); log.error('a', 'today')", now="2026-10-09 08:00")
        r = self.py("print(len(log.errors_since(24)), len(log.errors_since(72)))", now="2026-10-09 09:00")
        self.assertEqual(r.stdout.split(), ["2", "3"])

    def test_repeated_groups_errors_that_differ_only_in_numbers(self):
        for n, when in ((4, "2026-10-07 09:00"), (9, "2026-10-08 09:00"), (12, "2026-10-09 09:00")):
            self.py(f"log.error('tracker', 'apply failed for item {n}')", now=when)
        self.py("log.error('sweep', 'one-off')", now="2026-10-09 09:00")
        r = self.py("print(log.repeated(7, 3))", now="2026-10-09 10:00")
        self.assertIn("3, 'tracker', 'apply failed for item 4'", r.stdout)
        self.assertNotIn("sweep", r.stdout)

    def test_tail_returns_the_last_lines_across_days(self):
        self.py("log.info('a', 'one'); log.info('a', 'two')", now="2026-10-08 09:00")
        self.py("log.info('a', 'three')", now="2026-10-09 09:00")
        r = self.py("print([ln.split()[-1] for ln in log.tail(2)])")
        self.assertEqual(r.stdout.strip(), "['two', 'three']")


class DoctorAndSession(LogCase):
    def setUp(self):
        super().setUp()
        self.v.run("init")

    def at(self, when, *args, script):
        r = subprocess.run([sys.executable, str(self.root / "system" / "scripts" / script), *args],
                           env={**os.environ, "CREAITE_NOW": when}, capture_output=True, text=True)
        return r

    def test_doctor_passes_when_the_log_is_writable(self):
        out = self.v.run(script="doctor.py").stdout
        self.assertRegex(out, r"PASS  Debug log — system/logs: writable")

    def test_doctor_warns_but_does_not_fail_on_repeated_errors(self):
        for day in ("2026-10-09",):
            self.py("for i in range(3): log.error('tracker', 'apply failed for item %s' % i)", now=f"{day} 09:00")
        r = self.at("2026-10-09 10:00", script="doctor.py")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertRegex(r.stdout, r"WARN  Debug log — errors that keep coming back: 3 × tracker")

    def test_doctor_fails_when_nothing_can_be_logged(self):
        shutil.rmtree(self.logs, ignore_errors=True)               # tracker.py init (the test's setUp) now writes to it
        self.logs.parent.mkdir(parents=True, exist_ok=True)
        self.logs.write_text("not a folder")
        r = self.v.run(script="doctor.py", ok=False)
        self.assertEqual(r.returncode, 1)
        self.assertRegex(r.stdout, r"FAIL  Debug log — system/logs is not writable")

    def test_doctor_warns_on_a_level_it_does_not_know(self):
        self.setting(level="verbose")
        out = self.v.run(script="doctor.py").stdout
        self.assertRegex(out, r"WARN  Debug log — logging.level \"verbose\"")

    def test_session_start_reports_errors_from_the_last_24_hours_only(self):
        self.py("log.error('a', 'too old')", now="2026-10-07 09:00")
        quiet = self.at("2026-10-09 09:30", "start", "--json", script="session.py")
        self.assertEqual(json.loads(quiet.stdout)["status"]["log_errors"], 0)
        self.assertNotIn("error", self.at("2026-10-09 09:30", "start", script="session.py").stdout.split("Status:")[1])
        self.py("log.error('a', 'one'); log.error('a', 'two')", now="2026-10-09 08:00")
        loud = self.at("2026-10-09 09:30", "start", "--json", script="session.py")
        self.assertEqual(json.loads(loud.stdout)["status"]["log_errors"], 2)
        text = self.at("2026-10-09 09:30", "start", script="session.py").stdout
        self.assertIn("2 errors in the last 24 hours (system/logs/)", text)
        self.py("log.error('a', 'three')", now="2026-10-09 08:30")
        self.assertIn("3 errors in the last 24 hours", self.at("2026-10-09 09:30", "start", script="session.py").stdout)


# ===== BL-252 (fix-small-17): refused commands counted by shape, never their text =====
SAMPLE_REFUSALS = [                                  # (when, message) as live_server.py logs them (BL-140: refused_shape)
    ("2026-10-01 09:00", "r0 refused: tracker.py with a pipe"),                      # eight days old: outside the window
    ("2026-10-08 09:00", "r1 refused: tracker.py with a pipe"),
    ("2026-10-08 10:00", "r2 refused: tracker.py with a pipe, a redirect"),
    ("2026-10-09 08:00", "r3 refused: review.py with a cd … && prefix"),
    ("2026-10-09 08:10", "r4 refused: a command that isn't a creaite script"),
    ("2026-10-09 08:20", "r5 refused: CANARY-COMMAND grep secret | tee CANARY-FILE"),   # not a shape: counted as other, never shown
    ("2026-10-09 08:30", "r6 tool refused: Bash"),                                    # the tools line, not a shape: not counted
]


class Refusals(LogCase):
    def setUp(self):
        super().setUp()
        for when, msg in SAMPLE_REFUSALS:
            self.py(f"log.warn('run', {msg!r})", now=when)
        self.py("log.warn('server', 'x2 refused: tracker.py with a pipe')", now="2026-10-09 08:40")    # another area: not counted

    def test_the_counts_come_from_the_last_seven_days_by_shape(self):
        r = self.py("print(log.refusals(7)); print(log.refusals_line(7))", now="2026-10-09 09:00")
        counts, line = r.stdout.strip().splitlines()
        self.assertEqual(eval(counts), [("a pipe", 2), ("a redirect", 1), ("cd … &&", 1), ("not a creaite script", 1), ("other", 1)])
        self.assertEqual(line, "2 × a pipe, 1 × a redirect, 1 × cd … &&, 1 × not a creaite script, 1 × other")
        self.assertNotIn("CANARY", r.stdout)
        self.assertNotIn("tracker.py", r.stdout)                                     # counts only, not what was run

    def test_no_refusals_reads_none(self):
        self.assertEqual(self.py("print(log.refusals_line(7))", now="2026-10-30 09:00").stdout.strip(), "none")

    def test_doctor_shows_the_counts_without_any_command_text(self):
        # init at the fixed time too: run at today's date it logs a line and prunes the samples' days once they are a week old
        subprocess.run([sys.executable, str(self.root / "system" / "scripts" / "tracker.py"), "init"], check=True,
                       env={**os.environ, "CREAITE_NOW": "2026-10-09 09:00"}, capture_output=True, text=True)
        r = subprocess.run([sys.executable, str(self.root / "system" / "scripts" / "doctor.py")],
                           env={**os.environ, "CREAITE_NOW": "2026-10-09 09:00"}, capture_output=True, text=True)
        self.assertRegex(r.stdout, r"PASS  ask creaite's refused commands — last 7 days: 2 × a pipe, 1 × a redirect, 1 × cd … &&")
        self.assertNotIn("CANARY", r.stdout)
# ===== end BL-252 =====


# ===== BL-263 (fix-doctor-errors): repeated errors carry their times; only a recent repeat warns =====
class RepeatsWithTimes(LogCase):
    def setUp(self):
        super().setUp()
        self.v.run("init")

    def doctor(self, when):
        return subprocess.run([sys.executable, str(self.root / "system" / "scripts" / "doctor.py")],
                              env={**os.environ, "CREAITE_NOW": when}, capture_output=True, text=True)

    def test_an_old_burst_is_stopped_with_its_times_and_a_recent_one_warns(self):
        for t in ("21:20", "22:00", "23:10"):
            self.py("log.error('tracker', 'apply failed for proposed-1.json')", now=f"2026-10-09 {t}")
        self.py("log.error('tracker', 'apply failed for proposed-2.json')", now="2026-10-10 17:02")
        for t in ("09:00", "09:30", "09:45"):
            self.py("log.error('sweep', 'calendar read failed: TimeoutError')", now=f"2026-10-12 {t}")
        r = self.py("import json; print(json.dumps([(g['area'], g['count'], g['live'], log.span(g)) for g in log.repeats()]))",
                    now="2026-10-12 10:00")
        self.assertEqual(json.loads(r.stdout), [["sweep", 3, True, "12-10 09:00 to 12-10 09:45"],
                                                ["tracker", 4, False, "09-10 21:20 to 10-10 17:02"]])
        out = self.doctor("2026-10-12 10:00").stdout
        line = next(ln for ln in out.splitlines() if "Debug log" in ln)
        self.assertRegex(line, r"WARN  Debug log — errors that keep coming back: 3 × sweep: calendar read failed")
        self.assertIn("12-10 09:00 to 12-10 09:45", line)
        self.assertIn("stopped: 4 × tracker: apply failed for proposed-1.json — 09-10 21:20 to 10-10 17:02, none since", line)

    def test_an_old_burst_alone_does_not_warn(self):
        for t in ("21:20", "22:00", "23:10"):
            self.py("log.error('tracker', 'apply failed')", now=f"2026-10-09 {t}")
        line = next(ln for ln in self.doctor("2026-10-12 10:00").stdout.splitlines() if "Debug log" in ln)
        self.assertRegex(line, r"^PASS  Debug log — system/logs: writable")
        self.assertIn("stopped: 3 × tracker: apply failed — 09-10 21:20 to 09-10 23:10, none since", line)

    def test_the_window_is_a_setting(self):
        self.setting(repeat_window_hours=96)
        for t in ("21:20", "22:00", "23:10"):
            self.py("log.error('tracker', 'apply failed')", now=f"2026-10-09 {t}")
        self.assertIn("WARN  Debug log — errors that keep coming back", self.doctor("2026-10-12 10:00").stdout)

    def test_a_long_path_is_not_cut(self):
        path = "projects/_portfolio/people-register-proposals/2026-10-09 a very long staged proposal file name.json"
        msg = f"apply failed: the register proposal at {path} could not be read after the people register changed"
        for t in ("09:00", "09:10", "09:20"):
            self.py(f"log.error('tracker', {msg!r})", now=f"2026-10-12 {t}")
        line = next(ln for ln in self.doctor("2026-10-12 10:00").stdout.splitlines() if "Debug log" in ln)
        short = self.py(f"print(log.short({msg!r}))").stdout.strip()
        self.assertTrue(short.endswith(" …") and len(short) < len(msg), short)
        self.assertIn(short, line)
        for word in short[:-2].split():
            self.assertIn(word, msg.split())                       # every word kept is whole: no path cut in the middle
        self.assertEqual(self.py("print(log.short('projects/_portfolio/' + 'x' * 200))").stdout.strip(),
                         "projects/_portfolio/" + "x" * 200)        # one long path with no space is kept whole


class ClientLeft(LogCase):
    def test_a_connection_reset_is_logged_at_info_not_error(self):
        code = """
import live_server as L
for kind in (BrokenPipeError, ConnectionResetError):
    def boom(self, kind=kind): raise kind()
    L.Handler.do_GET = boom
    L.install_debug_log()
    class H: path = "/api/data"; command = "GET"
    L.Handler.do_GET(H())
"""
        self.setting(level="info")
        self.py(code, now="2026-10-12 10:00")
        text = "\n".join(self.day("2026-10-12"))
        self.assertRegex(text, r"INFO  server\s+GET /api/data client left: BrokenPipeError")
        self.assertRegex(text, r"INFO  server\s+GET /api/data client left: ConnectionResetError")
        self.assertNotIn("ERROR", text)
        self.assertEqual(self.py("print(len(log.repeats(minimum=1)))", now="2026-10-12 10:05").stdout.strip(), "0")
# ===== end BL-263 =====


class UpdateKeepsIt(LogCase):
    def test_an_update_neither_replaces_nor_removes_the_logs(self):
        engine = self.py("print(paths.ENGINE)").stdout
        self.assertNotIn("system/logs", engine)                  # the log is data: only the engine is replaced
        self.assertNotIn("logs", self.py("print([e for e in paths.ENGINE if 'log' in e])").stdout.strip("[]\n "))

    def test_an_update_adds_the_logging_setting_to_an_older_settings_file_and_keeps_its_values(self):
        sys.path.insert(0, str(self.root / "system" / "scripts"))
        import update  # noqa: E402
        incoming = (REPO / "system" / "templates" / "settings-defaults.json").read_text(encoding="utf-8")
        old = json.loads((self.root / "system" / "config" / "settings.json").read_text())
        old.pop("logging", None)
        text, added = update.merged_changes("system/config/settings.json", json.dumps(old), incoming)
        self.assertIn("logging", added)
        self.assertEqual(json.loads(text)["logging"], {"level": "info", "max_mb": 5, "keep_days": 7,
                                                       "repeat_window_hours": 24})    # BL-263: the repeat window
        old["logging"] = {"level": "debug"}                      # Alan's own value survives, new keys are added around it
        text, added = update.merged_changes("system/config/settings.json", json.dumps(old), incoming)
        self.assertEqual(json.loads(text)["logging"]["level"], "debug")
        self.assertEqual(json.loads(text)["logging"]["max_mb"], 5)

    def test_the_logs_are_not_in_git(self):
        self.assertIn("system/logs/*", (REPO / ".gitignore").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
