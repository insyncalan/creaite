"""Tests for v2.1.0 P4 (BL-338): the minutes record (minutes_record.py, minutes.py stage) and dates in words (date_words.py).

Run: python3 dev/tests/test_minutes_record.py      (quick tier: no Chrome; the parser's agreement with the dashboard needs Node)
Each test builds a throwaway vault (test_tracker.Vault) and runs the real scripts there, with a fictional meeting: the time tags
(VTT cue times, else speaker turns), the exact source line, the coverage actions with Undo, and deadlines in words worked out from
the meeting's date, by the scripts' parser and the dashboard's (core/datewords.js), which must agree word for word.
"""
import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import ABC, REPO, Vault  # noqa: E402
from test_plain_dates import ACCEPTED, FRI, REFUSED, SAT, WED  # noqa: E402

sys.path.insert(0, str(REPO / "system" / "scripts"))
import date_words  # noqa: E402

DAY, TITLE = "2026-10-14", "[ABC] Steering committee"          # a Wednesday
DRAFT = "system/staging/drafts/2026-10-14 Steering committee.html"
FILED = f"{ABC}/minutes/2026-10-14 Steering committee.html"
VTT = """WEBVTT

NOTE
Title: Steering committee

00:00:01.000 --> 00:00:05.000
<v Alan Carter>Morning all, first the SOW.</v>

00:00:05.000 --> 00:00:09.000
<v Alan Carter>And then the harbour migration.</v>

00:00:09.000 --> 00:00:15.000
<v Jane Doe>We agreed the pilot stays on the lighthouse site.</v>

00:00:15.000 --> 00:00:21.000
<v Omar Ali>I'll send the revised SOW next week. Data access is late.</v>
"""
TXT = "Alan Carter: Morning all.\nOmar Ali: I'll send the SOW by Friday.\nJane Doe: Agreed.\n"
AGENDA = "# Steering committee\n\n- SOW sign-off\n- Training plan\n- Budget review\n"


def minutes(**extra):
    """The record's content, as cx-minutes writes it."""
    return {"start": "10:00", "end": "11:00", "attendees": "Jane Doe (Example Client Ltd); Alan Carter, Omar Ali (Brightwater)",
            "summary": [{"text": "The committee reviewed the SOW.", "turn": 1}, "Data access remains the main risk."],
            "updates": [{"heading": "SOW", "items": [{"text": "Omar is revising the SOW.", "at": "00:00:17"},
                                                     {"flag": "PRIORITY", "text": "Sign-off is needed first.", "turn": 2}]},
                        {"heading": "Pilot", "items": [{"flag": "BOGUS", "text": "The pilot stays put.", "at": "00:00:12.400"}]}],
            "open_questions": ["Who owns the cut-over extract? Raised by Alan Carter; unresolved"], **extra}


def spec(transcript="inbox/2026-10-14 Steering committee.vtt", **extra):
    v = {"project": "ABC"}
    return {"title": TITLE, "date": DAY, "projects": ["ABC"], "transcript": transcript, "minutes": minutes(),
            "items": [
                {"table": "actions", "turn": 3, "due_words": "next week",
                 "values": {**v, "description": "Send the revised SOW to the client", "owner": "Omar Ali"}},
                {"table": "actions", "values": {**v, "description": "Book the UAT environment", "owner": "Alan Carter"},
                 "due_words": "whenever"},
                {"table": "decisions", "at": "00:00:10", "values": {**v, "decision": "The pilot stays on the lighthouse site",
                                                                      "made_by": "Jane Doe"}},
                {"table": "raid", "values": {**v, "type": "Risk", "description": "Data access late → the MVP slips"}},
            ], **extra}


class Base(unittest.TestCase):
    def setUp(self):
        self.now = os.environ.get("CREAITE_NOW")
        os.environ["CREAITE_NOW"] = "2026-10-14 12:00"           # creaite's clock: the draft is made on the meeting's day
        self.v = Vault()
        self.v.run("init")
        (self.v.root / "inbox/2026-10-14 Steering committee.vtt").write_text(VTT, encoding="utf-8")

    def tearDown(self):
        self.v.cleanup()
        if self.now is None:
            os.environ.pop("CREAITE_NOW", None)
        else:
            os.environ["CREAITE_NOW"] = self.now

    def stage(self, ok=True, **kw):
        f = self.v.root / "system/staging/drafts/meeting.json"
        f.write_text(json.dumps(kw.pop("whole", None) or spec(**kw)), encoding="utf-8")
        return self.v.run("stage", str(f), script="minutes.py", ok=ok)

    def proposal(self):
        p = next((self.v.root / "system/staging").glob("proposed-*.json"))
        return p, json.loads(p.read_text(encoding="utf-8"))

    def py(self, code, ok=True):
        r = subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts')\n" + code],
                           cwd=self.v.root, capture_output=True, text=True)
        if ok:
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        return r.stdout

    def js(self, code):
        return json.loads(self.py(code).strip().splitlines()[-1])

    def doc(self, path=DRAFT):
        return self.js(f"import creaite_doc\nprint(json.dumps(creaite_doc.read({path!r})))")

    def section(self, doc, sid):
        return next(s for s in doc["sections"] if s["id"] == sid)

    def change(self, op, ok=True):
        return self.js("import minutes_record\n"
                       f"try:\n    r = minutes_record.change({DRAFT!r}, {op!r})\n"
                       "except minutes_record.RecordError as e:\n    r = {'ok': False, 'message': str(e)}\n"
                       "r.pop('doc', None)\nprint(json.dumps(r))")


class Record(Base):
    def test_stage_drafts_the_record_with_the_style_sections_and_files_it_as_html(self):
        out = self.stage().stdout
        self.assertIn(f"Draft minutes: {DRAFT}", out)
        _, data = self.proposal()
        m = data["meeting"]
        self.assertEqual(m["draft"], DRAFT)
        self.assertIn({"op": "copy", "from": "draft", "to": FILED}, m["file_ops"])
        self.assertEqual(data["items"][0]["values"]["source"], f"{FILED} — Action Items")
        doc = self.doc()
        self.assertEqual((doc["kind"], doc["title"], doc["date"], doc["project_name"]),
                         ("minutes", "Steering committee", DAY, "Example Programme"))
        self.assertEqual([s["id"] for s in doc["sections"]],
                         ["header", "summary", "updates", "decisions", "raid", "actions", "open_questions", "source"])
        self.assertIn("Draft, generated by creaite on 14 October 2026. Not yet reviewed.", self.section(doc, "header")["text"])
        self.assertIn("**Attendees:** Jane Doe (Example Client Ltd)", self.section(doc, "header")["text"])
        upd = self.section(doc, "updates")
        self.assertIn("**SOW**\n- Omar is revising the SOW.\n- **PRIORITY** Sign-off is needed first.", upd["text"])
        self.assertIn("- The pilot stays put.", upd["text"])            # a flag that isn't one of the ten is dropped
        actions = self.section(doc, "actions")["rows"]
        self.assertEqual([r["ref"] for r in actions], ["@1", "@2"])
        self.assertEqual(actions[0]["cells"], {"owner": "Omar Ali", "action": "Send the revised SOW to the client",
                                               "due": "23-10-2026"})
        self.assertEqual(actions[0]["does"], "New action")
        self.assertEqual(self.section(doc, "raid")["rows"][0]["does"], "New risk")
        self.assertEqual(sorted(doc["items"]), ["@1", "@2", "@3", "@4"])
        self.assertEqual(doc["meta"]["proposal"], self.proposal()[0].name)
        self.assertFalse((self.v.root / "system/staging/drafts/meeting.json").exists())     # BL-118: the spec has done its job

    def test_time_tags_follow_the_vtt_cue_times(self):
        self.stage()
        doc = self.doc()
        self.assertTrue(doc["meta"]["timed"])
        self.assertEqual(doc["meta"]["turns"], 3)                    # Alan's two cues are one turn
        tags = self.section(doc, "summary")["tags"]
        self.assertEqual(tags, [{"ref": "transcript", "turn": 1, "time": "00:00:01", "text": "The committee reviewed the SOW."}])
        upd = {t["text"]: (t["turn"], t["time"]) for t in self.section(doc, "updates")["tags"]}
        self.assertEqual(upd, {"Omar is revising the SOW.": (3, "00:00:17"), "Sign-off is needed first.": (2, "00:00:09"),
                               "The pilot stays put.": (2, "00:00:12")})
        self.assertEqual(self.section(doc, "actions")["rows"][0]["at"], {"turn": 3, "time": "00:00:15"})
        self.assertEqual(self.section(doc, "decisions")["rows"][0]["at"], {"turn": 2, "time": "00:00:10"})
        self.assertNotIn("at", self.section(doc, "actions")["rows"][1])
        page = self.js("import creaite_doc\nprint(json.dumps(creaite_doc.render(creaite_doc.read(%r), editing=False)))" % DRAFT)
        self.assertNotIn("00:00:1", page)                            # tags are creaite's only: never on the page or an export
        self.assertIn("Send the revised SOW to the client", page)

    def test_without_cue_times_the_tags_are_speaker_turns(self):
        (self.v.root / "inbox/2026-10-14 Steering committee.txt").write_text(TXT, encoding="utf-8")
        s = spec(transcript="inbox/2026-10-14 Steering committee.txt")
        s["minutes"]["summary"] = [{"text": "Omar will send the SOW.", "turn": 2}, {"text": "Timed line", "at": "00:00:05"}]
        self.stage(whole=s)
        doc = self.doc()
        self.assertFalse(doc["meta"]["timed"])
        self.assertEqual(self.section(doc, "summary")["tags"],
                         [{"ref": "transcript", "turn": 2, "time": None, "text": "Omar will send the SOW."}])
        turns = self.js("import minutes_record\nprint(json.dumps(minutes_record.turns('inbox/2026-10-14 Steering committee.txt')))")
        self.assertEqual([t["who"] for t in turns["turns"]], ["Alan Carter", "Omar Ali", "Jane Doe"])

    def test_the_source_line_names_the_meeting_exactly(self):
        self.stage()
        self.assertEqual(self.section(self.doc(), "source")["text"],
                         "Teams transcript and meeting chat, Steering committee, 14 October 2026, 10:00–11:00 (UAE time)")
        lines = self.js("import minutes_record as m\nprint(json.dumps([m.source_line('[ABC] Weekly', '2026-09-30', '12:00', '13:05',"
                        " chat=False), m.source_line('Weekly', '2026-09-30'), m.source_line('Weekly', '2026-09-30', '12:00', None,"
                        " partial=True)]))")
        self.assertEqual(lines, ["Teams transcript, Weekly, 30 September 2026, 12:00–13:05 (UAE time)",
                                 "Teams transcript and meeting chat, Weekly, 30 September 2026",
                                 "Teams transcript and meeting chat, Weekly, 30 September 2026, 12:00 (UAE time). "
                                 "The transcript ends before the meeting does."])

    def test_a_record_is_never_refreshed_from_word(self):
        self.stage()
        r = self.v.run("refresh", self.proposal()[0].name, script="minutes.py", ok=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("edited in creaite", r.stdout)

    def test_a_record_with_a_word_draft_too_is_refused(self):
        s = spec()
        s["draft"] = "system/staging/drafts/x.docx"
        r = self.stage(ok=False, whole=s)
        self.assertEqual(r.returncode, 1)
        self.assertIn("without a Word", r.stdout)
        self.assertEqual(list((self.v.root / "system/staging").glob("proposed-*.json")), [])


class Deadlines(Base):
    def test_words_are_worked_out_from_the_meetings_date(self):
        wed, fri = "2026-10-14", "2026-10-16"
        cases = [("Friday", wed, "2026-10-16"), ("by Friday", wed, "2026-10-16"), ("friday", fri, "2026-10-23"),
                 ("next week", wed, "2026-10-23"), ("next week", fri, "2026-10-23"), ("next week", "2026-10-18", "2026-10-23"),
                 ("Next Wednesday", wed, "2026-10-21"), ("next wed", "2026-10-12", "2026-10-21"),
                 ("end of month", wed, "2026-10-30"), ("end of month", "2026-05-04", "2026-05-29"), ("eom", "2026-02-02", "2026-02-27"),
                 ("in 2 weeks", wed, "2026-10-28"), ("in 3 days", "2026-10-15", "2026-10-19"), ("+2d", "2026-10-15", "2026-10-16"),
                 ("30-10", wed, "2026-10-30"), ("10-10", wed, "2027-10-10"), ("30-10-2026", wed, "2026-10-30"),
                 ("tomorrow", wed, "2026-10-15"), ("not set", wed, None), ("", wed, None), ("whenever", wed, None)]
        for words, day, want in cases:
            self.assertEqual(date_words.parse(words, day, True, "deadline"), want, (words, day))
        self.assertEqual(date_words.parse("end of month", "2026-10-14", True, "deadline", (5, 6)), "2026-10-29")   # Fri–Sat weekend
        self.assertEqual(date_words.said("2026-10-23"), "Friday 23-10-2026")

    def test_stage_sets_the_date_and_says_it_was_read_from_words(self):
        out = self.stage().stdout
        _, data = self.proposal()
        a, b = data["items"][0], data["items"][1]
        self.assertEqual(a["values"]["due_date"], "2026-10-23")
        self.assertEqual(a["inferred"], [{"field": "due_date", "why": "said “next week”, from the meeting's date"}])
        self.assertNotIn("due_date", b["values"])
        self.assertIn("no-due-date", b["flags"])
        self.assertIn("deadline \"whenever\" isn't a date creaite can read; left Not set", out)
        self.assertEqual(self.section(self.doc(), "actions")["rows"][1]["cells"]["due"], "Not set")

    def test_a_deadline_typed_in_words_on_a_row(self):
        self.stage()
        r = self.change({"op": "deadline", "n": 2, "words": "end of month"})
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["message"], "Item 2 changed; due Friday 30-10-2026.")
        self.assertEqual(self.proposal()[1]["items"][1]["values"]["due_date"], "2026-10-30")
        self.assertEqual(self.section(self.doc(), "actions")["rows"][1]["cells"]["due"], "30-10-2026")
        self.assertEqual(self.doc()["version"], r["version"])
        bad = self.change({"op": "deadline", "n": 2, "words": "soonish"})
        self.assertFalse(bad["ok"])
        self.assertIn("isn't a date creaite can read", bad["message"])

    @unittest.skipUnless(shutil.which("node"), "needs Node")
    def test_the_dashboard_and_the_scripts_agree(self):
        module = (REPO / "system/templates/dashboard/src/core/datewords.js").as_uri()
        words = [(t, d, u, "") for t, d, u, _ in ACCEPTED] + [(t, SAT, True, "") for t in REFUSED]
        for mode in ("", "deadline"):
            for day in (SAT, WED, FRI, "2026-10-12", "2026-01-31", "2026-02-03", "2026-12-31", "2026-05-04"):
                for t in ("next week", "end of month", "eom", "next wed", "next sun", "by fri", "on monday", "in 2 weeks", "+3d",
                          "in 1 month", "3 days", "30-10", "1-1", "end of week", "end of next week", "fri", "today", "15 oct",
                          "oct 15", "16-10-26", "2026-10-16", "nonsense", "", "29-02", "+", "next month"):
                    words.append((t, day, mode == "deadline", mode))
        script = (f"import {{parseWords}} from {json.dumps(module)};\n"
                  f"const W={json.dumps(words)};\n"
                  "console.log(JSON.stringify(W.map(([t,d,u,m])=>[parseWords(t,d,u,m), parseWords(t,d,u,m,[5,6])])));")
        r = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        js = json.loads(r.stdout)
        py = [[date_words.parse(t, d, u, m), date_words.parse(t, d, u, m, (5, 6))] for t, d, u, m in words]
        self.assertEqual(len(js), len(py))
        for w, a, b in zip(words, js, py):
            self.assertEqual(a, b, w)

    def test_the_scripts_read_the_dashboards_own_forms(self):
        for text, today, due, want in ACCEPTED:
            self.assertEqual(date_words.parse(text, today, due), want, (text, today, due))
        for text in REFUSED:
            self.assertIsNone(date_words.parse(text, SAT, True), text)


class Coverage(Base):
    def setUp(self):
        super().setUp()
        ag = self.v.root / ABC / "agendas"
        ag.mkdir(parents=True, exist_ok=True)
        (ag / "2026-10-14 Steering committee agenda.md").write_text(AGENDA, encoding="utf-8")
        cal = {"fetched": "2026-10-14 08:00", "days": {"2026-10-28": [{"start": "10:00", "end": "11:00", "title": "[ABC] Steering committee"}]}}
        (self.v.root / "system/staging/calendar.json").write_text(json.dumps(cal), encoding="utf-8")
        s = spec()
        s["coverage"] = [{"point": "SOW sign-off", "verdict": "Covered"}, {"point": "Training plan", "verdict": "Not discussed"},
                         {"point": "Budget review", "verdict": "Touched on"}]
        self.stage(whole=s)

    def carried(self):
        f = self.v.root / "system/staging/carried.json"
        return [c["point"] for c in json.loads(f.read_text())["points"]] if f.exists() else []

    def test_coverage_is_kept_in_creaite_only(self):
        doc = self.doc()
        self.assertEqual([(c["point"], c["verdict"]) for c in doc["meta"]["coverage"]],
                         [("SOW sign-off", "Covered"), ("Training plan", "Not discussed"), ("Budget review", "Touched on")])
        self.assertNotIn("not_covered", [s["id"] for s in doc["sections"]])

    def test_carry_it_to_the_next_meeting_with_a_line_then_undo(self):
        r = self.change({"op": "cover", "point": "Training plan", "how": "carry"})
        self.assertTrue(r["ok"], r)
        self.assertEqual(self.carried(), ["Training plan"])
        doc = self.doc()
        self.assertEqual([s["id"] for s in doc["sections"]][-2:], ["not_covered", "source"])
        self.assertEqual(self.section(doc, "not_covered")["text"],
                         "- Training plan was not discussed; it is carried to the next Steering committee on 28 October 2026.")
        self.assertEqual(doc["meta"]["coverage"][1]["action"]["how"], "carry")
        again = self.change({"op": "cover", "point": "Training plan", "how": "drop"})
        self.assertIn("undo that first", again["message"])
        self.assertTrue(self.change({"op": "uncover", "point": "training plan"})["ok"])
        self.assertEqual(self.carried(), [])
        self.assertNotIn("not_covered", [s["id"] for s in self.doc()["sections"]])

    def test_a_separate_session_adds_an_action_for_alan_due_friday(self):
        self.change({"op": "cover", "point": "Budget review", "how": "session"})
        _, data = self.proposal()
        new = data["items"][-1]
        self.assertEqual((new["n"], new["table"], new["decision"]), (5, "actions", "pending"))
        self.assertEqual(new["values"]["owner"], "Alan Carter")
        self.assertEqual(new["values"]["due_date"], "2026-10-16")              # the Friday after the meeting
        self.assertEqual(new["values"]["description"], "Set up a separate session on Budget review")
        self.assertEqual(new["values"]["source"], f"{FILED} — Not covered in this meeting")
        doc = self.doc()
        self.assertEqual(self.section(doc, "actions")["rows"][-1]["ref"], "@5")
        self.assertIn("Budget review was not discussed; a separate session will be set up.", self.section(doc, "not_covered")["text"])
        self.change({"op": "uncover", "point": "Budget review"})
        self.assertEqual(len(self.proposal()[1]["items"]), 4)
        self.assertEqual([r["ref"] for r in self.section(self.doc(), "actions")["rows"]], ["@1", "@2"])

    def test_dropping_a_point_can_leave_the_minutes_alone(self):
        self.change({"op": "cover", "point": "Training plan", "how": "drop", "line": False})
        self.change({"op": "cover", "point": "Budget review", "how": "enough"})
        doc = self.doc()
        self.assertEqual(self.section(doc, "not_covered")["text"], "- Budget review was covered enough.")
        self.assertEqual(doc["meta"]["coverage"][1]["action"], {"how": "drop", "line": ""})
        self.assertIn("isn't on this meeting's agenda", self.change({"op": "cover", "point": "Lunch", "how": "drop"})["message"])


if __name__ == "__main__":
    unittest.main()
