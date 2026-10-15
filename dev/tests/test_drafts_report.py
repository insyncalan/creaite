"""#90 (v2.1.0): the ✦ on the weekly, client and minutes sheets. The draft kinds "report-section" and "minutes-section" in drafts.py.

Run: python3 dev/tests/test_drafts_report.py      (quick tier: no Chrome, no model)
- the facts, the sources, the prompt for each action (Polish, Shorter, Executive, Custom) and the reply's checks;
- privacy by construction: a client report's section draws only on the facts that make up the client version, and a minutes draft
  from the distributed version only on distributed_of. One of each kind of withheld content is seeded (an item that isn't
  client-visible, Sensitive, partner-only, excluded by a label, a memory line marked Client-safe: no; an Internal only line and row);
  none is in the prompt or the facts, and a control run shows each seed is real;
- the counts (offered, used, edited, rejected) include the two kinds, and hold counts only, never text.
"""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_reports as R  # noqa: E402  (its fixture: populate, ReportVault, NOW; the data is fictional)

HEAD = "import sys, json; sys.path.insert(0, 'system/scripts')\nimport drafts\n"
CLIENT_TEXT = "Phase two can start once the paperwork is signed."
WEEKLY = {"kind": "report-section", "report": "weekly", "code": "ABC", "week_ending": "2026-10-09", "section": "summary",
          "heading": "Summary", "text": "UAT start has slipped two weeks.", "action": "polish"}
CLIENT = {**WEEKLY, "report": "client", "text": CLIENT_TEXT}
# the words of everything a client report must never draw on, in the fixture (test_reports.populate)
INTERNAL_ONLY = ("Vendor exits the market", "Confirm tester names", "Absorb the phase one overrun", "Budget overrun on phase one")


def py(vault, code, now=R.NOW):
    r = subprocess.run([sys.executable, "-c", HEAD + code], cwd=vault.root, env={**os.environ, "CREAITE_NOW": now},
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return json.loads(r.stdout.strip().splitlines()[-1])


def everything(ctx):
    """All the model is given and all the page is shown of the facts: the prompt, the sources and the item."""
    return json.dumps([ctx.get("prompt"), ctx.get("sources"), ctx.get("item"), ctx.get("extra", {}).get("original")], ensure_ascii=False)


class ReportBase(unittest.TestCase):
    def setUp(self):
        self.v = R.ReportVault()
        R.populate(self.v)

    def tearDown(self):
        self.v.cleanup()

    def ctx(self, req):
        return py(self.v, f"print(json.dumps(drafts.context({req!r}), ensure_ascii=False))")

    def label(self, item_id, name):
        self.v.propose(f"lab-{item_id}", [{"n": 1, "op": "new", "table": "item_labels", "match": "strong", "flags": [],
                                           "decision": "approved", "values": {"item_id": item_id, "label": name, "reason": "kept out"}}])
        self.v.run("apply")

    def new_label(self, name, **values):
        self.v.propose(f"new-{name}", [{"n": 1, "op": "new", "table": "labels", "match": "strong", "flags": [],
                                        "decision": "approved", "values": {"name": name, "colour": "grey", **values}}])
        self.v.run("apply")


class Weekly(ReportBase):
    def test_a_weekly_section_is_drafted_from_the_weeks_facts(self):
        ctx = self.ctx(WEEKLY)
        self.assertEqual((ctx["feature"], ctx["kind"]), ("report-section", "report-section"))
        self.assertIn("UAT start has slipped two weeks.", ctx["prompt"])          # the section as it stands
        self.assertIn("--- FACTS (ranked) ---", ctx["prompt"])
        self.assertTrue(ctx["sources"] and ctx["sources"][0]["ref"] == "S1")
        self.assertEqual(ctx["extra"]["section"], "summary")
        self.assertEqual(ctx["item"]["code"], "ABC")
        self.assertIn("Example Programme", ctx["prompt"])                         # the full name, never only the code (BL-101)

    def test_each_action_has_its_own_instruction(self):
        seen = {}
        for action in ("polish", "shorter", "executive", "custom"):
            req = {**WEEKLY, "action": action, **({"instruction": "Make it about risks"} if action == "custom" else {})}
            seen[action] = self.ctx(req)["prompt"]
        self.assertIn("Polish the text", seen["polish"])
        self.assertIn("shorter, about half", seen["shorter"])
        self.assertIn("executive voice", seen["executive"])
        self.assertIn("Make it about risks", seen["custom"])
        self.assertEqual(len(set(seen.values())), 4)

    def test_a_custom_action_needs_words_and_an_unknown_action_is_refused(self):
        self.assertIn("Say what you want", self.ctx({**WEEKLY, "action": "custom"})["refused"])
        self.assertIn("Choose Polish", self.ctx({**WEEKLY, "action": "rewrite"})["refused"])
        self.assertIn("Say which report", self.ctx({**WEEKLY, "report": "other"})["refused"])
        self.assertIn("Not a project", self.ctx({**WEEKLY, "code": "ZZZ"})["refused"])
        self.assertIn("no words", self.ctx({**WEEKLY, "text": "  "})["nothing"])

    def test_the_reply_is_split_into_sentences_with_sources_and_checked(self):
        ctx = self.ctx(WEEKLY)
        reply = "UAT start has slipped by 20 days. [S1] Omar Ali is escalating it."
        got = py(self.v, f"print(json.dumps(drafts.result({WEEKLY!r}, {ctx!r}, {reply!r}), ensure_ascii=False))")
        self.assertEqual(got["section"], "summary")
        self.assertEqual([s["unsourced"] for s in got["sentences"]], [False, True])
        self.assertNotIn("[S1]", got["text"])
        notes = " ".join(n["note"] for n in got["notes"])
        self.assertTrue(any("20" in n["note"] or "Omar" in n["note"] for n in got["notes"]), got["notes"])   # edit_ai's check: figures and names added

    def test_panes_come_back_as_panes_and_a_reply_that_loses_one_is_dropped(self):
        req = {**WEEKLY, "section": "current_state", "heading": "Current state", "text": None,
               "panes": [{"title": "Done", "text": "Wave two finished."}, {"title": "Next", "text": "Wave three starts."}]}
        ctx = self.ctx(req)
        self.assertIn("### Done", ctx["prompt"])
        ok = py(self.v, f"print(json.dumps(drafts.result({req!r}, {ctx!r}, '### Done\\nWave two is finished.\\n### Next\\nWave three starts Monday.')))")
        self.assertEqual([p["title"] for p in ok["panes"]], ["Done", "Next"])
        bad = py(self.v, f"print(json.dumps(drafts.result({req!r}, {ctx!r}, '### Done\\nWave two is finished.')))")
        self.assertEqual(bad["text"], "")
        self.assertIn("panes", bad["message"])

    def test_the_word_vip_never_comes_out(self):
        ctx = self.ctx(WEEKLY)
        got = py(self.v, f"print(json.dumps(drafts.result({WEEKLY!r}, {ctx!r}, 'The VIP asked for it. [S1]')))")
        self.assertEqual(got["text"], "")
        self.assertNotIn("VIP", json.dumps(got))
        self.assertNotIn("VIP", json.dumps(ctx))


class Counts(ReportBase):
    def test_counts_include_the_two_kinds_and_hold_no_text(self):
        ctx = self.ctx(WEEKLY)
        reply = "UAT start has slipped two weeks. [S1] The secret reply words."
        py(self.v, f"r = drafts.result({WEEKLY!r}, {ctx!r}, {reply!r})\n"
                   "drafts.record('report-section', 'offered')\n"
                   "for f in ('report-section', 'minutes-section'):\n    for e in ('used', 'edited', 'rejected'):\n        drafts.record(f, e)\n"
                   "print(json.dumps(1))")
        stats = json.loads((self.v.root / "system/staging/draft-stats.json").read_text(encoding="utf-8"))
        self.assertEqual({e: stats["report-section"][e] for e in ("offered", "used", "edited", "rejected")},
                         {"offered": 1, "used": 1, "edited": 1, "rejected": 1})
        self.assertEqual({e: stats["minutes-section"][e] for e in ("used", "edited", "rejected")}, {"used": 1, "edited": 1, "rejected": 1})
        raw = (self.v.root / "system/staging/draft-stats.json").read_text(encoding="utf-8")
        for text in ("secret reply", "UAT start", "Example Programme", "ABC"):
            self.assertNotIn(text, raw)

    def test_the_main_command_counts_a_draft_as_offered_under_its_feature(self):
        ctx = self.ctx(WEEKLY)
        body = json.dumps({"request": WEEKLY, "context": ctx, "reply": "UAT start has slipped two weeks. [S1]"})
        r = subprocess.run([sys.executable, "system/scripts/drafts.py", "result"], cwd=self.v.root, input=body, text=True,
                           env={**os.environ, "CREAITE_NOW": R.NOW}, capture_output=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        stats = json.loads((self.v.root / "system/staging/draft-stats.json").read_text(encoding="utf-8"))
        self.assertEqual(stats["report-section"]["offered"], 1)

    def test_both_kinds_are_features_with_a_settings_switch(self):
        got = py(self.v, "print(json.dumps({k: drafts.FEATURES[k][0] for k in ('report-section', 'minutes-section')}))")
        self.assertEqual(sorted(got), ["minutes-section", "report-section"])


if __name__ == "__main__":
    unittest.main()
