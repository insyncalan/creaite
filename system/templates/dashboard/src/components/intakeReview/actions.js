// @ts-check
/* Intake and Review's Intake-side actions (#232-A, v2.5.0): Process (load the transcript if it is not loaded, then hand the saved
   file to cx-minutes through the run engine), Process all ready, Later, Not needed with a reason, Restore, and Upload files.
   Replaces intake.js's Calendar import and Upload files sections and the Intake parts of meetings.js for the new page; the old
   page keeps its own copies until 232-C retires it. Nothing here writes a file: the server's routes do (/api/transcripts/load,
   /api/inbox/upload, /api/intake/clear), and ask creaite's own run (askLive) makes the draft.
   Progress is the row's (irBusy); the ask panel is never opened, so ask creaite stays free (one run at a time is the engine's). */
import { askLive } from "../../ask.js";
import { jobLive, mtgBusy, mtgSkip, TXWHY } from "../../intake.js";
import { D, fd, TODAY } from "../../core/page.js";
import { api, OLDSERVER, oneLine, reloadData, snack, viaServer } from "../../core/server.js";
import { shared } from "../../core/state.js";
import { irAside, irBusy, irModel, irNote, irSetBusy } from "../../stores/intakeReview.js";

/** The reasons Not needed asks for (build_dashboard.NOT_NEEDED_REASONS). */
export const IR_REASONS = ["Informal chat", "No decisions", "Duplicate of another meeting", "Other"];
export const IR_UPLOAD_TYPES = [".vtt", ".docx", ".txt", ".md", ".pdf"];
const BUSY = "ask creaite is busy; try again when it's finished";

/** Whether Process applies: a meeting or file whose transcript is ready (not waiting, drafted or done). @param {any} m */
export const irCanProcess = m => !!m && m.stage === "arrived" && m.state === "ready" && m.src !== "draft";
/** Whether Later and Not needed apply: anything that has arrived and is not yet drafted. @param {any} m */
export const irCanSetAside = m => !!m && m.stage === "arrived" && m.src !== "draft";
/** The meetings Process all ready would run. */
export const irReady = () => irModel().meetings.filter((/** @type {any} */ m) => irCanProcess(m) && !irBusy.value.includes(m.id));

/** The calendar import row (D.meetings.rows) a model row came from. @param {any} m */
const calOf = m => (m.src === "calendar" ? ((D.meetings && D.meetings.rows) || []).find((/** @type {any} */ x) => x.key === m.key) || null : null);
const rowOf = (/** @type {string} */ id) => irModel().meetings.find((/** @type {any} */ x) => x.id === id) || null;
const when = (/** @type {any} */ m) => (m.start ? `${fd(m.day)} at ${m.start}` : fd(m.day));

/** Process one meeting or file. The row shows progress; a reason it could not be done is its note.
    @param {any} m @returns {Promise<boolean>} whether a draft came back */
export async function irProcess(m) {
  if (!irCanProcess(m)) return false;
  if (!viaServer()) { snack("Processing needs the live server"); return false; }
  if (mtgBusy() || irBusy.value.length) { snack(BUSY); return false; }
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
    try { await askLive(`process ${file}`, `Process “${m.title}” (${when(m)}) into draft minutes and proposed items`); } catch (e) { /* checked below */ }
    await reloadData();
    const after = rowOf(m.id);
    const done = !!after && after.stage !== "arrived";
    if (!done) irNote(m.id, "Couldn't: no draft came back");
    return done;
  } finally { irSetBusy(m.id, false); }
}

/** Process every meeting and file whose transcript is ready, one after another. */
export async function irProcessAll() {
  if (!viaServer()) { snack("Processing needs the live server"); return; }
  if (mtgBusy() || irBusy.value.length) { snack(BUSY); return; }
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

/** Later: the meeting leaves the ready list and comes back when its transcript arrives (a transcript already here: Restore).
    @param {any} m */
export function irLater(m) { return irCanSetAside(m) ? setAside([m], { kind: "later", seen: m.state === "ready" }, "Later") : Promise.resolve(false); }

/** Not needed, with a reason (and a one-line note); an Undo is offered. @param {any} m @param {string} reason @param {string} [note] */
export function irNotNeeded(m, reason, note) {
  return irCanSetAside(m) && IR_REASONS.includes(reason) ? setAside([m], { reason, note: note || "" }, "Not needed") : Promise.resolve(false);
}

/** Bring meetings back from Later or Not needed, by key. @param {string[]} keys */
export async function irRestore(keys) {
  const r = await api("/api/intake/clear", { op: "restore", keys });
  if (!r.ok) { snack(oneLine(r.message || "Couldn't restore")); return false; }
  await reloadData();
  snack(`Restored ${r.count} meeting${r.count === 1 ? "" : "s"}`);
  return true;
}

/** Open the Not needed reasons menu for a row. @param {any} m @param {HTMLElement | null} anchor */
export function irAskReason(m, anchor) { if (irCanSetAside(m)) irAside.value = { id: m.id, anchor }; }

/** Upload files (picked or dropped anywhere on the page): each becomes a row. @param {File[]} files */
export async function irAddFiles(files) {
  if (!files.length) return;
  if (!viaServer()) { snack("Adding files needs the live server"); return; }
  let added = 0;
  for (const f of files) {
    const ext = (f.name.match(/\.[^.]+$/) || [""])[0].toLowerCase();
    if (!IR_UPLOAD_TYPES.includes(ext)) { snack(`${f.name}: only .vtt, .docx, .txt, .md or .pdf`); continue; }
    if (f.size > 25 * 1048576) { snack(`${f.name} is over 25 MB`); continue; }
    const data = await new Promise((res, rej) => {
      const fr = new FileReader(); fr.onload = () => res(String(fr.result).split(",")[1] || ""); fr.onerror = () => rej(fr.error); fr.readAsDataURL(f);
    });
    const r = await api("/api/inbox/upload", { name: f.name, data });
    if (!r.ok) { if (r.message === OLDSERVER) { snack(OLDSERVER); return; } snack(`${f.name}: ${oneLine(r.message)}`); continue; }
    added++;
  }
  if (added) { await reloadData(); snack(`${added} file${added === 1 ? "" : "s"} added`); }
}
