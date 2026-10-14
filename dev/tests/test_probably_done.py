"""BL-218 (sprint-drafts-extraction): "Probably done". The sweep and the minutes find the open items a sent mail, a reply, a Teams message
or a meeting passage may show finished (plain code), the skill judges them, and stage proposes a closing update with the evidence.
Never closes anything by itself: a closing update is approved on its own.

Run: python3 dev/tests/test_probably_done.py
No model is called: the skill's judgement is written into the spec by the test.
"""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import Vault, action  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from split_dashboard import readable_page  # noqa: E402

NOW = "2026-10-09 16:00"
SENT = ("Email · From: Alan Carter <alan@brightwater.example> · Subject: [ABC] Revised SOW · Sent: 2026-10-09 15:02 · "
        "Link: https://outlook.office365.com/owa/?ItemID=pd1")
STRANGER = ("Email · From: Bob Stone <bob@elsewhere.example> · Subject: SOW · Sent: 2026-10-09 15:30 · "
            "Link: https://outlook.office365.com/owa/?ItemID=pd2")
TEAMS = "Teams · Chat: ABC core · From: Sara Example · Sent: 2026-10-09 14:00 · Link: https://teams.microsoft.com/l/message/pd3"


class Base(unittest.TestCase):
    """A vault with two open actions, and the helpers that read candidates and stage a sweep."""
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.cleanup)
        self.v.run("init")
        self.v.propose("seed", [
            action(1, description="Send the revised SOW to the client", owner="Alan Carter", raised="2026-10-01"),
            action(2, description="Book the UAT environment for the migration", owner="Sara Example", raised="2026-10-01")])
        self.v.run("apply")
        self.sow, self.uat = (a["id"] for a in self.v.rows("actions"))

    def run_(self, script, *args, ok=True):
        r = subprocess.run([sys.executable, str(self.v.root / "system/scripts" / script), *args], cwd=self.v.root,
                           env={**os.environ, "CREAITE_NOW": NOW}, capture_output=True, text=True)
        if ok and r.returncode not in (0, 3):
            raise AssertionError(f"{script} {args}: {r.stdout}{r.stderr}")
        return r

    def candidates(self, *messages):
        f = self.v.root / "system/staging/drafts/messages.json"
        f.write_text(json.dumps({"messages": list(messages)}))
        out = json.loads(self.run_("sweep.py", "done-candidates", str(f)).stdout)
        self.assertFalse(f.exists())                                      # BL-118: read, so removed
        return out["candidates"]

    def stage(self, *items):
        spec = self.v.root / "system/staging/drafts/sweep.json"
        spec.write_text(json.dumps({"window": {"start": "2026-10-09 08:00", "end": NOW}, "items": list(items)}))
        out = self.run_("sweep.py", "stage", str(spec)).stdout
        props = sorted((self.v.root / "system/staging").glob("proposed-*-sweep*.json"))
        return out, (props[-1] if props else None)

    def done(self, item_id, source=SENT, **d):
        return {"op": "update", "table": "actions", "id": item_id, "source": source,
                "done": {"strength": "Looks done", "quote": "Hi Jane, attached the revised SOW for the client.", "folder": "Sent Items",
                         **d}}

    def number(self, prop, ref):
        rows = json.loads(self.run_("review.py", "list", "--json").stdout)
        return next(r["n"] for r in rows if r["file"] == prop.name and r["ref"] == ref)


class ProbablyDone(Base):
    def test_a_sent_mail_closes_the_matching_item_with_evidence(self):
        found = self.candidates({"source": SENT, "folder": "Sent Items", "from": "Alan Carter <alan@brightwater.example>",
                                 "to": ["Jane Doe <jane.doe@client.com>"], "sent": "2026-10-09 15:02",
                                 "text": "Hi Jane, attached the revised SOW for the client.", "attachments": ["Revised SOW v3.docx"]})
        self.assertEqual([c["id"] for c in found[0]["candidates"]], [self.sow])
        self.assertEqual(found[0]["candidates"][0]["hint"], "Looks done")
        out, prop = self.stage(self.done(self.sow))
        self.assertIn("Probably done: 1", out)
        it = json.loads(prop.read_text())["items"][0]
        self.assertEqual((it["op"], it["id"], it["changes"]["status"]), ("update", self.sow, "Closed"))
        self.assertIn("attached the revised SOW", it["changes"]["latest_update"])
        self.assertEqual(it["suggested"]["strength"], "Looks done")
        self.assertEqual(it["suggested"]["evidence"]["kind"], "mail")
        self.assertTrue(it["why"].startswith("Looks done: Mail 09-10-2026 15:02"), it["why"])
        self.assertEqual(self.v.rows("actions")[0]["status"], "Open")      # nothing closed by itself
        self.run_("review.py", "approve", str(self.number(prop, 1)))
        self.run_("tracker.py", "apply")
        self.assertEqual(next(a for a in self.v.rows("actions") if a["id"] == self.sow)["status"], "Closed")
        st = json.loads((self.v.root / "system/staging/draft-stats.json").read_text())["done"]
        self.assertEqual((st["offered"], st["used"]), (1, 1))

    def test_an_item_in_another_project_is_refused(self):
        out, prop = self.stage(self.done(self.sow, project="DEF"))
        self.assertIn("only the item's own project", out)
        self.assertIsNone(prop)

    def test_an_unrelated_mail_proposes_nothing(self):
        self.assertEqual(self.candidates({"source": SENT, "folder": "Inbox", "from": "Jane Doe <jane.doe@client.com>",
                                          "sent": "2026-10-09 12:00", "text": "Lunch on Friday? The usual place is booked."}), [])

    def test_a_stranger_cannot_close_an_item(self):
        out, prop = self.stage(self.done(self.uat, source=STRANGER, folder="Inbox",
                                         quote="The UAT environment for the migration is booked."))
        self.assertIn("isn't from its owner or Alan", out)
        self.assertIsNone(prop)

    def test_teams_counts_a_little_less(self):
        _, prop = self.stage(self.done(self.uat, source=TEAMS, folder="Teams", who="Sara Example",
                                       quote="UAT environment for the migration is booked, done."))
        it = json.loads(prop.read_text())["items"][0]
        self.assertEqual(it["suggested"]["strength"], "Maybe done")
        self.assertIn("low-confidence", it["flags"])

    def test_a_closing_update_is_not_covered_by_approve_routine_and_the_reject_reason_is_stored(self):
        _, prop = self.stage(self.done(self.sow))
        self.run_("review.py", "bulk")
        self.assertEqual(json.loads(prop.read_text())["items"][0]["decision"], "pending")
        self.run_("review.py", "reject", str(self.number(prop, 1)), "--reason=Not sent yet")
        self.run_("tracker.py", "apply")
        self.assertEqual([r["reason"] for r in self.v.rows("rejected")], ["Not sent yet"])
        self.assertEqual(self.v.rows("actions")[0]["status"], "Open")
        st = json.loads((self.v.root / "system/staging/draft-stats.json").read_text())["done"]
        self.assertEqual(st["rejected"], 1)

    def test_not_done_re_dates_the_item(self):
        _, prop = self.stage(self.done(self.sow, strength="Not done", quote="The SOW is delayed to next week.", due_date="2026-10-16"))
        it = json.loads(prop.read_text())["items"][0]
        self.assertEqual(it["changes"], {"due_date": "2026-10-16"})

    def test_switched_off_it_stages_nothing(self):
        cfg = self.v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text())
        data["drafting"] = {"done": False}
        cfg.write_text(json.dumps(data))
        out, prop = self.stage(self.done(self.sow))
        self.assertIn("probably done is off", out)
        self.assertIsNone(prop)

    def test_a_meeting_passage_is_a_candidate_and_its_update_carries_the_evidence(self):
        t = self.v.root / "inbox/weekly.vtt"
        t.write_text("WEBVTT\n\n00:01.000 --> 00:05.000\n<v Sara Example>The UAT environment for the migration is booked now, done.</v>\n")
        found = json.loads(self.run_("minutes.py", "done-candidates", "ABC", str(t)).stdout)["candidates"]
        self.assertEqual((found[0]["id"], found[0]["speaker"]), (self.uat, "Sara Example"))
        (self.v.root / "system/staging/drafts/w.docx").write_bytes((self.v.root / "system/templates/minutes-template.docx").read_bytes())
        spec = self.v.root / "system/staging/drafts/meeting.json"
        spec.write_text(json.dumps({"title": "ABC weekly", "date": "2026-10-09", "projects": ["ABC"],
                                    "draft": "system/staging/drafts/w.docx", "transcript": "inbox/weekly.vtt", "items": [
                                        {"op": "update", "table": "actions", "id": self.uat, "set": {"status": "Closed"},
                                         "why": "Sara said it is booked", "section": "Actions",
                                         "done": {"strength": "Looks done", "quote": found[0]["quote"], "who": "Sara Example"}}]}))
        self.run_("minutes.py", "stage", str(spec))
        prop = next(p for p in (self.v.root / "system/staging").glob("proposed-*.json") if "sweep" not in p.name)
        it = json.loads(prop.read_text())["items"][0]
        self.assertEqual((it["suggested"]["strength"], it["suggested"]["evidence"]["kind"]), ("Looks done", "meeting"))
        self.assertTrue(it["why"].startswith("Looks done: Said in the meeting"), it["why"])


class ProbablyKept(Base):
    """BL-125 A, decision 10 (Alan, 13-10-2026): open promises are scanned too, by the same rules. A kept one becomes Done,
    and, being a probably-done guess, is approved on its own (decision 6's routine Done is for a plain update)."""
    EXTRACT = "Send the data extract for the migration"

    def setUp(self):
        super().setUp()
        self.v.propose("promises", [{"n": 1, "op": "new", "table": "promises", "match": "strong", "flags": [], "decision": "approved",
                                     "values": {"project": "ABC", "promised_by": "Sara Example", "promised_to": "Alan Carter",
                                                "description": self.EXTRACT, "raised": "2026-10-02", "due_date": "2026-10-08",
                                                "source": "projects/x/minutes/2026-10-02 Steering.docx — Actions"}}])
        self.v.run("apply")
        self.pid = self.v.rows("promises")[0]["id"]

    def sweep_promises(self, on):
        cfg = self.v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text())
        data["promises"] = {"from_sweep": on}
        cfg.write_text(json.dumps(data))

    def kept(self, **d):
        return {"op": "update", "table": "promises", "id": self.pid, "source": TEAMS,
                "done": {"strength": "Looks done", "quote": f"{self.pid}: sent the data extract for the migration, here it is.",
                         "folder": "Teams", "who": "Sara Example", **d}}

    def message(self):
        return {"source": TEAMS, "folder": "Teams", "from": "Sara Example", "sent": "2026-10-09 14:00",
                "text": "Sent the data extract for the migration, here it is."}

    def test_a_meeting_passage_shows_a_promise_kept(self):
        t = self.v.root / "inbox/weekly.vtt"
        t.write_text("WEBVTT\n\n00:01.000 --> 00:05.000\n<v Sara Example>I sent the data extract for the migration yesterday, done.</v>\n")
        found = json.loads(self.run_("minutes.py", "done-candidates", "ABC", str(t)).stdout)["candidates"]
        hit = next(c for c in found if c["id"] == self.pid)
        self.assertEqual((hit["table"], hit["owner"], hit["hint"]), ("promises", "Sara Example", "Looks done"))
        (self.v.root / "system/staging/drafts/w.docx").write_bytes((self.v.root / "system/templates/minutes-template.docx").read_bytes())
        spec = self.v.root / "system/staging/drafts/meeting.json"
        spec.write_text(json.dumps({"title": "ABC weekly", "date": "2026-10-09", "projects": ["ABC"],
                                    "draft": "system/staging/drafts/w.docx", "transcript": "inbox/weekly.vtt", "items": [
                                        {"op": "update", "table": "promises", "id": self.pid, "set": {"status": "Done"},
                                         "why": "Sara said she sent it", "section": "Actions",
                                         "done": {"strength": "Looks done", "quote": hit["quote"], "who": "Sara Example"}}]}))
        self.run_("minutes.py", "stage", str(spec))
        prop = next(p for p in (self.v.root / "system/staging").glob("proposed-*.json") if "sweep" not in p.name)
        it = json.loads(prop.read_text())["items"][0]
        self.assertEqual((it["changes"], it["suggested"]["strength"]), ({"status": "Done"}, "Looks done"))
        self.assertTrue(it["why"].startswith("Looks done: Said in the meeting"), it["why"])
        rows = json.loads(self.run_("review.py", "list", "--json").stdout)
        self.assertEqual(next(r for r in rows if r["file"] == prop.name and r["ref"] == 1)["why"], "closing update")

    def test_the_sweep_scans_promises_only_while_its_promises_are_on(self):
        self.assertNotIn(self.pid, json.dumps(self.candidates(self.message())))     # off by default: not even a candidate
        out, prop = self.stage(self.kept())
        self.assertIn("promises from the sweep are off", out)
        self.assertIsNone(prop)
        self.sweep_promises(True)
        found = self.candidates(self.message())
        self.assertIn(self.pid, [c["id"] for c in found[0]["candidates"]])
        out, prop = self.stage(self.kept())
        it = json.loads(prop.read_text())["items"][0]
        self.assertEqual((it["table"], it["changes"]), ("promises", {"status": "Done"}))   # no latest update on a promise
        self.assertEqual(it["suggested"]["strength"], "Looks done")                       # Teams naming its ID
        self.run_("review.py", "bulk")
        self.assertEqual(json.loads(prop.read_text())["items"][0]["decision"], "pending")   # a guess: one by one
        self.run_("review.py", "approve", str(self.number(prop, 1)))
        self.run_("tracker.py", "apply")
        self.assertEqual(self.v.rows("promises")[0]["status"], "Done")

    def test_a_stranger_cannot_mark_a_promise_kept(self):
        self.sweep_promises(True)
        out, prop = self.stage({**self.kept(), "source": STRANGER,
                                "done": {"strength": "Looks done", "quote": "The data extract for the migration was sent.",
                                         "folder": "Inbox"}})
        self.assertIn("isn't from its owner or Alan", out)                # only Sara (who made it) or Alan
        self.assertIsNone(prop)


class Page(unittest.TestCase):
    def test_review_leads_with_the_strength_and_the_evidence(self):
        repo = Path(__file__).resolve().parents[2]
        page = readable_page()     # BL-231: the source; the bundle reprints the code
        self.assertIn("function dnHtml(r)", page)
        self.assertIn("(r.dn?dnHtml(r):\"\")", page)
        self.assertIn('r["dn"]', (repo / "system/scripts/build_dashboard.py").read_text())


if __name__ == "__main__":
    unittest.main()
