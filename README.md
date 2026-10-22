# creaite

**Meetings in. A status you can trust out.**

creaite is a programme manager's assistant that does the admin of running a portfolio. It reads your meeting transcripts, Outlook and Teams, drafts the minutes, and proposes the actions, decisions, risks and issues that came out of them. You approve what is right. creaite keeps the record, tells you what needs attention today, and writes the weekly report, the client report and the steering one-pager from it.

It runs on your Mac, on your own project files, and it never changes anything until you say so.

> **This repository holds the creaite engine and fictional sample data only.** No real client, company or person is named here. Current version: see [`VERSION`](VERSION), with plain-English notes for each release in [`dev/release-notes/`](dev/release-notes/).

## What it does for you

**From a meeting to tracked work**
Drop in a Teams transcript. creaite drafts the minutes and lists every action, decision, risk and issue with an owner, a due date and a link back to the line in the transcript. You tick what becomes a tracked work item, fix what is wrong in place, and approve with one click. Export the minutes as Word, PDF or HTML, or draft the follow-up email.

**One page for what needs you today**
Today shows the meetings in your day, what is overdue or due soon, decisions waiting on you or on others, what you owe and what others owe you, and milestones that are slipping, with the open work each one depends on. Everything is a link to the item itself.

**Mail and Teams, checked for you**
creaite reads your Outlook and Teams, spots follow-ups and commitments, and offers them as suggestions. People you follow are never missed. Nothing is sent, replied to or deleted: it only reads.

**Reports without the Friday scramble**
A weekly report per project with health and the reasons, a client-safe report that shows only what you have flagged as client-visible, and a one-page steering committee summary, internal or client-safe. All draft as Word documents for you to review.

**Meeting prep in a minute**
A prep page for any meeting: the open items that matter, the latest reporting, suggested questions, and notes with sources.

**Ask in plain English**
Ask creaite for anything in your portfolio ("what is blocking go-live?", "move the pilot milestone to the 20th", "make a document of open risks"). It answers from your own record and cites where it came from.

## You stay in control

- **Nothing changes until you approve it.** Suggestions wait in one place, Intake. Routine ones can be approved together; new decisions, new risks and health changes always need your eye.
- **Everything can be undone.** Every save has an Undo, and changes to your files are backed up first.
- **A source on every item.** Each action, decision, risk and issue points to the meeting, email or chat it came from.
- **creaite never sends anything.** It does not send mail or Teams messages or publish reports. Drafts are for you to copy and send.
- **Your record stays on your Mac.** The database, the dashboard and the backups live on your laptop. Claude reads the content it works on, and the daily backup zip goes to your company OneDrive. Confidential material can be kept out of reports and prep pages.
- **Plain language, plain numbers.** The status is worked out from your own record by ordinary code, not guessed by a model.

## A week with creaite

1. **Monday to Thursday.** Meetings happen. creaite checks mail and Teams each morning; you open Today, see what needs you, and approve the suggestions from yesterday's meetings in a few minutes.
2. **Before a meeting.** Press Prep: the open items, the latest status and questions to raise.
3. **Friday.** The weekly report is already drafted per project. Review, adjust, file.
4. **Steering committee.** One click for the one-pager, from the same record.

## What you need

- A Mac (the only tested platform), with FileVault on.
- The Claude desktop app and the `claude` command, signed in, with Microsoft 365 connected and Anthropic's Word (docx) skill.
- Python 3.9 or later (creaite installs nothing at run time; its libraries are bundled), git, and Chrome or Edge for the dashboard.

Step-by-step set-up, including the optional double-click launcher and the sign-in start-up agent, is in [`dev/SETUP.md`](dev/SETUP.md). Say "setup" to creaite and it checks your machine for you.

## Try it with sample data

This repository includes a fictional portfolio so you can look around before using real data:

```sh
git config core.hooksPath dev/hooks          # blocks commits of real data
python3 dev/tools/demo_data.py load          # fictional demo portfolio (purge to remove)
system/scripts/run live_server.py            # serve the dashboard on 127.0.0.1
```

---

## Under the hood

For developers and the curious. creaite is plain Python (standard library plus bundled libraries) and a single-file dashboard, run by Claude Code.

```
transcripts · minutes · Outlook · Teams
              │
              ▼
   Claude skills (cx-minutes, cx-sweep)
              │  suggestions → system/staging/
              ▼
   review and approve (Intake / cx-review)
              │  tracker.py apply: the only writer
              ▼
   system/tracker.db ──► dashboard.html · tracker-view.xlsx · Word reports
```

- **One writer.** `system/scripts/tracker.py apply` is the only path into `tracker.db`.
- **The schema is the rulebook.** `system/scripts/schema.sql` validates every write.
- **Approval before writes.** Unattended runs only write proposals to `system/staging/`.
- **Rules.** What Claude may and may not do is in [`system/creaite-rules.md`](system/creaite-rules.md).

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

## Development

Requirements: macOS, Python 3.9+, Claude Code, Chrome or Edge. The `.creaite-dev` file marks this as the development repository, so session-start rules and live Microsoft 365 access are switched off here.

```sh
for t in dev/tests/test_*.py; do python3 "$t" || break; done   # run the tests
```

Design decisions, specs and the build plan are in [`dev/`](dev/).

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
