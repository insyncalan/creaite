// @ts-check
/* stores/prepShape.js (BL-286 part C, BL-256): Shape the meeting, inside the Prep popup. Alan writes the focus and the aim in
   his own words; Shape runs Claude read-only through the run engine (/api/prep/shape, streamed like /api/draft: progress,
   Stop, one run at a time); the reply says how creaite read the instruction (the focus, the aim, focus only or focus first),
   which Alan can change, and drafts the notes (Objective, Talking points, Ask, Carried over), every line cited. What's in
   focus comes from /api/prep/filter. Accept saves the instruction, the reading, the notes and what was ticked out in
   system/staging/prep-focus.json (/api/prep/focus/save, the server's own write, in the format prep_shape.py defines, which the
   prep page's focus band reads too). Nothing reaches the tracker and nothing is sent.
   Regenerate sends the boxes' text with creaite's last draft, so the server keeps every section Alan edited (per section). */
import { signal } from "@preact/signals";
import { api, oneLine, snack, viaServer } from "../core/server.js";
import { draftAsk, DRAFTFEATURES, draftStat } from "../drafts.js";
import { DRAFTKIND } from "../projects.js";

/** At load (src/main.js, after the agenda's): the switch in Settings › General › AI drafts (drafts.py FEATURES "shape"), and the
    kind. */
export function bootPrepShape() {
  DRAFTFEATURES.push(["shape", "Shape the meeting", "Prep: reads your focus and aim, then drafts the objective, talking points, ask and what's carried over, each line cited"]);
  Object.assign(DRAFTKIND, { shape: "shape" });
}

export const SHAPE_SECTIONS = /** @type {[string, string][]} */ ([["objective", "Objective"], ["talking_points", "Talking points"],
  ["ask", "Ask"], ["carried_over", "Carried over"]]);

/** @typedef {{type: string, id?: string, kind?: string, path?: string, label?: string, url?: string, section?: string}} Typed */
/** @typedef {{text: string, sources?: Typed[]}} NoteLine */
/** @typedef {Record<string, NoteLine[]>} Notes */
/** @typedef {{focus: {id?: string, text: string}[], aim: string, show: string}} Reading */
/** @typedef {{kind: string, id: string | null, label: string, why: string, insert: string}} ShapeChip */
/** @typedef {{level: string, section: string, note: string}} Check */
/** @typedef {{id: string, table: string, p: string, text: string, owner: string, due: string, status: string, type: string,
    why: string[], in_focus: boolean, excluded: boolean}} FilterItem */
/** @typedef {{path: string, name: string, why: string[], excluded: boolean}} FilterDoc */
/** @typedef {{items: FilterItem[], documents: FilterDoc[], n: number, N: number, docs_n: number, docs_N: number}} Filter */

/** The meeting being shaped (the Prep brief's key), or null when the popup shows the brief. */
export const shapeKey = signal(/** @type {string | null} */ (null));
export const shapeInstruction = signal("");
export const shapeChips = signal(/** @type {ShapeChip[]} */ ([]));
/** The chips already added to the text, by label (they leave the row). */
export const shapeUsed = signal(/** @type {string[]} */ ([]));
export const shapeConfidential = signal(false);
/** How creaite read the instruction (from the reply, or as Alan changed it). */
export const shapeReading = signal(/** @type {Reading | null} */ (null));
/** True once Alan has changed the reading: Regenerate then sends it. */
export const shapeReadingMine = signal(false);
/** The boxes' text, one line each, per section. */
export const shapeText = signal(/** @type {Record<string, string>} */ ({}));
/** The notes as last drafted or loaded, with their citations (the boxes' lines keep them, shapeLinesFrom). */
export const shapeNotes = signal(/** @type {Notes | null} */ (null));
/** creaite's own last draft: a section whose text differs from it is Alan's, and Regenerate keeps it. */
export const shapeDrafted = signal(/** @type {Notes | null} */ (null));
export const shapeChecks = signal(/** @type {Check[]} */ ([]));
export const shapeFilter = signal(/** @type {Filter | null} */ (null));
export const shapeExcluded = signal(/** @type {string[]} */ ([]));
/** "" when idle; else what is running: "shape" (with its steps) or "save". */
export const shapeBusy = signal("");
export const shapeSteps = signal(0);
export const shapeSourcesN = signal(0);
/** The last message from a run that didn't give a draft, or "". */
export const shapeMsg = signal("");
/** When the notes were accepted ("YYYY-MM-DD HH:MM"), or "". */
export const shapeAccepted = signal("");

const emptyNotes = () => /** @type {Notes} */ (Object.fromEntries(SHAPE_SECTIONS.map(([k]) => [k, []])));
/** @param {NoteLine[] | undefined} lines */
const textOf = lines => (lines || []).map(l => l.text).join("\n");

/** A section's lines from the text in its box, one line each; a line that is unchanged keeps its citations, an edited one
    keeps those of the line it replaced (the prep page's focus band does the same).
    @param {string} text @param {NoteLine[]} before @returns {NoteLine[]} */
export function shapeLinesFrom(text, before) {
  const old = before || [];
  return String(text || "").split("\n").map(s => s.trim()).filter(Boolean).slice(0, 12).map((t, i) => {
    const same = old.find(x => x.text === t) || old[i];
    return { text: t.slice(0, 600), sources: (same && same.sources) || [] };
  });
}

/** The notes as they are in the boxes now. @returns {Notes} */
export function notesNow() {
  const n = shapeNotes.value || emptyNotes(), t = shapeText.value;
  return /** @type {Notes} */ (Object.fromEntries(SHAPE_SECTIONS.map(([k]) => [k, k in t ? shapeLinesFrom(t[k], n[k]) : (n[k] || [])])));
}

/** The sections Alan has changed from creaite's last draft (Regenerate keeps them). */
export function editedSections() {
  const d = shapeDrafted.value;
  if (!d) return [];
  const now = notesNow(), flat = (/** @type {NoteLine[]} */ L) => L.map(l => l.text.replace(/\s+/g, " ").trim()).join("\n");
  return SHAPE_SECTIONS.map(([k]) => k).filter(k => flat(now[k] || []) !== flat(d[k] || []));
}

/** The item IDs in the reading's focus. */
export const focusIds = () => ((shapeReading.value || { focus: [] }).focus || []).map(f => f.id || "").filter(Boolean);

/** Put a record or a draft's notes into the boxes. @param {Notes | null | undefined} notes */
function fill(notes) {
  const n = { ...emptyNotes(), ...(notes || {}) };
  shapeNotes.value = n;
  shapeText.value = Object.fromEntries(SHAPE_SECTIONS.map(([k]) => [k, textOf(n[k])]));
}

let shapeAsked = 0;
/** Open shaping for a meeting: its chips, and what was accepted before (the instruction, the reading, the notes, what was
    ticked out), so Change focus starts from there. Kept while the same meeting stays open.
    @param {string} key */
export async function openShape(key) {
  const mine = ++shapeAsked;
  if (shapeKey.value !== key) {
    shapeKey.value = key;
    shapeInstruction.value = ""; shapeChips.value = []; shapeUsed.value = []; shapeConfidential.value = false;
    shapeReading.value = null; shapeReadingMine.value = false; shapeText.value = {}; shapeNotes.value = null;
    shapeDrafted.value = null; shapeChecks.value = []; shapeFilter.value = null; shapeExcluded.value = []; shapeMsg.value = "";
    shapeAccepted.value = ""; shapeSteps.value = 0; shapeSourcesN.value = 0;
  } else shapeKey.value = key;
  if (!viaServer()) return;
  const [c, f] = await Promise.all([api("/api/prep/chips", { key }).catch(() => null), api("/api/prep/focus", { key }).catch(() => null)]);
  if (mine !== shapeAsked || shapeKey.value !== key) return;
  if (c && c.ok) { shapeChips.value = c.chips || []; shapeConfidential.value = !!c.confidential; }
  const rec = f && f.ok && f.focus;
  if (rec && !shapeNotes.value) {
    shapeInstruction.value = rec.instruction || "";
    shapeReading.value = rec.reading || null;
    shapeDrafted.value = rec.drafted || null;
    shapeExcluded.value = rec.excluded || [];
    shapeAccepted.value = rec.accepted_at || "";
    fill(rec.notes);
    previewFilter();
  }
}

/** Back to the brief (what was typed is kept for this meeting). */
export function closeShape() { shapeKey.value = null; }

/** A chip adds its item to the instruction and leaves the row. @param {ShapeChip} c */
export function addChip(c) {
  const t = shapeInstruction.value.replace(/\s+$/, "");
  shapeInstruction.value = `${t}${t ? "\n" : ""}Also cover ${c.insert}.`;
  shapeUsed.value = [...shapeUsed.value, c.label];
}

let filtering = 0;
/** What's in focus for the reading on screen (or the accepted one): the server's focus filter, with what is ticked out. */
export async function previewFilter() {
  const key = shapeKey.value;
  if (!key || !viaServer()) return;
  const mine = ++filtering, ids = focusIds();
  const r = await api("/api/prep/filter", { key, focus: ids, excluded: shapeExcluded.value }).catch(() => null);
  if (mine === filtering && key === shapeKey.value && r && r.ok) shapeFilter.value = r.filter;
}

/** Tick an item or a document in or out of focus. @param {string} id */
export function toggleExcluded(id) {
  const s = new Set(shapeExcluded.value);
  if (s.has(id)) s.delete(id); else s.add(id);
  shapeExcluded.value = [...s];
  const f = shapeFilter.value;
  if (f) {
    const its = f.items.map(i => i.id === id ? { ...i, excluded: s.has(id) } : i);
    const documents = f.documents.map(d => d.path === id ? { ...d, excluded: s.has(id) } : d);
    shapeFilter.value = { ...f, items: its, documents, n: its.filter(i => !i.excluded).length, docs_n: documents.filter(d => !d.excluded).length };
  }
}

/** Alan corrects the reading (change): Regenerate sends it, and What's in focus follows. @param {Reading} r */
export function setReading(r) {
  shapeReading.value = r;
  shapeReadingMine.value = true;
  previewFilter();
}

/** Give a section back to creaite: its text returns to the last draft, so Regenerate redrafts it. @param {string} sec */
export function giveBack(sec) {
  const d = shapeDrafted.value;
  if (!d) return;
  shapeText.value = { ...shapeText.value, [sec]: textOf(d[sec]) };
}

/** Shape (or Regenerate): run the draft through the run engine. The boxes' text and creaite's last draft go with it, so the
    sections Alan edited are kept; a reading he changed goes too. */
export async function runShape() {
  const key = shapeKey.value;
  if (!key || shapeBusy.value) return;
  const instruction = shapeInstruction.value.trim();
  if (!instruction) { shapeMsg.value = "Write the focus and the aim first."; return; }
  /** @type {Record<string, any>} */
  const body = { key, instruction };
  if (shapeReadingMine.value && shapeReading.value) body.reading = shapeReading.value;
  if (shapeDrafted.value) body.current = { notes: notesNow(), drafted: shapeDrafted.value };
  shapeBusy.value = "shape"; shapeSteps.value = 0; shapeMsg.value = "";
  let r;
  try {
    r = await draftAsk(body, { url: "/api/prep/shape", label: "Shaping the meeting", status: () => {},
      onStep: (/** @type {number} */ n) => { shapeSteps.value = n; },
      onSources: (/** @type {any} */ ev) => { shapeSourcesN.value = (ev.sources || []).length; shapeConfidential.value = !!ev.confidential; } });
  } finally { shapeBusy.value = ""; }
  if (key !== shapeKey.value) return;
  if (!r || !r.ok || !r.reading) { shapeMsg.value = oneLine((r && (r.nothing || r.message)) || "") || "No draft came back"; return; }
  shapeReading.value = r.reading;
  shapeReadingMine.value = false;
  shapeDrafted.value = r.drafted || emptyNotes();
  shapeChecks.value = r.checks || [];
  shapeConfidential.value = !!r.confidential;
  fill(r.notes);
  previewFilter();
}

/** Accept: the instruction, the reading, the notes (as in the boxes), creaite's draft and what was ticked out, saved for this
    meeting in prep-focus.json. Counted in draft-stats.json as used or edited by the server. */
export async function acceptShape() {
  const key = shapeKey.value;
  if (!key || shapeBusy.value || !shapeReading.value) return false;
  if (!viaServer()) { snack("Saving needs the live server"); return false; }
  shapeBusy.value = "save";
  const r = await api("/api/prep/focus/save", { key, accept: true, instruction: shapeInstruction.value, reading: shapeReading.value,
    notes: notesNow(), drafted: shapeDrafted.value || emptyNotes(), excluded: shapeExcluded.value }).catch(() => null);
  shapeBusy.value = "";
  if (!r || !r.ok) { snack(oneLine((r && r.message) || "") || "Not saved"); return false; }
  shapeAccepted.value = (r.focus && r.focus.accepted_at) || "";
  snack(r.page ? "Accepted: on the prep page, and the Agendas page was updated" : "Accepted: the notes are on the prep page");
  return true;
}

/** Discard the draft: the boxes empty, and the rejection is counted. */
export function discardShape() {
  if (shapeDrafted.value) draftStat("shape", "rejected");
  shapeNotes.value = null; shapeDrafted.value = null; shapeText.value = {}; shapeChecks.value = []; shapeReading.value = null;
  shapeReadingMine.value = false; shapeFilter.value = null; shapeAccepted.value = "";
}
