# Sprint drafts-writing: agenda and invite, follow-up and chase emails, one set of facts in many forms (BL-223, BL-224, BL-227)

> **Update (12-10-2026): for v1.7.0.**
> - **Base:** branched from `sprint-drafts-fields` (`a344a33`), because it isn't on main yet; it already holds insight, BL-232 and the drafts scaffold.
> - **Main:** merge main in (never rebase) when asked. v1.7.0 work stays off main until `release-1.6.1` is cut.
> - **`check.py` holds you strictly:** no figure may rise, so split as you go.
> - **GitHub Actions:** none of your runs until told. Run test files locally, at most `-j 2`; the Chrome cap (BL-246) shares 3 Chrome tests across the machine.
> - **Ignore** the "For v1.6.0" line below.

Branch `sprint-drafts-writing`, worktree `../creaite-drafts-writing`. Made from `main` **after `sprint-insight` and `sprint-drafts-fields` have merged**, because BL-207's Generate work and BL-209 touch the same places. Runs beside `sprint-drafts-extraction`. **For v1.6.0.** It owns:
- `prep_page.py` and the Prep popup;
- `draftEmail`;
- Generate's dialog and `/api/current/generate`.

## Order: one commit each

1. **BL-223:** draft an agenda and POAD invite text from the Prep page.
2. **BL-224:** follow-up and chase emails, as new modes of the existing Draft email builder.
   - **The chase mode** (Alan, 11-10-2026) works from overdue items owned by other people, plus an "I sent it" log, `system/staging/chases.json` (references only, never message text).
   - It moves onto BL-125's "waiting on" when that is built.
   - Nothing is ever sent, and no Outlook draft is made.
3. **BL-227:** one set of facts, many forms (a steering note, a three-line update, and so on).
4. **Docs.**

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
