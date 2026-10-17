"""v2.1.0 P7 (BL-338): the minutes view, in a real browser on the real live server (LiveBrowserCase; no Claude runs at all).

A fictional steering committee is staged as a minutes record over the sample portfolio (test_dashboard.populate): a VTT
transcript with timed turns, an agenda with a point not discussed, three actions (one owner the people register doesn't know,
one deadline said as "by Friday"), a decision and a risk. The view opens from Review's Open draft and from its address.

- Side by side: with the distributed version on, matching sections and topics are the same height on both pages, so their
  headings stay level.
- Popups close on Esc and on a click outside, with focus back on the button that opened them: the deadline popover, the owner
  picker, a check, the Remove menu, Deal with it… and the approve popup (784 px).
- ✕ Remove takes the item and its line out of the minutes (its proposal item rejected "Removed in the minutes"); Undo on the
  toast brings it back; Keep the line only keeps the words with no item.
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
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import d, populate  # noqa: E402
from test_tracker import ABC, Vault  # noqa: E402

TITLE = "[ABC] Steering committee"
DAY = d(-1)
if date.fromisoformat(DAY).weekday() == 4:      # the minutes say "by Friday": a meeting held ON a Friday has no such check, so on a Saturday run use Thursday
    DAY = d(-2)
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
        self.b.wait("document.querySelector('#v-minutes .mnrow')", 15)

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
        self.assertGreater(self.ev("document.querySelectorAll('#v-minutes .page .mntag').length"), 4)
        b.eval("[...document.querySelectorAll('#v-minutes .page .mntag')].find(t=>t.textContent==='02:11').click()")
        b.pump(0.3)
        self.assertEqual(self.ev("document.querySelector('.mnturns li.on').dataset.turn"), "4", "the tag's turn is highlighted")
        top = self.ev("document.querySelector('#v-minutes .sheet-scroll').scrollTop")
        self.assertEqual(top, 0, "the sheet itself never moves")
        b.reload("typeof go==='function' && LIVE && document.querySelector('#v-minutes .mnrow')")
        self.assertEqual(self.ev("VIEW"), "minutes", "a reload keeps the minutes")

    def test_2_side_by_side_keeps_matching_headings_level(self):
        b = self.b
        b.click('#v-minutes .seg button:nth-child(2)')         # Internal + distributed
        b.wait("document.querySelector('[data-mnmode=side]')")
        b.eval("document.querySelector('.mnlines .mnio').click()")       # one summary line Internal only: the pages differ
        b.click("[data-mnmode=side]")
        b.wait("document.querySelectorAll('.sheet-pair > .sheet-fit > .sheet-a4 > .page').length===2")
        b.pump(0.5)
        tops = self.ev("""(()=>{ const [l,r]=document.querySelectorAll('.sheet-pair > .sheet-fit > .sheet-a4 > .page'), out=[];
          for(const h of l.querySelectorAll('section[data-id] > h2, .mnblock[data-level] > h3')){
            const sec=h.closest('section[data-id]').dataset.id, lv=h.parentElement.dataset.level;
            const o=lv?r.querySelector(`section[data-id="${sec}"] [data-level="${CSS.escape(lv)}"] > h3`):r.querySelector(`section[data-id="${sec}"] > h2`);
            if(o) out.push([sec+(lv?':'+lv:''), Math.round(h.getBoundingClientRect().top), Math.round(o.getBoundingClientRect().top)]); }
          return out; })()""")
        self.assertGreater(len(tops), 6)
        for name, left, right in tops:
            self.assertLessEqual(abs(left - right), 1, f"{name}: {left} and {right}")
        b.eval("document.querySelector('.sheet-scroll').scrollTop=400")
        b.pump(0.3)
        sec = self.ev("""(()=>{ const [l,r]=document.querySelectorAll('.sheet-pair > .sheet-fit > .sheet-a4 > .page');
          return [l.querySelector('section[data-id=actions] > h2').getBoundingClientRect().top, r.querySelector('section[data-id=actions] > h2').getBoundingClientRect().top]; })()""")
        self.assertLessEqual(abs(sec[0] - sec[1]), 1, "still level once scrolled")
        marked = self.ev("document.querySelector('.sheet-pair > .sheet-fit > .sheet-a4 > .page .mnline.internal').textContent")
        self.assertNotIn("The committee reviewed", self.ev("document.querySelectorAll('.sheet-pair > .sheet-fit > .sheet-a4 > .page')[1].textContent"))
        self.assertIn("The committee reviewed", marked)
        b.eval("document.querySelector('.sheet-scroll').scrollTop=0")   # #202: the top brings the full toolbar back
        b.pump(0.3)
        b.click("[data-mnmode=distributed]")                     # the Distributed page alone: the marked line isn't there
        b.wait("!document.querySelector('.sheet-pair')")
        self.assertNotIn("The committee reviewed", self.ev("document.querySelector('#v-minutes .page').textContent"))
        b.click("#v-minutes [data-mnexport]")
        b.wait("document.querySelector('#v-minutes .ddmenu.on')")
        names = self.ev("[...document.querySelectorAll('#v-minutes .ddmenu.on [role=menuitem]')].map(x=>x.textContent)")
        self.assertTrue(any("Distributed: Word" in n and "approved" in n for n in names), names)
        b.key("Escape")

    def test_3_popups_close_on_esc_and_a_click_outside_with_focus_back(self):
        b = self.b
        openers = {
            "deadline": "#v-minutes .mnrow[data-n='1'] .mndue",
            "owner": "#v-minutes .mnrow[data-n='3'] .mnowner",
            "check": "#v-minutes .mnrow[data-n='3'] .mnbar .mncheck",
            "what changes": None,
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
        for name, sel in (("remove", "#v-minutes .mnrow[data-n='1'] [data-mnremove]"), ("coverage", "[data-mncover='Training plan']")):
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
                self.assertEqual(round(self.ev("document.getElementById('mnApprove').getBoundingClientRect().width")), 784)
                if how == "esc":
                    b.key("Escape")
                else:
                    x, y = self.ev("(()=>{const r=document.getElementById('mnApprove').getBoundingClientRect(); return [r.left-20, r.top+20]})()")
                    for kind in ("mousePressed", "mouseReleased"):
                        b.call("Input.dispatchMouseEvent", type=kind, x=x, y=y, button="left", clickCount=1)
                b.pump(0.3)
                self.assertFalse(self.ev("document.getElementById('mnApprove').open"))
                self.assertEqual(self.ev("document.activeElement.id"), "mnApproveBtn")

    def test_4_remove_and_undo_then_keep_the_line_only(self):
        b = self.b
        b.click("#v-minutes .mnrow[data-n='1'] [data-mnremove]")
        b.click("#v-minutes .ddmenu.on [role=menuitem]:nth-of-type(1)")
        self.wait_saved("!document.querySelector(\"#v-minutes .mnrow[data-n='1']\")")
        self.assertEqual(self.staged(1)["decision"], "rejected")
        self.assertEqual(self.staged(1)["reject_reason"], "Removed in the minutes")
        self.assertNotIn(1, [r.get("n") for r in self.rows()])
        self.assertTrue(self.ev("document.getElementById('snack').classList.contains('on') && getComputedStyle(document.getElementById('snackU')).display!=='none'"))
        b.click("#snackU")
        self.wait_saved("document.querySelector(\"#v-minutes .mnrow[data-n='1']\")")
        self.assertEqual(self.staged(1)["decision"], "pending")
        self.assertEqual([r.get("n") for r in self.rows()][:1], [1], "back where it was")
        b.click("#v-minutes .mnrow[data-n='2'] [data-mnremove]")
        b.click("#v-minutes .ddmenu.on [role=menuitem]:nth-of-type(2)")
        self.wait_saved("document.querySelector(\"#v-minutes .mnrow.kept[data-n='2']\")")
        kept = [r for r in self.rows() if r.get("kept_line")]
        self.assertEqual(kept[0]["cells"]["action"], "Book the UAT test environment")
        self.assertIsNone(kept[0]["ref"], "the line only: no item")
        self.assertEqual(self.staged(2)["decision"], "rejected")

    def test_5_the_deadline_popover_works_words_out_from_the_meetings_date(self):
        b = self.b
        sel = "#v-minutes .mnrow[data-n='3'] .mndue"
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
        notes = self.ev("[...document.querySelectorAll('#v-minutes .mnbar .mncheck')].map(x=>x.getAttribute('aria-label'))")
        self.assertTrue(any("Pat Unknown isn't in the people register" in n for n in notes), notes)
        self.assertTrue(any("said “by Friday”" in n for n in notes), notes)
        b.eval("[...document.querySelectorAll('#v-minutes .mnbar .mncheck')].find(x=>/by Friday/.test(x.getAttribute('aria-label'))).click()")
        b.wait("document.querySelector('.mnck [data-ckact=use]')")
        b.click(".mnck [data-ckact=use]")
        friday = self.ev(f"CREAITE.parseWhen('by Friday', {json.dumps(DAY)}, true, 'deadline')")
        self.wait_saved(f"document.querySelector(\"#v-minutes .mnrow[data-n='2'] .mndue\").textContent==={json.dumps(self.ev(f'fd({json.dumps(friday)})'))}")
        self.assertEqual(self.staged(2)["values"]["due_date"], friday, "Use that sets what was said")
        b.click("[data-mncover='Training plan']")
        b.click("#v-minutes .ddmenu.on [role=menuitem]:nth-of-type(1)")
        self.wait_saved("document.querySelector('[data-point=\"Training plan\"] .mncov-done')")
        nc = next(s for s in self.record()["sections"] if s["id"] == "not_covered")
        self.assertIn("Training plan was not discussed; it is carried to the next", nc["text"])
        b.click("#mnApproveBtn")
        b.wait("document.getElementById('mnApprove').open")
        self.assertTrue(self.ev("document.getElementById('mnApAll').checked"), "the group's one tick, ticked")
        self.assertEqual(self.ev("[...document.querySelectorAll('#mnApprove [data-own]')].map(x=>[+x.dataset.own,x.checked])"),
                         [[4, False], [5, False]], "a new decision and a new risk: one tick each, not ticked")
        self.assertIn("check", self.ev("document.querySelector('#mnApprove .mnap-ck').textContent"))

    # ── v2.1.0 P7 follow-up (Alan, 15-10-2026): Draft the follow-up email, in the Export menu ──
    def seed_secrets(self):
        """A Sensitive decision (flag) and an Internal only action row, on the stored record; reloads the view."""
        doc = self.record()
        dec = next(s for s in doc["sections"] if s["id"] == "decisions")["rows"][0]
        act = next(s for s in doc["sections"] if s["id"] == "actions")["rows"][0]
        doc["items"][dec["ref"]]["flags"] = ["sensitive"]
        doc["layout"] = {**(doc.get("layout") or {}), "distributed": True, "internal_only": [{"section": "actions", "ref": act["ref"]}]}
        r = subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts'); import minutes_record; "
                            f"r = minutes_record.save_record({DRAFT!r}, json.loads({json.dumps(json.dumps(doc))}), 'seed'); print(json.dumps({{'ok': r.get('ok')}}))"],
                           cwd=self.v.root, capture_output=True, text=True, check=True)
        self.assertTrue(json.loads(r.stdout.strip().splitlines()[-1])["ok"])
        self.b.eval("go('review')")
        self.b.eval(f"go('minutes',{{file:{json.dumps(self.proposal)}}})")
        self.b.wait("document.querySelector('#v-minutes .mnrow')", 15)
        return dec["cells"]["decision"], act["cells"]["action"]

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

    def test_8_follow_up_email_distributed_version_holds_nothing_internal(self):
        b = self.b
        decision, action = self.seed_secrets()
        b.click("#v-minutes .seg button:nth-child(2)")
        b.wait("document.querySelector('[data-mnmode=side]')")
        names = self.menu_names()
        self.assertEqual([n for n in names if "follow-up" in n].__len__(), 1, names)          # Internal shown: one entry
        self.assertTrue(any(n.startswith("Internal:") and "follow-up" in n for n in names), names)
        b.key("Escape")
        b.click("[data-mnmode=side]")
        b.wait("document.querySelector('.sheet-pair')")
        names = self.menu_names()
        self.assertEqual(sum("follow-up" in n for n in names), 2, "side by side: both versions offered")
        b.key("Escape")
        b.click("[data-mnmode=distributed]")
        b.wait("!document.querySelector('.sheet-pair')")
        names = self.menu_names()
        self.assertEqual([n for n in names if "follow-up" in n], [n for n in names if n.startswith("Distributed:") and "follow-up" in n])
        self.pick("Distributed: Draft the follow-up email")
        whole = self.ev("document.getElementById('deDlg').textContent + ' ' + document.querySelector('#deSubj').value")
        self.assertNotIn(decision, whole, "a Sensitive decision never reaches the distributed draft")
        self.assertNotIn(action, whole, "an Internal only row never reaches it")
        self.assertNotIn("[Internal]", whole)
        self.assertNotIn("Internal: not for distribution", whole)
        self.assertIn("Distributed", self.ev("document.querySelector('#deTitle').textContent"))
        self.shots("distributed")
        b.key("Escape")
        b.click("[data-mnmode=internal]")
        self.menu_names()
        self.pick("Internal: Draft the follow-up email")
        both = self.ev("document.getElementById('deDlg').textContent")
        self.assertIn(action, both, "the Internal draft keeps it")
        self.assertIn("Internal: not for distribution.", self.ev("document.querySelector('#dePrev').textContent"))


if __name__ == "__main__":
    unittest.main()
