"""BL-286 (sprint-prep-server): meeting prep, reimagined: the server and Python side.

Run: python3 dev/tests/test_prep_reimagined.py
Covers the shaping reply's checks on fixture replies (good, a missing citation, a wrong section), the focus filter, prep-focus.json
(save, regenerate keeping Alan's edits, clear), the stored content route, the dated reporting, the series counts, the Agendas page
re-rendered without overwriting Alan's edits, and the confidential path never reading the invite. A stand-in Claude is used: no
model is called, nothing is sent, and the tracker never changes.
"""
import json
import os
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "system" / "scripts"))
import prep_shape  # noqa: E402
from test_dashboard import TODAY, d  # noqa: E402
from test_decisions_prep import prep_world  # noqa: E402
from test_tracker import ABC, Vault, action  # noqa: E402

KEY = "09:00|ABC weekly"
SOURCES = [{"ref": "S1", "id": "", "kind": "instruction", "text": "Alan's instruction", "link": {"type": "alan", "label": "Your instruction"}},
           {"ref": "S2", "id": "ABC-A-001", "kind": "item", "text": "ABC-A-001", "link": {"type": "item", "id": "ABC-A-001", "label": "ABC-A-001"}},
           {"ref": "S3", "id": "", "kind": "carried", "text": "Not covered", "link": {"type": "carried", "label": "Minutes"}}]
GOOD = """FOCUS: ABC-A-001; carried over: load test approver
AIM: A date from Jane for data access
SHOW: focus-only
OBJECTIVE:
- Leave with a committed date for data access (ABC-A-001). [S1, S2]
TALKING POINTS:
- Escalation to the CIO is three days overdue. [S2]
ASK:
- Jane: a date for data access. [S1]
CARRIED OVER:
- Who approves the load test plan. [S3]
"""
FAKE = r'''#!/usr/bin/env python3
import json, sys
args = sys.argv[1:]
p = args[args.index("--") + 1]
open(__file__ + ".calls", "a", encoding="utf-8").write(json.dumps({"prompt": p[:200], "allowed": args[args.index("--allowedTools") + 1],
     "denied": args[args.index("--disallowedTools") + 1]}) + "\n")
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init", "session_id": "sess-s"})
reply = ("FOCUS: ABC-A-001\nAIM: A date for data access\nSHOW: focus-first\nOBJECTIVE:\n- Agree a date for data access. [S1, S2]\n"
         "TALKING POINTS:\n- The escalation is overdue. [S2]\nASK:\n- Jane: a date. [S1]\nCARRIED OVER:\n- none\n")
out({"type": "assistant", "message": {"content": [{"type": "text", "text": reply}]}})
out({"type": "result", "result": reply, "session_id": "sess-s"})
'''


def py(v, code):
    """Run Python in the vault with its scripts on the path; its stdout's last line as JSON."""
    r = subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts'); " + code], cwd=v.root,
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout.strip().splitlines()[-1])


def world(v, confidential=False):
    """prep_world, plus: the series' two earlier meetings (minutes, items raised there, a point not covered), a link, a weekly
    report, and invitees given as addresses (one in the people register, one not)."""
    prep_world(v)
    for back in (14, 7):
        f = v.root / ABC / "minutes" / f"{d(-back)} ABC weekly.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("# ABC weekly\n\nABC-A-001 discussed.\n")
    src = f"{ABC}/minutes/{d(-7)} ABC weekly.md — Actions"
    v.propose("series", [action(1, description="Confirm the load test plan", due_date=d(5), source=src),
                         action(2, description="Share the latency results", due_date=d(6), source=src),
                         {"n": 3, "op": "new", "table": "links", "match": "strong", "flags": [], "decision": "approved",
                          "values": {"from_item": "ABC-003", "to_item": "ABC-A-001", "source": "Alan (cx-edit)"}}])
    v.run("apply")
    (v.root / "system/staging/carried.json").write_text(json.dumps({"points": [
        {"series": "abc weekly", "point": "Who approves the load test plan", "key": "k", "day": d(-7), "title": "ABC weekly"}]}))
    rep = v.root / ABC / "reports" / f"{d(-4)} Weekly report - Example Programme.docx"
    rep.parent.mkdir(parents=True, exist_ok=True)
    rep.write_bytes(b"x")
    cal = json.loads((v.root / "system/staging/calendar.json").read_text())
    ev = cal["days"][TODAY.isoformat()][0]
    ev["attendees"] += [{"name": "omar@def.example", "email": "omar@def.example"}, {"name": "lucy.hart@vendor.com"}]
    ev["recurrence"] = "weekly"
    if confidential:
        ev.update({"sensitivity": "confidential", "body": "Board secret: the merger plan", "where": "Room 7", "attendees": []})
    (v.root / "system/staging/calendar.json").write_text(json.dumps(cal))


class ReplyChecks(unittest.TestCase):
    """The shaping reply's checks, on fixture replies: no vault, no model."""

    def parse(self, reply):
        return prep_shape.parse(reply, SOURCES, ["ABC-A-001", "ABC-003"])

    def test_a_good_reply_gives_the_reading_and_cited_notes(self):
        out = self.parse(GOOD)
        self.assertTrue(out["ok"], out["checks"])
        self.assertEqual(out["reading"]["focus"][0], {"id": "ABC-A-001", "text": "ABC-A-001"})
        self.assertEqual(out["reading"]["show"], "focus-only")
        self.assertEqual(out["reading"]["aim"], "A date from Jane for data access")
        obj = out["notes"]["objective"][0]
        self.assertEqual(obj["text"], "Leave with a committed date for data access (ABC-A-001).")
        self.assertEqual([s["type"] for s in obj["sources"]], ["alan", "item"])
        self.assertEqual(out["notes"]["ask"][0]["text"], "Jane: a date for data access.")      # "Jane:" is a line, not a heading
        self.assertEqual(len(out["notes"]["carried_over"]), 1)

    def test_a_line_with_no_citation_or_a_made_up_one_is_an_error(self):
        out = self.parse(GOOD.replace("overdue. [S2]", "overdue.").replace("a date for data access. [S1]",
                                                                            "a date for data access. [S9]"))
        self.assertFalse(out["ok"])
        notes = {(c["section"], c["note"]) for c in out["checks"]}
        self.assertIn(("Talking points", "Line 1 cites no source."), notes)
        self.assertIn(("Ask", "Line 1 cites S9, which isn't a source."), notes)

    def test_a_wrong_section_is_reported_and_left_out(self):
        out = self.parse(GOOD.replace("TALKING POINTS:", "RISKS:"))
        self.assertFalse(out["ok"])
        self.assertIn("Risks isn't a section of the notes; its lines are left out.", [c["note"] for c in out["checks"]])
        self.assertEqual(out["notes"]["talking_points"], [])
        self.assertIn("The reply has no Talking points section.", [c["note"] for c in out["checks"]])

    def test_an_unknown_focus_id_and_a_missing_objective_are_errors(self):
        out = self.parse(GOOD.replace("FOCUS: ABC-A-001", "FOCUS: ABC-A-999").split("OBJECTIVE:")[0] + "ASK:\n- x [S1]\n")
        notes = [c["note"] for c in out["checks"] if c["level"] == "error"]
        self.assertIn("ABC-A-999 isn't in your project record.", notes)
        self.assertIn("The reply has no Objective section.", notes)


class Merge(unittest.TestCase):
    """Regenerate keeps the sections Alan edited unless he clears them."""

    def test_edited_sections_are_kept_and_clear_takes_the_new_draft(self):
        old = {"objective": [{"text": "Old objective"}], "ask": [{"text": "Old ask"}]}
        mine = {"objective": [{"text": "Old objective"}], "ask": [{"text": "My own ask"}]}
        new = {"objective": [{"text": "New objective"}], "ask": [{"text": "New ask"}], "talking_points": [{"text": "New point"}]}
        notes, kept = prep_shape.merge(new, {"notes": mine, "drafted": old})
        self.assertEqual((notes["objective"][0]["text"], notes["ask"][0]["text"]), ("New objective", "My own ask"))
        self.assertIn("ask", kept)
        notes, kept = prep_shape.merge(new, {"notes": mine, "drafted": old}, clear=["ask"])
        self.assertEqual(notes["ask"][0]["text"], "New ask")
        notes, _ = prep_shape.merge(new, {"notes": mine, "drafted": old}, clear=True)
        self.assertEqual(notes["ask"][0]["text"], "New ask")
        self.assertEqual(prep_shape.merge(new, None)[0]["talking_points"][0]["text"], "New point")


class InTheVault(unittest.TestCase):
    """The plain-code parts against a real tracker: the focus filter, the focus store, reporting, the series, the page."""

    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        world(cls.v)

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def test_1_the_focus_filter_lists_linked_items_and_documents_with_why(self):
        f = py(self.v, "import prep_shape; con = prep_shape.ro(); "
                       "print(json.dumps(prep_shape.focus_filter(con, ['ABC'], ['ABC-A-001'], {'ABC-A-002'})))")
        by = {i["id"]: i for i in f["items"]}
        self.assertEqual(by["ABC-A-001"]["why"], ["in focus"])
        self.assertIn("blocks ABC-A-001", by["ABC-003"]["why"])                                   # the links table
        self.assertTrue(any(w.startswith("same milestone (UAT start)") for w in by["ABC-A-002"]["why"]))
        self.assertTrue(any(w.startswith("cited in the same minutes") for w in by["ABC-A-002"]["why"]))
        self.assertTrue(by["ABC-A-002"]["excluded"])                                               # ticked out: listed, not counted
        self.assertEqual(f["n"], sum(1 for i in f["items"] if not i["excluded"]))
        self.assertGreater(f["N"], f["n"])
        docs = {x["path"]: x for x in f["documents"]}
        steering = next(p for p in docs if "Steering" in p)
        self.assertIn("ABC-A-001 comes from it", docs[steering]["why"])
        self.assertEqual(py(self.v, "import prep_shape; con = prep_shape.ro(); "
                                    "print(json.dumps(prep_shape.focus_filter(con, ['ABC'], ['ABC-A-001'], (), True)['documents']))"), [])

    def test_2_save_regenerate_keep_edits_and_clear(self):
        drafted = {"objective": [{"text": "Agree a date"}], "ask": [{"text": "Jane: a date"}]}
        rec = py(self.v, f"import prep_shape; r, e = prep_shape.save({KEY!r}, {TODAY.isoformat()!r}, "
                         f"{{'instruction': 'Focus on ABC-A-001', 'reading': {{'focus': [{{'id': 'ABC-A-001', 'text': 'ABC-A-001'}}], "
                         f"'aim': 'A date', 'show': 'focus-only'}}, 'drafted': {drafted!r}, 'notes': {drafted!r}, 'accept': True}}); "
                         "print(json.dumps([r, e]))")
        self.assertEqual((rec[0]["edited"], rec[1]), ([], "used"))
        mine = {**drafted, "ask": [{"text": "Jane: commit to a date, or accept masked data"}]}
        rec = py(self.v, f"import prep_shape; r, e = prep_shape.save({KEY!r}, {TODAY.isoformat()!r}, {{'notes': {mine!r}, "
                         f"'accept': True}}); print(json.dumps([r, e]))")
        self.assertEqual((rec[0]["edited"], rec[1]), (["ask"], "edited"))
        stored = json.loads((self.v.root / "system/staging/prep-focus.json").read_text())["meetings"]
        self.assertEqual(list(stored), [f"{TODAY.isoformat()}|{KEY}"])                             # one canonical key per meeting
        new = {"objective": [{"text": "A fresh objective"}], "ask": [{"text": "A fresh ask"}]}
        merged = py(self.v, f"import prep_shape; print(json.dumps(prep_shape.merge({new!r}, "
                            f"prep_shape.get('{TODAY.isoformat()}|{KEY}'))))")
        self.assertEqual(merged[0]["objective"][0]["text"], "A fresh objective")
        self.assertEqual(merged[0]["ask"][0]["text"], "Jane: commit to a date, or accept masked data")
        self.assertEqual(merged[1], ["ask"])

    def test_3_dated_reporting(self):
        rep = py(self.v, f"import prep_page, prep_view; print(json.dumps(prep_view.dated_reporting(prep_page.context({KEY!r}))))")[0]
        self.assertRegex(rep["line"], r"^Weekly report · week ending \d{2}-\d{2}-\d{4} · ▲ At risk$")
        self.assertTrue(rep["headline"].startswith("Build is two weeks behind"))
        self.assertLessEqual(len(rep["points"]), 3)
        kinds = {r["kind"]: r for r in rep["reports"]}
        self.assertEqual(kinds["Weekly report"]["date_shown"], f"{d(-4)[8:10]}-{d(-4)[5:7]}-{d(-4)[:4]}")
        self.assertEqual(kinds["Weekly report"]["link"]["type"], "file")
        self.assertEqual(kinds["Weekly report"]["link"]["kind"], "word")
        self.assertIn("Client report", kinds)

    def test_4_the_series_counts_and_the_popup_facts(self):
        b = py(self.v, f"import prep_view; print(json.dumps(prep_view.brief({KEY!r})))")
        self.assertTrue(b["ok"], b)
        last = f"{d(-7)[8:10]}-{d(-7)[5:7]}-{d(-7)[:4]}"
        self.assertEqual(b["series"]["text"], f"Every week · 3rd meeting · last {last}")
        self.assertTrue(b["facts"]["text"].startswith(f"Since the last meeting ({last}): "), b["facts"]["text"])
        names = [p["name"] for p in b["people"]["invitees"]]
        self.assertEqual(names, ["Sara Example", "Omar Ali", "Lucy Hart"])                         # addresses resolved to names
        self.assertEqual([p["registered"] for p in b["people"]["invitees"]], [True, True, False])
        self.assertFalse(any("@" in n for n in names))
        self.assertEqual(b["people"]["organiser"]["name"], "Jane Doe")
        s = py(self.v, f"import prep_page, prep_view; d = prep_page._collect(); ctx = prep_page.context({KEY!r}); "
                       f"print(json.dumps(prep_view.series(d, ctx, d['prep']['meetings'][{KEY!r}])))")
        rows = {r["day"]: r for r in s["meetings"]}
        self.assertTrue(rows[TODAY.isoformat()]["this"])
        self.assertEqual(rows[d(-7)]["raised"], {"actions": 2, "decisions": 0, "raid": 0})
        self.assertEqual(rows[d(-7)]["not_covered"], 1)
        self.assertEqual(rows[d(-14)]["raised"]["actions"], 0)
        self.assertEqual(rows[d(-7)]["minutes"]["path"], f"{ABC}/minutes/{d(-7)} ABC weekly.md")

    def test_5_chips_come_from_the_ranking_overdue_and_carried(self):
        c = py(self.v, f"import prep_shape; print(json.dumps(prep_shape.chips({KEY!r})))")
        kinds = [x["kind"] for x in c["chips"]]
        self.assertIn("invite", kinds)
        self.assertIn("overdue", kinds)
        self.assertIn("carried", kinds)
        self.assertLessEqual(len(kinds), prep_shape.MAX_CHIPS)
        self.assertTrue(all(x["insert"] for x in c["chips"]))

    def test_6_typed_sources(self):
        t = py(self.v, "import prep_view; print(json.dumps([prep_view.typed(s) for s in ["
                       "'Email · From: Jane Doe · Subject: Hi · Sent: 2026-10-01 09:00 · Link: https://outlook.office365.com/x', "
                       "'Teams · Chat: Omar · From: Omar · Sent: 2026-10-01 09:00', 'ABC-A-001', "
                       f"'{ABC}/minutes/2026-10-01 Steering.docx — Actions', 'Email · Link: javascript:alert(1)']]))")
        self.assertEqual((t[0]["type"], t[0]["url"]), ("mail", "https://outlook.office365.com/x"))
        self.assertNotIn("Link", t[0]["label"])
        self.assertEqual(t[1], {"type": "teams", "label": "Teams · Chat: Omar · From: Omar · Sent: 2026-10-01 09:00"})
        self.assertEqual(t[2], {"type": "item", "id": "ABC-A-001", "label": "ABC-A-001"})
        self.assertEqual((t[3]["type"], t[3]["kind"], t[3]["section"]), ("file", "word", "Actions"))
        self.assertNotIn("url", t[4])                                                              # only an https link is a link


def confidential_prompt(v):
    r = subprocess.run([sys.executable, "system/scripts/drafts.py", "context"], cwd=v.root, capture_output=True, text=True,
                       input=json.dumps({"kind": "shape", "key": KEY, "instruction": "Focus on ABC-A-001 only."}))
    return json.loads(r.stdout)


class Confidential(unittest.TestCase):
    """A confidential meeting is shaped from Alan's text and the tracker only."""

    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        world(cls.v, confidential=True)

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def test_the_shaping_prompt_never_holds_the_invite(self):
        ctx = confidential_prompt(self.v)
        self.assertTrue(ctx["extra"]["confidential"])
        self.assertNotIn("Board secret", ctx["prompt"])
        self.assertNotIn("Room 7", ctx["prompt"])
        self.assertIn("This meeting is confidential", ctx["prompt"])
        self.assertEqual({s["kind"] for s in ctx["sources"]} - {"instruction", "item", "milestone"}, set())
        self.assertNotIn("carried", {s["kind"] for s in ctx["sources"]})

    def test_the_closed_run_gets_no_tools_and_every_reading_tool_is_denied(self):
        got = py(self.v, "import live_server as ls; print(json.dumps([ls.run_tools('shape-closed', None), "
                         "ls.KIND_DENIES['shape-closed'], ls.run_tools('generate', None) == ls.READ_TOOLS]))")
        self.assertEqual(got[0], [])
        for t in ("Read", "Bash", "WebSearch"):
            self.assertIn(t, got[1])
        self.assertTrue(any("Microsoft_365" in t or "outlook" in t.lower() for t in got[1]), got[1])
        self.assertTrue(got[2])

    def test_no_chips_from_the_invite(self):
        c = py(self.v, f"import prep_shape; print(json.dumps(prep_shape.chips({KEY!r})))")
        self.assertTrue(c["confidential"])
        self.assertEqual([x for x in c["chips"] if x["kind"] in ("invite", "carried")], [])


class ThroughTheServer(unittest.TestCase):
    """The routes: shape (streamed, counted), the stored content, Accept regenerating the Agendas page without overwriting
    Alan's edits."""

    @classmethod
    def setUpClass(cls):
        from test_live_server import free_port
        cls.v = v = Vault()
        world(v)
        fake = v.root / "fake_shape.py"
        fake.write_text(FAKE)
        fake.chmod(0o755)
        cls.calls = Path(str(fake) + ".calls")
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
        import re
        html = urllib.request.urlopen(cls.base + "/").read().decode()
        cls.token = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]
        cls.db = (v.root / "system/tracker.db").read_bytes()

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)
        cls.v.cleanup()

    def post(self, path, body, stream=False):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        with urllib.request.urlopen(req, timeout=90) as r:
            raw = r.read().decode()
        if stream:
            return [json.loads(ln[6:]) for ln in raw.splitlines() if ln.startswith("data: ")]
        return json.loads(raw)

    def test_1_shape_streams_a_checked_draft_and_counts_it(self):
        evs = self.post("/api/prep/shape", {"key": KEY, "instruction": "Focus on ABC-A-001. I want a date from Jane."}, stream=True)
        src = next(e for e in evs if e["type"] == "sources")
        self.assertFalse(src["confidential"])
        self.assertEqual(src["sources"][0]["kind"], "instruction")
        draft = next(e for e in evs if e["type"] == "draft")
        self.assertTrue(draft["ok"] and draft["checks_ok"], draft)
        self.assertEqual(draft["reading"]["focus"][0]["id"], "ABC-A-001")
        self.assertEqual(draft["checks"], [])
        self.assertEqual(draft["notes"]["objective"][0]["text"], "Agree a date for data access.")
        self.assertEqual(draft["notes"]["carried_over"], [])
        stats = json.loads((self.v.root / "system/staging/draft-stats.json").read_text())
        self.assertEqual(stats["shape"]["offered"], 1)
        call = json.loads(self.calls.read_text().splitlines()[-1])
        self.assertNotEqual(call["allowed"], "")                                                   # not confidential: read tools
        self.assertFalse((self.v.root / "system/staging/prep-focus.json").exists())                 # nothing saved before Accept

    def test_2_the_view_shows_the_stored_content_without_running_claude(self):
        self.assertFalse(self.post("/api/prep/view", {"key": KEY})["stored"])
        py(self.v, f"import prep_page; rel, _ = prep_page.build({KEY!r}, {{'about': 'The weekly check-in.', 'notes': [{{'text': "
                   f"'Licences quote due Friday', 'source': 'Email · From: Jane Doe · Subject: Quote · Sent: {d(-1)} 09:00 · "
                   f"Link: https://outlook.office365.com/q', 'date': '{d(-1)}'}}], 'questions': ['Is UAT booked?']}}); print(json.dumps(rel))")
        before = self.calls.read_text() if self.calls.exists() else ""
        v = self.post("/api/prep/view", {"key": KEY})
        self.assertTrue(v["ok"] and v["stored"], v)
        mo = v["model"]
        self.assertTrue(mo["internal"])
        self.assertEqual(mo["notes"][0]["source"]["url"], "https://outlook.office365.com/q")
        self.assertEqual(mo["questions"], ["Is UAT booked?"])
        self.assertTrue(v["saved"]["path"].endswith(f"{TODAY.isoformat()} Prep - ABC weekly.html"))
        self.assertEqual(mo["meeting"]["project_name"], "Example Programme")                       # BL-101: by name
        self.assertTrue(mo["brief"]["series"]["text"].startswith("Every week"))
        self.assertEqual((self.calls.read_text() if self.calls.exists() else ""), before)          # Claude never ran
        stored = list((self.v.root / "system/staging/prep").glob("*.json"))
        self.assertEqual(len(stored), 1)
        page = (self.v.root / v["saved"]["path"]).read_text()
        self.assertIn('class="brief"', page)                                                        # the Briefing layout
        self.assertIn('<aside class="rail">', page)
        self.assertIn("This series", page)

    def test_3_accept_regenerates_the_page_and_never_overwrites_alans_edit(self):
        notes = {"objective": [{"text": "Leave with a date for data access", "sources": [{"type": "item", "id": "ABC-A-001",
                                                                                           "label": "ABC-A-001"}]}]}
        got = self.post("/api/prep/focus/save", {"key": KEY, "instruction": "Focus on ABC-A-001", "accept": True, "drafted": notes,
                                                 "notes": notes, "reading": {"focus": [{"id": "ABC-A-001", "text": "ABC-A-001"}],
                                                                             "aim": "A date", "show": "focus-only"}})
        self.assertTrue(got["ok"], got)
        page = self.v.root / got["page"]
        self.assertTrue(got["page"].endswith(f"{TODAY.isoformat()} Prep - ABC weekly.html"))
        self.assertIn("Leave with a date for data access", page.read_text())
        self.assertIn("Work items in focus", page.read_text())
        self.assertTrue(list((self.v.root / "system/backups/files").glob("*Prep - ABC weekly.html")))   # creaite's own, backed up
        page.write_text(page.read_text() + "<!-- Alan's note -->")
        again = self.post("/api/prep/focus/save", {"key": KEY, "notes": {"objective": [{"text": "A changed objective"}]}})
        self.assertTrue(again["page"].endswith("ABC weekly (2).html"), again["page"])
        self.assertIn("Alan's note", page.read_text())                                             # left alone
        self.assertNotIn("A changed objective", page.read_text())
        self.assertIn("A changed objective", (self.v.root / again["page"]).read_text())
        self.assertEqual(self.post("/api/prep/focus", {"key": KEY})["focus"]["edited"], ["objective"])
        stats = json.loads((self.v.root / "system/staging/draft-stats.json").read_text())
        self.assertEqual(stats["shape"]["used"], 1)
        flt = self.post("/api/prep/filter", {"key": KEY})
        self.assertEqual(flt["show"], "focus-only")
        self.assertIn("ABC-A-001", [i["id"] for i in flt["filter"]["items"]])
        self.assertTrue(self.post("/api/prep/focus/clear", {"key": KEY})["cleared"])
        self.assertIsNone(self.post("/api/prep/focus", {"key": KEY})["focus"])

    def test_4_brief_and_chips_routes_and_a_bad_key(self):
        self.assertTrue(self.post("/api/prep/brief", {"key": KEY})["facts"]["text"].startswith("Since the last meeting"))
        self.assertTrue(self.post("/api/prep/chips", {"key": KEY})["chips"])
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.post("/api/prep/view", {"key": "no key"})
        self.assertEqual(e.exception.code, 400)
        e.exception.close()

    def test_5_the_tracker_never_changed(self):
        self.assertEqual((self.v.root / "system/tracker.db").read_bytes(), self.db)


if __name__ == "__main__":
    unittest.main()
