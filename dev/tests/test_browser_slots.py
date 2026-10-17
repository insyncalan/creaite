"""#89: dev/tools/browser_slots.py limits how many test processes drive Chrome at once on one machine. No Chrome here: the
slots are plain flock files in a throwaway folder.

Run: python3 dev/tests/test_browser_slots.py   (quick tier)
"""
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tools"))
import browser_slots as bs  # noqa: E402


@unittest.skipIf(bs.fcntl is None, "no flock on this platform")
class Slots(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="slots-")
        self.held = []
        self.addCleanup(lambda: [s.release() for s in self.held])

    def take(self, n, wait=0.4):
        s = bs.acquire(n, wait=wait, folder=self.d, poll=0.05)
        self.held.append(s)
        return s

    def test_one_slot_serialises(self):
        a = self.take(1)
        with self.assertRaises(TimeoutError) as cm:
            self.take(1, wait=0.3)
        msg = str(cm.exception)
        self.assertIn("creaite-browser-slot-1.lock", msg)       # names the slot file…
        self.assertIn(f"by pid {os.getpid()}", msg)             # …and who holds it
        a.release()
        self.take(1)                                            # free again once released

    def test_two_slots_allow_two_holders(self):
        a, b = self.take(2), self.take(2)
        self.assertNotEqual(a.path, b.path)
        with self.assertRaises(TimeoutError):
            self.take(2, wait=0.3)

    def test_a_waiter_gets_the_slot_when_it_frees(self):
        a = self.take(1)
        threading.Timer(0.3, a.release).start()
        t = time.time()
        self.take(1, wait=5)
        self.assertGreaterEqual(time.time() - t, 0.2)

    def test_a_crashed_holder_lets_go(self):
        code = ("import sys; sys.path.insert(0, %r); import browser_slots as b; b.acquire(1, folder=%r); "
                "import os; os._exit(1)" % (str(HERE.parent / "tools"), self.d))
        subprocess.run([sys.executable, "-c", code], check=False)
        self.take(1)                                            # the process died holding it; the system released it

    def test_the_switches(self):
        self.assertEqual(bs.slot_count({}), 2)
        self.assertEqual(bs.slot_count({"CREAITE_BROWSER_SLOTS": "5"}), 5)
        for off in ("0", "off", "OFF"):
            self.assertEqual(bs.slot_count({"CREAITE_BROWSER_SLOTS": off}), 0)
        self.assertEqual(bs.slot_count({"CI": "true"}), 0)
        self.assertEqual(bs.slot_count({"GITHUB_ACTIONS": "true"}), 0)
        self.assertEqual(bs.slot_count({"CREAITE_BROWSER_SLOTS": "junk"}), 2)


if __name__ == "__main__":
    unittest.main()
