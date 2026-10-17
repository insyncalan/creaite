# Alan's list for v2.2.0 and v2.3.0

Prepared by Jarvis, Saturday 17-10-2026. Write your answer on the **Answer:** line under each item (yes / no / a word is enough). When you have finished, say "answered" and I will act on every line and record it. Parked items and Intake are left out on purpose.

Legend: **[2.2]** blocks the v2.2.0 candidate; **[2.2 later]** needed at the hand checks or the cut; **[2.3]** can wait.

---

## A. Decisions

### A1. [2.2] #197 run usage monitor: seven yes/no answers
Team Cap reviews the guarded proposal first (`run-usage-guarded-proposal-r2` e68471ae); the plain-English list is `dev/proposals/run-usage/README-plain.md` on that branch. Say now whether the direction stands:
1. Run engine hook (records finished, failed and stopped runs): **Answer:**
2. Widened hook (looks at every assistant event for skill names, never arguments): **Answer:**
3. VIP-call hook: **Answer:**
4. The one-line `reach.py` change (outside your brief; without it `test_record_commands` fails): **Answer:**
5. Rules file: folder-map rows and a Retention line: **Answer:**
6. `backup.py`: no change: **Answer:**
7. Tests: **Answer:**

### A2. [2.2] #186 Draft email AI bar on client facts and client checks
You said "keep 186 in". I read that as v2.2.0 (it was v2.3.0). It is a guarded-adjacent proposal first (`edit_ai.py`). 
- Release v2.2.0 (risk: it can hold the release up) or v2.3.0? **Answer:**
- Go for the proposal now? **Answer:**

### A3. [2.2] #200 the morning sweep never runs when nobody opens a terminal (defect, High)
Everything else daily runs from the server; the 07:00 sweep catch-up does not. Two fixes: (1) a sweep timer in `live_server.py` behind a setting such as `sweep.auto_when_due` (guarded, opus proposal for you first); (2) a "Sweep due since 07:00" banner with a Run sweep button on Today (not guarded, a visible change).
- Go on (1)? **Answer:**
- Go on (2)? **Answer:**
- Release: v2.2.0 or v2.3.0? **Answer:**

### A4. [2.2] #203 health sparkle: my assumptions
I took the Product Manager's lean for the two open questions: the sparkle suggests the health AND its reason (and flags when the facts differ); the project page first, the weekly report's health row after. Correct? **Answer:**

### A5. [2.2] #134 editors: the leftover branches
The rest of #134 (`bundle-134` 70a93ed9, `editor-134-chrome` d454b2d2) is built but needs a hand-merge that has not started. Your rule (items not yet started move to v2.3.0) applies, so I split the leftovers into a new v2.3.0 item and left #134 in v2.2.0 for what is already in the gate. Change that? **Answer:**

### A6. [2.2] #176 Help trim (a haiku draft, unreviewed)
Read `system/templates/help.md` on `help-trim-176` (8e14b5c6): OK to ship, or changes? **Answer:**

### A7. [2.2] #201 plain release notes (21 past releases)
Read `system/templates/help/whats-new.md` on `pm-intake-briefs`: OK as written (no dates)? Want dates? **Answer:**

### A8. [2.2] #158 Help Phase B
Built, in review. One open question: when do the old long guides go (the first-day and how-to cards are replaced in place)? **Answer:**

### A9. [2.2 later] The release itself
For v2.1.0 you let the release publish overnight once the automated gates were green and did your hand checks afterwards. For v2.2.0: publish after the gates are green (hand checks afterwards, a failed check ships as v2.2.1), or wait for your hand checks first? **Answer:**

### A10. [2.3] #193 design-system tidy-up: nine visible changes, yes or no each
Screenshots: `/private/tmp/claude-501/-Users-alanmahon-dev-env-creaite/d52ffadd-5b1b-4b44-93ee-b6ed15b8a6b9/scratchpad/tokens193/{before,after}/` (README.md has the numbers). Or "all nine".
1. Saved-view chip 28 px/12 px radius becomes a 26 px pill: **Answer:**
2. Project-page chips 20 px become 26 px: **Answer:**
3. Report cockpit date input 28 px becomes 32 px: **Answer:**
4. Project switcher text 14 px becomes 13 px: **Answer:**
5. New person fields: white ground, 13 px text, 10 px padding: **Answer:**
6. Due-date dialog input: white ground: **Answer:**
7. VIP choice in New person: 24 px native select becomes a 32 px field: **Answer:**
8. Filter menu button (.fsel): Team Stark found it is dead CSS, used nowhere, so this changes nothing you can see: **Answer (any):**
9. Headings: page titles 22 px, section headings 16 px, 34 px only for Today's day title and Help's hero, Help's own h2 stays 22 px: **Answer:**
(Checked: the heading weights do NOT change; the earlier worry was a misreading. Nine items stand.)

### A11. [2.3] The Friday close card (#187)
Weekend meetings on the card have no Prep button. Want prep pages there? (My default: no.) **Answer:**

### A12. [2.3] #153 chase facts
The chase email to an owner still carries the item's earlier "Latest update" lines (it goes to the owner, not a client). Leave, or strip them? **Answer:**

### A13. [2.3] v2.3.0 is too big for the people we have
About 19 items; about 10 are built and waiting for merges; the unbuilt ones lean on Team Cap (#132 L, #87, #88). Which, if any, move out of v2.3.0? **Answer:**

### A14. [2.3] #205 design system
First version is a measured snapshot; Team Stark found about 10 wrong statements and the Product Manager is correcting them. Review it once corrected, and approve it as the reference? **Answer:**

---

## B. Things only you can do

### B1. [2.2] Team Cap
You say it is running, but nothing from it has reached GitHub since its last green macOS run. Everything for the release waits on it (list: #199). Please confirm which laptop and ask it to read #199, or tell me to do the merges myself on this laptop. **Answer:**

### B2. [2.2] IT: the proxy question
IT approved the OpenAI egress. Does IT require a proxy? (The model-list call ignores proxy settings.) **Answer:**

### B3. [2.2 later] Hand checks
Hand checks for the v2.2.0 candidate (walk-through issue #135). How much time can you give, and when? **Answer:**

### B4. [2.2 later] The board's Release field
Not needed now (Help is in v2.2.0). Skip unless you want a v2.2.1 option anyway. **Answer:**

### B5. [2.3] The docs branch
`pm-intake-briefs` (mockups, briefs, 21 plain release notes, the design system): merge to `main` by pull request, as for `pm-mockups-111`? **Answer:**


---

## Alan's answers (17-10-2026, recorded by Jarvis)

A1 #197: all yes. A2 #186: move to v2.3.0. A3 #200: go with option 2 (the banner), release v2.3.0; the sweep timer is not approved. A4 #203: correct assumption. A5 #134: keep in v2.2.0. A6, A7, A8: yes, release v2.2.0. A9: go tonight. A10: yes to all. A11: no. A12: strip it. A13: keep as is for now, review later. A14: Alan reviews and approves once done. B1: Alan will check in with Team Cap. B2: no proxy. B3: do issue 135 now. B4: skip. B5: yes (merged, PR #2).
