"""The retained-rules test for the slimmed creaite-rules.md (#338, #327 part C).

Standard: the rules file at origin/v262-line, and the same file after the 2.6.2 VIP/follow rules diff (the test works out which one the
tree holds). The imported rules must keep, as WHOLE SENTENCES (never as fragments, never matched both ways):
  * the Non-negotiables section and the Development guard paragraph, byte for byte as in the original;
  * every rule-bearing sentence of every other section, one test per section (the FAMILIES below; state-specific wording in
    LINE_FAMILIES / CHAIN_FAMILIES);
  * REWORDED: an original "never" clause (whole) and the shorter whole clause that now carries it;
  * MAPPED: "never" clauses that only describe what a record holds or how code or the launcher behaves, kept word for word in the
    reference file, each with the reason and a pointer line that stays in the rules.
A completeness check takes every "never" clause of the original and fails if it is in none of these (or not a 6-word clause present
verbatim in the rules). MUTANTS are permanent: each one edits a copy of the slimmed rules and the check must go red; every fixture
sentence is also deleted and flipped automatically."""
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RULES = REPO / "system/creaite-rules.md"
REFERENCE = REPO / "system/templates/creaite-reference.md"
REF_PATH = "system/templates/creaite-reference.md"
DIFFS = [REPO / "dev/proposals/338/creaite-rules.diff", REPO / "dev/proposals/338/creaite-rules.after-chain.diff"]
CHAIN_MARK = "People you follow first"          # the 2.6.2 VIP/follow rules diff is in the file

# #347 (v2.6.6): dev/proposals/347/creaite-rules.md.diff changes two trigger cells of the skills table (the plain words "check my mail",
# "save", "undo last save"). It adds words and removes none, so no "never" sentence changes. The test takes the 347 wording off
# before it works out the 338 state (the 338 diffs were cut before it and do not apply over it) and puts it back on both sides, so the
# comparison is the same whichever way round the tree is. SUBS_347 is checked against the real diff (test_the_347_substitutions...).
RULES_347 = REPO / "dev/proposals/347/creaite-rules.md.diff"
MARK_347 = '"check my mail", "check my mail for ABC", "sweep"'
SUBS_347 = [
    ('"sweep", "sweep mail", "sweep mail for ABC", "sweep the last 7 days", "sweep the <subject> thread", "refresh calendar"',
     '"check my mail", "check my mail for ABC", "sweep", "sweep mail", "sweep mail for ABC", "sweep the last 7 days", "sweep the <subject> thread", "refresh calendar"'),
    ('"reject…", "apply", "undo last apply", "import excel"',
     '"reject…", "save", "apply", "undo last save", "undo last apply", "import excel"'),
]
# #339 (v2.6.7): dev/proposals/339/creaite-rules.diff inserts one sentence into the "What ask creaite may touch" bullet (the typed
# "refresh calendar" run; a sweep reads no home folder). It adds a sentence and removes none. Handled like 347: stripped before the 338
# state is worked out, put back on both sides, and checked against the real diff.
RULES_339 = REPO / "dev/proposals/339/creaite-rules.diff"
MARK_339 = 'a typed "refresh calendar" starts the small calendar run'
INSERT_339 = '**#339:** a typed "refresh calendar" starts the small calendar run, as the Calendar import button does (its own tools and two input files, no chat, no session, mode `calendar`; its closure is kept in the day\'s "Runs creaite started"), and a sweep run reads the vault and the projects folder, not the home folder.'
AT_339 = "is a plain chat (BL-309). Every change goes through"
# #250 (v2.6.10): dev/proposals/250/creaite-rules-250.diff adds one bullet (the sweep's transcript fetch) before the Assistant bullet.
# Handled like 347 and 339: stripped before the 338 state is worked out, put back on both sides.
RULES_250 = REPO / "dev/proposals/250/creaite-rules-250.diff"
MARK_250 = "**Transcripts fetched by a sweep (#250):**"
AT_250 = '- **Assistant ("ask creaite"'
STATE = {"347": False, "339": False, "250": False}         # whether the tree holds each patch's wording (set by states(); fixture() reads it)


def with_339(text):
    return text if INSERT_339 in text else text.replace(AT_339, "is a plain chat (BL-309). " + INSERT_339 + " Every change goes through", 1)


def without_339(text):
    return text.replace(" " + INSERT_339, "", 1)


def insert_250():
    """The one bullet the 250 diff adds (its only added line); "" if the diff is not in the tree."""
    if not RULES_250.exists():
        return ""
    return next((x[1:] for x in RULES_250.read_text(encoding="utf-8").splitlines() if x.startswith("+") and not x.startswith("+++")), "")


def with_250(text):
    bullet = insert_250()
    return text if not bullet or bullet in text else text.replace(AT_250, bullet + "\n" + AT_250, 1)


def without_250(text):
    bullet = insert_250()
    return text.replace(bullet + "\n", "", 1) if bullet else text


def strip(text):
    """The rules as the 338 diffs were cut: without the 347, 339 and 250 wording."""
    return without_250(without_339(without_347(text)))


def restore(text):
    """`text` with back the wording of the patches the tree holds."""
    text = with_347(text) if STATE["347"] else text
    text = with_250(text) if STATE["250"] else text
    return with_339(text) if STATE["339"] else text


def with_347(text):
    for old, new in SUBS_347:
        text = text.replace(new, old).replace(old, new)         # idempotent
    return text


def without_347(text):
    for old, new in SUBS_347:
        text = text.replace(new, old)
    return text

FAMILIES = {
    'Header': [
        'Each update replaces this file; never edit it in a live vault.',
        "Alan's own context and preferences live in the root `CLAUDE.md`, which an update never changes.",
        '**The full detail behind each rule (mechanisms, routes, file contents, history) is in `system/templates/creaite-reference.md`: read the section you need; it never loosens anything here.**',
        'If a file named `.creaite-dev` exists in the vault root, this is the development repository, not a live vault: do **not** run the session-start rules (backup, sweep, reminders, status line), never connect to Microsoft 365 for real data, and work from `dev/BUILD.md` and `dev/HANDOVER.md`.',
        'Only sample data lives here.',
        'Approved items are written to `system/tracker.db` (SQLite, the record).',
    ],
    'Non-negotiables': [
        '**Local, with one exception.**',
        'The engine, the database, staging, backups, history, the search index and git stay in this folder on the laptop and never live in a synced folder.',
        "Project files (minutes, transcripts, reports, project memory and the portfolio files) may live in Alan's **company OneDrive** when the `locations` setting points there (BL-85).",
        'The live database, the git folder and the working files are never synced.',
        'Never personal cloud storage, a web service or a published page.',
        '**Approval before writes.**',
        'Nothing reaches `system/tracker.db` until Alan approves it.',
        'Unattended (scheduled) runs only write proposals to `system/staging/`.',
        "Alan approves in Review, in the dashboard, or by ticking rows in a note's **Find updates** panel and pressing Apply (BL-301: the ticked rows are his approval; new risks, new decisions, milestone moves and health changes start unticked).",
        'Files change only when Alan asks, and every change has a way back (BL-141, below).',
        '**ask creaite is the administrator; the record and the engine stay behind their own commands (Alan, 10-10-2026).**',
        'ask creaite may read and change files across the vault, the projects folder and the home folder, and its own permission files, on these terms, which are enforced in code it cannot change (`reach.py`, the guard hook, `filechange.py`, the live server), never by its prompt:',
        "**Open:** reading anything in reach; ordinary changes (creating files, Alan's notes and drafts, project files he named, staging) are made at once, **backed up first, logged and undoable** (`filechange.py`; Activity › What ask creaite changed).",
        "**Sensitive, on one card:** a permission or settings file (including ask creaite's own), anything outside the vault and the projects folder, a delete or a move, another person's file (a transcript, sent minutes or a report, a client's document), more than ten files in one request, and anything but staging after it has read outside content (mail, Teams, a transcript, a document, a web page; never one of Alan's notes, BL-301).",
        'They are listed together on **one card** with the change shown; **Approve** makes them all, exactly as shown, **Decline** none.',
        "The approval is the live server's, bound to that exact change, used once, at most 30 minutes old; ask creaite can ask for a change but never grant it.",
        "The one exception is **Delete note** from the Notes tab (and a deleted note's **Move back** in Files): Alan's click on the dashboard's own button is the approval, so it has no card, and ask creaite can never make it (#255; Alan, 20-10-2026).",
        "**Never:** secrets (`~/.ssh`, `~/.aws`, keychains, password stores, browser profiles and saved logins), the operating system, the places that run commands on their own (shell start-up files, LaunchAgents, `.git`), and, for any change, the database, the engine, `creaite-rules.md`, `VERSION`, releases and creaite's own records.",
        'A permission change that would run anything, reach those, skip permissions, remove a safety entry, or allow a connector other than the Microsoft 365 reading tools or a built-in that acts outside the laptop (`permissions.tool_problem`: Monitor, SendMessage, the Cron and worktree tools, Artifact, NotebookEdit and the rest) is refused whatever is approved.',
        'Only `system/scripts/tracker.py apply` writes to the database.',
        'Never edit `system/tracker.db` with ad-hoc SQL, and never write to `tracker-view.xlsx` except through `excel_sync.py export`.',
        '**The schema is the rulebook.**',
        "If an apply fails validation, fix the proposal; never loosen `schema.sql` to make data fit without Alan's agreement.",
        'Each item references its file, email or chat.',
        '**Confidential material.**',
        'Exclude anything marked confidential or restricted from client reports unless Alan says otherwise.',
    ],
    'Folder map': [
        'Never changed by an update.',
        'Must stay in the root',
        'One per project: `CLAUDE.md` (project memory, with the client report settings and `Partners:` line), `minutes/`, `transcripts/`, `documents/`, `reports/`, `agendas/`, `notes/`.',
        'Only `minutes/` and `transcripts/` are ever extracted',
        "`99 System` (in the portfolio folder, reserved for creaite's own files and skipped whatever the saved list says), `_Templates` and the archive folders are never indexed",
        'Cross-project meetings and notes, `PORTFOLIO.md`, `project-register.md` and `people-register.md` (the last two are read every run)',
        'Only `tracker.py apply` moves a folder into or out of it; ask creaite never reads, writes or moves anything there',
        "Proposals awaiting review, drafts, ask creaite chats, the run log, `discarded/` (#280: a proposal Alan discards in Review is moved here, never deleted) and creaite's working records.",
        'Those records keep item IDs, references, counts, fingerprints, times and short gists, never message text, join links, passcodes or PINs.',
        "Exceptions, each listed in the reference: `calendar.json` keeps each invite's body as plain text, never join links or passcodes (a confidential meeting keeps only its title and times, BL-98), `vip.json` a gist and Claude's own summary, never message text, and `usage-reviews.jsonl` Alan's own notes (written only by the live server, never by ask creaite)",
        'Written only by the live server and the guard hook; on the never list for everything else',
        'The debug log (BL-102): item IDs, paths, counts and durations only, never the text of mail, minutes, notes or chats',
        '`VERSION`; `dashboard.html` (generated, never edit it by hand); `tracker-view.xlsx`; `system/scripts/` (`tracker.py` is the only database writer, `reach.py` decides what ask creaite may touch, locations come from `paths.py`; Activity › Quality is read only, internal only, never about a person); `system/templates/` (with `creaite-reference.md`); `system/branding/` (local only, out of git; logos stay in the git-ignored folder and never leave the laptop); `system/config/settings.json` (all tunable values; every change is backed up and logged); `.claude/` (must stay in the root); `system/` is never hidden',
    ],
    'Starting a session (creaite rule)': [
        'Read `system/config/settings.json` first; every time, threshold and switch below comes from there (defaults shown).',
        "At the first session of each day, copy `system/tracker.db` to `system/backups/tracker-YYYY-MM-DD.db` (if today's copy doesn't exist yet), then (BL-323) make the day's zip, copy it to the OneDrive backup folder (if OneDrive can't be reached nothing stops), run Tidy up once a day and the restore check once a week.",
        'Then archive the items closed long ago, once a day (BL-10, Retention below).',
        "This rule is the guarantee; the app's scheduler is only an optional extra.",
        '**Reminders (never draft on their own; skip any listed in `settings.json` `reminders.dismissed_forever`):**',
        '**Weekly report** (if `reminders.enabled`): from `reminders.weekly_report_day` `weekly_report_from` (Friday 12:00) for each active project whose report for that week isn\'t approved yet, say "ABC weekly report for week ending DD-MM-YYYY is due — say weekly report ABC for week ending DD-MM-YYYY" (one line per project).',
        '**Client reports:** for each active project that needs a separate client report (`Client report: on` in its `CLAUDE.md`; no line means on) and whose `Client report reminder` is not off, and whose `Client report rhythm` (default weekly) has passed since its last approved client report, say "ABC client report due (last: YYYY-MM-DD) — say client report ABC".',
        'A project with `Client report: off` has no client reminder.',
    ],
    'Skills and commands': [
        '**cx-minutes**: draft Word minutes and proposed items; filed on approval',
        '"review", "review ABC", "what\'s pending", "approve…", "reject…", "apply", "undo last apply", "import excel"',
        '**cx-review**: bulk approval never covers minutes, new decisions or new risks; explicit apply',
        '**cx-edit**: shown before → after, confirmed, written at the next apply',
        "Alan's own Claude Code session only: ask creaite never drafts, stages or writes a report",
        "**cx-client-report**: client-safe; its Word, HTML and PDF files are made only from its checked copy (`client_snapshot.client_export`, #239); a partner's name reaches a client only as its logo picture; risks, issues and decisions appear only if flagged client-visible.",
        "Alan's own Claude Code session only: ask creaite never drafts, stages or writes a report",
        '"steerco one-pager ABC", "steerco one-pager ABC client-safe"',
        '**cx-steerco** (BL-92): drafted to `system/staging/drafts/`, filed on approval, never overwriting.',
        'Never sends, never creates email.',
        'Manual only',
        '**cx-setup**: asks before every change',
        '**cx-setup**: install a release zip, shown first and confirmed; undo the last update',
        '**cx-document** (BL-75): built by `report.py adhoc` into `system/staging/drafts/`; nothing is filed or sent',
        'Rebuild `dashboard.html`: `system/scripts/run build_dashboard.py` (also runs after every apply)',
        'cx-minutes, cx-weekly-report, cx-client-report and cx-steerco are never scheduled (their reminders come from the session-start rule); optional scheduled tasks are in `system/config/schedules.md` and creaite never depends on them.',
    ],
    'Dashboard editing': [
        '**What it writes:** edits, new items, health with a reason, "Current state", and Approve or Reject are written as proposals to `system/staging/` (`source_run: "dashboard"`, already approved); nothing reaches the database until apply.',
        '**Live mode is required** (IT-approved): `system/scripts/run live_server.py` serves the dashboard on `127.0.0.1`; Alan starts it.',
        'If it is not reachable, edits still save to staging, while Apply and the assistant wait.',
        '**What ask creaite may touch (BL-141; Alan, 10-10-2026):** `system/scripts/reach.py` decides (ordinary, sensitive or never; `system/scripts/run reach.py never` prints the never list).',
        "An ask creaite chat starts with a **guard hook** (`reach.py hook`, run before every tool call, whatever a settings file allows; it fails closed) that refuses the never list (also inside a script's arguments), any direct `Edit` or `Write` outside `system/staging/drafts/` (`system/staging/` in a confirmed request; never a proposal or creaite's staging records), any `Bash` that isn't one creaite script run on its own (and never `permissions.py` or `propose.py setting`), any write of a weekly or client report file or draft (reading reports stays open) and, in a run Alan hasn't confirmed, every command that changes the record (`tracker.py apply`, `undo`, `review.py approve`, `reject`, `propose.py stage` and the rest; BL-267).",
        'A run creaite starts itself runs only read commands, and is held away from confidential notes (#60).',
        'A request that is only a sweep is recognised by the live server from its words, never by the model, and runs under the `sweep` mode: it may stage (`sweep.py stage`) and still refuses `tracker.py apply`, `undo`, `review.py approve`, `reject`, `propose.py stage` and any direct write outside `system/staging/drafts/`; anything more ("sweep and apply", an image, a confirmed request) is a plain chat (BL-309).',
        'Every change goes through `filechange.py` (backed up, logged, undoable).',
        "**A note is not outside content (BL-301; Alan, 15-10-2026):** reading one of Alan's notes, a `.md` file directly in a project's or the portfolio's notes folder, marks nothing; a note's pictures (`_images/`), a file in a subfolder of the notes folder and everything else in OneDrive still mark.",
        'A sensitive change is refused by `filechange.py` with "Needs approval" and shown on **one card** when the run ends; Approve issues the one-time approval (`reach.APPROVALS`), which nothing the model can read or run holds.',
        '**Permission files (BL-141):** `.claude/settings.json`, `.claude/settings.local.json`, `~/.claude/settings.json`, `system/config/settings.json` and the other configuration files are changed on approval: the exact content shown, checked before writing and again after (`permissions.settings_problem`), put back if it fails, logged and undoable.',
        '**Editors and notes (BL-301):** AI on selected text only offers a suggestion, which changes nothing until Alan accepts it, and runs Claude with no tools.',
        'Apply from **Find updates** writes the ticked rows as approved proposals in one apply, which Undo reverses.',
        'It writes no file of its own: every change goes through the store that already saves it.',
        'The code is changed only in ask creaite (`recode`); archive goes on the approval card.',
        "One-off Word documents (BL-75) are built by `report.py adhoc` into `system/staging/drafts/`, confirmed first; never `node`, never outside the vault; a project's Word file changes only through `filechange.py edit … --from <the new version in drafts>`.",
        '**Assistant ("ask creaite", ⌘J / Ctrl+J):** the live server runs Claude Code headless in this vault, so CLAUDE.md, skills and permission rules apply; tools are limited by `.claude/settings.json` plus a strict allow list, and anything that changes the record (apply, undo, proposals, drafting reports) is confirmed by Alan in the chat panel first.',
        'One request runs at a time.',
        'Alan can attach up to four PNG or JPEG images (BL-100): they are for discussion only, nothing is extracted from them, and they are deleted with their chat.',
        'Never use a skip-permissions mode.',
        "**Reading is open, all the time (Alan, 2026-10-09):** every Microsoft 365 reading tool, every vault and project file (minus the never list), and every creaite script's read commands, with no prompt; **Microsoft 365 actions stay off** (sending, deleting or changing mail, calendar, Teams or files act outside the laptop and can't be undone), and changes follow BL-141, only through `filechange.py`.",
        'The bulk rule still applies: the dashboard\'s "Approve routine" never covers minutes, reports, health changes, new decisions, a decision being recorded or withdrawn, or new risks.',
    ],
    'Updates': [
        "creaite is updated from a **release zip** (`creaite-X.Y.Z.zip`), never by copying files by hand: cx-setup or the dashboard's Settings installs it with `system/scripts/update.py`, after showing what changes and getting Alan's yes.",
        'An update replaces the **engine** only (`VERSION`, `system/scripts/`, `system/templates/`, `system/creaite-rules.md`, `.claude/skills/`) and adds new keys and permission rules to `settings.json` and `.claude/settings.json`, keeping every existing value.',
        'It never touches the root `CLAUDE.md` or any data.',
        'Never in the development repository (`.creaite-dev`).',
    ],
    'Project documents': [
        '`projects/<CODE> <Name>/documents/` holds key project documents (SOW, budgets, plans); Alan manages the subfolders and every version is kept.',
        '**Agendas (BL-135)** and **Notes (BL-301)** are not documents: Files lists each as its own folder.',
        'Agendas stay **passive** (never extracted, internal by default); search and ask creaite read them as they read documents.',
        '**What creaite may do with project files (BL-93):**',
        '**Read** every project document, whatever its folder.',
        'Never an online-only OneDrive file, `99 Archive` (or the old `_Archive`, `zz Archive`), `_Templates` or `99 System`.',
        'Reading is not extracting.',
        '**Create** a file in a project folder when producing something Alan asked for and approved (a Steerco pack, a report, an image).',
        'Creating never overwrites: a name that is taken gets a number.',
        '**Edit, rename, move or delete** an existing file only when Alan asks for it.',
        "A change to Alan's own notes is made at once; a delete, a move, a transcript, sent minutes or a report, an Office document in the project, or anything after reading outside content waits on the one approval card (BL-141).",
        "Reports are the user's own: ask creaite reads them, never changes them.",
        'Nothing is written unattended.',
        "Writes outside the project folders and the vault need Alan's approval (BL-141).",
        'Documents are **passive**: never extracted; a document changing never triggers anything; Claude reads them when a question or an instruction needs them, and says which it used.',
        'They are **internal by default**: nothing from `documents/` goes into a client report unless Alan explicitly says so.',
        "**Notes are passive until Find updates (BL-301):** never extracted, never read by the sweep or an unattended run, never in a client report; search, ask creaite and Prep read them and cite them (a confidential note's text is kept from Claude unless Alan says yes).",
        "Only Alan's **Find updates** on a note turns its lines into tracker changes, and what it applied is recorded beside the note in `system/staging/notes-sent.json`, never in it.",
    ],
    'Portability rules': [
        'creaite runs on a Mac with the things below and nothing else (macOS, the primary and only tested platform; Python 3.9 or later, the Claude desktop app and `claude` command signed in, Chrome or Edge, Microsoft 365 connected, git; NFR-12, BL-241; tiers in the reference file).',
        '**Runtime never pip installs; dev tools may be installed.**',
        'Nothing creaite runs installs a package or a tool; a missing library is a bundling fault, fixed in `vendor/`.',
        "Every creaite script runs through `system/scripts/run`, given the script's name and its arguments (for example `system/scripts/run doctor.py`).",
        'It runs only a script in `system/scripts/` by its bare name (no `-c`, `-m`, path or other program) and refuses an argument on the never list; every refusal exits 2.',
        'Never store an absolute path.',
        'Scripts take every location from `system/scripts/paths.py`.',
        '`CLAUDE.md`, `VERSION` and `.claude/` stay in the root; everything else lives in `projects/`, `system/` or `dev/`.',
        'Nothing goes in machine or user settings; the launcher and the login agent are the only things outside the vault, both optional.',
        "**Login agent (BL-243, optional):** `~/Library/LaunchAgents` is on `reach.py`'s never list, so ask creaite cannot install, change or remove it, and no permission rule allows `launchctl`.",
        "**Windows** is best effort and untested (Alan, 11-10-2026); ask creaite's protection of secrets is defined for macOS only.",
        'creaite never reads or downloads an online-only file, and `doctor.py` lists them.',
        'One machine only: there is no multi-machine lock.',
    ],
    'Memory rules': [
        'Nothing about this system goes in the user-level `~/.claude/CLAUDE.md`.',
        'Actions, risks, issues, decisions and health live only in `system/tracker.db`.',
        'Memory files describe context and never copy tracker rows.',
        '**Changes need approval.**',
        'Memory changes are proposed, like tracker items, and applied only after Alan approves.',
        'Lines marked `Client-safe: no` never appear in client reports.',
        '**Client-visible items.**',
        'Actions, decisions, and risks and issues carry a `client_visible` flag, off by default.',
        'Only flagged items can appear in a client report.',
        'Set it with cx-edit ("make ABC-002 client-visible").',
        "A partner's name reaches a client only as its logo picture.",
    ],
    'Retention': [
        "**Backups look after themselves (BL-323; Alan, 14-10-2026):** a daily **Tidy up**, after the backup and the zip, removes only files creaite wrote (matched by exact name in their own folder), never the newest of a kind, never in the development repository, not when that day's backup or zip failed, and never from a process an ask creaite run started (`backup.ask_run`); it can't be undone, and Health shows the last run.",
        'ask creaite keeps only the 10 most recent chats (BL-32).',
        '**Archiving (BL-10, BL-03) deletes nothing.**',
        'Once a day, closed or cancelled actions and RAID items, and done or dropped promises, closed `archive.after_months` (6) months ago are flagged archived through `tracker.py apply` (undoable); decisions, milestones and open items never are; editing an item un-archives it; never from an ask creaite run; restoring a project leaves items archived for their age archived.',
        "Weekly and client reports, minutes and Steerco one-pagers older than `archive.reports_after_months` (12) are, on Alan's yes on the approval card (offered monthly in Settings › Health), moved into the engagement's own `99 Archive` by `tracker.py apply` (never by ask creaite), and back, only on the live server's own approval card.",
        'Transcripts, agendas, documents and applied proposals are never archived.',
        "**Delete note (#124; Alan, 15-10-2026)** moves one note into `99 Archive/<notes folder>/`, and back, only by `tracker.py apply` from the dashboard's own button after Alan's confirm box, only the version he confirmed; never from an ask creaite run.",
        "`tracker.py` makes these moves only with the live server's one-time approval, so a proposal written into staging by hand is refused; such a proposal could still remove or copy a note, undoably.",
    ],
    'Conventions': [
        '**Dates (v0.23):** show and accept dates as **DD-MM-YYYY** (except the dashboard\'s Today page, which writes them out: "Thursday 15th October", the year only when it isn\'t this year; Alan, 2026-10-09) (and times as 24-hour HH:MM) in everything Alan reads or types — messages, the dashboard, minutes and report text, the Excel export (cells formatted DD-MM-YYYY) and plain-English commands.',
        'Convert at the edge; never mix the two in one place.',
        "The short code appears **only** as the prefix of a work item's ID (`ABC-A-003`), where a code is defined or typed (settings, the register, commands, filters, search), where a machine matches on it (the register's signals, a `[CODE]` tag, an Outlook category, the **Draft email subject**), and in the command a reminder tells Alan to say.",
    ],
}

LINE_FAMILIES = {
    'Non-negotiables': [
        "The one other thing that leaves the vault is **a closed daily backup zip of what rebuilds the vault** (BL-323; Alan, 14-10-2026), into that same OneDrive folder (`locations.offsite_backup`, which only Alan can open): the day's database backup (a closed copy), `system/config/`, `.claude/settings.local.json`, the root `CLAUDE.md`, `system/staging/` (never ask creaite's chats or their images, and never `vip.json`: VIP is private to Alan, BL-288), the git history as one closed file (a git bundle), the flow history files, `processed.txt` and a manifest.",
        'Microsoft 365 actions stay off.',
    ],
    'Starting a session (creaite rule)': [
        'Unless VIP alerts are off (`vip.enabled`) or nobody is a VIP, check for anything VIPs sent since the last check (cx-sweep\'s "VIPs" section, `--found start-up`) and say "VIP: n new" if any; they head Today until Alan marks them Seen.',
        'A VIP is never dropped by project matching or an ignore rule.',
    ],
    'Skills and commands': [
        'Never sends, never creates email drafts.',
    ],
    'Dashboard editing': [
        '**Run kinds:** the Prep page button, Intake Process, the VIP check are each their own run kind started by the live server, never a chat, with their own fenced mode and hook (see the reference file); a question on the Process row opens ask creaite only when Alan asks, never automatically.',
        "Prep pages are written by the live server, never by Claude, are marked Internal and never sent, and never overwrite a file creaite didn't write or one Alan edited (those get a number); the command line's `prep_page.py build` (cx-prep) saves through `filechange.py` instead (BL-271): logged, undoable, and on the card when the run has read outside content; the VIP check is read-only and never runs in the development repository.",
    ],
    'Conventions': [
        '**VIP is private to Alan (BL-288):** never call or label a person a VIP, or say who is one, in anything creaite writes or may show or share: minutes, reports, the steerco one-pager, prep pages, drafts, proposed items, gists, the Excel export and replies.',
        "The word stays only in the person's own VIP field, the register's VIP column and Settings › Essentials › People I follow.",
    ],
}      # wording before the 2.6.2 follow rules diff

CHAIN_FAMILIES = {
    'Non-negotiables': [
        "The one other thing that leaves the vault is **a closed daily backup zip of what rebuilds the vault** (BL-323; Alan, 14-10-2026), into that same OneDrive folder (`locations.offsite_backup`, which only Alan can open): the day's database backup (a closed copy), `system/config/`, `.claude/settings.local.json`, the root `CLAUDE.md`, `system/staging/` (never ask creaite's chats or their images, and never `vip.json`: who Alan follows stays on the laptop, BL-288), the git history as one closed file (a git bundle), the flow history files, `processed.txt` and a manifest.",
        "Microsoft 365 actions stay off, with one exception (#183; Alan, 19-10-2026): with **Create drafts in Outlook** on (`draft_email.outlook_drafts`, off by default) the live server's own token-checked route (`POST /api/email/draft`) may create an Outlook draft, and only a draft: it never sends, updates or deletes one, ask creaite can never do it, and every other Microsoft 365 action stays refused.",
    ],
    'Starting a session (creaite rule)': [
        'Unless follow alerts are off (`vip.enabled`, an internal name) or nobody is followed, check for anything the people you follow sent since the last check (cx-sweep\'s follow section, `--found start-up`) and say "Followed: n new" if any; they head Today until Alan marks them Seen.',
        'A followed person is never dropped by project matching or an ignore rule.',
    ],
    'Skills and commands': [
        'Never sends.',
        "An email about it follows the Draft email setting (#183): off, it is copied and pasted; on, the live server puts it in Alan's Outlook Drafts folder for him to check and send.",
        'The report is never sent.',
    ],
    'Dashboard editing': [
        '**Run kinds:** the Prep page button, Intake Process, the Follow check and Draft email delivery are each their own run kind started by the live server, never a chat, with their own fenced mode and hook (see the reference file); a question on the Process row opens ask creaite only when Alan asks, never automatically.',
        "Prep pages are written by the live server, never by Claude, are marked Internal and never sent, and never overwrite a file creaite didn't write or one Alan edited (those get a number); the command line's `prep_page.py build` (cx-prep) saves through `filechange.py` instead (BL-271): logged, undoable, and on the card when the run has read outside content; the Follow check is read-only and never runs in the development repository; **Create draft in Outlook** (#183) makes a draft only and never sends.",
    ],
    'Conventions': [
        '**The follow flag is shown in the app; the word VIP never is (BL-288, revised; Alan, 23-10-2026):** a person Alan follows carries the **follow flag** (one per person, in their People entry, "Follow this person").',
        'It is the only such mark creaite shows, and only inside the app: the "people you follow" alerts on Today, first in Review, the Work funnel\'s People I follow filter and the early warning.',
        'Never use the word VIP, or any other label of importance, in anything a client can see or that creaite writes, exports or shares: minutes, reports, the steerco one-pager, prep pages, drafts, proposed items, gists, the Excel export and replies; and never say in any of them who is followed.',
        '**Hidden stays private to each laptop** (F3), as does the list of who is followed until Alan decides otherwise (open question 1 in `dev/proposals/vip-follow-rules/README.md`).',
        "The word VIP may remain only in internal names that are never shown, exported or shared (code, `vip.*` settings keys, `vip.json`) and, until it is migrated, in the register's old `VIP` column.",
    ],
}     # wording after it

REWORDED = {"never a proposal or creaite's staging records), and any `Bash` that isn't one creaite script run on its own (and never `permissions": "never a proposal or creaite's staging records), any `Bash` that isn't one creaite script run on its own (and never `permissions.py` or `propose.py setting`)", "never Claude's": 'never by Claude',
    'never extracted by the sweep or an unattended run': 'never extracted, never read by the sweep or an unattended run',
    "never overwrites a file creaite didn't write or one Alan edited (those get a number), replaces creaite's own unchanged page for the same meeting and day after a copy to `system/backups/files/`, and records what it wrote in `system/staging/prep-pages": "never overwrite a file creaite didn't write or one Alan edited (those get a number)", 'never by the model, is its own confirmation': 'never by the model, and runs under the `sweep` mode',
    'never drafts, stages or writes a report (reports are made and edited in the Reporting hub) | Specified |': 'never drafts, stages or writes a report',
    'never edit it by hand |': 'never edit it by hand',
    'never extracted, internal by default), and search and ask creaite read them as they read documents': 'never extracted, internal by default)',
    'never message text, BL-99': 'never message text,',
}

# clause -> (why it may live in the reference, the pointer text that stays in the rules)
MAPPED = {
    'never any text, passcode or PIN, BL-42 phase 3), `intake-cleared': ('what transcripts.json holds (code writes it); the rules keep the general limit', 'never message text, join links, passcodes or PINs'),
    'never automatically)': ("how the Process row's button behaves (dashboard code); the rules keep it", 'opens ask creaite only when Alan asks, never automatically'),
    "never by ask creaite or the page's own storage": ("who writes usage-reviews.jsonl (the live server's route); the rules keep it", 'written only by the live server, never by ask creaite'),
    'never ending in `original`), the older `<CODE>-partner': ('how a logo file is named (report_server.py); no rule on behaviour', 'system/templates/creaite-reference.md'),
    'never hidden |': ("kept as it was in the Other paths cell; only the table's closing bar makes it a different clause", '`system/` is never hidden'),
    'never in a release)': ('says the dashboard source is development only; no rule on behaviour', 'system/templates/creaite-reference.md'),
    'never into)': ('the old archive folder names, read for one release; the rules keep the current rule', 'ask creaite never reads, writes or moves anything there'),
    'never list names macOS places (`Library/Keychains`, browser profiles under `Library/Application Support`) and would not protect `%APPDATA%`': ('says which places the never list names on macOS; the rules keep the Windows limit', "ask creaite's protection of secrets is defined for macOS only"),
    'never mid-job': ('how the optional launcher stops the server; a convenience outside the vault', 'system/templates/creaite-reference.md'),
    'never needed to run creaite)': ('says development tools are optional; no rule on behaviour', 'dev tools may be installed'),
    'never path in every argument form, an unquoted `#`, `**` or a `~` followed by anything but `/`, `reach': ('the argument forms reach.py refuses; the rules keep the refusal', "refuses the never list (also inside a script's arguments)"),
    'never raises': ("a script's description (usage_log.py); no rule on behaviour", 'system/templates/creaite-reference.md'),
    "never sends, called by the live server's route)": ("a script's description (draft_delivery.py); the rules keep that a draft is never sent", 'makes a draft only and never sends'),
    'never stops by itself)': ('how a server started by hand behaves; a convenience outside the vault', 'system/templates/creaite-reference.md'),
    'never text': ('what a staging record holds (code writes it); the rules keep the general limit', 'never message text, join links, passcodes or PINs'),
    'never text)': ('what a staging record holds (code writes it); the rules keep the general limit', 'never message text, join links, passcodes or PINs'),
    'never text), `agendas': ('what a staging record holds (code writes it); the rules keep the general limit', 'never message text, join links, passcodes or PINs'),
    'never text), `drafted': ('what a staging record holds (code writes it); the rules keep the general limit', 'never message text, join links, passcodes or PINs'),
    'never text), `notes-sent': ('what a staging record holds (code writes it); the rules keep the general limit', 'never message text, join links, passcodes or PINs'),
    'never text), `run-usage': ('what a staging record holds (code writes it); the rules keep the general limit', 'never message text, join links, passcodes or PINs'),
    "never the text of a prompt, a skill's arguments, a reply, a name or a path": ('what run-usage.jsonl holds (code writes it); the rules keep the general limit', 'never message text, join links, passcodes or PINs'),
    'never the text or the name of a file': ('what context-size.jsonl holds (code writes it); the rules keep the general limit', 'never message text, join links, passcodes or PINs'),
    'never their text': ('what drafted.json holds (code writes it); the rules keep the general limit', 'never message text, join links, passcodes or PINs'),
}

FRAGMENTS = set(['Never', 'never (the table is in `dev/BUILD', 'never are', 'never in it', 'never list', 'never list)', 'never list, and changes files only through `filechange', 'never` prints the never list)'])      # the bare word, or a term ("never list"), not a rule

# (state, text in the slimmed rules, edited text): every one must turn the check red
MUTANTS = [
    ("both", "in a run Alan hasn't confirmed, every command that changes the record", "in a run"),
    ("both", "A run creaite starts itself runs only read commands", "A run creaite starts itself runs commands"),
    ("both", "still refuses `tracker.py apply`, ", "still refuses "),
    ("both", "Only flagged items can appear in a client report.", "Flagged items can appear in a client report."),
    ("both", "flag, off by default.", "flag, on by default."),
    ("both", "up to four PNG or JPEG images", "up to forty PNG or JPEG images"),
    ("both", "checked before writing and again after", "checked before writing"),
    ("both", ", which nothing the model can read or run holds", ""),
    ("both", "or one Alan edited (those get a number)", ""),
    ("both", "made only from its checked copy", "made from its checked copy"),
    ("both", "only as its logo picture", "as its logo picture"),
    ("both", "started by the live server, never a chat", "started by the live server, a chat"),
    ("both", "never the newest of a kind", "the newest of a kind"),
    ("both", "**Decline** none", "**Decline** some"),
    ("both", "a note's pictures (`_images/`), a file in a subfolder of the notes folder and everything else in OneDrive still mark", ""),
    ("both", "; such a proposal could still remove or copy a note, undoably", ""),
    ("both", ", only the version he confirmed", ""),
    ("both", "Never use a skip-permissions mode.", ""),
    ("both", "Manual only", "Manual"),
    ("both", "Must stay in the root", "Stay in the root"),
    ("both", "(if OneDrive can't be reached nothing stops)", ""),
    ("both", "One request runs at a time.", ""),
    ("both", "**Microsoft 365 actions stay off**", "**Microsoft 365 actions stay on**"),
    ("both", "never from an ask creaite run; restoring", "restoring"),
    ("both", "Runtime never pip installs", "Runtime may pip install"),
    ("both", "Never store an absolute path.", "Store an absolute path."),
    ("both", "confirmed by Alan in the chat panel first", "confirmed"),
    ("both", "a confidential meeting keeps only its title and times", ""),
    ("both", "never message text, join links, passcodes or PINs", "message text"),
    ("both", "refuses the never list (also inside a script's arguments)", "refuses the never list"),
    ("both", "Lines marked `Client-safe: no` never appear in client reports", "Lines marked `Client-safe: no` appear in client reports"),
    ("both", "show and accept dates as **DD-MM-YYYY**", "show and accept dates as **YYYY-MM-DD**"),
    ("both", " (`system/staging/` in a confirmed request; never a proposal or creaite's staging records)", ""),
    ("both", "bulk approval never covers minutes, new decisions or new risks", "bulk approval covers minutes"),
    ("both", "ask creaite never drafts, stages or writes a report", "ask creaite drafts reports"),
    ("both", "Never an online-only OneDrive file", "An online-only OneDrive file"),
    ("both", "Only `system/scripts/tracker.py apply` writes to the database.", "`system/scripts/tracker.py apply` writes to the database."),
    ("both", "never write to `tracker-view.xlsx` except through `excel_sync.py export`", "write to `tracker-view.xlsx`"),
    ("both", "Nothing reaches `system/tracker.db` until Alan approves it.", "Alan approves `system/tracker.db` changes."),
    ("both", "anything more (\"sweep and apply\", an image, a confirmed request) is a plain chat", ""),
    ("both", "A note is not outside content (BL-301; Alan, 15-10-2026)", "A note is outside content"),
    ("both", "Creating never overwrites", "Creating overwrites"),
    ("both", "Transcripts, agendas, documents and applied proposals are never archived.", ""),
    ("both", "Reports are the user's own: ask creaite reads them, never changes them.", "Reports are the user's own."),
    ("both", "never `node`, never outside the vault", "never `node`"),
    ("both", "never by Claude", ""),
    ("both", "and never runs in the development repository", ""),
    ("line", "never call or label a person a VIP", "never label a person a VIP"),
    ("chain", "Never use the word VIP, or any other label of importance", "Never use the word VIP"),
    ("chain", "and never say in any of them who is followed", ""),
    ("chain", "makes a draft only and never sends", "makes a draft"),
]

FLIPS = [("never", "may"), ("Never", "May"), ("Only", "Also"), ("only", "also"), ("off by", "on by"), ("four", "forty"), ("nothing", "something"),
         ("every", "some"), ("stay off", "stay on"), (" not ", " "), ("unless", "and"), ("refus", "allow")]


def _stop(cell, i, depth, tick):
    """Whether the full stop at cell[i] ends a sentence: outside brackets and backticks, then a space or the bold mark."""
    if cell[i] != "." or tick or depth:
        return False
    after = cell[i + 1:i + 3]
    if re.search(r"(e\.g|v0)$", cell[max(0, i - 3):i]):
        return False
    return after[:1] == " " or after == "**" or after == "* " or i + 1 == len(cell)


def _split_cell(cell):
    out, start, depth, tick, i = [], 0, 0, False, 0
    while i < len(cell):
        ch = cell[i]
        tick = not tick if ch == "`" else tick
        depth += (ch in "([" and not tick) - (ch in ")]" and not tick and depth > 0)
        if _stop(cell, i, depth, tick):
            i += 2 if cell[i + 1:i + 3] == "**" else 0
            out.append(cell[start:i + 1].strip())
            start = i + 1
        i += 1
    out.append(cell[start:].strip())
    return out


def sentences(text):
    """Rules text as sentences: split at newlines, table bars, and a full stop outside brackets and backticks."""
    out = [s for line in text.split("\n") for cell in line.split("|") for s in _split_cell(cell)]
    return [re.sub(r"^(- )+", "", s).strip() for s in out if s.strip()]


def git_apply(text, diff, reverse=False):
    """`text` with `diff` applied (or reversed) on a scratch copy of system/creaite-rules.md; None if it does not apply."""
    d = Path(tempfile.mkdtemp(prefix="creaite-test-338-"))
    try:
        (d / "system").mkdir()
        (d / "system/creaite-rules.md").write_text(text, encoding="utf-8")
        cmd = ["git", "apply"] + (["-R"] if reverse else []) + [str(diff)]
        r = subprocess.run(cmd, cwd=d, capture_output=True, text=True)
        return (d / "system/creaite-rules.md").read_text(encoding="utf-8") if r.returncode == 0 else None
    finally:
        shutil.rmtree(d, ignore_errors=True)


def states():
    """(original, slim) for the tree's state, whichever way round the tree is."""
    tree = RULES.read_text(encoding="utf-8")
    STATE["347"], STATE["339"], STATE["250"] = MARK_347 in tree, MARK_339 in tree, MARK_250 in tree
    if STATE["347"] or STATE["339"] or STATE["250"]:
        orig, slim = _states(strip(tree))          # work out the 338 state on the wording the 338 diffs were cut on
        return restore(orig), restore(slim)
    return _states(tree)


def _states(tree):
    if "creaite-reference.md" in tree:
        for diff in DIFFS:
            orig = git_apply(tree, diff, reverse=True)
            if orig is not None:
                return orig, tree
        raise AssertionError("the slimmed rules are in the tree but no 338 diff reverses on them")
    for diff in DIFFS:
        slim = git_apply(tree, diff)
        if slim is not None:
            return tree, slim
    raise AssertionError("no 338 diff applies to the tree's creaite-rules.md")


def never_clauses(text):
    """Every "never" clause: from the word to the next . ; : or line end."""
    out = set()
    for m in re.finditer(r"(?i)\bnever\b", text):
        end = next((i for i in range(m.end(), len(text)) if text[i] in ".;:\n"), len(text))
        out.add(text[m.start():end].strip(" ,"))
    return out


def section(text, name):
    m = re.search(r"(?ms)^## " + re.escape(name) + r"\n.*?(?=^## |\Z)", text)
    return m.group(0) if m else ""


def guard_paragraph(text):
    m = re.search(r"(?m)^> \*\*Development guard\.\*\*.*$", text)
    return m.group(0) if m else ""


def fixture(chain):
    """name -> whole sentences for the state, state-specific wording included."""
    out = {k: list(v) for k, v in FAMILIES.items()}
    if STATE["347"]:                      # the cx-review trigger cell as the 347 diff words it
        out["Skills and commands"] = [with_347(x) for x in out["Skills and commands"]]
    for k, v in (CHAIN_FAMILIES if chain else LINE_FAMILIES).items():
        out.setdefault(k, []).extend(v)
    return out


def missing_in(slim, name, chain):
    sents = fixture(chain).get(name, [])
    return [s for s in dict.fromkeys(sents) if slim.count(s) < sents.count(s)]


def missing(slim, reference, orig, chain):
    """Everything that is no longer where it must be, as a list (empty when all is well)."""
    out = [s for name in fixture(chain) for s in missing_in(slim, name, chain)]
    out += [new for old, new in REWORDED.items() if old in orig and new not in slim]
    for clause, (_why, pointer) in MAPPED.items():
        if clause not in orig:
            continue                                  # a clause of the other state's wording
        if pointer not in slim:
            out.append(pointer)
        if clause not in reference:
            out.append(clause)
    for name in ("Non-negotiables",):
        if section(orig, name) != section(slim, name):
            out.append("section " + name)
    if guard_paragraph(orig) != guard_paragraph(slim):
        out.append("Development guard")
    return out


def unaccounted(orig, slim, chain):
    """Never clauses of the original that nothing above or the rules themselves hold."""
    held = [s for v in fixture(chain).values() for s in v]
    bad = []
    for c in sorted(never_clauses(orig)):
        if c in MAPPED or c in FRAGMENTS or c in REWORDED:
            continue
        if any(c in s for s in held) or (len(c.split()) >= 6 and c in slim):
            continue
        bad.append(c)
    return bad


def flip(sentence):
    for old, new in FLIPS:
        if old in sentence:
            return sentence.replace(old, new, 1)
    return sentence[:-6]


class RetainedRules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if shutil.which("git") is None:
            raise unittest.SkipTest("git is needed to apply the diff on a scratch copy")
        cls.orig, cls.slim = states()
        cls.chain = CHAIN_MARK in cls.orig
        cls.ref = REFERENCE.read_text(encoding="utf-8")

    def test_the_347_substitutions_are_what_the_347_diff_does(self):
        """SUBS_347 stands in for the 347 diff: applied to the tree's rules (without the 347 wording) the real diff must give the
        same file (so the substitutions cannot drift from the diff)."""
        if not RULES_347.exists():
            self.skipTest("no 347 diff in this tree")
        plain = strip(RULES.read_text(encoding="utf-8"))
        applied = git_apply(plain, RULES_347)
        self.assertIsNotNone(applied, "dev/proposals/347/creaite-rules.md.diff no longer applies to the rules")
        self.assertEqual(applied, with_347(plain))

    def test_the_339_insertion_is_what_the_339_diff_does(self):
        """INSERT_339 stands in for the 339 diff, as SUBS_347 does for the 347 diff."""
        if not RULES_339.exists():
            self.skipTest("no 339 diff in this tree")
        plain = strip(RULES.read_text(encoding="utf-8"))
        applied = git_apply(plain, RULES_339)
        self.assertIsNotNone(applied, "dev/proposals/339/creaite-rules.diff no longer applies to the rules")
        self.assertEqual(applied, with_339(plain))

    def test_the_non_negotiables_and_the_development_guard_are_unchanged(self):
        self.assertNotEqual(section(self.orig, "Non-negotiables"), "")
        self.assertEqual(section(self.slim, "Non-negotiables"), section(self.orig, "Non-negotiables"))
        self.assertEqual(guard_paragraph(self.slim), guard_paragraph(self.orig))
        for name in ("Local, with one exception", "Approval before writes", "ask creaite is the administrator", "Open:", "Sensitive, on one card",
                     "Never:", "One writer", "The schema is the rulebook", "Source on every row", "Confidential material"):
            self.assertIn("**" + name, section(self.slim, "Non-negotiables"))

    def test_nothing_is_missing_and_the_unmutated_rules_are_green(self):
        self.assertEqual(missing(self.slim, self.ref, self.orig, self.chain), [])

    def test_every_never_clause_of_the_original_is_accounted_for(self):
        self.assertEqual(unaccounted(self.orig, self.slim, self.chain), [], "a never clause is in neither the fixture nor the imported rules")

    def test_mapped_clauses_say_why_and_keep_a_pointer(self):
        for clause, (why, pointer) in MAPPED.items():
            self.assertTrue(why and pointer, clause)
            if clause in self.orig:
                self.assertIn(pointer, self.slim, "no pointer line in the rules for: " + clause)
                self.assertIn(clause, self.ref, "a moved clause is not in the reference: " + clause)

    def test_reworded_clauses_exist_whole_in_both(self):
        for old, new in REWORDED.items():
            if old in self.orig or old in self.ref:
                self.assertIn(new, self.slim)

    def test_the_rules_are_at_least_half_smaller(self):
        # the #250 bullet is one addition to both states, outside what 338 slims (the margin is a few bytes), so it is left out of the sizes
        self.assertLessEqual(len(without_250(self.slim).encode()), 0.5 * len(without_250(self.orig).encode()),
                             "the slimmed rules must be at most half the size")

    def test_the_rules_point_to_the_reference_and_it_says_it_never_loosens_them(self):
        self.assertIn(REF_PATH, self.slim)
        self.assertIn("never loosens `creaite-rules.md`", self.ref)

    def test_the_skills_table_and_dates_survive(self):
        rows = [ln for ln in self.slim.splitlines() if ln.startswith('| "')]
        self.assertGreaterEqual(len(rows), 12)                 # build_dashboard reads these rows
        self.assertIn("DD-MM-YYYY", self.slim)
        self.assertIn("YYYY-MM-DD", self.slim)

    def test_the_diffs_apply_forward_and_reverse(self):
        orig, slim = strip(self.orig), strip(self.slim)      # the 338 diffs were cut before the 347 and 339 wording
        self.assertEqual(git_apply(orig, DIFFS[1 if self.chain else 0]), slim)
        self.assertEqual(git_apply(slim, DIFFS[1 if self.chain else 0], reverse=True), orig)

    def test_the_line_diff_adds_no_chain_wording(self):
        line_slim = git_apply(strip(self.orig), DIFFS[0]) if not self.chain else None
        if line_slim is not None:
            for word in ("Follow check", "Create draft in Outlook", "People you follow"):
                self.assertNotIn(word, line_slim)

    def test_named_mutants_turn_it_red(self):
        killed = 0
        for state, old, new in MUTANTS:
            if state != "both" and (state == "chain") != self.chain:
                continue
            self.assertIn(old, self.slim, "mutant does not apply: %r" % old)
            mutant = self.slim.replace(old, new)
            self.assertNotEqual(mutant, self.slim)
            self.assertTrue(missing(mutant, self.ref, self.orig, self.chain), "mutant stays green: %r -> %r" % (old, new))
            killed += 1
        self.assertGreaterEqual(killed, 40)

    def test_every_fixture_sentence_deleted_or_flipped_turns_it_red(self):
        count = 0
        for name, sents in fixture(self.chain).items():
            for s in dict.fromkeys(sents):
                self.assertGreaterEqual(self.slim.count(s), sents.count(s))
                for mutant in (self.slim.replace(s, "", 1), self.slim.replace(s, flip(s), 1)):
                    self.assertTrue(missing(mutant, self.ref, self.orig, self.chain), "%s: stays green: %r" % (name, s[:80]))
                    count += 1
        for old, new in REWORDED.items():
            if old in self.orig:
                self.assertTrue(missing(self.slim.replace(new, "x", 1), self.ref, self.orig, self.chain))
                count += 1
        for clause, (_why, pointer) in MAPPED.items():
            if clause in self.orig:
                self.assertTrue(missing(self.slim.replace(pointer, "x"), self.ref, self.orig, self.chain))
                count += 1
        self.assertGreater(count, 250)

    def test_the_fixture_sentences_are_whole_sentences_of_the_rules(self):
        have = sentences(self.slim)
        bad = [s for sents in fixture(self.chain).values() for s in dict.fromkeys(sents) if s not in have]
        self.assertEqual(bad, [])


def _family_test(name):
    def test(self):
        self.assertEqual(missing_in(self.slim, name, self.chain), [])
    test.__name__ = "test_family_" + re.sub(r"\W+", "_", name.lower()).strip("_")
    return test


for _name in sorted(set(FAMILIES) | set(LINE_FAMILIES) | set(CHAIN_FAMILIES)):
    _t = _family_test(_name)
    setattr(RetainedRules, _t.__name__, _t)


if __name__ == "__main__":
    unittest.main()
