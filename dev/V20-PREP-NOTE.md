# v2.0.0 prep: v20-tiptap-vendor brought up to release-192

For Team 1. 14-10-2026, Alan approved starting v2.0.0 (BL-301 Notes). This branch was parked at `bc50d4f` (origin/main as of v1.8.x); it now has `origin/release-192` (`dde4343`: v1.9.0, v1.9.1 and v1.9.2) merged in. Nothing pushed.

## What changed since parking

release-192 brought in 33 first-parent commits: v1.9.0 (Meeting prep: BL-286, BL-287, BL-293, BL-295, BL-297 D, BL-298, BL-125 A, BL-288), v1.9.1 (BL-314 ask creaite routing and claims, BL-321 day arrows) and v1.9.2 (BL-315 reject reasons, BL-319 Today as one home and the sidebar on Preact, BL-320 settings catalogue, Work's reflow). The dashboard is now further on Preact (`system/templates/dashboard/src/components/…`, `stores/…`): the BL-301 wrapper `creaiteEditor` should be written as a Preact component over `tiptap.module.js`, beside those stores.

## Conflicts

**None.** Git merged cleanly: this branch only adds `system/templates/vendor/tiptap/`, `dev/tiptap/`, `dev/tools/tiptap*.py`, its tests and a `VENDORED` check in `dev/tools/check.py`; release-192 didn't touch any of them. `system/templates/vendor/README.md` merged both sections (Preact, Tiptap). `dashboard.html` is release-192's unchanged: nothing in the dashboard loads the editor yet, so no rebuild was needed (check.py's build-freshness check agrees).

## Checks

- `tiptap.py fetch` (46 pinned, hash-checked tarballs into `dev/.cache`), then `tiptap.py vendor --check`: **a fresh build**, byte for byte.
- `check.py`: **OK**.
- `run_tests.py -j 2 test_vendor_preact test_vendor_tiptap test_tiptap_pin test_tiptap_roundtrip test_dashboard_split test_snapshots`: **6 passed, 0 failed**.

## The round-trip gate (sample vault only)

- `python3.14 dev/tools/tiptap_roundtrip.py --exact`: **current 7/7, minutes 25/25, constructs 25/25, hard 69/69, stable 17/17; 0 failed.**
- `python3.14 dev/tools/tiptap_roundtrip.py --vault . --private --exact --json` (the repo's own sample vault, the same path Alan's run takes): **ABC pane 1 and pane 2 pass.**

It was **not** run against any real vault.

## Alan's command (the real-vault gate; read only)

From the development repository, on this branch, once per machine `python3.14 dev/tools/tiptap.py fetch`, then:

```
python3.14 dev/tools/tiptap_roundtrip.py --vault "<your vault folder>" --private --exact --json
```

It only reads (each project's Current state, through that vault's own `locations`), writes nothing, prints no text (ids, pass or fail, byte lengths, and for a failure the offset and construct), and exits 1 if any pane fails. Send the JSON back; it's safe to share.

---

# v2.0.0 prep: v20-notes-server brought up to release-192

For Team 1. 14-10-2026, Alan approved starting v2.0.0 (BL-301 Notes). This branch (BL-301's server side for B, C and E; see `dev/V20-NOTES-SERVER-NOTE.md`) was parked at `612b44d`; it now has `origin/release-192` (`dde4343`: v1.9.0, v1.9.1 and v1.9.2) merged in. Nothing pushed. The Tiptap branch's own prep note (gate results, Alan's command) is on `v20-tiptap-vendor`.

## Conflicts (3, all resolved by keeping both sides)

| File | What clashed | Resolution |
|---|---|---|
| `system/scripts/tracker.py` `build_index` | the index stamp: this branch's `"version": INDEX_VERSION` (BL-301) against release-192's `"readers": INDEX_READERS` (BL-276) | the stamp carries both; `index_state` checks both (version first, so an older vault says "built by an older release" and rebuilds once) |
| `system/creaite-rules.md` folder map, `system/scripts/` row | release-192 added `settings_catalogue.py`, `health.py`, `health_fixes.py`, `close_day.py`, `claims.py` | release-192's row, with `notes.py` added before `vendor/` |
| `dev/tests/test_tracker.py` `make_vault` | the scripts copied into test vaults | both lists (`claims.py`, `settings_catalogue.py`, `health.py`, and `notes.py`) |

## What else changed since parking

- **BL-320, the settings catalogue (in release-192): one fix needed.** This branch adds `locations.folders.notes` (`08 Notes`) to `settings-defaults.json`; every default key must have a catalogue entry. Added in `settings_catalogue.py`: `locations.folders.notes` ("Folders and OneDrive", "Notes folder"), and in `FIXED` beside the other folder keys (changed at set-up, not reset from Settings). `test_settings_catalogue` passes.
- **BL-275 (PDF search), BL-323 (backups) and BL-09 (`_Archive`, `paths.resolve`) are not in release-192.** They are on `release-193` (BL-275, BL-323) and `v194-archive` (BL-09), so the next catch-up will meet them. Looked ahead, without merging:
  - **BL-275:** release-193 raises `INDEX_READERS` to 3 at the same stamp line resolved above; expect the same small conflict, same resolution (keep both keys).
  - **BL-323:** its daily zip holds the database, `system/config/`, the root `CLAUDE.md`, `system/staging/` and the git bundle; never project files. So **`08 Notes` is out of the zip**, as BL-301 and BL-323 both imply (notes are project files, already in OneDrive). Two things for Alan: (1) `system/staging/notes-sent.json` (references and hashes only, no text) is **in** the zip, which is fine; (2) BL-301 B saves a note's **draft text to `system/staging/drafts/` as Alan types**, and BL-323 puts `system/staging/` (drafts included) in the zip and its OneDrive copy. A confidential note's draft would therefore reach `_Portfolio/99 System/creaite backups/`. Same company OneDrive as the note itself, so likely acceptable, but it is Alan's call; the alternative is excluding note drafts from the zip.
  - **BL-09:** `v194-archive` moves `zz Archive` to `_Archive` and adds `paths.resolve`'s archive mapping. This branch's `paths.note_files` and `_excluded_dirs` read through `paths.folder`, so an archived project's notes should follow; check `never_index` and `ALWAYS_NEVER_INDEX` against the notes folder when merging.
- **Security: no change.** This branch does not touch `reach.py`, `permissions.py`, `live_server.py`'s tool lists or `.claude/settings.json`; the merged diff against release-192 has none of them. `test_reach`, `test_guard_pinned` and `test_record_commands` pass unchanged. `notes.py` is a library with no command line, so it needs no `reach.SCRIPT_COMMANDS` entry. Decision 6 in the server note stands (a note in OneDrive still counts as outside content).

## Checks

- `check.py`: **OK** (including the type check and the Python 3.9 check).
- `run_tests.py -j 2 test_notes_server test_search test_search_dashboard test_search_eml test_search_live test_reach test_guard_pinned test_record_commands test_settings_catalogue test_settings_calmer test_settings_page test_check_py39 test_tracker test_onedrive_projects test_agendas_files`: **15 passed, 0 failed**.
- Quick tier, `run_tests.py -j 2 --quick`: **71 passed, 0 failed**.

## Still to do before v2.0.0 ships

As in `dev/V20-NOTES-SERVER-NOTE.md`: ship only with parts A, D and E; the dashboard side (Files, ⌘K's Notes group, the Notes tab, the drawer, `/api/notes/*`, `/api/edit/ai`) is not built. Settings › Folders and OneDrive will now list "Notes folder" as a fixed setting; the UI needs nothing more for it.
