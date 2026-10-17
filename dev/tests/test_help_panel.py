"""#158 Phase B part 4: the ? key's panel, the foot line and the empty-state links. A real browser against the real live server.

Run: python3 dev/tests/test_help_panel.py   (the page tests need Google Chrome; skipped otherwise)

The lists are `Screen:` lines in help.md. ? opens a side panel on the right with the screen's jobs, a link to its Reference page and
"Search all of Help"; it never fires while typing or over a dialog; Esc closes it in one press, as a layer (before a peek), and
focus goes back; ask creaite and the panel are never both open.
"""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import TEST_PALETTES_JS, LiveBrowserCase  # noqa: E402
from test_tracker import REPO  # noqa: E402

sys.path.insert(0, str(REPO / "system" / "scripts"))
import build_dashboard as bd  # noqa: E402

SCREENS = {"today": "Today", "work": "Work", "review": "Review", "projects": "Projects", "people": "People", "notes": "Notes",
           "inbox": "Intake", "files": "Files"}


class ScreenLines(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = bd.help_sections()

    def test_every_id_resolves_and_the_lists_are_two_to_five_jobs(self):
        tasks = {t["id"] for t in self.h["tasks"]}
        refs = {s["id"] for s in self.h["sections"]}
        self.assertEqual(list(self.h["screens"]), ["Today", "Work", "Review", "Projects", "People", "Notes", "Intake", "Files"])
        for name, sc in self.h["screens"].items():
            self.assertTrue(1 <= len(sc["jobs"]) <= 5, name)           # two to five; Files has the one the brief lists
            for i in sc["jobs"]:
                self.assertIn(i, tasks, f"{name} → {i}")
            self.assertIn(sc["ref"], refs, f"{name} reference")

    def test_the_starting_lists_are_the_agreed_ones(self):
        s = self.h["screens"]
        self.assertEqual(s["Review"]["jobs"], ["review-and-approve-proposals", "reject-with-a-reason", "fix-the-wrong-project",
                                               "when-it-looks-like-something-you-have", "when-creaite-says-looks-done"])
        self.assertEqual(s["Today"]["jobs"], ["start-the-day", "close-the-day", "prepare-for-a-meeting"])
        self.assertEqual(s["Intake"]["jobs"], ["turn-a-meeting-into-minutes", "why-isnt-my-meeting-in-intake"])

    def test_the_lines_are_not_on_the_page(self):
        for t in self.h["tabs"]:
            self.assertNotIn("Screen:", re.sub(r"<[^>]+>", " ", t["html"]))


class Panel(LiveBrowserCase):
    shared_server = True

    def open_panel(self, view):
        b = self.b
        b.eval("closeChat(); helpPanelClose(false)")
        b.eval(f"go('{view}')")
        b.eval("document.activeElement&&document.activeElement.blur()")
        b.key("?")
        b.pump(0.15)

    def test_each_screen_opens_its_jobs_and_esc_closes_in_one_press(self):
        b = self.b
        for view, name in SCREENS.items():
            self.open_panel(view)
            r = b.eval("""(()=>{ const p=document.querySelector('#hpanel'); return {on:p.classList.contains('on'), h:p.querySelector('h2').textContent,
              jobs:[...p.querySelectorAll('.hpn-jobs a')].length, ref:!!p.querySelector('.hpn-ref'), search:!!p.querySelector('[data-hp-search]'),
              focus:document.activeElement.id, hash:location.hash, right:Math.round(innerWidth-p.getBoundingClientRect().right)}; })()""")
            self.assertTrue(r["on"], view)
            self.assertEqual(r["h"], f"Help with {name}")
            self.assertTrue(1 <= r["jobs"] <= 5, view)
            self.assertTrue(r["ref"] and r["search"], view)
            self.assertEqual(r["right"], 0, view)                              # on the right, ask creaite's side
            b.key("Escape")
            self.assertFalse(b.eval("document.querySelector('#hpanel').classList.contains('on')"), view)

    def test_esc_returns_focus_to_where_it_was(self):
        b = self.b
        b.eval("go('today'); document.querySelector('#askBtn').focus()")
        b.key("?")
        self.assertTrue(b.eval("document.querySelector('#hpanel').classList.contains('on')"))
        self.assertEqual(b.eval("document.activeElement.id"), "hpnT")
        b.key("Escape")
        self.assertEqual(b.eval("document.activeElement.id"), "askBtn")

    def test_a_screen_with_no_list_opens_help_on_the_last_tab(self):
        b = self.b
        b.eval("helpGo('reference'); go('activity'); document.activeElement&&document.activeElement.blur()")
        b.key("?")
        self.assertEqual(b.eval("[VIEW, HELPARG, document.querySelector('#hpanel').classList.contains('on')]"), ["help", "reference", False])

    def test_it_never_fires_while_typing_or_over_a_dialog(self):
        b = self.b
        b.eval("go('review')")
        b.eval("document.querySelector('#rvQ').focus()")
        b.key("?")
        self.assertFalse(b.eval("document.querySelector('#hpanel').classList.contains('on')"))
        b.eval("""(()=>{ const d=document.createElement('div'); d.id='ce'; d.contentEditable='true'; d.tabIndex=0; document.body.append(d); d.focus(); })()""")
        b.key("?")
        self.assertFalse(b.eval("document.querySelector('#hpanel').classList.contains('on')"))
        b.eval("document.querySelector('#ce').remove()")
        b.eval("""(()=>{ const d=document.createElement('dialog'); d.id='tdlg'; d.innerHTML='<button id="tb">OK</button>'; document.body.append(d); d.showModal(); document.querySelector('#tb').focus(); })()""")
        b.key("?")
        self.assertFalse(b.eval("document.querySelector('#hpanel').classList.contains('on')"))
        b.eval("document.querySelector('#tdlg').close(); document.querySelector('#tdlg').remove()")
        b.eval("go('today'); document.activeElement&&document.activeElement.blur()")
        b.key("?")                                                            # and it works again once they are gone
        self.assertTrue(b.eval("document.querySelector('#hpanel').classList.contains('on')"))

    def test_the_panel_and_ask_creaite_are_never_both_open(self):
        b = self.b
        self.open_panel("today")
        b.eval("openChat()")
        self.assertEqual(b.eval("[document.querySelector('#hpanel').classList.contains('on'), document.querySelector('#chat').classList.contains('on')]"), [False, True])
        b.eval("document.activeElement&&document.activeElement.blur()")
        b.key("?")
        self.assertEqual(b.eval("[document.querySelector('#hpanel').classList.contains('on'), document.querySelector('#chat').classList.contains('on')]"), [True, False])

    def test_esc_layering_the_panel_closes_before_a_peek_and_a_peek_after(self):
        b = self.b
        b.eval("go('work')")
        b.eval("openRecord('actions', A[0].id)")
        b.pump(0.3)
        self.assertTrue(b.eval("document.querySelector('#panel').classList.contains('on')"))
        b.eval("document.activeElement&&document.activeElement.blur()")
        b.key("?")
        self.assertTrue(b.eval("document.querySelector('#hpanel').classList.contains('on')"))
        b.key("Escape")
        self.assertEqual(b.eval("[document.querySelector('#hpanel').classList.contains('on'), document.querySelector('#panel').classList.contains('on')]"), [False, True])
        b.key("Escape")
        self.assertFalse(b.eval("document.querySelector('#panel').classList.contains('on')"))

    def test_links_open_help_and_the_panel_closes(self):
        b = self.b
        self.open_panel("review")
        b.click("#hpanel .hpn-jobs a")
        b.pump(0.3)
        self.assertEqual(b.eval("[VIEW, HELPARG, document.querySelector('#hpanel').classList.contains('on')]"), ["help", "howto-review-and-approve-proposals", False])
        self.open_panel("people")
        b.click("#hpanel .hpn-ref")
        b.pump(0.2)
        self.assertEqual(b.eval("[VIEW, HELPARG]"), ["help", "reference-people"])
        self.open_panel("files")
        b.click("#hpanel [data-hp-search]")
        b.pump(0.2)
        self.assertEqual(b.eval("[VIEW, document.activeElement.id]"), ["help", "helpS"])

    def test_the_foot_line_on_the_eight_screens_text_not_a_button_and_it_stays(self):
        b = self.b
        for view, name in SCREENS.items():
            b.eval(f"go('{view}')")
            r = b.eval("""(()=>{ const s=document.querySelector('.view:not([hidden])'); const f=s.querySelector(':scope>.hfoot'); return f?{t:f.textContent, tag:f.tagName, btn:!!f.closest('button,a'), last:s.lastElementChild===f, shown:f.offsetHeight>0}:null; })()""")
            self.assertEqual(r, {"t": f"Press ? for help with {name}", "tag": "P", "btn": False, "last": True, "shown": True}, view)
        b.eval("go('review'); renderReview(); renderReview()")
        b.pump(0.2)
        self.assertEqual(b.eval("document.querySelectorAll('#v-review>.hfoot').length"), 1)       # a redraw doesn't double it
        b.eval("go('activity')")
        self.assertEqual(b.eval("document.querySelectorAll('#v-activity .hfoot').length"), 0)     # only the eight

    def test_an_empty_state_links_to_how_the_screen_works(self):
        b = self.b
        b.eval("go('review'); REV.splice(0); renderReview()")
        b.pump(0.3)
        t = b.eval("document.querySelector('#v-review .empty').textContent.replace(/\\s+/g,' ').trim()")
        self.assertIn("Nothing left to review", t)
        self.assertTrue(t.endswith("How Review works"), t)
        b.click("#v-review .empty .hp-how")
        b.pump(0.2)
        self.assertEqual(b.eval("[VIEW, HELPARG]"), ["help", "reference-review"])
        b.eval("go('projects'); P.splice(0); renderProjects()")
        b.pump(0.3)
        self.assertTrue(b.eval("document.querySelector('#v-projects .empty').textContent.replace(/\\s+/g,' ').trim()").endswith("How Projects works"))

    def test_desktop_and_900_light_and_dark_on_both_palettes(self):
        b = self.b
        for width in (1400, 900):
            b.resize(width, 900)
            self.open_panel("review")
            r = b.eval("""(()=>{ const lum=c=>{ const [r,g,b]=c.match(/[\\d.]+/g).slice(0,3).map(Number).map(v=>{ v/=255; return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4); }); return 0.2126*r+0.7152*g+0.0722*b; };
              const ratio=(a,b)=>{ const x=lum(a), y=lum(b); return (Math.max(x,y)+0.05)/(Math.min(x,y)+0.05); };
              const bgOf=el=>{ for(let e=el;e;e=e.parentElement){ const c=getComputedStyle(e).backgroundColor; if(!/rgba\\(0, 0, 0, 0\\)|transparent/.test(c)) return c; } return 'rgb(255,255,255)'; };
              const res={}; for(const pal of %s) for(const mode of ['Light','Dark']){ S.palette=pal; S.theme=mode; applyTheme();
                for(const s of ['#hpanel h2','#hpanel .hpn-k','#hpanel .hpn-jobs a','#hpanel .hpn-ref','#hpanel .hpn-f','#v-review .hfoot']){ const el=document.querySelector(s); res[pal+'|'+mode+'|'+s]=el?ratio(getComputedStyle(el).color,bgOf(el)):-1; } }
              const p=document.querySelector('#hpanel').getBoundingClientRect(); return {res, fits:p.width<=innerWidth&&p.right<=innerWidth+1}; })()""" % TEST_PALETTES_JS)
            self.assertTrue(r["fits"], width)
            self.assertEqual({k: v for k, v in r["res"].items() if v < 4.5}, {}, width)


if __name__ == "__main__":
    unittest.main()
