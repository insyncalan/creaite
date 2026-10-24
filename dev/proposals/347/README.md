# #347: plain words (check my mail, save, undo last save): the guarded patches

For Alan. Three small patches, none applied yet. This page says what each does, the risk, what you approve, and how they are pinned.

## What changes for you
- You can say **check my mail** instead of "sweep" (same thing; "sweep" keeps working).
- You can say **save** instead of "apply" and **undo last save** instead of "undo last apply" (the old words keep working).
- Help already shows the plain words first (this is on the branch, not a patch).

## The three patches (in this folder)
| Patch | Goes to | Needs |
|---|---|---|
| `creaite-rules.md.diff` | `system/creaite-rules.md` (the skills table: two rows get more trigger words) | **Your approval of the exact text below** (the rules file is guarded) |
| `live_server.py.diff` | `system/scripts/live_server.py` (adds "save" to the words a sweep thread subject may not contain, plus a marker comment) | Full review (guarded chain) |
| `skills.diff` | `.claude/skills/cx-sweep, cx-review, cx-edit, cx-weekly-report` (SKILL.md wording) | Full review; skills are not on the guarded chain list, so review is by hand |

Apply in any order, with `git apply dev/proposals/347/<name>` from the repo root. They apply cleanly on main and with the #358 patch in either order (Cap checked).

## H1: the rules wording for you to approve (exact diff)
Two table cells only; nothing is removed and no "never" sentence changes:
```diff
diff --git a/system/creaite-rules.md b/system/creaite-rules.md
index b9f094b1..2f687016 100644
--- a/system/creaite-rules.md
+++ b/system/creaite-rules.md
@@ -56,10 +56,10 @@ Paths are defined once in `system/scripts/paths.py`; keep this table in step wit
 | Alan says | Skill or action | Status |
 |-----------|-----------------|--------|
 | "process new minutes", "process <file>", "process <meeting>", "re-extract", "note: …" | **cx-minutes**: draft Word minutes and proposed items; filed on approval | Specified |
-| "sweep", "sweep mail", "sweep mail for ABC", "sweep the last 7 days", "sweep the <subject> thread", "refresh calendar" | **cx-sweep**: mail and Teams become proposals; runs at session start when due; skips what `sweep.ignore` (BL-97) matches; records anything a VIP sends (BL-99) as an alert first | Specified |
+| "check my mail", "check my mail for ABC", "sweep", "sweep mail", "sweep mail for ABC", "sweep the last 7 days", "sweep the <subject> thread", "refresh calendar" | **cx-sweep**: mail and Teams become proposals; runs at session start when due; skips what `sweep.ignore` (BL-97) matches; records anything a VIP sends (BL-99) as an alert first | Specified |
 | "prep for the <meeting>", "prep page for the ABC steering" | **cx-prep** (BL-98): one Internal HTML prep page, saved in the Agendas folder | Built |
 | "follow Mia Hale", "mark the follow alerts seen" | **People you follow (BL-99)**: the follow flag in the person's People entry (cx-edit); alerts in `system/staging/vip.json` (`sweep.py vip`), shown at the top of Today | Built |
-| "review", "review ABC", "what's pending", "approve…", "reject…", "apply", "undo last apply", "import excel" | **cx-review**: bulk approval never covers minutes, new decisions or new risks; explicit apply | Specified |
+| "review", "review ABC", "what's pending", "approve…", "reject…", "save", "apply", "undo last save", "undo last apply", "import excel" | **cx-review**: bulk approval never covers minutes, new decisions or new risks; explicit apply | Specified |
 | "mark ABC-A-003 done", "set sweep time to 06:30", "add an action for ABC…", "move ABC go-live to 2026-11-20", "add to ABC memory…", "add project DEF…", "close project ABC", "archive project ABC", "restore project ABC", "change project ABC's code to XYZ", "add Sara Khan to the people register" | **cx-edit**: shown before → after, confirmed, written at the next apply | Specified |
 | "weekly report", "weekly report ABC" | **cx-weekly-report**: manual, with a Friday reminder; blocks projects with pending items. Alan's own Claude Code session only: ask creaite never drafts, stages or writes a report | Specified |
 | "client report ABC" | **cx-client-report**: client-safe; its Word, HTML and PDF files are made only from its checked copy (`client_snapshot.client_export`, #239); a partner's name reaches a client only as its logo picture; risks, issues and decisions appear only if flagged client-visible. Never sends. An email about it follows the Draft email setting (#183): off, it is copied and pasted; on, the live server puts it in Alan's Outlook Drafts folder for him to check and send. The report is never sent. Manual, with a per-project reminder. Alan's own Claude Code session only: ask creaite never drafts, stages or writes a report | Specified |
```
Approve by replying with these words, or send changes: "Approved: creaite-rules.md.diff for #347 exactly as in dev/proposals/347/README.md."

## Risk
- **"save" means apply, but only as the whole message after a shown list (Cap's M3, fixed).** cx-review, cx-edit and cx-weekly-report now say the same: "save", "save ABC" or "save all", only after a list of approved items shown in this session, never for a note, a setting or a draft; otherwise ask; and the skill says "Saving n approved items: <IDs>" before it runs `tracker.py apply`. In your own Claude Code session no hook backs this up, so it rests on those words. "Save the draft" is never an apply (weekly report says so).
- **ask creaite:** unchanged. `tracker.py apply` and `undo` are refused in an unconfirmed run whatever the words (BL-267); the server never reads "save" as a command.
- **Sweep words:** "check my mail" already starts a sweep on main (#291). The live-server patch only makes "save" inside a thread subject ("sweep the budget save thread") a plain chat, so it can only refuse more.
- **Known, already on main, not changed here:** a capitalised word after "for" counts as a project code ("check my mail for UNDO" still sweeps, and only stages); a few edge wordings ("check my mailbox") are not covered by the tests.

## How the patches are pinned
- `live_server.py.diff` adds the comment `# #347:` above the list. `test_panel_sweep` skips until that marker is in the file; **once it is, "save" must be in the list or the test is red** (taking "save" out turns it red, it no longer skips).
- `test_v265_plain_words` skips until the skills diff is applied; once it is, cx-review, cx-edit and cx-weekly-report must each contain "whole message", "a note, a setting or a draft" and "Saving n approved items".
- `test_rules_retained_338` now accepts the rules with the 347 wording (it takes the 347 words off, works out the 338 state, puts them back on both sides), and a test checks those substitutions against the real diff, so no "never" sentence can be lost unnoticed. Passes with and without the diffs applied.

## Live-server patch, exact
```diff
diff --git a/system/scripts/live_server.py b/system/scripts/live_server.py
index 1d0867e6..5e474103 100644
--- a/system/scripts/live_server.py
+++ b/system/scripts/live_server.py
@@ -2323,7 +2323,8 @@ PANEL_SWEEP_WORDS = re.compile(
 # capitals or holds a digit; a short lower-case one (abc) is accepted unless it is a common word; anything else is a plain chat.
 PANEL_SWEEP_FOR = re.compile(r"\bfor ([a-z][a-z0-9]{2,6})\b", re.I)
 PANEL_SWEEP_COMMON = frozenset({"the", "all", "any", "now", "you", "one", "two", "new", "day", "mail", "me", "my"})
-PANEL_SWEEP_NOT = re.compile(r"\b(?:and|then|also|plus|apply|approve|reject|undo|stage|confirm|delete|send|close)\b", re.I)
+# #347: "save" is a second instruction too (Alan's plain word for apply); a thread subject may not carry it
+PANEL_SWEEP_NOT = re.compile(r"\b(?:and|then|also|plus|apply|save|approve|reject|undo|stage|confirm|delete|send|close)\b", re.I)
 
 
 def panel_sweep_code_ok(code):
```

## Where it goes after you approve
Apply all three on the release branch (not before the 2.6.5 gate), run `test_panel_sweep`, `test_v265_plain_words`, `test_rules_retained_338`, `test_plain_words`, `test_help`, `test_guard_pinned`, `test_reach` and `check.py`, then the usual Full review. After the update, the new words reach the live vault with the engine.
