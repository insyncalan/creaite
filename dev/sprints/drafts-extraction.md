# Sprint drafts-extraction: repeats, "probably done", sharpen on capture, and Quality (BL-221, BL-218, BL-220, BL-233)

> **Update (12-10-2026): for v1.7.0.**
> - **Base:** branched from `sprint-drafts-fields` (`a344a33`), because it isn't on main yet; it already holds insight, BL-232 and the drafts scaffold.
> - **Main:** merge main in (never rebase) when asked. v1.7.0 work stays off main until `release-1.6.1` is cut.
> - **`check.py` holds you strictly:** no figure may rise, so split as you go.
> - **GitHub Actions:** none of your runs until told. Run test files locally, at most `-j 2`; the Chrome cap (BL-246) shares 3 Chrome tests across the machine.
> - **Ignore** the "For v1.6.0" line below.

Branch `sprint-drafts-extraction`, worktree `../creaite-drafts-extraction`. Made from `main` **after `sprint-insight`, `sprint-drafts-fields` and the `fix-as-proposed` branch (BL-232) have merged**: it needs BL-205 (⌘K), BL-208's inferred fields and the drafts scaffold, and insight changes the same Review and cx-minutes code. **For v1.6.0.** It owns:
- `minutes.py`, `sweep.py` and `review.py`'s update cards;
- the cx-minutes and cx-sweep skills;
- `dev/staging-format.md`.

## Order: one commit each

1. **BL-221:** "Looks like": repeat proposals, merged as an update.
2. **BL-218:** "Probably done": the sweep and minutes propose closing an item, with evidence.
3. **BL-220:** sharpen on capture: chips and Sharpen for vague actions, the Review-side vague mark, and ⌘K chips.
4. **BL-233: Quality** (Alan split it from BL-182, 11-10-2026), last.
   - A read-only `system/scripts/quality.py` plus an Activity › Quality tab.
   - It reads applied and pending proposals, `rejected` (BL-133's reasons), BL-232's `as_proposed`, and `system/staging/draft-stats.json` (from drafts-fields).
   - It shows approved, edited and rejected counts by source and item type, the fields changed most, and each AI-draft feature's use and edit rate.
   - **Every figure shows its count and its denominator,** never a bare percentage, and nothing under 10 is rated.
   - It counts extraction and drafts only, never a person. No report or export reads it.
5. **Docs.**

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
