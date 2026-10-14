# Sprint comms: Team 1 ↔ Team 2

Started fresh in the new public repository on 15-10-2026. The earlier file is kept in the private `creaite-history` repository, on its own `sprint-comms` branch.

**Names:** laptop 1 (the Scrum Master) is **"Team 1"**, and laptop 2 is **"Team 2"**. Commit messages start "SPRINTCOMMS (Team 1): …" or "SPRINTCOMMS (Team 2): …".

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

- 15-10-2026 00:10 · Team 2 · **The migration is finished on GitHub; re-clone, then development restarts.**
  - **The new public repo** `insyncalan/creaite` started from one clean commit. The old repo is private as `insyncalan/creaite-history`, and its history stays there.
  - **v1.9.3 is published** here; its zip is attached by the release workflow.
  - **Carried over as one commit each, on main:** `v20-base`, `v20-capture` and `dev-repomigration` are here now. `release-194`, `v195-design-scale`, `v195-archiving`, `v196-move-back`, `v195-run-chat-bl330`, `v195-vip-conversations` and `v195-consistency` follow shortly. Each is scrubbed (the fictional names kept) and passes the banned-names test.
  - **Not carried:** the branches already inside those, such as the separate `v194-*` and `v20-*` parts. Fetch them from `creaite-history` only if one is needed.
  - **Team 1:** re-clone first (Alan has the steps), then start from these branches. Never push from the old clone again.
