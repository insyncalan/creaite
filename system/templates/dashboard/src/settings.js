// @ts-check
/* settings.js (BL-231 step 2b), moved from script/ by dev/tools/convert_area.py: 0073-settings-page-bl-115-sprint-settings.js, 0074-bl-214-sprint-ui-audit.js, 0075-after-bl-214.js, 0076-bl-235-fix-small-17.js, 0078-after-bl-163-settings-row.js, 0079-people-bl-55-bl-56.js, 0127-workstreams-bl-58-bl-56.js, 0138-sweep-and-alerts-bl-97-bl-99-bl-98.js, 0140-after-bl-152.js, 0153-bl-252-fix-small-17.js, 0154-bl-263-fix-doctor-errors.js, 0155-after-bl-263.js, 0163-bl-165-sprint-polish-2.js.
   Unchanged apart from `export`, `shared.` for the shared state (core/state.js) and the load-time steps, now in
   boot…() functions that src/main.js calls in today's order. */
import { closeDialog, openDialog } from "./components/Dialog.jsx";
import { makeArchiveAskDialog } from "./components/dialogs/PageDialogs.jsx";
import { closeFilterBar, drawFilterBar, filterBarOpen, openFilterBar } from "./components/FilterBar.jsx";

import { mdView, pendingEdit, RBMARK, SEARCHCFG } from "./ask.js";
import { A, DEC, open, openOnly, P, PEOPLE, peopleAll, pName, R, REGD, REV, saveWs, SWEPT, wsFor, wsHidden, wsKey, WSL, wsParts, wsUsed } from "./core/data.js";
import { effect } from "@preact/signals";
import { h, render } from "preact";
import { Essentials } from "./components/settings/Essentials.jsx";
import { Health } from "./components/settings/Health.jsx";
import { MoreSettings } from "./components/settings/MoreSettings.jsx";
import { drawTabs } from "./components/Tabs.jsx";
import { $, $$, addHTML, esc, html, ibtn, ic, putHTML, raw, swapHTML } from "./core/dom.js";
import { openPath } from "./core/fields.js";
import { typing } from "./core/keys.js";
import { mDots } from "./core/motion.js";
import { countLink, go, pLink, tabTitle } from "./core/nav.js";
import { applyMotion, applyTheme, cmdBox, copied, D, fd, ico, isMe, kindOf, MOD, MTICK, nowStamp, reduced, S, store, themeFade, themeOf, THEMES, TODAY, who } from "./core/page.js";
import { api, applyPending, DIAG, diagErr, diagLoad, editProposal, needVault, oneLine, refreshAll, reloadData, save, SERVED, setLive, setRhythm, SKEY, snack, status, toDb, viaServer, vq, writeSettings } from "./core/server.js";
import { shared } from "./core/state.js";
import { catalogue, changedOnly, checkHealth, lastCheckAt, loadCatalogue, query, resetSettings, SAVED, settingOf, startSettingsStore } from "./stores/settings.js";
import { chaseNote, draftAsk, openDraftEmail } from "./drafts.js";
import { refreshFiles } from "./files.js";
import { decLate, decLateWords, decRank } from "./meetings.js";
import { drawPanel, ebMarkSeen, errBanner, openNew, markStagedRows, pkDraw, PKDRAW, pkNewOffer, pkNote, pkSaveAndClose, pkSaving, REC } from "./panel.js";
import { closePanel, decorateWarnings, PKN, WARNS, warnSectionHtml, WICO, WSIG } from "./projects.js";
import { draftOn, renderReview } from "./review.js";
import { railLabelsOn, setRailCount } from "./stores/rail.js";
import { PEOPLE_MOVE, personPromises, plur, projLink, renderToday, tl } from "./today.js";
import { cell, fchipHtml, FDEFS, funnelTip, FX, groupsOf, hit, hlPrune, items, latesOf, ownersOf, personFlags, personLinks, personRedraw, personTbl, personWork, relaxHtml, renderPeople, rows, sizeList, viewsList, xcueSoon } from "./work.js";
/* ===== Settings page (BL-115, sprint-settings) ===== */
/* One page: the categories on the left, the settings on the right. SETSECTIONS is the one list the page is built from.
   An entry has an id, a category, a title, search keywords (`kw`) and `render()`, which returns what goes inside the card.
   With `raw`, `render()` returns the whole card (it carries its own id and data-sec). `elid` is the card's element id
   where something else looks it up; `after()` wires what needs the DOM. A later feature adds a section by adding an entry.
   How a setting saves is unchanged: the handlers below and in the sections' own code write settings.json through
   writeSettings (a backup, a log line, the live server's checks). */
/* BL-320 (v1.9.2): four categories. Essentials (the ~16 settings that change the day, opened first), People and projects,
   Advanced (everything else: the older categories' cards, each under its old name, then every remaining setting from the
   catalogue) and Health (what needs you, then the live server, set-up, Diagnostics, the version and Stop). The sections keep
   their old category as `cat`; CATOF maps it to where it now shows, so a section another module adds (Set-up, AI drafts) moves
   with no change to that module. */
export const SETCATS=[["essentials","Essentials"],["people","People and projects"],["advanced","Advanced"],["health","Health"]];
export const CATOF={general:"advanced",work:"advanced",review:"advanced",capture:"advanced",system:"health"};
export const OLDCATS={general:"You and the look",work:"Work and views",review:"Review and warnings",capture:"Capture and alerts",advanced:"Everything else"};
export const catOf=s=>CATOF[s.cat]||s.cat;
/* Addresses: #settings/<category> opens that category; #settings/<section> (sweep, diagnostics…) opens the category the
   section is in and scrolls to it. The old STAB values (prefs, admin, people, projects) and a bare #settings still work:
   setting STAB picks a category the same way. */
export const SETOLD={prefs:"essentials",admin:"people",general:"advanced",work:"advanced",capture:"advanced",system:"health"}, SETALIAS={diagnostics:"diag",updates:"version",backups:"live","live-server":"live","early-warnings":"warnings","ignore-rules":"sweep",follow:"vip"};
export function setResolve(t){ t=String(t||"").toLowerCase(); if(SETCATS.some(c=>c[0]===t)) return {cat:t}; if(SETOLD[t]) return {cat:SETOLD[t]};
  const sec=SETSECTIONS.find(x=>x.id===(SETALIAS[t]||t)); return sec?{cat:catOf(sec),sec:sec.id}:null; }
export let SECT=null; shared.SCAT="essentials"; shared.SQ="";                 /* the category, the section to scroll to, the search text */
export let CHANGED=false;                                                     /* BL-320: Show changed only */
export const sw=(k)=>`<input type="checkbox" class="switch" data-k="${k}" ${S[k]?"checked":""}>`;   /* BL-279: named by its row's label (row, srName), never its key */
export const tx=(k,ph)=>`<input type="text" data-k="${k}" value="${esc(S[k])}" placeholder="${ph||""}">`;
export const nm=(k)=>`<input type="number" data-k="${k}" value="${S[k]}" min="0" style="width:80px">`;
export const sl=(k,opts)=>`<select data-k="${k}">${opts.map(o=>Array.isArray(o)?`<option value="${o[0]}" ${S[k]===o[0]?"selected":""}>${o[1]}</option>`:`<option ${S[k]===o?"selected":""}>${o}</option>`).join("")}</select>`;
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootSettings0073(){
Object.defineProperty(window,"STAB",{configurable:true,get:()=>shared.SCAT,set:v=>{ const r=setResolve(v); shared.SCAT=r?r.cat:"essentials"; SECT=r&&r.sec||null; shared.SQ=""; const q=document.getElementById("setq"); if(q) q.value=""; }});
}
/* ===== BL-214 (sprint-ui-audit) ===== a Settings row ties its words to its field: the label (in a span with an id) names the field
   and the hint describes it (aria-labelledby, aria-describedby). A row with several fields names each "Label: its example". A field
   that already has a name keeps it; placeholders stay as examples. */
export let SRN=0;
export const srText=h=>String(h||"").replace(/<[^>]*>/g,"").replace(/\s+/g," ").trim();
export function srName(c,id,h,l){ const tags=String(c).match(/<(input|select|textarea)\b[^>]*>/g)||[], fields=tags.filter(t=>!/type="(hidden|button|submit)"/.test(t));
  const one=fields.length===1;
  return String(c).replace(/<(input|select|textarea)\b([^>]*)>/g,(m,tag,rest)=>{
    if(/type="(hidden|button|submit)"/.test(rest)||/aria-label(ledby)?=/.test(rest)) return m;
    const fid=(rest.match(/\bid="([^"]+)"/)||[])[1]; if(fid&&new RegExp(`<label[^>]*for="${fid}"`).test(c)) return m;
    if(one) return `<${tag} aria-labelledby="${id}"${h?` aria-describedby="${id}h"`:""}${rest}>`;
    const ex=(rest.match(/placeholder="([^"]*)"/)||rest.match(/title="([^"]*)"/)||[])[1]||"";
    return `<${tag} aria-label="${esc(srText(l)+(ex?": "+ex:""))}"${rest}>`; }); }
/* ===== BL-09: Archive and Restore in Settings › Projects =====
   Each project has Archive (Restore for an archived one, listed with Show archived). The live server builds the change with
   propose.py (the folder to _Archive, the register row to Retired codes, the project and its items marked archived) and puts it on
   the approval card in ask creaite; Approve applies it through tracker.py apply, and Undo reverses it. A project with open items
   lists them first: Cancel them all and archive, or Stop. */
const PSTATE={active:"Active",closed:"Closed",archived:"Archived"};
export function projArchiveHtml(){ const L=(D.project_states||[]).filter(p=>p.state!=="archived"||S.showArchived);
  return row("Show archived projects",sw("showArchived"),"Archived projects' items, and items archived for their age, in Work (tagged Archived), Today and the Excel export. Search finds them either way, marked Archived")
    +`<div class="tbl"><table class="mgr" id="projArch" aria-label="Projects: archive and restore"><tbody>${L.map(p=>{ const back=p.state==="archived";
      return `<tr><td>${esc(p.name)}</td><td>${PSTATE[p.state]||esc(p.state)}</td><td class="mgract"><button class="mini" data-parch="${back?"restore":"archive"}" data-pcode="${esc(p.code)}" aria-label="${back?"Restore":"Archive"} ${esc(p.name)}">${back?"Restore":"Archive"}</button></td></tr>`; }).join("")||'<tr><td class="sub">No projects yet.</td></tr>'}</tbody></table></div>`; }
/* BL-316: the Dialog block (made the first time it opens, components/dialogs/PageDialogs.jsx); Esc or the scrim is Stop */
export function openItemsAsk(name,open){ return new Promise(res=>{ const dlg=$("#parchDlg")||makeArchiveAskDialog();
  putHTML($("#parchBody"),html`<h2 id="parchH">${name} has ${open.length} open item${open.length===1?"":"s"}</h2><p class="sub">Nothing is archived with an item still open.</p><ul class="parchlist">${open.slice(0,30).map(o=>html`<li><b>${o.id}</b> ${o.text}</li>`)}</ul>${open.length>30?html`<p class="sub">and ${open.length-30} more</p>`:""}<div class="acts"><button class="btn" data-a="stop">Stop</button><button class="btn primary" data-a="go">Cancel them all and archive</button></div>`);
  const fin=v=>{ res(v); closeDialog(dlg); }; dlg.querySelector('[data-a="stop"]').onclick=()=>fin(false); dlg.querySelector('[data-a="go"]').onclick=()=>fin(true); dlg.addEventListener("close",()=>res(false),{once:true}); openDialog(dlg); }); }
export async function projArchive(code,action,cancel){ if(!viaServer()){ snack("Archiving needs the live server"); return; }
  const r=await api("/api/project/archive",{code,action,cancel_open:!!cancel});
  if(!r.ok&&(r.open||[]).length&&!cancel){ if(await openItemsAsk(pName(code),r.open)) return projArchive(code,action,true); snack("Stopped: nothing was archived"); return; }
  if(!r.ok){ snack(oneLine(r.message||"It couldn't be prepared")); return; }
  snack(r.message); await pendingEdit(); }
export function projArchiveBind(){ $$("#projArch [data-parch]").forEach(b=>b.onclick=()=>projArchive(b.dataset.pcode,b.dataset.parch,false)); }
/* ===== end BL-09 ===== */
export const row=(l,c,h)=>{ const id="sr"+(++SRN); return `<div class="srow"><div><span id="${id}">${l}</span>${h?`<small id="${id}h">${h}</small>`:""}</div><div>${srName(c,id,h,l)}</div></div>`; };
/* ===== end BL-214 ===== */
export const SETSECTIONS=[
 /* BL-320: a section with `mount` is a Preact component (dev/COMPONENTS.md), drawn into its own box; `match(words)` says
    whether a search (or Show changed only) finds anything in it. */
 {id:"essentials",cat:"essentials",title:"Essentials",kw:"essentials your day",
  mount:el=>render(h(Essentials,null),el),match:w=>{ const c=catalogue.value; return !!c&&c.essentials.some(r=>(!CHANGED||r.changed)&&sqHas(`${r.section} ${r.label} ${r.line} ${r.keys.join(" ")}`,w)); }},
 {id:"you",cat:"general",title:"You",kw:"short forms email domains identity owner mine company",
  render:()=>row("Short forms",tx("short","Alan, AC"),"Comma-separated; also matched as you (your name is in Essentials)")
   +row("Own email domains",`<input type="text" data-k="ownDomains" value="${esc((S.ownDomains||[]).join(", "))}" placeholder="example.com">`,"Comma-separated; addresses at these domains count as inside your company, so Draft email warns about anyone outside")},
 {id:"appearance",cat:"general",title:"Appearance",kw:"theme mode light dark colour palette column widths order reset motion animation reduced",
  render:()=>row("Column widths and order",ibtn("undo","Reset column widths and order",'id="rzReset"',"bd"),"Drag a column edge in Work to resize, or a heading to move it")},
 {id:"closeday",cat:"general",title:"Close the day",kw:"close the day evening catch up catch-up sweep before closing minutes shutdown",   /* BL-295; whether to catch up is in Essentials › Your day (BL-320) */
  render:()=>row("Catch up when the last sweep is older than (minutes)",nm("catchupAfter"),"A sweep more recent than this says “Caught up” instead, with Sweep again. Whether the card catches up is in Essentials › Your day")},
 {id:"views",cat:"work",title:"Opening views",kw:"default priority new action actions raid open status filter view",
  render:()=>row("New action priority",sl("defPriority",["Urgent","High","Medium","Low"]))+row("Actions open with",sl("defActionView",viewsList("actions")))+row("RAID opens with",sl("defRaidView",viewsList("raid")))+row("Decisions open with",sl("defDecisionView",viewsList("decisions")))},   /* BL-131 */
 {id:"board",cat:"work",title:"Work board",kw:"board group by actions raid decisions closed days column",
  render:()=>row("Actions board groups by",sl("bgActions",groupsOf("actions")))+row("RAID board groups by",sl("bgRaid",groupsOf("raid")))+row("Decisions board groups by",sl("bgDecisions",groupsOf("decisions")))
   +row("Board shows closed items from the last (days)",nm("boardClosedDays"),"The Closed column on a Work board; Show all brings the rest")},
 {id:"projpage",cat:"work",title:"Project page",kw:"flow weeks undated grace no due date list cap overdue ageing",
  render:()=>row("Flow looks back (weeks)",nm("flowWeeks"),"The project page's Flow card: opened and closed, overdue and ageing over this many weeks (8 or 12 are usual; 4 to 26 work)")
   +row("A new undated item counts as new for (days)",nm("undatedGrace"),"The project page's No due date card shows items raised this recently dimmer, so a fresh item isn't flagged the minute it's made")
   +row("Project page lists show at most",nm("listCap"),"Actions due or overdue; the rest are a link away")},
 {id:"files",cat:"work",title:"Files",kw:"files page documents project minutes transcripts reports search",
  render:()=>row("Show project documents",sw("filesDocs"),"Off by default: the Files page lists minutes, transcripts and reports (Weekly, Adhoc and Steerco), and skips the rest of a large engagement folder. Search still reads documents. Steerco is only read; creaite files nothing there.")},
 {id:"thresholds",cat:"review",title:"Review and health",kw:"stale due soon at risk off track overdue slip milestone urgent risks thresholds health review auto advance next proposal duplicate overlap",
  render:()=>row("Stale after (days)",nm("staleDays"))+row("Review: move to the next proposal after a decision",sw("rvAdvance"),"After Approve or Reject, the next undecided row is ready for the keyboard")
   +row("Review: possible duplicate when words overlap at least",`<input type="number" data-k="dupOverlap" value="${S.dupOverlap??0.6}" min="0.1" max="1" step="0.05" style="width:80px">`,"0.6 by default: the share of words a proposal has in common with an open item of the same type in the same project")+row("Due soon means within (days)",nm("dueSoon"))+row("At risk: action overdue more than (days)",nm("overdueDays"))
   +row("At risk: milestone slip up to (weeks)",nm("slipAtRisk"))+row("Off track: slip more than (weeks)",nm("slipOff"))+row("Off track: Urgent risks at least",nm("urgentOff"))},
 {id:"warnings",cat:"review",title:"Early warnings",elid:"warnSettings",kw:"early warnings signals re-dated repeat risk milestone slip long open key person vip dependency",render:()=>warnSectionHtml()},
 {id:"sweep",cat:"capture",title:"Sweep",kw:"sweep mail teams inbox sent items chats channels calendar look-back possible matches ignore rules due from",
  render:()=>row("First-run look-back (days)",nm("lookback"),"When the sweep runs and what it reads are in Essentials › Your day")
   +row("Show possible matches",sw("possible"))+'<div id="ignMgr"></div>',
  after:()=>renderIgnore()},
 {id:"vip",cat:"capture",title:"People I follow",elid:"vipSet",kw:"follow alerts important people notification browser",render:()=>vipSectionHtml()},
 {id:"reminders",cat:"capture",title:"Reminders",kw:"reminders weekly report day client report rhythm fortnightly monthly dismissed restore",
  render:()=>row("Reminders on",sw("remindersOn"),"The weekly report's day and time are in Essentials › Your day")
   +P.map(p=>row(`${p.name} client report`,`<select data-rhythm="${p.code}">${["Weekly","Fortnightly","Monthly","Off"].map(o=>`<option ${p.rhythm===o?"selected":""}>${o}</option>`).join("")}</select>`)).join("")
   +row("Dismissed reminders",`<button class="btn" id="remRestore">Restore</button>`,"Brings back reminders dismissed forever")},
 {id:"people",cat:"people",title:"People",raw:true,kw:"people owners register email aliases organisation role rename merge vip",render:()=>'<div class="card wide" id="peopleMgr" data-sec="people"></div>',after:()=>renderPeopleMgr()},
 {id:"workstreams",cat:"people",title:"Workstreams",raw:true,kw:"workstreams lead keywords rename merge retire project",render:()=>'<div class="card wide" id="wsMgr" data-sec="workstreams"></div>',after:()=>renderMgr("ws")},
 {id:"projects",cat:"people",title:"Projects and register",wide:true,kw:"projects register add close archive restore archived code signals domains matching",
  render:()=>'<p class="sub" style="margin:4px 0 0">Add or close projects and edit matching signals with plain English in ask creaite (for example <span data-codeok>“add project DEF…”, “add client.com to ABC\'s domains”</span>).</p>'+projArchiveHtml(),
  after:()=>projArchiveBind()},   /* BL-09 */
 {id:"health",cat:"health",title:"Health",kw:"health check problems fix",
  mount:el=>render(h(Health,null),el),match:()=>false},
 {id:"live",cat:"system",title:"Live server and backups",elid:"liveCard",kw:"live server backups port daily database backup status start terminal",
  render:()=>row("Status",shared.LIVE?'<span class="h-ok">Running</span>':'<span class="h-bad">Stopped</span>',"127.0.0.1, required")
   +row("Mail, Teams and data",esc(`${SWEPT==="never"?"Mail and Teams never swept":`Mail and Teams last swept ${fd(SWEPT)}`} · data as of ${fd(shared.DATA_AT).slice(0,16)}`))
   +row("Port",nm("port"),"The creaite app belongs to this port: if you change it, install the app again and reconnect the vault")
   +`<div class="srow" style="display:block"><div>Start the live server<small>Paste into Terminal</small></div>${cmdBox()}</div><div style="display:flex;gap:8px;margin-top:8px">${ibtn("refresh","Check now",'id="liveCheck"',"bd")}</div>`},
 {id:"diag",cat:"system",title:"Diagnostics",raw:true,kw:"diagnostics log level errors debug copy report folder",render:()=>diagCardHtml(),after:()=>{ if(SERVED) diagLoad().then(()=>{ if(shared.VIEW==="settings"&&shared.SCAT==="system") diagRedraw(); }); }},
 {id:"version",cat:"system",title:"creaite version",raw:true,kw:"version update install release zip undo",render:()=>'<div class="card" id="updCard" data-sec="version"><h2>creaite version</h2><p class="sub">Checking…</p></div>',after:()=>drawUpdates()},
 {id:"danger",cat:"system",title:"Stop the live server",elid:"dangerCard",kw:"stop live server quit",
  render:()=>row("Stop the live server",'<button class="btn danger" id="liveStop" title="Stops the live server; open creaite again from its launcher or Terminal">Stop</button>',"Open creaite again from its launcher or Terminal. Edits wait until it is running again")},
 {id:"more",cat:"advanced",title:"Everything else",kw:"everything else advanced",mount:el=>render(h(MoreSettings,{covered}),el),
  match:w=>{ const c=catalogue.value; return !!c&&c.settings.some(s=>s.tier!=="essentials"&&!covered(s.key)&&(!CHANGED||s.changed)&&sqHas(`${s.group} ${s.label} ${s.line} ${s.reason} ${s.key}`,w)); }}];
/* ===== BL-320 (v1.9.2): Settings, calmer, with Health inside =====
   The catalogue (/api/settings/catalogue, stores/settings.js) says, for every setting, whether it differs from its default.
   - Essentials, Health and Advanced's "Everything else" are components (`mount`); they read the catalogue and the page's
     search and Show changed only themselves.
   - Advanced's older cards are drawn as before, then each row that holds a setting gets the "changed" dot and Reset
     (setMark). A row's settings are found from its control's data attribute (ROWKEY); `covered` lists every setting these
     cards show, so "Everything else" lists only the rest.
   - Show changed only works like a search: the sections with a changed setting, across Essentials and Advanced, each
     showing only its changed rows.
   - A save on an older card rereads the catalogue (a moment later, once it is written); a save or a Reset anywhere brings
     the page's own copies up to date (setSynced). */
export const ROWKEY={k:v=>SKEY[v],vipk:v=>"vip."+v,drsw:v=>"drafting."+v,wk:v=>"warnings."+v};
export const COVERED_PREFIX=["warnings.","dashboard.rail."], COVERED_KEYS=["logging.level","sweep.ignore","vip.notify","reminders.dismissed_forever","dashboard.week_ahead_priorities"];
export const covered=k=>Object.values(SKEY).includes(k)||COVERED_KEYS.includes(k)||COVERED_PREFIX.some(p=>k.startsWith(p));
/** The settings a row of an older card holds, from its controls' data attributes. @param {Element} r */
export function rowKeys(r){ const out=[]; r.querySelectorAll("input,select,textarea").forEach(el=>{ const d=/** @type {HTMLElement} */(el).dataset;
  for(const [a,f] of Object.entries(ROWKEY)) if(d[a]!=null){ const k=f(d[a]); if(k&&!out.includes(k)) out.push(k); } }); return out; }
export const mounted=el=>!!(el&&el.closest&&el.closest("[data-mount]"));
/** The dot and Reset on each row of the older cards in `root` (idempotent: drawn afresh from the catalogue). @param {ParentNode} root */
export function setMark(root){ const c=catalogue.value; if(!c||!root) return;
  root.querySelectorAll(".srow").forEach(r=>{ if(mounted(r)) return; r.querySelectorAll(":scope .setdot,:scope .setreset").forEach(x=>x.remove()); r.classList.remove("chg");
    const ks=rowKeys(r).map(k=>settingOf(k)).filter(Boolean); if(!ks.some(s=>s.changed)) return; r.classList.add("chg");
    const lab=r.firstElementChild, name=srText(lab&&lab.firstElementChild?lab.firstElementChild.textContent:lab?lab.textContent:"");
    if(lab){ const d=document.createElement("span"); d.className="setdot"; d.setAttribute("role","img"); d.setAttribute("aria-label","Changed from the default"); d.title="Changed from the default"; (lab.firstElementChild||lab).after(d); }
    if(ks.every(s=>s.resettable)&&r.lastElementChild&&r.lastElementChild!==lab){ const b=document.createElement("button"); b.type="button"; b.className="mini setreset"; b.textContent="Reset";
      b.dataset.reset=ks.filter(s=>s.changed).map(s=>s.key).join(" "); b.setAttribute("aria-label",`Reset ${name} to its default`); b.title="Back to the default"; r.lastElementChild.append(b); } }); }
/** Bring the page's own copies of settings up to date after a save or a Reset. @param {Record<string, any>} ch */
export function setSynced(ch){ let reload=false, look=false;
  for(const [k,v] of Object.entries(ch)){
    const sk=Object.keys(SKEY).find(x=>SKEY[x]===k);
    if(sk) S[sk]=sk==="short"&&Array.isArray(v)?v.join(", "):v;
    if(k==="dashboard.theme"||k==="dashboard.palette"||k==="dashboard.motion") look=true;
    else if(k==="dashboard.week_ahead_priorities"){ S.weekPrios=v; reload=true; }
    else if(k.startsWith("drafting.")) S.drafting={...(S.drafting||{}),[k.slice(9)]:v};
    else if(k.startsWith("vip.")) VIPD()[k.slice(4)]=v;
    else if(k.startsWith("warnings.")){ const [,sig,f]=k.split("."), W=D.warn_settings||(D.warn_settings={}); W[sig]={...(W[sig]||{}),[f]:v}; }
    else if(k==="search.debounce_ms") SEARCHCFG.debounce_ms=v;
    else if(k==="dashboard.generate_days") S.genDays=v;
    else if(k==="dashboard.rail_labels") railLabelsOn.value=v!==false;   /* #156: Labels when collapsed */
    else if(k==="logging.level") DIAG.level=v;
    else if(k.startsWith("day.")||k==="work.weekend_days"||k==="dashboard.flow_weeks") reload=true; }
  if(look){ themeFade(); applyTheme(); applyMotion(); }
  if(reload) reloadData(); status(); }
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootSettings0076(){
startSettingsStore();
SAVED.push(setSynced);
/* a save on an older card: the catalogue is reread once it is written, so its dot and Reset follow */
let t=0; $("#settingsBody").addEventListener("change",e=>{ if(mounted(e.target)||!SERVED) return; clearTimeout(t); t=window.setTimeout(()=>loadCatalogue(),900); });
$("#settingsBody").addEventListener("click",async e=>{ const b=e.target.closest("[data-reset]"); if(!b||mounted(b)) return;
  const keys=b.dataset.reset.split(" ").filter(Boolean), name=(b.getAttribute("aria-label")||"").replace(/^Reset | to its default$/g,""); b.disabled=true;
  const r=await resetSettings(keys); if(!r.ok){ b.disabled=false; snack(r.message); return; }
  renderSettings(); snack(`${name}: back to its default`); });
const chg=/** @type {HTMLInputElement} */($("#setChanged")); if(chg) chg.onchange=()=>{ CHANGED=chg.checked; changedOnly.value=CHANGED; if(CHANGED&&!catalogue.value&&SERVED) loadCatalogue(); renderSettings(); $("#v-settings").scrollTop=0; };
/* when the catalogue arrives or changes: the older cards' dots follow; Show changed only and a search redraw, as their sections
   may change (a search typed before the catalogue arrived found nothing in Essentials or Everything else) */
effect(()=>{ const c=catalogue.value; if(!c||shared.VIEW!=="settings") return;
  if((CHANGED||shared.SQ.trim())&&!$("#settingsBody").contains(document.activeElement)) renderSettings(); else setMark($("#settingsBody")); });
/* the rail's count needs a recent check: one a minute after start-up when this browser hasn't checked for a day */
if(SERVED&&Date.now()-lastCheckAt()>24*3600*1000) window.setTimeout(()=>{ if(viaServer()) checkHealth(); },60*1000);
}
export const setCard=s=>s.mount?`<div class="setmount" id="set-${s.id}" data-sec="${s.id}" data-mount></div>`:s.raw?s.render():`<div class="card${s.wide?" wide":""}" id="${s.elid||"set-"+s.id}" data-sec="${s.id}"><h2>${s.title}</h2>${s.render()}</div>`;
export const catName=id=>(SETCATS.find(c=>c[0]===id)||[])[1]||"";
/* Search: sections and rows whose label, help text or keywords hold every word typed, across all categories. A section
   whose title or category matches shows all its rows; otherwise it shows just the rows that match, or all of them when
   only its keywords matched (for example "ignore rules" or "diagnostics"). A mounted section answers for itself (`match`).
   Show changed only (BL-320) narrows the same way to the rows with the dot, in Essentials and Advanced. */
export const sqWords=()=>shared.SQ.toLowerCase().split(/\s+/).filter(Boolean), sqHas=(txt,w)=>w.every(x=>txt.toLowerCase().includes(x));
export const rowText=r=>(r.classList.contains("srow")&&r.firstElementChild&&r.firstElementChild!==r.lastElementChild?r.firstElementChild:r).textContent;
export let SMATCH=new Set();
export const rowOK=(r,w)=>sqHas(rowText(r),w)&&(!CHANGED||r.classList.contains("chg"));
export function setSearchSections(){ const w=sqWords(); SMATCH=new Set(); const t=document.createElement("div");
  return SETSECTIONS.filter(s=>{ if(CHANGED&&!["essentials","advanced"].includes(catOf(s))) return false;
    if(s.mount) return s.match(w);
    if(!CHANGED&&sqHas(`${s.title} ${catName(catOf(s))} ${OLDCATS[s.cat]||""}`,w)){ SMATCH.add(s.id); return true; }
    putHTML(t,raw(setCard(s))); setMark(t); const rows=[...t.querySelectorAll(".srow,.igrow")];
    return (!CHANGED&&sqHas(s.kw,w))||rows.some(r=>rowOK(r,w)); }); }
export function setApplySearch(){ if(!shared.SQ.trim()&&!CHANGED) return; const w=sqWords();
  $$("#settingsBody [data-sec]").forEach(c=>{ if(c.hasAttribute("data-mount")||SMATCH.has(c.dataset.sec)) return; const rows=[...c.querySelectorAll(".srow,.igrow")], hit=rows.filter(r=>rowOK(r,w));
    rows.forEach(r=>{ r.hidden=hit.length||CHANGED?!hit.some(h=>h===r||h.contains(r)):false; }); }); }      /* a row inside a matching row (the ignore rules) stays */
export let MOUNTS=[];
export function setUnmount(){ MOUNTS.forEach(el=>render(null,el)); MOUNTS=[]; }
export function renderSettings(){ if(!SETCATS.some(c=>c[0]===shared.SCAT)) shared.SCAT="essentials";
  const searching=!!shared.SQ.trim()||CHANGED;
  query.value=shared.SQ.trim(); changedOnly.value=CHANGED;
  const chg=/** @type {HTMLInputElement} */($("#setChanged")); if(chg) chg.checked=CHANGED;
  if(SERVED&&!catalogue.value) loadCatalogue();
  drawTabs($("#setcatsHost"),{id:"setcats",className:"setcats",label:"Settings categories",vertical:true,controls:"settingsBody",
    items:SETCATS.map(([id,t])=>({id,label:t,data:{scat:id}})),selected:searching?"":shared.SCAT,onSelect:setOpen});   /* BL-316: the Tabs block */
  putHTML($("#setcatsel"),raw((searching?`<option value="">${CHANGED&&!shared.SQ.trim()?"Changed settings":"Search results"}</option>`:"")+SETCATS.map(([id,t])=>`<option value="${id}" ${!searching&&id===shared.SCAT?"selected":""}>${esc(t)}</option>`).join("")));
  const secs=searching?setSearchSections():SETSECTIONS.filter(s=>catOf(s)===shared.SCAT);
  const head=s=>searching?(s.mount&&s.id!=="more"?"":`<div class="setcrumb">${esc(catName(catOf(s)))} › ${esc(s.id==="more"?OLDCATS.advanced:s.title)}</div>`)
    :shared.SCAT==="advanced"&&OLDCATS[s.cat==="advanced"?"advanced":s.cat]&&(s===secs.find(x=>x.cat===s.cat))?`<h2 class="setgroup">${esc(OLDCATS[s.cat])}</h2>`:"";
  setUnmount();
  const none=CHANGED&&!shared.SQ.trim()?(catalogue.value?"Nothing is changed from its default.":"Reading your settings…"):`No settings match “${shared.SQ.trim()}”${CHANGED?" among the changed ones":""}.`;
  putHTML($("#settingsBody"),!secs.length?html`<p class="sub setnone" role="status">${none}</p>`:html`<div class="setstack">${raw(secs.map(s=>head(s)+setCard(s)).join(""))}</div>`);
  secs.forEach(s=>{ if(s.mount){ const el=document.getElementById("set-"+s.id); if(el){ MOUNTS.push(el); s.mount(el); } } else if(s.after) s.after(); });
  setMark($("#settingsBody"));
  setApplySearch();
  const b=id=>document.getElementById(id);
  if(b("rzReset")) b("rzReset").onclick=()=>{ shared.RZ={}; store.set("creaite-colwidths",shared.RZ); shared.COLORD={}; store.set("creaite-colorder",shared.COLORD); snack("Column widths and order reset"); };
  if(b("remRestore")) b("remRestore").onclick=async()=>{ if(!await writeSettings({"reminders.dismissed_forever":[]})) return; store.set("creaite-dismiss",[]); if(D.dismissed) D.dismissed.length=0;   /* BL-157: the set-up checklist comes back at once */ sessionStorage.removeItem("creaite-dismiss-s"); snack("Dismissed reminders restored"); };
  if(b("liveCheck")) b("liveCheck").onclick=()=>{ setLive(true); renderSettings(); };
  if(b("liveStop")) b("liveStop").onclick=async()=>{ if(!viaServer()){ snack("The live server isn't running"); return; } const r=await api("/api/stop",{}); if(r.ok){ snack("Live server stopped"); setTimeout(()=>setLive(false),600); } else snack(oneLine(r.message)); };
  if(SECT){ const c=document.querySelector(`#settingsBody [data-sec="${SECT}"]`); SECT=null; if(c) c.scrollIntoView({block:"start"}); }
  showSaved(); }
/* ===== end BL-320 ===== */
export const setOpen=t=>{ go("settings",t); };      /* the one way in: sets the category and writes the address */
export const setSearch=q=>{ shared.SQ=q; renderSettings(); $("#v-settings").scrollTop=0; };      /* the results start at the top: that is the jump to the match */
/* a quiet "Saved" beside the row that was just changed. The row is noted when it changes; writeSettings (every setting
   goes through it) or a client-report rhythm then marks it, and a page that redraws straight after still shows it. */
export let SETFLASH=null; shared.SETROW=null;
export function savedNow(){ if(shared.SETROW&&Date.now()-shared.SETROW.at<15000){ SETFLASH={...shared.SETROW,at:Date.now()}; showSaved(); } shared.SETROW=null; }
export function showSaved(){ if(!SETFLASH) return; const left=2500-(Date.now()-SETFLASH.at); if(left<=0){ SETFLASH=null; return; }
  const c=document.querySelector(`#settingsBody [data-sec="${SETFLASH.sec}"]`), r=c&&!c.hasAttribute("data-mount")&&c.querySelectorAll(".srow,.igrow")[SETFLASH.i]; if(!r) return;
  $$("#settingsBody .saved").forEach(x=>x.remove());
  addHTML((r.classList.contains("srow")?r.lastElementChild:r),r.classList.contains("srow")?"afterbegin":"beforeend",html`<span class="saved" role="status">${raw(MTICK)}Saved</span>`);
  setTimeout(()=>$$("#settingsBody .saved").forEach(x=>x.remove()),left); }
/* BL-36: creaite version and updates. update.py does the work through the live server; the page names a source
   ("releases" or "downloads"), never a path. Nothing installs without the second, confirming click. */
export const vnum=v=>String(v||"0.0.0").split(".").reduce((a,x)=>a*1000+Number(x||0),0);
export const fdt=at=>at?`${fd(at.slice(0,10))} ${at.slice(11,16)}`:"";
export async function drawUpdates(){ const c=document.getElementById("updCard"); if(!c) return;
  if(!viaServer()){ putHTML(c,html`<h2>creaite version</h2><p class="sub">Needs the live server.</p>`); return; }
  const r=await api("/api/update/status"); if(!document.getElementById("updCard")) return;
  if(!r.ok){ putHTML(c,html`<h2>creaite version</h2><p class="sub">${(r.message||"Couldn't read the version.")}</p>`); return; }
  const src=r.releases&&(!r.downloads||vnum(r.releases.version)>=vnum(r.downloads.version))?"releases":(r.downloads?"downloads":null);
  const z=src&&r[src], newer=!!z&&vnum(z.version)>vnum(r.installed);
  const where=src==="releases"?"system/releases":"Downloads";
  putHTML(c,html`<h2>creaite version</h2>${raw(row("Installed",esc(r.installed==="0.0.0"?"Not set":r.installed)))}${r.dev
    ?html`<p class="sub" style="margin:6px 0 0">Development repository: updates are made with git here, not installed.</p>`:html`${raw(row("Update",newer?`<button class="btn primary" id="updReview">Review ${esc(z.version)}</button>`:'<span class="sub">Up to date</span>',newer?`${esc(z.name)} in ${where}`:"Save a creaite-X.Y.Z.zip from GitHub in system/releases"))}${raw(row("Install from a file",`<button class="btn" id="updFile">Choose zip…</button><input type="file" id="updPick" accept=".zip" hidden>`,"The creaite-X.Y.Z.zip attached to the release, not “Source code (zip)”"))}${r.last?raw(row(`Last update: ${esc(r.last.from)} → ${esc(r.last.to)}`,'<button class="btn" id="updUndo">Undo update</button>',fdt(r.last.at))):""}`}<div id="updPlan"></div>`);
  const b=id=>document.getElementById(id);
  if(b("updReview")) b("updReview").onclick=()=>updReview(src,false);
  if(b("updFile")) b("updFile").onclick=()=>b("updPick").click();
  if(b("updPick")) b("updPick").onchange=e=>updUpload(e.target.files[0]);
  if(b("updUndo")) b("updUndo").onclick=e=>updUndo(e.currentTarget,false); setApplySearch(); }
export function updOut(html){ const o=document.getElementById("updPlan"); if(o) putHTML(o,raw(html)); }
export const updMsg=(m,bad)=>`<pre class="sub" style="white-space:pre-wrap;margin:8px 0 0;${bad?"color:var(--bad)":""}">${esc(m||"")}</pre>`;
export async function updUpload(f){ if(!f) return;
  if(!/^creaite-\d+\.\d+\.\d+\.zip$/.test(f.name)){ updOut(updMsg("Choose the creaite-X.Y.Z.zip attached to the release, not GitHub's “Source code (zip)”.",true)); return; }
  updOut('<p class="sub">Copying to system/releases…</p>');
  const data=await new Promise((ok,no)=>{ const rd=new FileReader(); rd.onload=()=>ok(String(rd.result).split(",")[1]||""); rd.onerror=no; rd.readAsDataURL(f); });
  const r=await api("/api/update/upload",{name:f.name,data}); if(!r.ok){ updOut(updMsg(r.message,true)); return; }
  await drawUpdates(); updReview("releases",false); }
export async function updReview(source,reinstall){ updOut('<p class="sub">Checking the release…</p>');
  const r=await api("/api/update/inspect",{source,reinstall}); if(!r.ok){ updOut(updMsg(r.message,true)); return; }
  const p=r.plan, n=(a,w)=>`${a.length} ${w}${a.length===1?"":"s"}`, adds=Object.entries(p.settings||{});
  updOut(`<div style="border-top:1px solid var(--line);margin-top:8px;padding-top:8px;font-size:13px">
    <b>creaite ${esc(p.from)} → ${esc(p.to)}</b>${p.released?` <span class="sub">released ${esc(p.released)}</span>`:""}
    ${p.notes?`<div class="relnotes" style="margin:6px 0">${mdView(p.notes,{hBase:2})}<button type="button" class="mini" id="updNotesCopy">Copy the notes</button></div>`:""}
    <div class="sub">${n(p.replaced,"file")} replaced, ${p.added.length} added, ${p.removed.length} removed${p.removed.length?`: ${esc(p.removed.join(", "))}`:""}.</div>
    ${p.left.length?`<div class="sub">Left in place (yours, not from a release): ${esc(p.left.join(", "))}</div>`:""}
    ${adds.map(([f,a])=>`<div class="sub">${esc(f)} gains: ${esc(a.join(", "))}</div>`).join("")}
    <div class="sub" style="margin-top:4px">Your CLAUDE.md and all data are kept; everything is backed up first and rolls back if a step fails.</div>
    <div style="display:flex;gap:8px;margin-top:8px"><button class="btn primary" id="updGo">Install creaite ${esc(p.to)}</button><button class="btn" id="updCancel">Cancel</button></div></div>`);
  document.getElementById("updCancel").onclick=()=>updOut("");
  const nc=document.getElementById("updNotesCopy"); if(nc) nc.onclick=()=>(navigator.clipboard?navigator.clipboard.writeText(p.notes):Promise.reject()).then(()=>{ copied(nc); snack("Copied"); },()=>snack("Couldn't copy"));   /* BL-196: the original text */
  document.getElementById("updGo").onclick=async e=>{ e.currentTarget.disabled=true; e.currentTarget.textContent="Installing…";
    const res=await api("/api/update/install",{source,reinstall});
    await drawUpdates(); updOut(updMsg(res.message,!res.ok)); snack(res.ok?`creaite ${p.to} installed; restart the live server`:"The update didn't install"); }; }
export async function updUndo(btn,keep){ if(!btn.dataset.armed){ btn.dataset.armed="1"; btn.textContent="Confirm undo"; btn.classList.add("danger"); return; }
  btn.disabled=true; const r=await api("/api/update/undo",{keep_database:keep});
  if(!r.ok&&/--keep-database/.test(r.message||"")){ updOut(updMsg("The database has changed since the update; undoing it would lose those changes.",true)+'<div style="margin-top:8px"><button class="btn" id="updKeep">Undo engine and settings only</button></div>');
    document.getElementById("updKeep").onclick=e=>{ e.currentTarget.dataset.armed="1"; updUndo(e.currentTarget,true); }; btn.disabled=false; return; }
  await drawUpdates(); updOut(updMsg(r.message,!r.ok)); if(r.ok) snack("Update undone; restart the live server"); }
export function renderMgr(kind){ if(kind==="ws"&&D.ws_table&&(wsTable()||![...A,...R].some(x=>x.ws))){ drawWsMgr(); return; }   /* not yet migrated: BL-57's lists */
  const isP=kind==="people", L=isP?PEOPLE:WSL; const names=isP?[...new Set([...A.map(a=>a.o),...R.map(r=>r.o),...L.added,...L.hidden])].filter(n=>n&&n!=="TBC"):[...new Set([...wsUsed(),...L.added.filter(k=>k.includes("|")),...L.hidden.filter(k=>k.includes("|"))])];
  const on=(x,k)=>{ const [pc,nm]=wsParts(k); return x.p===pc&&x.ws===nm; };
  const active=isP?peopleAll():null; const cA=n=>isP?A.filter(a=>a.o===n).length:A.filter(a=>on(a,n)).length, cR=n=>isP?R.filter(r=>r.o===n).length:R.filter(r=>on(r,n)).length;
  const label=n=>isP?esc(n):(([pc,nm])=>`<span class="pcode">${esc(pc)}</span> ${esc(nm)}`)(wsParts(n)), off=n=>isP?L.hidden.includes(n):wsHidden(...wsParts(n));
  // @ts-expect-error TS2556: wsParts(n) is always [code, name]
  const mergeTo=n=>isP?active.filter(x=>x!==n):((pc,nm)=>wsFor(pc).filter(x=>x!==nm).map(x=>wsKey(pc,x)))(...wsParts(n));
  putHTML($(isP?"#peopleMgr":"#wsMgr"),html`<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap"><h2 style="flex:1">${isP?"People (owners)":"Workstreams"}</h2>${isP?"":html`<select id="wsAddP" aria-label="Project">${P.map(p=>html`<option value="${p.code}">${p.name}</option>`)}</select>`}<input id="${raw(kind)}Add" type="text" placeholder="${isP?"Add a person":"Add a workstream"}" style="height:32px;border:1px solid var(--line);border-radius:6px;padding:0 10px"><button class="btn" data-mg="add" data-kind="${raw(kind)}">Add</button></div>
   <p class="sub" style="margin:4px 0 8px">${isP?"Rename or merge to fix spellings across every item (applied with Undo). Removing hides a name from the owner picker; items keep it.":html`Each project has its own workstreams. Rename or merge changes that project's items only (you'll be offered the same change in other projects using the name). Retiring hides it from that project's picker; items keep it.`}</p>
   <div class="tbl"><table class="mgr"><thead><tr><th>${isP?"Name":"Workstream"}</th><th class="num">Actions</th><th class="num">RAID</th><th></th></tr></thead><tbody>${raw(names.sort().map(n=>{ const isOff=off(n), me=isP&&isMe(n);
    return `<tr class="${isOff?"off":""}"><td>${label(n)}${me?' <span class="tag">(you)</span>':""}${isOff?` <span class="tag warn">${isP?"removed from list":"retired"}</span>`:""}</td><td class="num">${mgrLink(isP,n,"actions",cA(n))}</td><td class="num">${mgrLink(isP,n,"raid",cR(n))}</td><td class="mgract">${me?'<span class="x">Change in Settings › Essentials › You</span>':`${ibtn("type","Rename",`data-mg="ren" data-kind="${kind}" data-n="${esc(n)}"`,"sm")}<select class="mgsel" data-kind="${kind}" data-n="${esc(n)}"><option value="">Merge into…</option>${mergeTo(n).map(x=>`<option value="${esc(x)}">${esc(isP?x:wsParts(x)[1])}</option>`).join("")}</select>${isOff?ibtn("undo","Restore",`data-mg="restore" data-kind="${kind}" data-n="${esc(n)}"`,"sm"):ibtn("trash",isP?"Remove from list":"Retire",`data-mg="hide" data-kind="${kind}" data-n="${esc(n)}"`,"sm no")}`}</td></tr>`; }).join(""))}</tbody></table></div>`); }
/* BL-190 (sprint-links): Settings › People (and the older Workstreams list, before BL-57's table) count every item, any status, with that
   owner or workstream; each figure opens Work so. The Workstreams table's Open column mixes actions and RAID items and stays plain. */
export function mgrLink(isP,k,t,c){ const w=t==="actions"?"action":"RAID item";
  if(isP) return countLink(`${plur(c,w)} owned by ${k}, any status`,c,`${t}:open:`,{st:[],o:[k]});
  const [pc,nm]=wsParts(k); return countLink(`${plur(c,w)} in the ${nm} workstream of ${pName(pc)}, any status`,c,`${t}:open:${pc}`,{st:[],ws:[nm]}); }
export async function renameAll(kind,from,to,also){ to=(to||"").trim(); const isP=kind==="people";
  if(!isP){ if(to.includes("|")) to=wsParts(to)[1]; return renameWs(from,to,also); }
  await renamePerson(from,to); renderSettings(); }   /* BL-55: people are in the register */
/* BL-57: a workstream rename or merge changes one project's items; other projects using the name are offered after */
export async function renameWs(key,to,also){ const [pc,nm]=wsParts(key); if(!to||to===nm) return; const touched=[], merge=wsFor(pc).includes(to);
  const items=[...A.map(x=>["actions",x]),...R.map(x=>["raid",x])].filter(([,x])=>x.p===pc&&x.ws===nm).map(([t,x])=>({op:"update",table:t,id:x.id,changes:{workstream:to},based_on:x.updated_at}));
  const keep=()=>{ if(!WSL.added.includes(wsKey(pc,to))) WSL.added.push(wsKey(pc,to)); WSL.added=WSL.added.filter(k=>k!==key); };
  if(!items.length){ keep(); WSL.hidden=[...new Set([...WSL.hidden,key])]; saveWs(); renderSettings(); }
  else await save(`${merge?"Merged":"Renamed"} ${pc} workstream “${nm}” ${merge?"into":"to"} “${to}”`,items,null,()=>{ [...A,...R].forEach(x=>{ if(x.p===pc&&x.ws===nm){ x.ws=to; touched.push(x); } }); keep(); saveWs(); },
    ()=>{ touched.forEach(x=>{ x.ws=nm; }); });
  renderSettings();
  const others=also===false?[]:[...new Set([...A,...R].filter(x=>x.p!==pc&&x.ws===nm).map(x=>x.p))];
  if(others.length) snack(`${pc} done. ${others.join(", ")} also ${others.length===1?"has":"have"} “${nm}”.`,async()=>{ for(const o of others) await renameWs(wsKey(o,nm),to,false); },`Also rename in ${others.join(", ")}`); }
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootSettings0078(){
$("#setcatsel").onchange=e=>{ if(e.target.value) setOpen(e.target.value); };
$("#setq").oninput=e=>setSearch(e.target.value);
$("#setq").onkeydown=e=>{ if(e.key==="Escape"&&shared.SQ){ e.stopPropagation(); e.target.value=""; setSearch(""); } };
$("#settingsBody").addEventListener("change",e=>{ const r=mounted(e.target)?null:e.target.closest(".srow,.igrow"), c=r&&r.closest("[data-sec]");
  shared.SETROW=c?{sec:c.dataset.sec,i:[...c.querySelectorAll(".srow,.igrow")].indexOf(r),at:Date.now()}:null; },true);
$("#settingsBody").addEventListener("change",async e=>{ const el=e.target; if(el.dataset.rhythm){ const p=P.find(x=>x.code===el.dataset.rhythm), was=p.rhythm; if(await setRhythm(p.code,el.value)){ p.rhythm=el.value; snack(`Saved to ${p.name}'s CLAUDE.md`); savedNow(); } else el.value=was; return; } const k=el.dataset.k; if(!k||!SKEY[k]) return;
  let v=el.type==="checkbox"?el.checked:el.type==="number"?Number(el.value):el.value; if((k==="sweepDue"||k==="weeklyTime")&&!/^\d{2}:\d{2}$/.test(v)){ snack("Use 24-hour HH:MM"); el.value=S[k]; return; }
  const was=S[k]; if(!await writeSettings({[SKEY[k]]:k==="short"?String(v).split(",").map(x=>x.trim()).filter(Boolean):k==="ownDomains"?(v=String(v).split(",").map(x=>x.trim().toLowerCase()).filter(Boolean)):v})){ if(el.type==="checkbox") el.checked=!!was; else el.value=was; return; }
  S[k]=v; if(k==="theme"||k==="palette"){ themeFade(); applyTheme(); } if(k==="motion") applyMotion(); if(k==="palette") renderSettings(); if(k==="autoApply") renderSettings(); if(k==="filesDocs") refreshFiles(true); if(k==="flowWeeks") reloadData(); if(k==="showArchived") reloadData().then(()=>renderSettings());   /* BL-09 */ status(); snack("Saved to settings.json"); });
/* BL-302: the Workstreams list only. Settings › People has its own buttons (data-pm, below), saved to the register since BL-55,
   which removed savePeople; a data-mg button for people is no longer drawn, so one is ignored rather than throwing. */
$("#settingsBody").addEventListener("click",e=>{ const b=e.target.closest("[data-mg]"); if(!b) return; const kind=b.dataset.kind; if(kind!=="ws") return; const isP=false, L=WSL, save=saveWs, n=b.dataset.n;
  if(b.dataset.mg==="add"){ let v=$("#"+kind+"Add").value.trim(); if(!v) return; if(!isP) v=wsKey($("#wsAddP").value,v); L.added.push(v); L.hidden=L.hidden.filter(x=>x!==v); save(); renderSettings(); snack(`Added “${isP?v:wsParts(v).join(" · ")}”`); }
  if(b.dataset.mg==="hide"){ L.hidden.push(n); save(); renderSettings(); snack(isP?`Removed “${n}” from the owner list`:`Retired ${wsParts(n).join(" · ")}`,()=>{ L.hidden=L.hidden.filter(x=>x!==n); save(); renderSettings(); }); }
  if(b.dataset.mg==="restore"){ L.hidden=L.hidden.filter(x=>x!==n&&(isP||x!==wsParts(n)[1])); save(); renderSettings(); }
  if(b.dataset.mg==="ren"){ const td=b.closest("tr").cells[0]; putHTML(td,html`<span style="display:flex;gap:6px"><input type="text" value="${(isP?n:wsParts(n)[1])}" style="height:30px;border:1px solid var(--faint);border-radius:6px;padding:0 8px"><button class="mini ok">Save</button><button class="mini">Cancel</button></span>`); const inp=td.querySelector("input"); inp.focus(); inp.select(); const [ok,cn]=td.querySelectorAll("button");
    ok.onclick=()=>renameAll(kind,n,inp.value); cn.onclick=()=>renderSettings(); inp.onkeydown=ev=>{ if(ev.key==="Enter") renameAll(kind,n,inp.value); if(ev.key==="Escape"){ ev.stopPropagation(); renderSettings(); } }; } });
$("#settingsBody").addEventListener("change",e=>{ const s=e.target.closest("select.mgsel"); if(s&&s.value){ e.stopPropagation(); renameAll(s.dataset.kind,s.dataset.n,s.value); } },true);
}
/* ===== People (BL-55, BL-56) ===== */
/* BL-55: the people register, projects/_portfolio/people-register.md. It is edited only through proposals (file changes), so
   every change is logged and undoable. The file format and the matching rules are propose.py's; dev/tests/test_people_dashboard.py
   checks the two agree. A name is mapped to a full name only on an exact match (full name, alias or email); a likely match
   is offered, never used. */
export const PCOLS=["Full name","Email","Aliases","Organisation","Role","Hidden","Labels"], PFIELD={"Full name":"name","Email":"email","Aliases":"aliases","Organisation":"org","Role":"role","Hidden":"hidden","Labels":"labels"};
export const pKey=t=>String(t||"").replace(/\([^)]*\)/g," ").toLowerCase().replace(/[.,]/g," ").split(/\s+/).filter(Boolean).join(" ");
export const pCell=v=>String(v??"").replace(/\|/g,"/").replace(/\n/g," ").trim();
export const pSplit=line=>line.trim().replace(/^\|+|\|+$/g,"").split("|").map(c=>c.trim());
export function pTable(lines){ const at=lines.indexOf("## People"); if(at<0) return null; let i=at+1; while(i<lines.length&&!lines[i].startsWith("|")){ if(lines[i].startsWith("## ")) return null; i++; } if(i>=lines.length) return null;
  const head=i, rows=[]; i+=2; while(i<lines.length&&lines[i].startsWith("|")) rows.push(i++); return {head,rows}; }
export function peopleParse(text){ const lines=text.split("\n"), t=pTable(lines); if(!t) return []; const cols=pSplit(lines[t.head]), out=[];
  for(const i of t.rows){ const cells=pSplit(lines[i]), row={}; cols.forEach((c,j)=>{ row[c]=cells[j]||""; }); if(!(row["Full name"]||"").trim()) continue;
    const extra={}; cols.forEach(c=>{ if(!(c in PFIELD)) extra[c]=row[c]; });
    out.push({name:row["Full name"].trim(),email:(row["Email"]||"").trim(),aliases:(row["Aliases"]||"").split(",").map(a=>a.trim()).filter(Boolean),org:(row["Organisation"]||"").trim(),role:(row["Role"]||"").trim(),
      hidden:["yes","y","true","1"].includes((row["Hidden"]||"").trim().toLowerCase()),labels:(row["Labels"]||"").split(",").map(a=>a.trim()).filter(Boolean),extra}); }
  return out; }
export function peopleText(text,people){ const lines=text.split("\n"); if(lines[lines.length-1]==="") lines.pop(); const t=pTable(lines);
  let cols=t?pSplit(lines[t.head]):[]; cols=[...cols,...PCOLS.filter(c=>!cols.includes(c))]; people.forEach(p=>Object.keys(p.extra||{}).forEach(c=>{ if(!cols.includes(c)) cols.push(c); })); cols=[...new Set(cols)];
  const cell=(p,c)=>{ const f=PFIELD[c]; return f==="aliases"||f==="labels"?pCell((p[f]||[]).join(", ")):f==="hidden"?(p.hidden?"yes":""):pCell(f?p[f]:(p.extra||{})[c]); };
  const row=a=>"| "+a.join(" | ")+" |", table=[row(cols),"|"+cols.map(c=>"-".repeat(c.length+2)).join("|")+"|",...people.map(p=>row(cols.map(c=>cell(p,c))))];
  if(t){ const end=(t.rows.length?t.rows[t.rows.length-1]:t.head+1)+1; lines.splice(t.head,end-t.head,...table); }
  else if(lines.includes("## People")){ lines.splice(lines.indexOf("## People")+1,0,"",...table); }
  else lines.push("","## People","",...table);
  return lines.join("\n")+"\n"; }
export const lev=(a,b)=>{ let prev=Array.from({length:b.length+1},(_,i)=>i); for(let i=1;i<=a.length;i++){ const cur=[i]; for(let j=1;j<=b.length;j++) cur.push(Math.min(prev[j]+1,cur[j-1]+1,prev[j-1]+(a[i-1]!==b[j-1]?1:0))); prev=cur; } return prev[b.length]; };
/* the register, Alan (his name and short forms), and the names on items that aren't registered */
export function personPool(){ const me={name:S.me,email:"",aliases:S.short.split(",").map(x=>x.trim()).filter(Boolean),hidden:false,me:true}, mine=shared.REG.find(p=>pKey(p.name)===pKey(me.name));
  const pool=mine?shared.REG.map(p=>p===mine?{...p,aliases:[...new Set([...p.aliases,...me.aliases])]}:p):[...shared.REG,me], reg=new Set(pool.map(p=>pKey(p.name)));
  const others=[...new Set([...A.map(a=>a.o),...R.map(r=>r.o),...DEC.map(d=>d.by),...PEOPLE.added].filter(n=>n&&n!=="TBC"))].filter(n=>!reg.has(pKey(n))).sort(); return {pool,others}; }
/* {status: known | alias | email (name is the full name) | likely (candidates only) | unknown}; built once for bulk use */
export function resolver(){ const {pool,others}=personPool(), forms=[...pool.map(p=>[p.name,[p.name,...p.aliases]]),...others.map(n=>[n,[n]])];
  return text=>{ const raw=String(text||"").trim(), k=pKey(raw), out={input:raw,status:"unknown",name:null,candidates:[]}; if(!k) return out;
    for(const p of pool) if(pKey(p.name)===k) return {...out,status:"known",name:p.name,registered:true};
    for(const p of pool) if(p.aliases.some(a=>pKey(a)===k)) return {...out,status:"alias",name:p.name};
    if(raw.includes("@")) for(const p of pool) if(String(p.email||"").split(/[,;]/).some(e=>e.trim().toLowerCase()===raw.toLowerCase())) return {...out,status:"email",name:p.name};   /* several addresses (BL-99) */
    for(const n of others) if(pKey(n)===k) return {...out,status:"known",name:n,registered:false};
    const toks=raw.includes("@")?pKey(raw.split("@")[0].replace(/[._-]/g," ")):k, tt=toks.split(" ").filter(Boolean), scored=[];
    for(const [name,fs] of forms){ let best=0; for(const f of fs){ const fk=pKey(f), ft=fk.split(" ").filter(Boolean); if(!ft.length||!tt.length) continue;
        if(tt.every(t=>t.length>=2)&&tt.every(t=>ft.includes(t))) best=Math.max(best,3);
        else if(tt.length>=2&&ft.length>=2&&ft[0].startsWith(tt[0])&&ft.slice(1).some(w=>w.startsWith(tt[tt.length-1]))) best=Math.max(best,3);
        else if(/^\p{L}+$/u.test(toks)&&toks.length>=2&&toks.length<=4&&toks===ft.map(w=>w[0]).join("")) best=Math.max(best,2);
        else if(Math.min(toks.length,fk.length)>=4&&lev(toks,fk)<=(toks.length<10?1:2)) best=Math.max(best,1); }
      if(best) scored.push([best,name]); }
    scored.sort((a,b)=>b[0]-a[0]||(a[1]<b[1]?-1:a[1]>b[1]?1:0)); out.candidates=[...new Set(scored.map(s=>s[1]))].slice(0,3); if(out.candidates.length) out.status="likely"; return out; }; }
export const resolvePerson=t=>resolver()(t);
export function personOf(n){ if(!n||n==="TBC") return n; const r=resolvePerson(n); return r.name||n; }
export const isHiddenPerson=n=>{ const c=personOf(n); return PEOPLE.hidden.includes(n)||shared.REG.some(p=>p.hidden&&(p.name===c||p.name===n)); };
/* an owner the register doesn't know: shown in Review (flagged; never guessed or mapped) */
export const unknownOwner=o=>{ if(!o||o==="TBC"||!(REGD.exists||shared.REG.length)) return false; const s=resolvePerson(o).status; return s==="likely"||s==="unknown"; };

/* writing the register: one proposal holding the changed file (and, for a rename or merge, the items too) */
export let REGTEXT=(D.people_register||{}).text||"";   /* the file as last known: when it was built, then as this page last wrote it */
export let REGPEND=null;   /* the file's text when an edit of this page is still waiting to be applied (null: none). While the file still holds it, the next edit builds on REGTEXT, so edits chain and none overwrites another */
export async function regSave(what,mutate,items,doIt,undoIt){ if(!await needVault()) return false; let text, exists=true, disk=null;
  try{ disk=await vq(()=>shared.VW.read(REGD.path)); }catch(e){ disk=null; }
  const chained=disk!==null&&REGPEND!==null&&disk===REGPEND&&!!REGTEXT;
  if(disk!==null) text=chained?REGTEXT:disk;
  else if(REGD.exists&&REGTEXT) text=REGTEXT;   /* a file that exists but can't be read here is edited from the last known text; apply checks it hasn't changed */
  else{ text=REGD.template; exists=false; }
  const next=mutate(peopleParse(text)), content=peopleText(text,next), before=shared.REG;
  if(exists&&content===text) return true;
  const extra={file_changes:{title:what,project:null,file_changes_decision:"approved",file_ops:[{op:"write",path:REGD.path,content,previous:exists?text:null}]}};
  const was=REGTEXT, wasPend=REGPEND, ok=await save(what,items||[],extra,()=>{ shared.REG=next.map(p=>({...p})); REGD.exists=true; REGTEXT=content; REGPEND=chained?REGPEND:disk; if(doIt) doIt(); },()=>{ shared.REG=before; REGTEXT=was; REGPEND=wasPend; if(undoIt) undoIt(); });
  if(ok){ try{ if(await vq(()=>shared.VW.read(REGD.path))===content) REGPEND=null; }catch(e){} }   /* applied: the file holds it now, so the next edit starts from the file */
  if(ok&&shared.VIEW==="settings") renderSettings(); return ok; }
export const pBlank=n=>({name:n,email:"",aliases:[],org:"",role:"",hidden:false,extra:{}});
export const pFind=(list,n)=>list.find(p=>pKey(p.name)===pKey(n));
export const regAddPerson=p=>regSave(`Added ${p.name} to the people register`,L=>[...L,{...pBlank(p.name),...p,extra:{}}]);
export const regAddAlias=(name,alias)=>regSave(`Remembered “${alias}” as ${name}’s alias`,L=>{ let r=pFind(L,name); if(!r){ r=pBlank(name); L.push(r); } if(!r.aliases.some(a=>pKey(a)===pKey(alias))) r.aliases.push(alias); return L; });
export const regSetHidden=(name,hidden)=>regSave(hidden?`Removed ${name} from the owner list`:`Restored ${name} to the owner list`,L=>{ let r=pFind(L,name); if(!r){ r=pBlank(name); L.push(r); } r.hidden=hidden; return L; });
export const regEdit=(name,f)=>regSave(`Changed ${name} in the people register`,L=>{ let r=pFind(L,name); if(!r){ r=pBlank(name); L.push(r); } Object.assign(r,f); return L; });
/* rename: a plain rename, or a merge when the new name is already someone (the old name becomes an alias); every item follows */
export async function renamePerson(from,to){ from=String(from).trim(); to=String(to||"").trim(); if(!to||to===from) return false; const upd=[], tou=[];
  const merge=!!pFind(shared.REG,to)&&pKey(to)!==pKey(from); const dest=merge?pFind(shared.REG,to).name:to;
  [["actions",A,"owner","o"],["raid",R,"owner","o"],["decisions",DEC,"made_by","by"]].forEach(([t,arr,col,k])=>arr.filter(x=>x[k]===from).forEach(x=>{ upd.push({op:"update",table:t,id:x.id,changes:{[col]:dest},based_on:x.updated_at}); tou.push([x,k]); }));
  const what=`${merge?"Merged":"Renamed"} ${from} ${merge?"into":"to"} ${dest}`;
  return regSave(what,L=>{ const src=pFind(L,from), d=pFind(L,dest);
    if(src&&(!d||d===src)){ src.name=dest; return L; }
    if(src&&d){ ["email","org","role"].forEach(f=>{ d[f]=d[f]||src[f]; }); d.aliases=[...new Set([...d.aliases,src.name,...src.aliases])].filter(x=>pKey(x)!==pKey(d.name)); return L.filter(p=>p!==src); }
    if(d){ d.aliases=[...new Set([...d.aliases,from])].filter(x=>pKey(x)!==pKey(d.name)); return L; }
    return [...L,pBlank(dest)]; },upd,()=>{ tou.forEach(([x,k])=>{ x[k]=dest; }); },()=>{ tou.forEach(([x,k])=>{ x[k]=from; }); }); }

/* the new-person prompt: likely matches first ("Is “Sara” Sara Khan?"), otherwise the person's details. The name is
   required; email and aliases can be added later. Resolves {use, alias} (a match chosen), {person} (details), or null. */
export function askPerson(o){ const pr=new Promise(res=>{ const dlg=$("#personDlg"), cands=(o.candidates||[]).map(n=>pFind(personPool().pool,n)||{name:n,org:"",role:""}), typed=o.typed||"", p=o.person||{};
    const isMail=/@/.test(typed), set=(id,v)=>{ $("#pd_"+id).value=v||""; };     $("#pdTitle").textContent=o.edit?`Edit ${p.name}`:o.details?`Details for ${p.name}`:"New person";
    set("name",p.name||(isMail?"":typed)); set("email",p.email||(isMail?typed:"")); set("aliases",(p.aliases||[]).join(", ")); set("org",p.org); set("role",p.role);
    $("#pd_name").readOnly=!!(o.edit||o.details); $("#pdErr").textContent="";
    const showForm=()=>{ $("#pdMatch").hidden=true; $("#pdFields").hidden=false; $("#pdSave").hidden=false; $("#pd_name").focus(); };
    if(cands.length&&!o.edit&&!o.details){ $("#pdFields").hidden=true; $("#pdSave").hidden=true; $("#pdMatch").hidden=false;
      putHTML($("#pdMatch"),html`<p style="margin:0 0 8px">Is “${typed}” one of these?</p>${cands.map(c=>html`<button type="button" class="btn pdc" data-use="${c.name}">Yes, it’s ${c.name}${c.org||c.role?html` <small>${[c.org,c.role].filter(Boolean).join(" · ")}</small>`:""}</button>`)}
        <label class="sub" style="display:flex;gap:6px;align-items:center;margin:8px 0"><input type="checkbox" id="pdRemember" checked> Remember “${typed}” as an alias, so it maps next time</label><button type="button" class="btn" id="pdNew">No, add a new person</button>`); }
    else showForm();
    let done=false; const onClose=()=>{ if(!dlg.open) finish(null); },   /* Esc: cancelled. Chrome delivers "close" a frame late, so one from the last prompt can arrive while this one is open: ignore it */
      finish=v=>{ if(!done){ done=true; dlg.removeEventListener("close",onClose); res(v); } }, fin=v=>{ finish(v); if(dlg.open) dlg.close(); };
    $("#pdMatch").onclick=e=>{ const u=e.target.closest("[data-use]"); if(u) return fin({use:u.dataset.use,alias:$("#pdRemember").checked?typed:null}); if(e.target.closest("#pdNew")) showForm(); };
    $("#pdSave").onclick=()=>{ const f=id=>$("#pd_"+id).value.trim(), name=f("name"); if(!name){ $("#pdErr").textContent="A full name is required."; $("#pd_name").focus(); return; }
      if(!o.edit&&!o.details){ const r=resolvePerson(name); if(r.status==="alias"||r.status==="email"||(r.status==="known"&&r.registered)){ $("#pdErr").textContent=`${name} is already in the register as ${r.name}.`; return; } }
      const aliases=f("aliases").split(",").map(a=>a.trim()).filter(Boolean); if(typed&&!isMail&&!o.edit&&!o.details&&pKey(typed)!==pKey(name)&&!aliases.some(a=>pKey(a)===pKey(typed))) aliases.push(typed);   /* what was typed maps to them next time */
      fin({person:{name,email:f("email"),aliases,org:f("org"),role:f("role")}}); };
    $("#personForm").onsubmit=e=>{ if(e.submitter&&e.submitter.value==="cancel") return; e.preventDefault(); if(!$("#pdSave").hidden) $("#pdSave").click(); };
    dlg.addEventListener("close",onClose); $("#personForm [value=cancel]").onclick=e=>{ e.preventDefault(); fin(null); }; openDialog(dlg); });
  const keep=!!(o&&(o.edit||o.details)), cur=((o&&o.person&&o.person.extra)||{}).VIP||"";
    $$(".pdvip").forEach(el=>el.hidden=!keep); const sel=$("#pd_vip"); sel.value=[...sel.options].some(x=>x.value===cur.toLowerCase())?cur.toLowerCase():cur?"yes":"";
    return pr.then(res=>{ if(res&&res.person&&keep) res.person.extra={...((o.person&&o.person.extra)||{}),VIP:sel.value}; return res; }); }
/* an owner typed or picked: mapped to the full name if known, otherwise ask (matches first). null = cancelled */
export async function ownerFinal(typed,opt={}){ typed=String(typed||"").trim(); if(!typed||typed==="TBC") return typed||"TBC"; const r=resolvePerson(typed);
  if(r.status==="known"||r.status==="alias"||r.status==="email") return r.name;
  const res=await askPerson({typed,candidates:opt.skipMatch?[]:r.candidates}); if(!res) return null;
  if(res.use){ if(res.alias&&pKey(res.alias)!==pKey(res.use)&&!await regAddAlias(res.use,res.alias)) return null; return res.use; }
  return await regAddPerson(res.person)?res.person.name:null; }

/* Settings › People: the register, with each person's open work. Edit, rename, merge, remove from the owner list. */
export function renderPeopleMgr(){ pfLoad();
  putHTML($("#peopleMgr"),html`<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap"><h2 style="flex:1">People</h2><button class="btn" id="pmAdd" aria-haspopup="dialog">Add a person</button></div>
   <p class="sub" style="margin:4px 0 8px">Everyone who owns an item, with one full name each. Aliases and email addresses map to that name when minutes and mail are read; a name creaite doesn’t know is flagged in Review, never guessed. Rename or merge fixes spellings across every item (a merge keeps the old name as an alias). Removing hides a name from the owner picker; items keep it. Every change is saved as a proposal, with Undo.</p>
   ${PEOPLE.added.length||PEOPLE.hidden.length?html`<p class="sub" id="pmLegacy"><span class="tag warn">${PEOPLE.added.length+PEOPLE.hidden.length} name${PEOPLE.added.length+PEOPLE.hidden.length===1?"":"s"} still in settings.json</span> ${viaServer()?html`<button class="mini" data-ask="${PEOPLE_MOVE}">Move them into the register</button> <span class="sub">(ask creaite does it, asking first)</span>`:"Say “setup” in Claude Code to move them into the register."}</p>`:""}
   <div class="toolbar pmtools" role="search"><input id="pmQ" type="search" placeholder="Search name, alias, email or role" aria-label="Search people" autocomplete="off" value="${PF.q}"><span class="dd" id="pmFdd"></span></div>
   <div class="wapplied" id="pmApplied"></div><div class="vh" id="pmLive" role="status" aria-live="polite"></div>
   <div class="tbl"><table class="mgr"><thead><tr><th>Name</th><th>Email</th><th>Organisation · role</th><th>Aliases</th><th class="num" id="pmHA">Actions</th><th class="num" id="pmHR">RAID</th><th></th></tr></thead><tbody id="pmRows"></tbody></table></div>`);
  pfDraw(); }

/* ===== BL-264 (v19-people-filters) ===== Settings › People's filter, as Work's (BL-130, BL-132, BL-159): a search box, one funnel
   (F) with a picker (fields on the left in two groups, each field's choices with live counts on the right), chips for what is on,
   the count line with its hints, and Work's empty state. Fields: Project (from items and the register's stakeholders, D.stakeholders),
   How they're involved, Organisation, People I follow (the register's VIP column; never labelled "VIP", BL-288), In the register,
   Needs attention and Removed people. Ticks within a field are "any of", fields combine with "and"; Project and Organisation have
   "is not". Only fields and choices that exist in the data are offered. Removed people are hidden by default ("Removed: hidden").
   The filters are remembered until cleared (Alan, 12-10-2026), in this browser's storage as Work's remembered display choices are
   (store, "creaite-people-filters"); the search box is not. */
export const PF_KEY="creaite-people-filters", PF_MULTI=["proj","inv","org","vip","reg","att"], PF_REM=["hide","show","only"];
/** @type {{q:string, rem:string, neg:Set<string>, f:Object<string,Set<string>>, open?:boolean, pk:string, loaded:boolean}} */
export const PF={q:"",rem:"hide",neg:new Set(),f:Object.fromEntries(PF_MULTI.map(k=>[k,new Set()])),pk:"proj",loaded:false};
Object.defineProperty(PF,"open",{get:()=>filterBarOpen($("#pmFdd"))==="more"});   /* BL-316: whether the picker is open is the FilterBar's own state */

export function pfReset(){ PF_MULTI.forEach(k=>PF.f[k]=new Set()); PF.rem="hide"; PF.neg=new Set(); PF.q=""; }
export function pfLoad(){ if(PF.loaded) return; PF.loaded=true; const s=store.get(PF_KEY,null); if(!s||typeof s!=="object") return;
  PF_MULTI.forEach(k=>{ if(Array.isArray(s[k])) PF.f[k]=new Set(s[k].map(String)); });
  if(PF_REM.includes(s.rem)) PF.rem=s.rem; if(Array.isArray(s.neg)) PF.neg=new Set(s.neg.filter(k=>k==="proj"||k==="org")); }
export function pfSave(){ const o={rem:PF.rem,neg:[...PF.neg]}; PF_MULTI.forEach(k=>o[k]=[...PF.f[k]]); store.set(PF_KEY,o); }
/* everyone the table lists (the register, every owner and decision maker, the names still in settings.json), with what the filters read */
export function pfPeople(){ const rs=resolver(), canon=n=>rs(n).name||n, st=D.stakeholders||{};
  const names=[...new Set([...shared.REG.map(p=>p.name),...A.map(a=>a.o),...R.map(r=>r.o),...DEC.map(d=>d.by),...PEOPLE.added,...PEOPLE.hidden])].filter(n=>n&&n!=="TBC");
  return names.sort((a,b)=>a.localeCompare(b)).map(n=>{ const p=shared.REG.find(x=>x.name===n)||null, me=isMe(n), it={}, add=(c,i)=>{ if(!it[c]) it[c]=[0,0,0]; it[c][i]++; };
    A.forEach(a=>{ if(a.o===n) add(a.p,0); }); R.forEach(r=>{ if(r.o===n) add(r.p,1); }); DEC.forEach(d=>{ if(d.by===n) add(d.p,2); });
    const vk=p?String((p.extra||{}).VIP||"").trim():"";
    return {n,p,me,off:isHiddenPerson(n),reg:!!p||me,email:p&&p.email||"",org:p&&p.org||"",role:p&&p.role||"",aliases:p&&p.aliases||[],
      vip:!!vk&&!/^(no|n|false|0|-)$/i.test(vk),it,st:Object.keys(st).filter(c=>(st[c]||[]).some(s=>s===n||canon(s)===n))}; }); }
export const pfNoEmail=x=>!x.email&&!x.me, pfNoOrg=x=>!x.me&&(!x.org||!x.role);
export const pfProjOf=x=>[...new Set([...Object.keys(x.it),...x.st])];
export const pfScope=()=>PF.f.proj.size&&!PF.neg.has("proj")?[...PF.f.proj]:null;   /* the projects chosen (not "is not"), or null */
/* the fields offered: [key, label, group, choices [[value, label]], hit(person, value), hint]; a field with no choice is left out */
export function pfFields(L){ const has=f=>L.some(f), scope=()=>pfScope()||P.map(p=>p.code);
  return [
   ["proj","Project","Who",P.filter(p=>has(x=>pfProjOf(x).includes(p.code))).map(p=>[p.code,p.name]),(x,v)=>pfProjOf(x).includes(v),"Owns an action, RAID item or decision in it, or is one of its stakeholders in the project register."],
   ["inv","How they're involved","Who",[...(has(x=>Object.keys(x.it).length)?[["own","Owns items"]]:[]),...(has(x=>x.st.length)?[["stake","Named as a stakeholder"]]:[])],(x,v)=>v==="own"?scope().some(c=>x.it[c]):scope().some(c=>x.st.includes(c)),"In the projects chosen under Project, or in any project."],
   ["org","Organisation","Who",[...[...new Set(L.map(x=>x.org).filter(Boolean))].sort().map(o=>[o,o]),...(has(x=>!x.org)?[["—","No organisation"]]:[])],(x,v)=>v==="—"?!x.org:x.org===v,""],
   ["vip","People I follow","Who",has(x=>x.vip)?[["yes","Followed"],["no","Not followed"]]:[],(x,v)=>v==="yes"?x.vip:!x.vip,"Set in each person’s details."],
   ["reg","In the register","Tidy up",has(x=>!x.reg)?[["in","In the register"],["out","Not in the register (on items only)"]]:[],(x,v)=>v==="in"?x.reg:!x.reg,""],
   ["att","Needs attention","Tidy up",[...(has(pfNoEmail)?[["email","No email"]]:[]),...(has(pfNoOrg)?[["orgrole","No organisation or role"]]:[])],(x,v)=>v==="email"?pfNoEmail(x):pfNoOrg(x),"Details worth filling in, so mail and minutes map to the right person."],
   ["rem","Removed people","Tidy up",has(x=>x.off)?[["hide","Hidden"],["show","Shown with everyone"],["only","Removed only"]]:[],null,"Removed from the owner list; their items keep the name."]].filter(f=>f[3].length); }
export const pfRemOK=(x,r)=>r==="show"||(r==="only"?x.off:!x.off);
export const pfQOK=x=>{ const t=PF.q.trim().toLowerCase(); return !t||[x.n,x.email,x.role,...x.aliases].some(s=>s&&s.toLowerCase().includes(t)); };
/* does x show, skipping one field (or "q", the search)? Removed only narrows when the field is offered (someone is removed) */
export function pfPass(x,F,skip){ for(const f of F){ const k=f[0], set=PF.f[k]; if(k==="rem"||k===skip||!set||!set.size) continue; const h=[...set].some(v=>f[4](x,v)); if(PF.neg.has(k)?h:!h) return false; }
  if(skip!=="rem"&&F.some(f=>f[0]==="rem")&&!pfRemOK(x,PF.rem)) return false; return skip==="q"||pfQOK(x); }
export const pfOn=k=>k==="rem"?PF.rem!=="hide":!!(PF.f[k]&&PF.f[k].size);
export const pfDot=F=>F.filter(f=>f[0]==="rem"?PF.rem==="only":pfOn(f[0])).length;   /* the funnel counts what narrows the list beyond the default */
export const pfAny=F=>!!PF.q.trim()||F.some(f=>pfOn(f[0]));
export function pfChip(f){ const k=f[0], lab=v=>(f[3].find(o=>o[0]===v)||[v,v])[1];
  if(k==="rem") return PF.rem==="hide"?"Removed: hidden":PF.rem==="only"?"Removed only":"";
  const v=[...PF.f[k]]; return `${f[1]}: ${PF.neg.has(k)?"not ":""}${v.length<=2?v.map(lab).join(", "):v.length+" chosen"}`; }
export const pfWord=n=>`${n} ${n===1?"person":"people"}`;
/* the search's match marked in a cell's text */
export function pfHl(s){ s=String(s||""); const t=PF.q.trim(), i=t?s.toLowerCase().indexOf(t.toLowerCase()):-1;
  return i<0?html`${s}`:html`${s.slice(0,i)}<mark>${s.slice(i,i+t.length)}</mark>${s.slice(i+t.length)}`; }
/* a count: every item that person owns, any status (BL-190); with projects chosen, in those projects, and the link opens Work so */
export function pfLink(n,t,c,sc){ if(!sc) return mgrLink(true,n,t,c); const w=t==="actions"?"action":"RAID item";
  return countLink(`${plur(c,w)} owned by ${n} in ${sc.map(pName).join(", ")}, any status`,c,`${t}:open:${sc.length===1?sc[0]:""}`,sc.length===1?{st:[],o:[n]}:{st:[],o:[n],p:sc}); }
export function pfRow(x,sc,active){ const {n,p,me,off}=x, a=sc?sc.reduce((s,c)=>s+((x.it[c]||[])[0]||0),0):A.filter(i=>i.o===n).length, r=sc?sc.reduce((s,c)=>s+((x.it[c]||[])[1]||0),0):R.filter(i=>i.o===n).length;
  const via=sc&&!sc.some(c=>x.it[c])&&sc.some(c=>x.st.includes(c)), mergeTo=active.filter(y=>y!==n);
  return html`<tr class="${off?"off":""}" data-pn="${n}"><td>${pfHl(n)}${me?raw(' <span class="tag">(you)</span>'):""}${p||me?"":raw(' <span class="tag warn" title="On items but not in the register yet">not in register</span>')}${p&&!p.email?raw(' <span class="tag warn" title="Add email">no email</span>'):""}${off?raw(' <span class="tag warn">removed from list</span>'):""}${via?html`<span class="sub pmvia">named in the project’s stakeholders</span>`:""}</td>
     <td>${p&&p.email?pfHl(p.email):raw('<span class="sub">—</span>')}</td><td>${p&&(p.org||p.role)?html`${p.org||""}${p.org&&p.role?" · ":""}${pfHl(p.role)}`:raw('<span class="sub">—</span>')}</td><td class="sub">${p&&p.aliases.length?p.aliases.map((s,i)=>html`${i?", ":""}${pfHl(s)}`):"—"}</td>
     <td class="num">${raw(pfLink(n,"actions",a,sc))}</td><td class="num">${raw(pfLink(n,"raid",r,sc))}</td>
     <td class="mgract">${me?raw('<span class="x">Change in Settings › Essentials › You</span>'):html`${raw(ibtn("pencil",p?"Edit details":"Add details",`data-pm="edit" data-n="${esc(n)}" aria-haspopup="dialog"`,"sm"))}${raw(ibtn("type","Rename",`data-pm="ren" data-n="${esc(n)}"`,"sm"))}<select class="mgsel pmsel" data-n="${n}" aria-label="Merge ${n} into"><option value="">Merge into…</option>${mergeTo.map(y=>html`<option value="${y}">${y}</option>`)}</select>${raw(off?ibtn("undo","Restore",`data-pm="restore" data-n="${esc(n)}"`,"sm"):ibtn("trash","Remove from list",`data-pm="hide" data-n="${esc(n)}"`,"sm no"))}`}</td></tr>`; }
export function pfEmpty(L,F){ const act=F.filter(f=>f[0]==="rem"?PF.rem==="only":pfOn(f[0])).map(f=>({k:f[0],label:pfChip(f)}));
  if(PF.q.trim()) act.push({k:"q",label:`Search “${PF.q.trim()}”`});
  const ways=act.map(r=>({...r,n:L.filter(x=>pfPass(x,F,r.k)&&(r.k!=="rem"||!x.off)).length}));
  const head=act.length===1&&act[0].k==="q"?`Nobody matches “${esc(PF.q.trim())}”`:`Nobody matches ${act.length===1?"this filter":`these ${act.length} filters`}`;
  return relaxHtml(head,ways,pfWord,"","people"); }
/* BL-316: the funnel and its field picker are the FilterBar building block, drawn bare into #pmFdd (the funnel's own .dd) */
export let PFASK=null;   /* the field pfOpen asked for, read once as the picker opens */
export function pfBar(L,F,n){ const h=$("#pmFdd"); if(!h) return; if(F.length&&!F.some(f=>f[0]===PF.pk)) PF.pk=F[0][0]; const shown=L.filter(x=>pfPass(x,F)).length;
  drawFilterBar(h,{bare:true,fields:F.map(f=>{ const k=f[0], rem=k==="rem";
      return {id:k,label:f[1],section:f[2],note:f[5]||undefined,on:pfOn(k),single:rem,selected:rem?[PF.rem]:PF.f[k],not:k==="proj"||k==="org"?PF.neg.has(k):undefined,
        mark:rem?(PF.rem==="hide"?"default":PF.rem==="only"?"only":"shown"):pfOn(k)?(PF.neg.has(k)?"not · ":"")+PF.f[k].size:"",
        options:()=>f[3].map(([v,l])=>({value:v,label:l,extra:rem&&v==="hide"?"default":undefined,
          count:rem?L.filter(x=>pfPass(x,F,"rem")&&pfRemOK(x,v)).length:L.filter(x=>pfPass(x,F,k)&&f[4](x,v)).length}))}; }),
    onSelect:(k,vals)=>{ if(k==="rem") PF.rem=vals[0]||"hide"; else { const set=PF.f[k]; if(!set) return; set.clear(); vals.forEach(v=>set.add(v)); if(!set.size) PF.neg.delete(k); } pfDraw(); },
    onNot:(k,neg)=>{ neg?PF.neg.add(k):PF.neg.delete(k); pfDraw(); },
    more:{id:"pmFBtn",menuId:"pmFMenu",label:funnelTip(n,"Filter people"),menuLabel:"Filter people",count:n,on:!!n,key:"F",listLabel:"Filters",headId:"pmFph",
      field:PF.pk,onField:k=>{ PF.pk=k; pfDraw(); },result:`Showing ${shown} of ${L.length}`,resultId:"pmFpResult",doneId:"pmFpDone",
      clearAll:pfAny(F)?{id:"pmFpClear",run:()=>{ pfClearAll(); pfDraw(); }}:null,
      onOpen:()=>{ const k=PFASK; PFASK=null; if(k) PF.pk=k; else if(!pfOn(PF.pk)){ const L2=pfPeople(), F2=pfFields(L2); PF.pk=(F2.find(f=>f[0]!=="rem"&&pfOn(f[0]))||F2[0]||["proj"])[0]; } pfDraw(); }}}); }
export function pfApplied(L,F){ const el=$("#pmApplied"); if(!el) return; const chips=[];
  F.forEach(f=>{ const k=f[0];
    if(k==="rem"){ if(PF.rem!=="show") chips.push(fchipHtml(pfChip(f),k,PF.rem==="hide"?"Show removed people":"Stop showing only removed people",{def:PF.rem==="hide",edit:"pfedit",attr:"data-pfclr"})); return; }
    if(pfOn(k)) chips.push(fchipHtml(pfChip(f),k,`Remove the ${f[1].toLowerCase()} filter`,{neg:PF.neg.has(k),edit:"pfedit",attr:"data-pfclr"})); });
  if(PF.q.trim()) chips.push(fchipHtml(`Search: “${PF.q.trim()}”`,"q","Clear the search",{edit:"pfedit",attr:"data-pfclr"}));
  const shown=L.filter(x=>pfPass(x,F)).length, remF=F.some(f=>f[0]==="rem"), hid=remF&&PF.rem==="hide"?L.filter(x=>pfPass(x,F,"rem")&&x.off).length:0;
  const att=F.find(f=>f[0]==="att"), need=att&&!PF.f.att.size?L.filter(x=>pfPass(x,F)&&att[3].some(([v])=>att[4](x,v))).length:0;
  const bits=[html`Showing ${shown} of ${pfWord(L.length)}`];
  if(hid) bits.push(html`${hid} removed hidden <button type="button" class="linkbtn" data-pfquick="showrem">Show</button>`);
  if(remF&&PF.rem==="show") bits.push(html`removed shown <button type="button" class="linkbtn" data-pfquick="hiderem">Hide</button>`);
  if(need) bits.push(html`${need} need${need===1?"s":""} attention <button type="button" class="linkbtn" data-pfquick="att">Show</button>`);
  const extra=!!PF.q.trim()||F.some(f=>f[0]!=="rem"&&pfOn(f[0]))||remF&&PF.rem!=="hide";
  putHTML(el,html`${raw(chips.join(""))}${extra?html`<button type="button" class="linkbtn" id="pmClearF">Clear all</button>`:""}<span class="sp"></span><span class="sub" id="pmCount">${bits.map((b,i)=>html`${i?" · ":""}${b}`)}</span>`);
  const live=$("#pmLive"); if(live&&live.textContent!==`Showing ${shown} of ${pfWord(L.length)}`) live.textContent=`Showing ${shown} of ${pfWord(L.length)}`; }
/* draws everything below the search box from PF, then puts focus on `focus` (a selector) if given */
export function pfDraw(focus){ if(!$("#peopleMgr")||!$("#pmRows")) return; const L=pfPeople(), F=pfFields(L), n=pfDot(F);
  pfBar(L,F,n); pfApplied(L,F);
  const sc=pfScope(), tail=sc?` · ${sc.length===1?"this project":sc.length+" projects"}`:"", active=peopleAll(), list=L.filter(x=>pfPass(x,F));
  $("#pmHA").textContent="Actions"+tail; $("#pmHR").textContent="RAID"+tail; [$("#pmHA"),$("#pmHR")].forEach(h=>{ if(sc) h.title=`Counted in ${sc.map(pName).join(", ")}`; else h.removeAttribute("title"); });
  putHTML($("#pmRows"),list.length?list.map(x=>pfRow(x,sc,active)):html`<tr><td colspan="7">${raw(pfEmpty(L,F))}</td></tr>`);
  pfSave(); if(focus){ const el=$(focus); if(el) el.focus(); } }
export function pfOpen(k){ if(!pfFields(pfPeople()).length) return; PFASK=k||null; openFilterBar($("#pmFdd"),"more"); }
export function pfClose(back){ closeFilterBar($("#pmFdd"),back); }
export function pfClear(k){ if(k==="q"){ PF.q=""; const q=$("#pmQ"); if(q) q.value=""; } else if(k==="rem") PF.rem=PF.rem==="hide"?"show":"hide"; else if(PF.f[k]){ PF.f[k].clear(); PF.neg.delete(k); } }
export function pfClearAll(){ pfReset(); const q=$("#pmQ"); if(q) q.value=""; }
/* BL-231: the listeners, bound once from bootSettings0079 (the card is redrawn inside #settingsBody, which stays) */
export function pfBind(){ const body=$("#settingsBody"), inMgr=e=>e.target.closest&&e.target.closest("#peopleMgr");
  body.addEventListener("click",e=>{ if(!inMgr(e)) return; const t=e.target;
    if(t.closest("#pmFdd")) return;   /* the funnel and its picker: the FilterBar block's own */
    const c=t.closest("[data-pfclr]"); if(c){ pfClear(c.dataset.pfclr); pfDraw("#pmFBtn"); return; }
    const ed=t.closest("[data-pfedit]"); if(ed){ e.stopPropagation(); if(ed.dataset.pfedit==="q"){ $("#pmQ").focus(); $("#pmQ").select(); } else pfOpen(ed.dataset.pfedit); return; }
    const qk=t.closest("[data-pfquick]"); if(qk){ const w=qk.dataset.pfquick; if(w==="showrem") PF.rem="show"; else if(w==="hiderem") PF.rem="hide";
      else { const L=pfPeople(), a=pfFields(L).find(f=>f[0]==="att"); if(a) a[3].forEach(([v])=>PF.f.att.add(v)); } pfDraw("#pmFBtn"); return; }
    const rl=t.closest("[data-relax]"); if(rl){ const k=rl.dataset.relax; if(k==="all"){ pfClearAll(); snack("All filters cleared"); } else if(k==="rem") PF.rem="hide"; else pfClear(k); pfDraw("#pmQ"); return; }
    if(t.id==="pmClearF"){ pfClearAll(); pfDraw("#pmQ"); snack("Filters cleared"); } });
  body.addEventListener("input",e=>{ if(e.target.id!=="pmQ") return; PF.q=e.target.value; pfDraw(); });
  body.addEventListener("keydown",e=>{ const t=e.target; if(!inMgr(e)) return;
    if(t.id==="pmQ"&&e.key==="Escape"&&PF.q){ e.preventDefault(); e.stopPropagation(); pfClear("q"); pfDraw("#pmQ"); } });   /* the picker's keys are the FilterBar block's */
  /* F opens the picker and / goes to the search, on Settings › People only (elsewhere / is still ask creaite), as Activity's / does */
  document.addEventListener("keydown",e=>{ if(shared.VIEW!=="settings"||e.metaKey||e.ctrlKey||e.altKey||typing()) return; const b=$("#pmFBtn");
    if(!b||!b.offsetParent||document.querySelector("dialog[open]")||$("#chat").classList.contains("on")) return;
    if(e.key==="f"||e.key==="F"){ e.preventDefault(); e.stopImmediatePropagation(); PF.open?pfClose(true):pfOpen(); }
    else if(e.key==="/"){ e.preventDefault(); e.stopImmediatePropagation(); $("#pmQ").focus(); $("#pmQ").select(); } },true); }
/* ===== end BL-264 ===== */


/* links both ways: an owner name opens that person's page; Alan's own page is My work */
export const personLink=(n,label)=>!n||n==="TBC"?esc(label||n||""):`<a href="#" class="plink2" data-person="${esc(isMe(n)?S.me:personOf(n))}" title="Open ${esc(isMe(n)?"My work":personOf(n)+"’s page")}">${esc(label||who(n))}</a>`;

/* BL-56: the People view and a page per person. Counts only: no scores, ratings or on-time percentages. */
export const RECENT_DEC_DAYS=90;
export function PERS(){ const rs=resolver(), map=new Map(), get=n=>{ if(!map.has(n)) map.set(n,{name:n,p:shared.REG.find(x=>x.name===n)||null,A:[],R:[],D:[]}); return map.get(n); }, key=o=>rs(o).name||o;
  shared.REG.forEach(p=>get(p.name)); A.forEach(a=>{ if(a.o&&a.o!=="TBC") get(key(a.o)).A.push(a); }); R.forEach(r=>{ if(r.o&&r.o!=="TBC") get(key(r.o)).R.push(r); }); DEC.forEach(d=>{ if(d.by) get(key(d.by)).D.push(d); });
  return [...map.values()].filter(x=>x.A.length||x.R.length||x.D.length||(x.p&&!x.p.hidden)).map(x=>{ const oa=x.A.filter(open), oo=x.A.filter(openOnly), or=x.R.filter(open); return Object.assign(x,{oa,oo,or,late:[...oa,...or].filter(i=>i.due&&i.due<TODAY).length,codes:[...new Set([...x.A,...x.R,...x.D].map(i=>i.p))].sort()}); }); }
shared.PSORT={col:"late",dir:"desc"};
export const PSORTS={name:x=>x.name.toLowerCase(),org:x=>(x.p?x.p.org:"").toLowerCase(),role:x=>(x.p?x.p.role:"").toLowerCase(),oa:x=>x.oo.length,or:x=>x.or.length,late:x=>x.late};
export const dueSort=(a,b)=>{ const la=a.due&&a.due<TODAY, lb=b.due&&b.due<TODAY; return la!==lb?(la?-1:1):(a.due||"9999").localeCompare(b.due||"9999")||a.id.localeCompare(b.id); };
export const mKind=id=>A.some(x=>x.id===id)?"actions":R.some(x=>x.id===id)?"raid":"decisions";   /* declared before renderPerson, which runs at load */
shared.MCREATED=null; shared.MCREATEDOF=null;   /* declared before renderPerson, which runs at load */
shared.PKS=[]; shared.PKDONE=[]; shared.PKSEQ=0; export const PKAPPLIED=new Set();   /* declared before renderPerson, which runs at load */
export function renderPerson(name){ if(!shared.HAND||shared.HAND.name!==name) shared.HAND=null;   /* BL-58: a hand-over in progress belongs to one person */
  (()=>{ shared.PERSON=name; const el=$("#v-person"), x=PERS().find(y=>y.name===name);
  if(!x){ putHTML(el,html`<div class="wrapmax"><nav class="crumb" aria-label="Breadcrumb"><a href="#" data-go="people">People</a><span aria-hidden="true">›</span><span aria-current="page">${name}</span></nav><p class="sub">Nobody called “${name}” owns an item.</p></div>`); return; }
  const p=x.p, items=[...x.oa.map(a=>["actions",a]),...x.or.map(r=>["raid",r])], codes=[...new Set(items.map(([,i])=>i.p))].sort(), cutoff=new Date(TODAY); cutoff.setDate(cutoff.getDate()-RECENT_DEC_DAYS);
  const recent=x.D.filter(d=>d.date>=cutoff.toISOString().slice(0,10)).sort((a,b)=>b.date.localeCompare(a.date)), leads=Object.entries(D.leads||{}).filter(([k])=>personOf(k)===name).flatMap(([,v])=>v);
  putHTML(el,html`<div class="wrapmax"><nav class="crumb" aria-label="Breadcrumb"><a href="#" data-go="people">People</a><span aria-hidden="true">›</span><span aria-current="page">${name}</span></nav>
   <div style="display:flex;align-items:flex-start;gap:12px;flex-wrap:wrap"><div style="flex:1;min-width:260px"><h1>${name}${p||isMe(name)?"":html` <span class="tag warn" title="Owns items but isn’t in the people register">not in register</span>`}</h1>
     <p class="sub" style="margin:2px 0">${p&&(p.org||p.role)?[p.org,p.role].filter(Boolean).join(" · "):"Organisation and role not recorded"}${p&&p.email?html` · <a href="mailto:${p.email}">${p.email}</a>`:""}</p>
     ${p&&p.aliases.length?html`<p class="sub" style="margin:2px 0">Also written as ${p.aliases.join(", ")}</p>`:""}</div>
     ${raw(ibtn("pencil",p?"Edit details":"Add details",'id="ppEdit" aria-haspopup="dialog"',"bd"))}</div>
   <div class="ppcounts" role="group" aria-label="Counts"><span>${raw(countLink(`${plur(x.oo.length,"open action")} owned by ${name}`,x.oo.length,"actions:open:",{o:ownersOf(x.oo)},`<b>${x.oo.length}</b> open action${x.oo.length===1?"":"s"}`))}</span><span>${raw(countLink(`${plur(x.or.length,"open RAID item")} owned by ${name}`,x.or.length,"raid:open:",{o:ownersOf(x.or)},`<b>${x.or.length}</b> open risk${x.or.length===1?"":"s"} and issue${x.or.length===1?"":"s"}`))}</span><span class="${x.late?"late":""}">${raw(countLink(`${plur(x.late,"overdue item")} owned by ${name}`,x.late,"all:open:",{st:["Open"],due:["overdue"],ty:["Action","Risk","Issue","Assumption","Dependency"],o:ownersOf(latesOf(x))},`<b>${x.late}</b> overdue`))}</span><span>Projects ${raw(codes.map(pLink).join(" ")||"—")}</span></div>
   <div class="card ppcard"><h2>Open work${items.length?html` <span class="sub">· ${items.length}</span>`:""}</h2>${items.length?raw(personLinks(x)+personWork(x,codes)):html`<p class="sub">Nothing open.</p>`}</div>
   <div class="card ppcard"><h2>Decisions made${recent.length?html` <span class="sub">· last ${raw(RECENT_DEC_DAYS)} days</span>`:""}</h2>${recent.length?raw(personTbl("decisions",recent)):html`<p class="sub">None in the last ${raw(RECENT_DEC_DAYS)} days.</p>`}</div>
   ${leads.length?html`<div class="card ppcard"><h2>Workstreams led</h2><div class="mini-list">${leads.map(w=>html`<div class="li"><div class="t">${raw(pLink(w[0]))} ${w[1]}</div></div>`)}</div></div>`:""}</div>`);
  $("#ppEdit").onclick=async()=>{ const res=await askPerson(p?{edit:true,person:p}:{details:true,person:pBlank(name)}); if(res&&res.person){ const {name:_,...f}=res.person; await regEdit(name,f); renderPerson(name); } }; })();
  { const el=$("#v-person"), x=PERS().find(y=>y.name===name); if(x){
    const open=[...x.oa.map(a=>["actions",a]),...x.or.map(r=>["raid",r])], cut=new Date(TODAY); cut.setDate(cut.getDate()-P1_DAYS); const since=cut.toISOString().slice(0,10);
    const closed=[...x.A.map(a=>["actions",a]),...x.R.map(r=>["raid",r])].filter(([,i])=>i.st==="Closed"&&i.closed&&i.closed>=since).sort((a,b)=>b[1].closed.localeCompare(a[1].closed));
    addHTML(el.querySelector("#ppEdit"),"beforebegin",html`<button class="btn" id="ppEmail" aria-haspopup="dialog" data-tip="Draft an email with their open items" ${open.length?"":html`disabled aria-describedby="ppEmailNote"`}>${raw(ic("mail"))}Draft email</button>${open.length?html`<button class="btn" id="ppHand" data-tip="Hand their open items to someone else" ${shared.HAND?"disabled":""}>${raw(ic("handover"))}Hand over…</button>`:html`<span class="sub" id="ppEmailNote">Nothing open for ${name}, so no email is needed.</span>`}${raw(chaseNote(x))}`);   /* BL-83: Draft email replaces Prep 1:1; BL-224: when items were chased */
    const kp=WARNS().filter(w=>w.sig==="key_person"&&w.who===name);
    if(kp.length) addHTML(el.querySelector(".ppcounts"),"afterend",html`<div class="wnote">${kp.map(w=>html`<div>${raw(WICO.replace("<svg",'<svg width="14" height="14" style="flex:none;margin-top:1px"'))}<span>${(w.k==="projects"?pName(w.id):w.id)}: ${w.text}</span></div>`)}</div>`);
    const work=el.querySelector(".ppcard");
    addHTML(work,"afterend",html`<div class="card ppcard"><h2>Closed in the last ${raw(P1_DAYS)} days${closed.length?html` <span class="sub">· ${closed.length}</span>`:""}</h2>${closed.length?html`<div class="mini-list">${raw(closed.map(([k,i])=>`<div class="li" data-open="${k}:${i.id}"><div class="t">${ico(k==="actions"?"action":kindOf("raid",i))}${esc(i.t)}</div><div class="m">${pLink(i.p)} ${esc(i.id)} · closed ${fd(i.closed)}</div></div>`).join(""))}</div>`:html`<p class="sub">Nothing closed lately.</p>`}</div>`);
    if(shared.HAND){
      addHTML(work.querySelector("h2"),"afterend",html`<div class="handbar"><label><input type="checkbox" id="handAll" ${shared.HAND.picked.size===open.length?"checked":""}> All</label><span class="sub">${shared.HAND.picked.size} of ${open.length} selected · hand over to</span><input type="text" id="handTo" list="handPeople" placeholder="A person in the register" aria-label="Hand over to"><datalist id="handPeople">${peopleAll().filter(n=>n!==name).map(n=>html`<option value="${n}">`)}</datalist><button class="btn primary" id="handGo" ${shared.HAND.picked.size?"":"disabled"}>Hand over</button><button class="btn" id="handCancel">Cancel</button></div>`); }
    decorateWarnings(el); personFlags(el); } }   /* BL-58 */
  hlPrune();   /* BL-68 */
  tabTitle();
  { const el=$("#v-person"), x=PERS().find(y=>y.name===name); if(x){ const L=x.D.filter(d=>d.st==="Pending").sort(decRank); if(L.length){
    const em=el.querySelector("#ppEmail"); if(em&&em.disabled){ em.disabled=false; em.removeAttribute("aria-describedby"); $("#ppEmailNote")?.remove(); }
    const work=el.querySelector(".ppcard"); if(work){
    addHTML(work,"afterend",html`<div class="card ppcard" id="decWaiting"><h2>Decisions we're waiting on from ${name.split(/\s+/)[0]} <span class="sub">· ${raw(countLink(`${plur(L.length,"decision")} waiting on ${name}`,L.length,"decisions:pending:",{o:ownersOf(L)}))}</span></h2><div class="mini-list">${L.map(d=>html`<div class="li" data-open="decisions:${d.id}" tabindex="0"><div class="t">${raw(ico("decision"))}${d.t}</div><div class="m">${raw(pLink(d.p))} ${d.id} · ${d.due?decLate(d)?html`needed by ${fd(d.due)}, <span class="late">${raw(decLateWords(d))}</span>`:html`needed by ${fd(d.due)}`:"no date needed by"}</div></div>`)}</div></div>`); } } } }   /* BL-53: decisions waiting on them */
  { const pc=personPromises(name,n=>resolver()(n).name||n), w=$("#v-person .wrapmax"); if(pc&&w&&!$("#ppPromises")){   /* BL-125 A: after Open work */
    const work=w.querySelector(".ppcard"); if(work) addHTML(work,"afterend",pc); else addHTML(w,"beforeend",pc); } }
  if(!shared.LOADING){ mDots("work"); markStagedRows(); } }
export function peopleCk(add){ PERS().forEach(x=>add("People",x.name,[x.p&&x.p.org,x.p&&x.p.role].filter(Boolean).join(" · "),()=>{ if(isMe(x.name)) go("mine"); else go("person",x.name); })); }
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootSettings0079(){
pfBind();
$("#settingsBody").addEventListener("click",async e=>{ const b=e.target.closest("[data-pm],#pmAdd"); if(!b) return; const n=b.dataset.n, k=b.id==="pmAdd"?"add":b.dataset.pm, p=pFind(shared.REG,n||"");
  if(k==="add"){ const res=await askPerson({}); if(res&&res.person) await regAddPerson(res.person); }
  else if(k==="edit"){ const res=await askPerson(p?{edit:true,person:p}:{details:true,person:pBlank(n)}); if(res&&res.person){ const {name,...f}=res.person; await regEdit(n,f); } }
  else if(k==="hide") await regSetHidden(n,true);
  else if(k==="restore"){ PEOPLE.hidden=PEOPLE.hidden.filter(x=>x!==n); await regSetHidden(n,false); }
  else if(k==="ren"){ const td=b.closest("tr").cells[0]; putHTML(td,html`<span style="display:flex;gap:6px"><input type="text" value="${n}" style="height:30px;border:1px solid var(--faint);border-radius:6px;padding:0 8px"><button class="mini ok">Save</button><button class="mini">Cancel</button></span>`); const inp=td.querySelector("input"); inp.focus(); inp.select(); const [ok,cn]=td.querySelectorAll("button");
    ok.onclick=()=>renamePerson(n,inp.value); cn.onclick=()=>renderSettings(); inp.onkeydown=ev=>{ if(ev.key==="Enter") renamePerson(n,inp.value); if(ev.key==="Escape"){ ev.stopPropagation(); renderSettings(); } }; } });
$("#settingsBody").addEventListener("change",e=>{ const s=e.target.closest("select.pmsel"); if(s&&s.value){ e.stopPropagation(); renamePerson(s.dataset.n,s.value); } },true);
document.addEventListener("click",e=>{ const a=e.target.closest("[data-person]"); if(!a) return; e.preventDefault(); e.stopPropagation(); const n=a.dataset.person; if(isMe(n)) go("mine"); else go("person",n); },true);
/* renderPeople: BL-138 (sprint-all-items) draws the People view in two tabs, in its own section near the end */
document.addEventListener("click",e=>{ const h=e.target.closest("[data-psort]"); if(h&&shared.VIEW==="people"){ const c=h.dataset.psort; shared.PSORT=shared.PSORT.col===c?{col:c,dir:shared.PSORT.dir==="asc"?"desc":"asc"}:{col:c,dir:c==="name"||c==="org"||c==="role"?"asc":"desc"}; const kept=h.contains(document.activeElement); renderPeople(); if(kept){ const b=document.querySelector(`#peopleTbl th[data-psort="${c}"] button.thsort`); if(b) b.focus({preventScroll:true}); } return; }   /* v1.9.5 check 8: the redraw keeps focus on the same heading, so its new aria-sort is read and Enter again reverses */
  const r=e.target.closest("#peopleTbl tr[data-pp]"); if(r&&!e.target.closest("a,button")){ const n=r.dataset.pp; if(isMe(n)) go("mine"); else go("person",n); } });
}
/* ===== Workstreams (BL-58, BL-56) ===== */
/* Workstreams belong to each project, like milestones (tracker.db workstreams): a lead, keywords and aliases help
   creaite match items. The picker offers the project's Active ones; a new name is added on purpose, with suggested
   details, in the same proposal as the item. Settings › Workstreams edits the table; the project page lists them. */
export const WSD=()=>D.ws_table||[], wsTable=()=>WSD().length>0;
export const wsRow=(p,n)=>WSD().find(w=>w.p===p&&w.name.toLowerCase()===String(n||"").trim().toLowerCase());
export const WS_STOP=new Set("a an and the of to for in on at by with from is are be was were this that it its as or not no we our their they them will would should can could has have had do does did into about after before over under next new more any all per via vs".split(" "));
export function wsSuggest(code,name){ const low=String(name).trim().toLowerCase(), skip=new Set([...WS_STOP,...(low.match(/[a-z0-9]+/g)||[]),code.toLowerCase()]);
  const items=[...A,...R].filter(x=>x.p===code&&((x.ws||"").toLowerCase()===low||String(x.t||"").toLowerCase().includes(low)));
  const words={}, acr={}, owners={}, chans={}, bump=(o,k)=>o[k]=(o[k]||0)+1;
  items.forEach(x=>{ const t=String(x.t||""); (t.match(/[A-Za-z][A-Za-z0-9-]{2,}/g)||[]).forEach(w=>{ if(!skip.has(w.toLowerCase())&&w!==w.toUpperCase()) bump(words,w.toLowerCase()); });
    (t.match(/\b[A-Z][A-Z0-9]{1,5}\b/g)||[]).forEach(a=>{ if(a!==code&&!skip.has(a.toLowerCase())) bump(acr,a); });
    if(x.o&&x.o!=="TBC") bump(owners,x.o); const m=String(x.src||"").match(/Channel:\s*([^·]+)/); if(m) bump(chans,m[1].trim()); });
  const top=(o,n)=>Object.entries(o).sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0])).slice(0,n).map(e=>e[0]);
  const lead=top(owners,1)[0], r=lead?resolvePerson(lead):null;
  return {lead:r&&["known","alias","email"].includes(r.status)?r.name:"",keywords:top(words,4).join(", "),aliases:top(acr,3).join(", "),channel:top(chans,1)[0]||"",items:items.length}; }
export const WS_FIELDS=[["lead","Lead"],["keywords","Keywords"],["aliases","Aliases"],["channel","Teams channel"]];
export function wsConfirm(p,name){ const w=wsRow(p,name); if(w&&w.st==="Closed") return `“${w.name}” is closed in ${p}: reopen it in Settings › People and projects › Workstreams, or choose another.`;
  if(w) return null; const k=wsKey(p,name.trim());
  if(shared.CUR.wsNew!==k||!$("#wsNewBox")){ shared.CUR.wsNew=k; shared.WSNEW=null; const s=wsSuggest(p,name); $("#wsNewBox")?.remove();
    addHTML($("#f_ws").closest("dd"),"beforeend",html`<div class="wsnew" id="wsNewBox"><div class="sub">New workstream for ${p}, suggested from ${s.items} item${s.items===1?"":"s"}; change anything, then Save again.</div>${raw(WS_FIELDS.map(([f,l])=>`<label>${l}<input type="text" data-wsn="${f}" value="${esc(s[f])}" ${f==="lead"?'placeholder="A person from the people register"':""}></label>`).join(""))}</div>`);
    return `Add “${name.trim()}” to ${p}'s workstreams? Check its details below, then Save again.`; }
  shared.WSNEW={project:p,name:name.trim(),...Object.fromEntries($$("#wsNewBox [data-wsn]").map(i=>[i.dataset.wsn,i.value.trim()]))}; return null; }
shared.WSNEW=null;   /* the new workstream Alan confirmed; kept here because saving a new item closes the panel first */
/* BL-187 (fix-peek-140): the one route for a new workstream: its proposal item (op new, table workstreams) and the row the page
   shows until the apply. Used by the panel's save (below), Settings › Workstreams and the peek's "Add workstream…". */
export function wsNewOf(nv,src){ const values=Object.fromEntries(Object.entries({project:nv.project,name:nv.name,lead:nv.lead,keywords:nv.keywords,aliases:nv.aliases,channel:nv.channel,source:src||`${S.me} (dashboard), ${TODAY}`}).filter(([,v])=>v));
  return {item:{op:"new",table:"workstreams",values},row:{id:"",p:nv.project,name:nv.name,lead:nv.lead||"",keywords:nv.keywords||"",aliases:nv.aliases||"",channel:nv.channel||"",st:"Active",nA:0,nR:0}}; }
/* the new workstream travels in the same proposal as the item, ahead of it (undo removes both) */
/* Settings › Workstreams: the table, edited through proposals */
export let WSM={edit:null,closed:false,proj:""};
export function wsCells(w){ return WS_FIELDS.map(([f])=>`<td>${f==="lead"&&w.lead?esc(who(w.lead)):esc(w[f]||"")||'<span class="sub">—</span>'}</td>`).join(""); }
export function drawWsMgr(){ const L=WSD().filter(w=>(WSM.closed||w.st==="Active"||WSM.edit===w.id)&&(!WSM.proj||w.p===WSM.proj)), nClosed=WSD().filter(w=>w.st==="Closed").length;
  const ed=(w,isNew)=>`<tr class="wsedit" data-wsid="${esc(w.id||"")}"><td>${isNew?`<select data-wf="project">${P.map(p=>`<option value="${p.code}" ${p.code===w.p?"selected":""}>${esc(p.name)}</option>`).join("")}</select>`:`<span class="pcode">${esc(pName(w.p))}</span>`}</td><td><input type="text" data-wf="name" value="${esc(w.name||"")}" aria-label="Workstream"></td>${WS_FIELDS.map(([f,l])=>`<td><input type="text" data-wf="${f}" value="${esc(w[f]||"")}" aria-label="${l}"></td>`).join("")}<td colspan="2"></td><td class="mgract"><button class="mini" data-wsm="save">Save</button><button class="mini" data-wsm="cancel">Cancel</button></td></tr>`;
  putHTML($("#wsMgr"),html`<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap"><h2 style="flex:1">Workstreams</h2><select id="wsmP" aria-label="Project"><option value="">All projects</option>${P.map(p=>html`<option value="${p.code}" ${WSM.proj===p.code?"selected":""}>${p.name}</option>`)}</select><input id="wsmName" type="text" placeholder="New workstream" aria-label="New workstream"><button class="btn" data-wsm="add">Add…</button>${nClosed?html`<label class="sub"><input type="checkbox" id="wsmClosed" ${WSM.closed?"checked":""}> Show closed (${raw(nClosed)})</label>`:""}</div>
    <p class="sub" style="margin:6px 0 10px">Each project's own workstreams. A lead, keywords and aliases (e.g. UAT for Testing) help creaite match items from minutes and mail. Renaming one renames its items too; closing one stops it being chosen for new items. Every change is a proposal, with Undo.</p>
    <div class="tbl"><table class="mgr"><thead><tr><th>Project</th><th>Workstream</th>${raw(WS_FIELDS.map(([,l])=>`<th>${l}</th>`).join(""))}<th class="num">Open</th><th>Status</th><th></th></tr></thead><tbody>
    ${WSM.edit==="new"?raw(ed(WSM.draft,true)):""}${raw(L.map(w=>WSM.edit===w.id?ed(w,false):`<tr class="${w.st==="Closed"?"off":""}"><td><span class="pcode">${esc(pName(w.p))}</span></td><td>${esc(w.name)}</td>${wsCells(w)}<td class="num">${w.nA+w.nR}</td><td>${w.st}</td><td class="mgract"><button class="mini" data-wsm="edit" data-wsid="${w.id}">Edit</button><button class="mini" data-wsm="${w.st==="Active"?"close":"reopen"}" data-wsid="${w.id}">${w.st==="Active"?"Close":"Reopen"}</button></td></tr>`).join("")||`<tr><td colspan="9" class="sub">No workstreams yet${WSM.proj?` for ${WSM.proj}`:""}. Add one, or say “setup” to bring them in from the items.</td></tr>`)}</tbody></table></div>`); }
export async function wsmSave(tr){ const v=Object.fromEntries([...tr.querySelectorAll("[data-wf]")].map(i=>[i.dataset.wf,i.value.trim()])), id=tr.dataset.wsid;
  if(!v.name){ snack("Give the workstream a name"); return; } if(v.lead){ const o=await ownerFinal(v.lead); if(o===null) return; v.lead=o; }
  if(!id){ const p=v.project; if(wsRow(p,v.name)){ snack(`${p} already has “${v.name}”`); return; }
    const {item,row}=wsNewOf({...v,project:p});
    WSM.edit=null; await save(`${p} workstream ${v.name} added`,[item],null,()=>{ (D.ws_table=D.ws_table||[]).push(row); },()=>{ const i=WSD().indexOf(row); if(i>=0) D.ws_table.splice(i,1); }); drawWsMgr(); return; }
  const w=WSD().find(x=>x.id===id), changes={}; ["name",...WS_FIELDS.map(f=>f[0])].forEach(f=>{ if((v[f]||"")!==(w[f]||"")) changes[f]=v[f]||null; });
  WSM.edit=null; if(!Object.keys(changes).length){ drawWsMgr(); return; }
  if(changes.name&&WSD().some(x=>x!==w&&x.p===w.p&&x.name.toLowerCase()===changes.name.toLowerCase())){ snack(`${pName(w.p)} already has “${changes.name}”`); drawWsMgr(); return; }
  const before={...w}, old=w.name, moved=[...A,...R].filter(x=>x.p===w.p&&(x.ws||"").toLowerCase()===old.toLowerCase());
  await save(`${pName(w.p)} workstream ${old} ${changes.name?`renamed ${changes.name}`:"updated"}`,[{op:"update",table:"workstreams",id,changes,based_on:w.updated_at}],null,
    ()=>{ Object.assign(w,Object.fromEntries(Object.entries(changes).map(([k,x])=>[k,x||""]))); if(changes.name) moved.forEach(x=>x.ws=changes.name); },
    ()=>{ Object.assign(w,before); moved.forEach(x=>x.ws=old); }); drawWsMgr(); }
export async function wsmStatus(id,st){ const w=WSD().find(x=>x.id===id); if(!w) return;
  await save(`${pName(w.p)} workstream ${w.name} ${st==="Closed"?"closed":"reopened"}`,[st==="Closed"?{op:"cancel",table:"workstreams",id,based_on:w.updated_at}:{op:"update",table:"workstreams",id,changes:{status:"Active"},based_on:w.updated_at}],null,()=>{ w.st=st; },()=>{ w.st=st==="Closed"?"Active":"Closed"; }); drawWsMgr(); }

/* BL-56 phase 2: a person's page gets Hand over (their open items to someone in the register, one proposal, one undo),
   early-warning flags on their items and what they closed in the last 14 days. (Draft email, BL-83, replaced the Prep 1:1
   brief.) Counts only, never scores; nothing here reaches a client report. */
export const P1_DAYS=14;
export const ownedBy=(name,i)=>i.o&&i.o!=="TBC"&&personOf(i.o)===name;
shared.HAND=null;   /* {name, picked: Set of "k:id"} while handing over */
export async function handOver(name){ const to0=$("#handTo").value.trim(); if(!to0){ snack("Choose who takes them over"); $("#handTo").focus(); return; }
  const to=await ownerFinal(to0); if(to===null) return; if(to===name){ snack(`They're already ${name}'s`); return; }
  const picked=[...shared.HAND.picked].map(k=>k.split(":")).map(([k,id])=>[k,REC(k,id)]).filter(([,x])=>x);
  const items=picked.map(([k,x])=>({op:"update",table:k,id:x.id,changes:{owner:to},based_on:x.updated_at})), was=picked.map(([,x])=>[x,x.o]);
  shared.HAND=null; if(await save(`${items.length} item${items.length===1?"":"s"} handed over from ${name} to ${to}`,items,null,()=>was.forEach(([x])=>x.o=to),()=>was.forEach(([x,o])=>x.o=o))) renderPerson(name); else renderPerson(name); }
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootSettings0127(){
document.addEventListener("click",e=>{ const b=e.target.closest("#wsMgr [data-wsm]"); if(!b) return; e.preventDefault(); const a=b.dataset.wsm, tr=b.closest("tr");
  if(a==="add"){ const name=$("#wsmName").value.trim(), p=WSM.proj||P[0].code; WSM.draft={id:"",p,name,...(name?wsSuggest(p,name):{})}; WSM.edit="new"; drawWsMgr(); $('#wsMgr .wsedit [data-wf="name"]').focus(); }
  else if(a==="edit"){ WSM.edit=b.dataset.wsid; drawWsMgr(); }
  else if(a==="cancel"){ WSM.edit=null; drawWsMgr(); }
  else if(a==="save") wsmSave(tr);
  else if(a==="close") wsmStatus(b.dataset.wsid,"Closed"); else if(a==="reopen") wsmStatus(b.dataset.wsid,"Active"); });
document.addEventListener("change",e=>{ if(e.target.id==="wsmP"){ WSM.proj=e.target.value; drawWsMgr(); } if(e.target.id==="wsmClosed"){ WSM.closed=e.target.checked; drawWsMgr(); }
  if(e.target.closest&&e.target.closest("#wsMgr .wsedit [data-wf=project]")){ const tr=e.target.closest("tr"), name=tr.querySelector('[data-wf="name"]').value.trim(); if(name){ const s=wsSuggest(e.target.value,name); WS_FIELDS.forEach(([f])=>{ const i=tr.querySelector(`[data-wf="${f}"]`); if(i&&!i.value) i.value=s[f]||""; }); } } });
document.addEventListener("keydown",e=>{ const tr=e.target.closest&&e.target.closest("#wsMgr .wsedit"); if(!tr) return; if(e.key==="Enter"){ e.preventDefault(); wsmSave(tr); } if(e.key==="Escape"){ e.preventDefault(); e.stopPropagation(); WSM.edit=null; drawWsMgr(); } });
/* Review: an item whose workstream isn't one of its project's offers to add it, or to leave it blank */
document.addEventListener("click",async e=>{ const b=e.target.closest("[data-wsq]"); if(!b) return; e.preventDefault(); e.stopPropagation(); const r=REV.find(x=>x.n===+b.dataset.n); if(!r||!await needVault()) return;
  const name=r.ws_suggest, add=b.dataset.wsq==="add", s=add?wsSuggest(r.p,name):null;
  try{ await editProposal(r.file,data=>{ const items=data.items||[], it=items.find(i=>i.n===r.ref); if(!it||it.applied) throw new Error("that proposal has already been applied");
      it.flags=(it.flags||[]).filter(f=>f!=="new-workstream"); delete it.ws_suggest; if(!add) return;
      const known=wsRow(r.p,name), target=it.values||(it.changes=it.changes||{}); target.workstream=known?known.name:name;
      if(!known) items.splice(items.indexOf(it),0,{n:Math.max(0,...items.map(i=>+i.n||0))+1,op:"new",table:"workstreams",values:Object.fromEntries(Object.entries({project:r.p,name,lead:s.lead,keywords:s.keywords,aliases:s.aliases,channel:s.channel,source:`${S.me} in review, ${TODAY}`}).filter(([,x])=>x)),match:"strong",flags:[],decision:"approved"}); }); }
  catch(err){ snack("Not saved: "+err.message); return; }
  r.flags=(r.flags||[]).filter(f=>f!=="new-workstream"); r.ws_suggest=null; if(add&&!wsRow(r.p,name)) (D.ws_table=D.ws_table||[]).push({id:"",p:r.p,name,lead:s.lead,keywords:s.keywords,aliases:s.aliases,channel:s.channel,st:"Active",nA:0,nR:0});
  if(add&&r.rec) r.rec.ws=name; renderReview(); snack(add?`Workstream ${name} will be added to ${pName(r.p)} with this item — check its details in Settings › People and projects › Workstreams`:"Left without a workstream"); },true);
document.addEventListener("click",e=>{ const t=e.target;
  if(t.closest("#ppEmail")){ if(!t.closest("#ppEmail").disabled) openDraftEmail(shared.PERSON); return; }
  if(t.closest("#ppHand")){ shared.HAND={name:shared.PERSON,picked:new Set()}; renderPerson(shared.PERSON); return; }
  if(t.closest("#handCancel")){ shared.HAND=null; renderPerson(shared.PERSON); return; }
  if(t.closest("#handGo")){ handOver(shared.PERSON); return; }
  if(shared.HAND&&t.closest("tr.handpick")&&!t.closest("a,button")){ e.preventDefault(); e.stopPropagation(); const tr=t.closest("tr.handpick"), k=tr.dataset.k+":"+tr.dataset.row; shared.HAND.picked.has(k)?shared.HAND.picked.delete(k):shared.HAND.picked.add(k); personRedraw(); } },true);
document.addEventListener("change",e=>{ if(e.target.id==="handAll"&&shared.HAND){ const x=PERS().find(y=>y.name===shared.PERSON); shared.HAND.picked=e.target.checked?new Set([...x.oa.map(a=>"actions:"+a.id),...x.or.map(r=>"raid:"+r.id)]):new Set(); personRedraw(); } });
}
/* ===== Sweep and alerts (BL-97, BL-99, BL-98) ===== */
/* BL-97: Settings › Sweep lists the ignore rules (settings.json sweep.ignore, saved with a backup and a log entry):
   a switch, Edit and Delete on each, and Add a rule. The private rule is built in: it can be switched off, never
   deleted. sweep.py applies the rules (window, stage, calendar) and counts what they skip; a VIP always comes through. */
export const SA=()=>D.sweep_alerts||(D.sweep_alerts={ignore:[]});
export const IGW={mail:"Mail",teams:"Teams",calendar:"Calendar"}, IGF={subject:"Subject or title",sender:"Sender",channel:"Teams channel or chat"},
  IGH={begins:"begins with",contains:"contains",equals:"is exactly",address:"is the address",domain:"is in the domain"},
  IGHOW={subject:["begins","contains","equals"],sender:["address","domain","begins","contains","equals"],channel:["begins","contains","equals"]};
export let IGEDIT=null;                                   /* the rule being edited: its index, -1 for a new one, null for none */
export function igText(r){ if(r.builtin==="private") return "Anything marked private or personal, in mail, Teams and the calendar";
  return `${(r.where||[]).map(w=>IGW[w]||w).join(", ")} · ${IGF[r.field]||r.field} ${IGH[r.how]||r.how} “${r.text||""}”`; }
export function igHowOpts(field,how){ return (IGHOW[field]||IGHOW.subject).map(h=>`<option value="${h}" ${h===how?"selected":""}>${IGH[h]}</option>`).join(""); }
export function igForm(r){ return `<div class="igform" id="igForm"><label for="igName">Name</label><input type="text" id="igName" value="${esc(r.name||"")}" placeholder="For example ToDo invites">
   <span>Where</span><div class="igwhere">${Object.entries(IGW).map(([k,l])=>`<label><input type="checkbox" data-igw="${k}" ${(r.where||[]).includes(k)?"checked":""}> ${l}</label>`).join("")}</div>
   <label for="igField">Looks at</label><select id="igField">${Object.entries(IGF).map(([k,l])=>`<option value="${k}" ${k===r.field?"selected":""}>${l}</option>`).join("")}</select>
   <label for="igHow">Match</label><select id="igHow">${igHowOpts(r.field,r.how)}</select>
   <label for="igText">Text</label><input type="text" id="igText" value="${esc(r.text||"")}" placeholder="todo, someone@example.com or example.com">
   <div class="igbtns"><button class="btn primary" data-ig="save">Save rule</button><button class="btn" data-ig="cancel">Cancel</button></div></div>`; }
export function renderIgnore(){ const el=$("#ignMgr"); if(!el) return; const L=SA().ignore||[];
  putHTML(el,html`<div class="srow" style="display:block"><div>Ignore rules<small>The sweep skips what these match, even when it names a project, and the summary counts what was skipped. A message from someone you follow always comes through, and a thread or meeting you name yourself is never skipped. Matching ignores case.</small></div>
   <div class="iglist">${L.map((r,i)=>IGEDIT===i?raw(igForm(r)):html`<div class="igrow"><input type="checkbox" class="switch" data-igon="${raw(i)}" ${r.on!==false?"checked":""} aria-label="Use the rule ${r.name}"><div class="igtxt"><b>${r.name}</b>${r.builtin?html` <span class="tag">built in</span>`:""}<small>${igText(r)}</small></div>${r.builtin?"":html`<button class="mini" data-ig="edit" data-i="${raw(i)}">Edit</button><button class="mini" data-ig="del" data-i="${raw(i)}">Delete</button>`}</div>`)}
   ${IGEDIT===-1?raw(igForm({name:"",where:["mail"],field:"subject",how:"begins",text:"",on:true})):""}</div>
   ${IGEDIT===null?html`<button class="btn" data-ig="add" style="margin-top:8px">Add a rule</button>`:""}</div>`);
  if(IGEDIT!==null&&$("#igName")) $("#igName").focus(); }
export async function saveIgnore(list,msg){ if(!await writeSettings({"sweep.ignore":list})) return false; SA().ignore=list; if(msg) snack(msg); return true; }

/* BL-99 VIPs: people marked VIP in the register (an extra "VIP" column: management, client or yes). What they send is
   recorded by sweep.py vip (the sweep, the session start and the live server's timer) in system/staging/vip.json, and
   each unseen alert opens Today's Needs attention, above everything else, until Alan presses Seen. A count shows on
   Today in the rail and in the window title; a browser notification (asked for once) when one arrives while the page
   is open. VIP-sourced proposals sort first in Review. Nothing leaves the laptop. */
export const VIPD=()=>SA().vip||(SA().vip={alerts:[],people:{}}), VIPS=()=>(VIPD().alerts||[]).filter(a=>!a.seen&&!a.quiet);
/* BL-334: a conversation with nothing for Alan is one quiet line on Today (no buttons, no count), shown the day it was updated */
export const VIPQ=()=>(VIPD().alerts||[]).filter(a=>!a.seen&&a.quiet&&String(a.updated||"").slice(0,10)===TODAY);
/** what changed in the alerts, for a redraw: an updated conversation keeps its ID */
const vipSig=()=>(VIPD().alerts||[]).filter(a=>!a.seen).map(a=>`${a.id}@${a.updated||""}`).join();
export const vipKind=n=>{ const ppl=VIPD().people||{}; return ppl[n]||ppl[personOf(n)]||""; };
export const VIPKIND={mail:"Email",teams:"Teams",calendar:"Invite"}, BASETITLE=document.title;
export function vipWhen(a){ const d=(a.sent||"").slice(0,10); return d===TODAY?`today ${a.sent.slice(11,16)}`:d?`${fd(d)} ${a.sent.slice(11,16)}`.trim():""; }
/* BL-288: nothing says why a message is shown (who Alan follows is never labelled); BL-296: each has Create work item and
   Dismiss (Undo in the message). BL-319: the messages are rows of Today's To decide (today.js toDecideRows), newest first with
   the proposals and transcripts; their two icons keep the data-alertdo buttons this file's handler runs. */
export const ALERTWORD={mail:"email",teams:"Teams message",calendar:"invite"};
/* after a row goes: focus to the same button on the row now in its place in To decide (or its first action), else To decide's heading */
export function alertFocus(id,what){ const vis=()=>$$("#tdList > li").filter(l=>!l.hidden), i=vis().findIndex(r=>r.dataset.td==="al"+id); return ()=>{
  const L=vis(), next=L[Math.min(Math.max(0,i),L.length-1)];
  const b=next&&(next.querySelector(`[data-alertdo="${what}"]`)||next.querySelector("[data-tdact]")); if(b){ /** @type {HTMLElement} */(b).focus(); return; }
  const h=$("#hTd"); if(h&&h.offsetParent){ h.tabIndex=-1; h.focus(); return; } const h2=$("#hAttn"); if(h2){ h2.tabIndex=-1; h2.focus(); } }; }
export async function alertDismiss(id,cand){ if(!viaServer()){ snack("Dismiss needs the live server"); return; }
  const c=cand?{cand}:{}, r=await api("/api/alerts/dismiss",{ids:[id],...c}); if(!r.ok){ snack(r.message||"Not dismissed"); return; }
  const a=(VIPD().alerts||[]).find(x=>x.id===id), back=alertFocus(id,"dismiss"), it=cand&&a?(a.candidates||[]).find(/** @param {any} x */x=>x.n===cand):null;
  if(it){ it.dismissed=r.at||nowStamp(); if((a.candidates||[]).every(/** @param {any} x */x=>x.made||x.dismissed)) a.seen=r.at||nowStamp(); }   /* BL-334: that item only; nothing is staged */
  else if(a) a.seen=r.at||nowStamp();
  vipBadge(); renderToday(); back();
  snack(it?"Item dismissed":"Message dismissed",async()=>{ const u=await api("/api/alerts/undo",{ids:[id],...c}); if(!u.ok){ snack(u.message||"Not undone"); return; }
    if(it){ delete it.dismissed; if(a) delete a.seen; } else if(a){ delete a.seen; delete a.made; } VIPNOTED.add(id); vipBadge(); renderToday(); snack("Back in To decide"); }); }
/* Create work item (BL-296): the new-item peek, filled from the alert's references only (/api/alerts/prefill). Saving (⌘↵ or Save)
   stages it for Review through /api/alerts/make, which dismisses the message (never applied: check 45, BL-334); closing the peek
   leaves the message as it was. */
export const ALERTTYPES=[["action","Action"],["risk","Risk"],["issue","Issue"],["decision","Decision"]];
export const alertTypeOf=(k,x)=>k==="actions"?"action":k==="decisions"?"decision":String((x&&x.type)||"risk").toLowerCase();
export async function alertMake(id,type,keep,cand){ if(!viaServer()){ snack("Create work item needs the live server"); return; }
  const r=await api("/api/alerts/prefill",{id,...(type?{type}:{}),...(cand?{cand}:{})}); if(!r.ok||!r.prefill){ snack(r.message||"That message can't be read"); return; }
  type=r.prefill.type||type||"action";
  const pre=r.prefill, k=pre.table, v=pre.values||{}; openNew(k,k==="decisions"?"needed":"");
  if(!shared.CUR||shared.CUR.mode!=="new"||shared.CUR.k!==k) return;
  PKN.offer=null; pkNewOffer("");                                               /* not a kept draft of another new item */
  const x=shared.CUR.draft; x.p=pre.project||""; x.t=keep&&keep.t?keep.t:String(v.description??v.decision??"");
  if(k==="decisions"){ x.by=v.made_by||""; x.srcIn=pre.source||""; if(keep&&keep.due) x.due=keep.due; }
  else { x.o=v.owner||""; if(v.type) x.type=v.type; if(keep&&keep.due) x.due=keep.due; }
  if(pre.raised) x.raised=pre.raised;
  if(!keep&&k!=="decisions"&&v.due_date) x.due=v.due_date; if(!keep&&k==="decisions"&&v.needed_by) x.due=v.needed_by;   /* BL-334: a due date the conversation stated */
  shared.CUR.alert={id,type,cand:cand||0,link:pre.link||"",who:pre.who||"",sent:pre.sent||"",kind:pre.kind||"mail",marker:pre.marker||"",source:pre.source||""};
  shared.CUR.blank={...x}; drawPanel(); const t=$("#pkTitle"); if(t){ t.textContent=x.t; t.focus(); } }
export function alertValues(k,f){ const v=toDb(k,f); return {...v,project:f.p||""}; }
/* the peek's first stage for an item made from a message: the server stages it as a pending proposal for Review and dismisses the
   message. Check 45 (BL-334, Jarvis option (a)): it is never applied from here, and it isn't in the pill (staged = approved there);
   pkSaveAndClose then closes the peek through alertStaged, with Undo. */
export async function alertStage(k,nid,f){ const al=shared.CUR.alert, type=alertTypeOf(k,shared.CUR.draft); pkSaving("busy");
  const r=await api("/api/alerts/make",{id:al.id,type,values:alertValues(k,f),...(al.cand?{cand:al.cand}:{})});
  if(!r.ok){ pkSaving("fail"); pkNote(r.message||"Not staged"); return "wait"; }
  if(shared.CUR&&shared.CUR.nid===nid){ shared.CUR.staged=r.proposal; shared.CUR.alertDone={al,name:r.proposal,word:pkNewWordOf(k,type),title:f.t}; } pkSaving("ok");
  const a=(VIPD().alerts||[]).find(z=>z.id===al.id), it=a&&al.cand?(a.candidates||[]).find(/** @param {any} x */x=>x.n===al.cand):null;
  if(it){ it.made=r.made||{proposal:r.proposal}; if((a.candidates||[]).every(/** @param {any} x */x=>x.made||x.dismissed)) a.seen=nowStamp(); }   /* BL-334: that item only */
  else if(a){ a.seen=nowStamp(); a.made=r.made||{proposal:r.proposal}; } vipBadge(); return "ok"; }
const pkNewWordOf=(k,type)=>k==="actions"?"action":k==="decisions"?"decision":String(type||"item").toLowerCase();
/* Save's end for an item made from a message: the peek closes, Review gets the proposal, and Undo removes it (if Review hasn't
   decided it yet) and brings the message back */
export async function alertStaged(){ const d=shared.CUR&&shared.CUR.alertDone; closePanel(); if(!d) return;
  await reloadData(); renderToday();
  snack(`Staged the new ${d.word} for Review: “${String(d.title).slice(0,60)}”`,()=>alertUnstage(d)); }
export async function alertUnstage(d){ let ok=false;
  try{ ok=await vq(async()=>{ const path="system/staging/"+d.name; if(!/^proposed-[\w.-]+-dashboard(-\d+)?\.json$/.test(d.name)||!await shared.VW.exists(path)) return false;
      const data=JSON.parse(await shared.VW.read(path)); if((data.items||[]).some(/** @param {any} i */i=>i.applied||i.decision!=="pending")) return false;
      await shared.VW.remove(path); return true; }); }catch(e){ ok=false; }
  if(!ok){ snack("Already decided in Review: undo it in Activity"); return; }
  const c=d.al.cand?{cand:d.al.cand}:{}, u=await api("/api/alerts/undo",{ids:[d.al.id],...c});
  const a=(VIPD().alerts||[]).find(z=>z.id===d.al.id), it=a&&d.al.cand?(a.candidates||[]).find(/** @param {any} x */x=>x.n===d.al.cand):null;
  if(it){ delete it.made; delete it.dismissed; if(a) delete a.seen; } else if(a){ delete a.seen; delete a.made; }
  VIPNOTED.add(d.al.id); vipBadge(); await reloadData(); renderToday();
  snack(u.ok?`Undone: the new ${d.word} is no longer staged, and the message is back in To decide`:`Unstaged; the message wasn't put back: ${u.message||"try again"}`); }
/* why Draft from the message can't run, or "" */
export function alertDraftWhy(al){ return /^(private|confidential)$/i.test(al.marker||"")?`Not for a ${al.marker.toLowerCase()} message`:!draftOn("sharpen")?"Sharpen a vague action is off in Settings › Advanced › AI drafts":!viaServer()?"Drafting needs the live server":""; }
/* the strip at the top of the peek: where it came from, the type, Draft from the message, Save and Cancel */
export function alertPeekDraw(x,k){ let el=$("#pkAlert"); const al=shared.CUR&&shared.CUR.mode==="new"&&!shared.CUR.staged?shared.CUR.alert:null;
  if(!al){ if(el) el.hidden=true; return; }
  if(!el){ const d=$("#pkDraft"); if(d) addHTML(d,"afterend",html`<div class="pk-alert" id="pkAlert" role="group" aria-label="Made from a message"></div>`); else addHTML($("#pkScroll"),"afterbegin",html`<div class="pk-alert" id="pkAlert" role="group" aria-label="Made from a message"></div>`); el=$("#pkAlert"); }
  const cur=alertTypeOf(k,x), why=alertDraftWhy(al), when=vipWhen({sent:al.sent}), key=[al.id,cur,why].join("|"); el.hidden=false;
  if(el.dataset.key===key) return; el.dataset.key=key;   /* drawn once: a redraw between a press and its release would lose the click */
  putHTML(el,html`<div class="pk-alert-from">From ${al.who}’s ${ALERTWORD[al.kind]||"message"}${when?`, ${when}`:""}${al.link?html` · <a href="${al.link}" target="_blank" rel="noopener" class="hlink">Open the message</a>`:""}</div>
    <div class="pk-alert-row"><span class="pk-alert-types" role="group" aria-label="Make it">${ALERTTYPES.map(([t,w])=>html`<button type="button" class="mini" data-alerttype="${t}" aria-pressed="${t===cur?"true":"false"}">${w}</button>`)}</span>
    <button type="button" class="drbtn" data-alertdraft="1" aria-label="Draft from the message" data-tip="${why||"Reads the message (read only) and suggests a sharper title and any date it states. Nothing is saved until you save"}"${why?raw(' aria-disabled="true"'):""}>${raw(ic("spark"))}<span>Draft from the message</span></button>
    <span class="pk-alert-st" role="status" id="pkAlertSt"></span><span class="sp"></span>
    <button type="button" class="btn" data-alertpeek="cancel">Cancel</button><button type="button" class="btn primary" data-alertpeek="save" data-tip="Stages it and dismisses the message (${MOD}↵)">Save</button></div>`); }
export async function alertDraft(){ const al=shared.CUR&&shared.CUR.mode==="new"?shared.CUR.alert:null; if(!al) return;
  const why=alertDraftWhy(al); if(why){ snack(why); return; } const k=shared.CUR.k, nid=shared.CUR.nid, st=$("#pkAlertSt");
  const d=await draftAsk({id:al.id,type:alertTypeOf(k,shared.CUR.draft),...(al.cand?{cand:al.cand}:{})},{url:"/api/alerts/draft",label:"Reading the message",status:h=>{ if(st) putHTML(st,raw(h)); }});
  if(!shared.CUR||shared.CUR.nid!==nid) return;
  if(!d.ok||!d.prefill){ snack(d.message||"No draft came back"); return; }
  const v=d.prefill.values||{}, x=shared.CUR.draft, t=String(v.description??v.decision??"").trim(), due=v.due_date||v.needed_by||"", f=k==="actions"?"upd":k==="raid"?"resp":"why";
  if(t) x.t=t; if(due) x.due=due; if(d.prefill.detail&&!String(x[f]||"").trim()) x[f]=String(d.prefill.detail);
  pkDraw(); const tt=$("#pkTitle"); if(tt){ tt.textContent=x.t; tt.focus(); } snack("Drafted from the message: check it, then save"); }
export function vipBadge(){ const n=VIPS().length; setRailCount("today",n,`${n} message${n===1?"":"s"} to see first`);   /* BL-319: through the sidebar's store; BL-288: never labelled */
  document.title=(shared.RBMARKED?RBMARK:"")+(n?`(${n}) `:"")+BASETITLE; tabTitle(); }
export let VIPNOTED=new Set(VIPS().map(a=>a.id));                 /* alerts already there when the page opened aren't notified again */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootSettings0138(){
$("#settingsBody").addEventListener("click",async e=>{ const b=e.target.closest("[data-ig]"); if(!b) return; const L=[...(SA().ignore||[])], i=+b.dataset.i, k=b.dataset.ig;
  if(k==="add"){ IGEDIT=-1; renderIgnore(); return; }
  if(k==="edit"){ IGEDIT=i; renderIgnore(); return; }
  if(k==="cancel"){ IGEDIT=null; renderIgnore(); return; }
  if(k==="del"){ if(L[i].builtin||!confirm(`Delete the ignore rule “${L[i].name}”?`)) return; const name=L[i].name; L.splice(i,1); if(await saveIgnore(L,`Rule “${name}” deleted`)) renderIgnore(); return; }
  if(k==="save"){ const name=$("#igName").value.trim(), text=$("#igText").value.trim(), where=$$("#igForm [data-igw]").filter(c=>c.checked).map(c=>c.dataset.igw);
    if(!name||!text||!where.length){ snack(!name?"Give the rule a name":!text?"Say what text to match":"Choose where it applies"); return; }
    if(L.some((r,j)=>j!==IGEDIT&&r.name.toLowerCase()===name.toLowerCase())){ snack("Another rule has that name"); return; }
    const rule={name,where,field:$("#igField").value,how:$("#igHow").value,text,on:IGEDIT>=0?L[IGEDIT].on!==false:true};
    if(IGEDIT>=0) L[IGEDIT]=rule; else L.push(rule);
    if(await saveIgnore(L,`Rule “${name}” saved`)){ IGEDIT=null; renderIgnore(); } } });
$("#settingsBody").addEventListener("change",async e=>{ const el=e.target;
  if(el.id==="igField"){ putHTML($("#igHow"),raw(igHowOpts(el.value,$("#igHow").value))); return; }
  if(el.dataset.igon==null) return; const L=(SA().ignore||[]).map(r=>({...r})), r=L[+el.dataset.igon]; r.on=el.checked;
  if(!await saveIgnore(L,`${r.name}: ${r.on?"on":"off"}`)) el.checked=!el.checked; });
}
export function vipNotify(list){ if(VIPD().notify===false||!("Notification" in window)) return;
  list.filter(a=>!VIPNOTED.has(a.id)).forEach(a=>{ VIPNOTED.add(a.id);
    if(Notification.permission==="granted"){ try{ const n=new Notification(String(a.who||"creaite"),{body:a.subject,tag:"creaite-vip-"+a.id}); n.onclick=()=>{ window.focus(); go("today"); n.close(); }; }catch(e){} } });
  if(Notification.permission==="default"&&list.length&&!store.get("creaite-vip-asked",false)){ store.set("creaite-vip-asked",true); try{ Notification.requestPermission(); }catch(e){} } }
export async function vipPoll(){ if(!viaServer()) return; const r=await api("/api/vip"); if(!r.ok) return;
  const before=vipSig(); Object.assign(VIPD(),{alerts:r.alerts||[],last_check:r.last_check});
  if(vipSig()!==before){ vipNotify(VIPS()); vipBadge(); if(shared.VIEW==="today") renderToday(); } }
/* Settings › VIP alerts: the switches, and what "always" can honestly mean */
export function vipSectionHtml(){ const v=VIPD();
  return `<div class="srow"><div>Browser notification<small>When someone you follow writes, as well as the line on Today; your browser asks once. Whether to tell you, and how often to check, are in Essentials › People I follow. Choose who you follow in People and projects › People.</small></div><div><input type="checkbox" class="switch" data-vipk="notify" ${v.notify!==false?"checked":""} aria-label="Browser notification"></div></div>`; }
/* BL-99 in Work, Draft email and early warnings: a VIP chip on owners and makers, a VIP filter ("+ Filter"), a note
   in the Draft email when it goes to a VIP, and the "overdue item owned by a VIP" signal in Settings › Early warnings */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootSettings0140(){
document.addEventListener("click",e=>{ const b=e.target.closest("[data-alertdo],[data-alerttype],[data-alertdraft],[data-alertpeek]"); if(!b) return; e.preventDefault(); e.stopPropagation();
  const cand=Number(b.dataset.cand||0)||undefined;                                 /* BL-334: one candidate item of a conversation */
  if(b.dataset.alertdo==="dismiss") alertDismiss(b.dataset.id,cand); else if(b.dataset.alertdo==="make") alertMake(b.dataset.id,b.dataset.ctype||"",undefined,cand);
  else if(b.dataset.alerttype&&shared.CUR&&shared.CUR.alert){ if(b.getAttribute("aria-pressed")==="true") return; const x=shared.CUR.draft, t=String($("#pkTitle")?.textContent||x.t||"").trim(); alertMake(shared.CUR.alert.id,b.dataset.alerttype,{t,due:x.due},shared.CUR.alert.cand||undefined); }
  else if(b.dataset.alertdraft) alertDraft(); else if(b.dataset.alertpeek==="save") pkSaveAndClose(); else if(b.dataset.alertpeek==="cancel") closePanel(); },true);   /* BL-296 */
PKDRAW.push(alertPeekDraw);
setInterval(vipPoll,60*1000);
vipBadge();
/* Review: proposals from a VIP (flag "vip", set by sweep.py stage) first, labelled VIP */
/* the VIP chip on a person's page and in Settings › People; the VIP field in the person dialog (when editing) */
FX.vip=new Set();
["actions","raid","decisions"].forEach(t=>FDEFS[t].push(["vip","People I follow",()=>[["yes",t==="decisions"?"Made by someone I follow":"Owned by someone I follow"],["no","Not followed"]],x=>vipKind(x.o||x.by)?"yes":"no",1]));
WSIG.push(["vip_overdue","Overdue item owned by someone you follow closely","days","Overdue by at least (days)"]);
$("#settingsBody").addEventListener("change",async e=>{ const el=e.target, k=el.dataset.vipk; if(!k) return;
  const val=el.type==="checkbox"?el.checked:Math.max(5,Number(el.value)||30); const was=VIPD()[k];
  if(await writeSettings({["vip."+k]:val})){ VIPD()[k]=val; snack("Saved to settings.json"); if(k==="notify"&&val&&"Notification" in window&&Notification.permission==="default") Notification.requestPermission(); }
  else if(el.type==="checkbox") el.checked=!!was; else el.value=was; });
}
/* ===== BL-252 (fix-small-17) ===== how many commands ask creaite's guard refused in the last 7 days, by shape (a pipe, a redirect,
   cd … &&): the server sends fixed words and counts only, never a command (BL-102). A rise means the instruction isn't holding. */
export const diagRefusals=()=>SERVED?row("Refused commands",`<span id="diagRefused">${(DIAG.refusals||[]).length?esc(DIAG.refusals.map(x=>`${x.count} × ${x.shape}`).join(", ")):"None in the last 7 days"}</span>`,
  "Commands ask creaite's guard refused in the last 7 days, by shape. Counts only, never the command. A rise means its instruction to run each script on its own isn't holding"):"";
/* ===== end BL-252 ===== */
/* ===== BL-263 (fix-doctor-errors) ===== errors that keep coming back, with their first and last times: live (seen in the last
   day) or stopped. The server sends the logged area and message (IDs, paths and counts only, BL-102). */
export const diagRepeats=()=>SERVED&&(DIAG.repeats||[]).length?row("Repeated errors",`<span id="diagRepeats">${DIAG.repeats.map(g=>`${g.count} × ${esc(g.area)}: ${esc(g.message)} — ${esc(g.span)}${g.live?"":" (stopped)"}`).join("<br>")}</span>`,
  "Errors seen three or more times in the last 7 days. Only one seen in the last day is a warning; older ones have stopped"):"";
/* ===== end BL-263 ===== */
export function diagCardHtml(){ const off=SERVED?"":"disabled";
  const h=`<div class="card" id="diagCard" data-sec="diag"><h2>Diagnostics</h2>${SERVED?"":'<p class="sub">The log is written by the live server: start it to see errors here.</p>'}
   ${row("Log level",`<select id="diagLevel" ${off}><option value="info" ${DIAG.level==="info"?"selected":""}>info</option><option value="debug" ${DIAG.level==="debug"?"selected":""}>debug</option></select>`,"info keeps a line for what creaite did and for every error, for the last 7 days; debug adds detail while you chase a fault")}
   ${row("Log folder",`<button class="btn" id="diagOpen" ${off}>Open the folder</button>`,`${DIAG.days} day${DIAG.days===1?"":"s"} of log, in system/logs`)}
   ${row("Report",`<button class="btn" id="diagCopy" ${off}>Copy diagnostics</button>`,"The version, the health check, the safe settings and the last 200 log lines, for pasting into a chat: no names, addresses or paths")}
   ${diagRefusals()}${diagRepeats()}
   <div class="pph" style="margin-top:10px">Latest errors <span class="sub">· last 7 days</span> <button class="mini" id="diagRefresh" ${off}>Refresh</button></div>
   <div id="diagList">${DIAG.errors.length?DIAG.errors.map(diagErr).join(""):'<div class="sub">No errors in the last 7 days.</div>'}</div><div id="diagOut"></div></div>`;
  if(shared.VIEW==="settings"){ ebMarkSeen(); setTimeout(errBanner,0); } return h; }   /* opening Diagnostics counts as seeing them */
export function diagRedraw(){ const c=$("#diagCard"); if(c) swapHTML(c,raw(diagCardHtml())); setApplySearch(); }
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootSettings0155(){
/* BL-180 (sprint-peek-new): the header's "n errors in the last day" link is gone; the errors banner below the header replaces it */
document.addEventListener("click",async e=>{
  if(e.target.closest("[data-diag]")){ e.preventDefault(); go("settings","diag"); return; }
  if(e.target.closest("#diagRefresh")){ await diagLoad(); diagRedraw(); return; }
  if(e.target.closest("#diagOpen")){ openPath("system/logs"); return; }
  if(e.target.closest("#diagCopy")){ const r=await api("/api/diagnostics",{report:true}); if(!r||!r.ok){ snack("Couldn't build the report"); return; }
    try{ await navigator.clipboard.writeText(r.report); copied(e.target.closest("#diagCopy")); snack("Diagnostics copied: paste them into the chat"); }
    catch(err){ putHTML($("#diagOut"),html`<textarea id="diagReport" readonly aria-label="Diagnostics report"></textarea><div class="sub">Select all and copy: the browser wouldn't copy it for you.</div>`); $("#diagReport").value=r.report; $("#diagReport").select(); } } });
document.addEventListener("change",async e=>{ const el=e.target; if(el.id!=="diagLevel") return; const was=DIAG.level;
  if(await writeSettings({"logging.level":el.value})){ DIAG.level=el.value; snack(`Log level saved: ${el.value}`); } else el.value=was; });
if(SERVED) diagLoad().then(()=>{ status(); if(shared.VIEW==="settings") renderSettings(); });
}
/* ===== BL-165 (sprint-polish-2) ===== wide tables show that they scroll. Every table frame (.tbl) in the page whose table is wider
   than the frame gets the cue: a fade at the right edge and a "more columns →" button (it scrolls right by most of the frame),
   both gone once scrolled to the end, and a soft edge beside the first column once scrolled from the start. The first column
   stays fixed while the rest scrolls (.xstick), unless it is over half the frame, when it scrolls too (a fixed column that wide
   would leave no room to read the rest). Kept up to date on any render, scroll or resize. Help's tables are left alone. */
export function xcueOne(f){ const t=f.querySelector(":scope>table"); let c=f.querySelector(":scope>.xcue");
  const over=!!t&&f.offsetParent!==null&&getComputedStyle(f).overflowX!=="visible"&&t.scrollWidth>f.clientWidth+1;
  if(!over){ if(c) c.remove(); f.classList.remove("xscroll","xstick"); return; }
  if(!c){ addHTML(f,"afterbegin",html`<div class="xcue" aria-hidden="false"><div class="xfade l"></div><div class="xfade r"></div><button type="button" class="xmore" aria-label="More columns: scroll right">more columns →</button></div>`); c=f.firstElementChild; }
  if(!f.dataset.xc){ f.dataset.xc="1"; f.addEventListener("scroll",()=>xcueOne(f),{passive:true}); }
  f.classList.add("xscroll"); const first=t.querySelector("tr>:first-child"), fw=first?first.getBoundingClientRect().width:0, stick=fw>0&&fw<=f.clientWidth*.5;
  f.classList.toggle("xstick",stick); f.style.setProperty("--xstick",(stick?fw:0)+"px");
  c.style.width=f.clientWidth+"px"; c.querySelectorAll(".xfade").forEach(x=>x.style.height=f.clientHeight+"px");
  c.classList.toggle("end",f.scrollLeft+f.clientWidth>=f.scrollWidth-2); c.classList.toggle("moved",f.scrollLeft>1); }
export function xcueAll(){ shared.XCQ=0; $$(".content .tbl").forEach(f=>{ if(!f.closest("#v-help")) xcueOne(f); }); }
   /* the list's frame narrowed by the item panel (not only the window): it scrolls inside rather than running under the panel */
/* ===== end BL-165 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootSettings0163(){
new MutationObserver(ms=>{ if(ms.some(m=>![...m.addedNodes,...m.removedNodes].every(n=>n.nodeType===1&&n.classList.contains("xcue")))) xcueSoon(); }).observe($(".content"),{childList:true,subtree:true});
if(window.ResizeObserver) new ResizeObserver(xcueSoon).observe($(".content"));
addEventListener("resize",xcueSoon);
document.addEventListener("click",e=>{ const b=e.target.closest(".xmore"); if(!b) return; e.stopPropagation(); const f=b.closest(".tbl"); f.scrollBy({left:f.clientWidth*.8,behavior:reduced()?"auto":"smooth"}); },true);
if(window.ResizeObserver) new ResizeObserver(()=>requestAnimationFrame(sizeList)).observe($("#workWrap"));
xcueSoon();
}
