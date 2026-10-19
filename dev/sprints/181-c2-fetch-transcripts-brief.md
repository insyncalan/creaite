# #181 C2: fetch transcripts as they appear (2.6, after #232 lands)

Decided by Alan, 19-10-2026: build C2 **after #232 lands, as a sweep step, in 2.6**. C3 (draft minutes by series) stays later: its daily spending cap is to be asked later, and it waits for the 13-11-2026 review, the Usage monitor (#238) and the minutes confidence label (#169). Source: `dev/sprints/intake-review-2026-10-17.md` stages C2 and C3.

## What it does
Each sweep, for meetings that have ended and whose transcript now exists, creaite fetches the transcript text into Intake (the same place "Load" puts it today), so the meeting shows **Transcript ready** when you open Intake and **Process** starts at once. It is a read: **no AI runs and nothing is written to the tracker.** Nothing is processed until you press Process (or Process all ready).

## The setting (Alan: a setting, so off by default)
- Settings › **Sweep and Intake**, a new card **Transcripts**, key `sweep.fetch_transcripts`, **off by default**.
- **Label:** Fetch transcripts as they appear.
- **Help text:** "Off: creaite fetches a transcript when you press Process. On: each sweep fetches the transcripts of meetings that have ended, so they are ready when you open Intake. It only reads: no AI runs and nothing is written to the tracker. Confidential meetings are never fetched."
- Mockup: the Sweep and Intake tab of `dev/mockups/settings-v2-mockup.html`.

## Rules
1. **Confidential meetings are never fetched** (and nothing else is skipped: Alan's answer is "confidential only"). A confidential meeting keeps only its title and times, as the calendar does today.
2. **Only meetings the user could Process:** not ones already loaded, filed, cleared (Not needed) or snoozed with Later until a transcript arrives; Later brings a meeting back when its transcript arrives, as today.
3. **Look-back:** the existing "Calendar import goes back to" setting limits how far back it fetches.
4. **Local only:** fetched text stays in the vault (as Load does today); never in a synced folder; never in the debug log (counts and IDs only).
5. **Failure is quiet and honest:** if Microsoft 365 cannot be reached, the sweep says so in its summary and tries next time; a meeting just stays "Transcript ready" to fetch on Process, as today.
6. **Guard:** it is an unattended run. Jarvis checks the guarded files and the sweep's read-only tool list before design; the fetch uses the same Microsoft 365 reading tool that Process uses; ask creaite is unchanged.

## What the user sees
Nothing new on the page: rows say "Transcript ready" earlier, and the sweep summary adds "Fetched n transcripts". The Intake row for a fetched meeting reads exactly as one that was fetched by Process.

## Done when
With the setting off, nothing is fetched until Process (as today); with it on, a sweep fetches each eligible ended meeting's transcript exactly once; a confidential meeting is never fetched; no AI call is made and nothing reaches the tracker; a failure leaves the row ready and is reported; tests cover on and off, confidential, repeat sweeps (no refetch), and the guard.

## Open for later
C3's daily spending cap (Alan: "ask later").
