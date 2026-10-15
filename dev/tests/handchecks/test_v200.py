"""BL-301 (creaite 2.0.0): the hand checks in dev/handchecks/v2.0.0.md, automated.

Run them all, fill the Results table and make the screenshot sheet:  python3 dev/tools/handcheck.py v2.0.0
Run this file on its own (it makes the vault itself):                 python3 dev/tests/handchecks/test_v200.py

One method per check, `test_cNN_…`, its docstring quoting the check. Desktop (1400 px) and 900 px only.
  Wrapped      1 to 18, 20 to 42, 45   run the test(s) the check names (CHECKS), each in its own process, and pass when they all
                                       pass and none is skipped (a skipped test proves nothing). Their own vaults and servers.
  Written      19 (the day line's ] and T, in the hand-check vault) and 46 (the day's backup zip holds the note drafts)
  Judgement    44   the screenshot sheet (desktop and 900 px), plus the two tests that measure part of it
  Live only    43   the real-data gate reads Alan's real vault (LIVE_ONLY)
Helpers: hcbase.HandcheckCase (screens, notes, the sheet, own vaults), test_backups.Case (check 46).
"""
import re
import subprocess
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hcbase import NOTES, SCREENS, HandcheckCase, only  # noqa: E402,F401  (NOTES: read by handcheck.py)

TESTS = Path(__file__).resolve().parents[1]

KIND = {**{n: "scriptable" for n in range(1, 43) if n not in (43,)}, 45: "scriptable", 46: "scriptable",
        44: "judgement", 43: "live only"}

LIVE_ONLY = {
    43: "reads Alan's real vault (tiptap_roundtrip.py --vault <the live vault> --private --exact --vendored, plan step 6, "
        "with Team Cap on laptop 1), which no test may; the fixture gate is test_one_editor_gate.py",
}

# Check number: the tests its text names, "file::test" (files in dev/tests/)
CHECKS = {
    1: ["test_notes_server.py::test_the_folder_is_08_notes_and_doctor_does_not_ask_for_one_not_made"],
    2: ["test_dashboard.py::test_renders_in_chrome_without_errors"],
    3: ["test_notes_tab_browser.py::test_tabs_and_a_note_made_typed_and_saved_once"],
    4: ["test_notes_gaps.py::test_c_working_session_date_and_with_edited_later", "test_notes_gaps_browser.py::test_working_session_date_and_with_edited_in_the_header"],
    5: ["test_notes_tab_browser.py::test_tabs_and_a_note_made_typed_and_saved_once", "test_notes_tab.py::test_2_draft_then_save_once_and_undo"],
    6: ["test_notes_tab.py::test_2_draft_then_save_once_and_undo"],
    7: ["test_notes_tab_browser.py::test_pickers_chips_backlinks_and_the_peek"],
    8: ["test_notes_gaps_browser.py::test_image_button_files_a_picture_in_images"],
    9: ["test_notes_gaps_browser.py::test_renamed_title_renames_the_file_and_links_follow"],
    10: ["test_notes_tab.py::test_3_changed_outside_is_never_overwritten"],
    11: ["test_notes_tab_browser.py::test_list_collapses_and_stays_collapsed", "test_notes_tab.py::test_4_list_portfolio_and_refusals"],
    12: ["test_capture_drawer.py::test_confidential_switch_marks_the_note", "test_notes_server.py::test_a_new_project_gets_a_notes_folder"],
    13: ["test_capture_drawer.py::test_shortcut_opens_from_any_page_guesses_and_done_saves", "test_capture_drawer.py::test_n_is_the_second_key_and_not_while_typing"],
    14: ["test_capture_drawer.py::test_shortcut_opens_from_any_page_guesses_and_done_saves", "test_capture_drawer.py::test_escape_keeps_the_draft_and_returns_focus", "test_capture_drawer.py::test_unfiled_auto_and_refusals"],
    15: ["test_capture_drawer.py::test_done_and_find_updates_opens_the_note_with_find_updates"],
    16: ["test_capture_drawer.py::test_a_recent_note_opens_in_the_notes_tab"],
    17: ["test_capture_drawer.py::test_confidential_switch_default_off_and_saved", "test_capture_drawer.py::test_note_in_ask_creaite_and_new_note_in_cmdk"],
    18: ["test_capture_drawer.py::test_note_for_this_meeting", "test_capture_drawer.py::test_meeting_fills_the_working_session"],
    20: ["test_ai_select_notes.py::test_the_bar_offers_the_notes_options_and_make_this_an_action_before_say_what_you_want", "test_block_ai_select.py::test_the_bar_is_a_named_toolbar_with_the_menu_block_and_the_places_options"],
    21: ["test_ai_select.py::test_the_check_notes_every_date_number_name_and_id_lost_or_added", "test_block_ai_select.py::test_show_changes_is_a_toggle_and_the_notes_are_a_named_list"],
    22: ["test_ai_select.py::test_a_suggestion_changes_nothing_until_accept_and_one_undo_takes_it_back"],
    23: ["test_ai_select.py::test_discard_try_again_and_the_counts_hold_no_text", "test_ai_select.py::test_the_check_notes_every_date_number_name_and_id_lost_or_added"],
    24: ["test_ai_select.py::test_select_all_then_alt_slash_and_say_what_you_want"],
    25: ["test_ai_select_notes.py::test_a_confidential_note_asks_before_its_text_goes_to_claude", "test_ai_select.py::test_a_confidential_text_asks_once_before_it_goes_to_claude"],
    26: ["test_ai_select_notes.py::test_make_this_an_action_opens_find_updates_on_that_line_only", "test_ai_select_notes.py::test_a_selection_over_two_lines_runs_nothing_and_says_why"],
    27: ["test_ai_select.py::test_discard_try_again_and_the_counts_hold_no_text"],
    28: ["test_find_updates_panel.py::test_find_1_opens_the_panel_beside_the_note_with_markers_on_its_lines", "test_find_updates_panel.py::test_the_mockup_rows_grouped_with_markers_and_the_bulk_rule"],
    29: ["test_find_updates_panel.py::test_the_mockup_rows_grouped_with_markers_and_the_bulk_rule", "test_find_updates_panel.py::test_a_row_opens_in_the_peek_layout_to_edit_it_first", "test_notes_find.py::test_a_hedged_milestone_gets_a_confirm_action_when_claude_gave_none"],
    30: ["test_find_updates_panel.py::test_apply_writes_the_ticked_rows_in_one_apply_and_undo_reverses_it", "test_find_updates_panel.py::test_an_items_source_names_the_note_and_its_line", "test_find_updates_panel.py::test_a_source_link_opens_the_note_at_its_line_highlighted"],
    31: ["test_find_updates_panel.py::test_lines_already_sent_show_a_margin_tick", "test_find_updates_panel.py::test_apply_ticks_the_sent_lines_and_undo_takes_the_ticks_away"],
    32: ["test_find_updates_panel.py::test_save_for_later_and_a_second_run_skips_sent_lines"],
    33: ["test_notes_server.py::test_what_was_sent_is_kept_beside_the_note_without_its_text"],
    34: ["test_one_editor.py::test_a_small_edit_saves_everything_else_byte_for_byte"],
    35: ["test_one_editor.py::test_opening_and_saving_unchanged_writes_nothing"],
    36: ["test_one_editor.py::test_a_small_edit_saves_everything_else_byte_for_byte", "test_one_editor.py::test_undo_and_redo_are_the_editors_keys", "test_one_editor.py::test_escape_asks_before_losing_an_edit"],
    37: ["test_one_editor.py::test_every_text_field_is_the_one_editor_as_plain_text"],
    38: ["test_ai_select.py::test_make_it_executive_is_an_option_of_ai_beside_save"],
    39: ["test_notes_guard.py::test_a_note_doesnt_mark_and_a_transcript_in_the_same_project_still_does", "test_reach.py::test_a_note_is_what_notes_note_of_accepts"],
    40: ["test_notes_guard.py::test_the_server_marks_the_same_way", "test_notes_guard.py::test_a_note_doesnt_mark_and_a_transcript_in_the_same_project_still_does"],
    41: ["test_notes_guard.py::test_a_note_doesnt_mark_and_a_transcript_in_the_same_project_still_does"],
    42: ["test_notes_guard.py::test_everything_else_still_marks"],
    45: ["test_help.py::test_the_files_are_up_to_date_with_help_md", "test_help.py::test_how_to_has_the_tasks_in_five_groups", "test_snapshots.py::test_every_screen_matches_its_golden"],
    44: ["test_notes_tab_browser.py::test_narrow_screen_has_no_sideways_scroll", "test_one_editor.py::test_nothing_sideways_at_320_and_dark_and_reduced_motion"],
}

_RESULTS = {}      # "file::test": (ok, note)


def run_ref(ref):
    """One named test in its own process (python3 -m unittest -k <test> <module>, from dev/tests). Passes only when it ran at
    least one test and none failed or was skipped."""
    f, name = ref.split("::")
    try:
        r = subprocess.run([sys.executable, "-m", "unittest", "-k", name, f[:-3]], cwd=TESTS, capture_output=True, text=True,
                           timeout=900)
    except subprocess.TimeoutExpired:
        return False, f"{ref}: timed out after 900 s"
    out = r.stdout + r.stderr
    ran = re.search(r"Ran (\d+) test", out)
    n = int(ran.group(1)) if ran else 0
    if r.returncode == 0 and n >= 1 and "skipped" not in out:
        return True, f"{n} test(s) in {f}"
    why = "skipped (no Chrome?)" if r.returncode == 0 and n >= 1 else next(
        (ln for ln in reversed(out.strip().splitlines()) if re.match(r"(\w*Error|AssertionError|FAILED|Error)", ln)), out.strip()[-200:])
    return False, f"{ref}: {why}"[:300]


def setUpModule():
    """Run every named test the selected checks need, four at a time, before the checks report them."""
    want = {r for n, refs in CHECKS.items() if not only() or n in only() for r in refs}
    with ThreadPoolExecutor(4) as pool:
        for ref, res in zip(sorted(want), pool.map(run_ref, sorted(want))):
            _RESULTS[ref] = res


def named(case, n):
    """Pass when every test check `n` names passed."""
    bad = [_RESULTS[r][1] for r in CHECKS[n] if not _RESULTS[r][0]]
    if bad:
        case.fail("; ".join(bad))
    NOTES[n] = "; ".join(x for x in (NOTES.get(n), f"ran {', '.join(r.split('::')[1] for r in CHECKS[n])}") if x)[:280]


class Wrapped(unittest.TestCase):
    """Checks that run the tests they name."""

    def setUp(self):
        n = int(self._testMethodName[6:8])
        if only() and n not in only():
            self.skipTest("not in --only")

    def named(self, n):
        named(self, n)

    def test_c01_the_folder_is_08_notes_and_doctor_does_n(self):
        """1. `system/scripts/run doctor.py` → every check passes. Settings › Advanced shows the **Notes folder** setting (`08 Notes`, used when the projects live …"""
        self.named(1)

    def test_c02_renders_in_chrome_without_errors(self):
        """2. Visit every screen once → no page errors. Settings › Diagnostics says "No errors in the last 7 days" (check again at the end)."""
        self.named(2)

    def test_c03_tabs_and_a_note_made_typed_and_saved_onc(self):
        """3. Projects › Falcon Data Platform → two tabs, **Overview** and **Notes**, and no others. Notes → "No notes yet", with **New note**. The tab title is …"""
        self.named(3)

    def test_c04_c_working_session_date_and_with_edited_l(self):
        """4. **New note** → a dialog with Title and Template (**Blank**, **Stakeholder**, **Lessons learned**, **Working session**). Choose Working session: Date …"""
        self.named(4)

    def test_c05_tabs_and_a_note_made_typed_and_saved_onc(self):
        """5. Click in the note and type a line → no Edit or Save button; the toolbar shows while the cursor is in the note; the header says "Editing". Leave the …"""
        self.named(5)

    def test_c06_2_draft_then_save_once_and_undo(self):
        """6. Type, then wait 30 seconds without typing → "Saved" without leaving. Reload in the middle of typing → nothing lost (the draft comes back, then saves)."""
        self.named(6)

    def test_c07_pickers_chips_backlinks_and_the_peek(self):
        """7. Type `[[`, `@`, `#` and `/` on an empty line → each opens its picker; ↑ ↓ Enter and Esc work. Pick FAL-A-001 → a chip with its live state. Click the …"""
        self.named(7)

    def test_c08_image_button_files_a_picture_in_images(self):
        """8. **Image** on the toolbar, pick a small PNG → it shows after the paragraph, with a caption; `notes/_images/` holds it. × removes it from the note; the …"""
        self.named(8)

    def test_c09_renamed_title_renames_the_file_and_links(self):
        """9. **Rename:** change the title to "Catch-up with Lena Fischer" and leave the note → the file is now `Catch-up with Lena Fischer.md`; the address …"""
        self.named(9)

    def test_c10_3_changed_outside_is_never_overwritten(self):
        """10. Change the file in a text editor while the note is open, then type in creaite → nothing overwrites the file: "This note was changed outside …"""
        self.named(10)

    def test_c11_list_collapses_and_stays_collapsed(self):
        """11. « hides the list to a slim strip (⌘/ too) and the note widens; reload → still hidden. » brings it back. Projects › **Portfolio notes** → the …"""
        self.named(11)

    def test_c12_confidential_switch_marks_the_note(self):
        """12. ⋯ › Mark confidential → the header tag says "Confidential" and the file has `confidential: true`. Files → a Notes folder for FAL."""
        self.named(12)

    def test_c13_shortcut_opens_from_any_page_guesses_and(self):
        """13. On Work, Review, Today and Settings in turn, press **⌘⇧N** → the note drawer opens at the right, "New note", and the page doesn't move. Press **N** …"""
        self.named(13)

    def test_c14_shortcut_opens_from_any_page_guesses_and(self):
        """14. Type "FAL sandbox access granted yesterday" → Project says Falcon Data Platform, "guessed from “FAL”". Choose ORX → "chosen by you"; typing more …"""
        self.named(14)

    def test_c15_done_and_find_updates_opens_the_note_wit(self):
        """15. **Done and find updates** on a new FAL note → it is saved and the note opens on FAL's Notes tab with Find updates beside it (address …"""
        self.named(15)

    def test_c16_a_recent_note_opens_in_the_notes_tab(self):
        """16. In the drawer, click a saved note under Recent notes → it opens on its Notes tab."""
        self.named(16)

    def test_c17_confidential_switch_default_off_and_save(self):
        """17. The drawer's **Confidential** switch → off by default; on, Done → the file has `confidential: true`. Intake → Calendar import and Upload files only; …"""
        self.named(17)

    def test_c18_note_for_this_meeting(self):
        """18. Today → **Note** under FAL Steering committee; none under Dentist (private). Press it → the drawer is "Note for this meeting": Project Falcon Data …"""
        self.named(18)

    def test_c20_the_bar_offers_the_notes_options_and_mak(self):
        """20. In the FAL note, type "The sandbox is ready and teh review can start. Lena will start the security review." Select it → a small bar with **AI ▾** …"""
        self.named(20)

    def test_c21_the_check_notes_every_date_number_name_a(self):
        """21. **Fix spelling and grammar** → a card "A suggestion: your text is unchanged until you accept it", with "✓ Keeps your dates, numbers, names and item …"""
        self.named(21)

    def test_c22_a_suggestion_changes_nothing_until_accep(self):
        """22. **Accept** → the note's text changes in one step, and the note saves as usual. ⌘Z → the original text is back. ⌘⇧Z → the suggestion again."""
        self.named(22)

    def test_c23_discard_try_again_and_the_counts_hold_no(self):
        """23. Select the second sentence, **Shorter** → the suggestion adds "Due 20-10-2026.", and under it "The suggestion adds 20-10-2026, which your text didn't …"""
        self.named(23)

    def test_c24_select_all_then_alt_slash_and_say_what_y(self):
        """24. "Or say what you want…", type "capitals", Enter → the stand-in's answer in capitals; Esc in the box goes back to the text."""
        self.named(24)

    def test_c25_a_confidential_note_asks_before_its_text(self):
        """25. Mark the note confidential (⋯), select text, Rewrite clearly → first "This is confidential. Send the selected text to Claude for a suggestion? You're …"""
        self.named(25)

    def test_c26_make_this_an_action_opens_find_updates_o(self):
        """26. Select text on one line, **Make this an action, a risk, a decision or an update** → Find updates opens beside the note for that line only. Select …"""
        self.named(26)

    def test_c27_discard_try_again_and_the_counts_hold_no(self):
        """27. `system/staging/draft-stats.json` → counts under `edit` (offered, used, rejected), no text."""
        self.named(27)

    def test_c28_find_1_opens_the_panel_beside_the_note_w(self):
        """28. In vault A make a Working session note in FAL titled "Catch-up with Omar" with Omar Ali, then replace its body with the fixture's `BODY` from …"""
        self.named(28)

    def test_c29_the_mockup_rows_grouped_with_markers_and(self):
        """29. Each row has a numbered marker that matches one on its line; point at either → both highlight. The new risk and the memory line start unticked; the …"""
        self.named(29)

    def test_c30_apply_writes_the_ticked_rows_in_one_appl(self):
        """30. **Apply 5 changes** → "5 changes applied to Falcon Data Platform" with **Undo**; the items are in Work, each with the note's line as its source …"""
        self.named(30)

    def test_c31_lines_already_sent_show_a_margin_tick(self):
        """31. Apply again, close the panel, run Find updates again → only new or changed lines are read. A line already sent shows a ✓ in the note's left margin; …"""
        self.named(31)

    def test_c32_save_for_later_and_a_second_run_skips_se(self):
        """32. Tick a row, **Save for later** → it is in Review, under the note; nothing applied. Stop the live server, run Apply from an already-open panel → "The …"""
        self.named(32)

    def test_c33_what_was_sent_is_kept_beside_the_note_wi(self):
        """33. `system/staging/notes-sent.json` → paragraph numbers, fingerprints, item IDs and the apply number; no words from the note. The note file itself is …"""
        self.named(33)

    def test_c34_a_small_edit_saves_everything_else_byte(self):
        """34. In a text editor, add to the end of FAL's Current state section in `projects/FAL Falcon Data Platform/CLAUDE.md`: a line with `*an italic in stars*`, …"""
        self.named(34)

    def test_c35_opening_and_saving_unchanged_writes_noth(self):
        """35. Projects › Falcon Data Platform › the pencil (Edit current state), then **Save** with no change → `cmp` says nothing; no new apply in Activity."""
        self.named(35)

    def test_c36_a_small_edit_saves_everything_else_byte(self):
        """36. Edit again, change one word in the left pane, Save → `diff` shows only that line changed: the stars, the entity, the bare link, the list and the …"""
        self.named(36)

    def test_c37_every_text_field_is_the_one_editor_as_pl(self):
        """37. An item's title, latest update and source in the peek, and Prep's notes → typed text is saved exactly as typed (a leading `1. ` or `*` stays plain …"""
        self.named(37)

    def test_c38_make_it_executive_is_an_option_of_ai_bes(self):
        """38. AI ▾ beside Save in Current state › Make it executive → BL-106's whole-text flow (facts, evidence), as before."""
        self.named(38)

    def test_c39_a_note_doesnt_mark_and_a_transcript_in_t(self):
        """39. ask creaite (⌘J): "read my note and make a follow-up" → the stand-in reads the note, then asks for one new file in the same `08 Notes` folder → `HC …"""
        self.named(39)

    def test_c40_the_server_marks_the_same_way(self):
        """40. `system/guard/run.json` during or after that run → not marked as having read outside content."""
        self.named(40)

    def test_c41_a_note_doesnt_mark_and_a_transcript_in_t(self):
        """41. "read the transcript and make a follow-up" → the stand-in reads the transcript, then asks for the same kind of file → it waits on **one card** …"""
        self.named(41)

    def test_c42_everything_else_still_marks(self):
        """42. Repeat check 39 with the note's picture: `Read` a file in `08 Notes/_images/` (change `src` in the stand-in to a picture) → it still marks, and the …"""
        self.named(42)

    def test_c45_the_files_are_up_to_date_with_help_md(self):
        """45. Help (?) → How do I… has **Capture a note**, **Keep notes on a project** and **Turn a note into tracker changes**; Reference has Notes, Capture a …"""
        self.named(45)


class DayLine(HandcheckCase):
    """Check 19, written here: the test the check names covers today only."""

    def test_c19_note_on_any_day(self):
        """19. Move to tomorrow in the day line (]) and back (T) → Note shows on any day's non-private meetings."""
        b = self.b
        b.eval("go('today')")
        b.wait("document.querySelectorAll('#dayMeets .dm').length>0", 15)
        day = "document.getElementById('dayMeets').getAttribute('aria-label')"
        today = b.eval(day)
        self.assertTrue(today, "the day line is drawn (two days in the calendar)")
        sel = "[...document.querySelectorAll('#dayMeets .mnote')].map(x=>x.getAttribute('aria-label'))"
        self.assertEqual(b.eval(sel), ["Note for this meeting: FAL Steering committee"], "today's Note button")
        b.eval("document.activeElement&&document.activeElement.blur(); document.body.focus()")
        b.key("]")
        b.wait(f"{day}!==%r" % today, 10)
        b.pump(0.8)
        self.assertNotEqual(b.eval(day), today, "] moved to the next day")
        tomorrow = b.eval(sel)
        self.assertEqual(tomorrow, ["Note for this meeting: FAL Steering committee"], "tomorrow's Note button")
        b.eval("document.querySelector('#dayMeets .mnote').click()")
        b.wait("!document.getElementById('capDrawer').hidden&&document.getElementById('capTitle').value==='FAL Steering committee'", 10)
        b.key("Escape")
        b.eval("document.activeElement&&document.activeElement.blur(); document.body.focus()")
        b.key("T")
        b.wait(f"{day}===%r" % today, 10)
        self.assertEqual(b.errors, [], "page errors")
        self.note(19, "tomorrow shows the Note button on its meeting and opens the drawer on it; T returns to today (no private meeting tomorrow in the fixture)")


class Screens(HandcheckCase):
    """Check 44: the sheet (desktop and 900 px, two themes), plus the two tests that measure part of it."""

    def test_c44_across_the_screens(self):
        """44. Dark mode, forced colours, two themes, 1400 px and 900 px: the Notes tab, the drawer → on the screenshot sheet;
        the measuring tests pass."""
        SCREENS["notes"] = ("go('notes','FAL')", "!!document.getElementById('notesNew')")
        pals = ("creaite", "Brightwater")
        n = self.sheet(44, "notes", palettes=pals, widths=(1400, 900))

        def drawer(b):
            b.eval("document.activeElement&&document.activeElement.blur(); document.body.focus()")
            b.key("n")
            b.wait("!document.getElementById('capDrawer').hidden", 10)
        n += self.sheet(44, "work", palettes=pals, widths=(1400, 900), prepare=drawer)
        self.assertEqual(self.b.errors, [], "page errors")
        named(self, 44)
        self.note(44, f"{n} shots (Notes tab, capture drawer; 1400 and 900 px; creaite and Brightwater); the AI bar, suggestion and Find updates panel need the stand-in and are by hand")


def _backup_case():
    import test_backups
    return test_backups


@unittest.skipUnless(_backup_case().GIT, "needs git")
class NoteDraftsInTheZip(_backup_case().Case):
    """Check 46, written here: no test named it."""

    def test_c46_backup_zip_holds_note_drafts_not_notes(self):
        """46. The next day's backup zip holds `system/staging/drafts/notes/` and not the notes folder (Alan, 14-10-2026)."""
        import zipfile
        r = self.v.root
        (r / "system/staging/drafts/notes").mkdir(parents=True, exist_ok=True)
        (r / "system/staging/drafts/notes/FAL-draft.json").write_text('{"body": "half a note"}\n')
        for d in (r / "projects/_portfolio/notes", self.root / "ABC Alpha Programme/notes", self.root / "ABC Alpha Programme/08 Notes"):
            d.mkdir(parents=True, exist_ok=True)
            (d / "A filed note.md").write_text("# A filed note\n")
        _backup_case().git(r, "init", "-q")
        _backup_case().git(r, "add", "CLAUDE.md")
        _backup_case().git(r, "commit", "-q", "-m", "first")
        self.start()
        z = self.backups() / "creaite-backup-2026-10-14.zip"
        self.assertTrue(z.is_file(), "the day's zip")
        with zipfile.ZipFile(z) as zf:
            names = zf.namelist()
        self.assertIn("system/staging/drafts/notes/FAL-draft.json", names)
        self.assertFalse([n for n in names if "A filed note" in n or n.endswith(("/notes/", "/08 Notes/"))
                          or "/notes/" in n.replace("system/staging/drafts/notes/", "") or "08 Notes" in n],
                         "a notes folder is in the zip")
        NOTES[46] = "the zip holds system/staging/drafts/notes/ and no filed note, in the vault or the OneDrive stand-in"


if __name__ == "__main__":
    unittest.main()
