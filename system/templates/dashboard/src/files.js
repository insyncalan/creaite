// @ts-check
/* files.js (BL-231 step 2b), moved from script/ by dev/tools/convert_area.py: 0068-files.js, 0069-dashboard-pages-bl-87-to-bl-95.js.
   Unchanged apart from `export`, `shared.` for the shared state (core/state.js) and the load-time steps, now in
   boot…() functions that src/main.js calls in today's order. */
import { FILES, fpName, P, pName, WEEKSTART } from "./core/data.js";
import { $, $$, addHTML, html, ibtn, ic, putHTML, raw } from "./core/dom.js";
import { pointerIdle } from "./core/instant.js";
import { D, DDATE, fd, S, store, toIso } from "./core/page.js";
import { api, oneLine, SERVED, snack, viaServer } from "./core/server.js";
import { shared } from "./core/state.js";
import { pendingEdit } from "./ask.js";
import { inboxBadge, renderInbox } from "./intake.js";
import { hubFor, hubLink } from "./meetings.js";
/* ======================= Files ======================= */
shared.FSEL={p:"All",f:"All",sub:"",quick:"all"}; export const FOPEN=new Set(store.get("creaite-files-open",[]));
/* BL-331: the reports and minutes BL-03 archived (still in their _Archive), listed only under the Archived chip, each with Move back */
export const farch=()=>D.files_archived||[];
export const FNAME=Object.assign({_portfolio:"projects/_portfolio",inbox:"inbox"},D.folders);
export function renderFiles(){ const cnt=f=>FILES.filter(f).length; const pr=(b)=>b?"true":"false";
  const h=[html`<button data-p="All" data-f="All" aria-pressed="${pr(shared.FSEL.p==="All")}">All files<span class="n">${FILES.length}</span></button><button class="l1" data-p="inbox" data-f="All" aria-pressed="${pr(shared.FSEL.p==="inbox")}">Intake<span class="n">${cnt(x=>x.p==="inbox")}</span></button><button class="l1" data-p="_portfolio" data-f="All" aria-pressed="${pr(shared.FSEL.p==="_portfolio")}"><span title="${FNAME._portfolio}">Portfolio</span><span class="n">${cnt(x=>x.p==="_portfolio")}</span></button>`];
  P.forEach(p=>{ const c=p.code, op=FOPEN.has(c); h.push(html`<button class="l1" data-p="${c}" data-f="All" data-toggle="${c}" aria-expanded="${pr(op)}" aria-pressed="${pr(shared.FSEL.p===c&&shared.FSEL.f==="All")}"><span class="chev">${raw(ic("chevdown","chev turn"))}</span><span title="${FNAME[c]}">${pName(c)}</span><span class="n">${cnt(x=>x.p===c)}</span></button>`);
    if(op) ["minutes","transcripts","agendas",...(S.filesDocs?["documents"]:[]),"reports"].forEach(fd=>{ h.push(html`<button class="l2" data-p="${c}" data-f="${fd}" aria-pressed="${pr(shared.FSEL.p===c&&shared.FSEL.f===fd&&!shared.FSEL.sub)}">${fd}<span class="n">${cnt(x=>x.p===c&&x.f===fd)}</span></button>`);
      if(fd==="reports") REPFOLDERS.forEach(s=>h.push(html`<button class="l3" data-p="${c}" data-f="reports" data-s="${s}" aria-pressed="${pr(shared.FSEL.sub===s&&shared.FSEL.p===c)}">${s}<span class="n">${cnt(x=>x.p===c&&x.f==="reports"&&x.sub===s)}</span></button>`));
      if(fd==="documents") [...new Set(FILES.filter(x=>x.p===c&&x.f==="documents"&&x.sub).map(x=>x.sub))].forEach(s=>h.push(html`<button class="l3" data-p="${c}" data-f="documents" data-s="${s}" aria-pressed="${pr(shared.FSEL.sub===s&&shared.FSEL.p===c)}">${s}<span class="n">${cnt(x=>x.p===c&&x.f==="documents"&&x.sub===s)}</span></button>`)); }); });
  putHTML($("#tree"),html`${h}`);
  putHTML($("#fquick"),html`${[["all","All files"],["latest","Latest reports"],["week","This week's meetings"],["inbox","Intake"],...(farch().length?[["archived","Archived"]]:[])].map(q=>html`<button class="vchip" data-q="${q[0]}" aria-pressed="${String(shared.FSEL.quick===q[0]&&!(shared.FSEL.f==="reports"&&shared.FSEL.sub&&shared.FSEL.p==="All"))}">${q[1]}</button>`)}${REPFOLDERS.map(r=>html`<button class="vchip" data-rep="${r}" aria-pressed="${String(shared.FSEL.p==="All"&&shared.FSEL.f==="reports"&&shared.FSEL.sub===r)}" title="Reports filed in the ${r} folder">${r}</button>`)}`);
  const q=$("#fsName").value.toLowerCase(), t=$("#fsType").value, fr=DDATE.test($("#fsFrom").value)?toIso($("#fsFrom").value):"", to=DDATE.test($("#fsTo").value)?toIso($("#fsTo").value):"";
  let L=FILES.filter(x=>(shared.FSEL.p==="All"||x.p===shared.FSEL.p)&&(shared.FSEL.f==="All"||x.f===shared.FSEL.f)&&(!shared.FSEL.sub||x.sub===shared.FSEL.sub));
  if(shared.FSEL.quick==="latest"){ L=[]; P.forEach(p=>REPFOLDERS.forEach(k=>{ const r=FILES.filter(f=>f.p===p.code&&f.f==="reports"&&f.sub===k).sort((a,b)=>(b.date||b.mod||"").localeCompare(a.date||a.mod||""))[0]; if(r) L.push(r); })); }   /* BL-87: the newest in each report folder, by folder not by name */
  if(shared.FSEL.quick==="week") L=FILES.filter(f=>(f.f==="minutes"||f.f==="transcripts")&&f.date>=WEEKSTART);
  if(shared.FSEL.quick==="inbox") L=FILES.filter(f=>f.p==="inbox");
  if(shared.FSEL.quick==="archived") L=farch().slice();   /* BL-331 */
  L=L.filter(f=>(!q||f.n.toLowerCase().includes(q))&&(t==="All"||f.type===t)&&(!fr||f.date>=fr)&&(!to||f.date<=to)).sort((a,b)=>(b.date||"0").localeCompare(a.date||"0"));
  putHTML($("#filesTbl"),html`<table><thead><tr><th>Name</th><th>Location</th><th>Date</th><th>Size</th><th></th></tr></thead><tbody>${L.length?L.map(f=>html`<tr data-fp="${f.path}" class="${shared.FSELFILE===f.path?"sel":""}"><td><span class="ftype">${f.type}</span><a href="#" data-openfile="${f.path}">${f.n}</a>${FNEW.has(f.path)&&html` <span class="tag new">New</span>`}${f.archived&&html` <span class="tag">Archived</span>`}</td><td class="x">${f.p==="inbox"?"Intake":`${fpName(f.p)} › ${f.f}${f.sub?" › "+f.sub:""}`}</td><td style="white-space:nowrap">${f.date?fd(f.date):"—"}</td><td class="x">${f.kb>=1000?(f.kb/1000).toFixed(1)+" MB":f.kb+" KB"}</td><td style="text-align:right">${f.archived?html`<button class="mini" data-moveback="${f.path}" aria-label="Move back ${f.n}">Move back</button>`:raw(ibtn("folderopen","Open folder",html`data-openfile="${f.path.slice(0,f.path.lastIndexOf("/")+1)}"`,"sm"))}</td></tr>`):html`<tr><td colspan="5"><div class="empty">No files match. Clear the filters.</div></td></tr>`}</tbody></table>`); filesStatus(L.length);
  if(!shared.LOADING) $$("#filesTbl tr[data-fp]").forEach(tr=>{ const t=hubFor({path:tr.dataset.fp}), td=tr.querySelector("td"); if(t&&td&&!td.querySelector(".mhlink")) addHTML(td,"beforeend",hubLink(t,"Meeting")); }); }
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootFiles0068(){
$("#tree").addEventListener("click",e=>{ const b=e.target.closest("button"); if(!b) return; if(b.dataset.toggle){ const c=b.dataset.toggle; if(FOPEN.has(c)&&shared.FSEL.p===c&&shared.FSEL.f==="All") FOPEN.delete(c); else FOPEN.add(c); store.set("creaite-files-open",[...FOPEN]); } shared.FSEL={p:b.dataset.p,f:b.dataset.f,sub:b.dataset.s||"",quick:b.dataset.p==="inbox"?"inbox":"all"}; renderFiles(); });
$("#fquick").addEventListener("click",e=>{ const r=e.target.closest("[data-rep]"); if(r){ shared.FSEL=shared.FSEL.p==="All"&&shared.FSEL.f==="reports"&&shared.FSEL.sub===r.dataset.rep?{p:"All",f:"All",sub:"",quick:"all"}:{p:"All",f:"reports",sub:r.dataset.rep,quick:"all"}; renderFiles(); return; }   /* BL-87: a chip per report folder */
  const b=e.target.closest("[data-q]"); if(!b) return; shared.FSEL={p:"All",f:"All",sub:"",quick:b.dataset.q}; renderFiles(); });
["#fsName","#fsType","#fsFrom","#fsTo"].forEach(s=>$(s).addEventListener("input",renderFiles));
}
/* ===== Dashboard pages (BL-87 to BL-95) ===== */
/* BL-87 Files: fresh when you look. Opening Files or Intake, and the window regaining focus (at most every 10 seconds, and
   only on those pages), rescan just the file lists through GET /api/files; Refresh does it at once. A refresh keeps the
   filters, the selected file, the scroll position and the open folders (none of them are re-created). Files that appeared
   since you last looked are tagged New and counted; the tags are cleared the next time you open the page. A dashboard opened
   from disk (not served) keeps the file list of the last build. */
export const REPFOLDERS=["Weekly","Adhoc","Steerco"];
export let FSEEN=null, FNEW=new Set(), FAT=null, FERR=""; shared.FSELFILE=null; shared.FLAST=0; shared.FBUSY=false;
export const clockOf=at=>String(at||"").slice(11,16);
export function filesStatus(shown){ const n=FNEW.size, tot=FILES.length;
  $("#filesCount").textContent=`${shown===undefined?tot:shown} of ${tot} files${n?` · ${n} new`:""}`;
  $("#filesAt").textContent=FERR?FERR:shared.FBUSY&&shared.FBUSY==="slow"?"Checking…":SERVED&&(FAT||D.built_at)?`Updated ${clockOf(FAT||D.built_at)}.`:"File list as of the last build."; }
export async function refreshFiles(force){ if(!SERVED||!shared.LIVE||shared.FBUSY) return false; const now=Date.now(); if(!force&&now-shared.FLAST<10000) return false; shared.FLAST=now;
  shared.FBUSY=true; const slow=setTimeout(()=>{ if(shared.FBUSY){ shared.FBUSY="slow"; filesStatus(); } },1000);
  try{ const r=await fetch("/api/files",{headers:{"X-Creaite-Token":D.token||""}}), j=await r.json(); if(!r.ok||!j.ok) throw new Error(j.message||r.status);
    const known=new Set(FILES.map(f=>f.path)); const fresh=j.files.filter(f=>!known.has(f.path)&&f.p!=="inbox");
    FILES.splice(0,FILES.length,...j.files); D.files_archived=j.archived||[]; D.inbox=j.inbox; FAT=j.at; FERR="";
    if(FSEEN) fresh.forEach(f=>FNEW.add(f.path)); FSEEN=new Set(FILES.map(f=>f.path));
    [...FNEW].forEach(p=>{ if(!FSEEN.has(p)) FNEW.delete(p); }); }
  catch(e){ FERR=`Couldn't refresh the file list (${e.message}); showing the list from ${clockOf(FAT||D.built_at)||"the last build"}.`; }
  finally{ clearTimeout(slow); shared.FBUSY=false; }
  await pointerIdle();   /* Plan #85: a click in progress lands before the list is redrawn */
  inboxBadge(); if(shared.VIEW==="files") renderFiles(); else if(shared.VIEW==="inbox") renderInbox(); return true; }
/* looking at Files again clears what was new last time */
export function filesOpened(){ if(FSEEN){ FNEW.clear(); FSEEN=new Set(FILES.map(f=>f.path)); } else FSEEN=new Set(FILES.map(f=>f.path)); refreshFiles(true); }
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootFiles0069(){
window.addEventListener("focus",()=>{ if(shared.VIEW==="files"||shared.VIEW==="inbox") refreshFiles(false); });
$("#filesRefresh").onclick=()=>{ refreshFiles(true); if(!SERVED) snack("Refresh needs the live server; this page shows the file list of the last build"); };
$("#filesTbl").addEventListener("click",e=>{ const mb=e.target.closest("[data-moveback]"); if(mb){ moveBack(mb.dataset.moveback); return; } const tr=e.target.closest("tr[data-fp]"); if(!tr||e.target.closest("a,button")) return; shared.FSELFILE=tr.dataset.fp; $$("#filesTbl tr[data-fp]").forEach(r=>r.classList.toggle("sel",r===tr)); });
}
/* BL-331: Move back one archived report or minutes. The server builds the move (only a file the archive moved, back to its own
   place, never onto a file that is there) and puts it on the approval card; Approve applies it through tracker.py apply. */
export async function moveBack(path){ if(!viaServer()){ snack("Moving a file back needs the live server"); return; }
  const r=await api("/api/files/move-back",{path}); snack(oneLine(r.message||(r.ok?"On the approval card":"It couldn't be prepared"))); if(r.ok) await pendingEdit(); }
