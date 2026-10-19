"""#241 B and C: Work items v2, the keyboard and the client-visible switch. ↑ ↓ move, → or Enter opens the peek, ← closes it or
opens the row's menu; a click selects, and opens another row in the peek only while the peek is open; the peek runs over the
page. S, O, P and T change the status, owner, priority and due date of the cursor row (its cell's editor, the peek's picker, the
menu's list, or the bulk change for a selection); C closes with Undo. V, the eye in the peek bar and the row's menu turn
Client-visible on or off (a badge beside the ID, a tag in the list, Undo), and never without client messaging.
A real browser against the real live server.

Run: python3 dev/tests/test_work_items_v2_keys.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import work_data as W  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402

READY = "typeof go==='function' && LIVE"
MENU = ".cxmenu"
CMD = 4
SAVED = r"saved and applied|apply stopped|Not saved|isn't|can't"


class KeysV2(LiveBrowserCase):
    width, height = 1500, 1000

    @classmethod
    def load(cls, v):
        populate(v)
        W.load(v)

    def setUp(self):
        super().setUp()
        self.b.eval("localStorage.clear()")
        self.b.reload(READY)

    # ── helpers ──
    def open_work(self, tab="actions", grouping="none"):
        b = self.b
        b.eval("go('work')")
        b.wait("document.querySelector('#workTbl tbody tr, #workTbl .empty')")
        if b.eval("WT") != tab:
            b.click(f'#wtabs button[data-t="{tab}"]')
            b.wait(f"WT==='{tab}'")
        if grouping:
            b.eval(f"WLGRP[WT]={grouping!r}; renderWork()")                       # a plain list (not saved): rows in a fixed order
        b.wait("document.querySelector('#workTbl tbody tr[data-row]')")
        return b

    def ids(self):
        return self.b.eval("[...document.querySelectorAll('#workTbl tbody tr[data-row]')].map(r=>r.dataset.row)")

    def row(self, id_):
        return f'#workTbl tr[data-row="{id_}"]'

    def peek_id(self):
        return self.b.eval("pkOn()&&CUR&&CUR.mode==='record'?CUR.id:null")

    def blur(self):
        self.b.eval("document.activeElement&&document.activeElement.blur()")

    def arm(self):
        self.b.eval("document.getElementById('snackT').textContent=''")

    def saved(self, expect=SAVED):
        self.b.wait(f"new RegExp({expect!r}).test(document.getElementById('snackT').textContent)", 30)
        self.b.wait("PULSE.reloads===0 && !PULSE.busy && !EVS.timer", 30)

    def rec(self, table, id_):
        return next(r for r in self.v.rows(table) if r["id"] == id_)

    def menu_labels(self, level=0):
        return self.b.eval(f"""[...document.querySelectorAll("{MENU}")][{level}] ? [...document.querySelectorAll("{MENU}")[{level}]
          .querySelectorAll("[role=menuitem]")].map(b=>b.querySelector("span").firstChild.textContent) : []""")

    def pick(self, label, level=0):
        self.b.eval(f"""[...document.querySelectorAll("{MENU}")[{level}].querySelectorAll("[role=menuitem]")].find(b=>b.querySelector("span").firstChild.textContent==={json.dumps(label)}).click()""")

    def client_with_messaging(self):
        return self.b.eval("A.filter(x=>x.client&&x.st==='Open'&&cmOK(x.cm)).map(x=>x.id)")[0]

    # ── B: moving, opening, closing ──
    def test_arrows_move_open_and_close_and_left_opens_the_menu(self):
        b = self.open_work()
        ids = self.ids()
        self.blur()
        b.key("ArrowDown")
        self.assertEqual(b.eval("HLC"), ids[0])
        b.key("ArrowDown")
        self.assertEqual(b.eval("HLC"), ids[1])
        b.key("ArrowUp")
        self.assertEqual(b.eval("HLC"), ids[0])
        self.assertIsNone(self.peek_id())
        b.key("ArrowRight")                                                    # → opens the peek
        b.wait(f"pkOn()&&CUR&&CUR.id==={ids[0]!r}")
        self.blur()
        b.key("ArrowDown")                                                     # the peek follows
        b.wait(f"CUR&&CUR.id==={ids[1]!r}")
        self.blur()
        b.key("ArrowLeft")                                                     # ← closes the peek
        b.wait("!pkOn()")
        self.assertEqual(b.eval("HLC"), ids[1])
        b.key("ArrowLeft")                                                     # ← with no peek: the row's menu
        b.wait(f'!!document.querySelector("{MENU}")')
        self.assertEqual(self.menu_labels()[0], "Open")
        b.key("Escape")
        b.wait(f'!document.querySelector("{MENU}")')
        b.key("Enter")                                                         # Enter opens too
        b.wait(f"pkOn()&&CUR&&CUR.id==={ids[1]!r}")

    def test_a_click_selects_and_opens_only_while_the_peek_is_open_over_the_page(self):
        b = self.open_work()
        ids = self.ids()
        w0 = b.eval("Math.round(document.getElementById('workWrap').getBoundingClientRect().width)")
        b.click(self.row(ids[0]) + " td.title .wkm")
        self.assertEqual(b.eval("[...HL.keys()]"), [ids[0]])
        self.assertIsNone(self.peek_id())                                      # a click selects only
        b.click(self.row(ids[0]) + " td.title .wkm", count=2)                       # double-click opens
        b.wait(f"pkOn()&&CUR&&CUR.id==={ids[0]!r}")
        self.assertLessEqual(abs(b.eval("Math.round(document.getElementById('workWrap').getBoundingClientRect().width)") - w0), 2)   # over the page
        b.click(self.row(ids[2]) + " td.title .wkm")                               # with the peek open, a click shows that row
        b.wait(f"CUR&&CUR.id==={ids[2]!r}")
        self.assertLessEqual(abs(b.eval("Math.round(document.getElementById('workWrap').getBoundingClientRect().width)") - w0), 2)
        b.key("Escape")
        b.key("Escape")
        b.wait("!pkOn()")
        b.click(self.row(ids[3]) + " .rowid")                                  # the ID opens
        b.wait(f"pkOn()&&CUR&&CUR.id==={ids[3]!r}")

    # ── B: one key per property ──
    def test_s_o_p_t_open_the_cell_editors_on_the_cursor_row(self):
        b = self.open_work()
        ids = self.ids()
        b.click(self.row(ids[0]) + " td.title .wkm")
        self.blur()
        for key, f in (("s", "st"), ("o", "o"), ("p", "pr"), ("t", "due")):
            b.key(key)
            b.wait(f"document.querySelector('{self.row(ids[0])} td.editing[data-f=\"{f}\"]')")
            self.assertTrue(b.eval(f"document.querySelector('{self.row(ids[0])} td.editing').contains(document.activeElement)"), f)
            b.key("Escape")
            b.wait("!document.querySelector('#workTbl td.editing')")
            self.blur()

    def test_s_uses_the_menu_for_a_hidden_column_and_the_peek_picker_when_open(self):
        b = self.open_work()
        ids = self.ids()
        b.eval("COLVIS.actions=COLVIS.actions.filter(c=>c!=='st'); renderWork()")   # Status hidden (not saved)
        b.click(self.row(ids[0]) + " td.title .wkm")
        self.blur()
        b.key("s")
        b.wait(f'!!document.querySelector("{MENU}")')
        self.assertEqual(self.menu_labels(), ["Open", "Delayed", "Closed", "Cancelled"])
        b.key("Escape")
        b.wait(f'!document.querySelector("{MENU}")')
        b.key("Enter")
        b.wait(f"pkOn()&&CUR&&CUR.id==={ids[0]!r}")
        self.blur()
        b.key("o")                                                             # the peek's own owner picker
        b.wait("!!document.querySelector('.pkpop')")
        self.assertIn("Unassigned", b.eval("document.querySelector('.pkpop').textContent"))   # the people list

    def test_a_key_on_a_selection_is_the_bulk_change(self):
        b = self.open_work()
        ids = [i for i in self.ids() if b.eval(f"REC('actions',{i!r}).st")=="Open"][:2]
        b.click(self.row(ids[0]) + " td.title .wkm")
        b.click(self.row(ids[1]) + " td.title .wkm", modifiers=CMD)
        self.blur()
        b.key("s")
        b.wait(f'!!document.querySelector("{MENU}")')
        self.assertIn("2 items", b.eval(f'document.querySelector("{MENU} [role=menu]").getAttribute("aria-label")'))
        self.arm()
        self.pick("Delayed")
        self.saved()
        self.assertEqual([self.rec("actions", i)["status"] for i in ids], ["Delayed", "Delayed"])

    def test_c_closes_the_cursor_row_with_undo(self):
        b = self.open_work()
        id_ = next(i for i in self.ids() if b.eval(f"REC('actions',{i!r}).st") == "Open")
        b.click(self.row(id_) + " td.title .wkm")
        self.blur()
        self.arm()
        b.key("c")
        self.saved()
        self.assertIn("closed", b.eval("document.getElementById('snackT').textContent"))
        self.assertEqual(self.rec("actions", id_)["status"], "Closed")
        b.wait("document.getElementById('snack').classList.contains('on') && document.getElementById('snackU').offsetParent!==null")
        self.arm()
        b.click("#snackU")
        self.saved("^Undone")
        self.assertEqual(self.rec("actions", id_)["status"], "Open")

    def test_decisions_have_no_priority_and_are_not_closed(self):
        b = self.open_work("decisions")
        ids = self.ids()
        b.click(self.row(ids[0]) + " td.title .wkm")
        self.blur()
        b.key("p")
        b.wait("/no priority/.test(document.getElementById('snackT').textContent)")
        b.key("c")
        b.wait("/not closed/.test(document.getElementById('snackT').textContent)")

    # ── C: the client-visible switch ──
    def test_the_peek_eye_shows_and_switches_client_visible(self):
        b = self.open_work()
        id_ = self.client_with_messaging()
        b.eval(f"openRecord('actions',{id_!r})")
        b.wait(f"pkOn()&&CUR&&CUR.id==={id_!r}")
        self.assertEqual(b.eval("document.getElementById('pkCv').getAttribute('aria-pressed')"), "true")
        self.assertEqual(b.eval("document.getElementById('pkCv').dataset.key"), "V")
        self.assertTrue(b.eval("!!document.querySelector('#pkId .cv')"))                        # the badge beside the ID
        self.assertNotEqual(b.eval("getComputedStyle(document.getElementById('pkCv')).backgroundColor"),
                            b.eval("getComputedStyle(document.getElementById('pkLink')).backgroundColor"))   # tinted when on
        self.blur()
        b.key("v")                                                                             # V turns it off (staged, as every peek change)
        b.wait("document.getElementById('pkCv').getAttribute('aria-pressed')==='false'")
        self.assertFalse(b.eval("!!document.querySelector('#pkId .cv')"))
        b.wait("!document.getElementById('pkStage').hidden")
        b.click("#pkUndo")                                                                     # Undo last puts it back
        b.wait("document.getElementById('pkCv').getAttribute('aria-pressed')==='true'")
        b.click("#pkCv")                                                                       # and the eye itself switches it
        b.wait("document.getElementById('pkCv').getAttribute('aria-pressed')==='false'")

    def test_v_and_the_menu_switch_a_row_with_undo_and_the_tag_follows(self):
        b = self.open_work()
        id_ = self.client_with_messaging()
        self.assertTrue(b.eval(f"!!document.querySelector('{self.row(id_)} td.title .tg[data-tg=cv]')"))
        b.click(self.row(id_) + " td.title .wkm")
        self.blur()
        self.arm()
        b.key("v")
        self.saved()
        self.assertIn(f"Client-visible off for {id_}", b.eval("document.getElementById('snackT').textContent"))
        self.assertEqual(self.rec("actions", id_)["client_visible"], 0)
        b.wait(f"!document.querySelector('{self.row(id_)} td.title .tg[data-tg=cv]')")
        self.arm()
        b.click("#snackU")
        self.saved("^Undone")
        self.assertEqual(self.rec("actions", id_)["client_visible"], 1)
        b.wait(f"!!document.querySelector('{self.row(id_)} td.title .tg[data-tg=cv]')")
        b.click(self.row(id_) + " td.title .wkm", button="right")                                     # the row's menu
        b.wait(f'!!document.querySelector("{MENU}")')
        self.assertIn("Client-visible", self.menu_labels())
        self.assertEqual(b.eval(f"""[...document.querySelectorAll("{MENU} [role=menuitem]")].find(x=>x.querySelector("span").firstChild.textContent==="Client-visible").getAttribute("aria-current")"""), "true")
        self.arm()
        self.pick("Client-visible")
        self.saved()
        self.assertEqual(self.rec("actions", id_)["client_visible"], 0)

    def test_turning_on_without_messaging_opens_the_peek_and_saves_nothing(self):
        b = self.open_work()
        id_ = b.eval("A.filter(x=>!x.client&&x.st==='Open').map(x=>x.id)")[0]
        b.click(self.row(id_) + " td.title .wkm")
        self.blur()
        b.key("v")
        b.wait(f"pkOn()&&CUR&&CUR.id==={id_!r}")
        b.wait("/client messaging/.test(document.getElementById('pkNote').textContent)")
        self.assertEqual(self.rec("actions", id_)["client_visible"], 0)
        self.assertEqual(b.eval("document.getElementById('pkCv').getAttribute('aria-pressed')"), "false")


if __name__ == "__main__":
    unittest.main()
