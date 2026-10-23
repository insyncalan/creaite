"""2.6.2 (#314): POST /api/review with `expect` on a real live server over a throwaway vault.

The route passes the item's fingerprint to review.py (`--expect`), which checks it on the file it reads for the decision. The guarded
diffs (dev/proposals/review-expect/review.py.diff and live_server.diff) are applied to the throwaway copy when this tree lacks them, so the
same checks pass either way. Cases: a match decides that item only; a mismatch (item taken out, so the ref names another item: Cap's c55)
decides nothing and says why in plain words; a malformed `expect` is refused; no `expect` behaves as before. An OLD server (review.py's
diff but not the route's) ignores `expect`: documented, unchanged behaviour. Mutant: the pass-through removed -> the mismatch check goes red.

Run: python3 dev/tests/test_review_expect_routes.py
"""
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system/scripts"))
from test_tracker import Vault  # noqa: E402
import build_dashboard  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DIFFS = ROOT / "dev/proposals/review-expect"
HAS_REVIEW = "_main_with_expect" in (ROOT / "system/scripts/review.py").read_text()
HAS_ROUTE = '"--expect=' in (ROOT / "system/scripts/live_server.py").read_text() or "--expect={expect}" in (ROOT / "system/scripts/live_server.py").read_text()


def item(n, text):
    return {"n": n, "op": "new", "table": "actions", "match": "strong", "flags": [], "decision": "pending",
            "values": {"project": "ABC", "description": text, "owner": "Alan Carter", "due_date": "2027-01-15",
                       "source": "projects/ABC Example/minutes/2026-10-01 Steering.docx — Actions"}}


class Server:
    def __init__(self, route=True, mutate=False):
        self.home = Path(tempfile.mkdtemp(prefix="creaite-re262-")).resolve()
        self.v = Vault()
        d = self.v.root
        todo = [f for f, have in (("review.py.diff", HAS_REVIEW), ("live_server.diff", HAS_ROUTE)) if not have and (route or f == "review.py.diff")]
        if todo:
            subprocess.run(["git", "init", "-q", str(d)], check=True)
            for f in todo:
                subprocess.run(["git", "apply", str(DIFFS / f)], cwd=d, check=True)
        if HAS_ROUTE and not route:                    # this tree has the route's diff: the copy goes back to the old route
            subprocess.run(["git", "init", "-q", str(d)], check=True)
            subprocess.run(["git", "apply", "-R", str(DIFFS / "live_server.diff")], cwd=d, check=True)
        if mutate:
            f = d / "system/scripts/live_server.py"
            t = f.read_text()
            old = "return args + guard"
            assert old in t
            f.write_text(t.replace(old, "return args", 1))
        self.v.run("init")
        (d / ".creaite-dev").unlink(missing_ok=True)
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        self.base = f"http://127.0.0.1:{self.port}"
        env = {**os.environ, "HOME": str(self.home), "CREAITE_PORT": str(self.port), "CREAITE_NO_LAUNCHCTL": "1"}
        self.proc = subprocess.Popen([sys.executable, str(d / "system/scripts/live_server.py")], env=env,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(150):
            try:
                urllib.request.urlopen(self.base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        html = urllib.request.urlopen(self.base + "/").read().decode()
        self.token = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]
        self.n = 0

    def close(self):
        self.proc.terminate()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        self.v.cleanup()
        shutil.rmtree(self.home, ignore_errors=True)

    def stage(self):
        self.n += 1
        return self.v.propose(f"2026-10-21-09{self.n:02d}-r", [item(1, "Alpha item"), item(2, "Bravo item"), item(3, "Charlie item")]).name

    def fp(self, name, ref):
        data = json.loads((self.v.root / "system/staging" / name).read_text())
        return build_dashboard.item_fp(next(i for i in data["items"] if i["n"] == ref))

    def decisions(self, name):
        data = json.loads((self.v.root / "system/staging" / name).read_text())
        return {i["n"]: i["decision"] for i in data["items"]}

    def take_out(self, name, text):
        p = self.v.root / "system/staging" / name
        data = json.loads(p.read_text())
        data["items"] = [i for i in data["items"] if i["values"]["description"] != text]
        for k, it in enumerate(data["items"], 1):
            it["n"] = k
        p.write_text(json.dumps(data))

    def review(self, **body):
        req = urllib.request.Request(self.base + "/api/review", data=json.dumps(body).encode(), method="POST", headers={
            "Content-Type": "application/json", "X-Creaite-Token": self.token, "Sec-Fetch-Site": "same-origin", "Origin": self.base})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            with e:
                return json.loads(e.read() or b"{}")


class Checks:
    @staticmethod
    def match(s):
        name = s.stage()
        r = s.review(file=name, ref=2, decision="approved", modes=[], expect=s.fp(name, 2))
        assert r.get("ok") is True, r
        assert s.decisions(name) == {1: "pending", 2: "approved", 3: "pending"}, s.decisions(name)

    @staticmethod
    def mismatch(s):
        name = s.stage()
        bravo = s.fp(name, 2)
        s.take_out(name, "Alpha item")                 # Bravo is item 1 now; ref 2 is Charlie
        r = s.review(file=name, ref=2, decision="rejected", modes=[], expect=bravo)
        assert r.get("ok") is False, r
        assert "has changed since you looked at it" in r.get("message", ""), r
        assert "Traceback" not in r["message"] and "/" not in r["message"], r
        assert s.decisions(name) == {1: "pending", 2: "pending"}, s.decisions(name)

    @staticmethod
    def malformed(s):
        name = s.stage()
        for bad in ("Bravo item", "ABCDEF123456", "", 7, ["a" * 12]):
            r = s.review(file=name, ref=2, decision="approved", modes=[], expect=bad)
            assert r.get("ok") is False, (bad, r)
            assert "can't check which item" in r.get("message", ""), (bad, r)         # Cap's note 6: it says what is wrong, not "a decision Review knows"
        assert s.decisions(name) == {1: "pending", 2: "pending", 3: "pending"}

    @staticmethod
    def without(s):
        name = s.stage()
        r = s.review(file=name, ref=3, decision="rejected", modes=[])
        assert r.get("ok") is True, r
        assert s.decisions(name) == {1: "pending", 2: "pending", 3: "rejected"}


class Routes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = Server()

    @classmethod
    def tearDownClass(cls):
        cls.s.close()

    def test_a_match_decides_that_item_only(self):
        Checks.match(self.s)

    def test_a_mismatch_decides_nothing(self):
        Checks.mismatch(self.s)

    def test_a_malformed_expect_is_refused(self):
        Checks.malformed(self.s)

    def test_no_expect_behaves_as_before(self):
        Checks.without(self.s)


class OldServer(unittest.TestCase):
    """The engine has --expect but the route does not pass it: `expect` is ignored, the call behaves as it always did."""

    def test_expect_is_ignored(self):
        s = Server(route=False)
        try:
            name = s.stage()
            s.take_out(name, "Alpha item")
            r = s.review(file=name, ref=2, decision="rejected", modes=[], expect=s.fp(name, 1))
            self.assertTrue(r.get("ok"), r)                           # the old route acts on ref 2 (Charlie): why 2.6.2 ships both
            self.assertEqual(s.decisions(name)[2], "rejected")
        finally:
            s.close()


class Mutant(unittest.TestCase):
    def test_without_the_pass_through_the_mismatch_check_goes_red(self):
        s = Server(mutate=True)
        try:
            with self.assertRaises(AssertionError):
                Checks.mismatch(s)
        finally:
            s.close()


if __name__ == "__main__":
    unittest.main(verbosity=1)
