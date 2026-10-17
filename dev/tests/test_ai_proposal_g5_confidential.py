"""#132 round 1, G5 (proposal, not applied): confidential material only to Claude, enforced in the server.

Run: python3 dev/tests/test_ai_proposal_g5_confidential.py

g3-chosen-model.diff then g5-confidential-only-claude.diff are applied to a throwaway vault (ai_proposal_support). OpenAI is
"connected" with test-only stand-ins (the in-memory store and fake lister, CREAITE_FAKE_PROVIDERS=1, or a MemoryStore passed in);
no key, provider or network is real.

Done when:
- providers.confidential_job fails closed: a job that uses tools, material the server declared confidential (a closed meeting),
  material nobody checked, and text marked confidential, restricted or Client-safe: no are all confidential; only material the
  server declared clean, with clean text, is not;
- route_for (the server's one way to pick a model) never answers a provider other than Claude for confidential material, even
  when Alan chose that provider and accepted it as weaker, and at a limit with "another connected model"; send_allowed refuses
  such a call outright; clean material does reach the choice (the gate is not a blanket);
- the live server picks every run's model through route_for, never route; a run whose job Alan set to OpenAI starts today's
  Claude launch and says why (a closed meeting: confidential; everything else in round 1: not checked yet).
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ai_proposal_support as S  # noqa: E402

SETUP = r'''
import providers as pv, settings_catalogue as sc
cfg = json.loads(json.dumps(sc.defaults()))
cfg["ai"]["providers"] = pv.connect_changes("openai", ["fake-flagship", "fake-small"], ["fake-flagship", "fake-small"],
                                            cfg)["ai.providers"]
store = pv.MemoryStore(); store.put("openai", "x")
cfg["ai"]["jobs"].update({"write": "openai:fake-small", "quick": "openai:fake-small"})
cfg["ai"]["accepted_weaker"] = ["write=openai:fake-small", "quick=openai:fake-small"]
'''


class Policy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = S.vault("g3-chosen-model", "g5-confidential-only-claude")

    def test_confidential_job_fails_closed(self):
        out = S.run_py(self.root, r'''
import providers as pv
cases = [("tools", "", False), ("guard", "", False), ("write", "", True), ("write", "", None), ("quick", "plain", None),
         ("write", "This is CONFIDENTIAL.", False), ("quick", "restricted to the board", False),
         ("write", "Client-safe: no", False), ("write", "client-safe:no", False), ("write", "A plain sentence.", False),
         ("quick", "Unrestricted access.", False), ("nosuch", "", False)]
print(json.dumps([list(pv.confidential_job(j, t, d)) for j, t, d in cases]))''')
        self.assertEqual(out, [[True, "tools"], [True, "tools"], [True, "declared"], [True, "unchecked"], [True, "unchecked"],
                               [True, "marked"], [True, "marked"], [True, "marked"], [True, "marked"], [False, ""],
                               [False, ""], [True, "tools"]])

    def test_send_allowed_is_the_gate(self):
        out = S.run_py(self.root, r'''
import providers as pv
res = []
for model, conf in (("openai:fake-small", True), ("openai:fake-small", None), ("openai:fake-small", "yes"),
                    ("claude:opus", True), ("openai:fake-small", False), (None, True), ("", True)):
    try: pv.send_allowed(model, conf); res.append("sent")
    except pv.Refused as e: res.append(str(e))
print(json.dumps(res))''')
        words = "Confidential material is only ever sent to Claude."
        self.assertEqual(out, [words, words, words, "sent", "sent", words, words])

    def test_confidential_material_never_routes_to_another_provider(self):
        out = S.run_py(self.root, SETUP + r'''
res = {}
for job in ("write", "quick"):
    for name, text, declared in (("declared", "", True), ("unchecked", "", None), ("marked", "Confidential: the budget", False),
                                 ("client-safe no", "Client-safe: no", False), ("clean", "A plain sentence.", False)):
        for limited, mode in ((False, "ask"), (True, "other"), (True, "step_down"), (True, "ask")):
            c = json.loads(json.dumps(cfg)); c["ai"]["on_limit"] = mode
            r = pv.route_for(job, c, text=text, declared=declared, store=store, limited=limited)
            res[f"{job} | {name} | limited={limited} {mode}"] = [r["model"], r["confidential"], r["confidential_why"]]
print(json.dumps(res))''')
        for k, (model, conf, _why) in out.items():
            if "| clean |" in k:
                self.assertFalse(conf, k)
                continue
            self.assertTrue(conf, k)
            self.assertTrue(model is None or model.startswith("claude:"), f"{k}: {model}")
        self.assertEqual(out["write | clean | limited=False ask"][0], "openai:fake-small", "clean material keeps Alan's choice")
        self.assertEqual(out["write | declared | limited=False ask"][0], "claude:sonnet", "the recommended Claude model instead")
        self.assertEqual(out["quick | marked | limited=False ask"][0], "claude:haiku")


class Server(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = S.vault("g3-chosen-model", "g5-confidential-only-claude")

    def test_the_server_never_calls_route_directly(self):
        src = (self.root / "system" / "scripts" / "live_server.py").read_text(encoding="utf-8")
        self.assertNotIn("providers.route(", src)
        self.assertIn("routed = providers.route_for(job, settings, text=text, declared=declared)", src)
        self.assertIn('CONFIDENTIAL_KINDS = ("shape-closed",)', src)

    def test_runs_set_to_openai_start_on_claude_and_say_why(self):
        out = S.run_py(self.root, SETUP + r'''
import live_server as L
pv._BACKEND["pair"] = (store, pv.FakeLister())
res = {}
for kind, text in (("generate", "Draft the steering note."), ("shape-closed", "A closed meeting."),
                   ("edit-ai", "A plain sentence."), ("notes-find", "Confidential: the budget"), ("ask", "hello")):
    res[kind] = list(L.run_model(kind, cfg, text=text))
res["declared clean"] = list(L.run_model("generate", cfg, text="A plain sentence.", declared=False))
print(json.dumps(res))''', env={"CREAITE_FAKE_PROVIDERS": "1"})
        self.assertEqual(out["shape-closed"], [None, "Confidential material is only ever sent to Claude. So Claude ran it."])
        for kind in ("generate", "edit-ai", "notes-find"):
            self.assertEqual(out[kind], [None, "OpenAI isn't used for this yet. So Claude ran it."], kind)
        self.assertEqual(out["ask"], [None, ""], "a tools job never had OpenAI on offer")
        self.assertEqual(out["declared clean"], [None, "OpenAI isn't used for this yet, so Claude ran it."],
                         "only round 2 (G4) can run it on OpenAI; until then claude -p runs Claude")

    def test_the_launch_stays_todays_and_the_run_says_so(self):
        out = S.run_py(self.root, SETUP + r'''
import io, time, live_server as L, paths
p = paths.ROOT / "system" / "config" / "settings.json"
c = json.loads(p.read_text()); c["ai"] = cfg["ai"]; p.write_text(json.dumps(c))
pv._BACKEND["pair"] = (store, pv.FakeLister())
seen = []
class Proc:
    def __init__(self, cmd, **kw):
        seen.append(cmd); self.stdout, self.stderr, self.returncode, self.pid = io.StringIO(""), io.StringIO(""), 0, 0
    def wait(self, timeout=None): return 0
    def poll(self): return 0
    def kill(self): pass
    def terminate(self): pass
L.subprocess.Popen = Proc
r = L.Run("r-proposal-g5", "A closed meeting.", None, None, None, kind="shape-closed")
cmd = seen[0]
print(json.dumps({"model": cmd[cmd.index("--model") + 1], "models": cmd.count("--model"),
                  "steps": [e["label"] for e in r.events if e.get("type") == "step"]}))''', env={"CREAITE_FAKE_PROVIDERS": "1"})
        self.assertEqual((out["model"], out["models"]), ("sonnet", 1), "#126's pin: today's launch")
        self.assertEqual(out["steps"], ["Confidential material is only ever sent to Claude. So Claude ran it."])


if __name__ == "__main__":
    unittest.main()
