# #259 client-output leaks K2, K3, K5, P7, P16, P18: guarded proposals

v2.5.3 closes Team Cap's leaks still open after 2.5.2 (the verdict on #239, 20-10-2026). The unguarded part is on branch
`v253-client-k` (see `dev/tests/test_client_output_k.py`). Only one guarded file needs a change, and it is optional: the output
check already keeps every form out of every client file.

## 1. `client_leak.diff` (optional hardening, P16 at the gate)

`client_output.loose_findings` (new, unguarded) finds a hidden item's ID however it is written ("A B C - A - 0 0 1",
"ABC-A-0001", "ABC-0005", "ABC-5", "abc.a.001") and a hidden wording with hyphens, dots or underscores for its spaces
("Vendor-exits-the-market-before-go-live"). Every client output's check calls it (`client_output.text_findings`: export, Approve's
filed file and tracker.py apply's second check), so no client file can hold these forms today.

The diff makes the gate itself (`client_leak.text_findings`, which `client_leak.findings`, the snapshot's check and Save's
"left out" list read) call it too. That gives P16 in its strict form: gate(f(x)) refuses exactly when gate(x) refuses, and Alan
sees the finding while he edits rather than only when he exports.

- Apply: `git apply dev/proposals/client-output-k/client_leak.diff` (it passes `git apply --check` on `v253-client-k`).
- Test: `test_client_output_k.K.test_p16_gate_reads_the_loose_forms_once_the_guarded_diff_is_in` is an expected failure until
  the diff is in. It works out by itself whether the diff is applied, so it passes once it is, with no edit to the test.
- Verified: applied in a scratch copy, that test passes and the rest of the file stays green (see the branch report).

## 2. tracker.py apply's second check of a creaite-format client report: no diff needed

Cap's LOW finding: `tracker.py apply` re-checked only Word client drafts. `tracker.client_draft_problems` already calls
`review.client_apply_problem(blk, "report_decision")` on every approved report block. That function returned early for a
creaite-format draft (`word_draft`). It now hands a creaite-format client block to `review.creaite_client_problem`, which:

- refuses a client report filed by a `copy` (the draft as it is on disk), or without exactly one filed write and one snapshot write;
- checks the staged write as a filed report is checked (`client_output.filed_findings`: page text, every data-block string and the
  pictures);
- refuses it unless the snapshot written beside it is one the registry recorded at approval and names that write's SHA-256 as its
  source. A proposal edited after Approve is refused even when the gate knows none of its words.

Tests: `test_apply_refuses_a_staged_client_write_changed_to_hold_internal_content` and the control
`test_apply_control_an_untouched_staged_client_write_is_filed`. Both go through `tracker.py apply` in the throwaway vault.
`tracker.py` is unchanged.

## 3. The snapshot registry has no key (`client_snapshot.py` ~126): recommendation, do not add one now

`system/staging/client-snapshots.json` records each snapshot's SHA-256, and now also vouches for a filed client report's
sections (`creaite_doc.creaite_wrote`) and for apply's second check. A keyed hash (HMAC-SHA256 over the snapshot text) would stop
a writer that can change both a snapshot and the registry, but only if that writer can't read the key.

- ask creaite already can't write either file: the guard hook refuses any direct write outside `system/staging/drafts/`, and
  creaite's own staging records are refused for its changes.
- Any other local process runs as Alan. It could read a key kept in the vault just as easily, and the macOS keychain is outside
  what creaite may rely on (portability rule: nothing in machine settings).
- So a key adds code and a key to manage without moving the line. The real protection stays: everything is checked again after
  rendering (the output check, apply's second check).

If it is wanted later: keep the key in `system/guard/snapshot.key` (on the never list, written only by the live server), store
`mac` beside each hash in the registry, and treat an entry without a valid MAC as unknown (the snapshot is rebuilt from the file
and checked). That changes `client_snapshot.py` (unguarded) and adds `system/guard/` handling in `live_server.py` (guarded).

## What changed outside the guarded files (for the reviewer)

- **K2 / I20:** `creaite_doc.derive_sections`, `creaite_wrote` and `read_report`, plus `client_snapshot.read_once`. A text section
  counts as the client's only in a file whose bytes creaite itself last wrote: filechange's logged hash, not from an ask creaite
  run; or, for a filed report, its snapshot's source hash. Any other section that isn't one of creaite's own client sections is
  internal.
- **K3 / I19:** `creaite_doc.derive_facts`, called by `derive_client`. Items come from `report_doc.client_items` (the locked week's
  client-safe facts, then the tracker's for an item that became client-visible since), tag text from the item's client title, and
  `based_on` from `report_doc.baseline`. It fails closed: no facts means no items, tags or based_on.
- **Headings:** a draft keeps its own `layout.headings`. A filed or exported file's headings are made from its sections
  (`report_doc.filed_client_data`). Save remembers only the headings the sections also show (`report_server.remembered`), so a
  word stored only in one report's layout can't become the next report's shown heading.
- **P7:** `creaite_doc.client_shape` now also allow-lists inner keys: item keys (`ITEM_KEYS`), a creaite client table's own columns
  (`report_doc.CLIENT_COLUMNS`), row cells limited to the columns, a row source only `added`, layout lists of strings, row rules
  `{top: int}`, and header dates `YYYY-MM-DD`.
- **P16:** `client_output.loose_findings`, `fold_words` and `_loose_refs`.
- **K5:** `logo_check.clean_svg` keeps no `<text>` or `<tspan>` at all, drawn or not. This was the safer of the two choices:
  rejecting such a logo would leave the report with no logo, while dropping the words leaves the shapes. A wordmark should be
  uploaded as shapes or a PNG.
- **Missing snapshot test:** `test_snapshot_export_renders_the_snapshot_not_the_file_read_again`. The draft is changed on disk
  after the snapshot's check, and its mutant (render from the file) puts the late words in the export.
- **Properties:** `P16out` (mutant `loose_off`) and `P18facts` (mutant `facts_off`) are new. P7's unknown keys now also go into
  cells, columns, tags, figures, panes, header data, layout headings and row rules, and based_on, and half of them hold only words
  no gate knows.
- **Mutation proofs:** K2 and apply's second check are extra guards, so some proofs now switch them off as well: `trust_on` (every
  file read as creaite's own) for P11, P13, P13shared and P23; `apply_check_off` (in tracker.py's own process) for P23; and
  `allow_off+facts_off` for P7. P8, P9, P10 and P16 stay green with their mutants. That was already so on `origin/v253-release`
  (checked in a scratch copy), so it isn't caused by this branch.
- **Existing tests that follow K2:** none of their leak assertions changed. A payload written on disk now also goes in the Summary,
  which every output shows (`test_client_audience.tamper_on_disk`; step 2's hand-edited filed file). A client text section is
  added through Save (`test_client_output_step2.client_text`). The gap B mutant (step 3) also switches off the new loose check,
  which reads other projects' hidden wordings too.
