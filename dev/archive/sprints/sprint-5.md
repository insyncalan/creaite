# Sprint 5: All schema changes up front; decisions; the steering one-pager; "ask creaite"

Branch `sprint-5`, worktree `../creaite-sprint5`. **Starts now**, in parallel with `sprint-permissions`, `sprint-sweep-alerts`, `sprint-pages` and `sprint-4a`. **Merges last**, after Sprint 4b. Read BL-53, BL-50, BL-90 (part 2), BL-94, BL-92 and BL-105 in `dev/BACKLOG.md` first. They hold Alan's decisions; where one says "to confirm", take its stated default.

## Alan's decisions (2026-10-09)

- **All planned schema changes up front, in one migration.** This replaces the earlier "one schema change per wave" rule. The features that use the new tables come later; the schema is ready for them.
- **BL-92, the steering one-pager, is in this sprint,** after the sprints it depends on have merged.
- **The assistant is "ask creaite",** in lower case everywhere: the final pass of this sprint.

## Items

Commit each separately, in this order.

### 1. The schema migration (M)

Under the change control in `dev/BUILD.md`: `schema.sql`, `tracker.py` (validation, apply, undo, `migrate`), `excel_sync.py`, the conventions file (`tracker-conventions.md`), `dev/staging-format.md` and `dev/BUILD.md` change **together**. **Show Alan the exact DDL before writing it.**

- **BL-53, `decisions` gains:**
  - `status`: Pending, Made or Withdrawn. Every existing decision becomes Made, keeping its date.
  - `needed_by`.
  - `reasoning`, `options` and `revisit` (a date or a trigger in words).
  - `replaces` (the D-number it replaces).
  - `date` becomes optional, empty while Pending.
  - A pending decision keeps its D-number when it is made.
- **BL-50, a `promises` table:**
  - who to whom (people from the register), what, by when, project and source;
  - status: Open, Done or Dropped;
  - IDs in the house style;
  - no priority or workstream.
- **BL-90 part 2, a `links` table:** from item, to item, kind (`blocks` first). Items may be of any project.
- **BL-94, labels:**
  - `labels`: name, colour, note, behaviour (`warn`, `exclude`), and `builtin`, seeded with **Sensitive**, set to warn with exclude as the default choice;
  - `item_labels`: label and item.
  - **People labels** are a column in `people-register.md`. That's a file, not the schema; add the column and its reader here so it's ready.

**Proposals and Excel:**
- **Proposals:** `tracker.py` accepts proposals for every new field and table, with validation (an unknown label is refused; links point to items that exist), apply and **undo**.
- **Excel:**
  - the round trip carries the new decision fields;
  - a Promises sheet, and a Labels column on actions, RAID and decisions;
  - Links are read-only in Excel at first (state that on the sheet).

**The migration:** keeps every existing row; running it twice changes nothing; an update runs it (`update.py` already calls `migrate`).

**Tests:**
- the migration on a copy of a populated database;
- every new field and table through propose, apply and undo;
- Excel export and import;
- refusals for unknown labels, bad links, and a Made decision without a date.

### 2. BL-53: Fuller decision records, and decisions needed (M)

As BL-53 sets out:
- **Extraction:** cx-minutes and cx-sweep fill the new fields only where the source says so, and propose a pending decision when one is needed.
- **Making or withdrawing one:** "Record the decision" and "Withdraw".
- **Overdue:** a pending decision past `needed_by` is flagged, and appears in early warnings.
- **Where they show:** Today, a Decisions needed card on the project page, a Pending view in Work › Decisions, the person's page, Draft email, the weekly report, and revisit reminders.
- **Shared screens:** the project page belongs to `sprint-pages` and Today's VIP block to `sprint-sweep-alerts`. Put your cards in their own marked sections.
- **The cx-sweep skill** belongs to `sprint-sweep-alerts`. Add a separate subsection for decisions needed, and don't reword its steps.

### 3. Bring `main` in (when ready)

When `sprint-permissions` and `sprint-pages` have merged into `main`, merge `main` into this branch:
- resolve the conflicts;
- run the full suite;
- commit "Merge main into sprint-5".

Until then, keep working on items 1 and 2.

### 4. BL-92: Steering-committee one-pager (M)

As BL-92 sets out:
- **What it is:** a Word one-pager, from `report.py` like `weekly_stage`, with a new `steerco-template.docx` built by `dev/tools/build_templates.py`.
- **Two versions:** internal and client-safe. The client-safe one follows the client-report rules and BL-94's labels.
- **Sections:**
  - **decisions needed** (BL-53);
  - **blockers** (BL-90, using the new `links` table, plus milestone links);
  - **flow** (BL-91);
  - the rest as listed.
- **Filing:** drafted to `system/staging/drafts/`, and on approval filed into the project's **Steerco** folder (BL-85's mapping), never overwriting.
- **Offered from the calendar:** a "Draft the one-pager" link in Prep for steering meetings.
- **The skill:** a new `cx-steerco` skill, or an extension of cx-weekly-report, whichever reads more simply. Say which in BUILD.

### 5. BL-105: "ask creaite" in lower case (S): the final pass

- **Merge `main` in again first,** with Sprint 4b merged, so every screen's newest text is caught.
- **Then write the assistant's name "ask creaite"**, all lower case, everywhere Alan reads it:
  - the dashboard: button, panel heading, notes, menus, messages, tooltips, ⌘K;
  - `help.md`, then regenerate the guides;
  - `system/creaite-rules.md`, the skills and the script messages;
  - the spec.
- **Rules for the pass:**
  - **Sentence starts:** keep it lower case there too.
  - **Unchanged:** code identifiers, and the BRD's history.
  - **Already done:** the teal colour in the creaite teal theme, on `main`. Keep it.
- **Test:** no "Ask creaite" in user-visible text in `dashboard.html`, `help.md` or the guides.

## Boundaries

- **Owns:**
  - `schema.sql` and the schema parts of `tracker.py` and `excel_sync.py`;
  - the conventions file and `dev/staging-format.md`;
  - the people register's Labels column;
  - the decisions UI;
  - `report.py`'s one-pager;
  - the steerco template and the new skill.
- **Don't edit while the others run:**
  - **`sprint-permissions` owns:** `.claude/settings.json`, `permissions.py` and the allow lists.
  - **`sprint-sweep-alerts` owns:** `sweep.py`, the cx-sweep skill's existing steps and meeting prep.
  - **`sprint-pages` owns:** the Files page, the project page's existing cards, `files()`, and flow.
  - **`sprint-4a` owns:** the Work board.
- **Shared files** (`dashboard.html`, `build_dashboard.py`, `report.py`, `help.md`, `dev/dashboard-spec.md`):
  - put new code in its own marked section, `/* ===== Decisions and schema (BL-53, sprint 5) ===== */`;
  - don't reformat unrelated lines;
  - leave `BACKLOG.md` and `BRD.md` alone (updated at merge).
- **Help:** update `help.md`, then run `python3 dev/tools/build_guides.py`.
- **Development guard:** sample data only; test with temporary vaults.

## Done when

- **Tests,** as listed per item.
- **The full suite passes:** `python3 dev/tools/run_tests.py`.
- **Docs:** the spec, and a "Sprint 5" section in `dev/BUILD.md`.
- **Commits:** each item committed separately on `sprint-5`, with the attribution lines from the session's instructions. Never push or merge into `main`.

## Hand-offs

(Changes needed in files another sprint owns.)

- **`sprint-sweep-alerts`:**
  - **Meeting prep (BL-49):** list the project's decisions needed (`D.decisions` with `st === "Pending"`, needed-by in `due`) and the made decisions whose revisit date has come (`revisit`, a YYYY-MM-DD date). BL-53 says both feed meeting prep; I left prep alone as it's yours.
  - **`sweep.py stage`:** it defaults `date` for every new decision (`v.setdefault("date", …)`). I worked around it (the cx-sweep decisions subsection has the spec carry `"date": ""`, which `tracker.py` reads as not set). A one-line fix when convenient: only default `date` when `status` isn't `Pending`. Also useful: `op: update` on a pending decision, as `minutes.py` now supports, so a message that makes a pending decision updates it instead of leaving a note.
- **`sprint-4a`:** the Decisions board (BL-103) can now use `status` (Pending, Made, Withdrawn, as `st`) and the needed-by date (`due`) on decision cards. Work's Decisions columns, filters, views and sort changed in a few existing lines (marked `BL-53`).
- **`sprint-pages`:** the project page's Decisions needed card is added by a wrapper at the top of the right-hand column; "Recent decisions" now leaves pending decisions out (one token on its `dec` line).

## Outcome (closed 09-10-2026)

Merged into `main` as `8b2b34b`. Worktree `../creaite-sprint5` removed and the branch deleted.

- **Built:** all five items, each committed separately, then `main` brought in four times (sprint-pages, 4b, chat-sweep, backup-folder).
  - **1. The schema migration** (FR-101): decisions fields, `promises`, `links`, `labels` and `item_labels`, Excel, the people register's Labels column.
  - **2. Decisions needed** (FR-100, BL-53).
  - **3. `main` brought in** after sprint-pages and sprint-permissions merged.
  - **4. The steering one-pager** (FR-102, BL-92): the `cx-steerco` skill, `steerco-template.docx`, `report.py steerco-data` and `steerco-stage`.
  - **5. "ask creaite" in lower case** (FR-103, BL-105), re-run after chat-sweep merged.
- **Decisions Alan made along the way:**
  - the DDL was approved as shown (`labels.default_choice` added; `item_labels` carries BL-94's extra columns);
  - the filed one-pager is named `YYYY-MM-DD <Project name> Steerco one-pager[ (client)].docx`;
  - merge at the end without a full suite on the final state (the board's rule is one full pass on the final `main`).
- **Verified:** the sprint's own test files passed on the branch and on `main` after the merge; the conflicted files' tests passed at each merge. The full suite did not complete on the final state (three dashboard files that already fail on `main` failed in the partial run; see `STATUS.md`).
- **Not verified:** the one-pager has never been opened in Word, so its fit on one page is unchecked (the lists are capped to keep it to about a page).
- **Left over (the hand-offs above, now one backlog item):** BL-113, meeting prep listing decisions needed and revisits, and `sweep.py` not defaulting a pending decision's date and supporting `op: update` on one. Also still to build: the features on top of the new tables (BL-50 promises, BL-90 part 2's picker, BL-94 warnings).
- **A choice still open:** removed links, labels and item labels are recorded in `change_log` as `(removed)` so undo can restore them; a real `delete` op would be a small schema change.
- **A mistake to learn from:** `pkill` patterns used during the sprint to stop stale test runs matched processes in other sessions' worktrees, and may have disrupted their runs. Stop a test run by its process tree, never by name.
