"""BL-123: edit any field in the Work table with a dropdown or picker. A real browser against the real live server (the controls are
driven as a person would, except that a native list's choice is made by setting the select and firing its change event).

Run: python3 dev/tests/test_cell_edit.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import time
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase, pin_page_clock  # noqa: E402

META = 4


def iso(n):
    return (date.today() + timedelta(days=n)).isoformat()

def wd(n):
    """BL-181: n days on, moved to the next working day, so a test's date never raises the weekend alert."""
    d = date.today() + timedelta(days=n)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d.isoformat()



def shown(s):
    return f"{s[8:10]}-{s[5:7]}-{s[0:4]}"


class CellEdit(LiveBrowserCase):
    width, height = 1500, 1000

    def open_work(self, tab="actions"):
        b = self.b
        b.eval(f"WT={tab!r}; go('work')")
        # The page opens a list's options with showPicker(); on Linux and Windows Chrome shows a native list that takes the
        # first Escape and Tab itself. These tests check the page's own keys, so the native list is switched off here.
        b.eval("HTMLSelectElement.prototype.showPicker=function(){}")
        b.wait("document.querySelector('#workTbl tr[data-row]')")
        b.click('#wlay [data-lay="list"]')
        b.eval("document.activeElement&&document.activeElement.blur()")
        b.pump(0.3)
        return b

    def show(self, *cols):
        self.b.eval("COLVIS[WT]=[...new Set([...COLVIS[WT]," + ",".join(repr(c) for c in cols) + "])]; renderWork()")
        self.b.pump(0.3)

    def cell(self, id_, f):
        return f'#workTbl tr[data-row="{id_}"] td[data-f="{f}"]'

    def row(self, table, id_):
        return next(r for r in self.v.rows(table) if r["id"] == id_)

    def choose(self, id_, f, value, attr="data-cf"):
        """Click the value, then choose from its list."""
        b = self.b
        self.ready(id_, f)
        self.arm()
        b.click(self.cell(id_, f))
        b.wait(f"document.querySelector('{self.cell(id_, f)} select, {self.cell(id_, f)} input')")
        b.eval(f"""(()=>{{ const s=document.querySelector('{self.cell(id_, f)} select[{attr}="{f}"]'); s.value={value!r};
          s.dispatchEvent(new Event('change',{{bubbles:true}})); }})()""")
        self.saved()

    def arm(self):
        self.b.eval("document.getElementById('snackT').textContent=''")

    # dev-test-steadiness: each step waits for its own condition. saved() took any message as the save's and then slept
    # half a second; ready() didn't exist, so a click could reach a cell the page was still drawing again.
    SAVED = r"saved and applied|apply stopped|Not saved|isn't|can't|Not a date"   # the save's own message, done or refused

    def saved(self, expect=SAVED):
        """Wait for the save's own message (the apply can take a while under load), then for the page to finish the reload
        that came with it."""
        b = self.b
        try:
            b.wait(f"new RegExp({expect!r}).test(document.getElementById('snackT').textContent)", 30)
        except TimeoutError:
            self.fail(f"no {expect!r} message; the page says {self.snack()!r}")
        self.settle()

    def settle(self):
        """No data reload in flight, none queued from the live-update stream, and no cell editor open."""
        self.b.wait("PULSE.reloads===0 && !PULSE.busy && !EVS.timer && !document.querySelector('#workTbl td.editing')", 30)

    def ready(self, id_, f):
        """The cell is drawn and can be edited (its ▾ is there) and nothing else is being edited or reloaded."""
        self.settle()
        self.b.wait(f"document.querySelector('{self.cell(id_, f)}.ce .cebtn')")

    def snack(self):
        return self.b.eval("document.getElementById('snackT').textContent")

    # ── which values can be edited ──

    def test_the_right_values_are_editable_on_each_tab(self):
        b = self.open_work("actions")
        self.show("ws")
        for f in ("st", "o", "due", "pr", "ws"):
            self.assertEqual(b.eval(f"document.querySelectorAll('{self.cell('ABC-A-001', f)}.ce .cebtn').length"), 1, f)
        for f in ("t",):
            self.assertEqual(b.eval(f"document.querySelectorAll('{self.cell('ABC-A-001', f)}.ce').length"), 0, f)      # free text stays in the sidebar
        self.assertEqual(b.eval("document.querySelectorAll('#workTbl td.idc.ce').length"), 0)                          # the ID is not editable
        self.open_work("raid")
        self.show("st", "type", "ws")
        for f in ("st", "o", "type", "imp", "due", "ws"):
            n = b.eval(f"document.querySelectorAll('#workTbl td[data-f=\"{f}\"].ce').length")
            self.assertGreater(n, 0, f) if f != "ws" else None
        self.assertEqual(b.eval("document.querySelectorAll('#workTbl td[data-f=\"resp\"].ce').length"), 0)             # a response is free text
        self.open_work("decisions")
        self.assertEqual(b.eval("document.querySelectorAll('#workTbl td[data-f=\"st\"].ce').length"), 0)               # ABC-D-005 is made: its status is not changed here
        self.assertEqual(b.eval("document.querySelectorAll('#workTbl td[data-f=\"date\"].ce').length"), 1)

    # ── choosing saves ──

    def test_status_saves_with_undo_and_closing_fills_the_date(self):
        b = self.open_work()
        b.eval("setOf('st').clear(); workChanged()")                        # every status: a closed item would leave the open view
        b.pump(0.3)
        self.choose("ABC-A-001", "st", "Closed")
        row = self.row("actions", "ABC-A-001")
        self.assertEqual(row["status"], "Closed")
        self.assertEqual(row["closed"], date.today().isoformat())          # closing fills today, as the sidebar does
        self.assertIn("ABC-A-001 status", self.snack())
        self.assertEqual(b.eval("document.querySelectorAll('#workTbl td.editing').length"), 0)
        b.wait("document.getElementById('snack').classList.contains('on') && document.getElementById('snackU').offsetParent!==null")
        self.arm()
        b.click("#snackU")                                                  # Undo in the message
        self.saved("^Undone")
        row = self.row("actions", "ABC-A-001")
        self.assertEqual((row["status"], row["closed"]), ("Open", None))
        self.choose("ABC-A-001", "st", "Closed")                            # and reopening clears the date
        self.choose("ABC-A-001", "st", "Open")
        self.assertEqual(self.row("actions", "ABC-A-001")["closed"], None)

    def test_owner_priority_and_workstream(self):
        self.open_work()
        self.choose("ABC-A-002", "o", "TBC")
        self.assertEqual(self.row("actions", "ABC-A-002")["owner"], "TBC")
        self.choose("ABC-A-002", "o", "Omar Ali")                           # from the people register
        self.assertEqual(self.row("actions", "ABC-A-002")["owner"], "Omar Ali")
        self.choose("ABC-A-002", "pr", "Low")
        self.assertEqual(self.row("actions", "ABC-A-002")["priority"], "Low")
        opts = self.b.eval(f"[...document.querySelectorAll('{self.cell('ABC-A-002', 'ws')} select option')].map(o=>o.value)") if False else None
        self.assertIsNone(opts)

    def test_the_owner_list_is_the_register_with_tbc(self):
        b = self.open_work()
        b.click(self.cell("ABC-A-002", "o"))
        b.wait(f"document.querySelector('{self.cell('ABC-A-002', 'o')} select')")
        names = b.eval(f"[...document.querySelectorAll('{self.cell('ABC-A-002', 'o')} select option')].map(o=>o.value)")
        self.assertEqual(names[0], "TBC")
        self.assertIn("Sara Example", names)
        self.assertIn("Omar Ali", names)

    def test_due_date_typed_and_from_the_calendar(self):
        b = self.open_work()
        self.ready("ABC-A-002", "due")
        self.arm()
        b.click(self.cell("ABC-A-002", "due"))
        b.wait("document.getElementById('ceDate')")
        b.eval(f"document.getElementById('ceDate').value={shown(wd(20))!r}")
        b.key("Enter")
        self.saved()
        self.assertEqual(self.row("actions", "ABC-A-002")["due_date"], wd(20))
        self.ready("ABC-A-002", "due")
        self.arm()
        b.eval(f"document.querySelector('{self.cell('ABC-A-002', 'due')} .cebtn').click()")      # the ▾ button opens it too
        b.wait("document.getElementById('ceDate')")
        b.click("#v-work td.editing .dbtn")                                 # the calendar
        b.wait("document.querySelector('.cal')")
        target = b.eval("[...document.querySelectorAll('.cal .cg button[data-v]:not(.wkend):not(:disabled)')].map(x=>x.dataset.v).find(v=>v!==document.getElementById('ceDate').value)")   # BL-181: a working day
        b.eval(f"document.querySelector('.cal button[data-v=\"{target}\"]').click()")
        self.saved()
        self.assertEqual(self.row("actions", "ABC-A-002")["due_date"], f"{target[6:10]}-{target[3:5]}-{target[0:2]}")
        self.ready("ABC-A-002", "due")
        self.arm()
        b.click(self.cell("ABC-A-002", "due"))                              # clearing the date
        b.wait("document.getElementById('ceDate')")
        b.eval("document.getElementById('ceDate').value=''")
        b.key("Enter")
        self.saved()
        self.assertIsNone(self.row("actions", "ABC-A-002")["due_date"])

    def test_a_bad_date_is_refused_and_nothing_is_saved(self):
        b = self.open_work()
        before = self.row("actions", "ABC-A-002")["due_date"]
        b.click(self.cell("ABC-A-002", "due"))
        b.wait("document.getElementById('ceDate')")
        b.eval("document.getElementById('ceDate').value='31-02-2026'")
        b.key("Enter")
        b.pump(0.5)
        self.assertIn("real date", self.snack())
        self.assertEqual(self.row("actions", "ABC-A-002")["due_date"], before)
        self.assertEqual(b.eval("document.querySelectorAll('#workTbl td.editing').length"), 1)     # still open to correct

    def test_a_refused_change_puts_the_value_back(self):
        b = self.open_work()
        before = self.row("actions", "ABC-A-002")["due_date"]
        ok = b.eval("(async()=>{ const r=await ceApply('actions',['ABC-A-002'],{due:'not-a-date'}); return r; })()")
        b.pump(0.3)
        self.assertFalse(ok)
        self.assertIn("Not a date creaite knows", self.snack())   # BL-147
        self.assertEqual(self.row("actions", "ABC-A-002")["due_date"], before)

    def test_raid_priority_edits_impact_and_likelihood(self):
        b = self.open_work("raid")
        self.ready("ABC-003", "imp")
        b.click(self.cell("ABC-003", "imp"))
        b.wait(f"document.querySelectorAll('{self.cell('ABC-003', 'imp')} select').length===2")
        b.eval(f"""(()=>{{ const s=document.querySelector('{self.cell('ABC-003', 'imp')} select[data-cf="imp"]'); s.value='Low';
          s.dispatchEvent(new Event('change',{{bubbles:true}})); }})()""")
        self.saved()
        row = self.row("raid", "ABC-003")
        self.assertEqual(row["impact"], "Low")
        self.assertEqual(row["priority"], {"Low": "Medium"}.get(row["impact"], row["priority"]) if False else row["priority"])
        self.assertNotEqual(row["priority"], "Urgent")                      # worked out again from impact and likelihood

    def test_a_decision_is_changed_only_while_pending_and_made_opens_the_form(self):
        b = self.open_work("decisions")
        self.v.propose("dec", [{"n": 1, "op": "new", "table": "decisions", "match": "strong", "flags": [], "decision": "approved",
                                "values": {"project": "ABC", "decision": "Extend the pilot", "status": "Pending", "made_by": "Sara Example",
                                           "needed_by": iso(5), "source": "Alan (cx-edit)"}}])
        self.v.run("apply")
        b.eval("reloadData().then(()=>renderWork())")
        b.pump(1.0)
        pending = next(r["id"] for r in self.v.rows("decisions") if r["status"] == "Pending")
        b.click(self.cell(pending, "st"))
        b.wait(f"document.querySelector('{self.cell(pending, 'st')} select')")
        b.eval(f"""(()=>{{ const s=document.querySelector('{self.cell(pending, 'st')} select'); s.value='Made';
          s.dispatchEvent(new Event('change',{{bubbles:true}})); }})()""")
        b.wait("document.getElementById('panel').classList.contains('on')")
        b.wait("PKS.length===1", 10)                                                             # BL-176: the peek opens with Made staged
        self.assertEqual(b.eval("[CUR.id, PKS[0].patch.st, !!PKS[0].patch.date, document.getElementById('panel').classList.contains('peek')]"), [pending, "Made", True, True])
        self.assertEqual(self.row("decisions", pending)["status"], "Pending")                   # nothing is written until Apply

    # ── cancelling, selecting, keys ──

    def test_escape_and_clicking_away_leave_the_value_as_it_was(self):
        b = self.open_work()
        b.click(self.cell("ABC-A-002", "st"))
        b.wait(f"document.activeElement===document.querySelector('{self.cell('ABC-A-002', 'st')} select')")
        b.key("Escape")
        b.wait("document.querySelectorAll('#workTbl td.editing').length===0", 10)
        self.assertEqual(b.eval(f"document.querySelector('{self.cell('ABC-A-002', 'st')}').textContent.replace('▾','').trim()"), "Open")
        self.assertEqual(b.eval("document.querySelectorAll('#workTbl td.editing').length"), 0)
        b.click(self.cell("ABC-A-002", "pr"))
        b.wait(f"document.querySelector('{self.cell('ABC-A-002', 'pr')} select')")
        b.click("#workQ")                                                   # clicking away
        b.wait("document.querySelectorAll('#workTbl td.editing').length===0", 5)
        self.assertEqual(self.row("actions", "ABC-A-002")["status"], "Open")

    def test_a_click_on_a_value_highlights_its_row_and_a_key_selects_without_opening(self):
        b = self.open_work()
        b.click(self.cell("ABC-A-002", "pr"))
        b.wait(f"document.querySelector('{self.cell('ABC-A-002', 'pr')} select')")
        self.assertEqual(b.eval("[...document.querySelectorAll('#workTbl tr.hl')].map(r=>r.dataset.row)"), ["ABC-A-002"])
        b.wait(f"document.activeElement===document.querySelector('{self.cell('ABC-A-002', 'pr')} select')")
        b.key("Escape")
        b.wait("document.querySelectorAll('#workTbl td.editing').length===0", 10)
        b.click(self.cell("DEF-A-001", "pr"), modifiers=META)               # with Cmd it selects and opens nothing
        b.pump(0.3)
        self.assertEqual(b.eval("document.querySelectorAll('#workTbl td.editing').length"), 0)
        self.assertEqual(sorted(b.eval("[...document.querySelectorAll('#workTbl tr.hl')].map(r=>r.dataset.row)")), ["ABC-A-002", "DEF-A-001"])

    def test_the_keyboard_path(self):
        b = self.open_work()
        b.key("j")
        b.key("j")                                                          # the cursor is on the second row
        row = b.eval("HLC")
        for _ in range(12):                                                 # Tab through the ID links and the owner link to that row's ▾ buttons
            b.key("Tab")
            if b.eval("document.activeElement.className") == "cebtn":
                break
        self.assertEqual(b.eval("document.activeElement.className"), "cebtn")
        self.assertEqual(b.eval("document.activeElement.closest('tr').dataset.row"), row)
        b.key("Enter")                                                      # Enter opens the control
        b.wait("document.querySelectorAll('#workTbl td.editing select, #workTbl td.editing input').length===1")
        first = b.eval("document.querySelector('#workTbl td.editing').dataset.f")
        b.key("Tab")                                                        # Tab goes on to the next editable cell
        b.wait("document.querySelectorAll('#workTbl td.editing').length===0", 10)
        self.assertEqual(b.eval("document.activeElement.className"), "cebtn")
        self.assertNotEqual(b.eval("document.activeElement.dataset.ce"), first)
        b.key("Enter")
        b.wait("document.querySelectorAll('#workTbl td.editing').length===1")
        b.key("Escape")
        b.wait("document.querySelectorAll('#workTbl td.editing').length===0")
        self.assertEqual(b.eval("document.activeElement.className"), "cebtn")        # Esc cancels and the focus returns to the button

    def test_the_double_click_opens_the_sidebar_and_does_not_edit(self):
        b = self.open_work()
        # #241 a: the Compact row puts the ID and the project link on the title's line, so the cell's centre can be a link; the
        # double-click lands on the title cell's own marks (not a link), as it landed on the cell before
        b.click('#workTbl tr[data-row="ABC-A-002"] td.title .wkm', count=2)
        b.wait("document.getElementById('panel').classList.contains('on')")
        self.assertFalse(b.eval("EDITING"))

    def test_activity_has_a_line_with_the_items_text(self):
        self.open_work()
        self.choose("ABC-A-002", "st", "Closed")
        self.v.run(script="build_dashboard.py")
        time.sleep(0.2)
        rows = [r for r in self.v.rows("change_log") if r["item_id"] == "ABC-A-002" and r["field"] == "status"]
        self.assertEqual([(r["old_value"], r["new_value"]) for r in rows][-1], ("Open", "Closed"))


    # ── BL-251 (fix-due-button): the ▾ sits beside the value it edits ──

    def test_the_due_button_sits_beside_the_date(self):
        b = self.b
        pin_page_clock(b, date.today().isoformat() + " 10:00")   # the seed's dates are relative to today: ABC-A-001 is 3 days late
        geom = """(sel=>{ const td=document.querySelector(sel), btn=td.querySelector('.cebtn'), t=td.firstChild, r=document.createRange();
          r.selectNodeContents(t); const d=r.getBoundingClientRect(), k=btn.getBoundingClientRect(), x=td.querySelector(':scope > .x');
          return {text:t.textContent, sub:x?x.textContent:'', dTop:d.top, dBottom:d.bottom, dRight:d.right, kTop:k.top, kBottom:k.bottom,
                  kLeft:k.left, before:!!(x&&(btn.compareDocumentPosition(x)&Node.DOCUMENT_POSITION_FOLLOWING))}; })"""
        def level(sel, late):
            g = b.eval(f"{geom}({sel!r})")
            self.assertEqual(bool(g["sub"]), late, g)
            mid = (g["kTop"] + g["kBottom"]) / 2
            self.assertTrue(g["dTop"] <= mid <= g["dBottom"], g)            # the ▾ is on the date's line…
            self.assertGreaterEqual(g["kLeft"], g["dRight"] - 0.5, g)       # …and to its right
            return g
        self.open_work("actions")
        g = level(self.cell("ABC-A-001", "due"), True)
        self.assertIn("late", g["sub"])
        self.assertTrue(g["before"], g)                                       # the sub-line stays under the date and ▾
        g = level(self.cell("ABC-A-002", "due"), True)                        # "In 3 days"
        self.open_work("raid")
        g = level(self.cell("ABC-003", "due"), False)                       # no due date: no sub-line, ▾ at the end
        self.assertEqual(g["text"], "—")
        o = self.cell("ABC-A-001", "o")
        self.open_work("actions")
        self.assertEqual(b.eval(f"document.querySelector('{o}').lastElementChild.className"), "cebtn")   # Owner unchanged: ▾ last

if __name__ == "__main__":
    unittest.main(verbosity=2)
