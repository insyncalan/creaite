# v1.9.5: BL-325, one design scale

14-10-2026 · branch `v195-design-scale` (origin/v195-ui-fixes + `dev-week-ahead-urgent`, then 54a099b merged) · Team 2 · after BL-324 (`dev/V195-UI-FIXES-NOTE.md`)

Alan's three choices (14-10-2026) are kept: one heading pattern in sentence case; primary actions keep their treatment and only take the shared size and radius; snapshots re-recorded in one pass, with a before-and-after view per screen. Out of scope, as decided: the Word templates, the email drafts and the Impeccable taste rules.

## The before-and-after view

`dev/reviews/bl325-before-after/index.html`, kept in the private creaite-history repository only (its screenshots left the public repository, as the hand-check screenshots did). Each of the 12 screens (Today, Intake, Projects, the project page, Work, Milestones, Review, People, Files, Activity, Settings, Help) in creaite and Brightwater, light and dark, at 1400 by 1000: 48 pairs, before on the left, after on the right, the PNGs as rendered in `before/` and `after/` (9.2 MB). Before is `origin/v195-ui-fixes` at the start of this item (BL-324's ten fixes, without 54a099b's Files search change); after is this branch. Both were rendered by `dev/tools/ui_audit.py` in a throwaway vault with the tests' fictional portfolio. Development only: nothing ships it.

## Proof: `dev/tools/token_audit.py` before and after

Totals for every surface (dashboard, guides, prep page, offline page, the dev reference, Word, email):

| Check | Before (P1/P2/P3) | After (P1/P2/P3) |
|---|---|---|
| 1 Unused tokens | 0/2/0 | 0/2/0 (both in `dev/reference`, not shipped) |
| 2 Undefined tokens | 0/0/0 | 0/0/0 |
| 3 Theme completeness | 0/0/0 | 0/0/0 |
| 4 Hard-coded colours | 10/3/61 | 1/3/39 (the 1 is `dev/reference`) |
| 5 Scale drift | 0/6/58 | 0/1/17 |
| 6 Near-duplicate tokens | 0/11/13 | 0/11/10 |
| 7 Contrast | 5/0/0 | 5/0/0 (all `dev/reference`) |
| 8 Cross-surface | 0/4/17 | 0/2/14 |
| **All** | **15/26/149 (190)** | **6/19/80 (105)** |

The dashboard's scales (style.css and the shell's inline styles):

| Scale | Before: raw uses, distinct raw, token uses | After |
|---|---|---|
| font-size | 457, 46, 1 | 5, 1 (`.85em`, a listed exception), 447 |
| border-radius | 341, 19, 8 | 30, 1 (`50%`, a circle), 319 |
| box-shadow | 25, 20, 38 | 3, 3 (ask creaite's raised button, listed), 63 |
| z-index | 43, 19, 0 | 0, 0, 47 |
| spacing | 1598, 58 distinct, many off a scale | 1599, 41 distinct, every one on the 4px scale or a listed exception |
| line-height | 102, 21 | 95, 14 (near-duplicates folded; not part of BL-325's done-when) |

Check 5 now knows the scale: on a surface that defines the scale tokens it reports any font size, radius, shadow or z-index written raw, and any spacing off the 4px scale, bar the exceptions `on_scale()` lists. It finds none. The one P2 left in check 5 is line-height (14 distinct values, no tokens): BL-325 did not ask for a line-height scale.

## Tokens added

In one marked block near the top of `style.css` (`===== BL-325 scale`), shared by all nine palettes and copied into both guides by `build_guides.py`:

- **Type:** `--fs-2xs` 10, `--fs-xs` 12, `--fs-sm` 13, `--fs-md` 14, `--fs-lg` 16, `--fs-xl` 18, `--fs-2xl` 22, `--fs-display` 34. Folded: 9 → 10; 11, 11.5, 12 and 12.5 → 12; 13.5 → 13; 14.5 → 14; 15, 16 and 17 → 16; 20 → 18. Help's 30 rem sizes map to the same tokens (rem × 16, nearest step); its hero h1 is `--fs-display`.
- **Radius:** `--r-sm` 4, `--r-md` 8, `--r-lg` 12, `--r-xl` 16, `--r-pill` 999. Folded: 1 to 5 → 4; 6 to 10 → 8; 11 to 14 → 12; 17 and 18 → 16; 99 and 9999 → pill. A circle stays `50%`.
- **Shadow:** `--shadow-sm` (hints, tooltips, the "more columns" cue), `--shadow-md` (menus, popovers, calendars, the staged bar), `--shadow-lg` (a dragged ghost), and `--shadow-side` (the peek, the milestone editor, the evidence panel, ask creaite). Still black at low opacity in every theme; a theme's own `--shadow-card` and `--shadow-pop` are unchanged.
- **Z-index:** named layers, lowest first: `--z-under` 0, `--z-raised` 1, `--z-raised-2` 2, `--z-sticky` 3, `--z-sticky-2` 4, `--z-local` 5 (inside one component), `--z-menu` 30 (the two menus at 25 and 30 merged), `--z-panel` 40, `--z-panel-over` 41, `--z-chat` 45, `--z-badge` 46, `--z-stage` 47, `--z-pop` 60, `--z-pop-over` 65, `--z-toast` 70, `--z-drag` 80, `--z-viewer` 90, `--z-tip` 200, `--z-top` 210. The order is as before.
- **Controls:** `--ctl-h` 32, `--ctl-h-sm` 26 (`.mini`), `--ctl-r` (`--r-md`; Brightwater sets `--r-sm`), `--ctl-fs` (`--fs-sm`); `--ctl-h-lg` 40 and `--ctl-r-lg` 10 for Files' centred search only (54a099b: a deliberate large variant beside the 40px ask creaite button, not drift).
- **Spacing:** written in px on a 4px base: 2px steps to 16, 4px steps to 32, 8px steps above. 173 values folded (3 and 5 → 4, 7 → 8, 9 → 8, 11 → 12, 13 → 12, 18 → 16, 22 → 24, 26 → 24, 30 → 32 and so on; a tie goes to the multiple of 4, then of 8). Exceptions: 1px nudges, and em, ch, % or calc() spacing.
- **Colour:** `--brand-ink` (Brightwater's Charcoal on Signal Green; Linear's white on indigo) and `--brand-mark` (Retro Arcade's yellow icon on the blue rail item), each the same in light and dark.

## Merged

- `--day-ink`, `--day-muted` and `--day-rule` equalled `--ink`, `--muted` and `--line` in all 18 theme-modes: they are aliases now, set once on `:root` (90 definitions removed from the palettes and the base).
- The partial matches (`--bg` = `--day-page` in 17 of 18, `--accent` = `--day-sun` in 16, `--accent` = `--focus` in 12 and so on) differ in at least one theme, so they stay. The 11 P2 near-pairs are close, not equal (for example Claude's `--faint` and `--muted`, ΔE 0.8): they are different roles, left for a colour pass.

## Literals replaced

All ten P1 literals that equalled a token are gone from shipped files:

- Brightwater: `#1E1F1E` × 3 (the current rail item, its icon, the pressed view chip) → `var(--brand-ink)`.
- Notion: `.btn.primary` `#FFFFFF` → `var(--accent-ink)` (it was white in light and `--accent-ink` in dark; one rule now, the two dark overrides removed).
- Linear: `.btn.primary` `#FFFFFF` → `var(--brand-ink)`.
- Retro Arcade: `#FFFFFF` × 2 → `var(--btn-ink)`; `#FFFF00` → `var(--brand-mark)`.
- The offline page's `#fff` button text → `var(--accent-ink)`.
- The tenth is in `dev/reference/dashboard-reference.html`, the dev mock-up, not shipped: left.

## Controls (`ui_audit.py`, creaite light, rendered)

| Control | Before | After |
|---|---|---|
| `.ib` | 3 styles (28 and 32px; 6 and 8px corners) | 1 (32px, `--ctl-r`, 13px) |
| `.mini` | 2 styles | 1 (26px, `--ctl-r`) |
| `.dbtn` | 2 styles | 1 (32px square, `--ctl-r`) |
| `.linkbtn` | 4 (12, 13 and 14px; once in the heading face) | 1 (13px, the text face, 24px target) |
| fields and selects | 6 + 3 | 32px, `--ctl-r`, 13px, padding 0 10px everywhere, bar Activity's borderless field inside its box and Files' large search |
| `h1` | 3 (22, 34, 49.6px) | 22px on pages, 34px for Today's and Help's display titles |
| `h2` | 4 (13 caps, 14, 15, 18, and Help's 23.2) | 16px/22px on every page; Help keeps a 22px reading heading on its 16px text, on the same tokens |
| `.tag` | 3 (two faces) | 1 face and size; weight marks a state |

Primary actions keep their treatment (Today's and Intake's filled button, Review's outlined Approve, Work's tinted "+"); they only take the shared size and radius.

## Headings renamed

- **Today:** the six section labels (Getting started, Decisions needed, Needs attention, Your commitments, Resolved, Week ahead, Portfolio) were drawn as 13px bold capitals by CSS; the words were already in sentence case. They are now the shared h2 (BL-79's `#tBrief h2.th` rule is gone).
- **Intake:** "Calendar Import" → "Calendar import", "Upload Files" → "Upload files", "Quick Capture" → "Quick capture"; the icons beside them are gone.
- **Every place changed** (the names as product names, in sentence case throughout):
  - `system/templates/dashboard/shell.html` (the three headings), `src/settings.js` (Advanced: "Calendar import goes back to"), `src/meetings.js` (the notes label and a comment), `src/intake.js`, `src/drafts.js`, `src/core/fields.js`, `src/core/motion.js` (comments), `style.css` (a comment);
  - `system/templates/help.md` (23 uses: Start here's loop, the after-a-meeting steps, Intake's reference, Reference › Settings), so both guides and Help;
  - `system/creaite-rules.md` (2, the staging table), `.claude/skills/cx-sweep/SKILL.md` (1);
  - `system/scripts/build_dashboard.py` (7), `live_server.py` (2), `paths.py` (1), `sweep.py` (1), `transcripts.py` (2): comments and docstrings;
  - `dev/dashboard-spec.md` (11), and the tests that name them: `test_today_brief`, `test_transcripts_ui`, `test_clear_day`, `test_autosize_fields`, `test_plain_dates`, `test_ux_sweep_fixes`.
  - Left as written: history (`dev/BUILD.md`, the release notes, `dev/sprints/`, the reviews, the V18 notes, the mock-ups) and the files this item may not edit (`dev/BACKLOG.md`, `dev/BRD.md`, `dev/sprints/STATUS.md`).
- **Wording:** Projects' "(In 24 days)" → "(in 24 days)" (the portfolio table's next milestone; `today.js`).

## Touch targets

Checkboxes are drawn 16px inside a 24px target (a transparent 4px border, margins that keep the footprint; under forced colours the system's own checkbox); the Settings and milestone switches are 40 by 24 (were 40 by 22 and 36 by 20); the column-resize handle is 24px wide (was 8); `.linkbtn` and People's sort buttons answer 24 high. `ui_audit.py` no longer lists any checkbox, switch or resize handle under 24px; what remains are inline text links (exempt); the portfolio's project-name button now answers 24 high too.

## Surfaces

- **Help:** its rem scale is on the shared tokens; the guides carry the scale block, so they match.
- **Offline page:** creaite's colours light and dark (dark accent #5FC4D6, was #3FB6C8), its fonts (Source Sans 3, Schibsted Grotesk, JetBrains Mono when installed; the page loads nothing), and the type and radius scale; the button is 32px.

## Goldens re-recorded (test_snapshots, one pass)

The goldens hold DOM only, so the scale itself changed none of them; these changed for the wording, the headings and the shell's inline styles:

| Golden | Why |
|---|---|
| intake.html | The three section headings: no icon, and "Calendar import", "Upload files", "Quick capture" |
| help.html | Help's text names the sections in sentence case |
| settings-system.html | Advanced: "Calendar import goes back to" (label and aria-label) |
| projects.html, today.html | The portfolio table's "(in 24 days)", "(in 30 days)" |
| files.html | Files' filter fields' inline styles read `--ctl-h`, `--ctl-r` and `--ctl-fs` (were 32px and 8px literals) |

All other goldens are unchanged. The first two recording runs were cut short by a broken pipe to headless Chrome (other agents were running Chrome); the third ran clean, and `test_snapshots` then passed.

## Tests

`check.py`: OK at every commit.

Passing: test_snapshots, test_motion, test_dashboard_split, test_help, test_help_loop, test_ui_sweep, test_ask_creaite_name, test_dashboard_editing, test_strip_contrast, test_today_brief, test_prep_page_content, test_pages (Files' search bar), test_app_launcher (the offline page), test_transcripts_ui. The full suite: 206 of 210 files passed; the other four are test_snapshots (re-recorded since) and three that fail the same way on `origin/v195-ui-fixes` without this work (checked in a separate worktree), so they are not BL-325's: test_meeting_hub (`test_links_in_from_today_intake_and_an_unknown_address`), test_settings_page (`test_week_ahead_ticks_…`, after BL-319's Urgent-only default) and test_work_item_peek (`test_empty_title_bad_date_and_priority`; today plus three days is a Saturday).

Changed tests: test_dashboard_editing (Today's `--day-ink`, `--day-muted` and `--day-rule` read as the aliases; Apple's pill is `var(--r-pill)`), test_today_brief (Today's headings are exactly the shared h2 in every theme and mode, sentence case, one line; Intake's sections are named in sentence case with no icon), and the name changes in five more.

## Open points for Alan

- **Line height** has no scale yet (14 values; token_audit's one P2 in check 5). A follow-up could pair a line height with each type step.
- **The near-duplicate colours** (11 P2 pairs, ΔE under 2, each in one palette) are different roles that happen to sit close; a colour pass could separate or merge them.
- **Help** keeps a reading scale (22px headings on 16px text) and **Today and Help's hero** keep the 34px display title: both on the shared tokens, both deliberate.
- **Files' search** stays the large search (40px, 10px corners) beside the 40px ask creaite button (54a099b).

