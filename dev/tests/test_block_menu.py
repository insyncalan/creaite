"""BL-256, BL-286 B: Menu, the building block for a list of commands from a button (dev/COMPONENTS.md §3), as Work's New
decision menu: its ARIA, every key in its row (↓ opens; ↑ ↓ Home End move; Enter runs; Esc closes with focus back; Tab and a
click away close), disabled items skipped, a checkbox item that stays open, a disabled button that says why, escaped text.
BL-316: the props the moved menus need (a "…" button named by aria-label, no chevron, ids, plain items, headings and notes,
a tooltip on an item, a hidden button), openMenu (a menu from a control already in the page or at the pointer, aligned right,
and its loading state), and MenuPanel (its owner's keys first; a text field's keys left to the field).

Run: python3 dev/tests/test_block_menu.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

MOUNT = """(why=>{ document.getElementById('mfix')?.remove(); const box=document.createElement('div'); box.id='mfix';
  box.style.cssText='position:fixed;top:80px;left:80px;z-index:500;background:var(--surface)'; document.body.appendChild(box);
  window.PICKED=[]; window.BLOCKED=0; window.CHK=false;
  const draw=()=>mountMenu(box,{label:'Draft agenda', icon:'spark', data:{agenda:'1'}, why, onBlocked:()=>{ BLOCKED++; },
    items:[{id:'a', icon:'list', name:'POAD', line:'The <b>full</b> structure', mark:'last used'},
           {id:'b', icon:'list', name:'Off', disabled:true},
           {id:'c', icon:'filetext', name:'POAD lite'},
           {id:'s', sep:true},
           {id:'d', icon:'people', name:'Include who\\'s invited', checked:CHK}],
    onPick:id=>{ PICKED.push(id); if(id==='d'){ CHK=!CHK; draw(); } }});
  draw(); })"""
BTN = "#mfix button[aria-haspopup]"
ACTIVE = "(document.activeElement&&document.activeElement.textContent)"


class MenuBlock(LiveBrowserCase):
    shared_server = True

    def mount(self, why=""):
        b = self.b
        b.eval(f"{MOUNT}({why!r})")
        b.wait(f"document.querySelector('{BTN}')")
        return b

    def is_open(self):
        return self.b.eval("!!document.querySelector('#mfix [role=menu]')")

    def test_aria_and_opening_by_click(self):
        b = self.mount()
        self.assertEqual(b.eval(f"document.querySelector('{BTN}').getAttribute('aria-expanded')"), "false")
        self.assertEqual(b.eval(f"document.querySelector('{BTN}').dataset.agenda"), "1")
        b.click(BTN)
        b.wait("document.querySelector('#mfix [role=menu]')")
        self.assertEqual(b.eval(f"document.querySelector('{BTN}').getAttribute('aria-expanded')"), "true")
        self.assertEqual(b.eval("document.querySelector('#mfix [role=menu]').getAttribute('aria-label')"), "Draft agenda")
        roles = b.eval("[...document.querySelectorAll('#mfix [role=menu] > *')].map(e=>e.getAttribute('role'))")
        self.assertEqual(roles, ["menuitem", "menuitem", "menuitem", "separator", "menuitemcheckbox"])
        self.assertIn("POAD", b.eval(ACTIVE))                                    # focus on the first item
        self.assertIn("· last used", b.eval("document.querySelector('#mfix [role=menuitem]').textContent"))

    def test_keys_move_skip_disabled_and_run(self):
        b = self.mount()
        b.eval(f"document.querySelector('{BTN}').focus()")
        b.key("ArrowDown")                                                        # opens
        b.wait("document.querySelector('#mfix [role=menu]')")
        b.key("ArrowDown")
        self.assertIn("POAD lite", b.eval(ACTIVE))                                # the disabled one is skipped
        b.key("End")
        self.assertIn("Include", b.eval(ACTIVE))
        b.key("ArrowDown")
        self.assertIn("The <b>full</b>", b.eval(ACTIVE))                          # wraps; the text is escaped, not markup
        b.key("Home")
        b.key("ArrowUp")
        self.assertIn("Include", b.eval(ACTIVE))
        b.key("Home")
        b.key("Enter")
        b.wait("!document.querySelector('#mfix [role=menu]')")
        self.assertEqual(b.eval("PICKED"), ["a"])

    def test_escape_closes_with_focus_back_and_tab_and_a_click_away_close(self):
        b = self.mount()
        b.click(BTN)
        b.wait("document.querySelector('#mfix [role=menu]')")
        b.key("Escape")
        b.wait("!document.querySelector('#mfix [role=menu]')")
        self.assertEqual(b.eval("document.activeElement===document.querySelector('%s')" % BTN), True)
        b.click(BTN)
        b.wait("document.querySelector('#mfix [role=menu]')")
        b.key("Tab")
        b.wait("!document.querySelector('#mfix [role=menu]')")
        b.click(BTN)
        b.wait("document.querySelector('#mfix [role=menu]')")
        b.click("#v-today")
        b.wait("!document.querySelector('#mfix [role=menu]')")
        self.assertEqual(b.eval("PICKED"), [])

    def test_a_checkbox_item_toggles_and_stays_open(self):
        b = self.mount()
        b.click(BTN)
        b.click("#mfix [role=menuitemcheckbox]")
        b.wait("document.querySelector('#mfix [role=menuitemcheckbox]').getAttribute('aria-checked')==='true'")
        self.assertTrue(self.is_open())
        self.assertEqual(b.eval("PICKED"), ["d"])
        b.click("#mfix [role=menuitem]:not([aria-disabled])")
        self.assertFalse(self.is_open())

    def test_a_disabled_button_says_why_and_never_opens(self):
        b = self.mount("Drafting needs the live server")
        btn = f"document.querySelector('{BTN}')"
        self.assertEqual(b.eval(f"{btn}.getAttribute('aria-disabled')"), "true")
        self.assertEqual(b.eval(f"{btn}.dataset.tip"), "Drafting needs the live server")
        b.click(BTN)
        self.assertFalse(self.is_open())
        self.assertEqual(b.eval("BLOCKED"), 1)


    # ---- BL-316 ----
    def test_a_symbol_button_with_plain_items_headings_and_notes(self):
        b = self.b
        b.eval("""(()=>{ document.getElementById('mfix')?.remove(); const box=document.createElement('div'); box.id='mfix';
          box.style.cssText='position:fixed;top:80px;left:80px;z-index:500'; document.body.appendChild(box); window.PICKED=[];
          mountMenu(box,{label:'…', ariaLabel:'Options: the <i>report</i>', chevron:false, id:'mbtn', btnCls:'dots', labelCls:'w',
            menuId:'mmenu', menuCls:'extra', onPick:id=>PICKED.push(id),
            items:[{id:'h', head:'Status'}, {id:'run', name:'Run now', disabled:true, tip:'Needs the live server'},
                   {id:'s', name:'Dismiss'}, {id:'n', note:'Nothing else'}]}); })()""")
        b.wait("document.getElementById('mbtn')")
        self.assertEqual(b.eval("document.getElementById('mbtn').getAttribute('aria-label')"), "Options: the <i>report</i>")
        self.assertFalse(b.eval("!!document.querySelector('#mbtn .nch')"))                          # no chevron
        self.assertEqual(b.eval("document.querySelector('#mbtn span.w').textContent"), "…")
        b.click("#mbtn")
        b.wait("document.getElementById('mmenu')")
        self.assertTrue(b.eval("document.getElementById('mmenu').classList.contains('extra')"))
        self.assertEqual(b.eval("document.getElementById('mmenu').getAttribute('aria-label')"), "Options: the <i>report</i>")
        self.assertEqual(b.eval("[...document.querySelectorAll('#mmenu [role=menuitem]')].map(x=>[x.innerHTML,x.dataset.tip||''])"),
                         [["Run now", "Needs the live server"], ["Dismiss", ""]])                     # plain words, no <b>
        self.assertEqual(b.eval("[document.querySelector('#mmenu .fsec2').textContent, document.querySelector('#mmenu .mnote').textContent]"),
                         ["Status", "Nothing else"])                                                  # words, not items
        self.assertIn("Dismiss", b.eval(ACTIVE))                                                       # the disabled one is skipped
        b.key("Escape")
        b.eval("mountMenu(document.getElementById('mfix'),{label:'…', id:'mbtn', hidden:true, items:[], onPick:()=>{}})")
        b.wait("document.getElementById('mbtn').hidden")

    OPEN = """(o=>{ closeMenu(); document.getElementById('mfix')?.remove(); const box=document.createElement('div'); box.id='mfix';
      box.style.cssText='position:fixed;top:80px;left:'+(o.left||80)+'px;z-index:500'; document.body.appendChild(box);
      const a=document.createElement('button'); a.id='anc'; a.textContent='Open'; a.setAttribute('aria-haspopup','menu'); a.setAttribute('aria-expanded','false');
      const after=document.createElement('button'); after.id='after'; after.textContent='After'; box.append(a, after); window.PICKED=[]; window.CLOSED=[];
      a.onclick=()=>{ if(menuOpenFor(a)){ closeMenu(); return; }
        openMenu(a,{label:'Move <b>it</b> to', id:'pmenu', align:o.align, at:o.at, onPick:id=>PICKED.push(id), onClose:h=>CLOSED.push(h),
          items:[{id:'a', name:'This week', data:{bto:'week'}}, {id:'b', name:'Later', icon:'calendar', line:'After next week'}]}); }; a.focus(); })"""

    def open_at(self, align="left", at="undefined", left=80):
        b = self.b
        b.eval(f"{self.OPEN}({{align:'{align}', at:{at}, left:{left}}})")
        b.key("Enter")
        b.wait("document.getElementById('pmenu')")
        return b

    def test_open_menu_from_a_control_in_the_page(self):
        b = self.open_at()
        self.assertEqual(b.eval("document.getElementById('anc').getAttribute('aria-expanded')"), "true")
        self.assertEqual(b.eval("document.getElementById('pmenu').getAttribute('role')"), "menu")
        self.assertEqual(b.eval("document.getElementById('pmenu').getAttribute('aria-label')"), "Move <b>it</b> to")
        self.assertIn("This week", b.eval(ACTIVE))
        self.assertEqual(b.eval("document.querySelector('#pmenu [data-bto]').dataset.bto"), "week")
        self.assertEqual(b.eval("getComputedStyle(document.getElementById('pmenu')).position"), "fixed")
        r = b.eval("(()=>{ const m=document.getElementById('pmenu').getBoundingClientRect(), a=document.getElementById('anc').getBoundingClientRect(); return [Math.round(m.left-a.left), m.top>=a.bottom]; })()")
        self.assertEqual(r, [0, True])                                                                # under its control
        b.key("ArrowDown")
        self.assertIn("Later", b.eval(ACTIVE))
        b.key("Home")
        self.assertIn("This week", b.eval(ACTIVE))
        b.key("Escape")
        b.wait("!document.getElementById('pmenu')")
        self.assertEqual(b.eval("[document.activeElement.id, document.getElementById('anc').getAttribute('aria-expanded'), CLOSED]"),
                         ["anc", "false", ["esc"]])
        b.key("Enter")                                                                                # again: Tab closes, focus moves on
        b.wait("document.getElementById('pmenu')")
        b.key("Tab")
        b.wait("!document.getElementById('pmenu')")
        self.assertEqual(b.eval("document.activeElement.id"), "after")
        b.eval("document.getElementById('anc').focus()")
        b.key("Enter")
        b.wait("document.getElementById('pmenu')")
        b.key("ArrowDown")
        b.key("Enter")                                                                                # picks, and closes
        b.wait("!document.getElementById('pmenu')")
        self.assertEqual(b.eval("PICKED"), ["b"])
        b.click("#anc")
        b.wait("document.getElementById('pmenu')")
        b.click("#anc")                                                                               # its control again: closed
        b.wait("!document.getElementById('pmenu')")
        b.click("#anc")
        b.wait("document.getElementById('pmenu')")
        b.click("#v-today")                                                                           # a click away
        b.wait("!document.getElementById('pmenu')")

    def test_open_menu_aligned_right_and_at_the_pointer(self):
        b = self.open_at("right", left=500)
        self.assertEqual(b.eval("(()=>{ const m=document.getElementById('pmenu').getBoundingClientRect(), a=document.getElementById('anc').getBoundingClientRect(); return Math.round(m.right-a.right); })()"), 0)
        b = self.open_at("left", "{x:300, y:200}")
        self.assertEqual(b.eval("(r=>[Math.round(r.left), Math.round(r.top)])(document.getElementById('pmenu').getBoundingClientRect())"), [300, 200])
        b.eval("closeMenu()")

    def test_open_menu_while_loading_then_with_its_items(self):
        b = self.b
        b.eval(self.OPEN + "({})")
        b.eval("openMenu(document.getElementById('anc'),{label:'History', id:'pmenu', loading:true, items:[], onPick:()=>{}})")
        b.wait("document.querySelector('#pmenu .msk')")
        b.eval("openMenu(document.getElementById('anc'),{label:'History', id:'pmenu', items:[{id:'x', name:'A chat', line:'2 messages'}], onPick:id=>PICKED.push(id)})")
        b.wait("!document.querySelector('#pmenu .msk')")
        self.assertIn("A chat", b.eval(ACTIVE))                                                       # focus to its first item
        self.assertEqual(b.eval("document.querySelectorAll('.pophost').length"), 1)                   # redrawn, not opened twice
        b.key("Escape")
        b.wait("!document.getElementById('pmenu')")

    def test_menu_panel_runs_its_owners_keys_first_and_leaves_a_field_its_own(self):
        b = self.b
        b.eval("""(()=>{ closeMenu(); document.getElementById('mfix')?.remove(); const box=document.createElement('div'); box.id='mfix';
          box.style.cssText='position:fixed;top:80px;left:80px;z-index:500'; document.body.appendChild(box); window.CLOSED=[]; window.KEYS=[];
          mountMenuPanel(box,{label:'Reasons', id:'mpanel', bare:true, cls:'mine', onClose:h=>CLOSED.push(h),
            onKey:e=>{ KEYS.push(e.key); if(e.key==='1'){ e.preventDefault(); } if(e.key==='Escape'&&window.STAGE){ e.preventDefault(); } }},
            [{id:'a', name:'One'}, {id:'b', name:'Two'}], true); })()""")
        b.wait("document.getElementById('mpanel')")
        self.assertEqual(b.eval("document.getElementById('mpanel').className"), "mine")                 # bare: its own look
        self.assertIn("One", b.eval(ACTIVE))
        b.key("ArrowDown")
        self.assertIn("Two", b.eval(ACTIVE))
        b.key("1")
        self.assertEqual(b.eval("KEYS"), ["ArrowDown", "1"])
        b.eval("window.STAGE=1")
        b.key("Escape")                                                                               # used up by its owner
        self.assertEqual(b.eval("CLOSED"), [])
        b.eval("document.querySelector('#mpanel input').focus()")
        b.key("Home")                                                                                 # the field's own
        self.assertEqual(b.eval("document.activeElement.tagName"), "INPUT")
        b.eval("window.STAGE=0")
        b.key("Escape")
        self.assertEqual(b.eval("CLOSED"), ["esc"])
        b.eval("document.getElementById('mfix').remove()")


if __name__ == "__main__":
    unittest.main()
