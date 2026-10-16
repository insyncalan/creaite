"""#143 (v2.2.0): the one hover standard, core/hover.js. Every hover popup waits the same named delays, and no feature has a number of its own.

  tooltip  opens 400 ms after the pointer arrives, the next while one shows 100 ms, closes 150 ms after leaving
  card     opens 600 ms, closes 300 ms after the pointer leaves the trigger AND the card
  menu     opens 200 ms, a neighbouring menu 80 ms, closes 300 ms after leaving; a safe triangle keeps a diagonal move open
  keyboard focus opens a tooltip or card at once, Esc dismisses, the pointer may move onto the popup, nothing happens on touch.

Two parts:
- the state machine on a fake clock, in Node (no real waiting): open delay, close grace, neighbour switch, Esc, move onto the card,
  focus open, the safe triangle. Skipped when Node is missing.
- a real browser, against the real live server, at 1400 px and 900 px: the tooltip (timed in the page, with and without reduced
  motion), a hover Menu (a real mouse) and a hover card (hoverAttach). Only lower bounds are asserted (the delays); the exact timings are the Node cases' job, on a fake clock, so a loaded machine cannot fail them.

Run: python3 dev/tests/test_hover_standard.py   (Node for the first part, Google Chrome for the second; skipped otherwise)
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

HERE = Path(__file__).resolve().parent
HOVER_JS = HERE.parents[1] / "system/templates/dashboard/src/core/hover.js"


class StateMachine(unittest.TestCase):
    """core/hover.js on a fake clock."""

    @classmethod
    def setUpClass(cls):
        node = shutil.which("node")
        if not node:
            raise unittest.SkipTest("Node is not installed")
        cls.tmp = tempfile.TemporaryDirectory()
        mjs = Path(cls.tmp.name) / "hover.mjs"
        mjs.write_text(HOVER_JS.read_text(encoding="utf-8"), encoding="utf-8")        # a copy: Node reads .mjs as a module whatever its folder
        r = subprocess.run([node, str(HERE / "hover_units.mjs"), str(mjs)], capture_output=True, text=True, timeout=60)
        if r.returncode:
            raise AssertionError("the Node cases did not run: " + r.stderr[-800:])
        cls.results = json.loads(r.stdout)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def case(self, name):
        self.assertEqual(self.results.get(name), "ok", name)

    def test_constants(self):
        self.case("constants are the accepted numbers")

    def test_card(self):
        for n in self.results:
            if n.startswith("card:"):
                with self.subTest(n):
                    self.case(n)

    def test_menu(self):
        for n in self.results:
            if n.startswith("menu:") or n.startswith("safe"):
                with self.subTest(n):
                    self.case(n)

    def test_release(self):
        for n in self.results:
            if n.startswith("release:"):
                with self.subTest(n):
                    self.case(n)

    def test_every_case_ran(self):
        self.assertGreaterEqual(len(self.results), 20)


TIP_FIXTURE = """(()=>{ document.getElementById('hfix')?.remove(); const box=document.createElement('div'); box.id='hfix';
  box.style.cssText='position:fixed;top:300px;left:300px;z-index:500;display:flex;gap:40px';
  box.innerHTML='<button class="ib" id="hA" data-tip="Alpha" aria-label="Alpha">A</button><button class="ib" id="hB" data-tip="Beta" aria-label="Beta">B</button>';
  document.body.appendChild(box); })()"""
# time, in the page, from one synthetic mouseover to the tooltip showing the words (or from the pointer leaving to it going)
TIP_TIMES = """(async()=>{
  const tip=()=>document.getElementById('tip'), on=w=>{ const t=tip(); return !!t&&t.classList.contains('on')&&(w==null||t.textContent.startsWith(w)); };
  const until=(f,limit=2500)=>new Promise(r=>{ const t0=performance.now(); const i=setInterval(()=>{ if(f()||performance.now()-t0>limit){ clearInterval(i); r(Math.round(performance.now()-t0)); } },4); });
  const over=el=>el.dispatchEvent(new MouseEvent('mouseover',{bubbles:true}));
  const A=document.getElementById('hA'), B=document.getElementById('hB'), out={};
  over(A); out.first=await until(()=>on('Alpha'));
  over(B); out.next=await until(()=>on('Beta'));
  over(document.body); out.hide=await until(()=>!on());
  over(A); await new Promise(r=>setTimeout(r,200)); out.shownAt200=on();           // not at 200 ms
  over(document.body); await new Promise(r=>setTimeout(r,1000));
  return out; })()"""


class TooltipBase:
    shared_server = True
    width, height = 1400, 900

    def times(self):
        self.b.eval(TIP_FIXTURE)
        return self.b.eval(TIP_TIMES)

    def check(self, t):
        self.assertGreaterEqual(t["first"], 390, t)        # TIP_OPEN 400, no popup is instant
        self.assertGreaterEqual(t["next"], 90, t)          # TIP_NEXT 100: no longer 0 between icons
        self.assertGreaterEqual(t["hide"], 140, t)         # TIP_CLOSE 150, was 120
        self.assertFalse(t["shownAt200"], t)               # was 250: still nothing at 200 ms

    def test_tooltip_delays_at_desktop_width(self):
        self.check(self.times())

    def test_tooltip_delays_at_900_px(self):
        self.b.resize(900, 800)
        self.check(self.times())

    def test_keyboard_focus_shows_it_at_once_and_esc_hides_it(self):
        b = self.b
        b.eval(TIP_FIXTURE)
        b.eval("document.activeElement&&document.activeElement.blur(); document.getElementById('hA').focus()")
        b.key("Tab")                                       # a key press makes the focus a keyboard one
        b.key("Tab", 8)                                    # Shift+Tab back to A
        b.wait("document.getElementById('hA')===document.activeElement", 3)
        b.wait("document.getElementById('tip')&&document.getElementById('tip').classList.contains('on')", 1.5)   # no 400 ms wait to see
        b.key("Escape")
        b.wait("!document.getElementById('tip').classList.contains('on')", 2)


class TooltipReducedMotion(TooltipBase, LiveBrowserCase):
    reduced_motion = True                                  # no fade; the same delays


class TooltipFullMotion(TooltipBase, LiveBrowserCase):
    reduced_motion = False


MENU_FIXTURE = """(()=>{ document.getElementById('hmenus')?.remove(); const root=document.createElement('div'); root.id='hmenus';
  root.style.cssText='position:fixed;top:0;left:0;z-index:500;background:var(--surface)'; document.body.appendChild(root);
  window.HM={log:[],picked:[]};
  [['m1',80],['m2',420]].forEach(([id,left])=>{ const box=document.createElement('div'); box.id=id; box.style.cssText=`position:fixed;top:80px;left:${left}px`; root.appendChild(box);
    mountMenu(box,{label:'Menu '+id, hover:true, data:{hm:id}, items:[{id:'a',name:'First'},{id:'b',name:'Second'}], onPick:i=>HM.picked.push(id+i)});
    new MutationObserver(()=>{ const open=!!box.querySelector('[role=menu]'); if(open!==box._o){ box._o=open; HM.log.push({id,open,t:performance.now()}); } }).observe(box,{childList:true,subtree:true}); }); })()"""


class HoverMenu(LiveBrowserCase):
    shared_server = True
    reduced_motion = True

    def mouse(self, x, y):
        self.b.call("Input.dispatchMouseEvent", type="mouseMoved", x=x, y=y, button="none")
        self.b.pump(0.01)

    def at(self, sel):
        p = self.b.box(sel)
        self.assertTrue(p, sel)
        return p["x"], p["y"]

    def is_open(self, id):
        return self.b.eval(f"!!document.querySelector('#{id} [role=menu]')")

    def stamp(self):
        self.b.eval("window.T0=performance.now()")

    def took(self, id, open_):
        """ms from the stamp until menu `id` opened or closed, as the page saw it."""
        self.b.wait(f"HM.log.some(e=>e.id==={id!r}&&e.open==={'true' if open_ else 'false'}&&e.t>=T0)", 4)
        return round(self.b.eval(f"HM.log.filter(e=>e.id==={id!r}&&e.open==={'true' if open_ else 'false'}&&e.t>=T0)[0].t-T0"))

    def scenario(self):
        b = self.b
        b.eval(MENU_FIXTURE)
        b.wait("document.querySelector('#m1 button[aria-haspopup]')")
        b1, b2 = "#m1 button[aria-haspopup]", "#m2 button[aria-haspopup]"
        self.mouse(900, 600)
        # opens after 200 ms, without taking focus
        x, y = self.at(b1)
        self.stamp(); self.mouse(x, y)
        t = self.took("m1", True)
        self.assertGreaterEqual(t, 190, t)
        self.assertFalse(b.eval("!!document.querySelector('#m1 [role=menu]').contains(document.activeElement)"))
        # the pointer can move onto the list and it stays
        lx, ly = self.at("#m1 [role=menu] [role=menuitem]")
        self.mouse(lx, ly)
        b.pump(0.7)
        self.assertTrue(self.is_open("m1"))
        # a neighbouring menu takes over quickly, and the first closes
        x2, y2 = self.at(b2)
        self.stamp(); self.mouse(x2, y2)
        t2 = self.took("m2", True)
        self.assertGreaterEqual(t2, 70, t2)
        self.assertFalse(self.is_open("m1"))
        # Esc closes at once, and it stays shut while the pointer stays
        self.stamp(); b.key("Escape")
        self.took("m2", False)                               # closes on the key (the Node cases prove 'at once' on a fake clock)
        b.pump(0.8)
        self.assertFalse(self.is_open("m2"))
        # leaving and coming back opens it again; leaving closes it after 300 ms
        self.mouse(900, 600); b.pump(0.1)
        self.mouse(x2, y2)
        self.took("m2", True)
        self.stamp(); self.mouse(900, 600)
        t3 = self.took("m2", False)
        self.assertGreaterEqual(t3, 290, t3)
        # a click on a hover-opened menu keeps it and moves focus in; the keyboard opens one with focus inside
        self.mouse(x, y); self.took("m1", True)
        b.click(b1)
        b.pump(0.1)
        self.assertTrue(self.is_open("m1"))
        self.assertTrue(b.eval("document.activeElement&&document.activeElement.getAttribute('role')==='menuitem'"))
        b.key("Escape"); b.pump(0.1)
        self.mouse(900, 600); b.pump(0.5)
        b.eval("document.querySelector('#m2 button[aria-haspopup]').focus()")
        b.key("ArrowDown")
        b.wait("document.querySelector('#m2 [role=menu]')&&document.querySelector('#m2 [role=menu]').contains(document.activeElement)", 2)

    def hover_open_m1(self):
        b = self.b
        b.eval(MENU_FIXTURE)
        b.wait("document.querySelector('#m1 button[aria-haspopup]')")
        self.mouse(900, 600)
        x, y = self.at("#m1 button[aria-haspopup]")
        self.stamp(); self.mouse(x, y)
        self.took("m1", True)
        return x, y

    def test_after_a_click_in_esc_is_the_menus_own_and_focus_goes_back_to_the_button(self):
        b = self.b
        self.hover_open_m1()
        b.click("#m1 button[aria-haspopup]")                       # a click on the hover-opened menu moves focus in
        b.wait("document.querySelector('#m1 [role=menu]').contains(document.activeElement)", 3)
        b.key("Escape")
        b.wait("!document.querySelector('#m1 [role=menu]')", 3)
        b.wait("document.activeElement===document.querySelector('#m1 button[aria-haspopup]')", 3)

    def test_after_a_click_in_the_pointer_drifting_off_does_not_close_it(self):
        b = self.b
        self.hover_open_m1()
        b.click("#m1 button[aria-haspopup]")
        b.wait("document.querySelector('#m1 [role=menu]').contains(document.activeElement)", 3)
        self.mouse(900, 600)                                       # the mouse drifts away while the keys are in use
        b.key("ArrowDown")
        b.pump(0.9)                                                # well past the 300 ms grace
        self.assertTrue(self.is_open("m1"))
        self.assertTrue(b.eval("document.querySelector('#m1 [role=menu]').contains(document.activeElement)"))

    def test_down_on_a_hover_opened_menu_moves_in_and_the_menu_stays_when_the_pointer_leaves(self):
        b = self.b
        self.hover_open_m1()
        b.eval("document.querySelector('#m1 button[aria-haspopup]').focus()")
        b.key("ArrowDown")
        b.wait("document.querySelector('#m1 [role=menu]').contains(document.activeElement)", 3)
        self.mouse(900, 600)
        b.pump(0.9)
        self.assertTrue(self.is_open("m1"))

    def test_a_click_inside_the_hover_window_is_not_undone_by_the_late_hover_timer(self):
        b = self.b
        b.eval(MENU_FIXTURE)
        b.wait("document.querySelector('#m1 button[aria-haspopup]')")
        self.mouse(900, 600)
        b.click("#m1 button[aria-haspopup]")                       # the pointer arrives and clicks well inside the 200 ms
        b.wait("document.querySelector('#m1 [role=menu]')", 3)
        b.pump(0.6)                                                # the pending hover open would have fired by now
        self.assertTrue(b.eval("document.querySelector('#m1 [role=menu]').contains(document.activeElement)"))
        b.click("#m1 button[aria-haspopup]")                       # so the next click closes it, not moves focus in
        b.wait("!document.querySelector('#m1 [role=menu]')", 3)

    def test_menu_at_desktop_width(self):
        self.scenario()

    def test_menu_at_900_px(self):
        self.b.resize(900, 800)
        self.scenario()


CARD_FIXTURE = """(()=>{ document.getElementById('hcard')?.remove(); const root=document.createElement('div'); root.id='hcard';
  root.style.cssText='position:fixed;top:0;left:0;z-index:500'; document.body.appendChild(root);
  root.innerHTML='<button id="ct" style="position:fixed;top:120px;left:120px">Trigger</button><div id="cc" tabindex="-1" style="position:fixed;top:170px;left:120px;width:240px;height:120px;background:var(--surface);border:1px solid var(--line);display:none">Card</div>';
  window.HC={log:[]}; const t=root.querySelector('#ct'), c=root.querySelector('#cc');
  hoverAttach(t,{group:cardGroup,panel:()=>c.style.display==='none'?null:c,open:()=>{ c.style.display='block'; HC.log.push({open:true,t:performance.now()}); },close:()=>{ c.style.display='none'; HC.log.push({open:false,t:performance.now()}); }}); })()"""


class HoverCard(LiveBrowserCase):
    shared_server = True
    reduced_motion = True

    def mouse(self, x, y):
        self.b.call("Input.dispatchMouseEvent", type="mouseMoved", x=x, y=y, button="none")
        self.b.pump(0.01)

    def took(self, open_):
        flag = "true" if open_ else "false"
        self.b.wait(f"HC.log.some(e=>e.open==={flag}&&e.t>=T0)", 5)
        return round(self.b.eval(f"HC.log.filter(e=>e.open==={flag}&&e.t>=T0)[0].t-T0"))

    def scenario(self):
        b = self.b
        b.eval(CARD_FIXTURE)
        self.mouse(900, 600)
        tx, ty = self.at("#ct")
        b.eval("window.T0=performance.now()"); self.mouse(tx, ty)
        t = self.took(True)
        self.assertGreaterEqual(t, 590, t)                 # CARD_OPEN 600: not at the menu's 200
        cx, cy = self.at("#cc")                            # onto the card: it stays (hoverable, persistent)
        self.mouse(cx, cy)
        b.pump(0.8)
        self.assertEqual(b.eval("document.getElementById('cc').style.display"), "block")
        b.eval("window.T0=performance.now()"); self.mouse(900, 600)   # off the card: closes after 300 ms
        t2 = self.took(False)
        self.assertGreaterEqual(t2, 290, t2)
        # Esc dismisses at once and it stays shut until the pointer has left
        b.eval("window.T0=performance.now()"); self.mouse(tx, ty); self.took(True)
        b.eval("window.T0=performance.now()"); b.key("Escape")
        self.took(False)
        b.pump(1.0)
        self.assertEqual(b.eval("document.getElementById('cc').style.display"), "none")
        # keyboard focus opens it with no delay
        self.mouse(900, 600); b.pump(0.1)
        b.eval("document.activeElement&&document.activeElement.blur()")
        b.key("Tab"); b.key("Tab", 8)
        b.eval("window.T0=performance.now(); document.getElementById('ct').blur(); document.getElementById('ct').focus()")
        b.wait("document.getElementById('cc').style.display==='block'", 1.0)

    def at(self, sel):
        p = self.b.box(sel)
        self.assertTrue(p, sel)
        return p["x"], p["y"]

    def test_card_at_desktop_width(self):
        self.scenario()

    def test_card_at_900_px(self):
        self.b.resize(900, 800)
        self.scenario()


if __name__ == "__main__":
    unittest.main()
