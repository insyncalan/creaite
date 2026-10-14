"""Sprint 5 item 4 (BL-92): the steering-committee one-pager.

Run: python3 dev/tests/test_steerco.py
Each test builds a throwaway vault (test_tracker.Vault) with fictional data and runs the real scripts there. The clock is
fixed with CREAITE_NOW so dates are the same every day.
"""
import json
import os
import re
import sqlite3
import subprocess
import sys
import unittest
import zipfile
from contextlib import closing
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import ABC, Vault  # noqa: E402
from test_workstreams import add_project  # noqa: E402

TODAY = date(2026, 10, 9)
NOW = f"{TODAY} 09:00"
CM = ("What it is: The data feed is late.\nWhat it means for you: UAT may start later.\n"
      "What is being done: We are chasing the client weekly.")


def d(n):
    return (TODAY + timedelta(days=n)).isoformat()


def new(n, table, **v):
    return {"n": n, "op": "new", "table": table, "match": "strong", "flags": [], "decision": "approved",
            "values": {"project": "ABC", "source": f"{ABC}/minutes/2026-10-01 Steering.docx — Actions", **v}}


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        self.v.propose("seed", [
            new(1, "milestones", name="Build complete", baseline_date=d(-30), forecast_date=d(-30), status="Done"),
            new(2, "milestones", name="UAT start", baseline_date=d(10), forecast_date=d(24), client_visible=1,
                client_message="User testing starts once the data feed arrives."),   # BL-186: named to a client only when client-visible
            new(3, "milestones", name="Go-live", baseline_date=d(60), forecast_date=d(60)),
            # actions: closed in the period, overdue, due soon, due later, a client-visible one, a sensitive one
            new(4, "actions", description="Send the revised SOW", owner="Omar Ali", status="Closed", raised=d(-12), closed=d(-3)),
            new(5, "actions", description="Escalate data access to the client CIO", owner="Alan Carter", due_date=d(-2), priority="Urgent", raised=d(-8)),
            new(6, "actions", description="Book the UAT environment", owner="Sara Example", due_date=d(5), raised=d(-8)),
            new(7, "actions", description="Plan the go-live weekend", owner="Omar Ali", due_date=d(40), raised=d(-8)),
            new(8, "actions", description="Agree the pilot success criteria", owner="Sara Example (Example Client Ltd)", due_date=d(6),
                raised=d(-8), client_visible=1,
                client_message="What it is: Agree the success criteria for the pilot.\nWhat it means for you: You sign off the scope.\nWhat is being done: We sent a draft."),
            new(9, "actions", description="Renegotiate the licence price with the vendor", owner="Alan Carter", due_date=d(3), raised=d(-8)),
            # RAID
            new(10, "raid", type="Risk", description="Data access delayed so UAT slips", impact="High", likelihood="High", raised=d(-6),
                owner="Omar Ali", response_action="Escalating to the client CIO", client_visible=1, client_message=CM),
            new(11, "raid", type="Issue", description="Test licences not ordered", impact="Medium", likelihood="High", raised=d(-20), owner="Sara Example"),
            new(12, "raid", type="Dependency", description="Data feed from the client", raised=d(-15), owner="Sara Example (Example Client Ltd)",
                due_date=d(30), milestone="ABC-M-002", client_visible=1, client_message=CM),
            # decisions
            new(13, "decisions", decision="Extend the pilot by two weeks", status="Pending", made_by="Sara Example", needed_by=d(-3)),
            new(14, "decisions", decision="Choose the UAT venue", status="Pending", made_by="Alan Carter", needed_by=d(5)),
            new(15, "decisions", decision="Share the pilot plan with the client", status="Pending", made_by="Jane Doe", needed_by=d(7),
                client_visible=1, client_message="We would like your confirmation of the pilot plan."),
            new(16, "decisions", decision="Go-live moves two weeks", date=d(-4), made_by="Jane Doe", client_visible=1,
                client_message="The go-live moves by two weeks to allow for the data feed."),
            new(17, "decisions", decision="Drop the pricing option from the proposal", date=d(-2), made_by="Alan Carter", client_visible=1,
                client_message="The proposal no longer includes the pricing option."),
        ])
        self.v.run("apply")
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:     # history the report reads, set directly (fictional data)
            con.execute("UPDATE projects SET health = 'At risk', health_reason = 'Data access is late and UAT may start later' WHERE code = 'ABC'")
            for i, h in enumerate(["On track", "On track", "At risk", "At risk"]):
                con.execute("INSERT INTO updates (week_ending, project, health, summary) VALUES (?, 'ABC', ?, 'x')",
                            ((TODAY - timedelta(days=(TODAY.weekday() - 4) % 7 + 7 * (3 - i))).isoformat(), h))
            con.execute("INSERT INTO change_log (at, apply_id, tbl, item_id, field, old_value, new_value, op, via) VALUES "
                        "(?, NULL, 'milestones', 'ABC-M-002', 'forecast_date', ?, ?, 'update', 'test')", (f"{d(-5)} 10:00:00", d(17), d(24)))
            con.commit()
        self.v.propose("links", [
            {"n": 1, "op": "new", "table": "links", "match": "strong", "flags": [], "decision": "approved",
             "values": {"from_item": "ABC-A-002", "to_item": "ABC-A-003", "source": "Alan (cx-edit)"}}])
        self.v.run("apply")

    def tearDown(self):
        self.v.cleanup()

    def script(self, name, *args, ok=True):
        r = subprocess.run([sys.executable, str(self.v.root / "system/scripts" / name), *args], cwd=self.v.root,
                           env={**os.environ, "CREAITE_NOW": NOW}, capture_output=True, text=True)
        if ok and r.returncode != 0:
            raise AssertionError(f"{name} {args} failed:\n{r.stdout}\n{r.stderr}")
        return r

    def data(self, *args):
        return json.loads(self.script("report.py", "steerco-data", "ABC", *args).stdout)

    def label(self, item_id, name="Sensitive"):
        self.v.propose(f"lab-{item_id}", [{"n": 1, "op": "new", "table": "item_labels", "match": "strong", "flags": [], "decision": "approved",
                                           "values": {"item_id": item_id, "label": name, "reason": "reads as criticism"}}])
        self.v.run("apply")

    def stage(self, ok=True, **spec):
        f = self.v.root / "system/staging/drafts/steerco.json"
        f.write_text(json.dumps({"code": "ABC", **spec}))
        return self.script("report.py", "steerco-stage", str(f), ok=ok)

    def staged(self):
        return json.loads(sorted((self.v.root / "system/staging").glob("proposed-2*-steerco*.json"))[-1].read_text())

    def draft_text(self, block=None):
        block = block or self.staged()["report"]
        path = self.v.root / block["draft"]
        with zipfile.ZipFile(path) as z:
            return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", z.read("word/document.xml").decode("utf-8")))


class DataTests(Base):
    def test_the_internal_facts(self):
        got = self.data()
        self.assertEqual((got["version"], got["steerco_date"], got["health"]), ("internal", "2026-10-09", "At risk"))
        self.assertEqual(got["since"], d(-14))                                                 # no earlier one-pager: the last 14 days
        self.assertEqual(got["trend"], "Over the last 4 weekly updates: On track (2) → At risk (2).")
        self.assertIn("Milestone moved: UAT start, " + f"{d(17)[8:]}-{d(17)[5:7]}-{d(17)[:4]}", " ".join(got["changes"]))
        self.assertIn("New risk: ABC-007 Data access delayed so UAT slips", got["changes"])
        self.assertTrue(any(c.startswith("Decided: Go-live moves two weeks") for c in got["changes"]))
        self.assertTrue(any(c.startswith("Closed: Send the revised SOW") for c in got["changes"]))
        self.assertEqual([m["M_TEXT"] for m in got["milestones"]], ["Build complete", "UAT start", "Go-live"])
        self.assertEqual(got["milestones"][1]["M_STATUS"], "Slipped")          # BL-186: the five states
        self.assertEqual([r["R_ID"] for r in got["risks"]], ["ABC-007", "ABC-008"])           # by priority; the dependency isn't a risk
        self.assertEqual(got["risks"][0]["R_OWNER"], "Omar Ali")
        self.assertIn("Response: Escalating to the client CIO", got["risks"][0]["R_TEXT"])
        self.assertIn("No response yet.", got["risks"][1]["R_TEXT"])

    def test_decisions_needed_from_the_committee_and_from_alan(self):
        got = self.data()["decisions_needed"]
        self.assertEqual(got[0], "For the committee: Extend the pilot by two weeks — from Sara Example, needed by 06-10-2026 (3 days overdue)")
        self.assertTrue(got[1].startswith("For Alan: Choose the UAT venue — from Alan Carter, needed by 14-10-2026"))
        self.assertEqual(len(got), 3)

    def test_blockers_use_milestone_links_and_the_links_table(self):
        got = self.data()["blockers"]
        self.assertTrue(got[0].startswith("ABC-009 Data feed from the client (Sara Example (Example Client Ltd), due 08-11-2026) blocks UAT start (forecast 02-11-2026)"), got)
        self.assertIn("isn't due until", got[0])                                               # the dependency's date warning
        self.assertIn("ABC-A-002 Escalate data access to the client CIO blocks ABC-A-003 Book the UAT environment", got)

    def test_flow_and_the_next_period(self):
        got = self.data()
        self.assertTrue(got["flow"])
        nxt = got["next_period"]
        self.assertTrue(nxt[0].startswith("Escalate data access to the client CIO — Alan Carter, due 07-10-2026 (overdue)"), nxt)   # overdue first
        self.assertEqual(len(nxt), 4)                                                           # not "Plan the go-live weekend" (due in 40 days)
        self.assertFalse(any("go-live weekend" in x for x in nxt))

    def test_since_is_the_last_one_pager_in_the_steerco_folder(self):
        folder = self.v.root / "projects/ABC Example Programme/reports/Steerco"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{d(-7)} Example Programme Steerco one-pager.docx").write_bytes(b"x")
        got = self.data()
        self.assertEqual((got["last_steerco"], got["since"]), (d(-7), d(-7)))
        self.assertTrue(any(c.startswith("Closed: Send the revised SOW") for c in got["changes"]))      # closed 3 days ago: after the last one
        self.assertFalse(any(c.startswith("New risk: ABC-008") for c in got["changes"]))                 # raised 20 days ago: before it
        self.assertEqual(self.data("--since", d(-30))["since"], d(-30))

    def test_a_sensitive_item_is_marked_in_the_internal_facts(self):
        self.label("ABC-A-006")
        got = self.data()
        self.assertEqual(got["sensitive"], ["ABC-A-006"])
        self.assertTrue(any("Renegotiate the licence price with the vendor [Sensitive]" in x for x in got["next_period"]))


class ClientSafeTests(Base):
    def test_only_client_visible_items_in_their_client_words(self):
        got = self.data("--version", "client")
        self.assertEqual(got["version"], "client")
        self.assertEqual(got["flow"], "")                                                       # an internal measure
        self.assertEqual(got["risks"], [{"R_ID": "—", "R_TEXT": "Risk: The data feed is late. UAT may start later. We are chasing the client weekly.",
                                         "R_PRIORITY": "—", "R_OWNER": "—"}])
        self.assertEqual(got["decisions_needed"], ["We would like your confirmation of the pilot plan. (by 16-10-2026)"])
        self.assertTrue(any(c == "Decided: The go-live moves by two weeks to allow for the data feed." for c in got["changes"]))
        self.assertEqual(len(got["blockers"]), 1)
        self.assertIn("waiting on this for UAT start", got["blockers"][0])
        self.assertEqual([x for x in got["next_period"]], ["Agree the success criteria for the pilot. — Sara Example (Example Client Ltd), due 15-10-2026"])
        blob = json.dumps(got)
        self.assertEqual([m["M_STATUS"] for m in got["milestones"]], ["Expected later"])     # BL-186: client-visible milestones, in the client's words
        for internal in ("Extend the pilot", "Choose the UAT venue", "Renegotiate", "Escalate data access", "Test licences", "ABC-A-006", "ABC-D-010", "ABC-M-", "Go-live", "Build complete"):
            self.assertNotIn(internal, blob)

    def test_a_client_visible_item_with_an_excluding_label_is_left_out_and_reported(self):
        self.label("ABC-D-014")                                                                  # "Drop the pricing option": client-visible and Sensitive
        got = self.data("--version", "client")
        self.assertFalse(any("pricing" in c for c in got["changes"]))
        self.assertEqual(got["labelled_but_excluded"], ["ABC-D-014"])
        self.assertEqual(got["omitted"], ["ABC-D-014 is flagged client-visible and labelled Sensitive: left out (say \"include ABC-D-014\" to keep it)"])
        kept = self.data("--version", "client", "--include", "ABC-D-014")
        self.assertTrue(any("pricing" in c for c in kept["changes"]))
        self.assertEqual(kept["omitted"], [])

    def test_incomplete_client_messaging_is_reported_not_guessed(self):
        self.v.propose("cv", [{"n": 1, "op": "update", "table": "actions", "id": "ABC-A-007", "match": "strong", "flags": [], "decision": "approved",
                               "changes": {"client_visible": 0}}])
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            con.execute("UPDATE actions SET client_visible = 1 WHERE id = 'ABC-A-003'")        # visible, but its messaging is the empty headings
            con.commit()
        self.assertIn("ABC-A-003 needs its client messaging completed", self.data("--version", "client")["omitted"])


class StageTests(Base):
    def test_the_internal_draft_has_every_section_and_is_staged_for_approval(self):
        out = self.stage(version="internal").stdout
        block = self.staged()["report"]
        self.assertEqual((block["kind"], block["version"], block["report_decision"], block["project"]), ("steerco", "internal", "pending", "ABC"))
        text = self.draft_text()
        for heading in ("Overall Status", "What Changed", "Milestones", "Top Risks and Issues", "Decisions Needed", "Blockers", "Flow", "Next Period"):
            self.assertIn(heading, text)
        self.assertIn("Example Programme Steering Committee One-Pager", text)                    # the project's name (BL-101)
        self.assertNotIn("ABC Example Programme", text)                                           # never its code
        self.assertIn("AT RISK", text)
        self.assertIn("Internal version: not for the client.", text)
        self.assertIn("For the committee: Extend the pilot by two weeks", text)
        self.assertRegex(text, r"UAT start \S+ \S+ Slipped ")   # BL-186: the five states
        self.assertNotIn("{{", text)
        self.assertIn(f"On approval it is filed as: projects/ABC Example Programme/reports/Steerco/{TODAY} Example Programme Steerco one-pager.docx", out)
        self.assertEqual([o["op"] for o in block["file_ops"]], ["mkdir", "copy", "remove"])      # the Steerco folder is made if it isn't there

    def test_a_section_with_nothing_to_say_is_left_out_not_shown_empty(self):
        add_project(self.v, "DEF", "Quiet Project")
        self.v.run("init")
        f = self.v.root / "system/staging/drafts/steerco.json"
        f.write_text(json.dumps({"code": "DEF"}))
        out = self.script("report.py", "steerco-stage", str(f)).stdout
        text = self.draft_text(json.loads(sorted((self.v.root / "system/staging").glob("proposed-2*-steerco-DEF*.json"))[-1].read_text())["report"])
        self.assertIn("Overall Status", text)
        for heading in ("What Changed", "Milestones", "Top Risks and Issues", "Decisions Needed", "Blockers", "Next Period"):
            self.assertNotIn(heading, text)
        self.assertNotIn("None recorded", text)
        self.assertIn("Left out (nothing to say): ", out)

    def test_the_internal_version_marks_sensitive_items_and_warns(self):
        self.label("ABC-A-006")
        out = self.stage(version="internal").stdout
        text = self.draft_text()
        self.assertIn("Renegotiate the licence price with the vendor [Sensitive]", text)
        self.assertIn("Sensitive: 1 item below carry a label (ABC-A-006)", text)
        self.assertIn("Includes 1 sensitive item(s), marked in the document: ABC-A-006", out)

    def test_the_client_safe_draft_has_none_of_the_internal_content(self):
        out = self.stage(version="client").stdout
        text = self.draft_text()
        self.assertIn("Client-safe version.", text)
        for internal in ("Extend the pilot", "Choose the UAT venue", "Renegotiate", "Test licences", "Flow", "ABC-A-", "Internal version"):
            self.assertNotIn(internal, text)
        self.assertIn("We would like your confirmation of the pilot plan.", text)
        self.assertIn("(client)", self.staged()["report"]["file_ops"][-2]["to"])
        self.assertIn("Steerco one-pager (client).docx", out)

    def test_a_summary_from_claude_is_added_to_the_status_and_nothing_else_is_invented(self):
        self.stage(version="internal", summary=["Data access remains the one thing that matters; the committee is asked to unblock it."])
        text = self.draft_text()
        self.assertIn("the committee is asked to unblock it.", text)

    def test_a_project_with_pending_items_is_blocked_unless_forced(self):
        self.v.propose("pending", [dict(new(1, "actions", description="Something pending"), decision="pending")])
        r = self.stage(version="internal", ok=False)
        self.assertEqual(r.returncode, 3)
        self.assertIn("awaiting review", r.stdout)
        self.assertEqual(sorted((self.v.root / "system/staging/drafts").glob("*Steerco*")), [])
        self.stage(version="internal", force=True)
        self.assertEqual(len(list((self.v.root / "system/staging/drafts").glob("*Steerco one-pager*.docx"))), 1)


class FilingTests(Base):
    def approve(self):
        p = sorted((self.v.root / "system/staging").glob("proposed-2*-steerco*.json"))[-1]
        data = json.loads(p.read_text())
        data["report"]["report_decision"] = "approved"
        p.write_text(json.dumps(data))
        return self.v.run("apply", str(p))

    def steerco_files(self):
        folder = self.v.root / "projects/ABC Example Programme/reports/Steerco"
        return sorted(f.name for f in folder.glob("*")) if folder.is_dir() else []

    def test_approval_files_it_into_the_steerco_folder_stamped_approved(self):
        self.stage(version="internal")
        self.approve()
        self.assertEqual(self.steerco_files(), [f"{TODAY} Example Programme Steerco one-pager.docx"])
        text = self.draft_text({"draft": f"projects/ABC Example Programme/reports/Steerco/{TODAY} Example Programme Steerco one-pager.docx"})
        self.assertIn("Approved by", text)
        self.assertEqual(list((self.v.root / "system/staging/drafts").glob("*Steerco*")), [])           # the draft is gone

    def test_a_second_one_the_same_day_gets_a_number_and_nothing_is_overwritten(self):
        self.stage(version="internal")
        self.approve()
        first = (self.v.root / f"projects/ABC Example Programme/reports/Steerco/{TODAY} Example Programme Steerco one-pager.docx").read_bytes()
        self.stage(version="internal")
        self.assertIn(f"{TODAY} Example Programme Steerco one-pager 2.docx", self.staged()["report"]["file_ops"][-2]["to"])
        self.approve()
        self.assertEqual(self.steerco_files(), [f"{TODAY} Example Programme Steerco one-pager 2.docx", f"{TODAY} Example Programme Steerco one-pager.docx"])
        self.assertEqual((self.v.root / f"projects/ABC Example Programme/reports/Steerco/{TODAY} Example Programme Steerco one-pager.docx").read_bytes(), first)

    def test_a_file_already_there_is_never_replaced(self):
        folder = self.v.root / "projects/ABC Example Programme/reports/Steerco"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{TODAY} Example Programme Steerco one-pager.docx").write_bytes(b"Alan's own file")
        self.stage(version="internal")
        self.assertIn("one-pager 2.docx", self.staged()["report"]["file_ops"][-2]["to"])
        self.approve()
        self.assertEqual((folder / f"{TODAY} Example Programme Steerco one-pager.docx").read_bytes(), b"Alan's own file")

    def test_the_filed_name_has_the_project_name_and_never_the_code(self):
        self.stage(version="internal")
        self.stage(version="client", force=True)                                                 # the first draft is itself waiting for review
        names = [b["file_ops"][-2]["to"].rsplit("/", 1)[1] for b in (json.loads(p.read_text())["report"] for p in
                                                                 sorted((self.v.root / "system/staging").glob("proposed-2*-steerco*.json")))]
        self.assertEqual(sorted(names), [f"{TODAY} Example Programme Steerco one-pager (client).docx",
                                         f"{TODAY} Example Programme Steerco one-pager.docx"])
        self.assertFalse(any("ABC" in n for n in names))

    def test_an_earlier_file_without_the_name_still_counts_as_the_last_one(self):
        folder = self.v.root / "projects/ABC Example Programme/reports/Steerco"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{d(-9)} Steerco one-pager.docx").write_bytes(b"x")                          # named the earlier way
        self.assertEqual(self.data()["last_steerco"], d(-9))

    def test_undo_takes_the_filed_copy_away(self):
        self.stage(version="internal")
        self.approve()
        self.v.run("undo")
        self.assertEqual(self.steerco_files(), [])

    def test_the_client_safe_one_pager_is_checked_at_approval_like_a_client_report(self):
        self.stage(version="client")
        self.script("review.py", "list")
        out = self.script("review.py", "approve", "1").stdout
        self.assertNotIn("possible internal content", out)         # a clean client-safe draft passes
        self.assertIn("Report approved", out)

    def test_an_internal_item_that_leaks_into_the_client_draft_stops_approval(self):
        self.stage(version="client")
        block = self.staged()["report"]
        draft = self.v.root / block["draft"]
        parts = zipfile.ZipFile(draft)
        items = [(i, parts.read(i.filename)) for i in parts.infolist()]
        parts.close()
        with zipfile.ZipFile(draft, "w", zipfile.ZIP_DEFLATED) as z:                              # Alan types an internal ID into the draft
            for info, raw in items:
                if info.filename == "word/document.xml":
                    raw = raw.decode("utf-8").replace("Client-safe version.", "Client-safe version. See ABC-A-006.").encode("utf-8")
                z.writestr(info, raw)
        self.script("review.py", "list")
        out = self.script("review.py", "approve", "1").stdout
        self.assertIn("not approved — possible internal content in the client report", out)
        self.assertIn("ABC-A-006 isn't client-visible but its ID appears", out)

    def test_a_labelled_item_in_a_client_draft_stops_approval(self):
        self.label("ABC-D-014")                                                              # client-visible and Sensitive
        self.stage(version="client", include_labelled=["ABC-D-014"])                         # Alan chose to include it
        self.assertIn("The proposal no longer includes the pricing option.", self.draft_text())
        self.assertNotIn("Sensitive", self.draft_text())                                    # the client version shows no label and no internal ID
        self.assertEqual(self.staged()["report"]["included_labelled"], ["ABC-D-014"])        # Alan's choice, logged against the report
        self.script("review.py", "list")
        out = self.script("review.py", "approve", "1").stdout
        self.assertIn("ABC-D-014 is labelled Sensitive but its wording appears", out)       # BL-94's floor: it stops at review
        self.assertIn("--as-staged", out)


if __name__ == "__main__":
    unittest.main()
