# Rules changes for #183 and #250, in plain words

For Alan to read before approving. Two diffs to `system/creaite-rules.md`, applied in this order, plus one skill file.
Nothing else in the rules changes. Both are on `v262-183`, in `dev/proposals/`.

1. `draft-delivery/rules-and-skill.diff` (#183): the rules file and `.claude/skills/cx-client-report/SKILL.md`.
2. `fetch-transcripts/creaite-rules.diff` (#250): rules file only. It applies only after step 1 (both edit the same staging row).
   **Recommended order: #183, then Jarvis's VIP diff (`vip-follow-rules/creaite-rules.md.diff`), then `fetch-transcripts/creaite-rules.after-vip.diff`.**
   After the VIP diff the plain #250 diff fails (both edit the cx-sweep row), so use `after-vip` then. The VIP diff and #183 apply in either
   order. All orders tested against the real VIP diff (29e03fd9) on release2: see `RULES-ORDER.md`.

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
- **After:** "Never sends, never creates email drafts (the Draft email popup has no client-report email; #183's Outlook draft is a
  separate feature)." **Why (Cap's L3):** an earlier wording said a client report's email follows the Draft email setting. That is not
  built: the popup builds an update request, a chase and a meeting or minutes follow-up only. The text now claims nothing more.
- The skill file changes only its Rules line (the description and opening line keep "never creates email drafts", which is still true
  of the skill): "the popup's Outlook draft is the live server's own feature for its update, chase and follow-up emails; there is no
  client-report email, and this skill never uses it."

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
  nothing and offers Copy instead; off means copy and paste as before. It covers only the emails the popup builds (update request,
  chase, meeting and minutes follow-up); the chase is recorded for an update request or a chase only (L3: no client-report email exists). **Why:** this is the guard's definition; a reader of the rules
  sees what is allowed and what is checked.

## 7. Assistant ("ask creaite") bullet (#183)
- **Adds** one sentence after "Microsoft 365 actions stay off": the one exception is not ask creaite's; it is the popup's
  Create draft in Outlook (item 6). **Why:** so ask creaite's own bullet cannot be read as allowing it.

## What does not change
`permissions.py` and `reach.py` stay as they are: `outlook_create_draft` stays in the Microsoft 365 action list, so every other run
still denies it and no settings file can allow it. The allow exists only in the live server's route (a separate diff, `live_server.diff`).

## 8. NEW, proposed for you to approve or strike: "leaves the vault" (Cap's L4)
The first non-negotiable says only a closed backup zip leaves the vault. An Outlook draft does too (subject, To and body go to your
own mailbox), so it should be said. **Proposed new bullet, added after "Confidential material" (not in the "Local" bullet: Jarvis's VIP
diff edits that line and the two would conflict):**
> **A draft in Outlook is the one email that leaves the vault (#183; Alan to approve).** With **Create drafts in Outlook** on
> (`draft_email.outlook_drafts`, off by default), the email shown in the Draft email popup (its subject, To addresses and body) goes to
> Alan's own Outlook Drafts folder, only when he presses that button. It is a draft in his own mailbox: nothing is sent, and nothing
> else is written to Microsoft 365.

It is in `rules-and-skill.diff`. To leave it out, delete that one `+` line (and its hunk) before applying; nothing else depends on it.
