"""Tests for build_dashboard.py and the dashboard template (Step 4).

Run: python3 dev/tests/test_dashboard.py
Builds a throwaway vault with fictional data (ABC, DEF), builds the dashboard and checks the embedded data.
If Google Chrome is installed, it also loads the page headless and checks it renders with no script errors.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from cdp import chrome_path  # noqa: E402
from test_tracker import ABC, Vault, action  # noqa: E402

CHROME = Path(chrome_path() or "/nonexistent/chrome")      # CREAITE_CHROME, the PATH, then the macOS app (dev/tools/cdp.py)


def now():
    """The test clock, the one every test reads: CREAITE_NOW when it is set (as the scripts read it: "YYYY-MM-DD HH:MM[:SS]"), else the real time (#178)."""
    from datetime import datetime
    fixed = os.environ.get("CREAITE_NOW")
    return datetime.fromisoformat(fixed) if fixed else datetime.now()


def today():
    """Today for the sample data and fixtures: CREAITE_NOW's day when it is set, else the real one (#178). Use this, never date.today()."""
    return now().date()


_today = today


def page_clock_js(stamp):
    """JavaScript that pins a page's clock to `stamp` ("YYYY-MM-DD HH:MM[:SS]", as CREAITE_NOW pins the server's), running on from there:
    Date() and Date.now() read the pinned time; Date with arguments is unchanged. One body for live_browser.pin_page_clock and the
    headless probes (test_insight.chrome), so the page and the data agree (#178)."""
    from datetime import datetime
    t = datetime.fromisoformat(stamp)
    return """(()=>{ const R=Date, off=new R(%d,%d,%d,%d,%d,%d).getTime()-R.now();
  class D extends R{ constructor(...a){ if(a.length) super(...a); else super(R.now()+off); } static now(){ return R.now()+off; } }
  window.Date=D; })();""" % (t.year, t.month - 1, t.day, t.hour, t.minute, t.second)


TODAY = _today()
STAMP_DAY = "2026-10-10"        # the day populate()'s applies are stamped with: a fixed one, so no test depends on the real date


def d(days):
    return (TODAY + timedelta(days=days)).isoformat()


def new(table, n, **values):
    return {"n": n, "op": "new", "table": table, "values": values, "match": "strong", "flags": [],
            "decision": "approved"}


def png(w, h, rgb):
    """A small solid-colour PNG (standard library only)."""
    import struct
    import zlib
    raw = b"".join(b"\x00" + bytes(rgb) * w for _ in range(h))
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))  # noqa: E731
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + \
        chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def stamped_apply(v):
    """`apply` with its stamps on STAMP_DAY (unless the caller already set CREAITE_STAMP_DAY), not the real day."""
    with mock.patch.dict(os.environ, {"CREAITE_STAMP_DAY": os.environ.get("CREAITE_STAMP_DAY") or STAMP_DAY}):
        v.run("apply")


def populate(v):
    """A small fictional portfolio: ABC (slipping) and DEF (on track).

    Its dates count from CREAITE_NOW's day when that is set at the call (else TODAY, which also follows CREAITE_NOW at import), and its applies are stamped with STAMP_DAY (unless the
    caller already set CREAITE_STAMP_DAY), so what it builds does not change with the real date."""
    with mock.patch.dict(os.environ, {"CREAITE_STAMP_DAY": os.environ.get("CREAITE_STAMP_DAY") or STAMP_DAY}):
        _populate(v)


def _populate(v):
    anchor = _today() if os.environ.get("CREAITE_NOW") else TODAY      # its "today": CREAITE_NOW's day if set now, else TODAY
    d = lambda days: (anchor + timedelta(days=days)).isoformat()      # noqa: E731
    reg = v.root / "projects/_portfolio/project-register.md"
    reg.write_text(reg.read_text().replace("|  |  |  |  |  |  |  |  |",
                                           "| DEF | Digital Enablement | DEF Digital Enablement | Enable | Sam (sponsor) | "
                                           "def.example | DEF core | portal |"))
    v.run("init")
    for sub in ("minutes", "transcripts", "documents/Commercial", "reports"):
        (v.root / "projects/DEF Digital Enablement" / sub).mkdir(parents=True, exist_ok=True)
    (v.root / ABC / "CLAUDE.md").write_text(
        "# ABC — Example Programme\n\n## Brief\n\n- **Client / partner:** Example Client Ltd\n"
        "- **Client report rhythm:** fortnightly\n\n## Current state\n\n_Rewritten weekly._\n\n"
        "Build is two weeks behind because data access is late. Escalation is planned for "
        f"{d(2)}.\n\nUAT preparation continues on masked data.\n\n![Delivery plan](images/plan.png)\n"
        "![Missing](images/none.png)\n")
    (v.root / ABC / "images").mkdir(exist_ok=True)
    (v.root / ABC / "images/plan.png").write_bytes(png(240, 120, (11, 110, 127)))
    src = f"{ABC}/minutes/{d(-5)} Steering.docx — Actions"
    v.propose("seed", [
        new("milestones", 1, project="ABC", name="UAT start", baseline_date=d(10), forecast_date=d(24),
            source="Alan (cx-edit)"),
        new("milestones", 2, project="ABC", name="Build complete", baseline_date=d(-20), forecast_date=d(-20),
            status="Done", source="Alan (cx-edit)"),
        new("milestones", 3, project="DEF", name="Pilot live", baseline_date=d(30), forecast_date=d(30),
            source="Alan (cx-edit)"),
        action(4, description="Escalate data access to the client CIO", due_date=d(-3), priority="Urgent",
               milestone="ABC-M-001", source=src),
        action(5, description="Book UAT environment", owner="Sara Example", due_date=d(3), milestone="ABC-M-001",
               source=src),
        action(6, project="DEF", description="Agree pilot success criteria", owner="Omar Ali", due_date=d(5),
               source="Email · From: Omar Ali <omar@def.example> · Subject: [DEF] Pilot · Sent: 2026-10-01 09:00 · "
                      "Link: https://outlook.office365.com/owa/?ItemID=abc"),
        new("raid", 7, project="ABC", type="Risk", description="Data access delayed → UAT slips", impact="High",
            likelihood="High", raised=d(-10), source=src),
        new("raid", 8, project="ABC", type="Issue", description="Test licences not ordered", impact="Medium",
            likelihood="High", raised=d(-4), source=src),
        new("decisions", 9, project="ABC", decision="Go-live moves two weeks", made_by="Jane Doe", date=d(-5),
            source=src),
        new("updates", 10, week_ending=(anchor - timedelta(days=(anchor.weekday() - 4) % 7 + 7)).isoformat(),
            project="ABC", health="At risk", summary="Data access late"),
        {"n": 11, "op": "update", "table": "projects", "id": "ABC",
         "changes": {"health": "Off track", "health_reason": "UAT start slipped 14 days"}, "decision": "approved"},
    ])
    v.run("apply")
    # Files in every folder, a pending proposal with a draft, and something in the inbox
    for rel, body in ((f"{ABC}/minutes/{d(-5)} Steering.docx", b"x"), (f"{ABC}/documents/Plans/{d(-30)} Plan.md", b"plan"),
                      (f"{ABC}/reports/{d(-15)} Client report.docx", b"r"), ("inbox/Recording.vtt", b"WEBVTT"),
                      ("system/staging/drafts/Draft minutes.docx", b"d"), ("inbox/ABC weekly sync.vtt", b"WEBVTT abc"),
                      (f"{ABC}/transcripts/{d(-5)} Steering.vtt", b"WEBVTT filed"), ("inbox/Copy of filed.vtt", b"WEBVTT filed")):
        (v.root / rel).parent.mkdir(parents=True, exist_ok=True)
        (v.root / rel).write_bytes(body)
    v.propose("pending", [{**action(1, description="Chase legal on the SOW"), "decision": "pending"},
                          {**new("raid", 2, project="ABC", type="Risk", description="Vendor exits the market",
                                 raised=d(0), source=src), "decision": "pending"},
                          {"n": 3, "op": "new", "table": "actions", "match": "possible", "flags": [],
                           "decision": "pending", "values": {"project": "DEF", "description": "Confirm data owner",
                                                             "raised": d(0), "source": "Teams · Chat: Omar"}}],
              meeting={"key": "k", "title": "ABC Steering", "projects": ["ABC"], "draft":
                       "system/staging/drafts/Draft minutes.docx", "minutes_decision": "pending", "file_ops": []})


class DashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        populate(cls.v)
        cls.out = cls.v.run(script="build_dashboard.py").stdout
        cls.html = (cls.v.root / "dashboard.html").read_text(encoding="utf-8")
        cls.data = json.loads(re.search(r'<script type="application/json" id="data">(.*?)</script>', cls.html,
                                        re.S).group(1))

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def test_built_with_snapshot(self):
        self.assertIn("Built dashboard.html: 2 projects, 3 actions, 2 RAID, 1 decisions, 4 to review", self.out)
        self.assertTrue((self.v.root / f"system/history/dashboard-{TODAY.isoformat()}.html").exists())

    def test_self_contained_and_no_absolute_paths(self):
        # XML namespace names, compared as strings and never fetched: SVG's, and MathML's and XHTML's, which Preact
        # (BL-256, vendor/preact) uses to tell what kind of element it is creating
        links = set(re.findall(r'https?://[^\s"\'<>)]+', self.html)) - {"http://www.w3.org/2000/svg",
                                                                         "http://www.w3.org/1998/Math/MathML",
                                                                         "http://www.w3.org/1999/xhtml",
                                                                         # BL-301 A: text inside the vendored Tiptap module (an error message
                                                                         # and a comment), never fetched
                                                                         "https://prosemirror.net/docs/guide/#generatable",
                                                                         "https://github.com/markedjs/marked.`,",
                                                                         # #120: the Link popover's address placeholder, shown as hint text,
                                                                         # never fetched
                                                                         "https://example.com"}
        self.assertEqual({u for u in links if "office365.com" not in u and not u.startswith("http://127.0.0.1:")},
                         set())   # only stored message links, and this Mac's own live server
        self.assertNotIn(str(self.v.root), self.html)
        self.assertIsNone(self.data["vault_path"])

    def test_projects_milestones_and_health(self):
        abc = next(p for p in self.data["projects"] if p["code"] == "ABC")
        self.assertEqual((abc["health"], abc["reason"]), ("Off track", "UAT start slipped 14 days"))
        self.assertEqual(abc["slip"], 14)
        self.assertEqual([m[0] for m in abc["ms"]], ["Build complete", "UAT start"] if abc["ms"][0][1] < abc["ms"][1][1]
                         else [m[0] for m in abc["ms"]])
        uat = next(m for m in abc["ms"] if m[0] == "UAT start")
        self.assertEqual((uat[2], uat[3], uat[4], uat[5]), ("slip", "ABC-M-001", d(10), 0))   # 0 of 2 actions closed
        self.assertEqual(abc["client"], "Example Client Ltd")
        self.assertEqual(abc["rhythm"], "Fortnightly")
        self.assertTrue(abc["current"].startswith("Build is two weeks behind"))
        self.assertIn("\n\nUAT preparation continues on masked data.", abc["current"])   # paragraphs kept
        self.assertTrue(abc["current"].endswith("masked data.\n\n![Delivery plan](images/plan.png)\n\n"
                                                "![Missing](images/none.png)"))           # BL-63: images stay in place
        self.assertEqual([(i["alt"], i["ref"]) for i in abc["images"]], [("Delivery plan", "images/plan.png")])  # missing skipped
        self.assertTrue(abc["images"][0]["src"].startswith("data:image/png;base64,"))
        self.assertIn("current-state image not found", self.out)
        self.assertEqual(len(abc["trail"]), 6)
        self.assertEqual((len(abc["trailwhy"]), len(abc["trailend"])), (6, 6))    # #162: a reason and a Friday per bar
        self.assertEqual(abc["trail"][-2], "warn")                      # last week's update: At risk
        defp = next(p for p in self.data["projects"] if p["code"] == "DEF")
        self.assertEqual(defp["health"], "")                            # not set yet: shown neutral

    def test_items(self):
        a = {x["id"]: x for x in self.data["actions"]}
        self.assertEqual(a["ABC-A-001"]["ms"], "ABC-M-001")
        self.assertEqual(a["DEF-A-001"]["ms"], None)                     # milestone link is optional
        self.assertEqual({(r["id"], r["type"], r["imp"], r["lik"]) for r in self.data["raid"]},
                         {("ABC-003", "Risk", "High", "High"), ("ABC-004", "Issue", "Medium", "High")})
        # One number sequence per project: the RAID items and the decision follow ABC-A-001 and ABC-A-002
        self.assertEqual([x["id"] for x in self.data["decisions"]], ["ABC-D-005"])
        self.assertEqual({p["code"]: p["seq"] for p in self.data["projects"]}, {"ABC": 5, "DEF": 1})

    def test_review_matches_staging(self):
        rev = self.data["review"]
        listed = self.v.run("list", script="review.py").stdout
        self.assertEqual(len(rev), len(re.findall(r"^\s*(?:↳ )?\d+ · ", listed, re.M)))   # nested lines too (BL-41)
        kinds = {(r["kind"], r["why"], r["indiv"], r["p"]) for r in rev}
        self.assertIn(("draft", "Draft minutes", True, "ABC"), kinds)
        self.assertIn(("raid", "New risk", True, "ABC"), kinds)
        self.assertIn(("actions", "Possible match", False, None), kinds)
        listed_json = json.loads(self.v.run("list", "--json", script="review.py").stdout)
        by_ref = {(r["file"], r["ref"]): r["n"] for r in listed_json}
        self.assertEqual({(r["file"], r["ref"]): r["n"] for r in rev}, by_ref)   # same numbers as review.py

    def test_inbox_files_states_and_likely_project(self):
        """BL-42: inbox files with their likely project and state."""
        rows = {f["name"]: f for f in self.data["inbox"]}
        self.assertEqual((rows["Recording.vtt"]["state"], rows["Recording.vtt"]["ext"]), ("new", "vtt"))
        self.assertEqual(rows["ABC weekly sync.vtt"]["p"], "ABC")                # code in the name
        self.assertEqual(rows["Copy of filed.vtt"]["state"], "processed")         # identical to a filed transcript

    def test_activity_files_and_reminders(self):
        whats = [x["what"] for x in self.data["activity"]]
        self.assertIn("ABC · Example Programme — health: — → Off track", whats)          # BL-43: names the item
        made = next(w for w in whats if w.startswith("ABC-A-001 · "))
        self.assertIn("Escalate data access to the client CIO — created (owner Alan Carter, due ", made)
        risk = next(x for x in self.data["activity"] if x["id"] == "ABC-003" and x["change"].startswith("created"))
        self.assertIn("Risk", risk["change"])
        names = {(f["p"], f["f"], f["n"], f["sub"]) for f in self.data["files"]}
        self.assertNotIn(("ABC", "documents", f"{d(-30)} Plan.md", "Plans"), names)          # BL-87: documents are set aside by default
        self.assertIn(("ABC", "reports", f"{d(-15)} Client report.docx", "Weekly"), names)    # a report carries its folder
        self.assertIn(("inbox", "", "Recording.vtt", ""), names)
        self.assertTrue(all(not f["path"].startswith("/") for f in self.data["files"]))
        ids = [r["id"] for r in self.data["reminders"]]
        self.assertTrue(any(i.startswith("weekly:") for i in ids))
        self.assertIn(f"client:ABC:{d(-15)}", ids)                      # fortnightly, last one 15 days ago
        cmds = {r["id"]: r.get("cmd") for r in self.data["reminders"]}
        self.assertEqual(cmds[f"client:ABC:{d(-15)}"], "client report ABC")   # Run report now (BL-34)
        weekly = {i: c for i, c in cmds.items() if i.startswith("weekly:")}       # one per project still owed
        self.assertTrue(weekly and all(re.fullmatch(r"weekly report [A-Z][A-Z0-9]{2,6} for week ending \d{2}-\d{2}-\d{4}", c)
                                       and i.split(":")[2] in c for i, c in weekly.items()))

    @unittest.skipUnless(CHROME.exists(), "Google Chrome not installed")
    def test_renders_in_chrome_without_errors(self):
        profile = tempfile.mkdtemp(prefix="creaite-chrome-")
        cmd = [str(CHROME), "--headless", "--disable-gpu", f"--user-data-dir={profile}", "--no-first-run",
               "--disable-component-update", "--disable-background-networking", "--enable-logging=stderr", "--v=0",
               "--virtual-time-budget=3000", "--dump-dom", (self.v.root / "dashboard.html").as_uri()]
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=60)
            out, err = r.stdout, r.stderr
        except subprocess.TimeoutExpired as e:   # Chrome can linger after printing the page; use what it printed
            out, err = e.stdout or b"", e.stderr or b""
        finally:
            shutil.rmtree(profile, ignore_errors=True)
        out, err = out.decode("utf-8", "ignore"), err.decode("utf-8", "ignore")
        errors = [ln for ln in err.splitlines() if "CONSOLE" in ln and ("Uncaught" in ln or "Error" in ln)]
        self.assertEqual(errors, [])
        self.assertIn("Escalate data access to the client CIO", out)   # Today: your overdue commitment
        self.assertIn("Example Programme", out)                         # portfolio table
        self.assertNotIn("Sample data", out)

    @unittest.skipUnless(CHROME.exists(), "Google Chrome not installed")
    def test_day_view_names_the_organiser(self):
        """The saved calendar holds true (Alan organised it) or the organiser's name (BL-42): only true is "You"."""
        from test_insight import chrome
        cal = self.v.root / "system/staging/calendar.json"
        day = today().isoformat()           # the headless page is pinned to CREAITE_NOW too (test_insight.chrome), so page and calendar agree (#178)
        cal.write_text(json.dumps({"fetched": day + " 07:00", "days": {day: [
            {"start": "09:00", "end": "10:00", "title": "Mine", "where": "Teams", "organiser": True},
            {"start": "11:00", "end": "12:00", "title": "Theirs", "where": "Room 4", "organiser": "Jane Doe"}]}}))
        try:
            self.v.run(script="build_dashboard.py")
            out, errors = chrome(self.v, """go("today"); await new Promise(r=>setTimeout(r,50));
              window.OUT=[...document.querySelectorAll("#dayMeets .dm .wh")].map(e=>e.textContent);""", name="organiser")
        finally:
            cal.unlink()
            self.v.run(script="build_dashboard.py")
        self.assertEqual(errors, [])
        self.assertEqual(out, ["Teams · You organise", "Room 4 · Organised by Jane Doe"])

    @unittest.skipUnless(CHROME.exists(), "Google Chrome not installed")
    def test_clicks_raise_no_errors_and_columns_menu_closes(self):
        """BL-64: a page-wide click handler named the Owner filter menu, which exists only once Work has been
        opened, so every click before that threw. BL-128: the Columns menu is now the Display menu."""
        from test_insight import chrome
        out, errors = chrome(self.v, """
          const wait=ms=>new Promise(r=>setTimeout(r,ms)); go("today"); await wait(50);
          document.querySelector("#v-today h1").click(); await wait(20);           // before Work was ever opened
          go("work"); await wait(50);
          document.getElementById("dispBtn").click(); await wait(20); const opened=document.getElementById("dispMenu").classList.contains("on");
          document.querySelector("#v-work h1").click(); await wait(20);
          window.OUT={opened, closed:!document.getElementById("dispMenu").classList.contains("on")};""", name="bl64")
        self.assertEqual(errors, [])
        self.assertEqual(out, {"opened": True, "closed": True})


REPO_ROOT = Path(__file__).resolve().parents[2]


class SharedNumbering(unittest.TestCase):
    """The dashboard's ID preview follows tracker.next_id: one sequence across actions, RAID, decisions and promises
    (promises aren't on the page, so the build passes the highest number as each project's seq)."""

    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        self.v.propose("p", [action(1), {"n": 2, "op": "new", "table": "promises", "match": "strong", "flags": [],
                                         "decision": "approved", "values": {
                                             "project": "ABC", "promised_by": "Alan Carter", "promised_to": "Jane Doe",
                                             "description": "Send the plan", "raised": d(0), "source": "s"}}])
        self.v.run("apply")
        self.assertEqual([r["id"] for r in self.v.rows("promises")], ["ABC-P-002"])
        self.v.run(script="build_dashboard.py")

    def tearDown(self):
        self.v.cleanup()

    def test_seq_counts_promises(self):
        html = (self.v.root / "dashboard.html").read_text(encoding="utf-8")
        data = json.loads(re.search(r'<script type="application/json" id="data">(.*?)</script>', html, re.S).group(1))
        self.assertEqual(next(p for p in data["projects"] if p["code"] == "ABC")["seq"], 2)

    @unittest.skipUnless(CHROME.exists(), "Google Chrome not installed")
    def test_next_id_matches_the_tracker(self):
        from test_insight import chrome
        out, errors = chrome(self.v, 'window.OUT=["actions","raid","decisions"].map(k=>nextId(k,"ABC"));', name="nextid")
        self.assertEqual(errors, [])
        self.assertEqual(out, ["ABC-A-003", "ABC-003", "ABC-D-003"])     # after ABC-A-001 and the promise ABC-P-002
        self.v.propose("q", [action(1, description="Next one")])
        self.v.run("apply")
        self.assertEqual(self.v.rows("actions")[-1]["id"], "ABC-A-003")   # what the page showed is what the tracker gave


class DevMarker(unittest.TestCase):
    """The DEV marker shows only in the development repository (.creaite-dev), never in a vault."""
    def test_only_with_the_dev_file(self):
        v = Vault()
        try:
            v.run("init")
            data = lambda: json.loads(re.search(r'<script type="application/json" id="data">(.*?)</script>',
                                                (v.root / "dashboard.html").read_text(encoding="utf-8"), re.S).group(1))
            v.run(script="build_dashboard.py")
            self.assertIs(data()["dev"], False)
            (v.root / ".creaite-dev").write_text("")
            v.run(script="build_dashboard.py")
            self.assertIs(data()["dev"], True)
            self.assertIn('class="devtag"', (REPO_ROOT / "system/templates/dashboard.html").read_text(encoding="utf-8"))
        finally:
            v.cleanup()


class Favicon(unittest.TestCase):
    def test_icon_is_inline_and_matches_the_source(self):
        from urllib.parse import unquote
        root = Path(__file__).resolve().parents[2]
        page = (root / "system/templates/dashboard.html").read_text(encoding="utf-8")
        m = re.search(r'<link rel="icon" type="image/svg\+xml" href="data:image/svg\+xml,([^"]+)">', page)
        self.assertTrue(m, "no inline favicon")
        svg = unquote(m.group(1))
        self.assertNotIn("#", m.group(1))                        # '#' must be escaped in a data URI
        for part in re.findall(r'(?:fill|stroke)="(#[0-9A-Fa-f]{6})"|d="([^"]+)"',
                               (root / "dev/icon/creaite-icon-stage-small.svg").read_text(encoding="utf-8")):
            self.assertIn(part[0] or part[1], svg)               # same colours as the small Stage (BL-272)
        for shape in re.findall(r"<rect [^>]+/>", (root / "dev/icon/creaite-icon-stage-small.svg").read_text(encoding="utf-8")):
            self.assertIn(shape.replace('"', "'"), svg)              # and the same three squares


if __name__ == "__main__":
    unittest.main(verbosity=2)
