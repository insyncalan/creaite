// @ts-check
/* stores/intakeReview.js (#232-0, v2.5.0): Intake and Review's state. The model is the server's (D.intake_review, built by
   build_dashboard.intake_review_model); the rules are core/irFold.js (pure, tested under Node); this file holds the signals
   the page draws from and the one place that reads and writes the remembered view.

   Seams for the later parts (dev/proposals/intake-review-232/README.md):
   - irModel()      the model, refreshed with D (core/server.js Object.assign(D, …) brings a new one after every apply or reload)
   - irDone(n)      whether proposal n is decided on the page (REV's done flag, set by review.js's decide and rvDecideMany)
   - irRow(n)       the Review row for n (D.review): what 232-B's proposal rows draw
   - irOpen         the open meeting (one at a time); irClickMeeting(id) is the one click that opens or closes it
   - irPeek         the proposal shown in the peek (232-B), or null
   - irBusy         meeting ids being processed in the background (232-A: Process sets and clears it)
   - irTick         bump to redraw after REV changes without new data (renderIntakeReview does it) */
import { signal } from "@preact/signals";
import { D, store } from "../core/page.js";
import { REV } from "../core/data.js";
import { IR_STAGES, irCounts, irFoldClick, irKeepOpen, irStageClick, irToggle, irViewNorm } from "../core/irFold.js";

export const IR_VIEW_KEY = "creaite-ir-view";
/** @returns {import("../core/irFold.js").IrModel} */
export const irModel = () => /** @type {any} */ (D).intake_review || { meetings: [], mail: { needs: [], routine: [] }, other: { needs: [], routine: [] }, later: [], not_needed: [], counts: {} };
/** @param {number} n */
export const irRow = n => REV.find(r => r.n === n) || null;
/** @param {number} n */
export const irDone = n => { const r = irRow(n); return !r || !!r.done; };   /* gone from D.review: decided elsewhere */

/** This browser's view (List, Board or Two panes); never shared, never in settings.json. */
export const irView = signal(irViewNorm((() => { try { return store.get(IR_VIEW_KEY, "list"); } catch (x) { return "list"; } })()));
/** @param {string} v */
export function irSetView(v) { irView.value = irViewNorm(v); try { store.set(IR_VIEW_KEY, irView.value); } catch (x) { /* storage blocked: this page only */ } }

export const irOpen = signal(/** @type {string|null} */ (null));
export const irStage = signal("all");
export const irFolded = signal(/** @type {Record<string, boolean>} */ ({}));
export const irPeek = signal(/** @type {number|null} */ (null));
export const irSel = signal(/** @type {string|null} */ (null));   /* Two panes: the meeting on the right */
export const irBusy = signal(/** @type {string[]} */ ([]));
export const irTick = signal(0);

/** @param {string} id */
export function irClickMeeting(id) { irOpen.value = irToggle(irOpen.value, id, irModel()); }
/** @param {string} g */
export function irClickStage(g) { irStage.value = irStageClick(irStage.value, g); }
/** @param {string} sec */
export function irClickFold(sec) { irFolded.value = irFoldClick(irFolded.value, sec); }
/** After new data: the open meeting stays open while it is in the list. */
export function irAfterData() { irOpen.value = irKeepOpen(irOpen.value, irModel()); irTick.value++; }
/** The live counts, the badge among them (232-C wires the rail badge and Today to this). */
export const irLiveCounts = () => irCounts(irModel(), irDone);

/* ---- #232-C: addresses and links (232-A and 232-B leave this section alone) ----
   An address or a link names a place on the page: a stage (#intake-review&stage=drafted), a meeting (&m=<meeting id>) or a
   proposal (#review=<n>, go("intake-review", {n})). irTarget moves the page there; it never decides anything. */
/** The meeting whose groups hold proposal n, or null (mail, Teams and other proposals have no meeting). @param {number} n */
export function irMeetingOf(n) { const m = (irModel().meetings || []).find(x => x.groups && [...(x.groups.needs || []), ...(x.groups.routine || [])].includes(n)); return m ? m.id : null; }
/** @param {any} t  a proposal number, a meeting id, or {stage, m, n} @returns {boolean} whether it found what it named */
export function irTarget(t) {
  if (t == null || t === "") return false;
  if (typeof t === "number" || typeof t === "string") t = /^\d+$/.test(String(t)) ? { n: +t } : { m: String(t) };
  let hit = false;
  if (t.stage) { irStage.value = IR_STAGES.includes(t.stage) ? t.stage : "all"; hit = true; }
  const id = t.m && (irModel().meetings || []).some(x => x.id === t.m) ? t.m : t.n != null ? irMeetingOf(+t.n) : null;
  if (id) { irOpen.value = id; irSel.value = id; hit = true; }
  irTick.value++;
  return hit;
}
/** Open the meeting of the first of these proposals and bring it into view (Close the day's Review now, First thing, a toast). @param {number[]} ns */
export function irReveal(ns) {
  const hit = ns.some(n => irTarget({ n }));
  if (hit) requestAnimationFrame(() => requestAnimationFrame(() => { const el = document.querySelector(`#v-intake-review [data-irm="${irOpen.value}"]`); if (el && el.scrollIntoView) el.scrollIntoView({ block: "center" }); }));
  return hit;
}
/** The address's part of the page's place: the stage when filtered and the open meeting. */
export const irPlace = () => ({ stage: irStage.value === "all" ? "" : irStage.value, m: irOpen.value || "" });
