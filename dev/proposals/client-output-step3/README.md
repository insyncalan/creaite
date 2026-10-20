# Client output step 3: no client file around the snapshot (v2.5.1, #239)

Step 3 of `dev/proposals/client-output-snapshot.md`, on top of steps 1 and 2 (branch v251-step3). Built in unguarded files; the
guarded follow-ups are the diffs here, for Jarvis to apply. Every diff passes `git apply --check` on v251-step3.

## Every producer of client output, and how it is gated

| # | Producer (who makes a client file or text) | Gate after step 3 | Step |
|---|---|---|---|
| 1 | Reporting hub **Export** of a client report (HTML, Word, PDF): `/api/report/export` → `report_server._client_export` | `client_snapshot.client_export`: the checked snapshot only (hash verified), under the save route's lock, the made file checked again (`client_output.check`); a posted `page` is not taken and the answer says so (`page_ignored`) | 2, 3 |
| 2 | Reporting hub **Approve** of a client report: `/api/report/approve` → `report_doc.stage_client` → `tracker.py apply` | the snapshot's one check (`client_snapshot.build`), the filed file checked (`client_output.filed_findings`), the snapshot written beside it with its hash recorded | 1, 2 |
| 3 | **Show as exported** (client): `/api/report/exported-view` | `client_snapshot.preview_html`: a preview snapshot, built, checked and rendered as an export is, never written | 2 |
| 4 | `creaite_doc.export`, `_make_export`, `word_export` called directly (any script) | refuse a client report without `client_snapshot.TOKEN` | 2 |
| 5 | `/api/minutes/export`, `minutes_record.record_at` / `export` | refuse a file that is a report by any sign (kind, name, folder, data) | 1 |
| 6 | **`report.py client-stage`** (cx-client-report; Alan's own Claude Code session can still run it, ask creaite can't stage reports) | **routed**: saves the hub's own client draft (`report_doc.build` + `save_draft`), makes no Word file and stages nothing; its files come only from #1 and it is filed only by #2. The snapshot's check runs once at staging so Alan hears what would stop Approve; unknown spec keys refused; an open draft is never replaced unless `replace` | 3 |
| 7 | `docx_tools.py fill` (command line) and `report.fill` with the **client report template** | refused (`docx_tools.fill_command`: by path, or a byte copy of the template). `creaite_doc.word_export` fills a template it derives for one export (only from #1), so it is unaffected | 3 |
| 8 | `review.py approve` and the Excel Review sheet, on an **older Word client proposal** (staged by v2.5.0's client-stage) or the client-safe one-pager | the whole client check (`plain_findings`) plus the output check on the Word file (`review.word_output_findings`: body read through the confusables skeleton and JSON escapes with the health line still allowed per line; headers, footers, notes, comments and properties with no allowance; gap B; pictures against the templates'); **`--as-staged` no longer files a finding** (only the one-pager's own `included_labelled` stand); approval records the file's SHA-256 (`checked_sha256`) | 3 |
| 9 | **`tracker.py apply`** filing an approved Word client draft (#8's) | **guarded, `tracker.diff`**: refused unless the draft is the file whose check passed at approval and the check still passes (`review.client_apply_problem`); the decision goes back to pending | 3 (pending) |
| 10 | `report.py steerco-stage --version client` (cx-steerco client-safe; also Prep's "Draft the one-pager", through ask creaite) | checked as client output when made (`report.steerco_client_findings`): a finding deletes the draft and stages nothing; then #8 and #9 | 3 |
| 11 | `report.py adhoc` (cx-document) | refuses a client audience (#127): internal only | before |
| 12 | `export_page.build` (a page the browser posted) | refuses a client report's page outright; the client-only code is gone (below) | 3 |
| 13 | Distributed minutes (`/api/minutes/export`, audience distributed) | their own gate (out of scope, unchanged) | — |
| 14 | Text, not files: AI drafts with a client audience (`drafts.py`), AI on selected text in the client sheet (`edit_ai.py`), Match internal (`/api/report/match-check`) | each reply or match is checked with `client_leak` before it is shown or copied; nothing is filed; unchanged | — |
| 15 | Prep pages, the Excel export, search summaries | internal only; never client output | — |

Known limit of #7: it stops the old way of making a client Word file (the client template filled from free values); a template
edited by hand into another file is just a Word file Alan made himself. What can never be filed without a check is #8 and #9.

## The posted page (item 2)

- `/api/report/export` (client): `page` is not passed on (`client_snapshot.client_export` has no `page` parameter); the answer
  carries `page_ignored: true` and a sentence in its message, otherwise the same shape. `creaite_doc._posted_page` never looks at a
  page for a client report, and a client export never says `plain`.
- `export_page.py`: `build` refuses a client report's page (`CLIENT_PAGE`); gone: `CLIENT_ATTRS`, `CLIENT_SVG_ATTRS`, `ITEM_ID`,
  `client_attr_ok`, `metadata_free`, the `client` parameters of `css_closed`, `safe_css_value`, `src_ok`, `keep_attr`, `Clean`,
  `clean_markup`, `clean_css`, `css_strings`, `CSS_CONTENT`, and `check_page`'s `client_leak.plain_findings` call with its
  health-line allowance (the review's LOW 4: moot, and now dead code removed). The weekly report's Show as exported is unchanged.
- Dashboard: `CLIENT_EXPORT` (exportPage.jsx) and `exportClientReport`'s unused page argument removed; the client Show as exported
  is the server's render since step 2.

## Migration (item 3)

Fixtures made by v2.5.0's own writers (`dev/tests/fixtures/client-migration/make_fixtures.py`, run against a plain copy of
f92f440a; `MANIFEST.json` holds the version and each file's hash): a client draft, a filed client report (no snapshot), the same
filed report hand-edited on disk, the Word client report and the client-safe one-pager with their proposals.
`dev/tests/test_client_output_step3.py`, `test_migration_*`:
- a v2.5.0 draft opens (`where: draft`) and exports; its snapshot is built on first use (registry state `draft`);
- a v2.5.0 filed report opens (`where: filed`) and exports as HTML and Word; a snapshot is built from the filed file's text
  (state `filed`); the filed file is never rewritten; Show as exported works;
- the hand-edited filed report: every export answers "This client report can't be exported again: <findings>" (the hidden ID
  among them), Show as exported the same, and nothing is made;
- `system/staging/client-snapshots.json` deleted: the next export rebuilds (the same filed file's hash recorded again); for a
  report approved since, its snapshot beside it isn't trusted without the registry and is rebuilt from the filed file;
- older Word proposals still in Review are checked as #8 (`test_reports`, `test_client_gate` use the fixtures).

## Decided here (for review)

- cx-client-report no longer makes a Word file: the client report is the hub's (one document type, one exporter). Its period
  starts at `period_start` and ends on the week's Friday, and it is approved only after that week's internal report, as the hub's
  client report always was. `input_needed` lines join the next steps as "Needed from you: ...".
- `--as-staged` can't file client output with a finding. The one-pager's labelled items Alan chose (`include_labelled`) still
  stand, as BL-94 intended.
- A hard-linked picture or logo is never drawn (the review's L1): `creaite_doc.text_image` takes `paths.image_file`'s rules
  (`_own_picture`), and the Word logo check and the snapshot's logo table refuse a hard link too.

## Guarded diffs

1. `tracker.diff` (tracker.py): `client_draft_problems` in the apply's dry run (#9). Risk: low; an approved older Word client
   proposal from before this branch has no `checked_sha256`, so it goes back to Review to be approved again (said in the refusal).
   Tested with the diff applied in the test vault (`test_word_a_draft_changed_after_approval_is_never_filed_with_the_tracker_proposal`,
   `test_word_the_clean_approved_draft_is_filed_with_the_tracker_proposal`); without it, the mutant test shows the gap it closes.
2. `creaite-rules.diff` (creaite-rules.md): the cx-client-report row of the skills table says how it is approved and filed now.
3. Step 1 and 2 diffs, re-checked on v251-step3: `client-output-step1/client_leak.diff`, `client-output-step2/live_server.diff` and
   `reach.diff` all pass `git apply --check` unchanged; see "Checked with every diff applied" below.

## Checked with every diff applied

RESULTS
