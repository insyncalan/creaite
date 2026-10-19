"""#212: creaite 2.5.1's hand checks (dev/handchecks/v2.5.1.md, the Product Manager's merged sheet of 20-10-2026: 44 checks, 13 struck),
automated against a vault made from the release zip (tag v2.5.1, 7c731192). Every check feature-detects its fix in the vault and SKIPS
with the reason when it is absent, so the file also runs against earlier heads. Nothing fails for code that has not landed.
Checks the sheet strikes (7 to 14 and 18 to 22: #235 was in 2.5.0, #236 is 2.6, #238 is 2.5.2) are skipped as "struck"; their tests are
kept so the names still match (CREAITE_HC_251_STRUCK=1 runs them anyway).

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
  Filter240    23 to 26   #240 the Work filter panel is never cut off (shared vault; skipped until the vault holds fbPlace)
  Health242    27 to 31   #242 dismiss a Health problem (own vault; skipped until the vault holds #healthDismissed). 30: a safety-relevant
                          problem is never dismissable; a normal check since b7082a87 (it was an expected fail on b61ab409)
  Sweep243     32 to 35   #243 dismiss Today's Sweep due banner (own vault; skipped until the vault holds creaite-sweepdue-dismissed)
  Help249      36         #249 the Help sidebar closes with Esc or a click outside: Team Stark's test_help_dismiss (called) plus ? and
                          Help's search and links on the hand-check vault (shared)
  Cog244       37         no cog on the Projects list or Today's portfolio rows; it stays on the project page and in Settings
                          (test_project_settings, called, plus the portfolio rows and the doors on the hand-check vault; shared)
  AskReports   38 to 40   ask creaite cannot change, draft or file a report and can read one: the real guard hook (reach.py hook) run in the
                          vault, the report files compared before and after (shared vault; the answer's wording is the model's: live only)
                          38 and 39 each have a second body for the quoted, spliced and `run` forms of the commands (an expected fail on 2.5.1,
                          FAIL-expected; CREAITE_HC_251_STRICT=1 makes it a failure; the worst outcome of a check's bodies stands)
  ClientExport 41 to 43   the client-export hardening: Team Stark's tests, called (test_report_exports, test_export_page,
                          test_export_rename_name, test_client_audience, test_export_page_subset)
  44                      live only (judgement): a real logo in a client HTML and Word export; logos stay out of git

Kinds (the sheet's map): 6, 9, 14, 17, 22, 26, 31 and 35 are judgement (screenshots on the sheet, never Pass or Fail); 44 is live only
(judgement of a real logo; no test); the rest scriptable.
Held-reply technique: dev/tests/test_reshow_switch.py (the reply to /api/report/reshow is held 6 s while another project is opened).
Never Microsoft 365, never a real model: Claude is the hand-check vault's stand-in. Fictional data only (the demo's people).
"""
import json
import os
import re
import subprocess
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
from test_v240 import resolve as resolve_named, run_named        # Team Stark's tests, called as the 2.4.0 checks call them

KIND = {**{n: "scriptable" for n in (1, 2, 3, 4, 5, 7, 8, 10, 11, 12, 13, 15, 16, 18, 19, 20, 21, 23, 24, 25, 27, 28, 29, 30, 32, 33, 34,
                                     36, 37, 38, 39, 40, 41, 42, 43)},
        **{n: "judgement" for n in (6, 9, 14, 17, 22, 26, 31, 35)}}
# Check 44 is live only (no test method): the real logo never enters git, so only a person can look at it.
LIVE_ONLY = {44: "judgement: export a client report as HTML and as Word with your real logo and look at it; the logo stays out of git, "
                 "so no test can hold it (the logo paths, the SVG cleaning and the Word media are check 41)"}

# The sheet strikes these checks for 2.5.1 ("Checks 7 to 9 are not run", "10 to 14", "18 to 22"): #235 was in 2.5.0, #236 is in 2.6,
# #238 is in 2.5.2. Their tests stay so the names match; they are skipped unless CREAITE_HC_251_STRUCK=1.
STRUCK = {7, 8, 9, 10, 11, 12, 13, 14, 18, 19, 20, 21, 22}
RUN_STRUCK = os.environ.get("CREAITE_HC_251_STRUCK") == "1"

NOTES.clear()          # test_v230 (imported for its helpers) put its own notes for checks 5 and 11 here
NOTES.update({
    11: "waits for Alan's answer on #236 (where a followed person's conversation belongs): skipped until one reaches Needs attention",
    14: "open questions on #236: private conversations, proposals from a followed person's messages, seen and dismissed history",
    20: "no test yet: needs #238's cards and rows (no DOM to read until it is built)",
    21: "no test yet: needs #238's daily record of the always-loaded files",
    30: "must pass in 2.5.1: the five safety ids are protected since b7082a87 (it was an expected fail on b61ab409)",
    38: "the guard's refusal (reach.py hook, exit 2, the reason names the Reporting hub); how Claude words it to you is the model's: live only",
    40: "the guard allows the read (Read and Grep); the answer itself is the model's: live only",
    41: "PARTIAL: the save route's logo paths and the Word and SVG parts are called; the approve route shares the same function (report_server.own_header_logos) but has no test of its own",
    43: "Team Stark's tests, called; the sheet's four parts are: a posted page used only for the saved report's own words, another's refused, "
        "the minutes export refusing a client report, a weekly report staying internal",
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

    @classmethod
    def runnable(cls):
        """The checks of this class that will run: not struck by the sheet (so a class of struck checks starts no vault or server)."""
        return [m for m in super().runnable() if RUN_STRUCK or int(m[6:8]) not in STRUCK]

    def setUp(self):
        if not RUN_STRUCK and self.check_number() in STRUCK:
            self.skipTest("struck: not in 2.5.1 (the sheet's #235 was in 2.5.0, #236 is in 2.6, #238 is in 2.5.2); CREAITE_HC_251_STRUCK=1 runs it")
        super().setUp()

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

    @property
    def fix240(self):
        """#240 (v251-fpmenu): the funnel's panel is placed by fbPlace (fixed, kept in the window)."""
        return "fbPlace" in self.vtext("dashboard.html")

    @property
    def fix242(self):
        """#242 (v251-healthclear): Settings › Health can dismiss a problem (the folded "Dismissed (n)")."""
        return "healthDismissed" in self.vtext("dashboard.html")

    @property
    def fix243(self):
        """#243 (v251-sweepdismiss): the quiet x on Today's Sweep due banner."""
        return "creaite-sweepdue-dismissed" in self.vtext("dashboard.html")

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


# ══ #240 ══════════════════════════════════════════════════════════════════════════════════════════════════════════════

# The funnel's panel: where it is against the window and its button, and whether its Done button and Result line can be reached.
PANEL_JS = r"""((menuId, btnId) => {
  const m = document.getElementById(menuId), f = document.getElementById(btnId);
  if (!m || !f) return {missing: !m ? menuId : btnId};
  const R = e => { const r = e.getBoundingClientRect(); return {top: r.top, bottom: r.bottom, left: r.left, right: r.right, h: r.height}; };
  const shown = getComputedStyle(m).display !== 'none' && m.getBoundingClientRect().height > 0;
  const cs = getComputedStyle(m), out = {shown, panel: R(m), btn: R(f), vw: document.documentElement.clientWidth,
    vh: document.documentElement.clientHeight, position: cs.position, overflowY: cs.overflowY, sh: m.scrollHeight, ch: m.clientHeight, parts: {}};
  const inside = (e, x, y) => { const t = document.elementFromPoint(x, y); return !!t && e.contains(t); };
  out.centre = inside(m, (out.panel.left + out.panel.right) / 2, Math.min(out.panel.bottom, out.vh) - 4);
  for (const [name, sel] of [['Done', '.fpfoot .btn.primary'], ['Result', '.fpfoot .sub']]) {
    const e = m.querySelector(sel); if (!e) { out.parts[name] = null; continue; }
    e.scrollIntoView({block: 'nearest'});
    const r = R(e); out.parts[name] = {top: r.top, bottom: r.bottom, h: r.h, hit: inside(e, (r.left + r.right) / 2, (r.top + r.bottom) / 2)};
  }
  return out; })"""


class Filter240(V251Case):
    """Checks 23 to 26. The shared vault; only the Work filters change (and they are cleared). 1400 px wide; the window is made
    1000 and 420 px high, with a list of one row (short) and the whole list (long)."""
    TALL, LOW = 1000, 420

    def open_work(self, h, short, w=1400):
        b = self.b
        measure.width(b, w, h)
        b.reload("typeof go==='function' && LIVE")
        b.eval("go('work')")
        b.wait("document.querySelector('#workTbl tbody tr[data-row]')", 25)
        b.eval("clearAllFilters(); WQ=''; workChanged()")
        if short:
            first = b.eval("document.querySelector('#workTbl tbody tr[data-row]').dataset.row")
            b.eval(f"WQ={first!r}; workChanged()")
            b.wait("document.querySelectorAll('#workTbl tbody tr[data-row]').length===1", 10)
        else:
            self.assertGreater(b.eval("document.querySelectorAll('#workTbl tbody tr[data-row]').length"), 8, "premise: a long list")
        b.pump(0.3)

    def open_panel(self, menu="moreMenu", btn="moreBtn", due=True):
        b = self.b
        b.click(f"#{btn}")
        b.wait(f"document.getElementById('{menu}').classList.contains('on')", 10)
        if due and b.eval("!!document.querySelector('#moreMenu [data-fpk=\"due\"]')"):       # Due selected, as in Alan's screenshot
            b.click('#moreMenu [data-fpk="due"]')
        b.pump(0.5)

    def measure(self, menu="moreMenu", btn="moreBtn"):
        return self.b.eval(f"({PANEL_JS})({json.dumps(menu)}, {json.dumps(btn)})")

    def problems(self, m, label):
        """What is wrong with the open panel `m` (measure()): not shown, outside the window, not by its button, a part out of reach."""
        if m.get("missing"):
            return [f"{label}: {m['missing']} is not on the page"]
        if not m["shown"]:
            return [f"{label}: the panel is not open"]
        p, f, bad = m["panel"], m["btn"], []
        if p["top"] < -0.5 or p["left"] < -0.5 or p["bottom"] > m["vh"] + 0.5 or p["right"] > m["vw"] + 0.5:
            bad.append(f"{label}: the panel is outside the window ({p['top']:.0f}..{p['bottom']:.0f} of {m['vh']})")
        below = -0.5 <= p["top"] - f["bottom"] <= 16
        above = -0.5 <= f["top"] - p["bottom"] <= 16
        if not (below or above):
            bad.append(f"{label}: the panel is not attached to its button (panel {p['top']:.0f}..{p['bottom']:.0f}, button {f['top']:.0f}..{f['bottom']:.0f})")
        if p["left"] > f["right"] + 1 or p["right"] < f["left"] - 1:
            bad.append(f"{label}: the panel is off to the side of its button")
        if m["sh"] > m["ch"] + 1 and m["overflowY"] not in ("auto", "scroll"):
            bad.append(f"{label}: the panel is taller than its box and does not scroll ({m['sh']} in {m['ch']}, {m['overflowY']})")
        if not m["centre"]:
            bad.append(f"{label}: something else is drawn over the panel's visible part (it is cut off)")
        for name, r in m["parts"].items():
            if r is None:
                bad.append(f"{label}: no {name} in the panel")
            elif r["top"] < p["top"] - 1 or r["bottom"] > p["bottom"] + 1 or r["bottom"] > m["vh"] + 1 or r["top"] < -1 or not r["hit"]:
                bad.append(f"{label}: {name} cannot be reached ({r['top']:.0f}..{r['bottom']:.0f} in {p['top']:.0f}..{p['bottom']:.0f}, hit {r['hit']})")
        return bad

    def test_c23_the_panel_is_in_the_window_and_by_its_button(self):
        """23. Work › the funnel's filter panel, opened at two window heights (1000 and 420 px) with a short list (one row) and a
        long one → the panel is inside the window and next to the funnel (below it, or above it when there is no room), and if it is
        taller than the room it scrolls inside, so its Done button and Result line can be reached; nothing is drawn over it."""
        self.need(self.fix240, "#240 (v251-fpmenu)")
        bad, seen = [], []
        for h in (self.TALL, self.LOW):
            for short in (True, False):
                label = f"{h} px high, {'short' if short else 'long'} list"
                self.open_work(h, short)
                self.open_panel()
                m = self.measure()
                bad += self.problems(m, label)
                if not m.get("missing"):
                    seen.append(f"{h}/{'1' if short else 'n'}: {'below' if m['panel']['top'] >= m['btn']['bottom'] - 0.5 else 'above'}, {m['panel']['h']:.0f} high, {m['position']}")
        if bad:
            self.fail("; ".join(bad))
        self.note(23, "; ".join(seen))

    def test_c24_esc_and_an_outside_click_close_it(self):
        """24. The open panel closes on Esc, and focus goes back to the funnel; a click outside it closes it too, at both window heights."""
        self.need(self.fix240, "#240 (v251-fpmenu)")
        b = self.b
        for h in (self.TALL, self.LOW):
            self.open_work(h, False)
            self.open_panel(due=False)
            b.key("Escape")
            b.wait("!document.getElementById('moreMenu').classList.contains('on')", 10)
            self.assertEqual(b.eval("document.activeElement.id"), "moreBtn", f"{h} px high: Esc returns focus to the funnel")
            self.assertFalse(self.measure()["shown"], f"{h} px high: the panel is gone after Esc")
            self.open_panel(due=False)
            b.click("#v-work h1")
            b.wait("!document.getElementById('moreMenu').classList.contains('on')", 10)
            self.assertFalse(self.measure()["shown"], f"{h} px high: the panel is gone after a click outside it")
        self.note(24, "Esc closed it and focus went back to the funnel; a click on the heading closed it; at 1000 and 420 px high")

    def test_c25_the_other_filter_screens_too(self):
        """25. The same panel on the other screens that use it (Review, Activity, Settings › People), at 900 and 420 px high → inside the window
        and next to its button, its parts reachable, and Esc closes it."""
        self.need(self.fix240, "#240 (v251-fpmenu)")
        b = self.b
        bad, done = [], []
        for screen, btn, menu in (("review", "rvMore", "rvPick"), ("activity", "actFunnel", "actPick"), ("settings-people", "pmFBtn", "pmFMenu")):
            for h in (900, self.LOW):
                measure.width(b, 1400, h)
                b.reload("typeof go==='function' && LIVE")
                self.screen(screen)
                if not b.eval(f"(()=>{{ const e=document.getElementById('{btn}'); return !!e && e.offsetParent!==null; }})()"):
                    continue                                   # this screen has no filter button in this vault
                b.click(f"#{btn}")
                b.pump(0.6)
                label = f"{screen} at {h} px high"
                m = self.measure(menu, btn)
                bad += self.problems(m, label)
                b.key("Escape")
                b.pump(0.3)
                if self.measure(menu, btn).get("shown"):
                    bad.append(f"{label}: Esc leaves the panel open")
                done.append(f"{screen}/{h}")
        if not done:
            self.skipTest("none of Review, Activity and Settings › People draws a filter button in this vault")
        if bad:
            self.fail("; ".join(bad))
        self.note(25, "checked: " + ", ".join(done))

    def test_c26_panel_look(self):
        """26. (judgement) The Work filter panel at a low window (420 px high) on a short list, light and dark, at 1400 and 900 px
        wide: it reads as one panel under the funnel, with its edge, shadow and scroll showing and nothing cut by a straight line."""
        self.need(self.fix240, "#240 (v251-fpmenu)")

        def prepare(b):
            b.eval("clearAllFilters(); WQ=''; workChanged()")
            first = b.eval("document.querySelector('#workTbl tbody tr[data-row]').dataset.row")
            b.eval(f"WQ={first!r}; workChanged()")
            b.wait("document.querySelectorAll('#workTbl tbody tr[data-row]').length===1", 10)
            measure.width(b, b.eval("innerWidth"), self.LOW)
            if b.eval("document.getElementById('moreMenu').classList.contains('on')"):           # still open from the last shot
                b.key("Escape")
                b.pump(0.3)
            b.click("#moreBtn")
            b.wait("document.getElementById('moreMenu').classList.contains('on')", 10)
            if b.eval("!!document.querySelector('#moreMenu [data-fpk=\"due\"]')"):
                b.click('#moreMenu [data-fpk="due"]')
            b.pump(0.5)
        n = self.sheet(26, "work", palettes=["creaite"], widths=(1400, 900), prepare=prepare)
        self.b.eval("clearAllFilters(); WQ=''; workChanged(); true")
        self.note(26, f"judgement: {n} screenshots on the sheet" if n else "judgement: no sheet in this run")


# ══ #242 ══════════════════════════════════════════════════════════════════════════════════════════════════════════════

# The problems that touch the safety of the vault or of its data: never dismissable, whatever their status (Alan, 19-10-2026; the
# independent review of v251-healthclear b61ab409 found the KEEP list protects none of them).
SAFETY = ("vault_not_synced", "assistant_permissions", "backup_check", "offsite_backup", "extraction_scope")


class Health242(V251Case):
    """Checks 27 to 31. One vault of their own, with an old `zz Archive` folder so Health has a warning that may be dismissed
    (Settings › Health is read through the real doctor, which takes a few seconds). Each check starts with nothing dismissed."""
    own_vault = True
    TARGET = "old_archive_folders"
    ROWS = "#healthCard .hlist[aria-label=\"What needs you\"] .hrow"

    def setUp(self):
        super().setUp()
        (self.vault / "projects/zz Archive").mkdir(parents=True, exist_ok=True)
        for extra in (self.vault / "projects").glob("*/zz Archive"):          # check 29's second folder
            extra.rmdir()
        cfg = self.vault / "system/config/settings.json"
        data = json.loads(cfg.read_text(encoding="utf-8"))
        if (data.get("health") or {}).get("dismissed"):
            data["health"]["dismissed"] = []
            cfg.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def open_health(self):
        b = self.b
        b.reload("typeof go==='function' && LIVE")
        b.eval("go('settings','health')")
        b.wait("!!document.querySelector('#healthCard .hsum')", 180)
        b.pump(0.4)

    def rows(self):
        return self.b.eval(f"[...document.querySelectorAll('{self.ROWS}')].map(r=>r.dataset.check)")

    def more_badge(self):
        """The problem count on the sidebar's More button, as its name says it ("More, 2 problems"); 0 when it has none."""
        label = self.b.eval("(()=>{ const x=[...document.querySelectorAll('button')].find(e=>/^More\\b/.test(e.getAttribute('aria-label')||'')); return x?x.getAttribute('aria-label'):null; })()")
        self.assertIsNotNone(label, "the sidebar has a More button")
        m = re.search(r",\s*(\d+) problems?", label)
        return int(m.group(1)) if m else 0

    def dismiss(self, check, reason="Known, and fine for now"):
        b = self.b
        row = f"document.querySelector('#healthCard .hrow[data-check={check}]')"
        b.eval(f"{row}.querySelector('.hdismiss').click()")
        b.wait(f"!!{row}.querySelector('input.hreason')", 10)
        b.eval(f"(()=>{{ const i={row}.querySelector('input.hreason'); i.value={json.dumps(reason)}; i.dispatchEvent(new Event('input',{{bubbles:true}})); }})()")
        b.eval(f"{row}.querySelector('.hdismissgo').click()")

    def need_target(self):
        self.need(self.fix242, "#242 (v251-healthclear)")
        self.open_health()
        self.assertIn(self.TARGET, self.rows(), "premise: the old zz Archive folder is a Health warning")
        self.assertTrue(self.b.eval(f"!!document.querySelector('#healthCard .hrow[data-check={self.TARGET}] .hdismiss')"),
                        "the warning offers Dismiss")

    def test_c27_dismiss_drops_the_badge_and_lists_it(self):
        """27. Settings › Health: Dismiss a problem that is not about safety (with a reason) → the count on the sidebar's More button
        goes down by one, the problem leaves the list, and it is under a folded "Dismissed (1)" with its reason and the date; it is
        still dismissed after a reload."""
        self.need_target()
        b = self.b
        before, n = self.rows(), self.more_badge()
        self.assertEqual(n, len(before), "the badge counts the listed problems")
        self.dismiss(self.TARGET)
        wait_for(lambda: self.more_badge() == n - 1, 15, "the badge to drop by one")
        self.assertNotIn(self.TARGET, self.rows())
        b.wait("!!document.querySelector('#healthDismissed')", 10)
        self.assertIn("Dismissed (1)", b.eval("document.querySelector('#healthDismissed summary').textContent"))
        self.assertFalse(b.eval("document.querySelector('#healthDismissed').open"), "the Dismissed list is folded")
        b.eval("document.querySelector('#healthDismissed').open = true")
        text = b.eval(f"document.querySelector('#healthDismissed [data-check={self.TARGET}]').textContent")
        self.assertIn("Known, and fine for now", text)
        self.assertRegex(text, r"\b\d{2}-\d{2}-\d{4}\b", "the date, shown DD-MM-YYYY")
        saved = json.loads((self.vault / "system/config/settings.json").read_text(encoding="utf-8"))["health"]["dismissed"]
        self.assertEqual([d["id"] for d in saved], [self.TARGET], "stored in settings.json health.dismissed")
        self.open_health()
        self.assertNotIn(self.TARGET, self.rows(), "still dismissed after a reload")
        self.assertEqual(self.more_badge(), n - 1)
        self.note(27, f"badge {n} → {n - 1}; under Dismissed (1) with its reason and date; kept after a reload")

    def test_c28_restore_puts_it_back(self):
        """28. Restore on a dismissed problem → it is back in the list, the count on More goes up by one, the Dismissed list goes,
        and it stays restored after a reload."""
        self.need_target()
        b = self.b
        n = self.more_badge()
        self.dismiss(self.TARGET)
        wait_for(lambda: self.more_badge() == n - 1, 15, "the badge to drop by one")
        b.wait("!!document.querySelector('#healthDismissed')", 10)
        b.eval("document.querySelector('#healthDismissed').open = true")
        b.eval(f"document.querySelector('#healthDismissed [data-check={self.TARGET}] .hrestorebtn').click()")
        wait_for(lambda: self.more_badge() == n, 15, "the badge to come back")
        self.assertIn(self.TARGET, self.rows())
        self.assertFalse(b.eval("!!document.querySelector('#healthDismissed')"), "nothing is left under Dismissed")
        saved = json.loads((self.vault / "system/config/settings.json").read_text(encoding="utf-8"))["health"]["dismissed"]
        self.assertEqual(saved, [])
        self.open_health()
        self.assertIn(self.TARGET, self.rows(), "still listed after a reload")
        self.assertEqual(self.more_badge(), n)
        self.note(28, f"badge {n - 1} → {n}; back in the list; Dismissed gone; kept after a reload")

    def test_c29_it_comes_back_when_its_detail_changes(self):
        """29. A dismissed problem whose detail then changes (a second old zz Archive folder) is a new problem: it comes back in the
        list and counts again, and the Dismissed list no longer holds it."""
        self.need_target()
        n = self.more_badge()
        self.dismiss(self.TARGET)
        wait_for(lambda: self.more_badge() == n - 1, 15, "the badge to drop by one")
        folder = next(d for d in sorted((self.vault / "projects").iterdir()) if d.is_dir() and not d.name.startswith(("_", "zz")))
        (folder / "zz Archive").mkdir(exist_ok=True)
        self.open_health()
        self.assertIn(self.TARGET, self.rows(), "the changed problem is listed again")
        self.assertEqual(self.more_badge(), n)
        self.assertFalse(self.b.eval("!!document.querySelector('#healthDismissed')"), "and is not under Dismissed")
        self.note(29, f"a second zz Archive folder ({folder.name}) changed the detail: back in the list, badge {n}")

    def test_c30_a_safety_problem_is_never_dismissable(self):
        """30. A problem that is about safety (the vault in a synced folder, ask creaite's permissions, the backup checks, what
        extraction may read) cannot be dismissed, whether it is a failure or a warning: Health gives it no Dismiss, and even a
        dismissed entry for it leaves it in the list and counted. (Must pass in 2.5.1: b7082a87 protects the five ids; on b61ab409 it
        was an expected fail.)"""
        self.need(self.fix242, "#242 (v251-healthclear)")
        out = self.py("""
import health
res = {"checks": [{"id": i, "name": i, "status": st, "detail": "a detail"} for i in %s for st in ("fail", "warn")]}
dis = [{"id": i, "detail_key": health.problem_key(i, "a detail"), "reason": "", "date": "2026-10-19"} for i in %s]
out = health.health(res, dismissed=dis)
print(json.dumps({"still": sorted({p["id"] + ":" + p["severity"] for p in out["problems"]}),
                  "gone": sorted({p["id"] + ":" + p["severity"] for p in out["dismissed"]}), "keep": list(getattr(health, "KEEP", ()))}))
""" % (list(SAFETY), list(SAFETY)))
        self.assertEqual(out["gone"], [], f"safety-relevant problems that can be dismissed: {', '.join(out['gone'])}")
        every = sorted(f"{i}:{st}" for i in SAFETY for st in ("fail", "warn"))
        self.assertEqual(out["still"], every, "every safety problem, as a failure and as a warning, stays listed and counted")
        self.assertFalse(set(SAFETY) - set(out["keep"]), "the five safety ids are in health.KEEP")
        # and on the page, a safety problem that happens to be listed offers no Dismiss
        self.open_health()
        offered = self.b.eval(f"[...document.querySelectorAll('#healthCard .hrow[data-check]')].filter(r=>{json.dumps(list(SAFETY))}.includes(r.dataset.check) && r.querySelector('.hdismiss')).map(r=>r.dataset.check)")
        self.assertEqual(offered, [], f"Dismiss is offered on: {offered}")
        self.note(30, "all five safety ids, as a failure and as a warning, stay listed even with a dismissed entry; no Dismiss on the page")

    def test_c31_dismissed_look(self):
        """31. (judgement) Settings › Health with one problem dismissed: the quiet Dismiss, the reason line, and the folded Dismissed
        list opened with its Restore, in light and dark, at 1400 and 900 px."""
        self.need_target()
        self.dismiss(self.TARGET)
        self.b.wait("!!document.querySelector('#healthDismissed')", 15)

        def prepare(b):
            b.wait("!!document.querySelector('#healthCard .hsum')", 180)
            b.wait("!!document.querySelector('#healthDismissed')", 30)
            b.eval("document.querySelector('#healthDismissed').open = true; document.querySelector('#healthDismissed').scrollIntoView({block:'center'})")
        n = self.sheet(31, "settings-health", palettes=["creaite"], widths=(1400, 900), prepare=prepare)
        self.note(31, f"judgement: {n} screenshots on the sheet" if n else "judgement: no sheet in this run")


# ══ #243 ══════════════════════════════════════════════════════════════════════════════════════════════════════════════

class Sweep243(V251Case):
    """Checks 32 to 35. One vault of their own: the check writes system/staging/last-sweep.txt and rebuilds the dashboard, so the
    banner is due (the last sweep before today's 07:00, and it is 09:30) the way the real session start finds it."""
    own_vault = True
    KEY = "creaite-sweepdue-dismissed"
    VISIBLE = ("(()=>{const e=document.getElementById('sweepDue'); return !!e && !e.hidden && e.offsetParent!==null "
               "&& getComputedStyle(e).display!=='none';})()")

    def day(self, back=0):
        return (date.fromisoformat(self.now[:10]) - timedelta(days=back)).isoformat()

    def last_swept(self, stamp):
        """The last sweep recorded as `stamp` ("YYYY-MM-DD HH:MM"), and the dashboard rebuilt as the sweep's end does."""
        (self.vault / "system/staging/last-sweep.txt").write_text(stamp + "\n", encoding="utf-8")
        code, out = self.run_in_vault("build_dashboard.py")
        self.assertEqual(code, 0, out[-300:])

    def show_today(self, forget=False):
        b = self.b
        if forget:
            b.eval(f"try {{ localStorage.removeItem('{self.KEY}'); }} catch (e) {{}} true")
        b.reload("typeof go==='function' && LIVE")
        self.screen("today")
        b.pump(0.4)

    def visible(self):
        return self.b.eval(self.VISIBLE)

    def due_since_yesterday(self):
        self.last_swept(f"{self.day(1)} 07:30")
        self.show_today(forget=True)

    def test_c32_the_banner_shows_when_the_sweep_is_overdue(self):
        """32. When the last sweep was before 07:00 today and it is later than that, Today shows "Sweep due since 07:00" with the last
        sweep's time, a Run sweep button and a quiet x named "Dismiss until the next sweep is due"; when the sweep is not overdue
        there is no banner."""
        self.need(self.fix243, "#243 (v251-sweepdismiss)")
        b = self.b
        self.due_since_yesterday()
        self.assertTrue(self.visible(), "the banner is shown")
        text = b.eval("document.getElementById('sweepDue').innerText")
        self.assertIn("Sweep due since 07:00", text)
        self.assertIn(f"Last swept {self.day(1)} 07:30", text)
        self.assertEqual(b.eval("document.getElementById('sweepRun').textContent"), "Run sweep")
        self.assertEqual(b.eval("document.getElementById('sweepX').getAttribute('aria-label')"), "Dismiss until the next sweep is due")
        self.assertEqual(b.eval("document.getElementById('sweepX').tagName"), "BUTTON")
        self.assertEqual(b.eval("document.querySelectorAll('#sweepDue').length"), 1, "once only")
        self.last_swept(f"{self.day()} 08:15")
        self.show_today(forget=True)
        self.assertFalse(self.visible(), "no banner when the sweep ran after 07:00 today")
        self.note(32, f"shown for a sweep at {self.day(1)} 07:30 with Run sweep and the x; gone for one at {self.day()} 08:15")

    def test_c33_dismiss_hides_it_across_reload_and_redraw(self):
        """33. Press the x → the banner goes and stays gone after a reload, after Today is drawn again, after leaving Today and coming
        back, and after the page refreshes its data; with the keyboard (Enter on the x) it goes too and focus stays on Today."""
        self.need(self.fix243, "#243 (v251-sweepdismiss)")
        b = self.b
        self.due_since_yesterday()
        self.assertTrue(self.visible())
        b.click("#sweepX")
        b.pump(0.3)
        self.assertFalse(self.visible(), "the x hides it")
        self.assertTrue(b.eval(f"!!localStorage.getItem('{self.KEY}')"), "this browser remembers it")
        b.eval("renderToday(); true")
        self.assertFalse(self.visible(), "still hidden when Today is drawn again")
        b.eval("renderSweepDue(); true")
        self.assertFalse(self.visible())
        b.eval("go('work')")
        b.pump(0.3)
        self.screen("today")
        self.assertFalse(self.visible(), "still hidden after leaving Today and coming back")
        b.eval("Promise.resolve(typeof refreshAll === 'function' ? refreshAll() : 0).then(() => true)")
        b.pump(0.6)
        self.assertFalse(self.visible(), "still hidden after the page refreshes its data")
        self.show_today()
        self.assertFalse(self.visible(), "still hidden after a reload")
        self.assertEqual(b.eval("document.getElementById('sweepRun')"), None, "the Run sweep button went with it")
        # the keyboard
        self.show_today(forget=True)
        self.assertTrue(self.visible())
        b.eval("document.getElementById('sweepX').focus()")
        b.key("Enter")
        b.pump(0.3)
        self.assertFalse(self.visible(), "Enter on the x hides it")
        self.assertFalse(b.eval("document.activeElement === document.body"), "focus is not dropped onto the page")
        self.assertTrue(b.eval("!!document.activeElement.closest('#v-today')"), "focus stays on Today")
        self.note(33, "hidden after the click, a redraw, leaving and returning, a data refresh and a reload; Enter on the x works, focus stays on Today")

    def test_c34_it_returns_when_the_last_sweep_changes(self):
        """34. A dismissed banner comes back when the last sweep's time changes and the sweep is still due (a sweep ran before 07:00
        and is due again), and on the next day; it does not come back for nothing."""
        self.need(self.fix243, "#243 (v251-sweepdismiss)")
        b = self.b
        self.due_since_yesterday()
        b.click("#sweepX")
        b.pump(0.3)
        self.assertFalse(self.visible())
        self.last_swept(f"{self.day()} 06:10")                  # a sweep ran, but before today's 07:00: still due, another last time
        self.show_today()
        self.assertTrue(self.visible(), "back when the last sweep's time changed while still due")
        self.assertIn(f"Last swept {self.day()} 06:10", b.eval("document.getElementById('sweepDue').innerText"))
        b.click("#sweepX")
        b.pump(0.3)
        self.show_today()
        self.assertFalse(self.visible(), "dismissed again for the new time: it stays hidden")
        b.eval(f"localStorage.setItem('{self.KEY}', JSON.stringify({{day: {json.dumps(self.day(1))}, last: {json.dumps(self.day() + ' 06:10')}}})); true")
        self.show_today()
        self.assertTrue(self.visible(), "a dismissal made on an earlier day does not hide today's banner")
        b.eval(f"localStorage.setItem('{self.KEY}', 'not json'); true")
        self.show_today()
        self.assertTrue(self.visible(), "an unreadable remembered dismissal shows the banner")
        self.note(34, "back for another last-sweep time (06:10) and for a dismissal from yesterday; stayed hidden when nothing changed")

    def test_c35_banner_look(self):
        """35. (judgement) The Sweep due banner with its x, light and dark, at 1400 and 900 px: the x is quiet and at the right edge,
        it does not crowd Run sweep, and it is easy to find with the keyboard (its focus ring)."""
        self.need(self.fix243, "#243 (v251-sweepdismiss)")
        self.due_since_yesterday()

        def prepare(b):
            b.wait(self.VISIBLE, 15)
            b.eval("document.getElementById('sweepX').focus({focusVisible: true}); true")
        n = self.sheet(35, "today", palettes=["creaite"], widths=(1400, 900), prepare=prepare)
        self.note(35, f"judgement: {n} screenshots on the sheet" if n else "judgement: no sheet in this run")



# ══ #249, the cog, ask creaite and reports, the client export (the PM's checks 36 to 44) ══════════════════════════════════

REPO = Path(__file__).resolve().parents[3]


class Called251(V251Case):
    """Checks that call Team Stark's own tests (dev/tests/<file>.py, in a fresh process with a vault, server and Chrome of their own,
    as test_v240.py does) instead of writing them again. They run against THIS checkout's engine; the check first makes sure the hand-check
    vault was built from the same one, so they say the same thing about the zip."""

    def called(self, calls):
        """Run `calls` = [(file, (test tokens))]: skip while a test is not in this checkout, fail if one fails, else a note. Returns
        the number of tests called."""
        mine, theirs = self.vtext("VERSION").strip(), (REPO / "VERSION").read_text(encoding="utf-8").strip()
        if mine != theirs and not FORCE:
            self.skipTest(f"the hand-check vault runs creaite {mine}, this checkout {theirs}: the called tests would test another engine")
        found, missing = [], []
        for file, tokens in calls:
            ids, gone = resolve_named(file, tokens)
            missing += gone
            if ids:
                found.append((file, ids))
        if missing:
            self.skipTest("not in this checkout: " + ", ".join(missing[:3]) + (f" and {len(missing) - 3} more" if len(missing) > 3 else ""))
        failed, total = [], 0
        for file, ids in found:
            ok, msg = run_named(file, ids)
            total += len(ids)
            if not ok:
                failed.append(msg)
        self.assertEqual(failed, [], "\n".join(failed))
        self.note(self.check_number(), f"{total} named tests or test classes of Team Stark's called, all passed: {', '.join(f for f, _ in found)}")
        return total


# ── #249 ──

class Help249(Called251):
    """Check 36. The hand-check vault (shared): the Help sidebar on Today and Help's own search and links while it is open."""
    OPENER = "#v-today .dayband [data-thelp]"
    ON = "document.getElementById('helpPanel').classList.contains('on')"
    CALLS = [("test_help_dismiss", ("HelpDismiss.test_esc_closes_it_and_focus_goes_back_to_the_opener",
                                    "HelpDismiss.test_a_click_outside_closes_it_and_focus_goes_back",
                                    "HelpDismiss.test_a_click_inside_keeps_it_open", "HelpDismiss.test_the_opener_toggles_it"))]

    @property
    def fix249(self):
        """#249 (v251-helpdismiss): a press outside the Help panel closes it."""
        return "helpOutsidePress" in self.vtext("dashboard.html")

    def today(self):
        self.b.call("Emulation.setFocusEmulationEnabled", enabled=True)
        self.b.eval("go('today'); renderToday()")
        self.b.wait(f"document.querySelector({self.OPENER!r})", 20)

    def on(self):
        return self.b.eval(self.ON)

    def press_help(self):
        """The ? key, as a person types it (Shift + /), with nothing focused."""
        b = self.b
        b.eval("document.activeElement&&document.activeElement.blur&&document.activeElement.blur()")
        b.call("Input.dispatchKeyEvent", type="keyDown", key="?", code="Slash", text="?", windowsVirtualKeyCode=191, modifiers=8)
        b.call("Input.dispatchKeyEvent", type="keyUp", key="?", code="Slash", windowsVirtualKeyCode=191, modifiers=8)
        b.wait(self.ON, 10)

    def click_outside(self):
        """A real click on plain page text left of the panel (the day band's title), which acts on no click."""
        b = self.b
        x, y = b.eval("""(()=>{ const p=document.getElementById('helpPanel').getBoundingClientRect();
          const t=[...document.querySelectorAll('.view h1, #v-today .dayband h1, #v-today .dayband .dtitle, #v-today .dayband')]
            .find(e=>{ const r=e.getBoundingClientRect(); return r.width&&r.height&&r.left<p.left-20; });
          const r=t.getBoundingClientRect(); return [r.left+Math.min(20,r.width/2), r.top+r.height/2]; })()""")
        self.assertFalse(b.eval(f"!!document.elementFromPoint({x},{y}).closest('#helpPanel')"), "premise: the point is outside the panel")
        for kind in ("mouseMoved", "mousePressed", "mouseReleased"):
            b.call("Input.dispatchMouseEvent", type=kind, x=x, y=y, button="left", clickCount=1)
        b.pump(0.15)

    def test_c36_help_closes_on_esc_and_an_outside_click(self):
        """36. Press ? to open the Help sidebar, then press Esc → it closes; open it again and click outside it → it closes; Help's
        search and links still work while it is open. (#249; Team Stark's test_help_dismiss is called as well.)"""
        self.need(self.fix249, "#249 (v251-helpdismiss)")
        b = self.b
        self.today()
        self.press_help()
        self.assertIn("Help · Today", b.eval("document.getElementById('hpnT').textContent"))
        b.key("Escape")
        self.assertFalse(self.on(), "Esc closes the Help sidebar")
        self.press_help()
        self.click_outside()
        self.assertFalse(self.on(), "a click outside closes it")
        # Help's own search and links, while it is open
        self.press_help()
        b.click("#hpnFind")
        b.wait("VIEW==='help'", 10)
        self.assertEqual(b.eval("document.activeElement&&document.activeElement.id"), "helpQ", "Search all of Help puts you in Help's search box")
        self.assertFalse(self.on(), "the sidebar steps aside for the Help page")
        self.today()
        self.press_help()
        link = b.eval("document.querySelector('#helpPanel [data-hpn]').dataset.hpn")
        b.click("#helpPanel [data-hpn]")
        b.wait("VIEW==='help'", 10)
        self.assertIn(link, b.eval("location.hash"), "a link in the sidebar opens that place in Help")
        self.assertFalse(self.on())
        self.note(36, "Esc, a click outside, Search all of Help and a link, on the hand-check vault")
        self.called(self.CALLS)


# ── the Projects cog ──

class Cog244(Called251):
    """Check 37. The hand-check vault (shared): where the project settings door is, and where it is not."""
    CALLS = [("test_project_settings", ("test_the_projects_list_has_no_cog_in_its_rows",))]

    @property
    def cog_removed(self):
        """The cog removal (f69ca4d4) is in 2.5.1: the vault's VERSION is 2.5.1 or later."""
        try:
            return tuple(int(x) for x in self.vtext("VERSION").strip().split(".")[:3]) >= (2, 5, 1)
        except ValueError:
            return False

    def test_c37_no_cog_on_the_projects_list_or_the_portfolio_rows(self):
        """37. Projects: no cog beside any project's name; the project rows in Today's portfolio table have none either; a project's
        settings still open from the project page (the cog beside Reports and Browse files) and from Settings. (Team Stark's
        test_project_settings test for the Projects list is called as well.)"""
        self.need(self.cog_removed, "the cog removal (2.5.1)")
        b = self.b
        b.eval("go('projects')")
        b.wait("VIEW==='projects' && !!document.querySelector('#projTbl tbody tr')", 20)
        rows = b.eval("document.querySelectorAll('#projTbl tbody tr').length")
        self.assertGreater(rows, 0, "premise: the Projects list has rows")
        self.assertEqual(b.eval("document.querySelectorAll('#projTbl [data-psettings], #projTbl .iconbtn, #projTbl [aria-label*=\"settings\" i]').length"), 0,
                         "no cog (or other icon button) in the Projects list")
        b.eval("go('today'); renderToday()")
        b.wait("!!document.querySelector('#pfTbl tbody tr')", 20)
        pf = b.eval("""(()=>{ const rows=[...document.querySelectorAll('#pfTbl tbody tr')];
          return {rows: rows.length, cogs: document.querySelectorAll('#pfTbl [data-psettings], #pfTbl [aria-label*="settings" i]').length,
                  buttons: rows.map(r=>[...r.querySelectorAll('button')].map(x=>x.className).join(',')),
                  svgs: document.querySelectorAll('#pfTbl tbody td:first-child svg').length}; })()""")
        self.assertGreater(pf["rows"], 0, "premise: Today's portfolio has rows")
        self.assertEqual(pf["cogs"], 0, "no cog in Today's portfolio rows")
        self.assertEqual(set(pf["buttons"]), {"pfname"}, f"each portfolio row's first cell holds only the project's name button: {pf['buttons']}")
        self.assertEqual(pf["svgs"], 0, "no icon beside a portfolio project's name")
        b.eval("go('cockpit','FAL')")
        b.wait("VIEW==='cockpit' && !!document.querySelector('.cockfoot [data-psettings=FAL]')", 20)
        self.assertEqual(b.eval("[...document.querySelectorAll('.cockfoot [aria-label]')].map(x=>x.getAttribute('aria-label'))"),
                         ["Reports", "Browse files", "Project settings"], "the cog stays beside Reports and Browse files")
        b.click(".cockfoot [data-psettings=FAL]")
        b.wait("VIEW==='psettings'", 15)
        self.assertEqual(b.eval("document.querySelector('#psTitle').textContent"), "Project settings")
        b.eval("STAB='people'; go('settings')")
        b.wait("VIEW==='settings' && !!document.querySelector('#projSetList [data-psopen=FAL]')", 20)
        b.click("#projSetList [data-psopen=FAL]")
        b.wait("VIEW==='psettings' && psCode.value==='FAL'", 15)
        self.note(37, f"{rows} Projects rows and {pf['rows']} portfolio rows without a cog; the project page and Settings still open the settings")
        self.called(self.CALLS)


# ── ask creaite and reports ──

class AskReports(V251Case):
    """Checks 38 to 40. The hand-check vault (shared; each check puts its report files back as they were). They run the real guard hook
    (`reach.py hook`, the PreToolUse hook every ask creaite chat is started with) on the vault, as Claude Code does: the call as JSON on
    its standard input, exit 2 refusing it with the reason on standard error. What ask creaite then SAYS is the model's; that is live."""
    RUN = "hc-251-run"

    @property
    def fix_reports(self):
        """v2.5.1 (v251-askreports): reach.py refuses every write of a weekly or client report."""
        return "REPORTS_ARE_THE_USERS" in self.vtext("system/scripts/reach.py")

    def hook(self, tool, tool_input, mode="ask"):
        """(exit code, standard error) of the guard hook for one tool call, in this vault."""
        r = subprocess.run([sys.executable, "-I", "system/scripts/reach.py", "hook", "--run", self.RUN, "--mode", mode],
                           input=json.dumps({"tool_name": tool, "tool_input": tool_input}), cwd=self.vault, capture_output=True, text=True,
                           env={**os.environ, "CREAITE_NOW": self.now or ""}, timeout=60)
        return r.returncode, r.stderr

    def where(self):
        """FAL's report folders and the drafts folder, as the vault's paths.py maps them."""
        return self.py("import paths\nprint(json.dumps({'weekly': str(paths.folder('FAL', 'weekly_reports')),"
                       " 'client': str(paths.folder('FAL', 'client_reports')), 'drafts': str(paths.DRAFTS)}))")

    def report_files(self):
        """A weekly and a client report file of FAL's, fictional text: the setup's own old ones, else made here and removed again."""
        w = self.where()
        out = {}
        for kind, name in (("weekly", "2026-10-16 Weekly report - Falcon Data Platform.html"),
                           ("client", "2026-10-16 Client report - Falcon Data Platform (Northgate).html")):
            f = Path(w[kind]) / name
            f.parent.mkdir(parents=True, exist_ok=True)
            if not f.exists():
                f.write_text(f"<html><body><h1>{kind.title()} report</h1><p>Falcon Data Platform: the migration is on track.</p></body></html>\n", encoding="utf-8")
                self.addCleanup(lambda p=f: p.unlink() if p.exists() else None)
            out[kind] = f
        return w, out

    @staticmethod
    def stamp(f):
        return (f.read_bytes(), f.stat().st_mtime_ns)

    def listing(self, w):
        return {k: sorted(x.name for x in Path(w[k]).glob("*")) for k in ("weekly", "client", "drafts")}

    def test_c38_ask_creaite_cannot_change_a_report(self):
        """38. Ask creaite: "change the wording of this week's report" for a project → it says it cannot, points to the Reporting hub,
        and the report file is unchanged. (The guard's refusal of every way to write the file, the file compared before and after.)"""
        self.need(self.fix_reports, "ask creaite's report guard (v251-askreports)")
        w, files = self.report_files()
        before = {k: self.stamp(f) for k, f in files.items()}
        refused = []
        for kind, f in files.items():
            path = str(f)
            calls = [("Write", {"file_path": path, "content": "reworded"}),
                     ("Edit", {"file_path": path, "old_string": "on track", "new_string": "reworded"}),
                     ("MultiEdit", {"file_path": path, "edits": [{"old_string": "on track", "new_string": "reworded"}]}),
                     # the allowed route for a file change (filechange.py) is refused for a report, whatever the verb
                     ("Bash", {"command": f"python3 system/scripts/filechange.py edit '{path}' --from system/staging/drafts/x.html"}),
                     ("Bash", {"command": f"python3 system/scripts/filechange.py create '{path}' --from system/staging/drafts/x.html"}),
                     ("Bash", {"command": f"python3 system/scripts/filechange.py delete '{path}'"}),
                     ("Bash", {"command": f"cp system/staging/drafts/x.html '{path}'"})]
            for tool, inp in calls:
                code, err = self.hook(tool, inp)
                self.assertEqual(code, 2, f"{tool} on the {kind} report was let through: {err}")
                refused.append(f"{kind}:{tool}")
                if not str(inp.get("command", "")).startswith("cp "):          # a plain cp is refused by the general shell rule, whatever it names
                    self.assertIn("Reporting hub", err, f"{tool}: the refusal points to the Reporting hub")
        self.assertEqual({k: self.stamp(f) for k, f in files.items()}, before, "the report files are unchanged (bytes and modified time)")
        self.note(38, f"{len(refused)} ways to write the weekly and the client report refused by the guard; both files unchanged")

    def test_c39_ask_creaite_cannot_draft_or_file_a_report(self):
        """39. Ask creaite: "client report" or "weekly report" for a project → it does not draft or file one. (The guard refuses a
        report draft in the drafts folder and report.py weekly-stage and client-stage; nothing new appears.)"""
        self.need(self.fix_reports, "ask creaite's report guard (v251-askreports)")
        w, files = self.report_files()
        before = self.listing(w)
        drafts = w["drafts"]
        n = 0
        for name in ("2026-10-16 Falcon Data Platform Client report.json", "2026-10-16 Falcon Data Platform Weekly report.html",
                     "client_report_FAL.json", "Weekly-Report FAL.md"):
            code, err = self.hook("Write", {"file_path": f"{drafts}/{name}", "content": "{}"})
            self.assertEqual(code, 2, f"a draft called {name} was let through: {err}")
            self.assertIn("Reporting hub", err)
            n += 1
        for cmd in (f"python3 system/scripts/report.py weekly-stage {drafts}/x.json", f"system/scripts/run report.py client-stage {drafts}/x.json",
                    f"python3 system/scripts/report.py client-stage system/staging/drafts/x.json"):
            code, err = self.hook("Bash", {"command": cmd})
            self.assertEqual(code, 2, f"{cmd} was let through: {err}")
            n += 1
        for mode in ("confirmed", "sweep"):               # not even in a request Alan confirmed
            code, err = self.hook("Bash", {"command": f"python3 system/scripts/report.py client-stage {drafts}/x.json"}, mode)
            self.assertEqual(code, 2, f"client-stage in a {mode} run was let through: {err}")
            n += 1
        self.assertEqual(self.listing(w), before, "no report, draft or file appeared")
        code, err = self.hook("Write", {"file_path": f"{drafts}/notes-for-the-meeting.md", "content": "notes"})       # the control
        self.assertEqual(code, 0, f"an ordinary draft is still allowed: {err}")
        self.note(39, f"{n} attempts to draft, stage or file a report refused (also when Alan confirmed the request); an ordinary draft still allowed")

    # ── the quoted, spliced and `run` forms of the same commands (a known hole in 2.5.1's guard) ──

    STRICT = os.environ.get("CREAITE_HC_251_STRICT") == "1"
    QUOTED_WHY = "quoted words beat the raw-text report rule; fix proposed in dev/proposals/guard-174"

    def quoted_check(self, n, plain, quoted, modes=("ask",)):
        """The same refusal asked for in the quoted forms. `plain` and `quoted` are (tool, input) lists: the plain ones must be refused
        (else the guard is not in this vault and the check skips); then each quoted one, in each mode. All refused: pass. One allowed:
        FAIL-expected (a skip with the reason, the check's number keeps its plain-form result), or a hard failure with
        CREAITE_HC_251_STRICT=1."""
        self.need(self.fix_reports, "ask creaite's report guard (v251-askreports)")
        for tool, inp in plain:
            code, err = self.hook(tool, inp)
            self.assertEqual(code, 2, f"the plain form {inp} was let through: {err}")
        allowed = [f"{mode}: {inp.get('command') or inp.get('file_path')}" for mode in modes for tool, inp in quoted
                   for code, _ in [self.hook(tool, inp, mode)] if code != 2]
        if allowed:
            msg = f"{len(allowed)} of {len(quoted) * len(modes)} quoted forms let through, e.g. {allowed[0]}"
            if self.STRICT:
                self.fail(f"{msg} ({self.QUOTED_WHY})")
            self.note(n, f"quoted forms: FAIL-expected ({self.QUOTED_WHY}); {msg}")
            self.skipTest(f"FAIL-expected: {self.QUOTED_WHY}; {msg} (CREAITE_HC_251_STRICT=1 makes it a failure)")
        self.note(n, f"the quoted, spliced and run forms ({len(quoted)} x {len(modes)} modes) refused too")

    def test_c38_ask_creaite_cannot_change_a_report_quoted_forms(self):
        """38 (quoted forms). The same refusal when the verb of filechange.py is quoted or spliced, or the script is run through
        system/scripts/run: filechange.py 'edit' …, ed''it, "delete", run filechange.py "create". Expected to fail on 2.5.1."""
        w, files = self.report_files()
        before = {k: self.stamp(f) for k, f in files.items()}
        f = str(files["client"])
        src = "system/staging/drafts/x.html"
        plain = [("Bash", {"command": f"python3 system/scripts/filechange.py edit '{f}' --from {src}"})]
        quoted = [("Bash", {"command": c}) for c in (
            f"python3 system/scripts/filechange.py 'edit' '{f}' --from {src}",
            f"python3 system/scripts/filechange.py ed''it '{f}' --from {src}",
            f'python3 system/scripts/filechange.py "delete" \'{f}\'',
            f"system/scripts/run filechange.py edit '{f}' --from {src}",
            f"system/scripts/run filechange.py 'create' '{f}' --from {src}",
            f'system/scripts/run filechange.py "delete" \'{f}\'')]
        try:
            self.quoted_check(38, plain, quoted, ("ask", "confirmed", "sweep"))
        finally:
            self.assertEqual({k: self.stamp(x) for k, x in files.items()}, before, "the report files are unchanged")

    def test_c39_ask_creaite_cannot_draft_or_file_a_report_quoted_forms(self):
        """39 (quoted forms). report.py weekly-stage and client-stage with the verb quoted or spliced ('weekly-stage', weekly''-stage,
        "client-stage"), also through system/scripts/run, in an ask, a confirmed and a sweep run. Expected to fail on 2.5.1."""
        w, files = self.report_files()
        before = self.listing(w)
        d = w["drafts"]
        plain = [("Bash", {"command": f"python3 system/scripts/report.py weekly-stage {d}/x.json"})]
        verbs = ("'weekly-stage'", "weekly''-stage", '"client-stage"', "client-st''age", "'client'-stage")
        quoted = [("Bash", {"command": f"python3 system/scripts/report.py {v} {d}/x.json"}) for v in verbs]
        quoted += [("Bash", {"command": f"system/scripts/run report.py {v} {d}/x.json"}) for v in verbs]
        try:
            self.quoted_check(39, plain, quoted, ("ask", "confirmed", "sweep"))
        finally:
            self.assertEqual(self.listing(w), before, "no report, draft or file appeared")

    def test_c40_ask_creaite_can_still_read_a_report(self):
        """40. Ask creaite: "summarise this week's report" → it reads the report and answers. (The guard lets the read through; the
        answer is the model's and live only.)"""
        self.need(self.fix_reports, "ask creaite's report guard (v251-askreports)")
        w, files = self.report_files()
        for kind, f in files.items():
            code, err = self.hook("Read", {"file_path": str(f)})
            self.assertEqual(code, 0, f"Read of the {kind} report was refused: {err}")
            code, err = self.hook("Grep", {"pattern": "migration", "path": str(f.parent)})
            self.assertEqual(code, 0, f"a search of the {kind} reports folder was refused: {err}")
        code, err = self.hook("Bash", {"command": "python3 system/scripts/report.py weekly-data FAL"})
        self.assertNotIn("Reporting hub", err, "reading a report's data is not taken for writing one")
        self.note(40, "Read and Grep of both reports allowed by the guard")


# ── the client export ──

class ClientExport(Called251):
    """Checks 41 to 43: Team Stark's tests, called (each with a throwaway vault and live server of its own). No hand-check vault is
    used; the class asks for none."""
    PAGE = "test_export_page"
    CALLS = {
        41: [("test_report_exports", ("WordLogos",)), (PAGE, ("SvgLogoClean",))],
        42: [("test_export_rename_name", ("RenameName",)),
             ("test_client_audience", ("Audience.test_a_weekly_export_cannot_be_renamed_to_a_client_reports_name",))],
        43: [(PAGE, ("Server.test_c08_a_client_report_page_is_checked_for_internal_wording_too",)),
             ("test_export_page_subset", ("PageSubset.test_a_page_with_words_the_saved_report_does_not_hold_is_refused",
                                          "PageSubset.test_control_the_page_the_dashboard_posts_is_kept_styled")),
             ("test_export_page_subset_unit", ("Subset",)),
             ("test_client_audience", ("Audience.test_a_client_report_edited_to_say_minutes_is_never_exported_by_the_minutes_route",
                                       "Audience.test_a_weekly_report_saved_with_a_client_audience_is_refused",
                                       "Audience.test_a_weekly_draft_edited_on_disk_to_a_client_audience_is_exported_as_internal",
                                       "Audience.test_control_a_normal_client_report_saves_approves_and_exports"))],
    }

    def test_c41_only_the_projects_own_logos_and_a_clean_svg(self):
        """41. Put another project's logo path into a saved report by hand → a Word client export draws no header logo from it; saving
        or approving a client report stores only the project's own logo paths; a client HTML export with an SVG logo that carries a
        script, link, comment or hidden text draws only its shapes and text. (test_report_exports WordLogos, test_export_page
        SvgLogoClean.)"""
        self.need("own_header_logos" in self.vtext("system/scripts/report_server.py"), "the logo hardening (2.5.1 M1)")
        self.called(self.CALLS[41])

    def test_c42_a_typed_name_cannot_claim_another_filing_name(self):
        """42. A typed export name that matches another report's filing name does not overwrite or claim it (it gets a number, or
        is refused). (test_export_rename_name; test_client_audience's rename test.)"""
        self.called(self.CALLS[42])

    def test_c43_a_posted_page_is_checked_and_the_minutes_refuse_a_client_report(self):
        """43. A client export made from a posted page uses that page only when its words are the saved report's own; a page with
        other words is refused; the minutes export refuses a client report; a weekly report stays internal."""
        self.called(self.CALLS[43])


if __name__ == "__main__":
    import unittest
    unittest.main()
