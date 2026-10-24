# v1.9.5: the UI audit's fix-first findings

14-10-2026 · branch `v195-ui-fixes` (origin/main + `dev-ui-audit`) · Team 2 · source: `dev/reviews/ui-audit-2026-10-14.md`

Alan's decisions are kept: Word stays in the Brightwater brand, and Projects keeps its written-out dates. Neither was touched.

Proof is `python3.14 dev/tools/token_audit.py` before and after, and a rendered `dev/tools/ui_audit.py` run after (creaite and Brightwater, light and dark, 1400x1000, axe-core 4.10.2, throwaway vault).

## Token audit totals

| Check | Before | After |
|---|---:|---:|
| 2 Undefined tokens | 3 (P1) | 0 |
| 3 Theme completeness | 10 (P1) | 0 |
| 7 Contrast | 39 (P1) | 5 (all in `dev/reference/dashboard-reference.html`, the dev mock-up, which is not shipped) |
| 8 Cross-surface | 28 | 21 (all prep-page findings gone) |
| 6 Near-duplicate tokens | 23 | 24 (+1: Brightwater's new `--day-sun` #AB72FB sits ΔE 1.3 from `--violet`, as expected) |
| **P1 overall** | **62** | **15** (10 hard-coded colours and 5 in the reference: neither is on the fix-first list) |

## The findings

| # | Finding | What changed | Before → after |
|---|---|---|---|
| 1 | `--saffron` has no rule for the OS dark mode | Added `@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--saffron:#F2B544}}` | 9 palette findings (system dark #C7860E against explicit dark #F2B544) → 0 |
| 2 | `--line-strong` undefined in creaite, Brightwater and Notion | Defined in the base and in those three palettes, light and dark (creaite #B9C5CB/#3D4950, Brightwater #BDBDC7/#575A58, Notion #D1D0CD/#4A4A4A, base #C9D0D6/#3E474E) | undefined in 6 palette-modes → 0 |
| 3 | `--bad-ink` on `--bad` in dark is 1.71:1 | `--bad-ink:#601410` in the base dark rules, used by the 5 palettes that take it from the base. Also, `.edprob`, `.evstate.none` and `.ckdel` used `var(--bad-ink,var(--bad))` as plain text. `--bad-ink` is always set, so they drew white on a light ground. They now use `--bad` | 1.71:1 → 7.66:1 (5 findings → 0) |
| 4 | `--faint` under 4.5:1; `--day-past` under 3:1; Brightwater's now-line at 2.95:1 | Each colour moves the shortest distance towards black (light mode) or white (dark mode) that passes on every ground it is used on (bg, surface and sunk; the day page). 12 `--faint` values (base included) and 15 `--day-past` values changed, plus Brightwater's light `--day-sun` (#AE74FF → #AB72FB; the brand `--violet` is unchanged) | 34 dashboard contrast findings → 0. For example, creaite light faint went from 3.68:1 to 4.55:1 (#6F7D86 → #626E76), and creaite light day-past from 1.91:1 to 3.04:1 (#A9B6BD → #858F94) |
| 5 | `.colrz` has `role=separator` without `aria-valuenow` | `colResizer` (work.js) sets `aria-valuenow` (the width in px, kept current as it changes and on focus), `aria-valuemin` 60, `aria-valuemax` 900 and `aria-orientation` vertical | axe aria-required-attr: 220 nodes (report) → 0 |
| 6 | `th[data-psort]` uses ARIA that `th` doesn't allow | The `th` keeps `aria-sort` and `data-psort`. `role="button"` and `tabindex` are gone, and the label is now a real `<button class="thsort">` (drawn as the heading text), so sorting works from the keyboard as well | axe aria-allowed-attr on `th[data-psort]`: 40 nodes → 0 |
| 7 | `--pc` and `--d2` never set | Removed the dead `.tl .ms i.pc` rule (no code renders `.tl`). `build_guides.py` gives the guides `--d2:200ms` (the dashboard's), and the guides are rebuilt | 3 undefined-token findings → 0 |
| 8 | Control drift (`.btn`, inputs, section headings) | New `--ctl-h` 32px, `--ctl-r` 8px and `--ctl-fs` 13px, read by `.btn`, `#workQ`, `#pmQ`, `#rvQ` and the outliers. Today's buttons drop their own size rules (`.daynone .btn` 28px, `.setupbl .rmgo .btn` and `.rmrun` 30px/12px), as does the setup list's `.mini` (30px). Intake's fields (`.qcrow`, 30px/6px), Activity's (`.actdates`, 30px/6px; `.actsearch`, 34px), and Settings' (`.srow`, about 28px/6px) move onto the tokens. Files' search (`.vsearch`) stays 40px/10px: it is the page's centred search bar, with its 40px Ask button beside it, and `test_pages` (SearchBarTests) holds that by design. `h2` is 15px on Review (was 14px) and on Intake (was 18px) | Rendered (creaite light): `.btn` went from 3 styles to 1 (32px/13px on every page). Inputs and selects went from 6+3 styles to 2 at 32px/8px, plus Files' 40px search bar (kept on purpose) and Activity's borderless field inside its 32px box. `h2` went from 4 styles to 1 outside Help, at 15px on Activity, Intake, Review and Settings. `.mini` is now 26px everywhere |
| 9 | Help ignores theme fonts | `:root[data-palette] #v-help` maps `--hp-body` to `--font`, `--hp-display` to `--display` (or `--font`) and `--hp-mono` to `--mono`. Retro Arcade and Thermo Scan head in `--mono`, as their pages do. With creaite, Help looks the same as before, and the standalone guides are unchanged | Rendered, Brightwater: Help in Source Sans 3, Schibsted Grotesk and JetBrains Mono → Help in ABC Diatype |
| 10 | The prep page uses the system font and its own status colours | Now uses the dashboard's bad, ok, warn, warn-soft and muted colours (light and dark) and its type stacks: `--font` for Source Sans 3 text, `--display` for Schibsted Grotesk headings | Prep-page cross-surface findings: 5 P2 and 2 P3 → 0 |

## Open points for Alan

- **Prep page fonts:** the page names the creaite fonts but does not embed them. BL-98 and `test_prep_page_content` keep the page to one file with no `url()`, and embedding a font needs `url(data:…)`. So the named fonts show only where they are installed; otherwise the page uses the system font. Embedding them would add about 100 KB per page and a change to that rule.
- **Intake's section names:** "Calendar Import" and "Upload Files" are still in Title Case. These names are used across Help, the rules, Settings and the skills, so renaming them is a wording change for the whole product, not a style fix.
- **Today's labels:** Today keeps its uppercase section labels and its 34px title by design.
- **Not on the fix-first list (left alone):**
  - Brightwater's `.btn` radius is still 4px (its own palette rule), while its fields use 8px.
  - The side panel's `.pdraft` and `.pk-ask` buttons are unchanged.
  - Axe still reports the Settings category buttons (`button[data-scat]`, aria-allowed-attr) and `.spark` aria-label (aria-prohibited-attr).

## Goldens re-recorded (test_snapshots)

The goldens hold only DOM, not CSS, so none of the colour or font fixes changed them.

| Golden | Why |
|---|---|
| projects.html, today.html, work.html | Fix 5: the resize handles' new ARIA attributes |
| people.html | Fix 6: the `th` loses `role` and `tabindex`, and the label becomes `<button class="thsort">` |
| ask.html | `normalise()` now masks `aria-valuenow` (a measured width, as `style` px already is), and ask creaite's existing grip has that attribute |

## Tests

`check.py`: OK at every commit.

Passing: test_pages, test_snapshots, test_motion, test_dashboard_split, test_help, test_help_loop, test_ui_sweep, test_prep_page_content, test_wide_tables, test_cell_edit, test_dashboard_editing (theme contrast), test_strip_contrast, test_people_dashboard, test_work_filters_live, test_portfolio_table, test_today_brief and test_no_dead_ends.
