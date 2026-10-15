# Sprint polish-themes: Settings icon, rail refinement, and four new themes (BL-191, BL-192, BL-40)

Branch `sprint-polish-themes`, worktree `../creaite-polish-themes`, from `main`. Three small items plus four new themes (Claude, Apple, Retro Arcade, Thermo Scan) with full coverage audit. Rough size: six to eight days. This is UI polish + branding work that ships as v1.5.1.

> **Scrum master's notes (11-10-2026), for v1.5.1:**
> - **The four designs** are in `dev/reference/themes/`.
> - **The rules every theme already keeps** (BL-40, FR-57) come before the design's raw colours. Contrast is checked by the theme tests; health colours are always an icon plus text; there are no external resources; there is a light and a dark set.
> - **Retro Arcade and Thermo Scan use pure, saturated colours** (#0000FF, #FF0000, #00FF00 on black or navy). Take their character, but derive tokens that pass contrast (text 4.5:1, icons and boundaries 3:1), and record each change in BUILD.
> - **A dark-only design** gets a derived light set, as Linear's did; a light-only design gets a derived dark set, as Cursor's did.
> - **Since this brief was written, v1.4.0 and v1.5.0 added screens:**
>   - the peek;
>   - the Milestones page (Plan and Movement, with the INTERNAL VIEW and CLIENT VIEW marks);
>   - the errors banner;
>   - the counts as links.
>
>   Include them in the colour audit and the per-theme checks.
> - **There are now five themes plus four,** so nine.
> - **Release:** this sprint is **v1.5.1**; `VERSION` changes only at the release. Notes go in `dev/release-notes/1.5.1.md`.

## Items

Commit each separately, in this order.

### 1. BL-192: Change Settings icon from sliders to gear (S)

The Settings page in the rail currently uses `ic("sliders")`, which conflicts visually with the rail customization control (also sliders, BL-191). A gear icon is more conventional for Settings.

- **Change:** In `system/templates/dashboard.html`, RAIL_ITEMS list, change Settings icon from `ic("sliders")` to `ic("gear")`
- **Update Help:** if Help mentions the Settings icon by name, update it
- **Size:** S — one-line change
- **Touches:** `system/templates/dashboard.html` (RAIL_ITEMS, one icon name), Help (if it names icons)

### 2. BL-191: Rail customization via right-click, remove the visible button (S)

The rail customization currently has a visible "sliders" button at the foot. Move this control into a right-click context menu on the rail itself for less visual clutter.

- **Current:** `renderRail()` includes a `{ic("sliders")} Customise…` button at the foot
- **Change:** Remove the visible button; add right-click handler on the rail container that opens the same popover
- **Reachability:** Right-click remains discoverable; keep the Settings › Appearance row for those who prefer menu-based access
- **What stays:** all customization options (hide/show, reorder, display mode), Settings › General › Appearance row, the "…" button for hidden items, settings.json persistence
- **Touches:** `system/templates/dashboard.html` (right-click handler on `.rail`, remove the button, popover stays), `dev/dashboard-spec.md`, Help
- **Tests:** right-click opens popover; Settings › Appearance still works; no visible sliders button

### 3. BL-40a: Claude theme (S–M)

Build a new creaite theme based on Anthropic's Claude.com design: warm cream canvas, coral primary accent, dark navy surfaces, serif display headlines (adapted to creaite's constraints).

- **Theme name:** "Claude"
- **Source:** `dev/reference/themes/DESIGN-Claude.md` (lines 1–100, the color system)
- **Color palette:**
  - Canvas (default bg): `#faf9f5` (warm cream)
  - Primary (CTAs, accent): `#cc785c` (coral)
  - Primary active: `#a9583e` (coral darker)
  - Text/ink: `#141413` (warm dark)
  - Surface dark: `#181715` (dark navy for cards)
  - Success: `#5db872` (green)
  - Warning: `#d4a017` (gold)
  - Error: `#c64545` (red)
  - Muted text: `#6c6a64`
  - Borders/hairline: `#e6dfd8`
  - On dark text: `#faf9f5` (cream tint)
  
- **File location:** `system/templates/themes/claude.css` (or entry in a theme-colors map in dashboard.html, per current structure)
- **What to theme:** All views — Today, Intake, Work, Review, Projects, People, Files, Settings, Activity
  - Primary buttons use coral
  - Card backgrounds use cream or dark navy (alternating where possible)
  - Text uses warm black
  - Links use coral
  - Health/status indicators use success/warning/error
  
- **Touches:** `system/templates/dashboard.html` (add Claude theme to THEMES array), create `system/templates/themes/claude.css` (or inline CSS if current structure doesn't use separate files)

### 4. BL-40b: Apple theme (S–M)

Build a new creaite theme based on Apple's minimalist design: pure white canvas, single action blue, near-black text, photography-first (adapted for creaite's data-driven UI).

- **Theme name:** "Apple"
- **Source:** `dev/reference/themes/DESIGN-Apple.md` (lines 6–27, the color system)
- **Color palette:**
  - Canvas (default bg): `#ffffff` (pure white)
  - Primary (CTAs, accent): `#0066cc` (Action Blue)
  - Primary focus: `#0071e3` (darker blue for focus ring)
  - Text/ink: `#1d1d1f` (near-black)
  - Surface tile dark: `#272729` or `#2a2a2c` (near-black for dark cards)
  - Surface parchment: `#f5f5f7` (off-white alternate)
  - Success: use blue variants for status
  - Muted text: `#7a7a7a`
  - Borders: `#e0e0e0`
  - On dark text: `#ffffff` (pure white)

- **File location:** `system/templates/themes/apple.css` (or same structure as Claude)
- **What to theme:** All views — with an emphasis on minimal chrome, clean hierarchy, blue as the only accent
  - Primary buttons use Action Blue with pill radius (where possible)
  - Card backgrounds use white or parchment
  - Text uses near-black
  - Links use Action Blue
  - Borders are minimal, light gray hairlines
  - Avoid decorative shadows (Apple philosophy: only on product imagery, not on UI)

- **Touches:** `system/templates/dashboard.html` (add Apple theme to THEMES array), create `system/templates/themes/apple.css`

### 5. BL-40c: Retro Arcade theme (S–M)

Build a new creaite theme based on nostalgic 1980s arcade aesthetics: vivid primary colors, black background, pixel-art energy, playful and bold.

- **Theme name:** "Retro Arcade"
- **Source:** `dev/reference/themes/DESIGN-Retro-Arcade.md` (lines 5–10, the color system)
- **Color palette:**
  - Canvas (default bg): `#000000` (black)
  - Primary (CTAs, accent): `#0000FF` (electric blue)
  - Secondary: `#FF0000` (cherry red)
  - Tertiary: `#FFFF00` (bright yellow)
  - Success: `#00FF00` (lime green)
  - Warning/accent: `#FFFF00` (bright yellow)
  - Error: `#FF0000` (cherry red)
  - Accent emphasis: `#800080` (purple)
  - Alternate: `#00FFFF` (cyan)
  - Text: `#FFFFFF` (white)

- **File location:** `system/templates/themes/retro-arcade.css`
- **What to theme:** All views — bold, high-contrast, playful aesthetic
  - Black background throughout (dark mode by design)
  - Bright primary colors for CTAs and interactive elements
  - White text on black for maximum contrast
  - Success uses bright green, errors use cherry red, warnings use bright yellow
  - Links use electric blue
  - Cards have bright colored borders (cyan, purple, yellow borders)
  - Pixel-friendly: keep it bold and readable at any size

- **Touches:** `system/templates/dashboard.html` (add Retro Arcade theme to THEMES array), create `system/templates/themes/retro-arcade.css`

### 6. BL-40d: Thermo Scan theme (S–M)

Build a new creaite theme based on thermal imaging and infrared technology: dark navy background, thermal spectrum colors (blue→green→red), technical/analytical aesthetic.

- **Theme name:** "Thermo Scan"
- **Source:** `dev/reference/themes/DESIGN-Thermo-Scan.md` (lines 6–11, the color system)
- **Color palette:**
  - Canvas (default bg): `#050B26` (dark navy)
  - Primary: `#050B26` (dark navy background)
  - Secondary: `#FFFFFF` (white text)
  - Tertiary/accent: `#FFC800` (golden yellow for CTAs)
  - Success: `#00FF00` (green — cool in thermal spectrum)
  - Warning: `#FFC800` (golden yellow)
  - Error: `#FF0000` (red — hot in thermal spectrum)
  - Secondary accent: `#0000FF` (cool blue)
  - Text: `#FFFFFF` (white)

- **File location:** `system/templates/themes/thermo-scan.css`
- **What to theme:** All views — technical, analytical, thermal spectrum aesthetic
  - Dark navy background (dark mode by design)
  - White text on dark for high contrast readability
  - Golden yellow CTAs (warm accent)
  - Thermal spectrum colors: red for hot/errors, green for cool/success, blue for secondary
  - Links use golden yellow
  - Cards have subtle thermal gradient indicators (optional: blue→red spectrum on severity)
  - Monospace-inspired typography feel (Share Tech Mono aesthetic)

- **Touches:** `system/templates/dashboard.html` (add Thermo Scan theme to THEMES array), create `system/templates/themes/thermo-scan.css`

### 7. Theme coverage audit and Today page enhancements (M)

Ensure both new themes (and existing ones) are fully applied across **all pages**, with special focus on **Today** page which has the most visual variety.

- **Audit checklist:**
  - **Today page:** cards, health badges, priority labels, time tags, quick-capture input, week-ahead section, needs-attention reminders
  - **Intake page:** file upload area, calendar preview, proposed items
  - **Work page:** list rows, board cards, priority colors, status tags, due-date styling
  - **Review page:** proposal cards, conflict states, approval buttons
  - **Projects page:** project cards, health displays, forecast dates
  - **People page:** people list, VIP indicators, active/inactive states
  - **Files page:** file list, folder icons, file-type colors
  - **Settings page:** toggle switches, input fields, card backgrounds
  - **Activity page:** change-log rows, entry types, undo buttons
  - **Fixed items:**
    - Health badges: ensure they use semantic colors (ok/at-risk/off-track) mapped to theme colors, not hardcoded hex
    - Priority labels: Urgent/High/Medium/Low colors theme-aware
    - Status tags: Open/Closed/Delayed/Cancelled colors theme-aware
    - Due-date warnings: overdue, due-soon, weekend indicators use theme semantic colors
    - Links: all links use primary theme color
    - Buttons: primary/secondary buttons use theme palette
    - Borders: all borders use theme hairline color
    - Text hierarchy: body, muted, and accent text use theme colors

- **Steps:**
  1. Read the current THEMES array in dashboard.html and understand the current structure
  2. For each page view (`#v-today`, `#v-intake`, `#v-work`, etc.), scan for hardcoded colors and replace with CSS variables tied to the theme
  3. Test all five themes (Brightwater, creaite, Notion, Linear, Cursor, Claude, Apple) on each page
  4. Special focus: Today page — ensure all badges, tags, and warnings render correctly in all themes
  5. Check light and dark variants of each theme (where applicable)

- **Touches:** `system/templates/dashboard.html` (find all `color:`, `background:`, `border-color:` inline styles and replace with CSS variables; update all status/health/priority color logic), possibly `system/templates/themes/*.css` files if separate

## Decisions taken

| Question | Default |
|---|---|
| Should Claude theme use serif headlines? | Adaptation only: keep sans-serif for readability in creaite's dense UI; use warm cream canvas + coral accent as the signature. Full serif typography is too editorial for a work tool. |
| Should Apple theme use pill-radius buttons everywhere? | Only on primary CTAs and where it doesn't compromise UI density. Utility buttons stay compact. |
| Should themes be separate CSS files or inline in dashboard.html? | Check current structure. If separate (likely), place at `system/templates/themes/claude.css` and `system/templates/themes/apple.css`. If inline, add to the THEMES object. |
| How to handle status colors (health, priority, due-date warnings)? | Create a theme-aware color function or CSS variable map: `var(--status-ok)`, `var(--status-at-risk)`, `var(--status-off-track)`, `var(--priority-urgent)`, etc. All logic reads from these, not from hardcoded hex. |
| Which page has the highest color usage? | Today — health badges, priority tags, status indicators, time warnings, week-ahead cards. Test it first. |

## Boundaries

- **Owns:**
  - BL-192: Settings icon swap in RAIL_ITEMS
  - BL-191: Right-click handler on rail, removal of visible button
  - BL-40a: Claude theme colors and application across all views
  - BL-40b: Apple theme colors and application across all views
  - Theme color audit: replacing hardcoded colors with theme variables in all page views

- **Don't edit:** the dashboard data structure, the tracker, the report skills, the help system (unless help text needs to update to reflect icon/button changes)

- **Testing:** all five themes (or seven with the new ones) on all seven views (Today, Intake, Work, Review, Projects, People, Files, Settings, Activity) in light and dark mode (where applicable). Special emphasis: Today page with all its status indicators.

## Done when

- **Changes:** 
  - BL-192: Settings icon swapped from sliders to gear
  - BL-191: Right-click handler on rail, visible button removed
  - BL-40a: Claude theme created and registered
  - BL-40b: Apple theme created and registered
  - BL-40c: Retro Arcade theme created and registered
  - BL-40d: Thermo Scan theme created and registered
  - Theme color audit: all views updated with CSS variables instead of hardcoded colors

- **Testing:**
  - All nine themes (5 existing + 4 new) render without broken colors on Today, Intake, Work pages
  - All new themes render correctly on all seven views (Today, Intake, Work, Review, Projects, People, Files, Settings, Activity)
  - Hardcoded colors in all views replaced with CSS variables
  - Health badges, priority labels, status tags, due-date warnings all respect theme colors across all nine themes
  - Right-click on rail opens customization popover; Settings › Appearance still works
  - Settings icon changed from sliders to gear
  - Each theme (especially Retro Arcade and Thermo Scan with bold colors) tested for contrast and readability
  - Light modes (Claude, Apple) and dark modes (Retro Arcade, Thermo Scan) both work correctly

- **Docs:** `dev/dashboard-spec.md` (complete theme coverage list, color variables, nine themes), Help (icon/button changes, new themes listed), `dev/BUILD.md` (sprint summary), release notes for v1.5.1 listing all four new themes

- **Commits:** one per item (BL-192, BL-191, Claude theme, Apple theme, Retro Arcade theme, Thermo Scan theme, audit fixes), with attribution lines

## Hand-offs

None — this sprint is self-contained. The themes integrate with the existing Settings › General › Appearance section and THEMES selection.
