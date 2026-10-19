# E1 interface: "Find work items" (builder E, branch p260-e)

For builders A and C. No tracker.py change is needed (no proposal diff).

## The command string (A: `irProcess` for a minutes file)

    process <file> as minutes by someone else

`<file>` is the inbox path or name, as `irProcess` already sends it for `process <file>` (for example
`process inbox/Vendor call minutes.docx as minutes by someone else`). The phrase after the file is exactly
`as minutes by someone else`, lower case, no quotes. It is in `.claude/skills/cx-minutes/SKILL.md` (description, Modes table,
section "Minutes by someone else"). A transcript row keeps the plain `process <file>`.

## What the engine stages (A and C: what the rows will see)

Spec `"as": "minutes", "file": "inbox/<file>"`; the proposal's `meeting` block has `kind: "minutes by others"`,
`minutes_decision: "approved"`, `draft: null`, `transcript: null`, `source_file: <inbox path>`, `file_ops` (a `copy` from the
inbox path to `<project minutes folder>/YYYY-MM-DD Title.ext`, then a `remove` of the inbox path) and `note: <first filed copy>`.
`staging-format.md` has the full block.

- Key `fp:<day>|<title>|<content hash>` (so a second add of the same file stages nothing: "Already processed", exit 3, and after
  an apply `system/processed.txt` holds the key and the filed path).
- The `meeting.note` field is set only because `tracker.py` treats a block with `note` as having no draft to file
  (`minutes_draft_missing`). `build_dashboard.py` (`quick = ... or bool(m.get("note"))`, `step_transcript`) therefore reads it as a
  quick note ("A quick note: no transcript"). A and C should test `meeting.kind == "minutes by others"` first where the wording
  matters (running words: "Reading for work items"; the Done row: "Already processed"). Not changed here (not E's file).
- Unmatched project: stage prints "No project matched" and exits 1 with the file left in `inbox/`; the skill asks Alan for the
  project before staging again (C/A: the row can offer the project picker, as for a transcript).
- Optional tidy-up for Jarvis (tracker.py is guarded, not needed for this to work): `minutes_draft_missing` could test
  `blk.get("kind") == "minutes by others"` and `build_dashboard.draft_missing` the same, and then `note` could be dropped.
