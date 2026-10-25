# #328 plain-words line for the 2.6.7 notes

(dev/release-notes/2.6.7-plain.md does not exist on this branch, so the line is here.)

- **Process all ready now waits for a project.** It processes only the meetings whose project is Matched or one you chose before. A meeting whose project is only Likely or Not sure is skipped and listed by title ("Skipped 2 meetings until you pick a project: ..."), so you pick the project first. Pressing Process on a meeting itself still works whatever its state. A confidential meeting is still left out and counted, never named.

Decisions recorded (Jarvis, 26-10-2026): no organiser addresses saved; no live_server.py diff for the Shared learn (nothing of the kind is on this branch).
