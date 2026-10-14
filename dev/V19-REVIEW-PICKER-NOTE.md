# v19-review-picker: BL-297 D, Review's "Update an existing item instead" (note for Team 1)

13-10-2026. Branch `v19-review-picker`, from `origin/v19-base` (`dacf912`). Not pushed.

## What's built

- **Where:** any pending row with `op === "new"`, a project, and kind action, RAID item or decision (`rtOK` in
  `src/review.js`). Two places, both keyboard reachable:
  - the proposal's peek: a button under the "Editing a proposal" line, after the Looks like note when there is one
    (`rtNoteHtml`, drawn in `#pkPropTop` by `panel.js` `pkPropDraw`; the only change outside `review.js`);
  - the row's right-click menu (and Shift+F10): "Update an existing item instead…" (`cxReview`).
  Not on the row itself, so the default Review screen is unchanged.
- **The picker:** `rtOpen` posts `/api/review/candidates {file, ref}` and opens Work's picker (`pkList`, the `.pkpop`
  popover) as a listbox named "Update which action instead" (risk or issue, decision): button `aria-haspopup="listbox"`,
  `aria-expanded`, `aria-busy` while it asks; ↑ ↓ Home End, Enter picks, Esc and Tab close with focus back to the button;
  search when there are more than seven. Each option is "ID · title" with a hint: "Looks like" for the marked item, the
  strength and why ("Very likely: Same thread · Dana"), the owner, "Due DD-MM-YYYY". Never a percentage, never "VIP".
  No candidates: a message, no picker. Without the live server: a message naming the Claude Code command.
- **Choosing:** `rtGo` posts `/api/review/retarget {file, ref, id}`, closes the peek if it shows that proposal, reloads,
  and says "Now an update to ID" (or "Rejected as a duplicate of ID: it carried nothing new") with **Undo** (⌘Z too):
  `{file, ref, undo: true}` (review.py unmerge), then reloads. Refusals show the server's message.
- Help (`help.md`: Review steps 11, the "Or say" line, Features › Review), the printed guide rebuilt
  (`build_guides.py`), `dev/dashboard-spec.md` (a BL-297 D bullet after BL-221's), `.rtline` in `style.css`.

## Tests

- `dev/tests/test_smart_updates.py` `PickerBrowserTests` (headless Chrome, the real live server and review.py, FAL
  sample): the Review list has no picker button; the peek's button opens the listbox with FAL-A-007 first and "Very
  likely", never the item raised after the message, no "%" or "VIP"; ↓ moves, Esc closes and returns focus with
  `aria-expanded` false; Enter reopens and Enter picks; the proposal becomes an update to FAL-A-007 (`retargeted`),
  the tracker is untouched, the peek closes; Undo puts the new item back. The right-click menu offers it on the new item
  and not on an update, and opens the same picker. 3 tests, OK; the whole file 29, OK.
- Also run, all OK: test_snapshots, test_help (after `build_guides.py`), test_help_loop, test_dashboard_split,
  test_spec_fields, test_context_menu, test_review_project, test_review_triage, test_review_focus, test_no_dead_ends,
  test_reject_reasons, test_work_item_peek, test_dashboard_editing.
- `python3.14 dev/tools/check.py`: check: OK. Type check: 0.

## Goldens

None changed (BL-254's snapshots pass as they were; the Review screen is unchanged).

## Open

- Built on today's `pkList`, not a Preact component: COMPONENTS.md lists `pkList` as what the `Picker` block replaces, so
  this moves with it.
- Activity › Quality's line for `D.quality.repeats` ("Pointed at an existing item: …", BL-297-server.md) isn't drawn;
  that is `activity.js`, outside this item.
- No Undo on the row itself after the message has gone (the server doc's optional `undoable` flag in
  `build_dashboard.review_queue`); say "unmerge" in Claude Code, or reject the update.
- No single-key shortcut in Review (the key hint line is in the Review golden); the peek's button and Shift+F10 cover the
  keyboard.
