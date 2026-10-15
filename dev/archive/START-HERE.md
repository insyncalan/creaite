# Start here — GitHub and Claude Code

## Two folders, two purposes
| Folder | What | Git |
|---|---|---|
| `~/dev.env/creaite` | **Development repo** — engine, skills, docs, sample data. Has `.creaite-dev`. | GitHub (private) |
| `~/creaite` | **Live vault** — your real projects, mail-derived items, database. Created in BUILD Step 7. No `.creaite-dev`. | Local git only, **never pushed** (NFR-09) |

## One-time setup
1. `xcode-select --install` (git), then `git config --global user.name "Alan Carter"` and `git config --global user.email <you>`.
2. Optional but easiest: `brew install gh` then `gh auth login`.
3. Unzip the repo to `~/dev.env/creaite` (not in iCloud Desktop/Documents or OneDrive).
4. ```
   cd ~/dev.env/creaite
   git init -b main
   git config core.hooksPath dev/hooks
   git add . && git commit -m "creaite starter kit (BRD v0.23)"
   gh repo create creaite --private --source=. --push
   ```
   (Without gh: create an empty **private** repo on github.com, then `git remote add origin <url>` and `git push -u origin main`.)
5. Export the BRD to `dev/BRD.md` (see that file), commit it.

## Start developing
1. Claude desktop app › **Code** › open folder `~/dev.env/creaite`.
2. First prompt:
   > Read README.md, dev/START-HERE.md, dev/HANDOVER.md, dev/BUILD.md and dev/dashboard-spec.md. This is the development repo (.creaite-dev exists), so skip the vault session-start rules. Summarise the plan, list anything unclear, then start BUILD Step 0 on a branch called step-0-environment. Commit as you go; don't push without asking.
3. One branch per build step (`step-1-database`, …). At the end of each step: tests pass → you review the diff → merge to main → push.
4. Keep the reference design open: `dev/reference/dashboard-reference.html`.

## Rules for the repo
- Only fictional data (the ABC example). Never copy real minutes, mail or the live database here; the pre-commit hook blocks the obvious cases.
- Settings: commit `system/config/settings.json` with defaults only.
- The live vault is created from this repo in Step 7 and never pushed anywhere.
