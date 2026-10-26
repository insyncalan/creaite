# #385 phase 3: the guarded changes for a project's own folder

Four diffs, one per guarded file, for Alan's approval. They are cut against **origin/v269-chain 2da753ed** (`git diff --abbrev=8`). `git apply --check` is clean on v269-chain, on v269-main eb32046b (its guarded files are the same) and on main a62fbb0a (live_server.py applies with an offset). No pin moves: test_guard_pinned passes with the diffs applied, so there is no 385-pins diff.

| Diff | sha256 |
|---|---|
| 385-tracker.diff | 0dfd7d913534bbf4c1b4237aeefca9659193e28174c657f090a6c7c43379a6be |
| 385-reach.diff | 112a19b0082f4f6b632e8a96017a2c8195b325e5a7cf3d927a1c71104fba208c |
| 385-permissions.diff | e0a3cef7e9131135d62475503a99ead2e122de0825c4e25c18cc747512920b2c |
| 385-live_server.diff | 9f83a7c628145879e2ac3f11996e43acbd3fbbc8a6da92100496ea8a730f2edc |

The diffs use phase 2's paths.py API: `project_roots` (registered, fail closed), `_mapping` (archived entries too), `archive_slot`, `parts_below_base`, `in_mapped_notes`, `tool_patterns`, `project_paths_problem`, `project_mapping_problem`, `_loc_project_roots`, `_pattern_of`, `_fold` and `_mapped_name`.

- **tracker.py:** `safe_path` looks for skipped names under every base: the projects root and each mapped folder, compared as macOS compares names. `_copy_bases` adds each mapped folder. `_named_notes` also uses `in_mapped_notes`. `safe_path` refuses any path, for every purpose (write, copy, remove, mkdir), under a mapped folder or projects root that isn't there (Cap's MEDIUM 2: `_op_write`'s `mkdir(parents=True)` would make it on the laptop's own disk); the portfolio may still be made inside a projects root that is there. An undo of a remove skips, and says so, rather than restore into a missing base. Moves need no check of their own: a mapped folder and its slot share the folder that holds them, and the source must exist. `check_move` adds `_outside_end_problem`: an end outside `allowed_roots` is allowed only for an archive or restore whose ends are exactly the mapped folder and its `archive_slot`. A move's `made` has no stored path beside the folder, so it is recorded as None.
- **reach.py:** `roots()` adds one "projects" root for each mapped folder (`mapped_roots`): never its parent, its slot or an archived entry. `_never_verdict` checks skipped names under every base and refuses the archive folder beside a mapped project. `archive_move_problem` measures moves with `_move_parts`, from the folder or exactly its slot. `_portfolio_folder` never treats a mapped name as the portfolio. Grep marking includes each mapped folder.
- **permissions.py:** `_config_problem` calls `paths.project_paths_problem`. `project_dirs()` is the projects root plus each registered mapped folder from `paths._loc_project_roots` (already fail closed, under the register's spelling, so a saved key in another case still counts), written `~/…` and inside home only. It is used by `_add_refused`, `broad_rule` and `cmd_projects_root`, which adds every missing folder and logs one entry each, so undo takes them back one at a time. `dirs_for_locations` and `sync_project_dirs` keep additionalDirectories in step with project_paths.
- **live_server.py:** `extra_dirs` adds `reach.mapped_roots()`, the same list the hook uses. `deny_tools` uses `paths.tool_patterns`. Cap's LOW 4 is handled two ways. On the card, `card_dirs` puts the matching .claude/settings.json change on the same card as a settings.json change (merged into ask creaite's own change to that file, if there is one); if that change is refused, neither is offered. On a page save, `fs_save` calls `project_dirs_follow` in the same save.

## Cap's Full review (26-10-2026)

- **reach.py:** names compare as macOS compares them (`folded_under`, paths._fold: case and Unicode form) in `skipped_below`,
  the skipped-name test and `_move_parts`, as tracker's `_below_bases` does (MEDIUM 2). The archive slot beside every
  well-formed entry (`paths._loc_raw_roots`) stays never, so a mapping dropped on read (its folder now a symlink) never lifts it
  (LOW 2).
- **tracker.py:** `safe_path` keeps its old projects-root lines exactly and adds the #385 checks after them
  (`_missing_base_check`, `_skipped_below_bases`), and `check_move` keeps its `archive_move_problem` lines and checks
  `_outside_end_problem` after them: the landed #292 wording diff's hunks keep their context, so test_minutes_by_others_filing's
  scratch (used by test_tracker_inode_hold) can still reverse #292, #261 and E1 with this diff in tracker.py (MEDIUM 3: #261 and
  #292 landed in 2.6.1 and 2.6.4; the conflict was with #292's reversal, not #261's). An archive or a restore with a mapped project
  at either end, by name or by folder, goes exactly to or from its slot even when both ends are in reach (`_mapped_end`, LOW 1).
  An undo of a write or a draft status line into a base that isn't there skips, as a remove does (LOW 3).
- **permissions.py:** additionalDirectories never takes the home folder or a place on, or holding one on, reach's never list
  (`never_folder`, whatever is approved); `card_dirs_problem` refuses, on a card that changes locations, a .claude/settings.json
  change adding any folder that isn't the card's projects root or a project's own folder (MEDIUM 4). `cmd_projects_root` (and
  `cmd_apply`, which a sync's removes would also make repeat) numbers log entries with `next_id()` (LOW 7). A sync takes out the
  folder of every well-formed entry no longer honoured (archived, or its folder now a symlink: `_own_folder_dirs`, LOW 8).
- **live_server.py:** `card_dirs` refuses the settings change and ask creaite's own .claude/settings.json change together when
  `card_dirs_problem` says so (MEDIUM 4). A page save whose second write fails answers `ok: false` with the message (LOW 8). The
  expect_text save (`fs_write_if_unchanged`) of settings.json gets the notes-folder check and the matching additionalDirectories,
  as a plain write does (LOW 6).

Tests: `dev/tests/test_project_paths_385_guarded.py` (44 tests, each with a key-line mutant; StackOn292And261 shows the diff
before the review broke the #292 reversal) applies the diffs to a throwaway vault.
