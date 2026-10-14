# v18-handlers: the six early-bound handlers (BL-231 phase 2 preparation)

From laptop 2, 12-10-2026, item C of `dev/LAPTOP-2-WORK.md`. **A report only: nothing under `system/` changed.** It settles decision 2 of `dev/V18-PREP-NOTE.md`. Alan decides which are bugs; each fix is its own commit, outside the fold.

Line numbers are `system/templates/dashboard.html` at `a3e7125` (origin/main; the local `main` ref on this laptop was one merge behind, at `3ef9e5c`, where `wrappers.py` fails with `check.WRAPPER`).

## The answer

- **Two are bugs:** the **Close** button on the side panel (`#pClose`) and the **search button** (`#searchBtn`). Each skips a later feature that every other way in still runs.
- **Two were already put right in the page:** `#askBtn` and `#mtgRefresh` are bound again after their wrapper, so the click runs the wrapped function today. `wrappers.py` reports them as early only because it sees the first binding.
- **Two are compensated:** `#qcCancel` and the `resize` listener. A second listener does what the wrapper adds, so the result is the same.

## The table

| Control | Bound at | What the wrappers add (BL) | Today, from the control | Bug or intended | Recommendation |
|---|---|---|---|---|---|
| `#pClose` → `closePanel` (6 wrappers) | L4675 | **BL-167** L8697: drops the stored unsaved edit. **BL-176** L8809: blurs focus in the panel, removes `peek`, resets the peek. **BL-177** L9270: clears `PK.dirty` and `pkprop`. **BL-179** L9461: asks "keep or discard?" for an unsaved new item. **BL-219** L10595: drops the peek's draft. **BL-226** L10736: counts a health-reason draft that wasn't used as `rejected` and forgets it | Runs the original. BL-167 is copied by a capture listener at L8698. BL-177, BL-179 and BL-219 can't be reached: `#pClose` is hidden in the peek (CSS L1682), and it shows only on panels that aren't the peek. In the sample, that is the project health form; a proposal of another kind would also qualify. **Skipped:** BL-226 and BL-176's blur | **Bug** (BL-226; BL-176 minor) | Bind `#pClose` to the wrapped `closePanel` (`()=>closePanel()`, as `#pCancel` and `#pkClose` are). Then delete the L8698 capture listener, which would drop the draft twice and no longer protects anything. The test is under "Tests" below |
| `#askBtn` → `openChat` (1 wrapper) | L6375 | **BL-211** L6389: records where focus was (`CHATFROM`), so closing the chat gives focus back | **Already rebound** at L6397 to `e=>{ openChat(); if(!CHATFROM) CHATFROM={el:#askBtn…} }`, which calls the wrapped function. In Chrome: `CHATFROM` is `askBtn`, and after Esc focus is on `#askBtn` | **Intended**: already fixed | No fix needed. In the fold, remove the dead first binding at L6375 and keep L6397. `test_chat_focus_return.test_ask_button_by_pointer` covers it |
| `#qcCancel` → `qcClear` (1 wrapper) | L7171 | **BL-157** L8646: forgets the unsent Quick capture note kept in this browser (`creaite-qc-draft`) | Runs the original, then a second click listener at L8647 clears the same key ("Clear is wired to the original qcClear"). In Chrome, Clear and `qcClear()` give identical results: the stored note goes from the typed text to `""`, the field is empty and the form is closed | **Intended** (compensated) | In the fold, bind the folded `qcClear` and delete the L8647 listener together. Covered by `test_ux_sweep_fixes.test_quick_capture_keeps_an_unsent_note` and `test_today_brief` (both click `#qcCancel`) |
| `#searchBtn` → `openCk` (1 wrapper) | L6947 | **BL-205** L11167: starts each ⌘K with no earlier "which one?" pick (`CKPICK={}`) | **A click** runs the original and keeps the last pick. **Enter on the same button** (L6947, `onkeydown` calls `openCk()` by name) and **⌘K** (L6980) run the wrapped one. In Chrome, with an earlier pick of Sara Example for "the vendor": after a click, `ckPerson('the vendor')` still gives Sara Example. After Enter, ⌘K or `openCk()`, it gives "the vendor" (unknown), as BL-205 intends | **Bug**: the one control's click and key disagree | Bind the click to the wrapped `openCk` (`()=>openCk()`). The effect is small: a stale pick is reused only if the same words are typed again, but the change it stages could then be for the wrong person or item without asking. No test clicks `#searchBtn` |
| `#mtgRefresh` → `refreshCalendar` (1 wrapper) | L7815 | **BL-136** L8490: shows a loading skeleton if the refresh takes more than 150 ms, then fades the list in | **Already rebound** at the end of the wrapper (L8491: `$("#mtgRefresh").onclick=refreshCalendar`). In Chrome, `onclick===refreshCalendar` is true, and a click with a 400 ms stand-in run shows the skeleton | **Intended**: already fixed | No fix needed. In the fold, keep one binding after the function. `test_meetings` clicks Refresh but only checks the request, not the skeleton |
| `resize` → `sizeList` (1 wrapper) | L3513 | **BL-165** L8727: after sizing the Work list, schedules the "wider table scrolls" cue (`xcueSoon()`) | Runs the original. `xcueSoon` has its own `resize` listener (L8725), and a `ResizeObserver` on `#workWrap` calls the wrapped `sizeList` (L8728). In Chrome, narrowing the window to 700 px on Work gives `hscroll` on the frame and one `.xcue` cue. `getEventListeners(window).resize` lists the original `sizeList` and `xcueSoon` separately | **Intended** (compensated) | No fix needed. In the fold, the folded `sizeList` calls `xcueSoon` and the separate listener can stay: `XCQ` keeps it to one per frame. No test resizes the Work list |

## What Chrome showed for `#pClose`

These checks used the sample vault (`populate`) and a live server on a free port in headless Chrome. `draftStat` was replaced with a recorder, and a health-reason draft was planted in `DRH`, as BL-226 leaves it when a draft comes back.

| On ABC's health form, closed by | Draft counted | `DRH` afterwards | Reopening the form shows the old draft | Focus afterwards |
|---|---|---|---|---|
| **Close** (`#pClose`) | nothing | still set | **yes** | `#pClose`, inside the closed, zero-width panel |
| Cancel (`#pCancel`) | `reason:rejected` | cleared | no | `<body>` |
| Esc | `reason:rejected` | cleared | no | `<body>` |
| `closePanel()` | `reason:rejected` | cleared | no | `<body>` |

Close is the only way out that skips BL-226. Its draft is never counted, so `draft-stats.json` under-counts rejections, and it reappears the next time the form opens for that project. Close also leaves focus on a hidden button in a closed panel, which BL-176 says shouldn't happen.

Where `#pClose` can be pressed (`display` and panel open):

| Panel | Visible |
|---|---|
| action record (peek) | no |
| new action (peek) | no |
| milestone (opens the Movement peek) | no |
| project health | **yes** |

Because of this, the L8698 capture listener for BL-167 is dead code: BL-167 keys only actions, RAID items and decisions, and those always open in the peek.

## Tests

None of the existing tests would notice a change to the two bugs. Nothing clicks `#pClose` or `#searchBtn`. The fix commits should add:
- **`#pClose`:** on a health form with a draft, Close records `reason:rejected` and the reopened form has no draft.
- **`#searchBtn`:** a pick doesn't survive a click on the button.

## For phase 2

- `wrappers.py` lists `#askBtn` and `#mtgRefresh` as early references at load, but both are bound again later. Treat them as settled.
- The fold needs to keep only the final binding for each.
- If Alan rules `#pClose` and `#searchBtn` as bugs, fix them on main first. Then all six fold with "identical behaviour".
