# Rules changes for #183, in plain words

For Alan to read before approving. One diff to `system/creaite-rules.md` plus one skill file.
Nothing else in the rules changes. It is on `v262-183`, in `dev/proposals/`.

1. `draft-delivery/rules-and-skill.diff` (#183): the rules file and `.claude/skills/cx-client-report/SKILL.md`. It applies in either order with the VIP-follow rules diff.

Changes in the order they appear in the file.

## 1. Never list, last sentence (#183)
- **Before:** "Microsoft 365 actions stay off."
- **After:** the same, "with one exception": when **Create drafts in Outlook** is on (off by default), the live server's own route,
  `POST /api/email/draft`, may create an Outlook draft. Only a draft. It never sends, updates or deletes one, ask creaite can never
  do it, and every other Microsoft 365 action stays refused.
- **Why:** you retired "never creates email drafts" on 19-10-2026 and IT now allows `outlook_create_draft`. This keeps the door that narrow.

## 2. Folder map, `system/staging/` row (#183)
- **#183 adds** `drafted.json`: each Draft email put in Outlook or copied, as item IDs, times and fingerprints of the subject and
  addresses; never text. **Why:** the chase log needs to know a draft exists without keeping its words.

## 3. Folder map, `system/scripts/` row (#183)
- **Adds** `draft_delivery.py`: builds and checks the Outlook draft request, records the chase, matches Sent Items. Plain code;
  never sends; called only by the live server's route. **Why:** every script is listed here.

## 4. Skills table, "client report ABC" row (#183)
- **Before:** "Never sends, never creates email drafts."
- **After:** "Never sends." An email about it follows the Draft email setting: off, copy and paste; on, the live server puts it in your
  Outlook Drafts folder for you to check and send. The report itself is never sent. **Why:** the old wording would contradict item 1.
- The skill file says the same in three places (its description, its opening line and its Rules): "this skill never creates a draft;
  only the popup does, through the live server."

## 5. New bullet "Draft email delivery" (#183), after the Project settings page bullet
- **Adds** the one place the whole mechanism is stated: the setting and its Outlook access Check; the popup's primary button; the
  route runs Claude headless with one allowed tool (ToolSearch) and one tool that only its hook can allow (`outlook_create_draft`: no hook, or a hook that fails, means no draft), every other Microsoft 365 tool, every other
  connector and every other built-in denied, in an empty folder outside the vault with no settings loaded, so it can read nothing;
  the hook in the run checks every tool call before it runs and is the only way the draft is allowed: once, with exactly the subject, To and HTML shown
  (an injected To, Cc, Bcc or a second draft is refused before anything is made; Cap's M1), and the server checks afterwards that exactly one was made; the body is the preview's own HTML;
  the chase is logged when the draft is made (not "I sent it") and marked sent when a sweep sees it in Sent Items; a refusal records
  nothing and offers Copy instead; off means copy and paste as before. **Why:** this is the guard's definition; a reader of the rules
  sees what is allowed and what is checked.

## 6. Assistant ("ask creaite") bullet (#183)
- **Adds** one sentence after "Microsoft 365 actions stay off": the one exception is not ask creaite's; it is the popup's
  Create draft in Outlook (item 5). **Why:** so ask creaite's own bullet cannot be read as allowing it.

## What does not change
`permissions.py` and `reach.py` stay as they are: `outlook_create_draft` stays in the Microsoft 365 action list, so every other run
still denies it and no settings file can allow it. The allow exists only in the live server's route (a separate diff, `live_server.diff`).
