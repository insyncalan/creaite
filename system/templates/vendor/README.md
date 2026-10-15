# Bundled JavaScript libraries

`build_dashboard.py` inlines these into `dashboard.html`, so the page works offline with no CDN.

| File | Library | Licence |
|------|---------|---------|
| `tabulator.min.js`, `tabulator.min.css` | Tabulator: sortable, filterable tables | MIT |
| `chart.umd.min.js` | Chart.js: charts and the risk grid | MIT |

Add these files in build Step 4. Download them once, from the official releases, on a machine with internet access. Keep the version numbers and licence files beside them.

## Fonts and icons (Material 3)

| File | Library | Licence |
|------|---------|---------|
| `roboto-400.ttf`, `roboto-500.ttf`, `roboto-700.ttf` | Roboto (Regular, Medium, Bold), from Google Fonts; licence in `roboto-OFL.txt` | SIL OFL 1.1 |
| `material-symbols-*.svg` (optional) | Material Symbols, for full M3 icon fidelity | Apache-2.0 |

`build_dashboard.py` embeds the Roboto files into `dashboard.html` as base64 `@font-face` rules, so the page needs no network. Tabulator and Chart.js aren't needed: the reference design draws its own tables and charts.

## Help's fonts (BL-84)

| File | Font | Licence |
|------|------|---------|
| `schibsted-grotesk-500.woff2`, `-700`, `-800` | Schibsted Grotesk (display) | SIL OFL 1.1 |
| `source-sans-3-400.woff2`, `-600` | Source Sans 3 (body) | SIL OFL 1.1 |
| `jetbrains-mono-500.woff2` | JetBrains Mono (mono) | SIL OFL 1.1 |

Latin subsets only, and only the weights Help uses, to keep the size down. The licences are in `help-fonts-OFL.txt`. `build_dashboard.help_font_faces()` embeds them as data URIs in the dashboard, and `dev/tools/build_guides.py` in the two guides, so nothing loads from the network. A missing file is skipped and the page uses the system's fonts. `dev/tools/fetch_help_fonts.py` downloads them (development only).

## The wordmark (BL-273)

The rail's "creaite" wordmark in `dashboard.html` is IBM Plex Mono SemiBold (IBM Corp., Reserved Font Name "Plex") drawn as
outlined SVG paths, under the SIL Open Font License 1.1 (`dev/reference/logo/OFL.txt`). No font file is bundled: the page
carries the paths only. `dev/tools/outline_wordmark.py` made them once, in development, into `dev/reference/logo/wordmark-paths.json`.

## Preact and signals (BL-256)

| Folder in `preact/` | Library | Version (released) | Licence |
|------|---------|---------|---------|
| `preact/` | Preact, with its hooks and JSX runtime | 10.29.8 (01-08-2026) | MIT (`preact/LICENSE`) |
| `signals/` | `@preact/signals` | 2.11.2 (04-09-2026) | MIT (`signals/LICENSE`) |
| `signals-core/` | `@preact/signals-core` | 1.14.4 (07-07-2026) | MIT (`signals-core/LICENSE`) |

Only the ES module files the bundle needs and their type files (for `dev/tools/typecheck.py`) are kept.
`preact/manifest.json` records each tarball's SHA-256 and each file's; `dev/tests/test_vendor_preact.py` checks them.
The dashboard's build (`dev/tools/build_dashboard_js.py`, development only) bundles them into `dashboard.html` with the
rest of the script, so the page needs no network and nothing is installed at run time (NFR-12). To upgrade: Alan runs
`dev/tools/fetch_preact.sh`, then `python3 -I dev/tools/vendor_preact.py` with new pins, and the page is rebuilt.

## Tiptap, the editor (BL-301)

| File in `tiptap/` | Library | Version | Licence |
|------|---------|---------|---------|
| `tiptap.module.js` | Tiptap with `@tiptap/markdown`, ProseMirror, marked, linkifyjs and their dependencies, and creaite's exact Markdown writer (`dev/tiptap/`), as one minified ES module | Tiptap 3.31.3 (04-09-2026) | MIT (every bundled package's own licence file in `tiptap/licenses/`) |

`tiptap/manifest.json` records each bundled package's version, tarball SHA-256 and licence, the esbuild version, the
SHA-256 of the `dev/tiptap/` sources it was built from, and the SHA-256 of every file in the folder. It is built in
development only, never at run time (NFR-12): `python3 dev/tools/tiptap.py fetch` (the pinned tarballs, each checked
against its hash), then `python3 dev/tools/tiptap.py vendor`; commit the folder. `python3 dev/tools/tiptap.py vendor
--check` rebuilds in memory and compares byte for byte; `dev/tools/check.py` (VENDORED) and
`dev/tests/test_vendor_tiptap.py` do the same. The dashboard's one editor (`src/core/editor.js`, `creaiteEditor`) loads it (BL-301 A).
