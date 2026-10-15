"""BL-342 part 2: matching a followed person's thread to open work.

Run: python3 dev/tests/test_vip_matching.py
A throwaway vault with fictional people and actions; no Microsoft 365. Covers: a thread naming an open ID gives Update with
it; a thread with nothing similar gives New; an invented, closed or other project's ID falls to New; Chase only when the
item's owner is in the thread and Alan sent last (else Update); no project gives New and says so, with no list; two threads
for one item give two cards and a count; logging stages one pending update (based_on, thread as source) and a second thread
adds a line to the same proposal; a confidential thread logs only the neutral line; a private thread has no match; the
tracker is only read; and no "VIP" in the card or the proposal.
"""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_sweep_alerts import record, vip_file, vip_vault  # noqa: E402
from test_tracker import action  # noqa: E402

NOW = "2026-10-08 09:30"
MIA = "Mia Hale <mia@client.example>"
OMAR = "Omar Ali <omar@brightwater.example>"
ALAN = "Alan Carter <alan@brightwater.example>"
SECRET = "SECRET MESSAGE TEXT"


def conv(n, title="Project Falcon go-live", summary="Mia asks where the revised SOW is.", **extra):
    return {"kind": "teams", "conversation": f"19:chat-{n}@thread.v2", "title": title, "from": MIA, "people": [MIA, OMAR],
            "last": "2026-10-08 08:00", "link": f"https://teams.microsoft.com/l/chat/19:chat-{n}", "sensitivity": "normal",
            "summary": summary, "items": [{"type": "action", "text": "Send the revised SOW", "owner": "Omar Ali"}],
            "body": SECRET, **extra}


def py(v, code):
    """Run code in the vault with the engine importable; returns stdout as JSON."""
    r = subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts'); import sweep, paths\n" + code],
                       cwd=v.root, capture_output=True, text=True, env={**os.environ, "CREAITE_NOW": NOW})
    if r.returncode:
        raise AssertionError(r.stdout + r.stderr)
    return json.loads(r.stdout)


class MatchTests(unittest.TestCase):
    def setUp(self):
        self.v = v = vip_vault()
        (v.root / "system/config").mkdir(parents=True, exist_ok=True)
        cfg = v.root / "system/config/settings.json"
        d = json.loads(cfg.read_text())
        d["identity"] = {"name": "Alan Carter", "short_forms": ["Alan"], "own_domains": ["brightwater.example"]}
        cfg.write_text(json.dumps(d, indent=2))
        v.propose("seed", [
            action(1, description="Send revised SOW to client", owner="Omar Ali", due_date="2026-10-12"),
            action(2, description="Book the go-live rehearsal room", owner="Ben Ito", due_date="2026-10-20"),
            action(3, description="Closed one: archive old drafts", owner="Omar Ali", due_date="2026-10-02"),
        ])
        v.run("apply")
        import sqlite3
        from contextlib import closing
        with closing(sqlite3.connect(v.root / "system/tracker.db")) as con:
            con.execute("UPDATE actions SET status = 'Closed', closed = '2026-10-03' WHERE id = 'ABC-A-003'")
            # F7: another project with an open action, so an item of another project is really refused
            con.execute("INSERT INTO projects (code, name) VALUES ('XYZ', 'Project Other')")
            con.execute("INSERT INTO actions (id, project, description, owner, raised, source) VALUES "
                        "('XYZ-A-001', 'XYZ', 'Send revised SOW to client', 'Omar Ali', '2026-10-01', 'Email · test')")
            con.commit()
        self.ids = [r["id"] for r in v.rows("actions")]

    def tearDown(self):
        self.v.cleanup()

    def card(self, n=None):
        cards = [a for a in vip_file(self.v)["alerts"] if "match" in a or a.get("marker")]
        return cards if n is None else cards[n]

    def test_a_named_open_id_gives_update_and_nothing_similar_gives_new(self):
        record(self.v, [conv(1, summary="Mia chases ABC-A-001.", match={"id": "ABC-A-001", "relation": "update", "why": "A VIP asks about it."}),
                        conv(2, title="Project Falcon catering", summary="Lunch for the launch.",
                             items=[{"type": "action", "text": "Order lunch", "owner": "Mia Hale"}],
                             match={"id": None, "relation": "new", "why": "Nothing open about it."})], "check")
        a = {c["conv"]: c for c in vip_file(self.v)["alerts"]}
        m1, m2 = a["19:chat-1@thread.v2"]["match"], a["19:chat-2@thread.v2"]["match"]
        self.assertEqual((m1["id"], m1["relation"]), ("ABC-A-001", "update"))
        self.assertEqual(m1["t"], "Send revised SOW to client")
        self.assertNotRegex(m1["why"], r"(?i)\bvip")                                            # BL-288
        self.assertEqual((m2["id"], m2["relation"]), (None, "new"))

    def test_no_suggestion_at_all_still_finds_an_id_the_thread_names(self):
        record(self.v, [conv(1, summary="Mia asks about ABC-A-002 again.")], "check")
        m = vip_file(self.v)["alerts"][0]["match"]
        self.assertEqual((m["id"], m["relation"]), ("ABC-A-002", "update"))

    def test_an_invented_closed_or_other_id_becomes_new_not_an_error(self):
        for bad in ("ABC-A-099", "ABC-A-003", "XYZ-A-001", "not an id"):
            with self.subTest(bad):
                record(self.v, [conv(1, match={"id": bad, "relation": "update", "why": "It is that one."})], "check")
                m = vip_file(self.v)["alerts"][0]["match"]
                self.assertEqual((m["id"], m["relation"]), (None, "new"))
                self.assertNotIn(bad, json.dumps(m))
                (self.v.root / "system/staging/vip.json").unlink()

    def test_chase_needs_the_owner_in_the_thread_and_alan_last(self):
        chase = {"id": "ABC-A-001", "relation": "chase", "why": "Alan asked and had no answer."}
        record(self.v, [conv(1, last_from=ALAN, match=chase)], "check")
        self.assertEqual(vip_file(self.v)["alerts"][0]["match"]["relation"], "chase")
        (self.v.root / "system/staging/vip.json").unlink()
        record(self.v, [conv(1, last_from=OMAR, match=chase)], "check")                       # a reply after: Update
        self.assertEqual(vip_file(self.v)["alerts"][0]["match"]["relation"], "update")
        (self.v.root / "system/staging/vip.json").unlink()
        record(self.v, [conv(1, last_from=ALAN, match={**chase, "id": "ABC-A-002"})], "check")  # Ben Ito is not in the thread
        self.assertEqual(vip_file(self.v)["alerts"][0]["match"]["relation"], "update")
        (self.v.root / "system/staging/vip.json").unlink()
        record(self.v, [conv(1, match=chase)], "check")                                       # no last sender at all
        self.assertEqual(vip_file(self.v)["alerts"][0]["match"]["relation"], "update")

    def test_no_project_gives_new_says_so_and_has_no_list(self):
        a = py(self.v, "a = {'p': None, 'title': 'Quarterly lunch'}\n"
                       "sweep.vip_match(a, {'match': {'id': 'ABC-A-001', 'relation': 'update', 'why': 'x'}})\nprint(json.dumps(a))")
        self.assertEqual((a["match"]["id"], a["match"]["relation"]), (None, "new"))
        self.assertIn("No project matched", a["match"]["why"])
        self.assertEqual(py(self.v, "print(json.dumps(sweep.vip_open_items(None, {'title': 'x'})))"), [])

    def test_the_candidate_list_is_open_actions_of_the_project_best_first_and_at_most_15(self):
        got = py(self.v, "print(json.dumps(sweep.vip_open_items('ABC', {'title': 'Project Falcon go-live', 'summary': 'About ABC-A-002 and the room', "
                         "'people': ['Mia Hale', 'Omar Ali'], 'items': []})))")
        self.assertEqual([g["id"] for g in got], ["ABC-A-002", "ABC-A-001"])                  # named first; closed one left out
        self.assertTrue(got[0]["named"] and got[1]["owner_in_thread"])
        self.assertLessEqual(len(got), 15)

    def test_two_threads_one_item_show_two_cards_and_a_count(self):
        m = {"id": "ABC-A-001", "relation": "update", "why": "Both ask."}
        record(self.v, [conv(1, match=m), conv(2, match=m)], "check")
        cards = vip_file(self.v)["alerts"]
        self.assertEqual(len(cards), 2)
        self.assertEqual([c["match"]["count"] for c in cards], [2, 2])

    def test_log_stages_one_pending_update_and_a_second_thread_adds_a_line(self):
        m = {"id": "ABC-A-001", "relation": "update", "why": "Both ask."}
        record(self.v, [conv(1, summary="Mia wants the SOW by Friday.", match=m), conv(2, summary="Ben also asks for the SOW.", match=m)], "check")
        ids = [a["id"] for a in vip_file(self.v)["alerts"]]
        before = set(p.name for p in (self.v.root / "system/staging").glob("proposed-*"))
        first = py(self.v, f"print(json.dumps(sweep.vip_update_stage('{ids[0]}')))")
        again = py(self.v, f"print(json.dumps(sweep.vip_update_stage('{ids[0]}')))")           # the same thread again
        self.assertTrue(first["added"])
        self.assertFalse(again["added"])
        self.assertEqual(again["proposal"], first["proposal"])
        second = py(self.v, f"print(json.dumps(sweep.vip_update_stage('{ids[1]}')))")
        self.assertEqual(second["proposal"], first["proposal"])                               # one proposal per item
        new = set(p.name for p in (self.v.root / "system/staging").glob("proposed-*")) - before
        self.assertEqual(new, {first["proposal"]})
        spec = json.loads((self.v.root / "system/staging" / first["proposal"]).read_text())
        self.assertEqual(len(spec["items"]), 1)
        it = spec["items"][0]
        self.assertEqual((it["op"], it["table"], it["id"], it["decision"]), ("update", "actions", "ABC-A-001", "pending"))
        self.assertEqual(list(it["changes"]), ["latest_update"])
        self.assertEqual(len(it["changes"]["latest_update"].split("\n")), 2)
        self.assertIn("08-10-2026: Mia wants the SOW by Friday (from a Teams chat)", it["changes"]["latest_update"])
        self.assertTrue(it["based_on"])
        self.assertEqual((it["suggested"]["feature"], len(it["suggested"]["threads"])), ("thread", 2))
        self.assertIn("19:chat-1", it["source"])
        self.assertEqual(vip_file(self.v)["alerts"][0]["match"]["logged"]["proposal"], first["proposal"])
        self.assertNotIn(SECRET, json.dumps(spec))
        self.assertNotRegex(json.dumps(spec) + json.dumps(vip_file(self.v)), r"(?i)\bvip")    # BL-288 (the file's own key excepted)
        self.v.run("apply")                                                                   # pending: applies nothing
        self.assertIsNone(self.v.rows("actions")[0]["latest_update"])

    def test_a_confidential_thread_logs_only_the_neutral_line(self):
        record(self.v, [conv(1, sensitivity="confidential", summary="Salary review of the SOW team.",
                             match={"id": "ABC-A-001", "relation": "update", "why": "x"})], "check")
        aid = vip_file(self.v)["alerts"][0]["id"]
        py(self.v, f"print(json.dumps(sweep.vip_update_stage('{aid}')))")
        spec = json.loads(next((self.v.root / "system/staging").glob("proposed-*-dashboard*.json")).read_text())
        self.assertEqual(spec["items"][0]["changes"]["latest_update"], "Discussed in a confidential thread, 08-10-2026")
        self.assertNotIn("Salary", json.dumps(spec))

    def test_a_thread_with_a_new_message_is_the_same_card_and_adds_nothing(self):
        m = {"id": "ABC-A-001", "relation": "update", "why": "x"}
        record(self.v, [conv(1, match=m)], "check")
        aid = vip_file(self.v)["alerts"][0]["id"]
        first = py(self.v, f"print(json.dumps(sweep.vip_update_stage('{aid}')))")
        record(self.v, [conv(1, match=m, last="2026-10-08 09:10", link="https://teams.microsoft.com/l/chat/19:chat-1/newer")], "check")
        card = vip_file(self.v)["alerts"][0]
        self.assertEqual(card["id"], aid)
        again = py(self.v, f"print(json.dumps(sweep.vip_update_stage('{aid}')))")
        self.assertFalse(again["added"])
        spec = json.loads((self.v.root / "system/staging" / first["proposal"]).read_text())
        self.assertEqual(len(spec["items"][0]["suggested"]["lines"]), 1)
        self.assertEqual(spec["items"][0]["source"].count("19:chat-1"), 1)
        card.pop("link")                                                                      # a card with no link is still refused
        (self.v.root / "system/staging/vip.json").write_text(json.dumps({"alerts": [card]}))
        self.assertFalse(py(self.v, f"print(json.dumps(sweep.vip_update_stage('{aid}')))")["added"])

    def test_a_confidential_proposal_carries_neither_subject_nor_summary(self):
        record(self.v, [conv(1, title="Salary review for the Falcon team", sensitivity="confidential",
                             summary="Compensation changes for Omar.", match={"id": "ABC-A-001", "relation": "update", "why": "x"})], "check")
        aid = vip_file(self.v)["alerts"][0]["id"]
        out = py(self.v, f"print(json.dumps(sweep.vip_update_stage('{aid}')))")
        text = (self.v.root / "system/staging" / out["proposal"]).read_text()
        for word in ("Salary", "Compensation"):
            self.assertNotIn(word, text)
        self.assertEqual(json.loads(text)["items"][0]["source"], "Teams chat · Link: https://teams.microsoft.com/l/chat/19:chat-1")
        self.assertEqual(json.loads(text)["items"][0]["why"], "Logged from a confidential thread")

    def test_the_items_existing_latest_update_is_kept_in_front_of_the_new_lines(self):
        import sqlite3
        from contextlib import closing
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            con.execute("UPDATE actions SET latest_update = 'Draft sent to legal' WHERE id = 'ABC-A-001'")
            con.commit()
        m = {"id": "ABC-A-001", "relation": "update", "why": "x"}
        record(self.v, [conv(1, summary="Mia wants it Friday.", match=m), conv(2, summary="Ben agrees.", match=m)], "check")
        for a in vip_file(self.v)["alerts"]:
            out = py(self.v, f"print(json.dumps(sweep.vip_update_stage('{a['id']}')))")
        spec = json.loads((self.v.root / "system/staging" / out["proposal"]).read_text())
        lines = spec["items"][0]["changes"]["latest_update"].split("\n")
        self.assertEqual(lines[0], "Draft sent to legal")
        self.assertEqual(len(lines), 3)
        self.assertTrue(spec["items"][0]["based_on"])

    def test_a_private_thread_has_no_match_and_a_missing_match_refuses_to_log(self):
        record(self.v, [conv(1, sensitivity="private", match={"id": "ABC-A-001", "relation": "update", "why": "x"})], "check")
        a = vip_file(self.v)["alerts"][0]
        self.assertNotIn("match", a)
        r = subprocess.run([sys.executable, "-c", f"import sys; sys.path.insert(0,'system/scripts'); import sweep; sweep.vip_update_stage('{a['id']}')"],
                           cwd=self.v.root, capture_output=True, text=True)
        self.assertIn("no matched item", r.stderr)

    def test_end_to_end_log_handled_undo_and_confidential(self):
        """A matched thread: Log stages one update keeping the old text; again adds nothing; a second thread adds a line; Handled and
        Undo work; a confidential thread's proposal has no subject. One logged shape: card["match"]["logged"] = {proposal, at}."""
        import sqlite3
        from contextlib import closing
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            con.execute("UPDATE actions SET latest_update = 'Waiting on legal.' WHERE id = 'ABC-A-001'")
            con.commit()
        m = {"id": "ABC-A-001", "relation": "update", "why": "Both ask."}
        record(self.v, [conv(1, summary="Mia wants the SOW by Friday.", match=m), conv(2, summary="Ben also asks for it.", match=m),
                        conv(3, title="Salary review", sensitivity="confidential", summary="Pay talks.", match=m)], "check")
        cards = vip_file(self.v)["alerts"]
        by = {c["conv"]: c["id"] for c in cards}
        a1, a2, a3 = (by[f"19:chat-{n}@thread.v2"] for n in (1, 2, 3))
        self.assertTrue(all(c["match"]["count"] == 3 and c["state"] == "open" for c in cards))
        log = lambda i: py(self.v, f"print(json.dumps(sweep.vip_log('{i}')))")
        one = log(a1)
        self.assertEqual((one["added"], one["already"], one["state"]), (True, False, "staged"))
        self.assertEqual(set(one["logged"]), {"proposal", "at", "state"})
        spec = json.loads((self.v.root / "system/staging" / one["proposal"]).read_text())
        text = spec["items"][0]["changes"]["latest_update"]
        self.assertTrue(text.startswith("Waiting on legal.\n"))
        self.assertIn("Mia wants the SOW by Friday", text)
        again = log(a1)
        self.assertTrue(again["already"] and not again["added"])
        self.assertEqual(again["proposal"], one["proposal"])
        two = log(a2)
        self.assertEqual((two["proposal"], two["added"]), (one["proposal"], True))
        spec = json.loads((self.v.root / "system/staging" / one["proposal"]).read_text())
        self.assertEqual(len(spec["items"]), 1)
        self.assertEqual(len(spec["items"][0]["changes"]["latest_update"].split("\n")), 3)
        log(a3)
        spec = json.loads((self.v.root / "system/staging" / one["proposal"]).read_text())
        self.assertNotIn("Salary", json.dumps(spec))
        self.assertEqual(spec["items"][0]["suggested"]["threads"], [a1, a2, a3])
        card = {c["id"]: c for c in vip_file(self.v)["alerts"]}
        self.assertTrue(all(card[i]["match"]["logged"]["proposal"] == one["proposal"] for i in (a1, a2, a3)))
        self.assertNotIn("logged", card[a1])                                                  # one place only
        self.assertEqual(py(self.v, f"print(json.dumps(sweep.vip_handled(['{a1}'])))"), [a1])
        self.assertEqual({c["id"]: c for c in vip_file(self.v)["alerts"]}[a1]["state"], "handled")
        self.assertEqual(py(self.v, f"print(json.dumps(sweep.vip_undismiss(['{a1}'])))"), [a1])
        self.assertEqual({c["id"]: c for c in vip_file(self.v)["alerts"]}[a1]["state"], "open")

    def test_the_tracker_is_only_read(self):
        before = (self.v.root / "system/tracker.db").read_bytes()
        record(self.v, [conv(1, match={"id": "ABC-A-001", "relation": "update", "why": "x"})], "check")
        self.assertEqual((self.v.root / "system/tracker.db").read_bytes(), before)
        aid = vip_file(self.v)["alerts"][0]["id"]
        py(self.v, f"print(json.dumps(sweep.vip_log('{aid}')))")                              # F4: a Log leaves the tracker as it was
        self.assertEqual((self.v.root / "system/tracker.db").read_bytes(), before)

    def test_the_count_follows_dismiss_handled_and_undo(self):
        m = {"id": "ABC-A-001", "relation": "update", "why": "Both ask."}
        record(self.v, [conv(1, match=m), conv(2, match=m)], "check")
        a1, a2 = [c["id"] for c in vip_file(self.v)["alerts"]]
        counts = lambda: sorted((c["id"], c["match"]["count"]) for c in vip_file(self.v)["alerts"] if not c.get("seen"))  # noqa: E731
        py(self.v, f"print(json.dumps(sweep.vip_dismiss(['{a1}'])))")
        self.assertEqual(counts(), [(a2, 1)])                                                  # F1: the shown card counts alone
        py(self.v, f"print(json.dumps(sweep.vip_undismiss(['{a1}'])))")
        self.assertEqual([n for _, n in counts()], [2, 2])
        py(self.v, f"print(json.dumps(sweep.vip_handled(['{a2}'])))")
        self.assertEqual(counts(), [(a1, 1)])
        py(self.v, f"print(json.dumps(sweep.vip_seen(['{a1}'])))")
        self.assertEqual(vip_file(self.v)["alerts"][0]["match"]["count"], 1)

    def test_a_different_person_with_the_same_first_name_is_not_alan(self):
        chase = {"id": "ABC-A-001", "relation": "chase", "why": "Alan asked and had no answer."}
        for who, want in (("Alan Jones <alan.jones@other.example>", "update"), ("Alan <alan@other.example>", "update"),
                          ("Alan Carter <alan.carter@other.example>", "update"), ("Alan Carter", "chase"),
                          ("Alan Carter <alan.carter@brightwater.example>", "chase")):
            with self.subTest(who):
                record(self.v, [conv(1, last_from=who, match=chase)], "check")
                self.assertEqual(vip_file(self.v)["alerts"][0]["match"]["relation"], want)
                (self.v.root / "system/staging/vip.json").unlink()


if __name__ == "__main__":
    unittest.main()
