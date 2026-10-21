"""BL-106: the facts sheet an executive status is written from, and the checks on a drafted status.

Run: python3 dev/tests/test_status_facts.py
The clock is fixed (CREAITE_NOW) to Friday 09-10-2026 13:00; the data is fictional. The sheet is plain code: no model is called.
"""
import json
import sqlite3
import sys
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
from test_reports import ReportVault, new, populate  # noqa: E402
from test_tracker import ABC  # noqa: E402

PERIOD = ("--from", "2026-10-01", "--to", "2026-10-09")


class FactsCase(unittest.TestCase):
    def setUp(self):
        self.v = ReportVault()
        populate(self.v)
        src = f"{ABC}/minutes/2026-10-06 Steering.docx — Actions"
        (self.v.root / ABC / "minutes").mkdir(exist_ok=True)
        (self.v.root / ABC / "minutes/2026-10-06 Steering.md").write_text(
            "# Steering\n\nThe pilot finished. Handling time is down 11% against an 8% target.\n\nEveryone agreed to meet again.\n")
        self.v.propose("more", [
            new("raid", 1, project="ABC", type="Risk", description="Key tester leaves in November", impact="Low", likelihood="Low",
                raised="2026-10-02", source=src),
            new("raid", 2, project="ABC", type="Dependency", description="Client delivers the UAT data extract", owner="Jane Doe (Example Client Ltd)",
                due_date="2026-11-10", milestone="ABC-M-001", raised="2026-10-02", source=src),
            new("actions", 3, project="ABC", description="Book the UAT room", owner="Alan Carter", due_date="2026-10-02", raised="2026-09-30",
                status="Closed", closed="2026-10-05", source=src),
            new("updates", 4, week_ending="2026-10-02", project="ABC", health="On track", summary="Steady."),
            new("decisions", 5, project="ABC", decision="Extend the pilot by two weeks", made_by="Sara Example (Example Client Ltd)",
                status="Pending", needed_by="2026-10-07", source=src),
            new("decisions", 6, project="ABC", decision="Choose the UAT environment", made_by="Alan Carter", status="Pending",
                needed_by="2026-10-20", source=src),
            new("decisions", 7, project="ABC", decision="Approve the extra test licences", made_by="Jane Doe (Example Client Ltd)",
                status="Pending", needed_by="2026-10-14", client_visible=1,
                client_message="We need your approval to buy the extra test licences.", source=src),
        ])
        self.v.run("apply")
        self.v.propose("move", [{"n": 1, "op": "update", "table": "milestones", "id": "ABC-M-001",
                                 "changes": {"forecast_date": "2026-11-05"}, "decision": "approved"},
                                {"n": 2, "op": "update", "table": "projects", "id": "ABC",
                                 "changes": {"health": "At risk", "health_reason": "UAT start slipped 14 days"}, "decision": "approved"}])
        self.v.run("apply")
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:     # the throwaway vault's clock is the real one
            con.execute("UPDATE change_log SET at = '2026-10-07 09:00:00'")
            con.commit()

    def tearDown(self):
        self.v.cleanup()

    def facts(self, *extra, audience="internal"):
        out = self.v.at("facts", "ABC", *PERIOD, "--audience", audience, *extra, "--json", script="status_facts.py").stdout
        return json.loads(out)

    @staticmethod
    def lines(f, key):
        return [ln for p in f["parts"] if p["key"] == key for ln in p["lines"]]

    @staticmethod
    def texts(f, key):
        return [ln["text"] for p in f["parts"] if p["key"] == key for ln in p["lines"]]


class InternalSheet(FactsCase):
    def test_position_says_what_changed_since_the_last_status(self):
        pos = self.texts(self.facts(), "position")
        self.assertEqual(pos[0], "Health now: At risk — UAT start slipped 14 days.")
        self.assertIn("Changed since the last status: it was On track (week ending 02-10-2026), now At risk.", pos)

    def test_sentences_carry_no_item_ids_but_the_sources_do(self):
        f = self.facts()
        every = [ln["text"] for p in f["parts"] for ln in p["lines"]]
        import status_facts
        self.assertEqual([t for t in every if status_facts.ID_RE.search(t)], [])
        self.assertIn("ABC-005", f["sources"])
        self.assertNotIn("ABC-005", f["text"].split("[src:")[0])

    def test_exposure_names_the_top_risks_by_priority_and_counts_the_rest(self):
        ex = self.texts(self.facts(), "exposure")
        risks = [t for t in ex if t.startswith(("Risk", "Issue"))]
        self.assertEqual(len(risks), 2)                                              # max_risks
        self.assertTrue(risks[0].startswith("Risk, Urgent: Vendor exits the market"), risks)
        self.assertIn("1 further open risk or issue, not named here.", ex)
        self.assertNotIn("Key tester leaves in November", " ".join(ex))              # the lowest is not named

    def test_exposure_has_the_oldest_overdue_and_the_blocker(self):
        ex = self.texts(self.facts(), "exposure")
        self.assertTrue(any(t.startswith("Overdue by 14 days (due 25-09-2026): Escalate data access") for t in ex), ex)
        self.assertTrue(any(t.startswith("Blocker: Client delivers the UAT data extract") and "due after the milestone" in t for t in ex), ex)

    def test_movement_names_the_move_the_next_milestone_and_the_counts(self):
        mv = self.texts(self.facts(), "movement")
        self.assertIn("Milestone moved: UAT start, from 03-11-2026 to 05-11-2026.", mv)
        self.assertTrue(any(t.startswith("Next milestone: UAT start, forecast 05-11-2026, baseline 20-10-2026 (+16 days)") for t in mv), mv)
        self.assertTrue(any("1 action closed" in t for t in mv), mv)
        self.assertTrue(any(t.startswith("Closed and notable: Book the UAT room") for t in mv), mv)

    def more_room(self, n=6):
        cfg = self.v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text())
        data["status"]["max_asks"] = n
        cfg.write_text(json.dumps(data))

    def test_asks_are_other_peoples_actions_and_never_alans_own(self):
        self.more_room()
        f = self.facts()
        asks = self.texts(f, "asks")
        self.assertTrue(any(t.startswith("Waiting on Jane Doe: Sign the statement of work. Due 16-10-2026") for t in asks), asks)
        self.assertIn("Jane Doe", [a["who"] for a in f["asks"]])
        self.assertNotIn("Alan Carter", [a["who"] for a in f["asks"]])
        self.assertEqual([a["kind"] if "kind" in a else "action" for a in f["asks"]][:3], ["decision"] * 3)      # decisions first

    def test_decisions_needed_come_first_in_asks_in_both_directions(self):
        f = self.facts()
        asks = self.texts(f, "asks")
        self.assertEqual(asks[0], "Decision needed from Sara Example: Extend the pilot by two weeks. Needed by 07-10-2026, 2 days overdue.")
        self.assertEqual(asks[1], "Decision needed from Jane Doe: Approve the extra test licences. Needed by 14-10-2026.")
        self.assertEqual(asks[2], "Decision for Alan: Choose the UAT environment. Needed by 20-10-2026.")
        self.assertEqual([a["kind"] for a in f["asks"]][:3], ["decision"] * 3)
        self.assertTrue(any(t.startswith("2 further open actions") for t in asks), asks)           # the cap of three is shared with the actions
        self.assertFalse(any("Waiting on" in t for t in asks))                                    # no room left for actions

    def test_a_pending_decision_is_not_counted_as_made(self):
        mv = " ".join(self.texts(self.facts(), "movement"))
        self.assertNotIn("Extend the pilot", mv)

    def test_numbers_are_candidate_lines_with_their_file(self):
        f = self.facts()
        nums = self.lines(f, "numbers")
        joined = " ".join(n["text"] for n in nums)
        self.assertIn("Handling time is down 11% against an 8% target.", joined)
        self.assertNotIn("meet again", joined)
        self.assertTrue(any("2026-10-06 Steering.md" in s for n in nums for s in n["src"]))
        self.assertTrue(f["has_figures"])

    def test_the_wording_is_clean(self):
        for audience in ("internal", "client"):
            text = self.facts(audience=audience)["text"]
            for bad in ("..", "TBC", "Due no date", "1 actions", "1 risks"):
                self.assertNotIn(bad, text, (audience, bad))
        self.assertEqual(self.facts()["text"].count("Client delivers the UAT data extract"), 1)     # a blocker is not repeated as a warning

    def test_a_corrupt_word_file_is_skipped_not_fatal(self):
        (self.v.root / ABC / "minutes/2026-10-07 Broken.docx").write_bytes(b"not a zip")
        self.assertIn("Handling time is down 11% against an 8% target.", " ".join(self.texts(self.facts(), "numbers")))

    def test_a_cap_in_settings_changes_what_is_named(self):
        cfg = self.v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text())
        data["status"]["max_risks"] = 1
        cfg.write_text(json.dumps(data))
        ex = self.texts(self.facts(), "exposure")
        self.assertEqual(len([t for t in ex if t.startswith(("Risk", "Issue"))]), 1)
        self.assertIn("2 further open risks and issues, not named here.", ex)

    def test_a_part_with_nothing_to_say_is_left_out(self):
        self.v.propose("q", [new("projects", 1, code="QUI", name="Quiet Project")])
        self.v.run("apply")
        folder = self.v.root / "projects/QUI Quiet Project"
        for sub in ("minutes", "transcripts", "documents", "reports"):
            (folder / sub).mkdir(parents=True, exist_ok=True)
        (folder / "CLAUDE.md").write_text("# QUI\n\n## Current state\n\nSteady.\n")
        f = json.loads(self.v.at("facts", "QUI", "--json", script="status_facts.py").stdout)
        keys = [p["key"] for p in f["parts"]]
        self.assertIn("position", keys)
        for gone in ("exposure", "asks", "numbers"):
            self.assertNotIn(gone, keys)
        self.assertNotIn("## Exposure", f["text"])

    def test_a_wrong_audience_is_refused(self):
        r = self.v.at("facts", "ABC", "--audience", "press", script="status_facts.py", ok=False)
        self.assertEqual(r.returncode, 2)


class ClientSheet(FactsCase):
    def test_only_client_visible_items_in_their_own_words(self):
        f = self.facts(audience="client")
        text = f["text"]
        self.assertIn("Test licences are not yet ordered.", text)          # the client message, not the description
        self.assertNotIn("Vendor exits", text)                               # internal risk
        self.assertNotIn("Escalate data access", text)                       # internal action
        self.assertNotIn("Early warning", text)
        self.assertNotIn("Blocker", text)

    def test_no_flow_counts_and_no_numbers_from_internal_minutes(self):
        f = self.facts(audience="client")
        keys = [p["key"] for p in f["parts"]]
        self.assertNotIn("trend", keys)
        self.assertNotIn("numbers", keys)                                    # the only candidate is in internal minutes

    def test_asks_are_the_clients_own_visible_items(self):
        f = self.facts(audience="client")
        self.assertEqual([a["who"] for a in f["asks"]], ["Jane Doe", "Jane Doe"])        # Omar's action and the internal decisions are not client-visible
        asks = self.texts(f, "asks")
        self.assertEqual(asks[0], "Decision needed from Jane Doe: We need your approval to buy the extra test licences. Needed by 14-10-2026.")
        self.assertTrue(any("The signed statement of work." in t for t in asks))
        self.assertNotIn("Extend the pilot", f["text"])
        self.assertNotIn("Choose the UAT environment", f["text"])

    def test_no_internal_reasoning_about_health(self):
        pos = " ".join(self.texts(self.facts(audience="client"), "position"))
        self.assertNotIn("evidence", pos)


class Checks(unittest.TestCase):
    FACTS = {"has_figures": True, "asks": [{"who": "Sara Khan", "text": "Confirm the pilot extension", "due": "2026-10-16", "id": "ABC-A-004"}],
             "sources": ["ABC-A-004", "projects/ABC Example Programme/minutes/2026-10-06 Steering.md"]}
    GOOD = ("**At risk for the 20-11-2026 go-live: UAT data is six days late.**\n\n- **Why.** The pilot cut handling time by 11%.\n"
            "- **Ask.** We need Sara Khan to release the data by 16-10-2026.\n")

    def run_check(self, draft, **kw):
        import status_checks
        return {n["id"]: n["note"] for n in status_checks.check(draft, kw.pop("facts", self.FACTS), **kw)}

    def test_a_good_draft_passes_every_check(self):
        self.assertEqual(self.run_check(self.GOOD), {})

    def test_a_long_headline(self):
        long = "**At risk because " + "the data is late " * 10 + "so testing cannot start.**\n\n- **Ask.** Sara Khan by 16-10-2026."
        self.assertIn("headline", self.run_check(long))

    def test_no_position(self):
        self.assertIn("position", self.run_check("**Good progress overall, one thing to watch.**\n\n- Sara Khan needs to act by 16-10-2026.\n"))

    def test_item_numbers_in_the_text(self):
        self.assertIn("ids", self.run_check(self.GOOD + "- ABC-A-004 is overdue.\n"))

    def test_no_date_or_number(self):
        draft = "**At risk: the data is late.**\n\n- We need Sara Khan to act soon.\n"
        self.assertIn("figures", self.run_check(draft))
        self.assertNotIn("figures", self.run_check(draft, facts={**self.FACTS, "has_figures": False}))

    def test_a_pending_ask_not_mentioned(self):
        note = self.run_check("**On track for 20-11-2026.**\n\n- **Why.** The pilot finished on 06-10-2026.\n")["asks"]
        self.assertEqual(note, "No ask mentioned, but 1 item is waiting on others.")

    def test_length(self):
        self.assertIn("length", self.run_check(self.GOOD + "- " + "word " * 200, length="short"))
        self.assertNotIn("length", self.run_check(self.GOOD, length="standard"))

    def test_a_source_the_facts_do_not_have(self):
        sources = "- ABC-A-004 Confirm the pilot extension\n- ABC-A-099 something else\n- Steering minutes\n"
        self.assertIn("ABC-A-099", self.run_check(self.GOOD, sources=sources)["sources"])
        self.assertNotIn("sources", self.run_check(self.GOOD, sources="- ABC-A-004 Confirm the pilot extension\n"))

    def test_an_empty_draft_has_no_headline(self):
        self.assertIn("headline", self.run_check(""))


if __name__ == "__main__":
    unittest.main()
