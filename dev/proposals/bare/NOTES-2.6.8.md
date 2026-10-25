# Notes for 2.6.8: passwords and PINs in meeting invites

**Fixed.** A meeting title, place, organiser or invite text that says "Password", "PIN", "code", "token", "secret", "OTP", "API key", "Pw" or "Pswd" (also "P I N", "P.I.N.") followed by a plain word, for example "Password swordfish", now has that word treated as the secret. The whole title, place or organiser is dropped (a title becomes "Meeting"), or the line is dropped from the invite text. A calendar saved by an earlier version is cleaned again whenever it is read, and rewritten clean when a session starts.

**You may notice (on purpose).** To be safe, after one of those labels every word up to the end must belong to a short list of ordinary phrases, otherwise the first other word counts as the secret. These titles now show as "Meeting": Pin the roadmap, Password for all staff, Code sprint, Code clinic, Code Red, Pin board, Secret Santa party, Secret sauce, Token of appreciation, Secret project Falcon, Password reset for new hires. These phrases stay (alone, or followed only by words such as for, and, the, request, plan, workshop, session, review, sync): Password reset, policy, manager, management, expiry, rotation, audit, change; PIN entry, PIN pad; Code review, reviews, of conduct, base, freeze, quality, repository, handover, walkthrough, standards; Token refresh, expiry, rotation, economy, economics, Ring; Secret santa, management, manager, rotation; OTP setup, rollout, enrolment; API key rotation, management, review. A colon, equals sign, dash or bracket after the label or after one of those words always means a secret: "Password reset: hunter", "PIN entry swordfish" and "Password reset for hunter" are removed.

**The lines after a label.** In an invite's text, a line that ends on one of those labels or phrases ("Password reset", "Password reset for", "Password reset –", or a label alone) makes the next three lines with text go too, whatever they say; blank lines in between do not count. So "Password reset" followed by "Team standup at 10", "Agenda: budget", "Review and update" or a short list loses its next three lines; the fourth stays. A removed label line does the same, and a label line inside those three starts the count again. Table cells and list items without a surrounding table or page are read as lines in the same way.

**Plainly, what the lines rule costs.** If an invite has the line "Password reset" (or "Code review", "PIN entry" and so on) followed by "Team standup at 10" and the lines after it, those three lines are lost; the fourth line stays, by design. A label on a line of its own ("Passcode:") removes the next line with text however many blank lines come between. Older label gaps that the cleaning never handled stay as they were.

**Labels in a row.** When several labels stand alone one after another ("Meeting ID:", "Passcode:", "PIN:"), the next lines with text are removed one for each label, so a label list followed by its values loses exactly the values; if a label has no value of its own, one ordinary line after the list is lost with them. A / or | straight after a label ("API key / ...") now counts as a separator like a dash.

**Separators.** After a label, any punctuation or symbol (not just a colon) means a secret follows: "Passcode –", "Passcode →", "Passcode is", "Passcode (", also "Key:" on its own line. The line after goes with it. This also removes titles such as "Access & Security review" or "Key (draft): plan" that have a label word followed by a symbol; a sentence end (full stop, comma, semicolon, ! or ?) does not count. "Key milestones" and "Key dates" are unaffected.

**Sentence ends (a deliberate trade-off).** A separator with full stops, commas, question or exclamation marks round it ("Password.: hunter", "Passcode:!", "PIN?:") and an ellipsis ("Passcode...", "Passcode…") count as a separator. Two or more sentence-end marks in a row count as an ellipsis. A label followed only by ONE sentence end and then a plain word is kept on purpose, because in ordinary prose a sentence ends there and a new one starts: "Password! hunter" on one line, and a line "Passcode." followed by a line "hunter" (the label line goes, the next stays). A label followed by a sentence end and then a number ("Meeting ID. 123 456", "Meeting ID, 123", "Access code. 4417") is removed.

**Not covered (so far):**
- a secret written before its label ("swordfish is the password");
- the labels Key, Access, Login, Credentials, Pass, Guest wifi key and Dial-in followed by a plain word (too many ordinary titles, such as "Key milestones" or "Access review");
- Codice, Codigo, Sifre and Parola followed by a plain word;
- a label spelled letter by letter other than PIN ("P a s s");
- a secret on the line after its label, apart from a label alone on a line;
- labels in other alphabets beyond those already listed;
- HTML in a title or place (only the invite text is read as HTML);
- a secret that contains digits is handled by the older rules only.
- runs of punctuation between a label and its secret beyond the simple cases, and an escaped "&amp; swordfish" written after a phrase;
- Key, Access, Login, Credentials, Pass, Codice, Codigo, Sifre and Parola followed by a plain word (listed above) are known limits, as is a secret written before its label.
