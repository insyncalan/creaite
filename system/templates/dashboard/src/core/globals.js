// @ts-check
/* core/globals.js (BL-231 step 2b): the page's names on window, on purpose and in one place. The lists are in
   core/globals.json (dev/tools/build_dashboard_js.py reads it too); main.js calls publish() once every module has loaded.

   - tests: dev/tests drive the page by name (b.eval("go('today')"), b.wait("VIEW==='work'")). Each listed name that a
     module exports is put on window. `build_dashboard_js.py globals` regenerates the list; test_dashboard_split checks it.
   - live: the shared state (core/state.js). window.VIEW reads and writes shared.VIEW, for the tests (VSTATE="ok").
   - seams: functions a test replaces (window.api=…, snack=…). Their module keeps them in a `let` and exports
     `<module>Seams` with a setter for each, so the page's own calls see the replacement, as they did before modules.
   - not_on_window: exported names that would hide the browser's own (window.open).
   - Inline on…= attributes: the page has none (BL-255 keeps it that way), so they need no names.
   Only these names are on window; the modules reach each other by import (BL-231 step 2b: script/ and its prologue are gone). */
import G from "./globals.json";
import { shared } from "./state.js";

const taken = n => { const d = Object.getOwnPropertyDescriptor(window, n); return !!d && !d.configurable; };
const put = (n, desc) => { if (!taken(n)) Object.defineProperty(window, n, { configurable: true, ...desc }); };

export function publish(page) {
  for (const n of G.names.live) put(n, { get: () => shared[n], set: v => { shared[n] = v; } });
  const seams = new Set();
  for (const [key, setters] of Object.entries(page)) {
    if (!key.endsWith("Seams")) continue;
    for (const [n, set] of Object.entries(setters)) { seams.add(n); put(n, { get: () => page[n], set }); }
  }
  const skip = new Set([...G.names.live, ...G.names.not_on_window, ...seams]);
  for (const n of G.names.tests) if (n in page && !skip.has(n)) put(n, { value: page[n], writable: true });
}
