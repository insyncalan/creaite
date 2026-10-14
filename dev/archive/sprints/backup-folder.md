# Sprint: Backups go to `_Portfolio/99 System/creaite backups` (BL-112)

Branch `sprint-backup-folder`, worktree `../creaite-backup-folder`, made from `main` (`4987305`) on 09-10-2026. Read BL-112 in `dev/BACKLOG.md` first; it holds Alan's decisions. A small sprint (S): one default, one migration, one guard, wording and tests. **Plan confirmed 09-10-2026; not built yet.**

## Goal

creaite's closed copy of the daily database backup goes to `_Portfolio/99 System/creaite backups` instead of loose in `_Portfolio`. `99 System` is reserved for creaite's own files in the portfolio folder, never listed, indexed or read as a document. Vaults already on the old default move to the new one at the next update, with Alan shown the change first.

## Sequencing

- **Build after `sprint-4b` merges.** BL-112 says so because 4b changes `update.py` (its brief owns it: the retired deny rules in `merge_permissions`). Nothing else here conflicts: `sprint-5` and `sprint-recode` touch `tracker.py` elsewhere, and this sprint changes only `offsite_dir`'s wording if at all.
- **It ships in v1.2.0** with the others (board, 09-10-2026): add a line to `dev/release-notes/1.2.0.md` when it merges.
- **Everything new in `update.py` is one marked block** (`# ===== Backups folder (BL-112) =====`) plus one added call line in `install` and one in `plan`, so a later merge with 4b reads cleanly.

## Decisions (BL-112; the one marked "to confirm" is confirmed by Alan, below)

1. **New default** `_Portfolio/99 System/creaite backups`, in `paths.LOCATION_DEFAULTS` and `system/templates/settings-defaults.json`. The copy is written whole, as now, keeping the latest 14.
2. **creaite creates `99 System` and `creaite backups`** on first use. `offsite_copy` already runs `mkdir(parents=True)`, so no new code is needed there; a test proves it. A missing folder never fails anything. `doctor.py` warns only if the folder can't be written.
3. **`99 System` is never indexed (confirmed).** It joins the default `never_index`, **and** `paths` always treats it as reserved, whatever the saved list says. Today `never_index` is replaced, not merged, by a vault's saved list, and an update never adds to an existing list, so a saved list alone would leave the backups open to Files, the index and Ask creaite. One helper, `paths.never_index()` (the saved list plus `zz Archive`, `_Templates` and `99 System`), replaces the five places that read the setting (`_excluded_dirs`, the documents scan, `online_only_files`, `never_index_patterns`, `permissions.py`'s check).
4. **Migration at update, shown first and logged.** In `update.py`: if `locations.offsite_backup` is exactly the old default (`_Portfolio/creaite backups`, trailing slash ignored) it becomes the new one; any other value (Alan's own) is left; `99 System` is appended to `locations.never_index` if absent. A vault with no `locations` block gets the new defaults through the existing add-missing-keys merge. Both changes appear in the update's "settings" preview (`plan`) before Alan confirms, are written to `settings-log.jsonl` with the old value and `by: "update X.Y.Z"`, and are covered by "undo update" (which already restores `settings.json`). Running it twice changes nothing.
5. **The old folder is left alone.** creaite never moves or deletes the old copies. Once the new folder holds a copy, `doctor.py` adds a note: "the old folder `_Portfolio/creaite backups` still holds N copies and can be removed". Moving them is a separate confirmed step if Alan asks (BL-93).
6. **Not changed:** the 14-copy limit, the atomic write (temporary name, then rename), the local backups, and the rule that the live database is never copied.

## Items

Commit each separately.

### 1. The default and the reserved folder (`paths.py`, `settings-defaults.json`)
- New `offsite_backup` default; `99 System` in the default `never_index`.
- `paths.never_index()` and its five call sites (decision 3). Check each reader with `grep -n never_index system/scripts/*.py`; 4b may have changed `live_server.py` and `permissions.py`, so use the version on `main` at that time.

### 2. The migration (`update.py`)
- `migrate_backup_folder(text)`: takes `settings.json` text, returns the new text and the changes; used by `plan` (to show) and `install` (to write, after the add-missing-keys merge). Logging with the old value as in decision 4.

### 3. Doctor (`doctor.py`, and `tracker.py`'s `offsite_dir` if its message needs the path)
- The "no copy yet in …" line names the new folder (it already reads the setting).
- Warn only if the folder can't be created or written (try `mkdir` and a temporary file, then remove it); keep the "OneDrive running?" age note.
- The old-folder note (decision 5), once the new folder holds a copy.

### 4. Wording
- `system/creaite-rules.md` (the `locations` row of the folder map), `system/templates/help.md` ("Live server and backups", line about the OneDrive copy), then `python3 dev/tools/build_guides.py`; `dev/BUILD.md` (the BL-85 note and a short BL-112 note); `dev/BRD.md` FR-84; the release notes line.

## Done when

**Tests** (`dev/tests/test_onedrive_projects.py`, `test_update.py`, and `test_tracker.py` or `test_codes.py` for `paths`):
- the copy lands in `<Engagements>/_Portfolio/99 System/creaite backups/` with both folders created from nothing; the newest 14 are kept; no temporary file is left behind;
- the folders being absent, or unwritable, never stops a daily backup or a session start (doctor warns, only for unwritable);
- an update on a vault with the old default moves it, appends `99 System` to `never_index`, shows both in the plan, writes the log lines with the old value, and is undone by "undo update"; a custom `offsite_backup` is left alone; running it twice changes nothing; a vault with no `locations` block ends on the new defaults;
- `99 System` is skipped by Files, the search index, `online_only_files` and the Ask creaite read rules **even when the saved `never_index` is the old list**;
- doctor mentions the old folder only after the new one holds a copy, with the right count;
- the existing OneDrive tests now look in the new folder.
The full suite passes (`python3 dev/tools/run_tests.py`, on a quiet machine).

**Docs** as in item 4. **Commits** with the attribution lines from the session. **Never push or merge.**

## Boundaries

- **Owns:** the backup default and `paths.never_index()`; a marked block in `update.py`; the doctor lines; wording.
- **Don't edit:** `merge_permissions` and the rest of `update.py` that 4b changes; the schema or anything Sprint 5, recode or chat-sweep own (`dev/archive/sprints/STATUS.md`). `BACKLOG.md` is updated at merge.
- **Development guard:** sample data and temporary vaults only; never touch Alan's OneDrive or live vault.

## Confirmed by Alan (09-10-2026)

1. `99 System` is **always** skipped, whatever the saved `never_index` says (decision 3 stands).
2. **The old copies stay where they are.** creaite offers no move at the update; doctor only tells Alan when the old folder can be removed (decision 5 stands).

## Hand-offs (done 09-10-2026, after 4b merged)

- The assistant prompt in `live_server.py` now says "Never read zz Archive, _Templates or 99 System …", and `dev/release-notes/1.2.0.md` carries the backup folder (what's new, and before you update).
- The update preview shows the move in the release notes text (`plan()["notes"]`), not as its own line, so `dashboard.html` is untouched.
