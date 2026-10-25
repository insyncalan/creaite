# Notes for 2.6.8: passwords and PINs in meeting invites

**Fixed in 2.6.8 (a client leak that is also in 2.6.7).** A meeting ID or passcode written between underscores (`__Passcode:__ 4417`, `_Passcode_: 4417`, `Meeting_ID: 987 654 321`, `Passcode_4417`) was kept in a saved calendar title, place or invite text, and from there reached the Prep research request, the agenda and follow-up drafts and the minutes of that meeting. The same held for several other forms: more than two blank lines after the label, a label followed by a dash or an arrow instead of a colon, several labels on one line, "Zoom ID 4417", "Room ID - 4417", "Meeting: 987 654 321", "ID is 4417", "Pass-code: 4417" and "Token! 4417". All are now removed. Old saved entries are cleaned again when a session starts and before every reader (Today, Prep, drafts, Close the day, transcripts) uses them.

**Fixed.** A meeting title, place, organiser or invite text that says "Password", "PIN", "code", "token", "secret", "OTP", "API key", "Pw" or "Pswd" (also "P I N", "P.I.N.") followed by a plain word, for example "Password swordfish", now has that word treated as the secret. The whole title, place or organiser is dropped (a title becomes "Meeting"), or the line is dropped from the invite text. A calendar saved by an earlier version is cleaned again whenever it is read, and rewritten clean when a session starts.

**You may notice (on purpose).** To be safe, after one of those labels every word up to the end must belong to a short list of ordinary phrases, otherwise the first other word counts as the secret. These titles now show as "Meeting": Pin the roadmap, Password for all staff, Code sprint, Code clinic, Code Red, Pin board, Secret Santa party, Secret sauce, Token of appreciation, Secret project Falcon, Password reset for new hires. These phrases stay (alone, or followed only by words such as for, and, the, request, plan, workshop, session, review, sync): Password reset, policy, manager, management, expiry, rotation, audit, change; PIN entry, PIN pad; Code review, reviews, of conduct, base, freeze, quality, repository, handover, walkthrough, standards; Token refresh, expiry, rotation, economy, economics, Ring; Secret santa, management, manager, rotation; OTP setup, rollout, enrolment; API key rotation, management, review. A colon, equals sign, dash or bracket after the label or after one of those words always means a secret: "Password reset: hunter", "PIN entry swordfish" and "Password reset for hunter" are removed.

**The lines after a label.** What happens depends on how the label line ends.
- A label alone on a line, or ending on a separator or a function word ("Passcode:", "Password reset for", "Password reset -"): the next lines are its value. The next three lines with text go, whatever they say (blank lines do not count), and the label line goes with them. A label list ("Meeting ID:", "Passcode:") removes one value line for each label.
- A finished phrase that leads its line ("Password reset", "Code review", "Dress code", "Secret Santa"): only the lines among the next three that LOOK LIKE A VALUE go: a line of one or two words, a line with four or more digits, a word that mixes letters and digits, or a long hex-like string. A line that starts with a list marker (1., -, •, a)), a line of three or more plain words and a sentence ending in a full stop, ! or ? always stay. The heading goes only if one of those three lines was removed. So "Code review" followed by "1. Training dates / 2. Sign-off / 3. Reporting line / 4. AOB" loses nothing, and "Password reset" followed by "hunter" loses both. "IT update: password reset" opens nothing.
- "Meeting ID." (a stop mark) takes the next line with a number; a removed line (a link, a passcode line) in between does not use it up.

**What it still over-removes, and what it now leaks (the lines rule).**
- Over-removes: a heading that leads a line with a label phrase ("Password reset") together with up to three one- or two-word lines after it that have no list marker ("Budget review", "Hiring", "Vendors"). A label word followed by an ordinary word that is not on the lists ("Dress code for visitors", "Cost code changes", "Pin board", "Token budget") loses its own line.
- Leaks (known limits, pinned by tests): a value written as a bullet after a heading ("- hunter"); a value of three plain words on a line of its own ("correct horse battery"); a value more than three lines below the heading; a word-only value after "Meeting ID" with no separator.

**Labels in a row.** When several labels stand alone one after another ("Meeting ID:", "Passcode:", "PIN:"), the next lines with text are removed one for each label, so a label list followed by its values loses exactly the values; if a label has no value of its own, one ordinary line after the list is lost with them. A / or | straight after a label ("API key / ...") now counts as a separator like a dash.

**Separators.** After a label, any punctuation or symbol (not just a colon) means a secret follows: "Passcode –", "Passcode →", "Passcode is", "Passcode (", also "Key:" on its own line. The line after goes with it. This also removes titles such as "Access & Security review" or "Key (draft): plan" that have a label word followed by a symbol; a sentence end (full stop, comma, semicolon, ! or ?) does not count. "Key milestones" and "Key dates" are unaffected.

**Sentence ends (a deliberate trade-off).** A separator with full stops, commas, question or exclamation marks round it ("Password.: hunter", "Passcode:!", "PIN?:") and an ellipsis ("Passcode...", "Passcode…") count as a separator. Two or more sentence-end marks in a row count as an ellipsis. A label followed only by ONE sentence end and then a plain word is kept on purpose, because in ordinary prose a sentence ends there and a new one starts: "Password! hunter" on one line, and a line "Passcode." followed by a line "hunter" (the label line goes, the next stays). A label followed by a sentence end and then a number ("Meeting ID. 123 456", "Meeting ID, 123", "Access code. 4417") is removed.

**Underscores and markdown.** Underscores, asterisks, tildes and backticks round a label are read as spaces, so `snake_case` words are read as words: "pass_code", "meeting_id 4417" and "api_key abc" are removed, "code_review" and "my_password_manager plan" stay. A label line followed by a removed line (a link, a line with its own value) loses the next ordinary line as well, because the removed line is not taken for the value.

**Accents.** An accent or other combining mark on a label letter no longer hides the label ("Pásscode: 1234", "Piń: 1234", "Passwörd hunter", "Sécret"). Words that differ from a label only by accents are read as the label, so "Códe sprint", "Piñ board" and "Tokén of appreciation" lose their text to "Meeting" like their plain forms; "Códe review" and "Piñ pad" stay, and "Passwörter" is a different word and stays. The text that is kept keeps its accents. A markdown link whose text is a label ("[Passcode](http://...)") is read as that label.

**Odd characters.** A character that would turn into more than four characters when normalised (a ligature such as U+FDFA, which stands for eighteen letters, or a unit sign) is read as a space before it is expanded, so a hostile invite cannot make reading slow. No label letter expands that far.

**Saved calendars.** A saved meeting keeps only the fields the sweep writes (title, place, times, organiser, invite text, attendees, attachment names and a few flags); anything else in an old or foreign file (a description, a join link, a note at the top, a row that is not a meeting) is dropped when the file is cleaned and when it is read. The clean-up and a sweep's save take the same lock, so neither loses the other's write. A cleaned calendar is kept in memory while the file is unchanged, so repeated reads are fast.

**Details for the release note (Romanoff).** The saved-calendar clean-up always runs: if the calendar lock cannot be had within a few seconds (another process holds it, the lock file cannot be written, or the system has no file locking) it cleans without the lock and writes only if the file has not changed since it was read, and says so in the debug log. The read-side cache is keyed on modified time, size and inode; a rewrite that restores all three would be served the earlier CLEANED content, which is stale but never a leak. Day keys that are not YYYY-MM-DD dates and extra fields on attendees are dropped by design. The daily backup zips and their OneDrive copies keep an earlier raw `calendar.json` for their retention period.

**Idempotent cleaning.** Cleaning a saved text twice gives the same text as cleaning it once (a 40,000-body seeded test and Team Cap's 35-test property file). A kept label line whose window removed a line goes with it, so a later pass cannot open it again, and the window counts every line, so removals do not shift later lines into it. Two of Team Cap's tests ask that the one- and two-word lines after a leading heading survive; they are marked as accepted limits in `test_calendar_clean_idempotence.py` because such a line looks exactly like a value ("hunter").

**Status of the shapes Team Cap found (#369)** — shape | status | row names (in `test_invite_clean_bare.py` unless stated)

| Shape | Status | Rows |
|---|---|---|
| underscores and markdown wrappers around a label | closed | `u-*`, `m-underscore-*`, `test_invite_clean_sweep` decoration sweep |
| several labels on a line, a used-up value, unknown ID labels, sentence end then digits, Pass-code | closed | `m-*`, `id-*`, `se-*`, `split-pass-code` |
| a line cut at 2,000 characters through a label | closed | `c-cut-*` |
| a spacing mark (Mc) or an invisible filler inside a label | closed | `c-mc-*`, `c-hangul-filler`, `c-braille-blank` |
| markdown reference, titled, angle and double-bracket links; a footnote mark | closed | `c-md-*`, `c-footnote` |
| plurals, hyphen-joined labels, other dashes | closed | `c-plural-*`, `c-hyphen-*`, `c-nb-hyphen-*`, `c-en-dash-id` |
| Conf, Meet, Video, GoTo ID; Webinar, Conference, Event, Session #; Zoom ID number; bare ID with three digits | closed | `c-conf-id` ... `c-bare-id*` |
| a bare label in a header row; a separator or table rule on its own line; escaped HTML; tags inside a label | closed | `c-header-row`, `c-colon-own-line`, `c-table`, `c-escaped-html`, `c-wbr`, `c-comment`, `c-o-p`, `c-code-tag` |
| camelCase keys in a link (meetingPassword, confPin, userPin, sessionPwd, mpwd) | closed | `c-url-*` |
| a dash glued to a label and its value ("Passcode-4417", "PIN–4417", any dash character) | closed (compound words "Password-based", "PIN-protected", "Code-review", "Key-account" stay) | `test_invite_clean_sweep` dash sweep, `test_compound_words_stay` |
| a provider glued to a label (Zoom, Teams, Webex, Meet, GoTo, Skype, Bluejeans with Passcode, PIN, ID, Password, Meeting ID; hyphen, glued, camelCase, snake_case) | closed, except a word value after an ID label with no separator ("Zoom ID hunter") | `test_invite_clean_sweep` provider sweep |
| "Meeting ID." with a removed line and a second label before its number; a bullet or a table row as the value | closed ("Meeting ID. / Passcode: / 4417 / 987 654 321" removes both); a bulleted or numbered digit/ID value ("- 4417", "1. 987 654 321", "<li>ZQ7742</li>") now goes too; a word-only bullet ("- hunter") stays, an accepted limit | `x-two-labels-*`, `test_a_bulleted_id_after_a_heading_goes`, `test_a_word_only_bullet_value_after_a_heading_is_the_accepted_limit` |
| a line of underscores, dashes, dots, pipes, box-drawing or bullets between a label and its value | closed (transparent, like a table rule) | `test_invite_clean_idempotence` |
| reference-style, image, autolink, bare angle and parenthesised-URL markdown forms | closed | `k-*` |
| the organiser's address | kept (like an attendee's); a passcode in the display name is dropped | `test_calendar_shapes.OrganiserAddress` |
| a value two lines below a heading | removed if it looks like a value and is within three lines; a value four lines below stays | `test_a_value_two_lines_below_goes_four_lines_below_stays` |
| the recurrence field was saved unscrubbed | closed | `test_calendar_shapes.Recurrence` |
| "ID 12" (fewer than three digits), HTML around a label in a TITLE, a secret in Greek, Hebrew, Hindi, Thai or Russian | limit, by design | `NOT_COVERED`, `test_project_id_with_a_short_number_stays` |

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
- labels in scripts without rules: Greek (Κωδικός), Hebrew (סיסמה), Hindi (पासवर्ड), Thai (รหัสผ่าน) and Russian "Контрольный код" followed by a plain word;
- "şifre hunterxyz" and "Şifre" (Turkish) with a plain word on the same or the next line;
- "Meeting ID" followed by a plain word with no digit and no separator ("Meeting ID hunterxyz").
- a character that expands to more than four characters, or a symbol, INSIDE a label word ("P㈝IN: hunter", "P#IN: hunter") breaks the label (not a regression);
- reading a saved calendar of hundreds of hostile rows with 20,000-character bodies still takes seconds (a saved body is cut to 20,000 characters before it is cleaned again; real invites are far smaller and are not affected).

## bare19: list items, numbers, glued labels, the retry (Team Cap's probe and the reviewer)

**List markers (decision).** A list marker (`1.`, `a)`, `-`, `*`, a bullet, and the `<li>` that becomes `- `) is stripped first and the rest judged as a value. A bulleted line goes after a heading or a stop-label only on a STRONG sign: a number (below), a token of five or more characters with three or more digits ("ZQ7742"), or a long hex-like string, in at most three words. A **word-only bulleted line ("- hunter", `<li>hunter</li>`) stays: an accepted limit.** It cannot be told from an agenda item ("- Budget", "1. Intro", `<li>Hiring</li>`), and removing it would delete real agenda items under every heading such as "Code review" or "Password reset". Digit and ID bullets are no longer a limit. Fixes the new non-fixed-points too ("Key.\n- 123456": pass one kept it, pass two removed it).

**What counts as a number after "Meeting ID."** The rule that takes the next line after a label ending in a stop ("Bring your staff ID.") now needs a number that can be an ID: four or more digits in a row, digits in groups (3+3, 3+3+3, spaces or dashes), or a line of nothing but four or more digits ("55 66"). Dates (25-10-2026) and times (12:30) are taken out first; "Lunch at 12:30", "Room 4", "Item 12", "Room 204", "Starts 10:00" survive (this was data loss: the lunch line vanished).

**A label glued to digits.** "PIN4417", "Passcode4417", "Password123", "Pwd4417", "MeetingID123456", "Meeting ID123456", "ID123456789" (label then three or more digits, no separator) are removed. "ID badges", "Idaho 1234", "Pinterest 2026" stay. Fail closed: a product name such as "ID300" goes too.

**Rescrub diff v4.** `live_server-rescrub-v4.diff`: v3's retry set only one retry (the timer calling the job is itself alive, so `calendar_rescrub_retry` returned); v4 also checks `timer is not threading.current_thread()`. Tested with a held lock, a 0.3 s delay and several retries, and a mutant that fails when only one retry happens. Not applied to live_server.py.

**What the label approach costs (honest figure).** The reviewer's measurement on 13 realistic agendas (58 lines): 28 lines (48%) were lost. Examples: "Code of conduct\nAnnual refresher\nAll staff\nMandatory" gives ""; "Topics\n- Code review\n- Token refresh\n- Secret santa\n- Pin the roadmap\n- Zip code lookup" gives "Topics"; "Agenda:\n1. Welcome\n2. Password reset rollout\n3. Code of conduct refresh\n..." loses lines 2 and 3. **Accepted for 2.6.8 as fail-closed** (a lost agenda line is recoverable from the sender; a leaked passcode is not). **E1 in 2.6.9 replaces the label approach.** bare19 does not change these three examples (re-run: same output); the 13-agenda set was not available here, so the 48% is the reviewer's, not re-measured.
