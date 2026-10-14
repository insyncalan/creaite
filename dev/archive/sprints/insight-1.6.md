# Sprint insight: ⌘K that does things, Close the day, evidence on hover, Review focus mode, and the meeting hub (BL-205 to BL-209)

Branch `sprint-insight`, worktree `../creaite-insight`, from `main`. **For v1.6.0**; `VERSION` changes only at the release. Read BL-205 to BL-209 in `dev/BACKLOG.md` first. They hold Alan's requests (BL-205 and BL-206 are his high priority). Where an item says "to settle in the build", take its **recommended** option, record it in BUILD and carry on.

**Two sprints are finishing beside this one:**
- `sprint-review-work`: BL-200 (Review's project changes), BL-198 (the peek follows a click) and BL-197 (the right-click menu, with per-kind actions);
- `sprint-chat-text`: ask creaite's input, refusals and the markdown renderer.

The scrum master merges them into `main` soon and tells you. **Then run `git merge main` before items 3 to 5**: BL-205 reuses BL-197's per-kind actions, and BL-208 changes Review, which BL-200 changed.

## Order: one commit per item (or stage), each in a marked block (`/* ===== BL-2xx (sprint-insight) ===== */`)

1. **BL-207, evidence on hover:** start with the executive Current state, as the item recommends. Fact IDs come from `status_facts.py`; a sentence edited by hand loses its source mark until it is re-checked, and says so.
2. **BL-209, the meeting hub:** one page per meeting, from invite to follow-up, as it sets out.
3. **BL-205, one ⌘K that does things** (after `main` is brought in):
   - the verb set in plain code over `parseWhen` and BL-197's actions;
   - the before → after preview, and what else the change touches;
   - Enter always **stages**, never applies at once;
   - free-form requests are offered to ask creaite.
4. **BL-206, Close the day:**
   - the card and its Today button, plus the ⌘K entry;
   - the nudge **off** by default; "tomorrow" is the next **working** day;
   - only a small "closed" record is written, never anything in the tracker.
5. **BL-208, Review one proposal at a time:**
   - the focus mode;
   - until BL-60's source positions exist, the source note stands in for the transcript line;
   - shaky fields marked;
   - routine items sampled, as it sets out.
6. **Docs:** Help and the guides, the spec, a BUILD "Sprint insight" section with the FR text, and lines in `dev/release-notes/1.6.0.md`.

## Rules

- **The record's rules stand:**
  - approval before writes, and `tracker.py` the only writer;
  - every change from ⌘K or Review goes through the existing staging paths;
  - BL-189's peek staging rule holds;
  - bulk approval's exclusions are unchanged;
  - client-safe and confidential rules are unchanged, and evidence panels are internal only;
  - no Microsoft 365 action, nothing sent.
- **No schema change.** If one seems needed, stop that part and report it.
- **Look at it** in the real browser (`dev/tests/live_browser.py`, `dev/tools/cdp.py`) at 1400px and 1100px, chat open and closed, light and dark, in two themes. Keep the screenshots.
- **Tests:**
  - each item's "Touches" tests;
  - then **every** test file that touches the areas you changed (Review, ⌘K, Today, the project page, prep, `status_facts`), not a sample.

  One pass is enough; a file that fails under load and passes alone counts. Tests also run on GitHub's Linux runner: wait for conditions. Stop runs by their own process tree only; never `pkill` by name.
- **The usual edit rule:** don't edit `dev/BACKLOG.md`, `dev/BRD.md` or `dev/archive/sprints/STATUS.md`. Never push or merge.
