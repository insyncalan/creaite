// @ts-check
/* rowKeys (#302 C): the minutes' keyboard. Nothing on screen advertises it (Alan, 22-10-2026: no review-mode bar).
   J and K move from row to row (the rows shown, so a pressed attention chip is respected); then Y sets Tracked, M Minutes only,
   N Dropped (one key drops, nothing asked), E edits the row's words, S shows its source in the transcript, Z undoes the last Track choice (key or click). Never while typing in a field, never with a menu, list or dialog open, never with a modifier held, and not at all
   when Settings › Look and help has single-key shortcuts off (core/keys.js sees to that first). Until J or K has chosen a row,
   no key here is taken, so E and S stay the page keys they are everywhere else. The choices are the Track control's own
   (track.js setTrack), so counts, the strip and the Approve label follow as they do for a click. */
import { signal } from "@preact/signals";
import { setTrack, trackOf, trackRows } from "./track.js";
import { jumpTo } from "./TranscriptPane.jsx";
import { popupOpen, typing } from "../../core/keys.js";
import { snack } from "../../core/server.js";
import { shared } from "../../core/state.js";

/** @typedef {import("../report/Sheet.jsx").SheetDoc} SheetDoc */
/** @typedef {{doc: () => SheetDoc|null, plan: () => any[]|null, setDoc: (d: SheetDoc, why: string) => void}} RowKeyApi */

/** The row (its item number) the keys act on, or null. */
export const keyRow = signal(/** @type {number|null} */ (null));
/** The last key choices: the row and what the layout held for it before (undefined = nothing chosen). @type {{n: number, was: string|undefined}[]} */
const UNDO = [];
/** Note row n's choice before it changes, so Z can put it back (the keys and the Track control's clicks share one stack). @param {SheetDoc} doc @param {number} n */
export const rememberTrack = (doc, n) => { UNDO.push({ n, was: ((doc.layout || {}).track || {})[String(n)] }); };
export const rowKeysReset = () => { keyRow.value = null; UNDO.length = 0; };

/** The item numbers of the rows on screen, in page order. */
export const shownRows = () => [...document.querySelectorAll("#v-minutes tr.mi:not([hidden])")].map(r => Number(/** @type {HTMLElement} */ (r).dataset.n));

/** Move the cursor one row (or to the first or last when none is chosen). @param {1|-1} d */
export function moveRow(d) {
  const list = shownRows();
  if (!list.length) return;
  const at = keyRow.value == null ? -1 : list.indexOf(keyRow.value);
  const n = at < 0 ? (d === 1 ? list[0] : list[list.length - 1]) : list[Math.max(0, Math.min(list.length - 1, at + d))];
  keyRow.value = n;
  requestAnimationFrame(() => {
    const row = /** @type {HTMLElement|null} */ (document.querySelector(`#v-minutes tr.mi[data-n='${n}']`));
    if (row) { row.focus({ preventScroll: true }); row.scrollIntoView({ block: "nearest", behavior: "smooth" }); }
  });
}

/** Whether the keys apply on this page now. */
const active = () => shared.VIEW === "minutes" && !typing() && !popupOpen();

/** One keydown. Returns true when the key was taken. @param {KeyboardEvent} e @param {RowKeyApi} api */
export function rowKey(e, api) {
  if (e.metaKey || e.ctrlKey || e.altKey || e.shiftKey || e.isComposing || !e.key || e.key.length !== 1 || !active()) return false;
  const doc = api.doc();
  if (!doc || doc.state !== "draft") return false;
  const k = e.key.toLowerCase();
  if (k === "j" || k === "k") { moveRow(k === "j" ? 1 : -1); return true; }
  const n = keyRow.value;
  if (k === "z") {
    const u = UNDO.pop();
    if (!u) return false;
    const track = { ...(((doc.layout || {}).track) || {}) };
    if (u.was === undefined) delete track[String(u.n)]; else track[String(u.n)] = u.was;
    api.setDoc({ ...doc, layout: { ...(doc.layout || {}), track } }, "Track");
    keyRow.value = u.n;
    return true;
  }
  if (n == null || !"ymnes".includes(k)) return false;
  const r = trackRows(doc).find(x => x.n === n);
  if (!r) return false;
  if (k === "e") {
    const box = /** @type {HTMLElement|null} */ (document.querySelector(`#v-minutes tr.mi[data-n='${n}'] .mnit [contenteditable='true']`));
    if (box) box.focus();
    return true;
  }
  if (k === "s") {
    const turn = r.row && r.row.at && r.row.at.turn ? Number(r.row.at.turn) : null;
    if (turn) jumpTo(turn); else snack("This line has no place in the transcript");
    return true;
  }
  const want = k === "y" ? "y" : k === "n" ? "n" : "";
  if (trackOf(doc, r, api.plan()) === want) return true;
  rememberTrack(doc, n);
  api.setDoc(setTrack(doc, n, want), "Track");
  return true;
}

let installed = false;
/** Listen once for the keys, ahead of the page's own (capture), taking a key only when rowKey does. @param {RowKeyApi} api */
export function installRowKeys(api) {
  if (installed) return;
  installed = true;
  document.addEventListener("keydown", e => { if (rowKey(e, api)) { e.preventDefault(); e.stopPropagation(); } }, true);
}
