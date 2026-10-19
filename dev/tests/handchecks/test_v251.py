"""#212: creaite 2.5.1's hand checks (dev/handchecks/v2.5.1.md; the walk-through is judgement only), automated against a vault made
from the release zip. DRAFT for the 2.5.1 line (branch handchecks-v251): the fixes are on topic branches and not all built yet, so every
check feature-detects its fix in the vault and SKIPS with the reason when it is absent. Nothing fails for code that has not landed.

Run them all, fill the Results table and make the screenshot sheet:  python3 dev/tools/handcheck.py v2.5.1
Run this file on its own (it makes the vault itself):                 python3 dev/tests/handchecks/test_v251.py
Run a check with its fix absent, to see it red:                       CREAITE_HC_251_FORCE=1 python3 dev/tests/handchecks/test_v251.py

  Hidden234    1 to 6     #234 a left-out weekly row: says Left out, its eye re-shows it from the tracker, no empty export row, a late
                          answer lands nowhere, the client report (own vault; skipped until the vault holds /api/report/reshow)
  Picker235    7 to 9     #235 the Add actions picker with long titles (own vault; the fix is in 2.5.0)
  Followed236  10 to 14   #236 a followed person's conversations on Today (own vault). 10, 12, 13 hold today; 11 waits for Alan's answer
                          to the issue's intent questions (it is skipped until a recorded conversation reaches Needs attention)
  Today237     15 to 17   #237 Today's empty Needs attention and the header "?" (own, empty vault; skipped until the vault holds data-thelp)
  Usage238     18 to 22   #238 Activity › Usage (shared vault; skipped until Activity has a Usage tab; 20 and 21 are not written yet)

Kinds (the sheet's map): 6, 9, 14, 17 and 22 are judgement (screenshots on the sheet, never Pass or Fail); the rest scriptable.
Held-reply technique: dev/tests/test_reshow_switch.py (the reply to /api/report/reshow is held 6 s while another project is opened).
Never Microsoft 365, never a real model: Claude is the hand-check vault's stand-in. Fictional data only (the demo's people).
"""
import json
import os
import re
import sys
import zipfile
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))      # dev/tests
import hcbase
import measure
from hcbase import NOTES, SCREENS, db_rows, phase2, shown
from test_v230 import V230Case

KIND = {**{n: "scriptable" for n in (1, 2, 3, 4, 5, 7, 8, 10, 11, 12, 13, 15, 16, 18, 19, 20, 21)},
        **{n: "judgement" for n in (6, 9, 14, 17, 22)}}
LIVE_ONLY = {}

NOTES.clear()          # test_v230 (imported for its helpers) put its own notes for checks 5 and 11 here
NOTES.update({
    11: "waits for Alan's answer on #236 (where a followed person's conversation belongs): skipped until one reaches Needs attention",
    14: "open questions on #236: private conversations, proposals from a followed person's messages, seen and dismissed history",
    20: "no test yet: needs #238's cards and rows (no DOM to read until it is built)",
    21: "no test yet: needs #238's daily record of the always-loaded files",
})

SCREENS.setdefault("weekly", ("go('weekly',{code:'FAL'})", "document.querySelector('#v-reporting section[data-id=current_state]')"))

FORCE = os.environ.get("CREAITE_HC_251_FORCE") == "1"        # run a check although its fix is not in the vault (to see it red)

DAY0 = "2026-10-23"          # the weekly report's default week in the hand-check vault (today 19-10-2026)
CLIENT_MSG = ("What it is: The revised go-live plan is with the sponsor.\nWhat it means for you: Dates are confirmed once it is approved.\n"
              "What is being done: We are walking the sponsor through the plan.")
INTERNAL_NOTE = "INTERNALONLY hand check note"
DELAY = """(()=>{const f=window.fetch.bind(window); window.fetch=(u,o)=>String(u).endsWith('/api/report/reshow')
  ? (window.__held=(window.__held||0)+1, new Promise(r=>setTimeout(r,6000)).then(()=>f(u,o))) : f(u,o);})()"""


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


class V251Case(V230Case):
    """V230Case (the page's API, seeding, a Python probe in the vault) and what the 2.5.1 checks share."""
    width, height = 1400, 1000

    # ── is the fix in this vault? (feature detection; never fail on code that is not there) ──

    def vtext(self, rel):
        p = self.vault / rel
        return p.read_text(encoding="utf-8", errors="ignore") if p.exists() else ""

    @property
    def fix234(self):
        """#234 (v250-hiddenrow): the read-only route that re-shows a left-out row from the tracker."""
        return "/api/report/reshow" in self.vtext("system/scripts/report_server.py")

    @property
    def fix235(self):
        """#235 (v250-pickerfix, in 2.5.0): the picker's rows size to their text."""
        return bool(re.search(r"\.rs-pick-list\{[^}]*grid-auto-rows:\s*max-content", self.vtext("dashboard.html")))

    @property
    def fix237(self):
        """#237 (v251-todayhelp): the quiet "?" button in the Today header."""
        return "data-thelp" in self.vtext("dashboard.html")

    def need(self, present, what):
        if not present and not FORCE:
            self.skipTest(f"{what} is not in this vault yet; this check runs once it is merged (CREAITE_HC_251_FORCE=1 runs it anyway)")

    # ── the weekly and client report ──

    def wk(self, n=0):
        """The default week's Friday, n weeks on (each check that saves a report works in its own week)."""
        return (date.fromisoformat(DAY0) + timedelta(days=7 * n)).isoformat()

    def draft(self, kind, week=None):
        body = {"kind": kind, "code": "FAL", **({"week_ending": week} if week else {})}
        d = self.api("/api/report/draft", body)
        self.assertTrue(d.get("ok"), d)
        return d

    def overdue(self, doc):
        return next(s for s in doc["sections"] if s["id"] == "overdue")

    def leave_out(self, kind, week=None, blank=None):
        """Save FAL's report of `kind` with every Overdue actions row left out (the eye off), the way a person's click and save do;
        `blank`: a ref whose row is saved shown with empty cells instead (what an earlier build left behind). Returns the refs of the
        rows the saved report no longer holds an item for (the rows that used to draw "Click to write")."""
        d = self.draft(kind, week)
        doc = d["doc"]
        for row in self.overdue(doc)["rows"]:
            if row.get("ref"):
                row["shown"] = bool(blank and row["ref"] == blank)
                if blank and row["ref"] == blank:
                    row["cells"] = {}
        s = self.api("/api/report/save", {"doc": doc, "base_version": d.get("version") or doc.get("version") or None})
        self.assertTrue(s.get("ok"), s)
        back = self.draft(kind, week)["doc"]
        refs = [r["ref"] for r in self.overdue(back)["rows"] if r.get("ref") and r["ref"] not in (back.get("items") or {})]
        self.assertTrue(refs, "premise: the saved report keeps a stub row whose item it no longer holds")
        return refs

    def open_report(self, kind="weekly", week=None, code="FAL"):
        """The report page for `code`: the internal view (weekly) or the Client view."""
        b = self.b
        b.reload("typeof go==='function' && LIVE")
        arg = f"{{code:'{code}'{(', week:' + json.dumps(week)) if week else ''}}}"
        b.eval(f"go('{'clientreport' if kind == 'client' else 'weekly'}',{arg})")
        page = "client" if kind == "client" else "internal"
        b.wait(f"document.querySelector('#v-reporting .page[data-audience={page}] section[data-id=overdue]')", 25)
        b.pump(0.6)
        return f"#v-reporting .page[data-audience={page}] section[data-id=overdue]"

    def row_text(self, sec, ref):
        return self.b.eval(f"(()=>{{ const r=document.querySelector(\"{sec} tr[data-ref='{ref}']\"); return r ? r.textContent.replace(/\\s+/g,' ').trim() : null; }})()")

    def tracker(self, item_id):
        return db_rows(self.vault, "SELECT description, owner, due_date FROM actions WHERE id = ?", item_id)[0]


# ══ #234 ══════════════════════════════════════════════════════════════════════════════════════════════════════════════

class Hidden234(V251Case):
    """Checks 1 to 6. One vault of their own (they save reports and seed an item); each check uses its own week."""
    own_vault = True

    def test_c01_left_out_row_says_left_out(self):
        """1. Weekly report › Overdue actions: turn the eye off on the rows, save, reload the page → each row says "Left out" (and how
        to put it back), never "Click to write"; the ID stays."""
        self.need(self.fix234, "#234 (v250-hiddenrow)")
        week = self.wk(1)
        refs = self.leave_out("weekly", week)
        sec = self.open_report("weekly", week)
        for ref in refs:
            text = self.row_text(sec, ref)
            self.assertIsNotNone(text, f"{ref}: the row is on the page")
            self.assertIn(ref, text)
            self.assertIn("Left out", text, f"{ref}: {text}")
            self.assertNotIn("Click to write", text, f"{ref}: {text}")
        self.assertNotIn("Click to write", self.b.eval(f"document.querySelector('{sec}').innerText"))
        self.note(1, f"{len(refs)} rows ({', '.join(refs)}) say Left out after save and reload")

    def test_c02_the_eye_brings_the_row_back_from_the_tracker(self):
        """2. Turn the eye back on → the row shows the item's text, owner and due date from the tracker, not blank cells."""
        self.need(self.fix234, "#234 (v250-hiddenrow)")
        week = self.wk(2)
        self.leave_out("weekly", week)
        sec = self.open_report("weekly", week)
        ref = "FAL-A-003"
        row = self.tracker(ref)
        b = self.b
        b.wait(f"document.querySelector(\"{sec} tr[data-ref='{ref}'] .wr-eye\")", 10)
        b.eval(f"document.querySelector(\"{sec} tr[data-ref='{ref}'] .wr-eye\").click()")
        wait_for(lambda: row["description"] in (self.row_text(sec, ref) or ""), 20, f"{ref}'s text to come back")
        text = self.row_text(sec, ref)
        self.assertIn(row["owner"], text)
        self.assertIn(shown(row["due_date"]), text)
        self.assertNotIn("Click to write", text)
        self.assertNotIn("Left out", text)
        self.assertEqual(b.eval(f"document.querySelector(\"{sec} tr[data-ref='{ref}'] .wr-eye\").getAttribute('aria-pressed')"), "true")
        self.note(2, f"{ref} back with \"{row['description'][:30]}…\", {row['owner']}, {shown(row['due_date'])}")

    def test_c03_no_empty_row_in_an_export(self):
        """3. With one row left out and one saved blank, export the report (Word and HTML) → neither file has an empty row, and the
        left-out row's text is in neither."""
        self.need(self.fix234, "#234 (v250-hiddenrow)")
        week = self.wk(3)
        blank, left = "FAL-A-002", "FAL-A-003"
        self.leave_out("weekly", week, blank=blank)
        words = [self.tracker(left)["description"], self.tracker(blank)["description"]]
        e = self.api("/api/report/export", {"kind": "weekly", "code": "FAL", "week_ending": week, "fmt": "docx"})
        self.assertTrue(e.get("ok"), e)
        docx = Path(e["path"]) if Path(e["path"]).is_absolute() else self.vault / e["path"]
        with zipfile.ZipFile(docx) as z:
            xml = z.read("word/document.xml").decode("utf-8")
        word_text = re.sub(r"<[^>]+>", "", re.sub(r"</w:t>\s*<w:t[^>]*>", "", xml))
        html = self.export_html(week)
        for kind, text in (("Word", word_text), ("HTML", html)):
            for ref in (left, blank):
                self.assertNotIn(ref, text, f"{kind}: a row for {ref}, which is left out or blank")
            for w in words:
                self.assertNotIn(w, text, f"{kind} holds {w!r}")
        # and no row at all whose editable cells are every one empty (what the blank row used to export as)
        for tr in re.findall(r"<tr[ >].*?</tr>", html, re.DOTALL):
            rich = re.findall(r'<div class="wr-rich[^"]*">(.*?)</div>', tr, re.DOTALL)
            self.assertFalse(rich and not any(re.sub(r"<[^>]+>", "", x).strip() for x in rich), f"HTML: a row with every cell empty: {tr[:160]}")
        for tr in re.findall(r"<w:tr[ >].*?</w:tr>", xml, re.DOTALL):
            self.assertTrue(re.sub(r"<[^>]+>", "", re.sub(r"</w:t>\s*<w:t[^>]*>", "", tr)).strip(), "Word: a table row with every cell empty")
        self.note(3, "Word and HTML: no all-empty row; neither the left-out nor the blank row's words")

    def export_html(self, week, audience="internal"):
        """Export > HTML from the page, as a person does (the hub asks which report; a taken filing name opens the clash dialog,
        whose default, Add a number, is taken). Returns the file's text."""
        b = self.b
        self.open_report("weekly", week)
        reports = self.vault / "projects"
        before = set(reports.glob("*/reports/*"))
        b.eval("document.querySelector('#v-reporting #hubExport').click()")
        b.wait("document.querySelector('[role=menu] [role=menuitem]')", 10)
        b.eval("[...document.querySelectorAll('[role=menu] [role=menuitem]')].find(x=>x.textContent.includes('HTML')).click()")
        b.pump(0.5)
        if b.eval(f"!!document.querySelector('[data-hubpick={audience}]')"):
            b.eval(f"document.querySelector('[data-hubpick={audience}]').click()")

        def found():
            if b.eval("!!document.querySelector('#exportClashDlg[open]')"):
                b.eval("document.querySelector('#exportClashGo').click()")
            return [f for f in reports.glob("*/reports/*") if f not in before and f.suffix == ".html"]
        made = wait_for(found, 60, "the HTML export")
        b.pump(0.6)
        return made[0].read_text(encoding="utf-8")

    def test_c04_a_late_answer_lands_in_no_other_report(self):
        """4. Side by side on Falcon: turn the eye on for a left-out row, and before the answer comes back open another project →
        the other project's page, its report and its saved drafts hold nothing from Falcon's row."""
        self.need(self.fix234, "#234 (v250-hiddenrow)")
        refs = self.leave_out("weekly")                                       # the default week the hub opens
        ref = refs[0]
        mine = self.tracker(ref)["description"]
        b = self.b
        b.reload("typeof go==='function' && LIVE")
        for _ in range(4):                                                    # both reports on, so Side by side is offered
            b.eval("(()=>{ for (const c of ['FAL','ORX']) { const p=P.find(p=>p.code===c); if (p) p.cr=true; } crTick.value++; })()")
            b.pump(0.3)
        b.eval("go('reporting','FAL')")
        b.wait("document.querySelector('#v-reporting .page')", 25)
        b.click("#hubSeg [data-hv='side']")
        b.wait("document.querySelectorAll('#v-reporting .page').length==2", 20)
        b.pump(0.5)
        if not b.eval("typeof weeklyDoc!=='undefined' && typeof crInternal!=='undefined' && typeof crDoc!=='undefined'"):
            self.skipTest("the page does not expose weeklyDoc, crInternal and crDoc (v250-hiddenrow adds them); nothing to read")
        bare = f"#v-reporting .page[data-audience=internal] [data-id=overdue] tr.wr-bare[data-ref='{ref}']"
        b.wait(f"document.querySelector(\"{bare}\")", 10)
        b.eval(DELAY)
        b.eval(f"document.querySelector(\"{bare} .wr-eye\").click()")
        b.pump(0.3)
        self.assertEqual(b.eval("window.__held"), 1, "the eye asked the tracker once, and the answer is held")
        b.eval("go('reporting','ORX')")
        b.wait("weeklyDoc.value && weeklyDoc.value.project==='ORX' && document.querySelector('#v-reporting .page')", 25)
        b.pump(9)                                                            # the held answer arrives (6 s) and any autosave runs
        if b.eval("!!document.querySelector('[data-crmatchall]')"):          # the reviewer's path: Match internal on the other project
            b.eval("window.confirm=()=>true; setTimeout(()=>document.querySelector('[data-crmatchall]').click(),10); 1")
            b.pump(6)
        state = b.eval("""({wk: weeklyDoc.value && weeklyDoc.value.project, ci: crInternal.value && crInternal.value.project,
          cd: crDoc.value && crDoc.value.project, page: document.querySelector('#v-reporting').innerText,
          blob: JSON.stringify([weeklyDoc.value, crInternal.value, crDoc.value])})""")
        self.assertEqual(state["wk"], "ORX")
        self.assertIn(state["ci"], (None, "ORX"))
        self.assertIn(state["cd"], (None, "ORX"))
        for w in (mine, ref):
            self.assertNotIn(w, state["page"], f"ORX's page shows {w!r}")
            self.assertNotIn(w, state["blob"], f"ORX's documents on the page hold {w!r}")
        for kind in ("weekly", "client"):
            d = self.api("/api/report/draft", {"kind": kind, "code": "ORX"})
            if d.get("ok"):
                self.assertNotIn(mine, json.dumps(d["doc"]), f"ORX's {kind} draft holds {mine!r}")
        for f in (self.vault / "system/staging/drafts").glob("*Orbit*"):
            self.assertNotIn(mine, f.read_text(encoding="utf-8", errors="ignore"), f"{f.name} holds {mine!r}")
        self.note(4, f"reply held 6 s, ORX opened (Match internal pressed when offered): ORX's page, documents and drafts hold nothing of {ref}")

    def test_c05_client_report_left_out_row(self):
        """5. Client report › Overdue actions: leave a row out, save, reload → "Left out", not "Click to write"; turn the eye on →
        the client-safe words (the client message, owner and due), never the item's internal title or its internal note."""
        self.need(self.fix234, "#234 (v250-hiddenrow)")
        self.seed([{"op": "update", "table": "actions", "id": "FAL-A-002",
                    "changes": {"client_visible": 1, "client_message": CLIENT_MSG, "latest_update": INTERNAL_NOTE}}])
        week = self.wk(5)
        self.leave_out("client", week)
        sec = self.open_report("client", week)
        ref = "FAL-A-002"
        text = self.row_text(sec, ref)
        self.assertIsNotNone(text, "the client report's row is on the page")
        self.assertIn("Left out", text)
        self.assertNotIn("Click to write", text)
        b = self.b
        b.eval(f"document.querySelector(\"{sec} tr[data-ref='{ref}'] .wr-eye\").click()")
        wait_for(lambda: "go-live plan is with the sponsor" in (self.row_text(sec, ref) or ""), 20, "the client row to come back")
        text = self.row_text(sec, ref)
        self.assertIn("Alan Carter", text)
        self.assertIn("17-10-2026", text)
        internal = self.tracker(ref)["description"]
        self.assertNotIn(internal, text, "the internal title is not in the client report")
        page = b.eval("document.querySelector('#v-reporting .page[data-audience=client]').innerText")
        self.assertNotIn(INTERNAL_NOTE, page)
        self.assertNotIn(INTERNAL_NOTE, json.dumps(self.draft("client", week)["doc"]))
        self.note(5, "client row back with the client message only; no internal title or note on the page or in the draft")

    def test_c06_left_out_row_look(self):
        """6. (judgement) A left-out row reads as left out, not as a row waiting for text: the ID, "Left out" and the hint, in
        light and dark, at 1400 and 900 px."""
        self.need(self.fix234, "#234 (v250-hiddenrow)")
        week = self.wk(6)
        self.leave_out("weekly", week)

        def prepare(b):
            b.eval(f"go('weekly',{{code:'FAL', week:{json.dumps(week)}}})")
            b.wait("document.querySelector('#v-reporting section[data-id=overdue] tr[data-ref]')", 20)
            b.eval("document.querySelector('#v-reporting section[data-id=overdue]').scrollIntoView({block:'center'})")
        n = self.sheet(6, "weekly", palettes=["creaite"], widths=(1400, 900), prepare=prepare)
        self.note(6, f"judgement: {n} screenshots on the sheet" if n else "judgement: no sheet in this run")


# ══ #235 ══════════════════════════════════════════════════════════════════════════════════════════════════════════════

LONG = ("Agree the cut-over plan, the rollback steps and the named owners for every environment with the Example Client team, then "
        "confirm the dates in writing so the steering committee can sign them off before the freeze")
MID = "Chase the licence order with the vendor and record the purchase order number in the register"
SHORT = "Book the room"
TITLES = [LONG, SHORT, LONG + " (second pass)", MID, LONG + " (third pass)", SHORT + " twice", MID + " again",
          LONG + " (fourth pass)", SHORT + " once more", LONG + " (last)"]


class Picker235(V251Case):
    """Checks 7 to 9. One vault of their own: ten open Falcon actions, six with titles that wrap to several lines."""
    own_vault = True
    seeded = False
    SECTION = "#v-reporting section[data-id=overdue]"

    def seed_titles(self):
        if not type(self).seeded:
            day = date.fromisoformat((self.now or "2026-10-19")[:10])
            self.seed([{"op": "new", "table": "actions", "values": {
                "project": "FAL", "description": t, "owner": "Sara Khan", "due_date": (day + timedelta(days=20 + i)).isoformat(),
                "raised": (day - timedelta(days=2)).isoformat(), "source": "hand check 2.5.1"}} for i, t in enumerate(TITLES)])
            type(self).seeded = True

    def open_picker(self, w, mode):
        b = self.b
        self.seed_titles()
        measure.width(b, w, 1000)
        b.reload("typeof go==='function' && LIVE")
        measure.theme(b, "creaite", mode)
        b.eval("go('weekly',{code:'FAL'})")
        b.wait("document.querySelector('#v-reporting section[data-id=current_state]')", 20)
        b.eval(f"document.querySelector('{self.SECTION} .rs-pick-open').click()")
        b.wait(f"document.querySelectorAll('{self.SECTION} .rs-pick-row').length>=10", 15)
        b.pump(0.3)

    def check_picker(self, w, mode):
        self.open_picker(w, mode)
        q, S = self.b.eval, self.SECTION
        where = f"{w}px {mode}"
        rows = q(f"""[...document.querySelectorAll('{S} .rs-pick-row')].map(r=>{{const b=r.getBoundingClientRect(), t=r.querySelector('.rs-pick-t');
          return {{ref:r.dataset.ref, top:b.top, bottom:b.bottom, h:r.offsetHeight, text:t.scrollHeight}}}})""")
        self.assertGreaterEqual(len(rows), 10)
        self.assertGreater(max(r["text"] for r in rows), 3 * 12, f"{where}: some title wraps to several lines")
        for a, b in zip(rows, rows[1:]):
            self.assertLessEqual(a["bottom"], b["top"] + 0.5, f"{where}: {a['ref']} overlaps {b['ref']}")
        for r in rows:
            self.assertGreaterEqual(r["h"] + 0.5, r["text"], f"{where}: {r['ref']} is shorter than its text")
        box = q(f"""(()=>{{const l=document.querySelector('{S} .rs-pick-list'); return {{sh:l.scrollHeight, ch:l.clientHeight, oy:getComputedStyle(l).overflowY}}}})()""")
        self.assertGreater(box["sh"], box["ch"], f"{where}: the list scrolls inside its box")
        self.assertIn(box["oy"], ("auto", "scroll"))
        last = q(f"""(()=>{{const l=document.querySelector('{S} .rs-pick-list'); l.scrollTop=l.scrollHeight;
          const rs=l.querySelectorAll('.rs-pick-row'), r=rs[rs.length-1].getBoundingClientRect(), b=l.getBoundingClientRect();
          return {{rb:r.bottom, lb:b.bottom, rt:r.top, lt:b.top}}}})()""")
        self.assertLessEqual(last["rb"], last["lb"] + 1, f"{where}: the last row is fully inside the list at the bottom")
        self.assertGreaterEqual(last["rt"], last["lt"] - 1, f"{where}: the last row starts inside the list")
        return len(rows)

    def test_c07_picker_at_1400_light_and_dark(self):
        """7. Overdue actions › Add from the tracker, ten open actions with long titles, at 1400 px in light and dark → no two rows
        overlap, each row is as tall as its text, the list scrolls inside its box and its last row can be scrolled fully into view."""
        self.need(self.fix235, "#235 (v250-pickerfix)")
        n = [self.check_picker(1400, m) for m in ("light", "dark")]
        self.note(7, f"{n[0]} rows, no overlap, last row reachable, light and dark")

    def test_c08_picker_at_700_light_and_dark(self):
        """8. The same picker at 700 px in light and dark → the same: no overlap, rows as tall as their text, the last row reachable."""
        self.need(self.fix235, "#235 (v250-pickerfix)")
        n = [self.check_picker(700, m) for m in ("light", "dark")]
        self.note(8, f"{n[0]} rows, no overlap, last row reachable, light and dark")

    def test_c09_picker_look(self):
        """9. (judgement) The picker reads cleanly: a wrapped title keeps the owner and date on its first line, the hover band covers
        the whole row, and the list shows it scrolls."""
        self.need(self.fix235, "#235 (v250-pickerfix)")
        self.seed_titles()

        def prepare(b):
            b.eval(f"document.querySelector('{self.SECTION} .rs-pick-open').click()")
            b.wait(f"document.querySelectorAll('{self.SECTION} .rs-pick-row').length>=10", 15)
        n = self.sheet(9, "weekly", palettes=["creaite"], widths=(1400, 700), prepare=prepare)
        self.note(9, f"judgement: {n} screenshots on the sheet" if n else "judgement: no sheet in this run")


# ══ #236 ══════════════════════════════════════════════════════════════════════════════════════════════════════════════

R = "Rashid Al Suwaidi <rashid@northgate.example>"


class Followed236(V251Case):
    """Checks 10 to 14. One vault of their own. The issue's intent questions are still open (where a followed person's conversation
    belongs, whether history counts, how a private one shows), so only what its acceptance says plainly is scripted: every recorded
    conversation reaches Today and none is dropped (10), a dismissed one leaves Today and stays recorded (12), and nothing says who is
    followed (13). Check 11, the move into Needs attention, is skipped until a conversation shows there."""
    own_vault = True
    steps = set()

    def day(self):
        return (self.now or "2026-10-19")[:10]

    def conv(self, kind, cid, title, summary, items, last, **more):
        d = {"kind": kind, "conversation": cid, "title": title, "from": R, "people": [R, "Lena Fischer"], "last": f"{self.day()} {last}",
             "link": "https://teams.microsoft.com/l/chat/" + cid, "sensitivity": more.pop("marker", None) or "normal", "attachments": [],
             "summary": summary, "items": items}
        d.update(more)
        return d

    def record(self, step, conversations, at):
        if step not in self.steps:
            code, out = hcbase.vip_found(self.vault, conversations, f"{self.day()} {at}")
            self.assertEqual(code, 0, out[-500:])
            type(self).steps.add(step)
        self.b.eval("vipPoll().then(()=>{ go('today'); renderToday(); return true; })")
        self.screen("today")
        self.b.pump(0.8)

    OPEN = {"Falcon go-live": "Northgate will take the platform live.", "Licence order": "The licence order is placed.",
            "Falcon steering note": "A note from the steering."}

    def ensure(self):
        """Four conversations of every kind the sweep records for a followed person: a Teams chat, a mail, an invite's note, and a
        chat with nothing in it."""
        self.record("open", [
            self.conv("teams", "19:hc-falcon@thread.v2", "Falcon go-live", self.OPEN["Falcon go-live"],
                      [{"type": "action", "text": "Take the platform live", "owner": "Rashid Al Suwaidi", "due": "2026-10-26"}], "08:40"),
            self.conv("mail", "mail-hc-1", "Licence order", self.OPEN["Licence order"],
                      [{"type": "risk", "text": "Licences may arrive late"}], "08:41", subject="Licence order"),
            self.conv("calendar", "cal-hc-1", "Falcon steering note", self.OPEN["Falcon steering note"],
                      [{"type": "decision", "text": "Keep the January date"}], "08:50"),
            self.conv("teams", "19:hc-hello@thread.v2", "Group chat", "Greetings only.", [], "08:55")], "09:10")

    def vip(self):
        return json.loads((self.vault / "system/staging/vip.json").read_text(encoding="utf-8"))

    def today_text(self):
        return self.b.eval("document.getElementById('v-today').innerText")

    def test_c10_every_recorded_conversation_reaches_today(self):
        """10. The sweep records a followed person's Teams chat, mail and invite note (each with an item) and a chat with nothing in
        it → each of the three is on Today with its title, summary and project, the empty one as one quiet line, none dropped, and the
        count on Today's rail is the three."""
        self.ensure()
        text = self.today_text()
        for title, summary in self.OPEN.items():
            self.assertIn(title, text, f"{title!r} is on Today")
            self.assertIn(summary, text)
        self.assertIn("nothing for you", text, "the empty chat is one quiet line")
        self.assertIn("Falcon Data Platform", text, "the project, by name")
        alerts = [a for a in self.vip()["alerts"] if not a.get("seen")]
        self.assertEqual(len(alerts), 4, "all four are recorded")
        rail = self.b.eval("(()=>{ const e=document.querySelector('.rail button[data-v=\"today\"] .badge'); return e&&e.offsetParent?e.textContent.trim():''; })()")
        self.assertEqual(rail, "3", "the rail counts the three, not the quiet line")
        self.note(10, f"3 conversations + 1 quiet line on Today; rail {rail}")

    def test_c11_they_are_in_needs_attention(self):
        """11. The same three conversations are listed under Today's Needs attention, with the section's count."""
        self.ensure()
        b = self.b
        found = b.eval("""(()=>{ const t=document.getElementById('attnList').innerText; return ['Falcon go-live','Licence order','Falcon steering note'].filter(x=>t.includes(x)); })()""")
        if not found and not FORCE:
            self.skipTest("#236 is not built: the followed person's conversations lead To decide (BL-319, BL-288) and none is in Needs attention; "
                          "waits for Alan's answer to the issue's three questions")
        self.assertEqual(sorted(found), sorted(self.OPEN), "each conversation is a row in Needs attention")
        n = int(b.eval("document.getElementById('nAttn').textContent.trim()") or 0)
        self.assertGreaterEqual(n, 3)
        self.note(11, f"{len(found)} conversations in Needs attention, count {n}")

    def test_c12_a_dismissed_one_leaves_today_and_stays_recorded(self):
        """12. Dismiss one conversation → it leaves Today and the others stay; its record is kept (not deleted) in the recorded alerts."""
        self.ensure()
        b = self.b
        a = next(x for x in self.vip()["alerts"] if x.get("title") == "Licence order")
        r = self.api("/api/alerts/dismiss", {"ids": [a["id"]]})
        self.assertTrue(r.get("ok"), r)
        b.eval("vipPoll().then(()=>{ renderToday(); return true; })")
        wait_for(lambda: "Licence order" not in self.today_text(), 15, "the dismissed conversation to leave Today")
        text = self.today_text()
        self.assertIn("Falcon go-live", text)
        self.assertIn("Falcon steering note", text)
        kept = [x for x in self.vip()["alerts"] if x["id"] == a["id"]]
        self.assertEqual(len(kept), 1, "the record is kept")
        self.assertTrue(kept[0].get("seen"), "it is marked seen (dismissed), not deleted")
        u = self.api("/api/alerts/undo", {"ids": [a["id"]]})
        self.assertTrue(u.get("ok"), u)
        b.eval("vipPoll().then(()=>{ renderToday(); return true; })")
        wait_for(lambda: "Licence order" in self.today_text(), 15, "Undo to put it back")
        self.assertFalse([x for x in self.vip()["alerts"] if x["id"] == a["id"]][0].get("seen"), "Undo clears it")
        self.note(12, "dismissed: gone from Today, still in vip.json (marked seen); Undo put it back")

    def test_c13_nothing_says_who_is_followed(self):
        """13. Nothing on Today (a row, a chip, a tooltip, a label) says VIP or names who is followed."""
        self.ensure()
        html = self.b.eval("document.getElementById('v-today').innerHTML + ' ' + (document.querySelector('.rail')||{innerHTML:''}).innerHTML")
        self.assertNotRegex(html, r"(?i)\bvip\b", "the word VIP is not on Today or the rail")
        self.assertNotRegex(html, r"(?i)\bfollowed\b", "no label says someone is followed")
        self.note(13, "no VIP or followed wording in Today or the rail")

    def test_c14_open_questions(self):
        """14. (judgement) The issue's open questions, seen on Today: a private conversation (title and times only, or nothing), the
        proposals a sweep extracts from a followed person's mail (Review or Needs attention), and whether a seen or dismissed message
        still counts. Alan decides; this takes the screenshots."""
        self.ensure()
        self.record("private", [self.conv("teams", "19:hc-private@thread.v2", "Private matter", "x", [], "09:00", marker="private")], "09:20")
        n = self.sheet(14, "today", palettes=["creaite"], widths=(1400, 900))
        self.note(14, f"judgement: {n} screenshots on the sheet" if n else "judgement: no sheet in this run")


# ══ #237 ══════════════════════════════════════════════════════════════════════════════════════════════════════════════

class Today237(V251Case):
    """Checks 15 to 17. Their own vault with nothing in it (no projects, no items, reminders off), so nothing needs attention."""
    own_vault = True

    @classmethod
    def start_server(cls):
        """An empty vault from the same release zip, as dev/tests/test_today_empty_help.py has: no demo portfolio, reminders off."""
        import handcheck
        import shutil
        s = hcbase.session() or handcheck.Session(os.environ["CREAITE_HC_DIR"])
        if not s.zip and os.environ.get("CREAITE_HC_ZIP"):
            s.zip = Path(os.environ["CREAITE_HC_ZIP"])
        if not s.zip:
            s.build_zip()
        if not s.fake.exists():
            s.write_fake()
        root = s.dir / f"vault-{cls.__name__}"
        shutil.rmtree(root, ignore_errors=True)
        handcheck.run([sys.executable, "-I", handcheck.REPO / "system/scripts/update.py", "new-vault", s.zip, root], handcheck.REPO,
                      what="update.py new-vault")
        cfg_path = root / "system/config/settings.json"
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        cfg.setdefault("vip", {})["check_minutes"] = 100000
        cfg.setdefault("reminders", {})["enabled"] = False
        cfg_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        handcheck.run([root / "system/scripts/run", "build_dashboard.py"], root, {"CREAITE_NOW": s.now}, what="build_dashboard.py")
        cls._hc, cls.vault = s, root
        cls.proc, cls.base = s.start_server(root)
        cls.now = os.environ.get("CREAITE_HC_NOW") or s.now
        cls.v = None

    def today(self):
        self.b.eval("go('today'); renderToday()")
        self.b.wait("document.getElementById('attnList')", 15)
        self.b.pump(0.5)

    def test_c15_empty_needs_attention_is_only_the_sentence(self):
        """15. With nothing to attend to, Today's Needs attention says only "Nothing needs your attention." (no "How Today works"
        box or link under it, and none elsewhere on Today)."""
        self.need(self.fix237, "#237 (v251-todayhelp)")
        self.today()
        o = self.b.eval("""(()=>({rows:document.querySelectorAll('#attnList>li').length, none:document.querySelectorAll('#attnList .none').length,
          text:document.getElementById('attnList').textContent.trim(),
          box:document.querySelectorAll('#attnSec .hhow, #attnSec [data-hhow]').length,
          anywhere:document.querySelectorAll('#v-today .hhow, #v-today [data-hhow]').length}))()""")
        self.assertEqual(o["text"], "Nothing needs your attention.", "this vault has nothing to attend to")
        self.assertEqual([o["rows"], o["none"]], [1, 1])
        self.assertEqual(o["box"], 0, "no How Today works box in Needs attention")
        self.assertEqual(o["anywhere"], 0, "no How Today works box anywhere on Today")
        self.note(15, "the section holds one row, the sentence; no .hhow on Today")

    def test_c16_the_header_help_button_opens_todays_help(self):
        """16. The Today header has a quiet "?" button (named "Help for Today"); pressing it opens the Today help panel, titled
        "Help · Today", with its "How Today works" link."""
        self.need(self.fix237, "#237 (v251-todayhelp)")
        self.today()
        b = self.b
        o = b.eval("""(()=>{ const x=document.querySelector('#v-today .dayband [data-thelp]');
          return {found:!!x, label:x&&x.getAttribute('aria-label'), type:x&&x.type, shown:!!(x&&x.offsetParent)}; })()""")
        self.assertTrue(o["found"], "a help button in the Today header")
        self.assertEqual((o["label"], o["type"], o["shown"]), ("Help for Today", "button", True))
        b.eval("document.querySelector('#v-today .dayband [data-thelp]').click()")
        p = b.eval("""(()=>({on:document.getElementById('helpPanel').classList.contains('on'), title:document.getElementById('hpnT').textContent,
          how:[...document.querySelectorAll('#helpPanel [data-hpn]')].filter(a=>a.textContent==='How Today works').length}))()""")
        self.assertTrue(p["on"], "the help panel opens")
        self.assertEqual(p["title"], "Help · Today")
        self.assertEqual(p["how"], 1, "the panel carries the How Today works link")
        self.note(16, "the header ? opened \"Help · Today\" with the How Today works link")

    def test_c17_header_button_look(self):
        """17. (judgement) The "?" is quiet and sits beside Close the day without crowding it, at 1400 and 900 px, light and dark."""
        self.need(self.fix237, "#237 (v251-todayhelp)")
        n = self.sheet(17, "today", palettes=["creaite"], widths=(1400, 900))
        self.note(17, f"judgement: {n} screenshots on the sheet" if n else "judgement: no sheet in this run")


# ══ #238 ══════════════════════════════════════════════════════════════════════════════════════════════════════════════

class Usage238(V251Case):
    """Checks 18 to 22. The shared vault; nothing changes. Skipped until Activity has a Usage tab. 20 and 21 are not written: there is
    no page or file to read until #238 is built (the brief: dev/sprints/238-usage-monitor-brief.md on origin/pm-intake-briefs)."""

    def tabs(self):
        self.screen("activity")
        self.b.pump(0.5)
        return self.b.eval("[...document.querySelectorAll('#v-activity [role=tab]')].map(x=>x.textContent.trim())")

    def need_usage(self):
        if "Usage" not in self.tabs() and not FORCE:
            self.skipTest("#238 (the Usage tab in Activity) is not in this vault yet; this check runs once it is merged")

    def open_usage(self):
        self.need_usage()
        b = self.b
        b.eval("[...document.querySelectorAll('#v-activity [role=tab]')].find(x=>x.textContent.trim()==='Usage').click()")
        b.pump(0.8)
        return b.eval("""(()=>{ const t=[...document.querySelectorAll('#v-activity [role=tab]')].find(x=>x.textContent.trim()==='Usage');
          const p=t&&document.getElementById(t.getAttribute('aria-controls')); return {selected:!!t&&t.getAttribute('aria-selected')==='true',
          text:p?p.innerText:'', hidden:p?p.hidden:true}; })()""")

    def test_c18_activity_has_a_usage_tab(self):
        """18. Activity has a third tab, Usage, beside Changes and Quality; choosing it shows its page."""
        self.need_usage()
        self.assertEqual(self.tabs()[:2], ["Changes", "Quality"])
        o = self.open_usage()
        self.assertTrue(o["selected"], "the tab is selected")
        self.assertFalse(o["hidden"], "its page is shown")
        self.note(18, f"tabs: {', '.join(self.tabs())}")

    def test_c19_nothing_recorded_says_no_runs_yet(self):
        """19. With no runs recorded, the Usage tab says "No runs yet" instead of an empty chart or zeros."""
        self.need_usage()
        usage = self.vault / "system/staging/run-usage.jsonl"
        if usage.exists() and usage.read_text(encoding="utf-8").strip() and not FORCE:
            self.skipTest("the hand-check vault already has recorded runs")
        o = self.open_usage()
        self.assertIn("No runs yet", o["text"])

    @phase2("#238 is not built: no cards or rows to read yet")
    def test_c20_a_fixture_gives_the_cards_and_rows(self):
        """20. A fixture record of runs gives the summary cards, the by-kind rows and the 30-day change; no text fields are written."""

    @phase2("#238 is not built: no daily context-size record to read yet")
    def test_c21_the_context_size_record(self):
        """21. The live server's daily job appends one line a day per always-loaded file to the context-size record (file, bytes,
        estimated tokens, date; never text), and the page only reads it."""

    def test_c22_usage_look(self):
        """22. (judgement) The Usage tab against its locked mockup: cards, the cost-per-day chart, the tables, at 1400 and 900 px, light
        and dark."""
        self.need_usage()

        def prepare(b):
            b.eval("[...document.querySelectorAll('#v-activity [role=tab]')].find(x=>x.textContent.trim()==='Usage').click()")
        n = self.sheet(22, "activity", palettes=["creaite"], widths=(1400, 900), prepare=prepare)
        self.note(22, f"judgement: {n} screenshots on the sheet" if n else "judgement: no sheet in this run")


if __name__ == "__main__":
    import unittest
    unittest.main()
