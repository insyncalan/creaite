# 2.6.10 release-note draft: fetch transcripts as they appear (#250)

Draft paragraph for the release notes (Romanoff writes the final note).

**Fetch transcripts as they appear.** A new setting, **Fetch transcripts as they appear** (Settings › Mail, Teams and Intake › Checking mail and Teams), is off by default. When you switch it on, each mail and Teams check you run from the dashboard also fetches the transcript of every Teams meeting that has ended and puts it in Intake, so it is ready when you open the page. It only reads. No AI runs, nothing is added to your project records, and you still press **Process** to make minutes. Confidential meetings are never fetched. When the check ends, creaite says how many were fetched, how many it held back and how many are left for you to load with **Process**.

**Limits to know about.**
- A confidential meeting that was dropped from your calendar, while a normal meeting with the same title sits at the same times, can hold the normal one back. It is loaded when you press **Process**.
- A private all-day entry holds nothing back.
- When the clocks go back, a meeting in the repeated hour is held back rather than risk fetching a confidential one. Press **Process**.
- The fetch is off until you switch it on.
- The form of the transcript links from live Microsoft 365 is still to be checked on a real account; until then, a link creaite does not recognise is left for **Process**.

**Held more than before (fail closed).** When creaite cannot be sure a transcript is safe to fetch, it holds the transcript and leaves it for **Process**. Five cases:
- A transcript created more than 15 minutes before the meeting's start, or after its end, is held and goes to **Process**.
- A meeting booked at the same time as a confidential one is held, even if its own transcript is genuine.
- A confidential all-day entry holds every transcript on that day.
- Saved calendar entries written before 20-10 with no sensitivity stamp are held as unknown.
- A transcript with no created time is held.

One gap remains. A confidential meeting that was dropped from the saved calendar, whose transcript is created inside an identical time slot of a normal meeting, is not detected until the sweep stub is built.
