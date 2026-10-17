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
import { Icon } from "./Icon.jsx";

export const LINK_REFUSED = "Only http, https and mailto addresses can be linked.";

/** @typedef {import("../core/editor.js").EdHandle} LinkEd */
/** @typedef {{mode: "view", h: LinkEd, from: number, to: number, href: string}
    | {mode: "form", h: LinkEd, from: number, to: number, href: string, text: string, existing: boolean, whole: boolean, key: number}} PopState */

/** @type {PopState|null} */
let pop = null;
let root = /** @type {HTMLDivElement|null} */ (null), unplace = /** @type {(() => void)|null} */ (null), linkSeq = 0, formKey = 0;

/** The popover's host element, in the editor's modal dialog when it is in one. @param {LinkEd} h */
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
function drawLink() {
  const p = pop;
  if (!p || p.h.editor.isDestroyed) { closePop(); return; }
  const r = home(p.h);
  render(p.mode === "form" ? <LinkForm key={p.key} p={p} /> : <LinkView p={p} />, r);
  const box = /** @type {HTMLElement|null} */ (r.firstElementChild);
  if (unplace) { unplace(); unplace = null; }
  if (box) unplace = placeAtCaret(p.h.editor.view, p.to, box, { from: p.from, x: () => leftAt(p.h.editor.view, p.from), max: 320, scroll: false });
}

/** Open the link form for an editor: the selection (or the link under the cursor). @param {LinkEd} h */
export function openLinkForm(h) {
  const ed = h.editor;
  if (!h || ed.isDestroyed) return false;
  const sel = ed.state.selection;
  let $f = sel.$from, a = sel.from, z = sel.to;
  if (!sel.empty && !sel.node && !$f.parent.isTextblock) {          /* ⌘A is the whole document: the link goes over the text in it */
    let x = -1, y = -1;
    ed.state.doc.nodesBetween(sel.from, sel.to, (/** @type {any} */ n, /** @type {number} */ pos) => { if (n.isTextblock && n.content.size) { if (x < 0) x = pos + 1; y = pos + n.nodeSize - 1; } return !n.isTextblock; });
    if (x >= 0) { a = x; z = y; $f = ed.state.doc.resolve(x); }
  }
  if (sel.node || !$f || !$f.parent.isTextblock || $f.parent.type.spec.code) { snack("Put the cursor in some text to add a link"); return false; }
  if (!ed.state.schema.marks.link) return false;
  if (internalIn(ed.state.doc, a, z) || (sel.empty && $f.marks().some((/** @type {any} */ m) => m.type.name === "link") && !linkAt(ed))) {
    snack("A work item or person link can't also be a web link"); return false;
  }
  const have = linkAt(ed), from = have ? have.from : a, to = have ? have.to : z;
  const whole = !$f.sameParent(ed.state.doc.resolve(z));                       // several paragraphs: the words stay as they are
  const text = have ? have.text : ed.state.doc.textBetween(from, to);
  if (aiBar.value && aiBar.value.h === /** @type {any} */ (h)) aiBar.value = null;
  pop = { mode: "form", h, from, to, href: have ? have.href : "", text, existing: !!have, whole, key: ++formKey };
  drawLink();
  return true;
}

/** The form. @param {{p: Extract<PopState, {mode: "form"}>}} props */
function LinkForm({ p }) {
  const id = useRef(`linkpop-${++linkSeq}`).current;
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
    <div class="linkpop form" ref={box} role="dialog" aria-label="Link" aria-describedby={`${id}-err`} onKeyDown={key} onMouseDown={e => { if (!(/** @type {Element} */ (e.target)).closest("input")) { e.stopPropagation(); e.preventDefault(); } }}>
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
    <div class="linkpop view" role="dialog" aria-label="Link" onKeyDown={key} onMouseDown={e => { e.stopPropagation(); e.preventDefault(); }}>
      <span class="linkaddr" title={p.href}>{p.href.replace(/^mailto:/i, "")}</span>
      {open ? <a class="linkopen" data-lk="open" href={open} target="_blank" rel="noopener noreferrer">Open ↗</a> : null}
      <button type="button" data-lk="edit" onClick={() => { const h = p.h; closePop(); h.editor.chain().focus().setTextSelection({ from: p.from, to: p.to }).run(); openLinkForm(h); }}>Edit</button>
      <button type="button" data-lk="remove" onClick={() => { removeLink(p.h.editor, p.from, p.to); closePop(true); }}>Remove</button>
    </div>
  );
}

/** Show the view for the link under the cursor, or put the view away. @param {LinkEd} h */
function look(h) {
  const ed = h.editor;
  if (ed.isDestroyed) return;
  const l = ed.state.selection.empty ? linkAt(ed) : null;
  if (!l) { if (pop && pop.mode === "view" && pop.h === h) closePop(); return; }
  if (pop && pop.mode === "form") return;
  if (pop && pop.mode === "view" && pop.h === h && pop.from === l.from && pop.to === l.to && pop.href === l.href) return;
  pop = { mode: "view", h, from: l.from, to: l.to, href: l.href };
  drawLink();
}

/* ----- #121: the link button in a plain field's corner -----
   A plain field (an item's longer text fields, Prep's notes) has no toolbar, so while the cursor is in one a small Link button sits in its
   top-right corner (the same four ways in as a rich editor: this button, ⌘⇧K, a paste, and the `/` menu where the field has one, which none does).
   It is one button on the body, placed from the field's own rectangle; pressing it keeps the cursor in the text and opens the form. */
/** @type {HTMLDivElement|null} */
let cornerRoot = null;
/** @type {{h: LinkEd, off: () => void}|null} */
let cornerOn = null;
/** Put the corner button away. @param {LinkEd} [h] only if it is this field's */
function hideCorner(h) {
  if (!cornerOn || (h && cornerOn.h !== h)) return;
  cornerOn.off(); cornerOn = null;
  if (cornerRoot) render(null, cornerRoot);
}
/** Show the corner button for a plain field. @param {LinkEd} h */
function showCorner(h) {
  if (cornerOn && cornerOn.h === h) return;
  hideCorner();
  if (!cornerRoot) { cornerRoot = document.createElement("div"); cornerRoot.className = "linkcornerroot"; }
  const host = /** @type {HTMLElement} */ (h.el.closest("dialog[open]") || document.body);
  if (cornerRoot.parentElement !== host) host.appendChild(cornerRoot);
  const root = cornerRoot;
  render(<button type="button" class="linkcorner" data-lk="corner" aria-label="Add or edit a link (⌘⇧K)" data-tip="Add or edit a link (⌘⇧K)"
    aria-keyshortcuts="Meta+Shift+K Control+Shift+K"
    onMouseDown={e => { e.preventDefault(); e.stopPropagation(); }}
    onClick={e => { e.preventDefault(); e.stopPropagation(); h.focus(); openLinkForm(h); }}><Icon name="link" size={14} /></button>, root);
  const b = /** @type {HTMLElement|null} */ (root.firstElementChild);
  const put = () => {
    if (!b || !h.el.isConnected) return;
    const r = h.el.getBoundingClientRect(), vh = window.innerHeight, vw = document.documentElement.clientWidth;
    b.style.position = "fixed";
    b.style.left = `${Math.max(4, Math.min(r.right - 26, vw - 30))}px`;
    b.style.top = `${Math.max(r.top + 3, 4)}px`;
    b.hidden = r.bottom < 8 || r.top > vh - 8 || r.height < 12;
  };
  put();
  window.addEventListener("scroll", put, true); window.addEventListener("resize", put);
  const ro = typeof ResizeObserver === "function" ? new ResizeObserver(put) : null;
  if (ro) ro.observe(h.el);
  cornerOn = { h, off: () => { window.removeEventListener("scroll", put, true); window.removeEventListener("resize", put); if (ro) ro.disconnect(); } };
}

/** What creaiteEditor does for a rich editor (ED_HOOKS.link.attach): a click on a link shows its view; ⌘⇧K is the form; Tab reaches the
    view; leaving the text puts it away. @param {LinkEd} h */
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
  if (h.features === "plain") {          /* #121: the corner button while the cursor is in the field (and the form is not open for another) */
    const inField = () => el.contains(document.activeElement);
    el.addEventListener("focusin", () => showCorner(h));
    el.addEventListener("focusout", () => setTimeout(() => { if (!inField() && !(root && root.contains(document.activeElement))) hideCorner(h); }, 0));
    /* focus that moves from the link form to somewhere else (not back to the field) would leave the corner button behind */
    const away = (/** @type {FocusEvent} */ e) => {
      const t = /** @type {Node|null} */ (e.target);
      if (cornerOn && cornerOn.h === h && t && !el.contains(t) && !(root && root.contains(t)) && !(cornerRoot && cornerRoot.contains(t))) hideCorner(h);
    };
    document.addEventListener("focusin", away);
    const destroyed = h.destroy;
    h.destroy = () => { document.removeEventListener("focusin", away); destroyed(); };
    if (inField()) showCorner(h);
  }
  const destroy = h.destroy;
  h.destroy = () => { if (pop && pop.h === h) closePop(); hideCorner(h); destroy(); };
}

/** Called once at start-up, before any editor is made (src/main.js). */
export function bootLinkPopover() {
  /* #121: a link in shown text (a table cell, the peek, a draft) opens its address in a new tab and does nothing else: the row, card or button it sits in never also gets the click */
  document.addEventListener("click", e => {
    const a = /** @type {Element|null} */ (e.target && /** @type {Element} */ (e.target).closest ? /** @type {Element} */ (e.target).closest("a.tlink") : null);
    if (a && !a.closest(".ProseMirror, [contenteditable=true]")) e.stopPropagation();
  }, true);
  ED_HOOKS.link = { attach: attachLink, toast: (m, undo) => snack(m, undo), open: h => { openLinkForm(h); } };
}
