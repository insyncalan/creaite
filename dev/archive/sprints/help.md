# Sprint: Help in three tabs (BL-84)

Branch `sprint-help`, worktree `../creaite-help`. Runs beside `sprint-draft-email` (BL-83), which also edits `help.md`; **this sprint merges after it**. Read BL-84 in `dev/BACKLOG.md` first; it holds Alan's decisions.

## Goal

The dashboard's Help page becomes the guide Alan approved as an artifact, with the same look and feel. It has three tabs, **Start here**, **How do I…** and **Reference**, all from one source, `system/templates/help.md`. The two standalone guides are generated from that same source, so the guides and Help can never drift apart.

## The look and feel is fixed (Alan, 2026-10-08)

**The visual spec:**
- `system/templates/guide-first-day.html` and `system/templates/guide-how-to.html` (this repo's copies of the published artifacts);
- the published pages: https://claude.ai/artifact/EL7f163uxKMmUqgSyaPDMS (first day) and https://claude.ai/artifact/Fie1SURNoZqM9fqioyjrqT (how-to).

Match them. Don't reinterpret them.

**Components, kept as they are:**
- **The loop:** five stages in a row, the "You · Review" stage highlighted as the only gate, arrows between stages, a return line under them, and stacking on narrow widths.
- **Numbered first-hour steps**, the **daily rhythm** strip and the **"where things are"** grid.
- **The phrasebook table**, with phrases as mono chips.
- **The four rules** cards.
- **The how-to's grouped index**, then **task cards**, each with:
  - a mono "where" line;
  - the title;
  - numbered steps;
  - a dashed "Or say" row of chips.

  Linking to a task highlights its card.

**Typography and spacing:**
- the same type scale, weights, letter-spacing on eyebrows and labels, radii, gaps and widths;
- display, body and mono roles: Schibsted Grotesk, Source Sans 3 and JetBrains Mono;
- headings with balanced wrapping.

**Fonts:**
- The dashboard and the guides are offline: no Google Fonts.
- Vendor the three faces as WOFF2 (all SIL Open Font License; keep the licence file) in `system/templates/vendor/`. Embed them the way `build_dashboard.font_faces()` already embeds Roboto, and as data URIs in the generated guides.
- Keep the weights to what the pages use (500, 700, 800; 400 and 600; 500) and Latin subsets, to limit size. Say how much the dashboard grows.

**Colours:**
- In **creaite standard** the pages look exactly as the artifacts do: teal accent, amber for "you", green for the rules, the same neutrals.
- In Minimals and Brightwater, map the same roles to that theme's tokens (accent, warn, ok, surface, line, muted). The pages then fit the theme without changing shape.
- Light and dark mode both work, with contrast checked as for every theme.

**The icon:** the creaite icon heads Start here, as in the artifact.

## Items

Commit each separately.

### 1. One source: `help.md` in three parts

Restructure `system/templates/help.md` into three parts, marked by H1 headings `# Start here`, `# How do I…` and `# Reference`, with `##` sections under each. Write it so a person can still read it as plain Markdown.

**Start here:** the artifact's content as Markdown, with light conventions the renderer turns into the components:
- `## The loop`: a numbered list of five stages, each `**Title** (Stage label): text`, with the "you" stage marked (for example `{you}`);
- `## Your first hour`: numbered steps;
- `## Every day`: when and what pairs;
- `## Where things are`: view and line pairs, with the keys line;
- `## Say this`: a table;
- `## Four rules`: four bold-led items.

Define the conventions once, at the top of `help.md` in a comment, and keep them minimal.

**How do I…:** one `##` per task, in the artifact's five groups (marked by `### Group` lines, or an equally simple marker). Each task has:
- a `Where:` line;
- numbered steps;
- an `Or say:` line of backticked phrases.

Bring the 16 artifact tasks across as written, and update them for anything merged since: **Prep 1:1 is replaced by Draft email** (BL-83), so describe Draft email from its brief, `dev/archive/sprints/draft-email.md`.

**Reference:** everything in today's `help.md`, regrouped:
- keyboard shortcuts;
- lists and filters;
- how saving works;
- each feature's detail (Today, project page, early warnings, meeting prep, updates from meetings, Review, Intake, Files, Activity, People, Workstreams, Search);
- Settings, client messaging, dates, sources, documents and permissions, commands, live server and backups, troubleshooting.

Trim only what a task card already says in the same words. **Nothing may be dropped:** list any removed sentence under "Hand-offs", with where it now lives.

### 2. The renderer and the Help view

- **`build_dashboard.help_sections()`:**
  - learns the three parts, ordered lists, and the Start here and How-do-I conventions;
  - keeps `[start command]` filled in per vault;
  - returns a structure the page renders into the artifact's components.
- **`renderHelp()` in `dashboard.html`:**
  - three tabs: Start here, How do I…, Reference;
  - `?` opens the last tab used;
  - each tab has an address (`#help-start`, `#help-howto`, `#help-reference`, and `#help-howto-<task>` for a card), so Back and Forward work, and the how-to index jumps to a card and highlights it;
  - the Reference tab keeps today's side index.
- **Styles:** in their own marked section, `/* ===== Help (BL-84) ===== */`, written from the guide files' CSS and adapted to the dashboard's tokens as described above.

### 3. ⌘K finds Help

- Every task and reference section is an entry under "Help": "Help: Hand over someone's work", "Help: Early warnings". Choosing one opens its tab at that place.
- Typing "how do I…" or "help" lists the tasks first.

### 4. First visit opens Start here

- A new setting, `help.start_seen`, is false in `system/templates/settings-defaults.json`.
- The first time the dashboard opens in a vault with it false, it shows Help › Start here, then sets it to true (a settings write, logged as usual).
- Vaults that update get the key from the update, so they also see Start here once. Set it to true in this repo's own settings.

### 5. The standalone guides are generated

`dev/tools/build_guides.py` writes `system/templates/guide-first-day.html` (from Start here) and `guide-how-to.html` (from How do I…):
- the same components and CSS as the Help tabs;
- the creaite standard palette, light and dark, with the fonts embedded;
- self-contained, and linking to each other.

**Kept in step:** run it whenever `help.md` changes. A test fails if either file is out of date with `help.md` (rebuild and compare), so they can't drift.

**Release:** the guides ship in the engine, as now.

### 6. Retire the old Help structure

- Remove the old single-page Help layout, and the "Guides" section that points to the files (Help now contains them; say instead "a printable copy of these guides is in `system/templates/`").
- Update `dev/dashboard-spec.md`'s Help section.

## Boundaries

- **Owns:**
  - `help.md`;
  - `help_sections()` and `font_faces()` in `build_dashboard.py`;
  - in `dashboard.html`, the Help view, the Help ⌘K entries and the first-visit rule;
  - `dev/tools/build_guides.py`;
  - the two guide files;
  - the vendored fonts;
  - `settings-defaults.json` (the new key only).
- **Don't edit:** the People page and Draft email (`sprint-draft-email`). Describe Draft email in Help from its brief, and leave its code alone.
- **Shared files:** `dashboard.html`, `build_dashboard.py` and `dev/dashboard-spec.md`. Put new code in marked sections, and don't reformat unrelated lines.
- **At merge:** expect a conflict in `help.md` with `sprint-draft-email`. Take this sprint's structure, and keep Draft email's wording where it's more exact.
- **Development guard:** sample data only.
- **Docs:** leave `BACKLOG.md` and `BRD.md` alone; they are updated at merge.

## Done when

**Tests:**
- `help.md` parses into three parts, and every artifact component appears:
  - the five loop stages, with the gate marked;
  - the four first-hour steps;
  - the rhythm;
  - the views;
  - the phrasebook;
  - the four rules;
  - 16 or more tasks in five groups, each with Where, steps and Or say.
- Reference keeps every heading from today's Help.
- `[start command]` is filled in.
- In headless Chrome:
  - the three tabs and their addresses, plus Back and Forward;
  - an index link highlights its card;
  - ⌘K Help entries open the right place;
  - the first visit opens Start here once, and never again;
  - light and dark in all three themes with no contrast failures.
- The generated guides match `help.md` (rebuild and compare), are self-contained with no network, and link to each other.
- **A screenshot check against the artifact:** Start here and How do I… in creaite standard, light, at 1300px, look like the published artifacts. Put both screenshots in the merge notes for Alan.
- The full suite passes: `python3 dev/tools/run_tests.py`.

**Docs:** Help itself, the spec, and a short "Help in three tabs" section in `dev/BUILD.md`.

**Commits:** each item committed separately on `sprint-help`, with the attribution lines from the session's instructions. Never push or merge.

## Hand-offs

(Sentences moved or removed from today's Help, with where they went; anything another sprint must change.)

**Removed from today's Help** (nothing else was dropped or reworded; every other section is in Reference word for word):
- The **Guides** section ("New to creaite? Two one-page guides sit beside this help in `system/templates/`…", with its two bullets for `guide-first-day.html` and `guide-how-to.html`): Help now contains the guides. Reference's opening paragraph says instead that "a printable copy of those two guides is in `system/templates/`".
- The one-line intro under the title ("The dashboard's Help page (press `?`, or Settings › Help) is built from this file at every rebuild. Edit it here. `Cmd` on Mac, `Ctrl` on Windows."): now the comment at the top of `help.md`.
- In **People**, the **Prep 1:1** bullet ("**Prep 1:1** on a person's page opens a short brief: what they owe…"): replaced by a **Draft email** bullet written from `dev/archive/sprints/draft-email.md`. The Start here "People" view line and the how-to "Prepare for a meeting or 1:1" card changed the same way (Prep 1:1 became "Prepare for a meeting" plus a new "Ask someone for an update" card). Reword these from the built sprint at merge if its wording is more exact.

**Changed in Help on purpose:** the `?` shortcut row says it opens the tab used last.

**Needs doing by someone with the internet (Alan):** run `python3 dev/tools/fetch_help_fonts.py`, then `python3 dev/tools/build_guides.py`, and commit the three font families (WOFF2 files and `help-fonts-OFL.txt`) and the rebuilt guides. This session had no network, so the fonts are not vendored yet: Help and the guides use the system's sans and mono fonts until then, and the screenshots in `dev/archive/sprints/help-merge/` show that fallback.
