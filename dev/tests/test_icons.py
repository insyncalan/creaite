"""Sprint icons (BL-158 to BL-161): icons in place of words. A real browser against the real live server.

BL-158: one icon set (ic), one tooltip (hover after 250ms, at once on keyboard focus, gone on Esc), every icon-only button named
(aria-label and data-tip with the same words), no typed glyphs, the theme icon shows where it will go.
BL-159: Work's toolbar (List/Board icons, Display sliders, the funnel with a count, the New tile, one New button with a menu on
Decisions). BL-160: Review (funnel, Display, Approve routine, the bulk bar, the row actions). BL-161: the rest of the legend.

Run: python3 dev/tests/test_icons.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SHOWN = "(sel=>{ const e=document.querySelector(sel); return !!(e&&e.offsetParent&&getComputedStyle(e).visibility!=='hidden'&&getComputedStyle(e).opacity!=='0'); })"
# every visible button with an icon and no words: its name and its tooltip. The name is the tooltip's words, or (BL-319's
# IconButton) those words then what it acts on ("Approve and save: Share the plan"); a blocked one's tooltip says why instead
UNNAMED = """[...document.querySelectorAll('button')].filter(b=>b.offsetParent&&b.querySelector('svg')&&!b.textContent.trim()&&!b.closest('.rail'))
  .filter(b=>{ const n=b.getAttribute('aria-label')||'', t=b.dataset.tip||''; if(!n.trim()||!t.trim()) return true;
    return !(n===t||n.startsWith(t+': ')||n.startsWith(t+' to ')||b.getAttribute('aria-disabled')==='true'); }).map(b=>b.outerHTML.slice(0,160))"""
GLYPHS = "×✕📅🌙▸⌄"


class IconSet(LiveBrowserCase):
    """BL-158"""
    shared_server = True

    def hover(self, sel):
        p = self.b.box(sel)
        self.b.call("Input.dispatchMouseEvent", type="mouseMoved", x=p["x"], y=p["y"], button="none")
        return p

    def away(self):
        self.b.call("Input.dispatchMouseEvent", type="mouseMoved", x=5, y=880, button="none")

    def tip(self):
        return self.b.eval("(()=>{ const t=document.getElementById('tip'); return t&&t.classList.contains('on')?t.textContent:null; })()")

    def test_every_icon_only_button_is_named_on_every_page(self):
        b = self.b
        for v in ("today", "work", "review", "inbox", "files", "people", "activity", "settings", "projects"):
            b.eval(f"go({v!r})")
            b.pump(0.3)
            self.assertEqual(b.eval(UNNAMED), [], v)
        b.eval("go('work'); openChat()")
        b.pump(0.3)
        self.assertEqual(b.eval(UNNAMED), [], "ask creaite")

    def test_one_helper_and_no_typed_glyphs_on_controls(self):
        b = self.b
        self.assertTrue(b.eval("typeof ic==='function' && Object.keys(ICONS).length>=29"))
        self.assertIn('stroke-width="1.8"', b.eval("ic('funnel')"))
        self.assertEqual(b.eval("[...document.querySelectorAll('svg[data-ic]')].filter(s=>!s.innerHTML).length"), 0)   # all painted
        for v in ("work", "review", "files", "inbox"):
            b.eval(f"go({v!r})")
            b.pump(0.3)
            seen = b.eval(f"[...document.querySelectorAll('button')].filter(b=>b.offsetParent&&/[{GLYPHS}]/.test(b.textContent)).map(b=>b.outerHTML.slice(0,120))")
            self.assertEqual(seen, [], v)
        b.eval("go('files')")
        b.pump(0.3)
        b.click("#fmBtn")
        self.assertEqual(b.eval("document.querySelector('#fmBtn svg').dataset.icn"), "funnel")
        self.assertEqual(b.eval("document.querySelector('[data-cal=fsFrom] svg').dataset.icn"), "calendar")
        b.eval("openChat()")
        self.assertEqual(b.eval("document.querySelector('#chatClose svg').dataset.icn"), "x")

    def test_the_tooltip_shows_on_hover_and_focus_and_goes_on_esc(self):
        b = self.b
        b.eval("go('work')")
        b.pump(0.3)
        self.hover("#themeBtn")
        b.pump(0.1)
        self.assertIsNone(self.tip())                                        # not at once on hover
        b.pump(0.35)
        self.assertIn("theme", self.tip())                                   # after 250ms
        self.assertEqual(b.eval("document.getElementById('tip').getAttribute('role')"), "tooltip")
        self.away()
        b.pump(0.3)
        self.assertIsNone(self.tip())
        b.eval("document.getElementById('themeBtn').focus()")               # keyboard focus: at once
        b.key("Tab", 8)
        b.key("Tab")
        b.pump(0.05)
        self.assertEqual(b.eval("document.activeElement.id"), "themeBtn")
        b.wait("(()=>{ const t=document.getElementById('tip'); return !!(t&&t.classList.contains('on')); })()", 5)    # #152: drawn a frame after the focus
        self.assertIn("theme", self.tip())
        b.key("Escape")
        b.wait("(()=>{ const t=document.getElementById('tip'); return !(t&&t.classList.contains('on')); })()", 5)
        self.assertIsNone(self.tip())

    def test_the_theme_icon_shows_the_destination(self):
        b = self.b
        b.eval("S.theme='Light'; applyTheme()")
        self.assertEqual(b.eval("$('#themeBtn svg').dataset.icn"), "moon")
        self.assertEqual(b.eval("$('#themeBtn').dataset.tip"), "Switch to dark theme")
        self.assertEqual(b.eval("$('#themeBtn').getAttribute('aria-label')"), "Switch to dark theme")
        b.click("#themeBtn")
        b.pump(0.2)
        self.assertEqual(b.eval("document.documentElement.dataset.theme"), "dark")
        self.assertEqual(b.eval("$('#themeBtn svg').dataset.icn"), "sun")
        self.assertEqual(b.eval("$('#themeBtn').dataset.tip"), "Switch to light theme")
        b.eval("S.theme='Light'; applyTheme()")

    def test_a_collapsed_group_turns_its_chevron(self):
        b = self.b
        b.eval("go('work'); setLayout('actions','board')")
        b.pump(0.3)
        btn = "#workBoard .bcoll"
        self.assertEqual(b.eval(f"getComputedStyle(document.querySelector('{btn} svg')).transform"), "none")
        b.click(btn)
        b.pump(0.2)
        self.assertEqual(b.eval(f"document.querySelector('{btn}').getAttribute('aria-expanded')"), "false")
        self.assertNotEqual(b.eval(f"getComputedStyle(document.querySelector('{btn} svg')).transform"), "none")
        b.click(btn)
        b.eval("setLayout('actions','list')")


class WorkToolbar(LiveBrowserCase):
    """BL-159"""

    def work(self, tab="actions"):
        self.b.eval("go('work')")
        self.b.click(f'#wtabs [data-t="{tab}"]')
        self.b.wait(f"WT==={tab!r}")
        self.b.pump(0.2)

    def test_list_and_board_are_an_icon_switch_and_not_in_display(self):
        b = self.b
        self.work()
        self.assertEqual(b.eval("[...document.querySelectorAll('#wlay button')].map(x=>[x.getAttribute('aria-label'),x.dataset.tip,x.textContent.trim(),!!x.querySelector('svg')])"),
                         [["List", "List", "", True], ["Board", "Board", "", True]])
        b.click('#wlay [data-lay="board"]')
        b.wait("layoutOf(WT)==='board'")
        self.assertEqual(b.eval("[...document.querySelectorAll('#wlay button')].map(x=>x.getAttribute('aria-pressed'))"), ["false", "true"])
        self.assertTrue(b.eval("!document.getElementById('workBoard').hidden"))
        b.click('#wlay [data-lay="list"]')
        b.wait("layoutOf(WT)==='list'")
        self.assertEqual(b.eval("[...document.querySelectorAll('#wlay button')].map(x=>x.getAttribute('aria-pressed'))"), ["true", "false"])
        b.click("#dispBtn")
        self.assertTrue(b.eval("$('#dispMenu').classList.contains('on')"))
        self.assertFalse(b.eval("!!document.querySelector('#dispMenu [data-dlay]')"))        # the copy in Display is gone
        self.assertEqual(b.eval("[$('#dispBtn').dataset.key, $('#dispBtn').textContent.trim()]"), ["D", ""])

    def test_the_funnel_opens_the_picker_and_counts_the_filters(self):
        b = self.b
        self.work()
        b.eval("OWN.clear(); PROJF.clear(); PRIF.clear(); Object.values(FX).forEach(x=>x&&x.clear&&x.clear()); renderWork()")
        self.assertFalse(b.eval("!!document.querySelector('#moreBtn .fcount')"))
        self.assertEqual(b.eval("$('#moreBtn').dataset.tip"), "Add a filter")
        self.assertEqual(b.eval("$('#moreBtn').dataset.key"), "F")
        b.click("#moreBtn")
        b.wait("$('#moreMenu').classList.contains('on')")
        b.key("Escape")
        b.eval("PRIF.add('Urgent'); renderWork()")
        self.assertEqual(b.eval("$('#moreBtn .fcount').textContent"), "1")
        self.assertEqual(b.eval("$('#moreBtn').getAttribute('aria-label')"), "Add a filter: 1 on")
        b.eval("PRIF.clear(); renderWork()")

    def test_the_new_tile_says_the_tab_and_opens_the_peek(self):
        b = self.b
        for tab, word, kind in (("actions", "New action", "actions"), ("raid", "New RAID item", "raid")):
            self.work(tab)
            self.assertEqual(b.eval("[$('#newBtn').getAttribute('aria-label'), $('#newBtn').dataset.tip, $('#newBtn').textContent.trim()]"), [word, word, word])
            self.assertFalse(b.eval("$('#newBtn').classList.contains('primary')"))
            b.click("#newBtn")
            b.wait("CUR&&CUR.mode==='new'&&document.getElementById('panel').classList.contains('peek')")   # BL-179: the empty peek
            self.assertEqual(b.eval("CUR.k"), kind)
            self.assertFalse(b.eval("newMenuOpen()"))
            b.eval("EDITING=false; closePanel()")
        self.work("all")
        self.assertTrue(b.eval("document.getElementById('newBtn').hidden"))

    def test_decisions_has_one_new_button_with_a_menu(self):
        b = self.b
        self.work("decisions")
        self.assertFalse(b.eval("!!document.getElementById('newDecNeeded')"))
        b.click("#newBtn")
        b.wait("newMenuOpen()")
        self.assertEqual(b.eval("$('#newDecMenu').getAttribute('role')"), "menu")
        self.assertEqual(b.eval("[...document.querySelectorAll('#newDecMenu [role=menuitem] b')].map(x=>x.textContent)"), ["Record a decision", "Ask for a decision"])
        self.assertEqual(b.eval("document.activeElement.dataset.newd"), "made")
        b.key("ArrowDown")
        self.assertEqual(b.eval("document.activeElement.dataset.newd"), "needed")
        b.key("Escape")
        b.wait("!newMenuOpen() && document.activeElement.id==='newBtn'", 5)   # #152: focus goes back in an effect after the redraw: wait for it, don't race it
        self.assertEqual(b.eval("[newMenuOpen(), document.activeElement.id, $('#newBtn').getAttribute('aria-expanded')]"), [False, "newBtn", "false"])
        b.click("#newBtn")
        b.wait("newMenuOpen()", 5)
        b.wait("(document.body.click(), !newMenuOpen())", 5)                 # a click away closes it (tried until the menu's listener is in: it is added in an effect)
        self.assertFalse(b.eval("newMenuOpen()"))
        b.click("#newBtn")
        b.click('#newDecMenu [data-newd="made"]')
        b.wait("CUR&&CUR.mode==='new'")
        self.assertEqual(b.eval("[CUR.draft.st, CUR.draft.date===TODAY]"), ["Made", True])   # BL-179: the peek's draft
        b.eval("EDITING=false; closePanel()")
        b.click("#newBtn")
        b.click('#newDecMenu [data-newd="needed"]')
        b.wait("CUR&&CUR.mode==='new'&&CUR.draft.st==='Pending'")
        self.assertEqual(b.eval("[CUR.draft.st, CUR.draft.date]"), ["Pending", ""])


class ReviewIcons(LiveBrowserCase):
    """BL-160"""

    def test_toolbar_bulk_bar_and_rows(self):
        b = self.b
        b.eval("go('review',null,{legacy:true})")
        b.pump(0.4)
        self.assertEqual(b.eval("[$('#rvDispBtn').textContent.trim(), $('#rvDispBtn').getAttribute('aria-label')===$('#rvDispBtn').dataset.tip]"), ["", True])
        self.assertEqual(b.eval("$('#rvMore').dataset.tip"), "Add a filter")
        self.assertFalse(b.eval("'key' in $('#rvMore').dataset"))                  # F is Work's key only: no key shown here
        self.assertTrue(b.eval("/^Approve routine \\(\\d+\\)$/.test($('#routineBtn').textContent.trim()) && $('#routineBtn').querySelector('svg').dataset.icn==='checks'"))
        self.assertIn("Minutes, new decisions and new risks stay for you", b.eval("$('#routineBtn').dataset.tip"))
        b.eval("RVF.k.add('actions'); rvChanged()")
        self.assertEqual(b.eval("$('#rvMore .fcount').textContent"), "1")
        b.eval("RVF.k.clear(); rvChanged()")
        row = "#reviewBody tr[data-n]:not(.mparent)"
        b.eval(f"RHL.add(+document.querySelector('{row}').dataset.n); renderReview()")
        self.assertTrue(b.eval("/^Approve \\(\\d+\\)$/.test($('#bulkApprove').textContent) && !!$('#bulkApprove svg')"))
        self.assertTrue(b.eval("$('#bulkReject').textContent==='Reject with a reason R' && !!$('#bulkReject svg')"))   # BL-315: one menu
        self.assertEqual(b.eval("[$('#rvClear').dataset.tip, $('#rvClear').dataset.key]"), ["Clear the selection", "Esc"])
        acts = b.eval(f"""(()=>{{ const tr=document.querySelector('{row}'); const q=s=>tr.querySelector(s);
          return {{approve:q('[data-act=a]').textContent.trim(), reject:[q('[data-act=r]').textContent.trim(), q('[data-act=r]').getAttribute('aria-label'), q('[data-act=r]').dataset.key],
                  edit:[q('[data-act=e]').getAttribute('aria-label'), q('[data-act=e]').dataset.key, !!q('[data-act=e]').closest('.rowact')]}}; }})()""")
        self.assertEqual(acts, {"approve": "Approve", "reject": ["", "Reject, with a reason", "R"], "edit": ["Edit", "E", True]})
        b.eval("RHL.clear(); CHK.clear(); RSEL=0; renderReview()")
        # Edit shows on the cursor row, and on hover or focus of another row; not otherwise
        op = "(i=>getComputedStyle(document.querySelectorAll('#reviewBody tr[data-n]')[i].querySelector('.rowact')).opacity)"
        b.call("Input.dispatchMouseEvent", type="mouseMoved", x=5, y=5, button="none")
        b.pump(0.1)
        self.assertEqual(b.eval(f"{op}(0)"), "1")
        self.assertEqual(b.eval(f"{op}(2)"), "0")
        b.eval("document.querySelectorAll('#reviewBody tr[data-n]')[2].querySelector('[data-act=e]').focus()")
        self.assertEqual(b.eval(f"{op}(2)"), "1")


class TheRest(LiveBrowserCase):
    """BL-161"""
    shared_server = True

    def named(self, sel):
        return self.b.eval(f"[...document.querySelectorAll({sel!r})].map(x=>[x.getAttribute('aria-label'), x.dataset.tip, x.textContent.trim(), (x.querySelector('svg')||{{dataset:{{}}}}).dataset.icn])")

    def test_project_and_person_pages(self):
        b = self.b
        b.eval("go('cockpit','ABC')")
        b.pump(0.3)
        # #223: no Weekly report / Client report buttons; #225: a Reports icon beside Files, same size and style
        self.assertEqual(self.named(".cockfoot button"), [
            ["Reports", "Reports", "", "filetext"],
            ["Browse files", "Browse files", "", "folder"],
            ["Project settings", "Project settings", "", "gear"]])      # #228: the page's gear beside Files
        self.assertEqual(b.eval("document.querySelectorAll('.cockfoot [data-ask]').length"), 0)
        self.assertEqual(b.eval("[...document.querySelectorAll('.cockfoot button')].some(x=>/Weekly report|Client report/.test(x.textContent))"), False)
        box = b.eval("[...document.querySelectorAll('.cockfoot button')].map(x=>{const r=x.getBoundingClientRect();return [Math.round(r.width),Math.round(r.height),x.className,getComputedStyle(x).borderRadius]})")
        self.assertEqual(box[0][:2], box[1][:2])
        self.assertEqual(box[0][3], box[1][3])
        self.assertEqual(box[0][2].replace("bd", "").strip(), box[1][2].replace("bd", "").strip())
        self.assertEqual(box[2][3], box[1][3])
        # keyboard reachable: a real button, in tab order, opens the hub on Enter/click
        self.assertEqual(b.eval("document.querySelector('.cockfoot [data-reports]').tabIndex"), 0)
        b.eval("document.querySelector('.cockfoot [data-reports]').click()")
        b.pump(0.3)
        self.assertEqual(b.eval("location.hash"), "#reporting=ABC")
        self.assertEqual(b.eval("VIEW"), "reporting")
        b.eval("go('cockpit','ABC')")
        b.pump(0.3)
        b.eval("go('person','Omar Ali')")
        b.pump(0.3)
        self.assertEqual(self.named("#ppEdit")[0][:3], ["Edit details", "Edit details", ""])
        self.assertEqual([x[2:] for x in self.named("#ppEmail, #ppHand")], [["Draft email", "mail"], ["Hand over…", "handover"]])

    def test_rows_use_icons(self):
        b = self.b
        b.eval("go('files')")
        b.pump(0.3)
        self.assertEqual(self.named("#filesTbl button[data-openfile]")[0], ["Open folder", "Open folder", "", "folderopen"])
        b.eval("go('inbox',null,{legacy:true})")
        b.pump(0.3)
        got = self.named("#inboxTbl [data-inprev], #inboxTbl [data-inrm]")
        self.assertIn(["Preview", "Preview", "", "eye"], got)
        self.assertIn(["Remove from Intake", "Remove from Intake", "", "trash"], got)

    def test_send_turns_into_stop(self):
        b = self.b
        b.eval("openChat()")
        self.assertEqual(self.named("#chSend")[0], ["Send", "Send", "", "arrowup"])
        self.assertEqual(b.eval("$('#chSend').dataset.key"), "Enter")
        b.eval("setRunning(true)")
        self.assertEqual(self.named("#chSend")[0], ["Stop", "Stop", "", "stop"])
        self.assertIsNone(b.eval("$('#chSend').dataset.key"))               # #130: Esc never stops a run, so Stop shows no key
        r = b.eval("(()=>{ const r=$('#chSend').getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; })()")
        self.assertEqual(r, [32, 32])                                        # the same round button, not a second Stop
        b.eval("setRunning(false)")
        self.assertEqual(self.named("#chSend")[0][3], "arrowup")

    def test_the_copy_icon_ticks(self):
        b = self.b
        b.eval("go('settings'); const q=$('#setq'); q.value='live server'; q.dispatchEvent(new Event('input',{bubbles:true}))")
        b.pump(0.3)
        sel = "#settingsBody [data-copycmd]"
        b.wait(f"!!document.querySelector({sel!r})")
        self.assertEqual(self.named(sel)[0][3], "copy")
        b.eval(f"navigator.clipboard.writeText=()=>Promise.resolve(); document.querySelector({sel!r}).click()")
        b.wait(f"document.querySelector({sel!r}+' svg').dataset.icn==='check'", 3)
        self.assertEqual(b.eval(f"document.querySelector({sel!r}).textContent.trim()"), "")   # no word grows
        b.wait(f"document.querySelector({sel!r}+' svg').dataset.icn==='copy'", 3)


if __name__ == "__main__":
    unittest.main()
