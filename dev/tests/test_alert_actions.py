"""BL-296 (sprint-vip-p2-server): Dismiss, Undo and Create work item on a followed person's message, server side.

Run: python3 dev/tests/test_alert_actions.py
A throwaway vault with fictional alerts and a stand-in Claude (never Microsoft 365). Covers: Dismiss and Undo, the old
/api/vip/seen route, the prefill from references only, "Draft from the message" with the run mocked (its own allow list,
the development-repository guard, a private message refused, nothing written), staging a made item (dismissed, the
proposal recorded, its ID once applied), and no "VIP" in anything these routes return (BL-288).
"""
import json
import os
import re
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_live_server import free_port  # noqa: E402
from test_sweep_alerts import record, vip_vault  # noqa: E402

TOOLS = ["mcp__claude_ai_Microsoft_365__outlook_email_search", "mcp__claude_ai_Microsoft_365__chat_message_search",
         "mcp__claude_ai_Microsoft_365__read_resource"]
FAKE = r'''#!/usr/bin/env python3
import json, sys
from pathlib import Path
args = sys.argv[1:]
p = args[args.index("-p") + 1]
if p.startswith("creaite VIP check"):
    print(json.dumps({"type": "result", "result": "[]"}))
    sys.exit(0)
Path(__file__).with_name("draft-args.json").write_text(json.dumps(args))
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init", "session_id": "sess-m"})
reply = json.dumps({"title": "Confirm whether go-live can move a week (VIP)", "detail": "Mia asks if go-live can move.",
                    "due_date": "2026-10-16"})
out({"type": "assistant", "message": {"content": [{"type": "text", "text": reply}]}})
out({"type": "result", "result": reply, "session_id": "sess-m"})
'''
MIA = "Mia Hale <mia@client.example>"
GIST = "Asks whether go-live can move a week"
MESSAGES = [
    {"kind": "mail", "from": MIA, "subject": "[ABC] Go-live date", "sent": "2026-10-08 08:50",
     "link": "https://outlook.office365.com/owa/?ItemID=m1", "gist": GIST, "body": "SECRET BODY TEXT"},
    {"kind": "teams", "from": "Ben Ito <ben@brightwater.example>", "subject": "Quick one", "sent": "2026-10-08 09:05",
     "link": "https://teams.microsoft.com/l/message/t1", "gist": "Wants a call"},
    {"kind": "mail", "from": MIA, "subject": "[ABC] Personal", "sent": "2026-10-08 09:10", "link": "https://x/m3",
     "sensitivity": "confidential", "gist": "confidential message"},
    {"kind": "mail", "from": MIA, "subject": "[ABC] Licences", "sent": "2026-10-08 09:20", "link": "https://x/m4",
     "gist": "Licences"},
]


THREAD = {"kind": "teams", "conversation": "19:chat-thread@thread.v2", "title": "Go-live window", "from": MIA,
          "people": [MIA, "Omar Ali <omar@company.example>"], "last": "2026-10-08 08:30",
          "link": "https://teams.microsoft.com/l/chat/19:chat-thread", "sensitivity": "normal",
          "summary": "Mia asks whether go-live can move a week.", "type": "decision", "ask": "Say whether go-live can move",
          "due": "2026-10-16", "owners": ["you"], "items": []}


class AlertActionTests(unittest.TestCase):
    said = []                       # every body these routes returned, for the BL-288 check

    @classmethod
    def setUpClass(cls):
        cls.v = v = vip_vault()
        record(v, MESSAGES + [THREAD])
        cls.ids = {a["subject"]: a["id"] for a in cls.vip()["alerts"]}
        fake = v.root / "fake_claude.py"
        fake.write_text(FAKE)
        fake.chmod(0o755)
        cls.port = free_port()
        cls.base = f"http://127.0.0.1:{cls.port}"
        cls.proc = subprocess.Popen([sys.executable, str(v.root / "system/scripts/live_server.py")], cwd=v.root,
                                    env={**os.environ, "CREAITE_PORT": str(cls.port), "CREAITE_CLAUDE": str(fake)},
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
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
        cls.v.cleanup()

    @classmethod
    def vip(cls):
        return json.loads((cls.v.root / "system/staging/vip.json").read_text())

    def alert(self, subject):
        return next(a for a in self.vip()["alerts"] if a["subject"] == subject)

    def post(self, path, body, keep=True):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        with urllib.request.urlopen(req, timeout=60) as r:
            text = r.read().decode()
        if keep:
            self.said.append(text)
        return json.loads(text) if not text.startswith("data:") else text

    def unseen(self):
        return [a["subject"] for a in self.post("/api/vip", {}, keep=False)["alerts"]]

    def proposals(self):
        return sorted(p.name for p in (self.v.root / "system/staging").glob("proposed-*.json"))

    def test_1_dismiss_and_undo(self):
        aid = self.ids["[ABC] Licences"]
        got = self.post("/api/alerts/dismiss", {"ids": [aid]})
        self.assertEqual((got["ok"], got["dismissed"], got["ids"]), (True, 1, [aid]))
        self.assertNotIn("[ABC] Licences", self.unseen())
        self.assertIsNotNone(self.alert("[ABC] Licences")["seen"])                         # kept in the history
        self.assertEqual(self.post("/api/alerts/dismiss", {"ids": [aid]})["dismissed"], 0)  # already dismissed
        back = self.post("/api/alerts/undo", {"ids": [aid]})
        self.assertEqual((back["ok"], back["restored"]), (True, 1))
        self.assertIn("[ABC] Licences", self.unseen())
        self.assertIsNone(self.alert("[ABC] Licences")["seen"])
        with self.assertRaises(urllib.error.HTTPError) as e:                                # which one?
            self.post("/api/alerts/dismiss", {})
        self.assertEqual(e.exception.code, 400)
        e.exception.close()
        self.assertNotIn("SECRET", (self.v.root / "system/staging/vip.json").read_text())  # never message text

    def test_2_old_seen_route_still_works(self):
        aid = self.ids["[ABC] Licences"]
        got = self.post("/api/vip/seen", {"ids": [aid]}, keep=False)
        self.assertEqual((got["ok"], got["seen"]), (True, 1))
        self.assertNotIn("[ABC] Licences", self.unseen())
        self.post("/api/alerts/undo", {"id": aid})                                         # Undo covers a Seen too
        self.assertIn("[ABC] Licences", self.unseen())

    def test_3_prefill_holds_references_only(self):
        got = self.post("/api/alerts/prefill", {"id": self.ids["[ABC] Go-live date"]})
        self.assertTrue(got["ok"], got)
        pre = got["prefill"]
        self.assertEqual((pre["type"], pre["table"], pre["project"], pre["needs_project"]), ("action", "actions", "ABC", False))
        self.assertEqual(pre["project_name"], self.v.rows("projects")[0]["name"])
        self.assertEqual(pre["values"], {"description": "[ABC] Go-live date", "owner": "Alan Carter", "due_date": None})
        self.assertEqual(pre["raised"], "2026-10-08")
        self.assertEqual(pre["source"], "Email · From: Mia Hale <mia@client.example> · Subject: [ABC] Go-live date · "
                                        "Sent: 2026-10-08 08:50 · Link: https://outlook.office365.com/owa/?ItemID=m1")
        text = json.dumps(got)
        for never in (GIST, "SECRET", "gist", '"client"'):                                   # no text, no gist, no follow kind
            self.assertNotIn(never, text)
        teams = self.post("/api/alerts/prefill", {"id": self.ids["Quick one"], "type": "risk"})["prefill"]
        self.assertEqual((teams["project"], teams["needs_project"], teams["values"]["type"], teams["table"]),
                         (None, True, "Risk", "raid"))
        self.assertTrue(teams["source"].startswith("Teams · Chat: Quick one · From: Ben Ito · Sent: 2026-10-08 09:05"))
        dec = self.post("/api/alerts/prefill", {"id": self.ids["Quick one"], "type": "decision"})["prefill"]
        self.assertEqual(dec["values"], {"decision": "Quick one", "made_by": "Alan Carter", "needed_by": None})
        self.assertFalse(self.post("/api/alerts/prefill", {"id": "nope"})["ok"])
        self.assertFalse(self.post("/api/alerts/prefill", {"id": self.ids["Quick one"], "type": "memo"})["ok"])

    def draft(self, subject, run):
        text = self.post("/api/alerts/draft", {"id": self.ids[subject], "run": run})
        if isinstance(text, dict):
            return text
        return [json.loads(line[6:]) for line in text.splitlines() if line.startswith("data: ")]

    def test_4_draft_from_the_message_mocked(self):
        before, alerts = self.proposals(), self.vip()["alerts"]
        evs = self.draft("[ABC] Go-live date", "m-test-1")
        drafted = next(e for e in evs if e["type"] == "draft")
        self.assertTrue(drafted["ok"], drafted)
        pre = drafted["prefill"]
        self.assertEqual(pre["values"]["description"], "Confirm whether go-live can move a week")   # the word taken out
        self.assertNotIn("text", [e["type"] for e in evs if e.get("text")])                 # the raw reply isn't streamed
        self.assertEqual(pre["values"]["due_date"], "2026-10-16")
        self.assertEqual(pre["detail"], "Mia asks if go-live can move.")
        self.assertEqual(pre["source"][:13], "Email · From:")
        args = json.loads((self.v.root / "draft-args.json").read_text())
        self.assertEqual(args[args.index("--allowedTools") + 1].split(","), TOOLS)          # its own allow list only
        deny = args[args.index("--disallowedTools") + 1].split(",")
        for d in ("Bash", "Write", "Edit", "WebFetch"):
            self.assertIn(d, deny)
        self.assertNotIn("--settings", args)
        self.assertEqual(self.proposals(), before)                                          # nothing written
        self.assertEqual(self.vip()["alerts"], alerts)
        refused = self.draft("[ABC] Personal", "m-test-2")                                  # a confidential message
        self.assertFalse(refused["ok"])
        self.assertIn("write the item yourself", refused["message"])
        dev = self.v.root / ".creaite-dev"
        dev.write_text("")
        try:
            off = self.draft("[ABC] Go-live date", "m-test-3")
            self.assertEqual((off["ok"], off["off"]), (False, True))
            self.assertIn("development repository", off["message"])
        finally:
            dev.unlink()

    def test_5_make_stages_dismisses_and_records(self):
        aid = self.ids["[ABC] Go-live date"]
        got = self.post("/api/alerts/make", {"id": aid, "type": "action",
                                             "values": {"description": "Confirm whether go-live can move a week",
                                                        "due_date": "2026-10-16", "status": "Closed", "id": "ABC-A-999"}})
        self.assertTrue(got["ok"], got)
        self.assertEqual(got["made"]["state"], "staged")
        prop = json.loads((self.v.root / "system/staging" / got["proposal"]).read_text())
        self.assertTrue(got["proposal"].endswith("-dashboard.json"))
        self.assertEqual(prop["source_run"], "dashboard")
        item = prop["items"][0]
        self.assertEqual((item["op"], item["table"], item["decision"]), ("new", "actions", "pending"))   # for Review (check 45)
        self.assertIn("for Review", got["message"])
        v = item["values"]
        self.assertEqual((v["project"], v["owner"], v["due_date"], v["raised"]), ("ABC", "Alan Carter", "2026-10-16", "2026-10-08"))
        self.assertNotIn("status", v)                                                       # only the form's own fields
        self.assertIn("Link: https://outlook.office365.com/owa/?ItemID=m1", v["source"])
        self.assertNotIn("[ABC] Go-live date", self.unseen())                               # dismissed
        made = self.alert("[ABC] Go-live date")["made"]
        self.assertEqual((made["proposal"], made["n"], made["id"]), (got["proposal"], 1, None))
        p = self.v.root / "system/staging" / got["proposal"]
        self.v.run("apply")                                                                 # pending: an apply leaves it alone
        self.assertTrue(p.exists())
        self.assertFalse(any(r["description"] == "Confirm whether go-live can move a week" for r in self.v.rows("actions")))
        prop["items"][0]["decision"] = "approved"                                           # Alan approves it in Review
        p.write_text(json.dumps(prop))
        self.v.run("apply")                                                                 # and applies (not this route)
        self.post("/api/vip", {}, keep=False)
        made = self.alert("[ABC] Go-live date")["made"]
        self.assertRegex(made["id"] or "", r"^ABC-A-\d{3}$")
        row = next(r for r in self.v.rows("actions") if r["id"] == made["id"])
        self.assertEqual(row["description"], "Confirm whether go-live can move a week")
        pre = self.post("/api/alerts/prefill", {"id": aid})["prefill"]
        self.assertEqual((pre["made"]["id"], pre["made"]["state"]), (made["id"], "applied"))

    def test_6_make_needs_a_project_and_undo_forgets_a_removed_one(self):
        aid = self.ids["Quick one"]
        no = self.post("/api/alerts/make", {"id": aid, "values": {"description": "Call Ben back"}})
        self.assertEqual((no["ok"], no["message"]), (False, "Choose a project for it first."))
        self.assertIn("Quick one", self.unseen())                                           # left as it was
        got = self.post("/api/alerts/make", {"id": aid, "type": "issue",
                                             "values": {"project": "ABC", "description": "Call Ben back"}})
        self.assertTrue(got["ok"], got)
        self.assertEqual(json.loads((self.v.root / "system/staging" / got["proposal"]).read_text())
                         ["items"][0]["values"]["type"], "Issue")
        (self.v.root / "system/staging" / got["proposal"]).unlink()                          # the page's Undo last
        self.post("/api/alerts/undo", {"ids": [aid]})
        self.assertIn("Quick one", self.unseen())
        self.assertNotIn("made", self.alert("Quick one"))

    def test_6b_handled_undo_and_log(self):
        """BL-342: Handled settles a thread's card and stages nothing, Undo puts it back; Log on the matched item stages one
        pending update, once; a card with no match can't be logged."""
        aid = self.ids["Go-live window"]
        before = self.proposals()
        got = self.post("/api/alerts/handled", {"ids": [aid]})
        self.assertEqual((got["ok"], got["handled"], got["ids"]), (True, 1, [aid]))
        self.assertRegex(got["at"], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")
        card = self.alert("Go-live window")
        self.assertEqual((card["state"], bool(card["seen"]), bool(card["handled_at"])), ("handled", True, True))
        self.assertNotIn("Go-live window", self.unseen())
        self.assertEqual(self.proposals(), before)                                         # stages nothing
        self.assertEqual(self.post("/api/alerts/handled", {"ids": [aid]})["handled"], 0)    # already settled
        self.assertEqual(self.post("/api/alerts/undo", {"ids": [aid]})["restored"], 1)
        card = self.alert("Go-live window")
        self.assertEqual((card["state"], card["seen"]), ("open", None))
        self.assertIn("Go-live window", self.unseen())
        with self.assertRaises(urllib.error.HTTPError) as e:                                # which one?
            self.post("/api/alerts/handled", {})
        self.assertEqual(e.exception.code, 400)
        e.exception.close()
        no = self.post("/api/alerts/log", {"id": aid})
        self.assertEqual((no["ok"], no["message"]), (False, "No matched item to log it on."))
        self.assertFalse(self.post("/api/alerts/log", {"id": "nope"})["ok"])
        item = self.alert("[ABC] Go-live date")["made"]["id"]                                # the action test 5 made and applied
        st = json.loads((self.v.root / "system/staging/vip.json").read_text())
        next(a for a in st["alerts"] if a["id"] == aid)["match"] = {"id": item, "relation": "update", "why": "test"}
        (self.v.root / "system/staging/vip.json").write_text(json.dumps(st))
        before = self.proposals()
        log = self.post("/api/alerts/log", {"id": aid})
        self.assertTrue(log["ok"], log)
        self.assertEqual((log["id"], log["logged"]["state"], log["already"]), (item, "staged", False))
        self.assertIn(f"Staged an update on {item} for Review", log["message"])
        (new,) = [p for p in self.proposals() if p not in before]
        spec = json.loads((self.v.root / "system/staging" / new).read_text())
        (it,) = spec["items"]
        self.assertEqual((it["op"], it["table"], it["id"], it["decision"]), ("update", "actions", item, "pending"))
        self.assertTrue(it["based_on"])
        self.assertEqual(list(it["changes"]), ["latest_update"])
        again = self.post("/api/alerts/log", {"id": aid})
        self.assertEqual((again["ok"], again["already"], again["proposal"]), (True, True, log["proposal"]))
        self.assertIn("Already logged", again["message"])
        self.assertEqual(len([p for p in self.proposals() if p not in before]), 1)          # nothing new the second time
        self.assertEqual(self.alert("Go-live window")["match"]["id"], item)

    def test_7_no_vip_in_any_response(self):
        self.assertTrue(self.said)
        for text in self.said:
            self.assertNotRegex(text, r"(?i)\bvips?\b")


if __name__ == "__main__":
    unittest.main()
