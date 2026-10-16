# Help Phase A: acceptance checks (17-10-2026)

How to review Cap's batch 1 quickly. Written for the reviewer (Jarvis, or the review-round agent).

## Run

```
python3 dev/tools/help_acceptance.py            # prints a Markdown report, changes nothing
python3 dev/tools/help_acceptance.py --strict   # exits 1 if any check fails (for the test)
```

It reads `system/templates/help.md` against the targets in `dev/sprints/help-phase-a-brief.md`.

## What it checks

1. **Word budget:** each page against its target in the brief (flagged when more than 15 percent over), and the total against 14,791 words. Pages in the brief that do not exist yet are listed as "not yet present".
2. **Banned words and promises:** `cx-`, `BL-` numbers, `/api/`, `.json`, `staging`, `system/`, "Alan", "To decide" (renamed Intake and Review), "press Esc twice", 320 and 640 pixel and high-contrast promises, "Windows", "Ctrl", run meta-text. Text in backticks (Or say: phrases, commands) is skipped.
3. **House style:** the three parts in order; every How do I… page has "Where:", numbered steps and "Or say:".
4. **Settings paths:** the first level must be Essentials, People and projects, Advanced or Health; the second level is looked up in `settings_catalogue.py` and listed for a hand check if not found.
5. **Links inside Help:** every `](#…)` resolves to a page.
6. **Unique page ids.**

## Baseline on today's Help (main, before the rewrite)

70 pages and 33,506 words against a budget of 14,791 (over by 18,715). 39 pages are over their targets, and the banned-word check finds 43 hits (mostly Ctrl, Windows, "To decide", 320 and 640). The rewrite is done when the report says ALL CHECKS PASS.

## What it does not check (the reviewer still does)

- That nothing true was lost: compare each rewritten page with the old text and the code.
- That every route, button name and file name exists (the identity check from HOW-WE-WORK).
- Tone: short sentences, steps that start with a verb and name the button in bold.
- The "Checked against" line (the brief says each page records what it was checked against; the test for that line is Cap's).
