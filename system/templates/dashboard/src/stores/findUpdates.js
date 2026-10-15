// @ts-check
/* stores/findUpdates.js (BL-301 E, dev/COMPONENTS.md §2): Find updates, from a note to the tracker. The panel beside a note
   (components/notes/FindUpdates.jsx) reads these signals; the functions here are the only way they change.

   Find runs Claude through the run engine (/api/notes/find, streamed like /api/draft: progress, Stop, one run at a time) on the
   note's new or changed lines; the server checks every row by plain code (staging checks, the schema, the bulk rule, hedged lines)
   and the panel shows them grouped, ticked or not. Ticking a row is the approval: Apply sends the ticked rows to /api/notes/apply,
   which stages them approved (source_run "note") and applies them as one apply; Undo in the snackbar reverses all of it
   (/api/notes/undo). Save for later sends them to Review instead. Unticked rows are never staged. Nothing is ever applied on its own:
   only Alan's Apply. */
import { signal, computed } from "@preact/signals";
import { api, oneLine, reloadData, snack, viaServer, writeProposal } from "../core/server.js";
import { draftAsk } from "../drafts.js";
import { noteSetSent } from "./notes.js";

/** @typedef {{t: string, tone?: string, tip?: string}} FuFlag */
/** @typedef {{f: string, label: string, from: string, to: string}} FuChange */
/** @typedef {{f: string, label: string, kind: string, options?: string[] | null, part: string}} FuField */
/** One row: a change a line of the note gave.
    @typedef {{key: string, p: number, fp: string, kind: string, group: string, type: string, text: string, tick: boolean,
      lock?: string | null, invalid?: string, flags: FuFlag[], notes: string[], change?: FuChange[], fields: FuField[], item: any}} FuRow */
/** @typedef {{p: number, why: string}} FuLeft */

/** The note the panel is for (its stored path), or "". */
export const fuPath = signal("");
/** "idle" | "ask" (a confidential note: ask first) | "busy" | "ready" | "none" (nothing new) | "error" | "done" (all applied) */
export const fuState = signal("idle");
export const fuMsg = signal("");
export const fuSteps = signal(0);
/** @type {import("@preact/signals").Signal<FuRow[]>} */
export const fuRows = signal([]);
export const fuQuiet = signal(0);
/** The row being edited (its key), or "". */
export const fuOpen = signal("");
/** The note line hovered, from either side (0: none). */
export const fuHover = signal(0);
/** "apply" | "later" while saving, else "". */
export const fuSaving = signal("");
/** The last apply, for Undo: {apply_id, rows}. @type {import("@preact/signals").Signal<{apply_id: number, rows: FuRow[]} | null>} */
export const fuLast = signal(null);
/** Confidential notes Alan has already said yes to, this session (BL-301: it asks once). */
const ASKED = new Set();

/** The lines that gave a change, in note order, numbered from 1: {p: marker}. */
export const fuMarkers = computed(() => {
  const ps = [...new Set(fuRows.value.map(r => r.p))].sort((a, b) => a - b);
  return Object.fromEntries(ps.map((p, i) => [p, i + 1]));
});
export const fuTicked = computed(() => fuRows.value.filter(r => r.tick && !r.lock));

/** Start over for a note (the panel opened, or a different note). @param {string} path */
export function fuReset(path) {
  fuPath.value = path; fuState.value = "idle"; fuMsg.value = ""; fuSteps.value = 0; fuRows.value = []; fuQuiet.value = 0;
  fuOpen.value = ""; fuHover.value = 0; fuSaving.value = ""; fuLast.value = null;
}

/** Find updates on the note: its new or changed lines (or line `p` only). @param {{p?: number, confirm?: boolean}} [o] */
export async function fuFind(o = {}) {
  const path = fuPath.value;
  if (!path || fuState.value === "busy") return;
  if (!viaServer()) { fuState.value = "error"; fuMsg.value = "Find updates needs the live server."; return; }
  const confirm = !!o.confirm || ASKED.has(path);
  fuState.value = "busy"; fuSteps.value = 0; fuMsg.value = ""; fuOpen.value = "";
  const body = { path, ...(o.p ? { p: o.p } : {}), ...(confirm ? { confirm: true } : {}) };
  const r = /** @type {any} */ (await draftAsk(body, { url: "/api/notes/find", label: "Finding updates in the note", status: () => {},
    onStep: (/** @type {number} */ n) => { fuSteps.value = n; } }));
  if (path !== fuPath.value) return;                         /* another note was opened meanwhile */
  if (r && r.confidential && !Array.isArray(r.items)) { fuState.value = "ask"; fuMsg.value = r.message || ""; return; }
  if (confirm) ASKED.add(path);
  if (r && r.nothing) { fuState.value = "none"; fuMsg.value = r.nothing; fuRows.value = []; return; }
  if (!r || !r.ok || !Array.isArray(r.items)) { fuState.value = "error"; fuMsg.value = oneLine((r && r.message) || "") || "No updates came back."; return; }
  fuRows.value = r.items.map(x => ({ ...x, notes: x.notes || [], flags: x.flags || [], fields: x.fields || [] }));
  fuQuiet.value = r.quiet || 0;
  fuState.value = r.items.length ? "ready" : "none";
  if (!r.items.length) fuMsg.value = "Nothing in the new lines to turn into tracker changes. That's fine: not every line needs to be an item.";
}

/** A confidential note: Alan said yes, once. */
export function fuConfirm() { ASKED.add(fuPath.value); return fuFind({ confirm: true }); }

/** Tick or untick one row (a locked row stays as it is). @param {string} key @param {boolean} on */
export function fuTick(key, on) {
  fuRows.value = fuRows.value.map(r => r.key === key && !r.lock ? { ...r, tick: on } : r);
}

/** Change one field of a row before it is applied: the item's values or changes, a person or a memory line. The row's text follows.
    @param {string} key @param {FuField} field @param {string} v */
export function fuEdit(key, field, v) {
  fuRows.value = fuRows.value.map(r => {
    if (r.key !== key) return r;
    const item = JSON.parse(JSON.stringify(r.item));
    if (!["person", "memory"].includes(field.part) && !item[field.part]) item[field.part] = {};
    const part = field.part === "person" ? item.person : field.part === "memory" ? item.memory : item[field.part];
    if (v === "") delete part[field.f]; else part[field.f] = v;
    const nr = { ...r, item, invalid: undefined, lock: r.lock === "invalid" ? null : r.lock, edited: true };
    if (field.part === "values" && ["description", "decision"].includes(field.f)) nr.text = v;
    if (field.part === "memory") nr.text = `“${v}”`;
    if (field.part === "person") nr.text = [item.person.name, item.person.role, item.person.org].filter(Boolean).join(" · ");
    if (field.part === "changes" && r.change) nr.change = r.change.map(c => c.f === field.f ? { ...c, to: shownDay(v, field.kind) } : c);
    return nr;
  });
}

/** @param {string} v @param {string} kind */
const shownDay = (v, kind) => kind === "date" && /^\d{4}-\d{2}-\d{2}$/.test(v) ? `${v.slice(8, 10)}-${v.slice(5, 7)}-${v.slice(0, 4)}` : v;

/** Rows the server refused: each says why and is unticked. @param {Record<string, string>} problems */
function fuRefused(problems) {
  fuRows.value = fuRows.value.map(r => problems[r.key] ? { ...r, invalid: problems[r.key], tick: false } : r);
}

/** Apply the ticked rows (one apply, Undo in the snackbar), or save them for later (Review). Without the live server Apply saves
    them for Review through the vault folder instead, and says so. @param {"apply" | "later"} mode */
export async function fuApply(mode) {
  const picked = fuTicked.value, path = fuPath.value;
  if (!picked.length || fuSaving.value) return;
  if (!viaServer()) {
    try {
      await writeProposal(picked.filter(r => r.item && r.item.op).map(r => ({ ...r.item, decision: "pending" })), { source_run: "note", files: [path] });
      snack("The live server isn't running: saved for Review instead");
      fuDrop(picked);
    } catch (e) { snack("Not saved: " + oneLine(String(e && e.message || e))); }
    return;
  }
  fuSaving.value = mode;
  const r = await api("/api/notes/apply", { path, mode, rows: picked.map(x => ({ key: x.key, fp: x.fp, item: x.item })) });
  fuSaving.value = "";
  if (!r.ok) {
    if (r.problems) fuRefused(r.problems);
    snack(oneLine(r.message) || (mode === "apply" ? "Nothing applied" : "Nothing saved"));
    return;
  }
  fuDrop(picked);
  if (mode === "later") { snack(oneLine(r.message)); return; }
  fuLast.value = { apply_id: r.apply_id, rows: picked };
  noteSetSent(path, r.sent);                       /* BL-301 B: the lines just sent get their margin tick */
  await reloadData();
  snack(oneLine(r.message), () => fuUndo(), "Undo");
}

/** The applied or saved rows leave the panel; when none is left it says so. @param {FuRow[]} gone */
function fuDrop(gone) {
  const keys = new Set(gone.map(r => r.key));
  fuRows.value = fuRows.value.filter(r => !keys.has(r.key));
  fuOpen.value = "";
  if (!fuRows.value.length) { fuState.value = "done"; fuMsg.value = `${gone.length} change${gone.length === 1 ? "" : "s"} done. Run Find updates again after you add to the note.`; }
}

/** Undo the last apply: all of it; its rows come back to the panel and its lines count as new again. */
export async function fuUndo() {
  const last = fuLast.value;
  if (!last) return;
  const path = fuPath.value, r = await api("/api/notes/undo", { path, apply_id: last.apply_id });
  noteSetSent(path, r.sent);                       /* their ticks go: the lines count as new again */
  await reloadData();
  if (!r.ok) { snack(oneLine(r.message) || "Not undone"); return; }
  fuLast.value = null;
  const keys = new Set(fuRows.value.map(x => x.key));
  fuRows.value = [...fuRows.value, ...last.rows.filter(x => !keys.has(x.key))];
  fuState.value = "ready";
  snack("Undone");
}
