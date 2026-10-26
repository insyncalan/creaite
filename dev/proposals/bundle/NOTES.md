# Notes: bundle privacy

- **`update.py` does NOT replace an existing vault's `.gitignore`.** `STARTING_FILES` (which maps `.gitignore` to `system/templates/vault-gitignore`)
  is used by `new-vault` only. An update replaces the engine (`system/templates/vault-gitignore` itself changes), but a live vault keeps its old
  `.gitignore` until cx-setup's "Untrack private files in an existing vault" step (Alan's yes) adds the lines. So the template fix protects new vaults
  only; existing vaults need that step, and the backup.py patch for their old history.
- Earlier zips and their OneDrive copies still hold chats, images, `vip.json` and the raw calendar where the history did: Alan's to delete.
- Guarded: the patch (`backup-bundle.diff`) is a proposal; `backup.py` is unchanged on this branch.
