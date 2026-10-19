"""#241 D: a work item's complete history (system/scripts/item_history.py; design: dev/proposals/work-item-history/DESIGN.md).

The acceptance test from the brief: each field changed through each route (the peek, a cell, the bulk bar, the context menu,
Review, cx-edit, a note's Find updates, ask creaite, then Undo) gives exactly one event with the right before and after, the
route it came by, and no event carries message text. Each route is staged as the proposal that route writes (the dashboard's
four places differ only by the proposal's `place`, the contract in DESIGN.md) and applied with the real tracker.py.

The tests marked expectedFailure need the guarded diff in dev/proposals/work-item-history/ (the item_events table, tracker.py
writing it, live_server.py's read route); each says which part. Today's history is worked out from change_log and the applied
proposals, so the peek can show it before the diff lands.

Run: python3 dev/tests/test_item_history.py
"""
import json
import sqlite3
import subprocess
import sys
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import Vault, action  # noqa: E402

SECRET = "PLEASE-NEVER-SHOW-THIS-QUOTE"          # message text: in a proposal's why, evidence and done quote only
CLIENT_MSG = ("What it is: The signed statement of work.\nWhat it means for you: Work can start on phase two.\n"
              "What is being done: Legal review is under way.")
NEEDS_DIFF = "needs the guarded diff in dev/proposals/work-item-history/ ({})"
A, R = "ABC-A-001", "ABC-003"


def new(n, table, **values):
    return {"n": n, "op": "new", "table": table, "values": values, "match": "strong", "flags": [], "decision": "approved"}


def upd(n, table, id_, **changes):
    return {"n": n, "op": "update", "table": table, "id": id_, "changes": changes, "match": "strong", "flags": [],
            "decision": "approved"}


def seed(v):
    """A second project, an action (client messaging complete, so Client-visible can be turned on), two workstreams, two
    milestones and a risk."""
    v.run("init")
    v.propose("a0", [new(1, "projects", code="DEF", name="Other Programme")])
    v.run("apply")
    v.propose("a1", [action(1, client_message=CLIENT_MSG), action(2, description="Book the UAT room"),
                     new(3, "workstreams", project="ABC", name="Testing", created="2026-10-01", source="s"),
                     new(4, "workstreams", project="ABC", name="Build", created="2026-10-01", source="s"),
                     new(5, "milestones", project="ABC", name="Go-live", source="s"),
                     new(6, "milestones", project="ABC", name="Pilot", source="s"),
                     new(7, "raid", project="ABC", type="Risk", description="Data access late", impact="High",
                         likelihood="Low", raised="2026-10-01", source="s")])
    v.run("apply")


# The routes: (name, the proposal's top-level fields, its file name tag, an item's extra keys, the route, place and who expected)
ROUTES = [
    ("peek", {"source_run": "dashboard", "place": "peek", "peek": {"k": "actions"}}, "dashboard", {}, ("dashboard", "peek", "You")),
    ("cell", {"source_run": "dashboard", "place": "cell"}, "dashboard", {}, ("dashboard", "cell", "You")),
    ("bulk", {"source_run": "dashboard", "place": "bulk"}, "dashboard", {}, ("dashboard", "bulk", "You")),
    ("menu", {"source_run": "dashboard", "place": "menu"}, "dashboard", {}, ("dashboard", "menu", "You")),
    ("review", {"source_run": "cx-sweep"}, "sweep",
     {"decided_in": "dashboard", "why": f"Looks done: Mail from Sara: “{SECRET}”", "source": "Outlook: Re: SOW (2026-10-09)",
      "done": {"strength": "Looks done", "quote": SECRET},
      "suggested": {"feature": "done", "evidence": {"kind": "mail", "quote": SECRET, "source": "Outlook: Re: SOW"}}},
     ("review", "dashboard", "You")),
    ("cx-edit", {"source_run": "cx-edit"}, "edit", {}, ("cx-edit", None, "You")),
    ("note", {"source_run": "note", "note": {"path": "projects/ABC Example Programme/notes/Standup.md"}}, "note",
     {"source": "projects/ABC Example Programme/notes/Standup.md#p2"}, ("note", None, "You")),
    ("ask", {"source_run": "assistant"}, "ask", {}, ("assistant", None, "You")),
]

# The fields: (table, item, field, the two values it alternates between); the change sets the one it doesn't hold
FIELDS = [
    ("actions", A, "status", ("Open", "Delayed")),
    ("actions", A, "owner", ("Omar Ali", "Sara Example")),
    ("actions", A, "due_date", ("2026-11-03", "2026-11-17")),
    ("actions", A, "priority", ("High", "Low")),
    ("actions", A, "workstream", ("Testing", "Build")),
    ("actions", A, "milestone", ("ABC-M-001", "ABC-M-002")),
    ("actions", A, "description", ("Send the revised SOW", "Send the signed SOW")),
    ("actions", A, "latest_update", ("Draft is with legal", "Legal signed it off")),
    ("actions", A, "client_visible", ("0", "1")),
    ("raid", R, "impact", ("Medium", "Low")),
    ("raid", R, "likelihood", ("High", "Medium")),
    ("raid", R, "response_action", ("Ask for a data extract", "Escalate to the sponsor")),
    ("raid", R, "owner", ("Omar Ali", "Sara Example")),
]


def history(v, item):
    """item_history.history_of(item), run inside the throwaway vault (its own paths, database and staging)."""
    code = ("import json, sys; sys.path.insert(0, 'system/scripts'); import item_history; "
            "print(json.dumps(item_history.history_of(sys.argv[1]), ensure_ascii=False))")
    r = subprocess.run([sys.executable, "-c", code, item], cwd=v.root, capture_output=True, text=True)
    if r.returncode:
        raise AssertionError(r.stderr)
    return json.loads(r.stdout)


def q(v, sql, *args):
    with closing(sqlite3.connect(v.root / "system/tracker.db")) as con:
        con.row_factory = sqlite3.Row
        return [dict(r) for r in con.execute(sql, args)]


def current(v, table, item, field):
    val = q(v, f"SELECT {field} FROM {table} WHERE id = ?", item)[0][field]
    return None if val is None else str(val)


def last_apply(v):
    return q(v, "SELECT max(apply_id) AS n FROM applies")[0]["n"]


def of_apply(events, apply_id, field=None):
    return [e for e in events if e.get("apply_id") == apply_id and (field is None or e.get("field") == field)]


class Matrix(unittest.TestCase):
    """Every field through every route, then Undo. One vault for the class: the routes run in turn on the same two items."""

    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        seed(cls.v)
        cls.applied = {}                      # route → (apply_id, {(item, field): (before, after)})
        for i, (name, top, tag, extra, _) in enumerate(ROUTES):
            changes, items = {}, {}
            for table, item, field, pair in FIELDS:
                was = current(cls.v, table, item, field)
                to = pair[1] if was == pair[0] else pair[0]
                changes[(item, field)] = (was, to)
                items.setdefault((table, item), {})[field] = int(to) if field == "client_visible" else to
            props = [{**upd(n, t, i_, **ch), **extra} for n, ((t, i_), ch) in enumerate(items.items(), 1)]
            p = cls.v.propose(f"2026-10-1{i}-0900-{tag}-{name}", props, **top)     # propose() lets `top` set source_run
            cls.v.run("apply", p.name)
            cls.applied[name] = (last_apply(cls.v), changes)
        cls.before_undo = history(cls.v, A)["events"] + history(cls.v, R)["events"]
        cls.v.run("undo")
        cls.after = {A: history(cls.v, A), R: history(cls.v, R)}

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def test_each_field_through_each_route_is_one_event_with_its_before_and_after(self):
        for name, _, _, _, (route, place, who) in ROUTES:
            apply_id, changes = self.applied[name]
            for (item, field), (was, to) in changes.items():
                with self.subTest(route=name, item=item, field=field):
                    got = of_apply(self.after[item]["events"], apply_id, field)
                    self.assertEqual(len(got), 1, got)
                    e = got[0]
                    self.assertEqual((e["before"], e["after"]), (was, to))
                    self.assertEqual((e["route"], e["place"], e["who"]), (route, place, who))
                    self.assertTrue(e["via"])
                    self.assertTrue(e["at"])

    def test_undo_strikes_each_original_event_and_adds_its_own(self):
        apply_id, changes = self.applied[ROUTES[-1][0]]
        for (item, field), (was, to) in changes.items():
            with self.subTest(item=item, field=field):
                evs = of_apply(self.after[item]["events"], apply_id, field)
                orig = [e for e in evs if e["k"] != "undo"]
                undo = [e for e in evs if e["k"] == "undo"]
                self.assertEqual((len(orig), len(undo)), (1, 1), evs)
                self.assertTrue(orig[0]["struck"])
                self.assertEqual(orig[0]["struck_by"], undo[0]["id"])
                self.assertEqual(undo[0]["undoes"], orig[0]["id"])
                self.assertEqual((undo[0]["before"], undo[0]["after"]), (to, was))
                self.assertEqual((undo[0]["route"], undo[0]["who"]), ("undo", "You"))
                self.assertFalse(undo[0]["struck"])
        for name, _, _, _, _ in ROUTES[:-1]:                   # the earlier routes are untouched
            for e in of_apply(self.after[A]["events"], self.applied[name][0]):
                self.assertFalse(e["struck"], (name, e))

    def test_newest_first_and_the_tabs_kinds(self):
        evs = self.after[A]["events"]
        ats = [e["at"] for e in evs]
        self.assertEqual(ats, sorted(ats, reverse=True))
        kinds = {e["field"]: e["k"] for e in evs if e.get("field") and e["k"] != "undo"}
        self.assertEqual(kinds["latest_update"], "update")       # the Updates tab
        self.assertEqual(kinds["client_visible"], "cv")
        self.assertEqual(kinds["status"], "change")
        self.assertEqual(evs[-1]["k"], "create")                  # the oldest: created, once
        self.assertEqual(len([e for e in evs if e["k"] == "create"]), 1)
        self.assertEqual(self.after[R]["events"][-1]["k"], "create")

    def test_no_event_carries_message_text(self):
        text = json.dumps(self.after, ensure_ascii=False) + json.dumps(self.before_undo, ensure_ascii=False)
        self.assertNotIn(SECRET, text)
        self.assertNotIn("Looks done", text)
        allowed = {"id", "k", "who", "route", "place", "via", "field", "label", "before", "after", "at", "apply_id", "src",
                   "struck", "struck_by", "undoes", "exact", "note", "closed", "made", "mode"}
        for e in self.after[A]["events"]:
            self.assertLessEqual(set(e), allowed, e)

    def test_review_events_cite_the_source_reference(self):
        apply_id, _ = self.applied["review"]
        e = of_apply(self.after[A]["events"], apply_id, "owner")[0]
        self.assertEqual(e["src"], "Outlook: Re: SOW (2026-10-09)")
        n = of_apply(self.after[A]["events"], self.applied["note"][0], "owner")[0]
        self.assertEqual(n["src"], "projects/ABC Example Programme/notes/Standup.md#p2")

    def test_the_answer_says_it_was_worked_out_until_the_diff_lands(self):
        self.assertIn("exact", self.after[A])
        self.assertTrue(all("exact" in e for e in self.after[A]["events"]))


class Single(unittest.TestCase):
    """The other events: created, labels, links, a project move, a closed status, a rejection, chases and raised again."""

    def setUp(self):
        self.v = Vault()
        seed(self.v)

    def tearDown(self):
        self.v.cleanup()

    def apply(self, name, items, **top):
        p = self.v.propose(name, items, **top)
        self.v.run("apply", p.name)
        return last_apply(self.v)

    def test_created_is_one_event_with_owner_and_due(self):
        evs = history(self.v, "ABC-A-002")["events"]
        self.assertEqual([e["k"] for e in evs], ["create"])
        self.assertEqual(evs[0]["made"]["owner"], "Alan Carter")
        self.assertEqual(evs[0]["route"], "cx-edit")
        self.assertIn("Steering.docx", evs[0]["src"])

    def test_a_label_added_and_removed_is_one_event_each(self):
        add = self.apply("l1", [upd(1, "actions", A, labels=["Sensitive"])], source_run="dashboard", place="menu")
        rem = self.apply("l2", [upd(1, "actions", A, labels=[])], source_run="dashboard", place="peek")
        evs = history(self.v, A)["events"]
        a, r = of_apply(evs, add, "labels"), of_apply(evs, rem, "labels")
        self.assertEqual([(e["before"], e["after"], e["place"]) for e in a], [(None, "Sensitive", "menu")])
        self.assertEqual([(e["before"], e["after"], e["place"]) for e in r], [("Sensitive", None, "peek")])

    def test_a_link_is_one_event_on_each_end(self):
        n = self.apply("k1", [new(1, "links", from_item=A, to_item="ABC-A-002", source="s")], source_run="dashboard", place="peek")
        for item, words in ((A, "ABC-A-002"), ("ABC-A-002", A)):
            evs = of_apply(history(self.v, item)["events"], n, "links")
            self.assertEqual(len(evs), 1, evs)
            self.assertEqual(evs[0]["after"], f"{A}|ABC-A-002|blocks")
            self.assertIn(words, evs[0]["after"])

    def test_a_project_move_through_the_peek_and_review(self):
        n = self.apply("p1", [upd(1, "actions", "ABC-A-002", project="DEF")], source_run="dashboard", place="peek")
        m = self.apply("p2-sweep", [{**upd(1, "actions", "ABC-A-002", project="ABC"), "decided_in": "dashboard"}],
                       source_run="cx-sweep")
        evs = history(self.v, "ABC-A-002")["events"]
        self.assertEqual([(e["before"], e["after"], e["route"]) for e in of_apply(evs, n, "project")], [("ABC", "DEF", "dashboard")])
        self.assertEqual([(e["before"], e["after"], e["route"]) for e in of_apply(evs, m, "project")], [("DEF", "ABC", "review")])

    def test_closing_is_one_status_event_with_the_closed_date_folded_in(self):
        n = self.apply("c1", [upd(1, "actions", A, status="Closed")], source_run="dashboard", place="cell")
        evs = of_apply(history(self.v, A)["events"], n)
        self.assertEqual([e["field"] for e in evs], ["status"])
        self.assertEqual(evs[0]["closed"]["before"], None)
        self.assertTrue(evs[0]["closed"]["after"])

    def test_a_rejected_update_in_review_is_an_event_with_no_text(self):
        item = {**upd(1, "actions", A, owner="Omar Ali"), "decision": "rejected", "reject_reason": "Not an action",
                "why": f"From mail: “{SECRET}”", "decided_in": "dashboard"}
        n = self.apply("r1-sweep", [item], source_run="cx-sweep")
        evs = of_apply(history(self.v, A)["events"], n)
        self.assertEqual([(e["k"], e["route"], e.get("note")) for e in evs], [("reject", "review", "Not an action")])
        self.assertNotIn(SECRET, json.dumps(evs, ensure_ascii=False))

    def test_a_rejection_in_alans_own_words_keeps_them_out(self):
        item = {**upd(1, "actions", A, owner="Omar Ali"), "decision": "rejected", "reject_reason": "Sara said no on the call"}
        n = self.apply("r2-sweep", [item], source_run="cx-sweep")
        evs = of_apply(history(self.v, A)["events"], n)
        self.assertEqual([(e["k"], e.get("note")) for e in evs], [("reject", None)])

    def test_chases_and_raised_again_come_from_their_own_files(self):
        st = self.v.root / "system/staging"
        (st / "chases.json").write_text(json.dumps({"chases": [{"ids": [A, "ABC-A-002"], "date": "2026-10-15", "mode": "chase"}]}))
        (st / "mentions.jsonl").write_text(json.dumps({"at": "2026-10-14", "id": A, "run": "cx-minutes",
                                                       "source": "projects/ABC Example Programme/minutes/2026-10-14 Steering.docx"}) + "\n"
                                           + "not json\n")
        evs = history(self.v, A)["events"]
        chase = [e for e in evs if e["k"] == "chase"]
        again = [e for e in evs if e["k"] == "again"]
        self.assertEqual([(e["at"], e["mode"], e["who"]) for e in chase], [("2026-10-15", "chase", "You")])
        self.assertEqual([(e["at"], e["route"], e["who"]) for e in again], [("2026-10-14", "minutes", "creaite")])
        self.assertIn("Steering.docx", again[0]["src"])

    def test_activity_undo_several_strikes_the_change_it_put_back(self):
        n = self.apply("u1", [upd(1, "actions", A, owner="Omar Ali")], source_run="dashboard", place="peek")
        rowid = q(self.v, "SELECT rowid FROM change_log WHERE apply_id = ? AND field = 'owner'", n)[0]["rowid"]
        self.v.run("undo-changes", str(rowid))
        evs = of_apply(history(self.v, A)["events"], n, "owner")
        self.assertTrue(evs[0]["struck"])
        revert = [e for e in history(self.v, A)["events"] if e["route"] == "activity"]
        self.assertEqual([(e["k"], e["before"], e["after"], e["undoes"]) for e in revert], [("undo", "Omar Ali", "Alan Carter", evs[0]["id"])])

    def test_an_unknown_item_or_no_database_is_an_empty_history(self):
        self.assertEqual(history(self.v, "ABC-A-999")["events"], [])
        (self.v.root / "system/tracker.db").unlink()
        self.assertEqual(history(self.v, A)["events"], [])

    @unittest.expectedFailure
    def test_the_route_survives_losing_the_proposal(self):
        """NEEDS the diff: tracker.py stores the route, place and source on the event, so the applied proposal is not needed."""
        n = self.apply("s1", [upd(1, "actions", A, owner="Omar Ali")], source_run="dashboard", place="cell")
        for p in (self.v.root / "system/staging/applied").glob("proposed-s1.json"):
            p.unlink()
        e = of_apply(history(self.v, A)["events"], n, "owner")[0]
        self.assertEqual((e["route"], e["place"], e["exact"]), ("dashboard", "cell", True), NEEDS_DIFF.format("tracker.py"))

    @unittest.expectedFailure
    def test_events_are_stored_one_per_change_with_references_only(self):
        """NEEDS the diff: the item_events table (schema.sql) and tracker.py writing a row for every change_log row."""
        n = self.apply("e1-sweep", [{**upd(1, "actions", A, owner="Omar Ali"), "decided_in": "dashboard",
                                     "why": f"From mail: “{SECRET}”"}], source_run="cx-sweep")
        rows = q(self.v, "SELECT e.* FROM item_events e JOIN change_log c ON c.rowid = e.change WHERE e.apply_id = ? "
                         "AND c.field = 'owner'", n)
        self.assertEqual([(r["route"], r["place"], r["actor"]) for r in rows], [("review", "dashboard", "you")])
        cols = {r["name"] for r in q(self.v, "PRAGMA table_info(item_events)")}
        self.assertEqual(cols, {"event_id", "at", "apply_id", "item_id", "change", "kind", "route", "place", "actor", "src_ref",
                                "undoes"})
        self.assertNotIn(SECRET, json.dumps(q(self.v, "SELECT * FROM item_events")))

    @unittest.expectedFailure
    def test_an_undo_event_points_at_the_one_it_undoes(self):
        """NEEDS the diff: cmd_undo passes the original change_log rowid, stored as item_events.undoes."""
        n = self.apply("d1", [upd(1, "actions", A, owner="Omar Ali")], source_run="dashboard", place="peek")
        self.v.run("undo")
        rows = q(self.v, "SELECT e.event_id, e.undoes, e.route FROM item_events e JOIN change_log c ON c.rowid = e.change "
                         "WHERE c.apply_id = ? AND c.field = 'owner' ORDER BY e.event_id", n)
        self.assertEqual(len(rows), 2)
        self.assertEqual((rows[1]["undoes"], rows[1]["route"]), (rows[0]["event_id"], "undo"))


if __name__ == "__main__":
    unittest.main()
