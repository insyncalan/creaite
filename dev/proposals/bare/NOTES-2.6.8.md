# Notes for 2.6.8: passwords and PINs in meeting invites

**Fixed.** A meeting title, place, organiser or invite text that says "Password", "PIN" or "code" followed by a plain word (for example "Password swordfish") now has that word treated as the secret. The whole title, place or organiser is dropped (a title becomes "Meeting"), or the line is dropped from the invite text. Calendars saved by earlier versions are cleaned again when a session starts (and, with the live-server change, when the server starts and on its daily pass).

**You may notice.** To be safe, any word after those labels counts as a secret unless it is a common phrase. A title such as "Pin the roadmap on the wall" or "Password for all staff" now shows as "Meeting". Phrases that stay: Password reset, policy, manager, management, expiry, rotation, audit, change; PIN entry, PIN pad; Code review, reviews, of conduct, base, freeze, quality, repository, handover, walkthrough, standards.

**Not covered (so far):**
- a secret written before its label ("swordfish password");
- a secret after one of the phrases above ("Password reset hunterxyz");
- token, key, secret and access labels followed by a plain word;
- a label with its letters spaced out ("P I N");
- a secret on the line after its label, apart from a label alone on a line;
- labels in other alphabets beyond those already listed;
- HTML in a title or place (only the invite text is read as HTML);
- secrets that contain digits are handled by the older rules only.
