// @ts-check
/* settings.js (BL-231 step 2b), moved from script/ by dev/tools/convert_area.py: 0073-settings-page-bl-115-sprint-settings.js, 0074-bl-214-sprint-ui-audit.js, 0075-after-bl-214.js, 0076-bl-235-fix-small-17.js, 0078-after-bl-163-settings-row.js, 0079-people-bl-55-bl-56.js, 0127-workstreams-bl-58-bl-56.js, 0138-sweep-and-alerts-bl-97-bl-99-bl-98.js, 0140-after-bl-152.js, 0153-bl-252-fix-small-17.js, 0154-bl-263-fix-doctor-errors.js, 0155-after-bl-263.js, 0163-bl-165-sprint-polish-2.js.
   Unchanged apart from `export`, `shared.` for the shared state (core/state.js) and the load-time steps, now in
   boot…() functions that src/main.js calls in today's order. */
import { closeDialog, openDialog } from "./components/Dialog.jsx";
import { makeArchiveAskDialog } from "./components/dialogs/PageDialogs.jsx";

import { mdView, pendingEdit, RBMARK, SEARCHCFG } from "./ask.js";
import { A, DEC, open, openOnly, P, PEOPLE, peopleAll, pName, R, REGD, REV, SWEPT, wsKey } from "./core/data.js";
import { effect } from "@preact/signals";
import { h, render } from "preact";
import { essText, Essentials } from "./components/settings/Essentials.jsx";
import { Health } from "./components/settings/Health.jsx";
import { MoreSettings, moreRows, tabOfSetting } from "./components/settings/MoreSettings.jsx";
import { drawTabs } from "./components/Tabs.jsx";
import { $, $$, addHTML, esc, html, ibtn, ic, putHTML, raw, swapHTML } from "./core/dom.js";
import { openPath } from "./core/fields.js";
import { linkAnchor, linkUrl } from "./core/linkUrl.js";
import { mDots } from "./core/motion.js";
import { countLink, go, pLink, tabTitle } from "./core/nav.js";
import { applyMotion, applyTheme, cmdBox, copied, D, fd, ico, isMe, kindOf, MOD, MTICK, nowStamp, reduced, S, store, themeFade, themeOf, THEMES, TODAY, who } from "./core/page.js";
import { openProjectWs, psCat, psQ } from "./stores/projectSettings.js";   /* #228; v2.6: an old #settings/workstreams opens the project's Workstreams */
import { api, applyPending, DIAG, diagErr, diagLoad, editProposal, needVault, oneLine, onceFor, refreshAll, reloadData, save, SERVED, setLive, SKEY, snack, status, toDb, viaServer, vq, writeSettings } from "./core/server.js";
import { shared } from "./core/state.js";
import { catalogue, checkHealth, lastCheckAt, loadCatalogue, query, resetSettings, SAVED, settingOf, startSettingsStore } from "./stores/settings.js";
import { chaseNote, draftAsk, openDraftEmail } from "./drafts.js";
import { refreshFiles } from "./files.js";
import { decLate, decLateWords, decRank } from "./meetings.js";
import { drawPanel, ebMarkSeen, errBanner, openNew, markStagedRows, pkDraw, PKDRAW, pkNewOffer, pkNote, pkSaveAndClose, pkSaving, REC } from "./panel.js";
import { closePanel, decorateWarnings, PKN, WARNS, warnSectionHtml, WICO, WSIG } from "./projects.js";
import { draftOn, renderReview } from "./review.js";
import { railIconSize, railLabelsOn, railSizeNorm, setRailCount } from "./stores/rail.js";
import { personPromises, plur, projLink, renderToday, tl } from "./today.js";
import { cell, FDEFS, FX, groupsOf, hit, hlPrune, items, latesOf, ownersOf, personFlags, personLinks, personRedraw, personTbl, personWork, renderPeople, rows, sizeList, viewsList, xcueSoon } from "./work.js";
/* ===== Settings page (BL-115, sprint-settings) ===== */
/* One page: the categories on the left, the settings on the right. SETSECTIONS is the one list the page is built from.
   An entry has an id, a category, a title, search keywords (`kw`) and `render()`, which returns what goes inside the card.
   With `raw`, `render()` returns the whole card (it carries its own id and data-sec). `elid` is the card's element id
   where something else looks it up; `after()` wires what needs the DOM. A later feature adds a section by adding an entry.
   How a setting saves is unchanged: the handlers below and in the sections' own code write settings.json through
   writeSettings (a backup, a log line, the live server's checks). */
/* v2.6 (#246, Alan 19-10-2026): Settings is tabs. Essentials (the settings that change the day, opened first), Work and
   reports, Sweep and Intake, Reports and minutes, AI drafts, Look and help, Advanced (five sub-tabs, for tuning: most people
   never open it) and Health. Each section's `cat` names its tab (and `sub` its Advanced sub-tab); a section another module
   adds names its own (drafts.js: ai, today.js: health). An older module's category still lands somewhere (CATOF).
   Each catalogue group is drawn once: inside the hand-made card that holds it (`groups`), or as its own card on its tab
   (settings_catalogue.py GROUP_TAB, the `more-*` sections). "People and projects" is no longer a tab, and its three sections have
   left Settings (v2.6, the Settings line): People is the People page (#248), Workstreams and Archive are on each project's
   settings page (#247), and Show archived is on the Projects page (and in Work and reports › Opening views). Their old
   addresses (#settings/people, admin, projects, workstreams) open the new places (SETMOVED, settingsMoved). */
export const SETCATS=[["essentials","Essentials"],["work","Work and reports"],["sweep","Sweep and Intake"],["reports","Reports and minutes"],
  ["ai","AI drafts"],["look","Look and help"],["advanced","Advanced"],["health","Health"]];
export const ADVSUBS=[["review","Review and warnings"],["state","Current state"],["arch","Archiving and backups"],["folders","Folders and OneDrive"],["server","Server, search and logs"]];
/** The old Settings addresses whose sections moved out (v2.6): where each one opens now. "ws" is a project's settings page at
    its Workstreams section (the Projects page when no project is known). */
export const SETMOVED={people:"people",admin:"projects",projects:"projects",workstreams:"ws"};
/** The page an old Settings address opens now, as [view, argument], or null when it is still a Settings address.
    @param {any} t @param {string} [code] the project in hand, for workstreams */
export function settingsMoved(t,code){ const to=SETMOVED[String(t||"").toLowerCase()]; if(!to) return null;
  if(to==="people") return ["people","all"];
  if(to==="ws"){ const c=code&&P.some(p=>p.code===code)?code:""; if(c){ psCat.value="ws"; psQ.value=""; return ["psettings",c]; } }
  return ["projects",null]; }
export const CATOF={general:"look",capture:"sweep",review:"advanced",system:"health"};
export const OLDCATS={general:"You and the look",work:"Work and views",review:"Review and warnings",capture:"Capture and alerts",advanced:"Everything else"};
export const catOf=s=>CATOF[s.cat]||s.cat;
/* Addresses: #settings/<tab> opens that tab; #settings/<sub> an Advanced sub-tab; #settings/<section> (sweep, diagnostics…)
   opens the tab the section is in and scrolls to it. The old ones (prefs, admin, general, capture, system, the old "more")
   still work. */
export const SETOLD={prefs:"essentials",general:"look",capture:"sweep",system:"health",more:"advanced"}, SETALIAS={diagnostics:"diag",updates:"version",backups:"live","live-server":"live","early-warnings":"warnings","ignore-rules":"sweep",follow:"essentials",vip:"essentials",you:"essentials"};
export function setResolve(t){ t=String(t||"").toLowerCase(); if(SETCATS.some(c=>c[0]===t)) return {cat:t};
  if(ADVSUBS.some(c=>c[0]===t)) return {cat:"advanced",sub:t}; if(SETOLD[t]) return {cat:SETOLD[t]};
  const a=SETALIAS[t]||t; if(SETCATS.some(c=>c[0]===a)) return {cat:a};
  const sec=SETSECTIONS.find(x=>x.id===a); return sec?{cat:catOf(sec),sub:sec.sub||null,sec:sec.id}:null; }
export let SECT=null; shared.SCAT="essentials"; shared.SSUB="review"; shared.SQ="";   /* the tab, Advanced's sub-tab, the section to scroll to, the search text */
export const sw=(k)=>`<input type="checkbox" class="switch" data-k="${k}" ${S[k]?"checked":""}>`;   /* BL-279: named by its row's label (row, srName), never its key */
export const tx=(k,ph)=>`<input type="text" data-k="${k}" value="${esc(S[k])}" placeholder="${ph||""}">`;
export const nm=(k)=>`<input type="number" data-k="${k}" value="${S[k]}" min="0" style="width:80px">`;
export const sl=(k,opts)=>`<select data-k="${k}">${opts.map(o=>Array.isArray(o)?`<option value="${o[0]}" ${S[k]===o[0]?"selected":""}>${o[1]}</option>`:`<option ${S[k]===o?"selected":""}>${o}</option>`).join("")}</select>`;
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootSettings0073(){
Object.defineProperty(window,"STAB",{configurable:true,get:()=>shared.SCAT,set:v=>{ const r=setResolve(v); shared.SCAT=r?r.cat:"essentials"; if(r&&r.sub) shared.SSUB=r.sub; SECT=r&&r.sec||null; shared.SQ=""; const q=document.getElementById("setq"); if(q) q.value=""; }});
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
/* ===== BL-09: Archive and Restore =====
   Archive is on each project's settings page (#247), Restore on the Projects page (Show archived). The live server builds the
   change with propose.py (the folder to _Archive, the register row to Retired codes, the project and its items marked archived)
   and puts it on the approval card in ask creaite; Approve applies it through tracker.py apply, and Undo reverses it. A project
   with open items lists them first: Cancel them all and archive, or Stop. */
/* BL-316: the Dialog block (made the first time it opens, components/dialogs/PageDialogs.jsx); Esc or the scrim is Stop */
export function openItemsAsk(name,open){ return new Promise(res=>{ const dlg=$("#parchDlg")||makeArchiveAskDialog();
  putHTML($("#parchBody"),html`<h2 id="parchH">${name} has ${open.length} open item${open.length===1?"":"s"}</h2><p class="sub">Nothing is archived with an item still open.</p><ul class="parchlist">${open.slice(0,30).map(o=>html`<li><b>${o.id}</b> ${o.text}</li>`)}</ul>${open.length>30?html`<p class="sub">and ${open.length-30} more</p>`:""}<div class="acts"><button class="btn" data-a="stop">Stop</button><button class="btn primary" data-a="go">Cancel them all and archive</button></div>`);
  const fin=v=>{ res(v); closeDialog(dlg); }; dlg.querySelector('[data-a="stop"]').onclick=()=>fin(false); dlg.querySelector('[data-a="go"]').onclick=()=>fin(true); dlg.addEventListener("close",()=>res(false),{once:true}); openDialog(dlg); }); }
export async function projArchive(code,action,cancel){ if(!viaServer()){ snack("Archiving needs the live server"); return; }
  const r=await api("/api/project/archive",{code,action,cancel_open:!!cancel});
  if(!r.ok&&(r.open||[]).length&&!cancel){ if(await openItemsAsk(pName(code),r.open)) return projArchive(code,action,true); snack("Stopped: nothing was archived"); return; }
  if(!r.ok){ snack(oneLine(r.message||"It couldn't be prepared")); return; }
  snack(r.message); await pendingEdit(); }
/* ===== end BL-09 ===== */
export const row=(l,c,h)=>{ const id="sr"+(++SRN); return `<div class="srow"><div><span id="${id}">${l}</span>${h?`<small id="${id}h">${h}</small>`:""}</div><div>${srName(c,id,h,l)}</div></div>`; };

/* ===== end BL-214 ===== */
export const SHOWARCH_ROW=()=>row("Show archived projects",sw("showArchived"),"Archived projects' items, and items archived for their age, in Work (tagged Archived), Today and the Excel export. Search finds them either way, marked Archived");
/** v2.6 (#246): a tab's (or sub-tab's) catalogue groups that have no hand-made card, drawn as cards. @param {string} cat @param {string} [sub] */
const moreSection=(cat,sub)=>{ const tab=sub?`advanced/${sub}`:cat;
  return {id:"more-"+(sub||cat),cat,sub,more:true,title:"More",kw:`more settings ${tab}`,mount:el=>render(h(MoreSettings,{covered,tab,skip:EMBEDDED()}),el),
    match:w=>{ const c=catalogue.value; return !!c&&moreRows(c,covered,w).some(x=>tabOfSetting(c,x)===tab&&!EMBEDDED().includes(x.tier==="developer"?"Developer":x.group)); }}; };
export const SETSECTIONS=[
 /* BL-320: a section with `mount` is a Preact component (dev/COMPONENTS.md), drawn into its own box; `match(words)` says
    whether a search finds anything in it. v2.6 (#246): `groups` are the catalogue groups drawn inside this card, after its
    own rows (one card per group). */
 {id:"essentials",cat:"essentials",title:"Essentials",kw:"essentials your day you short forms email domains follow browser notification",
  mount:el=>render(h(Essentials,null),el),match:w=>{ const c=catalogue.value; return !!c&&c.essentials.some(r=>sqHas(essText(r),w)); }},
 {id:"views",cat:"work",title:"Opening views",groups:["Opening views"],kw:"default priority new action actions raid open status filter view opening page sort archived projects show",
  render:()=>row("New action priority",sl("defPriority",["Urgent","High","Medium","Low"]))+row("Actions open with",sl("defActionView",viewsList("actions")))+row("RAID opens with",sl("defRaidView",viewsList("raid")))+row("Decisions open with",sl("defDecisionView",viewsList("decisions")))+SHOWARCH_ROW()},   /* BL-131; BL-09's switch (also on the Projects page, #247) */
 {id:"board",cat:"work",title:"Work board",groups:["Work board"],kw:"board group by actions raid decisions closed days column",
  render:()=>row("Actions board groups by",sl("bgActions",groupsOf("actions")))+row("RAID board groups by",sl("bgRaid",groupsOf("raid")))+row("Decisions board groups by",sl("bgDecisions",groupsOf("decisions")))
   +row("Board shows closed items from the last (days)",nm("boardClosedDays"),"The Closed column on a Work board; Show all brings the rest")},
 {id:"projpage",cat:"work",title:"Project page",groups:["Project page"],kw:"flow weeks undated grace no due date list cap overdue ageing",
  render:()=>row("Flow looks back (weeks)",nm("flowWeeks"),"The project page's Flow card: opened and closed, overdue and ageing over this many weeks (8 or 12 are usual; 4 to 26 work)")
   +row("A new undated item counts as new for (days)",nm("undatedGrace"),"The project page's No due date card shows items raised this recently dimmer, so a fresh item isn't flagged the minute it's made")
   +row("Project page lists show at most",nm("listCap"),"Actions due or overdue; the rest are a link away")},
 {id:"files",cat:"work",title:"Files",groups:["Files"],kw:"files page documents project minutes transcripts reports search intake portfolio excel export",
  render:()=>row("Show project documents",sw("filesDocs"),"Off by default: the Files page lists minutes, transcripts and reports (Weekly, Adhoc and Steerco), and skips the rest of a large engagement folder. Search still reads documents. Steerco is only read; creaite files nothing there.")},
 moreSection("work"),
 {id:"sweep",cat:"sweep",title:"Sweep",groups:["Sweep"],kw:"sweep mail teams inbox sent items chats channels calendar look-back possible matches ignore rules due from promises",
  render:()=>row("First-run look-back (days)",nm("lookback"),"When the sweep runs and what it reads are in Essentials › Your day")
   +row("Show possible matches",sw("possible"))+'<div id="ignMgr"></div>',
  after:()=>renderIgnore()},
 moreSection("sweep"),
 {id:"closeday",cat:"sweep",title:"Close the day",groups:["Close the day"],kw:"close the day evening catch up catch-up sweep before closing minutes shutdown",   /* BL-295; whether to catch up is in Essentials › Your day (BL-320) */
  render:()=>row("Catch up when the last sweep is older than (minutes)",nm("catchupAfter"),"A sweep more recent than this says “Caught up” instead, with Sweep again. Whether the card catches up is in Essentials › Your day")},
 moreSection("reports"),
 {id:"reminders",cat:"reports",title:"Reminders",groups:["Reminders"],kw:"reminders weekly report day dismissed restore",   /* v2.6 (#246): each project's client report rhythm is in that project's settings */
  render:()=>row("Reminders on",sw("remindersOn"),"The weekly report's day and time are in Essentials › Your day; each project's client report rhythm is in that project's settings")
   +row("Dismissed reminders",`<button class="btn" id="remRestore">Restore</button>`,"Brings back reminders dismissed forever")},
 moreSection("ai"),
 {id:"appearance",cat:"look",title:"Appearance",groups:["Look and help","Look and layout"],kw:"theme mode light dark colour palette column widths order reset motion animation reduced icon size",
  render:()=>row("Column widths and order",ibtn("undo","Reset column widths and order",'id="rzReset"',"bd"),"Drag a column edge in Work to resize, or a heading to move it")},
 {id:"help",cat:"look",title:"Help",groups:["Help"],kw:"help start here first run first-run show again welcome",   /* v2.6 (#246): help.start_seen as a quiet button */
  render:()=>row("Show the first-run help again",'<button type="button" class="btn" id="helpAgain" data-setkey="help.start_seen">Show it again</button>',"Help › Start here opens by itself the next time creaite starts, as it did the first time")},
 moreSection("look"),
 {id:"thresholds",cat:"advanced",sub:"review",title:"Review and health",groups:["Review","Health thresholds"],kw:"stale due soon at risk off track overdue slip milestone urgent risks thresholds health review auto advance next proposal duplicate overlap spot check",
  render:()=>row("Stale after (days)",nm("staleDays"))+row("Review: move to the next proposal after a decision",sw("rvAdvance"),"After Approve or Reject, the next undecided row is ready for the keyboard")
   +row("Review: possible duplicate when words overlap at least",`<input type="number" data-k="dupOverlap" value="${S.dupOverlap??0.6}" min="0.1" max="1" step="0.05" style="width:80px">`,"0.6 by default: the share of words a proposal has in common with an open item of the same type in the same project")+row("Due soon means within (days)",nm("dueSoon"))+row("At risk: action overdue more than (days)",nm("overdueDays"))
   +row("At risk: milestone slip up to (weeks)",nm("slipAtRisk"))+row("Off track: slip more than (weeks)",nm("slipOff"))+row("Off track: Urgent risks at least",nm("urgentOff"))},
 {id:"warnings",cat:"advanced",sub:"review",title:"Early warnings",groups:["Early warnings"],elid:"warnSettings",kw:"early warnings signals re-dated repeat risk milestone slip long open key person vip dependency",render:()=>warnSectionHtml()},
 moreSection("advanced","review"),moreSection("advanced","state"),moreSection("advanced","arch"),moreSection("advanced","folders"),moreSection("advanced","server"),
 {id:"health",cat:"health",title:"Health",kw:"health check problems fix",
  mount:el=>render(h(Health,null),el),match:()=>false},
 moreSection("health"),                                         /* Health check: the dismissed problems' Reset; Stop stays last */
 {id:"live",cat:"health",title:"Live server and backups",elid:"liveCard",kw:"live server backups port daily database backup status start terminal",
  render:()=>row("Status",shared.LIVE?'<span class="h-ok">Running</span>':'<span class="h-bad">Stopped</span>',"127.0.0.1, required")
   +row("Mail, Teams and data",esc(`${SWEPT==="never"?"Mail and Teams never swept":`Mail and Teams last swept ${fd(SWEPT)}`} · data as of ${fd(shared.DATA_AT).slice(0,16)}`))
   +row("Port",nm("port"),"The creaite app belongs to this port: if you change it, install the app again and reconnect the vault")
   +`<div class="srow" style="display:block"><div>Start the live server<small>Paste into Terminal</small></div>${cmdBox()}</div><div style="display:flex;gap:8px;margin-top:8px">${ibtn("refresh","Check now",'id="liveCheck"',"bd")}</div>`},
 {id:"diag",cat:"health",title:"Diagnostics",raw:true,kw:"diagnostics log level errors debug copy report folder",render:()=>diagCardHtml(),after:()=>{ if(SERVED) diagLoad().then(()=>{ if(shared.VIEW==="settings") diagRedraw(); }); }},   /* #96: no test of the category: Diagnostics is no longer in "system", so its first read never redrew the card */
 {id:"version",cat:"health",title:"creaite version",raw:true,kw:"version update install release zip undo",render:()=>'<div class="card" id="updCard" data-sec="version"><h2>creaite version</h2><p class="sub">Checking…</p></div>',after:()=>drawUpdates()},
 {id:"danger",cat:"health",title:"Stop the live server",elid:"dangerCard",kw:"stop live server quit",
  render:()=>row("Stop the live server",'<button class="btn danger" id="liveStop" title="Stops the live server; open creaite again from its launcher or Terminal">Stop</button>',"Open creaite again from its launcher or Terminal. Edits wait until it is running again")}];
/** The catalogue groups a hand-made card holds (drawn inside it, never as their own card). */
export const EMBEDDED=()=>SETSECTIONS.flatMap(s=>s.groups||[]);
/* ===== BL-320 (v1.9.2): Settings, calmer, with Health inside =====
   The catalogue (/api/settings/catalogue, stores/settings.js) says, for every setting, whether it differs from its default.
   - Essentials, Health and Advanced's "Everything else" are components (`mount`); they read the catalogue and the page's
     search themselves.
   - Advanced's older cards are drawn as before, then each row that holds a setting gets the "changed" dot and Reset
     (setMark). A row's settings are found from its control's data attribute (ROWKEY); `covered` lists every setting these
     cards show, so "Everything else" lists only the rest.
   - A save on an older card rereads the catalogue (a moment later, once it is written); a save or a Reset anywhere brings
     the page's own copies up to date (setSynced). */
export const ROWKEY={k:v=>SKEY[v],vipk:v=>"vip."+v,drsw:v=>"drafting."+v,wk:v=>"warnings."+v};
/* v2.6 (#246): drafting.* are the AI drafts card's own switches (data-drsw), all but the agenda style; help.start_seen is Look and
   help › Help's button */
export const COVERED_PREFIX=["warnings.","dashboard.rail.","drafting."], COVERED_KEYS=["logging.level","sweep.ignore","vip.notify","reminders.dismissed_forever","dashboard.week_ahead_priorities","help.start_seen"], UNCOVERED=["drafting.agenda_style"];
export const covered=k=>!UNCOVERED.includes(k)&&(Object.values(SKEY).includes(k)||COVERED_KEYS.includes(k)||COVERED_PREFIX.some(p=>k.startsWith(p)));
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
    else if(k==="dashboard.rail_icon_size"){ railIconSize.value=railSizeNorm(v); S.railIconSize=railIconSize.value; }   /* #182 */
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
/* when the catalogue arrives or changes: the older cards' dots follow; a search redraws, as its sections
   may change (a search typed before the catalogue arrived found nothing in Essentials or Everything else) */
effect(()=>{ const c=catalogue.value; if(!c||shared.VIEW!=="settings") return;
  if(shared.SQ.trim()&&!$("#settingsBody").contains(document.activeElement)) renderSettings(); else setMark($("#settingsBody")); });
/* the rail's count needs a recent check: one a minute after start-up when this browser hasn't checked for a day */
if(SERVED&&Date.now()-lastCheckAt()>24*3600*1000) window.setTimeout(()=>{ if(viaServer()) checkHealth(); },60*1000);
}
export const setCard=s=>s.mount?`<div class="setmount" id="set-${s.id}" data-sec="${s.id}" data-mount></div>`:s.raw?s.render():`<div class="card${s.wide?" wide":""}" id="${s.elid||"set-"+s.id}" data-sec="${s.id}"><h2>${s.title}</h2>${s.render()}${s.groups?`<div class="setembed" data-embed="${s.id}" data-mount></div>`:""}</div>`;
export const catName=id=>(SETCATS.find(c=>c[0]===id)||[])[1]||"";
export const subName=id=>(ADVSUBS.find(c=>c[0]===id)||[])[1]||"";
/** Where a section is: "Advanced › Archiving and backups › Archiving and backups"; a `more` section names its tab only. */
export const crumbOf=s=>[catName(catOf(s)),catOf(s)==="advanced"?subName(s.sub||"review"):"",s.more?"":s.title].filter(Boolean).join(" › ");
/** True when a search finds a row in one of the catalogue groups a hand-made card holds. @param {any} s @param {string[]} w */
const embedHit=(s,w)=>{ const c=catalogue.value; return !!(c&&s.groups)&&moreRows(c,covered,w).some(x=>s.groups.includes(x.group)); };
/* Search: sections and rows whose label, help text or keywords hold every word typed, across all categories. A section
   whose title or category matches shows all its rows; otherwise it shows just the rows that match, or all of them when
   only its keywords matched (for example "ignore rules" or "diagnostics"). A mounted section answers for itself (`match`). */
export const sqWords=()=>shared.SQ.toLowerCase().split(/\s+/).filter(Boolean), sqHas=(txt,w)=>w.every(x=>txt.toLowerCase().includes(x));
export const rowText=r=>(r.classList.contains("srow")&&r.firstElementChild&&r.firstElementChild!==r.lastElementChild?r.firstElementChild:r).textContent;
export let SMATCH=new Set();
/* v2.6 (#246): an older card's row is also found by its settings' catalogue words (the label, line and key the catalogue gives
   them), so Settings search finds every setting by the same words wherever it is drawn (not by its key: a keyword match
   still shows the whole card) */
const rowCat=r=>rowKeys(r).map(k=>settingOf(k)).filter(Boolean).map(x=>`${x.label} ${x.line}`).join(" ");
export const rowOK=(r,w)=>sqHas(`${rowText(r)} ${rowCat(r)}`,w);
export function setSearchSections(){ const w=sqWords(); SMATCH=new Set(); const t=document.createElement("div");
  return SETSECTIONS.filter(s=>{ if(s.mount) return s.match(w);
    if(sqHas(`${s.title} ${crumbOf(s)} ${OLDCATS[s.cat]||""}`,w)){ SMATCH.add(s.id); return true; }
    putHTML(t,raw(setCard(s))); setMark(t); const rows=[...t.querySelectorAll(".srow,.igrow")];
    return sqHas(s.kw,w)||rows.some(r=>rowOK(r,w))||embedHit(s,w); }); }
export function setApplySearch(){ if(!shared.SQ.trim()) return; const w=sqWords();
  $$("#settingsBody [data-sec]").forEach(c=>{ if(c.hasAttribute("data-mount")||SMATCH.has(c.dataset.sec)) return; const rows=[...c.querySelectorAll(".srow,.igrow")].filter(r=>!mounted(r)), hit=rows.filter(r=>rowOK(r,w));
    rows.forEach(r=>{ r.hidden=hit.length?!hit.some(h=>h===r||h.contains(r)):false; }); }); }      /* a row inside a matching row (the ignore rules) stays */
export let MOUNTS=[];
export function setUnmount(){ MOUNTS.forEach(el=>render(null,el)); MOUNTS=[]; }
export function renderSettings(){ if(!SETCATS.some(c=>c[0]===shared.SCAT)) shared.SCAT="essentials";
  if(!ADVSUBS.some(c=>c[0]===shared.SSUB)) shared.SSUB="review";
  const searching=!!shared.SQ.trim();
  query.value=shared.SQ.trim();
  if(SERVED&&!catalogue.value) loadCatalogue();
  drawTabs($("#setcatsHost"),{id:"setcats",className:"setcats",label:"Settings categories",vertical:true,controls:"settingsBody",
    items:SETCATS.map(([id,t])=>({id,label:t,data:{scat:id}})),selected:searching?"":shared.SCAT,onSelect:setOpen});   /* BL-316: the Tabs block */
  putHTML($("#setcatsel"),raw((searching?`<option value="">Search results</option>`:"")+SETCATS.map(([id,t])=>`<option value="${id}" ${!searching&&id===shared.SCAT?"selected":""}>${esc(t)}</option>`).join("")));
  const adv=!searching&&shared.SCAT==="advanced";
  const secs=searching?setSearchSections():SETSECTIONS.filter(s=>catOf(s)===shared.SCAT&&(!adv||(s.sub||"review")===shared.SSUB));
  const head=s=>!searching||(s.mount&&!s.more)?"":`<div class="setcrumb">${esc(crumbOf(s))}</div>`;
  setUnmount();
  const none=`No settings match “${shared.SQ.trim()}”.`;
  const top=adv?`<p class="sub advnote">For tuning and rarely changed settings. Everything has a sensible default, so most people never open this.</p><div class="tabhost" id="setsubHost"></div>`:"";
  putHTML($("#settingsBody"),!secs.length?html`<p class="sub setnone" role="status">${none}</p>`:html`${raw(top)}<div class="setstack">${raw(secs.map(s=>head(s)+setCard(s)).join(""))}</div>`);
  if(adv) drawTabs($("#setsubHost"),{id:"subtabs",className:"tabs",label:"Advanced",controls:"settingsBody",
    items:ADVSUBS.map(([id,t])=>({id,label:t,data:{ssub:id}})),selected:shared.SSUB,onSelect:k=>setOpen(k)});   /* v2.6 (#246): Advanced's sub-tabs */
  secs.forEach(s=>{ if(s.mount){ const el=document.getElementById("set-"+s.id); if(el){ MOUNTS.push(el); s.mount(el); } }
    else{ if(s.after) s.after(); const em=s.groups&&document.querySelector(`#settingsBody [data-embed="${s.id}"]`);
      if(em){ MOUNTS.push(em); render(h(MoreSettings,{covered,groups:s.groups,bare:true,all:SMATCH.has(s.id)}),em); } } });
  setMark($("#settingsBody"));
  setApplySearch();
  const b=id=>document.getElementById(id);
  if(b("rzReset")) b("rzReset").onclick=()=>{ shared.RZ={}; store.set("creaite-colwidths",shared.RZ); shared.COLORD={}; store.set("creaite-colorder",shared.COLORD); snack("Column widths and order reset"); };
  if(b("helpAgain")) b("helpAgain").onclick=async()=>{ if(!await writeSettings({"help.start_seen":false})) return; S.helpSeen=false; snack("Help › Start here opens by itself next time creaite starts"); };   /* v2.6 (#246) */
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
const updStatus=onceFor(2000,()=>api("/api/update/status"));   /* #96 */
export async function drawUpdates(force){ const c=document.getElementById("updCard"); if(!c) return;
  if(!viaServer()){ putHTML(c,html`<h2>creaite version</h2><p class="sub">Needs the live server.</p>`); return; }
  const r=await updStatus(force); if(!document.getElementById("updCard")) return;
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
  await drawUpdates(true); updReview("releases",false); }
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
    await drawUpdates(true); updOut(updMsg(res.message,!res.ok)); snack(res.ok?`creaite ${p.to} installed; restart the live server`:"The update didn't install"); }; }
export async function updUndo(btn,keep){ if(!btn.dataset.armed){ btn.dataset.armed="1"; btn.textContent="Confirm undo"; btn.classList.add("danger"); return; }
  btn.disabled=true; const r=await api("/api/update/undo",{keep_database:keep});
  if(!r.ok&&/--keep-database/.test(r.message||"")){ updOut(updMsg("The database has changed since the update; undoing it would lose those changes.",true)+'<div style="margin-top:8px"><button class="btn" id="updKeep">Undo engine and settings only</button></div>');
    document.getElementById("updKeep").onclick=e=>{ e.currentTarget.dataset.armed="1"; updUndo(e.currentTarget,true); }; btn.disabled=false; return; }
  await drawUpdates(true); updOut(updMsg(r.message,!r.ok)); if(r.ok) snack("Update undone; restart the live server"); }
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootSettings0078(){
$("#setcatsel").onchange=e=>{ if(e.target.value) setOpen(e.target.value); };
$("#setq").oninput=e=>setSearch(e.target.value);
$("#setq").onkeydown=e=>{ if(e.key==="Escape"&&shared.SQ){ e.stopPropagation(); e.target.value=""; setSearch(""); } };
$("#settingsBody").addEventListener("change",e=>{ const r=mounted(e.target)?null:e.target.closest(".srow,.igrow"), c=r&&r.closest("[data-sec]");
  shared.SETROW=c?{sec:c.dataset.sec,i:[...c.querySelectorAll(".srow,.igrow")].indexOf(r),at:Date.now()}:null; },true);
$("#settingsBody").addEventListener("change",async e=>{ const el=e.target; const k=el.dataset.k; if(!k||!SKEY[k]) return;
  let v=el.type==="checkbox"?el.checked:el.type==="number"?Number(el.value):el.value; if((k==="sweepDue"||k==="weeklyTime")&&!/^\d{2}:\d{2}$/.test(v)){ snack("Use 24-hour HH:MM"); el.value=S[k]; return; }
  const was=S[k]; if(!await writeSettings({[SKEY[k]]:k==="short"?String(v).split(",").map(x=>x.trim()).filter(Boolean):k==="ownDomains"?(v=String(v).split(",").map(x=>x.trim().toLowerCase()).filter(Boolean)):v})){ if(el.type==="checkbox") el.checked=!!was; else el.value=was; return; }
  S[k]=v; if(k==="theme"||k==="palette"){ themeFade(); applyTheme(); } if(k==="motion") applyMotion(); if(k==="palette") renderSettings(); if(k==="autoApply") renderSettings(); if(k==="filesDocs") refreshFiles(true); if(k==="flowWeeks") reloadData(); if(k==="showArchived") reloadData().then(()=>renderSettings());   /* BL-09 */ status(); snack("Saved to settings.json"); });
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



/* links both ways: an owner name opens that person's page; Alan's own page is My work */
/* a person's address from the register, as a plain mail link when it is one mailbox (core/linkUrl.js judges it), else as plain text */
export const mailLink=e=>{ const u=linkUrl("mailto:"+e); return u?html`<a href="${u}">${e}</a>`:html`${e}`; };   /* a mailto opens the mail app: no target, no rel */
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
  if(!x){ putHTML(el,html`<div class="wrapmax"><nav class="crumb" aria-label="Breadcrumb"><a href="#" data-go="people">People</a><span aria-hidden="true">›</span><span aria-current="page">${name}</span></nav>
    <div style="display:flex;align-items:flex-start;gap:12px;flex-wrap:wrap"><div style="flex:1;min-width:260px"><h1>${name}</h1><p class="sub">Nobody called “${name}” owns an item.</p></div>${raw(ibtn("pencil","Add details",'id="ppEdit" aria-haspopup="dialog"',"bd"))}</div></div>`);
    /* #154: a name that owns nothing and is not on the register still offers the add-person form, so the menu's Add details is never a dead end */
    $("#ppEdit").onclick=async()=>{ const reg=shared.REG.find(y=>y.name===name), res=await askPerson(reg?{edit:true,person:reg}:{details:true,person:pBlank(name)}); if(res&&res.person){ const {name:_,...f}=res.person; await regEdit(name,f); renderPerson(name); } }; return; }
  const p=x.p, items=[...x.oa.map(a=>["actions",a]),...x.or.map(r=>["raid",r])], codes=[...new Set(items.map(([,i])=>i.p))].sort(), cutoff=new Date(TODAY); cutoff.setDate(cutoff.getDate()-RECENT_DEC_DAYS);
  const recent=x.D.filter(d=>d.date>=cutoff.toISOString().slice(0,10)).sort((a,b)=>b.date.localeCompare(a.date)), leads=Object.entries(D.leads||{}).filter(([k])=>personOf(k)===name).flatMap(([,v])=>v);
  putHTML(el,html`<div class="wrapmax"><nav class="crumb" aria-label="Breadcrumb"><a href="#" data-go="people">People</a><span aria-hidden="true">›</span><span aria-current="page">${name}</span></nav>
   <div style="display:flex;align-items:flex-start;gap:12px;flex-wrap:wrap"><div style="flex:1;min-width:260px"><h1>${name}${p||isMe(name)?"":html` <span class="tag warn" title="Owns items but isn’t in the people register">not in register</span>`}</h1>
     <p class="sub" style="margin:2px 0">${p&&(p.org||p.role)?[p.org,p.role].filter(Boolean).join(" · "):"Organisation and role not recorded"}${p&&p.email?html` · ${mailLink(p.email)}`:""}</p>
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
document.addEventListener("click",e=>{ const a=e.target.closest("[data-person]"); if(!a) return; e.preventDefault(); e.stopPropagation(); const n=a.dataset.person; if(isMe(n)) go("mine"); else go("person",n); },true);
/* renderPeople: BL-138 (sprint-all-items) draws the People view in two tabs, in its own section near the end */
document.addEventListener("click",e=>{ const h=e.target.closest("[data-psort]"); if(h&&shared.VIEW==="people"){ const c=h.dataset.psort; shared.PSORT=shared.PSORT.col===c?{col:c,dir:shared.PSORT.dir==="asc"?"desc":"asc"}:{col:c,dir:c==="name"||c==="org"||c==="role"?"asc":"desc"}; const kept=h.contains(document.activeElement); renderPeople(); if(kept){ const b=document.querySelector(`#peopleTbl th[data-psort="${c}"] button.thsort`); if(b) b.focus({preventScroll:true}); } return; }   /* v1.9.5 check 8: the redraw keeps focus on the same heading, so its new aria-sort is read and Enter again reverses */
  const r=e.target.closest("#peopleTbl tr[data-pp]"); if(r&&!e.target.closest("a,button")){ const n=r.dataset.pp; if(isMe(n)) go("mine"); else go("person",n); } });
}
/* ===== Workstreams (BL-58, BL-56) ===== */
/* Workstreams belong to each project, like milestones (tracker.db workstreams): a lead, keywords and aliases help
   creaite match items. The picker offers the project's Active ones; a new name is added on purpose, with suggested
   details, in the same proposal as the item. Each project's settings page edits its own (ProjectWorkstreams.jsx); the project page lists them. */
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
export function wsConfirm(p,name){ const w=wsRow(p,name); if(w&&w.st==="Closed") return `“${w.name}” is retired in ${pName(p)}: choose another (${pName(p)}'s settings › Workstreams lists the ones in use).`;
  if(w) return null; const k=wsKey(p,name.trim());
  if(shared.CUR.wsNew!==k||!$("#wsNewBox")){ shared.CUR.wsNew=k; shared.WSNEW=null; const s=wsSuggest(p,name); $("#wsNewBox")?.remove();
    addHTML($("#f_ws").closest("dd"),"beforeend",html`<div class="wsnew" id="wsNewBox"><div class="sub">New workstream for ${p}, suggested from ${s.items} item${s.items===1?"":"s"}; change anything, then Save again.</div>${raw(WS_FIELDS.map(([f,l])=>`<label>${l}<input type="text" data-wsn="${f}" value="${esc(s[f])}" ${f==="lead"?'placeholder="A person from the people register"':""}></label>`).join(""))}</div>`);
    return `Add “${name.trim()}” to ${p}'s workstreams? Check its details below, then Save again.`; }
  shared.WSNEW={project:p,name:name.trim(),...Object.fromEntries($$("#wsNewBox [data-wsn]").map(i=>[i.dataset.wsn,i.value.trim()]))}; return null; }
shared.WSNEW=null;   /* the new workstream Alan confirmed; kept here because saving a new item closes the panel first */
/* BL-187 (fix-peek-140): the one route for a new workstream: its proposal item (op new, table workstreams) and the row the page
   shows until the apply. Used by the panel's save (below), the project settings' Workstreams and the peek's "Add workstream…". */
export function wsNewOf(nv,src){ const values=Object.fromEntries(Object.entries({project:nv.project,name:nv.name,lead:nv.lead,keywords:nv.keywords,aliases:nv.aliases,channel:nv.channel,source:src||`${S.me} (dashboard), ${TODAY}`}).filter(([,v])=>v));
  return {item:{op:"new",table:"workstreams",values},row:{id:"",p:nv.project,name:nv.name,lead:nv.lead||"",keywords:nv.keywords||"",aliases:nv.aliases||"",channel:nv.channel||"",st:"Active",nA:0,nR:0}}; }
/* the new workstream travels in the same proposal as the item, ahead of it (undo removes both) */

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
/* Review: an item whose workstream isn't one of its project's offers to add it, or to leave it blank */
document.addEventListener("click",async e=>{ const b=e.target.closest("[data-wsq]"); if(!b) return; e.preventDefault(); e.stopPropagation(); const r=REV.find(x=>x.n===+b.dataset.n); if(!r||!await needVault()) return;
  const name=r.ws_suggest, add=b.dataset.wsq==="add", s=add?wsSuggest(r.p,name):null;
  try{ await editProposal(r.file,data=>{ const items=data.items||[], it=items.find(i=>i.n===r.ref); if(!it||it.applied) throw new Error("that proposal has already been applied");
      it.flags=(it.flags||[]).filter(f=>f!=="new-workstream"); delete it.ws_suggest; if(!add) return;
      const known=wsRow(r.p,name), target=it.values||(it.changes=it.changes||{}); target.workstream=known?known.name:name;
      if(!known) items.splice(items.indexOf(it),0,{n:Math.max(0,...items.map(i=>+i.n||0))+1,op:"new",table:"workstreams",values:Object.fromEntries(Object.entries({project:r.p,name,lead:s.lead,keywords:s.keywords,aliases:s.aliases,channel:s.channel,source:`${S.me} in review, ${TODAY}`}).filter(([,x])=>x)),match:"strong",flags:[],decision:"approved"}); }); }
  catch(err){ snack("Not saved: "+err.message); return; }
  r.flags=(r.flags||[]).filter(f=>f!=="new-workstream"); r.ws_suggest=null; if(add&&!wsRow(r.p,name)) (D.ws_table=D.ws_table||[]).push({id:"",p:r.p,name,lead:s.lead,keywords:s.keywords,aliases:s.aliases,channel:s.channel,st:"Active",nA:0,nR:0});
  if(add&&r.rec) r.rec.ws=name; renderReview(); snack(add?`Workstream ${name} will be added to ${pName(r.p)} with this item — check its details in ${pName(r.p)}'s settings › Workstreams`:"Left without a workstream",add?()=>openProjectWs(r.p):undefined,add?"Open its workstreams":undefined); },true);
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
/* BL-342 Part 5: a card with a promise of Alan's to add (or one staged) or a promise that looks kept stays a full card, even
   when he replied last (his promise is usually in that reply) or the thread is otherwise quiet, until he acts on it */
const vipOffers=/** @param {any} a */a=>a.marker!=="private"&&((a.promises||[]).some(/** @param {any} p */p=>p&&(p.state==="offered"||p.state==="staged"))||!!(a.kept&&a.kept.id&&a.kept.open!==false));
export const VIPD=()=>SA().vip||(SA().vip={alerts:[],people:{}}), VIPS=()=>(VIPD().alerts||[]).filter(a=>!a.seen&&(vipOffers(a)||(!a.quiet&&a.state!=="replied")));
/* BL-334: a conversation with nothing for Alan is one quiet line on Today (no buttons, no count), shown the day it was updated */
export const VIPQ=()=>(VIPD().alerts||[]).filter(a=>!a.seen&&a.quiet&&a.state!=="replied"&&!vipOffers(a)&&String(a.updated||"").slice(0,10)===TODAY);
/* BL-342: a thread Alan has answered (his own message after the last one) is one quiet "Replied" line the day he answered; a later message from someone else opens it again */
export const VIPR=()=>(VIPD().alerts||[]).filter(a=>!a.seen&&a.state==="replied"&&!vipOffers(a)&&String(a.replied_at||"").slice(0,10)===TODAY);
/** what changed in the alerts, for a redraw: an updated conversation keeps its ID */
const vipSig=()=>(VIPD().alerts||[]).map(a=>`${a.id}@${a.updated||""}@${a.seen?1:0}@${a.state||""}@${(a.match&&a.match.count)||0}`
  +`@${(a.promises||[]).map(/** @param {any} p */p=>`${p.key}:${p.state}`).join("+")}@${a.kept?`${a.kept.id}:${a.kept.staged?1:0}:${a.kept.open===false?0:1}`:""}`).join();   /* BL-342 Part 5 */
export const vipKind=n=>{ const ppl=VIPD().people||{}; return ppl[n]||ppl[personOf(n)]||""; };
export const VIPKIND={mail:"Email",teams:"Teams",calendar:"Invite"}, BASETITLE=document.title;
export function vipWhen(a){ const d=(a.sent||"").slice(0,10); return d===TODAY?`today ${a.sent.slice(11,16)}`:d?`${fd(d)} ${a.sent.slice(11,16)}`.trim():""; }
/* BL-288: nothing says why a message is shown (who Alan follows is never labelled); BL-296: each has Create work item and
   Dismiss (Undo in the message). BL-319: the messages are rows of Today's Messages section (today.js toDecideRows), newest first; their two icons keep the data-alertdo buttons this file's handler runs. */
export const ALERTWORD={mail:"email",teams:"Teams message",calendar:"invite"};
/* after a row goes: focus to the same button on the row now in its place in Messages (or its first action), else its heading */
export function alertFocus(id,what){ const vis=()=>$$("#tdList > li").filter(l=>!l.hidden), i=vis().findIndex(r=>r.dataset.td==="al"+id); return ()=>{
  const L=vis(), next=L[Math.min(Math.max(0,i),L.length-1)];
  const b=next&&(next.querySelector(`[data-alertdo="${what}"]`)||next.querySelector("[data-tdact]")); if(b){ /** @type {HTMLElement} */(b).focus(); return; }
  const h=$("#hTd"); if(h&&h.offsetParent){ h.tabIndex=-1; h.focus(); return; } const h2=$("#hAttn"); if(h2){ h2.tabIndex=-1; h2.focus(); } }; }
export async function alertDismiss(id,cand){ if(!viaServer()){ snack("Dismiss needs the live server"); return; }
  const c=cand?{cand}:{}, r=await api("/api/alerts/dismiss",{ids:[id],...c}); if(!r.ok){ snack(r.message||"Not dismissed"); return; }
  const a=(VIPD().alerts||[]).find(x=>x.id===id), back=alertFocus(id,"dismiss"), it=cand&&a?(a.candidates||[]).find(/** @param {any} x */x=>x.n===cand):null;
  if(it){ it.dismissed=r.at||nowStamp(); if((a.candidates||[]).every(/** @param {any} x */x=>x.made||x.dismissed)) a.seen=r.at||nowStamp(); }   /* BL-334: that item only; nothing is staged */
  else if(a) a.seen=r.at||nowStamp();
  await vipPoll(); vipBadge(); renderToday(); back();   /* BL-342 N1: the server's counts for the other cards on the same item */
  snack(it?"Item dismissed":"Message dismissed",async()=>{ const u=await api("/api/alerts/undo",{ids:[id],...c}); if(!u.ok){ snack(u.message||"Not undone"); return; }
    if(it){ delete it.dismissed; if(a) delete a.seen; } else if(a){ delete a.seen; delete a.made; } VIPNOTED.add(id); await vipPoll(); vipBadge(); renderToday(); snack("Back in Messages"); }); }
/* BL-342: Handled on a thread's card (Dismiss's effect, recorded as handled) and Log on the matched item (one pending update for Review) */
export async function alertHandled(id){ if(!viaServer()){ snack("Handled needs the live server"); return; }
  const r=await api("/api/alerts/handled",{ids:[id]}); if(!r.ok||!r.handled){ snack(r.message||"Not marked handled"); return; }
  const a=(VIPD().alerts||[]).find(x=>x.id===id), back=alertFocus(id,"handled");
  if(a){ a.seen=r.at||nowStamp(); a.state="handled"; } await vipPoll(); vipBadge(); renderToday(); back();
  snack("Marked handled",async()=>{ const u=await api("/api/alerts/undo",{ids:[id]}); if(!u.ok){ snack(u.message||"Not undone"); return; }
    if(a){ delete a.seen; a.state="open"; } VIPNOTED.add(id); await vipPoll(); vipBadge(); renderToday(); snack("Back in Messages"); }); }
/* BL-342 Part 2: Chase on a thread matched to an item that is waiting on someone else: BL-224's Draft email in Chase mode for that
   item's owner, the item ticked. Nothing is sent or written; the builder falls back to an update request when the item isn't past its date. */
export function alertChase(id){ const a=(VIPD().alerts||[]).find(x=>x.id===id), m=a&&a.match, it=m&&m.id&&REC("actions",m.id);
  if(!it){ snack("That item isn't open any more"); return; }
  const owner=String(it.o||"");
  if(!owner||!PERS().some(y=>y.name===owner)){ snack(`${owner||"The owner"} isn't on the People page, so there's no one to draft to`); return; }
  openDraftEmail(owner,"chase",m.id); }
export async function alertLog(id){ if(!viaServer()){ snack("Log needs the live server"); return; }
  const r=await api("/api/alerts/log",{id}); if(!r.ok){ snack(r.message||"Not logged"); return; }
  const a=(VIPD().alerts||[]).find(x=>x.id===id); if(a&&a.match) a.match.logged=r.logged;
  await reloadData(); renderToday(); snack(r.message||"Staged for Review"); }
/* BL-342 Part 3 B, step 9: "Looks done: close <ID>" stages one pending close of the matched action for Review (nothing is
   applied); Undo takes it back while it is still pending. The page's data is reloaded so the Review count follows. */
export async function alertClose(id,undo){ if(!viaServer()){ snack("Closing needs the live server"); return; }
  const r=await api("/api/alerts/close",{id,...(undo?{undo:true}:{})}); if(!r.ok){ snack(r.message||r.error||"Not staged"); return; }
  const a=(VIPD().alerts||[]).find(x=>x.id===id); if(a) a.closes=r.closes;
  await reloadData(); renderToday(); snack(r.message||(undo?"Taken back":"Staged for Review"),undo?undefined:()=>alertClose(id,true)); }
/* BL-342 Part 5: Add a promise, Dismiss a promise and Looks kept: mark kept, each by the card's ID and the promise's key (never
   its position or words). Add and mark kept stage one pending proposal for Review (nothing is applied) and Undo takes it back
   while it is still pending; Dismiss stages nothing, and its Undo puts the promise back. The page's data is reloaded, so the
   Review count follows. */
/** data-alertdo → [what, undo] for /api/alerts/promise */
const PROMISEDO=/** @type {Record<string,[string,boolean]>} */({promise:["add",false],promiseundo:["add",true],promisedismiss:["dismiss",false],kept:["kept",false],keptundo:["kept",true]});
export async function alertPromise(id,what,key,undo){ if(!viaServer()){ snack("Promises need the live server"); return; }
  const r=await api("/api/alerts/promise",{id,what,key:key||"",...(undo?{undo:true}:{})}); if(!r.ok){ snack(r.message||r.error||"Not staged"); return; }
  const a=(VIPD().alerts||[]).find(x=>x.id===id); if(a){ a.promises=r.promises; a.kept=r.kept; }
  await reloadData(); renderToday(); snack(r.message||(undo?"Taken back":"Staged for Review"),undo?undefined:()=>alertPromise(id,what,key,true)); }
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
  snack(u.ok?`Undone: the new ${d.word} is no longer staged, and the message is back in Messages`:`Unstaged; the message wasn't put back: ${u.message||"try again"}`); }
/* why Draft from the message can't run, or "" */
export function alertDraftWhy(al){ return /^(private|confidential)$/i.test(al.marker||"")?`Not for a ${al.marker.toLowerCase()} message`:!draftOn("sharpen")?"Sharpen a vague action is off in Settings › Advanced › AI drafts":!viaServer()?"Drafting needs the live server":""; }
/* the strip at the top of the peek: where it came from, the type, Draft from the message, Save and Cancel */
export function alertPeekDraw(x,k){ let el=$("#pkAlert"); const al=shared.CUR&&shared.CUR.mode==="new"&&!shared.CUR.staged?shared.CUR.alert:null;
  if(!al){ if(el) el.hidden=true; return; }
  if(!el){ const d=$("#pkDraft"); if(d) addHTML(d,"afterend",html`<div class="pk-alert" id="pkAlert" role="group" aria-label="Made from a message"></div>`); else addHTML($("#pkScroll"),"afterbegin",html`<div class="pk-alert" id="pkAlert" role="group" aria-label="Made from a message"></div>`); el=$("#pkAlert"); }
  const cur=alertTypeOf(k,x), why=alertDraftWhy(al), when=vipWhen({sent:al.sent}), alOpen=al.link?linkAnchor(al.link,"Open the message","hlink"):null, key=[al.id,cur,why].join("|"); el.hidden=false;
  if(el.dataset.key===key) return; el.dataset.key=key;   /* drawn once: a redraw between a press and its release would lose the click */
  putHTML(el,html`<div class="pk-alert-from">From ${al.who}’s ${ALERTWORD[al.kind]||"message"}${when?`, ${when}`:""}${alOpen?html` · ${raw(alOpen)}`:""}</div>
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
  return `<div class="srow"><div>Browser notification<small>When someone you follow writes, as well as the line on Today; your browser asks once. Whether to tell you, and how often to check, are in Essentials › People I follow. Choose who you follow on each project's settings page, under People and partners.</small></div><div><input type="checkbox" class="switch" data-vipk="notify" ${v.notify!==false?"checked":""} aria-label="Browser notification"></div></div>`; }
/* BL-99 in Work, Draft email and early warnings: a VIP chip on owners and makers, a VIP filter ("+ Filter"), a note
   in the Draft email when it goes to a VIP, and the "overdue item owned by a VIP" signal in Settings › Early warnings */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootSettings0140(){
document.addEventListener("click",e=>{ const b=e.target.closest("[data-alertdo],[data-alerttype],[data-alertdraft],[data-alertpeek]"); if(!b) return; e.preventDefault(); e.stopPropagation();
  const cand=Number(b.dataset.cand||0)||undefined;                                 /* BL-334: one candidate item of a conversation */
  if(b.dataset.alertdo==="handled") alertHandled(b.dataset.id); else if(b.dataset.alertdo==="log") alertLog(b.dataset.id); else if(b.dataset.alertdo==="chase") alertChase(b.dataset.id);
  else if(b.dataset.alertdo==="close") alertClose(b.dataset.id,false); else if(b.dataset.alertdo==="closeundo") alertClose(b.dataset.id,true);
  else if(PROMISEDO[b.dataset.alertdo||""]){ const [w,u]=PROMISEDO[b.dataset.alertdo||""]; alertPromise(b.dataset.id,w,b.dataset.pkey||"",u); }   /* BL-342 Part 5 */
  else if(b.dataset.alertdo==="dismiss") alertDismiss(b.dataset.id,cand); else if(b.dataset.alertdo==="make") alertMake(b.dataset.id,b.dataset.ctype||"",undefined,cand);
  else if(b.dataset.alerttype&&shared.CUR&&shared.CUR.alert){ if(b.getAttribute("aria-pressed")==="true") return; const x=shared.CUR.draft, t=String($("#pkTitle")?.textContent||x.t||"").trim(); alertMake(shared.CUR.alert.id,b.dataset.alerttype,{t,due:x.due},shared.CUR.alert.cand||undefined); }
  else if(b.dataset.alertdraft) alertDraft(); else if(b.dataset.alertpeek==="save") pkSaveAndClose(); else if(b.dataset.alertpeek==="cancel") closePanel(); },true);   /* BL-296 */
PKDRAW.push(alertPeekDraw);
setInterval(vipPoll,60*1000);
vipBadge();
/* Review: proposals from a VIP (flag "vip", set by sweep.py stage) first, labelled VIP */
/* the VIP chip on a person's page; the VIP field in the person dialog (when editing) */
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
  if(e.target.closest("#diagRefresh")){ await diagLoad(true); diagRedraw(); return; }
  if(e.target.closest("#diagOpen")){ openPath("system/logs"); return; }
  if(e.target.closest("#diagCopy")){ const r=await api("/api/diagnostics",{report:true}); if(!r||!r.ok){ snack("Couldn't build the report"); return; }
    try{ await navigator.clipboard.writeText(r.report); copied(e.target.closest("#diagCopy")); snack("Diagnostics copied: paste them into the chat"); }
    catch(err){ putHTML($("#diagOut"),html`<textarea id="diagReport" readonly aria-label="Diagnostics report"></textarea><div class="sub">Select all and copy: the browser wouldn't copy it for you.</div>`); $("#diagReport").value=r.report; $("#diagReport").select(); } } });
document.addEventListener("change",async e=>{ const el=e.target; if(el.id!=="diagLevel") return; const was=DIAG.level;
  if(await writeSettings({"logging.level":el.value})){ DIAG.level=el.value; snack(`Log level saved: ${el.value}`); } else el.value=was; });
if(SERVED) diagLoad().then(()=>{ status(); if(shared.VIEW==="settings") renderSettings(); });   /* #96: this redraw is needed (a page restored onto Settings drew before the Set-up card was registered); its reads are now shared */
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
