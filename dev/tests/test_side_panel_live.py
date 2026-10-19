"""BL-78 and BL-80: the side panel, in a real browser against the real live server. BL-176 (sprint-peek): an action, RAID item or
decision is the peek now (over the page, already editable, each change staged, ⌘↵ applies and closes); new items, milestones and
health keep the form, BL-78's ⌘↵ and BL-80's width, and those tests are unchanged.

Run: python3 dev/tests/test_side_panel_live.py   (needs Google Chrome; skipped otherwise)

BL-78: ⌘+Enter (Ctrl+Enter) saves the open form and closes the panel. BL-80: the panel is 420px wide while reading and
takes half the window while editing. Each test presses real keys and clicks, then reads the database the server wrote.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

META, CTRL = 4, 2


class PanelCase(LiveBrowserCase):
    def setUp(self):
        super().setUp()
        # BL-327: under load the vault's data is over PAGE_FRESH old by the time the page loads, so the page re-reads /api/data
        # after its first paint and redraws the Work table; a redraw between the click's press and release replaces the row and
        # the click is lost (the panel never opens). Wait for that reload (and any pulse) first.
        self.b.wait("PULSE.reloads===0 && !PULSE.busy && !EVS.timer", 30)

    def action(self, id_):
        return next(r for r in self.v.rows("actions") if r["id"] == id_)

    def first_action_id(self):
        return self.b.eval("A.find(x=>OPENST(x.st)).id")

    def open_row(self, id_=None):
        b = self.b
        b.eval("go('work')")
        b.wait("document.querySelector('#workTbl tbody tr[data-row]')")
        id_ = id_ or self.first_action_id()
        b.click_until(f'#workTbl tr[data-row="{id_}"] a.rowid', "document.getElementById('panel').classList.contains('on')")   # #152: pressed again if a redraw took the click
        import time
        last = -1
        for _ in range(40):                                                                         # wait for the slide to finish
            w = b.eval("document.getElementById('panel').getBoundingClientRect().width")
            if w > 300 and w == last:
                break
            last = w
            time.sleep(0.08)
        return id_

    def edit(self, id_=None):
        """BL-176: an item opens in the peek, already editable (there is no Edit)."""
        return self.open_row(id_)

    def title(self, text):
        """Type into the peek's title, as Alan would: focus it and replace its text (the commit happens on leaving it)."""
        self.b.eval(f"(()=>{{ const t=document.getElementById('pkTitle'); t.focus(); t.textContent={text!r}; }})()")

    def set_field(self, field, value):
        self.b.eval(f"(()=>{{ const e=document.getElementById('f_{field}'); e.value={value!r}; e.dispatchEvent(new Event('input',{{bubbles:true}})); e.dispatchEvent(new Event('change',{{bubbles:true}})); }})()")

    def panel_open(self):
        return self.b.eval("document.getElementById('panel').classList.contains('on')")

    def snack(self):
        return self.b.eval("document.getElementById('snackT').textContent")

    def clear_snack(self):
        self.b.eval("document.getElementById('snackT').textContent=''")

    def wait_closed(self):
        # generous waits: on a busy machine the save, the apply and the slide can take a while (the check is the same)
        self.b.wait("!document.getElementById('panel').classList.contains('on')", 30)
        self.b.wait("document.getElementById('panel').getBoundingClientRect().width<=1", 15)          # and the slide has finished


class SaveAndClose(PanelCase):
    def test_an_action_saves_and_closes_with_command_enter(self):
        id_ = self.edit()
        before = self.action(id_)["description"]
        self.title(before + " (edited)")
        self.clear_snack()
        self.b.key("Enter", modifiers=META)                                   # BL-176: commits the title, applies, closes
        self.wait_closed()
        self.b.wait("/Applied 1 change/.test(document.getElementById('snackT').textContent)", 10)
        self.assertEqual(self.action(id_)["description"], before + " (edited)")
        self.assertEqual(self.b.errors, [])

    def test_control_enter_does_the_same(self):
        id_ = self.edit()
        before = self.action(id_)["description"]
        self.title(before + " (ctrl)")
        self.b.key("Enter", modifiers=CTRL)
        self.wait_closed()
        self.b.wait("/Applied 1 change/.test(document.getElementById('snackT').textContent)", 10)
        self.assertEqual(self.action(id_)["description"], before + " (ctrl)")

    def test_it_saves_from_a_menu_and_from_the_owner_box_without_picking_the_highlighted_person(self):
        id_ = self.edit()
        owner = self.action(id_)["owner"]
        self.b.click('#panel [data-pkp="pr"]')                                  # a picked value is staged
        self.b.wait("document.querySelector('.pkpop')")
        self.b.eval("[...document.querySelectorAll('.pkpop .pkopt')].find(o=>o.textContent.trim()==='Low').focus()")
        self.b.key("Enter")
        self.b.wait("PKS.length===1", 10)
        self.b.click('#panel [data-pkp="o"]')                                   # the owner list open, a name typed and highlighted
        self.b.wait("document.querySelector('.pkpop .pkq')")
        self.b.type("Sara Example")
        self.assertTrue(self.b.eval("!!document.querySelector('.pkpop .pkopt')"))
        self.b.key("Enter", modifiers=META)                                     # closes the list without picking, applies, closes
        self.wait_closed()
        self.b.wait("/Applied 1 change/.test(document.getElementById('snackT').textContent)", 10)
        self.assertEqual(self.action(id_)["priority"], "Low")
        self.assertEqual(self.action(id_)["owner"], owner)

    def test_nothing_changed_just_closes(self):
        id_ = self.edit()
        row = self.action(id_)
        self.clear_snack()
        self.b.key("Enter", modifiers=META)
        self.wait_closed()
        self.assertEqual(self.snack(), "Nothing to apply")                                         # BL-176: said, and nothing written
        self.assertEqual(self.action(id_), row)                                                    # and the row is untouched

    def test_a_failed_check_leaves_the_panel_open_with_the_message(self):
        """BL-176: an empty title is refused (the old one kept); an item waiting for its client messaging stays open with the
        reason, and applies once the messaging is written."""
        id_ = self.edit()
        before = self.action(id_)["description"]
        self.title("")
        self.b.eval("document.getElementById('pkTitle').blur()")
        self.b.wait("document.getElementById('pkTitle').textContent.length>0", 5)
        self.assertIn("is needed", self.b.eval("document.getElementById('pkNote').textContent"))
        self.b.eval(f"pkClient('actions','{id_}',true)")
        self.b.wait("document.activeElement&&document.activeElement.dataset.pkf==='cm'", 5)
        self.b.key("Enter", modifiers=META)
        self.b.pump(0.6)
        self.assertTrue(self.panel_open())
        self.assertIn("client messaging", self.b.eval("document.getElementById('pkNote').textContent"))
        self.assertEqual(self.action(id_)["description"], before)
        self.b.eval("document.activeElement.textContent='What it is: Data access approvals\\nWhat it means for you: UAT may slip a week\\nWhat is being done: Escalated to the CIO'")
        self.b.key("Enter", modifiers=META)
        self.wait_closed()
        self.b.wait("/Applied 1 change/.test(document.getElementById('snackT').textContent)", 10)
        self.assertEqual(self.action(id_)["client_visible"], 1)

    def test_a_new_item_is_created_and_the_panel_closes(self):
        b = self.b
        b.eval("go('work')")
        b.wait("document.querySelector('#workTbl tbody tr[data-row]')")
        n = len(self.v.rows("actions"))
        b.eval("PROJF.clear(); PROJF.add('ABC'); renderWork()")              # BL-179: New is the peek, with the page's project
        b.click("#newBtn")
        b.wait("CUR&&CUR.mode==='new'&&document.activeElement.id==='pkTitle'")
        b.type("A brand new action")
        b.key("Enter", modifiers=META)
        self.wait_closed()
        b.wait("/created/.test(document.getElementById('snackT').textContent)", 10)
        self.assertEqual(len(self.v.rows("actions")), n + 1)

    def test_it_does_nothing_on_key_repeat(self):
        """BL-176: there is no read view; a held key doesn't apply."""
        id_ = self.open_row()
        self.b.eval(f"pkCommit('actions','{id_}',{{t:'Held key'}},'Action','','')")
        self.b.wait("PKS.length===1", 10)
        self.b.eval("document.getElementById('pkTitle').dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',metaKey:true,ctrlKey:true,repeat:true,bubbles:true}))")
        self.b.pump(0.4)
        self.assertTrue(self.panel_open())                                                          # a held key does not apply
        self.assertNotEqual(self.action(id_)["description"], "Held key")
        self.assertEqual(self.b.eval("PKS.length"), 1)

    def test_it_does_not_fire_from_the_ask_creaite_box(self):
        id_ = self.edit()
        self.b.eval(f"pkCommit('actions','{id_}',{{pr:'Low'}},'Priority','','')")
        self.b.wait("PKS.length===1", 10)
        self.b.eval("openChat()")
        self.b.click("#chIn")
        self.b.key("Enter", modifiers=META)
        self.b.pump(0.4)
        self.assertTrue(self.panel_open())
        self.assertEqual(self.b.eval("PKS.length"), 1)

    def test_a_milestone_saves_and_closes_and_a_bad_value_keeps_it_open(self):
        """BL-186: a milestone opens in its editor (the peek's place), where each change saves on its own; Esc closes it."""
        b = self.b
        b.eval("MVAUD='int'; go('cockpit','ABC')")   # BL-244: Client is the first-visit view; internal milestones show in Internal view
        b.wait("document.querySelector('#v-cockpit .mv-prow[data-mvedit]')")
        b.click("#v-cockpit .mv-prow[data-mvedit]")
        b.wait("document.getElementById('mvName')&&!document.getElementById('mvPeek').hidden")
        b.eval("const n=document.getElementById('mvNum'); n.value='150'; n.dispatchEvent(new Event('change',{bubbles:true}))")
        self.assertIn("0 to 100", b.eval("document.getElementById('snackT').textContent"))   # refused, nothing saved, still open
        self.assertFalse(b.eval("document.getElementById('mvPeek').hidden"))
        name = b.eval("document.getElementById('mvName').value")
        b.eval("document.getElementById('mvName').focus()")
        b.key("End")
        b.type(" v2")
        b.key("Enter")
        b.wait("/renamed|saved and applied/.test(document.getElementById('snackT').textContent)", 10)
        for _ in range(100):
            if name + " v2" in [m["name"] for m in self.v.rows("milestones")]:
                break
            b.pump(0.2)
        self.assertIn(name + " v2", [m["name"] for m in self.v.rows("milestones")])
        b.key("Escape")
        b.wait("document.getElementById('mvPeek').hidden")

    def test_health_saves_and_closes(self):
        b = self.b
        b.eval("go('cockpit','ABC')")
        b.wait("document.querySelector('#v-cockpit [data-edproj]')")
        b.click("#v-cockpit [data-edproj]")
        b.wait("document.getElementById('f_health')")
        b.eval("(()=>{ const s=document.getElementById('f_health'); s.value='At risk'; s.dispatchEvent(new Event('change',{bubbles:true})); })()")
        self.set_field("reason", "Data access is late")
        b.key("Enter", modifiers=META)
        self.wait_closed()
        b.wait("/health/.test(document.getElementById('snackT').textContent)", 10)
        self.assertEqual(next(p for p in self.v.rows("projects") if p["code"] == "ABC")["health"], "At risk")

    def test_a_proposal_in_review_is_saved_never_approved(self):
        b = self.b
        b.eval("go('review',null,{legacy:true})")
        b.wait("document.querySelector('#reviewBody tr[data-n]')")
        n = b.eval("REV.find(r=>!r.done&&r.kind==='actions').n")
        b.click(f'#reviewBody tr[data-n="{n}"] td.title', count=2)
        b.wait("EDITING && CUR.mode==='proposal'")
        self.title("Edited in review")                                         # BL-177: the peek layout, Save on ⌘↵
        b.key("Enter", modifiers=META)
        self.wait_closed()
        self.assertEqual(b.eval(f"[REV.find(r=>r.n=={n}).done||false, REV.find(r=>r.n=={n}).rec.t]"), [False, "Edited in review"])   # still waiting
        self.assertTrue(b.eval(f"REV.some(r=>r.n=={n}&&!r.done)"))

    def test_the_footer_says_so_only_while_editing(self):
        """BL-176: the peek has no "⌘↵ saves and closes" line; the staging bar's Apply shows the key instead."""
        id_ = self.open_row()
        self.assertEqual(self.b.eval("document.getElementById('pKeys').getBoundingClientRect().height"), 0)
        self.b.eval(f"pkCommit('actions','{id_}',{{pr:'Low'}},'Priority','','')")
        self.b.wait("!document.getElementById('pkStage').hidden", 10)
        self.assertIn(self.b.eval("MOD+'↵'"), self.b.eval("document.getElementById('pkApply').textContent"))

    # ===== BL-169 (sprint-polish-2) =====
    def keys_shown(self):
        return self.b.eval("document.getElementById('pKeys').getBoundingClientRect().height>0")

    def test_the_hint_waits_for_a_change(self):
        """BL-169, on the form that keeps it (project health; work items are the peek, milestones their editor, BL-186)."""
        b = self.b
        b.eval("go('cockpit','ABC')")
        b.wait("document.querySelector('#v-cockpit [data-edproj]')")
        b.click("#v-cockpit [data-edproj]")
        b.wait("document.getElementById('f_reason')")
        self.assertFalse(self.keys_shown())
        for _ in range(2):                                       # moving through the fields changes nothing
            b.key("Tab")
        self.assertFalse(self.keys_shown())
        b.eval("document.getElementById('f_reason').focus()")
        self.assertFalse(self.keys_shown())
        b.type(" more")
        self.assertTrue(self.keys_shown())
        fields = b.eval("document.getElementById('pBody').getBoundingClientRect().bottom")             # the fields' scrolling frame
        hint = b.eval("document.getElementById('pKeys').getBoundingClientRect().top")
        self.assertGreaterEqual(hint, fields - 1)                   # under the fields, never over one

    def test_a_new_item_shows_it_on_its_first_field(self):
        """BL-186: a new milestone opens in its editor with the cursor in its name, and there is no key line to show."""
        b = self.b
        b.eval("openNewMilestone('ABC')")
        b.wait("MV.add&&document.activeElement&&document.activeElement.id==='mvName'")
        self.assertFalse(self.keys_shown())
    # ===== end BL-169 =====


class WidePanel(PanelCase):
    """BL-80 for the forms that keep it (half the window, never less than the reading width); BL-176: the peek is half the window
    (never under 520px) whenever it is open, over the page, which keeps its room."""

    def width(self, expect=None):
        b = self.b
        if expect is not None:
            b.wait(f"Math.abs(document.getElementById('panel').getBoundingClientRect().width-{expect})<=1", 4)
        return round(b.eval("document.getElementById('panel').getBoundingClientRect().width"))

    def test_the_peek_is_half_the_window_and_never_under_520(self):
        for window, want in ((1400, 700), (1200, 600), (1000, 520), (700, 520)):
            self.b.resize(window, 900)
            # the rail starts collapsed below 1200px on the media query's change event, which Chrome sends at the next frame, not on
            # the resize; under load the click was aimed before the rail narrowed, so the table moved 156px left under it and the
            # press landed on another cell (an inline edit, no panel)
            self.b.wait(f"innerWidth==={window} && document.documentElement.classList.contains('railicons')==={str(window < 1200).lower()}")
            self.open_row()
            self.assertAlmostEqual(self.width(want), want, delta=1, msg=f"at {window}px")
            self.assertFalse(self.b.eval("EDITING"))
            self.b.key("Escape")                                              # #108, #161: one Esc clears the highlight and closes the peek
            self.b.wait("document.querySelectorAll('#workTbl tr.hl').length===0")
            self.wait_closed()
            self.assertLessEqual(self.width(), 1)

    def test_every_kind_of_panel_widens_and_returns(self):
        b = self.b
        b.resize(1400, 900)
        # a new item: the peek (BL-179), the same half
        b.eval("go('work')")
        b.wait("document.querySelector('#workTbl tbody tr[data-row]')")
        b.click("#newBtn")
        b.wait("CUR&&CUR.mode==='new'")
        self.assertAlmostEqual(self.width(700), 700, delta=1)
        b.click("#pkClose")
        self.wait_closed()
        self.assertLessEqual(self.width(), 1)                                   # closed: just the border
        # a milestone, then health, from the project page
        b.eval("MVAUD='int'; go('cockpit','ABC')")   # BL-244: Client is the first-visit view; internal milestones show in Internal view
        b.wait("document.querySelector('#v-cockpit .mv-prow[data-mvedit]')")
        b.click("#v-cockpit .mv-prow[data-mvedit]")                          # BL-186: the milestone editor, in the peek's place and size
        b.wait("!document.getElementById('mvPeek').hidden")
        self.assertAlmostEqual(round(b.eval("document.getElementById('mvPeek').getBoundingClientRect().width")), 700, delta=1)
        b.key("Escape")
        b.wait("document.getElementById('mvPeek').hidden")
        b.click("#v-cockpit [data-edproj]")
        b.wait("document.getElementById('f_health')")
        self.assertAlmostEqual(self.width(700), 700, delta=1)
        b.click("#pCancel")
        self.wait_closed()
        # a proposal in Review: the peek (BL-177), the same half
        b.eval("go('review',null,{legacy:true})")
        b.wait("document.querySelector('#reviewBody tr[data-n]')")
        n = b.eval("REV.find(r=>!r.done&&r.kind==='actions').n")
        b.click(f'#reviewBody tr[data-n="{n}"] td.title', count=2)
        b.wait("EDITING && CUR.mode==='proposal'")
        self.assertAlmostEqual(self.width(700), 700, delta=1)
        b.click("#pkCancel")
        self.wait_closed()

    def test_the_expand_icon_takes_it_to_full_width_and_back(self):
        b = self.b
        b.resize(1400, 900)
        self.edit()
        self.assertEqual(b.eval("document.querySelectorAll('#pEdit,#pSave,#pCancel').length"), 0)   # no Edit, Save or Cancel
        b.click("#pkExpand")
        rail = round(b.eval("document.querySelector('.rail').getBoundingClientRect().width"))
        self.assertAlmostEqual(self.width(1400 - rail), 1400 - rail, delta=1)
        b.click("#pkExpand")
        self.assertAlmostEqual(self.width(700), 700, delta=1)

    def test_the_list_keeps_its_room_and_the_selected_row(self):
        b = self.b
        b.resize(1400, 900)
        b.eval("go('work')")
        b.wait("document.querySelector('#workTbl tbody tr[data-row]')")
        before = b.eval("document.getElementById('v-work').getBoundingClientRect().width")
        id_ = self.open_row()
        self.width(700)
        after = b.eval("document.getElementById('v-work').getBoundingClientRect().width")
        self.assertAlmostEqual(before, after, delta=1)                          # BL-176: over the page, nothing gives up room
        self.assertTrue(b.eval(f"document.querySelector('#workTbl tr[data-row=\"{id_}\"]').classList.contains('sel')"))     # still marked

    def test_ask_creaite_and_the_peek_do_not_overlap(self):
        b = self.b
        b.resize(1400, 900)
        self.edit()
        b.eval("openChat()")
        b.wait("document.getElementById('chat').classList.contains('on')")
        b.wait("(()=>{ const p=document.getElementById('panel').getBoundingClientRect(), c=document.getElementById('chat').getBoundingClientRect(); return p.right<=c.left+1&&p.width>300; })()", 4)
        p = b.eval("(()=>{ const p=document.getElementById('panel').getBoundingClientRect(), c=document.getElementById('chat').getBoundingClientRect(); return [p.right, c.left, p.width, c.width]; })()")
        self.assertLessEqual(p[0], p[1] + 1)                                    # the peek ends where the chat begins
        self.assertGreaterEqual(round(p[2]), 520)                               # half of what is left, never under 520
        self.assertGreater(p[3], 300)                                           # and the chat keeps its width


if __name__ == "__main__":
    unittest.main()
