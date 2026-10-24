"""2.6.2 (#314): POST /api/review with `expect` on a real live server over a throwaway vault.

The route passes the item's fingerprint to review.py (`--expect`), which checks it on the file it reads for the decision. The guarded
diffs (dev/proposals/review-expect/review.py.diff and live_server.diff) are applied to the throwaway copy when this tree lacks them, so the
same checks pass either way. 2.6.3 (dev/proposals/expect-mandatory/live_server.diff) makes `expect` mandatory: the same copy is taken to the level a
case needs (0 the old route, 1 the 2.6.2 route where `expect` is optional, 2 mandatory) whatever level this tree is at. Cases: a match decides that item only; a mismatch (item taken out, so the ref names another item: Cap's c55)
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
MANDATORY = ROOT / "dev/proposals/expect-mandatory/live_server.diff"
HAS_REVIEW = "_main_with_expect" in (ROOT / "system/scripts/review.py").read_text()
_LIVE = (ROOT / "system/scripts/live_server.py").read_text()
HAS_ROUTE = '"--expect=' in _LIVE or "--expect={expect}" in _LIVE
HAS_MANDATORY = "Reload the page and try again" in _LIVE
TREE_LEVEL = 2 if HAS_MANDATORY else 1 if HAS_ROUTE else 0
LEVEL_DIFFS = [None, DIFFS / "live_server.diff", MANDATORY]          # LEVEL_DIFFS[n] takes level n-1 to level n


def item(n, text):
    return {"n": n, "op": "new", "table": "actions", "match": "strong", "flags": [], "decision": "pending",
            "values": {"project": "ABC", "description": text, "owner": "Alan Carter", "due_date": "2027-01-15",
                       "source": "projects/ABC Example/minutes/2026-10-01 Steering.docx — Actions"}}


class Server:
    def __init__(self, route=True, mutate=False, level=None):
        level = (1 if not route else TREE_LEVEL or 1) if level is None else level
        self.home = Path(tempfile.mkdtemp(prefix="creaite-re262-")).resolve()
        self.v = Vault()
        d = self.v.root
        level = 0 if not route else level
        subprocess.run(["git", "init", "-q", str(d)], check=True)
        if not HAS_REVIEW:
            subprocess.run(["git", "apply", str(DIFFS / "review.py.diff")], cwd=d, check=True)
        for n in range(TREE_LEVEL + 1, level + 1):                      # up to the wanted level
            subprocess.run(["git", "apply", str(LEVEL_DIFFS[n])], cwd=d, check=True)
        for n in range(TREE_LEVEL, level, -1):                          # or back down, last diff first
            subprocess.run(["git", "apply", "-R", str(LEVEL_DIFFS[n])], cwd=d, check=True)
        if mutate:
            f = d / "system/scripts/live_server.py"
            t = f.read_text()
            old = "return args + guard"
            assert old in t
            f.write_text(t.replace(old, "return args", 1))
        if mutate == "optional":                       # 2.6.3 mutant: the route lets a missing `expect` through again
            f = d / "system/scripts/live_server.py"
            t = f.read_text()
            old = "        if expect is None:\n            return None\n"
            assert old in t
            f.write_text(t.replace(old, "        if expect is None:\n            return []\n", 1))
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
    """The 2.6.2 level (`expect` optional), kept as the record of what 2.6.3 changes."""
    @classmethod
    def setUpClass(cls):
        cls.s = Server(level=1)

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
        Checks.without(self.s)       # the 2.6.2 level: optional


class Mandatory(unittest.TestCase):
    """2.6.3 (dev/proposals/expect-mandatory): a decision without `expect` is refused in plain words, whatever the decision."""

    @classmethod
    def setUpClass(cls):
        cls.s = Server(level=2)

    @classmethod
    def tearDownClass(cls):
        cls.s.close()

    def test_a_match_still_decides_that_item_only(self):
        Checks.match(self.s)

    def test_a_mismatch_still_decides_nothing(self):
        Checks.mismatch(self.s)

    def test_a_malformed_expect_is_still_refused(self):
        Checks.malformed(self.s)

    def test_no_expect_is_refused_for_every_decision_and_nothing_is_decided(self):
        s = self.s
        name = s.stage()
        for decision in ("approved", "rejected", "keep", "override", "discard", "delete"):
            r = s.review(file=name, ref=2, decision=decision, modes=[])
            self.assertFalse(r.get("ok"), (decision, r))
            self.assertIn("didn't say which item it meant", r.get("message", ""), (decision, r))
            self.assertIn("Reload the page", r["message"])
            self.assertNotIn("Traceback", r["message"])
        self.assertEqual(s.decisions(name), {1: "pending", 2: "pending", 3: "pending"})
        r = s.review(file=name, ref=2, decision="approved", modes=[], expect=s.fp(name, 2))      # and the same request with it works
        self.assertTrue(r.get("ok"), r)
        self.assertEqual(s.decisions(name), {1: "pending", 2: "approved", 3: "pending"})

    def test_a_proposal_that_is_gone_still_says_so_first(self):
        r = self.s.review(file="proposed-nope.json", ref=1, decision="approved")
        self.assertIn("no longer pending", r.get("message", ""))


class OldServer(unittest.TestCase):
    """The engine has --expect but the route does not pass it: `expect` is ignored, the call behaves as it always did."""

    def test_expect_is_ignored(self):
        s = Server(level=0)
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
        s = Server(mutate=True, level=2)
        try:
            with self.assertRaises(AssertionError):
                Checks.mismatch(s)
        finally:
            s.close()

    def test_a_route_that_lets_a_missing_expect_through_fails_the_mandatory_check(self):
        s = Server(mutate="optional", level=2)
        try:
            name = s.stage()
            r = s.review(file=name, ref=2, decision="approved", modes=[])
            self.assertTrue(r.get("ok"), "the mutant decides without expect, which Mandatory.test_no_expect_is_refused... would catch")
        finally:
            s.close()


if __name__ == "__main__":
    unittest.main(verbosity=1)
