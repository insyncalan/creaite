# The creaite design system: the definitive reference

Written 17-10-2026 for the Product Manager and anyone who mocks up or builds screens. **Everything here was read from the app's own files or measured on the running app** (the dashboard at 1400 × 1000, creaite palette, light mode, fictional data). Where a value is not listed here, the rule is: **do not invent it; take it from the app.**

## 1. The one rule

**A mockup starts from a snapshot of the real page, drawn by the real `style.css`.** Never hand-write CSS for something the app already has. Copy a file from `dev/design-system/pages/` (or `blank.html`) and change its content; use the app's own class names. A mockup that links `system/templates/dashboard/style.css` cannot drift from the app. See `dev/design-system/README.md`.

## 2. Sources of truth, in order

1. `system/templates/dashboard/style.css`: the tokens (`:root` and one block per palette) and every component's rules. The design scale is the block headed `BL-325 scale`.
2. `system/templates/dashboard/src/` and `shell.html`: the markup and which class does what.
3. `dev/COMPONENTS.md`: how shared components are built (agreed 13-10-2026).
4. `dev/V195-DESIGN-SCALE-NOTE.md`: why the scale is what it is.
5. `dev/tools/token_audit.py` and `dev/tools/ui_audit.py`: they flag a size, radius, shadow or layer that is off the scale, and controls drawn two ways.
6. `dev/design-system/pages/*.html` and `shots/*.png`: static snapshots of the real screens (this folder).

## 3. Foundations (the default palette, `creaite`)

### Colour (tokens; never a raw hex in a component)

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

Other colour tokens exist for Today's day band (`--day-*`), the wordmark and the status chips; read them in `style.css` before adding any. Nine palettes exist (creaite, Brightwater, Notion, Linear, Cursor, Claude, Apple, Retro Arcade, Thermo Scan); a mockup is drawn in **creaite** unless asked otherwise, and uses only tokens, so it works in every palette and in dark mode (Alt+D toggles dark in a snapshot).

### Type

- `--font`: "Source Sans 3","Segoe UI",system-ui,-apple-system,Arial,sans-serif
- `--display`: "Schibsted Grotesk","Helvetica Neue",Arial,sans-serif
- `--mono`: "JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,monospace

- Body text is the `--font` stack at **14 px**; table headers, key hints (`kbd`) and small labels use the mono font; page titles (h1) and section titles (h2) use the display font (h1 weight 800, h2 weight 700, tight letter-spacing).
- The size scale (use only these):
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
- `--scrim`: rgba(0,0,0,.25)
- `--ctl-h`: 32px
- `--ctl-h-sm`: 26px
- `--ctl-r`: var(--r-md)
- `--ctl-fs`: var(--fs-sm)
- `--ctl-h-lg`: 40px
- `--ctl-r-lg`: 10px

### Shadows and layers

- `--shadow-sm`: 0 4px 12px rgba(0,0,0,.14)
- `--shadow-md`: 0 8px 24px rgba(0,0,0,.18)
- `--shadow-lg`: 0 12px 32px rgba(0,0,0,.26)
- `--shadow-side`: -14px 0 32px rgba(0,0,0,.16)

- Layers: `--z-under` 0, `--z-raised` 1, `--z-raised-2` 2, `--z-sticky` 3, `--z-sticky-2` 4, `--z-local` 5, `--z-menu` 30, `--z-popup-scrim` 38, `--z-popup` 39, `--z-panel` 40, `--z-panel-over` 41, `--z-chat` 45, `--z-badge` 46, `--z-stage` 47, `--z-pop` 60, `--z-pop-over` 65, `--z-drag` 80, `--z-viewer` 90, `--z-tip` 200, `--z-top` 210, `--z-toast` 220.

## 4. Layout

- The app is a **left rail** (212 px wide expanded, 56 px collapsed; item rows 36 px) and a **top bar** (53 px: search or jump to…, ask creaite, theme) over a **page area** (the content column; most pages centre their content, Today at 80% width).
- A page starts with an **h1 title** (22 px, display font, weight 800), then a one-line sub (13 px, muted), then its controls, then its content.
- Spacing is a **4 px base**; use the scale values only.
- Desktop and 900 px only (Alan, 15-10-2026); no narrow-window design.

## 5. Components, as measured

| Component | Size | Text size / weight | Radius | Padding |
|---|---|---|---|---|
| Page title (h1) | 1139×28 px | 22px / 800 | 0px | 0px |
| Sub text | 911×20 px | 13px / 400 | 0px | 0px |
| Button | 68×32 px | 13px / 500 | 8px | 0px 12px |
| Mini button | 44×26 px | 12px / 500 | 8px | 0px 8px |
| Icon button | 32×32 px | 13px / 400 | 8px | 0px |
| View chip (pill) | 65×28 px | 13px / 400 | 12px | 0px 12px |
| Text input | 220×32 px | 13px / 400 | 8px | 0px 10px |
| Select | 84×32 px | 13px / 400 | 8px | 0px 10px |
| Table header cell | 318×33 px | 12px / 500 | 0px | 8px 12px |
| Table body cell | 318×49 px | 14px / 400 | 0px | 8px 12px |
| Tree (Files) | 250×170 px | 13px / 400 | 12px | 6px |
| Tree row | 236×28 px | 13px / 500 | 8px | 4px 8px |
| Rail | 212×913 px | 14px / 400 | 0px | 10px 8px |
| Rail item | 36×36 px | 13px / 500 | 8px | 0px |
| Top bar | 1188×53 px | 14px / 400 | 0px | 8px 20px |
| kbd | 24×19 px | 12px / 500 | 4px | 0px 4px |

Notes on the table above: the page title row shows the h1's own box (padding is 0); the *View chip* is the page-level pill (28 px high, 12 px radius, 13 px text, a 1 px border, the pressed state is ink-on-light inverted); a **Button** is 32 px high everywhere (`--ctl-h`), a **Mini button** 26 px (`--ctl-h-sm`), an **Icon button** 32 × 32. Inputs and selects are 32 px. A table has a 12 px radius card around it, 12 px mono uppercase headers, 14 px body, 8 × 12 px cell padding.

### Class names to use (checked in the snapshots)

`.btn` (add `.primary` for the main action), `.mini` (the compact button), `.ib` (icon button, with `.sm`), `.vchip` (a view or filter pill, `aria-pressed` for selected), `.tag` and `.badge` (small labels and counts), `.tbl` (a table), `.card`, `.toolbar` (a row of filters and controls), `.sub` (muted line), `kbd`, `.wrapmax` (the content column), `#tree` (the Files folder list, with its buttons as rows) and `.ddmenu` (a dropdown menu). The popup calendar is the app's own Picker; copy it from a snapshot with a date field rather than drawing one. The icons are the app's own SVGs (`svg.i`); the sparkle is the `spark` icon.

## 6. Patterns (how screens are put together)

- **List or table page:** title, sub, a toolbar of filter controls (search input, select, date fields with a calendar icon, a Refresh button), then the table card. See `pages/files.html`, `pages/work.html`, `pages/people.html`, `pages/activity.html`.
- **Filters:** pills for views, a search input, selects, a funnel for more (Work, Review, People); applied filters are chips under the bar.
- **Peek (side panel):** an item opens over the right half of the page and is editable in place; ⌘↵ saves and closes, Esc closes.
- **Dialogs:** a centred card on a scrim, Cancel and the main action at the foot.
- **Messages:** a toast at the foot; Undo waits for you.
- **Empty states** say the next step.
- **Dates:** DD-MM-YYYY on screen; the popup calendar for any date field.
- **Words:** British English, plain, short; no jargon.

## 7. Known rough edges (so a mockup does not copy them)

These are in the app today and are being tidied (#193): line heights have no tokens; 11 font sizes, 11 radii and 4 layers are raw values; five button styles and three input heights exist; the page titles are 34 px on Today and Help and 22 px elsewhere. When in doubt, use the values in section 5.

## 8. Checklist before a mockup is shown

1. Started from a snapshot in `dev/design-system/pages/` or `blank.html`, linking the real `style.css`.
2. Every control is an existing class at its real size (buttons 32 px, inputs 32 px, pills 28 px).
3. Colours are tokens only; it works in dark (Alt+D).
4. New components (genuinely new) are in one clearly marked block, built from tokens, and called out in the write-up as new.
5. Fictional data only; no real names.
