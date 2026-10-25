# 369b: raw calendar draft and the backups

Fixed unguarded in sweep.py (branch v268-draft): the calendar draft `system/staging/drafts/calendar.json` is removed whatever
happens to the save (saved, refused, unreadable, error), and a leftover one is removed when `calendar` or `calendar-window` starts.

`backup-draft.diff` (guarded file, apply by the guarded chain only): the daily zip no longer takes `system/staging/drafts/calendar*`.
It is a second line of defence for the moments a draft legitimately exists (while the reply is being written). `git apply --check` is clean on origin/main.

Other staging files: the zip still takes the rest of `system/staging/` (proposals, other drafts such as sweep or minutes inputs).
Those hold extracted items, not the raw invite; this fix does not change them.

Zips already made: any daily zip made after a refused calendar reply may hold the raw draft, locally in `system/backups/` and in
`_Portfolio/99 System/creaite backups`. creaite cannot change a closed zip. Alan should delete the zips made since the calendar
reply feature began (they are kept 30 days, then weekly, then monthly), in both folders, once a clean zip for today exists, and
check the OneDrive copy has no older version. Nothing is implemented for this.
