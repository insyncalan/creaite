// @ts-check
/* core/data.js (BL-231 step 2b): the tracker's data (`P`, `A`, `R`, `DEC`, `REV`, `ACT`), people and workstreams.
   Moved from script/ unchanged, apart from `export`, `shared.` for the shared state (state.js) and the steps that ran at load,
   which are now boot…() functions called by src/main.js in today's order. Pieces: 0010-data-from-tracker-db-system-staging-and.js */
import { D, days, fdMd, fdText, isMe, OPENST, prio, S, store, TODAY } from "./page.js";
import { writeSettings } from "./server.js";
import { shared } from "./state.js";
import { isHiddenPerson, resolver, WSD, wsTable } from "../settings.js";
/* ======================= data (from tracker.db, system/staging/ and the vault; see build_dashboard.py) ======================= */
export const P=D.projects, A=D.actions, R=D.raid, DEC=D.decisions, REV=D.review, FILES=D.files, REMINDERS=D.reminders;
shared.ACT=D.activity;
export const pName=c=>(P.find(p=>p.code===c)||{}).name||c;
export const LASTVISIT=store.get("creaite-lastvisit",D.data_at); 
export const SWEPT=D.last_sweep||"never";
export const WEEKSTART=(()=>{ const d=new Date(TODAY); d.setDate(d.getDate()-((d.getDay()+6)%7)); return d.toISOString().slice(0,10); })();
export const PEOPLE=D.people||{added:[],hidden:[]}, REGD=D.people_register||{exists:false,path:"projects/_portfolio/people-register.md",people:[],template:""}, WSL=store.get("creaite-ws",D.workstreams||{added:[],hidden:[]});
shared.REG=REGD.people.map(p=>({...p,extra:{}}));   /* BL-55: the people register; PEOPLE is only the old settings.json lists, until "setup" moves them */
export const saveWs=()=>{ store.set("creaite-ws",WSL); writeSettings({"workstreams.added":WSL.added,"workstreams.hidden":WSL.hidden}); };
export const peopleAll=()=>{ const rs=resolver(), s=new Set(); [...A.map(a=>a.o),...R.map(r=>r.o),...DEC.map(d=>d.by),...shared.REG.map(p=>p.name),...PEOPLE.added].forEach(n=>{ if(n&&n!=="TBC") s.add(rs(n).name||n); }); return [...s].filter(n=>!isHiddenPerson(n)).sort((a,b)=>isMe(a)?-1:isMe(b)?1:a.localeCompare(b)); };
export const useCount=n=>{ const rs=resolver(), is=o=>(rs(o).name||o)===n; return A.filter(a=>is(a.o)).length+R.filter(r=>is(r.o)).length; };
/* BL-57: workstreams belong to their project. Settings keeps "CODE|name" keys; a plain name (from before) counts everywhere */
export const wsKey=(p,n)=>`${p}|${n}`, wsParts=k=>{ const i=k.indexOf("|"); return i<0?[null,k]:[k.slice(0,i),k.slice(i+1)]; };
export const wsHidden=(p,n)=>WSL.hidden.includes(wsKey(p,n))||WSL.hidden.includes(n);
export const wsUsed=()=>[...new Set([...A,...R].filter(x=>x.ws).map(x=>wsKey(x.p,x.ws)))];
export const wsFor=code=>!code?[]:wsTable()?WSD().filter(w=>w.p===code&&w.st==="Active").map(w=>w.name).sort((a,b)=>a.localeCompare(b)):[...new Set([...[...A,...R].filter(x=>x.p===code&&x.ws).map(x=>x.ws),...WSL.added.filter(k=>k.startsWith(code+"|")).map(k=>wsParts(k)[1])])].filter(n=>!wsHidden(code,n)).sort();   /* BL-58: the table */
export const open=x=>OPENST(x.st), overdue=x=>open(x)&&x.due&&x.due<TODAY, soon=x=>open(x)&&x.due&&x.due>=TODAY&&days(x.due)<=S.dueSoon;
/* Open only (Alan, 11-10-2026): Work's All open, Mine, Due soon and Chase list status Open, Delayed has its own view. A figure that says
   "open" and opens one of those views counts openOnly; a figure by date (overdue, due soon, due or overdue, no due date) counts
   Open and Delayed, and its link carries st=Open,Delayed (the Overdue view already does), so Work lists exactly that many. */
export const openOnly=x=>x.st==="Open";
/* BL-231: what this block did at load, run in today's order by src/main.js (piece 0010's place) */
export function bootData(){
R.forEach(r=>r.pr=prio(r.imp,r.lik));
store.set("creaite-lastvisit",`${TODAY} ${new Date().toTimeString().slice(0,5)}`);
/* text written with ISO dates is shown DD-MM-YYYY (file names untouched) */
(()=>{ const conv=o=>["t","upd","resp","cm","cmd","reason","current"].forEach(k=>{ if(typeof o[k]==="string") o[k]=(k==="current"?fdMd:fdText)(o[k]); });
  [...A,...R,...DEC,...P].forEach(conv); REV.forEach(r=>{ conv(r.rec); }); shared.ACT.forEach(a=>a.what=fdText(a.what)); })();
}
