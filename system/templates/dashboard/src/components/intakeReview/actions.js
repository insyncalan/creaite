// @ts-check
/* Intake and Review's Intake-side actions (#232-A, v2.5.0): Process (load the transcript if it is not loaded, then hand the saved
   file to cx-minutes through the run engine), Process all ready, Later, Not needed with a reason, Restore, and Upload files.
   Replaces intake.js's Calendar import and Upload files sections and the Intake parts of meetings.js for the new page; the old
   page keeps its own copies until 232-C retires it. Nothing here writes a file: the server's routes do (/api/transcripts/load,
   /api/inbox/upload, /api/intake/clear), and ask creaite's own run (askLive) makes the draft.
   Progress is the row's (irBusy); the ask panel is never opened, so ask creaite stays free (one run at a time is the engine's). */
import { askLive } from "../../ask.js";
import { jobLive, mtgBusy, mtgCheckable, mtgSkip, TXWHY, UPLOAD_TYPES, uploadInboxFile } from "../../intake.js";
import { D, fd, fdText, TODAY } from "../../core/page.js";
import { api, OLDSERVER, oneLine, reloadData, snack, viaServer } from "../../core/server.js";
import { shared } from "../../core/state.js";
import { pName } from "../../core/data.js";
import { srcShort } from "../../core/fields.js";
import { irFixed, irKindOf, irMatches, irNameOk, irUnsure } from "../../core/irFold.js";
import { irAside, irBlocked, irBusy, irChecking, irFileKinds, irModel, irNote, irRow, irRefreshing, irSetBusy, irSetChecking, irSetFileKind, irTick } from "../../stores/intakeReview.js";

/** The reasons Not needed asks for (build_dashboard.NOT_NEEDED_REASONS). */
export const IR_REASONS = ["Informal chat", "No decisions", "Duplicate of another meeting", "Other"];
export const IR_UPLOAD_TYPES = UPLOAD_TYPES;
const BUSY = "ask creaite is busy; try again when it's finished";

/** Whether Process applies: a meeting or file whose transcript is ready (not waiting, drafted or done). @param {any} m */
export const irCanProcess = m => !!m && m.stage === "arrived" && m.state === "ready" && m.src !== "draft";
/** Whether Later and Not needed apply: anything that has arrived, is not yet drafted and is not being processed now. @param {any} m */
export const irCanSetAside = m => !!m && m.stage === "arrived" && m.src !== "draft" && !irBusy.value.includes(m.id);
/** A row's kind with this browser's choice applied: "transcript", "minutes", or "" for a file that is not sure (a meeting is a transcript). @param {any} m */
export const irFileKind = m => irKindOf(m, irFileKinds.value);
/** Why Process all ready leaves a row out, or "": a private or confidential meeting, or a file that is not sure what it is. An explicit
    Process on the row itself is "naming it", as cx-minutes allows (Alan, via Jarvis, 19-10-2026). @param {any} m */
export const irLeaveOut = m => (m.private || m.confidential ? "private" : irBadName(m) ? "name" : irUnsure(m, irFileKinds.value) ? "type" : "");
/** Why a row is left out, in the words the page uses (counts only: a confidential meeting is never named). */
export const IR_LEFT_WHY = "private, confidential, not sure what it is or name not allowed";
/** Whether a file's name cannot be sent to ask creaite (a control character, backtick, double quote or angle bracket): it must be
    renamed first, and Process and Process all ready skip it. @param {any} m */
export const irBadName = m => !!m && m.src === "upload" && !irNameOk(m.path || m.title);
/** The rows Process all ready would run. */
export const irReady = () => irModel().meetings.filter((/** @type {any} */ m) => irCanProcess(m) && !irLeaveOut(m) && !irBusy.value.includes(m.id));
/** The ready rows it leaves out (counts only: a confidential meeting is never named). */
export const irLeftOut = () => irModel().meetings.filter((/** @type {any} */ m) => irCanProcess(m) && !!irLeaveOut(m) && !irBusy.value.includes(m.id));
/** What a row's main button says: a transcript file is made into minutes, a minutes file is checked for work items, a meeting is processed.
    @param {any} m */
export const irProcessWord = m => (m.src !== "upload" ? "Process" : irFileKind(m) === "transcript" ? "Make minutes" : irFileKind(m) === "minutes" ? "Find work items" : "Process");
/** Choose what a file is (transcript or minutes); remembered in this browser. @param {any} m @param {string} kind */
export function irChooseKind(m, kind) { if (m && m.src === "upload" && !irFixed(m)) irSetFileKind(m, kind); }

/** The calendar import row (D.meetings.rows) a model row came from. @param {any} m */
const calOf = m => (m.src === "calendar" ? ((D.meetings && D.meetings.rows) || []).find((/** @type {any} */ x) => x.key === m.key) || null : null);
const rowOf = (/** @type {string} */ id) => irModel().meetings.find((/** @type {any} */ x) => x.id === id) || null;
const whenOf = (/** @type {any} */ m) => (m.start ? `${fd(m.day)} at ${m.start}` : fd(m.day));

/** Process one meeting or file. The row shows progress; a reason it could not be done is its note.
    @param {any} m @returns {Promise<boolean>} whether a draft came back */
export async function irProcess(m) {
  if (!irCanProcess(m)) return false;
  if (irBadName(m)) { irNote(m.id, "Rename this file to process it"); return false; }
  if (irUnsure(m, irFileKinds.value)) { irNote(m.id, "Say whether it is a transcript or minutes first"); return false; }
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
    if (!irNameOk(file)) { irNote(m.id, "Rename this file to process it"); return false; }      /* the name becomes part of the command */
    const minutes = irFileKind(m) === "minutes";           /* #232-E1: someone else's minutes are read for work items; no new minutes are drafted */
    try {
      await askLive(minutes ? `process ${file} as minutes by someone else` : `process ${file}`,
        minutes ? `Check “${m.title}” (${whenOf(m)}) for proposed items: minutes by someone else, no new minutes drafted` : `Process “${m.title}” (${whenOf(m)}) into draft minutes and proposed items`);
    } catch (e) { /* checked below */ }
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
  const ids = irReady().map((/** @type {any} */ m) => m.id), left = irLeftOut().length;
  for (const id of ids) { const m = rowOf(id); if (m) await irProcess(m); }
  if (left) snack(`${ids.length ? `Processed ${ids.length}. ` : ""}${left} left out: ${IR_LEFT_WHY}`);   /* counts only: a confidential meeting is never named */
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

/** Refresh the calendar (the icon beside "Calendar read" under the heading): read it again through the run engine. ask creaite's
    panel stays closed; the sub-line says Refreshing… and then shows the new time. @returns {Promise<boolean>} whether it ran */
export async function irRefreshCalendar() {
  if (!viaServer()) { snack("Refreshing needs the live server"); return false; }
  if (mtgBusy() || irBlocked() || irRefreshing.value) { snack(BUSY); return false; }
  irRefreshing.value = true;
  try {
    shared.RUNLABEL = "Refreshing the calendar";
    try { await askLive("refresh calendar", "Refresh the calendar for Intake and Today"); } catch (e) { /* the sub-line shows the time it has */ }
    await reloadData();
    return true;
  } finally { irRefreshing.value = false; irTick.value++; }
}

/** The words after "Calendar read": the time the calendar was last read (hh:mm), with the date when it was not today, or "No calendar
    yet". @param {string|null|undefined} fetched calendar.json's `fetched` ("YYYY-MM-DD HH:MM") @param {string} today YYYY-MM-DD */
export function irCalendarRead(fetched, today) {
  const f = String(fetched || "");
  if (!/^\d{4}-\d{2}-\d{2}/.test(f)) return "No calendar yet";
  const day = f.slice(0, 10), t = /^.{10}[ T](\d{2}:\d{2})/.exec(f);
  return `Calendar read ${[day === today ? "" : fd(day), t ? t[1] : ""].filter(Boolean).join(" ")}`;
}

/** Take an uploaded file out of Intake (kept in backups); an Undo puts it back. Used for a file that was already processed.
    @param {any} m @returns {Promise<boolean>} */
export async function irRemoveFile(m) {
  if (!m || m.src !== "upload" || !m.path) return false;
  if (!viaServer()) { snack("Removing needs the live server"); return false; }
  const r = await api("/api/inbox/remove", { path: m.path });
  if (!r.ok) { snack(oneLine(r.message === OLDSERVER ? OLDSERVER : r.message || "Couldn't remove it")); return false; }
  await reloadData();
  snack(`Removed ${m.title} from Intake (kept in backups)`, async () => {
    const b = await api("/api/inbox/restore", { kept: r.kept });
    if (b.ok) { await reloadData(); snack("Back in Intake"); } else snack(oneLine(b.message));
  });
  return true;
}

/* ---- the Search box (#232-A6) ---- */
/** What a meeting or file row is searched on: its title and its project's name. A private or confidential meeting is title only
    (the same words its row shows). @param {any} m */
export const irMeetingFields = m => (m.private || m.confidential ? [m.title] : [m.title, m.p ? pName(m.p) : ""]);
/** What a mail, Teams or other proposal is searched on: its title, its project's name and its source. @param {number} n */
export function irRowFields(n) {
  const r = irRow(n);
  return r ? [r.rec && r.rec.t, r.p ? pName(r.p) : "", fdText(srcShort(r.src))] : [];
}
/** The model with only the rows the search finds (the stage counts stay the page's whole). @param {any} model @param {string} q */
export function irFilterModel(model, q) {
  if (!String(q || "").trim()) return model;
  const keep = (/** @type {{needs: number[], routine: number[]}} */ g) => ({ needs: g.needs.filter(n => irMatches(q, irRowFields(n))), routine: g.routine.filter(n => irMatches(q, irRowFields(n))) });
  return { ...model, meetings: model.meetings.filter((/** @type {any} */ m) => irMatches(q, irMeetingFields(m))), mail: keep(model.mail), other: keep(model.other) };
}

/* ---- the entry points other screens call (the interface contract of #232: Today's day line, the palette, the rail) ---- */
/** Process the row with this id: its row id, its calendar event ID or key, or its file path. Resolves to whether a draft came back.
    @param {string} id @returns {Promise<boolean>} */
export function irProcessById(id) {
  const m = irModel().meetings.find((/** @type {any} */ x) => x.id === id || x.key === id || x.mkey === id || x.mkey === `calendar:${id}` || x.path === id);
  if (!m) { snack("That meeting isn't on the Intake page"); return Promise.resolve(false); }
  return irProcess(m);
}

/** Open the file chooser, from anywhere (a detached input, so it needs no Intake page on screen); the files chosen are added.
    Call it from a click or a key press: the browser allows a chooser only then. */
export function irPickFiles() {
  const el = document.createElement("input");
  el.type = "file"; el.multiple = true; el.accept = IR_UPLOAD_TYPES.join(","); el.hidden = true;
  el.addEventListener("change", () => { irAddFiles([...(el.files || [])]); el.remove(); });
  el.addEventListener("cancel", () => el.remove());
  document.body.appendChild(el);
  el.click();
}
