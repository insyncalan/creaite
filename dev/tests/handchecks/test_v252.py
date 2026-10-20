"""creaite 2.5.2's hand checks (dev/handchecks/v2.5.2.md: 25 checks, from the Product Manager's draft of 20-10-2026), automated
against a vault made from the release zip. Every check feature-detects its fix in the vault and SKIPS with the reason when it is
absent, so the file can be committed before the items land and runs against earlier heads. Nothing fails for code that has not landed.

Run them all, fill the Results table and make the screenshot sheet:  python3 dev/tools/handcheck.py v2.5.2
Run this file on its own (it makes the vault itself):                 python3 dev/tests/handchecks/test_v252.py
Run a check with its fix absent, to see it red:                       CREAITE_HC_252_FORCE=1 python3 dev/tests/handchecks/test_v252.py

  Client239    1, 2, 8    #239 the client output snapshot, on the hand-check vault's own Falcon reports (own vault): Approve freezes a
                          checked copy and every export is made from it; a posted page is never used; the minutes export refuses a client
                          report. Each also calls Team Stark's own tests of it (skipped until the vault holds client_snapshot.client_export)
  Called239    3 to 7, 9, 10  #239: Team Stark's tests, called (test_client_output_step1/2/3, test_client_audience, test_client_gate,
                          test_client_gate_late, test_export_rename_name); each skips until its tests are in this checkout
  11                      live only: a real client export (Word, HTML, PDF) with the real logo, opened in Word and a browser
  Usage238     12 to 18   #238 Activity › Usage (own vault; skipped until the vault holds #actTabU). 15 waits for the live server's
                          daily context-size job; 16 ("Your reviews" and CSV) waits for /api/usage/review (origin/v252-usage, not in the
                          2.5.2 release head d3a9d706)
  Intake245    19 to 21, 23 to 25  #245 Intake as a quiet line on Today (own vault; skipped until the vault holds tdQuiet)
  Empty245     22         #245 no line when nothing waits (own, empty vault)

Kinds: 18 and 25 are judgement (screenshots on the sheet, never Pass or Fail); 11 is live only (no test); the rest scriptable.
Never Microsoft 365, never a real model: Claude is the hand-check vault's stand-in. Fictional data only (the demo's people).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))      # dev/tests
import hcbase  # noqa: E402
from hcbase import NOTES, shown  # noqa: E402
from test_v230 import V230Case  # noqa: E402
from test_v240 import resolve as resolve_named, run_named  # noqa: E402  Team Stark's tests, called as the 2.4.0 checks call them

REPO = HERE.parents[2]

KIND = {**{n: "scriptable" for n in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24)},
        **{n: "judgement" for n in (18, 25)}}
LIVE_ONLY = {11: "with Alan: export a real client report as Word, HTML and PDF with the real logo and open each; it looks as before "
                 "and nothing hidden or internal is in it (logos stay out of git, so no test can hold them; checks 1 to 10 are the "
                 "automated half)"}

NOTES.clear()          # test_v230 (imported for its helpers) put its own notes here
NOTES.update({
    16: "waits for origin/v252-usage's Your reviews and its POST /api/usage/review (a guarded live_server.py diff); the 2.5.2 head "
        "d3a9d706 ships the read-only Usage tab of v251-usage-monitor, which has no review notes",
})

FORCE = os.environ.get("CREAITE_HC_252_FORCE") == "1"      # run a check although its fix is not in the vault (to see it red)

POISON = "POISONED-TEXT Jane Example wrote about the confidential merger"


def wait_for(fn, seconds=30, what="it"):
    """Poll `fn` until it returns something truthy; fail with `what` if it never does."""
    end = time.time() + seconds
    while time.time() < end:
        got = fn()
        if got:
            return got
        time.sleep(0.3)
    raise AssertionError(f"timed out waiting for {what}")


class V252Case(V230Case):
    """V230Case (the page's API, seeding, a Python probe in the vault) and what the 2.5.2 checks share."""
    width, height = 1400, 1000

    def vtext(self, rel):
        p = self.vault / rel
        return p.read_text(encoding="utf-8", errors="ignore") if p.exists() else ""

    def need(self, present, what):
        if not present and not FORCE:
            self.skipTest(f"{what} is not in this vault yet; this check runs once it is merged (CREAITE_HC_252_FORCE=1 runs it anyway)")

    # ── is the fix in this vault? (feature detection; never fail on code that is not there) ──

    @property
    def fix239(self):
        """#239 step 2 (v251-step2): every client file is made by client_snapshot.client_export from one checked snapshot."""
        return "def client_export" in self.vtext("system/scripts/client_snapshot.py")

    @property
    def fix239_page(self):
        """#239 step 3 (v251-step3): a page posted with a client export is not taken, and the answer says so."""
        return "page_ignored" in self.vtext("system/scripts/report_server.py")

    @property
    def fix238(self):
        """#238 (v251-usage-monitor, or v252-usage): Activity's Usage tab."""
        return "actTabU" in self.vtext("dashboard.html")

    @property
    def fix238_daily(self):
        """#238: the live server's daily job records the context sizes (the guarded live_server.py pass)."""
        src = self.vtext("system/scripts/live_server.py")
        return "usage_context_job" in src or "context_size" in src

    @property
    def fix238_reviews(self):
        """#238 (v252-usage): Your reviews, saved through POST /api/usage/review (needs its live_server.py diff)."""
        return "uRevAdd" in self.vtext("dashboard.html") and "usage_reviews" in self.vtext("system/scripts/live_server.py")

    @property
    def fix245(self):
        """#245 (v252-intake-line): the quiet Intake line on Today."""
        return "tdQuiet" in self.vtext("dashboard.html")

    # ── the page ──

    def reload(self):
        self.b.reload("typeof go==='function' && LIVE")
        if self.now:
            hcbase.pin_page_clock(self.b, self.now)

    def rebuild(self):
        code, out = self.run_in_vault("build_dashboard.py")
        self.assertEqual(code, 0, out[-400:])

    def today(self):
        self.b.eval("go('today'); renderToday()")
        self.b.wait("!document.getElementById('v-today').hidden && document.getElementById('mineSec')", 15)
        self.b.pump(0.4)


class Called252(V252Case):
    """Checks that call Team Stark's own tests (dev/tests/<file>.py, in a fresh process with a vault, server and Chrome of their own,
    as test_v240.py does) instead of writing them again. They run against THIS checkout's engine; the check first makes sure the
    hand-check vault was built from the same one, so they say the same thing about the zip."""

    def called(self, calls, note=True):
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
        if note:
            self.note(self.check_number(), f"{total} named tests of Team Stark's called, all passed: {', '.join(f for f, _ in found)}")
        return total


S1, S2, S3, AUD = "test_client_output_step1", "test_client_output_step2", "test_client_output_step3", "test_client_audience"
CALLS = {
    1: [(S2, ("Step2.test_snapshot_approve_writes_it_beside_the_filed_report_and_records_its_hash",
              "Step2.test_export_of_a_filed_report_renders_the_snapshot_not_the_file",
              "Step2.test_export_a_snapshot_changed_on_disk_is_refused",
              "Step2.test_whole_every_client_output_holds_no_needle")),
        (S3, ("Step3.test_route_cx_client_report_draft_is_approved_in_the_hub_and_exported_from_its_checked_copy",))],
    2: [(S1, ("Step1.test_f_a_page_posted_with_a_client_export_is_never_written",)),
        (S2, ("Step2.test_preview_a_posted_page_is_ignored", "Step2.test_preview_show_as_exported_is_the_servers_render_and_writes_nothing"))],
    3: [(AUD, ("Audience.test_a_draft_edited_on_disk_is_read_as_client_and_refused_at_approve_and_every_export",
               "Audience.test_a_draft_whose_kind_was_edited_on_disk_is_refused_at_approve_and_every_export",
               "Audience.test_read_report_reads_a_client_kind_as_client", "Audience.test_is_client_and_force_client_audience")),
        ("test_client_gate", ("TheSectionAudienceIsBoundOnTheServer.test_a_saved_client_report_that_reads_as_internal_is_refused",))],
    4: [(AUD, ("Audience.test_header_fields_sent_to_save_are_derived_again", "Audience.test_header_fields_edited_on_disk_are_derived_again",
               "Audience.test_header_fields_sent_with_approve_are_derived_again",
               "Audience.test_header_fields_edited_on_disk_are_derived_again_in_an_export_of_the_draft",
               "Audience.test_a_client_named_in_the_request_is_ignored")),
        (S1, ("Step1.test_b_a_logo_unticked_since_the_draft_was_made_is_not_drawn",)),
        ("test_client_gate", ("TheSectionAudienceIsBoundOnTheServer.test_a_page_claiming_weekly_for_the_client_report_gets_the_client_audience",))],
    5: [(S1, ("Step1.test_b_a_stored_logo_path_is_never_drawn_or_filed", "Step1.test_a_keys_the_gate_never_reads_never_reach_the_filed_client_file",
              "Step1.test_a_client_shape_keeps_only_known_keys", "Step1.test_c_a_picture_not_in_the_allowed_set_is_caught")),
        (S2, ("Step2.test_gap_c_a_picture_added_for_the_internal_report_is_never_in_a_client_file",
              "Step2.test_logo_a_logo_changed_after_approve_is_not_drawn_from_the_snapshot")),
        (S3, ("Step3.test_hard_link_a_hard_linked_client_picture_is_never_drawn",)),
        (AUD, ("Audience.test_the_filed_client_file_holds_only_creaites_own_meta_sources_and_layout",))],
    6: [(S1, ("Step1.test_look_alike_letters_are_read_as_the_letters_they_look_like",)),
        ("test_client_gate_late", ("TheReviewOf55967e3.test_an_invisible_character_hides_no_name_id_or_marker",
                                   "TheReviewOf55967e3.test_encoded_words_outside_any_address_are_read",
                                   "TheReviewOf62593f6.test_combining_marks_hide_no_id_marker_or_name"))],
    7: [(S3, ("Step3.test_gap_b_another_projects_hidden_wording_and_owner_never_reach_a_client_file",)),
        (AUD, ("Audience.test_another_projects_item_is_dropped_from_a_client_report",))],
    8: [(S1, ("Step1.test_e_a_client_draft_edited_to_say_minutes_is_refused_by_the_minutes_routes",
              "Step1.test_e_a_filed_client_report_edited_to_say_minutes_is_refused",
              "Step1.test_e_a_client_report_renamed_out_of_its_pattern_is_refused_by_its_data", "Step1.test_e_real_minutes_still_export")),
        (AUD, ("Audience.test_a_client_report_edited_to_say_minutes_is_never_exported_by_the_minutes_route",))],
    9: [("test_export_rename_name", ("RenameName",)),
        (AUD, ("Audience.test_a_weekly_export_cannot_be_renamed_to_a_client_reports_name",))],
    10: [(S3, ("Step3.test_word_template_docx_tools_never_fills_the_client_report_template",
               "Step3.test_route_cx_client_report_makes_no_word_file_and_stages_nothing",
               "Step3.test_word_as_staged_never_files_a_finding_and_approval_records_the_file",
               "Step3.test_word_a_draft_changed_after_approval_is_never_filed_with_the_tracker_proposal",
               "Step3.test_word_the_clean_approved_draft_is_filed_with_the_tracker_proposal",
               "Step3.test_migration_a_v2_5_0_filed_report_opens_and_exports_and_stays_untouched"))],
}


# ══ #239 ══════════════════════════════════════════════════════════════════════════════════════════════════════════════

class Client239(Called252):
    """Checks 1, 2 and 8 on the hand-check vault's own Falcon reports (a vault of their own: they approve and file reports), then
    Team Stark's tests of the same thing. The internal week is approved first, as the hub asks."""
    own_vault = True
    MARK = "Phase two starts once the paperwork is signed"
    _ready = None

    def post(self, path, body):
        self.b.wait("typeof D==='object' && !!D.token", 20)
        return self.api(path, body)

    def ready(self):
        """FAL's weekly report approved and a client draft saved with the marker sentence; returns the week (YYYY-MM-DD), once."""
        if type(self)._ready:
            return type(self)._ready
        w = self.post("/api/report/draft", {"kind": "weekly", "code": "FAL"})
        self.assertTrue(w.get("ok"), w)
        doc = w["doc"]
        week = doc.get("week_ending") or doc.get("date") or (doc.get("meta") or {}).get("period_end")       # the week's Friday
        self.assertRegex(str(week), r"^\d{4}-\d{2}-\d{2}$", f"premise: the draft names its week ({sorted(doc)})")
        h = next((s for s in w["doc"]["sections"] if s["id"] == "health"), None)
        if h is not None and not str(h.get("text") or "").strip():
            h["text"] = "The cut-over rehearsal moved a week."
        s = self.post("/api/report/save", {"doc": w["doc"], "base_version": w.get("version")})
        self.assertTrue(s.get("ok"), s)
        a = self.post("/api/report/approve", {"kind": "weekly", "code": "FAL", "week_ending": week, "force": True})
        self.assertTrue(a.get("ok") or "awaiting review" in str(a.get("message")), a)
        if not a.get("ok"):
            code, out = self.run_in_vault("tracker.py", "apply")
            self.assertEqual(code, 0, out[-400:])
        c = self.post("/api/report/draft", {"kind": "client", "code": "FAL", "week_ending": week})
        self.assertTrue(c.get("ok"), c)
        summary = next((s for s in c["doc"]["sections"] if s["id"] == "summary"), None)
        self.assertIsNotNone(summary, "premise: the client report has a summary section")
        summary["text"] = self.MARK + "."
        s = self.post("/api/report/save", {"doc": c["doc"], "base_version": c.get("version")})
        self.assertTrue(s.get("ok"), s)
        type(self)._ready = week
        return week

    def export(self, week, fmt, **more):
        return self.post("/api/report/export", {"kind": "client", "code": "FAL", "week_ending": week, "fmt": fmt, "on_clash": "number", **more})

    def text_of(self, p):
        p = Path(p)
        if p.suffix == ".pdf":                      # through the vault's bundled pypdf (pdftotext may be missing)
            return self.py("sys.path.insert(0, 'system/scripts/vendor')\nimport pypdf\n"
                           f"print(json.dumps(' '.join(x.extract_text() or '' for x in pypdf.PdfReader({str(p)!r}).pages)))")
        if p.suffix == ".docx":
            with zipfile.ZipFile(p) as z:
                return " ".join(z.read(n).decode("utf-8", "ignore") for n in z.namelist() if n.endswith(".xml"))
        return p.read_text(encoding="utf-8", errors="ignore")

    def registry(self):
        p = self.vault / "system/staging/client-snapshots.json"
        return json.loads(p.read_text(encoding="utf-8")).get("snapshots", {}) if p.exists() else {}

    def test_c01_approve_freezes_a_checked_copy_and_every_export_is_made_from_it(self):
        """1. Approve a client report → creaite freezes a checked copy of it; the approval is recorded; the Word, HTML and PDF client
        files are all made from that one copy."""
        self.need(self.fix239, "#239 step 2 (v251-step2: client_snapshot.client_export)")
        week = self.ready()
        a = self.post("/api/report/approve", {"kind": "client", "code": "FAL", "week_ending": week, "force": True})
        self.assertTrue(a.get("ok") or "awaiting review" in str(a.get("message")), a)
        if not a.get("ok"):
            code, out = self.run_in_vault("tracker.py", "apply")
            self.assertEqual(code, 0, out[-400:])
        snaps = sorted(self.vault.glob("projects/**/*.client.json"))
        self.assertTrue(snaps, "a snapshot (<filed name>.client.json) is written beside the filed client report")
        snap = snaps[-1]
        import hashlib
        h = hashlib.sha256(snap.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
        self.assertTrue(any(h in (e.get("hashes") or []) for e in self.registry().values()), "the snapshot's SHA-256 is recorded")
        self.assertIn(self.MARK, snap.read_text(encoding="utf-8"), "the snapshot holds the approved words")
        made = []
        for fmt in ("html", "docx", "pdf"):
            e = self.export(week, fmt)
            if fmt == "pdf" and not e.get("ok") and re.search(r"(?i)chrome|pdf", str(e.get("message"))):
                continue                                          # PDF needs Chrome headless; Word and HTML are the check
            self.assertTrue(e.get("ok"), (fmt, e))
            self.assertIn(self.MARK, self.text_of(self.vault / e["path"]), fmt)
            made.append(fmt)
        # the copy, not the file: change the filed report's words on disk and the next export still says the approved words
        filed = snap.with_name(snap.name[: -len(".client.json")])
        if filed.exists() and filed.suffix == ".html":
            raw = filed.read_text(encoding="utf-8")
            filed.write_text(raw.replace(self.MARK, "Phase two is cancelled"), encoding="utf-8")
            self.addCleanup(filed.write_text, raw, encoding="utf-8")
            e = self.export(week, "html")
            self.assertTrue(e.get("ok") or e.get("findings") is not None, e)
            if e.get("ok"):
                t = self.text_of(self.vault / e["path"])
                self.assertNotIn("Phase two is cancelled", t, "an export never takes words edited into the filed file")
        self.note(1, f"approved FAL's client report for {shown(week)}: {snap.name} recorded in the registry; {', '.join(made)} made from it")
        self.called(CALLS[1], note=False)

    def test_c02_a_posted_page_is_never_used(self):
        """2. A client export made from a page posted with the request: the posted page is never used (the saved, checked copy is)."""
        self.need(self.fix239_page, "#239 step 3 (v251-step3: page_ignored)")
        week = self.ready()
        page = f"<html><body><h1>Client report</h1><p>POSTEDPAGE words {POISON}</p></body></html>"
        e = self.export(week, "html", page=page)
        self.assertTrue(e.get("ok"), e)
        self.assertTrue(e.get("page_ignored"), "the answer says the page wasn't used")
        t = self.text_of(self.vault / e["path"])
        self.assertNotIn("POSTEDPAGE", t)
        self.assertIn(self.MARK, t, "the file is the saved report's own")
        self.note(2, "an HTML export posted with a page: page_ignored, the file holds the saved words only")
        self.called(CALLS[2], note=False)

    def test_c08_the_minutes_export_refuses_a_client_report(self):
        """8. The minutes export refuses a client report."""
        self.need(self.fix239, "#239 step 2 (v251-step2)")
        week = self.ready()
        e = self.export(week, "html")
        self.assertTrue(e.get("ok"), e)
        before = sorted(p.name for p in (self.vault / e["path"]).parent.iterdir())
        for fmt in ("docx", "html"):
            m = self.post("/api/minutes/export", {"path": e["path"], "format": fmt, "file_beside": True})
            self.assertFalse(m.get("ok"), (fmt, m))
        self.assertEqual(sorted(p.name for p in (self.vault / e["path"]).parent.iterdir()), before, "nothing new was made")
        self.note(8, "the minutes export refused FAL's client report as Word and as HTML; nothing made")
        self.called(CALLS[8], note=False)


class Called239(Called252):
    """Checks 3 to 7, 9 and 10: Team Stark's tests, called (each with a throwaway vault and live server of its own)."""

    def go(self, n):
        self.need(self.fix239, "#239 step 2 (v251-step2)")
        self.called(CALLS[n])

    def test_c03_a_client_report_is_always_a_client_report(self):
        """3. A client report whose file says it is internal (or has no kind) is still treated as a client report."""
        self.go(3)

    def test_c04_header_logos_and_audience_come_from_the_project(self):
        """4. The header, the logos and the audience on a client export come from the project at the time of export, not from the
        report file."""
        self.go(4)

    def test_c05_only_own_logos_and_pictures_and_extras_dropped(self):
        """5. Only the project's own logo files and the report's own pictures can be drawn; a logo or picture path from another
        project, or a hard-linked file, is not drawn; extra fields in the report are dropped."""
        self.need(self.fix239_page, "#239 step 3 (the hard-link rule)")
        self.go(5)

    def test_c06_look_alike_letters_are_caught(self):
        """6. Words hidden in look-alike letters or escapes (for example a Cyrillic letter inside a hidden item's word) are caught: the
        export is refused or the item is left out, as for a plain hidden word."""
        self.go(6)

    def test_c07_another_projects_words_are_caught(self):
        """7. Another project's words and owners in a client report are caught in the same way."""
        self.need(self.fix239_page, "#239 step 3 (gap B)")
        self.go(7)

    def test_c09_a_typed_name_cannot_claim_a_filing_name(self):
        """9. A typed export name that matches another report's filing name does not overwrite or claim it (it gets a number)."""
        self.go(9)

    def test_c10_the_older_word_route_is_gated(self):
        """10. A client report built by the older Word route goes through the same checked snapshot."""
        self.need(self.fix239_page, "#239 step 3")
        self.go(10)


# ══ #238 ══════════════════════════════════════════════════════════════════════════════════════════════════════════════

# The fixture (fictional, counts only), dev/tests/usage_fixture.py's runs moved to the session's today; its sums are worked there:
# this week 4 runs, $6.50, median start 21,000, average run $1.63; by kind ask 3, sweep 2, the alert check 1.
FX_DAY = date(2026, 10, 19)
FX_RUNS = [  # (when, kind, cost, start tokens, output, cache read, skills)
    ("2026-10-19T08:00:00", "ask", 1.00, 20000, 1000, 19000, []),
    ("2026-10-19T09:00:00", "ask", 2.00, 22000, 1000, 21000, ["cx-minutes"]),
    ("2026-10-17T10:00:00", "sweep", 3.00, 21000, 4000, 21000, ["cx-sweep"]),
    ("2026-10-15T10:00:00", "vip", 0.50, 21000, 0, 21000, []),
    ("2026-10-08T10:00:00", "ask", 2.00, 20000, 1000, 19000, []),
    ("2026-10-10T10:00:00", "sweep", 1.00, 20000, 1000, 20000, ["cx-sweep"]),
]
FX_KINDS = [["ask creaite", "3", "20,667", "20,000", "$5.00", "53%"], ["Sweep", "2", "23,000", "20,500", "$4.00", "42%"],
            ["Alert check", "1", "21,000", "21,000", "$0.50", "5%"]]
FX_CONTEXT = [("2026-09-19", "rules", 50000), ("2026-10-19", "rules", 53000), ("2026-10-12", "claude_md", 700),
              ("2026-10-19", "claude_md", 700), ("2026-10-19", "memory", 5000), ("2026-10-19", "skills", 9000)]
PANEL = "document.getElementById('actUsage')"
PTEXT = f"({PANEL}&&{PANEL}.innerText||'').replace(/\\s+/g,' ')"
CONTEXT_WORDS = {"rules", "claude_md", "memory", "skills"}


def moved(day_text, today):
    """A fixture date ("YYYY-MM-DD…") moved so that 2026-10-19 is `today`."""
    d = date.fromisoformat(day_text[:10]) + (today - FX_DAY)
    return d.isoformat() + day_text[10:]


class Usage238(V252Case):
    """Checks 12 to 18. A vault of their own: they write the run record and the context-size record (as usage_log and the daily job
    would), rebuild the page and read the tab."""
    own_vault = True

    def day(self):
        return date.fromisoformat((self.now or date.today().isoformat())[:10])

    def staging(self, name):
        return self.vault / "system/staging" / name

    def write_fixture(self, runs=True, context=True):
        t = self.day()
        for name, rows in (("run-usage.jsonl", [{"at": moved(a, t), "kind": k, "label": POISON if i == 0 else "chat",
                                                 "model": "claude-sonnet-5-5", "seconds": 5.0, "turns": 2, "input": 0, "output": o,
                                                 "cache_read": c, "cache_create": 0, "cost_usd": cost, "start_tokens": s,
                                                 "stopped": False, "skills": sk, **({"prompt": POISON} if i == 0 else {})}
                                                for i, (a, k, cost, s, o, c, sk) in enumerate(FX_RUNS)] if runs else []),
                           ("context-size.jsonl", [{"date": moved(d, t), "file": f, "bytes": b, "tokens": b // 4}
                                                   for d, f, b in FX_CONTEXT] if context else [])):
            p = self.staging(name)
            if rows:
                p.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
            elif p.exists():
                p.unlink()
        self.rebuild()
        self.reload()

    def tabs(self):
        self.screen("activity")
        return self.b.eval("[...document.querySelectorAll('#v-activity [role=tab]')].map(x=>x.textContent.trim())")

    def open_usage(self):
        b = self.b
        self.screen("activity")
        b.wait("!!document.querySelector('#actTabU')", 15)
        b.click("#actTabU")
        b.wait(f"{PANEL} && !{PANEL}.hidden && {PTEXT}.length > 20", 20)
        b.pump(0.6)
        return b

    def rows(self, sel):
        return self.b.eval(f"[...document.querySelectorAll({sel!r})].map(tr=>[...tr.children].map(c=>c.textContent.trim()))")

    def test_c12_activity_has_a_usage_tab(self):
        """12. Activity has a Usage tab beside Changes and Quality."""
        self.need(self.fix238, "#238 (the Usage tab)")
        tabs = self.tabs()
        self.assertEqual(tabs[:3], ["Changes", "Quality", "Usage"])
        b = self.open_usage()
        self.assertEqual(b.eval("document.querySelector('#actTabU').getAttribute('aria-selected')"), "true")
        self.assertEqual(b.eval("document.querySelector('#actTabU').getAttribute('aria-controls')"), "actUsage")
        self.assertTrue(b.eval("document.getElementById('actTbl').offsetParent===null"), "the change list steps aside")
        b.click("#actTabCh")
        b.wait(f"{PANEL}.hidden", 10)
        self.note(12, f"tabs: {', '.join(tabs)}; Usage shows its panel, Changes brings the list back")

    def test_c13_no_runs_yet(self):
        """13. With no runs recorded it says "No runs yet", not an empty chart or zeros."""
        self.need(self.fix238, "#238 (the Usage tab)")
        self.write_fixture(runs=False, context=False)
        b = self.open_usage()
        t = b.eval(PTEXT)
        self.assertIn("No runs yet", t)
        shown_bits = b.eval(f"[...{PANEL}.querySelectorAll('.ucard, svg, .ubar')].filter(e=>e.offsetParent!==null).length")
        self.assertEqual(shown_bits, 0, "no cards or chart drawn")
        for bad in ("NaN", "undefined", "$0.00"):
            self.assertNotIn(bad, t)
        self.note(13, "no run record: the tab says No runs yet; no cards, chart or zero sums")

    def test_c14_cards_table_chart_and_skills_from_a_fixture(self):
        """14. From a fixture record of runs: the summary cards, the by-kind table, the 14-day chart and the skills list show the right
        numbers; no text of any message is anywhere."""
        self.need(self.fix238, "#238 (the Usage tab)")
        self.write_fixture()
        b = self.open_usage()
        t = b.eval(PTEXT)
        for want in ("$6.50", "Cost this week", "Runs this week", "21,000", "$1.63", "Cost of an average run"):
            self.assertIn(want, t)
        kinds = self.rows('#actUsage table[aria-label="By kind of run"] tbody tr') or self.rows("#uKind tr")
        self.assertEqual(kinds, FX_KINDS)
        bars = b.eval("document.querySelectorAll('#actUsage rect.ubar, #actUsage .ubar').length")
        self.assertIn(bars, (14, 28), "a bar a day for 14 days (one or two aligned panels)")
        last = b.eval("(()=>{ const r=[...document.querySelectorAll('#actUsage rect.ubar title')]; return r.length ? r[r.length-1].textContent : ''; })()")
        if last:
            self.assertEqual(last, f"{shown(self.day().isoformat())}: $3.00, 2 runs")
        skills = {r[0]: r for r in (self.rows('#actUsage table[aria-label="Skills"] tbody tr') or self.rows("#uSkill tr"))}
        self.assertEqual(skills.get("cx-minutes", [])[1:3], ["1", "$2.00"])
        self.assertEqual(skills.get("cx-sweep", [])[1:3], ["2", "$4.00"])
        whole = b.eval("document.documentElement.outerHTML + ' ' + document.documentElement.innerText + ' ' + JSON.stringify(D.usage||{})")
        for word in ("POISONED", "Jane Example", "confidential merger"):
            self.assertNotIn(word, whole, "no text from the run record reaches the page or its data")
        self.note(14, f"fixture of 6 runs: cards $6.50, 4 runs, 21,000, $1.63; by kind {[k[0] for k in kinds]}; {bars} bars; no text")

    def test_c15_the_daily_context_size_record(self):
        """15. The live server's daily job adds one line a day per always-loaded file to the context-size record (file, bytes,
        estimated tokens, date; never text); the page only reads it."""
        self.need(self.fix238 and self.fix238_daily, "#238's daily context-size job (the guarded live_server.py pass)")
        f, today = self.staging("context-size.jsonl"), self.day().isoformat()
        f.unlink(missing_ok=True)

        def todays():
            if not f.exists():
                return []
            return [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines() if x.strip() and json.loads(x).get("date") == today]
        r = subprocess.run([sys.executable, "-I", "-c", "import sys, json\nsys.path.insert(0, 'system/scripts')\nimport live_server\n"
                            "print(json.dumps({'job': live_server.backup_daily_job(), 'again': (live_server.usage_context_job() "
                            "if hasattr(live_server, 'usage_context_job') else None)}))"],
                           cwd=self.vault, capture_output=True, text=True, env={**os.environ, "CREAITE_NOW": self.now or ""}, timeout=300)
        self.assertEqual(r.returncode, 0, r.stderr[-400:])
        out = json.loads(r.stdout.strip().splitlines()[-1])
        rows = todays()
        self.assertTrue(rows, f"the daily job wrote today's lines: {out['job']}")
        self.assertEqual({r["file"] for r in rows}, CONTEXT_WORDS, "one line per always-loaded group, by its fixed word")
        self.assertEqual(len(rows), len(CONTEXT_WORDS), "one line each, once")
        for r in rows:
            self.assertLessEqual(set(r), {"date", "file", "bytes", "tokens", "files"}, r)
            self.assertTrue(all(isinstance(r[k], int) for k in ("bytes", "tokens")), r)
        self.assertIsNone(out["again"], "the same day again: nothing more")
        before = f.read_bytes()
        code, again = self.run_in_vault("doctor.py")          # an ordinary pass of the engine writes nothing there either
        self.assertEqual(f.read_bytes(), before)
        # the page only reads it: opening the tab sends no write and leaves the file as it was
        self.rebuild()
        self.reload()
        b = self.b
        self.screen("activity")
        b.eval("window.__calls=[]; const f0=window.fetch; window.fetch=function(u,o){ window.__calls.push(((o&&o.method)||'GET')+' '+String(u).split('?')[0]); return f0.apply(this,arguments); }; true")
        b.click("#actTabU")
        b.wait(f"!{PANEL}.hidden", 15)
        b.pump(0.8)
        writes = [c for c in b.eval("window.__calls") if not c.startswith("GET ") and "usage" in c]
        self.assertEqual(writes, [], "the tab sends no write")
        self.assertEqual(f.read_bytes(), before, "the record is unchanged after the page read it")
        self.assertIn("Rules (creaite-rules.md)", b.eval(PTEXT))
        self.note(15, f"the daily job wrote {len(rows)} lines for {shown(today)} ({', '.join(sorted(r['file'] for r in rows))}), counts "
                      "only; a second run the same day added none; the tab only read it")

    @unittest.skip("struck from 2.5.2 (Natasha, 20-10-2026): Your reviews and the CSV follow in 2.5.3")
    def test_c16_your_reviews_and_csv(self):
        """16. "Your reviews": add a note → it is saved with its date and kept; Download as CSV gives the notes."""
        self.need(self.fix238 and self.fix238_reviews, "#238's Your reviews (origin/v252-usage with its /api/usage/review route)")
        b = self.open_usage()
        b.click("#uRevAdd")
        b.wait("document.getElementById('uRevForm').offsetParent!==null", 10)
        self.assertEqual(b.eval("document.getElementById('uRevDate').value"), self.day().isoformat())
        b.eval("document.getElementById('uRevSaw').value='Start load up a little'; document.getElementById('uRevDec').value='Trim the rules'")
        b.click("#uRevSave")
        b.wait("document.querySelectorAll('#uRev td.empty').length===0 || document.getElementById('uRevMsg').textContent!==''", 15)
        self.assertEqual(b.eval("document.getElementById('uRevMsg').textContent"), "", "the note was saved")
        self.assertIn("Start load up a little", b.eval("document.getElementById('uRev').innerText"))
        line = json.loads(self.staging("usage-reviews.jsonl").read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(line, {"date": self.day().isoformat(), "saw": "Start load up a little", "decided": "Trim the rules"})
        self.reload()
        b = self.open_usage()
        self.assertIn("Start load up a little", b.eval("document.getElementById('uRev').innerText"), "kept after a reload")
        csv = b.eval("uCsv((D.usage||{}).reviews||[])")
        self.assertIn(f'"{shown(self.day().isoformat())}","Start load up a little","Trim the rules"', csv)
        self.note(16, "a note saved with its date, kept after a reload, and in the CSV")

    def test_c17_alert_check_wording(self):
        """17. The kind that used to say VIP check says "Alert check" (nothing on the page says VIP)."""
        self.need(self.fix238, "#238 (the Usage tab)")
        self.write_fixture()
        b = self.open_usage()
        words = b.eval(f"{PANEL}.innerText + ' ' + [...{PANEL}.querySelectorAll('[aria-label],[title]')].map(e=>(e.getAttribute('aria-label')||'')+' '+(e.getAttribute('title')||'')+' '+e.textContent).join(' ')")
        self.assertIn("Alert check", words)
        self.assertNotRegex(words, r"(?i)\bvip\b")
        self.note(17, "the alert check's runs are \"Alert check\"; no VIP in the tab's text, names or tooltips")

    def test_c18_usage_look(self):
        """18. (judgement) The Usage tab against its locked mockup, light and dark, 1400 and 900 px."""
        self.need(self.fix238, "#238 (the Usage tab)")
        self.write_fixture()

        def prepare(b):
            b.eval("document.querySelector('#actTabU').click()")
        n = self.sheet(18, "activity", palettes=["creaite"], widths=(1400, 900), prepare=prepare)
        self.note(18, f"judgement: {n} screenshots on the sheet" if n else "judgement: no sheet in this run")


# ══ #245 ══════════════════════════════════════════════════════════════════════════════════════════════════════════════

KEY = "creaite-intakeline-dismissed"
LINE = "document.getElementById('tdQuiet')"
VISIBLE = f"(()=>{{const e={LINE}; return !!e && !e.hidden && e.offsetParent!==null;}})()"


class Intake245(V252Case):
    """Checks 19 to 21 and 23 to 25. A vault of their own: proposals staged (not applied), a meeting with its transcript ready and a
    new file in Intake, as the sweep and cx-edit would leave them; a message from a person Alan follows for 24."""
    own_vault = True
    _seeded = False

    def stage(self, text):
        """One proposal staged by propose.py stage, left pending (a sweep's or a meeting's proposal waits for Alan in Review)."""
        f = self.vault / "system/staging/drafts/hc-stage.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        due = (date.fromisoformat(self.now[:10]) + timedelta(days=9)).isoformat()
        f.write_text(json.dumps({"source_run": "cx-edit", "items": [
            {"op": "new", "table": "actions", "values": {"project": "FAL", "description": text, "owner": "Lena Fischer", "due_date": due,
                                                          "raised": self.now[:10], "source": f"Alan (cx-edit), {self.now[:10]}"},
             "decision": "pending"}]}),
                     encoding="utf-8")
        code, out = self.run_in_vault("propose.py", "stage", "system/staging/drafts/hc-stage.json")
        self.assertEqual(code, 0, out[-500:])

    def seed(self):
        if type(self)._seeded:
            return
        self.stage("Send the cut-over checklist to Northgate")
        self.stage("Book the go-live rehearsal room")
        tx = self.vault / "system/staging/transcripts.json"           # what the sweep records for today's FAL steering
        state = json.loads(tx.read_text(encoding="utf-8")) if tx.exists() else {"checked": {}}
        state.setdefault("checked", {})["hc-1"] = {"status": "available", "checked": self.now, "count": 1}
        tx.write_text(json.dumps(state), encoding="utf-8")
        (self.vault / "inbox").mkdir(exist_ok=True)
        shutil.copy2(self.vault / "system/templates/minutes-template.docx", self.vault / "inbox/2026 Falcon notes.docx")
        self.rebuild()
        type(self)._seeded = True

    def fresh(self, clear=True):
        self.seed()
        self.reload()
        if clear:
            self.b.eval(f"try{{localStorage.removeItem('{KEY}')}}catch(e){{}}")
        self.today()

    def text(self):
        return self.b.eval(f"({LINE}||{{textContent:''}}).textContent.replace(/\\s+/g,' ').trim()")

    def counts(self):
        return self.b.eval("({p:REV.filter(r=>!r.done).length, m:MTG().filter(mtgHasTx).length, f:(D.inbox||[]).filter(x=>x.state==='new').length})")

    @staticmethod
    def phrase(n, one, many):
        return f"{n} {one if n == 1 else many}"

    def test_c19_the_line_with_counts(self):
        """19. With meetings ready and proposals waiting, Today shows one small line at the foot of Your commitments with the right
        counts; the old Intake and Review section and its fold are gone."""
        self.need(self.fix245, "#245 (v252-intake-line)")
        self.fresh()
        b, c = self.b, self.counts()
        self.assertTrue(b.eval(VISIBLE), "the line is shown")
        self.assertGreaterEqual(c["p"], 2, "premise: the two staged proposals are in Review")
        self.assertEqual((c["m"], c["f"]), (1, 1), "premise: one meeting ready, one new file")
        parts = [self.phrase(c["m"], "meeting ready to process", "meetings ready to process"),
                 self.phrase(c["p"], "proposal to approve", "proposals to approve"),
                 self.phrase(c["f"], "new file to process", "new files to process")]
        self.assertEqual(self.text(), f"Intake: {parts[0]}, {parts[1]} and {parts[2]}.")
        self.assertEqual(b.eval("document.querySelectorAll('#tdQuiet').length"), 1, "one line")
        self.assertTrue(b.eval("document.getElementById('mineSec').lastElementChild.contains(document.getElementById('tdQuiet'))"),
                        "at the foot of Your commitments")
        o = b.eval("""({fold:!!document.getElementById('tdFold'), tdLine:!!document.getElementById('tdLine'),
          heads:[...document.querySelectorAll('#v-today h2')].map(h=>(h.firstChild||h).textContent.trim()),
          said:document.getElementById('v-today').textContent.includes('Intake and Review')})""")
        self.assertFalse(o["fold"] or o["tdLine"] or o["said"], o)
        self.assertNotIn("Intake and Review", o["heads"])
        self.note(19, f"\"{self.text()}\"; no Intake and Review section or fold")

    def test_c20_its_links(self):
        """20. Its links open Intake (the meetings) and Review (the proposals)."""
        self.need(self.fix245, "#245 (v252-intake-line)")
        self.fresh()
        b = self.b
        seen = {}
        for key, view in (("meetings", "inbox"), ("proposals", "review"), ("files", "inbox")):
            self.today()
            b.wait(f"document.querySelector('#tdQuiet [data-tdq={key}]')", 10)
            b.click(f"#tdQuiet [data-tdq={key}]")
            b.wait(f"VIEW==='{view}'", 10)
            seen[key] = view
        self.today()
        b.eval("document.querySelector('#tdQuiet [data-tdq=proposals]').focus()")
        b.key("Enter")
        b.wait("VIEW==='review'", 10)
        self.note(20, "meetings and files open Intake, proposals open Review (a click, and Enter from the keyboard)")

    def other_tab(self):
        """A second page of the same Chrome profile (so the same storage), driven by its own connection (test_today_intake_line)."""
        import urllib.request
        from cdp import Browser, WebSocket
        t = json.load(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{self.b.port}/json/new?{self.base}/", method="PUT")))
        c = Browser.__new__(Browser)
        c.ws, c.n, c.events, c.errors = WebSocket(t["webSocketDebuggerUrl"]), 0, [], []
        for domain in ("Page", "Runtime"):
            c.call(f"{domain}.enable")
        self.addCleanup(c.ws.close)
        c.wait("typeof go==='function' && LIVE", 20)
        if self.now:
            hcbase.pin_page_clock(c, self.now)
        c.settle_boot()
        c.eval("go('today'); renderToday()")
        return c

    def test_c21_dismiss_and_return(self):
        """21. The x hides the line; it stays hidden across a reload and in a second tab of the same browser, and comes back when a
        count rises above what it was (something new arrives) or the next morning. The choice is kept per browser; with browser storage
        blocked it still hides for that page load."""
        self.need(self.fix245, "#245 (v252-intake-line)")
        self.fresh()
        b = self.b
        c = self.other_tab()
        c.wait(VISIBLE, 10)
        b.eval("document.getElementById('tdQx').click()")
        b.pump(0.3)
        self.assertFalse(b.eval(VISIBLE), "the x hides it")
        c.wait(f"!{VISIBLE}", 10)                                           # the other tab of the same browser
        self.reload()
        self.today()
        self.assertFalse(b.eval(VISIBLE), "still hidden after a reload")
        # something new arrives: one more proposal
        self.stage("Confirm the hypercare rota")
        self.rebuild()
        self.reload()
        self.today()
        b.wait(VISIBLE, 15)
        self.assertIn(self.phrase(self.counts()["p"], "proposal to approve", "proposals to approve"), self.text())
        # the next morning
        b.eval("document.getElementById('tdQx').click()")
        b.pump(0.2)
        stored = b.eval(f"JSON.parse(localStorage.getItem('{KEY}'))")
        self.assertEqual(stored.get("day"), b.eval("TODAY"))
        b.eval(f"localStorage.setItem('{KEY}', JSON.stringify(Object.assign({json.dumps(stored)}, {{day:'2000-01-01'}})))")
        self.reload()
        self.today()
        self.assertTrue(b.eval(VISIBLE), "back the next morning")
        # browser storage blocked: it still hides for this page load
        b.eval("Object.defineProperty(window,'localStorage',{get(){ throw new Error('blocked'); }}); renderToday(); true")
        self.assertTrue(b.eval(VISIBLE))
        b.eval("document.getElementById('tdQx').click()")
        b.pump(0.2)
        b.eval("renderToday()")
        self.assertFalse(b.eval(VISIBLE), "with storage blocked it still hides for this load")
        self.reload()
        self.note(21, "hidden by the x, in the second tab and after a reload; back when a proposal arrived and the next morning; "
                      "with storage blocked it hid for the page load")

    def test_c23_no_quick_approve_or_reject_on_today(self):
        """23. The quick Approve and Reject on Today's rows are gone; approving works in Intake and Review."""
        self.need(self.fix245, "#245 (v252-intake-line)")
        self.fresh()
        b = self.b
        found = b.eval("""[...document.querySelectorAll('#v-today button, #v-today [role=button], #v-today a')].filter(e=>{
          const w=((e.getAttribute('aria-label')||'')+' '+(e.dataset.tip||'')+' '+e.textContent).trim();
          return /^(Approve|Reject)\\b/i.test(w); }).map(e=>e.outerHTML.slice(0,80))""")
        self.assertEqual(found, [], "no Approve or Reject on Today")
        self.assertEqual(b.eval("document.querySelectorAll('#v-today [data-tdact=approve],#v-today [data-tdact=reject],#v-today [data-rvact]').length"), 0)
        b.eval("go('review')")
        b.wait("!document.getElementById('v-review').hidden && document.getElementById('v-review').innerText.includes('cut-over checklist')", 15)
        n = b.eval("""[...document.querySelectorAll('#v-review button, #v-review [role=button]')].filter(e=>/^Approve\\b/i.test(
          ((e.getAttribute('aria-label')||'')+' '+e.textContent).trim())).length""")
        self.assertGreater(n, 0, "Review offers Approve")
        self.note(23, f"no Approve or Reject on Today; Review lists the staged proposals with {n} Approve controls")

    def test_c24_messages_section(self):
        """24. The Messages section sits above Week ahead only when there are messages from people you follow: each card has Make a work
        item and Dismiss; nothing on the card says who is followed."""
        self.need(self.fix245, "#245 (v252-intake-line)")
        self.fresh()
        b = self.b
        self.assertTrue(b.eval("document.getElementById('tdSec').hidden"), "no messages: no Messages section")
        rashid = "Rashid Al Suwaidi <rashid@northgate.example>"
        due = (date.fromisoformat(self.now[:10]) + timedelta(days=7)).isoformat()
        conv = {"kind": "teams", "conversation": "19:hc-252@thread.v2", "title": "Falcon go-live", "from": rashid,
                "people": [rashid, "Lena Fischer"], "last": f"{self.now[:10]} 08:40", "link": "https://teams.microsoft.com/l/chat/hc252",
                "sensitivity": "normal", "attachments": [], "summary": "Northgate will take the platform live once the checklist is signed.",
                "items": [{"type": "action", "text": "Sign the cut-over checklist", "owner": "Rashid Al Suwaidi", "due": due}],
                "messages": [{"text": POISON}], "body": POISON}
        code, out = hcbase.vip_found(self.vault, [conv], f"{self.now[:10]} 08:50")
        self.assertEqual(code, 0, out[-400:])
        self.rebuild()
        self.reload()
        self.today()
        b.wait("!document.getElementById('tdSec').hidden", 15)
        o = b.eval("""(()=>{ const s=document.getElementById('tdSec'); return {head:document.getElementById('hTd').firstChild.textContent.trim(),
          next:s.nextElementSibling&&s.nextElementSibling.id, rows:s.querySelectorAll('#tdList>li').length,
          acts:[...s.querySelectorAll('#tdList>li button')].map(x=>x.textContent.trim()||x.getAttribute('aria-label')),
          text:s.innerText+' '+[...s.querySelectorAll('[aria-label],[title],[data-tip]')].map(e=>(e.getAttribute('aria-label')||'')+' '+(e.getAttribute('title')||'')+' '+(e.dataset.tip||'')).join(' ')}; })()""")
        self.assertEqual(o["head"], "Messages")
        self.assertEqual(o["next"], "weekSec", "the section sits above Week ahead")
        self.assertGreaterEqual(o["rows"], 1)
        self.assertTrue(any(re.match(r"(?i)^(make|create) (a )?work item", a or "") for a in o["acts"]), o["acts"])
        self.assertTrue(any(re.match(r"(?i)^dismiss", a or "") for a in o["acts"]), o["acts"])
        self.assertNotRegex(o["text"], r"(?i)\bvip\b|\bfollow(ed|s|ing)?\b")
        self.assertNotIn("POISONED", o["text"])
        self.note(24, f"Messages above Week ahead with {o['rows']} card(s): {', '.join(sorted(set(x for x in o['acts'] if x)))}; "
                      "no VIP or followed wording")

    def test_c25_the_look(self):
        """25. (judgement) The line and the Messages cards look right, light and dark, 1400 and 900 px."""
        self.need(self.fix245, "#245 (v252-intake-line)")
        self.fresh()

        def prepare(b):
            b.eval(f"try{{localStorage.removeItem('{KEY}')}}catch(e){{}}; renderToday(); "
                   "document.getElementById('tdQuiet')&&document.getElementById('tdQuiet').scrollIntoView({block:'center'})")
        n = self.sheet(25, "today", palettes=["creaite"], widths=(1400, 900), prepare=prepare)
        self.note(25, f"judgement: {n} screenshots on the sheet" if n else "judgement: no sheet in this run")


class Empty245(V252Case):
    """Check 22. A vault of its own with nothing in it (no projects, no proposals, nothing in Intake), from the same release zip."""
    own_vault = True

    @classmethod
    def start_server(cls):
        import handcheck
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

    def test_c22_no_line_when_nothing_waits(self):
        """22. With nothing waiting there is no line."""
        self.need(self.fix245, "#245 (v252-intake-line)")
        b = self.b
        b.eval(f"try{{localStorage.removeItem('{KEY}')}}catch(e){{}}")
        self.today()
        self.assertEqual(b.eval("[REV.filter(r=>!r.done).length, MTG().filter(mtgHasTx).length, (D.inbox||[]).filter(x=>x.state==='new').length]"),
                         [0, 0, 0], "premise: nothing waits in this vault")
        self.assertFalse(b.eval(f"!!{LINE}"), "no line")
        self.assertFalse(b.eval("document.getElementById('mineSec').textContent.includes('Intake:')"))
        self.assertTrue(b.eval("document.getElementById('tdSec').hidden"), "and no Messages section")
        self.note(22, "an empty vault: no Intake line and no Messages section")


if __name__ == "__main__":
    import unittest
    unittest.main()
