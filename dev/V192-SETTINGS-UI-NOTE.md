# v1.9.2 · BL-320 page side: Settings, calmer, with Health inside

Branch `v192-settings-ui`, from `origin/v192-settings-server` (with `origin/main` merged in for Preact). For Team 1. Built on the
server note, `dev/V192-SETTINGS-SERVER-NOTE.md`. The full description is in `dev/dashboard-spec.md`, "Settings, calmer, and
Health: the page".

## What was built

- **Four places:** Essentials (opens first), People and projects, Advanced, Health. The sections keep their old `cat`; `CATOF`
  in `settings.js` maps them, so today.js's Set-up and drafts.js's AI drafts move with no change to those modules. Old
  addresses (`#settings/general`, `/system`, `/capture`, `prefs`…) still open the right place.
- **Preact components** (`src/components/settings/`): `Essentials.jsx`, `MoreSettings.jsx` (Advanced › Everything else),
  `Health.jsx`, `SettingRow.jsx` (the row frame: label, line, dot, Reset, Saved). Store: `src/stores/settings.js`.
- **Essentials:** the catalogue's 16 rows in six sections, each with its line and a real control (text with HH:MM checks,
  named tick-box groups, selects, switches, one AI drafts switch for every kind, mixed when some are off).
- **Advanced:** the older cards under their old names, with the Essentials' rows taken out, then Everything else: every other
  catalogue setting with a control by type, its default and why, the dot and Reset; set-up-only settings read only, with why.
  The old Advanced card (ADVSETS) is gone; its settings and limits are in Everything else.
- **Dot, Reset, Show changed only** everywhere in Essentials and Advanced (older cards get theirs from `setMark`). Reset uses
  `/api/settings/reset`. Search also finds a setting by its line, reason or old key.
- **Health:** problems from `/api/health`, severity in words, **How to fix** (manual step, Copy for a command), stopped errors,
  "n checks fine". Below it: the live server, Set-up, Diagnostics, version, Stop.
- **No VIP label** on Essentials or the People I follow card (the early warning's and ignore rules' wording is BL-288's).
- Help's Settings section rewritten and shorter; other Help references point at the new places.

## Fix it (wired to v192-fixit, merged here)

- `origin/v192-fixit` (887f8fd) is merged into this branch; `test_tracker.py` copies both `settings_catalogue.py`/`health.py` and `health_fixes.py`.
- `health.py`: `fix_for(kind, problem_id, detail)` asks `health_fixes.fix_for(check id, detail)`; when it finds a fix the problem's
  `fix` is `health_fixes.describe(id)` (`built: true`, with `does` and its command or url) plus the usual fields. Every other fix
  stays `built: false` with the manual step. `/api/health` also returns `standalone` (icon, m365), described the same way.
- `Health.jsx`: a built fix shows its `does` line and its button; the button posts `POST /api/health/fix/<id>` with no body and no
  query string (the server's contract, unchanged), says the reply's `message`, opens its `url` (m365: Claude's connector page)
  and checks again. The standalone fixes are under "If you need them". The mockup's "After every update" block is drawn, since
  update.py now runs those steps.
- `health_fixes.py` is in the scripts row of `system/creaite-rules.md`'s folder map.

## The rail's count (hook)

- `setRailCount` (v192-sidebar) isn't on this base. `stores/settings.js` has `showHealthCount(n)`, an empty hook an effect
  calls whenever `healthCount` changes. After merging v192-sidebar its body becomes
  `setRailCount("settings", n, `${n} to fix in Settings › Health`)` (import from `./rail.js` in stores).
- The count comes from the last check, kept in this browser (`creaite-health-count`), and a check a minute after start-up
  when the last is over a day old. Nothing polls.

## Not changed (other teams' files)

- Strings in today.js, review.js, rail.js, core/nav.js, core/fields.js and core/page.js still name the old places
  ("Settings › General › Appearance", "Settings › Work and views", "Settings › Health and warnings"…). Their links still work;
  the words want a pass by their owners.
- Set-up's own "Run the health check" button (today.js) now sits under Health's list, so it repeats it; Team 1 may drop it.

## Snapshots (BL-254)

- The six goldens `settings-general|work|health|capture|people|system` are replaced by four, `settings-essentials|people|
  advanced|health`, re-recorded on purpose: the page's structure is what BL-320 changes. Health's golden uses a fixed
  `/api/health` answer (doctor's answer depends on the machine). `help` was re-recorded for the Help text.
- **Needs Alan's agreement** (BL-254) before merge.

## Tests

- `dev/tests/test_settings_calmer.py` (new, 14 tests, Chrome).
- Updated for the new places: `test_settings_page.py`, `test_motion.py`, `test_field_names.py`, `test_project_names.py`,
  `test_dashboard_editing.py` (themes: file mode has no catalogue), `test_drafts_email.py`, `test_drafts_forms.py`,
  `test_snapshots.py`, `test_ui_sweep.py`.
