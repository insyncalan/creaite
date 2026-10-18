// @ts-check
/* core/nav.js (BL-231 step 2b): navigation (`go`, `navWrite`, the address), count links, the tab title and the open-all link.
   Moved from script/ unchanged, apart from `export`, `shared.` for the shared state (state.js) and the steps that ran at load,
   which are now boot…() functions called by src/main.js in today's order. Pieces: 0022-navigation.js, 0023-bl-190-sprint-links.js, 0024-after-bl-190-core.js, 0139-bl-152-sprint-ux.js, 0157-bl-153-sprint-ux.js */
import { actKindOf, renderActivity } from "../activity.js";
import { RBMARK } from "../ask.js";
import { A, DEC, P, pName, R, REV } from "./data.js";
import { $, $$, addHTML, esc, html, tipHide } from "./dom.js";
import { mFirst, mLeave } from "./motion.js";
import { curDrop } from "./editor.js";
import { cardGroup, menuGroup } from "./hover.js";
import { anim, DATE, mScroll, reduced, store } from "./page.js";
import { snack } from "./server.js";
import { shared } from "./state.js";
import { setRailView } from "../stores/rail.js";
import { filesOpened, renderFiles } from "../files.js";
import { helpNorm, renderHelp } from "../help.js";
import { helpScreenSync } from "../helpscreen.js";
import { renderInbox } from "../intake.js";
import { meetingRoute } from "../meetings.js";
import { renderPrep } from "../components/prep/PrepPage.jsx";
import { parseWeekly } from "../components/report/weekly/WeeklyView.jsx";
import { parseKey } from "../components/report/ClientView.jsx";   /* #221: the old weekly and client addresses; the hub opens them */
import { renderReports } from "../components/reporting/ReportsPage.jsx";   /* BL-337 */
import { openSpace, renderReporting } from "../components/reporting/ReportingSpace.jsx";
import { parseReporting, repWeek, reportingHref, spaceCode, spaceWeek } from "../stores/reporting.js";
import { hubView } from "../stores/hub.js";
import { notesCodeOk, notesLeave, renderNotes } from "../notes.js";
import { noteCur, noteFind } from "../stores/notes.js";
import { minutesPath, renderMinutes } from "../components/minutes/MinutesView.jsx";
import { prepHref, prepKeyOf, prepView, prepViewKey } from "../stores/prep.js";
import { mvAfter, mvEdClose, renderMilestones } from "../milestones.js";
import { openRecord, pkNewAsk, pkNewTitle } from "../panel.js";
import { askDiscard, closePanel, curGuard, PKN, renderCockpit, renderProjects } from "../projects.js";
import { renderReview } from "../review.js";
import { rjCloseMenu, rjLeave } from "../stores/rejects.js";
import { BASETITLE, PERS, renderPerson, renderSettings, setResolve, sw, VIPS } from "../settings.js";
import { renderToday, SETUPK } from "../today.js";
import { allViews, applyFilters, applyView, clearAllFilters, closeDisp, FDEFS, groupOf, groupsOf, layoutOf, listGroupOf, PROJF, renderPeople, renderWork, setPTab, snapshot, SORT, subOf, syncView, WB, WGRP, WINIT, WLAY, WLGRP, workChanged, WSUB } from "../work.js";
/* ======================= navigation ======================= */
shared.VIEW="today"; shared.COCK=null; shared.FROMPROJ=null; shared.NAVSTATE=null; shared.PERSON=null;
/* BL-38: every view writes its place to the address, so Back, Forward, reload and bookmarks work:
   #cockpit=ABC · #work=raid&v=open&p=ABC&from=ABC · …&item=ABC-003 (the open item). An open edit blocks leaving. */
export const viewEl=()=>$("#"+({cockpit:"v-cockpit",mine:"v-work"}[shared.VIEW]||"v-"+shared.VIEW));
export function navState(){ const st={v:shared.VIEW,arg:shared.VIEW==="cockpit"?shared.COCK:shared.VIEW==="person"?shared.PERSON:shared.VIEW==="help"?shared.HELPARG:shared.VIEW==="settings"?shared.SCAT:null,wt:shared.WT,wv:shared.WVIEW,p:[...PROJF],q:shared.WQ,from:shared.FROMPROJ,fx:shared.VIEW==="work"?snapshot():null,sort:SORT[shared.WT]||null,vb:shared.VIEW==="work"&&!shared.WVIEW?WB[shared.WT]||null:null,lay:shared.VIEW==="work"&&layoutOf(shared.WT)==="board"?"board":"list",g:shared.VIEW==="work"?groupOf(shared.WT):null,lg:shared.VIEW==="work"?listGroupOf(shared.WT):null,sg:shared.VIEW==="work"?subOf(shared.WT,layoutOf(shared.WT)):null,
  item:shared.CUR&&shared.CUR.mode==="record"?{k:shared.CUR.k,id:shared.CUR.id}:null,scroll:viewEl()?viewEl().scrollTop:0}; 
  if(shared.VIEW==="activity") st.aq={...shared.ACTF,types:[...(shared.ACTF.types||[])]};
  if(st.v==="people") st.arg=shared.PTAB;   /* BL-190 */
  if(shared.VIEW==="milestones"){ st.arg=shared.MSCODE; st.mv=shared.MV.view; st.ms=shared.MV.peek||null; }   /* BL-245 */
  if(shared.VIEW==="prep") st.arg=prepViewKey.value;   /* BL-286 D */
  if(shared.VIEW==="reports") st.arg=repWeek.value||null;   /* BL-337 */
  if(shared.VIEW==="reporting"){ st.arg=spaceCode.value; st.rw=spaceWeek.value; st.rv=hubView.value; }   /* #221: the hub: project, week, view */
  if(shared.VIEW==="notes"){ st.arg=shared.NOTECODE; const c=noteCur.value; st.note=c&&c.code===shared.NOTECODE?c.note.file:null; st.find=!!(st.note&&noteFind.value); }   /* BL-301 B */
  if(shared.VIEW==="minutes") st.arg=minutesPath();   /* v2.1.0 P7: the minutes record's stored path */
  return st; }
export function hashOf(st){
  if(st&&st.v==="notes") return `#notes=${st.arg||""}${st.note?`&n=${encodeURIComponent(st.note)}`:""}${st.note&&st.find?"&find=1":""}`;   /* BL-301 B */
  if(st&&st.v==="reporting") return reportingHref(st.arg,st.rw,st.rv);   /* BL-337, #221 */
  if(st&&st.v==="reports") return "#reports"+(st.arg?`&w=${st.arg}`:"");
  if(st&&st.v==="prep") return prepHref(st.arg||"");   /* BL-286 D: #prep=<the dated meeting key> */
  if(st&&st.v==="minutes") return `#minutes=${encodeURIComponent(typeof st.arg==="string"?st.arg:"")}`;   /* v2.1.0 P7 */
  if(st&&st.v==="milestones") return `#milestones${st.arg?`=${st.arg}`:""}&v=${st.mv==="move"?"movement":"plan"}${st.ms?`&ms=${st.ms}`:""}`;   /* BL-245 */
  if(st&&st.v==="people") return "#people"+(st.arg==="none"?"/none":"");   /* BL-190 */
  let h=st.v==="help"?`help-${st.arg||"start"}`:st.v==="settings"?`settings/${st.arg||"general"}`:st.v==="cockpit"?(st.arg?`cockpit=${st.arg}`:"cockpit"):st.v==="person"?`person=${encodeURIComponent(st.arg)}`:st.v==="work"?`work=${st.wt}${st.wv?`&v=${encodeURIComponent(st.wv)}`:""}${st.p&&st.p.length?`&p=${st.p.join(",")}`:""}${!st.wv&&st.fx?(Object.keys(st.fx).length?Object.entries(st.fx).map(([k,v])=>`&${k}=${v.map(encodeURIComponent).join(",")}`).join(""):"&f=none"):""}${st.lay==="board"?`&lay=board&g=${st.g}`:st.lg&&st.lg!=="none"?`&lg=${st.lg}`:""}${st.sg&&st.sg!=="none"?`&sg=${st.sg}`:""}${st.sort?`&s=${st.sort.col}.${st.sort.dir}`:""}${st.q&&st.q.trim()?`&q=${encodeURIComponent(st.q.trim().replace(/[&=#]/g," "))}`:""}${st.from?`&from=${st.from}`:""}${!st.wv&&st.vb?`&vb=${encodeURIComponent(st.vb)}`:""}`:st.v==="inbox"?"intake":st.v;
  if(st.item) h+=`&item=${st.item.id}`; h="#"+h;
  if(st&&st.v==="activity"&&st.aq){ const a=st.aq, p=[];
    if((a.q||"").trim()) p.push("q="+encodeURIComponent(a.q.trim())); if((a.types||[]).length) p.push("type="+a.types.map(encodeURIComponent).join(","));
    if(a.from) p.push("from="+a.from); if(a.to) p.push("to="+a.to); if(p.length) h+="&"+p.join("&"); } return h; }
export function parseHash(h){ { const mm=/^#?weekly=(.+)$/.exec(String(h||"")), a=mm&&parseWeekly(mm[1]); if(a&&P.some(p=>p.code===a.code)) return {v:"reporting",arg:a.code,rw:a.week||"",rv:"internal",wt:shared.WT,wv:null,p:[],from:null,item:null,scroll:0}; }   /* v2.1.0 P6; #221: the old weekly address opens the hub */
  { const q=(h||"").replace(/^#/,""); const mm=/^meeting=([0-9a-f]{6,20})/.exec(q); if(mm){ const to=meetingRoute(mm[1]), st=to&&parseHash(to); if(st) return st; snack("That meeting isn't in creaite's records any more"); return {v:"today",arg:null,wt:shared.WT,wv:null,p:[],from:null,item:null,scroll:0}; } }   /* v2.1.0 P10: the retired meeting page (BL-233) opens its Prep or its minutes */
  { const r=parseReporting(h,c=>P.some(p=>p.code===c)); if(r) return {v:"reporting",arg:r.code,rw:r.week,rv:r.view,wt:shared.WT,wv:null,p:[],from:null,item:null,scroll:0}; }   /* BL-337 */
  { const k=prepKeyOf(h); if(k) return {v:"prep",arg:k,wt:shared.WT,wv:null,p:[],from:null,item:null,scroll:0}; }   /* BL-286 D */
  { const mm=/^#?client-report=(.+)$/.exec(String(h||"")); if(mm){ const a=parseKey(mm[1]); return a&&P.some(p=>p.code===a.code)?{v:"reporting",arg:a.code,rw:a.week||"",rv:"client",wt:shared.WT,wv:null,p:[],from:null,item:null,scroll:0}:null; } }   /* v2.1.0 P8; #221: the old client report address opens the hub's Client view */
  { const mm=/^#?notes=([^&]+)(?:&n=([^&]*))?/.exec(String(h||"")); if(mm){ let code="", n=null; try{ code=decodeURIComponent(mm[1]); n=mm[2]?decodeURIComponent(mm[2]):null; }catch(e){ return null; }
    if(!notesCodeOk(code)) return null; return {v:"notes",arg:code,note:n,find:/[&]find=1(&|$)/.test(String(h||"")),wt:shared.WT,wv:null,p:[],from:null,item:null,scroll:0}; } }   /* BL-301 B */
  { const mm=/^#?minutes=(.+)$/.exec(String(h||"")); if(mm){ let a=""; try{ a=decodeURIComponent(mm[1]); }catch(e){ return null; } return /\.html$/i.test(a)?{v:"minutes",arg:a,wt:shared.WT,wv:null,p:[],from:null,item:null,scroll:0}:null; } }   /* v2.1.0 P7: #minutes=<stored path> */
  { const q=String(h||"").replace(/^#/,""), mm=/^milestones(?:=([^&]*))?((?:&.*)?)$/.exec(q);
    if(mm){ const code=mm[1]?decodeURIComponent(mm[1]):""; if(code&&!P.some(p=>p.code===code)) return null;
    const kv=Object.fromEntries(mm[2].split("&").filter(Boolean).map(x=>x.split("=")));
    return {v:"milestones",arg:code||null,mv:kv.v==="movement"?"move":"plan",ms:kv.ms?decodeURIComponent(kv.ms):null,wt:shared.WT,wv:null,p:[],from:null,item:null,scroll:0}; } }   /* BL-245 */
  { const m=/^#?people(?:\/(none|work))?$/.exec(h||""); if(m) return {v:"people",arg:m[1]||"work",wt:shared.WT,wv:null,p:[],from:null,item:null,scroll:0}; }   /* BL-190 */
  let x=String(h||""); if(/^#?activity\?/.test(x)) x=x.replace("?","&");
  const st=(h=>{ const q=(h||"").replace(/^#/,""); if(!q) return null; const parts=q.split("&"), [v,arg]=parts[0].split("=").map(decodeURIComponent), kv=Object.fromEntries(parts.slice(1).map(x=>{ const [k,val=""]=x.split("="); return [k,k==="v"||k==="q"||k==="vb"?decodeURIComponent(val):val]; }));
  const st={v,arg:null,wt:shared.WT,wv:null,p:[],from:null,item:null,scroll:0};
  { const sm=/^settings(?:\/([^/]+))?$/.exec(v); if(sm){ st.v="settings"; st.arg=sm[1]||arg||null; if(st.arg&&!setResolve(st.arg)) st.arg=null; return st; } }   /* BL-115: #settings/<category or section>; the old #settings and #settings=<tab> too */
  if(/^help(-|$)/.test(v)){ st.v="help"; st.arg=helpNorm(v.slice(5))||null; return st; }   /* BL-84: #help-start, #help-howto-<task>… */
  if(v==="cockpit"){ if(arg){ if(!P.some(p=>p.code===arg)) return null; st.arg=arg; } }   /* #204: bare #cockpit is the Choose a project page */
  else if(v==="work"){ st.wt=["actions","raid","decisions","all"].includes(arg)?arg:"actions";   /* BL-134: #work=all */ st.wv=kv.v||null; st.vb=kv.vb||null; st.p=(kv.p||"").split(",").filter(c=>P.some(p=>p.code===c)); st.q=kv.q||""; st.from=P.some(p=>p.code===kv.from)?kv.from:null;
    const fx={}; [...new Set(["st","due","o","pr","ws","ty","rs","src","cv","dt","dr","rr","cr","vip","ms",...FDEFS[st.wt].map(d=>d[0])])].filter(k=>k!=="p").flatMap(k=>[k,"!"+k]).forEach(k=>{ if(kv[k]!==undefined) fx[k]=kv[k].split(",").map(decodeURIComponent); });   /* BL-130: "!key" is "is not"; BL-318: the project filter is st.p, never a filter set, or a reload with a view and a project lost the view */ st.fx=Object.keys(fx).length?fx:kv.f==="none"?{}:null;   /* BL-77: "&f=none" is a list with no filters on (e.g. closed items shown too) */
    if(kv.s){ const [col,dir]=kv.s.split("."); st.sort={col,dir:dir==="desc"?"desc":"asc"}; }
    st.lay=kv.lay==="board"?"board":"list"; if(groupsOf(st.wt).some(g=>g[0]===kv.g)) st.g=kv.g;
    st.lg=groupsOf(st.wt).some(g=>g[0]===kv.lg)?kv.lg:"none"; st.sg=groupsOf(st.wt).some(g=>g[0]===kv.sg)?kv.sg:"none"; }   /* BL-129 */
  else if(v==="reports"){ st.arg=/^\d{4}-\d{2}-\d{2}$/.test(kv.w||"")?kv.w:null; }   /* BL-337 */
  else if(v==="person"){ if(!PERS().some(x=>x.name===arg)) return null; st.arg=arg; }
  else if(v==="item"){ const id=arg, k=A.some(x=>x.id===id)?"actions":R.some(x=>x.id===id)?"raid":DEC.some(x=>x.id===id)?"decisions":null; if(!k) return null; return {v:"work",arg:null,wt:k,wv:null,p:[],from:null,item:{k,id},scroll:0}; }
  else if(!["today","projects","reports","people","review","inbox","intake","files","activity","settings","help","mine"].includes(v)) return null;
  if(v==="intake") st.v="inbox";      /* BL-70: #intake is the address; #inbox still opens the screen */
  const id=kv.item; if(id){ const k=A.some(x=>x.id===id)?"actions":R.some(x=>x.id===id)?"raid":DEC.some(x=>x.id===id)?"decisions":null; if(k) st.item={k,id}; }
  return st; })(x);
    if(st&&st.v==="activity"){ const kv=Object.fromEntries(x.replace(/^#/,"").split("&").slice(1).map(y=>{ const i=y.indexOf("="); let v=i<0?"":y.slice(i+1); try{ v=decodeURIComponent(v); }catch(e){} return [i<0?y:y.slice(0,i),v]; }));
      st.aq={q:kv.q||"",types:(kv.type||"").split(",").filter(t=>actKindOf(t)),from:DATE.test(kv.from||"")?kv.from:"",to:DATE.test(kv.to||"")?kv.to:""}; } return st; }
export function navWrite(push){ if(push&&shared.MSNEXT!==null){ shared.MSCODE=shared.MSNEXT; shared.MSNEXT=null; }   /* BL-245 */
  const st=navState(); shared.NAVSTATE=st; try{ history[push?"pushState":"replaceState"](st,"",hashOf(st)); }catch(e){} }
export function shakeEdit(){ snack(shared.CUR&&shared.CUR.mode==="record"?"You're editing — save or cancel first":"Finish or cancel this first"); $("#pFoot").animate([{transform:"translateX(0)"},{transform:"translateX(-4px)"},{transform:"translateX(4px)"},{transform:"translateX(0)"}],{duration:220}); }
export function navBlocked(retry){ if(shared.EDITING&&shared.CUR){ shakeEdit(); return true; } return curGuard(retry); }   /* BL-47: unsaved current state asks first */
export const pkNewPending=()=>!!(shared.CUR&&shared.CUR.mode==="new"&&!shared.CUR.staged&&!shared.CUR.alert&&pkNewTitle());   /* BL-296: closing one made from a message just cancels it */   /* declared before curGuard, which runs at load */
export function restoreNav(st){ if(st&&st.v==="milestones"){ shared.MV.view=st.mv==="move"&&shared.MVAUD!=="cli"?"move":"plan"; shared.MV.after=st.ms?{id:st.ms}:null; }   /* BL-245 */
  if(!PKN.force&&pkNewPending()){ try{ history.pushState(shared.NAVSTATE,"",hashOf(shared.NAVSTATE)); }catch(x){} pkNewAsk(()=>history.back()); return; }   /* BL-179 */
  if(st&&st.v==="activity") shared.ACTF=st.aq?{...st.aq,types:[...(st.aq.types||[])]}:{};
  if(!st) st={v:"today",arg:null,wt:shared.WT,wv:null,p:[],from:null,item:null,scroll:0};
  if(st.v==="notes"){ shared.NOTEFILE=st.note||null; shared.NOTEFIND=!!st.find; }   /* BL-301 B: the note the address names opens; E: &find=1 opens Find updates */
  shared.WT=st.wt||shared.WT; if(st.v==="work"){ if(st.fx){ applyFilters(st.fx); WINIT[shared.WT]=true; if(st.vb&&allViews(shared.WT).some(v=>v.id===st.vb)) WB[shared.WT]=st.vb; syncView(); } else if(st.wv) applyView(st.wv);
    PROJF.clear(); (st.p||[]).forEach(c=>PROJF.add(c)); shared.WQ=st.q||""; SORT[shared.WT]=st.sort||null;
    if(st.lay){ shared.LAYCHOSEN=true; WLAY[shared.WT]=st.lay; if(st.g) WGRP[shared.WT]=st.g; }   /* BL-103: the layout and grouping are in the address */
    if(st.lg) WLGRP[shared.WT]=st.lay==="board"?(WLGRP[shared.WT]||"none"):st.lg; if(st.sg) WSUB[shared.WT+"|"+(st.lay||"list")]=st.sg; }   /* BL-129: the List's grouping and the sub-group too */
  if(st.v==="reports") repWeek.value=st.arg||"";   /* BL-337 */
  if(st.v==="reporting"){ spaceWeek.value=st.rw||""; hubView.value=st.rv||"internal"; }   /* #221 */
  go(st.v,st.arg,{restore:true,from:st.from});
  if(st.item){ const k=st.item.k; if(st.v==="work"&&shared.WT!==k&&shared.WT!=="all"){ shared.WT=k; renderWork(); }   /* BL-134: All items opens the item where it is */ openRecord(k,st.item.id); }
  const sc=st.scroll||0; requestAnimationFrame(()=>{ const el=viewEl(); if(el) el.scrollTop=sc; }); shared.NAVSTATE=navState(); shared.NAVSTATE.scroll=sc; }
export const mPageOf=v=>v==="work"||v==="mine"||v==="person"?"work":v==="review"?"review":v==="today"?"today":null;   /* declared before go, which runs at load */
export function go(v,arg,opt){ if(shared.RF&&v!=="review"){ shared.RF=null; }   /* BL-206 */
  if(v==="weekly"||v==="clientreport"){ const a=typeof arg==="string"?(v==="weekly"?parseWeekly(arg):parseKey(arg)):arg; if(!a||!a.code||!P.some(p=>p.code===a.code)) return false; spaceWeek.value=a.week||""; hubView.value=v==="clientreport"?"client":"internal"; v="reporting"; arg=a.code; }   /* #221: the weekly and client report pages are retired; their names open the hub */
  if(v==="milestones"){ if(arg&&!P.some(p=>p.code===arg)) return false; shared.MSNEXT=arg||null; }   /* #204: no project is the Choose a project page */
  if(shared.MVREADY&&(shared.MV.peek||shared.MV.add)) mvEdClose(true);   /* BL-245 */
  const from=shared.VIEW, fromPage=mPageOf(shared.VIEW);
  if(from==="notes"&&v!=="notes") notesLeave();   /* BL-301 B: leaving the note ends its editing session (its file is written) */
  if(!shared.LOADING&&from==="review"&&v!=="review"){ shared.MREVLEFT=true; rjCloseMenu(false); rjLeave(); }   /* BL-263; BL-315: the greyed rejected rows go when Review is left */
  if(v==="people"&&(arg==="none"||arg==="work")) setPTab(arg);   /* BL-190 */
  const r=((v,arg,opt={})=>{ if(!opt.restore){ if(navBlocked(()=>go(v,arg,opt))) return false; navWrite(false); }   /* keep this entry's item and scroll for Back */
  /* BL-77: "Your commitments" / "All mine" is Work on the Mine view, with nothing left over from earlier filters or a search, and its
     own address (#work=actions&v=mine) so a refresh, Back and a copied link keep any change made to it */
  if(v==="mine"&&!opt.restore){ clearAllFilters(); shared.WQ=""; SORT.actions=null; shared.WT="actions"; applyView("mine"); v="work"; arg=null; }
  shared.FROMPROJ=(v==="work"&&opt.from)||null;
  cardGroup.close(); menuGroup.close(); tipHide();   /* #215: a hover card, peek or menu does not outlive its page (Today stays in the DOM, hidden) */
  closePanel(true); closeDisp(false); shared.VIEW=v; $$(".view").forEach(s=>s.hidden=true);
  const id={cockpit:"v-cockpit",mine:"v-work"}[v]||"v-"+v; $("#"+id).hidden=false; $("#"+id).scrollTop=0;
  const railKey={cockpit:"projects",mine:"work",help:"settings",person:"people",prep:"today",notes:"projects",minutes:"review",weekly:"projects",clientreport:"projects",reporting:"projects"}[v]||v;   /* BL-286 D: the prep page sits under Today; v2.1.0 P7: the minutes under Review */
  setRailView(railKey);   /* BL-163, BL-319: the sidebar marks the page (through its store) */
  if(v==="mine"){ shared.WT="actions"; applyView("mine"); } if(v==="work"&&!arg) {} if(v==="cockpit") shared.COCK=arg; if(v==="milestones"&&!arg) shared.MSCODE=null; if(v==="person") shared.PERSON=arg; if(v==="notes") shared.NOTECODE=arg;
  if(v==="settings"&&arg) STAB=arg;      /* BL-115: a category, a section or an old tab name */
  ({today:renderToday,projects:renderProjects,people:renderPeople,person:()=>renderPerson(arg),cockpit:()=>renderCockpit(arg),work:renderWork,mine:renderWork,review:renderReview,inbox:renderInbox,files:renderFiles,activity:renderActivity,settings:renderSettings,help:()=>renderHelp(arg),prep:()=>renderPrep(arg),notes:()=>renderNotes(arg),reports:()=>renderReports(arg),reporting:()=>renderReporting(arg,true),minutes:()=>renderMinutes(arg)}[v]||(()=>{}))();
  if(!opt.restore) navWrite(true); return true; })(v,arg,opt);
  if(r!==false&&(v==="files"||v==="inbox")) filesOpened();
  if(r!==false) helpScreenSync();   /* #158: the foot line and the first-visit line are in place with the page, so nothing shifts afterwards */
  tabTitle();
  if(!shared.LOADING){ if(r!==false&&shared.VIEW!==from&&!reduced()){ const el=$$(".view").find(x=>!x.hidden); if(el) anim(el,[{opacity:0,transform:"translateY(4px)"},{opacity:1,transform:"none"}],{duration:200}); mFirst(shared.VIEW); }   /* BL-263: the page fades in */
    const to=mPageOf(shared.VIEW); if(r!==false&&fromPage&&fromPage!==to) mLeave(fromPage);   /* BL-263: last viewed */
    if(v==="review"&&r!==false){ const seen=store.get(SETUPK,{}); if(!seen.review){ seen.review=true; store.set(SETUPK,seen); } } }   /* BL-155 */
  if(v==="milestones"){ if(r!==false&&shared.MSNEXT!==null) shared.MSCODE=shared.MSNEXT; shared.MSNEXT=null; }
    if(r!==false&&v==="milestones"){ setRailView("projects"); renderMilestones(); mvAfter(); tabTitle(); }   /* BL-245 */
  return r; }
/* links from a project page into Work set the project filter; the rail leaves Work's filters as they were */
export const seeAll=(n,what,nav)=>n?`<a href="#" class="seeall" data-nav="${nav}">All ${n} ${what}${n===1?"":"s"} ›</a>`:"";
   /* capture: before row and panel handlers */
export function switchProject(d){ if(shared.VIEW!=="cockpit"||P.length<2) return; const i=P.findIndex(x=>x.code===shared.COCK); go("cockpit",P[(i+d+P.length)%P.length].code); }
export const pLink=code=>code?`<span class="pcode plink" data-proj="${code}" role="link" tabindex="0" title="Open ${esc(pName(code))}">${esc(pName(code))}</span>`:'<span class="pcode">No project</span>';
export function openWork(code,wt,view,extra){ if(navBlocked(()=>openWork(code,wt,view,extra))) return; clearAllFilters(); if(view==="dueor"){ view="open"; extra={st:["Open","Delayed"],due:["overdue","soon"]}; }   /* BL-48 */ if(view==="undated"){ view="open"; extra={st:wt==="raid"?["Open"]:["Open","Delayed"],due:["none"]}; }   /* BL-95 */
  if(view==="urgentonly"){ view="open"; extra={st:["Open"],pr:["Urgent"]}; }   /* BL-77: the Urgent risks figure counts Urgent only; the "Urgent and high" view also holds High */ shared.WT=wt; applyView(view); if(extra){ applyFilters(Object.assign(snapshot(),extra)); syncView(); }   /* BL-190: extra filters sit on top of the view's ([] clears one) */
  PROJF.clear(); if(code) PROJF.add(code); else ((extra&&extra.p)||[]).forEach(c=>PROJF.add(c)); shared.WQ=""; shared.SEL=null; go("work",null,{from:code||null}); }   /* BL-190: no code is every project; BL-264: or the projects in extra.p (Settings › People with several chosen) */
/* BL-231: what this block did at load, run in today's order by src/main.js (piece 0022's place) */
export function bootNav(){
window.addEventListener("popstate",e=>{ if((shared.EDITING&&shared.CUR)||(shared.CURED&&shared.CURED.dirty)){ try{ history.pushState(shared.NAVSTATE,"",hashOf(shared.NAVSTATE)); }catch(x){} if(shared.EDITING&&shared.CUR) shakeEdit(); else askDiscard(()=>history.back()); return; }
  curDrop();
  const old=!e.state&&/^#meeting=/.test(location.hash);   /* v2.1.0 P10: the retired meeting page's address becomes its Prep's or minutes' */
  restoreNav(e.state||parseHash(location.hash)); if(old){ shared.NAVSTATE=navState(); try{ history.replaceState(shared.NAVSTATE,"",hashOf(shared.NAVSTATE)); }catch(x){} } });
document.addEventListener("click",e=>{ const n=e.target.closest("[data-nav]"); if(n){ e.preventDefault(); e.stopPropagation(); const {wt,view,code,extra}=navParse(n.dataset.nav); openWork(code,wt,view,extra); return; }   /* BL-190: an optional fourth part adds filters */
  const pj=e.target.closest("[data-proj]"); if(pj){ e.preventDefault(); e.stopPropagation(); go("cockpit",pj.dataset.proj); return; }
  const sw=e.target.closest("[data-psw]"); if(sw) switchProject(+sw.dataset.psw); },true);
document.addEventListener("keydown",e=>{ if(e.key==="Enter"&&e.target.matches&&e.target.matches("[data-proj][role=link]")){ e.preventDefault(); go("cockpit",e.target.dataset.proj); return; }
  if(e.key==="Enter"&&e.target.matches&&e.target.matches("[data-nav][role=link]")){ e.preventDefault(); const {wt,view,code,extra}=navParse(e.target.dataset.nav); openWork(code,wt,view,extra); } });
document.addEventListener("change",e=>{ if(e.target.id==="projSw"){ const c=e.target.value; if(!go("cockpit",c)) e.target.value=shared.COCK; } });
}
/* ===== BL-190 (sprint-links) ===== every figure that counts work items opens Work on its tab, filtered to exactly those items.
   data-nav="<tab>:<view>:<project code>[:<filters>]": the optional fourth part is key=v1,v2&key2=… (values URI-encoded), the same keys
   applyFilters takes (st, due, o, pr, ty, rr, cr…), laid over the view's. An empty code is every project. countLink draws a figure:
   a link that says what it opens, or plain text when it counts nothing (a zero is never a link). */
export const navEnc=f=>Object.entries(f||{}).map(([k,v])=>`${k}=${[].concat(v).map(x=>encodeURIComponent(x)).join(",")}`).join("&");
export function navParse(s){ const [wt,view,code,...r]=String(s||"").split(":"), x=r.join(":"); let extra=null;
  if(x){ extra={}; x.split("&").forEach(p=>{ const i=p.indexOf("="), k=i<0?p:p.slice(0,i), v=i<0?"":p.slice(i+1); if(k) extra[k]=v===""?[]:v.split(",").map(decodeURIComponent); }); }
  return {wt,view,code:code||"",extra}; }
export const navOf=(nav,extra)=>nav+(extra&&Object.keys(extra).length?":"+navEnc(extra):"");
export const inProj=code=>code?` in ${pName(code)}`:"";
export function countLink(label,n,nav,extra,inner,cls){ const h=inner??String(n);
  return n?`<a href="#" class="cntl${cls?" "+cls:""}" data-nav="${esc(navOf(nav,extra))}" data-n="${n}" aria-label="${esc(label)}, open in Work">${h}</a>`:(cls?`<span class="${cls}">${h}</span>`:h); }
/* a figure whose items Work can't list as one (the Projects table's No date and Slip) opens the project page at the card that lists them */
export const jumpLink=(label,n,code,card,inner)=>n?`<a href="#" class="cntl" data-cockjump="${code}|${card}" aria-label="${esc(label)}, show on the project page">${inner}</a>`:inner;
/* ===== end BL-190 (core) ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js (piece 0023's place) */
export function bootCountLinks(){
document.addEventListener("click",e=>{ const j=e.target.closest&&e.target.closest("[data-cockjump]"); if(!j) return; e.preventDefault(); e.stopPropagation();
  const [code,card]=j.dataset.cockjump.split("|"); if(!go("cockpit",code)) return;
  requestAnimationFrame(()=>{ const el=card==="undated"?$("#undatedCard"):[...document.querySelectorAll("#v-cockpit .card h2")].find(h=>h.textContent.trim().startsWith("Milestones"))?.closest(".card"); if(el) mScroll(el,{block:card==="undated"?"center":"start"}); }); },true);
}

/* BL-231: what this block did at load, run in today's order by src/main.js (piece 0024's place) */
export function bootGoLinks(){
/* BL-163: the rail's buttons are handled by one listener (renderRail, above), as they move and are made again */
document.addEventListener("click",e=>{ const a=e.target.closest("[data-go]"); if(a){ e.preventDefault(); go(a.dataset.go); } });
document.addEventListener("click",e=>{ const a=e.target.closest("[data-rphub]"); if(a){ e.preventDefault(); const [code,week,view]=a.dataset.rphub.split("|"); openSpace(code,week||"",view==="client"||view==="side"?view:"internal"); } });   /* #221: a reminder or a link names a project, a week and a view; the hub opens there */
}
/* ===== BL-152 (sprint-ux) ===== the browser tab says where you are and what is waiting: "creaite · Work", "creaite · <Project
   name>", "creaite · Review (4)" (the count is what waits in Review, not Intake). The finished-run mark (BL-139) and the VIP count
   (BL-99) still go first, and "DEV · " in the development repository. It follows the page, the project or person shown and the count. */
export const TABNAME={today:"Today",inbox:"Intake",projects:"Projects",work:"Work",mine:"Work",reports:"Reports",people:"People",review:"Review",files:"Files",activity:"Activity",settings:"Settings",help:"Help"};
export function tabTitle(){ if(shared.VIEW==="prep"){ const v=prepView.value, t=v&&v.ok&&v.model?v.model.meeting.title:""; TABNAME.prep=t?`Prep · ${t}`:"Prep"; }   /* BL-286 D */
  if(shared.VIEW==="minutes") TABNAME.minutes="Minutes";   /* v2.1.0 P7 */
  const n=REV.filter(r=>!r.done).length, vips=VIPS().length;
  const where=shared.VIEW==="notes"&&shared.NOTECODE?(shared.NOTECODE==="_portfolio"?"Portfolio notes":`${pName(shared.NOTECODE)} notes`):shared.VIEW==="cockpit"&&shared.COCK?pName(shared.COCK):shared.VIEW==="person"&&shared.PERSON?shared.PERSON:shared.VIEW==="reporting"&&spaceCode.value?`${pName(spaceCode.value)} reporting`:TABNAME[shared.VIEW]||"";
  const t=(shared.RBMARKED?RBMARK:"")+(vips?`(${vips}) `:"")+BASETITLE+(where?` · ${where}`:"")+(shared.VIEW==="review"&&n?` (${n})`:"");
  if(document.title!==t) document.title=t; 
  if(shared.VIEW==="milestones"&&shared.MSCODE){ const t=document.title.replace(/ · [^·]*$/,"").replace(/ \(\d+\)$/,"")+` · ${pName(shared.MSCODE)} milestones`; if(document.title!==t) document.title=t; } }   /* BL-245 */
/* ===== end BL-152 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js (piece 0139's place) */
export function bootTabTitle(){
tabTitle();
}
/* ===== BL-153 (sprint-ux) ===== why Work can open on a narrowed list. Investigated: in a fresh browser Work opens on the view
   Settings › Work and views › Opening views names for each tab (work.defaults); the shipped default is All open. The UX review's
   sample vault was copied from the development repository with its local trial settings, where "Actions open with" had been set to
   Overdue, so Work opened there. That is deliberate (Alan's own setting), so nothing changes it; the page now says why the list is
   narrowed when a tab opens on a view other than its first: "Opened on Overdue, as set in Settings · Show all open". The line
   goes as soon as the view is changed, and a view Alan picks himself is never explained. */
export const OPENEDON={};
export function openedNote(){ const el=$("#wapplied"); if(!el) return; el.querySelector(".openedon")?.remove();
  const id=OPENEDON[shared.WT], v=id&&allViews(shared.WT).find(x=>x.id===id), first=allViews(shared.WT)[0];
  if(!v||shared.WVIEW!==id||id===first.id){ if(id&&shared.WVIEW!==id) delete OPENEDON[shared.WT]; return; }
  addHTML(el,"afterbegin",html`<span class="openedon sub">Opened on <b>${v.label}</b>, as set in <a href="#" data-openset>Settings</a> · <button type="button" class="linkbtn" data-openall>Show ${first.label.toLowerCase()}</button></span>`); }
/* ===== end BL-153 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js (piece 0157's place) */
export function bootOpenAll(){
document.addEventListener("click",e=>{ if(e.target.closest("[data-openall]")){ e.preventDefault(); delete OPENEDON[shared.WT]; applyView(allViews(shared.WT)[0].id); workChanged(); }
  else if(e.target.closest("[data-openset]")){ e.preventDefault(); go("settings","views"); } });
}
