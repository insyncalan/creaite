"""#132 round 2, G9 (proposal, not applied): backups, logs and Health, and a key that never reaches any of them.

Run: python3 dev/tests/test_ai_proposal_g9_backup_log_health.py

Round 1 (all but G1c) and round 2 up to g9-health.diff are applied to a throwaway vault with the fictional portfolio. The live
server's /api/ai routes run in-process with the test fakes (CREAITE_FAKE_PROVIDERS=1: an in-memory key store and a fake model
list), and the direct call goes to a fake HTTPS server on 127.0.0.1. No real key, keychain, provider or network.

Done when:
- every ai.* change (Connect, Choose, the limit, Disconnect) goes through settings_catalogue.save: a settings backup and one
  settings-log.jsonl line per key, ids only;
- Settings › Health lists each provider's connection (Claude's sign-in, OpenAI connected with its models offered) and Claude's
  limit, says when settings say connected but the key store has no key, and when test providers are on; never a key;
- after a whole journey (a refused key, an unreachable provider, Test, Connect, Choose, a suggestion sent to OpenAI, Health,
  Disconnect) the key is in no vault file, no backup, the debug log, settings-log.jsonl, the daily zip or its manifest, and
  no route's answer or Health's output.
"""
import json
import shutil
import sys
import unittest
import zipfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ai_proposal_support as S  # noqa: E402

OPENSSL = shutil.which("openssl")
KEY = S.KEY
BAD = "refused-key-9876543210ZYXWVUTESTONLY"
NET = "fake-net-1111111111TESTONLY"

JOURNEY = r'''
import ssl, time, live_server as L, providers as pv, health, paths
a = json.loads(%r)
pv._DIRECT["caller"] = pv.DirectCaller(base={"openai": a["base"]}, context=ssl.create_default_context(cafile=a["cert"]))
answers = []
class H:
    def __init__(self): self.events = None
    def send(self, code, body): answers.append([code, body])
    def follow(self, r):
        end = time.time() + 20
        while not r.done and time.time() < end: time.sleep(0.05)
        self.events = list(r.events)
L.ai_test_route(H(), {"provider": "openai", "key": a["bad"]})
L.ai_test_route(H(), {"provider": "openai", "key": a["net"]})
L.ai_test_route(H(), {"provider": "openai", "key": a["key"]})
pid = answers[-1][1]["pending"]
L.ai_connect_route(H(), {"pending": pid, "offered": ["fake-flagship", "fake-small"]})
L.ai_choose_route(H(), {"job": "quick", "model": "openai:fake-small", "accept": True})
L.ai_choose_route(H(), {"job": "write", "model": "openai:fake-flagship"})
L.ai_limit_route(H(), {"mode": "other"})
h = H(); L.edit_ai_route(h, {"option": "rewrite", "place": "notes", "code": "ABC", "text": "Please tidy this paragraph now."})
made_by = next(e for e in h.events if e["type"] == "draft").get("made_by")
health_out = health.health({"checks": []})
L.ai_disconnect_route(H(), {"provider": "openai"})
after = health.health({"checks": []})
print(json.dumps({"answers": answers, "made_by": made_by, "health": health_out, "after": after}))'''


@unittest.skipUnless(OPENSSL, "needs openssl to make the fake provider's certificate")
class Journey(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = S.populated(S.vault2("g9-health"))
        cls.tmp, cls.cert, cls.key = S.make_cert()
        cls.srv = S.chat_server(cls.cert, cls.key)
        cls.out = S.run_py(cls.root, JOURNEY % json.dumps({"base": cls.srv.base, "cert": cls.cert, "key": KEY, "bad": BAD,
                                                            "net": NET}), env={"CREAITE_FAKE_PROVIDERS": "1"})
        day = date.today().isoformat()
        shutil.copy2(cls.root / "system" / "tracker.db", cls.root / "system" / "backups" / f"tracker-{day}.db")
        cls.zip = Path(S.run_py(cls.root, f"import backup\nprint(json.dumps(str(backup.make_zip('{day}'))))"))

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_the_journey_ran(self):
        self.assertEqual(self.out["made_by"], "OpenAI fake small", "the suggestion went to OpenAI")
        self.assertEqual(len(self.srv.seen), 1)
        reasons = [b.get("reason") for _c, b in self.out["answers"][:2]]
        self.assertEqual(reasons, ["refused", "network"])

    def test_every_ai_change_is_backed_up_and_logged(self):
        log = [json.loads(x) for x in (self.root / "system" / "config" / "settings-log.jsonl").read_text().splitlines()]
        keys = [x["key"] for x in log]
        for k in ("ai.providers", "ai.jobs.quick", "ai.jobs.write", "ai.on_limit"):
            self.assertIn(k, keys)
        self.assertGreaterEqual(keys.count("ai.providers"), 2, "Connect and Disconnect")
        backups = list((self.root / "system" / "backups").glob("settings-*.json"))
        self.assertGreaterEqual(len(backups), 5, "a backup of the file before each save")
        disconnect = [x for x in log if x["key"] == "ai.providers"][-1]
        self.assertEqual(disconnect["new"], {}, "Disconnect leaves no OpenAI entry")
        self.assertIn({"key": "ai.jobs.quick", "new": "claude:haiku"},
                      [{"key": x["key"], "new": x["new"]} for x in log], "Disconnect put quick edits back on Claude")

    def test_health_shows_connection_state(self):
        ai = self.out["health"]["ai"]
        self.assertEqual(ai, ["Claude: your Claude subscription",
                              "OpenAI: connected, 2 models offered; the key is in this Mac's keychain"])
        self.assertEqual(self.out["after"]["ai"], ["Claude: your Claude subscription"])
        self.assertEqual([p["id"] for p in self.out["health"]["problems"]], ["ai_fake"], "test providers are said to be on")

    def test_the_key_is_nowhere(self):
        for k in (KEY, BAD, NET):
            for f in self.root.rglob("*"):
                if f.is_file() and not f.is_symlink():
                    self.assertNotIn(k.encode(), f.read_bytes(), f"{k[:10]}… in {f.relative_to(self.root)}")
            with zipfile.ZipFile(self.zip) as z:
                names = z.namelist()
                self.assertIn("system/config/settings-log.jsonl", names)
                for n in names:
                    self.assertNotIn(k.encode(), z.read(n), f"{k[:10]}… in the zip's {n}")
                self.assertTrue(any(n.endswith("manifest.json") for n in names))
            self.assertNotIn(k, json.dumps(self.out))
        logs = "".join(f.read_text() for f in (self.root / "system" / "logs").glob("debug-*.log"))
        self.assertIn("openai key tested", logs)
        self.assertNotIn("fake-good", logs)


class HealthLines(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = S.vault2("g9-health")

    def test_a_key_gone_from_the_store_and_the_limit(self):
        out = S.run_py(self.root, r'''
import providers as pv, health, settings_catalogue as sc
cfg = json.loads(json.dumps(sc.defaults()))
cfg["ai"]["providers"] = pv.connect_changes("openai", ["fake-small"], ["fake-small"], cfg)["ai.providers"]
gone = health.ai_models(cfg, pv.MemoryStore())
pv.LIMIT.update(resets=None, until=9e12, kind="")
limited = health.ai_models(json.loads(json.dumps(sc.defaults())), pv.MemoryStore())
pv.LIMIT.clear()
store = pv.MemoryStore(); store.put("claude", "sk-ant-TESTONLY-000000")
cfg2 = json.loads(json.dumps(sc.defaults())); cfg2["ai"]["providers"] = {"claude": {"auth": "key", "models": [], "offered": []}}
claude_key = health.ai_models(cfg2, store)
def broken():
    raise OSError("unreadable")
import paths; paths.load_settings = broken
print(json.dumps({"gone": gone, "limited": limited, "claude key": claude_key, "unreadable": health.ai_models()}))''')
        lines, problems = out["gone"]
        self.assertEqual(lines, ["Claude: your Claude subscription"])
        self.assertEqual([(p["id"], p["title"], p["severity"]) for p in problems],
                         [("ai_openai", "OpenAI is set up but this Mac's keychain has no key for it", "warn")])
        self.assertIn("nothing is sent to OpenAI", problems[0]["detail"])
        self.assertEqual(out["limited"][0][-1], "Claude's limit is reached.")
        self.assertEqual(out["claude key"][0], ["Claude: an API key in this Mac's keychain"])
        self.assertNotIn("sk-ant", json.dumps(out))
        self.assertEqual(out["unreadable"], [["AI models couldn't be checked (OSError)"], []])


if __name__ == "__main__":
    unittest.main()
