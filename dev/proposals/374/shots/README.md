# #374 sign-off screenshots (fictional data only)

- activity-changed-file-900.png: Activity, "What ask creaite changed", flipped build (FINDER_REVEAL on): a changed file shows its plain name and "in <project full name>", with Show in Finder and Undo. Check: no path, button present; in the app, Show in Finder selects the file itself (Finder highlights it in its folder), not just the folder.
- activity-changed-file-before-900.png: the same row before #374 (the old build): a full path in monospace, no Show in Finder. For comparison.
- activity-move-900.png: a moved file: "Old name in <project> → New name in <project>", with Show in Finder. Check: both ends are plain names; the button selects the new file.
- activity-gone-file-900.png: after Show in Finder on a file that no longer exists (server run with CREAITE_NO_LAUNCH=1): the message "That file isn't there any more." Check: wording, no path, nothing else happens.
- activity-outside-allowlist-900.png: a settings file (no Show in Finder) and a file directly in Intake (now has Show in Finder: the file itself is checked). Check: no button on the settings row, a button on the Intake row.
- activity-deleted-row-900.png: a Deleted row: plain name and project, Undo only, no Show in Finder (nothing is there to show).
- project-settings-folder-row-900.png and -1400.png: Project settings, Folder row for a OneDrive-style projects root: the real location in the ~ form (fictional OneDrive-TestCo path), with Open folder. Check: starts with ~/, no home folder name, fits at both widths. Retaken from the 2.6.10 build, where #385's Folder row (the same ~ location, wrapped on two lines at 900 px) also shows an "Its own folder" row beneath.
- files-tooltips-900.png: Files tree: the Portfolio entry's tooltip reads "Portfolio" (headless Chrome draws no native tooltip, so the label is drawn from the entry's real title text). Intake has no tooltip at all (no title attribute), as found earlier.

Taken from the flipped build with headless Chrome (CDP, fictional vault). activity-changed-file-before-900.png (old behaviour) and files-tooltips-900.png are the earlier shots, kept as they were. What Alan should check on the real Mac: Show in Finder selects the file itself.

## Known limit (Banner's LOW on the reveal fix, logged, no change)

A mapped project's archive slot is covered only for the `99 Archive` folder. An older `_Archive` or `zz Archive` folder inside a mapped project is not covered by that slot (Banner's LOW; not checked further, no change made).
