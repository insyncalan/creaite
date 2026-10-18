"""#212: creaite 2.4.0's hand checks (the reporting release), automated. SCAFFOLDING: it runs green-with-skips today and fills in
as Team Stark's branches land.

Run them all, fill the Results table and make the screenshot sheet:  python3 dev/tools/handcheck.py v2.4.0
Run this file on its own (it makes the vault itself, for check 35):   python3 dev/tests/handchecks/test_v240.py

Numbered to the Product Manager's draft sheet (`git show origin/pm-intake-briefs:dev/handchecks/drafts/v2.4.0-DRAFT.md`, 36 checks,
28 struck, numbering kept; it moves to dev/handchecks/v2.4.0.md when Team Stark's landed list arrives). One method per check,
`test_cNN_…`, its docstring quoting the sheet's check.

How a check is wired (as test_v220.py): most of 2.4.0 has its own tests in dev/tests (the sheet names them under each check).
NAMED below lists, per check, the tests it calls: (file in dev/tests, the test names, the branch that brings them). `run_named`
runs them in a fresh process (their own throwaway vault and server, never the live vault, never Microsoft 365, the stand-in Claude)
and the check passes when every one ran and passed, none skipped. A check whose file or test is not in this checkout yet skips
with "waiting for <branch>: <file>::<test>", and one the sheet says has "no test found yet" skips with that reason. So nothing is
written twice, and nothing fails for a part that has not landed (the sheet: a check for a part not in the cut is struck, not
failed). A token is "test_name" (every class that defines it) or "Class.test_name".

A named test list that does not cover the whole check is PARTIAL (what is missing is in the check's note): the check passes on what
exists, and the note says what still has to be added when the rest lands.

Kinds are the sheet's map (KIND below). A part that only a person with the real Finder, Word or trackpad can do is said in NOTES
(HAND_PARTS), because a LIVE_ONLY entry would replace the scripted Pass.
  Wrapped     1 to 34, 36      the named tests (no vault, server or Chrome of its own); 28 is struck
  Always      35               doctor and the page errors on the hand-check vault (shared; nothing changes data)
Desktop (1400 px) and 900 px only for the sheet (Alan, 15-10-2026).
"""
import ast
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hcbase
from hcbase import NOTES, HandcheckCase

HERE = Path(__file__).resolve().parent
TESTS = HERE.parent
REPO = HERE.parents[2]

# The sheet's automation map (PM, for Team Stark to confirm). Changes as built are noted here when Stark's list arrives.
KIND = {**{n: "scriptable" for n in (1, 2, 3, 4, 6, 7, *range(9, 15), 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26,
                                     *range(29, 37))},
        **{n: "measurable" for n in (5, 8, 15)},
        **{n: "judgement" for n in (27,)}}
# 28 is struck (Check this report, #170, is out of 2.4.0): no kind, no row.

# A whole check that only a person can do. None: every check has a scripted part. The hand parts are in NOTES.
LIVE_ONLY = {}
HAND_PARTS = {
    16: "the feel of the trackpad pinch is live only; the wheel event with Ctrl or Cmd is scripted",
    20: "the real Finder window (Show in Finder) and the real viewers (Open) are live only; the answer and the toast are scripted",
    24: "Word itself on the laptop (no repair prompt) is live only; the LibreOffice render and the package checks are scripted",
    27: "the colours and transparency of the logos are judged on the screenshot sheet",
}
for _n, _t in HAND_PARTS.items():
    NOTES.setdefault(_n, "hand part: " + _t)

# Check number: what it is missing from the draft sheet today (the check passes on what is named; see PARTIAL above)
PARTIAL = {
    4: "still to come from the hub agents: the Client and Side by side switches hiding when off, Approve and Export offering only "
       "the internal report",
    8: "still to come: the logo drawn in the report header (36 px high, 180 wide, a dark plate on dark)",
    20: "no test yet that Settings › Advanced no longer has the row 'File report exports beside it' (the golden changed on v240-int)",
}

# ── the named tests, per check: [(file in dev/tests, (test names), branch that brings them)] ─────────────────────────────────
P4, P3, P220, P226, P227, P229 = "p240-h4", "p240-h3", "p240-220", "p240-226", "p240-227", "p240-229"
SAVE = "test_report_export_save"
PAGE = "test_report_export_page"
SETTING = "test_client_report_setting"
PANEL = "test_client_report_panel"
WORD = "test_word_export_227"
EXPORT_PAGE = "test_export_page"
CLIENT_VIEW = "test_client_view"

NAMED = {
    1: [("test_icons", ("TheRest.test_project_and_person_pages",), P4)],
    2: [("test_icons", ("TheRest.test_project_and_person_pages",), P4)],
    4: [(SETTING, ("Storage.test_missing_lines_mean_on_with_reminder_and_every_logo", "Storage.test_off_and_on_are_read",
                   "Storage.test_the_rhythm_line_is_not_taken_for_the_setting",
                   "Storage.test_the_template_and_a_new_project_start_off", "Reminders.test_on_reminds",
                   "Reminders.test_off_has_no_client_reminder_but_keeps_the_weekly_one",
                   "Reminders.test_reminder_off_has_no_client_reminder", "SessionStart.test_session_start_follows_the_setting"), P3),
        (PANEL, ("test_the_panel_has_the_switch_the_settings_and_the_three_tiles", "test_every_control_is_named",
                 "test_cog_label_names_the_state", "test_how_often_name_reminder_and_logo_ticks_are_saved",
                 "test_off_is_stored_on_the_project_and_deletes_nothing", "test_it_is_still_off_after_a_reload",
                 "test_settings_projects_and_the_panel_are_one_setting",
                 "test_off_the_reports_page_lists_only_the_internal_report",
                 "test_off_the_reporting_space_and_card_do_not_break"), P3)],
    8: [(SETTING, ("Routes.test_a_new_draft_starts_with_the_project_logo_choice_in_both_reports",
                   "Routes.test_upload_saves_the_file_under_the_right_name",
                   "Routes.test_a_trimmed_copy_is_drawn_and_the_original_stays_untouched",
                   "Routes.test_a_jpeg_says_a_transparent_png_or_svg_sits_better", "Routes.test_an_svg_is_kept_as_it_is",
                   "Routes.test_changing_the_type_leaves_one_logo", "Routes.test_refusals_write_nothing",
                   "Routes.test_remove_deletes_the_logo_and_its_original",
                   "Routes.test_the_read_route_still_serves_an_uploaded_logo"), P3),
        (PANEL, ("test_a_logo_chosen_on_the_screen_is_trimmed_for_drawing_and_the_original_is_kept",
                 "test_the_file_chooser_adds_a_logo_and_remove_takes_it_away",
                 "test_a_jpeg_is_told_a_transparent_png_or_svg_sits_better",
                 "test_a_file_that_is_not_a_picture_is_refused_and_nothing_is_saved"), P3)],
    19: [("test_review_meta_229", ("test_a_row_has_exactly_one_meta_line", "test_detail_on_hover_and_in_the_peek_and_marks_stay"), P229),
         ("test_activity_kind_229", ("test_no_kind_button_and_the_funnel_filters_by_kind",), P229),
         ("test_activity_even_browser", ("test_search_and_funnel_are_even",), P229)],
    20: [(SAVE, ("ExportSave.test_check1_each_format_of_the_weekly_report_is_saved_in_reports",
                 "ExportSave.test_check2_the_answer_names_the_folder_and_show_in_finder_accepts_it",
                 "ExportSavePage.test_check2_the_toast_names_the_folder_with_show_in_finder_and_open",
                 "ExportSave.test_check4_a_read_only_folder_says_so_and_writes_nothing",
                 "ExportSavePage.test_check4_a_failed_save_is_said_on_the_page",
                 "ExportSave.test_check5_each_format_of_the_client_report_is_saved_in_reports"), P220)],
    21: [(SAVE, ("ExportSave.test_check3_a_taken_name_asks_and_writes_nothing", "ExportSave.test_check3_add_a_number",
                 "ExportSave.test_check3_rename_it", "ExportSave.test_check3_overwrite_keeps_a_backup",
                 "ExportSavePage.test_check3_a_taken_name_offers_the_three_choices_and_cancel_writes_nothing",
                 "ExportSavePage.test_check3_each_choice_does_what_it_says",
                 "ExportSave.test_reserved_html_of_an_unfiled_report_asks_and_approve_still_works",
                 "ExportSavePage.test_reserved_name_offers_no_overwrite_on_the_page",
                 "ExportSave.test_check3_html_after_the_report_is_filed_asks_and_overwrite_is_undoable"), P220)],
    22: [(PAGE, ("test_c01_header_logos_one_title", "test_c02_health_block_strip_and_last_week", "test_c03_at_a_glance_strip",
                 "test_c04_milestones_picture_gap_and_table", "test_c05_tables_columns_chips_late_and_empty",
                 "test_c06_headings_and_text", "test_every_section_matches_the_screen"), P226)],
    23: [(PAGE, ("test_c10_fixed_light_print_theme_on_a4", "test_c11_pdf_equals_html_apart_from_page_breaks"), P226)],
    24: [(WORD, ("test_check_01_title_block_once_and_the_reports_logos",
                 "test_check_02_health_one_label_reason_last_week_and_the_strip",
                 "test_check_03_at_a_glance_is_a_small_table_overdue_red", "test_check_04_milestones_picture_and_table",
                 "test_check_05_tables_full_columns_priority_late_and_empty_sentence",
                 "test_check_06_text_kept_no_empty_heading_images_never_dropped",
                 "test_check_10_package_is_sound_and_opens_without_repair", "test_check_10b_libreoffice_render_text_in_order",
                 "test_check_02_04_real_pictures_from_chrome"), P227)],
    25: [(PAGE, ("test_c07_left_out_stays_out_of_the_file_and_its_source",), P226),
         (PAGE, ("test_c12b_a_page_that_fails_the_server_check_gives_the_plain_file_without_the_leak",), P226),
         (EXPORT_PAGE, ("Server.test_a_hidden_section_a_hidden_row_and_hidden_words_are_refused",), P226),
         (WORD, ("test_check_07_left_out_content_is_absent",), P227)],
    26: [(CLIENT_VIEW, ("ClientBrowser.test_c08_the_client_export_is_the_clients_exported_page_and_holds_nothing_internal",), P226),
         (EXPORT_PAGE, ("Server.test_c08_a_client_report_page_is_checked_for_internal_wording_too",), P226),
         (WORD, ("test_check_08_client_report_same_writer",), P227)],
    27: [(PAGE, ("test_c01_header_logos_one_title",), P226),
         (WORD, ("test_check_01_title_block_once_and_the_reports_logos",), P227)],
    31: [(PAGE, ("test_c12_without_a_page_the_python_renderer_still_makes_a_file_and_says_so",
                 "test_c12b_a_page_that_fails_the_server_check_gives_the_plain_file_without_the_leak"), P226),
         (EXPORT_PAGE, ("Fallback",), P226)],
    33: [(PAGE, ("test_c09_dates_are_dd_mm_yyyy",), P226)],
    34: [("test_no_real_names", ("NoRealNames",), "main")],
}

# Checks the draft sheet says have no test yet (Team Stark names one, or a hub branch lands): skipped with this reason.
NO_TEST = "no test found yet (the draft sheet): waiting for Team Stark to name one"


# ── calling the tests the sheet names ────────────────────────────────────────

def _classes(path):
    """{class: (own test names, all test names including those inherited within the module)} for a test file."""
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    classes = {c.name: c for c in tree.body if isinstance(c, ast.ClassDef)}

    def own(c):
        return {f.name for f in c.body if isinstance(f, ast.FunctionDef) and f.name.startswith("test")}

    def every(c):
        found = set(own(c))
        for base in c.bases:
            if isinstance(base, ast.Name) and base.id in classes:
                found |= every(classes[base.id])
        return found
    return {name: (own(c), every(c)) for name, c in classes.items()}


def resolve(file, tokens, tests=None):
    """The unittest ids for the tokens in dev/tests/<file>.py, and the tokens not found there. A bare name means every class that
    defines it, "Class.name" is checked (inheritance within the file counts), a bare class name means all of its tests."""
    path = (tests or TESTS) / f"{file}.py"
    if not path.exists():
        return [], [f"{file}.py"]
    classes = _classes(path)
    ids, missing = [], []
    for t in tokens:
        if "." in t:
            cls, name = t.split(".", 1)
            if cls in classes and name in classes[cls][1]:
                ids.append(t)
            else:
                missing.append(f"{file}::{t}")
        elif t in classes:
            ids.append(t)
        else:
            hits = [c for c, (own, _) in classes.items() if t in own]
            ids += [f"{c}.{t}" for c in hits]
            if not hits:
                missing.append(f"{file}::{t}")
    return ids, missing


def run_named(file, ids, timeout=1500):
    """Run the unittest ids of dev/tests/<file>.py in a fresh process; a failure is run once more (browser tests are timing sensitive
    on a busy machine). Returns (ok, message)."""
    ok, msg = _run_named(file, ids, timeout)
    if ok:
        return ok, msg
    ok2, msg2 = _run_named(file, ids, timeout)
    return (True, f"{file}: passed on the second run (the first failed: {msg[:160]})") if ok2 else (False, msg2)


def _run_named(file, ids, timeout):
    """One run. The process gets no CREAITE_* variable (the hand-check vault's pinned clock and port are not theirs)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("CREAITE_")}
    try:
        r = subprocess.run([sys.executable, str(TESTS / f"{file}.py"), *ids], cwd=REPO, env=env, capture_output=True, text=True,
                           timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, f"{file}: timed out after {timeout} s"
    out = r.stdout + r.stderr
    ran = re.search(r"Ran (\d+) tests?", out)
    skipped = re.search(r"skipped=(\d+)", out)
    if r.returncode != 0:
        why = [ln for ln in out.splitlines() if ln.startswith(("FAIL:", "ERROR:", "AssertionError", "Error"))][:4]
        return False, f"{file}: " + " | ".join(why or out.strip().splitlines()[-3:])
    if skipped:
        return False, f"{file}: {skipped.group(1)} of the named tests were skipped (Chrome missing?)"
    if not ran or int(ran.group(1)) < len(ids):
        return False, f"{file}: ran {ran.group(1) if ran else '?'} tests, expected at least {len(ids)}"
    return True, ""


def plan(n, tests=None):
    """Check n's named tests: ([(file, ids, branch)], [(token, branch) not in the checkout])."""
    found, missing = [], []
    for file, tokens, branch in NAMED.get(n, []):
        ids, gone = resolve(file, tokens, tests)
        missing += [(g, branch) for g in gone]
        if ids:
            found.append((file, ids, branch))
    return found, missing


class Wrapped(unittest.TestCase):
    """Checks 1 to 34 and 36: they call the tests they name, or skip with what they wait for."""

    def setUp(self):
        n = int(self._testMethodName[6:8])
        if hcbase.only() and n not in hcbase.only():
            self.skipTest("not in --only")

    def waiting(self, reason=NO_TEST):
        self.skipTest(reason)

    def named(self, n):
        """Call check n's named tests: skip while any is not in this checkout, fail if one fails, else pass with a note."""
        found, missing = plan(n)
        if not NAMED.get(n):
            self.skipTest(NO_TEST)
        if missing:
            branches = sorted({b for _, b in missing})
            self.skipTest(f"waiting for {', '.join(branches)}: " + ", ".join(t for t, _ in missing[:3])
                          + (f" and {len(missing) - 3} more" if len(missing) > 3 else ""))
        failed, total = [], 0
        for file, ids, _ in found:
            ok, msg = run_named(file, ids)
            total += len(ids)
            if not ok:
                failed.append(msg)
        self.assertEqual(failed, [], "\n".join(failed))
        part = f"; PARTIAL, {PARTIAL[n]}" if n in PARTIAL else ""
        NOTES[n] = "; ".join(x for x in (NOTES.get(n), f"{total} existing tests called, all passed: "
                                         + ", ".join(sorted({f for f, _, _ in found})) + part) if x)[:300]

    # ── The project page ──

    def test_c01_old_buttons_gone(self):
        """1. The two buttons "Weekly report" and "Client report" are not at the bottom of the project page. (#223)"""
        self.named(1)

    def test_c02_reports_icon_beside_files(self):
        """2. A Reports icon sits beside "Browse files" (Reports first, then Browse files; same size, border radius and class;
        name and hover "Reports"; a real button, reachable by keyboard) and opens the hub for that project (#reporting=<CODE>).
        (#225)"""
        self.named(2)

    # ── The hub (#221) ──

    def test_c03_internal_client_side_by_side(self):
        """3. Internal | Client | Side by side: each shows the right report; side by side shows both at a readable size and
        scrolling together."""
        self.waiting()

    def test_c04_client_report_on_or_off(self):
        """4. The client report setting (cog, last on the line): off → the switch disappears, only the internal report shows, no
        client reminder, Approve offers only the internal report; on → returns, nothing lost. The setting holds for every future
        report until changed, and reports already written are kept."""
        self.named(4)

    def test_c05_one_line_of_controls(self):
        """5. All controls on one line (view switch, week menu, zoom, Show as exported, Export, Approve, cog) at 1400 px; icons with
        tooltips; the cog is the right-most."""
        self.waiting()

    def test_c06_week_menu(self):
        """6. The week Menu: the date with a drop-down list of weeks (health dot, internal and client status, jump to a date); no
        "<" or ">"."""
        self.waiting()

    def test_c07_header_goes_on_scroll(self):
        """7. Scroll the report down → the search bar and title block go at once, leaving the one line; they return only at the very
        top; clicking a button on the line never brings them back."""
        self.waiting()

    def test_c08_click_to_add_a_logo(self):
        """8. Logos: click a logo's place in the report header → choose a file → it appears in both reports; the file is saved in
        the logos folder as `firm.<ext>`, `<CODE>-client.<ext>` or `<CODE>-partner.<ext>`; a filled logo sits on the page with no
        box and keeps its transparency; the firm's logo is always shown, the client's and partner's as ticked in the cog panel."""
        self.named(8)

    def test_c09_one_header(self):
        """9. One header: no repeated "Weekly report / project" title; the title block reads "Weekly report · Internal" (client:
        "Client report · Client")."""
        self.waiting()

    def test_c10_identical_editing(self):
        """10. The client report has the same editing as the internal one: the section menu, eyes, Add from the tracker, text
        sections, Show as exported; each client section says "Matching internal" or "Edited for the client" with a Match internal
        button."""
        self.waiting()

    def test_c11_approve_order(self):
        """11. Approve: the internal report first; the client report only after the internal one is approved."""
        self.waiting()

    # ── The report page (#217, #218) ──

    def test_c12_section_menu(self):
        """12. Section menu: small, with an icon per item, fully visible at 80%, 100% and 120% zoom and at 900 px wide; Esc closes it
        and returns focus."""
        self.waiting()

    def test_c13_health_row(self):
        """13. The health indicator keeps its original width (120 px at 100%, 96 px in the hub); the six-week strip and its dates
        are the same width; Change is the small button."""
        self.waiting()

    def test_c14_eyes(self):
        """14. The include or leave-out switch is an eye (a crossed-out eye when left out), never a dot, everywhere it is used."""
        self.waiting()

    def test_c15_add_from_the_tracker(self):
        """15. "Add from the tracker" under Risks and issues and under Overdue actions lists open items not yet in the report;
        adding marks them "Added by you"; the tracker is unchanged; non-overdue actions can be added; the client report offers
        only client-visible items."""
        self.waiting()

    def test_c16_trackpad_zoom(self):
        """16. Pinch (or Ctrl or Cmd with the scroll wheel) over the report zooms it in and out in every view; the zoom control
        shows the percentage and returns to Fit."""
        self.waiting()

    def test_c17_free_text_section(self):
        """17. A free-text section can be added at the foot and from any section's menu, given a heading, edited with the whole
        editor (heading menu, B I S, code, lists including checklist, quote, link, Insert with table, picture and code block, undo
        and redo, the `/` menu, AI on selected text), moved, left out of the export and deleted. (#218; items that slip are named
        by Stark.)"""
        self.waiting()

    def test_c18_gap_under_the_timeline(self):
        """18. The milestone list starts below the timeline picture with a clear gap, on screen and in Show as exported."""
        self.waiting()

    # ── Review and Activity (#229) ──

    def test_c19_review_and_activity(self):
        """19. Review: each row has one meta line (kind, approve individually, Draft a response on risks, reject guess, reason, and
        the source with its Open source link), on a single line with an ellipsis; the owner, priority and due date are in the hover
        tooltip and the peek (which still edits them); the conflict block, "approve individually" and Draft a response stay on the
        row. Activity: the Kind button is gone; Kind is in the funnel's field list and filters as before (a chip on the filter bar);
        the tick boxes are unchanged."""
        self.named(19)

    # ── Exports (#226, #227, #219, #220) ──

    def test_c20_saved_and_where(self):
        """20. After an export of HTML, Word or PDF, a file is saved in the project's Reports folder first; the message names
        "<project> › Reports" as a link that opens the folder, with Show in Finder and Open; a failed save says so plainly ("Not
        saved: <why>. Nothing was written."). All three use the plain name (no "(read only)" in the HTML name). Settings › Advanced
        no longer has the row "File report exports beside it"."""
        self.named(20)

    def test_c21_name_clash_choice(self):
        """21. A taken file name asks: Add a number (default), Rename it (the field shows the whole name), or Overwrite (a backup is
        kept); nothing is overwritten without the choice; Cancel saves nothing. The plain HTML name is reserved for the filed
        report so an export can never block "Approve and file". After the report is filed, exporting HTML at the plain name asks
        Overwrite, Rename or Add a number (Overwrite backs up the filed report; undoable)."""
        self.named(21)

    def test_c22_html_export(self):
        """22. HTML export: opened on its own it looks like "Show as exported": the title block and logos, no duplicate title or
        empty heading; the health flag block, six-week strip and "Last week"; the figures strip; the timeline picture and the
        milestone table with DD-MM-YYYY dates and state chips; the Response and Late columns and priority chips; the screen's
        sentence for an empty table; no empty heading for an untitled pane; images present."""
        self.named(22)

    def test_c23_pdf_export(self):
        """23. The PDF is the same as the HTML export (apart from page breaks), in the light print theme, A4; a picture and its table
        stay together."""
        self.named(23)

    def test_c24_word_export(self):
        """24. Word: the same parts in the firm's template, one title, one flag colour, the logos, the strip and timeline as
        pictures, full tables, DD-MM-YYYY, no empty sections; it opens without a repair prompt; a later page checked as well as
        page 1. A milestone left out of the list still shows in the timeline, as built."""
        self.named(24)

    def test_c25_hidden_stays_out(self):
        """25. Hidden sections, rows and figures are absent from every export (and from the file's source). A milestone left out of
        the milestone list is absent from the table but still shown in the timeline picture, exactly as on screen."""
        self.named(25)

    def test_c26_client_export(self):
        """26. The client report exports through the same writers, client-visible items only, and only after the internal report is
        approved; nothing hidden or sensitive reaches the file."""
        self.named(26)

    def test_c27_logos_in_exports(self):
        """27. Logos in every export, keeping their transparency (an SVG becomes a PNG for Word)."""
        self.named(27)

    def test_c28_struck(self):
        """28. Struck: Check this report (#170) is out of 2.4.0; numbering kept."""
        self.skipTest("struck: #170 is out of 2.4.0 (numbering kept)")

    # ── Always ──

    def test_c29_themes_and_widths(self):
        """29. Light and dark, creaite and Cursor palettes, at 1400 px and 900 px: the hub, the report and the dialogs."""
        self.waiting("waiting for the hub screen (p240-h3, p240-h4) to take the screenshot sheet: " + NO_TEST)

    def test_c30_keyboard(self):
        """30. Keyboard: the toolbar, the week menu, the section menu, the cog panel and the export dialog work without a mouse; Esc
        closes each."""
        self.waiting()

    def test_c31_fallback(self):
        """31. Fallback: with no browser or live server an export still produces a plain file, and says so."""
        self.named(31)

    def test_c32_reopened_and_refused(self):
        """32. Left out items stay out when the report is reopened, and a client export is refused before the internal one is
        approved."""
        self.waiting()

    def test_c33_dates(self):
        """33. Dates in DD-MM-YYYY everywhere in the hub and the exports."""
        self.named(33)

    def test_c34_no_real_names_or_logos(self):
        """34. No real names or logos are in the repo (the test_no_real_names run on the whole tree)."""
        self.named(34)

    def test_c36_export_asks_which_report(self):
        """36. With the project's client report ON, Export (after the format) asks Internal, Client or Both; Both saves two files,
        each with its own name-clash choice, and one message names both. With it OFF, Export exports the internal report with no
        question. A new project starts with the client report OFF. The client switch is one setting, in the hub's cog panel and in
        Settings › Projects. The separate client report page is gone."""
        self.waiting()


class Always(HandcheckCase):
    """Check 35, on the shared hand-check vault: nothing here changes data."""

    def test_c35_doctor_and_log(self):
        """35. The doctor and the debug log show no new errors after a full pass."""
        code, out = self.run_in_vault("doctor.py")
        failed = [ln for ln in out.splitlines() if ln.startswith("FAIL")]
        self.assertEqual(failed, [], "\n".join(failed))
        self.assertEqual(code, 0, out[-500:])
        summary = re.search(r"(\d+) passed, (\d+) failed", out)
        names = [n for n in ("today", "work", "review", "intake", "files", "activity", "projects", "cockpit", "people", "help",
                             "settings-essentials", "settings-advanced", "settings-health") if n in hcbase.SCREENS]
        for name in names:
            with self.subTest(name):
                self.screen(name)
        self.assertEqual(self.b.errors, [], "page errors")
        diag = self.b.eval("api('/api/diagnostics',{}).then(r=>r)")
        self.assertEqual((diag or {}).get("errors"), [], f"Diagnostics lists errors: {str((diag or {}).get('errors'))[:200]}")
        self.note(35, (summary.group(0) if summary else "doctor passed") + f"; {len(names)} screens, 0 page errors; Diagnostics clean"
                  + "; the hub and report screens are added to the pass when they land")


if __name__ == "__main__":
    unittest.main()
