# Design brief: links and labels (BL-125 stages B and C)

**Status:** design brief, not scheduled; stage A (promises) is in v1.9.0 and goes first, as it shares the same hand-offs (the sweep, cx-minutes and Review). B and C can follow in either order. Mockup: `dev/mockups/links-labels-mockup.html` (open it from the file system; fictional sample-vault items, today 12-10-2026). Not to be confused with `links.md` (BL-190, every count opens Work). When built: branches `sprint-links-deps` (B) and `sprint-labels` (C), each from the tip of `main`, with the UX baseline (BL-157) checked before it is called done. The tables, Excel sheets and validation exist already (FR-101); no schema change is expected.

## Goal

**B:** a dependency can be attached to actions, risks and issues, in this project or another, as well as to a milestone, and the link warns as a milestone link does. **C:** labels on items and people, managed in Settings, used in Work, and checked on every route that carries an item out, with Claude's sensitivity read on top of a deterministic floor.

## The screens

**B. Links**
1. **Attach to…** in the item panel: a **Blocks** field with chips (project code, ◆ for a milestone, × to remove), a picker that searches actions, risks and milestones in any project, up to three suggestion chips with a reason ("same workstream", "shares 'cut-over'", "Falcon named in the text") and **None needed**. A date warning when the dependency is due after something it blocks ("Due 19-12-2026, after Cut-over (22-11-2026), which it blocks").
2. **Where links show:** in Work, each target row says "waiting on TID-R-003", with an at-risk marker when the date clashes; the project page's Dependencies card lists open dependencies by what they block, showing both projects for a cross-project one; the milestone row says what it is waiting on.
3. **Suggestions in Review:** a proposed dependency carries suggested links, each with **Accept** or **Decline**; nothing is attached until accepted; a declined one isn't raised again unless the text changes.

**C. Labels**
4. **Settings › Labels:** the list (Sensitive built in; Legal review; Client principal for people) with behaviour and use counts; add or edit with name, colour, note and behaviour (warn, or warn and exclude from client reports); remove, staged and undoable.
5. **In Work:** label chips on rows (and the owner's people label), a filter with "is" and "is not", bulk add or remove on ticked rows, and the double-catch notice when an item becomes both Sensitive and client-visible.
6. **Before sharing:** one card before any output that includes labelled items: labelled items, then items the sensitivity read thinks are sensitive (each with its reason and **Label it Sensitive**); Include or Exclude per item, Sensitive defaulting to Exclude; the choices logged against the output; a line that the floor (labels, people labels, word scan) always runs.

## In

B: the picker, the suggestions (dashboard, cx-edit, cx-minutes, cx-sweep), the warnings and markers, the card, meeting prep blockers, client-visible rules for client reports.
C: the Labels page and cx-edit phrases, item and people labels, Work property, group, filter and bulk change, the warning card on every route out (`report.py`, `review.py`, `report.adhoc`, Draft email, Excel export, ask creaite, search), the sensitivity read at extraction and before sharing, the double catch.

## Out

- An automatic critical path, and dates that move targets by themselves.
- Reminder-or-review label behaviours (later, once labels have been used).
- Word's own sensitivity label (BL-121, unrelated).
- Storing the sensitivity read's verdicts unless Alan labels the item.

## Questions for Alan

1. **The suggestion chips:** three at most, as written; should cross-project suggestions need the other project's code or an ID in the text, or also shared key words (noisier)?
2. **The date warning:** warn when the dependency is due after the target, or also when it is merely due within a week of it?
3. **The warning card:** one card per output, as in the mockup, or a lighter banner when every labelled item is already excluded by default?
4. **People labels:** does an item merely *naming* a labelled person (not owned by them) count as sensitive, or only owned items? Naming is noisier.
5. **The sensitivity read's cost:** it is one Claude call per output. Run it every time, or only for client-facing outputs (recommended)?
6. **Order:** B first (smaller, extends what exists), or C first (it touches every output and the rules file)?

## Files it touches

**B:** `system/scripts/build_dashboard.py` (the warning and the card), `system/templates/dashboard.html` (picker, chips, card, tags), `system/scripts/prep_page.py` (blockers), `.claude/skills/cx-minutes/`, `cx-sweep/` and `cx-edit/` (suggestions), Help, `dev/dashboard-spec.md`, `dev/tests/`.
**C:** `tracker.py`, `propose.py`, `report.py`, `review.py`, `build_dashboard.py`, `excel_sync.py`, `live_server.py`, `dashboard.html`, the people register reader, the skills (cx-minutes, cx-sweep, cx-client-report, cx-weekly-report, cx-document, cx-review, cx-edit), the tracker conventions, `system/creaite-rules.md` (the confidential-material rule rewritten around labels), `dev/staging-format.md`, `dev/BRD.md` (new FR; NFR-04, at merge), Help, `dev/tests/` (every output route warns; the double catch; a people label flows to items; undo; the read skipped cleanly with the floor still running).

## Size

**B: M**, about four days. **C: L**, about eight to ten days, most of it in proving every route out warns. Together XL, as BL-125 is sized; best as two releases.
