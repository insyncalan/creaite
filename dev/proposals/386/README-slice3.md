# #386 slice 3 (G-a, G-b): the people table and its one writer

Three guarded patches, NOT applied on any branch. Apply them only after review and Alan's word, as one change (see Apply order).

| Diff | File | sha256 (rev 2) |
|---|---|---|
| `schema-386.diff` (G-a) | `system/scripts/schema.sql` | `2a3aa690308cd5e7ca09c957c04934cd79eb69fc1b7855717046fb799e778739` |
| `tracker-386.diff` (G-b) | `system/scripts/tracker.py` | `575022c3a85a9124838c2c2ec58a2b393c8cc9bbac27a1ed67769dd2d754b28f` (rev 2c) |
| `reach-386.diff` (G-b2, one line) | `system/scripts/reach.py` | `2bdd0a4e387fbe2fda8b1d9239ad4fcd8973f57644b73bca4ec64a97b65b0f9f` (unchanged) |

Base: v2.6.9 release `0b637e926`. Chain: `GUARDED-386-s3.chain` (not pinned; `dev/tests/guarded_chain.py` is unchanged).

## Rev 2c (27-10-2026): no people op before the move (Banner's re-check, HIGH)

`tracker-386.diff` only: `7a295be7a5fb53e046cc96eb834f2462f92dcd39e3c04d07f340128008eb8c45` (rev 2b) → `575022c3a85a9124838c2c2ec58a2b393c8cc9bbac27a1ed67769dd2d754b28f` (rev 2c); schema and reach unchanged.

- **The finding:** one people `new` op (any people op) applied while the table was empty filled it with one row, and the export
  after that apply replaced the register (Follow, Hidden and everything the move refuses to drop) with that one row, beyond Undo
  or the move. Under the hard condition (the ordinary half stages people items) that would be the first People-page save.
- **The fix:** while the people table is empty, every people op (`new`, `add`, `update`, `rename`, `merge`, `cancel`, and any other)
  is held in Review, nothing written: "people aren't kept in your project record yet: run the move first (Settings › Health,
  "Move people into the tracker", or tracker.py migrate-people --dry-run to see what moves). Nothing was written." Only the move's
  own writes (via `migrate-people`) fill an empty table (`people_op`, called from `write_item`).
- **Auto-add is covered already:** a name on an item adds a person only once the table holds anyone (`add_named_people` checks
  `people_live`); `test_an_unknown_owner_adds_no_one_before_the_move` pins it, the register's bytes unchanged.
- **Failing tests first** (commit `1564d224e`, 2 failures against rev 2b): `EmptyTable.test_no_people_op_before_the_move` (Banner's
  case: REG with Follow and Hidden, seven people ops, every one held, the table empty, the project files byte for byte, and the
  move still refusing) and `..._without_a_register`. Writer's tests now run after a move. 46 tests.
- **Mutants for the guard, 3 run, 3 killed:** the guard off; "no table" instead of "an empty table"; the move's own writes refused too.
- **The ordinary half** must stage people items only after the move, or show the refusal (it is held, never lost).

## Rev 2b (27-10-2026): the label and project refusals say which, whose and how

`tracker-386.diff` only: `0ab907f63e9f6f80634f585d22c5ed7ad6dabe1e90a1a707c46b3004717a62b9` (rev 2) → `7a295be7a5fb53e046cc96eb834f2462f92dcd39e3c04d07f340128008eb8c45` (rev 2b); schema and reach unchanged.

- An unknown project code on a person: "projects_add: ZZZ isn't one of your projects: add the project first, or leave ZZZ out"
  (an unknown label already said which and how: "unknown label 'Nonesuch' (labels: …); add it in Settings or ask creaite first").
- In the move, every person the writer refuses is named, with how to fix it: "Kim Code: projects_add: ZZZ isn't … . Change Kim
  Code's row in the people register, or add what is missing first, then run the move again." Nothing is written.
- Failing tests first (commit `e3c61794a`, 2 failures against rev 2): `test_an_unknown_label_or_project_says_which_whose_and_how`
  (the move) and `test_an_unknown_label_or_project_says_how_to_fix_it` (an explicit new person). 42 tests now.

## Rev 2 (27-10-2026), after Banner's independent review

| Diff | rev 1 sha256 | rev 2 sha256 |
|---|---|---|
| `schema-386.diff` | `60c4c3e9318fb7c8a946d0d47867b640fb373002052afa1d4db1c41cdee75e85` | `2a3aa690308cd5e7ca09c957c04934cd79eb69fc1b7855717046fb799e778739` |
| `tracker-386.diff` | `70fc4eacb895b3558779c2ed9f41fcc7862ca4bc6788498b3b33a9dff57affec` | `0ab907f63e9f6f80634f585d22c5ed7ad6dabe1e90a1a707c46b3004717a62b9` |
| `reach-386.diff` | `2bdd0a4e387fbe2fda8b1d9239ad4fcd8973f57644b73bca4ec64a97b65b0f9f` | the same (Jarvis: kept exactly as is) |

What changed, finding by finding:

- **HIGH 1, hidden out of the record (Jarvis's ruling: follow and hidden live only in slice 2's private file).** No `hidden` column
  in the schema; no `hide` op (it is held: "op must be …"); `hidden` is not a person field (a proposal carrying it is held); the
  move never reads or copies the register's Hidden column; the export has no Hidden column. So hidden is not in tracker.db, its
  change_log, any db backup or zip, or the OneDrive register.
- **The old register's Hidden (and Follow) column: refused, not carried.** Slice 2's interface (`team-cap-386-s2` 19b51625,
  `people_private.py`) gives no caller a way to write the private file: only its own move (`migrate()`) and the live server's
  route (`set_flag`) change it, and Cap's revision makes the move explicit only (the page's first Follow, Hide or Restore, or
  Health). So the people move **refuses**, writing nothing, while the register has a Follow, VIP or Hidden value and slice 2's move
  hasn't run (`people_private.moved()`: its file's `moved`, or its tombstone `people-private.json.moved`), with: "who you follow
  or hide is still only in the register. Move it to its private file first (Settings › Health), so it isn't lost." Once slice 2
  has moved, those columns' values are slice 2's (an old copy restored later is ignored, as slice 2 does) and are dropped from the
  export. Empty Follow, VIP and Hidden columns never stop the move.
- **MEDIUM 2, a lossless move.** The move carries exactly the export's columns (`Full name, Email, Aliases, Organisation, Role,
  Labels, Group, Projects, Left projects`; **Group is now carried** as `is_group` and exported). It **refuses**, writing nothing (not
  even the db backup), when the register holds anything else: another column with values (an empty one carries nothing and is
  dropped), a row with no full name, a row longer than the header, a Group value that isn't yes or blank, a People table with no
  Full name column (`| Name |`), two columns with one name or no line under the header, or any text outside the People table but
  the template's own guidance lines (another section such as `## Groups`, another table, a free note). Those guidance lines (the
  "Keep this file at …" line, `Notes:` and its `- **Column:**` bullets, from any template version) are replaced by the export's
  own note. A row with anything in it and no name is refused, so a register with rows never moves as no one. A label or project code the record doesn't know stops it too
  (LOW below), naming the person.
- **MEDIUM 3, a pending old-style register write.** While any staged proposal (pending or approved, not applied or rejected) still
  writes the register (`regSave`, `propose.py people`), the move and its dry run refuse: "a change to the people register is still
  waiting in Review (<proposal file>). Apply or reject it first." So the move never makes such a write block every later apply.
- **MEDIUM 4, gating.** `dev/tests/test_people_table_386.py` skips with no diff applied
  (`OK (skipped=44)` since rev 2c), fails for every partial combination (`AllOrNone`, plus the tests themselves), and passes with all three. Markers: schema.sql's `-- People (#386)`,
  tracker.py's slice 3 banner, reach.py's migrate-people comment (so reach-386.diff needs no change).
- **LOWs, all fixed:**
  - names compare by `fold()` (NFC, spaces collapsed, `casefold`), in Python, everywhere: rename and merge carry across the seven
    columns ("ÉLODIE DURAND", "élodie durand" and a decomposed form are one name), the clash check, auto-add, the ambiguity check
    and the names from items. NFC and NFD twins are one person (two register rows: ambiguous, refused);
  - a move run again after an Undo records no hand edit (the move keeps the old register itself and its own export is never one);
  - a dry run (or a move) under a held write lock says "The record is busy … try again in a minute", exit 1, no traceback;
  - organisation and role refuse a bar and any line break (control, line or paragraph separator; names too);
  - an explicit `people new` is as strict as auto-add: TBC, TBD, unknown, n/a and none are not names or aliases, and labels and
    project codes being written must exist in the record;
  - the move writes the register's record (the copy kept, the export's hash) on its apply **before** the COMMIT, so a failed first
    export never leaves `file_ops` `[]`: the next save writes the register, and Undo still puts the old one back;
  - a write to the register in another case or Unicode form (`People-Register.md`) goes through the same refusal (`_folded`);
  - the test count and these limits are below.
- **Survivor mutants, each now killed by a test:** a dry run that takes a backup (`test_dry_run_writes_no_file_and_takes_no_backup`,
  every file compared but the debug log); merge dropping the labels or projects join (`test_merge_joins_labels_and_projects`); a
  migration that COMMITs on failure (`test_a_failure_mid_way_writes_nothing`); the export dropping Group
  (`test_the_export_reads_back_the_same`, `test_every_column_kept_then_undone`).
- **Failing tests first:** commit `2a35c6e4f` adds the tests with the rev 1 diffs unchanged. Against rev 1 (all three applied):
  29 failures in 20 tests (the HIGH, each MEDIUM, every LOW); with none applied: skipped. Rev 2 makes them pass.

## What G-a does (`schema.sql`, one new table)

`people`: `id` (INTEGER PRIMARY KEY AUTOINCREMENT, the person's key), `name` (NOT NULL, UNIQUE, NOCASE; 1 to 200 characters, trimmed,
no `|` or line break), `email`, `aliases` (JSON list), `organisation`, `role`, `is_group`, `labels` (JSON list), `projects_add`,
`projects_remove` (JSON lists of codes: Alan's edits to the projects derived from items), `needs_details`, `created`, `updated_at`.
**No follow and no hidden column** (BL-288; Jarvis, 27-10-2026: both stay in `system/staging/people-private.json`). Nothing else in
the schema changes; `tracker.py init` and `migrate` add the table (empty) through the existing `executescript`.

## What G-b does (`tracker.py`)

- **The table joins the writer:** `TABLES`, `KEYS` (`id`), `REQUIRED_NEW` (`name`). A new row's key is SQLite's rowid (`AUTO_KEY`);
  every field is logged in `change_log`, so `undo` and Activity work as for any item. People rows can't be cancelled.
- **Ops on table `people`:** `new` (or `add`) with `values`; `update` with `changes`; `rename` (`changes: {"name"}` only); `merge`
  (`id` into `into`: name and aliases become aliases, email, organisation and role fill gaps, lists join, the row goes). No `hide`.
- **Validation (held in Review with the reason, never guessed):** the name rules (no placeholder names); each email address has the
  shape `x@y`; organisation and role fit one cell; list entries have no comma, bar or line break; project codes are codes of your
  projects and labels are your labels; **no name or alias is anyone else's name or alias** (folded), so a rename onto another person
  says "merge". `needs_details` is kept by the writer: 1 while email, organisation or role is missing.
- **Rename and merge carry the name across all seven name columns** (actions.owner, raid.owner, decisions.made_by,
  promises.promised_by and promised_to, milestones.owner, workstreams.lead) in the same apply, in any case or Unicode form.
- **Auto-add:** once the table holds anyone, a name an apply writes into one of the seven columns that is no one's name or alias
  becomes a person with `needs_details` 1, in the same apply. TBC, TBD, unknown, n/a and none are not people. **Before the move
  nothing is added.**
- **The export:** after every apply and undo (`after_apply`, first step), once the table holds anyone, the register is written from
  the table: a "Made by creaite from your project record" note and one People table (`Full name, Email, Aliases, Organisation,
  Role, Labels, Group, Projects, Left projects`). **No Follow and no Hidden column.** Aliases stay third: client_leak reads that
  cell by position (a comment beside `EXPORT_COLUMNS`, and `test_aliases_are_the_third_column_of_the_export`). Written through
  `paths.write_text_atomic`; unchanged bytes are not rewritten.
- **A hand edit:** the sha256 of the last export is kept in `system/staging/people-export.json` (a hash and dates only). A register
  that differs from it is copied to `system/backups/files/people-register-hand-edit-<time>.md`, recorded there as `hand_edit`,
  noted on the terminal and the debug log, then replaced.
- **Old-style writes refused:** once the register is made from the table, a proposal's `write` of it (in any case or Unicode form) is
  refused before anything is written.
- **`tracker.py migrate-people [--dry-run]`:** one apply (via `migrate-people`, undoable): every register row in the export's columns
  (Projects → `projects_add`, Left projects → `projects_remove`, Group → `is_group`), then each name on an item, and Alan (settings
  identity), that is no one's name or alias, with `needs_details` 1. The old register is kept as
  `system/backups/people-register.before-386.md` (local only) and the export is written; **undo puts the old register back byte for
  byte** and empties the table. It **stops, writing nothing**, while a register write waits in Review, while who is followed or
  hidden is still only in the register, on anything it can't carry, on an ambiguity, and on a person the writer refuses (the whole
  move rolls back). Run again, it only adds new names from items. `--dry-run` prints counts only and writes no file.
- **Recode:** a person's `projects_add` and `projects_remove` follow the new code (and back on undo).

## What G-b2 does (`reach.py`, one entry, unchanged)

`SCRIPT_COMMANDS["tracker.py"]["migrate-people"] = (RECORD, "--dry-run")`: it writes the record, so ask creaite runs it only in a
run Alan confirmed (BL-267); `--dry-run` is a read. **A security decision:** it adds one command to the record list Alan named.

## The interface with slice 2 (people_private.py)

The move reads one thing of slice 2's: whether its move has run, through `people_private.moved()` when the module is installed (it
lands first), else the same test read directly (`people-private.json`'s `moved`, or the tombstone `people-private.json.moved`). It
never writes the private file, never strips the register's columns itself, and never imports anything else of slice 2's.

## Apply order (hard conditions)

1. **All three diffs together, as one commit.** Any one alone is broken: the schema alone is a table nothing writes; tracker alone
   writes, and `tracker.py read` reads, a table that isn't there; tracker without reach leaves `migrate-people` unclassified. They
   touch different files and apply cleanly alone and in any order (all six orders checked, and reversed cleanly).
2. **The ordinary half ships with the diffs (hard condition).** The ordinary half of slice 3 (`propose.py people …` and the page's
   `regSave` staging people items instead of writing the register) must land **in the same release as these diffs, and before any
   live `migrate-people`**. The diffs must not ship without it: after the move every old-style register write is refused, and with
   it the whole apply.
3. **Landing order before any live `migrate-people`:** also slice 2 (the private file, with its explicit move) and slice 1 with
   Cap's `has_table()` fix ("the table has rows") and `strict` reads.
4. **The move is explicit only.** `tracker.py migrate` and an update never run it. Alan starts it from a Health row, "Move people
   into the tracker" (ordinary half), after the dry-run count; it takes a database backup first; one save, so Undo reverses it.

## Stated limits

- Project stakeholders (from the project register) are not added as people by the move.
- "A group can't own as a person" is not enforced: `is_group` is stored and exported only.
- Activity shows a person's changes by their row number (the person's id), not their name.
- **What the move refuses rather than carries** (Alan changes the register first): extra columns with values (a Phone column, say),
  other sections, tables and free notes, rows without a name, unknown labels or project codes. The template's guidance lines are
  replaced by the export's own note (they are the template's, not Alan's).
- After the move, an old page that still stages a register write gets that write refused at apply (and with it that apply); the
  ordinary half's `regSave` change closes this, which is why it ships in the same release (Apply order 2).
- Name matching stays `casefold` (`fold`: NFC, spaces collapsed, casefold); Cap adopts it in slice 2's `people_private.key`
  (it used `lower`; they differ only on a few letters such as "ß").
- The Settings › Health wording in the move's refusal ("Move it to its private file first (Settings › Health)") follows Cap's final
  slice 2 tip, where the explicit move lives; it is changed to match that tip's wording if it differs.
- The case-folded register path (`People-Register.md`) is tested as a path only, not on a real case-insensitive disk. Alan can try
  it on the Mac: stage a write to `projects/_portfolio/People-Register.md` after the move and check the apply refuses it.

## Known non-blocking points (Banner's re-check lists; logged, not changed in rev 2c)

- MEDIUM, for slice 1 or slice 2: after the move, `people.py` still reads a `hidden` column that no longer exists.
- A refused write still takes a database backup, although the message says nothing was written.
- A stray `people-register.before-386.md` copy can be left after a forced kill.
- The template's guidance lines are matched by their start, so text Alan adds after one is dropped without a refusal.
- A merge or an update can leave one project code in both `projects_add` and `projects_remove`.
- A follow or hidden refusal is reported first and hides every other reason the move would refuse.
- The held-field message points to `propose.py fields people`, which does not exist yet.

## How verified

Throwaway worktrees off the branch (its guarded files are 0b637e926's), never the branch itself:

- `git apply --check` of each diff alone on `0b637e926`, all three in all six orders, then `git apply -R`: clean.
- `dev/tests/test_people_table_386.py` (46 tests since rev 2c):
  - none applied (the branch): OK, 44 skipped;
  - schema only: FAILED; tracker and reach only: FAILED; every other partial combination: FAILED;
  - all three: OK;
  - against rev 1 with all three applied: 29 failures (the failing-first run).
- Mutants, 27 run on tracker.py, 27 killed: each refusal of the lossless check (9), the private-column check, Group carried and
  exported, the pending write and its case-folded path, the check_write fold, fold without NFC, carry by SQLite NOCASE, the first
  export as a hand edit, the lock message, organisation and role, placeholder names, unknown labels and projects, control
  characters, `file_ops` left `[]`, a dry run taking a backup, merge dropping the lists join, COMMIT on failure, the tombstone.
- With all three applied, 21 related files OK: archive_projects, client_leak, client_leak_gate, client_leak_place,
  guarded_chain, no_real_names, people, people_dashboard, people_display, people_page_v2, people_projects_links_browser (Chrome),
  people_table_386, plain_words, reach, reach_line_entries, record_commands, spec_fields, tracker, tracker_inode_hold,
  tracker_words_292, writer_pinned.
- Slice 4 on top (`v2610-386s4b` with Cap's tests, 395971ca; `client_leak-386s4.diff` a8c5a3fb…): the four diffs apply, and
  client_leak_people_386, client_leak, client_leak_gate, client_leak_place, draft_chase and guarded_chain are OK.
- Python 3.9: not on this box; both changed files parse with the 3.9 grammar (`ast`, `feature_version=(3, 9)`).
- `dev/tools/check.py --no-js`: OK with the three applied and on the branch; `dev/check-baseline.json` untouched.
- Four ordinary test tweaks, green with and without the diffs: `test_writer_pinned.py` leaves an empty `people` table out of its
  snapshot; `test_archive_projects.py` lists `people` with the other newer tables; `test_spec_fields.py` leaves `people` out of
  propose's field tables; `test_record_commands.py` adds `tracker.py migrate-people` to the record list only when reach classifies it.

## Not in this slice (open)

- The ordinary half: `propose.py people …`, the page's `regSave`, `people.py` on the table, Health showing `hand_edit` and the
  move's refusals, `doctor.py`'s table list, the Health row that starts the move, Activity's wording for people rows.
- A recode does not rewrite the code inside old `change_log` values of people's project lists.
- G-c, G-d, G-e (client_leak, live_server, update) are slice 4.
