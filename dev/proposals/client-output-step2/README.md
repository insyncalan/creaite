# Proposal: the guarded parts of client output step 2 (v2.5.1, #239)

For Jarvis to apply. Step 2 (the checked snapshot and `client_snapshot.client_export` as the one client exporter) is built in
unguarded files only; these two small diffs are the guarded follow-ups. Neither is needed for step 2 to work: the code and the tests
pass with and without them. Both pass `git apply --check` on branch v251-step2.

## 1. live_server.py (live_server.diff): docstring only

What: the route list names `/api/report/exported-view` (Show as exported for a client report, the server's render of a preview
snapshot) and says `/api/minutes/export` refuses a report and that `creaite_doc.export` renders a client report only from
`client_snapshot.client_export`.

Why: the routes are registered by `report_server.routes()` (already `DRAFT_ROUTES.update(...)`), so no wiring changes; the module's
route list should still say what is served. Risk: none (text only). Test: `python3 dev/tools/check.py`.

## 2. reach.py (reach.diff): system/staging/client-snapshots is creaite's record

What: one row in the never-for-ask-creaite table: `("vault", "system/staging/client-snapshots", "write", RECORD)`.

Why: the snapshots creaite builds for an export with no approved one live there. Their integrity does not depend on this row (each
is verified against its SHA-256 in `system/staging/client-snapshots.json`, which `system/staging/*.json` already protects, and a
snapshot changed on disk is refused: `test_export_a_snapshot_changed_on_disk_is_refused`), but nothing but creaite should write
them: defence in depth. Risk: low. Checked with the diff applied in a scratch copy of v251-step2:
`python3 dev/tests/test_reach.py` passes (18 tests), and
`reach.classify('system/staging/client-snapshots/x.client.json', 'change')` answers never ("creaite's own record") while
`system/staging/drafts/` stays ordinary.

## 3. client_leak.py: nothing new in step 2

Step 2 needs no change to the gate itself: the picture rule (gap C) and the snapshot's checks live in `client_snapshot.py` and
`client_check.py`. The step 1 proposal (`dev/proposals/client-output-step1/client_leak.diff`: fold every text, read other projects'
hidden items) is still pending; when it is applied, remove the `expectedFailure` on
`test_P16_json_escaped_form_needs_the_guarded_gate_diff`.

## Not guarded, decided here (for review)

- A picture named `_images/<name>` without the `client-` prefix in a client report's text is a finding that blocks the export and
  Approve ("add the picture again from the client report"), not silently dropped. A client report Matched from internal text with a
  picture therefore needs that picture added again from the client sheet.
- A logo or picture changed after Approve is not drawn from the filed snapshot (its bytes no longer match the table); Approve again
  to take the new one.
- The older `report.py` client Word path (cx-client-report's docx_tools fill) is not routed through `client_export` yet.
