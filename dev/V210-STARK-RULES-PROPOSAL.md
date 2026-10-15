# v2.1.0: Team Stark's proposed lines for the rules and the skills (issue #74)

Not applied. `system/creaite-rules.md` is Team Cap's for wording, and the skills are not edited here. Each line is for Team Cap to take, reword or drop. Paths are the ones the branches create (P4 `v210-p4-minutes`, P5 `v210-p5-sheet`, P7 `v210-p7-minutes-view` and `v210-p7-followup`, P8 `v210-p8-client`, P9 `v210-p9-reports`). Nothing here touches a guard, a permission or the never list: none of these parts adds a script command, a permission rule or an approval.

## creaite-rules.md

**Folder map, `system/scripts/` row** (add after `drafts.js`/`quality.py` entries, in the same style):
> `minutes_record.py` / `date_words.py` (BL-338: a meeting's minutes as a creaite document drafted at staging, filed on approval; dates in words worked out from the meeting's date; library only, no command line); `client_check.py` (BL-336: the check of what a client report leaves out, run before every client export; read only).

**Folder map, `projects/<CODE> <Name>/` row or the minutes folder wording** (only if Team Cap's P1 text hasn't covered it):
> Minutes are filed as `YYYY-MM-DD <Meeting title>.html` (creaite's own format) when cx-minutes drafted them in creaite; older minutes stay Word. Filed minutes and filed reports are never saved over: a new version is saved under a new name.

**Folder map, `system/staging/` row:** no change. The minutes record draft lives in `drafts/<stem>.html`, which the row already names. A refused save removes only its own unsaved copy there.

**Dashboard editing section, a new bullet after "Prep page (BL-98)":**
> **Minutes and reports (v2.1.0):** Review's Open draft on minutes opens the minutes view (`#minutes=<path>`, under Review): the minutes as a sheet with the transcript, checks and item rows, Internal, Distributed or Side by side, and Approve minutes (the minutes and the ticked items in one apply through `tracker.py apply`, the one writer). Reports opens every project's week (`#reports`) and each project's reporting space (`#reporting=ABC`), and a client report has its own view (`#client-report=ABC/<week>/client`). These routes (`/api/minutes/draft|save|approve|export|followup`, `/api/report/check`) are dashboard-only (page token), and none passes an approver: **saving over filed minutes or a filed report is refused** with no approval and no card (Alan, 15-10-2026), so a change is a new version under a new name. Every client export runs the left-out check on the server first. The follow-up email is drafted by plain code from the version on screen, never holds what the Distributed version leaves out, and is never sent.

**Dashboard editing, "Rules" bullet:** add "minutes" to the lines the bulk rule never covers is not needed (it already says minutes); add nothing.

**Project documents / Client-safe:** one sentence for the client-leak rule:
> A client report's health difference (`meta.health_diff`: the reason and the internal flag) is kept in the draft only and is dropped from the filed client file and its data block (Alan, 15-10-2026).

**Skills and commands table, `cx-minutes` row:** "transcripts become draft minutes (a creaite page) and proposed items; filed on approval" in place of "draft Word minutes". **`cx-weekly-report`, `cx-client-report` rows:** "a draft report in the editor, filed in `reports/` on approval" in place of "a Word report" (once P3 lands; the wording is Team Cap's).

**Retention:** nothing from P4 to P9 adds a kept or deleted file.

## Skills: minimal changes for "draft into the editor"

### cx-minutes (`.claude/skills/cx-minutes/SKILL.md`)

P4 already changed this file on `v210-p4-minutes` (the record at stage; the Word path kept for older specs). For P7 add only:
1. In the step that tells Alan what happens next: "the minutes open as a page in Review (Open draft), where the transcript, checks and item rows are; **Approve minutes** applies the minutes and the ticked items in one apply".
2. "Saving over filed minutes is refused: a correction is a new version, under a new name."
3. "The follow-up email is drafted from the minutes view's Export menu, not by cx-minutes."
No other change; the Word path stays for a spec without `"minutes"`.

### cx-weekly-report (`.claude/skills/cx-weekly-report/SKILL.md`), once P3 lands

- Replace "drafts a Word weekly report filed in `reports/`" with "drafts the weekly report into the report editor (the A4 sheet, `#reporting=ABC`); Alan checks it there and approves; creaite files it in `reports/`".
- Replace the docx build step with the draft call (`/api/report/draft`, P3's contract) and keep the rule that a project with pending items is blocked.
- Add "A filed report is never saved over: a new version has a new name."

### cx-client-report (`.claude/skills/cx-client-report/SKILL.md`), once P3 lands

- Same replacement: the draft opens in the client view (`#client-report=ABC/<week>/client`) beside the internal week, not as a Word file.
- Add the two P8 rules: "the client's health may differ from the internal health but needs a reason, kept in the draft and never filed" and "every client export is preceded by the left-out check; it waits for the internal week's approval".
- Keep: client-visible items only, confidential material left out, never sends, never creates an email draft.
