# reach.py: two read-only scripts classified (2.6.4, line-reach)

`reach.diff` (guarded; one file, `system/scripts/reach.py`, +2 lines) adds two entries to `SCRIPT_COMMANDS`, both `READ`:

- `ai_budget.py` (#334): this week's AI budget figures; reads the usage log, writes nothing.
- `start_tokens_report.py` (#339 A0): start tokens per run kind; reads the usage log, writes nothing.

Without them `test_record_commands` fails ("every script with a command line is classified"), and an unconfirmed ask creaite chat would
be told it may not run them (an unknown command is declined, so the failure is safe, not open).

## Risk (for the reviewer)

Classing a script as `READ` lets an unconfirmed chat run it with no card. Both only read counts from the usage log and print them; neither
has a command that writes. The test below holds both to `read` (not stage, guarded or record) and checks that a one-word change to
`record` turns it red.

## Order

Last in the 2.6.4 chain: 345, 346, 334, then this. It touches a different file, so it goes in at any point. Tests:
`dev/tests/test_reach_line_entries.py` (works with or without the diff in the tree: it puts the diff on a copy of `reach.py`);
`test_record_commands` passes with it (run on a tree with all four diffs).
