# Proposal: the client gate reads a client report as client, and reads its header (v2.5.0 audience bypass)

For Alan's approval. `client_leak.py` is guarded, so this is NOT applied; `client_leak.diff` is the change (`git apply -p1`).

## Why

The client gate (`client_leak.findings`) and `make_safe` decided client versus internal from `audience` alone, so a client report
saved or edited on disk with audience "internal" (or none) passed with 0 findings. `doc_text` never read `project_name` or `client`,
which are shown in the header, the page title, the Word fields and the file names.

## Already fixed without touching this file (branch v250-audience)

- `creaite_doc.is_client(doc)`: kind client, or audience client or distributed.
- `creaite_doc.force_client_audience(doc)`: a client report's audience is set to "client" and its `project_name` (tracker) and
  `client` (project memory) derived again; called by `creaite_doc.read_report`, which the draft route, `stage_client`, filing
  (`_file_ops`), the relock, `creaite_doc.export`, the export route and review's client check read a stored report with (so a draft
  edited on disk), and by the save route, `save_draft` and `client_check.left_out`. (`loads` itself is left as it was: edit_ai's
  check of a saved report still refuses one whose file reads as internal, test_client_gate.)
- `creaite_doc.check_audience` refuses a client report whose audience isn't "client" (the save and approve routes answer it).
- `_internal_text`, `_check_baseline` and `report_doc.client_item_links` use `is_client`.

So today every route hands the gate a client report with audience "client" and derived header fields. This proposal makes the gate
safe on its own, for any future caller that skips the normalising.

## The change (client_leak.diff)

1. `findings` and `make_safe` use `creaite_doc.is_client` instead of the audience, and `findings` checks a client report as
   audience "client" whatever it says.
2. `doc_text` also reads `header_text`: `title`, `project_name`, `client`, and every string in `meta`, `sources` and `layout`
   (the filed file's data block holds them).

## Risk

- (2) can find a client name that is also a person's name owning only internal items, or a word like "confidential" in a client
  name: such a client report would then be refused until the project memory's Client line is changed. Wanted, but say so.
- Checked only with `git apply --check` and a compile; run `test_client_gate`, `test_client_audience`, `test_report_export_save`
  and `test_client_view` after applying.

## Further proposal lines (no diff yet)

3. (B) `text_findings` and `name_findings` read only the report's own project's hidden wording and owners. Another project's hidden
   item wording or owner, written in a client report's text without its ID, passes. Proposal: check every project's hidden item
   wording and owners (the tracker's items with `client_visible = 0`, any project), as the ID check already does across projects.
   Rows and items naming another project's item are already dropped outside this file (`creaite_doc.drop_other_projects`).
4. (C, not fixed yet: needs the dashboard to say which report a picture is for) a text section's `_images/<name>` is one store per
   project, so a client report can draw a picture uploaded for the internal report. Proposal for 2.5.1: `/api/report/image` takes
   the report kind and names a client report's pictures `client-<name>`; `creaite_doc.text_image` reads only `client-` pictures for
   a client report. Outside this file, but it changes the dashboard.
