"""#156 (folds in #139): the left rail's three states, the wordmark toggle, the active page, the counts, the hover flyouts and
the Labels when collapsed setting, in a real browser against the real live server.

Run: python3 dev/tests/test_rail_states.py   (needs Google Chrome; skipped otherwise)

Done when (the issue's list):
- expanded 224px (names beside the icons); collapsed 76px with each name under its icon (Labels when collapsed on, the
  default) or 56px icons only (off); the setting is dashboard.rail_labels, saved to settings.json and kept across a reload; the
  window's first state is expanded at 1100px and wider, collapsed below, and under 900px the rail stays collapsed;
- the wordmark is the toggle (aria-expanded, "Collapse the rail" / "Expand the rail", Enter and Space, "c_" when collapsed), no
  other toggle; icons only never opens the full rail on hover;
- the current page is a tonal pill with a bold name, a thicker icon and the 3px bar (icon 3:1 on the pill, light and dark, and
  in forced colours a border); counts: Review's an accent pill, More's amber and named ("More, 1 problem"), 99+ at most;
- flyouts on Projects (active projects by name with health), Work (four lists with open counts) and More (with Health, Help and the
  Customise sidebar block), on the hover standard's times (open after 200 ms, close 300 ms after leaving), by keyboard
  (→ or ↓ opens with focus inside, arrows, Esc back to the button); the icon alone still goes to the page;
- Customise sidebar stays (Labels when collapsed beside Icons only; a saved display "icons" opens as icons only).
Dates are pinned (CREAITE_NOW) so the page's day does not move under the tests.
"""
import json
import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("CREAITE_NO_LAUNCH", "1")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

META = 4
ARCH, CLOSED = "Archived Demo Programme", "Closed Demo Programme"
RGB = "(s=>{ const m=s.match(/[\\d.]+/g).map(Number); return m.slice(0,3); })"


def lum(c):
    def f(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (f(x) for x in c)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


class RailStates(LiveBrowserCase):
    width, height = 1400, 900

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": "2026-10-16 09:00"}

    # ── helpers ──
    def settings(self):
        return json.loads((self.v.root / "system/config/settings.json").read_text())

    def rail_w(self):
        return self.b.eval("Math.round(document.querySelector('.rail').getBoundingClientRect().width)")

    def wait_w(self, w):
        self.b.wait(f"Math.round(document.querySelector('.rail').getBoundingClientRect().width)==={w}", 5)

    def rect(self, sel):
        return self.b.eval(f"(s=>{{ const r=document.querySelector(s).getBoundingClientRect(); return {{l:r.left,t:r.top,r:r.right,b:r.bottom,w:r.width,h:r.height}}; }})({json.dumps(sel)})")

    def point(self, x, y):
        self.b.call("Input.dispatchMouseEvent", type="mouseMoved", x=x, y=y, button="none")

    def hover(self, sel):
        p = self.b.box(sel)
        self.point(p["x"], p["y"])

    def away(self):
        self.point(900, 600)

    def btn(self, v):
        return "#railMore" if v == "more" else f".rail #railMain [data-v={v}]"

    def fly(self, v):
        return "#railMoreMenu" if v == "more" else f"#railFly-{v}"

    def expanded(self, v):
        return self.b.eval(f"document.querySelector('{self.btn(v)}').getAttribute('aria-expanded')")

    def open_by_hover(self, v):
        self.hover(self.btn(v))
        self.b.wait(f"document.querySelector('{self.btn(v)}').getAttribute('aria-expanded')==='true'", 5)
        self.b.wait(f"(e=>e&&!e.hidden&&e.getClientRects().length>0)(document.querySelector('{self.fly(v)}'))", 5)

    def names(self, v):
        return self.b.eval(f"[...document.querySelectorAll('{self.fly(v)} [role=menuitem] .mname')].map(x=>x.textContent.trim())")

    def collapse(self):
        if self.rail_w() > 100:
            self.b.click("#railTog")
            self.wait_w(76)

    def set_labels(self, on):
        self.b.eval(f"railSetLabels({'true' if on else 'false'})")
        self.b.wait(f"railLabelsOn.value==={'true' if on else 'false'}", 5)
        for _ in range(100):
            if self.settings()["dashboard"].get("rail_labels") is on:
                return
            self.b.pump(0.05)
        self.fail("rail_labels never saved")

    def colours(self, sel):
        return self.b.eval(f"""(s=>{{ const e=document.querySelector(s), c=getComputedStyle(e), p={RGB};
          const bg=p(c.backgroundColor), ic=p(getComputedStyle(e.querySelector('svg')).color); return {{bg, ic}}; }})({json.dumps(sel)})""")

    # ── the three states ──
    def test_expanded_labels_under_icons_and_icons_only(self):
        b = self.b
        self.assertEqual(self.rail_w(), 224)                                                   # 1400px: expanded by default
        t = self.rect(".rail [data-v=work] .rl")["l"] - self.rect(".rail [data-v=work] svg")["r"]
        self.assertGreater(t, 4)                                                               # the name is beside the icon
        self.assertEqual(self.rect(".rail [data-v=work]")["h"], 36)
        b.click("#railTog")
        self.wait_w(76)
        ic, rl = self.rect(".rail [data-v=work] svg"), self.rect(".rail [data-v=work] .rl")
        self.assertGreaterEqual(rl["t"], ic["b"] - 1)                                          # under the icon
        self.assertEqual(self.rect(".rail [data-v=work]")["h"], 52)
        self.assertEqual(b.eval("document.querySelector('.rail').className.includes('labelled')"), True)
        self.set_labels(False)
        self.wait_w(56)
        self.assertTrue(b.eval("[...document.querySelectorAll('.rail #railMain .rl')].every(x=>x.offsetParent===null)"))
        self.assertEqual(self.rect(".rail [data-v=work]")["h"], 36)
        self.set_labels(True)
        self.wait_w(76)

    def test_the_setting_is_saved_kept_across_a_reload_and_is_an_essential(self):
        b = self.b
        self.assertTrue(self.settings()["dashboard"]["rail_labels"])                           # on by default
        self.collapse()
        self.set_labels(False)
        self.wait_w(56)
        b.reload("typeof go==='function' && LIVE")
        self.assertEqual(self.rail_w(), 56)                                                    # the collapse is this browser's, the labels the file's
        b.eval("go('settings','essentials')")
        b.wait("[...document.querySelectorAll('#settingsBody .srow')].some(r=>r.textContent.includes('Labels when collapsed'))", 10)
        sw = "[...document.querySelectorAll('#settingsBody .srow')].find(r=>r.textContent.includes('Labels when collapsed')).querySelector('input.switch')"
        self.assertFalse(b.eval(f"{sw}.checked"))
        b.eval(f"{sw}.click()")                                                                # on from Settings: the rail follows
        self.wait_w(76)
        self.assertTrue(self.settings()["dashboard"]["rail_labels"])

    def test_more_has_the_labels_switch_and_the_dialog_offers_it_beside_icons_only(self):
        b = self.b
        self.collapse()
        self.hover("#railMore")
        b.wait("!document.getElementById('railMoreMenu').hidden", 5)
        self.assertEqual(b.eval("document.getElementById('railLabelsSw').getAttribute('aria-checked')"), "true")
        b.click("#railLabelsSw")                                                               # a switch: the menu stays open
        self.wait_w(56)
        self.assertEqual(b.eval("document.getElementById('railLabelsSw').getAttribute('aria-checked')"), "false")
        self.assertFalse(b.eval("document.getElementById('railMoreMenu').hidden"))
        self.assertFalse(self.settings()["dashboard"]["rail_labels"])
        b.click("#railCustBtn")                                                                # Customise sidebar... opens the dialog
        b.wait("document.getElementById('railCust').open")
        self.assertFalse(b.eval("document.getElementById('railCustLabels').checked"))
        self.assertTrue(b.eval("!!document.getElementById('railCustIcons')"))
        b.click("#railCustLabels")
        b.click("#railCustDone")
        b.wait("!document.getElementById('railCust').open")
        self.wait_w(76)
        self.assertTrue(self.settings()["dashboard"]["rail_labels"])

    def test_a_saved_display_icons_opens_as_collapsed_icons_only(self):
        b = self.b
        s = self.settings()
        s["dashboard"]["rail"] = {"order": ["today", "work", "review", "projects", "people"], "more": ["inbox", "files", "activity", "settings"],
                                  "hidden": [], "display": "icons"}
        (self.v.root / "system/config/settings.json").write_text(json.dumps(s, indent=2))
        b.reload("typeof go==='function' && LIVE")
        self.assertEqual(self.rail_w(), 56)
        self.assertFalse(b.eval("railLabelsOn.value && document.querySelector('.rail').className.includes('labelled')"))
        b.click("#railTog")                                                                    # and the wordmark opens it
        self.wait_w(224)

    # ── the wordmark toggle ──
    def test_the_wordmark_is_the_toggle(self):
        b = self.b
        self.assertEqual(b.eval("document.querySelectorAll('.rail .rtog, #railTog, .rail [aria-controls=rail]').length"), 1)   # one toggle
        e = "document.getElementById('railTog')"
        self.assertEqual(b.eval(f"[{e}.tagName, {e}.getAttribute('aria-expanded'), {e}.getAttribute('aria-label')]"),
                         ["BUTTON", "true", "Collapse the rail"])
        self.assertTrue(b.eval(f"{e}.contains(document.querySelector('.rail .wm'))"))         # the wordmark is inside it
        b.eval(f"{e}.focus()")
        b.key("Enter")
        self.wait_w(76)
        self.assertEqual(b.eval(f"[{e}.getAttribute('aria-expanded'), {e}.getAttribute('aria-label'), document.activeElement===({e})]"),
                         ["false", "Expand the rail", True])
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('.rail .cmark')).display"), "block")   # "c_"
        self.assertEqual(b.eval("document.querySelector('.rail .cmark').textContent"), "c_")
        b.key(" ")
        self.wait_w(224)
        # a small chevron shows on hover when expanded
        b.eval("document.activeElement.blur()")
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('.rail .rchev')).opacity"), "0")
        self.hover("#railTog")
        b.wait("getComputedStyle(document.querySelector('.rail .rchev')).opacity==='1'", 5)
        # no other collapse control in the rail or the bar
        self.assertEqual(b.eval("[...document.querySelectorAll('.rail button, header.bar button')].filter(x=>/collapse|expand/i.test(x.getAttribute('aria-label')||'')).length"), 1)

    def test_icons_only_never_opens_the_full_rail_on_hover(self):
        b = self.b
        self.collapse()
        self.set_labels(False)
        self.wait_w(56)
        for v in ("today", "review", "people"):
            self.hover(self.btn(v))
            b.pump(0.8)
            self.assertEqual(self.rail_w(), 56)
        self.hover(self.btn("people"))
        b.wait("document.getElementById('tip')&&document.getElementById('tip').classList.contains('on')", 5)   # a tooltip, after 400 ms
        self.assertEqual(b.eval("document.getElementById('tip').textContent"), "People")
        self.away()
        self.hover(self.btn("projects"))
        b.wait("!!document.querySelector('#railFly-projects')", 5)                              # a flyout, not a tooltip
        self.assertEqual(self.rail_w(), 56)

    # ── the first state by width, and under 900px ──
    def test_first_state_by_width_and_the_rail_stays_collapsed_under_900px(self):
        b = self.b
        b.resize(1100, 800)
        self.wait_w(224)                                                                       # 1100px and wider: expanded
        b.resize(1099, 800)
        self.wait_w(76)                                                                        # below: collapsed
        b.click("#railTog")                                                                    # and can be opened
        self.wait_w(224)
        b.resize(900, 800)
        self.wait_w(224)                                                                       # a choice made here is kept
        b.eval("localStorage.clear()")
        b.reload("typeof go==='function' && LIVE")
        self.wait_w(76)
        self.assertFalse(b.eval("document.getElementById('railTog').disabled"))
        self.open_by_hover("projects")                                                         # flyouts work at 900px
        self.assertGreaterEqual(self.rect("#railFly-projects")["l"], self.rect(".rail")["r"])
        self.assertLessEqual(self.rect("#railFly-projects")["r"], 900)
        b.resize(899, 800)
        b.wait("innerWidth===899 && document.getElementById('railTog').disabled", 5)
        self.wait_w(76)                # under 900px: the pinned, collapsed rail
        self.assertEqual(b.eval("document.getElementById('railTog').getAttribute('aria-expanded')"), "false")

    # ── the active page ──
    def test_active_page_is_a_pill_with_a_bar_and_meets_contrast_light_and_dark_and_forced_colours(self):
        b = self.b
        cur = ".rail [data-v=today]"
        for mode in ("light", "dark"):
            b.eval(f"document.documentElement.setAttribute('data-theme','{mode}')")
            b.pump(0.3)
            c = self.colours(cur)
            self.assertGreaterEqual(ratio(c["ic"], c["bg"]), 3.0, (mode, c))                   # the icon 3:1 on the pill
            st = b.eval(f"(e=>[getComputedStyle(e).fontWeight, getComputedStyle(e.querySelector('svg')).strokeWidth, getComputedStyle(e,'::before').width, e.getAttribute('aria-current')])(document.querySelector('{cur}'))")
            self.assertEqual(st, ["700", "2.2px", "3px", "page"])
            other = self.colours(".rail [data-v=work]")                                        # an inactive icon 3:1 on the rail
            rail = b.eval(f"{RGB}(getComputedStyle(document.querySelector('.rail')).backgroundColor)")
            self.assertGreaterEqual(ratio(other["ic"], rail), 3.0, (mode, other, rail))
            self.assertNotEqual(c["bg"], rail)                                                 # the pill stands out from the rail
        b.eval("go('cockpit', P[0].code)")                                                     # a project page keeps Projects current
        self.assertEqual(b.eval("document.querySelector('.rail [data-v=projects]').getAttribute('aria-current')"), "page")
        b.call("Emulation.setEmulatedMedia", features=[{"name": "forced-colors", "value": "active"}])
        b.pump(0.3)
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('.rail [data-v=projects]')).borderTopWidth"), "2px")   # not colour alone
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('.rail')).borderRightWidth"), "1px")                   # the rail keeps its edge
        b.call("Emulation.setEmulatedMedia", features=[{"name": "forced-colors", "value": "none"}])

    # ── the counts ──
    def test_counts_review_accent_more_amber_and_named_99_plus_and_corner_badges(self):
        b = self.b
        n = b.eval("REV.filter(r=>!r.done).length")
        self.assertGreater(n, 0)
        accent = b.eval(f"{RGB}(getComputedStyle(document.documentElement).getPropertyValue('--accent').trim() ? (()=>{{ const d=document.createElement('i'); d.style.color='var(--accent)'; document.body.appendChild(d); const c=getComputedStyle(d).color; d.remove(); return c; }})() : '')")
        bg = b.eval(f"{RGB}(getComputedStyle(document.getElementById('revBadge')).backgroundColor)")
        self.assertEqual(bg, accent)                                                           # an accent pill, not red
        b.eval("setRailCount('review', 120, '120 waiting')")
        b.wait("document.getElementById('revBadge').textContent==='99+'", 5)
        b.eval(f"setRailCount('review', {n})")
        b.eval("healthCount.value=1")
        b.wait("document.getElementById('railMoreBadge').textContent==='1'", 5)
        warn = b.eval("(()=>{ const d=document.createElement('i'); d.style.color='var(--warn-soft)'; document.body.appendChild(d); const c=getComputedStyle(d).color; d.remove(); return c; })()")
        self.assertEqual(b.eval("getComputedStyle(document.getElementById('railMoreBadge')).backgroundColor"), warn)   # amber
        self.assertEqual(b.eval("document.getElementById('railMore').getAttribute('aria-label')"), "More, 1 problem")
        b.eval("healthCount.value=2")
        b.wait("document.getElementById('railMore').getAttribute('aria-label')==='More, 2 problems'", 5)
        b.eval("healthCount.value=1")
        self.hover("#railMore")
        b.wait("!document.getElementById('railMoreMenu').hidden", 5)
        self.assertIn("1 problem", b.eval("document.getElementById('railHealth').textContent"))     # the flyout names it
        self.away()
        b.wait("document.getElementById('railMoreMenu').hidden", 5)
        # collapsed: the badge sits on the icon's corner, inside the rail
        self.collapse()
        r = b.eval("""(()=>{ const rail=document.querySelector('.rail').getBoundingClientRect(), x=document.getElementById('revBadge').getBoundingClientRect(),
          i=document.querySelector('.rail [data-v=review] svg').getBoundingClientRect();
          return {inside:x.left>=rail.left&&x.right<=rail.right+1, onIcon:x.top<=i.top+8&&x.left>=i.left-4}; })()""")
        self.assertEqual(r, {"inside": True, "onIcon": True})
        self.assertNotIn("red", b.eval("getComputedStyle(document.getElementById('revBadge')).backgroundColor"))

    # ── the flyouts ──
    def seed(self):
        self.b.eval(f"""(()=>{{ P.push({{code:'ZZA',name:{ARCH!r},active:true,archived:true,health:'On track'}},
          {{code:'ZZC',name:{CLOSED!r},active:false,health:'At risk'}}); }})()""")

    def test_projects_flyout_lists_active_projects_by_name_with_health_and_opens_the_page(self):
        b = self.b
        self.seed()
        self.open_by_hover("projects")
        got = self.names("projects")
        want = b.eval("P.filter(p=>p.active!==false&&!p.archived).map(p=>p.name)")
        self.assertTrue(want)
        self.assertEqual(got, want)
        self.assertNotIn(ARCH, got)
        self.assertNotIn(CLOSED, got)
        self.assertFalse([n for n in got if n in b.eval("P.map(p=>p.code)")])                  # names, never codes
        self.assertEqual(b.eval(f"document.querySelector('{self.fly('projects')}').getAttribute('role')"), "menu")
        self.assertEqual(b.eval(f"document.querySelector('{self.fly('projects')}').getAttribute('aria-label')"), "Projects")
        self.assertLessEqual(self.rect(self.fly("projects"))["h"], 361)
        code = b.eval("P.filter(p=>p.active!==false&&!p.archived)[0].code")
        b.click(f"{self.fly('projects')} [role=menuitem]:nth-child(1)")
        b.wait(f"shared.VIEW==='cockpit' && shared.COCK==={code!r}", 5)
        b.wait(f"!document.querySelector('{self.fly('projects')}')", 5)                         # the pick closed it
        b.eval("go('work')")
        b.click(self.btn("projects"))                                                          # the icon alone: as before
        b.wait("shared.VIEW==='projects'", 5)
        self.assertFalse(b.eval(f"!!document.querySelector('{self.fly('projects')}')"))

    def test_a_project_added_or_closed_while_open_shows_the_change(self):
        b = self.b
        b.eval("P.push({code:'ZZN',name:'New Demo Programme',active:true,health:'On track'})")
        self.open_by_hover("projects")
        self.assertIn("New Demo Programme", self.names("projects"))
        self.away()
        b.wait("document.querySelector('#railMain [data-v=projects]').getAttribute('aria-expanded')==='false'", 5)
        b.eval("P.find(p=>p.code==='ZZN').active=false")
        self.open_by_hover("projects")
        self.assertNotIn("New Demo Programme", self.names("projects"))

    def test_work_flyout_lists_four_lists_with_counts_and_a_pick_opens_that_list(self):
        b = self.b
        self.open_by_hover("work")
        self.assertEqual(self.names("work"), ["Actions", "RAID", "Decisions", "All items"])
        counts = b.eval(f"[...document.querySelectorAll('{self.fly('work')} .fcount')].map(x=>+x.textContent)")
        self.assertEqual(counts[0], b.eval("A.filter(a=>OPENST(a.st)).length"))
        self.assertEqual(counts[3], sum(counts[:3]))
        b.click(f"{self.fly('work')} [role=menuitem]:nth-child(2)")
        b.wait("shared.VIEW==='work' && shared.WT==='raid'", 5)
        b.wait(f"!document.querySelector('{self.fly('work')}')", 5)

    def test_the_hover_standards_times_and_one_flyout_at_a_time(self):
        b = self.b
        self.hover(self.btn("projects"))
        b.pump(0.08)
        self.assertEqual(self.expanded("projects"), "false")                                   # not instant
        b.wait(f"document.querySelector('{self.btn('projects')}').getAttribute('aria-expanded')==='true'", 5)
        self.assertEqual(b.eval("document.activeElement===document.body || !document.activeElement.closest('[role=menu]')"), True)   # focus stays put
        self.hover(f"{self.fly('projects')} [role=menuitem]")                                  # onto the flyout: stays open
        b.pump(0.6)
        self.assertEqual(self.expanded("projects"), "true")
        self.away()
        b.pump(0.1)
        self.assertEqual(self.expanded("projects"), "true")                                    # a grace before it closes
        b.wait(f"document.querySelector('{self.btn('projects')}').getAttribute('aria-expanded')==='false'", 5)
        self.hover(self.btn("work"))
        b.wait(f"document.querySelector('{self.btn('work')}').getAttribute('aria-expanded')==='true'", 5)
        self.hover("#railMore")
        b.wait("document.querySelector('#railMore').getAttribute('aria-expanded')==='true'", 5)
        b.wait(f"document.querySelector('{self.btn('work')}').getAttribute('aria-expanded')==='false'", 5)
        self.assertEqual(b.eval("document.querySelectorAll('#railMain [aria-expanded=true], .railmore [aria-expanded=true]').length"), 1)

    def test_flyout_keyboard_arrows_open_with_focus_inside_esc_returns_and_enter_goes_to_the_page(self):
        b = self.b
        b.eval(f"document.querySelector('{self.btn('work')}').focus()")
        b.key("ArrowRight")
        b.wait(f"!!document.querySelector('{self.fly('work')}')", 5)
        self.assertEqual(b.eval(f"document.activeElement.closest('{self.fly('work')}')!==null"), True)   # focus inside, no delay
        b.key("ArrowDown")
        self.assertEqual(b.eval("document.activeElement.textContent.includes('RAID')"), True)
        b.key("Escape")
        b.wait(f"!document.querySelector('{self.fly('work')}')", 5)
        self.assertEqual(b.eval(f"document.activeElement===document.querySelector('{self.btn('work')}')"), True)
        b.key("ArrowDown")                                                                     # ↓ opens it too
        b.wait(f"!!document.querySelector('{self.fly('work')}')", 5)
        b.key("ArrowDown"); b.key("ArrowDown")
        b.key("Enter")                                                                         # Enter picks: Decisions
        b.wait("shared.VIEW==='work' && shared.WT==='decisions'", 5)
        b.eval(f"document.querySelector('{self.btn('projects')}').focus()")
        b.key("Enter")                                                                         # Enter on the icon: the page, as before
        b.wait("shared.VIEW==='projects'", 5)
        # More: → opens with focus inside, Esc closes with focus back
        b.eval("document.getElementById('railMore').focus()")
        b.key("ArrowRight")
        b.wait("!document.getElementById('railMoreMenu').hidden", 5)
        self.assertEqual(b.eval("document.getElementById('railMoreMenu').contains(document.activeElement)"), True)
        b.key("Escape")
        b.wait("document.getElementById('railMoreMenu').hidden", 5)
        self.assertEqual(b.eval("document.activeElement.id"), "railMore")

    def test_collapsed_flyouts_sit_beside_the_rail_and_a_click_on_more_still_toggles(self):
        b = self.b
        self.collapse()
        self.open_by_hover("work")
        self.assertGreaterEqual(self.rect(self.fly("work"))["l"], self.rect(".rail")["r"])
        self.assertFalse(b.eval(f"!!document.querySelector('{self.btn('work')}').dataset.tip"))   # no tooltip over it
        self.away()
        b.wait(f"!document.querySelector('{self.fly('work')}')", 5)
        b.click("#railMore")
        b.wait("!document.getElementById('railMoreMenu').hidden", 5)
        b.pump(0.5)
        self.assertEqual(self.expanded("more"), "true")                                        # a click opens it and it stays
        b.click("#railMore")
        b.wait("document.getElementById('railMoreMenu').hidden", 5)

    def test_a_page_moved_into_more_still_appears_in_its_flyout(self):
        b = self.b
        b.eval("railSave({...RAILCFG,order:['today','work','projects','people'],more:['review','inbox','files','activity','settings']})")
        b.wait("!document.querySelector('#railMain [data-v=review]')", 5)
        self.open_by_hover("more")
        self.assertIn("review", b.eval("[...document.querySelectorAll('#railMoreMenu [data-v]')].map(x=>x.dataset.v)"))
        self.assertEqual(b.eval("[...document.querySelectorAll('#railMoreMenu [role^=menuitem] .rl')].map(x=>x.textContent).slice(-3)"),
                         ["Help", "Customise sidebar…", "Labels when collapsed"])


if __name__ == "__main__":
    unittest.main()
