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

## How sessions talk to each other

**The board is the only channel between laptops.** Sessions on the same laptop may also message each other directly, for speed, but anything that matters goes on the board too. SPRINTCOMMS is frozen.

| From | To | How |
|---|---|---|
| A team lead | Jarvis | A comment on the item's issue, starting "Team Cap, HH:MM:" or "Team Stark, HH:MM:" (the time from `date`). On Jarvis's laptop, a direct message as well |
| Jarvis | A team lead | A comment on the item's issue (or #34 for anything general), starting "Jarvis, HH:MM, to Team …:". On the same laptop, a direct message as well |
| Anyone | Alan | Only through Jarvis: the digests (07:57 and 15:57 full, 11:57 and 19:57 lite), or straight away for a security or guard problem, possible data loss or a broken release |
| Alan | Anyone | He tells Jarvis, or comments on the issue. A team lead hearing a decision from Alan passes it to Jarvis, who records it once Alan confirms it directly |

**What a comment carries:**
- **Progress:** what was done, the % of Done-when points met, and an ETA (HH:MM).
- **A question:** "For Jarvis:" (order, defects, tests, docs, wording) or "For Alan:" (scope, visible changes, guard, security, permissions, confidential material), with a recommendation. Set the item to **Needs decision**. Jarvis answers within the hour, or takes it to Alan.
- **A push:** "push <branch> <sha>" once it's verified (new root, `test_no_real_names`, `check.py`, nothing uncommitted). On Jarvis's laptop, Jarvis checks and pushes. On the other laptop, the lead pushes from the main checkout, by branch name only (never `--tags`), and comments "pushed <branch> <sha>" for Jarvis to check.
- **Stopping:** a one-line "paused" or "back" on #34 when a lead stops for more than half an hour, so Jarvis doesn't move its work.

**Jarvis reads the board every hour at :17,** and acts on every new comment. Done-when boxes: the lead lists the points met, and Jarvis ticks them. Jarvis closes items.

**Decisions:** Jarvis records each one in `dev/HEAD-LOG.md`. A relayed decision isn't a decision until Alan confirms it to Jarvis directly. Guard, security, permission, scope and visible-change decisions are always Alan's.

## Model cost (BL-343, Alan, 15-10-2026)

The target is half the cost per shipped item. Most of the cost is long contexts re-read on every turn, and new agents writing a fresh context.
- **Restart or `/compact` a lead session (and Jarvis)** when its context passes about 150,000 tokens, or after each release cut, whichever comes first; at least twice a day. After more than an hour idle, start fresh with a handover rather than resuming.
- **Fewer new agents:** one agent per item; a follow-up goes to the agent that did the work.
- **Lead sessions run on Sonnet 5.5** (Alan, 15-10-2026): both team leads and Jarvis. Switch with `/model sonnet` at the next `/compact` or restart (a switch mid-context rewrites the whole cache once). A lead that has to judge a guard, security or permission diff, or a hard design call, hands it to an Opus agent with a tight brief.
- **Every agent names its model** (the Agent tool's `model`); an agent with no model is a mistake. Pick the cheapest that fits:
  - **Haiku 5.5:** running suites and checks, rebuilds (`dashboard.html`), board scans and ticks, finding files, counting.
  - **Sonnet 5.5, the default for everything else, code included** (Alan, 15-10-2026): product code, the dashboard, reports, settings, the sweep, tests, docs, release notes, hand-check text, merges, check.py fixes.
  - **Opus 5.5, only for the files where a subtle mistake is costly:** the guard (`reach.py` and its hook), `permissions.py`, `filechange.py`; the writer and the data (`tracker.py` apply, `schema.sql` and migrations, `backup.py`, `update.py`); the live server's runs, approvals and locking (`live_server.py`); and any item that has failed its tests or review twice on Sonnet. An item touching one of these files goes to Opus whole.
  - **The board names it (Alan, 15-10-2026):** every open item carries one label, `opus`, `sonnet` or `haiku`; no label means Sonnet. The lead launches the item's agent on that model. A lead may raise an item to Opus when it fails twice (and says so on the issue), and Jarvis relabels when an item's files change. Never lower an `opus` label without Jarvis.
  - **Measured on #87:** test failures and review rounds per item. Alan's limit is one extra review round per item; a kind of work that needs more goes back to Opus.
- **Cache reads cost the same on Sonnet as on Opus**, so a short context still saves the most; the model switch halves what's written and generated.
- **Tight briefs** (the issue, the files, the tests), and no local full suites when Actions runs the same suite.

## Rules

- **Pull requests close plan items:** put `closes insyncalan/creaite-plan#N` in the description.
- **Worktrees** only for work in flight, in `.claude/worktrees/`. Whoever made one removes it, and its local branch, as soon as the work has landed.
- **The repo is public.** No real client, company, project or person's name anywhere: use the fictional demo data. `dev/tests/test_no_real_names.py` guards it.
- **Cutting a release:** set VERSION, then run `python3 dev/tools/build_guides.py` and `python3 dev/tools/run_tests.py test_help`, and commit them together; then merge to main and publish. `build_release.py` refuses a stale guide.
- **Hand checks:** every hand check names the automated test that covers it (`file::test`), or is marked `judgement` (on the screenshot sheet) or `live only`, with the reason. `just handchecks vX.Y.Z` runs them (BL-341).
- **Notes:** a note for an item lives on its issue. Notes for shipped releases are in `dev/archive/notes/<release>/`.
- **CI (#89):** iterate with `python3 dev/tools/run_tests.py --changed`; the full suite runs only on release branches and on main, never from your own push. Never dispatch a Tests run on a commit a push run already covers: check `gh run list --workflow tests.yml` first. The Linux jobs run the suite in 3 shards (`--shard I/3`; Python 3.14 all files, 3.9 the non-browser files); macOS runs on release branches only; the release workflow skips its repeat suite when a successful "Tests" run exists for the exact commit. `run_tests.py` starts the files that failed last time first and stops a shard after 8 failed files (`--max-fail 8`). The result to wait for is the "Tests passed" job.
