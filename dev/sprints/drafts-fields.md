# Sprint drafts-fields: the AI-draft scaffold and per-field drafts (BL-219, BL-225, BL-222, BL-226)

Branch `sprint-drafts-fields`, worktree `../creaite-drafts-fields`, from `main`. **For v1.6.0** (Alan: all ten AI-draft items in 1.6.0). It starts now, beside `sprint-insight` and `sprint-ui-audit`. It owns the peek's Details draft buttons, the live server's draft routes and the new prompt templates. Keep to marked blocks (`/* ===== BL-2xx (sprint-drafts-fields) ===== */`). It overlaps `sprint-ui-audit` lightly (the snack, field names).

## Order: one commit each

1. **The shared scaffold**, used by all three AI-draft sprints:
   - one run-engine route kind for drafts;
   - the `drafting.<feature>` switches in Settings (through BL-115's `SETSECTIONS`);
   - a prompt-template folder convention;
   - one Draft button component;
   - the "Drafted from" mark Generate already uses;
   - the counts helper writing `system/staging/draft-stats.json`.
2. **BL-219:** draft the latest update, for one item and in bulk for stale items.
3. **BL-225:** draft client wording.
4. **BL-222:** draft decision reasoning and risk response.
5. **BL-226:** draft the reason for a health or forecast change.
6. **Docs.**

## Shared rules for this sprint

- **Read first:** "AI drafts: rules shared by BL-218 to BL-227" in `dev/BACKLOG.md`. A draft is a suggestion, never a write. It works in plain code first and uses a model only for wording and judgement, through the existing run engine (`kind="generate"`). Evidence goes on every draft (BL-207). Client-safe and confidential rules hold, as do approval before writes and bulk approval's exclusions.
- **Counting (Alan, 11-10-2026):** each draft kind is counted in `system/staging/draft-stats.json`: per feature, how many were offered, used, edited and rejected. Counts only, never text. `sprint-drafts-fields` builds the helper; the other two sprints use it.
- **No schema change.** If one seems needed, stop that part and report it.
- **Look at it** in the real browser (`dev/tests/live_browser.py`, `dev/tools/cdp.py`) at 1400px and 1100px, light and dark, in two themes. Keep the screenshots.
- **Tests:**
  - each item's "Touches" tests, with a stand-in model reply (never a real model call in tests);
  - then **every** test file touching the areas changed, not a sample.

  One pass is enough; a file that fails under load and passes alone counts. Tests also run on GitHub's Linux runner. Stop runs by their own process tree only; never `pkill` by name.
- **The usual edit rule:** don't edit `dev/BACKLOG.md`, `dev/BRD.md` or `dev/sprints/STATUS.md`. Write the FR text in BUILD, add lines to `dev/release-notes/1.6.0.md`, update Help and regenerate the guides. Don't change VERSION. Never push or merge.
