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
A4_PX = 210 * 96 / 25.4                                     # an A4 page at its real size (100%), in CSS pixels


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

    def file_box(self):
        """#324: Approve minutes asks where the minutes are filed when the server offers it (the guarded diff): press File and approve.
        Returns at once when the minutes are approved without the question."""
        self.b.wait("(document.getElementById('mnFiling')||{}).open || /Minutes approved/.test(document.getElementById('snack').textContent)", 30)
        if self.ev("!!(document.getElementById('mnFiling')||{}).open"):
            self.b.click("#mnFilingGo")

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
        self.assertEqual(by["decisions"][1], ["Track", "Decision", "Made by"])   # #302 A: Decisions say who made them
        self.assertEqual(by["actions"][1], ["Track", "Action", "Owner", "Due", "Priority", "Workstream"])
        self.assertEqual(by["raid"][1], ["Track", "Risk", "Owner", "Due", "Priority", "Workstream"])
        for sec, th, cells, off in heads:
            self.assertEqual(len(th), cells, f"{sec}: one heading per column")
            self.assertLess(off, 1.5, f"{sec}: each heading over its cells")
        self.assertFalse(self.ev("!!document.querySelector('#v-minutes .msrc, #v-minutes [data-mnremove], #v-minutes .mnopen')"), "no source arrow, no Remove menu, no Open")
        # the signed-off look (PM, 20-10-2026): fully boxed tables with a grey header row, values as filled pills, dashed only when empty
        look = self.ev("""(()=>{ const t=document.querySelector('#v-minutes table.mnt'), th=t.querySelector('th'), td=t.querySelector('tbody td'),
          cs=getComputedStyle(th), ds=getComputedStyle(td), own=getComputedStyle(document.querySelector("%s td.mnoc select")),
          none=document.querySelector("%s td.mnwc select");
          return {thL: cs.borderLeftWidth, thBg: cs.backgroundColor, tdL: ds.borderLeftWidth, tdR: ds.borderRightWidth,
            app: own.appearance, ownBorder: own.borderTopStyle, ownBg: own.backgroundColor, emptyBorder: getComputedStyle(none).borderTopStyle}; })()""" % (ROW % 1, ROW % 1))
        self.assertEqual((look["thL"], look["tdL"], look["tdR"]), ("1px", "1px", "1px"), f"boxed: {look}")
        self.assertNotIn(look["thBg"], ("rgba(0, 0, 0, 0)", "transparent"), "a grey header row")
        self.assertEqual(self.ev("getComputedStyle(document.querySelector('#v-minutes table.mnt th')).position"), "static",
                         "the grey header never sticks over the rows as the sheet scrolls")
        self.assertEqual(look["app"], "none", "a pill, not a native select with a chevron")
        self.assertNotEqual(look["ownBorder"], "dashed", "a value is a filled pill")
        self.assertEqual(look["emptyBorder"], "dashed", "an empty value is dashed")
        # a risk's Priority: shown read only, with the tip, never a control or a dash
        pr = self.ev(f"(()=>{{const c=document.querySelector(\"{ROW % 5} td.mnpc\"); return [c.querySelectorAll('select,button').length, c.textContent.trim(), (c.querySelector('.mnro')||{{dataset:{{}}}}).dataset.tip||'']}})()")
        self.assertEqual(pr[0], 0, "no control")
        self.assertNotEqual(pr[1], "—")
        self.assertEqual(pr[2], "Worked out from impact and likelihood")
        heads = self.ev("Object.fromEntries([...document.querySelectorAll('#v-minutes .page section[data-id] > h2')].map(h=>[h.parentElement.dataset.id, [(h.querySelector('input')||{}).value||'', (h.querySelector('.sheet-hn')||{}).textContent||'']]))")
        self.assertEqual(heads["decisions"], ["Decisions", "1"], "the heading with its count")
        self.assertEqual(heads["actions"], ["Actions", "3"], "Actions with its count, not Action Items")

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
        self.assertEqual(self.ev(f"document.querySelector({json.dumps(sel)}).textContent"), "No date", "the mockup's words for an empty due date")
        self.assertTrue(self.ev(f"document.querySelector({json.dumps(sel)}).classList.contains('empty')"), "dashed while empty")
        b.click(sel)
        b.wait("document.querySelector('.mndl')")
        self.assertEqual(len(self.ev("[...document.querySelectorAll('.mndl [data-quick]')].map(x=>x.dataset.quick)")), 5, "four quick picks and Not set")
        self.assertIn("Type a due date", self.ev("document.querySelector('.mndl-l').textContent"))
        self.assertGreater(self.ev("document.querySelectorAll('.mndl .pkday').length"), 27, "a month calendar")
        b.eval("document.getElementById('mnDlWords').focus()")
        b.type("in 2 weeks")
        b.pump(0.2)
        got = self.ev(f"CREAITE.parseWhen('in 2 weeks', {json.dumps(me.DAY)}, true, 'deadline')")
        self.assertIn(self.ev(f"fd({json.dumps(got)})"), self.ev("document.getElementById('mnDlSaid').textContent"))
        b.key("Enter")
        b.wait(f"document.querySelector({json.dumps(sel)}).textContent!=='No date'", 10)
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
        b.resize(900, 1000)                                     # #268: at 1400 both fit past 100%, so both are capped; at 900 the
        b.wait("innerWidth===900")                              # transcript leaves less room than the real size
        b.pump(0.6)
        try:
            self._transcript_choice(b, second)
        finally:
            b.resize(1400, 1000)

    def _transcript_choice(self, b, second):
        width = lambda: self.ev("document.querySelector('#v-minutes .sheet-fit').getBoundingClientRect().width")   # noqa: E731
        self.assertEqual(self.ev("document.getElementById('mnTrBtn').getAttribute('aria-pressed')"), "true", "shown by default")
        w0 = width()
        label = lambda: self.ev("document.querySelector('#v-minutes .sheet-zv').textContent")   # noqa: E731
        real = lambda: self.ev("Math.round(+document.querySelector('#v-minutes .sheet-fit').dataset.scale*100)+'%'")   # noqa: E731
        l0 = label()
        self.assertEqual(l0, real())
        b.click("#mnTrBtn")
        b.wait("!document.querySelector('.mnpane')")
        b.pump(0.4)
        self.assertEqual(label(), real(), "re-fitted, and the label says the new real size")
        self.assertNotEqual(label(), l0)
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
        b.wait("document.activeElement && document.activeElement.id==='mnTrBtn'", 5)   # focus back on the Transcript button
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
        real = lambda: self.ev("Math.round(+document.querySelector('#v-minutes .sheet-fit').dataset.scale*100)+'%'")   # noqa: E731
        self.assertEqual(z(), 1, "opens fitted to the width")
        fit = self.ev(f"(()=>{{const s=document.querySelector('#v-minutes .sheet-scroll'), f=document.querySelector('#v-minutes .sheet-fit'); return Math.min(s.clientWidth-32,{A4_PX})-f.getBoundingClientRect().width}})()")
        self.assertLess(abs(fit), 2, "the page fills the room, never past its real size")
        self.assertEqual(self.ev("document.querySelector('#v-minutes .sheet-zv').textContent"), real(), "the label says the real size")
        self.wheel("#v-minutes .sheet-scroll", -60, ctrl=True, times=40)
        self.assertEqual(z(), 2.5, "pinch in to 250%")
        self.assertEqual(self.ev("document.querySelector('#v-minutes .sheet-zv').textContent"), real())
        self.wheel("#v-minutes .sheet-scroll", 60, ctrl=True, times=60)
        self.assertEqual(z(), 0.5, "pinch out to 50%")
        self.b.click("#v-minutes .sheet-zoom button[aria-label='Zoom in']")
        self.b.pump(0.2)
        self.assertEqual(z(), 0.6)
        self.b.click("#v-minutes .sheet-zv")
        self.b.pump(0.2)
        self.assertEqual(z(), 1, "back to fit to width")

    def test_09b_fit_to_width_stops_at_100_and_centres_the_page_and_zoom_still_goes_past(self):
        b = self.b
        label = lambda: self.ev("document.querySelector('#v-minutes .sheet-zv').textContent")   # noqa: E731
        real = lambda: self.ev("Math.round(+document.querySelector('#v-minutes .sheet-fit').dataset.scale*100)+'%'")   # noqa: E731
        # left and right are measured inside the scroller's client box: a classic scrollbar (15 px in Linux Chrome, none with
        # the Mac's overlay scrollbars) takes room on the right that the page is rightly not centred over
        room = lambda: self.ev("""(()=>{ const el=document.querySelector('#v-minutes .sheet-scroll'), s=el.getBoundingClientRect(), f=document.querySelector('#v-minutes .sheet-fit').getBoundingClientRect();
          const inL=s.left+el.clientLeft, inR=inL+el.clientWidth;
          return {w: f.width, left: f.left-inL, right: inR-f.right, room: s.width-32, bar: el.offsetWidth-el.clientWidth-2*el.clientLeft}; })()""")   # noqa: E731
        b.click("#mnTrBtn")                                     # the transcript hidden: room for more than the real size at 1400
        b.wait("!document.querySelector('.mnpane')")
        b.pump(0.4)
        try:
            r = room()
            self.assertGreater(r["room"], A4_PX + 50, f"wide enough to test the cap: {r}")
            self.assertEqual(real(), "100%", "fit to width stops at the real size")
            self.assertEqual(label(), "100%", "and the label says so")
            self.assertLess(abs(r["w"] - A4_PX), 2, f"the page is A4 wide: {r}")
            self.assertLess(abs(r["left"] - r["right"]), 4, f"centred, grey either side: {r}")
            self.wheel("#v-minutes .sheet-scroll", -60, ctrl=True, times=40)
            self.assertEqual(real(), "250%", "a pinch still goes past 100%")
            self.assertEqual(label(), "250%")
            b.click("#v-minutes .sheet-zv")                    # the label re-fits, still capped
            b.pump(0.3)
            self.assertEqual(real(), "100%")
            self.assertEqual(label(), "100%")
            b.click("#v-minutes .sheet-zoom button[aria-label='Zoom in']")
            b.pump(0.2)
            self.assertEqual(label(), "110%", "the + button goes past 100% too")
        finally:
            b.click("#mnTrBtn")
            b.wait("document.querySelector('.mnpane')")

    def test_10_one_version_icon_tools_and_the_export_menu(self):
        bar = "#v-minutes .sheet-bar"
        txt = self.ev(f"document.querySelector({json.dumps(bar)}).textContent")
        for gone in ("One version", "Internal + distributed", "Side by side", "Distributed"):
            self.assertNotIn(gone, txt)
        self.assertFalse(self.ev("!!document.querySelector('#v-minutes [data-mnmode], #v-minutes .mnio')"), "no switch, no Internal only marks")
        icons = self.ev(f"[...document.querySelectorAll('{bar} .ib')].map(b=>b.getAttribute('aria-label'))")
        self.assertEqual(icons, ["Show as exported", "Transcript", "Export", "Read the transcript again"])      # #283: plain words
        labelled = self.ev(f"[...document.querySelectorAll('{bar} button')].filter(b=>!b.classList.contains('ib') && b.textContent.trim().length>4).map(b=>b.textContent.trim())")
        self.assertEqual(labelled, ["Approve minutes · tracks 3 actions"], "only Approve minutes keeps a label, and it says what it tracks (#302 A)")
        self.assertIn("M12 4v11", self.ev("document.querySelector('#v-minutes [data-mnexport] svg').innerHTML"), "Export is the download arrow")
        self.assertRegex(self.ev("document.querySelector('#v-minutes .sheet-status').textContent"), r"^Saved · version \d+$")
        self.assertEqual(self.ev("[...document.querySelectorAll('#mnSum b')].map(b=>b.textContent)"), ["3", "2"], "bold counts")
        self.b.click("#v-minutes [data-mnexport]")
        self.b.wait("document.querySelector('.ddmenu.on')")
        items = self.ev("[...document.querySelectorAll('.ddmenu.on [role=menuitem]')].map(x=>[x.querySelector('b,strong,.mname')?x.querySelector('b,strong,.mname').textContent:x.textContent, x.textContent])")
        names = [i[0] for i in items]
        self.assertEqual(names, ["Word", "PDF", "HTML", "Draft the follow-up email",       # #330: Shareable first, then Internal
                                 "Word (Internal)", "PDF (Internal)", "HTML (Internal)", "Draft an Internal follow-up email"])
        for name, whole in items[:3] + items[4:7]:
            self.assertGreater(len(whole), len(name) + 10, f"{name} has its description line")
        self.assertIn("edits never come back", items[4][1], "Word is an export only")
        self.b.key("Escape")

    def test_11_approve_with_a_problem_asks_first_then_registers_the_ticked_items(self):
        b = self.b
        b.click("#mnApproveBtn")
        b.wait("document.getElementById('mnApprove').open")
        self.assertEqual(self.ev("document.getElementById('mnApproveH').textContent"), "Approve the minutes")
        self.assertIn("Before these minutes are approved, 2 ticked items have", self.ev("document.querySelector('#mnApprove .sub').textContent"))
        self.assertGreater(self.ev("document.getElementById('mnApprove').getBoundingClientRect().width"), 700, "as wide as the mockup's")
        self.assertRegex(self.ev("(document.querySelector('#mnApprove .mnap-filed')||{}).textContent||''"),
                         r"^Files the minutes as 2026-10-\d\d .+\.html in .+", "where the minutes are filed (review L1)")
        open_checks = self.ev("document.querySelectorAll('#v-minutes .mncheck').length")      # the owner one is listed above already
        self.assertTrue(open_checks, "the meeting has checks open")
        self.assertEqual(self.ev("document.querySelectorAll('#mnApprove .mnap-ck li').length"), open_checks, "the checks still open (review L1)")
        lis = self.ev("[...document.querySelectorAll('#mnApprove .mnap-l li')].map(l=>l.textContent)")
        self.assertEqual(sorted(lis), ["Pat Unknown needs detailsShare the cut-over plan with the client",
                                       "Possible duplicate of ABC-A-002Book the UAT test environment"], "just the ticked items with a real problem")
        b.click("#mnApproveBack")
        b.pump(0.3)
        self.assertFalse(self.ev("document.getElementById('mnApprove').open"), "Go back")
        self.assertEqual(self.staged(1)["decision"], "pending", "nothing approved")
        b.click("#mnApproveBtn")
        b.wait("document.getElementById('mnApprove').open")
        b.click("#mnApproveGo")
        self.file_box()
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
        self.file_box()
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
        self.file_box()
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
        self.file_box()
        b.wait("document.getElementById('snack').classList.contains('on') && /Minutes approved/.test(document.getElementById('snack').textContent)", 30)
        self.assertIn("Minutes approved · no work items registered", self.snack())
        self.assertEqual([a for a in self.rows_of("actions") if a["description"] == "Send the revised SOW to the client"], [])
        self.assertIsNotNone(self.filed(), "the minutes are filed")
        b.wait("document.querySelector('#v-minutes .mnmeta') && /Approved and filed/.test(document.querySelector('#v-minutes .mnmeta').textContent)", 15)

    def test_14_at_1400_one_row_at_900_two_and_the_transcript_beside_the_sheet(self):
        for w in (1400, 900):
            with self.subTest(width=w):
                self.b.resize(w, 1000)
                self.b.pump(0.6)
                bar = self.ev("""(()=>{ const b=document.querySelector('#v-minutes .sheet-bar'), kids=[...b.querySelectorAll('button, .mnsum, .sheet-status')].filter(x=>x.offsetParent);
                  const tops=new Set(kids.map(k=>Math.round(k.getBoundingClientRect().top+k.getBoundingClientRect().height/2)));
                  return {h: b.getBoundingClientRect().height, rows: Math.max(...tops)-Math.min(...tops), right: Math.max(...kids.map(k=>k.getBoundingClientRect().right)), w: b.getBoundingClientRect().right}; })()""")
                self.assertLess(bar["rows"], 12 if w > 900 else 50, f"one row at {w} (two at 900, as the mockup): {bar}")
                self.assertLessEqual(bar["right"], bar["w"] + 0.5, f"nothing cut off at {w}")
                off = self.ev("""Math.max(...[...document.querySelectorAll('#v-minutes table.mnt')].map(t=>{ const r=t.querySelector('tbody tr');
                  return Math.max(...[...t.querySelectorAll('thead th')].map((h,i)=>Math.abs(h.getBoundingClientRect().left-r.children[i].getBoundingClientRect().left))); }))""")
                self.assertLess(off, 1.5)
                self.assertLessEqual(self.ev("document.scrollingElement.scrollWidth - innerWidth"), 0, "no sideways scroll")
                side = self.ev("""(()=>{ const p=document.querySelector('.mnpane').getBoundingClientRect(), s=document.querySelector('#v-minutes .mnsheet').getBoundingClientRect();
                  return {beside: p.left >= s.right - 1 && p.top < s.top + 60, w: p.width}; })()""")
                self.assertTrue(side["beside"], f"the transcript beside the sheet at {w}: {side}")
                if w == 900:
                    self.assertLess(abs(side["w"] - 280), 2, "narrower at 900")
                    turn = self.ev(f"document.querySelector(\"{ROW % 2}\").dataset.turn")
                    self.move(*self.centre(ROW % 2, True))
                    lit = self.ev(f"(()=>{{const l=document.querySelector(\".mnturns li[data-turn='{turn}']\"), r=l.getBoundingClientRect(); return l.classList.contains('hl') && r.top>=0 && r.bottom<=innerHeight && r.width>0}})()")
                    self.assertTrue(lit, "hovering a row lights a turn you can see")
                    self.move(5, 5)


    def test_15_esc_on_ai_keeps_the_words_and_read_again_never_touches_ask_creaite(self):
        b = self.b
        ed = ROW % 2 + " .mnit .sheet-ed"
        b.click(ed)
        self.caret_end(ed)
        b.type(" soon")
        b.eval("""(()=>{ const h=document.querySelector(%s).cxed, doc=h.editor.state.doc; let at=-1;
          doc.descendants((n,pos)=>{ if(at<0&&n.isText){ const i=n.text.indexOf('UAT'); if(i>=0) at=pos+i; } });
          h.focus(); h.editor.commands.setTextSelection({from:at,to:at+3}); })()""" % json.dumps(ed))
        b.wait("document.querySelector('#aiLayer .aispark')", 5)
        b.key("Escape")
        b.pump(0.3)
        self.assertFalse(self.ev("!!document.querySelector('#aiLayer .aispark')"), "Esc closes AI")
        self.assertIn("soon", self.ev(f"document.querySelector({json.dumps(ed)}).textContent"), "and the words typed stay (review LOW)")
        b.key("Escape")                                         # a second Esc puts the words back, as before
        b.pump(0.4)
        self.assertNotIn("soon", self.ev(f"document.querySelector({json.dumps(ed)}).textContent"))
        b.eval("openChat()")
        b.wait("document.getElementById('chIn')", 5)
        b.eval("(()=>{const t=document.getElementById('chIn'); t.value='half typed'; t.dispatchEvent(new Event('input',{bubbles:true}));})()")
        b.eval("document.getElementById('mnReBtn').click()")              # #283: Read again asks first, on the bar
        b.wait("document.getElementById('mnReGo')", 5)
        self.assertIn("Your edits here are set aside", self.ev("document.querySelector('#v-minutes .mnre').textContent"))
        b.eval("document.getElementById('mnReCancel').click()")
        b.wait("document.getElementById('mnReBtn')", 5)
        self.assertEqual(self.ev("document.getElementById('chIn').value"), "half typed", "ask creaite is never written into")


    def test_15b_read_again_runs_on_the_bar_and_opens_the_new_draft_with_undo(self):
        """#283: Read again is its own run (reLive, POST /api/minutes/reextract), never an ask creaite message: it asks first,
        then its step and Stop are on the bar and Approve minutes waits; at the end the new draft opens and the toast has Undo
        (reUndoLive), which brings the earlier one back. The server is stood in for (the seams): test_reextract runs the route."""
        b = self.b
        b.eval("""(()=>{ window.__re=[]; const p=%s;
          intakeSeams.reLive((x,onEv)=>{ window.__re.push(['run',x]); onEv({type:'run',id:'x-ui-1'}); onEv({type:'step',label:'Reading the transcript'});
            return new Promise(r=>{ window.__reDone=()=>r({ok:true,reextract:{run:'x-ui-1',state:'replaced',proposal:p,path:'x'},
              closure:{line:'Read again: 5 items found in the meeting. Your earlier version is set aside: Undo brings it back.'}}); }); });
          intakeSeams.reUndoLive(run=>{ window.__re.push(['undo',run]); return Promise.resolve({ok:true,proposal:p}); }); })()""" % json.dumps(self.proposal))
        b.eval("document.getElementById('mnReBtn').click()")
        b.wait("document.getElementById('mnReGo')", 5)
        b.eval("document.getElementById('mnReGo').click()")
        b.wait("document.getElementById('mnReStop')", 5)
        self.assertIn("Reading the transcript again: Reading the transcript", self.ev("document.querySelector('#v-minutes .mnre').textContent"))
        self.assertTrue(self.ev("document.getElementById('mnApproveBtn').disabled"), "Approve minutes waits while it reads")
        b.eval("window.__reDone()")
        b.wait("document.getElementById('mnReBtn') && /Read again: 5 items/.test(document.getElementById('snack').textContent)", 15)
        b.click("#snackU")
        b.wait("window.__re.length===2", 10)
        self.assertEqual(self.ev("window.__re"), [["run", self.proposal], ["undo", "x-ui-1"]])
        b.wait("/earlier minutes are back/.test(document.getElementById('snack').textContent)", 10)
        b.wait("document.querySelector('#v-minutes .sheet-bar') && !document.getElementById('mnReStop')", 10)

    def test_16_the_full_template_on_one_continuous_sheet_with_a_thin_page_marker(self):
        """Item 4 (PM, Alan agreed, 20-10-2026): the whole minutes template stays, laid out as one continuous sheet: a section is
        never pushed to the next page (no blank gap before page 2); a thin marker shows where a page would break."""
        b = self.b
        text = self.ev("document.querySelector('#v-minutes .page').innerText+' '+[...document.querySelectorAll('#v-minutes .page input.sheet-h')].map(i=>i.value).join(' ')")
        for words in ("Internal", "Executive Summary", "Updates", "Decisions", "Risks", "Issues", "Actions", "Open Questions", "Source"):
            self.assertIn(words, text, f"the template keeps {words}")
        self.assertTrue(self.ev("!!document.querySelector('#v-minutes .mncov, #v-minutes [data-extra=coverage]') || /Agenda coverage/i.test(document.querySelector('#v-minutes .page').innerText)"),
                        "and the agenda coverage")
        gaps = """(()=>{ const secs=[...document.querySelectorAll('#v-minutes .page > section[data-id]')];
          return {push: secs.map(s=>s.style.marginTop).filter(m=>m && m!=='0px'), gap: (k=>Math.max(0,...k.slice(1).map((s,i)=>s.offsetTop-(k[i].offsetTop+k[i].offsetHeight))))([...document.querySelector('#v-minutes .page').children].filter(x=>x.offsetParent)),
            marks: [...document.querySelectorAll('#v-minutes .sheet-break')].map(m=>[getComputedStyle(m).borderTopWidth, m.textContent])}; })()"""
        for h in (640, 700, 760, 820, 880):                   # a tall block in the summary: some section straddles the first page's foot
            with self.subTest(spacer=h):
                b.eval(f"(()=>{{ document.querySelectorAll('#v-minutes .t16sp').forEach(x=>x.remove()); const d=document.createElement('div'); d.className='t16sp'; d.style.height='{h}px';"
                       "document.querySelector('#v-minutes .page > section[data-id=summary], #v-minutes .page > section[data-id]:nth-of-type(2)').appendChild(d); })()")
                b.pump(0.4)
                g = self.ev(gaps)
                self.assertEqual(g["push"], [], f"no section pushed to the next page: {g}")
                self.assertLess(g["gap"], 48, f"no blank gap before page 2: {g}")
                self.assertTrue(g["marks"], f"a page marker: {g}")
                self.assertEqual(g["marks"][0], ["1px", "Page 2"], f"thin, and says the page: {g}")
        b.eval("document.querySelectorAll('#v-minutes .t16sp').forEach(x=>x.remove())")

    def test_16b_the_page_marker_never_crosses_a_row_or_a_line(self):
        """PM follow-up (20-10-2026): the dashed Page n marker moves to the next gap between rows or blocks; a table row stays whole."""
        b = self.b
        cross = """(()=>{ const out=[]; for (const m of document.querySelectorAll('#v-minutes .sheet-break')) { const y=m.getBoundingClientRect().top;
            for (const e of document.querySelectorAll('#v-minutes .page tr, #v-minutes .page p, #v-minutes .page li, #v-minutes .page h2, #v-minutes .page h3')) {
              const r=e.getBoundingClientRect(); if (r.height && y > r.top+1 && y < r.bottom-1) out.push([m.textContent, e.tagName, Math.round(y-r.top), Math.round(r.height)]); } }
          return {n: document.querySelectorAll('#v-minutes .sheet-break').length, cross: out}; })()"""
        hit = 0
        for h in range(560, 1000, 12):                       # a tall block in the summary moves the page's foot through every row in turn
            b.eval(f"(()=>{{ document.querySelectorAll('#v-minutes .t16sp').forEach(x=>x.remove()); const d=document.createElement('div'); d.className='t16sp'; d.style.height='{h}px';"
                   "document.querySelector('#v-minutes .page > section[data-id=summary]').appendChild(d); })()")
            b.pump(0.25)
            g = self.ev(cross)
            hit += g["n"] > 0
            with self.subTest(spacer=h):
                self.assertEqual(g["cross"], [], f"the marker sits in a gap, never across a row or a line: {g}")
        b.eval("document.querySelectorAll('#v-minutes .t16sp').forEach(x=>x.remove())")
        self.assertGreater(hit, 20, "a marker was there to check")

    def test_17_section_headings_with_their_counts_beside_them(self):
        got = self.ev("""Object.fromEntries([...document.querySelectorAll('#v-minutes .page section[data-id] > h2')].filter(h=>h.querySelector('.sheet-hn')).map(h=>{
          const i=h.querySelector('input.sheet-h'), n=h.querySelector('.sheet-hn'), c=document.createElement('canvas').getContext('2d'), cs=getComputedStyle(i);
          c.font=`${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
          const end=i.getBoundingClientRect().left+parseFloat(cs.paddingLeft)+parseFloat(cs.borderLeftWidth)+c.measureText(i.value).width;
          return [h.parentElement.dataset.id, [i.value, n.textContent, Math.round(n.getBoundingClientRect().left-end)]]; }))""")
        self.assertEqual(got["decisions"][:2], ["Decisions", "1"])
        self.assertEqual(got["actions"][:2], ["Actions", "3"], "Actions, as the mockup")
        for sec, (_, _, gap) in got.items():
            self.assertLess(gap, 14, f"{sec}: the count sits beside the heading, as the mockup: {got}")

    def test_18_dark_theme_the_white_paper_keeps_light_state_colours(self):
        """Cap's #268 review M2: in a dark theme the paper stays white, so the hover row, an Urgent or High priority and the
        "needs details" chip use light values: text 4.5:1 or more, and the hover row clearly differs from the paper."""
        got = self.ev("""(()=>{
          const rgb=c=>{const m=c.match(/[\\d.]+/g).map(Number); return m.length>3&&m[3]===0?null:m.slice(0,3)};
          const lum=([r,g,b])=>{const f=v=>{v/=255;return v<=.03928?v/12.92:((v+.055)/1.055)**2.4}; return .2126*f(r)+.7152*f(g)+.0722*f(b)};
          const ratio=(a,b)=>{const x=lum(a),y=lum(b); return (Math.max(x,y)+.05)/(Math.min(x,y)+.05)};
          const bg=e=>{for(;e;e=e.parentElement){const c=rgb(getComputedStyle(e).backgroundColor); if(c) return c} return [255,255,255]};
          const out={};
          for (const mode of ['dark','light']) {
            document.documentElement.setAttribute('data-theme',mode);
            const row=document.querySelector("#v-minutes tr.mi[data-n='1']"); row.classList.add('hl');
            const td=row.querySelector('td:nth-child(2)'), paper=rgb(getComputedStyle(document.querySelector('#v-minutes .sheet-a4 .page')).backgroundColor);
            const sel=row.querySelector('.msel'), cls=sel.className;
            const r={hover:ratio(rgb(getComputedStyle(td).color),bg(td)), hoverVsPaper:ratio(bg(td),paper)};
            row.classList.remove('hl');
            for (const p of ['U','H']) { sel.className=cls+' pr-'+p; r['pr'+p]=ratio(rgb(getComputedStyle(sel).color),bg(sel)); }
            sel.className=cls;
            const chip=document.querySelector('#v-minutes .mck:not(.info)'); r.chip=chip?ratio(rgb(getComputedStyle(chip).color),bg(chip)):0;
            r.paper=paper.join(','); out[mode]=r;
          }
          document.documentElement.removeAttribute('data-theme');
          return out; })()""")
        for mode, r in got.items():
            self.assertEqual(r["paper"], "255,255,255", f"{mode}: the paper stays white")
            for k in ("hover", "prU", "prH", "chip"):
                self.assertGreaterEqual(r[k], 4.5, f"{mode}: {k} legible on the paper: {r}")
            self.assertGreaterEqual(r["hoverVsPaper"], 1.15, f"{mode}: the hover row is clearly visible: {r}")

    def test_19_a_sensitive_item_shows_a_read_only_tag(self):
        """Cap's #268 review L2: an item marked Sensitive (or partner-only, or excluded) carries a read-only tag on its row."""
        p = self.v.root / "system/staging" / self.proposal
        data = json.loads(p.read_text(encoding="utf-8"))
        next(i for i in data["items"] if i["n"] == 4)["flags"] = ["sensitive"]
        p.write_text(json.dumps(data), encoding="utf-8")
        subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, 'system/scripts'); import minutes_record; "
                        f"minutes_record.change({me.DRAFT!r}, {{'op': 'deadline', 'n': 1, 'words': 'Friday'}})"],
                       cwd=self.v.root, capture_output=True, text=True, check=True)       # any change re-reads the staged items
        self.open()
        self.b.wait(f"document.querySelector(\"{ROW % 4} .mnsens\")", 15)
        self.assertEqual(self.ev(f"document.querySelector(\"{ROW % 4} .mnsens\").textContent"), "Sensitive")
        self.assertEqual(self.ev("document.querySelectorAll('#v-minutes .mnsens').length"), 1, "only the marked row")
        self.assertEqual(self.ev(f"document.querySelectorAll(\"{ROW % 4} .mnsens button\").length"), 0, "read only")


if __name__ == "__main__":
    unittest.main()
