// @ts-check
/* core/intakeApi.js (#232-C, v2.6.0): what Intake does with the server, with no page of its own. The meeting list's state and tests
   (MTG, MRUN, mtgLater, mtgCheckable, mtgSkip, mtgBusy, TXWHY), a transcript job (jobLive, checkMeeting), the inbox calls (the upload
   rules, previewInbox, removeInbox), Process's own route (processLive, #264) and the calendar refresh's (calendarLive, #265). They were intake.js's; they moved here so the one Intake page
   (components/intakeReview/), Today and the palette use them. The old Intake and Review pages were retired in 2.6.0 (C2);
   intake.js is an empty shell that re-exports this module, to be deleted in a later release. Nothing here draws a page. */
import { openDialog } from "../components/Dialog.jsx";
import { askStream, mdView, openChat, runAsk, setRunning } from "../ask.js";
import { $, html, putHTML, raw } from "./dom.js";
import { addEl } from "./fields.js";
import { D, fd, TODAY } from "./page.js";
import { api, OLDSERVER, oneLine, reloadData, snack, viaServer } from "./server.js";
import { shared } from "./state.js";

/* ===== The meeting list: this week's meetings from the saved calendar, and the state kept for each ===== */
export const MTG=()=>(D.meetings&&D.meetings.rows)||[], MRUN={};
/* A meeting that hasn't ended can't have a transcript yet: greyed and not selectable until it ends (Alan, 2026-10-09).
   Worked out in the page, so a meeting becomes selectable on its own once its end time passes. */
export let nowHM = function(){ const n=new Date(); return `${String(n.getHours()).padStart(2,"0")}:${String(n.getMinutes()).padStart(2,"0")}`; };   /* a function, so tests can set the clock */
export const mtgLater=m=>m.day>TODAY||(m.day===TODAY&&(m.end||m.start||"")>nowHM());
export const mtgBusy=()=>!!shared.RUN||(typeof shared.BUSY!=="undefined"&&shared.BUSY);
export const mtgCheckable=m=>!!m.id&&m.teams&&!mtgLater(m)&&!m.processed&&m.transcript!=="none";
export const TXWHY={none:"No transcript for this meeting",not_transcribed:"Not transcribed yet",no_access:"No access to the transcript"};
export const mtgSkip=m=>m.loaded?"":TXWHY[m.transcript]||(!m.transcript&&!m.teams?"Not a Teams meeting, so there is no transcript to load":"");

/** A run's id: its kind, the time and a random part (one clock read for every run here, #178; ported from 2.5.3's intake.js). @param {string} kind */
const runId = kind => `${kind}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2,8)}`;

/* ===== A transcript job (a check or a load) goes through the run engine like a question, but isn't a chat; the server writes the status and the files ===== */
export let jobLive = async function(url,body){ if(!shared.RUNLABEL) shared.RUNLABEL=/load/.test(url)?"Loading a transcript":"Checking a transcript"; const id=runId("r"), ctl=new AbortController(); shared.RUN={id,ctl}; setRunning(true);
  try{ await askStream(url,{...body,run:id},true,ctl,undefined,true); } finally{ shared.RUN=null; setRunning(false); } };   /* BL-326: drawn plainly (steps and the closure) */
export async function checkMeeting(m){ if(!viaServer()){ snack("Checking needs the live server"); return; } if(mtgBusy()){ snack("ask creaite is busy; try again when it's finished"); return; }
  MRUN[m.id]="checking"; openChat(); runAsk(addEl("msg u",html`${`Check the transcript of “${m.title}” (${fd(m.day)} at ${m.start})`}`));
  try{ await jobLive("/api/transcripts/check",{id:m.id}); }catch(e){} delete MRUN[m.id]; await reloadData(); }

/* ===== The inbox: the upload rules, preview and remove ===== */
export const kb=n=>n>1048576?`${(n/1048576).toFixed(1)} MB`:`${Math.max(1,Math.round(n/1024))} KB`;   /* a size in words (was intake.js's) */
/* One place for the upload rules (types, 25 MB, the upload call): Add files on the Intake page uses it.
   Returns {r, ext} for a file added; null for one skipped (a snack says why); false when the server is too old to go on. */
export const UPLOAD_TYPES=[".vtt",".docx",".txt",".md",".pdf"], UPLOAD_MAX=25*1048576;
export async function uploadInboxFile(f){ const ext=(f.name.match(/\.[^.]+$/)||[""])[0].toLowerCase();
  if(!UPLOAD_TYPES.includes(ext)){ snack(`${f.name}: only .vtt, .docx, .txt, .md or .pdf`); return null; }
  if(f.size>UPLOAD_MAX){ snack(`${f.name} is over 25 MB`); return null; }
  const data=await new Promise((res,rej)=>{ const fr=new FileReader(); fr.onload=()=>res(String(fr.result).split(",")[1]||""); fr.onerror=()=>rej(fr.error); fr.readAsDataURL(f); });
  const r=await api("/api/inbox/upload",{name:f.name,data}); if(!r.ok){ if(r.message===OLDSERVER){ snack(OLDSERVER); return false; } snack(`${f.name}: ${oneLine(r.message)}`); return null; }
  return {r,ext}; }
/* preview before processing; remove moves the file to backups (Undo puts it back) */
export async function previewInbox(path){ if(!viaServer()){ snack("Previewing needs the live server"); return; } const r=await api("/api/inbox/preview",{path});
  if(!r.ok){ snack(r.message===OLDSERVER?OLDSERVER:oneLine(r.message)); return; }
  if(r.open){ const o=await api("/api/open",{path}); snack(o.ok?"Opened in its own app":oneLine(o.message)); return; }
  $("#inPrevName").textContent=r.name; $("#inPrevText").textContent=r.text||"(empty)";
  { const md=/\.(md|markdown)$/i.test(r.name||path)&&!!r.text; $("#inPrevText").hidden=md; $("#inPrevMd").hidden=!md; putHTML($("#inPrevMd"),raw(md?mdView(r.text,{hBase:2}):"")); }   /* BL-196: a Markdown file is shown formatted */ $("#inPrevCut").hidden=!r.cut; $("#inPrev").dataset.path=path; openDialog("inPrev"); }
export async function removeInbox(path){ if(!viaServer()){ snack("Removing needs the live server"); return; } const f=(D.inbox||[]).find(x=>x.path===path), r=await api("/api/inbox/remove",{path});
  if(!r.ok){ snack(r.message===OLDSERVER?OLDSERVER:oneLine(r.message)); return; }
  D.inbox=(D.inbox||[]).filter(x=>x.path!==path);
  snack(`Removed ${f?f.name:path} from Intake (kept in backups)`,async()=>{ const b=await api("/api/inbox/restore",{kept:r.kept}); if(b.ok){ await reloadData(); snack("Back in Intake"); } else snack(oneLine(b.message)); }); }

/* ===== #264: Process is its own run kind (POST /api/intake/process), not an ask creaite message =====
   The click is Alan's go-ahead to stage: the server checks the files and runs cx-minutes under a guard that may stage those files'
   meetings for Review and nothing else. Progress and Stop are on the row; a question the run couldn't answer comes back per file
   (state "needs" with its question, or "not_staged"). Moved here from the retired intake.js (2.5.3) for the one Intake page. */
/** @typedef {{ok: boolean, files?: {path: string, state: string, question?: string}[], staged?: number, needs?: number, closure?: any, stopped?: boolean, message?: string}} ProcessResult */
/** One SSE stream from a run route: each event to `onEv`, folded into `got` by `fold`. @param {Response} r @param {(ev: any) => void} fold @param {(ev: any) => void} [onEv] */
async function readEvents(r, fold, onEv){ const rd=/** @type {ReadableStream<Uint8Array>} */(r.body).getReader(), dec=new TextDecoder(); let buf="";
  for(;;){ const {value,done}=await rd.read(); if(done) break; buf+=dec.decode(value,{stream:true});
    for(let i=buf.indexOf("\n\n"); i>=0; i=buf.indexOf("\n\n")){ const c=buf.slice(0,i); buf=buf.slice(i+2); if(!c.startsWith("data: ")) continue; let ev; try{ ev=JSON.parse(c.slice(6)); }catch(e){ continue; }
      fold(ev); if(onEv) onEv(ev); } } }
/** A run route's POST, streamed; one run at a time (shared.RUN), Stop by its ID. @param {string} url @param {any} body @param {string} pre @param {(got: any, ev: any) => void} fold @param {(ev: any) => void} [onEv] */
async function runRoute(url, body, pre, fold, onEv){ const id=runId(pre), ctl=new AbortController(); shared.RUN={id,ctl}; setRunning(true); /** @type {any} */ const got={};
  if(onEv) onEv({type:"run",id});     /* the run's ID first, for Stop */
  try{ const r=await fetch(url,{method:"POST",signal:ctl.signal,headers:{"Content-Type":"application/json","X-Creaite-Token":D.token||""},body:JSON.stringify({...body,run:id})});
    if(!r.ok||!r.body){ const j=await r.json().catch(()=>({})); return {ok:false,message:j.message||"It couldn't start: check the live server."}; }
    await readEvents(r, ev=>{ if(ev.type==="closure") got.closure=ev; else if(ev.type==="stopped") got.stopped=true; else if(ev.type==="error") got.message=ev.message; else fold(got,ev); }, onEv);
    return {ok:true,...got}; }
  catch(e){ return {ok:false,stopped:e&&e.name==="AbortError",message:e&&e.name==="AbortError"?"Stopped":"The live server stopped."}; }
  finally{ shared.RUN=null; setRunning(false); api("/api/ask/ack",{run:id}); } }
/* One Process run (a seam, so tests can stand in for the server). */
/** @param {{path: string, project?: string}[]} files @param {(ev: any) => void} [onEv] @returns {Promise<ProcessResult>} */
export let processLive = function(files,onEv){ return runRoute("/api/intake/process",{files},"i",(got,ev)=>{ if(ev.type==="intake"){ got.files=ev.files; got.staged=ev.staged; got.needs=ev.needs; } },onEv); };
/* #264 S6: the project goes with the file only when Alan chose it (the picker, or remembered for the series); a match from the
   title or the portfolio guess is left for the run to work out, never presented as his choice. The portfolio is "_portfolio". */
/** @param {any} m a calendar import row @param {string} path @returns {{path: string, project?: string}} */
export const mtgProcessFile=(m,path)=>m&&m.p&&m.how==="remembered"?{path,project:m.p}:{path};
/** Stop the run with this ID (Process or Refresh): the server ends it and says so on its stream. @param {string} id */
export function stopRun(id){ if(id) api("/api/ask/stop",{run:id}); }

/* ===== #265: Refresh is its own run kind (POST /api/calendar/refresh), not an ask creaite message =====
   The click is Alan's go-ahead to read his calendar and save it for Intake and Today: the server runs the sweep's calendar steps
   under a guard that may do that and nothing else. ask creaite doesn't open; the closure is said once. */
/** @typedef {{ok: boolean, saved?: boolean, meetings?: number, days?: number, transcripts?: boolean, closure?: any, stopped?: boolean, message?: string}} CalendarResult */
/* One calendar refresh (a seam, so tests can stand in for the server). */
/** @param {(ev: any) => void} [onEv] @returns {Promise<CalendarResult>} */
export let calendarLive = function(onEv){ return runRoute("/api/calendar/refresh",{},"c",(got,ev)=>{ if(ev.type==="calendar"){ got.saved=ev.saved; got.meetings=ev.meetings; got.days=ev.days; got.transcripts=ev.transcripts; } },onEv); };

/* ===== #283: Read again is its own run kind (POST /api/minutes/reextract), not an ask creaite message =====
   The click (after the Minutes view's ask) is Alan's go-ahead to draft one meeting's minutes afresh from its transcript: the server
   sets the earlier draft aside and runs cx-minutes under a guard that may stage that one meeting and nothing else; the new draft
   takes the place, with the Track choices carried where the item is the same, or the earlier one comes back (Stop, a failure, a
   question). Undo (POST /api/minutes/reextract/undo) brings the earlier one back. ask creaite doesn't open. */
/** @typedef {{run?: string, state?: string, proposal?: string, path?: string, items?: number, new?: number, gone?: number, kept?: number, question?: string}} ReadAgainOutcome */
/** @typedef {{ok: boolean, reextract?: ReadAgainOutcome, closure?: any, stopped?: boolean, message?: string}} ReadAgainResult */
/* One Read again run (a seam, so tests can stand in for the server). */
/** @param {string} proposal @param {(ev: any) => void} [onEv] @returns {Promise<ReadAgainResult>} */
export let reLive = function(proposal,onEv){ return runRoute("/api/minutes/reextract",{proposal},"x",(got,ev)=>{ if(ev.type==="reextract") got.reextract=ev; },onEv); };
/* Undo of a Read again, by its run's ID (a seam too). */
/** @param {string} run @returns {Promise<{ok: boolean, message?: string, proposal?: string, path?: string}>} */
export let reUndoLive = function(run){ return api("/api/minutes/reextract/undo",{run}); };

/** The test seams for the values above that tests replace (a stub transcript job, the clock). */
export const intakeSeams = { jobLive: /** @param {typeof jobLive} v */ v => { jobLive = v; }, nowHM: /** @param {typeof nowHM} v */ v => { nowHM = v; },
  processLive: /** @param {typeof processLive} v */ v => { processLive = v; }, calendarLive: /** @param {typeof calendarLive} v */ v => { calendarLive = v; },
  reLive: /** @param {typeof reLive} v */ v => { reLive = v; }, reUndoLive: /** @param {typeof reUndoLive} v */ v => { reUndoLive = v; } };
