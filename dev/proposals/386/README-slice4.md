# #386 slice 4 (G-c, G-d, G-e): the small guarded edits

One guarded patch, NOT applied on any branch. G-d and G-e were checked against slice 3 as built and need no diff (below); say so to
Alan with the package rather than sending empty diffs.

| Diff | File | sha256 |
|---|---|---|
| `client_leak-386s4.diff` (G-c) | `system/scripts/client_leak.py` | `3b4417aa18bfd26d4073fca637d55c1a255d26a1e9822fe1d88cab0bf67b22cb` |

Rev 2 (27-10-2026): `register_aliases` split so check.py passes with all four diffs applied (rev 1, `a8c5a3fb…cd9f`, gave
it complexity 16 against the limit of 15). The table read moved into `_table_aliases(con, out)`; behaviour is identical.

Base: v2.6.9 release `0b637e926`. Chain: `GUARDED-386-s4.chain` (not pinned; `dev/tests/guarded_chain.py` is unchanged).

## What G-c does (`client_leak.py`, 19 lines added, 4 changed)

`register_aliases(con=None)`: the register file is read exactly as before (the same tolerant parse; missing, unreadable or no
People table still raises `RegisterUnreadable`), and **then** tracker.db's `people` table on the caller's connection, when the
database has one, adds its names and aliases (in `_table_aliases`, a small helper, so each stays within check.py's limit). `people()` passes its `con`. A people table that can't be read (an SQLite error, or
an aliases value that isn't JSON or can't be listed) raises `RegisterUnreadable`: the names check still fails closed (#127).

Why a union and not "the table instead of the file": slice 3 writes the register from the table after every apply, so the two
agree; but between a hand edit (or ask creaite editing the file, an ordinary change) and the next apply, or after an export that
failed quietly (`export_people_quietly`), the file can hold fewer aliases than the record. Read alone, it would narrow the check.
With the union the check only ever widens. One stated edge: a client-visible owner's alias found only in the table also joins the
"shared" set (#123 review M2), so an internal owner's identical alias is then not flagged; that is the existing ambiguity rule,
reached only while the file and the table disagree.

**Not on `people.py` (a change from Cap's plan, which said "reads people.py"):** slice 1's `people.py` isn't on the 0b637e92
base, and its `has_table()` turns any database error into "no table" and falls back to the file (Banner's slice 1 LOW 3), which is
fail-open here. The diff reads the caller's open connection instead: no second connection, no `file:` URI (the `#`/`?` path
problem), and an error fails closed.

## Ordinary half (on the branch, not guarded)

`drafts.people_names` (the client-wording check) adds the table's names and aliases the same way (`table_people_names`), and stays
tolerant: no database, no table or a broken one adds nothing, as a missing register does. This is the "moves both together" Cap
and Banner agreed for slice 1's M2. The helper sits after `people_names` and the only line inside it is the `names.update(...)`
before the return, so slice 1's docstring edit to `people_names` merges without a conflict.

## G-d (`live_server.py`): no diff needed

- **:222, the read-only file rule** for `projects/_portfolio/people-register.md`: still right. Slice 3 keeps the register as a
  file, written from the table in today's format; the page still reads it and never writes it (it isn't in the `write` list;
  the page's `regSave` stages a proposal, which slice 3's `check_write` refuses once the table is in use).
- **:770, the staleness list:** people changes come through an apply (the record's version changes) and the export rewrites the
  register (listed); `system/staging/people-export.json` is directly in staging and so already stamped (not in `PAGE_IGNORE`).
- **:5848, `field_person`:** resolves through `propose.people_pool`/`resolve_person`, which slice 1 moves onto `people.py`
  (ordinary). Its behaviour moves with slice 1, not here.

## G-e (`update.py` :773): not built, open for Jarvis

Taking the register out of `STARTING_FILES` would make every new vault fail closed in the client names check: `register_aliases`
raises on a missing register, and slice 3's export writes the file only once the table holds anyone (`people_live`), which a new
vault's empty table never does until someone is added. It would need G-c to accept "no file" with an empty table, which can't be
told apart from an older vault whose register went missing (today's fail-closed case). Recommendation: keep the starting file (the
template is an empty People table; the first export replaces it and keeps the template aside as `people-register.before-386.md`).
The template's `Follow` column is slice 2's to drop (ordinary). `locations.py` :142 likewise stays.

## Apply order

1. G-c can land alone and in any order with slice 3's three diffs: it touches only `client_leak.py`, and with no `people` table it
   reads the register exactly as today.
2. It is meant to land with slice 3 (`schema-386.diff`, `tracker-386.diff`, `reach-386.diff`): `test_client_leak_people_386`'s
   `TableFromSchema` fails unless `tracker.py init` makes the table, so slice 4 without slice 3, or slice 3 without slice 4, leaves
   a failure.
3. Independent of Cap's guarded follow-ups on `team-cap-386-g` (`386-backup.diff`, `386-live_server-private.diff`): different
   files; `client_leak.py` and `drafts.py`'s `people_names` are the same on 0b637e92, a62fbb0a's slice 1 and c01eb86b.

## How verified

Throwaway worktrees (never the branch), on slice 3 rev 2b (`schema-386.diff` `2a3aa690…8739`, `tracker-386.diff` `7a295be7…eb45`,
`reach-386.diff` `2bdd0a4e…0f9f`, from `v2610-386s3b` 866901fb1, merged into this branch):

- `git apply --check` of each of the four diffs alone on `0b637e926`: clean. All 24 orders of the four applied, then reversed in
  reverse order: clean, tree back to the base.
- `dev/tools/check.py --no-js` with all four applied: OK (rev 1: "CC register_aliases has 16 complexity; the limit is 15").
- `dev/tests/test_client_leak_people_386.py` (11 tests; no skips):
  - none applied (the branch): FAILED (6 failures);
  - slice 3 only: FAILED (6 failures);
  - G-c only: FAILED (1 failure: `TableFromSchema`);
  - all four: OK.
  - `Complexity` runs check.py's own complexity measure on `register_aliases` and `_table_aliases`: it fails on rev 1 of the diff.
- Mutants on G-c (all four applied), 7 run, 7 killed: `people()` not passing `con`; the helper skipped; a table error swallowed;
  the table never read; its aliases not added; only SQLite errors failing closed; a missing register no longer failing closed.
- With all four applied: test_client_leak, test_client_leak_gate, test_client_leak_place, test_draft_chase, test_guarded_chain,
  test_people_table_386: OK.
