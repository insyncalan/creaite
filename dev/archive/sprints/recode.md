# Sprint: Recode a project (BL-111)

Branch `sprint-recode`, worktree `../creaite-recode`, made from the tip of `main` (`eaa2a8e`) on 09-10-2026. Read BL-111 in `dev/BACKLOG.md` first; it holds Alan's decisions. This brief settles the points BL-111 left open.

## Goal

Change a project's code (and optionally its name and folder) in one reviewed, undoable step, so that ORX "Kestrel Northgate" becomes FAL "Kestrel Energy AI" with every item, its history and its links following. Nothing is written until "apply"; "undo last apply" restores the exact previous state.

## Sequencing (read before merging)

BL-111 says "after Sprint 5 merges", because Sprint 5 adds tables that carry a `project` column or item IDs (`promises`, `links`, `item_labels`) and changes `tracker.py`. Alan asked for the sprint to be built now, so:

- **All new code is in one marked block** at the end of `tracker.py` (`# ===== Recode a project (BL-111) =====`) and one in `propose.py`; the hooks in existing code are single added lines (`write_item`, `cmd_undo`, `safe_path`'s writable list, `preview_lines`, `main`).
- **The tables the recode rewrites are a registry** (`RECODE_*` in the block), and a test fails when the schema holds a table or column the registry doesn't classify. When Sprint 5 merges (or this sprint merges second), that test names exactly what to add: `promises` (project, id), `links` (from and to item IDs), `item_labels` (item ID), and `decisions.replaces`.
- **Sprint 5 has merged (`8b2b34b`), `main` is in this branch and the registry is extended** (09-10). Ready to merge once the full suite passes.

## Decisions taken (BL-111 left these open; reverse any in review)

1. **A recode is its own proposal item**, `op: "recode"` on `projects`, not a set of row edits. Apply writes it inside the apply's one transaction, and undo reverses it from `change_log` entries on a pseudo-table `recode`. The ordinary field-by-field undo can't do it (it keys on item IDs, which a recode changes).
2. **IDs keep their numbers** (`ORX-A-001` becomes `FAL-A-001`). Item rows keep their `updated_at`: a rename is not a content change.
3. **History follows.** `change_log` rows are rewritten to the new IDs (`item_id`, and `id`, `milestone` and `project` values), so each item's history and the early-warning signals stay with it. The recode itself is logged as `recode` rows, so undo can map back.
4. **Rejected fingerprints are hashes of the project code**, so they are recomputed from the rejected items kept in `system/staging/` and `applied/`. A fingerprint that matches no kept proposal can't be tied to a project and is left alone (the cost is a rejected item being proposed again, once).
5. **The folder is never renamed by creaite.** `--folder` records the new name Alan has already given the engagement folder (it must exist), updates the register row, and rewrites every item's `source` path (`projects/<old folder>/…`) and the search sidecars to match. Without `--folder` the folder stays, and the command warns if its name still holds the old code or name.
6. **`reminders.dismissed_forever`** (settings) is not written by the apply, because settings are changed through the settings writer with its own backup. The preview prints the exact `propose.py setting …` command to run after the apply.
7. **Pending proposals** that mention the old code (whole token) make the recode refuse, listing them. Checked at stage and again at apply.
8. **Reported, not edited:** the old code or name in the people register, `PORTFOLIO.md`, settings, and other lines of the project's `CLAUDE.md`.
9. The old code goes into the register's **Retired codes** and can't be reused; the new code must not exist, be retired or appear anywhere in the register.

## Items

Commit each separately.

### 1. The engine (`tracker.py`)
- `recode_project(con, item, apply_id, via)`: validate; rewrite `projects`, the project column and IDs of `milestones`, `workstreams`, `actions`, `raid`, `decisions`, `updates`, the `milestone` links, `source` paths when the folder changes, `change_log`, `rejected` and `vault_search`; check `PRAGMA foreign_key_check`; log the recode.
- Hooks: `write_item` (the `recode` op), `cmd_undo` (a `recode` group is reversed in order with the other changes), `WRITABLE` gains `system/search/` (derived sidecars, for the folder rename).
- Foreign keys are deferred for the transaction (`PRAGMA defer_foreign_keys`), and the schema's own `CHECK`s run on every rewritten row.

### 2. The request (`propose.py`)
- `propose.py recode <OLD> <NEW> [--name "…"] [--folder "…"] [--dry-run]`: builds the spec (the recode item; the register row, Retired codes row and Shared table; the project `CLAUDE.md` heading; `mentions.jsonl`; sidecars), prints the preview (counts per table, sample new IDs, files changed, things to check by hand, the settings command), and stages it approved unless `--dry-run`.

### 3. Docs and skill
`dev/BUILD.md` section, `dev/staging-format.md` (the `recode` op), `tracker-conventions.md`, the cx-edit skill (a "Recode a project" recipe), `system/creaite-rules.md` (cx-edit row), `dev/archive/sprints/STATUS.md`.

## Done when

**Tests** (`dev/tests/test_recode.py`, temporary vaults):
- a project with items in every table, a milestone-linked action and RAID item, a rejected item, an update row and a mention: after apply, `tracker.py read` for the old code returns nothing, every item is under the new code with its number, its history and its milestone link;
- `--dry-run` and a pending-proposal refusal change nothing (database, files);
- undo restores the exact previous state (all tables, the register, `CLAUDE.md`, `mentions.jsonl`, `change_log` IDs, the rejected fingerprints);
- a recode with `--folder` rewrites sources and sidecars, and undo restores them;
- an existing, retired, malformed or equal code is refused with a clear message;
- a second apply after a recode (an ordinary edit under the new code) and its undo still work;
- the registry test: every table and column of `schema.sql` is classified.
The full suite passes (`python3 dev/tools/run_tests.py`, when no other session is running tests).

**Docs** as in item 3. **Commits** with the attribution lines from the session. **Never push or merge.**

## Boundaries

- **Owns:** the recode block in `tracker.py` and `propose.py`, the one-line hooks listed above, `test_recode.py`, the docs in item 3.
- **Don't edit:** the schema (`schema.sql`; Sprint 5 owns it), `excel_sync.py`, or anything else in Sprint 5, 4b or chat-sweep's list (`dev/archive/sprints/STATUS.md`). `BACKLOG.md` and `BRD.md` are updated at merge.
- **Development guard:** sample data and temporary vaults only. Never touch Alan's live vault.
- **Release:** an engine change, so it ships in a release zip; the release notes line is added when the release is cut (v1.2.0 is 4b's).
