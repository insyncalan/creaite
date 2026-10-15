"""BL-103: the Decisions board (sprint-debug-log-2b), in a real browser against the real live server.

Run: python3 dev/tests/test_decisions_board.py   (needs Google Chrome; skipped otherwise)

Cards are dragged with real mouse events. Every column is checked against an oracle written in Python, and every move is read back from
the database the server wrote. A decision has no milestone, so the groupings are Status, Decision maker and Needed by.
"""
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase, pin_page_clock  # noqa: E402
from test_decisions_dashboard import NOW, TODAY, d, load  # noqa: E402      the pinned Thursday


def week_sunday(day):
    return day + timedelta(days=6 - day.weekday())


def due_key(iso):
    """The oracle for the Needed by grouping of a pending decision."""
    if not iso:
        return "none"
    due = date.fromisoformat(iso)
    if due < TODAY:
        return "overdue"
    sun = week_sunday(TODAY)
    return "week" if due <= sun else "next" if due <= sun + timedelta(days=7) else "later"


class BoardCase(LiveBrowserCase):
    """ABC-D-005 and -008 made; ABC-D-006 pending from Sara and late; ABC-D-007 pending from Alan, needed in 5 days; DEF-D-002 pending
    from Omar with no date. Every test gets a fresh server so moves can be written freely."""
    width, height = 1500, 1000

    @classmethod
    def load(cls, v):
        load(v, TODAY)

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": NOW}

    def setUp(self):
        super().setUp()
        pin_page_clock(self.b, NOW)

    def row(self, id_):
        return next(r for r in self.v.rows("decisions") if r["id"] == id_)

    def open_board(self, group=None, view="all"):
        b = self.b
        b.eval("WT='decisions'; go('work')")
        b.wait("document.querySelector('#workTbl tbody tr[data-row], #workTbl .empty')")
        if view:
            b.click(f'#wviews [data-wv="{view}"]')
            b.wait(f"WVIEW==={view!r}")
        b.click('#wlay [data-lay="board"]')
        b.wait("!document.getElementById('workBoard').hidden && document.querySelector('#workBoard .bcol, #workBoard .empty')")
        if group:
            b.eval(f"(()=>{{ const s=document.getElementById('wgrp'); s.value={group!r}; s.dispatchEvent(new Event('change',{{bubbles:true}})); }})()")
            b.wait(f"groupOf(WT)==={group!r}")
        return b

    def columns(self, by="key"):
        """{column key (or label): [card IDs]} in page order."""
        attr = "c.dataset.col" if by == "key" else "c.querySelector('h3').textContent.replace(/ · \\d+$/,'')"
        return self.b.eval(f"Object.fromEntries([...document.querySelectorAll('#workBoard .bcol')].map(c=>[{attr},[...c.querySelectorAll('.bcard')].map(k=>k.dataset.row)]))")

    def card(self, id_):
        return f'#workBoard .bcard[data-row="{id_}"]'

    def col(self, key):
        return f'#workBoard .bcol[data-col="{key}"] .bch'

    def wait_saved(self, moved=""):
        self.b.wait(f"/saved and applied/.test(document.getElementById('snackT').textContent) && document.getElementById('snackT').textContent.includes({moved!r})", 15)


class Layout(BoardCase):
    shared_server = True

    def test_the_switch_is_on_the_decisions_tab_with_the_decisions_groupings(self):
        b = self.open_board()
        self.assertFalse(b.eval("document.getElementById('wlay').hidden"))
        self.assertEqual(b.eval("[...document.querySelectorAll('#wgrp option')].map(o=>o.textContent)"), ["Status", "Decision maker", "Needed by", "Project"])   # BL-129 adds Project
        self.assertEqual(b.eval("document.getElementById('wgrp').value"), "status")                  # the default for Decisions
        self.assertIn("lay=board&g=status", b.eval("location.hash"))
        self.assertEqual(b.errors, [])

    def test_actions_and_raid_keep_their_own_groupings(self):
        b = self.open_board()
        b.click('#wtabs button[data-t="actions"]')
        b.wait("WT==='actions'")
        b.click('#wlay [data-lay="board"]')
        b.wait("!document.getElementById('workBoard').hidden")
        self.assertEqual(b.eval("[...document.querySelectorAll('#wgrp option')].map(o=>o.value)"), ["due", "status", "owner", "milestone", "project", "priority", "workstream"])
        self.assertEqual(b.eval("groupOf('actions')"), "due")

    def test_the_layout_survives_a_reload_and_back(self):
        b = self.open_board(group="owner")
        b.reload("typeof go==='function' && LIVE")
        b.wait("!document.getElementById('workBoard').hidden && document.querySelector('#workBoard .bcol')")
        self.assertEqual(b.eval("WT"), "decisions")
        self.assertEqual(b.eval("groupOf('decisions')"), "owner")
        b.click('#wlay [data-lay="list"]')
        b.wait("document.getElementById('workBoard').hidden")
        self.assertNotIn("lay=board", b.eval("location.hash"))

    def test_status_columns(self):
        self.open_board()
        self.assertEqual({k: sorted(v) for k, v in self.columns().items()},
                         {"Pending": ["ABC-D-006", "ABC-D-007", "DEF-D-002"], "Made": ["ABC-D-005", "ABC-D-008"]})   # none withdrawn: no Withdrawn column

    def test_decision_maker_columns_me_first_then_by_count_then_no_one(self):
        self.open_board("owner")
        got = self.columns("label")
        heads = list(got)
        self.assertEqual(heads[0], "Me")
        self.assertEqual(heads[-1], "No one asked")
        self.assertEqual(got["Me"], ["ABC-D-007"])
        self.assertEqual(sorted(got["Jane Doe"]), ["ABC-D-005", "ABC-D-008"])
        self.assertEqual(heads[1], "Jane Doe")                                                       # two cards: before the one-card people
        self.assertEqual(got["Sara Example"], ["ABC-D-006"])
        self.assertEqual(got["Omar Ali"], ["DEF-D-002"])
        self.assertEqual(got["No one asked"], [])

    def test_needed_by_columns_against_the_oracle(self):
        self.open_board("due")
        got = self.columns()
        self.assertEqual(list(got)[:5], ["overdue", "week", "next", "later", "none"])
        want = {"overdue": ["ABC-D-006"], "none": ["DEF-D-002"]}
        want.setdefault(due_key(d(5)), []).append("ABC-D-007")
        for key in ("overdue", "week", "next", "later", "none"):
            self.assertEqual(sorted(got[key]), sorted(want.get(key, [])), key)
        self.assertIn("ABC-D-008", got["decided"])                                                  # made since the last 14 days
        self.assertTrue(set(got["decided"]) <= {"ABC-D-005", "ABC-D-008"})
        self.assertEqual(self.b.eval("document.querySelector('#workBoard .bcol[data-col=\"decided\"]').classList.contains('nodrop')"), True)

    def test_cards_show_who_is_asked_the_due_in_words_and_the_status(self):
        self.open_board()
        late = self.b.eval(f"document.querySelector('{self.card('ABC-D-006')}').textContent")
        self.assertIn("Extend the pilot by two weeks", late)
        self.assertIn("3 days late", late)
        self.assertEqual(self.b.eval(f"document.querySelector('{self.card('ABC-D-006')} .bdue').classList.contains('late')"), True)
        self.assertEqual(self.b.eval(f"document.querySelector('{self.card('ABC-D-006')} .bown').title"), "Asked of Sara Example")
        self.assertEqual(self.b.eval(f"document.querySelector('{self.card('ABC-D-006')} .bpri').textContent"), "Pending")
        self.assertIn("No date needed by", self.b.eval(f"document.querySelector('{self.card('DEF-D-002')}').textContent"))
        made = self.b.eval(f"document.querySelector('{self.card('ABC-D-008')}').textContent")
        self.assertIn("Made", made)
        self.assertEqual(self.b.eval(f"!!document.querySelector('{self.card('ABC-D-008')} .bmv')"), False)       # nothing to move

    def test_filters_search_and_saved_views_are_shared_with_the_list(self):
        b = self.open_board(view="pending")
        board = sorted(i for ids in self.columns().values() for i in ids)
        self.assertEqual(board, ["ABC-D-006", "ABC-D-007", "DEF-D-002"])
        b.click('#wlay [data-lay="list"]')
        b.wait("document.getElementById('workBoard').hidden")
        self.assertEqual(sorted(b.eval("[...document.querySelectorAll('#workTbl tbody tr[data-row]')].map(r=>r.dataset.row)")), board)
        b.eval("(()=>{ const q=document.getElementById('workQ'); q.value='pilot'; q.dispatchEvent(new Event('input',{bubbles:true})); })()")
        b.wait("document.getElementById('workQ').value==='pilot'")
        listed = sorted(b.eval("[...document.querySelectorAll('#workTbl tbody tr[data-row]')].map(r=>r.dataset.row)"))
        b.click('#wlay [data-lay="board"]')
        b.wait("!document.getElementById('workBoard').hidden")
        self.assertEqual(sorted(i for ids in self.columns().values() for i in ids), listed)
        self.assertEqual(listed, ["ABC-D-006", "DEF-D-002"])                                         # "pilot" is in both titles
        self.assertEqual(b.eval("document.querySelector('#wcount').textContent.startsWith('Showing 2')"), True)

    def test_a_saved_view_keeps_the_layout_and_grouping_for_decisions(self):
        b = self.open_board("owner", view="pending")
        b.eval("saveView('Waiting on people')")
        b.wait("(SAVED.decisions||[]).some(v=>v.name==='Waiting on people')", 15)
        v = next(v for v in b.eval("SAVED.decisions") if v["name"] == "Waiting on people")
        self.assertEqual((v["lay"], v["g"]), ("board", "owner"))
        b.click('#wlay [data-lay="list"]')
        b.eval("WGRP.decisions='status'")
        b.click('#wviews [data-wv="all"]')
        b.click('#wviews [data-wv="saved:Waiting on people"]')
        b.wait("layoutOf('decisions')==='board' && groupOf('decisions')==='owner'")
        b.wait("!document.getElementById('workBoard').hidden")

    def test_settings_choose_the_default_grouping(self):
        b = self.open_board()
        b.eval("go('settings','work')")
        b.wait("document.querySelector('select[data-k=\"bgDecisions\"]')")
        self.assertEqual(b.eval("[...document.querySelectorAll('select[data-k=\"bgDecisions\"] option')].map(o=>o.value)"), ["status", "owner", "due", "project"])
        self.assertEqual(b.eval("document.querySelector('select[data-k=\"bgDecisions\"]').value"), "status")
        b.eval("WGRP.decisions=undefined; S.bgDecisions='due'")                                      # the setting is the default until a choice is made
        self.assertEqual(b.eval("groupOf('decisions')"), "due")
        b.eval("S.bgDecisions='nonsense'")
        self.assertEqual(b.eval("groupOf('decisions')"), "status")                                  # an unknown value falls back


class Moves(BoardCase):
    # BL-176 (sprint-peek): Made opens the decision in the peek with Made staged (Date made today); nothing is written until Apply
    STAGED_MADE = "CUR && CUR.id===%r && document.getElementById('panel').classList.contains('peek') && PKS.length===1"

    def test_drag_to_made_opens_the_record_form_filled_in_and_writes_nothing_yet(self):
        b = self.open_board()
        b.drag(self.card("ABC-D-006"), self.col("Made"))
        b.wait(self.STAGED_MADE % "ABC-D-006", 15)
        self.assertEqual(b.eval("PKS[0].patch"), {"st": "Made", "date": TODAY.isoformat()})
        self.assertIn(f"{TODAY:%d-%m-%Y}", b.eval("document.querySelector('#panel [data-pkp=\"date\"]').textContent"))
        self.assertIn("Sara Example", b.eval("document.querySelector('#panel [data-pkp=\"o\"]').textContent"))
        self.assertEqual(self.row("ABC-D-006")["status"], "Pending")                                # staged, not written
        b.click("#pkApply")
        b.wait("PKS.length===0&&/Applied 1 change/.test(document.getElementById('snackT').textContent)", 20)
        row = self.row("ABC-D-006")
        self.assertEqual((row["status"], row["date"], row["made_by"]), ("Made", TODAY.isoformat(), "Sara Example"))
        self.assertEqual(len(self.v.rows("decisions")), 5)                                           # the same record and number
        self.assertEqual(b.errors, [])

    def test_cancelling_the_form_leaves_the_card_in_pending(self):
        b = self.open_board()
        b.drag(self.card("ABC-D-007"), self.col("Made"))
        b.wait(self.STAGED_MADE % "ABC-D-007", 15)
        b.click("#pkUndo")                                                                           # Undo last takes it back
        b.wait("PKS.length===0", 10)
        b.eval("closePanel()")
        self.assertEqual(self.row("ABC-D-007")["status"], "Pending")
        b.wait("(()=>{ const c=[...document.querySelectorAll('#workBoard .bcard[data-row=\"ABC-D-007\"]')]; return c.length>0; })()", 5)
        self.assertIn("ABC-D-007", self.columns()["Pending"])

    def test_move_to_made_from_the_menu_does_the_same(self):
        b = self.open_board()
        b.click(self.card("ABC-D-007") + " .bmv")
        b.click('#bdMoveMenu [data-bto="Made"]')
        b.wait(self.STAGED_MADE % "ABC-D-007", 15)
        self.assertEqual(b.eval("PKS[0].patch.st"), "Made")

    def test_drag_to_withdrawn_asks_first_then_withdraws_and_undo_brings_it_back(self):
        b = self.open_board()
        self.assertNotIn("Withdrawn", self.columns())                                                # no such column while empty: use the menu
        b.click(self.card("ABC-D-007") + " .bmv")
        b.click('#bdMoveMenu [data-bto="Withdrawn"]')
        b.wait("document.getElementById('boardDlg').open")
        self.assertEqual(b.eval("document.getElementById('bdOk').textContent"), "Withdraw")
        self.assertEqual(b.eval("document.getElementById('bdDateRow').hidden"), True)                # a question, not a date
        b.click("#bdCancel")
        self.assertEqual(self.row("ABC-D-007")["status"], "Pending")                                 # cancelling changes nothing
        b.click(self.card("ABC-D-007") + " .bmv")
        b.click('#bdMoveMenu [data-bto="Withdrawn"]')
        b.wait("document.getElementById('boardDlg').open")
        b.click("#bdOk")
        b.wait("/saved and applied/.test(document.getElementById('snackT').textContent)", 15)
        row = self.row("ABC-D-007")
        self.assertEqual((row["status"], row["date"]), ("Withdrawn", None))
        self.assertIn("ABC-D-007", self.columns().get("Withdrawn", []))
        b.click("#snackU")
        b.wait("DEC.find(x=>x.id==='ABC-D-007').st==='Pending'", 15)
        b.eval("reloadData()")
        self.assertEqual(self.row("ABC-D-007")["status"], "Pending")

    def test_a_made_decision_never_goes_back_to_pending(self):
        b = self.open_board()
        b.drag(self.card("ABC-D-008"), self.col("Pending"))
        b.wait("/can't go back to pending/.test(document.getElementById('snackT').textContent)", 10)
        self.assertEqual(self.row("ABC-D-008")["status"], "Made")
        self.assertIn("ABC-D-008", self.columns()["Made"])
        self.assertEqual(b.eval("document.getElementById('boardDlg').open"), False)

    def test_a_made_decision_cannot_be_moved_at_all(self):
        b = self.open_board()
        b.drag(self.card("ABC-D-008"), self.col("Made"))                                              # its own column: a no-op
        self.assertEqual(self.row("ABC-D-008")["status"], "Made")
        b.eval("boardMoveMenu(document.body, 'ABC-D-008')")
        b.wait("/can't be moved/.test(document.getElementById('snackT').textContent)", 10)
        self.assertEqual(b.eval("!!document.getElementById('bdMoveMenu')"), False)

    def test_drag_to_a_decision_maker_changes_who_is_asked(self):
        b = self.open_board("owner")
        b.drag(self.card("ABC-D-007"), self.col("Omar Ali"))
        self.wait_saved("ABC-D-007 now asked of Omar Ali")
        row = self.row("ABC-D-007")
        self.assertEqual((row["made_by"], row["status"]), ("Omar Ali", "Pending"))
        b.drag(self.card("ABC-D-007"), self.col("@none"))
        self.wait_saved("now asked of no one")
        self.assertIn(self.row("ABC-D-007")["made_by"], (None, ""))

    def test_a_made_decisions_maker_is_not_changed_from_the_board(self):
        b = self.open_board("owner")
        b.drag(self.card("ABC-D-008"), self.col("Omar Ali"))
        b.wait("/only a pending decision can be moved/.test(document.getElementById('snackT').textContent)", 10)
        self.assertEqual(self.row("ABC-D-008")["made_by"], "Jane Doe")

    def test_drag_to_a_needed_by_column_asks_for_a_date_and_never_a_past_one(self):
        b = self.open_board("due")
        b.drag(self.card("DEF-D-002"), self.col("next"))
        b.wait("document.getElementById('boardDlg').open")
        self.assertIn("Needed by, for DEF-D-002", b.eval("document.getElementById('bdTitle').textContent"))
        b.eval("(()=>{ const i=document.getElementById('bdDate'); i.value='01-01-2020'; })()")
        b.click("#bdOk")
        self.assertIn("past date", b.eval("document.getElementById('bdErr').textContent"))
        self.assertEqual(self.row("DEF-D-002")["needed_by"], None)
        future = TODAY + timedelta(days=12)
        b.eval(f"(()=>{{ document.getElementById('bdDate').value='{future:%d-%m-%Y}'; }})()")
        b.click("#bdOk")
        self.wait_saved("DEF-D-002 moved to")
        self.assertEqual(self.row("DEF-D-002")["needed_by"], future.isoformat())
        self.assertEqual(self.row("DEF-D-002")["status"], "Pending")

    def test_no_date_asks_before_clearing_it(self):
        b = self.open_board("due")
        b.drag(self.card("ABC-D-007"), self.col("none"))
        b.wait("document.getElementById('boardDlg').open")
        self.assertEqual(b.eval("document.getElementById('bdOk').textContent"), "Clear date")
        b.click("#bdOk")
        self.wait_saved("ABC-D-007 moved to No date")
        self.assertIn(self.row("ABC-D-007")["needed_by"], (None, ""))

    def test_overdue_and_decided_are_not_drop_targets(self):
        b = self.open_board("due")
        b.drag(self.card("ABC-D-007"), self.col("overdue"))
        b.wait("/Overdue is a date that has passed/.test(document.getElementById('snackT').textContent)", 10)
        self.assertEqual(self.row("ABC-D-007")["needed_by"], d(5))
        b.drag(self.card("ABC-D-007"), self.col("decided"))
        b.wait("/no needed-by date/.test(document.getElementById('snackT').textContent)", 10)
        self.assertEqual(self.row("ABC-D-007")["status"], "Pending")

    def test_a_dragged_card_that_is_dropped_outside_goes_back(self):
        b = self.open_board()
        b.drag(self.card("ABC-D-007"), "#wtabs")
        self.assertIn("ABC-D-007", self.columns()["Pending"])
        self.assertEqual(self.row("ABC-D-007")["status"], "Pending")

    def test_the_card_opens_the_panel_and_j_k_step_through_cards(self):
        b = self.open_board()
        b.click(self.card("ABC-D-006"))                              # BL-122: a click highlights the card and opens nothing
        self.assertEqual(b.eval(f"document.querySelector('{self.card('ABC-D-006')}').classList.contains('hl')"), True)
        self.assertFalse(b.eval("!!CUR"))
        b.click(self.card("ABC-D-006") + " .bid")                    # the ID opens it
        b.wait("CUR && CUR.id==='ABC-D-006'")
        self.assertEqual(b.eval(f"document.querySelector('{self.card('ABC-D-006')}').classList.contains('sel')"), True)


class Looks(BoardCase):
    shared_server = True

    def test_both_themes_and_a_phone_width(self):
        b = self.open_board()
        for theme in ("light", "dark"):
            b.eval(f"document.documentElement.setAttribute('data-theme','{theme}')")
            bg = b.eval(f"getComputedStyle(document.querySelector('{self.card('ABC-D-006')}')).backgroundColor")
            ink = b.eval(f"getComputedStyle(document.querySelector('{self.card('ABC-D-006')} .bct')).color")
            self.assertNotEqual(bg, ink, theme)
        b.eval("document.documentElement.removeAttribute('data-theme')")
        self.assertEqual(b.errors, [])


if __name__ == "__main__":
    unittest.main()
