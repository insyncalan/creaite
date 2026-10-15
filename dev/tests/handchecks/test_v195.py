"""BL-341: creaite 1.9.5's hand checks (dev/handchecks/v1.9.5.md), automated against a vault made from the release zip.

Run them all, fill the Results table and make the screenshot sheet:  python3 dev/tools/handcheck.py v1.9.5
Run this file on its own (it makes the vault itself):                 python3 dev/tests/handchecks/test_v195.py

One method per check, `test_cNN_…`, its docstring quoting the check. One class per group, so the groups can be written in
parallel without touching the same lines:
  Scriptable1     1, 2, 13, 14, 15, 17   phase 1
  Measured1       3, 5, 12               phase 1
  Judgement1      4, 10                  phase 1 (on the sheet)
  Measured2       6, 7, 8, 9, 16, 19     phase 2 (7 and 8: the accessibility tree in place of VoiceOver)
  Judgement2      11, 18, 20, 51         phase 2 (on the sheet; 51 also measured)
  Bl333And10      21 to 30               phase 2 (own vault: archiving changes data)
  Bl03And331      31 to 41               phase 2 (own vault)
  Bl334And316     42 to 47, 49, 50       phase 2 (own vault)
  48 is live only (LIVE_ONLY); so is a final VoiceOver spot check.
Helpers: hcbase.HandcheckCase (screens, notes, the sheet, own vaults), measure.py (CDP measures), sheet.py.

Numbering follows dev/handchecks/v1.9.5.md on release-195 (51 checks; BL-326's moved to v1.9.4.md).
"""
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import measure  # noqa: E402
from hcbase import NOTES, HandcheckCase, phase2  # noqa: E402,F401  (NOTES: read by handcheck.py)

KIND = {**{n: "scriptable" for n in (1, 2, 13, 14, 15, 17, *range(23, 48), 49, 50)},
        **{n: "measurable" for n in (3, 5, 6, 7, 8, 9, 12, 16, 19, 21, 22)},
        **{n: "judgement" for n in (4, 10, 11, 18, 20, 51)},
        48: "live only"}

LIVE_ONLY = {
    48: "needs Microsoft 365 connected and a real chat with a followed person; the hand-check vault never calls Microsoft 365",
}
# Also live only: a final VoiceOver spot check on 7 and 8, by ear. Headless Chrome has no screen reader, so the automated
# checks read Chrome's accessibility tree instead: what VoiceOver is given, not what it says.
VOICEOVER = "plus a VoiceOver spot check by hand (live only: the automated check reads the accessibility tree, not VoiceOver)"
NOTES.update({7: VOICEOVER, 8: VOICEOVER})

# The pages checks 9 and 12 name
PAGES_9 = ("today", "work", "review", "intake", "settings-essentials", "activity", "files")


class Scriptable1(HandcheckCase):
    """Start-up and BL-325's wording and primary actions."""

    def test_c01_doctor(self):
        """1. `system/scripts/run doctor.py` → every check passes, including the two archiving checks (items, reports). The
        reports check warns while the old files from step 4 are waiting: that is expected."""
        code, out = self.run_in_vault("doctor.py")
        failed = [ln for ln in out.splitlines() if ln.startswith("FAIL")]
        warns = [ln for ln in out.splitlines() if ln.startswith("WARN")]
        self.assertEqual(code, 0, out[-500:])
        self.assertEqual(failed, [])
        self.assertTrue(re.search(r"^PASS +Archiving of old items", out, re.M), "the items archiving check")
        self.assertTrue(re.search(r"^WARN +Old reports and minutes — Archive 4 reports", out, re.M),
                        "the reports archiving check warns about the four old files")
        others = [w.split("—")[0][4:].strip() for w in warns if "Old reports and minutes" not in w]
        summary = re.search(r"(\d+) passed, (\d+) failed", out)
        self.note(1, f"{summary.group(0) if summary else '?'}; reports check warns as expected"
                     + (f"; other warnings: {', '.join(others)}" if others else ""))

    def test_c02_no_page_errors(self):
        """2. Visit every screen once → no page errors. Settings › Diagnostics says "No errors in the last 7 days" (check
        again at the end)."""
        b = self.b
        for name in measure_screens():
            with self.subTest(name):
                self.screen(name)
        self.assertEqual(b.errors, [], "page errors")
        diag = b.eval("api('/api/diagnostics',{}).then(r=>r)")
        errors = (diag or {}).get("errors")
        self.assertEqual(errors, [], f"Diagnostics lists errors: {str(errors)[:200]}")
        self.note(2, f"{len(measure_screens())} screens, 0 page errors; Diagnostics: no errors in the last 7 days")

    def test_c13_today_headings(self):
        """13. Today → the section headings (Decisions needed, Needs attention, Week ahead, Portfolio …) are sentence-case
        headings like Settings', not small capitals. Today's large title is unchanged."""
        b = self.b
        style = "e=>{const s=getComputedStyle(e); return [s.fontSize,s.fontWeight,s.fontFamily,s.textTransform,s.fontVariantCaps,s.letterSpacing].join('|')}"
        self.screen("today")
        today = b.eval(f"[...document.querySelectorAll('#v-today h2')].filter(e=>e.offsetParent).map(e=>({{t:e.firstChild?.textContent?.trim()||e.innerText.split('\\n')[0], s:({style})(e)}}))")
        self.assertTrue(today, "Today has section headings")
        names = [h["t"] for h in today]
        for want in ("Needs attention", "Week ahead", "Portfolio"):    # Decisions needed shows only when one is waiting
            self.assertIn(want, names)
        for h in today:
            self.assertNotIn("|uppercase|", h["s"], h["t"])
            self.assertNotIn("small-caps", h["s"], h["t"])
            self.assertTrue(h["t"][:1].isupper() and h["t"][1:] != h["t"][1:].upper(), f"sentence case: {h['t']}")
        self.screen("settings-essentials")
        settings = b.eval(f"[...document.querySelectorAll('#v-settings h2')].filter(e=>e.offsetParent).map({style})")
        self.assertTrue(settings)
        self.assertEqual({h["s"] for h in today}, {settings[0]}, "Today's headings are drawn as Settings' are")
        self.screen("today")
        title = b.eval("(()=>{const e=document.querySelector('#v-today h1'); return e?getComputedStyle(e).fontSize:null})()")
        self.assertEqual(title, "34px", "Today's large title keeps its 34 px (by design)")
        self.note(13, f"{len(today)} headings, same font as Settings' ({settings[0].split('|')[0]}), none uppercase or small caps; title 34px")

    def test_c14_intake_names(self):
        """14. Intake → "Calendar import", "Upload files" and "Quick capture" in sentence case, with no icons beside them.
        Help and Settings › Advanced use the same names."""
        b = self.b
        names = ["Calendar import", "Upload files", "Quick capture"]
        self.screen("intake")
        heads = b.eval("[...document.querySelectorAll('#v-inbox .isec .ish h2')].map(e=>({t:e.innerText.trim(), icons:e.parentElement.querySelectorAll('svg,img,.i').length, tt:getComputedStyle(e).textTransform}))")
        self.assertEqual([h["t"] for h in heads], names)
        self.assertEqual([h["icons"] for h in heads], [0, 0, 0], "no icons beside them")
        self.assertEqual({h["tt"] for h in heads}, {"none"})
        self.screen("help")
        help_text = b.eval("document.getElementById('v-help').innerText")
        self.screen("settings-advanced")
        adv = b.eval("document.getElementById('v-settings').innerText")
        for n in names:
            self.assertIn(n, help_text, f"Help names {n}")
        old = [w for w in ("Upload a file", "Calendar Import", "Quick Capture", "Upload Files") if w in help_text + adv]
        self.assertEqual(old, [], "the old names")
        in_adv = [n for n in names if n in adv]
        self.note(14, f"headings {', '.join(names)}, no icons; Help names all three; Settings › Advanced names {', '.join(in_adv) or 'none of them'}")

    def test_c15_primary_actions(self):
        """15. Primary actions keep their look: Today's and Intake's filled button, Review's outlined Approve, Work's tinted "+"."""
        b = self.b
        look = "e=>{const s=getComputedStyle(e); return {bg:s.backgroundColor, border:s.borderTopColor, bw:s.borderTopWidth, color:s.color, text:e.innerText.trim().slice(0,30)}}"
        transparent = ("rgba(0, 0, 0, 0)", "transparent")
        self.screen("today")
        today = b.eval(f"[...document.querySelectorAll('#v-today .btn.primary')].filter(e=>e.offsetParent).map({look})")
        probed = not today
        if probed:                             # none on show in the demo's state: the rule itself, on a button in Today's view
            today = b.eval(f"""(()=>{{ const e=document.createElement('button'); e.className='btn primary'; e.textContent='Probe';
              document.getElementById('v-today').append(e); const r=({look})(e); e.remove(); return [r]; }})()""")
        self.screen("intake")
        intake = b.eval(f"[...document.querySelectorAll('#v-inbox .btn.primary')].filter(e=>e.offsetParent).map({look})")
        for where, bs in (("Today", today), ("Intake", intake)):
            self.assertTrue(bs, f"{where} has a primary button")
            for x in bs:
                self.assertNotIn(x["bg"], transparent, f"{where}'s {x['text']} is filled")
        self.screen("review")
        approve = b.eval(f"[...document.querySelectorAll('#v-review button[data-act=a]')].filter(e=>e.offsetParent).map({look})")
        self.assertTrue(approve, "Review shows Approve")
        surface = b.eval("getComputedStyle(document.documentElement).getPropertyValue('--surface').trim()")
        for x in approve[:3]:
            self.assertNotEqual(x["bw"], "0px", "Approve is outlined")
        self.screen("work")
        plus = b.eval(f"(()=>{{const e=document.getElementById('newBtn'); return e&&({look})(e)}})()")
        self.assertTrue(plus, "Work's + button")
        self.assertNotIn(plus["bg"], transparent, "Work's + is tinted")
        self.note(15, f"Today {today[0]['bg']}{' (the .btn.primary rule: none on show)' if probed else ''}, Intake {intake[0]['bg']}, Approve outlined ({approve[0]['bw']} {approve[0]['border']}; surface {surface}), Work + {plus['bg']}")

    def test_c17_in_24_days(self):
        """17. Projects → a next milestone reads "(in 24 days)", lower case; its written-out date is unchanged."""
        b = self.b
        self.screen("projects")
        found = b.eval("document.getElementById('v-projects').innerText.match(/[A-Z][a-z]+day \\d+[a-z]{2} [A-Z][a-z]+(?: \\d{4})? \\((?:in|In) \\d+ days?\\)/g)")
        self.assertTrue(found, "next milestones with a relative date")
        mer = [x for x in found if "(in 24 days)" in x]
        self.assertTrue(mer, f"Meridian's pilot review in 24 days: {found}")
        self.assertFalse([x for x in found if "(In " in x], "lower case")
        self.note(17, f"\"{mer[0]}\"")


def measure_screens():
    from hcbase import SCREENS
    return list(SCREENS)


class Measured1(HandcheckCase):
    """BL-324 and BL-325, measured."""

    def test_c03_saffron_in_system_dark(self):
        """3. Theme creaite, then Brightwater, each with the OS in dark mode (Rendering › `prefers-color-scheme: dark`) and the
        theme on "System" → the saffron bar under the wordmark is the dark-mode saffron, the same as with the theme set to Dark."""
        b = self.b
        fill = "getComputedStyle(document.querySelector('.rail .logo svg.wm .wmb')).fill"
        seen = []
        try:
            measure.media(b, dark=True)
            for p in ("creaite", "Brightwater"):
                measure.theme(b, p, "system")
                system = b.eval(fill)
                measure.theme(b, p, "dark")
                dark = b.eval(fill)
                measure.theme(b, p, "light")
                light = b.eval(fill)
                self.assertEqual(system, dark, f"{p}: System on a dark Mac draws the dark saffron")
                self.assertNotEqual(system, light, f"{p}: and not the light one")
                seen.append(f"{p} {system}")
        finally:
            measure.media(b)
            b.eval("applyTheme()")
        self.note(3, "System+dark = Dark: " + ", ".join(seen))

    def test_c05_dark_count_badges(self):
        """5. Dark mode, every theme → the rail's red count badges are readable (dark text on red), not white on pale red."""
        b = self.b
        worst = []
        try:
            for p in measure.themes(b):
                measure.theme(b, p, "dark")
                rows = measure.contrast(b, ".rail .badge")
                self.assertTrue(rows, f"{p}: the rail shows count badges")
                with self.subTest(p):
                    r = min(rows, key=lambda x: x["ratio"])
                    worst.append((r["ratio"], p))
                    self.assertGreaterEqual(r["ratio"], 4.5, f"{p} dark: {r['color']} on {r['background']}")
                    ink, bg = (lum(r["color"]), lum(r["background"]))
                    self.assertLess(ink, bg, f"{p} dark: dark text on red, not light text ({r['color']} on {r['background']})")
        finally:
            b.eval("applyTheme()")
        worst.sort()
        self.note(5, f"{len(worst)} themes in dark; lowest contrast {worst[0][0]}:1 ({worst[0][1]}); dark text on red in each")

    def test_c12_controls_match(self):
        """12. The same pages as check 9, in every theme → `.ib` icon buttons, small buttons (26 px), link buttons, chips and
        tags look the same everywhere; nothing is clipped or overlapping."""
        b = self.b
        kinds = {"ib": ".ib", "mini": ".mini", "linkbtn": ".linkbtn", "chip": ".chip", "tag": ".tag"}
        # One control is one class list (states and colour variants left out: they change colour, not shape); its look is
        # its size, weight, font, corner, case and, for buttons, height. Drift: one control drawn two ways in one theme.
        sig_js = r"""(sel)=>[...document.querySelectorAll(sel)].filter(e=>e.offsetParent&&!e.closest('#panel,#chat,dialog,.rail')).map(e=>{
          const s=getComputedStyle(e), r=e.getBoundingClientRect();
          const key=[...e.classList].filter(c=>!/^(on|active|sel|selected|open|cur|now|past|dirty|busy|acc|ok|bad|warn|muted|pri)$/.test(c)).sort().join('.');
          return {key, sig:[s.fontSize,s.fontWeight,s.fontFamily.split(',')[0],s.borderTopLeftRadius,s.textTransform,
                            (e.matches('.ib,.mini')?Math.round(r.height)+'px':'')].join(' '),
                  h:Math.round(r.height), clip:e.scrollWidth>e.clientWidth+1&&s.overflow!=='visible'&&s.textOverflow!=='ellipsis'}; })"""
        drift, clipped, sizes, counted = [], [], [], 0
        variants = {}
        try:
            for p in measure.themes(b):
                measure.theme(b, p, "light")
                seen = {}
                for page in PAGES_9:
                    self.screen(page, settle=0.2)
                    for k, sel in kinds.items():
                        for x in b.eval(f"({sig_js})({json.dumps(sel)})"):
                            seen.setdefault(x["key"], {}).setdefault(x["sig"], set()).add(page)
                            if p == "creaite":
                                variants.setdefault(k, set()).add(x["sig"])
                            counted += 1
                            if x["clip"]:
                                clipped.append(f"{p} {page} .{x['key']}")
                            if (k == "mini" and x["h"] != 26) or (k == "ib" and x["h"] != 32):
                                sizes.append(f"{p} {page} .{x['key']} {x['h']}px")
                for key, sigs in seen.items():
                    if len(sigs) > 1:
                        drift.append(f"{p} .{key}: " + "; ".join(f"{s} on {','.join(sorted(v))}" for s, v in sigs.items()))
        finally:
            b.eval("applyTheme()")
        more = [f".{k} {len(v)}" for k, v in variants.items() if len(v) > 1]
        self.note(12, f"{counted} controls, {len(PAGES_9)} pages × {len(measure.themes(b))} themes"
                      + (f"; {len(drift)} drifts, first: {drift[0]}" if drift else "; each control one look on every page")
                      + (f"; off-size: {sizes[:2]}" if sizes else "; .mini 26px, .ib 32px")
                      + (f"; clipped: {clipped[:2]}" if clipped else "")
                      + (f"; looks per kind in creaite (variants with their own classes, for the eye): {', '.join(more)}" if more else ""))
        self.assertEqual(clipped, [], "clipped controls")
        self.assertEqual(sizes, [], ".mini is 26 px and .ib 32 px")
        self.assertEqual(drift, [], "a control drawn more than one way")


def lum(css):
    v = [float(x) for x in re.findall(r"[\d.]+", css)[:3]]
    f = [(u / 255) / 12.92 if u / 255 <= 0.03928 else (((u / 255) + 0.055) / 1.055) ** 2.4 for u in v]
    return 0.2126 * f[0] + 0.7152 * f[1] + 0.0722 * f[2]


class Judgement1(HandcheckCase):
    """Judgement checks: their screenshots go on the sheet; Alan ticks them."""

    def test_c04_strong_borders(self):
        """4. In creaite, Brightwater and Notion → the strong borders (table headers, Settings' section rules) show in light
        and dark; none has vanished."""
        b = self.b
        faint = []
        for p in ("creaite", "Brightwater", "Notion"):
            for m in ("light", "dark"):
                measure.theme(b, p, m)
                self.screen("work")
                r = b.eval("""(()=>{ const th=document.querySelector('#workTbl thead th'); if(!th) return null; const s=getComputedStyle(th);
                  return {w:s.borderBottomWidth, c:s.borderBottomColor, bg:getComputedStyle(document.querySelector('#v-work .tbl')||document.body).backgroundColor}; })()""")
                if not r or r["w"] == "0px" or r["c"] == r["bg"]:
                    faint.append(f"{p} {m}: {r}")
        b.eval("applyTheme()")
        n = self.sheet(4, "work") + self.sheet(4, "settings-advanced")
        self.note(4, f"{n} shots" + (f"; header rule missing in {faint}" if faint else "; the table header rule is drawn in all six (measured)"))

    def test_c10_help_fonts(self):
        """10. Help in Brightwater, then Retro Arcade → Help uses the theme's fonts (Retro Arcade's headings in its monospace
        font). In creaite, Help looks as before."""
        b = self.b
        fonts = {}
        for p in ("Brightwater", "Retro Arcade", "creaite"):
            measure.theme(b, p, "light")
            self.screen("help")
            fonts[p] = b.eval("(()=>{const h=document.querySelector('#v-help h2,#v-help h1'); return h?getComputedStyle(h).fontFamily.split(',')[0]:null})()")
        b.eval("applyTheme()")
        n = self.sheet(10, "help")
        self.note(10, f"{n} shots; heading fonts: " + ", ".join(f"{p} {f}" for p, f in fonts.items()))


class Measured2(HandcheckCase):
    """Phase 2: BL-324 and BL-325's other measured checks."""

    def setUp(self):
        super().setUp()
        # A headless page never has the system's focus, so focus and blur events don't fire and a handle's focus listener
        # (which sets its value) never runs; Chrome's focus emulation gives the page focus as a window in front has it.
        self.b.call("Emulation.setFocusEmulationEnabled", enabled=True)

    def test_c06_past_time_faint_text(self):
        """6. Today in light and dark → the past hours and the now-line are clearly visible; faint text (dates, hints) is
        readable, not ghostly."""
        # The page's clock goes to 11:30, so the 10:00 to 11:00 steering is past (its dot and its dimmed words) and the sun
        # (the now-line) stands at 11:30. In every palette, light and dark, as drawn on the day band (what is really behind
        # them, every ancestor's opacity multiplied in): the past dot and the sun are marks that must be seen, 3:1 (WCAG
        # 1.4.11, the audit's bar for --day-past and --day-sun); the past meeting's dimmed words are held to the same 3:1
        # (dimmed on purpose, but still to be read); all other text on Today (dates, hints, the hour labels) is AA, 4.5:1 (3
        # when large). The "·" separators are decorative (aria-hidden punctuation) and left out.
        from live_browser import pin_page_clock
        b = self.b
        pin_page_clock(b, self.now[:10] + " 11:30")
        self.screen("today")
        self.assertTrue(b.eval("!!document.querySelector('#v-today .dm.past') && !!document.querySelector('#dayLine .dot.past')"),
                        "at 11:30 the 10:00 meeting is past")
        self.assertTrue(b.eval("!!document.querySelector('#dayLine .sun')"), "the sun (now) is drawn at 11:30")
        low, worst, n = [], {}, 0

        def keep(kind, p, m, rows, bar):
            nonlocal n
            for r in rows:
                n += 1
                need = bar(r)
                if kind not in worst or r["ratio"] < worst[kind][0]:
                    worst[kind] = (r["ratio"], f"{p} {m}")
                if r["ratio"] < need:
                    low.append((kind, f"{kind} {p} {m}: {r['sig']} \"{r['text'][:16]}\" {r['ratio']}:1 < {need}"))
        text_bar = lambda r: 3 if measure.large(r) else 4.5          # noqa: E731
        try:
            for p in measure.themes(b):
                for m in ("light", "dark"):
                    measure.theme(b, p, m)
                    keep("past dot", p, m, measure.paint_contrast(b, "#dayLine .dot.past", "fill"), lambda r: 3)
                    keep("now-line", p, m, measure.paint_contrast(b, "#dayLine .sun circle, #dayLine .sun path", "stroke"), lambda r: 3)
                    keep("hour labels", p, m, measure.paint_contrast(b, "#dayLine .hr", "fill"), text_bar)
                    words = [r for r in measure.paint_contrast(b, ".dm.past > :not(.acts), .dm.past > :not(.acts) *", scope="#v-today") if r["text"]]
                    keep("past words", p, m, words, lambda r: 3)
                    # the other text: elements with words of their own (not only their children's), outside the past meeting
                    own = b.eval("""[...document.querySelectorAll('#v-today *:not(svg):not(svg *)')].filter(e=>{ const r=e.getBoundingClientRect();
                      return r.width>0&&r.height>0&&getComputedStyle(e).visibility!=='hidden'&&!e.closest('[hidden],[inert]'); })
                      .map(e=>!e.closest('.dm.past')&&!e.matches('.daysep')&&[...e.childNodes].some(c=>c.nodeType===3&&c.textContent.trim()))""")
                    allrows = measure.paint_contrast(b, "#v-today *:not(svg):not(svg *)")
                    text = [r for r, mine in zip(allrows, own) if mine]
                    self.assertEqual(len(allrows), len(own), "one visibility rule for both lists")
                    self.assertTrue(text, "Today has text to measure")
                    keep("faint text", p, m, text, text_bar)
        finally:
            b.eval("applyTheme()")
        kinds = "; ".join(f"{k} lowest {v[0]}:1 ({v[1]})" for k, v in worst.items())
        self.note(6, f"{len(measure.themes(b))} palettes × light, dark at 11:30 (the 10:00 meeting past), {n} measures; {kinds}"
                     + (f"; {len(low)} under the bar, first: {low[0][1]}" if low else ""))
        if low:
            by = {}
            for kind, _ in low:
                by[kind] = by.get(kind, 0) + 1
            self.fail("under the contrast bar (palette × mode × element): " + ", ".join(f"{k} {v}" for k, v in by.items()))

    def test_c07_resize_handle_value(self):
        """7. VoiceOver (⌘F5) on a Work column-resize handle → it reads a value (its width) and changes as you resize with ←
        and →. (Automated through the accessibility tree: measure.ax_node; VoiceOver itself stays live only.)"""
        b = self.b
        self.screen("work")
        cols = b.eval("[...document.querySelectorAll('#workTbl thead th')].filter(th=>th.querySelector('.colrz')).map(th=>th.dataset.col)")
        self.assertTrue(cols, "Work's headings have resize handles")
        col = cols[1] if len(cols) > 1 else cols[0]           # not the first (title) column: it takes the table's spare width
        sel = f"#workTbl thead th[data-col=\"{col}\"] .colrz"
        width = f"Math.round(document.querySelector('#workTbl thead th[data-col=\"{col}\"]').getBoundingClientRect().width)"
        try:
            b.eval(f"document.querySelector({json.dumps(sel)}).focus()")
            b.pump(0.1)
            start = measure.ax_node(b, sel)
            self.assertEqual(start["role"], "separator")
            self.assertTrue((start["name"] or "").startswith("Resize "), f"named: {start['name']}")
            self.assertTrue(start["props"].get("focused"), "the handle takes focus")
            self.assertEqual((start["props"].get("valuemin"), start["props"].get("valuemax")), (60, 900))
            self.assertIsNotNone(start["value"], "the handle has a value (aria-valuenow)")
            w0 = b.eval(width)
            self.assertLessEqual(abs(start["value"] - w0), 1, f"the value is the column's width: {start['value']} against {w0} px")
            steps = [("start", start["value"], w0)]
            for k in ("ArrowRight", "ArrowRight", "ArrowLeft"):
                b.key(k)
                b.pump(0.1)
                steps.append((k, measure.ax_node(b, sel)["value"], b.eval(width)))
            for (_, v0, _), (k, v1, w1) in zip(steps, steps[1:]):
                self.assertEqual(v1 - v0, 16 if k == "ArrowRight" else -16, f"{k} moves the width by 16 px ({v0} → {v1})")
                self.assertLessEqual(abs(v1 - w1), 1, f"after {k} the value is the width: {v1} against {w1} px")
        finally:
            b.eval("(()=>{ localStorage.removeItem('creaite-colwidths'); return true; })()")
        self.note(7, f"{len(cols)} handles; \"{start['name']}\": separator, valuenow "
                     + " → ".join(str(v) for _, v, _ in steps) + " px (→ → ←), the column's width each time, range 60 to 900")

    def test_c08_sortable_headers(self):
        """8. Settings › People, Tab to a column heading → it is a button; Enter sorts, and VoiceOver reads the sort order."""
        # The sortable headings are the People page's (th[data-psort], reached from Settings › People); Settings › People's
        # own tables have none. Chrome's accessibility tree gives no sort property over CDP, so the order VoiceOver is given
        # is read from aria-sort on the heading, whose role must be columnheader (where aria-sort is allowed).
        b = self.b
        self.screen("settings-people")
        in_settings = b.eval("document.querySelectorAll('#v-settings th[data-psort], #v-settings th button').length")
        self.screen("people")
        heads = b.eval("[...document.querySelectorAll('#v-people th[data-psort]')].map(th=>th.dataset.psort)")
        self.assertTrue(heads, "People has sortable headings")
        names = "[...document.querySelectorAll('#v-people tbody tr')].map(r=>r.cells[0].innerText.trim().split('\\n')[0])"
        btn = "#v-people th[data-psort=\"name\"] button"
        b.eval(f"document.querySelector('#v-people th[data-psort=\"{heads[1]}\"] button').focus()")
        b.key("Tab", 8)                                        # Shift+Tab: back to the first heading, by the keyboard
        self.assertEqual(b.eval("document.activeElement.closest('th')?.dataset.psort"), "name", "Tab reaches the Name heading")
        node = measure.ax_node(b, btn)
        self.assertEqual(node["role"], "button", "the heading is a button")
        self.assertTrue(node["props"].get("focused"))
        head = measure.ax_node(b, "#v-people th[data-psort=\"name\"]")
        self.assertEqual(head["role"], "columnheader")
        seen, lost = [], []
        for want in ("ascending", "descending"):
            b.key("Enter")
            b.pump(0.3)
            sort = b.eval("document.querySelector('#v-people th[data-psort=\"name\"]').getAttribute('aria-sort')")
            order = b.eval(names)
            self.assertEqual(sort, want, "Enter sorts by name and the heading says which way")
            self.assertEqual(order, sorted(order, reverse=want == "descending"), f"rows in {want} order")
            others = b.eval("[...document.querySelectorAll('#v-people th[data-psort]:not([data-psort=\"name\"])')].map(t=>t.getAttribute('aria-sort'))")
            self.assertEqual(set(others), {"none"}, "the other headings say none")
            focus = b.eval("(()=>{const a=document.activeElement; return a&&a.closest&&a.closest('th')?a.closest('th').dataset.psort:a.tagName.toLowerCase()})()")
            seen.append(f"{want} ({measure.ax_node(b, btn)['name']})")
            if focus != "name":
                lost.append(f"after Enter ({want}) focus is on {focus}")
                b.eval(f"document.querySelector({json.dumps(btn)}).focus()")
        self.note(8, f"{len(heads)} sortable headings on People (Settings › People's tables: {in_settings}); Name: Tab reaches it, "
                     f"a button in a columnheader; Enter sorts {', then '.join(seen)}, aria-sort follows"
                     + (f"; {lost[0]}: VoiceOver has nothing to read the new order from" if lost else "; focus stays on the heading"))
        if lost:
            self.fail(f"{lost[0]}: focus leaves the heading after Enter, so VoiceOver can't read the new order")

    def test_c09_one_button_and_field_size(self):
        """9. Today, Work, Review, Intake, Settings, Activity and Files → buttons are one height (32 px) and fields one height
        (32 px), bar Files' large centred search bar (40 px, by design). Section headings look the same on each page."""
        # Buttons are .btn (the small .mini and the icon .ib are check 12's). Fields are one-line inputs and selects; a
        # textarea grows with its text and is left out. Settings is all three of its tabs. Section headings are the pages' h2;
        # Settings › Advanced's group labels (h2.setgroup, above its sections) are a second kind and listed in the note.
        b = self.b
        pages = ("today", "work", "review", "intake", "settings-essentials", "settings-advanced", "settings-people", "activity", "files")
        views = {"today": "#v-today", "work": "#v-work", "review": "#v-review", "intake": "#v-inbox", "activity": "#v-activity",
                 "files": "#v-files", "settings-essentials": "#v-settings", "settings-advanced": "#v-settings", "settings-people": "#v-settings"}
        fields = ("input:not([type=checkbox]):not([type=radio]):not([type=range]):not([type=file]):not([type=color]):not([type=hidden]),"
                  " select")
        head_js = """(v)=>[...document.querySelectorAll(v+' h2')].filter(e=>e.offsetParent).map(e=>{ const s=getComputedStyle(e);
          return {group:e.classList.contains('setgroup'), sig:[s.fontSize,s.fontWeight,s.lineHeight,s.fontFamily.split(',')[0],s.textTransform,s.color].join(' ')}; })"""
        off_b, off_f, heads, groups, nb, nf = [], [], {}, set(), 0, 0
        for page in pages:
            self.screen(page)
            v = views[page]
            for x in measure.boxes(b, ".btn", v):
                nb += 1
                if x["h"] != 32:
                    off_b.append(f"{page} {x['sig']} \"{x['text'][:20]}\" {x['h']}px")
            for x in measure.boxes(b, fields, v):
                nf += 1
                want = 40 if page == "files" and x["sig"].startswith("input#vsInput") else 32
                if x["h"] != want:
                    off_f.append(f"{page} {x['sig']} {x['h']}px")
            for h in b.eval(f"({head_js})({json.dumps(v)})"):
                if h["group"]:
                    groups.add(h["sig"])
                else:
                    heads.setdefault(h["sig"], set()).add(page)
        self.assertTrue(b.eval("!!document.querySelector('#vsInput')") and 40 in [x["h"] for x in measure.boxes(b, "#vsInput")],
                        "Files' large search bar is 40 px")
        self.note(9, f"{nb} buttons and {nf} fields on {len(pages)} screens (Settings' three tabs)"
                     + (f"; buttons not 32 px: {'; '.join(off_b[:3])}" if off_b else "; every .btn 32 px")
                     + (f"; fields off size ({len(off_f)}): {'; '.join(sorted(set(off_f))[:6])}" if off_f
                        else "; every field 32 px, Files' search 40 px")
                     + (f"; section headings one look ({next(iter(heads))})" if len(heads) == 1 else f"; {len(heads)} heading looks: {heads}")
                     + (f"; plus Settings › Advanced's group labels ({', '.join(groups)})" if groups else ""))
        bad = ([f"{len(off_b)} buttons not 32 px"] if off_b else []) + ([f"{len(off_f)} fields not 32 px"] if off_f else []) \
            + ([f"{len(heads)} section-heading looks"] if len(heads) != 1 else [])
        if bad:
            self.fail(", ".join(bad))

    def test_c16_touch_targets(self):
        """16. Checkboxes on Review, Intake and Activity, the Settings switches and the column-resize handles → each easy to
        hit (at least 24 px; DevTools › Inspect shows the box)."""
        # Each target's own box (DevTools › Inspect), both sides at least 24 px, and its centre hit-tests to it (nothing on top).
        b = self.b
        hit_js = """(sel,scope)=>[...document.querySelector(scope).querySelectorAll(sel)].filter(e=>{ const r=e.getBoundingClientRect();
          return r.width>0&&r.height>0&&!e.closest('[hidden],[inert]'); }).map(e=>{ e.scrollIntoView({block:'center',inline:'center'});
          const r=e.getBoundingClientRect(), h=document.elementFromPoint(r.left+r.width/2, r.top+r.height/2);
          return !!h&&(h===e||e.contains(h)||(h.closest('label')&&h.closest('label').contains(e))); })"""
        groups = [("Review checkboxes", "review", "#v-review", "input[type=checkbox]:not(.switch)"),
                  ("Intake checkboxes", "intake", "#v-inbox", "input[type=checkbox]:not(.switch)"),
                  ("Activity checkboxes", "activity", "#v-activity", "input[type=checkbox]:not(.switch)"),
                  ("Settings switches", "settings-essentials", "#v-settings", "input.switch"),
                  ("Settings switches", "settings-advanced", "#v-settings", "input.switch"),
                  ("resize handles", "work", "#v-work", ".colrz"),
                  ("resize handles", "projects", "#v-projects", ".colrz"),
                  ("resize handles", "today", "#v-today", ".colrz")]
        small, missed, sizes = [], [], {}
        for label, page, scope, sel in groups:
            self.screen(page)
            boxes = measure.hit_box(b, sel, scope)
            self.assertTrue(boxes, f"{label} on {page}")
            for x in boxes:
                sizes.setdefault(label, set()).add(f"{x['w']:g}×{x['h']:g}")
                if min(x["w"], x["h"]) < 24:
                    small.append(f"{page} {x['sig']} {x['w']}×{x['h']}")
            hits = b.eval(f"({hit_js})({json.dumps(sel)},{json.dumps(scope)})")
            missed += [f"{page} {sel} #{i}" for i, ok in enumerate(hits) if not ok]
        self.note(16, "; ".join(f"{k} {', '.join(sorted(v))} px" for k, v in sizes.items())
                      + (f"; under 24 px: {small[:3]}" if small else "; all at least 24 px")
                      + (f"; covered at the centre: {missed[:3]}" if missed else "; each hit at its centre"))
        if small or missed:
            self.fail(f"{len(small)} targets under 24 px, {len(missed)} covered at their centre")

    def test_c19_320_px_layers(self):
        """19. Every screen at 320 px → no sideways scroll. Menus, popovers, the peek, toasts and ask creaite stack in the
        right order (a menu over the peek, a toast over everything)."""
        # Layers at 320 px, each really open: the peek (a Work action), a popover from it (its Status picker), a menu (Work's
        # More views), ask creaite and a toast. Where two overlap the middle of the overlap is hit-tested; where they don't,
        # their stacking order decides (measure.on_top). The order: menu and popover over the peek, ask creaite over the peek,
        # a toast over all of them.
        b = self.b
        from hcbase import SCREENS
        wide, layers, wrong = [], [], []
        try:
            measure.width(b, 320, 800)
            for name in SCREENS:
                self.screen(name)
                o = measure.overflow_x(b)
                if not o["ok"]:
                    wide.append(f"{name} {o['sw']}px")

            def need(top, under, what):
                r = measure.on_top(b, top, under)
                self.assertIsNotNone(r["ok"], f"{what}: both showing ({top}, {under})")
                layers.append(f"{what} {'yes' if r['ok'] else 'NO'} ({r['how']}, z {r['top_z']}/{r['under_z']})")
                if not r["ok"]:
                    wrong.append(f"{what}: {top} z {r['top_z']} under {under} z {r['under_z']} ({r['how']})")

            def toast():
                b.eval("snack('Hand check toast')")
                b.pump(0.3)
            self.screen("work")
            b.eval("openRecord('actions',A[0].id)")
            b.wait("document.querySelector('#panel.peek.on')")
            b.pump(0.4)
            b.click('#pkProps [data-pkp="st"]')
            b.wait("document.querySelector('.pkpop')")
            need(".pkpop", "#panel.peek.on", "popover over the peek")
            toast()
            need(".snack.on", ".pkpop", "toast over the popover")
            need(".snack.on", "#panel.peek.on", "toast over the peek")
            b.key("Escape")
            b.pump(0.2)
            b.eval("document.getElementById('vmore').click()")
            b.wait("document.querySelector('#vmoreMenu.on')")
            need("#vmoreMenu.on", "#panel.peek.on", "menu over the peek")
            toast()
            need(".snack.on", "#vmoreMenu.on", "toast over the menu")
            b.key("Escape")
            b.pump(0.2)
            b.eval("openChat()")
            b.wait("getComputedStyle(document.getElementById('chat')).display!=='none'")
            b.pump(0.3)
            need("#chat", "#panel.peek.on", "ask creaite over the peek")
            toast()
            need(".snack.on", "#chat", "toast over ask creaite")
        finally:
            measure.width(b, self.width, self.height)
        self.note(19, f"{len(SCREENS)} screens at 320 px: " + (f"sideways scroll on {wide}" if wide else "no sideways scroll")
                      + "; " + "; ".join(layers))
        if wide or wrong:
            self.fail("; ".join(([f"sideways scroll at 320 px on {', '.join(w.split()[0] for w in wide)}"] if wide else []) + wrong))


class Judgement2(HandcheckCase):
    """Phase 2: the other judgement checks (screenshots on the sheet)."""

    @phase2()
    def test_c11_prep_page_fonts(self):
        """11. Build a prep page (Today › the FAL Steering committee › Prep page), then open it from the Agendas folder → the
        dashboard's fonts (where installed) and status colours, light and dark; still one file."""

    @phase2()
    def test_c18_offline_page(self):
        """18. Stop the server and reload → the offline page uses creaite's fonts and colours, light and dark, with a 32 px
        button. (Needs own_vault: it stops the server.)"""

    @phase2()
    def test_c20_audits_snapshots(self):
        """20. `python3 dev/tools/token_audit.py` and `dev/tools/ui_audit.py` from the repository → no P1 in shipped files; one
        variant of each control. Look through `dev/reviews/bl325-before-after/index.html` → you agree the re-recorded
        snapshots."""

    @phase2()
    def test_c51_dark_forced_320_help(self):
        """51. Dark mode, forced colours and 320 px: the Archived chip and Move back, Health's Archiving section, the alert card
        and quiet line, → readable, with no sideways scroll. Help says what Archiving and Move back are."""


class Bl333And10(HandcheckCase):
    """Phase 2: BL-333 (21, 22) and BL-10 archiving old items (23 to 29), with check 30's Health line. Own vault."""
    own_vault = True

    @phase2()
    def test_c21_today_stops_at_bottom(self):
        """21. Today at 1400 px, scroll to the bottom with the wheel → it stops at the last content; the rail doesn't scroll
        away. In the Console, `document.scrollingElement.scrollHeight === innerHeight` → `true`."""

    @phase2()
    def test_c22_intake_prep(self):
        """22. The same on Intake (at 1400 and 320 px), the Prep popup over Today, and Meetings › Prep → `true` on each, and
        the rail stays put."""

    @phase2()
    def test_c23_due_items_listed(self):
        """23. Make an old closed item: close FAL-A-004 and cancel ORX-R-001; `archive.py items --dry-run` 7 months on → both
        listed. An open action, any decision and any milestone are not."""

    @phase2()
    def test_c24_archived_through_apply(self):
        """24. Run it again without `--dry-run` → "Archived 2 items". Activity shows one apply (source archive); Review gets
        nothing."""

    @phase2()
    def test_c25_gone_search_health(self):
        """25. Work, Today and the Excel export → those two items are gone. Search for FAL-A-004's words → found, marked
        Archived. Settings › Health › Archiving → "Archived 2 items on DD-MM-YYYY"."""

    @phase2()
    def test_c26_show_archived(self):
        """26. Turn on "Show archived projects and items" (Settings › Work and views) → both are back, marked. Turn it off."""

    @phase2()
    def test_c27_edit_unarchives(self):
        """27. Search for FAL-A-004, open it and change its priority → it is live again (back in Work). Activity shows the
        un-archive in its change log."""

    @phase2()
    def test_c28_undo_nothing_in_review(self):
        """28. Undo the archive apply (Activity › Undo, or `tracker.py undo`) → ORX-R-001 is back, and nothing appears in
        Review."""

    @phase2()
    def test_c29_settings_zero_turns_off(self):
        """29. Settings › Advanced › Archiving → `archive.after_months` for actions, RAID and promises (6) and
        `archive.reports_after_months` (12). Set RAID to 0 and repeat the dry run with a cancelled RAID item → not listed."""

    @phase2()
    def test_c30_health_line_card(self):
        """30. Settings › Health → "Archive 4 reports and minutes older than 12 months", with **Archive them**. Press it → the
        change card lists "Move file … → …/_Archive/…" for the FAL weekly report, client report and steering minutes, and the
        portfolio's minutes. Not the transcript, the ad hoc notes or ORX's recent report."""


class Bl03And331(HandcheckCase):
    """Phase 2: BL-03 archiving old reports and minutes (31 to 34) and BL-331 move back (35 to 41). Own vault."""
    own_vault = True

    @phase2()
    def test_c31_moved_incl_portfolio(self):
        """31. Approve → the files are in `projects/FAL Falcon Data Platform/_Archive/reports/` and `/_Archive/minutes/`, and
        the portfolio's in `projects/_portfolio/_Archive/minutes/`. Nothing is deleted."""

    @phase2()
    def test_c32_links_not_indexed_guard(self):
        """32. Open FAL's latest-reports link for the moved report → it still opens. Search for its words → not found. In ask
        creaite, "read FAL's archived weekly report" → refused."""

    @phase2()
    def test_c33_quiet_for_month(self):
        """33. Health → the line now says "Archived 4 reports and minutes on DD-MM-YYYY" and stays quiet for the rest of the
        month."""

    @phase2()
    def test_c34_undo(self):
        """34. Undo → the files are back where they were, and the `_Archive` folders the move made are gone."""

    @phase2()
    def test_c35_archived_chip(self):
        """35. Archive them again (check 30). Files → an **Archived** chip; it lists the four moved files, each tagged Archived
        with **Move back**. No other row in Files has Move back. Clicking a name opens the file."""

    @phase2()
    def test_c36_move_back(self):
        """36. Move back the FAL weekly report → the change card. Approve → it is back in `reports/`, gone from the Archived
        list, and search finds it again."""

    @phase2()
    def test_c37_not_offered_again(self):
        """37. Health's monthly line → it does not offer that report again."""

    @phase2()
    def test_c38_undo(self):
        """38. Undo → the report is back in `_Archive`, unindexed."""

    @phase2()
    def test_c39_taken_place_refused(self):
        """39. Put a file with the same name in `reports/`, then Move back that report → refused: "rename or move that file
        first". The file in `reports/` is unchanged."""

    @phase2()
    def test_c40_portfolio_minutes(self):
        """40. Move back the portfolio's minutes → back in `projects/_portfolio/minutes/`."""

    @phase2()
    def test_c41_ask_creaite_refused(self):
        """41. In ask creaite, "move the archived FAL steering minutes back" → refused: "an archived file is moved back from
        Files (Move back), never from ask creaite"."""


class Bl334And316(HandcheckCase):
    """Phase 2: BL-334 alerts read the conversation (42 to 47) and BL-316's consistency (49, 50). Own vault."""
    own_vault = True

    @phase2()
    def test_c42_one_card_per_conversation(self):
        """42. Today → one card titled "Falcon go-live" (not "Group chat"), "updated 08:40", the summary, and two candidates,
        each with **Create work item** and **Dismiss**. The project is Falcon Data Platform, matched from the title."""

    @phase2()
    def test_c43_quiet_line(self):
        """43. A second conversation titled "Group chat" with nothing in it → one quiet line ("… : nothing for you"), with no
        buttons and no count. Its title is the people in it, never "Group chat"."""

    @phase2()
    def test_c44_same_card_updated(self):
        """44. Record the first conversation again at 09:05 with a third item → the same card is updated ("updated 09:05", three
        candidates). No second card."""

    @phase2()
    def test_c45_dismiss_create(self):
        """45. Dismiss the risk → it goes; nothing in Review. Create work item on the action → one proposal in Review, for
        Falcon Data Platform."""

    @phase2()
    def test_c46_sweep_skips_it(self):
        """46. Stage a sweep file whose item carries that conversation and a time before 09:05 → nothing proposed for it:
        "skipped (that conversation is summarised on Today …)"."""

    @phase2()
    def test_c47_no_message_text_no_vip(self):
        """47. `system/staging/vip.json` → the summary and candidates only; no message text. Nothing on screen says "VIP"."""

    @phase2()
    def test_c49_shared_behaviour(self):
        """49. On every screen, open each menu, picker and dialog: ↑ ↓ move, Enter chooses, Esc closes and returns focus, Tab
        stays inside a dialog. (dev/tests/test_shared_behaviour.py's probe, against this vault.)"""

    @phase2()
    def test_c50_old_helpers_zero(self):
        """50. `python3 dev/tools/check.py` from the repository → the old-helper count (newMenu, pkList, drawPicker, snackAdd and
        the rest) is 0."""


if __name__ == "__main__":
    unittest.main()
