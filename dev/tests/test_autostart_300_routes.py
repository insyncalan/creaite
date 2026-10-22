"""#300 review: the real routes and the launcher's remove, with mutants.

- LauncherOwnServer: `launch.py agent remove` and `install` with a stub `launchctl` on PATH. Not the agent's own server: the file is
  deleted first, then the job is unloaded. The agent's own server (launchd sets XPC_SERVICE_NAME to the job's label): the file is deleted
  and the job is NOT unloaded (that would stop the server that is answering), and the words say so (review H1).
- Routes: a real live server (throwaway HOME and agent folder, launchctl left alone) with the routes. They exist once the guarded diff
  (dev/proposals/300/live_server.diff) is applied; until then each test applies it to a throwaway copy of the vault (never to this tree),
  so the same checks run in both states. Token 403, Host 403, GET 404, a call that isn't the open page's 403, a non-boolean 400,
  ask creaite's run.json refuses (in progress, marked, unreadable), the development copy refuses, on and off round trip, an agent-started
  server says it keeps running.
- Mutants: each guard is removed from a throwaway copy of the routes, and the check for that guard must go red.

Run: python3 dev/tests/test_autostart_300_routes.py
"""
import json
import os
import re
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import Vault  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PROPOSAL = ROOT / "dev/proposals/300/live_server.diff"


def routes_exist():
    return "/api/autostart/status" in (ROOT / "system/scripts/live_server.py").read_text()


def label_of(vault_root):
    return "app.creaite." + (re.sub(r"[^a-z0-9]+", "-", Path(vault_root).name.lower()).strip("-") or "vault")


class LauncherOwnServer(unittest.TestCase):
    mutate = None                                  # [(old, new)] applied to the throwaway copy's launch.py, by the mutant check

    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.cleanup)
        self.d = self.v.root
        if self.mutate:
            f = self.d / "system/scripts/launch.py"
            text = f.read_text()
            for old, new in self.mutate:
                assert old in text, old
                text = text.replace(old, new, 1)
            f.write_text(text)
        (self.d / ".creaite-dev").unlink(missing_ok=True)
        self.agents = Path(tempfile.mkdtemp(prefix="creaite-300r-agents-"))
        self.bin = Path(tempfile.mkdtemp(prefix="creaite-300r-bin-"))
        self.addCleanup(shutil.rmtree, self.agents, True)
        self.addCleanup(shutil.rmtree, self.bin, True)
        self.log = self.bin / "calls.log"
        stub = self.bin / "launchctl"
        # logs each call and whether this vault's plist was still there when it was made
        stub.write_text('#!/bin/sh\necho "$1 plist=$([ -e "%s/%s.plist" ] && echo there || echo gone)" >> "%s"\nexit 0\n'
                        % (self.agents, label_of(self.d), self.log))
        stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
        self.env = {**os.environ, "CREAITE_AGENT_DIR": str(self.agents), "PATH": f"{self.bin}:{os.environ['PATH']}"}
        self.env.pop("CREAITE_NO_LAUNCHCTL", None)
        self.env.pop("XPC_SERVICE_NAME", None)
        self.plist = self.agents / f"{label_of(self.d)}.plist"

    def launch(self, *a, own=False):
        env = dict(self.env, **({"XPC_SERVICE_NAME": label_of(self.d)} if own else {}))
        return subprocess.run([sys.executable, str(self.d / "system/scripts/launch.py"), *a], cwd=self.d, env=env,
                              capture_output=True, text=True, timeout=60)

    def calls(self):
        return self.log.read_text().splitlines() if self.log.exists() else []

    def test_not_its_own_server_the_file_goes_first_then_the_job_is_unloaded(self):
        self.assertEqual(self.launch("agent", "install").returncode, 0)
        self.assertTrue(self.plist.exists())
        self.log.unlink(missing_ok=True)
        r = self.launch("agent", "remove")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(self.plist.exists())
        boots = [c for c in self.calls() if c.startswith("bootout")]
        self.assertEqual(boots, ["bootout plist=gone"])                       # unloaded, and the file was already gone
        self.assertIn("won't start when you sign in", r.stdout)
        self.assertNotIn("carries on", r.stdout)

    def test_its_own_server_is_never_unloaded_and_the_words_say_it_carries_on(self):
        self.assertEqual(self.launch("agent", "install").returncode, 0)
        self.log.unlink(missing_ok=True)
        r = self.launch("agent", "remove", own=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(self.plist.exists())                                  # the file is gone, so it isn't started at the next sign-in
        self.assertEqual([c for c in self.calls() if c.startswith(("bootout", "bootstrap"))], [])
        self.assertIn("carries on until you stop it", r.stdout)
        self.assertIn("won't start again when you sign in", r.stdout)

    def test_turning_it_on_from_its_own_server_does_not_unload_it_either(self):
        self.assertEqual(self.launch("agent", "install").returncode, 0)
        self.log.unlink(missing_ok=True)
        r = self.launch("agent", "install", own=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(self.plist.exists())
        self.assertEqual([c for c in self.calls() if c.startswith(("bootout", "bootstrap"))], [])
        self.assertIn("carries on", r.stdout)

    def test_state_says_when_this_is_the_agents_own_server(self):
        self.assertEqual(json.loads(self.launch("agent", "status", "--json").stdout)["own"], False)
        self.assertEqual(json.loads(self.launch("agent", "status", "--json", own=True).stdout)["own"], True)

    def test_nothing_to_remove_says_so(self):
        self.assertIn("No login agent", self.launch("agent", "remove").stdout)


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def make_routes_vault(mutation=None):
    """A throwaway vault whose live_server.py has the routes (the guarded diff applied to the copy when this tree hasn't it), and with
    `mutation` ((old, new) applied to the route's text) when asked. Returns the Vault."""
    v = Vault()
    d = v.root
    if not routes_exist():
        subprocess.run(["git", "init", "-q", str(d)], check=True)
        subprocess.run(["git", "apply", str(PROPOSAL)], cwd=d, check=True)
    if mutation:
        f = d / "system/scripts/live_server.py"
        text = f.read_text()
        old, new = mutation
        assert old in text, f"mutation target not found: {old[:60]}"
        f.write_text(text.replace(old, new, 1))
    return v


class Server:
    """A real live server on a throwaway vault, HOME and agent folder; launchctl is left alone."""

    def __init__(self, mutation=None, own=False):
        self.home = Path(tempfile.mkdtemp(prefix="creaite-300h-")).resolve()
        self.agents = self.home / "agents"
        self.v = make_routes_vault(mutation)
        self.v.run("init")
        (self.v.root / ".creaite-dev").unlink(missing_ok=True)
        self.port = free_port()
        self.base = f"http://127.0.0.1:{self.port}"
        env = {**os.environ, "HOME": str(self.home), "CREAITE_PORT": str(self.port), "CREAITE_AGENT_DIR": str(self.agents),
               "CREAITE_NO_LAUNCHCTL": "1"}
        env.pop("XPC_SERVICE_NAME", None)
        if own:
            env["XPC_SERVICE_NAME"] = label_of(self.v.root)
        self.proc = subprocess.Popen([sys.executable, str(self.v.root / "system/scripts/live_server.py")], env=env,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(150):
            try:
                urllib.request.urlopen(self.base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        html = urllib.request.urlopen(self.base + "/").read().decode()
        self.token = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]
        self.plist = self.agents / f"{label_of(self.v.root)}.plist"

    def close(self):
        self.proc.terminate()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        self.v.cleanup()
        shutil.rmtree(self.home, ignore_errors=True)

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

    def run_file(self, content):
        f = self.v.root / "system/guard/run.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        if f.is_dir():
            f.rmdir()
        else:
            f.unlink(missing_ok=True)
        if content == "DIR":
            f.mkdir()                                 # present but unreadable as a file
        elif content is not None:
            f.write_text(content)


class Checks:
    """Each guard's check, written once: a method takes a Server and raises AssertionError when the guard doesn't hold. The tests run
    them against the real routes, and the mutants run them against a route with that one guard removed (and expect a failure)."""

    @staticmethod
    def token(s):
        for path, body in (("/api/autostart/status", {}), ("/api/autostart/set", {"on": True})):
            for tok in (None, "wrong"):
                code, _ = s.post(path, body, token=tok)
                assert code == 403, (path, tok, code)
        assert not s.plist.exists()

    @staticmethod
    def host(s):
        code, _ = s.post("/api/autostart/set", {"on": True}, host="evil.example")
        assert code == 403, code
        assert not s.plist.exists()

    @staticmethod
    def get_is_404(s):
        code, _ = s.post("/api/autostart/set", method="GET")
        assert code == 404, code
        code, _ = s.post("/api/autostart/status", method="GET")
        assert code == 404, code

    @staticmethod
    def page_call(s):
        code, _ = s.post("/api/autostart/set", {"on": True}, page=False)               # a good token, but not the open page's own call
        assert code == 403, code
        code, _ = s.post("/api/autostart/set", {"on": True}, page=True)
        assert code == 200
        s.post("/api/autostart/set", {"on": False})

    @staticmethod
    def bool_only(s):
        for bad in ("true", 1, None, "on", [True]):
            body = {} if bad is None else {"on": bad}
            code, got = s.post("/api/autostart/set", body)
            assert code == 400 and not got.get("ok"), (bad, code)
        assert not s.plist.exists()

    @staticmethod
    def lock_order(s):
        """The run.json check is made inside START_LOCK, the lock every run start takes (read from the route's own text)."""
        text = (s.v.root / "system/scripts/live_server.py").read_text()
        body = text[text.index("def autostart_set_route"):text.index("AUTOSTART_ROUTES = ")]
        lines = body.splitlines()
        i = next(n for n, ln in enumerate(lines) if "autostart_run_blocks()" in ln)
        w = next(n for n, ln in enumerate(lines) if ln.strip() == "with START_LOCK:")
        assert w < i and len(lines[i]) - len(lines[i].lstrip()) > len(lines[w]) - len(lines[w].lstrip()), "the check is outside START_LOCK"

    @staticmethod
    def run_json_refuses(s):
        for content in ('{"run": "r-1", "mode": "chat", "marked": []}', '{"marked": ["read mail"]}', "{not json", "[1]", "DIR"):
            s.run_file(content)
            code, got = s.post("/api/autostart/set", {"on": True})
            assert code == 200 and got.get("ok") is False, (content, code, got)
            assert not s.plist.exists(), content
            assert not re.search(r"run\.json|launch\.py|guard|json", got["message"]), got["message"]
        s.run_file(None)

    @staticmethod
    def dev_refuses(s):
        (s.v.root / ".creaite-dev").write_text("")
        try:
            code, got = s.post("/api/autostart/status", {})
            assert code == 200 and got["supported"] is False and got["dev"] is True, got
            code, got = s.post("/api/autostart/set", {"on": True})
            assert got.get("ok") is False and "development copy" in got["message"], got
            assert not s.plist.exists()
        finally:
            (s.v.root / ".creaite-dev").unlink(missing_ok=True)


class RealRoutes(unittest.TestCase):
    """The routes, through a real live server (the guarded diff applied to a throwaway copy when this tree hasn't it)."""

    @classmethod
    def setUpClass(cls):
        cls.s = Server()

    @classmethod
    def tearDownClass(cls):
        cls.s.close()

    def setUp(self):
        self.s.run_file(None)
        (self.s.v.root / ".creaite-dev").unlink(missing_ok=True)

    def test_token(self):
        Checks.token(self.s)

    def test_host(self):
        Checks.host(self.s)

    def test_get_is_404(self):
        Checks.get_is_404(self.s)

    def test_only_the_open_pages_own_call(self):
        Checks.page_call(self.s)

    def test_a_non_boolean_is_400(self):
        Checks.bool_only(self.s)

    def test_ask_creaites_run_refuses(self):
        Checks.run_json_refuses(self.s)

    def test_the_development_copy_refuses(self):
        Checks.dev_refuses(self.s)

    def test_the_run_check_is_made_inside_the_run_start_lock(self):
        Checks.lock_order(self.s)

    def test_on_and_off_round_trip_in_words_and_touches_only_the_agent_folder(self):
        s = self.s
        code, got = s.post("/api/autostart/status", {})
        self.assertEqual((code, got["ok"], got["supported"], got["on"], got["own"]), (200, True, True, False, False))
        code, got = s.post("/api/autostart/set", {"on": True})
        self.assertTrue(got["ok"] and got["on"], got)
        self.assertTrue(s.plist.exists())
        self.assertEqual(got["message"], "creaite will start when you sign in.")
        code, got = s.post("/api/autostart/set", {"on": False})
        self.assertTrue(got["ok"] and not got["on"], got)
        self.assertFalse(s.plist.exists())
        self.assertEqual(got["message"], "creaite won't start when you sign in.")
        self.assertFalse((s.home / "Library").exists())                       # nothing under the (throwaway) home's Library
        for m in (got["message"],):
            self.assertNotRegex(m, r"launch\.py|\.plist|system/")

    def test_a_failure_is_logged_with_no_path(self):
        s = self.s
        s.post("/api/autostart/set", {"on": True})
        subprocess.run(["chmod", "500", str(s.agents)])                         # the agent folder can't be written: a real failure
        try:
            code, got = s.post("/api/autostart/set", {"on": False})
            if os.access(s.agents, os.W_OK):
                self.skipTest("this account can write to a read-only folder")
            self.assertFalse(got["ok"])
            self.assertIn("That didn't change", got["message"])
        finally:
            subprocess.run(["chmod", "700", str(s.agents)])
            s.post("/api/autostart/set", {"on": False})
        logs = "".join(f.read_text() for f in (s.v.root / "system/logs").glob("debug-*.log")) if (s.v.root / "system/logs").exists() else ""
        lines = [ln for ln in logs.splitlines() if " autostart " in ln]
        self.assertTrue(any("failed" in ln for ln in lines), lines)
        for ln in lines:
            self.assertNotIn(str(s.home), ln)
            self.assertNotRegex(ln, r"\.plist|/")


class OwnServerRoutes(unittest.TestCase):
    """A server that is the agent's own job (XPC_SERVICE_NAME set by launchd): off removes the file and the reply says it keeps running."""

    @classmethod
    def setUpClass(cls):
        cls.s = Server(own=True)

    @classmethod
    def tearDownClass(cls):
        cls.s.close()

    def test_off_from_the_agents_own_server_says_it_keeps_running(self):
        s = self.s
        code, got = s.post("/api/autostart/status", {})
        self.assertTrue(got["own"])
        s.post("/api/autostart/set", {"on": True})
        self.assertTrue(s.plist.exists())
        code, got = s.post("/api/autostart/set", {"on": False})
        self.assertTrue(got["ok"], got)
        self.assertFalse(s.plist.exists())
        self.assertIn("keeps running until you stop it", got["message"])
        self.assertEqual(s.post("/api/autostart/status", {})[1]["on"], False)       # and the server answered: it is still up


# (name, text in the route, replacement, the check that must then fail)
MUTANTS = [
    ("run.json refusal removed", "        busy = autostart_run_blocks()\n        if busy:", "        busy = None\n        if busy:", "run_json_refuses"),
    ("bool check removed", "    if not isinstance(on, bool):\n        return handler.send(400", "    if False:\n        return handler.send(400", "bool_only"),
    ("page_call removed", "    if not page_call(handler):\n        return handler.send(403, {\"ok\": False, \"message\": \"Not allowed\"})\n    on = req.get(\"on\")",
     "    on = req.get(\"on\")", "page_call"),
    ("development refusal removed", "    if st is None or not st.get(\"supported\"):", "    if st is None:", "dev_refuses"),
    ("fails open on an unreadable run.json", "    except (OSError, ValueError):\n        return \"creaite can't tell", "    except (OSError, ValueError):\n        return None\n        return \"creaite can't tell", "run_json_refuses"),
    ("run.json check moved out of START_LOCK", "    with START_LOCK:\n        busy = autostart_run_blocks()",
     "    busy = autostart_run_blocks()\n    with START_LOCK:", "lock_order"),
]


class Mutants(unittest.TestCase):
    """Each guard removed from a throwaway copy of the routes: the check for it must go red (a test that stays green proves nothing)."""

    def mutant_server(self, mutation, check):
        s = Server(mutation=mutation)
        self.addCleanup(s.close)
        return s

    def test_each_guard_has_a_check_that_catches_its_removal(self):
        ran = 0
        for name, old, new, check in MUTANTS:
            if check is None:
                continue
            s = Server(mutation=(old, new))
            try:
                with self.assertRaises(AssertionError, msg=f"mutant survived: {name}"):
                    getattr(Checks, check)(s)
                ran += 1
            finally:
                s.close()
        self.assertEqual(ran, len(MUTANTS))

    def test_the_unmutated_routes_pass_every_check(self):
        s = Server()
        try:
            for check in ("token", "host", "get_is_404", "page_call", "bool_only", "run_json_refuses", "dev_refuses", "lock_order"):
                getattr(Checks, check)(s)
        finally:
            s.close()


class LauncherMutants(unittest.TestCase):
    """The H1 guards removed from launch.py (a throwaway copy): the own-server tests must go red."""

    def red(self, pairs, names):
        mutated = type("Mutated", (LauncherOwnServer,), {"mutate": pairs})
        suite = unittest.TestSuite(mutated(n) for n in names)
        with open(os.devnull, "w") as null:
            res = unittest.TextTestRunner(stream=null, verbosity=0).run(suite)
        self.assertFalse(res.wasSuccessful(), "the tests stayed green with the guard removed")

    def test_treating_every_server_as_not_the_agents_own_is_caught(self):
        self.red([('return os.environ.get("XPC_SERVICE_NAME") == agent_label()', "return False")],
                 ["test_its_own_server_is_never_unloaded_and_the_words_say_it_carries_on",
                  "test_turning_it_on_from_its_own_server_does_not_unload_it_either"])

    def test_unloading_before_deleting_the_file_is_caught(self):
        self.red([("    had = f.exists()\n    if had:\n        f.unlink()\n", "    had = f.exists()\n"),
                  ('        launchctl("bootout", f"{agent_domain()}/{agent_label()}")\n    print((',
                   '        launchctl("bootout", f"{agent_domain()}/{agent_label()}")\n    f.unlink(missing_ok=True)\n    print((')],
                 ["test_not_its_own_server_the_file_goes_first_then_the_job_is_unloaded"])


if __name__ == "__main__":
    unittest.main()
