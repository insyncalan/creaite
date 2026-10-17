# The creaite design system: the definitive reference

**Taken from:** commit `c237a088` on `origin/v220-int-gate` (its `VERSION` file says 2.1.0; this is the v2.2.0 line, not yet cut), on 2026-10-17. The stylesheet in this folder, `style.snapshot.css`, is a copy of that commit's `system/templates/dashboard/style.css`, and every snapshot page is drawn by it. Palette creaite, light mode, 1400 × 1000, fictional sample data. Details: `SNAPSHOT.json`.

**It describes that line, not older or newer ones.** Differences already known: **#198** narrows the expanded rail to 188 px in v2.2.0 (not in this snapshot until it is merged); **#193** (`tokens-193-full`) adds line-height tokens and moves raw sizes, radii and layers onto tokens. Refresh the snapshots after each of those lands (section 9).

Rule for readers: every number below was read from `style.snapshot.css` or measured on the rendered pages. Where an element comes in more than one size, the table lists each size and how many were seen, so nothing here claims a single value that is not true.

## 1. The one rule

**A mockup starts from a snapshot of the real page, drawn by the real stylesheet.** Copy a file from `pages/` (or `blank.html`) and change its content, using the app's own class names. Never hand-write CSS for something the app already has. See `README.md`.

## 2. Sources of truth, in order

1. `system/templates/dashboard/style.css`: the tokens and every component's rules (here `style.snapshot.css`). The scale is the block headed `BL-325 scale`.
2. `system/templates/dashboard/src/` and `shell.html`: the markup and which class does what.
3. `dev/COMPONENTS.md`: how shared components are built.
4. `dev/V195-DESIGN-SCALE-NOTE.md`: why the scale is what it is.
5. `dev/tools/token_audit.py`, `dev/tools/ui_audit.py`: they flag anything off the scale.
6. This folder: `pages/*.html`, `shots/*.png`, `blank.html`, `gallery.html`.

## 3. Foundations (palette `creaite`)

### Colour

| Token | Light | Dark |
|---|---|---|
| `--bg` | `#F3F6F7` | `#0F1518` |
| `--surface` | `#FFFFFF` | `#171E22` |
| `--sunk` | `#EAF0F2` | `#1E272C` |
| `--ink` | `#14212A` | `#E4EAED` |
| `--muted` | `#4D5C66` | `#A2AEB5` |
| `--faint` | `#626E76` | `#828E95` |
| `--line` | `#D7DFE3` | `#2A343A` |
| `--line-strong` | `#B9C5CB` | `#3D4950` |
| `--accent` | `#0B6E7F` | `#5FC4D6` |
| `--accent-ink` | `#FFFFFF` | `#00323A` |
| `--accent-soft` | `#DCEFF2` | `#16363C` |
| `--bad` | `#B3261E` | `#F2B8B5` |
| `--bad-soft` | `#FBE7E5` | `#3B1F1D` |
| `--warn` | `#8A5A00` | `#F0C66B` |
| `--warn-soft` | `#FBF0DA` | `#3A2C10` |
| `--ok` | `#2E6B3A` | `#9FD6A5` |
| `--ok-soft` | `#E3F2E5` | `#1D3322` |
| `--focus` | `#0B6E7F` | `#5FC4D6` |
| `--inverse` | `#14212A` | `#E4EAED` |
| `--inverse-ink` | `#E4EAED` | `#171E22` |

More colour tokens exist (Today's `--day-*`, `--bad-ink`, `--knob`, `--stage-dot`); read them in `style.snapshot.css` before adding one. Nine palettes exist (creaite, Brightwater, Notion, Linear, Cursor, Claude, Apple, Retro Arcade, Thermo Scan); some change shapes as well as colours (for example a palette sets the view pill's radius). A mockup is drawn in **creaite** unless asked, uses tokens only, and must work in dark (Alt+D flips a snapshot).

### Type

- `--font`: "Source Sans 3","Segoe UI",system-ui,-apple-system,Arial,sans-serif
- `--display`: "Schibsted Grotesk","Helvetica Neue",Arial,sans-serif
- `--mono`: "JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,monospace

- Body is the `--font` stack at 14 px. Page and section titles (`h1`, `h2`, `h3`) use `--display`; table headers (`th`) and key hints (`kbd`) use `--mono`.
- Table headers in the creaite palette are mono, 12 px, weight 500, uppercase, letter-spaced `.08em`; that comes from the palette's own block (not the base).

### Scale (the `BL-325` block)

- `--fs-2xs`: 10px
- `--fs-xs`: 12px
- `--fs-sm`: 13px
- `--fs-md`: 14px
- `--fs-lg`: 16px
- `--fs-xl`: 18px
- `--fs-2xl`: 22px
- `--fs-display`: 34px
- `--r-sm`: 4px
- `--r-md`: 8px
- `--r-lg`: 12px
- `--r-xl`: 16px
- `--r-pill`: 999px
- `--ctl-h`: 32px
- `--ctl-h-sm`: 26px
- `--ctl-r`: var(--r-md)
- `--ctl-fs`: var(--fs-sm)
- `--ctl-h-lg`: 40px
- `--ctl-r-lg`: 10px

Spacing is a 4 px base (2 px steps to 16, 4 px steps to 32, 8 px steps above); written as plain px.

### Shadows and layers

- `--shadow-sm`: 0 4px 12px rgba(0,0,0,.14)
- `--shadow-md`: 0 8px 24px rgba(0,0,0,.18)
- `--shadow-lg`: 0 12px 32px rgba(0,0,0,.26)
- `--shadow-side`: -14px 0 32px rgba(0,0,0,.16)
- A palette may also set `--shadow-card` and `--shadow-pop` (creaite sets soft layered ones; some palettes set none).
- Layers: `--z-under` 0, `--z-raised` 1, `--z-raised-2` 2, `--z-sticky` 3, `--z-sticky-2` 4, `--z-local` 5, `--z-menu` 30, `--z-popup-scrim` 38, `--z-popup` 39, `--z-panel` 40, `--z-panel-over` 41, `--z-chat` 45, `--z-badge` 46, `--z-stage` 47, `--z-pop` 60, `--z-pop-over` 65, `--z-drag` 80, `--z-viewer` 90, `--z-tip` 200, `--z-top` 210, `--z-toast` 220.

### Rail width

`--rail-w` is 224px (expanded 224 px, icons only 56 px, icons with labels 76 px).

## 4. Layout

- Left **rail** (`.rail`, items `.nv` at 36 px) beside a **top bar** (`.bar`, 53 px: the search, ask creaite and the theme switch) over the **page** (`.view` sections; most pages put their content in `.wrapmax`).
- A page opens with `h1`, then a muted line (`.sub`, 13 px), then its controls (`.toolbar`, 32 px), then its content.
- Desktop and 900 px only (Alan, 15-10-2026).

## 5. Components, as measured

Each row is every visible instance of the selector across the 12 snapshot pages: the heights seen, the text sizes, the weights, the corner radii, with the number of instances in brackets. Where there is more than one value, **both are real**: read the note, and when unsure copy the markup from the page where the control already is.

| Component | Selector | Height seen | Text size | Weight | Radius | Note |
|---|---|---|---|---|---|---|
| Button | `.btn` | 32 (50), 26 (3) | 13px (50), 12px (3) | 500 (53) | 8px (53) | 13 px text; a few compact 26 px ones sit in dense rows |
| Primary button | `.btn.primary` | 32 (2), 26 (1) | 13px (2), 12px (1) | 500 (3) | 8px (3) | accent fill, `--accent-ink` text |
| Quiet button | `.btn.quiet` | 32 (12) | 13px (12) | 500 (12) | 8px (12) | no border or fill, accent text, `--accent-soft` on hover (style.snapshot.css line 541) |
| Mini button | `.mini` | 26 (14) | 12px (14) | 500 (14) | 8px (14) | the compact button, `--ctl-h-sm` |
| Icon button | `.ib` | 32 (48), 34 (8), 30 (4) | 13px (60) | 400 (60) | 8px (60) | 32 × 32 normally; 34 and 30 appear (see below) |
| Icon button, small | `.ib.sm` | 32 (42), 34 (8) | 13px (50) | 400 (50) | 8px (50) | `.sm` changes only the icon size (16 px), not the box |
| Icon button, bordered | `.ib.bd` | 32 (6) | 13px (6) | 400 (6) | 8px (6) | a `--line` border and `--surface` fill (line 1705) |
| Round icon button | `.iconbtn` | 32 (16) | 14px (16) | 400 (16) | 50% (16) | a circle, 32 px |
| View pill | `.vchip` | 28 (14) | 13px (14) | 400 (14) | 12px (14) | radius 12 in creaite (Linear and Cursor draw it as a full pill); selected = ink fill |
| Tag | `.tag` | 17 (11), 20 (4) | 12px (15) | 400 (10), 500 (5) | 0px (11), 999px (4) | plain muted 12 px text by default; the pill form is added by its context (line 3099, 3565) |
| Chip | `.chip` | 20 (3) | 12px (3) | 500 (3) | 999px (3) | a small pill, 20 px |
| Filter chip | `.fchip` | 24 (1) | 13px (1) | 400 (1) | 999px (1) | a removable filter, 24 px pill |
| Key hint | `.kbd` | 19 (13) | 12px (13) | 500 (13) | 4px (13) | mono |
| Search (top bar) | `.search` | 36 (12) | 14px (12) | 400 (12) | 8px (12) | the app-wide search; `--bg` fill |
| Text input | `input[type=text]` | 32 (6), 28 (2) | 13px (8) | 400 (8) | 8px (8) | `--ctl-h` 32; 28 px inside some date fields |
| Search input | `input[type=search]` | 32 (5), 40 (1) | 13px (5), 14px (1) | 400 (6) | 8px (4), 0px (1) | 32; the vault search on Files is 40 (`--ctl-h-lg`) |
| Select | `select` | 32 (8) | 13px (6), 14px (2) | 400 (8) | 8px (8) | 32 |
| Date field button | `.dbtn` | 28 (2), 32 (2) | 13px (4) | 400 (4) | 8px (4) | the calendar button beside a date field |
| Switch | `.switch` | 24 (5) | 13px (5) | 400 (5) | 999px (5) | a 24 px pill |
| Table card | `.tbl` | 70 (1), 623 (1), 329 (1) | 14px (10) | 400 (10) | 12px (10) | 12 px radius (creaite palette) |
| Table header cell | `.tbl th` | 33 (31), 35 (10) | 12px (41) | 500 (41) | 0px (41) | mono, uppercase, letter-spaced (creaite palette block) |
| Table body cell | `.tbl td` | 49 (114), 57 (33), 59 (16) | 14px (161), 12px (24) | 400 (181), 500 (4) | 0px (185) | rows 49 to 59 px depending on content |
| Tabs | `.tabs button` | 38 (11) | 14px (11) | 500 (11) | 0px (11) | underline style |
| Card | `.card` | 173 (3), 344 (2), 127 (1) | 14px (19) | 400 (19) | 12px (19) | 12 px radius (creaite palette) |
| Toolbar | `.toolbar` | 32 (4) | 14px (4) | 400 (4) | 0px (4) | a row of controls, 32 px |
| Rail item | `.nv` | 36 (84) | 13px (84) | 500 (77), 700 (7) | 8px (84) | 36 px; the current page is weight 700 |
| Top bar | `.bar` | 53 (12) | 14px (12) | 400 (12) | 0px (12) | padding 8 × 20; holds the search and ask creaite |
| Page title | `h1` | 28 (10), 34 (1), 40 (1) | 22px (10), 34px (2) | 800 (12) | 0px (12) | display font; 22 px, and 34 px on Today and Help |
| Section title | `h2` | 22 (22), 33 (6), 23 (3) | 16px (28), 22px (6) | 700 (34) | 0px (34) | display font; 16 px mostly, 22 px in some places |
| Sub-section title | `h3` | 24 (13), 16 (1) | 16px (13), 12px (1) | 700 (13), 500 (1) | 0px (14) | 16 px, weight 700 |

Two classes that look like components but are **not to be drawn**: `.fsel` (a 36 px, 16 px-radius select, `style.snapshot.css` line 676) is **dead CSS on this line: no screen uses it**, so it is not rendered and must not be copied into a mockup; `.fgrid` (the item details form, line 804 onward) is styled in the CSS (its fields have a 1 px `--faint` border, 8 px radius and 4 × 8 px padding at line 806) but is not rendered in these snapshots, so its sizes are **read from the CSS, not measured**. Menus, dialogs and the peek exist in the running app but not in the static snapshots; copy their markup from the app rather than redrawing them.

### Two things worth knowing

- **There is no generic badge.** The rail's count (`.rail .badge`) is its own thing (18 px, radius 8, accent fill); other counts are `.n`, `.cnt` or text in a table.
- **Controls differ by context.** A control's size comes from its container as well as its class: in the same snapshot, a text field is 32 px in a toolbar, 28 px inside some date fields, 36 px as the top-bar search and 40 px as the vault search. Do not normalise them in a mockup.

## 6. Patterns (as the snapshots show them)

- **List page** (`pages/files.html`, `work.html`, `people.html`, `activity.html`): `h1`, controls (`.toolbar`), a `.tbl` card.
- **Filters:** `.vchip` pills for views, a search input, selects, date fields with a calendar button (`.dwrap` and `.dbtn`).
- **Peek, dialogs, toasts and menus** exist in the running app and are not in the static snapshots; copy them from the app.
- **Dates** on screen: DD-MM-YYYY. **Words:** British English, plain, short.

## 7. Known rough edges (do not copy them)

On this line (Team Stark's recount of the gate's stylesheet, 17-10-2026): font sizes have **19** distinct raw values, border radii **13**, layers **10** raw uses in **7** values, line heights **22** distinct values with no tokens, and **49** distinct raw heights. Buttons, icon buttons and fields come in more than one size (section 5), and page titles are 34 px on Today and Help and 22 px elsewhere. #193 (`tokens-193-full`) tidies sizes, radii, layers and line heights; the heights and the title sizes stay open.

## 8. Checklist before a mockup is shown

1. Started from a snapshot in `pages/` or `blank.html`; the file's header says which commit it came from.
2. Every existing control is an existing class, at the size the snapshot shows.
3. Colours are tokens only; it works in dark (Alt+D).
4. Anything genuinely new sits in one block marked `/* NEW */`, built from tokens, and the write-up says it is new.
5. Fictional data only; no real names.

## 9. Keeping it right

- Snapshots come from the **release line the next release is built on**, never from main when main is behind: `python3 dev/tools/design_system_snapshots.py --repo <checkout> --label <branch>`.
- Refresh after: the v2.2.0 cut, #198 (rail width) and #193 (tokens) landing, and any release that changes how a screen looks. Update the top of this file from `SNAPSHOT.json` each time.
- Team Stark checks this file against the code when it changes (#205).
