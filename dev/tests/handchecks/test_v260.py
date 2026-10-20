"""#212: creaite 2.6.0's hand checks (dev/handchecks/v2.6.0.md, a DRAFT sheet for the Product Manager to replace), automated. Written
before the five items are merged, so every check FEATURE-DETECTS what it needs and SKIPS with the reason when the behaviour is not in
the vault or the checkout: the file runs on any head and nothing fails for code that has not landed.

Run them all, fill the Results table and make the screenshot sheet:  python3 dev/tools/handcheck.py v2.6.0
Run this file on its own (it makes the vault itself, for the direct checks):  python3 dev/tests/handchecks/test_v260.py
Run a check with its feature absent, to see it red:                  CREAITE_HC_260_FORCE=1 python3 dev/tests/handchecks/test_v260.py
Make a FAIL-expected check a failure (the review findings still open):  CREAITE_HC_260_STRICT=1

The five items (board issues in creaite-plan; the branches they are built on, none merged into main when this was written):
  #232 Intake       1 to 21   the combined Intake page: p260-a (the page), p260-b (the update-proposal peek), p260-c (the rename),
                              p260-e (minutes from someone else). Merge them in that order; the generated files are regenerated.
  #236 From rows    22 to 30  followed people's proposals and notes in Today's Needs attention: v26-followed-needs
  #183 Drafts       31 to 42  Create draft in Outlook from the Draft email builder: v26-draft-delivery-fix (the route is a proposal for
                              the guarded live_server.py: dev/proposals/draft-delivery/live_server.diff)
  #241 Work items   43 to 55  marks, compact rows, keys S O P T C V, the Client-visible switch: v26-work-items-abc (D, the history, is
                              v26-work-items-d and waits for a guarded diff)
  #245 Intake line  56 to 63  the quiet Intake line on Today: v252-intake-line

How a check is wired (as test_v240.py): most of the five items have their own tests in dev/tests (the sheet names them under each
check). NAMED below lists, per check, the tests it calls: (file in dev/tests, the test or class names, the branch that brings them).
`run_named` runs them in a fresh process (their own throwaway vault and server, never the live vault, never Microsoft 365, the
stand-in Claude) and the check passes when every one ran and passed, none skipped. A check whose file or test is not in this
checkout yet skips with "waiting for <branch>: <file>::<test>". Nothing is written twice. A few checks are direct: they drive the
hand-check vault (made from the release zip) in the browser or with the vault's own scripts (22, 30, 51, 53; the judgement lines 21, 42, 55 and 63 take screenshots).

Never Microsoft 365: #183's draft in Outlook is Microsoft 365, so 41 is live only; the app side (the request, the checks, the refusal
words, the chase record) is called from the builders' tests, which use no connector. Fictional data only.

FAIL-expected: a check that holds a finding the reviewers raised on the branch's head and that is not fixed yet (49: C against Draft
email; 51: the letter keys act inside a dialog or on a repeat; 53: a damaged saved layout). It skips with the failure's words, as
"FAIL-expected: ...", until the fix lands; CREAITE_HC_260_STRICT=1 makes it a failure; once it passes it is a normal pass.
"""
import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))      # dev/tests
import hcbase
import measure
from hcbase import NOTES, SCREENS, HandcheckCase, db_rows
from test_v240 import resolve, run_named                      # Team Stark's wrapper, as the 2.4.0 checks call it

FORCE = os.environ.get("CREAITE_HC_260_FORCE") == "1"        # run a direct check although its feature is not in the vault
STRICT = os.environ.get("CREAITE_HC_260_STRICT") == "1"      # a FAIL-expected check is a failure

KIND = {**{n: "scriptable" for n in (*range(1, 20), 22, 23, 24, 25, 26, 27, 28, 29, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 43, 44, 45, 46,
                                     47, 48, 49, 50, 51, 52, 53, 54, 56, 57, 58, 59, 60, 61)},
        **{n: "measurable" for n in (62,)},
        **{n: "judgement" for n in (21, 30, 42, 55, 63)}}
# 20 is struck (the Done row's result is deferred to 2.6.1: no kind). 41 is live only (below).
LIVE_ONLY = {41: "Microsoft 365: with the setting on and your Outlook allowing drafts, press Create draft in Outlook and look in "
                 "Outlook's Drafts folder; nothing here may call a connector, so only the app side is scripted (checks 31 to 40)"}

NOTES.clear()
NOTES.update({
    3: "the real Finder drag is live only; the overlay and the drop are scripted",
    17: "PARTIAL: the engine (staging with no draft, the filed copy on approval, the refusal of a transcript) is scripted; how the "
        "real model reads someone else's minutes is live only",
    20: "struck: Q9, deferred to 2.6.1 (the plan's Q9); the locked mockup draws the result, the branch does not",
    31: "the card's words and place are scripted; the real Outlook access is check 41",
    32: "the stand-in answers the access check; a real Check against Microsoft 365 is live only (41)",
    40: "waits for Alan to apply dev/proposals/draft-delivery/live_server.diff (guarded) and move test_draft_route.py to dev/tests",
    41: "live only: Microsoft 365",
    49: "FAIL-expected on 3014848d: C closes the cursor row and takes the key from Draft email (BL-298) whenever the peek is open; "
        "waits for Alan's decision on which binding",
    51: "FAIL-expected on 3014848d (review MEDIUM 2 and 3): the letter keys do not check for an open dialog or menu or for key repeat",
    53: "FAIL-expected on 3014848d (review LOW 4): a wrong-typed value in creaite-listgrp stops the Work page drawing",
    54: "waits for v26-work-items-d (the history) and its guarded route (dev/proposals/work-item-history/live_server.diff)",
    59: "two tabs are scripted by the builder's own test (a second page in the same browser)",
})

# Check number: [(file in dev/tests, [test names or "Class" or "Class.name"], the branch that brings it)]. A bare name means every class
# that defines it; a bare class name means all its tests.
IR = "test_intake_review_"
NAMED = {
    # ── #232 Intake ──
    1: [(IR + "wiring", ["test_go_aliases", "test_old_addresses_and_forms", "test_badge_today_page_and_title_agree", "test_one_palette_entry"],
         "p260-c"),
        (IR + "page", ["test_the_address_and_the_old_ones", "test_one_sidebar_entry"], "p260-c")],
    2: [(IR + "chrome", ["Head"], "p260-a")],
    3: [(IR + "chrome", ["AddFiles"], "p260-a"),
        (IR + "finish", ["test_a_file_dropped_on_the_ask_panel_is_not_also_uploaded", "test_a_drop_something_else_already_took_is_not_uploaded"],
         "p260-a")],
    4: [(IR + "page", ["test_the_three_views_and_the_choice_is_remembered", "test_stage_filter_and_folded_sections"], "p260-a"),
        (IR + "chrome", ["StageBoxes"], "p260-a")],
    5: [(IR + "files", ["test_a_transcript_file_row", "test_a_minutes_file_row", "test_a_file_that_is_not_sure_asks_before_it_can_be_processed",
                        "test_the_switch_changes_the_button_word_and_survives_a_reload", "test_choosing_a_type_makes_the_file_ready_and_counts_it",
                        "test_process_sends_the_command_that_fits_the_kind_and_the_row_says_what_it_is_doing",
                        "test_a_file_already_filed_is_a_done_row_with_remove_and_undo"], "p260-a")],
    6: [(IR + "files", ["test_process_all_ready_skips_private_confidential_and_unsure_and_says_how_many",
                        "test_an_explicit_process_on_a_confidential_row_still_works"], "p260-a"),
        (IR + "intake", ["test_process_all_ready_goes_one_after_another"], "p260-a")],
    7: [(IR + "search", ["Search"], "p260-a")],
    8: [(IR + "rules", ["test_a_confidential_meeting_shows_only_its_title_and_times",
                        "test_a_confidential_meeting_set_aside_keeps_no_project_in_the_lists"], "p260-a"),
        (IR + "finish", ["test_a_row_flagged_confidential_names_no_project_whatever_the_model_carries",
                         "test_a_confidential_meeting_keeps_only_title_and_times_after_a_run_too", "ConfidentialModel"], "p260-a")],
    9: [(IR + "intake", ["test_process_shows_progress_and_ask_stays_free", "test_process_loads_the_transcript_first_and_skips_with_the_reason_on_the_row",
                         "test_the_row_offers_process_later_and_not_needed_only_when_they_apply", "test_age_and_stale_are_on_the_meeting_row"],
         "p260-a"),
        (IR + "finish", ["test_process_called_twice_at_once_starts_one_run", "test_enter_on_a_row_that_is_running_starts_nothing_more",
                         "test_process_does_nothing_while_ask_creaite_is_working", "test_process_does_nothing_while_a_transcript_check_runs",
                         "test_a_waiting_teams_meeting_says_what_the_sweep_found_and_offers_check_again",
                         "test_check_again_looks_the_transcript_up_without_opening_the_ask_panel_and_the_row_turns_ready"], "p260-a")],
    10: [(IR + "intake", ["test_not_needed_asks_reason_then_undo", "test_h_hides_and_transcript_brings_back", "test_uploaded_file_keeps_reason",
                          "IntakeModelA"], "p260-a"),
         (IR + "finish", ["test_the_later_tooltip_tells_the_truth_for_each_kind_of_row", "test_restore_says_file_for_a_file_and_meeting_for_a_meeting"],
          "p260-a")],
    11: [(IR + "intake", ["test_board_process_moves_the_card"], "p260-a"),
         (IR + "files", ["test_the_board_and_two_panes_use_the_same_words"], "p260-a"),
         (IR + "chrome", ["Gaps"], "p260-a")],
    12: [(IR + "routine", ["Routine"], "p250-b")],
    13: [(IR + "mail", ["Mail"], "p250-b"),
         (IR + "update_peek", ["test_the_rows_line_names_the_item_and_says_the_latest_update_in_words"], "p260-b")],
    14: [(IR + "update_peek", ["test_the_whole_item_with_the_changed_fields_marked", "test_the_note_the_chips_and_the_if_approved_line_say_the_same",
                               "test_the_latest_update_shows_the_old_over_the_new_and_edits",
                               "test_a_status_the_item_already_has_is_plain_and_the_note_leaves_it_out"], "p260-b"),
         (IR + "update", ["PureRules.test_changed_is_against_the_live_row"], "p260-b")],
    15: [(IR + "update_peek", ["UpdatePeekSaves"], "p260-b"), (IR + "update", ["ApplyPath"], "p260-b")],
    16: [(IR + "update_peek", ["test_a_conflict_hides_save_and_approve_and_shows_the_two_values", "test_the_target_that_has_gone_falls_back_to_the_old_form",
                               "test_previous_and_next_include_the_updates"], "p260-b"),
         (IR + "peek", ["PeekReadOnly.test_prev_next_step_through_the_proposals", "PeekReadOnly.test_esc_closes_the_peek_first_then_the_meeting"], "p250-b")],
    17: [("test_minutes_by_others", ["StageTests", "Refusals", "ApplyTests"], "p260-e"),
         ("test_minutes_by_others_filing", ["Fixed"], "p260-e")],
    18: [(IR + "keys_intake", ["IntakeKeys"], "p260-a"), (IR + "keys_review", ["KeysReview"], "p250-b")],
    19: [(IR + "rules", ["test_nobody_is_labelled_a_vip_in_any_view", "test_a_project_is_named_never_its_code"], "p260-a"),
         (IR + "rules_proposals", ["ProposalRules"], "p250-b")],
    # ── #236 From rows in Needs attention ── (22 is direct)
    23: [("test_followed_needs", ["Proposals.test_a_memory_note_about_the_message_is_a_row_linking_to_the_note",
                                 "Proposals.test_the_rows_are_pointers_to_review_not_messages_for_the_check_or_the_reports"], "v26-followed-needs")],
    24: [("test_followed_needs", ["Dropped", "Page.test_c_every_unseen_recorded_message_has_a_row"], "v26-followed-needs")],
    25: [("test_followed_needs", ["Dismissed.test_dismiss_removes_the_row_and_keeps_it_in_the_history", "Dismissed.test_a_re_sweep_that_mentions_it_again_changes_nothing",
                                 "Cards.test_a_dismissed_card_stays_dismissed_when_the_thread_only_carries_on", "Page.test_d_dismissed_stays_out_and_in_the_file"],
         "v26-followed-needs")],
    26: [("test_followed_needs", ["Dismissed.test_a_new_risk_or_action_in_the_thread_brings_it_back_as_new",
                                 "Dismissed.test_a_staged_update_of_an_active_item_brings_it_back", "Dismissed.test_a_dismissed_note_stays_gone_when_another_note_follows",
                                 "Dismissed.test_the_returned_row_is_not_stale_after_undo", "Reworded", "Cards.test_a_new_risk_brings_it_back_as_new",
                                 "Cards.test_a_new_ask_of_a_different_kind_brings_it_back", "Dismiss"], "v26-followed-needs")],
    27: [("test_followed_needs", ["PrivateThreads", "Dropped.test_a_private_conversation_still_keeps_its_whole_thread_out",
                                 "Cards.test_a_private_conversation_stays_dismissed", "Page.test_e_a_private_conversation_is_its_title_and_times_only"],
         "v26-followed-needs")],
    28: [("test_followed_needs", ["Page.test_f_the_counts_and_the_badge_include_the_new_rows", "Proposals.test_a_decided_proposal_takes_its_row_away"],
          "v26-followed-needs")],
    29: [("test_followed_needs", ["Proposals.test_the_word_is_nowhere", "Page.test_g_no_label_anywhere_in_the_section"], "v26-followed-needs")],
    # ── #183 Draft email delivery ──
    31: [("test_draft_delivery_popup", ["EssentialsCard.test_the_draft_email_card_is_second_with_its_words_and_off"], "v26-draft-delivery-fix"),
         ("test_draft_delivery", ["SettingAndRequest.test_the_setting_is_off_by_default_and_a_request_is_refused_while_off"], "v26-draft-delivery-fix")],
    32: [("test_draft_delivery_popup", ["EssentialsCard.test_check_says_yes_with_the_time_or_no_and_turns_the_setting_off"], "v26-draft-delivery-fix"),
         ("test_draft_delivery", ["Access"], "v26-draft-delivery-fix")],
    33: [("test_draft_delivery_popup", ["Popup.test_off_is_todays_popup"], "v26-draft-delivery-fix")],
    34: [("test_draft_delivery_popup", ["Popup.test_on_offers_create_draft_first_keeps_the_copies_and_drops_i_sent_it"], "v26-draft-delivery-fix")],
    35: [("test_draft_delivery_popup", ["Popup.test_the_draft_body_is_the_previews_html_and_the_copys_html",
                                       "Popup.test_the_email_is_markup_outlook_takes_in_the_copy_and_the_draft_edited_or_not"], "v26-draft-delivery-fix"),
         ("test_draft_delivery", ["SettingAndRequest.test_the_body_is_the_previews_html_byte_for_byte_with_the_subject_and_to_as_shown", "Markup", "CopiedCommand"],
          "v26-draft-delivery-fix")],
    36: [("test_draft_delivery_popup", ["Popup.test_no_address_on_record_says_so_and_still_offers_the_draft"], "v26-draft-delivery-fix"),
         ("test_draft_delivery", ["SettingAndRequest.test_no_address_on_record_still_makes_the_draft_with_nothing_in_to"], "v26-draft-delivery-fix")],
    37: [("test_draft_delivery_popup", ["Popup.test_after_the_draft_is_made_the_button_reads_draft_created_and_the_chase_is_recorded",
                                       "Popup.test_a_copy_with_the_setting_on_leaves_the_references_for_the_sweep"], "v26-draft-delivery-fix"),
         ("test_draft_delivery", ["ChaseRecords", "SentItems", "SweepStage"], "v26-draft-delivery-fix")],
    38: [("test_draft_delivery_popup", ["Popup.test_a_refusal_keeps_the_email_records_nothing_and_offers_copy_it_instead"], "v26-draft-delivery-fix"),
         ("test_draft_delivery", ["Check"], "v26-draft-delivery-fix")],
    39: [("test_draft_delivery", ["NeverSends", "Access.test_an_injected_cc_bcc_or_changed_subject_or_to_is_never_reported_as_success",
                                 "Access.test_the_check_uses_a_reading_tool"], "v26-draft-delivery-fix")],
    40: [("test_draft_route", ["Route"], "the guarded live_server.diff")],
    # ── #241 Work items ──
    43: [("test_work_items_v2_list", ["test_compact_by_default_comfortable_on_request_row_height_only"], "v26-work-items-abc"),
         ("test_work_density_widths", ["DensityWidths"], "v26-work-items-abc")],
    44: [("test_work_items_v2_list", ["test_status_and_priority_marks_beside_the_columns_with_words", "test_client_visible_items_carry_a_tag"],
          "v26-work-items-abc")],
    45: [("test_work_items_v2_list", ["test_default_grouping_per_tab_where_nothing_is_saved", "test_closed_comes_last_and_keeps_its_rows",
                                      "test_no_grouping_is_kept_as_a_choice_and_reset_returns_to_the_default",
                                      "test_a_saved_grouping_wins_and_a_chosen_order_shows_the_list_in_that_order"], "v26-work-items-abc")],
    46: [("test_work_items_v2_keys", ["test_arrows_move_open_and_close_and_left_opens_the_menu",
                                     "test_a_click_selects_and_opens_only_while_the_peek_is_open_over_the_page"], "v26-work-items-abc")],
    47: [("test_work_items_v2_keys", ["test_s_o_p_t_open_the_cell_editors_on_the_cursor_row", "test_s_uses_the_menu_for_a_hidden_column_and_the_peek_picker_when_open",
                                     "test_a_key_on_a_selection_is_the_bulk_change", "test_decisions_have_no_priority_and_are_not_closed"], "v26-work-items-abc")],
    48: [("test_work_items_v2_keys", ["test_c_closes_the_cursor_row_with_undo"], "v26-work-items-abc")],
    49: [("test_draft_chase_pane", ["TheIcon"], "v26-work-items-abc")],
    50: [("test_work_items_v2_keys", ["test_the_peek_eye_shows_and_switches_client_visible", "test_v_and_the_menu_switch_a_row_with_undo_and_the_tag_follows",
                                     "test_turning_on_without_messaging_opens_the_peek_and_saves_nothing"], "v26-work-items-abc")],
    52: [("test_work_layout_survives", ["LayoutSurvives"], "v26-work-items-abc"), ("test_work_board", ["BoardLayout"], "v26-work-items-abc")],
    54: [("test_item_history", ["Matrix.test_each_field_through_each_route_is_one_event_with_its_before_and_after",
                               "Matrix.test_undo_strikes_each_original_event_and_adds_its_own", "Matrix.test_no_event_carries_message_text"],
          "v26-work-items-d")],
    # ── #245 The Intake line on Today ──
    56: [("test_today_intake_line", ["Shows.test_counts_in_the_locked_wording_with_two_links_and_an_x", "Shows.test_plurals_and_singulars",
                                    "Shows.test_only_one_kind_waiting_has_one_phrase", "Shows.test_new_files_in_intake_are_a_third_phrase",
                                    "Shows.test_it_is_the_last_thing_in_your_commitments", "Shows.test_no_line_when_nothing_waits",
                                    "Shows.test_the_phrases_say_what_the_pages_count"], "v252-intake-line")],
    57: [("test_today_intake_line", ["Links"], "v252-intake-line")],
    58: [("test_today_intake_line", ["Dismiss"], "v252-intake-line")],
    59: [("test_today_intake_line", ["TwoTabs", "Shows.test_the_line_has_no_live_role_and_a_small_hidden_region_announces_the_count_politely",
                                    "Shows.test_a_redraw_with_the_same_count_leaves_the_region_alone_and_a_dismiss_silences_it"], "v252-intake-line")],
    60: [("test_today_intake_line", ["Shows.test_the_section_and_its_fold_are_gone_and_the_page_never_says_intake_and_review",
                                    "Shows.test_no_quick_approve_or_reject_on_todays_rows", "Messages"], "v252-intake-line")],
    61: [("test_today_intake_line", ["Shows.test_confidential_meeting_counts_but_is_never_named", "Shows.test_no_vip_label_and_dates_are_not_us_style"],
          "v252-intake-line")],
    62: [("test_today_intake_line", ["Narrow"], "v252-intake-line")],
}

# Known findings on a branch's head: the check runs and, while the finding stands, skips with these words (STRICT makes it a failure).
EXPECT_FAIL = {
    49: "#241 review HIGH: the new C (close) takes the key from BL-298's C (Draft email) while the peek is open; test_draft_chase_pane fails 2 and "
        "errors 2 on 3014848d. Needs Alan's decision (another binding for close, or yield C to Draft email in the peek)",
}


def plan(n):
    """Check n's named tests: ([(file, ids, branch)], [(token, branch) not in the checkout])."""
    found, missing = [], []
    for file, tokens, branch in NAMED.get(n, []):
        ids, gone = resolve(file, tokens)
        missing += [(g, branch) for g in gone]
        if ids:
            found.append((file, ids, branch))
    return found, missing


class Called(unittest.TestCase):
    """The checks that call the tests they name: no vault, server or Chrome of their own (those tests make their own)."""

    def setUp(self):
        n = int(self._testMethodName[6:8])
        if hcbase.only() and n not in hcbase.only():
            self.skipTest("not in --only")

    def named(self, n):
        """Call check n's named tests: skip while any is not in this checkout, fail if one fails, else pass with a note."""
        found, missing = plan(n)
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
        if failed and n in EXPECT_FAIL and not STRICT:
            self.skipTest(f"FAIL-expected: {EXPECT_FAIL[n]} ({failed[0][:120]}; CREAITE_HC_260_STRICT=1 makes it a failure)")
        self.assertEqual(failed, [], "\n".join(failed))
        NOTES[n] = "; ".join(x for x in (NOTES.get(n), f"{total} existing tests called, all passed: "
                                         + ", ".join(sorted({f for f, _, _ in found}))) if x)[:300]

    # ── #232 Intake ──

    def test_c01_one_sidebar_entry_named_intake(self):
        """1. Sidebar: one entry named "Intake" (tray icon, badge for what waits); there is no separate Review entry; the old addresses
        (#review, #inbox) open Intake; the palette has one entry."""
        self.named(1)

    def test_c02_heading_sub_line_and_refresh(self):
        """2. Intake: the heading is "Intake"; under it "n ready to process · n proposals to approve · Calendar read hh:mm" with a refresh
        icon; the icon reads the calendar again with ask creaite closed, once, and the time moves on."""
        self.named(2)

    def test_c03_add_files_and_the_drop_overlay(self):
        """3. Add files is an icon button; dragging a file over the page shows "Drop to add files" across the whole page; dropping it adds
        a row; dropping on the ask creaite panel does not."""
        self.named(3)

    def test_c04_views_and_stage_boxes(self):
        """4. List, Board and Two panes (the choice is remembered); the boxes Arrived, Drafted, Approved and a fourth, Show all, with icons
        and counts, filter the page."""
        self.named(4)

    def test_c05_file_rows_say_what_they_are(self):
        """5. A file row says what it is and what Process will do (transcript: "Make minutes"; minutes: "Find work items"), with where it
        was added and its size; a file creaite cannot tell offers Transcript and Minutes and cannot be processed until you choose; the
        choice survives a reload; a file already filed is a Done row, "Already processed"."""
        self.named(5)

    def test_c06_process_all_ready_leaves_some_out(self):
        """6. Process all ready (n) leaves out private meetings, confidential meetings and files creaite is not sure of, and says how many it
        left out; Process on one such row still works."""
        self.named(6)

    def test_c07_search(self):
        """7. The Search box filters meetings and files by title and project name, proposals by title, project name and source; Esc clears
        it; the stage counts stay whole; a confidential meeting is found by its title only."""
        self.named(7)

    def test_c08_a_confidential_meeting_shows_title_and_times_only(self):
        """8. A confidential meeting shows only its title and times (no project) in List, Board and Two panes, in the Later and Not needed
        lists, and after it has been processed."""
        self.named(8)

    def test_c09_process_a_meeting(self):
        """9. Process on a ready meeting: the row shows progress and ask creaite stays free; one run at a time (a second Process or Enter
        starts nothing); a meeting with no transcript yet says what the sweep found and offers Check again; a skipped or failed one says why
        on its row."""
        self.named(9)

    def test_c10_later_not_needed_and_restore(self):
        """10. Later, and Not needed with one of four reasons: both can be undone and restored; an uploaded file keeps its reason; the Later
        tooltip tells the truth for each kind of row; Restore says "file" for a file."""
        self.named(10)

    def test_c11_board_and_two_panes_match_the_list(self):
        """11. Board cards and the Two panes list use the same words as the List rows, each row has the icon of what it is, and Two panes
        shows a summary line and the stage track."""
        self.named(11)

    def test_c12_approve_routine(self):
        """12. Approve routine (n) approves only the routine group, in one apply with one Undo, never the group that needs your decision; the
        meeting stays open."""
        self.named(12)

    def test_c13_mail_and_teams_proposals_in_words(self):
        """13. A proposal from mail or Teams says what changes in words: "Closes ABC-A-014: Draft the comms plan · status Open → Closed ·
        Looks done" (a changed latest update as "and the latest update"); a new action or risk names its owner, date or impact; the source
        line has no times."""
        self.named(13)

    def test_c14_the_update_peek_shows_the_whole_item(self):
        """14. An update proposal opens the whole item in the peek with only the fields that change marked "was → now", the note "What
        changes if you approve" saying the same, and the latest update with the old text over the new."""
        self.named(14)

    def test_c15_edit_in_the_update_peek_and_save_and_approve(self):
        """15. Edit the status, due date or latest update in the update peek and press Save and approve: every column you edited is written
        on apply, the others are left alone, and the change log records each."""
        self.named(15)

    def test_c16_conflict_gone_target_and_previous_next(self):
        """16. An update that conflicts with the current value hides Save and approve and shows both values; an update whose item has gone
        falls back to the plain form; Previous and Next step through every proposal, updates included; Esc closes the peek before the
        meeting."""
        self.named(16)

    def test_c17_find_work_items_in_minutes_by_someone_else(self):
        """17. Find work items on a minutes file from someone else: proposed items, no draft minutes; on approval the file is copied into the
        project's minutes folder and leaves the inbox; Undo puts it back; a transcript without a draft is still refused."""
        self.named(17)

    def test_c18_keys(self):
        """18. Keys: Enter processes or opens, N asks for a reason, H sets aside, arrows move, A approves, R opens the reasons; Esc closes the
        peek first."""
        self.named(18)

    def test_c19_the_rules_hold_on_every_row(self):
        """19. On every Intake row: nobody is labelled a VIP, projects are named (never their code), dates are DD-MM-YYYY and the source line
        has no times."""
        self.named(19)

    @unittest.skip("struck: the Done row's result is deferred to 2.6.1 (Q9)")
    def test_c20_a_finished_meeting_says_its_result(self):
        """20. A finished meeting's row says what happened ("5 approved, 1 rejected"). STRUCK: deferred to 2.6.1 (the plan's Q9; the locked
        mockup draws it, the branch does not)."""

    # ── #236 From rows ──

    def test_c23_a_memory_note_from_a_followed_person_is_a_row(self):
        """23. A project-memory note whose source is a followed person's message gets a "From <name>" row in Needs attention that opens
        the note; the rows are pointers (file, item), never message text, in the check or the reports."""
        self.named(23)

    def test_c24_nothing_recorded_is_missed(self):
        """24. A followed person's message the sweep recorded but Today did not list reaches Review and Today: an item the card does not
        list is staged; every unseen recorded message has a row."""
        self.named(24)

    def test_c25_dismiss_stays_gone(self):
        """25. Dismiss a From row: it goes (Undo brings it back), it stays gone after a sweep that only mentions the thread again, and it
        is kept in vip.json."""
        self.named(25)

    def test_c26_it_comes_back_only_for_something_new(self):
        """26. A dismissed row comes back, as new, only when the thread gains a new action or risk or updates an active item; a light
        rewording does not bring it back; a dismissed note never returns."""
        self.named(26)

    def test_c27_a_private_conversation_is_title_and_times(self):
        """27. A private conversation shows its title and times only (no text, no label saying who is followed), with Dismiss as its only
        action; it stays dismissed."""
        self.named(27)

    def test_c28_counts_and_badge(self):
        """28. The Needs attention count and the side bar's badge include the From rows; deciding the proposal takes its row away."""
        self.named(28)

    def test_c29_no_label_anywhere(self):
        """29. No row, count or tip in Needs attention says who is followed (the word is nowhere)."""
        self.named(29)

    # ── #183 Draft email delivery ──

    def test_c31_the_draft_email_card_in_settings(self):
        """31. Settings › Essentials has a "Draft email" card, second, with the switch to create drafts in Outlook, off by default, and its
        words; with the switch off a request to make a draft is refused and nothing is made."""
        self.named(31)

    def test_c32_the_outlook_access_check(self):
        """32. The card's Check says yes with the time when Outlook allows drafts, or no and turns the switch off; read-only access, a
        refusal or no answer never count as yes."""
        self.named(32)

    def test_c33_off_is_todays_popup(self):
        """33. With the switch off the Draft email popup is as today: Copy buttons and "I sent it"."""
        self.named(33)

    def test_c34_on_offers_create_draft(self):
        """34. With the switch on the popup offers "Create draft in Outlook" first, keeps the copy buttons and has no "I sent it"."""
        self.named(34)

    def test_c35_the_draft_is_the_previews_email(self):
        """35. The draft body is today's email exactly as the preview and the copy show it (same HTML, subject and To), in markup Outlook
        takes (no span, class, style tag or script); an edited email is made as edited."""
        self.named(35)

    def test_c36_no_address_on_record(self):
        """36. A person with no stored email still gets the Outlook draft, with nothing in To, and the popup says so."""
        self.named(36)

    def test_c37_the_chase_is_recorded_without_i_sent_it(self):
        """37. After the draft is made the button reads "Draft created" with a link, the chase is recorded without "I sent it", and the next
        sweep marks it sent once Sent Items shows the mail (a different subject, recipient or time does not match)."""
        self.named(37)

    def test_c38_a_refusal_keeps_the_email(self):
        """38. If Outlook will not make the draft the email is kept, nothing is recorded, and the popup offers Copy it instead; a result
        with other arguments or another tool is never reported as made."""
        self.named(38)

    def test_c39_only_a_draft_is_ever_made(self):
        """39. Only a draft is ever made: every send, update and delete tool is refused by name, the run reads no mail, Teams or files, an
        added Cc or Bcc or a changed subject or To is refused, and no code names a send tool."""
        self.named(39)

    def test_c40_the_servers_own_route(self):
        """40. The live server's own, token-checked route makes the draft (never ask creaite): a copy is never refused for its markup, a draft
        is; one run at a time; the run starts outside the vault. Waits for the guarded live_server.diff."""
        self.named(40)

    # ── #241 Work items ──

    def test_c43_compact_rows_and_comfortable(self):
        """43. Work: rows are one line (the ID beside the title) by default; Comfortable, from the icons beside the list and board switch,
        gives the two-line row; only the row height changes, never a column width, and never the Board."""
        self.named(43)

    def test_c44_marks_and_the_client_tag(self):
        """44. Status and priority show as marks beside the Status and Priority columns (which stay in Display with their width and
        visibility), with words for screen readers; a client-visible item carries a tag."""
        self.named(44)

    def test_c45_grouping(self):
        """45. Where nothing is saved: Actions are grouped by due (Overdue, This week, Next week, Later, No date, Closed folded last), RAID
        by priority, Decisions Pending then Made; "No grouping" is kept as a choice; a saved grouping wins."""
        self.named(45)

    def test_c46_cursor_peek_and_click(self):
        """46. Arrows move the cursor row; Right, Enter or a double click opens the peek, Left closes it (or opens the menu when no peek is
        open); a click selects, and opens another row only while the peek is open."""
        self.named(46)

    def test_c47_s_o_p_t(self):
        """47. S, O, P and T open the status, owner, priority and due editors on the cursor row (the menu when the column is hidden, the
        peek's picker when it is open); on a selection they are the bulk change; a decision has no priority and is not closed."""
        self.named(47)

    def test_c48_c_closes_the_cursor_row(self):
        """48. C closes the cursor row, with Undo."""
        self.named(48)

    def test_c49_c_and_draft_email_in_the_peek(self):
        """49. With the peek open on an open action, C still opens Draft email (BL-298), and the shortcut table says what C does.
        FAIL-expected on 3014848d: the new C takes the key; waits for Alan's decision."""
        self.named(49)

    def test_c50_the_client_visible_switch(self):
        """50. The eye in the peek bar (key V, and the right-click menu) switches Client-visible: on or off at a glance, a badge beside the
        ID, a tag in the list, an Undo toast; default off; turning it on without a client message opens the peek and saves nothing."""
        self.named(50)

    def test_c52_saved_layout_survives(self):
        """52. A saved layout survives the update and a reload: every saved Work key comes back identical, a list column's width, order and
        visibility, and a board column's collapse; the Board and its tests are unchanged."""
        self.named(52)

    def test_c54_the_complete_history(self):
        """54. The peek's Activity lists every change to the item (every field, through every route, undo included), newest first, as "who, via
        where, what, when", with no message text. Waits for #241 D and its guarded route."""
        self.named(54)

    # ── #245 The Intake line on Today ──

    def test_c56_the_line_and_its_wording(self):
        """56. Today: one quiet line at the foot of Your commitments, "Intake: 3 meetings ready to process, 2 proposals to approve and 1 new
        file to process." (singular and plural right, a part left out at zero), none when nothing waits."""
        self.named(56)

    def test_c57_the_links(self):
        """57. Each phrase is a link to the page it names (meetings and files open Intake; proposals open Intake once #232 joins the pages,
        Review before it), by click and by Enter, in Tab order meetings, proposals, files, then the x."""
        self.named(57)

    def test_c58_the_x_hides_it_until_something_new(self):
        """58. The x ("Dismiss until something new arrives") hides the line, and it stays hidden across a redraw, leaving Today and coming
        back, and a reload; it returns when a count rises (a proposal, a meeting or a file) and the next morning; fewer waiting stays
        hidden."""
        self.named(58)

    def test_c59_per_browser_and_announced_politely(self):
        """59. The dismissal is kept per browser and read by another tab at once; the count is announced politely, and a redraw with the same
        count says nothing."""
        self.named(59)

    def test_c60_messages_section_and_no_quick_approve(self):
        """60. Today has no "Intake and Review" section or fold; the followed people's message cards keep a section of their own,
        "Messages", hidden when empty; Today's rows have no quick Approve or Reject."""
        self.named(60)

    def test_c61_confidential_is_counted_not_named(self):
        """61. A confidential meeting is counted but never named in the line; no VIP wording; dates DD-MM-YYYY."""
        self.named(61)

    def test_c62_at_900_px(self):
        """62. At 900 px the line is one or two lines, never a list, and nothing scrolls sideways."""
        self.named(62)


# ══ direct checks: the hand-check vault, made from the release zip ═══════════════════════════════════════════════════════════════

SCREENS.update({
    "intake-page": ("go('intake-review')", "!!document.querySelector('#v-intake-review h1')"),
    "settings-draft-email": ("go('settings','essentials')", "!!document.querySelector('#set-essentials .srow')"),
})


class Direct(HandcheckCase):
    """What the direct checks share: the vault's text (feature detection) and the vault's own scripts."""

    def vtext(self, rel):
        p = self.vault / rel
        return p.read_text(encoding="utf-8", errors="ignore") if p.exists() else ""

    def need(self, present, what):
        if not present and not FORCE:
            self.skipTest(f"{what} is not in this vault yet; this check runs once it is merged (CREAITE_HC_260_FORCE=1 runs it anyway)")


class From236(Direct):
    """Checks 22 and 30 (#236): a sweep stages a proposal from a followed person's email; Today's Needs attention gets a "From <name>"
    row for it. A vault of its own (the check stages a proposal)."""
    own_vault = True
    WHO = "Rashid Al Suwaidi"
    ADDRESS = "rashid@northgate.example"
    SUBJECT = "Sign-off for the Falcon cut-over plan"
    TITLE = "Confirm the cut-over plan sign-off with the sponsor"

    @property
    def fix236(self):
        return "def followed_sync" in self.vtext("system/scripts/sweep.py")

    def stage_from_followed(self):
        """sweep.py stage with one action whose source is an email from the followed sponsor (what the sweep does), once."""
        if getattr(type(self), "_staged", False):
            return
        spec = {"window": {"start": "2026-10-19 08:00", "end": self.now},
                "items": [{"table": "actions", "match": "strong", "values": {
                    "project": "FAL", "description": self.TITLE, "owner": "Sara Khan",
                    "source": f"Email · From: {self.WHO} <{self.ADDRESS}> · Subject: {self.SUBJECT} · Sent: 2026-10-19 16:20 · "
                              "Link: https://outlook.example/mail/handcheck-236"}}]}
        f = self.vault / "system/staging/drafts/hc-sweep.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(spec), encoding="utf-8")
        code, out = self.run_in_vault("sweep.py", "stage", "system/staging/drafts/hc-sweep.json")
        self.assertEqual(code, 0, out)
        code, out = self.run_in_vault("build_dashboard.py")
        self.assertEqual(code, 0, out)
        type(self)._staged = True

    def rows(self):
        b = self.b
        b.reload("typeof go==='function' && LIVE")
        b.eval("go('today'); EXPAND.add('attn'); renderToday()")
        b.wait("document.querySelector('#attnList > li.alrow')", 20)
        b.pump(0.6)
        return b.eval(r"""[...document.querySelectorAll('#attnList > li.alrow')].map(l=>({al:l.dataset.al,
          text:l.textContent.replace(/\s+/g,' ').trim().replace(/^\d+(?=\D)/,''), btns:[...l.querySelectorAll('button')].map(x=>x.getAttribute('aria-label')||''),
          link:(l.querySelector('a.t')||{}).textContent||''}))""")

    def test_c22_a_followed_persons_proposal_is_a_from_row_in_needs_attention(self):
        """22. After a sweep stages a proposal from a followed person's email, Today › Needs attention has a "From <name>" row for it that
        opens the proposal; Review still holds the proposal; Dismiss is on the row."""
        self.need(self.fix236, "#236 (v26-followed-needs)")
        self.stage_from_followed()
        rows = [r for r in self.rows() if r["text"].startswith(f"From {self.WHO}")]
        self.assertTrue(rows, "no From row for the followed person in Needs attention")
        row = rows[0]
        self.assertIn("proposal", row["text"])
        self.assertTrue(any(x.startswith("Open in") for x in row["btns"]) or row["link"], row)
        self.assertTrue(any(x.startswith("Dismiss") for x in row["btns"]), row["btns"])
        pending = hcbase.pending_proposals(self.vault)
        self.assertTrue(pending, "the proposal is still pending (Review holds it)")
        self.assertIn(self.TITLE, " ".join((self.vault / "system/staging" / p).read_text() for p in pending))
        self.note(22, f"row: {row['text'][:90]}")

    def test_c30_from_rows_look(self):
        """30. The From rows read cleanly in Needs attention: the name, what is waiting and where it goes, Open and Dismiss, light and
        dark, 1400 and 900 px (judgement, on the screenshot sheet)."""
        self.need(self.fix236, "#236 (v26-followed-needs)")
        self.stage_from_followed()
        self.rows()
        self.assertGreaterEqual(self.sheet(30, "today"), 0)


class Judgement(Direct):
    """Checks 21, 42, 55 and 63: how the new screens look. The shared vault; the screenshots go on the sheet (judgement, never Pass or
    Fail) and a check passes once they are taken. Each skips until its feature is in the vault."""

    def test_c21_intake_look(self):
        """21. Intake reads cleanly in List, Board and Two panes: the heading and sub-line, the Add files icon, the stage boxes with their
        icons and the Show all box, the file and meeting rows, and the update peek, in light and dark, both palettes, 1400 and 900 px
        (judgement, on the screenshot sheet)."""
        self.need("v-intake-review" in self.vtext("dashboard.html"), "#232 (p260-a, the Intake page)")
        self.assertGreaterEqual(self.sheet(21, "intake-page"), 0)

    def test_c42_draft_email_look(self):
        """42. The Draft email card in Settings › Essentials and the popup's Create draft in Outlook read as the locked mockup
        (dev/mockups/draft-delivery-mockup.html) shows them, light and dark, 1400 and 900 px (judgement, on the screenshot sheet)."""
        self.need("outlook_drafts" in self.vtext("dashboard.html") + self.vtext("system/config/settings.json"), "#183 (v26-draft-delivery-fix)")
        self.assertGreaterEqual(self.sheet(42, "settings-draft-email"), 0)

    def test_c55_work_list_look(self):
        """55. The Work list in Compact and in Comfortable: the marks, the tags, the client-visible badge, the density icons beside the list
        and board switch, the open peek with its eye, light and dark, 1400 and 900 px (judgement, on the screenshot sheet)."""
        self.need("creaite-density" in self.vtext("dashboard.html"), "#241 (v26-work-items-abc)")
        self.assertGreaterEqual(self.sheet(55, "work"), 0)

    def test_c63_intake_line_look(self):
        """63. The Intake line on Today is quiet: muted, at the foot of Your commitments, the x at the right edge without crowding the
        links, a focus ring from the keyboard, light and dark, 1400 and 900 px (judgement, on the screenshot sheet)."""
        self.need("tdQuiet" in self.vtext("dashboard.html"), "#245 (v252-intake-line)")
        self.assertGreaterEqual(self.sheet(63, "today"), 0)


class Work241(Direct):
    """Checks 51 and 53 (#241): findings the reviewers raised on the branch's head, driven on the hand-check vault's Work page. They
    are FAIL-expected until the fix lands (they skip with the failure's words; CREAITE_HC_260_STRICT=1 makes them failures)."""
    WHY51 = ("the letter keys (S O P T C V) act while a dialog or menu is open and on a held key's repeats (#241 review MEDIUM 2 and 3: "
             "only the arrows check wkArrowOK / dialog[open]; no e.repeat guard)")
    WHY53 = "a wrong-typed value in creaite-listgrp stops Work drawing: listGroupDefault does `in WLGRP` on a primitive (#241 review LOW 4)"

    @property
    def fix241(self):
        return "creaite-density" in self.vtext("dashboard.html")

    def expect_fail(self, why, fn):
        """Run `fn`; a failure while the finding stands skips with its words (FAIL-expected), a failure under STRICT fails."""
        try:
            fn()
        except (AssertionError, RuntimeError) as e:
            if STRICT:
                raise
            self.skipTest(f"FAIL-expected: {why}: {str(e)[:160]} (CREAITE_HC_260_STRICT=1 makes it a failure)")

    def open_work(self):
        b = self.b
        b.eval("localStorage.clear()")
        b.reload("typeof go==='function' && LIVE")
        b.eval("go('work')")
        b.wait("document.querySelector('#workTbl tbody tr[data-row]')", 20)
        b.eval("WLGRP[WT]='none'; renderWork()")
        b.wait("document.querySelector('#workTbl tbody tr[data-row]')", 20)
        b.eval("document.activeElement&&document.activeElement.blur()")
        return b

    def open_ids(self):
        return self.b.eval("[...document.querySelectorAll('#workTbl tbody tr[data-row]')].map(r=>r.dataset.row)")

    def status(self, id_):
        return self.b.eval(f"REC('actions',{id_!r}).st")

    def test_c51_letter_keys_leave_a_dialog_alone_and_act_once(self):
        """51. While a dialog or a menu is open the letter keys (S, O, P, T, C, V) do nothing to the cursor row, and a held key acts once, not
        on every repeat."""
        self.need(self.fix241, "#241 (v26-work-items-abc)")
        b = self.open_work()
        ids = [i for i in self.open_ids() if self.status(i) == "Open"]
        self.assertTrue(ids, "premise: an open action on the Work list")
        first = ids[0]

        def run():
            b.key("ArrowDown")
            while b.eval("HLC") != first:
                b.key("ArrowDown")
            # a held key: repeats (autoRepeat) act on nothing; only the first press does
            b.call("Input.dispatchKeyEvent", type="keyDown", key="c", code="KeyC", windowsVirtualKeyCode=67, autoRepeat=True)
            b.call("Input.dispatchKeyEvent", type="keyUp", key="c", code="KeyC", windowsVirtualKeyCode=67)
            b.pump(1.0)
            self.assertEqual(self.status(first), "Open", "a repeat of C closed the cursor row")
            # a modal dialog is open: C does nothing to the row behind it
            b.eval("document.getElementById('boardDlg').showModal()")
            b.pump(0.2)
            b.call("Input.dispatchKeyEvent", type="keyDown", key="c", code="KeyC", windowsVirtualKeyCode=67)
            b.call("Input.dispatchKeyEvent", type="keyUp", key="c", code="KeyC", windowsVirtualKeyCode=67)
            b.pump(1.0)
            b.eval("document.getElementById('boardDlg').close()")
            self.assertEqual(self.status(first), "Open", "C closed the cursor row behind an open dialog")
        self.expect_fail(self.WHY51, run)

    def test_c53_a_damaged_saved_layout_does_not_stop_work(self):
        """53. A damaged saved layout (a wrong kind of value kept in this browser) never stops Work from drawing: the page falls back to its
        defaults."""
        self.need(self.fix241, "#241 (v26-work-items-abc)")
        b = self.b

        def run():
            for key, value in (("creaite-listgrp", '"x"'), ("creaite-listgrp", "5"), ("creaite-listgrp", "true"), ("creaite-density", "{}")):
                b.eval("localStorage.clear()")
                b.eval(f"localStorage.setItem({key!r}, {value!r})")
                b.reload("typeof go==='function' && LIVE")
                try:
                    b.eval("go('work')")
                    b.wait("document.querySelector('#workTbl tbody tr[data-row]')", 12)
                except (TimeoutError, RuntimeError):
                    self.fail(f"Work does not draw with {key} = {value}")
        self.expect_fail(self.WHY53, run)
        b.eval("localStorage.clear()")


if __name__ == "__main__":
    unittest.main()
