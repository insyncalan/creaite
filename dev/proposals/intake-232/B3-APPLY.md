# B3 (#232, release 2.6): what an update proposal edited in the peek can now write

For the independent review of the apply path (the plan asks for an Opus review of B3). Read only on `tracker.py`: nothing in it, or in any
guarded file, changed. What changed is **what a proposal file carries** after Alan edits it in the dashboard.

## What changed

Before: Save in the peek on an update proposal (the old edit form) wrote one column: `it.changes[r.rec.field] = f.to` (the first
change's field, one value).

Now: `panel.js` `updSave(approve)` (called by `pkPropSave` when the open proposal is an update, `shared.CUR.upd`) sets
`it.changes` to the result of `core/irUpdate.js` `irSaveChanges(table, changes, live, opened, draft)` through the existing
`editProposal(file, fn)` (the dashboard's staging write, with `edited_in: "dashboard"`, and `decision: "approved"`,
`decided_in: "dashboard"` for Save and approve). It writes nothing else: no `values`, no `based_on`, no `id`, no `table`, no `op`.
The apply is still `tracker.py apply` (the one writer), after Alan approves.

## Exactly which columns can now be written, and from where

`irSaveChanges` starts from the proposal's own `changes` (the sweep's or the minutes', as staged) and touches **only** the columns in
`EDITABLE[table]`, and only when Alan changed that value in the peek (the draft differs from what the peek opened with):

| Table | Editable in the peek (column) | Peek control | Notes |
|-------|-------------------------------|--------------|-------|
| `actions` | `status`, `due_date`, `latest_update` | Status listbox, date picker, the Latest update text field | |
| `raid` | `status`, `due_date` | Status listbox, date picker | A RAID item has no `latest_update`: the draft's is ignored (test). `response_action`, `impact`, `likelihood` are read-only |
| `decisions` | `status`, `needed_by` | Status listbox, date picker (shown as "Needed by") | plus `date` (below) |

Side column: for a `decisions` row, when Alan's status edit is `Made` and the live row has no `date`, the draft's `date` (the
peek's own status rule puts today there, as it always has) is carried with it, because the schema's `CHECK (status <> 'Made' OR date IS NOT NULL)` would refuse the apply otherwise. `date` is written only in that case.

For an edited column: the value becomes the draft's (trimmed; empty becomes `null`); **if it equals the live row's value, the column is
removed from `changes`** (nothing to write). A column Alan did not touch stays exactly as the proposal had it, including every
read-only column (`owner`, `priority`, `project`, `workstream`, `milestone`, `client_visible`, `client_message`, `description`,
`response_action`, ...): the draft is never read for them.

Never written by the peek: `closed` (the draft's `closed` set by the status rule is ignored: `tracker.py` derives it in
`_closed_for_update`), `updated_at`, `id`, `project`, any column of any other table.

If the edit leaves `changes` empty, the save is refused in the peek ("Nothing would change if this were approved"). If nothing was
edited, the proposal file is not rewritten at all.

## How each is validated

Twice: in the browser (`irSaveChanges`), then by `tracker.py apply`, which is the rule.

| Column | Browser check (`irSaveChanges`) | Tracker check on apply (`write_item` → `_update_row`) |
|--------|----------------------------------|--------------------------------------------------------|
| `status` | one of the table's allowed words (`STATUSES`, the tracker's `ALLOWED`) | `check_values`: `ALLOWED[(table, "status")]`; SQL `CHECK` on the column; `_check_decision` (a Made decision never goes back to Pending); `_closed_for_update` sets `closed` |
| `due_date`, `needed_by`, `date` | a real calendar date `YYYY-MM-DD` | `_check_date`; SQL `GLOB` and `CHECK`; `date` must be set when `status = Made` |
| `latest_update` | none (free text; empty becomes `null`) | a column of `actions` (`_check_changes` refuses a column the table lacks, with the valid ones named) |
| any other column in `changes` | not touched | the same rules as before the peek: `_check_changes` (unknown column, `id`, `updated_at`, a key refused), `check_values`, `_merged_row` (RAID priority derived from impact and likelihood, row rules, client messaging headings) |

`based_on` (set by the sweep when it stages an update) is not touched, so a row changed in the tracker since the proposal still
comes back as a conflict at apply (`_existing_row`), as before.

## Tests (apply level)

`dev/tests/test_intake_review_update.py` `ApplyPath` (real vault, real `tracker.py apply`):
- `due_date` and `latest_update` written together; the changed columns are exactly `due_date`, `latest_update`, `updated_at`;
- `status: Closed` sets `closed` itself (the peek never writes it);
- the change log holds one line per column written;
- a bad status, a date in the wrong form, an impossible date and an unknown column are each refused, with the row unchanged;
- a column outside the peek's set (`owner`) passes through as the proposal had it;
- a decision made in the peek: refused without its date, applied with it.

Pure rules (`PureRules`, run under Node): untouched columns stay as the proposal had them; an edited due date takes his value; an edit
back to the live value drops the column; a read-only column is never written whatever the draft says (owner, impact; a RAID
item's `latest_update`); the side `date`; an empty result is an error.
Browser (`test_intake_review_update_peek.py`, `UpdatePeekSaves`): Save with a changed due date stages `{"due_date": new,
"latest_update": as proposed}` and does not approve; Save and approve with a changed status writes status, the proposal's due date
and latest update to the tracker.

## What the reviewer should look at

1. `panel.js` `updSave`: only `it.changes`, `edited_in`, `decision`, `decided_in` are written; the rewrite is skipped when nothing
   was edited; `needVault()` and `editProposal` are the existing guards (the item must not be `applied`).
2. `core/irUpdate.js` `irSaveChanges`: `EDITABLE` and `SIDE` are the only columns it can add or change; a column in `changes` that
   is not editable is copied through untouched.
3. The in-memory row after a save (`r.rec.changes`, `r.rec.field`, `hold` through `irHold`) is the page's mirror; the file is the record.
4. Nothing here reaches the tracker before Approve (Save only stages; Save and approve then runs the ordinary `decide`).

No server route and no `tracker.py` change was needed.
