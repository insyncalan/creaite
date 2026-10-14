# Repo migration, end to end

The one plan for moving creaite to its post-migration way of working (14-10-2026). It covers the code move, the clean-up, the private board and the handover to the Head of Product and Delivery. **Written by the Scrum Master and the Product Manager together; the Scrum Master runs it.** **Trigger (Alan, 14-10-2026):** development carries on until v1.9.3 is published; the migration then starts at once (no fixed slot), with a short **go/no-go from Alan** first, because step 0 makes the repo private. v1.9.3 was published at 18:58 on 14-10-2026, so the remaining gate is the precondition that matters most: **`dev-no-real-names` merged and the guard green**, since the new repo starts from that tree.

**No real names.** This repo is public. Nothing in this file, in a commit message or in an archived file names a real client, company, project or person (Alan, 14-10-2026).

## The end state

- **Code:** in a **fresh** public repo `insyncalan/creaite` (same name, so `update.py`'s `RELEASE_REPO` and every link keep working) that starts from the scrubbed `main` as **one root commit with no earlier history**, so no real name survives in it. `main` holds every published release; only in-flight branches are carried over.
- **The old repo:** renamed `insyncalan/creaite-history` and made **private** (kept, Alan, 14-10-2026). It holds the full history, every old branch and tag, the old SPRINTCOMMS and the old release zips.
- **Plan:** in the private repo `insyncalan/creaite-plan`. One issue per backlog item, a private GitHub Project board, and one milestone per release plus Unscheduled.
- **`dev/BACKLOG.md`** is a read-only export of the board.
- **STATUS, SPRINTCOMMS and BUILD-WATCH** are retired.
- **`dev/`** keeps only living documents. Shipped notes are in `dev/archive/`.
- **The Head** (a fresh session, from 15-10-2026 08:00) owns the board, the release plan and the digests, under the delegation charter. A team lead on each laptop runs that laptop's build agents.

## Before "go migration"

- [ ] Alan has run `gh auth refresh -s project` (the Project board needs it).
- [ ] Every build agent on both laptops is at a commit and has pushed. No agent is mid-edit.
- [ ] `dev-no-real-names` is merged: the scrub and its banned-names guard test.
- [ ] Every open docs branch is in `main`, so the backlog text is complete. As of 14-10-2026, `dev-archive-security`, `dev-bl326-v210` and `dev-decisions-1to4` show as not merged; the earlier docs branches were copied in.
- [ ] A safety tag on the old repo's `main`: `pre-migration-2026-10-14` (it goes private with the old repo).
- [ ] The v1.9.3 release zip is attached (the last release built in the old repo).
- [ ] Every branch to carry over passes the banned-names guard test (`python3.14 dev/tools/run_tests.py test_no_real_names` on that branch).
- [x] Alan has agreed the clean-up inventory (Phase B) (14-10-2026: "clean up agreed").

## When development stops and restarts

Development doesn't wait for the board (Alan, 14-10-2026).

- **Stops:** at Phase A step 1, the freeze: straight after Alan's go (work-in-progress commits, push, stop: about 5 to 10 minutes), once both teams have posted "frozen".
- **Restarts:** on each laptop as soon as step 8 is done there (its re-clone made and its branches carried over), about 45 minutes after the freeze. Each laptop's lead posts "resumed" in the fresh SPRINTCOMMS. Building can restart before step 7's suite run is green; **cutting a release waits for it.**
- **Alongside the restarted development:**
  - **Phase B** commits to the new `main` touch only `dev/` docs and `dev/archive/`. It archives only **shipped** releases' notes; a note for an in-flight branch (v1.9.4, v1.9.5, v2.0.0, BL-331) stays where it is until that release ships, so feature branches don't clash with it. Worktree removal happens in the old clone.
  - **Phase C**: only edits to `dev/BACKLOG.md` stay paused, until step 15. Builders carry on.
- **One reason a laptop might wait longer:** a branch that fails the banned-names guard at step 6 isn't carried over until it's scrubbed; its team carries on with its other branches meanwhile.

## Phase A: the code move (Scrum Master)

Checked 14-10-2026: the old repo has 0 forks, 0 stars and 0 Actions secrets, and its name appears in code only as `update.py`'s `RELEASE_REPO` (and its tests), so keeping the name means no code change. About 1.5 to 2 hours; both teams are frozen for about 45 minutes of it.

0. **First, the moment Alan says "go migration": make the old repo private** (Alan, 14-10-2026: "when time comes", not before). Tag `pre-migration-2026-10-14` on its `main` first; tell both teams in SPRINTCOMMS; then `gh repo edit insyncalan/creaite --visibility private --accept-visibility-change-consequences` (visibility only; the rename to `creaite-history` stays at step 3, so every signed-in push, fetch and `gh` command keeps working). Check from a signed-out browser that the repo and its releases no longer show. Until the new public repo exists: Actions uses the account's private-repo minutes (hold back re-runs), and signed-out links (release downloads, raw URLs) fail.
1. **Freeze (quick: about 5 to 10 minutes).** Both teams were warned in advance that the freeze follows straight after the trigger. The instruction is: **commit whatever you have as a work-in-progress commit, push, and stop**; interrupted test runs are re-run after the restart. Each team posts "frozen". The Scrum Master records each laptop's in-flight branches and their heads in the Log below.
2. **Last checks.** The preconditions above are ticked; every branch to carry over passes the guard test; `main` passes the guard test over the whole tree (and the v1.9.3 release zip's contents).
3. **Retire the old repo.** The tag and the private flip are already done (step 0); rename `insyncalan/creaite` to `insyncalan/creaite-history`; make it private. Check from a signed-out browser that `github.com/insyncalan/creaite-history` is not visible.
4. **Create the new public `insyncalan/creaite`**: issues off (the plan lives in `creaite-plan`), wiki off, default branch `main`. From the scrubbed `main`, make one root commit (`git checkout --orphan`, commit the whole tree with the message "creaite at v1.9.3: fresh public history (14-10-2026)") and push it as `main`.
5. **Recreate the releases (scrubbed only).** A scan on 14-10-2026 found **real names inside the published zips** v1.7.0 to v1.9.2 (shipped skills, `drafts.py`, a drafts template), so **no old zip is ever uploaded to the new repo**: the old releases and their zips stay only in the private `creaite-history`. The new repo gets **one release**, rebuilt from the scrubbed root commit by the Release zip workflow (which runs the suite and attaches the zip), and its zip is checked with the banned-names guard before the release is published. Its version is **v1.9.3** (Alan, 14-10-2026: numbering kept; no restart at v0.1, no jump to v2.0.0). `update.py fetch` picks the newest release, so Alan's live vault is unaffected. (The v1.9.1 and v1.9.3 release notes in the old repo were scrubbed in place on 14-10-2026.)
6. **Carry over the in-flight branches.** For each branch in the Log: take its diff against the old `main` it was based on, apply it on the new `main` as **one commit** with a message naming its BL and the old head, run the guard test, and push. Branches not carried over stay only in `creaite-history` (this replaces deleting merged branches; see Phase B). `sprint-comms` starts fresh with one entry: "moved; the old log is in creaite-history".
7. **Turn on Actions and run the suite once on the new `main`.** It must be green (the three old date tests are already fixed on main).
8. **Both laptops re-clone** the new repo into a new folder, recreate only the worktrees they need, and confirm `git log` shows the one root commit. Old worktrees and the old clone are kept, untouched, until Done when is ticked, then removed (Phase B).
9. **Verify and log.** No banned name anywhere in the new repo (the guard test on every branch); `update.py fetch` lists the releases; the Log below has each step's time and result; the Scrum Master posts "migration done" in the fresh SPRINTCOMMS.

## Phase B: the clean-up (agreed list first)

Rules:
- Nothing is lost: everything removed stays in the private `creaite-history`, and anything uncertain is moved to `dev/archive/`, not deleted.
- One commit per category, so each can be reviewed and reverted.
- The full test suite passes afterwards, because some tools and tests read files under `dev/`.
- Clean up after Phase A, in the new repo, so moving files doesn't conflict with the branches being carried over.

| Category | What's there (14-10-2026) | Proposed action |
|---|---|---|
| Build notes at the top of `dev/` (`V18-…`, `V19…`, `V190–V193-…`, `DEV-…-NOTE.md`) | 37 files | Shipped releases' notes move to `dev/archive/notes/<release>/`. Notes for releases not yet published stay until they ship; after the migration, a note lives on its item's issue |
| `dev/sprints/` | 75 files, including `STATUS.md`, `DECISIONS-FOR-ALAN.md`, `TEMPLATE.md`, two `.patch` files and briefs for shipped sprints | Shipped briefs and the `.patch` files go to `dev/archive/sprints/`. `STATUS.md` is retired (the board replaces it). `DECISIONS-FOR-ALAN.md` goes to `dev/archive/` and seeds `dev/HEAD-LOG.md`. `TEMPLATE.md` and in-flight contracts (for example `BL-322-contract.md`) stay until their release ships |
| Comms and hand-over files | `SPRINTCOMMS.md` (branch `sprint-comms`), `BUILD-WATCH.md` (local, git-excluded), `HANDOVER.md`, `START-HERE.md`, `V18-LAPTOP-GUIDE.md` | `sprint-comms` gets a last "moved to the board" entry and is then left frozen (not deleted). BUILD-WATCH is deleted locally. `HANDOVER.md` and `START-HERE.md` are replaced by one short `dev/HOW-WE-WORK.md` that points to the charter, the board and `dev/HEAD-LOG.md`. The laptop guide goes to `dev/archive/` |
| Old one-off files at the top of `dev/` | `check-baseline.json`, `wrappers-inventory.json` and similar | Check each one: keep it if a test or tool reads it, otherwise move it to `dev/archive/` |
| Remote branches merged into `main` | 98 | **Not carried over** to the new repo (Phase A step 6), so nothing to delete; they stay in `creaite-history`. Release tags are recreated (step 5) |
| Remote branches not merged | 38 (only the "keep" ones are carried over in Phase A step 6; the rest stay in `creaite-history`) | **In flight, keep:** `v194-*`, `v195-*`, `v196-move-back`, `v20-*`. **Docs, merge then delete:** `dev-archive-security`, `dev-bl326-v210`, `dev-decisions-1to4`, `dev-bl327-defects`. **Old release branches** (`release-1.3`, `release-1.5.2`, `release-1.6.1`, `fix-v181`): delete if their tag exists. **The rest** (`creaite-tooling`, `tooling-extras`, `dev-security-pack`, `dev-ui-audit`, `dev-bl255-check`, `dev-handchecks-19x`, `dev-release-notes-19x`, `dev-backlog-275-276`, `dev-bl298-polish-backlog`): a keep-or-drop list for Alan |
| Local worktrees | 27 on laptop 2 (laptop 1 not counted) | Both laptops re-clone in Phase A step 8, so the old worktrees all go with the old clone once Done when is ticked. Each laptop's lead does its own: laptop 1's are Team 1's |
| Ignored local files (dev database, staging, logs, demo data) | not in git | Leave them |

### Worktree clean-up (Alan, 14-10-2026)

Every old worktree goes, on both laptops, once Done when is ticked. Each laptop's lead does its own; laptop 1's are Team 1's.

**Steps, in the old clone on each laptop:**

1. `git worktree list`, and record the list in the Log.
2. For each worktree, check `git status` is clean and its branch head is on GitHub or in `creaite-history`. Anything unpushed is pushed or saved as a patch first. Nothing is removed with uncommitted work in it.
3. `git worktree remove <path>`, without `--force` unless step 2 passed and a file is only locked.
4. `git worktree prune`, then delete the local branches that are gone.
5. Worktrees made by other tools, outside `.claude/worktrees/`: remove them the same way. On laptop 2, the one in `~/.local/share/kilo/worktree-pool/` goes (Alan, 14-10-2026).
6. The old clone's folder is renamed `creaite-old-clone`, kept for 7 days, then deleted on Alan's OK.

**After the migration, the standing rule:** a worktree is made only for in-flight work, in `.claude/worktrees/` of the new clone. The agent or lead that made it removes it, and its local branch, as soon as its work has landed. The digest lists any worktree older than 2 days.

**Laptop 2 today (27, plus the main checkout):**

| Group | Worktrees | When they go |
|---|---|---|
| Finished releases | `cut-190`, `cut-191`, `cut-192`, `cut-192-fix`, `release-prep-192`, `v192-today-home` | At clean-up |
| v1.9.3, the last old-repo release | `cut-193`, `release-193`, `release-prep-193` | Once v1.9.3 is published |
| Carried over to the new repo | `v194-archive`, `v194-instant`, `v194-instant-fix`, `v195-archiving`, `v195-archiving-fix`, `v195-design-scale`, `v195-design-scale-bl333`, `v195-run-chat`, `v195-consistency`, `v196-move-back`, `v20-notes-server-prep`, `v20-ai-select`, `v20-capture`, `v20-one-editor` | Once each branch is carried over and recreated in the new clone (Phase A steps 6 and 8) |
| Scrub and docs | `dev-no-real-names`, `dev-repomigration` | Once merged |
| Comms | `sprint-comms` | Once the fresh `sprint-comms` is started (Phase A step 6) |
| Another tool's | `kilo/worktree-pool/…/colorful-dimple` (detached) | Remove (Alan, 14-10-2026) |

## Phase C: the board (Scrum Master)

10. Pause edits to `dev/BACKLOG.md`, and tell both teams when the pause starts and ends.
11. Create a milestone on `insyncalan/creaite-plan` for each release, plus Unscheduled.
12. Create the private Project board, with these fields:
    - **Priority:** Urgent, High, Normal or Low.
    - **State:** Idea, Needs decision, Ready, Building, In review, Shipped, On hold or Dropped.
    - **Release:** a version, or Unscheduled.
    - **Size** and **Team**.
13. Create the views: by release, by state, and Needs decision (Alan's queue).
14. Create one issue per open backlog item from the scrubbed text, with its write-up as the body and its fields set.
15. Make `dev/BACKLOG.md` a read-only export generated from the board (with a header saying so), and note in the code repo that pull requests close plan items with "closes insyncalan/creaite-plan#N".

## Phase D: the handover to the Head (15-10-2026, 08:00)

16. Alan starts a fresh Head session on the laptop he's at, with the start-up brief: the charter, the board, `dev/HEAD-LOG.md` and the digest times (full at 08:00 and 16:00, lite at 12:00 and 20:00).
17. The roles change over:
    - The Scrum Master becomes the laptop 2 team lead, and Team 1's lead becomes the laptop 1 team lead. Neither edits the plan any more.
    - The Product Manager session stands down.
18. The Head sends the first digest, and the one-week pilot starts (15-10 to 21-10-2026).

## If something goes wrong

- **Code move:** until step 8, nothing is lost: rename `creaite-history` back to `creaite`, make it public again only if Alan says so, and delete the half-made new repo. After step 8, fix forward in the new repo. **Clean-up:** revert the one category's commit.
- **Board:** the plan repo is new and separate. Delete and recreate what failed. `dev/BACKLOG.md` stays the plan until step 15 is done.
- **Stopping part-way:** Phase B and Phase C can each stop at any step and resume. Edits to `dev/BACKLOG.md` stay paused until the board is complete or the migration is abandoned.

## Done when

- [ ] `main` has every published release, the suite is green, and the tag exists.
- [ ] Only in-flight branches remain on GitHub, and only in-flight worktrees on each laptop.
- [ ] `dev/` holds only living documents, and the rest is in `dev/archive/`.
- [ ] Every open backlog item is an issue on the private board, with its fields set; `dev/BACKLOG.md` is the export.
- [ ] The banned-names guard test passes on `main`.
- [ ] The Head's start-up brief is ready for 08:00.

## Log

| When | Who | What |
|---|---|---|
| 14-10-2026 | Product Manager | First draft: end state, preconditions, clean-up inventory, board, handover, rollback |
| 14-10-2026 | Alan (via the Product Manager) | Trigger changed: v1.9.3 published (done 18:58) → Alan's go/no-go → step 0 → a quick freeze (WIP commit, push, stop; 5–10 min). No fixed slot. Gate in practice: the scrub merged and the guard green |
| 14-10-2026 | Alan (via the Product Manager) | Development stops only at the freeze (step 1) and restarts per laptop after step 8; Phases B and C run alongside; only BACKLOG.md edits wait for step 15. Clock times are added here at "go migration" |
| 14-10-2026 | Alan | Step 0 added: the old repo goes private as the first step of the migration, not before ("when time comes") |
| 14-10-2026 | Alan (via the Product Manager) | Version numbering kept: the new repo's one release is v1.9.3; next releases stay v1.9.4, v1.9.5, v2.0.0 (Notes), v2.1.0; branch names and release groups unchanged; `update.py` unchanged |
| 14-10-2026 | Scrum Master | Step 5 changed: published zips v1.7.0–v1.9.2 contain real names, so no old zip goes to the new repo; one scrubbed release only. v1.9.1 and v1.9.3 release notes scrubbed in place |
| 14-10-2026 | Scrum Master | Phase A written (fresh public repo, old one private as `creaite-history`); preconditions, Phase B branch and worktree rows, and the rollback aligned with it |
| 14-10-2026 | Product Manager | Alan agreed the clean-up list (all build notes and `dev/sprints/` to `dev/archive/`; HANDOVER and START-HERE become `dev/HOW-WE-WORK.md`; SPRINTCOMMS and BUILD-WATCH retired; every old worktree removed, the kilo one included) |
| 14-10-2026 | Scrum Master | Migration run. The scrub went in two rounds: people's names first, then the firm and its domains; the hand-check screenshots were taken out of git. The old repo was made private and renamed `creaite-history`. The new public repo was created; two Team 1 branches carrying the old history were pushed into it by mistake and deleted, so the repo was deleted and recreated clean. v1.9.3 was released in the new repo. The in-flight branches were carried over as one commit each on top of the new `main` |
