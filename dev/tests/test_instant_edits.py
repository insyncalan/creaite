"""BL-304 (v1.9.4): changes appear at once, and only what changed is fetched again.

Run: python3 dev/tests/test_instant_edits.py   (needs Google Chrome; skipped otherwise)
A throwaway vault (test_dashboard.populate) and the real live server. Each Done-when point:
- an edit in a Work cell, the board, the peek and ⌘K is on screen within one animation frame (measured in the page, from the
  edit to the next requestAnimationFrame) and is then staged and applied in the background through the same path as before;
- a forced apply failure puts the record back with the reason and offers Retry, which saves it; a change held as a conflict
  ("changed elsewhere") is put back the same way and leaves nothing in staging;
- Undo works after the save and while it is still saving;
- two quick edits to one item are applied in order, each its own apply;
- with auto-apply off the change shows as staged;
- a change from elsewhere fetches just those items (no /api/data) and never clobbers an edit still saving; a gap in the
  live-updates stream falls back to a full reload.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

COUNT_FETCH = """(()=>{ if(window.__F) return; window.__F={data:0,records:0}; const f0=window.fetch;
  window.fetch=function(u,o){ const s=String(u); if(s.startsWith('/api/data')) __F.data++; if(s.startsWith('/api/records')) __F.records++; return f0.apply(this,arguments); }; })()"""
FRAME = "await new Promise(r=>requestAnimationFrame(()=>r()))"
TIMINGS = {}


class InstantEdits(LiveBrowserCase):
    width, height = 1640, 1000

    # ── helpers ──
    def settle(self):
        self.b.wait("PULSE.reloads===0 && !PULSE.busy && !EVS.timer && !document.querySelector('#workTbl td.editing')", 30)

    def counts(self):
        return self.b.eval("({data:__F.data,records:__F.records})")

    def row(self, id_):
        return next(r for r in self.v.rows("actions") if r["id"] == id_)

    def staged(self):
        return sorted(p.name for p in (self.v.root / "system/staging").glob("proposed-*-dashboard*.json"))

    def snack(self):
        return self.b.eval("document.getElementById('snackT').textContent")

    def wait_snack(self, pattern, timeout=30):
        try:
            self.b.wait(f"new RegExp({pattern!r}).test(document.getElementById('snackT').textContent)", timeout)
        except TimeoutError:
            self.fail(f"no {pattern!r} message; the page says {self.snack()!r}")

    def open_list(self, cols=("pr",)):
        b = self.b
        b.eval("WT='actions'; go('work')")
        b.eval("HTMLSelectElement.prototype.showPicker=function(){}")
        b.wait("document.querySelector('#workTbl tr[data-row]')")
        b.click('#wlay [data-lay="list"]')
        b.eval("setOf('st').clear(); workChanged()")
        b.eval("COLVIS[WT]=[...new Set([...COLVIS[WT]," + ",".join(repr(c) for c in cols) + "])]; renderWork()")
        b.wait("document.querySelector('#workTbl tr[data-row=\"ABC-A-002\"] td[data-f=\"pr\"].ce .cebtn')")
        b.eval(COUNT_FETCH)
        self.settle()
        return b

    def cell_edit(self, id_, f, value):
        """Choose a value in a Work cell; returns what the page showed one frame later and how long that took (ms)."""
        cell = f'#workTbl tr[data-row="{id_}"] td[data-f="{f}"]'
        return self.b.eval(f"""(async()=>{{ ceOpen(document.querySelector({cell!r})); const s=document.querySelector({(cell + ' select[data-cf]')!r});
          s.value={value!r}; const t0=performance.now(); s.dispatchEvent(new Event('change',{{bubbles:true}})); {FRAME};
          const td=document.querySelector({cell!r}), tr=td&&td.closest('tr');
          return {{ms:performance.now()-t0, text:td?td.textContent:'', rec:REC('actions',{id_!r}).{f}, saving:!!(tr&&tr.querySelector('.pkdot.saving'))}}; }})()""")

    # ── on screen within a frame ──
    def test_a_work_cell_shows_within_a_frame_then_applies_with_no_full_reload(self):
        b = self.open_list()
        before = len(self.v.rows("applies"))
        r = self.cell_edit("ABC-A-002", "pr", "Urgent")
        TIMINGS["Work cell"] = r["ms"]
        self.assertIn("Urgent", r["text"])
        self.assertEqual(r["rec"], "Urgent")
        self.assertTrue(r["saving"], "the row carries the saving dot while it saves")
        self.assertLess(r["ms"], 500)   # one frame; generous for a loaded runner (the value check is the frame)
        self.wait_snack("— saved")
        self.settle()
        self.assertEqual(self.row("ABC-A-002")["priority"], "Urgent")
        self.assertEqual(len(self.v.rows("applies")), before + 1)
        self.assertFalse(b.eval("!!document.querySelector('#workTbl tr[data-row=\"ABC-A-002\"] .pkdot')"), "the mark clears")
        c = self.counts()
        self.assertEqual(c["data"], 0, "no full /api/data reload for a single change")
        self.assertGreaterEqual(c["records"], 1)
        self.assertEqual(self.staged(), [])

    def test_the_board_shows_the_move_within_a_frame(self):
        b = self.b
        b.eval("go('work')")
        b.wait("document.querySelector('#workTbl tbody tr, #workBoard .bcol')")
        b.click('#wlay [data-lay="board"]')
        b.wait("!document.getElementById('workBoard').hidden && document.querySelector('#workBoard .bcard[data-row=\"ABC-A-002\"]')")
        b.eval(COUNT_FETCH)
        self.settle()
        col = "(()=>{ const c=document.querySelector('#workBoard .bcard[data-row=\"ABC-A-002\"]'); return c?c.closest('.bcol').dataset.col:null; })()"
        was = b.eval(col)
        r = b.eval(f"""(async()=>{{ const t0=performance.now(); boardMove('actions','ABC-A-002',{{st:'Delayed'}},'ABC-A-002 moved'); {FRAME};
          return {{ms:performance.now()-t0, col:{col}, rec:REC('actions','ABC-A-002').st}}; }})()""")
        TIMINGS["board"] = r["ms"]
        self.assertEqual(r["rec"], "Delayed")
        self.assertLess(r["ms"], 500)   # one frame; generous for a loaded runner (the value check is the frame)
        self.wait_snack("— saved")
        self.settle()
        self.assertEqual(self.row("ABC-A-002")["status"], "Delayed")
        self.assertEqual(b.eval(col), r["col"], "the card was already where the save left it")
        if was is not None and r["col"] is not None:
            self.assertNotEqual(was, r["col"])
        self.assertEqual(self.counts()["data"], 0)

    def test_the_peek_shows_the_change_within_a_frame_and_stages_it(self):
        b = self.open_list()
        b.eval("openRecord('actions','ABC-A-002')")
        b.wait("CUR&&CUR.id==='ABC-A-002'&&document.getElementById('panel').classList.contains('peek')")
        self.settle()
        b.click('#panel [data-pkp="st"]')
        b.wait("document.querySelector('.pkpop')")
        r = b.eval(f"""(async()=>{{ const o=[...document.querySelectorAll('.pkpop .pkopt')].find(o=>o.querySelector('span').firstChild.textContent==='Delayed');
          const t0=performance.now(); o.click(); {FRAME};
          const chip=document.querySelector('#panel [data-pkp="st"]'), td=document.querySelector('#workTbl tr[data-row="ABC-A-002"] td[data-f="st"]');
          return {{ms:performance.now()-t0, chip:chip?chip.textContent:'', cell:td?td.textContent:'', rec:REC('actions','ABC-A-002').st}}; }})()""")
        TIMINGS["peek"] = r["ms"]
        self.assertEqual(r["rec"], "Delayed")
        self.assertIn("Delayed", r["chip"])
        self.assertIn("Delayed", r["cell"])
        self.assertLess(r["ms"], 500)   # one frame; generous for a loaded runner (the value check is the frame)
        b.wait("PKS.length===1", 15)                             # staged in the background (the peek never applies on the spot)
        self.assertEqual(len(self.staged()), 1)
        self.assertEqual(self.row("ABC-A-002")["status"], "Open")
        b.wait("!!document.querySelector('#workTbl tr[data-row=\"ABC-A-002\"] .pkdot[data-st=\"staged\"]')")

    def test_cmd_k_shows_the_change_within_a_frame(self):
        b = self.open_list()
        r = b.eval(f"""(async()=>{{ CKPICK={{}}; const c=ckParse('make ABC-A-002 urgent'); const t0=performance.now(); ckStage(c); {FRAME};
          const td=document.querySelector('#workTbl tr[data-row="ABC-A-002"] td[data-f="pr"]');
          return {{ms:performance.now()-t0, cell:td?td.textContent:'', rec:REC('actions','ABC-A-002').pr}}; }})()""")
        TIMINGS["⌘K"] = r["ms"]
        self.assertEqual(r["rec"], "Urgent")
        self.assertIn("Urgent", r["cell"])
        self.assertLess(r["ms"], 500)   # one frame; generous for a loaded runner (the value check is the frame)
        self.wait_snack("^Saved")
        self.assertEqual(len(self.staged()), 1)

    # ── failure, Retry and Undo ──
    def test_a_forced_apply_failure_puts_it_back_with_the_reason_and_retry_saves_it(self):
        b = self.open_list()
        b.eval("""window.__api0=api; window.api=async(p,body)=>p==='/api/apply'?{ok:false,message:'Forced failure for the test'}:__api0(p,body)""")
        r = self.cell_edit("ABC-A-002", "pr", "Urgent")
        self.assertEqual(r["rec"], "Urgent")                            # shown at once
        self.wait_snack("^Not saved: Forced failure for the test")
        self.settle()
        self.assertEqual(b.eval("REC('actions','ABC-A-002').pr"), "Medium")   # put back
        self.assertNotIn("Urgent", b.eval("document.querySelector('#workTbl tr[data-row=\"ABC-A-002\"] td[data-f=\"pr\"]').textContent"))
        self.assertEqual(b.eval("document.getElementById('snackU').textContent"), "Retry")
        self.assertEqual(self.staged(), [], "the failed proposal isn't left in staging")
        self.assertEqual(self.row("ABC-A-002")["priority"], "Medium")
        b.eval("window.api=__api0")
        b.eval("document.getElementById('snackU').click()")
        b.wait("REC('actions','ABC-A-002').pr==='Urgent'", 2)              # Retry: on screen again at once
        self.wait_snack("— saved")
        self.settle()
        self.assertEqual(self.row("ABC-A-002")["priority"], "Urgent")
        self.assertEqual(self.counts()["data"], 0)

    def test_a_change_made_elsewhere_is_put_back_and_reloaded(self):
        b = self.open_list()
        b.eval("REC('actions','ABC-A-002').updated_at='2001-01-01 00:00:00'")   # as if another window changed it since
        self.cell_edit("ABC-A-002", "pr", "Urgent")
        self.wait_snack("^Not saved: ABC-A-002 changed elsewhere; reloaded it")
        self.settle()
        self.assertEqual(b.eval("REC('actions','ABC-A-002').pr"), "Medium")
        self.assertEqual(b.eval("REC('actions','ABC-A-002').updated_at"), self.row("ABC-A-002")["updated_at"])   # reloaded
        self.assertEqual(self.row("ABC-A-002")["priority"], "Medium")
        self.assertEqual(self.staged(), [], "not left behind as a conflict")

    def test_undo_after_the_save_and_while_it_is_saving(self):
        b = self.open_list()
        self.cell_edit("ABC-A-002", "pr", "Urgent")
        self.wait_snack("— saved")
        self.settle()
        b.click("#snackU")
        self.wait_snack("^Undone")
        self.settle()
        self.assertEqual(self.row("ABC-A-002")["priority"], "Medium")
        self.assertEqual(b.eval("REC('actions','ABC-A-002').pr"), "Medium")
        # while it is still saving: the apply is held back a second; Undo puts it back at once and nothing stays applied
        b.eval("""window.__api0=api; window.api=async(p,body)=>{ if(p==='/api/apply') await new Promise(r=>setTimeout(r,1000)); return __api0(p,body); }""")
        self.cell_edit("ABC-A-002", "pr", "Low")
        self.assertIn("saving", self.snack())
        b.click("#snackU")
        self.assertEqual(b.eval("REC('actions','ABC-A-002').pr"), "Medium")
        b.eval("(async()=>{ await savesSettled(); return true; })()")
        self.settle()
        b.eval("window.api=__api0")
        self.assertEqual(self.row("ABC-A-002")["priority"], "Medium")
        self.assertEqual(b.eval("REC('actions','ABC-A-002').pr"), "Medium")
        # as with any Undo of an apply (tracker.py undo), what was applied goes back to Review as pending: nothing approved is left
        for name in self.staged():
            items = json.loads((self.v.root / "system/staging" / name).read_text())["items"]
            self.assertTrue(all(i.get("decision") == "pending" for i in items), name)

    # ── order and concurrency ──
    def test_two_quick_edits_to_one_item_apply_in_order(self):
        b = self.open_list()
        before = len(self.v.rows("applies"))
        shown = b.eval(f"""(async()=>{{ boardMove('actions','ABC-A-002',{{pr:'Urgent'}},'one'); boardMove('actions','ABC-A-002',{{pr:'Low'}},'two'); {FRAME};
          return REC('actions','ABC-A-002').pr; }})()""")
        self.assertEqual(shown, "Low")
        b.eval("(async()=>{ await savesSettled(); return true; })()")
        self.settle()
        self.assertEqual(self.row("ABC-A-002")["priority"], "Low")
        applies = self.v.rows("applies")
        self.assertEqual(len(applies), before + 2, "each its own apply, in order")
        log = [r for r in self.v.rows("change_log") if r["item_id"] == "ABC-A-002" and r["field"] == "priority"]
        self.assertEqual([r["new_value"] for r in log[-2:]], ["Urgent", "Low"])
        self.assertEqual(self.staged(), [], "no conflict held")
        self.assertEqual(b.eval("REC('actions','ABC-A-002').pr"), "Low")

    def test_a_change_from_elsewhere_fetches_only_that_item_and_never_clobbers_one_in_flight(self):
        b = self.open_list()
        b.eval("""window.__api0=api; window.api=async(p,body)=>{ if(p==='/api/apply') await new Promise(r=>setTimeout(r,1500)); return __api0(p,body); }""")
        self.cell_edit("ABC-A-002", "pr", "Urgent")                    # still saving for a while
        # a live update for the same item arrives meanwhile: the store takes the server's row, the edit in flight stays on top
        self.assertTrue(b.eval("(async()=>await refreshRecords(['ABC-A-002']))()"))
        self.assertEqual(b.eval("REC('actions','ABC-A-002').pr"), "Urgent")
        b.eval("(async()=>{ await savesSettled(); return true; })()")
        self.settle()
        b.eval("window.api=__api0")
        self.assertEqual(self.row("ABC-A-002")["priority"], "Urgent")
        # an apply from another source (cx-edit): the stream names the item; the page fetches just it
        c0 = self.counts()
        other = b.eval("A.find(x=>x.p==='DEF').id")
        self.v.propose("elsewhere", [{"n": 1, "op": "update", "table": "actions", "id": other,
                                      "changes": {"owner": "Sara Example"}, "decision": "approved"}])
        self.v.run("apply")
        b.wait(f"REC('actions',{other!r}).o==='Sara Example'", 20)
        self.settle()
        c1 = self.counts()
        self.assertEqual(c1["data"], c0["data"], "no /api/data for a change from elsewhere")
        self.assertGreater(c1["records"], c0["records"])

    def test_a_gap_in_the_stream_reloads_everything(self):
        b = self.open_list()
        b.eval("PULSE.v='before the gap'; evOn({type:'changed',seq:999,parts:['tracker','review'],v:'gap'})")   # no IDs: what a gap sends
        b.wait("__F.data>=1", 20)
        self.settle()
        n = self.counts()["data"]
        b.eval("evOn({type:'changed',seq:1000,parts:['tracker'],ids:{actions:['ABC-A-001']},v:'ids'})")
        b.wait("__F.records>=1", 20)
        self.settle()
        self.assertEqual(self.counts()["data"], n)

    # ── auto-apply off ──
    def test_with_auto_apply_off_it_shows_as_staged(self):
        b = self.open_list()
        b.eval("S.autoApply=false")
        r = self.cell_edit("ABC-A-002", "pr", "Urgent")
        self.assertEqual(r["rec"], "Urgent")
        self.wait_snack("press Save")
        b.wait("!!document.querySelector('#workTbl tr[data-row=\"ABC-A-002\"] .pkdot[data-st=\"staged\"]')")
        self.assertEqual(len(self.staged()), 1)
        self.assertEqual(self.row("ABC-A-002")["priority"], "Medium")

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        if TIMINGS:
            print("\nBL-304 timings (edit to the next frame, ms): " + json.dumps({k: round(v, 1) for k, v in TIMINGS.items()}), file=sys.stderr)


if __name__ == "__main__":
    unittest.main()
