// @ts-check
/* Intake and Review's Intake-side actions (#232-A, v2.5.0): Process (load the transcript if it is not loaded, then hand the saved
   file to cx-minutes through the run engine), Process all ready, Later, Not needed with a reason, Restore, and Upload files.
   Replaces intake.js's Calendar import and Upload files sections and the Intake parts of meetings.js for the new page; the old
   page keeps its own copies until 232-C retires it. Nothing here writes a file: the server's routes do (/api/transcripts/load,
   /api/inbox/upload, /api/intake/clear), and Process's own run kind (#264, POST /api/intake/process through processLive) makes the
   draft; Refresh is the calendar's own run kind (#265, POST /api/calendar/refresh through calendarLive). Someone else's minutes (Find
   work items) take the same Process route with "as": "minutes" (#232 E1; the guard's half is dev/proposals/intake-232-minutes/).
   Progress and Stop are the row's (irBusy); the ask panel is never opened. One run goes at a time (the engine's), so ask creaite
   waits while a row is processing. */
import { openChat } from "../../ask.js";
import { calendarLive, jobLive, mtgBusy, mtgCheckable, mtgProcessFile, mtgSkip, processLive, stopRun, TXWHY, UPLOAD_TYPES, uploadInboxFile } from "../../core/intakeApi.js";
import { D, fd, fdText, TODAY } from "../../core/page.js";
import { api, OLDSERVER, oneLine, reloadData, snack, viaServer } from "../../core/server.js";
import { shared } from "../../core/state.js";
import { pName } from "../../core/data.js";
import { srcShort } from "../../core/fields.js";
import { irFixed, irKindOf, irMatches, irNameOk, irUnsure } from "../../core/irFold.js";
import { irAside, irAskQ, irBlocked, irBusy, irChecking, irFileKinds, irModel, irNote, irRefRun, irRow, irRefreshing, irSetAskQ, irSetBusy, irSetChecking, irSetFileKind, irStep, irTick } from "../../stores/intakeReview.js";

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

/** The Process run in progress (its ID, for Stop on the row), or "". */
let irRun = "";

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
    irSetAskQ(m.id, null); irStep.value = "";
    let r = /** @type {any} */ (null);
    try {                                                  /* #264: the click is the go-ahead; progress and Stop are on the row */
      const x = m.src === "calendar" ? calOf(m) : null;
      const sent = minutes ? { path: file, as: "minutes" } : x ? mtgProcessFile(x, file) : { path: file };
      r = await processLive([sent], ev => { if (ev.type === "run") irRun = ev.id; else if (ev.type === "step") irStep.value = ev.label || ""; });
    } catch (e) { /* checked below */ }
    finally { irRun = ""; irStep.value = ""; }
    if (r && r.stopped) irStopped = true;
    await reloadData();
    const after = rowOf(m.id);
    const done = !after || after.stage !== "arrived";      /* a file that was filed away has left the inbox: that is done, not failed */
    const o = r && (r.files || []).find((/** @type {any} */ f) => f.path === file);
    if (!done && o && (o.state === "needs" || o.state === "not_staged")) {     /* the run's own question, with ask creaite about this */
      irSetAskQ(m.id, { state: o.state, question: oneLine(o.question || "") });
      irNote(m.id, o.state === "needs" ? `Needs you: ${oneLine(o.question || "")}` : "Not in Review yet: process it again, or ask creaite");
    } else if (!done) irNote(m.id, r && r.stopped ? "Stopped: nothing was added to Review" : `Couldn't: ${oneLine((r && r.message) || "no draft came back")}`);
    if (r && r.closure && r.closure.line) snack(oneLine(r.closure.line));
    return done;
  } finally { irSetBusy(m.id, false); }
}

/** Whether Stop was pressed (or a run came back stopped) since Process all ready began: it then starts no further row. */
let irStopped = false;
/** Stop on the running row: the server ends the run and says so; the row then says nothing was staged, and Process all ready
    starts nothing more. */
export function irStop() { irStopped = true; if (irRun) stopRun(irRun); }
/** Whether the running row can offer Stop (every Process run, Find work items too, is Process's own run kind). @param {any} m */
export const irCanStop = m => !!m && irBusy.value.includes(m.id);
/** "ask creaite about this": the panel opens with the run's question filled in; nothing is sent by itself. @param {any} m */
export function irAskAbout(m) {
  const q = irAskQ.value[m.id]; if (!q) return;
  openChat();
  const box = /** @type {HTMLTextAreaElement | null} */ (document.getElementById("chIn"));
  if (box) { box.value = `About the Intake file “${m.title}”: ${q.question || "Process didn't stage it. Why not, and what should I do?"}`; box.focus(); }
}

/** Process every meeting and file whose transcript is ready, one after another. Stop on the running row ends the rest too. */
export async function irProcessAll() {
  if (!viaServer()) { snack("Processing needs the live server"); return; }
  if (mtgBusy() || irBusy.value.length || irChecking.value.length) { snack(BUSY); return; }
  const ids = irReady().map((/** @type {any} */ m) => m.id), left = irLeftOut().length;
  irStopped = false; let ran = 0;
  for (const id of ids) {
    if (irStopped) break;
    const m = rowOf(id); if (m) { await irProcess(m); ran++; }
  }
  if (irStopped) { snack(`Stopped: ${ids.length - ran} not started`); irStopped = false; return; }
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
  let added = 0, skipped = 0;
  try {
    for (const f of files) {
      const u = await uploadInboxFile(f);
      if (u === false) return;
      if (u) added++; else skipped++;
    }
  } catch (e) { snack("The files couldn't be added: the live server didn't answer. Try again."); if (added) await reloadData(); return; }
  if (added) await reloadData();
  if (added) snack(`${added} file${added === 1 ? "" : "s"} added to Intake${skipped ? `; ${skipped} not added (only .vtt, .docx, .txt, .md or .pdf, up to 25 MB each)` : ""}`);
}

/** Refresh the calendar (the icon beside "Calendar read" under the heading): the calendar's own run kind (#265). ask creaite's
    panel stays closed; the sub-line says Refreshing… with the run's step, the icon becomes Stop, and the closure is said once.
    @returns {Promise<boolean>} whether it ran */
export async function irRefreshCalendar() {
  if (irRefRun.value) { stopRun(irRefRun.value.id); return false; }       /* the icon is Stop while it runs */
  if (!viaServer()) { snack("Refreshing needs the live server"); return false; }
  if (mtgBusy() || irBlocked() || irRefreshing.value) { snack(BUSY); return false; }
  irRefreshing.value = true; irRefRun.value = { id: "", step: "" };
  let r = /** @type {any} */ (null);
  try {
    shared.RUNLABEL = "Refreshing the calendar";
    try {
      r = await calendarLive(ev => { const c = irRefRun.value; if (!c) return;
        if (ev.type === "run") irRefRun.value = { ...c, id: ev.id }; else if (ev.type === "step") irRefRun.value = { ...c, step: ev.label || "" }; });
    } catch (e) { /* the sub-line shows the time it has */ }
    irRefRun.value = null;
    await reloadData();
    snack(r && r.closure ? oneLine(r.closure.line) : r && r.stopped ? "Stopped" : oneLine((r && r.message) || "The calendar was not saved"));
    return true;
  } finally { irRefRun.value = null; irRefreshing.value = false; irTick.value++; }
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
