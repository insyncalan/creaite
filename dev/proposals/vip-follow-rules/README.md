# VIP / follow flag: proposed rules wording (for Alan's approval, not applied)

Decision (Alan, via Jarvis, 23-10-2026): only the **follow flag** is shared inside the app. The word **VIP** stays out of anything a client sees and, per BL-288, out of anything creaite writes, exports or shares.

Files here: `creaite-rules.md.diff` (checked with `git apply --check` and `-R --check` against `origin/v261-line2`, 6 lines changed in `system/creaite-rules.md`, nothing applied), `CODE-PLACES.md` (every code place, not built).

## Before and after (the one that matters, rules line 189)

Before: "VIP is private to Alan (BL-288): never call or label a person a VIP, or say who is one, in anything creaite writes or may show or share ... VIPs still work unlabelled ... The word stays only in the person's own VIP field, the register's VIP column and Settings › Essentials › People I follow."

After: "The follow flag is shown in the app; the word VIP never is (BL-288, revised; Alan, 23-10-2026): a person Alan follows carries the follow flag (one per person, in their People entry, 'Follow this person'). It is the only such mark creaite shows, and only inside the app: the 'people you follow' alerts on Today, first in Review, the Work funnel's People I follow filter and the early warning. Never use the word VIP, or any other label of importance, in anything a client can see or that creaite writes, exports or shares ... and never say in any of them who is followed. Hidden stays private to each laptop (F3), as does the list of who is followed until Alan decides otherwise. The word VIP may remain only in internal names that are never shown, exported or shared (code, `vip.*` settings keys, `vip.json`) and, until it is migrated, in the register's old `VIP` column."

The other five edits are renames of the concept in the rules, no behaviour change:
- Line 11 (backup): "never `vip.json`: VIP is private to Alan" becomes "who Alan follows stays on the laptop".
- Line 58 and 62 (session start): "VIP check" becomes "follow check"; the printed line "VIP: n new" becomes "Followed: n new"; "A VIP is never dropped" becomes "A followed person is never dropped".
- Line 82 (commands): "make Mia Hale a VIP" / "mark the VIP alerts seen" become "follow Mia Hale" / "mark the follow alerts seen".
- Line 119: "VIP check (BL-99)" becomes "Follow check (BL-99)".
Untouched: `vip.json`, `vip.enabled`, `vip.check_minutes`, `vip.notify`, `vip.quiet_*`, `sweep.py vip` appear in the rules as internal names (lines 39, 47, 62, 82, 119), still allowed by the new last sentence.

## Reasoning

- The dashboard and Help already say "people you follow" and the VIP check results are already unlabelled; the rule only has to catch up and say what "shared in the app" means.
- Keeping the word out of anything written or exported is the existing BL-288 line, made explicit for "any label of importance" so a synonym does not creep in.
- Minimal diff: internal names stay (renaming `vip.*` keys and `vip.json` is a migration, see CODE-PLACES.md).

## Reconciliation with F3 (`dev/proposals/f3/README.md` on `origin/v264-f3`)

- Hidden: private per laptop in F3 and in the proposed rule. No conflict.
- Follow (today the register's VIP value): F3 puts VIP in `system/staging/people-private.json`, "never in the shared register file, the people table, the generated Markdown", other laptops get no VIP. The decision says the follow flag is shared inside the app. The proposed text says shown in the app and keeps "who is followed" on the laptop until you decide. Two readings of "shared inside the app":
  - (a) shown to Alan wherever the app shows the person (a label in the app only). F3 as built still works; only the word changes.
  - (b) stored in the shared people table and travels to another laptop's app. F3's private file, `people_text` and the "no VIP column" test would change.

## Open questions

1. Reading (a) or (b) above? The diff is written for (a); (b) needs F3's design changed and one more sentence in the rule (remove "stays on the laptop" in line 11 and the "as does the list of who is followed" clause).
2. Internal names: is the word VIP allowed in `vip.*` settings keys, `vip.json`, function names and the `Settings` JSON, which sit in the OneDrive backup zip (a closed zip only Alan can open)? The diff says yes; the alternative is a rename with a settings migration (CODE-PLACES.md, "Rename option").
3. The register's `VIP` column: keep reading it until migrated (as proposed), or rename the column to `Follow` in one step with F3's importer?
4. The `management` / `client` kinds in the VIP column ("a VIP kind"): they are a label of importance. Drop them (follow is yes/no) or keep as an unshown internal value?
5. Sentence in settings_catalogue line 56, "Only you see who you follow": true under (a), false under (b).
6. Commands "make X a VIP" and "mark the VIP alerts seen": accept the old wording as an alias for one release?
7. The old test `test_vip_private.py` and the plain-words baseline (`dev/PLAIN-WORDS.md` has no VIP/follow entry, so no change there): confirm the guard code that matches the word VIP (`drafts.VIP_RE`, `edit_ai.VIP_LOOSE`, `live_server.ALERT_WORD`) stays as is: it enforces the proposed rule.
