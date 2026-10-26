# Proposal: a filtered git bundle in the daily zip (guarded file: system/scripts/backup.py)

`backup-bundle.diff` is a patch for `system/scripts/backup.py`. It is NOT applied on any branch. Apply it only after review, off `origin/main`
(`git apply --check dev/proposals/bundle/backup-bundle.diff` passes on a62fbb0a).

Revision 3. sha256 of backup-bundle.diff: `f5f5a851d5022169fe9ff1234fb33fcadae794706dd21242626f98a5a0206922`

## Why

`make_bundle` runs `git bundle create --all`, which copies every commit ever made. The gitignore fix (vault-gitignore) only stops NEW commits
holding ask creaite chats, their images, `vip.json` and the raw calendar. A vault whose older commits already hold them keeps putting them
into every daily zip and its OneDrive copy (BL-323: the zip must never hold chats, images or vip.json; BL-288).

## Options

| | (a) orphan commit in the real repo | (b) filtered export in a temp repo | (c) rewrite history |
|---|---|---|---|
| How | temp index and `commit-tree`, bundle one ref, delete the ref | `git archive HEAD` minus private paths, into a temp repo, one commit, bundle it | filter-branch |
| History in the bundle | one snapshot | one snapshot | full, filtered |
| Touches the real repo | writes objects (and briefly a ref) into it | no: `archive` and `rev-list` only read | rewrites it: rejected |
| Failure risk | a crash leaves a stray ref and loose objects; a locked index is a hazard | none for the real repo | destroys history |
| Size | small | small | as now |

**Chosen: (b), plus one shortcut.** If no commit on any ref ever touched `system/staging`, `system/logs` or `system/branding`
(`git rev-list --all -n 1 -- <paths>` is empty), the bundle is `--all` exactly as before, so new vaults keep their full history. Only a vault whose
history holds those paths gets the snapshot.

## What the patch does (`backup.py`)

- `PRIVATE_PATHS`, `PRIVATE_SPECS` (`:(icase)` pathspecs), `EXCLUDE_SPECS` (`:(exclude,icase)`), `SAFE_GIT` (the `-c` flags), `SNAPSHOT_NOTE`, `BUNDLE_NOTE`.
- `make_bundle(dest)`: same signature and return (None when made, else why not). Fails closed: git missing, a failed git step, a timeout or an
  OS error give a string and no file at `dest`.
- `bundle_filtered(git, dest)`: the check, then `--all` or the snapshot. The check is `git rev-list --all --full-history -n 1 -- <icase paths>`:
  `--full-history` so a private file reachable only through a merge's second parent (`merge -s ours`, then the side branch deleted) is found, and
  `icase` so `System/Staging/...` (a commit made on Linux, or a case-insensitive volume) is found.
- The snapshot: a temporary index (`GIT_INDEX_FILE`, so the vault's own index is never touched) filled by `read-tree HEAD`; `ls-files` with the
  exclude pathspecs; `checkout-index` of those files into a temporary directory; then `git init`, same branch name, `add -A -f`, one commit,
  `git bundle create dest HEAD <branch>`. This keeps `export-ignore` files (unlike `git archive`) and tracked files the committed `.gitignore`
  would hide (`-f`). The temp git runs with `core.hooksPath=/dev/null`, `core.excludesFile=/dev/null`, no signing and a fixed identity, so none of
  the user's hooks or global settings run on it.
- `restore_plan(..., snapshot)`, `cmd_show`, `verify`: the snapshot is shown, not hidden. The manifest has `"git_note"`; `backup.py show` prints it;
  the restore plan says "git history: one snapshot commit, restored from the bundle"; the restore check state gets `"note"`, which Health shows
  through `doctor.backup_check` (an ordinary file, committed on the branch with its test).
- `run_git`: drops every `GIT_*` variable of the caller (a `GIT_DIR`, `GIT_INDEX_FILE` or `GIT_WORK_TREE` exported by a hook or wrapper would point git at the vault's own repository and change it) and sets only the temporary `GIT_INDEX_FILE`. `fail`: removes a half-made bundle. `make_zip`: the manifest gets `"git_note"`; when the bundle fails `"git"` holds the reason and there is no `vault.bundle`.

## What history is lost (snapshot case only)

All earlier commits: the bundle holds one commit, the latest tree minus the private paths (memory files, scripts, templates, `system/config/`).
Commits made later in the real repo are not in an earlier zip, as before. Uncommitted work is not in the bundle, as before. The real repo is
never changed. Size: smaller than `--all`.

## Known limit: a moved private file

The filter works on paths. A private file that was renamed to another path in the latest commit (for example `git mv system/staging/vip.json
notes-vip.json`) is not recognised and stays in the snapshot. Only the three folders are filtered. Tested as a known limit
(`test_a_moved_private_file_stays_in_the_snapshot`).

## Restore and the weekly check

- `restore_git(data)` does `git init` and `git fetch bundle +refs/heads/*:refs/heads/*`, then finds the branch from `HEAD` in `list-heads`. The snapshot
  bundle names `HEAD` and the branch, so it works unchanged and gives a repo with one commit (tested). The working files are not touched.
- `verify_bundle` (the weekly restore check, `deep_checks`) runs `git bundle verify` and `unbundle`: passes on a snapshot (tested).
- cx-setup's restore calls `backup.py restore`, so it follows the same path.

## Failure behaviour

Git missing: "git isn't installed", no bundle. Any git step failing, or `tar` failing: "git bundle failed: ...", the partial file removed, no
bundle. Manifest `"git"` holds the reason. The history check itself failing gives no bundle (never an unfiltered one). The vault's HEAD, refs and
index are read, never written (tested by comparing them before and after).

## How verified (patch applied in a throwaway worktree, never on the branch)

`dev/tests/test_bundle_privacy.py`, class `ExistingVault` (skipped unless `PRIVATE_PATHS` is in backup.py): old history holding a chat and
`vip.json` is absent from every blob and commit of the cloned bundle; a HEAD that still tracks them is filtered; a clean history keeps all commits;
HEAD, refs, status and index are unchanged; restore_git and verify_bundle read the snapshot; a failing git gives a zip with no `vault.bundle` and a
manifest reason; no git gives no bundle. Mutants: removing the `:(exclude)` pathspecs fails the HEAD-tracking test; forcing `--all` fails two tests.
16 tests pass patched; `test_backups` (21) and `dev/tools/check.py` pass patched. Revision 3 test: with `GIT_INDEX_FILE`, `GIT_DIR`, `GIT_DIR`+`GIT_WORK_TREE` or `GIT_OBJECT_DIRECTORY` exported at the vault's own repository, make_bundle leaves its index, config, HEAD, refs and status byte-identical; the commit-hook test uses a global `~/.gitconfig` (HOME). Mutants (each fails the privacy tests), now also no `GIT_*` stripping: no `--full-history`, no icase in the check, no icase in the exclude, no `core.hooksPath`, no `-f`. Removing only `core.excludesFile` is not caught, because `-f` already covers it (the flag is a second line of defence).

## Not changed

Old zips and their OneDrive copies keep whatever they held: they are Alan's to delete. creaite does not rewrite git history.
