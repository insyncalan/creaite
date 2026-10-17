"""#132 round 1, G1 (proposal, not applied): the keychain key store and the rules that keep model runs away from it.

Run: python3 dev/tests/test_ai_proposal_g1_keystore.py

Each test applies dev/proposals/ai-models/round1/g1-key-store.diff to a throwaway vault and checks it there (ai_proposal_support).
No real keychain is touched: KeychainStore is driven through a stand-in for the Security framework calls, which records every
call. The one real round trip (a fake key in this Mac's login keychain under a unique test name, deleted at once) runs only with
CREAITE_KEYCHAIN_LIVE=1 on a Mac.

Done when:
- the store: one keychain item per vault and provider; has() never reads the secret and counts a keychain that can't answer as
  no key; put() checks the key's shape before any call and replaces an earlier key; peek() reads it back; remove() deletes it;
  every error is plain words and a status, never the key; providers.py starts no program and touches no environment variable;
  only the live server can read a key (no other script calls peek); backend() picks the keychain only on a Mac;
- a model run, in every guard mode (ask, confirmed, sweep, sweep held, prep, held), is refused `security`, `defaults`, `osascript`,
  python -c, providers.py (directly or through system/scripts/run) and a creaite script given the keychain's path; ask, confirmed and
  sweep are refused reading the keychain file (the held modes are G1c's); the wrapper refuses providers.py;
- no permission rule may name the keychain command, the keychain folder, creaite's keychain items or providers.py, whatever is
  approved; ordinary rules are unchanged;
- the /api/ai routes answer a keychain that says no in plain words, with no key, and save nothing.
"""
import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ai_proposal_support as S  # noqa: E402

KEY = "fake-good-0123456789abcdefTESTONLY"

FAKE_API = r'''
import providers as pv
class FakeApi:
    """Stands in for the Security framework: a dict of items, every call recorded, statuses forced per method if asked."""
    def __init__(self, force=None):
        self.items, self.calls, self.force = {}, [], dict(force or {})
    def _f(self, name, ok):
        return self.force.get(name, ok)
    def add(self, service, account, label, secret):
        self.calls.append(("add", service, account, label, type(secret).__name__))
        if "add" in self.force: return self.force["add"]
        if (service, account) in self.items: return pv.DUPLICATE
        self.items[(service, account)] = secret; return 0
    def exists(self, service, account):
        self.calls.append(("exists", service, account))
        return self._f("exists", 0 if (service, account) in self.items else pv.NOT_FOUND)
    def read(self, service, account):
        self.calls.append(("read", service, account))
        if "read" in self.force: return self.force["read"], None
        v = self.items.get((service, account)); return (0, v) if v is not None else (pv.NOT_FOUND, None)
    def delete(self, service, account):
        self.calls.append(("delete", service, account))
        if "delete" in self.force: return self.force["delete"]
        return 0 if self.items.pop((service, account), None) is not None else pv.NOT_FOUND
'''


class Store(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = S.vault("g1-key-store")

    def check(self, code, env=None):
        return S.run_py(self.root, FAKE_API + code, env)

    def test_one_item_per_vault_and_provider(self):
        out = self.check(r'''
a = pv.KeychainStore(FakeApi(), vault=pv.vault_id("/tmp/vault-a"))
b = pv.KeychainStore(FakeApi(), vault=pv.vault_id("/tmp/vault-b"))
bad = []
for p in ("local", "hosted_free", "deepseek", "nosuch", "../x"):
    try: a.service(p); bad.append(p)
    except ValueError: pass
print(json.dumps({"a": a.service("openai"), "b": b.service("openai"), "claude": a.service("claude"), "here": pv.vault_id(),
                  "bad": bad, "account": pv.KEYCHAIN_ACCOUNT}))''')
        self.assertRegex(out["a"], r"^creaite\.ai\.[0-9a-f]{12}\.openai$")
        self.assertNotEqual(out["a"], out["b"], "two vaults must not share a key")
        self.assertTrue(out["claude"].endswith(".claude"))
        self.assertRegex(out["here"], r"^[0-9a-f]{12}$")
        self.assertEqual(out["bad"], [], "a provider that takes no key has no keychain item")
        self.assertEqual(out["account"], "creaite")

    def test_has_never_reads_the_secret_and_a_keychain_that_cannot_answer_is_no_key(self):
        out = self.check(r'''
api = FakeApi(); st = pv.KeychainStore(api, vault="v")
before = st.has("openai"); st.put("openai", "%s"); api.calls.clear()
after = st.has("openai")
locked = pv.KeychainStore(FakeApi(force={"exists": -25308}), vault="v").has("openai")
print(json.dumps({"before": before, "after": after, "calls": [c[0] for c in api.calls], "locked": locked}))''' % KEY)
        self.assertEqual((out["before"], out["after"]), (False, True))
        self.assertEqual(out["calls"], ["exists"], "has() asks whether the item is there, never for its secret")
        self.assertFalse(out["locked"], "a locked keychain counts as not connected: nothing is sent")

    def test_put_checks_the_key_first_and_replaces_an_earlier_one(self):
        out = self.check(r'''
api = FakeApi(); st = pv.KeychainStore(api, vault="v")
refused = []
for k in ("", "short", "has space inside", "quote\"d-0123456789", "new\nline-0123456789", "x" * 401, None, 12345678):
    try: st.put("openai", k)
    except pv.Refused as e: refused.append(str(e))
calls_after_refusals = len(api.calls)
st.put("openai", "%s"); st.put("openai", "  fake-second-0123456789  ")
print(json.dumps({"refused": len(refused), "words": refused[0], "calls_after_refusals": calls_after_refusals,
                  "calls": [c[0] for c in api.calls], "label": api.calls[1][3], "kind": api.calls[1][4],
                  "now": st.peek("openai")}))''' % KEY)
        self.assertEqual(out["refused"], 8)
        self.assertIn("doesn't look like a key", out["words"])
        self.assertEqual(out["calls_after_refusals"], 0, "a bad key never reaches the keychain")
        self.assertEqual(out["calls"], ["delete", "add", "delete", "add"], "put replaces: the old item goes, the new one is added")
        self.assertEqual(out["label"], "creaite AI key (OpenAI)")
        self.assertEqual(out["kind"], "bytes")
        self.assertEqual(out["now"], "fake-second-0123456789", "the key is kept trimmed, and the later one wins")

    def test_peek_and_remove(self):
        out = self.check(r'''
st = pv.KeychainStore(FakeApi(), vault="v")
none = st.peek("openai"); st.put("openai", "%s")
got = st.peek("openai"); first = st.remove("openai"); second = st.remove("openai")
print(json.dumps({"none": none, "got": got, "first": first, "second": second, "after": st.has("openai")}))''' % KEY)
        self.assertEqual(out, {"none": None, "got": KEY, "first": True, "second": False, "after": False})

    def test_peek_is_the_only_way_back_and_the_stand_ins_hold_nothing(self):
        out = self.check(r'''
res = {}
try: pv.KeyStore().peek("openai"); res["base"] = "no error"
except NotImplementedError: res["base"] = "abstract"
res["not built"] = pv.NotBuiltStore().peek("openai")
m = pv.MemoryStore(); m.put("openai", "%s"); res["memory"] = m.peek("openai") == "%s"
print(json.dumps(res))''' % (KEY, KEY))
        self.assertEqual(out, {"base": "abstract", "not built": None, "memory": True})

    def test_the_keychain_is_asked_only_about_a_connected_provider(self):
        out = self.check(r'''
import settings_catalogue as sc
api = FakeApi(); st = pv.KeychainStore(api, vault="v")
cfg = json.loads(json.dumps(sc.defaults()))
pv.state(cfg, st); pv.route("write", cfg, st); pv.route("tools", cfg, st)
before = [c[0] for c in api.calls]
cfg["ai"]["providers"] = pv.connect_changes("openai", ["fake-small"], ["fake-small"], cfg)["ai.providers"]
api.calls.clear(); pv.state(cfg, st)
print(json.dumps({"default": before, "connected": sorted({c[1].rsplit(".", 1)[-1] for c in api.calls}),
                  "kinds": sorted({c[0] for c in api.calls})}))''')
        self.assertEqual(out["default"], [], "at the defaults nothing asks the keychain (pages, runs, tests)")
        self.assertEqual(out["connected"], ["openai"])
        self.assertEqual(out["kinds"], ["exists"], "and then only whether the item is there")

    def test_every_keychain_error_is_plain_words_and_never_the_key(self):
        out = self.check(r'''
res = {}
for method, status in (("add", -25308), ("add", -128), ("delete", -25293), ("read", -25291), ("read", -99999)):
    api = FakeApi(force={method: status}); st = pv.KeychainStore(api, vault="v")
    if method == "read": api.items[(st.service("openai"), "creaite")] = b"%s"
    try:
        st.peek("openai") if method == "read" else st.put("openai", "%s")
        res[f"{method} {status}"] = "no error"
    except pv.KeychainError as e:
        res[f"{method} {status}"] = [str(e), e.status, e.__cause__ is None and e.__context__ is None]
try:
    pv.KeychainStore(FakeApi(force={"delete": -25308}), vault="v").remove("openai"); res["remove"] = "no error"
except pv.KeychainError as e:
    res["remove"] = [str(e), e.status, True]
print(json.dumps(res))''' % (KEY, KEY))
        self.assertEqual(len(out), 6)
        for name, got in out.items():
            self.assertIsInstance(got, list, name)
            words, status, clean = got
            self.assertNotIn(KEY, words, name)
            self.assertNotIn("fake-good", words, name)
            self.assertTrue(clean, f"{name}: no chained exception that could carry the key")
            self.assertTrue(words.endswith(".") and len(words) < 120, name)
        self.assertIn("locked", out["add -25308"][0])
        self.assertIn("status -99999", out["read -99999"][0])

    def test_no_program_no_environment_and_only_the_live_server_reads_a_key(self):
        src = (self.root / "system" / "scripts" / "providers.py").read_text(encoding="utf-8")
        for bad in ("subprocess", "os.system", "Popen", "os.exec", "os.spawn", "os.environ[", "environ.update", "putenv",
                    "/usr/bin/security", "find-generic-password", "add-generic-password"):
            self.assertNotIn(bad, src, f"providers.py must not use {bad}: the key would leave the process")
        self.assertIn("class KeychainStore(KeyStore)", src)
        self.assertIn('LoadLibrary("/System/Library/Frameworks/Security.framework/Security")', src)
        readers = sorted(f.name for f in (self.root / "system" / "scripts").glob("*.py")
                         if ".peek(" in f.read_text(encoding="utf-8") and f.name != "providers.py")
        self.assertTrue(set(readers) <= {"live_server.py"}, f"only the live server may read a key back: {readers}")

    def test_backend_picks_the_keychain_only_on_a_mac(self):
        out = self.check(r'''
res = {}
for plat in ("darwin", "linux", "win32"):
    pv._BACKEND.clear(); sys.platform = plat
    store, lister = pv.backend()
    res[plat] = [type(store).__name__, type(lister).__name__, pv.built()]
os.environ["CREAITE_FAKE_PROVIDERS"] = "1"; pv._BACKEND.clear(); sys.platform = "darwin"
res["fake"] = [type(pv.backend()[0]).__name__, pv.built()]
print(json.dumps(res))''')
        self.assertEqual(out["darwin"], ["KeychainStore", "NotBuiltLister", False],
                         "with G1 alone the page still can't connect: the model list is G2")
        self.assertEqual(out["linux"], ["NotBuiltStore", "NotBuiltLister", False])
        self.assertEqual(out["win32"], ["NotBuiltStore", "NotBuiltLister", False])
        self.assertEqual(out["fake"], ["MemoryStore", True])

    @unittest.skipUnless(os.environ.get("CREAITE_KEYCHAIN_LIVE") == "1" and sys.platform == "darwin",
                         "the real keychain round trip runs only with CREAITE_KEYCHAIN_LIVE=1 on a Mac")
    def test_real_keychain_round_trip_with_a_fake_key(self):
        out = S.run_py(self.root, r'''
import secrets, providers as pv
st = pv.KeychainStore(vault="proposal-test-" + secrets.token_hex(4))
key = "fake-live-" + secrets.token_hex(8)
try:
    res = {"before": st.has("openai")}
    st.put("openai", key); res["has"] = st.has("openai"); res["peek"] = st.peek("openai") == key
    hits = [str(f) for f in __import__("pathlib").Path(".").rglob("*") if f.is_file() and key.encode() in f.read_bytes()]
    res["vault_files_with_key"] = hits
finally:
    res["removed"] = st.remove("openai")
res["after"] = st.has("openai")
print(json.dumps(res))''')
        self.assertEqual(out, {"before": False, "has": True, "peek": True, "vault_files_with_key": [], "removed": True,
                               "after": False})


GUARD_MODES = (("ask", False), ("confirmed", False), ("sweep", False), ("sweep", True), ("prep", False), ("held", False))


class ModelRuns(unittest.TestCase):
    """What a model run could do to reach the keychain: nothing, in every guard mode (reach.decide, as the hook calls it)."""

    @classmethod
    def setUpClass(cls):
        cls.root = S.vault("g1-key-store")
        cls.home = S.fake_home()

    def decide(self, calls):
        return S.run_py(self.root, r'''
import reach
calls = json.loads(%r)
out = {}
for mode, held in %r:
    for tool, inp in calls:
        out[f"{mode}{' held' if held else ''} | {tool} | {json.dumps(inp)}"] = list(reach.decide(tool, inp, mode, "", held))
print(json.dumps(out))''' % (json.dumps(calls), GUARD_MODES), env={"HOME": str(self.home)})

    def test_no_mode_runs_a_command_that_reaches_the_keychain(self):
        kc = f"{self.home}/Library/Keychains/login.keychain-db"
        cmds = ["security find-generic-password -s creaite.ai.x.openai -w", "/usr/bin/security dump-keychain",
                "security add-generic-password -s x -a y -w z", "defaults read com.apple.security",
                "osascript -e 'do shell script \"security find-generic-password -w\"'",
                "python3 -c \"import providers\"", "python3 -c 'print(1)'", "system/scripts/run providers.py",
                "python3 system/scripts/providers.py", "system/scripts/run providers.py peek openai",
                f"cat {kc}", "env | grep KEY", "printenv"]
        out = self.decide([["Bash", {"command": c}] for c in cmds])
        allowed = sorted(k for k, v in out.items() if v[0])
        self.assertEqual(allowed, [], "every one of these is refused in every mode")
        self.assertEqual(len(out), len(cmds) * len(GUARD_MODES))
        # a creaite script handed the keychain's path: refused by ask creaite's hook (its never list); in the held modes it is
        # G1c's (system/scripts/run refuses it as well, wrap_problem, whatever the mode)
        by_path = self.decide([["Bash", {"command": f"system/scripts/run search.py preview {kc}"}],
                               ["Bash", {"command": f"python3 system/scripts/docx_tools.py text {kc}"}]])
        self.assertEqual(sorted(k for k, v in by_path.items() if v[0] and not k.startswith(("prep", "held"))), [])

    def test_providers_py_is_refused_by_name_even_in_a_confirmed_run(self):
        out = self.decide([["Bash", {"command": "system/scripts/run providers.py"}]])
        why = out['confirmed | Bash | {"command": "system/scripts/run providers.py"}']
        self.assertEqual(why[0], False)
        self.assertIn("AI key store", why[1], "refused because it is the key store, not only because it is unclassified")

    def test_reading_the_keychain_file_is_refused_in_ask_confirmed_and_sweep(self):
        kc = f"{self.home}/Library/Keychains/login.keychain-db"
        out = self.decide([["Read", {"file_path": kc}], ["Grep", {"pattern": "x", "path": f"{self.home}/Library"}],
                           ["Glob", {"pattern": "*", "path": f"{self.home}/Library/Keychains"}]])
        for k, v in out.items():
            if not k.startswith(("prep", "held")):          # the held modes: G1c (a separate item)
                self.assertFalse(v[0], k)

    def test_the_wrapper_refuses_providers_py(self):
        out = S.run_py(self.root, r'''
import reach
print(json.dumps([reach.wrap_problem(["providers.py"]), reach.wrap_problem(["providers.py", "x"]),
                  reach.wrap_problem(["doctor.py"])]))''')
        self.assertIn("AI key store", out[0] or "")
        self.assertIn("AI key store", out[1] or "")
        self.assertIsNone(out[2], "other scripts still run through the wrapper")


class PermissionRules(unittest.TestCase):
    """No permission rule may reach the keychain or the key store, whatever is approved (permissions.py)."""

    @classmethod
    def setUpClass(cls):
        cls.root = S.vault("g1-key-store")

    def test_rules_that_reach_the_keychain_are_refused(self):
        rules = ["Bash(security *)", "Bash(security find-generic-password *)", "Bash(/usr/bin/security *)",
                 "Bash(security:*)", "Read(~/Library/Keychains/**)", "Read(//Users/x/Library/Keychains/login.keychain-db)",
                 "Edit(~/Library/Keychains/**)", "Bash(system/scripts/run providers.py *)",
                 "Bash(python3 system/scripts/providers.py *)", "Read(creaite.ai.*)", "Bash(open -a Keychain*)"]
        ordinary = ["Bash(python3 system/scripts/report.py *)", "Edit(inbox/**)", "Read(**)", "Bash(system/scripts/run doctor.py *)"]
        out = S.run_py(self.root, r'''
import permissions as P
rules, ordinary = %r, %r
base = {"permissions": {"allow": ["Read(**)"], "deny": ["Edit(.claude/settings.json)", "Write(.claude/settings.json)"]}}
res = {"refusal": {r: P.rule_refusal(r) for r in rules + ordinary},
       "settings": {r: P.settings_problem("claude", base, {"permissions": {**base["permissions"],
                                                                           "allow": base["permissions"]["allow"] + [r]}})
                    for r in rules},
       "check": {r: P.check_full(r)["ok"] for r in ["Bash(system/scripts/run providers.py *)",
                                                     "Bash(python3 system/scripts/providers.py *)", "Bash(security *)"]}}
print(json.dumps(res))''' % (rules, ordinary))
        for r in rules:
            self.assertIn("keychain", out["refusal"][r] or "", r)
            self.assertIn("keychain", out["settings"][r] or "", r)
        for r in ordinary:
            self.assertNotIn("keychain", out["refusal"][r] or "", f"{r}: an ordinary rule isn't caught by the keychain check")
        self.assertEqual(set(out["check"].values()), {False})


class Routes(unittest.TestCase):
    """The /api/ai routes (non-guarded block) when the keychain says no."""

    @classmethod
    def setUpClass(cls):
        cls.root = S.vault("g1-key-store")

    def test_a_keychain_that_says_no_answers_plain_words_and_saves_nothing(self):
        out = S.run_py(self.root, r'''
import live_server as L, providers as pv, paths
class Locked(pv.MemoryStore):
    def put(self, p, k): raise pv.KeychainError(-25308)
    def remove(self, p): raise pv.KeychainError(-25308)
pv._BACKEND["pair"] = (Locked(), pv.FakeLister())
sent = []
class H:
    def send(self, code, body): sent.append([code, body])
before = (paths.ROOT / "system/config/settings.json").read_text()
pid = pv.hold("openai", "%s", ["fake-small"])
L.ai_connect_route(H(), {"pending": pid, "offered": ["fake-small"]})
L.ai_disconnect_route(H(), {"provider": "openai"})
after = (paths.ROOT / "system/config/settings.json").read_text()
print(json.dumps({"sent": sent, "unchanged": before == after}))''' % KEY)
        self.assertTrue(out["unchanged"], "nothing is saved when the keychain says no")
        for code, body in out["sent"]:
            self.assertEqual((code, body["ok"], body["reason"]), (200, False, "keychain"))
            self.assertIn("locked", body["message"])
            self.assertNotIn(KEY, json.dumps(body))


if __name__ == "__main__":
    unittest.main()
