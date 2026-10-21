"""#272: Suggest says nothing rather than writing the model's refusal into the field.

When a Suggest draft (a risk's response, a decision's reasoning or options, an action's latest update, Sneak peek's update) has
nothing to base a suggestion on, the prompt asks for exactly NO_SUGGESTION; drafts.py treats that, and a reply whose first sentence
reads as a refusal ("No passage … was supplied, so I can't suggest …"), as Nothing: no draft, a plain note naming what it would have
drawn on, and draft-stats.json counts it as "nothing" (never "offered" or "used"). In the peek nothing is written to the field and
the note shows under the button, until the next action.

Run: python3 dev/tests/test_suggest_nothing_272.py   (the browser test needs Google Chrome; skipped otherwise)
Claude is a stand-in that answers with the reply the test wrote beside it; no model is called.
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import drafts_fake  # noqa: E402
from test_tracker import Vault  # noqa: E402
from test_drafts_update import DraftCase  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "system/scripts"))
import drafts  # noqa: E402

REFUSAL = ("No passage or closed-risk response was supplied, so I can't suggest a specific action. Jane Doe, as owner, should set out "
           "the response from the Programme board minutes of 15-10-2026.")
SRC = [{"id": "ABC-R-001", "kind": "source", "text": "Its source: Programme board minutes", "ref": "S1"}]


def ctx(kind, table="raid", field="response_action", **item):
    return {"kind": kind, "feature": drafts.KINDS[kind][0], "sources": SRC, "item": {"id": "ABC-R-001", "table": table, "field": field, **item}}


RISK = ctx("thinking")
REASONING = ctx("thinking", "decisions", "reasoning")
OPTIONS = ctx("thinking", "decisions", "options")
UPDATE = ctx("update", "actions", None, since="2026-10-01")
SNEAK = ctx("sneak-update", "actions", None, mode="tidy")
ALL = (RISK, REASONING, OPTIONS, UPDATE, SNEAK)

# Replies that read as a refusal: each must come back as Nothing, for every Suggest kind.
REFUSALS = [
    REFUSAL,
    "RESPONSE: No passage or closed-risk response was supplied, so I can't suggest a specific action.\nIMPACT: Medium | unknown [S1]",
    "I can't suggest a response from these sources. [S1]",
    "I cannot suggest the reasoning: the passage doesn't cover it.",
    "I'm unable to suggest an update from what was given.",
    "I don't have enough information to suggest a response.",
    "There is not enough information to suggest a response. [S1]",
    "Not enough information to draft an update.",
    "The passage doesn't say.",
    "The sources do not give the options considered.",
    "There is no meeting passage to base a suggestion on.",
    "There is nothing in the sources about the reasoning.",
    "Nothing to suggest from the sources given.",
    "As an AI, I can only work from the sources, and they say nothing about it.",
    "Unable to suggest a response: no source was provided.",
    "Sorry, I can't draft an update here.",
    "- I can't suggest options from this passage.",
]
# Real suggestions, some with refusal-like words later on or about someone else: none may be caught.
REAL = [
    "Escalate to the client CIO and test on masked data meanwhile. [S1]",
    "There is no fallback supplier, so line one up with a short contract. [S1]",
    "The vendor is unable to provide test data until May; agree masked data with the client. [S1]",
    "Test data was not provided by the client, so UAT is delayed by a week. [S1]",
    "Jane Doe said she can't make Friday, so the review moves to Monday. [S1]",
    "The vendor has not given enough information to plan the cut-over; chase them this week. [S1]",
    "The team cannot finish testing until data access is granted. [S1]",
    "Line up a second supplier. [S1] If that isn't possible, I can't see another route, so escalate. [S1]",
    "Raised again at the weekly sync; there is no date yet. [S1]",
    "Agree a short extension with the supplier while the contract is renegotiated, as the closed risk did. [S1] Not enough testers "
    "are free in November, so book them now. [S1]",
    "Treat the vendor as an AI partner for the pilot and review in December. [S1]",
    "The contract doesn't say who pays for the extension; agree it with legal. [S1]",
    # v2.6 review: a real suggestion that opens with "I can't give/say…" and then gives a usable body
    "I can't give a firm date, but the vendor has committed to the end of November, so plan UAT for December. [S1]",
    "I can't say for certain, however escalating to the client CIO this week is the safest route. [S2]",
    "I can't say when the vendor will deliver. Escalate to the client CIO and test on masked data meanwhile. [S1]",
]
SENTINELS = ["NO_SUGGESTION", "  NO_SUGGESTION\n", "`NO_SUGGESTION`", "```\nNO_SUGGESTION\n```", '"NO_SUGGESTION"', "NO_SUGGESTION.",
             "RESPONSE: NO_SUGGESTION", "REASONING:\nNO_SUGGESTION", "**NO_SUGGESTION**"]


class Rule(unittest.TestCase):
    def test_a_refusal_is_nothing_for_every_suggest_kind(self):
        for c in ALL:
            for reply in REFUSALS:
                with self.subTest(kind=c["kind"], field=c["item"]["field"], reply=reply):
                    out = drafts.result({}, c, reply)
                    self.assertTrue(out.get("nothing"), out)
                    self.assertEqual(out["text"], "")
                    self.assertEqual(out["sentences"], [])

    def test_the_sentinel_is_nothing_however_it_is_wrapped(self):
        for c in ALL:
            for reply in SENTINELS:
                with self.subTest(kind=c["kind"], reply=reply):
                    out = drafts.result({}, c, reply)
                    self.assertTrue(out.get("nothing"), out)
                    self.assertEqual(out["text"], "")

    def test_the_sentinel_is_case_sensitive_and_must_stand_alone(self):
        for reply in ("no_suggestion", "NO_SUGGESTION: the passage is about something else, but escalate anyway."):
            self.assertFalse(drafts.result({}, RISK, reply).get("nothing"), reply)

    def test_real_suggestions_pass(self):
        for c in ALL:
            for reply in REAL:
                with self.subTest(kind=c["kind"], reply=reply):
                    out = drafts.result({}, c, reply)
                    self.assertFalse(out.get("nothing"), out)
                    self.assertTrue(out["text"])

    def test_the_note_names_what_each_kind_would_have_drawn_on(self):
        say = lambda c: drafts.result({}, c, "NO_SUGGESTION")["nothing"]  # noqa: E731
        self.assertEqual(say(RISK), "Nothing to suggest from: no meeting passage and no closed risks with a response")
        self.assertEqual(say(REASONING), "Nothing to suggest from: no meeting passage gives the reasoning")
        self.assertEqual(say(OPTIONS), "Nothing to suggest from: no meeting passage gives the options considered")
        self.assertEqual(say(UPDATE), "Nothing to draft from: nothing since 01-10-2026 says where the action stands")
        self.assertIn("Nothing to draft from", say(SNEAK))

    def test_other_kinds_are_left_as_they_were(self):
        c = {"kind": "health", "feature": "reason", "sources": SRC, "item": {}}
        self.assertFalse(drafts.result({}, c, "I can't suggest a reason.").get("nothing"))

    def test_every_suggest_prompt_carries_the_contract(self):
        for name in ("thinking-response", "thinking-decision", "update", "sneak-update"):
            text = (REPO / f"system/templates/drafts/{name}.md").read_text(encoding="utf-8")
            with self.subTest(template=name):
                self.assertIn("reply with exactly NO_SUGGESTION and nothing else", text)
        self.assertNotIn("The passage doesn't say.", (REPO / "system/templates/drafts/thinking-decision.md").read_text(encoding="utf-8"))


class Counts(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.cleanup)

    def result(self, reply):
        r = subprocess.run([sys.executable, str(self.v.root / "system/scripts/drafts.py"), "result"], cwd=self.v.root,
                           capture_output=True, text=True, input=json.dumps({"request": {}, "context": RISK, "reply": reply}))
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_nothing_is_counted_as_nothing_never_offered_or_used(self):
        out = self.result(REFUSAL)
        self.assertTrue(out["nothing"])
        stats = json.loads((self.v.root / "system/staging/draft-stats.json").read_text())
        self.assertEqual(stats["thinking"], {"offered": 0, "used": 0, "edited": 0, "rejected": 0, "nothing": 1})
        self.result("Escalate to the client CIO. [S1]")
        stats = json.loads((self.v.root / "system/staging/draft-stats.json").read_text())
        self.assertEqual(stats["thinking"]["offered"], 1)
        self.assertEqual(stats["thinking"]["nothing"], 1)

    def test_the_closure_line_says_nothing_was_suggested(self):
        line = drafts.run_closure({"run": {"done": "Suggested the thinking fields"}}, drafts.result({}, RISK, REFUSAL))
        self.assertEqual(line["line"], "Nothing to suggest from: no meeting passage and no closed risks with a response")


FAKE = r'''#!/usr/bin/env python3
import json, sys
args = sys.argv[1:]
p = args[args.index("--") + 1]
open(__file__ + ".prompt", "w", encoding="utf-8").write(p)
reply = open(__file__ + ".reply", encoding="utf-8").read()
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init", "session_id": "sess-n"})
out({"type": "assistant", "message": {"content": [{"type": "text", "text": reply}]}})
out({"type": "result", "result": reply, "session_id": "sess-n"})
'''
NOTES = f"{drafts_fake.ABC}/minutes/2026-10-15 Programme board.md"


class Peek(DraftCase):
    """The peek on a risk: Suggest with a refusal reply leaves the field as it was and shows the note under the button."""

    @classmethod
    def load(cls, v):
        drafts_fake.load(v)
        (v.root / NOTES).write_text("# Programme board\n\nThe courier contract may lapse before go-live.\n")
        v.propose("r272", [{"n": 1, "op": "new", "table": "raid", "match": "strong", "flags": [], "decision": "approved",
                            "values": {"project": "ABC", "type": "Risk", "description": "The courier contract may lapse before go-live",
                                       "impact": "Medium", "likelihood": "Low", "raised": "2026-10-15",
                                       "response_action": "Keep the current courier on a rolling month", "source": f"{NOTES} — Risks"}}])
        v.run("apply")
        cls.fake = v.root / "fake_claude.py"
        cls.fake.write_text(FAKE)
        cls.fake.chmod(0o755)

    def reply(self, text):
        Path(str(self.fake) + ".reply").write_text(text, encoding="utf-8")

    def risk(self):
        import sqlite3
        con = sqlite3.connect(self.v.root / "system/tracker.db")
        try:
            return con.execute("SELECT id, response_action FROM raid WHERE description LIKE 'The courier contract%'").fetchone()
        finally:
            con.close()

    def test_a_refusal_writes_nothing_and_shows_the_note_until_the_next_action(self):
        rid, before = self.risk()
        self.reply(REFUSAL)
        b = self.b
        b.eval(f"openRecord('raid','{rid}')")
        b.wait("document.querySelector('#pkDescDr [data-draft=thinking][data-drf=resp]')")
        field = "document.getElementById('pkDesc').textContent"
        self.assertEqual(b.eval(field), before)
        b.click("#pkDescDr [data-draft=thinking]")
        b.wait("document.querySelector('#pkAiDraft .drnone')", 30)
        self.assertEqual(b.eval("document.querySelector('#pkAiDraft .drnone').innerText").strip(),
                         "Nothing to suggest from: no meeting passage and no closed risks with a response")
        self.assertIsNone(b.eval("document.querySelector('#pkAiDraft .drcard')"))
        self.assertEqual(b.eval(field), before)                                          # the field is as it was
        self.assertNotIn("can't suggest", b.eval("document.getElementById('panel').innerText"))
        self.assertEqual(b.eval("PKS.length"), 0)                                         # nothing staged
        self.assertEqual(self.risk()[1], before)
        self.assertEqual(self.stats()["thinking"].get("nothing"), 1)
        self.assertEqual(self.stats()["thinking"]["offered"], 0)
        b.eval("document.getElementById('pkDesc').dispatchEvent(new InputEvent('input',{bubbles:true}))")   # the next action
        b.wait("!document.querySelector('#pkAiDraft .drnone')")
        self.assertEqual(b.errors, [])

    def test_the_sentinel_writes_nothing_either(self):
        rid, before = self.risk()
        self.reply("NO_SUGGESTION")
        b = self.b
        b.eval(f"openRecord('raid','{rid}')")
        b.wait("document.querySelector('#pkDescDr [data-draft=thinking][data-drf=resp]')")
        b.click("#pkDescDr [data-draft=thinking]")
        b.wait("document.querySelector('#pkAiDraft .drnone')", 30)
        self.assertEqual(b.eval("document.getElementById('pkDesc').textContent"), before)
        self.assertEqual(b.errors, [])


if __name__ == "__main__":
    unittest.main()
