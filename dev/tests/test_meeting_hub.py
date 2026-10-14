"""BL-209: the meeting hub (one page per meeting, from invite to follow-up) and Coverage (was the agenda discussed?).

Run: python3 dev/tests/test_meeting_hub.py   (the browser half needs Google Chrome; skipped otherwise)
The clock is fixed to Wednesday 14-10-2026 15:00. The meetings are fictional: a steering tomorrow with its prep page, a design
review this morning whose transcript is ready, last week's steering (two projects, an agenda, coverage, waiting in Review), and a
quick note. Nothing here calls Microsoft 365 or a model.
"""
import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from live_browser import LiveBrowserCase, pin_page_clock  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_tracker import ABC, Vault  # noqa: E402

NOW = "2026-10-14 15:00"
ENV = {**os.environ, "CREAITE_NOW": NOW}
PREP = (ABC + "/agendas/2026-10-15 ABC Steering prep.html")


def py(v, code):
    r = subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts')\n" + code], cwd=v.root,
                       capture_output=True, text=True, env=ENV)
    if r.returncode:
        raise AssertionError(r.stdout + r.stderr)
    return r.stdout


def run(v, *args, script="minutes.py", ok=True):
    r = subprocess.run([sys.executable, str(v.root / "system/scripts" / script), *args], cwd=v.root, capture_output=True, text=True, env=ENV)
    if ok and r.returncode:
        raise AssertionError(r.stdout + r.stderr)
    return r


def load(v):
    populate(v)
    st = v.root / "system/staging"
    (st / "calendar.json").write_text(json.dumps({"fetched": "2026-10-14 07:00", "days": {
        "2026-10-08": [{"id": "e3", "start": "10:00", "end": "11:00", "title": "ABC Steering", "teams": True}],
        "2026-10-14": [{"id": "e2", "start": "09:00", "end": "09:45", "title": "ABC Design review", "teams": True}],
        "2026-10-15": [{"id": "e1", "start": "10:00", "end": "11:00", "title": "ABC Steering", "teams": True}]}}))
    (st / "transcripts.json").write_text(json.dumps({"checked": {"e2": {"status": "available", "checked": "2026-10-14 10:00"}}}))
    agendas = v.root / ABC / "agendas"
    agendas.mkdir(parents=True, exist_ok=True)
    (agendas / "2026-10-08 ABC Steering agenda.md").write_text("# ABC Steering\n\n1. UAT readiness\n2. Budget\n3. Vendor risk\n")
    (v.root / PREP).write_text('<html><body><details open><summary><h2>Questions and asks</h2></summary><ul><li>Is UAT on for 04-11?</li></ul>'
                               '</details></body></html>')
    (st / "prep-pages.json").write_text(json.dumps({PREP: {"sha": "x", "key": "2026-10-15|10:00|ABC Steering", "day": "2026-10-15",
                                                           "at": "2026-10-14 08:00"}}))
    shutil.copy(v.root / "system/templates/minutes-template.docx", st / "drafts/2026-10-08 ABC Steering.docx")
    (v.root / "inbox").mkdir(exist_ok=True)
    (v.root / "inbox/steering.vtt").write_text("WEBVTT\n\n00:00:01.000 --> 00:00:05.000\n<v Alan>UAT is ready for November.\n")
    spec = st / "drafts/steering.json"
    spec.write_text(json.dumps({"title": "ABC Steering", "date": "2026-10-08", "event_id": "e3", "projects": ["ABC", "DEF"],
                                "draft": "system/staging/drafts/2026-10-08 ABC Steering.docx", "transcript": "inbox/steering.vtt",
                                "items": [{"table": "actions", "section": "Actions", "values": {
                                    "project": "ABC", "description": "Book the UAT room", "owner": "Sara Example", "raised": "2026-10-08"}}],
                                "coverage": [{"point": "UAT readiness", "verdict": "Covered"}, {"point": "Budget", "verdict": "Not discussed"},
                                             {"point": "UAT is ready for November", "verdict": "Touched on"}]}))
    out = run(v, "stage", str(spec)).stdout
    note = v.root / ABC / "minutes/2026-10-13 Quick note - Corridor chat.md"
    note.write_text("# Quick note — Corridor chat\n\nSara will chase the licences.\n")
    spec2 = st / "drafts/note.json"
    spec2.write_text(json.dumps({"title": "Quick note - Corridor chat", "date": "2026-10-13", "projects": ["ABC"],
                                 "note": f"{ABC}/minutes/2026-10-13 Quick note - Corridor chat.md",
                                 "coverage": [{"point": "Budget", "verdict": "Covered"}],
                                 "items": [{"table": "actions", "section": "Actions", "values": {
                                     "project": "ABC", "description": "Chase the test licences", "owner": "Sara Example"}}]}))
    out2 = run(v, "stage", str(spec2)).stdout
    run(v, script="build_dashboard.py")
    return out, out2


def hub(v):
    return json.loads(py(v, "import build_dashboard as b\nprint(json.dumps(b.collect()['hub']))").strip().splitlines()[-1])


def by(h, **kw):
    return next(m for m in h.values() if all(m.get(k) == x for k, x in kw.items()))


def steps(m):
    return {k: (s, t) for k, _, s, t in m["steps"]}


class HubData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        cls.stage_out, cls.note_out = load(cls.v)
        cls.h = hub(cls.v)

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def test_a_meeting_tomorrow_with_its_prep_page_waits_for_nothing(self):
        m = by(self.h, key="calendar:e1")
        s = steps(m)
        self.assertEqual(s["invite"][0], "done")
        self.assertEqual(s["prep"], ("done", "Prep page made"))
        self.assertEqual(m["prep"], PREP)
        self.assertNotIn("current", [x[0] for x in s.values()])
        self.assertIsNone(m["next"])

    def test_a_meeting_this_morning_with_a_transcript_ready(self):
        m = by(self.h, key="calendar:e2")
        s = steps(m)
        self.assertEqual(s["prep"][0], "skip")
        self.assertEqual(s["transcript"], ("current", "Ready to load"))
        self.assertEqual(m["next"], {"act": "intake", "label": "Load the transcript"})

    def test_a_multi_project_meeting_is_one_hub_waiting_in_review_with_its_coverage(self):
        m = by(self.h, key="calendar:e3")
        self.assertEqual(sorted(m["p"]), ["ABC", "DEF"])
        self.assertEqual(len([x for x in self.h.values() if x["key"] == "calendar:e3"]), 1)
        s = steps(m)
        self.assertEqual(s["draft"][0], "done")
        self.assertEqual(s["coverage"], ("done", "1 of 2 not discussed"))
        self.assertEqual(s["review"], ("current", "2 waiting for you"))
        self.assertEqual(m["next"], {"act": "review", "label": "Review the minutes and 1 item"})
        self.assertEqual([x["t"] for x in m["items"]], ["Book the UAT room"])
        self.assertTrue(m["items"][0]["you"])

    def test_coverage_keeps_the_agendas_own_points_and_never_transcript_text(self):
        prop = next(json.loads(p.read_text()) for p in (self.v.root / "system/staging").glob("proposed-*.json")
                    if (json.loads(p.read_text()).get("meeting") or {}).get("key") == "calendar:e3")
        self.assertEqual(prop["meeting"]["coverage"], [{"point": "UAT readiness", "verdict": "Covered"}, {"point": "Budget", "verdict": "Not discussed"}])
        self.assertEqual(prop["meeting"]["agenda"], f"{ABC}/agendas/2026-10-08 ABC Steering agenda.md")
        self.assertNotIn("ready for November", json.dumps(prop["meeting"]))
        self.assertIn("isn't on the agenda; left out", self.stage_out)
        self.assertEqual(json.loads(run(self.v, "agenda", "ABC", "--date", "2026-10-15", "--title", "ABC Steering").stdout)["points"],
                         ["Is UAT on for 04-11?"])                               # no agenda file: the prep page's questions

    def test_a_quick_note_has_no_invite_or_transcript_and_no_agenda_skips_coverage(self):
        m = by(self.h, quick=True)
        s = steps(m)
        self.assertEqual(s["invite"], ("skip", "No invite: a quick note"))
        self.assertEqual(s["transcript"][0], "skip")
        self.assertEqual(s["coverage"], ("skip", "No agenda, so not checked"))
        self.assertIn("coverage left out: this meeting has no agenda", self.note_out)
        self.assertEqual(m["next"]["act"], "review")
        self.assertIn(f"{ABC}/minutes/2026-10-13 Quick note - Corridor chat.md", m["files"])

    def test_carry_to_the_next_agenda_shows_on_the_series_next_prep_page(self):
        self.assertIn("Carried", run(self.v, "carry", "on", "--key", "calendar:e3", "--point", "Budget").stdout)
        out = json.loads(py(self.v, "import minutes, prep_page\nc = minutes.carried_for('ABC Steering', '2026-10-15')\n"
                                    "print(json.dumps({'c': c, 'h': prep_page.carried_html({'carried': prep_page._carried('ABC Steering', '2026-10-15')}),"
                                    "'other': minutes.carried_for('DEF Standup', '2026-10-15'), 'before': minutes.carried_for('ABC Steering', '2026-10-08')}))"))
        self.assertEqual([c["point"] for c in out["c"]], ["Budget"])
        self.assertIn("Not covered last time", out["h"])
        self.assertIn("Budget", out["h"])
        self.assertEqual((out["other"], out["before"]), ([], []))
        self.assertEqual(run(self.v, "carry", "on", "--key", "calendar:e3", "--point", "Lunch", ok=False).returncode, 2)
        self.assertIn("carried_html(ctx)", (Path(__file__).resolve().parents[2] / "system/scripts/prep_page.py").read_text())
        run(self.v, "carry", "off", "--key", "calendar:e3", "--point", "Budget")
        self.assertEqual(json.loads((self.v.root / "system/staging/carried.json").read_text())["points"], [])

    def test_nothing_reaches_the_tracker(self):
        self.assertNotIn("Book the UAT room", [a["description"] for a in self.v.rows("actions")])


class HubBrowser(LiveBrowserCase):
    shared_server = False

    @classmethod
    def load(cls, v):
        load(v)
        cal = v.root / "system/staging/calendar.json"      # the page's Today is the browser's day, pinned to NOW in setUp
        data = json.loads(cal.read_text())                  # (it was the real day: on 14-10-2026 it met the design review)
        data["days"].setdefault(NOW[:10], []).append({"id": "e9", "start": "08:00", "end": "08:30", "title": "ABC Daily check", "teams": True})
        cal.write_text(json.dumps(data))
        run(v, script="build_dashboard.py")

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": NOW}

    def setUp(self):
        super().setUp()
        pin_page_clock(self.b, NOW)                         # the page's clock as the server's, whatever the machine's day

    def token(self, key):
        return self.b.eval(f"Object.entries(D.hub).find(([t,m])=>m.key==={json.dumps(key)})[0]")

    def test_the_page_its_address_and_the_next_step(self):
        b = self.b
        t = self.token("calendar:e3")
        b.eval(f"location.hash='#meeting={t}'")
        b.wait("VIEW==='meeting' && document.querySelector('#v-meeting .mhstrip')")
        self.assertEqual(b.eval("[...document.querySelectorAll('#v-meeting .mhstrip li')].map(l=>l.dataset.step)"),
                         ["invite", "prep", "transcript", "draft", "coverage", "review", "follow"])
        self.assertEqual(b.eval("document.querySelector('#v-meeting .mhstrip [aria-current=step]').dataset.step"), "review")
        self.assertEqual(b.eval("document.querySelector('#v-meeting [data-mhact]').textContent"), "Review the minutes and 1 item")
        self.assertIn("ABC Steering", b.eval("document.title"))
        self.assertIn("Budget", b.eval("document.querySelector('#v-meeting .mhcov').innerText"))
        b.click('#v-meeting [data-mhcarry="1"]')
        b.wait("document.querySelector('#v-meeting [data-mhcarry=\"1\"]').getAttribute('aria-pressed')==='true'")
        self.assertEqual(json.loads((self.v.root / "system/staging/carried.json").read_text())["points"][0]["point"], "Budget")
        b.click("#v-meeting [data-mhact]")
        b.wait("VIEW==='review'")
        b.wait("document.querySelector('#v-review .mhcovrow')")
        self.assertIn("1 of 2 agenda points not fully discussed", b.eval("document.querySelector('#v-review .mhcovrow').innerText"))
        self.assertEqual(b.errors, [])

    def test_links_in_from_today_intake_and_an_unknown_address(self):
        b = self.b
        b.eval("go('today')")
        daily = "[...document.querySelectorAll('#dayMeets .dm')].find(d=>/ABC Daily check/.test(d.innerText))?.querySelector('.mhlink')"
        b.wait(daily)                                       # today also has the design review: the daily check's own link
        b.eval(daily + ".click()")
        b.wait("VIEW==='meeting'")
        self.assertIn("ABC Daily check", b.eval("document.querySelector('#v-meeting h1').textContent"))
        b.eval(f"go('meeting',{json.dumps(self.token('calendar:e2'))})")
        b.wait("/ABC Design review/.test(document.querySelector('#v-meeting h1').textContent)")
        self.assertEqual(b.eval("document.querySelector('#v-meeting [data-mhact]').textContent"), "Load the transcript")
        b.eval("go('inbox')")
        b.wait("document.querySelector('#mtgBody .mhlink')", 15)
        b.eval("location.hash='#meeting=ffffffffff'")
        b.wait("VIEW==='meeting' && /isn't in creaite's records/.test(document.getElementById('v-meeting').innerText)")


if __name__ == "__main__":
    unittest.main()
