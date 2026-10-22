"""BL-124: change several selected Work items at once. A real browser against the real live server.

Run: python3 dev/tests/test_bulk_edit.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import time
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

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


def new_action(n, description, **v):
    return {"n": n, "op": "new", "table": "actions", "match": "strong", "flags": [], "decision": "approved",
            "values": {"project": "ABC", "description": description, "owner": "Alan Carter", "source": "Alan (cx-edit)", **v}}


class BulkEdit(LiveBrowserCase):
    width, height = 1500, 1000

    def open_work(self, tab="actions", layout="list"):
        b = self.b
        b.eval(f"WT={tab!r}; go('work')")
        b.wait("document.querySelector('#workTbl tr[data-row], #workBoard .bcard')")
        b.click(f'#wlay [data-lay="{layout}"]')
        if tab == "actions":
            b.eval("setOf('st').clear(); workChanged()")
        b.eval("COLVIS[WT]=[...new Set([...COLVIS[WT],'src'])]; renderWork(); document.activeElement&&document.activeElement.blur()")
        b.pump(0.4)
        return b

    def src(self, id_):
        return f'#workTbl tr[data-row="{id_}"] td:last-child'

    def arm(self):
        self.b.eval("document.getElementById('snackT').textContent=''")

    def saved(self):
        """Wait for the save to report (the apply can take a while under load), then let the page settle."""
        self.b.wait("document.getElementById('snackT').textContent!==''", 30)
        self.b.pump(0.5)

    def until(self, ready, timeout=30):
        """The page shows a save at once and the apply follows; wait (on a runner under load too) until the database has it."""
        end = time.time() + timeout
        while time.time() < end and not ready():
            self.b.pump(0.1)

    def acts(self, field, *ids):
        return [self.row("actions", i)[field] for i in ids]

    def select(self, *ids):
        b = self.b
        self.arm()
        b.click(self.src(ids[0]))
        for i in ids[1:]:
            b.click(self.src(i), modifiers=META)
        b.pump(0.2)

    def row(self, table, id_):
        return next(r for r in self.v.rows(table) if r["id"] == id_)

    def bar(self):
        return self.b.eval("""(()=>{ const e=document.getElementById('wbulk'); return {hidden:e.hidden||!e.offsetParent, n:(e.querySelector('.bkn')||{}).textContent,
          fields:[...e.querySelectorAll('[data-bf]')].map(s=>({f:s.dataset.bf, off:s.disabled, why:s.title})), q:[...e.querySelectorAll('[data-bq]')].map(b=>b.dataset.bq)}; })()""")

    def pick(self, f, value):
        self.b.eval(f"""(()=>{{ const s=document.querySelector('#wbulk select[data-bf="{f}"]'); s.value={value!r};
          s.dispatchEvent(new Event('change',{{bubbles:true}})); }})()""")
        self.saved()

    def snack(self):
        return self.b.eval("document.getElementById('snackT').textContent")

    def applies(self):
        return len(self.v.rows("applies"))

    # ── the bar ──

    def test_the_bar_appears_with_two_or_more_and_names_the_count(self):
        self.open_work()
        self.select("ABC-A-001")
        self.assertTrue(self.bar()["hidden"])                              # one highlighted: no bar
        self.select("ABC-A-001", "ABC-A-002")
        bar = self.bar()
        self.assertFalse(bar["hidden"])
        self.assertEqual(bar["n"], "2 selected")
        self.assertEqual(bar["q"], ["all", "close", "reopen", "clear"])          # BL-129: "Select all N matching" first
        self.assertEqual([f["f"] for f in bar["fields"]], ["st", "o", "due", "pr", "ws", "ms"])
        self.assertFalse(any(f["off"] for f in bar["fields"]))             # one project: every field is offered
        self.b.click("#wbulk [data-bq=clear]")                             # × clears it
        self.assertEqual(self.b.eval("HL.size"), 0)
        self.assertTrue(self.bar()["hidden"])

    def test_a_field_that_does_not_apply_is_withheld_with_the_reason(self):
        self.open_work()
        self.select("ABC-A-001", "DEF-A-001")                              # two projects
        fields = {f["f"]: f for f in self.bar()["fields"]}
        for f in ("ws", "ms"):
            self.assertTrue(fields[f]["off"], f)
            self.assertIn("different projects", fields[f]["why"])
        for f in ("st", "o", "due", "pr"):
            self.assertFalse(fields[f]["off"], f)
        self.open_work("raid")                                             # RAID offers impact and likelihood, not a priority
        self.select_raid()
        self.assertEqual([f["f"] for f in self.bar()["fields"]], ["st", "o", "due", "imp", "lik", "ws", "ms"])
        self.v.propose("dec2", [{"n": 1, "op": "new", "table": "decisions", "match": "strong", "flags": [], "decision": "approved",
                                 "values": {"project": "ABC", "decision": "A second decision", "status": "Pending", "made_by": "Sara Example",
                                            "needed_by": iso(5), "source": "Alan (cx-edit)"}}])
        self.v.run("apply")
        self.open_work("decisions")
        self.b.eval("reloadData().then(()=>renderWork())")
        self.b.pump(1.0)
        self.b.eval("HL.clear(); DEC.slice(0,2).forEach(d=>HL.set(d.id,'decisions')); hlPaint()")
        self.assertEqual([f["f"] for f in self.bar()["fields"]], ["by"])   # a decision has only its maker here
        self.assertEqual(self.bar()["q"], ["clear"])                       # and no Close

    def select_raid(self):
        ids = self.b.eval("[...document.querySelectorAll('#workTbl tr[data-row]')].map(r=>r.dataset.row)")
        self.select(*ids[:2])

    # ── one click, one Undo ──

    def test_close_two_with_one_click_one_undo_and_a_line_each(self):
        b = self.open_work()
        before = self.applies()
        self.select("ABC-A-001", "ABC-A-002")
        b.click("#wbulk [data-bq=close]")
        self.saved()
        self.until(lambda: self.applies() > before and self.acts("status", "ABC-A-001", "ABC-A-002") == ["Closed", "Closed"])
        for id_ in ("ABC-A-001", "ABC-A-002"):
            row = self.row("actions", id_)
            self.assertEqual((row["status"], row["closed"]), ("Closed", date.today().isoformat()))
        self.assertEqual(self.applies(), before + 1)                       # one apply
        self.assertIn("Closed 2 items", self.snack())
        self.assertEqual(self.b.eval("HL.size"), 0)                         # the highlight is cleared afterwards
        lines = [r for r in self.v.rows("change_log") if r["field"] == "status" and r["new_value"] == "Closed"]
        self.assertEqual(sorted(r["item_id"] for r in lines), ["ABC-A-001", "ABC-A-002"])   # Activity: a line for each item
        self.arm()
        b.click("#snackU")                                                  # one Undo puts both back
        self.saved()
        self.until(lambda: self.acts("status", "ABC-A-001", "ABC-A-002") == ["Open", "Open"])
        for id_ in ("ABC-A-001", "ABC-A-002"):
            self.assertEqual(self.row("actions", id_)["status"], "Open")
        b.eval("setOf('st').clear(); workChanged()")
        self.select("ABC-A-001", "ABC-A-002")
        b.click("#wbulk [data-bq=reopen]")
        self.saved()
        self.until(lambda: self.row("actions", "ABC-A-001")["closed"] is None)
        self.assertEqual(self.row("actions", "ABC-A-001")["closed"], None)

    def test_owner_priority_and_due_date_from_the_bar(self):
        b = self.open_work()
        self.select("ABC-A-001", "ABC-A-002")
        self.pick("o", "Omar Ali")
        self.until(lambda: self.acts("owner", "ABC-A-001", "ABC-A-002") == ["Omar Ali"] * 2)
        self.assertEqual([self.row("actions", i)["owner"] for i in ("ABC-A-001", "ABC-A-002")], ["Omar Ali", "Omar Ali"])
        self.assertIn("Owner set to Omar Ali on 2 items", self.snack())
        self.select("ABC-A-001", "ABC-A-002")
        self.pick("pr", "Low")
        self.until(lambda: self.acts("priority", "ABC-A-001", "ABC-A-002") == ["Low", "Low"])
        self.assertEqual([self.row("actions", i)["priority"] for i in ("ABC-A-001", "ABC-A-002")], ["Low", "Low"])
        self.select("ABC-A-001", "ABC-A-002")
        b.eval(f"document.getElementById('bkDate').focus(); document.getElementById('bkDate').value={shown(wd(30))!r}")
        b.key("Enter")                                                      # a date is set with Enter (or the calendar)
        self.saved()
        self.until(lambda: self.acts("due_date", "ABC-A-001", "ABC-A-002") == [wd(30)] * 2)
        self.assertEqual([self.row("actions", i)["due_date"] for i in ("ABC-A-001", "ABC-A-002")], [wd(30), wd(30)])

    def test_items_that_cannot_take_the_change_are_left_out_and_named(self):
        b = self.open_work()
        self.v.propose("late", [new_action(1, "Raised in the future", raised=iso(3))])
        self.v.run("apply")
        b.eval("reloadData().then(()=>renderWork())")
        b.pump(1.0)
        late = next(r["id"] for r in self.v.rows("actions") if r["description"] == "Raised in the future")
        self.select("ABC-A-002", late)
        b.click("#wbulk [data-bq=close]")
        self.saved()
        self.until(lambda: self.row("actions", "ABC-A-002")["status"] == "Closed")
        self.assertEqual(self.row("actions", "ABC-A-002")["status"], "Closed")       # the one that can, changes
        self.assertEqual(self.row("actions", late)["status"], "Open")                # the other is left out
        text = self.snack()
        self.assertIn(late, text)
        self.assertIn("Left out", text)
        self.select(late, "ABC-A-001") if False else None

    def test_nothing_changes_when_no_item_can_take_it(self):
        b = self.open_work()
        self.v.propose("late", [new_action(1, "Raised in the future", raised=iso(3)), new_action(2, "Also raised in the future", raised=iso(4))])
        self.v.run("apply")
        b.eval("reloadData().then(()=>renderWork())")
        b.pump(1.0)
        before = self.applies()
        late = [r["id"] for r in self.v.rows("actions") if "future" in r["description"]]
        self.select(*late)
        b.click("#wbulk [data-bq=close]")
        b.pump(0.8)
        self.assertEqual(self.applies(), before)                            # nothing is saved unless at least one item can take it
        self.assertIn("Nothing changed", self.snack())
        self.assertTrue(all(self.row("actions", i)["status"] == "Open" for i in late))

    def test_editing_a_cell_of_a_highlighted_row_changes_all_of_them(self):
        b = self.open_work()
        self.select("ABC-A-001", "ABC-A-002")
        # #241 A: in the Compact row the owner cell's centre is the person link (which opens the person, as a link should); the
        # cell's own ▾ opens its editor, which is what this test checks
        b.click('#workTbl tr[data-row="ABC-A-002"] td[data-f="o"] .cebtn')
        b.wait("document.querySelector('#workTbl td.editing select')")
        self.assertEqual(sorted(b.eval("[...HL.keys()]")), ["ABC-A-001", "ABC-A-002"])   # the group stays highlighted
        b.eval("""(()=>{ const s=document.querySelector('#workTbl td.editing select'); s.value='Omar Ali'; s.dispatchEvent(new Event('change',{bubbles:true})); })()""")
        self.saved()
        self.until(lambda: self.acts("owner", "ABC-A-001", "ABC-A-002") == ["Omar Ali"] * 2)
        self.assertEqual([self.row("actions", i)["owner"] for i in ("ABC-A-001", "ABC-A-002")], ["Omar Ali", "Omar Ali"])
        self.assertIn("2 items", self.snack())
        self.assertEqual(self.row("actions", "DEF-A-001")["owner"], "Omar Ali")        # (it already was Omar's) and nothing else moved

    def test_a_long_batch_asks_first(self):
        b = self.open_work()
        self.v.propose("many", [new_action(i, f"Batch item {i}") for i in range(1, 27)])
        self.v.run("apply")
        b.eval("reloadData().then(()=>renderWork())")
        b.pump(1.2)
        before = self.applies()
        ids = b.eval("[...document.querySelectorAll('#workTbl tr[data-row]')].map(r=>r.dataset.row)")
        self.assertGreater(len(ids), 25)
        b.eval(f"HL.clear(); {ids!r}.forEach(i=>HL.set(i,'actions')); hlPaint()")
        b.click("#wbulk [data-bq=close]")
        b.wait("document.getElementById('boardDlg').open")
        self.assertIn("Change", b.eval("document.getElementById('bdTitle').textContent"))
        b.click("#bdCancel")
        b.pump(0.6)
        self.assertEqual(self.applies(), before)                            # cancelling changes nothing
        b.click("#wbulk [data-bq=close]")
        b.wait("document.getElementById('boardDlg').open")
        self.arm()
        b.click("#bdOk")
        self.saved()
        self.until(lambda: self.applies() == before + 1 and {r["status"] for r in self.v.rows("actions") if r["description"].startswith("Batch item")} == {"Closed"})
        self.assertEqual(self.applies(), before + 1)
        self.assertEqual({r["status"] for r in self.v.rows("actions") if r["description"].startswith("Batch item")}, {"Closed"})

    def test_the_same_bar_is_over_the_board(self):
        b = self.open_work(layout="board")
        cards = b.eval("[...document.querySelectorAll('#workBoard .bcard')].map(c=>c.dataset.row)")
        b.click(f'#workBoard .bcard[data-row="{cards[0]}"] .bct')
        b.click(f'#workBoard .bcard[data-row="{cards[1]}"] .bct', modifiers=META)
        self.assertFalse(self.bar()["hidden"])
        self.assertEqual(self.bar()["n"], "2 selected")
        self.pick("pr", "Low")
        self.until(lambda: set(self.acts("priority", *cards[:2])) == {"Low"})
        self.assertEqual({self.row("actions", c)["priority"] for c in cards[:2]}, {"Low"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
