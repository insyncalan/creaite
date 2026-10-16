"""Confidential mail in an alert gets a real summary (Alan, 15-10-2026; plan #17), never in client output.

Run: python3 dev/tests/test_vip_confidential.py
A throwaway vault with fictional people and data (never Microsoft 365). A confidential conversation from a followed person
keeps Claude's own summary and candidate items, marked "confidential": true, with no message text and no attachment names;
Today shows the summary with a quiet "Confidential" mark and never the word VIP (BL-288). A work item made from it is never
client-visible (whatever the form sends) and carries the Sensitive label, so neither the summary nor the item reaches a client
report or a client-safe steerco one-pager built for that project. A private conversation keeps its neutral line, and an
ordinary one is unchanged.
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
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_reports import ReportVault, populate  # noqa: E402
from test_sweep_alerts import REGISTER, run, vip_file  # noqa: E402
from test_vip_conversations import CHAT, SECRET, vault  # noqa: E402

NOW = "2026-10-09 13:00"
GIST = "Budget holder asks to pause the second-phase hiring until the board meets"
ACT = "Prepare a hiring pause options note"
DEC = "Second-phase hiring waits for the board"
CONF = {**CHAT, "conversation": "19:chat-conf@thread.v2", "sensitivity": "confidential", "summary": GIST,
        "attachments": ["Board pack draft.pptx"], "last": "2026-10-08 08:40",
        "items": [{"type": "action", "text": ACT, "owner": "Mia Hale", "due": "2026-10-20"},
                  {"type": "decision", "text": DEC, "owner": None, "due": None}]}


def record(v, found, now, how="sweep"):
    f = v.root / "system/staging/drafts/found.json"
    f.write_text(json.dumps(found))
    return run(v, "sweep.py", "vip", "record", str(f), "--found", how, now=now).stdout


def make(v, aid, cand, values=None, kind=None):
    """sweep.vip_make, as /api/alerts/make calls it, in the throwaway vault."""
    code = ("import json, sys; sys.path.insert(0, 'system/scripts'); import sweep; "
            f"print(json.dumps(sweep.vip_make({aid!r}, {kind!r}, {values!r}, {cand!r})))")
    r = subprocess.run([sys.executable, "-c", code], cwd=v.root, capture_output=True, text=True,
                       env={**os.environ, "CREAITE_NOW": NOW})
    if r.returncode:
        raise AssertionError(r.stdout + r.stderr)
    return json.loads(r.stdout.strip().splitlines()[-1])


class ConfidentialRecordTests(unittest.TestCase):
    """The record: a real summary for a confidential conversation; private and ordinary ones as before."""

    def setUp(self):
        self.v = vault()

    def tearDown(self):
        self.v.cleanup()

    def test_a_confidential_conversation_keeps_a_real_summary_marked_confidential(self):
        record(self.v, [{**CONF, "body": SECRET, "messages": [{"text": SECRET}]}], "2026-10-08 09:30")
        a = vip_file(self.v)["alerts"][0]
        self.assertEqual((a["summary"], a["marker"], a.get("confidential")), (GIST, "confidential", True))
        self.assertEqual(a["gist"], GIST[:140])
        self.assertEqual([c["text"] for c in a["candidates"]], [ACT, DEC])
        self.assertEqual(a["title"], "Project Falcon go-live")
        self.assertEqual(a["p"], "ABC")                                                      # matched, as for any other
        self.assertEqual(a["attachments"], [])                                               # internal only: no file names
        self.assertFalse(a["quiet"])
        text = (self.v.root / "system/staging/vip.json").read_text()
        self.assertNotIn(SECRET, text)                                                       # never message text
        self.assertNotIn("Board pack", text)

    def test_an_old_placeholder_is_not_shown_as_a_summary(self):
        record(self.v, [{**CONF, "summary": "private", "items": []}], "2026-10-08 09:30")
        a = vip_file(self.v)["alerts"][0]
        self.assertEqual((a["summary"], a.get("confidential")), ("", True))

    def test_a_private_conversation_still_keeps_only_a_neutral_line(self):
        record(self.v, [{**CONF, "sensitivity": "private"}], "2026-10-08 09:30")
        a = vip_file(self.v)["alerts"][0]
        self.assertEqual((a["summary"], a["candidates"], a["marker"], a["p"]), ("private conversation", [], "private", None))
        self.assertNotIn("confidential", a)

    def test_an_ordinary_conversation_is_unchanged(self):
        record(self.v, [CHAT], "2026-10-08 09:30")
        a = vip_file(self.v)["alerts"][0]
        self.assertIsNone(a["marker"])
        self.assertNotIn("confidential", a)
        self.assertTrue(a["summary"].startswith("Mia's team will take the solution"))

    def test_the_old_message_shape_marks_a_confidential_message(self):
        record(self.v, [{"kind": "mail", "from": CHAT["from"], "subject": "Budget", "sent": "2026-10-08 08:50",
                         "link": "https://x/c1", "gist": GIST, "sensitivity": "confidential"}], "2026-10-08 09:30")
        a = vip_file(self.v)["alerts"][0]
        self.assertEqual((a["gist"], a["marker"], a.get("confidential")), (GIST, "confidential", True))


class ConfidentialClientOutputTests(unittest.TestCase):
    """Nothing from a confidential alert reaches client output: a made item is not client-visible and is labelled Sensitive;
    the client report and the client-safe one-pager for the project never carry the summary or the item."""

    @classmethod
    def setUpClass(cls):
        cls.v = v = ReportVault()
        populate(v)
        (v.root / "projects/_portfolio/people-register.md").write_text(REGISTER)
        (v.root / "system/staging/drafts").mkdir(parents=True, exist_ok=True)
        record(v, [CONF, {**CHAT, "last": "2026-10-08 08:30"}], NOW)
        alerts = vip_file(v)["alerts"]
        cls.conf = next(a for a in alerts if a.get("confidential"))
        cls.plain = next(a for a in alerts if not a.get("confidential"))
        cls.made_a = make(v, cls.conf["id"], 1, {"client_visible": 1, "client_message": "x"})   # the form can't make it client-visible
        cls.made_d = make(v, cls.conf["id"], 2)
        cls.made_plain = make(v, cls.plain["id"], 1)
        for f in (v.root / "system/staging").glob("proposed-*-dashboard*.json"):          # Alan approves them in Review
            spec = json.loads(f.read_text())
            for it in spec["items"]:
                it["decision"] = "approved"
            f.write_text(json.dumps(spec))
        v.run("apply")

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def item(self, table, head, text):
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            con.row_factory = sqlite3.Row
            row = con.execute(f"SELECT * FROM {table} WHERE {head} = ?", (text,)).fetchone()
            labels = [r[0] for r in con.execute("SELECT label FROM item_labels WHERE item_id = ?", (row["id"],))]
        return dict(row), labels

    def test_a_made_item_is_not_client_visible_and_is_labelled_sensitive(self):
        for made in (self.made_a, self.made_d):
            v = made["values"]
            self.assertEqual((v["client_visible"], v["labels"]), (0, ["Sensitive"]))
            self.assertNotIn("client_message", v)
        row, labels = self.item("actions", "description", ACT)
        self.assertEqual((row["client_visible"], labels), (0, ["Sensitive"]))
        row, labels = self.item("decisions", "decision", DEC)
        self.assertEqual((row["client_visible"], labels), (0, ["Sensitive"]))

    def test_an_item_made_from_an_ordinary_alert_is_unchanged(self):
        v = self.made_plain["values"]
        self.assertNotIn("labels", v)
        self.assertNotIn("client_visible", v)
        row, labels = self.item("actions", "description", v["description"])
        self.assertEqual((row["client_visible"], labels), (0, []))

    def test_the_client_report_never_carries_the_summary_or_the_item(self):
        data = self.v.at("client-data", "ABC", "--since", "2026-10-01", script="report.py").stdout
        f = self.v.root / "system/staging/drafts/client.json"
        f.write_text(json.dumps({"code": "ABC", "period_start": "2026-10-01", "summary": ["Phase two is being prepared."],
                                 "progress": ["Plan revised"], "next_steps": ["Sign the statement of work"],
                                 "input_needed": ["Signature by 16-10"]}))
        out = self.v.at("client-stage", str(f), script="report.py").stdout
        prop = next((self.v.root / "system/staging").glob("proposed-*-client-ABC.json"))
        text = self.v.run("text", str(self.v.root / json.loads(prop.read_text())["report"]["draft"]), script="docx_tools.py").stdout
        for said in (data, out, text):
            for secret in (GIST, ACT, DEC, "Budget holder", "hiring"):
                self.assertNotIn(secret, said)

    def test_the_client_safe_one_pager_never_carries_them_and_the_internal_one_marks_them(self):
        f = self.v.root / "system/staging/drafts/steerco.json"
        for version in ("client", "internal"):
            f.write_text(json.dumps({"code": "ABC", "version": version, "force": True}))     # past the client report in Review
            r = subprocess.run([sys.executable, str(self.v.root / "system/scripts/report.py"), "steerco-stage", str(f)],
                               cwd=self.v.root, env={**os.environ, "CREAITE_NOW": NOW}, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            spec = json.loads(sorted((self.v.root / "system/staging").glob("proposed-2*-steerco*.json"))[-1].read_text())
            with zipfile.ZipFile(self.v.root / spec["report"]["draft"]) as z:
                text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", z.read("word/document.xml").decode("utf-8")))
            for secret in (GIST, "Budget holder"):
                self.assertNotIn(secret, text + r.stdout)                                  # the summary: never in a document
            if version == "client":
                for secret in (ACT, DEC, "hiring"):
                    self.assertNotIn(secret, text + r.stdout)
            else:
                self.assertIn(f"{ACT} [Sensitive]", text)                                  # internal: there, marked


ASK = "Tell the board chair the hiring pause is agreed"
WHY = "Budget holder wants the hiring pause logged against the statement of work"
CONF4 = {**CONF, "conversation": "19:chat-conf4@thread.v2", "type": "action", "ask": ASK, "due": "2026-10-20",
         "owners": ["Mia Hale", "you"], "match": {"id": "", "relation": "update", "why": WHY}}


def py(v, code):
    r = subprocess.run([sys.executable, "-c", "import json, sys; sys.path.insert(0, 'system/scripts'); import sweep\n" + code],
                       cwd=v.root, capture_output=True, text=True, env={**os.environ, "CREAITE_NOW": NOW})
    if r.returncode:
        raise AssertionError(r.stdout + r.stderr)
    return r.stdout.strip()


class ConfidentialThreadFieldsTests(unittest.TestCase):
    """Part 4 of BL-342: a confidential card keeps its type, ask, due date, owners and matched item (words only, internal) and
    the match's reason is neutralised; a private card keeps none; a Log click stages only the neutral line, and the wording of
    the ask and the reason is in no staged proposal, client report, one-pager or database row, even for a client-visible item."""

    @classmethod
    def setUpClass(cls):
        cls.v = v = ReportVault()
        populate(v)
        (v.root / "projects/_portfolio/people-register.md").write_text(REGISTER)
        (v.root / "system/staging/drafts").mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(v.root / "system/tracker.db")) as con:
            cls.item, = con.execute("SELECT id FROM actions WHERE description = 'Sign the statement of work'").fetchone()
            cls.visible = con.execute("SELECT client_visible FROM actions WHERE id = ?", (cls.item,)).fetchone()[0]
        record(v, [{**CONF4, "match": {**CONF4["match"], "id": cls.item}},
                   {**CONF, "conversation": "19:chat-priv@thread.v2", "sensitivity": "private", "ask": ASK, "due": "2026-10-20",
                    "owners": ["Mia Hale"], "match": {"id": cls.item, "relation": "update", "why": WHY}}], NOW)
        alerts = vip_file(v)["alerts"]
        cls.conf = next(a for a in alerts if a.get("confidential"))
        cls.priv = next(a for a in alerts if a.get("marker") == "private")
        cls.logged = json.loads(py(v, f"print(json.dumps(sweep.vip_log({cls.conf['id']!r})))"))

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def test_the_item_is_client_visible(self):
        self.assertEqual(self.visible, 1)                                                    # the worst case for a leak

    def test_a_confidential_card_keeps_type_ask_due_owners_and_the_match(self):
        a = self.conf
        self.assertEqual((a["type"], a["ask"], a["due"], a["owners"]), ("action", ASK, "2026-10-20", ["Mia Hale", "you"]))
        self.assertEqual((a["match"]["id"], a["match"]["relation"]), (self.item, "update"))
        self.assertEqual(a["summary"], GIST)

    def test_the_matchs_reason_is_neutralised_for_a_confidential_card_only(self):
        self.assertEqual(self.conf["match"]["why"], "The thread moves it forward.")
        self.assertNotIn(WHY, json.dumps(self.conf))
        self.assertTrue(self.conf["match"]["t"])                                             # the item's title is the tracker's

    def test_a_private_card_keeps_none_of_the_new_fields(self):
        a = self.priv
        self.assertEqual((a["type"], a["ask"], a["due"], a["owners"]), (None, "", None, []))
        self.assertNotIn("match", a)
        self.assertNotIn(ASK, json.dumps(a))

    def test_log_stages_only_the_neutral_line(self):
        self.assertRegex(self.logged["line"], r"^Discussed in a confidential thread, \d\d-10-2026$")
        specs = [f.read_text() for f in (self.v.root / "system/staging").glob("proposed-*.json")]
        self.assertTrue(any(self.item in t for t in specs))
        for text in specs:
            for secret in (ASK, WHY, GIST, "Budget holder", "hiring", "Board pack", SECRET, "Budget talk", "Falcon"):
                self.assertNotIn(secret, text)

    def test_nothing_reaches_a_client_report_a_one_pager_or_the_database(self):
        for f in (self.v.root / "system/staging").glob("proposed-*-dashboard*.json"):       # Alan approves the Log in Review
            spec = json.loads(f.read_text())
            for it in spec["items"]:
                it["decision"] = "approved"
            f.write_text(json.dumps(spec))
        self.v.run("apply")
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            row = con.execute("SELECT latest_update, client_visible FROM actions WHERE id = ?", (self.item,)).fetchone()
            dump = "\n".join(con.iterdump())
        self.assertIn("Discussed in a confidential thread", row[0])
        self.assertEqual(row[1], 1)
        data = self.v.at("client-data", "ABC", "--since", "2026-10-01", script="report.py").stdout
        said = [dump, data]
        f = self.v.root / "system/staging/drafts/steerco4.json"
        for version in ("client", "internal"):
            f.write_text(json.dumps({"code": "ABC", "version": version, "force": True}))
            r = subprocess.run([sys.executable, str(self.v.root / "system/scripts/report.py"), "steerco-stage", str(f)],
                               cwd=self.v.root, env={**os.environ, "CREAITE_NOW": NOW}, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            spec = json.loads(sorted((self.v.root / "system/staging").glob("proposed-2*-steerco*.json"))[-1].read_text())
            with zipfile.ZipFile(self.v.root / spec["report"]["draft"]) as z:
                said.append(re.sub(r"<[^>]+>", " ", z.read("word/document.xml").decode("utf-8")) + r.stdout)
        for text in said:
            for secret in (ASK, WHY, GIST, "Budget holder", "hiring pause", "Board pack"):
                self.assertNotIn(secret, text)


class ConfidentialPageTests(unittest.TestCase):
    """Today: the confidential card shows its summary and a "Confidential" mark; an ordinary card has none; no VIP."""

    @classmethod
    def setUpClass(cls):
        from test_insight import chrome
        cls.v = v = vault()
        today = date.today().isoformat()
        record(v, [{**CONF, "last": f"{today} 08:40", "type": "action", "ask": ASK, "due": "2026-10-20",
                    "owners": ["Mia Hale", "you"]}, {**CHAT, "last": f"{today} 08:30"}], f"{today} 09:30")
        run(v, "build_dashboard.py")
        probe = """const out={}; go("today"); renderToday();
          const cards=[...document.querySelectorAll('#tdList>li.td-message')];
          out.cards=cards.map(li=>({t:li.querySelector('.t').textContent, mark:(li.querySelector('.tdmark')||{}).textContent||"",
            sum:(li.querySelector('.tdsum')||{}).textContent||"", ask:(li.querySelector('.tdask')||{}).textContent||"",
            who:(li.querySelector('.tdwho')||{}).textContent||"", tag:(li.querySelector('.tdtag')||{}).textContent||"", cands:li.querySelectorAll('.tdcand').length,
            cls:(li.querySelector('.tdmark')||{className:""}).className}));
          out.page=document.getElementById('tdList').textContent; window.OUT=out;"""
        cls.out, cls.errors = chrome(v, probe, "vip-conf")

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def test_the_confidential_card_shows_the_summary_and_the_mark(self):
        self.assertEqual(self.errors, [])
        self.assertIsNotNone(self.out)
        self.assertNotIn("error", self.out, self.out)
        cards = self.out["cards"]
        self.assertEqual(len(cards), 2, cards)
        conf = next(c for c in cards if c["sum"] == GIST)
        self.assertEqual(conf["mark"], "Confidential")
        self.assertIn("tag tdctag", conf["cls"])                                             # the existing quiet tag style
        self.assertEqual(conf["cands"], 2)
        self.assertEqual(conf["tag"], "Action")                                              # the new chips sit beside the mark
        self.assertIn(ASK, conf["ask"])
        self.assertIn("Mia Hale, you", conf["who"])
        self.assertIn("20th October", conf["who"])
        plain = next(c for c in cards if c["sum"] != GIST)
        self.assertEqual(plain["mark"], "")
        self.assertNotIn("confidential conversation", self.out["page"])
        self.assertNotRegex(self.out["page"], r"\bVIPs?\b")                                  # BL-288


if __name__ == "__main__":
    unittest.main()
