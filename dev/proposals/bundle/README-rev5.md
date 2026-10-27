# Revision 5 of the backup bundle patch (incremental)

`backup-bundle-rev5.diff` (sha256 `b3fc5d69ece73cf7b67e9d4a416e48776a4cd4c96713c64ff73631b7d6efd05d`, 42 lines) applies on top of rev 4 (`backup-bundle.diff`, c366014b, approved and pinned, unchanged). Applied on the 2.6.9 file (`git show 0b637e92:system/scripts/backup.py`, which already holds G1, G2 and rev 4) or on v2.6.8's file after rev 4, it gives the same backup.py, sha256 `72c3fd4660a42c6f533e6794291ce3558859254e4aaad49701f1197a4fc0c4d2`.

## Why

CI diagnostic run 40404813380: in the snapshot path, cleaning up the temporary directory failed with `OSError(39, 'Directory not empty')` at `snap/.git`. The temporary repository's background `git gc --auto` / maintenance (detached after the snapshot commit once there are many loose objects, as in a big vault) was still writing while Python deleted the folder. `make_bundle` turned that into "git bundle failed: OSError": no bundle that day, although the bundle had been made correctly.

## What changes (three places in backup.py)

1. `SAFE_GIT` also sets `gc.auto=0`, `maintenance.auto=false`, `gc.autoDetach=false`, and now every step on the temporary repository runs with it (`init`, `checkout` and `bundle create` did not before): `run_git(git, snap, *SAFE_GIT, *step)`.
2. `tempfile.TemporaryDirectory` becomes `tempfile.mkdtemp` with `try/finally: shutil.rmtree(work, ignore_errors=True)` (Python 3.9 floor: no `ignore_cleanup_errors`). A folder that will not delete never discards a good bundle. Any failure to BUILD the bundle still returns the failure string with no `vault.bundle`.
3. Nothing else: fail closed, the history check and the clean-history path are unchanged.

## Tests (dev/tests/test_bundle_privacy.py; skipped unless backup.py has `gc.auto=0`)

- `test_snapshot_survives_background_gc`: 1,500 small files plus 12 incompressible 1 MB files, a global `~/.gitconfig` with `[gc] auto = 1` and `[maintenance] strategy = gc` so git starts a background gc after the snapshot commit; the bundle is made and no temporary folder is left behind. On rev 4 it fails 19 times in 20 (`OSError`); with rev 5 it passes 20 of 20 (git 2.56, macOS).
- `test_a_folder_that_will_not_delete_does_not_discard_the_bundle`: `shutil.rmtree` raises for the work folder; the bundle is still made.
- Mutants: removing the gc flags fails the first (the leftover-folder check; 5 of 5), removing `ignore_errors` fails the second.
- With rev 4 + rev 5 applied: the whole privacy file (20 tests), `test_backups` (21) and `check.py` pass.

## Not changed

Rev 4's bytes. Old zips are unaffected.
