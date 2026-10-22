"""#241 D: the live server's read route for a work item's history, GET /api/item/history?id=… (item_history.history_of).

The route is in the guarded diff (dev/proposals/work-item-history/live_server.diff), so these tests are expectedFailure until
Jarvis applies it; then they pass and the decorators come off (tests-after.diff).

Run: python3 dev/tests/test_item_history_route.py
"""
import json
import re
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import Vault  # noqa: E402
from test_item_history import seed, upd  # noqa: E402
from test_live_server import free_port  # noqa: E402

NEEDS_DIFF = "needs dev/proposals/work-item-history/live_server.diff (the /api/item/history route)"


class HistoryRoute(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = v = Vault()
        seed(v)
        v.propose("h1", [upd(1, "actions", "ABC-A-001", owner="Omar Ali")], source_run="dashboard", place="peek")
        v.run("apply")
        cls.port = free_port()
        cls.base = f"http://127.0.0.1:{cls.port}"
        env = {**__import__("os").environ, "CREAITE_PORT": str(cls.port), "CREAITE_CLAUDE": "/bin/false"}
        cls.proc = subprocess.Popen([sys.executable, str(v.root / "system/scripts/live_server.py")], env=env,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                urllib.request.urlopen(cls.base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        html = urllib.request.urlopen(cls.base + "/").read().decode()
        cls.token = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)
        cls.v.cleanup()

    def get(self, query, token=True):
        req = urllib.request.Request(self.base + "/api/item/history" + query,
                                     headers={"X-Creaite-Token": self.token} if token else {})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, None

    @unittest.expectedFailure
    def test_the_route_gives_the_items_events(self):
        st, body = self.get("?id=ABC-A-001")
        self.assertEqual(st, 200, NEEDS_DIFF)
        owner = [e for e in body["events"] if e.get("field") == "owner"]
        self.assertEqual([(e["before"], e["after"], e["place"]) for e in owner], [("Alan Carter", "Omar Ali", "peek")])

    @unittest.expectedFailure
    def test_bad_ids_are_refused(self):
        for q in ("", "?id=../tracker.db", "?id=ABC-A-001&id=ABC-A-002"):
            self.assertEqual(self.get(q)[0], 400, (q, NEEDS_DIFF))

    def test_the_token_is_required(self):              # refused with or without the diff: never readable unauthorised
        self.assertIn(self.get("?id=ABC-A-001", token=False)[0], (403, 404))


if __name__ == "__main__":
    unittest.main()
