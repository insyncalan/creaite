"""#158 Phase B part 5: the first-visit line, "Press ? for help with <screen>", once per screen. A real browser, the real live server.

Run: python3 dev/tests/test_help_firstline.py   (needs Google Chrome; skipped otherwise)

Alan's rules (17-10-2026): one quiet line directly under the title, accent left edge, once on each of the eight screens; any key or
click clears it and still does its normal job; ? clears it and opens the panel; never over an open item, a dialog or ask creaite
(it waits until they close) nor while typing; remembered per screen in this browser (once per page load if storage fails); a
setting under Settings > Essentials > Look and help turns it off; no animation under reduced motion.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import TEST_PALETTES_JS, LiveBrowserCase  # noqa: E402
from test_tracker import REPO  # noqa: E402

sys.path.insert(0, str(REPO / "system" / "scripts"))
import settings_catalogue as sc  # noqa: E402

LINE = "document.querySelector('.view:not([hidden]) .hline')"


class Catalogue(unittest.TestCase):
    def test_the_setting_is_an_essential_in_look_and_help_and_on_by_default(self):
        rows = [r for r in sc.ESSENTIAL_ROWS if "help.press_line" in r[3]]
        self.assertEqual([(r[0], r[1]) for r in rows], [("Look and help", "Show the Press ? line on each screen")])
        import json
        d = json.loads((REPO / "system/templates/settings-defaults.json").read_text(encoding="utf-8"))
        self.assertIs(d["help"]["press_line"], True)
        self.assertIn("help.press_line", sc.CATALOGUE)


class FirstLine(LiveBrowserCase):
    shared_server = True

    def go(self, view):
        self.b.eval(f"go('{view}')")
        self.b.pump(0.25)

    def line(self):
        return self.b.eval(f"(()=>{{ const l={LINE}; return l?{{t:l.textContent, prev:l.previousElementSibling&&(l.previousElementSibling.tagName+(l.previousElementSibling.className?'.'+l.previousElementSibling.className:'')), "
                           "edge:getComputedStyle(l).borderLeftWidth, colour:getComputedStyle(l).borderLeftColor}:null; })()")

    def test_it_shows_once_per_screen_under_the_title(self):
        for view, name in (("today", "Today"), ("work", "Work"), ("review", "Review"), ("projects", "Projects"), ("people", "People"),
                           ("inbox", "Intake"), ("files", "Files")):
            self.go(view)
            r = self.line()
            self.assertIsNotNone(r, view)
            self.assertEqual(r["t"], f"Press ? for help with {name}")
            self.assertTrue(r["prev"].startswith(("H1", "DIV.hhead")), (view, r["prev"]))        # directly under the title
            self.assertEqual(r["edge"], "3px")                                                   # the accent left edge
            self.b.eval("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Shift',bubbles:true}))")
        self.go("today")
        self.assertIsNone(self.line())                                                          # a screen already shown has no line again
        seen = self.b.eval("JSON.parse(localStorage.getItem('creaite-help-line-seen'))")
        self.assertEqual(sorted(seen), ["Files", "Intake", "People", "Projects", "Review", "Today", "Work"])

    def test_notes_has_one_too(self):
        self.b.eval("go('notes','_portfolio')")
        self.b.pump(0.5)
        self.assertEqual((self.line() or {}).get("t"), "Press ? for help with Notes")

    def test_a_key_or_a_click_clears_it_and_still_does_its_job(self):
        b = self.b
        self.go("files")
        self.assertIsNotNone(self.line())
        b.eval("document.activeElement&&document.activeElement.blur()")
        b.key("n")                                                                              # N opens a note: the key is not swallowed
        b.pump(0.3)
        self.assertIsNone(self.line())
        self.assertTrue(b.eval("!!document.querySelector('#capDrawer.on, #capDrawer[open], #capDrawer:not([hidden])')"))
        b.eval("closeCapture&&closeCapture()")
        self.go("people")
        self.assertIsNotNone(self.line())
        b.click("#askBtn")                                                                      # a click: ask creaite opens as it always does
        b.pump(0.3)
        self.assertIsNone(self.line())
        self.assertTrue(b.eval("document.querySelector('#chat').classList.contains('on')"))

    def test_the_question_mark_clears_it_and_opens_the_panel(self):
        b = self.b
        self.go("people")
        self.assertIsNotNone(self.line())
        b.eval("document.activeElement&&document.activeElement.blur()")
        b.key("?")
        b.pump(0.2)
        self.assertIsNone(self.line())
        self.assertTrue(b.eval("document.querySelector('#hpanel').classList.contains('on')"))

    def test_it_waits_for_an_open_item_a_dialog_ask_creaite_and_a_field(self):
        b = self.b
        b.call("Emulation.setFocusEmulationEnabled", enabled=True)                               # a headless page fires focusout only when it has focus
        b.eval("go('work'); openRecord('actions', A[0].id)")                                      # an item open over Work, before the line could come
        b.pump(0.4)
        self.assertTrue(b.eval("document.querySelector('#panel').classList.contains('on')"))
        self.assertIsNone(self.line())
        b.eval("closePanel()")
        b.pump(0.3)
        self.assertEqual((self.line() or {}).get("t"), "Press ? for help with Work")             # it came when the item closed
        b.eval("openChat()")
        self.go("review")
        self.assertIsNone(self.line())
        b.eval("closeChat()")
        b.pump(0.3)
        self.assertEqual((self.line() or {}).get("t"), "Press ? for help with Review")
        b.eval("(()=>{ const d=document.createElement('dialog'); d.id='tdlg'; d.innerHTML='<button>OK</button>'; document.body.append(d); d.showModal(); })()")
        self.go("files")
        self.assertIsNone(self.line())
        b.eval("document.querySelector('#tdlg').close()")
        b.pump(0.3)
        self.assertEqual((self.line() or {}).get("t"), "Press ? for help with Files")
        b.eval("(()=>{ const i=document.createElement('input'); i.id='tmp'; document.body.append(i); i.focus(); })()")
        self.go("projects")
        self.assertIsNone(self.line())                                                           # while typing in a field
        b.eval("document.querySelector('#tmp').blur()")
        b.pump(0.3)
        self.assertEqual((self.line() or {}).get("t"), "Press ? for help with Projects")

    def test_if_storage_fails_it_shows_once_per_page_load(self):
        b = self.b
        b.eval("Storage.prototype.getItem=()=>{ throw new Error('x'); }; Storage.prototype.setItem=()=>{ throw new Error('x'); };")
        self.go("work")
        self.assertIsNotNone(self.line())
        b.eval("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Shift',bubbles:true}))")
        self.go("review")
        self.go("work")
        self.assertIsNone(self.line())

    def test_the_setting_turns_it_off_and_its_row_is_in_look_and_help(self):
        b = self.b
        self.go("settings")
        self.assertTrue(b.eval("document.body.textContent.includes('Show the Press ? line on each screen')"))
        flip = """(()=>{ const r=[...document.querySelectorAll('#settingsBody .srow')].find(x=>x.textContent.includes('Show the Press ? line on each screen'));
          const sw=r&&r.querySelector('input.switch'); if(!sw) return null; sw.click(); return sw.checked; })()"""
        self.assertIs(b.eval(flip), False)                                                       # on by default; the switch turns it off
        b.pump(0.6)
        self.assertIs(b.eval("S.pressLine"), False)
        self.go("files")
        self.assertIsNone(self.line())
        self.go("settings")
        self.assertIs(b.eval(flip), True)                                                        # and back on, for the other tests
        b.pump(0.6)
        self.assertIs(b.eval("S.pressLine"), True)

    def test_no_animation_under_reduced_motion(self):
        self.go("people")
        self.assertEqual(self.b.eval(f"getComputedStyle({LINE}).animationDuration"), "0s")

    def test_desktop_and_900_light_and_dark_on_both_palettes(self):
        b = self.b
        for width in (1400, 900):
            b.resize(width, 900)
            b.eval("localStorage.removeItem('creaite-help-line-seen')")
            self.go("review")
            r = b.eval("""(()=>{ const l=%s; const lum=c=>{ const [r,g,b]=c.match(/[\\d.]+/g).slice(0,3).map(Number).map(v=>{ v/=255; return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4); }); return 0.2126*r+0.7152*g+0.0722*b; };
              const ratio=(a,b)=>{ const x=lum(a), y=lum(b); return (Math.max(x,y)+0.05)/(Math.min(x,y)+0.05); };
              const bgOf=el=>{ for(let e=el;e;e=e.parentElement){ const c=getComputedStyle(e).backgroundColor; if(!/rgba\\(0, 0, 0, 0\\)|transparent/.test(c)) return c; } return 'rgb(255,255,255)'; };
              const res={}; for(const pal of %s) for(const mode of ['Light','Dark']){ S.palette=pal; S.theme=mode; applyTheme(); res[pal+'|'+mode]=l?ratio(getComputedStyle(l).color,bgOf(l)):-1; }
              return {res, side:document.documentElement.scrollWidth<=innerWidth+1}; })()""" % (LINE, TEST_PALETTES_JS))
            self.assertTrue(r["side"], width)
            self.assertEqual({k: v for k, v in r["res"].items() if v < 4.5}, {}, width)


if __name__ == "__main__":
    unittest.main()
