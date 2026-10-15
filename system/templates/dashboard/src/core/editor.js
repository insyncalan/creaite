// @ts-check
/* ===== BL-301 A (v2.0.0) ===== the one editor. Every place the dashboard edits text in place uses creaiteEditor(): Tiptap 3
   (ProseMirror), vendored and pinned (system/templates/vendor/tiptap/, built from dev/tiptap/ by dev/tools/tiptap.py), with
   its Markdown extension (beta upstream, so pinned) and creaite's exact writer (dev/tiptap/writer.js).

   Two kinds of text:
   - "current" (Markdown: Current state's panes). Loaded with Tiptap's Markdown parser, which keeps each text's written form,
     and saved by the exact writer: what was read is written back byte for byte (the round-trip gate,
     dev/tools/tiptap_roundtrip.py, checks every Current state in the sample vault and the fixtures; test_one_editor_gate).
     A text nobody changed is given back as it came, whatever the writer would say. What the document can't hold (the line
     ending, the blank lines around the text) is kept around it (envelope). HTML comments stay, hidden while editing.
   - "plain" (plain text: the peek's text fields, Prep's notes). Paragraphs only, one a line: no Markdown, no marks, so the
     stored text stays plain text, as every other screen and report shows it. `multiline: false` makes a one-line field.

   The editable element is the element given (ProseMirror mounts on it), so its id, classes, data-… and aria-… stay, and the
   code and tests that find it by them keep working. Each change to the document fires an "input" event on it, as typing in
   a contenteditable always did, so the places' own handlers (dirty flags, staging) are unchanged. Undo and redo are the
   editor's own (⌘Z, ⌘⇧Z); the places keep their own keys (⌘↵, Esc) and save paths. */
import { createEditor, envelope, wrap, markdownOf, Mark, mergeAttributes, Plugin, PluginKey } from "tiptap";
import { addHTML, ic, raw } from "./dom.js";
import { shared } from "./state.js";

/** A transaction with this meta changes the document without counting as an edit (claim marks put on as it opens). */
export const ED_QUIET="cxQuiet";

/* BL-207's sentence marks, as a ProseMirror mark: <span class="claim" data-c="n">. Never written: the Markdown has no claims
   (edMarkdown drops them first). Its painting (classes, title) is the page's (claimPaint), so a change to those attributes
   is not an edit. */
export const ClaimMark=Mark.create({ name:"claim", inclusive:false, excludes:"",
  addAttributes(){ return { c:{ default:null, parseHTML:el=>el.getAttribute("data-c"), renderHTML:a=>a.c==null?{}:{"data-c":String(a.c)} } }; },
  parseHTML(){ return [{ tag:"span.claim[data-c]" }]; },
  renderHTML({ HTMLAttributes }){ return ["span", mergeAttributes({ class:"claim" }, HTMLAttributes), 0]; },
  addProseMirrorPlugins(){ return [new Plugin({ key:new PluginKey("cxClaimView"), props:{ markViews:{ claim:mark=>{ const dom=document.createElement("span"); dom.className="claim";
    if(mark.attrs.c!=null) dom.dataset.c=String(mark.attrs.c); return { dom, ignoreMutation:m=>m.type==="attributes" }; } } } })]; } });

/* BL-63's pictures: the image node shown as creaite's figure (figure.cimg, the picture, an editable caption that is the
   image's alt text, and × to remove it). `src(ref)` gives the picture for its reference (images/x.png, or new:<id>). */
function figureView(src){ return ({ node, getPos, editor })=>{ let cur=node;
  const fig=document.createElement("figure"); fig.className="cimg"; fig.contentEditable="false"; fig.dataset.ref=cur.attrs.src||"";
  const pic=()=>{ const s=src?src(cur.attrs.src||""):null; if(s){ const i=document.createElement("img"); i.src=s; i.alt=cur.attrs.alt||""; return i; }
    const d=document.createElement("div"); d.className="sub"; d.textContent=`Image not found: ${cur.attrs.src||""}`; return d; };
  let shown=pic(); fig.appendChild(shown);
  const cap=document.createElement("figcaption"); cap.contentEditable="true"; cap.setAttribute("aria-label","Caption"); cap.textContent=cur.attrs.alt||""; fig.appendChild(cap);
  const del=document.createElement("button"); del.type="button"; del.className="cimgdel"; del.setAttribute("aria-label","Remove image"); del.title="Remove image";
  addHTML(del,"beforeend",raw(ic("x")));
  fig.appendChild(del);
  cap.addEventListener("input",()=>{ const p=getPos(); if(typeof p!=="number") return; const alt=cap.textContent.replace(/\s+/g," ");
    editor.view.dispatch(editor.state.tr.setNodeMarkup(p,undefined,{ ...cur.attrs, alt })); });
  /** removes the picture from the document (the × button) */
  fig.cxRemove=()=>{ const p=getPos(); if(typeof p==="number") editor.view.dispatch(editor.state.tr.delete(p,p+cur.nodeSize)); };
  return { dom:fig,
    update:n=>{ if(n.type!==cur.type) return false; const was=cur; cur=n; fig.dataset.ref=n.attrs.src||"";
      if(n.attrs.src!==was.attrs.src){ const p=pic(); shown.replaceWith(p); shown=p; } else if(shown.tagName==="IMG") shown.setAttribute("alt",n.attrs.alt||"");
      if(document.activeElement!==cap&&cap.textContent!==(n.attrs.alt||"")) cap.textContent=n.attrs.alt||""; return true; },
    stopEvent:e=>!!(e.target instanceof Element&&e.target.closest("figcaption,.cimgdel")),
    ignoreMutation:()=>true }; }; }

/** The Markdown of a document's JSON with the claim marks taken out (the exact writer writes only what Markdown holds). */
function dropClaims(json){ if(!json||typeof json!=="object") return json; const out={ ...json };
  if(out.marks){ out.marks=out.marks.filter(m=>m.type!=="claim"); if(!out.marks.length) delete out.marks; }
  if(out.content) out.content=out.content.map(dropClaims); return out; }

/* #122: Current state's heading levels. The editor has Heading 1 to 3; Current state's text is read to the next `## ` line, so it
   writes them `###`, `####`, `#####` (`headShift` 2: Alan, 15-10-2026). These map a Markdown text between the two, line by line,
   leaving fenced code alone. Only the levels the mapping owns move: on the way in `###` to `#####`, on the way out `#` to `###`. */
/** @param {string} md @param {(level: number) => number} to @returns {string} */
function mapHeads(md,to){ let fence=false;
  return String(md).split("\n").map(line=>{ if(/^\s*(```|~~~)/.test(line)){ fence=!fence; return line; } if(fence) return line;
    const m=/^(#{1,6})([ \t].*|)$/.exec(line); if(!m) return line; const n=to(m[1].length); return n===m[1].length?line:"#".repeat(n)+m[2]; }).join("\n"); }
/** A stored text into the editor's levels (headShift 2: `###` `####` `#####` become 1 2 3). @param {string} md @param {number} shift */
export const headsIn=(md,shift)=>shift?mapHeads(md,n=>n>shift&&n<=shift+3?n-shift:n):md;
/** The editor's Markdown into the stored levels (1 2 3 become `###` `####` `#####`). @param {string} md @param {number} shift */
export const headsOut=(md,shift)=>shift?mapHeads(md,n=>n<=3?n+shift:n):md;

/** Plain text as a document: one paragraph a line. */
const plainDoc=t=>({ type:"doc", content:String(t??"").split("\n").map(l=>l?{ type:"paragraph", content:[{ type:"text", text:l }] }:{ type:"paragraph" }) });
/** A document's plain text: its paragraphs, one a line. */
const plainText=doc=>{ const L=[]; doc.forEach(p=>{ L.push(p.textContent); }); return L.join("\n"); };

/**
 * BL-301 D: AI on selected text. `place` chooses the options (edit_ai.py PLACES: "current", "plain", "notes", "email");
 * `project()` the project's code (its name, people and open item IDs go with the text); `confidential()` true makes the page ask
 * once (per `key()`) before the text goes to Claude.
 * @typedef {{place: string, project?: () => string, confidential?: () => boolean, key?: () => string}} EdAi
 * @typedef {{features?: "current"|"plain"|"notes", markdown?: string, html?: string, text?: string, multiline?: boolean,
 *   imageSrc?: (ref: string) => (string|null|undefined), editorProps?: object, extensions?: any[], prop?: "textContent"|"value",
 *   ai?: EdAi, headShift?: number}} EdOptions
 * @typedef {{el: HTMLElement, editor: any, features: string, multiline?: boolean, headShift: number, value: () => string, setValue: (v: string) => void,
 *   touched: () => boolean, focus: (at?: any) => void, destroy: () => void}} EdHandle
 */
/**
 * The one editor on `el` (BL-301 A). `el` itself becomes the editable root.
 * @param {HTMLElement} el @param {EdOptions} [o] @returns {EdHandle}
 */
export function creaiteEditor(el,o={}){ const features=o.features||"current", plain=features==="plain", multiline=o.multiline!==false, headShift=plain?0:(o.headShift|0);
  if(/** @type {any} */ (el).cxed) /** @type {any} */ (el).cxed.destroy();
  let orig="", env=null, touched=false;
  const load=v=>{ touched=false;
    if(plain){ orig=String(v??""); return { json:plainDoc(orig) }; }
    if(o.html!==undefined&&v===undefined){ orig=null; return { html:o.html }; }
    orig=String(v??""); env=envelope(orig); return { markdown:headsIn(env.inner,headShift) }; };
  const content=load(plain?o.text:o.markdown);
  const props={ ...(o.editorProps||{}),
    handleKeyDown:(view,e)=>{ if(!multiline&&e.key==="Enter") return true; const f=/** @type {any} */ (o.editorProps||{}).handleKeyDown; return f?f(view,e):false; },
    ...(plain?{ transformPastedText:t=>multiline?t.replace(/\r\n?/g,"\n"):t.replace(/\s*[\r\n]+\s*/g," ") }:{}) };
  const editor=createEditor({ mount:el },{ features, ...content, injectCSS:false, editorProps:props,
    extensions:list=>{ const out=list.map(x=>x&&x.name==="image"?x.extend({ addNodeView:()=>figureView(o.imageSrc) }):x);
      return [...out,...(plain?[]:[ClaimMark]),...(o.extensions||[])]; } });
  const blank=()=>{ el.classList.toggle("blank",editor.isEmpty); };
  editor.on("transaction",({ transaction:tr })=>{ if(!tr.docChanged) return; blank(); if(tr.getMeta(ED_QUIET)) return; touched=true;
    el.dispatchEvent(new Event("input",{ bubbles:true })); });
  blank();
  /** @type {EdHandle} */
  const h={ el, editor, features, multiline, headShift,
    value:()=>{ if(!touched&&orig!==null) return orig;
      if(plain) return plainText(editor.state.doc);
      const md=headsOut(markdownOf(editor,dropClaims(editor.getJSON())).markdown,headShift); return env?wrap(env,md):md; },
    setValue:v=>{ const c=load(v); editor.chain().setMeta(ED_QUIET,true).setMeta("addToHistory",false)
      .setContent(c.json??c.html??c.markdown,{ emitUpdate:false, ...(c.markdown!==undefined?{ contentType:"markdown" }:{}) }).run(); touched=false; blank(); },
    touched:()=>touched,
    focus:at=>{ editor.commands.focus(at??null); },
    destroy:()=>{ if(o.prop) delete /** @type {any} */ (el)[o.prop]; try{ editor.destroy(); }catch(e){ /* already gone with its page */ }
      if(/** @type {any} */ (el).cxed===h) delete /** @type {any} */ (el).cxed; } };
  /** @type {any} */ (el).cxed=h;
  if(o.ai&&ED_HOOKS.ai) ED_HOOKS.ai(h,o.ai);      /* BL-301 D: the AI bar over a selection (components/AiSelect.jsx) */
  /* `prop` (a plain field that code reads and sets by a property, as the peek's do by textContent and Prep's by value, as
     its textarea had): that property of the element is the field's text, its lines joined by "\n", and setting it sets the
     text quietly (not an edit: setting a field's text by code never was) */
  if(o.prop&&plain){ const proto=o.prop==="textContent"?Object.getOwnPropertyDescriptor(Node.prototype,"textContent"):null;
    Object.defineProperty(el,o.prop,{ configurable:true,
      get(){ return !editor.isDestroyed?h.value():proto?proto.get.call(el):""; },
      set(v){ if(!editor.isDestroyed) h.setValue(String(v??"")); else if(proto) proto.set.call(el,v); } }); }
  return h; }

/** The editor on `el` (or the element holding it), if there is one. @param {any} el @returns {EdHandle|null} */
export const edOf=el=>{ const r=el&&el.closest?el.closest(".ProseMirror"):null; return (r&&r.cxed)||(el&&el.cxed)||null; };
/** The text of an editable field: its editor's value (Markdown or plain text), else the element's own text. @param {any} el */
export const edValue=el=>{ const h=edOf(el); return h?h.value():(el?el.textContent:""); };
/** Set an editable field's text, quietly (not an edit, not undoable): its editor's, else the element's. @param {any} el @param {string} v */
export function edSet(el,v){ const h=edOf(el); if(h) h.setValue(v); else if(el) el.textContent=v; }
/** Put claim marks (BL-207) on text the document already holds, quietly: `runs` are [text node, from, to, n] in the editor's own
   DOM (as the sentence finder walks it). The text and its written form are unchanged. @param {any} el @param {any[]} runs */
export function edClaim(el,runs){ const h=edOf(el); if(!h||!runs.length) return false; const ed=h.editor, view=ed.view, type=ed.schema.marks.claim; let tr=ed.state.tr;
  for(const [node,x,y,n] of runs){ let a, b; try{ a=view.posAtDOM(node,x); b=view.posAtDOM(node,y); }catch(e){ continue; } if(b>a) tr=tr.addMark(a,b,type.create({ c:String(n) })); }
  view.dispatch(tr.setMeta(ED_QUIET,true).setMeta("addToHistory",false)); return true; }
/** Current state's editing ends: its two editors are destroyed and shared.CURED cleared (the one way it is cleared). */
export function curDrop(){ const c=shared.CURED; if(c){ for(const k of ["ed1","ed2"]) if(c[k]){ c[k].destroy(); c[k]=null; } } shared.CURED=null; }
/* ===== end BL-301 A ===== */

/* ===== BL-301 D (v20-ai-select) ===== AI on selected text: what an editor's selection holds, and putting a suggestion in its
   place as one transaction (one ⌘Z undoes it). The AI bar itself is components/AiSelect.jsx, which sets ED_HOOKS.ai at boot, so
   the core imports no component. */
/** @type {{ai: null | ((h: EdHandle, ai: EdAi) => void)}} */
export const ED_HOOKS={ ai:null };
/**
 * A range of an editor as the AI sees it. Inside one paragraph (or heading, or list line) it is that run of text (`inline`);
 * across paragraphs it widens to the whole blocks it touches, so a reply of whole blocks replaces whole blocks. A rich editor's
 * text is Markdown (by the exact writer, claim marks taken out); a plain one's is its lines.
 * @typedef {{from: number, to: number, text: string, inline: boolean}} EdRange
 * @param {EdHandle} h @param {number} from @param {number} to @returns {EdRange|null}
 */
export function edRange(h,from,to){ const ed=h.editor, doc=ed.state.doc; if(to<=from) return null;
  if(h.features==="plain"){ const text=doc.textBetween(from,to,"\n"); return text.trim()?{ from, to, text, inline:false }:null; }
  const $f=doc.resolve(from), $t=doc.resolve(to);
  if($f.sameParent($t)&&$f.parent.isTextblock){ const cut=$f.parent.cut($f.parentOffset,$t.parentOffset);
    const json={ type:"doc", content:[{ type:"paragraph", ...(cut.content.size?{ content:cut.content.toJSON() }:{}) }] };
    const text=headsOut(markdownOf(ed,dropClaims(json)).markdown,h.headShift); return text.trim()?{ from, to, text, inline:true }:null; }
  const a=$f.depth?$f.before(1):from, b=$t.depth?$t.after(1):to;
  const text=headsOut(markdownOf(ed,dropClaims({ type:"doc", content:doc.slice(a,b).content.toJSON() })).markdown,h.headShift);
  return text.trim()?{ from:a, to:b, text, inline:false }:null; }
/** The editor's selection as an EdRange, or null when nothing (or only spaces) is selected. @param {EdHandle} h */
export const edSelection=h=>{ const s=h.editor.state.selection; return s.empty?null:edRange(h,s.from,s.to); };
/**
 * Put `text` (Markdown for a rich editor, lines for a plain one) in place of `r`, as one undoable transaction. False when the
 * range no longer holds what it held (the text was edited since): nothing is changed then.
 * @param {EdHandle} h @param {EdRange} r @param {string} text @returns {boolean}
 */
export function edReplace(h,r,text){ const ed=h.editor; if(ed.isDestroyed) return false;
  const now=r.to<=ed.state.doc.content.size?edRange(h,r.from,r.to):null; if(!now||now.text!==r.text) return false;
  let content;
  if(h.multiline===false) text=String(text).replace(/\s*[\r\n]+\s*/g," ").trim();   /* a one-line field stays one line (the peek's title) */
  if(h.features==="plain"){ const L=String(text).replace(/\r\n?/g,"\n").split("\n"); content=L.length===1?(L[0]?[{ type:"text", text:L[0] }]:[]):plainDoc(L.join("\n")).content; }
  else { const blocks=(ed.schema.nodeFromJSON(ed.markdown.parse(headsIn(String(text),h.headShift))).toJSON().content)||[];
    content=r.inline&&blocks.length===1&&blocks[0].type==="paragraph"?(blocks[0].content||[]):blocks; }
  const chain=ed.chain().focus();
  return (content.length?chain.insertContentAt({ from:r.from, to:r.to },content,{ updateSelection:true }):chain.deleteRange({ from:r.from, to:r.to })).run(); }
/* ===== end BL-301 D ===== */
