// @ts-check
/* stores/reportingSettings.js (#221 H1): whether a project has a separate client report. ONE function, `clientReportOn(code)`, is the
   only place the Reporting hub (and anything else) asks. H1's version answers true for every project (the default for existing
   projects, brief item 6) unless the page has been told otherwise for this session with `setClientReportOn`. H3 replaces the body
   with the real, persistent storage (the project's own setting, the same one as Settings › Projects) and keeps the two names. */
import { signal } from "@preact/signals";

/** Projects switched off for this page's life (H1 only; H3's storage replaces it). @type {import("@preact/signals").Signal<Set<string>>} */
const off = signal(new Set());

/** Does this project have a separate client report? Reads a signal, so a page that calls it redraws when the setting changes.
    @param {string} code @returns {boolean} */
export function clientReportOn(code) {
  return !off.value.has(code);
}

/** Switch a project's client report on or off for this page (H1's stand-in for H3's setting). @param {string} code @param {boolean} on */
export function setClientReportOn(code, on) {
  const next = new Set(off.peek());
  if (on) next.delete(code); else next.add(code);
  off.value = next;
}
