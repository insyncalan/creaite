# v1.9.3 Sneak peek (BL-322): the server side

Team 2, branch `v193-sneak-peek-server` (from `origin/main` + `origin/dev-bl322-sneak-peek`). The screen is built on
`v193-sneak-peek-ui` against `dev/sprints/BL-322-contract.md`.

## What was built

- **`system/scripts/sneak_peek.py`** (new; Python 3.9, standard library only). Reads one instruction on the item open in the
  peek, in plain code, and writes nothing. `read_request({id, text, picks})` → the contract's reply. Command line:
  `sneak_peek.py read` (JSON on stdin). Covers, on actions, RAID items, decisions, milestones and promises where each applies:
  owner / decision maker / promised by or to (people register; `@` names; two matches → `choices`, answered by `picks`; none →
  no change); dates in Alan's words (today, tomorrow, Friday, next Tuesday = next week's, next week, end of the month, in 3
  days, 20-10, 20-10-2026, push it out / back / bring it forward); status in each kind's words; priority; impact and likelihood
  (the recalculated priority shown as a derived row; the tracker works it out); workstream (active ones of the project) and
  milestone; add / remove a label; client-visible on (confirm; refused until the client message is complete, with a `client`
  draft offer) and off; add an update; a RAID item's response; revisit (date or condition); rewording; decision made (with
  date and who) and withdraw; a milestone's state (reason required when better than the dates); risk → issue; "because …"
  reasons. Tasks: link, follow-on action, risk from an action, promise, chase hand-off (Draft chase, tone), go to (source,
  milestone, project), quick facts (chased, source, links), Claude drafts. The confirm list and the Never list are as BL-322.
- **Every staged change is tried in the tracker's own dry run** (`tracker.dry_run`, always rolled back) before it is offered,
  so the schema's rules apply as written; a refusal comes back in `problems` and nothing is staged.
- **`POST /api/sneak/read`** in `live_server.py` (token-checked like every POST; in-process; takes `LOCK` so its dry run never
  meets an apply). No write route: the screen stages `stage.items` through the peek's own save path and applies with
  `/api/apply`, Undo with `/api/undo`.
- **`tracker.py`: `@n` link ends** (`sibling_refs`, `resolve_sibling_refs`). A link item's `from_item`/`to_item` may be `@n`, the
  ID given to new item `n` of the same proposal (written before it). So a follow-on action, risk or promise and its link go in
  one apply and one undo. Used in both the dry run and the apply; after the apply the real ID is in `values`, the `@n` under
  `refs`. Documented in `dev/staging-format.md`.
- **Draft kind `sneak-update`** (feature `update`) in `drafts.py`, prompt `system/templates/drafts/sneak-update.md`: an action's
  update tidied (`mode: tidy`) or worded from Alan's reason (`mode: reason`, `text`). `live_server.py`: added to
  `DRAFT_KINDS`, and `draft_request` keeps `mode`. "write a client message" and "draft the reasoning/options" reuse the existing
  `client` and `thinking` kinds. With a feature off, `needs_claude.off` is true and says why; the plain-code part still works.

## Gaps and decisions for the screen or Alan

- **RAID items, decisions and promises have no latest-update column** (BL-322 says no schema change). "add an update" on them is
  refused with a pointer (a RAID item's response). A milestone's "because …" goes into its `internal_note`.
- The follow-on links: a new action or risk **blocks** the open item; the open item **blocks** a new promise (links have only
  `blocks`).
- Nothing new is sent anywhere; the chase task only opens Draft chase (`/api/chase/pane`).

## Security list changes (for Team 1)

- `reach.SCRIPT_COMMANDS`: **added `"sneak_peek.py": {"read": READ}`**. It only reads (its dry run is rolled back). No other
  security list changed: no permission rule, no never-list entry, no guard-hook change. ask creaite isn't given the script; the
  live server calls it in-process.

## Tests

- `dev/tests/test_sneak_peek_read.py` (new, 31 tests): dates on several weekdays with a pinned clock; each field on each kind;
  an ambiguous owner and its pick; no match; the confirm list; the Never list; tasks; drafts on and off; a read writes nothing;
  the real apply and undo of a new action with its `@1` link; a bad `@n` stops the apply; the route (token-checked, read only,
  the new draft kind known to `/api/draft`).
- `dev/tests/test_tracker.py`: `make_vault` copies `sneak_peek.py`.
- Passing: test_sneak_peek_read, test_guard_pinned, test_reach, test_record_commands, test_script_policy, test_live_server,
  test_drafts_scaffold, test_drafts_update, test_drafts_client, test_drafts_thinking, test_drafts_reason, test_drafts_agenda,
  test_drafts_email, test_drafts_forms, test_draft_chase, test_tracker; `check.py`: OK.
