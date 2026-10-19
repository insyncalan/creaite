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
        self.assertIn("summarised on Today", out)
        self.assertEqual(rows(self.v), [])


class PrivateThreads(unittest.TestCase):
    """(e) a proposal from a private conversation's thread is its title and times only (no summary, no project, no words)."""

    def test_the_row_takes_the_cards_neutral_title_and_no_project(self):
        v = vip_vault()
        try:
            priv = {**CHAT, "conversation": "19:chat-private@thread.v2", "link": "https://x/private", "sensitivity": "private",
                    "title": "Personal", "kind": "mail"}
            record(v, [priv])
            stage(v, [item("Book the thing", src("A secret subject", "https://x/private", sent="2026-10-09 12:00"))])
            got = rows(v, "proposal")
            self.assertEqual(len(got), 1, got)
            self.assertEqual((got[0]["marker"], got[0]["title"], got[0]["p"]), ("private", "Mia Hale, Omar Ali", None))
            self.assertNotIn("secret", json.dumps(got))
        finally:
            v.cleanup()


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
        self.b.eval("go('today'); EXPAND.add('td'); renderToday()")
        self.b.wait("document.querySelector('#tdList li')")

    def rows(self):
        return self.b.eval(r"""[...document.querySelectorAll('#tdList > li')].map(l=>({key:l.dataset.td, kind:l.className,
          text:l.textContent.replace(/\s+/g,' ').trim(), btns:[...l.querySelectorAll('button')].map(x=>x.getAttribute('aria-label')||''),
          title:(l.querySelector('a.t')||l.querySelector('.t')||{}).textContent||''}))""")

    def test_a_the_proposal_and_b_the_note_are_from_rows_that_go_to_review(self):
        b = self.b
        got = {r["key"]: r for r in self.rows()}
        prop = next(r for r in got.values() if r["text"].startswith("ProposalFrom Mia Hale: [ABC] SOW"))
        note = next(r for r in got.values() if r["text"].startswith("NoteFrom Mia Hale: [ABC] SOW"))
        self.assertIn("2 proposals in Review", prop["text"])
        self.assertIn("Send the SOW", prop["text"])
        self.assertIn("Risk", prop["text"])
        self.assertIn("A note for", note["text"])
        self.assertIn("memory", note["text"])
        for r in (prop, note):
            self.assertTrue(any(x.startswith("Open in Review") for x in r["btns"]), r["btns"])
            self.assertTrue(any(x.startswith("Dismiss") for x in r["btns"]), r["btns"])
        b.click(f'#tdList li[data-td="{prop["key"]}"] a.t')                        # the title goes to the proposal, highlighted
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
        o = b.eval("""({rows:VIPS().length, followed:VIPS().filter(a=>a.kind==='proposal'||a.kind==='note').length,
          nTd:document.getElementById('nTd').textContent, badge:document.getElementById('vipBadge')?document.getElementById('vipBadge').getAttribute('aria-label'):null,
          tdNew:!document.getElementById('tdNew').hidden, quiet:document.querySelectorAll('#tdList > li.td-quiet').length,
          all:document.querySelectorAll('#tdList > li').length})""")
        self.assertEqual(o["followed"], 2)
        self.assertEqual(o["nTd"], str(o["all"] - o["quiet"] + 2 * 0 + b.eval("tdLine().reduce((a,x)=>a+x.n,0)")))
        self.assertTrue(o["tdNew"])
        self.assertEqual(o["badge"], f"{o['rows']} messages to see first")

    def test_g_no_label_anywhere_in_the_section(self):
        html = self.b.eval("document.getElementById('tdSec').outerHTML")
        self.assertIsNone(says_vip(html))
        self.assertIsNone(WORD.search(self.b.eval("[...document.querySelectorAll('#tdSec [aria-label],#tdSec [data-tip]')].map(e=>(e.getAttribute('aria-label')||'')+' '+(e.dataset.tip||'')).join(' ')")))


class Dismiss(LiveBrowserCase):
    """(d) in the page: Dismiss takes a From row away with Undo; a re-sweep that mentions it again leaves it gone; a new risk in the
    thread brings it back, as new."""

    @classmethod
    def load(cls, v):
        fixture(v)

    def row(self, text):
        return self.b.eval(f"""(()=>{{ const l=[...document.querySelectorAll('#tdList > li')].find(x=>x.textContent.includes({json.dumps(text)}));
          return l?l.dataset.td.slice(2):null; }})()""")

    def refresh(self):
        run(self.v, "build_dashboard.py", now=STAMP)
        self.b.eval("EXPAND.add('td'); reloadData().then(()=>renderToday())")
        self.b.pump(1.5)

    def test_dismiss_stay_gone_come_back(self):
        b = self.b
        b.eval("go('today'); EXPAND.add('td'); renderToday()")
        rid = self.row("2 proposals in Review")
        self.assertTrue(rid)
        b.click(f'#tdList [data-alertdo="dismiss"][data-id="{rid}"]')
        b.wait(f"!document.querySelector('#tdList li[data-td=\"al{rid}\"]')")
        self.assertTrue(next(a for a in vip_file(self.v)["alerts"] if a["id"] == rid)["seen"])
        b.click("#snackU")                                                                   # Undo puts it back
        b.wait(f"document.querySelector('#tdList li[data-td=\"al{rid}\"]')")
        b.click(f'#tdList [data-alertdo="dismiss"][data-id="{rid}"]')
        b.wait(f"!document.querySelector('#tdList li[data-td=\"al{rid}\"]')")
        stage(self.v, [item("Send the SOW", src("RE: [ABC] SOW", "https://x/4", sent=f"{TODAY} 11:00"))], now=STAMP)   # asked again
        self.refresh()
        self.assertIsNone(self.row("2 proposals in Review"))
        self.assertIsNone(self.row("proposals in Review"))
        stage(self.v, [item("Book the UAT environment", src("RE: [ABC] SOW", "https://x/5", sent=f"{TODAY} 11:30"))], now=STAMP)   # a new action
        self.refresh()
        self.assertTrue(self.row("new since you dismissed it"), self.b.eval("[...document.querySelectorAll('#tdList > li')].map(l=>l.textContent)"))
        self.assertIn("proposals in Review", self.b.eval("document.querySelector('#tdList li[data-td=\"al" + rid + "\"]').textContent"))


if __name__ == "__main__":
    unittest.main()
