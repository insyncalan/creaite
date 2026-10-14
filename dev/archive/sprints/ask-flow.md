# Sprint ask-flow: queued messages, one card that applies, the chat shown at once, more quips and coloured dots (BL-257, BL-258, BL-262, BL-259, BL-261)

Branch `sprint-ask-flow`, worktree `../creaite-ask-flow`, from `fix-search-read` (BL-252), because BL-252 also edits `ASK_PROMPT`. **For v1.7.0.** Read each item in `dev/BACKLOG.md`. Also read, in `dev/BUILD.md`, the sections on ask creaite's run engine, BL-141 (the guard and the one card), BL-199, BL-201 and BL-196 (Sprint chat-text), and BL-195 (the quips).

## Order: one commit per item, each in a marked block (`===== BL-2xx (sprint-ask-flow) =====`)

1. **BL-262: reopening ask creaite shows the chat at once, never redrawn.**
   - **Test first:** write the test that reproduces the redraw.
   - **The fix:**
     - never clear and redraw `#chLog`;
     - `/api/ask/attach` takes a sequence number and sends only newer events;
     - the history is drawn in one step;
     - the greeting is no longer typed out character by character on reopen.
2. **BL-257: messages sent during a run are queued and run in order when it finishes.** The queue is kept with the chat, so it survives a reload, and shown in the panel.
   - Stop clears the queue, and says so.
   - A queued message can be removed before it runs.
3. **BL-258: one card with the exact before and after.**
   - **Approve** stages and applies through `tracker.py apply` at once. **Reject** discards.
   - The card is built from `propose.py preview` output, never from the model's own description.
   - **Approval before writes holds:** it applies only on Alan's explicit Approve on that card, and the bulk rule still holds (minutes, health, new decisions and new risks are never bundled into an approve-all).
   - **BL-141's card for file changes is separate and unchanged.** Nothing here can approve a file change.
4. **BL-259 and BL-261: about 150 office quips and coloured working dots.**
   - **Quips:** each is shown for a random 5 to 10 s, with no repeats until the deck is used up.
   - **Dots:** ask creaite's three working dots get a colour each, from new theme tokens, meeting 3:1 in every theme, light and dark. The animation is unchanged.
5. **Docs:** Help, the spec, a BUILD "Sprint ask-flow" section with the FR text, lines in `dev/release-notes/1.7.0.md`, and hand checks.

## Rules
- **Guard tests:** the refusal tests in `test_reach`, `test_permissions`, `test_admin_card`, `test_ask_shell_shapes` and `test_ask_tiers` pass **unchanged**.
- **`python3 dev/tools/check.py`:** must pass strictly. Never use `--allow-worse`.
- **Tests:**
  - run your own tests plus every chat and ask file (`grep -l -i "chLog\|ask/attach\|ASK_PROMPT\|mdots\|working(" dev/tests/*.py`);
  - use at most `-j 2`, because the runner's Chrome cap is shared machine-wide;
  - never run the full suite.
- **Look at it:** in the real browser (`dev/tools/cdp.py`), at 1400px, in light and dark, in three themes. Keep the screenshots in the scratchpad.
- **Never push or merge.** No Actions runs unless told.
- **Processes:** stop only your own processes, by PID. Never `pkill`.
- **The usual edit rule:** don't edit `dev/BACKLOG.md`, `dev/BRD.md` or `dev/archive/sprints/STATUS.md`. No schema change.
