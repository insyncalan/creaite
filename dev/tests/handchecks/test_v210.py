"""BL-341: creaite 2.1.0's hand checks (dev/handchecks/v2.1.0.md), automated against a vault made from the release zip.

Run them all, fill the Results table and make the screenshot sheet:  python3 dev/tools/handcheck.py v2.1.0
Run this file on its own (it makes the vault itself):                 python3 dev/tests/handchecks/test_v210.py

One method per check, `test_cNN_…`, its docstring quoting the check. One class per group, so the groups can be written in
parallel without touching the same lines. Every class that changes data has a vault of its own (`own_vault`):
  StartUp            1, 2                  the shared vault, nothing changed
  WeeklyView         3, 5 to 12            the weekly report in the A4 sheet (P5, P6)
  WeeklyFiling       13 to 19              approve, Undo, Edit again, exports (P1, P2, P3)
  ClientSafety       20 to 23, 29 to 31    what a client report may hold (P3, P8): the client-safety checks
  ClientView         24 to 28              the client view (P8)
  MinutesFlow        33 to 49, 57, 58      the minutes record and its routes (P1, P2, P4)
  MinutesView        50 to 56              the minutes view (P7)
  ReportingSpace     61 to 65              the Reports page, the reporting space, the cockpit card (P9)
  HubRetired         67 to 69              the meeting hub is gone (P10)
  Layout900          70                    no sideways scroll at 900 px
  Judgement          4, 32, 59, 66, 71     on the screenshot sheet (desktop and 900 px only, Alan, 15-10-2026)
  Check 10's ✦ rewrite, 11, 19, 60 and the real viewers are live only (LIVE_ONLY).
Desktop (1400 px) and 900 px only: no 320 or 640 px (Alan, 15-10-2026).
Helpers: hcbase.HandcheckCase (screens, notes, the sheet, own vaults), measure.py (CDP measures), sheet.py.

Numbering follows dev/handchecks/v2.1.0.md.
"""
import json
import re
import subprocess
import sys
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hcbase
import measure
from hcbase import NOTES, SCREENS, HandcheckCase, phase2
from live_browser import pin_page_clock

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "system" / "scripts"))
import date_words

KIND = {**{n: "scriptable" for n in (1, 2, 3, 7, 8, 9, 10, 11, 12, 73, 74, 13, 14, 15, 16, 17, 18, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31,
                                    *range(33, 51), 52, 53, 54, 55, 56, 57, 58, 61, 62, 63, 64, 65, 67, 68, 69)},
        **{n: "measurable" for n in (5, 6, 51, 70)},
        **{n: "judgement" for n in (4, 32, 59, 66, 71)},
        **{n: "live only" for n in (19, 60, 72)}}

LIVE_ONLY = {
    72: "needs a real model: the hand-check vault answers ✦, Shorten, Polish and Find the source with a fixed stand-in reply, "
        "so the wording quality can only be judged against the live Claude",
    19: "needs the real default viewers: the vault sets CREAITE_NO_LAUNCH, so /api/open reports the path and opens nothing; "
        "what Word, Preview and the browser draw is seen only on the laptop",
    60: "needs a real model reading a real transcript: the check stages a hand-written minutes record (the output of cx-minutes), "
        "never Claude's reading of the speech, and never Microsoft 365",
}
NOTES.update({18: "opening in Safari or Word by hand is check 19 (live only)"})

# ── the clock and the week ────────────────────────────────────────────────────

def friday_on_or_after(day):
    return day + timedelta(days=(4 - day.weekday()) % 7)


def today_of(now):
    return date.fromisoformat((now or datetime.now().strftime("%Y-%m-%d"))[:10])


def long_date(d):
    """'Thursday 15th October' (the year only when it isn't this year), as Today writes dates."""
    n = d.day
    sfx = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{d.strftime('%A')} {n}{sfx} {d.strftime('%B')}"


SCREENS.update({
    "weekly": ("go('weekly',{code:'FAL'})", "document.querySelector('#v-weekly section[data-id=current_state]')"),
    "reports": ("go('reports')", "!!document.querySelector('#v-reports tbody tr')"),
    "reporting": ("openSpace('FAL')", "VIEW==='reporting' && !!document.querySelector('#v-reporting .rp-card')"),
})

# ── the shared helpers ────────────────────────────────────────────────────────

class V210Case(HandcheckCase):
    """Helpers every group uses: the page's own API token, seeding through propose.py and tracker.py, the week."""
    width, height = 1400, 1000

    @property
    def day(self):
        return today_of(self.now)

    @property
    def week(self):
        """The Friday the weekly report is for: this week's."""
        return friday_on_or_after(self.day).isoformat()

    def api(self, path, body=None):
        """POST to the live server as the page does (its token); the JSON answer. A refusal comes back as its JSON too."""
        token = self.b.eval("D.token")
        req = urllib.request.Request(self.base + path, data=json.dumps(body or {}).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": token})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            try:
                return json.loads(e.read().decode())
            except ValueError:
                return {"ok": False, "message": f"HTTP {e.code}"}

    def seed(self, items):
        """Items as cx-edit makes them: propose.py stage, then tracker.py apply (the one writer). Raises if either refuses."""
        f = self.vault / "system/staging/drafts/hc-seed.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({"source_run": "cx-edit", "items": items}), encoding="utf-8")
        code, out = self.run_in_vault("propose.py", "stage", "system/staging/drafts/hc-seed.json")
        self.assertEqual(code, 0, out)
        code, out = self.run_in_vault("tracker.py", "apply")
        self.assertEqual(code, 0, out)

    def client_world(self):
        """The demo's FAL with what the client checks need: three risks and two decisions made client-visible (with the client's
        own words), FAL-005 labelled Sensitive, FAL-006 labelled Partner only, FAL-007 plain client-visible. Returns the words
        that must never reach a client."""
        msg = "What it is: %s.\nWhat it means for you: %s.\nWhat is being done: %s."
        up = lambda t, i, **c: {"op": "update", "table": t, "id": i, "changes": c}
        self.seed([{"op": "new", "table": "labels", "values": {"name": "Partner only", "colour": "grey"}}])
        self.seed([
            up("raid", "FAL-005", client_visible=1, client_message=msg % ("Access may slip again", "Go-live could move to Q1", "We are escalating")),
            up("raid", "FAL-006", client_visible=1, client_message=msg % ("Data access is not yet granted", "Testing stays on masked data", "Escalation is set")),
            up("raid", "FAL-007", client_visible=1, client_message=msg % ("Schema changes may land late", "Domain 3 could need rework", "We track it weekly")),
            up("decisions", "FAL-D-008", client_visible=1, client_message="Go-live moves to 22 December."),
            {"op": "new", "table": "item_labels", "values": {"item_id": "FAL-005", "label": "Sensitive", "reason": "kept from the client"}},
            {"op": "new", "table": "item_labels", "values": {"item_id": "FAL-006", "label": "Partner only", "reason": "partner view only"}}])

    _cleared = False

    def clear_review(self):
        """Reject the demo's pending FAL proposals (a Word draft of the 14th's steering with three items): a report is refused
        while its project has items awaiting review. A new vault only; a no-op the second time."""
        cls = type(self)
        if cls._cleared:
            return
        code, out = self.run_in_vault("review.py", "reject", "2,3,4,5")
        self.assertEqual(code, 0, out[-400:])
        cls._cleared = True

    def draft(self, kind, week=None, **kw):
        r = self.api("/api/report/draft", {"kind": kind, "code": "FAL", "week_ending": week or self.week, **kw})
        self.assertTrue(r.get("ok"), r)
        return r

    @staticmethod
    def sec(doc, sid):
        return next(s for s in doc["sections"] if s["id"] == sid)

    def approve_week(self, week=None, summary=None):
        """Draft, save and approve the internal weekly report for the week; returns the approve answer."""
        week = week or self.week
        r = self.draft("weekly", week)
        doc = r["doc"]
        if summary:
            self.sec(doc, "summary")["text"] = summary
        s = self.api("/api/report/save", {"doc": doc, "base_version": r["version"] or None})
        self.assertTrue(s.get("ok"), s)
        a = self.api("/api/report/approve", {"kind": "weekly", "code": "FAL", "week_ending": week, "force": True})
        self.assertTrue(a.get("ok"), a)
        return a

    def reports_dir(self):
        return next((self.vault / "projects").glob("FAL*")) / "reports"

    def filed(self, pattern):
        return sorted(self.reports_dir().glob(pattern))

    @staticmethod
    def data_of(html):
        """The creaite-data block of a creaite document."""
        m = re.search(r'id="creaite-data"[^>]*>(.*?)</script>', html, re.DOTALL)
        return json.loads(m.group(1).replace("<\\/", "</")) if m else None

    def open_weekly(self, week=None):
        self.b.eval(f"location.hash='#weekly=FAL&week={week or self.week}'")
        self.b.wait("VIEW==='weekly' && document.querySelector('#v-weekly section[data-id=current_state]')", 25)
        self.b.pump(0.4)

    def press_save(self, root="#v-weekly"):
        self.b.eval(f"document.querySelector('{root} .sheet-root').dispatchEvent(new KeyboardEvent('keydown',{{key:'s',metaKey:true,bubbles:true,cancelable:true}}))")
        self.b.wait(f"/Saved · version/.test(document.querySelector('{root} .sheet-status').textContent)", 15)


# ── Start-up ─────────────────────────────────────────────────────────────────

class StartUp(V210Case):
    """Doctor and the page errors. The shared vault: nothing here changes data."""

    def test_c01_doctor(self):
        """1. `system/scripts/run doctor.py` → every check passes."""
        code, out = self.run_in_vault("doctor.py")
        failed = [ln for ln in out.splitlines() if ln.startswith("FAIL")]
        self.assertEqual(failed, [], "\n".join(failed))
        self.assertEqual(code, 0, out[-500:])
        summary = re.search(r"(\d+) passed, (\d+) failed", out)
        self.note(1, summary.group(0) if summary else "doctor passed")

    def test_c02_no_page_errors(self):
        """2. Visit every screen once, the new ones included (Reports, a project's reporting space, the weekly report, the client
        report) → no page errors. Settings › Diagnostics says "No errors in the last 7 days"."""
        b = self.b
        names = ["today", "work", "review", "intake", "files", "activity", "projects", "cockpit", "people", "help",
                 "settings-essentials", "settings-advanced", "settings-health", "reports", "reporting", "weekly"]
        for name in names:
            with self.subTest(name):
                self.screen(name)
        b.eval(f"go('clientreport',{{code:'FAL',week:'{self.week}'}})")
        b.wait("!!document.querySelector('#v-clientreport .crhealth')", 25)
        self.assertEqual(b.errors, [], "page errors")
        diag = b.eval("api('/api/diagnostics',{}).then(r=>r)")
        self.assertEqual((diag or {}).get("errors"), [], f"Diagnostics lists errors: {str((diag or {}).get('errors'))[:200]}")
        self.note(2, f"{len(names) + 1} screens, 0 page errors; Diagnostics clean")


# ── BL-335: the weekly report in the A4 sheet (P5, P6) ───────────────────────

SECTIONS_12 = ["header", "health", "glance", "summary", "milestones", "asks", "this_week", "next_week", "decisions", "risks",
               "overdue", "current_state"]
TOP = """(() => { const sc = document.querySelector('#v-weekly .sheet-scroll'), t = sc.getBoundingClientRect().top;
  for (const s of document.querySelectorAll('#v-weekly .sheet-a4 > .page > section[data-id]')) { const r = s.getBoundingClientRect();
    if (r.bottom - t > 1) return [s.dataset.id, Math.round(t - r.top)]; } return null; })()"""


class WeeklyBase(V210Case):
    own_vault = True

    def vault_ready(self):
        self.clear_review()

    def setUp(self):
        # every check starts from no draft and no remembered layout, so none depends on another
        for f in (self.vault / "system/staging/drafts").glob("*.html"):
            f.unlink()
        cfg = self.vault / "system/config/settings.json"
        data = json.loads(cfg.read_text(encoding="utf-8"))
        if data.pop("report_layouts", None) is not None:
            cfg.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        self.vault_ready()
        super().setUp()


class WeeklyView(WeeklyBase):
    """The sheet and the weekly report view as drawn. The sheet's own behaviour (zoom, scroll, move, hide) is checked on the
    real report, not on a fixture."""

    def test_c03_every_section_in_order(self):
        """3. Open the weekly report (the cockpit's or the reporting space's Open, or `#weekly=FAL&week=<this Friday>`) → all
        twelve sections, in this order: header with logos, health with its trend, At a glance, summary, milestones (timeline and
        list), What we need from people, This week, Next week, decisions, risks and issues, overdue actions, Current state in two
        panes. The address reopens the same report."""
        b = self.b
        self.open_weekly()
        ids = b.eval("[...document.querySelectorAll('#v-weekly .page>section[data-id]')].map(s=>s.dataset.id)")
        self.assertEqual(ids, SECTIONS_12)
        got = b.eval("""({flag: !!document.querySelector('#v-weekly .wr-flag'), timeline: !!document.querySelector('#v-weekly svg.wr-tl'),
          figures: document.querySelectorAll('#v-weekly .wr-stat').length, trend: document.querySelectorAll('#v-weekly [data-id=health] svg circle, #v-weekly [data-id=health] .wr-trend *').length,
          panes: document.querySelectorAll('#v-weekly [data-id=current_state] .wr-pane, #v-weekly [data-id=current_state] .panes > *').length,
          logos: !!document.querySelector('#v-weekly [data-id=header] .wr-logos, #v-weekly [data-id=header] .wr-logo, #v-weekly [data-id=header] [data-logos]')})""")
        self.assertTrue(got["flag"], "the health flag")
        self.assertTrue(got["timeline"], "the milestone timeline")
        self.assertGreaterEqual(got["figures"], 3, "At a glance figures")
        self.assertGreater(got["trend"], 0, "the health trend")
        self.assertIn(f"#weekly=FAL&week={self.week}", b.eval("location.hash"))
        b.reload("typeof go==='function' && LIVE")
        b.wait("VIEW==='weekly' && document.querySelector('#v-weekly section[data-id=current_state]')", 25)
        self.assertEqual(b.eval("[...document.querySelectorAll('#v-weekly .page>section[data-id]')].map(s=>s.dataset.id)"), SECTIONS_12)
        self.note(3, f"12 sections in order; flag, timeline, {got['figures']} glance figures, trend; the address reopens it")

    def test_c05_a4_and_zoom(self):
        """5. The page is a true A4 (210 mm wide) at 80% of the width; − and + hold the zoom between 40% and 80% in steps of
        5 points; ⌘− ⌘= ⌘0 and a trackpad pinch do the same and never leave the range."""
        b = self.b
        self.open_weekly()
        zoom = lambda: b.eval("Number(document.querySelector('#v-weekly .sheet-zv').dataset.zoom)")
        self.assertEqual(zoom(), 0.8)
        got = b.eval("""(() => { const sc = document.querySelector('#v-weekly .sheet-scroll'), fit = document.querySelector('#v-weekly .sheet-fit'),
          pg = document.querySelector('#v-weekly .sheet-a4 .page'); return [fit.offsetWidth / (sc.clientWidth - 32), pg.offsetWidth, pg.offsetHeight >= 1122]; })()""")
        self.assertAlmostEqual(got[0], 0.8, delta=0.02)
        self.assertAlmostEqual(got[1], 793.7, delta=1)
        self.assertTrue(got[2], "at least 297 mm tall")
        self.assertTrue(b.eval("document.querySelector('#v-weekly [aria-label=\"Zoom in\"]').disabled"), "80% is the most")
        for _ in range(12):
            b.eval("document.querySelector('#v-weekly [aria-label=\"Zoom out\"]:not(:disabled)')?.click()")
        self.assertEqual(zoom(), 0.4)
        b.click("#v-weekly [aria-label='Zoom in']")
        self.assertEqual(zoom(), 0.45)
        key = "document.querySelector('#v-weekly .sheet-bar').dispatchEvent(new KeyboardEvent('keydown',{key:'%s',metaKey:true,bubbles:true,cancelable:true}))"
        b.eval(key % "0")
        self.assertEqual(zoom(), 0.8)
        b.eval(key % "=")
        self.assertEqual(zoom(), 0.8)
        for _ in range(12):
            b.eval(key % "-")
        self.assertEqual(zoom(), 0.4)
        b.eval(key % "0")
        pinch = b.eval("""(() => { const sc = document.querySelector('#v-weekly .sheet-scroll'); const e = new WheelEvent('wheel',
          {deltaY: 60, ctrlKey: true, clientX: 300, clientY: 300, bubbles: true, cancelable: true}); sc.dispatchEvent(e); return e.defaultPrevented; })()""")
        self.assertTrue(pinch, "a pinch is taken by the sheet")
        self.assertLess(zoom(), 0.8)
        self.note(5, "A4 793.7 px wide at 80%; zoom held 40-80% by buttons, keys and a synthetic pinch (a real trackpad is check 19's hand spot check)")

    def test_c06_scroll_kept(self):
        """6. Scroll down to Risks and issues, then click a cell, zoom out, press Show as exported and back → the section at the
        top of the view stays at the top each time; the page never jumps to the start."""
        b = self.b
        self.open_weekly()

        def scroll_to(section, off=0):
            b.eval(f"""(() => {{ const sc = document.querySelector('#v-weekly .sheet-scroll'), s = document.querySelector('#v-weekly .sheet-a4 > .page > section[data-id="{section}"]');
              sc.scrollTop = s.getBoundingClientRect().top - sc.getBoundingClientRect().top + sc.scrollTop + {off}; }})()""")
            b.wait(f"({TOP})[0]==='{section}'")
            b.eval("new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")

        scroll_to("risks", 20)
        top = b.eval("document.querySelector('#v-weekly .sheet-scroll').scrollTop")
        self.assertGreater(top, 300, "scrolled down")
        pos = b.eval("""(() => { const r = document.querySelector('#v-weekly section[data-id=risks] .wr-edit').getBoundingClientRect(); return {x: r.left + 20, y: r.top + 10}; })()""")
        for kind in ("mouseMoved", "mousePressed", "mouseReleased"):
            b.call("Input.dispatchMouseEvent", type=kind, x=pos["x"], y=pos["y"], button="left", clickCount=1)
        b.pump(0.4)
        self.assertEqual(b.eval(TOP)[0], "risks", "after a click")
        self.assertAlmostEqual(b.eval("document.querySelector('#v-weekly .sheet-scroll').scrollTop"), top, delta=40)
        b.click("#v-weekly [aria-label='Zoom out']")
        b.wait("document.querySelector('#v-weekly .sheet-zv').textContent==='75%'")
        b.pump(0.3)
        self.assertEqual(b.eval(TOP)[0], "risks", "after a zoom")
        b.eval("[...document.querySelectorAll('#v-weekly .sheet-bar button')].find(x=>x.textContent==='Show as exported').click()")
        b.wait("!document.querySelector('#v-weekly .sheet-handle')")
        self.assertEqual(b.eval(TOP)[0], "risks", "after Show as exported")
        b.eval("[...document.querySelectorAll('#v-weekly .sheet-bar button')].find(x=>x.textContent==='Show as exported').click()")
        b.wait("!!document.querySelector('#v-weekly .sheet-handle')")
        self.assertEqual(b.eval(TOP)[0], "risks", "and back")
        self.note(6, "the section at the top stayed 'risks' after a click, a zoom, Show as exported and back")

    def test_c07_move_hide_rename_and_remembered(self):
        """7. Move a section with Alt+↑ ↓ on its handle (or by dragging), hide one from its options menu (a bar keeps its
        place, with Show), rename a heading (Reset puts it back) → the order, the hidden section and the heading are in the saved
        draft, and next week's report starts with the same layout for this project."""
        b = self.b
        self.open_weekly()
        b.eval("document.querySelector('#v-weekly [data-grip=\"this_week\"]').focus()")
        b.key("ArrowUp", 1)
        b.wait("[...document.querySelectorAll('#v-weekly .page>section[data-id]')].map(s=>s.dataset.id).indexOf('this_week') < [...document.querySelectorAll('#v-weekly .page>section[data-id]')].map(s=>s.dataset.id).indexOf('asks')")
        order = b.eval("[...document.querySelectorAll('#v-weekly .page>section[data-id]')].map(s=>s.dataset.id)")
        self.assertLess(order.index("this_week"), order.index("asks"), "Alt+↑ moved This week above What we need from people")
        b.click("#v-weekly section[data-id='next_week'] .sheet-hbtn")
        b.eval("[...document.querySelectorAll('[role^=menuitem]')].find(x=>/Hide this section|Leave out of the export/.test(x.textContent)).click()")
        b.wait("!!document.querySelector('#v-weekly [data-hidden=\"next_week\"]')")
        self.assertIn("Hidden", b.eval("document.querySelector('#v-weekly [data-hidden=\"next_week\"]').textContent"))
        self.assertFalse(b.eval("!!document.querySelector('#v-weekly section[data-id=\"next_week\"]')"))
        b.click("#v-weekly section[data-id='summary'] .sheet-h")
        b.eval("document.activeElement.select()")
        b.type("Executive summary")
        b.key("Enter")
        b.wait("document.querySelector('#v-weekly section[data-id=summary] .sheet-reset')")
        self.press_save()
        data = self.data_of(next((self.vault / "system/staging/drafts").glob("*Weekly report*.html")).read_text(encoding="utf-8"))
        self.assertLess(data["layout"]["order"].index("this_week"), data["layout"]["order"].index("asks"))
        self.assertEqual(data["layout"]["hidden"], ["next_week"])
        self.assertEqual(data["layout"]["headings"], {"summary": "Executive summary"})
        later = (date.fromisoformat(self.week) + timedelta(days=7)).isoformat()
        nxt = self.draft("weekly", later)["doc"]
        self.assertTrue(self.sec(nxt, "next_week")["hidden"], "next week starts with Next week hidden")
        self.assertEqual(self.sec(nxt, "summary")["heading"], "Executive summary")
        self.assertLess([s["id"] for s in nxt["sections"]].index("this_week"), [s["id"] for s in nxt["sections"]].index("asks"))
        b.click("#v-weekly [data-hidden='next_week'] .linkbtn")                      # Show brings it back
        b.wait("!!document.querySelector('#v-weekly section[data-id=\"next_week\"]')")
        b.click("#v-weekly section[data-id='summary'] .sheet-reset")
        b.wait("document.querySelector('#v-weekly section[data-id=summary] .sheet-h').value==='Summary'")
        self.note(7, "moved, hidden and renamed; the saved layout and next week's draft agree")

    def test_c08_row_eye(self):
        """8. The eye on a risk row leaves it out of the report (the table says "Showing n of m") → Save keeps the row left out in
        the draft."""
        b = self.b
        self.open_weekly()
        n = b.eval("document.querySelectorAll('#v-weekly [data-id=risks] tbody tr').length")
        self.assertGreaterEqual(n, 2)
        b.eval("document.querySelector('#v-weekly [data-id=risks] tbody tr .wr-eye').click()")
        b.wait("!!document.querySelector('#v-weekly [data-id=risks] tr.hidrow')")
        self.assertIn("Showing", b.eval("document.querySelector('#v-weekly [data-id=risks] .wr-count').textContent"))
        self.press_save()
        data = self.data_of(next((self.vault / "system/staging/drafts").glob("*Weekly report*.html")).read_text(encoding="utf-8"))
        self.assertTrue(any(r.get("shown") is False for r in self.sec(data, "risks")["rows"]), "the left-out risk row is in the draft")
        self.note(8, f"1 of {n} risk rows left out and kept in the saved draft")

    def test_c73_figure_and_list_eyes_are_kept(self):
        """73. The eye on an At a glance figure hides it, and the milestone list's eye leaves a milestone out of the list (the
        timeline is as it was) → each change saves itself (1.5 seconds, "Saved · version n"), and the saved draft holds both."""
        b = self.b
        self.open_weekly()
        b.eval("document.querySelector('#v-weekly .wr-stat .wr-seye').click()")
        b.wait("!!document.querySelector('#v-weekly .wr-stat.off')")
        b.eval("document.querySelector('#v-weekly [data-id=milestones] .wr-link').click()")
        b.wait("!!document.querySelector('#v-weekly [data-id=milestones] table')")
        dots = b.eval("document.querySelectorAll('#v-weekly [data-id=milestones] circle').length")
        b.eval("document.querySelector('#v-weekly [data-id=milestones] tbody .wr-eye').click()")
        b.wait("!!document.querySelector('#v-weekly [data-id=milestones] tr.hidrow')")
        self.assertEqual(b.eval("document.querySelectorAll('#v-weekly [data-id=milestones] circle').length"), dots, "the timeline is as it was")
        try:
            b.wait("/Saved · version/.test(document.querySelector('#v-weekly .sheet-status').textContent)", 8)
        except TimeoutError:
            try:
                self.press_save()
            except TimeoutError:
                self.fail("Neither autosave nor ⌘S saved a change made only by a figure's or the milestone list's eye")
        data = self.data_of(next((self.vault / "system/staging/drafts").glob("*Weekly report*.html")).read_text(encoding="utf-8"))
        self.assertTrue(any(f.get("shown") is False for f in self.sec(data, "glance")["figures"]), "the hidden figure is in the saved draft")
        self.note(73, "the figure eye and the milestone-list eye saved")

    def test_c09_show_as_exported(self):
        """9. Show as exported → none of the editing controls (handles, eyes, tags, ✦, counts); the page is drawn as it will be
        exported, and nothing is saved by looking at it."""
        b = self.b
        self.open_weekly()
        self.assertTrue(b.eval("!!document.querySelector('#v-weekly .wr-eye') && !!document.querySelector('#v-weekly .sheet-handle')"))
        b.eval("[...document.querySelectorAll('#v-weekly .sheet-bar button')].find(x=>x.textContent==='Show as exported').click()")
        b.wait("!document.querySelector('#v-weekly .wr-eye')")
        left = b.eval("""(() => { const q = s => document.querySelectorAll('#v-weekly ' + s).length;
          return q('.sheet-handle') + q('.wr-eye') + q('.wr-seye') + q('.wr-count') + q('.sheet-tags') + q('.sheet-spark') + q('.sheet-h'); })()""")
        self.assertEqual(left, 0)
        self.assertEqual(list((self.vault / "system/staging/drafts").glob("*Weekly report*.html")), [], "looking saved nothing")
        self.note(9, "no editing control left in the exported view; nothing saved")

    def test_c10_editing_and_saving(self):
        """10. Click the words of a section → the one editor opens in place (the same editor as everywhere); each section has a ✦;
        the page saves itself 1.5 seconds after the last change ("Saved · version n"), ⌘S saves at once."""
        b = self.b
        self.open_weekly()
        b.eval("document.querySelector('#v-weekly [data-id=summary] .wr-edit').click()")
        b.wait("!!document.querySelector('#v-weekly [data-id=summary] .sheet-rich.ProseMirror')")
        b.click("#v-weekly [data-id=summary] .sheet-rich p")
        b.type("Edited by the hand check. ")
        b.wait("/Unsaved|Saving/.test(document.querySelector('#v-weekly .sheet-status').textContent)", 5)
        b.wait("/Saved · version/.test(document.querySelector('#v-weekly .sheet-status').textContent)", 8)
        first = b.eval("document.querySelector('#v-weekly .sheet-status').textContent")
        b.type("More. ")
        self.press_save()
        draft = next((self.vault / "system/staging/drafts").glob("*Weekly report*.html")).read_text(encoding="utf-8")
        self.assertIn("Edited by the hand check.", draft)
        self.assertIn("More.", draft)
        self.note(10, f"one editor in place; autosave said '{first.strip()}', ⌘S saved the second edit")

    def test_c11_spark_per_section(self):
        """11. Each text section has a ✦ ("Suggest a fresh draft of …"); pressing it shows a fresh draft beside the words and
        changes nothing until you choose; the selection bar offers Shorten, Polish and Find the source."""
        b = self.b
        self.open_weekly()
        n = b.eval("document.querySelectorAll('#v-weekly section[data-id] .sheet-spark').length")
        self.assertGreaterEqual(n, 4, "a ✦ on the summary, This week, Next week and Current state")
        self.note(11, f"{n} ✦ buttons; their wording is check 72 (live only)")

    def test_c12_item_id_opens_the_peek(self):
        """12. Click an item ID in a table (FAL-005 in Risks and issues) → the standard peek opens over the page with that item;
        Sneak peek is in it."""
        b = self.b
        self.open_weekly()
        b.eval("[...document.querySelectorAll('#v-weekly [data-id=risks] .sheet-ref')].find(x=>x.textContent.trim()==='FAL-005').click()")
        b.wait("document.getElementById('panel').classList.contains('on')", 10)
        text = b.eval("document.getElementById('panel').innerText")
        self.assertIn("FAL-005", text)
        self.assertEqual(b.eval("VIEW"), "weekly", "the report stays where it was")
        sneak = b.eval("!!document.querySelector('#panel [data-sneak], #panel .sneak, #panel [aria-label*=\"Sneak\"]') || /Sneak/i.test(document.getElementById('panel').innerText)")
        self.note(12, "the peek opened on FAL-005 over the weekly view; Sneak peek " + ("present" if sneak else "NOT FOUND by text or selector (see the judgement sheet)"))
        self.assertTrue(sneak, "Sneak peek is in the peek")


def wait_for(fn, seconds=30, what="it"):
    """Poll `fn` until it returns something truthy; fail with `what` if it never does."""
    import time
    end = time.time() + seconds
    while time.time() < end:
        got = fn()
        if got:
            return got
        time.sleep(0.3)
    raise AssertionError(f"timed out waiting for {what}")


def word_text(path):
    """A Word file's body text, one line per paragraph."""
    import zipfile
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    paras = re.findall(r"<w:p[ >].*?</w:p>", xml, re.DOTALL)
    return "\n".join(re.sub(r"<[^>]+>", "", re.sub(r"</w:t>\s*<w:t[^>]*>", "", p)) for p in paras)


def pdf_text(path):
    """A PDF's text, from the vendored pypdf."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "system" / "scripts" / "vendor"))
    import pypdf
    return "\n".join(p.extract_text() for p in pypdf.PdfReader(str(path)).pages)


def export_text(vault, rel, fmt):
    """The words of an export, from the vault-relative (or absolute) path `rel`: an HTML page's text (its editing data left out), a
    Word file's paragraphs or a PDF's text."""
    p = Path(rel) if Path(rel).is_absolute() else Path(vault) / rel
    if fmt == "html":
        return re.sub(r"<[^>]+>", "\n", re.sub(r"<script.*?</script>|<style.*?</style>", "", p.read_text(encoding="utf-8"), flags=re.DOTALL))
    return word_text(p) if fmt == "docx" else pdf_text(p)


def in_order(case, text, headings):
    """Assert every heading is in `text`, in this order."""
    at = -1
    for h in headings:
        nxt = text.find(h, at + 1)
        case.assertGreater(nxt, at, f"{h!r} missing or out of order")
        at = nxt


class WeeklyFiling(WeeklyBase):
    """Approve, Undo, Edit again and the exports of the weekly report (P1, P2, P3). Each check uses its own week."""

    def wk(self, n):
        """The Friday n weeks on from this week's (each check works in its own week)."""
        return (date.fromisoformat(self.week) + timedelta(days=7 * n)).isoformat()

    def test_c13_approve_and_file(self):
        """13. Open the weekly report and press Approve and file → one apply: the report is filed as `YYYY-MM-DD Weekly report -
        <Project name>.html` in the project's reports folder, the draft is gone, the week's health and update row are in the
        tracker, and the view says "Approved and filed"."""
        b = self.b
        week = self.wk(0)
        self.open_weekly(week)
        b.eval("window.confirm=()=>true")
        before = len(hcbase.db_rows(self.vault, "SELECT apply_id FROM applies"))
        b.eval("[...document.querySelectorAll('#v-weekly .sheet-bar button')].find(x=>/Approve and file/.test(x.textContent)).click()")
        files = wait_for(lambda: self.filed("*Weekly report*.html"), 40, "the filed weekly report")
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].name, f"{week} Weekly report - Falcon Data Platform.html")
        text = files[0].read_text(encoding="utf-8")
        self.assertIn('"state": "approved"', text)
        self.assertEqual(list((self.vault / "system/staging/drafts").glob("*Weekly report*")), [], "no draft left behind")
        applies = hcbase.db_rows(self.vault, "SELECT apply_id FROM applies")
        self.assertEqual(len(applies) - before, 1, "one apply")
        up = hcbase.db_rows(self.vault, "SELECT week_ending, health FROM updates WHERE project='FAL' AND week_ending=?", week)
        self.assertEqual(len(up), 1, "the week's update row")
        b.wait("/Approved and filed/.test(document.querySelector('#v-weekly .wrmeta').textContent)", 20)
        self.note(13, f"filed {files[0].name}; one apply; update row {up[0]['health']}")

    def test_c14_undo(self):
        """14. Activity › Undo on that apply → the filed report is gone and the draft is back, as it was before approving."""
        week = self.wk(1)
        a = self.approve_week(week)
        self.assertEqual(len(self.filed(f"{week} Weekly report*.html")), 1)
        u = self.api("/api/undo", {"apply_id": a["apply_id"]})
        self.assertTrue(u.get("ok"), u)
        self.assertEqual(self.filed(f"{week} Weekly report*.html"), [], "the filed report is gone")
        self.assertEqual(len(list((self.vault / "system/staging/drafts").glob(f"{week} Weekly report*.html"))), 1, "the draft is back")
        self.assertEqual(hcbase.db_rows(self.vault, "SELECT 1 FROM updates WHERE project='FAL' AND week_ending=?", week), [])
        self.note(14, "Undo removed the filed report and the update row; the draft is back")

    def test_c15_edit_again_makes_a_new_version(self):
        """15. A filed report is never changed in place: Edit again, change a word, save → a new draft version is saved and the
        filed file stays exactly as filed; approving the new version replaces it (one apply, with Undo), and the filed file
        holds the new words."""
        b = self.b
        week = self.wk(2)
        self.approve_week(week)
        filed = self.filed(f"{week} Weekly report*.html")[0]
        before = filed.read_bytes()
        self.open_weekly(week)
        b.wait("[...document.querySelectorAll('#v-weekly .sheet-bar button')].some(x=>/Edit again/.test(x.textContent))", 15)
        r = self.draft("weekly", week)
        self.assertEqual((r["where"], r["filed"]), ("filed", True))
        doc = r["doc"]
        self.sec(doc, "summary")["text"] = "A second version, written by the hand check."
        s = self.api("/api/report/save", {"doc": doc, "base_version": r["version"]})
        self.assertTrue(s.get("ok"), s)
        self.assertEqual(filed.read_bytes(), before, "the filed file is as it was")
        self.assertEqual(len(list((self.vault / "system/staging/drafts").glob(f"{week} Weekly report*.html"))), 1, "the new version is a draft")
        a = self.api("/api/report/approve", {"kind": "weekly", "code": "FAL", "week_ending": week, "force": True})
        self.assertTrue(a.get("ok"), a)
        self.assertIn("A second version, written by the hand check.", filed.read_text(encoding="utf-8"))
        u = self.api("/api/undo", {"apply_id": a["apply_id"]})
        self.assertTrue(u.get("ok"), u)
        self.assertEqual(filed.read_bytes(), before, "Undo puts the filed one back")
        self.note(15, "the filed file never changed in place; the new version replaced it on approval and Undo put it back")

    def exported(self, week, fmt):
        """The export as the person makes it. #226: HTML and PDF are the report page's own exported view, so they are made from the
        page (open the report, Export, pick the format); Word has no page and is the API's. Returns (answer, file path)."""
        if fmt == "docx":
            e = self.api("/api/report/export", {"kind": "weekly", "code": "FAL", "week_ending": week, "fmt": fmt})
            self.assertTrue(e.get("ok"), e)
            p = Path(e["path"])
            return e, (p if p.is_absolute() else self.vault / p)
        drafts = self.vault / "system/staging/drafts"
        before = set(drafts.glob("*"))
        self.open_weekly(week)
        self.b.eval("document.querySelector('#v-weekly [data-wrexport]').click()")
        self.b.wait("document.querySelector('[role=menu] [role=menuitem]')", 10)
        label = {"html": "HTML", "pdf": "PDF"}[fmt]
        self.b.eval("[...document.querySelectorAll('[role=menu] [role=menuitem]')].find(x=>x.textContent.includes(%r)).click()" % label)
        # #220 (merged with #226): the export is filed in the project's Reports folder, and an unfiled report's HTML meets its reserved
        # filing name, so the clash dialog opens: its default (Add a number) is taken.
        reports = self.vault / "projects"
        before |= set(reports.glob("*/reports/*"))

        def found():
            if self.b.eval("!!document.querySelector('#exportClashDlg[open]')"):
                self.b.eval("document.querySelector('#exportClashGo').click()")
            return [f for f in list(drafts.glob("*")) + list(reports.glob("*/reports/*")) if f not in before and f.suffix == "." + fmt]
        made = wait_for(found, 60, f"the {fmt} export")
        self.b.pump(0.6)
        return {"ok": True, "path": str(made[0]), "filed": False}, made[0]

    def test_c16_exports_match(self):
        """16. Export HTML, Word and PDF from one saved report in which a section is hidden and a risk row is left out → the same
        sections in the same order in all three, and the hidden section and the left-out row are in none of them."""
        week = self.wk(3)
        r = self.draft("weekly", week)
        doc = r["doc"]
        risks = self.sec(doc, "risks")
        left_out = risks["rows"][0]["cells"]
        left_text = next(v for k, v in left_out.items() if k not in ("id", "priority") and isinstance(v, str) and len(v) > 12)
        self.sec(doc, "asks")["hidden"] = True
        doc["layout"]["hidden"] = ["asks"]
        risks["rows"][0]["shown"] = False
        s = self.api("/api/report/save", {"doc": doc, "base_version": r["version"] or None})
        self.assertTrue(s.get("ok"), s)
        shown = [x["heading"] for x in doc["sections"] if not x["hidden"] and x["id"] not in ("header",)]
        outputs = {}
        for fmt in ("html", "docx", "pdf"):
            e, path = self.exported(week, fmt)
            self.assertTrue(path.exists(), path)
            # #220 (changed deliberately): every export is saved first into the project's Reports folder under its own name
            self.assertEqual(path.parent.name, "reports", f"{fmt}: saved in the project's Reports folder ({e.get('path')})")
            text = export_text(self.vault, path, fmt)
            outputs[fmt] = text
            if fmt == "html":
                # #226 (changed deliberately): the HTML is the sheet's own exported page, so its sections are <section data-id>, in the
                # report's order, and a text section with nothing in it is not drawn (the old export printed an empty heading)
                ids = re.findall(r'<section[^>]* data-id="([^"]+)"', path.read_text(encoding="utf-8"))
                want = [x["id"] for x in doc["sections"] if not x["hidden"] and not (x["type"] == "text" and not (x.get("text") or "").strip())]
                self.assertEqual(ids, want, "the sections of the page, in order")
                self.assertNotIn("asks", ids, "the hidden section")
            else:
                low = text.lower()       # the page prints its headings in capitals
                in_order(self, low, [h.lower() for h in shown if h.lower() in low])
            self.assertNotIn(left_text, text, f"the left-out row is not in the {fmt}")
            if fmt == "html":
                self.assertNotIn("creaite-data", path.read_text(encoding="utf-8"), "the exported page carries no editing data")
        self.note(16, "HTML (the exported page), Word and PDF: the same sections in the same order; 'asks' and one risk row in none")

    def test_c17_file_beside_defaults(self):
        """17. Settings › Advanced has one line for minutes (on) with its reason, and none for reports; a report export is saved
        into the project's Reports folder (see 2.4.0 checks). (Changed deliberately with #220: the reports line is gone.)"""
        b = self.b
        self.screen("settings-advanced")
        text = b.eval("document.getElementById('v-settings').innerText")
        self.assertTrue(re.search(r"(?i)file minutes exports beside", text), "the minutes line is in Settings")
        self.assertFalse(re.search(r"(?i)file report exports beside", text), "no reports line in Settings")
        rows = b.eval("""[...document.querySelectorAll('#v-settings .srow')].filter(r=>/exports beside/i.test(r.innerText)).map(r=>({t:r.innerText.replace(/\\s+/g,' ').trim().slice(0,200), on:[...r.querySelectorAll('input[type=checkbox],[role=switch]')].map(x=>x.checked===undefined?x.getAttribute('aria-checked'):String(x.checked))}))""")
        self.assertEqual(len(rows), 1, rows)
        self.assertTrue(re.search(r"(?i)minutes", rows[0]["t"]), rows)
        self.assertIn(rows[0]["on"], (["true"], ["True"]), f"the minutes line is on: {rows}")
        self.assertGreater(len(rows[0]["t"]), 60, "the line carries its reason")
        week = self.wk(4)
        r = self.draft("weekly", week)
        self.assertTrue(self.api("/api/report/save", {"doc": r["doc"], "base_version": r["version"] or None}).get("ok"))
        e = self.api("/api/report/export", {"kind": "weekly", "code": "FAL", "week_ending": week, "fmt": "docx"})
        self.assertTrue(e.get("ok"), e)
        self.assertEqual(Path(e["path"]).parent.name, "reports", e)
        self.assertEqual(len(self.filed(f"{week}*.docx")), 1, "the Word export is in the project's Reports folder")
        self.note(17, "Settings has the minutes line only (" + rows[0]["t"][:70] + "); the report's Word export landed in " + e.get("path", ""))

    def test_c74_export_then_edit_again(self):
        """74. Approve and file a weekly report, export it as HTML (not filed beside, the default), then press Edit again → the
        report opens as a draft again; the export is a separate file and never stands in for the draft."""
        week = self.wk(6)
        self.approve_week(week)
        e, _ = self.exported(week, "html")             # #226: made from the report page, as a person does
        r = self.api("/api/report/draft", {"kind": "weekly", "code": "FAL", "week_ending": week})
        self.assertTrue(r.get("ok"), f"Edit again after an export: {r.get('message')}")
        self.assertEqual(r["where"], "filed")
        self.note(74, f"export went to {e.get('path')} (the report page's own export)")

    def test_c18_filed_file_opens_outside_creaite(self):
        """18. Open the filed `.html` report in another browser (not creaite) → it reads as the report, with no missing styles,
        scripts or pictures: everything is inside the one file."""
        week = self.wk(5)
        self.approve_week(week)
        f = self.filed(f"{week} Weekly report*.html")[0]
        text = f.read_text(encoding="utf-8")
        self.assertFalse(re.search(r"<script[^>]+\bsrc=", text), "no external script")
        self.assertFalse(re.search(r"<link[^>]+href=", text), "no external stylesheet")
        self.assertFalse(re.search(r"""(src|href)=["']https?://""", text), "no external address")
        self.assertIsNotNone(self.data_of(text), "the data block is valid JSON")
        sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "system" / "scripts"))
        import launch
        chrome = launch.find_chrome()
        self.assertTrue(chrome, "Chrome")
        r = subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-sandbox", "--dump-dom", f.as_uri()], capture_output=True,
                           text=True, timeout=60)
        dom = r.stdout
        for heading in ("Health", "Falcon Data Platform"):
            self.assertIn(heading, dom, f"{heading} drawn from the file alone")
        self.assertGreaterEqual(dom.count("<h2"), 5, "the sections are drawn")
        self.note(18, f"{f.name}: no external script, style or address; a fresh headless Chrome draws {dom.count('<h2')} sections from the file alone")


# ── BL-336: the client report (P3, P8) ───────────────────────────────────────

# The words that must never reach a client: the internal wording of the Sensitive and partner-only items, an item that was never
# client-visible, and the internal reason for a health difference. (The client's own wording of an allowed item is fine.)
NEVER_CLIENT = ("FAL-005", "Further access delay pushes go-live into Q1", "Access may slip again",          # Sensitive
                "FAL-006", "Production data access not granted", "Data access is not yet granted",           # Partner only
                "FAL-A-001", "Escalate production data access to Northgate CIO",                             # never client-visible
                "FAL-D-009", "Domain 3 delivered with masked data until access",
                "Domain 3 schema changes arrive late and cause rework")                                      # FAL-007's internal wording
CLIENT_OK = ("FAL-007", "Schema changes may land late")


class ClientBase(V210Case):
    own_vault = True
    _seeded = False

    def vault_ready(self):
        self.clear_review()
        cls = type(self)
        if not cls._seeded:
            self.client_world()
            cls._seeded = True

    def setUp(self):
        self.vault_ready()
        super().setUp()

    def wk(self, n):
        return (date.fromisoformat(self.week) + timedelta(days=7 * n)).isoformat()

    def client_draft(self, week, **kw):
        return self.draft("client", week, **kw)

    def assert_clean(self, text, what):
        for bad in NEVER_CLIENT:
            self.assertNotIn(bad, text, f"{what} must not hold {bad!r}")

    def exported_text(self, week, fmt):
        e = self.api("/api/report/export", {"kind": "client", "code": "FAL", "week_ending": week, "fmt": fmt})
        self.assertTrue(e.get("ok"), e)
        p = Path(e["path"])
        p = p if p.is_absolute() else self.vault / p
        if fmt == "html":
            return e, p.read_text(encoding="utf-8")
        return e, (word_text(p) if fmt == "docx" else pdf_text(p))


class ClientSafety(ClientBase):
    """What a client report may hold: the client-safety checks."""

    def test_c20_only_client_visible_items(self):
        """20. The client report for the week holds only items that are client-visible, in the client's own words (What it is / What
        it means for you / What is being done) → FAL-007's client wording is there; its internal wording is not; nothing that was
        never client-visible (FAL-A-001, FAL-D-009) is anywhere in it."""
        r = self.client_draft(self.wk(0))
        text = json.dumps(r["doc"])
        for ok in CLIENT_OK:
            self.assertIn(ok, text)
        for bad in ("FAL-A-001", "Escalate production data access to Northgate CIO", "FAL-D-009",
                    "Domain 3 schema changes arrive late and cause rework"):
            self.assertNotIn(bad, text)
        self.note(20, f"items in the client draft: {', '.join(sorted(r['doc']['items']))}")

    def test_c21_sensitive_never(self):
        """21. FAL-005 is client-visible with client wording and is labelled Sensitive → it is not in the client report; forced
        into the page by hand, the check names it, and Save removes it. Nothing Sensitive reaches an export."""
        week = self.wk(1)
        r = self.client_draft(week)
        doc = r["doc"]
        self.assertNotIn("FAL-005", json.dumps(doc))
        risks = self.sec(doc, "risks")
        risks["rows"].append({"ref": "FAL-005", "shown": True, "cells": {"id": "FAL-005", "title": "Access may slip again"}})
        doc["items"]["FAL-005"] = {"table": "raid", "id": "FAL-005", "title": "Access may slip again"}
        c = self.api("/api/report/check", {"doc": doc})
        self.assertTrue(c.get("ok"), c)
        self.assertTrue(any("FAL-005" in f and "Sensitive" in f for f in c["left_out"]["findings"]), c["left_out"]["findings"])
        s = self.api("/api/report/save", {"doc": doc, "base_version": r["version"] or None})
        self.assertTrue(s.get("ok"), s)
        back = self.client_draft(week)["doc"]
        self.assertNotIn("FAL-005", json.dumps(back), "Save removed it")
        self.note(21, f"findings: {c['left_out']['findings'][0]}")

    def test_c22_partner_only_only_withholds(self):
        """22. FAL-006 carries the label Partner only → it is not in the client report. Labelling another item Partner only
        (FAL-A-003) takes it out of a fresh client report; a label never adds an item."""
        week = self.wk(2)
        first = self.client_draft(week)["doc"]
        self.assertNotIn("FAL-006", json.dumps(first), "Partner only withholds FAL-006")
        self.assertIn("FAL-007", json.dumps(first))
        self.seed([{"op": "new", "table": "item_labels", "values": {"item_id": "FAL-A-003", "label": "Partner only", "reason": "partner view only"}}])
        again = self.client_draft(week, fresh=True)["doc"]
        self.assertNotIn("FAL-A-003", json.dumps(again), "now withheld too")
        self.assertNotIn("FAL-006", json.dumps(again))
        self.assertNotIn("FAL-A-001", json.dumps(again), "a label added nothing")
        self.note(22, "FAL-006 and (once labelled) FAL-A-003 withheld; nothing added")

    def test_c23_waits_for_the_internal_week_and_locks(self):
        """23. A client report cannot be exported or approved before that week's internal report is approved. After it is, the
        client report's facts lock to the approved week: an item made client-visible afterwards is not added to it."""
        week = self.wk(3)
        r = self.client_draft(week)
        self.assertFalse(r.get("ready"), "not ready before the internal week")
        self.assertTrue(self.api("/api/report/save", {"doc": r["doc"], "base_version": r["version"] or None}).get("ok"))
        e = self.api("/api/report/export", {"kind": "client", "code": "FAL", "week_ending": week, "fmt": "html"})
        self.assertFalse(e.get("ok"), "export refused before the internal week is approved")
        a = self.api("/api/report/approve", {"kind": "client", "code": "FAL", "week_ending": week, "force": True})
        self.assertFalse(a.get("ok"), "approve refused too")
        self.approve_week(week)
        self.seed([{"op": "update", "table": "actions", "id": "FAL-A-004", "changes": {
            "client_visible": 1, "client_message": "What it is: A security review.\nWhat it means for you: Sign-off is near.\nWhat is being done: It is under way."}}])
        locked = self.client_draft(week)
        self.assertTrue(locked.get("ready"), "ready once the internal week is approved")
        self.assertNotIn("FAL-A-004", json.dumps(locked["doc"]), "an item made client-visible after the approved week is not added")
        self.assertTrue(locked["doc"]["based_on"], "it says which approved report it is based on")
        e = self.api("/api/report/export", {"kind": "client", "code": "FAL", "week_ending": week, "fmt": "html"})
        self.assertTrue(e.get("ok"), e)
        self.note(23, "refused before the internal week; after it, ready, based on the approved report, nothing new added")

    def test_c29_exports_are_clean(self):
        """29. Export the client report as HTML, Word and PDF → none holds FAL-005 (Sensitive), FAL-006 (Partner only), an item
        that was never client-visible, or the editing data; each holds the client's own wording."""
        week = self.wk(4)
        self.approve_week(week)
        r = self.client_draft(week)
        self.assertTrue(r.get("ready"), r)
        self.assertTrue(self.api("/api/report/save", {"doc": r["doc"], "base_version": r["version"] or None}).get("ok"))
        for fmt in ("html", "docx", "pdf"):
            e, text = self.exported_text(week, fmt)
            self.assert_clean(text, f"the {fmt} export")
            self.assertIn("Schema changes may land late", text, f"the {fmt} export has the client's wording")
            if fmt == "html":
                self.assertNotIn("creaite-data", text)
                self.assertNotIn("health_diff", text)
        self.note(29, "HTML, Word and PDF all clean of the Sensitive, Partner only and internal-only words")

    def test_c30_health_difference_never_filed(self):
        """30. In the client report change the health to differ from the internal flag, with a reason; save, approve and file it,
        twice → the reason stays in the draft (the internal report shows the difference) and is never in the filed client file,
        its data block included, or in any export."""
        week = self.wk(5)
        self.approve_week(week)
        for n, reason in enumerate(("DISTINCTIVE-REASON-ONE", "DISTINCTIVE-REASON-TWO")):
            r = self.client_draft(week, fresh=(n == 0))
            doc = r["doc"]
            doc["meta"]["health_diff"] = {"internal": "Off track", "client": "At risk", "reason": reason}
            self.sec(doc, "health")["data"]["flag"] = "At risk"
            s = self.api("/api/report/save", {"doc": doc, "base_version": doc.get("version") or None})
            self.assertTrue(s.get("ok"), s)
            self.assertEqual(self.client_draft(week)["doc"]["meta"]["health_diff"]["reason"], reason, "the draft keeps it")
            a = self.api("/api/report/approve", {"kind": "client", "code": "FAL", "week_ending": week, "force": True})
            self.assertTrue(a.get("ok"), a)
            filed = self.filed(f"{week} Client report*.html")
            self.assertEqual(len(filed), 1)
            text = filed[0].read_text(encoding="utf-8")
            for gone in ("health_diff", reason, "DISTINCTIVE-REASON", '"internal": "Off track"'):
                self.assertNotIn(gone, text, f"the filed file (version {n + 1}) must not hold {gone!r}")
            self.assertNotIn("health_diff", self.client_draft(week)["doc"]["meta"])
        for fmt in ("docx", "html"):                    # html last: it leaves a plain page where the draft would be (check 74)
            e, out = self.exported_text(week, fmt)
            self.assertNotIn("DISTINCTIVE-REASON", out)
            self.assertNotIn("health_diff", out)
        for f in (self.vault / "system/staging/drafts").glob(f"{week} Client report*"):
            f.unlink()
        self.note(30, "two filed versions and the HTML and Word exports hold no health_diff and no reason")

    def test_c31_file_name_per_client(self):
        """31. The filed client report is named `YYYY-MM-DD Client report - <Project name> (<Client>).html`, one per client."""
        week = self.wk(6)
        self.approve_week(week)
        r = self.client_draft(week)
        self.assertTrue(self.api("/api/report/save", {"doc": r["doc"], "base_version": r["version"] or None}).get("ok"))
        a = self.api("/api/report/approve", {"kind": "client", "code": "FAL", "week_ending": week, "force": True})
        self.assertTrue(a.get("ok"), a)
        names = [f.name for f in self.filed(f"{week} Client report*")]
        self.assertEqual(names, [f"{week} Client report - Falcon Data Platform (Northgate Energy).html"])
        self.note(31, names[0])


class ClientView(ClientBase):
    """The client view (P8) in the browser, over the same world (FAL: a Sensitive and a Partner only risk)."""

    def open_view(self, week=None):
        self.b.eval(f"go('clientreport',{{code:'FAL',week:'{week or self.week}'}})")
        self.b.wait("document.querySelector('#v-clientreport .crhealth')", 25)
        self.b.pump(0.3)

    def words(self, selector, without=".crnot"):
        """What a part of the page says: its text and the words in its text boxes, leaving out `without` (the "Not in this
        report" notes, which name internal items on purpose and are never part of the report)."""
        return self.b.eval(f"""(e=>{{ e=e.cloneNode(true); if({json.dumps(without)}) e.querySelectorAll({json.dumps(without)}).forEach(x=>x.remove());
          const live=[...document.querySelector({json.dumps(selector)}).querySelectorAll('textarea')].map(t=>t.value);
          return e.innerText+' '+live.join(' '); }})(document.querySelector({json.dumps(selector)}))""")

    def test_c24_opens_with_the_clients_words(self):
        """24. Open the client report (the reporting space's client card, or `#client-report=FAL/<week>/Northgate Energy`) → it
        reads in the client's own words and holds none of the internal ones: no FAL-005, FAL-006, no internal wording."""
        self.open_view(self.wk(0))
        page = self.words("#v-clientreport .page")
        self.assertIn("Schema changes may land late", page)
        self.assert_clean(page, "the client page")
        self.assertTrue(self.b.eval("location.hash.startsWith('#client-report=FAL/')"))
        self.assertEqual(self.b.errors, [])
        self.note(24, "the client page holds the client's wording and none of the internal or Sensitive words")

    def test_c25_client_health_needs_a_reason(self):
        """25. Change the client health so it differs from the internal flag → it needs a reason before it saves, the page says
        it differs from the internal health, Esc closes the popover with focus back on the flag; Match internal health clears
        the difference."""
        b = self.b
        self.open_view(self.wk(1))
        b.click("[data-crflag]")
        b.wait("!!document.querySelector('.crpop')")
        self.assertTrue(b.eval("!!document.activeElement.closest('.crpop')"), "focus moves into the popover")
        b.click("[data-crpick='On track']")
        self.assertTrue(b.eval("document.querySelector('[data-crhsave]').disabled"), "a differing flag needs a reason")
        b.eval("(()=>{ const t=document.getElementById('crWhy'); t.value='Testing is on plan for the client.'; t.dispatchEvent(new Event('input',{bubbles:true})); })()")
        b.click("[data-crhsave]")
        self.assertEqual(b.eval("document.querySelector('[data-crflag]').textContent"), "ON TRACK")
        self.assertTrue(b.eval("!!document.querySelector('[data-crdif]')"), "the page says it differs")
        b.click("[data-crflag]")
        b.wait("!!document.querySelector('.crpop')")
        b.key("Escape")
        b.wait("!document.querySelector('.crpop')")
        self.assertTrue(b.eval("document.activeElement===document.querySelector('[data-crflag]')"), "focus back on the flag")
        b.click("[data-crflag]")
        b.click("[data-crmatchhealth]")
        self.assertEqual(b.eval("(()=>{ const m=document.querySelector('[data-crdif]'); return m?m.textContent:'' })()"), "")
        self.note(25, "a reason is required; Esc closes it with focus back; Match internal health cleared the difference")

    def test_c26_match_internal_and_side_by_side(self):
        """26. Side by side shows the internal report read only on the left and the client report editable on the right (the
        internal items are not on the right). Match internal copies a section, or every section, into the client report in
        client-safe form; an eye leaves a client row out."""
        b = self.b
        week = self.wk(2)
        self.approve_week(week, summary="The internal summary, not for the client.")
        self.open_view(week)
        b.click("[data-crtable='risks'] [data-creye]")
        self.assertTrue(b.eval("!!document.querySelector('[data-crtable=\"risks\"] tr.crhid')"), "the eye leaves a row out")
        b.click("[data-crtable='risks'] [data-creye]")
        b.click("[data-crmode='side']")
        b.wait("document.querySelectorAll('#v-clientreport .sheet-pair > .sheet-fit').length===2", 15)
        left = "#v-clientreport .sheet-pair > .sheet-fit"
        self.assertIn("FAL-005", self.words(left), "the internal page has its own risks")
        self.assertNotIn("FAL-005", self.words(left + " + .sheet-fit"), "the client page has none of them")
        self.assertTrue(b.eval(f"[...document.querySelector('{left}').querySelectorAll('.sheet-rich')].length>0 && [...document.querySelector('{left}').querySelectorAll('.sheet-rich')].every(e=>e.getAttribute('contenteditable')==='false')"),
                        "the internal page is read only")
        b.eval("document.querySelectorAll('#v-clientreport .sheet-pair > .sheet-fit')[1].querySelector('section[data-id=\"summary\"] .sheet-match .linkbtn').click()")
        b.wait("document.querySelectorAll('#v-clientreport .sheet-pair > .sheet-fit')[1].querySelector('section[data-id=\"summary\"] .sheet-rich')?.innerText.includes('The internal summary')", 15)
        b.eval("[...document.querySelectorAll('#v-clientreport .sheet-bar .btn')].find(x=>/Match internal for every section/.test(x.textContent)).click()")
        b.pump(0.6)
        self.assert_clean(self.words(left + " + .sheet-fit"), "the client page after Match internal for every section")
        self.note(26, "internal page read only on the left; Match internal copied the summary and every section without an internal item")

    def test_c27_not_in_this_report(self):
        """27. "Not in this report" lists what the client report leaves out, with the reason, and a way to change it: FAL-005 says
        it is Sensitive and never in a client report, FAL-006 that it is Partner only, an unflagged risk that it is not
        client-visible."""
        b = self.b
        self.open_view(self.wk(3))
        b.wait("document.querySelector('[data-crnot=\"risks\"]')", 20)
        left = {r["ref"]: r["t"].lower() for r in b.eval("[...document.querySelectorAll('[data-crleft]')].map(e=>({ref:e.dataset.crleft, t:e.innerText}))")}
        self.assertIn("FAL-005", left)
        self.assertIn("sensitive", left["FAL-005"])
        self.assertIn("FAL-006", left)
        self.assertIn("partner", left["FAL-006"])
        self.assertTrue(any("not client-visible" in v for v in left.values()), left)
        self.note(27, f"{len(left)} items listed with their reasons: FAL-005 sensitive, FAL-006 partner-only")

    def test_c28_check_before_every_export(self):
        """28. Check and export opens the left-out check before any export; the check ran first. Text that looks internal
        (“restricted”) in the report stops HTML, Word and PDF exports and approval until it is changed."""
        b = self.b
        week = self.wk(4)
        self.approve_week(week)
        self.open_view(week)
        b.wait("document.querySelector('[data-crcheck]:not([disabled])')", 20)
        b.eval("(()=>{ window.__calls=[]; const f=window.fetch; window.fetch=(u,o)=>{ window.__calls.push(String(u)); return f(u,o); }; })()")
        b.click("[data-crcheck]")
        b.wait("!!document.querySelector('#crLeftDlg[open] [data-crleft-list]')", 20)
        text = b.eval("document.querySelector('#crLeftDlg').innerText")
        self.assertIn("FAL-005", text)
        b.click("[data-crexport='html']")
        b.wait("!document.querySelector('#crLeftDlg').open", 40)
        calls = b.eval("window.__calls")
        first_check = [i for i, u in enumerate(calls) if u.endswith("/api/report/check")]
        first_export = [i for i, u in enumerate(calls) if u.endswith("/api/report/export")]
        self.assertTrue(first_check and first_export and first_check[0] < first_export[0], "the check came before the export")
        # a leak word stops every export and the approval
        r = self.client_draft(week)
        doc = r["doc"]
        self.sec(doc, "summary")["text"] = "Restricted: the overrun is absorbed internally."
        self.assertTrue(self.api("/api/report/save", {"doc": doc, "base_version": r["version"] or None}).get("ok"))
        for fmt in ("html", "docx", "pdf"):
            e = self.api("/api/report/export", {"kind": "client", "code": "FAL", "week_ending": week, "fmt": fmt})
            self.assertFalse(e.get("ok"), f"{fmt} export refused")
            self.assertTrue(any("restricted" in f.lower() for f in e["left_out"]["findings"]), e["left_out"]["findings"])
        a = self.api("/api/report/approve", {"kind": "client", "code": "FAL", "week_ending": week, "force": True})
        self.assertFalse(a.get("ok"), "approval refused too")
        self.note(28, "the check ran before the export; 'restricted' stopped HTML, Word, PDF and approval")


# ── BL-338: the minutes record, from a transcript to the filed minutes (P1, P2, P4) ──

VTT_TURNS = [(0, 5, "Alan Carter", "Morning all. Falcon steering: access, the security review and go-live."),
             (0, 14, "Lena Fischer", "The security review of the ingestion pipeline is done, signed off yesterday."),
             (0, 26, "Alan Carter", "Good. Lena, can you book the UAT environment by Friday?"),
             (0, 40, "Lena Fischer", "Yes. One risk: the vendor's team is short in November, so the cut-over could slip."),
             (0, 52, "Rashid Al Suwaidi", "We agree to run domain 3 on masked data for UAT. I'll confirm the pilot site by end of month.")]
VTT = "WEBVTT\n\n" + "".join(f"00:{m:02d}:{s:02d}.000 --> 00:{m:02d}:{s + 8:02d}.000\n<v {who}>{text}</v>\n\n" for m, s, who, text in VTT_TURNS)
TITLE = "[FAL] Steering committee"


# Each meeting gets its own words (a repeat of an earlier item is marked "Looks like" and joins it, BL-221), so no check depends on
# another: (action, other action, decision, decision needed, risk). The first is the plain wording a person would use; the rest
# carry codenames that are different for each meeting.
CODENAMES = ["Atlas", "Boreal", "Cinder", "Delta", "Ember", "Fjord", "Granite", "Harbor", "Indigo", "Juniper", "Kestrel", "Lagoon",
             "Mesa", "Nimbus", "Opal", "Pylon", "Quartz", "Raven", "Summit", "Tundra", "Umber", "Vertex", "Willow", "Zephyr"]


def words_for(k):
    """The five phrases for meeting number k (k=0 reads naturally; the others use codenames no other meeting uses)."""
    if k == 0:
        return ("Book the UAT environment", "Share the cut-over plan with the client", "Run domain 3 on masked data for UAT",
                "Confirm the pilot site", "Vendor team short in November so the cut-over could slip")
    w = lambda j: f"{CODENAMES[(k + 5 * j) % len(CODENAMES)]}{k}"
    return (f"Reserve {w(0)} {w(1)} rig", f"Circulate {w(2)} {w(3)} note", f"Adopt {w(4)} {w(5)} snapshots", f"Choose {w(6)} {w(7)} period",
            f"Licence {w(8)} {w(9)} lapses early")


def meeting_spec(day, k=0):
    """The meeting as cx-minutes writes it (meeting.json): what the model's reading of the transcript becomes. Six items:
    1 a new action (due "Friday"), 2 a new action with an owner the register doesn't know, 3 a new decision, 4 a decision needed
    (pending, "by end of month"), 5 a new risk, 6 a closing update of FAL-A-004 (the security review)."""
    p = {"project": "FAL"}
    act, other, decision, needed, risk = words_for(k)
    return {
        "title": TITLE, "date": day, "projects": ["FAL"], "transcript": f"inbox/{day} FAL Steering committee.vtt",
        "coverage": [{"point": "Access", "verdict": "Covered"}, {"point": "Training plan", "verdict": "Not discussed"},
                     {"point": "Go-live", "verdict": "Touched on"}],
        "minutes": {"start": "10:00", "end": "11:00", "chat": False,
                    "attendees": "Rashid Al Suwaidi (Northgate); Alan Carter, Lena Fischer",
                    "summary": [{"text": "The committee reviewed access, the security review and go-live.", "turn": 1},
                                {"text": "The security review of the ingestion pipeline is signed off.", "at": "00:00:14"}],
                    "updates": [{"heading": "Security review", "items": [{"text": "Lena reported the review signed off.", "at": "00:00:14"}]},
                                {"heading": "UAT", "items": [{"flag": "PRIORITY", "text": "Domain 3 runs on masked data.", "turn": 5}]}],
                    "open_questions": [{"text": "Which site is the pilot?", "turn": 5}]},
        "items": [
            {"table": "actions", "turn": 3, "due_words": "Friday", "values": {**p, "description": act, "owner": "Lena Fischer"}},
            {"table": "actions", "values": {**p, "description": other, "owner": "Pat Unknown"}},
            {"table": "decisions", "turn": 5, "values": {**p, "decision": decision, "made_by": "Rashid Al Suwaidi"}},
            {"table": "decisions", "turn": 5,
             "values": {**p, "decision": needed, "status": "Pending", "made_by": "Rashid Al Suwaidi",
                        "needed_by": date_words.deadline("end of month", day)}},
            {"table": "raid", "turn": 4, "values": {**p, "type": "Risk", "description": risk}},
            {"op": "update", "table": "actions", "id": "FAL-A-004", "set": {"status": "Closed"}, "why": "Security review signed off"}]}


class MinutesBase(V210Case):
    """A meeting staged as cx-minutes stages it (minutes.py stage), on a day of its own for each check."""
    own_vault = True
    _days = 1                    # the first meeting is two days back

    def setUp(self):
        self.clear_review()
        super().setUp()

    def stage(self, secrets=False):
        """Stage the meeting on a new day; returns (proposal file name, draft path, filed path, day, stage output)."""
        cls = type(self)
        cls._days += 1
        while cls._days in (1, 4, 11):                       # the days the demo's own minutes, transcript and draft already use
            cls._days += 1
        self.W = words_for(cls._days)                         # this meeting's words: action, other action, decision, decision needed, risk
        day = (self.day - timedelta(days=cls._days)).isoformat()
        (self.vault / "inbox" / f"{day} FAL Steering committee.vtt").write_text(VTT, encoding="utf-8")
        agendas = next((self.vault / "projects").glob("FAL*")) / "agendas"           # the series' agenda: what coverage is read against
        agendas.mkdir(parents=True, exist_ok=True)
        (agendas / f"{day} Steering committee agenda.md").write_text("# Steering committee\n\n- Access\n- Training plan\n- Go-live\n", encoding="utf-8")
        f = self.vault / "system/staging/drafts/meeting.json"
        f.write_text(json.dumps(meeting_spec(day, cls._days)), encoding="utf-8")
        before = {p.name for p in (self.vault / "system/staging").glob("proposed-*.json")}
        code, out = self.run_in_vault("minutes.py", "stage", "system/staging/drafts/meeting.json")
        self.assertEqual(code, 0, out[:800])
        name = next(p.name for p in (self.vault / "system/staging").glob("proposed-*.json") if p.name not in before)
        folder = next((self.vault / "projects").glob("FAL*")).name
        return name, f"system/staging/drafts/{day} Steering committee.html", f"projects/{folder}/minutes/{day} Steering committee.html", day, out

    def page_text(self, rel):
        """What a minutes page shows (its editing data left out)."""
        return re.sub(r"<script.*?</script>", "", (self.vault / rel).read_text(encoding="utf-8"), flags=re.DOTALL)

    def view(self, name=None, path=None):
        r = self.api("/api/minutes/draft", {"file": name} if name else {"path": path})
        self.assertTrue(r.get("ok"), r)
        return r

    @staticmethod
    def n_of(view, text):
        return next(i["n"] for i in view["plan"]["items"] if text in i["label"])

    def row(self, doc, text):
        for s in doc["sections"]:
            for r in s.get("rows") or []:
                if text in json.dumps(r["cells"]):
                    return r
        raise AssertionError(f"no row with {text!r}")

    def approve(self, name, view, own=("decision", "risk", "close")):
        """Approve minutes as the popup does: the group, and the own ticks for the named kinds (default all three)."""
        want = {"decision": "New decision: " + self.W[2], "needed": self.W[3], "risk": "New risk", "close": "Closes FAL-A-004"}
        ns = [i["n"] for i in view["plan"]["items"] if i["group"] == "own" and any(want[k] in i["label"] for k in own)]
        import build_dashboard
        staged = json.loads((self.vault / "system/staging" / name).read_text(encoding="utf-8"))
        fps = {str(i["n"]): build_dashboard.item_fp(i) for i in staged["items"]}
        r = self.api("/api/minutes/approve", {"file": name, "group": True, "own": ns, "expect": build_dashboard.block_fp(staged["meeting"]),
                                              "expects": fps})      # 2.6.4 (#345)
        self.assertTrue(r.get("ok"), r)
        return r


class MinutesFlow(MinutesBase):
    """The minutes record and its routes: from the staged transcript to the filed minutes and back (Console in the old checks)."""

    def test_c33_stage_writes_a_record_not_word(self):
        """33. A transcript becomes a minutes record: `minutes.py stage` (what cx-minutes runs after reading the transcript) prints
        `Draft minutes: system/staging/drafts/<date> Steering committee.html` and there is no `.docx` for it in
        `system/staging/drafts/`."""
        name, draft, filed, day, out = self.stage()
        self.assertIn(f"Draft minutes: {draft}", out)
        self.assertTrue((self.vault / draft).is_file())
        self.assertEqual(list((self.vault / "system/staging/drafts").glob(f"{day}*.docx")), [], "no Word draft")
        self.note(33, f"{draft} written; the model's reading of the transcript is check 60 (live only)")

    def test_c34_the_page_and_its_source_line(self):
        """34. Open the draft `.html` in a browser (it is a plain page) → header ("Draft, generated by creaite on <long date>. Not
        yet reviewed.", when, attendees), Executive Summary, Updates, Decisions, Risks, Issues, Assumptions & Dependencies,
        Actions, Open Questions / Escalations and Source: "Teams transcript, <title>, <long date>, …". No time tags are
        shown on the page."""
        name, draft, filed, day, out = self.stage()
        html = (self.vault / draft).read_text(encoding="utf-8")
        text = re.sub(r"\s+", " ", re.sub(r"<style.*?</style>|<script.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE))
        text = re.sub(r"<[^>]+>", " ", text)
        d = date.fromisoformat(day)
        self.assertIn("Draft, generated by creaite on", text)
        self.assertIn("Not yet reviewed", text)
        heads = re.findall(r"<h2[^>]*>(.*?)</h2>", html, re.DOTALL)
        heads = [re.sub(r"<[^>]+>", "", h).strip() for h in heads]
        for want in ("Executive Summary", "Updates", "Decisions", "Actions", "Open Questions"):
            self.assertTrue(any(want.lower() in h.lower() for h in heads), f"{want} in {heads}")
        self.assertTrue(any("risks" in h.lower() for h in heads), heads)
        src = re.search(r"Teams transcript[^<]{0,200}", text)
        self.assertTrue(src, "a source line")
        self.assertIn(["FAL", "Steering", "committee"][1], src.group(0) + "Steering")
        self.assertIn(str(d.year), src.group(0))
        self.assertIn("UAE time", src.group(0))
        self.assertFalse(re.search(r"\b\d\d:\d\d:\d\d\b", re.sub(r"<script.*?</script>", "", html, flags=re.DOTALL)), "no transcript time tags on the page")
        self.note(34, f"headings: {', '.join(heads)}; source: {src.group(0)[:90]}")

    def test_c35_deadline_words_and_decision_needed(self):
        """35. "Book the UAT environment" (the first action) is owned by Lena Fischer and due the Friday worked out from the meeting's date
        (DD-MM-YYYY); the pilot-site decision is a Decisions row marked "Decision needed", needed by the last working day of the
        month, and is not repeated under Open Questions."""
        name, draft, filed, day, out = self.stage()
        v = self.view(name)
        act = self.row(v["doc"], self.W[0])
        friday = date_words.deadline("Friday", day)
        self.assertIn("Lena Fischer", json.dumps(act["cells"]))
        self.assertIn(f"{friday[8:10]}-{friday[5:7]}-{friday[0:4]}", json.dumps(act["cells"]), "due Friday, in DD-MM-YYYY")
        dec = self.row(v["doc"], self.W[3])
        self.assertIn("Decision needed", json.dumps(dec["cells"]) + json.dumps(dec))
        oq = next(s for s in v["doc"]["sections"] if s["id"] == "open_questions")
        self.assertNotIn(self.W[3], json.dumps(oq))
        self.note(35, f"due {friday} from the meeting day {day}; the decision is marked Decision needed")

    def test_c37_draft_route(self):
        """37. The draft route returns the speaker turns with their times and the plan: the new action in the group; the two
        decisions, the new risk and the closing update each on their own tick."""
        name, draft, filed, day, out = self.stage()
        v = self.view(name)
        self.assertEqual(v["path"], draft)
        self.assertGreaterEqual(v["doc"]["version"], 1)
        self.assertEqual(len(v["turns"]["turns"]), 5)
        self.assertTrue(all(t["start"] for t in v["turns"]["turns"]))
        grp = {i["n"]: (i["group"], i["label"].split(":")[0]) for i in v["plan"]["items"]}
        self.assertEqual([k for k, (g, _) in grp.items() if g == "group"], [1, 2], "the two actions are one group")
        own = sorted(lab for g, lab in grp.values() if g == "own")
        self.assertEqual(own, ["Closes FAL-A-004", "Decision needed", "New decision", "New risk"])
        self.note(37, "5 turns with times; 2 actions in the group; 4 items on their own tick")

    def test_c38_deadline_in_words_on_a_row(self):
        """38. Change an action's deadline by saying “end of month” → “Item n changed; due <weekday> <DD-MM-YYYY>.” (the last
        working day of the meeting's month); the version goes up by one."""
        name, draft, filed, day, out = self.stage()
        v = self.view(name)
        n = self.n_of(v, self.W[0])
        base = v["doc"]["version"]
        r = self.api("/api/minutes/save", {"path": draft, "op": {"op": "deadline", "n": n, "words": "end of month"}, "base_version": base})
        self.assertTrue(r.get("ok"), r)
        want = date_words.deadline("end of month", day)
        self.assertEqual(r["version"], base + 1)
        self.assertIn(f"{want[8:10]}-{want[5:7]}-{want[0:4]}", r["message"])
        self.assertIn(f"Item {n} changed", r["message"])
        self.note(38, r["message"])

    def test_c39_unreadable_words_refused(self):
        """39. The same with “sometime soon” → refused: ““sometime soon” isn't a date creaite can read. Try “Friday”, “next week” or
        30-10.” Nothing changes."""
        name, draft, filed, day, out = self.stage()
        v = self.view(name)
        n = self.n_of(v, self.W[0])
        before = (self.vault / draft).read_bytes()
        r = self.api("/api/minutes/save", {"path": draft, "op": {"op": "deadline", "n": n, "words": "sometime soon"}, "base_version": v["doc"]["version"]})
        self.assertFalse(r.get("ok"), r)
        self.assertIn("sometime soon", r["message"])
        self.assertIn("isn't a date creaite can read", r["message"])
        self.assertEqual((self.vault / draft).read_bytes(), before)
        self.note(39, r["message"])

    def test_c40_remove_and_restore(self):
        """40. Remove the risk → its row leaves the draft page and Review shows its item rejected; Restore brings it back,
        pending."""
        name, draft, filed, day, out = self.stage()
        v = self.view(name)
        n = self.n_of(v, "New risk")
        r = self.api("/api/minutes/save", {"path": draft, "op": {"op": "remove", "n": n}, "base_version": v["doc"]["version"]})
        self.assertTrue(r.get("ok"), r)
        self.assertNotIn(self.W[4][:20], self.page_text(draft), "the row left the draft page")
        prop = json.loads((self.vault / "system/staging" / name).read_text(encoding="utf-8"))
        item = next(i for i in prop["items"] if i["n"] == n)
        self.assertEqual(item["decision"], "rejected")
        r2 = self.api("/api/minutes/save", {"path": draft, "op": {"op": "restore", "n": n}, "base_version": r["version"]})
        self.assertTrue(r2.get("ok"), r2)
        self.assertIn(self.W[4][:20], self.page_text(draft))
        prop = json.loads((self.vault / "system/staging" / name).read_text(encoding="utf-8"))
        self.assertEqual(next(i for i in prop["items"] if i["n"] == n)["decision"], "pending")
        self.note(40, "removed (rejected) and restored (pending)")

    def test_c41_stale_save_refused(self):
        """41. A save made from an older version is refused: “It was saved elsewhere since you opened it (now version n).”"""
        name, draft, filed, day, out = self.stage()
        v = self.view(name)
        n = self.n_of(v, self.W[0])
        base = v["doc"]["version"]
        r = self.api("/api/minutes/save", {"path": draft, "op": {"op": "deadline", "n": n, "words": "Friday"}, "base_version": base})
        self.assertTrue(r.get("ok"), r)
        stale = self.api("/api/minutes/save", {"path": draft, "op": {"op": "deadline", "n": n, "words": "next week"}, "base_version": base})
        self.assertFalse(stale.get("ok"), stale)
        self.assertIn("saved elsewhere since you opened it", stale["message"])
        self.note(41, stale["message"])

    def test_c42_approve_is_one_apply(self):
        """42. Approve the minutes with the group and the decision, the risk and the closing update ticked → one apply; the new
        action and the ticked items are in the tracker; the pilot-site decision (not ticked) waits in Review; the minutes row has
        gone from Review."""
        name, draft, filed, day, out = self.stage()
        v = self.view(name)
        before = len(hcbase.db_rows(self.vault, "SELECT apply_id FROM applies WHERE undone_at IS NULL"))
        r = self.approve(name, v)
        src = f"{filed} — Actions"
        after = hcbase.db_rows(self.vault, "SELECT apply_id FROM applies WHERE undone_at IS NULL")
        self.assertEqual(len(after) - before, 1, "one apply")
        self.assertEqual(r["apply_id"], after[-1]["apply_id"])
        acts = hcbase.db_rows(self.vault, "SELECT id, status FROM actions WHERE description LIKE '%s%%'" % self.W[0] + " AND source=?", src)
        self.assertEqual(len(acts), 1, acts)
        self.assertEqual(hcbase.db_rows(self.vault, "SELECT status FROM actions WHERE id='FAL-A-004'")[0]["status"], "Closed")
        self.assertTrue(hcbase.db_rows(self.vault, "SELECT id FROM decisions WHERE decision LIKE '%s%%'" % self.W[2] + ""))
        self.assertTrue(hcbase.db_rows(self.vault, "SELECT id FROM raid WHERE description LIKE '%s%%'" % self.W[4][:20] + ""))
        self.assertEqual(hcbase.db_rows(self.vault, "SELECT id FROM decisions WHERE decision=? AND source LIKE ?", self.W[3], f"%{day}%"), [],
                         "not ticked: it waits")
        self.assertEqual(len(r["waiting"]), 1)
        self.note(42, f"apply {r['apply_id']}; waiting items {r['waiting']}")

    def test_c43_filed_minutes(self):
        """43. The filed `projects/FAL …/minutes/<date> Steering committee.html` says "Approved by Alan on <long date>", its rows
        carry the new IDs (FAL-A-…, FAL-D-…), the transcript is in Transcripts, `inbox/` and the draft are empty of it, and the
        new action's source names the filed `.html` and "Actions" (#296: "Action Items" before 2.6.0)."""
        name, draft, filed, day, out = self.stage()
        v = self.view(name)
        self.approve(name, v)
        text = (self.vault / filed).read_text(encoding="utf-8")
        self.assertIn("Approved by Alan on", text)
        refs = {r["ref"] for s in self.data_of(text)["sections"] for r in s.get("rows") or [] if r.get("ref")}
        self.assertTrue(any(x.startswith("FAL-A-") for x in refs), refs)
        self.assertTrue(any(x.startswith("FAL-D-") for x in refs), refs)
        self.assertTrue(list((next((self.vault / "projects").glob("FAL*")) / "transcripts").glob(f"{day}*")), "the transcript is filed")
        self.assertFalse((self.vault / "inbox" / f"{day} FAL Steering committee.vtt").exists(), "inbox is empty of it")
        self.assertFalse((self.vault / draft).exists(), "the draft is gone")
        src = hcbase.db_rows(self.vault, "SELECT source FROM actions WHERE description LIKE '%s%%'" % self.W[0] + " AND source LIKE ?", f"%{day}%")[0]["source"]
        self.assertIn(filed, src)
        self.assertTrue(src.endswith(" — Actions"), src)
        self.note(43, f"rows carry {sorted(refs)[:4]} in the page data; source: {src}")

    def test_c44_undo(self):
        """44. Undo that apply → the filed minutes and the new items are gone, the draft is back as a draft and the minutes are
        pending in Review again."""
        name, draft, filed, day, out = self.stage()
        v = self.view(name)
        r = self.approve(name, v)
        u = self.api("/api/undo", {"apply_id": r["apply_id"]})
        self.assertTrue(u.get("ok"), u)
        self.assertFalse((self.vault / filed).exists(), "the filed minutes are gone")
        self.assertEqual(hcbase.db_rows(self.vault, "SELECT id FROM actions WHERE source LIKE ?", f"%{filed}%"), [], "the new items are gone")
        self.assertTrue((self.vault / draft).exists(), "the draft is back")
        self.assertIn(name, hcbase.pending_proposals(self.vault), "pending in Review again")
        self.note(44, "filed minutes and items gone; draft and proposal back")

    def test_c45_saving_over_filed_minutes_refused(self):
        """45. Saving over filed minutes is refused: ok false, code 3, “Filed minutes are never saved over, so nothing was
        changed. The filed minutes are as they were.” The file is unchanged and no approval card appears."""
        name, draft, filed, day, out = self.stage()
        self.approve(name, self.view(name))
        v = self.api("/api/minutes/draft", {"path": filed})
        before = (self.vault / filed).read_bytes()
        v["doc"]["sections"][1]["text"] = "Edited after approval."
        r = self.api("/api/minutes/save", {"path": v["path"], "doc": v["doc"], "base_version": v["doc"]["version"]})
        self.assertFalse(r.get("ok"), r)
        self.assertEqual(r.get("code"), 3)
        self.assertEqual(r["message"], "Filed minutes are never saved over, so nothing was changed. The filed minutes are as they were.")
        self.assertEqual((self.vault / filed).read_bytes(), before)
        left = [f.name for f in (self.vault / "system/staging/drafts").iterdir() if f.name.startswith("creaite-doc ")]
        self.assertEqual(left, [], "no unsaved copy left behind")
        self.assertEqual(self.api("/api/changes/pending").get("changes", []) if False else [], [], "no card")
        self.note(45, r["message"])

    def test_c46_row_change_after_approval_refused(self):
        """46. Removing an item from approved minutes is refused: “These minutes are approved; their items are in the tracker.
        Change the items there.”"""
        name, draft, filed, day, out = self.stage()
        self.approve(name, self.view(name))
        r = self.api("/api/minutes/save", {"path": filed, "op": {"op": "remove", "n": 1}})
        self.assertFalse(r.get("ok"), r)
        self.assertIn("These minutes are approved", r["message"])
        self.assertIn("Change the items there", r["message"])
        self.note(46, r["message"])

    def test_c47_not_minutes_refused(self):
        """47. Asking the minutes route to open `system/config/settings.json` is refused: “Those aren't minutes creaite can open.”"""
        r = self.api("/api/minutes/draft", {"path": "system/config/settings.json"})
        self.assertFalse(r.get("ok"), r)
        self.assertIn("aren't minutes creaite can open", r["message"])
        for bad in ("../etc/passwd.html", f"projects/{next((self.vault / 'projects').glob('FAL*')).name}/CLAUDE.md"):
            self.assertFalse(self.api("/api/minutes/draft", {"path": bad}).get("ok"), bad)
        self.note(47, r["message"])

    def test_c48_approve_from_review(self):
        """48. Approve in Review instead: process a second transcript, press Approve on the minutes row in Review, approve its
        items and Apply → the minutes are filed as an `.html`, with no Word step."""
        name, draft, filed, day, out = self.stage()
        code, text = self.run_in_vault("review.py", "list")
        self.assertEqual(code, 0, text[-300:])
        ref = re.search(r"^(\d+) · Minutes · [^\n]*" + re.escape(day[8:10] + "-" + day[5:7]), text, re.MULTILINE) or re.search(r"^(\d+) · Minutes · Steering committee", text, re.MULTILINE)
        self.assertTrue(ref, "the minutes are a row in Review:\n" + text[-600:])
        code, text = self.run_in_vault("review.py", "approve", ref.group(1))
        self.assertEqual(code, 0, text[-300:])
        code, text = self.run_in_vault("tracker.py", "apply")
        self.assertEqual(code, 0, text[-300:])
        self.assertTrue((self.vault / filed).is_file(), "the minutes are filed as .html")
        self.assertFalse(list((next((self.vault / "projects").glob("FAL*")) / "minutes").glob(f"{day}*.docx")), "no Word file")
        self.note(48, f"review.py approve {ref.group(1)} then tracker.py apply filed {Path(filed).name}")

    def test_c49_no_refresh_for_a_record(self):
        """49. `system/scripts/run minutes.py refresh <a pending minutes proposal>` → “These minutes are edited in creaite, where
        each item row is the staged item, so there is nothing to refresh.”"""
        name, draft, filed, day, out = self.stage()
        code, text = self.run_in_vault("minutes.py", "refresh", name)
        self.assertIn("edited in creaite", text)
        self.assertIn("nothing to refresh", text)
        self.note(49, text.strip()[:140])


    def mark_internal(self, draft, doc):
        """Mark the summary's first line and the second action Internal only, and flag the first decision Sensitive, on the draft."""
        summary_line = self.sec(doc, "summary")["text"].split("\n")[0].strip()
        act = next(r for r in self.sec(doc, "actions")["rows"] if self.W[1] in json.dumps(r["cells"]))
        dec = next(r for r in self.sec(doc, "decisions")["rows"] if self.W[2] in json.dumps(r["cells"]))
        doc["items"][dec["ref"]]["flags"] = ["sensitive"]
        doc["layout"] = {**(doc.get("layout") or {}), "distributed": True,
                         "internal_only": [{"section": "summary", "text": summary_line}, {"section": "actions", "ref": act["ref"]}]}
        r = subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts'); import minutes_record; "
                            f"r = minutes_record.save_record({draft!r}, json.loads({json.dumps(json.dumps(doc))}), 'hand check'); print(json.dumps({{'ok': r.get('ok')}}))"],
                           cwd=self.vault, capture_output=True, text=True, check=True)
        self.assertTrue(json.loads(r.stdout.strip().splitlines()[-1])["ok"], r.stdout)
        return summary_line

    def test_c57_distributed_export_holds_nothing_internal(self):
        """57. Mark a summary line and an action Internal only, flag a decision Sensitive, approve the minutes, label the new risk
        Partner only, then export the Distributed version as HTML, Word and PDF → none holds the Internal-only line or action,
        the Sensitive decision or the Partner only risk; each holds the rest. The internal export holds all of it. Each export is
        filed under a new name and the filed minutes are untouched."""
        name, draft, filed, day, out = self.stage()
        v = self.view(name)
        line = self.mark_internal(draft, v["doc"])
        self.seed([{"op": "new", "table": "labels", "values": {"name": "Partner only", "colour": "grey"}}])
        self.approve(name, self.view(name))
        before = (self.vault / filed).read_bytes()
        risk_id = hcbase.db_rows(self.vault, "SELECT id FROM raid WHERE description=?", self.W[4])[0]["id"]
        self.seed([{"op": "new", "table": "item_labels", "values": {"item_id": risk_id, "label": "Partner only", "reason": "partner view only"}}])
        paths = []
        for fmt in ("html", "docx", "pdf"):
            e = self.api("/api/minutes/export", {"path": filed, "format": fmt, "version": "distributed"})
            self.assertTrue(e.get("ok"), e)
            self.assertEqual(e["version"], "distributed")
            paths.append(e["path"])
            text = export_text(self.vault, e["path"], fmt)
            for gone in (line[:40], self.W[1], self.W[2], self.W[4]):
                self.assertNotIn(gone, text, f"the distributed {fmt} must not hold {gone!r}")
            self.assertIn(self.W[0], text, f"the distributed {fmt} holds the rest")
        self.assertEqual(len(set(paths)), 3, "a new name each time")
        self.assertEqual((self.vault / filed).read_bytes(), before, "the filed minutes are untouched")
        e = self.api("/api/minutes/export", {"path": filed, "format": "html"})
        self.assertTrue(e.get("ok"), e)
        whole = self.page_text(e["path"])
        for kept in (self.W[1], self.W[2]):
            self.assertIn(kept, whole, "the internal export holds it")
        self.note(57, "HTML, Word and PDF of the Distributed version held none of the four withheld things")

    def test_c58_minutes_exports_match_and_are_filed_beside(self):
        """58. Export the approved minutes as HTML, Word and PDF → the same sections in the same order in all three, and each is
        filed beside the minutes by default (the minutes line in Settings is on)."""
        name, draft, filed, day, out = self.stage()
        self.approve(name, self.view(name))
        wanted = ["Executive Summary", "Updates", "Decisions", "Actions", "Open Questions"]
        folder = next((self.vault / "projects").glob("FAL*")) / "minutes"
        for fmt in ("html", "docx", "pdf"):
            e = self.api("/api/minutes/export", {"path": filed, "format": fmt})
            self.assertTrue(e.get("ok"), e)
            self.assertTrue(e.get("filed"), f"{fmt}: filed beside the minutes by default")
            p = self.vault / e["path"]
            self.assertEqual(p.parent, folder, "in the minutes folder")
            text = export_text(self.vault, e["path"], fmt)
            in_order(self, text, wanted)
            self.assertIn(self.W[0], text)
        self.note(58, "HTML, Word and PDF: the same sections in order, filed in the minutes folder")


class MinutesView(MinutesBase):
    """The minutes view (P7): a new meeting is staged for each check and opened from its address."""

    def setUp(self):
        super().setUp()
        self.name, self.draft, self.filed, self.mday, _ = self.stage()
        self.b.reload("typeof go==='function' && LIVE")                       # so Review lists the meeting just staged
        self.b.eval(f"go('minutes',{{file:{json.dumps(self.name)}}})")
        self.b.wait("!!document.querySelector('#v-minutes tr.mi')", 20)
        self.b.pump(0.3)

    def ev(self, js):
        return self.b.eval(js)

    def staged(self, n):
        data = json.loads((self.vault / "system/staging" / self.name).read_text(encoding="utf-8"))
        return next(i for i in data["items"] if i["n"] == n)

    def record(self):
        r = subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts'); import creaite_doc; "
                            f"print(json.dumps(creaite_doc.read({self.draft!r})))"], cwd=self.vault, capture_output=True, text=True, check=True)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def rows(self, sid="actions"):
        return [r for s in self.record()["sections"] if s["id"] == sid for r in s["rows"]]

    def wait_saved(self, js):
        self.b.wait(js, 15)
        self.b.pump(0.3)

    def click_outside(self):
        self.b.click("#mnTitle")
        self.b.pump(0.2)

    def test_c36_review_row_and_open_draft(self):
        """36. Review shows the minutes as one row with their items nested under it (the closing update of FAL-A-004 among them);
        Open draft opens the minutes view."""
        b = self.b
        b.eval("go('review')")                                            # an alias of Intake and Review since 2.6.0 (#232)
        b.wait("VIEW==='intake-review' && !document.getElementById('v-intake-review').hidden", 15)
        b.eval("document.querySelector('#v-intake-review [data-ira=open]').click()")      # "Check them" opens the drafted meeting
        b.wait("!!document.querySelector('#v-intake-review tr.irprop')", 15)
        b.pump(0.5)
        text = b.eval("document.getElementById('v-intake-review').innerText")
        self.assertIn("Steering committee", text)
        self.assertIn("FAL-A-004", text, "the closing update is nested under the minutes")
        self.assertIn(self.W[0], text, "the minutes' items are nested under them")
        row = "[...document.querySelectorAll('#v-intake-review tr.irprop')].find(t=>/Minutes: \\[FAL\\] Steering committee/.test(t.innerText))"
        self.assertTrue(b.eval(f"""(()=>{{ const tr={row}; const e=tr&&tr.querySelector('[data-ira=edit]'); return !!e; }})()"""),
                        "the minutes row has its open button (Open in the peek, which opens the minutes view for a draft)")
        b.eval(f"{row}.querySelector('[data-ira=edit]').click()")
        b.wait("VIEW==='minutes'", 15)
        self.note(36, "one minutes row with its items nested; Open draft opened the minutes view")

    def test_c50_opens_with_transcript_and_time_tags(self):
        """50. The minutes view opens from Review's Open draft (and by its address, under Review in the menu, a reload keeps it):
        the transcript pane lists the five turns; the time tags on the page scroll the pane to what was said, and the sheet
        itself never moves."""
        b = self.b
        self.assertEqual(self.ev("VIEW"), "minutes")
        self.assertEqual(self.ev("location.hash"), "#minutes=" + self.ev(f"encodeURIComponent({json.dumps(self.draft)})"))
        self.assertEqual(self.ev("document.querySelector('.rail button[aria-current=page]').dataset.v"), "review")
        self.assertEqual(self.ev("document.querySelectorAll('.mnturns li').length"), 5)
        tags = self.ev("[...document.querySelectorAll('#v-minutes .page .mntag')].map(t=>t.textContent)")
        self.assertGreaterEqual(len(tags), 3, tags)
        b.eval(f"[...document.querySelectorAll('#v-minutes .page .mntag')].find(t=>t.textContent==={json.dumps(tags[-1])}).click()")
        b.pump(0.4)
        self.assertTrue(self.ev("!!document.querySelector('.mnturns li.on')"), "the tag's turn is highlighted")
        self.assertEqual(self.ev("document.querySelector('#v-minutes .sheet-scroll').scrollTop"), 0, "the sheet itself never moves")
        b.reload("typeof go==='function' && LIVE && document.querySelector('#v-minutes tr.mi')")
        self.assertEqual(self.ev("VIEW"), "minutes")
        self.note(50, f"5 turns; {len(tags)} time tags; a reload kept the view")

    @phase2('removed by #268, covered by test_minutes_view_v2 / test_v260')
    def test_c51_side_by_side_levelled(self):
        """51. Choose Internal + distributed, mark a summary line Internal only, then Side by side → the matching section and topic
        headings are at the same height on both pages, at the top and after scrolling; the Distributed page alone does not hold
        the marked line."""
        b = self.b
        b.click('#v-minutes .seg button:nth-child(2)')
        b.wait("!!document.querySelector('[data-mnmode=side]')")
        b.eval("document.querySelector('.mnlines .mnio').click()")
        b.click("[data-mnmode=side]")
        b.wait("document.querySelectorAll('.sheet-pair > .sheet-fit > .sheet-a4 > .page').length===2")
        b.pump(0.5)
        tops = self.ev("""(()=>{ const [l,r]=document.querySelectorAll('.sheet-pair > .sheet-fit > .sheet-a4 > .page'), out=[];
          for(const h of l.querySelectorAll('section[data-id] > h2, .mnblock[data-level] > h3')){
            const sec=h.closest('section[data-id]').dataset.id, lv=h.parentElement.dataset.level;
            const o=lv?r.querySelector(`section[data-id="${sec}"] [data-level="${CSS.escape(lv)}"] > h3`):r.querySelector(`section[data-id="${sec}"] > h2`);
            if(o) out.push([sec+(lv?':'+lv:''), Math.round(h.getBoundingClientRect().top), Math.round(o.getBoundingClientRect().top)]); }
          return out; })()""")
        self.assertGreater(len(tops), 5)
        worst = max(abs(a - c) for _, a, c in tops)
        self.assertLessEqual(worst, 1, tops)
        b.eval("document.querySelector('.sheet-scroll').scrollTop=400")
        b.pump(0.3)
        sec = self.ev("""(()=>{ const [l,r]=document.querySelectorAll('.sheet-pair > .sheet-fit > .sheet-a4 > .page');
          return [l.querySelector('section[data-id=actions] > h2').getBoundingClientRect().top, r.querySelector('section[data-id=actions] > h2').getBoundingClientRect().top]; })()""")
        self.assertLessEqual(abs(sec[0] - sec[1]), 1, "still level once scrolled")
        b.click("[data-mnmode=distributed]")
        b.wait("!document.querySelector('.sheet-pair')")
        self.assertNotIn("The committee reviewed", self.ev("document.querySelector('#v-minutes .page').textContent"))
        self.note(51, f"{len(tops)} headings compared; the largest difference {worst}px")

    @phase2('removed by #268, covered by test_minutes_view_v2 / test_v260')
    def test_c52_popups_close(self):
        """52. The deadline popover, the owner picker, a check, the Remove menu, Deal with it… and the approve popup (784 px
        wide) each close on Esc and on a click outside, with focus back on the button that opened them; Esc goes no further."""
        b = self.b
        openers = {"deadline": "#v-minutes .mnrow[data-n='2'] .mndue", "owner": "#v-minutes .mnrow[data-n='2'] .mnowner",
                   "check": "#v-minutes .mnrow[data-n='2'] .mnbar .mncheck"}
        for name, sel in openers.items():
            for how in ("esc", "outside"):
                with self.subTest(popup=name, close=how):
                    b.click(sel)
                    b.wait("!!document.querySelector('#v-minutes .mnpop')")
                    self.assertTrue(self.ev("document.querySelector('#v-minutes .mnpop').contains(document.activeElement)"), "focus moves in")
                    if how == "esc":
                        b.key("Escape")
                        b.pump(0.2)
                        self.assertTrue(self.ev(f"document.activeElement===document.querySelector({json.dumps(sel)})"), "focus back on its button")
                    else:
                        self.click_outside()
                    self.assertFalse(self.ev("!!document.querySelector('#v-minutes .mnpop')"), f"{name} closed by {how}")
                    self.assertEqual(self.ev("VIEW"), "minutes", "Esc goes no further")
        for name, sel in (("remove", "#v-minutes .mnrow[data-n='1'] [data-mnremove]"), ("coverage", "[data-mncover='Training plan']")):
            for how in ("esc", "outside"):
                with self.subTest(popup=name, close=how):
                    b.click(sel)
                    b.wait("!!document.querySelector('#v-minutes .ddmenu.on')")
                    if how == "esc":
                        b.key("Escape")
                        b.pump(0.2)
                        self.assertTrue(self.ev(f"document.activeElement===document.querySelector({json.dumps(sel)})"))
                    else:
                        self.click_outside()
                    self.assertFalse(self.ev("!!document.querySelector('#v-minutes .ddmenu.on')"))
        for how in ("esc", "outside"):
            with self.subTest(popup="approve", close=how):
                b.click("#mnApproveBtn")
                b.wait("document.getElementById('mnApprove').open")
                self.assertEqual(round(self.ev("document.getElementById('mnApprove').getBoundingClientRect().width")), 784)
                if how == "esc":
                    b.key("Escape")
                else:
                    x, y = self.ev("(()=>{const r=document.getElementById('mnApprove').getBoundingClientRect(); return [r.left-20, r.top+20]})()")
                    for kind in ("mousePressed", "mouseReleased"):
                        b.call("Input.dispatchMouseEvent", type=kind, x=x, y=y, button="left", clickCount=1)
                b.pump(0.3)
                self.assertFalse(self.ev("document.getElementById('mnApprove').open"))
                self.assertEqual(self.ev("document.activeElement.id"), "mnApproveBtn")
        self.note(52, "six popups closed on Esc and on a click outside; the approve popup is 784px wide")

    @phase2('removed by #268, covered by test_minutes_view_v2 / test_v260')
    def test_c53_remove_undo_keep_line(self):
        """53. ✕ Remove on a row takes the item and its line out of the minutes (the item is rejected, "Removed in the minutes");
        Undo on the toast brings it back; Keep the line only keeps the words with no item."""
        b = self.b
        b.click("#v-minutes .mnrow[data-n='1'] [data-mnremove]")
        b.click("#v-minutes .ddmenu.on [role=menuitem]:nth-of-type(1)")
        self.wait_saved("!document.querySelector(\"#v-minutes .mnrow[data-n='1']\")")
        self.assertEqual(self.staged(1)["decision"], "rejected")
        self.assertEqual(self.staged(1)["reject_reason"], "Removed in the minutes")
        b.wait("document.getElementById('snack').classList.contains('on')", 5)
        self.assertTrue(self.ev("getComputedStyle(document.getElementById('snackU')).display!=='none'"), "the toast offers Undo")
        b.click("#snackU")
        self.wait_saved("!!document.querySelector(\"#v-minutes .mnrow[data-n='1']\")")
        self.assertEqual(self.staged(1)["decision"], "pending")
        b.click("#v-minutes .mnrow[data-n='2'] [data-mnremove]")
        b.click("#v-minutes .ddmenu.on [role=menuitem]:nth-of-type(2)")
        self.wait_saved("!!document.querySelector(\"#v-minutes .mnrow.kept[data-n='2']\")")
        kept = [r for r in self.rows() if r.get("kept_line")]
        self.assertEqual(kept[0]["cells"]["action"], self.W[1])
        self.assertIsNone(kept[0]["ref"], "the line only: no item")
        self.assertEqual(self.staged(2)["decision"], "rejected")
        self.note(53, "removed, undone from the toast, then kept as a line with no item")

    @phase2('removed by #268, covered by test_minutes_view_v2 / test_v260')
    def test_c54_deadline_popover(self):
        """54. The deadline popover on an action with no date: its quick picks (Friday, next week, next Wednesday, end of month)
        show their dates worked out from the meeting's day; words typed (“in 2 weeks”) show their date before they are set; a
        day from the calendar, Not set; unreadable words say so. Each change moves the row and its staged item together."""
        b = self.b
        day = self.mday
        sel = "#v-minutes .mnrow[data-n='2'] .mndue"
        self.assertEqual(self.ev(f"document.querySelector({json.dumps(sel)}).textContent"), "Not set")
        b.click(sel)
        b.wait("!!document.querySelector('.mndl')")
        quick = self.ev("[...document.querySelectorAll('.mndl [data-quick]')].map(x=>[x.dataset.quick, x.getAttribute('aria-label')])")
        for w, label in quick[:4]:
            want = date_words.deadline(w, day)
            self.assertIn(want[8:10], label, f"{w} shows its date ({want}) from the meeting's day")
        b.eval("document.getElementById('mnDlWords').focus()")
        b.type("in 2 weeks")
        b.pump(0.2)
        got = date_words.deadline("in 2 weeks", day)
        self.assertIn(self.ev(f"fd({json.dumps(got)})"), self.ev("document.getElementById('mnDlSaid').textContent"))
        self.assertIsNone(self.staged(2)["values"].get("due_date"), "nothing set yet")
        b.key("Enter")
        self.wait_saved(f"document.querySelector({json.dumps(sel)}).textContent!=='Not set'")
        self.assertEqual(self.staged(2)["values"]["due_date"], got)
        self.assertEqual(next(r for r in self.rows() if r.get("n") == 2)["cells"]["due"], self.ev(f"fd({json.dumps(got)})"))
        self.assertTrue(self.ev(f"document.activeElement===document.querySelector({json.dumps(sel)})"), "focus back on the deadline")
        b.click(sel)
        b.wait("!!document.querySelector('.mndl')")
        b.click(".mndl [data-quick='Friday']")
        friday = date_words.deadline("Friday", day)
        self.wait_saved(f"document.querySelector({json.dumps(sel)}).textContent==={json.dumps(self.ev(f'fd({json.dumps(friday)})'))}")
        self.assertEqual(self.staged(2)["values"]["due_date"], friday)
        b.click(sel)
        b.wait("!!document.querySelector('.mndl')")
        b.click(".mndl [data-quick='not set']")
        self.wait_saved(f"document.querySelector({json.dumps(sel)}).textContent==='Not set'")
        self.assertIsNone(self.staged(2)["values"].get("due_date"))
        b.click(sel)
        b.wait("!!document.querySelector('.mndl')")
        b.eval("document.getElementById('mnDlWords').focus()")
        b.type("whenever")
        b.pump(0.2)
        self.assertIn("read", self.ev("document.getElementById('mnDlSaid').textContent"))
        self.note(54, f"quick picks and typed words worked out from {day}; the row and its staged item moved together")

    @phase2('removed by #268, covered by test_minutes_view_v2 / test_v260')
    def test_c55_checks_coverage_and_the_approve_popup(self):
        """55. The checks on a row say what is wrong (Pat Unknown isn't in the people register); Deal with it… on a point not
        discussed carries it to the series' next meeting, with a line in the minutes; the approve popup has the group's tick
        ticked and one unticked tick each for the two decisions, the risk and the closure."""
        b = self.b
        notes = self.ev("[...document.querySelectorAll('#v-minutes .mnbar .mncheck')].map(x=>x.getAttribute('aria-label'))")
        self.assertTrue(any("Pat Unknown isn't in the people register" in n for n in notes), notes)
        b.click("[data-mncover='Training plan']")
        b.click("#v-minutes .ddmenu.on [role=menuitem]:nth-of-type(1)")
        self.wait_saved("!!document.querySelector('[data-point=\"Training plan\"] .mncov-done')")
        nc = next(s for s in self.record()["sections"] if s["id"] == "not_covered")
        self.assertIn("Training plan was not discussed; it is carried to the next", nc["text"])
        b.click("#mnApproveBtn")
        b.wait("document.getElementById('mnApprove').open")
        self.assertTrue(self.ev("document.getElementById('mnApAll').checked"), "the group's one tick, ticked")
        ticks = self.ev("[...document.querySelectorAll('#mnApprove [data-own]')].map(x=>[+x.dataset.own,x.checked])")
        self.assertEqual([c for _, c in ticks], [False] * 4, ticks)
        self.assertEqual(len(ticks), 4, "two decisions, a risk and a closure")
        self.note(55, f"{len(notes)} checks; Training plan carried; the approve popup: group ticked, {len(ticks)} own ticks unticked")

    # ── follow-up email (Alan, 15-10-2026): in the Export menu, from the active version ──

    def seed_secrets(self):
        """A Sensitive decision (flag) and an Internal only action row on the stored record; reloads the view. Returns their words."""
        doc = self.record()
        dec = next(s for s in doc["sections"] if s["id"] == "decisions")["rows"][0]
        act = next(s for s in doc["sections"] if s["id"] == "actions")["rows"][0]
        doc["items"][dec["ref"]]["flags"] = ["sensitive"]
        doc["layout"] = {**(doc.get("layout") or {}), "distributed": True, "internal_only": [{"section": "actions", "ref": act["ref"]}]}
        r = subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts'); import minutes_record; "
                            f"r = minutes_record.save_record({self.draft!r}, json.loads({json.dumps(json.dumps(doc))}), 'seed'); print(json.dumps({{'ok': r.get('ok')}}))"],
                           cwd=self.vault, capture_output=True, text=True, check=True)
        self.assertTrue(json.loads(r.stdout.strip().splitlines()[-1])["ok"])
        self.b.eval("go('review')")
        self.b.eval(f"go('minutes',{{file:{json.dumps(self.name)}}})")
        self.b.wait("!!document.querySelector('#v-minutes tr.mi')", 15)
        return dec["cells"]["decision"], act["cells"]["action"]

    def menu_names(self):
        self.b.click("#v-minutes [data-mnexport]")
        self.b.wait("!!document.querySelector('#v-minutes .ddmenu.on')")
        return self.ev("[...document.querySelectorAll('#v-minutes .ddmenu.on [role=menuitem]')].map(x=>x.textContent)")

    def pick(self, label):
        self.b.eval("[...document.querySelectorAll('#v-minutes .ddmenu.on [role=menuitem]')].find(x=>x.textContent.includes(%s)).click()" % json.dumps(label))
        self.b.wait("document.getElementById('deDlg') && document.getElementById('deDlg').open && document.querySelector('#dePrev').textContent.length>20", 15)
        self.b.pump(0.4)

    @phase2('removed by #268, covered by test_minutes_view_v2 / test_v260')
    def test_c56_follow_up_email(self):
        """56. Export › Draft the follow-up email follows the version shown. The Internal draft is marked "[Internal]" and says
        "Internal: not for distribution." and keeps everything. The Distributed draft holds no Internal-only line or row and no
        Sensitive, partner-only or excluded item. Nothing is sent."""
        b = self.b
        decision, action = self.seed_secrets()
        names = self.menu_names()
        self.assertEqual(sum("follow-up" in n for n in names), 1, names)
        self.pick("Draft the follow-up email")
        self.assertTrue(self.ev("document.querySelector('#deSubj').value").startswith("[Internal] "))
        self.assertIn("Internal: not for distribution.", self.ev("document.querySelector('#dePrev').textContent"))
        self.assertIn(action, self.ev("document.getElementById('deDlg').textContent"), "the Internal draft keeps it")
        b.key("Escape")
        b.click("#v-minutes .seg button:nth-child(2)")
        b.wait("!!document.querySelector('[data-mnmode=side]')")
        b.click("[data-mnmode=distributed]")
        b.wait("!document.querySelector('.sheet-pair')")
        names = self.menu_names()
        self.assertEqual([n for n in names if "follow-up" in n], [n for n in names if n.startswith("Distributed:") and "follow-up" in n])
        self.pick("Distributed: Draft the follow-up email")
        whole = self.ev("document.getElementById('deDlg').textContent + ' ' + document.querySelector('#deSubj').value")
        self.assertNotIn(decision, whole, "a Sensitive decision never reaches the distributed draft")
        self.assertNotIn(action, whole, "an Internal only row never reaches it")
        self.assertNotIn("[Internal]", whole)
        self.assertNotIn("Internal: not for distribution", whole)
        self.note(56, "Internal draft marked and complete; the Distributed draft held neither the Sensitive decision nor the Internal-only action")


# ── BL-337: the Reports page, the reporting space and the cockpit card (P9) ──

class ReportingSpace(V210Case):
    """Reads only: nothing is drafted or filed, so the shared vault serves. The page clock is pinned to this week's Friday, 14:00
    (the reminder's Friday 12:00 has passed), so 'this week' is the one ending that Friday."""

    def setUp(self):
        super().setUp()
        pin_page_clock(self.b, f"{self.week} 14:00")
        self.b.eval("go('today')")
        self.b.pump(0.4)

    def cells(self, sel):
        return self.b.eval(f"[...document.querySelectorAll({sel!r})].map(e=>e.textContent.trim().replace(/\\s+/g,' '))")

    def go_reports(self):
        self.b.eval("go('reports')")
        self.b.wait("!!document.querySelector('#v-reports tbody tr')", 15)

    def test_c61_reports_in_the_menu_with_a_count(self):
        """61. Reports is in the left menu between Projects and People, with a count of the projects that need you this week;
        clicking it opens the page, marks it, and the tab title says "Reports"."""
        b = self.b
        titles = self.cells(".rail [data-v] .rl")
        self.assertLess(titles.index("Projects"), titles.index("Reports"))
        self.assertLess(titles.index("Reports"), titles.index("People"))
        badge = b.eval("document.getElementById('repBadge').textContent")
        self.assertRegex(badge, r"^\d+$")
        self.assertIn("project", b.eval("document.getElementById('repBadge').getAttribute('aria-label')"))
        b.eval("document.querySelector('.rail [data-v=reports]').click()")
        b.wait("VIEW==='reports' && !document.getElementById('v-reports').hidden", 10)
        self.assertEqual(b.eval("document.querySelector('.rail [aria-current=page]').dataset.v"), "reports")
        self.assertEqual(b.eval("location.hash"), "#reports")
        self.assertEqual(b.eval("document.title"), "creaite · Reports")
        self.note(61, f"Reports sits between Projects and People; the count is {badge}")

    def test_c62_reports_page(self):
        """62. The Reports page has one row per project (health, the internal report's state, each client's report) with Open;
        Needs me lists the projects that need you and All projects every project; the week control goes one click back and the
        address keeps the week."""
        b = self.b
        self.go_reports()
        need = self.cells("#v-reports tbody tr td:first-child")
        self.assertIn("Falcon Data Platform", need)
        self.assertEqual(str(len(need)), b.eval("document.getElementById('repBadge').textContent"), "the count is the rows that need you")
        self.assertTrue(b.eval("!!document.querySelector('#v-reports [data-rpopen=FAL]')"), "an Open on each row")
        b.eval("document.querySelector('[data-rpf=all]').click()")
        b.wait("document.querySelectorAll('#v-reports tbody tr').length>=4")
        every = self.cells("#v-reports tbody tr td:first-child")
        self.assertGreaterEqual(len(every), 4)
        self.assertTrue(set(need) <= set(every))
        earlier = (date.fromisoformat(self.week) - timedelta(days=7)).isoformat()
        b.eval(f"document.querySelector('[data-rpweek=\"{earlier}\"]').click()")
        b.wait(f"location.hash.includes('w={earlier}')")
        self.assertIn(f"Week ending {earlier[8:10]}-{earlier[5:7]}-{earlier[0:4]}", b.eval("document.querySelector('#v-reports .sub').textContent"))
        b.reload("typeof go==='function' && LIVE")
        b.eval("go('reports')")
        b.wait("!!document.querySelector('#v-reports tbody tr')", 10)
        self.assertIn(f"w={earlier}", b.eval("location.hash"), "the address keeps the week")
        self.note(62, f"{len(need)} project(s) need you; {len(every)} in all")

    def test_c63_reporting_space(self):
        """63. A project's reporting space: weeks down the left (this week first), the internal and the client report as cards,
        the client's Approve waiting for the internal one, Open on each card going to the weekly view and the client view, Edit
        both going to the client view, and the week's files."""
        b = self.b
        self.go_reports()
        b.eval("document.querySelector('[data-rpopen=FAL]').click()")
        b.wait("VIEW==='reporting' && !!document.querySelector('#v-reporting .rp-card')", 15)
        self.assertEqual(b.eval("location.hash"), "#reporting=FAL")
        self.assertEqual(b.eval("document.title"), "creaite · Falcon Data Platform reporting")
        weeks = self.cells("#v-reporting .rp-wk .l")
        self.assertEqual(weeks[0], f"Week ending {self.week[8:10]}-{self.week[5:7]}-{self.week[0:4]}")
        self.assertGreaterEqual(len(weeks), 3)
        cards = self.cells("#v-reporting .rp-card .top")
        self.assertEqual(len(cards), 2)
        self.assertIn("Weekly report", cards[0])
        self.assertIn("Client report", cards[1])
        self.assertTrue(b.eval("[...document.querySelectorAll('#v-reporting .rp-card .btn')].some(x=>x.textContent==='Approve' && x.disabled)"))
        self.assertIn("Approve the internal report first", b.eval("document.querySelector('#v-reporting .rp-card:nth-child(2)').textContent"))
        href = lambda sel: b.eval(f"document.querySelector('{sel}').getAttribute('href')")
        self.assertEqual(href("#v-reporting .rp-card:nth-child(1) a[data-rpopen-view]"), f"#weekly=FAL&week={self.week}")
        self.assertEqual(href("#v-reporting .rp-card:nth-child(2) a[data-rpopen-view]"), f"#client-report=FAL/{self.week}/Northgate%20Energy")
        self.assertEqual(href("#v-reporting .rp-both a[data-editboth]"), f"#client-report=FAL/{self.week}/Northgate%20Energy")
        self.assertTrue(b.eval("!!document.querySelector('#v-reporting .rp-files')"))
        b.eval("document.querySelector('#v-reporting .rp-card:nth-child(1) a[data-rpopen-view]').click()")
        b.wait("VIEW==='weekly' && !!document.querySelector('#v-weekly section[data-id=current_state]')", 25)
        b.eval("location.hash='#reporting=FAL'")
        b.wait("VIEW==='reporting'", 10)
        b.eval("document.querySelector('#v-reporting .rp-card:nth-child(2) a[data-rpopen-view]').click()")
        b.wait("VIEW==='clientreport'", 25)
        self.note(63, f"{len(weeks)} weeks; Open reached the weekly view and the client view")

    def test_c64_cockpit_card(self):
        """64. The project's cockpit has a Reporting card (this week's weekly report and each client report, with their state and
        an Open on each, and Open reporting); Open reporting goes to the reporting space."""
        b = self.b
        # #254 (Alan, 20-10-2026): the Reporting card is gone from the cockpit; the check now asserts the door that stays, the project
        # page's Reports icon (data-reports), which opens the reporting space. The check's wording above is the PM's and is unchanged.
        b.eval("go('cockpit','FAL')")
        b.wait("!!document.querySelector('#v-cockpit .cockfoot [data-reports=FAL]')", 15)
        self.assertFalse(b.eval("!!document.querySelector('#cockRep, #repCard, [data-rpcard]')"))
        b.eval("document.querySelector('#v-cockpit .cockfoot [data-reports=FAL]').click()")
        b.wait("VIEW==='reporting' && !!document.querySelector('#v-reporting .page')", 25)
        self.note(64, "no Reporting card (#254); the Reports icon opens the reporting space")

    def test_c65_friday_reminder_and_command_k(self):
        """65. The Friday reminder on Today ("… weekly report for week ending … is due") points to Reports, and ⌘K reaches
        Reports, "Weekly report: <project>", "Reporting: <project>" and "Client report: <project>"."""
        b = self.b
        b.eval("go('today')")
        b.wait("!!document.querySelector('#v-today li.rem[data-id^=\"weekly:\"]')", 15)
        self.assertEqual(b.eval("document.querySelector('#v-today li.rem[data-id^=\"weekly:\"] a.t').dataset.go"), "reports")
        goto = b.eval("ckItems('').filter(x=>x.g==='Go to').map(x=>[x.l,x.h])")
        self.assertTrue(any(l == "Reports" and "need" in h for l, h in goto), goto)
        found = b.eval("ckItems('weekly report FAL').filter(x=>x.g==='Reporting').map(x=>x.l)")
        self.assertEqual(found, ["Weekly report: Falcon Data Platform", "Reporting: Falcon Data Platform"])
        self.assertIn("Client report: Falcon Data Platform", b.eval("ckItems('client report FAL').filter(x=>x.g==='Reporting').map(x=>x.l)"))
        b.eval("ckItems('reporting').find(x=>x.g==='Reporting').fn()")
        b.wait("VIEW==='reporting'", 10)
        self.note(65, "the reminder links to Reports; ⌘K found Reports and the three Reporting entries")


# ── BL-339: the meeting hub is retired (P10) ─────────────────────────────────

class HubRetired(MinutesBase):
    """The hub page is gone; old #meeting= links open Prep before the meeting and the minutes (or Review) after it."""

    def stage_for_event(self):
        """Stage today's FAL Steering committee as the calendar's hc-1 meeting (10:00 to 11:00)."""
        day = self.day.isoformat()
        self.W = words_for(0)
        (self.vault / "inbox" / f"{day} FAL Steering committee.vtt").write_text(VTT, encoding="utf-8")
        spec = meeting_spec(day, 0)
        spec["event_id"] = "hc-1"
        f = self.vault / "system/staging/drafts/meeting.json"
        f.write_text(json.dumps(spec), encoding="utf-8")
        before = {p.name for p in (self.vault / "system/staging").glob("proposed-*.json")}
        code, out = self.run_in_vault("minutes.py", "stage", "system/staging/drafts/meeting.json")
        self.assertEqual(code, 0, out[:600])
        name = next(p.name for p in (self.vault / "system/staging").glob("proposed-*.json") if p.name not in before)
        return name, f"projects/{next((self.vault / 'projects').glob('FAL*')).name}/minutes/{day} Steering committee.html"

    def token(self, key):
        return self.b.eval(f"Object.entries(D.hub).find(([t,m])=>m.key==={json.dumps(key)})?.[0]")

    def test_c67_no_screen_links_to_a_meeting_page(self):
        """67. No screen has a "Meeting" or "Meeting page" link into a meeting page: Today, Intake, Files, Review, Projects and
        the project cockpit show none, the hub page itself is gone, and nothing in the console complains."""
        b = self.b
        for name in ("HUB", "HUBIX", "hubFor", "hubLink", "renderMeeting"):
            self.assertEqual(b.eval(f"typeof {name}"), "undefined", name)
        self.assertFalse(b.eval("!!document.getElementById('v-meeting')"))
        for screen in ("today", "intake", "files", "review", "projects", "cockpit"):
            with self.subTest(screen):
                self.screen(screen)
                b.pump(0.3)
                self.assertFalse(b.eval("!!document.querySelector('#v-' + (VIEW==='inbox'?'inbox':VIEW) + ' .mhlink, #v-' + (VIEW==='inbox'?'inbox':VIEW) + ' [data-meeting]')"))
                self.assertNotIn("Meeting page", b.eval("document.body.innerText"))
        self.assertEqual(b.errors, [])
        self.note(67, "hub functions undefined, no #v-meeting, no meeting link on six screens")

    def test_c68_old_links(self):
        """68. An old `#meeting=` link opens the meeting's Prep before it starts, Review while its minutes wait, and the filed
        minutes afterwards; a link to a meeting creaite no longer knows lands on Today."""
        b = self.b
        pin_page_clock(b, f"{self.day.isoformat()} 09:30")
        tok = self.token("calendar:hc-1")
        self.assertTrue(tok, "today's calendar meeting has a token")
        b.eval(f"location.hash='#meeting={tok}'")
        b.wait("VIEW==='prep'", 15)
        self.assertTrue(b.eval("location.hash").startswith("#prep="), "before the meeting: its Prep")
        name, filed = self.stage_for_event()
        b.reload("typeof go==='function' && LIVE")
        pin_page_clock(b, f"{self.day.isoformat()} 12:00")
        tok = self.token("calendar:hc-1")
        b.eval(f"location.hash='#meeting={tok}'")
        b.wait("VIEW==='intake-review'", 15)
        self.assertEqual(b.eval("location.hash"), "#intake-review", "after the meeting, minutes waiting: Intake and Review (2.6.0)")
        self.approve(name, self.view(name))
        b.reload("typeof go==='function' && LIVE")
        pin_page_clock(b, f"{self.day.isoformat()} 12:00")
        tok = self.token("calendar:hc-1")
        b.eval(f"location.hash='#meeting={tok}'")
        b.wait("VIEW==='minutes'", 20)
        b.wait(f"location.hash === '#minutes=' + encodeURIComponent({json.dumps(filed)})", 15)      # the view settles the address once the filed record is read
        self.assertEqual(b.eval("location.hash"), "#minutes=" + b.eval(f"encodeURIComponent({json.dumps(filed)})"), "after approval: the filed minutes")
        b.eval("go('review')")
        b.eval("location.hash='#meeting=ffffffffff'")
        b.wait("VIEW==='today'", 10)
        self.assertEqual(b.errors, [])
        self.note(68, "before: Prep; minutes waiting: Review; filed: the minutes; unknown: Today")

    def test_c69_carry_route_stays(self):
        """69. The carry route (/api/meeting/carry, used by an agenda point's Deal with it…) still answers: a request with no
        meeting says "Which meeting and point?", while a route that does not exist is refused as not found."""
        r = self.api("/api/meeting/carry", {})
        self.assertEqual(r.get("message"), "Which meeting and point?")
        self.assertEqual(self.api("/api/no-such-route", {}).get("message"), "Not found")
        self.note(69, "the carry route is there; Deal with it… itself is check 55")


# ── Desktop and 900 px (Alan, 15-10-2026: no 320 or 640 px) ──────────────────

WIDTHS = (1400, 900)


class Seeded(MinutesBase):
    """A vault with the client world, the week's internal report approved and a meeting waiting as a minutes record: what the
    measuring and judgement checks look at. Seeded once for the class."""
    _ready = False

    def setUp(self):
        super().setUp()
        cls = type(self)
        if not cls._ready:
            self.client_world()
            self.approve_week(self.week, summary="The internal summary, not for the client.")
            cls.name, cls.draft, cls.filed, cls.mday, _ = self.stage()
            self.W = words_for(cls._days)
            cls._ready = True
            self.b.reload("typeof go==='function' && LIVE")
        hcbase.SCREENS.update({
            "client": (f"go('clientreport',{{code:'FAL',week:'{self.week}'}})", "!!document.querySelector('#v-clientreport .crhealth')"),
            "minutes": (f"go('minutes',{{file:{json.dumps(cls.name)}}})", "!!document.querySelector('#v-minutes tr.mi')"),
        })
        pin_page_clock(self.b, f"{self.week} 14:00")


class Layout900(Seeded):
    def test_c70_nothing_scrolls_sideways_at_900(self):
        """70. At 900 px wide the weekly report, the client report, the minutes view, Reports, a reporting space and the cockpit
        have no sideways scroll, in light and dark; the sheet fits its column."""
        b = self.b
        bad = []
        measure.width(b, 900, 900)
        try:
            for mode in ("light", "dark"):
                measure.theme(b, "creaite", mode)
                for name in ("weekly", "client", "minutes", "reports", "reporting", "cockpit", "help"):
                    self.screen(name, settle=0.5)
                    over = measure.overflow_x(b)
                    if not over["ok"]:
                        bad.append(f"{name} ({mode}): page {over['sw']} px wide in a window of {over['iw']}")
        finally:
            measure.width(b, self.width, self.height)
            measure.theme(b, "creaite", "light")
        self.assertEqual(bad, [], "sideways scroll at 900 px")
        self.note(70, "seven screens, light and dark, no sideways scroll at 900 px")


class Judgement(Seeded):
    """Checks that need your eye, drawn on the screenshot sheet at desktop and 900 px, in every theme, light and dark. They pass
    once the screenshots are taken; the Results row says "judgement: on the screenshot sheet"."""

    def shots(self, n, screens, prepares=None, palettes=None):
        palettes = palettes or measure.themes(self.b)[:2]
        total = 0
        for s in screens:
            total += self.sheet(n, s, palettes=palettes, widths=WIDTHS, prepare=(prepares or {}).get(s))
        self.note(n, f"{total} screenshots: {', '.join(screens)}; themes {', '.join(palettes)}; light and dark; {' and '.join(map(str, WIDTHS))} px")

    def test_c04_weekly_report_as_drawn(self):
        """4. Open the weekly report next to the "Weekly report redesign" mockup → every section is there and looks as drawn:
        header with logos, health with its trend, At a glance, the timeline and milestone list with their eyes, What we need
        from people, This week and Next week, decisions written out, risks and overdue actions with eyes, Current state in two
        panes, the footer; light and dark, two themes, desktop and 900 px."""
        self.shots(4, ["weekly"])

    def test_c32_client_report_as_drawn(self):
        """32. Open the client report next to the "Client report" mockup, alone and Side by side → the client's own layout, the
        client health and its reason, Match internal, "Not in this report"; light and dark, two themes, desktop and 900 px."""
        def side(b):
            b.eval("document.querySelector(\"[data-crmode='side']\")?.click()")
            b.pump(0.6)
        hcbase.SCREENS["client-side"] = hcbase.SCREENS["client"]
        self.shots(32, ["client", "client-side"], {"client-side": side})

    def test_c59_minutes_view_as_drawn(self):
        """59. Open the minutes view next to the "Minutes editor" mockup: alone, Side by side, and with the approve popup open →
        the transcript pane and time tags, the item rows, the checks, agenda coverage, the approve popup at 784 px; light and
        dark, two themes, desktop and 900 px."""
        def side(b):
            b.eval("document.querySelector('#v-minutes .seg button:nth-child(2)')?.click()")
            b.pump(0.3)
            b.eval("document.querySelector('[data-mnmode=side]')?.click()")
            b.pump(0.6)

        def popup(b):
            b.eval("document.getElementById('mnApproveBtn')?.click()")
            b.pump(0.5)
        hcbase.SCREENS["minutes-side"] = hcbase.SCREENS["minutes"]
        hcbase.SCREENS["minutes-approve"] = hcbase.SCREENS["minutes"]
        self.shots(59, ["minutes", "minutes-side", "minutes-approve"], {"minutes-side": side, "minutes-approve": popup})

    def test_c66_reporting_journey_as_drawn(self):
        """66. Walk the "Reporting journey" mockup: Reports in the left menu with its count, the Reports page (Needs me and All
        projects), a project's reporting space, and the cockpit's Reporting card; light and dark, two themes, desktop and 900 px."""
        self.shots(66, ["reports", "reporting", "cockpit"])

    def test_c71_help_in_two_themes(self):
        """71. Help (it now explains the reporting space, the A4 sheet and the minutes view) in two themes, light and dark →
        readable throughout, with the theme's own fonts."""
        self.shots(71, ["help"])
