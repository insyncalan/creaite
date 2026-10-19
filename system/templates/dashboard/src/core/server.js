// @ts-check
/* core/server.js (BL-231 step 2b): vault access, the live server (`api`, `reloadData`, `applyNow`), proposals (`writeProposal`, `save`), the snackbar and undo, status, the pulse, the event stream and the debug log's error hook.
   Moved from script/ unchanged, apart from `export`, `shared.` for the shared state (state.js) and the steps that ran at load,
   which are now boot…() functions called by src/main.js in today's order. Pieces: 0011-vault-access-step-4b-file-system-access.js, 0012-live-server-step-4c.js, 0013-bl-253-sprint-live-updates.js, 0014-after-bl-253.js, 0015-bl-266-fix-backup-names.js, 0016-after-bl-266.js, 0017-bl-232-fix-as-proposed-capture-edits-eve.js, 0018-after-bl-232.js, 0019-live-apply-undo-snackbar.js, 0020-bl-215-sprint-ui-audit.js, 0021-after-bl-215.js, 0141-chat-and-sweep-the-open-page-refreshes-i.js, 0142-bl-253-sprint-live-updates.js, 0152-debug-log-bl-102-part-2.js */
import { renderReports } from "../components/reporting/ReportsPage.jsx";
import { renderReporting } from "../components/reporting/ReportingSpace.jsx";
import { reportsBadge, spaceCode } from "../stores/reporting.js";
import { renderActivity } from "../activity.js";
import { drawStatusDot } from "../components/StatusDot.jsx";
import { drawToast } from "../components/Toast.jsx";
import { openChat, reattach, say } from "../ask.js";
import { A, DEC, FILES, P, R, REMINDERS, REV } from "./data.js";
import { $, $$, addHTML, esc, html, putHTML, raw } from "./dom.js";
import { typing } from "./keys.js";
import { mCells, mCounts } from "./motion.js";
import { go, tabTitle } from "./nav.js";
import { D, days, fd, fdMd, fdText, mK, mSay, nowStamp, prio, reduced, S, TODAY } from "./page.js";
import { shared } from "./state.js";
import { ovAdd, ovBusy, ovDrop, ovReapply, RECORD_KINDS, RECSTAT, recordsRefresh, saveQueue } from "./instant.js";
import { refreshFiles } from "../files.js";
import { inboxBadge, renderInbox } from "../intake.js";
import { mvEdDraw, mvSig, renderMilestones } from "../milestones.js";
import { drawPanel, errBanner, MD_IMG, markStagedRows, pkReconcile, pkStageDraw, REC } from "../panel.js";
import { drawPrep, renderCockpit, renderProjects } from "../projects.js";
import { setRailCount } from "../stores/rail.js";
import { irAfterData } from "../stores/intakeReview.js";   /* #232-B: the new page redraws after a decision */
import { renderReview, RHL, rvKey, rvSyncChk } from "../review.js";
import { ownerFinal, renderPerson, row, savedNow, vipPoll, WSD, wsNewOf } from "../settings.js";
import { renderToday } from "../today.js";
import { hit, items, renderPeople, renderWork, rvPaint } from "../work.js";
/* ======================= vault access (Step 4b): File System Access API, Chrome or Edge ======================= */
/* The browser remembers the vault folder (IndexedDB). Every write goes through one queue (vq) so concurrent saves
   can't overwrite each other. Edits become proposals in system/staging/; settings go to settings.json. */
export const VDB=()=>new Promise((res,rej)=>{ const q=indexedDB.open("creaite-vault",1); q.onupgradeneeded=()=>q.result.createObjectStore("h"); q.onsuccess=()=>res(q.result); q.onerror=()=>rej(q.error); });
export async function vget(){ try{ const db=await VDB(); return await new Promise(r=>{ const t=db.transaction("h").objectStore("h").get("vault"); t.onsuccess=()=>r(t.result||null); t.onerror=()=>r(null); }); }catch(e){ return null; } }
export async function vput(h){ const db=await VDB(); await new Promise(r=>{ const t=db.transaction("h","readwrite"); t.objectStore("h").put(h,"vault"); t.oncomplete=r; t.onerror=r; }); }
export let VH=null; shared.VSTATE="none"; shared.VQ=Promise.resolve();
export const vq=fn=>{ const run=shared.VQ.then(fn,fn); shared.VQ=run.catch(()=>{}); return run; };
export async function vaultInit(){ if(!("showDirectoryPicker" in window)){ shared.VSTATE="unsupported"; status(); return; }
  VH=await vget(); if(!VH){ shared.VSTATE="none"; status(); return; }
  try{ shared.VSTATE=(await VH.queryPermission({mode:"readwrite"}))==="granted"?"ok":"prompt"; }catch(e){ shared.VSTATE="none"; } status(); }
export async function isVault(h){ try{ const sc=await (await h.getDirectoryHandle("system")).getDirectoryHandle("scripts"); await sc.getFileHandle("paths.py"); await h.getFileHandle("CLAUDE.md"); return true; }catch(e){ return false; } }
export async function vaultConnect(){ try{
    if(VH&&shared.VSTATE==="prompt"){ shared.VSTATE=(await VH.requestPermission({mode:"readwrite"}))==="granted"?"ok":"prompt"; status(); if(shared.VSTATE==="ok") snack("Vault reconnected"); return shared.VSTATE==="ok"; }
    const h=await window.showDirectoryPicker({id:"creaite-vault",mode:"readwrite"});
    if(!await isVault(h)){ snack("That folder isn't the creaite vault. Choose the folder that holds CLAUDE.md and system/."); return false; }
    VH=h; await vput(h); shared.VSTATE="ok"; status(); snack("Vault connected"); return true;
  }catch(e){ if(e.name!=="AbortError") snack("Couldn't connect the vault: "+e.message); return false; } }
export let needVault = async function(){ if(viaServer()||shared.VSTATE==="ok") return true; if(shared.VSTATE==="unsupported"){ snack("Saving needs Chrome or Edge"); return false; } return await vaultConnect(); };
export async function vdir(path,create){ let d=VH; for(const part of path.split("/").filter(Boolean)) d=await d.getDirectoryHandle(part,{create:!!create}); return d; }
export const split=path=>{ const i=path.lastIndexOf("/"); return [path.slice(0,i),path.slice(i+1)]; };
export const FVW={
  async read(path){ const [d,f]=split(path); return await (await (await (await vdir(d)).getFileHandle(f)).getFile()).text(); },
  async write(path,text){ const [d,f]=split(path); const w=await (await (await vdir(d,true)).getFileHandle(f,{create:true})).createWritable(); await w.write(text); await w.close(); },
  async remove(path){ const [d,f]=split(path); await (await vdir(d)).removeEntry(f); },
  async exists(path){ try{ const [d,f]=split(path); await (await vdir(d)).getFileHandle(f); return true; }catch(e){ return false; } },
  async append(path,text){ let old=""; try{ old=await FVW.read(path); }catch(e){} await FVW.write(path,old+text); },
  async upload(path,blob){ await FVW.write(path,blob); } };
/* ======================= live server (Step 4c) ======================= */
/* Served by live_server.py: writes, applies and ask creaite go through it (no folder access needed). Opened as a
   file: folder access is used for saves, and the page looks for a running server to offer the live dashboard. */
export const SERVED=!!D.live&&location.protocol.startsWith("http");
export const OLDSERVER="The live server is older than this dashboard and doesn't know this yet. Restart it: Ctrl+C in its Terminal window, then python3 system/scripts/live_server.py";
/* ===== BL-253 (sprint-live-updates) ===== when the page last saved through the server: its own change event waits for its reload */
export let OWNPOST=0;
/* ===== end BL-253 ===== */
export let api = async function(path,body){ if(!/^\/api\/(here|pulse|vip|files|ask\/running|review\/guesses|review\/rejects|review\/candidates)$/.test(path)) OWNPOST=Date.now();   /* reads are not the page's own saves (BL-315's too) */ try{ const r=await fetch(path,{method:"POST",headers:{"Content-Type":"application/json","X-Creaite-Token":D.token||""},body:JSON.stringify(body||{})});
    const j=await r.json().catch(()=>({ok:false,message:`HTTP ${r.status}`})); if(!r.ok) j.ok=false;
    if(r.status===404&&j.message==="Not found") j.message=OLDSERVER;   /* the page is newer than the running server */
    return j; }
  catch(e){ setLive(false); return {ok:false,message:"The live server isn't reachable"}; } };
export const SVW={ async read(p){ const r=await api("/api/fs",{op:"read",path:p}); if(!r.ok) throw new Error(r.message); return r.text; },
  async write(p,t){ const r=await api("/api/fs",{op:"write",path:p,text:t}); if(!r.ok) throw new Error(r.message); },
  async remove(p){ const r=await api("/api/fs",{op:"remove",path:p}); if(!r.ok) throw new Error(r.message); },
  async exists(p){ const r=await api("/api/fs",{op:"exists",path:p}); return !!r.exists; },
  async append(p,t){ const r=await api("/api/fs",{op:"append",path:p,text:t}); if(!r.ok) throw new Error(r.message); },
  async upload(p,blob){ const data=await new Promise((res,rej)=>{ const fr=new FileReader(); fr.onload=()=>res(String(fr.result).split(",")[1]); fr.onerror=()=>rej(fr.error); fr.readAsDataURL(blob); });
    const r=await api("/api/fs",{op:"upload",path:p,data}); if(!r.ok) throw new Error(r.message); } };
export const viaServer=()=>SERVED&&shared.LIVE;
shared.VW={ read:(...a)=>(viaServer()?SVW:FVW).read(...a), write:(...a)=>(viaServer()?SVW:FVW).write(...a), remove:(...a)=>(viaServer()?SVW:FVW).remove(...a),
  exists:(...a)=>(viaServer()?SVW:FVW).exists(...a), append:(...a)=>(viaServer()?SVW:FVW).append(...a), upload:(...a)=>(viaServer()?SVW:FVW).upload(...a) };
export const oneLine=m=>String(m||"").split("\n").map(x=>x.trim()).filter(Boolean).join(" · ").slice(0,240);
/* #92: tracker.py refuses an apply when a file changed after the item was staged ("write: <path> changed since this proposal was
   made"); said in plain words, with what to do. Only the page's wording: tracker.py's refusal is unchanged. */
export const applyWords=m=>{ const t=String(m||""), f=t.match(/write: (.+?) changed since this proposal was made/);
  return f?`${f[1].split("/").pop()} changed after this item was staged, so nothing was written. Stage it again from the current file, or drop it in Review.`:t; };
/* fresh data after an apply or undo */
/* BL-216: Review keeps its selection and highlight across a reload (rvHold before, rvRestore after) */
export function rvHold(){ const keys=[...RHL].map(n=>REV.find(x=>x.n===n)).filter(Boolean).map(rvKey), t=$$("#reviewBody tr[data-n]")[shared.RSEL], cr=t&&REV.find(x=>x.n===+t.dataset.n); return {keys,ck:cr&&rvKey(cr)}; }
export function rvRestore(h){ if(!h) return; const {keys,ck}=h;
  RHL.clear(); REV.filter(r=>keys.includes(rvKey(r))&&!r.done).forEach(r=>RHL.add(r.n)); rvSyncChk();
  if(shared.VIEW==="review"){ renderReview(); if(ck){ const r=REV.find(x=>rvKey(x)===ck), i=r?$$("#reviewBody tr[data-n]").findIndex(tr=>+tr.dataset.n===r.n):-1; if(i>=0){ shared.RSEL=i; rvPaint(); } } } }
export async function reloadData(){ PULSE.reloads++; try{   /* BL-253: reloads in flight counted */
    const hold=rvHold();
    await (async()=>{ if(!SERVED) return; try{ const r=await fetch("/api/data",{headers:{"X-Creaite-Token":D.token}}); if(!r.ok) return; const n=await r.json(); RECSTAT.full++;
  Object.assign(D,n); [[P,n.projects],[A,n.actions],[R,n.raid],[DEC,n.decisions],[REV,n.review],[FILES,n.files],[REMINDERS,n.reminders]].forEach(([a,b])=>a.splice(0,a.length,...b));
  shared.ACT=n.activity; R.forEach(x=>x.pr=prio(x.imp,x.lik)); shared.DATA_AT=n.data_at||shared.DATA_AT;
  [...A,...R,...DEC,...P].forEach(o=>["t","upd","resp","cm","cmd","reason","current"].forEach(k=>{ if(typeof o[k]==="string") o[k]=(k==="current"?fdMd:fdText)(o[k]); })); shared.ACT.forEach(a=>a.what=fdText(a.what));
  ovReapply();   /* BL-304: a change still saving stays on screen */
  refreshAll(); }catch(e){} })();
    rvRestore(hold);
    if(SERVED&&PULSE.v!=null&&!PULSE.busy){ const r=await pulseGet(); if(r&&!PULSE.stale){ PULSE.v=r.v; PULSE.pending=r.pending; } }   /* BL-110: take the new fingerprint, so his own saves don't cause a second reload */
  }finally{ PULSE.reloads--; }
  await pkReconcile();
  if(SERVED){ await diagLoad(); errBanner(); } }
/* BL-327: the server sent the last built data at once (its first load no longer waits for the file lists and the hub); when
   that data is over a minute old the page fetches the rest straight after its first paint, through the usual reload */
export function bootPageRefresh(){ if(SERVED&&D.page_refresh) reloadData(); }
/* BL-189 (sprint-milestones): every apply but the peek's own leaves the peek's staged changes in staging (hold_peek); pkApply passes peek */
export async function applyNow(o){ const r=await api("/api/apply",o&&o.peek?{}:{hold_peek:true}); await reloadData(); if(!r.ok) r.message=applyWords(r.message); return r; }
export let undoApply = async function(id,ids){ const u=await api("/api/undo",{apply_id:id}); if(!(ids&&await refreshRecords(ids))) await reloadData(); snack(u.ok?"Undone":oneLine(u.message)); };   /* BL-304: ids, just those items again */
/* BL-304: just these items again (Review keeps its selection; the peek's staging is reconciled), or false */
export async function refreshRecords(ids){ if(!SERVED) return false; return await recordsRefresh(ids,{hold:rvHold,restore:rvRestore,after:async()=>{ await pkReconcile(); }}); }
/* several quick decisions (bulk approve) become one apply */
export let APPLYT=null, APPLYN=0;
export function applySoon(){ APPLYN++; clearTimeout(APPLYT); APPLYT=setTimeout(async()=>{ const n=APPLYN; APPLYN=0; const r=await applyNow();
  snack(r.ok?`Applied ${n} decision${n===1?"":"s"}`:"Apply stopped: "+oneLine(r.message),r.ok?()=>undoApply(r.apply_id):null); },600); }
/* drafts and conflicts go through review.py, so its checks run; its questions come back as buttons */
export async function reviewViaServer(r,decision,modes){ const res=await api("/api/review",{file:r.file,ref:r.ref,decision,modes:modes||[]});
  if(res.ok){ if(S.autoApply) applySoon(); else await reloadData(); snack(oneLine(res.message)); return; }
  openChat(); const m=res.message||""; let acts="";
  if(/possible internal content/.test(m)) acts=`<button class="mini" data-rv="retry">I've edited the draft: check again</button><button class="mini" data-rv="as-staged">File it anyway</button>`;
  else if(/differs from the staged items/.test(m)) acts=(/--sync/.test(m)?`<button class="mini" data-rv="sync">Update owners and dates to match the draft</button>`:"")+(r.ref==="meeting"?`<button class="mini" data-rv="refresh">Rebuild the items from the draft</button>`:"")+`<button class="mini" data-rv="as-staged">Keep the items as staged</button>`;
  /* review.py speaks to Claude Code ("2: …, or say “approve 2 --as-staged”"); here the buttons do that */
  await say(m.replace(/^\s*Approved \d+\.\s*/,"").replace(/^\s*\d+:\s*/,"").replace(/,? or say “[^”]*”\.?/g,".").replace(/\n\s*\(say [^)]*\)/g,"").trim(),acts);
  $$("#chLog [data-rv]").forEach(b=>b.onclick=()=>{ $$("#chLog [data-rv]").forEach(x=>x.disabled=true); if(b.dataset.rv==="refresh"){ refreshItems(r); return; } reviewViaServer(r,decision,b.dataset.rv==="retry"?modes:[...(modes||[]),b.dataset.rv]); }); }
/* re-extract: rebuild a meeting's proposed items from its edited draft */
export async function refreshItems(r){ const res=await api("/api/refresh",{file:r.file}); await reloadData();
  openChat(); await say(res.ok?res.message.replace(/^.*problem\(s\)\n/,""):oneLine(res.message)); }
/* BL-149 (sprint-ux): a conflict is settled on its row in Review (Keep current or Use this one), not in the chat. BL-231 step 2b
   folded in the replacement that Today's BL-149 block (script/0027) assigned at load; the chat version it replaced never ran. */
export async function conflictChoice(r){ const tr=document.querySelector(`#reviewBody tr[data-n="${r.n}"]`), b=tr&&tr.querySelector('[data-act="co"]');
  if(shared.VIEW!=="review") go("review"); snack("This conflicts with a newer change: choose Keep current or Use this one on its row"); (b||tr)?.focus?.(); }
export let ALERT0=null; shared.LIVELINK=false;
export async function checkLive(){ if(SERVED){ try{ const r=await fetch("/health",{cache:"no-store"}); setLive(r.ok); }catch(e){ setLive(false); } return; }
  /* ===== BL-212 (sprint-ui-audit) ===== /health sends no cross-origin header now, so a page opened from a file can't read it;
     a no-cors request still resolves when something answers on the port and fails when nothing does */
  try{ await fetch(`http://127.0.0.1:${S.port}/health`,{cache:"no-store",mode:"no-cors"}); shared.LIVELINK=true; }catch(e){ shared.LIVELINK=false; } status(); }
export const z2=n=>String(n).padStart(2,"0");
export const stampFile=()=>{ const d=new Date(); return `${TODAY}-${z2(d.getHours())}${z2(d.getMinutes())}${z2(d.getSeconds())}`; };
/* ===== BL-266 (fix-backup-names) ===== a backup's name is stamped to the second; two saves in one second must not overwrite
   the first backup, so a taken name gets -2, -3 and so on, as writeProposal does */
export async function freeBackup(stem,ext){ const s=stampFile(); let name=`${stem}${s}${ext}`, i=2;
  while(await shared.VW.exists(name)) name=`${stem}${s}-${i++}${ext}`; return name; }
/* ===== end BL-266 ===== */
export const stampFull=()=>{ const d=new Date(); return `${TODAY} ${z2(d.getHours())}:${z2(d.getMinutes())}:${z2(d.getSeconds())}`; };
/* UI fields → tracker fields */
export const FIELD={actions:{t:"description",p:"project",ws:"workstream",o:"owner",pr:"priority",due:"due_date",st:"status",raised:"raised",closed:"closed",upd:"latest_update",client:"client_visible",cm:"client_message",ms:"milestone"},
  raid:{t:"description",p:"project",type:"type",ws:"workstream",o:"owner",resp:"response_action",due:"due_date",imp:"impact",lik:"likelihood",st:"status",raised:"raised",closed:"closed",client:"client_visible",cm:"client_message",ms:"milestone"},
  decisions:{t:"decision",p:"project",by:"made_by",date:"date",client:"client_visible",cmd:"client_message",st:"status",due:"needed_by",why:"reasoning",opts:"options",revisit:"revisit",replaces:"replaces"}};   /* BL-53 */
/** @returns {Record<string, any>} the record's values under the tracker's column names */
export function toDb(k,o){ const v={}; for(const [ui,db] of Object.entries(FIELD[k]||{})) if(ui in o){ let x=o[ui]; if(ui==="client") x=x?1:0; if(x===""||x===undefined) x=null; v[db]=x; } return v; }
/* a proposal file in the staging format, already approved (source_run: dashboard) */
export function writeProposal(items,extra){ return vq(async()=>{ let name=`proposed-${stampFile()}-dashboard.json`, i=2;
  while(await shared.VW.exists("system/staging/"+name)) name=`proposed-${stampFile()}-dashboard-${i++}.json`;
  const data=Object.assign({created:stampFull().replace(" ","T"),source_run:"dashboard",files:[],items:items.map((it,j)=>Object.assign({n:j+1,match:"strong",flags:[],decision:"approved"},it))},extra||{});
  await shared.VW.write("system/staging/"+name,JSON.stringify(data,null,2)+"\n"); return name; }); }
export let editProposal = function(file,mut){ return vq(async()=>{ const path="system/staging/"+file; let data; try{ data=JSON.parse(await shared.VW.read(path)); }catch(e){ throw new Error("that proposal has already been applied or removed"); } const apWas=apSnap(data); mut(data); apStamp(data,apWas); await shared.VW.write(path,JSON.stringify(data,null,2)+"\n"); }); };
/* ===== BL-232 (fix-as-proposed): capture edits. Every page edit of a proposal goes through editProposal, which (as
   tracker.stamp_as_proposed does for review.py and minutes.py) gives an item whose values (new) or changes (update) the
   edit altered a write-once as_proposed copy of what they were. One that has it keeps it; one whose as_proposed an
   Undo took away isn't given another. ===== */
export const apKey=v=>JSON.stringify(v,(k,x)=>x&&typeof x==="object"&&!Array.isArray(x)?Object.fromEntries(Object.keys(x).sort().map(n=>[n,x[n]])):x);
export function apSnap(data){ const m=new Map(); (data.items||[]).forEach(it=>{ if(!it||typeof it!=="object") return; const part=it.op==="update"?"changes":"values", v=it[part];
  m.set(it.n,{op:it.op,part,had:"as_proposed" in it,key:v&&typeof v==="object"?apKey(v):null,copy:v&&typeof v==="object"?JSON.parse(JSON.stringify(v)):null}); }); return m; }
export function apStamp(data,was){ (data.items||[]).forEach(it=>{ const w=it&&was.get(it.n); if(!w||w.had||w.key===null||w.op!==it.op||it.applied||"as_proposed" in it) return;
  if(apKey(it[w.part]??null)!==w.key) it.as_proposed=w.copy; }); }
/* ===== end BL-232 ===== */
/* save = the change on screen at once (BL-304), then the proposal written and, with auto-apply, applied in the background, one
   save at a time in the order made. `opt.recs` ([{k, id, f}], the items and fields it changes) makes it a record edit: it
   returns at once, the rows show a hollow "saving" dot until it is applied, a live update never clobbers it, and only those
   items are fetched again afterwards. Without it (milestones, workstreams, the register…) the caller waits, as before, and
   the page reloads all its data. A refused write or apply puts the record back, says why, and offers Retry. Undo works
   while it is still saving (nothing is written, or what was applied is undone) as after. */
export let SNACKOP=null;
export async function save(what,items,extra,doIt,undoIt,by,opt){
  { const nv=shared.WSNEW;
    if(nv&&(items||[]).some(i=>["actions","raid"].includes(i.table)&&String((i.values||i.changes||{}).workstream||"").toLowerCase()===nv.name.toLowerCase()
        &&((i.values||{}).project||(i.changes||{}).project||String(i.id||"").split("-")[0])===nv.project)){
      if(nv.lead){ const o=await ownerFinal(nv.lead); if(o===null) return false; nv.lead=o; }
      const {item,row}=wsNewOf(nv);
      items=[item,...items]; const d0=doIt, u0=undoIt;
      doIt=()=>{ (D.ws_table=D.ws_table||[]).push(row); if(d0) d0(); }; undoIt=()=>{ const i=WSD().indexOf(row); if(i>=0) D.ws_table.splice(i,1); if(u0) u0(); };
      shared.WSNEW=null; if(shared.CUR) shared.CUR.wsNew=null; what+=` (new workstream ${nv.name})`; opt={...(opt||{}),wsNew:true}; } }   /* BL-58: a new workstream goes with the first item that uses it */
  if(!await needVault()) return false;
  const recs=(opt&&opt.recs)||[], quick=recs.length>0, op={what,items,extra,doIt,undoIt,by,opt:opt||{},recs,state:"queued",cancel:false,rebase:ovBusy(recs)||!!(opt&&opt.retry),name:null,apply_id:null};
  doIt(); ovAdd(recs); refreshAll();   /* BL-304: on screen now, before anything is written */
  const live=viaServer()&&S.autoApply;
  if(quick&&live){ SNACKOP=op; snack(`${what} — saving…`,()=>opUndo(op)); }
  const run=saveQueue(()=>live?saveApply(op):saveStage(op));
  if(quick&&!(opt&&opt.wait)) return true;   /* opt.wait: the caller needs the outcome (ask creaite's field card names the apply) */
  return await run; }
/* a later change to an item an earlier one changed: based on the item as the earlier one left it */
function opRebase(op){ op.items.forEach(it=>{ if(it&&it.based_on!=null&&RECORD_KINDS.includes(it.table)){ const x=REC(it.table,it.id); if(x&&x.updated_at) it.based_on=x.updated_at; } }); }
const opIds=op=>[...new Set(op.items.filter(it=>it&&it.id&&RECORD_KINDS.includes(it.table)).map(it=>it.id))];
const opTargeted=op=>op.recs.length>0&&!op.opt.wsNew&&op.items.every(it=>RECORD_KINDS.includes(it.table)&&it.op!=="new");
/* back on screen as it was: the change's own undo, then what is still saving on top again */
function opRevert(op){ ovDrop(op.recs); op.undoIt(); ovReapply(); refreshAll(); }
async function opDropFile(name){ try{ await vq(async()=>{ const pth="system/staging/"+name; if(await shared.VW.exists(pth)) await shared.VW.remove(pth); }); return true; }catch(e){ return false; } }
async function opFail(op,msg){ op.state="failed"; opRevert(op);
  if(opTargeted(op)&&viaServer()) await refreshRecords(opIds(op));   /* "reloaded it": the item as it is now */
  snack(msg,()=>{ save(op.what,op.items,op.extra,op.doIt,op.undoIt,op.by,{...op.opt,retry:true}); },"Retry"); return false; }
async function saveApply(op){ PULSE.reloads++;   /* its own change event waits for it */
  try{ if(op.cancel){ op.state="cancelled"; return false; }
    if(op.rebase) opRebase(op);
    op.state="writing"; try{ op.name=await writeProposal(op.items,op.extra); }catch(e){ return await opFail(op,"Not saved: "+e.message); }
    if(op.cancel){ await opDropFile(op.name); op.state="cancelled"; return false; }
    op.state="applying"; const res=await api("/api/apply",{hold_peek:true});
    if(!res.ok){ await opDropFile(op.name); return await opFail(op,"Not saved: "+oneLine(applyWords(res.message))); }
    let held=false; try{ held=await shared.VW.exists("system/staging/"+op.name); }catch(e){ held=false; }
    if(held){ await opDropFile(op.name); const ids=opIds(op); return await opFail(op,`Not saved: ${ids.join(", ")||"it"} changed elsewhere; reloaded ${ids.length>1?"them":"it"}`); }   /* held as a conflict: not applied */
    op.state="done"; op.apply_id=res.apply_id; ovDrop(op.recs);
    if(!(opTargeted(op)&&await refreshRecords(opIds(op)))) await reloadData();
    if(op.cancel){ const u=await api("/api/undo",{apply_id:op.apply_id}); if(!(opTargeted(op)&&await refreshRecords(opIds(op)))) await reloadData(); if(!u.ok) snack("Not undone: "+oneLine(u.message)); return false; }
    const undo=()=>undoApply(op.apply_id,opTargeted(op)?opIds(op):null);
    if(!op.recs.length) snack(`${op.what} — saved and applied`,undo);
    else if(SNACKOP===op&&TOAST.open){ TOAST.text=`${op.what} — saved and applied`; shared.UNDO=undo; drawPageToast(); }   /* the same message, its time kept (BL-316: the Toast block) */
    else if(SNACKOP===op) snack(`${op.what} — saved and applied`,undo);   /* the message had gone (Retry hides it as it starts) */
    return true;
  }finally{ PULSE.reloads--; } }
/* Undo pressed while it is still saving: back on screen now; nothing is written, or what was applied is undone */
function opUndo(op){ if(op.state==="done"){ undoApply(op.apply_id,opTargeted(op)?opIds(op):null); return; }
  if(op.state==="failed"||op.cancel) return; op.cancel=true; opRevert(op); snack(`Undone: ${op.what}`); }
/* auto-apply off, or no live server: staged (written, not applied), shown at once with the staged dot until Apply */
async function saveStage(op){ let name;
  try{ name=await writeProposal(op.items,op.extra); }catch(e){ return await opFail(op,"Not saved: "+e.message); }
  ovDrop(op.recs); refreshAll();
  apply(op.what,()=>{},async()=>{ op.undoIt(); ovReapply(); try{ await vq(async()=>{ if(await shared.VW.exists("system/staging/"+name)) await shared.VW.remove("system/staging/"+name); else throw 0; }); }catch(e){ snack(viaServer()?"Already applied: undo it in Activity":"Already applied: use “undo last apply” in Claude Code"); } },op.by,opIds(op)); return true; }   /* BL-149 */
/* settings.json: backup, change, log line per key */
export const SKEY={bgActions:"work.board.group.actions",bgRaid:"work.board.group.raid",bgDecisions:"work.board.group.decisions",boardClosedDays:"work.board.closed_days",flowWeeks:"dashboard.flow_weeks",undatedGrace:"dashboard.undated_grace_days",filesDocs:"dashboard.files_show_documents",showArchived:"dashboard.show_archived",railLabels:"dashboard.rail_labels",helpLine:"help.first_line",listCap:"dashboard.project_list_cap",me:"identity.name",short:"identity.short_forms",defPriority:"defaults.new_action_priority",defActionView:"defaults.actions_status_filter",defRaidView:"defaults.raid_status_filter",defDecisionView:"defaults.decisions_view",dueSoon:"review.due_soon_days",autoApply:"dashboard.auto_apply",theme:"dashboard.theme",palette:"dashboard.palette",motion:"dashboard.motion",remindersOn:"reminders.enabled",weeklyDay:"reminders.weekly_report_day",weeklyTime:"reminders.weekly_report_from",sweepDue:"sweep.due_from",lookback:"sweep.first_run_lookback_days",srcInbox:"sweep.sources.inbox",srcSent:"sweep.sources.sent_items",srcChats:"sweep.sources.teams_chats",srcChannels:"sweep.sources.teams_channels",srcCalendar:"sweep.sources.calendar",possible:"sweep.show_possible_matches",staleDays:"review.stale_after_days",rvAdvance:"review.auto_advance",dupOverlap:"review.duplicate_overlap",overdueDays:"health.at_risk_overdue_days",slipAtRisk:"health.at_risk_milestone_slip_weeks_max",slipOff:"health.off_track_milestone_slip_weeks_over",urgentOff:"health.off_track_urgent_risks_min",port:"live_mode.port",dailyBackup:"backups.daily",ownDomains:"identity.own_domains",catchupSweep:"day.catchup_sweep",catchupAfter:"day.catchup_after_minutes"};
export async function writeSettings(changes){ let sp=null;
    if(shared.SETROW&&Date.now()-shared.SETROW.at<2000){ const box=document.querySelector(`#settingsBody [data-sec="${shared.SETROW.sec}"]`), r=box&&box.querySelectorAll(".srow,.igrow")[shared.SETROW.i];
      if(r){ $$("#settingsBody .mspin").forEach(x=>x.remove()); sp=document.createElement("span"); sp.className="mspin"; sp.setAttribute("role","status"); sp.setAttribute("aria-label","Saving");
        (r.classList.contains("srow")?r.lastElementChild:r).insertAdjacentElement(r.classList.contains("srow")?"afterbegin":"beforeend",sp); } }   /* BL-263: a spinner beside the setting while it is written */
  try{ const ok=await (async()=>{ if(!await needVault()) return false;
  try{ await vq(async()=>{ const path="system/config/settings.json", text=await shared.VW.read(path), js=JSON.parse(text), at=stampFull(), logs=[];
    for(const [key,val] of Object.entries(changes)){ const parts=key.split("."); let o=js; parts.slice(0,-1).forEach(q=>{ if(typeof o[q]!=="object"||o[q]===null) o[q]={}; o=o[q]; }); const last=parts[parts.length-1];
      logs.push(JSON.stringify({at,key,old:o[last]===undefined?null:o[last],new:val})); o[last]=val; }
    await shared.VW.write(await freeBackup("system/backups/settings-",".json"),text); await shared.VW.write(path,JSON.stringify(js,null,2)+"\n"); await shared.VW.append("system/config/settings-log.jsonl",logs.join("\n")+"\n"); }); return true;
  }catch(e){ snack("Settings not saved: "+e.message); return false; } })();
  if(ok) savedNow(); return ok; } finally{ if(sp) sp.remove(); } }
/* a project's CLAUDE.md: Current state is a proposal (file change); the client-report rhythm is a setting */
export const memPath=code=>`projects/${D.folders[code]}/CLAUDE.md`;
export function replaceCurrent(md,text,dropped=[]){ const re=/(^## Current state[^\n]*\n)([\s\S]*?)(?=^## |(?![\s\S]))/m;
  if(!re.test(md)) return md.replace(/\s*$/,"\n\n## Current state\n\n"+text.trim()+"\n");
  const placed=new Set(text.split("\n").map(l=>(l.match(MD_IMG)||[])[2]).filter(Boolean));
  return md.replace(re,(m,h,body)=>{ const lines=body.split("\n"), g=lines.filter(l=>/^_.*_$/.test(l.trim())), im=lines.filter(l=>l.trim().startsWith("![")&&!placed.has((l.match(MD_IMG)||[])[2])&&!dropped.includes((l.match(MD_IMG)||[])[2]));
    return h+"\n"+(g.length?g.join("\n")+"\n\n":"")+text.trim()+"\n"+(im.length?"\n"+im.join("\n")+"\n":"")+"\n"; }); }
export async function setRhythm(code,val){ if(!await needVault()) return false;
  try{ await vq(async()=>{ const path=memPath(code), text=await shared.VW.read(path), re=/(\*\*Client report rhythm:\*\*[ \t]*)([A-Za-z]+)/;
    const m=text.match(re); if(!m) throw new Error(`no “Client report rhythm:” line in ${path}; use cx-edit`);
    await shared.VW.write(await freeBackup(`system/backups/files/${code}-CLAUDE-`,".md"),text); await shared.VW.write(path,text.replace(re,"$1"+val.toLowerCase()));
    await shared.VW.append("system/config/settings-log.jsonl",JSON.stringify({at:stampFull(),key:`client_report_rhythm.${code}`,old:m[2],new:val.toLowerCase()})+"\n"); }); return true;
  }catch(e){ snack("Not saved: "+e.message); return false; } }

/* H3 (#221): one "- **<label>:** <value>" line of a project's CLAUDE.md, the way the rhythm is saved (needs the vault, a copy of the
   file in system/backups/files/, a line in settings-log.jsonl). A line that is missing is added under the rhythm line, or under
   "Client / partner". The line's italic note (_(…)_) stays. Returns whether it was saved; `was` is the old value. */
export function memLineEdit(text,label,val){
  const lab=label.replace(/[.*+?^${}()|[\]\\\/]/g,"\\$&"), re=new RegExp("^([ \\t]*(?:[-*][ \\t]+)?\\*\\*"+lab+":\\*\\*[ \\t]*)([^\\n]*?)([ \\t]*(?:_\\(.*\\)_)?)$","m");
  if(/^(on|off)$/.test(val)){      /* the on/off lines: only the leading on or off is rewritten, anything after it ("on, pending client OK") stays */
    const re2=new RegExp("^([ \\t]*(?:[-*][ \\t]+)?\\*\\*"+lab+":\\*\\*[ \\t]*)(on|off)\\b([^\\n]*)$","mi"), m2=text.match(re2);
    if(m2) return {text:text.replace(re2,(_,a,b,c)=>a+val+c),was:m2[2].toLowerCase()}; }
  const m=text.match(re); if(m) return {text:text.replace(re,(_,a,b,c)=>a+val+(c?c.replace(/^\s*/,"   "):"")),was:m[2].trim()};
  const near=/^([ \t]*(?:[-*][ \t]+)?)\*\*Client report rhythm:\*\*[^\n]*$/m.exec(text)||/^([ \t]*(?:[-*][ \t]+)?)\*\*Client \/ partner:\*\*[^\n]*$/m.exec(text);
  if(!near) return null;
  const at=near.index+near[0].length; return {text:text.slice(0,at)+"\n"+near[1]+"**"+label+":** "+val+text.slice(at),was:""};
}
export async function setMemLine(code,label,val,key){ if(!await needVault()) return false;
  try{ await vq(async()=>{ const path=memPath(code), text=await shared.VW.read(path), r=memLineEdit(text,label,val);
    if(!r) throw new Error(`no “${label}:” line, and no “Client report rhythm:” line to put it under, in ${path}; use cx-edit`);
    if(r.text===text) return;
    await shared.VW.write(await freeBackup(`system/backups/files/${code}-CLAUDE-`,".md"),text); await shared.VW.write(path,r.text);
    await shared.VW.append("system/config/settings-log.jsonl",JSON.stringify({at:stampFull(),key:`${key}.${code}`,old:r.was,new:val})+"\n"); }); return true;
  }catch(e){ snack("Not saved: "+e.message); return false; } }

/* ======================= live, apply, undo, the toast ======================= */
shared.LIVE=!!D.live; shared.HELD=[]; shared.DATA_AT=D.data_at||"";
shared.UNDO=null;
/* BL-316: the message at the foot of the page is the Toast building block (components/Toast.jsx), which keeps BL-215's rules:
   one with Undo stays 10 seconds, a plain one 5; the pointer over it or focus inside it holds it, and leaving starts the full
   time again; Esc hides it (at once when you are on it, otherwise when Esc has nothing else to close); focus that was in it goes
   back where it came from. snack(msg, undo, label) stays the call (and the seam tests replace); it draws the block, at once. */
const TOAST={open:false,text:"",action:"",run:0};
function drawPageToast(){ const host=document.getElementById("toastHost"); if(!host) return;
  drawToast(host,{...TOAST,onAction:()=>{ if(shared.UNDO) shared.UNDO(); },onHide:hideSnack}); }
export let snack = function(msg,undo,label){ shared.UNDO=undo||null;
  Object.assign(TOAST,{open:true,text:msg,action:undo?(label||"Undo"):"",run:TOAST.run+1}); drawPageToast(); };
/** Hide the message (its time is up, Esc, its action, ⌘Z). */
export function hideSnack(){ if(!TOAST.open) return; TOAST.open=false; drawPageToast(); }
/* BL-231: what this block did at load, run in today's order by src/main.js (pieces 0019 and 0020's place). ⌘Z (Ctrl+Z) in Work
   undoes the last change, as Review's does, when focus isn't in a text field (BL-215). */
export function bootToast(){
drawPageToast();
document.addEventListener("keydown",e=>{ if(shared.VIEW!=="work"||!(e.metaKey||e.ctrlKey)||e.shiftKey||e.altKey||e.key.toLowerCase()!=="z") return;
  if(typing()||(e.target.closest&&e.target.closest("dialog,.ddmenu,#chat"))) return;
  e.preventDefault(); if(!shared.UNDO){ snack("Nothing to undo"); return; } const u=shared.UNDO; shared.UNDO=null; hideSnack(); u(); });
}
export const DIAG={level:"info",days:0,errors:[],last24:0,loaded:false};   /* declared before status, which runs at load */
export function status(){ putHTML($("#status"),html`${viaServer()||shared.VSTATE==="ok"?"":html`<button class="mini" id="vaultBtn">${shared.VSTATE==="prompt"?"Reconnect vault":shared.VSTATE==="unsupported"?"Read-only: use Chrome":"Connect vault"}</button>`}${shared.HELD.length?html`<span class="pend">${shared.HELD.length} held</span>`:""}`);   /* BL-71: only what needs an action; Live moved to the rail */
  $("#liveAlert").classList.toggle("on",!shared.LIVE); $("#liveAlert").classList.toggle("found",shared.LIVELINK);
  if(ALERT0===null) ALERT0=$("#liveAlert").innerHTML;
  if(!(shared.LIVELINK&&!SERVED)){ if($("#liveAlert").innerHTML!==ALERT0) putHTML($("#liveAlert"),raw(ALERT0)); }
  else putHTML($("#liveAlert"),html`<b>The live server is running.</b> This copy of the dashboard is the file version; <a href="http://127.0.0.1:${Number(S.port)}/">open the live dashboard</a> to save and apply directly.`); drawStatusDot($("#chSub"),shared.LIVE?{status:"ok",word:"Claude Code on this laptop, working in your vault"}:{status:"off",word:"Live server not running — commands will be copied instead"});   /* BL-316: the StatusDot block */ 
  if(!shared.LOADING) errBanner(); }
/* BL-86: the installed app. The service worker shows an offline page when the server is stopped; the page says "still here"
   every 10 seconds, so a server the launcher started can stop itself when the last window closes. */
export function setLive(on){ const was=shared.LIVE; shared.LIVE=on; if(on&&!was&&SERVED){ reloadData(); reattach(); } if(on&&shared.HELD.length){ const n=shared.HELD.length; shared.HELD.forEach(h=>h()); shared.HELD=[]; shared.DATA_AT=nowStamp(); snack(`Live server back — applied ${n} held change${n===1?"":"s"}`); } status(); }
/* every write goes through apply(): logs to Activity, applies now (or holds), offers Undo */
export function apply(what,doIt,undoIt,by="You, in the dashboard",ids=[]){
  doIt(); const entry={at:nowStamp(),what,by,undo:undoIt};
  const commit=()=>{ shared.ACT.unshift(entry); shared.DATA_AT=entry.at; };
  if(!S.autoApply){ const pend={what,commit,undo:undoIt,ids}; shared.PENDING.push(pend); refreshAll(); snack(`${what} — saved; press Apply to write it`,()=>{ undoIt(); const i=shared.PENDING.indexOf(pend); if(i>=0) shared.PENDING.splice(i,1); refreshAll(); }); return; }   /* BL-304: ids, the staged dot */
  if(shared.LIVE) commit(); else shared.HELD.push(commit);
  refreshAll(); snack(shared.LIVE?`${what} — saved and applied`:`${what} — saved; applies when the server is back`,()=>{ undoIt(); const i=shared.ACT.indexOf(entry); if(i>=0) shared.ACT.splice(i,1); refreshAll(); });
}
shared.PENDING=[];
export async function applyPending(){ if(viaServer()){ const r=await applyNow(); shared.PENDING=[]; refreshAll(); snack(r.ok?oneLine(r.message):"Apply stopped: "+oneLine(r.message),r.ok?()=>undoApply(r.apply_id):null); return; }
  snack("Say “apply” in Claude Code, or start the live server"); }
export function refreshAll(){ const cells=mCells(), cnts=mCounts(), hp=new Map(P.map(p=>[p.code,p.health])), wt=typeof shared.WT==="undefined"?"":shared.WT, v=shared.VIEW;   /* BL-263 */
  if(shared.VIEW==="reports") renderReports(); if(shared.VIEW==="reporting") renderReporting(spaceCode.value);   /* BL-337 */
  status(); renderBadge(); inboxBadge(); if(shared.VIEW==="intake-review") irAfterData(); if(shared.VIEW==="inbox") renderInbox(); if(shared.VIEW==="today") renderToday(); if(shared.VIEW==="work"||shared.VIEW==="mine") renderWork(); if(shared.VIEW==="review") renderReview(); if(shared.VIEW==="activity") renderActivity(); if(shared.VIEW==="cockpit") renderCockpit(shared.COCK); if(shared.VIEW==="projects") renderProjects(); if(shared.VIEW==="people") renderPeople(); if(shared.VIEW==="person") renderPerson(shared.PERSON); if(shared.CUR&&!shared.EDITING) drawPanel(); 
  if(!reduced()&&v===shared.VIEW){
    const hit=[]; if(cells&&wt===shared.WT){ const cols=$$("#workTbl thead th").map(th=>th.dataset.col||""); $$("#workTbl tr[data-row]").slice(0,300).forEach(tr=>[...tr.children].forEach((td,i)=>{ const k=tr.dataset.row+"|"+cols[i]; if(cols[i]&&cells.has(k)&&cells.get(k)!==td.textContent.trim()) hit.push(td); })); }
    if(cnts) $$("#v-today .th .cnt").forEach(e=>{ const k=e.id||e.parentElement.id; if(cnts.has(k)&&cnts.get(k)!==e.textContent.trim()) hit.push(e); });
    if(hit.length>12) mSay(`${hit.length} values changed`); else hit.forEach(td=>{ td.classList.remove("mflash"); void td.offsetWidth; td.classList.add("mflash"); setTimeout(()=>td.classList.remove("mflash"),1400*mK()+100); });
    P.forEach(p=>{ if(hp.has(p.code)&&hp.get(p.code)!==p.health) $$(`[data-cock="${p.code}"] .health,#v-cockpit .health`).filter(el=>shared.VIEW!=="cockpit"||shared.COCK===p.code).forEach(el=>{ el.classList.add("mhchg"); setTimeout(()=>el.classList.remove("mhchg"),900*mK()+100); }); }); }
  pkStageDraw(); markStagedRows();
  if(shared.MVREADY){ const sig=mvSig(); if(sig!==shared.MV.sig){ shared.MV.sig=sig;
      if(shared.VIEW==="milestones"&&!(document.activeElement&&["mvNote","mvRbWhy","mvAdjWhy"].includes(document.activeElement.id))) renderMilestones();
      if(shared.MV.peek&&!shared.MV.add&&!(document.activeElement&&document.activeElement.closest&&document.activeElement.closest("#mvPeek input[type=text],#mvPeek textarea"))) mvEdDraw(); } }   /* BL-245: once the Milestones block has run (a reload with staged peek changes refreshes before it) */
  if(shared.PREPEV&&$("#prepDlg")&&$("#prepDlg").open) drawPrep(); }   /* BL-286 E: an applied edit shows in the Prep popup */
export function renderBadge(){ const n=REV.filter(r=>!r.done).length; setRailCount("review",n); reportsBadge(); tabTitle(); }   /* BL-337: Reports' count */
/* BL-231: what this block did at load, run in today's order by src/main.js (piece 0021's place) */
export function bootLive(){
if(SERVED){ if("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(()=>{});
  const here=()=>{ fetch("/api/here",{method:"POST",headers:{"Content-Type":"application/json","X-Creaite-Token":D.token||""},body:"{}"}).catch(()=>{}); };
  here(); setInterval(here,10000); }
document.addEventListener("click",e=>{ if(e.target.closest("#checkLive")){ checkLive(); snack(SERVED?"Checking…":"Looking for the live server…"); } });
document.addEventListener("click",e=>{ if(e.target.closest("#vaultBtn")) vaultConnect(); });
}
/* ===== Chat and sweep: the open page refreshes itself (BL-110 part 2) ===== */
/* /api/pulse is a fingerprint of file stamps. When it changes the page re-reads its data, unless Alan is editing:
   then a chip in the top bar waits, and the reload happens when the edit ends or the chip is clicked. */
export const PULSE={v:null,pending:null,stale:false,timer:null,busy:false,reloads:0};   /* BL-253: reloads */
export function pulseEditing(withFocus){   /* what must never be disturbed */
  if(shared.EDITING&&shared.CUR) return true; if(shared.CURED) return true; if(document.querySelector("dialog[open]")) return true;
  if(!withFocus) return false; const a=document.activeElement;
  return !!a&&(a.tagName==="INPUT"||a.tagName==="TEXTAREA"||a.tagName==="SELECT"||a.isContentEditable); }
export async function pulseGet(){ try{ const r=await fetch("/api/pulse",{method:"POST",headers:{"Content-Type":"application/json","X-Creaite-Token":D.token||""},body:"{}"}); if(!r.ok) return null; const j=await r.json(); return j.ok?j:null; }catch(e){ return null; } }
export async function pulseReload(r){
  const prev=PULSE.pending; PULSE.v=r.v; PULSE.pending=r.pending; PULSE.stale=false; $("#newChip").classList.remove("on"); clearInterval(PULSE.timer); PULSE.timer=null;
  await reloadData();
  if(prev!=null&&r.pending>prev){ const n=r.pending-prev; snack(`${n} new item${n===1?"":"s"} in Review`); } }
export async function pulseCheck(){
  if(!SERVED||!shared.LIVE||PULSE.busy||document.hidden) return; PULSE.busy=true;
  try{ const r=await pulseGet(); if(!r) return;
    if(PULSE.v==null){ PULSE.v=r.v; PULSE.pending=r.pending; return; }
    if(r.v===PULSE.v) return;
    if(pulseEditing(true)){ PULSE.stale=true; $("#newChip").classList.add("on"); if(!PULSE.timer) PULSE.timer=setInterval(()=>{ if(!pulseEditing(true)) pulseCheck(); },2000); return; }
    await pulseReload(r);
  }finally{ PULSE.busy=false; } }
   /* BL-253: only while the stream is down */
/* ===== end Chat and sweep (refresh) ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js (piece 0141's place) */
export function bootPulse(){
$("#newChip").onclick=async()=>{ if(pulseEditing(false)){ snack("Finish or save what you're editing first; the page refreshes then"); return; }
  const r=await pulseGet(); if(r) await pulseReload(r); };
document.addEventListener("visibilitychange",()=>{ if(!document.hidden) pulseCheck(); });
window.addEventListener("focus",()=>pulseCheck());
if(SERVED){ pulseCheck(); setInterval(()=>{ if(!EVS.up) pulseCheck(); },(S.healthSecs||30)*1000); }
}
/* ===== BL-253 (sprint-live-updates) ===== live updates pushed, not polled. One stream per page, GET /api/events, read with
   fetch (EventSource can't send the X-Creaite-Token header every /api route checks, and a token in the address would reach
   logs). The server says `changed` with the parts that changed within about a second; the page reloads only those parts
   where a route for them exists (files: /api/files; vip: /api/vip) and otherwise does what the pulse does (tracker, review
   and calendar: the fingerprint, then the whole of /api/data, waiting while Alan is editing, the #newChip). settings is
   named but nothing re-reads it in place: settings take effect at the next load, as before. While the stream is down the
   pulse runs every healthSecs as before; the stream is retried with a growing wait. A tab hidden for 10 minutes closes its
   stream and reopens it when shown; leaving the page closes it. After a server restart the retry is refused as stale and
   BL-174's banner says reload; the stream then stays closed. */
export const EVS={up:false,ctl:null,retry:null,wait:1000,hid:null,parts:new Set(),timer:null,opened:0,ids:new Set(),full:false};   /* BL-304: ids, full */
export const EV_FULL=["tracker","review","calendar"], EV_HIDDEN_MS=10*60*1000, EV_QUIET_MS=1200;
export function evStale(){ const b=$("#staleAlert"); return !!b&&!b.hidden; }
export function evOpen(){ if(!SERVED||EVS.ctl||document.hidden||evStale()) return; clearTimeout(EVS.retry); EVS.retry=null;
  const ctl=new AbortController(); EVS.ctl=ctl; EVS.opened++;
  fetch("/api/events",{headers:{"X-Creaite-Token":D.token||""},signal:ctl.signal,cache:"no-store"}).then(res=>evRead(res,ctl))
    .catch(()=>null).finally(()=>evDown(ctl)); }
export async function evRead(res,ctl){ if(!res.ok||!res.body) return;
  EVS.up=true; EVS.wait=1000; const rd=res.body.getReader(), dec=new TextDecoder(); let buf="";
  for(;;){ const {value,done}=await rd.read(); if(done||ctl.signal.aborted) return; buf+=dec.decode(value,{stream:true});
    for(let i=buf.indexOf("\n\n"); i>=0; i=buf.indexOf("\n\n")){ const ch=buf.slice(0,i); buf=buf.slice(i+2); if(!ch.startsWith("data: ")) continue;
      let ev; try{ ev=JSON.parse(ch.slice(6)); }catch(e){ continue; } evOn(ev); } } }
export function evDown(ctl){ if(EVS.ctl!==ctl) return; EVS.ctl=null; EVS.up=false;
  if(ctl.signal.aborted||evStale()) return;                    /* closed on purpose, or the page is out of date (BL-174) */
  pulseCheck();                                                /* the fallback catches anything sent while it was down */
  EVS.retry=setTimeout(evOpen,EVS.wait); EVS.wait=Math.min(EVS.wait*2,30000); }
export function evClose(){ clearTimeout(EVS.retry); EVS.retry=null; const c=EVS.ctl; if(c){ c.abort(); EVS.ctl=null; EVS.up=false; } }
export function evOn(ev){ if(ev.type==="hello"){ pulseCheck(); return; }  /* a (re)connect: anything missed meanwhile shows now */
  if(ev.type!=="changed") return; (ev.parts||[]).forEach(p=>EVS.parts.add(p));
  if((ev.parts||[]).includes("tracker")){ const ids=ev.ids&&typeof ev.ids==="object"?ev.ids:null;   /* BL-304: the items the tracker's change log names */
    if(!ids||Object.keys(ids).some(t=>!RECORD_KINDS.includes(t))) EVS.full=true; else Object.values(ids).forEach(L=>(L||[]).forEach(id=>EVS.ids.add(id))); }
  clearTimeout(EVS.timer); EVS.timer=setTimeout(evFlush,250); }
export async function evFlush(){ EVS.timer=null;
  if(PULSE.reloads>0||Date.now()-OWNPOST<EV_QUIET_MS){ EVS.timer=setTimeout(evFlush,400); return; }  /* the page's own save reloads itself */
  const parts=new Set(EVS.parts), ids=[...EVS.ids], full=EVS.full; EVS.parts.clear(); EVS.ids.clear(); EVS.full=false;
  if(parts.has("files")) refreshFiles(true);
  if(parts.has("vip")) vipPoll();
  /* BL-304: the tracker or Review changed and the event named the items: just those (and Review, Activity) again. The calendar,
     a change to anything but actions, RAID and decisions, a gap in the stream or a failed fetch: the whole of /api/data, as before */
  if(parts.has("calendar")||full){ if(EV_FULL.some(p=>parts.has(p))) pulseCheck(); return; }
  if(!parts.has("tracker")&&!parts.has("review")) return;
  if(pulseEditing(true)){ parts.forEach(p=>{ if(EV_FULL.includes(p)) EVS.parts.add(p); }); ids.forEach(i=>EVS.ids.add(i)); EVS.timer=setTimeout(evFlush,2000);
    $("#newChip").classList.add("on"); return; }   /* typing: after, as the pulse waits, with the chip showing that something waits */
  const prev=PULSE.pending;
  if(!await refreshRecords(ids)){ pulseCheck(); return; }
  if(!PULSE.stale) $("#newChip").classList.remove("on");   /* the pulse's own wait (a full reload still to come) keeps it */
  if(prev!=null&&PULSE.pending!=null&&PULSE.pending>prev){ const n=PULSE.pending-prev; snack(`${n} new item${n===1?"":"s"} in Review`); } }   /* as pulseReload says it */
/* ===== end BL-253 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js (piece 0142's place) */
export function bootEventStream(){
document.addEventListener("visibilitychange",()=>{ clearTimeout(EVS.hid); EVS.hid=null;
  if(document.hidden) EVS.hid=setTimeout(()=>{ if(document.hidden) evClose(); },EV_HIDDEN_MS); else evOpen(); });
addEventListener("pagehide",evClose);
addEventListener("pageshow",e=>{ if(e.persisted) evOpen(); });
if(SERVED) evOpen();
}
/* ===== Debug log (BL-102 part 2) ===== */
/* The page reports its own script errors to the live server's debug log (short fields only; the server takes quoted
   text, addresses and paths out), and Settings › Diagnostics shows the latest errors, opens the log folder, switches the
   level and copies a report to paste into a chat. A quiet link in the top bar appears only when there were errors today. */
shared.DIAGSENT=0;
export const diagHook=(message,source,line)=>{ if(!SERVED||shared.DIAGSENT>=50||/^(Uncaught )?ResizeObserver loop/.test(String(message||""))) return; shared.DIAGSENT++;   /* BL-283: a browser notice, not a fault */
  fetch("/api/log/error",{method:"POST",headers:{"Content-Type":"application/json","X-Creaite-Token":D.token||""},keepalive:true,
    body:JSON.stringify({message:String(message||"").slice(0,300),view:typeof shared.VIEW==="string"?shared.VIEW:"",source:String(source||"").slice(0,300),line:line||0})
  }).then(()=>{ diagLoad(true).then(()=>{ status(); }); }).catch(()=>{}); };
/* #96: one read for the callers that arrive together. A page that opens on Settings asked for the same thing three times in
   50 ms (the card, the start-up read and the redraw it caused). While a read is in flight everyone gets that read; a finished
   one is reused for `ttl` ms; `force` is for a person pressing Refresh, an install or a new error (it waits for the one in
   flight, then reads again). */
export function onceFor(ttl,fn){ let pend=null, at=-Infinity, last;
  const run=()=>{ const p=Promise.resolve().then(fn).then(v=>{ last=v; at=Date.now(); return v; }).finally(()=>{ if(pend===p) pend=null; }); pend=p; return p; };
  return force=>{ if(pend) return force?pend.then(run,run):pend; return !force&&Date.now()-at<ttl?Promise.resolve(last):run(); }; }
export const diagLoad=onceFor(2000,async()=>{ if(!SERVED) return; const r=await api("/api/diagnostics",{}); if(r&&r.ok) Object.assign(DIAG,{level:r.level,days:r.days,errors:r.errors,last24:r.last24,groups:r.groups||[],newest:r.newest||null,refusals:r.refusals||[],repeats:r.repeats||[],loaded:true}); });   /* BL-180: groups and newest feed the errors banner; BL-252: refusals */
export const diagErr=e=>`<details class="diagerr"><summary><span class="x">${esc(fd(e.at.slice(0,10)))} ${esc(e.at.slice(11,16))}</span> · ${esc(e.area)} · ${esc(e.message)}</summary>${e.detail.length?`<pre class="diagtb">${esc(e.detail.join("\n"))}</pre>`:'<div class="sub">No traceback.</div>'}</details>`;
/* BL-231: what this block did at load, run in today's order by src/main.js (piece 0152's place) */
export function bootDebugLog(){
window.addEventListener("error",e=>diagHook(e.message,e.filename,e.lineno));
window.addEventListener("unhandledrejection",e=>diagHook(e.reason&&e.reason.message?e.reason.message:e.reason,"promise",0));
/* BL-255: its .diagerr rules are in style.css, so the page adds no <style> at run time and the policy can list the style hashes */
}

/* BL-231: test seams. A test replaces these through window.api and the rest (core/globals.js puts the
   accessors on window); the page itself never replaces them, so they are `let`, not function declarations. */
export const serverSeams = { api: v => { api = v; }, editProposal: v => { editProposal = v; }, needVault: v => { needVault = v; }, snack: v => { snack = v; }, undoApply: v => { undoApply = v; } };
