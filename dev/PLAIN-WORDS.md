# Plain words

The words creaite uses in anything the user reads, and the words it never shows. Agreed by Alan on 22-10-2026 (plain words programme, extends BL-313; release v2.6.1).

**The rule.** A user never sees a file path, a script name or the word "sweep". Engineering words stay in code, logs, the debug log and Settings › Diagnostics, never on any other screen, message, reply or Help page a user reads.

**User-visible text** means the dashboard (every page, card, button, toast and error), messages the live server returns to the dashboard, ask creaite's replies, printed reminders and status lines, and the Help. It does not mean code identifiers, comments, logs, Diagnostics or Help's developer pages.

## The agreed words

| Engineering word | Say instead | Where it appears today (examples) |
|---|---|---|
| sweep (noun) | **mail and Teams check** (short: "the check") | Today: "Sweep due since 07:00" → "Mail and Teams not checked yet today"; "The last sweep was…" → "The last check was…"; "No calendar yet: it comes in with the sweep" → "…with the next check" |
| Run sweep / Run the first sweep | **Check now** / **Run the first check** | Today, Intake |
| swept / has not been swept | "Mail and Teams haven't been checked yet" | Today, Health |
| Sweep time; Settings group "Sweep" | **Daily check time**; group **Checking mail and Teams** | Settings › Advanced |
| catch-up sweep | "a last check of mail and Teams" | Close the day |
| ignore list; "Keep noise out of the sweep" | **what creaite skips** (rules) | Settings |
| proposal / proposed | **suggestion** | Review: "Claude's proposals. N waiting" → "Suggestions. N waiting"; "Decide one proposal at a time"; "Approves every routine proposal" |
| stage / staged | **save for review** / "waiting in Review" | "Stage for review", "Staged for review"; your own change reads "Saved", with Undo (BL-313) |
| apply / applied | **save** / **approve** | Apply button → **Save approved items**; "Apply stopped. Nothing was written." → "Nothing was saved." |
| tracker | **your project record** (or "your work items") | "Updating the tracker", "Checked against the tracker", "isn't in the tracker". Lower priority: acceptable if explained once |
| vault | **your creaite folder** / "creaite" | "Search the vault" → **Search everything**; "the vault isn't connected"; "isn't in the vault yet" |
| live server / server | **creaite** ("creaite isn't running") | "The live server isn't reachable" → "creaite has stopped. Reopen the creaite app, or paste this into Terminal: <the start command>" (the stopped alert and Settings › Health › Diagnostics are the only two places that show the restart command); "Saving needs the live server"; "Live server needed: search runs through it" |
| extract / extraction / re-extract | **find items in the meeting** / "read it again" | Intake, minutes: "so you can check the extraction", "never extracted" |
| refused / "whatever is approved" | "creaite can't do that", with one plain reason | Approval card, permission messages |
| unknown field / invalid / validation errors | Name the meeting and the item, never the file: "One suggestion (Budget review, decision 1) couldn't be saved. It needs fixing in Review." | Apply errors, e.g. "unknown field(s) for decisions: raised. Valid: …" |
| file paths and file names | the folder's friendly name ("your drafts", "the project's minutes folder"), with an **Open** button | Apply error naming `proposed-….json`; "source not found" naming an inbox file; messages naming `system/staging/` or `.claude/settings.json` |
| script names, commands, skill names | nothing: creaite runs it for the user. A command that truly must be typed is shown only in Settings › Diagnostics | Restart alert with `system/scripts/run live_server.py`; "filechange.py undo"; "cx-edit"; "review.py" |

## Banned in user-visible text

These must not appear outside Diagnostics, logs and Help's developer pages. The guard test (step 2 of the programme) fails on them.

- **Words:** sweep, swept, sweeping; proposal, proposed (as a noun or status); stage, staged, staging; apply, applied (as the save step); vault; live server; extract, extraction, re-extract; refused; unknown field; valid/invalid (as a validation message). "tracker" is discouraged, not banned.
- **Path patterns:** `system/`, `projects/`, `inbox/`, `.claude/`, `_portfolio`, `.json`, `.jsonl`, `.py`, `.db`, `.vtt`.
- **Names:** any `cx-` skill name, any script name (`tracker.py`, `review.py`, `live_server.py`, `filechange.py` and the rest), `system/scripts/run`, `python`/`python3`.

## Chat commands

ask creaite keeps understanding the old commands (`sweep`, `apply`, `process new minutes`) so nothing breaks. Replies, the Help and any hint teach the plain ones: "check my mail", "save", "process the meeting".

## Where the words change (fix plan)

1. This glossary.
2. A guard test over user-visible strings (banned words, path patterns, `cx-` names), with Diagnostics, logs and Help's developer pages allow-listed by name.
3. Tier 1: every path, script name and "sweep" on screen (Today, Settings, Intake, Close the day, save errors, Health) and the server messages that carry a path.
4. Tier 2: suggestion, save, project record, creaite folder and "creaite isn't running" across the dashboard and ask creaite's replies (BL-313).
5. Tier 3: the Help rewrite and the chat command wording.

A review pack with before and after screenshots per tier goes to Alan before commit.

## Step 2: the guard test (#290)

`dev/tests/test_plain_words.py` checks every user-visible string against the banned list above, and
`dev/tests/plain_words_baseline.json` holds its data. It is a ratchet: the count may only fall.

- **What it reads.** The dashboard (the built page's script, module by module, and the shell's text and visible
  attributes, with HTML tags taken out first), the Help (`help.md` and What's new), and the Python messages that reach
  the dashboard (values under a message key such as `message`, `error`, `problem` or `why`, `("problem", …)` pairs, the
  message of a `raise`, and `print` in `session.py` and `tracker.py`). Comments, logs, keys, class names, selectors and
  addresses are skipped.
- **What fails.** A string that breaks a rule and isn't in the baseline (a new offender), or a baseline offender that has
  gone (it was fixed or reworded): take it out so the count can't climb back. Each offender is its file, its rule and a
  fingerprint of the string, so moving code within a file changes nothing.
- **Warn, not fail.** `severity` in the data file: `"tracker": "warn"` reports and never fails until Tier 2 (#292) lands;
  then delete that line and it fails like the rest.
- **Allow-lists** are by file (`allow.files`: Diagnostics' and the debug log's own code, `doctor.py`) or by identifier
  (`allow.identifiers`: one function, `settings.js#diagCardHtml`, or one Help section, `help.md#<section title>`), each
  with its reason. Never by word: a visible string that says "stage", "valid" or "refused" still fails everywhere else.
- **Run it:** `python3 dev/tests/test_plain_words.py`. It prints the offenders per rule and the total.
- **After fixing offenders** (Tier 1 to 3), rewrite the baseline and commit it with the fix:
  `CREAITE_UPDATE_PLAIN_BASELINE=1 python3 dev/tests/test_plain_words.py`. It rewrites only `offenders` and keeps
  `severity` and `allow`. A rewrite that adds offenders needs a deliberate reason in the commit message.
- **The dashboard is read from the built page** (`system/templates/dashboard.html`): rebuild it after changing its source
  (`check.py` fails until you do).
