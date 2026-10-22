"""BL-342 Part 5: promises from Alan's own messages in a thread, and a promise that looks kept (staged only, on his click).

Run: python3 dev/tests/test_vip_promises.py
The Part 3 B vault (test_vip_single_call: fictional people, Alan Carter as identity.name, project ABC with open actions,
project XYZ) plus promises: ABC-P-012 (by Alan Carter, to Sara Example, open), ABC-P-013 (by Sara Example, to Alan Carter,
open), ABC-P-009 (Done) and XYZ-P-002 (open, another project). Probe-style fixtures: the reply a model gave, fed to plain code
(vip_clean, then vip_record with what was offered), never Microsoft 365 or a real Claude; the server tests use a stand-in
claude. Covers every drop reason (each a fixture), the staging and its Undo, the confidential neutral line, a private card,
the client report and one-pager, the counts for Activity › Quality, the route and its lock order, and no label anywhere.
"""
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import unittest
import urllib.request
import zipfile
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_live_server import free_port  # noqa: E402
from test_sweep_alerts import check_since, vip_file, vip_vault  # noqa: E402
from vip_single_call_support import FAKE, MAIL_ID, NOW, OFF, SECRET, SARA, py, seed, thread  # noqa: E402

ALAN_ADDR, SARA_ADDR, BEN = "alan@brightwater.example", "sara@brightwater.example", "Ben Ito <ben@brightwater.example>"
AT = f"2026-10-08T09:10{OFF}"                  # Alan's reply in the thread (over 15 minutes old, so not waited for)
P12 = "Share the budget summary with Sara"


def seed_promises(v):
    """ABC-P-012 (Alan's, open), ABC-P-013 (Sara's, to Alan, open), ABC-P-009 (Done), XYZ-P-002 (open, another project)."""
    with closing(sqlite3.connect(v.root / "system/tracker.db")) as con:
        rows = [("ABC-P-012", "ABC", "Alan Carter", "Sara Example", P12, "2026-10-14", "Open", None),
                ("ABC-P-013", "ABC", "Sara Example", "Alan Carter", "Send the signed statement of work", "2026-10-12", "Open", None),
                ("ABC-P-009", "ABC", "Alan Carter", "Sara Example", "Book the steering room", None, "Done", "2026-10-05"),
                ("XYZ-P-002", "XYZ", "Alan Carter", "Sara Example", "Send the other plan", None, "Open", None)]
        con.executemany("INSERT INTO promises (id, project, promised_by, promised_to, description, due_date, status, closed, "
                        "raised, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, '2026-10-01', 'Email · test')", rows)
        con.commit()


def promise(what="Send the revised plan to Mia", to="Sara", due="2026-10-09", at=AT):
    return {"what": what, "to": to, "due": due, "at": at}


def alan_said(*proms, **extra):
    """A thread whose newest message is Alan's reply (09:10), with the promises he made in it."""
    return thread(**{"last": AT, "last_from": ALAN_ADDR, "replied": AT, "people": [thread()["from"], SARA, BEN],
                     "promises": list(proms) if proms else [promise()], **extra})


CHECK = ("st = sweep.vip_state(); parts = sweep.vip_prompt_parts(st)\n"
         "found, counts = sweep.vip_clean(json.loads(sys.argv[1]), '2026-10-08 08:00', sweep.local_zone(), st['alerts'])\n"
         "op = set(json.loads(sys.argv[2])) if sys.argv[2] != 'null' else parts['offered_promises']\n"
         "checked = {'offered': parts['offered'], 'offered_promises': op, 'counts': counts}\n"
         "new = sweep.vip_record(found, 'check', checked=checked)\n"
         "print(json.dumps({'new': [a['id'] for a in new], 'counts': checked['counts'], 'parts': parts['open_promises']}))")


class Base(unittest.TestCase):
    def setUp(self):
        self.v = vip_vault()
        seed(self.v)
        seed_promises(self.v)

    def tearDown(self):
        self.v.cleanup()

    def check(self, found, offered=None):
        """What the live server's check does with a reply: vip_clean, then vip_record with what was offered."""
        r = subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts'); import sweep\n" + CHECK,
                            json.dumps(found), json.dumps(offered)], cwd=self.v.root, capture_output=True, text=True,
                           env={**os.environ, "CREAITE_NOW": NOW, "CREAITE_TZ_OFFSET": OFF})
        if r.returncode:
            raise AssertionError(r.stdout + r.stderr)
        return json.loads(r.stdout)

    def cards(self):
        return vip_file(self.v)["alerts"]

    def card(self):
        return self.cards()[0]

    def proms(self):
        return self.card().get("promises") or []

    def reset(self):
        (self.v.root / "system/staging/vip.json").unlink()

    def call(self, fn, *args):
        return py(self.v, "import sys\ntry:\n    print(json.dumps(sweep." + fn + "(*json.loads(" + repr(json.dumps(list(args)))
                          + "))))\n"
                          "except (LookupError, ValueError) as e:\n    print(json.dumps({'refused': str(e)}))")

    def staged(self):
        out = []
        for f in sorted((self.v.root / "system/staging").glob("proposed-*-dashboard*.json")):
            out += [(f.name, i) for i in json.loads(f.read_text())["items"]]
        return out

    def stats(self):
        f = self.v.root / "system/staging/draft-stats.json"
        return json.loads(f.read_text()) if f.exists() else {}

    def settings(self, **blocks):
        cfg = self.v.root / "system/config/settings.json"
        d = json.loads(cfg.read_text())
        for k, val in blocks.items():
            d.setdefault(k, {}).update(val)
        cfg.write_text(json.dumps(d))

    def promise_rows(self):
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            return {r[0]: r[1] for r in con.execute("SELECT id, status FROM promises")}


class PromptPartsTests(Base):
    def test_open_promises_are_offered_soonest_first_at_most_10_a_project_and_30_in_all(self):
        parts = py(self.v, "p = sweep.vip_prompt_parts(); print(json.dumps([json.loads(p['open_promises']), "
                           "sorted(p['offered_promises'])]))")
        work, offered = parts
        self.assertEqual([x["id"] for x in work["ABC"]], ["ABC-P-013", "ABC-P-012"])          # soonest due first
        self.assertEqual(work["ABC"][1], {"id": "ABC-P-012", "t": P12, "by": "Alan Carter", "to": "Sara Example",
                                          "due": "2026-10-14"})
        self.assertEqual(offered, ["ABC-P-012", "ABC-P-013", "XYZ-P-002"])                      # never a Done one
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            for code in ("P1AB", "P2AB", "P3AB", "P4AB"):
                con.execute("INSERT INTO projects (code, name) VALUES (?, ?)", (code, f"Project {code}"))
                con.executemany("INSERT INTO promises (id, project, promised_by, promised_to, description, raised, source) "
                                "VALUES (?, ?, 'Alan Carter', 'Sara Example', ?, '2026-10-01', 'x')",
                                [(f"{code}-P-{i:03d}", code, "A promise " + "word " * 30 + str(i)) for i in range(1, 13)])
            con.commit()
        work, offered = py(self.v, "p = sweep.vip_prompt_parts(); print(json.dumps([json.loads(p['open_promises']), "
                                   "sorted(p['offered_promises'])]))")
        self.assertEqual(len(offered), 30)
        self.assertTrue(all(len(v) <= 10 for v in work.values()))
        self.assertTrue(all(len(x["t"]) <= 80 for v in work.values() for x in v))
        self.assertEqual((py(self.v, "print(json.dumps([sweep.VIP_PROMISES_PER_PROJECT, sweep.VIP_PROMISES_MAX]))")), [10, 30])


class NewPromiseTests(Base):
    """Rules 1 to 8: a promise is offered only when it is Alan's own, in his message, to someone else, new."""

    def test_alans_sent_promise_is_offered_with_the_name_from_the_register(self):
        got = self.check([alan_said()])
        [p] = self.proms()
        self.assertEqual({k: p[k] for k in ("what", "to", "due", "at", "state")},
                         {"what": "Send the revised plan to Mia", "to": "Sara Example", "due": "2026-10-09",
                          "at": "2026-10-08 09:10", "state": "offered"})
        self.assertRegex(p["key"], r"^[0-9a-f]{12}$")
        self.assertEqual(got["counts"].get("promises_offered"), 1)
        self.assertEqual(self.stats()["promise"]["offered"], 1)                              # Activity › Quality's count
        self.assertEqual(self.promise_rows()["ABC-P-012"], "Open")                          # nothing written to the record
        self.assertEqual(self.staged(), [])                                                  # nothing staged by the check

    def test_a_reply_only_object_on_an_open_card_carries_its_promise(self):
        self.check([thread(match={"id": "ABC-A-007", "relation": "update", "why": "About the plan."})])
        got = self.check([{"kind": "mail", "conversation": MAIL_ID + "1", "replied": AT, "promises": [promise()]}])
        self.assertEqual(self.card()["state"], "replied")
        self.assertEqual([p["to"] for p in self.proms()], ["Sara Example"])
        self.assertEqual(got["counts"].get("promises_offered"), 1)

    def drop(self, reason, reply, n=1):
        got = self.check(reply)
        self.assertEqual([p for p in self.proms() if p["state"] == "offered"], [], reason)
        self.assertEqual(got["counts"].get("promises_" + reason), n, got["counts"])
        self.reset()

    def test_every_drop_reason(self):
        cases = {
            "private": [alan_said(sensitivity="private")],
            "shape": [alan_said(promises="Send the plan by Friday")],
            "vague": [alan_said(promise(what="Send it"))],
            "quoted": [alan_said(promise(what='He wrote "I will send the revised plan to you all by Friday at noon"'))],
            "self": [alan_said(promise(to="Alan Carter"))],
            "no_to": [alan_said(promise(to=""))],
            "no_zone": [alan_said(promise(at="2026-10-08 09:20"))],
            "future": [alan_said(promise(at=f"2026-10-08T11:00{OFF}"))],
            "old": [alan_said(promise(at=f"2026-10-07T09:00{OFF}"))],
            "not_alan": [thread(last=AT, last_from=SARA_ADDR, promises=[promise()])],   # the message at `at` is Sara's
            "repeat": [alan_said(promise(what="share the BUDGET summary, with Sara!"))],  # ABC-P-012's words, normalised
        }
        for reason, reply in cases.items():
            with self.subTest(reason):
                self.drop(reason, reply)

    def test_quotes_in_any_style_are_refused(self):
        run = "I will send the revised plan to you all by Friday at noon"
        for what in (f"Said '{run}'", f"Said \u2018{run}\u2019", f"\u00ab{run}\u00bb", f"\u201c{run}\u201d"):
            with self.subTest(what):
                self.drop("quoted", [alan_said(promise(what=what))])

    def test_a_short_alan_or_a_time_that_is_neither_his_reply_nor_his_last_message(self):
        self.drop("self", [alan_said(promise(to="Alan"))])
        self.drop("not_alan", [alan_said(promise(at=f"2026-10-08T09:05{OFF}"))])            # an older message of his

    def test_a_card_with_no_project_has_none(self):
        got = self.check([alan_said(title="Lunch on Friday", subject="Lunch on Friday", summary="Lunch plans.",
                                    people=["Mia Hale <mia@client.example>"])])
        if self.card().get("p"):
            self.skipTest("the fixture matched a project")
        self.assertEqual(self.proms(), [])
        self.assertEqual(got["counts"].get("promises_no_project"), 1)

    def test_at_most_three_the_first_by_time(self):
        proms = [promise(what=f"Send the revised plan part {n}") for n in range(1, 5)]
        got = self.check([alan_said(*proms)])
        self.assertEqual(len(self.proms()), 3)
        self.assertEqual(got["counts"].get("promises_over"), 1)
        self.reset()
        got = self.check([alan_said(promise(), 7)])
        self.assertEqual((len(self.proms()), got["counts"].get("promises_shape")), (1, 1))

    def test_dates(self):
        for due in ("Friday", "2026-10-07", "2026-02-30", None):
            with self.subTest(due):
                self.check([alan_said(promise(due=due))])
                self.assertIsNone(self.proms()[0]["due"])
                self.reset()

    def test_an_unknown_name_is_kept_as_written(self):
        self.check([alan_said(promise(to="Zed Unknown"))])
        self.assertEqual(self.proms()[0]["to"], "Zed Unknown")

    def test_the_same_promise_is_never_offered_twice_and_a_dismissed_one_stays_dismissed(self):
        self.check([alan_said()])
        got = self.check([alan_said(last=f"2026-10-08T09:12{OFF}", replied=f"2026-10-08T09:12{OFF}",
                                    promises=[promise(at=f"2026-10-08T09:12{OFF}")])])
        self.assertEqual(len(self.proms()), 1)
        self.assertEqual(got["counts"].get("promises_repeat"), 1)
        aid, key = self.card()["id"], self.proms()[0]["key"]
        self.assertEqual(self.call("vip_promise_dismiss", aid, key)["state"], "dismissed")
        self.check([alan_said(last=f"2026-10-08T09:14{OFF}", replied=f"2026-10-08T09:14{OFF}",
                              promises=[promise(at=f"2026-10-08T09:14{OFF}")])])
        self.assertEqual([p["state"] for p in self.proms()], ["dismissed"])
        self.assertEqual(self.staged(), [])

    def test_the_sweep_never_offers_one(self):
        py(self.v, "sweep.vip_record(" + json.dumps([{**alan_said(), "replied": "2026-10-08 09:20", "last": "2026-10-08 09:20"}])
           + ", 'sweep')\nprint('1')")
        self.assertNotIn("promises", self.card())

    def test_the_debug_line_counts_them_without_text(self):
        line = py(self.v, "print(json.dumps(sweep.vip_check_line({'returned': 1, 'kept': 1, 'promises_offered': 1, "
                          "'promises_not_alan': 2, 'promisekept_offered': 1, 'closes_kept': 1}, [], 1.0, 0.3)))")
        self.assertEqual(line, "check: 1 returned, 1 kept, 0 new or updated, 0 replied, closes kept 1, promises not_alan 2, "
                               "offered 1, promise kept offered 1, 1.0s, $0.3000")


def sara_kept(pid="ABC-P-013", **extra):
    """Sara, who made ABC-P-013, sends it: her message is the newest."""
    return thread(**{"last_from": SARA_ADDR, "people": [thread()["from"], SARA, BEN],
                     "kept": {"id": pid, "evidence": "Sara sent the signed statement of work"}, **extra})


class KeptTests(Base):
    def kept(self):
        return self.card().get("kept")

    def test_alans_own_message_keeps_his_promise(self):
        got = self.check([alan_said(promises=[], kept={"id": "ABC-P-012", "evidence": "Alan sent the budget summary to Sara"})])
        self.assertEqual(self.kept(), {"id": "ABC-P-012", "evidence": "Alan sent the budget summary to Sara",
                                       "who": "Alan Carter", "at": "2026-10-08 09:10"})
        self.assertEqual(got["counts"].get("promisekept_offered"), 1)
        self.assertEqual(self.stats()["done"]["offered"], 1)                                  # it follows Looks done

    def test_the_person_who_made_it_keeps_theirs(self):
        self.check([sara_kept()])
        self.assertEqual((self.kept()["id"], self.kept()["who"]), ("ABC-P-013", "Sara Example"))

    def drop(self, reason, reply, offered=None):
        got = self.check(reply, offered)
        self.assertIsNone(self.kept(), reason)
        self.assertEqual(got["counts"].get("promisekept_" + reason), 1, got["counts"])
        self.reset()

    def test_every_drop_reason(self):
        cases = {"shape": ([sara_kept(kept="ABC-P-013")], None),
                 "not_owner": ([sara_kept(last_from="ben@brightwater.example")], None),          # Ben didn't make it
                 "not_open": ([sara_kept("ABC-P-009")], None),                                   # Done already
                 "not_offered": ([sara_kept()], ["ABC-P-012"]),
                 "no_evidence": ([sara_kept(kept={"id": "ABC-P-013", "evidence": "  "})], None),
                 "quoted": ([sara_kept(kept={"id": "ABC-P-013", "evidence":
                                             "She said 'here is the signed statement of work for you all now'"})], None),
                 "private": ([sara_kept(sensitivity="private")], None)}
        for reason, (reply, offered) in cases.items():
            with self.subTest(reason):
                self.drop(reason, reply, offered)
        for bad in ("XYZ-P-002", "ABC-P-01", "ABC-P-014", "ABC-A-007"):                       # other project, a slip, none
            with self.subTest(bad):
                self.drop("not_open", [sara_kept(bad)])
        self.drop("not_owner", [alan_said(promises=[], kept={"id": "ABC-P-013", "evidence": "Alan thanked Sara for it"})])

    def test_the_switch_off_and_a_promise_raised_after_the_message(self):
        self.settings(drafting={"done": False})
        self.drop("off", [sara_kept()])
        self.settings(drafting={"done": True})
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            con.execute("UPDATE promises SET raised = '2026-10-09' WHERE id = 'ABC-P-013'")
            con.commit()
        self.drop("raised_after", [sara_kept()])

    def test_a_confidential_card_keeps_only_the_fixed_words(self):
        self.check([sara_kept(sensitivity="confidential")])
        self.assertEqual(self.kept()["evidence"], "The thread shows it done.")

    def test_a_later_message_without_it_takes_back_an_unstaged_one(self):
        self.check([sara_kept()])
        self.check([thread(last=f"2026-10-08T09:05{OFF}", people=[thread()["from"], SARA, BEN])])
        self.assertIsNone(self.kept())


class StageTests(Base):
    """One click stages one pending proposal for Review; nothing is applied; Undo leaves nothing."""

    def setUp(self):
        super().setUp()
        self.check([alan_said(kept={"id": "ABC-P-012", "evidence": "Alan sent the budget summary to Sara"})])
        self.aid, self.key = self.card()["id"], self.proms()[0]["key"]

    def test_add_stages_one_pending_new_promise_routine_in_review(self):
        got = self.call("vip_promise_stage", self.aid, self.key)
        self.assertEqual(got["state"], "staged")
        [(name, item)] = self.staged()
        self.assertEqual(name, got["proposal"])
        self.assertEqual((item["op"], item["table"], item["decision"]), ("new", "promises", "pending"))
        v = item["values"]
        self.assertEqual({k: v[k] for k in ("project", "promised_by", "promised_to", "description", "due_date", "raised")},
                         {"project": "ABC", "promised_by": "Alan Carter", "promised_to": "Sara Example",
                          "description": "Send the revised plan to Mia", "due_date": "2026-10-09", "raised": "2026-10-08"})
        self.assertIn("https://outlook.example/owa/?ItemID=t1", v["source"])
        self.assertEqual(item["suggested"], {"feature": "promise", "threads": [self.aid], "key": self.key})
        self.assertEqual(item["why"], "From a thread: you promised it in a message you sent")
        self.assertEqual(item["flags"], [])
        rule = py(self.v, "import review\nprint(json.dumps(review.individual_only(json.load(open('system/staging/" + name
                  + "'))['items'][0])))")
        self.assertIsNone(rule)                                                                # routine, as every new promise
        self.assertEqual(self.proms()[0]["state"], "staged")
        self.assertEqual(self.call("vip_promise_stage", self.aid, self.key), {"refused": "Already staged for Review."})
        self.assertEqual(len(self.staged()), 1)
        self.assertNotIn("ABC-P-014", self.promise_rows())                                    # nothing applied

    def test_undo_leaves_nothing_and_a_decided_or_changed_one_is_refused(self):
        self.call("vip_promise_stage", self.aid, self.key)
        self.assertEqual(self.call("vip_promise_unstage", self.aid, self.key)["state"], "undone")
        self.assertEqual(self.staged(), [])
        self.assertEqual(self.proms()[0]["state"], "offered")
        for change, said in (({"as_proposed": {"description": "x"}}, "You changed it in Review, so decide it there."),
                             ({"decision": "approved"}, "Already decided in Review.")):
            with self.subTest(said):
                self.call("vip_promise_stage", self.aid, self.key)
                [(name, item)] = self.staged()
                f = self.v.root / "system/staging" / name
                spec = json.loads(f.read_text())
                spec["items"][0].update(change)
                f.write_text(json.dumps(spec))
                self.assertEqual(self.call("vip_promise_unstage", self.aid, self.key), {"refused": said})
                self.assertEqual(len(self.staged()), 1)
                f.unlink()
                st = vip_file(self.v)
                st["alerts"][0]["promises"][0].update({"state": "offered"})
                st["alerts"][0]["promises"][0].pop("staged")
                (self.v.root / "system/staging/vip.json").write_text(json.dumps(st))

    def test_undo_of_an_item_that_is_no_longer_the_cards_is_refused_and_changes_nothing(self):
        self.call("vip_promise_stage", self.aid, self.key)
        [(name, item)] = self.staged()
        f = self.v.root / "system/staging" / name
        spec = json.loads(f.read_text())
        spec["items"][0]["suggested"]["threads"] = ["another-card"]
        f.write_text(json.dumps(spec))
        self.assertEqual(self.call("vip_promise_unstage", self.aid, self.key),
                         {"refused": "That isn't this thread's to take back: decide it in Review."})
        self.assertEqual(len(self.staged()), 1)
        self.assertEqual(self.proms()[0]["state"], "staged")

    def test_no_due_date_and_an_unknown_name_are_flagged(self):
        self.reset()
        self.check([alan_said(promise(to="Zed Unknown", due=None))])
        p = self.proms()[0]
        self.call("vip_promise_stage", self.card()["id"], p["key"])
        [(name, item)] = self.staged()
        self.assertEqual(item["flags"], ["no-due-date", "unknown-owner"])
        self.assertNotIn("due_date", item["values"])
        self.assertEqual(item["values"]["promised_to"], "Zed Unknown")

    def test_dismiss_stages_nothing_and_undo_puts_it_back(self):
        self.assertEqual(self.call("vip_promise_dismiss", self.aid, self.key)["state"], "dismissed")
        self.assertEqual(self.call("vip_promise_stage", self.aid, self.key),
                         {"refused": "That promise was dismissed: Undo the dismiss first."})
        self.assertEqual(self.staged(), [])
        self.assertEqual(self.call("vip_promise_action", self.aid, "dismiss", self.key, True)["state"], "offered")
        self.assertEqual(self.call("vip_promise_action", self.aid, "add", self.key)["state"], "staged")

    def test_the_click_checks_the_card_again(self):
        def edit(**fields):
            st = vip_file(self.v)
            st["alerts"][0].update(fields)
            (self.v.root / "system/staging/vip.json").write_text(json.dumps(st))
        cases = {"handled": ({"state": "handled", "seen": "2026-10-08 09:12"}, "This thread is handled: nothing to stage."),
                 "seen": ({"seen": "2026-10-08 09:12"}, "This thread was marked seen: nothing to stage."),
                 "private": ({"marker": "private"}, "No promises for a private conversation.")}
        card = self.card()
        for name, (fields, said) in cases.items():
            with self.subTest(name):
                edit(**{k: card.get(k) for k in ("state", "seen", "marker")})
                edit(**fields)
                self.assertEqual(self.call("vip_promise_stage", self.aid, self.key), {"refused": said})
                self.assertEqual(self.call("vip_kept_stage", self.aid), {"refused": said})
        edit(**{k: card.get(k) for k in ("state", "seen", "marker")})
        self.assertEqual(self.call("vip_promise_stage", self.aid, "nope"), {"refused": "That promise isn't on this thread any more."})
        self.assertEqual(self.call("vip_promise_stage", "nope", self.key), {"refused": "That thread isn't on Today any more."})
        self.assertEqual(self.call("vip_promise_action", self.aid, "apply", self.key), {"refused": "Add, kept or dismiss?"})
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:              # now open under another ID
            con.execute("INSERT INTO promises (id, project, promised_by, promised_to, description, raised, source) VALUES "
                        "('ABC-P-020', 'ABC', 'Alan Carter', 'Sara Example', 'Send the revised plan to Mia', '2026-10-08', 'x')")
            con.commit()
        self.assertEqual(self.call("vip_promise_stage", self.aid, self.key), {"refused": "ABC-P-020 is already open for this."})

    def test_kept_stages_one_pending_done_held_on_its_own_with_looks_done(self):
        got = self.call("vip_kept_stage", self.aid)
        self.assertEqual((got["id"], got["state"]), ("ABC-P-012", "staged"))
        [(name, item)] = self.staged()
        self.assertEqual((item["op"], item["table"], item["id"], item["changes"], item["decision"]),
                         ("update", "promises", "ABC-P-012", {"status": "Done"}, "pending"))
        self.assertTrue(item["based_on"])
        self.assertEqual(item["suggested"]["feature"], "done")
        self.assertEqual(item["suggested"]["evidence"]["said"], "Alan sent the budget summary to Sara")
        self.assertEqual(item["why"], "Looks kept: Alan sent the budget summary to Sara")
        rule = py(self.v, "import review\nprint(json.dumps(review.individual_only(json.load(open('system/staging/" + name
                  + "'))['items'][0])))")
        self.assertEqual(rule, "closing update")
        self.v.run("bulk", script="review.py")                                              # Approve routine leaves it
        self.assertEqual(self.staged()[0][1]["decision"], "pending")
        rows = py(self.v, "import build_dashboard, tracker\ncon = tracker.connect()\n"
                          "print(json.dumps([r.get('dn') for r in build_dashboard.review_queue(con) if r.get('dn')]))")
        self.assertEqual([(r["strength"], r["ev"]) for r in rows],
                         [("Looks done", "Mail 08-10-2026 09:10 by Alan Carter: Alan sent the budget summary to Sara")])
        self.assertEqual(self.call("vip_kept_stage", self.aid), {"refused": "Already staged for Review."})
        self.assertEqual(self.promise_rows()["ABC-P-012"], "Open")                          # nothing applied
        self.assertEqual(self.call("vip_kept_unstage", self.aid)["state"], "undone")
        self.assertEqual(self.staged(), [])

    def test_kept_is_refused_once_pending_elsewhere_closed_or_switched_off(self):
        f = self.v.root / "system/staging/proposed-2026-10-08-090000-edit.json"
        f.write_text(json.dumps({"source_run": "cx-edit", "files": [], "items": [
            {"n": 1, "op": "update", "table": "promises", "id": "ABC-P-012", "changes": {"status": "Done"}, "decision": "pending"}]}))
        self.assertEqual(self.call("vip_kept_stage", self.aid), {"refused": "Already staged for Review."})
        f.unlink()
        self.settings(drafting={"done": False})
        self.assertEqual(self.call("vip_kept_stage", self.aid), {"refused": "Looks done suggestions are switched off in Settings."})
        self.settings(drafting={"done": True})
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            con.execute("UPDATE promises SET status = 'Done', closed = '2026-10-08' WHERE id = 'ABC-P-012'")
            con.commit()
        self.assertEqual(self.call("vip_kept_stage", self.aid), {"refused": "ABC-P-012 isn't open any more."})
        self.assertEqual(self.staged(), [])
        refreshed = py(self.v, "st = sweep.vip_made_refresh(); print(json.dumps(st['alerts'][0]['kept']))")
        self.assertIs(refreshed["open"], False)                                               # the card hides it

    def test_a_decided_promise_is_done_on_the_card(self):
        self.call("vip_promise_stage", self.aid, self.key)
        [(name, item)] = self.staged()
        f = self.v.root / "system/staging" / name
        spec = json.loads(f.read_text())
        spec["items"][0]["decision"] = "approved"
        f.write_text(json.dumps(spec))
        self.v.run("apply")
        self.assertEqual(py(self.v, "st = sweep.vip_made_refresh(); print(json.dumps(st['alerts'][0]['promises'][0]['state']))"),
                         "done")
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            row = con.execute("SELECT id, promised_by, promised_to, status FROM promises WHERE description = ?",
                              ("Send the revised plan to Mia",)).fetchone()
        self.assertEqual(row[1:], ("Alan Carter", "Sara Example", "Open"))
        self.assertEqual(row[0], "ABC-P-014")                                                  # the shared number sequence
        self.assertEqual(self.call("vip_promise_unstage", self.aid, self.key), {"refused": "Already decided in Review."})


class CountTests(Base):
    """Activity › Quality counts the card's promises as their own feature: offered, used, edited, rejected (counts only)."""

    def test_decisions_are_counted_and_quality_lists_the_feature(self):
        got = py(self.v, "import extraction, quality\n"
                         "it = {'suggested': {'feature': 'promise'}}\n"
                         "extraction.count_decision(it, 'approved'); extraction.count_decision({**it, 'as_proposed': {'a': 1}}, 'approved')\n"
                         "extraction.count_decision(it, 'rejected'); extraction.count_decision(it, 'pending')\n"
                         "print(json.dumps([r for r in quality.drafts_rows() if r['feature'] == 'promise']))")
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["label"], "Promises from your own messages")
        stats = self.stats()["promise"]
        self.assertEqual((stats["used"], stats["edited"], stats["rejected"]), (1, 1, 1))
        self.assertNotIn("promise", py(self.v, "import drafts\nprint(json.dumps(list(drafts.FEATURES)))"))   # no switch

    def test_the_page_counts_its_own_review_decision(self):
        src = (Path(__file__).resolve().parents[2] / "system/templates/dashboard/src/review.js").read_text()
        self.assertIn('it.suggested.feature==="promise"&&(v==="approved"||v==="rejected")) draft' + 'Stat("promise",v==="rejected"', src)


class ConfidentialTests(Base):
    SUBJECT = "Project Falcon board secrets"
    SUMMARY = "The board discussed the secret plan figures and hiring."

    def test_a_confidential_promise_and_kept_are_staged_in_neutral_words(self):
        self.check([alan_said(promise(what="Send the board the secret hiring figures"), sensitivity="confidential",
                              subject=self.SUBJECT, title=self.SUBJECT, summary=self.SUMMARY,
                              kept={"id": "ABC-P-012", "evidence": "Alan sent the secret budget summary"})])
        a = self.card()
        self.assertEqual(a["promises"][0]["what"], "Send the board the secret hiring figures")   # the card is internal
        self.call("vip_promise_stage", a["id"], a["promises"][0]["key"])
        self.call("vip_kept_stage", a["id"])
        items = [i for _, i in self.staged()]
        new = next(i for i in items if i["op"] == "new")
        kept = next(i for i in items if i["op"] == "update")
        self.assertEqual(new["values"]["description"], "Follow up on a confidential thread")
        self.assertEqual(new["why"], "From a confidential thread")
        self.assertEqual(kept["why"], "Looks kept: from a confidential thread")
        self.assertEqual(kept["suggested"]["evidence"]["said"], "The thread shows it done.")
        self.assertNotIn("who", kept["suggested"]["evidence"])
        staged = json.dumps(items)
        for word in ("secret", "hiring", self.SUBJECT, "Falcon", SECRET):
            self.assertNotIn(word, staged)
        self.assertNotRegex(staged, r"(?i)\bboard\b")                                       # "dashboard" is the source_run
        self.assertNotRegex(staged, r"\bVIP\b")

    def test_a_private_card_offers_none_and_a_late_private_flag_takes_the_offer_away(self):
        self.check([alan_said(kept={"id": "ABC-P-012", "evidence": "Alan sent it"})])
        self.assertTrue(self.proms())
        self.check([alan_said(sensitivity="private", last=f"2026-10-08T09:12{OFF}", replied=f"2026-10-08T09:12{OFF}",
                              promises=[promise(at=f"2026-10-08T09:12{OFF}")])])
        a = self.card()
        self.assertNotIn("promises", a)
        self.assertNotIn("kept", a)


class MergeTests(Base):
    """card_merge: the kept card holds both cards' promises; a staged one stays reachable by Undo on the kept card."""

    MERGE = ("st = sweep.vip_state(); keep, drop = [next(a for a in st['alerts'] if a['id'] == x) for x in sys.argv[1:3]]\n"
             "sweep.card_merge(st, keep, drop); sweep.vip_save(st)\nprint(json.dumps(keep))")

    def merge(self, keep, drop):
        r = subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts'); import sweep\n" + self.MERGE,
                            keep, drop], cwd=self.v.root, capture_output=True, text=True,
                           env={**os.environ, "CREAITE_NOW": NOW, "CREAITE_TZ_OFFSET": OFF})
        if r.returncode:
            raise AssertionError(r.stdout + r.stderr)
        return json.loads(r.stdout)

    def test_promises_and_staged_kept_survive_a_merge_and_undo_reaches_both(self):
        self.check([alan_said(kept={"id": "ABC-P-012", "evidence": "Alan sent the budget summary to Sara"})])
        a = self.card()["id"]
        extra = {"conversation": MAIL_ID + "2", "subject": "Project Falcon plan, again", "title": "Project Falcon plan, again",
                 "link": "https://outlook.example/owa/?ItemID=t2"}
        self.check([sara_kept(**extra)])
        b = next(x["id"] for x in self.cards() if x["id"] != a)
        key = next(x for x in self.cards() if x["id"] == a)["promises"][0]["key"]
        self.call("vip_promise_stage", a, key)
        self.call("vip_kept_stage", a)
        self.call("vip_kept_stage", b)
        self.assertEqual(len(self.staged()), 3)
        kept = self.merge(b, a)
        self.assertEqual([p["key"] for p in kept["promises"]], [key])
        self.assertEqual(kept["kept"]["id"], "ABC-P-013")
        self.assertEqual([k["id"] for k in kept["kept_more"]], ["ABC-P-012"])
        self.assertEqual(self.call("vip_promise_unstage", b, key)["state"], "undone")       # by the merged card's ID
        self.assertEqual(self.call("vip_kept_unstage", b)["state"], "undone")
        self.assertEqual(self.staged(), [])                                                  # nothing orphaned


class ClientOutputTests(Base):
    def test_an_applied_promise_reaches_no_client_report_or_client_safe_one_pager(self):
        self.check([alan_said(promise(what="Send Mia the private pricing workbook"))])
        a = self.card()
        self.call("vip_promise_stage", a["id"], a["promises"][0]["key"])
        for name, _ in self.staged():
            f = self.v.root / "system/staging" / name
            spec = json.loads(f.read_text())
            spec["items"][0]["decision"] = "approved"
            f.write_text(json.dumps(spec))
        self.v.run("apply")
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            self.assertEqual(con.execute("SELECT count(*) FROM promises WHERE description LIKE '%pricing workbook%'").fetchone()[0], 1)
            cols = [r[1] for r in con.execute("PRAGMA table_info(promises)")]
        self.assertNotIn("client_visible", cols)                                              # no flag exists or is added
        r = subprocess.run([sys.executable, str(self.v.root / "system/scripts/report.py"), "client-data", "ABC", "--since",
                            "2026-10-01"], cwd=self.v.root, env={**os.environ, "CREAITE_NOW": NOW}, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        said = [r.stdout]
        f = self.v.root / "system/staging/drafts/steerco5.json"
        f.write_text(json.dumps({"code": "ABC", "version": "client", "force": True}))
        r = subprocess.run([sys.executable, str(self.v.root / "system/scripts/report.py"), "steerco-stage", str(f)],
                           cwd=self.v.root, env={**os.environ, "CREAITE_NOW": NOW}, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        spec = json.loads(sorted((self.v.root / "system/staging").glob("proposed-2*-steerco*.json"))[-1].read_text())
        with zipfile.ZipFile(self.v.root / spec["report"]["draft"]) as z:
            said.append(re.sub(r"<[^>]+>", " ", z.read("word/document.xml").decode("utf-8")) + r.stdout)
        for text in said:
            self.assertNotIn("pricing workbook", text)


class GuardTests(unittest.TestCase):
    """Part 5 adds no claude launch and changes no command line; the route holds LOCK then VIP_WRITE, never while claude runs."""

    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[2] / "system/scripts"
        cls.ls_src = (root / "live_server.py").read_text(encoding="utf-8")
        sw = (root / "sweep.py").read_text(encoding="utf-8")
        cls.block = sw[sw.index("# ===== BL-342 Part 5:"):sw.index("# ===== end BL-342 Part 5 =====")]

    def test_the_route_holds_lock_then_vip_write_and_launches_nothing(self):
        body = self.ls_src[self.ls_src.index("def alert_promise_route("):self.ls_src.index("SWEEP_ALERT_ROUTES.update({\"/api/alerts/promise\"")]
        self.assertIn("with LOCK, VIP_WRITE:", body)
        for word in ("subprocess", "prompt_last", "claude", "Popen"):
            self.assertNotIn(word, body)

    def test_the_sweep_code_launches_nothing_and_never_writes_the_record(self):
        for word in ("subprocess", "claude_path", "Popen", "tracker.connect", "tracker.main", "apply", "os.system"):
            self.assertNotIn(word, self.block, word)
        self.assertEqual(self.block.count("vip_ro()"), 4)                                    # read-only connections only

    def test_one_claude_launch_in_the_whole_server_for_the_check(self):
        body = self.ls_src[self.ls_src.index("def vip_check("):self.ls_src.index("\ndef ", self.ls_src.index("def vip_check(") + 1)]
        self.assertEqual((body.count("prompt_last("), body.count("subprocess.run(")), (1, 1))
        self.assertIn('"offered_promises": parts["offered_promises"]', body)


class PromiseServerTests(unittest.TestCase):
    """The live server's own check with a stand-in claude: the prompt carries the promise rules and OPEN PROMISES; the reply's
    promise and kept are checked; the route stages and undoes by the card's ID and the promise's key; no label anywhere."""

    @classmethod
    def setUpClass(cls):
        cls.v = v = vip_vault()
        seed(v)
        seed_promises(v)
        check_since(v)
        reply = [alan_said(kept={"id": "ABC-P-012", "evidence": "Alan sent the budget summary to Sara"})]
        (v.root / "vip-replies.json").write_text(json.dumps([reply]))
        fake = v.root / "fake_claude.py"
        fake.write_text(FAKE)
        fake.chmod(0o755)
        cls.port = free_port()
        cls.base = f"http://127.0.0.1:{cls.port}"
        cls.proc = subprocess.Popen([sys.executable, str(v.root / "system/scripts/live_server.py")], cwd=v.root,
                                    env={**os.environ, "CREAITE_PORT": str(cls.port), "CREAITE_CLAUDE": str(fake),
                                         "CREAITE_NOW": NOW, "CREAITE_TZ_OFFSET": OFF},
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(300):
            try:
                urllib.request.urlopen(cls.base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        html = urllib.request.urlopen(cls.base + "/").read().decode()
        cls.token = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]
        for _ in range(600):
            if re.search(r"INFO\s+vip\s", cls.log()):
                break
            time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)
        cls.v.cleanup()

    @classmethod
    def log(cls):
        return "\n".join(f.read_text() for f in (cls.v.root / "system/logs").glob("debug-*.log"))

    def post(self, path, body):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())

    def test_the_prompt_asks_for_alans_promises_and_lists_the_open_ones(self):
        calls = [json.loads(f.read_text()) for f in sorted(self.v.root.glob("vip-call-*.json"))]
        self.assertEqual(len(calls), 1)
        args = calls[0]["args"]
        self.assertNotIn("--model", args)
        prompt = args[-1]
        self.assertIn("Alan's promises: in Alan's own message that you give as \"replied\"", prompt)
        self.assertIn("a promise made to Alan", prompt)
        self.assertIn('"ABC-P-012"', prompt)                                                  # OPEN PROMISES filled
        self.assertNotIn("ABC-P-009", prompt)                                                 # a Done one never
        self.assertIn('"kept": {"id": "the ID exactly as listed"', prompt)
        self.assertIn("no items, type, ask, due, owners, match, closes, promises or kept", prompt)
        self.assertEqual(re.findall(r"VIP", prompt.replace("creaite VIP check.", "").replace("creaite follow check.", "").replace("Never use the word VIP", "")), [])

    def test_the_debug_line_counts_the_promises(self):
        lines = [ln for ln in self.log().splitlines() if re.search(r"\s+vip\s", ln)]
        self.assertEqual(len(lines), 1, lines)
        self.assertIn("promises offered 1, promise kept offered 1", lines[0])
        for word in ("revised plan", "Sara", "budget", SECRET):
            self.assertNotIn(word, lines[0])

    def test_z_the_route_stages_undoes_and_dismisses_by_id_and_key(self):
        card = next(a for a in vip_file(self.v)["alerts"] if a.get("promises"))
        aid, key = card["id"], card["promises"][0]["key"]
        said = [self.post("/api/alerts/promise", {"id": aid, "what": "add", "key": key})]
        self.assertEqual((said[0]["ok"], said[0]["state"]), (True, "staged"))
        self.assertEqual(said[0]["promises"][0]["staged"]["proposal"], said[0]["proposal"])
        said.append(self.post("/api/alerts/promise", {"id": aid, "what": "add", "key": key}))
        self.assertEqual((said[-1]["ok"], said[-1]["error"]), (False, "Already staged for Review."))
        said.append(self.post("/api/alerts/promise", {"id": aid, "what": "kept"}))
        self.assertEqual((said[-1]["ok"], said[-1]["id"]), (True, "ABC-P-012"))
        self.assertEqual(len(list((self.v.root / "system/staging").glob("proposed-*-dashboard*.json"))), 2)
        said.append(self.post("/api/alerts/promise", {"id": aid, "what": "kept", "undo": True}))
        said.append(self.post("/api/alerts/promise", {"id": aid, "what": "add", "key": key, "undo": True}))
        self.assertEqual([s["state"] for s in said[-2:]], ["undone", "undone"])
        self.assertEqual(list((self.v.root / "system/staging").glob("proposed-*-dashboard*.json")), [])
        said.append(self.post("/api/alerts/promise", {"id": aid, "what": "dismiss", "key": key}))
        self.assertEqual(said[-1]["state"], "dismissed")
        said.append(self.post("/api/alerts/promise", {"id": aid, "what": "dismiss", "key": key, "undo": True}))
        self.assertEqual(said[-1]["state"], "offered")
        said.append(self.post("/api/alerts/promise", {"id": "nope", "what": "add", "key": key}))
        self.assertFalse(said[-1]["ok"])
        said.append(self.post("/api/vip", {}))
        text = json.dumps(said) + json.dumps(vip_file(self.v))
        self.assertNotRegex(text.replace('"vip', ""), r"\bVIP\b")
        self.assertNotIn(SECRET, text)
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            self.assertEqual(con.execute("SELECT status FROM promises WHERE id = 'ABC-P-012'").fetchone()[0], "Open")


if __name__ == "__main__":
    unittest.main()
