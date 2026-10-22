"""BL-322 Sneak peek, the server side: sneak_peek.py reads what Alan types about the one item open in the peek, in plain code.

- Dates in Alan's words on several weekdays (a pinned clock), people from the register (two matches ask, none changes nothing),
  every agreed field on each kind of item it applies to (action, RAID item, decision, milestone, promise), the tasks (link, a
  follow-on action, a risk from an action, a promise, chase, go, quick facts, Claude drafts), the confirm list, the Never list,
  never more than one existing item, and nothing written by a read.
- What it stages goes through the real apply: one proposal, one apply, one undo, even for a new item with its link (`@n`).

Run: python3 dev/tests/test_sneak_peek_read.py     (quick tier: no Chrome, no model)
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
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
from test_tracker import Vault  # noqa: E402
import sneak_peek  # noqa: E402

NOW = "2026-10-14 10:00"          # a Wednesday
SRC = "projects/ABC Example Programme/minutes/2026-10-01 Steering.docx — Actions"
PEOPLE = """# People register

## People

| Full name | Email | Aliases | Organisation | Role | Hidden | Labels |
|-----------|-------|---------|--------------|------|--------|--------|
| Alan Carter | alan@example.com | Alan | Brightwater | Programme manager |  |  |
| Tom Reid | tom@example.com | Tom | Kestrel Group | Lead |  |  |
| Leo Marsh | leo@example.com | Leo | Kestrel Group | Tester |  |  |
| Sam Patel | sam.p@example.com |  | Brightwater | Analyst |  |  |
| Sam Okafor | sam.o@example.com |  | Kestrel Group | Engineer |  |  |
| Chris Dunn | robin@example.com | Chris | Larkspur | Sponsor |  |  |
"""


def new(n, table, **values):
    return {"n": n, "op": "new", "table": table, "values": values, "match": "strong", "flags": [], "decision": "approved"}


class SneakCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = v = Vault()
        v.run("init")
        (v.root / "projects/_portfolio/people-register.md").write_text(PEOPLE, encoding="utf-8")
        v.propose("setup", [
            new(1, "workstreams", project="ABC", name="Testing", created="2026-10-01", source="setup"),
            new(2, "workstreams", project="ABC", name="Discovery", created="2026-09-01", status="Closed", source="setup"),
            new(3, "milestones", project="ABC", name="Northgate UAT complete", baseline_date="2026-11-06", forecast_date="2026-11-06",
                source="setup"),
            new(4, "actions", project="ABC", description="Share the Northgate UAT plan", owner="Tom Reid",
                due_date="2026-10-17", raised="2026-10-01", source=SRC),
            new(5, "raid", project="ABC", type="Risk", description="Northgate's test environment isn't ready for UAT", owner="Tom Reid",
                impact="High", likelihood="Medium", response_action="Agree dates with Northgate", due_date="2026-10-20",
                raised="2026-10-01", source=SRC),
            new(6, "decisions", project="ABC", decision="Which four use cases go into Phase 2", made_by="Chris Dunn",
                status="Pending", needed_by="2026-10-23", source=SRC),
            new(7, "promises", project="ABC", promised_by="Alan Carter", promised_to="Tom Reid",
                description="Send the Northgate terms", due_date="2026-10-16", raised="2026-10-01", source=SRC),
            new(8, "actions", project="ABC", description="Book the test lab", owner="Alan Carter", raised="2026-10-01", source=SRC,
                client_visible=1, client_message="What it is: the test lab booking\nWhat it means for you: testing can start\n"
                                                 "What is being done: Alan is booking it now", labels=["Sensitive"]),
        ])
        v.run("apply")
        with closing(sqlite3.connect(v.root / "system/tracker.db")) as con:
            cls.A = con.execute("SELECT id FROM actions WHERE description = 'Share the Northgate UAT plan'").fetchone()[0]
            cls.A2 = con.execute("SELECT id FROM actions WHERE description = 'Book the test lab'").fetchone()[0]
            cls.R = con.execute("SELECT id FROM raid").fetchone()[0]
            cls.D = con.execute("SELECT id FROM decisions").fetchone()[0]
            cls.M = con.execute("SELECT id FROM milestones").fetchone()[0]
            cls.P = con.execute("SELECT id FROM promises").fetchone()[0]

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def read(self, item, text, **extra):
        env = {**os.environ, "CREAITE_NOW": NOW}
        r = subprocess.run([sys.executable, str(self.v.root / "system/scripts/sneak_peek.py"), "read"],
                           input=json.dumps({"id": item, "text": text, **extra}), capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def ch(self, out, field):
        return next((c for c in out["changes"] if c["field"] == field), None)

    def staged(self, out):
        self.assertTrue(out["stage"], out)
        return out["stage"]["items"]


class Dates(unittest.TestCase):
    def test_dates_in_alans_words_on_several_weekdays(self):
        p = sneak_peek.parse_date
        wed, fri, sun, mon = "2026-10-14", "2026-10-16", "2026-10-18", "2026-10-19"
        self.assertEqual(p("Friday", wed), "2026-10-16")
        self.assertEqual(p("friday", fri), "2026-10-23")              # on a Friday, "Friday" is a week today
        self.assertEqual(p("next Tuesday", wed), "2026-10-20")        # next week's Tuesday
        self.assertEqual(p("next tuesday", sun), "2026-10-20")        # Sunday: next week starts tomorrow
        self.assertEqual(p("next tuesday", mon), "2026-10-27")
        self.assertEqual(p("tuesday", mon), "2026-10-20")
        self.assertEqual(p("today", wed), wed)
        self.assertEqual(p("tomorrow", wed), "2026-10-15")
        self.assertEqual(p("in 3 days", wed), "2026-10-17")
        self.assertEqual(p("in two weeks", wed), "2026-10-28")
        self.assertEqual(p("next week", wed), "2026-10-21")
        self.assertEqual(p("end of the month", wed), "2026-10-31")
        self.assertEqual(p("20-10", wed), "2026-10-20")
        self.assertEqual(p("20/10/27", wed), "2027-10-20")
        self.assertEqual(p("by 05-01-2027", wed), "2027-01-05")
        self.assertIsNone(p("31-02", wed))
        self.assertIsNone(p("soonish", wed))

    def test_push_it_out(self):
        m = sneak_peek.PUSH.search("push it out a week")
        self.assertEqual(sneak_peek.shifted(m, "2026-10-17"), "2026-10-24")
        m = sneak_peek.PUSH.search("bring it forward 2 days")
        self.assertEqual(sneak_peek.shifted(m, "2026-10-17"), "2026-10-15")
        m = sneak_peek.PUSH.search("push it back three days")
        self.assertEqual(sneak_peek.shifted(m, "2026-10-17"), "2026-10-20")


class Fields(SneakCase):
    def test_owner_and_due_on_an_action_with_what_was_understood(self):
        text = "owner to Leo and due Friday"
        out = self.read(self.A, text)
        self.assertEqual(out["item"]["kind"], "action")
        self.assertEqual(self.ch(out, "owner")["to"], "Leo Marsh")
        due = self.ch(out, "due_date")
        self.assertEqual((due["from"], due["to"], due["to_shown"]), ("2026-10-17", "2026-10-16", "Friday 16-10-2026"))
        self.assertFalse(out["confirm"])
        self.assertEqual([text[u["start"]:u["end"]] for u in out["understood"]], ["owner to Leo", "due Friday"])
        item = self.staged(out)[0]
        self.assertEqual(item["op"], "update")
        self.assertEqual(item["changes"], {"owner": "Leo Marsh", "due_date": "2026-10-16"})
        self.assertTrue(item["based_on"])

    def test_two_matches_ask_which_and_a_pick_answers(self):
        out = self.read(self.A, "owner to Sam")
        self.assertEqual(out["choices"]["typed"], "sam")
        self.assertEqual({o["value"] for o in out["choices"]["options"]}, {"Sam Patel", "Sam Okafor"})
        self.assertIsNone(out["stage"])
        out = self.read(self.A, "owner to Sam", picks={"sam": "Sam Okafor"})
        self.assertEqual(self.ch(out, "owner")["to"], "Sam Okafor")
        self.assertIsNone(out["choices"])

    def test_no_match_changes_nothing(self):
        out = self.read(self.A, "owner to Zebedee")
        self.assertIsNone(out["stage"])
        self.assertIn("Zebedee", out["problems"][0])

    def test_me_and_at_names(self):
        self.assertEqual(self.ch(self.read(self.A, "assign to me"), "owner")["to"], "Alan Carter")
        self.assertEqual(self.ch(self.read(self.A, "owner to @Chris Dunn"), "owner")["to"], "Chris Dunn")

    def test_priority_status_workstream_milestone_on_an_action(self):
        out = self.read(self.A, "make it urgent and due next Tuesday")
        self.assertEqual(self.ch(out, "priority")["to"], "Urgent")
        self.assertEqual(self.ch(out, "due_date")["to"], "2026-10-20")
        out = self.read(self.A, "workstream to testing, milestone Northgate UAT complete")
        self.assertEqual(self.ch(out, "workstream")["to"], "Testing")
        self.assertEqual(self.ch(out, "milestone")["to"], self.M)
        self.assertIn("closed workstream", self.read(self.A, "workstream to Discovery")["problems"][0])
        self.assertIn("no workstream", self.read(self.A, "workstream to Finance")["problems"][0])
        out = self.read(self.A, "delayed")
        self.assertEqual(self.ch(out, "status")["to"], "Delayed")
        out = self.read(self.A, "close it")
        self.assertEqual(self.ch(out, "status")["to"], "Closed")
        self.assertTrue(out["offer_closing_update"])
        self.assertFalse(out["confirm"])
        out = self.read(self.A, "close it, add an update: Northgate signed off the plan")
        self.assertFalse(out["offer_closing_update"])
        self.assertEqual(self.ch(out, "latest_update")["to"], "Alan: Northgate signed off the plan. (14-10-2026)")

    def test_push_it_out_a_week_because_puts_the_reason_in_the_update(self):
        out = self.read(self.A, "push it out a week because Northgate's test dates slipped")
        self.assertEqual(self.ch(out, "due_date")["to"], "2026-10-24")
        self.assertEqual(self.ch(out, "latest_update")["to"],
                         "Alan: Due moved to 24-10-2026: Northgate's test dates slipped. (14-10-2026)")
        self.assertEqual(out["needs_claude"]["kind"], "sneak-update")
        self.assertTrue(out["needs_claude"]["optional"])
        self.assertEqual(out["needs_claude"]["request"]["mode"], "reason")

    def test_impact_and_likelihood_recalculate_priority_on_a_risk(self):
        out = self.read(self.R, "likelihood high")
        self.assertEqual(self.ch(out, "likelihood")["to"], "High")
        pr = self.ch(out, "priority")
        self.assertTrue(pr["derived"])
        self.assertEqual((pr["from"], pr["to"]), ("High", "Urgent"))
        self.assertEqual(self.staged(out)[0]["changes"], {"likelihood": "High"})        # the tracker works priority out
        self.assertIn("impact and likelihood", self.read(self.R, "make it urgent")["problems"][0])
        out = self.read(self.R, "target next Wednesday, response: Escalate to Northgate's lead")
        self.assertEqual(self.ch(out, "due_date")["to"], "2026-10-21")
        self.assertEqual(self.ch(out, "response_action")["to"], "Escalate to Northgate's lead")
        self.assertIn("open, closed or cancelled", self.read(self.R, "delayed")["problems"][0])

    def test_labels_and_client_visible(self):
        out = self.read(self.A, "label it Sensitive")
        self.assertEqual(self.ch(out, "labels")["to"], ["Sensitive"])
        self.assertEqual(self.staged(out)[0]["changes"], {"labels": ["Sensitive"]})
        self.assertIn("no label", self.read(self.A, "label it Shiny")["problems"][0])
        out = self.read(self.A, "make it client-visible")                    # its client message isn't written
        self.assertIsNone(out["stage"])
        self.assertIn("client message", out["problems"][0])
        self.assertEqual(out["needs_claude"]["kind"], "client")
        out = self.read(self.A2, "not client-visible")
        self.assertEqual(self.ch(out, "client_visible")["to"], 0)
        self.assertFalse(out["confirm"])

    def test_decision_fields(self):
        out = self.read(self.D, "needed by Friday, decision maker to Sam Patel")
        self.assertEqual(self.ch(out, "needed_by")["to"], "2026-10-16")
        self.assertEqual(self.ch(out, "made_by")["to"], "Sam Patel")
        out = self.read(self.D, "revisit on 30-11")
        self.assertEqual(self.ch(out, "revisit")["to"], "2026-11-30")
        out = self.read(self.D, "revisit if adoption falls below 60%")
        self.assertEqual(self.ch(out, "revisit")["to"], "Revisit if adoption falls below 60%")
        self.assertIn("drafted by Claude", self.read(self.D, "reasoning: because")["problems"][0])
        self.assertIn("Only decisions", self.read(self.A, "revisit on 30-11")["problems"][0])

    def test_milestone_fields(self):
        out = self.read(self.M, "forecast to 13-11, owner to Chris")
        self.assertEqual(self.ch(out, "forecast_date")["to"], "2026-11-13")
        self.assertEqual(self.ch(out, "owner")["to"], "Chris Dunn")
        self.assertFalse(out["confirm"])
        out = self.read(self.M, "forecast to 20-11 because Northgate's environment is late")
        self.assertEqual(self.ch(out, "internal_note")["to"], "Northgate's environment is late")

    def test_promise_fields(self):
        out = self.read(self.P, "due next Tuesday")
        self.assertEqual(self.ch(out, "due_date")["to"], "2026-10-20")
        out = self.read(self.P, "done")
        self.assertEqual(self.ch(out, "status")["to"], "Done")


class Confirms(SneakCase):
    def test_the_confirm_list(self):
        cases = [(self.A, "rename to Share the Northgate UAT plan and test schedule", "description"),
                 (self.A, "cancel it", "status"), (self.R, "cancel it", "status"),
                 (self.D, "withdraw it", "status"), (self.D, "Chris decided use cases 1, 2 and 4", "status"),
                 (self.A2, "remove the Sensitive label", "labels"), (self.R, "this has happened", "type"),
                 (self.M, "state at risk", "state"), (self.M, "mark it done", "status"), (self.P, "drop it", "status"),
                 (self.D, "reword to Which use cases go into Phase 2", "decision")]
        for item, text, field in cases:
            out = self.read(item, text)
            self.assertTrue(out["confirm"], (text, out))
            self.assertTrue(self.ch(out, field)["confirm"], text)
            self.assertTrue(out["stage"], (text, out["problems"]))

    def test_decision_made_records_its_date_and_who(self):
        out = self.read(self.D, "Chris decided use cases 1, 2 and 4")
        ch = self.staged(out)[0]["changes"]
        self.assertEqual((ch["status"], ch["date"], ch["decision"]), ("Made", "2026-10-14", "Use cases 1, 2 and 4"))

    def test_rewording_shows_old_and_new(self):
        out = self.read(self.A, "rename to Share the plan")
        c = self.ch(out, "description")
        self.assertEqual((c["from"], c["to"]), ("Share the Northgate UAT plan", "Share the plan"))

    def test_a_milestone_state_better_than_the_dates_needs_a_reason(self):
        self.v.propose("late", [{"n": 1, "op": "update", "table": "milestones", "id": self.M,
                                 "changes": {"forecast_date": "2026-11-20"}, "match": "strong", "flags": [], "decision": "approved"}])
        self.v.run("apply")
        try:
            out = self.read(self.M, "state on track")
            self.assertIsNone(out["stage"])
            self.assertIn("needs a reason", out["problems"][0])
            out = self.read(self.M, "state on track because Northgate caught up")
            self.assertEqual(self.ch(out, "state")["to"], "On track")
            self.assertEqual(self.ch(out, "state_reason")["to"], "Northgate caught up")
        finally:
            self.v.run("undo")

    def test_a_risk_becoming_an_issue_keeps_its_response(self):
        out = self.read(self.R, "this has happened")
        self.assertEqual(self.staged(out)[0]["changes"], {"type": "Issue"})


class Never(SneakCase):
    def test_the_never_list_is_refused_with_where_to_go(self):
        cases = [("email Tom about this", "draft_chase"), ("send it to Tom on Teams", "draft_chase"),
                 ("close all of Tom's overdue", "ask"), ("set the health to at risk", "project_page"),
                 ("change the settings", "settings"), ("add a person to the people register", "people"),
                 ("baseline to 06-11", "milestone_form"), ("project to DEF", "cx_edit"), ("change the source", "cx_edit"),
                 ("delete it", "cx_edit"), ("why is this late?", "ask")]
        for text, where in cases:
            out = self.read(self.A if "baseline" not in text else self.M, text)
            self.assertEqual((out["refused"] or {}).get("point_to"), where, (text, out))
            self.assertIsNone(out["stage"], text)
            self.assertEqual(out["changes"], [], text)

    def test_a_read_writes_nothing(self):
        before = self.v.snapshot()
        staging = sorted(p.name for p in (self.v.root / "system/staging").iterdir())
        for text in ("owner to Leo", "add an action for Leo to confirm the test dates, due Friday", "blocked by " + self.R):
            self.read(self.A, text)
        self.assertEqual(self.v.snapshot(), before)
        self.assertEqual(sorted(p.name for p in (self.v.root / "system/staging").iterdir()), staging)

    def test_an_unknown_item_and_a_bad_request(self):
        self.assertFalse(self.read("ABC-A-999", "close it")["ok"])
        r = subprocess.run([sys.executable, str(self.v.root / "system/scripts/sneak_peek.py"), "read"], input="[]",
                           capture_output=True, text=True)
        self.assertFalse(json.loads(r.stdout)["ok"])


class Tasks(SneakCase):
    def test_link_it_both_ways_both_ends_must_exist(self):
        out = self.read(self.A, f"blocked by {self.R}")
        self.assertEqual(out["task"]["kind"], "link")
        self.assertEqual(self.staged(out)[0]["values"]["from_item"], self.R)
        self.assertEqual(self.staged(out)[0]["values"]["to_item"], self.A)
        out = self.read(self.A, f"this blocks {self.M}")
        self.assertEqual((out["task"]["from_item"], out["task"]["to_item"]), (self.A, self.M))
        self.assertIn("no item", self.read(self.A, "blocked by ABC-777")["problems"][0])

    def test_a_follow_on_action_a_risk_and_a_promise_are_new_items_linked_in_one_proposal(self):
        out = self.read(self.A, "add an action for Leo to confirm the test dates, due Friday")
        items = self.staged(out)
        self.assertEqual([i["table"] for i in items], ["actions", "links"])
        self.assertEqual(items[0]["values"]["owner"], "Leo Marsh")
        self.assertEqual(items[0]["values"]["due_date"], "2026-10-16")
        self.assertEqual(items[1]["values"]["from_item"], "@1")
        out = self.read(self.A, "raise a risk that Northgate's test dates slip")
        v = self.staged(out)[0]["values"]
        self.assertEqual((v["type"], v["impact"], v["likelihood"]), ("Risk", "Medium", "Medium"))
        self.assertIn("raised from an action", self.read(self.R, "raise a risk that it slips")["problems"][0])
        out = self.read(self.A, "I promised Tom the Northgate terms by Friday")
        items = self.staged(out)
        self.assertEqual((items[0]["values"]["promised_to"], items[0]["values"]["promised_by"]),
                         ("Tom Reid", "Alan Carter"))
        self.assertEqual(items[1]["values"]["to_item"], "@1")

    def test_staged_items_apply_in_one_step_and_undo_in_one(self):
        out = self.read(self.A, "add an action for Leo to confirm the test dates, due Friday")
        self.v.propose("sneak", [dict(it, n=i + 1, match="strong", flags=[], decision="approved")
                                 for i, it in enumerate(out["stage"]["items"])], source_run="dashboard")
        self.v.run("apply")
        new_id = next(a["id"] for a in self.v.rows("actions") if a["description"] == "Confirm the test dates")
        self.assertIn((new_id, self.A), [(l["from_item"], l["to_item"]) for l in self.v.rows("links")])
        self.v.run("undo")
        self.assertFalse(any(a["description"] == "Confirm the test dates" for a in self.v.rows("actions")))
        self.assertEqual(self.v.rows("links"), [])

    def test_undo_puts_back_the_sibling_reference_so_a_reapply_links_the_item_it_creates(self):
        out = self.read(self.A, "add an action for Leo to confirm the dates again, due Friday")
        p = self.v.propose("sneak-undo", [dict(it, n=i + 1, match="strong", flags=[], decision="approved")
                                          for i, it in enumerate(out["stage"]["items"])], source_run="dashboard")
        self.v.run("apply")
        old_id = next(a["id"] for a in self.v.rows("actions") if a["description"] == "Confirm the dates again")
        self.v.run("undo")
        back = json.loads(p.read_text())
        link = back["items"][1]
        self.assertEqual(link["values"]["from_item"], "@1")                  # never the ID the undone apply gave
        self.assertNotIn("refs", link)
        self.assertEqual(link["decision"], "pending")
        other = self.v.propose("unrelated", [new(1, "actions", project="ABC", description="Unrelated work", owner="Alan Carter",
                                                 raised="2026-10-01", source=SRC)])
        self.v.run("apply", other.name)                                       # takes the old ID
        self.assertIn(old_id, [a["id"] for a in self.v.rows("actions") if a["description"] == "Unrelated work"])
        for it in back["items"]:
            it["decision"] = "approved"
        p.write_text(json.dumps(back))
        self.v.run("apply", p.name)
        made = next(a["id"] for a in self.v.rows("actions") if a["description"] == "Confirm the dates again")
        self.assertNotEqual(made, old_id)
        pairs = [(l["from_item"], l["to_item"]) for l in self.v.rows("links")]
        self.assertIn((made, self.A), pairs)
        self.assertNotIn((old_id, self.A), pairs)
        self.v.run("undo")                                                    # leave the class's vault as it was
        q = self.v.propose("undo-unrelated", [{"n": 1, "op": "cancel", "table": "actions", "id": old_id, "match": "strong",
                                               "flags": [], "decision": "approved"}])
        self.v.run("apply", q.name)
        p.unlink()

    def test_a_bad_sibling_reference_after_undo_is_held_in_review(self):
        out = self.read(self.A, "add an action for Leo to check the lab, due Friday")
        p = self.v.propose("sneak-bad", [dict(it, n=i + 1, match="strong", flags=[], decision="approved")
                                         for i, it in enumerate(out["stage"]["items"])], source_run="dashboard")
        self.v.run("apply")
        self.v.run("undo")
        back = json.loads(p.read_text())
        for it in back["items"]:
            it["decision"] = "approved"
        back["items"][1]["values"]["from_item"] = "@7"
        p.write_text(json.dumps(back))
        before = self.v.rows("links")
        r = self.v.run("apply", p.name, ok=False)
        self.assertIn("isn't a new item written before it", r.stdout)
        self.assertIn(f"Held in Review, not applied: {p.name} item 2:", r.stdout)     # #280: the bad link is held, never written
        self.assertEqual(self.v.rows("links"), before)
        link = json.loads(p.read_text())["items"][1]
        self.assertEqual((link["decision"], "invalid" in link["flags"]), ("pending", True))
        self.v.run("undo")                                                    # the action #280 let through: the vault as it was
        self.assertFalse(any(a["description"] == "Check the lab" for a in self.v.rows("actions")))
        p.unlink()

    def test_a_sibling_reference_must_name_a_new_item_before_it(self):
        before = self.v.rows("links")
        p = self.v.propose("badref", [new(1, "links", from_item="@2", to_item=self.A, source="test")], source_run="dashboard")
        r = self.v.run("apply", ok=False)
        self.assertIn("isn't a new item written before it", r.stdout)
        self.assertEqual(self.v.rows("links"), before)
        p.unlink()

    def test_the_chase_hand_off_says_draft_email_not_draft_chase(self):
        """#153 finding 2: the button was renamed Draft email; the hand-off's marked words and the help line say the same."""
        out = self.read(self.A, "chase Tom, firmer")
        self.assertIn("Draft email to Tom Reid, Firmer. Nothing is sent", json.dumps(out))
        self.assertNotIn("Draft chase", json.dumps(out))
        src = (Path(__file__).resolve().parents[2] / "system/scripts/sneak_peek.py").read_text()
        self.assertNotIn("Draft chase", src)

    def test_chase_goto_facts(self):
        out = self.read(self.A, "chase Tom, firmer")
        self.assertEqual(out["task"], {"kind": "chase", "pane": {"id": self.A, "tone": 2, "to": "Tom Reid"}})
        self.assertIsNone(out["stage"])
        out = self.read(self.A, "open the source")
        self.assertEqual(out["task"]["target"], "source")
        self.assertEqual(out["task"]["ref"], SRC)
        self.assertEqual(self.read(self.A, "open the project")["task"]["ref"], "ABC")
        self.assertIn("no milestone", self.read(self.A, "show the milestone")["problems"][0])
        out = self.read(self.A, "when was this last chased?")
        self.assertEqual(out["task"]["kind"], "facts")
        self.assertEqual(out["task"]["rows"][0]["text"], "Not chased yet.")
        out = self.read(self.A, "where did this come from?")
        self.assertEqual(out["task"]["rows"][0]["text"], SRC)
        self.assertEqual(self.read(self.A, "what does this block?")["task"]["topic"], "links")

    def test_claude_drafts_and_with_drafts_off(self):
        out = self.read(self.A, "write a client message")
        self.assertEqual(out["needs_claude"]["request"], {"kind": "client", "id": self.A})
        out = self.read(self.D, "draft the options")
        self.assertEqual(out["needs_claude"]["request"], {"kind": "thinking", "id": self.D, "field": "options"})
        self.assertIn("no update to tidy", self.read(self.A2, "tidy the update")["problems"][0])
        cfg = self.v.root / "system/config/settings.json"
        before = cfg.read_text()
        data = json.loads(before)
        data["drafting"] = {**(data.get("drafting") or {}), "client": False, "update": False}
        cfg.write_text(json.dumps(data))
        try:
            out = self.read(self.A, "write a client message")
            self.assertTrue(out["needs_claude"]["off"])
            self.assertIsNone(out["needs_claude"]["request"])
            self.assertIn("AI drafts are off", out["needs_claude"]["why"])
            out = self.read(self.A, "push it out a week because Northgate slipped")            # the plain-code part still works
            self.assertTrue(self.ch(out, "latest_update"))
            self.assertTrue(out["needs_claude"]["off"])
        finally:
            cfg.write_text(before)


class SneakDraft(SneakCase):
    """The new draft kind, sneak-update (drafts.py context; the model's part is the drafts module's own, tested there)."""

    def context(self, body):
        r = subprocess.run([sys.executable, str(self.v.root / "system/scripts/drafts.py"), "context"], input=json.dumps(body),
                           capture_output=True, text=True, env={**os.environ, "CREAITE_NOW": NOW})
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_tidy_and_reason_and_their_refusals(self):
        out = self.context({"kind": "sneak-update", "id": self.A, "mode": "reason", "text": "Northgate's test dates slipped"})
        self.assertEqual(out["feature"], "update")
        self.assertIn("Turn Alan's reason into the action's latest update", out["prompt"])
        self.assertIn("Northgate's test dates slipped", out["prompt"])
        self.assertEqual(len(out["sources"]), 1)
        self.assertIn("no update to tidy", self.context({"kind": "sneak-update", "id": self.A2, "mode": "tidy"})["nothing"])
        self.assertIn("Only actions", self.context({"kind": "sneak-update", "id": self.R, "mode": "tidy"})["refused"])
        self.assertIn("tidying", self.context({"kind": "sneak-update", "id": self.A, "mode": "other"})["refused"])


class Route(SneakCase):
    """POST /api/sneak/read on the real live server: token-checked, read only."""

    @classmethod
    def setUpClass(cls):
        import re
        import socket
        import time
        import urllib.request
        super().setUpClass()
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            cls.port = s.getsockname()[1]
        cls.base = f"http://127.0.0.1:{cls.port}"
        env = {**os.environ, "CREAITE_PORT": str(cls.port), "CREAITE_NOW": NOW}
        cls.proc = subprocess.Popen([sys.executable, str(cls.v.root / "system/scripts/live_server.py")], env=env,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(150):
            try:
                urllib.request.urlopen(cls.base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        html = urllib.request.urlopen(cls.base + "/").read().decode()
        cls.token = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)
        super().tearDownClass()

    def post(self, path, body, token=True):
        import urllib.error
        import urllib.request
        headers = {"Content-Type": "application/json", **({"X-Creaite-Token": self.token} if token else {})}
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST", headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            e.close()
            return e.code, None

    def test_the_route_reads_and_writes_nothing(self):
        before = self.v.snapshot()
        code, out = self.post("/api/sneak/read", {"id": self.A, "text": "owner to Leo, due Friday"})
        self.assertEqual(code, 200)
        self.assertTrue(out["ok"], out)
        self.assertEqual(out["stage"]["items"][0]["changes"], {"owner": "Leo Marsh", "due_date": "2026-10-16"})
        code, out = self.post("/api/sneak/read", {"id": self.A, "text": "email Tom"})
        self.assertEqual(out["refused"]["point_to"], "draft_chase")
        code, out = self.post("/api/sneak/read", {"id": 5})
        self.assertFalse(out["ok"])
        self.assertEqual(self.v.snapshot(), before)

    def test_the_route_needs_the_token(self):
        code, out = self.post("/api/sneak/read", {"id": self.A, "text": "close it"}, token=False)
        self.assertEqual(code, 403)

    def test_the_new_draft_kind_is_known_to_the_draft_route(self):
        code, out = self.post("/api/draft", {"kind": "sneak-update", "id": self.R, "mode": "tidy"})
        self.assertEqual(code, 200)
        self.assertIn("Only actions", out["message"])                     # refused before any model call


if __name__ == "__main__":
    unittest.main()
