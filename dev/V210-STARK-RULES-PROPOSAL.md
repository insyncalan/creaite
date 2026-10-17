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

## P1 to P3 (Team Cap's parts, written by Team Stark; issue #74)

Not applied: `system/creaite-rules.md` and the skills are not edited here. Paths are the ones on `sprint-reporting` (P1 `creaite_doc.py`, P2 its export, P3 `report_doc.py`, `report_server.py`, `client_leak.py`) and `v210-p3-relock`. None of them adds a script command line, a permission rule, an approval or a guard change: the libraries have no command line (so no `reach.SCRIPT_COMMANDS` entry), the routes are the live server's own, and `reach.py` is unchanged.

### creaite-rules.md

**Folder map, `system/scripts/` row** (after the entries above):
> `creaite_doc.py` (v2.1.0 P1: creaite's document format: a weekly report, a client report or a meeting's minutes as one `.html` file holding the A4 page and its data; read, save through `filechange.py`, versions, undo, and the exports to HTML, Word and PDF, P2; library only, no command line); `report_doc.py` / `report_server.py` / `client_leak.py` (P3, BL-335, BL-336: the reports built from the tracker as creaite documents, the live server's `/api/report/*` routes, and the check that nothing Sensitive, partner-only or not client-visible reaches a client report; no command line).

**Folder map, `projects/<CODE> <Name>/` row (reports and minutes folders):**
> Weekly and client reports are filed as `YYYY-MM-DD Weekly report - <Project name>.html` and `YYYY-MM-DD Client report - <Project name> (<Client>).html` (creaite's own format, one per client) when drafted in creaite; older reports stay Word. A filed report or minutes is never saved over: a change is a new draft or a new version, filed only on approval (one apply, with Undo).

**Folder map, `system/branding/` row:** add "`logos/` holds the report logos (`firm.<ext>`, `<CODE>-client.<ext>`, `<CODE>-partner.<ext>`); local only, kept out of git".

**Folder map, `system/config/settings.json` row:** add "`report_layouts.<CODE>` keeps each project's weekly layout and each client's layout; `reports.file_exports_beside` (reports, off) and `reports.file_minutes_exports_beside` (minutes, on) decide whether an export is filed beside its source".

**Non-negotiables, "Confidential material" bullet:** one sentence:
> A client report holds only client-visible items; an item labelled Sensitive or partner-only never appears in one (a partner-only label can only withhold, never add), and a client report is approved or exported only after that week's internal report is approved. Nothing is sent.

**Dashboard editing section, a new bullet after the Minutes and reports bullet P4 to P9 proposes:**
> **Report routes (v2.1.0):** `/api/report/draft|save|approve|export` (page token, under the live server's lock, none passes an approver). A draft is the filed report if there is no draft, else a new one built from the tracker; Save writes the draft, and on a filed report writes a new draft and leaves the filed file as it is (Alan, 15-10-2026); Approve stages one proposal and applies it with `tracker.py apply`, so Undo puts the filed report back exactly (the proposal stays in Review); Approving the internal week re-locks the project's unfiled client drafts to its approved facts, withholding only. Export is made from the data (HTML, Word, PDF) and is filed beside the report only when `reports.file_exports_beside` is on.

**Skills and commands table, `cx-weekly-report` and `cx-client-report` rows:** already proposed above ("a draft report in the editor, filed in `reports/` on approval"); add "as a creaite page (`.html`)" and, for `cx-client-report`, "only after the week's internal report is approved".

**Retention:** nothing from P1 to P3 adds a kept or deleted file beyond file-change backups (90 days, already listed): a report's earlier versions are backups of its saves.

### Skills

The P3 lines under cx-weekly-report and cx-client-report above hold. Add only the P1 to P3 facts:

- **cx-weekly-report:** the draft is `/api/report/draft` (`report_doc.weekly_doc`); Approve is `/api/report/approve` (`report_doc.stage_weekly`, one proposal applied with `tracker.py apply`); the Word build step (`report.py weekly_stage`) stays only for the old flow until Team Cap retires it. "To correct a filed report, edit it: that starts a new draft and the filed report stays as it was until it is approved."
- **cx-client-report:** `report_doc.client_doc` and `stage_client`; "Approve the internal week first" is a hard refusal, not a warning; one report per client, named `… (<Client>).html`; the leak check (`client_leak.findings`) runs at Approve and Export, and a finding stops both. "A partner-only label (Partner only, partner-only or partner) keeps an item out."
- **Both:** exports are HTML, Word or PDF from the data (`creaite_doc.export`); filing them beside the report is Alan's setting (reports off, minutes on), never the skill's choice.
