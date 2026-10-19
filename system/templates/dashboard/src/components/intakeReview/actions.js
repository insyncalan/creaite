// @ts-check
/* Intake and Review's Intake-side actions (#232-A, v2.5.0): Process (load the transcript if it is not loaded, then hand the saved
   file to cx-minutes through the run engine), Process all ready, Later, Not needed with a reason, Restore, and Upload files.
   Replaces intake.js's Calendar import and Upload files sections and the Intake parts of meetings.js for the new page; the old
   page keeps its own copies until 232-C retires it. Nothing here writes a file: the server's routes do (/api/transcripts/load,
   /api/inbox/upload, /api/intake/clear), and ask creaite's own run (askLive) makes the draft.
   Progress is the row's (irBusy); the ask panel is never opened, so ask creaite stays free (one run at a time is the engine's). */
import { askLive } from "../../ask.js";
import { jobLive, mtgBusy, mtgCheckable, mtgSkip, TXWHY, UPLOAD_TYPES, uploadInboxFile } from "../../intake.js";
import { D, fd, TODAY } from "../../core/page.js";
import { api, OLDSERVER, oneLine, reloadData, snack, viaServer } from "../../core/server.js";
import { shared } from "../../core/state.js";
import { irAside, irBusy, irChecking, irModel, irNote, irSetBusy, irSetChecking } from "../../stores/intakeReview.js";

/** The reasons Not needed asks for (build_dashboard.NOT_NEEDED_REASONS). */
export const IR_REASONS = ["Informal chat", "No decisions", "Duplicate of another meeting", "Other"];
export const IR_UPLOAD_TYPES = UPLOAD_TYPES;
const BUSY = "ask creaite is busy; try again when it's finished";

/** Whether Process applies: a meeting or file whose transcript is ready (not waiting, drafted or done). @param {any} m */
export const irCanProcess = m => !!m && m.stage === "arrived" && m.state === "ready" && m.src !== "draft";
/** Whether Later and Not needed apply: anything that has arrived, is not yet drafted and is not being processed now. @param {any} m */
export const irCanSetAside = m => !!m && m.stage === "arrived" && m.src !== "draft" && !irBusy.value.includes(m.id);
/** The meetings Process all ready would run: a private meeting ("Busy") is left out (Alan, via Jarvis, 19-10-2026). */
export const irReady = () => irModel().meetings.filter((/** @type {any} */ m) => irCanProcess(m) && !m.private && !irBusy.value.includes(m.id));

/** The calendar import row (D.meetings.rows) a model row came from. @param {any} m */
const calOf = m => (m.src === "calendar" ? ((D.meetings && D.meetings.rows) || []).find((/** @type {any} */ x) => x.key === m.key) || null : null);
const rowOf = (/** @type {string} */ id) => irModel().meetings.find((/** @type {any} */ x) => x.id === id) || null;
const whenOf = (/** @type {any} */ m) => (m.start ? `${fd(m.day)} at ${m.start}` : fd(m.day));

/** Process one meeting or file. The row shows progress; a reason it could not be done is its note.
    @param {any} m @returns {Promise<boolean>} whether a draft came back */
export async function irProcess(m) {
  if (!irCanProcess(m)) return false;
  if (!viaServer()) { snack("Processing needs the live server"); return false; }
  if (mtgBusy() || irBusy.value.length || irChecking.value.length) { snack(BUSY); return false; }
  irNote(m.id, ""); irSetBusy(m.id, true);
  const label = `Processing “${m.title}”`;
  try {
    let file = m.path;
    if (m.src === "calendar") {
      const x = calOf(m);
      if (!x) { irNote(m.id, "Skipped: refresh the calendar to pick this meeting"); return false; }
      const why = mtgSkip(x);
      if (why) { irNote(m.id, `Skipped: ${why}`); return false; }
      file = x.loaded;
      if (!file) {                                   /* Load and Process are one step */
        shared.RUNLABEL = label;
        try { await jobLive("/api/transcripts/load", { id: x.id }); } catch (e) { /* the row says what happened */ }
        await reloadData();
        const now = calOf(m);
        file = now && now.loaded;
        if (!file) { irNote(m.id, `Skipped: ${TXWHY[/** @type {keyof TXWHY} */ (now && now.transcript)] || "No transcript could be loaded"}`); return false; }
      }
    }
    shared.RUNLABEL = label;
    try { await askLive(`process ${file}`, `Process “${m.title}” (${whenOf(m)}) into draft minutes and proposed items`); } catch (e) { /* checked below */ }
    await reloadData();
    const after = rowOf(m.id);
    const done = !after || after.stage !== "arrived";      /* a file that was filed away has left the inbox: that is done, not failed */
    if (!done) irNote(m.id, "Couldn't: no draft came back");
    return done;
  } finally { irSetBusy(m.id, false); }
}

/** Process every meeting and file whose transcript is ready, one after another. */
export async function irProcessAll() {
  if (!viaServer()) { snack("Processing needs the live server"); return; }
  if (mtgBusy() || irBusy.value.length || irChecking.value.length) { snack(BUSY); return; }
  const ids = irReady().map((/** @type {any} */ m) => m.id);
  for (const id of ids) { const m = rowOf(id); if (m) await irProcess(m); }
}

/** The clear route's item for a row. @param {any} m @param {Record<string, any>} [extra] */
const asideItem = (m, extra) => ({ key: m.key || m.path, day: m.src === "upload" ? TODAY : m.day, start: m.start || "", title: m.title, ...extra });

/** Set meetings aside through the clear route, then offer Undo. @param {any[]} ms @param {Record<string, any>} extra @param {string} what */
async function setAside(ms, extra, what) {
  if (!viaServer()) { snack("This needs the live server"); return false; }
  const r = await api("/api/intake/clear", { op: "clear", items: ms.map(m => asideItem(m, extra)) });
  if (!r.ok) { snack(oneLine(r.message === OLDSERVER ? OLDSERVER : r.message || "Couldn't do that")); return false; }
  const keys = ms.map(m => m.key || m.path);
  await reloadData();
  snack(`${what}: ${ms.length === 1 ? ms[0].title : `${ms.length} meetings`}`, () => irRestore(keys));
  return true;
}

/** Later: a waiting meeting leaves the list and comes back when its transcript arrives; a ready one or a file (its transcript is
    already here) stays in Later until it is restored. @param {any} m */
export function irLater(m) { return irCanSetAside(m) ? setAside([m], { kind: "later", seen: m.state === "ready" }, "Later") : Promise.resolve(false); }

/** Not needed, with a reason (and a one-line note); an Undo is offered. @param {any} m @param {string} reason @param {string} [note] */
export function irNotNeeded(m, reason, note) {
  return irCanSetAside(m) && IR_REASONS.includes(reason) ? setAside([m], { reason, note: note || "" }, "Not needed") : Promise.resolve(false);
}

/** What "Restored n …" calls the things restored: files (keys that are inbox paths), meetings, or both. @param {string[]} keys @param {number} n */
export function irRestoredWords(keys, n) {
  const files = keys.filter(k => ((D.inbox || []).some((/** @type {any} */ f) => f.path === k))).length;
  const noun = files === 0 ? "meeting" : files === keys.length ? "file" : "item";
  return `Restored ${n} ${noun}${n === 1 ? "" : "s"}`;
}

/** Bring meetings back from Later or Not needed, by key. @param {string[]} keys */
export async function irRestore(keys) {
  const r = await api("/api/intake/clear", { op: "restore", keys });
  if (!r.ok) { snack(oneLine(r.message || "Couldn't restore")); return false; }
  await reloadData();
  snack(irRestoredWords(keys, r.count));
  return true;
}

/** Whether Check again applies: a Teams meeting that is still waiting for its transcript and has ended. @param {any} m */
export function irCanCheck(m) {
  const x = m && m.state === "waiting" && m.stage === "arrived" ? calOf(m) : null;
  return !!x && !m.private && mtgCheckable(x) && !irChecking.value.includes(m.id);
}

/** Check again: look the transcript up through the run engine (no chat is opened); the row shows what the sweep finds.
    @param {any} m @returns {Promise<boolean>} whether a check ran */
export async function irCheck(m) {
  if (!irCanCheck(m)) return false;
  if (!viaServer()) { snack("Checking needs the live server"); return false; }
  if (mtgBusy() || irBusy.value.length || irChecking.value.length) { snack(BUSY); return false; }
  irSetChecking(m.id, true);
  try {
    shared.RUNLABEL = `Checking “${m.title}”`;
    try { await jobLive("/api/transcripts/check", { id: /** @type {any} */ (calOf(m)).id }); } catch (e) { /* the row shows what was found */ }
    await reloadData();
    return true;
  } finally { irSetChecking(m.id, false); }
}

/** Open the Not needed reasons menu for a row. @param {any} m @param {HTMLElement | null} anchor */
export function irAskReason(m, anchor) { if (irCanSetAside(m)) irAside.value = { id: m.id, anchor }; }

/** Upload files (picked or dropped anywhere on the page): each becomes a row. @param {File[]} files */
export async function irAddFiles(files) {
  if (!files.length) return;
  if (!viaServer()) { snack("Adding files needs the live server"); return; }
  let added = 0;
  for (const f of files) {
    const u = await uploadInboxFile(f);
    if (u === false) return;
    if (u) added++;
  }
  if (added) { await reloadData(); snack(`${added} file${added === 1 ? "" : "s"} added`); }
}
