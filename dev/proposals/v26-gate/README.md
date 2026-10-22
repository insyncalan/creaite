# v2.6 gate: safe_path refuses a mid-resolve OSError in the relative path's words

**Guarded file:** `system/scripts/tracker.py`. Diff: `tracker-resolve-oserror.diff` (`git apply --check` and `git apply -R --check`
pass on v26-gate-b; it does not touch the E1 diff's hunks, so the E1 tests' `patch -R` still works).

**Why.** CI run 39759059174, Python 3.9 shard: `test_minutes_by_others_filing.py`, the flip test, found
`OSError [Errno 22] Invalid argument: '/tmp/.../inbox/m.txt'` from `_op_remove`. CPython 3.9.25's `Path.resolve()` calls its
backported `realpath`, which lstats a link and then readlinks it without catching an error: when the link is swapped for a file
in between, it raises EINVAL with the full path (3.10 and later keep that part as it is). `safe_path` let it out.

**The change.** `safe_path`'s resolve and `paths.rel` move into `_safe_resolved`, which turns that OSError into
`Invalid("<purpose>: <rel> changed while it was being checked (OSError)")` (a helper keeps safe_path under the complexity limit).
The other route, `stash` -> `paths.rel`, is fixed in `paths.py` (not guarded, committed on this branch): `paths._resolved` keeps
the name and resolves the folder, as later Pythons do.

**Proved.** With an injected EINVAL from `realpath` on `inbox/m.txt`: without the diff, `_op_remove` raises the OSError with the
absolute path; with it, `Invalid: remove: inbox/m.txt changed while it was being checked (OSError)`. With the diff applied:
`test_minutes_by_others_filing.py` 54 OK (3.14; Probes on 3.9.6), `test_tracker.py` OK, `check.py` OK.
