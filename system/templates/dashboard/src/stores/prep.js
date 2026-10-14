// @ts-check
/* stores/prep.js (BL-286 part D, BL-256): the in-app prep page's state, Meetings › Prep (#prep=<key>).
   One store per area (dev/COMPONENTS.md §2): the meeting's key, the view the live server returns (/api/prep/view: the page
   model, the stored content and where the Agendas file was saved), the tab, and the functions that change them. Saving the
   focus notes goes through /api/prep/focus/save, the server's own write (prep-focus.json); nothing reaches the tracker. */
import { signal } from "@preact/signals";
import { TODAY } from "../core/page.js";
import { api, oneLine, snack, viaServer } from "../core/server.js";

/** The meeting key the server takes: "HH:MM|title" (today), "YYYY-MM-DD|HH:MM|title" (any day). */
export const PREP_KEY = /^(\d{4}-\d{2}-\d{2}\|)?\d{2}:\d{2}\|.{1,200}$/;

/** The key with its day, so an address keeps naming the same meeting tomorrow: "YYYY-MM-DD|HH:MM|title".
    @param {string} key @param {string} [day] */
export function prepDated(key, day) {
  const k = String(key || "");
  return /^\d{4}-\d{2}-\d{2}\|/.test(k) ? k : `${day || TODAY}|${k}`;
}

/** The address of a meeting's prep page inside creaite: "#prep=<the dated key, URI-encoded>". Other screens link here
    (the Prep popup's Open prep page, BL-287's Open icon).
    @param {string} key @param {string} [day] */
export function prepHref(key, day) { return `#prep=${encodeURIComponent(prepDated(key, day))}`; }

/** The key in "#prep=…", or null when the address isn't a prep page's.
    @param {string} hash */
export function prepKeyOf(hash) {
  const m = /^#?prep=(.+)$/.exec(String(hash || ""));
  if (!m) return null;
  let k = "";
  try { k = decodeURIComponent(m[1]); } catch (e) { return null; }
  return PREP_KEY.test(k) ? k : null;
}

/** @typedef {{type: string, id?: string, kind?: string, path?: string, label?: string, url?: string, section?: string}} Typed */
/** @typedef {{text: string, sources?: Typed[]}} NoteLine */
/** @typedef {{ok: boolean, message?: string, model?: any, stored?: boolean, saved?: {path: string, at: string, at_shown: string} | null, live?: boolean}} PrepViewResult */

export const prepViewKey = signal(/** @type {string | null} */ (null));
export const prepView = signal(/** @type {PrepViewResult | null} */ (null));
export const prepLoading = signal(false);
export const prepTab = signal("prep");
export const prepSaving = signal(/** @type {string} */ (""));

let pageAsked = 0;
/** Load (or reload) a meeting's view. Claude never runs: the server reads the stored content.
    @param {string} key @param {{keepTab?: boolean}} [o] */
export async function loadPrep(key, o = {}) {
  const mine = ++pageAsked, same = prepViewKey.value === key;
  prepViewKey.value = key;
  if (!o.keepTab && !same) prepTab.value = "prep";
  if (!viaServer()) { prepView.value = { ok: false, message: "The prep page needs the live server." }; return; }
  prepLoading.value = true;
  if (!same) prepView.value = null;
  const r = await api("/api/prep/view", { key });
  if (mine !== pageAsked) return;
  prepLoading.value = false;
  prepView.value = r && r.ok ? r : { ok: false, message: oneLine((r && r.message) || "") || "Couldn't load the prep page" };
}

/** Save the focus record in place (no Accept): the notes edited on the page, or the reading's "show".
    @param {{notes?: Record<string, NoteLine[]>, reading?: any, excluded?: string[], questions?: string[] | null}} part @param {string} what */
export async function saveFocus(part, what) {
  const key = prepViewKey.value;
  if (!key) return false;
  if (!viaServer()) { snack("Saving needs the live server"); return false; }
  prepSaving.value = what;
  const r = await api("/api/prep/focus/save", { key, ...part });
  prepSaving.value = "";
  if (!r || !r.ok) { snack(oneLine((r && r.message) || "") || "Not saved"); return false; }
  const v = prepView.value;
  if (v && v.model && key === prepViewKey.value) {
    if (part.reading || part.excluded || "questions" in part) await loadPrep(key, { keepTab: true });   // the work table follows the reading; the questions are the model's
    else prepView.value = { ...v, model: { ...v.model, focus: r.focus } };
  }
  snack(r.page ? "Saved, and the Agendas page was updated" : "Saved");
  return true;
}

/** A section's lines from the text in its box, one line each; a line that is unchanged keeps its citations, an edited one
    keeps those of the line it replaced.
    @param {string} text @param {NoteLine[]} before @returns {NoteLine[]} */
export function linesFrom(text, before) {
  const old = before || [];
  return String(text || "").split("\n").map(s => s.trim()).filter(Boolean).slice(0, 12).map((t, i) => {
    const same = old.find(x => x.text === t) || old[i];
    return { text: t.slice(0, 600), sources: (same && same.sources) || [] };
  });
}
