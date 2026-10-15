# How we work

How creaite's development is run, from 15-10-2026. It replaces `HANDOVER.md` and `START-HERE.md` (both now in `dev/archive/`).

## Where things are

- **The delegation charter** (Alan's Claude Docs page): what Jarvis, the Head of Product and Delivery (HOPD), may decide alone, what goes to Alan, and how defaults go ahead.
- **The board:** the private GitHub Project on `insyncalan/creaite-plan`. Every backlog item is an issue there. `dev/BACKLOG.md` is a read-only export of it; don't edit it by hand.
- **`dev/HEAD-LOG.md`:** every decision, the reason and who made it, newest first.
- **`dev/BUILD.md`** and **`dev/dashboard-spec.md`:** how creaite is built and how the dashboard looks.

## Who does what

- **Jarvis** runs the plan: a fresh Claude session given the charter. There is one Jarvis at a time, and Jarvis moves with Alan (the baton). The pinned "Head" issue on the board (insyncalan/creaite-plan#82) says which laptop Jarvis is on, and holds the baton procedure, the start-up brief and each handover note.
- **A team lead per laptop** runs the build agents: **Team Cap** on laptop 1, **Team Stark** on laptop 2. There is no cap on build agents.
- **Alan** decides what the charter keeps for him. A default Jarvis raises goes ahead at the second digest after it was raised, never overnight.
- **Digests:** four a day (full at 08:00 and 16:00, lite at 12:00 and 20:00), and on demand.

## Rules

- **Pull requests close plan items:** put `closes insyncalan/creaite-plan#N` in the description.
- **Worktrees** only for work in flight, in `.claude/worktrees/`. Whoever made one removes it, and its local branch, as soon as the work has landed.
- **The repo is public.** No real client, company, project or person's name anywhere: use the fictional demo data. `dev/tests/test_no_real_names.py` guards it.
- **Notes:** a note for an item lives on its issue. Notes for shipped releases are in `dev/archive/notes/<release>/`.
