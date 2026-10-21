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
# 2.6.0 (#232 C2): Review and Intake are one page ("intake-review"); it stands for both
PAGES_9 = ("today", "work", "intake-review", "settings-essentials", "activity", "files")


class Scriptable1(HandcheckCase):
    """Start-up and BL-325's wording and primary actions. Own vault: check 13 adds a pending decision and 15 records a sweep."""
    own_vault = True

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
        # Decisions needed shows only while a pending decision has a decision maker and a needed-by date: add one, as cx-edit
        # does (propose.py stage, then tracker.py apply)
        from datetime import date, timedelta
        day = date.fromisoformat((self.now or date.today().isoformat())[:10])
        spec = self.vault / "system/staging/drafts/hc-decision.json"
        spec.write_text(json.dumps({"source_run": "cx-edit", "items": [{"op": "new", "table": "decisions", "values": {
            "project": "FAL", "decision": "Approve the go-live date for the data platform", "status": "Pending",
            "made_by": "Rashid Al Suwaidi", "needed_by": (day + timedelta(days=5)).isoformat(), "source": "hand check 13 (BL-341)"}}]}),
            encoding="utf-8")
        code, out = self.run_in_vault("propose.py", "stage", "system/staging/drafts/hc-decision.json")
        self.assertEqual(code, 0, out)
        code, out = self.run_in_vault("tracker.py", "apply")
        self.assertEqual(code, 0, out)
        b.reload("typeof go==='function' && LIVE")
        style = "e=>{const s=getComputedStyle(e); return [s.fontSize,s.fontWeight,s.fontFamily,s.textTransform,s.fontVariantCaps,s.letterSpacing].join('|')}"
        self.screen("today")
        today = b.eval(f"[...document.querySelectorAll('#v-today h2')].filter(e=>e.offsetParent).map(e=>({{t:e.firstChild?.textContent?.trim()||e.innerText.split('\\n')[0], s:({style})(e)}}))")
        self.assertTrue(today, "Today has section headings")
        names = [h["t"] for h in today]
        for want in ("Decisions needed", "Needs attention", "Week ahead", "Portfolio"):
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
        self.note(13, f"{len(today)} headings (Decisions needed seeded: a pending FAL decision through propose.py stage and tracker.py apply), same font as Settings' ({settings[0].split('|')[0]}), none uppercase or small caps; title 34px")

    def test_c14_intake_names(self):
        """14. Intake → "Calendar import", "Upload files" and "Quick capture" in sentence case, with no icons beside them.
        Help and Settings › Advanced use the same names."""
        # 2.6.0 (#232 C2): the one Intake page has no Calendar import, Upload files or Quick capture sections any more (its
        # meetings and files are rows; Upload files is its drop and button; Quick capture became the note drawer, ⌘⇧N). What
        # the check guards stays: the page's own section headings in sentence case with no icons beside them, and the three
        # names, as Help and Settings use them, never in their old forms.
        b = self.b
        names = ["Calendar import", "Upload files", "Quick capture"]
        self.screen("intake-review")
        heads = b.eval("[...document.querySelectorAll('#v-intake-review h2')].filter(e=>e.offsetParent).map(e=>({t:e.innerText.trim(), icons:e.querySelectorAll('svg,img,.i').length, tt:getComputedStyle(e).textTransform}))")
        self.assertTrue(heads, "Intake has section headings")
        for h in heads:
            self.assertTrue(h["t"][:1].isupper() and h["t"][1:] != h["t"][1:].upper(), f"sentence case: {h['t']}")
        self.assertEqual({h["icons"] for h in heads}, {0}, "no icons beside them")
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
        self.note(14, f"Intake's headings {', '.join(h['t'] for h in heads)} (2.6's one page: the three sections are gone), sentence case, no icons; Help names all three; Settings › Advanced names {', '.join(in_adv) or 'none of them'}")

    def test_c15_primary_actions(self):
        """15. Primary actions keep their look: Today's and Intake's filled button, Review's outlined Approve, Work's tinted "+".
        (2.6.0, #232 C2: Review and Intake are one page; its Approve is the one checked outlined, and any filled button it
        draws is checked filled.)"""
        b = self.b
        look = "e=>{const s=getComputedStyle(e); return {bg:s.backgroundColor, border:s.borderTopColor, bw:s.borderTopWidth, color:s.color, text:e.innerText.trim().slice(0,30)}}"
        transparent = ("rgba(0, 0, 0, 0)", "transparent")
        # Today's filled button is Getting started's next step. Before the first sweep that step is Connect Microsoft 365, which
        # has Copy, Check again and How instead of a button; once a sweep is recorded, Open Review is the filled one. So: Today
        # once (the checklist is seen, as on a first run), a sweep recorded (sweep.py done --normal), Today again.
        self.screen("today")
        self.assertTrue(b.eval("!!document.querySelector('#setupList')"), "Getting started shows before the first sweep")
        before = b.eval("[...document.querySelectorAll('#v-today .btn.primary')].filter(e=>e.offsetParent).length")
        code, out = self.run_in_vault("sweep.py", "done", "--started", f"{(self.now or '')[:10]} 09:00", "--normal")
        self.assertEqual(code, 0, out)
        b.reload("typeof go==='function' && LIVE")
        self.screen("today")
        today = b.eval(f"[...document.querySelectorAll('#v-today .btn.primary')].filter(e=>e.offsetParent).map({look})")
        self.screen("intake-review")
        intake = b.eval(f"[...document.querySelectorAll('#v-intake-review .btn.primary')].filter(e=>e.offsetParent).map({look})")
        self.assertTrue(today, "Today has a primary button")
        for where, bs in (("Today", today), ("Intake", intake)):
            for x in bs:
                self.assertNotIn(x["bg"], transparent, f"{where}'s {x['text']} is filled")
        approve = b.eval(f"[...document.querySelectorAll('#v-intake-review button[data-ira=approve]')].filter(e=>e.offsetParent).map({look})")
        self.assertTrue(approve, "Intake shows Approve")
        surface = b.eval("getComputedStyle(document.documentElement).getPropertyValue('--surface').trim()")
        for x in approve[:3]:
            self.assertNotEqual(x["bw"], "0px", "Approve is outlined")
        self.screen("work")
        plus = b.eval(f"(()=>{{const e=document.getElementById('newBtn'); return e&&({look})(e)}})()")
        self.assertTrue(plus, "Work's + button")
        self.assertNotIn(plus["bg"], transparent, "Work's + is tinted")
        self.note(15, f"Today's {today[0]['text']} {today[0]['bg']} (after a sweep; before it, Getting started had {before or 'no'} filled button: its next step, Connect Microsoft 365, has none), Intake {intake[0]['bg'] if intake else 'no filled button (2.6)'}, Approve outlined ({approve[0]['bw']} {approve[0]['border']}; surface {surface}), Work + {plus['bg']}")

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


def open_prep_peek(b, title="Steering committee"):
    """#111 B (2.2): Today's meeting title opens the Prep peek on focus (the old Prepare button and Prep popup are gone).
    Focus the title of today's meeting named `title` (else the first with a peek) and wait for the peek's Open the prep page."""
    b.call("Emulation.setFocusEmulationEnabled", enabled=True)
    b.eval("document.activeElement&&document.activeElement.blur()")
    b.wait("document.querySelector('#dayMeets .dmti')", 15)
    b.eval(f"""(()=>{{ const ts=[...document.querySelectorAll('#dayMeets .dmti')];
      (ts.find(t=>t.textContent.includes({json.dumps(title)}))||ts[0]).focus(); return true; }})()""")
    b.wait("document.querySelector('#dayMeets .dmpop [data-prepgo]')", 15)


def measure_screens():
    """Every screen once: "review" and "intake" are hcbase's aliases of the one Intake page (2.6.0, #232 C2), so left out."""
    from hcbase import SCREENS
    return [n for n in SCREENS if n not in ("review", "intake")]


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
        """8. People, Tab to the Name column heading → a button in a column header; Enter sorts ascending, then descending,
        aria-sort follows and focus stays on the heading, so VoiceOver reads the new order."""
        # The sortable headings are the People page's (th[data-psort], reached from Settings › People); Settings › People's
        # own tables have none. Chrome's accessibility tree gives no sort property over CDP, so the order VoiceOver is given
        # is read from aria-sort on the heading, whose role must be columnheader (where aria-sort is allowed).
        b = self.b
        self.screen("settings-essentials")                    # the Settings line: Settings › People is the People page now
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
        pages = ("today", "work", "intake-review", "settings-essentials", "settings-advanced", "project-settings", "activity", "files")
        views = {"today": "#v-today", "work": "#v-work", "intake-review": "#v-intake-review", "activity": "#v-activity",
                 "files": "#v-files", "settings-essentials": "#v-settings", "settings-advanced": "#v-settings", "project-settings": "#v-psettings"}
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
        """16. Checkboxes on Review, Intake (2.6: one page with none) and Activity, the Settings switches and the column-resize handles → each easy to
        hit (at least 24 px; DevTools › Inspect shows the box)."""
        # Each target's own box (DevTools › Inspect), both sides at least 24 px, and its centre hit-tests to it (nothing on top).
        b = self.b
        hit_js = """(sel,scope)=>[...document.querySelector(scope).querySelectorAll(sel)].filter(e=>{ const r=e.getBoundingClientRect();
          return r.width>0&&r.height>0&&!e.closest('[hidden],[inert]'); }).map(e=>{ e.scrollIntoView({block:'center',inline:'center'});
          const r=e.getBoundingClientRect(), h=document.elementFromPoint(r.left+r.width/2, r.top+r.height/2);
          return !!h&&(h===e||e.contains(h)||(h.closest('label')&&h.closest('label').contains(e))); })"""
        # 2.6.0 (#232 C2): the one Intake page has no checkboxes (Review's and Intake's went with their pages; bulk approval
        # is Approve routine), so it has none to measure; asserted, so a checkbox that comes back is measured here again
        self.screen("intake-review")
        self.assertEqual(b.eval("document.querySelectorAll('#v-intake-review input[type=checkbox]').length"), 0,
                         "Intake has checkboxes again: measure them here as Review's and Intake's were")
        groups = [("Activity checkboxes", "activity", "#v-activity", "input[type=checkbox]:not(.switch)"),
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
        wide, layers, wrong = [], [], []
        try:
            measure.width(b, 320, 800)
            for name in measure_screens():
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
        self.note(19, f"{len(measure_screens())} screens at 320 px: " + (f"sideways scroll on {wide}" if wide else "no sideways scroll")
                      + "; " + "; ".join(layers))
        if wide or wrong:
            self.fail("; ".join(([f"sideways scroll at 320 px on {', '.join(w.split()[0] for w in wide)}"] if wide else []) + wrong))


class Judgement2(HandcheckCase):
    """Phase 2: the other judgement checks (screenshots on the sheet; what can be measured is measured and noted). Own vault:
    check 11 writes a prep page, 18 stops and restarts the server, 51 archives the old reports and records two conversations."""
    own_vault = True
    TOKENS = ("bg", "surface", "ink", "muted", "line", "accent")
    STATUS = ("ok", "warn", "bad")

    # ── helpers (this class's own) ──

    def _vars(self, names):
        """The page's root custom properties, lower case: {name: value}."""
        return self.b.eval("(n=>{ const s=getComputedStyle(document.documentElement); return Object.fromEntries(n.map(k=>[k, s.getPropertyValue('--'+k).trim().toLowerCase()])); })(%s)" % json.dumps(list(names)))

    def _dashboard_vars(self, names):
        """The dashboard's creaite theme tokens, light and dark: {mode: {name: value}}."""
        out = {}
        try:
            for m in ("light", "dark"):
                measure.theme(self.b, "creaite", m)
                out[m] = self._vars(names)
        finally:
            self.b.eval("applyTheme()")
        return out

    def _record(self, n, screen, palette, mode, w, note=""):
        """One screenshot of what is on screen now, on the sheet."""
        import sheet as sheetmod
        if not sheetmod.enabled():
            return 0
        path = sheetmod.shot_path(n, screen, palette, mode, w)
        measure.shot(self.b, path)
        sheetmod.record(n, screen, palette, mode, w, path, note)
        return 1

    def _file_page_shots(self, n, screen, measure_fn=None):
        """Screenshots of the page now loaded (not the dashboard), light and dark × 1400 and 320 px, by the system's colour
        scheme (DevTools › Rendering). measure_fn(mode, width) runs before each shot; returns {(mode, width): its value}."""
        b, k, seen = self.b, 0, {}
        try:
            for w in (1400, 320):
                measure.width(b, w, 1000 if w > 600 else 800)
                for m in ("light", "dark"):
                    measure.media(b, dark=(m == "dark"))
                    b.pump(0.2)
                    if measure_fn:
                        seen[(m, w)] = measure_fn(m, w)
                    k += self._record(n, screen, "creaite", m, w)
        finally:
            measure.media(b)
            measure.width(b, self.width, self.height)
        return k, seen

    # ── the checks ──

    def test_c11_prep_page_fonts(self):
        """11. Build a prep page (Today › the FAL Steering committee › Prep page; since 2.2 its title's Prep peek › Open the prep
        page), then open it from the Agendas folder → the
        dashboard's fonts (where installed) and status colours, light and dark; still one file."""
        b = self.b
        dash = self._dashboard_vars(self.STATUS)
        # Today › the meeting's Prep peek (#111 B: its title; the Prepare button is gone) › Open the prep page › Refresh research:
        # the stand-in Claude researches, the server writes it
        self.screen("today")
        open_prep_peek(b)
        b.click("#dayMeets .dmpop [data-prepgo]")
        b.wait("[...document.querySelectorAll('#v-prep button')].some(e=>e.innerText.includes('Refresh research'))", 15)
        b.eval("[...document.querySelectorAll('#v-prep button')].find(e=>e.innerText.includes('Refresh research')).click()")
        b.wait("/Prep page saved: /.test(document.body.innerText)", 60)
        rel = b.eval("document.body.innerText.match(/Prep page saved: (projects\\/[^\\n]*?\\.html)/)[1]")
        f = self.vault / rel
        self.assertTrue(f.is_file(), f"the page is in the Agendas folder: {rel}")
        self.assertEqual(f.parent.name, "agendas")
        text = f.read_text(encoding="utf-8")
        outside = re.findall(r"<link\b[^>]*>|<script\b[^>]*\bsrc=|<img\b[^>]*\bsrc=\"(?!data:)|url\(\s*['\"]?(?!data:)|@import", text, re.I)
        self.assertEqual(outside, [], "still one file: nothing loaded from outside it")
        # Open it from the Agendas folder: the file itself, as Finder would open it in Chrome
        b.goto(f.as_uri())
        b.wait("document.querySelector('h1')", 10)

        def look(mode, w):
            return {"vars": self._vars(self.STATUS),
                    "body": b.eval("getComputedStyle(document.body).fontFamily.split(',')[0].replace(/\"/g,'')"),
                    "h1": b.eval("getComputedStyle(document.querySelector('h1')).fontFamily.split(',')[0].replace(/\"/g,'')"),
                    "installed": b.eval("['Source Sans 3','Schibsted Grotesk'].filter(f=>document.fonts.check('16px \"'+f+'\"'))"),
                    "overflow": measure.overflow_x(b)["ok"]}
        shots, seen = self._file_page_shots(11, "prep page (opened from the Agendas folder)", look)
        for (m, w), x in seen.items():
            self.assertEqual(x["vars"], dash[m], f"{m} at {w}px: the status colours are the dashboard's (creaite)")
            self.assertEqual((x["body"], x["h1"]), ("Source Sans 3", "Schibsted Grotesk"), "the dashboard's type stacks")
        sideways = [f"{m} {w}px" for (m, w), x in seen.items() if not x["overflow"]]
        first = seen[("light", 1400)]
        self.note(11, f"{shots} shots; {rel.rsplit('/', 1)[-1]}, {len(text) // 1024} KB, one file (no link, script src, url() "
                      f"or @import); status colours = the dashboard's in light and dark ({', '.join(f'{k} {v}' for k, v in dash['light'].items())} "
                      f"/ {', '.join(dash['dark'].values())}); fonts Source Sans 3 / Schibsted Grotesk, installed here: "
                      f"{', '.join(first['installed']) or 'neither (system font shown)'}"
                      + (f"; scrolls sideways at {', '.join(sideways)}" if sideways else "; no sideways scroll at 320 px"))

    def test_c18_offline_page(self):
        """18. Stop the server and reload → the offline page uses creaite's fonts and colours, light and dark, with a 32 px
        button. (Needs own_vault: it stops the server.)"""
        import time
        b, cls = self.b, type(self)
        dash = self._dashboard_vars(self.TOKENS)
        # the service worker (BL-86) must hold the offline page before the server stops
        deadline = time.time() + 20
        while not b.eval("navigator.serviceWorker.getRegistration().then(r=>!!(r&&r.active)).then(a=>a&&caches.match('/offline').then(x=>!!x))"):
            self.assertLess(time.time(), deadline, "the service worker never held the offline page")
            b.pump(0.3)
        cls._hc.stop_server(cls.proc)

        def restart():
            cls.proc, cls.base = cls._hc.start_server(cls.vault)
        self.addCleanup(restart)                       # the next checks need it
        b.eval("location.reload()", wait=False)       # ⌘R (Page.reload's ignoreCache would bypass the service worker)
        b.pump(0.5)
        b.wait("document.readyState==='complete' && !!document.querySelector('h1')", 20)
        self.assertEqual(b.eval("document.querySelector('h1').innerText"), "The live server isn't running")

        def look(mode, w):
            return {"vars": self._vars(self.TOKENS),
                    "body": b.eval("getComputedStyle(document.body).fontFamily.split(',')[0].replace(/\"/g,'')"),
                    "h1": b.eval("getComputedStyle(document.querySelector('h1')).fontFamily.split(',')[0].replace(/\"/g,'')"),
                    "button": measure.boxes(b, "button"), "overflow": measure.overflow_x(b)["ok"],
                    "contrast": min(r["ratio"] for r in measure.contrast(b, "h1, p, button, code"))}
        shots, seen = self._file_page_shots(18, "offline page (server stopped)", look)
        diffs = []
        for (m, w), x in seen.items():
            self.assertEqual([bx["h"] for bx in x["button"]], [32.0], f"{m} {w}px: one 32 px button")
            self.assertEqual((x["body"], x["h1"]), ("Source Sans 3", "Schibsted Grotesk"), "creaite's type stacks")
            self.assertTrue(x["overflow"], f"{m} {w}px: no sideways scroll")
            for k in ("bg", "ink", "accent"):
                self.assertEqual(x["vars"][k], dash[m][k], f"{m}: --{k} is creaite's")
            diffs += [f"{m} --{k} {x['vars'][k]} (dashboard {dash[m][k]})" for k in self.TOKENS if x["vars"][k] != dash[m][k] and w == 1400]
        worst = min(x["contrast"] for x in seen.values())
        self.note(18, f"{shots} shots (served by the service worker with the server stopped); button 32px; Source Sans 3 / "
                      f"Schibsted Grotesk; bg, ink and accent = the creaite theme's, light and dark"
                      + (f"; differs: {', '.join(diffs)}" if diffs else "; surface, muted and line too")
                      + f"; lowest text contrast {worst}:1; no sideways scroll at 320 px")

    def test_c20_audits_snapshots(self):
        """20. `python3 dev/tools/token_audit.py` and `dev/tools/ui_audit.py` from the repository → no P1 in shipped files; one
        variant of each control. Look through the screenshot sheet's check 20 (every screen in every theme, light and dark, at
        1400 px, and in the default theme at 320 px) → you agree how each screen looks."""
        import os
        import subprocess
        repo = Path(__file__).resolve().parents[3]
        r = subprocess.run([sys.executable, "dev/tools/token_audit.py", "--json"], cwd=repo, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr[-500:])
        found = json.loads(r.stdout)["findings"]
        p1 = [f for f in found if f["sev"] == "P1"]
        shipped = [f"{f['file']}:{f['line']} {f['msg'][:80]}" for f in p1 if not str(f["file"]).startswith("dev/")]
        out = Path(os.environ.get("CREAITE_HC_DIR") or ".") / "ui-audit"
        u = subprocess.run([sys.executable, "dev/tools/ui_audit.py", "--out", str(out), "--themes", "creaite", "--modes", "light",
                            "--widths", "1400x1000"], cwd=repo, capture_output=True, text=True, timeout=600)
        self.assertEqual(u.returncode, 0, u.stderr[-500:])
        (out / "summary.md").write_text(u.stdout, encoding="utf-8")
        kinds = re.findall(r"^- \*\*(\w+)\*\*: (\d+) classes, \d+ rendered styles; (\d+) classes drawn more than one way", u.stdout, re.M)
        self.assertTrue(kinds, "ui_audit's control summary")
        more = [f"{k} {n}" for k, _, n in kinds if int(n)]
        # Drift shows in the other themes too (Jarvis, #81): every theme in light and dark at 1400 px, and the default
        # theme (creaite) at 320 px
        shots = sum(self.sheet(20, s, widths=(1400,)) + self.sheet(20, s, palettes=["creaite"], widths=(320,))
                    for s in measure_screens())
        self.note(20, f"{shots} shots of every screen (every theme at 1400 px, creaite at 320 px) on the sheet, in place of dev/reviews/bl325-before-after/; "
                      f"token audit: {len(p1)} P1, {len(shipped)} in shipped files"
                      + (f" ({'; '.join(shipped[:3])})" if shipped else f" (all in dev/: {', '.join(sorted({f['file'] for f in p1}))})")
                      + f"; ui_audit (creaite, light, 1400 px): classes drawn more than one way: {', '.join(more) or 'none'}"
                      + f" (state or drift: judge from {out / 'summary.md'})")
        self.assertEqual(shipped, [], "P1 findings in shipped files")

    def test_c51_dark_forced_320_help(self):
        """51. Dark mode, forced colours and 320 px: the Archived chip and Move back, Health's Archiving section, the alert card
        and quiet line, → readable, with no sideways scroll. Help says what Archiving and Move back are."""
        b, day = self.b, (self.now or "")[:10]
        # The state: the old reports archived (Health's Archive them, then Approve on the card, as their buttons do) and two
        # conversations recorded (check 42's and 43's, through sweep.py vip record)
        r = b.eval("api('/api/health/fix/archive_reports',{}).then(r=>r)")
        self.assertTrue(r and r.get("card"), f"Archive them: {r}")
        r = b.eval("api('/api/edit/pending',{}).then(p=>api('/api/edit/approve',{card:p.card.card}))")
        self.assertTrue(r and r.get("ok"), f"Approve: {r}")
        found = self.vault / "system/staging/hc-found.json"
        conv = {"kind": "teams", "from": "Rashid Al Suwaidi <rashid@northgate.example>", "sensitivity": "normal", "attachments": [],
                "people": ["Rashid Al Suwaidi <rashid@northgate.example>", "Lena Fischer"]}
        found.write_text(json.dumps([
            dict(conv, conversation="19:hc-falcon@thread.v2", title="Falcon go-live", last=f"{day} 08:40", link="https://teams.microsoft.com/l/chat/hc",
                 summary="Northgate will take the platform from production to live; go-live work falls under the existing contract.",
                 items=[{"type": "action", "text": "Take the platform from production to live", "owner": "Rashid Al Suwaidi"},
                        {"type": "decision", "text": "Go-live work falls under the existing contract"}]),
            dict(conv, conversation="19:hc-chat@thread.v2", title="Group chat", last=f"{day} 08:50", link="https://teams.microsoft.com/l/chat/hc2",
                 summary="Greetings only.", items=[])]), encoding="utf-8")
        try:
            code, out = self.run_in_vault("sweep.py", "vip", "record", "system/staging/hc-found.json", "--found", "sweep")
        finally:
            found.unlink()
        self.assertEqual(code, 0, out)
        b.reload("typeof go==='function' && LIVE")

        def archived(bb):
            bb.eval("document.querySelector('#fquick [data-q=archived]').click()")
            bb.wait("document.querySelector('#filesTbl [data-moveback]')", 10)
            bb.eval("document.querySelector('#filesTbl').scrollIntoView({block:'start'})")

        def health(bb):
            bb.wait("document.querySelector('#healthArchiving')", 20)
            bb.eval("document.querySelector('#healthArchiving').scrollIntoView({block:'center'})")

        def alerts(bb):
            bb.wait("document.querySelector('#tdList .td-message') && document.querySelector('#tdList .td-quiet')", 10)
            bb.pump(0.3)                                   # Today settles (the day band redraws) before it is scrolled
            bb.eval("""(()=>{ const e=document.querySelector('#tdList .td-message, #tdList .td-quiet');   // the first of the two
              e.scrollIntoView({block:'start'}); scrollBy(0, -70); return true; })()""")

        archiving_li = "[...document.querySelectorAll('#v-help li')].find(e=>e.offsetParent&&/^Archiving \\(Settings/.test(e.innerText))"

        def help_(bb):
            bb.eval("go('help','reference')")             # Help › Reference › Settings
            bb.wait(archiving_li, 10)
            bb.eval(archiving_li + ".scrollIntoView({block:'start'})")

        surfaces = [("files", "Files › Archived", archived, "#filesTbl .tag, #filesTbl [data-moveback], #fquick [data-q=archived]"),
                    ("settings-health", "Settings › Health › Archiving", health, "#healthArchiving li"),
                    ("today", "Today › the alert card and quiet line", alerts, "#tdList .td-message, #tdList .td-message *, #tdList .td-quiet, #tdList .td-quiet *"),
                    ("help", "Help › Archiving and Move back", help_, None)]
        variants = [("dark", False, 1400), ("dark", False, 320), ("forced dark", True, 320), ("forced light", True, 320)]
        sideways, low, shots = [], [], 0
        try:
            for w_mode, forced, w in variants:
                measure.width(b, w, 1000 if w > 600 else 800)
                measure.media(b, dark="dark" in w_mode, forced=forced)
                measure.theme(b, "creaite", "system" if forced else "dark")
                for screen, label, prep, sel in surfaces:
                    self.screen(screen, settle=0.3)
                    prep(b)
                    b.pump(0.2)
                    if not measure.overflow_x(b)["ok"]:
                        sideways.append(f"{label} {w_mode} {w}px")
                    if sel and not forced:
                        for x in measure.contrast(b, sel):
                            if x["text"] and x["ratio"] < (3 if measure.large(x) else 4.5):
                                low.append(f"{label} {w}px {x['sig']} '{x['text'][:20]}' {x['ratio']}:1")
                    shots += self._record(51, label, "creaite", w_mode, w)
        finally:
            measure.media(b)
            measure.width(b, self.width, self.height)
            b.eval("applyTheme()")
        self.screen("help")
        b.eval("go('help','reference')")
        para = b.wait(archiving_li + ".innerText", 10)
        self.assertIn("Move back", para, "Help says what Move back is")
        self.assertIn("99 Archive", para, "Help says what archiving does")
        self.note(51, f"{shots} shots (Files › Archived, Health › Archiving, Today's alert card and quiet line, Help; dark at 1400 "
                      f"and 320 px, forced colours at 320 px); "
                      + (f"sideways scroll: {'; '.join(sideways)}" if sideways else "no sideways scroll in any")
                      + (f"; below AA in dark: {'; '.join(sorted(set(low))[:4])}" if low else "; text contrast AA in dark")
                      + "; Help's Archiving paragraph explains Archive them and Move back")
        self.assertEqual(sideways, [], "no sideways scroll")
        self.assertEqual(low, [], "readable in dark mode")


class Bl333And10(HandcheckCase):
    """BL-333 (21, 22) and BL-10 archiving old items (23 to 29), with check 30's Health line. Own vault: archiving changes data.

    The checks run in order and build on each other (23 closes the two items, 24 archives them, 27 edits one, 28 undoes the
    archive); each makes what it needs itself when it runs alone (--only). The demo's RAID IDs are CODE-NNN, so the check's
    "ORX-R-001" is ORX-005 here (Orbit's first risk, "Late UAT data slips sign-off")."""
    own_vault = True
    ACTION, RAID = "FAL-A-004", "ORX-005"
    WORDS = "security review ingestion"                 # FAL-A-004's words: "Complete security review of ingestion pipeline"

    # ── helpers (this class's own) ──

    @staticmethod
    def hc():
        import hcbase
        return hcbase

    def later(self):
        """Today plus 7 months, 09:00: the check's CREAITE_NOW for archive.py."""
        return self.hc().months_on(self.now, 7)[:10] + " 09:00"

    def row(self, table, item):
        return (self.hc().db_rows(self.vault, f"SELECT * FROM {table} WHERE id = ?", item) or [{}])[0]

    def until(self, test, what, timeout=20):
        """Poll `test()` (Python) while the page keeps running; fail with `what` if it never holds."""
        import time
        end = time.time() + timeout
        while time.time() < end:
            if test():
                return
            self.b.pump(0.2)
        self.fail(f"timed out waiting for {what}")

    def reopen(self):
        """The page loaded again (after a change made outside it), the clock still pinned."""
        self.b.reload("typeof go==='function' && LIVE")
        self.b.pump(0.5)

    def daily_slot_taken(self):
        """The live server's daily job runs archive.py daily a minute after start-up, once a day. Wait for it (up to 100 s), so it
        can't run after the checks' own archive.py run (whose day is seven months on) and overwrite Health's line."""
        import time
        state = self.vault / "system/staging/archive-state.json"
        end = time.time() + 100
        while time.time() < end:
            try:
                if (json.loads(state.read_text()).get("items") or {}).get("day"):
                    return "the server's daily run had taken today's slot"
            except (OSError, ValueError):
                pass
            time.sleep(1)
        self.run_in_vault("archive.py", "daily")
        return "today's slot taken with archive.py daily (the server's hadn't run in 100 s)"

    def set_status(self, k, item, status):
        """Work › the item › its status, then Apply: the dashboard's own peek (pkSetStatus, as the status menu does) and the
        peek's Apply button. Waits until the record has it."""
        b = self.b
        self.screen("work")
        b.eval(f"openRecord({json.dumps(k)},{json.dumps(item)})")
        b.wait("document.getElementById('panel').classList.contains('on')")
        b.eval(f"pkSetStatus({json.dumps(k)},{json.dumps(item)},{json.dumps(status)}).then(()=>true)")
        b.wait("!document.getElementById('pkStage').hidden")
        b.click("#pkApply")
        self.until(lambda: self.row(k, item).get("status") == status, f"{item} {status} in the record")
        b.pump(0.5)

    def close_both(self):
        """Close FAL-A-004 and cancel ORX-005 in Work (once)."""
        if self.row("actions", self.ACTION).get("status") != "Closed":
            self.set_status("actions", self.ACTION, "Closed")
        if self.row("raid", self.RAID).get("status") != "Cancelled":
            self.set_status("raid", self.RAID, "Cancelled")

    def dry_run(self):
        code, out = self.run_in_vault("archive.py", "items", "--dry-run", env={"CREAITE_NOW": self.later()})
        self.assertEqual(code, 0, out[-400:])
        return re.findall(r"^(\S+) \((\w+)\)$", out, re.M), out

    def archive_apply(self):
        """The apply archive.py made (its proposal ends -archive.json), or None."""
        for a in self.hc().db_rows(self.vault, "SELECT apply_id, proposals, undone_at FROM applies ORDER BY apply_id DESC"):
            if "-archive.json" in (a["proposals"] or ""):
                return a
        return None

    def ensure_archived(self):
        """Checks 23 and 24's state (closed, then archived seven months on), made here when this check runs on its own."""
        if self.archive_apply():
            return
        self.daily_slot_taken()
        self.close_both()
        code, out = self.run_in_vault("archive.py", "items", env={"CREAITE_NOW": self.later()})
        self.assertEqual(code, 0, out[-400:])

    def search(self, words):
        """Files' search bar: type the words; returns the results' text, or "" when nothing came back."""
        b = self.b
        self.screen("files")
        b.click("#vsInput")
        b.type(words)
        b.wait("document.querySelector('#vsResults .vsr')||/Nothing found/.test(document.getElementById('vsResults').innerText)", 15)
        return b.eval("document.getElementById('vsResults').innerText")

    def show_archived(self, on):
        """Settings: the show-archived switch (data-k showArchived), clicked as Alan would; waits until the page has reloaded
        its data. Returns the switch row's label and its section."""
        b = self.b
        self.screen("settings-work")                           # v2.6 (#246): Work and reports › Opening views
        sel = "input.switch[data-k=showArchived]"
        b.wait(f"document.querySelector('{sel}')")
        where = b.eval(f"""(()=>{{ const e=document.querySelector('{sel}'), r=e.closest('.srow'), s=e.closest('[data-sec]');
          return {{label:(r.querySelector('span[id]')||r).innerText.split('\\n')[0].trim(), help:(r.querySelector('small')||{{}}).innerText||'',
                  sec:s&&s.dataset.sec, heading:s&&(s.querySelector('h2,h3')||{{}}).innerText, on:e.checked}}; }})()""")
        if where["on"] != on:
            b.click(sel)
            b.wait(f"S.showArchived==={json.dumps(on)}")
            self.until(lambda: json.loads((self.vault / "system/config/settings.json").read_text())["dashboard"].get("show_archived") == on,
                       "show_archived saved")
            b.pump(1.5)                                        # reloadData()
        return where

    def bottom(self, label, box, wheel=True):
        """BL-333 on the screen in view: the wheel turned to the end over `box`; the window never scrolls (Console:
        scrollHeight === innerHeight), the box stops at its last content, and the rail stays put. Returns problems."""
        b, problems = self.b, []
        rail0 = measure.rect(b, ".rail")
        w = measure.wheel_to_bottom(b, box) if wheel else None
        end = measure.scroll_end(b, box)
        page = measure.overflow_y(b)
        rail1 = measure.rect(b, ".rail")
        if end is None:
            return [f"{label}: no {box}"]
        if not page["ok"]:
            problems.append(f"{label}: scrollHeight {page['sh']} !== innerHeight {page['ih']}")
        if w and w["window_top"]:
            problems.append(f"{label}: the window scrolled {w['window_top']} px")
        if end["sh"] > end["ch"] + 1:
            if w and end["top"] < end["sh"] - end["ch"] - 1:
                problems.append(f"{label}: the wheel stopped at {end['top']} of {end['sh'] - end['ch']}")
            if end["sh"] > end["end"] + 1:
                problems.append(f"{label}: {box} scrolls {end['sh'] - end['end']} px past its last content ({end['last']})")
        if rail0 != rail1:
            problems.append(f"{label}: the rail moved ({rail0} → {rail1})")
        self.seen.append(f"{label} {page['sh']}={page['ih']}"
                         + (f", {box} {end['top']}/{end['sh'] - end['ch']} px ends at {end['last']}" if end["sh"] > end["ch"] + 1 else ""))
        return problems

    # ── BL-333 ──

    def test_c21_today_stops_at_bottom(self):
        """21. Today at 1400 px, scroll to the bottom with the wheel → it stops at the last content; the rail doesn't scroll
        away. In the Console, `document.scrollingElement.scrollHeight === innerHeight` → `true`."""
        self.seen = []
        measure.width(self.b, 1400, 1000)
        self.screen("today", settle=1)
        long_enough = measure.scroll_end(self.b, "#v-today")
        problems = self.bottom("Today 1400", "#v-today")
        self.note(21, "; ".join(self.seen) + f" (wheel, real events; Today {long_enough['sh']} px tall in a {long_enough['ch']} px box)")
        self.assertGreater(long_enough["sh"], long_enough["ch"], "Today is long enough to scroll")
        self.assertEqual(problems, [], "; ".join(problems))

    def test_c22_intake_prep(self):
        """22. The same on Intake (at 1400 and 320 px), the Prep popup over Today, and Meetings › Prep → `true` on each, and
        the rail stays put."""
        b, problems = self.b, []
        self.seen = []
        try:
            for w in (1400, 320):
                measure.width(b, w, 1000 if w > 600 else 800)
                self.screen("intake-review", settle=1)
                problems += self.bottom(f"Intake {w}", "#v-intake-review")
            measure.width(b, 1400, 1000)
            # The Prep popup over Today is the Prep peek since 2.2 (#111 B); Meetings › Prep is the prep page (#prep=, BL-286 D),
            # the meeting hub's page having gone with BL-339
            self.screen("today", settle=1)
            open_prep_peek(b)
            b.pump(1)
            for box in ("#dayMeets .dmpop", "#v-today"):
                problems += self.bottom(f"Prep peek ({box})", box, wheel=box != "#v-today")
            b.click("#dayMeets .dmpop [data-prepgo]")
            b.wait("location.hash.startsWith('#prep=') && !document.getElementById('v-prep').hidden && /Steering committee/.test(document.getElementById('v-prep').textContent)", 15)
            b.pump(1)
            problems += self.bottom("Meetings › Prep", "#v-prep")
        finally:
            measure.width(b, self.width, self.height)
        self.note(22, "; ".join(self.seen))
        self.assertEqual(problems, [], "; ".join(problems))

    # ── BL-10 ──

    def test_c23_due_items_listed(self):
        """23. Make an old closed item: close FAL-A-004 and cancel ORX-005; `archive.py items --dry-run` 7 months on → both
        listed, with the demo's own item closed today (MER-A-003). An open action, any decision and any milestone are not."""
        slot = self.daily_slot_taken()
        self.close_both()
        listed, out = self.dry_run()
        ids = {i for i, _ in listed}
        self.assertIn(self.ACTION, ids, out)
        self.assertIn(self.RAID, ids, out)
        self.assertFalse({t for _, t in listed} & {"decisions", "milestones"}, out)
        open_ids = {r["id"] for r in self.hc().db_rows(self.vault, "SELECT id FROM actions WHERE status IN ('Open', 'Delayed')")}
        self.assertTrue(open_ids)
        self.assertFalse(ids & open_ids, "an open action is listed")
        others = sorted(ids - {self.ACTION, self.RAID})
        self.note(23, f"closed and cancelled in Work (status, then Apply); CREAITE_NOW {self.later()}: {len(ids)} listed "
                      f"({', '.join(sorted(ids))})" + (f" — {', '.join(others)} is the demo's own item closed today" if others else "")
                      + f"; no open action ({len(open_ids)}), decision or milestone; ORX-R-001 is ORX-005 in the demo; {slot}")

    def test_c24_archived_through_apply(self):
        """24. Run it again without `--dry-run` → "Archived n items", n the dry run's count. Activity shows one apply, its lines
        by "Archived for age"; Review gets nothing."""
        b = self.b
        self.daily_slot_taken()
        self.close_both()
        listed, _ = self.dry_run()
        self.assertIsNone(self.archive_apply(), "not archived yet")
        self.assertIn("FAL-A-004", self.hc().xlsx_text(self.vault / "tracker-view.xlsx"), "in the Excel export before")
        self.screen("review")
        rev0, pend0 = b.eval("REV.length"), self.hc().pending_proposals(self.vault)
        code, out = self.run_in_vault("archive.py", "items", env={"CREAITE_NOW": self.later()})
        self.assertEqual(code, 0, out[-400:])
        m = re.search(r"^Archived (\d+) items?\b.*$", out, re.M)
        self.assertTrue(m, out[-300:])
        n = int(m.group(1))
        self.assertEqual(n, len(listed), "as many as the dry run listed")
        for t, i in (("actions", self.ACTION), ("raid", self.RAID)):
            self.assertEqual(self.row(t, i).get("archived"), 1, i)
        a = self.archive_apply()
        logged = self.hc().db_rows(self.vault, "SELECT tbl, item_id, field FROM change_log WHERE apply_id = ?", a["apply_id"])
        self.assertEqual({r["field"] for r in logged}, {"archived"})
        self.assertEqual(len(logged), n, "one apply holds them all")
        self.assertEqual(self.hc().pending_proposals(self.vault), pend0, "nothing new waiting for Review")
        self.reopen()
        self.screen("review")
        rev1 = b.eval("REV.length")
        self.assertEqual(rev1, rev0, "Review gets nothing")
        self.screen("activity", settle=1)
        rows = b.eval("""[...document.querySelectorAll('#actTbl tr')].filter(r=>/archived: 0 → 1/.test(r.innerText)).map(r=>{
          const c=r.querySelectorAll('td'); return {what:c[2].innerText.trim(), by:c[3].innerText.trim()}; })""")
        self.assertEqual(len(rows), n, f"Activity lists the {n} archived")
        bys = sorted({r["by"] for r in rows})
        prop = json.loads(a["proposals"])[0].split("/")[-1]
        self.note(24, f"\"{m.group(0)}\" ({n}: FAL-A-004, ORX-005 and the demo's MER-A-003, closed today too, so not the check's 2); "
                      f"one apply ({a['apply_id']}, {prop}), {len(logged)} archived "
                      f"flags; Review {rev0} → {rev1}, no new proposal; Activity's By column: {', '.join(bys)}")
        self.assertEqual(bys, ["Archived for age"],
                         f"Activity names the source as \"{', '.join(bys)}\", not \"Archived for age\" (build_dashboard's BY for "
                         f"archive.py's proposal, whose change_log.via is its file name; without it, \"Approved in review\")")

    def test_c25_gone_search_health(self):
        """25. Work, Today and the Excel export → those items are gone. Search for FAL-A-004's words → found, marked Archived.
        Settings › Health › Archiving → "Archived n items on DD-MM-YYYY", the same n and the run's date."""
        b = self.b
        self.ensure_archived()
        self.reopen()
        self.screen("work")
        work = b.eval(f"[A.some(a=>a.id==={json.dumps(self.ACTION)}), R.some(a=>a.id==={json.dumps(self.RAID)}), "
                      f"document.getElementById('v-work').innerText.includes({json.dumps(self.ACTION)})]")
        self.assertEqual(work, [False, False, False], "gone from Work")
        self.screen("today", settle=1)
        today = b.eval("document.getElementById('v-today').innerText")
        for x in (self.ACTION, self.RAID, "Complete security review of ingestion pipeline", "Late UAT data slips sign-off"):
            self.assertNotIn(x, today, "gone from Today")
        xl = self.hc().xlsx_text(self.vault / "tracker-view.xlsx")
        self.assertNotIn(self.ACTION, xl, "gone from the Excel export")
        self.assertNotIn(self.RAID, xl, "gone from the Excel export")
        self.assertIn("FAL-A-001", xl, "the export itself is there")
        found = self.search(self.WORDS)
        self.assertIn(self.ACTION, found)
        hit = [ln for ln in found.splitlines() if self.ACTION in ln]
        self.assertTrue(hit and "Archived" in hit[0], f"marked Archived: {hit}")
        self.screen("settings-health", settle=1)
        health = b.eval("document.getElementById('v-settings').innerText")
        line = re.search(r"Archived (\d+) items? on (\d\d-\d\d-\d{4})[^\n]*", health)
        st = json.loads((self.vault / "system/staging/archive-state.json").read_text())["items"]
        self.assertTrue(line, "Health's archiving line")
        self.assertEqual((int(line.group(1)), line.group(2)), (st["archived"], self.hc().shown(self.later())))
        self.note(25, f"not in Work, Today or tracker-view.xlsx; search \"{self.WORDS}\": {hit[0].strip()}; Health: \"{line.group(0).strip()}\" "
                      f"({st['archived']}, not 2: the demo's MER-A-003 too; the date is the run's, seven months on)")

    def test_c26_show_archived(self):
        """26. Turn on "Show archived projects" (Settings › Work and reports › Opening views since v2.6, #246; its help mentions items
        archived for their age) → both are back in Work (Closed and Cancelled shown), each row tagged Archived. Turn it off."""
        b, problems = self.b, []
        self.ensure_archived()
        self.reopen()
        try:
            where = self.show_archived(True)
            back = b.eval(f"[A.find(a=>a.id==={json.dumps(self.ACTION)})||null, R.find(a=>a.id==={json.dumps(self.RAID)})||null]")
            self.assertTrue(all(back), "both back in the page's data")
            self.screen("work")
            b.click("#stBtn")
            b.eval("""(()=>{ for(const v of ['Closed','Cancelled']){ const i=[...document.querySelectorAll('#stMenu input[type=checkbox]')].find(x=>x.value===v);
              if(i&&!i.checked){ i.checked=true; i.dispatchEvent(new Event('change',{bubbles:true})); } } return true; })()""")
            b.key("Escape")
            b.pump(0.5)
            row = b.eval(f"(document.querySelector('#workTbl tr[data-row={json.dumps(self.ACTION)}]')||{{}}).innerText||''")
            self.assertIn("Complete security review", row, "FAL-A-004 is back in Work (with Closed shown)")
            marked = {i: bool(x.get("ar") or x.get("archived")) for i, x in zip((self.ACTION, self.RAID), back)}   # the page's flag is "ar"
            if "Archived" not in row:
                problems.append(f"FAL-A-004's Work row isn't marked Archived (\"{' '.join(row.split())[:90]}\")")
            if not all(marked.values()):
                problems.append(f"the page's records carry no archived flag ({', '.join(k for k, v in marked.items() if not v)}), "
                                "so nothing can mark them")
            label = "Show archived projects"
            if where["label"] != label or where["sec"] != "views" or "opening views" not in (where["heading"] or "").lower():
                problems.append(f"the switch is \"{where['label']}\" in Settings › {where['heading']} ({where['sec']}), not \"{label}\" "
                                f"in Work and reports › Opening views")
            if "archived for their age" not in where["help"]:
                problems.append(f"its help doesn't mention items archived for their age: \"{where['help'][:100]}\"")
        finally:
            self.show_archived(False)
        gone = b.eval(f"A.some(a=>a.id==={json.dumps(self.ACTION)})||R.some(a=>a.id==={json.dumps(self.RAID)})")
        self.assertFalse(gone, "gone again once it is off")
        self.note(26, f"\"{where['label']}\" in Settings › {where['heading']}; on: both back in Work (FAL-A-004's row with Closed shown); off: gone again" + (f"; {'; '.join(problems)}" if problems else ""))
        self.assertEqual(problems, [], "; ".join(problems))

    def test_c27_edit_unarchives(self):
        """27. With the switch off, search for FAL-A-004 and open it → its panel opens. Change its priority → it is live again
        (back in Work). Activity shows the un-archive in its change log."""
        b, problems = self.b, []
        self.ensure_archived()
        self.reopen()
        if self.row("actions", self.ACTION).get("archived") != 1:
            self.skipTest("FAL-A-004 isn't archived (already edited)")
        self.assertIn(self.ACTION, self.search(self.WORDS))
        b.click("#vsResults .vsr")
        b.pump(1)
        opened = b.eval("document.getElementById('panel').classList.contains('on')")
        if not opened:
            said = b.eval("(document.getElementById('snackT')||{}).textContent||''")
            problems.append(f"opening it from search is refused: \"{said}\" (Falcon's project isn't archived: the item was archived "
                            "for its age, ask.js openFound treats every archived item as an archived project's); opened with "
                            "Show archived on instead")
            self.show_archived(True)
            self.search(self.WORDS)
            b.click("#vsResults .vsr")
            b.wait("document.getElementById('panel').classList.contains('on')")
        pr = self.row("actions", self.ACTION).get("priority")
        new = "High" if pr != "High" else "Low"
        b.eval(f"pkCommit('actions',{json.dumps(self.ACTION)},{{pr:{json.dumps(new)}}},'Priority',{json.dumps(pr)},{json.dumps(new)}).then(()=>true)")
        b.wait("!document.getElementById('pkStage').hidden")
        b.click("#pkApply")
        self.until(lambda: self.row("actions", self.ACTION).get("priority") == new, "the priority in the record")
        if not opened:
            self.show_archived(False)
        x = self.row("actions", self.ACTION)
        self.assertEqual(x.get("archived"), 0, "live again")
        self.reopen()
        self.assertTrue(b.eval(f"A.some(a=>a.id==={json.dumps(self.ACTION)})"), "back in Work")
        self.screen("activity", settle=1)
        un = b.eval(f"""[...document.querySelectorAll('#actTbl tr')].map(r=>r.innerText.replace(/\\s+/g,' ').trim())
          .filter(t=>t.includes({json.dumps(self.ACTION)})&&/archived: 1 → 0/.test(t))""")
        self.assertTrue(un, "Activity shows the un-archive")
        self.note(27, f"priority {pr} → {new} in the peek, Apply: archived 1 → 0, back in Work; Activity: \"{un[0][:90]}\""
                      + (f"; {problems[0]}" if problems else ""))
        self.assertEqual(problems, [], "; ".join(problems))

    def test_c28_undo_nothing_in_review(self):
        """28. Undo the archive apply with its own Undo in Activity → ORX-005 is back, and nothing appears in Review. Ticking the
        archive's lines instead (Undo selected) is refused: "archived for its age: use Undo on the archive apply, …"."""
        b = self.b
        self.ensure_archived()
        a = self.archive_apply()
        if a["undone_at"] or self.row("raid", self.RAID).get("archived") != 1:
            self.skipTest("the archive apply is already undone")
        latest = lambda: self.hc().db_rows(self.vault, "SELECT max(apply_id) AS n FROM applies WHERE undone_at IS NULL")[0]["n"]
        self.reopen()
        self.screen("review")
        rev0, pend0 = b.eval("REV.length"), self.hc().pending_proposals(self.vault)
        steps, refused = [], ""
        if latest() != a["apply_id"]:
            # Activity's Undo is on the latest apply only; older changes are ticked and undone as one new apply (BL-164)
            self.screen("activity", settle=1)
            b.eval("""(()=>{ [...document.querySelectorAll('#actTbl tr')].filter(r=>/archived: 0 → 1/.test(r.innerText)&&!/since undone/.test(r.innerText))
              .forEach(r=>r.querySelector('input[type=checkbox]').click()); return true; })()""")
            b.click("#actUndoSel")
            b.wait("document.getElementById('actDlg')&&document.getElementById('actDlg').open", 15)
            refused = b.eval("document.getElementById('actDlgBody').innerText.replace(/\\s+/g,' ').trim()")
            said = refused
            if b.eval("!!document.getElementById('actDlgGo')"):
                b.click("#actDlgGo")
                b.pump(2)
                said += " " + b.eval("document.body.innerText")
            else:
                b.click("#actDlgCancel")
            steps.append(f"ticking the archive's rows in Activity: \"{refused[:160]}\"")
            self.assertIn("archived for its age", said, "Undo selected on the archive's lines says how to bring the item back")
        for _ in range(4):                                     # then Activity › Undo on the latest apply, until the archive's is undone
            if self.row("raid", self.RAID).get("archived") == 0:
                break
            n = latest()
            self.reopen()
            if n == a["apply_id"]:                             # Review as it is just before the archive's own undo (undoing
                self.screen("review")                          # check 27's edit first returns that edit to Review, as any undo)
                rev0, pend0 = b.eval("REV.length"), self.hc().pending_proposals(self.vault)
            self.screen("activity", settle=1)
            b.click(f"#actTbl [data-undoapply='{n}']")
            self.until(lambda n=n: n not in [r["apply_id"] for r in self.hc().db_rows(self.vault, "SELECT apply_id FROM applies WHERE undone_at IS NULL")],
                       f"apply {n} undone")
            steps.append(f"Activity › Undo on apply {n}" + (" (the archive's)" if n == a["apply_id"] else
                                                            " (check 27's edit, the latest: it goes back to Review, as an undone edit does)"))
        self.assertEqual(self.row("raid", self.RAID).get("archived"), 0, "ORX-005 back")
        b.pump(1)
        self.assertEqual(self.hc().pending_proposals(self.vault), pend0, "nothing new waiting for Review")
        self.reopen()
        self.assertTrue(b.eval(f"R.some(a=>a.id==={json.dumps(self.RAID)})"), "ORX-005 back in the page's data")
        self.screen("review")
        rev1 = b.eval("REV.length")
        self.assertEqual(rev1, rev0, "nothing appears in Review")
        self.note(28, "; then ".join(steps) + f"; ORX-005 archived 1 → 0, back in Work; Review {rev0} → {rev1}, no new proposal")

    def test_c29_settings_zero_turns_off(self):
        """29. Settings › Advanced › Archiving → `archive.after_months` for actions, RAID and promises (6) and
        `archive.reports_after_months` (12). Set RAID to 0 and repeat the dry run with a cancelled RAID item → not listed."""
        b = self.b
        self.close_both()
        self.assertEqual(self.row("raid", self.RAID).get("archived"), 0, "ORX-005: cancelled and not archived")
        labels = ["Archive closed actions after (months)", "Archive closed RAID items after (months)",
                  "Archive done promises after (months)", "Offer to archive reports and minutes after (months)"]
        find = "[...document.querySelectorAll('#v-settings .srow')].find(r=>r.innerText.startsWith(%s))"

        def archiving():                       # v2.6 (#246): Settings › Advanced › Archiving and backups, its own sub-tab
            b.eval("go('settings','arch')")
            b.wait("SSUB==='arch' && !!document.querySelector('#settingsBody .srow')", 15)
            b.pump(0.5)
        archiving()
        heading = b.eval(f"""(()=>{{ const r={find % json.dumps(labels[0])}; if(!r) return '';
          const hs=[...document.querySelectorAll('#v-settings h2,#v-settings h3')].filter(h=>h.compareDocumentPosition(r)&Node.DOCUMENT_POSITION_FOLLOWING);
          return hs.length?hs[hs.length-1].innerText.trim():''; }})()""")
        values = [b.eval(f"(({find % json.dumps(x)})||{{querySelector:()=>null}}).querySelector('input')?.value??null") for x in labels]
        self.assertEqual(values, ["6", "6", "6", "12"])
        listed, _ = self.dry_run()
        self.assertIn(self.RAID, {i for i, _ in listed}, "listed at 6 months")

        def set_raid(v):
            b.eval(f"""(()=>{{ const i=({find % json.dumps(labels[1])}).querySelector('input'); i.focus(); i.value={json.dumps(str(v))};
              i.dispatchEvent(new Event('input',{{bubbles:true}})); i.dispatchEvent(new Event('change',{{bubbles:true}})); i.blur(); return true; }})()""")
            self.until(lambda: json.loads((self.vault / "system/config/settings.json").read_text())["archive"]["after_months"]["raid"] == v,
                       f"archive.after_months.raid = {v} saved")
        try:
            set_raid(0)
            again, out = self.dry_run()
            self.assertNotIn(self.RAID, {i for i, _ in again}, out)
            self.assertFalse([i for i, t in again if t == "raid"], out)
        finally:
            archiving()
            set_raid(6)
        self.note(29, f"Settings › Advanced{(' › ' + heading) if heading else ''}: actions, RAID, promises 6, reports 12; "
                      f"RAID set to 0 in the page (saved to settings.json): the cancelled ORX-005 not listed "
                      f"({len(again)} listed: {', '.join(i for i, _ in again) or 'none'}); set back to 6")

    def test_c30_health_line_card(self):
        """30. Settings › Health → "Archive 4 reports and minutes older than 12 months", with **Archive them**. Press it → the
        change card lists "Move file … → …/99 Archive/…" for the FAL weekly report, client report and steering minutes, and the
        portfolio's minutes. Not the transcript, the ad hoc notes or ORX's recent report."""
        b = self.b
        self.screen("settings-health", settle=1)
        health = b.eval("document.getElementById('v-settings').innerText")
        self.assertIn("Archive 4 reports and minutes older than 12 months", health)
        b.wait("[...document.querySelectorAll('#v-settings button')].some(x=>x.innerText.trim()==='Archive them')")
        b.eval("[...document.querySelectorAll('#v-settings button')].find(x=>x.innerText.trim()==='Archive them').setAttribute('data-hc','arch')")
        b.click("button[data-hc=arch]")
        b.wait("document.querySelector('#chat .confirm.edcard .edlines li')", 20)
        lines = b.eval("[...document.querySelectorAll('#chat .confirm.edcard .edlines li')].map(l=>l.innerText.trim())")
        fal, port = "projects/FAL Falcon Data Platform/", "projects/_portfolio/"
        want = [f"Move file {fal}minutes/2025-09-02 FAL steering minutes.docx → {fal}99 Archive/minutes/2025-09-02 FAL steering minutes.docx",
                f"Move file {fal}reports/2025-08-29 Falcon Data Platform weekly report.docx → {fal}99 Archive/reports/2025-08-29 Falcon Data Platform weekly report.docx",
                f"Move file {fal}reports/2025-09-05 Falcon Data Platform client report.docx → {fal}99 Archive/reports/2025-09-05 Falcon Data Platform client report.docx",
                f"Move file {port}minutes/2025-09-10 Portfolio review minutes.docx → {port}99 Archive/minutes/2025-09-10 Portfolio review minutes.docx"]
        self.assertEqual(sorted(lines), sorted(want))
        text = " ".join(lines)
        for never in ("transcript", "data notes", "Orbit Customer App weekly report"):
            self.assertNotIn(never, text)
        b.click("#chat .confirm.edcard [data-ed=reject]")     # check 31 approves it in its own vault; this one leaves it as it was
        b.pump(1)
        self.assertFalse(list((self.vault / fal / "99 Archive").glob("*/*")), "nothing moved")
        self.note(30, "Health: \"Archive 4 reports and minutes older than 12 months\" with Archive them; the card: the FAL weekly "
                      "report, client report and steering minutes and the portfolio's minutes, each Move file … → …/99 Archive/…; "
                      "not the transcript, the notes or ORX's report; Rejected afterwards (31 approves in its own vault)")


class Bl03And331(HandcheckCase):
    """BL-03 archiving old reports and minutes (31 to 34) and BL-331 move back (35 to 41). Own vault.

    Driven in the page as Alan would: Settings › Health's **Archive them**, the change card's **Approve** in ask creaite, Files'
    Archived chip and **Move back**, Activity's Undo, Files' search box. Two stand-ins, both this class's own:
    - CREAITE_NO_LAUNCH on its server, so opening a file reports the path the server would open instead of starting Word;
    - a stand-in Claude that makes its tool calls the way Claude Code does: each one through the run's own PreToolUse guard
      hook (reach.py hook, from the --settings the server passes) first, refused when the hook exits 2. What is refused is
      the product's own guard and card, never the stand-in's.
    The FAL weekly report and the portfolio's minutes get one made-up word each (WORD, PWORD), so search can be checked."""
    own_vault = True
    FAL = "projects/FAL Falcon Data Platform"
    WEEKLY = f"{FAL}/reports/2025-08-29 Falcon Data Platform weekly report.docx"
    CLIENT = f"{FAL}/reports/2025-09-05 Falcon Data Platform client report.docx"
    STEER = f"{FAL}/minutes/2025-09-02 FAL steering minutes.docx"
    PORTF = "projects/_portfolio/minutes/2025-09-10 Portfolio review minutes.docx"
    DUE = (WEEKLY, CLIENT, STEER, PORTF)
    KEPT = (f"{FAL}/transcripts/2025-09-02 FAL steering transcript.docx", f"{FAL}/reports/2025-09-05 Falcon data notes.docx")
    WORD, PWORD = "kestrelquill", "ploverthistle"          # made-up words, one in each of two files
    FAKE = r'''#!/usr/bin/env python3
"""A stand-in Claude for BL-03/BL-331's hand checks: each tool call goes through the run's PreToolUse guard hook first, as
Claude Code runs it (the command in --settings, the call as JSON on standard input; exit 2 refuses). Every call is logged
beside this file (tool, input, exit, stderr). Nothing here decides what is refused."""
import json, os, subprocess, sys
args = sys.argv[1:]
p = args[args.index("--") + 1]
out = lambda o: print(json.dumps(o), flush=True)
if p.startswith("creaite VIP check"):
    out({"type": "result", "result": "[]", "session_id": "sess-vip"})
    sys.exit(0)
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fake_claude_guarded.jsonl")
hook = None
if "--settings" in args:
    try:
        hook = json.loads(args[args.index("--settings") + 1])["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    except (ValueError, KeyError, IndexError):
        hook = None
out({"type": "system", "subtype": "init", "session_id": "sess-hc-guard"})
denied, n = [], [0]
FAL = "projects/FAL Falcon Data Platform"

def call(name, inp, do=None):
    n[0] += 1
    cid = f"t{n[0]}"
    out({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": cid, "name": name, "input": inp}]}})
    if hook:
        r = subprocess.run(["/bin/sh", "-c", hook], input=json.dumps({"hook_event_name": "PreToolUse", "tool_name": name,
                           "tool_input": inp}), capture_output=True, text=True)
        code, err = r.returncode, r.stderr
    else:
        code, err = 2, "no guard hook was given"
    with open(LOG, "a") as f:
        f.write(json.dumps({"tool": name, "input": inp, "exit": code, "stderr": err[-400:]}) + "\n")
    if code == 2:
        denied.append({"tool_name": name, "tool_use_id": cid, "tool_input": inp})
        out({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": cid, "is_error": True, "content": err.strip()}]}})
        return False, err.strip()
    res = do() if do else "ok"
    out({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": cid, "is_error": False, "content": res}]}})
    return True, res

low = p.lower()
if "archived" in low and "read" in low:
    ok, why = call("Read", {"file_path": os.path.join(os.getcwd(), FAL, "99 Archive/reports/2025-08-29 Falcon Data Platform weekly report.docx")})
    text = "Here it is." if ok else f"I can't read it: {why}"
elif "archived" in low and "move" in low:
    a, o = f"{FAL}/99 Archive/minutes/2025-09-02 FAL steering minutes.docx", f"{FAL}/minutes/2025-09-02 FAL steering minutes.docx"
    call("Bash", {"command": f'system/scripts/run filechange.py move "{a}" "{o}"'})
    spec = {"source_run": "cx-edit", "items": [], "file_changes": {"title": "Move back 2025-09-02 FAL steering minutes.docx",
            "project": "FAL", "archive": "reports_back", "file_ops": [{"op": "move", "from": a, "to": o}]}}
    path = os.path.join(os.getcwd(), "system/staging/drafts/hc-move-back.json")
    def write():
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w").write(json.dumps(spec))
        return "written"
    call("Write", {"file_path": path, "content": json.dumps(spec)}, write)
    text = "I've prepared the move back.\nCHANGE: system/staging/drafts/hc-move-back.json | Move the FAL steering minutes back"
else:
    text = "Done."
out({"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}})
out({"type": "result", "result": text, "session_id": "sess-hc-guard", "permission_denials": denied})
'''

    @staticmethod
    def add_word(path, word):
        """Add one paragraph holding `word` to a .docx (its word/document.xml), so search has a word only that file holds."""
        import zipfile
        tmp = path.with_name(path.name + ".tmp")
        with zipfile.ZipFile(path) as z, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as w:
            for item in z.infolist():
                data = z.read(item.filename)
                if item.filename == "word/document.xml":
                    text = data.decode("utf-8")
                    para = f"<w:p><w:r><w:t>The {word} budget line</w:t></w:r></w:p>"
                    at = text.rfind("<w:sectPr")
                    at = at if at != -1 else text.rfind("</w:body>")
                    data = (text[:at] + para + text[at:]).encode("utf-8")
                w.writestr(item, data)
        tmp.replace(path)

    # ── this class's set-up: its server's stand-ins ──

    @classmethod
    def start_server(cls):
        import handcheck
        env0, make0 = handcheck.Session.server_env, handcheck.Session.make_vault
        fake = None

        def make(s, name="vault"):
            root = make0(s, name)
            cls.add_word(root / cls.WEEKLY, cls.WORD)
            cls.add_word(root / cls.PORTF, cls.PWORD)
            return root

        def env(s, root, port):
            nonlocal fake
            fake = s.dir / "fake_claude_guarded.py"
            fake.write_text(cls.FAKE, encoding="utf-8")
            fake.chmod(0o755)
            return {**env0(s, root, port), "CREAITE_CLAUDE": str(fake), "CREAITE_NO_LAUNCH": "1"}
        handcheck.Session.server_env, handcheck.Session.make_vault = env, make
        try:
            super().start_server()
        finally:
            handcheck.Session.server_env, handcheck.Session.make_vault = env0, make0
        cls.guard_log = fake.parent / "fake_claude_guarded.jsonl"

    def setUp(self):
        super().setUp()
        self.spy()

    # ── helpers ──

    @staticmethod
    def archived(stored):
        """The stored path's place below its engagement's (or the portfolio's) own 99 Archive."""
        parts = stored.split("/")
        return "/".join(parts[:2] + ["99 Archive"] + parts[2:])

    def at(self, stored):
        return self.vault / stored

    def spy(self):
        """Record each /api/open, /api/files/move-back and /api/health/fix answer the page gets (window.__got)."""
        self.b.eval("""(()=>{ if(window.__got) return true; window.__got=[]; const f0=window.fetch;
          window.fetch=async(...a)=>{ const r=await f0(...a); const u=String(a[0]&&a[0].url||a[0]);
            if(/\\/api\\/(open|files\\/move-back|health\\/fix|undo)/.test(u)) r.clone().json().then(j=>window.__got.push({u,j})).catch(()=>{});
            return r; }; return true; })()""")

    def got(self, route):
        return [x["j"] for x in self.b.eval("window.__got") if route in x["u"]]

    def wait_for(self, fn, timeout=30, what="the change"):
        import time
        end = time.time() + timeout
        while time.time() < end:
            if fn():
                return
            self.b.pump(0.2)
        self.fail(f"timed out waiting for {what}")

    def health(self):
        """Settings › Health, once its check has answered: (the archive_reports problem row's text or None, the Archiving lines)."""
        self.screen("settings-health")
        self.b.wait("!!document.querySelector('#healthArchiving') || !!document.querySelector('#healthCard .hrow[data-check=archive_reports]')", 60)
        self.b.pump(0.3)
        return self.b.eval("""(()=>{ const r=document.querySelector('#healthCard .hrow[data-check=archive_reports]');
          return [r?r.innerText:null, [...document.querySelectorAll('#healthArchiving li')].map(l=>l.innerText.trim())]; })()""")

    def approve_card(self):
        """The change card in ask creaite: (its title, its lines), then Approve, as Alan presses it."""
        b = self.b
        b.wait("!!document.querySelector('#chLog [data-ecard] [data-ed=approve]')", 60)
        card = b.eval("(()=>{ const c=[...document.querySelectorAll('#chLog [data-ecard]')].pop(); "
                      "return [c.querySelector('b').textContent, [...c.querySelectorAll('.edlines li')].map(l=>l.innerText.trim())]; })()")
        b.eval("[...document.querySelectorAll('#chLog [data-ecard]')].pop().querySelector('[data-ed=approve]').click()")
        b.wait("[...document.querySelectorAll('#chLog [data-ecard]')].pop().querySelector('.acts').textContent.includes('Approved')", 90)
        return card

    def archive_via_health(self):
        """Health's Archive them, then Approve on the card; (the offer's text, the card's title, its lines)."""
        row, _ = self.health()
        self.assertTrue(row, "Health offers to archive the old reports and minutes")
        self.b.eval("document.querySelector('#healthCard .hrow[data-check=archive_reports] .hact button').click()")
        title, lines = self.approve_card()
        self.wait_for(lambda: all(self.at(self.archived(f)).is_file() for f in self.DUE), what="the files in 99 Archive")
        return row, title, lines

    def ensure_archived(self, *stored):
        """The four (or those named) in 99 Archive: archived through Health and the card if they aren't."""
        if not all(self.at(self.archived(f)).is_file() for f in stored or self.DUE):
            self.archive_via_health()

    def files_archived(self):
        """Files › the Archived chip: [(stored path, tagged Archived, has Move back, name)]. Since #124 a row's data-fp (and its
        Move back and open link) is the file's own place in 99 Archive, unique where two came from one stored path, and data-hp
        the stored path it came from."""
        b = self.b
        self.screen("files")
        b.wait("!!document.querySelector('#fquick [data-q=\"archived\"]')", 20)
        b.eval("document.querySelector('#fquick [data-q=\"archived\"]').click()")
        b.pump(0.4)
        return b.eval("[...document.querySelectorAll('#filesTbl tr[data-fp]')].map(tr=>[tr.dataset.hp||tr.dataset.fp, "
                      "[...tr.querySelectorAll('.tag')].some(t=>t.textContent.trim()==='Archived'), "
                      "!!tr.querySelector('[data-moveback]'), tr.querySelector('a[data-openfile]').textContent])")

    def move_back(self, stored):
        """Files' Move back on the archived file `stored`; the route's answer."""
        rows = self.files_archived()
        self.assertIn(stored, [r[0] for r in rows], "listed under Archived")
        n = len(self.got("/api/files/move-back"))
        self.b.eval(f"document.querySelector('#filesTbl [data-moveback={json.dumps(self.archived(stored))}]').click()")   # #124: its place in 99 Archive
        self.wait_for(lambda: len(self.got("/api/files/move-back")) > n, what="Move back's answer")
        return self.got("/api/files/move-back")[-1]

    def undo_latest(self):
        """Undo the latest apply as Alan would: Activity's "Undo this apply" when Activity has a line for it; else the Undo
        the card's "Approved" message carries (the same /api/undo {apply_id}), sent from the page. Returns how it was undone."""
        b = self.b
        self.screen("activity")
        b.pump(0.5)
        n = len(self.got("/api/undo"))
        if b.eval("!!document.querySelector('#actTbl [data-undoapply]')"):
            how = "Activity › Undo this apply"
            b.eval("document.querySelector('#actTbl [data-undoapply]').click()")
        else:
            apply_id = b.eval("D.latest_apply")
            self.assertTrue(apply_id, "an apply to undo")
            how = f"the card's Undo (/api/undo apply {apply_id}; Activity has no line for a file-only apply)"
            b.eval(f"api('/api/undo',{{apply_id:{json.dumps(apply_id)}}}).then(r=>{{ window.__got.push({{u:'/api/undo',j:r}}); return reloadData(); }})")
        self.wait_for(lambda: len(self.got("/api/undo")) > n, what="the undo")
        self.assertTrue(self.got("/api/undo")[-1].get("ok"), self.got("/api/undo")[-1])
        return how

    def search(self, words):
        """Files' search box, as typed (its results drawn), and the same /api/search answer the box gets: the stored paths
        of the results (reports, documents and meetings)."""
        b = self.b
        self.screen("files")
        b.eval(f"(()=>{{ const i=document.getElementById('vsInput'); i.value={json.dumps(words)}; i.dispatchEvent(new Event('input',{{bubbles:true}})); return true; }})()")
        b.wait("!document.getElementById('vsResults').hidden && document.getElementById('vsNote').textContent!=='Searching…' "
               "&& !!document.getElementById('vsResults').textContent", 30)
        found = b.eval(f"fetch('/api/search?'+new URLSearchParams({{q:{json.dumps(words)}}}),{{headers:{{'X-Creaite-Token':D.token||''}}}})"
                       ".then(r=>r.json()).then(j=>Object.values(j.groups||{}).flat().map(r=>(r.opens&&r.opens.path)||r.path||r.title))")
        b.eval("vsClear()")
        return found

    def opened(self, stored):
        """Open `stored` the way a saved prep page's link does (#openfile=…, through /api/open); the server's answer."""
        n = len(self.got("/api/open"))
        self.b.eval(f"location.hash='#openfile='+encodeURIComponent({json.dumps(stored)})")
        self.wait_for(lambda: len(self.got("/api/open")) > n, what="/api/open")
        return self.got("/api/open")[-1]

    def ask(self, text):
        """Send `text` in ask creaite and wait for the run to end; the new part of the chat, as text."""
        b = self.b
        b.eval("openChat()")
        b.wait("!!document.getElementById('chIn')")
        before = b.eval("document.getElementById('chLog').innerText.length")
        b.eval(f"(()=>{{ const i=document.getElementById('chIn'); i.value={json.dumps(text)}; i.dispatchEvent(new Event('input',{{bubbles:true}})); send(); return true; }})()")
        b.wait("BUSY", 20)
        b.wait("!BUSY", 120)
        b.pump(0.5)
        return b.eval(f"document.getElementById('chLog').innerText.slice({before})")

    def guard_calls(self):
        if not self.guard_log.exists():
            return []
        return [json.loads(x) for x in self.guard_log.read_text().splitlines() if x.strip()]

    # ── the checks ──

    def test_c31_moved_incl_portfolio(self):
        """31. Approve → the files are in `projects/FAL Falcon Data Platform/99 Archive/reports/` and `/99 Archive/minutes/`, and
        the portfolio's in `projects/_portfolio/99 Archive/minutes/`. Nothing is deleted."""
        before = sorted(str(p.relative_to(self.vault)) for p in (self.vault / "projects").rglob("*") if p.is_file())
        self.assertIn(self.WEEKLY, self.search(self.WORD), "before: search finds the weekly report by its word")
        row, title, lines = self.archive_via_health()
        self.assertIn("Archive 4 reports and minutes older than 12 months", row)
        for f in self.DUE:
            self.assertFalse(self.at(f).exists(), f)
            self.assertTrue(self.at(self.archived(f)).is_file(), self.archived(f))
            self.assertIn(f"Move file {f} → {self.archived(f)}", lines)
        self.assertTrue((self.vault / self.FAL / "99 Archive/reports").is_dir() and (self.vault / self.FAL / "99 Archive/minutes").is_dir())
        self.assertTrue((self.vault / "projects/_portfolio/99 Archive/minutes").is_dir())
        for f in self.KEPT:
            self.assertTrue(self.at(f).is_file(), f"kept in place: {f}")
        after = sorted(str(p.relative_to(self.vault)) for p in (self.vault / "projects").rglob("*") if p.is_file())
        moved = {f: self.archived(f) for f in self.DUE}
        self.assertEqual(sorted(moved.get(f, f) for f in before), after, "nothing deleted: every file is where it was or moved")
        self.note(31, f"before: search \"{self.WORD}\" finds the weekly report; "
                      f"Health › Archive them → card \"{title}\" ({len(lines)} moves) → Approve: 4 files in their 99 Archive "
                      f"(FAL reports ×2, FAL minutes, portfolio minutes); {len(after)} files before and after, none deleted")

    def test_c32_links_not_indexed_guard(self):
        """32. Open FAL's latest-reports link for the moved report → it still opens. Search for its words → not found. In ask
        creaite, "read FAL's archived weekly report" → refused."""
        self.ensure_archived()
        link = self.opened(self.WEEKLY)
        self.assertTrue(link.get("ok"), link)
        self.assertEqual(link.get("path"), str((self.vault / self.archived(self.WEEKLY)).resolve()), "it opens the file in 99 Archive")
        found = self.search(self.WORD)
        self.assertEqual([f for f in found if "weekly report" in str(f) or "99 Archive" in str(f)], [], f"not found: {found}")
        chat = self.ask("read FAL's archived weekly report")
        calls = [c for c in self.guard_calls() if c["tool"] == "Read" and "99 Archive" in json.dumps(c["input"])]
        self.assertTrue(calls, "the stand-in asked to Read the archived file")
        self.assertEqual(calls[-1]["exit"], 2, f"the guard hook refuses it: {calls[-1]}")
        self.assertIn("refused", chat.lower())
        why = calls[-1]["stderr"].strip()
        self.note(32, "the demo's Recent reports link FAL's newer reports, so the moved report's stored link is opened as a saved "
                      f"prep page's link (#openfile=…) → /api/open opens {self.archived(self.WEEKLY).split('/', 2)[2]}; search \"{self.WORD}\" "
                      f"→ {len(found)} results, not it; ask creaite: the guard hook (reach.py hook, as Claude Code runs it) exits 2: "
                      f"\"…{why[-90:]}\" (stand-in Claude; a real model's wording by hand)")

    def test_c33_quiet_for_month(self):
        """33. Health → the line now says "Archived 4 reports and minutes on DD-MM-YYYY" and stays quiet for the rest of the
        month."""
        self.ensure_archived()
        row, lines = self.health()
        day = self.now[:10]
        want = f"Archived 4 reports and minutes on {day[8:10]}-{day[5:7]}-{day[:4]}"
        self.assertIsNone(row, "no offer while archived this month")
        self.assertTrue(any(want in ln for ln in lines), f"{want!r} in {lines}")
        import calendar
        y, m = int(day[:4]), int(day[5:7])
        last = f"{day[:8]}{calendar.monthrange(y, m)[1]:02d} 18:00"
        code, out = self.run_in_vault("archive.py", "status", "--json", env={"CREAITE_NOW": last})
        st = json.loads(out.strip().splitlines()[-1])
        self.assertEqual(code, 0, out)
        self.assertFalse(st["reports"]["offer"], st)
        self.assertTrue(st["reports_line"].startswith(want), st["reports_line"])
        self.note(33, f"Health: \"{[ln for ln in lines if want in ln][0]}\", no Archive them; archive.py status on {last[:10]}: "
                      f"offer false, same line")

    def test_c34_undo(self):
        """34. Undo → the files are back where they were, and the `99 Archive` folders the move made are gone."""
        self.ensure_archived()
        how = self.undo_latest()
        self.wait_for(lambda: all(self.at(f).is_file() for f in self.DUE), what="the files back")
        for f in self.DUE:
            self.assertFalse(self.at(self.archived(f)).exists(), f)
        self.assertFalse((self.vault / self.FAL / "99 Archive").exists(), "FAL's 99 Archive is gone")
        self.assertFalse((self.vault / "projects/_portfolio/99 Archive").exists(), "the portfolio's 99 Archive is gone")
        self.note(34, f"Undo through {how} → 4 files back; both 99 Archive folders gone")

    def test_c35_archived_chip(self):
        """35. Archive them again (check 30). Files → an **Archived** chip; it lists the four moved files, each tagged Archived
        with **Move back**, the portfolio's at "Portfolio › minutes". No other row in Files has Move back. Clicking a name opens
        the file."""
        b = self.b
        again = not all(self.at(self.archived(f)).is_file() for f in self.DUE)
        self.ensure_archived()
        rows = self.files_archived()
        self.assertEqual(sorted(r[0] for r in rows), sorted(self.DUE))
        self.assertTrue(all(r[1] and r[2] for r in rows), rows)
        # BL-101: the portfolio is "Portfolio" in Files, never its folder name
        where = b.eval(f"(document.querySelector('#filesTbl tr[data-hp={json.dumps(self.PORTF)}] td.x')||{{}}).textContent||''")
        self.assertEqual(where, "Portfolio › minutes", "the portfolio's minutes are under Portfolio")
        self.assertNotIn("_portfolio", b.eval("document.getElementById('v-files').innerText"), "Files never shows the folder name")
        others = {}
        for q in b.eval("[...document.querySelectorAll('#fquick [data-q]')].map(e=>e.dataset.q)"):
            if q == "archived":
                continue
            b.eval(f"document.querySelector('#fquick [data-q={json.dumps(q)}]').click()")
            b.pump(0.3)
            others[q] = b.eval("[document.querySelectorAll('#filesTbl tr[data-fp]').length, document.querySelectorAll('#filesTbl [data-moveback]').length]")
        for code in b.eval("P.map(p=>p.code)") + ["_portfolio"]:
            b.eval(f"document.querySelector('#tree [data-p={json.dumps(code)}][data-f=All]').click()")
            b.pump(0.3)
            others[code] = b.eval("[document.querySelectorAll('#filesTbl tr[data-fp]').length, document.querySelectorAll('#filesTbl [data-moveback]').length]")
        self.assertEqual({k: v[1] for k, v in others.items() if v[1]}, {}, "Move back only under Archived")
        self.files_archived()
        n = len(self.got("/api/open"))
        b.eval(f"document.querySelector('#filesTbl tr[data-hp={json.dumps(self.STEER)}] a[data-openfile]').click()")
        self.wait_for(lambda: len(self.got("/api/open")) > n, what="/api/open")
        o = self.got("/api/open")[-1]
        self.assertTrue(o.get("ok"), o)
        self.assertEqual(o.get("path"), str((self.vault / self.archived(self.STEER)).resolve()))
        self.note(35, f"{'archived again through Health and the card' if again else 'already archived (check 34 not run)'}; Archived chip lists 4, each tagged Archived with Move back (the portfolio's at Portfolio › minutes); no Move back under "
                      f"{len(others)} other chips and folders ({sum(v[0] for v in others.values())} rows); clicking the steering "
                      f"minutes' name → /api/open opens it in 99 Archive")

    def test_c36_move_back(self):
        """36. Move back the FAL weekly report → the change card. Approve → it is back in `reports/`, gone from the Archived
        list, and search finds it again."""
        self.ensure_archived(self.WEEKLY)
        r = self.move_back(self.WEEKLY)
        self.assertTrue(r.get("ok") and r.get("card"), r)
        title, lines = self.approve_card()
        self.assertEqual(lines, [f"Move file {self.archived(self.WEEKLY)} → {self.WEEKLY}"])
        self.wait_for(lambda: self.at(self.WEEKLY).is_file(), what="the report back")
        self.assertFalse(self.at(self.archived(self.WEEKLY)).exists())
        self.assertNotIn(self.WEEKLY, [x[0] for x in self.files_archived()], "gone from the Archived list")
        found = self.search(self.WORD)
        self.assertIn(self.WEEKLY, found, "search finds it again")
        self.note(36, f"Move back → card \"{title}\", one line \"Move file …/99 Archive/reports/… → …/reports/…\" → Approve: "
                      f"back in reports/, 3 left under Archived, search \"{self.WORD}\" finds it")

    def test_c37_not_offered_again(self):
        """37. Health's monthly line → it does not offer that report again."""
        if self.at(self.archived(self.WEEKLY)).is_file():
            self.move_back(self.WEEKLY)
            self.approve_card()
            self.wait_for(lambda: self.at(self.WEEKLY).is_file(), what="the report back")
        row, lines = self.health()
        self.assertIsNone(row, "no offer this month")
        from datetime import date
        d = date.fromisoformat(self.now[:10])
        nxt = date(d.year + (d.month == 12), d.month % 12 + 1, 2).isoformat() + " 09:00"
        code, out = self.run_in_vault("archive.py", "status", "--json", env={"CREAITE_NOW": nxt})
        st = json.loads(out.strip().splitlines()[-1])
        self.assertEqual((st["reports"]["due"], st["reports"]["offer"]), (0, False), st)
        code, out = self.run_in_vault("archive.py", "reports", env={"CREAITE_NOW": nxt})
        self.assertEqual(code, 1, f"nothing to archive next month either: {out}")
        self.assertNotIn(self.WEEKLY, out)
        line = next((ln for ln in lines if "reports and minutes" in ln), "")
        self.note(37, f"Health this month: \"{line}\", no offer; archive.py on {nxt[:10]}: 0 due, no offer, "
                      f"reports exits 1 (\"{out.strip()[:60]}\")")

    def test_c38_undo(self):
        """38. Undo → the report is back in `99 Archive`, unindexed."""
        self.assertTrue(self.at(self.WEEKLY).is_file(), "needs check 36's move back")
        how = self.undo_latest()
        self.wait_for(lambda: self.at(self.archived(self.WEEKLY)).is_file(), what="the report in 99 Archive again")
        self.assertFalse(self.at(self.WEEKLY).exists())
        found = self.search(self.WORD)
        self.assertEqual([f for f in found if "weekly report" in str(f)], [], f"unindexed: {found}")
        self.assertIn(self.WEEKLY, [x[0] for x in self.files_archived()], "listed under Archived again")
        self.note(38, f"Undo through {how} → in 99 Archive again, under Archived; search "
                      f"\"{self.WORD}\" doesn't find it")

    def test_c39_taken_place_refused(self):
        """39. Put a file with the same name in `reports/`, then Move back that report → refused: "rename or move that file
        first". The file in `reports/` is unchanged."""
        self.ensure_archived(self.WEEKLY)
        taken = self.at(self.WEEKLY)
        taken.write_bytes(b"a newer file with the same name\n")
        try:
            cards = self.b.eval("document.querySelectorAll('#chLog [data-ecard]').length")
            r = self.move_back(self.WEEKLY)
            self.assertFalse(r.get("ok"), r)
            self.assertIn("rename or move that file first", r.get("message", ""))
            self.b.pump(0.5)
            self.assertEqual(self.b.eval("document.querySelectorAll('#chLog [data-ecard]').length"), cards, "no card")
            self.assertEqual(taken.read_bytes(), b"a newer file with the same name\n", "unchanged")
            self.assertTrue(self.at(self.archived(self.WEEKLY)).is_file())
            toast = self.b.eval("document.body.innerText.includes('rename or move that file first')")
            self.note(39, f"refused: \"…{r['message'][-90:]}\"{' (shown in the toast)' if toast else ''}; no card; the file in "
                          "reports/ unchanged")
        finally:
            taken.unlink()

    def test_c40_portfolio_minutes(self):
        """40. Move back the portfolio's minutes → back in `projects/_portfolio/minutes/`."""
        self.ensure_archived(self.PORTF)
        r = self.move_back(self.PORTF)
        self.assertTrue(r.get("ok") and r.get("card"), r)
        title, lines = self.approve_card()
        self.assertEqual(lines, [f"Move file {self.archived(self.PORTF)} → {self.PORTF}"])
        self.wait_for(lambda: self.at(self.PORTF).is_file(), what="the minutes back")
        self.assertFalse(self.at(self.archived(self.PORTF)).exists())
        found = self.search(self.PWORD)
        self.note(40, "card \"Move file projects/_portfolio/99 Archive/minutes/… → projects/_portfolio/minutes/…\" → Approve: back in projects/_portfolio/minutes/"
                      + ("; search finds it again" if self.PORTF in found else f"; search \"{self.PWORD}\": {found}"))

    def test_c41_ask_creaite_refused(self):
        """41. In ask creaite, "move the archived FAL steering minutes back" → refused: "an archived file is moved back from
        Files (Move back), never from ask creaite"."""
        self.ensure_archived(self.STEER)
        seen = len(self.guard_calls())
        chat = self.ask("move the archived FAL steering minutes back")
        self.assertIn("an archived file is moved back from Files (Move back), never from ask creaite", chat)
        self.assertTrue(self.at(self.archived(self.STEER)).is_file(), "still in 99 Archive")
        self.assertFalse(self.at(self.STEER).exists())
        calls = self.guard_calls()[seen:]
        bash = [c for c in calls if c["tool"] == "Bash"]
        write = [c for c in calls if c["tool"] == "Write"]
        self.assertTrue(bash and bash[-1]["exit"] == 2, f"filechange.py move on 99 Archive refused by the hook: {bash}")
        self.note(41, "ask creaite: filechange.py move refused by the guard hook (exit 2); the move-back spec written in drafts "
                      f"({'allowed' if write and write[-1]['exit'] == 0 else 'refused'}) and named on a CHANGE line → the server's "
                      "card refuses it: \"…never from ask creaite\"; the minutes stay in 99 Archive (stand-in Claude)")


class Bl334And316(HandcheckCase):
    """Phase 2: BL-334 alerts read the conversation (42 to 47) and BL-316's consistency (49, 50). Own vault.

    42 to 47 build on each other, as the hand checks do: `ensure(step)` records (or does) each earlier step once, so any of
    them runs on its own with --only. Recording is the check's own command (`sweep.py vip record <file> --found sweep`,
    hcbase.vip_found), each recorded ten minutes after the conversation's last message, so "updated HH:MM" on the card is
    shown to be the last message's time (`last`), not when it was recorded."""
    own_vault = True
    CONV = "19:hc-falcon@thread.v2"
    RASHID = "Rashid Al Suwaidi <rashid@northgate.example>"
    SECRET = "HC MESSAGE TEXT NEVER KEPT"          # a message's own text, sent with each conversation: vip.json must not keep it

    @classmethod
    def setUpClass(cls):
        cls.steps = set()
        super().setUpClass()

    # ── the conversations (fictional: the demo's people) ──
    def day(self):
        return (self.now or "")[:10]

    def falcon(self, later=False):
        from datetime import date, timedelta
        due = (date.fromisoformat(self.day()) + timedelta(days=7)).isoformat()
        items = [{"type": "action", "text": "Take the platform from production to live", "owner": "Rashid Al Suwaidi", "due": due},
                 {"type": "decision", "text": "Go-live work falls under the existing contract"}]
        if later:
            items.append({"type": "risk", "text": "Test licences may not arrive before go-live"})
        return {"kind": "teams", "conversation": self.CONV, "title": "Falcon go-live", "from": self.RASHID,
                "people": [self.RASHID, "Lena Fischer"], "last": f"{self.day()} {'09:05' if later else '08:40'}",
                "link": "https://teams.microsoft.com/l/chat/hc", "sensitivity": "normal", "attachments": [],
                "summary": "Northgate will take the platform from production to live; go-live work falls under the existing contract.",
                "items": items, "messages": [{"text": self.SECRET}], "body": self.SECRET}

    def hello(self):
        return {"kind": "teams", "conversation": "19:hc-hello@thread.v2", "title": "Group chat", "from": self.RASHID,
                "people": [self.RASHID, "Lena Fischer"], "last": f"{self.day()} 08:44",
                "link": "https://teams.microsoft.com/l/chat/hc-hello", "sensitivity": "normal", "attachments": [],
                "summary": "Greetings only.", "items": [], "messages": [{"text": self.SECRET}]}

    def ensure(self, step):
        """Do the hand checks' steps up to `step` once each: first (42), quiet (43), update (44)."""
        import hcbase
        order = {"first": (8, 50, [lambda: self.falcon()]),                 # last message 08:40
                 "quiet": (8, 55, [lambda: self.falcon(), self.hello]),
                 "update": (9, 15, [lambda: self.falcon(later=True), self.hello])}  # last message 09:05
        for name in order:
            if name not in self.steps:
                h, m, make = order[name]
                code, out = hcbase.vip_found(self.vault, [f() for f in make], f"{self.day()} {h:02d}:{m:02d}")
                self.assertEqual(code, 0, out[-500:])
                type(self).steps.add(name)
            if name == step:
                break
        self.b.eval("vipPoll().then(()=>{ go('today'); renderToday(); return true; })")
        self.screen("today")

    def vip(self):
        return json.loads((self.vault / "system/staging/vip.json").read_text(encoding="utf-8"))

    def alert(self, conv=None):
        return next(a for a in self.vip()["alerts"] if a.get("conv") == (conv or self.CONV))

    def proposals(self):
        return sorted(p.name for p in (self.vault / "system/staging").glob("proposed-*.json"))

    def page_card(self):
        """Today's card for the Falcon conversation, as drawn: shown (To decide's "+n more" opened if it sits below the top
        five), its title, its text, its candidates (tag, the item, and each button's action and item number)."""
        b = self.b
        b.eval("(()=>{ const m=document.querySelector('#v-today [data-more=td][aria-expanded=false]'); if(m) m.click(); return true; })()")
        b.pump(0.3)
        return b.eval("""(()=>{ const L=[...document.querySelectorAll('#tdList>li.td-message')];
          return L.map(li=>({title:li.querySelector('.t').textContent, hidden:li.hidden||!li.offsetParent,
            text:li.textContent.replace(/\\s+/g,' ').trim(), rowButtons:li.querySelectorAll(':scope>.tacts button').length,
            rowActs:[...li.querySelectorAll(':scope>.tacts button')].map(x=>x.dataset.alertdo||''),
            cands:[...li.querySelectorAll('.tdcand')].map(c=>({tag:c.querySelector('.tdctag').textContent, t:c.querySelector('.ct').textContent,
              buttons:[...c.querySelectorAll('button')].map(x=>[x.dataset.alertdo, x.dataset.cand, x.getAttribute('aria-label')||x.dataset.tip||''])}))})); })()""")

    def falcon_cards(self):
        return [c for c in self.page_card() if c["title"] == "Falcon go-live"]

    @staticmethod
    def labels(cand):
        return [x[0] for x in cand["buttons"]]

    def test_c42_one_card_per_conversation(self):
        """42. Today → one card titled "Falcon go-live" (not "Group chat"), "updated 08:40" (its last message, recorded at
        08:50), the summary, and two candidates, each with **Create work item** and **Dismiss**. The project is Falcon Data
        Platform, matched from the title."""
        self.ensure("first")
        cards = self.falcon_cards()
        self.assertEqual(len(cards), 1, f"one card: {[c['title'] for c in self.page_card()]}")
        c = cards[0]
        self.assertFalse(c["hidden"], "the card is on show")
        self.assertNotIn("Group chat", c["text"])
        self.assertIn("updated 08:40", c["text"])
        self.assertIn("Northgate will take the platform from production to live", c["text"])
        self.assertIn("Falcon Data Platform", c["text"], "the project, by name")
        self.assertEqual([x["tag"] for x in c["cands"]], ["Action", "Decision"])
        for x in c["cands"]:
            self.assertEqual(self.labels(x), ["make", "dismiss"], x)
        self.assertEqual(c["rowButtons"], 1, "the work-item buttons are per item")
        self.assertEqual(c["rowActs"], ["handled"], "BL-342: only Handled on the card itself")
        a = self.alert()
        self.assertEqual(a["p"], "FAL", "matched from the title")
        names = [x[2] for x in c["cands"][0]["buttons"]]
        self.note(42, f"card \"{c['title']}\", updated 08:40 (the last message; recorded at 08:50), Falcon Data Platform (p=FAL); "
                      f"Action + Decision, each {' / '.join(n.split(':')[0] for n in names)}")

    def test_c43_quiet_line(self):
        """43. A second conversation titled "Group chat" with nothing in it → one quiet line ("… : nothing for you"), with only
        Seen (#276) and no count. Its title is the people in it, never "Group chat"."""
        self.ensure("quiet")
        b = self.b
        quiet = b.eval("""[...document.querySelectorAll('#tdList>li.td-quiet')].map(li=>({text:li.textContent.replace(/\\s+/g,' ').trim(),
          buttons:li.querySelectorAll('button').length, acts:[...li.querySelectorAll('button')].map(x=>x.dataset.alertdo||''),
          tag:!!li.querySelector('.tdtag')}))""")
        self.assertEqual(len(quiet), 1, quiet)
        q = quiet[0]
        self.assertIn("Rashid Al Suwaidi with Lena Fischer: nothing for you", q["text"])
        self.assertEqual(q["buttons"], 1, "only Seen")                                       # #276
        self.assertEqual(q["acts"], ["seen"], "the one button is Seen")
        self.assertFalse(q["tag"], "no tag")
        page = b.eval("document.getElementById('tdList').textContent")
        self.assertNotIn("Group chat", page)
        a = self.alert("19:hc-hello@thread.v2")
        self.assertTrue(a["quiet"])
        self.assertEqual(a["title"], "Rashid Al Suwaidi, Lena Fischer", "the people, never Group chat")
        open_ = [x for x in self.vip()["alerts"] if not x.get("seen") and not x.get("quiet")]
        rail = b.eval("(()=>{ const e=document.querySelector('.rail button[data-v=\"today\"] .badge'); return e&&e.offsetParent?e.textContent.trim():''; })()")
        self.assertEqual(rail, str(len(open_)) if open_ else "", "the rail counts the card, not the quiet line")
        self.assertEqual(len(self.falcon_cards()), 1, "the first card is still one card")
        self.note(43, f"\"{q['text']}\", only Seen; title in vip.json \"{a['title']}\"; Today's count {rail or '0'} (the card only)")

    def test_c44_same_card_updated(self):
        """44. Record the first conversation again, its last message at 09:05, with a third item → the same card is updated
        ("updated 09:05", three candidates). No second card."""
        self.ensure("quiet")
        before = self.alert()["id"]
        self.ensure("update")
        cards = self.falcon_cards()
        self.assertEqual(len(cards), 1, "no second card")
        c = cards[0]
        self.assertIn("updated 09:05", c["text"])
        self.assertEqual([x["tag"] for x in c["cands"]], ["Action", "Decision", "Risk"])
        a = self.alert()
        self.assertEqual(a["id"], before, "the same alert")
        self.assertEqual(len([x for x in self.vip()["alerts"] if x.get("conv") == self.CONV]), 1)
        self.note(44, "same alert id, updated 09:05 (the last message; recorded at 09:15), Action + Decision + Risk; one card")

    def test_c45_dismiss_create(self):
        """45. Dismiss the risk → it goes; nothing in Review. Create work item on the action → its panel, filled in; Save → one
        proposal in Review (staged, not applied), for Falcon Data Platform."""
        self.ensure("update")
        b = self.b
        before = self.proposals()
        b.eval("document.querySelector('#tdList [data-alertdo=dismiss][data-cand=\"3\"]').click()")
        b.wait("!document.querySelector('#tdList [data-alertdo=dismiss][data-cand=\"3\"]')", 10)
        b.pump(0.5)
        self.assertEqual(self.proposals(), before, "Dismiss stages nothing")
        self.assertTrue(self.alert()["candidates"][2].get("dismissed"))
        self.assertEqual([x["tag"] for x in self.falcon_cards()[0]["cands"]], ["Action", "Decision"], "the risk goes")
        b.eval("document.querySelector('#tdList [data-alertdo=make][data-cand=\"1\"]').click()")
        b.wait("document.getElementById('panel').classList.contains('on') && document.querySelector('[data-alertpeek=save]')", 15)
        b.pump(0.4)
        filled = b.eval("(document.getElementById('pkTitle')||{}).textContent||''")
        says = b.eval("(document.getElementById('panel').innerText.match(/Save \\(.\\S*\\) [^\\n]*/)||[''])[0]")
        b.eval("document.querySelector('[data-alertpeek=save]').click()")
        b.wait("!document.querySelector('#tdList [data-alertdo=make][data-cand=\"1\"]')", 15)
        b.pump(0.8)
        after = self.proposals()
        new = sorted(set(after) - set(before))
        made = self.alert()["candidates"][0].get("made") or {}
        applied = (self.vault / "system/staging/applied" / str(made.get("proposal"))).exists()
        self.assertEqual(len(new), 1, f"one proposal in Review: none; the peek says \"{says}\", but Save applied it at once "
                                      f"(made {made.get('id')} from {made.get('proposal')}, now in staging/applied/: {applied})")
        spec = json.loads((self.vault / "system/staging" / new[0]).read_text(encoding="utf-8"))
        self.assertEqual(len(spec["items"]), 1)
        item = spec["items"][0]
        self.assertEqual(item["table"], "actions")
        self.assertEqual(item["values"]["project"], "FAL")
        self.assertEqual(item["values"]["description"], "Take the platform from production to live")
        self.screen("review")
        rev = b.eval("document.getElementById('v-intake-review').innerText")
        self.assertIn("Take the platform from production to live", rev)
        self.assertIn("Falcon Data Platform", rev)
        self.assertEqual(b.errors, [], "page errors")
        self.note(45, f"Dismiss: 0 proposals, risk gone; Create work item (peek \"{filled}\", saved): "
                      f"1 proposal {new[0]} (actions, FAL), shown in Review under Falcon Data Platform")

    def test_c46_sweep_skips_it(self):
        """46. Stage a sweep file whose item carries that conversation and a time before 09:05 → nothing proposed for it:
        "skipped (that conversation is summarised on Today …)"."""
        self.ensure("update")
        before = self.proposals()
        src = (f"Teams · Chat: Falcon go-live · From: Rashid Al Suwaidi · Sent: {self.day()} 08:50 · "
               "Link: https://teams.microsoft.com/l/message/hc-a1")
        f = self.vault / "system/staging/drafts/hc-sweep.json"
        f.write_text(json.dumps({"items": [{"table": "actions", "conversation": self.CONV,
                                            "values": {"project": "FAL", "description": "Take the platform from production to live",
                                                       "owner": "Alan Carter", "source": src}}]}), encoding="utf-8")
        code, out = self.run_in_vault("sweep.py", "stage", f)
        self.assertEqual(code, 0, out[-500:])
        self.assertEqual(self.proposals(), before, "nothing proposed")
        line = next((ln.strip() for ln in out.splitlines() if "summarised on Today" in ln), "")
        self.assertIn("skipped (that conversation is summarised on Today", line)
        self.note(46, f"no proposal; \"{line[:120]}\"")

    def test_c47_no_message_text_no_vip(self):
        """47. `system/staging/vip.json` → the summary and candidates only; no message text. Nothing on screen says "VIP"."""
        self.ensure("update")
        text = (self.vault / "system/staging/vip.json").read_text(encoding="utf-8")
        self.assertNotIn(self.SECRET, text, "no message text")
        for a in self.vip()["alerts"]:
            self.assertFalse({"messages", "body", "text"} & set(a), f"message fields kept: {sorted(a)}")
        a = self.alert()
        self.assertTrue(a["summary"])
        self.assertTrue(a["candidates"])
        self.assertNotIn("VIP", text.replace('"vip"', ""), "vip.json says VIP")
        b = self.b
        shown = b.eval("document.body.innerText + ' ' + document.title")
        self.assertNotIn("VIP", shown, "on Today")
        names = b.eval("[...document.querySelectorAll('#v-today [aria-label],#v-today [data-tip],#v-today [title]')]"
                       ".map(e=>(e.getAttribute('aria-label')||'')+(e.getAttribute('data-tip')||'')+(e.getAttribute('title')||'')).join(' ')")
        self.assertNotIn("VIP", names, "in Today's labels and tips")
        self.note(47, f"vip.json: {len(self.vip()['alerts'])} alerts, keys {sorted(a)[:6]}…, no message text (a sentinel "
                      "message text was sent with each conversation and isn't kept); no \"VIP\" in Today's text, labels, tips or the window title")

    def test_c49_shared_behaviour(self):
        """49. On every screen, open each menu, picker and dialog: ↑ ↓ move, Enter chooses, Esc closes and returns focus, Tab
        stays inside a dialog. (dev/tests/test_shared_behaviour.py's probe, against this vault.)"""
        import os
        import sqlite3
        from contextlib import closing
        import hcbase
        import test_shared_behaviour as tsb
        with closing(sqlite3.connect(self.vault / "system/tracker.db")) as con:
            ms = con.execute("SELECT id FROM milestones WHERE project='FAL' AND status<>'Done' ORDER BY id LIMIT 1").fetchone()[0]
        screens = hcbase.behaviour_screens(ms)
        if os.environ.get("SB_ONLY"):                  # as test_shared_behaviour: only those screens (unreached isn't judged)
            screens = {k: v for k, v in screens.items() if k in os.environ["SB_ONLY"].split(",")}
        d = hcbase.behaviour_driver(self, screens)
        keys, undo, shown, missing, n_open = set(), set(), [], [], 0
        for name in screens:
            try:
                d.goto(name)
            except (TimeoutError, RuntimeError) as e:
                missing.append(f"{name} ({str(e).splitlines()[0][:60]})")
                continue
            shown.append(name)
            try:                                   # each opener goes to the screen again: one the demo can't reopen is noted, as above
                for o, bad in d.each_opener(name, lambda i, o: d.drive(i, o["kind"])):
                    n_open += 1
                    if bad:
                        keys.add((tsb.screen_area(name), f"keys: {name} {o['sig']} “{o['name']}”: {'; '.join(bad)}"))
            except (TimeoutError, RuntimeError) as e:
                missing.append(f"{name} for its openers ({str(e).splitlines()[0][:60]})")
        for screen, script, sig, area, _how, label in tsb.SharedBehaviour.KEYED:
            if screen in shown:
                bad = getattr(d, script)()
                if bad:
                    keys.add((area, f"keys: {sig} “{label}”: {'; '.join(bad)}"))
        n_undo = 0
        for name in shown:
            done = set()

            def once(i, o, done=done):
                g = (o["sig"], tsb.undo_group(o["name"]))
                if g in done:
                    return None
                done.add(g)
                return d.pick(i, o)
            try:
                for o, bad in d.each_opener(name, once):
                    if bad is None:
                        continue
                    n_undo += 1
                    if bad:
                        undo.add((tsb.screen_area(name), f"undo: {name} {o['sig']} “{tsb.undo_group(o['name'])}”: {'; '.join(bad)}"))
            except (TimeoutError, RuntimeError) as e:
                missing.append(f"{name} for Undo ({str(e).splitlines()[0][:60]})")
        unreached = {(s["area"], "unreached: " + tsb.site_name(s)) for s in tsb.inventory() if not tsb.reached(s, d.seen)}
        known = tsb.expected("unreached")
        # Unreached is noted, not judged: it depends on the states a vault shows, and the demo's differ from the snapshot
        # sample's, where test_shared_behaviour judges it (run_tests.py).
        self.note(49, (f"screens the demo doesn't show: {', '.join(missing)}; " if missing else "")
                      + f"{len(shown)} screens, {n_open} openers driven (Enter, ↓ ↑, Esc and focus back, Tab), ⌘K and the Archive "
                      f"prompt; {n_undo} choices that save checked for Undo"
                      + (f"; {len(keys)} key failures" if keys else "; no key failures")
                      + (f"; {len(undo)} without Undo" if undo else "; each saved change offers Undo")
                      + f"; unreached {len(unreached)} (known {len(known)}"
                      + (f"; not reached on the demo: {', '.join(x.split(': ', 1)[1].split(' (')[0] for _, x in sorted(unreached - known))}" if unreached - known else "") + ")"
                      + "; wording and empty states not re-read here (checks 13, 14 and BL-325's tests)")
        self.assertFalse(keys, "\n".join(sorted(x for _, x in keys)))
        self.assertFalse(undo, "\n".join(sorted(x for _, x in undo)))

    def test_c50_old_helpers_zero(self):
        """50. `python3 dev/tools/check.py` from the repository → the old-helper count (newMenu, pkList, drawPicker, snackAdd and
        the rest) is 0."""
        import subprocess
        repo = Path(__file__).resolve().parents[3]
        r = subprocess.run([sys.executable, str(repo / "dev/tools/check.py")], cwd=repo, capture_output=True, text=True, timeout=900)
        out = r.stdout + r.stderr
        m = re.search(r"Old helpers \(BL-316, falling to 0\): (\d+) in all \(baseline (\d+)\): (.*)", out)
        self.assertTrue(m, f"check.py printed no old-helper line: {out[-400:]}")
        self.assertEqual(int(m.group(1)), 0, m.group(0))
        self.note(50, f"check.py exit {r.returncode}; \"Old helpers: {m.group(1)} in all (baseline {m.group(2)})\"; {m.group(3)[:120]}")


if __name__ == "__main__":
    unittest.main()
