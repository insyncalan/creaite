"""v1.9.5 hand checks 6 and 9 (plan #81; BL-324 and BL-325's scope): past time on Today's day band can be seen, and the
controls the check found off size are the design scale's one control height.

Check 6, in every palette, light and dark, measured as drawn on the day band (what is really behind them, every ancestor's
opacity multiplied in):
- the past dot (--day-past) and the now-line (the sun, --day-sun) are marks that must be seen: 3:1 (WCAG 1.4.11);
- a past meeting's dimmed words: 3:1, the agreed bar for de-emphasised past text;
- the day line's "Next week" label (10 px): 4.5:1 (WCAG 1.4.3, small text).
Held for a decision, not fixed (HELD below): the sun in Brightwater light, 2.78:1. It is --day-sun, which the Now dot and
the "Now" label share, so raising it would change them too.
Check 9: Intake's Clear day (.btn.mtgclr) and the fields Intake's project select, Activity's search, Settings' search (on its
three tabs), Settings › People's Merge into selects and the Workstreams manager's project select and name are --ctl-h (32 px).
Files' 40 px search is by design and not here.

Over test_today_days's fixture (Tuesday 13-10-2026 at 11:05: the 09:00 stand-up is past, the sun stands at 11:05, the day
line has "Next week"), both clocks pinned.

Run: python3 dev/tests/test_day_past_and_sizes.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_today_days as fx  # noqa: E402  (fixes CREAITE_NOW and the fixture's TODAY on import)
from live_browser import TEST_PALETTES, LiveBrowserCase, pin_page_clock, theme_names  # noqa: E402

# The paint of each visible match (its text colour, fill or stroke) against the first opaque background behind it, every
# ancestor's opacity multiplied in. After dev/tests/handchecks/measure.py's paint_contrast (BL-341).
PAINT = r"""(sel, prop) => {
  const parse = c => { const m = (c||"").match(/[\d.]+/g); if (!m || /^none|url/.test(c||"")) return null; const v = m.map(Number);
    return {r:v[0], g:v[1], b:v[2], a:v.length > 3 ? v[3] : 1}; };
  const over = (top, under) => { const a = top.a + under.a*(1-top.a); if (!a) return {r:0,g:0,b:0,a:0};
    const mix = k => (top[k]*top.a + under[k]*under.a*(1-top.a))/a; return {r:mix("r"), g:mix("g"), b:mix("b"), a}; };
  const lum = c => { const f = u => { u/=255; return u<=0.03928 ? u/12.92 : ((u+0.055)/1.055)**2.4; };
    return 0.2126*f(c.r) + 0.7152*f(c.g) + 0.0722*f(c.b); };
  const ratio = (x, y) => { const [lo, hi] = [lum(x), lum(y)].sort((p, q) => p - q); return (hi+0.05)/(lo+0.05); };
  const behind = el => { const layers = []; for (let e = el; e; e = e.parentElement) { const c = parse(getComputedStyle(e).backgroundColor);
      if (c && c.a > 0) { layers.push(c); if (c.a >= 1) break; } }
    let bg = parse(getComputedStyle(document.documentElement).backgroundColor); if (!bg || bg.a < 1) bg = {r:255,g:255,b:255,a:1};
    for (const c of layers.reverse()) bg = over(c, bg); return bg; };
  const opacity = el => { let o = 1; for (let e = el; e; e = e.parentElement) o *= Number(getComputedStyle(e).opacity || 1); return o; };
  return [...document.querySelectorAll(sel)].filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 &&
      getComputedStyle(e).visibility !== "hidden" && !e.closest("[hidden],[inert]"); })
    .map(e => { const s = getComputedStyle(e), bg = behind(e), p0 = parse(s[prop]); if (!p0) return null;
      const o = opacity(e) * (prop === "fill" ? Number(s.fillOpacity || 1) : prop === "stroke" ? Number(s.strokeOpacity || 1) : 1);
      const fg = over({...p0, a: p0.a*o}, bg);
      return {sig: e.tagName.toLowerCase() + ((e.getAttribute("class")||"").trim() ? "." + e.getAttribute("class").trim().split(/\s+/).join(".") : ""),
              text: (e.innerText||e.textContent||"").trim().slice(0, 20), own: [...e.childNodes].some(c => c.nodeType === 3 && c.textContent.trim()),
              ratio: Math.round(ratio(fg, bg)*100)/100}; }).filter(Boolean);
}"""


class Base(LiveBrowserCase):
    shared_server = True

    @classmethod
    def load(cls, v):
        fx.world(v)

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": fx.NOW}

    def setUp(self):
        super().setUp()
        pin_page_clock(self.b, fx.NOW)

    def paint(self, sel, prop="color"):
        return self.b.eval(f"({PAINT})({json.dumps(sel)}, {json.dumps(prop)})")


# Nothing is held: Brightwater light's sun (--day-sun, shared by the Now dot, the "Now" label and the ripple) went from
# #AB72FB (2.78:1) to #A26DED (3.06:1), same hue (Alan, 15-10-2026, #81)
HELD = set()


class PastTimeContrast(Base):
    """Check 6."""

    def setUp(self):
        super().setUp()
        self.b.eval("go('today')")
        self.b.wait("document.querySelector('#dayLine .dot.past') && document.querySelector('#dayLine .sun') "
                    "&& document.querySelector('#v-today .dm.past') && document.querySelector('#todayDate .daywk')")

    def measure(self):
        """{kind: [(palette, mode, ratio, what)]} over every palette, light and dark."""
        out = {"past dot": [], "now-line": [], "past words": [], "next week": []}
        try:
            for p in TEST_PALETTES:
                for m in ("light", "dark"):
                    self.b.eval(f"document.documentElement.dataset.palette={json.dumps(p)}; document.documentElement.dataset.theme={json.dumps(m)}")
                    self.b.pump(0.05)
                    for kind, sel, prop in (("past dot", "#dayLine .dot.past", "fill"),
                                            ("now-line", "#dayLine .sun circle, #dayLine .sun path", "stroke"),
                                            ("past words", "#v-today .dm.past > :not(.acts), #v-today .dm.past > :not(.acts) *", "color"),
                                            ("next week", "#todayDate .daywk", "color")):
                        rows = [r for r in self.paint(sel, prop) if prop != "color" or r["own"]]
                        self.assertTrue(rows, f"{kind}: nothing measured in {p} {m}")
                        out[kind] += [(p, m, r["ratio"], f"{r['sig']} {r['text']!r}") for r in rows]
        finally:
            self.b.eval("applyTheme()")
        return out

    BARS = {"past dot": 3.0, "now-line": 3.0, "past words": 3.0, "next week": 4.5}

    def low(self, got):
        return [(k, p, m, f"{k} {p} {m}: {what} {r}:1 < {self.BARS[k]}") for k, rows in got.items() for p, m, r, what in rows
                if r < self.BARS[k]]

    def test_past_time_and_its_labels_can_be_seen_in_every_palette(self):
        low = [x for x in self.low(self.measure()) if x[:3] not in HELD]
        self.assertEqual(len(theme_names()), 9)
        self.assertEqual([x[3] for x in low], [])

    def test_the_past_words_are_a_colour_not_a_fade(self):
        """Preferred over an opacity: the dimmed words take a token colour, so what they are drawn in is the colour measured."""
        op = self.b.eval("[...document.querySelectorAll('#v-today .dm.past > :not(.acts)')].map(e=>getComputedStyle(e).opacity)")
        self.assertTrue(op)
        self.assertEqual(set(op), {"1"})
        self.assertEqual(self.b.eval("getComputedStyle(document.querySelector('#todayDate .daywk')).opacity"), "1")


# (name, how to get there, what must be shown, selectors measured)
SCREENS = (
    ("intake", "go('intake-review')", "document.querySelector('#irQ') && document.querySelector('[data-ira=processall]')",
     ("#irQ", "[data-ira=processall]")),      # #232 C2: the search box and Process all ready (the old Calendar import's Clear day and project select went with it)
    ("activity", "go('activity')", "document.getElementById('actQ')", ("#actQ",)),
    ("settings-essentials", "go('settings','essentials')", "document.getElementById('setq')?.offsetParent", ("#setq",)),
    ("settings-advanced", "go('settings','advanced')", "document.getElementById('setq')?.offsetParent", ("#setq",)),
    ("settings-people", "go('settings','people')",
     "document.querySelector('#peopleMgr select.pmsel') && document.getElementById('wsmP') && document.getElementById('wsmName')",
     ("#setq", "#peopleMgr select.pmsel", "#settingsBody select.mgsel", "#wsmP", "#wsmName")),
)


class OneControlSize(Base):
    """Check 9."""

    def test_the_off_size_controls_are_the_one_control_height(self):
        b = self.b
        want = b.eval("parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--ctl-h'))")
        self.assertEqual(want, 32)
        off, n = [], 0
        for name, go, ready, sels in SCREENS:
            b.eval(go)
            b.wait(ready, 15)
            b.pump(0.2)
            for sel in sels:
                hs = b.eval(f"[...document.querySelectorAll({json.dumps(sel)})].filter(e=>e.offsetParent).map(e=>Math.round(e.getBoundingClientRect().height*10)/10)")
                self.assertTrue(hs, f"{name}: no {sel} on screen")
                n += len(hs)
                off += [f"{name} {sel} {h}px" for h in sorted(set(hs)) if h != want]
        self.assertGreater(n, 10)
        self.assertEqual(off, [])


if __name__ == "__main__":
    unittest.main()
