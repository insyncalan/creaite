# Sprint polish: the apply defect and tonight's backlog (BL-114, BL-116 to BL-124)

Branch `sprint-polish`, worktree `../creaite-polish`, from `main` after v1.2.0 (`01542ab`). One sprint, built in order, because almost every item touches `dashboard.html`. BL-115 (the Settings page) is its own sprint, `sprint-settings` (`settings-page.md`), running alongside; this one **merges first**. Read BL-114 and BL-116 to BL-124 in `dev/BACKLOG.md` first. They hold Alan's decisions; where one says "to confirm", take its stated default and note it in BUILD.

## Items

Commit each separately, in this order.

### 1. Defect: a proposal already made blocks the apply (S)

**What happens:** two proposals that write the same change to one file (for example two cx-edit memory changes made from the same text). The first applies. The second finds the file already says what it proposes, fails `previous` (or "already exists"), and the whole apply stops.

**The fix so far** is in `dev/sprints/polish-defect.patch`, taken from an unfinished copy on `main`. Apply it with `git apply dev/sprints/polish-defect.patch`. It adds the following to `run_file_ops` in `tracker.py`:
- a `write` whose target already holds the proposed content is skipped;
- nothing is written, and there is nothing to undo.

**Still to do:**
- **The new test fails:** `test_write_already_made_does_not_block_apply` stages two proposals, but only one is staged (`1 != 2`). Find out why (`propose.py stage` may name both files the same, or merge identical proposals) and fix the test or the staging, whichever is wrong. Say which in BUILD.
- **Same check on the other file ops** (`append`, `edit`, `rename`, the memory changes and the register): a change that is already in place passes quietly, and a real conflict (the file changed to something else) still stops the apply with its message.
- **Duplicate permission rules:** the dev `.claude/settings.json` has `filechange.py *` and `chat_message_search` listed twice, after rules were added from the panel. Check whether `permissions.py apply` adds a rule that is already listed. If it does, make it a no-op that says so, with a test. Don't edit the dev settings file; Alan's copy stays as it is.

**Tests:** `test_propose.py` passes, plus one test for each other file op that is already in place, and the conflict cases still refused.

### 2. BL-118: staging commands delete their own draft input (S)

As BL-118 sets out. When it's done, the two interim `rm system/staging/drafts/…` rules come out of `.claude/settings.json` in the engine (the release's template). Alan's live vault gets them removed by `update.py` only if it already removes retired rules; otherwise note it for the release notes.

### 3. BL-121: Word drafts are approved without any sensitivity label (S)

As BL-121 sets out. This includes the settings migration in `update.py` (the setting goes from an existing vault's `settings.json`, logged).

### 4. BL-116 and BL-117: Current state on the project page (S)

One commit for both, as BL-117 says (same function). Remove Add notes, and keep the text's width when the second pane is empty.

### 5. BL-119: Calendar Import, one Process button (S)

### 6. BL-120: ask creaite keeps your place when a live update arrives (S)

Include the Jump to latest button in all seven themes, checked for contrast.

### 7. BL-114: Work shows only the controls for the layout in use (S)

Finish it before BL-122, so the selection controls are added to the toolbar as it ends up.

### 8. BL-122, BL-123, BL-124: select, edit in the table, edit several at once (M, M–L, M)

Three commits, in that order, as the backlog sets out. One BRD requirement covers all three.

**Review's bulk rule is unchanged:** selecting several items in Review never approves minutes, reports, health changes, new decisions, a decision recorded or withdrawn, or new risks in bulk.

## Boundaries

- **`sprint-settings` runs alongside and owns the Settings view:** `renderSettings` and its four wrappers, the Settings cards and the address handling for `#settings`. Don't edit those. BL-121 removes the Word label setting: take it out of the settings defaults and the migration, and if it has a control on the Settings page, remove just that control and note it in BUILD so `sprint-settings` drops it too.
- **Shared files** (`dashboard.html`, `help.md`, `dev/dashboard-spec.md`, `build_dashboard.py`): put new code in marked sections (`/* ===== <BL-number> (sprint-polish) ===== */`) and don't reformat unrelated lines.
- **Engine changes ship in a release:** items 1 to 3 are `tracker.py`, `propose.py`, `permissions.py`, `sweep.py`, `review.py`, `live_server.py` and `update.py`. Add a line for each to `dev/release-notes/1.3.0.md` (create it; don't change `VERSION`).
- **Don't touch `dev/BACKLOG.md` or `dev/BRD.md`;** they are updated at merge. Write the FR text you'd add in BUILD.
- **Help:** update `help.md`, then run `python3 dev/tools/build_guides.py`.
- **Tests start from your own settings:** the repo's `system/config/settings.json` has Alan's uncommitted dev values, which change some outcomes. Run tests in the worktree, which has the committed copy.
- **Stop a test run by its process tree, never with `pkill` by name** (Sprint 5's lesson).
- **Development guard:** sample data only; test with temporary vaults.

## Done when

- **Tests:** as listed per item, plus each item's "Touches" tests in the backlog.
- **The full suite passes once** on the final branch: `python3 dev/tools/run_tests.py -j 4`.
- **Docs:** `dev/dashboard-spec.md`, Help and the guides, a "Sprint polish" section in `dev/BUILD.md`, and the 1.3.0 notes.
- **Commits:** each item committed separately on `sprint-polish`, with the attribution lines from the session's instructions. Never push or merge into `main`.
