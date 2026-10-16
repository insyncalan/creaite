// @ts-check
/* work.js (BL-231 step 2b), moved from script/ by dev/tools/convert_area.py: 0030-work.js, 0031-bl-150-sprint-ux.js, 0032-bl-159-sprint-icons.js, 0033-bl-160-sprint-icons.js, 0034-after-bl-160-js.js, 0035-work-board-bl-103-sprint-4a.js, 0036-bl-128-sprint-work-views.js, 0037-decisions-board-bl-103-sprint-debug-log.js, 0038-bl-129-sprint-work-views.js, 0039-bl-130-sprint-work-views.js, 0040-bl-132-sprint-work-views.js, 0041-bl-131-sprint-work-views.js, 0130-person-rows-bl-68.js, 0131-bl-122-sprint-polish.js, 0132-bl-123-sprint-polish.js, 0133-bl-124-sprint-polish.js, 0147-bl-134-sprint-all-items.js, 0148-bl-138-sprint-all-items.js, 0149-bl-190-sprint-links.js, 0150-after-bl-190-people.js.
   Unchanged apart from `export`, `shared.` for the shared state (core/state.js) and the load-time steps, now in
   boot…() functions that src/main.js calls in today's order. */
import { openDialog } from "./components/Dialog.jsx";
import { drawFilterBar, fitFilterBar } from "./components/FilterBar.jsx";

import { closeMenu, menuOpenFor, openMenu } from "./components/Menu.jsx";
import { drawTabs } from "./components/Tabs.jsx";
import { drawNewTile } from "./components/work/NewTile.jsx";
import { A, DEC, open, overdue, P, peopleAll, pName, R, REV, wsFor } from "./core/data.js";
import { $, $$, addHTML, esc, html, ic, putHTML, raw, swapHTML, tipHide } from "./core/dom.js";
import { CALI, closeCal, DATE_HELP, srcShort, WK, wkAsk, wkClear } from "./core/fields.js";
import { typing } from "./core/keys.js";
import { mDots, mFlipRows, mNoFade, mSnapRows, mTick } from "./core/motion.js";
import { countLink, go, navBlocked, navWrite, openedNote, OPENEDON, pLink } from "./core/nav.js";
import { anim, cmdOK, cmOK, D, days, DDATE, fd, fdText, ico, isMe, kindOf, nowStamp, OPENST, reduced, rel, S, store, TODAY, toIso, who } from "./core/page.js";
import { oneLine, save, SKEY, snack, toDb, writeSettings, z2 } from "./core/server.js";
import { shared } from "./core/state.js";
import { draftBtn } from "./drafts.js";
import { kb } from "./intake.js";
import { decLate, decLateWords, withdrawDecision } from "./meetings.js";
import { ceListPlace } from "./milestones.js";
import { commitRecord, fieldsFor, markSel, msChoices, norm, openNew, openRecord, pkCommit, markStagedRows, pkFollowable, pkKeepFocus, pkSetStatus, REC, validate } from "./panel.js";
import { closePanel, wflag } from "./projects.js";
import { CHK, isMin, RHL, rvBar, rvBulkOK, RVF, RVFIELDS, rvSyncChk } from "./review.js";
import { dueSort, isHiddenPerson, nm, ownerFinal, PERS, personLink, PSORTS, renderPerson, row, xcueAll } from "./settings.js";
import { plur } from "./today.js";
/* ======================= Work ======================= */
shared.WT="actions"; shared.WVIEW=null; shared.SEL=null; shared.WQ=""; export const OWN=new Set(), PROJF=new Set(), PRIF=new Set();
/* BL-45: Work's filters combine. Status, Due, Owner, Project and Priority sit on the toolbar; "+ Filter" holds the
   rest; every menu shows counts. Views are presets that set filters on screen, and Alan can save his own. */
export const FX={st:new Set(),due:new Set(),ws:new Set(),ty:new Set(),rs:new Set(),src:new Set(),cv:new Set(),dt:new Set(),ms:new Set()};
export let RR={from:"",to:""}; shared.DR={from:"",to:""}; shared.CR={from:"",to:""};   /* CR: closed between (BL-190) */ export const SORT={}, WINIT={}, NEG=new Set();   /* RR: raised between; NEG: the fields set to "is not" (BL-130) */
export const PRIOS=["Urgent","High","Medium","Low"];
/* free-text search: every word must appear somewhere in the item (ID, text, owner, workstream, response, update, source, project…) */
export const qOK=x=>{ const w=shared.WQ.toLowerCase().split(/\s+/).filter(Boolean); if(!w.length) return true;
  const hay=[...Object.values(x).filter(v=>typeof v==="string"),...["due","raised","closed","date"].map(k=>x[k]?fd(x[k]):""),who(x.o||x.by),(P.find(p=>p.code===x.p)||{}).name||""].join(" ").toLowerCase(); return w.every(t=>hay.includes(t)); };   /* BL-62: dates as shown too */
export const items=()=>shared.WT==="all"?allRows():shared.WT==="actions"?A:shared.WT==="raid"?R:DEC;   /* BL-134: All items is the merged read model */
export const dueKey=x=>{ const op=shared.WT==="actions"?open(x):x.st==="Open"||x.st==="Pending"; if(!op) return "closed";   /* BL-62: closed items aren't due */
  return x.due&&x.due<TODAY?"overdue":x.due&&days(x.due)<=S.dueSoon?"soon":!x.due?"none":"later"; };
export const srcKind=x=>{ const s=String(x.src||""); return /dashboard/i.test(s)?"Dashboard":/excel/i.test(s)?"Excel":/cx-edit/i.test(s)?"cx-edit":/^Teams|Teams ·|"type":\s*"Teams"/i.test(s)?"Teams":/Outlook|"type":\s*"Email"|^RE:|^FW:/i.test(s)?"Mail":/\.(docx|vtt|txt|md)\b/i.test(s)?"Minutes":"Other"; };
export const uniq=(f)=>[...new Set(items().map(f).filter(Boolean))].sort((a,b)=>a.localeCompare(b));
export const ownerOpts=()=>uniq(x=>x.o||x.by).sort((a,b)=>isMe(a)?-1:isMe(b)?1:a.localeCompare(b)).map(n=>[n,isMe(n)?`Me (${who(n)})`:who(n)]);
export const yesNo=()=>[["yes","Yes"],["no","No"]];
export const wsOpts=()=>[["","No workstream"],...uniq(x=>x.ws).map(v=>[v,v])];   /* BL-62: items with none can be found */
/* [key, label, options, value of an item, in "+ Filter", custom test] */
export const FDEFS={
  actions:[["st","Status",()=>["Open","Delayed","Closed","Cancelled"].map(v=>[v,v]),x=>x.st],
    ["due","Due",()=>[["overdue","Overdue"],["soon",`Due in ${S.dueSoon} days`],["none","No date"],["later","Later"]],dueKey],
    ["o","Owner",ownerOpts,x=>x.o],["p","Project",()=>P.map(p=>[p.code,p.name]),x=>x.p],["pr","Priority",()=>PRIOS.map(v=>[v,v]),x=>x.pr],
    ["ws","Workstream",wsOpts,x=>x.ws||"",1],["src","Source",()=>uniq(srcKind).map(v=>[v,v]),srcKind,1],["cv","Client-visible",yesNo,x=>x.client?"yes":"no",1]],
  raid:[["st","Status",()=>["Open","Closed","Cancelled"].map(v=>[v,v]),x=>x.st],
    ["due","Due",()=>[["overdue","Overdue"],["soon",`Due in ${S.dueSoon} days`],["none","No date"],["later","Later"]],dueKey],
    ["o","Owner",ownerOpts,x=>x.o],["p","Project",()=>P.map(p=>[p.code,p.name]),x=>x.p],["pr","Priority",()=>PRIOS.map(v=>[v,v]),x=>x.pr],
    ["ty","Type",()=>["Risk","Issue","Assumption","Dependency"].map(v=>[v,v]),x=>x.type,1],["rs","Response",()=>[["yes","Has a response"],["none","No response yet"]],x=>x.resp?"yes":"none",1],
    ["ws","Workstream",wsOpts,x=>x.ws||"",1],["src","Source",()=>uniq(srcKind).map(v=>[v,v]),srcKind,1],["cv","Client-visible",yesNo,x=>x.client?"yes":"no",1],
    ["ms","Milestone",()=>[["yes","Attached to a milestone"],["no","Not attached"]],x=>x.ms?"yes":"no",1]],   /* BL-90: a dependency's milestone link */
  decisions:[["st","Status",()=>["Pending","Made","Withdrawn"].map(v=>[v,v]),x=>x.st],["o","Made by",ownerOpts,x=>x.by],["p","Project",()=>P.map(p=>[p.code,p.name]),x=>x.p],
    ["due","Needed by",()=>[["overdue","Overdue"],["soon",`Needed in ${S.dueSoon} days`],["none","No date"],["later","Later"]],dueKey,1],
    ["dt","Date",()=>[["7","Last 7 days"],["14","Last 14 days"],["30","Last 30 days"]],x=>x.date,0,(x,set)=>[...set].some(n=>days(x.date)>=-n&&days(x.date)<=0)],
    ["cv","Client-visible",yesNo,x=>x.client?"yes":"no"],["src","Source",()=>uniq(srcKind).map(v=>[v,v]),srcKind,1]]};
export const BTNID={o:"own",p:"proj",pr:"pri"};
export const setOf=k=>k==="o"?OWN:k==="p"?PROJF:k==="pr"?PRIF:FX[k];
export const defs=()=>FDEFS[shared.WT], defOf=k=>defs().find(d=>d[0]===k);
export const hit=(d,x,set)=>d[5]?d[5](x,set):set.has(String(d[3](x)));
export function passes(x,skip){ for(const d of defs()){ if(d[0]===skip) continue; const set=setOf(d[0]); if(set.size&&(NEG.has(d[0])?hit(d,x,set):!hit(d,x,set))) return false; }   /* BL-130: "is not" excludes */
  if(shared.WT!=="decisions"&&skip!=="dr"&&(shared.DR.from||shared.DR.to)&&(!x.due||(shared.DR.from&&x.due<shared.DR.from)||(shared.DR.to&&x.due>shared.DR.to))) return false;
  if(shared.WT!=="decisions"&&skip!=="rr"&&(RR.from||RR.to)&&(!x.raised||(RR.from&&x.raised<RR.from)||(RR.to&&x.raised>RR.to))) return false;
  if(shared.WT!=="decisions"&&skip!=="cr"&&(shared.CR.from||shared.CR.to)&&(!x.closed||(shared.CR.from&&x.closed<shared.CR.from)||(shared.CR.to&&x.closed>shared.CR.to))) return false;   /* BL-190: closed between */   /* BL-130: raised between */
  return skip==="q"||qOK(x); }
export const countFor=(k,v)=>{ const d=defOf(k), one=new Set([v]); return items().filter(x=>passes(x,k)&&hit(d,x,one)).length; };
/* sorting: a header click sorts, again reverses, a third time returns to the default order */
// @ts-expect-error TS2362: true and false subtract as 1 and 0 (overdue items sort first)
export const DEFSORT={actions:(a,b)=>(overdue(b)-overdue(a))||(a.due||"9").localeCompare(b.due||"9"),raid:(a,b)=>PRIOS.indexOf(a.pr)-PRIOS.indexOf(b.pr),decisions:(a,b)=>(a.st==="Pending")!==(b.st==="Pending")?(a.st==="Pending"?-1:1):a.st==="Pending"?(a.due||"9").localeCompare(b.due||"9"):b.date.localeCompare(a.date)};   /* BL-53: pending first, soonest needed first */
export const SORTKEY={t:x=>x.t.toLowerCase(),o:x=>who(x.o).toLowerCase(),due:x=>x.due||"9999",pr:x=>PRIOS.indexOf(x.pr),st:x=>x.st,ws:x=>(x.ws||"").toLowerCase(),type:x=>x.type,resp:x=>(x.resp||"").toLowerCase(),by:x=>(x.by||"").toLowerCase(),date:x=>x.date,id:x=>x.id,src:x=>srcKind(x),upd:x=>x.upd_at||"",raised:x=>x.raised||""};   /* upd and raised: the Work board's sort chooser */
export function rows(t=shared.WT,L=items().filter(x=>passes(x)),s=SORT[t],def=DEFSORT[t]){ if(!s) return L.sort(def);   /* BL-68: any page can sort its own list of one type */
  if(s.col==="_def"){ L.sort(def); return s.dir==="desc"?L.reverse():L; }   /* BL-128: the default order, reversed */
  const k=SORTKEY[s.col]||(()=>""); return L.sort((a,b)=>{ const x=k(a),y=k(b); return (x<y?-1:x>y?1:0)*(s.dir==="desc"?-1:1)||def(a,b); }); }
/* views: built-in presets and Alan's saved views (settings.json work.saved_views) */
/* BL-131: Chase on every tab (open, someone else's, stale); a fourth element `true` puts a preset under More views (Overdue on Actions) */
export const PRESETS={actions:[["open","All open",{st:["Open"]}],["mine","Mine",{st:["Open"],o:["@me"]}],["soon","Due soon",{st:["Open"],due:["soon"]}],["chase","Chase",{st:["Open"],"!o":["@me"],sl:["yes"]}],["delayed","Delayed",{st:["Delayed"]}],["overdue","Overdue",{st:["Open","Delayed"],due:["overdue"]},true],["closed","Closed",{st:["Closed","Cancelled"]}]],
  raid:[["open","All open",{st:["Open"]}],["urgent","Urgent and high",{st:["Open"],pr:["Urgent","High"]}],["unatt","Unattached dependencies",{st:["Open"],ty:["Dependency"],ms:["no"]}],["nomit","No response yet",{st:["Open"],rs:["none"]}],["chase","Chase",{st:["Open"],"!o":["@me"],sl:["yes"]}],["soon","Due soon",{st:["Open"],due:["soon"]}],["mine","Mine",{st:["Open"],o:["@me"]}],["closed","Closed",{st:["Closed","Cancelled"]}]],
  decisions:[["all","All",{}],["pending","Pending",{st:["Pending"]}],["chase","Chase",{st:["Pending"],"!o":["@me"],sl:["yes"]}],["overdue","Overdue",{st:["Pending"],due:["overdue"]}],["recent","Last 14 days",{dt:["14"]}],["client","Client-visible",{cv:["yes"]}]]};
shared.SAVED=Object.assign({actions:[],raid:[],decisions:[]},S.savedViews||{});
export const allViews=t=>[...PRESETS[t].map(p=>({id:p[0],label:p[1],f:p[2],builtin:true,more:!!p[3]})),...(shared.SAVED[t]||[]).map(v=>({...v,id:"saved:"+v.name,label:v.name,f:v.f||{}}))];   /* BL-128: a saved view's display (layout, group, order) comes with it */
export const viewsList=t=>allViews(t).map(v=>[v.id,v.label]);
export const myOwnerNames=()=>[...new Set([S.me,...items().map(x=>x.o||x.by).filter(n=>n&&isMe(n))])];
export function snapshot(){ const f={}; defs().forEach(d=>{ if(d[0]==="p") return; const v=[...setOf(d[0])].sort(); if(!v.length) return;
    f[(NEG.has(d[0])?"!":"")+d[0]]=d[0]==="o"&&v.length&&v.every(isMe)?["@me"]:v; }); if(shared.WT!=="decisions"&&(shared.DR.from||shared.DR.to)) f.dr=[shared.DR.from,shared.DR.to];
  if(shared.WT!=="decisions"&&(RR.from||RR.to)) f.rr=[RR.from,RR.to]; if(shared.WT!=="decisions"&&(shared.CR.from||shared.CR.to)) f.cr=[shared.CR.from,shared.CR.to]; return f; }   /* BL-130: an excluded field is stored as "!key", so older views load unchanged */
export const sameF=(a,b)=>{ const ka=Object.keys(a).sort(), kb=Object.keys(b).sort(); return ka.join()===kb.join()&&ka.every(k=>[...a[k]].sort().join("|")===[...b[k]].sort().join("|")); };
export function applyFilters(f){ defs().forEach(d=>{ if(d[0]!=="p") setOf(d[0]).clear(); }); shared.DR={from:"",to:""}; RR={from:"",to:""}; shared.CR={from:"",to:""}; [...NEG].forEach(k=>{ if(k!=="p") NEG.delete(k); });
  Object.entries(f||{}).forEach(([k,v])=>{ if(k==="dr"){ shared.DR={from:v[0]||"",to:v[1]||""}; return; } if(k==="rr"){ RR={from:v[0]||"",to:v[1]||""}; return; } if(k==="cr"){ shared.CR={from:v[0]||"",to:v[1]||""}; return; }
    const neg=k[0]==="!"; if(neg) k=k.slice(1); const set=setOf(k); if(!set) return; if(neg) NEG.add(k); (k==="o"&&v.includes("@me")?myOwnerNames():v).forEach(x=>set.add(x)); }); }
export function applyView(id){ const v=allViews(shared.WT).find(v=>v.id===id||v.label.toLowerCase()===String(id||"").toLowerCase())||allViews(shared.WT)[0]; applyFilters(v.f); shared.WVIEW=WB[shared.WT]=v.id; WINIT[shared.WT]=true;
  if(v.lay){ shared.LAYCHOSEN=true; WLAY[shared.WT]=v.lay; if(v.g) WGRP[shared.WT]=v.g; }   /* BL-103: a saved view also keeps its layout and grouping */
  if("o" in v) SORT[shared.WT]=v.o||null;   /* BL-128: and its order */
  if("lg" in v) WLGRP[shared.WT]=v.lg||"none"; if("sg" in v) WSUB[shared.WT+"|board"]=v.sg||"none"; if("lsg" in v) WSUB[shared.WT+"|list"]=v.lsg||"none"; }   /* BL-129: the List's grouping and the sub-groups */
export function syncView(){ const snap=snapshot(), V=allViews(shared.WT), cur=V.find(v=>v.id===shared.WVIEW)||V.find(v=>v.id===WB[shared.WT]);   /* BL-131: the view in use stays it while it still matches */
  if(cur&&viewMatches(cur,snap)){ shared.WVIEW=WB[shared.WT]=cur.id; return; } const m=V.find(v=>viewMatches(v,snap)); if(m) shared.WVIEW=WB[shared.WT]=m.id; else shared.WVIEW=null; }
export function defaultView(t){ return t==="all"?"open":t==="actions"?S.defActionView:t==="raid"?S.defRaidView:S.defDecisionView||"all"; }   /* BL-131: Decisions has a default view too */
export function workChanged(){ syncView(); renderWork(); navWrite(false); }
export function btnLabel(d){ const l=btnLabel0(d); return NEG.has(d[0])&&setOf(d[0]).size?l.replace(/^([^:]*: )?/,(m,a)=>a?a+"not ":"Not "):l; }   /* BL-130 */
export function btnLabel0(d){ const set=setOf(d[0]), v=[...set], opts=d[2](), lab=x=>(opts.find(o=>o[0]===x)||[x,x])[1];
  if(!v.length) return d[0]==="o"?(shared.WT==="decisions"?"Anyone":"All owners"):d[0]==="p"?"All projects":d[0]==="pr"?"All priorities":d[1];
  if(d[0]==="o") return v.length===1?who(v[0]):v.every(isMe)?"Me":`${v.length} owners`;
  if(d[0]==="p") return v.length===1?pName(v[0]):`${v.length} projects`;
  if(d[0]==="pr") return PRIOS.filter(x=>set.has(x)).join(", ");
  return `${d[1]}: ${v.length<=2?v.map(lab).join(", "):v.length+" chosen"}`; }
/* BL-316: Work's filter bar is the FilterBar building block (components/FilterBar.jsx), drawn into #wfilters from FDEFS and the
   date ranges; the block draws the buttons, their lists, + Filter's field picker and BL-150's folding, and says what changed */
export function workBarProps(){ const R=FPRANGES(), main=defs().filter(d=>!d[4]), more=defs().filter(d=>d[4]);
  if(![...defs().map(d=>d[0]),...R.map(r=>r[0])].includes(shared.FPK)) shared.FPK=(more.find(d=>setOf(d[0]).size)||more[0]||main[0])[0];
  const rng=k=>k==="dr"?shared.DR:k==="rr"?RR:shared.CR, rOn=k=>!!(rng(k).from||rng(k).to), total=items().length, shown=items().filter(x=>passes(x)).length;
  const fields=[...defs().map(d=>{ const k=d[0], on=!!setOf(k).size, id=BTNID[k]||k;
      return {id:k,label:d[1],main:!d[4],section:d[4]?"More fields":undefined,btnId:d[4]?undefined:`${id}Btn`,menuId:`${id}Menu`,data:{"open-fk":k},
        button:btnLabel(d),on,selected:setOf(k),not:NEG.has(k),mark:on?`${NEG.has(k)?"not · ":""}set`:"",onlyMe:k==="o"?myOwnerNames():undefined,
        options:()=>d[2]().map(o=>({value:o[0],label:o[1],count:countFor(k,o[0])}))}; }),
    ...R.map(([k,l])=>({id:k,label:l,section:"More fields",on:rOn(k),mark:rOn(k)?"set":"",range:{from:rng(k).from?fd(rng(k).from):"",to:rng(k).to?fd(rng(k).to):"",name:l.replace(/ between$/,"")}}))];
  return {fields,
    onSelect:(k,vals)=>{ const set=setOf(k); set.clear(); vals.forEach(v=>set.add(v)); workChanged(); },
    onNot:(k,n)=>{ n?NEG.add(k):NEG.delete(k); workChanged(); },
    onRange:(k,end,text)=>{ const v=text.trim(); if(v&&!DDATE.test(v)){ snack("Not a date creaite knows. "+DATE_HELP); return; } rng(k)[end]=v?toIso(v):""; workChanged(); },
    more:{id:"moreBtn",menuId:"moreMenu",label:funnelTip(wfCount()),menuLabel:"Add a filter",count:wfCount(),key:"F",
      on:defs().some(d=>d[4]&&setOf(d[0]).size)||!!(shared.DR.from||shared.DR.to||RR.from||RR.to||shared.CR.from||shared.CR.to),
      field:shared.FPK,onField:k=>{ shared.FPK=k; drawWorkFilters(); },query:shared.FPQ,
      onQuery:q=>{ shared.FPQ=q; const vis=[...defs().map(d=>[d[0],d[1]]),...FPRANGES()].filter(f=>!q||f[1].toLowerCase().includes(q.toLowerCase()));
        if(vis.length&&!vis.some(f=>f[0]===shared.FPK)) shared.FPK=vis[0][0]; drawWorkFilters(); },
      result:`Result: ${shown} of ${total} shown`,resultId:"fpResult",doneId:"fpDone"},
    fold:()=>{ const bar=$("#v-work .toolbar"); if(!bar||!bar.offsetParent) return false;   /* BL-150; BL-176: the peek is over the page, so it folds nothing; BL-173: nor does ask creaite */
      return $("#panel").classList.contains("on")&&!$("#panel").classList.contains("peek")||innerWidth<1100?bar:null; }}; }
export function drawWorkFilters(){ const h=$("#wfilters"); if(h) drawFilterBar(h,workBarProps()); }
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootWork0031(){
if(window.ResizeObserver) new ResizeObserver(()=>requestAnimationFrame(()=>fitFilterBar($("#wfilters")))).observe($("#v-work"));   /* BL-150 */
}
/* ===== BL-159 (sprint-icons) ===== the Work toolbar in icons. The funnel carries how many filters are on; the New tile says the
   tab's own word (in its label, its tooltip and, on hover or focus, as it grows); on Decisions it opens a two-item menu:
   Record a decision (the form as Made, dated today) and Ask for a decision (as Pending: openNew("decisions","needed")).
   The tile is components/work/NewTile.jsx; on Decisions it is the Menu building block (BL-316). */
export function wfCount(){ return defs().filter(d=>setOf(d[0])&&setOf(d[0]).size).length+(shared.WT!=="decisions"&&(shared.DR.from||shared.DR.to)?1:0)+(shared.WT!=="decisions"&&(RR.from||RR.to)?1:0)+(shared.WT!=="decisions"&&(shared.CR.from||shared.CR.to)?1:0); }
export function funnelTip(n,what="Add a filter"){ return n?`${what}: ${n} on`:what; }   /* BL-264: Settings › People says "Filter people" */
export function newTile(){ const h=$("#newHost"); if(!h) return; const w=shared.WT==="actions"?"New action":shared.WT==="raid"?"New RAID item":"New decision";
  drawNewTile(h,{word:w,decisions:shared.WT==="decisions",hidden:shared.WT==="all",onNew:()=>openNew(shared.WT),onDecision:how=>openNew("decisions",how==="needed"?"needed":undefined)}); }
export function newMenuOpen(){ return !!$("#newDecMenu"); }
/* ===== end BL-159 (JS) ===== */
/* ===== BL-160 (sprint-icons) ===== Review in icons: the funnel counts its filters (Review's own: Kind, Needs, Source, Project, Age);
   Approve and Reject keep their words in the bulk bar; on a row, Approve keeps its word, Reject is the x, and Edit and Refresh
   items show on hover, on focus and on the cursor row (.rowact), so the keyboard still reaches them. */
export function rvfCount(){ return RVFIELDS.filter(f=>RVF[f[0]]&&RVF[f[0]].size).length; }
/* ===== end BL-160 (JS) ===== */
/* BL-264: one applied-filter chip, shared by Work and Settings › People: its words (escaped here), an x that clears it (`attr`
   names the key), tinted when it is an exclusion (`neg`), quiet when it is a default (`def`); with `edit`, the words are a button
   (data-<edit>) that opens the picker at that field. */
export function fchipHtml(label,k,clr,{neg=false,def=false,edit="",attr="data-clr"}={}){
  return `<span class="fchip${neg?" neg":""}${def?" def":""}">${edit?`<button type="button" class="cl" data-${edit}="${esc(k)}" aria-label="Change: ${esc(label)}">${esc(label)}</button>`:esc(label)}<button ${attr}="${esc(k)}" aria-label="${esc(clr)}">${ic("x")}</button></span>`; }
export function renderApplied(total,shown){ const chips=[];
  defs().forEach(d=>{ const v=[...setOf(d[0])]; if(!v.length) return; const opts=d[2](), lab=x=>(opts.find(o=>o[0]===x)||[x,x])[1];
    const neg=NEG.has(d[0]); chips.push(fchipHtml(`${d[1]}: ${neg?"not ":""}${d[0]==="o"&&v.every(isMe)?"Me":v.map(lab).join(", ")}`,d[0],`Remove the ${d[1].toLowerCase()} filter`,{neg})); });   /* BL-130: an exclusion is tinted and says "not" */
  if(shared.WT!=="decisions"&&(shared.DR.from||shared.DR.to)) chips.push(`<span class="fchip">Due: ${shared.DR.from?fd(shared.DR.from):"…"} to ${shared.DR.to?fd(shared.DR.to):"…"}<button data-clr="dr" aria-label="Remove the due date range">${ic("x")}</button></span>`);
  if(shared.WT!=="decisions"&&(RR.from||RR.to)) chips.push(`<span class="fchip">Raised: ${RR.from?fd(RR.from):"…"} to ${RR.to?fd(RR.to):"…"}<button data-clr="rr" aria-label="Remove the raised date range">${ic("x")}</button></span>`);
  if(shared.WT!=="decisions"&&(shared.CR.from||shared.CR.to)) chips.push(`<span class="fchip">Closed: ${shared.CR.from?fd(shared.CR.from):"…"} to ${shared.CR.to?fd(shared.CR.to):"…"}<button data-clr="cr" aria-label="Remove the closed date range">${ic("x")}</button></span>`);
  if(shared.WQ.trim()) chips.push(fchipHtml(`Search: “${shared.WQ.trim()}”`,"q","Clear the search"));
  putHTML($("#wapplied"),html`${raw(chips.join(""))}${chips.length?html`<button class="linkbtn" id="clearF">Clear all</button>`:""}${!shared.WVIEW&&chips.length||!shared.WVIEW&&WB[shared.WT]?raw(viewSaveBtns()):""}<span class="sp"></span><span class="sub"><span id="wcount">Showing ${raw(shown)} of ${raw(total)}</span><span id="whidden"></span></span>`); }   /* BL-132: #whidden says what is hidden */
export const COLS={actions:[["id","ID"],["t","Action"],["o","Owner"],["due","Due"],["pr","Priority"],["st","Status"],["ws","Workstream"],["ms","Milestone"],["src","Source"],["upd","Last updated"]],raid:[["id","ID"],["t","Risk or issue"],["type","Type"],["o","Owner"],["due","Due"],["pr","Priority"],["resp","Response"],["st","Status"],["ws","Workstream"],["ms","Milestone"],["src","Source"],["upd","Last updated"]],   /* BL-128: Milestone and Last updated can be shown */decisions:[["id","ID"],["t","Decision"],["st","Status"],["by","Made by"],["due","Needed by"],["date","Date"],["src","Source"]]};
shared.COLVIS=store.get("creaite-cols",{actions:["t","o","due","pr","st"],raid:["t","o","due","pr","resp"],decisions:["t","st","by","due","date","src"]});
export const cmTag=x=>x.client&&!("cmd" in x?cmdOK(x.cmd):cmOK(x.cm))?' <span class="tag warn">· client messaging to complete</span>':"";
export function cell(k,x,t=shared.WT){ if(t==="all") return allCell(k,x);
  if(t==="decisions"&&k==="due") return `<td data-f="due" class="${decLate(x)?"late":""}" style="white-space:nowrap">${x.due?fd(x.due):"—"}<div class="x">${x.st==="Pending"&&x.due?rel(x.due):""}</div></td>`;
  const h=(()=>{ if(k==="t"){ const sub=t==="actions"?`${x.ws?esc(x.ws):""}${x.upd?` · ${esc(x.upd)}`:""}`:t==="raid"?`${x.type}${x.ws?" · "+esc(x.ws):""}${x.type==="Dependency"&&x.st==="Open"&&!x.ms?" · not attached":""}`:""; return `<td class="title" data-f="t">${ico(kindOf(t,x))}${esc(x.t)}${cmTag(x)}${x.ar?' <span class="tag">Archived</span>':""}<div class="x"><a href="#" class="rowid" data-rid="${x.id}" title="Open ${x.id}">${x.id}</a> · ${pLink(x.p)}${sub}</div></td>`; }
  if(k==="o") return `<td data-f="o">${personLink(x.o)}</td>`;
  if(k==="due") return `<td data-f="due" class="${(t==="actions"?overdue(x):x.st==="Open"&&x.due&&x.due<TODAY)?"late":""}" style="white-space:nowrap">${x.due?fd(x.due):"—"}<div class="x">${x.due&&OPENST(x.st)?rel(x.due):""}</div></td>`;
  if(k==="pr") return `<td data-f="${t==="raid"?"imp":"pr"}" class="${x.pr==="Urgent"?"prio-urgent":""}">${x.pr}</td>`;
  if(k==="st") return `<td data-f="st">${x.st}</td>`;
  if(k==="ws") return `<td data-f="ws">${esc(x.ws||"—")}</td>`;
  if(k==="resp") return `<td data-f="resp" class="x">${x.resp?esc(x.resp):'<span class="tag bad">None yet</span>'}</td>`;
  if(k==="by") return `<td data-f="by">${personLink(x.by,x.by)}</td>`;
  if(k==="date") return `<td data-f="date" style="white-space:nowrap">${fd(x.date)}</td>`;
  if(k==="id") return `<td class="x idc" style="white-space:nowrap">${x.id}</td>`;
  if(k==="type") return `<td data-f="type">${x.type}</td>`;
  if(k==="src") return `<td class="x">${esc(fdText(srcShort(x.src)))}</td>`;
  if(k==="ms") return `<td data-f="ms">${x.ms?esc(msLabel(x.ms)):"—"}</td>`;                                   /* BL-128 */
  if(k==="upd") return `<td class="x" style="white-space:nowrap">${x.upd_at?fd(x.upd_at.slice(0,10)):"—"}</td>`; return "<td></td>"; })();
    return h; }   /* BL-288: who Alan follows is never labelled */
export const msLabel=id=>{ for(const p of P){ const m=(p.ms||[]).find(m=>m[3]===id); if(m) return m[0]; } return ((D.milestone_names||{})[id]||[id])[0]; };   /* BL-128: the name alone */
/* BL-68: the heading row and a row of any list of one item type; Work and a person's page both draw theirs here.
   o.fixed: no drag to reorder; o.rz: remembered widths; o.pick: a Set of "type:id" adds a tick column (hand over);
   o.tr: extra attributes on the row */
export const rowHead=(t,C,s,o={})=>`<thead><tr>${o.pick?'<th class="pickcol" aria-label="Select"></th>':""}${C.map(c=>`<th data-col="${c[0]}"${o.fixed?"":' draggable="true"'} aria-sort="${s&&s.col===c[0]?(s.dir==="asc"?"ascending":"descending"):"none"}" title="Sort by ${c[1].toLowerCase()}"${o.rz&&shared.RZ[t+"|"+c[0]]?` style="width:${shared.RZ[t+"|"+c[0]]}px;min-width:${shared.RZ[t+"|"+c[0]]}px"`:""}>${c[1]}${s&&s.col===c[0]?`<span class="sarrow">${s.dir==="asc"?"▲":"▼"}</span>`:""}</th>`).join("")}</tr></thead>`;
export const rowHtml=(t,x,C,o={})=>`<tr class="click ${o.sel===x.id?"sel":""}${o.pick?" handpick":""}" data-row="${x.id}"${o.tr||""}>${o.pick?`<td class="pickcol"><input type="checkbox" class="handbox" data-hk="${t}:${x.id}" aria-label="Hand over ${esc(x.id)}" ${o.pick.has(t+":"+x.id)?"checked":""}></td>`:""}${C.map(c=>cell(c[0],x,t)).join("")}</tr>`;
export function renderWork(){ const fresh=!WINIT[shared.WT], dv=fresh?defaultView(shared.WT):null;   /* BL-136 */
  ALLC=null; if(shared.WT==="all") delete WLAY.all;   /* BL-113 */
  shared.CE=null;   /* BL-251 */
  if(WINIT[shared.WT]) syncView();   /* BL-132 */
  (()=>{ if(!WINIT[shared.WT]) applyView(defaultView(shared.WT));
  drawWorkTabs();   /* BL-316 */
  renderViewBar();   /* BL-131 */
  newTile();   /* BL-159 */
  drawWorkFilters(); if($("#workQ").value!==shared.WQ) $("#workQ").value=shared.WQ;
  const fromP=shared.FROMPROJ&&PROJF.size===1&&PROJF.has(shared.FROMPROJ)?shared.FROMPROJ:null; $("#workCrumb").hidden=!fromP;   /* BL-38 */
  if(fromP) putHTML($("#workCrumb"),html`<a href="#" data-go="projects">Projects</a><span aria-hidden="true">›</span><a href="#" data-proj="${raw(fromP)}">${raw(fromP)}</a><span aria-hidden="true">›</span><span aria-current="page">${raw({actions:"Actions",raid:"RAID",decisions:"Decisions"}[shared.WT])}</span>`);
  const C=orderedCols(), L=rows(), s=SORT[shared.WT];
  renderApplied(items().length,L.length); renderLayoutBar();
  if(layoutOf(shared.WT)==="board"){ $("#workTbl").textContent=""; renderBoard(L); return; }
  $("#workBoard").textContent="";
  putHTML($("#workTbl"),html`${raw(rowHead(shared.WT,C,s))}<tbody>${raw(listBody(shared.WT,C,L)||`<tr><td colspan="${C.length}"><div class="empty">${shared.WQ.trim()?`Nothing in this view matches “${esc(shared.WQ.trim())}”.`:"Nothing in this view."}</div></td></tr>`)}</tbody>`);
  rzApply(); sizeList(); })();
  { const total=items().length, shown=items().filter(x=>passes(x)).length, h=hiddenCount();
    const ht=h.n?` · ${h.n} ${h.closed?"closed ":""}hidden${h.closed?"":" by the status filter"}`:"", hs=$("#whidden"); if(hs) hs.textContent=ht;
    const e=$(layoutOf(shared.WT)==="board"?"#workBoard .empty":"#workTbl .empty");
    if(!shown&&e){ putHTML(e,raw(emptyHtml())); const F=activeFilters(); workAnnounce(F.length?e.querySelector("h2").textContent+". "+[...e.querySelectorAll(".relax > div")].map(d=>d.querySelector("span").textContent+": "+d.querySelector(".sub").textContent).join("; "):"Nothing here yet"); }
    else workAnnounce(`Showing ${shown} of ${total}${ht}`); }   /* BL-130 */
  $$("#v-work tr[data-row], #v-mine tr[data-row]").forEach(tr=>{ const td=tr.querySelector("td.title"); if(td&&!td.querySelector(".wflag")) addHTML(td,"afterbegin",raw(wflag(shared.WT,tr.dataset.row))); });   /* BL-51 */
  hlPrune();   /* BL-68 */
  ceDecorate();   /* BL-251 */
  allDecorate();   /* BL-113 */
  if(!shared.LOADING){ mDots("work");
    if(fresh&&dv&&dv!==allViews(shared.WT)[0].id) OPENEDON[shared.WT]=shared.WVIEW; openedNote();
  markStagedRows(); } }
shared.COLORD=store.get("creaite-colorder",{});
export function orderedCols(t=shared.WT){ const vis=COLS[t].filter(c=>shared.COLVIS[t].includes(c[0])||c[0]==="t"), ord=shared.COLORD[t]||[];
  return vis.sort((a,b)=>{ const i=ord.indexOf(a[0]), j=ord.indexOf(b[0]); return (i<0?99+COLS[t].indexOf(a):i)-(j<0?99+COLS[t].indexOf(b):j); }); }
export function moveCol(col,before){ const keys=orderedCols().map(c=>c[0]).filter(k=>k!==col); const i=before?keys.indexOf(before):keys.length; keys.splice(i<0?keys.length:i,0,col);
  shared.COLORD[shared.WT]=keys; store.set("creaite-colorder",shared.COLORD); renderWork(); }
export let DRAGCOL=null;
/* BL-77: this closes the menus on a click anywhere else. It used to run for the opening click too (a second listener on the same
   document isn't stopped by stopPropagation), so every filter menu closed the moment it opened. */
export async function saveView(name){ name=String(name||"").trim().replace(/[<>"]/g,""); if(!name){ snack("Name the view first"); return; }
  if(allViews(shared.WT).some(v=>v.label.toLowerCase()===name.toLowerCase())){ snack(`There's already a view called “${name}”`); return; }
  shared.SAVED[shared.WT]=[...(shared.SAVED[shared.WT]||[]),{name,...viewState()}]; if(await writeSettings({"work.saved_views":shared.SAVED})){ shared.WVIEW=WB[shared.WT]="saved:"+name; renderWork(); navWrite(false); snack(`View “${name}” saved`); } else shared.SAVED[shared.WT]=shared.SAVED[shared.WT].filter(v=>v.name!==name); }
export async function deleteView(name){ const before=shared.SAVED[shared.WT]; shared.SAVED[shared.WT]=before.filter(v=>v.name!==name);
  if(await writeSettings({"work.saved_views":shared.SAVED})){ if(WB[shared.WT]==="saved:"+name) WB[shared.WT]=null; if(shared.WVIEW==="saved:"+name){ shared.WVIEW=null; syncView(); } renderWork(); navWrite(false); snack(`View “${name}” deleted`,viewUndo(before)); } else shared.SAVED[shared.WT]=before; }
/* BL-316: a change to the saved views offers Undo (a move moves it back, a rename renames it back); a delete puts the tab's
   views back as they were */
export const viewUndo=before=>{ const t=shared.WT; return async()=>{ const now=shared.SAVED[t]; shared.SAVED[t]=before;
  if(await writeSettings({"work.saved_views":shared.SAVED})){ renderWork(); navWrite(false); snack("View put back"); } else shared.SAVED[t]=now; }; };
/* BL-62: each tab keeps its own filters, search and sort; switching tabs never carries filters across */
export const TABSTATE={};
export function saveTab(){ TABSTATE[shared.WT]={fx:snapshot(),p:[...PROJF],q:shared.WQ,view:shared.WVIEW,base:WB[shared.WT]||null}; }
/* BL-316: Work's tabs are the Tabs building block (#wtabs, drawn into #wtabsHost); ← → Home End wrap round */
export const WTABS=[["actions","Actions"],["raid","RAID"],["decisions","Decisions"],["all","All items"]].map(([t,l])=>({id:t,label:l,data:{t}}));
export function workTabGo(t){ if(t===shared.WT) return; saveTab(); loadTab(t); shared.SEL=null; hlClear(); closePanel(); renderWork(); navWrite(false); }
export function drawWorkTabs(){ const h=$("#wtabsHost"); if(h) drawTabs(h,{items:WTABS,selected:shared.WT,onSelect:workTabGo,label:"Work",className:"tabs",id:"wtabs",wrap:true}); }
export function clearAllFilters(){ Object.values(FX).forEach(s=>s.clear()); OWN.clear(); PRIF.clear(); PROJF.clear(); shared.DR={from:"",to:""}; RR={from:"",to:""}; shared.CR={from:"",to:""}; NEG.clear(); }
export function loadTab(t){ clearAllFilters(); shared.WT=t; const st=TABSTATE[t]; if(!st){ WINIT[t]=false; shared.WQ=""; return; }
  applyFilters(st.fx); st.p.forEach(c=>PROJF.add(c)); shared.WQ=st.q; WINIT[t]=true; syncView(); if(TABSTATE[t]&&TABSTATE[t].base) WB[t]=TABSTATE[t].base; }
   /* BL-159: on Decisions, the menu */
/* column chooser */
export function dispProps(){ const ord=orderedCols().map(c=>c[0]), rest=COLS[shared.WT].filter(c=>!ord.includes(c[0]));   /* BL-128: was the Columns menu */
  return [...orderedCols(),...rest].map(c=>{ const shown=ord.includes(c[0]), i=ord.indexOf(c[0]); return `<label><input type="checkbox" data-prop id="dprop-${c[0]}" value="${c[0]}" ${shown?"checked":""} ${c[0]==="t"?"disabled":""}>${c[1]}${shown?`<span class="colmv"><button type="button" data-mv="${c[0]}" data-d="-1" aria-label="Move ${c[1]} earlier" ${i===0?"disabled":""}>↑</button><button type="button" data-mv="${c[0]}" data-d="1" aria-label="Move ${c[1]} later" ${i===ord.length-1?"disabled":""}>↓</button></span>`:""}</label>`; }).join(""); }
/* BL-128 (sprint-work-views): the column chooser is the Display menu's Properties (dispProps); its moves and ticks are handled there */
/* resize columns (remembered) */
shared.RZ=store.get("creaite-colwidths",{});
/* BL-285: one column resizer for every remembered table (Work's, Today's Portfolio): a pointer drag, a keyboard separator
   (←/→, 16 px), 60 to 900 px, double-click puts the column back; widths in creaite-colwidths under the key given */
export function colResizer(th,k,after){ if(shared.RZ[k]){ th.style.width=shared.RZ[k]+"px"; th.style.minWidth=shared.RZ[k]+"px"; }
  const h=document.createElement("span"); h.className="colrz"; h.tabIndex=0; h.setAttribute("role","separator"); h.setAttribute("aria-label","Resize "+th.textContent+" column");
  /* v1.9.5 (UI audit P1-6): a focusable separator needs its value: the width in px, 60 to 900 */
  const val=w=>h.setAttribute("aria-valuenow",String(Math.round(Math.max(60,Math.min(900,w||0)))));
  h.setAttribute("aria-orientation","vertical"); h.setAttribute("aria-valuemin","60"); h.setAttribute("aria-valuemax","900"); val(shared.RZ[k]||th.getBoundingClientRect().width);
  h.addEventListener("focus",()=>val(th.getBoundingClientRect().width));
  const put=w=>{ w=Math.max(60,Math.min(900,w)); th.style.width=w+"px"; th.style.minWidth=w+"px"; shared.RZ[k]=Math.round(w); val(w); };
  h.addEventListener("click",e=>e.stopPropagation());
  h.addEventListener("pointerdown",e=>{ e.preventDefault(); const x0=e.clientX,w0=th.getBoundingClientRect().width; document.body.classList.add("resizing"); h.setPointerCapture(e.pointerId);
    const mv=ev=>put(w0+ev.clientX-x0);
    const up=()=>{ h.removeEventListener("pointermove",mv); h.removeEventListener("pointerup",up); h.removeEventListener("pointercancel",up); document.body.classList.remove("resizing"); store.set("creaite-colwidths",shared.RZ); if(after) after(); };
    h.addEventListener("pointermove",mv); h.addEventListener("pointerup",up); });
  h.addEventListener("dblclick",e=>{ e.stopPropagation(); delete shared.RZ[k]; th.style.width=""; th.style.minWidth=""; store.set("creaite-colwidths",shared.RZ); snack("Column width reset"); });
  h.addEventListener("keydown",e=>{ if(e.key!=="ArrowLeft"&&e.key!=="ArrowRight") return; e.preventDefault(); put(th.getBoundingClientRect().width+(e.key==="ArrowRight"?16:-16)); store.set("creaite-colwidths",shared.RZ); });
  th.appendChild(h); }
export function rzApply(){ $$("#workTbl th").forEach(th=>colResizer(th,shared.WT+"|"+th.dataset.col,sizeList)); }
/* frame holds 50 rows, then scrolls inside; never overhangs */
export const xcueSoon=()=>{ if(!shared.XCQ) shared.XCQ=requestAnimationFrame(xcueAll); };   /* declared before sizeList, which runs at load */
shared.XCQ=0;   /* declared before sizeList, which runs at load */
export function sizeList(){ const w=$("#workWrap"), t=$("#workTbl"); if(!w.offsetParent){ if(!shared.LOADING) xcueSoon(); return; } w.classList.toggle("hscroll",t.scrollWidth>w.clientWidth+1);
  const rs=[...t.tBodies[0].rows]; if(rs.length>50){ w.classList.add("capped"); w.style.maxHeight=(t.tHead.offsetHeight+rs.slice(0,50).reduce((a,r)=>a+r.getBoundingClientRect().height,0)+4)+"px"; } else { w.classList.remove("capped"); w.style.maxHeight=""; } 
  if(!shared.LOADING) xcueSoon(); }   /* BL-167: the "wider table scrolls" cue */
   /* BL-122: a click highlights; the ID opens. BL-123: a click on an editable value edits it */
   /* Shift-click selects rows, not text */
/* BL-144: one handler for every [data-open] link. A link that has no address of its own (href="#") would otherwise change the
   address to an empty one, which the page reads as Today; so it is cancelled here, for every view. A link with a real address
   (Activity's) is left to the browser on Cmd-, Ctrl- or Shift-click, to open that address in a new tab. */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootWork0034(){
$("#workTbl").addEventListener("dragstart",e=>{ const th=e.target.closest&&e.target.closest("th[data-col]"); if(!th||document.body.classList.contains("resizing")){ e.preventDefault(); return; } DRAGCOL=th.dataset.col; e.dataTransfer.effectAllowed="move"; e.dataTransfer.setData("text/plain",DRAGCOL); });
$("#workTbl").addEventListener("dragover",e=>{ const th=e.target.closest("th[data-col]"); if(!th||!DRAGCOL) return; e.preventDefault(); $$("#workTbl th").forEach(x=>x.classList.toggle("dropbefore",x===th&&th.dataset.col!==DRAGCOL)); });
$("#workTbl").addEventListener("drop",e=>{ const th=e.target.closest("th[data-col]"); if(!th||!DRAGCOL) return; e.preventDefault(); const c=DRAGCOL; DRAGCOL=null; if(th.dataset.col!==c) moveCol(c,th.dataset.col); });
$("#workTbl").addEventListener("dragend",()=>{ DRAGCOL=null; $$("#workTbl th").forEach(x=>x.classList.remove("dropbefore")); });
/* applied-filter chips, Clear all, Save view */
$("#wapplied").addEventListener("click",e=>{ const c=e.target.closest("[data-clr]");
  if(c){ const k=c.dataset.clr; if(k==="dr") shared.DR={from:"",to:""}; else if(k==="rr") RR={from:"",to:""}; else if(k==="cr") shared.CR={from:"",to:""}; else if(k==="q") shared.WQ=""; else { setOf(k).clear(); NEG.delete(k); } workChanged(); return; }
  if(e.target.id==="clearF"){ PROJF.clear(); shared.WQ=""; shared.FROMPROJ=null; applyView(PRESETS[shared.WT][0][0]); renderWork(); navWrite(false); snack(`Filters cleared`); return; }   /* BL-62 */
  if(e.target.id==="saveView"){ swapHTML(e.target,html`<span class="saveview"><input id="viewName" placeholder="Name this view" aria-label="View name"><button class="mini ok" id="viewSave">Save</button></span>`); $("#viewName").focus(); return; }
  if(e.target.id==="viewSave") saveView($("#viewName").value); });
$("#wapplied").addEventListener("keydown",e=>{ if(e.target.id==="viewName"){ if(e.key==="Enter") saveView(e.target.value); if(e.key==="Escape"){ e.stopPropagation(); renderWork(); } } });
$("#wviews").onclick=e=>{ if(e.target.closest("[data-vmenu],#vmore,#vrename,[data-vren]")) return;   /* BL-131: a saved view's menu, More views and renaming are handled below */
  const b=e.target.closest("[data-wv]"); if(!b) return; applyView(b.dataset.wv); renderWork(); navWrite(false); };
/* sortable headers (a drag still moves the column) */
$("#workTbl").addEventListener("click",e=>{ const th=e.target.closest("th[data-col]"); if(!th||e.target.closest(".colrz")||document.body.classList.contains("resizing")) return;
  const col=th.dataset.col, s=SORT[shared.WT]; SORT[shared.WT]=!s||s.col!==col?{col,dir:"asc"}:s.dir==="asc"?{col,dir:"desc"}:null; renderWork(); navWrite(false); });
drawWorkTabs();   /* BL-316: the Tabs block; choosing a tab is workTabGo */
$("#workQ").addEventListener("input",e=>{ shared.WQ=e.target.value; renderWork(); navWrite(false); });
$("#workQ").addEventListener("keydown",e=>{ if(e.key==="Escape"&&shared.WQ){ e.preventDefault(); e.stopPropagation(); shared.WQ=""; renderWork(); navWrite(false); } if(e.key==="Enter"){ const L=rows(); if(L.length){ e.preventDefault(); e.target.blur(); openRecord(shared.WT,L[0].id); } } });
window.addEventListener("resize",sizeList);
$("#workTbl").addEventListener("click",e=>{ if(e.target.closest(".colrz")) return; const tr=e.target.closest("tr[data-row]"); if(tr&&!ceClick(e,tr)) hlRowClick(e,shared.WT,tr); });
$("#workTbl").addEventListener("dblclick",e=>{ const tr=e.target.closest("tr[data-row]"); if(tr&&!e.target.closest("td.editing")) hlRowOpen(e,shared.WT,tr,false); });
$("#workTbl").addEventListener("mousedown",e=>{ if(e.shiftKey&&e.target.closest("tr[data-row]")) e.preventDefault(); });
document.addEventListener("click",e=>{ if(e.target.closest(".undset")) return; const o=e.target.closest("[data-open]"); if(!o) return;
  if(o.tagName==="A"&&(e.metaKey||e.ctrlKey||e.shiftKey)&&(o.getAttribute("href")||"#")!=="#") return;
  if(o.tagName==="A") e.preventDefault(); const [k,id]=o.dataset.open.split(":"); openRecord(k,id); });
}
/* ======================= Work board (BL-103, Sprint 4a) =======================
   A Board layout beside the List for Actions and RAID: the same items (the same filters, search, chips, saved views and sort,
   through passes() and rows()) as cards in columns. Dragging a card, or its "Move to…" menu, changes the item exactly as a cell
   edit does: boardMove() → commitRecord() → save(), so it is one proposal with Undo. No hand-ordering: nothing new is stored. */
export const BGROUPS=[["due","Due"],["status","Status"],["owner","Owner"],["milestone","Milestone"]], BDEFG={actions:"due",raid:"owner",decisions:"status"};
export const DGROUPS=[["status","Status"],["owner","Decision maker"],["due","Needed by"]];   /* BL-103: a decision has no milestone */
/* BL-129 (sprint-work-views): each tab's groupings, for the List's groups, the Board's columns and its swimlanes */
export const GROUPS={actions:[...BGROUPS,["project","Project"],["priority","Priority"],["workstream","Workstream"]],raid:[...BGROUPS,["project","Project"],["priority","Priority"],["type","Type"]],decisions:[...DGROUPS,["project","Project"]]};
export const groupsOf=t=>GROUPS[t];
export const WLAY=store.get("creaite-worklay",{}), WGRP=store.get("creaite-workgrp",{}), BHIDE=store.get("creaite-boardhide",{}), BCOLL=store.get("creaite-boardcoll",{});
export let BCUR=null, BDRAG=null, BNOCLICK=0; shared.LAYCHOSEN=false; export const BSHOWALL=new Set(), BCLALL=new Set(store.get("creaite-boardclosedall",[]));   /* BCLALL (BL-128): tabs whose Closed column shows all */
export const layoutOf=t=>WLAY[t]==="board"&&(shared.LAYCHOSEN||innerWidth>=640)?"board":"list";   /* under 640px the List is the default */
export const groupOf=t=>{ const ok=g=>groupsOf(t).some(x=>x[0]===g), set=({actions:S.bgActions,raid:S.bgRaid,decisions:S.bgDecisions})[t]; return ok(WGRP[t])?WGRP[t]:ok(set)?set:BDEFG[t]; };
export const isoAdd=(iso,n)=>{ const d=new Date(iso+"T12:00:00"); d.setDate(d.getDate()+n); return `${d.getFullYear()}-${z2(d.getMonth()+1)}-${z2(d.getDate())}`; };
export const isoDow=iso=>(new Date(iso+"T12:00:00").getDay()+6)%7, weekSun=iso=>isoAdd(iso,6-isoDow(iso));
export const thisFriday=()=>{ const f=isoAdd(TODAY,4-isoDow(TODAY)); return f<TODAY?TODAY:f; }, nextFriday=()=>isoAdd(weekSun(TODAY),-2+7);
export function dueBucket(t,x){ if(!(t==="actions"?open(x):x.st==="Open")) return "closed"; if(!x.due) return "none"; if(x.due<TODAY) return "overdue";
  const sun=weekSun(TODAY); return x.due<=sun?"week":x.due<=isoAdd(sun,7)?"next":"later"; }
export const initials=n=>!n||n==="TBC"?"?":String(n).trim().split(/\s+/).map((w,i,a)=>i===0||i===a.length-1?w[0]:"").join("").toUpperCase();
/* the columns for a tab's current grouping: {key,label,items,drop,value,why}; {pick:true} when Milestone needs a project first */
export function boardCols(t,L,g=groupOf(t)){ if(GENB.has(g)) return {cols:wgGroups(t,g,L,true).map(gr=>({key:gr.key,label:gr.label,items:gr.items,drop:!!gr.settable,value:gr.value,why:gr.why}))};
  if(t==="decisions") return decCols(L,g);
  const cols=[], closedDays=+S.boardClosedDays||14;
  const closedCol=(key,label,items,drop,extra)=>{ const all=BSHOWALL.has(t+"|"+g+"|"+key)||BCLALL.has(t), recent=items.filter(x=>!x.closed||days(x.closed)>=-closedDays);
    return {key,label,items:all?items:recent,hidden:all?0:items.length-recent.length,limited:true,drop,...extra}; };
  if(g==="due"){ const B={overdue:[],week:[],next:[],later:[],none:[],closed:[]}; L.forEach(x=>B[dueBucket(t,x)].push(x));
    cols.push({key:"overdue",label:"Overdue",items:B.overdue,drop:false,why:"Overdue is a date that has passed: pick a date in another column"},
      {key:"week",label:"This week",items:B.week,drop:true},{key:"next",label:"Next week",items:B.next,drop:true},{key:"later",label:"Later",items:B.later,drop:true},{key:"none",label:"No date",items:B.none,drop:true});
    if(B.closed.length) cols.push(closedCol("closed","Closed",B.closed,false,{why:"Change the status to close or reopen an item"})); }
  else if(g==="status"){ const sts=t==="actions"?["Open","Delayed","Closed","Cancelled"]:["Open","Closed","Cancelled"];
    sts.forEach(st=>{ const it=L.filter(x=>x.st===st); if(st==="Cancelled"&&!it.length) return;
      cols.push(st==="Closed"?closedCol(st,st,it,true,{value:st}):{key:st,label:st,items:it,drop:true,value:st}); }); }
  else if(g==="owner"){ const me=[], tbc=[], map=new Map();
    L.forEach(x=>{ const o=x.o; if(!o||o==="TBC") tbc.push(x); else if(isMe(o)) me.push(x); else { if(!map.has(o)) map.set(o,[]); map.get(o).push(x); } });
    cols.push({key:"@me",label:"Me",items:me,drop:true,value:S.me});
    [...map].sort((a,b)=>b[1].length-a[1].length||a[0].localeCompare(b[0])).forEach(([n,it])=>cols.push({key:n,label:n,items:it,drop:true,value:n}));
    cols.push({key:"TBC",label:"TBC",items:tbc,drop:true,value:"TBC"}); }
  else { if(PROJF.size!==1) return {pick:true}; const p=P.find(q=>q.code===[...PROJF][0]); if(!p) return {pick:true};
    const known=new Set(); p.ms.filter(m=>m[3]).forEach(m=>{ known.add(m[3]); const it=L.filter(x=>x.ms===m[3]); if(m[6]==="Cancelled"&&!it.length) return; cols.push({key:m[3],label:m[0]+(m[6]==="Cancelled"?" (cancelled)":""),items:it,drop:true,value:m[3]}); });
    cols.push({key:"",label:"No milestone",items:L.filter(x=>!x.ms||!known.has(x.ms)),drop:true,value:""}); }
  return {cols}; }
/* the column an item sits in under the current grouping */
export function boardKeyOf(t,g,x){ if(GENB.has(g)) return wgKey(t,g,x); if(t==="decisions"){ return g==="status"?x.st:g==="owner"?(!x.by?"@none":isMe(x.by)?"@me":x.by):decBucket(x); } if(g==="due") return dueBucket(t,x); if(g==="status") return x.st; if(g==="owner") return !x.o||x.o==="TBC"?"TBC":isMe(x.o)?"@me":x.o; return x.ms||""; }
export const ptCode=x=>`<span class="bpc" title="${esc(pName(x.p))}">${esc(pName(x.p))}</span>`;       /* BL-101: the name; long ones are cut by the width, never swapped for the code */
/* BL-128: a card shows the properties chosen in Display, in their order, at most four (the ID and project always) */
export const cardProps=t=>orderedCols(t).map(c=>c[0]).filter(k=>k!=="t"&&k!=="id").slice(0,4);
export const bprop=(k,x)=>k==="ws"?(x.ws?esc(x.ws):""):k==="ms"?(x.ms?esc(msLabel(x.ms)):""):k==="src"?esc(fdText(srcShort(x.src))):k==="upd"?(x.upd_at?"Updated "+fd(x.upd_at.slice(0,10)):""):k==="type"?esc(x.type||""):k==="resp"?(x.resp?"Response set":"No response"):k==="date"?(x.date?fd(x.date):""):k==="st"?esc(x.st):"";
export function cardHtml(t,x,g){ if(t==="decisions"){
    const pend=x.st==="Pending", late=decLate(x), P4=cardProps("decisions"), due=pend?(x.due?(late?decLateWords(x):rel(x.due)):"No date needed by"):x.st==="Made"?`Made ${x.date?fd(x.date):""}`.trim():"Withdrawn";
    return `<div class="bcard" role="listitem" tabindex="0" data-row="${esc(x.id)}" aria-label="${esc(x.id)}: ${esc(x.t)}">
    <div class="bct">${wflag("decisions",x.id)}${esc(x.t)}</div>
    <div class="bcm"><span class="bid">${esc(x.id)}</span>${ptCode(x)}${x.client?'<span class="bcv" title="Client-visible" aria-label="Client-visible">◐</span>':""}<span class="sp"></span>${P4.includes("by")?`<span class="bown" title="${esc(x.by?(pend?"Asked of ":"Made by ")+x.by:"No one asked yet")}">${esc(initials(x.by))}</span>`:""}</div>
    <div class="bcm">${P4.includes("due")?`<span class="bdue ${late?"late":""}">${esc(due)}</span>`:""}<span class="sp"></span>${P4.filter(k=>k==="date"||k==="src").map(k=>{ const v=bprop(k,x); return v?`<span class="bprop" data-p="${k}">${v}</span>`:""; }).join("")}${P4.includes("st")?`<span class="bpri ${pend?"":"bdecided"}">${esc(x.st)}</span>`:""}${pend?`<button class="bmv" type="button" aria-haspopup="menu" aria-label="Move ${esc(x.id)} to…" title="Move to…">⋯</button>`:""}</div></div>`; }
  const od=t==="actions"?overdue(x):x.st==="Open"&&x.due&&x.due<TODAY, op=t==="actions"?open(x):x.st==="Open";
  const due=!x.due?"No date":!op?`Due ${fd(x.due)}`:rel(x.due), P4=cardProps(t), extra=P4.filter(k=>!["o","due","pr"].includes(k)).map(k=>{ const v=bprop(k,x); return v?`<span class="bprop" data-p="${k}">${v}</span>`:""; }).join("");
  return `<div class="bcard" role="listitem" tabindex="0" data-row="${esc(x.id)}" aria-label="${esc(x.id)}: ${esc(x.t)}">
    <div class="bct">${wflag(t,x.id)}${esc(x.t)}</div>
    <div class="bcm"><span class="bid">${esc(x.id)}</span>${ptCode(x)}${x.client?'<span class="bcv" title="Client-visible" aria-label="Client-visible">◐</span>':""}<span class="sp"></span>${P4.includes("o")?`<span class="bown" title="${esc(x.o&&x.o!=="TBC"?x.o:"No owner yet")}">${esc(initials(x.o))}</span>`:""}</div>
    <div class="bcm">${P4.includes("due")?`<span class="bdue ${od?"late":""}">${esc(due)}</span>`:""}<span class="sp"></span>${extra}${P4.includes("pr")?`<span class="bpri ${x.pr==="Urgent"?"prio-urgent":""}">${esc(x.pr||"")}</span>`:""}<button class="bmv" type="button" aria-haspopup="menu" aria-label="Move ${esc(x.id)} to…" title="Move to…">⋯</button></div></div>`; }
export const bcKey=(t,g,key)=>`${t}|${g}|${key}`;
/* #144: each board column's width, per board (tab and grouping), remembered in the browser. 260 to 640 px, 270 by default;
   the handle on a column's right edge drags, ←/→ move it 16 px, a double-click puts it back. */
export const BW_MIN=260, BW_MAX=640, BW_DEF=270;
/* A remembered width is only trusted as a finite number inside the limits; anything else (null, arrays, strings, NaN, huge or negative values) is dropped on load. */
const bwOk=w=>typeof w==="number"&&Number.isFinite(w)&&w>=BW_MIN&&w<=BW_MAX;
const bwClean=raw=>{ const out={}; if(!raw||typeof raw!=="object"||Array.isArray(raw)) return out;
  Object.keys(raw).forEach(b=>{ const o=raw[b]; if(!o||typeof o!=="object"||Array.isArray(o)) return; const k={};
    Object.keys(o).forEach(c=>{ if(bwOk(o[c])) k[c]=Math.round(o[c]); }); if(Object.keys(k).length) out[b]=k; }); return out; };
export const BW=bwClean(store.get("creaite-boardw",{}));
const bwBoard=()=>BCUR?`${BCUR.t}|${BCUR.g}`:`${shared.WT}|${groupOf(shared.WT)}`;
export const bwGet=(b,key)=>{ const o=BW[b]; if(!o||typeof o!=="object") return undefined; const w=o[key]; return bwOk(w)?w:undefined; };
const bwStyle=(b,key)=>{ const w=bwGet(b,key); return w?` style="flex-basis:${w}px;width:${w}px"`:""; };
const bwHandle=(b,key,label,w)=>`<span class="bcrz" role="separator" tabindex="0" aria-orientation="vertical" aria-label="Resize ${esc(label)} column" aria-valuemin="${BW_MIN}" aria-valuemax="${BW_MAX}" aria-valuenow="${w||BW_DEF}"></span>`;
export function bwPut(b,key,w,save){ w=Number(w); if(!Number.isFinite(w)) w=BW_DEF; w=Math.round(Math.max(BW_MIN,Math.min(BW_MAX,w)));
  if(w===BW_DEF){ if(BW[b]){ delete BW[b][key]; if(!Object.keys(BW[b]).length) delete BW[b]; } } else { if(!BW[b]||typeof BW[b]!=="object") BW[b]={}; BW[b][key]=w; }
  $$("#workBoard .bcol").forEach(c=>{ if(c.dataset.col!==key) return; c.style.flexBasis=w+"px"; c.style.width=w+"px"; const h=c.querySelector(".bcrz"); if(h) h.setAttribute("aria-valuenow",String(w)); });
  if(save) store.set("creaite-boardw",BW); return w; }
export function bwReset(b,key){ bwPut(b,key,BW_DEF,true); }
export function renderBoard(L){ const t=shared.WT, sg=subOf(t,"board"), g=groupOf(t), el=$("#workBoard");
  if(sg!=="none"&&L.length){ const B=boardCols(t,L,g); if(!B.pick){   /* swimlanes: one row per sub-group value, each with the board's columns */
    const lanes=wgGroups(t,sg,L,!BHIDE[t]); BCUR={t,g,cols:B.cols,sub:sg,lanes};
    let cols=B.cols; if(BHIDE[t]) cols=cols.filter(c=>c.items.length||c.hidden);
    putHTML($("#workBoard"),html`<div class="bswim">${raw(lanes.map(ln=>{ const k=`${t}|${g}|lane|${sg}|${ln.key}`, coll=!!BCOLL[k], n=ln.items.length, inl=new Set(ln.items.map(x=>x.id));
      return `<section class="blane${coll?" collapsed":""}" data-lane="${esc(ln.key)}" aria-label="${esc(ln.label)}, ${n} item${n===1?"":"s"}">
        <header class="blh"><button class="bcoll" type="button" data-bcoll="${esc(k)}" aria-expanded="${!coll}" aria-label="${coll?"Expand":"Collapse"} ${esc(ln.label)}">${ic("chevdown","chev")}</button><h3>${esc(ln.label)} · ${n}</h3></header>
        ${coll?"":`<div class="blcols">${cols.map(c=>{ const it=c.items.filter(x=>inl.has(x.id)), m=it.length;
          return `<section class="bcol${c.drop?"":" nodrop"}" data-col="${esc(c.key)}" data-lane="${esc(ln.key)}"${bwStyle(`${t}|${g}`,c.key)} aria-label="${esc(c.label)} in ${esc(ln.label)}, ${m} item${m===1?"":"s"}"><header class="bch"><h3>${esc(c.label)} · ${m}</h3></header>
            <div class="bcards" role="list">${it.map(x=>cardHtml(t,x,g)).join("")||'<div class="bnone">Nothing here</div>'}</div><div class="bdrop" aria-hidden="true">${c.drop?"Drop to move here":esc(c.why||"Can't drop here")}</div>${bwHandle(`${t}|${g}`,c.key,c.label,bwGet(`${t}|${g}`,c.key))}</section>`; }).join("")}</div>`}</section>`; }).join(""))}</div>`);
    markSel(); return; } }
  const B=boardCols(t,L,g);
  if(B.pick){ BCUR={t,g,cols:[]}; putHTML(el,html`<div class="bpick"><b>Group by milestone needs one project.</b> Milestones belong to a project, so choose one: <select id="bpickP" aria-label="Project for the milestone board"><option value="">Choose a project</option>${P.map(p=>html`<option value="${p.code}">${p.name}</option>`)}</select></div>`); return; }
  BCUR={t,g,cols:B.cols}; let cols=B.cols; if(BHIDE[t]) cols=cols.filter(c=>c.items.length||c.hidden);
  if(!L.length){ putHTML(el,html`<div class="empty">${shared.WQ.trim()?html`Nothing in this view matches “${shared.WQ.trim()}”.`:"Nothing in this view."}</div>`); return; }
  putHTML(el,raw(cols.map(c=>{ const k=bcKey(t,g,c.key), coll=!!BCOLL[k], n=c.items.length;
    return `<section class="bcol${coll?" collapsed":""}${c.drop?"":" nodrop"}" data-col="${esc(c.key)}"${coll?"":bwStyle(`${t}|${g}`,c.key)} aria-label="${esc(c.label)}, ${n} item${n===1?"":"s"}">
      <header class="bch"><button class="bcoll" type="button" data-bcoll="${esc(k)}" aria-expanded="${!coll}" aria-label="${coll?"Expand":"Collapse"} ${esc(c.label)}">${ic("chevdown","chev")}</button><h3>${esc(c.label)} · ${n}</h3></header>
      ${coll?"":`<div class="bcards" role="list">${c.items.map(x=>cardHtml(t,x,g)).join("")||'<div class="bnone">Nothing here</div>'}</div>
      ${c.limited&&(c.hidden||BSHOWALL.has(k))?`<button class="linkbtn bshow" type="button" data-bshow="${esc(k)}">${BSHOWALL.has(k)?`Last ${+S.boardClosedDays||14} days only`:`Show all (${c.hidden} older)`}</button>`:""}
      <div class="bdrop" aria-hidden="true">${c.drop?"Drop to move here":esc(c.why||"Can't drop here")}</div>${bwHandle(`${t}|${g}`,c.key,c.label,bwGet(`${t}|${g}`,c.key))}`}</section>`; }).join("")||`<div class="empty">Nothing in this view.</div>`));
  markSel(); }
export function renderLayoutBar(){ const t=shared.WT, bd=layoutOf(t)==="board";
  $$("#wlay button").forEach(b=>b.setAttribute("aria-pressed",String(b.dataset.lay===(bd?"board":"list"))));
  $("#workWrap").style.display=bd?"none":""; $("#workBoard").hidden=!bd;
  $("#whintList").hidden=bd; $("#whintBoard").hidden=!bd;      /* BL-114 (sprint-polish): the hint line is written for the layout in use */
  putHTML($("#whintList"),raw(workHint("list"))); putHTML($("#whintBoard"),raw(workHint("board")));   /* BL-128: one function builds both */
  drawDisp(); }   /* always drawn (hidden until opened), so its controls exist for the address and the tests */
export function setLayout(t,lay){ if(t==="all") return; shared.LAYCHOSEN=true; WLAY[t]=lay; store.set("creaite-worklay",WLAY); renderWork(); navWrite(false); }
/* what a move to a column changes. Due asks for a date (never a past one); the others set the field. Returns false if cancelled. */
export async function boardDrop(id,key){ { const t=shared.WT, g=BCUR&&BCUR.g; if(GENB.has(g)){ const x=REC(t,id), col=BCUR.cols.find(c=>c.key===key);
    if(!x||!col||boardKeyOf(t,g,x)===key) return false; if(t==="decisions"&&x.st!=="Pending"){ snack(`${x.id} is ${x.st.toLowerCase()}: only a pending decision can be moved`); return false; }
    const p=wgPatch(t,g,{settable:col.drop,value:col.value}); if(!p){ snack(col.why||"Can't drop there"); return false; } return boardMove(t,id,p,`${x.id} moved to ${col.label}`); } }
  if(shared.WT==="decisions") return decBoardDrop(id,key);
  const t=shared.WT, x=REC(t,id), g=BCUR&&BCUR.g, col=BCUR&&boardTargets(t,g).find(c=>c.key===key); if(!x||!col||!col.drop) return false;
  if(boardKeyOf(t,g,x)===key) return false;
  const what=`${x.id} moved to ${col.label}: ${x.t.length>60?x.t.slice(0,57)+"…":x.t}`; let patch;
  if(g==="due"){ if(key==="none"){ if(!await boardAsk({title:`Clear the due date of ${x.id}?`,hint:x.t,clear:true})) return false; patch={due:""}; }
    else { const d=await boardAsk({title:`Due date for ${x.id}`,hint:x.t,date:key==="week"?thisFriday():key==="next"?nextFriday():isoAdd(TODAY,14),range:key}); if(!d) return false; patch={due:d}; } }
  else if(g==="status") patch={st:col.value};
  else if(g==="owner") patch={o:col.value};
  else patch={ms:col.value};
  return await boardMove(t,id,patch,what); }
/* one change, saved as a cell edit is: the same checks (validate, norm, the owner resolved against the register), one proposal, Undo */
export async function boardMove(k,id,patch,label){ const x=REC(k,id); if(!x) return false; const f={...patch};
  for(const n of ["o","by"]) if(n in f&&f[n]&&f[n]!=="TBC"){ const o=await ownerFinal(f[n]); if(o===null) return false; f[n]=o; }
  if("st" in f&&k!=="decisions") f.closed=x.closed||null;                 /* closing fills today; reopening clears it (norm), as the form does */
  if(k==="raid"){ if(!("imp" in f)) f.imp=x.imp; if(!("lik" in f)) f.lik=x.lik; }
  norm(k,f); const v={...f}; if("closed" in v) v.raised=x.raised; delete v.imp; delete v.lik; delete v.pr;
  const err=validate(k,v,false,x); if(err){ snack(oneLine(err)); return false; }
  const r=await commitRecord(k,id,f,label); if(r==="nochange") return false; return !!r; }
/* the date prompt (and the "clear the date?" question): a small dialog; resolves to YYYY-MM-DD, true (clear) or null */
export function boardAsk(o){ const {title,hint,date,clear,range,okText}=o, p=new Promise(res=>{ const dlg=$("#boardDlg"); let done=false; const fin=v=>{ if(done) return; done=true; closeCal(); if(dlg.open) dlg.close(); res(v); };
  $("#bdTitle").textContent=title; $("#bdHint").textContent=hint||""; $("#bdErr").textContent=""; $("#bdDateRow").hidden=!!clear;
  const inp=$("#bdDate"); inp.value=date?fd(date):""; $("#bdOk").textContent=okText||(clear?"Clear date":"Move");
  $("#bdRange").textContent=range==="week"?`This week runs to ${fd(weekSun(TODAY))}.`:range==="next"?`Next week is ${fd(isoAdd(weekSun(TODAY),1))} to ${fd(isoAdd(weekSun(TODAY),7))}.`:range==="later"?`Later starts ${fd(isoAdd(weekSun(TODAY),8))}.`:"";
  const ok=()=>{ if(clear){ fin(true); return; } const v=inp.value.trim(); if(!DDATE.test(v)){ $("#bdErr").textContent="Not a date creaite knows. "+DATE_HELP; return; } const iso=toIso(v);
    if(isNaN(new Date(iso))||fd(iso)!==v){ $("#bdErr").textContent="That isn't a real date."; return; } if(iso<TODAY){ $("#bdErr").textContent="Choose today or a later day: a past date would make it overdue."; return; } fin(iso); };
  $("#bdOk").onclick=ok; $("#bdCancel").onclick=()=>fin(null); dlg.onclose=()=>fin(null); inp.onkeydown=e=>{ if(e.key==="Enter"){ e.preventDefault(); ok(); } };
  $$("#bdQuick [data-q]").forEach(b=>b.onclick=()=>{ inp.value=fd(b.dataset.q==="fri"?thisFriday():b.dataset.q==="nfri"?nextFriday():isoAdd(TODAY,14)); $("#bdErr").textContent=""; });
  openDialog(dlg,{focus:clear?"#bdOk":"#bdDate"}); if(!clear) inp.select(); });
  const ok0=$("#bdOk").onclick, inp=$("#bdDate");
    if(!o.clear){ const gated=()=>{ wkClear(); const v=inp.value.trim(), iso=DDATE.test(v)?toIso(v):""; if(iso&&iso>=TODAY&&!WK.ok&&wkAsk(iso,$("#bdDateRow"),d=>{ inp.value=fd(d); ok0(); },{inline:true,after:$("#bdDateRow")})) return; ok0(); };
      $("#bdOk").onclick=gated; inp.onkeydown=e=>{ if(e.key==="Enter"){ e.preventDefault(); gated(); } }; }
    p.finally(wkClear); return p; }
/* "Move to…" on a card: the same moves, without dragging */
export function boardMoveMenu(btn,id){ if(menuOpenFor(btn)){ closeMenu(); return; }
  { const x=REC(shared.WT,id); if(shared.WT==="decisions"&&x&&x.st!=="Pending"){ snack(`${x.id} is ${x.st.toLowerCase()}: it can't be moved`); return; } }   /* Move to… offers nothing for a decision that is no longer pending */
  const t=shared.WT, x=REC(t,id), g=BCUR&&BCUR.g; if(!x||!BCUR) return;
  const cur=boardKeyOf(t,g,x), cols=boardTargets(t,g).filter(c=>c.drop&&c.key!==cur), sub=BCUR.sub, lanes=sub?BCUR.lanes.filter(l=>l.key!==wgKey(t,sub,x)):[];
  /** @type {any[]} */ const items=[...(sub?[{id:"h1",head:grpLabel(t,g)}]:[]),
    ...(cols.length?cols.map(c=>({id:"c:"+c.key,name:c.label,data:{bto:c.key}})):[{id:"n1",note:"Nowhere else to move it"}]),
    ...(sub?[{id:"h2",head:`${grpLabel(t,sub)} (lane)`},...(lanes.length?lanes.map(l=>({id:"l:"+l.key,name:l.label,disabled:!l.settable,tip:l.settable?undefined:l.why||"",data:{blto:l.key}})):[{id:"n2",note:"No other lane"}])]:[])];
  openMenu(btn,{label:`Move ${x.id} to`,id:"bdMoveMenu",align:"right",items,
    onPick:k=>{ if(k.startsWith("c:")) boardDrop(id,k.slice(2)); else laneDrop(id,boardKeyOf(t,BCUR.g,x),k.slice(2)); }}); }
/* every column the grouping can move an item to, including a Cancelled column that is hidden while empty */
export function boardTargets(t,g){ const all=[...BCUR.cols], end=t==="decisions"?"Withdrawn":"Cancelled"; if(g==="status"&&!all.some(c=>c.key===end)) all.push({key:end,label:end,drop:true,value:end,items:[]}); BCUR.all=all; return all; }
   /* BL-122 */
   /* BL-122: Space highlights, Enter opens */
/* dragging, with pointer events (so a mouse, a pen and the test driver all work). The card moves only when it is dropped on a
   column that accepts it; Esc or dropping anywhere else puts it back. Overdue and Closed (in Due) are not drop targets. */
export function boardDragEnd(){ const d=BDRAG; BDRAG=null; if(!d) return null; if(d.ghost) d.ghost.remove(); d.card.classList.remove("dragging"); document.body.classList.remove("bdragging"); $$("#workBoard .bcol").forEach(c=>c.classList.remove("drop","nodrop-hover")); return d; }
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootWork0035(){
$("#wlay").addEventListener("click",e=>{ const b=e.target.closest("[data-lay]"); if(b) setLayout(shared.WT,b.dataset.lay); });
$("#workBoard").addEventListener("click",e=>{ if(performance.now()-BNOCLICK<30) return;
  const mv=e.target.closest(".bmv"); if(mv){ e.stopPropagation(); boardMoveMenu(mv,mv.closest(".bcard").dataset.row); return; }
  const cl=e.target.closest("[data-bcoll]"); if(cl){ const k=cl.dataset.bcoll; BCOLL[k]=!BCOLL[k]; store.set("creaite-boardcoll",BCOLL); renderWork(); return; }
  const sh=e.target.closest("[data-bshow]"); if(sh){ const k=sh.dataset.bshow; BSHOWALL.has(k)?BSHOWALL.delete(k):BSHOWALL.add(k); renderWork(); return; }
  const col=e.target.closest(".bcol.collapsed"); if(col){ const k=bcKey(shared.WT,groupOf(shared.WT),col.dataset.col); BCOLL[k]=false; store.set("creaite-boardcoll",BCOLL); renderWork(); return; }
  const c=e.target.closest(".bcard"); if(c) hlRowClick(e,shared.WT,c); });
$("#workBoard").addEventListener("pointerdown",e=>{ const h=e.target.closest&&e.target.closest(".bcrz"); if(!h||e.button!==0) return; e.preventDefault(); e.stopPropagation();
  const col=h.closest(".bcol"), key=col.dataset.col, b=bwBoard(), x0=e.clientX, w0=col.getBoundingClientRect().width; document.body.classList.add("resizing"); h.setPointerCapture(e.pointerId);
  const mv=ev=>bwPut(b,key,w0+ev.clientX-x0,false), up=()=>{ h.removeEventListener("pointermove",mv); h.removeEventListener("pointerup",up); h.removeEventListener("pointercancel",up); document.body.classList.remove("resizing"); store.set("creaite-boardw",BW); BNOCLICK=performance.now(); };
  h.addEventListener("pointermove",mv); h.addEventListener("pointerup",up); h.addEventListener("pointercancel",up); },true);
$("#workBoard").addEventListener("dblclick",e=>{ const h=e.target.closest&&e.target.closest(".bcrz"); if(!h) return; e.stopPropagation(); bwReset(bwBoard(),h.closest(".bcol").dataset.col); snack("Column width reset"); },true);
$("#workBoard").addEventListener("keydown",e=>{ const h=e.target.closest&&e.target.closest(".bcrz"); if(!h||(e.key!=="ArrowLeft"&&e.key!=="ArrowRight")) return; e.preventDefault(); e.stopPropagation();
  const col=h.closest(".bcol"); bwPut(bwBoard(),col.dataset.col,col.getBoundingClientRect().width+(e.key==="ArrowRight"?16:-16),true); },true);
$("#workBoard").addEventListener("dblclick",e=>{ const c=e.target.closest(".bcard"); if(c&&!e.target.closest(".bmv")) hlRowOpen(e,shared.WT,c); });
$("#workBoard").addEventListener("mousedown",e=>{ if(e.shiftKey&&e.target.closest(".bcard")) e.preventDefault(); });
$("#workBoard").addEventListener("change",e=>{ if(e.target.id==="bpickP"&&e.target.value){ PROJF.clear(); PROJF.add(e.target.value); workChanged(); } });
$("#workBoard").addEventListener("keydown",e=>{ const c=e.target.closest(".bcard"); if(c&&e.target===c&&(e.key==="Enter"||e.key===" ")){ e.preventDefault(); if(e.key===" "){ hlToggle(shared.WT,c.dataset.row); return; } hlOnly(shared.WT,c.dataset.row); openRecord(shared.WT,c.dataset.row); } });
$("#workBoard").addEventListener("pointerdown",e=>{ if(e.button!==0||e.pointerType==="touch") return; const c=e.target.closest(".bcard"); if(!c||e.target.closest("button,a,input,select")) return;
  BDRAG={id:c.dataset.row,card:c,x:e.clientX,y:e.clientY,active:false,over:null,ghost:null}; });
document.addEventListener("pointermove",e=>{ const d=BDRAG; if(!d) return;
  if(!d.active){ if(Math.hypot(e.clientX-d.x,e.clientY-d.y)<6) return; d.active=true; d.card.classList.add("dragging"); document.body.classList.add("bdragging");
    d.ghost=d.card.cloneNode(true); d.ghost.classList.add("bghost"); d.ghost.removeAttribute("id"); d.ghost.style.width=d.card.getBoundingClientRect().width+"px"; document.body.appendChild(d.ghost); }
  d.ghost.style.left=(e.clientX+10)+"px"; d.ghost.style.top=(e.clientY+10)+"px";
  const wb=$("#workBoard").getBoundingClientRect(); if(e.clientX>wb.right-48) $("#workBoard").scrollLeft+=18; else if(e.clientX<wb.left+48) $("#workBoard").scrollLeft-=18;
  const el=document.elementFromPoint(e.clientX,e.clientY), col=el&&el.closest&&el.closest("#workBoard .bcol"); d.over=col?col.dataset.col:null; d.lane=col?col.dataset.lane:undefined;   /* BL-129: and the swimlane */
  $$("#workBoard .bcol").forEach(c=>{ const on=c===col; c.classList.toggle("drop",on&&!c.classList.contains("nodrop")); c.classList.toggle("nodrop-hover",on&&c.classList.contains("nodrop")); }); });
document.addEventListener("pointerup",e=>{ const d=BDRAG; if(!d) return; if(!d.active){ BDRAG=null; return; }
  const over=d.over, ok=over!==null&&!!BCUR.cols.find(c=>c.key===over&&c.drop); boardDragEnd(); BNOCLICK=performance.now();
  if(BCUR.sub&&over!==null&&d.lane!==undefined){ laneDrop(d.id,over,d.lane); return; }   /* BL-129: a swimlane board: the column, the lane or both */
  if(over!==null&&!ok){ const c=BCUR.cols.find(c=>c.key===over); snack(c&&c.why?c.why:"Can't drop there"); return; }
  if(ok) boardDrop(d.id,over); });
document.addEventListener("keydown",e=>{ if(e.key==="Escape"&&BDRAG&&BDRAG.active){ e.preventDefault(); e.stopPropagation(); boardDragEnd(); BNOCLICK=performance.now(); } },true);
}
/* ===== BL-128 (sprint-work-views) =====
   One Display menu beside the List | Board switch: Layout, Group by, Sub-group, Order by (with a reverse button), Properties (the List's
   columns and the Board card's fields, at most four on a card) and Show (empty groups; on the Board, the Closed column's window). Options
   that don't apply to the layout in use are hidden, not greyed (BL-114). Reset returns the tab's display to its default (the layout
   stays as it is). D opens it; Esc or Done closes it and puts the focus back on the button. Nothing here changes what is filtered. */
export const WLGRP=store.get("creaite-listgrp",{}), WSUB=store.get("creaite-worksub",{});    /* the List's grouping per tab (none by default); the sub-group per tab and layout */
export const DEFCOLS={actions:["t","o","due","pr","st"],raid:["t","o","due","pr","resp"],decisions:["t","st","by","due","date","src"]};
export const dispOpen=()=>$("#dispMenu").classList.contains("on");
export const SORTOPTS=t=>t==="decisions"?[["","Default order"],["due","Needed by"],["date","Date"],["st","Status"],["by","Made by"],["t","Title"],["upd","Last updated"],["id","ID"]]
  :[["","Default order"],["due","Due date"],["pr","Priority"],["st","Status"],["o","Owner"],["t","Title"],["upd","Last updated"],["raised","Raised"],["id","ID"]];
/* the key-hint line for each layout, built from the controls that exist (BL-114, BL-122, BL-123, BL-128) */
/** @type {[string[] | "", string, string][]} the keys (or none), what they do, and the layout they belong to */
export const HINTS=[[["J","K"],"move","list"],[["J","K"],"step through the cards","board"],[["Space"],"select","both"],["","click a value to change it","list"],[["Enter"],"or the ID opens","both"],
  ["","drag a card, or use its <b>Move to…</b> menu, to change it","board"],[["D"],"display","both"],[["F"],"filters","both"],[["Esc"],"clear","both"],["","click a heading to sort","list"],["","drag a column edge to resize","list"]];
export function workHint(lay){ return HINTS.filter(h=>h[2]==="both"||h[2]===lay).map(([k,t])=>(k?k.map(x=>`<span class="kbd">${x}</span>`).join(" ")+" ":"")+t).join(" · "); }
export function drawDisp(){ const m=$("#dispMenu"), t=shared.WT, bd=layoutOf(t)==="board", s=SORT[t], cur=s?(s.col==="_def"?"":s.col):"", opts=SORTOPTS(t), focusKey=document.activeElement&&m.contains(document.activeElement)?(document.activeElement.id||document.activeElement.dataset.mv+"|"+document.activeElement.dataset.d):null;
  const gopts=bd?groupsOf(t):[["none","None"],...groupsOf(t)], gcur=bd?groupOf(t):listGroupOf(t), sub=subOf(t,bd?"board":"list");   /* BL-129: the List groups too */
  putHTML(m,html`<div><h3><label for="wgrp">${bd?"Group by (columns)":"Group by"}</label></h3><div class="dline"><select id="wgrp">${gopts.map(g=>html`<option value="${g[0]}" ${g[0]===gcur?"selected":""}>${g[1]}</option>`)}</select></div></div>
    <div ${!bd&&gcur==="none"?"hidden":""}><h3><label for="wsub">${bd?"Sub-group (swimlanes)":"Sub-group"}</label></h3><div class="dline"><select id="wsub"><option value="none">None</option>${groupsOf(t).filter(g=>g[0]!==gcur).map(g=>html`<option value="${g[0]}" ${g[0]===sub?"selected":""}>${g[1]}</option>`)}</select></div></div>
    <h3><label for="wbsort">Order by</label></h3><div class="dline"><select id="wbsort">${opts.map(o=>html`<option value="${o[0]}" ${o[0]===cur?"selected":""}>${o[1]}</option>`)}${cur&&!opts.some(o=>o[0]===cur)?html`<option value="${cur}" selected>Sorted by ${cur}</option>`:""}</select><button type="button" class="btn" id="wordRev" aria-pressed="${raw(!!(s&&s.dir==="desc"))}" aria-label="Reverse the order" title="Reverse the order">⇅</button></div>
    <h3>Properties${bd?html` <span class="sub">· a card shows the first four</span>`:""}</h3><div class="dprops">${raw(dispProps())}</div>
    <h3>Show</h3><div class="dline" ${!bd&&gcur==="none"?"hidden":""}><label class="dchk"><input type="checkbox" id="wshowempty" ${BHIDE[t]?"":"checked"}> Empty groups</label></div>${bd?html`
    <div class="dline"><label for="wclosed">${t==="decisions"?"Decided":"Closed"} column</label><select id="wclosed"><option value="recent" ${BCLALL.has(t)?"":"selected"}>Last ${raw(+S.boardClosedDays||14)} days</option><option value="all" ${BCLALL.has(t)?"selected":""}>All</option></select></div>`:html`<div class="dline sub">Closed items: use the Status filter.</div>`}
    <div class="dfoot"><button type="button" class="linkbtn" id="dispReset">Reset to this tab’s default</button><span class="sp"></span><button type="button" class="btn primary" id="dispDone">Done</button></div>`);
  if(focusKey){ const f=m.querySelector("#"+CSS.escape(focusKey))||(focusKey.includes("|")?m.querySelector(`[data-mv="${focusKey.split("|")[0]}"][data-d="${focusKey.split("|")[1]}"]`):null); if(f&&!f.disabled) f.focus(); else m.querySelector("button,select,input")?.focus(); }
  { if(shared.WT!=="all") return; const m=$("#dispMenu"), seg=m.querySelector('.seg[aria-label="Layout"]');
    if(seg){ const line=seg.closest(".dline"); if(line.previousElementSibling&&line.previousElementSibling.tagName==="H3") line.previousElementSibling.remove(); line.remove(); }
    const s=$("#wbsort"); if(!s) return; const cur=SORT.all&&SORT.all.col!=="_def"?SORT.all.col:"";
    [...s.options].forEach(o=>{ if(/^Sorted by /.test(o.textContent)) o.remove(); });
    addHTML(s,"beforeend",html`<option value="type">Type</option><option value="p">Project</option>`); s.value=cur; } }
export function openDisp(){ const m=$("#dispMenu"); if(dispOpen()){ closeDisp(true); return; } $$(".ddmenu.on").forEach(x=>x.classList.remove("on")); drawDisp(); m.hidden=false; m.classList.add("on"); $("#dispBtn").setAttribute("aria-expanded","true"); $("#dispBtn").classList.add("on");
  (m.querySelector('[aria-pressed="true"]')||m.querySelector("button,select,input"))?.focus(); }
export function closeDisp(focus){ const m=$("#dispMenu"); if(!dispOpen()&&m.hidden) return; m.classList.remove("on"); m.hidden=true; $("#dispBtn").setAttribute("aria-expanded","false"); $("#dispBtn").classList.remove("on"); if(focus) $("#dispBtn").focus(); }
export function dispChanged(){ renderWork(); navWrite(false); }
export function dispReset(){ const t=shared.WT; delete WGRP[t]; delete WLGRP[t]; delete WSUB[t+"|list"]; delete WSUB[t+"|board"]; SORT[t]=null; shared.COLVIS[t]=[...DEFCOLS[t]]; delete shared.COLORD[t]; delete BHIDE[t]; BCLALL.delete(t);
  store.set("creaite-workgrp",WGRP); store.set("creaite-listgrp",WLGRP); store.set("creaite-worksub",WSUB); store.set("creaite-cols",shared.COLVIS); store.set("creaite-colorder",shared.COLORD); store.set("creaite-boardhide",BHIDE); store.set("creaite-boardclosedall",[...BCLALL]);
  dispChanged(); snack("Display reset to this tab’s default"); }
/* ===== end BL-128 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootWork0036(){
$("#dispBtn").addEventListener("click",e=>{ e.stopPropagation(); openDisp(); });
$("#dispMenu").addEventListener("click",e=>{ e.stopPropagation(); const t=shared.WT;
  const l=e.target.closest("[data-dlay]"); if(l){ setLayout(t,l.dataset.dlay); return; }
  const mv=e.target.closest("[data-mv]"); if(mv){ e.preventDefault(); const ord=orderedCols().map(c=>c[0]), i=ord.indexOf(mv.dataset.mv), j=i+Number(mv.dataset.d);
    if(j<0||j>=ord.length) return; [ord[i],ord[j]]=[ord[j],ord[i]]; shared.COLORD[t]=ord; store.set("creaite-colorder",shared.COLORD); dispChanged(); return; }
  if(e.target.id==="wordRev"){ const s=SORT[t]; SORT[t]=!s?{col:"_def",dir:"desc"}:{col:s.col,dir:s.dir==="desc"?"asc":"desc"}; if(SORT[t].col==="_def"&&SORT[t].dir==="asc") SORT[t]=null; dispChanged(); return; }
  if(e.target.id==="dispReset"){ dispReset(); return; }
  if(e.target.id==="dispDone"){ closeDisp(true); } });
$("#dispMenu").addEventListener("change",e=>{ const t=shared.WT, i=e.target;
  if(i.id==="wgrp"){ if(layoutOf(t)==="board"){ WGRP[t]=i.value; store.set("creaite-workgrp",WGRP); } else { WLGRP[t]=i.value; store.set("creaite-listgrp",WLGRP); } dispChanged(); return; }
  if(i.id==="wsub"){ WSUB[t+"|"+layoutOf(t)]=i.value; store.set("creaite-worksub",WSUB); dispChanged(); return; }
  if(i.id==="wbsort"){ const v=i.value; SORT[t]=v?{col:v,dir:v==="upd"||v==="raised"||v==="date"?"desc":"asc"}:null; dispChanged(); return; }
  if(i.id==="wshowempty"){ BHIDE[t]=!i.checked; store.set("creaite-boardhide",BHIDE); dispChanged(); return; }
  if(i.id==="wclosed"){ i.value==="all"?BCLALL.add(t):BCLALL.delete(t); store.set("creaite-boardclosedall",[...BCLALL]); dispChanged(); return; }
  if(i.dataset.prop!==undefined){ const L=shared.COLVIS[t], v=i.value; i.checked?L.includes(v)||L.push(v):L.splice(L.indexOf(v),1); store.set("creaite-cols",shared.COLVIS); dispChanged(); } });
$("#dispMenu").addEventListener("keydown",e=>{ if(e.key==="Escape"){ e.preventDefault(); e.stopPropagation(); closeDisp(true); } });
document.addEventListener("click",e=>{ if(dispOpen()&&!e.target.closest(".ddisp")) closeDisp(false); });
}
/* ===== Decisions board (BL-103, sprint-debug-log-2b) =====
   The Work board's Board layout for Decisions: the same cards, columns, filters, search, saved views and sort as Actions and RAID
   (through the same functions, wrapped here), grouped by Status (Pending, Made, Withdrawn), Decision maker or Needed by. A decision has
   no milestone. A move is one change with Undo, as everywhere on the board, but a status move is the decision's own act: to Made opens
   the Record-the-decision form (the date made, today, the same record and number), to Withdrawn asks first, and a decision that is
   already made or withdrawn can't be moved (a made one never goes back to pending). */
export const DEC_NOBACK="A decision that has been made or withdrawn can't go back to pending; record a new one that replaces it";
export const decBucket=x=>{ if(x.st!=="Pending") return "decided"; if(!x.due) return "none"; if(x.due<TODAY) return "overdue"; const sun=weekSun(TODAY); return x.due<=sun?"week":x.due<=isoAdd(sun,7)?"next":"later"; };
export function decCols(L,g){ const cols=[], closedDays=+S.boardClosedDays||14;
  if(g==="status"){ const by=st=>L.filter(x=>x.st===st);
    cols.push({key:"Pending",label:"Pending",items:by("Pending"),drop:false,why:DEC_NOBACK},{key:"Made",label:"Made",items:by("Made"),drop:true,value:"Made"});
    const w=by("Withdrawn"); if(w.length) cols.push({key:"Withdrawn",label:"Withdrawn",items:w,drop:true,value:"Withdrawn"}); }
  else if(g==="owner"){ const me=[], none=[], map=new Map();
    L.forEach(x=>{ if(!x.by) none.push(x); else if(isMe(x.by)) me.push(x); else { if(!map.has(x.by)) map.set(x.by,[]); map.get(x.by).push(x); } });
    cols.push({key:"@me",label:"Me",items:me,drop:true,value:S.me});
    [...map].sort((a,b)=>b[1].length-a[1].length||a[0].localeCompare(b[0])).forEach(([n,it])=>cols.push({key:n,label:n,items:it,drop:true,value:n}));
    cols.push({key:"@none",label:"No one asked",items:none,drop:true,value:""}); }
  else { const B={overdue:[],week:[],next:[],later:[],none:[],decided:[]}; L.forEach(x=>B[decBucket(x)].push(x));
    cols.push({key:"overdue",label:"Overdue",items:B.overdue,drop:false,why:"Overdue is a date that has passed: pick a date in another column"},
      {key:"week",label:"This week",items:B.week,drop:true},{key:"next",label:"Next week",items:B.next,drop:true},{key:"later",label:"Later",items:B.later,drop:true},{key:"none",label:"No date",items:B.none,drop:true});
    if(B.decided.length){ const all=BSHOWALL.has("decisions|due|decided")||BCLALL.has("decisions"), recent=B.decided.filter(x=>!x.date||days(x.date)>=-closedDays);
      cols.push({key:"decided",label:"Decided",items:all?B.decided:recent,hidden:all?0:B.decided.length-recent.length,limited:true,drop:false,why:"A decision that has been made or withdrawn has no needed-by date"}); } }
  return {cols}; }
/* the form that records a decision opens on the same record, filled in as the panel's own button does */
export function recordFromBoard(id){ openRecord("decisions",id); if(!shared.CUR||shared.CUR.id!==id||shared.CUR.k!=="decisions") return false; pkSetStatus("decisions",id,"Made"); return true; }   /* BL-176 (sprint-peek): the peek opens with Made staged (Date made today), not a form */
export async function decBoardDrop(id,key){ const t="decisions", x=REC(t,id), g=BCUR&&BCUR.g, col=BCUR&&boardTargets(t,g).find(c=>c.key===key); if(!x||!col||!col.drop) return false;
  if(boardKeyOf(t,g,x)===key) return false;
  if(x.st!=="Pending"){ snack(`${x.id} is ${x.st.toLowerCase()}: only a pending decision can be moved`); return false; }
  const what=`${x.id} moved to ${col.label}: ${x.t.length>60?x.t.slice(0,57)+"…":x.t}`;
  if(g==="status"){
    if(key==="Made") return recordFromBoard(x.id);
    if(key==="Withdrawn"){ if(!await boardAsk({title:`Withdraw ${x.id}?`,hint:x.t,clear:true,okText:"Withdraw"})) return false; await withdrawDecision(x); return true; }
    return false; }
  if(g==="owner") return await boardMove(t,id,{by:col.value},`${x.id} now asked of ${col.label==="No one asked"?"no one":col.label}`);
  if(key==="none"){ if(!await boardAsk({title:`Clear the needed-by date of ${x.id}?`,hint:x.t,clear:true})) return false; return await boardMove(t,id,{due:""},what); }
  const d=await boardAsk({title:`Needed by, for ${x.id}`,hint:x.t,date:key==="week"?thisFriday():key==="next"?nextFriday():isoAdd(TODAY,14),range:key}); if(!d) return false;
  return await boardMove(t,id,{due:d},what); }
/* ===== BL-129 (sprint-work-views) =====
   Grouping in the List, one sub-group level, and swimlanes on the Board. One grouping function (wgGroups) serves the List's
   collapsible header rows, the Board's new columns (Project, Priority, Workstream, Type) and the swimlanes. A group header shows
   its count and the overdue count, collapses (remembered per tab and grouping), and has a tick for its visible rows. A Shift
   range never reaches a collapsed group (its rows aren't drawn); collapsing takes its rows out of the highlight and says how many.
   "Select all N matching" is the one exception: it states N, which counts collapsed groups too. On a swimlane board a card moved
   across a column and a lane states both changes and saves them as one proposal (one Undo); Move to… offers the column and the
   lane as two steps. Decisions keep their board rules (FR-110); a lane move reassigns who is asked. */
export const LCOLL=store.get("creaite-listcoll",{});
export let HLNOTE=""; shared.HLALL=false;                       /* HLALL: "Select all N matching" is in force; HLNOTE: what the bar says after a collapse */
export const grpOK=(t,g)=>groupsOf(t).some(x=>x[0]===g);
export function listGroupOf(t){ return grpOK(t,WLGRP[t])?WLGRP[t]:"none"; }
export function subOf(t,lay){ const s=WSUB[t+"|"+lay], g=lay==="board"?groupOf(t):listGroupOf(t); return g!=="none"&&grpOK(t,s)&&s!==g?s:"none"; }
export const grpLabel=(t,g)=>(groupsOf(t).find(x=>x[0]===g)||[g,g])[1];
export const grpNoun=(t,n)=>t==="actions"?`${n} action${n===1?"":"s"}`:t==="raid"?`${n} item${n===1?"":"s"}`:`${n} decision${n===1?"":"s"}`;
export const itemLate=(t,x)=>t==="actions"?overdue(x):t==="raid"?x.st==="Open"&&!!x.due&&x.due<TODAY:decLate(x);
export const ownerOf=(t,x)=>t==="decisions"?x.by:x.o;
export function wgKey(t,g,x){ if(g==="project") return x.p||""; if(g==="due") return t==="decisions"?decBucket(x):dueBucket(t,x); if(g==="status") return x.st;
  if(g==="owner"){ const o=ownerOf(t,x); return t==="decisions"?(!o?"@none":isMe(o)?"@me":o):(!o||o==="TBC"?"TBC":isMe(o)?"@me":o); }
  if(g==="milestone") return x.ms||""; if(g==="priority") return x.pr||""; if(g==="workstream") return x.ws||""; if(g==="type") return x.type||""; return ""; }
export const DUELAB={overdue:"Overdue",week:"This week",next:"Next week",later:"Later",none:"No date",closed:"Closed",decided:"Decided"};
/* the groups of L under g, in order: {key,label,items,value,settable,why}. `empty` adds the fixed values that have no items. */
export function wgGroups(t,g,L,empty){ if(t==="all"&&["type","status","priority"].includes(g)){
    const ks=g==="type"?ALL_TYPES:g==="status"?ALL_ST:[...PRIOS,""], out=ks.map(k=>({key:k,label:k||"No priority",items:L.filter(x=>wgKey(t,g,x)===k),why:"Change it on the item’s own tab"}));
    return empty?out:out.filter(x=>x.items.length); }
  const by=new Map(); L.forEach(x=>{ const k=wgKey(t,g,x); if(!by.has(k)) by.set(k,[]); by.get(k).push(x); });
  const G=(key,label,extra)=>({key,label,items:by.get(key)||[],...extra}); let out=[];
  if(g==="project"){ const ks=empty?P.map(p=>p.code):[...by.keys()]; out=[...new Set(ks)].map(k=>G(k,k?pName(k):"No project",{why:"An item's project can't be changed here"})).sort((a,b)=>a.label.localeCompare(b.label)); }
  else if(g==="due") out=(t==="decisions"?["overdue","week","next","later","none","decided"]:["overdue","week","next","later","none","closed"]).map(k=>G(k,DUELAB[k],{why:"Change a date in its cell or the panel"})).filter(x=>x.items.length||(empty&&x.key!=="closed"&&x.key!=="decided"));
  else if(g==="status") out=(t==="actions"?["Open","Delayed","Closed","Cancelled"]:t==="raid"?["Open","Closed","Cancelled"]:["Pending","Made","Withdrawn"]).map(k=>G(k,k,t==="decisions"?{why:"Record or withdraw a decision from its column or the panel"}:{settable:true,value:k}));
  else if(g==="owner"){ const me=t==="decisions"?"@me":"@me", none=t==="decisions"?"@none":"TBC";
    const rest=[...by.keys()].filter(k=>k!==me&&k!==none).sort((a,b)=>by.get(b).length-by.get(a).length||a.localeCompare(b));
    out=[G(me,"Me",{settable:true,value:S.me}),...rest.map(k=>G(k,k,{settable:true,value:k})),G(none,t==="decisions"?"No one asked":"TBC",{settable:true,value:t==="decisions"?"":"TBC"})]; }
  else if(g==="milestone"){ const ps=new Set(L.map(x=>x.p)); const ks=[...by.keys()].filter(Boolean);
    out=ks.map(k=>G(k,msLabel(k)+(ps.size>1?` (${pName((P.find(p=>(p.ms||[]).some(m=>m[3]===k))||{}).code||"")})`:""),{settable:true,value:k})).sort((a,b)=>a.label.localeCompare(b.label)); out.push(G("","No milestone",{settable:true,value:""})); }
  else if(g==="priority") out=PRIOS.map(k=>G(k,k,t==="actions"?{settable:true,value:k}:{why:"A RAID item's priority comes from its impact and likelihood: change those"}));
  else if(g==="workstream"){ out=[...by.keys()].filter(Boolean).sort((a,b)=>a.localeCompare(b)).map(k=>G(k,k,{settable:true,value:k})); out.push(G("","No workstream",{settable:true,value:""})); }
  else if(g==="type") out=["Risk","Issue","Assumption","Dependency"].map(k=>G(k,k,{settable:true,value:k}));
  return empty?out:out.filter(x=>x.items.length); }
/* what moving an item into group gr of grouping g changes, or null with gr.why */
export function wgPatch(t,g,gr){ if(!gr||!gr.settable) return null; const f={status:"st",owner:t==="decisions"?"by":"o",milestone:"ms",priority:"pr",workstream:"ws",type:"type"}[g]; return f?{[f]:gr.value}:null; }
/* the List: group header rows (and sub-group rows), then the rows. Rows carry their groups so ticks and collapse can find them. */
export function grpHead(t,gr,lvl,key,coll,n){ if(t==="all") t="raid"; const late=gr.items.filter(x=>itemLate(t,x)).length;
  return `<tr class="wgh lv${lvl}${coll?" coll":""}" data-gk="${esc(key)}"><td colspan="${n}"><button type="button" class="wgtog" data-gtog="${esc(key)}" aria-expanded="${!coll}" aria-label="${coll?"Expand":"Collapse"} ${esc(gr.label)}">${ic("chevdown","chev")}</button><input type="checkbox" class="wgtick" data-gtick="${esc(key)}" aria-label="Select the rows in ${esc(gr.label)}" ${coll||!gr.items.length?"disabled":""}> <b class="wgn">${esc(gr.label)}</b> <span class="sub">${grpNoun(t,gr.items.length)}${late?` · <span class="late">${late} overdue</span>`:""}${coll?" · collapsed":""}</span></td></tr>`; }
export function listBody(t,C,L){ const g=listGroupOf(t), row=(x,a)=>rowHtml(t,x,C,{sel:shared.SEL,tr:a}); if(g==="none"||!L.length) return L.map(x=>row(x,"")).join("");
  const sg=subOf(t,"list"); let h="";
  wgGroups(t,g,L,!BHIDE[t]).forEach(gr=>{ const k=`${t}|${g}|${gr.key}`, coll=!!LCOLL[k]; h+=grpHead(t,gr,1,k,coll,C.length); if(coll) return;
    if(sg==="none"){ h+=gr.items.map(x=>row(x,` data-g1="${esc(k)}"`)).join(""); return; }
    wgGroups(t,sg,gr.items,false).forEach(s2=>{ const k2=`${k}|${sg}|${s2.key}`, c2=!!LCOLL[k2]; h+=grpHead(t,s2,2,k2,c2,C.length); if(!c2) h+=s2.items.map(x=>row(x,` data-g1="${esc(k)}" data-g2="${esc(k2)}"`)).join(""); }); });
  return h; }
export const grpRows=k=>$$(`#workTbl tr[data-row]`).filter(r=>r.dataset.g1===k||r.dataset.g2===k);
export function grpTicks(){ $$("#workTbl .wgtick").forEach(c=>{ const rs=grpRows(c.dataset.gtick), n=rs.filter(r=>HL.has(r.dataset.row)).length; c.checked=!!rs.length&&n===rs.length; c.indeterminate=n>0&&n<rs.length; }); }
export function grpToggle(k){ const sel="#workTbl tbody tr", key=e=>e.dataset.row||("g:"+e.dataset.gk), snap=reduced()?null:mSnapRows(sel,key), open=!!LCOLL[k];
  const before=HL.size; LCOLL[k]=!LCOLL[k]; if(!LCOLL[k]) delete LCOLL[k]; store.set("creaite-listcoll",LCOLL); renderWork();   /* after "Select all N matching" the selection keeps every matching item */
  const left=before-HL.size; if(left>0){ HLNOTE=`${left} left the selection: ${left===1?"its group is":"their group is"} collapsed`; hlPaint(); snack(`${left} selected item${left===1?"":"s"} left the selection: the group is collapsed`); }
  if(!snap) return; mFlipRows(snap,sel,key,320,true); const b=$(`#workTbl [data-gtog="${CSS.escape(k)}"]`); if(b) anim(b,[{transform:`rotate(${open?-90:90}deg)`},{transform:"none"}],{duration:320,easing:"inout"}); }
/* the Board's new columns (Project, Priority, Workstream, Type) come from the same groups */
export const GENB=new Set(["project","priority","workstream","type"]);
/* the column part of a move (asking for a date where the column is a date), with what changes; null if cancelled or refused */
export async function colPatch(t,g,x,col,also){ const hint=`${x.t}${also?` · also ${also}`:""}`;
  if(t==="decisions"&&g==="status") return null;
  if(g==="due"){ if(col.key==="none"){ if(!await boardAsk({title:`Clear the ${t==="decisions"?"needed-by":"due"} date of ${x.id}?`,hint,clear:true})) return null; return {p:{due:""},asked:true}; }
    const d=await boardAsk({title:`${t==="decisions"?"Needed by":"Due date"} for ${x.id}`,hint,date:col.key==="week"?thisFriday():col.key==="next"?nextFriday():isoAdd(TODAY,14),range:col.key}); return d?{p:{due:d},asked:true}:null; }
  if(g==="status") return {p:{st:col.value}}; if(g==="owner") return {p:{[t==="decisions"?"by":"o"]:col.value}}; if(g==="milestone") return {p:{ms:col.value}};
  const p=wgPatch(t,g,{settable:col.drop,value:col.value}); return p?{p}:null; }
export async function laneDrop(id,colKey,laneKey){ const t=shared.WT, x=REC(t,id); if(!x||!BCUR||!BCUR.sub) return false; const g=BCUR.g, sg=BCUR.sub;
  const col=boardTargets(t,g).find(c=>c.key===colKey), lane=BCUR.lanes.find(l=>l.key===laneKey); if(!col||!lane) return false;
  const colCh=boardKeyOf(t,g,x)!==colKey, laneCh=wgKey(t,sg,x)!==laneKey; if(!colCh&&!laneCh) return false;
  if(t==="decisions"&&x.st!=="Pending"){ snack(`${x.id} is ${x.st.toLowerCase()}: only a pending decision can be moved`); return false; }
  const lp=laneCh?wgPatch(t,sg,lane):{}; if(!lp){ snack(lane.why||"Can't move it to that lane"); return false; }
  const laneTxt=laneCh?`${grpLabel(t,sg).toLowerCase()} → ${lane.label}`:"";
  if(!colCh) return boardMove(t,id,lp,`${x.id} moved to ${lane.label}`);
  if(!col.drop){ snack(col.why||"Can't drop there"); return false; }
  if(t==="decisions"&&g==="status"){                                            /* FR-110: Made opens the form (with the lane's person); Withdrawn asks */
    if(colKey==="Made"){ const ok=recordFromBoard(x.id); if(ok&&laneCh&&shared.CUR) pkCommit("decisions",x.id,lp,grpLabel(t,sg),"",lane.label); return ok; }   /* BL-176: the lane's change is staged beside it */
    if(colKey==="Withdrawn"){ if(laneCh){ snack("Move it to the lane first, then withdraw it"); return false; } return boardDrop(id,colKey); } return false; }
  const cp=await colPatch(t,g,x,col,laneTxt); if(!cp) return false;
  if(!cp.asked&&!await boardAsk({title:`Move ${x.id}?`,hint:`${grpLabel(t,g)} → ${col.label} · ${laneTxt}. ${x.t}`,clear:true,okText:"Move"})) return false;
  return boardMove(t,id,{...cp.p,...lp},`${x.id} moved to ${col.label} · ${lane.label}`); }
/* Move to…: the column and the lane as two steps (so dragging is never the only way, WCAG 2.5.7) */
/* ===== end BL-129 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootWork0038(){
$("#workTbl").addEventListener("click",e=>{ const tg=e.target.closest("[data-gtog]"), tk=e.target.closest("[data-gtick]"), hd=e.target.closest("tr.wgh");
  if(tk){ e.stopPropagation(); const rs=grpRows(tk.dataset.gtick); shared.HLALL=false; HLNOTE=""; if(tk.checked) rs.forEach(r=>HL.set(r.dataset.row,shared.WT)); else rs.forEach(r=>HL.delete(r.dataset.row)); hlSettle(); return; }
  if(tg||hd){ grpToggle((tg||hd).dataset.gtog||hd.dataset.gk); } });
/* "Select all N matching" (BL-124's bar): the whole filtered result, collapsed groups included, the number stated first */
document.addEventListener("click",e=>{ const b=e.target.closest("#wbulk [data-bq=all]"); if(!b) return; const L=rows(); HL.clear(); L.forEach(x=>HL.set(x.id,shared.WT)); shared.HLALL=true; HLNOTE=""; hlPaint(); });
}
/* ===== BL-130 (sprint-work-views) =====
   "+ Filter" opens a searchable field picker (F opens it too): the five main fields first, the rest under More fields, then the
   date ranges. Every field has "is" (any of the ticked values, as before) and "is not" (none of them); an excluded field's chip is
   tinted and says "not", and it is stored as "!key" in a saved view and the address, so older views and links load unchanged.
   New fields: Stale (no change for review.stale_after_days; open items only, and for a decision its last change, else its date),
   Last updated and Raised (actions and RAID; a decision has its Date), Milestone on Actions (RAID's gains the milestones themselves).
   Labels and Blocked (BL-125) join as further FDEFS entries; the picker lists whatever FDEFS holds. */
export const staleAge=(t,x)=>{ const d=(x.upd_at||"").slice(0,10)||(t==="decisions"?x.date:x.raised)||""; return d?-days(d):null; };
export const isStale=(t,x)=>{ const op=t==="actions"?open(x):t==="raid"?x.st==="Open":x.st==="Pending", a=staleAge(t,x); return op&&a!==null&&a>=(+S.staleDays||7); };
export const msOpts=()=>{ const ps=PROJF.size===1?P.filter(p=>PROJF.has(p.code)):P; return ps.flatMap(p=>(p.ms||[]).filter(m=>m[3]).map(m=>[m[3],m[0]+(ps.length>1?` (${p.name})`:"")])); };
export const lastDays=[["7","Last 7 days"],["14","Last 14 days"],["30","Last 30 days"]], within=(iso,set)=>!!iso&&[...set].some(n=>-days(iso.slice(0,10))<=+n&&-days(iso.slice(0,10))>=0);
shared.FPK=null; shared.FPQ="";
export const FPRANGES=()=>shared.WT==="decisions"?[]:[["dr","Due between"],["rr","Raised between"],["cr","Closed between"]];   /* BL-190: closed between */
/* ===== end BL-130 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootWork0039(){
Object.assign(FX,{sl:new Set(),lu:new Set(),rd:new Set()});
["actions","raid","decisions"].forEach(t=>{ const L=FDEFS[t];
  L.push(["sl","Stale",()=>[["yes",`Stale (no change for ${+S.staleDays||7} days)`],["no","Not stale"]],x=>isStale(t,x)?"yes":"no",1]);
  if(t==="decisions") return;
  L.push(["lu","Last updated",()=>lastDays,x=>x.upd_at,1,(x,set)=>within(x.upd_at,set)],["rd","Raised",()=>lastDays,x=>x.raised,1,(x,set)=>within(x.raised,set)]);
  if(t==="actions") L.push(["ms","Milestone",()=>[["none","No milestone"],...msOpts()],x=>x.ms||"none",1]);
  else { const i=L.findIndex(d=>d[0]==="ms"); L[i]=["ms","Milestone",()=>[["yes","Attached to a milestone"],["no","Not attached"],...msOpts()],x=>x.ms?"yes":"no",1,(x,set)=>set.has(x.ms?"yes":"no")||(!!x.ms&&set.has(x.ms))]; } });
}
/* ===== BL-132 (sprint-work-views) =====
   When nothing matches, the list (or board) names the filters, counts what removing each one alone would show, and offers Remove,
   Include closed items (when that would add some) and Clear all filters. The count line says what is hidden: on the List what the
   Status filter excludes, on the Board what the Closed column's window leaves out; never what another filter removes (those are the
   chips). A polite live region (#wlive) announces the count and the empty state when they change (WCAG 4.1.3). */
export const CLOSEDST={actions:["Closed","Cancelled"],raid:["Closed","Cancelled"],decisions:["Made","Withdrawn"]};
export function activeFilters(){ const out=[]; defs().forEach(d=>{ const v=[...setOf(d[0])]; if(!v.length) return; const opts=d[2](), lab=x=>(opts.find(o=>o[0]===x)||[x,x])[1];
    out.push({k:d[0],label:`${d[1]}: ${NEG.has(d[0])?"not ":""}${d[0]==="o"&&v.every(isMe)?"Me":v.map(lab).join(", ")}`}); });
  if(shared.WT!=="decisions"&&(shared.DR.from||shared.DR.to)) out.push({k:"dr",label:`Due: ${shared.DR.from?fd(shared.DR.from):"…"} to ${shared.DR.to?fd(shared.DR.to):"…"}`});
  if(shared.WT!=="decisions"&&(RR.from||RR.to)) out.push({k:"rr",label:`Raised: ${RR.from?fd(RR.from):"…"} to ${RR.to?fd(RR.to):"…"}`});
  if(shared.WT!=="decisions"&&(shared.CR.from||shared.CR.to)) out.push({k:"cr",label:`Closed: ${shared.CR.from?fd(shared.CR.from):"…"} to ${shared.CR.to?fd(shared.CR.to):"…"}`});
  if(shared.WQ.trim()) out.push({k:"q",label:`Search “${shared.WQ.trim()}”`}); return out; }
/* with the closed statuses added to the Status filter, how many would show (0 when that isn't a widening) */
export function withClosed(){ const st=FX.st, add=CLOSEDST[shared.WT].filter(v=>!st.has(v)); if(!st.size||NEG.has("st")||!add.length) return 0;
  add.forEach(v=>st.add(v)); const n=items().filter(x=>passes(x)).length; add.forEach(v=>st.delete(v)); return n; }
export function hiddenCount(){ if(layoutOf(shared.WT)==="board") return {n:BCUR&&BCUR.cols?BCUR.cols.reduce((a,c)=>a+(c.hidden||0),0):0,closed:true};
  if(!FX.st.size) return {n:0}; const out=items().filter(x=>passes(x,"st")&&!passes(x)); return {n:out.length,closed:out.every(x=>CLOSEDST[shared.WT].includes(x.st))}; }
export const itemsWord=n=>`${n} item${n===1?"":"s"}`;
export function emptyHtml(){ const F=activeFilters();
  if(!F.length) return `<div class="wempty"><h2>Nothing here yet</h2></div>`;
  const rel=F.map(f=>({...f,n:items().filter(x=>passes(x,f.k)).length})), cl=withClosed();
  const head=F.length===1&&F[0].k==="q"?`Nothing in this view matches “${esc(shared.WQ.trim())}”`:`Nothing matches ${F.length===1?"this filter":`these ${F.length} filters`}`;
  return relaxHtml(head,rel,itemsWord,cl?`<div><span>Include closed items</span><span class="sub">${itemsWord(cl)}</span><button type="button" class="btn" data-relax="closed">Show</button></div>`:"","items"); }
/* BL-264: the empty state's markup, shared by Work and Settings › People. `head` is markup; `rel` is each filter on ({k, label, n:
   what removing it alone would show}), counted in `word`; `more` is markup for further rows (Work's Include closed items), which
   also count as a way out; `noun` is what would show. */
export function relaxHtml(head,rel,word,more,noun){
  return `<div class="wempty"><h2>${head}</h2><div class="sub">${rel.some(r=>r.n)||more?`Removing one of them alone would show ${noun}:`:"Removing any one of them alone still shows nothing."}</div>
    <div class="relax">${rel.map(r=>`<div><span>Remove <b>${esc(r.label)}</b></span><span class="sub">${word(r.n)}</span><button type="button" class="btn" data-relax="${esc(r.k)}" aria-label="Remove ${esc(r.label)}, showing ${word(r.n)}">Remove</button></div>`).join("")}
    ${more}</div>
    <div class="wefoot"><button type="button" class="btn primary" data-relax="all">Clear all filters</button></div></div>`; }
export let WLIVE="";
export function workAnnounce(text){ const el=$("#wlive"); if(!el||text===WLIVE) return; WLIVE=text; el.textContent=text; }
/* ===== end BL-132 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootWork0040(){
document.addEventListener("click",e=>{ const b=e.target.closest("[data-relax]"); if(!b||!b.closest("#v-work")) return; const k=b.dataset.relax;
  if(k==="all"){ clearAllFilters(); shared.WQ=""; shared.FROMPROJ=null; snack("All filters cleared"); }
  else if(k==="closed") CLOSEDST[shared.WT].forEach(v=>FX.st.add(v));
  else if(k==="q") shared.WQ=""; else if(k==="dr") shared.DR={from:"",to:""}; else if(k==="rr") RR={from:"",to:""}; else if(k==="cr") shared.CR={from:"",to:""}; else { setOf(k).clear(); NEG.delete(k); }
  workChanged(); });
}
/* ===== BL-131 (sprint-work-views) =====
   Saved views. The view in use is remembered per tab (WB) when it is changed: its chip keeps a dot (with words for screen readers)
   and the applied row offers Update view (a saved view) and Save as new view (any view; a built-in one can't be overwritten).
   A saved view keeps its filters and its display (layout, grouping, sub-group, order); a built-in view is filters only. Each saved
   view's ▾ menu renames, moves it earlier or later, or deletes it (settings work.saved_views, in that order). The chip row never
   wraps: views that don't fit, and Overdue on Actions, sit under More views (n), and the view in use always stays in sight.
   Each tab's default view is on the Settings page (Opening views). */
export const WB={};                                     /* the view each tab's current state came from */
export function viewState(){ return {f:snapshot(),lay:layoutOf(shared.WT),g:groupOf(shared.WT),o:SORT[shared.WT]||null,lg:listGroupOf(shared.WT),sg:subOf(shared.WT,"board"),lsg:subOf(shared.WT,"list")}; }
export function viewMatches(v,snap){ if(!sameF(snap,v.f)) return false; if(v.builtin) return true;
  const c=viewState(), lay=v.lay||"list"; if(v.lay&&v.lay!==c.lay) return false;
  if(lay==="board"){ if(v.g&&v.g!==c.g) return false; if("sg" in v&&(v.sg||"none")!==c.sg) return false; }
  else { if("lg" in v&&(v.lg||"none")!==c.lg) return false; if("lsg" in v&&(v.lsg||"none")!==c.lsg) return false; }
  return !("o" in v)||JSON.stringify(v.o||null)===JSON.stringify(c.o); }
export function viewSaveBtns(){ const b=allViews(shared.WT).find(v=>v.id===WB[shared.WT]);
  return `${b&&!b.builtin?`<button class="linkbtn" id="updView" title="Save these filters and this display into “${esc(b.label)}”">Update view</button>`:""}<button class="linkbtn" id="saveView">${b?"Save as new view":"Save view"}</button>`; }
export let VRENAME=null;                                 /* the saved view being renamed */
export const VMORE={views:[]};                           /* the views under More views, as last drawn */
/* BL-316: More views is the Menu block's menu, opened from its chip */
export function moreViewsMenu(b){ if(menuOpenFor(b)){ closeMenu(); return; }
  openMenu(b,{label:"More views",id:"vmoreMenu",onPick:id=>{ applyView(id); renderWork(); navWrite(false); },items:VMORE.views.map(v=>({id:v.id,name:v.label,cls:"vmitem",data:{wv:v.id}}))}); }
/* the views bar (BL-316): toggle buttons (aria-pressed) that choose the list's view, each with its own
   menu, renaming in place and More views; not Chips (a Chip is a labelled value) and not tabs (no panels), so it stays its own */
export function renderViewBar(){ const el=$("#wviews"), V=allViews(shared.WT), dirty=!shared.WVIEW&&!!WB[shared.WT], act=shared.WVIEW||WB[shared.WT];
  const chip=v=>{ const on=v.id===act, dot=dirty&&on;
    if(VRENAME&&v.id==="saved:"+VRENAME) return `<span class="vwrap vren"><input id="vrename" value="${esc(v.label)}" aria-label="New name for the ${esc(v.label)} view"><button class="mini ok" type="button" data-vren="save">Save</button><button class="mini" type="button" data-vren="cancel">Cancel</button></span>`;
    return `<span class="vwrap"><button class="vchip${dot?" dirty":""}" data-wv="${esc(v.id)}" aria-pressed="${on}"${dot?' title="Changed since it was opened: Update view or Save as new view"':""}>${esc(v.label)}${dot?'<span class="vdot" aria-hidden="true">●</span><span class="vh"> (changed, not saved)</span>':""}</button>${v.builtin?"":`<button class="vmenu" type="button" data-vmenu="${esc(v.label)}" aria-haspopup="menu" aria-expanded="false" aria-label="Options for the ${esc(v.label)} view" title="Rename, move or delete">▾</button>`}</span>`; };
  let row=V.filter(v=>!v.more||v.id===act), more=V.filter(v=>v.more&&v.id!==act); VMORE.views=more;
  const draw=()=>{ putHTML(el,raw(row.map(chip).join("")+(!shared.WVIEW&&!WB[shared.WT]?'<span class="vchip custom" aria-pressed="true">Custom</span>':"")
    +(more.length?`<span class="dd vmorewrap"><button class="vchip" type="button" id="vmore" aria-haspopup="menu" aria-expanded="false">More views (${more.length}) ▾</button></span>`:""))); };
  draw(); if(!el.offsetParent) return;
  for(let n=0;n<40&&el.scrollWidth>el.clientWidth+1;n++){ const i=row.map(v=>v.id!==act&&!(VRENAME&&v.id==="saved:"+VRENAME)).lastIndexOf(true); if(i<0) break; more.unshift(row.splice(i,1)[0]); draw(); } }
export async function updateView(){ const b=allViews(shared.WT).find(v=>v.id===WB[shared.WT]); if(!b||b.builtin) return; const before=shared.SAVED[shared.WT], i=before.findIndex(v=>v.name===b.label); if(i<0) return;
  shared.SAVED[shared.WT]=before.map((v,j)=>j===i?{...v,...viewState(),name:v.name}:v); if(await writeSettings({"work.saved_views":shared.SAVED})){ shared.WVIEW=WB[shared.WT]=b.id; renderWork(); navWrite(false); snack(`View “${b.label}” updated`); } else shared.SAVED[shared.WT]=before; }
export async function moveView(name,d){ const L=[...(shared.SAVED[shared.WT]||[])], i=L.findIndex(v=>v.name===name), j=i+d; if(i<0||j<0||j>=L.length) return; [L[i],L[j]]=[L[j],L[i]]; const before=shared.SAVED[shared.WT]; shared.SAVED[shared.WT]=L;
  if(await writeSettings({"work.saved_views":shared.SAVED})){ renderWork(); snack(`“${name}” moved ${d<0?"earlier":"later"}`,()=>moveView(name,-d)); $(`#wviews [data-vmenu="${CSS.escape(name)}"]`)?.focus(); } else shared.SAVED[shared.WT]=before; }
export async function renameView(old,name){ name=String(name||"").trim().replace(/[<>"]/g,""); if(!name){ snack("Name the view first"); return; } if(name===old){ VRENAME=null; renderWork(); return; }
  if(allViews(shared.WT).some(v=>v.label.toLowerCase()===name.toLowerCase()&&v.label!==old)){ snack(`There's already a view called “${name}”`); return; }
  const before=shared.SAVED[shared.WT]; shared.SAVED[shared.WT]=before.map(v=>v.name===old?{...v,name}:v); const ch={"work.saved_views":shared.SAVED}, dk={actions:"defActionView",raid:"defRaidView",decisions:"defDecisionView"}[shared.WT];
  if(S[dk]==="saved:"+old) ch[SKEY[dk]]="saved:"+name;                                          /* the default view follows its new name */
  if(await writeSettings(ch)){ if(ch[SKEY[dk]]) S[dk]="saved:"+name; if(shared.WVIEW==="saved:"+old) shared.WVIEW="saved:"+name; if(WB[shared.WT]==="saved:"+old) WB[shared.WT]="saved:"+name; VRENAME=null; renderWork(); navWrite(false); snack(`View renamed “${name}”`,()=>renameView(name,old)); $(`#wviews [data-wv="saved:${CSS.escape(name)}"]`)?.focus(); }
  else shared.SAVED[shared.WT]=before; }
/* BL-316: a saved view's ▾ opens the Menu block's menu */
export function savedViewMenu(btn,name){ if(menuOpenFor(btn)){ closeMenu(); return; } const L=shared.SAVED[shared.WT]||[], i=L.findIndex(v=>v.name===name);
  openMenu(btn,{label:`The ${name} view`,id:"vmenuPop",items:[{id:"rename",name:"Rename",data:{vm:"rename"}},{id:"up",name:"Move earlier",disabled:i<=0,data:{vm:"up"}},
      {id:"down",name:"Move later",disabled:i>=L.length-1,data:{vm:"down"}},{id:"delete",name:"Delete",data:{vm:"delete"}}],
    onPick:a=>{ if(a==="rename"){ VRENAME=name; renderWork(); const inp=$("#vrename"); inp&&(inp.focus(),inp.select()); } else if(a==="up") moveView(name,-1); else if(a==="down") moveView(name,1); else deleteView(name); }}); }
/* ===== end BL-131 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootWork0041(){
$("#wviews").addEventListener("click",e=>{ const m=e.target.closest("[data-vmenu]"); if(m){ e.stopPropagation(); savedViewMenu(m,m.dataset.vmenu); return; }
  if(e.target.closest("#vmore")){ e.stopPropagation(); moreViewsMenu($("#vmore")); return; }
  const r=e.target.closest("[data-vren]"); if(r){ e.stopPropagation(); if(r.dataset.vren==="save") renameView(VRENAME,$("#vrename").value); else { VRENAME=null; renderWork(); } } });
$("#wviews").addEventListener("keydown",e=>{ if(e.target.id==="vrename"){ if(e.key==="Enter"){ e.preventDefault(); renameView(VRENAME,e.target.value); } if(e.key==="Escape"){ e.preventDefault(); e.stopPropagation(); const n=VRENAME; VRENAME=null; renderWork(); $(`#wviews [data-vmenu="${CSS.escape(n)}"]`)?.focus(); } } });
$("#wapplied").addEventListener("click",e=>{ if(e.target.id==="updView") updateView(); });
window.addEventListener("resize",()=>{ if(shared.VIEW==="work") renderViewBar(); });
}
/* ===== Person rows (BL-68) ===== */
/* A person's open work is the Work lists' own rows: rows(), cell() and orderedCols() with the item type, so a change
   to one changes both. Grouped by project; an Actions table and a Risks and issues table under each, without the Owner
   column (the person owns every row). Columns, their order and widths are Work's, per type. Sorting is the page's own. */
export const PRS={};   /* sort per type on a person's page; null is the default order: overdue first, then by due date */
export const personTbl=(t,L,label,pick)=>{ const C=orderedCols(t).filter(c=>c[0]!=="o"), s=PRS[t]||null, R=rows(t,L.slice(),s,t==="decisions"?DEFSORT.decisions:dueSort);
  return `${label?`<div class="pptype">${label} <span>· ${L.length}</span></div>`:""}<div class="tbl"><table class="ptbl" data-t="${t}">${rowHead(t,C,s,{fixed:1,rz:1,pick})}<tbody>${R.map(x=>rowHtml(t,x,C,{sel:shared.SEL,pick,tr:` data-k="${t}"`})).join("")}</tbody></table></div>`; };
export function personWork(x,codes){ const pick=shared.HAND&&shared.HAND.name===x.name?shared.HAND.picked:null;
  return codes.map(c=>{ const a=x.oa.filter(i=>i.p===c), r=x.or.filter(i=>i.p===c);
    return `<div class="pph">${pLink(c)}</div>${a.length?personTbl("actions",a,"Actions",pick):""}${r.length?personTbl("raid",r,"Risks and issues",pick):""}`; }).join(""); }
export const ownerNames=L=>[...new Set(L.map(i=>i.o).filter(Boolean))];
export const personLinks=x=>`<div class="pplinks">${x.oa.length?'<a href="#" data-seeall="actions">See all actions in Work ›</a>':""}${x.or.length?'<a href="#" data-seeall="raid">See all risks and issues in Work ›</a>':""}</div>`;
/* Work, filtered to this person: every spelling of their name that owns an item, open items only */
export function seeAllInWork(t){ const x=PERS().find(y=>y.name===shared.PERSON); if(!x||navBlocked(()=>seeAllInWork(t))) return;
  clearAllFilters(); shared.WT=t; applyView("open"); applyFilters({st:t==="actions"?["Open","Delayed"]:["Open"],o:ownerNames(t==="actions"?x.oa:x.or)}); syncView(); shared.WQ=""; shared.SEL=null; go("work"); }
export function personFlags(el){ el.querySelectorAll("table.ptbl tr[data-row]").forEach(tr=>{ const td=tr.querySelector("td.title"); if(td&&!td.querySelector(".wflag")) addHTML(td,"afterbegin",raw(wflag(tr.dataset.k,tr.dataset.row))); }); }
export function personRedraw(){ const to=$("#handTo")?.value; renderPerson(shared.PERSON); if(to) $("#handTo").value=to; }
   /* BL-122 */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootWork0130(){
$("#v-person").addEventListener("click",e=>{ if(shared.HAND&&e.target.closest("tr[data-row]")) return;
  const sa=e.target.closest("[data-seeall]"); if(sa){ e.preventDefault(); seeAllInWork(sa.dataset.seeall); return; }
  const th=e.target.closest("table.ptbl th[data-col]"); if(th){ const t=th.closest("table").dataset.t, col=th.dataset.col, s=PRS[t]; PRS[t]=!s||s.col!==col?{col,dir:"asc"}:s.dir==="asc"?{col,dir:"desc"}:null; personRedraw(); return; }
  const tr=e.target.closest("table.ptbl tr[data-row]"); if(tr) hlRowClick(e,tr.dataset.k,tr); });
$("#v-person").addEventListener("dblclick",e=>{ if(shared.HAND) return; const tr=e.target.closest("table.ptbl tr[data-row]"); if(tr) hlRowOpen(e,tr.dataset.k,tr); });
$("#v-person").addEventListener("mousedown",e=>{ if(e.shiftKey&&!shared.HAND&&e.target.closest("table.ptbl tr[data-row]")) e.preventDefault(); });
document.addEventListener("keydown",e=>{ if(shared.VIEW!=="person"||shared.HAND||typing()||e.metaKey||e.ctrlKey||e.altKey||(e.key!=="j"&&e.key!=="k")) return;   /* as in Work: j and k step through the rows */
  const trs=$$("#v-person table.ptbl tr[data-row]"); if(!trs.length) return; const i=trs.findIndex(tr=>tr.dataset.row===shared.SEL), tr=trs[e.key==="j"?Math.min(i+1,trs.length-1):Math.max(i-1,0)];
  openRecord(tr.dataset.k,tr.dataset.row); tr.scrollIntoView({block:"nearest"}); });
}
/* ===== BL-122 (sprint-polish) =====
   Selecting and opening in the Work lists (table and board), a person's page and Review. A click on a row highlights it, and only
   it; Cmd/Ctrl-click adds or removes a row; Shift-click highlights the range from the last row clicked (with Cmd/Ctrl it adds the
   range). The ID, a double-click or Enter opens the sidebar. J and K move the cursor (and the sidebar follows when it is already
   open), Shift extends, Space toggles, Esc clears the highlight and then closes the sidebar. The highlight is not the open record
   (that keeps `.sel`); two or more highlighted close the sidebar and BL-124's bar takes over. A view setting only: nothing is saved. */
export const HL=new Map(); shared.HLA=null; shared.HLC=null;     /* highlighted items (id → type), the anchor of a Shift range, the cursor */
export const hlOrder=()=>shared.VIEW==="activity"?$$("#actTbl tr[data-row]").map(e=>({id:e.dataset.row,k:"act"})):shared.VIEW==="person"?$$("#v-person table.ptbl tr[data-row]").map(e=>({id:e.dataset.row,k:e.dataset.k})):
  layoutOf(shared.WT)==="board"?$$("#workBoard .bcard[data-row]").map(e=>({id:e.dataset.row,k:shared.WT})):$$("#workTbl tr[data-row]").map(e=>({id:e.dataset.row,k:shared.WT}));
shared.MKEYHELD=false;   /* BL-263 (36): declared before hlPaint, which runs at load */
export const HLTICK=new Set();   /* BL-263: the rows whose tick was drawn */
export function hlPaint(){ const paint=()=>{ $$("#workTbl tr[data-row],#v-person table.ptbl tr[data-row],#workBoard .bcard[data-row]").forEach(el=>{ const on=HL.has(el.dataset.row);
    el.classList.toggle("hl",on); el.classList.toggle("cur",el.dataset.row===shared.HLC); el.setAttribute("aria-selected",String(on)); });
  $$("#workTbl .cebtn").forEach(b=>{ if(!b.matches(":focus")) b.tabIndex=b.closest("tr").dataset.row===shared.HLC?0:-1; });
  $("#workTbl").setAttribute("role","grid"); $("#workTbl").setAttribute("aria-multiselectable","true"); hlBar(); grpTicks(); };
  if(shared.LOADING){ paint(); return; }   /* BL-231: as when the address was restored at load */
  const changed=$$("#workTbl tr[data-row],#v-person table.ptbl tr[data-row],#workBoard .bcard[data-row]").filter(e=>e.classList.contains("hl")!==HL.has(e.dataset.row)||e.classList.contains("cur")!==(e.dataset.row===shared.HLC)).length; mNoFade(()=>mTick("#workTbl tr[data-row],#v-person table.ptbl tr[data-row],#workBoard .bcard[data-row]",e=>e.dataset.row,HLTICK,paint),changed); }
export function hlClear(){ shared.HLALL=false; HLNOTE=""; if(!HL.size&&shared.HLC==null) return; HL.clear(); shared.HLA=shared.HLC=null; hlPaint(); }
export function hlOnly(k,id){ shared.HLALL=false; HLNOTE=""; HL.clear(); HL.set(id,k); shared.HLA=shared.HLC=id; hlPaint(); }
export function hlToggle(k,id){ HL.has(id)?HL.delete(id):HL.set(id,k); shared.HLA=shared.HLC=id; hlSettle(); }
export function hlPick(e,k,id){ shared.HLALL=false; HLNOTE=""; const mod=e.metaKey||e.ctrlKey, order=hlOrder(), ai=shared.HLA==null?-1:order.findIndex(o=>o.id===shared.HLA);
  if(e.shiftKey&&ai>=0){ const bi=order.findIndex(o=>o.id===id); if(bi>=0){ if(!mod) HL.clear(); order.slice(Math.min(ai,bi),Math.max(ai,bi)+1).forEach(o=>HL.set(o.id,o.k)); } }
  else if(mod){ HL.has(id)?HL.delete(id):HL.set(id,k); shared.HLA=id; }
  else { HL.clear(); HL.set(id,k); shared.HLA=id; }
  shared.HLC=id; hlSettle(); }
export function hlSettle(){ if(HL.size>=2&&shared.CUR&&shared.CUR.mode==="record"&&$("#panel").classList.contains("on")&&!shared.EDITING) closePanel(); hlPaint(); }
export function hlPrune(){ if(shared.HLALL&&shared.VIEW==="work"){ const ok=new Set(rows().map(x=>x.id)); [...HL.keys()].forEach(id=>{ if(!ok.has(id)) HL.delete(id); }); if(HL.size<2) shared.HLALL=false; hlPaint(); return; }
  if(shared.VIEW!=="work"&&shared.VIEW!=="person"){ HL.clear(); shared.HLA=shared.HLC=null; return; }
  const vis=new Set(hlOrder().map(o=>o.id)); [...HL.keys()].forEach(id=>{ if(!vis.has(id)) HL.delete(id); }); if(shared.HLA!=null&&!vis.has(shared.HLA)) shared.HLA=null; if(shared.HLC!=null&&!vis.has(shared.HLC)) shared.HLC=null; hlPaint(); }
export function hlRowClick(e,k,el){ const follow=pkFollowable(e), was=document.activeElement;
  (()=>{ const id=el.dataset.row, onId=e.target.closest(".rowid,td.idc,.bid");
  if(!onId&&e.target.closest("a,button,input,select,textarea,label,[data-proj],[data-person],[role=link],.wflag")) return;     /* a link or a control in the row does its own job */
  if(onId&&!e.metaKey&&!e.ctrlKey&&!e.shiftKey){ e.preventDefault(); hlOnly(k,id); openRecord(k,id); return; }
  hlPick(e,k,id); })();
    const id=el.dataset.row; if(!follow||!id||(shared.CUR&&shared.CUR.mode==="record"&&shared.CUR.id===id)) return;
    if(e.target.closest(".rowid,td.idc,.bid")) return;              /* the ID opened it already */
    if(e.target.closest("a,button,input,select,textarea,label,[data-proj],[data-person],[role=link],.wflag")) return;
    if(!HL.has(id)||HL.size!==1) return;
    pkKeepFocus(was,()=>openRecord(k,id)); return; }
export function hlRowOpen(e,k,el,field=true){ if(e.target.closest("a:not(.rowid),button,input,select,textarea,label,[data-proj],[data-person],[role=link]")) return; const id=el.dataset.row, td=e.target.closest("td[data-f]");
  hlOnly(k,id); openRecord(k,id,field&&td?td.dataset.f:undefined); }
export function hlKey(e){ if(e.shiftKey&&!/^[JK]$/.test(e.key)||e.altKey) return false;
  const a=document.activeElement; if(a&&a!==document.body&&/^(A|BUTTON|SUMMARY)$/.test(a.tagName)&&(e.key==="Enter"||e.key===" ")) return false;
  const order=hlOrder(); if(!order.length) return false; const i=order.findIndex(o=>o.id===(shared.HLC??shared.SEL)), key=e.key.toLowerCase();
  const onBoard=layoutOf(shared.WT)==="board"&&shared.VIEW==="work";
  if(key==="j"||key==="k"){ const n=Math.max(0,Math.min(order.length-1,(i<0?(key==="j"?-1:order.length):i)+(key==="j"?1:-1))), o=order[n];
    if(e.shiftKey){ if(shared.HLA==null||!order.some(x=>x.id===shared.HLA)) shared.HLA=(order[Math.max(i,0)]||o).id; const a2=order.findIndex(x=>x.id===shared.HLA); HL.clear(); order.slice(Math.min(a2,n),Math.max(a2,n)+1).forEach(x=>HL.set(x.id,x.k)); shared.HLC=o.id; hlSettle(); }
    else { HL.clear(); HL.set(o.id,o.k); shared.HLA=shared.HLC=o.id; if(shared.CUR&&shared.CUR.mode==="record"&&$("#panel").classList.contains("on")&&!shared.EDITING) openRecord(o.k,o.id); hlPaint(); }
    const el=$$(onBoard?"#workBoard .bcard[data-row]":shared.VIEW==="person"?"#v-person table.ptbl tr[data-row]":"#workTbl tr[data-row]")[n]; el&&el.scrollIntoView({block:"nearest"}); e.preventDefault(); return true; }
  if(e.key===" "&&i>=0&&!onBoard){ e.preventDefault(); hlToggle(order[i].k,order[i].id); return true; }
  if(e.key==="Enter"&&i>=0&&!(shared.CUR&&$("#panel").classList.contains("on"))){ e.preventDefault(); const o=order[i]; hlOnly(o.k,o.id); openRecord(o.k,o.id); return true; }   /* BL-176: E retired with the Edit button */
  return false; }
/* Review (BL-122): the same rules over the rows of #reviewBody. A highlighted row that may be ticked (not individual-approval) is ticked too. */
export const RVTICK=new Set();   /* BL-263: the rows whose tick was drawn */
export function rvPaint(){ const paint=()=>{ $$("#reviewBody tr[data-n]").forEach(tr=>{ const n=+tr.dataset.n, on=RHL.has(n), r=REV.find(x=>x.n===n); tr.classList.toggle("hl",on); tr.setAttribute("aria-selected",String(on));
    tr.classList.toggle("sel",+tr.dataset.ri===shared.RSEL); const cb=tr.querySelector("input[type=checkbox]"); if(cb&&!cb.disabled&&r&&!isMin(r)) cb.checked=RHL.has(n); });
  rvSyncChk(); rvBar(); };
  if(shared.LOADING){ paint(); return; }   /* BL-231: as when the address was restored at load */
  const changed=$$("#reviewBody tr[data-n]").filter(e=>e.classList.contains("hl")!==RHL.has(+e.dataset.n)||e.classList.contains("sel")!==(+e.dataset.ri===shared.RSEL)).length; mNoFade(()=>mTick("#reviewBody tr[data-n]",e=>e.dataset.n,RVTICK,paint),changed); }   /* BL-133: the bar replaces the two buttons */
export const rvOrder=()=>$$("#reviewBody tr[data-n]").map(t=>+t.dataset.n);
export function rvTick(n){ const r=REV.find(x=>x.n===n); if(r&&rvBulkOK(r)) CHK.add(n); }
export function rvOnly(n){ RHL.clear(); CHK.clear(); RHL.add(n); rvTick(n); shared.RVA=n; }
shared.RVA=null;                                        /* the anchor of a Shift range */
export function rvPick(e,n){ const mod=e.metaKey||e.ctrlKey, order=rvOrder(), ai=shared.RVA==null?-1:order.indexOf(shared.RVA);
  if(e.shiftKey&&ai>=0){ const bi=order.indexOf(n); if(!mod){ RHL.clear(); CHK.clear(); } order.slice(Math.min(ai,bi),Math.max(ai,bi)+1).forEach(x=>{ RHL.add(x); rvTick(x); }); }
  else if(mod){ if(RHL.has(n)){ RHL.delete(n); CHK.delete(n); } else { RHL.add(n); rvTick(n); } shared.RVA=n; }
  else rvOnly(n); }
/* ===== end BL-122 ===== */
/* ===== BL-123 (sprint-polish) =====
   Edit any field in the Work table in place. A click on an editable value (or its ▾ button, or Enter on the button) opens that field's
   control where the value is: a list for status, owner (the people register, with TBC), priority, type, impact and likelihood,
   workstream (the project's own), a calendar for a date. Choosing a value saves it; Esc, or clicking away, leaves it as it was.
   The controls come from the same field definitions as the sidebar (`fieldsFor`), and the save is the board's (`boardMove`): the
   same checks, one proposal, Undo in the message, a line in Activity. A RAID item's priority is worked out from its impact and
   likelihood, so its cell edits those two. Free text, the ID and the project stay in the sidebar. A decision's status is changed
   only while pending, and Made opens the form that records it, as on the board. */
export const CE_FIELDS={actions:["st","o","due","pr","ws","ms"],raid:["st","o","type","imp","due","ws","ms"],decisions:["st","by","date"]};   /* ms: BL-128 gave Milestone a column */
export const CE_LABEL={st:"status",o:"owner",by:"made by",due:"due date",date:"date",pr:"priority",imp:"priority",ws:"workstream",type:"type",ms:"milestone"};
shared.CE=null;        /* the editor open: {k, id, f, td, html} */
export function ceEditable(k,x,f){ if(!x||!(CE_FIELDS[k]||[]).includes(f)) return false;
  if(k==="decisions"){ if(f==="st") return x.st==="Pending"; if(f==="date") return x.st==="Made"; return x.st!=="Withdrawn"; }
  return true; }
export function ceDecorate(){ if(shared.VIEW!=="work"||layoutOf(shared.WT)==="board") return;
  $$("#workTbl tr[data-row]").forEach(tr=>{ const x=REC(shared.WT,tr.dataset.row); tr.querySelectorAll("td[data-f]").forEach(td=>{ const f=td.dataset.f; if(!ceEditable(shared.WT,x,f)||td.querySelector(".cebtn")) return;
      td.classList.add("ce"); const btn=`<button type="button" class="cebtn" data-ce="${f}" tabindex="-1" aria-haspopup="listbox" aria-label="Change the ${CE_LABEL[f]} of ${esc(x.id)}" title="Change the ${CE_LABEL[f]}">▾</button>`;
      /* ===== BL-251 (fix-due-button) ===== the ▾ sits on the value's line, directly after it: before the cell's first sub-line
         (a due cell's "3 days late", "In 2 days", "Made") when it has one, else at the end. */
      const sub=td.querySelector(":scope > .x"); addHTML((sub||td),sub?"beforebegin":"beforeend",raw(btn));
      /* ===== end BL-251 ===== */ }); });
  hlPaint(); }
export const ceOpts=o=>(o||[]).map(v=>Array.isArray(v)?v:[v,v]);
export function ceSelect(label,opts,cur,attr=""){ const L=ceOpts(opts); if(cur!=null&&!L.some(o=>o[0]===cur)) L.push([cur,cur||"None"]);
  return `<select class="ceedit" aria-label="${esc(label)}" ${attr}>${L.map(o=>`<option value="${esc(o[0])}" ${o[0]===cur?"selected":""}>${esc(o[1])}</option>`).join("")}</select>`; }
export function ceControl(k,x,f){ const F=fieldsFor(k,x), def=n=>F.find(e=>e[0]===n)||[], lab=`${CE_LABEL[f]} of ${x.id}`;
  if(f==="imp") return `<span class="ceset">${ceSelect("Impact of "+x.id,def("imp")[3],x.imp,'data-cf="imp"')}${ceSelect("Likelihood of "+x.id,def("lik")[3],x.lik,'data-cf="lik"')}</span>`;
  if(f==="o"||f==="by") return ceSelect(lab,["TBC",...peopleAll()],(k==="decisions"?x.by:x.o)||"TBC",`data-cf="${f}"`);
  if(f==="ws") return ceSelect(lab,[["","None"],...wsFor(x.p).map(w=>[w,w])],x.ws||"",'data-cf="ws"');
  if(f==="ms") return ceSelect(lab,msChoices(x.p,x.ms||""),x.ms||"",'data-cf="ms"');                        /* BL-128 (sprint-work-views) */
  if(f==="date"||f==="due") return `<span class="dwrap ceedit"><input type="text" id="ceDate" data-pick="1" data-date="1" data-cf="${f}" value="${esc(x[f]?fd(x[f]):"")}" placeholder="DD-MM-YYYY" autocomplete="off" aria-label="${esc(lab)}"><button type="button" class="dbtn" data-cal="ceDate" aria-label="Choose date">${CALI}</button></span>`;
  if(k==="decisions"&&f==="st") return ceSelect(lab,[["Pending","Pending"],["Made","Made (record it)"],["Withdrawn","Withdrawn"]],"Pending",'data-cf="st"');
  return ceSelect(lab,def(f)[3],x[f],`data-cf="${f}"`); }
export function ceOpen(td){ const tr=td.closest("tr[data-row]"), id=tr.dataset.row, x=REC(shared.WT,id), f=td.dataset.f; if(!x||!ceEditable(shared.WT,x,f)) return;   /* BL-178's version (milestones' sprint), folded in by BL-231 step 2b */
  if(shared.CE) ceClose(true);
  shared.CE={k:shared.WT,id,f,td,html:td.innerHTML}; td.classList.add("editing"); putHTML(td,raw(ceControl(shared.WT,x,f)));
  td.querySelectorAll("select.ceedit").forEach(s=>{ s.size=Math.max(2,Math.min(8,s.options.length)); s.classList.add("celist"); });
  ceListPlace();
  const first=td.querySelector("select,input"); if(first) first.focus(); }
export function ceClose(restore){ if(!shared.CE) return; const {td,html}=shared.CE; shared.CE=null; closeCal(); if(restore&&td.isConnected){ td.classList.remove("editing"); putHTML(td,raw(html)); } }
export async function ceApply(k,ids,patch){ const id=ids[0], x=REC(k,id);
  if(HL.size>=2&&HL.has(id)){ const diff=Object.fromEntries(Object.entries(patch).filter(([n,v])=>String(x[n]??"")!==String(v??""))), f=Object.keys(diff)[0];     /* BL-124: the whole highlight */
    if(!f){ return false; } return await batchMove(k,[...HL.keys()],diff,bkWhat(f,diff[f])); }
  return await boardMove(k,id,patch); }
export async function ceCommit(patch){ if(shared.CE&&patch&&patch.due&&!WK.ok){ const td=shared.CE.td; if(wkAsk(patch.due,td.querySelector(".dwrap")||td,v=>ceCommit({...patch,due:v}))) return; }
  if(!shared.CE) return; const {k,id,f}=shared.CE; ceClose(false);
  if(k==="decisions"&&f==="st"){ const x=REC(k,id); if(patch.st==="Made") recordFromBoard(id); else if(patch.st==="Withdrawn"){ if(await boardAsk({title:`Withdraw ${id}?`,hint:x.t,clear:true,okText:"Withdraw"})) await withdrawDecision(x); } renderWork(); return; }
  const ok=await ceApply(k,[id],patch); if(!ok) renderWork(); }
export function ceRead(){ if(!shared.CE) return null; const out={}; let bad="";
  shared.CE.td.querySelectorAll("[data-cf]").forEach(el=>{ const n=el.dataset.cf; let v=el.value.trim();
    if(el.dataset.date){ if(v===""){ out[n]=null; return; } const t=DDATE.test(v)?toIso(v):"", d=t?new Date(t+"T12:00:00"):null;
      if(!d||isNaN(d)||d.toISOString().slice(0,10)!==t){ bad=DDATE.test(v)?"That isn't a real date.":"Not a date creaite knows. "+DATE_HELP; return; } v=t; }
    out[n]=v; });
  if(bad){ snack(bad); return null; } return out; }
export function ceClick(e,tr){ const td=e.target.closest("td.ce"); if(!td) return false;
  if(e.target.closest(".ceedit,.cal")) return true;                                        /* inside the open editor */
  if(e.target.closest("a")) return false;                                                  /* the owner's link goes to their page */
  const id=tr.dataset.row, mod=e.metaKey||e.ctrlKey||e.shiftKey;
  if(mod){ hlPick(e,shared.WT,id); return true; }                                                 /* with a key it selects and opens nothing */
  if(!(HL.has(id)&&HL.size>=2)) hlOnly(shared.WT,id);                                             /* a click on a value also highlights its row (a highlighted group stays) */
  e.preventDefault(); ceOpen(td); return true; }
     /* the calendar sets the value and fires a plain input event; typing fires an InputEvent */
/* ===== end BL-123 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootWork0132(){
document.addEventListener("change",e=>{ if(!shared.CE||!e.target.matches||!e.target.matches("#workTbl select[data-cf]")) return; const sets=shared.CE.td.querySelectorAll("select[data-cf]"); const p=ceRead(); if(p) ceCommit(p); });
document.addEventListener("input",e=>{ if(shared.CE&&e.target.id==="ceDate"&&!(e instanceof InputEvent)){ const p=ceRead(); if(p) ceCommit(p); } });
document.addEventListener("keydown",e=>{ if(!shared.CE) return; const inEd=e.target.closest&&e.target.closest("#workTbl td.editing, .cal");
  if(e.key==="Escape"){ e.preventDefault(); e.stopPropagation(); const td=shared.CE.td; closeCal(); ceClose(true); const b=td.querySelector(".cebtn"); b&&b.focus(); return; }
  if(inEd&&e.key==="Enter"&&e.target.id==="ceDate"){ e.preventDefault(); const p=ceRead(); if(p) ceCommit(p); return; }
  if(inEd&&e.key==="Tab"){ const td=shared.CE.td; ceClose(true); const btns=$$("#workTbl tr[data-row] .cebtn"), i=btns.indexOf(td.querySelector(".cebtn"));
    const next=btns[i+(e.shiftKey?-1:1)]; if(next){ e.preventDefault(); next.tabIndex=0; next.focus(); } } },true);
document.addEventListener("focusout",e=>{ if(!shared.CE||!shared.CE.td.contains(e.target)) return; const to=e.relatedTarget; if(to&&(shared.CE.td.contains(to)||(to.closest&&to.closest(".cal")))) return;
  setTimeout(()=>{ if(shared.CE&&!shared.CE.td.contains(document.activeElement)&&!document.querySelector(".cal")) ceClose(true); },120); });
}
/* ===== BL-124 (sprint-polish) =====
   Change several selected items at once. With two or more rows highlighted (BL-122) a bar appears above the list or the board:
   "3 selected", Close and Reopen, and the fields that can be changed together as the same lists and picker as BL-123. A field that
   doesn't apply to every selected item isn't offered, and says why on hover; workstream and milestone belong to one project, so
   they are offered only when every item is in the same one. The change is checked item by item (`prepMove`: the sidebar's own
   checks); items that can't take it are left out and named in the message, the others change, and nothing is saved unless at least
   one can. It is one proposal, so one Undo and one apply; Activity gets a line for each item. A long batch (over 25) asks first.
   Editing a cell of a highlighted row (BL-123) changes that field for every highlighted row. Closing or reassigning many asks
   nothing more, because Undo is one click; deleting is not offered. The Review bulk rule is separate and unchanged. */
export const BULK_MAX=25;
export const BK_STATUS={actions:["Open","Delayed","Closed","Cancelled"],raid:["Open","Closed","Cancelled"]};
export const bkItems=()=>[...HL.entries()].map(([id,k])=>({k,id,x:REC(k,id)})).filter(o=>o.x);
/* the sidebar's checks for one item: returns {f} ready to save, or {err} */
export function prepMove(k,x,patch,owner){ const f={...patch};
  for(const n of ["o","by"]) if(n in f&&f[n]&&f[n]!=="TBC") f[n]=owner;
  if("st" in f&&k!=="decisions") f.closed=x.closed||null;
  if(k==="raid"){ if(!("imp" in f)) f.imp=x.imp; if(!("lik" in f)) f.lik=x.lik; }
  norm(k,f); const v={...f}; if("closed" in v) v.raised=x.raised; delete v.imp; delete v.lik; delete v.pr;
  const err=validate(k,v,false,x); return err?{err}:{f}; }
export const bkSame=(a,b)=>String(a??"").trim()===String(b??"").trim();
export const bkChanged=(x,f)=>Object.keys(f).filter(n=>typeof f[n]==="boolean"?!!x[n]!==f[n]:!bkSame(x[n],f[n]));
/* one change to several items: one proposal, one Undo. `what` names it ("Closed 4 items"). */
export async function batchMove(k,ids,patch,what){ const r=await itemsMove(ids.map(id=>({k,id,patch})),what), done=r.done.length>0; if(done) hlClear(); return done; }
/* BL-314: the same save for a list of {k, id, patch}, each item with its own change (ask creaite's field card): each owner resolved
   against the register (ownerFinal), each item through the sidebar's checks (prepMove), then one proposal, one apply, one Undo.
   Resolves to {done, left, missing}: the IDs saved (none when nothing was), the items left out and why, and IDs not on the page. */
export async function itemsMove(list,what,opts={}){ const owners=new Map(), none={done:[],left:[],missing:[]};
  for(const o of list) for(const n of ["o","by"]){ const v=o.patch[n]; if(n in o.patch&&v&&v!=="TBC"&&!owners.has(v)){ const w=await ownerFinal(v); if(w===null) return none; owners.set(v,w); } }
  const ok=[], left=[], missing=[];
  for(const {k,id,patch} of list){ const x=REC(k,id); if(!x){ missing.push(id); continue; }
    const owner=owners.get(patch.o)??owners.get(patch.by)??null, r=prepMove(k,x,patch,owner); if(r.err){ left.push(`${id} (${oneLine(r.err).replace(/\.$/,"")})`); continue; }
    const ch=bkChanged(x,r.f); if(ch.length) ok.push({k,id,x,f:r.f,ch,before:{...x}}); }
  if(!ok.length){ snack(left.length?`Nothing changed. Left out: ${left.join("; ")}.`:"Nothing changed: they already have that."); return {...none,left,missing}; }
  if(list.length>BULK_MAX&&!await boardAsk({title:`Change ${list.length} items?`,hint:what,clear:true,okText:"Change them"})) return {...none,left,missing};
  const items=ok.map(o=>({op:"update",table:o.k,id:o.id,changes:toDb(o.k,Object.fromEntries(o.ch.filter(n=>!(o.k==="raid"&&n==="pr")).map(n=>[n,o.f[n]]))),based_on:o.x.updated_at}));
  const n=ok.length, text=what.replace("{n}",`${n} item${n===1?"":"s"}`)+(left.length?`. Left out: ${left.join("; ")}`:"");
  const done=await save(text,items,null,()=>{ ok.forEach(o=>Object.assign(o.x,o.f,{upd_at:nowStamp()})); },()=>{ ok.forEach(o=>{ Object.keys(o.x).forEach(c=>delete o.x[c]); Object.assign(o.x,o.before); }); },undefined,{recs:ok.map(o=>({k:o.k,id:o.id,f:Object.fromEntries(o.ch.map(n=>[n,o.f[n]]))})),wait:!!opts.wait});   /* BL-304: on screen at once */
  return {done:done?ok.map(o=>o.id):[],left,missing}; }
/* what the bar offers for these items: [field, label, options|"date", reason when withheld] */
export function bkFields(){ const L=bkItems(); if(L.length<2) return []; const k=L[0].k, mixed=L.some(o=>o.k!==k), one=new Set(L.map(o=>o.x.p)); const proj=one.size===1?[...one][0]:null, x0=L[0].x;
  const why=mixed?"These items are of different kinds":"";
  const sel=(f,label,opts,skip)=>[f,label,opts,why||skip||""];
  if(k==="decisions") return [sel("by","Made by",["TBC",...peopleAll()],L.some(o=>o.x.st==="Withdrawn")?"A withdrawn decision keeps its decision maker":"")];
  const projOnly=proj?"":"These items are in different projects";
  const F=fieldsFor(k,x0), opt=n=>(F.find(e=>e[0]===n)||[])[3];
  return [sel("st","Status",BK_STATUS[k]),sel("o","Owner",["TBC",...peopleAll()]),sel("due","Due date","date"),
    ...(k==="actions"?[sel("pr","Priority",opt("pr"))]:[sel("imp","Impact",opt("imp")),sel("lik","Likelihood",opt("lik"))]),
    sel("ws","Workstream",proj?[["","None"],...wsFor(proj).map(w=>[w,w])]:[],projOnly),sel("ms","Milestone",proj?msChoices(proj,""):[],projOnly)]; }
export const BK_LABEL={st:"status",o:"owner",by:"made by",due:"due date",pr:"priority",imp:"impact",lik:"likelihood",ws:"workstream",ms:"milestone"};
export function hlBar(){ if(shared.VIEW==="work"&&shared.WT==="all"){ const bar=$("#wbulk"); if(bar){ bar.hidden=true; bar.textContent=""; } }   /* BL-113: no bulk bar on the All tab */
  else { (()=>{ const bar=$("#wbulk"); if(!bar) return; const L=bkItems();
  if(shared.VIEW!=="work"||L.length<2){ bar.hidden=true; bar.textContent=""; return; }
  const k=L[0].k, F=bkFields(), canClose=k!=="decisions"&&L.every(o=>o.k===k);
  const ctl=([f,label,opts,why])=>f==="due"?`<span class="bkf"><label class="bklab" for="bkDate">${label}</label><span class="dwrap"><input type="text" id="bkDate" data-pick="1" data-date="1" data-bf="due" placeholder="DD-MM-YYYY" autocomplete="off" ${why?"disabled":""} aria-label="Set the due date of ${L.length} items" title="${esc(why)}"><button type="button" class="dbtn" data-cal="bkDate" ${why?"disabled":""} aria-label="Choose date">${CALI}</button></span></span>`
    :`<span class="bkf"><label class="bklab">${label}<select data-bf="${f}" ${why?'disabled aria-disabled="true"':""} title="${esc(why)}"><option value="">Set…</option>${ceOpts(opts).map(o=>`<option value="${esc(o[0])}">${esc(o[1])}</option>`).join("")}</select></label></span>`;
  bar.hidden=false;
  putHTML(bar,html`<span class="bkn" aria-live="polite">${L.length} selected</span>${canClose?html`<button type="button" class="btn" data-bq="close">Close</button><button type="button" class="btn" data-bq="reopen">Reopen</button>`:""}${raw(F.map(ctl).join(""))}<span class="sp"></span><button type="button" class="btn" data-bq="clear" aria-label="Clear the selection" title="Clear the selection (Esc)">${raw(ic("x"))}</button>`); })();
  { const bar=$("#wbulk"); if(bar&&!bar.hidden&&shared.VIEW==="work"){ const all=rows(), shown=new Set(hlOrder().map(o=>o.id)), hid=[...HL.keys()].filter(id=>!shown.has(id)).length;
    const n=bar.querySelector(".bkn"); if(n) n.textContent=`${HL.size} selected${hid?` (${hid} in collapsed groups)`:""}${HLNOTE?` · ${HLNOTE}`:""}`;
    if(HL.size<all.length) n&&addHTML(n,"afterend",html`<button type="button" class="linkbtn" data-bq="all" title="Highlights every item the filters show, in collapsed groups too">Select all ${all.length} matching</button>`); } } }
  if(!shared.LOADING){ const bar=$("#wbulk"); if(bar&&!bar.hidden){ const L=bkItems();
    if(L.length&&L.every(o=>o.k==="actions")&&!bar.querySelector("[data-drbulk]")) { const sp=bar.querySelector(".sp"); if(sp) addHTML(sp,"beforebegin",
      html`${raw(draftBtn("update-bulk","Draft updates",`Draft an update for each of the ${L.length} from what has happened since, as proposals in Review`,'data-drbulk="1"'))}<span class="drbst" role="status"></span>`); } } } }
export const bkWhat=(f,v)=>f==="st"&&v==="Closed"?"Closed {n}":f==="st"&&v==="Open"?"Reopened {n}":`${BK_LABEL[f][0].toUpperCase()+BK_LABEL[f].slice(1)} set to ${v===""||v===null||v===undefined?"none":(f==="due"?fd(v):v)} on {n}`;
export async function bkApply(f,v){ if(f==="due"&&v&&!WK.ok&&wkAsk(v,$("#bkDate")||document.body,d=>bkApply("due",d))) return; const L=bkItems(); if(L.length<2) return; await batchMove(L[0].k,L.map(o=>o.id),{[f]:v},bkWhat(f,v)); }
export function bkDate(){ const i=$("#bkDate"); if(!i) return; const v=i.value.trim(); let out=null;
  if(v!==""){ const t=DDATE.test(v)?toIso(v):"", d=t?new Date(t+"T12:00:00"):null; if(!d||isNaN(d)||d.toISOString().slice(0,10)!==t){ snack(DDATE.test(v)?"That isn't a real date.":"Not a date creaite knows. "+DATE_HELP); return; } out=t; }
  bkApply("due",out); }
/* ===== end BL-124 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootWork0133(){
document.addEventListener("click",e=>{ const b=e.target.closest("#wbulk [data-bq]"); if(!b) return; const q=b.dataset.bq;
  if(q==="clear") hlClear(); else if(q==="close") bkApply("st","Closed"); else if(q==="reopen") bkApply("st","Open"); });
document.addEventListener("change",e=>{ const s=e.target.closest&&e.target.closest("#wbulk select[data-bf]"); if(!s||!s.value&&s.value!=="") return; if(s.value===""&&s.selectedIndex===0) return; const f=s.dataset.bf, v=s.value; bkApply(f,v); });
document.addEventListener("input",e=>{ if(e.target.id==="bkDate"&&!(e instanceof InputEvent)) bkDate(); });
document.addEventListener("keydown",e=>{ if(e.target.id==="bkDate"&&e.key==="Enter"){ e.preventDefault(); bkDate(); } });
}
/* ===== BL-134 (sprint-all-items) =====
   All items: a fourth Work tab listing Actions, RAID and Decisions together, read-only (frame 7 of the work mock-up).
   The merged read model: allRows() gives one row per item, a copy carrying k (its table), type (ALL_TYPES) and the shared
   fields. A decision's owner (o) is Made by (who made it, or who is asked); its due is Needed by, and a made decision's is its
   Date; its raised is its Date too, and it has no priority (blank, sorted last) and no workstream. st is the status bucket
   (Open: Open, Delayed, Pending; Closed: Closed, Made; Cancelled: Cancelled, Withdrawn) that the filters, groups and counts
   use, so the shared code that reads x.st works unchanged; nst is the item's own word, which its cell shows. IDs are unique
   across the three tables, so a row is k plus id; kOfId(id) finds the table and every handler reads it from the row. The copy
   is rebuilt on each render (ALLC), so a change made on another tab or in the panel shows at once. */
export const ALL_TYPES=["Action","Decision","Risk","Issue","Assumption","Dependency"];   /* the one list: promises (BL-125) would be a seventh entry */
export const ALL_ST=["Open","Closed","Cancelled"];
export const allBucket=s=>s==="Open"||s==="Delayed"||s==="Pending"?"Open":s==="Closed"||s==="Made"?"Closed":"Cancelled";
export let ALLC=null;
export function allRows(){ if(ALLC) return ALLC;
  const row=(k,x,extra)=>{ const r={...x,k,...extra}; r.nst=x.st; r.st=allBucket(x.st); return r; };
  ALLC=[...A.map(x=>row("actions",x,{type:"Action"})),...R.map(x=>row("raid",x,{type:x.type||"Risk"})),
    ...DEC.map(x=>row("decisions",x,{type:"Decision",o:x.by||"",due:x.st==="Made"?(x.date||null):(x.due||null),raised:x.date||"",pr:""}))];
  return ALLC; }
export const allLate=x=>x.st==="Open"&&!!x.due&&x.due<TODAY;
export const kOfId=id=>A.some(x=>x.id===id)?"actions":R.some(x=>x.id===id)?"raid":DEC.some(x=>x.id===id)?"decisions":null;
/* the filters: Status (the three buckets), Due, Owner, Project, Priority on the toolbar; Type, Stale, Last updated and Raised in
   "+ Filter". Fields that only some types have (Workstream, Response, Milestone, Source, Client-visible) are not offered. */
   /* no priority (a decision) sorts after Low */
/* The tab (stage 2): BL-128 to BL-132's own components pointed at allRows(). The List only (no Board: the layout switch and the
   Display menu's Layout are hidden here). Read-only: no cell editing (BL-123), no bulk bar (BL-124), no New button; a click
   highlights, the ID, a double-click or Enter opens the item's own panel (openRecord with the row's table), and hovering a cell
   says which tab to edit it on. Saved views are kept with the others (work.saved_views.all); the default view is All open. */
 
export const ALLTAB={actions:"Actions",raid:"RAID",decisions:"Decisions"};
/* groups: Type, Status (the buckets) and Priority (with No priority) list every value; Project, Owner and Due are the shared ones */
/* a group header counts items and overdue ones (the bucket's Open, as RAID's) */
/* the cells: each type's own words (status, a made decision's date), a Type tag that carries its word, and where to edit it */
export function allCell(k,x){ let h;
  if(k==="t") h=cell("t",x,x.k).replace('<td class="title" data-f="t">',`<td class="title" data-f="t">${wflag(x.k,x.id)}`);
  else if(k==="type") h=`<td data-f="type"><span class="typetag">${esc(x.type)}</span></td>`;
  else if(k==="due"){ const made=x.k==="decisions"&&x.nst==="Made"; h=`<td data-f="due" class="${allLate(x)?"late":""}" style="white-space:nowrap">${x.due?fd(x.due):"—"}<div class="x">${made&&x.due?"Made":x.due&&x.st==="Open"?rel(x.due):""}</div></td>`; }
  else if(k==="pr") h=x.pr?cell("pr",x,x.k):'<td data-f="pr" class="x">—</td>';
  else if(k==="st") h=`<td data-f="st">${esc(x.nst)}</td>`;
  else if(k==="p") h=`<td data-f="p">${pLink(x.p)}</td>`;
  else h=cell(k,x,x.k);
  return h.replace(/^<td(?![^>]*\btitle=)/,`<td title="Edit it on the ${ALLTAB[x.k]} tab"`); }
/* opening: the row's own table, never the tab */
/* no Board here */
/* no bulk bar */
export function allDecorate(){ const on=shared.WT==="all"; $("#wlay").hidden=on; if(!on) return;
  $$("#workTbl tr[data-row]").forEach(tr=>{ tr.dataset.k=kOfId(tr.dataset.row)||""; });
  const c=$("#workCrumb [aria-current]"); if(c&&!$("#workCrumb").hidden) c.textContent="All items";
  putHTML($("#whintList"),html`${raw(workHint("list").replace(/ · click a value to change it/,""))} · read-only: change an item on its own tab`); }
/* Links in (stage 3): the project page's work card gains one "All items" link, to All items filtered to the project and open.
   The other links into Work, ask creaite and search are unchanged. */
/* ===== end BL-134 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootWork0147(){
FDEFS.all=[["st","Status",()=>ALL_ST.map(v=>[v,v]),x=>x.st],
  ["due","Due",()=>[["overdue","Overdue"],["soon",`Due in ${S.dueSoon} days`],["none","No date"],["later","Later"]],dueKey],
  ["o","Owner",ownerOpts,x=>x.o],["p","Project",()=>P.map(p=>[p.code,p.name]),x=>x.p],["pr","Priority",()=>PRIOS.map(v=>[v,v]),x=>x.pr],
  ["ty","Type",()=>ALL_TYPES.map(v=>[v,v]),x=>x.type,1],
  ["sl","Stale",()=>[["yes",`Stale (no change for ${+S.staleDays||7} days)`],["no","Not stale"]],x=>{ const a=staleAge("all",x); return x.st==="Open"&&a!==null&&a>=(+S.staleDays||7)?"yes":"no"; },1],
  ["lu","Last updated",()=>lastDays,x=>x.upd_at,1,(x,set)=>within(x.upd_at,set)],["rd","Raised",()=>lastDays,x=>x.raised,1,(x,set)=>within(x.raised,set)]];
/* the default order: overdue first, then due soonest, undated last (a made decision by its date) */
// @ts-expect-error TS2362: true and false subtract as 1 and 0 (late items sort first)
DEFSORT.all=(a,b)=>(allLate(b)-allLate(a))||(a.due||"9").localeCompare(b.due||"9")||a.id.localeCompare(b.id);
CLOSEDST.all=["Closed","Cancelled"];
{ const pk=SORTKEY.pr; SORTKEY.pr=x=>{ const i=pk(x); return i<0?PRIOS.length:i; }; }
SORTKEY.p=x=>pName(x.p).toLowerCase();
COLS.all=[["id","ID"],["t","Item"],["type","Type"],["o","Owner"],["due","Due"],["pr","Priority"],["st","Status"],["p","Project"],["ws","Workstream"],["src","Source"],["upd","Last updated"]];
DEFCOLS.all=["t","type","o","due","st"];
if(!Array.isArray(shared.COLVIS.all)) shared.COLVIS.all=[...DEFCOLS.all];
GROUPS.all=[["project","Project"],["type","Type"],["owner","Owner"],["due","Due"],["status","Status"],["priority","Priority"]];
BDEFG.all="due";
PRESETS.all=[["open","All open",{st:["Open"]}],["mine","Mine",{st:["Open"],o:["@me"]}],["soon","Due soon",{st:["Open"],due:["soon"]}],["chase","Chase",{st:["Open"],"!o":["@me"],sl:["yes"]}],
  ["overdue","Overdue",{st:["Open"],due:["overdue"]},true],["closed","Closed",{st:["Closed","Cancelled"]}]];
if(!Array.isArray(shared.SAVED.all)) shared.SAVED.all=[];
}
/* ===== BL-138 (sprint-all-items) =====
   People in two tabs. "With work" (first and default): anyone with an open action, an open risk or issue, or a decision waiting
   on them (a Decision needed where they are the one asked, BL-53); made and withdrawn decisions are history, not an assignment.
   You are always first on With work. "Nothing assigned": the other people creaite knows (the people register, which meeting
   attendees, mail, Teams and reports add to, and anyone whose items are all closed), with the projects they appear in, a count
   of their closed items and "not in register" for a name only seen on items. Nobody is on both; a hidden person (Settings ›
   People) is on neither. Each tab keeps its own sort. The tab is kept in the address (#people/none) and remembered in this
   browser, so the rail and the breadcrumbs return to it; a plain #people address opens With work. Counts only (BL-56). */
export const PSORTT={work:{col:"late",dir:"desc"},none:{col:"name",dir:"asc"}};
shared.PTAB=store.get("creaite-peopletab","work")==="none"?"none":"work";
export function setPTab(t){ t=t==="none"?"none":"work"; PSORTT[shared.PTAB]=shared.PSORT; shared.PTAB=t; shared.PSORT=PSORTT[t]; store.set("creaite-peopletab",t); }
export function peopleTabs(){ const L=PERS().filter(x=>!isHiddenPerson(x.name)).map(x=>Object.assign(x,{dw:x.D.filter(d=>d.st==="Pending"),cl:[...x.A,...x.R].filter(i=>!open(i)).length+x.D.filter(d=>d.st!=="Pending").length}));
  const has=x=>x.oa.length||x.or.length||x.dw.length;
  return {work:L.filter(x=>has(x)||isMe(x.name)),none:L.filter(x=>!has(x)&&!isMe(x.name))}; }
export function renderPeople(){ const T=peopleTabs(), none=shared.PTAB==="none", f=PSORTS[shared.PSORT.col]||PSORTS.name;
  const L=T[shared.PTAB].sort((a,b)=>(!none&&(isMe(a.name)?-1:isMe(b.name)?1:0))||(()=>{ const x=f(a),y=f(b); return (x<y?-1:x>y?1:0)*(shared.PSORT.dir==="asc"?1:-1); })()||a.name.localeCompare(b.name));
  if(!$("#ptabsHost")) addHTML($("#peopleTbl"),"beforebegin",html`<div class="tabhost" id="ptabsHost"></div>`);   /* BL-316: the Tabs block */
  drawTabs($("#ptabsHost"),{items:[["work","With work"],["none","Nothing assigned"]].map(([k,l])=>({id:k,label:l,count:T[k].length,data:{ptab:k}})),selected:shared.PTAB,
    onSelect:k=>{ if(k===shared.PTAB) return; setPTab(k); renderPeople(); navWrite(false); },label:"People",className:"tabs",id:"ptabs",controls:"peopleTbl",wrap:true});
  const th=(c,l,num)=>`<th class="${num?"num":""}" data-psort="${c}" aria-sort="${shared.PSORT.col===c?(shared.PSORT.dir==="asc"?"ascending":"descending"):"none"}"><button type="button" class="thsort">${l}${shared.PSORT.col===c?(shared.PSORT.dir==="asc"?" ▲":" ▼"):""}</button></th>`;   /* v1.9.5 (UI audit P1-7): aria-sort stays on the column header; the control is a real button inside it */
  const nameCell=x=>`<td class="title"><a href="#" class="plink2" data-person="${esc(x.name)}">${esc(isMe(x.name)?`You (${x.name})`:x.name)}</a>${x.p||isMe(x.name)?"":` <span class="tag warn" title="${none?"Seen on items but isn’t in the people register":"Owns items but isn’t in the people register"}">not in register</span>`}</td>
    <td>${x.p&&x.p.org?esc(x.p.org):'<span class="sub">—</span>'}</td><td>${x.p&&x.p.role?esc(x.p.role):'<span class="sub">—</span>'}</td><td>${x.codes.map(pLink).join(" ")||'<span class="sub">—</span>'}</td>`;
  $("#peopleTbl").setAttribute("role","tabpanel");
  putHTML($("#peopleTbl"),!L.length?html`<div class="empty">${none?"Everyone creaite knows has something assigned.":"No one has open work or a decision waiting on them."}</div>`:none?html`<table><thead><tr>${raw(th("name","Name"))}${raw(th("org","Organisation"))}${raw(th("role","Role"))}<th>Projects</th>${raw(th("cl","Closed items",1))}</tr></thead><tbody>${L.map(x=>html`<tr class="click" data-pp="${x.name}">${raw(nameCell(x))}<td class="num">${raw(countLink(`${plur(x.cl,"closed item")} of ${x.name}`,x.cl,"all:closed:",{st:["Closed","Cancelled"],o:ownersOf([...x.A,...x.R,...x.D])},x.cl||"—"))}</td></tr>`)}</tbody></table>`:html`<table><thead><tr>${raw(th("name","Name"))}${raw(th("org","Organisation"))}${raw(th("role","Role"))}<th>Projects</th>${raw(th("oa","Open actions",1))}${raw(th("or","Open RAID",1))}${raw(th("dw","Decisions waiting",1))}${raw(th("late","Overdue",1))}</tr></thead><tbody>${L.map(x=>html`<tr class="click" data-pp="${x.name}">${raw(nameCell(x))}
    ${raw(personCounts(x))}</tr>`)}</tbody></table>`); }
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootWork0148(){
shared.PSORT=PSORTT[shared.PTAB];
Object.assign(PSORTS,{dw:x=>x.dw.length,cl:x=>x.cl});
}
/* ===== BL-190 (sprint-links) ===== the People list's figures open Work filtered to that person (every spelling of their name on
   the items counted, so aliases are included) and that kind: Open actions (status Open only, as All open lists them), Open RAID,
   Decisions waiting (they are the one asked) and Overdue (All items: their Open and Delayed actions and RAID items past due). A zero stays plain. */
export const ownersOf=L=>[...new Set(L.map(i=>i.o||i.by).filter(Boolean))];
export const latesOf=x=>[...x.oa,...x.or].filter(i=>i.due&&i.due<TODAY);
export function personCounts(x){ const nm=isMe(x.name)?"you":x.name, late=latesOf(x);
  return `<td class="num">${countLink(`${plur(x.oo.length,"open action")} owned by ${nm}`,x.oo.length,"actions:open:",{o:ownersOf(x.oo)})}</td>`
    +`<td class="num">${countLink(`${plur(x.or.length,"open RAID item")} owned by ${nm}`,x.or.length,"raid:open:",{o:ownersOf(x.or)})}</td>`
    +`<td class="num">${countLink(`${plur(x.dw.length,"decision")} waiting on ${nm}`,x.dw.length,"decisions:pending:",{o:ownersOf(x.dw)},x.dw.length||"—")}</td>`
    +`<td class="num ${x.late?"late":""}">${countLink(`${plur(late.length,"overdue item")} owned by ${nm}`,late.length,"all:open:",{st:["Open"],due:["overdue"],ty:["Action","Risk","Issue","Assumption","Dependency"],o:ownersOf(late)},late.length||"—")}</td>`; }
/* ===== end BL-190 (People) ===== */
/* the address: #people is With work, #people/none Nothing assigned; go("people") with no tab keeps the one last used */
/* ===== end BL-138 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootWork0150(){
/* BL-316: People's two tabs are the Tabs block (renderPeople draws them; a click or ← → Home End chooses) */
}
