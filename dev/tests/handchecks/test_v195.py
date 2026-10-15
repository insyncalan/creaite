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
p = args[args.index("-p") + 1]
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
    ok, why = call("Read", {"file_path": os.path.join(os.getcwd(), FAL, "_Archive/reports/2025-08-29 Falcon Data Platform weekly report.docx")})
    text = "Here it is." if ok else f"I can't read it: {why}"
elif "archived" in low and "move" in low:
    a, o = f"{FAL}/_Archive/minutes/2025-09-02 FAL steering minutes.docx", f"{FAL}/minutes/2025-09-02 FAL steering minutes.docx"
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
        """The stored path's place below its engagement's (or the portfolio's) own _Archive."""
        parts = stored.split("/")
        return "/".join(parts[:2] + ["_Archive"] + parts[2:])

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
        self.wait_for(lambda: all(self.at(self.archived(f)).is_file() for f in self.DUE), what="the files in _Archive")
        return row, title, lines

    def ensure_archived(self, *stored):
        """The four (or those named) in _Archive: archived through Health and the card if they aren't."""
        if not all(self.at(self.archived(f)).is_file() for f in stored or self.DUE):
            self.archive_via_health()

    def files_archived(self):
        """Files › the Archived chip: [(stored path, tagged Archived, has Move back, name)]."""
        b = self.b
        self.screen("files")
        b.wait("!!document.querySelector('#fquick [data-q=\"archived\"]')", 20)
        b.eval("document.querySelector('#fquick [data-q=\"archived\"]').click()")
        b.pump(0.4)
        return b.eval("[...document.querySelectorAll('#filesTbl tr[data-fp]')].map(tr=>[tr.dataset.fp, "
                      "[...tr.querySelectorAll('.tag')].some(t=>t.textContent.trim()==='Archived'), "
                      "!!tr.querySelector('[data-moveback]'), tr.querySelector('a[data-openfile]').textContent])")

    def move_back(self, stored):
        """Files' Move back on the archived file `stored`; the route's answer."""
        rows = self.files_archived()
        self.assertIn(stored, [r[0] for r in rows], "listed under Archived")
        n = len(self.got("/api/files/move-back"))
        self.b.eval(f"document.querySelector('#filesTbl [data-moveback={json.dumps(stored)}]').click()")
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
        """31. Approve → the files are in `projects/FAL Falcon Data Platform/_Archive/reports/` and `/_Archive/minutes/`, and
        the portfolio's in `projects/_portfolio/_Archive/minutes/`. Nothing is deleted."""
        before = sorted(str(p.relative_to(self.vault)) for p in (self.vault / "projects").rglob("*") if p.is_file())
        self.assertIn(self.WEEKLY, self.search(self.WORD), "before: search finds the weekly report by its word")
        row, title, lines = self.archive_via_health()
        self.assertIn("Archive 4 reports and minutes older than 12 months", row)
        for f in self.DUE:
            self.assertFalse(self.at(f).exists(), f)
            self.assertTrue(self.at(self.archived(f)).is_file(), self.archived(f))
            self.assertIn(f"Move file {f} → {self.archived(f)}", lines)
        self.assertTrue((self.vault / self.FAL / "_Archive/reports").is_dir() and (self.vault / self.FAL / "_Archive/minutes").is_dir())
        self.assertTrue((self.vault / "projects/_portfolio/_Archive/minutes").is_dir())
        for f in self.KEPT:
            self.assertTrue(self.at(f).is_file(), f"kept in place: {f}")
        after = sorted(str(p.relative_to(self.vault)) for p in (self.vault / "projects").rglob("*") if p.is_file())
        moved = {f: self.archived(f) for f in self.DUE}
        self.assertEqual(sorted(moved.get(f, f) for f in before), after, "nothing deleted: every file is where it was or moved")
        self.note(31, f"before: search \"{self.WORD}\" finds the weekly report; "
                      f"Health › Archive them → card \"{title}\" ({len(lines)} moves) → Approve: 4 files in their _Archive "
                      f"(FAL reports ×2, FAL minutes, portfolio minutes); {len(after)} files before and after, none deleted")

    def test_c32_links_not_indexed_guard(self):
        """32. Open FAL's latest-reports link for the moved report → it still opens. Search for its words → not found. In ask
        creaite, "read FAL's archived weekly report" → refused."""
        self.ensure_archived()
        link = self.opened(self.WEEKLY)
        self.assertTrue(link.get("ok"), link)
        self.assertEqual(link.get("path"), str((self.vault / self.archived(self.WEEKLY)).resolve()), "it opens the file in _Archive")
        found = self.search(self.WORD)
        self.assertEqual([f for f in found if "weekly report" in str(f) or "_Archive" in str(f)], [], f"not found: {found}")
        chat = self.ask("read FAL's archived weekly report")
        calls = [c for c in self.guard_calls() if c["tool"] == "Read" and "_Archive" in json.dumps(c["input"])]
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
        """34. Undo → the files are back where they were, and the `_Archive` folders the move made are gone."""
        self.ensure_archived()
        how = self.undo_latest()
        self.wait_for(lambda: all(self.at(f).is_file() for f in self.DUE), what="the files back")
        for f in self.DUE:
            self.assertFalse(self.at(self.archived(f)).exists(), f)
        self.assertFalse((self.vault / self.FAL / "_Archive").exists(), "FAL's _Archive is gone")
        self.assertFalse((self.vault / "projects/_portfolio/_Archive").exists(), "the portfolio's _Archive is gone")
        self.note(34, f"Undo through {how} → 4 files back; both _Archive folders gone")

    def test_c35_archived_chip(self):
        """35. Archive them again (check 30). Files → an **Archived** chip; it lists the four moved files, each tagged Archived
        with **Move back**. No other row in Files has Move back. Clicking a name opens the file."""
        b = self.b
        again = not all(self.at(self.archived(f)).is_file() for f in self.DUE)
        self.ensure_archived()
        rows = self.files_archived()
        self.assertEqual(sorted(r[0] for r in rows), sorted(self.DUE))
        self.assertTrue(all(r[1] and r[2] for r in rows), rows)
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
        b.eval(f"document.querySelector('#filesTbl tr[data-fp={json.dumps(self.STEER)}] a[data-openfile]').click()")
        self.wait_for(lambda: len(self.got("/api/open")) > n, what="/api/open")
        o = self.got("/api/open")[-1]
        self.assertTrue(o.get("ok"), o)
        self.assertEqual(o.get("path"), str((self.vault / self.archived(self.STEER)).resolve()))
        self.note(35, f"{'archived again through Health and the card' if again else 'already archived (check 34 not run)'}; Archived chip lists 4, each tagged Archived with Move back; no Move back under "
                      f"{len(others)} other chips and folders ({sum(v[0] for v in others.values())} rows); clicking the steering "
                      f"minutes' name → /api/open opens it in _Archive")

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
        self.note(36, f"Move back → card \"{title}\", one line \"Move file …/_Archive/reports/… → …/reports/…\" → Approve: "
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
        """38. Undo → the report is back in `_Archive`, unindexed."""
        self.assertTrue(self.at(self.WEEKLY).is_file(), "needs check 36's move back")
        how = self.undo_latest()
        self.wait_for(lambda: self.at(self.archived(self.WEEKLY)).is_file(), what="the report in _Archive again")
        self.assertFalse(self.at(self.WEEKLY).exists())
        found = self.search(self.WORD)
        self.assertEqual([f for f in found if "weekly report" in str(f)], [], f"unindexed: {found}")
        self.assertIn(self.WEEKLY, [x[0] for x in self.files_archived()], "listed under Archived again")
        self.note(38, f"Undo through {how} → in _Archive again, under Archived; search "
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
        self.note(40, "card \"Move file projects/_portfolio/_Archive/minutes/… → projects/_portfolio/minutes/…\" → Approve: back in projects/_portfolio/minutes/"
                      + ("; search finds it again" if self.PORTF in found else f"; search \"{self.PWORD}\": {found}"))

    def test_c41_ask_creaite_refused(self):
        """41. In ask creaite, "move the archived FAL steering minutes back" → refused: "an archived file is moved back from
        Files (Move back), never from ask creaite"."""
        self.ensure_archived(self.STEER)
        seen = len(self.guard_calls())
        chat = self.ask("move the archived FAL steering minutes back")
        self.assertIn("an archived file is moved back from Files (Move back), never from ask creaite", chat)
        self.assertTrue(self.at(self.archived(self.STEER)).is_file(), "still in _Archive")
        self.assertFalse(self.at(self.STEER).exists())
        calls = self.guard_calls()[seen:]
        bash = [c for c in calls if c["tool"] == "Bash"]
        write = [c for c in calls if c["tool"] == "Write"]
        self.assertTrue(bash and bash[-1]["exit"] == 2, f"filechange.py move on _Archive refused by the hook: {bash}")
        self.note(41, "ask creaite: filechange.py move refused by the guard hook (exit 2); the move-back spec written in drafts "
                      f"({'allowed' if write and write[-1]['exit'] == 0 else 'refused'}) and named on a CHANGE line → the server's "
                      "card refuses it: \"…never from ask creaite\"; the minutes stay in _Archive (stand-in Claude)")


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
