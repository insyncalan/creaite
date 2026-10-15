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

    @phase2()
    def test_c06_past_time_faint_text(self):
        """6. Today in light and dark → the past hours and the now-line are clearly visible; faint text (dates, hints) is
        readable, not ghostly."""

    @phase2()
    def test_c07_resize_handle_value(self):
        """7. VoiceOver (⌘F5) on a Work column-resize handle → it reads a value (its width) and changes as you resize with ←
        and →. (Automated through the accessibility tree: measure.ax_node; VoiceOver itself stays live only.)"""

    @phase2()
    def test_c08_sortable_headers(self):
        """8. Settings › People, Tab to a column heading → it is a button; Enter sorts, and VoiceOver reads the sort order."""

    @phase2()
    def test_c09_one_button_and_field_size(self):
        """9. Today, Work, Review, Intake, Settings, Activity and Files → buttons are one height (32 px) and fields one height
        (32 px), bar Files' large centred search bar (40 px, by design). Section headings look the same on each page."""

    @phase2()
    def test_c16_touch_targets(self):
        """16. Checkboxes on Review, Intake and Activity, the Settings switches and the column-resize handles → each easy to
        hit (at least 24 px; DevTools › Inspect shows the box)."""

    @phase2()
    def test_c19_320_px_layers(self):
        """19. Every screen at 320 px → no sideways scroll. Menus, popovers, the peek, toasts and ask creaite stack in the
        right order (a menu over the peek, a toast over everything)."""


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
        """11. Build a prep page (Today › the FAL Steering committee › Prep page), then open it from the Agendas folder → the
        dashboard's fonts (where installed) and status colours, light and dark; still one file."""
        b = self.b
        dash = self._dashboard_vars(self.STATUS)
        # Today › the meeting › Prepare › Open prep page › Refresh research: the stand-in Claude researches, the server writes it
        self.screen("today")
        b.click("#dayMeets [data-prep]")
        b.wait("document.querySelector('#prepDlg [data-prepview]')", 10)
        b.eval("document.querySelector('#prepDlg [data-prepview]').click()")
        b.wait("[...document.querySelectorAll('.pph button')].some(e=>e.innerText.includes('Refresh research'))", 15)
        b.eval("[...document.querySelectorAll('.pph button')].find(e=>e.innerText.includes('Refresh research')).click()")
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
        variant of each control. Look through the screenshot sheet's check 20 (every screen, creaite, light and dark, 1400 and
        320 px) → you agree how each screen looks."""
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
        shots = sum(self.sheet(20, s, palettes=["creaite"]) for s in measure_screens())
        self.note(20, f"{shots} shots of every screen on the sheet, in place of dev/reviews/bl325-before-after/; "
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
            bb.eval("""(()=>{ const ys=[...document.querySelectorAll('#tdList .td-message, #tdList .td-quiet')].map(e=>e.getBoundingClientRect().top);
              scrollBy(0, Math.min(...ys) - 70); return true; })()""")      # the first of the two at the top, under the bar

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
        self.assertIn("_Archive", para, "Help says what archiving does")
        self.note(51, f"{shots} shots (Files › Archived, Health › Archiving, Today's alert card and quiet line, Help; dark at 1400 "
                      f"and 320 px, forced colours at 320 px); "
                      + (f"sideways scroll: {'; '.join(sideways)}" if sideways else "no sideways scroll in any")
                      + (f"; below AA in dark: {'; '.join(sorted(set(low))[:4])}" if low else "; text contrast AA in dark")
                      + "; Help's Archiving paragraph explains Archive them and Move back")
        self.assertEqual(sideways, [], "no sideways scroll")
        self.assertEqual(low, [], "readable in dark mode")


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
