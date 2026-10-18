"""#132 round 2, G10 (proposal, not applied): the builder's two review points.

Run: python3 dev/tests/test_ai_proposal_g10_review.py

Round 1 (all but G1c) and round 2 up to g10-fake-switch-and-tested-key.diff are applied to a throwaway vault. No real key,
keychain, provider or network.

Done when:
- CREAITE_FAKE_PROVIDERS=1 switches the test fakes on only in the development repository (.creaite-dev in the vault root) or
  in a test's throwaway vault (inside the system's temporary folder); a vault anywhere else ignores it, gets the real
  (not-built off a Mac, keychain on a Mac) seams, and the debug log says the switch was ignored; without the switch, never;
- a key tested but not yet kept is held for five minutes at most, one per provider (a new Test drops the last), used once,
  dropped by a timer when it runs out even if nothing else happens, on Disconnect of its provider, and when the server stops or
  restarts; it is never written to any file.
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ai_proposal_support as S  # noqa: E402

KEY = S.KEY

MODE = r'''
import providers as pv
pv._BACKEND.clear()
store, lister = pv.backend()
print(json.dumps({"fake": pv.fake_mode(), "store": type(store).__name__, "lister": type(lister).__name__}))'''


class FakeSwitch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = S.vault2("g10-fake-switch-and-tested-key")
        cls.other_tmp = Path(tempfile.mkdtemp(prefix="creaite-elsewhere-"))     # a temporary folder the vault isn't inside

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.other_tmp, ignore_errors=True)

    def mode(self, env):
        return S.run_py(self.root, MODE, env=env)

    def test_a_test_vault_honours_the_switch(self):
        self.assertEqual(self.mode({"CREAITE_FAKE_PROVIDERS": "1"}),
                         {"fake": True, "store": "MemoryStore", "lister": "FakeLister"})

    def test_a_vault_outside_the_temporary_folder_ignores_it(self):
        out = self.mode({"CREAITE_FAKE_PROVIDERS": "1", "TMPDIR": str(self.other_tmp)})   # the vault is not inside it now
        self.assertFalse(out["fake"])
        self.assertNotIn(out["store"], ("MemoryStore",))
        self.assertNotIn(out["lister"], ("FakeLister",))
        logs = "".join(f.read_text() for f in (self.root / "system" / "logs").glob("debug-*.log"))
        self.assertIn("CREAITE_FAKE_PROVIDERS ignored: this isn't the development repository or a test's vault", logs)

    def test_the_development_repository_honours_it(self):
        (self.root / ".creaite-dev").write_text("development\n")
        try:
            out = self.mode({"CREAITE_FAKE_PROVIDERS": "1", "TMPDIR": str(self.other_tmp)})
        finally:
            (self.root / ".creaite-dev").unlink()
        self.assertTrue(out["fake"])

    def test_without_the_switch_never(self):
        self.assertFalse(self.mode({})["fake"])
        self.assertFalse(self.mode({"CREAITE_FAKE_PROVIDERS": "yes"})["fake"])


class TestedKey(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = S.vault2("g10-fake-switch-and-tested-key")

    def test_limits(self):
        out = S.run_py(self.root, r'''
import time, providers as pv
r = {"seconds": pv.PENDING_SECONDS}
a = pv.hold("openai", "k1-TESTONLY-aaaaaaaa", ["m"])
b = pv.hold("openai", "k2-TESTONLY-bbbbbbbb", ["m"])
r["one per provider"] = [pv.take(a), pv.take(b)["key"]]
r["used once"] = pv.take(b)
c = pv.hold("openai", "k3-TESTONLY-cccccccc", ["m"]); d = pv.hold("claude", "k4-TESTONLY-dddddddd", [])
r["disconnect openai"] = [pv.forget_all("openai"), sorted(v["provider"] for v in pv._PENDING.values())]
r["stop"] = [pv.forget_all(), len(pv._PENDING)]
pv.PENDING_SECONDS = 0.3
e = pv.hold("openai", "k5-TESTONLY-eeeeeeee", ["m"]); time.sleep(0.8)
r["timer"] = [len(pv._PENDING), pv.take(e)]
print(json.dumps(r))''')
        self.assertEqual(out["seconds"], 300)
        self.assertEqual(out["one per provider"], [None, "k2-TESTONLY-bbbbbbbb"], "a new Test drops the last")
        self.assertIsNone(out["used once"])
        self.assertEqual(out["disconnect openai"], [1, ["claude"]])
        self.assertEqual(out["stop"], [1, 0])
        self.assertEqual(out["timer"], [0, None], "gone when it runs out, with nothing else happening")

    def test_disconnect_and_server_stop_drop_it(self):
        out = S.run_py(self.root, r'''
import live_server as L, providers as pv
class H:
    def send(self, code, body): pass
pv.hold("openai", "k6-TESTONLY-ffffffff", ["m"])
L.ai_disconnect_route(H(), {"provider": "openai"})
r = {"disconnect": len(pv._PENDING)}
pv.hold("openai", "k7-TESTONLY-gggggggg", ["m"])
L.forget_tested_keys()
r["stop"] = len(pv._PENDING)
src = open(L.__file__, encoding="utf-8").read()
r["hooked"] = [src.count("forget_tested_keys()"), "forget_tested_keys()                                  # #132 G10\n    try:\n        EVENTS.close()" in src]
print(json.dumps(r))''', env={"CREAITE_FAKE_PROVIDERS": "1"})
        self.assertEqual(out["disconnect"], 0)
        self.assertEqual(out["stop"], 0)
        self.assertEqual(out["hooked"], [4, True], "its definition, and SIGTERM, main's end and a restart all call it")

    def test_never_written(self):
        S.run_py(self.root, r'''
import live_server as L, providers as pv
answers = []
class H:
    def send(self, code, body): answers.append(body)
L.ai_test_route(H(), {"provider": "openai", "key": %r})
L.ai_state_route(H(), {})
print(json.dumps(answers))''' % KEY, env={"CREAITE_FAKE_PROVIDERS": "1"})
        for f in self.root.rglob("*"):
            if f.is_file() and not f.is_symlink():
                self.assertNotIn(KEY.encode(), f.read_bytes(), str(f.relative_to(self.root)))


if __name__ == "__main__":
    unittest.main()
