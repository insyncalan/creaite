"""#132: AI models (Settings › Essentials › AI models), server side: providers.py's rules and the /api/ai/… routes.

Run: python3 dev/tests/test_ai_models.py

- The four kinds of job: the lists hold only connected providers' offered models, the recommended model marked and the
  default; a job that needs tools lists only models that can use them; a weaker choice needs Use it anyway, then is
  remembered.
- The limit: "another connected model" needs a second provider, never runs a tool job or confidential material; Ask me asks;
  Step down runs writing as a quick edit and tool jobs wait. Confidential material only ever goes to Claude. A quick edit
  whose check fails retries once on the next kind up.
- The connect journey through a real live server with the fake provider (CREAITE_FAKE_PROVIDERS=1; fake keys only, no
  network): a wrong key, a network error, Cancel, Done, Manage, Disconnect resetting the choices that used it. The key never
  appears in an answer, a file in the vault (settings, backups, logs) or the debug log.
- Without the fake (a real vault, until the keychain is built) nothing connects and no key is held.
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
from test_dashboard import populate  # noqa: E402
from test_tracker import REPO, Vault  # noqa: E402

sys.path.insert(0, str(REPO / "system" / "scripts"))
import providers as pv  # noqa: E402
import settings_catalogue as sc  # noqa: E402

GOOD_KEY = "fake-good-0123456789abcdefTESTONLY"


def with_openai(offered=("fake-flagship", "fake-small")):
    """Settings and a store with a fake OpenAI connected."""
    cfg = json.loads(json.dumps(sc.defaults()))
    cfg["ai"]["providers"] = pv.connect_changes("openai", ["fake-flagship", "fake-small", "fake-embedding"], list(offered),
                                                cfg)["ai.providers"]
    st = pv.MemoryStore()
    st.put("openai", "x")
    return cfg, st


class Rules(unittest.TestCase):
    """providers.py with no vault and no server."""

    def setUp(self):
        self.cfg = json.loads(json.dumps(sc.defaults()))
        self.store = pv.MemoryStore()

    def test_only_claude_at_first_with_the_recommended_models_as_defaults(self):
        st = pv.state(self.cfg, self.store)
        self.assertEqual([p["id"] for p in st["providers"]], ["claude", "openai", "local", "hosted_free", "deepseek"])
        self.assertEqual({p["id"]: p["status"] for p in st["providers"]},
                         {"claude": "connected", "openai": "not", "local": "soon", "hosted_free": "soon", "deepseek": "soon"})
        self.assertNotIn("Gemini", json.dumps(st))
        self.assertNotIn("Grok", json.dumps(st))
        self.assertEqual(st["line"], "Claude is connected. Add OpenAI to use it for drafting and quick edits. "
                                     "Anything else is on its way.")
        self.assertTrue(st["more_hint"])
        jobs = {j["id"]: j for j in st["jobs"]}
        self.assertEqual(list(jobs), ["guard", "tools", "write", "quick"])
        self.assertEqual({k: j["value"] for k, j in jobs.items()},
                         {"guard": "claude:opus", "tools": "claude:sonnet", "write": "claude:sonnet", "quick": "claude:haiku"})
        for j in jobs.values():
            self.assertEqual([o["label"] for o in j["options"]], ["Claude Opus 5.5", "Claude Sonnet 5.5", "Claude Haiku 5.5"])
            self.assertEqual([o["id"] for o in j["options"] if o["recommended"]], [j["value"]])
        self.assertEqual([o["id"] for o in jobs["guard"]["options"] if o["weaker"]], ["claude:sonnet", "claude:haiku"])
        self.assertEqual([o["id"] for o in jobs["quick"]["options"] if o["weaker"]], [])
        self.assertEqual(st["on_limit"], "ask")
        self.assertEqual([x["enabled"] for x in st["limits"]], [True, False, True])
        self.assertEqual(st["limits"][1]["line"], pv.NEEDS_SECOND)

    def test_settings_hold_model_ids_and_never_a_key(self):
        cfg, st = with_openai()
        self.assertNotIn('"x"', json.dumps(cfg))                     # the store's key never reaches settings
        self.assertEqual(cfg["ai"]["providers"]["openai"]["offered"], ["fake-flagship", "fake-small"])
        self.assertEqual([m["id"] for m in cfg["ai"]["providers"]["openai"]["models"]], ["fake-flagship", "fake-small"])
        self.assertEqual({k for m in cfg["ai"]["providers"]["openai"]["models"] for k in m}, {"id", "label", "grade", "tools"})

    def test_a_job_that_needs_tools_lists_only_models_that_can(self):
        cfg, st = with_openai()
        jobs = {j["id"]: j for j in pv.state(cfg, st)["jobs"]}
        for k in ("guard", "tools"):
            self.assertTrue(all(o["id"].startswith("claude:") for o in jobs[k]["options"]), k)
            self.assertTrue(jobs[k]["tools_only"])
        self.assertIn("openai:fake-flagship", [o["id"] for o in jobs["write"]["options"]])
        with self.assertRaisesRegex(pv.Refused, "tools"):
            pv.choose("tools", "openai:fake-flagship", True, cfg, st)
        with self.assertRaisesRegex(pv.Refused, "isn't offered"):
            pv.choose("write", "openai:not-there", True, cfg, st)

    def test_a_weaker_choice_asks_first_then_is_remembered(self):
        with self.assertRaisesRegex(pv.Refused, "weaker"):
            pv.choose("guard", "claude:sonnet", False, self.cfg, self.store)
        ch = pv.choose("guard", "claude:sonnet", True, self.cfg, self.store)
        self.assertEqual(ch, {"ai.jobs.guard": "claude:sonnet", "ai.accepted_weaker": ["guard=claude:sonnet"]})
        self.cfg["ai"]["accepted_weaker"] = ch["ai.accepted_weaker"]
        self.assertEqual(pv.choose("guard", "claude:sonnet", False, self.cfg, self.store), {"ai.jobs.guard": "claude:sonnet"})
        self.assertEqual(pv.choose("write", "claude:opus", False, self.cfg, self.store), {"ai.jobs.write": "claude:opus"})

    def test_grades_from_the_names(self):
        cfg, st = with_openai()
        write = {o["id"]: o for o in pv.options("write", cfg, st)}
        self.assertFalse(write["openai:fake-flagship"]["weaker"])
        self.assertTrue(write["openai:fake-small"]["weaker"])
        self.assertNotIn("openai:fake-embedding", write)

    def test_disconnect_resets_what_used_it(self):
        cfg, st = with_openai()
        cfg["ai"]["jobs"]["write"] = "openai:fake-flagship"
        cfg["ai"]["jobs"]["quick"] = "openai:fake-small"
        cfg["ai"]["accepted_weaker"] = ["quick=openai:fake-small", "guard=claude:sonnet"]
        cfg["ai"]["on_limit"] = "other"
        ch = pv.disconnect_changes("openai", cfg, st)
        self.assertEqual(ch["ai.providers"], {})
        self.assertEqual((ch["ai.jobs.write"], ch["ai.jobs.quick"]), ("claude:sonnet", "claude:haiku"))
        self.assertNotIn("ai.jobs.guard", ch)
        self.assertEqual(ch["ai.accepted_weaker"], ["guard=claude:sonnet"])
        self.assertEqual(ch["ai.on_limit"], "ask")

    def test_manage_untick_resets_a_job_set_to_it(self):
        cfg, st = with_openai()
        cfg["ai"]["jobs"]["quick"] = "openai:fake-small"
        ch = pv.offer_changes("openai", ["fake-flagship"], cfg, st)
        self.assertEqual(ch["ai.providers"]["openai"]["offered"], ["fake-flagship"])
        self.assertEqual(ch["ai.jobs.quick"], "claude:haiku")

    def test_limit_choices(self):
        with self.assertRaisesRegex(pv.Refused, "second connected provider"):
            pv.set_limit("other", self.cfg, self.store)
        self.assertEqual(pv.set_limit("step_down", self.cfg, self.store), {"ai.on_limit": "step_down"})
        cfg, st = with_openai()
        self.assertEqual(pv.set_limit("other", cfg, st), {"ai.on_limit": "other"})

    def test_routing_at_a_limit_and_with_confidential_material(self):
        cfg, st = with_openai()
        r = lambda job, **k: pv.route(job, cfg, st, **k)   # noqa: E731
        self.assertEqual(r("write")["model"], "claude:sonnet")
        cfg["ai"]["on_limit"] = "ask"
        self.assertTrue(r("write", limited=True)["ask"])
        cfg["ai"]["on_limit"] = "other"
        self.assertEqual(r("write", limited=True)["model"], "openai:fake-flagship")
        self.assertTrue(r("tools", limited=True)["wait"])                       # never a job that needs tools
        self.assertTrue(r("write", limited=True, confidential=True)["wait"])    # never confidential material
        cfg["ai"]["on_limit"] = "step_down"
        self.assertEqual(r("write", limited=True)["model"], "claude:haiku")
        self.assertTrue(r("guard", limited=True)["wait"])
        cfg["ai"]["jobs"]["write"] = "openai:fake-flagship"
        self.assertEqual(r("write")["model"], "openai:fake-flagship")
        self.assertEqual(r("write", confidential=True)["model"], "claude:sonnet")   # confidential: only Claude

    def test_a_quick_edit_whose_check_fails_retries_on_the_next_kind_up(self):
        self.assertEqual(pv.retry_kind("quick", ["ABC-A-003 is missing"]), "write")
        self.assertIsNone(pv.retry_kind("quick", []))
        self.assertIsNone(pv.retry_kind("write", ["a date changed"]))

    def test_keys_are_checked_and_refusals_never_echo_them(self):
        self.assertEqual(pv.check_key("openai", ""), "Paste the key first.")
        self.assertIn("no spaces", pv.check_key("openai", "abc def"))
        self.assertIn("can't be connected", pv.check_key("local", "abc"))
        self.assertIn("(401)", pv.refused_words("openai", 401))

    def test_a_real_vault_connects_nothing_until_the_keychain_is_built(self):
        old = os.environ.pop("CREAITE_FAKE_PROVIDERS", None)
        pv._BACKEND.clear()
        try:
            store, lister = pv.backend()
            self.assertFalse(pv.built())
            self.assertFalse(store.has("openai"))
            with self.assertRaises(pv.NotBuilt):
                lister.models("openai", GOOD_KEY)
            with self.assertRaises(pv.NotBuilt):
                store.put("openai", GOOD_KEY)
        finally:
            pv._BACKEND.clear()
            if old is not None:
                os.environ["CREAITE_FAKE_PROVIDERS"] = old

    def test_a_held_key_runs_out(self):
        pid = pv.hold("openai", GOOD_KEY, ["fake-small"], now=1000)
        self.assertIsNone(pv.take(pid, now=1000 + pv.PENDING_SECONDS + 1))
        pid = pv.hold("openai", GOOD_KEY, ["fake-small"], now=1000)
        self.assertTrue(pv.forget(pid))
        self.assertIsNone(pv.take(pid, now=1000))


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Routes(unittest.TestCase):
    """The connect journey through a real live server with the fake provider."""

    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        populate(cls.v)
        cls.port = free_port()
        cls.base = f"http://127.0.0.1:{cls.port}"
        cls.proc = subprocess.Popen([sys.executable, str(cls.v.root / "system/scripts/live_server.py")], stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL, env={**os.environ, "CREAITE_PORT": str(cls.port),
                                                                    "CREAITE_NO_LAUNCH": "1", "CREAITE_FAKE_PROVIDERS": "1"})
        for _ in range(100):
            try:
                urllib.request.urlopen(cls.base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        html = urllib.request.urlopen(cls.base + "/", timeout=60).read().decode()
        cls.token = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)
        cls.v.cleanup()

    def post(self, path, body, token=True):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", **({"X-Creaite-Token": self.token} if token else {})})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
                code = r.status
        except urllib.error.HTTPError as e:
            raw, code = e.read(), e.code
            e.close()
        self.assertNotIn(GOOD_KEY.encode(), raw, path)
        return code, json.loads(raw or b"{}")

    def settings(self):
        return json.loads((self.v.root / "system/config/settings.json").read_text())

    def test_the_journey(self):
        for path in pv_routes():
            self.assertIn(self.post(path, {}, token=False)[0], (401, 403), path)
        code, st = self.post("/api/ai/state", {})
        self.assertEqual((code, st["ok"], st["built"]), (200, True, True))
        # a wrong key, a network error: nothing held, nothing saved
        code, out = self.post("/api/ai/test", {"provider": "openai", "key": "sk-wrong-TESTONLY"})
        self.assertEqual((out["ok"], out["reason"], out["status"]), (False, "refused", 401))
        self.assertIn("OpenAI did not accept this key (401)", out["message"])
        self.assertNotIn("sk-wrong", json.dumps(out))
        out = self.post("/api/ai/test", {"provider": "openai", "key": "fake-net-TESTONLY"})[1]
        self.assertEqual(out["reason"], "network")
        self.assertEqual(self.post("/api/ai/test", {"provider": "local", "key": GOOD_KEY})[0], 400)
        # Cancel after a good test: the held key is dropped and nothing is connected
        out = self.post("/api/ai/test", {"provider": "openai", "key": GOOD_KEY})[1]
        self.assertTrue(out["ok"])
        self.assertEqual([m["id"] for m in out["models"]], ["fake-flagship", "fake-small"])
        self.post("/api/ai/forget", {"pending": out["pending"]})
        self.assertEqual(self.post("/api/ai/connect", {"pending": out["pending"], "offered": []})[0], 409)
        self.assertEqual(self.post("/api/ai/state", {})[1]["providers"][1]["status"], "not")
        # Done: connected, its models in the text-only lists, nothing else changed
        out = self.post("/api/ai/test", {"provider": "openai", "key": GOOD_KEY})[1]
        code, st = self.post("/api/ai/connect", {"pending": out["pending"], "offered": ["fake-flagship", "fake-small"]})
        self.assertEqual(code, 200)
        self.assertEqual(st["providers"][1]["status"], "connected")
        self.assertEqual(st["line"], "Claude and OpenAI are connected. Anything else is on its way.")
        jobs = {j["id"]: j for j in st["jobs"]}
        self.assertIn("openai:fake-small", [o["id"] for o in jobs["quick"]["options"]])
        self.assertNotIn("openai:fake-small", [o["id"] for o in jobs["tools"]["options"]])
        self.assertEqual(jobs["write"]["value"], "claude:sonnet")
        # choose: a weaker model asks first; a tool job refuses a model without tools
        self.assertEqual(self.post("/api/ai/choose", {"job": "write", "model": "openai:fake-small"})[0], 409)
        self.assertEqual(self.post("/api/ai/choose", {"job": "write", "model": "openai:fake-small", "accept": True})[0], 200)
        self.assertEqual(self.post("/api/ai/choose", {"job": "tools", "model": "openai:fake-flagship", "accept": True})[0], 400)
        self.assertEqual(self.post("/api/ai/limit", {"mode": "other"})[0], 200)
        self.assertEqual(self.settings()["ai"]["accepted_weaker"], ["write=openai:fake-small"])
        # Disconnect: the models leave the lists and what used them goes back to the recommended model
        code, st = self.post("/api/ai/disconnect", {"provider": "openai"})
        self.assertEqual((code, st["reset"]), (200, ["write"]))
        s = self.settings()["ai"]
        self.assertEqual((s["jobs"]["write"], s["on_limit"], s["accepted_weaker"], s["providers"]),
                         ("claude:sonnet", "ask", [], {}))
        # the key is nowhere on disk: settings, their backups, the settings log, the debug log, staging
        for p in self.v.root.rglob("*"):
            if p.is_file() and p.stat().st_size < 5_000_000:
                self.assertNotIn(GOOD_KEY.encode(), p.read_bytes(), str(p))
        logs = "".join(p.read_text(errors="replace") for p in (self.v.root / "system/logs").glob("*.log"))
        self.assertIn("ai-models", logs)
        self.assertNotIn("fake-good", logs)


def pv_routes():
    return ("/api/ai/state", "/api/ai/test", "/api/ai/connect", "/api/ai/forget", "/api/ai/offer", "/api/ai/disconnect",
            "/api/ai/choose", "/api/ai/limit")


if __name__ == "__main__":
    unittest.main()
