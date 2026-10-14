# V19 CSP note: BL-255 prototype, report-only

Branch `dev-csp-proto`, 12-10-2026, laptop 2 (item E of `dev/LAPTOP-2-WORK.md`). Nothing under `system/` changed.

## The answer

BL-255's policy, exactly as written, is close to ready. Across 30 screens and states it raised **one violation**: the service worker. `script-src` holds only a hash, and `worker-src` falls back to `script-src` (not to `default-src`), so registering `/sw.js` is refused. **Add `worker-src 'self'`.** Nothing else fired: no inline handlers, no `javascript:` links, no `eval`, and the app script's hash matched.

`style-src 'unsafe-inline'` has to stay for now. Without it, 236 `style=` violations fire on 25 of the 30 screens (90 distinct).

## How it was run

`dev/tools/csp_proto.py` (development only):

- It builds the tests' sample vault (`test_dashboard.populate`: two projects, a pending proposal, a Current-state image) in a scratch folder.
- It starts that vault's own `live_server.py` unchanged, wrapped at run time. The wrapper adds `Content-Security-Policy-Report-Only` to every HTML page and to `sw.js`, and adds a `/csp-report` endpoint.
- It drives headless Chrome (`dev/tools/cdp.py`) through every screen, records each `securitypolicyviolation` event by screen, and collects the browser's own reports as a cross-check.

```
python3.14 dev/tools/csp_proto.py run --out <scratch> --policy bl255|strict|lean
```

The hashes are computed from each response as the browser parses it (each block ends at the first close tag). Only executed scripts are hashed: the `<script type="application/json">` data block is not executed, needs no hash and raised nothing.

Three policies were tested. Each also has `'report-sample'` and a `report-uri`, which change nothing that is allowed.

| Policy | What it is |
|---|---|
| `bl255` | BL-255's text exactly, with the app script's hash filled in |
| `strict` | `bl255` with `style-src 'self' 'sha256-<style block>'`, so no `'unsafe-inline'` |
| `lean` | `bl255` without `data:` and `blob:` in `img-src` and `font-src` |

The screens: page load (Today), Today, Projects, the project page, Milestones, the milestone editor, People, Person, Work (actions; and the action, RAID and decision panels open), Review, Intake, Files, Activity, the six Settings categories, the three Help tabs, ⌘K with a query, ask creaite's panel, an image attached in ask creaite, and the offline page.

## Violations by screen

| Screen | bl255 | strict (`style=`) | lean |
|---|---|---|---|
| Page load (Today) | 1 (worker-src) | 39 (+1 worker-src) | 8: favicon and mask `data:`, 6 Roboto and Help `data:` fonts, worker-src |
| Today | 0 | 2 | 0 |
| Projects | 0 | 2 | 0 |
| Project page (ABC) | 0 | 26 | 1: the Current-state image (`data:`) |
| Milestones | 0 | 0 | 0 |
| Milestone editor | 0 | 8 | 0 |
| People / Person | 0 / 0 | 1 / 5 | 0 |
| Work: actions; action, RAID, decision panels | 0 | 3; 4, 3, 3 | 0 |
| Review | 0 | 8 | 0 |
| Intake | 0 | 14 | 0 |
| Files | 0 | 24 | 0 |
| Activity | 0 | 27 | 0 |
| Settings: General, Work and views, Health and warnings | 0 | 5, 8, 17 | 0 |
| Settings: Capture and alerts, People and projects, System | 0 | 5, 9, 17 | 0 |
| Help: start, how-to, reference | 0 | 0 | 0 |
| ⌘K / ask creaite panel | 0 / 0 | 2 / 1 | 0 |
| ask creaite: image attached | 0 | 4 | 2: preview `blob:`, shrunk thumbnail `data:` |
| Offline page | 0 | 0 | 0 |
| **Total** | **1** | **236 + 1** | **10** |

## Violations by kind

| Kind | bl255 | strict | Notes |
|---|---|---|---|
| Inline handler (`on*=`) | 0 | 0 | None in the source (0) or at run time |
| `javascript:` link | 0 | 0 | None in the source |
| Inline `<script>` | 0 | 0 | One executed block; its hash matched |
| `style=` attribute | 0 | 236 (90 distinct, 66 distinct values) | 215 in the template source; the rest are built at run time |
| `<style>` element | 0 | 0 | See below: the run-time one happened to be hashed |
| worker-src (`/sw.js`) | 1 | 1 | Needs `worker-src 'self'` |
| img-src `data:` / `blob:` | 0 | 0 | `lean`: needed (favicon, CSS masks, Current-state images, image thumbnails; attach preview) |
| font-src `data:` | 0 | 0 | `lean`: needed (the embedded Roboto and Help faces) |
| connect-src | 0 | 0 | `'self'` covers every `fetch` and the BL-253 change stream (a `fetch` stream, not `EventSource`) |

## What each directive needs

- **`script-src`:** the one hash is enough. `render()` only replaces `/*__FONTS__*/`, which is in the `<style>` block, and `/*__DATA__*/`, which is in the JSON block, so **the app script's hash is fixed per release**. It can be computed once at build, not on every request. `CREAITE_TEST_INJECT` appends a script for tests; it will be reported, which is harmless in report-only and a test-only exception under enforcement.
- **`worker-src 'self'`:** new. Without it the installed app loses its offline page (BL-86).
- **`style-src 'self' 'unsafe-inline'`:** keep it. The `strict` list, most common first, is `white-space:nowrap` (41), `text-align:right` (24), `width:80px` (24, Settings number inputs), `width:90px` (12), `cursor:pointer` (10) and `max-width:36ch` (8). These are fixed strings that could become classes. The rest are computed values: timeline positions (`left:240px`), sizes (`width:728px;height:108px`), `--split:62`, theme swatches (`background:#0B6E7F`) and image thumbnails (`background-image:url('data:…')`). Those would need CSSOM (`el.style.setProperty(...)`, which CSP allows) instead of HTML strings.
- **The run-time `<style>`** (`document.head.insertAdjacentHTML(... '<style>.diagerr…')`, line 8337) did not fire under `strict` only by chance: the prototype hashes every `<style>…</style>` it finds in the page text, the string inside the script included. A real strict policy should move those rules into the main `<style>` block.
- **`img-src 'self' data: blob:`:** all three are needed.
- **`font-src 'self' data:`:** needed. Help's fonts are `data:` too and raised nothing under `bl255`.
- **`connect-src 'self'`:** enough.
- **The others** (`object-src 'none'`, `base-uri 'none'`, `form-action 'self'`, `frame-ancestors 'none'`): nothing fired. `manifest-src` falls back to `default-src 'self'`, which covers `/manifest.webmanifest`.

## Not exercised, checked by reading

- **The Prep page (BL-98)** needs a Claude run. `window.open("")` and the `blob:` link fallback both **inherit the dashboard's policy**. The Prep page HTML (`prep_page.py`) has a `<style>` and no `<script>`, and the "Preparing…" stub has a `style=`: fine under `bl255`, but it would break under a strict `style-src`.
- **`offline.html`** has its own inline `<script>` and `<style>`. The prototype hashed it per response (0 violations). BL-255 must give `/offline` its own hash, or move its script into a file served from `/app/`.
- **The saved-to-disk page:** the `<meta>` policy was not tested. `SERVED` is false there, so it has no service worker, and `worker-src` doesn't matter.
- **Current-state image upload** (`curImgFile`), the AI draft dialogs and context menus were not opened. They use the same `style=`, `data:` and `blob:` patterns already seen.

## What BL-231's bundle must change

1. **Keep exactly one executed inline script** (the bundle), still inline so the saved page works. Write it as the exact bytes between `<script>` and `</script>`, with no `</script` inside: esbuild escapes it in strings, so check it. **Compute its hash in the build** (`build_dashboard.py` or `build_release.py`), not at render.
2. **No new inline handlers, `javascript:` URLs, `eval`, `new Function` or `setTimeout("string")`.** Add a check.py rule so the count stays at zero.
3. **Move the run-time `<style>` insertions into the stylesheet.** Optionally, start replacing the fixed `style=` strings with classes and the computed ones with CSSOM, as screens move (BL-256's components make this natural). This is only needed if `'unsafe-inline'` is ever dropped.

## What BL-255 must change

1. **Add `worker-src 'self'`** to the policy text. This is the only change the run asked for.
2. **Hash once per release.** Send the header from `live_server.py` on every HTML response: `/`, `/dashboard.html` and `/offline`, each with its own hash. Send the `<meta>` version in the saved page, without `frame-ancestors`.
3. **Keep the existing BL-212 header** (`frame-ancestors 'none'`) in the same header, or merge it in, so the two do not conflict.
4. **Report-only for a week,** with a `report-uri` endpoint like the prototype's. Reports carry the page URL and blocked URI, never page text (`report-sample` is optional; leave it out in a live vault). Log them as counts to the debug log (BL-102) rather than keeping the bodies.
5. **Add a test:** the served page's hash matches its script, and a headless run of the main screens raises no violation (`csp_proto.py`'s `visit()` is a starting point).

## BL-255, report-only (sprint-csp-report, 13-10-2026)

**Done.** `live_server.py` sends `Content-Security-Policy-Report-Only` on every `text/html` reply (`/`, `/dashboard.html`, `/offline`), built from the bytes being sent (`csp_hashes`: each executed inline `<script>`, the JSON data block and `src=` scripts left out, a block ending at its first close tag, CR LF read as LF). So the hashes follow the template and BL-231's bundle without a build step, and `CREAITE_TEST_INJECT`'s script is covered too. The policy is BL-255's text plus `worker-src 'self'` and `report-uri /csp-report`. BL-212's enforced `Content-Security-Policy: frame-ancestors 'none'` and the other headers are untouched (a separate header).

- `POST /csp-report` is answered before the token check (a browser's report can't carry one): loopback address and Host only, no other site's `Origin`, not `Sec-Fetch-Site: cross-site`, 16 KB at most, 60 reports a minute (the rest counted and said once). Each report is one `INFO csp report-only violation: <directive> <kind>` line (kind: inline, eval, data, blob, self, external, other). Nothing else is written.
- `live_mode.script_policy`: `"report-only"` (default) or `"off"`. Added to `settings-defaults.json`, so an update adds it.
- doctor: "Script policy (report-only) — n violations in 7 days (top three by directive and kind)", which Copy diagnostics includes.
- Tests: `dev/tests/test_script_policy.py`, with a Chrome check that the page raises no violation and that an unlisted inline script still runs and is reported.

**Style hashes are computed but not sent.** Listing them (`style-src-elem`) cancels `'unsafe-inline'`, and the run-time `.diagerr` `<style>` (dashboard.html, `insertAdjacentHTML`) is then reported on every load, which would bury the week's signal. `CSP_STRICT_STYLES = True` turns them on once that rule is in the stylesheet (BL-231); `style-src-attr 'unsafe-inline'` then keeps the `style=""` attributes.

**What enforcing will need.**
1. A week of report-only with doctor at 0 (or only understood reports), on Alan's own vault.
2. `live_mode.script_policy: "enforce"`, sending `Content-Security-Policy` with the same text merged into BL-212's header (one `frame-ancestors 'none'`), report-uri kept. Decide whether the test-only `CREAITE_TEST_INJECT` script is hashed (it is today) or the tests run report-only.
3. The saved-to-disk page: a `<meta http-equiv="Content-Security-Policy">` from `build_dashboard.py` (no `frame-ancestors`, no `report-uri`; a meta tag can't be report-only, so this lands with enforcement).
4. The Prep page opened with `window.open("")` inherits the policy; check it under enforcement (it has a `<style>` and no script: fine unless strict styles are on).
5. Optionally, after BL-231: move `.diagerr` into the stylesheet and turn on `CSP_STRICT_STYLES` in report-only first.
