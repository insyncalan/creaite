# v26-line: merge conflicts

Base: `origin/v253-release` (23a9db25). Merge order: v26-settings-line-2, v26-people-m2-m3, v26-minutes-view-v2,
v26-track-from-review, p260-r-fix, v247-follow-fix.

## Merge 1: origin/v26-settings-line-2 (e96a9594) — IN PROGRESS, NOT COMMITTED

Base side (v2.5.3) carries #252 (`_Archive` renamed `99 Archive`) and #238 `usage_reviews.py`; the settings line
carries the Settings tabs, the People page (#248) and the one-page project settings (#247).

| File | Resolution | Why |
|------|-----------|-----|
| `system/scripts/settings_catalogue.py` | theirs | theirs is a superset: adds the `vip.notify` row (#246) above the #97 quiet-hours rows both sides share |
| `system/scripts/vip_schedule.py` (add/add) | theirs | only the comment's quote style differs |
| `dev/tests/test_tracker.py` | ours | keeps `usage_reviews.py` (#238 delta) in the test vault's script list; theirs predates it |
| `system/templates/dashboard/src/settings.js` | theirs, `_Archive` -> `99 Archive` in the comment | the settings line removed `projArchiveHtml` (Archive moved to the project settings page, #247); #252's folder name kept |
| `system/templates/help.md` | theirs, plus ours' **Health** and **Archiving** lines; `_Archive` -> `99 Archive` | theirs restructured the Settings tabs; ours added the sweep-lock line and the #252 archive wording. Judgment call: line-level union |
| `system/templates/dashboard.html` | theirs, then rebuilt (globals, split build, guides) | generated |
| `dev/tests/snapshots/settings-advanced.html`, `settings-essentials.html` | theirs, to be regenerated after assembly | generated |
| `system/creaite-rules.md` | **unresolved**: guarded, and the session is not permitted to write it | see below |

### creaite-rules.md (blocks the merge commit)

The settings line edited the rules file directly (cc7c24e1). Two Folder-map rows conflict with #252/#238 on the base.
The resolved text is ours (v2.5.3) plus the settings line's wording changes, made by `git merge-file` on scratch copies
and checked. To finish merge 1:

    git checkout --ours system/creaite-rules.md
    git apply dev/proposals/v26-line/merge1-rules-resolution.diff
    git add system/creaite-rules.md dev/proposals/v26-line
    git commit --no-edit

The diff applies to v2.5.3's file (HEAD:system/creaite-rules.md); verified with `patch` against that version. No
later branch in the order touches the rules file again.
