"""BL-256 (dev/COMPONENTS.md §3): the Tabs building block, as Today's day line (BL-293, `items`) and the prep page (BL-286 D,
`tabs` with `idBase`) use it. Roles and names, the roving tabindex, ← → Home End moving and selecting with focus following
(stopping at the ends for `items`, wrapping round for `tabs`), a click selecting, aria-current, aria-controls and the panels'
ids, and escaped text. (The two branches' tests, joined on release-190.)

Run: python3 dev/tests/test_block_tabs.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

# A fixture: three tabs in a box on the page; onSelect redraws at once, as a screen does, and records the choice.
MOUNT = """(()=>{ let box=document.getElementById('tbFix'); if(box) box.remove(); box=document.createElement('div'); box.id='tbFix';
  document.body.appendChild(box); window.TBSEL=[];
  const items=[{id:'a',label:'Alpha'},{id:'b',label:'<b>Beta</b>',name:'Beta, today',current:true,className:'today'},{id:'c',label:'Gamma'}];
  const draw=sel=>drawTabs(box,{items,selected:sel,label:'Fixture tabs',className:'fx',tabClass:'t',controls:'tbPanel',onSelect:id=>{ TBSEL.push(id); draw(id); }});
  draw('a'); })()"""
TABS = "[...document.querySelectorAll('#tbFix [role=tab]')]"


class TabsBlock(LiveBrowserCase):
    shared_server = True

    def setUp(self):
        super().setUp()
        self.b.eval(MOUNT)

    def state(self):
        return self.b.eval(f"{TABS}.map(t=>[t.getAttribute('aria-selected'),t.tabIndex])")

    def test_roles_names_and_roving_tabindex(self):
        b = self.b
        self.assertEqual(b.eval("(()=>{ const l=document.querySelector('#tbFix [role=tablist]'); return [l.className,l.getAttribute('aria-label')]; })()"),
                         ["fx", "Fixture tabs"])
        self.assertEqual(self.state(), [["true", 0], ["false", -1], ["false", -1]])
        self.assertEqual(b.eval(f"{TABS}.map(t=>[t.className,t.getAttribute('aria-label'),t.getAttribute('aria-current'),t.getAttribute('aria-controls')])"),
                         [["t", None, None, "tbPanel"], ["t today", "Beta, today", "date", "tbPanel"], ["t", None, None, "tbPanel"]])

    def test_arrows_home_end_move_select_and_take_the_focus(self):
        b = self.b
        b.eval(f"{TABS}[0].focus()")
        b.key("ArrowRight")
        self.assertEqual((self.state()[1], b.eval("document.activeElement.dataset.tab")), (["true", 0], "b"))
        b.key("End")
        self.assertEqual(b.eval("document.activeElement.dataset.tab"), "c")
        b.key("ArrowRight")                                         # the last stays the last
        self.assertEqual(b.eval("document.activeElement.dataset.tab"), "c")
        b.key("Home")
        self.assertEqual(b.eval("document.activeElement.dataset.tab"), "a")
        self.assertEqual(b.eval("TBSEL"), ["b", "c", "c", "a"])

    def test_a_click_selects(self):
        self.b.eval(f"{TABS}[2].click()")
        self.assertEqual(self.state()[2], ["true", 0])

    def test_its_text_is_escaped(self):
        html = self.b.eval("document.querySelector('#tbFix').innerHTML")
        self.assertIn("&lt;b&gt;Beta&lt;/b&gt;", html)
        self.assertNotIn("<b>", html)


# A fixture: three tabs mounted in a box at the top of the page, redrawn on every choice, as a screen's store would.
MOUNT_IDS = """(()=>{ const box=document.createElement('div'); box.id='tabsFix'; document.body.prepend(box); window.__chosen=[];
  const draw=sel=>mount(Tabs,{tabs:[{id:'a',label:'Alpha'},{id:'b',label:'<b>Beta</b>'},{id:'c',label:'Gamma'}],selected:sel,
    label:'Fixture',idBase:'fx',onSelect:id=>{ window.__chosen.push(id); draw(id); }},box); draw('a'); return true; })()"""
SEL_IDS = "[...document.querySelectorAll('#tabsFix [role=tab]')].map(t=>t.getAttribute('aria-selected')+t.tabIndex).join(' ')"


class TabsBlockIds(LiveBrowserCase):
    shared_server = True        # it only reads

    def setUp(self):
        super().setUp()
        self.b.eval(MOUNT_IDS)

    def test_roles_names_and_ids(self):
        b = self.b
        self.assertEqual(b.eval("document.querySelector('#tabsFix [role=tablist]').getAttribute('aria-label')"), "Fixture")
        self.assertEqual(b.eval("document.querySelector('#tabsFix [role=tablist]').className"), "tabs")
        self.assertEqual(b.eval("document.querySelectorAll('#tabsFix [role=tab]').length"), 3)
        self.assertEqual(b.eval("document.querySelector('#fx-tab-b').getAttribute('aria-controls')"), "fx-panel-b")
        self.assertEqual(b.eval(SEL_IDS), "true0 false-1 false-1")      # only the chosen tab is in the Tab order

    def test_keys_move_choose_and_focus(self):
        b = self.b
        b.eval("document.querySelector('#fx-tab-a').focus()")
        b.key("ArrowRight")
        b.wait("document.activeElement && document.activeElement.id==='fx-tab-b'")
        self.assertEqual(b.eval(SEL_IDS), "false-1 true0 false-1")
        b.key("End")
        b.wait("document.activeElement.id==='fx-tab-c'")
        b.key("ArrowRight")                                            # wraps round
        b.wait("document.activeElement.id==='fx-tab-a'")
        b.key("ArrowLeft")
        b.wait("document.activeElement.id==='fx-tab-c'")
        b.key("Home")
        b.wait("document.activeElement.id==='fx-tab-a'")
        self.assertEqual(b.eval("window.__chosen"), ["b", "c", "a", "c", "a"])

    def test_a_click_chooses(self):
        b = self.b
        b.click("#fx-tab-c")
        self.assertEqual(b.eval("window.__chosen"), ["c"])
        self.assertEqual(b.eval(SEL_IDS), "false-1 false-1 true0")

    def test_its_text_is_escaped(self):
        b = self.b
        self.assertEqual(b.eval("document.querySelector('#fx-tab-b').textContent"), "<b>Beta</b>")
        self.assertIsNone(b.eval("document.querySelector('#fx-tab-b b')"))


# BL-316: the props the page's tab lists use: the list's id, a tab's own id, its own panel, a count and data- attributes;
# wrap-round with `items`.
MOUNT_MORE = """(()=>{ let box=document.getElementById('tmFix'); if(box) box.remove(); box=document.createElement('div'); box.id='tmFix';
  document.body.appendChild(box); window.TMSEL=[];
  const items=[{id:'a',label:'With work',count:3,tabId:'tmA',controls:'tmPanelA',data:{pt:'a'}},
    {id:'b',label:'Nothing assigned',count:'<i>0</i>',controls:'tmPanelB',data:{pt:'b'}}];
  const draw=sel=>drawTabs(box,{items,selected:sel,label:'More',className:'tabs',id:'tmList',controls:'tmPanel',wrap:true,
    onSelect:id=>{ TMSEL.push(id); draw(id); }});
  draw('a'); })()"""


class TabsBlockMore(LiveBrowserCase):
    shared_server = True

    def setUp(self):
        super().setUp()
        self.b.eval(MOUNT_MORE)

    def test_ids_panels_counts_and_data(self):
        b = self.b
        self.assertEqual(b.eval("document.querySelector('#tmFix [role=tablist]').id"), "tmList")
        self.assertEqual(b.eval("[...document.querySelectorAll('#tmList [role=tab]')].map(t=>[t.id,t.getAttribute('aria-controls'),"
                                "t.dataset.pt,t.textContent,t.querySelector('span.sub').textContent])"),
                         [["tmA", "tmPanelA", "a", "With work 3", "3"], ["", "tmPanelB", "b", "Nothing assigned <i>0</i>", "<i>0</i>"]])
        self.assertIsNone(b.eval("document.querySelector('#tmList i')"))           # the count is text too

    def test_wrap_round_with_items(self):
        b = self.b
        b.eval("document.querySelector('#tmA').focus()")
        b.key("ArrowLeft")
        b.wait("document.activeElement && document.activeElement.dataset.pt==='b'")
        b.key("ArrowRight")
        b.wait("document.activeElement.id==='tmA'")
        self.assertEqual(b.eval("TMSEL"), ["b", "a"])


if __name__ == "__main__":
    unittest.main()
