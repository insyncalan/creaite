# Sprint: Permissions and the assistant (BL-93, BL-96, BL-100, BL-86)

**Status (09-10-2026): merged into `main` (`bd0ebf5`, 00:51); worktree removed.**

Branch `sprint-permissions`, worktree `../creaite-permissions`. Runs in parallel with `sprint-sweep-alerts` (`../creaite-sweep`) and `sprint-pages` (`../creaite-pages`). **This sprint merges first.** Read BL-93, BL-96, BL-100 and BL-86 in `dev/BACKLOG.md` first. They hold Alan's decisions; follow them, and where one says "to confirm", take its stated default.

## Goal

The assistant and the live server can do the work Alan asks for in the project folders, with each widening as narrow as possible, confirmed and undoable. Alan can paste an image into Ask creaite. creaite opens as an app from a launcher.

## Security stance

This sprint widens permissions, so treat every rule as security-sensitive:
- **Narrow by construction:**
  - paths only inside the vault and the projects root (`paths.projects_root()`);
  - never the engine, the database or the permission files themselves, except through the confirmed edit BL-96 describes;
  - never a wildcard over the home folder.
- **Every write is confirmed in the panel first and logged.** Every rule added is listed by `permissions.py list` and reversible with `undo`.
- **Never a skip-permissions mode.**
- **`doctor.py` checks the rules** in `.claude/settings.json` match what `permissions.py` allows, and flags anything broader.

## Items

Commit each separately, in this order.

### 1. BL-93: Read all project documents; write to all project folders (S)

- **Where:** `paths.py`, `FS_RULES` and the allow lists in `live_server.py`, `permissions.py`, `doctor.py`, one narrow rule in `.claude/settings.json`, and `system/creaite-rules.md` (Project documents).
- **The OneDrive layout:** with BL-85 the projects may live outside the vault. Rules must resolve the projects root, never hard-code a path, and never store an absolute path.

### 2. BL-96: Ask creaite may edit files in the creaite and project folders (M)

- **Confirmed edits:** as BL-96 sets out, including lifting the deny entries for the permission files only for a confirmed edit.
- **Narrow rules** for the folders.
- **The panel** shows exactly what will change before Alan confirms.

### 3. BL-100: Paste an image into Ask creaite (S)

- **In the chat box:** paste, drop or attach an image; thumbnails show; a shrink step; images in the history bubbles; a larger view.
- **The upload:** a route with type and size checks.
- **Where images live:** a chat-images folder covered by `READ_TOOLS` and `FS_RULES`. Deleting a chat deletes its images.

### 4. BL-86: creaite as a Chrome app, started by a launcher (M)

- **Part 1, installable:** a manifest, the icon (`dev/icon/`) and offline routes.
- **Part 2, the launcher** (`system/scripts/launch.py`): starts the live server for Alan, with a "still here" route and a stop-when-closed timer, as BL-86 sets out.
- **Ports:** the dev repo uses port 8766 and a live vault uses 8765, so the launcher reads `live_mode.port`. Two vaults must be able to run side by side.
- **Engine list:** add the new files to the engine list in `paths.py`.

## Boundaries

- **Owns:**
  - `permissions.py`, `FS_RULES`, `READ_TOOLS` and the allow lists in `live_server.py`;
  - `.claude/settings.json`;
  - the Ask creaite chat box and its history;
  - the manifest, the launcher and their routes;
  - `doctor.py`'s permission checks.
- **Don't edit:**
  - **`sprint-sweep-alerts` owns:** `sweep.py`, the cx-sweep skill, `calendar.json`, meeting prep and VIPs.
  - **`sprint-pages` owns:** the Files page, the project page, `files()`, and the trends and flow code.

  Note anything needed under "Hand-offs".
- **Shared files** (`dashboard.html`, `live_server.py`, `paths.py`, `help.md`, `dev/dashboard-spec.md`, `system/creaite-rules.md`):
  - put new code in its own marked section, `/* ===== Permissions and assistant (BL-93, BL-96, BL-100, BL-86) ===== */`;
  - add live-server routes in a marked block;
  - don't reformat unrelated lines;
  - leave `BACKLOG.md` and `BRD.md` alone (updated at merge).
- **Help:** update `help.md`, then run `python3 dev/tools/build_guides.py`.
- **Development guard:** sample data only; test with temporary vaults and a temporary projects root.

## Done when

**Tests:**
- each new rule is exactly as narrow as specified;
- a path outside the vault or the projects root is refused;
- the engine, the database and the permission files are refused, except through the confirmed edit;
- `permissions.py list` and `undo` cover every rule added;
- doctor flags a broader rule;
- image upload type and size checks; images deleted with their chat;
- the panel's paste and attach in headless Chrome;
- the manifest and offline routes;
- the launcher starts the server on the configured port, and the stop timer.

The full suite passes: `python3 dev/tools/run_tests.py`.

**Docs:** the spec updated, and a short "Permissions and the assistant" section in `dev/BUILD.md`.

**Commits:** each item committed separately on `sprint-permissions`, with the attribution lines from the session's instructions. Never push or merge.

## Hand-offs

(Changes needed in files another sprint owns.)
