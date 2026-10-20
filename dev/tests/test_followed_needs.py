"""#236: what the sweep pulls out of a followed person's messages reaches Today (Alan, 19-10-2026).

Alan's answers: (1) both the proposals the sweep stages from a followed person's mail or chat and a note about them written into
a project's memory appear as "From <person>" rows linking to the proposal or note (Review still holds the proposals), and a
recorded message that Today missed is a bug; (2) a dismissed row stays gone unless a follow-up adds a genuine change to an active
item or a new item (a new risk or action), and then it comes back as new; (3) a private conversation shows its title and times only.

Run: python3 dev/tests/test_followed_needs.py     (the quick tier needs no Chrome; the page tier is skipped without it)
A throwaway vault with fictional people. No Microsoft 365. Rows hold references only (file, item number), never message text; the
word that labels a followed person (BL-288) appears nowhere.
"""
import json
import re
import sys
import unittest
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_sweep_alerts import REGISTER, record, run, vip_file, vip_vault  # noqa: E402
from test_vip_threads import py  # noqa: E402
from test_vip_screens import says_vip  # noqa: E402

NOW = "2026-10-09 13:00"
MIA = "Mia Hale <mia@client.example>"
OMAR = "Omar Ali <omar@company.example>"
WORD = re.compile(r"\bVIP\b")
ABC_MEMORY = "projects/ABC Example Programme/CLAUDE.md"


def src(subject, link, sender=MIA, sent="2026-10-08 08:00", kind="Email"):
    """A structured source, as the sweep writes it."""
    if kind == "Teams":
        return f"Teams · Chat: {subject} · From: {sender} · Sent: {sent} · Link: {link}"
    return f"{kind} · From: {sender} · Subject: {subject} · Sent: {sent} · Link: {link}"


def item(text, source, table="actions", **more):
    values = {"project": "ABC", "description": text, "owner": "Alan Carter", "source": source, **more}
    return {"table": table, "match": "strong", "values": values}


def stage(v, items, now=NOW):
    f = v.root / "system/staging/drafts/sweep.json"
    f.write_text(json.dumps({"window": {"start": "2026-10-07 08:00", "end": now}, "items": items}))
    return run(v, "sweep.py", "stage", str(f), now=now).stdout


def stage_note(v, source, text="A fact about the SOW.\n"):
    """A project-memory note about a message, staged as cx-edit stages one (an approved proposal, written at the next apply)."""
    f = v.root / "system/staging/drafts/note.json"
    f.write_text(json.dumps({"source_run": "cx-edit", "items": [], "file_changes": {
        "title": "Add to ABC memory", "project": "ABC", "source": source,
        "file_ops": [{"op": "write", "path": ABC_MEMORY, "content": (v.root / ABC_MEMORY).read_text() + text}]}}))
    return run(v, "propose.py", "stage", str(f), now=NOW).stdout


def page(v):
    run(v, "build_dashboard.py", now=NOW)
    html = (v.root / "dashboard.html").read_text(encoding="utf-8")
    return json.loads(re.search(r'<script type="application/json" id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))


def rows(v, kind=None):
    """The followed-person proposal and note rows the page is given."""
    return [a for a in page(v)["sweep_alerts"]["vip"]["alerts"] if a.get("kind") in ((kind,) if kind else ("proposal", "note"))]


def sync(v, expr="None"):
    """Run followed_sync on the vault's vip.json (saving it, as the poll does) and return `expr` as JSON."""
    return py(v, f"st = sweep.vip_made_refresh()\nprint(json.dumps({expr}))")


def card(v, aid):
    return next(a for a in vip_file(v)["alerts"] if a["id"] == aid)


class Proposals(unittest.TestCase):
    """(a) a proposal from a followed person's message is a row; (b) so is a note; Review keeps both."""

    def setUp(self):
        self.v = vip_vault()

    def tearDown(self):
        self.v.cleanup()

    def test_a_sweep_proposal_from_a_followed_person_is_one_row_linking_to_it(self):
        out = stage(self.v, [item("Send the SOW", src("[ABC] SOW", "https://x/1")),
                             item("Test licences may not arrive", src("[ABC] SOW", "https://x/2"), table="raid", type="Risk"),
                             item("Book the room", src("Room", "https://x/3", sender=OMAR))])
        self.assertIn("Sweep: 3 items", out)
        got = rows(self.v, "proposal")
        self.assertEqual(len(got), 1, got)                                  # one row for the thread; Omar is not followed
        r = got[0]
        self.assertEqual((r["who"], r["title"], r["p"], r["medium"]), ("Mia Hale", "[ABC] SOW", "ABC", "mail"))
        self.assertEqual([x["ref"] for x in r["refs"]], [1, 2])
        self.assertEqual(len({x["file"] for x in r["refs"]}), 1)
        self.assertIsNone(r.get("seen"))
        self.assertEqual(r["link"], "https://x/1")
        pending = [x for x in page(self.v)["review"] if x["flags"] and "vip" in x["flags"]]      # Review still holds them
        self.assertEqual(len(pending), 2)
        self.assertNotIn("Send the SOW", json.dumps(r))                      # references only, never the item's or the message's words

    def test_a_teams_source_with_the_name_only_is_followed_too(self):
        stage(self.v, [item("Confirm go-live", src("Falcon go-live", "https://t/1", sender="Mia Hale", kind="Teams"))])
        got = rows(self.v, "proposal")
        self.assertEqual([(r["who"], r["medium"], r["title"]) for r in got], [("Mia Hale", "teams", "Falcon go-live")])

    def test_the_name_alone_does_not_follow_a_sender_with_another_address(self):
        stage(self.v, [item("Send the SOW", src("[ABC] SOW", "https://x/1", sender="Mia Hale <evil@attacker.example>"))])
        self.assertEqual(rows(self.v), [])                                   # stage flags by address; so does the row
        stage(self.v, [item("Confirm go-live", src("Falcon go-live", "https://t/1", sender="Mia Hale", kind="Teams"))])
        self.assertEqual(len(rows(self.v, "proposal")), 1)                   # no address at all: the name still matches

    def test_a_memory_note_about_the_message_is_a_row_linking_to_the_note(self):
        stage_note(self.v, src("[ABC] SOW", "https://x/9"))
        stage_note(self.v, src("Elsewhere", "https://x/10", sender=OMAR))
        got = rows(self.v, "note")
        self.assertEqual(len(got), 1, got)
        r = got[0]
        self.assertEqual((r["who"], r["title"], r["p"]), ("Mia Hale", "[ABC] SOW", "ABC"))
        self.assertEqual([x["ref"] for x in r["refs"]], ["file_changes"])
        self.assertTrue(r["refs"][0]["file"].endswith("-edit.json"))
        self.assertNotIn("A fact about the SOW", json.dumps(r))

    def test_the_rows_are_pointers_to_review_not_messages_for_the_check_or_the_reports(self):
        stage(self.v, [item("Send the SOW", src("[ABC] SOW", "https://x/1"))])
        sync(self.v)
        got = py(self.v, "st = sweep.vip_state()\nprint(json.dumps([sweep.vip_open(a) for a in st['alerts']"
                         " if a['kind'] in ('proposal','note')], ))")
        self.assertEqual(got, [False])                                       # not counted as an unseen message (reminders, weekly data)
        parts = py(self.v, "print(json.dumps(sweep.vip_prompt_parts()['cards']))")
        self.assertEqual(parts, [])                                          # never offered to the model
        none = py(self.v, "import build_dashboard, report\nprint(json.dumps([build_dashboard.vip_unseen_by_project(),"
                          " report.weekly_vip('ABC', [])['unseen_alerts']]))")
        self.assertEqual(none, [{}, []])                                     # nor in the dashboard's VIP counts or the weekly report

    def test_a_decided_proposal_takes_its_row_away(self):
        stage(self.v, [item("Send the SOW", src("[ABC] SOW", "https://x/1"))])
        self.assertEqual(len(rows(self.v)), 1)
        prop = next((self.v.root / "system/staging").glob("proposed-*-sweep.json"))
        data = json.loads(prop.read_text())
        data["items"][0]["decision"] = "rejected"
        prop.write_text(json.dumps(data))
        self.assertEqual(rows(self.v), [])
        self.assertEqual([a for a in sync(self.v, "st['alerts']") if a["kind"] in ("proposal", "note")], [])

    def test_the_word_is_nowhere(self):
        stage(self.v, [item("Send the SOW", src("[ABC] SOW", "https://x/1"))])
        stage_note(self.v, src("[ABC] SOW", "https://x/9"))
        sync(self.v)
        self.assertIsNone(WORD.search((self.v.root / "system/staging/vip.json").read_text()))
        self.assertIsNone(WORD.search(json.dumps(rows(self.v))))


class Dismissed(unittest.TestCase):
    """(d) dismissed rows stay gone; a genuine change brings one back as new."""

    def setUp(self):
        self.v = vip_vault()
        stage(self.v, [item("Send the SOW", src("[ABC] SOW", "https://x/1"))])
        self.rid = rows(self.v, "proposal")[0]["id"]

    def tearDown(self):
        self.v.cleanup()

    def dismiss(self, rid=None):
        return py(self.v, f"print(json.dumps(sweep.vip_dismiss({{{(rid or self.rid)!r}}})))")

    def test_dismiss_removes_the_row_and_keeps_it_in_the_history(self):
        self.assertEqual(self.dismiss(), [self.rid])
        self.assertEqual(rows(self.v), [])
        self.assertTrue(card(self.v, self.rid)["seen"])
        back = py(self.v, f"print(json.dumps(sweep.vip_undismiss({{{self.rid!r}}})))")
        self.assertEqual(back, [self.rid])
        self.assertEqual([r["id"] for r in rows(self.v)], [self.rid])

    def test_a_re_sweep_that_mentions_it_again_changes_nothing(self):
        self.dismiss()
        out = stage(self.v, [item("Send the SOW", src("[ABC] SOW", "https://x/1"))], now="2026-10-09 15:00")
        self.assertIn("proposed before", out)
        self.assertEqual(rows(self.v), [])
        out = stage(self.v, [item("Send the SOW", src("RE: [ABC] SOW", "https://x/4", sent="2026-10-09 14:00"))], now="2026-10-09 15:05")
        self.assertEqual(rows(self.v), [], out)                              # a later mail asking the same thing is the same item

    def test_a_new_risk_or_action_in_the_thread_brings_it_back_as_new(self):
        self.dismiss()
        stage(self.v, [item("Test licences may not arrive", src("RE: [ABC] SOW", "https://x/5", sent="2026-10-09 14:00"),
                            table="raid", type="Risk")], now="2026-10-09 15:10")
        got = rows(self.v, "proposal")
        self.assertEqual(len(got), 1)
        self.assertIsNone(got[0]["seen"])
        self.assertTrue(got[0].get("returned"))
        self.assertEqual(len(got[0]["refs"]), 2)

    def test_a_staged_update_of_an_active_item_brings_it_back(self):
        self.dismiss()
        self.v.propose("seed", [{"n": 1, "op": "new", "table": "decisions", "match": "strong", "flags": [], "decision": "approved",
                                 "values": {"project": "ABC", "decision": "Pick the vendor", "status": "Pending", "made_by": "Mia Hale",
                                           "source": "Alan (cx-edit)"}}])
        self.v.run("apply")
        f = self.v.root / "system/staging/drafts/u.json"
        f.write_text(json.dumps({"items": [{"op": "update", "table": "decisions", "id": "ABC-D-001", "why": "Mia confirmed it",
                       "set": {"status": "Made"}, "source": src("RE: [ABC] SOW", "https://x/6", sent="2026-10-09 14:00")}]}))
        out = run(self.v, "sweep.py", "stage", str(f), now="2026-10-09 15:10").stdout
        self.assertIn("1 item", out)
        got = rows(self.v, "proposal")
        self.assertEqual([r["id"] for r in got], [self.rid], out)           # the same thread: the dismissed row is back
        self.assertIsNone(got[0]["seen"])

    def test_a_dismissed_note_stays_gone_when_another_note_follows(self):
        stage_note(self.v, src("[ABC] SOW", "https://x/9"))
        nid = rows(self.v, "note")[0]["id"]
        self.dismiss(nid)
        stage_note(self.v, src("RE: [ABC] SOW", "https://x/11"), text="Another fact.\n")
        self.assertEqual(rows(self.v, "note"), [])                           # a note is not an item: no genuine change

    def test_the_returned_row_is_not_stale_after_undo(self):
        self.dismiss()
        py(self.v, f"print(json.dumps(sweep.vip_undismiss({{{self.rid!r}}})))")
        self.assertIsNone(card(self.v, self.rid)["seen"])


CHAT = {"kind": "teams", "conversation": "19:chat-falcon@thread.v2", "title": "Falcon go-live", "from": MIA, "people": [MIA, OMAR],
        "last": "2026-10-08 08:40", "link": "https://teams.microsoft.com/l/chat/19:chat-falcon", "sensitivity": "normal",
        "summary": "Mia's team takes the solution to live; Omar to confirm the date.", "type": "action",
        "ask": "Confirm the go-live date", "due": "2026-10-20", "owners": ["you"],
        "items": [{"type": "action", "text": "Confirm the go-live date", "owner": "Omar Ali", "due": "2026-10-20"}]}


class Reworded(unittest.TestCase):
    """(d) a dismissed From row stays gone for a light reword of its item and comes back for a different wording of the ask."""

    def setUp(self):
        self.v = vip_vault()
        stage(self.v, [item("Send the SOW to Mia by Friday", src("[ABC] SOW", "https://x/1"))])
        rid = rows(self.v, "proposal")[0]["id"]
        py(self.v, f"print(json.dumps(sweep.vip_dismiss({{{rid!r}}})))")
        self.assertEqual(rows(self.v), [])

    def tearDown(self):
        self.v.cleanup()

    def test_a_light_reword_stays_gone_and_a_synonym_reword_comes_back(self):
        stage(self.v, [item("Send the SOW to Mia on Friday", src("RE: [ABC] SOW", "https://x/7", sent="2026-10-09 14:00"))],
              now="2026-10-09 15:10")
        self.assertEqual(rows(self.v), [], "a light reword of a dismissed item is the same item")
        stage(self.v, [item("Share the statement of work with Mia", src("RE: [ABC] SOW", "https://x/8", sent="2026-10-09 14:30"))],
              now="2026-10-09 15:20")
        got = rows(self.v, "proposal")
        self.assertEqual(len(got), 1, "a different wording of the ask is a new item")
        self.assertIsNone(got[0]["seen"])


class Cards(unittest.TestCase):
    """(d) the conversation cards: a whole-card Dismiss stays dismissed through a re-mention (the defect this test found)."""

    def setUp(self):
        self.v = vip_vault()
        record(self.v, [CHAT])
        self.cid = vip_file(self.v)["alerts"][0]["id"]

    def tearDown(self):
        self.v.cleanup()

    def rec(self, **change):
        record(self.v, [{**CHAT, **change}])
        return card(self.v, self.cid)

    def test_a_dismissed_card_stays_dismissed_when_the_thread_only_carries_on(self):
        py(self.v, f"print(json.dumps(sweep.vip_dismiss({{{self.cid!r}}})))")
        a = self.rec(last="2026-10-08 09:05", summary="Mia says thanks; the date is still to confirm.")
        self.assertTrue(a["seen"], "a later message that raises nothing new brought the dismissed card back")
        a = self.rec(last="2026-10-08 09:20")                                  # the same ask and items, said again
        self.assertTrue(a["seen"])

    def test_a_new_risk_brings_it_back_as_new(self):
        py(self.v, f"print(json.dumps(sweep.vip_dismiss({{{self.cid!r}}})))")
        a = self.rec(last="2026-10-08 09:05", items=CHAT["items"] + [{"type": "risk", "text": "Test licences may not arrive"}])
        self.assertFalse(a["seen"])

    def test_a_new_ask_of_a_different_kind_brings_it_back(self):
        py(self.v, f"print(json.dumps(sweep.vip_handled({{{self.cid!r}}})))")
        a = self.rec(last="2026-10-08 09:05", type="decision", ask="Decide who signs off the plan")
        self.assertFalse(a["seen"])
        self.assertEqual(a["state"], "open")

    def test_a_private_conversation_stays_dismissed(self):
        priv = {**CHAT, "conversation": "19:chat-private@thread.v2", "link": "https://teams.microsoft.com/l/chat/19:p",
                "sensitivity": "private", "title": "Personal"}
        record(self.v, [priv])
        pid = next(a["id"] for a in vip_file(self.v)["alerts"] if a.get("marker") == "private")
        py(self.v, f"print(json.dumps(sweep.vip_dismiss({{{pid!r}}})))")
        record(self.v, [{**priv, "last": "2026-10-08 09:30"}])
        self.assertTrue(card(self.v, pid)["seen"])


class Dropped(unittest.TestCase):
    """(c) the recorded-but-missed bug found: an item the sweep read in a conversation Today already summarised was skipped
    ("summarised on Today") even when the card did not list it, so it reached neither the card nor Review."""

    def setUp(self):
        self.v = vip_vault()
        record(self.v, [CHAT])
        self.link = CHAT["link"]

    def tearDown(self):
        self.v.cleanup()

    def teams(self, text, **more):
        return item(text, src("Falcon go-live", self.link, kind="Teams", sent="2026-10-08 08:00"), **more)

    def test_an_item_the_card_lists_stays_on_the_card(self):
        out = stage(self.v, [self.teams("Confirm go-live date")], now="2026-10-08 09:30")
        self.assertIn("summarised on Today", out)
        self.assertEqual(rows(self.v), [])

    def test_an_item_the_card_does_not_list_is_staged_and_shown(self):
        out = stage(self.v, [self.teams("Confirm go-live date"), self.teams("Order the extra test licences")], now="2026-10-08 09:30")
        self.assertIn("Sweep: 1 item", out)
        got = rows(self.v, "proposal")
        self.assertEqual([(r["who"], r["title"], [x["tag"] for x in r["refs"]]) for r in got], [("Mia Hale", "Falcon go-live", ["action"])])

    def test_a_private_conversation_still_keeps_its_whole_thread_out(self):
        priv = {**CHAT, "conversation": "19:chat-private@thread.v2", "link": "https://x/private2", "sensitivity": "private", "title": "Personal"}
        record(self.v, [priv])
        out = stage(self.v, [item("Book the thing", src("Personal", "https://x/private2", kind="Teams", sent="2026-10-08 08:00"))], now="2026-10-08 09:30")
        self.assertIn("private thread", out)                                   # and now by the closed-thread rule, whatever the card lists
        self.assertEqual(rows(self.v), [])


class PrivateThreads(unittest.TestCase):
    """(e) a proposal from a private conversation's thread is its title and times only (no summary, no project, no words)."""

    def test_the_row_takes_the_cards_neutral_title_and_no_project(self):
        v = vip_vault()
        try:
            priv = {**CHAT, "conversation": "19:chat-private@thread.v2", "link": "https://x/private", "sensitivity": "private",
                    "title": "Personal", "kind": "mail"}
            v.propose("earlier", [{"n": 1, "op": "new", "table": "actions", "match": "strong", "flags": [], "decision": "pending",   # staged before the thread was marked
                                   "values": {"project": "ABC", "description": "Book the thing", "owner": "Alan Carter",
                                              "source": src("A secret subject", "https://x/private", sent="2026-10-09 12:00")}}])
            record(v, [priv])
            got = rows(v, "proposal")
            self.assertEqual(len(got), 1, got)
            self.assertEqual((got[0]["marker"], got[0]["title"], got[0]["p"]), ("private", "Mia Hale, Omar Ali", None))
            self.assertNotIn("secret", json.dumps(got))
        finally:
            v.cleanup()


MAILCONF = {**CHAT, "kind": "mail", "conversation": "AAQk-conf-mail", "title": "Pay review", "link": "https://outlook.example/conf1",
            "sensitivity": "confidential", "last": "2026-10-08 08:25", "summary": "Mia raised the pay review.",
            "items": [{"type": "action", "text": "Prepare the pay review", "owner": "Omar Ali"}]}
CONF_SPELLINGS = ["confidential", "Confidential", "CONFIDENTIAL", " confidential ", "Confidential\n"]
PRIVATE_SPELLINGS = ["private", "Private", "PRIVATE", "personal", "Personal", " private "]
PREFIXES = ["RE: ", "Re: ", "re:", "FW: ", "Fw: ", "Fwd: ", "FWD:", "AW: ", "RE[2]: ", "Re(3): ", "RE: RE: FW: ", "Re: Fwd: AW: ", "[EXT] RE: ",
            "RE : "]


def pending_files(v):
    return sorted((v.root / "system/staging").glob("proposed-*-sweep*.json"))


class ConfidentialThreads(unittest.TestCase):
    """HIGH (Stark's review of #236): an item from a confidential (or private) thread of a followed person never reaches Review
    without its label. Main stages nothing from such a thread (the card was "summarised"); #236 stages what a card does not list,
    and must not do it for a thread marked confidential or private: the sweep's rule is that a VIP's confidential thread is alerted
    with its marker and its content is not read into proposals (cx-sweep, VIP section). So nothing is staged, in every spelling
    of the marker and with any subject prefix, and nothing of the item is echoed in the sweep's output."""

    def setUp(self):
        self.v = vip_vault()

    def tearDown(self):
        self.v.cleanup()

    def staged(self, subject, link="https://outlook.example/conf1", kind="Email", text="Book the catering for the offsite", **more):
        return stage(self.v, [item(text, src(subject, link, kind=kind, sent="2026-10-08 08:00"), **more)], now="2026-10-08 09:30")

    def test_every_spelling_of_the_marker_stages_nothing_for_a_card_that_does_not_list_the_item(self):
        for n, spelling in enumerate(CONF_SPELLINGS + PRIVATE_SPELLINGS):
            with self.subTest(spelling=spelling):
                link = f"https://outlook.example/c{n}"
                record(self.v, [{**MAILCONF, "conversation": f"AAQk-{n}", "link": link, "sensitivity": spelling}])
                out = self.staged("Pay review", link=link, text=f"Book the catering for the offsite {n}")
                self.assertIn("Sweep: 0 items", out)
                self.assertNotIn("catering", out)                        # the sweep's output does not echo it
                self.assertEqual(pending_files(self.v), [])
                self.assertEqual(rows(self.v), [])

    def test_the_card_that_lists_the_item_stages_nothing_either(self):
        record(self.v, [MAILCONF])
        out = self.staged("Pay review", text="Prepare the pay review")
        self.assertIn("Sweep: 0 items", out)
        self.assertEqual(pending_files(self.v), [])

    def test_a_teams_chat_and_a_match_by_the_conversation_id_alone(self):
        record(self.v, [{**CONF, "last": "2026-10-08 08:25"}])
        out = stage(self.v, [{**item("Book the catering for the offsite", src("Another title", "https://x/other", kind="Teams")),
                              "conversation": CONF["conversation"]}], now="2026-10-08 09:30")
        self.assertIn("Sweep: 0 items", out)
        self.assertEqual(pending_files(self.v), [])

    def test_a_reply_prefix_on_the_subject_still_finds_the_thread(self):
        record(self.v, [MAILCONF])
        for prefix in PREFIXES:
            with self.subTest(prefix=prefix):
                out = self.staged(prefix + "Pay review", link="https://outlook.example/other-" + str(abs(hash(prefix))))
                self.assertIn("Sweep: 0 items", out)
                self.assertEqual(pending_files(self.v), [])

    def test_a_normal_thread_with_a_card_still_stages_what_the_card_does_not_list(self):
        record(self.v, [{**MAILCONF, "sensitivity": "normal"}])
        out = self.staged("Pay review", text="Book the catering for the offsite")
        self.assertIn("Sweep: 1 item", out)                                          # #236's own fix is intact

    def test_a_spec_item_that_carries_the_marker_is_not_staged(self):
        spec = item("Book the catering for the offsite", src("Anything", "https://outlook.example/none", sent="2026-10-08 08:00"))
        out = stage(self.v, [{**spec, "sensitivity": "Confidential"}], now="2026-10-08 09:30")
        self.assertIn("Sweep: 0 items", out)
        self.assertEqual(pending_files(self.v), [])

    def test_an_update_from_a_confidential_thread_is_not_staged_either(self):
        record(self.v, [MAILCONF])
        self.v.propose("seed", [{"n": 1, "op": "new", "table": "decisions", "match": "strong", "flags": [], "decision": "approved",
                                 "values": {"project": "ABC", "decision": "Pick the vendor", "status": "Pending", "made_by": "Mia Hale",
                                           "source": "Alan (cx-edit)"}}])
        self.v.run("apply")
        f = self.v.root / "system/staging/drafts/u.json"
        f.write_text(json.dumps({"items": [{"op": "update", "table": "decisions", "id": "ABC-D-001", "why": "Mia confirmed it",
                       "set": {"status": "Made"}, "source": src("RE: Pay review", "https://outlook.example/conf1", sent="2026-10-08 08:00")}]}))
        out = run(self.v, "sweep.py", "stage", str(f), now="2026-10-08 09:30").stdout
        self.assertIn("Sweep: 0 items", out)

    def test_a_proposal_staged_before_the_thread_was_marked_shows_the_mark_and_no_item_words(self):
        for n, prefix in enumerate(["", "RE: ", "Re: ", "FW: ", "Fwd: ", "AW: ", "RE[2]: ", "RE: RE: "]):
            stage(self.v, [item(f"Order letters {n}", src(prefix + "Pay review", f"https://outlook.example/p{n}", sent="2026-10-08 08:00"))],
                  now="2026-10-08 09:00")
        record(self.v, [MAILCONF])
        got = rows(self.v, "proposal")
        self.assertEqual(len(got), 1, got)                                           # one thread, whatever the prefix
        self.assertEqual((got[0]["marker"], got[0]["title"]), ("confidential", "Pay review"))

    def test_a_row_for_a_prefixed_subject_is_marked_whichever_the_prefix(self):
        record(self.v, [MAILCONF])
        for prefix in PREFIXES:
            with self.subTest(prefix=prefix):
                # staged directly as a proposal (as an earlier sweep would have), so the stage-time check is not what is tested
                path = self.v.propose("earlier", [{"n": 1, "op": "new", "table": "actions", "match": "strong", "flags": [], "decision": "pending",
                                                   "values": {"project": "ABC", "description": "Order letters", "owner": "Alan Carter",
                                                              "source": src(prefix + "Pay review", "https://outlook.example/z", sent="2026-10-08 08:00")}}])
                try:
                    got = rows(self.v, "proposal")
                    self.assertEqual([(r["marker"], r["title"]) for r in got], [("confidential", "Pay review")])
                finally:
                    path.unlink()


TODAY = date.today().isoformat()
YESTERDAY = date.fromordinal(date.today().toordinal() - 1).isoformat()
STAMP = f"{TODAY} 12:00"
PRIVATE = {**CHAT, "conversation": "19:chat-private@thread.v2", "title": "Personal", "link": "https://teams.microsoft.com/l/chat/19:p",
           "sensitivity": "private", "last": f"{TODAY} 08:20", "summary": "SECRET WORDS", "items": [{"type": "action", "text": "SECRET ITEM"}]}
CONF = {**CHAT, "conversation": "19:chat-conf@thread.v2", "title": "Pay review", "link": "https://teams.microsoft.com/l/chat/19:c",
        "sensitivity": "confidential", "last": f"{TODAY} 08:25", "summary": "Mia raised the pay review.",
        "items": [{"type": "action", "text": "Prepare the pay review", "owner": "Omar Ali"}]}
LIVE = {**CHAT, "last": f"{TODAY} 08:40"}
HELLO = {"kind": "teams", "conversation": "19:chat-hello@thread.v2", "title": "Quick hello", "from": MIA, "people": [MIA, OMAR],
         "last": f"{TODAY} 08:15", "link": "https://teams.microsoft.com/l/chat/19:hello", "sensitivity": "normal",
         "summary": "Greetings only.", "items": []}
ANSWERED = {**CHAT, "conversation": "19:chat-answered@thread.v2", "title": "Answered chat", "link": "https://teams.microsoft.com/l/chat/19:a",
            "last": f"{TODAY} 07:30", "replied": f"{TODAY} 07:45", "type": "action", "ask": "Send the plan", "items": []}
DISMISSED = {**CHAT, "conversation": "19:chat-gone@thread.v2", "title": "Dismissed chat", "link": "https://teams.microsoft.com/l/chat/19:d",
             "last": f"{TODAY} 08:05"}
MESSAGE = {"kind": "mail", "from": MIA, "subject": "[ABC] Licence count", "sent": f"{TODAY} 08:30", "link": "https://x/m2",
           "gist": "Wants the licence count."}
OLDQUIET = {**HELLO, "conversation": "19:chat-old@thread.v2", "title": "Yesterday's greeting", "link": "https://teams.microsoft.com/l/chat/19:o",
            "last": f"{YESTERDAY} 08:15"}


def rec_at(v, found, when=STAMP):
    f = v.root / "system/staging/drafts/found.json"
    f.write_text(json.dumps(found))
    return run(v, "sweep.py", "vip", "record", str(f), "--found", "sweep", now=when).stdout


def fixture(v):
    """Mia is followed. Every kind of thing the sweep records, plus two proposals and a memory note from her mail."""
    populate(v)
    (v.root / "projects/_portfolio/people-register.md").write_text(REGISTER, encoding="utf-8")
    (v.root / "system/staging/drafts").mkdir(parents=True, exist_ok=True)
    rec_at(v, [LIVE, HELLO, PRIVATE, CONF, ANSWERED, DISMISSED, MESSAGE])
    rec_at(v, [OLDQUIET], when=f"{YESTERDAY} 12:00")
    gone = next(a["id"] for a in vip_file(v)["alerts"] if a.get("title") == "Dismissed chat")
    py(v, f"print(json.dumps(sweep.vip_dismiss({{{gone!r}}})))", now=STAMP)
    stage(v, [item("Send the SOW", src("[ABC] SOW", "https://x/1", sent=f"{TODAY} 08:00")),
              item("Test licences may not arrive", src("[ABC] SOW", "https://x/2", sent=f"{TODAY} 08:10"), table="raid", type="Risk")], now=STAMP)
    stage_note(v, src("[ABC] SOW", "https://x/9", sent=f"{TODAY} 08:20"))
    v.propose("earlier-conf", [{"n": 1, "op": "new", "table": "actions", "match": "strong", "flags": [], "decision": "pending",    # staged before the thread was marked
                                "values": {"project": "ABC", "description": "Order the pay letters", "owner": "Alan Carter",
                                           "source": src("RE: Pay review", CONF["link"], kind="Teams", sent=f"{TODAY} 08:30")}}])
    run(v, "build_dashboard.py", now=STAMP)


class Page(LiveBrowserCase):
    """Today's rows in a real browser: (a) and (b) the From rows and where they go, (c) nothing recorded is missed, (e) a private
    conversation is its title and times, (f) the counts, (g) no label; (d) dismiss, re-mention, change."""
    shared_server = True

    @classmethod
    def load(cls, v):
        fixture(v)

    def setUp(self):
        super().setUp()
        self.b.eval("go('today'); EXPAND.add('td'); EXPAND.add('attn'); renderToday()")
        self.b.wait("document.querySelector('#tdList li') && document.querySelector('#attnList li.alrow')")

    def rows(self):
        """Today's followed-person rows in both places: Needs attention (where: attn; #236) and Messages (where: td)."""
        return self.b.eval(r"""[...document.querySelectorAll('#attnList > li.alrow, #tdList > li')].map(l=>({where:l.closest('#attnList')?'attn':'td',
          key:l.dataset.td||'al'+l.dataset.al, kind:l.className, text:l.textContent.replace(/\s+/g,' ').trim().replace(/^\d+(?=\D)/,''),
          btns:[...l.querySelectorAll('button')].map(x=>x.getAttribute('aria-label')||''),
          title:(l.querySelector('a.t')||l.querySelector('.t')||{}).textContent||''}))""")

    def test_a_the_proposal_and_b_the_note_are_from_rows_that_go_to_review(self):
        b = self.b
        got = {r["key"]: r for r in self.rows()}
        prop = next(r for r in got.values() if r["text"].startswith("From Mia Hale: [ABC] SOW") and "proposals" in r["text"])
        note = next(r for r in got.values() if r["text"].startswith("From Mia Hale: [ABC] SOW") and "memory" in r["text"])
        self.assertIn("2 proposals in Review", prop["text"])
        self.assertIn("Send the SOW", prop["text"])
        self.assertIn("Risk", prop["text"])
        self.assertIn("A note for", note["text"])
        self.assertIn("memory", note["text"])
        for r in (prop, note):
            self.assertEqual(r["where"], "attn")                                      # Needs attention, not Messages
            self.assertTrue(any(x.startswith("Open in Review") for x in r["btns"]), r["btns"])
            self.assertTrue(any(x.startswith("Dismiss") for x in r["btns"]), r["btns"])
        b.click(f'#attnList li[data-al="{prop["key"][2:]}"] a.t')                        # the title goes to the proposal, highlighted
        b.wait("!document.getElementById('v-review').hidden")
        self.assertTrue(b.eval("RHL.size>0"))
        self.assertTrue(b.eval("REV.filter(r=>RHL.has(r.n)).every(r=>!r.done)"))

    def test_c_every_unseen_recorded_message_has_a_row(self):
        """None is silently dropped: each unseen alert in vip.json shows, as a card, a quiet line or a Replied line."""
        unseen = [a for a in self.b.eval("D.sweep_alerts.vip.alerts") if not a.get("seen")]                # what the page was given, new rows included
        self.assertGreaterEqual(len(unseen), 8)
        unseen = [a for a in unseen if a.get("title") != "Yesterday's greeting"]               # a quiet line is for the day it was updated (BL-334)
        shown = {r["key"] for r in self.rows()}
        missing = [(a.get("title") or a.get("subject"), a.get("updated"), a.get("state")) for a in unseen if "al" + a["id"] not in shown]
        self.assertEqual(missing, [], "recorded but not on Today")

    def test_d_dismissed_stays_out_and_in_the_file(self):
        shown = {r["title"] for r in self.rows()}
        self.assertNotIn("Dismissed chat", shown)
        self.assertTrue(next(a for a in vip_file(self.v)["alerts"] if a.get("title") == "Dismissed chat")["seen"])

    def test_e_a_private_conversation_is_its_title_and_times_only(self):
        r = next(x for x in self.rows() if x["title"] == "Mia Hale, Omar Ali")
        self.assertRegex(r["text"], r"^Mia Hale, Omar Aliupdated \d\d:\d\d$")
        for word in ("private", "Private", "SECRET", "From", "follow", "Message", "Teams", "no project"):
            self.assertNotIn(word, r["text"])
        self.assertEqual(r["btns"], ["Dismiss: Mia Hale, Omar Ali"])
        self.assertNotIn("Mia", " ".join(r["btns"]).replace("Mia Hale, Omar Ali", ""))

    def test_f_the_counts_and_the_badge_include_the_new_rows(self):
        b = self.b
        o = b.eval("""(()=>{ const attn=a=>a.kind==='proposal'||a.kind==='note'||a.marker==='private'; return {vips:VIPS().length, moved:VIPS().filter(attn).length, cards:VIPS().filter(a=>!attn(a)).length,
          nAttn:document.getElementById('nAttn').textContent, attn:document.querySelectorAll('#attnList > li:not(:has(.none))').length,
          alrows:document.querySelectorAll('#attnList > li.alrow').length, nTd:document.getElementById('nTd').textContent,
          badge:document.getElementById('vipBadge')?document.getElementById('vipBadge').getAttribute('aria-label'):null,
          quiet:document.querySelectorAll('#tdList > li.td-quiet').length,
          all:document.querySelectorAll('#tdList > li').length, tdMoved:document.querySelectorAll('#tdList > li[data-td^="alfp"]').length}; })()""")
        self.assertEqual(o["moved"], 4)                                          # the proposal row, the note row, the confidential thread's row and the private conversation
        self.assertEqual(o["alrows"], 4)
        self.assertEqual(o["nAttn"], str(o["attn"]))                             # the heading's count includes them
        self.assertEqual(o["tdMoved"], 0)                                        # and none is also in Messages
        self.assertEqual(o["nTd"], str(o["all"] - o["quiet"]))                   # Messages counts only its cards (#245: the Intake line has its own counts)
        self.assertGreaterEqual(o["all"], o["cards"])
        self.assertEqual(o["badge"], f"{o['vips']} items to see first")          # the left bar counts everything unseen; a From row is not a message

    def test_h_the_from_rows_come_after_the_existing_attention_items(self):
        """Stark's review: they led the list. The help says decisions, reminders, the gaps line, then the From rows."""
        order = self.b.eval("[...document.querySelectorAll('#attnList > li')].map(l=>l.classList.contains('alrow'))")
        self.assertIn(True, order)
        self.assertIn(False, order, "the fixture has other attention items")
        self.assertEqual(order, sorted(order), order)                                # every other row, then every From row

    def test_i_a_confidential_threads_row_is_marked_and_shows_no_item_words(self):
        r = next(x for x in self.rows() if x["where"] == "attn" and "Pay review" in x["text"])
        self.assertIn("Confidential", r["text"])
        self.assertIn("From Mia Hale: Pay review", r["text"])                         # the prefix is gone from the title, the mark is kept
        self.assertNotIn("Order the pay letters", r["text"])
        self.assertNotIn("RE:", r["text"])

    def test_g_no_label_anywhere_in_the_section(self):
        html = self.b.eval("document.getElementById('tdSec').outerHTML+document.getElementById('attnSec').outerHTML")
        self.assertIsNone(says_vip(html))
        self.assertIsNone(WORD.search(self.b.eval("[...document.querySelectorAll('#tdSec [aria-label],#tdSec [data-tip],#attnSec [aria-label],#attnSec [data-tip]')].map(e=>(e.getAttribute('aria-label')||'')+' '+(e.dataset.tip||'')).join(' ')")))


class Dismiss(LiveBrowserCase):
    """(d) in the page: Dismiss takes a From row away with Undo; a re-sweep that mentions it again leaves it gone; a new risk in the
    thread brings it back, as new."""

    @classmethod
    def load(cls, v):
        fixture(v)

    def row(self, text):
        return self.b.eval(f"""(()=>{{ const l=[...document.querySelectorAll('#attnList > li.alrow')].find(x=>x.textContent.includes({json.dumps(text)}));
          return l?l.dataset.al:null; }})()""")

    def refresh(self):
        run(self.v, "build_dashboard.py", now=STAMP)
        self.b.eval("EXPAND.add('td'); EXPAND.add('attn'); reloadData().then(()=>renderToday())")
        self.b.pump(1.5)

    def test_dismiss_stay_gone_come_back(self):
        b = self.b
        b.eval("go('today'); EXPAND.add('td'); EXPAND.add('attn'); renderToday()")
        rid = self.row("2 proposals in Review")
        self.assertTrue(rid)
        b.click(f'#attnList [data-alertdo="dismiss"][data-id="{rid}"]')
        b.wait(f"!document.querySelector('#attnList li[data-al=\"{rid}\"]')")
        self.assertTrue(next(a for a in vip_file(self.v)["alerts"] if a["id"] == rid)["seen"])
        b.click("#snackU")                                                                   # Undo puts it back
        b.wait(f"document.querySelector('#attnList li[data-al=\"{rid}\"]')")
        b.click(f'#attnList [data-alertdo="dismiss"][data-id="{rid}"]')
        b.wait(f"!document.querySelector('#attnList li[data-al=\"{rid}\"]')")
        stage(self.v, [item("Send the SOW", src("RE: [ABC] SOW", "https://x/4", sent=f"{TODAY} 11:00"))], now=STAMP)   # asked again
        self.refresh()
        self.assertIsNone(self.row("2 proposals in Review"))
        self.assertIsNone(self.row("proposals in Review"))
        stage(self.v, [item("Book the UAT environment", src("RE: [ABC] SOW", "https://x/5", sent=f"{TODAY} 11:30"))], now=STAMP)   # a new action
        self.refresh()
        self.assertTrue(self.row("new since you dismissed it"), self.b.eval("[...document.querySelectorAll('#attnList > li')].map(l=>l.textContent)"))
        self.assertIn("proposals in Review", self.b.eval("document.querySelector('#attnList li[data-al=\"" + rid + "\"]').textContent"))


if __name__ == "__main__":
    unittest.main()
