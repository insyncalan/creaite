"""#366 (review kit, slice A): calendar content never reaches a client output. Fictional data; no browser (quick tier).

Run: python3 dev/tests/test_calendar_client_outputs.py

Protects: a meeting the sweep saved to system/staging/calendar.json (title, place, organiser, body, attendee and attachment names,
and a join link, meeting ID, passcode and dial-in in the body) is never copied into anything a client is handed:
  - the client report (the draft, its HTML and Word exports, the filed report);
  - the client-safe Steerco one-pager (`report.py steerco-data` and the Word file `steerco-stage` makes);
  - the AI drafts' client-audience facts (status form for a client, the Draft email polish, client wording of one item).
A confidential meeting keeps only its title and times in calendar.json, a private one is "Busy": their details (place, organiser, body,
attendees, attachments, recurrence) are in no saved file and in no client output either. The follow-up email's facts do carry the
invite's attendees, by design (the meeting's own follow-up, never a client report); that is recorded here, not treated as a leak.
No client output builder reads calendar.json today, so tests 2 to 4 (client report, Steerco, AI draft contexts) are tripwires: they
fail only if a builder starts reading the calendar. The outputs that really read the calendar are the agenda (the meeting's Prep
page) and the follow-up email (test 5).
Source: the review kit's probe `k26-b-outputs` (dev/proposals/review-kit/src/k26/b232.py on team-cap-reviewkit-26d), made to run
on current main with CREAITE_NOW pinned and no kit shim.
"""
import json
import os
import subprocess
import sys
import unittest
import zipfile
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_reports import NOW, ReportRoutes  # noqa: E402  (the class's harness only: no browser)

WEEK = "2026-10-09"
CAN = ["KITBODYCANARY", "Quentin Canary", "q.canary@client.example", "KITATTACH", "KITTITLECANARY", "KITORGCANARY", "KITPLACECANARY"]
HELD = ["KITCONFBODY", "KITCONFATT", "KITCONFPLACE", "KITCONFORG", "KITCONFATTACH", "KITCONFREC", "c@client.example",
        "KITPRIVBODY", "KITPRIVPLACE", "KITPRIVTITLE"]
JOIN = ["KITJOINTOKEN", "Zq7rTpass", "852 1234 5678", "85212345678", "+44 20 7946 0000", "teams.example"]
BODY = ("KITBODYCANARY roadmap and budget talk\nJoin: https://teams.example/l/meetup-join/KITJOINTOKEN\n"
        "Meeting ID: 852 1234 5678\nPasscode: Zq7rTpass\nDial in: +44 20 7946 0000,,85212345678#")


def text_of(p):
    """A file's text; a Word, Excel or PowerPoint file is read member by member."""
    p = Path(p)
    if p.suffix in (".docx", ".pptx", ".xlsx"):
        with zipfile.ZipFile(p) as z:
            return "".join(z.read(n).decode("utf-8", "ignore") for n in z.namelist() if n.endswith(".xml"))
    return p.read_text(encoding="utf-8", errors="ignore")


class CalendarClientOutputs(unittest.TestCase):
    """The report routes on a live server in a throwaway vault (test_reports.ReportRoutes' harness, without its tests)."""
    setUpClass = classmethod(ReportRoutes.setUpClass.__func__)
    tearDownClass = classmethod(ReportRoutes.tearDownClass.__func__)
    post, section = ReportRoutes.post, ReportRoutes.section

    @property
    def reports(self):
        return self.v.root / "projects/ABC Example Programme/reports"

    def env(self):
        return {**os.environ, "CREAITE_NOW": NOW}

    def cmd(self, script, *args, stdin=None):
        return subprocess.run([sys.executable, f"system/scripts/{script}", *args], cwd=self.v.root, capture_output=True, text=True,
                              input=stdin, env=self.env(), timeout=240)

    def plant(self):
        day = (date.fromisoformat(NOW[:10]) + timedelta(days=1)).isoformat()
        events = [
            {"id": "o1", "start": "09:00", "end": "10:00", "title": "KITTITLECANARY ABC steering", "where": "KITPLACECANARY room",
             "organiser": "KITORGCANARY Person", "teams": True, "sensitivity": "normal", "body": BODY, "attachments": ["KITATTACH-plan.docx"],
             "attendees": [{"name": "Quentin Canary", "email": "q.canary@client.example"}]},
            {"id": "o2", "start": "11:00", "end": "12:00", "title": "ABC board", "where": "KITCONFPLACE Room", "organiser": "KITCONFORG Person",
             "teams": True, "sensitivity": "confidential", "body": "KITCONFBODY roadmap", "attachments": ["KITCONFATTACH.docx"],
             "recurrence": "KITCONFREC weekly", "attendees": [{"name": "KITCONFATT Person", "email": "c@client.example"}]},
            {"id": "o3", "start": "13:00", "end": "13:30", "title": "KITPRIVTITLE dentist", "where": "KITPRIVPLACE", "sensitivity": "private",
             "body": "KITPRIVBODY"},
        ]
        spec = self.v.root / "system/staging/drafts/calendar.json"
        spec.parent.mkdir(parents=True, exist_ok=True)
        spec.write_text(json.dumps({"days": {day: events}}), encoding="utf-8")
        r = self.cmd("sweep.py", "calendar", str(spec))
        cal = self.v.root / "system/staging/calendar.json"
        self.assertTrue(cal.is_file(), r.stdout + r.stderr)
        return cal.read_text(encoding="utf-8")

    def client_draft(self):
        """A saved client draft whose internal week is approved (the same steps as the report routes' own tests)."""
        r = self.post("/api/report/draft", {"kind": "weekly", "code": "ABC", "week_ending": WEEK})
        self.assertTrue(r["ok"], r)
        self.section(r["doc"], "health")["text"] = "UAT start slipped two weeks."
        self.assertTrue(self.post("/api/report/save", {"doc": r["doc"], "base_version": r["version"]})["ok"])
        a = self.post("/api/report/approve", {"kind": "weekly", "code": "ABC", "week_ending": WEEK, "force": True})
        self.assertTrue(a["ok"] or "awaiting review" in a["message"], a)
        r = self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": WEEK})
        self.assertTrue(r["ok"], r)
        self.assertTrue(self.post("/api/report/save", {"doc": r["doc"], "base_version": r["version"]})["ok"])
        return r

    def assert_clean(self, name, text, needles=None):
        low = text.lower()
        left = [n for n in (needles or CAN + HELD + JOIN) if n.lower() in low]
        self.assertEqual(left, [], f"{name} holds calendar content: {left}")

    def test_calendar_json_keeps_no_join_detail_and_held_meetings_keep_nothing(self):
        cal = self.plant()
        self.assertIn("KITTITLECANARY", cal, "control: the ordinary meeting was saved")
        self.assert_clean("calendar.json", cal, JOIN + HELD)

    def test_client_report_draft_exports_and_filed_report(self):
        self.plant()
        self.reports.mkdir(parents=True, exist_ok=True)
        for f in self.reports.glob("*"):
            if f.is_file():
                f.unlink()
        self.client_draft()
        draft = self.v.root / "system/staging/drafts"
        outs = {f.name: text_of(f) for f in draft.glob("*Client report*") if f.is_file()}
        for fmt in ("html", "docx"):
            e = self.post("/api/report/export", {"kind": "client", "code": "ABC", "week_ending": WEEK, "fmt": fmt, "on_clash": "number"})
            self.assertTrue(e.get("ok"), e)
            outs["export." + fmt] = text_of(self.v.root / e["path"])
        a = self.post("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "force": True})
        if a.get("ok"):
            for f in self.reports.glob("*Client report*"):
                outs["filed " + f.name] = text_of(f)
        self.assertGreaterEqual(len(outs), 3, f"the client outputs were made: {sorted(outs)}")
        for name, text in outs.items():
            self.assertGreater(len(text), 200, f"control: {name} has content")
            self.assert_clean(name, text)

    def test_client_steerco_data_and_word_one_pager(self):
        self.plant()
        data = self.cmd("report.py", "steerco-data", "ABC", "--version", "client")
        self.assertEqual(data.returncode, 0, data.stdout + data.stderr)
        self.assertGreater(len(data.stdout), 100, "control: facts were produced")
        self.assert_clean("steerco-data (client)", data.stdout)
        spec = self.v.root / "system/staging/drafts/steerco.json"
        spec.write_text(json.dumps({"code": "ABC", "version": "client", "summary": ["The programme is on course."]}), encoding="utf-8")
        s = self.cmd("report.py", "steerco-stage", str(spec))
        made = list((self.v.root / "system/staging/drafts").glob("*Steerco one-pager*"))
        self.assertTrue(made, "steerco-stage made a file: " + (s.stdout + s.stderr)[-200:])
        for f in made:
            self.assert_clean(f.name, text_of(f))

    def test_client_audience_ai_draft_contexts(self):
        self.plant()
        cases = (("status form for a client", {"kind": "status-form", "code": "ABC", "form": "email", "audience": "client", "length": "short"}),
                 ("polish", {"kind": "polish", "text": "Dear team, a short update on the programme.", "tone": "warm"}),
                 ("client wording of an item", {"kind": "client", "id": "ABC-A-003"}))
        for label, req in cases:
            p = self.cmd("drafts.py", "context", stdin=json.dumps(req))
            self.assertEqual(p.returncode, 0, f"{label}: {p.stdout}{p.stderr}")
            self.assertGreater(len(p.stdout), 20, f"control: {label} has content")
            self.assert_clean("drafts context: " + label, p.stdout)

    def test_followup_facts_carry_the_invites_attendees_by_design(self):
        """Information, not a leak: the meeting's own follow-up email names who was invited; no client report does."""
        self.plant()
        code = ("import sys, json; sys.path.insert(0,'system/scripts')\nimport drafts\n"
                "print(json.dumps(drafts.followup_facts({'eid':'o1'})))")
        fu = subprocess.run([sys.executable, "-c", code], cwd=self.v.root, capture_output=True, text=True, env=self.env(), timeout=120)
        self.assertEqual(fu.returncode, 0, fu.stdout + fu.stderr)
        facts = fu.stdout
        self.assert_clean("follow-up facts", facts, JOIN + HELD)       # even there: no join detail, no held meeting
        self.assertIn("Quentin", facts, "the attendee is named for the follow-up (by design)")


del ReportRoutes                      # imported for its harness only: unittest must not collect its tests here


if __name__ == "__main__":
    unittest.main()
