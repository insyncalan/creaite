"""BL-256, BL-316 (dev/COMPONENTS.md §3): the FilterBar building block, on a small fixture that mounts it as Work, Review and
Settings › People do (the area keeps the state and redraws the bar with drawFilterBar). A main filter is a button with a
multi-select list: its ARIA (aria-haspopup="listbox", aria-expanded, role="listbox" with aria-multiselectable, role="option"
with aria-selected), every key in its row (Enter and ↓ open; focus goes to the search or the first option; ↑ ↓ Home End
move; Space and Enter tick; Esc closes with focus back on the button; Tab and a click away close), the search over six
options, Only me, Select all (what the search shows) and Clear, "is not", and the button's words. The funnel opens the field
picker (a dialog): the main fields first, a section's heading, ↑ ↓ choosing a field, → into its options and ← back, a date
range, Done and Esc with focus back on the funnel. BL-150: unused filters fold away while the row would wrap, never a set one,
and the funnel says how many it holds. Text is escaped.

Run: python3 dev/tests/test_block_filter_bar.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

# The fixture: a toolbar holding the bar; FBX holds the state as an area would, and every change redraws the bar at once.
MOUNT = """((width)=>{ document.getElementById('fbFix')?.remove(); const bar=document.createElement('div'); bar.id='fbFix'; bar.className='toolbar';
  bar.style.cssText='position:fixed;top:70px;left:70px;z-index:500;display:flex;flex-wrap:wrap;gap:6px;background:var(--surface);width:'+width+'px';
  const q=document.createElement('input'); q.id='fbQ'; q.type='search'; q.setAttribute('aria-label','Search'); q.style.width='160px';
  const host=document.createElement('span'); host.className='wfilters'; host.id='fbBar'; bar.append(q, host); document.body.appendChild(bar);
  const ST=['Open','Delayed','Closed','Cancelled','Parked','<b>Bold</b>','Waiting','Done'];
  window.FBX={sel:{st:new Set(), o:new Set(), p:new Set(), ws:new Set()}, not:new Set(), range:{from:'',to:''}, field:'ws', query:'', log:[], fold:false};
  const opts=(k,L)=>()=>L.map((v,i)=>({value:v,label:v,count:k==='st'&&i===2?0:i+1}));
  const lab=(k,l)=>FBX.sel[k].size?`${l}: ${FBX.not.has(k)?'not ':''}${[...FBX.sel[k]].join(', ')}`:l;
  window.fbxDraw=()=>{ const f=(id,label,main,L,extra)=>({id,label,main,options:opts(id,L),selected:FBX.sel[id],not:FBX.not.has(id),on:!!FBX.sel[id].size,
      button:lab(id,label),btnId:main?id+'Btn':undefined,menuId:id+'Menu',section:main?undefined:'More fields',mark:FBX.sel[id].size?'set':'',...(extra||{})});
    drawFilterBar(host,{fields:[f('st','Status',true,ST), f('o','Owner',true,['Me','Sara','Omar'],{onlyMe:['Me']}), f('p','Project',true,['ABC','DEF']),
        f('ws','Work <i>stream</i>',false,['Build','Run']),
        {id:'dr',label:'Due between',section:'More fields',on:!!(FBX.range.from||FBX.range.to),range:{...FBX.range,name:'Due'}}],
      onSelect:(k,v)=>{ FBX.log.push(['sel',k,v]); FBX.sel[k]=new Set(v); fbxDraw(); },
      onNot:(k,n)=>{ FBX.log.push(['not',k,n]); n?FBX.not.add(k):FBX.not.delete(k); fbxDraw(); },
      onRange:(k,end,t)=>{ FBX.log.push(['range',k,end,t]); FBX.range[end]=t; fbxDraw(); },
      more:{id:'fbMore',menuId:'fbPick',label:'Add a filter',menuLabel:'Add a filter',count:0,key:'F',field:FBX.field,
        onField:k=>{ FBX.field=k; fbxDraw(); },query:FBX.query,onQuery:t=>{ FBX.query=t; fbxDraw(); },
        result:'Result: 3 of 9 shown',resultId:'fbResult',doneId:'fbDone'},
      fold:()=>FBX.fold?bar:null}); };
  fbxDraw(); })"""
ACTIVE = "(document.activeElement&&(document.activeElement.id||document.activeElement.textContent))"
OPTS = "[...document.querySelectorAll('#stMenu [role=option]')]"


class FilterBarBlock(LiveBrowserCase):
    shared_server = True

    def setUp(self):
        super().setUp()
        self.b.eval(f"{MOUNT}(900)")
        self.b.wait("document.getElementById('stBtn')")

    def expanded(self, sel):
        return self.b.eval(f"document.querySelector('{sel}').getAttribute('aria-expanded')")

    def is_open(self, menu="stMenu"):
        return self.b.eval(f"document.getElementById('{menu}').classList.contains('on')")

    def test_aria_roles_and_names(self):
        b = self.b
        self.assertEqual(b.eval("['stBtn','oBtn','pBtn'].map(i=>document.getElementById(i).getAttribute('aria-haspopup'))"), ["listbox"] * 3)
        self.assertEqual(self.expanded("#stBtn"), "false")
        self.assertEqual(b.eval("document.getElementById('stBtn').getAttribute('aria-controls')"), "stMenu")
        self.assertFalse(b.eval("!!document.getElementById('wsBtn')"))                        # a field only in + Filter has no button
        b.click("#stBtn")
        self.assertTrue(self.is_open())
        self.assertEqual(self.expanded("#stBtn"), "true")
        lb = b.eval("(()=>{ const l=document.querySelector('#stMenu [role=listbox]'); return [l.getAttribute('aria-multiselectable'),l.getAttribute('aria-label')]; })()")
        self.assertEqual(lb, ["true", "Status"])
        self.assertEqual(b.eval(f"{OPTS}.length"), 8)
        self.assertEqual(b.eval(f"{OPTS}.map(o=>o.getAttribute('aria-selected'))"), ["false"] * 8)
        self.assertEqual(b.eval(f"{OPTS}[2].className"), "dim")                                # matches nothing now
        self.assertEqual(b.eval("document.getElementById('fbMore').getAttribute('aria-haspopup')"), "dialog")
        self.assertEqual(b.eval("document.getElementById('fbMore').dataset.key"), "F")

    def test_every_key_in_a_list(self):
        b = self.b
        b.eval("document.getElementById('stBtn').focus()")
        b.key("Enter")
        b.wait("document.getElementById('stMenu').classList.contains('on')")
        self.assertTrue(b.eval("document.activeElement.matches('#stMenu input.mq')"))         # over six: the search first
        b.key("ArrowDown")
        self.assertEqual(b.eval(ACTIVE), "Open1")
        b.key("ArrowDown")
        self.assertEqual(b.eval(ACTIVE), "Delayed2")
        b.key("ArrowUp")
        self.assertEqual(b.eval(ACTIVE), "Open1")
        b.key("End")
        self.assertEqual(b.eval(ACTIVE), "Done8")
        b.key("Home")
        self.assertEqual(b.eval(ACTIVE), "Open1")
        b.key(" ")
        self.assertEqual(b.eval("FBX.log.at(-1)"), ["sel", "st", ["Open"]])
        self.assertEqual(b.eval(f"{OPTS}[0].getAttribute('aria-selected')"), "true")
        self.assertEqual(b.eval("document.getElementById('stBtn').textContent"), "Status: Open")   # the button says what is chosen
        self.assertEqual(b.eval(ACTIVE), "Open1")                                                # focus stays on the option
        b.key("ArrowDown")
        b.key("Enter")
        self.assertEqual(b.eval("FBX.log.at(-1)"), ["sel", "st", ["Open", "Delayed"]])
        b.key("Enter")
        self.assertEqual(b.eval("FBX.log.at(-1)"), ["sel", "st", ["Open"]])
        b.key("Escape")
        self.assertFalse(self.is_open())
        self.assertEqual(b.eval("document.activeElement.id"), "stBtn")
        self.assertEqual(self.expanded("#stBtn"), "false")
        b.key("ArrowDown")                                                                        # ↓ on the button opens it too
        self.assertTrue(self.is_open())
        b.key("Tab")
        self.assertFalse(self.is_open())
        self.assertEqual(self.expanded("#stBtn"), "false")
        b.click("#oBtn")                                                                          # three options: no search, the first option
        self.assertTrue(self.is_open("oMenu"))
        self.assertFalse(b.eval("!!document.querySelector('#oMenu input.mq')"))
        self.assertEqual(b.eval(ACTIVE), "Me1")
        b.click("#stBtn")                                                                         # another one closes it
        self.assertEqual([self.is_open("oMenu"), self.is_open()], [False, True])
        b.click("#fbQ")                                                                           # a click away closes it
        self.assertFalse(self.is_open())

    def test_search_select_all_clear_only_me_and_not(self):
        b = self.b
        b.click("#stBtn")
        b.type("o")
        self.assertEqual(b.eval(f"{OPTS}.map(o=>o.querySelector('input').value)"), ["Open", "Closed", "<b>Bold</b>", "Done"])
        b.click("#stMenu [data-ma=all]")
        self.assertEqual(b.eval("FBX.log.at(-1)"), ["sel", "st", ["Open", "Closed", "<b>Bold</b>", "Done"]])   # what the search shows
        self.assertEqual(b.eval("document.querySelector('#stMenu .mq').value"), "o")              # BL-62: the search text is kept
        self.assertTrue(b.eval("document.activeElement===document.querySelector('#stMenu .mq')"))  # and its focus
        self.assertEqual(b.eval("document.getElementById('stBtn').textContent"), "Status: Open, Closed, <b>Bold</b>, Done")
        b.click("#stMenu [data-ma=clear]")
        self.assertEqual(b.eval("FBX.log.at(-1)"), ["sel", "st", []])
        self.assertFalse(b.eval("!!document.querySelector('#stMenu [data-ma=me]')"))              # Only me: only where the area gives it
        b.click("#stMenu [data-neg='1']")
        self.assertEqual(b.eval("FBX.log.at(-1)"), ["not", "st", True])
        self.assertEqual(b.eval("[...document.querySelectorAll('#stMenu .seg button')].map(x=>x.getAttribute('aria-pressed'))"), ["false", "true"])
        self.assertEqual(b.eval("document.querySelector('#stMenu .isnot .sub').textContent"), "none of")
        b.click("#oBtn")
        b.click("#oMenu [data-ma=me]")
        self.assertEqual(b.eval("FBX.log.at(-1)"), ["sel", "o", ["Me"]])
        b.click("#oMenu input[data-fk=o][value=Sara]")                                            # a click on an option's box ticks it
        self.assertEqual(b.eval("FBX.log.at(-1)"), ["sel", "o", ["Me", "Sara"]])
        self.assertTrue(self.is_open("oMenu"))                                                    # and the list stays open

    def test_text_is_escaped(self):
        b = self.b
        b.click("#stBtn")
        self.assertEqual(b.eval("document.querySelectorAll('#stMenu b').length"), 0)
        self.assertIn("<b>Bold</b>", b.eval("document.getElementById('stMenu').textContent"))
        b.click("#fbMore")
        self.assertEqual(b.eval("document.querySelectorAll('#fbPick i').length"), 0)
        self.assertIn("Work <i>stream</i>", b.eval("document.getElementById('fbPick').textContent"))

    def test_the_funnel_and_its_field_picker(self):
        b = self.b
        self.assertEqual(self.expanded("#fbMore"), "false")
        b.eval("document.getElementById('fbMore').focus()")
        b.key("Enter")
        b.wait("document.getElementById('fbPick').classList.contains('on')")
        self.assertEqual(self.expanded("#fbMore"), "true")
        self.assertEqual(b.eval("[document.getElementById('fbPick').getAttribute('role'),document.getElementById('fbPick').getAttribute('aria-label')]"),
                         ["dialog", "Add a filter"])
        self.assertEqual(b.eval("document.activeElement.id"), "fpq")                               # its "Find a field…" box
        self.assertEqual(b.eval("[...document.querySelectorAll('#fbPick .fpf')].map(x=>x.dataset.fpk)"), ["st", "o", "p", "ws", "dr"])
        self.assertEqual(b.eval("[...document.querySelectorAll('#fbPick .fsec2')].map(x=>x.textContent)"), ["More fields"])
        self.assertEqual(b.eval("document.querySelector('#fbPick .fpf[aria-selected=true]').dataset.fpk"), "ws")
        b.key("ArrowDown")                                                                          # into the fields, on the chosen one
        self.assertEqual(b.eval("document.activeElement.dataset.fpk"), "ws")
        b.key("ArrowDown")
        self.assertEqual([b.eval("FBX.field"), b.eval("document.activeElement.dataset.fpk")], ["dr", "dr"])
        self.assertEqual(b.eval("[...document.querySelectorAll('#fbPick .drange input')].map(i=>[i.dataset.dr,i.getAttribute('aria-label')])"),
                         [["from", "Due from"], ["to", "Due to"]])
        b.key("Home")
        self.assertEqual(b.eval("FBX.field"), "st")
        b.key("ArrowRight")                                                                        # → into its options
        self.assertEqual(b.eval(ACTIVE), "Open1")
        b.key(" ")
        self.assertEqual(b.eval("FBX.log.at(-1)"), ["sel", "st", ["Open"]])
        b.key("ArrowLeft")                                                                         # ← back to the field
        self.assertEqual(b.eval("document.activeElement.dataset.fpk"), "st")
        b.key("Escape")
        self.assertFalse(self.is_open("fbPick"))
        self.assertEqual(b.eval("document.activeElement.id"), "fbMore")
        self.assertEqual(self.expanded("#fbMore"), "false")
        # a date range; Done closes with focus back on the funnel; typing finds a field
        b.click("#fbMore")
        b.type("due")
        self.assertEqual(b.eval("FBX.query"), "due")
        self.assertEqual(b.eval("[...document.querySelectorAll('#fbPick .fpf')].map(x=>x.dataset.fpk)"), ["dr"])
        b.click("#fbPick .fpf[data-fpk=dr]")
        b.eval("(()=>{ const i=document.querySelector('#fbPick [data-dr=from]'); i.value='01-11-2026'; i.dispatchEvent(new Event('change',{bubbles:true})); })()")
        self.assertEqual(b.eval("FBX.log.at(-1)"), ["range", "dr", "from", "01-11-2026"])
        self.assertEqual(b.eval("document.getElementById('fbResult').textContent"), "Result: 3 of 9 shown")
        b.click("#fbDone")
        self.assertFalse(self.is_open("fbPick"))
        self.assertEqual(b.eval("document.activeElement.id"), "fbMore")
        b.click("#fbMore")
        b.click("#fbQ")                                                                            # a click away closes it
        self.assertFalse(self.is_open("fbPick"))

    def test_bl150_unused_filters_fold_into_the_funnel(self):
        b = self.b
        b.eval("FBX.sel.o=new Set(['Me']); fbxDraw()")
        w = b.eval("(()=>{ const r=[...document.querySelectorAll('#fbFix>input, #fbBar>.dd')].map(e=>e.getBoundingClientRect()); return Math.ceil(r.at(-1).right-r[0].left); })()")
        b.eval(f"document.getElementById('fbFix').style.width='{w - 20}px'; FBX.fold=true; fbxDraw()")   # 20px short of one row

        folded = b.eval("[...document.querySelectorAll('#fbBar>.dd.wfold')].map(d=>d.querySelector('button').id)")
        self.assertEqual(folded, ["pBtn"])                                                         # from the end; never the first, never a set one
        self.assertEqual(b.eval("document.getElementById('fbMore').getAttribute('aria-label')"), "Add a filter. 1 more filter is here")
        tops = b.eval("[...document.querySelectorAll('#fbFix>*, #fbBar>.dd:not(.wfold)')].map(e=>e.offsetTop)")
        self.assertLessEqual(max(tops) - min(tops), 8)                                            # one row
        b.eval("FBX.fold=false; fbxDraw()")
        self.assertEqual(b.eval("document.querySelectorAll('#fbBar .wfold').length"), 0)
        self.assertEqual(b.eval("document.getElementById('fbMore').getAttribute('aria-label')"), "Add a filter")
        self.assertEqual(b.errors, [])


if __name__ == "__main__":
    unittest.main()
