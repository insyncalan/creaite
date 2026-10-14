# Sprint ask-creaite-access: risk tiers on the approval card (BL-194)

Branch `sprint-ask-creaite-access`, worktree `../creaite-ask-access`, from `main` after `sprint-polish-themes` has merged (the card uses its warning and danger tokens). For v1.5.1. Read **BL-194** in `dev/BACKLOG.md` (narrowed by Alan, 11-10-2026) and **BL-141** in `dev/BUILD.md` › Sprint admin, with its design rule, before anything else.

## The rule above all others

BL-141's design rule stands: **enforcement lives in code the model cannot change.** This sprint changes only how the card *shows* changes and how they are *logged*. It must not:
- widen what ask creaite can reach;
- change the never list, the guard hook or the one-time approvals;
- weaken `permissions.settings_problem`.

If anything here seems to need one of those, stop that part and report it.

## Build, one commit each, in marked blocks (`/* ===== BL-194 (sprint-ask-creaite-access) ===== */`)

1. **The detector and the tier:** `reach.permission_change(old_text, new_text)`, and a tier (Sensitive or High-risk) for every change on the card.
2. **The card:** `changesCardHtml()` shows the two tiers (words and an icon on the theme's warning and danger bands) and keeps BL-141's single Approve and Decline. It adds the rollback line, with Copy, under each High-risk item.
3. **The log:** the tier is recorded in `files-log.jsonl` and shown in Activity › What ask creaite changed.
4. **Docs:** Help (ask creaite's permission model), the spec, BUILD ("Sprint ask-creaite-access" with the FR text), and a line in `dev/release-notes/1.5.1.md`.

## Rules

- **Look at it:** in the real browser, the card with one item of each tier, in all nine themes, light and dark. Keep the screenshots.
- **Tests:**
  - every item in BL-194's "Touches";
  - `test_admin_card`, `test_reach`, `test_permissions`, `test_permission_panel`, `test_permission_file`, `test_open_write` and `test_file_access`, all unchanged and passing.

  One pass is enough. Tests also run on GitHub's Linux runner. Stop runs by their own process tree only.
- **The usual edit rule:** don't edit `dev/BACKLOG.md`, `dev/BRD.md` or `dev/sprints/STATUS.md`. Never push or merge. No schema change.
