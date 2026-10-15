# v18-fold: note for the Scrum Master

From the second laptop, 12-10-2026. **This touches `system/templates/dashboard.html` while v1.7.0 is still open, at Alan's request.**

Alan ruled that the two bugs in `dev/archive/notes/v1.8.0/V18-HANDLERS-NOTE.md` are bugs to fix, here, as the first commits of BL-231 phase 2. The branch is `v18-fold`, from `origin/main` at `3764b02`. No wrapper has been folded yet: these two commits only make two controls run the full function, so that the fold has nothing left to decide for them.

## The two commits

| Commit | Change | Lines in `dashboard.html` |
|---|---|---|
| `255503a` | **Panel Close** (`#pClose`): `onclick=closePanel` becomes `onclick=()=>closePanel()`, as `#pCancel` and `#pkClose` already are. The capture listener that patched BL-219's peek draft for Close (old L8704) is removed, because the wrapper now does it | 1 changed, 1 removed |
| `59da8ec` | **Search button** (`#searchBtn`): `onclick=openCk` becomes `onclick=()=>openCk()`, as its Enter key already is | 1 changed |

**Behaviour that changes, on purpose (each now matches Cancel, Esc, Enter and ⌘K):**
- **Close drops an unused health-reason draft.** It counts it as `reason: rejected` (BL-226), so the draft isn't shown again.
- **Close moves focus out of the closed panel** (BL-176), and runs the BL-167, BL-177, BL-179 and BL-219 steps.
- **Close writes the address bar for a record panel,** like Cancel and Esc. Before, the click event reached `closePanel(quiet)` as a truthy `quiet`, so Close alone skipped `navWrite`.
- **A click on Search starts with no earlier "which one?" pick** (`CKPICK = {}`, BL-205).

## Checks

- **New test:** `dev/tests/test_early_bound_controls.py` (Chrome tier, stand-in Claude). Run against unfixed main, both of its tests **fail**, with the kept draft and the kept pick. On this branch both pass.
- **The other test files that mention these controls or functions:** 33 passed, 0 failed locally at `-j 2` (435 s), including `test_snapshots`, `test_cmdk_change`, `test_dashboard_editing`, `test_side_panel_live` and `test_work_item_peek`.
- **`check.py`:** OK.
- **`wrappers.py`:** 245 wrappers, unchanged. Early references are down from 21 to 19: `closePanel` and `openCk` are gone.

## Carried over from `dev/V18-PREP-NOTE.md` (removed on this branch)

That note's branch is merged and its decisions are settled:
1. `check.py` counts 245 real wrappers (`3ef9e5c`).
2. The six early-bound handlers are dealt with by `dev/archive/notes/v1.8.0/V18-HANDLERS-NOTE.md` and the two commits above.
3. Still open for the fold, see below.
4. The guide's `npx -p` command is fixed.
5. The 241 figure is superseded by 245.

What's still open for the fold:
- **Five functions are replaced outright, then wrapped:** `pkWrite`, `pkStOpt`, `pkTextRule`, `pkIs` and `openNew`. Their first definitions are dead code. The fold keeps the replacement and drops the dead original.
- **Two handlers are bound twice, harmlessly:** `#askBtn` and `#mtgRefresh`. `wrappers.py` still lists them as early references. In the fold, keep the later binding and drop the first.

`dev/LAPTOP-2-WORK.md` item C still points to the removed note, which stays readable in git history (`git show 3764b02:dev/V18-PREP-NOTE.md`).

## For you

- **Merging:** the edit is three lines, in places v1.7.0's sprints are unlikely to touch: the `#pClose` binding after `closePanel` (around L4678), the L8704 listener, and the `#searchBtn` binding (around L6951). It should merge cleanly into main now, or into v1.7.0 if you'd rather ship the two fixes there.
- **The rest of phase 2 (folding) hasn't started.** It still waits for your three confirmations in `dev/archive/V18-LAPTOP-GUIDE.md`: v1.7.0 released, BL-254 goldens on main, nobody else editing `dashboard.html`.
- **This branch stays open for the fold.** Merging these commits now and continuing on `v18-fold` later, with main merged in, is fine.

## Phase 2: the fold, done (13-10-2026)

Every in-place wrapper is folded into its function, in the function's original place, with its steps in the order they ran. `wrappers.py` reports 0 chains and `dev/check-baseline.json` has `wrappers: 0` (245 at the start). One commit per batch, in the plan's order, and one for the load-time settlement:

| Commit | What | Wrappers |
|---|---|---|
| `bd06444` | Batch 1: fold 20 one-step wrappers | 245 → 225 |
| `2a3a850` | Batch 2: fold 20 one-step wrappers | 225 → 205 |
| `75bb782` | Batch 3: fold 20 one-step wrappers | 205 → 185 |
| `34e904f` | Batch 4: fold 19 wrappers | 185 → 166 |
| `0d273f2` | Batch 5: fold the two-step chains | 166 → 146 |
| `8151b5f` | Batch 6: fold 20 wrappers and the replacements | 146 → 126 |
| `f5254c9` | Batch 7: fold the three-step chains | 126 → 108 |
| `f3f2daf` | Batch 8: fold the four-step chains | 108 → 89 |
| `dd2ce37` | Batch 9: fold renderReview, closePanel, renderPerson, openChat | 89 → 69 |
| `1b56542` | Batch 10: fold the navigation and load-time chains | 69 → 49 |
| `e11e400` | Batch 11: fold parseHash and renderToday | 49 → 39 |
| `4b7d7c6` | Batch 12: fold drawPanel | 39 → 29 |
| `3757fc4` | the address restored at load runs as it did (mid-chain settlement) | — |
| `35bcda5` | Batch 13: fold renderWork | 29 → 20 |
| `6748eed` | Batch 14: fold renderCockpit | 20 → 9 |
| `d8d0cc5` | Batch 15: fold go | 9 → 0 |

**How each batch was checked:**
- `check.py` passes and its baseline is lowered.
- **Screen snapshots:** every screen recorded into a scratch folder for the batch and for the base commit (`e933759`) and compared: byte for byte the same every time. No golden was touched. Note that `test_snapshots` itself fails on the base commit too since 13-10: Today's "Resolved since 12th October 2026" takes the real date (`LASTVISIT`), not the pinned one. A fault in the snapshot set-up, for another sprint.
- **Every test file that mentions a folded function** (by name, or `go(` for `go`), at `-j 1`. `test_weekend_dates`, `test_writer_pinned` and `test_cmdk_change` fail, the same way, on the base commit (they depend on today's date); everything else passes.
- **A load probe** (scratch, not committed): the page loaded in headless Chrome at 21 addresses (each then followed by Today and Work), every snapshot screen and 23 interactions, and the whole `<body>` compared with the base commit's; and a loop that loads the page at those addresses, in the live and the file version, on a first visit and with a peek change staged in the vault, and reports any error. The probe found the load-time cases below; the tests found three more (`test_help`, `test_peek_fixes`, `test_work_filter_picker`), now fixed.

**The open points from before:**
- **Replaced, then wrapped** (`pkWrite`, `pkStOpt`, `pkTextRule`, `pkIs`, `openNew`): the replacement is kept, in the original's place, with its wrappers folded in; the dead first version is gone.
- **Bound twice** (`#askBtn`, `#mtgRefresh`): BL-211's own `#askBtn` and `#chatClose` bindings are kept and the first ones dropped; `#mtgRefresh` keeps its first binding and BL-263's rebinding is gone. `#qcCancel` stays bound to `qcClear`, which now forgets the unsent note itself, and the listener that copied that step is gone. `sizeList` runs `xcueSoon`; `xcueSoon`'s own resize listener stays.
- **A wrapper `check.py` didn't count:** BL-211's `closeChat` (in a `const oc=openChat, cc=closeChat` block) is folded too.

**Mid-chain references: what runs during the page's load.** The page restores the address it was opened at (`restoreNav` → `go` → the view's renderer, and Help on a first visit) early in its load, before most later blocks had added their steps; a few blocks then draw again (the panel, the cockpit, Today). Folded, those calls would get every step: some read state declared further down (a `let`/`const` read too early stops the page, depending on the data: a stale action, a weekend date, a client-visible item, an unsaved panel draft), some use parts of the page built later, and some draw or store what the page drew or stored only later. Settled, kept exactly:
- **`LOADING`** (declared near the top) is true while the address is restored and Help opened at load. The steps added after that point check it, so those calls run exactly as before: about 40 steps, in `go`, the renderers (Today, Work, Review and its rows, a person, the cockpit, Activity, Projects, the day line, Meetings, Files), the panel (`drawPanel`, `openRecord`), `hlPaint`, `rvPaint`, `hlBar`, `sizeList`, `status` and `renderAskChanges` (read as it starts: it is async).
- **Ready checks the page already had, or that a block sets:** BL-245's steps wait for `MVREADY` (refreshAll's milestone step, `go`'s closing of a milestone peek); the peek is drawn once its `#pkScroll` exists, `closePanel`'s new-item step once `#pkAsk` exists; the cockpit's Draft all once its kind is registered (`DRAFTKIND["client-bulk"]`).
- **The first restore doesn't parse milestone or meeting addresses**, as before BL-245 and BL-233 taught `parseHash` them: the Milestones page is restored by its own block, and a meeting address still opens Today (BL-233 never restored it at load: a fault, kept).
- **About 30 declarations are moved up**, each marked "declared before …, which runs at load": plain values or small arrows read by a function that a later draw at load runs. Nothing else moved.

**What still differs from the base commit at load (for Alan to rule on):**
- **Close the day's door icon.** Today is drawn again at load, after the restore and before BL-205 added its step, so on the base commit the button stays empty after a load or reload until Today is drawn again. Folded, it has its icon from the start. Keeping the fault would need a guard of its own.
- **Not visible:** opened at `#milestones=…`, the hidden Today's Getting started card gets BL-165's wording and buttons at load; it is drawn again, the same as before, when Today opens.

**Found on the way, not changed (each the same on the base commit):** opened directly at `#review`, Review's rows lack BL-186's Project button, BL-225's Draft a response and BL-206's One at a time until Review is drawn again; opened at a project page, its Client messaging card lacks Draft all until it is drawn again; a `#meeting=…` address opens Today. Each is the same kind of fault as the door icon (a later step never drawn at load), kept exactly because they are on the restore path.

**Left over:** nothing. One thing to watch: now and then a probe run's Diagnostics listed `POST /api/pulse 500`. The page sends the same request as on the base commit (`{}`), the same page passed on a rerun each time, and `pulse_route` reads files that may be mid-write, so it looks like a race in the live server; it was not seen in the base commit's three runs.
