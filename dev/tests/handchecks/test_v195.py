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
        self.screen("settings-people")
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
                self.screen("intake", settle=1)
                problems += self.bottom(f"Intake {w}", "#v-inbox")
            measure.width(b, 1400, 1000)
            self.screen("today", settle=1)
            b.click("[data-prep]")
            b.wait("document.getElementById('prepDlg')&&document.getElementById('prepDlg').open&&document.getElementById('prepBody').children.length", 15)
            b.pump(1)
            problems += self.bottom("Prep popup", "#prepBody")
            for box in ("#prepDlg", "#v-today"):
                problems += self.bottom(f"Prep popup ({box})", box, wheel=False)
            b.eval("document.getElementById('prepDlg').close()")
            title = b.eval("Object.entries(D.hub||{}).find(([t,m])=>m.key==='calendar:hc-1')?.[0]||''")
            self.assertTrue(title, "the FAL Steering committee has a meeting page")
            b.eval(f"go('meeting',{json.dumps(title)})")
            b.wait("/FAL Steering committee/.test((document.querySelector('#v-meeting h1')||{}).textContent||'')", 15)
            b.pump(1)
            problems += self.bottom("Meetings › Prep", "#v-meeting")
        finally:
            measure.width(b, self.width, self.height)
        self.note(22, "; ".join(self.seen))
        self.assertEqual(problems, [], "; ".join(problems))

    # ── BL-10 ──

    def test_c23_due_items_listed(self):
        """23. Make an old closed item: close FAL-A-004 and cancel ORX-R-001; `archive.py items --dry-run` 7 months on → both
        listed. An open action, any decision and any milestone are not."""
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
        """24. Run it again without `--dry-run` → "Archived 2 items". Activity shows one apply (source archive); Review gets
        nothing."""
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
        self.assertTrue(all("archiv" in x.lower() for x in bys),
                        f"Activity names the source as \"{', '.join(bys)}\", not archive: build_dashboard's BY has no entry for "
                        f"archive.py's proposal (change_log.via is its file name), so it falls back to \"Approved in review\"")

    def test_c25_gone_search_health(self):
        """25. Work, Today and the Excel export → those two items are gone. Search for FAL-A-004's words → found, marked
        Archived. Settings › Health › Archiving → "Archived 2 items on DD-MM-YYYY"."""
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
        """26. Turn on "Show archived projects and items" (Settings › Work and views) → both are back, marked. Turn it off."""
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
            marked = {i: bool(x.get("archived")) for i, x in zip((self.ACTION, self.RAID), back)}
            if "Archived" not in row:
                problems.append(f"FAL-A-004's Work row isn't marked Archived (\"{' '.join(row.split())[:90]}\")")
            if not all(marked.values()):
                problems.append(f"the page's records carry no archived flag ({', '.join(k for k, v in marked.items() if not v)}), "
                                "so nothing can mark them")
            catalogue = "Show archived projects and items"
            if where["label"] != catalogue or "views" not in (where["heading"] or "").lower():
                problems.append(f"the switch is \"{where['label']}\" in Settings › {where['heading']}, not \"{catalogue}\" in Work and "
                                f"views (the catalogue's label; the Advanced list leaves it out as covered); its help: "
                                f"\"{where['help'][:80]}\"")
        finally:
            self.show_archived(False)
        gone = b.eval(f"A.some(a=>a.id==={json.dumps(self.ACTION)})||R.some(a=>a.id==={json.dumps(self.RAID)})")
        self.assertFalse(gone, "gone again once it is off")
        self.note(26, "on: both back in Work (FAL-A-004's row with Closed shown); off: gone again" + (f"; {'; '.join(problems)}" if problems else ""))
        self.assertEqual(problems, [], "; ".join(problems))

    def test_c27_edit_unarchives(self):
        """27. Search for FAL-A-004, open it and change its priority → it is live again (back in Work). Activity shows the
        un-archive in its change log."""
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
        """28. Undo the archive apply (Activity › Undo, or `tracker.py undo`) → ORX-R-001 is back, and nothing appears in
        Review."""
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
            if b.eval("!!document.getElementById('actDlgGo')"):
                b.click("#actDlgGo")
                b.pump(2)
            else:
                b.click("#actDlgCancel")
            steps.append(f"ticking the archive's rows in Activity: \"{refused[:160]}\"")
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
        self.screen("settings-advanced", settle=1)
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
            self.screen("settings-advanced", settle=0.5)
            set_raid(6)
        self.note(29, f"Settings › Advanced{(' › ' + heading) if heading else ''}: actions, RAID, promises 6, reports 12; "
                      f"RAID set to 0 in the page (saved to settings.json): the cancelled ORX-005 not listed "
                      f"({len(again)} listed: {', '.join(i for i, _ in again) or 'none'}); set back to 6")

    def test_c30_health_line_card(self):
        """30. Settings › Health → "Archive 4 reports and minutes older than 12 months", with **Archive them**. Press it → the
        change card lists "Move file … → …/_Archive/…" for the FAL weekly report, client report and steering minutes, and the
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
        want = [f"Move file {fal}minutes/2025-09-02 FAL steering minutes.docx → {fal}_Archive/minutes/2025-09-02 FAL steering minutes.docx",
                f"Move file {fal}reports/2025-08-29 Falcon Data Platform weekly report.docx → {fal}_Archive/reports/2025-08-29 Falcon Data Platform weekly report.docx",
                f"Move file {fal}reports/2025-09-05 Falcon Data Platform client report.docx → {fal}_Archive/reports/2025-09-05 Falcon Data Platform client report.docx",
                f"Move file {port}minutes/2025-09-10 Portfolio review minutes.docx → {port}_Archive/minutes/2025-09-10 Portfolio review minutes.docx"]
        self.assertEqual(sorted(lines), sorted(want))
        text = " ".join(lines)
        for never in ("transcript", "data notes", "Orbit Customer App weekly report"):
            self.assertNotIn(never, text)
        b.click("#chat .confirm.edcard [data-ed=reject]")     # check 31 approves it in its own vault; this one leaves it as it was
        b.pump(1)
        self.assertFalse(list((self.vault / fal / "_Archive").glob("*/*")), "nothing moved")
        self.note(30, "Health: \"Archive 4 reports and minutes older than 12 months\" with Archive them; the card: the FAL weekly "
                      "report, client report and steering minutes and the portfolio's minutes, each Move file … → …/_Archive/…; "
                      "not the transcript, the notes or ORX's report; Rejected afterwards (31 approves in its own vault)")


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
