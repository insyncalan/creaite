"""BL-256, BL-286 B: Menu, the building block for a list of commands from a button (dev/COMPONENTS.md §3), as Work's New
decision menu: its ARIA, every key in its row (↓ opens; ↑ ↓ Home End move; Enter runs; Esc closes with focus back; Tab and a
click away close), disabled items skipped, a checkbox item that stays open, a disabled button that says why, escaped text.

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


if __name__ == "__main__":
    unittest.main()
