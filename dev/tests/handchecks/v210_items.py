"""creaite 2.1.0's hand checks beyond the reporting set (checks 75 on): one row per user-visible change or hardening step.

The single source for dev/handchecks/v2.1.0.md's second half and for test_v210.py's `Items` class: `python3 dev/tests/handchecks/v210_items.py`
prints the Markdown (checks, landing table, Results rows). Update a row's `branch`/`probes` here, and rerun the file.

A row is on main when every one of its `probes` is true on this checkout: a probe is `(test file, test name)` (the test exists), or
`("absent", test file, text)` (the text has gone from that file). Until then the check is an EXPECTED SKIP naming the branch; once the
branch is merged the same row runs its `tests` (each test file in its own process: they must all pass, none skipped).
`tests` empty and `branch` "none" = not built yet (no branch exists): an expected skip with no tests.

kind: scriptable | judgement | live only. `note` adds "test only" for the hardening rows (nothing to see, only a test to run).
Desktop (1400 px) and 900 px only.
"""

ITEMS = [
    # ── v2.0.0 polish and the nine small UX items ────────────────────────────
    dict(n=75, issue="#98", title="Two more toggles in forced colours", branch="ux-98-forced-colours-toggles", kind="scriptable",
         do="Turn on forced colours (DevTools › Rendering › Emulate CSS forced-colors: active). Open an item's peek and a milestone's peek.",
         see="The item peek's Client-visible switch and a milestone's Visible to client switch each show a track and a thumb, and on differs from off; outside forced colours they look as before.",
         tests=["test_forced_colours_toggles.py"], probes=[("test_forced_colours_toggles.py", "test_the_switches_are_visible_and_differ_on_and_off_in_forced_colours")]),
    dict(n=76, issue="v2.0.0 polish A", title="The AI bar's menu stays on screen; the Confidential switch in forced colours", branch="v200-polish-a", kind="scriptable",
         do="In a note, select a line near the bottom of a short window and open the AI bar's menu. Then turn on forced colours and open the capture drawer.",
         see="The menu opens upward when there is more room above and every item is reachable at 900 px; the drawer's Confidential switch keeps a visible track and thumb, on and off.",
         tests=["test_v200_polish_a.py"], probes=[("test_v200_polish_a.py", "test_the_menu_stays_in_a_short_window_and_every_item_is_reachable")]),
    dict(n=77, issue="v2.0.0 polish B", title="The AI bar and the run badge stay out of the way", branch="v200-polish-b", kind="scriptable",
         do="Select text in a note; open Find updates; run something that leaves the run badge up.",
         see="The AI bar sits above the selection, so it no longer hides the next line; opening Find updates takes the bar down; a finished run badge rises clear of Apply.",
         tests=["test_v200_polish_b.py"], probes=[("test_v200_polish_b.py", "test_the_run_badge_never_covers_apply_in_find_updates")]),
    dict(n=78, issue="#101", title="⌘↵ saves in every dialog", branch="ux-101-cmd-enter-dialogs", kind="scriptable",
         do="Open any dialog (a new action, a milestone, a board, a label) and press ⌘↵ (Ctrl+Enter).",
         see="The dialog's main button is pressed; nothing happens in a dialog that is opted out, with a required field empty, with the button disabled, in the middle of composing text or on plain Enter; Esc still closes.",
         tests=["test_dialog_cmd_enter.py"], probes=[("test_dialog_cmd_enter.py", "test_every_dialog_is_listed")]),
    dict(n=79, issue="#102", title="Show changed only is gone from Settings", branch="ux-102-show-changed", kind="scriptable",
         do="Open Settings › Essentials and Advanced.",
         see="There is no Show changed only control; Reset on an older card still works.",
         tests=["test_settings_calmer.py"], probes=[("test_settings_calmer.py", "test_reset_on_an_older_card_and_no_show_changed_only")]),
    dict(n=80, issue="#104", title="One line leaves Today", branch="ux-104-today-line", kind="scriptable",
         do="Open Today and look under Week ahead.",
         see="The note \"Urgent work, every milestone and decision, and meetings\" is gone.",
         tests=["test_today_home.py", "test_today_brief.py"],
         probes=[("absent", "test_today_home.py", "Urgent work, every milestone and decision, and meetings")]),
    dict(n=81, issue="#105", title="Week ahead can be hidden", branch="ux-105-week-ahead-toggle", kind="scriptable",
         do="On Today, click the Week ahead heading, then reload.",
         see="It folds like Resolved (same heading and chevron), is open until you hide it, and the choice is remembered in this browser.",
         tests=["test_today_home.py", "test_today_brief.py"], probes=[("test_today_home.py", "test_the_week_ahead_folds_like_resolved_and_is_remembered")]),
    dict(n=82, issue="#106", title="The action peek's Latest update grows", branch="ux-106-latest-update-multiline", kind="scriptable",
         do="Open an action's peek and type or paste several lines into Latest update.",
         see="The field grows with its text up to 60% of the window, then scrolls inside; the full text is saved; the drag handle and a dragged height are kept.",
         tests=["test_autosize_fields.py"], probes=[("test_autosize_fields.py", "test_peek_latest_update_grows_then_scrolls_and_saves_the_full_text")]),
    dict(n=83, issue="#107", title="Top risks and issues: two lines of resolution action", branch="ux-107-risks-two-lines", kind="scriptable",
         do="On Today, find a risk with a long resolution action.",
         see="Two lines show, cut cleanly, not five.",
         tests=["test_milestone_words.py"], probes=[("test_milestone_words.py", "test_long_text_is_cut_at_two_lines")]),
    dict(n=84, issue="#108", title="After Esc or a click outside, nothing stays highlighted", branch="ux-108-esc-highlight", kind="scriptable",
         do="Open a peek from a Today panel and from a Work row; press Esc; click outside; tick rows on Work and press Esc or click outside.",
         see="No panel or row stays highlighted; Esc and a click outside also clear a bulk selection (the bulk bar and a row tick keep it).",
         tests=["test_peek_esc_highlight.py", "test_row_selection.py"], probes=[("test_peek_esc_highlight.py", "test_a_click_outside_clears_a_bulk_selection")]),
    dict(n=85, issue="#109", title="The health form sits over the page", branch="ux-109-health-peek-overlay", kind="scriptable",
         do="On a project's cockpit, click the pencil on the health.",
         see="The form opens over the page like the other peeks, without squashing it; focus returns to the pencil.",
         tests=["test_health_peek_overlay.py"], probes=[("test_health_peek_overlay.py", "test_other_forms_keep_their_place")]),
    dict(n=86, issue="#113", title="Today at 80% width", branch="ux-113-today-80", kind="scriptable",
         do="Open Today at 1400 px and 900 px.",
         see="The page content is 80% wide and centred; the coloured band stays full width.",
         tests=["test_today_home.py"], probes=[("test_today_home.py", "test_the_headers_content_is_80_percent_centred_and_the_band_full_width_at_1400_and_900")]),
    dict(n=87, issue="#114", title="Review's multi-select bar floats", branch="review-114-floating-toolbar", kind="scriptable",
         do="On Review, select a row far down a long list and scroll to the end.",
         see="The bar sits at the bottom edge of the window, centred in the column, always in view; the last row can scroll clear of it; nothing moves when it appears or goes; toasts sit above it; it re-docks when the sidebar or ask creaite panel resizes; Approve still skips minutes, new decisions and new risks.",
         tests=["test_review_floating_bar.py"], probes=[("test_review_floating_bar.py", "test_desktop")]),
    # ── Notes ────────────────────────────────────────────────────────────────
    dict(n=88, issue="#115", title="Notes header, + Tags and the date reader", branch="notes-115-header-focus", kind="scriptable",
         do="Open a note. Check the header; type \"last monday\" in the date box, then pick a day with the keyboard; add, rename and remove tags.",
         see="+ New note is Work's tile; the list's collapse control is a quiet chevron at the right; Find updates and ... sit on the title row with no wrap; one property line holds Created, Date and With; the date box shows \"Reads as …\" before Enter and keeps the old date for text it cannot read; the pop-up opens on a click, typing or Down (not on focus alone), is not clipped at 900 px, and Esc closes it without reopening; tags add, rename (Enter, Esc cancels) and remove without duplicates (60 characters, 20 tags).",
         tests=["test_notes_header.py", "test_notes_tab.py"], probes=[("test_notes_header.py", "test_the_header_is_tidy_at_1400_and_900")]),
    dict(n=89, issue="#115", title="Notes focus mode", branch="none", kind="judgement", sheet=["notes"],
         do="Open a note and enter focus mode (the design is in the issue). Leave with Esc, a click outside and the leave icon.",
         see="Only the note is drawn; leaving flushes the save first. Not built yet: no branch has focus mode.",
         tests=[], probes=[]),
    dict(n=90, issue="#124", title="Delete note", branch="notes-124-delete-note", kind="scriptable",
         do="In a note's ... menu choose Delete note…, confirm, then Approve the one card; then Undo from the toast; then restore it from Files › Archived.",
         see="The confirm box says it moves to this project archive and links show missing until it is restored; the card is the only thing that moves it (Decline leaves it); the note closes, the list updates and the toast says \"Moved … to the archive\" with Undo; the note is read-only while the card waits; a name taken in the archive gets a number; never while ask creaite has read outside content.",
         tests=["test_notes_delete.py", "test_notes_delete_browser.py"], probes=[("test_notes_delete.py", "test_a_one_card_reject_moves_nothing_approve_moves_undo_restores")]),
    dict(n=91, issue="#119 (server half)", title="Autosave keeps one backup per editing session", branch="notes-autosave-server-drafts", kind="scriptable",
         do="Edit a note, pausing for about two seconds several times; then Undo the change in What ask creaite changed.",
         see="Several saves in one editing session make one backup (a new one after five minutes idle, another file or a change in between) and one log line each; Undo takes the whole session back in one step; a change approved on the card, a settings file or a save in a marked run is never joined; no draft step is left.",
         tests=["test_notes_autosave_backups.py", "test_notes_tab.py", "test_notes_gaps.py"], probes=[("test_notes_autosave_backups.py", "test_n_saves_in_one_session_make_one_backup_and_n_log_lines")]),
    dict(n=92, issue="#119 (page half)", title="Notes save line: Editing, then Saved", branch="none", kind="scriptable",
         do="Type in a note and stop.",
         see="The save line reads \"Editing\", then \"Saved 14:02\" about two seconds after the last key; no \"Draft kept\", no recovery prompt; saves on leaving, switching and closing. Not built yet (it follows #115 and the server half).",
         tests=[], probes=[]),
    # ── The Generate current state dialog ────────────────────────────────────
    dict(n=93, issue="#110 A", title="The redesigned Generate current state dialog", branch="current-state-dialog", kind="scriptable",
         do="On a project's cockpit open Generate current state. Try the fields, Draw on, Client-safe, ⌘↵, then Generate and Change settings.",
         see="736 px wide at desktop and at 900 px with nothing overflowing and the footer in view even in a short window; four quiet fields with their defaults and one hint line; Steer it is full width and resizable; starters add a sentence and never send; Draw on folds to one line; Client-safe reads client-visible items only; while writing the setup folds to one line; Change settings drops the draft; ⌘↵ generates here and a typed date is read first.",
         tests=["test_generate_dialog.py", "test_drafts_forms.py", "test_status_live_browser.py"], probes=[("test_generate_dialog.py", "test_it_is_736px_wide_at_desktop_and_at_900px_and_nothing_overflows")]),
    dict(n=94, issue="#110 B", title="Steer it further", branch="current-state-refine", kind="scriptable",
         do="After a draft appears, use Steer it further with a starter and with your own words.",
         see="The box appears under every form's result and not before; asking with nothing typed sends nothing; version 2 is written from the same facts, the previous version and the change; hand edits and sources are kept per version.",
         tests=["test_generate_refine.py", "test_generate_dialog.py"], probes=[("test_generate_refine.py", "test_refine_with_nothing_typed_asks_for_the_change_and_sends_nothing")]),
    # ── ✦ on the sheets and the editors ──────────────────────────────────────
    dict(n=95, issue="#90", title="✦ on the weekly and minutes sheets", branch="v210-star-fix", kind="scriptable",
         do="On the weekly report and the minutes view press ✦ on a section (Polish, Shorter, Executive, Custom); accept one, dismiss one; reorder sections and press ✦ again.",
         see="A suggestion changes nothing until you accept it and lands on the section you asked for after a reorder; its checks and \"No source\" marks show; a client draft never sees the internal health or its reason, nor any Sensitive, partner-only or not client-visible item; counts only, never text; there is no ✦ bar on the client sheet until #123. Check 11 and the wording check 72 rest on this.",
         tests=["test_drafts_report.py", "test_drafts_report_route.py", "test_redraft_reorder.py", "test_client_leak.py"],
         probes=[("test_drafts_report.py", "test_the_internal_health_and_its_reason_never_reach_a_client_draft")]),
    dict(n=96, issue="#123", title="The client sheet's AI sends client-visible items only", branch="none", kind="scriptable",
         do="Press the AI on the client report's sheet; look at the # picker and chips.",
         see="The AI is given client-visible items only; the picker and chips show client-visible items only (or are off). Must land before v2.1.0 ships. Not built yet.",
         tests=[], probes=[]),
    dict(n=97, issue="#122", title="One editor everywhere: the shared foundation", branch="none", kind="judgement", sheet=[],
         do="Open an editor in Notes, Current state and a report sheet.",
         see="The same toolbar, checklist, / menu and headings (1 to 3) in every editor with its profile. Not built yet.",
         tests=[], probes=[]),
    dict(n=98, issue="#117 #118 #120", title="Margin sparkle, hover bar, aligned checklist, links", branch="none", kind="judgement", sheet=[],
         do="In any editor use the margin sparkle, the grouped hover bar, Turn into, the / menu and a Link (http, https and mailto only).",
         see="As designed on the issues. Not built yet: no branches. v2.2.0 may take the plain-field links (#121).",
         tests=[], probes=[]),
    # ── The VIP thread cards (BL-342 Part 3 B) ───────────────────────────────
    dict(n=99, issue="BL-342 Part 3 B", title="VIP thread cards: type, ask, due, owners and the match", branch="bl342-part3b-v3", kind="scriptable",
         do="Record sample conversations (sweep.py vip record, the hand-check helper), then on Today log, mark Handled, Dismiss, Chase and Undo.",
         see="Each card names its type, ask, due date, owners and the matched open action; two threads on one item show two cards and a count; Log stages one pending update; a new message in the same thread is the same card; Handled and Dismiss update the other cards' chips and Undo brings them back; Chase opens the Draft email builder in Chase mode for the owner; \"Looks done: close <ID>\" is a pending status change only and never applies.",
         tests=["test_vip_matching.py", "test_vip_threads.py", "test_vip_screens.py", "test_alert_actions.py", "test_sweep_alerts.py", "test_vip_single_call.py"],
         probes=[("test_vip_matching.py", "test_a_named_open_id_gives_update_and_nothing_similar_gives_new")]),
    dict(n=100, issue="BL-342 Part 3 B", title="VIP cards: private, confidential and client-safe", branch="bl342-part3b-v3", kind="scriptable",
         do="Run the confidentiality tests; look at a confidential and a private card.",
         see="A confidential card keeps only neutral words (no subject, no summary); a private thread has no match; nothing reaches a client report, the one-pager or the database; no card, route, field or logged update ever says the word VIP.",
         tests=["test_vip_confidential.py", "test_vip_private.py"], probes=[("test_vip_private.py", "test_the_card_the_page_data_the_routes_and_the_logged_update_never_say_vip")]),
    dict(n=101, issue="BL-342 Part 3 B", title="The VIP probe on laptop 1 (one real Microsoft 365 call)", branch="bl342-part3b-v3", kind="live only",
         live="needs one real Microsoft 365 call on laptop 1 (Team Cap): the VIP check, with no --tools flag and every built-in denied by name, must still read mail and Teams and answer; no test may call Microsoft 365",
         do="On laptop 1, in the live vault, press the VIP check once (or wait for vip.check_minutes).",
         see="The check completes, reads real mail and Teams, and records references and a gist; the debug log shows no tool refusal.",
         tests=[], probes=[]),
    # ── The hardening (#116) ─────────────────────────────────────────────────
    dict(n=102, issue="#116 A, A2", title="VIP check and the search answer: no built-in tools", branch="main", kind="scriptable",
         do="Run the pins (no model, no Microsoft 365).",
         see="The VIP check runs with no built-in tools (every one denied by name, ToolSearch allowed); the search answer has Read, Grep and Glob only, the Microsoft 365 reading tools denied, and --strict-mcp-config.",
         tests=["test_vip_tools_pinned.py", "test_search_tools_pinned.py"], probes=[("test_vip_tools_pinned.py", ""), ("test_search_tools_pinned.py", "")]),
    dict(n=103, issue="#116 A3, A4", title="Held and closed runs cannot write", branch="main", kind="scriptable",
         do="Run the pins.",
         see="Held-mode runs (Prep page, Current state, AI drafts, Shape the meeting, transcript check) and the shape-closed and notes-find runs have Edit, Write, MultiEdit and NotebookEdit denied by name.",
         tests=["test_held_edit_deny.py", "test_closed_runs_no_writers.py"], probes=[("test_closed_runs_no_writers.py", "")]),
    dict(n=104, issue="#116 F2", title="Every run names its built-in tools", branch="main", kind="scriptable",
         do="Run the pins.",
         see="Each run kind has an explicit --tools list; every known built-in it does not name is denied; no Task in a chat; an unknown kind fails closed; the prompt stays last.",
         tests=["test_run_tools_explicit.py"], probes=[("test_run_tools_explicit.py", "")]),
    dict(n=105, issue="#116 F3", title="The permission card refuses other connectors and acting built-ins", branch="main", kind="scriptable",
         do="Run the tests; run doctor.",
         see="An allow rule for any connected service other than the Microsoft 365 reading tools, or for a built-in that acts outside the laptop, is refused whatever is approved; doctor flags one already present in the project, local or user settings.",
         tests=["test_permissions_mcp.py"], probes=[("test_permissions_mcp.py", "")]),
    dict(n=106, issue="#116 A5", title="Held runs read only (Bash)", branch="held-bash-fix-final", kind="scriptable",
         do="Run the tests.",
         see="A held run is never marked, may run only creaite's read commands, refuses a # comment, ~+ ~- and wildcards, and applies the never list to every argument form; tracker.py validate only on a file in system/staging.",
         tests=["test_held_bash_arg_forms.py", "test_held_run_bash_writes.py"], probes=[("test_held_bash_arg_forms.py", "test_every_form_is_refused")]),
    dict(n=107, issue="#116 A6", title="ask creaite's guard: argument forms and wrap/hook", branch="ask-hook-fix-final", kind="scriptable",
         do="Run the tests.",
         see="ask creaite refuses the never list in every argument form (--opt=PATH, quoted $HOME, a wildcard, //), an unquoted #, ~+ ~- and **, and reach.py wrap or hook as a Bash call; tracker.py validate only on a proposal in staging.",
         tests=["test_ask_bash_arg_forms.py", "test_record_commands.py"], probes=[("test_ask_bash_arg_forms.py", "test_every_form_is_refused")]),
    dict(n=108, issue="#91", title="A message starting with - is never read as a Claude option", branch="main", kind="scriptable",
         do="Run the test; send ask creaite a message that starts with \"--\".",
         see="It is answered as a message; the prompt goes after -- in both claude -p launches.",
         tests=["test_prompt_after_dashdash.py"], probes=[("test_prompt_after_dashdash.py", "")]),
    dict(n=109, issue="#125", title="Close the day does not depend on the date", branch="main", kind="scriptable",
         do="Run the test.",
         see="It passes whatever the real date is (the fixture is stamped from a fixed day).",
         tests=["test_close_day.py"], probes=[("test_close_day.py", "")]),
    # ── Small defects fixed in this release ──────────────────────────────────
    dict(n=110, issue="#92", title="A refused Apply says what to do", branch="fix-refused-apply", kind="scriptable",
         do="Change a file after an item was staged, then Apply.",
         see="The refusal says in plain words what happened and what to do.",
         tests=["test_refused_apply_words.py"], probes=[("test_refused_apply_words.py", "test_real_refusal_becomes_plain_words")]),
    dict(n=111, issue="#94", title="Health: a card fix says it is waiting on the card", branch="health-card-wording", kind="scriptable",
         do="In Settings › Health press a Fix it that raises the approval card.",
         see="It says \"on the approval card, waiting for you\", not done; a failed one still says failed; a direct fix still says done.",
         tests=["test_health_fixes.py", "test_settings_calmer.py"], probes=[("test_health_fixes.py", "test_every_card_fix_says_it_is_waiting_on_the_card")]),
    dict(n=112, issue="#95", title="The first page after a restart stays quick", branch="search-stall", kind="scriptable",
         do="Restart the server and open the dashboard while the search index builds; search.",
         see="A search never holds the lock while the index builds (it answers from the index as it stands, saying it is indexing); the index builds with a short pause after each file and PDF page; the command line is never slowed.",
         tests=["test_search_stall.py", "test_index_pace.py"], probes=[("test_search_stall.py", "test_a_search_answers_while_the_index_builds_and_never_holds_the_lock")]),
    dict(n=113, issue="#96", title="Settings reads each status once", branch="settings-poll-repro", kind="scriptable",
         do="Open Settings after an update and leave it open.",
         see="Each status is read once; nothing polls while the page sits there; Refresh still reads afresh.",
         tests=["test_settings_poll.py"], probes=[("test_settings_poll.py", "test_opening_settings_reads_each_status_once")]),
    dict(n=114, issue="#93", title="The live server says why it stopped", branch="live-exit-log", kind="scriptable",
         do="Run the test (a log line only; nothing to see in the page).",
         see="A start that stops says why in the debug log; an hourly stale-page count is logged.",
         tests=["test_live_server_exit_log.py"], probes=[("test_live_server_exit_log.py", "")]),
    # ── Live only and judgement ──────────────────────────────────────────────
    dict(n=115, issue="#116", title="Every hardened run still works with the real Claude", branch="main", kind="live only",
         live="needs the real claude on laptop 1: with --tools lists and denies per run kind, one ask creaite chat that reads a note, one Prep page, one Search question and one Current state draft must each still work",
         do="On laptop 1 (or the development copy with the real Claude): ask creaite to read a note; build a Prep page; ask a Search question; Generate a current state.",
         see="Each completes; none reports a refused tool that it needs.",
         tests=[], probes=[]),
    dict(n=116, issue="#114", title="Review's floating bar as drawn", branch="review-114-floating-toolbar", kind="judgement", sheet=["review-selected"],
         do="Look at Review with several rows selected, light and dark, desktop and 900 px.",
         see="The bar floats at the bottom edge, centred, with the page's tokens; it covers no row action.",
         tests=[], probes=[("test_review_floating_bar.py", "test_desktop")]),
    dict(n=117, issue="#113 #105", title="Today as drawn (80% width, Week ahead folded)", branch="ux-113-today-80", kind="judgement", sheet=["today"],
         do="Look at Today, light and dark, desktop and 900 px.",
         see="Content is 80% wide and centred under a full-width band; Week ahead sits like Resolved.",
         tests=[], probes=[("test_today_home.py", "test_the_headers_content_is_80_percent_centred_and_the_band_full_width_at_1400_and_900")]),
    dict(n=118, issue="#115", title="The Notes header as drawn", branch="notes-115-header-focus", kind="judgement", sheet=["notes"],
         do="Look at a note, light and dark, desktop and 900 px.",
         see="One tidy title row, one property line, Tags on their own line, nothing wrapping.",
         tests=[], probes=[("test_notes_header.py", "test_the_header_is_tidy_at_1400_and_900")]),
    dict(n=119, issue="#110", title="Generate current state as drawn", branch="current-state-dialog", kind="judgement", sheet=["generate"],
         do="Look at the dialog (set up, and the draft with Steer it further), light and dark, desktop and 900 px.",
         see="Quiet fields with hairlines on hover and focus, a readable hint line, the footer in view.",
         tests=[], probes=[("test_generate_dialog.py", "test_it_is_736px_wide_at_desktop_and_at_900px_and_nothing_overflows")]),
    dict(n=120, issue="#124", title="Delete note: the wording and the one card (by hand)", branch="notes-124-delete-note", kind="live only",
         live="seen by hand on the development copy: the confirm box and the one approval card are judged for wording and layout in both themes (the screenshots would need the live approval, which a test may not grant)",
         do="Delete a note in the development copy; read the confirm box and the card at 1400 px and 900 px, light and dark.",
         see="The words are plain and match the issue; both the box and the card show, and only Approve moves the note.",
         tests=[], probes=[("test_notes_delete_browser.py", "test_delete_note_confirm_then_card_then_undo")]),
    dict(n=121, issue="BL-342 Part 3 B", title="A thread card as drawn (by hand)", branch="bl342-part3b-v3", kind="live only",
         live="seen by hand: the cards need the sweep's conversations; the test (test_vip_screens) checks both themes and both widths, but whether the card reads well is Alan's call",
         do="Look at a thread card on Today, light and dark, desktop and 900 px.",
         see="Type, ask, due, owners and the match read at a glance; the chips and the count are clear.",
         tests=[], probes=[("test_vip_screens.py", "test_the_card_in_both_themes_and_both_widths")]),
]


GROUPS = [(75, 88, "Polish and the small UX items (#98, #101 to #109, #113, #114, v2.0.0 polish A and B)"),
          (88, 93, "Notes (#115, #119, #124)"),
          (93, 95, "The Generate current state dialog (#110)"),
          (95, 99, "✦ on the sheets and the one editor (#90, #123, #122, #117, #118, #120)"),
          (99, 102, "VIP thread cards (BL-342 Part 3 B)"),
          (102, 110, "Security hardening (#116: A, A2 to A6, F2, F3; #91; #125)"),
          (110, 115, "Small defects fixed in this release (#92 to #96)"),
          (115, 122, "Live only, and checks for your eye")]


def markdown():
    """The second half of the Checks section, from ITEMS."""
    out = []
    for lo, hi, head in GROUPS:
        out.append(f"\n### {head}\n")
        for it in ITEMS:
            if lo <= it["n"] < hi:
                kind = {"scriptable": "scriptable", "judgement": "judgement", "live only": "live only"}[it["kind"]]
                if it["issue"].startswith("#116") or it["issue"] in ("#91", "#125") or it["n"] in (114,):
                    kind += ": test only"
                where = {"main": "on main", "none": "not built yet (no branch)"}.get(it["branch"], f"branch `{it['branch']}`")
                out.append(f"{it['n']}. **{it['issue']} {it['title']}.** {it['do']} → {it['see']}")
                bits = [f"{kind}", where]
                if it["tests"]:
                    bits.insert(1, "tests " + ", ".join(f"`{t}`" for t in it["tests"]))
                if it.get("sheet"):
                    bits.insert(1, "sheet: " + ", ".join(it["sheet"]) + " (light and dark, desktop and 900 px)")
                if it["kind"] == "live only":
                    bits.insert(1, "why by hand: " + it["live"])
                out.append("   - " + "; ".join(bits) + ".")
    return "\n".join(out) + "\n"


def landing():
    """The landing table (item, issue, branch, checks)."""
    rows = ["| Check | Item | Branch | Kind |", "|---|---|---|---|"]
    for it in ITEMS:
        rows.append(f"| {it['n']} | {it['issue']} {it['title']} | {'main' if it['branch'] == 'main' else '`' + it['branch'] + '`' if it['branch'] != 'none' else 'none yet'} | {it['kind']} |")
    return "\n".join(rows) + "\n"


def results():
    return "".join(f"| {it['n']} | {it['issue']} | {it['title'][:60]} | [ ] | [ ] | |\n" for it in ITEMS)


if __name__ == "__main__":
    import sys
    print({"checks": markdown, "landing": landing, "results": results}[sys.argv[1] if len(sys.argv) > 1 else "checks"]())
