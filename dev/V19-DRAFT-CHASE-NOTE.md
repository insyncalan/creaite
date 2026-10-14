# v19-draft-chase: BL-298's Draft chase pane (v1.9.0)

Team 2, 13-10-2026. Branch `v19-draft-chase`, from `origin/v19-base`. Not pushed (the main session pushes).

## What was built

- **The icon:** a Draft chase envelope (with an arrow) in the peek's `#pkBar`, immediately left of Copy link; key **C**. Shown for an
  open action, risk or issue and a pending decision; hidden for closed, cancelled, made or withdrawn items, proposals and new items.
- **The pane**, inside the peek (`#pkChase` takes `#pkScroll`'s place, Back or Esc returns to the item), as drawn in
  `dev/mockups/draft-chase-mockup.html`: the mode line, To (chip and email; for Alan's own item the suggestions with their why and
  + Anyone), To get … done and What I need from you (help only), Reply by beside Tone, Include the latest update, the email with
  its To and Subject lines, then the result line, Copy as text, I sent it and Copy for Outlook (primary). No "VIP" anywhere.
- **Preact, as COMPONENTS.md says:** `src/components/peek/ChasePane.jsx` (`ChasePane`, `ChaseEmail`, `mountChase`), JSX-only text,
  icons as element data (`CHASE_ICON`, also fed to `ICONS.chase` for the bar's `ibtn`). panel.js mounts it (block `BL-298
  (v19-draft-chase)` at its end, `bootPanelChase` in main.js after `bootPanel0166`).
- **The email** is drawn in its fixed colours (Calibri, `DE_COLOURS`) whatever the theme, every element styled inline, so the
  preview is what Outlook gets. Copy for Outlook serialises that DOM (`XMLSerializer`: no new `innerHTML`, the sink count is
  unchanged) as `text/html` with the server's plain text as `text/plain`; Copy as text gives the subject and the plain text.
- **I sent it** posts `/api/chases {ids:[id], mode}`, updates `SA().chases` and says "Recorded: chased Sara on 13-10-2026. The next
  one will be a second reminder."; the preview steps up to the next tone.
- **Polish** (Alan, 13-10-2026, option A; `dev/mockups/draft-chase-polish-mockup.html`): one row under the email, above the
  buttons, with **Polish the wording** (Polish again once one is in use) and no Warm/Neutral/Firm chips: it uses the pane's Tone
  (First → warm, Second → neutral, Firmer → firm, `POLISH_TONES`). Someone else's item and a decision: the opening only (kind
  `polish`). Alan's own item: kind `polish-help` (drafts.py, prompt `system/templates/drafts/polish-help.md`), which also suggests
  To get … done and What I need from you; the server reads the item itself and the model gets the opening, the item's wording, its
  latest update, Alan's two lines and the tone, never the table, subject or addresses. Yours beside Polished (or Suggested), Keep
  mine or Use this; the subject line then shows a Polished tag. Changing the tone or the two lines drops it. AI drafts off: the
  button greyed (aria-disabled) with the reason under it. Counted under `email` like the Draft email's Polish (`polishAsk`, shared).

## Server routes

Both routes the doc names are on `v19-base` and used as they are: `POST /api/chase/pane` (called again 150 ms after each change,
with `to`, `tone`, `reply_by`, `include_update`, `outcome`, `need`, `cover`) and `POST /api/chases`. Nothing stubbed.

## One server change: chase mode in the singular (Alan's decision)

Alan decided "Chase mode uses singular wording for one item"; `drafts.py` still had DE_CHASE's plural texts. Added
`CHASE_WORDING["chase_one"]` (the three openings and asks in the singular; the subjects, the reply-by sentence, the thanks and
"Kind regards," stay DE_CHASE's) and used it in `_chase_words`. `CHASE_WORDING["chase"]` still equals the page's `DE_CHASE`
(the person page's multi-item chase is unchanged, and the test comparing them still passes). `test_draft_chase.py`'s tone test
now expects the singular texts.

## Tests

- New: `dev/tests/test_draft_chase_pane.py` (14, Chrome, the real live server): the icon's place, name, key and when it shows; C,
  Back and Esc; C while typing; each mode with its defaults and wording; the preview following tone, date, the latest update, the
  outcome and the need as typed; suggestions and + Anyone; the email's colours in the dark theme; Copy for Outlook (a stubbed
  clipboard: HTML as plain as the Draft email's, with its text fallback), Copy as text, a refused clipboard; Polish off; I sent it
  (chases.json holds IDs, a date and the mode only; the next one steps up; Alan's own item recorded as help).
- `test_draft_chase.py`: 25, passing with the singular wording.
- Goldens: only `work-panel` changed (the peek's bar gains the icon and the hidden `#pkChase`), re-recorded deliberately.
- `check.py`: OK; the type check: 0.

## Help and spec

- `system/templates/help.md`: the How-to (already there from the server sprint) gains Esc and Use mine; the keys table gains C;
  the icon legend gains the envelope. Guides rebuilt.
- `dev/dashboard-spec.md`: a new section "Draft chase in the peek (BL-298)" and the toolbar line.

## Open

- The mockup's chip has a "×"; it isn't built: for Alan's own item a suggestion or + Anyone replaces the recipient, and for the
  others the recipient is the owner or decision maker. Say if the × is wanted (it would need "no recipient yet" from the server,
  which today falls back to the first suggestion).
- + Anyone is a search box and up to eight matches as buttons, not yet the shared Combobox block (COMPONENTS.md lists it, not built).
- The person page's chase note (`chaseNote`) reads `SA().chases`, so it shows the new chase the next time that page is drawn.
