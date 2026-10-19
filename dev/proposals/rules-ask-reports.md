# creaite-rules.md: ask creaite does not write reports (guarded: Jarvis applies)

Alan, 19-10-2026; `reach.py` refuses it (v251-askreports 6249e5a4). Suggested edits:

1. Skills table, rows "weekly report" and "client report ABC": append "Alan's own Claude Code session only: ask creaite never drafts, stages or writes a report (reports are made and edited in the Reporting hub)".
2. "What ask creaite may touch" (the guard hook bullet): add "a direct Edit or Write of a weekly or client report file or draft, a `report.py weekly-stage` or `client-stage` run, and a Bash call that names a report file are refused (`reach.is_report_file`, `report_command_refusal`); reading reports stays open."
3. Project documents, "What creaite may do with project files": "Reports are the user's own: ask creaite reads them, never changes them."
