# Scheduled tasks (optional)

creaite does **not** depend on these. The session-start rule in `CLAUDE.md` runs the daily sweep whenever it's due. A scheduled task only helps if the laptop happens to be awake earlier.

The app stores schedules on the machine, not in this folder. cx-setup offers to create them ("setup"), or you can create them by hand in the Claude desktop app.

Tasks run only while the app is open and the laptop is awake. cx-minutes, cx-weekly-report and cx-client-report are never scheduled; the session-start rule reminds Alan when they're due.

## morning-sweep (optional)

- **When:** weekdays at 07:00 local time
- **Prompt:** Run cx-sweep for creaite. Proposals only; never run apply. Finish with one line in `system/staging/run-log.txt`.
