// @ts-check
/* core/instant.js (BL-304, v1.9.4): changes appear at once, and only what changed is fetched again.

   - An edit (the peek, a Work cell, the board, ⌘K, a bulk change) changes the in-memory record and the screen first, marked as
     saving (a hollow dot on its row); it is then staged and applied in the background through the same staging and apply path
     as before (writeProposal, /api/apply, tracker.py's checks, the bulk rule, the log and Undo, all unchanged).
   - INFLIGHT holds each change still saving as an overlay ({k, id, f}); fresh data from the server (a targeted refresh, a full
     reload, a live update from elsewhere) is laid down first and the overlays on top, so nothing in flight is ever clobbered.
   - SAVEQ runs the background saves one at a time, in the order they were made: two quick edits to one item are applied in
     that order, each its own apply with its own Undo; a later one rebases on the record the earlier one left.
   - recordsRefresh(ids) fetches just those items (GET /api/records) with Review, Activity and the latest apply, merges them
     into the store (A, R, DEC keep their objects) and redraws; it never calls /api/data. A full reload (reloadData) stays the
     fallback: on start, after a server restart, when the live-updates stream has a gap or names more than items, and from
     Settings › Diagnostics. */
import { A, DEC, open, P, R, REV, snapModelKeys } from "./data.js";
import { D, fdText, prio } from "./page.js";
import { shared } from "./state.js";
import { REC } from "../panel.js";
import { PULSE, pulseGet, refreshAll } from "./server.js";

/** @typedef {{k:string, id:string, f:Record<string, any>}} Overlay */
/** @type {Map<string, Overlay[]>} "k|id" → the changes to that item still saving, oldest first */
export const INFLIGHT = new Map();
export const RECORD_KINDS = ["actions", "raid", "decisions"];
export const ovKey = (k, id) => k + "|" + id;
/** @param {Overlay[]} recs */
export function ovAdd(recs) { for (const r of recs || []) { const key = ovKey(r.k, r.id); if (!INFLIGHT.has(key)) INFLIGHT.set(key, []); INFLIGHT.get(key)?.push(r); } }
/** @param {Overlay[]} recs */
export function ovDrop(recs) { for (const r of recs || []) { const key = ovKey(r.k, r.id), L = INFLIGHT.get(key); if (!L) continue; const i = L.indexOf(r); if (i >= 0) L.splice(i, 1); if (!L.length) INFLIGHT.delete(key); } }
/** whether another change to any of these items is still saving */
export const ovBusy = recs => (recs || []).some(r => INFLIGHT.has(ovKey(r.k, r.id)));
/** the IDs with a change still saving (the hollow dot) */
export const savingIds = () => new Set([...INFLIGHT.values()].flat().map(o => o.id));
/* fresh data first, then what is staged in the peek (oldest), then what is still saving (newest) on top */
export function ovReapply() {
  for (const s of shared.PKS || []) { if (!RECORD_KINDS.includes(s.k) || !s.patch) continue; const x = REC(s.k, s.id); if (x) { Object.assign(x, s.patch); if (s.k === "raid") x.pr = prio(x.imp, x.lik); } }
  for (const L of INFLIGHT.values()) for (const o of L) { const x = REC(o.k, o.id); if (!x) continue; Object.assign(x, o.f); if (o.k === "raid") x.pr = prio(x.imp, x.lik); } }

/* the background saves, one at a time in the order made */
/** @type {Promise<any>} */
export let SAVEQ = Promise.resolve();
/** @template T @param {() => Promise<T>} fn @returns {Promise<T>} */
export function saveQueue(fn) { const run = SAVEQ.then(fn, fn); SAVEQ = run.catch(() => {}); return run; }
/** resolves when every background save made so far has finished (tests, and ⌘↵'s apply) */
export async function savesSettled() { let q; do { q = SAVEQ; await q; } while (q !== SAVEQ); }

/* ---- targeted refresh ---- */
const TEXT = ["t", "upd", "resp", "cm", "cmd", "reason"];
/** one item from /api/records, made as reloadData makes it (dates in text shown DD-MM-YYYY; RAID priority recalculated) */
export function recNorm(t, o) { TEXT.forEach(k => { if (typeof o[k] === "string") o[k] = fdText(o[k]); }); if (t === "raid") o.pr = prio(o.imp, o.lik); return o; }
/** merge /api/records' answer into the store: the items in place (same objects), Review, Activity and the apply's time */
export function recMerge(n) {
  const T = { actions: A, raid: R, decisions: DEC };
  for (const t of RECORD_KINDS) for (const got of (n.records && n.records[t]) || []) {
    const arr = T[t], x = arr.find(o => o.id === got.id); recNorm(t, got);
    if (x) { Object.keys(x).forEach(c => { if (!(c in got)) delete x[c]; }); Object.assign(x, got); } else arr.push(got); }
  for (const id of n.missing || []) for (const t of RECORD_KINDS) { const arr = T[t], i = arr.findIndex(o => o.id === id); if (i >= 0) arr.splice(i, 1); }
  for (const k of ["review_focus", "peek_staged", "activity_capped", "activity_older", "milestone_names", "latest_apply"]) if (k in n) D[k] = n[k];
  if (Array.isArray(n.review)) { snapModelKeys(false); REV.splice(0, REV.length, ...n.review); D.review = REV; }
  if (Array.isArray(n.activity)) { shared.ACT = n.activity; shared.ACT.forEach(a => a.what = fdText(a.what)); }
  if (n.data_at) shared.DATA_AT = n.data_at;
  ovReapply(); undatedRecount(); }
/** each project's count of open work with no date (BL-95), again from the store: /api/records names items, not projects.
    Mirrors build_dashboard.undated_counts, as the page's undatedWork does. */
export function undatedRecount() {
  for (const p of P) { if (!p || !p.undated) continue;
    const a = A.filter(x => x.p === p.code && open(x) && !x.due).length;
    const r = R.filter(x => x.p === p.code && x.st === "Open" && !x.due && (x.type === "Risk" || x.type === "Issue" || x.resp)).length;
    p.undated = { actions: a, raid: r, total: a + r }; } }
/** counts for tests: how often each way of refreshing ran */
export const RECSTAT = { records: 0, full: 0 };
/** fetch just these items (and Review, Activity) and redraw; false when the server couldn't answer (the caller reloads all).
    o.aged (BL-10): an item archived for its age is fetched too, for search to open it */
export async function recordsRefresh(ids, o = {}) {
  const list = [...new Set(ids || [])].filter(Boolean);
  if (list.length > 200) return false;
  PULSE.reloads++; let n = null;
  try {
    try { const r = await fetch("/api/records?ids=" + encodeURIComponent(list.join(",")) + (o.aged ? "&aged=1" : ""), { headers: { "X-Creaite-Token": D.token || "" }, cache: "no-store" });
      if (r.ok) n = await r.json(); } catch (e) { n = null; }
    if (!n || !n.ok) return false;
    const hold = o.hold ? o.hold() : null;   /* gate-fix-2: held once the answer is in, so a selection made while it was in flight is kept */
    RECSTAT.records++; recMerge(n); refreshAll(); if (o.restore) o.restore(hold);
    if (PULSE.v != null && !PULSE.busy) { const r = await pulseGet(); if (r && !PULSE.stale) { PULSE.v = r.v; PULSE.pending = r.pending; } }   /* BL-110: his own change doesn't cause a second reload */
  } finally { PULSE.reloads--; }
  if (o.after) await o.after();
  return true; }
