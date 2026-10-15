# v2.1.0 contract: creaite's document format, its calls and the export call

Team Cap, branch `sprint-reporting` (P1 `v210-p1-doc`, P2 `v210-p2-exports`). Team Stark builds P4 against this from day 1.
Changed (15-10-2026, Team Stark): §4.6 matches Sheet as built. `partner.match(id)` is an action: Sheet ignores its return value and the partner applies the result; "every section" is a loop of single calls, never `null`. Rewrite only; no code changed.
Changed (15-10-2026, plan #65; Jarvis's decision): "File the exports beside it" is split by kind, one source of truth.
`reports.file_exports_beside` (weekly and client reports, **off** by default, BL-335) and `reports.file_minutes_exports_beside`
(minutes, **on** by default, BL-338); `creaite_doc.file_beside_default(kind)` picks by the document's kind, and
`report_server` uses it (its own `FILE_BESIDE_DEFAULT` is gone). `export`'s signature is unchanged.
Changed (15-10-2026, P8; Jarvis agreed): §4.6 `partner.match(id | null)`, the view's own Match internal (client-safe). Addition only.
Changed (15-10-2026, before P5): §4, Sheet.jsx's props and slots, written (it was a placeholder); `components/report/SheetStub.jsx`
added for Team Stark's P7 parts. Additions only.
Changed (15-10-2026, P5, additions; Jarvis for P8): §4.1 `leftReadOnly` (Side by side with the left, internal page read only and the right page editable);
§4.6 `partner.match(id)` (optional: Match internal calls it when given, else the generic copy); §4.1 notes: a hidden section keeps its
content in the draft until it is saved, the editors' `readonly` AI place. Additions only.
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
- **The settings**, by kind: "File report exports beside it" is `reports.file_exports_beside` (weekly and client reports, off
  by default, BL-335); "File minutes exports beside them" is `reports.file_minutes_exports_beside` (minutes, on by default,
  BL-338). Callers pass `file_beside=creaite_doc.file_beside_default(kind)` unless Alan ticked otherwise for this export.
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

`system/templates/dashboard/src/components/report/Sheet.jsx` (P5, Team Cap): the A4 page every report and the minutes are
edited on. It knows the data block (§1) and nothing about weekly, client or minutes: a **view** (P6 weekly, P7 minutes, P8
client) mounts it, supplies the renderers for its own sections and rows, and does its own server calls (`/api/report/*`,
`/api/minutes/*`). **Team Stark builds P7's parts now on `components/report/SheetStub.jsx`** (same props, same slot calls, a
plain textarea instead of the one editor, no zoom gestures, no AI); moving onto the real sheet is changing the import. The
JSDoc types below are in `SheetStub.jsx` until P5, then exported from `Sheet.jsx` (the stub re-exports them).

### 4.1 Props

```js
<Sheet
  doc={doc}                      // the data block (§1), as the route gave it; Sheet never mutates it: every change is onChange
  baseVersion={3}                // the version the editor opened (draft answer's `version`); Sheet sends it with each save
  scrollKey="weekly:ABC:2026-10-16:internal"   // where the scroll position and zoom are kept for this page (in memory)
  zoom={0.8} onZoom={z => …}     // optional: controlled zoom; omitted, Sheet keeps its own (0.8 to start)
  exported={false} onExported={b => …}         // Show as exported (controlled; the toolbar's toggle calls onExported)
  readOnly={false}               // approved and not yet Edit again, or a version opened from versions(): no editing controls
  leftReadOnly={false}           // Side by side only: the left (internal) page is read only (no controls, no saves) and the right stays editable (P8)
  renderers={{ byId: {…}, byType: {…}, row: {…} }}   // §4.3
  extras={[…]}                   // creaite-only blocks between sections (minutes' coverage, the milestone note) §4.3
  checks={[…]}                   // inline checks to underline (§4.5); the view works them out
  ai={{ place: "report", project: () => "ABC", confidential: () => false }}   // the one editor's AI options (BL-301 D)
  onRedraft={(section) => Promise<Redraft>}    // ✦ beside a heading (§4.4); omitted, no ✦
  onSelectAction={(id, sel) => Promise<…>}     // only "source" (Find the source) comes here; the others are the editor's (§4.4)
  onOpenItem={(ref) => boolean}  // a view's own peek for a ref (P7: a staged item); false → the standard peek (§4.7)
  partner={null}                 // Side by side (§4.6)
  onChange={(doc, why) => …}     // every edit: the whole new doc, and a short reason ("Section moved", "Heading reset")
  onSave={({doc, base_version}) => Promise<SaveAnswer>}   // Sheet calls it; the view posts to its save route
  onEvent={(ev) => …}            // everything else Sheet does (§4.8)
  toolbar={vnode}                // the view's own buttons (Approve, Export, Internal | Client | Side by side), drawn at the bar's right
/>
```

| Prop | Rule |
|------|------|
| `doc`, `onChange` | Controlled: Sheet draws `doc` and hands back a new one; the view keeps it (in its store) and passes it back. Sheet changes `sections` and `layout` together (order → `layout.order`, hide → `layout.hidden`, rename → `layout.headings`, figure order → `layout.glance`) so P3's `remember_layout` gets a consistent layout. |
| `baseVersion`, `onSave` | Sheet saves 1.5 s after the last change, on ⌘S and when it unmounts with unsaved changes, one save at a time (a change during a save is saved after it). `SaveAnswer` is the save route's answer (§2 `save`, P3's `save_draft`: `ok`, `version`, `conflict`, `message`, `removed`). On `ok` Sheet takes `version` as the next base and shows "Saved · version N" in the bar; on `conflict` it stops saving and shows the message with **Reload** (`onEvent({type: "reload"})`); `removed` (client leak) is shown as a line under the bar. |
| `zoom` | The page's width as a share of the sheet area's width, **0.4 to 0.8** (BL-335: 80% by default). − and + in the bar (steps of 0.05), trackpad pinch (a `wheel` with `ctrlKey`, its default prevented), ⌘+ ⌘− and ⌘0 (back to 0.8) while focus is in the sheet area. Clamped; the point under the pointer (or the top of the view for keys) stays put. |
| `scrollKey` | **The scroll position is never reset by a redraw** (P5's first rule). Sheet owns its scroller and never sets `scrollTop` except to restore: it remembers, per `scrollKey`, the top-most visible section's id and the offset into it, and restores that after a zoom, a section move, a show-as-exported toggle, a doc replaced by a save or reload, and on switching views (each view passes its own key; switching back returns to the place). |
| `exported` | Show as exported: the page exactly as `creaite_doc.render(doc, editing=False)` gives it: no handles, bars, ✦, checks, tags, ≠ markers, extras, hidden-section bars or hidden rows; read only. Sheet's page markup uses render's classes (`.page`, `header.doc`, `section[data-id]`, `h2`, `table`, `.figure`) and the same type sizes (body 14px, tables 12.5px), so editing and exported differ only by the controls. |
| `leftReadOnly` | With a `partner`: the left page is drawn and behaves as `readOnly` (no controls, no saves, `onChange` never called for it) while the right page stays editable. Ignored without a `partner`. |
| `readOnly` | No editing controls and no saves; ✦, selection actions, the peek and Show as exported still work. |

**Page breaks.** The page is A4 at the chosen width (210 × 297 mm, padded 16 mm like the print `@page` margin, so a page holds
265 mm of content). Sheet marks a break every 265 mm of content at the current scale, as a thin dashed line across the page
with "Page 2" at its right; a section with `break-inside: avoid-page` that would straddle is drawn starting on the next page,
as Chrome prints it. Markers are creaite only. The footer's page number is the export's (P2), not Sheet's.

### 4.2 The section model

Each `doc.sections[i]` is drawn in list order, with a **handle** at its left while editing (hover or focus):

- **Move:** drag the handle, or Alt+↑ / Alt+↓ with focus on it; the list order changes and `layout.order` with it. The header
  section (`type: "header"`) moves like any other only if the view says so (`renderers.byId.header.fixed`, default fixed).
- **Hide:** the handle's menu (`Menu` block) has Hide; the section becomes the §1 hidden stub (content dropped on save) and a
  thin "Hidden: <heading> · Show" bar holds its place. Show brings back an empty section of its type; the view refills it on
  `onEvent({type: "section-shown", id})` (P3's `/api/report/draft` with `fresh`, or the minutes' own).
- **Rename:** the heading is a one-line plain field in place. A heading not equal to `default_heading` shows **Reset** beside
  it: `heading = default_heading`, and the id leaves `layout.headings`.
- **Rows** (`type: "table"`): each row has an eye; `shown: false` keeps only `ref` and `shown` (§1) and is greyed in place
  with its ref while editing. "Showing 5 of 8" sits under the table when any row is hidden. Rows hidden one by one are this
  document's only; row rules (`layout.rows`) are the view's.
- **Figures** (`type: "figures"`): drag to reorder (`layout.glance`), eye to hide (`shown`).

### 4.3 Slots: how a view draws its sections

```js
renderers = {
  byId:   { health: HealthSection, milestones: Timeline, current_state: CurrentPanes },   // first choice
  byType: { text: …, table: …, figures: …, panes: … },                                     // then this; then Sheet's default
  row:    { risks: RiskRow, actions: ItemRow },                                            // a table section's rows, by section id
}
extras = [{ key: "coverage", after: "actions", render: CoverageBlock }]   // after: a section id, or null for the end
```

Sheet has a default for every §1 type (text through the one editor, rich; table cells plain; figures; panes; header; health
and timeline as their `text`), so a view supplies only what differs. A renderer gets one argument, **`SectionCtx`**:

| Field | What it is |
|-------|------------|
| `section`, `doc` | The section and the whole document (read only). |
| `editing`, `exported`, `readOnly` | How it is being drawn: a renderer draws no controls when `exported` or `readOnly`. |
| `update(patch, why)` | Merge `patch` into this section and call `onChange`. |
| `setMeta(patch, why)` | Merge into `doc.meta` (minutes: coverage, cue times). |
| `Text` | The one editor as a component: `<ctx.Text field="text" rich />` edits `section.text` (or a row cell with `row`, `col`), saves through `update`, carries `ai`, the checks and the tags for that field. On the stub, a textarea. |
| `ItemRef` | `<ctx.ItemRef id="ABC-A-003" />`: an ID that opens the peek (§4.7). |
| `Tag` | `<ctx.Tag tag={t} />`: a source tag (§4.5). |
| `level(key)` | Returns `data-level={key}` props for a block that must sit level with its partner in Side by side (a minutes topic). |
| `Spark` | `<ctx.Spark />`: the ✦ for this section, for a renderer that draws its own heading row (absent without `onRedraft`). |
| `peer` | The partner document's section with the same id in Side by side, else `null` (for Match internal and ≠). |

A **row renderer** gets `RowCtx`: `{row, index, section, item: doc.items[row.ref] || null, editing, exported, readOnly,
setRow(patch, why), removeRow(why), Text, ItemRef, Tag}`. `removeRow` takes the row out of the section (P7's ✕ Remove; Undo is
the view's, by putting it back through `update`). The deadline popover, the owner picker, Looks like and Looks done live in
P7's row renderer, not in Sheet.

An **extra** gets `{doc, editing, readOnly, setMeta, ItemRef}`; it is drawn while editing and read only, never in Show as
exported or an export. Coverage is an extra over `doc.meta.coverage`, not a section.

### 4.4 AI: ✦, selection actions

- **✦ beside a heading** (only when `onRedraft` is given and the section type is `text` or `panes`, or the view's renderer
  draws `ctx.Spark`): Sheet calls `onRedraft(section)` and shows its answer, **`Redraft`** `{text, panes?, sources: [{ref,
  label}], lines?: string[]}`, beside Alan's text, with **Keep mine**, **Use this** and, when `lines` is given, **Add the new
  lines**. Nothing changes before a choice; Use this or Add goes through `update`. The view builds the request: P6 from the
  week's facts (client-safe facts only in a Client view, BL-336), P7 from the transcript. `/api/edit/ai` is the transport
  only for a selection (below); a section redraft needs more than the selected text (see open question 1).
- **Selection actions** are the one editor's AI bar (BL-301 D, `AiSelect.jsx`) with `ai.place` `"report"` or `"minutes"`:
  **Shorten** (`shorter`), **Make it executive** (`executive`), **Polish** and **Find the source**, in that order, then
  "Or say what you want…". Suggestions are shown beside Alan's words with Accept or Discard, as everywhere. **Find the
  source** is not a rewrite: the editor calls `onSelectAction("source", {sectionId, text})` and Sheet shows the answer, `{found:
  [{ref, label, quote?}]}`, as a small list; each opens the item, file or transcript point (`onEvent({type: "source", …})`).
  P5 adds the `report` and `minutes` places (and the `polish` option) to `edit_ai.py` `PLACES`.

### 4.5 Checks and source tags

- **Checks** `[{id, section, field?, row?, quote, note, last?, actions: [{id, label}]}]`: Sheet underlines the first match of
  `quote` in that field (the editor's claim mark, never saved) and shows `note` and `last` ("Last recorded: 3 overdue on
  14-10-2026") on hover or focus, with the check's actions as buttons (reports: Use that, Keep mine; minutes: Use that, Keep
  mine, Show in the transcript). A click is `onEvent({type: "check", id, action})`; the view changes the text or drops the
  check. Open checks are counted in the bar ("2 checks open"), for the approve popup to list.
- **Source tags** are `section.tags` (§1) and a row's `source`: drawn after their line as a small chip (an item ID, or a time
  for the minutes, P4's shape `{ref: "transcript", turn, time, text}`: `turn` the transcript turn's number, `time` its HH:MM:SS or
  null when the transcript has no times; Jarvis, 15-10-2026 on plan #70); a click opens the item (§4.7) or emits
  `{type: "tag", tag}` for a time tag (P7 scrolls the transcript); hover shows ✕ to remove one; **Remove all tags** beside the heading. **Never exported** (render
  ignores `tags`), never in Show as exported.

### 4.6 Side by side

`partner = {doc, label: "Client" | "Distributed", baseVersion, scrollKey, renderers?, match?, onChange, onSave, readOnly?}`: Sheet
draws `doc` (always the internal one) on the left and `partner.doc` on the right, each with its own saves.

- **Level:** sections with the same `id`, and blocks with the same `ctx.level(key)` inside them, are given the same height
  (the shorter padded at its foot), so their headings stay level; re-measured on every change (`ResizeObserver`).
- **Scroll together** (on by default, a toggle in the bar): one scroller for both.
- **≠ markers** on the left page: a section whose shown content differs from its peer (headings, text, rows shown, figures,
  health flag) gets "≠ Client" (or "≠ Distributed"); hover shows both versions. creaite only.
- **Match internal** on each right-hand section and **Match internal for every section** in the bar. Both are actions:
  **`partner.match?: (id: string) => void`** (optional; P5 added it, Sheet as built, 15-10-2026). When the view gives it, Sheet
  calls `partner.match(id)` for the section and ignores any return value; the partner applies the result itself (the Client view:
  `match: id => setClientDoc(matchFor(id))`). The bar's button loops over the sections whose content differs from the peer and calls
  `partner.match(id)` once for each, never with `null`, so "every section" is a loop of single calls. Each call must read the
  partner's latest doc when it runs, because one click makes several calls in a row.
  A Client view must give `match`: a verbatim copy would put internal rows and wording on the client's page (P8's
  `clientDoc.matchClientSection` copies only what a client may see). Without it, Sheet makes the generic copy: the left section's
  content goes in, keeping the right page's hidden sections, logos and row eyes, as `partner.onChange(doc, "Matched internal")`
  (distributed minutes).
  The label "Matching internal" or "Edited for the client" is worked out by comparing, not stored.

### 4.7 Item IDs and the peek

`ItemRef`, row refs and tags open **the standard peek, with Sneak peek in it** (BL-322): `onOpenItem(ref)` first; if it
returns false, a milestone (`-M-`) opens with `milestones.js` `openMilestone(id)` and anything else with `panel.js`
`openRecord("all", id)`. Sheet never opens its own peek or mounts `SneakPeek`. An ID Sheet can't find in the tracker or
`doc.items` is drawn as plain text. When the peek saves, the view refreshes `doc.items` (its route's draft, or the data
reload) and passes the new `doc`; Sheet redraws in place, the scroll kept.

### 4.8 Events (`onEvent`)

| `type` | Fields | When |
|--------|--------|------|
| `saved` | `version`, `answer` | A save answered `ok`. |
| `save-failed` | `answer` | Not `ok` (a conflict also stops autosave). |
| `reload` | | Alan pressed Reload after a conflict. |
| `section-shown`, `section-hidden`, `section-moved`, `heading-reset` | `id` (`to` for a move) | After the `onChange` for it. |
| `zoom` | `zoom` | Zoom changed (also `onZoom`). |
| `exported` | `on` | Show as exported toggled (also `onExported`). |
| `check` | `id`, `action` | A check's button. |
| `tag` | `tag` | A time tag clicked, or ✕ on a tag (`removed: true`). |
| `source` | `ref` | A found source picked (Find the source). |
| `item` | `ref` | An item opened in the peek. |
| `redraft` | `id`, `choice` (`keep`, `use`, `add`) | A ✦ answer used or kept (for the drafts counts). |

### 4.9 The stub (now)

`components/report/SheetStub.jsx` takes every prop above and honours: `doc`/`onChange`, `renderers` (`byId`, `byType`, `row`)
with the same `SectionCtx` and `RowCtx`, `extras`, `exported`, `readOnly`, `onSave` with `baseVersion` (on ⌘S and a Save
button, no timer), `onOpenItem` then the standard peek, the scroll kept on redraw, `zoom` as a fixed width (no gestures),
and `partner` drawn as two columns (no levelling, no ≠). It ignores `checks`, `ai`, `onRedraft` and `onSelectAction`. Its
`Text` is a `<textarea>`; its `Spark` and handles are absent.

### 4.10 Open questions (for Alan or the Product Manager)

1. **✦ on a section:** the plan says "through `/api/edit/ai`", but that route sends only the selected text and the project's
   names and IDs, while BL-335 wants a fresh draft "from the week's facts, with its sources". Proposed: a new `/api/draft`
   kind per section (`report-section`, `minutes-section`), built like the BL-218 drafts; Sheet only needs `onRedraft`, so
   either answer fits the contract.
2. **Find the source:** where it looks (the week's tracker changes and sources for reports, the transcript for minutes) and
   whether it may call Claude or is plain code. Sheet only needs `onSelectAction("source")`.
3. **Polish** has no `edit_ai.py` option yet (`spelling` is the nearest). Is Polish spelling and grammar only, or a light
   rewrite?
4. **Inline checks for reports:** no route works them out yet (`status_checks.check` is Current state's). P6 needs one on
   the week's facts ("the last recorded figure"); the contract fixes only the check's shape.
5. **The peek's save reaching the report:** the components base has no `dataVersion` signal yet (`dev/COMPONENTS.md` §2
   plans `src/stores/data.js`). P5 adds it unless the Scrum Master prefers the views to reload through their routes.
6. **The editor isn't on `sprint-reporting` yet** (v2.0.0's `core/editor.js`, `TextEditor.jsx`, `AiSelect.jsx` are on
   `v20-base`), so the stub cannot use it and P5 waits for v2.0.0's merge, as the plan says.

## Integration notes (v2.1.0)

When P6, P7 and P8 merge into one page, the dashboard's source is bundled into one script and `dev/tools/check.py`'s JSDUP
fails a top-level name declared in two modules. Each part's top-level name must therefore be unique across the bundle, and
the old name must not come back at the merge. Status is as at `eb10dd4a` (`origin/v210-integration-rehearsal`).

| Part | Old name | New name | Where it is now | Status |
|------|----------|----------|-----------------|--------|
| P6 | `Bar` | `WeeklyBar` | `components/report/weekly/WeeklyView.jsx:41` | done |
| P6 | `RENDER` | `WEEKLY_RENDER` | `components/report/weekly/WeeklyView.jsx:25` | done |
| P6 | `FLAGS` | `HEALTH_FLAGS` | `components/report/weekly/Top.jsx:42` | done |
| P6 | `MON` | `TL_MONTHS` | `components/report/weekly/Timeline.jsx:11` | done (`MON` in `core/datewords.js` is a different, core name) |
| P6 | `take` | `takeWeekly` | `stores/weekly.js:43` | done |
| P7 | `MONTHS` | `MONTH_WORDS` | `core/datewords.js:17` (P7 adds this file) | done (clashed with `MONTHS` in `components/Picker.jsx`) |
| P7 | `where` | `filedAt` | `components/minutes/ApprovePopup.jsx:17` | done |
| P8 | `Bar` | `ClientBar` | `components/report/ClientView.jsx:42` | done |
| P8 | `Pop` | `ClientPop` | `components/report/ClientParts.jsx:50` | done |
| P8 | `FLAGS` | `CLIENT_FLAGS` | `components/report/clientDoc.js:11` | done |
| P8 | `withSection` | `withClientSection` | `components/report/clientDoc.js:20` | done (P6's `withSection` in `weeklyDoc.js` stays) |
| P8 | `matchSection`, `matchAll` | `matchClientSection`, `matchClientAll` | `components/report/clientDoc.js:58, 79` | done (`sheetLib.js` keeps `matchSection`, `matchAll` for Sheet) |

The P6 and P8 names are already in the tree; the table is kept so a merge does not bring the old names back. The P7 row for
