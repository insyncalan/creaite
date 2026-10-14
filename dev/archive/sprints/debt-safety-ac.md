# Sprint debt-safety (parts A and C): the client-safe check fails closed, and the swallowed exceptions (BL-228)

Branch `sprint-debt-safety`, worktree `../creaite-debt-safety`, from `main`. **For v1.6.1** (Alan, 11-10-2026). Read BL-228 in `dev/BACKLOG.md`. **Build parts A and C only:**
- **Part B** (the ratchet) belongs to creaite-41's `check.py`.
- **Part D** (escaping by default) comes later, once the dashboard sprints have merged.

No change to what Alan sees.

## Order: one commit per part, each change in a marked block (`# ===== BL-228 (sprint-debt-safety) =====`)

1. **Part A: the client-safe check fails closed.** Do exactly what BL-228 A says, with its tests:
   - `client_findings` in `review.py` skips the check **only** for "no such table";
   - any other error becomes a finding in words;
   - read every `except` on the client-report and Steerco client-safe paths (`report.py`, `review.py`, `docx_tools.py`) and fix any that skip a confidentiality check.

   List each one you read and what you decided.
2. **Part C: triage the swallowed exceptions.**
   - **The ones that are right:** keep each and give it a one-line reason comment.
   - **Narrow the broad ones** BL-228 C names, and log the rest at debug level: names and counts only, never message text (BL-102).
   - **`review.update_parts`' `SystemExit`:** give `tracker.py` a connect that raises a normal error. Keep that change small and in a marked block, because creaite-41's BL-229 will split other parts of `tracker.py` later.
   - **Tests:** as BL-228 C says.
3. **Docs:** a BUILD "Sprint debt-safety (A, C)" section with the FR text (fails closed; every silent `except` has a reason), and one line under "## Changes" in `dev/release-notes/1.6.0.md`.

## Rules

- **Others are building beside you:**
  - ui-audit and drafts-fields touch `live_server.py`;
  - insight and drafts-fields touch `review.py` and `build_dashboard.py`;
  - portability touches `doctor.py`, `update.py` and `permissions.py`.

  Keep each change small and marked. Don't reformat or move code you aren't changing.
- **Never weaken a check:** a confidentiality guard must fail closed. If a change would hide an error from Alan, stop and report.
- **Tests:**
  - your own tests, plus every test file that mentions `client_findings`, `client_safe`, `steerco`, `report.py`, `review.py`, `connect(` or the functions you narrowed;
  - use `-j 2` at most, because seven sprints are testing;
  - one pass is enough; a file that fails under load and passes alone counts;
  - stop only your own processes, by PID; never `pkill` by name.
- **The usual edit rule:** don't edit `dev/BACKLOG.md`, `dev/BRD.md` or `dev/archive/sprints/STATUS.md`. Never push or merge. No schema change.

## Done when

Parts A and C are committed, and their tests and the related files pass. The report lists:
- each `except` you read on the client paths, with its decision;
- each swallowed exception, with its decision;
- the tests and their results.
