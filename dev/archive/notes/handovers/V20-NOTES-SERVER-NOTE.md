# v20-notes-server: BL-301 server side (v2.0.0)

For the Scrum Master. Laptop 2, item 3 of `dev/LAPTOP-2-WORK.md`. Branch `v20-notes-server`, from `origin/main` at `dd7bb9f`. The dashboard isn't touched.

## What's built

- **The notes folder.** A new folder kind, `notes`, in `paths.py`: `LOCATION_DEFAULTS.folders.notes = "08 Notes"`, `DEFAULT_FOLDERS.notes = "notes"`, and the same key in `settings-defaults.json`, so `update.py` adds it to an existing vault. A vault whose saved `locations.folders` predates it gets `08 Notes` from the defaults anyway. Portfolio and Unfiled notes go in the portfolio's notes folder (`_Portfolio/08 Notes`, or `projects/_portfolio/notes`).
  - **Made on first use:** nothing creates the folder for an existing project until its first note is saved.
  - **New projects get it:** `notes` is now in `PROJECT_SUBFOLDERS` for the default layout. With a projects folder, `propose.folder_ops` adds `mkdir <project>/08 Notes` when Alan's skeleton doesn't have one, and adds it only once when it does. Alan's `_Templates/_Skeleton` is never written to.
  - **Listing:** `paths.note_files(code)` returns the `.md` files directly in the notes folder; pictures in `_images/` are not notes. `paths.is_note(p)` and `paths.NOTE_IMAGES` are also new. `project_files` returns notes as their own kind (`"notes"`), as it does agendas (BL-135). `_excluded_dirs` keeps the notes folder out of the documents walk, so in an outside root a note or its picture is never a document.
- **The note format** is in a new library, `system/scripts/notes.py`. It has no command line, so it needs no `reach.SCRIPT_COMMANDS` or permission entry, and it never writes a project file.
  - `parse` and `render` round-trip the front matter: `title, created, updated, tags, pinned, confidential, date, with`. Unknown keys are kept after the known ones. Lists and flags are read whatever was written.
  - `touched` is the save stamp: it sets `updated` and fills `created` if missing.
  - `template(name, title, …)` builds a note from the four templates in `system/templates/notes/` (`blank`, `stakeholder`, `lessons-learned`, `working-session`). A Working session note also gets `date` and `with`.
  - `file_name` and `new_path` name a note by its title; a taken name gets a number (`paths.free_path`). `images(code)` is the `_images` folder.
  - `index_text`, `index_date` and `is_confidential` serve search.
- **`system/staging/notes-sent.json`** (`paths.NOTES_SENT`):
  - Shape: `{"version": 1, "notes": {"<stored note path>": [{"p": 4, "fp": "<16 hex>", "ids": ["ABC-A-010"], "at": "YYYY-MM-DD HH:MM"}]}}`. It never holds text.
  - Functions in `notes.py`:
    - `paragraphs(body)`: blank-line blocks numbered from 1, the `#p<n>` of a source.
    - `fingerprint(text)`: a hash of the paragraph with whitespace normalised.
    - `record_sent(rel, [(n, text, ids)], at)`: an atomic write.
    - `unsent(rel, body)`: the paragraphs that are new or changed since the last Find updates.
    - `sent_ids(rel, body)`: the margin ticks. A paragraph that moves keeps its tick, because matching is by fingerprint.
  - Nothing calls these yet. The part E route (`/api/notes/find`) will.
- **Search** (kind `note`):
  - **Indexing:** `tracker.build_index` gets one hook, `index_entry_text(f, folder)`. A note is read by `notes.index_text`: title, tags and people, then the body, with the front matter left out. It is dated by `notes.index_date`: the Working session date, else `updated`, else `created`. `text_of` is untouched (clash with BL-276 avoided). `STORED_KIND["notes"] = "note"`.
  - **Rebuild after updating:** `INDEX_VERSION = 2` is written into `system/search/index-built.json`, and `index_state` reports a stamp from an older release as stale ("built by an older release"), so an existing vault rebuilds once.
  - **`search.py`:**
    - A new **`notes`** group in the results and totals.
    - The type words `note` and `notes` make a Notes chip.
    - A note opens in the preview, and the preview shows it without its front matter (`indexed_text`).
    - Ask's `context` reads notes and labels them "Note (internal)". A note marked **confidential** is never read there: its text is left out and only counted ("n confidential note(s) also matched; their text is left out").
    - Unknown kinds from a later release are skipped instead of raising `KeyError`.
    - For check.py, `file_result` and `file_passages` were split out of `file_results` and `context`.
- **`doctor.py`:** the notes folder joins the folders that must not overlap a meeting folder. `mapped_folders` doesn't report a notes folder that hasn't been made yet.
- **`system/creaite-rules.md`** (BL-301's "Rules text"):
  - Folder map: `notes/` in the project row; `08 Notes` and the skeleton in `locations`; portfolio notes; `notes-sent.json` in staging; `notes.py` in scripts; `notes/` in templates.
  - "Approval before writes" names the Find updates panel.
  - New Dashboard editing lines: **One editor** (Tiptap) and **Notes**.
  - Project documents: notes aren't documents and are **passive until Find updates**.

## Files touched

- New: `system/scripts/notes.py`, `system/templates/notes/{blank,stakeholder,lessons-learned,working-session}.md`, `dev/tests/test_notes_server.py`, this note.
- Changed:
  - Engine: `system/scripts/paths.py`, `tracker.py`, `search.py`, `propose.py`, `doctor.py`, `system/templates/settings-defaults.json`, `system/creaite-rules.md`.
  - Tests:
    - `dev/tests/test_tracker.py` copies `notes.py` into test vaults.
    - `dev/tests/test_search.py` and `test_search_live.py` now expect the `notes` group in results and totals.
    - `dev/tests/test_onedrive_projects.py`: the default layout's new project has five subfolders.

## Tests

- `dev/tests/test_notes_server.py`, 24 tests on fixtures in both layouts (vault `notes/` and OneDrive `08 Notes`):
  - format, templates, names, paragraphs, `notes-sent.json`;
  - listing as its own kind, never documents, never extracted, `is_note`;
  - search group, type word, dates and front matter in the index, preview, confidential notes kept from Ask's context;
  - portfolio notes, the index version stamp, new-project folders (with and without the folder in the skeleton), doctor.
- Quick tier, `run_tests.py -j 2 --quick`: 59 passed, 0 failed. Then `test_search`, `test_search_live`, `test_search_dashboard`, `test_agendas_files` and `test_notes_server`: 5 passed. The full Chrome tier was not run here; run Actions.
- `python3.14 dev/tools/check.py`: `check: OK`.

## Alan's answers (13-10-2026)

Alan accepted all seven decisions below as written. In particular:
- **Shipping:** **ship this branch only with the rest of BL-301** (parts A, D and E), not in a v1.9.x release. Please don't merge it until then.
- **Confidential notes:** they stay searchable on the laptop but out of ask creaite.
- **Reading a note in OneDrive:** it still counts as outside content (no guard change).
- **Search:** notes get their own group, not hidden by "include documents".
- **Routine choices:** dates, folder creation and paragraph numbering, all accepted.

## Decisions for Alan

1. **Dates in the front matter are `YYYY-MM-DD`** (`created`, `updated`, `date`), as everything else is stored. The notes list's "recent" order can use the file's modified time. (The write-up didn't say.)
2. **The default layout's folder is `notes/`** (the write-up said so). New projects in both layouts get the folder. Existing projects get it on their first note. Alan's own skeleton folder isn't changed; creaite adds the `mkdir` itself.
3. **Search shows notes in a group of their own, "Notes"**, next to Documents, rather than inside Documents (as agendas are). This follows "a Notes filter in search". The Settings switch "include documents" does not hide notes.
4. **A confidential note is still indexed and found by search** (search stays on the laptop). Its text is kept out of Ask's gathered context until the dashboard's "asks once" (parts D and E) exists.
5. **Find updates' paragraph is a blank-line block, numbered from 1.** Its fingerprint ignores spacing, so reflowing a line doesn't make it new.
6. **`reach.py` is unchanged.** Writing a `.md` note is already "ordinary" (Alan's own notes). With a projects folder outside the vault, however, reading a note still counts as "read a project document" for the outside-content mark, because notes sit in the engagement folder that `document_roots` covers. Whether notes should be exempt (they're Alan's words, but he may paste a client's email into one) is a guard change for Alan to decide. It isn't made here.
7. **The rules text describes the finished v2.0.0** (Tiptap everywhere, Find updates, the AI suggestions). It should ship only with parts A, D and E, so this branch shouldn't go into a v1.9.x release.

## What the dashboard part needs (not done here)

- **Files:** add `"notes"` to the folder list in `src/files.js` (beside agendas). `build_dashboard.files` already carries notes as `f: "notes"`, but not the portfolio's (it adds only minutes and transcripts for `_portfolio`), so portfolio notes need adding there for the Portfolio view.
- **Search (⌘K):** add `notes` to `SGROUP` in `src/ask.js` (label "Notes") and a Notes filter. Results come with `opens.type: "preview"`; the Notes tab may want its own opener. `ask.js:86`'s kind mapping should map `f === "notes"` to `note`.
- **The Notes tab, the drawer, autosave through `filechange.py`, `/api/notes/*`, `/api/notes/find`, `/api/edit/ai`:**
  - `notes.template`, `notes.new_path`, `notes.touched`, `notes.render` and `notes.parse` give the file text and name.
  - `notes.record_sent`, `unsent` and `sent_ids` give part E's record and margin ticks.
  - `paths.folder(code, "notes")` is the folder to make on the first save.
- **Prep:** leave confidential notes out (`notes.is_confidential`). The peek's "n notes mention this" can come from `vault_search` with `kind = 'note'`.
- **Help** and `dev/dashboard-spec.md` updates.
