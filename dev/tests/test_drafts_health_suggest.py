"""#203: Suggest the health and its reason (the plain-code half): the health is the tracker's, the facts are read from the tracker
alone, a client suggestion holds client-visible items only, and nothing is written.

Run: python3 dev/tests/test_drafts_health_suggest.py
The vault is a throwaway one; no model is called (the reply is given to `drafts.py result`, as the fake Claude would print it).
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
import drafts_fake  # noqa: E402
from test_tracker import Vault, action  # noqa: E402

NOW = "2026-10-17 09:00"
GOOD = "Two actions are overdue and UAT start has slipped. [S1, S2] The next step is to escalate data access. [S1]"


class Suggest(unittest.TestCase):
    def setUp(self):
        old = os.environ.get("CREAITE_NOW")
        os.environ["CREAITE_NOW"] = NOW
        self.addCleanup(lambda: os.environ.__setitem__("CREAITE_NOW", old) if old else os.environ.pop("CREAITE_NOW", None))
        self.v = Vault()
        self.addCleanup(self.v.cleanup)
        drafts_fake.load(self.v)
        self.db = self.v.root / "system/tracker.db"

    def sql(self, q, *args):
        with closing(sqlite3.connect(self.db)) as con:
            con.row_factory = sqlite3.Row
            rows = [dict(r) for r in con.execute(q, args)]
            con.commit()
            return rows

    def drafts(self, cmd, payload):
        r = subprocess.run([sys.executable, str(self.v.root / "system/scripts/drafts.py"), cmd], cwd=self.v.root, capture_output=True,
                           text=True, input=json.dumps(payload), env={**os.environ, "CREAITE_NOW": NOW})
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def ctx(self, **extra):
        return self.drafts("context", {"kind": "health", "code": "ABC", "field": "suggest", **extra})

    def result(self, ctx, reply=GOOD):
        return self.drafts("result", {"request": {}, "context": ctx, "reply": reply})

    def mark_client(self):
        """Make one overdue action and one risk client-visible with client wording; return their ids (the rest stay internal)."""
        act = self.sql("SELECT id FROM actions WHERE project='ABC' AND description LIKE 'Escalate data access%'")[0]["id"]
        risk = self.sql("SELECT id FROM raid WHERE project='ABC' AND type='Risk'")[0]["id"]
        self.sql("UPDATE actions SET client_visible=1, client_message=? WHERE id=?",
                 "What it is: Access to your data is late.\nWhat it means for you: Testing may start later.\n"
                 "What is being done: We are raising it with your leadership.", act)
        self.sql("UPDATE raid SET client_visible=1, client_message=? WHERE id=?",
                 "What it is: Testing could slip.\nWhat it means for you: A later start.\nWhat is being done: We are watching it.", risk)
        return act, risk

    def test_facts_come_from_the_tracker_with_no_page_facts(self):
        c = self.ctx(facts=["A page fact that must be ignored"], to="On track")
        texts = " | ".join(s["text"] for s in c["sources"])
        self.assertNotIn("page fact", texts)
        self.assertIn("Escalate data access to the client CIO", texts)
        self.assertIn("Action overdue by 3 days", texts)
        self.assertIn("Test licences not ordered", texts)                 # an open issue
        self.assertIn("UAT start", texts)                                  # the slipped milestone
        self.assertIn("Health was last set", texts)                       # movement since the last health set
        self.assertTrue(c["prompt"].startswith("Write the reason for a suggested health"))

    def test_the_health_is_the_evidence_functions_not_the_models(self):
        out = self.result(self.ctx(), "Everything is fine. [S1]")
        script = f"import sys; sys.path.insert(0, {str(self.v.root / 'system/scripts')!r}); import report; print(report.health_evidence('ABC')['suggested'])"
        want = subprocess.run([sys.executable, "-c", script], cwd=self.v.root, capture_output=True, text=True,
                              env={**os.environ, "CREAITE_NOW": NOW}).stdout.strip()
        self.assertIn(want, ("On track", "At risk", "Off track"))
        self.assertEqual(out["health"], want)

    def test_differs_is_true_then_false(self):
        out = self.result(self.ctx())
        current = self.sql("SELECT health, health_reason FROM projects WHERE code='ABC'")[0]
        self.assertEqual(out["current"], {"health": current["health"], "reason": current["health_reason"]})
        self.assertEqual(out["differs"], out["health"] != current["health"])
        other = "On track" if out["health"] != "On track" else "At risk"
        self.sql("UPDATE projects SET health=? WHERE code='ABC'", other)
        self.assertTrue(self.result(self.ctx())["differs"])
        self.sql("UPDATE projects SET health=? WHERE code='ABC'", out["health"])
        again = self.result(self.ctx())
        self.assertFalse(again["differs"])
        self.assertEqual(again["current"]["health"], out["health"])

    def test_the_reply_shape_and_evidence_item_ids(self):
        out = self.result(self.ctx())
        for k in ("health", "reason", "differs", "current", "evidence", "audience"):
            self.assertIn(k, out)
        self.assertEqual(out["audience"], "internal")
        self.assertEqual(out["reason"], out["text"])
        self.assertLessEqual(len(out["sentences"]), 3)
        refs = {e["ref"] for e in out["evidence"]}
        a = self.sql("SELECT id FROM actions WHERE description LIKE 'Escalate data access%'")[0]["id"]
        self.assertIn(a, refs)
        self.assertIn("ABC-M-001", refs)
        self.assertTrue(all(e["text"] for e in out["evidence"]))
        self.assertEqual(out["unsourced"], 0)

    def test_a_made_up_health_or_evidence_ref_in_the_reply_is_ignored(self):
        c = self.ctx()
        base = self.result(c)
        out = self.result(c, "HEALTH: Off track\nEVIDENCE: ZZZ-A-999\nThe health is Off track because of ZZZ-A-999. [S99, ZZZ-A-999]")
        self.assertEqual(out["health"], base["health"])
        self.assertEqual(out["evidence"], base["evidence"])
        self.assertNotIn("ZZZ-A-999", json.dumps(out["evidence"]))
        self.assertTrue(out["unsourced"] >= 1)                            # the unknown tag counts for nothing

    def test_an_unsourced_sentence_is_counted(self):
        out = self.result(self.ctx(), "UAT start has slipped. [S1] Nobody is worried.")
        self.assertEqual(out["unsourced"], 1)

    def test_client_mode_holds_client_visible_items_only(self):
        act, risk = self.mark_client()
        c = self.ctx(audience="client")
        ids = {s["id"] for s in c["sources"]}
        self.assertEqual(ids, {act, risk})
        texts = " | ".join(s["text"] for s in c["sources"])
        self.assertIn("Access to your data is late", texts)
        for internal in ("Test licences", "Go-live moves", "UAT start slipped", "Your project record's criteria give", "Health was last set"):
            self.assertNotIn(internal, texts)
            self.assertNotIn(internal, c["prompt"])
        self.assertIn("A client will read", c["prompt"])
        out = self.result(c, "Testing may start later because access to your data is late. [S1]")
        self.assertEqual(out["audience"], "client")
        self.assertEqual({e["ref"] for e in out["evidence"]}, {act, risk})
        self.assertEqual(out["current"]["reason"], "")                    # the internal reason never rides a client reply
        self.assertEqual(out["reason"], "Testing may start later because access to your data is late.")

    def test_client_mode_with_no_client_visible_item_says_so_and_asks_no_model(self):
        c = self.ctx(audience="client")
        self.assertIn("nothing to explain", c["nothing"].lower() if "nothing" in c else "")
        self.assertIn("that a client may see", c["nothing"])

    def test_a_client_reply_that_leaks_an_internal_item_is_dropped(self):
        self.mark_client()
        c = self.ctx(audience="client")
        leaked = self.sql("SELECT id FROM raid WHERE description LIKE 'Test licences%'")[0]["id"]
        out = self.result(c, f"Testing may start later; {leaked} is also open. [S1]")
        self.assertEqual(out["reason"], "")
        self.assertIn("isn't client-safe", out["message"])
        # the tracker's own health reason is internal too
        reason = self.sql("SELECT health_reason FROM projects WHERE code='ABC'")[0]["health_reason"]
        out = self.result(c, f"{reason}. [S1]")
        self.assertEqual(out["reason"], "")
        # a client reason keeps only sentences with a source
        out = self.result(c, "Testing may start later. [S1] The supplier is being squeezed.")
        self.assertEqual(out["reason"], "Testing may start later.")

    def test_nothing_is_written_to_the_tracker(self):
        with closing(sqlite3.connect(self.db)) as con:
            log = con.execute("SELECT count(*) FROM change_log").fetchone()[0]
        self.result(self.ctx())
        self.mark_client()
        before = self.v.snapshot()
        self.result(self.ctx(audience="client"))
        self.assertEqual(self.v.snapshot(), before)
        with closing(sqlite3.connect(self.db)) as con:
            self.assertEqual(con.execute("SELECT count(*) FROM change_log").fetchone()[0], log)

    def test_the_existing_reason_mode_is_unchanged(self):
        c = self.drafts("context", {"kind": "health", "code": "ABC", "to": "At risk", "facts": ["Two actions are overdue"]})
        self.assertTrue(c["prompt"].startswith("Write the reason for a health change"))
        self.assertIn("it is now At risk", c["prompt"])
        self.assertIn("Two actions are overdue", c["prompt"])
        out = self.result(c, "Two actions are overdue. [S1]")
        self.assertEqual(set(out) & {"health", "differs", "evidence", "current"}, set())
        self.assertEqual(out["text"], "Two actions are overdue.")
        r = self.drafts("context", {"kind": "health", "code": "DEF", "to": "On track", "facts": []})
        self.assertIn("Say why in your own words", r["nothing"])

    # ----- review fixes (health-203-fix-plain) -----
    def overdue_action(self, n, **v):
        """Add an overdue ABC action through the one writer (tracker.py apply)."""
        self.v.propose(f"n{n}", [action(n, description=v.pop("description", f"Overdue thing {n}"), due_date="2026-09-01", **v)])
        self.v.run("apply")
        return self.sql("SELECT id FROM actions ORDER BY rowid DESC LIMIT 1")[0]["id"]

    def source_texts(self):
        c = self.ctx()
        return " | ".join(s["text"] for s in c["sources"]), c["prompt"].split("--- FACTS ---")[1]

    def test_confidential_items_never_reach_the_prompt_whatever_the_fact_length(self):
        long_ = "Chase the supplier about the licence renewal and the data room access for the audit team " * 2 + "marked confidential"
        a = self.overdue_action(31, description=long_)
        b = self.overdue_action(32, description="Plain board action", latest_update="restricted: board only",
                                source="projects/ABC/documents/restricted board paper.docx")
        c_ = self.overdue_action(33, description="Short confidential note")
        d_ = self.overdue_action(34, description="Documents source action", source="projects/ABC Example Programme/documents/Plan.docx")
        self.sql("UPDATE raid SET response_action='confidential: legal view' WHERE description LIKE 'Test licences%'")
        self.sql("UPDATE raid SET source='projects/ABC/documents/x.docx' WHERE description LIKE 'Data access delayed%'")
        self.sql("INSERT INTO decisions (id, project, decision, made_by, status, needed_by, source) VALUES "
                 "('ABC-D-090','ABC','Approve the restricted budget route','Jane Doe','Pending','2026-09-01','projects/ABC/documents/b.docx')")
        texts, prompt = self.source_texts()
        for gone in (a, b, c_, d_, "Plain board action", "Test licences", "Data access delayed", "restricted budget", "ABC-D-090"):
            self.assertNotIn(gone, texts)
            self.assertNotIn(gone, prompt)
        self.assertIn("Escalate data access", texts)                    # ordinary facts remain

    def test_a_confidential_closed_action_is_not_movement(self):
        self.sql("INSERT INTO actions (id, project, description, owner, status, closed, raised, source) VALUES "
                 "('ABC-A-095','ABC','Quiet closure','Alan Carter','Closed','2026-10-16','2026-10-01','projects/ABC/documents/c.docx')")
        self.assertNotIn("Quiet closure", self.source_texts()[0])

    def test_an_undone_health_change_is_not_the_last_set(self):
        self.v.propose("h", [{"n": 1, "op": "update", "table": "projects", "id": "ABC",
                              "changes": {"health": "On track", "health_reason": "All fine"}, "decision": "approved"}])
        self.v.run("apply")
        self.assertIn("last set", self.source_texts()[0])
        self.assertIn("to On track", self.source_texts()[0])
        self.v.run("undo")
        texts = self.source_texts()[0]
        self.assertNotIn("to On track", texts)
        self.assertIn("to Off track", texts)                              # the earlier, still standing, change

    def test_a_client_health_is_computed_from_client_visible_items_only(self):
        self.sql("UPDATE raid SET priority='Urgent'")
        for n in (41, 42, 43, 44):
            self.overdue_action(n)                                        # internal-only and well overdue
        internal = self.result(self.ctx())
        self.assertNotEqual(internal["health"], "On track")
        act = self.sql("SELECT id FROM actions WHERE description LIKE 'Escalate data access%'")[0]["id"]
        self.sql("UPDATE actions SET client_visible=1, client_message=? WHERE id=?",
                 "What it is: Access to your data is late.\nWhat it means for you: Testing may start later.\n"
                 "What is being done: We are raising it.", act)
        c = self.ctx(audience="client")
        out = self.result(c, "Testing may start later because access is late. [S1]")
        self.assertEqual(out["health"], "On track")
        self.assertEqual(out["differs"], self.sql("SELECT health FROM projects WHERE code='ABC'")[0]["health"] != "On track")
        self.assertNotIn("Urgent", json.dumps(out))

    def test_the_cap_keeps_each_kind_and_movement_does_not_repeat_an_open_item(self):
        for n in range(51, 59):
            self.overdue_action(n)
        c = self.ctx()
        kinds = [s["kind"] for s in c["sources"]]
        self.assertLessEqual(len(kinds), 12)
        self.assertLessEqual(kinds.count("overdue"), 3)
        for k in ("criteria", "milestone", "raid", "movement"):
            self.assertIn(k, kinds)
        self.assertTrue(any("Health was last set" in s["text"] for s in c["sources"]))
        ids = [s["id"] for s in c["sources"] if s["kind"] != "criteria" and "Health was last set" not in s["text"]]
        self.assertEqual(len(ids), len(set(ids)))


    # ----- review fixes 2 (health-203-fix2-plain) -----
    def uat(self):
        return self.sql("SELECT id FROM milestones WHERE project='ABC' AND name LIKE 'UAT%'")[0]["id"]

    def test_a_decisions_options_and_a_milestones_own_fields_keep_it_out(self):
        self.sql("INSERT INTO decisions (id, project, decision, made_by, status, needed_by, options, reasoning, source) VALUES "
                 "('ABC-D-090','ABC','Pick the vendor ZQXDEC','Jane Doe','Pending','2026-10-01','confidential: vendor A or B',"
                 "'because','projects/ABC/minutes/m.md')")
        self.assertNotIn("ZQXDEC", self.source_texts()[1])
        for col, val in (("description", "confidential acquisition gate"), ("internal_note", "restricted"),
                         ("source", "projects/ABC/documents/a.docx")):
            self.sql(f"UPDATE milestones SET {col}=? WHERE id=?", val, self.uat())
            self.assertNotIn("Milestone UAT start", self.source_texts()[0], col)
            self.sql(f"UPDATE milestones SET {col}=? WHERE id=?", "plain" if col != "source" else "Alan (cx-edit)", self.uat())
        self.assertIn("Milestone UAT start", self.source_texts()[0])

    def test_a_confidential_milestone_name_is_not_in_the_criteria_line(self):
        self.sql("UPDATE milestones SET name='Confidential merger close' WHERE id=?", self.uat())
        texts, prompt = self.source_texts()
        self.assertNotIn("Confidential merger", texts)
        self.assertNotIn("Confidential merger", prompt)
        self.assertEqual(self.result(self.ctx())["health"], "At risk")        # the health itself is unchanged

    def test_archived_items_are_not_facts_and_do_not_drive_the_health(self):
        for n in (61, 62):
            self.overdue_action(n, description=f"Archived thing ZQXARCH{n}")
        self.sql("UPDATE actions SET archived=1 WHERE description LIKE 'Archived thing%'")
        self.sql("UPDATE milestones SET archived=1 WHERE id=?", self.uat())
        self.sql("UPDATE raid SET archived=1")
        texts, prompt = self.source_texts()
        self.assertNotIn("ZQXARCH", prompt)
        self.assertNotIn("UAT start", texts)
        self.assertNotIn("criteria give", texts)                              # nothing live drives it any more except the escalation action


if __name__ == "__main__":
    unittest.main()
