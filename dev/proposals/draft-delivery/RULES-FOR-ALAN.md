# Rules changes for #183 and #250, in plain words

For Alan to read before approving. Two diffs to `system/creaite-rules.md`, applied in this order, plus one skill file.
Nothing else in the rules changes. Both are on `v262-183`, in `dev/proposals/`.

1. `draft-delivery/rules-and-skill.diff` (#183): the rules file and `.claude/skills/cx-client-report/SKILL.md`.
2. `fetch-transcripts/creaite-rules.diff` (#250): rules file only. It applies only after step 1 (both edit the same staging row).
   If Jarvis's `vip-follow-rules` diff is applied first, use `fetch-transcripts/creaite-rules.after-vip.diff` instead of step 2
   (the VIP diff and the #250 diff both edit the cx-sweep row, so the plain one fails after it). The VIP diff and #183 apply in either order.

Changes in the order they appear in the file.

## 1. Never list, last sentence (#183)
- **Before:** "Microsoft 365 actions stay off."
- **After:** the same, "with one exception": when **Create drafts in Outlook** is on (off by default), the live server's own route,
  `POST /api/email/draft`, may create an Outlook draft. Only a draft. It never sends, updates or deletes one, ask creaite can never
  do it, and every other Microsoft 365 action stays refused.
- **Why:** you retired "never creates email drafts" on 19-10-2026 and IT now allows `outlook_create_draft`. This keeps the door that narrow.

## 2. Folder map, `system/staging/` row (#183, then #250)
- **#183 adds** `drafted.json`: each Draft email put in Outlook or copied, as item IDs, times and fingerprints of the subject and
  addresses; never text. **Why:** the chase log needs to know a draft exists without keeping its words.
- **#250 adds** to `transcripts.json` the times a sweep fetched a transcript, left it for Process or could not save it (and a count
  of tries); and a new `sweep-fetched.json` (event IDs only, cleared when the sweep finishes). **Why:** so a transcript is fetched
  once and a failure is visible.

## 3. Folder map, `system/scripts/` row (#183)
- **Adds** `draft_delivery.py`: builds and checks the Outlook draft request, records the chase, matches Sent Items. Plain code;
  never sends; called only by the live server's route. **Why:** every script is listed here.

## 4. Skills table, "client report ABC" row (#183)
- **Before:** "Never sends, never creates email drafts."
- **After:** "Never sends." An email about it follows the Draft email setting: off, copy and paste; on, the live server puts it in your
  Outlook Drafts folder for you to check and send. The report itself is never sent. **Why:** the old wording would contradict item 1.
- The skill file says the same in three places (its description, its opening line and its Rules): "this skill never creates a draft;
  only the popup does, through the live server."

## 5. Skills table, cx-sweep row (#250)
- **Adds:** with `sweep.fetch_transcripts` on (off by default) a sweep also fetches ended meetings' transcripts into `inbox/`: read
  only, Microsoft 365 reading tools only, no AI, nothing to the tracker; never a confidential meeting or one whose sensitivity is
  missing or unknown. **Only in the live server's own run: no script writes `inbox/`**, so a sweep from Claude Code never fetches
  (option 2, chosen by Jarvis/Alan 23-10-2026; you can overrule). **Why:** transcripts arrive without you pressing Load.

## 6. New bullet "Draft email delivery" (#183), after the Project settings page bullet
- **Adds** the one place the whole mechanism is stated: the setting and its Outlook access Check; the popup's primary button; the
  route runs Claude headless with exactly two tools (`outlook_create_draft`, ToolSearch), every other Microsoft 365 tool, every other
  connector and every other built-in denied, in an empty folder outside the vault with no settings loaded, so it can read nothing;
  a hook in the run checks every tool call before it runs and lets the draft through once, with exactly the subject, To and HTML shown
  (an injected To, Cc, Bcc or a second draft is refused before anything is made; Cap's M1), and the server checks afterwards that exactly one was made; the body is the preview's own HTML;
  the chase is logged when the draft is made (not "I sent it") and marked sent when a sweep sees it in Sent Items; a refusal records
  nothing and offers Copy instead; off means copy and paste as before. **Why:** this is the guard's definition; a reader of the rules
  sees what is allowed and what is checked.

## 7. Assistant ("ask creaite") bullet (#183)
- **Adds** one sentence after "Microsoft 365 actions stay off": the one exception is not ask creaite's; it is the popup's
  Create draft in Outlook (item 6). **Why:** so ask creaite's own bullet cannot be read as allowing it.

## What does not change
`permissions.py` and `reach.py` stay as they are: `outlook_create_draft` stays in the Microsoft 365 action list, so every other run
still denies it and no settings file can allow it. The allow exists only in the live server's route (a separate diff, `live_server.diff`).
