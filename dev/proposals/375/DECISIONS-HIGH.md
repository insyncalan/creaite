# #375 decisions on the two HIGH findings (adversarial review 2.6.9), items 4 to 6

Branch `v269-c`, from `v269-order` (3dc0a04d). Code: `system/scripts/invite_filter.py` only (`invite_clean.py`, the 2.6.8 scrub, is untouched).
Measured with the adversarial generators (`git show v269-adv:dev/tests/test_e1_adversarial.py`, 3,000 bodies per generator, its fixed seeds) on composition D
(`scrub_raw_first`, the default), plus the 27 fixtures and the 40,000-body fuzz harness. Fictional data only.

## How the new rules are wired

* They live in `invite_filter.py` and are switched on only for composition D (`keep_indices(..., extras=True)`). The E1-minimal anchor layer
  (`keep_indices` with the default `extras=False`) stays label-free, local and idempotent, so the existing spec, props and mutation tests hold unchanged.
* D repeats the extended passes until nothing changes (at most four rounds), so removing a line that exposes a new neighbour cannot make the
  filter non-idempotent.
* Each rule has a module flag for the tests (`_USE_ORPHANS`, `_USE_SENTENCE`, `_USE_EXT_LABELS`, `_USE_SIGNATURE`, `_USE_BOUNDARIES`).

## HIGH 1: a 4-digit PIN or short password behind a label the scrub does not list

Decision: **(ii), the cheap rule, done** (two parts). It is a limit of the 2.6.8 scrub too, but the rule costs almost no ordinary text.

1. **Orphan rule.** After a block that was dropped whole because it held an anchor (a link, a dial string, a 7+ digit run), up to two following
   short value-only blocks go with it: 1 or 2 lines, at most 24 characters and 4 tokens in all, one token a 4 to 8 digit number or a short
   letter-and-digit token (a bare year needs a label line beside it). No label word is consulted, so `Clave\n8825`, `Hasło : 7679`,
   `访问代码 | 4256` all go. In D the scrub has already removed the join block, so the block is judged on the original lines and the matching
   short block is removed from the scrub's output (`_without_orphans`).
2. **Extended multilingual label pass** (`_LABELS_X`, only in D): Clave, Contraseña, Código de acceso/secreto, Lösenord, Åtkomstkod, Pinkod, Hasło,
   Kod dostępu, Şifre, Parola, Geçiş kodu, Codice (segreto, di accesso), Senha, Código, Passwort, Kennwort, Zugangscode, Mot de passe, Code d'accès,
   Code secret, Toegangscode, Wachtwoord, Pincode, 密码, 访问代码, 会议密码, 비밀번호, 암호, 패스코드, Пароль, Код доступа, Пин-код, パスコード, パスワード,
   暗証番号, plus English forms the scrub misses (pass, security/entry/door/verification/auth/join/room/meeting code, meeting number...). A table bar
   `|` counts as a separator in this pass only.

Numbers (leak bodies of 3,000, D): `localised` 315 to 51 (orphan alone 315 to 124 with the labels off, labels alone to 164); `html_split` 257 to 0.
Remaining `localised` leaks (51): a label the list does not know, a short value two blocks away from the ID block, or a value the scrub's window took
with the label (leaving two groups of an id, finding 3). Known limit: an id of fewer than 7 digits behind a label we do not know.
Data loss: ordinary agenda sets unchanged by this rule (`agenda_isolated`, `agenda_list`, `table_cells`, `innocent` identical before and after);
`localised` isolated loss 406 to 406 (before item 7). Provider invites: 0 leaks, 0 agenda lines lost.

## HIGH 2: a code in a plain sentence ("Use 6802 to join", "Pass 4417")

Decision: **a narrow cheap rule, done** (one line only, never its block). A first, wider rule (any 4 to 6 digit number in a short sentence with
join/dial/enter/use/pass/code/pin words) was **rejected on the numbers**: on a 30-line set of ordinary sentences it lost 12 lines (before: 3, all
2.6.8 behaviour), among them `Use case 4521 is approved`, `Enter room 1234 via the east door`, `Pass the PO 45012 to finance`.

The shipped rule: one of use/enter/pass/dial/type/press/quote/key in/passcode/code/pin/password/access code **directly followed** by a 4 to 6 digit
number (not a year, date or time), in a line of at most 3 words ("Pass 4417") or one that also holds a join/dial/enter/access/prompted/meeting/call/bridge/
connect/login/sign word ("Use 6802 to join"). Result: ordinary-sentence probe 3 of 30 lost before, 3 of 30 after (same lines); the 39 English
phrasings with 4, 5 and 6 digit values leak 2, 2, 2 before (`Use {v} to join`, `Pass {v}`) and 0, 0, 0 after. The adversarial `phrasing` generator
leaks 119 to 52 bodies; the rest are words and alphanumeric tokens (`Use falcon to join`, `Pass zqsm45`), a **documented limit**: no digit shape to
anchor on, and a word after "use" or "pass" is ordinary English. A bare 4-digit year used as a code (about 2 per cent of 4-digit PINs) is not caught.

## Item 4a, an id one group per line or folded over lines

Done. Consecutive digit-only lines of at most 4 digits join into one candidate and are dropped with their block: three or more lines of 6+ digits in all,
or two lines of 3 to 4 digits each (6+ in all; the scrub may already have taken the first group with its label). Output stays a subset of the lines.
`html_split` 257 to 0 leak bodies, `digit_styles` 75 to 30. Remaining `digit_styles` 30: the label line carries the first group (`PIN - 266`), the scrub
takes it, and what is left is `483` `21`, five digits in two lines. Not done: joining a 2-line, 5-digit remainder would take ordinary column numbers.

## Item 4b, address-style tokens

Done: `meet-8990@x`, `pin.1234@x`, `join449038@x`, `mailto:join449038@x` (a join/meet/pin/conf/bridge/dial/pass/code word and 4+ digits in the local part, an
anchor); a JWT shape (`eyJ...` two long dotted parts, an anchor); the unlabelled one-token lines `Summer2026!` (letters, digits, then marks),
`abc-defg-hij` (a Meet code) and `sk-live-...` style blobs (a 16+ character run with 4+ letter and digit changes). `phones` 218 to 0 leak bodies, `noise` 428 to 67.
Not done, and why: (1) a Meet code inside a sentence without a link (no shape to tell it from `one-time-use`; as a whole line it goes, and a line
that is only `one-time-use` is lost, a known false positive); (2) tokens of fewer than 16 random characters with `.` `_` `-` (`sk-live-596-x` style), too
close to ordinary file names such as `budget-review-2026-final.pdf`, which the test keeps; (3) an address local part with 4+ digits and no join/meet/pin
word (room mailboxes carry digits).

## Item 6, signature blocks

Done, conservative. A block that has a sign-off line (regards, best regards, kind regards, best, thanks, thank you, cheers, sincerely, `--`) **above** its first
anchor line loses only the anchor lines and a phone label line (`M:`, `Mobile:`, `Tel`...) just above one; name, title, company and e-mail stay. A region
(divider to divider) whose only anchors sit in such a signature does not condemn the region. A block without a sign-off line is dropped whole as before.
Collateral lines lost in `phones`: 1,885 to 575 (the rest is the contact-list and Dial-in shapes, which are not signatures); the number never survives
(`phones` leaks 0). Risk accepted: a join block that follows a sign-off line inside the same block loses only its anchor lines, not its other lines (the
label layer and the orphan rule take values it leaves). `reply_chain` collateral unchanged (1,496: quoted/forwarded blocks are not signatures).

## Item 7 (coordinator extra), HTML Meet agenda lost in D

Cause confirmed: the scrub turns HTML into text without the `<hr>`/`<p>` boundaries, so a join block and the agenda read as one block. Fix in
`invite_filter.py` (D order): each scrub line is matched back to the original (converted) line it came from, and a divider or blank placeholder is put
where the original had one between two matched lines; the anchor layer judges blocks with them, then the placeholders are removed. Agenda lines kept on
Meet, Teams, Zoom, Webex and GoToMeeting, plain and HTML, three positions (30 bodies, 170 agenda and note lines): 153 of 170 before, 170 of 170 after; provider leaks 0 before
and after. Generators: `templates` isolated loss 762 to 0, `localised` 406 to 105, `html_split` 1,094 to 69, `agenda_isolated` 5,140 to 4,660; leaks unchanged.
