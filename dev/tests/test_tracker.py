"""Tests for tracker.py and doctor.py.

Run: python3 dev/tests/test_tracker.py
Each test builds a throwaway vault in a temporary folder (scripts, schema, config, register and the
ABC example) and runs the real scripts there, so the repository's own tracker.db is never touched.
"""
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import zipfile
from contextlib import closing
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ABC = "projects/ABC Example Programme"


NO_CACHE = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyc.*")    # Python writes these through a temporary name, which a copy running beside other test files can catch vanishing


# ===== BL-172 (sprint-polish-2) =====
# Every vault this process makes is remembered, and any still there when the process ends is removed (a test whose
# setUp or setUpClass failed never reaches its own cleanup). Only this process's own vaults: never one another run made.
# The runner (dev/tools/run_tests.py) sets CREAITE_TEST_TAG to the file's name, so a vault left behind names its file.
import atexit  # noqa: E402

MADE_VAULTS = []


def _remove_own_vaults():
    for d in MADE_VAULTS:
        shutil.rmtree(d, ignore_errors=True)


atexit.register(_remove_own_vaults)


def vault_prefix():
    tag = re.sub(r"[^A-Za-z0-9_]", "", os.environ.get("CREAITE_TEST_TAG", ""))
    return f"creaite-test-{tag}-" if tag else "creaite-test-"
# ===== end BL-172 =====


def make_vault():
    os.environ["CREAITE_NO_LAUNCH"] = "1"    # BL-171: every test that builds a vault inherits it, so /api/open never starts Word
    tmp = Path(tempfile.mkdtemp(prefix=vault_prefix()))
    MADE_VAULTS.append(tmp)                  # BL-172
    scripts = tmp / "system" / "scripts"
    scripts.mkdir(parents=True)
    for f in ("paths.py", "schema.sql", "tracker.py", "doctor.py", "excel_sync.py", "docx_tools.py",
              "minutes.py", "review.py", "build_dashboard.py", "live_server.py",
              "sweep.py", "session.py", "propose.py",
              "report.py", "update.py", "search.py", "permissions.py", "locations.py", "filechange.py", "reach.py", "launch.py", "log.py", "transcripts.py",
              "prep_page.py", "prep_shape.py", "prep_view.py", "status_facts.py", "status_checks.py", "status_prompt.py", "forecast.py",
              "drafts.py",   # AI drafts (sprint-drafts-fields)
              "close_day.py",                                       # BL-295
              "health_fixes.py",                                    # BL-320: Health's Fix it
              "backup.py",                                          # BL-323: the daily zip, retention, Tidy up, restore
              "extraction.py", "quality.py",                       # sprint-drafts-extraction
              "claims.py",                                         # BL-314
              "settings_catalogue.py", "health.py",                # BL-320
              "archive.py",                                        # BL-10, BL-03
              "notes.py",                                          # BL-301: the note format, read by search
              "capture.py",                                        # BL-301 C: the capture drawer's server side
              "edit_ai.py",                                        # BL-301 D: AI on selected text
              "sneak_peek.py",                                     # BL-322
              "notes_find.py",                                     # BL-301 E: Find updates
              "client_leak.py", "report_doc.py", "report_server.py",   # v2.1.0 P3
              "creaite_doc.py",                                    # v2.1.0 P1: creaite's document format
              "run"):                                              # BL-237: the interpreter wrapper (copy2 keeps its execute bit)
        shutil.copy2(REPO / "system" / "scripts" / f, scripts / f)
    shutil.copytree(REPO / "system" / "scripts" / "vendor", scripts / "vendor", ignore=NO_CACHE)
    shutil.copytree(REPO / "system" / "config", tmp / "system" / "config",   # never the dev repo's own logs (git-ignored):
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyc.*", "*.jsonl"))   # change numbers start at 1
    cfg = tmp / "system" / "config" / "settings.json"    # trial state from the dev repo never leaks into tests
    committed = subprocess.run(["git", "-C", str(REPO), "show", "HEAD:system/config/settings.json"], capture_output=True, text=True)
    data = json.loads(committed.stdout if committed.returncode == 0 else cfg.read_text())   # the committed copy, not Alan's dev one
    data.setdefault("reminders", {})["dismissed_forever"] = []
    dflt = data.get("defaults", {})                      # Work opens on its shipped views, not one chosen while trying the app
    for k in [k for k in dflt if k.endswith("_status_filter")]:
        dflt.pop(k)
    cfg.write_text(json.dumps(data, indent=2))
    shutil.copytree(REPO / "system" / "templates", tmp / "system" / "templates", ignore=NO_CACHE)
    (tmp / ".claude").mkdir()
    shipped = subprocess.run(["git", "-C", str(REPO), "show", "HEAD:.claude/settings.json"], capture_output=True, text=True)
    if shipped.returncode == 0:      # the committed template, never Alan's dev copy with rules he added while trying the app
        (tmp / ".claude" / "settings.json").write_text(shipped.stdout, encoding="utf-8")
    else:
        shutil.copy2(REPO / ".claude" / "settings.json", tmp / ".claude" / "settings.json")
    shutil.copytree(REPO / ".claude" / "skills", tmp / ".claude" / "skills", ignore=NO_CACHE)    # ask creaite suggestions (BL-24)
    shutil.copy2(REPO / "CLAUDE.md", tmp / "CLAUDE.md")
    shutil.copy2(REPO / "system" / "creaite-rules.md", tmp / "system" / "creaite-rules.md")   # BL-36
    for tracked in ("_portfolio", "ABC Example Programme"):   # only the tracked sample projects, never demo or real ones
        shutil.copytree(REPO / "projects" / tracked, tmp / "projects" / tracked, ignore=NO_CACHE)
    for d in ("inbox", "system/staging/applied", "system/staging/drafts", "system/history", "system/backups"):
        (tmp / d).mkdir(parents=True, exist_ok=True)
    # processed.txt starts empty, as in a fresh checkout (it isn't in git): the dev repo's own copy, from trying the app,
    # would make tests see different data on this Mac and on GitHub (test_writer_pinned did)
    (tmp / "system" / "processed.txt").write_text("", encoding="utf-8")
    return tmp


def make_draft(path, status="Draft for review"):
    """A filled copy of the minutes template, as cx-minutes would produce."""
    src = REPO / "system" / "templates" / "minutes-template.docx"
    with zipfile.ZipFile(src) as z:
        parts = {i: z.read(i.filename) for i in z.infolist()}
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for info, raw in parts.items():
            if info.filename == "word/document.xml":
                xml = raw.decode("utf-8").replace("{{STATUS_LINE}}", status)
                xml = re.sub(r"\{\{[A-Z_]+\}\}", "sample", xml)
                raw = xml.encode("utf-8")
            z.writestr(info, raw)


def docx_text(path):
    with zipfile.ZipFile(path) as z:
        return re.sub(r"<[^>]+>", " ", z.read("word/document.xml").decode("utf-8"))


class Vault:
    def __init__(self):
        self.root = make_vault()

    def run(self, *args, script="tracker.py", ok=True, cwd=None):
        r = subprocess.run([sys.executable, str(self.root / "system" / "scripts" / script), *args],
                           cwd=cwd or tempfile.gettempdir(), capture_output=True, text=True)
        if ok and r.returncode != 0:
            raise AssertionError(f"{script} {args} failed:\n{r.stdout}\n{r.stderr}")
        return r

    def propose(self, name, items, **extra):
        p = self.root / "system" / "staging" / f"proposed-{name}.json"
        p.write_text(json.dumps({"created": "2026-10-04T09:00:00", "source_run": "cx-edit",
                                 "files": [], "items": items, **extra}, indent=2))
        return p

    def rows(self, table):
        with closing(sqlite3.connect(self.root / "system" / "tracker.db")) as con:
            con.row_factory = sqlite3.Row
            return [dict(r) for r in con.execute(f"SELECT * FROM {table} ORDER BY 1")]

    def snapshot(self):
        """Data tables plus every vault file outside the engine's own working folders."""
        with closing(sqlite3.connect(self.root / "system" / "tracker.db")) as con:
            data = {t: con.execute(f"SELECT * FROM {t} ORDER BY 1").fetchall()
                    for t in ("projects", "actions", "raid", "decisions", "updates", "rejected")}
        files = {}
        for f in sorted(self.root.rglob("*")):
            rel = f.relative_to(self.root).as_posix()
            if f.is_file() and "__pycache__" not in f.parts and not rel.startswith(("system/backups", "system/staging", "system/tracker.db", "system/search",
                                                   "system/scripts/__pycache__", "tracker-view.xlsx",
                                                   "dashboard.html", "system/history", "system/logs")):  # regenerated views
                files[rel] = hashlib.sha256(f.read_bytes()).hexdigest()
        return data, files

    def cleanup(self):
        shutil.rmtree(self.root, ignore_errors=True)


def action(n, **v):
    values = {"project": "ABC", "description": "Send revised SOW to client", "owner": "Alan Carter",
              "raised": "2026-10-01", "source": f"{ABC}/minutes/2026-10-01 Steering.docx — Actions"}
    values.update(v)
    return {"n": n, "op": "new", "table": "actions", "values": values, "match": "strong", "flags": [],
            "decision": "approved"}


class TrackerTests(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.v.run("init")

    def tearDown(self):
        self.v.cleanup()

    def test_init_creates_db_with_register_projects(self):
        self.assertEqual([(p["code"], p["name"]) for p in self.v.rows("projects")], [("ABC", "Example Programme")])
        out = self.v.run("init").stdout  # running again never overwrites
        self.assertIn("Checked", out)

    def test_apply_assigns_ids_and_logs(self):
        self.v.propose("a", [
            action(1),
            {"n": 2, "op": "new", "table": "raid", "match": "strong", "flags": [], "decision": "approved",
             "values": {"project": "ABC", "type": "Risk", "description": "Data access delayed → MVP slips",
                        "impact": "High", "likelihood": "High", "priority": "Low", "raised": "2026-10-01",
                        "source": f"{ABC}/minutes/x.docx — Risks"}},
            {"n": 3, "op": "new", "table": "decisions", "match": "strong", "flags": [], "decision": "approved",
             "values": {"project": "ABC", "decision": "Go-live moves to 15 Nov", "date": "2026-10-01",
                        "source": f"{ABC}/minutes/x.docx — Decisions"}},
        ])
        out = self.v.run("apply").stdout
        self.assertIn("written 3", out)
        self.assertEqual(self.v.rows("actions")[0]["id"], "ABC-A-001")
        raid = self.v.rows("raid")[0]
        self.assertEqual(raid["id"], "ABC-002")   # one number sequence per project: never ABC-A-001 and ABC-001
        self.assertEqual(raid["priority"], "Urgent")  # calculated, never typed
        self.assertEqual(self.v.rows("decisions")[0]["id"], "ABC-D-003")
        self.assertTrue((self.v.root / "system/staging/applied/proposed-a.json").exists())
        self.assertTrue(any(p.name.endswith("-apply.db") for p in (self.v.root / "system/backups").iterdir()))
        log = self.v.rows("change_log")
        self.assertTrue(all(r["apply_id"] == 1 for r in log))
        self.assertIn(("actions", "ABC-A-001", "description"), {(r["tbl"], r["item_id"], r["field"]) for r in log})
        # Next action in the same project continues the sequence
        self.v.propose("b", [action(1, description="Book UAT environment")])
        self.v.run("apply")
        self.assertEqual([a["id"] for a in self.v.rows("actions")], ["ABC-A-001", "ABC-A-004"])  # continues after the RAID item and decision

    def test_numbers_are_never_reused_across_types(self):
        for n in range(3):
            self.v.propose(f"n{n}", [action(1, description=f"Action {n}"),
                {"n": 2, "op": "new", "table": "raid", "match": "strong", "flags": [], "decision": "approved",
                 "values": {"project": "ABC", "type": "Risk", "description": f"Risk {n}", "impact": "Low",
                            "likelihood": "Low", "raised": "2026-10-01", "source": f"{ABC}/minutes/x.docx"}}])
            self.v.run("apply")
        nums = [r["id"][-3:] for t in ("actions", "raid", "decisions", "promises") for r in self.v.rows(t)]
        self.assertEqual(len(nums), len(set(nums)), nums)

    def test_missing_raised_filled_from_source_then_staging_date(self):
        """BL-26: a proposed action or RAID item without Raised gets the source's date, else the staging date."""
        no_date = {"n": 3, "op": "new", "table": "raid", "match": "strong", "flags": [], "decision": "approved",
                   "values": {"project": "ABC", "type": "Risk", "description": "Vendor capacity",
                              "source": "Teams · ABC – Core team"}}
        p = self.v.propose("r", [action(1, raised=None), action(2, raised=None, source="Outlook · RE: SOW · 2026-09-30"),
                                 no_date])
        out = self.v.run("apply").stdout
        self.assertIn("item 1: Raised set to 01-10-2026", out)
        self.assertEqual(sorted(a["raised"] for a in self.v.rows("actions")), ["2026-09-30", "2026-10-01"])
        self.assertEqual(self.v.rows("raid")[0]["raised"], "2026-10-04")            # staged (created) date
        self.assertEqual(json.loads((p.parent / "applied" / p.name).read_text())["items"][0]["values"]["raised"], "2026-10-01")  # kept

    def test_milestone_percent_complete(self):
        """BL-29: 0–100 or null; Alan's figure wins over the calculated one."""
        ms = {"n": 1, "op": "new", "table": "milestones", "match": "strong", "flags": [], "decision": "approved",
              "values": {"project": "ABC", "name": "UAT", "source": "Alan (cx-edit)"}}
        self.v.propose("m", [ms, action(2, milestone="ABC-M-001"), action(3, milestone="ABC-M-001", status="Closed",
                                                                         closed="2026-10-02")])
        self.v.run("apply")
        sys.path.insert(0, str(self.v.root / "system" / "scripts"))
        import importlib
        import tracker
        importlib.reload(tracker)
        con = sqlite3.connect(self.v.root / "system" / "tracker.db")
        con.row_factory = sqlite3.Row
        row = lambda: con.execute("SELECT * FROM milestones WHERE id = 'ABC-M-001'").fetchone()  # noqa: E731
        self.assertEqual(tracker.milestone_progress(con, row()), (50, 50, 1, 2))
        self.v.propose("p", [{"n": 1, "op": "update", "table": "milestones", "id": "ABC-M-001", "decision": "approved",
                              "match": "strong", "flags": [], "changes": {"percent_complete": 80}}])
        self.v.run("apply")
        self.assertEqual(tracker.milestone_progress(con, row()), (80, 50, 1, 2))
        bad = self.v.propose("q", [{"n": 1, "op": "update", "table": "milestones", "id": "ABC-M-001", "decision": "approved",
                                    "match": "strong", "flags": [], "changes": {"percent_complete": 101}}])
        self.assertIn("0 to 100", self.v.run("apply", ok=False).stdout)
        bad.unlink()
        con.close()

    def test_invalid_proposal_rejected_with_reason(self):
        p = self.v.propose("bad", [action(1, due_date="09-10-2026"), action(2, status="Done"),
                                   action(3, project="XYZ"), action(4, client_visible=1)])
        r = self.v.run("validate", str(p), ok=False)
        self.assertEqual(r.returncode, 1)
        items = json.loads(p.read_text())["items"]
        reasons = {i["n"]: i.get("invalid_reason", "") for i in items}
        self.assertTrue(all("invalid" in i["flags"] for i in items))
        self.assertIn("YYYY-MM-DD", reasons[1])
        self.assertIn("Open, Delayed, Closed, Cancelled", reasons[2])
        self.assertIn("XYZ", reasons[3])
        self.assertIn("client messaging", reasons[4])
        # Apply refuses the whole batch and writes nothing
        r = self.v.run("apply", str(p), ok=False)
        self.assertIn("Nothing was written", r.stdout)
        self.assertEqual(self.v.rows("actions"), [])
        # Fixing the proposal clears the flag
        data = json.loads(p.read_text())
        data["items"] = [action(1, due_date="2026-10-09")]
        p.write_text(json.dumps(data))
        self.assertEqual(self.v.run("validate", str(p)).returncode, 0)
        self.assertNotIn("invalid", json.loads(p.read_text())["items"][0]["flags"])

    def test_rules_closed_date_health_reason_and_client_message(self):
        self.v.propose("a", [action(1)])
        self.v.run("apply")
        based = self.v.rows("actions")[0]["updated_at"]
        self.v.propose("b", [{"n": 1, "op": "update", "table": "actions", "id": "ABC-A-001",
                              "changes": {"status": "Closed"}, "based_on": based, "decision": "approved"}])
        self.v.run("apply")
        self.assertIsNotNone(self.v.rows("actions")[0]["closed"])  # closing fills the closed date
        p = self.v.propose("c", [{"n": 1, "op": "update", "table": "projects", "id": "ABC",
                                  "changes": {"health": "At risk"}, "decision": "approved"}])
        r = self.v.run("validate", str(p), ok=False)
        self.assertIn("needs a reason", r.stdout)
        msg = "What it is: SOW revision\nWhat it means for you: Sign-off needed\nWhat is being done: Draft sent"
        d = self.v.propose("d", [action(1, client_visible=1, client_message=msg)])
        self.v.run("apply", str(d))
        self.assertEqual(self.v.rows("actions")[1]["client_visible"], 1)

    def test_two_proposals_editing_one_row_dont_abort_the_apply(self):
        """Each passes validate; together the second is a conflict: held for review, the rest is written."""
        self.v.propose("a", [action(1)])
        self.v.run("apply")
        ua = self.v.rows("actions")[0]["updated_at"]
        upd = lambda ch: {"n": 1, "op": "update", "table": "actions", "id": "ABC-A-001", "changes": ch,  # noqa: E731
                          "based_on": ua, "match": "strong", "flags": [], "decision": "approved"}
        self.v.propose("b", [upd({"owner": "Sara"})])
        c = self.v.propose("c", [upd({"priority": "High"}), action(2, description="Unrelated sweep action")])
        out = self.v.run("apply").stdout
        acts = {a["description"]: a for a in self.v.rows("actions")}
        self.assertIn("Unrelated sweep action", acts)                       # the rest is written
        self.assertEqual(acts["Send revised SOW to client"]["owner"], "Sara")
        held = json.loads(c.read_text())["items"][0]
        self.assertEqual((held["decision"], "conflict" in held["flags"]), ("pending", True))   # held, not lost
        self.assertIn("held", out.lower())

    def test_milestone_link_stays_in_its_project(self):
        self.v.propose("m", [{"n": 1, "op": "new", "table": "milestones", "match": "strong", "flags": [],
                              "decision": "approved", "values": {"project": "ABC", "name": "UAT", "source": "s"}},
                             {"n": 2, "op": "new", "table": "projects", "match": "strong", "flags": [],
                              "decision": "approved", "values": {"code": "DEF", "name": "Other"}}])
        self.v.run("apply")
        self.v.propose("x", [action(1, project="DEF", milestone="ABC-M-001")])
        out = self.v.run("apply", ok=False).stdout
        self.assertIn("milestone ABC-M-001 belongs to ABC, not DEF", out)

    def test_conflict_is_held_not_overwritten(self):
        self.v.propose("a", [action(1)])
        self.v.run("apply")
        p = self.v.propose("b", [{"n": 1, "op": "update", "table": "actions", "id": "ABC-A-001",
                                  "changes": {"owner": "Sara Example"}, "based_on": "2026-01-01 00:00:00",
                                  "decision": "approved"}])
        out = self.v.run("apply", str(p)).stdout
        self.assertIn("held 1", out)
        self.assertEqual(self.v.rows("actions")[0]["owner"], "Alan Carter")
        item = json.loads(p.read_text())["items"][0]
        self.assertIn("conflict", item["flags"])
        self.assertEqual(item["decision"], "pending")
        self.assertEqual(item["current"]["owner"], "Alan Carter")  # review can show both versions

    def test_rejected_and_pending_items(self):
        p = self.v.propose("a", [action(1), {**action(2, description="Chase legal"), "decision": "rejected"},
                                 {**action(3, description="Pending one"), "decision": "pending"}])
        self.v.run("apply")
        self.assertEqual(len(self.v.rows("rejected")), 1)
        self.assertTrue(p.exists())  # still has a pending item, so it stays in staging
        items = json.loads(p.read_text())["items"]
        self.assertEqual([bool(i.get("applied")) for i in items], [True, True, False])

    def test_apply_then_undo_restores_exact_state(self):
        # Prior state: one action, then a meeting to file with items, a rejection and an update
        self.v.propose("seed", [action(1)])
        self.v.run("apply")
        draft = "system/staging/drafts/2026-10-01 ABC Steering committee.docx"
        transcript = "inbox/Recording 2026-10-01.vtt"
        make_draft(self.v.root / draft)
        (self.v.root / transcript).write_text("WEBVTT\n\n00:00.000 --> 00:02.000\n<v Alan>Welcome</v>\n")
        based = self.v.rows("actions")[0]["updated_at"]
        before = self.v.snapshot()
        p = self.v.propose("meeting", [
            {**action(1, description="Book UAT environment"), "source_run": "cx-minutes"},
            {"n": 2, "op": "update", "table": "actions", "id": "ABC-A-001", "based_on": based,
             "changes": {"owner": "Sara Example", "status": "Delayed"}, "decision": "approved"},
            {**action(3, description="Not wanted"), "decision": "rejected"},
        ], source_run="cx-minutes", meeting={
            "key": "fp:2026-10-01|abc steering committee|abc123", "title": "ABC Steering committee",
            "date": "2026-10-01", "projects": ["ABC"], "draft": draft, "transcript": transcript,
            "minutes_decision": "approved", "file_ops": [
                {"op": "copy", "from": "draft", "to": f"{ABC}/minutes/2026-10-01 ABC Steering committee.docx"},
                {"op": "copy", "from": "transcript", "to": f"{ABC}/transcripts/2026-10-01 ABC Steering committee.vtt"},
                {"op": "remove", "path": transcript},
                {"op": "remove", "path": draft}]})
        out = self.v.run("apply").stdout
        self.assertIn("written 2, filed 1, rejected 1", out)
        filed = self.v.root / ABC / "minutes/2026-10-01 ABC Steering committee.docx"
        self.assertTrue(filed.exists())
        self.assertIn("Approved by Alan on", docx_text(filed))
        self.assertFalse((self.v.root / transcript).exists())
        self.assertFalse((self.v.root / draft).exists())
        self.assertIn("abc steering committee", (self.v.root / "system/processed.txt").read_text())
        self.assertTrue((self.v.root / "system/staging/applied" / p.name).exists())

        out = self.v.run("undo").stdout
        self.assertIn("Undid apply 2", out)
        self.assertEqual(self.v.snapshot(), before)  # database and files exactly as before
        self.assertIn("Draft for review", docx_text(self.v.root / draft))
        back = json.loads(p.read_text())  # proposal is back in staging with its items pending
        self.assertTrue(all(i["decision"] == "pending" and "applied" not in i for i in back["items"]))
        self.assertEqual(back["meeting"]["minutes_decision"], "pending")
        # A second undo steps back through the earlier apply
        self.v.run("undo")
        self.assertEqual(self.v.rows("actions"), [])
        self.assertIn("Nothing to undo", self.v.run("undo").stdout)

    def test_undo_skips_items_changed_since(self):
        self.v.propose("a", [action(1), action(2, description="Book UAT environment")])
        self.v.run("apply")
        self.v.propose("b", [{"n": 1, "op": "update", "table": "actions", "id": "ABC-A-001",
                              "changes": {"owner": "Sara Example"}, "decision": "approved"}])
        self.v.run("apply")
        self.v.run("undo")  # undoing a later apply restores the exact values, so nothing is skipped below
        con = sqlite3.connect(self.v.root / "system/tracker.db")  # test setup only: a stray outside edit
        con.execute("UPDATE actions SET owner = 'Omar Ali' WHERE id = 'ABC-A-001'")
        con.commit()
        con.close()
        out = self.v.run("undo").stdout
        self.assertIn("skipped ABC-A-001: changed since that apply", out)
        self.assertEqual([a["id"] for a in self.v.rows("actions")], ["ABC-A-001"])  # ABC-A-002 removed
        items = json.loads((self.v.root / "system/staging/proposed-a.json").read_text())["items"]
        self.assertEqual([("applied" in i) for i in items], [True, False])  # skipped item stays applied

    def test_undo_of_a_field_changed_twice_in_one_apply_restores_the_original(self):
        self.v.propose("a", [action(1)])
        self.v.run("apply")
        before = {k: v for k, v in self.v.rows("actions")[0].items()}
        upd = lambda owner: {"n": 1, "op": "update", "table": "actions", "id": "ABC-A-001",
                             "changes": {"owner": owner}, "decision": "approved"}
        self.v.propose("b1", [upd("Sara Example")])                  # two proposals, one field, applied together
        self.v.propose("b2", [upd("Omar Ali")])
        self.v.run("apply")
        self.assertEqual(self.v.rows("actions")[0]["owner"], "Omar Ali")
        out = self.v.run("undo").stdout
        self.assertNotIn("skipped", out)                              # its own second change isn't "changed since"
        self.assertEqual(self.v.rows("actions")[0]["owner"], before["owner"])   # the original, not the middle value

    def test_minutes_rejected_files_transcript_only(self):
        draft = "system/staging/drafts/2026-10-02 ABC Checkpoint.docx"
        transcript = "inbox/Recording 2026-10-02.vtt"
        make_draft(self.v.root / draft)
        (self.v.root / transcript).write_text("WEBVTT\n")
        self.v.propose("m", [], source_run="cx-minutes", meeting={
            "key": "fp:2026-10-02|abc checkpoint|1", "draft": draft, "transcript": transcript,
            "minutes_decision": "rejected", "file_ops": [
                {"op": "copy", "from": "draft", "to": f"{ABC}/minutes/2026-10-02 ABC Checkpoint.docx"},
                {"op": "copy", "from": "transcript", "to": f"{ABC}/transcripts/2026-10-02 ABC Checkpoint.vtt"},
                {"op": "remove", "path": transcript}, {"op": "remove", "path": draft}]})
        self.v.run("apply")
        self.assertTrue((self.v.root / ABC / "transcripts/2026-10-02 ABC Checkpoint.vtt").exists())
        self.assertFalse((self.v.root / ABC / "minutes/2026-10-02 ABC Checkpoint.docx").exists())
        self.assertFalse((self.v.root / draft).exists())

    def test_file_ops_stay_inside_vault(self):
        p = self.v.propose("x", [], meeting={"key": "k", "minutes_decision": "approved", "draft": None,
                                             "transcript": None, "file_ops": [
                                                 {"op": "write", "path": "system/scripts/evil.py", "content": "x"}]})
        r = self.v.run("apply", str(p), ok=False)
        self.assertIn("not in projects/, inbox/, system/staging/ or system/search/", r.stdout)
        self.assertFalse((self.v.root / "system/scripts/evil.py").exists())

    def test_write_and_mkdir_undo(self):
        memory = f"{ABC}/CLAUDE.md"
        old = (self.v.root / memory).read_text()
        before = self.v.snapshot()
        self.v.propose("w", [], report={"report_decision": "approved", "draft": None, "file_ops": [
            {"op": "write", "path": memory, "content": old + "\nNew line\n", "previous": old},
            {"op": "mkdir", "path": "projects/DEF Digital Enablement/minutes"}]})
        self.v.run("apply")
        self.assertIn("New line", (self.v.root / memory).read_text())
        self.assertTrue((self.v.root / "projects/DEF Digital Enablement/minutes").is_dir())
        self.v.run("undo")
        self.assertEqual(self.v.snapshot(), before)
        self.assertFalse((self.v.root / "projects/DEF Digital Enablement").exists())

    def test_index_and_query(self):
        d = self.v.root / ABC / "documents" / "Plans"
        d.mkdir(parents=True)
        (d / "2026-09-01 Plan.md").write_text("Delivery plan for ABC-A-003 and the data-access workstream")
        make_draft(self.v.root / ABC / "minutes/2026-10-01 Steering.docx")
        shutil.copy2(self.v.root / ABC / "minutes/2026-10-01 Steering.docx",
                     self.v.root / "projects/_portfolio/minutes/2026-10-01 Steering.docx")
        out = self.v.run("index").stdout
        self.assertIn("Indexed 2 file(s)", out)  # the duplicate meeting copy is indexed once
        hits = json.loads(self.v.run("query", "ABC-A-003").stdout)
        self.assertEqual(hits[0]["path"], f"{ABC}/documents/Plans/2026-09-01 Plan.md")
        self.assertIn("[", hits[0]["snippet"])
        self.assertEqual(json.loads(self.v.run("query", "data-access", "--project", "ABC").stdout)[0]["kind"],
                         "documents")
        meeting = json.loads(self.v.run("query", "sample", "--project", "_portfolio").stdout)
        self.assertEqual(len(meeting), 1)

    def test_read(self):
        self.v.propose("a", [action(1)])
        self.v.run("apply")
        rows = json.loads(self.v.run("read", "actions", "--project", "ABC").stdout)
        self.assertEqual(rows[0]["id"], "ABC-A-001")
        one = json.loads(self.v.run("read", "actions", "--id", "ABC-A-001").stdout)
        self.assertEqual(len(one), 1)
        self.assertIn("raid", json.loads(self.v.run("read").stdout))

    # ===== BL-252 (fix-search-read) =====
    def test_read_search_matches_words_case_insensitively(self):
        self.v.propose("a", [action(1, description="Send revised SOW to client"),
                             action(2, description="Book the steering room"),
                             action(3, description="Sign the sow addendum", status="Closed", closed="2026-10-02")])
        self.v.run("apply")
        ids = lambda *a: [r["id"] for r in json.loads(self.v.run("read", "actions", *a).stdout)]  # noqa: E731
        self.assertEqual(ids("--project", "ABC", "--search", "sow"), ["ABC-A-001", "ABC-A-003"])
        self.assertEqual(ids("--project", "ABC", "--search", "SOW", "--status", "open"), ["ABC-A-001"])
        self.assertEqual(ids("--search", "Sow", "--status", "closed"), ["ABC-A-003"])
        self.assertEqual(ids("--search", "sow", "--id", "ABC-A-003"), ["ABC-A-003"])
        self.assertEqual(ids("--project", "XYZ", "--search", "sow"), [])
        self.assertEqual(ids("--search", "nothing like this"), [])
        every = json.loads(self.v.run("read", "--search", "steering").stdout)  # all tables: only those with words
        self.assertEqual([r["id"] for r in every["actions"]], ["ABC-A-002"])
        self.assertNotIn("links", every)

    def test_read_unknown_table_or_option_fails_listing_the_valid_ones(self):
        r = self.v.run("read", "action", "--search", "sow", ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("unknown table action", r.stderr)
        self.assertIn("actions, raid", r.stderr)
        r = self.v.run("read", "actions", "--grep", "sow", ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("unknown option --grep", r.stderr)
        self.assertIn("--search", r.stderr)
        self.assertIn("--status", r.stderr)
        r = self.v.run("read", "actions", "--search", ok=False)
        self.assertIn("needs a value", r.stderr)
        r = self.v.run("read", "actions", "--status", "pending", ok=False)
        self.assertIn("open or closed", r.stderr)
    # ===== end BL-252 =====


class DoctorTests(unittest.TestCase):
    def setUp(self):
        self.v = Vault()

    def tearDown(self):
        self.v.cleanup()

    def test_fails_without_db_then_passes(self):
        r = self.v.run(script="doctor.py", ok=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL  tracker.db integrity", r.stdout)
        self.v.run("init")
        r = self.v.run(script="doctor.py")
        self.assertIn("0 failed", r.stdout)

    def test_flags_absolute_path(self):
        self.v.run("init")
        self.v.propose("abs", [action(1, source="/Users/someone/creaite/projects/x.docx")])
        r = self.v.run(script="doctor.py", ok=False)
        self.assertIn("FAIL  No absolute paths stored", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
