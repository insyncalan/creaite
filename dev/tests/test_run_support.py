"""BL-246: the test runner shares the machine fairly: tiers, a machine-wide Chrome cap, and a private temporary folder per
test file that is always removed.

Run: python3 dev/tests/test_run_support.py   (quick tier: starts no Chrome)

Real processes throughout: slot holders are separate Python processes, killed with SIGKILL as a crash would be; the
runner runs real (tiny) test files. Everything happens in temporary folders, never /tmp/creaite-chrome-slots.
"""
import io
import json
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent / "tools"
BASE = Path(tempfile.mkdtemp(prefix="creaite-runbase-"))
os.environ["CREAITE_CHROME_LOCKS"] = str(BASE / "slots")
os.environ["CREAITE_CHROME_CAP"] = "2"
os.environ["CREAITE_RUN_BASE"] = str(BASE / "runs")
(BASE / "runs").mkdir()
sys.path.insert(0, str(TOOLS))
import run_support as support  # noqa: E402
import run_tests  # noqa: E402

HOLDER = f"import sys; sys.path.insert(0, {str(TOOLS)!r}); import run_support as R, time; R.take_slot(); print('took', flush=True); time.sleep(60)"


def holder():
    """A separate process that takes a slot and keeps it for a minute (or until killed)."""
    return subprocess.Popen([sys.executable, "-u", "-c", HOLDER], stdout=subprocess.PIPE, text=True, env=os.environ)


def gone(pid):
    """True when no process has this PID (a zombie counts as gone)."""
    r = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True)
    return r.returncode != 0 or r.stdout.strip().startswith("Z")


class Tiers(unittest.TestCase):
    def test_a_browser_test_is_chrome(self):
        self.assertTrue(support.is_chrome(HERE / "test_work_board.py"))

    def test_taking_data_helpers_from_a_chrome_test_file_stays_quick(self):
        self.assertFalse(support.is_chrome(HERE / "test_reach.py"))         # imports Vault, ABC: no Chrome
        self.assertFalse(support.is_chrome(HERE / "test_tracker.py"))

    def test_a_chrome_helper_imported_inside_a_method_counts(self):
        self.assertTrue(support.is_chrome(HERE / "test_sweep_alerts.py"))   # `from test_insight import chrome` in a method

    def test_this_file_is_quick(self):
        self.assertFalse(support.is_chrome(Path(__file__)))

    def test_both_tiers_are_populated(self):
        files = sorted(HERE.glob("test_*.py"))
        chrome = sum(1 for f in files if support.is_chrome(f))
        self.assertGreater(chrome, len(files) // 2)
        self.assertGreater(len(files) - chrome, 20)


class Slots(unittest.TestCase):
    def setUp(self):
        self.procs = []

    def tearDown(self):
        for p in self.procs:
            p.kill()
            p.wait()

    def start(self):
        p = holder()
        self.procs.append(p)
        return p

    def test_the_cap_holds_across_processes_and_a_killed_holder_frees_its_slot(self):
        a, b = self.start(), self.start()
        self.assertEqual(a.stdout.readline().strip(), "took")
        self.assertEqual(b.stdout.readline().strip(), "took")
        c = self.start()
        self.assertTrue(c.stdout.readline().startswith("(waiting for a Chrome slot"))
        time.sleep(1)
        self.assertIsNone(c.poll())
        t = time.time()
        os.kill(a.pid, signal.SIGKILL)                    # a crash: no clean-up code runs
        self.assertEqual(c.stdout.readline().strip(), "took")
        self.assertLess(time.time() - t, 3)

    def test_a_slot_handed_to_a_test_is_held_until_that_test_ends(self):
        first = self.start()
        first.stdout.readline()
        parent = (f"import sys, subprocess; sys.path.insert(0, {str(TOOLS)!r}); import run_support as R; fd = R.take_slot(); "
                  "c = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(4)'], pass_fds=(fd,), "
                  "stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); print(c.pid)")
        child = int(subprocess.run([sys.executable, "-c", parent], capture_output=True, text=True, env=os.environ).stdout)
        late = self.start()                               # the parent has gone; its child still holds the slot
        self.assertTrue(late.stdout.readline().startswith("(waiting"))
        self.assertEqual(late.stdout.readline().strip(), "took")
        self.assertTrue(gone(child))                      # it got the slot only once the child had ended


class Folders(unittest.TestCase):
    def test_a_files_folder_is_removed_and_its_vaults_counted(self):
        d = support.RunDir()
        try:
            f = d.for_file()
            (f / "creaite-test-probe-1").mkdir()
            (f / "creaite-test-probe-2").mkdir()
            (f / "other").mkdir()
            self.assertEqual(support.RunDir.finish(f), 2)
            self.assertFalse(f.exists())
        finally:
            d.close()
        self.assertFalse(d.root.exists())

    def test_the_folder_of_a_run_that_was_killed_is_removed_by_the_next(self):
        p = subprocess.Popen([sys.executable, "-c", "pass"])
        p.wait()                                          # a PID whose process has ended
        dead = support.RUN_BASE / f"{support.RUN_PREFIX}{p.pid}"
        (dead / "1" / "creaite-test-left").mkdir(parents=True)
        mine = support.RUN_BASE / f"{support.RUN_PREFIX}{os.getpid()}"
        mine.mkdir(exist_ok=True)
        try:
            support.sweep_stale(say=lambda m: None)
            self.assertFalse(dead.exists())
            self.assertTrue(mine.exists())                # a live run's folder is never touched
        finally:
            support.shutil.rmtree(mine, ignore_errors=True)


class Runner(unittest.TestCase):
    def write(self, name, body):
        d = Path(tempfile.mkdtemp(prefix="creaite-probe-tests-", dir=BASE))
        f = d / name
        f.write_text(body, encoding="utf-8")
        return f

    def test_a_test_files_temporary_folders_are_removed_when_it_ends(self):
        f = self.write("test_probe_leaves.py", "import tempfile; tempfile.mkdtemp(prefix='creaite-test-probe-'); "
                                                "print(tempfile.gettempdir())")
        r = run_tests.Runner()
        try:
            _, code, _, out, left = r.run(f, chrome=False)
        finally:
            r.close()
        self.assertEqual(code, 0)
        self.assertEqual(left, 1)
        private = Path(out.strip())
        self.assertTrue(str(private).startswith(str(r.dir.root)))     # its TMPDIR was the runner's folder
        self.assertFalse(private.exists())
        self.assertFalse(r.dir.root.exists())

    def test_stop_ends_the_test_and_everything_it_started(self):
        pidfile = BASE / "child.pid"
        f = self.write("test_probe_hangs.py",
                       "import subprocess, time; c = subprocess.Popen(['sleep', '120']); "
                       f"open({str(pidfile)!r}, 'w').write(str(c.pid)); time.sleep(120)")
        r = run_tests.Runner()
        t = threading.Thread(target=r.run, args=(f, False), daemon=True)
        t.start()
        for _ in range(100):
            if pidfile.exists() and pidfile.read_text():
                break
            time.sleep(0.1)
        child = int(pidfile.read_text())
        r.stop()
        t.join(10)
        r.close()
        self.assertFalse(t.is_alive())
        for _ in range(20):
            if gone(child):
                break
            time.sleep(0.1)
        self.assertTrue(gone(child), "the test's own child (its live server or Chrome) was left running")
        self.assertFalse(r.dir.root.exists())


class FlakeLog(unittest.TestCase):
    """A file that failed under load and passed alone is logged with which tests failed and the end of that output."""

    def test_the_log_names_the_failed_tests_and_keeps_the_error(self):
        out = ("FAIL: test_a (__main__.BuildsTakeTurns.test_a)\nTraceback (most recent call last):\n"
               "AssertionError: 5 not greater than 20\nERROR: test_b (__main__.Other)\n")
        self.assertEqual(run_tests.failed_tests(out), ["BuildsTakeTurns.test_a", "Other.test_b"])   # 3.11+ and older forms
        saved, run_tests.FLAKY = run_tests.FLAKY, BASE / "flaky.jsonl"
        try:
            run_tests.log_flaky("test_probe.py", 12, out)
            entry = json.loads(run_tests.FLAKY.read_text(encoding="utf-8"))
            self.assertEqual(entry["failed"], ["BuildsTakeTurns.test_a", "Other.test_b"])
            self.assertIn("AssertionError: 5 not greater than 20", entry["tail"])
            printed = io.StringIO()
            with redirect_stdout(printed):
                run_tests.flaky_report()
            self.assertIn("last failed: BuildsTakeTurns.test_a, Other.test_b — AssertionError: 5 not greater than 20",
                          printed.getvalue())
        finally:
            run_tests.FLAKY = saved


# ===== BL-247: servers and Chromes end with their test =====
import proc_guard  # noqa: E402

SPAWNER = (f"import sys, subprocess, time; sys.path.insert(0, {str(TOOLS)!r}); import proc_guard; "
           "p = proc_guard.spawn(['sh', '-c', 'sleep 300 & echo $!; wait'], stdout=subprocess.PIPE, text=True); "
           "print(p.pid, p.stdout.readline().strip(), flush=True); time.sleep(300)")


def confined_clean(**kw):
    """support.clean() with the temporary folder pointed at this test's own, so a direct run never sweeps the real one."""
    before = tempfile.tempdir
    tempfile.tempdir = str(BASE / "tmp")
    Path(tempfile.tempdir).mkdir(exist_ok=True)
    try:
        return support.clean(say=lambda m: None, **kw)
    finally:
        tempfile.tempdir = before


def wait_gone(*pids, within=8):
    """True when every PID has gone within `within` seconds."""
    end = time.time() + within
    while time.time() < end:
        if all(gone(p) for p in pids):
            return True
        time.sleep(0.1)
    return False


class Guard(unittest.TestCase):
    def test_stop_ends_the_process_and_what_it_started(self):
        p = proc_guard.spawn(["sh", "-c", "sleep 300 & echo $!; wait"], stdout=subprocess.PIPE, text=True)
        grandchild = int(p.stdout.readline())
        proc_guard.stop(p, grace=2)
        self.assertTrue(wait_gone(p.pid, grandchild))

    def test_a_process_killed_outright_takes_what_it_started_with_it(self):
        parent = subprocess.Popen([sys.executable, "-u", "-c", SPAWNER], stdout=subprocess.PIPE, text=True)
        child, grandchild = (int(x) for x in parent.stdout.readline().split())
        os.kill(parent.pid, signal.SIGKILL)            # no clean-up code runs: only the watchdog is left to act
        parent.wait()
        self.assertTrue(wait_gone(child, grandchild), "the watchdog didn't end the group of a killed parent")

    def test_a_process_that_exits_normally_stops_what_it_left_running(self):
        code = SPAWNER.replace("time.sleep(300)", "pass")      # exits at once without stopping its child: atexit does
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=30).stdout
        child, grandchild = (int(x) for x in out.split())
        self.assertTrue(wait_gone(child, grandchild))


class RunnerEndsWhatTestsStart(unittest.TestCase):
    def write(self, name, body):
        d = Path(tempfile.mkdtemp(prefix="creaite-probe-tests-", dir=BASE))
        (d / name).write_text(body, encoding="utf-8")
        return d / name

    def test_a_leaked_child_holding_the_output_neither_hangs_the_run_nor_survives_it(self):
        pidfile = BASE / "leak.pid"
        f = self.write("test_probe_leak.py", "import subprocess; c = subprocess.Popen(['sleep', '300']); "
                                             f"open({str(pidfile)!r}, 'w').write(str(c.pid)); print('done')")
        r = run_tests.Runner()
        t = time.time()
        try:
            _, code, _, out, _ = r.run(f, chrome=False)
        finally:
            r.close()
        self.assertEqual(code, 0)
        self.assertIn("done", out)
        self.assertLess(time.time() - t, 30)            # not the leaked child's 300 s
        self.assertTrue(wait_gone(int(pidfile.read_text())))

    def test_a_runner_killed_mid_test_leaves_nothing_behind(self):
        pidfile = BASE / "mid.pids"
        probe = self.write("test_probe_mid.py",
                           f"import sys, subprocess, os, time; sys.path.insert(0, {str(TOOLS)!r}); import proc_guard; "
                           "a = subprocess.Popen(['sleep', '300']); "                 # a server started the plain way
                           "b = proc_guard.spawn(['sleep', '300']); "                 # and one through the guard
                           f"open({str(pidfile)!r}, 'w').write(f'{{os.getpid()}} {{a.pid}} {{b.pid}}'); time.sleep(300)")
        driver = (f"import sys; sys.path.insert(0, {str(TOOLS)!r}); from pathlib import Path; import run_tests; "
                  f"r = run_tests.Runner(); print(r.dir.root, flush=True); r.run(Path({str(probe)!r}), chrome=False)")
        runner = subprocess.Popen([sys.executable, "-u", "-c", driver], stdout=subprocess.PIPE, text=True, env=os.environ)
        root = Path(runner.stdout.readline().strip())
        for _ in range(100):
            if pidfile.exists() and len(pidfile.read_text().split()) == 3:
                break
            time.sleep(0.1)
        pids = [int(x) for x in pidfile.read_text().split()]
        os.kill(runner.pid, signal.SIGKILL)             # the runner dies mid-test, with no chance to clean up
        runner.wait()
        self.assertTrue(wait_gone(*pids, within=15), "the test or something it started is still running")
        confined_clean(only=set())                      # the next run's clean-up: the dead runner's folder goes
        self.assertFalse(root.exists())


class Clean(unittest.TestCase):
    def test_an_orphaned_test_server_is_stopped(self):
        (BASE / "tmp").mkdir(exist_ok=True)
        vault = Path(tempfile.mkdtemp(prefix="creaite-test-clean-", dir=BASE / "tmp"))   # where confined_clean looks
        script = vault / "system" / "scripts" / "live_server.py"
        script.parent.mkdir(parents=True)
        script.write_text("import time; time.sleep(300)\n", encoding="utf-8")
        orphaner = (f"import subprocess, sys; p = subprocess.Popen([sys.executable, {str(script)!r}], "   # not our pipe:
                    "start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); print(p.pid)")
        pid = int(subprocess.run([sys.executable, "-c", orphaner], capture_output=True, text=True).stdout)
        for _ in range(50):                             # re-parented to PID 1 once its parent has gone
            if subprocess.run(["ps", "-o", "ppid=", "-p", str(pid)], capture_output=True, text=True).stdout.strip() == "1":
                break
            time.sleep(0.1)
        before = tempfile.tempdir
        tempfile.tempdir = str(BASE / "tmp")
        try:
            self.assertNotIn(pid, [p for p, _ in support.orphans()])    # too young: launch.py detaches servers on purpose
            self.assertIn((pid, "test live server"), support.orphans(age=0))
        finally:
            tempfile.tempdir = before
        stopped, _ = confined_clean(age=0, only={pid})
        self.assertEqual(stopped, 1)
        self.assertTrue(wait_gone(pid))
        support.shutil.rmtree(vault, ignore_errors=True)

    def test_an_old_test_folder_goes_unless_something_is_using_it(self):
        tmp = BASE / "tmp"
        tmp.mkdir(exist_ok=True)
        old, used = tmp / "creaite-test-clean-old", tmp / "creaite-test-clean-used"
        for d in (old, used):
            d.mkdir(exist_ok=True)
            os.utime(d, (time.time() - 7200, time.time() - 7200))
        holder = subprocess.Popen(["sleep", "60"], cwd=used)            # works inside it
        try:
            os.utime(used, (time.time() - 7200, time.time() - 7200))
            confined_clean(only=set())
            self.assertFalse(old.exists())
            self.assertTrue(used.exists())
        finally:
            holder.kill()
            holder.wait()
            support.shutil.rmtree(used, ignore_errors=True)
# ===== end BL-247 =====


def tearDownModule():
    support.shutil.rmtree(BASE, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
