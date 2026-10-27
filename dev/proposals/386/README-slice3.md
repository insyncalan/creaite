# #386 slice 3 (G-a, G-b): the people table and its one writer

Three guarded patches, NOT applied on any branch. Apply them only after review and Alan's word, as one change (see Apply order).

| Diff | File | sha256 |
|---|---|---|
| `schema-386.diff` (G-a) | `system/scripts/schema.sql` | `60c4c3e9318fb7c8a946d0d47867b640fb373002052afa1d4db1c41cdee75e85` |
| `tracker-386.diff` (G-b) | `system/scripts/tracker.py` | `70fc4eacb895b3558779c2ed9f41fcc7862ca4bc6788498b3b33a9dff57affec` |
| `reach-386.diff` (G-b2, one line) | `system/scripts/reach.py` | `2bdd0a4e387fbe2fda8b1d9239ad4fcd8973f57644b73bca4ec64a97b65b0f9f` |

Base: v2.6.9 release `0b637e926`. Chain: `GUARDED-386-s3.chain` (not pinned; `dev/tests/guarded_chain.py` is unchanged).

## What G-a does (`schema.sql`, one new table)

`people`: `id` (INTEGER PRIMARY KEY AUTOINCREMENT, the person's key), `name` (NOT NULL, UNIQUE, NOCASE; 1 to 200 characters, trimmed,
no `|` or line break), `email`, `aliases` (JSON list), `organisation`, `role`, `is_group`, `hidden`, `labels` (JSON list),
`projects_add`, `projects_remove` (JSON lists of codes: Alan's edits to the projects derived from items), `needs_details`, `created`,
`updated_at`. **No follow column** (Jarvis's ruling: who is followed stays in `system/staging/people-private.json`, BL-288). The
column names are the ones slice 1's `people._table_legacy` reads. Nothing else in the schema changes; `tracker.py init` and
`migrate` add the table (empty) through the existing `executescript`.

## What G-b does (`tracker.py`)

- **The table joins the writer:** `TABLES`, `KEYS` (`id`), `REQUIRED_NEW` (`name`). A new row's key is SQLite's rowid (`AUTO_KEY`);
  every field is logged in `change_log`, so `undo` and Activity work as for any item. People rows can't be cancelled.
- **Ops on table `people`:** `new` (or `add`) with `values`; `update` with `changes`; `rename` (`changes: {"name"}` only); `hide`;
  `merge` (`id` into `into`: name and aliases become aliases, email, organisation and role fill gaps, lists join, the row goes).
  Lists may be sent as JSON lists; they are stored trimmed, each once whatever its case.
- **Validation (held in Review with the reason, never guessed):** the name rules; each email address has the shape `x@y`; list entries
  have no comma, bar or line break; project codes are codes; **no name or alias is anyone else's name or alias** (case-folded), so a
  rename onto another person says "merge". `needs_details` is kept by the writer: 1 while email, organisation or role is missing.
- **Rename and merge carry the name across all seven name columns** (actions.owner, raid.owner, decisions.made_by,
  promises.promised_by and promised_to, milestones.owner, workstreams.lead) in the same apply, any case, each change logged.
- **Auto-add:** once the table holds anyone, a name an apply writes into one of the seven columns that is no one's name or alias
  becomes a person with `needs_details` 1, in the same apply (one Undo takes both). TBC, TBD, unknown, n/a and none are not people.
  **Before the move nothing is added** (the empty table never shadows the register).
- **The export:** after every apply and undo (`after_apply`, first step), once the table holds anyone, the register file is written
  from the table: a "Made by creaite from the tracker" note and one People table in today's format (`Full name, Email, Aliases,
  Organisation, Role, Hidden, Labels, Group, Projects, Left projects`), so the existing readers (propose, the page, client_leak)
  read it unchanged. **No Follow column.** Written through `paths.write_text_atomic`, not `_op_write`, so no stale check can block it.
  Idempotent: unchanged bytes are not rewritten.
- **A hand edit:** the sha256 of the last export is kept in `system/staging/people-export.json` (a hash and dates only). A register
  that differs from it is copied to `system/backups/files/people-register-hand-edit-<time>.md`, recorded there as `hand_edit`
  (for Health, ordinary half), noted on the terminal and the debug log, then replaced.
- **Old-style writes refused:** once the register is made from the table, a proposal's `write` of it is refused before anything is
  written ("change people as people items"), instead of being overwritten after the apply.
- **`tracker.py migrate-people [--dry-run]`:** one apply (via `migrate-people`, so it can be undone): every register row with every
  column (Projects → `projects_add`, Left projects → `projects_remove`), then each name on an item, and Alan (settings identity:
  Alan is in the export), that is no one's name or alias, with `needs_details` 1. The old register is kept as
  `system/backups/people-register.before-386.md` (local only), and the export is written; the apply records it, so **undo puts the
  old register back byte for byte** and empties the table. It **stops, writing nothing**, when a name or alias belongs to two rows,
  or while who is followed is still only in the register (a Follow/VIP value and no `moved` mark in `people-private.json`: run
  slice 2's `people_private.py migrate` first). Run again, it only adds new names from items. `--dry-run` prints counts only.
- **Recode:** a person's `projects_add` and `projects_remove` follow the new code (and back on undo); `people` is in `RECODE_OTHER`.

## What G-b2 does (`reach.py`, one entry)

`SCRIPT_COMMANDS["tracker.py"]["migrate-people"] = (RECORD, "--dry-run")`: it writes the record, so ask creaite runs it only in a
run Alan confirmed (BL-267); `--dry-run` is a read. **A security decision:** it adds one command to the record list Alan named.

## Apply order (hard conditions)

1. **All three diffs together, as one commit.** Any one alone is broken: the schema alone is a table nothing writes (and a recode is
   refused: the table is unclassified); tracker alone writes, and `tracker.py read` reads, a table that isn't there; tracker without
   reach leaves `migrate-people` unclassified (test_record_commands fails; ask creaite refuses it). They touch different files and
   apply cleanly in any order (four orders checked, and reversed cleanly).
2. **Before anyone runs `migrate-people` in a live vault:** slice 2 (the private follow file) and the ordinary half of slice 3
   (`propose.py people …` and the page's `regSave` staging people items instead of a register write; `people.py` reading the table).
   Until then the old write paths are refused with a message once the table is in use. With the table empty (every vault until
   `migrate-people`), behaviour is unchanged.
3. **`people.has_table()` (slice 1) must mean "has rows":** `init`/`migrate` create the table empty; read as it is today, slice 1's
   reader would switch to an empty table. One-line ordinary fix in `people.py` (`SELECT 1 FROM people LIMIT 1`), with slice 3's
   ordinary half.

## How verified

Throwaway worktrees off `0b637e926` (never the branch):

- `git apply` of each diff alone and of all three in four orders, then `git apply -R`: clean.
- `dev/tests/test_people_table_386.py` (ordinary, 20 tests):
  - all three applied: OK;
  - schema only: FAILED (16 failures, 1 error); also test_writer_pinned's recode case fails;
  - tracker and reach only: FAILED (15 failures, 3 errors); also test_tracker's `read` fails;
  - none (the branch): FAILED (16 failures, 3 errors).
  No test skips: half-applied fails.
- Mutants, 14 run, 14 killed: no rename carry; auto-add before the move; no export after apply; merge without carry; follow guard
  off; ambiguity check off; old-style register write allowed; alias clash allowed; hand edit not kept; migration undo leaving the
  new register; needs_details never cleared; TBC as a person; recode leaving people; only six name columns.
- With all three applied: the quick tier, 298 files passed, 0 failed (`run_tests.py --quick -j 4`); after the last wording edits the
  15 closest files again (tracker, writer_pinned, archive_projects, record_commands, spec_fields, plain_words, recode, people,
  activity_undo, item_history, new_vault, schema_sprint5, guard_pinned, guarded_chain, the new file): OK. Python 3.9 not on this box.
- `dev/tools/check.py --no-js`: OK with both applied and on the branch; `dev/check-baseline.json` untouched (no new entry needed).
- Four ordinary test tweaks, green with and without the diffs: `test_writer_pinned.py` leaves an empty `people` table out of its
  snapshot (the pins predate it); `test_archive_projects.py` lists `people` with the other newer tables; `test_spec_fields.py`
  leaves `people` out of propose's field tables (the ordinary half); `test_record_commands.py` adds `tracker.py migrate-people` to
  the record list only when reach classifies it (the `restore-discarded` pattern).

## Not in this slice (open)

- The ordinary half: `propose.py people …`, the page's `regSave`, `people.py` on the table, Health showing `hand_edit`, `doctor.py`'s
  table list, Activity's wording for people rows (keys are row ids).
- Project stakeholders (the project register) are not backfilled as people; the page still adds them as before.
- "A group can't own as a person" is not enforced: `is_group` is stored only.
- A recode does not rewrite the code inside old `change_log` values of people's project lists.
- G-c, G-d, G-e (client_leak, live_server, update) are slice 4.
