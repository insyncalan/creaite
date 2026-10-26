# Notes: bundle privacy

- **`update.py` does NOT replace an existing vault's `.gitignore`.** `STARTING_FILES` (which maps `.gitignore` to `system/templates/vault-gitignore`)
  is used by `new-vault` only. An update replaces the engine (`system/templates/vault-gitignore` itself changes), but a live vault keeps its old
  `.gitignore` until cx-setup's "Untrack private files in an existing vault" step (Alan's yes) adds the lines. So the template fix protects new vaults
  only; existing vaults need that step, and the backup.py patch for their old history.
- Earlier zips and their OneDrive copies still hold chats, images, `vip.json` and the raw calendar where the history did: Alan's to delete.
- Guarded: the patch (`backup-bundle.diff`) is a proposal; `backup.py` is unchanged on this branch.

## Known limit and release-notes line

- A path filter cannot follow a private file that was renamed to another path. Only `system/staging`, `system/logs` and `system/branding` are filtered.
- **Release-notes line (plain words):** "Your daily backup no longer carries ask creaite chats, their pictures or your VIP list in its history copy. If your vault's history already held them, the history copy in new backups is one snapshot of your latest state instead of every earlier version. Older backup zips are unchanged: delete them if you want those files gone."
- Health shows "git history in the zip: one snapshot commit" under the weekly restore check when the newest zip is a snapshot.
