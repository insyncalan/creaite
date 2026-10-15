# v2.1.0 contract: creaite's document format, its calls and the export call

Team Cap, branch `sprint-reporting` (P1 `v210-p1-doc`, P2 `v210-p2-exports`). Team Stark builds P4 against this from day 1.
Changed (15-10-2026, P3; Alan's decision, option C): **a filed report or minutes is never changed in place.** Save on an approved,
filed document writes a new draft in `system/staging/drafts/` (the filed version as its base); the filed file stays exactly as it
is until Alan approves that draft, and that approve is the normal one apply with Undo (tracker.py replaces the filed file whole and
Undo puts it back). There is no approval card for it and the live server never passes `approver=reach.APPROVALS.issue`: `save`'s
`approver` stays only for a caller that needs it (none in v2.1.0). P3's reports: `report_doc.save_draft`; P4 does the same for minutes.
Changed (15-10-2026, P3): `export` is looked up as `creaite_doc.export`, then `doc_export.export`, then `report_export.export`
(`report_server.export_call`); the live server opens the filed copy itself. A report's export is filed beside it only when Alan
ticks it (BL-335; the route's `file_beside` defaults to false, the backlog winning over the plan's "on by default").
Changed (15-10-2026, P3, additions): an approved weekly report's `meta.client_facts` keeps the week's client-safe facts, which that
week's client reports lock to (`based_on`); a client report's `meta` has `period_start`, `period_end`, `locked`, `facts_on`,
`facts_week`. The layouts are kept in settings.json `report_layouts.<CODE>` (`weekly`, `clients.<client>`).
Changed (15-10-2026, before any use): no command line (a script command line must be classified in `reach.SCRIPT_COMMANDS`, a
guard change; P3 and P4 call it from Python); `save` takes `approver` instead of `approval`; `project_name` added.
Changed (15-10-2026, P2): `export` answers also carry `open_after`; `out_dir` is a stored folder to file in instead of beside
the document; the HTML export is filed as `<name> (read only).html` (the document's own name is the document); a filed export's
draft is removed (`draft: null`) and kept only when it isn't filed or waits on Alan's card (`needs_approval: true`); the setting
is `reports.file_exports_beside` (on), read by `file_beside_default()`.

Read with `git show sprint-reporting:dev/sprints/v210-contract.md`. A change goes in a "Changed:" line at the top and a
SPRINTCOMMS entry. Additions only once Team Stark has started; nothing is renamed.

## In one paragraph

A weekly report, a client report and a meeting's minutes are each **one `.html` file**: a self-contained A4 page rendered
from the data (inline CSS, no script but the data block, no external resource, so it opens in any browser), plus
`<script type="application/json" id="creaite-data">` holding the data. **The data is the record; the page is always rendered
from it** by `creaite_doc.render`, so the filed page and every export match. Saving goes through `filechange.py`: a new file
is a create, a later save is an edit (the earlier version backed up, logged, undoable). `system/scripts/creaite_doc.py` is the
only code that reads or writes the format.

## 1. The data block (`schema` 1)

```json
{
  "format": "creaite-doc",
  "schema": 1,
  "kind": "weekly",
  "audience": "internal",
  "project": "ABC",
  "project_name": "Example Programme",
  "title": "Weekly report",
  "date": "2026-10-16",
  "client": null,
  "version": 3,
  "saved_at": "2026-10-16 14:02:11",
  "state": "draft",
  "approved_at": null,
  "based_on": null,
  "layout": {"order": ["health", "glance", "summary"], "hidden": ["asks"], "headings": {"summary": "Executive summary"},
             "glance": ["next_milestone", "overdue", "high_risks", "decisions_needed"], "logos": ["firm", "client"],
             "milestones": ["ABC-M-002", "ABC-M-004"], "rows": {"risks": {"top": 5}}},
  "sections": [
    {"id": "health", "type": "health", "heading": "Health", "default_heading": "Health", "hidden": false,
     "text": "**At risk:** the data migration has slipped two weeks.",
     "data": {"flag": "At risk", "trend": [{"date": "2026-09-11", "flag": "On track"}], "last_week": {"flag": "On track", "why": "…"}}},
    {"id": "summary", "type": "text", "heading": "Executive summary", "default_heading": "Summary", "hidden": false,
     "text": "Markdown, as the one editor writes it.", "tags": [{"ref": "ABC-A-003", "text": "SOW signed"}]},
    {"id": "risks", "type": "table", "heading": "Risks and issues", "default_heading": "Risks and issues", "hidden": false,
     "columns": [{"key": "id", "label": "ID"}, {"key": "title", "label": "Risk"}, {"key": "owner", "label": "Owner"}],
     "rows": [{"ref": "ABC-002", "cells": {"id": "ABC-002", "title": "Vendor capacity", "owner": "Sam Patel"}, "shown": true},
              {"ref": "ABC-005", "shown": false}]},
    {"id": "glance", "type": "figures", "heading": "At a glance", "default_heading": "At a glance", "hidden": false,
     "figures": [{"key": "overdue", "label": "Overdue actions", "value": "3", "note": "", "shown": true}]},
    {"id": "asks", "type": "table", "heading": "What we need from people", "default_heading": "What we need from people",
     "hidden": true}
  ],
  "items": {"ABC-002": {"table": "raid", "id": "ABC-002", "title": "Vendor capacity", "status": "Open", "owner": "Sam Patel"}},
  "sources": [{"ref": "projects/ABC Example/minutes/2026-10-14 Steering.html", "label": "Steering, 14-10-2026"}],
  "meta": {}
}
```

**Top level**

| Field | What it is |
|-------|------------|
| `format`, `schema` | Always `"creaite-doc"`; `schema` is this shape's version (1). A reader refuses a newer schema; an older one is upgraded in `read`. |
| `kind` | `weekly`, `client` or `minutes`. |
| `audience` | `internal` (default), `client` (a Client view, BL-336) or `distributed` (the minutes' distributed version, BL-338). |
| `project` | The project code (`_portfolio` for a cross-project meeting). Shown nowhere: the page uses the name (BL-101). |
| `project_name` | The project's full name as it stood (`tracker.project_label`, set by `new`); the page shows this. |
| `title` | Weekly: `Weekly report`. Client: `Client report`. Minutes: the meeting's title. |
| `date` | YYYY-MM-DD: the week ending (Friday) for reports, the meeting's day for minutes. |
| `client` | The client's name for a Client view; else `null`. |
| `version`, `saved_at` | Set by `save` (1 for a new file, then +1 each save); never set by a caller. |
| `state`, `approved_at` | `draft` or `approved`; set by the approve routes (P3, P4), carried by `save`. |
| `based_on` | `{"path", "version"}` of the approved internal document a client view or distributed minutes lock to; else `null`. |
| `layout` | The layout as used for this document (P3 also keeps it per project or client in settings). Keys: `order` (section ids), `hidden` (ids), `headings` (id → renamed heading), `glance` (figure keys in order), `logos` (`firm`, `client`, `partner`), `milestones` (refs shown in the list), `rows` (row rules by section id, e.g. `{"top": 5}`). Unknown keys are kept. |
| `sections` | **In page order** (the list's order is the order; `layout.order` only remembers it for next time). |
| `items` | Each item **as it stood** when saved, keyed by its ID (tracker row fields, plus `table`). |
| `sources` | `[{ref, label}]`: files, mail or chats the document draws on. |
| `meta` | Kind-specific, owned by the part that writes it: minutes put the transcript path, cue times, coverage and the source line here (P4); reports the health difference and its reason (P8). Kept as written. |

**A section**

| Field | What it is |
|-------|------------|
| `id` | Stable within a kind (weekly: `header`, `health`, `glance`, `summary`, `milestones`, `asks`, `this_week`, `next_week`, `decisions`, `risks`, `overdue`, `current_state`; minutes: from `minutes-style.md`, P4). |
| `type` | `text`, `table`, `figures`, `health`, `timeline`, `panes` or `header`. An unknown type renders its `text` only. |
| `heading`, `default_heading` | As shown, and creaite's own (for Reset). |
| `hidden` | A hidden section keeps only `id`, `type`, `heading`, `default_heading`, `hidden`; its content is dropped on save. |
| `text` | Markdown, as the one editor writes it (paragraphs, lists, bold, italic, links). |
| `columns`, `rows` | Tables: `columns` `[{key, label}]`; each row `{ref, cells: {key: text}, shown, source}`. A row with `shown: false` keeps only `ref` and `shown`. |
| `figures` | `[{key, label, value, note, shown}]` for At a glance; a hidden figure keeps only `key` and `shown`. |
| `panes` | `[{title, text}]` for Current state (type `panes`). |
| `tags` | Source tags `[{ref, text}]`: creaite only, never rendered on the page or exported. |
| `data` | Type-specific extras (health's `flag`, `trend`, `last_week`; a timeline's milestone refs). Kept as written. |

**The rule that holds whatever the caller sends:** hidden sections, hidden rows and hidden figures never reach the filed page or
an export, and their content never reaches the file. `items` loses an item that only a hidden row or section referred to.

## 2. `creaite_doc.py`: read, write and versions

Python, standard library only. **A library, with no command line** (the live server and the other scripts import it). Paths are stored paths
(`projects/<folder>/…`, or a vault path such as `system/staging/drafts/…`); a `Path` is also accepted.

```python
class DocError(ValueError)                    # every refusal below; str(e) is a plain sentence for Alan

new(kind, project, title, date, sections=(), *, audience="internal", client=None, layout=None, items=None,
    sources=None, meta=None) -> dict          # a schema-1 document, version 0, state "draft"; nothing written

read(path) -> dict                            # the data block, upgraded to the current schema
loads(text) -> dict                           # the same, from a file's text
is_doc(path) -> bool                          # a .html file with a creaite-data block; never raises
dumps(doc) -> str                             # the whole file: render(doc) with the data block
render(doc, editing=True) -> str              # the page; editing=False leaves the data block out (the HTML export)
clean(doc) -> dict                            # a copy with hidden content dropped (save and render call it)

save(path, doc, why, *, base_version=None, approver=None, via="cli") -> dict
versions(path) -> list
read_version(path, change) -> dict            # the version that change <change> replaced (from its backup)
undo(path) -> dict                            # undo the latest save of this file (filechange.py undo)

target(kind, project, date, name=None, client=None) -> str   # the stored path a document is filed at
search_text(path_or_doc) -> str               # headings and text of every shown section, for the search index
sections_text(doc) -> list                    # [(id, heading, text)] of every shown section
```

**`read` / `loads` errors (DocError):** "That file isn't there.", "That isn't a creaite document (no creaite-data block).",
"Its data isn't valid JSON.", "It was saved by a newer creaite (schema N); update creaite to open it."

**`save(path, doc, why, …)`** renders `dumps(clean(doc))` with `version` (the file's version + 1, or 1) and `saved_at`, writes it to
`system/staging/drafts/` and hands it to `filechange.perform`: a **create** when the file isn't there, else an **edit** (the
earlier version backed up under `system/backups/files/changes/<n>/`, logged in `files-log.jsonl`, undoable). Returns

```json
{"ok": true, "code": 0, "path": "projects/ABC Example/reports/2026-10-16 Weekly report - Example Programme.html",
 "version": 4, "change": 57, "message": "Changed … (change 57; …)"}
```

- `code` 0 saved; 1 refused (`message` says why; nothing written); 3 needs approval (`ok: false`, `needs_approval: true`; in an
  ask creaite run the change is on Alan's card, and the draft stays for it).
- `base_version`: the version the editor opened. If the file is now at another version: code 1, `conflict: true`,
  "It was saved elsewhere since you opened it (now version N).", nothing written.
- **Approval.** A draft in `system/staging/drafts/` and a first filing (a create) are ordinary. Saving over a filed report or
  minutes is **sensitive** under `reach.py` (a report or meeting record that may have been sent), so it needs Alan's approval.
  The live server, when Alan himself presses Save, passes `approver=reach.APPROVALS.issue`: `save` calls it with the exact
  change's fingerprint (`filechange.fingerprint`) and hands the one-time token to `filechange.perform`. `save` never issues a
  token itself, and without `approver` such a save answers code 3.
- A file at `path` that isn't a creaite document: code 1, "A file that isn't a creaite document is there; creaite never
  overwrites it."
- `why`: up to 300 characters, logged ("Weekly report saved", "Minutes approved").

**`versions(path)`** newest first:

```json
[{"version": 4, "current": true, "at": "2026-10-16 14:02:11", "change": 57, "why": "Weekly report saved"},
 {"version": 3, "current": false, "at": "2026-10-16 11:40:02", "change": 57, "backup": "system/backups/files/changes/0057/…"}]
```

The current file, then each earlier version kept in a backup (`change` is the save that replaced it; `read_version(path, 57)`
opens it). A backup that Tidy up removed (90 days) is not listed. Undone saves are not listed.

**`undo(path)`** undoes the latest save of that file that isn't undone: `{"ok", "message", "version"}` (the version now current,
or `null` when undoing the first save removed the file). Refused, as filechange refuses, when the file changed since.

**`target(kind, project, date, name=None, client=None)`** (file names from `paths.py` folders and `report.report_file`):

| Kind | Folder (`paths.folder`) | File |
|------|------------------------|------|
| `weekly` | `weekly_reports` | `YYYY-MM-DD Weekly report - <Project name>.html` |
| `client` | `client_reports` | `YYYY-MM-DD Client report - <Project name>.html`, or `… - <Project name> (<Client>).html` with `client` |
| `minutes` | `minutes` | `YYYY-MM-DD <Meeting title>.html` (`name` is the title; reserved characters removed, at most 80) |

`<Project name>` is the project's full name (`tracker.project_label`); `project` may be `_portfolio` for minutes.

**Search.** `tracker.text_of` reads a creaite document through `search_text`: each shown section's heading, then its text,
table cells, figures and panes, a blank line between sections (so `search.paragraphs` keeps each under its heading). Tags,
hidden content and the data block's other fields are not indexed. Files are found as today (`paths.project_files`).

## 3. The export call (P2 provides; signature fixed now)

```python
export(path, fmt, *, out_dir=None, file_beside=True, open_after=True) -> dict
```

- `path`: a creaite document (a draft or filed). `fmt`: `"html"`, `"docx"` or `"pdf"`. Every export is made from the data, so
  all three have the same sections in the same order, and nothing hidden.
- **HTML:** `render(doc, editing=False)`: the page without the data block. **Word:** `docx_tools.py fill` with
  `weekly-report-template.docx`, `client-report-template.docx` or `minutes-template.docx`. **PDF:** Chrome's print to PDF of the
  HTML export.
- Written to `system/staging/drafts/`; with `file_beside` (the default) also filed beside the document through `filechange.py`
  (a create, never overwriting: a taken name gets a number), named as the document with the export's extension (HTML:
  `<name> (read only).html`). `out_dir` (a stored folder) files it there instead. Filed, the draft is removed.
- **The setting** "File the exports beside it" is `reports.file_exports_beside`, on by default; callers pass
  `file_beside=creaite_doc.file_beside_default()` unless Alan ticked otherwise for this export.
- **Word:** the kind's template keeps its title block (project or meeting, status line `Internal · Draft, version N` or
  `… · Approved <date>`, the date; a client report's `meta.period_start` gives its period); its health and attendees lines go,
  and each shown section follows in page order as the template's heading, Markdown paragraphs and, for a table, the template's
  table with the section's columns. **PDF:** Chrome headless (`launch.find_chrome`), a throwaway profile, at most 90 seconds.
- `open_after`: passed back in the answer; the live server opens the export in the default viewer (`/api/open`); from the
  command line nothing opens.
- Returns `{"ok": true, "format": "pdf", "path": "<stored path of the filed copy, or the draft>", "draft": "<drafts path, or
  null once filed>", "filed": true, "open_after": true, "message": "…"}`; on failure `{"ok": false, "format", "message"}`
  ("Chrome wasn't found…", "The Word template is missing…", or a filechange refusal; `needs_approval: true` and `draft` when
  the filing waits on Alan's card). A client view or distributed minutes is refused until the document `based_on` names is
  approved ("A client report is exported only after the internal report is approved.").

## 4. Sheet.jsx props and slots (added before P5)

To be written by Team Cap before P5 starts.
