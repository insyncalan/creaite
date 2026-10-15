# v1.9.3 Sneak peek (BL-322): the screen

Team 2, branch `v193-sneak-peek-ui` (from `origin/main` + `origin/dev-bl322-sneak-peek`). Built as drawn in
`dev/mockups/sneak-peek-mockup.html`, strictly to `dev/sprints/BL-322-contract.md` (re-read at the end; its one "Changed:" line,
`refused.where` and `busy`, is used). Not pushed.

## Merges in this branch (read before merging)

- **`origin/v19-draft-chase` is merged in** (BL-298). The sparkle sits left of Draft chase and "chase Tom, firmer" hands over to
  it, so the screen needs the pane; `v19-draft-chase` is "Ready" for v1.9.0, so it lands on main first anyway and git sees the
  same commits.
- **`v193-sneak-peek-server` is merged in (local)** to test end to end: every Chrome test here runs against the real
  `/api/sneak/read`. Merge order as agreed: v1.9.0's `v19-draft-chase`, then the server branch, then this one.

## What was built

- **`src/components/peek/SneakPeek.jsx`** (Preact, COMPONENTS.md: JSX-only text, icons as element data, JSDoc types): the box.
  The output (`#spOut`, polite live region): the words with what was understood marked (`.sp-mark` buttons; a click takes the
  stretch out and reads again), then one card: the change (from → to, a derived priority "worked out", "Understood in plain code"
  or "Read by Claude"), a new item ("ID given when applied") or a link, the optional closing update, leftover problems; a pick list
  for two people of one name; a refusal with its `where` and a button to go there; quick facts (read only); go somewhere; the
  chase hand-off; a Claude-only draft (or, with AI drafts off, why). Input row: the sparkle, `#spIn`, "Esc close".
- **`src/sneak.js`**: opening and closing, the keys, the hosts in the peek (`#pkSneak`) and the milestone editor (`#mvSneak`, kept
  across `mvEdDraw`'s whole redraws by `sneakMvAttach`), the room kept under the scroll area (`--sp-h` from a ResizeObserver), and
  the save path (`sneakCommit`: `stage.items` as one dashboard proposal with the peek's file name and `peek` envelope, into
  `PKS`, applied at once with `applyNow({peek:true})`, `pkReconcile`; Undo is `/api/undo {apply_id}`).
- **Opening:** `//` outside a field (window-capture keydown; the first `/` waits 330 ms, then is replayed on `document`, so ask
  creaite, Activity's and Settings' own `/` work as before); the sparkle `#pkSneakBtn` immediately left of `#pkChaseBtn`
  (`#mvSneakBtn` before Close in the milestone editor); the foot line "// Change this item in words". Only an action, RAID item or
  decision in record mode, or an existing milestone; not a proposal, a new item, or while Draft chase is open.
- **Keys:** Enter makes a plain change; the confirm list (amber, `#spNeed`) takes ⌘⏎ (the box is first in `CMDENTER`) or a click,
  never plain Enter; Esc closes the box only (the peek's and the milestone editor's Esc leave `.sp-box` alone) and returns focus;
  ↑ in the empty box recalls the last instruction (kept across items).
- **Claude:** `/api/draft` through `draftAsk` (Stop while it runs), Yours beside Drafted, Keep mine or Use this (Enter), counted
  with `draftStat`; `sneak-update` is under Draft the latest update's switch (`DRAFTKIND`).
- **Small edits elsewhere:** `panel.js` (`chaseOpen(start)`; Esc exclusion for `.sp-box`), `ChasePane.jsx` (`start` → its first
  `opts`), `milestones.js` (one call in `mvEdDraw`), `main.js`, `style.css` (block `BL-322`; tokens only; at ≤600 px the peek's
  Expand is hidden, as the peek is full width there, so the toolbar fits 320 px), `globals.json` (regenerated).
- **Docs:** Help (a How do I… card "Change an item in words (Sneak peek)", `/ /` in the keys table, the Sparkle in the icons
  table; the How-To guide rebuilt) and `dev/dashboard-spec.md` (a "Sneak peek" section; the toolbar line).

## Tests

- **`dev/tests/test_sneak_peek_ui.py` (new, 25 Chrome tests, real server):** the sparkle's place, name, key and icon; not for a
  proposal or a new item; `//` opens, one `/` opens ask creaite after the wait; neither in a field; the foot line, Esc (peek stays
  open, focus back), the sparkle's second press; room kept for the box; an action's owner and due date (marks shown), Undo, priority,
  ↑; closing with a closing update; a risk's impact (derived priority), likelihood and response; a decision's needed by, revisit and
  decision maker; a milestone's forecast and owner (the box survives the editor's redraw; Esc keeps the editor); a mark taken back
  out; an update and a label; a follow-on action with its `@1` link and one Undo removing both; the confirm list (plain Enter makes
  nothing, ⌘⏎ does; a click does; risk → issue; a milestone state); two Sams asking which; a refusal pointing to Draft chase and
  changing nothing; quick facts; "chase Sara, firmer" opening Draft chase in Firmer; Keep mine and Use this with the stand-in
  Claude; AI drafts off saying why while a plain change still works; 320 px with no sideways scroll; no "VIP".
- `test_cmd_enter.py`: the expected `CMDENTER` names gain `sneak`.
- **Passing:** test_sneak_peek_ui, test_sneak_peek_read, test_snapshots, test_dashboard_split, test_help, test_help_loop,
  test_ui_sweep, test_draft_chase, test_draft_chase_pane, test_cmd_enter, test_milestone_ui, test_tracker, test_live_server,
  test_dashboard (and its data, editing and milestones files); `check.py`: OK (type check 0).
- **Failing, not from this branch:** `test_work_item_peek.py` › `Rules.test_empty_title_bad_date_and_priority` fails the same way on
  `origin/main`'s own dashboard (checked by swapping the built page): "+3d" from Wednesday 14-10-2026 lands on Saturday, and the
  weekend question holds the change, so `PKS.length===1` never comes. Date-dependent; it will pass again from tomorrow.

## Goldens

- **`work-panel` re-recorded** (the sparkle in the toolbar, the foot line and the empty box host). No other golden changed.

## Added after the first report (Alan: "complete as drawn")

- **`@` pick list:** `@` opens a listbox of people (the register less hidden people, then other item owners; up to six, with the
  organisation, never a VIP label), filtered as you type; ↑ ↓, Enter, Tab or a click picks ("@Full Name "), Esc closes the list
  only. `#spIn` is a combobox with `aria-activedescendant`; a polite line says how many match; "No one … matches" when none does.
- **Changed-field flash:** after a change (and after Undo) the changed fields fade from `--warn-soft` over 1.6 s (`.sp-flash`, put
  back after a redraw). Under reduced motion it holds still, through the one `prefers-reduced-motion` rule (and
  `data-motion="reduce"`). The earlier `no-preference` block for the box's rise is gone (test_motion allows one rule).
- **Tests:** 7 more in `test_sneak_peek_ui.py` (PeoplePicker 4, Flash 2, FlashReduced 1): 32 in all. No golden changed.

## Open

- A marked word is taken out by its stretch only; tidying the joining words ("and", commas) is a best effort in the screen.
