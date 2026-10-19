"""#232-B hardening (v2.5.0): what the brief, the locked mockup and Alan's answers (18-10-2026) ask of the proposal side that the
first cut (p250-b) must keep or still owes. Real Chrome against the live server.

Covered: the approved routine wording (exact, with its full stop); rvBulkOK is the server's rule (`hold`) and also respects the
"invalid" flag; Approve routine never covers minutes, reports, health changes, new decisions, decisions made, new risks, a conflict
or an invalid item, even when the page is handed a model that puts them in the routine group; a guessed field does NOT make an
item non-routine; an invalid proposal is held back in the list; #229's ONE meta line with the detail on hover; the restored hooks
(.drrv, data-wkrv, "No Word draft was made", approve individually, the conflict block, Draft a response); Reject with a reason and
Undo; Open source opens the whole file (no time); the arrow and Esc keys.

Run: python3 dev/tests/test_intake_review_harden.py   (needs Google Chrome; skipped otherwise). Desktop width only.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import intake_review_support as S  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402
from test_tracker import action  # noqa: E402

ROW = "#v-intake-review tr.irprop"
WORDING = "Each has a project and no conflict, and none is a change you approve one by one."
SRC = "projects/ABC Example Programme/minutes/2026-10-05 Example steering.html — Action Items"


def extras():
    """Every kind the bulk rule holds back, a guessed field (routine), and an invalid item, beside the fixture's own seven."""
    return [
        S.pending({**action(8, description="Conflicting routine action", source=SRC), "flags": ["conflict"]}),
        S.pending({**action(9, description="Invalid routine-looking action", source=SRC), "flags": ["invalid"]}),
        S.pending({**action(10, description="Action with a guessed owner", owner="Sara Example", due_date="2026-12-01", source=SRC),
                   "inferred": [{"field": "owner", "why": "the only person named near it"}]}),
        S.pending({"n": 11, "op": "update", "table": "projects", "id": "ABC", "match": "strong", "flags": [],
                   "changes": {"health": "At risk", "health_reason": "Slipping"}, "source": SRC}),
        S.pending({"n": 12, "op": "update", "table": "decisions", "id": "ABC-D-001", "match": "strong", "flags": [], "changes": {"status": "Made"}, "source": SRC}),
    ]


# the page is handed a model that puts EVERY pending row in the routine group: only rows the rule allows may be approved
ALL_ROUTINE = """(()=>{ const ns=REV.filter(r=>!r.done).map(r=>r.n);
  D.intake_review={v:1,meetings:[{id:'mH',src:'calendar',title:'Hostile model',day:'2026-10-05',start:'09:00',p:null,stage:'drafted',state:'proposals',
    age:0,stale:false,groups:{needs:[],routine:ns}}],mail:{needs:[],routine:[]},other:{needs:[],routine:[]},later:[],not_needed:[],counts:{}};
  irOpen.value='mH'; go('intake-review'); go('intake-review'); return ns; })()"""
SPLIT = """(()=>{ const live=REV.filter(r=>!r.done);
  D.intake_review={v:1,meetings:[{id:'mH',src:'calendar',title:'Sample steering',day:'2026-10-05',start:'09:00',p:null,stage:'drafted',state:'proposals',
    age:0,stale:false,groups:{needs:live.filter(r=>r.hold).map(r=>r.n),routine:live.filter(r=>!r.hold).map(r=>r.n)}}],mail:{needs:[],routine:[]},other:{needs:[],routine:[]},later:[],not_needed:[],counts:{}};
  irOpen.value='mH'; go('intake-review'); go('intake-review'); return live.map(r=>r.n); })()"""


class Base(LiveBrowserCase):
    width, height = 1500, 1100

    @classmethod
    def load(cls, v):
        S.load(v)
        v.propose("2026-10-05-0900-steering", S.meeting_items() + extras(), meeting=S.MEETING)

    def show(self, script=SPLIT):
        b = self.b
        b.eval("go('today')")
        b.eval(script)
        b.wait(f"!!document.querySelector('{ROW}')")

    def redraw(self, js):
        self.b.eval(f"{js}; go('intake-review')")
        self.b.pump(0.2)

    def row(self, text):
        return f"(()=>{{ const r=[...document.querySelectorAll('{ROW}')].find(t=>t.querySelector('.icttl').textContent.includes({text!r})); return r; }})()"


class Rules(Base):
    shared_server = True

    def test_routine_heading_wording_exact(self):
        self.show()
        self.assertEqual(self.b.eval("document.querySelector('tr.icsubhead.routine .icshs').textContent"), WORDING)

    def test_rvBulkOK_respects_the_invalid_flag_whatever_hold_says(self):
        b = self.b
        self.show()
        self.assertFalse(b.eval("rvBulkOK({n:1,kind:'actions',p:'ABC',flags:['invalid'],hold:'',rec:{t:'x'}})"))
        self.assertFalse(b.eval("rvBulkOK({n:1,kind:'actions',p:'ABC',flags:['invalid'],rec:{t:'x'}})"), "a row without hold keeps the invalid check too")

    def test_every_held_kind_has_a_hold_and_is_not_bulk_ok(self):
        b = self.b
        self.show()
        held = b.eval("""Object.fromEntries(REV.filter(r=>!r.done).map(r=>[r.rec.t, [r.hold, rvBulkOK(r)]]))""")
        for text, why in (("Scope creep", "new risk"), ("Approve the revised timeline", "new decision"), ("Conflicting routine", "conflict"),
                          ("Invalid routine-looking", "invalid"), ("ABC", "health change")):
            hit = [v for k, v in held.items() if text in k]
            if text == "ABC":
                hit = [v for k, v in held.items() if v[0] == "health change"]
            self.assertTrue(hit, text)
            self.assertEqual(hit[0][0], why, (text, hit))
            self.assertFalse(hit[0][1], text)
        guessed = [v for k, v in held.items() if "guessed owner" in k]
        self.assertEqual(guessed, [["", True]], "a guessed field does not make an item non-routine")

    def test_a_guessed_field_sits_in_the_routine_group_and_an_invalid_item_in_the_first(self):
        b = self.b
        self.show()
        grp = lambda t: b.eval(f"(()=>{{ const r={self.row(t)}; let p=r; while(p&&!(p.classList.contains('icsubhead'))) p=p.previousElementSibling; return p?p.dataset.irg:null; }})()")  # noqa: E731
        self.assertEqual(grp("guessed owner"), "routine")
        self.assertEqual(grp("Invalid routine-looking"), "needs")
        self.assertEqual(grp("Conflicting routine"), "needs")


class Row(Base):
    shared_server = True

    def test_one_meta_line_per_row_and_its_detail_is_the_tooltip(self):
        b = self.b
        self.show()
        res = b.eval(f"""[...document.querySelectorAll('{ROW}')].map(tr=>{{
          const w=[...tr.querySelectorAll('td.title .why, td.title .icchg')].filter(e=>!e.closest('.cfvs'));
          return [w.length, tr.querySelector('.icttl').textContent]; }})""")
        self.assertTrue(res)
        bad = [t for n, t in res if n != 1]
        self.assertEqual(bad, [], "each proposal row has exactly one meta line (#229); the emphasised line and the source share it")
        tips = b.eval(f"[...document.querySelectorAll('{ROW}')].filter(tr=>!tr.querySelector('.why[data-tip], .icchg[data-tip]')).length")
        self.assertEqual(tips, 0, "the detail (owner, priority, due) is the line's tooltip on every row")

    def hook_row(self):
        self.show()
        return self.b.eval("REV.find(r=>!r.done&&!r.hold&&r.kind==='actions').n")

    def test_hook_drafted_tag(self):
        a = self.hook_row()
        self.redraw(f"REV.find(x=>x.n=={a}).drafted='done'")
        self.assertIn("Drafted", self.b.eval(f"document.querySelector(\"{ROW}[data-irn='{a}'] .tag.drrv\").textContent"))

    def test_hook_weekend_note_buttons(self):
        a = self.hook_row()
        self.redraw(f"REV.find(x=>x.n=={a}).rec.due='2026-10-10'")                              # a Saturday
        self.assertEqual(self.b.eval(f"document.querySelectorAll(\"{ROW}[data-irn='{a}'] [data-wkrv]\").length"), 2)

    def test_hook_approve_individually_and_draft_a_response(self):
        b = self.b
        self.show()
        risk = b.eval("REV.find(r=>!r.done&&r.kind==='raid').n")
        self.redraw(f"REV.find(x=>x.n=={risk}).rec.resp=''")
        self.assertIn("approve individually", b.eval(f"document.querySelector(\"{ROW}[data-irn='{risk}']\").textContent"))
        self.assertTrue(b.eval(f"!!document.querySelector(\"{ROW}[data-irn='{risk}'] [data-drrisk]\")"), "Draft a response")

    def test_hook_no_word_draft_notice(self):
        self.hook_row()
        m = self.b.eval("REV.find(r=>!r.done&&r.kind==='draft').n")
        self.redraw(f"REV.find(x=>x.n=={m}).nodraft=true")
        self.assertIn("No Word draft was made for these minutes", self.b.eval(f"document.querySelector(\"{ROW}[data-irn='{m}']\").textContent"))

    def test_a_conflict_shows_its_block_and_keeps_the_two_choices(self):
        b = self.b
        self.show()
        c = b.eval("REV.find(r=>!r.done&&(r.flags||[]).includes('conflict')).n")
        row = f"{ROW}[data-irn='{c}']"
        self.assertTrue(b.eval(f"!!document.querySelector(\"{row} .cfvs\")"), "the before/after block")
        self.assertTrue(b.eval(f"!!document.querySelector(\"{row} [data-act=ck]\") && !!document.querySelector(\"{row} [data-act=co]\")"), "Keep current / Use this one")

    def test_open_source_opens_the_whole_file_with_no_time(self):
        b = self.b
        self.show()
        a = f"{ROW} a.srclink[data-openfile]"
        self.assertTrue(b.eval(f"!!document.querySelector(\"{a}\")"))
        self.assertEqual(b.eval(f"document.querySelector(\"{a}\").textContent"), "Open source")
        self.assertFalse(b.eval(f"document.querySelector(\"{a}\").dataset.t || document.querySelector(\"{a}\").dataset.noteline"))
        self.assertNotRegex(b.eval(f"[...document.querySelectorAll('{ROW}')].map(t=>t.querySelector('td.title').textContent).join(' ')"), r"\b\d{1,2}:\d{2}\b")

    def test_hostile_text_stays_text(self):
        b = self.b
        self.show()
        a = b.eval("REV.find(r=>!r.done&&!r.hold).n")
        self.redraw(f"(()=>{{ const r=REV.find(x=>x.n=={a}); r.rec.t='<img src=x onerror=window.__pwn=1>'; r.src='Email · From: <b>x</b> · Subject: <i>s</i> · Link: javascript:window.__pwn=2'; }})()")
        self.assertIsNone(b.eval("window.__pwn"))
        self.assertEqual(b.eval(f"document.querySelectorAll(\"{ROW}[data-irn='{a}'] img, {ROW}[data-irn='{a}'] b:not(.icttl), {ROW}[data-irn='{a}'] i\").length"), 0)
        self.assertEqual(b.eval(f"document.querySelectorAll(\"{ROW}[data-irn='{a}'] a[href^='javascript']\").length"), 0)


class Keys(Base):
    shared_server = True

    def test_arrows_and_esc_after_the_peek_was_closed_another_way(self):
        b = self.b
        self.show()
        first, second = b.eval(f"[...document.querySelectorAll('{ROW}')].map(t=>+t.dataset.irn).filter(n=>['actions','raid','decisions'].includes(REV.find(r=>r.n===n).kind)).slice(0, 2)")
        b.eval(f"document.querySelector(\"{ROW}[data-irn='{first}']\").focus()")
        b.key("ArrowDown")
        b.wait(f"document.activeElement.dataset && document.activeElement.dataset.irn=='{second}'")
        b.click(f"{ROW}[data-irn='{first}'] .icttl")
        b.wait("document.getElementById('panel').classList.contains('on')")
        b.click("#pkClose")                                                                      # closed with its own button, not Esc
        b.wait("!document.getElementById('panel').classList.contains('on')")
        b.key("Escape")
        b.wait("irOpen.value===null")                                                            # one Esc closes the meeting; it was not swallowed by a stale peek mark


class Decide(Base):
    def test_approve_routine_never_covers_the_held_kinds_even_in_a_hostile_model(self):
        b = self.b
        self.show(ALL_ROUTINE)
        b.click("[data-ira=routine]")
        b.wait("/Approved/.test(document.getElementById('snackT').textContent)", 25)
        b.pump(1)
        made = {r["description"] for r in self.v.rows("actions")}
        for t in ("Conflicting routine action", "Invalid routine-looking action"):
            self.assertNotIn(t, made)
        self.assertIn("Action with a guessed owner", made)
        self.assertFalse(any(r["description"].startswith("Scope creep") for r in self.v.rows("raid")))
        self.assertFalse(any(r["decision"].startswith("Approve the revised") for r in self.v.rows("decisions")))
        self.assertNotEqual(next(r for r in self.v.rows("actions") if r["id"] == "ABC-A-001")["status"], "Closed")
        self.assertNotEqual(next(r for r in self.v.rows("projects") if r["code"] == "ABC")["health"], "At risk")

    def test_reject_with_a_reason_then_undo(self):
        b = self.b
        self.show()
        n = b.eval("REV.find(r=>!r.done&&!r.hold).n")
        b.click(f"{ROW}[data-irn='{n}'] [data-ira=reject]")
        b.wait("!!document.getElementById('rvReason')")
        b.key("1")
        b.wait(f"!document.querySelector(\"{ROW}[data-irn='{n}']\")", 20)
        b.wait("document.getElementById('snackU') && !document.getElementById('snackU').hidden", 20)
        b.click("#snackU")
        b.wait(f"REV.some(r=>r.n=={n}&&!r.done)", 20)       # the reload brings the server's own model, so the check is on the rows


if __name__ == "__main__":
    unittest.main()
