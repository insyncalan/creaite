# v1.9.1 — ask creaite's changes through the dashboard's own actions (BL-314, routing)

Branch `v191-ask-routing`. Taken over from Team 1's paused WIP (`026f15d`, "not tested") on 14-10-2026, Alan approving.
Guard decision (Alan, directly, 14-10-2026, commit `daf54fa`): a change asked in ask creaite runs through the dashboard's own
action (same route, card, Undo); the model gains no new command; BL-141's guard and BL-267's record gate stay.

## What Team 1 had
- `live_server.py`: the `EDIT: <item ID> | <field> | <new value>` reply line in ASK_PROMPT and CONFIRMED_PROMPT; `strip_confirm`
  strips it; `build_field_card` checks each line against the tracker (`tracker.py read`), maps the field to the dashboard's own
  key, normalises the value (dates, choices, owner through the people register), applies the dashboard's rules (closing fills
  the closed date, a made decision can't go back to pending, a title can't be emptied), previews with `propose.py preview` from
  `system/guard/`, and emits a `fieldcard` event; `run_holds` holds the queue on it.
- `ask.js`: `fieldCardHtml` / `fieldFlow` (Cancel, Go ahead), saving each item with `boardMove`.
- Also: a CHANGE spec holding only field updates was diverted onto the field card.
- Not tested; no Help, spec, skill text or note.

## What I finished
- **Dropped the CHANGE-spec diversion.** It broke `test_ask_change_card` (8 failures: the BL-258 card stopped appearing). The
  CHANGE card is unchanged and stays for what the field card doesn't cover (new items, projects, memory, register,
  client-visible, over ten changes); field changes reach the field card through EDIT lines, as the prompt says.
- **One proposal, one Undo.** `boardMove` per item wrote one proposal and one apply per item, so Undo undid only the last.
  `work.js` now has `itemsMove(list, what)`: the Work bulk bar's save (`batchMove`, now a thin wrapper over it) with a patch per
  item: `ownerFinal` per owner, `prepMove` (the sidebar's `norm` and `validate`), one `save()` → one proposal through `/api/fs`
  (`source_run: "dashboard"`), applied through `/api/apply` with auto-apply, one Undo. Items left out are named in the chat.
  `batchMove`'s behaviour is unchanged (test_bulk_edit, test_work_board_moves pass).
- Go ahead is offered only when the card is valid and has items; a card with problems offers only Cancel.
- Server functions split to pass check.py's complexity limit (`field_date`, `field_choice`, `field_person`, `field_value`,
  `field_decision_status`, `field_closed`, `field_rules`, `field_one`, `field_items`, `field_preview`, `build_field_card`).
- Tests: `dev/tests/test_ask_field_card.py` (server: preview lines and patch, several items on one card, unknown ID / field /
  choice / impossible date, made decision → pending refused, "already" gives no card, CHANGE card unchanged, no new route;
  Chrome: Go ahead writes one dashboard proposal, applied, page data updated, closed date filled, Undo restores; Cancel writes
  nothing; a card with problems offers only Cancel).
- Help (`system/templates/help.md`), `dev/dashboard-spec.md` (new section), cx-edit's panel line (`.claude/skills/cx-edit/SKILL.md`).

## How routing works
1. The model, asked to change fields of existing actions, RAID items or decisions, ends its reply with up to ten
   `EDIT: <ID> | <field> | <value>` lines. It runs nothing and writes nothing for them.
2. At the end of a guarded run, the server (`build_field_card`) checks every line against the tracker and the dashboard's rules,
   previews the result with `propose.py preview`, and sends `fieldcard {card, title, valid, lines, problems, notes, items}`.
   Lines shown are the preview's, never the model's words.
3. The page shows the card. **Go ahead** is Alan's own click on the dashboard's own save (`itemsMove`): the same checks, route,
   staging, auto-apply and Undo as the bulk bar or a peek edit. **Cancel** writes nothing. The bulk rule (Review's "Approve
   routine") is untouched: this is an edit, not a Review approval.
4. Limitation: the field card isn't kept over a page reload (unlike the CHANGE card's `/api/edit/pending`); nothing is written
   without it, so Alan asks again.

## Security changes for Team 1 to confirm
None. reach.py, the guard hook, filechange.py, permissions.py, READ/DENY/WRITE tools and SCRIPT_COMMANDS are untouched; no new
server route; the model gains no command (a reply line only). Every listed guard test passes unchanged: test_guard_pinned,
test_reach, test_record_commands, test_script_policy, test_run_read_pinned, test_ask_access, test_ask_confirmed_apply,
test_ask_change_card, test_admin_card.

## Merge with ask-claims
`git merge-tree --write-tree HEAD origin/v191-ask-claims` is clean (no conflict), so this branch does **not** contain ask-claims.
A trial merge of both (not committed) passed check.py, test_ask_claims, test_ask_field_card, test_ask_change_card and
test_chat_and_sweep: the claims check runs on text blocks after `strip_confirm` (which strips EDIT lines), and `_end_answered`
runs the "I can't" check, the CHANGE card and the field card side by side.

**Merge order:** `origin/v191-ask-claims` first, then this branch; it merges cleanly after. **After the second merge, run
`python3.14 dev/tools/split_dashboard.py build` and commit `system/templates/dashboard.html`:** git's text merge of the built
file differs from a rebuild of the merged sources (the trial's tests ran on the rebuilt file; check.py OK).
