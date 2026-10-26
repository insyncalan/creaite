# #371 front end: final strings

Wording approved by Jarvis on 26-10-2026 (Alan can change it). The only button is Process, so every line says Process.

Server (`Job.no_event`):
- No Microsoft 365 call: "Claude Code did not reach Microsoft 365, so it never looked for the meeting's calendar event and nothing was loaded. Press Process to try again." (the page's cue to look again once; `irNoReach` in `actions.js` matches "did not reach Microsoft 365")
- Search only: "Claude Code searched Microsoft 365 but never opened the meeting's calendar event, so nothing was loaded. Press Process to try again."
- Event unreadable: "The meeting's calendar event was found but could not be read, so nothing was loaded. Press Process to try again."

Page:
- Retry starts: "Claude Code did not reach Microsoft 365. Looking again, once."
- Second try fails: "Looked again, and Microsoft 365 still could not be reached. Nothing was loaded. Press Process to try again."
- Retry works: "Found it on the second look."

Only the no-call failure is retried, once; a stopped run or any other failure is not.
