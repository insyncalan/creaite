# The component guide (BL-256)

**Status: agreed by Alan (13-10-2026), with his answers to Q1 to Q3 below.** Changes go through the Scrum Master, so
this stays the one rule set.

Screens move to Preact with signals one at a time, only when a screen is being changed anyway (BL-286's Prep screens
first). Code not yet moved stays as it is: `html`, `putHTML` and `shared` keep working beside the components.

**Built so far (step 2, 13-10-2026):** Preact 10.29.8 and `@preact/signals` 2.11.2 (`-core` 1.14.4), vendored in
`system/templates/vendor/preact/` with a hash manifest (`dev/tools/vendor_preact.py`); JSX through esbuild's automatic
runtime; `StatusDot` on Today's portfolio table. BL-316 (14-10-2026): `FilterBar` built and every filter bar of the
same pattern moved onto it (Work's, Review's, Settings › People's funnel). `Toast` built and the page's message (`#snack`) drawn by it.

## 1. Files and names

- One component per file under `system/templates/dashboard/src/components/`, PascalCase, named for what it is, never for
  the screen it was first made for: `Menu.jsx`, `Dialog.jsx`, `Picker.jsx`, `FilterBar.jsx`, `Peek.jsx`. The file's
  one export has the file's name. Helpers only it uses stay in the file.
- A screen made of components is `src/components/<area>/` (`components/prep/PrepBrief.jsx`); building blocks sit at the
  top level and never import a screen.
- Stores: `src/stores/<area>.js` (beside `core/`), because code not yet moved reads them too.
- The areas mount a screen into its existing container (`render(<PrepBrief/>, $("#prepBody"))`). Old code never
  writes into a mounted container (a test checks it).
- **Q1, answered (Alan, 13-10-2026):** `src/components/`, not BL-256's `dashboard/components/`, so esbuild's and tsc's
  paths stay inside `src/`.

## 2. State

- **Signals, one store per area** (`src/stores/prep.js` exports `signal`s and `computed`s and the functions that change
  them). A component reads `store.x.value` and redraws only when that signal changes.
- **A component's own state** (`useSignal` or `useState`) only for what nobody else reads: open or closed, the text
  typed in a search, the active option.
- **`shared` stays** for everything not yet moved. When a field moves into a store, its `shared` entry becomes an
  accessor onto the signal (as `globals.json`'s `live` accessors already do for `window`), so old code and the tests
  keep reading and writing it unchanged. A field lives in one place only.
- **The data** (`D`, `P`, `A`, `R`, `DEC`, `ACT`, `PEOPLE`) stays in `core/data.js` for now. `src/stores/data.js` holds a
  `dataVersion` signal that `reloadData` and `refreshAll` bump, so a component that reads the data redraws after a
  reload. BL-304 grows this into records keyed by ID.
- **Records stay put, changes go on top (BL-304, v1.9.4, `core/instant.js`).** `A`, `R` and `DEC` keep their objects:
  a targeted refresh (`recordsRefresh`, `GET /api/records?ids=…`) merges each item into the object already there, so a
  component holding a record keeps it. A change still saving is an overlay in `INFLIGHT`, laid over any fresh data by
  `ovReapply()`; never write to a record from fresh data without calling it. Not yet signals: the merge ends in
  `refreshAll`, as a reload does.
- Saving is unchanged: `save`/`writeProposal`/`api` in core. No component writes to the server by any other route. A
  record edit passes `opt.recs` to `save` (or goes through the peek's `pkCommit`), so it shows at once (BL-304).

## 3. The building blocks

Written once, used everywhere, each with its keyboard, focus and screen-reader names built in (BL-214, BL-216,
BL-279). They keep today's class names and markup, so a screen that moves to them doesn't change its snapshot.

| Block | Job | Keyboard, focus and ARIA | Replaces |
|---|---|---|---|
| `Menu` | A list of commands from a button or a right-click | Button: `aria-haspopup="menu"`, `aria-expanded`. `role="menu"`/`menuitem`; ↑ ↓ Home End move, Enter or Space runs, Esc and Tab close, focus back to the button; a click away closes; disabled items `aria-disabled` and skipped. Props (BL-316): `ariaLabel` (a button whose words are a symbol, "…"), `chevron: false`, `labelCls`, `id`, `menuId`, `menuCls`, `hidden`; items may be plain words (no `icon` or `line`), a `head` or a `note` (words, not items), with a `tip` and a `cls`. `openMenu(anchor, {label, items, onPick, id, cls, align, at, loading, onClose})` opens one from a control already in the page (its `aria-expanded` follows) or at the pointer (`at`), fixed and kept in the window; `closeMenu`, `menuOpenFor`. `MenuPanel` is the `role="menu"` box with the keys built in for a menu with its own contents (`bare`, `onKey` first, `autoFocus`, `boxRef`; a text field inside keeps ↑ Home End); `menuMove` is the arrow keys alone | Moved (BL-316): Work's New tile (`components/work/NewTile.jsx`), More views, a saved view's ▾, a board card's Move to…; Today's reminder "…"; ask creaite's History; Review's Move to project and the peek's More (were `pkList` menus); the sidebar's More and Review's reasons menu (`MenuPanel`). The right-click menu (was `review.js` `cxOpen`) is `components/review/ContextMenu.jsx`: one `MenuPanel` per level, with submenus and a search (`openContextMenu` at the pointer, `openContextMenuAt` under a control; BL-316) |
| `Dialog` | A modal: the native `<dialog>` with `showModal()` | Named by its heading (`aria-labelledby`; `ariaLabel` when it has none; `describedBy`); focus to the first field or the one given; Esc (`cancel`) closes and focus returns to the opener (unless the owner has put focus elsewhere); a scrim click closes only when nothing is typed; popovers inside it (the calendar, the date hint) render inside it. Props (BL-316): `open` left out makes a dialog opened by old code: drawn once (its inner ids then exist for the code that fills them), opened with `openDialog(id or element, {focus, modal})` and closed with `closeDialog` or `close()`, at once; Esc and a form's `method=dialog` close it as the browser does; the scrim closes it unless something was typed or chosen since it opened (or `dirty`, a boolean or a function, says so); `onClose` is told after. `modal: false` opens it without the scrim (the Prep popup's swap while the peek is over it); a close whose event comes after it was opened again is not a close, and the first opener is kept | Moved (BL-316): the eight dialogs that were in `shell.html` (`cmdk`, `inPrev`, `searchPrev`, `llDlg`, `rvDlg`, `boardDlg`, `genDlg`, `personDlg`), drawn by `components/dialogs/PageDialogs.jsx` (`bootDialogs`, the first start-up step); the draft email (`#deDlg`, was `deDialog`), Undo changes (`#actDlg`) and the Prep popup (`#prepDlg`), made on first use (`makeDraftEmailDialog`, `makeUndoDialog`, `makePrepDialog`); Customise sidebar (`#railCust`) |
| `Picker` | Choose one value from a button (status, priority, project) | Button `aria-haspopup="listbox"`, `aria-expanded`; `role="listbox"`, `option`, `aria-selected`; optional search box first; ↑ ↓ move, Enter picks, Esc closes and returns focus; "No match"; "Use '…'" when new values are allowed; kept inside the window, above ask creaite Built (BL-316, `components/Picker.jsx`): one popup at a time from a control already in the page. `openPicker(anchor, {options, value, onPick(v, typed, o), search, label, allowNew, role: "listbox"\|"menu", filter(q), cls, onClose(how)})`: an option is `{v, label, icon (an icon's name), mark (a vnode, e.g. a status ring), hint, disabled, id, …}`; Tab closes it and moves on from the control. `openDatePicker(anchor, {value, label, onPick(iso), parse(text), error, weekend(iso), typedNote(text), placeholder, onClose})`: a month's calendar, `role="dialog"` (its control says `aria-haspopup="dialog"`): ← → ↑ ↓ a day or a week across months, the quick days, a typed box, Tab out of either end closes. `openPopover(anchor, {label, content (a vnode), cls, id, role, focus, onClose})`: a small dialog of its own (Esc, focus to `focus` or its first field, Tab out closes). `closePicker(how, focus)`, `pickerOpenFor(anchor)`, `placePicker(el, anchor)`; `onClose(how)` (`esc`, `tab`, `away`, `pick`, `owner`) returns true when the owner has put focus itself; `shared.PKPOP` is `{el, anchor}` while one is open. | Replaced, and removed (BL-316): `panel.js` `pkList`, `pkMk`, `pkPopClose`, `pkPlace`, `pkDate` (the classes `.pkpop`, `.pkopt` stay); `htmlPopover` (Review's move preview is `#rvDlg`) |
| `Combobox` (`PersonPicker` is one) | Type to choose, with suggestions | `<input role="combobox">`, `aria-expanded`, `aria-controls`, `aria-activedescendant` (focus stays in the field); ↑ ↓ move, Enter picks, Esc closes, then clears; the project's own people first; the one matcher, `ownerMatches` (BL-187) Built (BL-316, `components/Combobox.jsx`): `Combobox` / `mountCombobox(host, {id, name, value, label, placeholder, empty, options(q, typed), onPick(o), onInput(v)})`; a suggestion `{v, label, sub, head (a group heading before it), cls, fill (what the field shows; default label), remove() and removeLabel (its ×)}`; `onPick` returning false leaves the field to the owner; a second Esc clears the field; `closeCombobox()`, `comboboxOpen()`. Keeps `.combo`, `.combo-list`, `.copt`, `.act`, `.cgrp`. Its first user is the form's owner field (`core/fields.js` `mountOwnerFields`, `ownerOptions`) | `core/fields.js` owner combobox (`comboDraw`, `comboClose`, `shared.COMBO`, `shared.CI`); the peek's owner list stays a Picker with search |
| `FilterBar` | The row of filters over a list | Each filter is a button with a multi-select listbox (`aria-multiselectable`), search when over six options, Only me, Select all, Clear and "not"; the button's label says what is chosen; never wraps: unused filters fold into + Filter (BL-150); state in the area's store and the address (`navWrite`). Built (BL-316): a main filter's button has `aria-haspopup="listbox"`, `aria-expanded`, `aria-controls`; Enter, a click or ↓ opens it with focus in the search or on the first option (`role="option"`, `aria-selected`); ↑ ↓ move (↑ from the first option climbs to Clear, Select all, the search, is / is not), Home End go to the first and last option, Space or Enter ticks, Esc closes with focus back on the button, Tab and a click away close. The funnel (`aria-haspopup="dialog"`, `aria-expanded`) opens the field picker: every field, the main ones first, a section's heading where it changes; ↑ ↓ Home End choose a field, → or Enter go into its options, ← back; a date-range field is two boxes; Done or Esc close it with focus back on the funnel; a click or focus away closes it. Drawn from old code with `drawFilterBar(host, {fields, onSelect, onNot, onRange, more, bare, fold})`: each field `{id, label, main, button, btnId, menuId, data, on, options() (value, label, count, extra), selected, not (left out: no is / is not), onlyMe, single, range, section, note, mark}`; `more` the funnel `{id, menuId, label, menuLabel, count, on, key, listLabel, field, onField, query, onQuery, onOpen, result, resultId, doneId, headId, clearAll}`; `bare` draws the funnel alone into its own `.dd`; `fold` names the row that must stay on one line. The area keeps every value and redraws the bar; the bar keeps only what is open (`filterBarOpen`, `openFilterBar`, `closeFilterBar`, `fitFilterBar`) | Moved (BL-316): Work's bar (`workBarProps`, `drawWorkFilters`; were `renderFilterBar`, `drawMenu`, `drawPicker`, `wfFit`); Review's (`rvBarProps`, `drawReviewFilters`; was `rvFilterBar`, `rvDrawPick`): Kind, Needs and Source now open their own lists as Work's do, the funnel the picker; Settings › People's funnel (`pfBar`, bare; was `pfPicker`); Activity's (`actBarProps`; was `actFilter`, a row of type toggles and two date boxes): Kind opens its list, the funnel holds Kind and When (two date boxes). None left |

| `Tabs` | Switch between panels of one screen | `role="tablist"`, `tab`, `tabpanel`, `aria-selected`, `aria-controls`; roving `tabindex`; ← → Home End move and select (as today). Props (BL-316): the list's `id`; per tab `tabId` (its button's id), `controls` (its own panel), `count` (after the words, as `<span class="sub">`), `data` (data- attributes); `wrap` either way. Drawn from old code into a `.tabhost` box (`display:contents`) with `drawTabs` | Moved (BL-316): Work's `#wtabs`; Help's `#helpTabs`; People's `#ptabs`; Activity's Changes and Quality (was `actTab`); the history feeds' tabs in the peek (`#pkTabs`), the milestone editor and the project panel (was `feedTabsHtml`, now `feedTabItems` and `mountFeedTabs`) |
| `Toast` | The one message at the foot of the page, with Undo or another action | `role="status"`, polite; 10 s with an action, 5 s without; held while pointed at or focused; Esc hides it (BL-215's rules); focus that was in it goes back; ⌘Z in Work undoes. `snack(msg, undo, label)` stays the call and the seam tests replace. Built (BL-316): props `open`, `text`, `action` (the button's words; none: no button, the shorter time), `onAction`, `onHide` (the owner draws it again closed), `run` (a new message: its time and bar start again), `id`/`textId`/`actionId` (default `#snack`, `#snackT`, `#snackU`), `ms`/`actionMs` (`TOAST_MS`, `TOAST_ACTION_MS`), `layers` (what Esc closes first, `TOAST_LAYERS`); today's classes (`.on`, `.held`, `.mtimer`). `drawToast(host, props)` draws it at once, so code that reads `#snack` straight after sees it. While a modal dialog is open the toast's host sits inside the top one (`toastLayer`), so its Undo can be reached; it goes back when the dialog closes | Moved (BL-316): `core/server.js` `snack` now draws it into `#toastHost` (`hideSnack` closes it; `bootToast` draws it and adds Work's ⌘Z); `snk…`, `SNK_LAYERS`, `bootSnackUndo`, `bootSnackKeys` gone; Review's ⌘Z closes it with `hideSnack`. `review.js` `snackAdd` removed: nothing called it since BL-315 |
| `Peek` | The frame of the side peek over the page: header, ID, close, previous and next | `role="dialog"`, not modal, named "Edit ABC-A-003"; Esc closes unless a popover is open, focus back to the row; the staged dot; scroll, focus and typed text survive a redraw (BL-262). The contents stay the area's Built (BL-316, `components/Peek.jsx`): `Peek({id, label, cls, open, children})` (an `<aside role="dialog">`); `peekFrame(id, {label, cls})` makes the frame once at the end of the page, hidden, and returns it for old code to fill (replaces `mvPeekEl`); `PeekBar({onClose, closeKey, onExpand, expandLabel, onPrev, onNext, prevOff, nextOff, ids: {close, expand, prev, next}, children})`, each an IconButton (Previous and Next blocked at the ends), `drawPeekBar(host, props)`. Esc and focus return stay the owner's. IconButton gained `id` and `hidden` (backward compatible) | the frame in `panel.js` `drawPanel` (`#panel.peek`); `milestones.js` `mvPeekEl` (`#mvPeek`) |
| `StatusDot` | Health or status as a dot | Never colour alone: it carries its word (visible, or as hidden text); variants ok, warn, bad, off, staged. `health` draws health()'s icon and word; `status` a plain dot (class `cls`, default `dot`) with its `word` beside it (in a span `wordId`, `live`, when other code updates it) or its own name (`label`: `role="img"` and the tooltip). `statusDotNodes` (drawn once, for old code), `drawStatusDot` (redrawn in place), `mountStatusDots` (placeholders) | Moved (BL-316): the live line (`#chSub`), the staging bar's dot (`#pkStage`), a staged row's `.pkdot` (`markStagedRows`, was `pkDots`); Today's portfolio. Not dots: the funnel buttons' counts in Work, Review and People are `.fcount` badges |
| `Chip` | A small labelled value: a tag, a suggestion, a property button | As a button: a full name ("Owner: not set"), `aria-haspopup` when it opens a picker, the tooltip from `data-tip`; a removable chip's × is "Remove …". `drawChips(host, chips)` (BL-316) draws a row old code redraws (each entry a Chip's props, `key` keeps a chip across redraws) | Moved (BL-316): the peek's property buttons (`components/peek/PeekProps.jsx`, `peekPropNodes`; was `pkChip`); the suggested fields in the peek and Quick capture (`capChipsDraw`; was `chipEls`); a dependency's suggested milestones in the form and the peek (`depSugDraw`, `#depSug`; was `depChips`). Not chips: Work's views bar (`renderViewBar`, was `renderViewChips`) is a row of toggle buttons (`aria-pressed`) with menus and renaming, so it stays its own |
| `TextEditor` | A box of plain text on the one editor (`core/editor.js` `creaiteEditor`, Tiptap, BL-301 A) | `role="textbox"`, `aria-multiline`, named by `aria-labelledby` (and `aria-describedby`); one paragraph a line, the text never read as markup; its element's `value` reads and sets the text as a textarea's did (setting it is quiet, not an edit); `onInput` on each change, `onCommit` when left; ⌘Z and ⌘⇧Z the editor's; Enter refused when one line; a new value from the store never lands under the cursor | Prep's notes and questions (`PrepPage.jsx` `.ppbox`), the Prep popup's shaped notes (`PrepShape.jsx` `.shbox`); the peek's text fields use `creaiteEditor` directly (`panel.js` `pkEdMount`) |
| `AiBar`, `AiSuggestion` (`AiSelect.jsx`) | AI on selected text in any `creaiteEditor` given `ai` (BL-301 D): the bar over a selection, and the suggestion Alan accepts or discards | #117: `AiSpark` (a margin button beside a non-empty selection, `aria-expanded`) opens `AiBar`, `role="toolbar"` "AI and formatting on the selected text": **Turn into** (`Menu` with `hover`, radio items, no AI) apart from the tinted AI zone (Format notes, the place's groups as hover `Menu`s, part E's `aiAction` items under "Make into", **Ask…**, a named box: Enter or ⌘↵ asks, Esc back to the text); both placed with `placeAtCaret`; a place the place table (`AI_PLACE_TABLE`) switches off shows nothing; Alt+/ opens the bar with the first AI menu open. Suggestion: `role="dialog"`, not modal, named by the option; focus to its first button in each state (ask, running, failed, ready); Esc discards with focus back to the text; Show changes `aria-pressed` (`<del>`, `<ins>`); the check a list named "Check it"; Accept one transaction (⌘Z), a one-line field kept one line. Drawn in `#aiLayer` (on the body, or inside an open modal dialog) | Current state's Make it executive button (now an item of AI ▾ beside Save, `AiMenu`) |

Also small and shared: `Icon` (from `ICONS`), `IconButton` (today's `ibtn`: the same words in `aria-label` and the
tooltip). **Q2, answered (Alan, 13-10-2026):** the icons become element data (each icon's elements and attributes), so
`Icon` needs no raw HTML; `<Markdown>` stays the only exception.

## 4. Text and safety

- **Text only through JSX** (escaped by design). No HTML strings, no `html`/`raw`/`putHTML` in a component, no `ref`
  that writes `innerHTML`, so check.py's sink count can't rise.
- **One exception:** `<Markdown>` wraps `mdChat`, the one sanitised Markdown renderer, with `dangerouslySetInnerHTML`.
  check.py counts `dangerouslySetInnerHTML` and the ratchet allows that one.
- No `eval`, `new Function` or inline `on…=` attributes (BL-255's script policy).

## 5. Styling

- The existing design tokens only (`var(--accent)`, `var(--line)` …): no new colours, no colour literals; a test fails
  one in `src/components/**/*.css`. Every theme then works with no extra work.
- **The one design scale (BL-325)** for every size: type `var(--fs-*)`, radius `var(--r-*)`, shadow `var(--shadow-sm|md|lg|side)`,
  layers `var(--z-*)`, and a control's height, radius and text size `var(--ctl-h)`, `var(--ctl-r)`, `var(--ctl-fs)`; spacing in px
  on the 4px scale (2px steps to 16, then 20, 24, 28, 32, 40, 48 …). The scale is the marked block at the top of `style.css`;
  `dev/tools/token_audit.py` (check 5) reports anything off it.
- One stylesheet per component area (`src/components/blocks.css`, `src/components/prep/prep.css`), added after `style.css` by
  the build. The blocks reuse today's classes (`.bmenu`, `.pkpop`, `.tabs`, `#snack`) rather than restyling them.
- Motion through `core/motion.js` (it honours reduced motion); no new animation library.

## 6. Tests

- **Each building block has its own Chrome test** (`dev/tests/test_block_<name>.py`), on a small fixture that mounts
  it: its ARIA roles and names, every key in its row above, focus return, and that its text is escaped.
- **A screen's test checks the composition** (the right blocks, wired to its store).
- **BL-254's snapshots stay the check that nothing moved**: a screen that moves keeps its goldens; a golden that changes
  needs Alan's agreement.

## 7. Types

- Every component carries JSDoc: a `@typedef` for its props and `@param {Props} props`. `checkJs` (`typecheck.py`)
  covers `src/components/**/*.jsx` and `src/stores/`, and the count stays 0.
- Preact's own type files come with the pinned library, so tsc needs no download beyond today's.

## 8. Libraries

- Preact, its hooks and `@preact/signals` only: MIT, pinned, bundled into the page with the rest of the script,
  offline, nothing installed at run time (NFR-12).
- **No third-party component library** without Alan's agreement; `preact/compat` only if he agrees one and it stays
  small and offline.
- **Q3, answered (Alan, 13-10-2026):** we build our own blocks, with no outside library.
