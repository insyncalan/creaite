"""BL-342 Part 1: a thread's card (type, ask, due date, owners), its keys, Handled, Replied and Log on the matched item.

Run: python3 dev/tests/test_vip_threads.py
A throwaway vault with fictional people and a stand-in Claude (never Microsoft 365). Covers each "Done when" point of Part 1:
a three-message chat gives one card with a type, a due date, owners and an ask, and a greeting-only thread is type fyi with no
buttons; a due date that is not a date is dropped and overdue cards sort first; Handled settles the card, stages nothing and
Undo puts it back; a reply in the thread closes it as Replied and a later message from someone else opens it again; a thread
matches a card on any key it has been seen under and two cards found to share an ID are merged (Handled kept); Log on the
matched item stages exactly one pending `update` with `based_on`, clicking again stages nothing new, and a second thread for
the same item adds a line to the same proposal; a confidential thread logs only the neutral line; and the word VIP and message
text appear nowhere (vip.json, the proposals).
"""
import json
import os
import re
import subprocess
import sys
import time
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_live_server import free_port  # noqa: E402
from test_sweep_alerts import TZ, check_since, fast_checks, run, vip_file, vip_vault, zoned  # noqa: E402

MIA = "Mia Hale <mia@client.example>"
OMAR = "Omar Ali <omar@company.example>"
SECRET = "SECRET MESSAGE TEXT"
NOW = "2026-10-09 13:00"

CHAT = {"kind": "teams", "conversation": "19:chat-falcon@thread.v2", "title": "Project Falcon go-live",
        "from": MIA, "people": [MIA, OMAR], "last": "2026-10-08 08:40",
        "link": "https://teams.microsoft.com/l/chat/19:chat-falcon", "sensitivity": "normal", "attachments": [],
        "summary": "Mia's team will take the solution from production to live (VIP); Omar to confirm the date.",
        "type": "action", "ask": "Confirm the go-live date with Mia's team (VIP)", "due": "2026-10-20",
        "owners": ["you", "Omar Ali"],
        "items": [{"type": "action", "text": "Confirm the go-live date", "owner": "Omar Ali", "due": "2026-10-20"}],
        "messages": [{"text": SECRET}], "body": SECRET}
HELLO = {"kind": "teams", "conversation": "19:chat-hello@thread.v2", "title": "Group chat", "from": MIA,
         "people": [MIA, OMAR], "last": "2026-10-08 08:20", "link": "https://teams.microsoft.com/l/chat/19:chat-hello",
         "sensitivity": "normal", "summary": "Greetings only.", "items": [], "body": SECRET}
MAIL = {"kind": "mail", "conversation": "AAQk-mail-1", "title": "Licence numbers", "subject": "Licence numbers", "from": MIA,
        "people": [MIA, OMAR], "last": "2026-10-08 10:00", "link": "https://outlook.example/owa/?ItemID=m1",
        "sensitivity": "normal", "summary": "Mia asks how many test licences are needed.", "type": "decision",
        "ask": "Say how many test licences are needed", "due": "2026-10-12", "owners": "you", "items": []}

FAKE = r'''#!/usr/bin/env python3
import json, sys
from pathlib import Path
args = sys.argv[1:]
here = Path(__file__).parent
n = len(list(here.glob("vip-call-*.json"))) + 1
(here / f"vip-call-{n}.json").write_text(json.dumps(args))
replies = json.loads((here / "vip-replies.json").read_text())
found = replies[min(n, len(replies)) - 1]
print(json.dumps({"type": "result", "result": "Here they are: " + json.dumps(found)}))
'''


def py(v, code, now=NOW):
    """Run some Python in the vault with sweep imported; the last line printed is JSON."""
    r = subprocess.run([sys.executable, "-c", "import json, sys; sys.path.insert(0, 'system/scripts'); import sweep\n" + code],
                       cwd=v.root, capture_output=True, text=True, env={**os.environ, "CREAITE_NOW": now})
    if r.returncode:
        raise AssertionError(r.stdout + r.stderr)
    out = r.stdout.strip().splitlines()
    return json.loads(out[-1]) if out else None


def rec(v, found, now="2026-10-08 09:30", how="sweep"):
    f = v.root / "system/staging/drafts/found.json"
    f.write_text(json.dumps(found))
    return run(v, "sweep.py", "vip", "record", str(f), "--found", how, now=now).stdout


def card(v, title):
    return next(a for a in vip_file(v)["alerts"] if a["title"] == title)


def proposals(v):
    return sorted(p.name for p in (v.root / "system/staging").glob("proposed-*.json"))


def make_action(v, description="Confirm the go-live date"):
    """An open action ABC-A-… in the throwaway tracker (a proposal Alan approved, applied)."""
    spec = {"created": "2026-10-08T09:00:00", "source_run": "cx-edit", "files": [],
            "items": [{"n": 1, "op": "new", "table": "actions", "match": "strong", "flags": [], "decision": "approved",
                       "values": {"project": "ABC", "description": description, "owner": "Omar Ali", "due_date": "2026-10-20",
                                  "raised": "2026-10-01", "source": "Email · From: Omar Ali <omar@company.example> · "
                                  "Subject: Go-live · Sent: 2026-10-01 09:00 · Link: https://x/seed"}}]}
    stamp = f"{len(list((v.root / 'system/staging/applied').glob('*'))) if (v.root / 'system/staging/applied').exists() else 0}"
    (v.root / "system/staging" / f"proposed-2026-10-01-09000{stamp}-edit.json").write_text(json.dumps(spec))
    v.run("apply")
    return next(r["id"] for r in v.rows("actions") if r["description"] == description)


class CardRecordTests(unittest.TestCase):
    """The card's shape and the keys, with the real scripts and a stand-in reply."""

    def setUp(self):
        self.v = vip_vault()

    def tearDown(self):
        self.v.cleanup()

    def test_a_chat_card_has_a_type_an_ask_a_due_date_and_owners(self):
        rec(self.v, [CHAT])
        a = card(self.v, "Project Falcon go-live")
        self.assertEqual((a["type"], a["due"], a["owners"], a["state"]), ("action", "2026-10-20", ["you", "Omar Ali"], "open"))
        self.assertEqual(a["ask"], "Confirm the go-live date with Mia's team")                  # the word taken out (BL-288)
        self.assertFalse(a["quiet"])
        self.assertIn("id:19:chat-falcon@thread.v2", a["keys"])
        self.assertIn("link:https://teams.microsoft.com/l/chat/19:chat-falcon", a["keys"])
        self.assertNotIn("replied_at", a)

    def test_a_greeting_is_fyi_with_no_ask_and_a_quiet_line(self):
        rec(self.v, [HELLO])
        a = card(self.v, "Mia Hale, Omar Ali")
        self.assertEqual((a["type"], a["ask"], a["due"], a["owners"], a["quiet"]), ("fyi", "", None, [], True))

    def test_the_type_defaults_from_the_first_item_and_a_bad_type_too(self):
        rec(self.v, [{**CHAT, "type": "memo", "ask": None, "owners": None, "due": None,
                      "items": [{"type": "risk", "text": "Licences may be late"}]}])
        a = card(self.v, "Project Falcon go-live")
        self.assertEqual((a["type"], a["ask"], a["owners"], a["due"]), ("risk", "", [], None))

    def test_a_due_date_that_is_not_a_date_is_dropped(self):
        for bad in ("next week", "2026-13-45", "20-10-2026", "2026-02-30", "", None, 20261020):
            with self.subTest(bad=bad):
                self.assertIsNone(py(self.v, f"print(json.dumps(sweep.real_date({bad!r})))"))
        self.assertEqual(py(self.v, "print(json.dumps(sweep.real_date('2026-10-20')))"), "2026-10-20")
        rec(self.v, [{**CHAT, "due": "soon", "items": [{"type": "action", "text": "Do it", "due": "tomorrow"}]}])
        a = card(self.v, "Project Falcon go-live")
        self.assertEqual((a["due"], a["candidates"][0]["due"]), (None, None))

    def test_the_ask_is_one_short_line(self):
        rec(self.v, [{**CHAT, "ask": "Reply\n  to   Mia " + "x" * 400}])
        ask = card(self.v, "Project Falcon go-live")["ask"]
        self.assertLessEqual(len(ask), 140)
        self.assertNotIn("\n", ask)

    def test_a_private_thread_has_no_type_ask_due_or_owners(self):
        rec(self.v, [{**CHAT, "sensitivity": "private"}])
        a = vip_file(self.v)["alerts"][0]
        self.assertEqual((a["type"], a["ask"], a["due"], a["owners"], a["marker"]), (None, "", None, [], "private"))

    def test_a_confidential_thread_keeps_the_fields_and_the_mark(self):
        rec(self.v, [{**CHAT, "sensitivity": "confidential"}])
        a = card(self.v, "Project Falcon go-live")
        self.assertEqual((a["type"], a["due"], a.get("confidential")), ("action", "2026-10-20", True))

    def test_no_message_text_and_no_label_in_vip_json(self):
        rec(self.v, [CHAT, HELLO, MAIL])
        text = (self.v.root / "system/staging/vip.json").read_text()
        self.assertNotIn(SECRET, text)
        self.assertNotRegex(text, r"(?i)\bvips?\b")

    # ----- keys -----

    def test_a_mail_thread_matches_on_its_local_key_when_the_id_is_missing(self):
        rec(self.v, [MAIL])
        again = {**MAIL, "conversation": None, "subject": "RE: [ABC] Licence numbers", "title": "RE: Licence numbers",
                 "link": "https://outlook.example/owa/?ItemID=m2", "last": "2026-10-08 11:00", "summary": "Omar answered."}
        rec(self.v, [again], now="2026-10-08 12:00")
        alerts = vip_file(self.v)["alerts"]
        self.assertEqual(len(alerts), 1)                                                       # one card for one thread
        self.assertEqual(alerts[0]["summary"], "Omar answered.")
        self.assertEqual(alerts[0]["last"], "2026-10-08 11:00")
        self.assertEqual(alerts[0]["conv"], "AAQk-mail-1")                                      # the card keeps its ID
        self.assertTrue(any(k.startswith("loc:") for k in alerts[0]["keys"]))

    def test_the_id_turning_up_later_is_added_to_the_card(self):
        rec(self.v, [{**MAIL, "conversation": None}])
        self.assertFalse(card(self.v, "Licence numbers").get("conv"))
        rec(self.v, [MAIL], now="2026-10-08 12:00")                                             # nothing newer, but the ID is learnt
        a = card(self.v, "Licence numbers")
        self.assertEqual(a["conv"], "AAQk-mail-1")
        self.assertIn("id:AAQk-mail-1", a["keys"])
        self.assertEqual(len(vip_file(self.v)["alerts"]), 1)

    def test_two_chats_that_share_a_link_but_not_an_id_stay_two(self):
        rec(self.v, [CHAT, {**CHAT, "conversation": "19:other@thread.v2", "title": "Another chat"}])
        self.assertEqual(len(vip_file(self.v)["alerts"]), 2)

    def test_two_cards_found_to_share_an_id_are_merged_and_handled_is_kept(self):
        a1 = {**MAIL, "conversation": None, "link": "https://outlook.example/owa/?ItemID=a", "last": "2026-10-08 09:00",
              "summary": "First reading."}
        rec(self.v, [a1])                                                                       # card A: link and local key only
        rec(self.v, [{**MAIL, "subject": "Something else", "title": "Something else", "conversation": "AAQk-mail-1",
                      "link": "https://outlook.example/owa/?ItemID=b", "last": "2026-10-08 09:10", "summary": "Second."}])
        self.assertEqual(len(vip_file(self.v)["alerts"]), 2)
        first = next(x for x in vip_file(self.v)["alerts"] if x["title"] == "Licence numbers")
        py(self.v, f"sweep.vip_handled({{{first['id']!r}}})")                                   # A is handled
        rec(self.v, [{**MAIL, "last": "2026-10-08 09:20", "summary": "Newest."}], now="2026-10-08 09:40")   # ID of B, subject of A
        alerts = vip_file(self.v)["alerts"]
        self.assertEqual(len(alerts), 1)                                                         # merged
        m = alerts[0]
        self.assertEqual((m["id"], m["summary"], m["last"]), (first["id"], "Newest.", "2026-10-08 09:20"))
        self.assertIn("id:AAQk-mail-1", m["keys"])
        self.assertTrue(any(k.startswith("loc:") for k in m["keys"]))
        self.assertTrue(any(k == "link:https://outlook.example/owa/?ItemID=b" for k in m["keys"]))

    def test_the_merge_keeps_the_newest_summary_and_handled(self):
        rec(self.v, [{**MAIL, "conversation": None, "last": "2026-10-08 09:00", "summary": "Old.",
                      "link": "https://outlook.example/owa/?ItemID=a"}])
        rec(self.v, [{**MAIL, "title": "Other", "subject": "Other", "last": "2026-10-08 09:05", "summary": "Newer.",
                      "link": "https://outlook.example/owa/?ItemID=b"}])
        a, b = vip_file(self.v)["alerts"]
        py(self.v, f"sweep.vip_handled({{{b['id']!r}}})")                                       # the newer one is handled
        got = py(self.v, """st = sweep.vip_state()
x, y = st['alerts']
sweep.card_merge(st, x, y)
print(json.dumps({'n': len(st['alerts']), 'summary': x['summary'], 'state': x['state'], 'seen': bool(x['seen'])}))""")
        self.assertEqual(got, {"n": 1, "summary": "Newer.", "state": "handled", "seen": True})

    # ----- Handled and Undo -----

    def test_handled_settles_the_card_stages_nothing_and_undo_puts_it_back(self):
        rec(self.v, [CHAT])
        aid = card(self.v, "Project Falcon go-live")["id"]
        before = proposals(self.v)
        got = py(self.v, f"print(json.dumps(sweep.vip_handled({{{aid!r}}})))")
        self.assertEqual(got, [aid])
        a = card(self.v, "Project Falcon go-live")
        self.assertEqual(a["state"], "handled")
        self.assertTrue(a["seen"] and a["handled_at"])
        self.assertEqual(proposals(self.v), before)                                             # nothing staged
        self.assertEqual(py(self.v, f"print(json.dumps(sweep.vip_handled({{{aid!r}}})))"), [])   # already settled
        py(self.v, f"print(json.dumps(sweep.vip_undismiss({{{aid!r}}})))")
        a = card(self.v, "Project Falcon go-live")
        self.assertEqual((a["state"], a["seen"]), ("open", None))
        self.assertNotIn("handled_at", a)

    # ----- Replied -----

    def test_a_reply_after_the_last_message_closes_the_card_as_replied(self):
        rec(self.v, [CHAT])
        rec(self.v, [{**CHAT, "replied": "2026-10-08 09:15"}], now="2026-10-08 09:30")
        a = card(self.v, "Project Falcon go-live")
        self.assertEqual((a["state"], a["replied_at"]), ("replied", "2026-10-08 09:15"))
        self.assertIsNone(a["seen"])
        self.assertEqual(py(self.v, "print(json.dumps([sweep.vip_open(a) for a in sweep.vip_state()['alerts']]))"), [False])

    def test_a_reply_before_the_last_message_is_not_a_reply(self):
        rec(self.v, [{**CHAT, "replied": "2026-10-08 08:00"}])
        self.assertEqual(card(self.v, "Project Falcon go-live")["state"], "open")

    def test_a_later_message_from_someone_else_opens_it_again(self):
        rec(self.v, [CHAT])
        rec(self.v, [{**CHAT, "replied": "2026-10-08 09:15"}])
        rec(self.v, [{**CHAT, "last": "2026-10-08 10:30", "summary": "Mia replied with a new date."}], now="2026-10-08 11:00")
        a = card(self.v, "Project Falcon go-live")
        self.assertEqual((a["state"], a["summary"]), ("open", "Mia replied with a new date."))
        self.assertNotIn("replied_at", a)
        self.assertEqual(py(self.v, "print(json.dumps([sweep.vip_open(a) for a in sweep.vip_state()['alerts']]))"), [True])

    def test_vip_replied_closes_a_card_directly(self):
        rec(self.v, [CHAT])
        aid = card(self.v, "Project Falcon go-live")["id"]
        self.assertFalse(py(self.v, f"print(json.dumps(sweep.vip_replied({aid!r}, '2026-10-08 08:00')))"))   # before the message
        self.assertTrue(py(self.v, f"print(json.dumps(sweep.vip_replied({aid!r}, '2026-10-08 09:00')))"))
        self.assertEqual(card(self.v, "Project Falcon go-live")["replied_at"], "2026-10-08 09:00")

    def test_a_handled_card_is_not_closed_as_replied(self):
        rec(self.v, [CHAT])
        aid = card(self.v, "Project Falcon go-live")["id"]
        py(self.v, f"sweep.vip_handled({{{aid!r}}})")
        rec(self.v, [{**CHAT, "replied": "2026-10-08 09:15"}])
        self.assertEqual(card(self.v, "Project Falcon go-live")["state"], "handled")

    # ----- sort -----

    def test_overdue_cards_sort_first_then_due_date_then_last_message(self):
        alerts = [{"id": "a", "due": None, "last": "2026-10-08 12:00"}, {"id": "b", "due": "2026-10-20", "last": "2026-10-08 08:00"},
                  {"id": "c", "due": "2026-10-05", "last": "2026-10-08 07:00"}, {"id": "d", "due": "2026-10-01", "last": "2026-10-08 06:00"},
                  {"id": "e", "due": None, "last": "2026-10-08 13:00"}, {"id": "f", "due": "2026-10-20", "last": "2026-10-08 09:00"}]
        got = py(self.v, f"print(json.dumps([a['id'] for a in sweep.vip_sort({alerts!r}, '2026-10-08')]))")
        self.assertEqual(got, ["d", "c", "f", "b", "e", "a"])


class LogTests(unittest.TestCase):
    """Log on the matched item: one pending update, once, a line added for a second thread, a neutral line when confidential."""

    def setUp(self):
        self.v = vip_vault()
        self.item = make_action(self.v)
        rec(self.v, [CHAT, MAIL])

    def tearDown(self):
        self.v.cleanup()

    def match(self, title, item=None, relation="update"):
        aid = card(self.v, title)["id"]
        py(self.v, f"""st = sweep.vip_state()
for a in st['alerts']:
    if a['id'] == {aid!r}:
        a['match'] = {{'id': {item or self.item!r}, 'relation': {relation!r}, 'why': 'test'}}
sweep.vip_save(st)""")
        return aid

    def log(self, aid):
        return py(self.v, f"print(json.dumps(sweep.vip_log({aid!r})))")

    def staged(self):
        out = []
        for f in (self.v.root / "system/staging").glob("proposed-*-dashboard*.json"):
            out.append(json.loads(f.read_text()))
        return out

    def row(self):
        return next(r for r in self.v.rows("actions") if r["id"] == self.item)

    def test_log_stages_exactly_one_pending_update_with_based_on(self):
        aid = self.match("Project Falcon go-live")
        before = proposals(self.v)
        got = self.log(aid)
        self.assertEqual((got["id"], got["state"], got["already"]), (self.item, "staged", False))
        self.assertEqual(len(proposals(self.v)), len(before) + 1)
        (spec,) = self.staged()
        self.assertEqual(spec["source_run"], "dashboard")
        (item,) = spec["items"]
        self.assertEqual((item["op"], item["table"], item["id"], item["decision"]), ("update", "actions", self.item, "pending"))
        self.assertEqual(item["based_on"], self.row()["updated_at"])
        self.assertEqual(list(item["changes"]), ["latest_update"])
        self.assertRegex(item["changes"]["latest_update"], r"^\d\d-10-2026: Mia's team will take the solution.* \(from a Teams chat\)$")
        self.assertEqual(item["suggested"]["feature"], "thread")
        self.assertIn("Teams · Chat: Project Falcon go-live", item["source"])
        a = card(self.v, "Project Falcon go-live")
        self.assertEqual((a["match"]["id"], a["match"]["logged"]["proposal"]), (self.item, got["proposal"]))
        self.assertIsNone(a["seen"])                                                            # the card stays until Alan acts
        self.assertEqual(self.row()["latest_update"], None)                                     # nothing reached the tracker

    def test_clicking_again_stages_nothing_new(self):
        aid = self.match("Project Falcon go-live")
        first = self.log(aid)
        before = proposals(self.v)
        again = self.log(aid)
        self.assertEqual((again["already"], again["proposal"], again["state"]), (True, first["proposal"], "staged"))
        self.assertEqual(proposals(self.v), before)
        self.assertEqual(self.staged()[0]["items"][0]["changes"]["latest_update"].count("\n"), 0)

    def test_a_second_thread_for_the_same_item_adds_a_line_to_the_same_proposal(self):
        a1, a2 = self.match("Project Falcon go-live"), self.match("Licence numbers")
        first = self.log(a1)
        before = proposals(self.v)
        second = self.log(a2)
        self.assertEqual(second["proposal"], first["proposal"])
        self.assertEqual(proposals(self.v), before)                                              # one proposal for the item
        (spec,) = self.staged()
        self.assertEqual(len(spec["items"]), 1)
        lines = spec["items"][0]["changes"]["latest_update"].split("\n")
        self.assertEqual(len(lines), 2)
        self.assertIn("Mia's team will take the solution", lines[0])
        self.assertIn("Mia asks how many test licences", lines[1])
        self.assertEqual(spec["items"][0]["suggested"]["threads"], [a1, a2])

    def test_a_change_made_in_review_is_kept_when_a_second_thread_is_logged(self):
        a1, a2 = self.match("Project Falcon go-live"), self.match("Licence numbers")
        first = self.log(a1)
        f = self.v.root / "system/staging" / first["proposal"]
        spec = json.loads(f.read_text())
        spec["items"][0]["changes"]["latest_update"] = "ALAN EDITED TEXT"                       # edited in Review
        f.write_text(json.dumps(spec))
        self.log(a2)
        (spec,) = self.staged()
        lines = spec["items"][0]["changes"]["latest_update"].split("\n")
        self.assertEqual(lines[0], "ALAN EDITED TEXT")
        self.assertEqual(len(lines), 2)
        self.assertIn("Mia asks how many test licences", lines[1])

    def test_a_merged_card_keeps_the_thread_it_had_logged(self):
        a1, a2 = self.match("Project Falcon go-live"), self.match("Licence numbers")
        self.log(a2)
        py(self.v, f"""st = sweep.vip_state()
by = {{a['id']: a for a in st['alerts']}}
sweep.card_merge(st, by[{a1!r}], by[{a2!r}])
sweep.vip_save(st)""")
        got = py(self.v, f"print(json.dumps(sweep.vip_update_stage({a1!r})))")
        self.assertFalse(got["added"])                                                           # the same thread, already in
        self.assertEqual(len(self.staged()[0]["items"][0]["suggested"]["lines"]), 1)

    def test_log_is_refused_without_a_match_for_a_closed_item_and_for_a_private_thread(self):
        aid = card(self.v, "Project Falcon go-live")["id"]
        with self.assertRaises(AssertionError) as e:
            self.log(aid)
        self.assertIn("No matched item", str(e.exception))
        aid = self.match("Project Falcon go-live", item="ABC-A-999")
        with self.assertRaises(AssertionError) as e:
            self.log(aid)
        self.assertIn("isn't open", str(e.exception))
        with self.assertRaises(AssertionError) as e:
            self.log("nope")
        self.assertIn("isn't on Today", str(e.exception))
        self.assertEqual(self.staged(), [])

    def test_a_confidential_thread_logs_only_the_neutral_line(self):
        rec(self.v, [{**CHAT, "conversation": "19:conf@thread.v2", "title": "Budget talk", "link": "https://x/conf",
                      "sensitivity": "confidential", "summary": "SECRET SUMMARY about the budget"}])
        aid = self.match("Budget talk")
        self.log(aid)
        (item,) = self.staged()[0]["items"]
        self.assertRegex(item["changes"]["latest_update"], r"^Discussed in a confidential thread, \d\d-10-2026$")
        self.assertNotIn("SECRET", json.dumps(self.staged()))

    def test_no_label_and_no_message_text_in_the_proposal(self):
        self.log(self.match("Project Falcon go-live"))
        text = json.dumps(self.staged())
        self.assertNotIn(SECRET, text)
        self.assertNotRegex(text, r"(?i)\bvips?\b")

    def test_a_proposal_that_has_gone_lets_the_card_log_again(self):
        aid = self.match("Project Falcon go-live")
        first = self.log(aid)
        (self.v.root / "system/staging" / first["proposal"]).unlink()
        again = self.log(aid)
        self.assertEqual((again["already"], again["state"]), (False, "staged"))


class ThreadServerTests(unittest.TestCase):
    """The live server's check with a stand-in Claude returning the Part 1 fields: the page data (what /api/vip serves) has one
    card with a type, a due date, owners and an ask, and a quiet greeting is type fyi with no buttons."""

    @classmethod
    def setUpClass(cls):
        cls.v = v = vip_vault()
        cfg = v.root / "system/config/settings.json"
        d = json.loads(cfg.read_text())
        d.setdefault("vip", {})["check_minutes"] = 0.02
        cfg.write_text(json.dumps(d, indent=2))
        fast_checks(v)
        (v.root / "vip-replies.json").write_text(json.dumps([zoned([CHAT, HELLO])]))
        check_since(v)
        fake = v.root / "fake_claude.py"
        fake.write_text(FAKE)
        fake.chmod(0o755)
        cls.port = free_port()
        cls.base = f"http://127.0.0.1:{cls.port}"
        cls.proc = subprocess.Popen([sys.executable, str(v.root / "system/scripts/live_server.py")], cwd=v.root,
                                    env={**os.environ, "CREAITE_PORT": str(cls.port), "CREAITE_CLAUDE": str(fake),
                                         "CREAITE_NOW": "2026-10-08 09:30", "CREAITE_TZ_OFFSET": TZ},
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                urllib.request.urlopen(cls.base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        html = urllib.request.urlopen(cls.base + "/").read().decode()
        cls.token = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]
        cls.said = []

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)
        cls.v.cleanup()

    @classmethod
    def post(cls, path, body):
        req = urllib.request.Request(cls.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": cls.token})
        with urllib.request.urlopen(req, timeout=30) as r:
            text = r.read().decode()
        cls.said.append(text)
        return json.loads(text)

    def wait_cards(self):
        for _ in range(150):
            got = self.post("/api/vip", {})
            if len(got["alerts"]) == 2:
                return got
            time.sleep(0.1)
        self.fail(f"never two cards: {got}")

    def test_1_the_page_data_has_the_card_and_the_quiet_line(self):
        got = self.wait_cards()
        card_ = next(a for a in got["alerts"] if not a.get("quiet"))
        self.assertEqual((card_["type"], card_["due"], card_["owners"]), ("action", "2026-10-20", ["you", "Omar Ali"]))
        self.assertEqual(card_["ask"], "Confirm the go-live date with Mia's team")
        quiet = next(a for a in got["alerts"] if a.get("quiet"))
        self.assertEqual((quiet["type"], quiet["ask"], quiet["candidates"]), ("fyi", "", []))
        self.assertEqual(card_["state"], "open")

    def test_2_handled_undo_and_log_over_the_routes(self):
        got = self.wait_cards()
        aid = next(a for a in got["alerts"] if not a.get("quiet"))["id"]
        before = proposals(self.v)
        h = self.post("/api/alerts/handled", {"ids": [aid]})
        self.assertEqual((h["ok"], h["handled"], h["ids"]), (True, 1, [aid]))
        self.assertNotIn(aid, [a["id"] for a in self.post("/api/vip", {})["alerts"]])
        self.assertEqual(proposals(self.v), before)
        self.assertEqual(self.post("/api/alerts/handled", {"ids": [aid]})["handled"], 0)
        u = self.post("/api/alerts/undo", {"ids": [aid]})
        self.assertEqual(u["restored"], 1)
        self.assertIn(aid, [a["id"] for a in self.post("/api/vip", {})["alerts"]])
        no = self.post("/api/alerts/log", {"id": aid})                                             # no match yet
        self.assertEqual((no["ok"], no["message"]), (False, "No matched item to log it on."))

    def test_3_nothing_says_the_label(self):
        self.assertTrue(self.said)
        for text in self.said:
            self.assertNotRegex(text, r"(?i)\bvips?\b")
            self.assertNotIn(SECRET, text)


if __name__ == "__main__":
    unittest.main()
