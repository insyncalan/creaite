"""BL-163, BL-191, BL-319 part 6: the sidebar, in a real browser against the real live server.

Run: python3 dev/tests/test_rail_customise.py   (needs Google Chrome; skipped otherwise)

The sidebar is drawn by components (components/sidebar/, dev/COMPONENTS.md) from stores/rail.js: RAIL_ITEMS and the saved
choice in settings.json, dashboard.rail = {order, more, hidden, display}, written through writeSettings (a backup and a log
line). The top holds Today, Work, Review, Projects, Reports (BL-337) and People; More, at the bottom, holds Intake, Files, Activity and
Settings and opens upwards (sideways when collapsed). The collapse toggle sits at the top-left before the wordmark, in the
same place either way; ⌘\\ does the same; the choice is remembered. Collapsed, the sidebar is a 56px rail of named icons
with badges. Customise sidebar moves pages between the two lists by drag, by its arrow buttons or by Alt and the arrow
keys; Today is always first; Icons only; Reset to default; Done saves, Cancel and Esc don't.
"""
import json
import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("CREAITE_NO_LAUNCH", "1")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

ALT, META, SHIFT = 1, 4, 8
TOP = ["today", "work", "review", "projects", "reports", "people"]
MORE = ["inbox", "files", "activity", "settings"]
RECT = "(s=>{ const r=document.querySelector(s).getBoundingClientRect(); return {l:Math.round(r.left),t:Math.round(r.top),r:Math.round(r.right),b:Math.round(r.bottom),w:Math.round(r.width)}; })"


class Sidebar(LiveBrowserCase):
    width, height = 1400, 900

    # ── helpers ──
    def settings(self):
        return json.loads((self.v.root / "system/config/settings.json").read_text())

    def saved(self):
        return self.settings().get("dashboard", {}).get("rail")

    def top(self):
        return self.b.eval("[...document.querySelectorAll('#railMain button[data-v]')].map(b=>b.dataset.v)")

    def more(self):
        return self.b.eval("[...document.querySelectorAll('#railMoreMenu button[data-v]')].map(b=>b.dataset.v)")

    def rect(self, sel):
        return self.b.eval(f"{RECT}({json.dumps(sel)})")

    def wait_saved(self, js_cond):
        """Wait until settings.json holds what the page shows (the write is asynchronous)."""
        for _ in range(100):
            r = self.saved()
            if r and self.b.eval(f"(r=>{js_cond})({json.dumps(r)})"):
                return r
            self.b.pump(0.05)
        self.fail(f"settings.json never matched: {js_cond}; it has {self.saved()}")

    def reload(self):
        self.b.reload(wait_for="typeof go==='function' && LIVE")

    def open_more(self):
        self.b.click("#railMore")
        self.b.wait("!document.getElementById('railMoreMenu').hidden")

    def open_customise(self):
        self.open_more()
        self.b.click("#railCustBtn")
        self.b.wait("document.getElementById('railCust').open")

    def row(self, rid, what):
        return f'#railCust li[data-rid="{rid}"] [data-mv="{what}"]'

    # ── the default sidebar ──
    def test_the_default_sidebar(self):
        b = self.b
        self.assertEqual(self.top(), TOP)
        self.assertEqual(self.more(), MORE)
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('.rail')).width"), "212px")
        self.assertEqual(b.eval("document.querySelector('.rail [data-v=today]').getAttribute('aria-current')"), "page")
        self.assertEqual(b.eval("document.querySelector('.rail [data-v=work] .rl').textContent"), "Work")   # names shown
        # the toggle sits at the top-left, before the wordmark
        tog, logo, first = self.rect("#railTog"), self.rect(".rail .logo"), self.rect("#railMain button")
        self.assertLess(tog["r"], logo["l"] + 1)
        self.assertLess(tog["b"], first["t"] + 1)
        self.assertEqual(b.eval("document.getElementById('railTog').getAttribute('aria-expanded')"), "true")
        self.assertEqual(b.eval("document.getElementById('railTog').getAttribute('aria-label')"), "Collapse the sidebar")
        self.assertEqual(b.eval("document.getElementById('railTog').getAttribute('aria-controls')"), "rail")
        # More is at the bottom, below the pages
        self.assertGreater(self.rect("#railMore")["t"], self.rect("#railMain")["b"] + 40)
        self.assertEqual(b.eval("document.getElementById('railMore').getAttribute('aria-haspopup')"), "menu")
        b.click('.rail button[data-v="work"]')                                                 # every button opens its page
        b.wait("VIEW==='work'")
        self.assertEqual(b.eval("document.querySelector('.rail [data-v=work]').getAttribute('aria-current')"), "page")
        self.assertEqual(b.eval("document.querySelector('.rail [data-v=today]').getAttribute('aria-current')"), "false")
        b.eval("go('cockpit','ABC')")                                                          # a project page marks Projects
        self.assertEqual(b.eval("document.querySelector('.rail [data-v=projects]').getAttribute('aria-current')"), "page")

    # ── collapse ──
    def test_the_toggle_collapses_in_place_says_what_it_will_do_and_is_remembered(self):
        b = self.b
        before = self.rect("#railTog")
        b.click("#railTog")
        self.wait_saved("r.display==='icons'")
        b.wait("getComputedStyle(document.querySelector('.rail')).width==='56px'")
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('.shell')).gridTemplateColumns.split(' ')[0]"), "56px")
        after = self.rect("#railTog")
        self.assertEqual((before["l"], before["t"], before["w"]), (after["l"], after["t"], after["w"]))   # in the same place
        t = b.eval("(e=>[e.getAttribute('aria-expanded'),e.getAttribute('aria-label'),e.dataset.tip])(document.getElementById('railTog'))")
        self.assertEqual(t, ["false", "Expand the sidebar", "Expand the sidebar"])
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('.rail .logo')).display"), "none")
        self.reload()
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('.rail')).width"), "56px")
        # ⌘\ expands it again, wherever focus is
        b.eval("go('work')")
        b.key("\\", META)
        self.wait_saved("r.display==='titles'")
        b.wait("getComputedStyle(document.querySelector('.rail')).width==='212px'")
        self.assertEqual(b.eval("document.getElementById('railTog').getAttribute('aria-label')"), "Collapse the sidebar")
        b.key("\\", META)
        self.wait_saved("r.display==='icons'")

    def test_collapsed_icons_are_named_with_tooltips_badges_and_the_accent_bar(self):
        b = self.b
        pending = b.eval("REV.filter(r=>!r.done).length")
        self.assertGreater(pending, 0)
        b.eval("railSave({...RAILCFG,display:'icons'})")
        self.wait_saved("r.display==='icons'")
        b.wait("getComputedStyle(document.querySelector('.rail')).width==='56px'")
        names = b.eval("[...document.querySelectorAll('#railMain button[data-v]')].map(x=>[x.getAttribute('aria-label'),x.dataset.tip,x.querySelector('.rl').offsetParent===null])")
        self.assertEqual([n[1] for n in names], ["Today", "Work", "Review", "Projects", "Reports", "People"])
        self.assertTrue(all(n[0].startswith(n[1]) and n[2] for n in names), names)            # named, words not shown
        self.assertEqual(names[2][0], f"Review, {pending} waiting")                            # the count in the name too
        r = b.eval("""(()=>{ const rail=document.querySelector('.rail').getBoundingClientRect(), bd=document.getElementById('revBadge'), x=bd.getBoundingClientRect();
          return {inside:x.left>=rail.left&&x.right<=rail.right+1, shown:getComputedStyle(bd).display!=='none', text:bd.textContent}; })()""")
        self.assertEqual(r, {"inside": True, "shown": True, "text": str(pending)})
        bar = b.eval("getComputedStyle(document.querySelector('.rail button[aria-current=page]'),'::before').width")
        self.assertEqual(bar, "3px")                                                          # the current page keeps its bar
        # the one tooltip, beside the rail
        b.eval("document.querySelector('.rail [data-v=people]').dispatchEvent(new MouseEvent('mouseover',{bubbles:true}))")
        b.wait("document.getElementById('tip')&&document.getElementById('tip').classList.contains('on')")
        self.assertEqual(b.eval("document.getElementById('tip').textContent"), "People")
        self.assertGreaterEqual(self.rect("#tip")["l"], self.rect(".rail")["r"])
        # expanded, no tooltip on a page (its name is shown)
        b.eval("railSave({...RAILCFG,display:'titles'})")
        self.wait_saved("r.display==='titles'")
        b.wait("!document.querySelector('.rail [data-v=people]').dataset.tip")

    def test_a_narrow_window_always_shows_the_icons_and_hides_the_toggle(self):
        b = self.b
        b.resize(1000, 800)
        b.wait("getComputedStyle(document.querySelector('.rail')).width==='56px'")         # under 1200px: collapsed
        b.resize(420, 800)
        b.wait("getComputedStyle(document.querySelector('.rail')).width==='48px'")         # under 480px: 48px, as before BL-319
        self.assertTrue(b.eval("document.getElementById('railTog').hidden"))
        self.assertTrue(b.eval("[...document.querySelectorAll('.rail button[data-v]')].every(x=>x.getAttribute('aria-label'))"))
        self.assertNotEqual((self.saved() or {}).get("display"), "icons")                     # nothing saved: it's the window
        b.resize(1400, 900)
        b.wait("getComputedStyle(document.querySelector('.rail')).width==='212px'")

    # ── More ──
    def test_more_opens_upwards_with_a_badge_for_what_waits_inside(self):
        b = self.b
        pending = b.eval("REV.filter(r=>!r.done).length")
        b.eval("railSave({...RAILCFG,order:['today','work','projects','people'],more:['review','inbox','files','activity','settings']})")
        self.wait_saved("r.more[0]==='review'")
        b.wait("document.getElementById('railMoreBadge').textContent!=='0'")
        new = b.eval("(D.inbox||[]).filter(f=>f.state==='new').length")
        m = b.eval("(()=>{ const m=document.getElementById('railMore'); return {label:m.getAttribute('aria-label'), badge:document.getElementById('railMoreBadge').textContent, shown:getComputedStyle(document.getElementById('railMoreBadge')).display}; })()")
        self.assertEqual(m["badge"], str(pending + new))
        self.assertNotEqual(m["shown"], "none")
        self.assertTrue(m["label"].startswith(f"More: Review has {pending} waiting"), m)   # a count and a name, never colour alone
        self.open_more()
        self.assertEqual(b.eval("document.getElementById('railMore').getAttribute('aria-expanded')"), "true")
        menu, btn = self.rect("#railMoreMenu"), self.rect("#railMore")
        self.assertLessEqual(menu["b"], btn["t"])                                             # upwards
        self.assertEqual(b.eval("document.activeElement.dataset.v"), "review")               # focus on the first page
        self.assertIn(str(pending), b.eval("document.querySelector('#railMoreMenu [data-v=review]').textContent"))
        self.assertEqual(b.eval("[...document.querySelectorAll('#railMoreMenu [role=menuitem]')].pop().textContent"), "Customise sidebar…")
        b.key("ArrowDown")
        self.assertEqual(b.eval("document.activeElement.dataset.v"), "inbox")
        b.key("End")
        self.assertEqual(b.eval("document.activeElement.id"), "railCustBtn")
        b.key("Home")
        b.key("ArrowUp")                                                                       # wraps round
        self.assertEqual(b.eval("document.activeElement.id"), "railCustBtn")
        b.key("Escape")
        b.wait("document.getElementById('railMoreMenu').hidden")
        self.assertEqual(b.eval("document.activeElement.id"), "railMore")
        self.open_more()
        b.click("#railMoreMenu [data-v=files]")                                                # choosing a page opens it and closes More
        b.wait("VIEW==='files'")
        b.wait("document.getElementById('railMoreMenu').hidden")
        self.assertEqual(b.eval("document.querySelector('#railMoreMenu [data-v=files]').getAttribute('aria-current')"), "page")
        # a click away closes it
        self.open_more()
        b.click("#v-files h1")
        b.wait("document.getElementById('railMoreMenu').hidden")

    def test_collapsed_more_opens_sideways(self):
        b = self.b
        b.eval("railSave({...RAILCFG,display:'icons'})")
        self.wait_saved("r.display==='icons'")
        b.wait("getComputedStyle(document.querySelector('.rail')).width==='56px'")
        self.open_more()
        self.assertGreaterEqual(self.rect("#railMoreMenu")["l"], self.rect(".rail")["r"])
        self.assertTrue(b.eval("[...document.querySelectorAll('#railMoreMenu .rl')].every(x=>x.offsetParent!==null)"))   # names shown in the menu
        self.assertEqual(b.eval("document.getElementById('railMore').dataset.tip").split(":")[0], "More")

    def test_an_empty_more_is_hidden(self):
        b = self.b
        b.eval("railSave({...RAILCFG,order:[...RAILCFG.order,...RAILCFG.more],more:[]})")
        self.wait_saved("!r.more.length")
        b.wait("!document.getElementById('railMore')")
        self.assertEqual(len(self.top()), 10)

    # ── Customise ──
    def test_customise_moves_pages_by_button_and_keyboard_and_saves_on_done(self):
        b = self.b
        self.open_customise()
        self.assertEqual(b.eval("document.getElementById('railCust').getAttribute('aria-labelledby')"), "railCustH")
        self.assertEqual(b.eval("document.getElementById('railCustH').textContent"), "Customise sidebar")
        self.assertTrue(b.eval("document.getElementById('railCust').contains(document.activeElement)"))
        lists = b.eval("[...document.querySelectorAll('#railCust ul')].map(u=>[document.getElementById(u.getAttribute('aria-labelledby')).textContent,[...u.children].map(li=>li.dataset.rid)])")
        self.assertEqual(lists, [["In the sidebar", TOP], ["In More", MORE]])
        # Today: always first, no controls
        self.assertIn("Always first", b.eval("document.querySelector('#railCust li[data-rid=today]').textContent"))
        self.assertEqual(b.eval("document.querySelectorAll('#railCust li[data-rid=today] button').length"), 0)
        self.assertTrue(b.eval(f"document.querySelector({json.dumps(self.row('work', 'up'))}).disabled"))   # nothing goes above Today
        # Settings to the sidebar, by its button; focus stays with it
        b.click(self.row("settings", "swap"))
        self.assertEqual(b.eval("document.querySelector('#railCust ul[data-zone=top]').lastElementChild.dataset.rid"), "settings")
        self.assertEqual(b.eval("document.activeElement.closest('li').dataset.rid"), "settings")
        self.assertEqual(b.eval("document.activeElement.getAttribute('aria-label')"), "Move Settings to More")
        self.assertIn("Settings moved to the sidebar", b.eval("document.querySelector('#railCust [aria-live]').textContent"))
        # People up, by its button
        b.click(self.row("people", "up"))
        # Work to More with Alt+→ on its row, then down within More with Alt+↓
        b.eval(f"document.querySelector({json.dumps(self.row('work', 'down'))}).focus()")
        b.key("ArrowRight", ALT)
        b.key("ArrowDown", ALT)                                                                # it was last: nothing happens
        b.key("ArrowUp", ALT)
        lists = b.eval("[...document.querySelectorAll('#railCust ul')].map(u=>[...u.children].map(li=>li.dataset.rid))")
        self.assertEqual(lists, [["today", "review", "projects", "people", "reports", "settings"], ["inbox", "files", "work", "activity"]])
        self.assertEqual(b.eval("document.activeElement.closest('li').dataset.rid"), "work")
        self.assertEqual(self.top(), TOP)                                                       # nothing changes until Done
        b.click("#railCustDone")
        b.wait("!document.getElementById('railCust').open")
        r = self.wait_saved("r.more.includes('work')")
        self.assertEqual((r["order"], r["more"]), (["today", "review", "projects", "people", "reports", "settings"], ["inbox", "files", "work", "activity"]))
        self.assertEqual(self.top(), r["order"])
        self.assertEqual(self.more(), r["more"])
        self.assertEqual(b.eval("document.activeElement.id"), "railMore")                     # focus back where it was opened from
        backups = list((self.v.root / "system/backups").glob("settings-*.json"))
        self.assertTrue(backups)
        log = (self.v.root / "system/config/settings-log.jsonl").read_text().splitlines()
        self.assertEqual(json.loads(log[-1])["key"], "dashboard.rail")
        self.reload()
        self.assertEqual(self.top(), r["order"])

    def test_customise_drag_between_the_lists(self):
        b = self.b
        self.open_customise()
        b.drag('#railCust li[data-rid="files"] [data-rgrip]', '#railCust li[data-rid="review"]', offset=(0, -8))
        lists = b.eval("[...document.querySelectorAll('#railCust ul')].map(u=>[...u.children].map(li=>li.dataset.rid))")
        self.assertEqual(lists, [["today", "work", "files", "review", "projects", "reports", "people"], ["inbox", "activity", "settings"]])
        b.drag('#railCust li[data-rid="work"] [data-rgrip]', '#railCust li[data-rid="today"]', offset=(0, -8))   # never above Today
        self.assertEqual(b.eval("document.querySelector('#railCust ul[data-zone=top]').firstElementChild.dataset.rid"), "today")
        b.click("#railCustDone")
        self.wait_saved("r.order.join()==='today,work,files,review,projects,reports,people'&&r.more.join()==='inbox,activity,settings'")

    def test_cancel_and_esc_keep_the_sidebar_and_reset_restores_the_default(self):
        b = self.b
        self.open_customise()
        b.click(self.row("work", "swap"))
        b.click("#railCustCancel")
        b.wait("!document.getElementById('railCust').open")
        self.assertEqual(self.top(), TOP)
        self.open_customise()
        self.assertIn("work", b.eval("[...document.querySelectorAll('#railCust ul[data-zone=top] li')].map(l=>l.dataset.rid)"))   # the draft starts afresh
        b.click(self.row("work", "swap"))
        b.key("Escape")
        b.wait("!document.getElementById('railCust').open")
        self.assertEqual(self.top(), TOP)
        self.assertEqual(b.eval("document.activeElement.id"), "railMore")
        # Reset to default, Icons only
        b.eval("railSave({order:['today','people','files'],more:['work'],display:'titles'})")
        self.wait_saved("r.order.join()==='today,people,files,review,projects,reports'")
        self.open_customise()
        b.click("#railCustReset")
        b.click("#railCustIcons")
        self.assertTrue(b.eval("document.getElementById('railCustIcons').checked"))
        self.assertEqual(b.eval("document.getElementById('railCustIcons').getAttribute('role')"), "switch")
        b.click("#railCustDone")
        r = self.wait_saved("r.display==='icons'")
        self.assertEqual((r["order"], r["more"]), (TOP, MORE))
        b.wait("getComputedStyle(document.querySelector('.rail')).width==='56px'")

    def test_right_click_settings_and_cmd_k_open_customise(self):
        b = self.b
        b.click(".rail [data-v=work]", button="right")
        b.wait("document.getElementById('railCust').open")
        b.key("Escape")
        b.wait("!document.getElementById('railCust').open")
        self.assertTrue(b.eval("document.activeElement.matches('.rail [data-v=work]')"))   # focus back on the page right-clicked
        b.eval("go('settings','appearance')")
        b.wait("document.getElementById('railCustSet')")
        b.click("#railCustSet")
        b.wait("document.getElementById('railCust').open")
        b.key("Escape")
        b.wait("!document.getElementById('railCust').open")
        self.assertEqual(b.eval("document.activeElement.id"), "railCustSet")
        self.assertIn("sidebar", b.eval("SETSECTIONS.find(x=>x.id==='appearance').kw"))
        b.key("k", META)
        b.wait("document.getElementById('cmdk').open")
        b.type("Customise the rail")                                                           # ⌘K's entry (ask.js keeps its words)
        b.key("Enter")
        b.wait("document.getElementById('railCust').open")

    def test_a_page_in_more_still_opens_from_cmd_k(self):
        b = self.b
        b.key("k", META)
        b.wait("document.getElementById('cmdk').open")
        b.type("Activity")
        b.key("Enter")
        b.wait("VIEW==='activity'")
        self.assertFalse(b.eval("document.getElementById('v-activity').hidden"))
        self.assertEqual(b.eval("document.querySelector('#railMoreMenu [data-v=activity]').getAttribute('aria-current')"), "page")

    # ── the saved choice ──
    def test_rail_norm_keeps_unknown_ids_out_today_first_and_appends_new_pages(self):
        b = self.b
        n = b.eval("railNorm({order:['bogus','review','today','settings'],more:['today','files','nosuch'],hidden:['bogus'],display:'sideways'})")
        self.assertEqual(n["order"], ["today", "review", "settings", "work", "projects", "reports", "people"])
        self.assertEqual(n["more"], ["files", "inbox", "activity"])
        self.assertEqual((n["hidden"], n["display"]), ([], "titles"))
        # a choice saved before More existed: the default More, plus what it had hidden
        n = b.eval("railNorm({order:['today','inbox','projects','work','people','review','files','activity','settings'],hidden:['people'],display:'icons'})")
        self.assertEqual(n, {"order": ["today", "projects", "work", "review", "reports"], "more": ["inbox", "files", "activity", "settings", "people"], "hidden": [], "display": "icons"})
        # a settings.json written before a page existed: the page is appended to its group, never lost
        s = self.settings()
        s.setdefault("dashboard", {})["rail"] = {"order": ["today", "people", "nosuch"], "more": ["settings"], "hidden": [], "display": "titles"}
        (self.v.root / "system/config/settings.json").write_text(json.dumps(s, indent=2))
        self.reload()
        self.assertEqual(self.top(), ["today", "people", "work", "review", "projects", "reports"])
        self.assertEqual(self.more(), ["settings", "inbox", "files", "activity"])

    def test_a_failed_write_puts_the_sidebar_back(self):
        b = self.b
        b.eval("needVault=async()=>false")                                                      # the vault can't be written
        b.eval("railSave({...RAILCFG,display:'icons'}).then(ok=>{window.__ok=ok})")
        b.wait("window.__ok===false")
        self.assertEqual(b.eval("RAILCFG.display"), "titles")
        b.wait("getComputedStyle(document.querySelector('.rail')).width==='212px'")


if __name__ == "__main__":
    unittest.main()
