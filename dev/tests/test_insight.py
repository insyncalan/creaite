"""Tests for the insight sprint: early warnings (BL-51), meeting prep (BL-49) and quick capture (BL-54).

Run: python3 dev/tests/test_insight.py
Each class builds a throwaway vault with fictional data and runs the real scripts there. Early-warning history is
written straight into change_log at chosen dates (constructed history); the scripts themselves never do that.
"""
import json
import os
import sqlite3
import subprocess
import sys
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import ABC, Vault, action  # noqa: E402

TODAY = "2026-10-14"          # a Wednesday; this week starts 12-10-2026


def new(table, n, **values):
    return {"n": n, "op": "new", "table": table, "values": values, "match": "strong", "flags": [], "decision": "approved"}


def py(v, code, now=TODAY + " 09:00"):
    """Run Python in the vault with its scripts importable and the clock fixed; returns stdout."""
    r = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, 'system/scripts')\n" + code],
                       cwd=v.root, capture_output=True, text=True, env={**os.environ, "CREAITE_NOW": now})
    if r.returncode:
        raise AssertionError(r.stdout + r.stderr)
    return r.stdout


def warnings(v):
    return json.loads(py(v, "import json, paths, build_dashboard as b\nfrom datetime import date\n"
                            f"print(json.dumps(b.early_warnings(paths.load_settings(), date.fromisoformat('{TODAY}'))))"))


def set_warnings(v, **changes):
    cfg = v.root / "system/config/settings.json"
    data = json.loads(cfg.read_text())
    for key, val in changes.items():
        sig, field = key.split("__")
        data.setdefault("warnings", {}).setdefault(sig, {})[field] = val
    cfg.write_text(json.dumps(data, indent=2))


def log(v, rows):
    """Constructed history: (at, tbl, item_id, field, old, new[, apply_id])."""
    with closing(sqlite3.connect(v.root / "system/tracker.db")) as con:
        for r in rows:
            at, tbl, item, field, old, new_, *rest = r
            con.execute("INSERT INTO change_log (at, apply_id, tbl, item_id, field, old_value, new_value, op, via) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, 'update', 'dashboard')",
                        (at, rest[0] if rest else None, tbl, item, field, old, new_))
        con.commit()


class EarlyWarningTests(unittest.TestCase):
    """BL-51: each signal on constructed history, thresholds and switches, and its use in reports."""

    @classmethod
    def setUpClass(cls):
        cls.v = v = Vault()
        v.run("init")
        closed = [action(10 + i, description=f"Closed task {i}", raised="2026-09-01", status="Closed",
                         closed=f"2026-09-0{4 + i % 3}") for i in range(5)]          # ABC usually closes in about 4 days
        v.propose("seed", [
            action(1, description="Send revised SOW", due_date="2026-10-20", raised="2026-10-01"),          # ABC-A-001
            action(2, description="Book the steering room", due_date="2026-10-20", raised="2026-10-01"),    # ABC-A-002
            action(3, description="Old closed one", raised="2026-09-01", status="Closed", closed="2026-09-03"),  # A-003
            action(4, description="Chase legal on the DPA", raised="2026-09-01"),                            # ABC-A-004
            *closed,                                                                                          # A-005…009
            new("raid", 20, project="ABC", type="Risk", description="Data access delayed", raised="2026-09-20",
                source=f"{ABC}/minutes/2026-09-20 Steering.docx — RAID"),                                      # ABC-010 (one sequence: after A-001…009)
            new("raid", 21, project="ABC", type="Risk", description="Vendor exits", raised="2026-09-20",
                response_action="Second supplier lined up", source=f"{ABC}/minutes/2026-09-20 Steering.docx — RAID"),
            new("milestones", 30, project="ABC", name="UAT start", baseline_date="2026-10-20",
                forecast_date="2026-11-10", source="Alan (cx-edit)"),                                        # ABC-M-001
            new("milestones", 31, project="ABC", name="Build complete", baseline_date="2026-10-01",
                forecast_date="2026-10-15", source="Alan (cx-edit)"),                                        # ABC-M-002
        ])
        v.run("apply")
        with closing(sqlite3.connect(v.root / "system/tracker.db")) as con:
            con.execute("INSERT INTO applies (apply_id, at, proposals, undone_at) VALUES (900, '2026-10-02', '[]', '2026-10-02')")
            con.commit()
        log(v, [("2026-10-02 10:00:00", "actions", "ABC-A-001", "due_date", "2026-10-05", "2026-10-09"),
                ("2026-10-06 10:00:00", "actions", "ABC-A-001", "due_date", "2026-10-09", "2026-10-13"),
                ("2026-10-10 10:00:00", "actions", "ABC-A-001", "due_date", "2026-10-13", "2026-10-20"),
                ("2026-10-01 10:00:00", "actions", "ABC-A-002", "due_date", None, "2026-10-05"),        # first date: not a re-date
                ("2026-10-02 10:00:00", "actions", "ABC-A-002", "due_date", "2026-10-05", "2026-10-08", 900),  # undone
                ("2026-10-06 10:00:00", "actions", "ABC-A-002", "due_date", "2026-10-08", "2026-10-12"),
                ("2026-10-09 10:00:00", "actions", "ABC-A-002", "due_date", "2026-10-12", "2026-10-20"),
                *[(f"2026-09-0{d} 10:00:00", "actions", "ABC-A-003", "due_date", "2026-09-01", "2026-09-02") for d in (1, 2, 3)],
                ("2026-10-07 10:00:00", "milestones", "ABC-M-001", "forecast_date", "2026-10-20", "2026-10-27"),
                ("2026-10-13 10:00:00", "milestones", "ABC-M-001", "forecast_date", "2026-10-27", "2026-11-10"),
                ("2026-09-22 10:00:00", "milestones", "ABC-M-002", "forecast_date", "2026-10-01", "2026-10-08"),
                ("2026-09-29 10:00:00", "milestones", "ABC-M-002", "forecast_date", "2026-10-08", "2026-10-15")])
        with open(v.root / "system/staging/mentions.jsonl", "w") as f:
            for src in ("fp:2026-09-27|steering|aa", "fp:2026-10-04|steering|bb", "fp:2026-10-04|steering|bb"):
                f.write(json.dumps({"at": src[3:13], "id": "ABC-010", "run": "cx-minutes", "source": src}) + "\n")
            f.write(json.dumps({"at": "2026-10-04", "id": "ABC-011", "run": "cx-minutes", "source": "x"}) + "\n")
            f.write(json.dumps({"at": "2026-10-05", "id": "ABC-011", "run": "cx-sweep", "source": "y"}) + "\n")
        cls.base = (v.root / "system/config/settings.json").read_text()

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def setUp(self):
        (self.v.root / "system/config/settings.json").write_text(self.base)

    def by(self, ws):
        return {(w["sig"], w["id"]): w["text"] for w in ws}

    def test_each_signal_on_constructed_history(self):
        got = self.by(warnings(self.v))
        self.assertEqual(got[("redated", "ABC-A-001")], "Re-dated 3 times (last on 10-10-2026)")
        self.assertNotIn(("redated", "ABC-A-002"), got)          # 2 re-dates: the first date and the undone one don't count
        self.assertNotIn(("redated", "ABC-A-003"), got)          # closed
        self.assertEqual(got[("repeat_risk", "ABC-010")], "Raised in 3 meetings or sweeps, with no response yet")
        self.assertNotIn(("repeat_risk", "ABC-011"), got)        # has a response
        self.assertEqual(got[("milestone_slip", "ABC-M-001")], "Forecast moved later 2 weeks running (now 10-11-2026)")
        self.assertNotIn(("milestone_slip", "ABC-M-002"), got)   # slipped two weeks running, but not lately
        self.assertEqual(got[("long_open", "ABC-A-004")], "Open 43 days; ABC's actions usually close in 4")
        self.assertNotIn(("long_open", "ABC-A-001"), got)        # 13 days: under the 14-day floor
        self.assertTrue(all(w["p"] == "ABC" and w["k"] in ("actions", "raid", "milestones") for w in warnings(self.v)))

    def test_thresholds_and_switches(self):
        set_warnings(self.v, redated__times=2, repeat_risk__mentions=4, milestone_slip__weeks=3, long_open__factor=20)
        got = self.by(warnings(self.v))
        self.assertIn(("redated", "ABC-A-002"), got)
        self.assertNotIn(("repeat_risk", "ABC-010"), got)
        self.assertNotIn(("milestone_slip", "ABC-M-001"), got)
        self.assertNotIn(("long_open", "ABC-A-004"), got)
        set_warnings(self.v, redated__on=False, repeat_risk__on=False, milestone_slip__on=False, long_open__on=False)
        self.assertEqual(warnings(self.v), [])

    def test_in_health_evidence_and_the_weekly_draft(self):
        data = json.loads(py(self.v, "import json, report\nprint(json.dumps(report.weekly_data('ABC')))"))
        self.assertIn("ABC-A-001: Re-dated 3 times (last on 10-10-2026)", data["early_warnings"])
        self.assertEqual(len(data["early_warnings"]), 4)
        ev = json.loads(py(self.v, "import json, report\nprint(json.dumps(report.health_evidence('ABC')))"))
        self.assertEqual(ev["warnings"], data["early_warnings"])

    def test_in_the_dashboard_data(self):
        self.v.run(script="build_dashboard.py")
        import re
        html = (self.v.root / "dashboard.html").read_text(encoding="utf-8")
        d = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))
        self.assertTrue(isinstance(d["warnings"], list))     # built with today's date; the signals are tested above
        self.assertEqual(d["warn_settings"]["redated"], {"on": True, "times": 3})

    def test_repeat_mentions_are_logged_at_staging(self):
        """A duplicate skipped by minutes.py stage or sweep.py stage is logged as a mention of the open item."""
        log_file = self.v.root / "system/staging/mentions.jsonl"
        before = log_file.read_text()
        spec = self.v.root / "system/staging/drafts/spec.json"
        spec.write_text(json.dumps({"date": "2026-10-13", "title": "ABC Steering 13", "projects": ["ABC"], "items": [
            {"table": "raid", "values": {"project": "ABC", "type": "Risk", "description": "Data access delayed"}}]}))
        self.v.run("stage", str(spec), script="minutes.py", ok=False)
        sweep = self.v.root / "system/staging/drafts/sweep.json"
        sweep.write_text(json.dumps({"window": {}, "items": [
            {"table": "actions", "values": {"project": "ABC", "description": "Send revised SOW",
                                            "source": "Email · From: Sam · Link: https://outlook/abc"}}]}))
        self.v.run("stage", str(sweep), script="sweep.py")
        added = [json.loads(ln) for ln in log_file.read_text()[len(before):].splitlines()]
        self.assertEqual([(m["id"], m["run"]) for m in added], [("ABC-010", "cx-minutes"), ("ABC-A-001", "cx-sweep")])
        self.assertEqual(added[1]["source"], "https://outlook/abc")
        log_file.write_text(before)
        for p in (self.v.root / "system/staging").glob("proposed-*.json"):
            p.unlink()


def data_of(v):
    import re
    html = (v.root / "dashboard.html").read_text(encoding="utf-8")
    return json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))


def chrome(v, script, name="probe"):
    """Load the built dashboard headless with `script` appended; it must set window.OUT. Returns OUT and errors."""
    import shutil
    import tempfile
    from test_dashboard import CHROME
    html = (v.root / "dashboard.html").read_text(encoding="utf-8")
    probe = v.root / f"{name}.html"
    probe.write_text(html.replace("</body>", "<script>window.addEventListener('load',async()=>{try{" + script +
                                  "}catch(e){window.OUT={error:String(e&&e.stack||e)}} const p=document.createElement('pre');"
                                  "p.id='out';p.textContent=JSON.stringify(window.OUT);document.body.appendChild(p);});"
                                  "</script></body>"), encoding="utf-8")
    import html as h
    import re
    # A headless Chrome on a runner running a dozen other browsers can outlast any one timeout (and then prints no page at all):
    # give each try three minutes and try again, once more, only if it printed nothing.
    for _ in range(3):
        profile = tempfile.mkdtemp(prefix="creaite-chrome-")
        cmd = [str(CHROME), "--headless", "--disable-gpu", f"--user-data-dir={profile}", "--no-first-run",
               "--disable-component-update", "--disable-background-networking", "--enable-logging=stderr", "--v=0",
               "--virtual-time-budget=4000", "--dump-dom", probe.as_uri()]
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=180)
            out, err = r.stdout, r.stderr
        except subprocess.TimeoutExpired as e:
            out, err = e.stdout or b"", e.stderr or b""
        finally:
            shutil.rmtree(profile, ignore_errors=True)
        m = re.search(r'<pre id="out">(.*?)</pre>', out.decode("utf-8", "ignore"), re.S)
        if m:
            break
    errors = [ln for ln in err.decode("utf-8", "ignore").splitlines() if "CONSOLE" in ln and ("Uncaught" in ln or "Error" in ln)]
    return (json.loads(h.unescape(m.group(1))) if m else None), errors


class MeetingPrepTests(unittest.TestCase):
    """BL-49: today's meetings matched to a project, the portfolio or nothing; the brief in Chrome."""

    @classmethod
    def setUpClass(cls):
        from test_dashboard import d, populate
        cls.v = v = Vault()
        populate(v)
        (v.root / ABC / "minutes" / f"{d(-7)} ABC Steering.docx").write_bytes(b"x")    # the series' last meeting
        today = d(0)
        events = [{"start": "09:00", "end": "09:30", "title": "ABC Steering", "where": "Teams"},
                  {"start": "10:00", "end": "10:30", "title": "Weekly sync 12", "where": "Room 4"},
                  {"start": "11:00", "end": "11:30", "title": "Portfolio review"},
                  {"start": "12:00", "end": "12:30", "title": "Portal walkthrough"},
                  {"start": "13:00", "end": "14:00", "title": "Busy", "private": True}]
        (v.root / "system/staging/calendar.json").write_text(json.dumps({"fetched": today + " 07:00", "days": {today: events}}))
        v.run(script="build_dashboard.py")
        cls.data, cls.today, cls.d = data_of(v), today, staticmethod(d)

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def test_matching_and_since(self):
        m = self.data["prep"]["meetings"]
        self.assertEqual({k: (x["p"], x["how"]) for k, x in m.items()}, {
            "09:00|ABC Steering": ("ABC", "matched"), "10:00|Weekly sync 12": (None, "unsure"),
            "11:00|Portfolio review": ("_portfolio", "portfolio"), "12:00|Portal walkthrough": ("DEF", "matched")})
        self.assertEqual((m["09:00|ABC Steering"]["last"], m["09:00|ABC Steering"]["since"]), (self.d(-7), self.d(-7)))
        self.assertEqual((m["10:00|Weekly sync 12"]["last"], m["10:00|Weekly sync 12"]["since"]), (None, self.d(-7)))
        self.assertEqual(m["10:00|Weekly sync 12"]["series"], "weekly sync")              # numbers dropped

    def test_a_remembered_series(self):
        cfg = self.v.root / "system/config/settings.json"
        base = cfg.read_text()
        data = json.loads(base)
        data["prep"] = {"series": {"weekly sync": "DEF"}}
        cfg.write_text(json.dumps(data))
        try:
            self.v.run(script="build_dashboard.py")
            self.assertEqual(data_of(self.v)["prep"]["meetings"]["10:00|Weekly sync 12"]["p"], "DEF")
            self.assertEqual(data_of(self.v)["prep"]["meetings"]["10:00|Weekly sync 12"]["how"], "remembered")
        finally:
            cfg.write_text(base)
            self.v.run(script="build_dashboard.py")

    def test_brief_in_chrome(self):
        from test_dashboard import CHROME
        if not CHROME.exists():
            self.skipTest("Google Chrome not installed")
        out, errors = chrome(self.v, """
          const wait=ms=>new Promise(r=>setTimeout(r,ms)); go("today"); await wait(50);
          const links=[...document.querySelectorAll("#dayMeets .preplink")].map(b=>b.getAttribute("aria-label"));
          document.querySelector('[data-prep="0"]').click(); await wait(50);
          const dlg=document.getElementById("prepDlg"), body=()=>dlg.innerText;
          const matched={open:dlg.open, title:document.getElementById("prepTitle").textContent, text:body(),
                         proj:document.getElementById("prepProjBtn").dataset.code};
          dlg.querySelector('[data-open^="actions:"]').click(); await wait(50);
          const opened={dlg:dlg.open, panel:document.getElementById("panel").classList.contains("on"), cur:CUR&&CUR.id};
          closePanel(); await wait(50); opened.back=dlg.matches(":modal"); dlg.close(); document.querySelector('[data-prep="1"]').click(); await wait(50);
          const unsure={text:body(), proj:document.getElementById("prepProjBtn").dataset.code};
          dlg.close(); document.querySelector('[data-prep="2"]').click(); await wait(50);
          const portfolio=body();
          window.OUT={links, matched, opened, unsure, portfolio};""")
        self.assertEqual(errors, [])
        self.assertEqual(out["links"], ["Prepare for ABC Steering", "Prep for Weekly sync 12", "Prepare for Portfolio review",
                                        "Prep for Portal walkthrough"])   # none for the private one; BL-293: Prepare when worth it
        mt = out["matched"]
        self.assertTrue(mt["open"])
        self.assertEqual((mt["title"], mt["proj"]), ("ABC Steering", "ABC"))
        self.assertIn("Escalate data access to the client CIO", mt["text"])                  # open actions, overdue first
        self.assertLess(mt["text"].index("Escalate data access"), mt["text"].index("Book UAT environment"))
        self.assertIn("Test licences not ordered", mt["text"])                                # issue, no response
        self.assertIn("Go-live moves two weeks", mt["text"])                                  # decided since the last meeting
        self.assertIn(f"Since the last meeting ({self.d(-7)[8:10]}-{self.d(-7)[5:7]}-{self.d(-7)[:4]})", mt["text"])
        self.assertEqual(out["opened"]["dlg"], True)                                          # a line opens its item in the peek, over the popup (BL-286 E)
        self.assertTrue(out["opened"]["panel"])
        self.assertTrue(out["opened"]["back"])                                                # closing the peek brings the popup back, modal
        self.assertIn("Not sure which project", out["unsure"]["text"])
        self.assertEqual(out["unsure"]["proj"], "")
        self.assertIn("Across every project", out["portfolio"])
        self.assertIn("Agree pilot success criteria", out["portfolio"])                       # DEF, due soon


CAPTURE_SCRIPT = r"""
<script>
(async()=>{ const out={errors:[]}, wait=ms=>new Promise(r=>setTimeout(r,ms)); window.ASKED=[];
  askLive=async(q,c)=>{ window.ASKED.push([q,c]); };      // the stream itself is tested at the server
  try{
    await checkLive(); go("inbox"); await wait(50);
    out.box=!!document.querySelector("#v-inbox #qcap"); out.notToday=!document.querySelector("#v-today #qcap"); out.ck=ckItems("quick").map(i=>i.l);
    document.getElementById("qcNotes").focus(); await wait(20); out.more=!document.getElementById("qcMore").hidden;
    document.getElementById("qcNotes").value="Sara confirmed the pilot extends to 60 agents.\nAlan to update the plan by Friday.";
    document.getElementById("qcProj").value="ABC"; document.getElementById("qcWho").value="Sara Example";
    await qcProcess(); out.asked=ASKED.slice(); out.cleared=document.getElementById("qcNotes").value;
    document.getElementById("qcNotes").value="Lunch with the team"; await qcProcess(); await wait(50);
    out.unsure=document.getElementById("qcMsg").textContent; out.unsureOpen=!document.getElementById("qcMore").hidden;
    window.ASKED=[]; await handle("note: DEF portal walkthrough booked for March"); out.note=ASKED.slice(); out.noteMsg=document.getElementById("qcMsg").textContent; out.chat=[...document.querySelectorAll("#chLog .msg")].map(m=>m.textContent).slice(-2);
  }catch(e){ out.errors.push(String(e&&e.stack||e)); }
  const pre=document.createElement("pre"); pre.id="result"; pre.textContent=JSON.stringify(out); document.body.appendChild(pre);
})();
</script>
"""


class QuickCaptureTests(unittest.TestCase):
    """BL-54: the note saved (name, folder, no overwrite) through /api/capture, a run started on it, cx-minutes'
    note staging, and the Today box, ⌘K and "note:" in headless Chrome."""

    @classmethod
    def setUpClass(cls):
        import socket
        import time
        import urllib.request
        from test_dashboard import populate
        from test_live_server import FAKE_CLAUDE
        cls.v = v = Vault()
        populate(v)
        fake = v.root / "fake_claude.py"
        fake.write_text(FAKE_CLAUDE)
        fake.chmod(0o755)
        (v.root / "inject.html").write_text(CAPTURE_SCRIPT)
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            cls.port = s.getsockname()[1]
        cls.base = f"http://127.0.0.1:{cls.port}"
        env = {**os.environ, "CREAITE_PORT": str(cls.port), "CREAITE_CLAUDE": str(fake),
               "CREAITE_TEST_INJECT": str(v.root / "inject.html")}
        cls.proc = subprocess.Popen([sys.executable, str(v.root / "system/scripts/live_server.py")], env=env,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            try:
                urllib.request.urlopen(cls.base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        import re
        page = urllib.request.urlopen(cls.base + "/").read().decode()
        cls.token = json.loads(re.search(r'id="data">(.*?)</script>', page, re.S).group(1).replace("<\\/", "</"))["token"]

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)
        cls.v.cleanup()

    def post(self, path, body):
        import urllib.error
        import urllib.request
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read().decode()
                return r.status, (json.loads(raw) if r.headers.get_content_type() == "application/json" else raw)
        except urllib.error.HTTPError as e:
            with e:
                return e.code, json.loads(e.read() or b"{}")

    def test_note_saved_named_and_never_overwritten(self):
        minutes = self.v.root / ABC / "minutes"
        st, r = self.post("/api/capture", {"notes": "Pilot extends to 60 agents.", "code": "ABC", "date": "2026-10-06",
                                           "title": "Call with Sara", "who": "Sara Example"})
        self.assertEqual((st, r["path"], r["code"], r["matched"]),
                         (200, f"{ABC}/minutes/2026-10-06 Quick note - Call with Sara.md", "ABC", False))
        text = (minutes / "2026-10-06 Quick note - Call with Sara.md").read_text()
        self.assertIn("- **Date:** 06-10-2026\n- **Project:** ABC Example Programme\n- **Who was there:** Sara Example", text)
        self.assertTrue(text.rstrip().endswith("Pilot extends to 60 agents."))
        st, r2 = self.post("/api/capture", {"notes": "Second call.", "code": "ABC", "date": "2026-10-06", "title": "Call with Sara"})
        self.assertEqual(r2["name"], "2026-10-06 Quick note - Call with Sara (2).md")       # never overwrites
        st, r3 = self.post("/api/capture", {"notes": "ABC: legal / SOW signed?\nmore", "date": "2026-10-06"})
        self.assertEqual((r3["name"], r3["matched"]), ("2026-10-06 Quick note - ABC legal SOW signed.md", True))  # title from the first line
        for name in (r["name"], r2["name"], r3["name"]):
            (minutes / name).unlink()

    def test_refused_or_unclear(self):
        self.assertEqual(self.post("/api/capture", {"notes": "  "})[0], 400)
        self.assertEqual(self.post("/api/capture", {"notes": "x", "code": "ABC", "date": "06-10-2026"})[0], 400)
        self.assertEqual(self.post("/api/capture", {"notes": "x", "code": "ZZZ"})[0], 400)
        self.assertEqual(self.post("/api/capture", {"notes": "x" * 20001, "code": "ABC"})[0], 413)
        st, r = self.post("/api/capture", {"notes": "Lunch with the team"})
        self.assertEqual((st, r["candidates"]), (409, []))
        st, r = self.post("/api/capture", {"notes": "ABC and DEF both slipping"})
        self.assertEqual((st, r["candidates"]), (409, ["ABC", "DEF"]))

    def test_a_run_starts_on_the_note(self):
        """The page sends "process <note>" as a confirmed request: write tools allowed, streamed like any run."""
        import urllib.request
        st, r = self.post("/api/capture", {"notes": "Pilot extends.", "code": "ABC", "date": "2026-10-06", "title": "Run"})
        req = urllib.request.Request(self.base + "/api/ask", method="POST", headers={
            "Content-Type": "application/json", "X-Creaite-Token": self.token}, data=json.dumps({
                "message": f"process {r['path']}", "confirmed": 'Process the quick note "Run" (ABC) into proposed items',
                "run": "capture-run-1"}).encode())
        with urllib.request.urlopen(req, timeout=60) as resp:
            evs = [json.loads(ln[6:]) for ln in resp.read().decode().splitlines() if ln.startswith("data: ")]
        self.assertIn({"type": "text", "text": "Write tools allowed."}, evs)
        self.assertEqual(evs[-1]["type"], "done")
        self.post("/api/ask/ack", {"run": "capture-run-1"})
        (self.v.root / r["path"]).unlink()

    def test_note_staged_and_recorded_as_processed(self):
        """minutes.py stage with "note": nothing copied or moved, the note is each item's source, processed on apply."""
        st, r = self.post("/api/capture", {"notes": "Alan to update the plan.", "code": "ABC", "date": "2026-10-06",
                                           "title": "Stage me"})
        spec = self.v.root / "system/staging/drafts/note.json"
        spec.write_text(json.dumps({"title": "Quick note - Stage me", "date": "2026-10-06", "projects": ["ABC"],
                                    "note": r["path"], "items": [{"table": "actions", "section": "Actions", "values": {
                                        "project": "ABC", "description": "Update the plan for the pilot extension",
                                        "owner": "Alan Carter"}}]}))
        before = {p.name for p in (self.v.root / "system/staging").glob("proposed-*.json")}
        self.v.run("stage", str(spec), script="minutes.py")
        new_file = next(p for p in (self.v.root / "system/staging").glob("proposed-*.json") if p.name not in before)
        prop = json.loads(new_file.read_text())
        self.assertEqual(prop["meeting"]["file_ops"], [])
        self.assertEqual((prop["meeting"]["note"], prop["meeting"]["minutes_decision"]), (r["path"], "approved"))
        self.assertEqual(prop["items"][0]["values"]["source"], f"{r['path']} — Actions")
        prop["items"][0]["decision"] = "approved"
        new_file.write_text(json.dumps(prop))
        self.v.run("apply")
        self.assertIn(prop["meeting"]["key"], (self.v.root / "system/processed.txt").read_text())
        self.assertTrue((self.v.root / r["path"]).exists())                                  # left where it was filed
        self.assertIn("Update the plan for the pilot extension", [a["description"] for a in self.v.rows("actions")])
        spec.write_text(json.dumps({"title": "Quick note - Stage me", "date": "2026-10-06", "projects": ["ABC"],      # the command deleted its spec (BL-118)
                                    "note": r["path"], "items": []}))
        self.assertIn("Already processed", self.v.run("stage", str(spec), script="minutes.py", ok=False).stdout)
        self.v.run("undo")
        (self.v.root / r["path"]).unlink()

    def test_today_box_palette_and_note_in_chrome(self):
        import re
        import shutil
        import tempfile
        from test_dashboard import CHROME
        if not CHROME.exists():
            self.skipTest("Google Chrome not installed")
        profile = tempfile.mkdtemp(prefix="creaite-chrome-")
        cmd = [str(CHROME), "--headless", "--disable-gpu", f"--user-data-dir={profile}", "--no-first-run",
               "--disable-component-update", "--disable-background-networking", "--virtual-time-budget=8000",
               "--dump-dom", self.base + "/"]
        try:
            out = subprocess.run(cmd, capture_output=True, timeout=90).stdout
        except subprocess.TimeoutExpired as e:
            out = e.stdout or b""
        finally:
            shutil.rmtree(profile, ignore_errors=True)
        import html as h
        m = re.search(r'<pre id="result">(.*?)</pre>', out.decode("utf-8", "ignore"), re.S)
        self.assertTrue(m, "the live page didn't finish the scripted steps")
        r = json.loads(h.unescape(m.group(1)))
        self.assertEqual(r["errors"], [])
        self.assertTrue(r["box"] and r["more"] and r["notToday"])          # BL-66: on the Intake page, not Today
        self.assertIn("Quick capture", r["ck"])
        (q, title), = r["asked"]
        self.assertEqual(q, f"process {ABC}/minutes/{q.split('/minutes/')[1]}")
        self.assertRegex(q, r"/minutes/\d{4}-\d{2}-\d{2} Quick note - Sara confirmed the pilot extends to 60 agents\.md$")
        self.assertIn("without Word minutes", title)
        self.assertEqual(r["cleared"], "")
        self.assertIn("couldn't tell which project", r["unsure"])
        self.assertTrue(r["unsureOpen"])
        self.assertEqual(len(r["note"]), 1, (r.get("noteMsg"), r.get("chat")))               # "note: …" in ask creaite
        (q2, _), = r["note"]
        self.assertRegex(q2, r"^process projects/DEF Digital Enablement/minutes/\d{4}-\d{2}-\d{2} Quick note - DEF portal walkthrough booked for March\.md$")
        for f in list((self.v.root / ABC / "minutes").glob("* Quick note - *")) + \
                list((self.v.root / "projects/DEF Digital Enablement/minutes").glob("* Quick note - *")):
            f.unlink()


if __name__ == "__main__":
    unittest.main(verbosity=2)
