# v2.6.1: the two LOW notes of the 2.6.0 re-cut security review (issue #275), and the dead `rel`

**Guarded file:** `system/scripts/tracker.py`. Diff: `tracker-resolve-einval.diff` (one hunk; `git apply --check` passes on
origin/v260-release 93d0dfcd). Everything else is committed on branch `v261-low-notes`: `system/scripts/paths.py` (not guarded) and
`dev/tests/test_paths_resolved_low_notes.py`.

## L1 - `paths._resolved` caught any OSError (committed, paths.py)

The 2.6.0 fallback (resolve the folder, keep the name) was for one case: CPython 3.9.25's realpath raising EINVAL when a link at the
last part is swapped for a file between its lstat and its readlink. It caught every OSError, and for a name of `..` it would have
returned an un-normalised path (`.../real/..`). Now it falls back **only for errno.EINVAL and only when the last part is a real name**
(not `.`, `..` or empty). Any other OSError, and that case, is raised as it was before 2.6.0. Both changes were suggested by the review;
doing both is the narrowest. `tracker._safe_resolved` already turns the OSError into "<rel> changed while it was being checked".

## L2 - a NUL byte in a path (proposal, tracker.py)

Before 2.6.0 a NUL byte (`inbox/a\0b`) escaped `safe_path` as a bare `ValueError`; 2.6.0 turned it into
`Invalid("...path is outside the vault ('inbox/a\x00b')")`, which refuses (good) with the wrong reason. **Decision: refuse it
explicitly, as `Invalid("<purpose>: path contains a NUL character")`, checked first in `_safe_resolved`.** It still refuses (an
`Invalid`, the caller's existing handling); the message is true and does not echo the path. Other `ValueError`s keep the "outside the
vault" wording. `paths.rel`/`paths._resolved` are unchanged for NUL: they still raise `ValueError`, and no caller depends on them for
confinement (review: every confinement decision resolves again in `safe_path` or `reach`).

## INFO - dead `def rel` (committed, paths.py)

The older `def rel` at paths.py:90 is shadowed by the one at line 220 (no module-level code calls `rel` between them; `grep` finds no
other definition or alias). Removed; the test asserts one `def rel(`.

## Proved

`dev/tests/test_paths_resolved_low_notes.py` (quick tier, 9 tests). The race is forced by a stand-in for `Path.resolve` raising
`OSError(EINVAL)`; nothing races. On 93d0dfcd 6 of 9 fail (EINVAL on `..`, four other errnos, the second `def rel`); with the change all
pass. The tracker half applies the diff to a throwaway vault's `tracker.py` (or accepts it already applied) and checks the NUL message
for three NUL paths and that the raced `rel` is still refused in relative words. Run with Python 3.14.7 and 3.9.6.
