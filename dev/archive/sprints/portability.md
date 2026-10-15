# Sprint portability: one interpreter, gh downloads, the vendor manifest, the Brewfile, the rule, the CI matrix (BL-237 to BL-242)

Branch `sprint-portability`, worktree `../creaite-portability`, from `main` (which has BL-243, the login agent). **For v1.6.1** (Alan, 11-10-2026). Read BL-237 to BL-243 in `dev/BACKLOG.md`, BL-141 in `dev/BUILD.md` (Sprint admin: the guard, the never list, the one-time approvals), and `dev/SETUP.md`.

## Order: one commit per item, each change in a marked block (`# ===== BL-23x (sprint-portability) =====`)

1. **BL-240: Brewfile.** `dev/Brewfile` pins `gh`, `git` and the Python used for tests. Add a note in `dev/README.md`. It is development only and stays out of the release zip; check `paths.ENGINE` and `build_release.py`.
2. **BL-239: Vendor manifest.**
   - SHA-256 for every file in `system/scripts/vendor/`.
   - A `dev/tools/` script that rebuilds the manifest when a library is deliberately upgraded.
   - A `doctor.py` check that fails on a missing, changed or extra file.
   - A line in `vendor/README.md`.
   - **Tests:** a clean vendor passes; a changed, missing and extra file each fail; doctor's count changes, so update the tests that expect "24 of 24", and say so in the report.
3. **BL-238: `gh release download` in update.**
   - `update.py` (and cx-setup's update step) can fetch the newest release zip with `gh release download` into `system/releases/`, then carries on as now: shown first, confirmed, installed, with the checksums verified.
   - If `gh` is missing or not signed in, it says so plainly and falls back to the manual download.
   - **Never add a general `Bash(gh *)` permission rule:** the call goes through `update.py`, so the rule stays one creaite script run on its own (BL-141). Inbound only.
   - **Tests:** use a stand-in `gh` on PATH; never contact GitHub from a test.
4. **BL-237: one interpreter wrapper (take the most care here).**
   - **The wrapper:** a small wrapper in the vault picks the newest Python 3.9 or later once and runs the script.
   - **Who calls it:** the launcher, the login agent, the sweep and the hooks.
   - **The permission rules** name it once, instead of a `python` and a `python3` copy of every rule.
   - **What changes together:** `reach.py`'s hook ("one creaite script run on its own"), `permissions.py`, and `live_server.py`'s allow lists. Change them with their tests.
   - **What the wrapper must refuse:** anything that isn't a creaite script in `system/scripts/` (no `-c`, no `-m`, no other path, no extra command) and anything on the never list.
   - **BL-141 must not be weakened in any way:**
     - every existing refusal test in `test_reach.py`, `test_permissions.py`, `test_admin_card.py` and `test_ask_shell_shapes.py` still passes **unchanged**;
     - add tests that try to escape through the wrapper.
   - **Updates:** existing vaults' `python`/`python3` rules keep working, because an update only adds rules.
   - **Ship the template, not the dev copy:** edit the **shipped template** `.claude/settings.json` only as committed. Never commit the working copy's changes in the main repo: Alan's dev copy there is modified and must never be committed.
   - **If any step would loosen the guard, stop and report** instead.
5. **BL-241: the portability rule.** Rewrite `system/creaite-rules.md`'s Portability section in the three tiers BL-241 sets out.
   - **Windows:** best effort, untested (Alan's decision).
   - **The never list** names macOS places only.
   - **Keep:** the "Runtime never pip installs; dev tools may be installed" line (Alan) and the login agent line.
   - **Also update:** `dev/SETUP.md` to match.
6. **BL-242: CI matrix.**
   - Run the suite in `.github/workflows/tests.yml` on Python 3.9 and 3.14 (Ubuntu).
   - Add a macOS job marked `continue-on-error`.
   - **Manual dispatch only:** add no push or pull-request trigger, because BL-234 stays parked by Alan.
   - Keep the `files` input. Workflow permissions read-only, and never `pull_request_target`.
   - Check that the release workflow is unaffected.
7. **Docs:** a BUILD "Sprint portability" section with the FR text, the Help or guides where a user sees a change (update via gh), and lines under "## Changes" in `dev/release-notes/1.6.0.md`, plus hand checks.

## Rules

- **Others are building beside you:** ui-audit (security headers) and drafts-fields (draft routes) also change `live_server.py`, and debt-safety changes `review.py`, `report.py` and `tracker.py`'s connect. Keep your changes small and marked.
- **Tests:**
  - your own tests;
  - every file that mentions `reach`, `permissions`, `update.py`, `doctor`, `launch.py`, `vendor` or `python3 system/scripts`, run in full, not sampled;
  - use `-j 2` at most;
  - one pass is enough; a file that fails under load and passes alone counts;
  - tests also run on Linux;
  - stop only your own processes, by PID; never `pkill` by name.
- **Safety:**
  - Never run a real `launchctl`, `gh` against GitHub, `brew install` or `pip install` from tests.
  - Don't install anything on this Mac.
  - Development repo only: sample data, no Microsoft 365.
- **The usual edit rule:** don't edit `dev/BACKLOG.md`, `dev/BRD.md` or `dev/archive/sprints/STATUS.md`. Never push or merge. No schema change.

## Done when

All six items are committed, and their tests and the related files pass, with every BL-141 refusal test unchanged. Help, SETUP, the rules, BUILD and the notes are current. The report lists Alan's hand checks and the new doctor count.
