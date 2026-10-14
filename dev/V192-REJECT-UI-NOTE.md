# v192-reject-ui: BL-315 screens (Team 2 → Team 1)

Branch `v192-reject-ui`, from `origin/v192-reject-reasons` with `origin/main` merged in. Built by Team 2 with Alan's approval
(14-10-2026; it touches `review.js`, Team 1's module). Server side unchanged: it uses the four routes in
`dev/V192-REJECT-REASONS-NOTE.md` as they are. **No server, guard or schema change.**

**Merge order:** `v192-reject-reasons` first, then this branch (it contains it).

## What is built

- **One reasons menu**, `components/review/RejectMenu.jsx` (Preact, per dev/COMPONENTS.md: text through JSX only, Menu's keys and
  ARIA), its state in `stores/rejects.js`. "Reject n because", the seven on 1 to 7, **Use each guess** (G) and **No reason** (0);
  ↑ ↓ Home End, Enter or Space, Esc (focus back to the opener; `aria-expanded` on it), Tab or a click away closes.
- **Every way in opens it:** the bar's **Reject with a reason** (R) (the old Reject (n) and `#bulkRejectWhy` are gone), a row's ✕
  and ▾, R and Shift+R (highlighted rows, else the cursor row), the row's menu (right-click or Shift+F10: "Reject with a reason…"),
  the peek's Reject, One at a time's R. Minutes, reports and file changes are still rejected as before (they take no reason).
  A row's ✕ or ▾ acts on the selection when that row is in it, as in the mockup.
- **Guesses:** `/api/review/guesses` once per set of pending rows; each row shows "guess: Chatter" in grey (with "(looks like
  ABC-A-009)" when it names an item). G rejects each row with its own guess.
- **Duplicate:** takes the item a "Looks like" or a guess names; for one row with none it asks (the look-alikes from
  `/api/review/candidates`, an ID typed, or "Don't name it"). With several rows and more than one unnamed, they are rejected as
  Duplicate with no item.
- **After a reject:** one line in `#rvresult` and the message, with **Undo** (every row back in Review, highlighted). The rows stay
  greyed (`tr.rvgone`) where they were, with the chip **Rejected · Chatter** until Review is left; the chip or its ▾ changes the
  reason (with Undo); **Approve instead** approves in one step and applies; an item approved only on its own (new risk, new
  decision, minutes…) goes back to Review highlighted and its proposal opens; nothing is approved in bulk that the bulk rule keeps
  back. Right-click or Shift+F10 on a greyed row: Change the reason…, Approve instead, Put back in Review.
- **Activity › Quality › What you rejected** (`components/review/RejectsList.jsx`, `#qRejects`): `/api/review/rejects` when Quality
  opens; each line has the chip, Approve instead and Undo.
- Without the live server a reject still records its reason in the proposal (BL-133's way); guesses, changing a reason and Approve
  instead say they need the server.
- Help (Review steps 11 and 12, the keys table, the icons table, the Review reference) and `dev/dashboard-spec.md` updated; guides
  rebuilt.

## Tests

- New `dev/tests/test_rejects_ui.py` (Chrome, 10 tests, one per Done-when point): selection and the bar; every way in opens the
  menu (✕, ▾, R, Shift+R, the bar, Shift+F10, the peek; Esc and focus return; `aria-expanded`); 1–7, G and 0 with the right
  reasons in the proposal, `rejected.reason` and `D.quality`; the guesses shown and used by G (with `duplicate_of`); a batch's
  Undo; the chip changes the reason (Duplicate asks for the item; a bad ID is refused), Undo puts it back, the record is updated
  in place, leaving Review clears the rows; Approve instead (one step, Undo rejects it again with its reason; a new risk goes back
  to Review and opens); Activity's list (chip, Undo, Approve instead); Duplicate asks / Don't name it / a known look-alike; 320 px
  with no sideways scroll and no "VIP".
- Updated for the new behaviour (R and ✕ open the menu; the bar's label): `test_reject_reasons` (ReasonMenu's menu test now checks
  BL-315's menu), `test_review_triage` (the bar label, Reject then 0, the message), `test_context_menu` (the menu's labels),
  `test_icons` (the bar and the row's ✕ name), `test_work_item_peek` (the peek's Reject then 0).
- Passing: those, plus `test_rejects_real_life`, `test_review_focus`, `test_review_nesting`, `test_review_project`,
  `test_bulk_edit`, `test_snapshots`, `test_dashboard_split`, `test_help`, `test_help_loop`, `test_ui_sweep`, `test_motion`,
  `test_record_commands`, `test_dashboard`, `test_quality`, `test_activity_undo`; `check.py` OK. The one red is main's
  date-dependent `test_work_item_peek` Rules test (`test_empty_title_bad_date_and_priority`), as on main today.

## Goldens re-recorded (BL-254; BL-315's intended screens only)

- `review.html`: the bar's Reject with a reason (R) and no ▾ beside it; the rows' ✕ named "Reject, with a reason" with
  `aria-haspopup`; the guess on a row; the hint line (R is reject with a reason; Shift+R gone).
- `activity.html`: Quality's new "What you rejected" heading, note and (empty until opened) list box.
- `work-panel.html`: the peek's Reject has `aria-haspopup="menu"` and `aria-expanded`.

## Overlap with v192-sidebar (the rail)

No shared logic. Both touch `core/nav.js` (this branch: `go()` leaving Review clears the greyed rows; the sidebar: `setRailView`
in place of the rail's `aria-current` lines; different lines, plus one import each), `core/server.js` (this: the `api()` read
list; the sidebar: `renderBadge`), `main.js` (exports and a boot call), `shell.html` (Review's bar and Activity's Quality vs the
rail), `style.css` (new rules in different places), `help.md` (Review vs the sidebar's section), `globals.json` and the generated
`dashboard.html`. Merge either first; on the second, take both sides, then rebuild with `split_dashboard.py build` and
`build_dashboard_js.py globals`, and rebuild the guides.
