# v19-portfolio: BL-285 and BL-308 (v1.9.0)

For the Scrum Master. Laptop 2, branch `v19-portfolio` from `main` (`78a0cb5`), 13-10-2026. No schema change.

## BL-285: Today › Portfolio, description on hover, resizable columns

- **Description on hover.** `portfolioTable` (`src/today.js`) no longer prints the `sub` line (`p.client`) under the name: each row is one line. The name is a `button.pfname` (styled as the text it replaced) carrying `data-tip` with the description, so the dashboard's one tooltip (`#tip`) shows it on hover and on keyboard focus; screen readers get it from a hidden `span.vh` named by `aria-describedby` (`pfd-<CODE>` on Today, `pjd-<CODE>` on Projects, so the ids never clash). No `title` attribute. An empty description has no `data-tip` and no description. The button also gives keyboard users a way to open the project (Enter), which the row never had.
- **Resizable columns.** Work's resizer is now shared: `colResizer(th, key, after)` in `src/work.js` (pointer drag, a keyboard separator with ←/→ in 16 px steps, 60 to 900 px, double-click resets with "Column width reset"), and `rzApply` calls it for Work, unchanged in behaviour and markup (Work's golden is untouched). `pfResize(box)` (`src/today.js`) gives each portfolio heading (`th[data-col]`: `project`, `health`, `evidence`, `trend`, `next`) a handle, remembered in `creaite-colwidths` under `portfolio|<column>`. Settings › Work's "reset column widths" clears these too (it clears the whole store). The Today click handler ignores `.colrz`, so a resize never opens the project.
- **Projects page.** It draws the same `portfolioTable`, so it gets the same one-line rows, tooltip and resizable columns, sharing the same remembered widths.
- **Reflow.** Wide columns scroll inside the table's frame (`.tbl` `overflow:auto`); at 320 px nothing scrolls sideways (tested with two columns at 900).
- Spec (`dev/dashboard-spec.md`, Today › Portfolio) and Help (Today › Portfolio) updated.

## BL-308: the wordmark without its dashed copy

- `shell.html`: the `<use class="wmd">` (dashed draft) is gone; the word (`.wmw`) and the saffron bar (`.wmb`) stay, `role="img"`, `aria-label="creaite"`. The view box is cropped from `7 14 306 70` to `7 25 306 60` (the top band only held the draft): the width, and so the word's size, is unchanged at 62 px; the logo is about 2 px shorter.
- `style.css`: the `.wmd` rules, the forced-colours `.wmd{display:none}` and BL-291's `@media (prefers-contrast: more){ .logo .wmd{display:none} }` removed.
- `dev/reference/logo/`: `wordmark-preview.svg` and `creaite-wordmark.svg` redrawn without the draft (same crop); `wordmark-paths.json`'s `art` and `tokens` drop the draft (the paths are unchanged); `README.md` updated (the icon keeps its dashed draft square). `dev/tools/outline_wordmark.py` writes the new layout, so a rerun matches.
- Help (High contrast, the wordmark) and the spec (the wordmark) updated.
- **Alan sees it before merge** (BL-308's done-when): the rail, any palette.

## Goldens (BL-254)

Re-recorded only `today` and `projects`: the portfolio table's headings now carry `data-col` and the resize handles, and the name is a button with its tooltip instead of a description line. No other screen changed (Work's resizer markup is identical). The wordmark is in the rail, which no golden captures.

## Tests

- New `dev/tests/test_portfolio_table.py` (10): source checks (no dashed copy in the shell, no `.wmd` or BL-291 rule in the CSS, no description line or `title` in `portfolioTable`); in Chrome on the snapshot vault: one line per project and the tooltip on hover; Tab reaches the name, the tooltip shows, `aria-describedby` holds, Enter opens the project; an empty description has no tooltip; every column has a separator handle; drag resizes, is remembered across a reload, a click on the handle doesn't open the project, double-click resets; the keyboard resizes within 60 to 900; nothing scrolls sideways at 320 px.
- `test_ui_sweep.py`: BL-291's test replaced by BL-308's (no draft, one `<use>`, the word and the bar shown, in normal contrast, forced colours and `prefers-contrast: more`).
- `test_outline_wordmark.py`: the preview has one path (the word) and no dashes.
- `python3 dev/tools/check.py`: OK; type check (tsc) 0 errors.
