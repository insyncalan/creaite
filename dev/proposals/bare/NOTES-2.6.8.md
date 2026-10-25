# Notes for 2.6.8: passwords and PINs in meeting invites

**Fixed.** A meeting title, place, organiser or invite text that says "Password", "PIN", "code", "token", "secret", "OTP", "API key", "Pw" or "Pswd" (also "P I N", "P.I.N.") followed by a plain word, for example "Password swordfish", now has that word treated as the secret. The whole title, place or organiser is dropped (a title becomes "Meeting"), or the line is dropped from the invite text. A calendar saved by an earlier version is cleaned again whenever it is read, and rewritten clean when a session starts.

**You may notice (on purpose).** To be safe, any word after those labels counts as a secret unless the pair is a common phrase. A title such as "Pin the roadmap on the wall" or "Password for all staff" now shows as "Meeting". These phrases stay: Password reset, policy, manager, management, expiry, rotation, audit, change; PIN entry, PIN pad; Code review, reviews, of conduct, base, freeze, quality, repository, handover, walkthrough, standards; Token refresh, expiry, rotation, economy; Secret santa, management, manager, rotation; OTP setup, rollout, enrolment; API key rotation, management, review. Such a phrase is only kept when it ends there, or goes on with an ordinary word such as "for", "and", "plan" or "workshop". "Password reset: hunter" or "PIN entry swordfish" is removed.

**Not covered (so far):**
- a secret written before its label ("swordfish is the password");
- a secret after a phrase and an ordinary word ("Password reset for hunter");
- the labels Key, Access, Login, Credentials, Pass, Guest wifi key and Dial-in followed by a plain word (too many ordinary titles, such as "Key milestones" or "Access review");
- Codice, Codigo, Sifre and Parola followed by a plain word;
- a label spelled letter by letter other than PIN ("P a s s");
- a secret on the line after its label, apart from a label alone on a line;
- labels in other alphabets beyond those already listed;
- HTML in a title or place (only the invite text is read as HTML);
- a secret that contains digits is handled by the older rules only.
