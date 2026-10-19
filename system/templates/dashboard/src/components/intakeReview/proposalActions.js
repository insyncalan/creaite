// @ts-check
/* Intake and Review's proposal actions (#232-B, v2.5.0): what a proposal row's buttons and keys do. Every decision goes through the
   Review page's own flows (review.js: decide, rvDecideMany, rjMenuFor), so the checks, the draft counts, the reasons and the
   one-apply, one-Undo batch are the same ones; this file only wires them to the new rows.
   - approve(n), reject(n, anchor), edit(n)       one row's buttons
   - approveRoutine(ns)                           the routine group's button: one apply, one Undo, never the first group
   - openPeek(n)                                  the right-hand panel on a proposal, previous and next through the rows on the page
   - bootProposalKeys()                           the arrow keys and the row keys (A approve, R reject, E edit, Enter peek) */
import { $ } from "../../core/dom.js";
import { reviewViaServer, snack } from "../../core/server.js";
import { shared } from "../../core/state.js";
import { draftWhyNot } from "../../drafts.js";
import { openProposal } from "../../panel.js";
import { decide, rjMenuFor, rvBulkOK, rvDecideMany, rvRejectOK } from "../../review.js";
import { boardAsk } from "../../work.js";
import { irPeek, irRow, irSel, irTick } from "../../stores/intakeReview.js";

const redraw = () => { irTick.value++; };

/** @param {number} n */
export async function approve(n) { await decide(n, "approved"); redraw(); }

/** The reasons menu (or a plain reject for minutes, reports and file changes). @param {number} n @param {Element|null} anchor */
export function reject(n, anchor) {
  const r = irRow(n); if (!r || r.done) return;
  if (rvRejectOK(r)) rjMenuFor([r], /** @type {any} */ (anchor), redraw); else decide(n, "rejected").then(redraw);
}

/** Keep current / Use this one on a conflict. @param {number} n @param {"keep"|"override"} how */
export async function settle(n, how) { const r = irRow(n); if (r && !r.done) { await reviewViaServer(r, how, []); redraw(); } }

/** Draft a response on a new risk: the peek opens and asks. @param {number} n */
export function draftResponse(n) {
  const why = draftWhyNot("thinking"); if (why) { snack(why); return; }
  openPeek(n);
  setTimeout(() => { const t = /** @type {HTMLElement|null} */ ($('#pkDescDr [data-draft="thinking"][data-drf="resp"]')); if (t) t.click(); }, 0);
}

/** The pencil: the peek for an item, the minutes view or Word for minutes. @param {number} n */
export function edit(n) { const r = irRow(n); if (!r || r.done) return; if (["draft", "files"].includes(r.kind)) openProposal(n); else openPeek(n); }

/** What "Approve routine (n)" approves: the group's rows that are still routine now, nothing else. @param {number[]} ns */
export async function approveRoutine(ns) {
  const rows = ns.map(irRow).filter(r => r && !r.done && rvBulkOK(r));
  if (!rows.length) { snack("Nothing routine to approve"); return; }
  if (rows.length > shared.RV_MAX && !await boardAsk({ title: `Approve ${rows.length} routine proposals?`, hint: "Applied at once; Undo reverses the batch", clear: true, okText: `Approve ${rows.length}` })) return;
  const res = await rvDecideMany(rows, "approved");
  redraw();
  const text = `Approved ${res.n}${res.failed && res.failed.length ? ` · not saved: ${res.failed.join(", ")}` : ""}`;
  if (res.undo) { const undo = res.undo; snack(text, async () => { await undo(); redraw(); }); } else snack(text);
}

/** The proposals on the page now, in the order they are drawn (the peek's previous and next follow it). */
const shownNs = () => /** @type {HTMLElement[]} */ ([...document.querySelectorAll("#v-intake-review tr.irprop[data-irn]")]).map(t => +(t.dataset.irn || 0));
/** The ones the peek can show (an action, a risk, an issue, a decision or an update). */
const peekable = (/** @type {number} */ n) => { const r = irRow(n); return !!r && !r.done && !["draft", "files"].includes(r.kind); };

/** Open the peek on proposal n; Previous and Next walk the peekable rows as drawn. @param {number} n */
export function openPeek(n) {
  const r = irRow(n); if (!r || r.done) return;
  shared.PKSRC = {
    view: "intake-review",
    order: () => shownNs().filter(peekable).map(x => ({ id: `rv${x}`, k: "proposal" })),
    step: (/** @type {{id: string}} */ o) => { const m = +o.id.slice(2); openProposal(m); irPeek.value = m; markRow(m); },
  };
  openProposal(n);
  if (shared.CUR && shared.CUR.mode === "proposal") { irPeek.value = n; markRow(n); }
}
/** The row the peek shows is the selected one. @param {number} n */
function markRow(n) {
  document.querySelectorAll("#v-intake-review tr.irprop.sel").forEach(t => t.classList.remove("sel"));
  const t = document.querySelector(`#v-intake-review tr.irprop[data-irn='${n}']`); if (t) { t.classList.add("sel"); t.scrollIntoView({ block: "nearest" }); }
}

let booted = false;
/** Arrow keys walk the meetings and the proposals as one list; A, R, E and Enter act on the proposal with focus. Esc: a stale peek
    mark goes first, so one Esc closes the peek and the next closes the meeting (the page's own handler does the rest). */
export function bootProposalKeys() {
  if (booted) return; booted = true;
  document.addEventListener("keydown", e => {
    if (shared.VIEW !== "intake-review" || e.metaKey || e.ctrlKey || e.altKey) return;
    if (e.key === "Escape" && irPeek.value != null && !$("#panel").classList.contains("on")) irPeek.value = null;   /* the peek was closed another way */
    const t = /** @type {HTMLElement} */ (e.target);
    if (t && t.closest && t.closest("input,textarea,select,[contenteditable=true],[role=menu],dialog")) return;
    const row = t && t.closest ? /** @type {HTMLElement|null} */ (t.closest("tr.irprop[data-irn]")) : null;
    if (!row) return;
    const n = +(row.dataset.irn || 0);
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      const all = /** @type {HTMLElement[]} */ ([...document.querySelectorAll("#v-intake-review tr.irprop[data-irn], #v-intake-review tr[data-irm]")]);
      const next = all[all.indexOf(row) + (e.key === "ArrowDown" ? 1 : -1)];
      e.preventDefault(); e.stopPropagation();
      if (next) { next.focus(); if (next.dataset.irm) irSel.value = next.dataset.irm || null; }
      return;
    }
    if (t.closest("button,a")) return;                                   /* a focused control does its own job */
    const r = irRow(n); if (!r || r.done) return;
    if (e.key === "Enter") { e.preventDefault(); if (peekable(n)) openPeek(n); else edit(n); }
    else if (e.key === "a" || e.key === "A") { e.preventDefault(); approve(n); }
    else if (e.key === "r" || e.key === "R") { e.preventDefault(); reject(n, row.querySelector("[data-ira=reject]")); }
    else if (e.key === "e" || e.key === "E") { e.preventDefault(); edit(n); }
  }, true);
}
