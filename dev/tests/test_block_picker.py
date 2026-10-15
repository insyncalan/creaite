"""BL-316: Picker, Combobox and Peek, the building blocks for choosing a value, typing to choose and a side peek's frame
(dev/COMPONENTS.md §3), each on a small fixture in the real page: their ARIA, every key in their row, focus return, a click
away, and that their text is escaped.

Run: python3 dev/tests/test_block_picker.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

FIX = """(()=>{ document.getElementById('pfix')?.remove(); const box=document.createElement('div'); box.id='pfix';
  box.style.cssText='position:fixed;top:80px;left:80px;z-index:500;background:var(--surface)';
  box.innerHTML='<button type="button" id="pbtn" aria-haspopup="listbox" aria-expanded="false">Choose</button><button type="button" id="after">After</button><div id="chost"></div>';
  document.body.appendChild(box); window.PICKED=[]; window.CLOSED=[]; })()"""
LIST = """openPicker(document.getElementById('pbtn'),{label:'Fruit',value:'b',search:SEARCH,allowNew:true,
  options:[{v:'a',label:'Apple <b>x</b>',icon:'check',hint:'red'},{v:'b',label:'Banana'},{v:'c',label:'Cherry',disabled:true},{v:'d',label:'Date',id:'optD'}],
  onPick:(v,t)=>PICKED.push([v,!!t]),onClose:h=>{ CLOSED.push(h); }})"""
ACTIVE = "(document.activeElement&&(document.activeElement.id||document.activeElement.textContent))"


class PickerBlock(LiveBrowserCase):
    shared_server = True

    def open_list(self, search=False):
        b = self.b
        b.eval(FIX)
        b.eval(f"document.getElementById('pbtn').focus(); {LIST.replace('SEARCH', 'true' if search else 'false')}")
        b.wait("document.querySelector('.pkpop [role=listbox]')")
        return b

    def test_list_aria_keys_pick_and_escape(self):
        b = self.open_list()
        self.assertEqual(b.eval("document.getElementById('pbtn').getAttribute('aria-expanded')"), "true")
        self.assertEqual(b.eval("document.querySelector('.pkpop [role=listbox]').getAttribute('aria-label')"), "Fruit")
        self.assertEqual(b.eval(ACTIVE), "Banana")                                   # the chosen one has focus
        self.assertEqual(b.eval("document.querySelector('.pkpop .pkopt').textContent"), "Apple <b>x</b>red")   # escaped
        self.assertTrue(b.eval("!!PKPOP&&pickerOpenFor(document.getElementById('pbtn'))"))
        b.key("ArrowDown")
        self.assertEqual(b.eval(ACTIVE), "optD")                                     # the disabled one is skipped
        b.key("ArrowDown")
        self.assertIn("Apple", b.eval(ACTIVE))                                       # wraps
        b.key("End")
        self.assertEqual(b.eval(ACTIVE), "optD")
        b.key("Escape")
        b.wait("!document.querySelector('.pkpop')")
        self.assertEqual(b.eval("document.activeElement.id"), "pbtn")
        self.assertEqual(b.eval("document.getElementById('pbtn').getAttribute('aria-expanded')"), "false")
        self.assertEqual(b.eval("CLOSED"), ["esc"])
        self.open_list()
        b.key("Enter")
        b.wait("!document.querySelector('.pkpop')")
        self.assertEqual(b.eval("PICKED"), [["b", False]])
        self.assertEqual(b.eval("document.activeElement.id"), "pbtn")

    def test_search_no_match_use_typed_tab_and_click_away(self):
        b = self.open_list(search=True)
        self.assertEqual(b.eval("document.activeElement.className"), "pkq")
        b.eval("const q=document.querySelector('.pkq'); q.value='zz'; q.dispatchEvent(new Event('input',{bubbles:true}))")
        b.wait("document.querySelector('[data-new]')")
        self.assertIn("Use “zz”", b.eval("document.querySelector('[data-new]').textContent"))
        b.key("Enter")
        b.wait("!document.querySelector('.pkpop')")
        self.assertEqual(b.eval("PICKED"), [["zz", True]])
        self.open_list(search=True)
        b.key("Tab")
        b.wait("!document.querySelector('.pkpop')")
        self.assertIn(b.eval("document.activeElement.id"), ("pbtn", "after"))      # moved on from the control
        self.open_list()
        b.click("#after")
        b.wait("!document.querySelector('.pkpop')")
        self.assertEqual(b.eval("CLOSED.slice(-1)[0]"), "away")

    def test_date_picker_is_a_dialog_with_arrows_typed_and_escape(self):
        b = self.b
        b.eval(FIX)
        b.eval("document.getElementById('pbtn').focus(); openDatePicker(document.getElementById('pbtn'),{value:'2026-10-14',label:'Due date',"
               "parse:t=>/^\\d\\d-\\d\\d-\\d{4}$/.test(t)?toIso(t):null,weekend:iso=>[5,6].includes((new Date(iso+'T00:00:00Z').getUTCDay()+6)%7),"
               "onPick:v=>PICKED.push(v)})")
        b.wait("document.querySelector('.pkpop.pkcal')")
        self.assertEqual(b.eval("document.querySelector('.pkpop').getAttribute('role')"), "dialog")
        self.assertEqual(b.eval("document.activeElement.dataset.d"), "2026-10-14")
        b.key("ArrowRight")
        self.assertEqual(b.eval("document.activeElement.dataset.d"), "2026-10-15")
        b.key("ArrowDown")
        b.key("ArrowDown")
        b.key("ArrowDown")
        self.assertEqual(b.eval("document.activeElement.dataset.d"), "2026-11-05")    # across the month
        self.assertIn("November", b.eval("document.querySelector('.pkcalh b').textContent"))
        self.assertIn("weekend", b.eval("document.querySelector('.pkday[data-d=\"2026-11-07\"]').getAttribute('aria-label')"))
        b.eval("const t=document.querySelector('.pkdt'); t.focus(); t.value='nonsense'")
        b.key("Enter")
        b.wait("document.querySelector('.pkdt.bad')")
        self.assertTrue(b.eval("document.querySelector('.pkerr').textContent.length>0"))
        b.eval("document.querySelector('.pkdt').value='20-10-2026'")
        b.key("Enter")
        b.wait("!document.querySelector('.pkpop')")
        self.assertEqual(b.eval("PICKED"), ["2026-10-20"])
        b.eval("openDatePicker(document.getElementById('pbtn'),{label:'Due date',parse:()=>null,onPick:v=>PICKED.push(v)})")
        b.wait("document.querySelector('.pkpop.pkcal')")
        b.key("Escape")
        b.wait("!document.querySelector('.pkpop')")
        self.assertEqual(b.eval("document.activeElement.id"), "pbtn")

    def test_popover_focus_escape_and_the_html_shim(self):
        b = self.b
        b.eval(FIX)
        b.eval("const el=openPopover(document.getElementById('pbtn'),{label:'New one',id:'popX',cls:'pkws'});"
               "const i=document.createElement('input'); el.appendChild(i); i.focus()")
        b.wait("document.getElementById('popX')")
        self.assertEqual(b.eval("document.getElementById('popX').getAttribute('role')"), "dialog")
        self.assertEqual(b.eval("document.getElementById('popX').getAttribute('aria-label')"), "New one")
        b.key("Escape")
        b.wait("!document.getElementById('popX')")
        self.assertEqual(b.eval("document.activeElement.id"), "pbtn")
        b.eval("htmlPopover(document.getElementById('pbtn'),'rvmv','<p class=\"z\">Hi</p>')")
        self.assertTrue(b.eval("!!document.querySelector('.pkpop.rvmv p.z')"))
        b.eval("closePicker('owner',false)")
        self.assertFalse(b.eval("!!document.querySelector('.pkpop')"))


class ComboboxBlock(LiveBrowserCase):
    shared_server = True

    def mount(self):
        b = self.b
        b.eval(FIX)
        b.eval("""window.REMOVED=[]; mountCombobox(document.getElementById('chost'),{id:'cb',label:'Owner',value:'',
          options:(q)=>['Ann <i>A</i>','Bob','Cat'].filter(n=>!q||n.toLowerCase().includes(q.toLowerCase())).map((n,i)=>({v:n,label:n,sub:i?'':'3 items',head:i===0?'Mine':'',remove:()=>REMOVED.push(n)})),
          onPick:o=>{ PICKED.push(o.v); }})""")
        b.wait("document.getElementById('cb')")
        return b

    def test_aria_keys_pick_escape_clears(self):
        b = self.mount()
        b.click("#cb")                                                                             # focus in opens it
        b.wait("document.querySelector('.combo.open')")
        inp = "document.getElementById('cb')"
        self.assertEqual(b.eval(f"{inp}.getAttribute('role')"), "combobox")
        self.assertEqual(b.eval(f"{inp}.getAttribute('aria-expanded')"), "true")
        self.assertEqual(b.eval(f"{inp}.getAttribute('aria-controls')"), "cb-list")
        self.assertEqual(b.eval(f"{inp}.getAttribute('aria-activedescendant')"), "cb-o0")
        self.assertIn("Ann <i>A</i>", b.eval("document.getElementById('cb-o0').textContent"))     # escaped
        b.key("ArrowDown")
        self.assertEqual(b.eval(f"{inp}.getAttribute('aria-activedescendant')"), "cb-o1")
        self.assertEqual(b.eval("document.activeElement.id"), "cb")                               # focus stays in the field
        b.key("Enter")
        b.wait("!document.querySelector('.combo.open')")
        self.assertEqual(b.eval("PICKED"), ["Bob"])
        self.assertEqual(b.eval(f"{inp}.value"), "Bob")
        b.key("ArrowDown")
        b.wait("document.querySelector('.combo.open')")
        b.key("Escape")
        b.wait("!document.querySelector('.combo.open')")
        self.assertEqual(b.eval(f"{inp}.value"), "Bob")
        b.key("Escape")
        self.assertEqual(b.eval(f"{inp}.value"), "")                                               # a second Esc clears
        b.eval(f"{inp}.value='ca'; {inp}.dispatchEvent(new Event('input',{{bubbles:true}}))")
        b.wait("document.querySelectorAll('.combo .copt').length===1")
        self.assertTrue(b.eval("comboboxOpen()"))
        b.eval("closeCombobox()")
        b.wait("!document.querySelector('.combo.open')")


class PeekBlock(LiveBrowserCase):
    shared_server = True

    def test_frame_and_bar(self):
        b = self.b
        b.eval("document.getElementById('pkfx')?.remove()")
        self.assertTrue(b.eval("peekFrame('pkfx',{label:'Edit <milestone>',cls:'mv-peek'})===peekFrame('pkfx',{label:'x'})"))
        self.assertEqual(b.eval("[document.getElementById('pkfx').getAttribute('role'),document.getElementById('pkfx').getAttribute('aria-label'),document.getElementById('pkfx').hidden]"),
                         ["dialog", "Edit <milestone>", True])
        b.eval("window.PB=[]; drawPeekBar(document.getElementById('pkfx'),{onClose:()=>PB.push('c'),onPrev:()=>PB.push('p'),onNext:()=>PB.push('n'),prevOff:true,ids:{close:'pfC'}})")
        self.assertEqual(b.eval("document.getElementById('pfC').getAttribute('aria-label')"), "Close")
        b.eval("document.querySelectorAll('#pkfx .ib').forEach(x=>x.click())")
        self.assertEqual(b.eval("PB"), ["c", "n"])                                                 # Previous is blocked at the start
        b.eval("document.getElementById('pkfx').remove()")


if __name__ == "__main__":
    unittest.main()
