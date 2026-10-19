# #183 Draft email delivery: put the draft in Outlook (2.6)

**Approved and locked by Alan, 19-10-2026.** Mockup: `dev/mockups/draft-delivery-mockup.html`, built on the Settings snapshot with the app's real popup classes. Fictional data. The guard design is Jarvis's; this brief is the setting, its wording and what the user sees.

## The decision (Alan, 19-10-2026, relayed by Jarvis)
"Never creates email drafts" is retired. Creating an Outlook draft is allowed when a setting says so, because some people can write to Outlook and some cannot; the setting switches between the two, off where they cannot write. It is a draft only: creaite never sends.

## The setting
- **Where:** Settings › Essentials, a new card **Draft email**, setting key `draft_email.outlook_drafts`, **off by default**.
- **Label:** Create drafts in Outlook.
- **Help text:** "Off: creaite builds the email and you copy and paste it into Outlook. On: creaite puts it in your Outlook Drafts folder, ready for you to check and send. It never sends anything. Turn it off if you can't write to Outlook."
- **Outlook access row (accepted):** a **Check** button that asks Outlook whether drafts can be created and says so: "You can create drafts in Outlook (checked hh:mm)." or "Outlook says you can't write here, so drafts stay copy and paste." (and turns the setting off). Without it a person who cannot write only finds out on the first draft.

## What the user sees in the Draft email popup
| | Off (today) | On |
|---|---|---|
| Header line | "Nothing is sent: copy it and paste it into Outlook" | "Nothing is sent: creaite puts a draft in your Outlook Drafts folder, for you to check and send" |
| Buttons | Copy email, Copy as plain text, I sent it (chase only), Close | **Create draft in Outlook** (primary), **Copy email, Copy as plain text (kept, Alan 19-10)**, Close. No I sent it |
| After | "Copied" | "Draft created in Outlook (your Drafts folder). Open it there to check and send. Open in Outlook"; the button reads Draft created |
| Chase | recorded when you press I sent it | recorded when the draft is created; marked sent when a sweep finds the email in Sent Items. If you copy the email instead, the sweep finding it in Sent Items records it |
| If Outlook refuses | n/a | "Outlook would not create the draft (reason). Nothing was sent and nothing was recorded." with **Copy it instead** and a pointer to the setting; the email is kept |

The draft's body is the preview as edited, so what is on screen is what lands in Outlook (same HTML as the copy). Subject and addresses as shown.

## Two rules from Alan (19-10-2026)
- **No stored address does not stop the draft.** If the person has no email address on record, the draft is still created in Outlook, with nothing in To. The popup says so before ("No email address on record for <name>. The draft is still created, with nothing in To: add the address in Outlook.") and after ("It has no recipient yet: add the address in Outlook."). With the setting off, the popup says to add the address when pasting. The chase is still recorded.
- **Keep today's rich email.** The draft's body is the preview's own HTML exactly as built today (its colours, the table, the project name heading, overdue dates in red, the greeting and sign-off); nothing is simplified or turned into plain text. The Outlook draft carries that HTML, and the subject and the To as shown. A test compares the draft's body to the preview's HTML.

## Rules (Jarvis's guard design, for the build)
Default off; drafts only, never send; ask creaite stays read-only; the live server's token-checked route makes the draft; the chase is logged without "I sent it". Also: the Microsoft 365 write tool is allowed only for create-draft and only from that route; `permissions.py` and `reach.py` still refuse every other M365 action; the rules file's "Microsoft 365 actions stay off" and cx-client-report's "never creates email drafts" are rewritten to say so (Jarvis's guarded pass).

## Decided (Alan, 19-10-2026)
1. A chase steps up when the draft is created, and shows "sent" once a sweep sees it in Sent Items.
2. A client email draft follows the same on/off setting (a client report is still never sent).
3. The **Outlook access** row (Check button) is wanted.
4. The Copy buttons stay in the On mode beside Create draft in Outlook; only I sent it goes.

## Done when
The setting exists and is off by default; on, the popup creates a draft in Outlook and nothing else; off, today's popup is unchanged; a refusal keeps the email and offers Copy; the chase is recorded without "I sent it"; tests cover the route (draft created, refused, never sent) and the guard.
