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
import { IR_KINDS, IR_STAGES, irCounts, irFoldClick, irKeepOpen, irKindOf, irStageClick, irToggle, irViewNorm } from "../core/irFold.js";

export const IR_VIEW_KEY = "creaite-ir-view";
/** @returns {import("../core/irFold.js").IrModel} */
export const irModel = () => /** @type {any} */ (D).intake_review || { meetings: [], mail: { needs: [], routine: [] }, other: { needs: [], routine: [] }, later: [], not_needed: [], counts: {} };
/** @param {number} n */
export const irRow = n => REV.find(r => r.n === n) || null;
/** @param {number} n */
export const irDone = n => { const r = irRow(n); return !r || !!r.done; };   /* gone from D.review: decided elsewhere */
/** The open proposals Review holds that the model does not (a sweep staged them since the model was built: the quick refresh after
    a tracker or Review event brings D.review but not D.intake_review). The counts include them at once; the page, when it is
    shown, reloads the data to draw them (core/server.js evFlush, core/nav.js go). @returns {number[]} */
export const irMissing = () => {
  const m = /** @type {any} */ (irModel()), have = new Set([...(m.meetings || []).flatMap((/** @type {any} */ x) => [...x.groups.needs, ...x.groups.routine]),
    ...["mail", "other"].flatMap(k => [...(m[k].needs || []), ...(m[k].routine || [])])]);
  return REV.filter(r => !r.done && !have.has(r.n)).map(r => r.n);
};
/** The files in D.inbox that wait to be processed: new, an upload, not a loaded meeting's transcript and not set aside (those are
    listed in the model's later or not_needed, by path). `fresh` are those the model lacks (one dropped in inbox/ since it was built:
    the quick file refresh brings D.inbox but not D.intake_review); `ready` those whose kind is known, `sure` the fresh ones among
    them (the rest need a type). Today's line, the badge and the page all count from this. */
export const irFreshFiles = () => {
  const m = /** @type {any} */ (irModel()), kinds = irFileKinds.value, idOf = (/** @type {any} */ x) => x.path || x.key,
    aside = new Set([...(m.later || []), ...(m.not_needed || [])].map(idOf).filter(Boolean)),
    known = new Set((m.meetings || []).map((/** @type {any} */ x) => x.path).filter(Boolean)),
    waiting = ((/** @type {any} */ (D)).inbox || []).filter((/** @type {any} */ f) => f.state === "new" && f.uploaded !== false && !f.event && !aside.has(f.path)),
    sure = (/** @type {any} */ f) => !!irKindOf({ src: "upload", path: f.path, ft: f.ft, size: f.size, day: f.date }, kinds), fresh = waiting.filter((/** @type {any} */ f) => !known.has(f.path));
  return { waiting, fresh, ready: waiting.filter(sure), sure: fresh.filter(sure) };
};
export const irModelBehind = () => irMissing().length > 0 || irFreshFiles().fresh.length > 0;
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
export function irAfterData() { irOpen.value = irKeepOpen(irOpen.value, irModel()); irPruneKinds(); irTick.value++; }
/** The live counts, the badge among them (232-C wires the rail badge and Today to this). */
export const irLiveCounts = () => {
  const c = irCounts(irModel(), irDone, irFileKinds.value), fr = irFreshFiles();
  /* #232-C: a file that arrived since the model was built (the quicker file refresh does not rebuild it) counts at once, as the
     Intake badge did; a transcript Calendar import loaded belongs to its meeting's row */
  const extra = fr.fresh.length, sure = fr.sure.length;   /* a file of unknown kind is not ready */
  const late = irMissing().length;   /* proposals the quick refresh brought into Review before the model was rebuilt */
  const k = { ...c, to_approve: c.to_approve + late, badge: c.badge + late };
  return extra ? { ...k, arrived: k.arrived + extra, ready: k.ready + sure, need_type: k.need_type + extra - sure, badge: k.badge + sure, all: k.all + extra } : k;
};

/* ===== #232-A (Intake side) ===== signals for the meeting row's actions; the actions themselves are in
   components/intakeReview/actions.js (re-exported by IntakeReviewPage.jsx). Keep this section 232-A's. */
/** A row's note after a Process that did not draft anything (Skipped: …, Couldn't: …), by meeting id. */
export const irNotes = signal(/** @type {Record<string, string>} */ ({}));
/** #307: the files the last Add files could not add, each named with why ("notes.xlsx: …"). They stay on the page until dismissed
    or the next Add files replaces them (a toast would vanish, and the next file's toast would replace it). */
export const irAddProblems = signal(/** @type {string[]} */ ([]));
/** The Not needed reasons menu: the meeting it is for and what opened it, or null. */
export const irAside = signal(/** @type {{id: string, anchor: HTMLElement | null} | null} */ (null));
/** A note on a meeting's row, or "" to clear it. @param {string} id @param {string} text */
export function irNote(id, text) { const n = { ...irNotes.value }; if (text) n[id] = text; else delete n[id]; irNotes.value = n; }
/** Whether ask creaite (or a transcript job) is running: mirrors shared.RUN and shared.BUSY, which are not signals, so a button
    that reads this redraws when the run ends (ask.js setRunning and the BUSY flag set it). */
export const irAsk = signal(false);
/** Meeting ids whose transcript is being looked up again (Check again). */
export const irChecking = signal(/** @type {string[]} */ ([]));
/** Whether a row's Process must wait: this page is drafting or checking, or ask creaite is working. A signal read, so it redraws. */
export const irBlocked = () => irBusy.value.length > 0 || irChecking.value.length > 0 || irAsk.value;
/** @param {string} id @param {boolean} on */
export function irSetChecking(id, on) { irChecking.value = on ? [...irChecking.value.filter(x => x !== id), id] : irChecking.value.filter(x => x !== id); }
/** The kind (transcript or minutes) chosen for a file, by its path: this browser's, kept in localStorage (never shared, never in
    settings.json); another browser derives it again from the file's name. */
export const IR_KIND_KEY = "creaite-ir-filekind";
export const irFileKinds = signal(/** @type {Record<string, {k: string, size: number, day: string}>} */ ((() => {
  try {
    const v = store.get(IR_KIND_KEY, {});
    if (!v || typeof v !== "object" || Array.isArray(v)) return {};
    return Object.fromEntries(Object.entries(v).filter(([, e]) => e && typeof e === "object" && IR_KINDS.includes(/** @type {any} */ (e).k)));   /* an older entry (a bare word) has no size: it is dropped */
  } catch (x) { return {}; }
})()));
const irSaveKinds = () => { try { store.set(IR_KIND_KEY, irFileKinds.value); } catch (x) { /* storage blocked: this page only */ } };
/** Choose a file's kind. The choice is kept with the file's size and day, so it is never taken for another file that later has the
    same path. @param {any} m the file's row @param {string} kind */
export function irSetFileKind(m, kind) {
  if (!m || !m.path || !IR_KINDS.includes(kind)) return;
  irFileKinds.value = { ...irFileKinds.value, [m.path]: { k: kind, size: m.size || 0, day: m.day || "" } };
  irSaveKinds();
}
/** Drop the choices whose file is gone from inbox/ or is no longer the file they were made for (new data brings D.inbox). */
export function irPruneKinds() {
  const inbox = /** @type {any[]|undefined} */ (/** @type {any} */ (D).inbox);
  if (!Array.isArray(inbox)) return;
  const cur = irFileKinds.value, keep = /** @type {typeof cur} */ ({});
  for (const [p, e] of Object.entries(cur)) { const f = inbox.find(x => x.path === p); if (f && e.size === (f.size || 0) && e.day === (f.date || "")) keep[p] = e; }
  if (Object.keys(keep).length !== Object.keys(cur).length) { irFileKinds.value = keep; irSaveKinds(); }
}
/** The Search box's text: filters the meetings, files and mail rows on this page (client side; never saved). */
export const irQuery = signal("");
/** Whether files are being dragged over the page: the full-page "Drop to add files" overlay shows (pointer-events none, so ask creaite's panel still gets its images). */
export const irDropOn = signal(false);
/** Whether the calendar is being read again (the refresh icon under the heading): the sub-line says "Refreshing…" meanwhile. */
export const irRefreshing = signal(false);
/** #264 on this page: the Process run's latest step in plain words (the route's "step" events), shown on the running row. */
export const irStep = signal("");
/** #264: a question the Process run could not answer without Alan (or "not staged"), by row id: the row offers "ask creaite about
    this", which opens the panel with the question filled in (never sent by itself). */
export const irAskQ = signal(/** @type {Record<string, {state: string, question: string}>} */ ({}));
/** @param {string} id @param {{state: string, question: string} | null} q */
export function irSetAskQ(id, q) { const n = { ...irAskQ.value }; if (q) n[id] = q; else delete n[id]; irAskQ.value = n; }
/** #265 on this page: the calendar refresh in progress, its run ID (for Stop) and its latest step, or null. */
export const irRefRun = signal(/** @type {{id: string, step: string} | null} */ (null));
/** Mark a meeting as being processed (or not). @param {string} id @param {boolean} on */
export function irSetBusy(id, on) { irBusy.value = on ? [...irBusy.value.filter(x => x !== id), id] : irBusy.value.filter(x => x !== id); }

/* ---- #232-C: addresses and links (232-A and 232-B leave this section alone) ----
   An address or a link names a place on the page: a stage (#intake-review&stage=drafted), a meeting (&m=<meeting id>) or a
   proposal (#review=<n>, go("intake-review", {n})). irTarget moves the page there; it never decides anything. */
/** The meeting whose groups hold proposal n, or null (mail, Teams and other proposals have no meeting). @param {number} n */
export function irMeetingOf(n) { const m = (irModel().meetings || []).find(x => x.groups && [...(x.groups.needs || []), ...(x.groups.routine || [])].includes(n)); return m ? m.id : null; }
/** @param {any} t  a proposal number, a meeting id, or {stage, m, n} @returns {boolean} whether it found what it named */
export function irTarget(t) {
  if (t == null || t === "") return false;
  if (typeof t === "number" || typeof t === "string") t = /^\d+$/.test(String(t)) ? { n: +t } : { m: String(t) };
  let found = false;
  if (t.stage) { irStage.value = IR_STAGES.includes(t.stage) ? t.stage : "all"; found = true; }
  const id = t.m && (irModel().meetings || []).some(x => x.id === t.m) ? t.m : t.n != null ? irMeetingOf(+t.n) : null;
  if (id) { irOpen.value = id; irSel.value = id; found = true; }
  irTick.value++;
  return found;
}
/** Open the meeting of the first of these proposals and bring it into view (Close the day's Review now, First thing, a toast). @param {number[]} ns */
export function irReveal(ns) {
  const found = ns.some(n => irTarget({ n }));
  if (found) requestAnimationFrame(() => requestAnimationFrame(() => { const el = document.querySelector(`#v-intake-review [data-irm="${irOpen.value}"]`); if (el && el.scrollIntoView) el.scrollIntoView({ block: "center" }); }));
  return found;
}
/** The address's part of the page's place: the stage when filtered and the open meeting. */
export const irPlace = () => ({ stage: irStage.value === "all" ? "" : irStage.value, m: irOpen.value || "" });
