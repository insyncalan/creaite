// @ts-check
/* core/intakeApi.js (#232-C, v2.6.0): what Intake does with the server, with no page of its own. The meeting list's state and tests
   (MTG, MRUN, mtgLater, mtgCheckable, mtgSkip, mtgBusy, TXWHY), a transcript job (jobLive, checkMeeting), the inbox calls (the upload
   rules, previewInbox, removeInbox) and the calendar refresh. They were intake.js's; they moved here unchanged so the one Intake page
   (components/intakeReview/) and Today use them without the old Intake page. intake.js re-exports every name, so nothing that imported
   it breaks.

   Nothing here draws the old pages. Where the old page still needs to redraw after one of these, it registers a function in
   `intakeHooks` (intake.js does, at load); with no hook set each is a no-op. The hooks go with the old page. */
import { openDialog } from "../components/Dialog.jsx";
import { askLive, askStream, mdView, openChat, runAsk, setRunning } from "../ask.js";
import { $, html, putHTML, raw } from "./dom.js";
import { addEl } from "./fields.js";
import { D, fd, TODAY } from "./page.js";
import { api, OLDSERVER, oneLine, reloadData, snack, viaServer } from "./server.js";
import { shared } from "./state.js";

/** The old page's redraws, set by intake.js. `refreshing` returns the function that ends its "Refreshing…" look.
    @type {{meetings: () => void, inbox: () => void, refreshing: () => (() => void)}} */
export const intakeHooks = { meetings() {}, inbox() {}, refreshing: () => () => {} };

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

/* ===== A transcript job (a check or a load) goes through the run engine like a question, but isn't a chat; the server writes the status and the files ===== */
export let jobLive = async function(url,body){ if(!shared.RUNLABEL) shared.RUNLABEL=/load/.test(url)?"Loading a transcript":"Checking a transcript"; const id=`r-${Date.now().toString(36)}-${Math.random().toString(36).slice(2,8)}`, ctl=new AbortController(); shared.RUN={id,ctl}; setRunning(true);
  try{ await askStream(url,{...body,run:id},true,ctl,undefined,true); } finally{ shared.RUN=null; setRunning(false); } };   /* BL-326: drawn plainly (steps and the closure) */
export async function checkMeeting(m){ if(!viaServer()){ snack("Checking needs the live server"); return; } if(mtgBusy()){ snack("ask creaite is busy; try again when it's finished"); return; }
  MRUN[m.id]="checking"; intakeHooks.meetings(); openChat(); runAsk(addEl("msg u",html`${`Check the transcript of “${m.title}” (${fd(m.day)} at ${m.start})`}`));
  try{ await jobLive("/api/transcripts/check",{id:m.id}); }catch(e){} delete MRUN[m.id]; await reloadData(); intakeHooks.meetings(); }

/* ===== The inbox: the upload rules, preview and remove ===== */
/* One place for the upload rules (types, 25 MB, the upload call): Add files on the Intake page and the old Upload files section both use it.
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
  D.inbox=(D.inbox||[]).filter(x=>x.path!==path); intakeHooks.inbox();
  snack(`Removed ${f?f.name:path} from Intake (kept in backups)`,async()=>{ const b=await api("/api/inbox/restore",{kept:r.kept}); if(b.ok){ await reloadData(); intakeHooks.inbox(); snack("Back in Intake"); } else snack(oneLine(b.message)); }); }

/* ===== The calendar: read it again now. Runs through the run engine (askLive); `chat:false` keeps ask creaite's panel closed and adds no message. ===== */
/** @param {{chat?: boolean}} [opts] @returns {Promise<boolean>} true when the refresh ran */
export async function refreshCalendar(opts){ const chat=!opts||opts.chat!==false; let ran=false;
  if(!viaServer()){ snack("Refreshing needs the live server"); return false; } if(mtgBusy()){ snack("ask creaite is busy; try again when it's finished"); return false; }
  const end=intakeHooks.refreshing();
  try{ if(chat){ openChat(); addEl("msg u","Refresh calendar"); }
    try{ await askLive("refresh calendar","Refresh the calendar for Intake and Today"); ran=true; }catch(e){} await reloadData(); intakeHooks.meetings(); return ran; }
  finally{ end(); } }

/** The test seams for the values above that tests replace (a stub transcript job, the clock). */
export const apiSeams = { jobLive: /** @param {typeof jobLive} v */ v => { jobLive = v; }, nowHM: /** @param {typeof nowHM} v */ v => { nowHM = v; } };
