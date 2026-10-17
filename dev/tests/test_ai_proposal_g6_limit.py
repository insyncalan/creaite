"""#132 round 2, G6 (proposal, not applied): Claude's limit, seen in a run's stream, and the Ask me card.

Run: python3 dev/tests/test_ai_proposal_g6_limit.py

Round 1 (all but G1c), g4-direct-call.diff and g6-limit-card.diff are applied to a throwaway vault with the fictional portfolio.
claude -p is a recorder that answers with the stream Claude Code 2.1.288 gives at a limit (a rate_limit_event with status
"rejected", an assistant message with error "rate_limit", a result with is_error); OpenAI is the test stand-in on a fake HTTPS
server. No real Claude, provider, key or network.

Done when:
- providers.limit_signal reads the three signals (and "clear" from an allowed event or a good result), and nothing else;
- a run that hits the limit ends with one card in the chat's existing "cant" event (the reset time, what ai.on_limit does next,
  Open AI models) and an error with the same words; it is never retried (one launch), and its words are never a suggestion;
- Ask me offers "Run this one on <another model>" only for AI on selected text with another provider connected; the page's
  limit_choice "other" then routes this one request there, and only while the limit holds; text that isn't clean still goes
  to Claude (G5, G4's checks); another connected model (on_limit "other") does the same without asking; Step down runs writing
  on the quick-edit model and the run says so; a later good result clears the limit; the VIP check skips while it holds.
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
RESETS = int(time.time()) + 3600
LIMIT_STREAM = [{"type": "system", "subtype": "init", "session_id": "s-limit"},
                {"type": "rate_limit_event", "session_id": "s-limit", "uuid": "u1",
                 "rate_limit_info": {"status": "rejected", "resetsAt": RESETS, "rateLimitType": "five_hour"}},
                {"type": "assistant", "error": "rate_limit",
                 "message": {"content": [{"type": "text", "text": "You've hit your limit · resets 3pm"}]}},
                {"type": "result", "subtype": "success", "is_error": True, "result": "You've hit your limit · resets 3pm"}]


class Signal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = S.vault2("g6-limit-card")

    def test_the_three_signals_and_clear(self):
        out = S.run_py(self.root, r'''
import providers as pv
cases = [
 {"type": "rate_limit_event", "rate_limit_info": {"status": "rejected", "resetsAt": 1800000000, "rateLimitType": "seven_day_opus"}},
 {"type": "rate_limit_event", "rate_limit_info": {"status": "rejected"}},
 {"type": "rate_limit_event", "rate_limit_info": {"status": "allowed_warning", "resetsAt": 1800000000}},
 {"type": "rate_limit_event", "rate_limit_info": {"status": "allowed"}},
 {"type": "assistant", "error": "rate_limit", "message": {"content": []}},
 {"type": "assistant", "error": "overloaded", "message": {"content": []}},
 {"type": "result", "is_error": True, "result": "You've hit your limit · resets 3pm (Europe/London)"},
 {"type": "result", "is_error": True, "result": "Claude AI usage limit reached|1760000000"},
 {"type": "result", "is_error": True, "result": "API Error: 500"},
 {"type": "result", "is_error": False, "result": "You've hit your limit is what the text says"},
 {"type": "user", "message": {"content": "You've hit your limit"}}, "not an event", {"type": "rate_limit_event"}]
print(json.dumps([pv.limit_signal(c) for c in cases]))''')
        self.assertEqual(out, [{"resets": 1800000000, "kind": "seven_day_opus"}, {"resets": None, "kind": ""}, "clear", "clear",
                               {"resets": None, "kind": ""}, None, {"resets": None, "kind": ""}, {"resets": None, "kind": ""},
                               None, "clear", None, None, "clear"])

    def test_seen_held_cleared_and_said(self):
        out = S.run_py(self.root, r'''
import providers as pv
from datetime import datetime
now = datetime(2026, 10, 17, 12, 0).timestamp()
r = {}
pv.limit_seen({"type": "rate_limit_event", "rate_limit_info": {"status": "rejected", "resetsAt": now + 3 * 3600}}, now)
r["held"], r["words"] = pv.limited_now(now + 60), pv.reset_words(pv.LIMIT["resets"], now)
r["after reset"] = pv.limited_now(now + 3 * 3600 + 1)
pv.limit_seen({"type": "result", "is_error": False, "result": "ok"}, now)
r["cleared"] = pv.limited_now(now + 60)
pv.limit_seen({"type": "assistant", "error": "rate_limit"}, now)
r["unknown"] = [pv.limited_now(now + 60), pv.limited_now(now + pv.LIMIT_UNKNOWN + 1), pv.LIMIT["resets"]]
r["tomorrow"] = pv.reset_words(datetime(2026, 10, 18, 9, 0).timestamp(), now)
print(json.dumps(r))''')
        self.assertEqual((out["held"], out["words"], out["after reset"], out["cleared"]), (True, "at 15:00", False, False))
        self.assertEqual(out["unknown"], [True, False, None], "no reset time: assumed for 15 minutes, and said to be unknown")
        self.assertEqual(out["tomorrow"], "on 18-10-2026 at 09:00")

    def test_the_card_per_choice(self):
        out = S.run_py(self.root, r'''
import providers as pv, settings_catalogue as sc
cfg = json.loads(json.dumps(sc.defaults()))
pv.LIMIT.update(resets=None, until=9e12, kind="")
none = {m: [pv.limit_card(j, pv.with_choice(cfg, m), f) for j, f in (("tools", ""), ("write", ""), ("quick", "edit-ai"))]
        for m in ("ask", "other", "step_down")}
cfg["ai"]["providers"] = pv.connect_changes("openai", ["fake-flagship", "fake-small"], ["fake-flagship", "fake-small"],
                                           cfg)["ai.providers"]
store = pv.MemoryStore(); store.put("openai", "x"); pv._BACKEND["pair"] = (store, pv.FakeLister())
two = {m: [pv.limit_card(j, pv.with_choice(cfg, m), f) for j, f in (("tools", ""), ("write", ""), ("quick", "edit-ai"),
                                                                     ("quick", ""))] for m in ("ask", "other", "step_down")}
print(json.dumps({"none": none, "two": two}))''')
        head = "Claude's limit is reached, and it didn't say when it resets. Nothing was changed."
        for mode, cards in out["none"].items():
            self.assertTrue(all(c["offer"] is None for c in cards), mode)
        self.assertEqual(out["none"]["ask"][0]["line"], head + " Jobs that use tools wait: try again then.")
        self.assertEqual(out["none"]["ask"][2]["line"], head + " Try again then.")
        self.assertEqual(out["none"]["step_down"][1]["line"],
                         head + " Writing runs as a quick edit until then: try again to run it on Claude Haiku 5.5.")
        ask = out["two"]["ask"]
        self.assertEqual([c["offer"] for c in ask], [None, None, {"choice": "other", "label": "Run this one on OpenAI fake flagship"},
                                                     None], "offered only for AI on selected text, never a tools job")
        self.assertEqual(ask[2]["line"], head)
        self.assertEqual(out["two"]["other"][2]["line"],
                         head + " Try again to run it on OpenAI fake flagship, unless it holds confidential material.")
        self.assertEqual(out["two"]["other"][0]["line"], head + " Jobs that use tools wait: try again then.")
        self.assertTrue(all(c["offer"] is None for m in ("other", "step_down") for c in out["two"][m]))


@unittest.skipUnless(OPENSSL, "needs openssl to make the fake provider's certificate")
class Runs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = S.populated(S.vault2("g6-limit-card"))
        cls.tmp, cls.cert, cls.key = S.make_cert()
        cls.srv = S.chat_server(cls.cert, cls.key)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        self.srv.seen.clear()

    def run_in(self, code, jobs=None, **more):
        more.setdefault("claude_reply", [LIMIT_STREAM])
        return S.run_py(self.root, S.openai_setup(self.srv, self.cert, jobs or {}, **more) + code)

    def test_a_chat_at_the_limit_gets_one_card_and_no_retry(self):
        out = self.run_in(r'''
r = L.Run("r-limit-chat-01", "What's overdue on ABC?", None, None, None)
end = time.time() + 20
while not r.done and time.time() < end: time.sleep(0.05)
print(json.dumps({"events": r.events, "launched": len(launched), "held": pv.limited_now()}))''')
        cards = [e for e in out["events"] if e["type"] == "cant"]
        self.assertEqual(len(cards), 1)
        when = time.strftime("%H:%M", time.localtime(RESETS))
        self.assertEqual(cards[0]["what"], "limit")
        self.assertTrue(cards[0]["line"].startswith(f"Claude's limit is reached; it resets at {when}. Nothing was changed."),
                        cards[0]["line"])
        self.assertEqual(cards[0]["go"], {"page": "settings", "arg": "aiModels", "label": "Open AI models"})
        self.assertIsNone(cards[0]["offer"])
        self.assertIn({"type": "error", "message": cards[0]["line"]}, out["events"])
        self.assertEqual(out["launched"], 1, "never retried by itself")
        self.assertTrue(out["held"])
        logs = "".join(f.read_text(encoding="utf-8") for f in (self.root / "system" / "logs").glob("debug-*.log"))
        at = time.strftime("%Y-%m-%dT%H:%M", time.localtime(RESETS))
        self.assertIn(f"r-limit-chat-01 ask: Claude's limit (five_hour), resets {at}", logs)

    def test_a_suggestion_at_the_limit_offers_another_model_and_its_words_are_never_a_draft(self):
        out = self.run_in(r'''
h = suggest({"text": a["text"]})
print(json.dumps({"events": h.events, "launched": len(launched)}))''', text=CLEAN)
        types = [e["type"] for e in out["events"]]
        self.assertNotIn("draft", types, "the limit's words are never a suggestion")
        card = next(e for e in out["events"] if e["type"] == "cant")
        self.assertEqual(card["offer"], {"choice": "other", "label": "Run this one on OpenAI fake flagship"})
        self.assertEqual(out["launched"], 1)
        self.assertEqual(self.srv.seen, [], "nothing goes to OpenAI until Alan presses the card's button")

    def test_the_ask_me_choice_runs_this_one_on_the_other_model_only_while_the_limit_holds(self):
        out = self.run_in(r'''
h1 = suggest({"text": a["text"]})                                   # hits the limit: the card
h2 = suggest({"text": a["text"], "limit_choice": "other"})          # Alan presses "Run this one on OpenAI fake flagship"
h3 = suggest({"text": "See ABC-A-001 for the plan.", "limit_choice": "other"})   # not clean: still Claude's
pv.LIMIT.clear()
h4 = suggest({"text": a["text"], "limit_choice": "other"})          # no limit now: the choice is ignored
pick = lambda h: [e for e in h.events if e["type"] in ("step", "draft")]
print(json.dumps({"h2": pick(h2), "h3": pick(h3), "h4": pick(h4), "launched": len(launched)}))''', text=CLEAN,
                          claude_reply=[LIMIT_STREAM, LIMIT_STREAM, "<<<SUGGESTION\nClaude's.\nSUGGESTION>>>"])
        self.assertEqual(out["h2"][0]["label"], "Sent to OpenAI fake flagship: the selected text and the instruction only.")
        self.assertEqual(out["h2"][1]["made_by"], "OpenAI fake flagship")
        self.assertEqual(len(self.srv.seen), 1, "only h2 reached OpenAI")
        self.assertEqual(json.loads(self.srv.seen[0]["body"])["model"], "fake-flagship")
        self.assertIn("This text holds an item ID", out["h3"][0]["label"])
        self.assertEqual(out["launched"], 3, "h1, h3 and h4 ran on Claude")
        self.assertEqual([e["type"] for e in out["h4"]], ["draft"])
        self.assertNotIn("made_by", out["h4"][0])

    def test_another_connected_model_without_asking_but_never_confidential(self):
        out = self.run_in(r'''
pv.LIMIT.update(resets=None, until=time.time() + 600, kind="")
h1 = suggest({"text": a["text"]})
h2 = suggest({"text": "This is confidential: the budget."})
pick = lambda h: [e["label"] for e in h.events if e["type"] == "step"]
print(json.dumps({"h1": pick(h1), "h2": pick(h2), "launched": len(launched)}))''', text=CLEAN, on_limit="other")
        self.assertEqual(out["h1"], ["Sent to OpenAI fake flagship: the selected text and the instruction only."])
        self.assertEqual(out["h2"], ["Confidential material is only ever sent to Claude. So Claude ran it."])
        self.assertEqual(out["launched"], 1)
        self.assertEqual(len(self.srv.seen), 1)

    def test_step_down_says_so_and_a_good_result_clears_the_limit(self):
        out = self.run_in(r'''
pv.LIMIT.update(resets=None, until=time.time() + 600, kind="")
res = {"generate": list(L.run_model("generate")), "ask": list(L.run_model("ask"))}
r = L.Run("r-limit-clear-01", "Hello", None, None, None)
end = time.time() + 20
while not r.done and time.time() < end: time.sleep(0.05)
res["held after a good run"] = pv.limited_now()
print(json.dumps(res))''', jobs={"quick": "claude:haiku"}, on_limit="step_down",
                          claude_reply=["All fine."])
        self.assertEqual(out["generate"], ["haiku", "Claude's limit is reached, so this ran as a quick edit on Claude Haiku 5.5 "
                                                    "(Step down one kind)."])
        self.assertEqual(out["ask"], [None, ""], "a tools job waits: no model, no step (its run shows the card)")
        self.assertFalse(out["held after a good run"])

    def test_the_vip_check_skips_while_the_limit_holds(self):
        out = self.run_in(r'''
r = {"before": L.vip_limited()}
r["seen"] = L.vip_limited(json.dumps({"type": "result", "is_error": True, "result": "You've hit your limit · resets 3pm"}))
r["unreadable"] = L.vip_limited("not json")
print(json.dumps(r))''')
        self.assertEqual(out, {"before": False, "seen": True, "unreadable": True})
        src = (self.root / "system" / "scripts" / "live_server.py").read_text(encoding="utf-8")
        self.assertIn("            vip_limited(r.stdout)                                                                # #132 G6\n"
                      "            found, why, cost = vip_reply(r)", src, "the check's own reply is read for the limit")
        self.assertIn('    if vip_limited():                                     # #132 G6: no call while Claude\'s limit holds\n'
                      '        return "skipped: Claude\'s limit is reached"', src)


if __name__ == "__main__":
    unittest.main()
