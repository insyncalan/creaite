# #250 guarded diffs G3 and G4 (2.6.10)

G3 is at **revision 2** (sha256 `920b91643838b92529ef19f8163c8b4c41095e7c986832fe98ce0ca0d098ed85`): `answered` also needs the stream's `result` event (not `is_error`) and a non-empty final answer, in the helper `Run._answered(proc, final)`. Revision 1 (`fb93369c...`) let an exit 0 with no answer write.

Patch files only; nothing guarded is edited in a commit. Chain: `dev/proposals/GUARDED-2.6.10.chain` (not pinned, no marked commit). Order: G1, G2, G3, G4.
Base: origin/main a62fbb0a. G1 (#382) and G2 (#371) are the 2.6.9 extra diffs on branch `v269-g12`.

| | File | Patch | sha256 |
|---|---|---|---|
| G3 | `system/scripts/live_server.py` | `dev/proposals/250/live_server-250.diff` | see below |
| G4 | `system/creaite-rules.md` | `dev/proposals/250/creaite-rules-250.diff` | see below |

(Hashes: `shasum -a 256` of the two files; the report that carried this README lists them.)

## G3: what it does (all inside `class Run`, one block `# ===== #250 ... end #250 =====`, plus four one-line hooks)

- `_start`: `self.fetch = self._fetch_for(kind, sweep)`. `_fetch_for` returns `transcripts.SweepFetch()` for a sweep run (`kind == "sweep"`, the catch-up and
  Close the day, or a typed sweep) when `transcripts.fetch_on()` (setting exactly true); else `None`. A construction fault gives `None` (logged by name).
- `_on_tool_result`: `self._fetch_observe(part)`. The helper hands `observe(name, input, text, is_error)` only the `read_resource` results (the tool name is
  `transcripts.FETCH_TOOLS[1]`, exact), the text being the server's own copy; a fault is logged by name and the reader goes on.
- `read()`: after the closure steps and `_finish_job`, before `_done()`: `self._fetch_finish(proc, final)`. `answered` (`Run._answered`, rev 2) = not stopped, not timed out, not failed,
  exit code 0, `usage_result` a dict without `is_error`, and a non-empty final answer. `finish(answered)` runs in try/except; its counts go through `fetch_text`. A typed sweep (not "plain") shows the line as a chat text; a run
  creaite started shows it in its closure: `_close` calls `_with_fetch_line` ("<the run's own line>. 2 transcripts fetched, ..."). `_done()` always runs.
- No new tool, no `--add-dir`, no allow rule, `KIND_TOOLS` unchanged, no `sweep.py done`, no `sweep-fetched.json`; counts only in the line.
- Complexity: `_on_tool_result` gains no branch; `check.py` clean (the long-line count stays at the limit).

## G4: the rules bullet (revision 2, sha256 `42a90418a4045f3ad2d71cfd93340fc9bfda74c7d338f30c92772f1f873b52f4`; revision 1 was `8552df1bfa8d8166fbc4dcc1998a20b80f18ea680e3c2cb80de4881f8712f7be`)

One bullet, "Transcripts fetched by a sweep (#250)", before the Assistant bullet, 625 bytes (revision 1: 1,099). Revision 2 matches the code (Cap's review):
off by default (exactly true); the live server writes the transcripts a sweep run **read** into `inbox/`, only once the run has answered; held back unless the saved
calendar and the event as read both say normal and no confidential or private meeting overlaps; the known gap (a closed event missing from the saved calendar:
private events dropped by default, ignore rules, declines, stale saves; and unread by the run); nothing reaches `system/tracker.db`, staging gets only `transcripts.json`
(times, counts); closure counts only. Removed: "nothing written to staging", "each finished transcript", "extracted".
Size: `test_rules_retained_338` leaves this bullet out of both sides of its half-size check, so it uses none of that margin (74 bytes spare on the 2.6.8 file, measured);
no trim elsewhere is needed for this line. Every sentence tried as a trim (the prep_page clause, the one-off Word sentence, the Prep pages sentence) is pinned by that test.
It needed an ordinary test change: `dev/tests/test_rules_retained_338.py` now knows the 250 bullet (stripped before the 338 state is worked out, put back on
both sides, and left out of the half-size check, whose margin is a few bytes).

## Apply order (git apply --check and apply, in a throwaway worktree of this branch, clean in every case)

G3 alone on main; G1, G2, G3; G3, G1, G2; G1, G3, G2; G2, G3, G1. G3's hunks do not touch G1's or G2's. G4 applies on main alone.
G1 on its own makes `test_run_tools_explicit.test_tool_less_kinds_see_no_claude_md_and_no_memory` fail (it pins the old cwd); that is G1's test change
(`tests-followup`), not G3's.

## How verified

Throwaway worktree with G1+G2+G3+G4 applied: `py_compile`; `dev/tools/check.py` OK; `test_live_fetch_250` (26), `test_transcripts`, `test_fetch_transcripts`
(+ hostile), `test_fetch_settle`, `test_transcript_hold`, `test_job_prompts_365`, `test_job_tools_365`, `test_fresh_ask_327`, `test_lighter_runs_339`,
`test_held_edit_deny`, `test_guard_pinned`, `test_run_read_pinned`, `test_live_*`, `test_guarded_chain`, `test_rules_pointers_338`,
`test_rules_retained_338`, `test_intake_review_rules`, `test_no_real_names`: all pass.
Mutants (a mutated copy of the patched file, each run against `test_live_fetch_250`; all 16 fail the test; rev 2 adds 5 more, one per clause of `_answered`: ended_well, returncode, isinstance, is_error, final; all killed): fetch not assigned; non-sweep kinds get a fetch;
setting ignored; observer not called; observer gets every tool; finish always `True`; timed-out, stop, exit-code, failed flag each not considered; finish
outside the try; finish not called; finish after `_done()`; closure line not joined; typed sweep shows no line; counts dropped.
