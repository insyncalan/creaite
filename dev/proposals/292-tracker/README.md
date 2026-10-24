# #292 plain words in `tracker.py`: the exact strings (README first, no diff yet)

Status: written (`tracker.diff`, `live_server.diff`), after Jarvis's decisions: the save-id line `Apply N:`, `Held in Review, not applied`, the
usage line and the "Schema changed ... run tracker.py migrate" line all STAY. Only rows no other code reads are changed. Two guarded files,
one diff each, Full review. Chain order: 345, 346, 334, line-reach, then `tracker.diff`, then `live_server.diff` (checked on clean main
in that order and reversed, and in other orders: the same tree each time).

## Final table: changed and left

Changed (36 lines of `tracker.py`; one line of `live_server.py`): every row marked "wording" in the table below whose words no
page code, `review.py`, `claims.py`, `build_dashboard.py`, Help or skill reads, and that no golden file pins. Checked by grep per row at
write time: the only hits outside `tracker.py` were a comment in `itemLink.js` and the same sentence in `live_server.py:1407`
(changed in `live_server.diff`, so the page's "Nothing to save" and `test_hold_peek` agree). Also changed, the two returned (not raised)
copies of "the file changed since it was staged" (lines 1614 and 2784), so the sentence reads the same everywhere.

| Left for 2.6.5 | Why | What must move with it |
|---|---|---|
| 825 unknown fields (`. Valid:`) | meaning and shape change; `build_dashboard.py:828` cuts at `. Valid:` | that reader, same step |
| 891 conflict reason (`after this proposal was made`) | pinned in `pinned/conflict.json` (4 places); stored in the waiting files | re-record the pin, deliberately |
| 1675 / 2013 `write: ... since this proposal was made` | read by `core/server.js` applyWords | the page reader |
| 2467 guard folder text | second raise of the same words in `live_server.py:5396`, 2 tests | both guarded files |
| 2866 `Nothing applied: every decided item is held` | pinned in 3 goldens | re-record the pins |
| 2939 / 3084 `Held in Review, not applied` | decision: stays; read by review.js, core/server.js, 38 tests | -- |
| 3121 / 5001 `Apply stopped` (and the recode line) | read by core/server.js, findUpdates.js, Help, ~10 tests | the page reader |
| 3317 `Apply failed` | read by core/server.js, test_refused_apply_words | the page reader |
| 3337 `Apply N: written ...` | decision: stays; read by review.py:2608, live_server.py:8401, say.js, review.js, minutes.js | -- |
| 3450 `Undid apply N` | pinned in 17 goldens and read in 6 tests | re-record the pins |
| 3737 usage line, 3985 `Schema changed` | decision: stay | -- |

The quoted "before" strings are the engine's own words and so contain the words the plain-words rule bans; that is the point of the
table. Everything else in this note avoids them.

## What this is

#292 (`origin/v264-292`, 8c9b728e) changed the wording everywhere the dashboard and the unguarded scripts say it, and left `tracker.py`
as it was, because `tracker.py` is guarded. `test_plain_words` counts `tracker.py` too: its strings are the ones that stay in the
baseline until this diff lands. The table lists every message string in `tracker.py` that breaks a rule (the same list the test builds:
`python_strings`, 46 distinct strings; "about 59 findings" is the same list with the repeats per rule counted separately). The "after" column
uses #292's own vocabulary (`dev/PLAIN-WORDS.md`: suggestion, save, your project record, your creaite folder, Intake, "ask creaite").

Rules for the diff once approved:
- Only the text of a message changes. No condition, no return value, no key, no log line, no comment.
- Where code reads a message (next table), that code changes in the same step, and a test holds the pair together.
- `test_plain_words`' baseline is rewritten in the same commit (count falls by the strings changed).

## Already decided by #292, for these strings

- "Nothing to apply: no decided items." becomes "Nothing to save: no decided items." (#292's `test_refused_apply_words.py` already
  expects the new sentence from the page's `applyWords`; `tracker.py:2854` and `live_server.py:1407` still say the old one).
- "isn't in the tracker" becomes "isn't in your project record" in the unguarded scripts #292 touched (`minutes.py`, `drafts.py`,
  `report.py`, with their tests). `claims.py` and `review.py` were not changed by #292: `claims.py` still flags "(not in the tracker)" and
  `test_ask_claims.py` matches it, so that pair is a separate unguarded follow-up. The tracker's own `is not in the tracker` family below is
  the guarded remainder.
- The page's `plainSay` (core/say.js) already rewords these on screen, so the server text is mainly for ask creaite's replies, the
  Excel round-trip's messages and any reader of the raw answer; that is why the table shows who reads them.

## The table

Columns: line in `tracker.py` (as on origin/main e6389af8, which v264-guarded is cut from), function, before, after, then who mentions the same words: tests,
page (JS), other scripts (review.py, claims.py, excel_sync.py, live_server.py ... basenames), Help and skills, and the note (meaning
change or matching code). "Mentions" is a search for the longest fixed part of the sentence, so it can include a comment or a
different sentence with the same words; each hit is checked when the diff is written.

| Line | Function | Before | After | Tests | Page (JS) | Other scripts | Help / skills | Note |
|---|---|---|---|---|---|---|---|---|
| 284 | `canonical_labels` | `unknown label {} (labels: {}); add it in Settings or with cx-edit first` | `unknown label {} (labels: {}); add it in Settings or ask creaite first` | - | - | - | - | wording |
| 405 | `_safe_resolved` | `{}: path is outside the vault ({})` | `{}: path is outside your creaite folder ({})` | - | - | - | - | wording |
| 413 | `safe_path` | `{}: path must be relative to the vault root ({})` | `{}: path must be relative to your creaite folder ({})` | - | - | - | - | wording |
| 416 | `safe_path` | `{}: path is outside the vault and the projects folder ({})` | `{}: path is outside your creaite folder and the projects folder ({})` | - | - | - | - | wording |
| 418 | `safe_path` | `{}: {} is not in projects/, inbox/, system/staging/ or system/search/` | `{}: {} is not in a project folder, Intake, the waiting suggestions or the search index` | - | - | - | - | wording (names folders by their friendly names) |
| 540 | `_item_label` | `{} isn't an action, RAID item or decision in the tracker, so it can't carry a label` | `{} isn't an action, RAID item or decision in your project record, so it can't carry a label` | - | - | - | - | wording |
| 570 | `_project_exists` | `project {} is not in the tracker` | `project {} is not in your project record` | test_milestones.py, test_schema_sprint5.py | itemLink.js | - | - | wording |
| 579 | `_milestone_link` | `milestone {} is not in the tracker` | `milestone {} is not in your project record` | test_milestones.py, test_schema_sprint5.py | itemLink.js | - | - | wording |
| 610 | `check_decision` | `{} (replaced by this decision) is not in the tracker` | `{} (replaced by this decision) is not in your project record` | - | - | - | - | wording |
| 629 | `check_link` | `{} {} is not in the tracker` | `{} {} is not in your project record` | test_milestones.py, test_schema_sprint5.py | itemLink.js | - | - | wording |
| 825 | `unknown_fields_message` | `unknown field(s) for {}: {}. Valid: {}` | `{} can't take the field(s) {}. It takes: {}` | test_held_visible.py, test_intake_review_harden_b.py, test_refused_apply_words.py, test_save_not_blocked.py, test_schema_sprint5.py, test_spec_fields.py | - | - | - | WORDING + SHAPE: build_dashboard.py:828 cuts the message at '. Valid:' to show the reason; it changes in step |
| 891 | `_existing_row` | `{} changed at {} after this proposal was made` | `{} changed at {} after this suggestion was made` | test_no_dead_ends.py | - | - | - | wording |
| 932 | `_check_new_fields` | `new items carry no ID; tracker.py assigns it` | `new items carry no ID; creaite gives them one` | - | - | - | - | wording |
| 1437 | `cmd_validate` | `Item {}: Raised set to {} (source or staging date)` | `Item {}: Raised set to {} (the source's date or the date it was suggested)` | - | - | - | - | wording |
| 1507 | `__init__` | `copy: the source must be a path in the vault or the projects folder, with no '..' ({})` | `copy: the source must be a path in your creaite folder or the projects folder, with no '..' ({})` | - | - | - | - | wording |
| 1511 | `__init__` | `copy: a source is filed only from inbox/, staging drafts or uploads, or a project folder ({})` | `copy: a source is filed only from Intake, your drafts or uploads, or a project folder ({})` | - | - | - | - | wording |
| 1515 | `__init__` | `copy: the source is outside the vault and the projects folder ({})` | `copy: the source is outside your creaite folder and the projects folder ({})` | - | - | - | - | wording |
| 1675 (also line 2013) | `_op_write` | `write: {} changed since this proposal was made` | `write: {} changed since this suggestion was made` | test_propose.py, test_refused_apply_words.py | server.js | - | - | WORDING + MATCHED: core/server.js applyWords reads it with /write: (.+?) changed since this proposal was made/ |
| 1845 (also line 1888) | `_copy_into` | `copy: {}: the file changed since it was staged` | `copy: {}: the file changed since it was saved for review` | - | - | - | - | wording |
| 1921 | `_open_inbox_folder` | `remove: {} is not a file in inbox/` | `remove: {} is not a file in Intake` | - | - | - | - | wording |
| 1955 | `_remove_checked` | `remove: {}: the file changed since it was staged` | `remove: {}: the file changed since it was saved for review` | - | - | - | - | wording |
| 2292 | `check_move` | `move: path must be a stored projects/ path ({})` | `move: the path must be inside a project folder ({})` | - | - | - | - | wording |
| 2467 | `card_marker_ok` | `system/guard is a symlink` | `creaite's guard folder is a link, so nothing was changed` | - | - | live_server.py | - | wording; the same words are raised in live_server.py:5396 (a second guarded file) and matched by 2 tests |
| 2854 | `cmd_apply` | `Nothing to apply: no decided items.` | `Nothing to save: no decided items.` | test_refused_apply_words.py | - | live_server.py | - | wording; ALREADY EXPECTED by #292's test_refused_apply_words.py (line 55); the same sentence is in live_server.py:1407 (guarded), which must change in the same step |
| 2866 | `cmd_apply` | `Nothing applied: every decided item is held in Review.` | `Nothing saved: every decided item is held in Review.` | - | - | - | - | wording |
| 2914 | `_load_work` | `{} item {}: Raised set to {} (source or staging date)` | `{} item {}: Raised set to {} (the source's date or the date it was suggested)` | - | - | - | - | wording |
| 2939 | `_validate_work` | `Held in Review, not applied: {} item {}: {}` | `Held in Review, not saved: {} item {}: {}` | test_archive_items.py, test_archive_projects.py, test_held_missing_source.py, test_held_visible.py, test_intake_review_update.py, test_intake_say_307.py +4 | review.js, server.js | - | - | WORDING + HEAVILY MATCHED (see 'Lines the code reads'): review.js heldLines/heldWords, core/server.js ownHeld/applyBlockers, 38 test files. Decision: change everywhere in one step, or leave as the page already rewords it |
| 3021 | `by_others_problem` | `copy: {} is taken by a different file in this apply` | `copy: {} is taken by a different file in this save` | test_minutes_by_others_filing.py | - | - | - | wording |
| 3036 | `_skip_by_others_problems` | `Left in staging, not applied: {}: {}.` | `Left waiting, not saved: {}: {}.` | test_card_only_moves.py, test_delete_note_no_card.py, test_notes_card_only_ops.py | - | - | - | wording; 4 tests |
| 3051 | `_skip_card_leftovers` | `Left in staging, not applied: {}. Delete note or Move back again, or remove {}.` | `Left waiting, not saved: {}. Delete note or Move back again, or remove {}.` | - | - | - | - | wording; 4 tests |
| 3084 | `_hold_missing_sources` | `Held in Review, not applied: {} {}` | `Held in Review, not saved: {} {}` | test_archive_items.py, test_archive_projects.py, test_held_missing_source.py, test_held_visible.py, test_intake_review_update.py, test_intake_say_307.py +4 | review.js, server.js | - | - | as 2939 |
| 3121 | `_report_blocked` | `Apply stopped. Nothing was written.` | `Saving stopped. Nothing was written.` | test_card_only_moves.py, test_minutes_draft.py, test_minutes_track_review.py, test_notes_card_only_ops.py, test_refused_apply_words.py, test_save_not_blocked.py | - | - | - | WORDING + MATCHED: core/server.js applyWords/applyBlockers read 'Apply stopped'; 10 test files; #292 tests still accept 'apply stopped' next to the new wording |
| 3221 | `sibling_refs` | `{} {} refers to item {}, which isn't a new item written before it in this proposal` | `{} {} refers to item {}, which isn't a new item written before it in this suggestion` | - | - | - | - | wording |
| 3317 | `_report_rolled_back` | `Apply failed; nothing was written. {}: {}` | `Saving failed; nothing was written. {}: {}` | test_refused_apply_words.py | - | - | - | WORDING + MATCHED: core/server.js applyWords reads /^Apply failed/m; test_refused_apply_words.py |
| 3320 | `_report_rolled_back` | `(The database backup from before the apply is {}.)` | `(The backup from before this save is {}.)` | - | - | - | - | wording |
| 3337 | `_finish_apply` | `Apply {}: written {}, filed {}, rejected {}, {}{} still pending.` | `(leave as it is, or 'Save {}: written ...')` | test_intake_fix2_307.py | settings.js | close_day.py, live_server.py, sweep.py | SKILL.md | DO NOT CHANGE WITHOUT A DECISION: a status line the code reads: review.py:2608 (re 'Apply (\d+):'), live_server.py:8401 (re '^Apply (\d+): ' with a test mutant in test_delete_note_no_card), core/say.js savedCapped and review.js/minutes.js read 'written (\d+), filed, rejected'. Changing the prefix means changing two more guarded files |
| 3419 | `cmd_undo` | `Apply {} is the 1.5.0 migration that retired Missed (those milestones are now Overdue). It can't be undone, as Missed no longer exists; change a milestone's state instead. Nothing was changed.` | `Save {} is the 1.5.0 migration that retired Missed (those milestones are now Overdue). It can't be undone, as Missed no longer exists; change a milestone's state instead. Nothing was changed.` | - | - | - | - | wording |
| 3450 | `cmd_undo` | `Undid apply {}: {} item(s) reversed.` | `Undid save {}: {} item(s) reversed.` | test_schema_sprint5.py | - | - | - | wording; 5 tests |
| 3737 | `cmd_undo_changes` | `Usage: tracker.py undo-changes [--dry-run] [--json] <rowid> [<rowid> …]` | `Usage: undo-changes [--dry-run] [--json] <rowid> [<rowid> ...]` | - | - | - | - | MEANING: a typed-command usage line (reaches the page only as live_server.py:6136's fallback); decision: leave it, or drop the script name |
| 3863 | `migrate_workstreams` | `Workstreams added from items and settings ({}): {}. Leads and keywords are yours to fill (each project's settings › Workstreams, or cx-edit).` | `Workstreams added from items and settings ({}): {}. Leads and keywords are yours to fill (each project's settings > Workstreams, or ask creaite).` | - | - | - | - | wording |
| 3938 | `migrate_schema` | `Missed is retired: {} milestone(s) ({}) are now Planned with the state Overdue (apply {}, in Activity).` | `Missed is retired: {} milestone(s) ({}) are now Planned with the state Overdue (save {}, in Activity).` | - | - | - | - | wording; 3 tests, milestones.js |
| 3985 | `cmd_init` | `Schema changed for {}: run tracker.py migrate.` | `Schema changed for {}: creaite needs to update its records (Settings > Health).` | - | - | - | - | MEANING: today it tells a person to type a command; the new words point at Health (decision) |
| 4933 (also line 2061) | `archive_project` | `{} is not a project in the tracker` | `{} is not a project in your project record` | - | - | - | - | wording |
| 4960 | `recode_project` | `{} pending proposal(s) still mention {}: {}. Apply or reject them first` | `{} waiting suggestion(s) still mention {}: {}. Save or reject them first` | test_recode.py | - | - | - | wording; scripts and help.md quote it |
| 5001 | `recode_barrier` | `Apply stopped. Nothing was written.\n  {}: a recode is applied on its own, with no other items in its proposal.` | `Saving stopped. Nothing was written.\n  {}: a change of project code is saved on its own, with no other items in its suggestion.` | test_refused_apply_words.py | - | - | - | WORDING + MATCHED: core/server.js and findUpdates.js read 'a recode is applied on its own'; test_refused_apply_words.py; help.md |
| 5004 | `recode_barrier` | `{} is a recode: applying it first, on its own. Run apply again for the other proposals.` | `{} is a change of project code: saving it first, on its own. Save again for the other suggestions.` | - | - | - | - | wording; 1 test |

## Lines the code reads (must move with the wording, or stay)

| What reads it | Reads | Where | If the words change |
|---|---|---|---|
| Save result: id of the save | `Apply N:` at the start of the finishing line | `review.py:2608` (`Apply (\d+):`), `live_server.py:8401` (`^Apply (\d+): `, held by a test mutant in `test_delete_note_no_card.py`) | Both guarded files change too, or the prefix stays. Recommendation: keep the finishing line `Apply N: written X, filed Y, rejected Z, ...` as it is (a status line, not a sentence a person reads; the page shows its own "Saved ..." words) |
| Counts in that line | `written (\d+), filed (\d+), rejected (\d+)` | `core/say.js` savedCapped, `review.js:489`, `stores/minutes.js:233` | Only if the line changes |
| Held-in-Review lines | `Held in Review, not applied: <own> item <n>: <why>` | `review.js` heldLines/heldWords, `core/server.js` ownHeld/applyBlockers, `core/say.js` REWORDS, 38 test files, `live_server.py`, `build_dashboard.py` | Largest blast radius. Either change all in one step, or leave it (the page already says "Held in Intake, not saved"). Needs a decision |
| Stopped / failed / recode lines | `Apply stopped`, `Apply failed`, `a recode is applied on its own`, `write: ... changed since this proposal was made` | `core/server.js` applyWords/applyBlockers, `stores/findUpdates.js`, `help.md`, `test_refused_apply_words.py` and about ten more tests | Page and tests change in the same step; the tests keep one case with the old words only if an older server must still be understood (it need not: one release) |
| Field problems | `. Valid:` | `build_dashboard.py:828` | Cut at the new separator in the same step |
| Guard folder | `system/guard is a symlink` | `live_server.py:5396` (a second raise of the same words), 2 tests | Two guarded files; or leave it (it is never shown: it reaches the debug log) |
| Item not found | `is not in the tracker` family | no code parses the guarded text; `claims.py` flags its own "(not in the tracker)" wording (not changed by #292, see above) | Safe |
| Excel round-trip | none of these strings | `excel_sync.py` only mentions "Missed is retired" in a comment | Safe |

## Meaning changes to look at (everything else keeps its meaning)

- 825 unknown fields: "can't take ... It takes: ..." rewords an error about a field name; same fact, new shape (see the `. Valid:` row).
- 3737 usage line and 3985 schema line: today they tell a person to type a command. The vocabulary allows a typed command only in
  Settings > Diagnostics. Options: leave both (CLI use only) or take the script name out. Needs a decision.
- 3337 the finishing line: recommended unchanged, see above.
- 2939 and 3084 held lines: decision above.

## How the diff will be checked

- `git apply --check` and reverse on the chain after 345, 346, 334 and line-reach.
- A test that runs each changed message through `tracker.py` for real (a throwaway copy) and asserts the new sentence, plus one mutant
  per matched pair (page reader or guarded reader left on the old words, the pair goes red).
- `test_plain_words` (baseline down by the number changed), `check.py`, `test_refused_apply_words`, `test_save_not_blocked`,
  `test_propose`, `test_schema_sprint5`, `test_recode`, `test_held_*`, `test_minutes_*` on a scratch tree.

## Checked

`dev/tests/test_tracker_words_292.py` (works with or without the diffs in the tree): every changed sentence is the new one and the old one
is gone; every sentence in the left column is untouched; the command line says "Nothing to save", "is not in your project record" and still
prints `Apply 1: written 1, filed 0, rejected 0`; a mutant puts the old words back and the matching check goes red. Tests that asserted
the old text now accept both (a normalising `.replace` or a shorter fixed part), so the suite is green with and without the diffs;
`test_hold_peek`, `test_refused_apply_words` and `test_minutes_by_others_filing` already expect the new "Nothing to save" on v264-line.
