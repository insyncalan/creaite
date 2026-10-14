# Sprint comms: Team 1 ↔ Team 2

**Frozen 15-10-2026 (Jarvis): the board replaces this file.** Started fresh in the new public repository on 15-10-2026. The earlier file is kept in the private `creaite-history` repository, on its own `sprint-comms` branch.

**Names (Alan, 15-10-2026):** laptop 1 (the Scrum Master) is **"Team Cap"**, and laptop 2 is **"Team Stark"** (earlier Team 1 and Team 2). Commit messages start "SPRINTCOMMS (Team Cap): …" or "SPRINTCOMMS (Team Stark): …".

**This repository is public.** Never write a real client, company, project or person's name here. Use the fictional sample data only (Brightwater, Kestrel Group, Northgate, FAL, MER, ORX, ABC, Alan Carter).

**The one channel between the two laptops: this file, on branch `sprint-comms`.**
- **Both laptops commit this file on `sprint-comms` and push it.** It is never merged into main.
- **Newest entry first,** under "Latest". Each entry starts with `DD-MM-YYYY HH:MM · team ·`.
- **To write:**
  ```
  git fetch origin && git checkout sprint-comms && git pull --ff-only
  # edit dev/SPRINTCOMMS.md, commit it, then push
  git push origin sprint-comms
  ```
  Never force-push. If the push is refused, pull again (a merge is fine) and push.
- **To read:** `git fetch origin && git show origin/sprint-comms:dev/SPRINTCOMMS.md`
- **Each laptop checks `sprint-comms` every 5 minutes.**

## Latest (newest first: DD-MM-YYYY HH:MM · team · what)

- 15-10-2026 02:20 · Jarvis · **This file is frozen: the board replaces it.** From now on, Team Cap and Team Stark work from their sub-issues on the private board ("creaite plan", over `insyncalan/creaite-plan`). Each lead sets its item's State, names its branch and pull request, and leaves a progress comment at each step on the issue. Questions go as a comment on the item, which moves to Needs decision. Jarvis (the Head of Product and Delivery) plans, decides within the charter and answers on the issues. A pull request closes a plan item with "closes insyncalan/creaite-plan#N". `dev/HOW-WE-WORK.md` and `dev/HEAD-LOG.md` on main hold the rest. Nothing more is written here.

- 15-10-2026 00:45 · Team Stark (Team 2) · **New team names (Alan): Team 1 is "Team Cap" and Team 2 is "Team Stark".** Commit messages start "SPRINTCOMMS (Team Cap): …" or "SPRINTCOMMS (Team Stark): …". **v2.0.0 is split between the teams (main 77bf5727, `dev/sprints/v200-notes-release.md`), and steps 1 to 5 run in parallel:**
  - **Team Cap:** B's margin ticks; the notes guard change (`v20-notes-guard`, test_guard_pinned re-pinned deliberately); the real-data round-trip gate with Alan; the rules text and the release notes; `release-200`'s integration and cut.
  - **Team Stark:** bringing `v20-capture` level with `v20-base`; finishing D (the wiring into Notes, and E's "Make this an action" hook); the review snapshot fix (BL-315's guess); Help, the guides, the spec and the hand checks.
  - **Start after the restart post.** Team Stark is re-cloning laptop 2 now.

- 15-10-2026 00:35 · Team 2 · **All 10 branches are carried over, and the v2.0.0 plan is on main.**
  - **Carried** (one commit each on a478bbd6; banned-names test and check.py pass on each; the full suite hasn't run on them yet):
    - `release-194` deba7023: `test_fast_save` passes now. `test_snapshots` fails on settings-advanced, the branch's own state.
    - `v195-design-scale` 955215cc: carried from its merge with cut-193. The before-and-after screenshots (`dev/reviews/bl325-before-after/`) are left in creaite-history, because they show real names.
    - `v195-archiving` 9e810e32: merged with v1.9.x code; the doctor count is now 36.
    - `v196-move-back` 88c6093b
    - `v195-run-chat-bl330` 6a7c4ee7: `test_run_chat` wasn't verified locally (it hung under load); leave it to Actions.
    - `v195-vip-conversations` 532ac4fb
    - `v195-consistency` 6c364e1a: BL-316 work in progress; its snapshots fail as they did before the freeze.
    - `v20-base` 9e462313, `v20-capture` fc457306, `dev-repomigration` 53f5f98a
  - **Real names scrubbed during the carry-over:** the Notes server's VIP example, capture and archive tests, and a client name in `test_run_chat`.
  - **The v2.0.0 Notes release plan is on main (3040baf8):** `dev/sprints/v200-notes-release.md`, from the PM.
    - **Alan's decisions (15-10-2026):**
      - no new tabs in v2.0.0 (BL-317 stays on hold);
      - a click opens a note link or chip, and ⌥-click edits inside it;
      - note drafts stay in the backup zip;
      - **notes are exempt from outside content:** reading a .md note in a notes folder (`notes.note_of`) no longer marks an ask creaite run. That's a guard change, on its own branch `v20-notes-guard`, with its own tests and test_guard_pinned re-pinned deliberately.
    - **The PM's recommendations:** E's calls stay as built, and the Draft email preview stays plain in v2.0.0.
    - **Order:**
      1. merge the latest `v20-base` into `v20-capture`;
      2. Team 2 finishes D (the wiring into Notes, and E's "Make this an action" hook);
      3. B's margin ticks;
      4. the guard change;
      5. the review snapshot (BL-315's guess);
      6. Alan's real-data round-trip gate;
      7. rules and docs;
      8. `release-200` is cut from `release-195`, after v1.9.4 and v1.9.5.
  - **Development restarts after Team 2 re-clones** (about 10 minutes). I'll post "development restarts" then.

- 15-10-2026 00:10 · Team 2 · **The migration is finished on GitHub; re-clone, then development restarts.**
  - **The new public repo** `insyncalan/creaite` started from one clean commit. The old repo is private as `insyncalan/creaite-history`, and its history stays there.
  - **v1.9.3 is published** here; its zip is attached by the release workflow.
  - **Carried over as one commit each, on main:** `v20-base`, `v20-capture` and `dev-repomigration` are here now. `release-194`, `v195-design-scale`, `v195-archiving`, `v196-move-back`, `v195-run-chat-bl330`, `v195-vip-conversations` and `v195-consistency` follow shortly. Each is scrubbed (the fictional names kept) and passes the banned-names test.
  - **Not carried:** the branches already inside those, such as the separate `v194-*` and `v20-*` parts. Fetch them from `creaite-history` only if one is needed.
  - **Team 1:** re-clone first (Alan has the steps), then start from these branches. Never push from the old clone again.
