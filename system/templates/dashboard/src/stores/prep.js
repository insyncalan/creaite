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
/** The words the page's one polite live region says: "Saved" after each save, "" while saving or typing (#111 piece A). */
export const prepSavedSay = signal("");

let pageAsked = 0;
/** Load (or reload) a meeting's view. Claude never runs: the server reads the stored content.
    @param {string} key @param {{keepTab?: boolean}} [o] */
export async function loadPrep(key, o = {}) {
  const mine = ++pageAsked, same = prepViewKey.value === key;
  prepViewKey.value = key;
  if (!o.keepTab && !same) prepTab.value = "prep";
  if (!viaServer()) { prepView.value = { ok: false, message: "The prep page needs creaite to be running." }; return; }
  prepLoading.value = true;
  if (!same) prepView.value = null;
  const r = await api("/api/prep/view", { key });
  if (mine !== pageAsked) return;
  prepLoading.value = false;
  prepView.value = r && r.ok ? r : { ok: false, message: oneLine((r && r.message) || "") || "Couldn't load the prep page" };
}

/** Save the focus record in place (no Accept): the notes edited on the page, or the reading's "show". `quiet` (save-as-typed)
    leaves out the "Saved" toast: the page's own status line says it.
    @param {{notes?: Record<string, NoteLine[]>, reading?: any, excluded?: string[], questions?: string[] | null}} part @param {string} what
    @param {{quiet?: boolean}} [o] */
export async function saveFocus(part, what, o = {}) {
  const key = prepViewKey.value;
  if (!key) return false;
  if (!viaServer()) { snack("Saving needs creaite to be running"); return false; }
  prepSaving.value = what;
  prepSavedSay.value = "";                                  // cleared first, so the same word is announced again after the next save
  const r = await api("/api/prep/focus/save", { key, ...part });
  prepSaving.value = "";
  if (!r || !r.ok) { snack(oneLine((r && r.message) || "") || "Not saved"); return false; }
  const v = prepView.value;
  if (v && v.model && key === prepViewKey.value) {
    if (part.reading || part.excluded || part.questions === null) await loadPrep(key, { keepTab: true });   // the work table follows the reading; the research's questions come back from the model
    else if (Array.isArray(part.questions)) prepView.value = { ...v, model: { ...v.model, focus: r.focus, questions: (r.focus && r.focus.questions) || part.questions, questions_edited: true } };
    else prepView.value = { ...v, model: { ...v.model, focus: r.focus } };
  }
  prepSavedSay.value = "Saved";
  if (!o.quiet) snack(r.page ? "Saved, and the Agendas page was updated" : "Saved");
  return true;
}

/** Saves one after another, so a second edit never starts from a view the first has not yet updated. */
let queue = Promise.resolve();
/** @template T @param {() => Promise<T>} fn @returns {Promise<T>} */
const inOrder = fn => { const run = queue.then(fn, fn); queue = run.then(() => {}, () => {}); return run; };

/** Notes sections on the page: three editors (Objective, Talking points, Ask) and the Carried over lines, which an edit of
    another section carries unchanged. */
export const NOTE_KEYS = ["objective", "talking_points", "ask", "carried_over"];

/** Save one section's text as typed (quiet, in order): the other sections are the view's latest.
    @param {string} sec @param {string} text */
export function saveSection(sec, text) {
  return inOrder(async () => {
    const v = prepView.value, notes = (v && v.model && v.model.focus && v.model.focus.notes) || {};
    /** @type {Record<string, NoteLine[]>} */
    const all = {};
    NOTE_KEYS.forEach(k => { all[k] = k === sec ? linesFrom(text, notes[k]) : (notes[k] || []); });
    return saveFocus({ notes: all }, "notes", { quiet: true });
  });
}

/** Save the questions and asks as typed. @param {string} text */
export function saveQuestions(text) {
  return inOrder(() => saveFocus({ questions: text.split("\n").map(x => x.trim()).filter(Boolean) }, "questions", { quiet: true }));
}

/** @typedef {"raise" | "note" | "skip"} Play */
/** What Alan has chosen for an item: Raise (named in the focus), Skip (ticked out of it), else Note. Kept in prep-focus.json's
    reading and excluded lists (the existing routes); never in the tracker.
    @param {string} id @param {any} focus the view's model.focus @returns {Play} */
export function playOf(id, focus) {
  const f = focus || {};
  if ((f.excluded || []).includes(id)) return "skip";
  return ((f.reading || {}).focus || []).some((/** @type {any} */ x) => x.id === id) ? "raise" : "note";
}

/** Raise / Note / Skip for one item. @param {{id: string, text: string}} item @param {Play} to */
export function setPlay(item, to) {
  return inOrder(async () => {
    const v = prepView.value, f = (v && v.model && v.model.focus) || {};
    if (playOf(item.id, f) === to) return true;
    const r = f.reading || { focus: [], aim: "", show: "focus-first" };
    const focus = (r.focus || []).filter((/** @type {any} */ x) => x.id !== item.id);
    if (to === "raise") {
      if (focus.length >= 12) { snack("Twelve items at most can be raised"); return false; }
      focus.push({ id: item.id, text: String(item.text || item.id).slice(0, 200) });
    }
    const excluded = (f.excluded || []).filter((/** @type {string} */ x) => x !== item.id).concat(to === "skip" ? [item.id] : []);
    return saveFocus({ reading: { ...r, focus }, excluded }, "play", { quiet: true });
  });
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
