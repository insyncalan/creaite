# #183 Draft email delivery: put the draft in Outlook (2.6)

Mockup (for Alan): `dev/mockups/draft-delivery-mockup.html`, built on the Settings snapshot with the app's real popup classes. Fictional data. The guard design is Jarvis's; this brief is the setting, its wording and what the user sees.

## The decision (Alan, 19-10-2026, relayed by Jarvis)
"Never creates email drafts" is retired. Creating an Outlook draft is allowed when a setting says so, because some people can write to Outlook and some cannot; the setting switches between the two, off where they cannot write. It is a draft only: creaite never sends.

## The setting
- **Where:** Settings › Essentials, a new card **Draft email**, setting key `draft_email.outlook_drafts`, **off by default**.
- **Label:** Create drafts in Outlook.
- **Help text:** "Off: creaite builds the email and you copy and paste it into Outlook. On: creaite puts it in your Outlook Drafts folder, ready for you to check and send. It never sends anything. Turn it off if you can't write to Outlook."
- **Outlook access row (proposed):** a **Check** button that asks Outlook whether drafts can be created and says so: "You can create drafts in Outlook (checked hh:mm)." or "Outlook says you can't write here, so drafts stay copy and paste." (and turns the setting off). Without it a person who cannot write only finds out on the first draft. To confirm with Alan.

## What the user sees in the Draft email popup
| | Off (today) | On |
|---|---|---|
| Header line | "Nothing is sent: copy it and paste it into Outlook" | "Nothing is sent: creaite puts a draft in your Outlook Drafts folder, for you to check and send" |
| Buttons | Copy email, Copy as plain text, I sent it (chase only), Close | **Create draft in Outlook** (primary), Close. No copy buttons, no I sent it |
| After | "Copied" | "Draft created in Outlook (your Drafts folder). Open it there to check and send. Open in Outlook"; the button reads Draft created |
| Chase | recorded when you press I sent it | recorded when the draft is created; marked sent when a sweep finds the email in Sent Items |
| If Outlook refuses | n/a | "Outlook would not create the draft (reason). Nothing was sent and nothing was recorded." with **Copy it instead** and a pointer to the setting; the email is kept |

The draft's body is the preview as edited, so what is on screen is what lands in Outlook (same HTML as the copy). Subject and addresses as shown.

## Rules (Jarvis's guard design, for the build)
Default off; drafts only, never send; ask creaite stays read-only; the live server's token-checked route makes the draft; the chase is logged without "I sent it". Also: the Microsoft 365 write tool is allowed only for create-draft and only from that route; `permissions.py` and `reach.py` still refuse every other M365 action; the rules file's "Microsoft 365 actions stay off" and cx-client-report's "never creates email drafts" are rewritten to say so (Jarvis's guarded pass).

## Open points
1. **When a chase steps up:** at creation of the draft (as "I sent it" does today), or only once a sweep sees it sent? Recommendation: step up at creation, and show "sent" once seen, so a draft left unsent is visible rather than lost.
2. Whether the Check button is wanted (above).
3. **Client emails and the client-report skill:** the report's "never creates email drafts" line goes; a client report is still never sent, and a client email draft follows the same on/off setting. Confirm with Alan.

## Done when
The setting exists and is off by default; on, the popup creates a draft in Outlook and nothing else; off, today's popup is unchanged; a refusal keeps the email and offers Copy; the chase is recorded without "I sent it"; tests cover the route (draft created, refused, never sent) and the guard.
