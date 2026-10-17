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
import { createEditor, envelope, wrap, markdownOf, Extension, Mark, mergeAttributes, Plugin, PluginKey } from "tiptap";
import { addHTML, ic, raw } from "./dom.js";
import { shared } from "./state.js";
import { linkGuard, pasteLink, scrubNow } from "./editorLink.js";
import { isLinkUrl, linkUrl } from "./linkUrl.js";
import { linkSegments, linkWrite } from "./linkText.js";

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
   and the mapping is reversible (an untouched line comes out as it went in):
   - in:  stored `###` `####` `#####` become `#` `##` `###` (the editor's 1 to 3); every other line that starts with 1 to 6 `#` and a
          space (stored `#`, `##`, `######`) is kept as plain text by putting a zero-width space (U+200B) before the first `#`, so the
          editor shows a paragraph with a visible literal `# `; a line that already starts with U+200B and `#` gets one more;
   - out: the editor's `#` `##` `###` become `###` `####` `#####`; a typed level above 3 is clamped to `#####` (the editor is limited to
          three levels as well, see the `extensions` in creaiteEditor); one U+200B is taken off a line that starts with U+200B and `#`.
   Fenced code and HTML comments (a `# ` line inside either is text, not a heading) are left alone. */
/*HEADS-BEGIN*/
/** @param {string} md @param {(zw: string, level: number, rest: string) => string} to @returns {string} */
function mapHeads(md,to){ let fence=false, comment=false;
  return String(md).split("\n").map(line=>{
    if(comment){ if(line.includes("-->")) comment=false; return line; }
    if(/^\s*(```|~~~)/.test(line)){ fence=!fence; return line; } if(fence) return line;
    if(line.includes("<!--")&&!line.slice(line.indexOf("<!--")+4).includes("-->")){ comment=true; return line; }
    const m=/^((?:> {0,4}|>\t)*)(\u200B*)(#{1,6})([ \t].*|)$/.exec(line); return m?m[1]+to(m[2],m[3].length,m[4]):line; }).join("\n"); }   /* a heading in a quote (`> # x`, `> > # x`) is shifted too: the quote prefix stays as it is; after each `>` the editor reads a heading with up to four spaces or one tab (more is code, and is left alone) */
/** A stored text into the editor's levels (headShift 2: `###` `####` `#####` become 1 2 3; other `#` lines stay literal text).
    @param {string} md @param {number} shift */
export const headsIn=(md,shift)=>shift?mapHeads(md,(z,n,rest)=>z===""&&n>shift&&n<=shift+3?"#".repeat(n-shift)+rest:"\u200B"+z+"#".repeat(n)+rest):md;
/** The editor's Markdown into the stored levels (1 2 3 become `###` `####` `#####`; above 3 is clamped to `#####`).
    @param {string} md @param {number} shift */
export const headsOut=(md,shift)=>shift?mapHeads(md,(z,n,rest)=>z!==""?z.slice(1)+"#".repeat(n)+rest:"#".repeat(Math.min(n,3)+shift)+rest):md;
/*HEADS-END*/
/** #117: a suggestion (or any text) about to be written into a host that stores its headings shifted (Current state, `headShift` 2) never holds a
    `# ` or `## ` line: those would be written back as they are, and a `## ` line ends the `## Current state` section. They become `###` and `####`
    (the shift is added), so a stray `##` from the AI lands as `####`. A line already shifted (`###` and deeper), a literal one (U+200B first) and
    fenced code are left alone. @param {string} md @param {number} shift */
export const headsSafe=(md,shift)=>shift?mapHeads(md,(z,n,rest)=>z===""&&n<=shift?"#".repeat(n+shift)+rest:z+"#".repeat(n)+rest):md;

/** Plain text as a document: one paragraph a line. With `links` (#121) a `[words](address)` whose address core/linkUrl.js accepts is a link mark on the
    words; the same text with any other address stays the literal characters it is. */
const plainDoc=(t,links)=>({ type:"doc", content:String(t??"").split("\n").map(l=>{ if(!l) return { type:"paragraph" };
  if(!links) return { type:"paragraph", content:[{ type:"text", text:l }] };
  const segs=linkSegments(l).map(x=>x.href?{ type:"text", text:x.t, marks:[{ type:"link", attrs:{ href:linkUrl(x.href) } }] }:{ type:"text", text:x.t });
  return segs.length?{ type:"paragraph", content:segs }:{ type:"paragraph" }; }) });
/** A document's plain text: its paragraphs, one a line; a link written `[words](address)` (#121). */
const plainText=doc=>{ const L=[]; doc.forEach(p=>{ let line=""; p.forEach(c=>{ const m=c.isText&&c.marks.find(x=>x.type.name==="link"); const w=m?linkWrite(c.text,m.attrs.href):null; line+=w??c.textContent; }); L.push(line); }); return L.join("\n"); };
/** #121: the link mark of a plain-text field. The address is shown only if core/linkUrl.js accepts it (an anchor with none is inert text). It is the
    mark core/editorLink.js and components/LinkPopover.jsx act on, so a plain field has the very same link as a rich one, stored as `[words](address)`. */
const PlainLink=Mark.create({ name:"link", inclusive:false, excludes:"link",
  addAttributes(){ return { href:{ default:null } }; },
  parseHTML(){ return [{ tag:"a[href]", getAttrs:el=>{ const h=/** @type {HTMLElement} */ (el).getAttribute("href"); return isLinkUrl(h)?{ href:linkUrl(h) }:false; } }]; },
  renderHTML({ HTMLAttributes }){ const h=HTMLAttributes.href; return ["a", isLinkUrl(h)?{ class:"tlink", href:linkUrl(h), target:"_blank", rel:"noopener noreferrer" }:{ class:"tlink" }, 0]; } });
/* ===== #133 ===== the Email feature set: Draft email's preview (drafts.js #dePrev) as a host of the one editor. The email is HTML for Outlook
   (inline styles, a table of actions, coloured spans). The document keeps what the builder wrote beside the content, so an edit
   brings the styles along: every block carries its `style` (and the table's align, cellpadding, cellspacing, border and width) as
   attributes, and a coloured run is the `emailSpan` mark. Nothing here is Markdown: the builder (drafts.js draftEmail) stays the source,
   an unedited email is copied from the builder and only an edited one is written from this document (drafts.js deHtml). */
/** The attributes an email's blocks keep as written. */
const EMAIL_ATTRS = ["style", "align", "cellpadding", "cellspacing", "border", "width", "valign", "bgcolor"];
const EmailStyles = Extension.create({ name: "emailStyles",
  addGlobalAttributes(){ return [{ types:["paragraph","table","tableRow","tableCell","tableHeader"],
    attributes:Object.fromEntries(EMAIL_ATTRS.map(a=>[a,{ default:null, parseHTML:el=>el.getAttribute(a),
      renderHTML:v=>v[a]==null?{}:a==="style"?{ style:v.style, "data-cx-style":v.style }:{ [a]:v[a] } }])) }]; } });   /* Tiptap rewrites a style through the CSSOM (rgb(), spaces): the text as written rides in data-cx-style and is put back on copy */
/** A run with its own inline style (the muted grey and the red or amber of a due date): <span style="color:…">. */
const EmailSpan = Mark.create({ name:"emailSpan", inclusive:false,
  addAttributes(){ return { style:{ default:null, parseHTML:el=>el.getAttribute("style"), renderHTML:a=>a.style?{ style:a.style, "data-cx-style":a.style }:{} } }; },
  parseHTML(){ return [{ tag:"span[style]" }]; },
  renderHTML({ HTMLAttributes }){ return ["span", HTMLAttributes, 0]; } });
/** The extensions an email keeps from the notes set (everything else, Markdown included, is left out: typing `# ` or `- ` in an email
    must not start a heading or a list; a pasted list or heading is flattened to paragraphs). @param {any[]} list @returns {any[]} */
const emailSet = list => list.filter(x => x && ["starterKit","bold","italic","hardBreak","tableKit","table"].includes(x.name))
  .map(x => x.name === "starterKit" ? x.configure({ heading:false, blockquote:false, codeBlock:false, horizontalRule:false, strike:false, code:false,
    bold:false, italic:false, link:false, hardBreak:false, bulletList:false, orderedList:false, listItem:false, listKeymap:false, trailingNode:false }) : x)
  .concat([EmailStyles, EmailSpan]);
/** An email document as the HTML an email client takes: the editor's own HTML, a cell's lone paragraph unwrapped (the builder wrote the
    cell's text directly, and a paragraph's margin would grow every row), the editor's marks (strong) kept. @param {any} editor @returns {string} */
export function edEmailHtml(editor){ try{ editor.view.domObserver.flush(); }catch(e){ /* nothing pending */ }
  const t=new DOMParser().parseFromString(editor.getHTML(),"text/html").body;   /* parsed, never set into the page */
  t.querySelectorAll("[data-cx-style]").forEach(e=>{ e.setAttribute("style",e.getAttribute("data-cx-style")); e.removeAttribute("data-cx-style"); });
  t.querySelectorAll("colgroup").forEach(e=>e.remove());       /* the editor's column widths: the builder's table has none */
  t.querySelectorAll('[colspan="1"],[rowspan="1"]').forEach(e=>{ if(e.getAttribute("colspan")==="1") e.removeAttribute("colspan"); if(e.getAttribute("rowspan")==="1") e.removeAttribute("rowspan"); });
  t.querySelectorAll("td,th").forEach(c=>{ const k=c.children; if(k.length===1&&k[0].tagName==="P"&&!k[0].getAttribute("style")&&c.childNodes.length===1) k[0].replaceWith(...k[0].childNodes); });
  return t.innerHTML; }
/* ===== end #133 ===== */

/**
 * BL-301 D: AI on selected text. `place` chooses the options (edit_ai.py PLACES: "current", "plain", "notes", "email");
 * `project()` the project's code (its name, people and open item IDs go with the text); `confidential()` true makes the page ask
 * once (per `key()`) before the text goes to Claude.
 * @typedef {{place: string, project?: () => string, confidential?: () => boolean, key?: () => string,
 *   document?: () => ({kind: string, code: string, week_ending: string, client: string}|null)}} EdAi
 * @typedef {{features?: "current"|"plain"|"notes"|"email", markdown?: string, html?: string, text?: string, multiline?: boolean,
 *   imageSrc?: (ref: string) => (string|null|undefined), editorProps?: object, extensions?: any[], prop?: "textContent"|"value",
 *   ai?: EdAi, headShift?: number, links?: boolean}} EdOptions
 * @typedef {{el: HTMLElement, editor: any, features: string, links?: boolean, multiline?: boolean, headShift: number, value: () => string, setValue: (v: string) => void,
 *   touched: () => boolean, focus: (at?: any) => void, destroy: () => void}} EdHandle
 */
/**
 * The one editor on `el` (BL-301 A). `el` itself becomes the editable root.
 * @param {HTMLElement} el @param {EdOptions} [o] @returns {EdHandle}
 */
export function creaiteEditor(el,o={}){ const features=o.features||"current", plain=features==="plain", email=features==="email", links=!email&&(!plain||!!o.links), multiline=o.multiline!==false, headShift=plain||email?0:(o.headShift|0);
  if(/** @type {any} */ (el).cxed) /** @type {any} */ (el).cxed.destroy();
  let orig="", env=null, touched=false;
  const load=v=>{ touched=false;
    if(plain){ orig=String(v??""); return { json:plainDoc(orig,links) }; }
    if(email){ orig=String(v??o.html??""); return { html:orig }; }       /* #133: the builder's HTML is the source; value() gives it back until the email is edited */
    if(o.html!==undefined&&v===undefined){ orig=null; return { html:o.html }; }
    orig=String(v??""); env=envelope(orig); return { markdown:headsIn(env.inner,headShift) }; };
  const content=load(plain?o.text:email?o.html:o.markdown);
  const props={ ...(o.editorProps||{}),
    handleKeyDown:(view,e)=>{ if(!multiline&&e.key==="Enter") return true; const f=/** @type {any} */ (o.editorProps||{}).handleKeyDown; return f?f(view,e):false; },
    ...(links?{ handlePaste:(view,e)=>{ if(pasteLink(editor,/** @type {ClipboardEvent} */ (e),(m,u)=>{ if(ED_HOOKS.link) ED_HOOKS.link.toast(m,u); })) return true;
        const f=/** @type {any} */ (o.editorProps||{}).handlePaste; return f?f(view,e):false; } }:{}),
    ...(plain?{ transformPastedText:t=>multiline?t.replace(/\r\n?/g,"\n"):t.replace(/\s*[\r\n]+\s*/g," ") }:{}) };
  const editor=createEditor({ mount:el },{ features:email?"notes":features, ...content, injectCSS:false, editorProps:props,
    extensions:email0=>{ const list=email?emailSet(email0):email0; const out=list.map(x=>x&&x.name==="image"?x.extend({ addNodeView:()=>figureView(o.imageSrc) })
        :x&&x.name==="link"?x.extend({ inclusive:false })      // #120: typing after a link is outside it (a pasted or made link does not swallow the next word)
        :x&&x.name==="starterKit"&&headShift?x.configure({ heading:{ levels:[1,2,3] } }):x);      // a shifted host has the three levels it can store (typed #### is text)
      return [...out,...(plain?(links?[PlainLink]:[]):email?[]:[ClaimMark]),...(links?[Extension.create({ name:"cxLinkGuard", addProseMirrorPlugins:()=>[linkGuard(ED_QUIET)] })]:[]),...(o.extensions||[])]; } });
  if(links) scrubNow(editor,ED_QUIET);      /* #120: a refused address in the text it was opened with shows as plain text (quietly; an untouched text is still given back as it came) */
  const blank=()=>{ el.classList.toggle("blank",editor.isEmpty); };
  editor.on("transaction",({ transaction:tr })=>{ if(!tr.docChanged) return; blank(); if(tr.getMeta(ED_QUIET)) return; touched=true;
    el.dispatchEvent(new Event("input",{ bubbles:true })); });
  blank();
  /** @type {EdHandle} */
  const h={ el, editor, features, links, multiline, headShift,
    value:()=>{ if(!touched&&orig!==null) return orig;
      if(plain) return plainText(editor.state.doc);
      if(email) return edEmailHtml(editor);
      const md=headsOut(markdownOf(editor,dropClaims(editor.getJSON())).markdown,headShift); return env?wrap(env,md):md; },
    setValue:v=>{ if(email){ try{ editor.view.domObserver.flush(); }catch(e){ /* nothing pending */ } }   /* a change the page made to the DOM and the editor has not read yet is read first, so it cannot come back after the new text */
      const c=load(v); editor.chain().setMeta(ED_QUIET,true).setMeta("addToHistory",false)
      .setContent(c.json??c.html??c.markdown,{ emitUpdate:false, ...(c.markdown!==undefined?{ contentType:"markdown" }:{}) }).run(); touched=false; blank(); },
    touched:()=>touched,
    focus:at=>{ editor.commands.focus(at??null); },
    destroy:()=>{ if(o.prop) delete /** @type {any} */ (el)[o.prop]; try{ editor.destroy(); }catch(e){ /* already gone with its page */ }
      if(/** @type {any} */ (el).cxed===h) delete /** @type {any} */ (el).cxed; } };
  /** @type {any} */ (el).cxed=h;
  if(links&&ED_HOOKS.link) ED_HOOKS.link.attach(h);      /* #120: click a link for its popover; the link form (components/LinkPopover.jsx) */
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
/** @type {{ai: null | ((h: EdHandle, ai: EdAi) => void), link: null | {attach: (h: EdHandle) => void, toast: (msg: string, undo: () => void) => void, open: (h: EdHandle) => void}}} */
export const ED_HOOKS={ ai:null, link:null };
/**
 * A range of an editor as the AI sees it. Inside one paragraph (or heading, or list line) it is that run of text (`inline`);
 * across paragraphs it widens to the whole blocks it touches, so a reply of whole blocks replaces whole blocks. A rich editor's
 * text is Markdown (by the exact writer, claim marks taken out); a plain one's is its lines.
 * @typedef {{from: number, to: number, text: string, inline: boolean}} EdRange
 * @param {EdHandle} h @param {number} from @param {number} to @returns {EdRange|null}
 */
export function edRange(h,from,to){ const ed=h.editor, doc=ed.state.doc; if(to<=from) return null;
  if(h.features==="plain"){ const text=doc.textBetween(from,to,"\n"); return text.trim()?{ from, to, text, inline:false }:null; }
  if(h.features==="email"){ const $a=doc.resolve(from), $b=doc.resolve(to);        /* #133: one paragraph or one cell, as text: a suggestion never reshapes the table or crosses a cell */
    if(!$a.sameParent($b)||!$a.parent.isTextblock) return null;
    const text=doc.textBetween(from,to,"\n","\n"); return text.trim()?{ from, to, text, inline:true }:null; }
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
  if(h.features==="email"){ const L=String(text).replace(/\r\n?/g,"\n").trim().split(/\s*\n\s*/).filter(Boolean);   /* lines of an email's paragraph are line breaks, never a new block */
    content=[]; L.forEach((l,i)=>{ if(i) content.push({ type:"hardBreak" }); content.push({ type:"text", text:l }); }); }
  else if(h.features==="plain"){ const L=String(text).replace(/\r\n?/g,"\n").split("\n"); content=L.length===1?(L[0]?[{ type:"text", text:L[0] }]:[]):plainDoc(L.join("\n")).content; }
  else { const blocks=(ed.schema.nodeFromJSON(ed.markdown.parse(headsIn(headsSafe(String(text),h.headShift),h.headShift))).toJSON().content)||[];
    content=r.inline&&blocks.length===1&&blocks[0].type==="paragraph"?(blocks[0].content||[]):blocks; }
  const chain=ed.chain().focus();
  return (content.length?chain.insertContentAt({ from:r.from, to:r.to },content,{ updateSelection:true }):chain.deleteRange({ from:r.from, to:r.to })).run(); }
/* ----- BL-117: Turn into (formatting, no AI): the type of the selected blocks, by the editor's own commands ----- */
/** The kinds Turn into offers: id → the name the toast uses. */
export const TURN_NAMES=/** @type {Record<string,string>} */ ({ text:"text", h1:"heading 1", h2:"heading 2", h3:"heading 3", ul:"a bulleted list",
  ol:"a numbered list", task:"a checklist", quote:"a quote" });
/** What every selected block is now, as a Turn into id, or "" when they differ. @param {EdHandle} h */
export function edTurnKind(h){ const ed=h.editor, s=ed.state.selection; const kinds=new Set();
  ed.state.doc.nodesBetween(s.from,s.to,(n,pos,parent)=>{ if(!n.isTextblock) return;
    const $p=ed.state.doc.resolve(pos); let k=n.type.name==="heading"?"h"+n.attrs.level:"text";
    for(let d=$p.depth;d>0;d--){ const t=$p.node(d).type.name; if(t==="taskList"){ k="task"; break; } if(t==="bulletList"){ k="ul"; break; }
      if(t==="orderedList"){ k="ol"; break; } if(t==="blockquote"){ k="quote"; break; } }
    kinds.add(k); return false; });
  return kinds.size===1?[...kinds][0]:""; }
/** Turn the selected blocks into `kind`: first plain paragraphs (out of any list or quote), then the kind, in one transaction (one
    ⌘Z). Every block the selection touches is converted, whatever it was. @param {EdHandle} h @param {string} kind @returns {boolean} */
export function edTurnInto(h,kind){ const ed=h.editor; if(ed.isDestroyed||!TURN_NAMES[kind]||ed.state.selection.empty) return false;
  const { from, to }=ed.state.selection; let a=-1, z=-1;      /* only the blocks that hold text: ⌘A also takes the empty paragraph the editor keeps at the end, which must stay a paragraph */
  ed.state.doc.nodesBetween(from,to,(n,pos)=>{ if(n.isTextblock&&n.content.size){ if(a<0) a=pos+1; z=pos+n.nodeSize-1; } return !n.isTextblock; });
  const c=ed.chain().focus(); if(a>=0&&z>=a) c.setTextSelection({ from:Math.max(from,a), to:Math.min(to,z) });
  c.clearNodes();
  if(kind==="h1"||kind==="h2"||kind==="h3") c.setHeading({ level:+kind[1] });
  else if(kind==="ul") c.toggleBulletList(); else if(kind==="ol") c.toggleOrderedList();
  else if(kind==="task") c.toggleTaskList(); else if(kind==="quote") c.toggleBlockquote();
  return c.run(); }
/* ===== end BL-301 D ===== */
