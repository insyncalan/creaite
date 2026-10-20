"""#268 Minutes view v2, in a real browser on the real live server (LiveBrowserCase; no Claude runs).

The fictional steering committee of test_minutes_editor is staged as a minutes record (three actions, one owner who needs
details, a decision and a risk). Alan signed off the mockup on 20-10-2026 (dev/mockups/minutes-view-v2-mockup.html):

- Track column, three states per item: tick = register a work item, cross = remove the line from the minutes, neither = it
  stays in the minutes untracked. Actions and issues start ticked, decisions and risks neither; clicking the pressed button
  clears it; the bar sums it up ("n work items to register · n kept in the minutes only · n removed"); the choice survives
  a reload.
- Aligned tables: one heading per column (Track, the item, Owner, and for risks, issues and actions Due, Priority,
  Workstream).
- Inline editing, no popup: the item's words and the summary are edited where they stand (Enter or a click away saves, Esc
  puts them back); Owner, Priority and Workstream are in-row dropdowns; Due opens the deadline popover.
- Hovering a row lights its transcript turn and hovering a turn lights its rows.
- The transcript hides from the Transcript button or its close button, the page rescales, and the choice is remembered:
  after a reload and for a different meeting.
- The header slims on scroll and the slim bar shows the title; Ctrl and the wheel zoom from 50% to 250%.
- One version only: no One version / Internal + distributed switch; the bar's tools are icon buttons; Export has Word, PDF,
  HTML and Draft the follow-up email.
- Approve minutes is one click: Before approving only when a ticked item has a real problem ("needs details", a possible
  duplicate); the snack says "Minutes approved · n work items registered" with Undo; nothing ticked approves the minutes
  with no items (#261).

Run: python3 dev/tests/test_minutes_view_v2.py      (Chrome tier; skipped without Chrome)
"""
import json
import sqlite3
import subprocess
import sys
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402
import test_minutes_editor as me  # noqa: E402
from test_tracker import ABC  # noqa: E402

ROW = "#v-minutes tr.mi[data-n='%d']"
SECOND = "Budget review"


def stage_second(v):
    """A second meeting (another title, the same day and transcript), staged as minutes: its proposal's file name."""
    before = {p.name for p in (v.root / "system/staging").glob("proposed-*.json")}
    spec = me.meeting_spec()
    spec["title"] = f"[ABC] {SECOND}"
    spec["transcript"] = f"inbox/{me.DAY} {SECOND}.vtt"
    spec.pop("coverage", None)
    (v.root / "inbox" / f"{me.DAY} {SECOND}.vtt").write_text(me.VTT, encoding="utf-8")
    spec["items"] = spec["items"][:1]
    f = v.root / "system/staging/drafts/meeting2.json"
    f.write_text(json.dumps(spec), encoding="utf-8")
    v.run("stage", str(f), script="minutes.py")
    return next(p.name for p in (v.root / "system/staging").glob("proposed-*.json") if p.name not in before)


class MinutesViewV2(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        populate(v)
        v.propose("ws", [{"n": 1, "op": "new", "table": "workstreams", "decision": "approved",       # one workstream for the dropdown (BL-58)
                          "values": {"project": "ABC", "name": "Testing", "lead": "Sara Example", "status": "Active", "source": "t"}}])
        v.run("apply")
        v.run(script="build_dashboard.py")
        cls.proposal = me.stage_meeting(v)

    def setUp(self):
        super().setUp()
        self.open()

    # ── helpers ──
    def open(self, proposal=None):
        self.b.eval(f"go('minutes',{{file:{json.dumps(proposal or self.proposal)}}})")
        self.b.wait("document.querySelector('#v-minutes tr.mi')", 15)
        self.b.pump(0.3)

    def ev(self, js):
        return self.b.eval(js)

    def staged(self, n, name=None):
        p = self.v.root / "system/staging" / (name or self.proposal)
        p = p if p.exists() else self.v.root / "system/staging/applied" / (name or self.proposal)
        return next(i for i in json.loads(p.read_text(encoding="utf-8"))["items"] if i["n"] == n)

    def record(self, path=me.DRAFT):
        r = subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts'); import creaite_doc; "
                            f"print(json.dumps(creaite_doc.read({path!r})))"], cwd=self.v.root, capture_output=True, text=True, check=True)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def trk(self):
        return self.ev("Object.fromEntries([...document.querySelectorAll('#v-minutes tr.mi')].map(r=>[r.dataset.n, r.dataset.trk]))")

    def summary(self):
        return self.ev("(document.getElementById('mnSum')||{}).textContent||''")

    def centre(self, sel, into_view=False):
        if into_view:
            self.ev(f"document.querySelector({json.dumps(sel)}).scrollIntoView({{block:'center'}})")
            self.b.pump(0.4)
        return self.ev(f"(()=>{{const r=document.querySelector({json.dumps(sel)}).getBoundingClientRect(); return [r.left+Math.min(r.width/2,40), r.top+r.height/2]}})()")

    def move(self, x, y):
        self.b.call("Input.dispatchMouseEvent", type="mouseMoved", x=x, y=y)
        self.b.pump(0.15)

    def wheel(self, sel, dy, ctrl=False, times=1):
        x, y = self.centre(sel)
        for _ in range(times):
            self.b.call("Input.dispatchMouseEvent", type="mouseWheel", x=x, y=y, deltaX=0, deltaY=dy, modifiers=2 if ctrl else 0)
            self.b.pump(0.05)
        self.b.pump(0.3)

    def caret_end(self, sel):
        self.ev(f"(()=>{{const e=document.querySelector({json.dumps(sel)}), s=getSelection(); s.selectAllChildren(e); s.collapseToEnd();}})()")
        self.b.pump(0.15)

    def snack(self):
        return self.ev("document.getElementById('snack').classList.contains('on') ? document.getElementById('snack').textContent : ''")

    def filed(self):
        return next((self.v.root / ABC / "minutes").glob("*Steering committee.html"), None)

    def rows_of(self, table):
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            con.row_factory = sqlite3.Row
            return [dict(r) for r in con.execute(f"SELECT * FROM {table}")]

    # ── tests ──
    def test_01_three_states_their_defaults_clearing_and_the_summary(self):
        self.assertEqual(self.trk(), {"1": "y", "2": "y", "3": "y", "4": "", "5": ""}, "actions ticked; the decision and the risk neither")
        self.assertEqual(self.summary(), "3 work items to register · 2 kept in the minutes only")
        self.b.click(ROW % 1 + " .mntrk button.n")
        self.b.pump(0.2)
        self.assertEqual(self.trk()["1"], "n")
        self.assertEqual(self.summary(), "2 work items to register · 2 kept in the minutes only · 1 removed")
        self.assertEqual(self.ev(f"document.querySelector(\"{ROW % 1} .mntrk button.n\").getAttribute('aria-pressed')"), "true")
        self.b.click(ROW % 1 + " .mntrk button.n")               # the pressed one again: cleared
        self.b.pump(0.2)
        self.assertEqual(self.trk()["1"], "")
        self.assertEqual(self.summary(), "2 work items to register · 3 kept in the minutes only")
        self.b.click(ROW % 4 + " .mntrk button.y")               # a decision ticked
        self.b.pump(0.2)
        self.assertEqual(self.trk()["4"], "y")
        self.assertEqual(self.summary(), "3 work items to register · 2 kept in the minutes only")
        self.assertIn("neither keeps it in the minutes only", self.ev("document.querySelector('#v-minutes table.mnt th').dataset.tip"), "the Track heading explains it")
        self.assertFalse(self.ev("!!document.querySelector('#v-minutes .mnleg')"), "no legend")
        self.b.wait("(document.querySelector('#v-minutes .sheet-status')||{}).textContent.startsWith('Saved')", 15)
        self.assertEqual(self.record()["layout"]["track"], {"1": "", "4": "y"}, "kept with the page")
        self.assertEqual(self.staged(1)["decision"], "pending", "nothing changes the item before Approve minutes")
        self.b.reload("typeof go==='function' && LIVE && document.querySelector('#v-minutes tr.mi')")
        self.b.pump(0.3)
        self.assertEqual(self.trk(), {"1": "", "2": "y", "3": "y", "4": "y", "5": ""}, "the choices survive a reload")

    def test_02_aligned_tables_one_heading_per_column(self):
        heads = self.ev("""[...document.querySelectorAll('#v-minutes table.mnt')].map(t=>{ const sec=t.closest('section[data-id]').dataset.id,
          th=[...t.querySelectorAll('thead th')].map(x=>x.textContent.trim()), cells=t.querySelector('tbody tr').children.length,
          off=[...t.querySelectorAll('thead th')].map((h,i)=>Math.abs(h.getBoundingClientRect().left-t.querySelector('tbody tr').children[i].getBoundingClientRect().left));
          return [sec, th, cells, Math.max(...off)]; })""")
        by = {h[0]: h for h in heads}
        self.assertEqual(by["decisions"][1], ["Track", "Decision", "Owner"])
        self.assertEqual(by["actions"][1], ["Track", "Action", "Owner", "Due", "Priority", "Workstream"])
        self.assertEqual(by["raid"][1], ["Track", "Risk", "Owner", "Due", "Priority", "Workstream"])
        for sec, th, cells, off in heads:
            self.assertEqual(len(th), cells, f"{sec}: one heading per column")
            self.assertLess(off, 1.5, f"{sec}: each heading over its cells")
        self.assertFalse(self.ev("!!document.querySelector('#v-minutes .msrc, #v-minutes [data-mnremove], #v-minutes .mnopen')"), "no source arrow, no Remove menu, no Open")

    def test_03_inline_edit_saves_on_enter_and_esc_puts_it_back(self):
        b = self.b
        ed = ROW % 1 + " .mnit .sheet-ed"
        b.click(ed)
        self.caret_end(ed)
        b.type(" today")
        b.key("Enter")
        b.wait("document.querySelector(\"%s\").textContent.includes('today') && !document.activeElement.closest('.mnit')" % (ROW % 1), 10)
        b.wait("1", 1)
        self.b.pump(1.0)
        self.assertEqual(self.staged(1)["values"]["description"], "Send the revised SOW to the client today", "Enter saved it to the staged item")
        b.click(ed)
        self.caret_end(ed)
        b.type(" and tomorrow")
        b.key("Escape")
        b.pump(0.5)
        self.assertEqual(self.ev(f"document.querySelector({json.dumps(ed)}).textContent"), "Send the revised SOW to the client today", "Esc put the words back")
        self.assertEqual(self.staged(1)["values"]["description"], "Send the revised SOW to the client today")
        self.assertFalse(self.ev("!!document.querySelector('#v-minutes .edcard, #v-minutes .mnpop')"), "no popup")
        b.click(ed)                                            # AI on selected text, as in every editor
        b.eval("""(()=>{ const h=document.querySelector(%s).cxed, doc=h.editor.state.doc; let at=-1;
          doc.descendants((n,pos)=>{ if(at<0&&n.isText){ const i=n.text.indexOf('revised'); if(i>=0) at=pos+i; } });
          h.focus(); h.editor.commands.setTextSelection({from:at,to:at+7}); })()""" % json.dumps(ed))
        b.wait("document.querySelector('#aiLayer .aispark')", 5)
        b.key("Escape")
        b.pump(0.3)
        # the summary, where it stands
        summ = "#v-minutes section[data-id=summary] .sheet-ed"
        was = self.ev(f"document.querySelector({json.dumps(summ)}).textContent")
        b.click(summ)
        self.caret_end(summ)
        b.type(" Extra words.")
        b.pump(0.2)
        self.assertIn("Extra words.", self.ev(f"document.querySelector({json.dumps(summ)}).textContent"))
        b.key("Escape")
        b.pump(0.4)
        self.assertEqual(self.ev(f"document.querySelector({json.dumps(summ)}).textContent"), was, "Esc undoes the summary edit")
        b.click(summ)
        self.caret_end(summ)
        b.type(" Kept.")
        b.click("#v-minutes .sheet-zv")                       # a click away keeps it
        b.wait("(document.querySelector('#v-minutes .sheet-status')||{}).textContent.startsWith('Saved')", 15)
        self.assertIn("Kept.", next(s for s in self.record()["sections"] if s["id"] == "summary")["text"])

    def test_04_owner_priority_and_workstream_dropdowns_in_the_row(self):
        b = self.b
        sel = ROW % 1 + " td.mnpc select"
        b.eval(f"(()=>{{const s=document.querySelector({json.dumps(sel)}); s.value='High'; s.dispatchEvent(new Event('change',{{bubbles:true}}));}})()")
        b.wait(f"document.querySelector({json.dumps(sel)}) && document.querySelector({json.dumps(sel)}).value==='High' && document.querySelector({json.dumps(sel)}).classList.contains('pr-H')", 10)
        b.pump(0.5)
        self.assertEqual(self.staged(1)["values"].get("priority"), "High")
        own = ROW % 1 + " td.mnoc select"
        names = self.ev(f"[...document.querySelector({json.dumps(own)}).options].map(o=>o.value)")
        self.assertIn("Sara Example", names)
        b.eval(f"(()=>{{const s=document.querySelector({json.dumps(own)}); s.value='Sara Example'; s.dispatchEvent(new Event('change',{{bubbles:true}}));}})()")
        b.wait(f"document.querySelector({json.dumps(own)}).value==='Sara Example'", 10)
        b.pump(0.5)
        self.assertEqual(self.staged(1)["values"]["owner"], "Sara Example")
        ws = ROW % 1 + " td.mnwc select"
        opts = self.ev(f"[...document.querySelector({json.dumps(ws)}).options].map(o=>o.value).filter(Boolean)")
        self.assertTrue(opts, "the project's workstreams are offered")
        b.eval(f"(()=>{{const s=document.querySelector({json.dumps(ws)}); s.value={json.dumps(opts[0])}; s.dispatchEvent(new Event('change',{{bubbles:true}}));}})()")
        b.wait(f"document.querySelector({json.dumps(ws)}).value==={json.dumps(opts[0])}", 10)
        b.pump(0.5)
        self.assertEqual(self.staged(1)["values"].get("workstream"), opts[0])
        rws = ROW % 5 + " td.mnwc select"                     # a risk's workstream: the record refuses it until the proposal lands; said, and kept as it was
        b.eval(f"(()=>{{const s=document.querySelector({json.dumps(rws)}); s.value={json.dumps(opts[0])}; s.dispatchEvent(new Event('change',{{bubbles:true}}));}})()")
        b.wait("document.getElementById('snack').classList.contains('on')", 10)
        b.pump(0.4)
        if self.staged(5)["values"].get("workstream") != opts[0]:
            self.assertIn("can't be changed from the minutes", self.snack())
            self.assertEqual(self.ev(f"document.querySelector({json.dumps(rws)}).value"), "", "the row keeps its value")
        self.assertIn("needs details", self.ev(f"document.querySelector(\"{ROW % 3}\").textContent"), "#266's wording")
        self.assertNotIn("people register", self.ev("document.querySelector('#v-minutes .page').textContent"))

    def test_05_due_opens_the_deadline_popover_with_words_quick_picks_and_a_calendar(self):
        b = self.b
        sel = ROW % 3 + " .mndue"
        self.assertEqual(self.ev(f"document.querySelector({json.dumps(sel)}).textContent"), "Not set")
        b.click(sel)
        b.wait("document.querySelector('.mndl')")
        self.assertEqual(len(self.ev("[...document.querySelectorAll('.mndl [data-quick]')].map(x=>x.dataset.quick)")), 5, "four quick picks and Not set")
        self.assertGreater(self.ev("document.querySelectorAll('.mndl .pkday').length"), 27, "a month calendar")
        b.eval("document.getElementById('mnDlWords').focus()")
        b.type("in 2 weeks")
        b.pump(0.2)
        got = self.ev(f"CREAITE.parseWhen('in 2 weeks', {json.dumps(me.DAY)}, true, 'deadline')")
        self.assertIn(self.ev(f"fd({json.dumps(got)})"), self.ev("document.getElementById('mnDlSaid').textContent"))
        b.key("Enter")
        b.wait(f"document.querySelector({json.dumps(sel)}).textContent!=='Not set'", 10)
        b.pump(0.4)
        self.assertEqual(self.staged(3)["values"]["due_date"], got)
        b.click(sel)
        b.wait("document.querySelector('.mndl')")
        b.eval("document.querySelector('.mndl .pkday:not(.on)').click()")
        b.wait(f"document.querySelector({json.dumps(sel)}).textContent!=={json.dumps(self.ev(f'fd({json.dumps(got)})'))}", 10)
        b.pump(0.4)
        self.assertNotEqual(self.staged(3)["values"]["due_date"], got, "a day from the calendar")

    def test_06_hover_lights_both_ways(self):
        turn = self.ev(f"document.querySelector(\"{ROW % 2}\").dataset.turn")
        self.assertTrue(turn, "the row knows its turn")
        self.move(*self.centre(ROW % 2, True))
        self.assertEqual(self.ev("[...document.querySelectorAll('.mnturns li.hl')].map(l=>l.dataset.turn)"), [turn], "the row lights its turn")
        self.move(5, 5)
        self.assertEqual(self.ev("document.querySelectorAll('.mnturns li.hl').length"), 0)
        self.move(*self.centre(f".mnturns li[data-turn='{turn}']", True))
        self.assertIn("2", self.ev("[...document.querySelectorAll('#v-minutes tr.mi.hl')].map(r=>r.dataset.n)"), "the turn lights its rows")
        self.move(5, 5)
        self.assertEqual(self.ev("document.querySelectorAll('#v-minutes tr.mi.hl').length"), 0)

    def test_07_the_transcript_choice_rescales_survives_a_reload_and_applies_to_another_meeting(self):
        b = self.b
        second = stage_second(self.v)
        width = lambda: self.ev("document.querySelector('#v-minutes .sheet-fit').getBoundingClientRect().width")   # noqa: E731
        self.assertEqual(self.ev("document.getElementById('mnTrBtn').getAttribute('aria-pressed')"), "true", "shown by default")
        w0 = width()
        b.click("#mnTrBtn")
        b.wait("!document.querySelector('.mnpane')")
        b.pump(0.4)
        self.assertEqual(self.ev("document.getElementById('mnTrBtn').getAttribute('aria-pressed')"), "false")
        self.assertGreater(width(), w0 + 100, "the page rescales into the room")
        b.reload("typeof go==='function' && LIVE && document.querySelector('#v-minutes tr.mi')")
        b.pump(0.3)
        self.assertFalse(self.ev("!!document.querySelector('.mnpane')"), "hidden after a reload")
        self.b.eval("go('review')")
        self.open(second)
        self.assertFalse(self.ev("!!document.querySelector('.mnpane')"), "and for another meeting")
        b.click("#mnTrBtn")
        b.wait("document.querySelector('.mnpane')")
        b.click(".mnpane [data-mnpane=close]")                 # the close button hides it too
        b.wait("!document.querySelector('.mnpane')")
        b.click("#mnTrBtn")
        b.wait("document.querySelector('.mnpane')")
        self.b.eval("go('review')")
        self.open()
        self.assertTrue(self.ev("!!document.querySelector('.mnpane')"), "shown again, remembered")
        self.assertEqual(self.ev("localStorage.getItem('creaite-minutes-transcript')"), "true")

    def test_08_the_header_slims_on_scroll_and_shows_the_title(self):
        self.assertFalse(self.ev("document.querySelector('#v-minutes .sheet-root').classList.contains('rpt-slim')"))
        self.wheel("#v-minutes .sheet-scroll", 300)
        self.b.wait("document.querySelector('#v-minutes .sheet-root').classList.contains('rpt-slim')", 5)
        self.assertEqual(self.ev("getComputedStyle(document.querySelector('#v-minutes .mnhead')).height"), "0px", "the page header is hidden")
        mini = self.ev("(()=>{const m=document.querySelector('#v-minutes .sheet-mini'); return getComputedStyle(m).display!=='none' && m.getBoundingClientRect().width>20 ? m.textContent : ''})()")
        self.assertIn("Steering committee", mini, "the slim bar shows the title")
        self.assertEqual(self.ev("Math.round(document.querySelector('#v-minutes .sheet-bar').getBoundingClientRect().height)") < 60, True, "one row")

    def test_09_ctrl_wheel_zooms_from_50_to_250_and_the_buttons_stay(self):
        z = lambda: self.ev("+document.querySelector('#v-minutes .sheet-zv').dataset.zoom")   # noqa: E731
        self.assertEqual(z(), 0.8)
        self.wheel("#v-minutes .sheet-scroll", -60, ctrl=True, times=40)
        self.assertEqual(z(), 2.5, "pinch in to 250%")
        self.assertEqual(self.ev("document.querySelector('#v-minutes .sheet-zv').textContent"), "250%")
        self.wheel("#v-minutes .sheet-scroll", 60, ctrl=True, times=60)
        self.assertEqual(z(), 0.5, "pinch out to 50%")
        self.b.click("#v-minutes .sheet-zoom button[aria-label='Zoom in']")
        self.b.pump(0.2)
        self.assertEqual(z(), 0.6)
        self.b.click("#v-minutes .sheet-zv")
        self.b.pump(0.2)
        self.assertEqual(z(), 0.8, "back to 80%")

    def test_10_one_version_icon_tools_and_the_export_menu(self):
        bar = "#v-minutes .sheet-bar"
        txt = self.ev(f"document.querySelector({json.dumps(bar)}).textContent")
        for gone in ("One version", "Internal + distributed", "Side by side", "Distributed"):
            self.assertNotIn(gone, txt)
        self.assertFalse(self.ev("!!document.querySelector('#v-minutes [data-mnmode], #v-minutes .mnio')"), "no switch, no Internal only marks")
        icons = self.ev(f"[...document.querySelectorAll('{bar} .ib')].map(b=>b.getAttribute('aria-label'))")
        self.assertEqual(icons, ["Show as exported", "Transcript", "Export", "Re-extract: draft the minutes again from the transcript"])
        labelled = self.ev(f"[...document.querySelectorAll('{bar} button')].filter(b=>!b.classList.contains('ib') && b.textContent.trim().length>4).map(b=>b.textContent.trim())")
        self.assertEqual(labelled, ["Approve minutes"], "only Approve minutes keeps a label")
        self.b.click("#v-minutes [data-mnexport]")
        self.b.wait("document.querySelector('.ddmenu.on')")
        items = self.ev("[...document.querySelectorAll('.ddmenu.on [role=menuitem]')].map(x=>[x.querySelector('b,strong,.mname')?x.querySelector('b,strong,.mname').textContent:x.textContent, x.textContent])")
        names = [i[0] for i in items]
        self.assertEqual(names, ["Word", "PDF", "HTML", "Draft the follow-up email"])
        for name, whole in items[:3]:
            self.assertGreater(len(whole), len(name) + 10, f"{name} has its description line")
        self.assertIn("never come back", items[0][1], "Word is an export only")
        self.b.key("Escape")

    def test_11_approve_with_a_problem_asks_first_then_registers_the_ticked_items(self):
        b = self.b
        b.click("#mnApproveBtn")
        b.wait("document.getElementById('mnApprove').open")
        lis = self.ev("[...document.querySelectorAll('#mnApprove li')].map(l=>l.textContent)")
        self.assertEqual(sorted(lis), ["Pat Unknown needs detailsShare the cut-over plan with the client",
                                       "Possible duplicate of ABC-A-002Book the UAT test environment"], "just the ticked items with a real problem")
        b.click("#mnApproveBack")
        b.pump(0.3)
        self.assertFalse(self.ev("document.getElementById('mnApprove').open"), "Go back")
        self.assertEqual(self.staged(1)["decision"], "pending", "nothing approved")
        b.click("#mnApproveBtn")
        b.wait("document.getElementById('mnApprove').open")
        b.click("#mnApproveGo")
        b.wait("document.getElementById('snack').classList.contains('on') && /Minutes approved/.test(document.getElementById('snack').textContent)", 30)
        self.assertIn("Minutes approved · 3 work items registered", self.snack())
        self.assertTrue(self.ev("getComputedStyle(document.getElementById('snackU')).display!=='none'"), "with Undo")
        descs = [a["description"] for a in self.rows_of("actions")]
        for d in ("Send the revised SOW to the client", "Book the UAT test environment", "Share the cut-over plan with the client"):
            self.assertIn(d, descs)
        self.assertNotIn("The pilot stays on the lighthouse site", [x["decision"] for x in self.rows_of("decisions")], "the decision stays in the minutes only")
        self.assertNotIn("Data access late → the MVP slips", [x["description"] for x in self.rows_of("raid")])
        filed = self.filed()
        self.assertIsNotNone(filed)
        self.assertIn("lighthouse site", filed.read_text(encoding="utf-8"), "kept in the minutes")
        b.wait("document.querySelector('#v-minutes .mnmeta') && /Approved and filed/.test(document.querySelector('#v-minutes .mnmeta').textContent)", 15)
        b.click("#snackU")                                      # Undo: the whole apply back, and the draft on the page again
        b.wait("document.querySelector('#v-minutes tr.mi') && /Draft/.test(document.querySelector('#v-minutes .mnmeta').textContent)", 30)
        self.assertNotIn("Share the cut-over plan with the client", [a["description"] for a in self.rows_of("actions")])
        # #268's bug: after Undo the minutes are exactly as they were before Approve (the untracked decision and risk keep their
        # controls), and approving again gives the same result: nothing goes to Review
        b.wait(f"document.querySelector(\"{ROW % 4} td.mnoc select\") && document.querySelector(\"{ROW % 5} td.mnoc select\")", 30)
        self.assertEqual(self.trk(), {"1": "y", "2": "y", "3": "y", "4": "", "5": ""}, "the Track column as it was")
        self.assertEqual(self.summary(), "3 work items to register · 2 kept in the minutes only")
        self.assertEqual(self.ev("document.querySelectorAll('#v-minutes tr.mi td.mnoc select').length"), 5, "every row has its Owner dropdown again")
        self.assertEqual(self.staged(4)["decision"], "pending")
        self.assertNotIn("reject_reason", self.staged(5))
        b.wait("!document.getElementById('snack').classList.contains('on') || !/Minutes approved/.test(document.getElementById('snack').textContent)", 15)
        b.click("#mnApproveBtn")
        b.wait("document.getElementById('mnApprove').open")
        b.click("#mnApproveGo")
        b.wait("document.getElementById('snack').classList.contains('on') && /Minutes approved/.test(document.getElementById('snack').textContent)", 30)
        self.assertIn("Minutes approved · 3 work items registered", self.snack())
        self.assertNotIn("wait in Review", self.snack(), "the same result as the first time")
        self.assertNotIn("The pilot stays on the lighthouse site", [x["decision"] for x in self.rows_of("decisions")])

    def test_12_approve_with_no_problem_is_one_click_and_a_cross_removes_the_line(self):
        b = self.b
        b.click(ROW % 3 + " .mntrk button.y")                   # Pat Unknown's action: neither, so no problem is left
        b.click(ROW % 2 + " .mntrk button.n")                   # crossed: out of the minutes
        b.pump(0.3)
        self.assertEqual(self.summary(), "1 work item to register · 3 kept in the minutes only · 1 removed")
        b.click("#mnApproveBtn")
        b.wait("document.getElementById('snack').classList.contains('on') && /Minutes approved/.test(document.getElementById('snack').textContent)", 30)
        self.assertFalse(self.ev("document.getElementById('mnApprove').open"), "no box")
        self.assertIn("Minutes approved · 1 work item registered", self.snack())
        self.assertEqual(self.staged(2)["decision"], "rejected")
        self.assertEqual(self.staged(3)["reject_reason"], "Removed in the minutes")
        filed = self.filed().read_text(encoding="utf-8")
        self.assertNotIn("Book the UAT test environment", filed, "the crossed line left the minutes")
        self.assertIn("Share the cut-over plan with the client", filed, "neither: the line stays")
        self.assertIn("lighthouse site", filed)

    def test_13_approve_with_nothing_ticked_files_the_minutes_with_no_items(self):
        b = self.b
        for n in (1, 2, 3):
            b.click(ROW % n + " .mntrk button.y")
            b.pump(0.1)
        self.assertEqual(self.summary(), "0 work items to register · 5 kept in the minutes only")
        b.click("#mnApproveBtn")
        b.wait("document.getElementById('snack').classList.contains('on') && /Minutes approved/.test(document.getElementById('snack').textContent)", 30)
        self.assertIn("Minutes approved · no work items registered", self.snack())
        self.assertEqual([a for a in self.rows_of("actions") if a["description"] == "Send the revised SOW to the client"], [])
        self.assertIsNotNone(self.filed(), "the minutes are filed")
        b.wait("document.querySelector('#v-minutes .mnmeta') && /Approved and filed/.test(document.querySelector('#v-minutes .mnmeta').textContent)", 15)

    def test_14_at_1400_and_900_the_bar_is_one_row_and_the_headings_sit_over_their_cells(self):
        for w in (1400, 900):
            with self.subTest(width=w):
                self.b.resize(w, 1000)
                self.b.pump(0.6)
                bar = self.ev("""(()=>{ const b=document.querySelector('#v-minutes .sheet-bar'), kids=[...b.querySelectorAll('button, .mnsum, .sheet-status')].filter(x=>x.offsetParent);
                  const tops=new Set(kids.map(k=>Math.round(k.getBoundingClientRect().top+k.getBoundingClientRect().height/2)));
                  return {h: b.getBoundingClientRect().height, rows: Math.max(...tops)-Math.min(...tops), right: Math.max(...kids.map(k=>k.getBoundingClientRect().right)), w: b.getBoundingClientRect().right}; })()""")
                self.assertLess(bar["rows"], 12, f"one row at {w}: {bar}")
                self.assertLessEqual(bar["right"], bar["w"] + 0.5, f"nothing cut off at {w}")
                off = self.ev("""Math.max(...[...document.querySelectorAll('#v-minutes table.mnt')].map(t=>{ const r=t.querySelector('tbody tr');
                  return Math.max(...[...t.querySelectorAll('thead th')].map((h,i)=>Math.abs(h.getBoundingClientRect().left-r.children[i].getBoundingClientRect().left))); }))""")
                self.assertLess(off, 1.5)
                self.assertLessEqual(self.ev("document.scrollingElement.scrollWidth - innerWidth"), 0, "no sideways scroll")


if __name__ == "__main__":
    unittest.main()
