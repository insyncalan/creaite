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
    """Phase 2: BL-334 alerts read the conversation (42 to 47) and BL-316's consistency (49, 50). Own vault.

    42 to 47 build on each other, as the hand checks do: `ensure(step)` records (or does) each earlier step once, so any of
    them runs on its own with --only. Recording is the check's own command (`sweep.py vip record <file> --found sweep`,
    hcbase.vip_found) with the clock at the time the check names, so "updated HH:MM" is that time (the card says when it was
    recorded, which by hand is when the tester ran the command)."""
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
        order = {"first": (8, 40, [lambda: self.falcon()]),
                 "quiet": (8, 45, [lambda: self.falcon(), self.hello]),
                 "update": (9, 5, [lambda: self.falcon(later=True), self.hello])}
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
            cands:[...li.querySelectorAll('.tdcand')].map(c=>({tag:c.querySelector('.tdctag').textContent, t:c.querySelector('.ct').textContent,
              buttons:[...c.querySelectorAll('button')].map(x=>[x.dataset.alertdo, x.dataset.cand, x.getAttribute('aria-label')||x.dataset.tip||''])}))})); })()""")

    def falcon_cards(self):
        return [c for c in self.page_card() if c["title"] == "Falcon go-live"]

    @staticmethod
    def labels(cand):
        return [x[0] for x in cand["buttons"]]

    def test_c42_one_card_per_conversation(self):
        """42. Today → one card titled "Falcon go-live" (not "Group chat"), "updated 08:40", the summary, and two candidates,
        each with **Create work item** and **Dismiss**. The project is Falcon Data Platform, matched from the title."""
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
        self.assertEqual(c["rowButtons"], 0, "the buttons are per item")
        a = self.alert()
        self.assertEqual(a["p"], "FAL", "matched from the title")
        names = [x[2] for x in c["cands"][0]["buttons"]]
        self.note(42, f"card \"{c['title']}\", updated 08:40 (recorded at 08:40), Falcon Data Platform (p=FAL); "
                      f"Action + Decision, each {' / '.join(n.split(':')[0] for n in names)}")

    def test_c43_quiet_line(self):
        """43. A second conversation titled "Group chat" with nothing in it → one quiet line ("… : nothing for you"), with no
        buttons and no count. Its title is the people in it, never "Group chat"."""
        self.ensure("quiet")
        b = self.b
        quiet = b.eval("""[...document.querySelectorAll('#tdList>li.td-quiet')].map(li=>({text:li.textContent.replace(/\\s+/g,' ').trim(),
          buttons:li.querySelectorAll('button').length, tag:!!li.querySelector('.tdtag')}))""")
        self.assertEqual(len(quiet), 1, quiet)
        q = quiet[0]
        self.assertIn("Rashid Al Suwaidi with Lena Fischer: nothing for you", q["text"])
        self.assertEqual(q["buttons"], 0, "no buttons")
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
        self.note(43, f"\"{q['text']}\", 0 buttons; title in vip.json \"{a['title']}\"; Today's count {rail or '0'} (the card only)")

    def test_c44_same_card_updated(self):
        """44. Record the first conversation again at 09:05 with a third item → the same card is updated ("updated 09:05", three
        candidates). No second card."""
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
        self.note(44, "same alert id, updated 09:05, Action + Decision + Risk; one card")

    def test_c45_dismiss_create(self):
        """45. Dismiss the risk → it goes; nothing in Review. Create work item on the action → one proposal in Review, for
        Falcon Data Platform."""
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
        rev = b.eval("document.getElementById('v-review').innerText")
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
            for o, bad in d.each_opener(name, lambda i, o: d.drive(i, o["kind"])):
                n_open += 1
                if bad:
                    keys.add((tsb.screen_area(name), f"keys: {name} {o['sig']} “{o['name']}”: {'; '.join(bad)}"))
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
