"""#307 path 12: POST /api/review/restore-discarded through a real live server on a throwaway vault, with mutants.

The route is dev/proposals/discard-undo/live_server.py.diff (guarded) and the command it runs is review.py.diff; until this tree has
them each test applies the diffs to the throwaway vault (never to this tree), so the same checks run in both states.
Token 403, Host 403, GET 404, not the open page's own call 403, a bad body 400, the development copy refuses, the job lock is taken
for ten seconds at most, discard then restore round trip (the file is back byte for byte, in words), a second restore says it is gone, a name
already waiting is refused; each guard is removed from a copy of the route and the check for it must go red.

Run: python3 dev/tests/test_discard_undo_routes.py
"""
import json
import os
import re
import socket
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_held_missing_source as hm  # noqa: E402
from test_discard_undo import PROPOSALS, COMMAND_IN_TREE  # noqa: E402
from test_tracker import Vault, make_draft  # noqa: E402

ROUTE_IN_TREE = "/api/review/restore-discarded" in (hm.REPO / "system/scripts/live_server.py").read_text(encoding="utf-8")
PATH = "/api/review/restore-discarded"


def make_vault(mutation=None):
    v = Vault()
    d = v.root
    if not (COMMAND_IN_TREE and ROUTE_IN_TREE):
        subprocess.run(["git", "init", "-q", str(d)], check=True)
        if not COMMAND_IN_TREE:
            subprocess.run(["git", "apply", str(PROPOSALS / "review.py.diff")], cwd=d, check=True)
        if not ROUTE_IN_TREE:
            subprocess.run(["git", "apply", str(PROPOSALS / "live_server.py.diff")], cwd=d, check=True)
    if mutation:
        f = d / "system/scripts/live_server.py"
        text = f.read_text()
        old, new = mutation
        assert old in text, f"mutation target not found: {old[:60]}"
        f.write_text(text.replace(old, new, 1))
    return v


class Server:
    def __init__(self, mutation=None):
        self.now = os.environ.get("CREAITE_NOW")
        os.environ["CREAITE_NOW"] = f"{hm.DAY} 18:00"
        self.v = make_vault(mutation)
        self.root = self.v.root
        self.v.run("init")
        (self.root / ".creaite-dev").unlink(missing_ok=True)
        with socket.socket() as sk:
            sk.bind(("127.0.0.1", 0))
            self.port = sk.getsockname()[1]
        self.base = f"http://127.0.0.1:{self.port}"
        self.proc = subprocess.Popen([sys.executable, str(self.root / "system/scripts/live_server.py")],
                                     env={**os.environ, "CREAITE_PORT": str(self.port)}, stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
        for _ in range(150):
            try:
                urllib.request.urlopen(self.base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        page = urllib.request.urlopen(self.base + "/").read().decode()
        self.token = json.loads(re.search(r'id="data">(.*?)</script>', page, re.S).group(1).replace("<\\/", "</"))["token"]

    def close(self):
        self.proc.terminate()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        self.v.cleanup()
        if self.now is None:
            os.environ.pop("CREAITE_NOW", None)
        else:
            os.environ["CREAITE_NOW"] = self.now

    def post(self, path, body=None, token="good", host=None, page=True, raw=None, method="POST"):
        headers = {"Content-Type": "application/json"}
        if token == "good":
            headers["X-Creaite-Token"] = self.token
        elif token:
            headers["X-Creaite-Token"] = token
        if host:
            headers["Host"] = host
        if page:
            headers["Sec-Fetch-Site"] = "same-origin"
            headers["Origin"] = self.base
        data = raw if raw is not None else json.dumps(body if body is not None else {}).encode()
        req = urllib.request.Request(self.base + path, data=None if method == "GET" else data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            with e:
                try:
                    return e.code, json.loads(e.read() or b"{}")
                except ValueError:
                    return e.code, {}

    def discarded(self):
        """Stage held minutes, discard them through /api/review. (staged path, its bytes before, the discarded path)"""
        (self.root / hm.TRANSCRIPT).write_text(hm.VTT, encoding="utf-8")
        make_draft(self.root / hm.DRAFT)
        f = self.root / "system/staging/drafts/meeting.json"
        f.write_text(json.dumps({"title": hm.TITLE, "date": hm.DAY, "projects": ["ABC"], "transcript": hm.TRANSCRIPT,
                                 "draft": hm.DRAFT, "items": [hm.ITEM]}), encoding="utf-8")
        self.v.run("stage", str(f), script="minutes.py", cwd=self.root)
        (self.root / hm.TRANSCRIPT).unlink()
        prop = sorted((self.root / "system/staging").glob("proposed-*.json"))[-1]
        before = prop.read_bytes()
        code, res = self.post("/api/review", {"file": prop.name, "ref": "meeting", "decision": "discard"})
        assert code == 200 and res["ok"], res
        return prop, before, self.root / "system/staging/discarded" / prop.name


class Checks:
    """Each guard's check, written once: raises AssertionError when the guard doesn't hold. Run against the real route, and against a
    route with that one guard removed (which must fail)."""

    @staticmethod
    def token(s):
        prop, before, aside = s.discarded()
        for tok in (None, "wrong"):
            code, _ = s.post(PATH, {"file": prop.name}, token=tok)
            assert code == 403, (tok, code)
        assert aside.is_file() and not prop.exists()

    @staticmethod
    def host(s):
        prop, before, aside = s.discarded()
        code, _ = s.post(PATH, {"file": prop.name}, host="evil.example")
        assert code == 403, code
        assert aside.is_file() and not prop.exists()

    @staticmethod
    def get_is_404(s):
        code, _ = s.post(PATH, method="GET")
        assert code == 404, code

    @staticmethod
    def page_call(s):
        prop, before, aside = s.discarded()
        code, _ = s.post(PATH, {"file": prop.name}, page=False)         # a good token, but not the open page's own call
        assert code == 403, code
        assert aside.is_file() and not prop.exists()

    @staticmethod
    def bad_body(s):
        prop, before, aside = s.discarded()
        for body in ({}, {"file": 5}, {"file": ""}, {"file": "../proposed-x.json"}, {"file": "discarded/" + prop.name},
                     {"file": "x/../proposed-y.json"}, {"file": "/etc/passwd"}, {"file": "proposed-a..b.json"}):
            code, got = s.post(PATH, body)
            assert code == 400 and not got.get("ok"), (body, code)
        assert aside.is_file() and not prop.exists()

    @staticmethod
    def dev_refuses(s):
        prop, before, aside = s.discarded()
        (s.root / ".creaite-dev").write_text("")
        try:
            code, got = s.post(PATH, {"file": prop.name})
            assert code == 200 and got.get("ok") is False and "development copy" in got["message"], got
            assert aside.is_file() and not prop.exists()
        finally:
            (s.root / ".creaite-dev").unlink(missing_ok=True)

    @staticmethod
    def lock_bounded(s):
        """The job lock is taken, for ten seconds at most, before review.py runs (read from the route's own text)."""
        text = (s.root / "system/scripts/live_server.py").read_text()
        body = text[text.index("def review_restore_discarded_route"):text.index("REVIEW_WORK_ROUTES[\"/api/review/restore-discarded\"]")]
        assert "LOCK.acquire(timeout=10)" in body and body.index("LOCK.acquire(timeout=10)") < body.index('run("review.py"')
        assert "LOCK.release()" in body


class RealRoute(unittest.TestCase):
    def setUp(self):
        self.s = Server()
        self.addCleanup(self.s.close)

    def test_token(self):
        Checks.token(self.s)

    def test_host(self):
        Checks.host(self.s)

    def test_get_is_404(self):
        Checks.get_is_404(self.s)

    def test_only_the_open_pages_own_call(self):
        Checks.page_call(self.s)

    def test_a_bad_body_is_400(self):
        Checks.bad_body(self.s)

    def test_the_development_copy_refuses(self):
        Checks.dev_refuses(self.s)

    def test_the_job_lock_is_taken_for_ten_seconds_at_most(self):
        Checks.lock_bounded(self.s)

    def test_discard_then_restore_round_trip_in_words(self):
        s = self.s
        prop, before, aside = s.discarded()
        code, got = s.post(PATH, {"file": prop.name})
        self.assertEqual((code, got["ok"]), (200, True), got)
        self.assertEqual(got["message"], f"Put back: {hm.TITLE} is waiting in Intake again.")
        self.assertEqual(prop.read_bytes(), before)
        self.assertFalse(aside.exists())
        _, rows = s.post("/api/review", {"file": "x", "ref": "x", "decision": "approve"})                 # the server still answers
        self.assertTrue(any(r["ref"] == "meeting" for r in json.loads(s.v.run("list", "--json", script="review.py", cwd=s.root).stdout)))
        code, again = s.post(PATH, {"file": prop.name})                                                   # nothing left to put back
        self.assertFalse(again["ok"])
        self.assertIn("isn't among the ones set aside", again["message"])
        self.assertNotRegex(again["message"], r"Traceback|\.py|system/")

    def test_a_name_already_waiting_is_refused_and_nothing_moves(self):
        s = self.s
        prop, before, aside = s.discarded()
        prop.write_text("{}", encoding="utf-8")
        code, got = s.post(PATH, {"file": prop.name})
        self.assertFalse(got["ok"])
        self.assertIn("already waiting in Intake", got["message"])
        self.assertEqual(prop.read_text(encoding="utf-8"), "{}")
        self.assertTrue(aside.is_file())


# (name, text in the route, replacement, the check that must then fail)
MUTANTS = [
    ("page_call removed", "    if not page_call(handler):\n        return handler.send(403, {\"ok\": False, \"message\": \"Not allowed\"})\n    name = req.get(\"file\")",
     "    name = req.get(\"file\")", "page_call"),
    ("name check removed", "    if not isinstance(name, str) or not RESTORE_NAME.fullmatch(name) or \"..\" in name:",
     "    if not isinstance(name, str):", "bad_body"),
    ("development refusal removed", "    if (paths.ROOT / \".creaite-dev\").exists():\n        return handler.send(200, {\"ok\": False, \"message\": \"This is the development copy",
     "    if False:\n        return handler.send(200, {\"ok\": False, \"message\": \"This is the development copy", "dev_refuses"),
    ("job lock waited for without end", "so nothing was put back.\"})\n    if not LOCK.acquire(timeout=10):",
     "so nothing was put back.\"})\n    if not LOCK.acquire():", "lock_bounded"),
]


class Mutants(unittest.TestCase):
    def test_each_guard_has_a_check_that_catches_its_removal(self):
        for name, old, new, check in MUTANTS:
            s = Server(mutation=(old, new))
            try:
                with self.assertRaises(AssertionError, msg=f"mutant survived: {name}"):
                    getattr(Checks, check)(s)
            finally:
                s.close()

    def test_the_token_and_host_checks_are_the_servers_own(self):
        """do_POST's token and Host checks come before any route; the route can't lose them (token and host checks above run on it)."""
        text = (hm.REPO / "system/scripts/live_server.py").read_text(encoding="utf-8")
        self.assertIn("if not self.authorised():", text[text.index("def do_POST"):][:600])


if __name__ == "__main__":
    unittest.main()
