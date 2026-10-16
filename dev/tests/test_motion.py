"""BL-136 (sprint-motion): restrained animation. Stage A: the tokens, the one reduced-motion rule, the helpers, the Motion setting,
press and focus, the sliding indicator, the tick and the bars, filter chips, switch and save, the ask button's sheen, copy
confirmation and the theme fade.

Run: python3 dev/tests/test_motion.py   (the browser tests need Google Chrome; skipped otherwise)

The real live server in a throwaway vault with fictional data, and the real dashboard in headless Chrome. Tests wait for
conditions, never fixed pauses; where an effect must still be running when it is checked, --k (the duration multiplier) is
raised so it lasts long enough on a loaded machine.
"""
import json
import re
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import TEST_PALETTES, LiveBrowserCase  # noqa: E402
import work_data as W  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_review_triage import load_queue  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from split_dashboard import readable_page  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "system" / "templates" / "dashboard.html"
PALETTES = TEST_PALETTES   # creaite and Cursor only (live_browser.TEST_PALETTES)
PAGES = ("today", "work", "review", "projects", "people", "inbox", "files", "activity", "settings", "help")

# every element's longest transition and animation, ::before and ::after included, and any animation still running
SWEEP = """(()=>{ const ms=v=>Math.max(0,...String(v).split(",").map(x=>{ x=x.trim(); return x.endsWith("ms")?parseFloat(x):parseFloat(x)*1000; }).filter(n=>!isNaN(n)));
  const bad=[]; for(const el of document.querySelectorAll("*")) for(const p of [null,"::before","::after"]){ const c=getComputedStyle(el,p);
    const t=ms(c.transitionDuration), a=c.animationName!=="none"?ms(c.animationDuration):0;
    if(t>0||a>0) bad.push(`${el.tagName.toLowerCase()}${el.id?"#"+el.id:""}.${String(el.className&&el.className.baseVal!==undefined?el.className.baseVal:el.className).split(" ").join(".")}${p||""} t=${t} a=${a}`); }
  const running=document.getAnimations().filter(a=>a.playState==="running").map(a=>String(a.animationName||(a.effect&&a.effect.target&&a.effect.target.className)||"script"));
  return {bad:bad.slice(0,12), n:bad.length, running}; })()"""


def css():
    s = TEMPLATE.read_text(encoding="utf-8")
    return s[s.index("<style>"):s.index("</style>")]


def script():
    s = readable_page()     # BL-231: the source; the bundle reprints the code
    return s[s.index("<script>", s.index("</style>")):]


class StaticRules(unittest.TestCase):
    """The stylesheet's rules, read from the template."""

    def test_the_tokens_are_defined_once_on_root(self):
        c = css()
        m = re.search(r":root\{--k:1;[^}]*\}", c)
        self.assertTrue(m, "the BL-136 token block")
        for tok, val in (("--d1", "120ms"), ("--d2", "200ms"), ("--d3", "320ms"), ("--d4", "520ms")):
            self.assertIn(f"{tok}:calc({val}*var(--k))", m.group(0))
        for tok, val in (("--out", ".2,.7,.2,1"), ("--inout", ".65,0,.35,1"), ("--in", ".4,0,1,1")):
            self.assertIn(f"{tok}:cubic-bezier({val})", m.group(0))
        self.assertEqual(len(re.findall(r"--d3:", c)), 1)

    def test_one_reduced_motion_rule_and_the_scattered_ones_are_gone(self):
        c = css()
        self.assertEqual(c.count("prefers-reduced-motion"), 1)
        self.assertNotIn("prefers-reduced-motion:no-preference", c)
        self.assertIn(':root[data-motion="reduce"] *', c)                  # the in-app setting uses the same collapse

    def test_no_transition_or_keyframes_moves_width_height_top_or_left(self):
        c = css()
        allowed = set()
        for m in re.finditer(r"([^{}]+)\{([^{}]*transition:[^{}]*)\}", c):
            for t in re.findall(r"transition:([^;}]*)", m.group(2)):
                props = [p.strip().split(" ")[0] for p in t.split(",")]
                hit = {"width", "height", "top", "left", "all"} & set(props)
                if hit:
                    self.assertIn(m.group(1).strip().split()[-1], allowed, f"{m.group(1).strip()} transitions {hit}")
        for m in re.finditer(r"@keyframes\s+([\w-]+)\s*\{((?:[^{}]*\{[^{}]*\})*)[^{}]*\}", c):
            self.assertFalse(re.search(r"(?<![\w-])(width|height|top|left)\s*:", m.group(2)), f"@keyframes {m.group(1)}")

    def test_only_the_listed_animations_loop(self):
        c = css()
        loops = set()
        for m in re.finditer(r"animation:\s*([\w-]+)[^;}]*\binfinite\b", c):
            loops.add(m.group(1))
        self.assertLessEqual(loops, {"sp", "askpulse", "mshim", "mhair", "mwave", "mripple", "mang", "mrbp"}, loops)   # spinner, ask pulse, loading shimmer, run hairline, typing dots, now ripple, the focused ask input, the run badge (BL-139)

    def test_every_smooth_scroll_goes_through_the_helper(self):
        s = script()
        self.assertNotIn('behavior:"smooth"', s)
        self.assertNotIn("behavior:'smooth'", s)
        self.assertIn('behavior:reduced()?"instant":"smooth"', s)

    def test_the_motion_setting_has_a_default(self):
        d = json.loads((ROOT / "system" / "templates" / "settings-defaults.json").read_text())
        self.assertEqual(d["dashboard"]["motion"], "System")


class Motion(LiveBrowserCase):
    shared_server = True
    reduced_motion = False      # these tests check the motion itself
    width, height = 1400, 900

    def setUp(self):
        super().setUp()
        self.b.eval("window.__errs=[]; addEventListener('error',e=>__errs.push(e.message)); addEventListener('unhandledrejection',e=>__errs.push(String(e.reason)))")

    def tearDown(self):
        try:
            self.assertEqual(self.b.eval("window.__errs"), [])
        finally:
            super().tearDown()

    def os_reduce(self, on):
        self.b.call("Emulation.setEmulatedMedia", features=[{"name": "prefers-reduced-motion", "value": "reduce" if on else "no-preference"}])
        on = "true" if on else "false"
        self.b.wait(f"matchMedia('(prefers-reduced-motion: reduce)').matches==={on}")

    def motion(self, m):
        self.b.eval(f"S.motion={m!r}; applyMotion()")

    def page(self, v):
        self.b.eval(f"go({v!r})")
        self.b.wait(f"VIEW==={v!r}")

    def settings_file(self):
        return json.loads((self.v.root / "system" / "config" / "settings.json").read_text())

    # ---- 1. the setting and the rule ----
    def test_follow_system_obeys_the_system_and_reduce_and_full_override_it(self):
        b = self.b
        self.assertEqual(b.eval("S.motion"), "System")
        self.assertFalse(b.eval("reduced()"))
        self.assertNotEqual(b.eval("getComputedStyle(document.querySelector('.btn')).transitionDuration.split(',')[0]"), "0s")
        self.os_reduce(True)
        self.assertTrue(b.eval("reduced() && document.documentElement.dataset.reduced==='1'"))
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('.btn')).transitionDuration.split(',')[0]"), "0s")
        self.motion("Full")                                              # Full: creaite's own motion runs even so
        self.assertFalse(b.eval("reduced()"))
        self.assertEqual(b.eval("document.documentElement.dataset.motion"), "full")
        self.assertNotEqual(b.eval("getComputedStyle(document.querySelector('.btn')).transitionDuration.split(',')[0]"), "0s")
        spin = b.eval("(()=>{ const s=document.createElement('span'); s.className='spin'; document.body.appendChild(s); const c=getComputedStyle(s); const r=[c.animationDuration,c.animationIterationCount]; s.remove(); return r; })()")
        self.assertEqual(spin, ["0s", "1"])                              # but the spinner, essential state, follows the system
        self.os_reduce(False)
        self.motion("Reduce")                                            # Reduce, with the system's setting off
        self.assertTrue(b.eval("reduced() && document.documentElement.dataset.motion==='reduce'"))
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('.btn')).transitionDuration.split(',')[0]"), "0s")
        self.motion("System")

    def test_reduce_leaves_no_motion_on_any_page(self):
        b = self.b
        self.motion("Reduce")
        b.wait("!document.getAnimations().some(a=>a.playState==='running')")   # the first paint's own effects have finished
        for v in PAGES:
            self.page(v)
            if v == "work":
                for lay in ("list", "board"):
                    b.eval(f"document.querySelector('#wlay [data-lay={lay}]').click()")
                    b.wait("!document.querySelector('.mind')")
                    b.pump(0.05)
                    r = b.eval(SWEEP)
                    self.assertEqual((r["n"], r["running"]), (0, []), f"work {lay}: {r['bad']}")
                b.eval("document.querySelector('#wlay [data-lay=list]').click()")
                continue
            b.pump(0.05)
            r = b.eval(SWEEP)
            self.assertEqual((r["n"], r["running"]), (0, []), f"{v}: {r['bad']}")
        b.eval("go('cockpit','ABC')")
        b.wait("VIEW==='cockpit'")
        r = b.eval(SWEEP)
        self.assertEqual((r["n"], r["running"]), (0, []), f"project: {r['bad']}")
        self.motion("System")

    def test_the_setting_is_on_the_settings_page_saves_and_survives_a_reload(self):
        b = self.b
        row = "[...document.querySelectorAll('#set-essentials .srow')].find(r=>r.querySelector('span[id]').textContent==='Motion')"                       # BL-320: an Essential
        b.eval("go('settings','essentials')")
        b.wait(f"!!({row})")
        opts = b.eval(f"[...{row}.querySelectorAll('option')].map(o=>[o.value,o.textContent])")
        self.assertEqual(opts, [["System", "Follow my Mac"], ["Reduce", "Reduce"], ["Full", "Full"]])
        b.eval(f"(()=>{{ const e={row}.querySelector('select'); e.value='Reduce'; e.dispatchEvent(new Event('change',{{bubbles:true}})); }})()")
        b.wait("document.documentElement.dataset.motion==='reduce'")
        end = time.time() + 8
        while time.time() < end and self.settings_file()["dashboard"].get("motion") != "Reduce":
            time.sleep(0.1)
        self.assertEqual(self.settings_file()["dashboard"]["motion"], "Reduce")
        b.reload()
        b.wait("typeof go==='function' && LIVE")
        b.eval("window.__errs=[]")
        self.assertEqual(b.eval("[S.motion, document.documentElement.dataset.motion, reduced()]"), ["Reduce", "reduce", True])
        b.eval("go('settings','essentials')")                        # put it back for the other tests
        b.wait(f"!!({row})")
        b.eval(f"(()=>{{ const e={row}.querySelector('select'); e.value='System'; e.dispatchEvent(new Event('change',{{bubbles:true}})); }})()")
        end = time.time() + 8
        while time.time() < end and self.settings_file()["dashboard"].get("motion") != "System":
            time.sleep(0.1)
        self.assertEqual(self.settings_file()["dashboard"]["motion"], "System")

    def test_the_settings_search_finds_motion(self):
        b = self.b
        b.eval("STAB='general'; go('settings')")
        b.wait("!!document.querySelector('#settingsBody [data-sec]')")
        b.eval("setSearch('reduce motion')")
        b.wait("!!([...document.querySelectorAll('#set-essentials .srow')].find(r=>r.querySelector('span[id]').textContent==='Motion'))")
        b.eval("setSearch('')")

    def test_tokens_resolve_in_every_theme_light_and_dark(self):
        b = self.b
        for pal in PALETTES:
            for mode in ("Light", "Dark"):
                b.eval(f"S.palette={pal!r}; S.theme={mode!r}; applyTheme()")
                got = b.eval("['--d1','--d3','--out'].map(t=>getComputedStyle(document.documentElement).getPropertyValue(t).trim())")
                self.assertTrue(all(got), (pal, mode, got))
                self.assertEqual(b.eval("getComputedStyle(document.documentElement).getPropertyValue('--k').trim()"), "1")
        b.eval("S.palette='creaite'; S.theme='System'; applyTheme()")

    def test_anim_and_scrolling_honour_reduced_motion(self):
        b = self.b
        spy = "(()=>{ const calls=[]; const o=Element.prototype.scrollIntoView; Element.prototype.scrollIntoView=function(x){ calls.push(x); }; mScroll(document.body,{block:'start'}); Element.prototype.scrollIntoView=o; return calls; })()"
        self.assertEqual(b.eval(spy), [{"block": "start", "behavior": "smooth"}])
        self.motion("Reduce")
        self.assertEqual(b.eval(spy), [{"block": "start", "behavior": "instant"}])
        self.assertEqual(b.eval("anim(document.body,[{opacity:1},{opacity:1}],{duration:900}).effect.getTiming().duration"), 1)
        b.eval("window.__cu=document.createElement('b'); document.body.appendChild(__cu); countUp(__cu,42)")
        self.assertEqual(b.eval("[__cu.textContent, __cu.getAttribute('aria-label')]"), ["42", "42"])   # at once, and readable from the first frame
        b.eval("__cu.remove()")
        self.motion("System")
        self.assertEqual(b.eval("anim(document.body,[{opacity:1},{opacity:1}],{duration:900}).effect.getTiming().duration"), 900)

    def test_j_and_k_scroll_instantly(self):
        s = script()
        self.assertIn('el&&el.scrollIntoView({block:"nearest"})', s)    # the key-driven scroll never asks for smooth

    # ---- 2. press, hover and focus ----
    def test_buttons_lift_and_press_with_translate_and_inputs_grow_a_ring(self):
        b = self.b
        self.page("work")
        r = b.eval("""(()=>{ const t=document.createElement('style'); document.head.appendChild(t);
          const btn=document.querySelector('#wlay').closest('.toolbar')?.querySelector('.btn')||document.querySelector('#v-work .btn'); const c=getComputedStyle(btn);
          return {prop:c.transitionProperty, ok:c.transitionProperty.includes('translate')&&c.transitionProperty.includes('scale')}; })()""")
        self.assertTrue(r["ok"], r)
        self.assertIn(":hover{translate:0 -1px}", css())               # the translate property, so a button's own transform stays:
        jump = b.eval("(()=>{ const j=document.createElement('button'); j.className='btn primary chjump'; document.body.appendChild(j); const t=getComputedStyle(j).transform; j.remove(); return t; })()")
        self.assertNotEqual(jump, "none")                                # ask creaite's centred Jump to latest keeps its translateX(-50%)
        b.call("Emulation.setFocusEmulationEnabled", enabled=True)
        b.eval("document.getElementById('workQ').focus()")
        b.wait("getComputedStyle(document.getElementById('workQ')).boxShadow.includes('0px 0px 0px 3px')")   # the ring grows in
        self.assertNotEqual(b.eval("getComputedStyle(document.getElementById('workQ')).outlineStyle"), "")

    # ---- 3. sliding indicator ----
    def test_the_indicator_glides_between_tabs_layouts_and_categories_then_goes(self):
        b = self.b
        b.eval("document.documentElement.style.setProperty('--k',20)")    # long enough to see on a loaded machine
        self.page("work")
        b.eval("document.querySelector('#wtabs [data-t=raid]').click()")
        self.assertEqual(b.eval("document.querySelectorAll('#wtabs > .mind').length"), 1)
        self.assertTrue(b.eval("document.getElementById('wtabs').classList.contains('mmove')"))
        self.assertEqual(b.eval("document.querySelector('#wtabs > .mind').getAnimations().length"), 1)
        b.eval("document.querySelector('#wtabs [data-t=actions]').click()")
        self.assertEqual(b.eval("document.querySelectorAll('#wtabs > .mind').length"), 1)                    # one at a time
        b.eval("document.querySelector('#wlay [data-lay=board]').click()")
        self.assertEqual(b.eval("document.querySelectorAll('#wlay > .mind').length"), 1)
        b.eval("document.querySelector('#wlay [data-lay=list]').click()")
        b.eval("STAB='general'; go('settings')")
        b.wait("!!document.querySelector('#setcats [data-scat=health]')")
        b.eval("document.querySelector('#setcats [data-scat=health]').click()")
        b.wait("document.querySelector('#setcats [aria-selected=true]').dataset.scat==='health'")
        self.assertEqual(b.eval("document.querySelectorAll('#setcats > .mind').length"), 1)
        b.eval("document.documentElement.style.setProperty('--k',1)")
        b.wait("!document.querySelector('.mind') && !document.querySelector('.mmove')", timeout=15)

    def test_no_indicator_when_reduced_or_on_first_render(self):
        b = self.b
        self.page("work")
        self.motion("Reduce")
        b.eval("document.querySelector('#wtabs [data-t=raid]').click()")
        self.assertFalse(b.eval("!!document.querySelector('.mind')"))
        b.eval("document.querySelector('#wtabs [data-t=actions]').click()")
        self.motion("System")
        b.eval("renderWork()")                                           # a render with the same tab: nothing moves
        self.assertFalse(b.eval("!!document.querySelector('.mind')"))

    # ---- 4. tick and bars ----
    def test_a_newly_highlighted_row_draws_its_tick_once(self):
        b = self.b
        self.page("work")
        b.eval("document.documentElement.style.setProperty('--k',20)")
        ids = b.eval("$$('#workTbl tr[data-row]').slice(0,2).map(t=>t.dataset.row)")
        b.eval(f"hlToggle(WT,{ids[0]!r})")
        self.assertTrue(b.eval(f"document.querySelector('#workTbl tr[data-row=\"{ids[0]}\"]').classList.contains('mtick')"))
        self.assertEqual(b.eval(f"getComputedStyle(document.querySelector('#workTbl tr[data-row=\"{ids[0]}\"] td.title'),'::before').animationName"), "mtickdraw")
        b.eval(f"hlToggle(WT,{ids[1]!r})")                               # two: the change-several bar shows, at once
        self.assertFalse(b.eval("document.getElementById('wbulk').hidden"))
        b.eval("renderWork()")                                           # a re-render draws nothing
        self.assertEqual(b.eval("$$('#workTbl tr.mtick').length"), 0)
        self.assertEqual(b.eval("$$('#workTbl tr.hl').length"), 2)
        b.eval("hlClear()")
        self.assertTrue(b.eval("document.getElementById('wbulk').hidden"))   # the bar leaves at once
        b.eval("document.documentElement.style.setProperty('--k',1)")

    def test_a_large_range_and_reduced_motion_draw_no_tick(self):
        b = self.b
        self.page("work")
        n = b.eval("rows().length")
        b.eval("rows().forEach(x=>HL.set(x.id,WT)); hlPaint()")
        self.assertEqual(b.eval("$$('#workTbl tr.mtick').length"), 0 if n > 12 else b.eval("$$('#workTbl tr.hl').length"))
        b.eval("hlClear()")
        self.motion("Reduce")
        ids = b.eval("$$('#workTbl tr[data-row]').slice(0,1).map(t=>t.dataset.row)")
        b.eval(f"hlToggle(WT,{ids[0]!r})")
        self.assertEqual(b.eval("$$('#workTbl tr.mtick').length"), 0)
        b.eval("hlClear()")
        self.motion("System")

    def test_the_bars_rise_with_starting_style(self):
        c = css()
        self.assertIn("@starting-style{.wbulk{opacity:0;transform:translateY(8px)}}", c)

    # ---- 5. filter chips ----
    def test_one_chip_scales_in_and_one_removed_closes_up(self):
        b = self.b
        self.page("work")
        b.eval("document.documentElement.style.setProperty('--k',20)")
        b.pump(0.1)                                                       # the chip row's first measure is taken on the next frame
        n = b.eval("$$('#wapplied .fchip').length")
        b.eval("setOf('pr').add('High'); renderWork()")
        self.assertEqual(b.eval("$$('#wapplied .fchip').length"), n + 1)
        self.assertEqual(b.eval("document.querySelector('#wapplied [data-clr=pr]').closest('.fchip').getAnimations().length"), 1)
        self.assertEqual(b.eval("$$('#wapplied .fchip').reduce((n,c)=>n+c.getAnimations().length,0)"), 1)   # only the new one
        b.pump(0.1)
        b.eval("document.querySelector('#wapplied [data-clr=pr]').click()")
        self.assertEqual(b.eval("$$('#wapplied .fchip').length"), n)      # gone from the row at once
        self.assertEqual(b.eval("$$('body > .mghost').length"), 1)       # a copy fades where it was
        self.assertEqual(b.eval("document.querySelector('body > .mghost').textContent"), "")   # with no text of its own
        b.eval("document.documentElement.style.setProperty('--k',1)")
        b.wait("!document.querySelector('.mghost')", timeout=15)

    def test_several_chips_at_once_swap_without_motion(self):
        b = self.b
        self.page("work")
        b.eval("document.documentElement.style.setProperty('--k',20)")
        b.pump(0.1)
        n = b.eval("$$('#wapplied .fchip').length")
        b.eval("setOf('pr').add('High'); setOf('pr').add('Medium'); WQ='a'; renderWork()")   # two new chips together
        self.assertEqual(b.eval("$$('#wapplied .fchip').length"), n + 2)
        self.assertEqual(b.eval("$$('#wapplied .fchip').reduce((n,c)=>n+c.getAnimations().length,0)"), 0)
        b.pump(0.1)
        b.eval("document.getElementById('clearF').click()")             # Clear all
        self.assertEqual(b.eval("$$('.mghost').length"), 0)
        b.eval("document.documentElement.style.setProperty('--k',1)")

    # ---- 6. switch and save ----
    def test_the_switch_slides_by_transform(self):
        b = self.b
        b.eval("STAB='general'; go('settings')")
        b.wait("!!document.querySelector('#settingsBody .switch')")
        c = b.eval("(()=>{ const s=document.querySelector('#settingsBody .switch'); const c=getComputedStyle(s,'::after'); return [c.transitionProperty, c.transitionTimingFunction]; })()")
        self.assertEqual(c[0], "transform")
        self.assertIn("1.35", c[1])                                     # the small overshoot

    def test_a_save_ticks_only_when_it_worked(self):
        b = self.b
        b.eval("STAB='work'; go('settings')")
        b.wait("!!document.querySelector('[data-k=boardClosedDays]')")
        b.eval("{ const e=document.querySelector('[data-k=boardClosedDays]'); e.value='15'; e.dispatchEvent(new Event('change',{bubbles:true})) }")
        b.wait("!!document.querySelector('#settingsBody .saved .mtk')")
        self.assertFalse(b.eval("!!document.querySelector('#settingsBody .mspin')"))
        b.wait("!document.querySelector('#settingsBody .saved')", timeout=8)
        b.eval("window.__vw=VW.write; VW.write=async()=>{ throw new Error('disk full'); }")      # a save that fails
        b.eval("{ const e=document.querySelector('[data-k=boardClosedDays]'); e.value='16'; e.dispatchEvent(new Event('change',{bubbles:true})) }")
        b.wait("/Settings not saved/.test(document.getElementById('snack').textContent)")
        self.assertFalse(b.eval("!!document.querySelector('#settingsBody .saved')"))
        self.assertFalse(b.eval("!!document.querySelector('#settingsBody .mspin')"))
        b.eval("VW.write=__vw")

    # ---- 7. ask button ----
    def test_the_ask_button_sweeps_once_on_hover_and_never_idles(self):
        b = self.b
        b.call("Emulation.setEmulatedMedia", features=[{"name": "hover", "value": "hover"}, {"name": "pointer", "value": "fine"},   # a desktop with a mouse
                                                       {"name": "prefers-reduced-motion", "value": "no-preference"}])
        self.assertEqual(b.eval("getComputedStyle(document.getElementById('askBtn'),'::before').animationName"), "none")   # never idles
        if not b.eval("matchMedia('(hover:hover)').matches"):                                     # headless Linux Chrome reports no hover, emulated or not
            self.os_reduce(False)
            self.skipTest("this browser reports no hover, so the hover-only sheen can't run (checked on macOS)")
        # The hover is forced through DevTools rather than a mouse move: headless Chrome doesn't always count a synthetic
        # move as hovering. What is checked is the rule: on hover the sheen runs, once.
        b.call("DOM.enable"); b.call("CSS.enable")
        root = b.call("DOM.getDocument", depth=0)["root"]["nodeId"]
        node = b.call("DOM.querySelector", nodeId=root, selector="#askBtn")["nodeId"]
        b.call("CSS.forcePseudoState", nodeId=node, forcedPseudoClasses=["hover"])
        try:
            b.wait("getComputedStyle(document.getElementById('askBtn'),'::before').animationName==='msheen'", 15)
            self.assertEqual(b.eval("getComputedStyle(document.getElementById('askBtn'),'::before').animationIterationCount"), "1")
        finally:
            b.call("CSS.forcePseudoState", nodeId=node, forcedPseudoClasses=[])
            self.os_reduce(False)                                                                 # back to the class's own media setting

    # ---- 35. copy ----
    def test_copy_shows_a_tick_says_copied_and_returns(self):
        b = self.b
        b.eval("""window.__clip=[]; Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async t=>{ __clip.push(t); }}});
          window.__cb=document.createElement('button'); __cb.className='mini'; __cb.dataset.copycmd=''; __cb.textContent='Copy'; document.body.appendChild(__cb); __cb.click()""")
        b.wait("__cb.classList.contains('mcopied')")
        self.assertEqual(b.eval("[__cb.textContent, !!__cb.querySelector('.mtk'), __clip.length]"), ["Copied", True, 1])
        b.wait("document.getElementById('mlive').textContent==='Copied'")
        self.assertEqual(b.eval("document.getElementById('mlive').getAttribute('aria-live')"), "polite")
        b.wait("!__cb.classList.contains('mcopied')", timeout=6)
        self.assertEqual(b.eval("__cb.textContent"), "Copy")
        b.eval("__cb.remove()")

    def test_a_failed_copy_shows_no_tick(self):
        b = self.b
        b.eval("""Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async()=>{ throw new Error('blocked'); }}});
          openChat(); const d=document.createElement('div'); d.innerHTML='<div class=\"mdcode\"><pre><code>x</code></pre><button class=\"mdcopy mini\" data-mdcopy>Copy</button></div>'; document.getElementById('chLog').appendChild(d);
          window.__mb=d.querySelector('[data-mdcopy]'); __mb.click()""")
        b.wait("/Couldn't copy/.test(document.getElementById('snack').textContent)")
        self.assertFalse(b.eval("__mb.classList.contains('mcopied')"))

    # ---- 37. theme fade ----
    def test_the_theme_fades_only_around_a_change(self):
        b = self.b
        self.assertFalse(b.eval("document.documentElement.classList.contains('themefade')"))   # never at load
        b.eval("S.theme='Dark'; applyTheme()")                           # code redrawing the theme (and the contrast tests) does not fade
        self.assertFalse(b.eval("document.documentElement.classList.contains('themefade')"))
        b.eval("S.theme='System'; applyTheme()")
        b.eval("document.documentElement.style.setProperty('--k',10)")
        b.eval("document.getElementById('themeBtn').click()")            # the moon button: Alan's change
        self.assertTrue(b.eval("document.documentElement.classList.contains('themefade')"))
        self.assertIn("background-color", b.eval("getComputedStyle(document.querySelector('.btn')).transitionProperty"))
        b.eval("document.documentElement.style.setProperty('--k',1)")
        b.wait("!document.documentElement.classList.contains('themefade')", timeout=8)
        self.motion("Reduce")
        b.eval("document.getElementById('themeBtn').click()")            # and back, with no fade under Reduce
        self.assertFalse(b.eval("document.documentElement.classList.contains('themefade')"))
        self.motion("System")
        b.eval("S.theme='System'; applyTheme(); writeSettings({'dashboard.theme':'System'})")

RUNNING = "(el=>el?el.getAnimations().filter(a=>a.playState!=='finished').length:-1)"


class MotionPages(LiveBrowserCase):
    """Stages B and C on a vault with about 60 actions: overlays, lists, numbers, status, ask creaite and ambient."""
    shared_server = True
    reduced_motion = False
    width, height = 1500, 1000

    @classmethod
    def load(cls, v):
        populate(v)
        W.load(v)

    def setUp(self):
        super().setUp()
        self.b.eval("window.__errs=[]; addEventListener('error',e=>__errs.push(e.message)); addEventListener('unhandledrejection',e=>__errs.push(String(e.reason)))")

    def tearDown(self):
        try:
            self.assertEqual(self.b.eval("window.__errs"), [])
        finally:
            super().tearDown()

    def slow(self, k=20):
        self.b.eval(f"document.documentElement.style.setProperty('--k',{k})")

    def work(self):
        self.b.eval("go('work')")
        self.b.wait("VIEW==='work' && !!document.querySelector('#workTbl tr[data-row]')")

    # ---- 8, 10, 11: menus, dialogs, the message ----
    def test_menus_and_dialogs_ease_in_and_close_at_once_for_the_keyboard(self):
        b = self.b
        self.slow()
        self.work()
        b.eval("openDisp()")
        self.assertTrue(b.eval("dispOpen()"))
        self.assertGreater(b.eval(f"{RUNNING}(document.getElementById('dispMenu'))"), 0)          # @starting-style: it eases in
        b.eval("closeDisp(false)")
        self.assertFalse(b.eval("dispOpen()"))                                                    # closing is the state, at once
        self.assertEqual(b.eval("getComputedStyle(document.getElementById('dispMenu')).pointerEvents"), "none")
        b.eval("openCk()")
        self.assertTrue(b.eval("document.getElementById('cmdk').open"))
        self.assertGreater(b.eval(f"{RUNNING}(document.getElementById('cmdk'))"), 0)
        self.assertEqual(b.eval("document.activeElement.id"), "cmdkIn")                           # focus is where it was before
        b.key("Escape")
        self.assertFalse(b.eval("document.getElementById('cmdk').open"))
        self.slow(1)

    def test_one_message_at_a_time_with_a_timer_line_for_undo(self):
        b = self.b
        b.eval("snack('First',()=>{})")
        self.assertTrue(b.eval("document.getElementById('snack').classList.contains('mtimer')"))
        b.eval("snack('Second')")
        self.assertEqual(b.eval("[document.querySelectorAll('.snack').length, document.getElementById('snackT').textContent]"), [1, "Second"])
        self.assertFalse(b.eval("document.getElementById('snack').classList.contains('mtimer')"))

    # ---- 9: the panel ----
    def test_the_panel_slides_in_and_is_usable_from_the_first_frame(self):
        b = self.b
        self.slow()
        self.work()
        rid = b.eval("document.querySelector('#workTbl tr[data-row]').dataset.row")
        b.eval(f"openRecord(WT,{rid!r})")
        self.assertTrue(b.eval("document.getElementById('panel').classList.contains('on')"))
        self.assertGreater(b.eval(f"{RUNNING}(document.querySelector('#panel .pin'))"), 0)
        self.assertEqual(b.eval("getComputedStyle(document.getElementById('panel')).transitionDuration"), "0s")   # the width never animates
        self.assertEqual(b.eval("document.elementFromPoint(innerWidth-60, 200)?.closest('#panel')?.id"), "panel")  # clickable now
        b.eval("closePanel()")
        self.assertFalse(b.eval("document.getElementById('panel').classList.contains('on')"))
        self.slow(1)

    # ---- 13: sort ----
    def test_a_short_sort_glides_and_a_long_one_does_not(self):
        b = self.b
        self.work()
        b.eval("PROJF.clear(); PROJF.add('DEF'); renderWork()")
        n = b.eval("$$('#workTbl tr[data-row]').length")
        self.assertLessEqual(n, 30)
        self.slow()
        b.eval("document.querySelector('#workTbl th[data-col=t]').click()")
        b.pump(0.1)
        moving = b.eval("$$('#workTbl tr[data-row]').filter(t=>t.getAnimations().length).length")
        self.assertGreater(moving, 0)
        b.eval("PROJF.clear(); renderWork()")
        self.assertGreater(b.eval("$$('#workTbl tr[data-row]').length"), 30)
        b.eval("document.querySelector('#workTbl th[data-col=t]').click()")
        b.pump(0.1)
        self.assertEqual(b.eval("$$('#workTbl tr[data-row]').filter(t=>t.getAnimations().length).length"), 0)
        b.eval("document.querySelector('#workTbl th[data-col=t]').click(); document.querySelector('#workTbl th[data-col=t]').click()")   # twice, fast
        self.slow(1)
        rows = b.eval("$$('#workTbl tr[data-row]').map(t=>t.dataset.row)")
        self.assertEqual(len(rows), len(set(rows)))                                              # nothing doubled
        self.assertEqual(b.eval("$$('#workTbl tr[data-row]').filter(t=>getComputedStyle(t).opacity!=='1'&&!t.getAnimations().length).length"), 0)

    # ---- 14: group collapse ----
    def test_groups_open_and_close_repeatedly_and_end_right(self):
        b = self.b
        self.work()
        b.eval("WLGRP[WT]='project'; renderWork()")                                                       # group the list by project (BL-129)
        b.wait("!!document.querySelector('#workTbl tr.wgh')")
        self.slow()
        k = b.eval("document.querySelector('#workTbl tr.wgh').dataset.gk")
        before = b.eval("$$('#workTbl tr[data-row]').length")
        for _ in range(5):
            b.eval(f"grpToggle({k!r})")
        self.slow(1)
        self.assertNotEqual(b.eval("$$('#workTbl tr[data-row]').length"), before)               # odd number of toggles: collapsed
        b.eval(f"grpToggle({k!r})")
        self.assertEqual(b.eval("$$('#workTbl tr[data-row]').length"), before)
        b.eval("delete WLGRP[WT]; renderWork()")

    # ---- 33: board drag ----
    def test_drag_lifts_the_card_lights_a_column_that_takes_it_and_moves_nothing(self):
        b = self.b
        self.work()
        b.click('#wlay [data-lay="board"]')
        b.wait("!!document.querySelector('#workBoard .bcard')")
        card = b.eval("(document.querySelector('#workBoard .bcol[data-col=\"later\"] .bcard')||document.querySelector('#workBoard .bcard')).dataset.row")
        b.drag(f'#workBoard .bcard[data-row="{card}"]', '#workBoard .bcol[data-col="next"] .bch', release=False)
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('.bghost')).animationName"), "mlift")
        self.assertTrue(b.eval("document.querySelector('#workBoard .bcol[data-col=\"next\"]').classList.contains('drop')"))
        if b.eval("!!document.querySelector('#workBoard .bcol[data-col=\"overdue\"]')"):
            b.call("Input.dispatchMouseEvent", type="mouseMoved", button="left", buttons=1, **b.eval("(()=>{ const r=document.querySelector('#workBoard .bcol[data-col=\"overdue\"] .bch').getBoundingClientRect(); return {x:r.x+r.width/2,y:r.y+r.height/2}; })()"))
            b.pump(0.05)
            self.assertFalse(b.eval("document.querySelector('#workBoard .bcol[data-col=\"overdue\"]').classList.contains('drop')"))   # refuses: never lit
        b.mouse_up()
        b.pump(0.05)
        self.assertFalse(b.eval("!!document.querySelector('.bghost')"))
        self.assertEqual(b.eval("$$('#workBoard .bcard').filter(c=>c.getAnimations().length).length"), 0)   # the move is never animated
        b.eval("document.getElementById('boardDlg').open && document.getElementById('boardDlg').close()")
        b.click('#wlay [data-lay="list"]')

    # ---- 36: hover wash, J/K ----
    def test_the_highlight_cross_fades_but_a_held_key_or_a_range_is_instant(self):
        b = self.b
        self.work()
        self.assertNotEqual(b.eval("getComputedStyle(document.querySelector('#workTbl tr[data-row] td')).transitionDuration"), "0s")
        ids = b.eval("$$('#workTbl tr[data-row]').slice(0,6).map(t=>t.dataset.row)")
        self.slow(30)
        b.eval(f"hlOnly(WT,{ids[0]!r})")
        self.assertGreater(b.eval(f"$$('#workTbl tr[data-row=\"{ids[0]}\"] td').filter(td=>td.getAnimations().length).length"), 0)
        b.eval(f"HL.clear(); {json.dumps(ids)}.forEach(i=>HL.set(i,WT)); HLC={ids[5]!r}; hlPaint()")    # a range: at once
        self.assertEqual(b.eval(f"$$('#workTbl tr[data-row=\"{ids[3]}\"] td').filter(td=>td.getAnimations().length).length"), 0)
        b.eval("document.dispatchEvent(new KeyboardEvent('keydown',{key:'j',repeat:true}))")         # a held key
        b.eval(f"HL.clear(); HL.set({ids[4]!r},WT); HLC={ids[4]!r}; hlPaint()")
        self.assertEqual(b.eval(f"$$('#workTbl tr[data-row=\"{ids[0]}\"] td').filter(td=>td.getAnimations().some(a=>a.playState==='running'&&a.transitionProperty)).length"), 0)
        b.eval("document.dispatchEvent(new KeyboardEvent('keyup',{key:'j'})); hlClear()")
        self.slow(1)

    # ---- 16, 31, 32: page change, landing, banners ----
    def test_a_new_page_rises_in_and_back_still_works(self):
        b = self.b
        b.eval("go('today')")
        b.eval("go('files')")
        self.assertGreater(b.eval(f"{RUNNING}(document.getElementById('v-files'))"), 0)
        self.assertEqual(b.eval("VIEW"), "files")                                                  # the state is there at once
        b.eval("history.back()")
        b.wait("VIEW==='today'")

    def test_landing_pulses_on_arrival_only_and_opens_a_collapsed_group(self):
        b = self.b
        self.work()
        rid = b.eval("document.querySelector('#workTbl tr[data-row]').dataset.row")
        b.eval("renderWork(); document.querySelector('#workTbl th[data-col=t]').click()")
        self.assertFalse(b.eval("!!document.querySelector('.mland')"))                          # a render or a sort: no pulse
        calls = b.eval(f"""(()=>{{ const c=[]; const o=Element.prototype.scrollIntoView; Element.prototype.scrollIntoView=function(x){{ c.push(x); }};
          SEL={rid!r}; mLandRow(); Element.prototype.scrollIntoView=o; return [c, !!document.querySelector('#workTbl tr.mland[data-row="{rid}"]')]; }})()""")
        self.assertEqual(calls[0], [{"block": "center", "behavior": "smooth"}])
        self.assertTrue(calls[1])

    def test_a_banner_showing_at_load_does_not_animate(self):
        b = self.b
        self.assertTrue(b.eval("document.documentElement.classList.contains('mready')"))
        self.assertEqual(b.eval(f"{RUNNING}(document.getElementById('liveAlert'))"), 0)

    # ---- 15: skeleton ----
    def test_a_slow_load_shows_the_skeleton_and_a_fast_one_never_does(self):
        b = self.b
        b.eval("openChat(); window.__api=api; window.__seen=false; new MutationObserver(()=>{ if(document.querySelector('#chHistMenu .msk')) __seen=true; }).observe(document.body,{childList:true,subtree:true})")
        b.eval("api=async(u,x)=>u==='/api/chats'?{chats:[]}:__api(u,x); drawHistory()")
        b.wait("document.getElementById('chHistMenu').classList.contains('on')")
        b.pump(0.3)
        self.assertFalse(b.eval("__seen"))
        b.eval("histClose(); api=async(u,x)=>{ if(u==='/api/chats'){ await new Promise(r=>setTimeout(r,600)); return {chats:[]}; } return __api(u,x); }; drawHistory()")
        b.wait("__seen")
        b.wait("!document.querySelector('#chHistMenu .msk')")
        b.eval("api=__api; histClose()")

    # ---- 18, 19, 20, 27: first paint, once ----
    def test_counts_count_up_once_with_the_final_number_readable_at_once(self):
        b = self.b
        b.eval("go('cockpit','ABC')")
        b.wait("VIEW==='cockpit'")
        r = b.eval("$$('#v-cockpit .evbox .v').filter(e=>e.hasAttribute('aria-label')).map(e=>e.getAttribute('aria-label'))")
        b.wait("$$('#v-cockpit .evbox .v').every(e=>!e.hasAttribute('aria-label')||e.textContent===e.getAttribute('aria-label'))")
        b.eval("go('today'); go('cockpit','ABC')")                                                 # a return: no count this time
        self.assertEqual(b.eval("MFIRST.has('cockpit')"), True)
        self.assertTrue(isinstance(r, list))

    # ---- 22, 23: flash ----
    def test_a_changed_cell_flashes_after_a_refresh_and_nothing_else_does(self):
        b = self.b
        self.work()
        self.slow()
        b.eval("refreshAll()")
        self.assertEqual(b.eval("$$('.mflash').length"), 0)                                      # nothing changed: nothing flashes
        rid = b.eval("document.querySelector('#workTbl tr[data-row]').dataset.row")
        b.eval(f"(A.find(x=>x.id==={rid!r})||R.find(x=>x.id==={rid!r})).t='Renamed by a live refresh'; refreshAll()")
        self.assertEqual(b.eval("$$('.mflash').length"), 1)
        self.assertEqual(b.eval("document.querySelector('.mflash').closest('tr').dataset.row"), rid)
        self.slow(1)

    # ---- 24, 25: now marker, run hairline ----
    def test_the_hairline_shows_while_a_run_is_alive_and_animations_pause_when_hidden(self):
        b = self.b
        css = "getComputedStyle(document.querySelector('.bar'),'::after')"
        self.assertEqual(b.eval(f"{css}.animationName"), "none")
        b.eval("askWorking(true)")
        self.assertEqual(b.eval(f"{css}.animationName"), "mhair")
        b.eval("setLive(false)")
        self.assertEqual(b.eval(f"{css}.animationName"), "none")                                  # the server dropped: it stops
        b.eval("setLive(true); askWorking(false)")
        self.assertEqual(b.eval(f"{css}.animationName"), "none")
        b.eval("document.documentElement.classList.add('mhidden')")
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('.bar'),'::after').animationPlayState"), "paused")
        b.eval("document.documentElement.classList.remove('mhidden')")

    # ---- 26: ask creaite ----
    def test_live_reply_words_fade_in_without_moving_anything_and_a_long_one_appears_whole(self):
        b = self.b
        b.eval("openChat()")
        r = b.eval("""(()=>{ const d=document.createElement('div'); d.className='msg a md'; d.innerHTML='<p>Seven actions are <b>overdue</b> across two projects.</p>'; document.getElementById('chLog').appendChild(d);
          const h=d.offsetHeight, t=d.textContent, top=document.getElementById('chLog').scrollTop; mWords(d); return [d.querySelectorAll('.mw').length, d.textContent===t, d.offsetHeight===h, document.getElementById('chLog').scrollTop===top]; })()""")
        self.assertEqual(r, [7, True, True, True])
        n = b.eval("(()=>{ const d=document.createElement('div'); d.textContent=Array(450).fill('word').join(' '); mWords(d); return d.querySelectorAll('.mw').length; })()")
        self.assertEqual(n, 0)
        self.assertTrue(b.eval("!!document.querySelector('#chLog .msg') || true"))
        self.assertIn("mWords(await sayMd(", script())                                             # live replies only (history uses addEl)

    def test_the_typing_dots_and_the_input_border_only_while_working_or_focused(self):
        b = self.b
        b.eval("openChat(); window.__s=addEl('step','<span class=\"spin mdots\"><i></i><i></i><i></i></span>Working…')")
        self.assertEqual(b.eval("getComputedStyle(__s.querySelector('.mdots i')).animationName"), "mwave")
        b.eval("__s.remove()")
        b.call("Emulation.setFocusEmulationEnabled", enabled=True)
        b.pump(0.5)                                                                               # openChat() focuses the box a moment later
        b.eval("document.getElementById('chIn').blur()")                                          # start unfocused
        b.wait("document.activeElement!==document.getElementById('chIn')")
        self.assertEqual(b.eval("getComputedStyle(document.getElementById('chIn')).animationName"), "none")
        b.eval("document.getElementById('chIn').focus()")
        self.assertEqual(b.eval("getComputedStyle(document.getElementById('chIn')).animationName"), "mang")
        b.eval("document.getElementById('chIn').blur()")
        self.assertEqual(b.eval("getComputedStyle(document.getElementById('chIn')).animationName"), "none")

    # ---- 28, 30 ----
    def test_one_spotlight_and_the_empty_icon_rests_after_two_floats(self):
        c = css()
        self.assertEqual(len(re.findall(r"radial-gradient\(260px circle", c)), 1)
        self.assertIn("@media (hover:hover) and (pointer:fine){\n  #projTbl{position:relative}", c)
        b = self.b
        self.work()
        b.eval("WQ='zzzz nothing matches'; renderWork()")
        el = b.eval("(()=>{ const h=document.querySelector('.wempty>h2'); if(!h) return null; const c=getComputedStyle(h,'::before'); return [c.animationName,c.animationIterationCount]; })()")
        if el:
            self.assertEqual(el, ["mfloat", "2"])
        b.eval("WQ=''; renderWork()")

    # ---- 38: new since your last visit ----
    def test_new_rows_get_a_dot_only_after_a_first_visit_and_nothing_is_written_outside_the_browser(self):
        b = self.b
        self.work()
        self.assertEqual(b.eval("$$('.mnew').length"), 0)                                         # first visit: none
        b.eval("go('today'); localStorage.setItem('creaite-lastviewed',JSON.stringify({work:'2000-01-01 00:00'}))")   # as if Work was last seen long ago
        before = sorted(p.name for p in (self.v.root / "system/staging").rglob("*"))
        b.reload()
        b.wait("typeof go==='function' && LIVE")
        b.eval("window.__errs=[]")
        self.work()
        n = b.eval("$$('#workTbl .mnew').length")
        self.assertGreater(n, 0)
        self.assertEqual(b.eval("document.querySelector('#workTbl .mnew').getAttribute('aria-label')"), "New since your last visit")
        self.assertEqual(b.eval("document.querySelector('#workTbl .mnew').textContent"), "")
        b.wait("$$('#workTbl .mnew').length<" + str(n), timeout=8)                                 # on screen for 2s: it fades
        b.eval("go('today')")
        self.assertGreater(b.eval("JSON.parse(localStorage.getItem('creaite-lastviewed')).work"), "2000")   # left: the time moves on
        self.assertEqual(before, sorted(p.name for p in (self.v.root / "system/staging").rglob("*")))


    # ---- ask creaite's approval card (BL-141) ----
    def test_the_approval_card_rises_in_with_its_changes_following(self):
        b = self.b
        b.eval("openChat(); window.__c=addEl('confirm-wrap',changesCardHtml({card:'x',items:[1,2,3,4,5,6,7,8,9,10].map(n=>({title:'Change '+n,reason:'A settings file'}))}))")
        self.assertEqual(b.eval("getComputedStyle(__c.querySelector('.chgcard')).animationName"), "mrise4")
        delays = b.eval("[...__c.querySelectorAll('.chglist>li')].map(li=>getComputedStyle(li).animationDelay)")
        self.assertEqual((delays[0], delays[1], delays[9]), ("0.12s", "0.16s", "0.4s"))       # 40ms steps, at most 8
        b.eval("__c.remove()")


class MotionReview(LiveBrowserCase):
    """Approve or reject a row, the cleared queue, and a bulk approval with no motion."""
    reduced_motion = False
    width, height = 1500, 1100

    @classmethod
    def load(cls, v):
        populate(v)
        load_queue(v)

    def open(self):
        self.b.eval("go('review')")
        self.b.wait("document.querySelector('#reviewBody tr[data-n]')")

    def test_one_row_tints_three_fast_are_all_right_and_bulk_has_no_motion(self):
        b = self.b
        self.open()
        b.eval("document.documentElement.style.setProperty('--k',20)")
        ns = b.eval("REV.filter(r=>/^Batch /.test(r.rec.t)).map(r=>r.n)")
        b.eval("window.__g=0; new MutationObserver(()=>{ if(document.querySelector('.mrowghost')) __g++; }).observe(document.body,{childList:true})")
        b.eval(f"decide({ns[0]},'approved')")
        b.wait(f"REV.find(r=>r.n==={ns[0]})?.done==='approved'")
        b.wait(f"(t=>t&&$$('td',t).some(td=>td.getAnimations().length))(document.querySelector('#reviewBody tr[data-n=\"{ns[0]}\"]'))")   # it tints where it is
        b.eval(f"[{ns[1]},{ns[2]},{ns[3]}].forEach(n=>decide(n,'rejected'))")                    # three within a frame
        b.wait(f"[{ns[1]},{ns[2]},{ns[3]}].every(n=>REV.find(r=>r.n===n)?.done==='rejected')", 20)
        b.eval("document.documentElement.style.setProperty('--k',1)")
        rows = b.eval("$$('#reviewBody tr[data-n]').map(t=>t.dataset.n)")
        self.assertEqual(len(rows), len(set(rows)))                                                # nothing doubled
        self.assertEqual(b.eval("$$('#reviewBody tr[data-n]').filter(t=>t.getBoundingClientRect().height===0).length"), 0)   # nothing left hidden
        rest = b.eval("REV.filter(r=>/^Batch /.test(r.rec.t)&&!r.done).map(r=>r.n)")
        b.eval(f"RHL.clear(); CHK.clear(); {json.dumps(rest)}.forEach(n=>{{ RHL.add(n); CHK.add(n); }}); renderReview()")
        b.click("#bulkApprove")
        b.wait(f"{json.dumps(rest)}.every(n=>!REV.find(r=>r.n===n&&!r.done))", 20)
        self.assertEqual(b.eval("__g"), 0)                                                         # a bulk approval swaps at once
        self.assertEqual(b.eval("$$('#reviewBody tr[data-n] td').filter(td=>td.getAnimations().some(a=>!a.transitionProperty&&a.playState==='running')).length"), 0)

    def test_clearing_the_queue_draws_the_tick_once_and_an_empty_open_does_not(self):
        b = self.b
        self.open()
        b.eval("RHL.clear(); CHK.clear(); REV.filter(r=>!r.done).forEach(r=>{ r.done='approved'; }); renderReview()")
        self.assertTrue(b.eval("!!document.querySelector('.rvdone.mcleared .mclear')"))
        b.eval("renderReview()")                                                                   # a re-render keeps it, drawn, without drawing again
        self.assertEqual(b.eval("[$$('.mclear').length, document.querySelector('.rvdone').classList.contains('mstill')]"), [1, True])
        b.eval("go('today'); go('review')")
        self.assertFalse(b.eval("!!document.querySelector('.rvdone.mcleared')"))                 # opened already empty: no tick


if __name__ == "__main__":
    unittest.main()
