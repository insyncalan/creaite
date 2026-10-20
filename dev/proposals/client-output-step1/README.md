# Proposal: the client gate reads every text in its folded forms, and other projects' hidden items (v2.5.1 step 1, #239)

For Jarvis to apply. `client_leak.py` is guarded, so this is NOT applied; `client_leak.diff` is the change
(`git apply --check dev/proposals/client-output-step1/client_leak.diff` passes on branch v251-step1).

## Why

Step 1 closes the HIGHs outside the guarded files: the output of every client export (and the file Approve files) is checked again
after it is made (`client_output.check` / `filed_findings`), and that check already reads text through the confusables skeleton,
JSON `\uXXXX` escapes, and other projects' hidden wording and owners. The document gate itself (`client_leak.findings`) still
reads only the plain and %-/entity-decoded forms and only the report's own project, so:

- a JSON-escaped hidden word (`Internal only`, `Escalate ...`) passes the gate: property P16json fails today (an
  expected failure in `dev/tests/test_client_output_properties.py`); the output check keeps it out of every file;
- another project's hidden item wording, or a person who owns only another project's internal items, passes the gate (proposal
  line 3, "B", of `dev/proposals/audience-bypass/README.md`); the output check refuses the export or the filing instead, so the
  user learns late (at export, not in the sheet's check).

## The change (client_leak.diff)

1. `folded(text)`: the text joined with `confusables.skeleton(text)` (NFKC, invisible and format characters gone, look-alike
   letters of Cyrillic, Greek, Armenian, Lisu, Cherokee and small capitals made Latin, before and after NFKD/NFKC) and
   `client_output.unescaped(text)` (JSON escapes read).
2. `findings` reads `folded(doc text)`; `internal_findings` folds its texts before the marker and health-reason checks; `marked`
   folds; `plain_findings` folds.
3. `findings` adds `client_output.other_project_findings(con, code, text)`: another project's not-client-visible wording (15
   characters or more) and its internal-only owners who are not people this report may name (this project's client-visible
   owners and Alan).

Both helpers live in unguarded modules (`confusables.py`, `client_output.py`), so the guarded change is small.

## Checked

With the diff applied in the worktree (then reverted): `test_client_leak`, `test_client_gate`, `test_client_audience`,
`test_client_gate_reviews`, `test_client_item_links`, `test_client_output_step1` all pass, and P16json passes (it then reports an
unexpected success: remove its `expectedFailure` when applying).

## Risk

- (3) can refuse a client report that names a person who owns only internal items in another project and none in this one; that
  is the point, but a shared supplier contact named on purpose would need a client-visible item or the people register's alias.
- The skeleton maps a few letters of real names in those scripts to Latin; both sides of every match are folded the same way, so a
  name still matches itself.
