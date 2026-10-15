# v1.8.0 on a second laptop: a step-by-step guide

Written 12-10-2026 by the Scrum Master session for Alan. **v1.8.0 is BL-231 and nothing else** (Alan, 12-10-2026): untangle the dashboard. Read "### BL-231" in `dev/BACKLOG.md` once before you start; this guide turns it into steps you can follow, with the prompts to paste into Claude Code.

## The shape of it

| Phase | What | When | Touches the app? |
|---|---|---|---|
| 0 | Set up the laptop | now | no |
| 1 | Preparation tools | **now**, while v1.7.0 is being built on laptop 1 | no, `dev/` only |
| 2 | Fold the 241 wrappers | **only after v1.7.0 has shipped** | yes: `dashboard.html` |
| 3 | Split into ES modules, bundled by esbuild | after phase 2 | yes |
| 4 | Type-check with `checkJs` | after phase 3 | `dev/` and comments |
| 5 | Escaping leftovers, then hand over for release | after phase 4 | yes |

**Why the wait before phase 2:** every v1.7.0 dashboard sprint (ask-flow, decisions-needed, live updates, escaping, ui-sweep) is editing `dashboard.html` now. Folding it at the same time would clash with all of them, and the work would have to be redone. BL-231 also needs BL-254's screen snapshots, which are recorded near the end of v1.7.0. Phase 1 can't clash with anything: it only adds tools in `dev/`.

## Ground rules for this laptop

1. **Never push `main`.** Work only on branches named `v18-…`. The Scrum Master session on laptop 1 is the only one that merges into main.
2. **Never force-push, and never rebase a branch once it's pushed.** To catch up with main, merge main into your branch.
3. **`dev/tools/check.py` must pass** before every commit. Never use `--allow-worse`. This sprint should *lower* the figures; lower the baseline with `check.py --update-baseline` as they fall.
4. **Full test suites run on GitHub Actions,** not on the laptop: `gh workflow run tests.yml --ref <branch>`. Local runs are single files, at `-j 2` at most.
5. **Development repository only:** sample data, never your real vault, never Microsoft 365. The `.creaite-dev` file in the repo marks it.
6. **Don't edit** `dev/BACKLOG.md`, `dev/BRD.md` or `dev/archive/sprints/STATUS.md` from this laptop. The Scrum Master records progress; you tell Alan, who tells the Scrum Master.
7. **No skip-permissions mode** in Claude Code. Approve each permission it asks for.

## Phase 0: set up the laptop (about 30 to 45 minutes)

1. **Install the basics:**
   - Claude Code, signed in to the same account;
   - Google Chrome;
   - git;
   - Homebrew in your home folder (no admin rights needed), as on laptop 1.
2. **Clone the repository** into the same layout as laptop 1:
   ```
   mkdir -p ~/dev.env && cd ~/dev.env
   git clone https://github.com/insyncalan/creaite.git
   cd creaite
   ```
3. **Install the development tools** from the Brewfile, then sign `gh` in:
   ```
   brew bundle --file=dev/Brewfile
   gh auth login
   ```
4. **Check Python:** `python3 --version` should be 3.14, and `/usr/bin/python3 --version` 3.9 (the floor creaite supports).
5. **Check it works:**
   ```
   python3 dev/tools/check.py
   python3 dev/tools/run_tests.py --list | head
   python3 dev/tools/run_tests.py -j 2 test_tracker
   ```
   `check.py` should say `check: OK` and the test should pass. If not, stop and tell the Scrum Master on laptop 1 what it printed.
6. **Open Claude Code in `~/dev.env/creaite`.** It reads the repo's `CLAUDE.md` and `system/creaite-rules.md`, and sees `.creaite-dev`, so it knows this is the development repo.

## Phase 1: preparation (start now)

All of this lives in `dev/`, so it can't clash with v1.7.0. Use one branch, `v18-prep`.

**Prompt 1: the wrapper inventory.** Paste into Claude Code:

> You're working on creaite's development repo. Read BL-231 in dev/BACKLOG.md (step 1) and dev/tools/check.py (how it counts in-place wrappers). Create a branch `v18-prep` from main. Write `dev/tools/wrappers.py`, standard library only. It reads `system/templates/dashboard.html`'s script and prints, for every function wrapped in place (`const x=fn; fn=function…`), the chain in order (first definition, then each wrapper, with line numbers), and every **mid-chain reference**: a place that takes a reference to the function between two of its wrappers (`addEventListener(…, fn)`, `const f = fn`, an object holding it, a callback). Output a readable report and a JSON file `dev/wrappers-inventory.json`. Suggest batches of about 20 wrappers, easiest chains first, with drawPanel, renderWork, renderCockpit and go last, each alone. Add a quick test in dev/tests that runs it on a small sample script. check.py must pass. Commit; don't push. Show me the summary: chain count, total wrappers, mid-chain references, and the batch plan.

**Prompt 2: pin esbuild.**

> On branch `v18-prep`: write `dev/tools/esbuild.py`, standard library only. It downloads a **pinned** esbuild native binary (`@esbuild/darwin-arm64` and `@esbuild/linux-x64`, version 0.28.2) from the npm registry tarball with `urllib`, checks a SHA-256 written in the script, unpacks `package/bin/esbuild` into `dev/.cache/esbuild/` (add that to .gitignore), and runs it. No Node, no npm, nothing in `system/` may depend on it (runtime never installs, NFR-12). Add a test that the hash check refuses a changed file (use a fake download). Prove it bundles two small ES modules into one IIFE script. check.py must pass. Commit; don't push.

**Prompt 3: the identical-output harness (prepare for step 2a).**

> On branch `v18-prep`: write `dev/tools/split_dashboard.py` and a test, `dev/tests/test_dashboard_split.py`, that prove a split is a **move, not a rewrite**:
> - `split` cuts `system/templates/dashboard.html` into `dev/scratch-split/` (the HTML shell, the CSS, and the script cut at its existing `/* ===== … ===== */` block boundaries, in today's order);
> - `join` puts them back together;
> - the test checks the joined page is **byte-for-byte identical** to the original.
>
> Don't move the real source yet; this only proves the tool on today's file. check.py must pass. Commit; don't push.

**Prompt 4: the checkJs set-up.**

> On branch `v18-prep`: add `dev/jsconfig.json` for TypeScript's `checkJs` (`noEmit`, ES2020, DOM), and `dev/tools/typecheck.py`. That script runs `npx --yes -p typescript@5.6.3 tsc -p dev/jsconfig.json` only if Node is present on this development machine, and otherwise says how to install it with Homebrew (`brew install node`; development only, allowed by the 11-10-2026 rule). Run it once against a copy of the dashboard's script extracted to `dev/scratch-split/` and report the error count. It will be large; that's the starting figure. Add nothing to check.py's ratchet yet. Commit; don't push.

**Then publish phase 1:**
```
git push -u origin v18-prep
gh workflow run tests.yml --ref v18-prep
```
Tell Alan "v18-prep is pushed". He passes it to the Scrum Master, who merges it into main. It's dev-only, so it can merge at any time.

## Phase 2: fold the wrappers (only after v1.7.0 has shipped)

**Before you start, ask the Scrum Master (through Alan) to confirm three things:**
- v1.7.0 is released;
- BL-254's screen snapshots (the goldens) are recorded on main;
- no other sprint is editing `dashboard.html`.

Then:
```
git checkout main && git pull
git checkout -b v18-fold
```

**Prompt 5: one batch at a time.** Repeat it for each batch in the plan from Prompt 1:

> On branch `v18-fold`, fold **batch N** from `dev/wrappers-inventory.json` (run `python3 dev/tools/wrappers.py` again first, so the line numbers are current).
> 1. **Mid-chain references first.** For each mid-chain reference in this batch, decide what it should call after folding, keeping today's behaviour exactly, and note it in the commit message.
> 2. **Fold each chain** into its original function, in the original place, keeping the order of the wrapped steps. Delete the wrapper blocks.
> 3. **Behaviour is identical:** no screen, text, key or request changes.
> 4. **Check the batch:**
>    - run `python3 dev/tools/check.py` (the wrappers count must fall; then `--update-baseline`);
>    - run the screen snapshots: `python3 dev/tools/run_tests.py -j 2 test_snapshots`;
>    - run every test file that mentions a folded function, at `-j 2`.
> 5. If a snapshot differs, **stop and show me the diff.** Never update a golden in this phase.
>
> Commit the batch on its own. Push the branch and start `gh workflow run tests.yml --ref v18-fold`. Wait for it to pass before the next batch.

**The last four** (`drawPanel`, `renderWork`, `renderCockpit`, `go`) go one per batch, each with its own Actions run.

**Done when** `python3 dev/tools/wrappers.py` reports 0 and the check.py baseline has `wrappers: 0`. Tell Alan "v18-fold is ready". The Scrum Master merges it.

## Phase 3: ES modules, bundled by esbuild

On a new branch `v18-modules` from main, after `v18-fold` has merged.

**Prompt 6: step 2a, the byte-identical move.**

> Following BL-231 step 2a, move the dashboard's source into `system/templates/dashboard/`: the shell, the CSS and the script blocks, using `dev/tools/split_dashboard.py`. `dev/tools/build_release.py` and the test runner build `system/templates/dashboard.html` from them. That file stays, as a **generated** file, at the same path, so tests, `make_vault` and `update.py` keep working. `test_dashboard_split` must prove the built page is **byte-for-byte identical** to the page before the move. check.py and the full suite on Actions must pass. Commit.

**Prompt 7: step 2b, ES modules by area.**

> Following BL-231 step 2b:
> 1. Turn the script blocks into ES modules by area: core and state, rail, Today, Work, Review, Intake, Files, Activity, Settings, Help, ⌘K and ask creaite, and milestones. One `main.js` imports them all.
> 2. Bundle with the pinned esbuild from `dev/tools/esbuild.py` into one IIFE, placed in the page's single inline `<script>`. No network, and nothing new in the vault at run time.
> 3. The output is no longer byte-identical, so **BL-254's snapshots are the check**. Every screen must match its golden unchanged.
>
> Commit by area. Run the full suite on Actions after each.

Tell Alan when `v18-modules` is ready.

## Phase 4: checkJs

**Prompt 8:**

> Turn on `// @ts-check` module by module, adding JSDoc types until each module has no type errors. Then add the type-error count to check.py's ratchet, beside pyright and Biome, so it can only fall. Development only: nothing in `system/` depends on TypeScript or Node. Commit per module.

## Phase 5: escaping leftovers, and hand-over

**Prompt 9:**

> Following BL-231 step 4, move the HTML-string sinks that v1.7.0's BL-228 part D left onto the `html` helper, until check.py's count of sinks printing tracker or file data is 0. The snapshots must stay unchanged. Then check BL-231's "Done when" list item by item and report each one as met or not.

Tell Alan the branch name. The Scrum Master merges it, runs the release steps and publishes v1.8.0.

## If something goes wrong

- **A snapshot differs during folding:** that's a behaviour change, so the fold is wrong. Undo that chain (`git checkout -- system/templates/dashboard.html`) and fold it more carefully. Never update the golden to make it pass.
- **check.py fails:** fix the code. Never use `--allow-worse`.
- **Main has moved on:** merge it in with `git merge main`, never `git rebase`. Re-run check.py and the snapshots.
- **Unsure whether something clashes with laptop 1:** ask the Scrum Master through Alan before touching any file outside `dev/`.
