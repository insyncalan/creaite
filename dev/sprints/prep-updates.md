# Sprint: Prep updates (BL-65)

Branch `sprint-prep-updates`, worktree `../creaite-prep-updates`. Runs in parallel with `sprint-meetings` (BL-42 phase 2) and `sprint-person-rows` (BL-68). Read BL-65 in `dev/BACKLOG.md` first; it holds Alan's decisions.

**Merge order:** this sprint merges first, then `sprint-meetings`, then `sprint-person-rows`.

## Goal

When cx-minutes processes a meeting, the matched project's open items are expected. For those the transcript discusses, it proposes updates: status, a new due date, a response, a latest update. It never proposes them again as new items.

## Decisions already made

- **Every meeting matched to a project** (Alan, 2026-10-07), whether or not Alan opened its prep brief.
- **Items not discussed** are left alone.
- **A repeat** of an open item is still logged as a mention (BL-51's "raised repeatedly" signal).

## Items

Commit each separately.

### 1. `minutes.py stage` stages updates

- **The spec format.** A minutes spec may now hold update items:
  - `{"op": "update", "table": "actions"|"raid", "id": "ABC-A-003", "set": {field: value}, "why": "…", "source": "<file> — <section>"}`.
  - `minutes.py` fills `based_on` from the row's `updated_at`, so the apply holds a conflict if the item changed after the proposal was made.
- **Fields it may change:**
  - actions: `status`, `due_date`, `latest_update`;
  - RAID: `status`, `response_action`, `due_date`.
  - It never changes owner, title or project; those stay with cx-edit and Review.
- **What it rejects:** an update to an item that is closed, belongs to another project or doesn't exist. The message names the item.
- **Dedupe:** a proposed new item that matches an open item of the same project (`open_duplicates`) becomes an update to it, or a mention only if nothing changed. It never becomes a second item.
- **Format docs:** `dev/staging-format.md`, which describes the proposal format.

### 2. cx-minutes reads the expected items

- **Project and series:** after matching the project, cx-minutes gets the meeting's series from the same logic as meeting prep (`build_dashboard.series_of` and `prep_match`, with `settings.json` `prep.series`).
- **Open items:** it reads the project's open actions, and its risks and issues with no response.
- **How:** add a read-only helper, `minutes.py expected <CODE> [--title "<meeting title>"]`, which prints them as JSON. The skill calls it and doesn't query the database itself.
- **The skill text** (`SKILL.md` and `references/tracker-conventions.md`): compare the transcript with the expected items; propose updates only for those discussed, citing the transcript; never re-propose them as new.
- **Quick notes too:** a quick note (BL-54) gets the same treatment.

### 3. Review shows the updates under their minutes

- **Grouping:** in `review.py` (`build_rows` nesting, BL-41) and the dashboard's Review, update items appear under the meeting's minutes beside its new items.
- **Display:** each shows before → after for the changed fields. They're labelled "Update", and are never covered by "Approve routine" if they change status to Closed.

## Boundaries

- **Owns:**
  - `minutes.py`: stage, the new `expected` command, dedupe;
  - the cx-minutes skill and its references;
  - `review.py`;
  - in `dashboard.html`, Review's rendering of update items;
  - `dev/staging-format.md`.
- **Don't edit:**
  - **`sprint-meetings` owns:** `sweep.py` and the cx-sweep skill; the Inbox view in `dashboard.html`; the Inbox routes in `live_server.py`; `minutes.py meeting_key` and `processed_on`. It needs only processing by event ID, which already works.
  - **`sprint-person-rows` owns:** Work's row code (`rows()`, `cell()`, `orderedCols()`) and the person page.

  Note anything needed there under "Hand-offs".
- **Shared files** (`dashboard.html`, `help.md`, `dev/dashboard-spec.md`, the cx-minutes skill):
  - put new code in its own marked section, `/* ===== Prep updates (BL-65) ===== */`;
  - in the skill, add a new subsection rather than rewording existing steps;
  - don't reorder lines;
  - leave `BACKLOG.md` and `BRD.md` alone: they are updated at merge.
- **Development guard:** sample data only; test with temporary vaults.

## Done when

**Tests (new `dev/tests/test_prep_updates.py`):**
- staging an update fills `based_on`;
- a change after staging is held as a conflict at apply;
- the field limits;
- closed, wrong-project and missing items are rejected;
- dedupe turns a duplicate new item into an update or a mention;
- `expected` lists the right items for a project and series;
- Review nests updates under their minutes and shows before → after;
- "Approve routine" skips closing updates.

The full suite passes: `python3 dev/tools/run_tests.py`.

**Docs:** Help and `dev/dashboard-spec.md` updated, and a short "Prep updates" section added to `dev/BUILD.md`.

**Commits:** each item committed separately on `sprint-prep-updates`, with the attribution lines from the session's instructions. Never push or merge.

## Hand-offs

(Changes needed in files another sprint owns.)

- **None needed from `sprint-meetings` or `sprint-person-rows`.** `minutes.py` changes sit in `cmd_stage`'s item loop, new functions beside `note_mention` and before `main`, and one `expected` branch in `main`; `meeting_key` and `processed_on` are untouched. Nothing here touches Work's rows, `cell()` or `renderPerson`.
- **`build_dashboard.py` (a small edit outside the brief's list):** `review_queue` now gives an update item's title (`review.update_parts`), `why` and `src` (the item's own `source`) to the dashboard. If another sprint changes that function, keep those three lines.
- **`cx-review` skill:** not edited (it isn't in this sprint's list). Its layout text could mention that an update from a meeting is labelled "Update" and is individual-only when it closes an item ("closing update").
- **Merge note:** `sprint-meetings` also edits `minutes.py` (`meeting_key`, `processed_on` and, if it adds processing by event ID, `main`). The `expected` branch and the `Expected items` section are separate hunks.
