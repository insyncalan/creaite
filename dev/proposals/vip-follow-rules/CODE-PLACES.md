# Code places the VIP / follow rule would change (not built)

Counts are case-insensitive "vip" matches in `origin/v261-line2` (a2288848). Guarded: creaite-rules.md, schema.sql, tracker.py, propose.py, review.py, build_dashboard.py, paths.py (F3's list, #317); I also treat live_server.py, reach.py, permissions.py, backup.py and the skills as guarded-by-process (assumption: no single guard list found in the tree). Size: S under 10 lines, M 10 to 50, L over 50. Most hits are internal identifiers and comments that the proposed rule allows (last sentence of the rule), so "change" below means a user-visible string, a written output or the register data. Option: rename everything internal as well (see the end).

## A. People register: column, parse, editor

| File:line | Today | Would change | Guarded | Size |
|---|---|---|---|---|
| system/scripts/propose.py:829-847 (`person_vip`, `vip_people`) | reads the register's extra column `VIP` (blank / management / client / yes) | read `Follow` (and still `VIP` until migrated); return yes/no, drop the kind; name `person_follow` | yes | S |
| system/templates/people-register-template.md:7, 16 | header column `VIP`; note "Anything a VIP sends ..." | column `Follow`, wording "people you follow" | no | S |
| system/templates/dashboard/src/stores/peopleRegister.js:12, 37, 180-185 | reads and writes `r.extra.VIP`; keeps value "management"/"client" | write `Follow`; read both | no | S |
| system/templates/dashboard/src/settings.js:473 (people editor note), 633-650 | comments and `VIPD/VIPS/VIPKIND` names | comments only (names optional) | no | S |
| dev/proposals/f3 (people_table.py `parse_register`, `render_register`, `people-private.json`, `{"vip": ...}`) | VIP and Hidden taken into private values | depends on open question 1; under (b) the flag moves into the table | yes (propose.py, schema.sql, tracker.py) | M to L |

## B. Rules, skills and Help (text Alan reads)

| File:line | Today | Would change | Guarded | Size |
|---|---|---|---|---|
| system/creaite-rules.md:11, 58, 62, 82, 119, 189 | see the diff | the diff | yes | S |
| .claude/skills/cx-sweep/SKILL.md (11 hits; 14, 45, 71-80) | section "VIPs (BL-99)", "VIP column", "Never write VIP" | heading "People you follow"; keep "never write VIP" sentence at line 80 | no | M |
| .claude/skills/cx-edit/SKILL.md:49 | "make Mia Hale a VIP" etc. | "follow Mia Hale", "Mia isn't followed any more" | no | S |
| .claude/skills/cx-review/SKILL.md:63 | "VIP items first ... flag `vip`" | wording; the flag name internal | no | S |
| .claude/skills/cx-weekly-report/SKILL.md:48 | "`vip`, BL-99" key | wording only | no | S |
| system/templates/help.md:525, 529, 531, 547, 961 | heading "Never miss a VIP", "VIP is private to you", the commands in 547, "VIPs:" at 961 | heading "Never miss a message from someone you follow"; rewrite 529 per rule; commands | no | S |

## C. Settings, catalogue, defaults

| File:line | Today | Would change | Guarded | Size |
|---|---|---|---|---|
| system/scripts/settings_catalogue.py:56 | "Only you see who you follow." | reword if reading (b) | no | S |
| settings_catalogue.py:57-66, 133-145, 361-363 | keys `vip.*`, `warnings.vip_overdue.*`; labels already "People I follow" | none (labels done); keys only if renamed | no | none |
| system/templates/settings-defaults.json:69-70, 251 | `"vip"` block with `_about` "people marked VIP in the people register" | `_about` text; key only if renamed | no | S |
| system/config/settings.json (3 hits) | live copy, same keys | only with a rename (migration) | no | S |
| system/templates/dashboard/src/components/settings/Essentials.jsx:119-132 | `case "vip.enabled"` etc. | none | no | none |

## D. Server and sweep (written or shown output)

| File:line | Today | Would change | Guarded | Size |
|---|---|---|---|---|
| system/scripts/sweep.py:2563 | prints `VIP: n new alert(s)` (the session-start line) | `Followed: n new` | no (sweep.py) | S |
| sweep.py:2552 | prints "Marked n VIP alert(s) seen." | "follow alert" | no | S |
| sweep.py:30-32, 62, 330, 391-392, 935-939, 993, 1179-1250, 1362, 1497, 2316, 2538-2632 (277 hits) | command `sweep.py vip`, flag `"vip"`, `vip.json`, `vip_*` functions; 1362 strips the word VIP from gists | none for the word's enforcement; renames only with the rename option | no | L (rename only) |
| system/scripts/live_server.py:4006, 4020, 3946 | printed "VIP check: n new", "the VIP check failed", status text shown in /api/vip | "Follow check ..." (these reach the dashboard banner and the terminal) | yes | S |
| live_server.py:415 (`VIP_PRIVATE_RULE`), 3819 (`VIP_PROMPT`), 3878, 4199 (`ALERT_WORD`) | prompts given to Claude that say "VIP is private to Alan: never call a person a VIP"; strip regex | reword the prompt to the follow concept; keep the strip regex (it enforces the rule) | yes | S |
| live_server.py routes `/api/vip`, `/api/vip/seen`, `EVENT_PARTS`, `vip_timer`, 4540 | internal names (148 hits in total) | none unless renamed | yes | L (rename only) |
| system/scripts/build_dashboard.py:1110-1156, 2312-2434, 2538-2568, 2882, 3217-3233, 3349 (35 hits) | `vip_unseen`, `vip_kinds`, early-warning signal `vip_overdue`, `"vip"` flag sort, `vip` block given to the page | none unless renamed; `vip_kinds` drops the kind if question 4 says so | yes | M |
| system/scripts/vip_schedule.py (11), usage_log.py:8, 20, 47 (`"vip"` run kind), permissions.py:610-624, reach.py:986, 2424, backup.py:13, 62 | internal | backup.py:13 comment "never vip.json" stays; others none | backup.py/reach.py/permissions.py guarded | none |
| system/scripts/excel_sync.py:291-292 | drops the `vip` flag from the Review sheet | none (it enforces the rule) | no | none |

## E. Dashboard source (system/templates/dashboard/src; dashboard.html is generated: 120 hits, rebuilt)

- today.js (13 hits; 63, 68, 158, 189, 561-596, 662, 830): `VIPCARDS`, `VIPKIND`, `TVIPSEEN`, comments. None user-visible ("Message", "Email", "Teams"). No change except comments.
- settings.js (62 hits; 187-212, 633-829): identifiers, comments "VIP chip", "Settings › VIP alerts" (804), "labelled VIP" (822): comments to reword; visible strings already "People I follow". S.
- core/server.js:70, 463, 495; core/nav.js:97, 220-227; core/globals.json:170, 853-855; core/motion.js:152; stores/rail.js:30; ask.js:650, 691; milestones.js:119; sneak.js:149; components UsagePanel.jsx:25 (label "Alert check", already plain), RailButton.jsx:5, NoteEditor.jsx:39, ChasePane.jsx:9, SneakPeek.jsx:11; style.css:1438-1447, 1644 (`.vipl` class): internal names and comments only. None changed unless renamed.

## F. AI drafting and client-facing code (these enforce the rule: keep)

- system/scripts/drafts.py:910, 932, 963, 2362 (`VIP_RE = \bVIPs?\b`), 2405, 2430, 2623, 2726: drops any line containing VIP from drafts. Keep; it enforces "never in anything creaite writes".
- system/scripts/edit_ai.py:17, 313-314 (`VIP_LOOSE`), 424, 725-733: same for look-alike spellings. Keep.
- system/scripts/report.py:537, 598-609 (`weekly_vip`, `vip` key given to the weekly-report skill; skill says "the people Alan follows closely"): internal weekly report input, not client output; confirm it never prints. Rename only.
- system/scripts/prep_page.py:271, calendar_refresh.py:59 (a prompt sentence "no VIP"): reword the prompt line. S.
- extraction.py, status_*.py, doctor.py, steerco: no VIP hits in a2288848 (grep found none).

## G. Tests that pin the word (dev/tests: 76 files mention it, about 440 matches)

Pinning the behaviour that the word never appears (stay as they are; they enforce the rule): test_vip_private.py (77), test_client_leak_place.py (6), test_vip_confidential.py, test_drafts_report.py, test_minutes_reply_262.py. Tests with the word in names, strings and identifiers (change only under the rename option, or where they assert the Help heading, the `VIP: n new` line, the template column or `make X a VIP`): test_vip_*.py (13 files incl. single_call, close, stage, threads, conversations, matching, promises, quiet_hours, screens, tools_pinned), test_sweep_alerts.py (69), test_alert_actions.py (21), test_followed_needs.py (45), test_settings_page.py, test_settings_catalogue.py, test_run_usage*.py, test_people*.py, test_today_intake_line.py, snapshots/settings-essentials.html (5), handchecks/test_v195.py (24), test_v254, test_v260. Minimum under the proposed rule (no rename): about 6 to 10 test files for the changed strings (the session line, help heading and commands, register template column, `Followed: n new`). Size M. dev/PLAIN-WORDS.md has no VIP or follow entry; if a plain-words baseline test counts words in help.md and the template, the Help rewrite changes its total (check at build).

## H. Where the word VIP would STILL appear after the proposed change

1. Internal names, never shown, exported or shared: `vip.*` settings keys and the `vip` block, `warnings.vip_overdue`, `vip.json`, `sweep.py vip`, `/api/vip*`, `vip_*` functions and variables, the `"vip"` proposal flag and run kind, CSS class `.vipl`, `VIP*` JS names, test names. Allowed by the proposed rule's last sentence. Note: `settings.json` and `vip.json` go into the OneDrive backup zip (closed, only Alan can open): flag in open question 2.
2. The register's old `VIP` column until migrated: allowed ("until it is migrated"); it is in `people-register.md`, which sits in the OneDrive portfolio folder (a project file Alan owns). Under F3 it is removed from the generated copy.
3. The enforcing code: `VIP_RE`, `VIP_LOOSE`, `ALERT_WORD`, strip regexes and the prompt sentences telling Claude never to write the word. Required: they must contain the word to match it.
4. Comments and docstrings, `dev/` history and design notes: allowed (not shown or shared).
5. Not allowed after the change and so changed: Help heading and commands (B), `VIP: n new` and the server's "VIP check ..." lines (D), the register template column and note (A), cx-edit and cx-sweep skill wording (B), the settings-defaults `_about` (C).

## Rename option (not proposed, for sizing)

Rename every internal name to `follow`: settings keys (migration in `settings.json` and the zip), `vip.json` to `follow.json` (backup LEFT_OUT, reach.py, build_dashboard ALERT_HIDDEN, live_server stamps), routes, the proposal flag, tests. Roughly 1,500 matches in system/ and dev/tests, six guarded files, a settings migration and a one-release alias for old commands: L, high risk, no rule benefit.
