"""v2.1.0 P7 (BL-338): the minutes view, in a real browser on the real live server (LiveBrowserCase; no Claude runs at all).

A fictional steering committee is staged as a minutes record over the sample portfolio (test_dashboard.populate): a VTT
transcript with timed turns, an agenda with a point not discussed, three actions (one owner the people register doesn't know,
one deadline said as "by Friday"), a decision and a risk. The view opens from Review's Open draft and from its address.

- #268 (Minutes view v2): one version only, so there is no distributed version, Side by side or Internal only mark to test
  here any more (the server's distributed export keeps its own tests in test_minutes_approve).
- Popups close on Esc and on a click outside, with focus back on the button that opened them: the deadline popover, a check,
  Deal with it… and the Before approving box (#268: 480 px, shown only when a ticked item has a real problem).
- #268: a crossed line is left out of Show as exported; a line with neither ticked stays (the Track column replaces ✕ Remove
  and Keep the line only; test_minutes_view_v2 has the rest).
- The deadline popover: words worked out from the meeting's date (shown before they are set), the quick picks with their
  dates, a day from the calendar, Not set; each changes the row and its staged item together.
- Time tags scroll the transcript pane to what was said; coverage's Deal with it… carries a point with a line in the minutes.

Run: python3 dev/tests/test_minutes_editor.py      (Chrome tier; skipped without Chrome)
"""
import json
import os
import subprocess
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import d, populate  # noqa: E402
from test_tracker import ABC, Vault  # noqa: E402

TITLE = "[ABC] Steering committee"
DAY = d(-1)
while date.fromisoformat(DAY).weekday() not in (1, 2, 3):   # the minutes say "by Friday": the meeting is held on a Tuesday to Thursday, whatever day the run is pinned to (#178)
    DAY = (date.fromisoformat(DAY) - timedelta(days=1)).isoformat()
TURNS = [(0, 1, "Alan Carter", "Morning all, first the SOW."), (0, 20, "Omar Ali", "I'll send the revised SOW next week."),
         (1, 5, "Jane Doe", "We agreed the pilot stays on the lighthouse site."),
         (2, 10, "Omar Ali", "Data access is still late, that's the risk."),
         (3, 0, "Sara Example", "I'll book the UAT test environment by Friday."), (4, 30, "Alan Carter", "Thanks all.")]
VTT = "WEBVTT\n\n" + "".join(f"00:{m:02d}:{s:02d}.000 --> 00:{m:02d}:{s + 5:02d}.000\n<v {who}>{text}</v>\n\n" for m, s, who, text in TURNS)
SHOTS = (Path.home() / "dev.env/team-stark-shots/p7-followup") if os.environ.get("P7_SHOTS") else None
DRAFT = f"system/staging/drafts/{DAY} Steering committee.html"


def meeting_spec():
    """The meeting as cx-minutes writes it (meeting.json)."""
    p = {"project": "ABC"}
    return {
        "title": TITLE, "date": DAY, "projects": ["ABC"], "transcript": f"inbox/{DAY} Steering committee.vtt",
        "coverage": [{"point": "SOW sign-off", "verdict": "Covered"}, {"point": "Training plan", "verdict": "Not discussed"},
                     {"point": "Budget review", "verdict": "Touched on"}],
        "minutes": {"start": "10:00", "end": "11:00", "chat": False,
                    "attendees": "Jane Doe (Example Client Ltd); Alan Carter, Omar Ali, Sara Example",
                    "summary": [{"text": "The committee reviewed the SOW and the pilot site.", "turn": 1},
                                {"text": "Data access remains the main risk.", "at": "00:02:11"}],
                    "updates": [{"heading": "SOW", "items": [{"text": "Omar is revising the SOW.", "at": "00:00:21"},
                                                             {"flag": "PRIORITY", "text": "Sign-off is needed first.", "turn": 1}]},
                                {"heading": "Pilot", "items": [{"text": "The pilot stays on the lighthouse site.", "at": "00:01:06"}]}],
                    "open_questions": [{"text": "Who owns the cut-over extract?", "turn": 6}]},
        "items": [
            {"table": "actions", "turn": 2, "due_words": "next week",
             "values": {**p, "description": "Send the revised SOW to the client", "owner": "Omar Ali"}},
            {"table": "actions", "turn": 5, "due_words": "next week",
             "values": {**p, "description": "Book the UAT test environment", "owner": "Sara Example"}},
            {"table": "actions", "values": {**p, "description": "Share the cut-over plan with the client", "owner": "Pat Unknown"}},
            {"table": "decisions", "at": "00:01:06", "values": {**p, "decision": "The pilot stays on the lighthouse site",
                                                                 "made_by": "Jane Doe"}},
            {"table": "raid", "turn": 4, "values": {**p, "type": "Risk", "description": "Data access late → the MVP slips"}},
        ]}


def stage_meeting(v):
    """Stage the meeting in vault `v` (minutes.py stage, the real script): its proposal's file name."""
    (v.root / "inbox" / f"{DAY} Steering committee.vtt").write_text(VTT, encoding="utf-8")
    ag = v.root / ABC / "agendas"
    ag.mkdir(parents=True, exist_ok=True)
    (ag / f"{DAY} Steering committee agenda.md").write_text("# Steering committee\n\n- SOW sign-off\n- Training plan\n- Budget review\n",
                                                            encoding="utf-8")
    before = {p.name for p in (v.root / "system/staging").glob("proposed-*.json")}
    f = v.root / "system/staging/drafts/meeting.json"
    f.write_text(json.dumps(meeting_spec()), encoding="utf-8")
    v.run("stage", str(f), script="minutes.py")
    return next(p.name for p in (v.root / "system/staging").glob("proposed-*.json") if p.name not in before)


_SAMPLE = {}


def sample_view():
    """The /api/minutes/draft answer for the staged meeting, made once in a throwaway vault (for test_ui_sweep, which answers
    the route with it so its sample vault stays as it is)."""
    if "view" not in _SAMPLE:
        v = Vault()
        try:
            populate(v)
            name = stage_meeting(v)
            r = subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts'); import minutes_record; "
                                f"print(json.dumps(minutes_record.view({name!r})))"], cwd=v.root, capture_output=True, text=True, check=True)
            _SAMPLE["view"] = json.loads(r.stdout.strip().splitlines()[-1])
        finally:
            v.cleanup()
    return _SAMPLE["view"]


def open_sample(b):
    """Open the minutes view with /api/minutes/draft answered by sample_view() (every other call goes to the server)."""
    b.eval(f"(()=>{{ if(window.__mnSample) return; window.__mnSample=1; const real=window.fetch.bind(window), ans={json.dumps(json.dumps(sample_view()))}; "
           "window.fetch=(u,o)=>String(u).endsWith('/api/minutes/draft')?Promise.resolve(new Response(ans,{headers:{'Content-Type':'application/json'}})):real(u,o); })()")
    b.eval(f"go('minutes',{{path:{json.dumps(DRAFT)}}})")


class MinutesEditor(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        populate(v)
        cls.proposal = stage_meeting(v)

    def setUp(self):
        super().setUp()
        self.b.eval(f"go('minutes',{{file:{json.dumps(self.proposal)}}})")
        self.b.wait("document.querySelector('#v-minutes tr.mi')", 15)

    # ── helpers ──
    def ev(self, js):
        return self.b.eval(js)

    def staged(self, n):
        data = json.loads((self.v.root / "system/staging" / self.proposal).read_text(encoding="utf-8"))
        return next(i for i in data["items"] if i["n"] == n)

    def record(self):
        r = subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts'); import creaite_doc; "
                            f"print(json.dumps(creaite_doc.read({DRAFT!r})))"], cwd=self.v.root, capture_output=True, text=True, check=True)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def rows(self, sid="actions"):
        return [r for s in self.record()["sections"] if s["id"] == sid for r in s["rows"]]

    def active(self):
        return self.ev("(()=>{const a=document.activeElement; return a?(a.id||a.getAttribute('aria-label')||a.textContent||'').trim():''})()")

    def click_outside(self):
        self.b.click("#v-minutes .sheet-zv")                    # in the toolbar, which stays on screen when the header hides on a scroll (#202)
        self.b.pump(0.2)

    def wait_saved(self, js):
        self.b.wait(js, 15)
        self.b.pump(0.3)

    # ── tests ──
    def test_1_opens_from_review_and_its_address_with_the_transcript_and_time_tags(self):
        b = self.b
        self.assertEqual(self.ev("VIEW"), "minutes")
        self.assertEqual(self.ev("location.hash"), "#minutes=" + self.ev(f"encodeURIComponent({json.dumps(DRAFT)})"))
        self.assertEqual(self.ev("document.querySelector('.rail button[aria-current=page]').dataset.v"), "review", "under Review, no new page")
        self.assertEqual(self.ev("document.querySelectorAll('.mnturns li').length"), 6)
        self.assertGreater(self.ev("document.querySelectorAll('#v-minutes .page .mntag').length"), 2)   # #268: the summary is edited in place, so its lines carry no tags now
        turn = self.ev("(()=>{const t=[...document.querySelectorAll('#v-minutes .page .mntag')].find(t=>t.textContent==='01:06'); t.click(); return t.dataset.turn})()")
        b.pump(0.3)
        self.assertEqual(self.ev("document.querySelector('.mnturns li.on').dataset.turn"), turn, "the tag's turn is highlighted")
        top = self.ev("document.querySelector('#v-minutes .sheet-scroll').scrollTop")
        self.assertEqual(top, 0, "the sheet itself never moves")
        b.reload("typeof go==='function' && LIVE && document.querySelector('#v-minutes tr.mi')")
        self.assertEqual(self.ev("VIEW"), "minutes", "a reload keeps the minutes")

    def test_2_one_version_only(self):
        """#268 change 1 (Alan: "I only ever want one version of minutes"): the One version / Internal + distributed switch, the
        Internal / Distributed / Side by side switch and the Internal only marks are gone; Export offers no distributed file."""
        self.assertFalse(self.ev("!!document.querySelector('#v-minutes .seg, #v-minutes [data-mnmode], #v-minutes .mnio, #v-minutes .sheet-pair')"))
        names = self.menu_names()
        self.assertFalse([n for n in names if "Distributed" in n or "Internal:" in n], names)
        self.b.key("Escape")

    def test_3_popups_close_on_esc_and_a_click_outside_with_focus_back(self):
        b = self.b
        openers = {                                       # #268: the owner is an in-row dropdown now, not a popover
            "deadline": "#v-minutes tr.mi[data-n='1'] .mndue",
            "check": "#v-minutes tr.mi[data-n='2'] .mnrow2 .mncheck",
        }
        for name, sel in openers.items():
            if not sel:
                continue
            for how in ("esc", "outside"):
                with self.subTest(popup=name, close=how):
                    b.click(sel)
                    b.wait("document.querySelector('#v-minutes .mnpop')")
                    self.assertTrue(self.ev("document.querySelector('#v-minutes .mnpop').contains(document.activeElement)"), "focus moves in")
                    if how == "esc":
                        b.key("Escape")
                        b.pump(0.2)
                        self.assertTrue(self.ev(f"document.activeElement===document.querySelector({json.dumps(sel)})"), "focus back on its button")
                    else:
                        self.click_outside()
                    self.assertFalse(self.ev("!!document.querySelector('#v-minutes .mnpop')"), f"{name} closed by {how}")
                    self.assertEqual(self.ev("VIEW"), "minutes", "Esc goes no further")
        for name, sel in (("coverage", "[data-mncover='Training plan']"),):     # #268: no Remove menu (the Track column's cross)
            for how in ("esc", "outside"):
                with self.subTest(popup=name, close=how):
                    b.click(sel)
                    b.wait("document.querySelector('#v-minutes .ddmenu.on')")
                    if how == "esc":
                        b.key("Escape")
                        b.pump(0.2)
                        self.assertTrue(self.ev(f"document.activeElement===document.querySelector({json.dumps(sel)})"))
                    else:
                        self.click_outside()
                    self.assertFalse(self.ev("!!document.querySelector('#v-minutes .ddmenu.on')"))
        for how in ("esc", "outside"):
            with self.subTest(popup="approve", close=how):
                b.click("#mnApproveBtn")
                b.wait("document.getElementById('mnApprove').open")
                self.assertEqual(round(self.ev("document.getElementById('mnApprove').getBoundingClientRect().width")), 480)   # #268: the small Before approving box
                if how == "esc":
                    b.key("Escape")
                else:
                    x, y = self.ev("(()=>{const r=document.getElementById('mnApprove').getBoundingClientRect(); return [r.left-20, r.top+20]})()")
                    for kind in ("mousePressed", "mouseReleased"):
                        b.call("Input.dispatchMouseEvent", type=kind, x=x, y=y, button="left", clickCount=1)
                b.pump(0.3)
                self.assertFalse(self.ev("document.getElementById('mnApprove').open"))
                self.assertEqual(self.ev("document.activeElement.id"), "mnApproveBtn")

    def test_4_a_crossed_line_is_left_out_of_show_as_exported(self):
        """#268 change 2 replaces ✕ Remove and Keep the line only: a cross removes the line from the minutes (on approval), neither keeps
        it as a line with no item. Show as exported shows the minutes as they will be filed."""
        b = self.b
        b.click("#v-minutes tr.mi[data-n='1'] .mntrk button.n")
        b.pump(0.2)
        b.click("#v-minutes .sheet-exp")
        b.wait("document.querySelector('#v-minutes .sheet-exp').getAttribute('aria-pressed')==='true'")
        b.pump(0.3)
        page = self.ev("document.querySelector('#v-minutes .page').textContent")
        self.assertNotIn("Send the revised SOW to the client", page, "the crossed line is left out")
        self.assertIn("Book the UAT test environment", page)
        self.assertIn("The pilot stays on the lighthouse site", page, "neither: the line stays")
        self.assertFalse(self.ev("!!document.querySelector('#v-minutes .page .mntrk')"), "no Track column in the exported view")
        b.click("#v-minutes .sheet-exp")
        b.pump(0.2)
        self.assertEqual(self.staged(1)["decision"], "pending", "nothing changes before Approve minutes")

    def test_5_the_deadline_popover_works_words_out_from_the_meetings_date(self):
        b = self.b
        sel = "#v-minutes tr.mi[data-n='3'] .mndue"
        self.assertEqual(self.ev(f"document.querySelector({json.dumps(sel)}).textContent"), "Not set")
        b.click(sel)
        b.wait("document.querySelector('.mndl')")
        quick = self.ev("[...document.querySelectorAll('.mndl [data-quick]')].map(x=>[x.dataset.quick, x.getAttribute('aria-label')])")
        want = {w: self.ev(f"CREAITE.parseWhen({json.dumps(w)}, {json.dumps(DAY)}, true, 'deadline')") for w in ("Friday", "next week", "next wednesday", "end of month")}
        for w, label in quick[:4]:
            self.assertIn(self.ev(f"fd({json.dumps(want[w])})"), label, f"{w} shows its date from the meeting's day")
        b.eval("document.getElementById('mnDlWords').focus()")
        b.type("in 2 weeks")
        b.pump(0.2)
        got = self.ev(f"CREAITE.parseWhen('in 2 weeks', {json.dumps(DAY)}, true, 'deadline')")
        self.assertIn(self.ev(f"fd({json.dumps(got)})"), self.ev("document.getElementById('mnDlSaid').textContent"), "the date shown before it is set")
        self.assertIsNone(self.staged(3)["values"].get("due_date"), "nothing set yet")
        b.key("Enter")
        self.wait_saved(f"document.querySelector({json.dumps(sel)}).textContent!=='Not set'")
        self.assertEqual(self.staged(3)["values"]["due_date"], got)
        self.assertEqual(self.ev(f"document.querySelector({json.dumps(sel)}).textContent"), self.ev(f"fd({json.dumps(got)})"))
        self.assertEqual(next(r for r in self.rows() if r.get("n") == 3)["cells"]["due"], self.ev(f"fd({json.dumps(got)})"))
        self.assertTrue(self.ev(f"document.activeElement===document.querySelector({json.dumps(sel)})"), "focus back on the deadline")
        b.click(sel)
        b.wait("document.querySelector('.mndl')")
        b.click(".mndl [data-quick='Friday']")
        friday = self.ev(f"CREAITE.parseWhen('Friday', {json.dumps(DAY)}, true, 'deadline')")
        self.wait_saved(f"document.querySelector({json.dumps(sel)}).textContent==={json.dumps(self.ev(f'fd({json.dumps(friday)})'))}")
        self.assertEqual(self.staged(3)["values"]["due_date"], friday)
        b.click(sel)
        b.wait("document.querySelector('.mndl')")
        b.eval("document.querySelector('.mndl .pkday:not(.on)').click()")
        self.wait_saved(f"document.querySelector({json.dumps(sel)}).textContent!=={json.dumps(self.ev(f'fd({json.dumps(friday)})'))}")
        self.assertTrue(self.staged(3)["values"]["due_date"].startswith(friday[:7]), "a day from the calendar's month")
        b.click(sel)
        b.wait("document.querySelector('.mndl')")
        b.click(".mndl [data-quick='not set']")
        self.wait_saved(f"document.querySelector({json.dumps(sel)}).textContent==='Not set'")
        self.assertIsNone(self.staged(3)["values"].get("due_date"))
        b.click(sel)
        b.wait("document.querySelector('.mndl')")
        b.eval("document.getElementById('mnDlWords').focus()")
        b.type("whenever")
        b.pump(0.2)
        self.assertIn("isn't", self.ev("document.getElementById('mnDlSaid').textContent").replace("Not a date creaite can read", "isn't"))

    def test_6_checks_inline_coverage_and_the_approve_popups_groups(self):
        b = self.b
        self.assertIn("Pat Unknown needs details", self.ev("document.querySelector(\"#v-minutes tr.mi[data-n='3'] .mnrow2\").textContent"))   # #266's wording
        notes = self.ev("[...document.querySelectorAll('#v-minutes .mnrow2 .mncheck')].map(x=>x.getAttribute('aria-label'))")
        self.assertTrue(any("said “by Friday”" in n for n in notes), notes)
        b.eval("[...document.querySelectorAll('#v-minutes .mnrow2 .mncheck')].find(x=>/by Friday/.test(x.getAttribute('aria-label'))).click()")
        b.wait("document.querySelector('.mnck [data-ckact=use]')")
        b.click(".mnck [data-ckact=use]")
        friday = self.ev(f"CREAITE.parseWhen('by Friday', {json.dumps(DAY)}, true, 'deadline')")
        self.wait_saved(f"document.querySelector(\"#v-minutes tr.mi[data-n='2'] .mndue\").textContent==={json.dumps(self.ev(f'fd({json.dumps(friday)})'))}")
        self.assertEqual(self.staged(2)["values"]["due_date"], friday, "Use that sets what was said")
        b.click("[data-mncover='Training plan']")
        b.click("#v-minutes .ddmenu.on [role=menuitem]:nth-of-type(1)")
        self.wait_saved("document.querySelector('[data-point=\"Training plan\"] .mncov-done')")
        nc = next(s for s in self.record()["sections"] if s["id"] == "not_covered")
        self.assertIn("Training plan was not discussed; it is carried to the next", nc["text"])
        b.click("#mnApproveBtn")                              # #268: the box lists only the ticked items with a real problem
        b.wait("document.getElementById('mnApprove').open")
        self.assertIn("Pat Unknown needs details", self.ev("document.getElementById('mnApprove').textContent"))
        self.assertNotIn("pilot stays", self.ev("document.getElementById('mnApprove').textContent"), "the decision isn't ticked")

    # ── v2.1.0 P7 follow-up (Alan, 15-10-2026): Draft the follow-up email, in the Export menu ──
    def shots(self, name):
        """With P7_SHOTS set: the open draft at 1400 and 900 px."""
        if not SHOTS:
            return
        SHOTS.mkdir(parents=True, exist_ok=True)
        for w in (1400, 900):
            self.b.resize(w, 900)
            self.b.pump(0.4)
            self.b.screenshot(str(SHOTS / f"{name}-{w}.png"))
        self.b.resize(1400, 900)

    def menu_names(self):
        self.b.click("#v-minutes [data-mnexport]")
        self.b.wait("document.querySelector('#v-minutes .ddmenu.on')")
        return self.ev("[...document.querySelectorAll('#v-minutes .ddmenu.on [role=menuitem]')].map(x=>x.textContent)")

    def pick(self, label):
        self.b.eval("[...document.querySelectorAll('#v-minutes .ddmenu.on [role=menuitem]')].find(x=>x.textContent.includes(%s)).click()" % json.dumps(label))
        self.b.wait("document.getElementById('deDlg') && document.getElementById('deDlg').open && document.querySelector('#dePrev').textContent.length>20", 15)
        self.b.pump(0.4)

    def test_7_follow_up_email_internal_version_is_marked_internal(self):
        names = self.menu_names()
        self.assertTrue(any("Draft the follow-up email" in n for n in names), names)
        self.assertEqual(sum("follow-up" in n for n in names), 1, "one version: one entry")
        self.pick("Draft the follow-up email")
        self.assertEqual(self.ev("document.querySelector('#deSubj').value").startswith("[Internal] "), True)
        prev = self.ev("document.querySelector('#dePrev').textContent")
        self.assertIn("Internal: not for distribution.", prev)
        self.assertIn("Send the revised SOW", self.ev("document.getElementById('deDlg').textContent"))
        self.shots("internal")


if __name__ == "__main__":
    unittest.main()
