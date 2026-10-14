---
name: cx-document
description: creaite one-off Word documents (BL-75). Builds a branded Brightwater Word document from the tracker, such as an actions register, a RAID extract, a decision log or a milestone list, as a draft in system/staging/drafts/. Use when Alan says "make a Word document of …", "actions register for ABC", "a document of open risks", "document of Omar's overdue actions", "export the decisions to Word", "draft an actions list for the steering committee". Uses report.py only: never node, never /tmp, never a new permission.
---

# cx-document

Turn a request for a one-off document into a branded Word draft in `system/staging/drafts/`. The tables come from the tracker, never from you; the words around them come from the request. Nothing is filed, sent or written to the tracker.

**Projects by name (BL-101):** refer to a project by its full name in everything Alan reads (summaries, tables, messages, file names, drafts). The short code appears only inside a work item's ID (`ABC-A-003`) and in a command he can type; `tracker.project_label(code)` gives the name.

All paths are relative to the vault root. Scripts (standard library; run from the vault root):
- `system/scripts/run report.py adhoc-data <actions|raid|decisions|milestones> [--project CODE[,CODE]] [--owner NAME] [--status open|closed|all] [--type Risk] [--overdue] [--due-before YYYY-MM-DD]`: the rows as JSON, to read before writing an introduction (count, columns, rows).
- `system/scripts/run report.py adhoc <spec.json>`: builds `system/staging/drafts/YYYY-MM-DD <title>.docx` from `system/templates/adhoc-template.docx` (the Brightwater house style: wordmark, Calibri in Charcoal, Signal Green section rules, Charcoal table headers). Never overwrites; says where it wrote.

## Flow

1. **Interpret the request.** Which table (actions, RAID, decisions, milestones), which projects, owner, status, dates. Dates are shown DD-MM-YYYY and typed YYYY-MM-DD. "Open" is the default; say "all" or "closed" only when asked. Ask one short question only if it can't be guessed (which project?).
2. **Look at the data** with `adhoc-data` (read-only). If it's empty, say so and ask whether to widen it; don't build an empty document.
3. **Write the spec** in `system/staging/drafts/adhoc-spec.json`, then run `report.py adhoc` on it (it deletes the spec itself once the document is built):

```json
{"title": "ABC open actions", "subtitle": "Actions register",
 "sections": [
   {"heading": "Summary", "paragraphs": ["14 open actions across ABC; 3 are overdue."]},
   {"heading": "Open actions", "tracker": {"table": "actions", "project": "ABC", "status": "open", "group_by": "project"}}],
 "landscape": false}
```
   - A section may hold `paragraphs`, `bullets`, a literal `table` (`{"columns": ["Name", "Role"], "rows": [["…", "…"]]}`) or a `tracker` query (filters: `project`, `owner`, `status`, `type`, `overdue`, `due_before`, `due_after`, `workstream`, `columns`, `group_by: "project"`, `limit`). Columns for `columns`: actions `id project description owner workstream priority due_date status latest_update raised closed`; RAID `id project type description owner priority response_action due_date status workstream raised closed`; decisions `id project decision status made_by needed_by date` (`status` filter: `pending`, `made` or `withdrawn`, BL-53); milestones `id project name baseline_date forecast_date percent status`.
   - Use `"landscape": true` for five or more columns. Keep the words short and plain, in British English. Put only facts from the tracker or the request into paragraphs; never invent figures.
4. **Say where it is** (the path the script printed) and that it's a draft for Alan to open in Word. Mention anything left out.

## Rules

- **Only these scripts.** Never `node`, never a library you install, never a file in `/tmp` or anywhere outside the vault. If a document can't be made this way, say what is missing instead of working around it.
- **Internal by default.** These documents are Alan's own; they are not client reports. Include client-visible or confidential items only as the tracker holds them, and never put anything from `documents/` into one unless Alan says so.
- **Read-only on the tracker.** No proposals, no apply.
- **If a command is refused for permission,** don't try another way round it. See the permission request in the panel's prompt: end with one `PERMISSION:` line naming the rule you need and why.
