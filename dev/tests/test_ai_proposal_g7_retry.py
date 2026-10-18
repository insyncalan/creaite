"""#132 round 2, G7 (proposal, not applied): a quick edit whose fact check fails is tried once more, on a stronger model.

Run: python3 dev/tests/test_ai_proposal_g7_retry.py

Round 1 (all but G1c) and round 2 up to g7-quick-edit-retry.diff are applied to a throwaway vault with the fictional portfolio.
claude -p is a recorder answering one reply per launch; OpenAI is the test stand-in on a fake HTTPS server. No real Claude,
provider, key or network.

Done when:
- there is no retry at the default settings (quick edits and writing both run on Claude Sonnet), with no notes, or after one
  retry: never a loop;
- a retry goes to the writing kind's model only when it is stronger than the one that made the suggestion (at the defaults
  that is never: the page's "Claude Haiku" for quick edits is #126's Sonnet pin until G3's item 7 changes it); to Claude with the
  prompt Claude always gets (and --model set), to another provider only with outside_prompt and only for text the checks
  passed (text that isn't clean retries on Claude);
- the user sees a step saying it was tried once more and on which model, and the draft says which model made it (retried);
  a second suggestion that still loses a fact is shown with its notes; one that doesn't come back leaves the first;
- the second suggestion goes through the same checks: in the client place a reply with an item the client may not see is
  dropped, exactly as the first would be;
- a retry is not listed as a run and never starts a queued message.
"""
import json
import shutil
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ai_proposal_support as S  # noqa: E402

OPENSSL = shutil.which("openssl")
TEXT = "Send the plan by 12-11-2026, with 3 options."
LOSES = "<<<SUGGESTION\nSend the plan soon, with some options.\nSUGGESTION>>>"
KEEPS = "<<<SUGGESTION\nSend the plan, with 3 options, by 12-11-2026.\nSUGGESTION>>>"

PLAN = r'''
pv.LIMIT.clear()
got = {"notes": [{"id": "dates-lost", "note": "x"}]}
ctx = {"option": "rewrite", "place": "notes", "code": "ABC", "original": a["text"], "prompt": "CLAUDE PROMPT"}
plans = {}
for name, c, g, first in (("default", ctx, got, None), ("no notes", ctx, {"notes": []}, "haiku"),
                          ("retried", dict(ctx, retried=True), got, "haiku"), ("from haiku", ctx, got, "haiku"),
                          ("from openai", dict(ctx, made_by_id="openai:fake-small"), got, None),
                          ("not clean", dict(ctx, original="See ABC-A-001 by 12-11-2026."), got, "haiku")):
    p = L.retry_plan(c, g, first)
    plans[name] = p and {"route": {k: (v if k != "direct" else "a direct call") for k, v in p["route"].items()},
                         "prompt": p["prompt"], "made_by": p["made_by"]}
print(json.dumps(plans))'''

SUGGEST = r'''
h = suggest({"text": a["text"]})
print(json.dumps({"events": h.events, "launched": launched, "runs": list(L.RUNS)}))'''


@unittest.skipUnless(OPENSSL, "needs openssl to make the fake provider's certificate")
class Retry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = S.populated(S.vault2("g7-quick-edit-retry"))
        cls.tmp, cls.cert, cls.key = S.make_cert()
        cls.srv = S.chat_server(cls.cert, cls.key)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        self.srv.seen.clear()
        self.srv.reply = KEEPS

    def run_in(self, code, jobs=None, **more):
        return S.run_py(self.root, S.openai_setup(self.srv, self.cert, jobs or {}, text=TEXT, **more) + code)

    def suggest(self, jobs=None, **more):
        out = self.run_in(SUGGEST, jobs, **more)
        out["steps"] = [e["label"] for e in out["events"] if e["type"] == "step"]
        out["draft"] = next((e for e in out["events"] if e["type"] == "draft"), None)
        return out

    def test_when_a_retry_is_planned(self):
        at_default = self.run_in(PLAN)
        self.assertIsNone(at_default["default"], "Sonnet to Sonnet: nothing stronger, so no retry, as today")
        opus = self.run_in(PLAN, {"write": "claude:opus"})
        self.assertEqual(opus["default"], {"route": {"alias": "opus", "nested": True}, "prompt": "CLAUDE PROMPT",
                                           "made_by": "Claude Opus 5.5"}, "#126's Sonnet pin, then Opus for writing")
        self.assertIsNone(opus["no notes"])
        self.assertIsNone(opus["retried"], "one retry at most")
        self.assertEqual(opus["from openai"]["route"], {"alias": "opus", "nested": True}, "OpenAI's small model to Opus")
        to_openai = self.run_in(PLAN, {"write": "openai:fake-flagship"})
        self.assertEqual(to_openai["default"]["route"], {"direct": "a direct call", "nested": True})
        self.assertNotIn("CLAUDE PROMPT", to_openai["default"]["prompt"], "another provider gets outside_prompt only")
        self.assertIn(TEXT, to_openai["default"]["prompt"])
        self.assertEqual(to_openai["not clean"]["route"], {"alias": "sonnet", "nested": True},
                         "text that isn't clean retries on Claude's recommended writing model, never on OpenAI")

    def test_a_lost_fact_is_tried_once_more_on_claude_opus(self):
        out = self.suggest({"write": "claude:opus"}, claude_reply=[LOSES, KEEPS])
        self.assertEqual(len(out["launched"]), 2)
        first, second = out["launched"]
        self.assertEqual(first[first.index("--model") + 1], "sonnet")
        self.assertEqual(second[second.index("--model") + 1], "opus")
        self.assertEqual(second[:second.index("--model")], first[:first.index("--model")], "the same launch, but the model")
        self.assertEqual(out["steps"], ["The check found a changed fact, so this was tried once more on Claude Opus 5.5."])
        self.assertEqual(out["draft"]["text"], "Send the plan, with 3 options, by 12-11-2026.")
        self.assertEqual((out["draft"]["made_by"], out["draft"]["retried"], out["draft"]["notes"]),
                         ("Claude Opus 5.5", True, []))
        self.assertEqual(len(out["runs"]), 1, "the retry isn't listed as a run")

    def test_never_a_loop_and_a_failing_second_is_shown_with_its_notes(self):
        out = self.suggest({"write": "claude:opus"}, claude_reply=[LOSES, LOSES, KEEPS])
        self.assertEqual(len(out["launched"]), 2, "one retry, never a third")
        self.assertTrue(out["draft"]["notes"])
        self.assertTrue(out["draft"]["retried"])

    def test_a_second_that_doesnt_come_back_leaves_the_first(self):
        out = self.suggest({"write": "claude:opus"}, claude_reply=[LOSES, ""])
        self.assertEqual(out["steps"][-1], "The second try didn't give a suggestion, so the first is shown with its notes.")
        self.assertEqual(out["draft"]["text"], "Send the plan soon, with some options.")
        self.assertNotIn("retried", out["draft"])

    def test_a_retry_on_openai_sends_only_the_selection(self):
        out = self.suggest({"write": "openai:fake-flagship"}, claude_reply=[LOSES])
        self.assertEqual(len(out["launched"]), 1)
        self.assertEqual(len(self.srv.seen), 1)
        body = json.loads(self.srv.seen[0]["body"])
        self.assertEqual(body["model"], "fake-flagship")
        sent = body["messages"][0]["content"]
        self.assertIn(TEXT, sent)
        for word in ("Example Programme", "Omar Ali", "Its people"):
            self.assertNotIn(word, sent)
        self.assertEqual(out["draft"]["made_by"], "OpenAI fake flagship")

    def test_the_first_model_is_the_one_the_run_used(self):
        same = self.suggest({"quick": "claude:opus", "write": "claude:opus"}, claude_reply=[LOSES, KEEPS])
        self.assertEqual(len(same["launched"]), 1, "Opus made it: Opus for writing is not stronger, so no retry")
        self.srv.reply = LOSES
        from_openai = self.suggest({"quick": "openai:fake-small", "write": "claude:sonnet"}, claude_reply=[KEEPS])
        self.assertEqual(len(self.srv.seen), 1)
        self.assertEqual(len(from_openai["launched"]), 1, "OpenAI's small model made it: Sonnet is stronger, so one retry")
        self.assertEqual(from_openai["draft"]["made_by"], "Claude Sonnet 5.5")

    def test_a_retry_never_starts_a_queued_message(self):
        out = self.run_in(r'''
calls = []
real = L.queue_after
L.queue_after = lambda run: calls.append(run.id) or real(run)
h = suggest({"text": a["text"]})
print(json.dumps({"calls": calls, "launched": len(launched)}))''', {"write": "claude:opus"}, claude_reply=[LOSES, KEEPS])
        self.assertEqual(out["launched"], 2)
        self.assertEqual(len(out["calls"]), 1, "only the suggestion's own run, never its retry")
        self.assertFalse(out["calls"][0].endswith("-retry"))

    def test_no_retry_at_the_defaults(self):
        out = self.suggest(claude_reply=[LOSES, KEEPS])
        self.assertEqual(len(out["launched"]), 1)
        self.assertEqual(out["steps"], [])
        self.assertTrue(out["draft"]["notes"], "shown with its notes, as today")

    def test_the_client_check_is_never_relaxed_on_the_retry(self):
        out = self.run_in(r'''
import edit_ai
ctx = {"option": "shorter", "place": "client", "code": "ABC", "original": a["text"], "people": [], "format": "markdown",
       "prompt": "CLAUDE PROMPT"}
class FakeRun:
    id, stop, alias, said = "e-client-retry-01", False, None, []
    def __init__(self): self.events = []
    def emit(self, kind, **d): self.events.append(dict(d, type=kind))
job = L.EditJob({}, ctx); job.run = FakeRun()
first = job.checked(a["first"], ctx)
second = job.again(first)
print(json.dumps({"first": first, "second": second, "launched": len(launched), "steps": job.run.events}))''',
                          {"write": "claude:opus"}, first=LOSES,
                          claude_reply=["<<<SUGGESTION\nSend the plan, with 3 options, by 12-11-2026. See ABC-A-001.\n"
                                        "SUGGESTION>>>"])
        self.assertTrue(out["first"]["notes"])
        self.assertEqual(out["launched"], 1, "the retry ran")
        self.assertEqual(out["second"], out["first"], "the second held an item the client may not see: never shown")
        self.assertNotIn("ABC-A-001", json.dumps(out["second"]))
        self.assertEqual(out["steps"][-1]["label"], "The second try was dropped by the checks, so the first is shown with its notes.")


if __name__ == "__main__":
    unittest.main()
