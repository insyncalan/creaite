# creaite

A personal portfolio reporting system for a programme manager, run by Claude Code on a Mac. Meeting transcripts, Outlook and Teams go in; actions, decisions, risks and issues come out — proposed by Claude, approved by a person, then recorded in a local SQLite tracker with a dashboard, an Excel view and Word reports.

**This repository holds the engine and fictional sample data only.** Real vault data is never committed (see `.gitignore` and `dev/hooks/pre-commit`). Current version: see [`VERSION`](VERSION).

## How it works

```
transcripts · minutes · Outlook · Teams
              │
              ▼
   Claude skills (cx-minutes, cx-sweep)
              │  proposals → system/staging/
              ▼
   review and approve (cx-review / dashboard)
              │  tracker.py apply  — the only writer
              ▼
   system/tracker.db ──► dashboard.html · tracker-view.xlsx · Word reports
```

- **Local only.** All project data stays on the laptop. Nothing goes to cloud storage or a published page.
- **Approval before writes.** Nothing reaches the database until it is approved; unattended runs only write proposals.
- **One writer.** `system/scripts/tracker.py apply` is the only path into `tracker.db`; every apply can be undone.
- **Source on every row.** Each item cites its file, email or chat.

## Skills

| Skill | What it does |
|-------|--------------|
| `cx-minutes` | Teams transcripts → draft Word minutes and proposed items |
| `cx-sweep` | Outlook and Teams since the last sweep → proposed items; runs at session start when due |
| `cx-review` | Shows everything pending by project; approve, reject, apply, undo |
| `cx-edit` | Plain-English changes to items, projects, memory and settings |
| `cx-weekly-report` | Per-project health, updates and a Word weekly report |
| `cx-client-report` | A client-safe Word report; only client-visible items appear |
| `cx-steerco` | A one-page Word summary for a steering committee (internal or client-safe), filed in the Steerco folder on approval |
| `cx-setup` | Health check, repair, Microsoft 365 checks, install and undo updates |

Skills live in [`.claude/skills/`](.claude/skills/). The rules Claude follows are in [`system/creaite-rules.md`](system/creaite-rules.md).

## Repository layout

| Path | Contents |
|------|----------|
| `system/scripts/` | Python engine: `tracker.py`, `build_dashboard.py`, `live_server.py`, `report.py`, `update.py` and others. Standard library plus bundled `vendor/`; no pip installs |
| `system/templates/` | Word, dashboard and report templates; bundled JavaScript |
| `system/config/` | `settings.json` (all tunable values) and optional schedules |
| `.claude/` | Skills and permissions for unattended runs |
| `projects/` | Sample project (`ABC Example Programme`) and `_portfolio/` templates |
| `dev/` | Requirements, build plan, design decisions, specs, tests and tools |

## Setup on a new machine

A live vault needs these and nothing else (BL-241; the three tiers are in [`system/creaite-rules.md`](system/creaite-rules.md) › Portability rules, the steps in [`dev/SETUP.md`](dev/SETUP.md)):

- macOS, the only tested platform. Windows is best effort and untested; ask creaite's never list names macOS places only.
- Python 3.9 or later. Every script runs through `system/scripts/run` (for example `system/scripts/run doctor.py`), which picks the newest one on `PATH`. No pip installs: libraries are bundled in `vendor/`.
- The Claude desktop app and the `claude` command, signed in, with Microsoft 365 connected and Anthropic's docx skill.
- Chrome or Edge for the dashboard; git (the command line developer tools); FileVault on; the vault in a local folder outside OneDrive and iCloud.

Optional: the double-click launcher and the login agent (macOS conveniences, outside the vault), and the development tools in `dev/Brewfile` (`gh` lets "update creaite" fetch a release itself).

## Development

Requirements: macOS, Python 3.9+, Claude Code, Chrome or Edge. The `.creaite-dev` file marks this as the development repository, so session-start rules and live Microsoft 365 access are switched off here.

```sh
git config core.hooksPath dev/hooks          # blocks commits of real data
python3 dev/tools/demo_data.py load          # fictional demo portfolio (purge to remove)
system/scripts/run live_server.py            # serve the dashboard on 127.0.0.1
for t in dev/tests/test_*.py; do python3 "$t" || break; done   # run the tests
```

## Releases and updates

Publishing a GitHub release tagged `vX.Y.Z` (matching `VERSION`) runs the [Release zip](.github/workflows/release.yml) workflow: it runs the tests, builds `creaite-X.Y.Z.zip` and attaches it to the release.

To update a live vault, say **"update creaite"**: with `gh` installed and signed in it fetches the zip into `system/releases/` itself; otherwise download the attached zip (not "Source code") there first. An update replaces the engine only, never data or the root `CLAUDE.md`, backs up first and can be reversed with **"undo update"**. Full steps: [`dev/SETUP.md`](dev/SETUP.md#releasing-and-updating-bl-36).

## Documentation

| Document | Purpose |
|----------|---------|
| [`dev/HOW-WE-WORK.md`](dev/HOW-WE-WORK.md) | How development is run: the Head, the teams, the board, pull requests and worktrees |
| [`dev/HEAD-LOG.md`](dev/HEAD-LOG.md) | Every development decision, newest first |
| [`dev/SETUP.md`](dev/SETUP.md) | New-machine checklist, Outlook rules, releasing and updating |
| [`dev/BUILD.md`](dev/BUILD.md) | The build plan, step by step |
| [`dev/archive/HANDOVER.md`](dev/archive/HANDOVER.md) | The design decisions to v1.9.3 (archived) |
| [`dev/BRD.md`](dev/BRD.md) | Requirements |
| [`dev/BACKLOG.md`](dev/BACKLOG.md) | Backlog |
| [`dev/staging-format.md`](dev/staging-format.md) | Proposal format and Excel round-trip |
| [`dev/dashboard-spec.md`](dev/dashboard-spec.md) + [`dev/reference/dashboard-reference.html`](dev/reference/dashboard-reference.html) | Dashboard spec and the single source of design truth |
