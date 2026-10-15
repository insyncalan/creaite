"""BL-103: the Work board's drags (Sprint 4a), in a real browser against the real live server.

Run: python3 dev/tests/test_work_board_moves.py   (needs Google Chrome; skipped otherwise)

Split from test_work_board.py so the layout tests and the drags run side by side. Real mouse events; every move is read back from the database the server wrote.
"""
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from work_board_case import BoardCase, TODAY, iso, wd, week_sunday  # noqa: E402

class BoardMoves(BoardCase):
    """Real drags. Each test gets its own vault, because a move changes it."""

    def test_drag_to_a_due_column_asks_for_a_date_and_saves(self):
        b = self.open_board("actions", "due", view="open")
        card = self.card_in("Later")
        b.drag(self.card_sel(card), self.col_sel("week") + " .bch")
        b.wait("document.getElementById('boardDlg').open")
        self.assertEqual(b.eval("document.getElementById('bdTitle').textContent"), f"Due date for {card}")
        friday = TODAY + timedelta(days=4 - TODAY.weekday())
        friday = TODAY if friday < TODAY else friday
        self.assertEqual(b.eval("document.getElementById('bdDate').value"), friday.strftime("%d-%m-%Y"))      # a sensible default
        t1 = wd(1)                                                                   # BL-181: a working day, so no weekend alert
        b.eval(f"document.getElementById('bdDate').value={t1[8:10] + '-' + t1[5:7] + '-' + t1[:4]!r}")
        b.click("#bdOk")
        self.wait_saved()
        self.assertEqual(self.action(card)["due_date"], t1)
        self.assertIn(card, self.columns()["This week"] if date.fromisoformat(t1) <= week_sunday(TODAY) else self.columns()["Next week"])

    def test_cancelling_the_date_puts_the_card_back(self):
        b = self.open_board("actions", "due", view="open")
        card = self.card_in("Later")
        before = self.action(card)["due_date"]
        b.drag(self.card_sel(card), self.col_sel("next") + " .bch")
        b.wait("document.getElementById('boardDlg').open")
        b.click("#bdCancel")
        b.wait("!document.getElementById('boardDlg').open")
        self.assertEqual(self.action(card)["due_date"], before)
        self.assertIn(card, self.columns()["Later"])

    def test_a_past_date_is_refused(self):
        b = self.open_board("actions", "due", view="open")
        card = self.card_in("Later")
        before = self.action(card)["due_date"]
        b.drag(self.card_sel(card), self.col_sel("week") + " .bch")
        b.wait("document.getElementById('boardDlg').open")
        b.eval(f"document.getElementById('bdDate').value={iso(-2)[8:10] + '-' + iso(-2)[5:7] + '-' + iso(-2)[:4]!r}")
        b.click("#bdOk")
        self.assertIn("Choose today or a later day", b.eval("document.getElementById('bdErr').textContent"))
        self.assertTrue(self.dialog_open())
        self.assertEqual(self.action(card)["due_date"], before)

    def test_overdue_is_not_a_drop_target(self):
        b = self.open_board("actions", "due", view="open")
        card = self.card_in("Later")
        before = self.action(card)["due_date"]
        self.assertTrue(b.eval("document.querySelector('#workBoard .bcol[data-col=\"overdue\"]').classList.contains('nodrop')"))
        b.drag(self.card_sel(card), self.col_sel("overdue") + " .bch")
        self.assertFalse(self.dialog_open())
        self.assertIn("Overdue is a date that has passed", b.eval("document.getElementById('snackT').textContent"))
        self.assertEqual(self.action(card)["due_date"], before)
        self.assertIn(card, self.columns()["Later"])
        # the Move to… menu never offers it either
        b.click(self.card_sel(card) + " .bmv")
        b.wait("document.getElementById('bdMoveMenu')")
        self.assertEqual(b.eval("[...document.querySelectorAll('#bdMoveMenu button')].map(x=>x.textContent)"), ["This week", "Next week", "No date"])

    def test_drop_on_no_date_asks_to_clear_it(self):
        b = self.open_board("actions", "due", view="open")
        card = self.card_in("Later")
        b.drag(self.card_sel(card), self.col_sel("none") + " .bch")
        b.wait("document.getElementById('boardDlg').open")
        self.assertIn("Clear the due date", b.eval("document.getElementById('bdTitle').textContent"))
        self.assertTrue(b.eval("document.getElementById('bdDateRow').hidden"))
        b.click("#bdOk")
        self.wait_saved()
        self.assertIsNone(self.action(card)["due_date"])

    def test_drag_to_a_status_sets_it_and_closing_fills_the_date(self):
        b = self.open_board("actions", "status", view="open")
        card = self.card_in("Open")
        # all statuses (no status chips), so the closed items show too
        b.eval("clearAllFilters(); workChanged()")
        b.wait("document.querySelector('#workBoard .bcol[data-col=\"Closed\"]')")
        b.drag(self.card_sel(card), self.col_sel("Closed") + " .bch")
        self.wait_saved()
        row = self.action(card)
        self.assertEqual((row["status"], row["closed"]), ("Closed", TODAY.isoformat()))
        b.click("#snackU")                                                                           # Undo
        b.wait("A.find(x=>x.id===%r).st==='Open'" % card, 15)
        b.eval("reloadData()")
        self.assertEqual(self.action(card)["status"], "Open")
        self.assertIsNone(self.action(card)["closed"])
        # reopening clears the closed date
        closed = next(r for r in self.v.rows("actions") if r["status"] == "Closed")
        b.drag(self.card_sel(closed["id"]), self.col_sel("Open") + " .bch")
        self.wait_saved()
        row = self.action(closed["id"])
        self.assertEqual((row["status"], row["closed"]), ("Open", None))

    def test_drag_to_an_owner_reassigns_and_tbc_clears(self):
        b = self.open_board("actions", "owner", view="open")
        sara = next(h for h in self.columns() if h.startswith("Sara"))
        card = self.card_in("Me")
        b.drag(self.card_sel(card), self.col_sel(sara) + " .bch")
        self.wait_saved(f"moved to {sara}")
        self.assertEqual(self.action(card)["owner"], sara)
        b.drag(self.card_sel(card), self.col_sel("TBC") + " .bch")
        self.wait_saved("moved to TBC")
        self.assertEqual(self.action(card)["owner"], "TBC")

    def test_drag_to_a_milestone_attaches_and_detaches_it(self):
        b = self.open_board("actions", "milestone", view="open")
        b.eval("PROJF.clear(); PROJF.add('ABC'); workChanged()")
        b.wait("document.querySelector('#workBoard .bcol')")
        card = self.card_in("No milestone")
        b.drag(self.card_sel(card), self.col_sel("ABC-M-001") + " .bch")
        self.wait_saved("moved to UAT start")
        self.assertEqual(self.action(card)["milestone"], "ABC-M-001")
        b.drag(self.card_sel(card), self.col_sel("") + " .bch")
        self.wait_saved("moved to No milestone")
        self.assertIsNone(self.action(card)["milestone"])
        heads = [h.split(" · ")[0] for h in self.headers()]
        self.assertNotIn("Pilot live", heads)                                                        # another project's milestone is never offered

    def test_move_to_menu_does_the_same_without_dragging(self):
        b = self.open_board("actions", "owner", view="open")
        card = self.card_in("Me")
        b.click(self.card_sel(card) + " .bmv")
        b.wait("document.getElementById('bdMoveMenu')")
        names = b.eval("[...document.querySelectorAll('#bdMoveMenu button')].map(x=>x.textContent)")
        self.assertNotIn("Me", names)                                                                # not where it already is
        b.click("#bdMoveMenu button[data-bto=\"TBC\"]")
        self.wait_saved()
        self.assertEqual(self.action(card)["owner"], "TBC")

    def test_move_menu_keyboard(self):
        b = self.open_board("actions", "due", view="open")
        card = self.card_in("Later")
        b.eval(f"document.querySelector('{self.card_sel(card)} .bmv').focus()")
        b.key("Enter")
        b.wait("document.getElementById('bdMoveMenu')")
        self.assertEqual(b.eval("document.activeElement.textContent"), "This week")
        b.key("Escape")
        b.wait("!document.getElementById('bdMoveMenu')")
        self.assertEqual(b.eval("document.activeElement.className"), "bmv")

    def test_escape_cancels_a_drag(self):
        b = self.open_board("actions", "owner", view="open")
        card = self.card_in("Me")
        sara = next(h for h in self.columns() if h.startswith("Sara"))
        before = self.action(card)["owner"]
        b.drag(self.card_sel(card), self.col_sel(sara) + " .bch", release=False)
        self.assertTrue(b.eval("document.body.classList.contains('bdragging')"))
        self.assertTrue(b.eval("!!document.querySelector('.bghost')"))
        self.assertTrue(b.eval(f"document.querySelector('{self.col_sel(sara)}').classList.contains('drop')"))     # the target is marked
        self.assertIn("Drop to move here", b.eval(f"document.querySelector('{self.col_sel(sara)} .bdrop').textContent"))   # in words, not just colour
        b.key("Escape")
        b.mouse_up()
        self.assertFalse(b.eval("document.body.classList.contains('bdragging')"))
        self.assertEqual(self.action(card)["owner"], before)
        self.assertFalse(b.eval("document.getElementById('snackT').textContent.includes('saved')"))

    def test_a_click_without_moving_opens_the_card_and_does_not_move_it(self):
        b = self.open_board("actions", "owner", view="open")
        card = self.card_in("Me")
        before = self.action(card)
        b.click(self.card_sel(card) + " .bid")                         # BL-122: the ID opens a card
        b.wait("document.getElementById('panel').classList.contains('on')")
        self.assertEqual(self.action(card), before)

    def test_raid_moves_keep_the_priority(self):
        b = self.open_board("raid", "owner", view="open")
        card = self.card_in("Me")
        before = self.raid(card)
        sara = next(h for h in self.columns() if h.startswith("Sara"))
        b.drag(self.card_sel(card), self.col_sel(sara) + " .bch")
        self.wait_saved()
        after = self.raid(card)
        self.assertEqual(after["owner"], sara)
        self.assertEqual((after["impact"], after["likelihood"]), (before["impact"], before["likelihood"]))

    def test_closed_column_shows_recent_items_with_show_all(self):
        v = self.v
        old = [r for r in v.rows("actions") if r["status"] == "Closed"][:2]
        con = __import__("sqlite3").connect(v.root / "system/tracker.db")
        con.execute("UPDATE actions SET raised=?, closed=? WHERE id=?", (iso(-60), iso(-40), old[0]["id"]))
        con.commit()
        con.close()
        b = self.open_board("actions", "status", view="closed")
        b.eval("reloadData()")
        b.wait(f"A.find(x=>x.id==={old[0]['id']!r}).closed==={iso(-40)!r}")
        b.click('#wlay [data-lay="list"]')
        b.click('#wlay [data-lay="board"]')
        b.wait("document.querySelector('#workBoard .bcol')")
        self.assertNotIn(old[0]["id"], self.columns()["Closed"])
        b.click("#workBoard .bshow")
        b.wait(f"document.querySelector('#workBoard .bcard[data-row=\"{old[0]['id']}\"]')")
        self.assertIn("Last 14 days only", b.eval("document.querySelector('#workBoard .bshow').textContent"))

    def test_undo_restores_the_owner(self):
        b = self.open_board("actions", "owner", view="open")
        card = self.card_in("Me")
        sara = next(h for h in self.columns() if h.startswith("Sara"))
        before = self.action(card)["owner"]
        b.drag(self.card_sel(card), self.col_sel(sara) + " .bch")
        self.wait_saved()
        b.click("#snackU")
        b.wait("/Undone/.test(document.getElementById('snackT').textContent)", 15)
        self.assertEqual(self.action(card)["owner"], before)
        self.assertIn(card, b.eval("[...document.querySelectorAll('#workBoard .bcol[data-col=\"@me\"] .bcard')].map(c=>c.dataset.row)"))


if __name__ == "__main__":
    unittest.main()
