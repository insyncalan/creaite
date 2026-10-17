// @ts-check
/* LinkPopover (#120): links in every rich editor (Notes, the capture drawer, Current state; the report sheets' rich fields get the
   check and the key). One small popover, two shapes, both labelled as a dialog ("Link"):
   - the FORM (add or edit): Text (the selected words, editable) and Address, with Add or Apply, Remove link and Open for an existing
     link, and Cancel. Enter applies, Esc cancels and gives the cursor back, Tab stays inside it. An address is judged by
     core/linkUrl.js (http, https and mailto only: "example.com" gets https://, javascript:, data: and file: are refused with a
     message and nothing is inserted). With no words selected the address is its own text.
   - the VIEW: a click on a link, or the cursor arriving in one by the arrow keys, shows its address with Open (a new tab,
     rel="noopener noreferrer"), Edit and Remove. A plain click never opens the address; Open is always an explicit step. Tab from the
     text moves into it (outside a list, where Tab is Indent); ⌘⇧K edits the link under the cursor from anywhere in the text.
   Four ways in to the form: the toolbar's Link button (components/EditorBar.jsx), the `/` menu's Link row (components/SlashMenu.jsx),
   ⌘⇧K (Ctrl+Shift+K off a Mac; ⌘K is the command palette), and pasting an address (core/editorLink.js: over selected words the words
   become the link; alone, the address becomes a link; a toast with Undo either way). Work-item and person links (creaite:item,
   creaite:person) are not web links: the form refuses to write over them and a click on one is the note's (open the item).
   It is drawn on the body (or in the editor's open modal dialog), position:fixed from the editor's own coordinates (core/caretPlace.js).
   The text goes through JSX only. The AI bar (components/AiSelect.jsx) is put away while the form is open and comes back with the
   selection when the cursor returns to the text. */
import { render } from "preact";
import { useEffect, useRef, useState } from "preact/hooks";
import { ED_HOOKS } from "../core/editor.js";
import { applyLink, internalIn, linkAt, removeLink } from "../core/editorLink.js";
import { linkUrl, typedLinkUrl } from "../core/linkUrl.js";
import { placeAtCaret } from "../core/caretPlace.js";
import { snack } from "../core/server.js";
import { aiBar } from "../stores/aiEdit.js";

export const LINK_REFUSED = "Only http, https and mailto addresses can be linked.";

/** @typedef {import("../core/editor.js").EdHandle} EdHandle */
/** @typedef {{mode: "view", h: EdHandle, from: number, to: number, href: string}
    | {mode: "form", h: EdHandle, from: number, to: number, href: string, text: string, existing: boolean, whole: boolean, key: number}} PopState */

/** @type {PopState|null} */
let pop = null;
let root = /** @type {HTMLDivElement|null} */ (null), unplace = /** @type {(() => void)|null} */ (null), seq = 0, formKey = 0;

/** The popover's host element, in the editor's modal dialog when it is in one. @param {EdHandle} h */
function home(h) {
  if (!root) { root = document.createElement("div"); root.className = "linkroot"; }
  const host = /** @type {HTMLElement} */ (h.el.closest("dialog[open]") || document.body);
  if (root.parentElement !== host) host.appendChild(root);
  return root;
}
/** Where the words start, for the popover's left edge. @param {any} view @param {number} from */
const leftAt = (view, from) => { try { return view.coordsAtPos(from).left; } catch (e) { return 16; } };

/** Put the popover away. @param {boolean} [back] give the focus back to the text */
function closePop(back) {
  const p = pop;
  pop = null;
  if (unplace) { unplace(); unplace = null; }
  if (root) render(null, root);
  if (p && p.h.editor.isDestroyed) return;
  if (back && p) {
    const ed = p.h.editor;
    ed.chain().focus().setTextSelection(Math.min(p.to, ed.state.doc.content.size)).run();
  }
}
/** Draw the popover for the current state, placed under the words. */
function draw() {
  const p = pop;
  if (!p || p.h.editor.isDestroyed) { closePop(); return; }
  const r = home(p.h);
  render(p.mode === "form" ? <LinkForm key={p.key} p={p} /> : <LinkView p={p} />, r);
  const box = /** @type {HTMLElement|null} */ (r.firstElementChild);
  if (unplace) { unplace(); unplace = null; }
  if (box) unplace = placeAtCaret(p.h.editor.view, p.to, box, { from: p.from, x: () => leftAt(p.h.editor.view, p.from), max: 320, scroll: false });
}

/** Open the link form for an editor: the selection (or the link under the cursor). @param {EdHandle} h */
export function openLinkForm(h) {
  const ed = h.editor;
  if (!h || ed.isDestroyed) return false;
  const sel = ed.state.selection, $f = sel.$from;
  if (sel.node || !$f || !$f.parent.isTextblock || $f.parent.type.spec.code) { snack("Put the cursor in some text to add a link"); return false; }
  if (!ed.state.schema.marks.link) return false;
  if (internalIn(ed.state.doc, sel.from, sel.to) || (sel.empty && $f.marks().some((/** @type {any} */ m) => m.type.name === "link") && !linkAt(ed))) {
    snack("A work item or person link can't also be a web link"); return false;
  }
  const have = linkAt(ed), from = have ? have.from : sel.from, to = have ? have.to : sel.to;
  const whole = !$f.sameParent(sel.$to);                       // several paragraphs: the words stay as they are
  const text = have ? have.text : ed.state.doc.textBetween(from, to);
  if (aiBar.value && aiBar.value.h === /** @type {any} */ (h)) aiBar.value = null;
  pop = { mode: "form", h, from, to, href: have ? have.href : "", text, existing: !!have, whole, key: ++formKey };
  draw();
  return true;
}

/** The form. @param {{p: Extract<PopState, {mode: "form"}>}} props */
function LinkForm({ p }) {
  const id = useRef(`linkpop-${++seq}`).current;
  const box = useRef(/** @type {HTMLDivElement|null} */ (null));
    const addrIn = useRef(/** @type {HTMLInputElement|null} */ (null));
  const [text, setText] = useState(p.text);
  const [addr, setAddr] = useState(p.href);
  const [err, setErr] = useState("");
  useEffect(() => { const f = addrIn.current; if (f) { f.focus(); f.select(); } }, []);          /* the cursor starts in Address (the mockup): paste or type it, Enter */
  const submit = () => {
    const a = addr.trim();
    if (!a) { setErr("Enter an address."); addrIn.current?.focus(); return; }
    if (!typedLinkUrl(a)) { setErr(LINK_REFUSED); addrIn.current?.focus(); return; }
    const ed = p.h.editor;
    if (ed.isDestroyed) { closePop(); return; }
    const ok = applyLink(ed, { from: p.from, to: p.to, text: p.whole ? ed.state.doc.textBetween(p.from, p.to) : text, address: a });
    if (!ok) { setErr(LINK_REFUSED); return; }
    pop = null; closePop();
    ed.commands.focus();
  };
  /** @param {KeyboardEvent} e */
  const key = e => {
    if (e.isComposing) return;
    if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); closePop(true); return; }
    if (e.key === "Enter" && !(/** @type {Element} */ (e.target)).closest("button")) { e.preventDefault(); e.stopPropagation(); submit(); return; }
    if (e.key === "Tab") {          /* a small dialog: Tab stays inside it */
      const f = /** @type {HTMLElement[]} */ ([...(box.current?.querySelectorAll("input,button,a[href]") || [])]).filter(x => !x.hasAttribute("disabled"));
      if (!f.length) return;
      const i = f.indexOf(/** @type {HTMLElement} */ (document.activeElement));
      if (e.shiftKey && i <= 0) { e.preventDefault(); f[f.length - 1].focus(); }
      else if (!e.shiftKey && i === f.length - 1) { e.preventDefault(); f[0].focus(); }
    }
  };
  const open = linkUrl(p.href);
  return (
    <div class="linkpop form" ref={box} role="dialog" aria-label="Link" aria-describedby={`${id}-err`} onKeyDown={key} onMouseDown={e => { if (!(/** @type {Element} */ (e.target)).closest("input")) e.stopPropagation(); }}>
      <label for={`${id}-t`}>Text</label>
      <input id={`${id}-t`} type="text" value={p.whole ? "Several paragraphs selected" : text} disabled={p.whole} autocomplete="off" spellcheck={false}
        placeholder="The words to link (the address if empty)" onInput={e => setText(/** @type {HTMLInputElement} */ (e.currentTarget).value)} />
      <label for={`${id}-a`}>Address</label>
      <input id={`${id}-a`} ref={addrIn} type="text" inputmode="url" value={addr} autocomplete="off" spellcheck={false} placeholder="https://example.com or name@example.com"
        aria-invalid={err ? "true" : "false"} aria-describedby={`${id}-err`}
        onInput={e => { setAddr(/** @type {HTMLInputElement} */ (e.currentTarget).value); if (err) setErr(""); }} />
      <div class="linkerr" id={`${id}-err`} role="alert">{err}</div>
      <div class="linkrow">
        <button type="button" class="linkgo" data-lk="apply" onClick={submit}>{p.existing ? "Apply" : "Add"}</button>
        {p.existing ? <button type="button" data-lk="remove" onClick={() => { removeLink(p.h.editor, p.from, p.to); closePop(true); }}>Remove link</button> : null}
        {p.existing && open ? <a class="linkopen" data-lk="open" href={open} target="_blank" rel="noopener noreferrer">Open ↗</a> : null}
        <button type="button" data-lk="cancel" onClick={() => closePop(true)}>Cancel</button>
      </div>
    </div>
  );
}

/** The one-line view of a link. @param {{p: Extract<PopState, {mode: "view"}>}} props */
function LinkView({ p }) {
  const open = linkUrl(p.href);
  /** @param {KeyboardEvent} e */
  const key = e => {
    if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); closePop(true); }
  };
  return (
    <div class="linkpop view" role="dialog" aria-label="Link" onKeyDown={key} onMouseDown={e => e.stopPropagation()}>
      <span class="linkaddr" title={p.href}>{p.href.replace(/^mailto:/i, "")}</span>
      {open ? <a class="linkopen" data-lk="open" href={open} target="_blank" rel="noopener noreferrer">Open ↗</a> : null}
      <button type="button" data-lk="edit" onClick={() => { const h = p.h; closePop(); h.editor.chain().focus().setTextSelection({ from: p.from, to: p.to }).run(); openLinkForm(h); }}>Edit</button>
      <button type="button" data-lk="remove" onClick={() => { removeLink(p.h.editor, p.from, p.to); closePop(true); }}>Remove</button>
    </div>
  );
}

/** Show the view for the link under the cursor, or put the view away. @param {EdHandle} h */
function look(h) {
  const ed = h.editor;
  if (ed.isDestroyed) return;
  const l = ed.state.selection.empty ? linkAt(ed) : null;
  if (!l) { if (pop && pop.mode === "view" && pop.h === h) closePop(); return; }
  if (pop && pop.mode === "form") return;
  if (pop && pop.mode === "view" && pop.h === h && pop.from === l.from && pop.to === l.to && pop.href === l.href) return;
  pop = { mode: "view", h, from: l.from, to: l.to, href: l.href };
  draw();
}

/** What creaiteEditor does for a rich editor (ED_HOOKS.link.attach): a click on a link shows its view; ⌘⇧K is the form; Tab reaches the
    view; leaving the text puts it away. @param {EdHandle} h */
export function attachLink(h) {
  const el = h.el, ed = h.editor;
  /** @param {MouseEvent} e */
  const click = e => {
    const a = /** @type {Element} */ (e.target).closest ? /** @type {Element} */ (e.target).closest("a") : null;
    if (!a || !el.contains(a)) return;
    e.preventDefault();                                                            // a click on a link never leaves the page
    if (e.altKey || e.metaKey || e.ctrlKey || e.shiftKey) return;
    setTimeout(() => look(h), 0);                                                  // after the editor has put the cursor where it was clicked
  };
  /** @param {MouseEvent} e */
  const aux = e => { if ((/** @type {Element} */ (e.target)).closest && (/** @type {Element} */ (e.target)).closest("a")) e.preventDefault(); };
  /** @param {KeyboardEvent} e */
  const keydown = e => {
    if (e.isComposing || ed.view.composing) return;
    const k = e.key.toLowerCase();
    if (k === "k" && e.shiftKey && (e.metaKey || e.ctrlKey) && !e.altKey) { e.preventDefault(); e.stopPropagation(); openLinkForm(h); return; }
    if (!pop || pop.h !== h || pop.mode !== "view") return;
    if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); closePop(); return; }
    if (e.key === "Tab" && !e.shiftKey && !ed.isActive("listItem") && !ed.isActive("taskItem")) {
      const first = /** @type {HTMLElement|null} */ (root && root.querySelector("a,button"));
      if (first) { e.preventDefault(); e.stopPropagation(); first.focus(); }
    }
  };
  /** @param {KeyboardEvent} e */
  const keyup = e => { if (/^(Arrow|Home$|End$|Page)/.test(e.key)) look(h); };
  const sel = () => { if (pop && pop.mode === "view" && pop.h === h) look(h); };
  const blur = () => setTimeout(() => { if (pop && pop.mode === "view" && pop.h === h && !(root && root.contains(document.activeElement)) && !el.contains(document.activeElement)) closePop(); }, 150);
  el.addEventListener("click", click); el.addEventListener("auxclick", aux); el.addEventListener("keydown", keydown, true); el.addEventListener("keyup", keyup);
  el.addEventListener("focusout", blur);
  ed.on("selectionUpdate", sel);
  const destroy = h.destroy;
  h.destroy = () => { if (pop && pop.h === h) closePop(); destroy(); };
}

/** Called once at start-up, before any editor is made (src/main.js). */
export function bootLinkPopover() {
  ED_HOOKS.link = { attach: attachLink, toast: (m, undo) => snack(m, undo), open: h => { openLinkForm(h); } };
}
