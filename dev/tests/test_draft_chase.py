"""BL-298 (sprint-draft-chase-server): Draft email from the peek, the server and Python side.

Run: python3 dev/tests/test_draft_chase.py
The wording for the three modes (chase, help, decision) and the three tones, exactly as accepted (dev/BACKLOG.md › BL-298 › As
accepted); the defaults (reply by two working days ahead, the tone from the chase count, the latest update on); the recipient
suggestions for Alan's own item; /api/chase/pane; and /api/chases recording each mode as item IDs, a date and the mode only.
Chase mode keeps BL-224's DE_CHASE subjects, its texts in the singular for one item (Alan, 13-10-2026). No model is called here.
"""
import json
import os
import re
import socket
import subprocess
import sys
import time
import unittest
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "system/scripts"))
import drafts  # noqa: E402
from test_dashboard import new  # noqa: E402
from test_tracker import ABC, Vault, action  # noqa: E402

NOW = "2026-10-13 09:00"          # a Tuesday
HELP = {"id": "FAL-A-007", "code": "FAL", "name": "Kestrel Energy AI", "kind": "actions", "owner": "Alan Carter",
        "text": "Reach out to Dana on back-to-back commercials", "due": "2026-10-19", "priority": "Medium",
        "update": "Alan: Tom asked for the commercials to mirror the Kestrel Group contract terms (12-10-2026)"}
HELP_OPTS = {"mode": "help", "reply_by": "2026-10-15", "first": "Dana", "from": "Alan", "today": "2026-10-13", "hour": 9,
             "outcome": "the back-to-back commercials for Northgate agreed",
             "need": "Confirm whether the Northgate terms mirror the Kestrel Group contract, and who on your side signs them off."}
DECISION = {"id": "MER-D-002", "code": "MER", "name": "Larkspur Phase 2", "kind": "decisions", "owner": "Chris Dunn",
            "text": "Which use cases go into the Phase 2 proposal", "due": "2026-10-15", "priority": "",
            "update": "", "unblocks": "the Phase 2 proposal"}
CHASE = {"id": "FAL-A-009", "code": "FAL", "name": "Kestrel Energy AI", "kind": "actions", "owner": "Tom Reid",
         "text": "Share the Northgate UAT plan", "due": "2026-10-09", "priority": "High",
         "update": "Tom: plan in draft, waiting on Northgate's test environment dates (08-10-2026)"}
SAME = {"reply_by": "2026-10-15", "from": "Alan", "today": "2026-10-13", "hour": 9}


class HelpWording(unittest.TestCase):
    """Alan's own item: a request for help, never a chase; the three tones as accepted."""

    def draft(self, tone, last=""):
        return drafts.chase_draft(HELP, {**HELP_OPTS, "tone": tone, "chased": {"n": tone, "last": last}})

    def test_first(self):
        d = self.draft(0)
        self.assertEqual(d["subject"], "[FAL] Your help with back-to-back commercials")
        self.assertEqual(d["opening"], "I've been asked to follow up with you on the back-to-back commercials, to get the back-to-back "
                                       "commercials for Northgate agreed. The action is with me (FAL-A-007), and I need your help to close it.")

    def test_second(self):
        d = self.draft(1, "2026-10-13")
        self.assertEqual(d["subject"], "[FAL] Following up: your help with back-to-back commercials")
        self.assertEqual(d["opening"], "I'm following up on my note of 13-10-2026 about the back-to-back commercials; I still need your "
                                       "help to get the back-to-back commercials for Northgate agreed. The action is with me (FAL-A-007), "
                                       "and I need your help to close it.")

    def test_firmer(self):
        d = self.draft(2, "2026-10-13")
        self.assertEqual(d["subject"], "[FAL] Needed this week: your help with back-to-back commercials")
        self.assertEqual(d["opening"], "I need to close this out this week: the action to get the back-to-back commercials for Northgate agreed "
                                       "is with me, and I can't finish it without your input.")

    def test_the_rest_of_the_email(self):
        d = self.draft(0)
        self.assertEqual((d["need_label"], d["need"]), ("What I need from you:", HELP_OPTS["need"]))
        self.assertEqual(d["ask"], "Could you let me know by Thursday 15-10-2026? If someone else is better placed to help, a name would be "
                                   "just as useful.")
        self.assertEqual(d["row"]["owner"], "Owner: Alan Carter")
        self.assertEqual(d["row"]["update"], f"Latest update: {HELP['update']}")
        self.assertEqual((d["row"]["due_label"], d["row"]["due_words"], d["row"]["overdue"]), ("Due", "due in 6 days", False))
        t = d["text"]
        self.assertTrue(t.startswith("Good morning, Dana,\n\nI've been asked"), t)
        self.assertIn(f"\nWhat I need from you: {HELP_OPTS['need']}\n", t)
        self.assertTrue(t.endswith("\n\nThank you,\nAlan"), t)
        off = drafts.chase_draft(HELP, {**HELP_OPTS, "tone": 0, "include_update": False})
        self.assertEqual(off["row"]["update"], "")
        self.assertNotIn("Latest update", off["text"])

    def test_without_an_outcome_or_need_it_fills_them_from_the_item(self):
        d = drafts.chase_draft(HELP, {**SAME, "mode": "help", "tone": 0, "first": "Dana"})
        self.assertIn("to get the back-to-back commercials done.", d["opening"])
        self.assertEqual(d["need"], "Your input on the back-to-back commercials.")
        self.assertEqual(d["outcome"], "the back-to-back commercials done")                    # for the pane's To get … done
        plain = drafts.chase_draft({**HELP, "text": "Share the Northgate UAT plan"}, {**SAME, "mode": "help", "tone": 0})
        self.assertEqual(plain["subject"], "[FAL] Your help with Share the Northgate UAT plan")
        self.assertIn("follow up with you on “Share the Northgate UAT plan”, to get this done.", plain["opening"])


class DecisionWording(unittest.TestCase):
    """A decision waiting on someone: to the decision maker, by its needed-by date."""

    def draft(self, tone, n=0, last=""):
        return drafts.chase_draft(DECISION, {**SAME, "mode": "decision", "tone": tone, "first": "Chris", "chased": {"n": n, "last": last}})

    def test_the_three_tones(self):
        first, second, firm = self.draft(0), self.draft(1, 1, "2026-10-08"), self.draft(2, 2, "2026-10-08")
        self.assertEqual(first["subject"], "[MER] Decision needed: Which use cases go into the Phase 2 proposal")
        self.assertEqual(second["subject"], "[MER] Second reminder: decision needed: Which use cases go into the Phase 2 proposal")
        self.assertEqual(firm["subject"], "[MER] Decision needed this week: Which use cases go into the Phase 2 proposal")
        self.assertEqual(first["opening"], "A quick note on the decision below, which is needed soon for the Phase 2 proposal.")
        self.assertEqual(second["opening"], "I'm following up on my earlier note of 08-10-2026 about the decision below; it is needed "
                                            "for the Phase 2 proposal.")
        self.assertEqual(firm["opening"], "This decision is now holding up the Phase 2 proposal; I have asked for it twice, most recently "
                                          "on 08-10-2026.")
        for d in (first, second, firm):
            self.assertEqual(d["ask"], "Could you let me have the decision, or tell me what you need to make it, by Thursday 15-10-2026?")

    def test_the_row(self):
        r = self.draft(0)["row"]
        self.assertEqual((r["label"], r["due_label"], r["due"], r["due_words"]), ("Decision needed:", "Needed by", "15-10-2026",
                                                                                  "needed in 2 days"))
        self.assertEqual(r["owner"], "")

    def test_no_earlier_chase_date_reads_cleanly(self):
        self.assertEqual(self.draft(1)["opening"], "I'm following up on my earlier note about the decision below; it is needed for the "
                                                   "Phase 2 proposal.")
        self.assertEqual(self.draft(2)["opening"], "This decision is now holding up the Phase 2 proposal; I have asked for it before.")


class ChaseWording(unittest.TestCase):
    """Someone else's item: BL-224's three chase texts, unchanged."""

    def test_the_wording_is_de_chase_as_it_stands(self):
        js = (REPO / "system/templates/dashboard/src/drafts.js").read_text(encoding="utf-8")
        block = re.search(r"const DE_CHASE=\[(.*?)\];", js, re.S).group(1)
        rows = re.findall(r'\{subj:"(.*?)",open:"(.*?)",ask:"(.*?)"\}', block)
        w = drafts.CHASE_WORDING["chase"]
        self.assertEqual([r[0] for r in rows], list(w["subjects"]))
        self.assertEqual([r[1] for r in rows], list(w["openings"]))
        self.assertEqual([r[2] for r in rows], list(w["asks"]))
        self.assertIn('DE_THANKS="Thank you very much for your help."', (REPO / "system/templates/dashboard/src/drafts.js")
                      .read_text(encoding="utf-8"))

    def test_the_three_tones(self):
        d = [drafts.chase_draft(CHASE, {**SAME, "mode": "chase", "tone": t, "first": "Tom", "chased": c})
             for t, c in ((0, {"n": 0, "last": ""}), (1, {"n": 1, "last": "2026-10-08"}), (2, {"n": 2, "last": "2026-10-10"}))]
        self.assertEqual([x["subject"] for x in d], ["[FAL] Reminder: Share the Northgate UAT plan", "[FAL] Second reminder: Share the Northgate UAT plan",
                                                     "[FAL] Overdue, reply needed: Share the Northgate UAT plan"])
        # Alan, 13-10-2026: one item, so DE_CHASE's texts in the singular; the subjects stay DE_CHASE's
        self.assertEqual(d[0]["opening"], "A quick reminder about the item below, which is now past its due date.")
        self.assertEqual(d[1]["opening"], "I'm following up on my earlier note of 08-10-2026 about the item below, which is still overdue.")
        self.assertEqual(d[2]["opening"], "This item is now well overdue and is holding up other work; I have chased it twice, most "
                                          "recently on 10-10-2026.")
        self.assertEqual(d[0]["ask"], "Could you let me know where it stands, and when I can expect it? It would be helpful to hear "
                                      "back by Thursday 15-10-2026. Thank you very much for your help.")
        self.assertEqual(d[1]["ask"].split("?")[0], "Could you let me have an update, and a date for it")
        self.assertTrue(d[2]["ask"].startswith("Please reply with a firm date, or tell me what is blocking it so that we can resolve it "
                                               "together."))
        self.assertEqual((d[0]["row"]["due_words"], d[0]["row"]["overdue"]), ("4 days overdue", True))
        self.assertTrue(d[0]["text"].endswith("Kind regards,\nAlan"))

    def test_a_risk_asks_its_owner_for_the_response(self):
        risk = {**CHASE, "id": "FAL-004", "kind": "raid", "type": "Risk", "text": "Northgate test environment late", "response": ""}
        r = drafts.chase_draft(risk, {**SAME, "mode": "chase", "tone": 0})["row"]
        self.assertEqual((r["label"], r["response"]), ("Risk:", "Response: none recorded yet"))

    def test_a_polished_opening_replaces_only_the_opening(self):
        plain = drafts.chase_draft(CHASE, {**SAME, "mode": "chase", "tone": 0})
        polished = drafts.chase_draft(CHASE, {**SAME, "mode": "chase", "tone": 0, "cover": "A new opening."})
        self.assertEqual(polished["text"].replace("A new opening.", plain["opening"]), plain["text"])


class Defaults(unittest.TestCase):
    def test_two_working_days_ahead(self):
        self.assertEqual(drafts.working_days_ahead("2026-10-12", 2, {}), "2026-10-14")   # Monday → Wednesday
        self.assertEqual(drafts.working_days_ahead("2026-10-15", 2, {}), "2026-10-19")   # Thursday → Monday, over the weekend
        self.assertEqual(drafts.working_days_ahead("2026-10-16", 2, {}), "2026-10-20")   # Friday → Tuesday
        self.assertEqual(drafts.working_days_ahead("2026-10-17", 2, {}), "2026-10-20")   # Saturday → Tuesday
        gulf = {"work": {"weekend_days": ["Friday", "Saturday"]}}
        self.assertEqual(drafts.working_days_ahead("2026-10-15", 2, gulf), "2026-10-19")  # Thursday → (Sunday, Monday)
        self.assertEqual(drafts.working_days_ahead("2026-10-14", 2, gulf), "2026-10-18")  # Wednesday → (Thursday, Sunday)

    def test_the_tone_from_the_chase_count_and_the_update_on(self):
        counts = {"A": {"n": 1, "last": "2026-10-08"}, "B": {"n": 5, "last": "2026-10-10"}}
        for item, tone in (("X", 0), ("A", 1), ("B", 2)):
            d = drafts.chase_defaults(item, "2026-10-16", counts, {})
            self.assertEqual((d["tone"], d["reply_by"], d["include_update"]), (tone, "2026-10-20", True))
        self.assertEqual(drafts.chase_defaults("A", "2026-10-16", counts, {})["chased"], {"n": 1, "last": "2026-10-08"})
        self.assertEqual(drafts.chase_draft(CHASE, {**SAME, "mode": "chase", "chased": {"n": 1, "last": "2026-10-08"}})["tone"], 1)

    def test_the_mode_follows_whose_item_it_is(self):
        self.assertEqual(drafts.chase_mode("actions", "Alan Carter", "Alan Carter"), "help")
        self.assertEqual(drafts.chase_mode("actions", "Sara Example", "Alan Carter"), "chase")
        self.assertEqual(drafts.chase_mode("raid", "Sara Example", "Alan Carter"), "chase")
        self.assertEqual(drafts.chase_mode("decisions", "Jane Doe", "Alan Carter"), "decision")
        self.assertEqual(drafts.chase_mode("decisions", "alan carter", "Alan Carter"), "help")


REGISTER = """# People register

## People

| Full name | Email | Aliases | Organisation | Role | Hidden | Labels | VIP |
|-----------|-------|---------|--------------|------|--------|--------|-----|
| Alan Carter | alan@brightwater.example | Alan | Brightwater | Programme manager |  |  |  |
| Jane Doe | jane.doe@client.com | Jane, JD | Example Client Ltd | Sponsor |  |  | yes |
| Omar Ali | omar@def.example | Omar | Enable | Project manager |  |  |  |
| Sara Example | sara.example@client.com | Sara | Example Client Ltd | Delivery lead |  |  |  |
| Tom Reid | tom.r@example.com | Tom | Northgate | Account lead |  |  |  |
| Dana Okoye | dana.o@example.com |  | Northgate | Commercial lead |  |  |  |
| Quiet Person | quiet@example.com |  | Elsewhere | Former lead | yes |  |  |
"""


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class VaultCase(unittest.TestCase):
    """A throwaway vault: Alan's own action, someone else's overdue action, a pending decision, a closed action."""

    @classmethod
    def setUpClass(cls):
        cls.v = v = Vault()
        v.run("init")
        (v.root / "projects/_portfolio/people-register.md").write_text(REGISTER)
        src = f"{ABC}/minutes/2026-10-12 Alan x Tom catch up.docx — Actions"
        v.propose("seed", [
            action(1, description="Reach out to Dana on back-to-back commercials", due_date="2026-10-19", raised="2026-10-12",
                   latest_update="12-10-2026: Tom asked for the commercials to mirror the Kestrel Group terms", source=src),
            action(2, description="Share the UAT plan", owner="Sara Example", due_date="2026-10-09", priority="High", raised="2026-10-05",
                   source="Email · From: Omar Ali <omar@def.example> · Subject: UAT plan · Sent: 2026-10-05 10:00"),
            action(3, description="Send the pricing note", raised="2026-10-05",
                   source="Email · From: Omar <omar@def.example> · Subject: Pricing · Sent: 2026-10-05 10:00"),
            new("decisions", 4, project="ABC", decision="Which use cases go into phase 2", made_by="Jane Doe", status="Pending",
                needed_by="2026-10-15", source="Alan (cx-edit), 2026-10-06"),
            action(5, description="Old thing", raised="2026-10-01", status="Closed", closed="2026-10-02"),
            action(6, description="Confidential: board pack figures", owner="Sara Example", raised="2026-10-01"),
        ])
        v.run("apply")
        (v.root / "system/staging/calendar.json").write_text(json.dumps({"days": {"2026-10-12": [
            {"id": "e1", "start": "10:00", "end": "10:30", "title": "Alan x Tom catch up", "attendees": [
                {"name": "Tom Reid", "email": "tom.r@example.com"}, {"name": "Alan Carter", "email": "alan@brightwater.example"},
                {"name": "Sara Example", "email": ""}]}]}}))
        ids = {r["description"]: r["id"] for r in v.rows("actions")}
        cls.mine, cls.theirs, cls.omars, cls.closed, cls.secret = (ids["Reach out to Dana on back-to-back commercials"], ids["Share the UAT plan"],
                                                                   ids["Send the pricing note"], ids["Old thing"],
                                                                   ids["Confidential: board pack figures"])
        cls.decision = v.rows("decisions")[0]["id"]

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def pane(self, **req):
        r = subprocess.run([sys.executable, "system/scripts/drafts.py", "chase-pane"], input=json.dumps(req), capture_output=True, text=True,
                           cwd=self.v.root, env={**os.environ, "CREAITE_NOW": NOW})
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)


class Recipients(VaultCase):
    def test_the_ranking_for_alans_own_item(self):
        p = self.pane(id=self.mine)
        got = [(s["name"], s["why"]) for s in p["suggestions"]]
        self.assertEqual(got, [("Dana Okoye", "named in the item"), ("Tom Reid", "named in the item"),
                               ("Sara Example", "at the meeting"), ("Jane Doe", "project stakeholder"), ("Omar Ali", "project stakeholder"),
                               ("Example Person", "project stakeholder")])                # Shared, not in the people register
        self.assertEqual((p["suggestions"][-1]["email"], p["suggestions"][-1]["known"]), ("", False))
        self.assertEqual(p["suggestions"][0]["email"], "dana.o@example.com")
        self.assertEqual({s["project"] for s in p["suggestions"]}, {"Example Programme"})       # by name, never the code
        self.assertEqual(p["to"], {"name": "Dana Okoye", "email": "dana.o@example.com", "first": "Dana"})
        anyone = [a["name"] for a in p["anyone"]]
        self.assertNotIn("Alan Carter", anyone)
        self.assertNotIn("Quiet Person", anyone)                                                # hidden
        self.assertIn("Tom Reid", anyone)
        self.assertNotIn("vip", json.dumps(p).lower())                                          # BL-288: nobody is labelled

    def test_who_raised_it_comes_before_the_stakeholders(self):
        got = [(s["name"], s["why"]) for s in self.pane(id=self.omars)["suggestions"]]
        self.assertEqual(got, [("Omar Ali", "raised it"), ("Jane Doe", "project stakeholder"),
                               ("Example Person", "project stakeholder")])

    def test_alan_picks_the_recipient(self):
        p = self.pane(id=self.mine, to="Tom Reid")
        self.assertEqual(p["to"]["email"], "tom.r@example.com")
        self.assertTrue(p["draft"]["greeting"].endswith(", Tom,"))


class Pane(VaultCase):
    def test_alans_own_item_is_help(self):
        p = self.pane(id=self.mine, hour=9, outcome="the commercials agreed", need="Your sign-off.")
        self.assertTrue(p["ok"], p)
        self.assertEqual((p["mode"], p["mode_tag"]), ("help", "Yours"))
        self.assertEqual(p["mode_line"], "This action is yours, so this asks for help rather than chasing. It makes clear the action is with "
                                         "you and what you need from them.")
        self.assertEqual(p["defaults"], {"reply_by": "2026-10-15", "tone": 0, "include_update": True, "chased": {"n": 0, "last": ""}})
        d = p["draft"]
        self.assertEqual(d["subject"], "[ABC] Your help with back-to-back commercials")
        self.assertIn("to get the commercials agreed.", d["opening"])
        self.assertEqual(d["need"], "Your sign-off.")
        self.assertIn("Thursday 15-10-2026", d["ask"])
        self.assertEqual(p["wording"]["help"]["subjects"][0], "Your help with")

    def test_someone_elses_item_is_a_chase_to_its_owner(self):
        p = self.pane(id=self.theirs)
        self.assertEqual((p["mode"], p["to"]["name"], p["to"]["email"]), ("chase", "Sara Example", "sara.example@client.com"))
        self.assertEqual(p["mode_line"], "Chasing Sara, who owns it. Not chased before: a first reminder.")
        self.assertEqual((p["suggestions"], p["anyone"]), ([], []))
        self.assertEqual(p["draft"]["subject"], "[ABC] Reminder: Share the UAT plan")

    def test_a_pending_decision_asks_its_decision_maker(self):
        p = self.pane(id=self.decision, tone=1)
        self.assertEqual((p["mode"], p["to"]["name"]), ("decision", "Jane Doe"))
        self.assertEqual(p["draft"]["subject"], "[ABC] Second reminder: decision needed: Which use cases go into phase 2")
        self.assertIn("the next steps on Example Programme", p["draft"]["opening"])
        self.assertEqual(p["draft"]["unblocks"], "the next steps on Example Programme")

    def test_closed_confidential_and_unknown_items_are_refused(self):
        for item, words in ((self.closed, "closed"), (self.secret, "confidential"), ("ABC-A-999", "isn't in your project record")):
            p = self.pane(id=item)
            self.assertFalse(p["ok"])
            self.assertIn(words, p["message"])


class Server(VaultCase):
    """/api/chase/pane and /api/chases on the live server."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.port = free_port()
        cls.base = f"http://127.0.0.1:{cls.port}"
        env = {**os.environ, "CREAITE_PORT": str(cls.port), "CREAITE_NOW": NOW}
        cls.proc = subprocess.Popen([sys.executable, str(cls.v.root / "system/scripts/live_server.py")], env=env,
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
        cls.proc.terminate()                  # our own server only, by its process
        cls.proc.wait(timeout=10)
        super().tearDownClass()

    def post(self, path, body):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())

    def log(self):
        p = self.v.root / "system/staging/chases.json"
        return json.loads(p.read_text())["chases"] if p.exists() else []

    def test_each_mode_is_recorded_with_ids_only_and_the_next_one_steps_up(self):
        before = len(self.log())
        for item, mode in ((self.theirs, "chase"), (self.mine, "help"), (self.decision, "decision")):
            r = self.post("/api/chases", {"ids": [item], "mode": mode})
            self.assertTrue(r["ok"], r)
            self.assertEqual(r["record"]["mode"], mode)
            self.assertEqual(r["chases"][item]["n"], 1)
        recs = self.log()[before:]
        self.assertEqual([sorted(x) for x in recs], [["date", "ids", "mode"]] * 3)     # references only, never text
        self.assertEqual([(x["ids"], x["mode"]) for x in recs], [([self.theirs], "chase"), ([self.mine], "help"),
                                                                 ([self.decision], "decision")])
        self.assertTrue(all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", x["date"]) for x in recs))
        p = self.post("/api/chase/pane", {"id": self.mine, "hour": 9})
        self.assertEqual((p["mode"], p["defaults"]["tone"], p["draft"]["tone_name"]), ("help", 1, "Second"))
        self.assertTrue(p["draft"]["subject"].startswith("[ABC] Following up: your help with"))
        d = self.post("/api/chase/pane", {"id": self.decision})
        self.assertIn("Chased once, on", d["mode_line"])

    def test_chase_mode_is_unchanged(self):
        r = self.post("/api/chases", {"ids": [self.omars, "not an id"], "mode": "something else"})
        self.assertEqual(r["record"]["mode"], "chase")                                   # an unknown mode is a chase, as before
        self.assertEqual(r["record"]["ids"], [self.omars])
        for mode in ("update", "followup"):                                              # BL-224's other records still kept, not counted
            self.assertEqual(self.post("/api/chases", {"ids": [self.closed], "mode": mode})["record"]["mode"], mode)
        self.assertNotIn(self.closed, self.post("/api/chases", {"ids": [self.omars]})["chases"])

    def test_the_pane_route_reads_only(self):
        before = sorted(p.name for p in (self.v.root / "system/staging").iterdir())
        p = self.post("/api/chase/pane", {"id": self.theirs, "tone": 2, "include_update": False, "reply_by": "2026-10-20"})
        self.assertEqual((p["draft"]["tone"], p["draft"]["row"]["update"]), (2, ""))
        self.assertIn("Tuesday 20-10-2026", p["draft"]["ask"])
        self.assertEqual(sorted(p.name for p in (self.v.root / "system/staging").iterdir()), before)
        self.assertFalse(self.post("/api/chase/pane", {"id": "../../etc"})["ok"])


class PolishHelp(VaultCase):
    """Polish in the pane (Alan, 13-10-2026, option A): the kind "polish-help" for Alan's own item rewords the opening and suggests
    To get … done and What I need from you. The model gets the opening, the item's own wording, its latest update, his two lines
    and the tone, never the table, subject or addresses; anyone else's item and a decision are refused (they use "polish")."""
    OPENING = "I've been asked to follow up with you on the back-to-back commercials, to get the commercials agreed."

    def drafts(self, cmd, body):
        r = subprocess.run([sys.executable, "system/scripts/drafts.py", cmd], input=json.dumps(body), capture_output=True, text=True,
                           cwd=self.v.root, env={**os.environ, "CREAITE_NOW": NOW})
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def context(self, **req):
        return self.drafts("context", {"kind": "polish-help", "id": self.mine, "text": self.OPENING, "tone": "warm",
                                       "outcome": "the commercials agreed", "need": "Your sign-off.", **req})

    def test_the_prompt_holds_the_opening_the_item_and_the_two_lines_only(self):
        c = self.context()
        self.assertEqual((c["kind"], c["feature"]), ("polish-help", "email"))
        p = c["prompt"]
        self.assertIn("in a warm tone", p)
        for words in (self.OPENING, "Reach out to Dana on back-to-back commercials", "Tom asked for the commercials to mirror the Kestrel Group terms",
                      "To get … done, as Alan has it: the commercials agreed", "What I need from you, as Alan has it: Your sign-off."):
            self.assertIn(words, p)
        for never in ("[ABC]", "Your help with", "@", "19-10-2026", "2026-10-19", "Good morning", "Could you let me know by"):
            self.assertNotIn(never, p)                                  # no subject, address, table row or the rest of the email
        self.assertEqual([s["kind"] for s in c["sources"]], ["paragraph", "item", "update", "outcome", "need"])

    def test_someone_elses_item_a_decision_and_a_confidential_line_are_refused(self):
        for item in (self.theirs, self.decision):
            self.assertIn("only for your own items", self.context(id=item)["refused"])
        self.assertIn("confidential or restricted", self.context(need="The restricted board pack.")["refused"])
        self.assertIn("closed", self.context(id=self.closed)["refused"])
        self.assertEqual(self.context(text="")["nothing"], "There is no opening to polish.")

    def test_the_reply_is_parsed_and_checked(self):
        c = self.context()
        reply = ("TEXT: I'm picking up the back-to-back commercials and want them agreed. [S1, S2]\n"
                 "OUTCOME: to get the Northgate commercials agreed on the Kestrel Group terms.\n"
                 "NEED: Tell me whether the terms can mirror Kestrel Group by 20-10-2026")
        out = self.drafts("result", {"request": {"kind": "polish-help"}, "context": c, "reply": reply})
        self.assertEqual(out["text"], "I'm picking up the back-to-back commercials and want them agreed.")
        self.assertEqual(out["sentences"][0]["refs"], ["S1", "S2"])
        self.assertEqual(out["outcome"], "the Northgate commercials agreed on the Kestrel Group terms")       # reads after "to get", no full stop
        self.assertEqual(out["need"], "Tell me whether the terms can mirror Kestrel Group by 20-10-2026.")
        self.assertEqual((out["original"], out["was_outcome"], out["was_need"]), (self.OPENING, "the commercials agreed", "Your sign-off."))
        self.assertEqual(out["notes"], ["The What I need from you mentions 20-10-2026, which the item doesn't give."])
        stats = json.loads((self.v.root / "system/staging/draft-stats.json").read_text())
        self.assertGreaterEqual(stats["email"]["offered"], 1)                                    # counted with the Draft email's Polish

    def test_a_missing_line_is_noted_and_yours_kept(self):
        c = self.context()
        out = self.drafts("result", {"request": {"kind": "polish-help"}, "context": c, "reply": "TEXT: A new opening. [S1]"})
        self.assertEqual((out["text"], out["outcome"], out["need"]), ("A new opening.", "", ""))
        self.assertEqual(out["notes"], ["No To get … done came back, so yours is kept.", "No What I need from you came back, so yours is kept."])

    def test_the_live_server_keeps_the_two_lines_and_knows_the_kind(self):
        sys.path.insert(0, str(REPO / "system/scripts"))
        import live_server
        self.assertIn("polish-help", live_server.DRAFT_KINDS)
        got = live_server.draft_request({"kind": "polish-help", "id": "ABC-A-001", "text": "x" * 2000, "tone": "firm",
                                         "outcome": "y" * 400, "need": "z" * 600, "to": "Dana"})
        self.assertEqual((len(got["text"]), len(got["outcome"]), len(got["need"]), got["tone"]), (1500, 300, 500, "firm"))


if __name__ == "__main__":
    unittest.main()
