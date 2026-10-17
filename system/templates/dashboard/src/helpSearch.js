// @ts-check
/* helpSearch.js (#158 Phase B part 1): one search over all of Help, local and instant. The index is built in the page from the
   text Help already holds (D.help.tabs, no new request): every how-to card, every Reference section, each part of Start here and
   each What's new version is a page; its lines are the paragraphs, list items, table cells and headings. Words are matched whole
   or as a prefix, blind to case and accents, and a plural finds the singular. Nothing is sent anywhere. */
export const hnorm=s=>String(s||"").normalize("NFD").replace(/[̀-ͯ]/g,"").toLowerCase();
export const hwords=s=>hnorm(s).match(/[a-z0-9]+/g)||[];
/* a word's stem for plurals: proposals → proposal, categories → category, boxes → box; short words are left alone */
export function hstem(w){ if(w.length<=3) return w; if(w.endsWith("ies")) return w.slice(0,-3)+"y"; if(/(x|ch|sh|ss|zz)es$/.test(w)) return w.slice(0,-2);
  if(w.endsWith("s")&&!/(ss|us|is)$/.test(w)) return w.slice(0,-1); return w; }
/* does a word of the text answer a typed word: equal, or (from two letters) starting with it, plurals folded */
export function hmatch(word,q){ const a=hstem(word), b=hstem(q); return q.length<2?word===q:a.startsWith(b)||word.startsWith(q); }
export const HPARTS={howto:"How do I…",reference:"Reference",start:"Start here",whatsnew:"What's new"};
const POOL=["p","li","td","th","h1","h2","h3"];
/** @type {null|Array<{arg:string,part:string,title:string,lines:string[],words:string[]}>} */
let INDEX=null, INDEXOF=null;
function ownText(el){ const c=el.cloneNode(true); c.querySelectorAll("ul,ol,.hp-arrow,svg").forEach(x=>x.remove()); return c.textContent.replace(/\s+/g," ").trim(); }
function linesOf(root){ const out=[], seen=new Set(); root.querySelectorAll(POOL.join(",")).forEach(el=>{ const t=ownText(el); if(t.length>1&&!seen.has(t)){ seen.add(t); out.push(t); } }); return out; }
/** Build (once per tabs list) the pages of Help from the tabs' HTML. */
export function helpPages(tabs){ if(INDEX&&INDEXOF===tabs) return INDEX; const pages=[], dp=new DOMParser();
  for(const tab of tabs){ const doc=dp.parseFromString(`<div>${tab.html}</div>`,"text/html"), id=tab.id;
    const add=(arg,title,root,part=id)=>{ const lines=linesOf(root); pages.push({arg,part,title,lines,words:hwords(title+" "+lines.join(" "))}); };
    if(id==="howto") doc.querySelectorAll(".hp-task").forEach(a=>add("howto-"+a.getAttribute("data-task"),a.querySelector("h3")?.textContent||"",a));
    else if(id==="reference") doc.querySelectorAll(".hp-ref").forEach(a=>add("reference-"+a.getAttribute("data-ref"),a.querySelector("h2")?.textContent||"",a));
    else if(id==="whatsnew") doc.querySelectorAll(".hp-wn").forEach(a=>add("whatsnew-"+a.getAttribute("data-ver"),"What's new in "+a.getAttribute("data-ver"),a));
    else { const hero=doc.querySelector(".hp-hero"); if(hero) add(id,tab.title,hero);
      doc.querySelectorAll("section").forEach(s=>add(id,s.querySelector("h2")?.textContent||tab.title,s)); } }
  INDEX=pages; INDEXOF=tabs; return pages; }
/** Pages that hold every typed word, best first: {page, line (the best matching line), at (its index), score}. */
export function helpFind(tabs,q){ const qs=hwords(q); if(!qs.length) return []; const out=[];
  for(const p of helpPages(tabs)){ if(!qs.every(w=>p.words.some(x=>hmatch(x,w)))) continue;
    const tw=hwords(p.title), titleHits=qs.filter(w=>tw.some(x=>hmatch(x,w))).length;
    let best=-1, bestN=-1, lineHits=0;
    p.lines.forEach((l,i)=>{ const lw=hwords(l), n=qs.filter(w=>lw.some(x=>hmatch(x,w))).length; if(n) lineHits++; if(n>bestN){ bestN=n; best=i; } });
    const phrase=qs.length>1&&p.lines.some(l=>hnorm(l).includes(hnorm(q).trim()))?6:0;
    out.push({page:p,at:Math.max(best,0),line:p.lines[Math.max(best,0)]||p.title,score:titleHits*8+(titleHits===qs.length?6:0)+bestN*3+Math.min(lineHits,5)+phrase}); }
  return out.sort((a,b)=>b.score-a.score||a.page.title.localeCompare(b.page.title)); }
/** A line as safe HTML with the words that matched marked. */
export function hmark(line,q){ const qs=hwords(q), xe=s=>s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
  let out="", last=0; for(const m of String(line).matchAll(/[\p{L}\p{N}]+/gu)){ const w=hnorm(m[0]); if(qs.some(x=>hmatch(w,x))){ out+=xe(line.slice(last,m.index))+"<mark>"+xe(m[0])+"</mark>"; last=m.index+m[0].length; } }
  return out+xe(line.slice(last)); }
/** A line cut to about 150 characters around its first marked word. */
export function hsnip(line,q,n=150){ if(line.length<=n) return line; const qs=hwords(q); let at=0;
  for(const m of line.matchAll(/[\p{L}\p{N}]+/gu)){ if(qs.some(x=>hmatch(hnorm(m[0]),x))){ at=m.index; break; } }
  const a=Math.max(0,at-50), cut=line.slice(a,a+n); return (a>0?"…":"")+cut+(a+n<line.length?"…":""); }
