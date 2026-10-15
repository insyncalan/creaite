# dev-build-isolation: note for the Scrum Master

From laptop 2, 13-10-2026. Two lines in `dev/` only. **Merge before laptop 2's BL-264 branch.**

## The problem

On laptop 2, a fresh `main` failed `check.py`:
- **"BUILT dashboard.html is out of date":** rebuilding added `"use strict";` to the app script.
- **3 TSC errors:** TS2322, "`Timeout` is not assignable to `number`", in `core/dom.js`.

**Cause:** an unrelated JavaScript project had left `tsconfig.json`, `package.json` and `node_modules` in Alan's home folder.
- **esbuild** looks for a `tsconfig.json` in the folders above the source, found `~/tsconfig.json` (`"strict": true`) and emitted strict mode.
- **TypeScript** loads `@types` packages from parent folders' `node_modules`, and picked up `@types/node`, so `setTimeout` returned Node's `Timeout`.

Laptop 1 has no such files, so it passed there. Any machine with a `tsconfig.json` or `node_modules` above the repo would build a different page.

## The fix

- **`dev/tools/build_dashboard_js.py`:** adds `--tsconfig-raw={}` to esbuild's flags, so it never reads a tsconfig or jsconfig from outside the repo.
- **`dev/jsconfig.json`:** `"types": []`, so tsc loads no `@types` package from a parent folder. The dashboard's own types come from `dev/types/` through `include`, as before.

## Checks

- **Run with the stray home-folder files still in place:**
  - `split_dashboard.py stale` says up to date;
  - `typecheck.py` reports 0 type errors;
  - `check.py` says OK.
- **The build page is unchanged:** byte for byte, the build matches the committed `dashboard.html`.
- **Related tests:** 18 test files that mention the build, split, esbuild or type check all pass locally at `-j 2`.
- **Since then, on laptop 2:** Alan has moved the stray project out of the home folder, so this laptop is clean either way.
