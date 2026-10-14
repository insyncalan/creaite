# The component guide (BL-256)

**Status: agreed by Alan (13-10-2026), with his answers to Q1 to Q3 below.** Changes go through the Scrum Master, so
this stays the one rule set.

Screens move to Preact with signals one at a time, only when a screen is being changed anyway (BL-286's Prep screens
first). Code not yet moved stays as it is: `html`, `putHTML` and `shared` keep working beside the components.

**Built so far (step 2, 13-10-2026):** Preact 10.29.8 and `@preact/signals` 2.11.2 (`-core` 1.14.4), vendored in
`system/templates/vendor/preact/` with a hash manifest (`dev/tools/vendor_preact.py`); JSX through esbuild's automatic
runtime; `StatusDot` on Today's portfolio table.

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
- Saving is unchanged: `save`/`writeProposal`/`api` in core. No component writes to the server by any other route.

## 3. The building blocks

Written once, used everywhere, each with its keyboard, focus and screen-reader names built in (BL-214, BL-216,
BL-279). They keep today's class names and markup, so a screen that moves to them doesn't change its snapshot.

| Block | Job | Keyboard, focus and ARIA | Replaces |
|---|---|---|---|
| `Menu` | A list of commands from a button or a right-click | Button: `aria-haspopup="menu"`, `aria-expanded`. `role="menu"`/`menuitem`; ↑ ↓ Home End move, Enter or Space runs, Esc and Tab close, focus back to the button; a click away closes; disabled items `aria-disabled` and skipped | `work.js` `newMenu`, `boardMenu`, `viewMenu`; `review.js` `rvReasonMenu`, `rvMoveMenu`; the context menu; the rail's and Today's menus (`.bmenu`) |
| `Dialog` | A modal: the native `<dialog>` with `showModal()` | Named by its heading (`aria-labelledby`); focus to the first field or the one given; Esc (`cancel`) closes and focus returns to the opener; a scrim click closes only when nothing is typed; popovers inside it (the calendar, the date hint) render inside it | the eight `<dialog>`s in `shell.html` (`cmdk`, `rvDlg`, `boardDlg`, `genDlg`, `personDlg` …) and `drafts.js` `deDialog` |
| `Picker` | Choose one value from a button (status, priority, project) | Button `aria-haspopup="listbox"`, `aria-expanded`; `role="listbox"`, `option`, `aria-selected`; optional search box first; ↑ ↓ move, Enter picks, Esc closes and returns focus; "No match"; "Use '…'" when new values are allowed; kept inside the window, above ask creaite | `panel.js` `pkList`, `pkMk`, `pkPopClose`, `pkPlace` (`.pkpop`, `.pkopt`) |
| `Combobox` (`PersonPicker` is one) | Type to choose, with suggestions | `<input role="combobox">`, `aria-expanded`, `aria-controls`, `aria-activedescendant` (focus stays in the field); ↑ ↓ move, Enter picks, Esc closes, then clears; the project's own people first; the one matcher, `ownerMatches` (BL-187) | `core/fields.js` owner combobox (`comboDraw`, `comboClose`, `shared.COMBO`, `shared.CI`); the peek's owner list |
| `FilterBar` | The row of filters over a list | Each filter is a button with a multi-select listbox (`aria-multiselectable`), search when over six options, Only me, Select all, Clear and "not"; the button's label says what is chosen; never wraps: unused filters fold into + Filter (BL-150); state in the area's store and the address (`navWrite`) | `work.js` `renderFilterBar`, `drawMenu`, `drawPicker`, `wfFit`; `review.js` `rvFilterBar`; `activity.js` `actFilter` |
| `Tabs` | Switch between panels of one screen | `role="tablist"`, `tab`, `tabpanel`, `aria-selected`, `aria-controls`; roving `tabindex`; ← → Home End move and select (as today) | `#wtabs`; Help's `#helpTabs`; People's `#ptabs`; Activity's tabs (`actTab`); `milestones.js` `feedTabsHtml` |
| `Toast` | The one message at the foot of the page, with Undo or another action | `role="status"`, polite; 10 s with an action, 5 s without; held while pointed at or focused; Esc hides it (BL-215's rules); focus that was in it goes back; ⌘Z in Work undoes. `snack(msg, undo, label)` stays the call and the seam tests replace | `core/server.js` `snack`, `snk…`, `bootSnackUndo`, `bootSnackKeys`; `review.js` `snackAdd` |
| `Peek` | The frame of the side peek over the page: header, ID, close, previous and next | `role="dialog"`, not modal, named "Edit ABC-A-003"; Esc closes unless a popover is open, focus back to the row; the staged dot; scroll, focus and typed text survive a redraw (BL-262). The contents stay the area's | the frame in `panel.js` `drawPanel` (`#panel.peek`); `milestones.js` `mvPeekEl` (`#mvPeek`) |
| `StatusDot` | Health or status as a dot | Never colour alone: it carries its word (visible, or as hidden text); variants ok, warn, bad, off, staged | `class="dot …"` in Today, Review, the panel, the live status; `meetings.js` `hdot`; `panel.js` `pkDots` |
| `Chip` | A small labelled value: a tag, a suggestion, a property button | As a button: a full name ("Owner: not set"), `aria-haspopup` when it opens a picker, the tooltip from `data-tip`; a removable chip's × is "Remove …" | `panel.js` `pkChip`; `drafts.js` `chipEls`; `work.js` `renderViewChips`; `projects.js` `depChips` |
| `TextEditor` | A box of plain text on the one editor (`core/editor.js` `creaiteEditor`, Tiptap, BL-301 A) | `role="textbox"`, `aria-multiline`, named by `aria-labelledby` (and `aria-describedby`); one paragraph a line, the text never read as markup; its element's `value` reads and sets the text as a textarea's did (setting it is quiet, not an edit); `onInput` on each change, `onCommit` when left; ⌘Z and ⌘⇧Z the editor's; Enter refused when one line; a new value from the store never lands under the cursor | Prep's notes and questions (`PrepPage.jsx` `.ppbox`), the Prep popup's shaped notes (`PrepShape.jsx` `.shbox`); the peek's text fields use `creaiteEditor` directly (`panel.js` `pkEdMount`) |
| `AiBar`, `AiSuggestion` (`AiSelect.jsx`) | AI on selected text in any `creaiteEditor` given `ai` (BL-301 D): the bar over a selection, and the suggestion Alan accepts or discards | Bar: `role="toolbar"` "AI on the selected text", **AI ▾** is the `Menu` block (the place's options, part E's `aiAction` items, "Or say what you want…" last, a named box: Enter asks, Esc back to the text); Alt+/ opens the menu with focus in it. Suggestion: `role="dialog"`, not modal, named by the option; focus to its first button in each state (ask, running, failed, ready); Esc discards with focus back to the text; Show changes `aria-pressed` (`<del>`, `<ins>`); the check a list named "Check it"; Accept one transaction (⌘Z), a one-line field kept one line. Drawn in `#aiLayer` (on the body, or inside an open modal dialog) | Current state's Make it executive button (now an item of AI ▾ beside Save, `AiMenu`) |

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
