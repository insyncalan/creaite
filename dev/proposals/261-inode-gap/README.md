# 2.6.1 proposal: the remove holds the file open through the inode check

**Guarded file:** `system/scripts/tracker.py`. Diff: `tracker-inode.py.diff` (git format, `git apply` or `patch -p1`).
`git apply --check` and `git apply -R --check` pass on `origin/v260-release` (93d0dfcd).

## The gap

Found by the gate-B agent; real on Linux (ext4, tmpfs), not on APFS. `_remove_checked` (#232 E1) reads the staged inbox copy of
someone else's minutes with `_read_regular`, which **closes** the file, then `_unlink_same` moves the name to a private name and
deletes it only if its `(st_dev, st_ino)` is the one that was read. Between the close and the move, a local process can unlink the
staged file and write a different file at the same name. With nothing holding the old inode, Linux gives its number straight to
the new file, so the identity check matches and the **different file is deleted** (the apply succeeds). APFS does not reuse a
number so soon, which is why macOS never showed it; the E1 tests needed `HOLD` to keep their own swaps honest on Linux CI.

## The fix

`_read_regular` takes an optional list `hold`: once the file is known to be regular it adds a `dup` of its descriptor.
`_remove_checked` passes one and closes what it holds in its `finally`, after `_unlink_same`. While a descriptor is open the inode
stays allocated even after its name is unlinked, so no other file can have its number, and the existing comparison is again a
comparison with the very file that was read. Nothing else changes: the same refusal messages, the put-back, the private name,
and every E1 mutation string still matches once. Other callers of `_read_regular` are unchanged. Complexity stays within
`check.py`'s limits (`check: OK`).

## Apply order

1. #232 E1 (`dev/proposals/intake-232/E1-tracker.rebased-on-280.diff`) - already in 2.6.0.
2. `dev/proposals/v26-gate/tracker-resolve-oserror.diff` - already on `v260-release`.
3. This diff. (Also checked on `origin/v26-gate-fix` with step 2 applied: applies cleanly.)

The diff touches E1's hunks, so `test_minutes_by_others_filing.py`'s scratch now reverses this diff before it reverses E1 for its
"defect today" tests (`INODE_DIFF`, `INODE_MARKER = "hold=held"`); that change is in this branch and works with or without the
diff in the repo.

## Tests

`dev/tests/test_tracker_inode_hold.py` (no skip needed: like the E1 tests it patches a scratch copy, applying the diff when the
repo lacks it and reversing it for the defect class). The swap is made in the `stash` hook (after the read and check, before the
move) and keeps **no** descriptor.

- `test_a_different_file_given_the_freed_inode_number_is_not_deleted`: with a faithful fake of Linux's rule (`os.stat` of the
  moved-aside name reports the staged inode number only while no descriptor in the process holds that inode), the apply stops
  with "a different file was put there; it is left alone" and rolls back. Proves the fix on any platform.
- `DefectWithoutHold`: the same, diff off: the different file is deleted, RC 0 (the gap, shown on macOS too).
- `test_with_the_real_file_system_a_different_file_is_not_deleted`: no fake; red without the fix on Linux CI, green on APFS either way.
- Two leak tests: the held descriptor is closed after a refusal and after a normal remove (red if the close loop is removed).

Results (macOS, Python 3.14 and 3.9.6): diff applied - `test_tracker_inode_hold` 5 OK, `test_minutes_by_others_filing` 54 OK,
`test_tracker` 23 OK, `check.py` OK; `E1_TRACKER_UNPATCHED=1 ... DefectToday` OK; diff reversed - all of the above OK.

## Residual risks

- A file system whose inode numbers are not stable or not unique (some SMB/NFS mounts, FUSE) could still mis-identify a file;
  `inbox/` is in the local vault, so this is outside the supported set-up.
- The held descriptor is a read-only `dup`; a process that already had the staged file open before staging could still edit it in
  place, which the checksum (read before the hold) does not see after the read. That is unchanged from E1 and not this gap.
- Windows is untested (no `dir_fd` rename there); unchanged.
