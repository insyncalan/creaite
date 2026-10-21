# #259 client-output leaks K2, K3, K5, P7, P16, P18: guarded proposals

v2.5.3 closes Team Cap's leaks still open after 2.5.2 (the verdict on #239, 20-10-2026) and Cap's NOT READY findings on c25a28fe
(#259, 20-10-2026, 23:18: round 2, below). The unguarded part is on branch `v253-client-k` (see `dev/tests/test_client_output_k.py`
and `dev/tests/test_client_output_k_round2.py`). One guarded file needs a change: `client_leak.diff`, which Cap asks for.

Correction (round 2): the first version of this README said "the output check already keeps every form out of every client
file". That was not true. The output check (`client_output.text_findings`) reads the P16 forms for every creaite-format client
file, but the Word client body (the client-safe steerco one-pager, older Word client reports: `review.client_findings` to
`client_leak.plain_findings`) and AI client drafts (`edit_ai.client_problems`) did not. Round 2 closes both in unguarded code
(`review.word_output_findings` and `edit_ai._loose_problems` call `client_output.loose_findings`), and the diff puts the same check
in the gate itself.

## 1. `client_leak.diff` (P16 at the gate; wanted by Cap, MEDIUM 3)

`client_output.loose_findings` (new, unguarded) finds a hidden item's ID however it is written ("A B C - A - 0 0 1",
"ABC-A-0001", "ABC-0005", "ABC-5", "abc.a.001") and a hidden wording with hyphens, dots or underscores for its spaces
("Vendor-exits-the-market-before-go-live"). Every creaite-format client output's check calls it (`client_output.text_findings`: export, Approve's
filed file and tracker.py apply's second check), and since round 2 so do the Word client body's check and AI client drafts.

The diff makes the gate itself (`client_leak.text_findings`, which `client_leak.findings`, the snapshot's check and Save's
"left out" list read) call it too. That gives P16 in its strict form: gate(f(x)) refuses exactly when gate(x) refuses, and Alan
sees the finding while he edits rather than only when he exports.

- Apply: `git apply dev/proposals/client-output-k/client_leak.diff` (it passes `git apply --check` on `v253-client-k`).
- Test: `test_client_output_k.K.test_p16_gate_reads_the_loose_forms_once_the_guarded_diff_is_in` is an expected failure until
  the diff is in. It works out by itself whether the diff is applied, so it passes once it is, with no edit to the test.
- Verified (round 2): `git apply --check` and, once applied, `git apply -R --check` both pass on the branch head; applied in a
  scratch copy, `test_client_output_k.py` (18, no expected failure left) and `test_client_output_k_round2.py` (24) are green.
- Round 3 (Jarvis, 21-10-2026): with the diff in, `test_client_gate`'s "ABC A 4/10 is the review day." was read as ABC-A-004 (a
  false positive). `client_output._loose_refs` (unguarded) now skips digits that are a fraction, date or time (a number then `/`,
  `.`, `-` or `:` and a digit: "4/10", "4/10/2026", "12.5", "4-10", "4:10"), but only when that first number is one or two
  digits with no leading zero, and not three or more digits spaced one by one ("1/2/3"). Cap's HIGH on this: "ABC-A-0001/1" and
  "A B C - A - 001.5" let ABC-A-001 through, so a leading zero or a longer first run stays an ID ("0001/1", "001.5", "001-5",
  "001/2026", "01/1", "0/0/4"), and the digits before the first mark are read as a number too ("0 0 1.5" is 001). "A B C - A -
  0 0 1", "ABC-A-0001" and "ABC A 4." still block. Tests: `test_client_gate.TextFindingsMatchesEveryId` (the false positive
  and its variants; the loose and padded forms still found), `test_client_output_k_round2.test_l6_a_padded_id_*` and its
  control, and four more `f_loose_id` forms in the P16out property. The diff also moves the memory, chase-log and label checks into
  `client_leak._context_findings`, so `text_findings` stays within check.py's complexity limit (`check: OK` with it applied).
- It errs towards over-blocking: `client_leak.make_safe`, which strips the parts the gate finds, then also strips a part holding a
  loose form. That is the wanted direction.

## 2. tracker.py apply's second check of a creaite-format client report: no diff needed

Cap's LOW finding: `tracker.py apply` re-checked only Word client drafts. `tracker.client_draft_problems` already calls
`review.client_apply_problem(blk, "report_decision")` on every approved report block. That function returned early for a
creaite-format draft (`word_draft`). It now hands a creaite-format client block to `review.creaite_client_problem`, which:

- refuses a client report filed by a `copy` (the draft as it is on disk), or without exactly one filed write and one snapshot write;
- checks the staged write as a filed report is checked (`client_output.filed_findings`: page text, every data-block string and the
  pictures);
- refuses it unless the snapshot written beside it is one the registry recorded at approval and names that write's SHA-256 as its
  source.

That was not enough (Cap, round 2, HIGH 2): the function took the block's own `kind`, `version` and `format` as given, so a staged
proposal edited to `kind: weekly`, or with `format` removed, was filed with a hidden ID in it, and an extra write (a `.md` or `.pdf`
beside the report) was never checked. Round 2 fixes it in `review.py` (unguarded; tracker.py calls it, so tracker.py stays as it
is). See "Round 2" below.

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
  run; or, for a filed report, the source hash of the snapshot Approve wrote beside that file (round 2: never a snapshot an
  export built). Any other section that isn't one of creaite's own client sections is internal.
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
  `allow_off+facts_off` for P7. P8, P9, P10 and P16 stayed green with their mutants (already so on `origin/v253-release`), because
  a second guard gave the same protection; their mutants and P8's cases are now widened, and all 26 go red under their mutants:
  - P8 (`signs_off`): the minutes route refused a client report by its file name before `report_signs` was reached. P8 now also
    exports a minutes-named copy of the client report from drafts (source `renamed`), where only the report's data gives it away.
  - P9 (`names_off`): `name_problem` (in `_settle_name`) repeats `_name_problem`; the mutant switches off both.
  - P10 (`page_used`): step 3's guard is three deep (the client export route sends no page, `_posted_page` returns none for a
    client report, `export_page.build` refuses one); the mutant passes the posted page through all three.
  - P16 (`decoder_off`): the look-alike decoder is in `edit_ai.LOOK_ALIKE` and `confusables.TABLE`; the mutant filters both. Only
    the look-alike form depends on it, so it fails 1 to 3 of the 30 proof cases (seeds 239 and 1 to 4), never none.
  - P22 (`match_raw`): on seed 2 the mutant's raw check crashed on a malformed document (a list where the code goes), which
    stopped the proof run and left P23 green after it. The mutant now reads such a document as sent and finds nothing, as an
    unchecked route would; P22 and P23 then go red on seed 2 as on 239.
- **Existing tests that follow K2:** none of their leak assertions changed. A payload written on disk now also goes in the Summary,
  which every output shows (`test_client_audience.tamper_on_disk`; step 2's hand-edited filed file). A client text section is
  added through Save (`test_client_output_step2.client_text`). The gap B mutant (step 3) also switches off the new loose check,
  which reads other projects' hidden wordings too.

## Round 2: Cap's NOT READY findings on c25a28fe (#259, 20-10-2026, 23:18)

All unguarded; tracker.py and client_leak.py are unchanged (the diff above is the only guarded change). Tests:
`dev/tests/test_client_output_k_round2.py` (24) and the new property `P26twice`. Each leak test was run on the pre-fix tree (the
branch with `v253-release` merged, 632719f4) and failed there (32 failures, 3 errors; the controls passed); each has a mutant that
puts the old behaviour back and goes red.

- **HIGH 1, trust laundering.** `creaite_doc.creaite_wrote` now trusts a filed report only through
  `client_snapshot.approved_source(path)`: the snapshot at `beside(path)` (the path `filed_snapshot` gives), its registry entry
  made by Approve, its bytes a hash that entry recorded, its `state` filed and its `source.path` that same filed path. The
  registry marks how each entry was made (`made`: `approve` from `for_filing`, `export` from `ensure`); an export's rebuild is
  never a source of trust. Tests `test_h1_*` (html and docx, three export orders, the export route, the registry's marks, a
  snapshot copied beside another name); property `P26twice` (approve, edit the filed file on disk with a text section marked
  client, export two to four times in random html/docx order: no export holds it). Mutants: `test_mutant_h1_*` and P26twice's
  `launder_on` (c25a28fe's `any(state == filed and source_sha256 == digest)` put back: 19 leaking exports in 12 cases, always a
  later export, never the first).
- **HIGH 2, the apply re-check.** `review.client_apply_problem` derives whether a report block files client output from its
  files (`files_client`: a client report's or client one-pager's name, a client snapshot, the client reports folder when it isn't
  also the weekly one, a write holding a creaite client document, a draft that is one or holds the client-safe one-pager's own
  line), and the format the same way (`creaite_files`). A creaite-format client filing may run exactly Approve's three ops: one
  write of the `.html` at the report's own filed path, its snapshot at `beside(that path)`, and the removal of the report's own
  draft; anything else (a `.md` or `.pdf` write, a copy, a move, a mkdir, a renamed target) is refused. A Word client filing may
  run only one copy of the `.docx` draft, a mkdir and the draft's removal (`word_ops_problem`). The steerco client to internal
  switch is caught by the draft's name `(client)` and its body line "Client-safe version.", so it needs `checked_sha256` and the
  check like any client file. Tests `test_h2_*` through `tracker.py apply` (kind weekly, format removed, both, both without the
  snapshot, kind steerco/internal, extra `.md`, extra `.pdf`, extra `.md` with kind weekly, an extra copy, the write moved; the
  steerco switch with the target renamed or the kind removed), controls (the untouched proposal and an internal one-pager are
  filed). Mutants `test_mutant_h2_*` (the old re-check files kind weekly, format removed, the extra `.md` and the switched
  one-pager).
- **MEDIUM 3, P16 outside the output check.** The Word client body (`review.word_output_findings`, which `client_findings`
  calls) and AI client drafts (`edit_ai._loose_problems`, from `client_problems`) call `client_output.loose_findings` on the
  text, its skeleton and its JSON escapes read. `client_leak.diff` (section 1) puts the same in the gate. Tests `test_m3_*` (the
  steerco Word body and AI drafts: "A B C - A - 0 0 1", "ABC-A-0001", the hyphenated title; clean controls); the steerco Word body
  test runs with or without the diff, as the unguarded check closes it either way. Mutants `test_mutant_m3_*`
  (`loose_findings` switched off: every form passes again).
- **MEDIUM 4, K3 leftovers.** `creaite_doc._shape_section` derives `default_heading`: creaite's own heading for one of its own
  client sections (id and type in `report_doc.SECTIONS`), `""` for any other. `_shape_layout` keeps a list value only when it is
  known (`_layout_known`): `order` and `hidden` a section id (creaite's own or one of the document's), `glance` a
  `report_doc.GLANCE["client"]` key, `logos` a kind the project has (`report_doc.logo_kinds`, plus the bare `partner`),
  `milestones` one of the project's item IDs; `headings` and `rows` keyed by a known section id. Tests `test_m4_*` (sent to Save
  and edited on disk; a control that the known values are kept). Mutant `test_mutant_m4_*`.
- **MEDIUM 5, accepted by design (residual).** creaite's own client text sections (Summary, Progress, Next steps) in a filed file
  edited on disk are still shown, guarded by the word gate and the output check only: they are the report's own words, and
  holding them back would leave a filed report with no body. HIGH 1 made this worse (on a later export the whole edited file was
  trusted, so added text sections showed too); with HIGH 1 fixed, an edited filed file's added sections are held on every export,
  so the residual is only words no gate knows typed into creaite's own sections of a filed file outside creaite. Closing it fully
  needs the export to render the approved snapshot even when the filed file changed (refusing the edited file instead); that is
  a behaviour change for Alan to decide, not made here.
- **LOW 6, P16 edges.** Up to eight separators between an ID's letters (was four), up to six between its digits, any of them
  `/`, `,` or `·` (was spaces, dots, underscores and hyphens, up to three), and a zero-width or format character read both as
  nothing and as a space when a wording is matched. Tests `test_l6_*` with controls (a date after the code, a list of numbers,
  "A B C 1 2 3 4").
- **LOW 7, an unreadable draft.** `creaite_doc.read_raw` answers a file it can't open with a DocError sentence,
  `client_snapshot.ensure` a filed file with a SnapshotError, and `report_server.guarded` turns any other OSError into a refusal
  (no HTTP 500). Still fails closed: no file is written. Test `test_l7_*` (export, approve and draft routes).

- **Found while testing round 2.** `report_doc.client_facts` never closed its tracker connection; K3 calls it on every clean,
  so `test_client_gate_reviews`' connection count went from equal to 9 opened, 3 closed on c25a28fe. It now closes it. `clean`
  shapes the layout again after it drops the internal text sections, so it stays a fixed point (P3) with MEDIUM 4's lists.
  `test_client_gate_reviews`' planted item title now expects the finding or the title gone from the cleaned document: since K3
  an item's stored values are the tracker's facts, so the planted words never reach the gate or an output. A weekly report's
  data names a `client` logo kind, so `files_client` reads a write's or draft's kind from its data block, never a loose match.
