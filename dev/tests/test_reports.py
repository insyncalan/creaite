"""Tests for report.py and the report checks in review.py (cx-weekly-report, cx-client-report).

Run: python3 dev/tests/test_reports.py
The clock is fixed (CREAITE_NOW) to Friday 09-10-2026 13:00; the data is fictional.
"""
import json
import os
import re
import subprocess
import sys
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_dashboard import png  # noqa: E402
from test_tracker import ABC, Vault  # noqa: E402

NOW = "2026-10-09 13:00"
CLIENT_MSG = ("What it is: The signed statement of work.\nWhat it means for you: Work can start on phase two.\n"
              "What is being done: Legal review is under way.")


def new(table, n, **values):
    return {"n": n, "op": "new", "table": table, "values": values, "match": "strong", "flags": [], "decision": "approved"}


def edit_docx(path, old, new_text):
    with zipfile.ZipFile(path) as z:
        parts = {i: z.read(i.filename) for i in z.infolist()}
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for info, raw in parts.items():
            if info.filename == "word/document.xml":
                text = raw.decode("utf-8")
                assert old in text, old
                raw = text.replace(old, new_text, 1).encode("utf-8")
            z.writestr(info, raw)


class ReportVault(Vault):
    def at(self, *args, script, ok=True):
        r = subprocess.run([sys.executable, str(self.root / "system/scripts" / script), *args],
                           env={**os.environ, "CREAITE_NOW": NOW}, cwd=self.root, capture_output=True, text=True)
        if ok and r.returncode != 0:
            raise AssertionError(f"{script} {args}: {r.stdout}{r.stderr}")
        return r


def populate(v):
    v.run("init")
    (v.root / ABC / "images").mkdir(exist_ok=True)
    (v.root / ABC / "images/plan.png").write_bytes(png(300, 150, (11, 110, 127)))
    (v.root / ABC / "CLAUDE.md").write_text(
        "# ABC — Example Programme\n\n## Brief\n\n- **Client / partner:** Example Client Ltd\n"
        "- **Client report rhythm:** weekly\n\n## Sensitivities\n\n- Budget overrun on phase one is being absorbed (Client-safe: no)\n\n"
        "## Current state\n\n_Rewritten weekly._\n\nBuild is two weeks behind.\n\n![Delivery plan](images/plan.png)\n")
    src = f"{ABC}/minutes/2026-10-06 Steering.docx — Action Items"
    v.propose("seed", [
        new("milestones", 1, project="ABC", name="UAT start", baseline_date="2026-10-20", forecast_date="2026-11-03",
            source="s"),
        new("actions", 2, project="ABC", description="Escalate data access to the client CIO", owner="Alan Carter",
            due_date="2026-09-25", raised="2026-09-20", source=src),
        new("actions", 3, project="ABC", description="Sign the statement of work", owner="Jane Doe (Example Client Ltd)",
            due_date="2026-10-16", raised="2026-10-06", client_visible=1, client_message=CLIENT_MSG, source=src),
        new("actions", 4, project="ABC", description="Send the revised plan", owner="Alan Carter", due_date="2026-10-14",
            raised="2026-10-06", client_visible=1, client_message=CLIENT_MSG.replace("signed statement of work",
                                                                                     "revised delivery plan"), source=src),
        new("actions", 5, project="ABC", description="Confirm tester names", owner="Omar Ali (Example Client Ltd)",
            raised="2026-10-06", client_visible=0, source=src),
        new("raid", 6, project="ABC", type="Risk", description="Vendor exits the market before go-live",
            impact="High", likelihood="High", raised="2026-10-01", source=src),
        new("raid", 7, project="ABC", type="Issue", description="Test licences not ordered", impact="Medium",
            likelihood="High", raised="2026-10-05", client_visible=1,
            client_message="What it is: Test licences are not yet ordered.\nWhat it means for you: Testing could start late.\n"
                           "What is being done: Purchase order raised this week.", source=src),
        new("decisions", 8, project="ABC", decision="Go-live stays on 20 November", made_by="Steering committee",
            date="2026-10-06", client_visible=1, client_message="Go-live remains on 20 November.", source=src),
        new("decisions", 9, project="ABC", decision="Absorb the phase one overrun internally", made_by="Alan Carter",
            date="2026-10-07", source=src),
    ])
    v.run("apply")


class WeeklyTests(unittest.TestCase):
    def setUp(self):
        self.v = ReportVault()
        populate(self.v)

    def tearDown(self):
        self.v.cleanup()

    def spec(self, **extra):
        f = self.v.root / "system/staging/drafts/weekly.json"
        f.write_text(json.dumps({"code": "ABC", "health": "At risk", "health_reason": "UAT start slipped 14 days",
                                 "summary": ["UAT start has slipped two weeks.", "Escalation is planned."],
                                 "key_changes": "UAT start moved", "current_state": "Recovery plan agreed with the client.",
                                 "progress": ["Plan revised"], "next_week": ["Escalate data access"],
                                 "help_needed": ["Sponsor support with the CIO"], **extra}))
        return str(f)

    def test_weekly_data_and_health_criteria(self):
        d = json.loads(self.v.at("weekly-data", "ABC", script="report.py").stdout)
        self.assertEqual((d["week_ending"], d["week_start"]), ("2026-10-09", "2026-10-05"))
        self.assertEqual(d["suggested_health"], "At risk")
        self.assertTrue(any("ABC-A-001" in r and "more than 7 days" in r for r in d["reasons"]))
        self.assertTrue(any("UAT start moved 14 days" in r for r in d["reasons"]))
        self.assertEqual([r["id"] for r in d["top_risks"]], ["ABC-005", "ABC-006"])          # Urgent first
        self.assertEqual([x["id"] for x in d["decisions"]], ["ABC-D-007", "ABC-D-008"])
        self.assertEqual(d["blocked"], 0)
        self.assertFalse(d["quiet_week"])

    def test_blocked_by_pending_items(self):
        self.v.propose("pending", [{**new("actions", 1, project="ABC", description="Pending", raised="2026-10-08",
                                          source="s"), "decision": "pending"}])
        r = self.v.at("weekly-stage", self.spec(), script="report.py", ok=False)
        self.assertEqual(r.returncode, 3)
        self.assertIn("Example Programme has 1 item awaiting review — review first.", r.stdout)

    def test_weekly_report_end_to_end(self):
        out = self.v.at("weekly-stage", self.spec(), script="report.py").stdout
        self.assertIn("Health: At risk — UAT start slipped 14 days", out)
        prop = next((self.v.root / "system/staging").glob("proposed-*-weekly-ABC.json"))
        data = json.loads(prop.read_text())
        self.assertEqual([i["table"] for i in data["items"]], ["updates", "projects"])
        ops = [o["op"] for o in data["report"]["file_ops"]]
        self.assertEqual(ops, ["write", "copy", "remove"])
        draft = self.v.root / data["report"]["draft"]
        text = self.v.run("text", str(draft), script="docx_tools.py").stdout
        for expected in ("Example Programme\nWeekly Report", "Week ending 9 October 2026", "AT RISK   UAT start slipped 14 days",
                         "UAT start | 03-11-2026 | 20-10-2026 | — | Slipped",   # no linked actions, none set; BL-186: the five states
                         "ABC-A-001 | Escalate data access to the client CIO | Alan Carter | 25-09-2026",
                         "ABC-005 | Risk: Vendor exits the market before go-live | Urgent | TBC", "Delivery plan"):
            self.assertIn(expected, text)
        with zipfile.ZipFile(draft) as z:
            self.assertTrue(any(n.startswith("word/media/creaite-") for n in z.namelist()))   # the image (BL-12)
        # approve: the report and its items (an unlabelled draft is fine, BL-121), then apply
        self.v.run("list", script="review.py")
        listed = json.loads(self.v.run("list", "--json", script="review.py").stdout)
        nums = sorted({r["n"] for r in listed})
        out = self.v.run("approve", ",".join(map(str, nums)), script="review.py").stdout
        self.assertNotIn("labelled", out)                                                                  # BL-121: no label asked for
        self.assertIn(f"Approved {len(nums)}.", out)
        self.v.run("apply")
        filed = self.v.root / ABC / "reports/2026-10-09 Weekly report - Example Programme.docx"
        self.assertRegex(self.v.run("text", str(filed), script="docx_tools.py").stdout, r"Approved by Alan on \d+ \w+ 2026")
        self.assertEqual(self.v.rows("updates")[0]["health"], "At risk")
        abc = next(p for p in self.v.rows("projects") if p["code"] == "ABC")
        self.assertEqual((abc["health"], abc["health_reason"]), ("At risk", "UAT start slipped 14 days"))
        memory = (self.v.root / ABC / "CLAUDE.md").read_text()
        self.assertIn("Recovery plan agreed with the client.", memory)
        self.assertIn("![Delivery plan](images/plan.png)", memory)                          # image line kept
        self.assertNotIn("Build is two weeks behind.", memory)
        r = self.v.at("weekly-stage", self.spec(), script="report.py", ok=False)
        self.assertIn("already filed", r.stdout)
        session = self.v.at("start", "--force", script="session.py").stdout
        self.assertNotIn("Weekly report for week ending 09-10-2026", session)              # reminder satisfied

    def test_edited_weekly_draft_syncs(self):
        self.v.at("weekly-stage", self.spec(), script="report.py")
        prop = next((self.v.root / "system/staging").glob("proposed-*-weekly-ABC.json"))
        draft = self.v.root / json.loads(prop.read_text())["report"]["draft"]
        edit_docx(draft, "UAT start has slipped two weeks.", "UAT start has slipped two weeks; recovery is on track.")
        listed = json.loads(self.v.run("list", "--json", script="review.py").stdout)
        n = next(r["n"] for r in listed if r["ref"] == "report")
        out = self.v.run("approve", str(n), script="review.py").stdout
        self.assertIn("Summary: draft says", out)
        self.assertIn("Approved 1.", self.v.run("approve", str(n), "--sync", script="review.py").stdout)
        data = json.loads(prop.read_text())
        self.assertIn("recovery is on track", data["items"][0]["values"]["summary"])

    def test_formatted_current_state(self):
        """BL-22: Markdown in Current state becomes bold runs and list paragraphs in Word; unedited, it isn't a difference."""
        md = "Recovery plan **agreed**.\n\n- Data access by *Friday*\n- UAT on masked data\n\n1. Escalate\n2. Re-plan"
        self.v.at("weekly-stage", self.spec(current_state=md), script="report.py")
        prop = next((self.v.root / "system/staging").glob("proposed-*-weekly-ABC.json"))
        data = json.loads(prop.read_text())
        self.assertEqual(data["report"]["current_state"], md)
        draft = self.v.root / data["report"]["draft"]
        text = self.v.run("text", str(draft), script="docx_tools.py").stdout
        for line in ("Recovery plan agreed.", "• Data access by Friday", "• UAT on masked data", "1. Escalate", "2. Re-plan"):
            self.assertIn(line + "\n", text)
        with zipfile.ZipFile(draft) as z:
            xml = z.read("word/document.xml").decode()
        self.assertRegex(xml, r"<w:b/>[^<]*</w:rPr><w:t[^>]*>agreed</w:t>")
        self.assertRegex(xml, r"<w:i/>[^<]*</w:rPr><w:t[^>]*>Friday</w:t>")
        self.assertIn('<w:ind w:left="360" w:hanging="360"/>', xml)
        listed = json.loads(self.v.run("list", "--json", script="review.py").stdout)
        n = next(r["n"] for r in listed if r["ref"] == "report")
        out = self.v.run("approve", str(n), script="review.py").stdout
        self.assertNotIn("Current state: draft says", out)
        self.assertIn("Approved 1.", out)

    def test_milestone_percent_in_report(self):
        """BL-29: a % complete Alan set shows in the weekly report's milestones table."""
        ms = next(m for m in self.v.rows("milestones") if m["name"] == "UAT start")
        self.v.propose("pc", [{"n": 1, "op": "update", "table": "milestones", "id": ms["id"], "decision": "approved",
                               "match": "strong", "flags": [], "changes": {"percent_complete": 40}}])
        self.v.run("apply")
        self.v.at("weekly-stage", self.spec(), script="report.py")
        draft = next((self.v.root / "system/staging/drafts").glob("* Weekly report - Example Programme.docx"))
        self.assertIn("UAT start | 03-11-2026 | 20-10-2026 | 40% | Slipped",
                      self.v.run("text", str(draft), script="docx_tools.py").stdout)

    def test_fuller_formats_in_word(self):
        """BL-47: sub-heading (the minutes' topic style), quote, nested lists, strikethrough and links reach Word, and an
        unedited draft raises no difference."""
        md = ("Lead with ~~old~~ new and [the plan](https://example.com/plan).\n\n### Next steps\n\n> Hold the date\n\n"
              "- Data\n  - Masked extract\n  1. Book UAT\n- Escalate")
        self.v.at("weekly-stage", self.spec(current_state=md), script="report.py")
        prop = next((self.v.root / "system/staging").glob("proposed-*-weekly-ABC.json"))
        draft = self.v.root / json.loads(prop.read_text())["report"]["draft"]
        text = self.v.run("text", str(draft), script="docx_tools.py").stdout
        for line in ("Lead with old new and the plan (https://example.com/plan).", "Next steps", "Hold the date",
                     "• Data", "• Masked extract", "1. Book UAT", "• Escalate"):
            self.assertIn(line + "\n", text)
        with zipfile.ZipFile(draft) as z:
            xml = z.read("word/document.xml").decode()
        self.assertNotIn("STYLE_TOPIC", xml)                                     # the sample is removed
        self.assertRegex(xml, r"<w:strike/>[^<]*</w:rPr><w:t[^>]*>old</w:t>")
        self.assertIn('<w:ind w:left="720" w:hanging="360"/>', xml)              # nested level
        self.assertIn('<w:ind w:left="567"/>', xml)                              # quote
        heading = next(p for p in re.findall(r"<w:p[ >].*?</w:p>", xml, re.S) if ">Next steps<" in p)
        self.assertNotIn("**", heading)
        listed = json.loads(self.v.run("list", "--json", script="review.py").stdout)
        n = next(r["n"] for r in listed if r["ref"] == "report")
        out = self.v.run("approve", str(n), script="review.py").stdout
        self.assertNotIn("Current state: draft says", out)

    def test_images_in_place(self):
        """BL-63: an image sits where it is placed in Current state, in Word and in the project's CLAUDE.md, and an
        unedited draft raises no difference."""
        md = "Before the plan.\n\n![Delivery plan](images/plan.png)\n\nAfter the plan."
        self.v.at("weekly-stage", self.spec(current_state=md), script="report.py")
        prop = next((self.v.root / "system/staging").glob("proposed-*-weekly-ABC.json"))
        data = json.loads(prop.read_text())
        draft = self.v.root / data["report"]["draft"]
        with zipfile.ZipFile(draft) as z:
            xml = z.read("word/document.xml").decode()
        paras = re.findall(r"<w:p[ >].*?</w:p>", xml, re.S)
        at = lambda pred: next(i for i, p in enumerate(paras) if pred(p))  # noqa: E731
        before, pic = at(lambda p: ">Before the plan.<" in p), at(lambda p: "rIdCreaiteImg" in p)   # not the template's logo
        caption, after = at(lambda p: ">Delivery plan<" in p), at(lambda p: ">After the plan.<" in p)
        self.assertEqual(sorted([before, pic, caption, after]), [before, pic, caption, after])
        self.assertEqual(xml.count('r:embed="rIdCreaiteImg'), 1)               # once, not again at the end
        memory = next(o for o in data["report"]["file_ops"] if o["op"] == "write")["content"]
        self.assertIn("Before the plan.\n\n![Delivery plan](images/plan.png)\n\nAfter the plan.\n", memory)
        self.assertEqual(memory.count("![Delivery plan]"), 1)
        listed = json.loads(self.v.run("list", "--json", script="review.py").stdout)
        n = next(r["n"] for r in listed if r["ref"] == "report")
        self.assertNotIn("Current state: draft says", self.v.run("approve", str(n), script="review.py").stdout)

    def test_replace_current_keeps_images(self):
        """BL-63: images stay where the new text places them; any it leaves out are kept at the end."""
        import importlib
        sys.path.insert(0, str(self.v.root / "system/scripts"))
        report = importlib.import_module("report")
        old = "# X\n\n## Current state\n\n_Guide._\n\nOld.\n\n![A](images/a.png)\n![B](images/b.png)\n\n## Next\n"
        new = report.replace_current(old, "One.\n\n![B](images/b.png)\n\nTwo.")
        self.assertIn("_Guide._\n\nOne.\n\n![B](images/b.png)\n\nTwo.\n\n![A](images/a.png)\n", new)
        self.assertEqual((new.count("![A]"), new.count("![B]")), (1, 1))
        self.assertTrue(new.endswith("## Next\n"))

    def test_current_context_for_a_draft(self):
        """BL-46: the material for a Current state draft, from the vault only, for one project and period."""
        folder = self.v.root / ABC
        for rel in ("minutes/2026-10-05 Steering.docx", "minutes/2026-08-01 Old.docx", "documents/Plan.docx"):
            (folder / rel).parent.mkdir(parents=True, exist_ok=True)
            (folder / rel).write_bytes(b"x")
        out = self.v.at("current-context", "ABC", "--from", "2026-10-01", "--to", "2026-10-09", script="report.py").stdout
        self.assertIn("Period: 01-10-2026 to 09-10-2026", out)
        self.assertIn("## Open actions", out)
        self.assertIn(f"{ABC}/minutes/2026-10-05 Steering.docx", out)
        self.assertNotIn("2026-08-01 Old.docx", out)                              # outside the period
        self.assertNotIn("documents/Plan.docx", out)                              # documents only when asked
        out = self.v.at("current-context", "ABC", "--from", "2026-10-01", "--to", "2026-10-09", "--sources",
                        "documents", script="report.py").stdout
        self.assertIn("documents/Plan.docx", out)
        self.assertNotIn("## Open actions", out)

    def test_health_better_than_evidence_needs_a_reason(self):
        """BL-52: the weekly report won't stage a health better than the criteria without a reason."""
        r = self.v.at("weekly-stage", self.spec(health="On track", health_reason=""), script="report.py", ok=False)
        self.assertEqual(r.returncode, 3)
        self.assertIn("better than the evidence suggests", r.stdout)

    def test_quiet_week(self):
        self.v.propose("q", [new("projects", 1, code="QUI", name="Quiet Project")])
        self.v.run("apply")
        folder = self.v.root / "projects/QUI Quiet Project"
        for sub in ("minutes", "transcripts", "documents", "reports"):
            (folder / sub).mkdir(parents=True, exist_ok=True)
        (folder / "CLAUDE.md").write_text("# QUI\n\n## Current state\n\nSteady.\n")
        f = self.v.root / "system/staging/drafts/q.json"
        f.write_text(json.dumps({"code": "QUI", "health": "On track", "health_reason": "Nothing outstanding"}))
        self.assertTrue(json.loads(self.v.at("weekly-data", "QUI", script="report.py").stdout)["quiet_week"])
        self.v.at("weekly-stage", str(f), script="report.py")
        draft = next((self.v.root / "system/staging/drafts").glob("* Weekly report - Quiet Project.docx"))
        text = self.v.run("text", str(draft), script="docx_tools.py").stdout
        self.assertIn("No change this week.", text)
        self.assertIn("Overdue Actions", text)                                             # the open position still shows


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.v = ReportVault()
        populate(self.v)

    def tearDown(self):
        self.v.cleanup()

    def spec(self, **extra):
        f = self.v.root / "system/staging/drafts/client.json"
        f.write_text(json.dumps({"code": "ABC", "summary": ["Phase two is being prepared."], "progress": ["Plan revised"],
                                 "next_steps": ["Sign the statement of work"], "input_needed": ["Signature by 16-10"],
                                 **extra}))
        return str(f)

    def test_client_data_filter(self):
        d = json.loads(self.v.at("client-data", "ABC", "--since", "2026-10-01", script="report.py").stdout)
        self.assertEqual([a["id"] for a in d["client_actions"]], ["ABC-A-002"])           # the client's own
        self.assertEqual([a["id"] for a in d["our_commitments"]], ["ABC-A-003"])
        self.assertEqual(d["client_actions"][0]["text"], "The signed statement of work.")  # client messaging, not description
        self.assertEqual([x["id"] for x in d["decisions"]], ["ABC-D-007"])                 # only client-visible
        self.assertEqual([r["id"] for r in d["risks"]], ["ABC-006"])
        self.assertTrue(any("ABC-005" in x for x in d["excluded_high_risks"]))             # Urgent risk not client-visible
        self.assertTrue(d["client_safe_no"])

    def test_first_report_needs_a_start_date(self):
        r = self.v.at("client-stage", self.spec(), script="report.py", ok=False)
        self.assertIn("first client report", r.stdout)

    def test_client_report_and_internal_content_check(self):
        out = self.v.at("client-stage", self.spec(period_start="2026-10-01"), script="report.py").stdout
        self.assertIn("Not client-visible, so left out: ABC-005", out)
        prop = next((self.v.root / "system/staging").glob("proposed-*-client-ABC.json"))
        draft = self.v.root / json.loads(prop.read_text())["report"]["draft"]
        text = self.v.run("text", str(draft), script="docx_tools.py").stdout
        self.assertIn("Example Client Ltd · 1 October 2026 to 9 October 2026", text)
        self.assertIn("The signed statement of work. | Jane Doe (Example Client Ltd) | 16-10-2026", text)
        self.assertIn("Issue: Test licences are not yet ordered. Testing could start late. Purchase order raised this week.",
                      text)
        self.assertIn("Go-live remains on 20 November.", text)
        for internal in ("Vendor exits the market", "Absorb the phase one overrun", "ABC-A-", "Confirm tester names"):
            self.assertNotIn(internal, text)
        # Alan pastes something internal into the draft: the check stops it
        edit_docx(draft, "Phase two is being prepared.", "Phase two is being prepared. Vendor exits the market before go-live.")
        listed = json.loads(self.v.run("list", "--json", script="review.py").stdout)
        n = next(r["n"] for r in listed if r["ref"] == "report")
        out = self.v.run("approve", str(n), script="review.py").stdout
        self.assertIn("possible internal content", out)
        self.assertIn("ABC-005 isn't client-visible but its wording appears", out)
        self.assertIn("Approved 1.", self.v.run("approve", str(n), "--as-staged", script="review.py").stdout)


# ===== v2.1.0 P3 (BL-335, BL-336): the reports in creaite, through the live server's routes =====
WEEKLY_FILE = f"{ABC}/reports/2026-10-09 Weekly report - Example Programme.html"
WEEKLY_DRAFT = "system/staging/drafts/2026-10-09 Weekly report - Example Programme.html"


class ReportRoutes(unittest.TestCase):
    """/api/report/draft, save, approve and export on a live server in a throwaway vault (P2's real export, creaite_doc.export)."""

    @classmethod
    def setUpClass(cls):
        import socket
        import time
        import urllib.request
        cls.v = v = ReportVault()
        populate(v)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            cls.port = sock.getsockname()[1]
        cls.base = f"http://127.0.0.1:{cls.port}"
        env = {**os.environ, "CREAITE_PORT": str(cls.port), "CREAITE_NOW": NOW, "CREAITE_NO_LAUNCH": "1"}
        cls.proc = subprocess.Popen([sys.executable, str(v.root / "system/scripts/live_server.py")], env=env,
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

    def post(self, path, body):
        import urllib.request
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode())

    def section(self, doc, sid):
        return next(s for s in doc["sections"] if s["id"] == sid)

    def test_1_weekly_draft_save_approve_and_a_new_version(self):
        r = self.post("/api/report/draft", {"kind": "weekly", "code": "ABC", "week_ending": "2026-10-09"})
        self.assertTrue(r["ok"], r)
        self.assertEqual((r["where"], r["version"], r["filed"]), ("new", 0, False))
        doc = r["doc"]
        self.assertEqual([s["id"] for s in doc["sections"]][:4], ["header", "health", "glance", "summary"])
        self.assertEqual(self.section(doc, "risks")["rows"][0]["ref"], "ABC-005")         # Urgent first
        self.section(doc, "health")["text"] = "UAT start slipped two weeks."
        self.section(doc, "summary")["text"] = "UAT start has slipped two weeks; escalation is planned."
        self.section(doc, "asks")["hidden"] = True
        doc["layout"]["hidden"] = ["asks"]
        doc["layout"]["headings"] = {"summary": "Executive summary"}
        s = self.post("/api/report/save", {"doc": doc, "base_version": 0})
        self.assertTrue(s["ok"], s)
        self.assertEqual((s["path"], s["version"]), (WEEKLY_DRAFT, 1))
        settings = json.loads((self.v.root / "system/config/settings.json").read_text())
        self.assertEqual(settings["report_layouts"]["ABC"]["weekly"]["hidden"], ["asks"])        # remembered for the project
        a = self.post("/api/report/approve", {"kind": "weekly", "code": "ABC", "week_ending": "2026-10-09"})
        self.assertTrue(a["ok"], a)
        filed = (self.v.root / WEEKLY_FILE).read_text(encoding="utf-8")
        self.assertIn('"state": "approved"', filed)
        self.assertIn('"client_facts"', filed)
        self.assertFalse((self.v.root / WEEKLY_DRAFT).exists())
        up = self.v.rows("updates")
        self.assertEqual((up[0]["week_ending"], up[0]["health"]), ("2026-10-09", "At risk"))
        # a filed report is never changed in place: Save makes a new draft; the filed file stays until that is approved
        r = self.post("/api/report/draft", {"kind": "weekly", "code": "ABC", "week_ending": "2026-10-09"})
        self.assertEqual((r["where"], r["filed"]), ("filed", True))
        doc = r["doc"]
        self.section(doc, "summary")["text"] = "A second version."
        s = self.post("/api/report/save", {"doc": doc, "base_version": r["version"]})
        self.assertEqual((s["ok"], s["path"], s.get("needs_approval")), (True, WEEKLY_DRAFT, None))
        self.assertEqual((self.v.root / WEEKLY_FILE).read_text(encoding="utf-8"), filed)
        a = self.post("/api/report/approve", {"kind": "weekly", "code": "ABC", "week_ending": "2026-10-09"})
        self.assertTrue(a["ok"], a)
        self.assertIn("A second version.", (self.v.root / WEEKLY_FILE).read_text(encoding="utf-8"))
        u = self.post("/api/undo", {"apply_id": a["apply_id"]})
        self.assertTrue(u["ok"], u)
        self.assertEqual((self.v.root / WEEKLY_FILE).read_text(encoding="utf-8"), filed)        # Undo puts the filed one back
        self.assertTrue((self.v.root / WEEKLY_DRAFT).exists())
        nxt = self.post("/api/report/draft", {"kind": "weekly", "code": "ABC", "week_ending": "2026-10-16"})["doc"]
        self.assertTrue(self.section(nxt, "asks")["hidden"])                                   # next week starts the same way
        self.assertEqual(self.section(nxt, "summary")["heading"], "Executive summary")

    def test_2_client_view_export_after_the_internal_week_and_never_a_leak(self):
        r = self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": "2026-10-09"})
        self.assertTrue(r["ok"], r)
        self.assertTrue(r["ready"], r)                     # test_1 approved the internal week
        doc = r["doc"]
        self.assertEqual(doc["based_on"]["path"], WEEKLY_FILE)
        self.assertNotIn("ABC-005", json.dumps(doc))
        self.section(doc, "summary")["text"] = "Restricted: we will absorb the phase one overrun internally."
        self.assertTrue(self.post("/api/report/save", {"doc": doc, "base_version": 0})["ok"])
        e = self.post("/api/report/export", {"kind": "client", "code": "ABC", "week_ending": "2026-10-09", "fmt": "pdf"})
        self.assertFalse(e["ok"])
        self.assertIn("contains “restricted”", e.get("findings", []), e)
        a = self.post("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": "2026-10-09"})
        self.assertFalse(a["ok"])
        self.assertIn("possible internal content", a["message"])
        self.section(doc, "summary")["text"] = "Testing starts on plan."
        self.assertTrue(self.post("/api/report/save", {"doc": doc, "base_version": 1})["ok"])
        e = self.post("/api/report/export", {"kind": "client", "code": "ABC", "week_ending": "2026-10-09", "fmt": "docx"})
        self.assertEqual((e["ok"], e["filed"], e.get("launched")), (True, True, None), e)   # #220: saved in Reports first; opening is separate
        self.assertIn("Client report - Example Programme (Example Client Ltd).docx", e["message"])
        a = self.post("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": "2026-10-09"})
        self.assertIn("awaiting review", a["message"])           # test_1's Undo left its proposal waiting in Review
        a = self.post("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": "2026-10-09", "force": True})
        self.assertTrue(a["ok"], a)
        self.assertTrue((self.v.root / ABC / "reports/2026-10-09 Client report - Example Programme (Example Client Ltd).html").exists())

    def test_3_client_before_its_internal_week_is_refused(self):
        r = self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": "2026-10-23"})
        self.assertTrue(r["ok"])
        self.assertEqual(r["baseline"]["date"], "2026-10-09")                 # the latest approved week; the report says which
        e = self.post("/api/report/export", {"kind": "client", "code": "ABC", "week_ending": "2026-10-23", "fmt": "html"})
        self.assertEqual(e, {"ok": False, "message": "Save the report before exporting it."})
        bad = self.post("/api/report/draft", {"kind": "weekly", "code": "ZZZ"})
        self.assertEqual(bad, {"ok": False, "message": "ZZZ isn't in the tracker."})
# ===== end v2.1.0 P3 =====


# ===== v2.1.0 P3 re-lock (plan #71 point 1): a client draft saved before the internal week is approved can be exported after it =====
class RelockRoutes(unittest.TestCase):
    """Approving the internal week re-locks the project's client drafts to its approved facts, withholding what those facts don't hold."""
    setUpClass = classmethod(ReportRoutes.setUpClass.__func__)
    tearDownClass = classmethod(ReportRoutes.tearDownClass.__func__)
    post = ReportRoutes.post
    section = ReportRoutes.section

    def test_a_draft_saved_before_the_approval_is_locked_withheld_and_exportable(self):
        r = self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": "2026-10-09"})
        doc = r["doc"]
        self.assertIn("ABC-006", doc["items"])
        self.assertIsNone(doc["based_on"])
        self.assertTrue(self.post("/api/report/save", {"doc": doc, "base_version": 0})["ok"])
        # after the draft: ABC-006 stops being client-visible, ABC-005 becomes client-visible
        self.v.propose("shift", [
            {"n": 1, "op": "update", "table": "raid", "id": "ABC-006", "changes": {"client_visible": 0}, "decision": "approved"},
            {"n": 2, "op": "update", "table": "raid", "id": "ABC-005", "decision": "approved",
             "changes": {"client_visible": 1, "client_message": "What it is: The vendor may leave.\nWhat it means for you: Testing could slip.\n"
                                                              "What is being done: A second vendor is lined up."}}])
        self.v.run("apply")
        w = self.post("/api/report/draft", {"kind": "weekly", "code": "ABC", "week_ending": "2026-10-09"})["doc"]
        self.section(w, "health")["text"] = "UAT start slipped two weeks."
        self.assertTrue(self.post("/api/report/save", {"doc": w, "base_version": 0})["ok"])
        a = self.post("/api/report/approve", {"kind": "weekly", "code": "ABC", "week_ending": "2026-10-09"})
        self.assertTrue(a["ok"], a)
        self.assertEqual(len(a["relocked"]), 1, a)
        c = self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": "2026-10-09"})
        locked = c["doc"]
        self.assertEqual(locked["based_on"]["path"], WEEKLY_FILE)
        self.assertEqual((locked["meta"]["locked"], locked["meta"]["facts_week"]), (True, "2026-10-09"))
        self.assertNotIn("ABC-006", json.dumps(locked))                       # no longer in the approved facts: withheld
        self.assertNotIn("ABC-005", json.dumps(locked))                       # became visible after: never added
        self.assertIn("ABC-A-002", locked["items"])                           # still there
        self.assertTrue(c["ready"], c)
        e = self.post("/api/report/export", {"kind": "client", "code": "ABC", "week_ending": "2026-10-09", "fmt": "html"})
        self.assertTrue(e["ok"], e)
        # a new approved version of the week re-locks it to that version, adding nothing
        w = self.post("/api/report/draft", {"kind": "weekly", "code": "ABC", "week_ending": "2026-10-09"})
        self.section(w["doc"], "summary")["text"] = "A second version."
        self.assertTrue(self.post("/api/report/save", {"doc": w["doc"], "base_version": w["version"]})["ok"])
        a = self.post("/api/report/approve", {"kind": "weekly", "code": "ABC", "week_ending": "2026-10-09"})
        self.assertTrue(a["ok"], a)
        again = self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": "2026-10-09"})["doc"]
        filed_version = json.loads(re.search(r'id="creaite-data"[^>]*>(.*?)</script>', (self.v.root / WEEKLY_FILE).read_text(encoding="utf-8"), re.S).group(1))["version"]
        self.assertGreater(filed_version, locked["based_on"]["version"])
        self.assertEqual(again["based_on"]["version"], filed_version)
        self.assertNotIn("ABC-005", json.dumps(again))
# ===== end v2.1.0 P3 re-lock =====


if __name__ == "__main__":
    unittest.main(verbosity=2)
