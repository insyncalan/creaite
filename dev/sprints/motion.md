# Sprint motion: restrained animation across the dashboard (BL-136)

Branch `sprint-motion`, worktree `../creaite-motion`, from `main` **after `sprint-work-views` and `sprint-all-items` have merged** (and so after `sprint-polish`, `sprint-settings` and `sprint-prep-files`). One sprint in three stages, because every item adds small hooks to the same `dashboard.html` functions the Work, Review, Today, Portfolio and ask creaite code already owns. Rough size: six to eight days (38 items; Alan has seen the size and wants it left as it is).

**The design is `dev/mockups/motion-mockup.html`** (38 live examples, each with its timing, where it lives in creaite, and its reduced-motion behaviour). Open it first, with **Slow ×3** and **Reduced motion** to hand. Then read **BL-136 in `dev/BACKLOG.md`**: it holds Alan's decisions and the 38 numbered items this brief follows. Where the mock-up and the backlog differ, the backlog wins; where the code and the backlog differ, say so in BUILD.

**Out of this sprint:** the **Board card move** animation (Alan excluded it: a card move, a lane move and a drop swap instantly, as now). Of the drag feedback, only the **card lift and the target highlight** are in (item 33); a drop placeholder is not. Confetti, parallax, bounce, page-wide fades and any idle loop beyond those the backlog lists.

## Before starting

1. `git worktree list` shows `sprint-polish`, `sprint-settings`, `sprint-prep-files`, `sprint-work-views` and `sprint-all-items` gone, and `git log main` has all five. If any is not merged, stop and say so. `sprint-all-items` must merge first (Alan's order, on the board): the All items tab and the People page's two tabs are then animated with the rest. (Stage A touches only the stylesheet and a helper block, so Alan may allow it to start earlier; ask, don't assume.)
2. Bring `main` in. Read what the Work views sprint actually built: the Display menu, group headers and swimlanes, the empty state, the saved-view chips and Review's bar. Items 3, 5, 12, 13 and 14 attach to those.
3. Read the existing motion in `dashboard.html`: `grep -n "prefers-reduced-motion\|@keyframes\|animation:\|transition:" system/templates/dashboard.html`. Today that is the spinner (`sp`), the ask pulse (`askpulse`), the ask button's hover and a handful of 100–150 ms transitions, each with its own reduced-motion rule. Fold these into the new tokens and the one reduced-motion rule; don't leave two systems.
4. Run `test_dashboard.py`, `test_work_board.py`, `test_work_filters_live.py`, `test_decisions_board.py` and the Review and ask creaite tests first, to know what passes.

## Items

Commit each separately, in this order, on `sprint-motion`. The numbers are BL-136's.

### Stage A: foundation and feedback (S–M)

**1. Tokens, the reduced-motion rule and the helper block, first (everything else uses them).**
- CSS tokens on `:root`, once, in the base theme block (the other themes inherit them): `--d1` 120 ms, `--d2` 200 ms, `--d3` 320 ms, `--d4` 520 ms; `--out` cubic-bezier(.2,.7,.2,1), `--inout` (.65,0,.35,1), `--in` (.4,0,1,1). Durations are multiplied by a `--k` (default 1) so a test or a "slow" debug switch can scale them; do not expose `--k` as a user setting.
- **One** `@media (prefers-reduced-motion: reduce)` rule that collapses every animation and transition (the mock-up's rule), replacing the scattered ones. Colour and ticks may stay as 0-duration changes.
- The helper block, one marked section, about 40 lines, no library: `reduced()` (reads the media query once and on change), `anim(el, keyframes, opts)` (Web Animations API; duration 1 ms when reduced), `countUp(el, to, ms, decimals, suffix)`, `flip(els, mutate)` and `slideDown(el)`, as in the mock-up. Every scripted effect goes through `anim` so reduced motion is honoured in one place.
- **Existing smooth scrolls:** `grep -n "behavior:\"smooth\"" system/templates/dashboard.html` finds two `scrollIntoView` calls. A script's explicit smooth scroll ignores the CSS rule, so both go through the helper (`scrollTo(el, opts)`: instant when reduced, smooth otherwise). Scrolling from J/K, and any repeated key, is always instant.
- **In-app Motion setting:** a control on the Settings page (in whichever category BL-115 gives appearance and display; look first): **Follow system** (default), **Reduce**, **Full**. It is saved with the other dashboard settings (`settings.json`, default added to `settings-defaults.json`, read like the others), applied as `data-motion="reduce"` on `<html>` before first paint, and `reduced()` reads it as well as the media query. "Full" overrides the system setting only for creaite's own non-essential motion; say so in its hint. The tests and the Help screenshots use "Reduce".
- Test the rule here: with reduced motion emulated (DevTools `Emulation.setEmulatedMedia`), walk every page and assert that no element has a non-zero computed transition or animation duration, apart from none being allowed to loop.

**2. Press, hover and focus (BL-136 item 2).** Buttons lift 1 px on hover and press to 98%; inputs grow a 3 px soft ring on focus. Applied once through the shared button and input classes, not per button. Keep the existing focus outline (it is the accessibility cue); the ring is an addition.

**3. Sliding indicator (item 3).** One moving element under the List | Board switch, the Work tabs (including the **All items** tab), the People page's two tabs and the Settings categories. It must recompute on resize and when a tab's label changes (a count arriving), or it will sit in the wrong place.

**4. Tick and bulk bar (item 4).** The checkbox tick draws in (BL-122's selection); the BL-124 bar rises when the first row is selected and leaves when the last is cleared. The bar never blocks a click while moving.

**5. Filter chips (item 5).** Scale in 200 ms; close up on removal 160 ms. Applies to Work filters and saved view chips (BL-130, BL-131). **Restoring a saved view that changes many chips at once does not animate.**

**6. Switch and save (item 6).** The Settings switch settles with a 4% overshoot; a save shows spinner, a drawn tick, then the label returns. The tick state must follow the real save result, including a failure (no tick; the existing error stays).

**7. Ask button sheen (item 7).** One light sweep on hover; nothing idle.

**35. Copy confirmation (item 35).** Copy diagnostics, the pasted copy commands, copy a link and the Draft email subject: the label swaps to a drawn tick and "Copied" for 1.4 s, then returns. It reuses item 6's tick component, and a polite live region announces "Copied" (WCAG 4.1.3). The copy itself must not wait for the animation, and a failed copy shows the existing error, not a tick.

**37. Theme switch fade (item 37).** Changing theme or light and dark in Settings: add a `themefade` class to `<html>` for about 300 ms around the change so surfaces and text cross-fade over 200 ms (background, colour, border and shadow only), then remove it so ordinary hovers are not slowed. Never on first load or when the page is first painted in the saved theme. Applies to all seven themes. Reduced motion: instant.

### Stage B: overlays, lists and structure (M)

**8. Menus and popovers (item 8).** Display, the field picker, row actions, Move to…: 200 ms in from 4 px above at 97%, anchored to the button; 150 ms out. Use `@starting-style` and `transition-behavior: allow-discrete` where the menu uses `display` or `popover`, so no script timing is needed; check each browser the dashboard supports (Chrome and Edge, per the rules). Focus handling and Esc are unchanged.

**9. Detail panel (item 9).** 320 ms in from the right with the scrim, 240 ms out; its lines follow at 40 ms steps (capped at 8). Opening the panel from a click on an ID (BL-122) must not feel slower: the content is interactive from the first frame.

**10. Dialogs (item 10).** Move, Apply and Undo confirmations, Reconnect vault: 97% to 100% with a 4 px lift and scrim fade, 320 ms; 200 ms out.

**11. Toast with Undo (item 11).** Rises 320 ms; a thin timer line shows the Undo window; leaves in 200 ms. **One toast at a time**: a new one replaces the old at once. If the app already has a toast or message line, restyle and animate that; don't add a second mechanism.

**12. Approve or reject a row (item 12).** In Review the row tints green or red (200 ms), closes up (240 ms), and the Undo toast returns it. **A bulk approval, Approve routine, Approve all and any batch over about 12 rows skip the motion** and swap straight away. The tint is never the only cue (the toast and the count still say what happened).

**13. Reorder on sort (item 13).** FLIP, 320 ms, ease-in-out, on re-sorting a Work list, Review or the Chase view. Capped at about 30 rows (instant above). **Not on the Board:** a card move, a lane move and a drop are not animated (Alan's exclusion); test that they are not.

**14. Group collapse (item 14).** BL-129's groups and swimlanes, Settings sections and Prep: `grid-template-rows` 0fr to 1fr over 320 ms with the chevron turning. The collapse state is still remembered as BL-129 specifies; the animation never changes what is selected (BL-129's rule that a range never reaches collapsed rows holds while the animation runs).

**33. Board drag: card lift and column highlight (item 33).** On pick-up the card lifts (scale 1.03, soft shadow, 120 ms) and the dragged copy follows the pointer as the board does now; the column or swimlane under the pointer gets a soft wash and an accent edge (120 ms); on drop both settle and the card **lands at once, with no glide** (the move itself stays un-animated, as Alan excluded). A column that cannot take the drop (FR-110's rules for Decisions, a locked lane) **does not light up**, and whatever refusal the board shows today is unchanged. Keyboard users have Move to…, which has no lift. Read the board's existing drag code (BL-103, `test_work_board.py` drags with real mouse events) and add classes to it; don't replace the drag. Reduced motion: wash and edge appear, no lift. A drop placeholder is not part of this item.

**34. Review queue cleared (item 34).** When the last item in Review is decided, BL-133's empty-queue summary appears with one circle and tick drawn over about 700 ms and the summary rising 4 px. **Once per clearing**, never when Review is opened already empty or re-rendered. No confetti. Under reduced motion it is shown.

**36. Row hover and the J / K highlight (item 36).** Every Work, Review and Today list: a light hover wash on rows (120 ms, `@media (hover: hover)` only). J and K (and the arrows) move BL-122's highlight by cross-fading the old row out and the new one in over 120 ms (no travelling element, so re-rendered or grouped lists cannot break it). A held key, or a jump of more than one row, is instant. The selection rules of BL-122 and BL-129 are unchanged. The All items tab and the People tabs get the same classes from the shared row code.

**15. Skeleton to content (item 15).** Shimmer only while the live server or a list is loading (Today, Calendar Import, ask creaite history); content cross-fades in over 320 ms with a 4 px rise. The shimmer stops under reduced motion and is never shown for a load that finishes within about 150 ms (no flash of skeleton).

**16. Page change cross-fade (item 16).** The old view fades 100 ms, the new rises 4 px over 200 ms, on the content region only. Use the View Transitions API where it keeps this simple, with a script fallback. Addresses (`#work`, `#settings`) and the back button behave exactly as now.

**17. Scroll-linked header shadow, progress line and item reveal (item 17).** Long Work lists, Prep and reports: CSS `animation-timeline` only, no scroll listeners; feature-detected with `@supports`, static where unsupported. Do not apply the item reveal to the Work lists' rows (they re-render too often); use it for Prep and report pages.

**31. Landing pulse (item 31).** Arriving on a row from Today, a search result, "Show them", Open source or an `openWork` link scrolls it into view (instant when reduced) and gives it one soft highlight: a 3 px accent edge and wash, held about a second, faded over 1.8 s. One function, `landOn(el)`, called by the existing navigation code at the point it already highlights or scrolls to a row; it fires only on arrival, never on a normal render, a sort or a live refresh. If the row is in a collapsed group (BL-129), the group opens first. The highlight is also the row's selection highlight state: don't fight BL-122's.

**32. Banners arriving (item 32).** The red "live server not reachable" alert and a new VIP alert at the top of Today: 200 ms slide-and-fade in (`grid-template-rows` 0fr to 1fr, so the page below eases down with it), 160 ms close-up on dismiss or Seen. A banner that is already showing at page load does not animate. It must never push a click target away mid-click: the animation is on the banner's own height only after the first frame is interactive.

### Stage C: numbers, status, ask creaite and ambient (M)

**38. New since your last visit (item 38).** Work, Review and Today's Needs attention: a small dot on rows created since this browser last viewed that page. It is a presentation of existing timestamps (`created`/`raised`, a proposal's age) compared with a last-viewed time that the page keeps wherever it already keeps view state (check first: the collapse and saved-view code; wrap in try/catch, as the dashboard does). **Nothing is written to the vault, the database or staging; no schema change.** First-ever visit shows no dots. The dot is simply there on render (no entrance); once its row has been on screen about 2 s, or is opened, it shrinks and fades over 600 ms and the last-viewed time moves on when the page is left. Colour is not the only cue: the row carries visually hidden text "New since your last visit". Reduced motion: it just disappears. The All items tab and the People tabs use the same code.

**18. Count-up tiles (item 18).** Today counters, Portfolio tiles, project header counts: 700 ms, tabular figures. **Once on page load, never on a refresh or a live update** (a flag per page view). The final number is in the DOM from the start for screen readers and for tests; the count is visual only (`aria-hidden` on the running text, or set the final value as the accessible name).

**19. Progress bars (item 19).** Milestones, workstreams, Portfolio rows: 700 ms with a 60 ms stagger, once.

**20. Sparkline draw-in (item 20).** Portfolio and project trends: 900 ms, the area and end point fading in after.

**21. Health ring (item 21).** Project card and report cover: ring and number together, 900 ms. The report's Word and PDF output are unchanged (this is the dashboard only).

**22. Changed values flash (item 22).** After an Apply, an Excel import or a live refresh of Today, a changed cell gets a 3 px accent edge and soft wash that fade over 1.4 s, the old value sliding out and the new in. Compare the values before and after a render by key, so only genuinely changed cells flash; the first render never flashes. Skip it above about 12 changed cells and say so in one line instead.

**23. Health change (item 23).** The dot's colour eases (520 ms) and one soft ring leaves it, once. Never on first render.

**24. Today's "now" marker (item 24).** A 2.8 s ripple while the page is open and visible: pause when the tab is hidden (`visibilitychange`), so a background tab does no work. The day's events fade in at 80 ms steps on first paint.

**25. Sweep and run progress (item 25).** A hairline slides under the header while a run is alive (sweep, minutes, report drafting); each step spins, then ticks; the hairline fades when the run ends or is stopped. Wire it to the live server's run engine (the same state that shows progress and Stop today), not to a timer. It also stops if the server becomes unreachable.

**26. ask creaite (item 26).** Typing dots wave while Claude works; the reply's words fade in at 25 ms steps with a trace of blur. **Live replies only**, never the history, a re-opened chat or a reply longer than about 400 words (that one appears whole). The chat's scroll position stays where the reader left it (BL-120); the animation must not call `scrollTo` or change layout height as words arrive.

**27. Staggered reveal on first paint (item 27).** Today only: tiles, then Needs attention rows at 40 ms steps (capped at 8), then the day. Under a second in all, never repeated on a refresh or when returning to Today from another page.

**28. Cursor spotlight card (item 28).** Alan agreed: **one hero card at most**, the first project card on Portfolio. A soft radial wash follows the pointer, fades in over 320 ms. Pointer devices only (`@media (hover: hover) and (pointer: fine)`). It never carries information and never appears for keyboard focus.

**29. Rotating gradient border (item 29).** The ask creaite input only, and **only while it has focus** (a 5 s turn using a registered `@property --ang`); a plain line otherwise. Where `@property` is unsupported, a static accent border. Reduced motion: static accent border.

**30. Floating empty-state icon (item 30).** Empty Review, empty Work results (BL-132) and an empty inbox: a 6 px, 5 s float that **stops after ten seconds** and rests (Alan agreed the cap on 09-10-2026). Implement with `animation-iteration-count: 2` (two 5 s cycles) rather than script. Reduced motion: no float.

## Decisions taken (Alan, 09-10-2026)

| Question | Decision |
|---|---|
| Board card move | **Not animated** |
| Floating empty-state icon | Runs for ten seconds, then rests |
| Cursor spotlight | One hero card at most (Portfolio's first project card) |
| Gradient border | The ask creaite input, on focus only |
| In-app Motion setting | Added to item 1 (Follow system, Reduce, Full) |
| Landing pulse, banners | Added as items 31 and 32 in Stage B |
| Drag feedback on the Board | The card **lift** and the target-column **highlight** are in (item 33); the drop placeholder and the move itself are not |
| Alan's "Worth considering" list | All in: landing pulse (31), banners (32), drag lift and highlight (33), queue cleared (34), copy confirmation (35), row hover and J / K (36), theme fade (37), new-since-last-visit dot (38) |
| Sprint size | Left as is (38 items), Alan 10-10-2026 |
| Test bar | Per `STATUS.md`: this sprint's own tests, then only the conflicted files' tests at merge, and one full suite on the final `main` before the release |
| Everything else in the mock-up | Built, in the three stages above |

## Boundaries

- **Owns:** the stylesheet, a helper block and small animation hooks in `system/templates/dashboard.html` (the Work, Review, Today, Portfolio, Settings, Prep and ask creaite parts), and their tests. By the time this starts, the Work views sprint has merged, so nothing else should be in flight on those; if another sprint has started on them, ask before editing.
- **Don't change** what is saved, applied or proposed: no schema change, no change to `tracker.py`, `propose.py`, the live server's API or the apply path. The one exception to "dashboard only": item 25 needs the run's state, which the page already receives; if it does not, say so in BUILD before touching the live server.
- **Every effect is behaviour-neutral.** Remove all of the CSS and the helper block and the dashboard must work exactly as before: no state lives in an animation, no handler waits for `transitionend` or `animationend` (use timeouts that cannot hang, or no waiting at all), and a test clicks fast, repeats an action mid-animation, and checks the data is right.
- **No new library, no network, no external font or image** (portability rules). The mock-up's CSS and helpers are the reference, not a dependency.
- **Shared files** (`dashboard.html`, `help.md`, `dev/dashboard-spec.md`): new code in marked sections (`/* ===== BL-136 (sprint-motion) ===== */`); don't reformat unrelated lines. Edit existing transitions in place only where item 1 folds them into tokens.
- **Performance:** only `opacity` and `transform` (plus `grid-template-rows`); no `will-change` left on; nothing animates when the tab is hidden; a 500-row Work list renders and scrolls as before (time it before and after and note it in BUILD).
- **Themes:** all seven themes, light and dark. The flash, the ring, the skeleton shimmer and the gradient border use colour tokens only; check each in the default, the Brightwater theme and dark. **Colour is never the only cue** (row tint, health ring, flash).
- **Don't touch `dev/BACKLOG.md` or `dev/BRD.md`;** they are updated at merge. Write the FR text you'd add in BUILD (a new requirement for motion: the house rules, reduced motion, the exclusions).
- **Help:** a short "Motion and reduced motion" note in `help.md` (what moves, that it follows the system setting), then `python3 dev/tools/build_guides.py`.
- **Release notes:** a line for the next version in `dev/release-notes/`; don't change `VERSION`. The dashboard template is part of the engine, so this ships in a release.
- **Tests start from your own settings:** run them in the worktree, not the main folder.
- **Stop a test run by its process tree,** never with `pkill` by name.
- **Development guard:** sample data only; test with temporary vaults.

## Tests

In a real browser against the real live server, like `test_work_board.py` (Chrome; skipped otherwise). A new `dev/tests/test_motion.py`, plus additions to the files that own each page.
- **Foundation:** the tokens are defined on `:root` in every theme; with reduced motion emulated, a sweep over every page finds no element with a non-zero computed `transition-duration` or `animation-duration`, no running animation (`document.getAnimations()` is empty after settling), and counts show their final value at once; the one reduced-motion rule exists and the old scattered ones are gone.
- **Static check on the CSS:** no `transition` or `@keyframes` animates `width`, `height`, `top` or `left` on a list element (an allow-list of the progress-bar fill and the sliding indicator, which are single elements); no animation loops except the listed ones (`sp`, the sweep hairline, the typing dots, the now ripple, the empty-state float with a finite count).
- **Behaviour neutral:** click Approve on three Review rows in 100 ms, press Undo mid-collapse, sort twice mid-FLIP, open and close the panel quickly, collapse and expand a group repeatedly: the database, the highlight and the counts are right at the end, and no row is left hidden or doubled.
- **Skips:** a bulk approval, Approve all, and a 40-row sort produce no `getAnimations()`; the Board card move and a lane move produce none (Alan's exclusion).
- **Once only:** count-up and first-paint reveal run on first load and not on a live refresh, a return to Today, or a re-render after an edit; the flash fires only for cells whose value changed and never on the first render.
- **Progress:** the sweep hairline appears when a run starts, is gone when it finishes, is stopped and when the server drops.
- **ask creaite:** the scroll position is unchanged while words stream in (BL-120); history and a re-opened chat do not animate; a reply over about 400 words appears whole.
- **Empty-state float:** the icon has `animation-iteration-count` 2 and rests afterwards.
- **Spotlight and border:** the spotlight is on one element only and absent with `hover: none`; the gradient border shows only with focus in the input.
- **Hidden tab:** with the page hidden, the now marker's ripple is paused.
- **Setting:** Reduce makes the sweep over every page find no motion, with the OS setting off; Follow system obeys the OS setting; Full does not animate when the OS asks for reduced motion on essential state (a spinner), and the choice survives a reload.
- **Smooth scroll:** under reduced motion, `scrollIntoView` is called without `behavior:"smooth"` (a spy on the helper), and J/K repeat is never smooth.
- **Landing and banners:** `landOn` fires from Today, search and Show them and not from a sort or live refresh; a row in a collapsed group opens the group first; a banner present at load does not animate.
- **Drag:** a real-mouse drag (as `test_work_board.py`) shows the lift class on pick-up and the highlight on the column under the pointer, clears both on drop, and moves the card with no animation; a column that refuses the drop never gets the highlight.
- **Others:** the copy tick follows a real copy and announces it; the theme fade class is added for about 300 ms around a change and not at load; Review shows the cleared summary once on clearing and not when opened empty; the new-visit dot shows for rows newer than the last view, not on a first visit, fades after 2 s on screen, writes nothing outside the browser's own storage, and the hidden text is present; J/K cross-fades and a held key does not.
- **Accessibility:** focus order and the focus outline are unchanged; the count-up's final number is readable by the accessibility tree from the first frame; Esc and keyboard moves act at once, never after an animation.
- **Existing:** `test_dashboard.py`, `test_work_board.py`, `test_work_filters_live.py`, `test_decisions_board.py`, `test_dashboard_editing.py`, `test_review_nesting.py`, `test_minutes_review.py`, `test_live_server.py` and the ask creaite tests still pass.

## Done when

- **Tests:** as above, per item.
- **This sprint's own tests** pass (the files named above) before it asks to merge; at the merge only the files for code that had conflicts are re-run. The full suite runs **once, on the final `main` before the release** (`python3 dev/tools/run_tests.py -j 4`, when no other session is running tests), as `STATUS.md` sets out for v1.2.0. A failure is read and fixed or reported; a flake that passes alone is named, not hidden.
- **Docs:** `dev/dashboard-spec.md` gains a **Motion** section holding the house rules and the token table; Help and the guides; a "Sprint motion" section in `dev/BUILD.md`.
- **Alan sees it:** before asking to merge, walk Today, Work (List and Board), Review, Portfolio, a project page, Settings and ask creaite with motion on, then again with the system's Reduce motion turned on, in the default and dark themes, and list any difference from the mock-up. Include one run at **Slow ×3** (a debug switch in the browser console: `document.documentElement.style.setProperty('--k', 3)`) to judge the easing, and the timing note for the 500-row list.
- **Commits:** each item committed separately on `sprint-motion`, with the attribution lines from the session's instructions. Never push or merge into `main`.
