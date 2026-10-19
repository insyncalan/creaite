"""#232-B (v2.5.0): Intake and Review's proposal side, in a real browser against the live server.

The full proposal row (kind pill, title, ONE emphasised meta line, quote, source with Open source, Approve, Reject with a reason),
the two groups under a meeting (Needs your decision / Routine, the approved heading), Approve routine (one apply, one Undo,
never the first group), the rule shared with the server (`hold`, and the invalid flag), the peek with previous and next, the
restored hooks from #229 and the arrow and Esc keys.

Run: python3 dev/tests/test_intake_review_proposals.py   (needs Google Chrome; skipped otherwise). Desktop width only.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_review_triage import load_queue  # noqa: E402

ROW = "#v-intake-review tr.irprop[data-irn]"
ROUTINE_HEAD = "Each has a project and no conflict, and none is a change you approve one by one."

SHOW = """(()=>{
  const live=REV.filter(r=>!r.done), needs=live.filter(r=>r.hold).map(r=>r.n), routine=live.filter(r=>!r.hold).map(r=>r.n);
  D.intake_review={v:1,meetings:[{id:'mA',src:'calendar',title:'Sample steering',day:'2026-10-05',start:'09:00',p:null,stage:'drafted',state:'proposals',
    age:0,stale:false,groups:{needs,routine}}],mail:{needs:[],routine:[]},other:{needs:[],routine:[]},later:[],not_needed:[],counts:{}};
  irOpen.value='mA'; irStage.value='all'; irFolded.value={}; go('intake-review'); irTick.value++; return {needs,routine}; })()"""


class Base(LiveBrowserCase):
    width, height = 1500, 1100

    @classmethod
    def load(cls, v):
        populate(v)
        load_queue(v)

    def show(self):
        b = self.b
        b.eval("localStorage.removeItem('creaite-ir-view'); irSetView('list'); go('today')")
        out = b.eval(SHOW)
        b.wait(f"!!document.querySelector('{ROW}')")
        return out

    def redraw(self, js=""):
        self.b.eval(f"{js}; irTick.value++")
        self.b.pump(0.2)


class Rows(Base):
    shared_server = True

    def test_rvBulkOK_equals_hold_for_every_kind_and_the_invalid_flag(self):
        b = self.b
        self.show()
        res = b.eval("""REV.filter(r=>!r.done).map(r=>({n:r.n,hold:r.hold,ok:rvBulkOK(r)}))""")
        self.assertTrue(res)
        for r in res:
            self.assertIsInstance(r["hold"], str, "every Review row carries hold")
            self.assertEqual(r["ok"], r["hold"] == "", r)
        self.assertTrue(any(r["hold"] == "" for r in res) and any(r["hold"] for r in res))
        # the server holds an invalid item back; the page must too (it did not read the flag before)
        ok = b.eval("""(()=>{ const r=REV.find(x=>!x.done&&!x.hold); r.flags=[...(r.flags||[]),'invalid']; return [rvBulkOK(r), r.n]; })()""")
        self.assertFalse(ok[0])
        # a hold the page has not seen as a flag still holds
        self.assertFalse(b.eval("""(()=>{ const r=REV.find(x=>!x.done&&!x.hold&&!(x.flags||[]).includes('invalid')); r.hold='health change'; return rvBulkOK(r); })()"""))

    def test_the_two_groups_and_the_approved_routine_heading(self):
        b = self.b
        g = self.show()
        self.assertTrue(g["needs"] and g["routine"])
        self.assertEqual(b.eval("[...document.querySelectorAll('#v-intake-review tr.icsubhead')].map(t=>t.dataset.irg)"), ["needs", "routine"])
        self.assertEqual(b.eval("document.querySelector('tr.icsubhead.routine .icshs').textContent"), ROUTINE_HEAD)
        self.assertIn("Needs your decision", b.eval("document.querySelector('tr.icsubhead.needs .icsh').textContent"))
        self.assertEqual(b.eval(f"document.querySelectorAll('{ROW}').length"), len(g["needs"]) + len(g["routine"]))
        # every routine row sits under the Routine head, every other under the first
        order = b.eval("[...document.querySelectorAll('#v-intake-review tr.icsubhead, #v-intake-review tr.irprop')].map(t=>t.dataset.irg||t.dataset.irn)")
        cut = order.index("routine")
        self.assertEqual(sorted(int(x) for x in order[1:cut]), sorted(g["needs"]))
        self.assertEqual(sorted(int(x) for x in order[cut + 1:]), sorted(g["routine"]))
        self.assertEqual(b.eval("document.querySelector('[data-ira=routine]').textContent.replace(/\\s+/g,' ').trim()"),
                         f"Approve routine ({len(g['routine'])})")

    def test_a_proposal_row_has_its_parts(self):
        b = self.b
        g = self.show()
        n = g["routine"][0]
        row = f"{ROW}[data-irn='{n}']"
        self.assertEqual(b.eval(f"document.querySelector(\"{row} .ickind\").textContent"), "Action")
        self.assertTrue(b.eval(f"document.querySelector(\"{row} .icttl\").textContent.trim().length>3"))
        self.assertTrue(b.eval(f"!!document.querySelector(\"{row} [data-ira=approve]\")"))
        self.assertEqual(b.eval(f"document.querySelector(\"{row} [data-ira=reject]\").getAttribute('aria-haspopup')"), "menu")
        self.assertIn("Routine", b.eval(f"document.querySelector(\"{row} .why\").textContent"))
        # a risk: its own pill; an update with evidence: the quote with its rail
        risk = next(r for r in b.eval("REV.filter(r=>!r.done&&r.kind==='raid').map(r=>({n:r.n,type:r.rec.type}))"))
        self.assertEqual(b.eval(f"document.querySelector(\"{ROW}[data-irn='{risk['n']}'] .ickind\").textContent"), risk["type"])
        self.assertIn("approve individually", b.eval(f"document.querySelector(\"{ROW}[data-irn='{risk['n']}'] .why\").textContent"))
        up = b.eval("REV.find(r=>!r.done&&r.kind==='update'&&r.rec.target).n")
        self.redraw(f"(()=>{{ const r=REV.find(x=>x.n=={up}); r.rec.why='Sara said it was finished on the call'; }})()")
        self.assertEqual(b.eval(f"document.querySelector(\"{ROW}[data-irn='{up}'] .icq\").textContent"), "Sara said it was finished on the call")

    def test_an_update_says_what_changes_in_words(self):
        b = self.b
        self.show()
        up = b.eval("REV.find(r=>!r.done&&r.kind==='update'&&r.rec.field==='status'&&r.rec.target)")
        self.assertTrue(up, "the sample has a closing update")
        line = b.eval(f"document.querySelector(\"{ROW}[data-irn='{up['n']}'] .why\").textContent")
        self.assertIn(f"Closes {up['rec']['target']}", line)
        self.assertRegex(line, r"status [^→]+ → Closed")
        self.redraw(f"(()=>{{ REV.find(x=>x.n=={up['n']}).dn={{strength:'Looks done',ev:'Mail from Sara'}}; }})()")
        self.assertIn("Looks done", b.eval(f"document.querySelector(\"{ROW}[data-irn='{up['n']}'] .why\").textContent"))

    def test_one_meta_line_with_detail_on_hover_and_no_times(self):
        b = self.b
        self.show()
        res = b.eval("""[...document.querySelectorAll('#v-intake-review tr.irprop')].map(tr=>{
          const w=[...tr.querySelectorAll('td.title .why')].filter(e=>!e.closest('.cfvs'));
          return [w.length, w[0]?w[0].getBoundingClientRect().height:0, parseFloat(getComputedStyle(w[0]).lineHeight)||16, w[0]?w[0].textContent:'']; })""")
        self.assertTrue(res)
        for n, h, lh, text in res:
            self.assertEqual(n, 1, "a proposal row has exactly one meta line")
            self.assertLessEqual(h, lh * 1.5 + 1, "the meta line wraps")
            self.assertNotRegex(text, r"\b\d{1,2}:\d{2}\b", "the source line shows no time (Open source opens the whole file)")
        tip = b.eval(f"document.querySelector(\"{ROW} .why[data-tip]\") ? document.querySelector(\"{ROW} .why[data-tip]\").dataset.tip : ''")
        self.assertTrue(tip.strip(), "the detail (owner, due, priority) is the line's tooltip")
        p = b.box(f"{ROW} .why[data-tip]")
        b.call("Input.dispatchMouseEvent", type="mouseMoved", x=p["x"], y=p["y"], button="none")
        b.wait("!!document.getElementById('tip')&&document.getElementById('tip').classList.contains('on')&&document.getElementById('tip').textContent.trim().length>0", timeout=5)

    def test_the_restored_hooks_stay_on_the_row(self):
        b = self.b
        g = self.show()
        a = g["routine"][0]
        # AI-drafted: the Drafted tag
        self.redraw(f"REV.find(x=>x.n=={a}).drafted='done'")
        self.assertIn("Drafted", b.eval(f"document.querySelector(\"{ROW}[data-irn='{a}'] .tag.drrv\").textContent"))
        # a due date on a Saturday: the weekend note with its two buttons, beside the one meta line
        self.redraw(f"(()=>{{ const r=REV.find(x=>x.n=={a}); r.rec.due='2026-10-10'; }})()")
        self.assertEqual(b.eval(f"document.querySelectorAll(\"{ROW}[data-irn='{a}'] [data-wkrv]\").length"), 2)
        self.assertEqual(b.eval(f"document.querySelectorAll(\"{ROW}[data-irn='{a}'] td.title .why\").length"), 1)
        # no Word draft: the notice
        d = b.eval("(REV.find(r=>!r.done&&r.kind==='draft')||{}).n")
        if d:
            self.redraw(f"REV.find(x=>x.n=={d}).nodraft=true")
            self.assertIn("No Word draft was made for these minutes", b.eval(f"document.querySelector(\"{ROW}[data-irn='{d}']\").textContent"))
        # approve individually, and Draft a response on a risk with none
        r = b.eval("REV.find(x=>!x.done&&x.kind==='raid').n")
        self.redraw(f"REV.find(x=>x.n=={r}).rec.resp=''")
        self.assertIn("approve individually", b.eval(f"document.querySelector(\"{ROW}[data-irn='{r}'] .why\").textContent"))
        self.assertTrue(b.eval(f"!!document.querySelector(\"{ROW}[data-irn='{r}'] [data-drrisk]\")"))

    def test_a_conflict_shows_its_block_and_the_two_choices(self):
        b = self.b
        self.show()
        c = b.eval("REV.find(r=>!r.done&&(r.flags||[]).includes('conflict')).n")
        row = f"{ROW}[data-irn='{c}']"
        self.assertTrue(b.eval(f"!!document.querySelector(\"{row} .cfvs\")"))
        self.assertTrue(b.eval(f"!!document.querySelector(\"{row} [data-act=ck]\") && !!document.querySelector(\"{row} [data-act=co]\")"))
        self.assertFalse(b.eval(f"!!document.querySelector(\"{row} [data-ira=approve]\")"))
        self.assertEqual(b.eval(f"document.querySelectorAll(\"{row} td.title .why\").length"), 1)

    def test_open_source_is_a_link_to_the_whole_file(self):
        b = self.b
        self.show()
        self.redraw("(()=>{ const r=REV.find(x=>!x.done&&x.kind==='actions'); r.src='projects/ABC Example/minutes/2026-10-05 Steering.docx'; window.__osrc=r.n; })()")
        n = b.eval("window.__osrc")
        a = f"{ROW}[data-irn='{n}'] a.srclink"
        self.assertEqual(b.eval(f"document.querySelector(\"{a}\").dataset.openfile"), "projects/ABC Example/minutes/2026-10-05 Steering.docx")
        self.assertEqual(b.eval(f"document.querySelector(\"{a}\").textContent"), "Open source")
        self.assertFalse(b.eval(f"document.querySelector(\"{a}\").dataset.t"))      # no jump to a time

    def test_a_click_opens_the_peek_and_previous_and_next_step_through(self):
        b = self.b
        self.show()
        ns = b.eval(f"[...document.querySelectorAll('{ROW}')].map(t=>+t.dataset.irn).filter(n=>['actions','raid','decisions','update'].includes(REV.find(r=>r.n===n).kind))")
        self.assertGreaterEqual(len(ns), 3)
        b.click(f"{ROW}[data-irn='{ns[0]}'] .icttl")
        b.wait(f"document.getElementById('panel').classList.contains('on') && CUR && CUR.n=={ns[0]}")
        self.assertEqual(b.eval("irPeek.value"), ns[0])
        b.click("#pkNext")
        b.wait(f"CUR.n=={ns[1]}")
        b.click("#pkPrev")
        b.wait(f"CUR.n=={ns[0]}")
        # Esc closes the peek first and leaves the meeting open; a second Esc closes the meeting
        b.key("Escape")
        b.wait("!document.getElementById('panel').classList.contains('on')")
        self.assertEqual(b.eval("irOpen.value"), "mA")
        self.assertIsNone(b.eval("irPeek.value"))
        b.key("Escape")
        b.wait("irOpen.value===null")

    def test_reject_opens_the_reasons_menu_and_keys_move_between_rows(self):
        b = self.b
        g = self.show()
        n = g["routine"][0]
        b.click(f"{ROW}[data-irn='{n}'] [data-ira=reject]")
        b.wait("!!rjMenu.value && rjMenu.value.rows.length===1")
        b.key("Escape")
        b.wait("!rjMenu.value")
        first, second = b.eval(f"[...document.querySelectorAll('{ROW}')].map(t=>+t.dataset.irn).slice(0,2)")
        b.eval(f"document.querySelector(\"{ROW}[data-irn='{first}']\").focus()")
        b.key("ArrowDown")
        b.wait(f"document.activeElement && document.activeElement.dataset && document.activeElement.dataset.irn=='{second}'")
        b.key("ArrowUp")
        b.wait(f"document.activeElement.dataset.irn=='{first}'")
        self.assertEqual(b.eval("irOpen.value"), "mA")


class Decide(Base):
    """Deciding writes the proposal files: one server for each test."""

    def test_approve_one_then_undo(self):
        b = self.b
        g = self.show()
        n = g["routine"][0]
        t = b.eval(f"REV.find(x=>x.n=={n}).rec.t")
        b.click(f"{ROW}[data-irn='{n}'] [data-ira=approve]")
        b.wait(f"!document.querySelector(\"{ROW}[data-irn='{n}']\")", 20)
        b.wait(f"[...document.querySelectorAll('#v-intake-review')].length===1 && !REV.some(r=>r.n=={n}&&!r.done)", 20)
        self.assertEqual(b.eval("irOpen.value"), "mA")               # an apply never closes the open meeting
        self.assertTrue(any(r["description"] == t for r in self.v.rows("actions")), "approved item reached the tracker")

    def test_approve_routine_is_one_apply_one_undo_and_never_covers_the_first_group(self):
        b = self.b
        g = self.show()
        b.eval("""window.__calls=[]; const f=window.fetch; window.fetch=function(u,o){ try{ window.__calls.push(String(u)); }catch(e){} return f.apply(this,arguments); }""")
        want = [(n, b.eval(f"REV.find(x=>x.n=={n}).rec.t")) for n in g["routine"]]
        b.click("[data-ira=routine]")
        b.wait("!REV.some(r=>!r.done&&!r.hold)", 30)
        b.wait("!document.querySelector('tr.icsubhead.routine')", 20)
        self.assertEqual(b.eval("window.__calls.filter(u=>/\\/api\\/apply$/.test(u)).length"), 1, "one apply for the whole batch")
        self.assertEqual(b.eval("irOpen.value"), "mA")
        made = {r["description"] for r in self.v.rows("actions")}
        for n, t in want:
            kind = b.eval(f"(REV.find(x=>x.n=={n})||{{}}).kind")
            self.assertTrue(t in made or kind != "actions", t)
        # the first group is untouched: the risk, the decision, the closing update, the health change
        self.assertTrue(b.eval(f"[{','.join(map(str, g['needs']))}].every(n=>REV.some(r=>r.n===n&&!r.done))"))
        self.assertFalse(any(r["description"].startswith("Scope creep") for r in self.v.rows("raid")))
        self.assertNotEqual(next(r for r in self.v.rows("actions") if r["id"] == "ABC-A-001")["status"], "Closed")
        # one Undo puts everything back
        b.wait("document.getElementById('snackU') && !document.getElementById('snackU').hidden", 20)
        b.eval("window.__calls.length=0")
        b.click("#snackU")
        b.wait("REV.filter(r=>!r.done&&!r.hold).length>0", 30)
        self.assertEqual(b.eval("window.__calls.filter(u=>/\\/api\\/undo$/.test(u)).length"), 1, "one Undo for the whole batch")
        self.assertFalse(any(r["description"].startswith("Batch ") for r in self.v.rows("actions")))

    def test_reject_with_a_reason(self):
        b = self.b
        g = self.show()
        n = g["routine"][0]
        t = b.eval(f"REV.find(x=>x.n=={n}).rec.t")
        b.click(f"{ROW}[data-irn='{n}'] [data-ira=reject]")
        b.wait("!!rjMenu.value")
        b.key("0")                                                            # No reason (the menu's own key)
        b.wait(f"!document.querySelector(\"{ROW}[data-irn='{n}']\")", 20)
        self.assertFalse(any(r["description"] == t for r in self.v.rows("actions")))


if __name__ == "__main__":
    unittest.main()
