// @ts-check
/* core/identity.js (#307 h2): what an item IS on Intake, by its content, never its number. The engine renumbers items inside a
   proposal file (sweep.py) and a file name can be written again, so file + ref alone can name another item. The fingerprint is the
   first 12 hex of a SHA-256 of a canonical JSON of the item's identity-bearing fields. Python twin: system/scripts/item_fp.py
   (the page's rows carry the fingerprint from build_dashboard.py; a test compares both). THE SPEC:
   - canonical JSON: object keys sorted (by code point), array order kept, no spaces; strings NFC-normalised, then JSON-escaped;
   - numbers: an integer is its decimal digits (1.0 and -0 are "1" and "0"; beyond 2^53 the digits of the double); any other number
     is {"f":<floor(x*1e6+0.5)>}; true, false and null as they are; an absent field is null;
   - an item: [op, table, id, changes, values]; a block (minutes, report, file changes): [key, title, draft, project, projects]. */

/** @param {any} x @returns {string} */
export function fpCanon(x){
  if(x===null||x===undefined) return "null";
  if(typeof x==="boolean") return x?"true":"false";
  if(typeof x==="number"){ if(!isFinite(x)) return "null"; if(Number.isInteger(x)) return Math.abs(x)>Number.MAX_SAFE_INTEGER?BigInt(x).toString():String(x===0?0:x);
    return `{"f":${Math.floor(x*1e6+0.5)}}`; }
  if(typeof x==="string") return JSON.stringify(x.normalize("NFC"));
  if(Array.isArray(x)) return "["+x.map(fpCanon).join(",")+"]";
  return "{"+Object.keys(x).sort((a,b)=>cmp(a.normalize("NFC"),b.normalize("NFC"))).map(k=>JSON.stringify(k.normalize("NFC"))+":"+fpCanon(x[k])).join(",")+"}";
}
/* code-point order (Python's), not UTF-16 order */
const cmp=(a,b)=>{ const x=Array.from(a), y=Array.from(b); for(let i=0;i<Math.min(x.length,y.length);i++){ const d=x[i].codePointAt(0)-y[i].codePointAt(0); if(d) return d; } return x.length-y.length; };

/** SHA-256 of a string's UTF-8 bytes, as hex (synchronous: the page's actions are not) @param {string} s */
export function fpSha256(s){
  const K=new Uint32Array(64); { let n=2,i=0; while(i<64){ let p=true; for(let d=2;d*d<=n;d++) if(n%d===0){ p=false; break; } if(p){ K[i++]=Math.floor((Math.cbrt(n)%1)*4294967296); } n++; } }
  const H=new Uint32Array(8); { let n=2,i=0; while(i<8){ let p=true; for(let d=2;d*d<=n;d++) if(n%d===0){ p=false; break; } if(p){ H[i++]=Math.floor((Math.sqrt(n)%1)*4294967296); } n++; } }
  const b=new TextEncoder().encode(s), l=b.length, tot=((l+9+63)>>6)<<6, m=new Uint8Array(tot); m.set(b); m[l]=0x80;
  const dv=new DataView(m.buffer); dv.setUint32(tot-8,Math.floor(l*8/4294967296)); dv.setUint32(tot-4,(l*8)>>>0);
  const w=new Uint32Array(64), rr=(x,n)=>(x>>>n)|(x<<(32-n));
  for(let o=0;o<tot;o+=64){ for(let i=0;i<16;i++) w[i]=dv.getUint32(o+i*4);
    for(let i=16;i<64;i++){ const s0=rr(w[i-15],7)^rr(w[i-15],18)^(w[i-15]>>>3), s1=rr(w[i-2],17)^rr(w[i-2],19)^(w[i-2]>>>10); w[i]=(w[i-16]+s0+w[i-7]+s1)>>>0; }
    let [a,bb,c,d,e,f,g,h]=H;
    for(let i=0;i<64;i++){ const S1=rr(e,6)^rr(e,11)^rr(e,25), ch=(e&f)^(~e&g), t1=(h+S1+ch+K[i]+w[i])>>>0, S0=rr(a,2)^rr(a,13)^rr(a,22), mj=(a&bb)^(a&c)^(bb&c), t2=(S0+mj)>>>0;
      h=g; g=f; f=e; e=(d+t1)>>>0; d=c; c=bb; bb=a; a=(t1+t2)>>>0; }
    H[0]+=a; H[1]+=bb; H[2]+=c; H[3]+=d; H[4]+=e; H[5]+=f; H[6]+=g; H[7]+=h; }
  return Array.from(H,x=>x.toString(16).padStart(8,"0")).join("");
}
const short=x=>fpSha256(fpCanon(x)).slice(0,12);
/** the fingerprint of a staged item (the object in a proposal file's `items`) @param {any} it */
export const itemFp=it=>short([it.op,it.table,it.id,it.changes,it.values]);
/** the fingerprint of a minutes, report or file-changes block (a proposal file's `meeting`, `report`, `file_changes`) @param {any} b */
export const blockFp=b=>short([b.key,b.title,b.draft,b.project,b.projects]);
const BLOCKS=["meeting","report","file_changes"];

/** What a row stands for, taken when the page drew it: {file, ref, fp, row}. A row from an older model has no fp (then only the
    server's changed-file check applies). @param {any} rw */
export const itemGuard=rw=>({file:rw.file,ref:rw.ref,fp:rw.fp||null,rw});
/** The item in the freshly read proposal `data` that the row stands for, or null: the one at its ref if its content matches, else
    the single other item that matches. A row with no fingerprint is trusted at its ref. Sets row.ref to the item's number now.
    @param {any} data @param {any} rw @param {{table:string,id:string}=} same only for an unapproved merge-save of an update: that record */
export function findGuarded(data,rw,same){
  if(BLOCKS.includes(rw.ref)){ const b=data[rw.ref]; return b&&(!rw.fp||blockFp(b)===rw.fp)?b:null; }
  const its=(data.items||[]).filter(i=>i&&typeof i==="object");
  const at=its.find(i=>i.n===rw.ref);
  if(!rw.fp) return at||null;
  if(at&&itemFp(at)===rw.fp) return at;
  const alike=its.filter(i=>itemFp(i)===rw.fp);
  if(alike.length===1){ rw.ref=alike[0].n; return alike[0]; }
  /* a save that only puts right the columns Alan edited (the peek's Save without approving) merges into the file's own `changes`, so
     an update still at its number that updates the same record is the same item even if its other columns moved on (another window) */
  if(same&&at&&at.op==="update"&&at.table===same.table&&at.id===same.id) return at;
  return null;
}
/** after a saved edit the row stands for the item as it now is @param {any} data @param {any} rw */
export function refreshGuard(data,rw){
  if(!rw||!rw.fp) return;
  const it=BLOCKS.includes(rw.ref)?data[rw.ref]:(data.items||[]).find(i=>i&&i.n===rw.ref);
  if(it) rw.fp=BLOCKS.includes(rw.ref)?blockFp(it):itemFp(it);
}
