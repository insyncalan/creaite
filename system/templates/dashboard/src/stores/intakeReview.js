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
import { irCounts, irFoldClick, irKeepOpen, irStageClick, irToggle, irViewNorm } from "../core/irFold.js";

export const IR_VIEW_KEY = "creaite-ir-view";
/** @returns {import("../core/irFold.js").IrModel} */
export const irModel = () => /** @type {any} */ (D).intake_review || { meetings: [], mail: { needs: [], routine: [] }, other: { needs: [], routine: [] }, later: [], not_needed: [], counts: {} };
/** @param {number} n */
export const irRow = n => REV.find(r => r.n === n) || null;
/** @param {number} n */
export const irDone = n => { const r = irRow(n); return !r || !!r.done; };   /* gone from D.review: decided elsewhere */
/** Whether proposal n now has a hold (a peek edit made it a new risk, say): the groups move it from Routine to Needs. @param {number} n */
export const irHeld = n => { const r = irRow(n); return !!(r && r.hold); };

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

/* ===== #232-A (Intake side) ===== signals for the meeting row's actions; the actions themselves are in
   components/intakeReview/actions.js (re-exported by IntakeReviewPage.jsx). Keep this section 232-A's. */
/** A row's note after a Process that did not draft anything (Skipped: …, Couldn't: …), by meeting id. */
export const irNotes = signal(/** @type {Record<string, string>} */ ({}));
/** The Not needed reasons menu: the meeting it is for and what opened it, or null. */
export const irAside = signal(/** @type {{id: string, anchor: HTMLElement | null} | null} */ (null));
/** A note on a meeting's row, or "" to clear it. @param {string} id @param {string} text */
export function irNote(id, text) { const n = { ...irNotes.value }; if (text) n[id] = text; else delete n[id]; irNotes.value = n; }
/** Mark a meeting as being processed (or not). @param {string} id @param {boolean} on */
export function irSetBusy(id, on) { irBusy.value = on ? [...irBusy.value.filter(x => x !== id), id] : irBusy.value.filter(x => x !== id); }
