// @ts-check
/* core/closeDayRows.js (#358): which of Close the day's four source rows a finished step ticks, and which row shows as now. Pure,
   no imports: dev/tests/test_mail_check.py runs it under Node. */

/** Which of SOURCES a run's step line is (its index), or -1 for any other step. #358: whole labels only, matched exactly (the server's
    describe_tool form, or, for the catch-up, a run creaite started, its plain_step words), never a search of the text, so a mail subject
    with "Teams" in it ticks nothing. The calendar has no row, and a script step ("Staging what the sweep found") ticks nothing.
    "Matching to projects" (3) is never ticked by a step. */
const CD_LABELS = [
  ["Searching mail", "Microsoft 365: outlook email search"],
  ["Searching Teams chats", "Reading Teams chats", "Microsoft 365: chat message search", "Microsoft 365: teams list chats"],
  ["Reading Teams channels", "Microsoft 365: teams list channels", "Microsoft 365: teams list channel messages"],
];
/** @param {string} label */
export function cdSourceOf(label) {
  return CD_LABELS.findIndex(l => l.includes(label));
}

/** The row shown as now: the first of the three source rows not done, and only once the run has finished a step (before that every row
    waits). Matching to projects is never shown as now. @param {{steps: number, done: number[]}} cu */
export const cdNow = cu => (cu.steps > 0 ? [0, 1, 2].find(i => !cu.done.includes(i)) ?? -1 : -1);
