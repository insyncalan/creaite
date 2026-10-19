# Client output from one checked snapshot (v2.5.1, #239)

Status: design for Alan's yes. Nothing here is built. Written from the four independent reviews of f17c03c6 (repros in the review's
`work-*` folders: logo path, kind to minutes, export race, unread keys, posted page, look-alikes).

## The problem in one line
A client report is checked in one place (a draft on disk) and rendered from another (a re-read of that file, or a page the browser posts),
by several exporters. Every review finding is "the thing checked is not the thing rendered", or "a stored field the renderer trusts".

## The model
1. **Snapshot.** Approving (and an export with no approved snapshot yet) builds a *snapshot*: the cleaned client document made from
   the tracker, the project memory and the draft's **text only**, never its stored header. It is checked once (`client_leak.findings`
   and the label and left-out checks) and written as `<name>.client.json` beside the filed report with its SHA-256 recorded in
   `system/staging/client-snapshots.json`. A snapshot is never edited; a change is a new snapshot.
2. **One export function.** `client_export(code, week, fmt)` is the only way a client Word, HTML or PDF file is made. It runs under the
   handler lock, reads **only** the snapshot (hash verified), renders it, then runs a **post-render check on the output text**
   (client_leak on the text of the .docx XML, the .html or the PDF text, plus a list of the embedded pictures and their hashes against
   the snapshot's allowed pictures). Any finding: nothing is filed, the file is deleted.
3. **Derived at render, never stored:** header, `project_name`, `client`, kind, audience (always client), logos (from
   `report_doc.logos(code)` at render time), the week. The stored values are ignored.
4. **Allow-list of keys** (top level, section, row, meta): the snapshot builder copies only these; anything else is dropped and
   counted, never copied (fixes unread keys, `ref`, `milestones`, `timeline` skips).
5. **The server renders; the browser never posts the page.** The exported-page route stops accepting `page`: "Show as exported" is
   the server's render of the snapshot (or of a preview snapshot, marked Preview), so the page check (`export_page.check_page`) shrinks
   to the post-render check.
6. **Pictures**: only the project's `images/<name>` and the document's `_images/<name>` as now, plus logos from the project logo
   folder by name (no paths); all by the snapshot's picture table (name, hash).

## Routes that change
- `/api/report/approve` (client): builds and checks the snapshot, files the `.html` from it. (weekly/internal: unchanged.)
- `/api/report/export`: client kind calls `client_export`; takes the lock; `page` ignored (kept in the request for one release).
- `/api/minutes/export`, `record_at`: refuse a document that is a client report by any sign (kind, file name pattern, folder, data
  block `kind`); distributed minutes keep their own gate (out of scope).
- `/api/report/save`, `/draft`, `/check`: unchanged in behaviour, but save keeps only the allow-listed keys and never stores logos.
- `/api/report/match-check`: gates the same function (shared code), unchanged for the browser.
- `creaite_doc.export` / `word_export`: client documents refuse to render unless called by `client_export` (a token argument).
- `report_doc.stage_client`, `client_check.left_out`: become steps of building the snapshot, not separate gates.

## Migration
- Existing drafts: read once, text copied into the new shape; header and logos dropped; nothing is re-filed.
- Existing filed client reports: untouched files. Opening one for export builds a snapshot from the file's text and checks it as
  client; if it fails the check it is shown as "can't be exported again: <findings>" (a deliberate, safe break).
- `client-snapshots.json` is created on first use; deleting it only means snapshots are rebuilt.

## What breaks (on purpose)
- A hand-edited filed client file no longer exports unless it passes the check on its text.
- Show-as-exported edits the browser made to the page (not the report) no longer exist; edits go through the report.
- Scripts that call `creaite_doc.export` on a client document directly.
- ~25 tests that post a `page` or set stored logos/header (they move to the snapshot), and the export-page golden files.

## Test plan (from the review repros)
Each repro becomes a fail-first test that must fail on f17c03c6 and pass after: logo path / stale logo, kind edited to minutes
(draft and filed), concurrent save during export (real HTTP, 80 exports, 0 needles), unread top-level key and section `ref`, posted page
with foreign text (route refuses `page`), other-project wording (separate item B, listed), look-alike letters (fold more scripts or
NFKC plus confusables table in the post-render check), text-section audience spelling. Plus mutation tests: removing the post-render
check, the lock, the hash check or the allow-list each fails a named test. Plus a whole-output scan test: every client output of the
demo vault contains none of the needles, in .html, .docx, .pdf and the filed data block.

## Size and order
Large: about 3 to 4 days with Cap reviewing. Order: (1) allow-list + render-time header/logos + post-render check + lock (closes
the HIGHs, no data model change, 1 day); (2) snapshot file and hash, `client_export` as the only path, minutes refusal (1 day);
(3) drop the posted page, migrate, tests and goldens (1 to 2 days). Step 1 alone could ship as 2.5.1 if Alan wants the HIGHs closed first.

## Risks
Guarded files touched: `client_leak.py` (post-render check, look-alikes) and `live_server.py` (route wiring): Jarvis applies. The
post-render PDF text check depends on the PDF text extractor already used in tests; Word and HTML checks read the XML/markup.
