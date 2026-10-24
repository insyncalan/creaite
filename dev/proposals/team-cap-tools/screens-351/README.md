# Today page at 1400 px, before and after (issue #351)

Captured 24-10-2026, 12:35 to 12:45 (the page's own clock: "today" is Saturday 24-10-2026). Desktop only: viewport 1400 x 1000, light theme,
headless Chrome driven over CDP, scratch vault per release (built from the published release zip, fictional demo data), live server on 127.0.0.1
with a spare port, stopped afterwards. Nothing real: the people (Riley Stone, Morgan Lee, Jordan Park, Casey Quinn, Avery Shaw, the user "Sam Reid"),
the meetings and the projects are invented. `shoot.py <zip> <label> <out dir> <work dir>` repeats a capture (needs Chrome, python3 -I).

Same data in every run: ten meetings on Friday 23-10 and ten on Saturday 24-10 (Teams and in person; transcript ready, none, not transcribed,
not checked yet, one with minutes made), a few on 19 to 22 and on 26 and 27 October; the calendar read to 27-10 (so 28 to 30 October are unread).

| File | What it shows |
|---|---|
| `today-vX-past-friday-23.png` | Friday 23rd October picked in the day line: follow-up chips under each meeting (No transcript, Transcript ready + Process, Not checked yet + Check, Minutes made) |
| `today-vX-today.png` | Saturday 24th October, today: no chips; titles carry the dotted "peek" underline; a NOW marker on the current meeting |
| `today-vX-hover.png` | The mouse over today's meeting title "Project kickoff": the Prep peek opens (aim, in play, since last time, Open the prep page) |
| `today-vX-past-hover.png` | The mouse over a meeting title on Friday 23rd: nothing opens (the title is plain text) |
| `dom-vX.json` | The page text read from the DOM: day line, headline, each meeting's chips, whether the title is hoverable, popup text, the unread day (Wed 28) and a later day (Mon 26) |

Releases (published zips from github.com/insyncalan/creaite): v2.6.1 and v2.6.3 are the two asked for. v2.6.1 already contains #318, so it is
not a "before #318" release; v2.6.0 is (dom-v2.6.0.json only; its pictures are the same as v2.6.3 except the unread day). v2.2.0 and v2.1.0
are included as earlier references (v2.1.0 shows "Prep" and "Note" buttons where v2.2.0 and later have the peek).

Result in short: for read days, v2.6.1 and v2.6.3 draw the same day line, headline, chips and title hover as v2.2.0 to v2.6.0. The past-day shots
of v2.6.1 and v2.6.3 are byte-identical. The one visible change from #318 (v2.6.1) is an unread day: "Wednesday has not been read yet" with
"Not read yet" and Refresh calendar, where v2.6.0 said "No meetings on Wednesday. The day is yours."
