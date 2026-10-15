# V190 BL-255 check note

Branch `dev-bl255-check`, from `origin/release-191` (5926119). Asked because the release-branch integration said "BL-255's re-hash (wave 3): no branch seen".

## Answer

**Nothing is missing.** There is no re-hash branch because none is needed: BL-255 (merged in `d1b66f1` and `702b00e`, then `ff9b6e0`) computes the hashes **per response** from the exact bytes `live_server.py` sends (`csp_hashes`, `csp_policy`, `csp_header`), not at build time. Whatever the template or the Preact bundle becomes, the header names its scripts and styles; it can't go stale. STATUS's wave 3 "re-hash" was planned when the hash was to be computed in the build (`V19-CSP-NOTE.md`, "What BL-231's bundle must change", 1); sprint-csp-report chose per response instead.

## What exists (on release-191)

- `Content-Security-Policy-Report-Only` on every HTML reply (`/`, `/dashboard.html`, `/offline`): BL-255's text, plus `worker-src 'self'`, `style-src-elem 'self' <style hashes>`, `style-src-attr 'unsafe-inline'`, `report-uri /csp-report`. BL-212's enforced `frame-ancestors 'none'` header unchanged. `live_mode.script_policy` "off" sends none.
- `POST /csp-report` answered before the token check, as Alan decided (13-10-2026): loopback only, no cross-site Origin, 16 KB, 60 a minute, one debug-log line each (directive and kind only). doctor counts them.
- **The `<meta>` policy for the page saved to disk is not there, by design**: a meta tag can't be report-only, so it lands with enforcement (`V19-CSP-NOTE.md`, "What enforcing will need", 3). Not a gap for v1.9.0's report-only week.

## Verified on this branch

- The committed `system/templates/dashboard.html` (the bundle) has exactly two `<script>` tags: the `application/json` data block (not hashed, not run) and the one app script, with no `</script` inside it and no `src=`. The served hash equals the hash of that script (independently computed).
- No inline `on*=` attributes, no `javascript:` URLs, no external `src`/`href`, and in the app script no `eval(`, `new Function(`, string `setTimeout`/`setInterval`, `on*="` markup or `javascript:`.
- Report-only on by default; the report endpoint as decided.
- **Headless Chrome, the real server's policy, every screen** (a scratch sweep from `csp_proto.py`'s list plus the newer screens, on the prep test world): page load; Today, Projects, a project page, Milestones, People, a person, Work (actions, an action, a RAID item, a decision), Mine, Review, Intake, Files and Files › Agendas (a saved prep page present), Activity, all 6 Settings categories, all 3 Help tabs (fonts), the command palette, ask creaite and an attached image (`blob:`), a Meeting page, the Prep popup, Current state with an image inserted, and `/offline`. **0 violations, 0 page errors, 0 reports reached `/csp-report`.** The service worker registered (worker-src) and the event stream was up (connect-src).
- Not covered: Meetings › Prep (`#prep=`), because `sprint-prep-page` isn't on release-191 (RELEASE-BRANCHES-NOTE); the prep page HTML itself has a `<style>` and no script, opened in its own window.

## Added

`dev/tests/test_script_policy.py`:
- `Template`: the committed bundle is one app script plus the data block, the hash sent is that script's, and nothing a hash-only policy would stop (the static checks above), so a later bundle that adds an inline handler, an external script or `eval` fails here.
- `InChrome` now walks every main screen, Settings category and Help tab (was Projects only) and asserts the service worker registered, with no violation on any.

Tests: test_script_policy, test_security_headers, test_dashboard_split, test_snapshots, test_live_server pass; `check.py` OK.
