# Manual check: "Untrack private files in an existing vault" (cx-setup, step 6)

Live vault only (Alan's own laptop). It cannot be scripted. About five minutes. Do it in Terminal in the vault folder.

1. **Before.** Run `git ls-files system/staging system/logs system/branding | head`. If it prints nothing, this vault is already clean: stop, the check passes. If it prints files, carry on.
2. Run `git status --short | head` and note it. Run `git log --oneline | wc -l` and note the number of commits.
3. In Claude Code say "setup". When it reaches Git, it should offer "Untrack private files". It must show the `.gitignore` lines to add and say that earlier backup zips still hold the files. It must ask for your yes and make a fresh backup first. Say yes.
4. **After.** Run `git ls-files system/staging system/logs system/branding`: it should print nothing.
5. Run `git status --short`: it should show nothing about `system/staging`, `system/logs` or `system/branding` (the files are still on disk, so check `ls system/staging` still lists them).
6. Run `git log --oneline | wc -l`: one more commit than in step 2 ("Stop tracking staging"), none lost.
7. Say "back up now" (or run `system/scripts/run backup.py check`): the backup still works and the check says it checks out.
8. Confirm the wording: the message told you old zips (and their OneDrive copies) still hold the files and are yours to delete.
