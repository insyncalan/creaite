# #97 Halve the alert check's cost (Alan, 20-10-2026)

Alan: the alert check (the check for messages from the people you follow; BL-342) costs about $4.80 a day (about 1% of laptop 2's daily spend, from Jarvis's probe runs, not yet measured in production). **He wants it halved.** Decisions: **quiet hours overnight and at weekends, as a setting: yes. Wait for the Usage tab's real data before any guarded change: yes.** Mockup: the Essentials tab of `dev/mockups/settings-v2-mockup.html` (card People I follow).

## Step 1: quiet hours (a setting; no guarded change)
- Settings › Essentials › **People I follow**, two new rows (wording avoids the word VIP, BL-288):
  - **Pause alert checks overnight** (switch, **on by default**) from **19:00** to **07:00** (editable). Help: "No checks between these times. The first check after them looks back to the last one, so nothing is missed: it is just noticed later."
  - **Pause alert checks on weekend days** (switch, **on by default**). Help: "Uses the weekend days set in Essentials › You."
- Keys: `vip.quiet_overnight`, `vip.quiet_from`, `vip.quiet_to`, `vip.quiet_weekend`. The live server's check timer skips a tick inside quiet time; the first tick after it runs the usual look-back from the last check, so no message is missed.
- **Expected saving.** At the current 30 minutes, always on: 48 checks a day, 336 a week. With overnight and weekends paused: 24 a day on five days, 120 a week: **about 64% fewer checks**, so roughly $1.70 a day on the probe figure. That is more than half, if creaite is open round the clock; if it is open only in working hours the saving is smaller and the interval should rise as well (`vip.check_minutes`, 10 to 240; 45 or 60 minutes).
- Tests: no check inside quiet time (overnight, weekend, the boundaries); the first check after it looks back to the last check; the setting off restores today's behaviour; nothing in the page or the log says VIP.

## Step 2: only if step 1 and the real data say it is still above half
Read the real cost from the Usage tab ("Alert check" kind, 2.5.2) over several days. If it is still above half, load less context per call: start the alert check with the same no-context flags the tool-less runs use (#126), after a probe proving the Microsoft 365 reading tools still load. That is a guarded change in `live_server.py` and needs an Opus review and Alan's approval of the exact diff. It overlaps #87 (half the model cost), which would trim the always-loaded rules for every run. Not scheduled.

## Not doing
Haiku for Teams chats only (small saving, more moving parts), and the two-stage split (the first stage alone cost $0.30 to $0.35).

## Done when
Quiet hours work and are on by default; the check count over a weekday and a weekend matches the table above on a pinned clock; no message is missed across a quiet period; the Usage tab shows the new daily cost; Alan sees it halved (or step 2 is scheduled).
