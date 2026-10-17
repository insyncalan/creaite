"""#158 Phase B part 1: one search over all of Help. A real browser against the real live server.

Run: python3 dev/tests/test_help_search.py   (needs Google Chrome; skipped otherwise)

The box is on every tab; "/" focuses it while Help is open (anywhere else "/" is still ask creaite); results are grouped by part
with the match marked; a plural finds the singular, case and accents don't matter; a result opens its page at the matching line;
an empty result offers Ask creaite; the palette lists matching how-tos by title and the best three lines, from the same index.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import TEST_PALETTES_JS, LiveBrowserCase  # noqa: E402


class HelpSearch(LiveBrowserCase):
    shared_server = True

    def search(self, text):
        b = self.b
        b.eval("closeChat(); go('help','start')")
        b.wait("document.querySelector('#helpS')")
        b.eval("document.querySelector('#helpS').focus()")
        b.eval("(()=>{ const i=document.querySelector('#helpS'); i.value=''; i.dispatchEvent(new Event('input',{bubbles:true})); })()")
        b.type(text)
        b.pump(0.2)
        return b.eval("""(()=>{ const r=document.querySelector('#helpRes'); return {shown:!r.hidden, paneHidden:document.querySelector('#helpPane').hidden,
          groups:[...r.querySelectorAll('.hs-g h2')].map(h=>h.firstChild.textContent.trim()),
          rows:[...r.querySelectorAll('.hs-r')].map(a=>[a.dataset.help,a.querySelector('.hs-t').textContent]),
          marks:[...r.querySelectorAll('mark')].map(m=>m.textContent), text:r.textContent.replace(/\\s+/g,' ').trim()}; })()""")

    def test_slash_focuses_the_search_on_help_and_is_ask_creaite_elsewhere(self):
        b = self.b
        b.eval("go('today')")
        b.key("/")
        b.pump(0.2)
        self.assertTrue(b.eval("document.querySelector('#chat').classList.contains('on')"))
        b.eval("closeChat(); go('help','howto')")
        b.eval("document.activeElement&&document.activeElement.blur()")
        b.key("/")
        b.pump(0.1)
        self.assertEqual(b.eval("document.activeElement.id"), "helpS")
        self.assertFalse(b.eval("document.querySelector('#chat').classList.contains('on')"))
        for tab in ("start", "howto", "reference"):                           # the box is on every tab
            b.eval(f"helpGo('{tab}')")
            self.assertTrue(b.eval("!!document.querySelector('#helpS')&&document.querySelector('#helpS').offsetHeight>0"), tab)

    def test_a_word_on_a_reference_page_and_on_a_how_to_card(self):
        r = self.search("workstreams")
        self.assertTrue(r["shown"] and r["paneHidden"])
        self.assertIn("Reference", r["groups"])
        self.assertIn("How do I…", r["groups"])
        self.assertIn(["reference-workstreams", "Workstreams"], r["rows"])
        self.assertTrue(all(m.lower().startswith("workstream") for m in r["marks"]))
        self.assertGreater(len(r["marks"]), 0)

    def test_a_plural_finds_the_singular_and_case_and_accents_do_not_matter(self):
        a = self.search("proposal")
        b = self.search("PROPOSALS")
        c = self.search("pröposals")
        self.assertGreater(len(a["rows"]), 3)
        self.assertEqual(sorted(a["rows"]), sorted(b["rows"]))
        self.assertEqual(sorted(a["rows"]), sorted(c["rows"]))
        d = self.search("milest")                                                # a prefix
        self.assertTrue(any(row[0] == "reference-milestones-plan-and-movement" for row in d["rows"]))

    def test_no_result_offers_ask_creaite_with_the_words(self):
        b = self.b
        r = self.search("zzqqxx")
        self.assertIn("Nothing in Help for ‘zzqqxx’", r["text"])
        self.assertEqual(r["rows"], [])
        b.click("#helpRes [data-hs-ask]")
        b.pump(0.4)
        self.assertTrue(b.eval("document.querySelector('#chat').classList.contains('on')"))
        self.assertEqual(b.eval("document.querySelector('#chIn').value"), "zzqqxx")

    def test_a_result_opens_its_page_at_the_matching_line_and_marks_it(self):
        b = self.b
        self.search("workstreams")
        b.eval("document.querySelector('#helpRes [data-help=\"reference-workstreams\"]').scrollIntoView()")
        b.click("#helpRes [data-help=\"reference-workstreams\"]")
        b.pump(0.4)
        r = b.eval("""(()=>{ const f=document.querySelector('#helpPane .hp-found'); const q=f&&f.getBoundingClientRect();
          return {hash:location.hash, found:!!f, inView:!!q&&q.top>=0&&q.bottom<=innerHeight, inRef:!!f&&!!f.closest('#hr-workstreams'),
                  results:document.querySelector('#helpRes').hidden, pane:document.querySelector('#helpPane').hidden}; })()""")
        self.assertEqual(r, {"hash": "#help-reference-workstreams", "found": True, "inView": True, "inRef": True, "results": True, "pane": False})
        b.key("Escape")                                                           # Esc in an emptied box leaves it
        b.eval("go('help','start')")
        self.assertFalse(b.eval("!!document.querySelector('#helpPane .hp-found')"))

    def test_escape_clears_the_box_then_leaves_it(self):
        b = self.b
        self.search("workstreams")
        b.eval("document.querySelector('#helpS').focus()")
        b.key("Escape")
        b.pump(0.1)
        self.assertEqual(b.eval("document.querySelector('#helpS').value"), "")
        self.assertTrue(b.eval("document.querySelector('#helpRes').hidden&&!document.querySelector('#helpPane').hidden"))
        b.key("Escape")
        self.assertNotEqual(b.eval("document.activeElement.id"), "helpS")

    def test_the_palette_lists_how_tos_by_title_and_the_best_three_by_line(self):
        b = self.b
        r = b.eval("""(()=>{ const items=ckItems('workstream').filter(i=>i.g==='Help');
          const q2=ckItems('hand over someone').filter(i=>i.g==='Help');
          return {titles:items.map(i=>[i.l,i.h]), lines:items.filter(i=>i.h&&i.h!=='How do I…'&&i.h!=='Reference').length, first:q2[0]&&[q2[0].l,q2[0].h]}; })()""")
        self.assertEqual(r["first"], ["Help: Hand over someone's work", "How do I…"])
        self.assertIn(["Help: Workstreams", "Reference"], r["titles"])
        self.assertLessEqual(r["lines"], 3)
        self.assertGreater(r["lines"], 0)
        b.eval("go('today'); openCk(); const i=document.getElementById('cmdkIn'); i.value='workstream'; i.dispatchEvent(new Event('input',{bubbles:true}));")
        b.pump(0.2)
        self.assertTrue(b.eval("[...document.querySelectorAll('#cmdkList button')].some(x=>x.textContent.startsWith('Help: Workstreams'))"))
        b.key("Escape")

    def test_desktop_and_900_light_and_dark_on_both_palettes(self):
        b = self.b
        for width in (1400, 900):
            b.resize(width, 900)
            b.eval("go('help','start')")
            self.search("workstreams")
            res = b.eval("""(()=>{ const lum=c=>{ const [r,g,b]=c.match(/[\\d.]+/g).slice(0,3).map(Number).map(v=>{ v/=255; return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4); }); return 0.2126*r+0.7152*g+0.0722*b; };
              const ratio=(a,b)=>{ const x=lum(a), y=lum(b); return (Math.max(x,y)+0.05)/(Math.min(x,y)+0.05); };
              const bgOf=el=>{ for(let e=el;e;e=e.parentElement){ const c=getComputedStyle(e).backgroundColor; if(!/rgba\\(0, 0, 0, 0\\)|transparent/.test(c)) return c; } return 'rgb(255,255,255)'; };
              const res={}; for(const pal of %s) for(const mode of ['Light','Dark']){ S.palette=pal; S.theme=mode; applyTheme();
                for(const s of ['.hs-g h2','.hs-t','.hs-l','.hs-l mark','.hp-search input','.hs-more']){ const el=document.querySelector('#helpRes '+s)||document.querySelector(s); if(!el){ res[pal+'|'+mode+'|'+s]=-1; continue; }
                  res[pal+'|'+mode+'|'+s]=ratio(getComputedStyle(el).color,s==='.hs-l mark'?getComputedStyle(el).backgroundColor:bgOf(el)); } }
              return {res, side:document.documentElement.scrollWidth<=innerWidth+1}; })()""" % TEST_PALETTES_JS)
            self.assertTrue(res["side"], width)
            bad = {k: round(v, 2) for k, v in res["res"].items() if 0 <= v < 4.5 or (v == -1 and not k.endswith(".hs-more"))}
            self.assertEqual(bad, {}, width)


if __name__ == "__main__":
    unittest.main()
