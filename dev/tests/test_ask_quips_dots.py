"""BL-259 and BL-261: ask creaite's working line. A real browser against the real live server on the sample data.

- BL-259: about 150 office quips; each stays for a random 5 to 10 seconds; none comes back until the deck is used up; a new
  working line within 5 seconds keeps the quip already showing. Still aria-hidden, with "Working" for screen readers.
- BL-261: the three dots take three shades of the active theme's accent (tokens --mdot-1 to --mdot-3), each at least 3:1 against
  the panel in every theme, light and dark; switching theme recolours them; reduced motion still stops the animation.

Run: python3 dev/tests/test_ask_quips_dots.py   (needs Google Chrome; skipped otherwise)
"""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase, theme_names  # noqa: E402

# The page's clock, stepped by the test: Date.now() reads window.T.
CLOCK = "window.T=1e12; Date.now=()=>window.T;"
RATIO = r"""(()=>{ const P=s=>{ const m=s.match(/rgba?\(([^)]+)\)/); if(m){ const p=m[1].split(/[ ,\/]+/).filter(Boolean).map(Number); return [p[0],p[1],p[2]]; }
    const c=s.match(/color\(srgb ([^)]+)\)/); const p=c[1].split(/[ \/]+/).filter(Boolean).map(Number); return [p[0]*255,p[1]*255,p[2]*255]; };
  const lum=c=>{ const f=v=>{ v/=255; return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4); }; return 0.2126*f(c[0])+0.7152*f(c[1])+0.0722*f(c[2]); };
  const ratio=(a,b)=>{ const x=lum(a), y=lum(b); return (Math.max(x,y)+0.05)/(Math.min(x,y)+0.05); };
  const bg=P(getComputedStyle(document.getElementById('chat')).backgroundColor);
  return [...document.querySelectorAll('#chLog .mdots i')].map(i=>({c:getComputedStyle(i).backgroundColor,r:ratio(P(getComputedStyle(i).backgroundColor),bg)})); })()"""


class Quips(LiveBrowserCase):
    shared_server = True
    width, height = 1400, 900

    def test_about_150_quips_in_the_same_voice(self):
        quips = self.b.eval("QUIPS")
        self.assertGreaterEqual(len(quips), 140)
        self.assertLessEqual(len(quips), 160)
        self.assertEqual(len(set(quips)), len(quips))
        self.assertTrue(all(len(q) <= 45 and not q.endswith(("…", ".")) for q in quips), [q for q in quips if len(q) > 45])

    def test_each_stays_5_to_10_seconds_and_none_repeats_until_the_deck_is_used_up(self):
        b = self.b
        out = b.eval(CLOCK + """(()=>{ QDECK=[]; QNOW={text:"",i:-1,until:0}; const seen=[], spans=[];
          for(let k=0;k<QUIPS.length*2;k++){ const t=quipNow(), start=window.T; let s=0;
            while(quipNow()===t&&s<20000){ window.T+=100; s+=100; } seen.push(t); spans.push(window.T-start); }
          return {seen,spans}; })()""")
        n = len(self.b.eval("QUIPS"))
        first, second = out["seen"][:n], out["seen"][n:]
        self.assertEqual(len(set(first)), n)                        # every quip once before any comes back
        self.assertEqual(len(set(second)), n)
        self.assertTrue(all(5000 <= s <= 10100 for s in out["spans"]), (min(out["spans"]), max(out["spans"])))
        self.assertGreater(len(set(s // 1000 for s in out["spans"])), 3)   # random, not one fixed time
        self.assertTrue(all(a != b2 for a, b2 in zip(out["seen"], out["seen"][1:])))

    def test_a_new_working_line_keeps_a_quip_shown_for_under_5_seconds(self):
        b = self.b
        b.eval("openChat()")
        r = b.eval(CLOCK + """(()=>{ QDECK=[]; QNOW={text:"",i:-1,until:0}; const a=working(); const ta=a.querySelector('.quip').textContent;
          window.T+=4900; a.remove(); const c=working(); const tc=c.querySelector('.quip').textContent;
          window.T+=10200; quip(c); const td=c.querySelector('.quip').textContent; c.remove();
          return [ta,tc,td, a.querySelector('.quip').getAttribute('aria-hidden'), c.querySelector('.vh').textContent]; })()""")
        self.assertEqual(r[0], r[1])                               # kept: up for under 5 seconds
        self.assertNotEqual(r[1], r[2])                            # changed once its time was up
        self.assertEqual(r[3:], ["true", "Working"])


class Dots(LiveBrowserCase):
    shared_server = True
    width, height = 1400, 900
    reduced_motion = False

    def test_three_accent_shades_at_3_to_1_in_every_theme_light_and_dark(self):
        b = self.b
        b.eval("openChat(); window.W=working()")
        failures, colours = [], {}
        for palette in theme_names():
            for mode in ("light", "dark"):
                b.eval(f"document.documentElement.dataset.palette='{palette}'; document.documentElement.dataset.theme='{mode}'")
                dots = b.eval(RATIO)
                self.assertEqual(len(dots), 3)
                colours[(palette, mode)] = tuple(d["c"] for d in dots)
                self.assertEqual(len(set(colours[(palette, mode)])), 3, (palette, mode, dots))     # three shades
                failures += [f"{palette} {mode} dot {i + 1}: {d['r']:.2f}" for i, d in enumerate(dots) if d["r"] < 3]
        self.assertEqual(failures, [])
        self.assertGreater(len(set(colours.values())), len(theme_names()))       # they follow the theme
        accent = b.eval("(()=>{ const t=document.createElement('i'); t.style.background='var(--accent)'; document.body.append(t); const c=getComputedStyle(t).backgroundColor; t.remove(); return c; })()")
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('#chLog .mdots i')).backgroundColor"), accent)
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('#chLog .mdots i')).animationName"), "mwave")   # unchanged
        b.eval("W.remove()")


class DotsReduced(LiveBrowserCase):
    shared_server = True
    width, height = 1400, 900

    def test_reduced_motion_still_stops_the_animation(self):
        b = self.b
        b.eval("openChat(); window.W=working()")
        cs = b.eval("(()=>{ const s=getComputedStyle(document.querySelector('#chLog .mdots i')); return [s.animationName,s.animationDuration,s.animationIterationCount]; })()")
        self.assertTrue(cs[0] == "none" or re.fullmatch(r"0s", cs[1]) or cs[2] == "1", cs)
        b.eval("W.remove()")


if __name__ == "__main__":
    unittest.main()
