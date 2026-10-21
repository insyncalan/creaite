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
import sqlite3
import subprocess
import sys
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_reports as R  # noqa: E402  (its fixture: populate, ReportVault, NOW; the data is fictional)
import test_minutes_approve as M  # noqa: E402

HEAD = "import sys, json; sys.path.insert(0, 'system/scripts')\nimport drafts\n"
CLIENT_TEXT = "Phase two can start once the paperwork is signed."
WEEKLY = {"kind": "report-section", "report": "weekly", "code": "ABC", "week_ending": "2026-10-09", "section": "summary",
          "heading": "Summary", "text": "UAT start has slipped two weeks.", "action": "polish"}
WEEKLY["document"] = {"kind": "weekly", "code": "ABC", "week_ending": "2026-10-09"}   # #127: the audience comes from the report named
CLIENT = {**WEEKLY, "report": "client", "text": CLIENT_TEXT,
          "document": {"kind": "client", "code": "ABC", "week_ending": "2026-10-09", "client": ""}}
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
        self.assertIn("Say which report", self.ctx({k: v for k, v in WEEKLY.items() if k != "document"})["refused"])
        self.assertIn("Not a project", self.ctx({**WEEKLY, "code": "ZZZ"})["refused"])
        self.assertIn("no words", self.ctx({**WEEKLY, "text": "  "})["nothing"])

    def test_the_reply_is_split_into_sentences_with_sources_and_checked(self):
        ctx = self.ctx(WEEKLY)
        reply = "UAT start has slipped by 20 days. [S1] Omar Ali is escalating it."
        got = py(self.v, f"print(json.dumps(drafts.result({WEEKLY!r}, {ctx!r}, {reply!r}), ensure_ascii=False))")
        self.assertEqual(got["section"], "summary")
        self.assertEqual([s["unsourced"] for s in got["sentences"]], [False, True])
        self.assertNotIn("[S1]", got["text"])
        # edit_ai's check: the figure and the name it added
        self.assertTrue(any("20" in n["note"] or "Omar" in n["note"] for n in got["notes"]), got["notes"])

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


class ClientSection(ReportBase):
    """Privacy by construction: the facts are the client version's, line by line through client_leak."""

    def seed_withheld(self):
        """One of each kind of withheld content, on top of the fixture's internal-only items: a client-visible item that is
        Sensitive, one that is partner-only, one a label excludes, and the memory line marked Client-safe: no."""
        self.new_label("Partner only")
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            con.execute("INSERT OR IGNORE INTO labels (name, behaviour) VALUES ('Exclude from client', 'exclude')")
            con.commit()
        self.label("ABC-006", "Sensitive")           # Test licences (client-visible)
        self.label("ABC-D-007", "Partner only")      # Go-live stays on 20 November (client-visible)
        self.label("ABC-A-002", "Exclude from client")   # Sign the statement of work (client-visible)

    WITHHELD = ("Test licences", "Go-live stays", "Go-live remains", "statement of work", *INTERNAL_ONLY)

    def test_control_the_client_sheet_does_hold_these_before_they_are_withheld(self):
        ctx = self.ctx(CLIENT)
        text = everything(ctx)
        self.assertIn("Test licences are not yet ordered", text)                      # client-visible: in the client version
        self.assertIn("Go-live remains on 20 November", text)
        self.assertIn("statement of work", text)
        for internal in INTERNAL_ONLY:
            self.assertNotIn(internal, text)                                            # never client-visible

    def test_nothing_withheld_is_in_the_prompt_or_the_facts(self):
        self.seed_withheld()
        ctx = self.ctx(CLIENT)
        self.assertIn("prompt", ctx, ctx)
        text = everything(ctx)
        for gone in self.WITHHELD:
            self.assertNotIn(gone, text)
        self.assertNotIn("ABC-006", text)
        self.assertNotIn("ABC-D-007", text)
        self.assertEqual(ctx["extra"]["audience"], "client")
        self.assertIn("Audience: client-safe", ctx["prompt"])

    def test_each_kind_of_withheld_line_is_dropped_by_client_leak_itself(self):
        """The second check, apart from the client sheet: a line resting on a withheld item is dropped whatever the sheet held."""
        self.seed_withheld()
        lines = {"internal-only": {"text": "Confirm tester names", "src": ["ABC-A-004"]},
                 "sensitive": {"text": "Licences", "src": ["ABC-006"]}, "partner-only": {"text": "Go-live", "src": ["ABC-D-007"]},
                 "excluded": {"text": "Sign it", "src": ["ABC-A-002"]},
                 "memory line": {"text": "Budget overrun on phase one is being absorbed", "src": []},
                 "internal wording": {"text": "See documents/plan for the confidential detail", "src": []},
                 "client-visible": {"text": "Send the revised plan", "src": ["ABC-A-003"]}}
        got = py(self.v, f"import client_leak\ncon = client_leak.connect()\nb = client_leak.blocking_labels(con)\n"
                         f"print(json.dumps({{k: drafts.client_line_ok(con, 'ABC', ln, b) for k, ln in {lines!r}.items()}}))")
        self.assertEqual(got, {"internal-only": False, "sensitive": False, "partner-only": False, "excluded": False,
                               "memory line": False, "internal wording": False, "client-visible": True})

    def test_a_section_that_already_holds_internal_wording_is_not_sent(self):
        got = self.ctx({**CLIENT, "text": "Vendor exits the market before go-live."})
        self.assertIn("isn't client-safe", got["refused"])
        self.assertNotIn("prompt", got)

    def test_a_reply_that_brings_in_internal_wording_is_dropped(self):
        ctx = self.ctx(CLIENT)
        reply = "The vendor exits the market before go-live, so we absorb the phase one overrun. [S1]"
        got = py(self.v, f"print(json.dumps(drafts.result({CLIENT!r}, {ctx!r}, {reply!r})))")
        self.assertEqual(got["text"], "")
        self.assertIn("isn't client-safe", got["message"])
        ok = py(self.v, f"print(json.dumps(drafts.result({CLIENT!r}, {ctx!r}, 'Testing could start late. [S1]')))")
        self.assertEqual(ok["text"], "Testing could start late.")

    REASON = "ZEBRAINTERNAL vendor is failing to deliver the build on time"

    def set_health(self, health="Off track", reason=REASON):
        """The tracker's internal health and its reason (a test vault: set directly, as the fixture's labels are)."""
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            con.execute("UPDATE projects SET health = ?, health_reason = ? WHERE code = 'ABC'", (health, reason))
            con.commit()

    def result(self, req, ctx, reply):
        return py(self.v, f"print(json.dumps(drafts.result({req!r}, {ctx!r}, {reply!r}), ensure_ascii=False))")

    def test_the_internal_health_and_its_reason_never_reach_a_client_draft(self):
        """#90 review F1: the tracker's internal health reason is in the weekly facts (the seed is real) and never in a client
        section's prompt, sources or item; nor are the internal flag's "Health now" and "Changed since" lines."""
        self.set_health()
        weekly = self.ctx(WEEKLY)
        self.assertIn("ZEBRAINTERNAL", weekly["prompt"])                                 # control: the internal sheet holds it
        ctx = self.ctx(CLIENT)
        self.assertIn("prompt", ctx, ctx)
        for where in (everything(ctx), json.dumps(ctx, ensure_ascii=False)):
            self.assertNotIn("ZEBRAINTERNAL", where)
            self.assertNotIn("vendor is failing", where)
            self.assertNotIn("Health now", where)
            self.assertNotIn("Changed since the last status", where)
        self.assertIn("Test licences are not yet ordered", ctx["prompt"])               # the client facts are still there

    def test_a_client_reply_that_brings_in_the_internal_reason_or_marker_is_dropped(self):
        self.set_health()
        ctx = self.ctx(CLIENT)
        for reply in (f"{self.REASON}. [S1]", "The vendor is failing to deliver the build, so testing waits. [S1]",
                      "Testing could start late; this is internal only. [S1]"):
            got = self.result(CLIENT, ctx, reply)
            self.assertEqual(got["text"], "", reply)
            self.assertIn("isn't client-safe", got["message"])
            self.assertNotIn("ZEBRA", json.dumps(got))
        ok = self.result(CLIENT, ctx, "Testing could start late. [S1]")
        self.assertEqual(ok["text"], "Testing could start late.")
        self.assertNotIn("ZEBRA", json.dumps(ok))
        # the same words in the section as Alan wrote it are his, not the draft's: his own words may come back
        own = {**CLIENT, "text": "The vendor is failing to deliver the build on time."}
        ctx2 = self.ctx(own)
        self.assertEqual(self.result(own, ctx2, "The vendor is failing to deliver the build on time. [S1]")["text"],
                         "The vendor is failing to deliver the build on time.")

    def test_the_client_facts_are_the_client_reports_locked_facts(self):
        """#90 review F4: with the internal week approved, a client draft's facts are the locked meta.client_facts: a client wording
        changed in the tracker since is not in them, and the prompt says which week they are locked to."""
        before = self.ctx(CLIENT)
        self.assertIn("no internal weekly report is approved", before["prompt"])
        py(self.v, "import report_doc\nd = report_doc.weekly_doc('ABC')\n"
                   "next(s for s in d['sections'] if s['id'] == 'health')['text'] = 'UAT start slipped two weeks.'\n"
                   "r = report_doc.save_draft(d)\nreport_doc.stage_weekly(r['path'])\nprint(json.dumps(1))")
        self.v.at("apply", script="tracker.py")
        self.v.propose("later", [{"n": 1, "op": "update", "table": "decisions", "id": "ABC-D-007", "match": "strong", "flags": [],
                                  "decision": "approved", "changes": {"client_message": "LIVEMARK the go-live moved"}}])
        self.v.at("apply", script="tracker.py")
        ctx = self.ctx(CLIENT)
        self.assertIn("locked to the approved internal weekly report for week ending 09-10-2026", ctx["prompt"])
        self.assertIn("Go-live remains on 20 November", ctx["prompt"])
        self.assertNotIn("LIVEMARK", everything(ctx))


def _minutes_vault_case():
    class MinutesSection(M.Base):
        """A distributed version never holds an Internal only line or row, nor a Sensitive, partner-only or excluded item."""
        GONE = M.FollowUp.GONE
        seed = M.FollowUp.seed

        def ctx(self, **extra):
            req = {"kind": "minutes-section", "path": M.DRAFT, "section": "summary", "action": "polish", "version": "distributed",
                   "text": "The committee met.\n\nSECRETLINE is for us only.", **extra}
            return self.js("import drafts\nprint(json.dumps(drafts.context(" + repr(req) + "), ensure_ascii=False))")

        def test_the_distributed_prompt_and_facts_hold_nothing_withheld(self):
            self.seed()
            ctx = self.ctx()
            self.assertIn("prompt", ctx, ctx)
            text = everything(ctx)
            for gone in self.GONE:
                self.assertNotIn(gone, text)
            self.assertIn("The committee met.", ctx["prompt"])                      # the version's own words
            self.assertIn("Book the UAT environment", text)                          # what everyone may see is a source
            self.assertIn("Shared action", text)
            self.assertIn("distributed version", ctx["prompt"])
            self.assertEqual(ctx["extra"]["audience"], "distributed")

        def test_the_distributed_words_come_from_the_record_never_from_the_page(self):
            self.seed()
            ctx = self.ctx(text="SECRETLINE is for us only. Internal-only row action.")      # a page that sent the internal words
            text = everything(ctx)
            self.assertNotIn("SECRETLINE", text)
            self.assertNotIn("Internal-only row action", text)

        def test_the_internal_version_draws_on_the_distributed_facts_and_says_so(self):
            """#90 review F3 (changed from "keeps them"): an internal-version draft's facts are the distributed version's, so no
            Internal only row or withheld item can be laundered into a section that is distributed. A section with a line marked
            Internal only is refused (a redraft would lose the mark); another section is drafted, from the distributed facts."""
            self.seed()
            got = self.ctx(version="internal")
            self.assertIn("marked Internal only", got["refused"])
            self.assertNotIn("prompt", got)
            # a section with no marked line: SECRETLINE is in the record but never in the facts
            doc = self.js("import minutes_record\nprint(json.dumps(minutes_record.record_at(" + repr(M.DRAFT) + ")[1]))")
            other = next(s["id"] for s in doc["sections"] if s.get("type") not in ("header", "table") and s["id"] != "summary"
                         and str(s.get("text") or "").strip() not in ("", "None recorded."))
            ctx = self.ctx(version="internal", section=other, text="Alan's internal words for this section.")
            self.assertIn("prompt", ctx, ctx)
            text = everything(ctx)
            for gone in self.GONE:
                self.assertNotIn(gone, text)
            self.assertIn("Alan's internal words for this section.", ctx["prompt"])          # the internal words are the page's
            self.assertIn("This is the internal version.", ctx["prompt"])
            self.assertIn("distributed version's", ctx["prompt"])
            self.assertEqual(ctx["extra"]["audience"], "internal")

        def test_other_versions_sections_and_paths_are_refused(self):
            self.seed()
            self.assertIn("internal or the distributed", self.ctx(version="client")["refused"])
            self.assertIn("can't be redrafted", self.ctx(section="actions")["refused"])          # a table
            self.assertIn("can't be redrafted", self.ctx(section="nope")["refused"])
            self.assertIn("minutes creaite can open", self.ctx(path="../../etc/passwd")["refused"])

        def test_the_reply_is_checked_and_a_vip_is_dropped(self):
            self.seed()
            ctx = self.ctx()
            got = self.js("import drafts\nprint(json.dumps(drafts.result({}, " + repr(ctx) + ", 'The committee met and agreed. [S1]')))")
            self.assertEqual((got["section"], got["text"]), ("summary", "The committee met and agreed."))
            bad = self.js("import drafts\nprint(json.dumps(drafts.result({}, " + repr(ctx) + ", 'A VIP joined. [S1]')))")
            self.assertEqual(bad["text"], "")

        def test_the_reply_gets_the_minutes_check_against_the_records_project(self):
            """#262 (2.6): the ✦ reply is checked as the AI bar's is, against the project the record names (never the page's):
            an added item a client may not see, a loose VIP spelling or an unknown name is dropped; a project-less record is
            refused before Claude."""
            self.seed()
            ctx = self.ctx()
            self.assertEqual(ctx["extra"]["code"], "ABC")
            for added in ("ABC-A-002 is open.", "abc a 2 is open.", "A V.I.P. joined.", "Sara Example will chase."):
                got = self.js("import drafts\nprint(json.dumps(drafts.result({}, " + repr(ctx) + ", "
                              + repr("The committee met. " + added + " [S1]") + ")))")
                self.assertEqual(got["text"], "", added)
                self.assertNotIn("VIP", got.get("message", "").upper().replace(".", ""), added)   # BL-288
            for doc in ({}, {"meta": {"projects": ["ZZZ"]}}, {"project": ""}):
                got = self.js("import drafts\ntry:\n    drafts.minutes_project(" + repr(doc) + ")\n    r = ''\n"
                              "except drafts.Refused as e:\n    r = str(e)\nprint(json.dumps(r))")
                self.assertIn("no project in the tracker", got, doc)
    return MinutesSection


MinutesSection = _minutes_vault_case()


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
