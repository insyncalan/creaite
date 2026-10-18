"""#132 round 2, G4 (proposal, not applied): the direct call to OpenAI for a quick edit, after the checks.

Run: python3 dev/tests/test_ai_proposal_g4_direct.py

Round 1's diffs (all but G1c) and g4-direct-call.diff are applied to a throwaway vault (ai_proposal_support.vault2), with the
small fictional portfolio in its tracker. OpenAI is "connected" with test stand-ins (an in-memory store holding a fake key), the
direct call goes to a fake HTTPS server on 127.0.0.1 whose certificate only the test trusts, and claude -p is a recorder. No real
key, provider or network.

Done when:
- the declared list is exactly AI on selected text's ten options (not "Or say what you want…", not "Make it executive"); nothing
  else, and no writing job, is declared;
- edit_ai.outside_problems finds, in the text actually sent, the word VIP, confidential/restricted/Client-safe/internal-only
  markers, an email address, an item ID however written, a project's code or name, its internal health reason, a person or
  organisation creaite knows, and what the client check finds; clean text passes; a tracker or register that can't be read fails
  closed;
- what is sent is the option's instruction, the format rule and the selection: never the project's name, people or item IDs;
- the call: one POST to /v1/chat/completions, the key in one header, model/messages/max_completion_tokens/store=false only;
  refusals, 5xx, redirects, oversized, non-JSON and empty answers, timeouts and untrusted certificates are errors that hold
  neither the key, the prompt nor the reply; too long a prompt is never sent; the debug log gets host, status and token counts;
- through the live server: clean text goes to OpenAI and the draft says which model made it; text with an ID, a person or a
  confidential marker, and the free-instruction option, go to Claude with a step saying why, and nothing reaches the fake
  server; at the default settings nothing changes (the route answers as before, claude -p runs); in the client place the reply
  is still checked; Stop ends a slow call.
"""
import json
import shutil
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ai_proposal_support as S  # noqa: E402

OPENSSL = shutil.which("openssl")
CLEAN = "Please tidy this paragraph about the plan for next week."


@unittest.skipUnless(OPENSSL, "needs openssl to make the fake provider's certificate")
class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = S.populated(S.vault2("g4-direct-call"))
        cls.tmp, cls.cert, cls.key = S.make_cert()
        cls.srv = S.chat_server(cls.cert, cls.key)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        self.srv.seen.clear()
        self.srv.mode = "ok"

    def run_in(self, code, jobs=None, **more):
        return S.run_py(self.root, S.openai_setup(self.srv, self.cert, {"quick": "openai:fake-small"} if jobs is None else jobs,
                                                  **more) + code)


class Declared(Base):
    def test_the_declared_list(self):
        out = S.run_py(self.root, r'''
import providers as pv
print(json.dumps({"clean": {k: list(v) for k, v in pv.CLEAN_FEATURES.items()},
                  "decl": [pv.declared("edit-ai", "rewrite", []), pv.declared("edit-ai", "rewrite", ["an item ID"]),
                           pv.declared("edit-ai", "custom", []), pv.declared("edit-ai", "executive", []),
                           pv.declared("generate", "rewrite", []), pv.declared("edit-ai", "rewrite", None)],
                  "hosts": pv.DIRECT_HOSTS, "limits": [pv.DIRECT_TIMEOUT, pv.DIRECT_SEND, pv.DIRECT_CAP, pv.DIRECT_TOKENS]}))''')
        self.assertEqual(out["clean"], {"edit-ai": ["rewrite", "shorter", "longer", "spelling", "polish", "formal", "warmer",
                                                    "format", "checklist", "summary"]})
        self.assertEqual(out["decl"], [False, True, True, True, True, True], "only a declared option with no problems is clean")
        self.assertEqual(out["hosts"], {"openai": "api.openai.com"})
        self.assertEqual(out["limits"], [30, 16000, 256000, 2000])

    def test_outside_problems(self):
        out = S.run_py(self.root, r'''
import edit_ai
cases = {"clean": ("ABC", "Please tidy this paragraph about the plan."), "id": ("ABC", "See ABC-A-001 for the plan."),
         "loose id": ("", "see abc a 1 now"), "person": ("ABC", "Jane said the plan is fine."),
         "owner": ("", "Omar Ali will send it."), "organisation": ("", "Example Client Ltd wants it."),
         "project name": ("", "The Example Programme is late."), "code": ("", "ABC is late."),
         "health reason": ("", "UAT start slipped 14 days, sadly."), "email": ("", "write to someone@example.com"),
         "confidential": ("", "This is confidential."), "restricted": ("", "Restricted to the board."),
         "client-safe": ("", "Client-safe: no"), "internal": ("", "For internal use only."), "vip": ("", "a V.I.P. call"),
         "lower-case code word": ("", "the abc of it")}
print(json.dumps({k: edit_ai.outside_problems(c, t) for k, (c, t) in cases.items()}))''')
        self.assertEqual(out.pop("clean"), [])
        self.assertEqual(out.pop("lower-case code word"), [], "a code is matched as capitals; an ID however written")
        for name, why in out.items():
            self.assertTrue(why, f"{name} must not go to another provider")
        self.assertIn("an item ID", out["id"])
        self.assertIn("an item ID", out["loose id"])
        self.assertIn("a person or organisation creaite knows", out["person"])
        self.assertIn("a person or organisation creaite knows", out["owner"])
        self.assertIn("a person or organisation creaite knows", out["organisation"])
        self.assertIn("a project's code or name", out["project name"])
        self.assertIn("a project's internal health reason", out["health reason"])
        self.assertEqual(out["vip"], ["something private"])

    def test_outside_problems_fails_closed(self):
        out = S.run_py(self.root, r'''
import edit_ai, paths, tracker
res = {}
real = paths.PEOPLE_REGISTER
paths.PEOPLE_REGISTER = paths.ROOT / "nowhere.md"
res["register"] = edit_ai.outside_problems("", "A plain sentence.")
paths.PEOPLE_REGISTER = real
def broken():
    raise OSError("no database")
tracker.connect = broken
res["tracker"] = edit_ai.outside_problems("", "A plain sentence.")
print(json.dumps(res))''')
        self.assertEqual(out["register"], [S_REGISTER])
        self.assertEqual(out["tracker"], ["the check couldn't run"])

    def test_the_prompt_sent_holds_no_project_facts(self):
        out = S.run_py(self.root, r'''
import edit_ai
ctx = edit_ai.context({"option": "rewrite", "place": "notes", "code": "ABC", "text": "Please tidy this paragraph."})
print(json.dumps({"claude": ctx["prompt"], "outside": edit_ai.outside_prompt("rewrite", "notes", "Please tidy this paragraph."),
                  "client": edit_ai.outside_prompt("shorter", "client", "Please tidy this paragraph.")}))''')
        self.assertIn("Example Programme", out["claude"], "Claude's prompt names the project, as today")
        for word in ("Example Programme", "ABC-", "Omar Ali", "Sara Example", "Its people", "open item IDs", "The project"):
            self.assertNotIn(word, out["outside"], word)
        self.assertIn("<<<TEXT\nPlease tidy this paragraph.\nTEXT>>>", out["outside"])
        self.assertIn("Rewrite the text so it reads clearly", out["outside"])
        self.assertIn("This text is for the client.", out["client"])


S_REGISTER = "the people register couldn't be read"


CALL = r'''
import providers as pv
c = pv._DIRECT["caller"]
try:
    r = ["ok"] + list(c.complete(a.get("provider", "openai"), a.get("model", "fake-small"), a.get("prompt", "Tidy this."), a["key"]))
except pv.KeyRefused as e:
    r = ["refused", e.status, str(e), e.__cause__ is None and (e.__context__ is None or e.__suppress_context__)]
except pv.ProviderUnreachable as e:
    r = ["unreachable", str(e), e.__cause__ is None and (e.__context__ is None or e.__suppress_context__)]
except ValueError as e:
    r = ["refused before sending", str(e)]
print(json.dumps(r))'''


class Call(Base):
    def call(self, mode="ok", **kw):
        self.srv.mode = mode
        self.srv.seen.clear()
        return self.run_in("a.update(json.loads(%r))\n" % json.dumps(kw) + CALL, timeout=kw.get("timeout", 5))

    def test_one_post_with_the_key_in_one_header(self):
        out = self.call(prompt="Tidy this, please.")
        self.assertEqual(out, ["ok", "<<<SUGGESTION\nA tidier sentence.\nSUGGESTION>>>", {"in": 120, "out": 40}])
        self.assertEqual(len(self.srv.seen), 1)
        req = self.srv.seen[0]
        self.assertEqual((req["method"], req["path"]), ("POST", "/v1/chat/completions"))
        self.assertEqual([k for k, v in req["headers"].items() if S.KEY in v], ["Authorization"])
        body = json.loads(req["body"])
        self.assertEqual(body, {"model": "fake-small", "messages": [{"role": "user", "content": "Tidy this, please."}],
                                "max_completion_tokens": 2000, "store": False})

    def test_errors_hold_no_key_prompt_or_reply(self):
        for mode, want in (("401", "refused"), ("429", "refused"), ("500", "unreachable"), ("redirect", "unreachable"),
                           ("big", "unreachable"), ("notjson", "unreachable"), ("empty", "unreachable")):
            out = self.call(mode, prompt="SECRET-PROMPT-WORDS")
            self.assertEqual(out[0], want, mode)
            self.assertTrue(out[-1], f"{mode}: no chained exception")
            text = json.dumps(out)
            for x in (S.KEY, "SECRET-PROMPT-WORDS", "echo"):
                self.assertNotIn(x, text, mode)
            self.assertEqual(len(self.srv.seen), 1, f"{mode}: one request; a redirect is never followed")

    def test_timeout_and_tls(self):
        t0 = time.monotonic()
        self.assertEqual(self.call("slow", timeout=0.5)[0], "unreachable")
        self.assertLess(time.monotonic() - t0, 10)
        out = S.run_py(self.root, S.openai_setup(self.srv, self.cert) + r'''
pv._DIRECT["caller"] = pv.DirectCaller(base={"openai": a["base"]})       # the system's trust store: the test's cert isn't in it
try:
    pv._DIRECT["caller"].complete("openai", "fake-small", "Tidy.", a["key"]); print(json.dumps("sent"))
except pv.ProviderUnreachable as e:
    print(json.dumps("unreachable"))''')
        self.assertEqual(out, "unreachable")

    def test_too_much_or_a_bad_model_is_never_sent(self):
        for kw in ({"prompt": "x" * 16001}, {"prompt": ""}, {"model": "fake small; rm"}, {"provider": "claude"},
                   {"provider": "deepseek"}):
            out = self.call(**kw)
            self.assertEqual(out[0], "refused before sending", kw)
        self.assertEqual(self.call(key="bad key")[:2], ["refused", 400])
        self.assertEqual(self.srv.seen, [])

    def test_the_debug_log_has_host_status_and_counts_only(self):
        self.call(prompt="SECRET-PROMPT-WORDS")
        self.call("401", prompt="SECRET-PROMPT-WORDS")
        logs = "".join(f.read_text(encoding="utf-8") for f in (self.root / "system" / "logs").glob("debug-*.log"))
        self.assertIn("127.0.0.1 direct call: 200, 120 tokens in, 40 out", logs)
        self.assertIn("127.0.0.1 direct call: 401", logs)
        for x in (S.KEY, "fake-good", "SECRET-PROMPT-WORDS", "tidier"):
            self.assertNotIn(x, logs)

    def test_production_uses_the_one_host_and_tests_never_reach_it(self):
        out = S.run_py(self.root, r'''
import providers as pv
c = pv.DirectCaller()
pv._DIRECT.clear(); os.environ["CREAITE_FAKE_PROVIDERS"] = "1"; fake = type(pv.caller()).__name__
print(json.dumps({"base": c.base, "timeout": c.timeout, "cap": c.cap, "under the fakes": fake,
                  "verify": c.context.check_hostname}))''')
        self.assertEqual(out["base"], {"openai": "https://api.openai.com"})
        self.assertEqual((out["timeout"], out["cap"]), (30, 256000))
        self.assertEqual(out["under the fakes"], "NotBuiltCaller")
        self.assertTrue(out["verify"])


ROUTE = r'''
h = suggest(json.loads(%r))
print(json.dumps({"sent": h.sent, "events": h.events, "launched": launched}))'''


class Route(Base):
    def suggest(self, req, jobs=None, **more):
        out = self.run_in(ROUTE % json.dumps(req), jobs, **more)
        out["steps"] = [e["label"] for e in out["events"] or [] if e["type"] == "step"]
        out["draft"] = next((e for e in out["events"] or [] if e["type"] == "draft"), None)
        return out

    def test_clean_text_goes_to_openai_and_says_so(self):
        out = self.suggest({"text": CLEAN})
        self.assertEqual(out["launched"], [], "no claude -p")
        self.assertEqual(len(self.srv.seen), 1)
        sent = json.loads(self.srv.seen[0]["body"])["messages"][0]["content"]
        self.assertIn(CLEAN, sent)
        for word in ("Example Programme", "Omar Ali", "Sara Example", "ABC-A-"):
            self.assertNotIn(word, sent)
        self.assertEqual(out["steps"], ["Sent to OpenAI fake small: the selected text and the instruction only."])
        self.assertEqual((out["draft"]["text"], out["draft"]["made_by"]), ("A tidier sentence.", "OpenAI fake small"))
        logs = "".join(f.read_text(encoding="utf-8") for f in (self.root / "system" / "logs").glob("debug-*.log"))
        self.assertNotIn(S.KEY, logs)
        self.assertNotIn(CLEAN, logs)

    def test_text_that_isnt_clean_goes_to_claude_and_says_why(self):
        for text, why in (("See ABC-A-001 for the plan.", "This text holds an item ID, so it went to Claude, not OpenAI."),
                          ("Jane said the plan is fine.",
                           "This text holds a person or organisation creaite knows, so it went to Claude, not OpenAI."),
                          ("This is confidential.", "Confidential material is only ever sent to Claude. So Claude ran it.")):
            out = self.suggest({"text": text})
            self.assertEqual(len(out["launched"]), 1, text)
            self.assertEqual(out["steps"], [why], text)
            self.assertNotIn("made_by", out["draft"], text)
        self.assertEqual(self.srv.seen, [], "nothing reached the other provider")

    def test_the_free_instruction_goes_to_claude(self):
        out = self.suggest({"text": CLEAN, "option": "custom", "instruction": "Make it rhyme."})
        self.assertEqual(len(out["launched"]), 1)
        self.assertEqual(out["steps"], ["OpenAI isn't used for this option, so Claude ran it."])
        self.assertEqual(self.srv.seen, [])

    def test_at_the_defaults_nothing_changes(self):
        out = self.suggest({"text": CLEAN}, jobs={})
        self.assertEqual(len(out["launched"]), 1)
        self.assertEqual(out["steps"], [])
        self.assertNotIn("made_by", out["draft"])
        self.assertEqual(self.srv.seen, [])
        cmd = out["launched"][0]
        self.assertEqual(cmd[cmd.index("--model") + 1], "sonnet", "#126's pin, as today")

    def test_a_refused_key_ends_in_plain_words(self):
        self.srv.mode = "401"
        out = self.suggest({"text": CLEAN})
        errors = [e["message"] for e in out["events"] if e["type"] == "error"]
        self.assertEqual(errors, ["OpenAI did not accept this key (401). Check you copied all of it, and that it has not "
                                  "been revoked."])
        self.assertEqual(out["launched"], [], "never sent on to Claude by itself")
        self.assertNotIn(S.KEY, json.dumps(out))

    def test_the_client_place_reply_is_still_checked(self):
        out = self.run_in(r'''
import edit_ai
ctx = {"option": "shorter", "place": "client", "code": "ABC", "original": "A plain sentence for the client.", "people": [],
       "format": "markdown", "made_by": "OpenAI fake small"}
print(json.dumps(edit_ai.result({"context": ctx, "reply": "<<<SUGGESTION\nA plain sentence. See ABC-A-001.\nSUGGESTION>>>"})))''')
        self.assertEqual(out["text"], "")
        self.assertIn("isn't client-safe", out["message"])

    def test_stop_ends_a_slow_call(self):
        self.srv.mode = "slow"
        out = self.run_in(r'''
h = H()
t = threading.Thread(target=L.edit_ai_route, args=(h, {"option": "rewrite", "place": "notes", "code": "ABC", "text": a["text"]}))
t.start(); time.sleep(0.5)
r = L.current_run(); t0 = time.time(); r.request_stop(); t.join(10)
print(json.dumps({"took": time.time() - t0, "types": [e["type"] for e in h.events]}))''', text=CLEAN, timeout=10)
        self.assertLess(out["took"], 2.5, "Stop doesn't wait for the provider")
        self.assertIn("stopped", out["types"])
        self.assertNotIn("draft", out["types"])


if __name__ == "__main__":
    unittest.main()
