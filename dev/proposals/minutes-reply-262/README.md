# Proposal #262: AI on the minutes sheet can't add anything internal to the Distributed version

> **Apply order:** #186's diff first. On its own: then this `edit_ai.diff`. With #263 too: #186, then #263's diff, then
> **`edit_ai-after-263.diff`** (not `edit_ai.diff`). The other order (#262's plain diff before #263) makes #263's diff fail a hunk, and
> #263's guard then stops `edit_ai.py` from loading, on purpose.

Alan said yes to this on 20-10-2026 (decision 6 of #186). `edit_ai.py` is guarded-adjacent, so it is not changed on this branch:
`edit_ai.diff` is the change, and it applies **on top of #186's diff** (apply #186 first). No page change is needed: the page already
shows a dropped suggestion's message. The help (Reference › minutes) has one new line.

## What is wrong today

You edit minutes on the **Internal** sheet; the **Distributed** version, which goes to attendees who may be outside, is made from it
(Internal-only lines, and Sensitive, partner-only or excluded items, are left out). The sheet's AI bar (Shorten, Make it executive,
Polish, Ask…) gives Claude the project's full facts (every open item ID and owner), and its reply gets **no client check**. So a
suggestion on an ordinary (distributed) line could bring in an internal item or an internal owner's name, and once you press Use it is
in the Distributed minutes.

Worked example (fictional). The selected line is "The statement of work is with the client." You press Polish. Claude replies "The
statement of work is with the client; ABC-005 (vendor exit risk) is also open, and Omar Ali is chasing." Today that is offered as is.

## What is chosen

- **Facts: unchanged.** The sheet edits the Internal minutes, which rightly hold internal items and owners, so Claude still gets the
  full facts, and the sheet's prompt stays exactly as shipped (test_edit_ai_client_place's frozen prompts still hold).
- **Reply: checked for what it ADDS.** The client check (`client_problems`, the client sheet's check) runs on the suggestion, and any
  finding the selected text already had is set aside: what you wrote is yours. A suggestion is **dropped** when it adds:
  - an item a client may not see (not client-visible, Sensitive, partner-only, excluded by a label, another project's), however the ID
    is written (`ABC-005`, `abc 005`);
  - a person's name that the selected text and the client-visible items' owners don't give;
  - the tracker's internal health reason, an internal-only marker, or the word VIP.
- **Fails closed.** Minutes with no project behind them, or a tracker or people register that can't be read: the suggestion is
  dropped with the usual reason (nothing to check against).
- The check runs on every line of the sheet, Internal-only lines too: the server can't tell which line the selection is on without
  trusting the page, and Claude shouldn't add facts anywhere (its prompt already says so). That is the strict side.

## Review fixes (693f0406)

- **VIP in the selection no longer hides the reply.** The client check stops at the word VIP, so a selection holding it used to let
  any reply through. Now the word is checked on its own (a reply that adds it is dropped) and taken out of both texts before the rest
  of the check, which then runs in full: "Our VIP sponsor is happy." plus an added internal item, owner, health reason or marker is
  dropped; a reply that only keeps the selection's own word passes. The message never says VIP (BL-288).
- **HTML inside an ID or a name** (`ABC<!-- -->-A-004`, `<b>ABC</b>-A-004`, `ABC-A-00<b>4</b>`, `Om<b>ar</b> Ali`): every reply check
  (the minutes sheet, the client sheet, the outside email) now also reads the text with HTML tags and comments taken out. It only
  adds findings.
- **Minutes with no project, or an unknown one, are refused before Claude runs** ("These minutes have no project in the tracker, so
  a suggestion couldn't be checked before it reaches the Distributed version; nothing was sent to Claude."), instead of a run whose
  every reply is dropped.

## What you will see

- A suggestion that adds something internal: "The suggestion was dropped: it added something internal (an item that isn't
  client-visible, a name or internal wording) that the Distributed version would carry. Try again, or edit the minutes yourself."
- Minutes with no project, or a project the tracker doesn't hold: refused before Claude runs (the message above).
- Everything else: as today.

## What can still go wrong

- **The same limits as the client checks (#127):** odd spellings (`A B C - A - 0 0 4`, `ABC 5`, "ABC A zero zero four"), "O. Ali" or a
  paraphrase of the health reason in a reply are not caught.
- **Your own text.** An internal item or name already in the line you select stays (it is yours); if that line is not Internal-only it
  goes to the Distributed version as today. Marking the line Internal-only is still how to keep it out.
- **A tampered page** could claim another place for the sheet; the server can't see which page is open (the #123 limit).
- **Portfolio minutes** with no project code can't be checked, so their suggestions are always dropped (fails closed).

## Decisions for Alan

1. **Check what the reply adds, keep the full facts.** Recommended (as above).
2. **No project means no suggestion** on the minutes sheet (fails closed). Recommended: yes; say if portfolio minutes should instead be
   checked against every project.

## How to apply and undo

- Apply, from the repo root, after #186: `patch -p0 < dev/proposals/minutes-reply-262/edit_ai.diff` (`-p0`: no `a/` or `b/` prefix).
  #262 and #263 both change `result()`: when #263 is already applied, use `edit_ai-after-263.diff` instead (the same change, written
  for that file; it keeps #263's client-field check).
- Undo: `patch -R -p0 < dev/proposals/minutes-reply-262/edit_ai.diff` (before undoing #186).
- Tests: `python3 dev/tests/test_minutes_reply_262.py`. `MR_262_UNPATCHED=1` gives the copy #186 only (the dropping tests go red);
  `MR_262_MUTATE=<name>` breaks one piece and must go red.

## Size and risk

- Size: **S.** About 90 lines in `edit_ai.py` (after the review fixes): `MINUTES_PLACES`, `minutes_problems`, and `_reply_problems`, which `result()` now calls
  for the minutes sheet, the client place and the outside email (the same checks as before for those two; `result()` itself got
  simpler). No `live_server.py` change, no page change.
- Risk: low. More suggestions may be dropped on the minutes sheet, only when they add something internal.
- Needs: an independent review of the diff.

## Found while reviewing, a separate item (not changed here)

The ✦ redraft of one minutes section (`drafts.py`, kind `minutes-section`, `build_minutes_section` and `minutes_version`) is a
different path from the sheet's AI bar. Today it builds its facts from `minutes_record.distributed_of` (the Distributed version: no
Internal-only line, no withheld item), refuses an Internal-version section that holds an Internal-only line, gives Claude no tracker
item IDs or owners (its `code` is empty), and drops a Distributed section that names VIP; but its reply gets no `client_problems`
check, so a redraft could still bring in an internal item ID or an owner's name from Claude's own words. It is the same risk as
#262, smaller (Claude isn't given the facts), and more than a few lines to close (the section needs its minutes' project and the
same "what it adds" check), so it wants its own item: run `minutes_problems` on the section reply against the minutes' project.
