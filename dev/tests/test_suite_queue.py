"""Dev speed: dev/tools/suite_queue.py makes big test runs on one machine take turns. Plain flock files in a throwaway folder; no Chrome.

Run: python3 dev/tests/test_suite_queue.py   (quick tier)
"""
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tools"))
import suite_queue as q  # noqa: E402


@unittest.skipIf(q.fcntl is None, "no flock on this platform")
class Queue(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="queue-")
        self.held = []
        self.addCleanup(lambda: [t.release() for t in self.held])

    def join(self):
        t = q.take_ticket(self.d)
        self.held.append(t)
        return t

    def test_first_run_goes_at_once(self):
        t = q.wait_turn(1, wait=1, folder=self.d, poll=0.05, say=lambda m: None)
        self.held.append(t)
        self.assertIsNotNone(t)

    def test_second_run_waits_for_the_first_then_goes(self):
        first = self.join()
        mine = self.join()
        self.assertEqual(q.ahead(Path(self.d) / "creaite-suite-queue", mine.path), [first.path])
        first.release()
        self.assertEqual(q.ahead(Path(self.d) / "creaite-suite-queue", mine.path), [])

    def test_a_dead_runs_ticket_is_ignored_and_removed(self):
        folder = q.queue_folder(self.d)
        stale = folder / "00000000000000000001-99999"
        stale.write_text("99999 gone")
        mine = self.join()
        self.assertEqual(q.ahead(folder, mine.path), [])
        self.assertFalse(stale.exists())

    def test_timeout_names_the_runs_ahead(self):
        self.join()
        with self.assertRaises(TimeoutError):
            q.wait_turn(1, wait=0.3, folder=self.d, poll=0.05, say=lambda m: None)

    def test_two_at_once_allowed_when_n_is_two(self):
        self.join()
        t = q.wait_turn(2, wait=1, folder=self.d, poll=0.05, say=lambda m: None)
        self.held.append(t)
        self.assertIsNotNone(t)

    def test_waiters_go_in_arrival_order_across_processes(self):
        code = ("import sys,time;sys.path.insert(0,%r);import suite_queue as q;"
                "t=q.wait_turn(1,folder=%r,poll=0.05,say=lambda m:None);print(time.time(),flush=True);time.sleep(0.3)"
                % (str(HERE.parent / "tools"), self.d))
        procs = []
        for _ in range(3):
            procs.append(subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True))
            time.sleep(0.15)
        starts = [float(p.communicate(timeout=30)[0]) for p in procs]
        self.assertEqual(starts, sorted(starts))
        self.assertGreater(starts[2] - starts[0], 0.5)       # they ran one after another

    def test_off_in_ci_and_when_zero(self):
        self.assertEqual(q.runs_allowed({"CI": "1"}), 0)
        self.assertEqual(q.runs_allowed({"CREAITE_SUITE_RUNS": "off"}), 0)
        self.assertEqual(q.runs_allowed({}), 1)
        self.assertEqual(q.runs_allowed({"CREAITE_SUITE_RUNS": "2"}), 2)

    def test_small_runs_never_queue(self):
        self.assertEqual(q.min_files({}), 60)
        self.assertEqual(q.min_files({"CREAITE_QUEUE_MIN_FILES": "5"}), 5)


if __name__ == "__main__":
    unittest.main()
