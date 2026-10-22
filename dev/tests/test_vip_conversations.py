"""BL-334: alerts from people Alan follows read the conversation, not the message.

Run: python3 dev/tests/test_vip_conversations.py
A throwaway vault with fictional people and a stand-in Claude (never Microsoft 365). Covers each "Done when" point: a
three-message chat (greeting, commitment, decision) gives one card with one summary, one action and one decision, its
project matched from the chat's title; a greeting-only chat gives one quiet line with only Seen; a later message updates the
same card; Dismiss stages nothing and Create work item stages one proposal; a later sweep proposes nothing from a
conversation already summarised; vip.json holds no message text. Also: the check keeps its own read-only allow list, the wait
for quiet (at most 15 minutes), the title fallback, the project from the people, a private conversation's neutral line, and
no "VIP" in anything shown (BL-288).
"""
import json
import os
import re
import subprocess
import sys
import time
import unittest
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_live_server import free_port  # noqa: E402
from test_sweep_alerts import TZ, check_since, fast_checks, record, run, vip_file, vip_vault, zoned  # noqa: E402

TOOLS = ["mcp__claude_ai_Microsoft_365__outlook_email_search", "mcp__claude_ai_Microsoft_365__chat_message_search",
         "mcp__claude_ai_Microsoft_365__outlook_calendar_search", "mcp__claude_ai_Microsoft_365__read_resource"]
MIA = "Mia Hale <mia@client.example>"
OMAR = "Omar Ali <omar@company.example>"
SECRET = "SECRET MESSAGE TEXT"

CHAT = {"kind": "teams", "conversation": "19:chat-falcon@thread.v2", "title": "Project Falcon go-live",
        "from": MIA, "people": [MIA, OMAR], "last": "2026-10-08 08:40",
        "link": "https://teams.microsoft.com/l/chat/19:chat-falcon", "sensitivity": "normal", "attachments": [],
        "summary": "Mia's team will take the solution from production to live; go-live work falls under the existing contract (VIP).",
        "items": [{"type": "action", "text": "Take the solution from production to live", "owner": "Mia Hale", "due": "2026-10-20"},
                  {"type": "decision", "text": "Go-live work falls under the existing contract", "owner": None, "due": None}],
        "messages": [{"text": SECRET}], "body": SECRET}
HELLO = {"kind": "teams", "conversation": "19:chat-hello@thread.v2", "title": "Group chat", "from": MIA,
         "people": [MIA, OMAR], "last": "2026-10-08 08:20", "link": "https://teams.microsoft.com/l/chat/19:chat-hello",
         "sensitivity": "normal", "summary": "Greetings only.", "items": [], "body": SECRET}
LATER = {**CHAT, "last": "2026-10-08 09:05",
         "summary": "Mia's team takes it to live under the existing contract; Omar raised a risk on test licences.",
         "items": CHAT["items"] + [{"type": "risk", "text": "Test licences may not arrive before go-live", "owner": "Omar Ali"}]}

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


def vault():
    v = vip_vault()
    (v.root / "system/staging/drafts").mkdir(parents=True, exist_ok=True)
    return v


def proposals(v):
    return sorted(p.name for p in (v.root / "system/staging").glob("proposed-*.json"))


class ConversationServerTests(unittest.TestCase):
    """The live server's check with a stand-in Claude: one card per conversation, the quiet line, the update in place,
    Dismiss and Create work item on one candidate, and no message text kept."""

    @classmethod
    def setUpClass(cls):
        cls.v = v = vault()
        cfg = v.root / "system/config/settings.json"
        d = json.loads(cfg.read_text())
        d.setdefault("vip", {})["check_minutes"] = 0.02                                   # every ~1 s
        cfg.write_text(json.dumps(d, indent=2))
        fast_checks(v)
        (v.root / "vip-replies.json").write_text(json.dumps([zoned([CHAT, HELLO]), zoned([CHAT, HELLO]), zoned([LATER, HELLO])]))
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

    def wait_for(self, test, what):
        for _ in range(150):
            got = self.post("/api/vip", {})
            if test(got):
                return got
            time.sleep(0.1)
        self.fail(f"never {what}: {got}")

    def test_1_the_check_reads_conversations_with_its_own_read_only_tools(self):
        self.wait_for(lambda g: len(g["alerts"]) == 2, "two conversations")
        args = json.loads((self.v.root / "vip-call-1.json").read_text())
        self.assertEqual(args[args.index("--allowedTools") + 1].split(","), TOOLS)          # unchanged allow list
        prompt = args[args.index("--") + 1]
        self.assertEqual(args[-2:], ["--", prompt])                    # #91: the prompt last, after `--`, never an option
        self.assertIn("one object per conversation", prompt)
        self.assertIn("everyone's messages", prompt)
        self.assertIn("Never use the word VIP in a gist, a summary, an item or anywhere in the reply", prompt)

    def test_2_one_card_one_summary_an_action_and_a_decision_matched_from_the_title(self):
        got = self.wait_for(lambda g: len(g["alerts"]) == 2, "two conversations")
        card = next(a for a in got["alerts"] if not a.get("quiet"))
        self.assertEqual(card["title"], "Project Falcon go-live")
        self.assertEqual(card["p"], "ABC")                                                   # from the chat's title
        self.assertTrue(card["summary"].startswith("Mia's team will take the solution"))
        self.assertNotIn("VIP", card["summary"])                                             # BL-288
        self.assertLessEqual(len(card["summary"]), 300)
        self.assertEqual([(c["n"], c["type"]) for c in card["candidates"]][:2], [(1, "action"), (2, "decision")])   # (+ a later risk)
        self.assertEqual(card["candidates"][0]["owner"], "Mia Hale")
        self.assertEqual(card["candidates"][0]["due"], "2026-10-20")
        quiet = next(a for a in got["alerts"] if a.get("quiet"))
        self.assertEqual(quiet["title"], "Mia Hale, Omar Ali")                         # never "Group chat"
        self.assertEqual(quiet["candidates"], [])

    def test_3_a_later_message_updates_the_same_card(self):
        first = self.wait_for(lambda g: len(g["alerts"]) == 2, "two conversations")
        card_id = next(a["id"] for a in first["alerts"] if not a.get("quiet"))
        got = self.wait_for(lambda g: any(len(a.get("candidates") or []) == 3 for a in g["alerts"]), "the update")
        self.assertEqual(len(got["alerts"]), 2)                                              # no new card
        card = next(a for a in got["alerts"] if not a.get("quiet"))
        self.assertEqual(card["id"], card_id)
        self.assertEqual(card["last"], "2026-10-08 09:05")
        self.assertEqual(card["updated"], "2026-10-08 09:30")
        self.assertEqual(card["candidates"][2]["type"], "risk")

    def test_4_dismiss_stages_nothing_and_create_work_item_stages_one_proposal(self):
        got = self.wait_for(lambda g: any(len(a.get("candidates") or []) == 3 for a in g["alerts"]), "the update")
        card = next(a for a in got["alerts"] if not a.get("quiet"))
        before = proposals(self.v)
        r = self.post("/api/alerts/dismiss", {"ids": [card["id"]], "cand": 1})
        self.assertTrue(r["ok"], r)
        self.assertEqual(proposals(self.v), before)                                          # Dismiss: nothing staged
        pre = self.post("/api/alerts/prefill", {"id": card["id"], "cand": 2})["prefill"]
        self.assertEqual((pre["type"], pre["table"], pre["project"]), ("decision", "decisions", "ABC"))
        self.assertEqual(pre["values"]["decision"], "Go-live work falls under the existing contract")
        made = self.post("/api/alerts/make", {"id": card["id"], "cand": 2, "values": {}})
        self.assertTrue(made["ok"], made)
        after = proposals(self.v)
        self.assertEqual(len(after), len(before) + 1)                                        # one proposal
        spec = json.loads((self.v.root / "system/staging" / made["proposal"]).read_text())
        self.assertEqual(len(spec["items"]), 1)
        self.assertEqual((spec["items"][0]["table"], spec["items"][0]["decision"]), ("decisions", "pending"))   # for Review (check 45)
        self.assertIn("Chat: Project Falcon go-live", spec["items"][0]["values"]["source"])
        st = vip_file(self.v)
        card = next(a for a in st["alerts"] if a["id"] == card["id"])
        self.assertTrue(card["candidates"][0]["dismissed"])
        self.assertEqual(card["candidates"][1]["made"]["proposal"], made["proposal"])
        self.assertIsNone(card["seen"])                                                      # the risk still waits
        r = self.post("/api/alerts/dismiss", {"ids": [card["id"]], "cand": 3})
        self.assertIsNotNone(next(a for a in vip_file(self.v)["alerts"] if a["id"] == card["id"])["seen"])   # all settled
        self.assertEqual(len(proposals(self.v)), len(before) + 1)
        u = self.post("/api/alerts/undo", {"ids": [card["id"]], "cand": 3})
        self.assertEqual(u["restored"], 1)
        back = next(a for a in vip_file(self.v)["alerts"] if a["id"] == card["id"])
        self.assertIsNone(back["seen"])
        self.assertNotIn("dismissed", back["candidates"][2])
        (self.v.root / "system/staging" / made["proposal"]).unlink()                         # the page's Undo: unstaged first
        u = self.post("/api/alerts/undo", {"ids": [card["id"]], "cand": 2})
        self.assertEqual(u["restored"], 1)                                                   # then the item is back on the card
        self.assertNotIn("made", next(a for a in vip_file(self.v)["alerts"] if a["id"] == card["id"])["candidates"][1])

    def test_5_no_message_text_and_no_label(self):
        self.wait_for(lambda g: len(g["alerts"]) == 2, "two conversations")
        text = (self.v.root / "system/staging/vip.json").read_text()
        self.assertNotIn(SECRET, text)                                                       # vip.json: no message text
        self.assertNotIn("messages", json.loads(text)["alerts"][0])
        for body in self.said:
            self.assertNotIn("VIP", body)                                                    # BL-288


class ConversationRecordTests(unittest.TestCase):
    """The record itself (sweep.py vip record): the wait for quiet, the title and project rules, a private conversation,
    and the sweep's skip for a summarised conversation."""

    def setUp(self):
        self.v = vault()

    def tearDown(self):
        self.v.cleanup()

    def record_at(self, found, now, how="check"):
        f = self.v.root / "system/staging/drafts/found.json"
        f.write_text(json.dumps(found))
        return run(self.v, "sweep.py", "vip", "record", str(f), "--found", how, now=now).stdout

    def test_a_conversation_still_going_is_waited_for_at_most_15_minutes(self):
        talk = {**CHAT, "last": "2026-10-08 09:25"}
        self.record_at([talk], "2026-10-08 09:30")
        st = vip_file(self.v)
        self.assertEqual(st["alerts"], [])                                                   # 5 minutes old: waited for
        self.assertTrue(st["held"])
        self.assertIsNone(st.get("last_check"))                                              # not past the conversation
        self.record_at([talk], "2026-10-08 09:38")
        self.assertEqual(vip_file(self.v)["alerts"], [])                                     # 13 minutes: still waiting
        self.record_at([{**talk, "last": "2026-10-08 09:44"}], "2026-10-08 09:46")           # carries on, but waited 16 min
        st = vip_file(self.v)
        self.assertEqual(len(st["alerts"]), 1)
        self.assertNotIn("held", st)
        self.assertEqual(st["last_check"], "2026-10-08 09:46")

    def test_the_sweep_records_at_once_and_titles_fall_back_to_the_people(self):
        self.record_at([{**HELLO, "title": None, "last": "2026-10-08 09:29"}], "2026-10-08 09:30", how="sweep")
        a = vip_file(self.v)["alerts"][0]
        self.assertEqual(a["title"], "Mia Hale, Omar Ali")
        self.assertTrue(a["quiet"])

    def test_the_project_from_the_people_when_the_title_names_none(self):
        chat = {**CHAT, "conversation": "19:x", "title": "Quick sync", "summary": "Agreed the next step.",
                "people": ["Pat Lee <pat@client.com>", MIA], "items": [{"type": "action", "text": "Send the next step"}]}
        self.record_at([chat], "2026-10-08 09:30", how="sweep")
        self.assertEqual(vip_file(self.v)["alerts"][0]["p"], "ABC")                         # client.com is ABC's domain

    def test_a_private_conversation_keeps_only_a_neutral_line(self):
        self.record_at([{**CHAT, "sensitivity": "private"}], "2026-10-08 09:30", how="sweep")
        a = vip_file(self.v)["alerts"][0]
        self.assertEqual((a["summary"], a["candidates"], a["marker"], a["p"]), ("private conversation", [], "private", None))
        self.assertEqual(a["title"], "Mia Hale, Omar Ali")
        self.assertFalse(a["quiet"])

    def test_a_conversation_without_a_followed_person_is_left_out(self):
        self.record_at([{**CHAT, "from": OMAR, "people": [OMAR]}], "2026-10-08 09:30", how="sweep")
        f = self.v.root / "system/staging/vip.json"
        self.assertEqual(json.loads(f.read_text())["alerts"] if f.exists() else [], [])

    def test_a_later_sweep_proposes_nothing_from_a_summarised_conversation(self):
        self.record_at([CHAT], "2026-10-08 09:30", how="sweep")
        src = ("Teams · Chat: Project Falcon go-live · From: Mia Hale · Sent: {} · "
               "Link: https://teams.microsoft.com/l/message/{}")
        f = self.v.root / "system/staging/drafts/sweep.json"
        f.write_text(json.dumps({"items": [
            {"table": "actions", "conversation": "19:chat-falcon@thread.v2",
             "values": {"project": "ABC", "description": "Take the solution from production to live",
                        "owner": "Alan Carter", "source": src.format("2026-10-08 08:30", "a1")}},
            {"table": "decisions", "values": {"project": "ABC", "decision": "Go-live work falls under the existing contract",
                                              "source": src.format("2026-10-08 08:35", "a2")}}]}))       # by its title
        out = run(self.v, "sweep.py", "stage", str(f)).stdout
        self.assertEqual(list((self.v.root / "system/staging").glob("proposed-*-sweep.json")), [])
        self.assertEqual(out.count("summarised on Today"), 2)
        f.write_text(json.dumps({"items": [                                                   # a newer message: proposed
            {"table": "actions", "conversation": "19:chat-falcon@thread.v2",
             "values": {"project": "ABC", "description": "Book the go-live window", "owner": "Alan Carter",
                        "source": src.format("2026-10-08 09:10", "a3")}}]}))
        run(self.v, "sweep.py", "stage", str(f))
        self.assertEqual(len(list((self.v.root / "system/staging").glob("proposed-*-sweep.json"))), 1)

    def test_the_old_message_shape_still_records(self):
        out = record(self.v, [{"kind": "mail", "from": MIA, "subject": "Quick one", "sent": "2026-10-08 08:50",
                               "link": "https://x/m1", "gist": "Asks for a call."}])
        self.assertIn("Followed: 1 new alert", out)
        self.assertNotIn("summary", vip_file(self.v)["alerts"][0])


class ConversationPageTests(unittest.TestCase):
    """Today: one card per conversation (its title, "updated HH:MM" at its last message, the summary, each candidate with Create work item and
    Dismiss), the quiet line with only Seen and no count, and never the word VIP."""

    @classmethod
    def setUpClass(cls):
        from test_insight import chrome
        cls.v = v = vault()
        today = date.today().isoformat()
        f = v.root / "system/staging/drafts/found.json"
        f.write_text(json.dumps([{**CHAT, "last": f"{today} 08:40"}, {**HELLO, "last": f"{today} 08:20"}]))
        run(v, "sweep.py", "vip", "record", str(f), "--found", "sweep", now=f"{today} 09:30")
        run(v, "build_dashboard.py")
        probe = """const out={}; go("today"); renderToday();
          const card=document.querySelector('#tdList>li.td-message'), quiet=document.querySelector('#tdList>li.td-quiet');
          out.card=card&&card.textContent.replace(/\\s+/g,' ').trim();
          out.title=card&&card.querySelector('.t').textContent;
          out.cands=card?[...card.querySelectorAll('.tdcand')].map(li=>[li.querySelector('.tdctag').textContent,
            [...li.querySelectorAll('button')].map(b=>[b.dataset.alertdo,b.dataset.cand])]):null;
          out.cardButtons=card?card.querySelectorAll(':scope>.tacts button').length:-1;
          out.quiet=quiet&&quiet.textContent.replace(/\\s+/g,' ').trim(); out.quietButtons=quiet?quiet.querySelectorAll('button').length:-1;
          out.count=document.getElementById('nTd').textContent; out.page=document.getElementById('tdList').textContent;
          window.OUT=out;"""
        cls.out, cls.errors = chrome(v, probe, "vip-conv")

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def test_the_card_and_the_quiet_line(self):
        o = self.out
        self.assertEqual(self.errors, [])
        self.assertIsNotNone(o)
        self.assertNotIn("error", o, o)
        self.assertEqual(o["title"], "Project Falcon go-live")
        self.assertIn("updated 08:40", o["card"])                                            # the last message, not when it was recorded
        self.assertNotIn("09:30", o["card"])                                                 # (plan #81)
        self.assertIn("Example Programme", o["card"])                                        # the matched project, by name
        self.assertIn("Mia's team will take the solution from production to live", o["card"])
        self.assertEqual(o["cands"], [["Action", [["make", "1"], ["dismiss", "1"]]], ["Decision", [["make", "2"], ["dismiss", "2"]]]])
        self.assertEqual(o["cardButtons"], 1)                                                # BL-342: Handled on the card; the work-item buttons are per item
        self.assertIn("Mia Hale with Omar Ali: nothing for you", o["quiet"])
        self.assertIn("updated 08:20", o["quiet"])                                           # its own last message
        self.assertEqual(o["quietButtons"], 1)                                               # #276: only Seen
        self.assertEqual(o["count"], "1")                                                    # the quiet line isn't counted
        self.assertNotIn("VIP", o["page"])                                                   # BL-288


if __name__ == "__main__":
    unittest.main()
