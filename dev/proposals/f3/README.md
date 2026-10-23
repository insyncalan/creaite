# F3 (2.6.4): the people table and the stable person ID

Status: a simulation branch (`v264-f3`). Ships nothing. Guarded changes are diffs only, never applied in this tree. Demo data only.

## Spec found vs assumed

Found (read): #314 (2.6.2 plan, F1 columns and F-slicing), #315 (2.6.3 plan: F2 IDs above 999; one rebuild per release), #317 (2.6.4 plan: F3), #312 (Your profile: ID keyed on email, "This is me" on the laptop only), the design report's "Where Alan has landed" (data and IDs paragraphs). Note: the issue numbers the brief gave (#314, #315, #317) hold the 2.6.2, 2.6.3 and 2.6.4 release plans.

Found in the spec:
- A people table with a stable ID derived from the email (#312's function, Python and JS twins), an importer from `people-register.md`, and the Markdown register kept as a generated copy after each save.
- VIP and Hidden stay private on each laptop, never in the table that travels.
- Additive only: a new table, no rebuild of an existing table. Rollback = restore the dated copy of `tracker.db` and `update.py undo`.
- Guarded files named in #317: `schema.sql`, `tracker.py`, `propose.py`, `review.py`, `build_dashboard.py`, `paths.py`.

Assumed (not in the spec):
- The ID is the first 16 hex characters of SHA-256 of the trimmed, lower-cased primary email (the brief's wording). No code for it existed on `origin/v261-line2` (searched `person_id`, `sha256`), so it is defined here in `person_id.py`.
- The fallback ID for a person without an email (`n` plus 15 hex characters of the normalised name) and its flag.
- Where the private values live (below), and the backup exclusion.
- `review.py` and `paths.py` need no change in this slice (see "What changes in each guarded file").

## Design

New non-guarded files (in this branch):
- `system/scripts/person_id.py`: `person_id(email)`, `fallback_id(name)`, `id_for(name, email)`, `is_fallback`. JS twin: `dev/proposals/f3/person_id.js` (synchronous SHA-256; the test runs both through node and compares).
- `system/scripts/people_table.py`: pure logic, no database. `parse_register` (importer: unknown columns kept in `extra`, Hidden and VIP taken out into private values, flags for no email or a repeated address), `render_register` (the generated Markdown copy), `plan_import` (insert, update, remove, re-key), and the laptop's private file (`load_private`, `save_private`, `merge_private`, `overlay`).
- Tests: `dev/tests/test_people_table.py` (runs on the plain branch) and `dev/tests/test_people_table_db.py` (end to end on a throwaway vault; skips until the diffs are applied).
- Demo data: `dev/proposals/f3/fixture/people-register.md` (six fictional people: two addresses, a mixed-case address with spaces, one with no email, extra columns Slack and Desk, VIP and Hidden set). Expected: 6 people, one flagged (no email), private values for three people.
- `dev/tests/test_tracker.py`: `make_vault` copies the two new modules (propose.py imports them once the diff is applied).

The person: `{id, id_source ("email" or "name"), name, emails[], aliases[], org, role, labels[], extra{}}`. The first address sets the ID; later addresses map to the same person.

IDs:
- Email ID: case and space insensitive; a second address in the cell never changes it.
- No email: `n` plus 15 hex (never equal to an email ID, which is all hex), flagged "no email: its ID comes from the name".
- Two rows with one address: the second gets a name-based ID and a flag; two rows with one name and no address: the second is skipped and flagged.
- Adding an email to a name-based person changes the ID. The plan reports it as "gained an email" and replaces the old row. Nothing refers to person IDs yet, so nothing breaks; once something does (later slices) an `old_ids` alias is needed (open question 2).

Private on each laptop (decision): `system/staging/people-private.json`, `{"version": 1, "people": {<id>: {"hidden": true, "vip": "management"}}}`.
- Not in the shared register file, not in the people table, not in the generated Markdown, never in a change file.
- Excluded from the daily backup zip by one line in `backup.py` (`LEFT_OUT`, next to `vip.json`, so restore also refuses it). It sits in `staging/` beside `vip.json` for the same reason; `system/config/` was rejected because it is in the zip.
- Written in one step (temporary file, then rename). The importer adds values found in an older register to it; what the laptop already has wins.
- BL-288: the generated Markdown's intro says only "personal settings for each person are not kept here"; the word VIP is not written into anything shared. A test checks the generated copy has no VIP or Hidden column and no value.
- Another laptop that imports the generated register gets no VIP or Hidden; each person sets their own.

The generated register (`render_register`): readable table (Full name, Email, Aliases, Organisation, Role, Labels, then any extra columns), a mark line `<!-- people-table: generated ... -->`, everything outside the table kept when regenerating. `import(generate(table)) == table` is tested, including the text being stable on a second generation. A `|` in a cell becomes `/` (as today).

## What changes in each guarded file (diffs here, not applied)

- `schema.diff`: one new table `people` (`CREATE TABLE IF NOT EXISTS`): `person_id` (primary key, 16 characters), `id_source`, `name`, JSON text columns `emails`, `aliases`, `labels`, `extra`, `org`, `role`, `position`, `updated_at`. No VIP or Hidden column. Existing tables untouched; `tracker.py migrate` already runs the schema to add new tables, so no rebuild.
- `tracker.diff`: `people_rows`, `people_write` (one transaction, all or nothing) and two commands. `people-import [--file F] [--dry-run]` prints the counts and who needs a look, takes a database copy first (tagged `migrate`, so the daily Tidy up's 14-day rule covers it), writes the table and merges private values. `people-export [--out F]` prints the Markdown copy (or saves it directly in `system/staging/drafts/`). The register file itself is never written by tracker.py: the file change goes through `filechange.py` (`edit --from` the draft), as for Word files.
- `propose.diff`: `people_parse` adds `id`, `id_source`, and overlays this laptop's `hidden` and `vip`, so every reader (`drafts.py`, `sweep.py`, `report.py`, `build_dashboard.py` through `people_view` and `vip_people`) keeps working unchanged; `person_vip` reads the private value first (the old extra VIP column still works); `people_text` leaves out Hidden and VIP columns when the register is a generated copy (so the old register keeps behaving exactly as today until it is migrated). The module is imported as `ptable` because propose.py already has a function called `people_table`.
- `backup.diff`: one entry in `LEFT_OUT`.
- `recode.diff` (found by the chain simulation, confirmed against these final diffs): adds `people` to `RECODE_OTHER` in `tracker.py`. Without it `propose.py recode` refuses ("doesn't know how to recode people") because `people.person_id` looks like an ID column. `test_a_recode_works_with_the_people_table_and_leaves_it_alone` fails without it and passes with it. Apply after `tracker.diff`.
- `build_dashboard.py`: no diff needed. It reads people only through `propose.people_view` and `propose.vip_people`, which now carry the overlay. The dashboard's own JavaScript people page (not a Python file) still writes the Hidden column; see open question 3.
- `review.py`, `paths.py`: no change in this slice. `paths.py` could name the private file; `people_table.PRIVATE_FILE` is the single place for now.
- `reach.py`: not changed; needs a decision whether ask creaite may read `people-private.json` (open question 4).

Doctor note: `doctor.py` requires every script to import `paths`; `person_id.py` imports it without using it (comment says why).

## Migration from the old register

1. Dated manual copy of `system/tracker.db` (Alan's acceptance, as for F2).
2. Apply the diffs; `tracker.py migrate` adds the empty `people` table.
3. `tracker.py people-import --dry-run`, read the "needs a look" list (people with no email), then `tracker.py people-import`. The register file is not touched at this point; VIP and Hidden are copied to this laptop's private file.
4. `people-export` to a draft, review, then one `filechange.py` edit replaces the register with the generated copy (Hidden and VIP columns go; from then on they are private). Other laptops do steps 2 to 3 only after their own private values are set.

## Rollback

Before step 4: nothing outside the new table changed; drop it by restoring the copy from step 1, and the old register is as it was. After step 4: restore the register through `filechange.py undo` (file backups are kept 90 days), restore the database copy and run `update.py undo`. The private file can stay (an old engine ignores it) or be deleted. The change is additive, so an old engine opens the new database (it ignores the extra table).

## Interplay with F1 and F2

- F1 (nullable author, origin, sequence, base_version, engine version on `applies` and `change_log`): the table is not yet written through apply, so it adds no `change_log` rows; an import is one transaction plus a database copy. When people edits move to apply (later slice), a change carries `author` as the person ID and a people row gets the `base_version` column; nothing here blocks that.
- F2 (IDs above 999, table rebuilds): independent. F3 adds a table and rebuilds none, so the two migrations do not interact; `people` has no CHECK on digit counts. If F2 lands first, F3's apply order is unchanged. `migrate_schema()` takes the rebuild path only if an existing table's definition changed; `people` is created in the "adds any new tables" step in both branches.
- #312 (Your profile): "This is me" is also per laptop. It can live in the same private file (a `me` person ID) in a later slice; the ID function is the one #312 needs, so its profile code should import `person_id.py` rather than define a second one.

## Tests

- `python3 dev/tests/test_people_table.py` (25 tests: stable ID incl. JS twin via node, importer, generator and round trip, plan, private file, 1,000-person timing under 2 seconds; about 0.05 seconds measured).
- `python3 dev/tests/test_people_table_db.py` (8 tests, end to end; skips on the plain branch): import, no VIP or Hidden in the table or the generated copy, second import changes nothing, export then import round trip, dry run, re-key on a new email, propose reads the private values back, the generated register's `people_text` leaves them out, `migrate` adds the table to an older database, 1,000 people import and re-import.
- Run with the diffs applied on a throwaway worktree: `test_people`, `test_tracker`, `test_backups`, `test_vip_private`, `test_vip_matching` pass.

## Questions and decisions

**Decided by Alan, 23-10-2026 ("AM: adopt"): all eight recommendations below are adopted.** F3 is built on these answers when F2 has shipped (2.6.4). Nothing below changes without Alan.

## Open questions, with a recommendation for each (answer "AM:" in one pass)

(The questions are kept as asked; the Recommendation column is the decided answer.)

| # | Question | Recommendation | Why | Cost |
|---|---|---|---|---|
| 1 | Keep or remove a person dropped from the register? | Keep them, marked inactive (a nullable `inactive` flag), not deleted. | Old items still name them; deleting loses who an owner was. | One nullable column on `people` (additive, same release) and one line in the importer; small. |
| 2 | An `old_ids` alias list when a person's ID changes. | Add it before anything refers to a person ID (the first slice that does), not in 2.6.4. | Nothing refers to person IDs yet, so a change breaks nothing today. | A JSON column plus a lookup helper; small, but it must land before F4 and later. |
| 3 | The dashboard People page still writes Hidden into the register text. | Do not run migration step 4 until a `live_server.py` route writes the private file; ship that route in 2.6.4 or hold step 4 to 2.6.5. | Until then the old register and the overlay keep working unchanged, so holding costs nothing. | One guarded route plus page change; medium, one more diff for review. |
| 4 | May ask creaite read `people-private.json`? | No: add it to the never-read list next to `vip.json`. | BL-288: VIP is private to Alan; same reason, same answer. | One line in `reach.py` (guarded); tiny. |
| 5 | Undo of a people import: database copy plus file undo, or move the import into apply? | Keep copy plus file undo for 2.6.4. | Import is a one-off migration; apply needs a `change_log` delete op and a `review.py` change. | None now; moving it into apply is the next slice (medium). |
| 6 | Who writes the table and regenerates the register after each edit? | Apply writes it, then regenerates the register file through `filechange.py`; the People page and cx-edit stage a proposal. | Keeps "one writer" true and every change undoable. | The next slice: `tracker.py`, `review.py`, `propose.py` (guarded); medium to large. |
| 7 | A person with several emails: only the first sets the ID. | Add a "primary" marker only if reordering becomes real; for now the first address is fixed once imported and a reorder is reported as a re-key. | The ID is the shared key, so it should not move by accident; the plan already reports a change. | Small now (a report line); a marker column later if needed. |
| 8 | A name-based ID changes when the name is corrected. | Same as 2: report it, keep the `old_ids` alias, and ask for an email on every flagged person at import. | The remedy is the same; an email makes the ID stable. | None extra beyond 2. |
