// @ts-check
/* ItemPicker (#122 step C): the `#` work-item list every rich editor offers, one component for Notes and Current state. Type `#` at the
   start of a line or after a space and the list opens at the caret (position:fixed, core/caretPlace.js) with the host's project's items,
   open ones first, narrowed by what follows the `#` (ID, designation or title). Each row reads 'ID · Designation: title'; ↑ ↓ move,
   Enter or Tab pick, Esc closes and leaves the text, a click picks. Picking replaces the "#query" with the link (core/itemLink.js):
   the whole of 'ID · Designation: title' as one link to `creaite:item/<ID>`. Focus stays in the text, the editor carries
   aria-activedescendant, and the list is a listbox. Not in a code block, code or a link; an input-method composition never opens it.
   Nothing is written until a row is chosen. The `/` menu's "Work item" row types a `#`, which opens this list. */
import { render } from "preact";
import { useEffect, useLayoutEffect, useRef } from "preact/hooks";
import { placeAtCaret } from "../core/caretPlace.js";
import { OWN_STEP } from "../core/undoSteps.js";
import { itemByQuery, itemContent, itemOptions } from "../core/itemLink.js";
import { Icon } from "./Icon.jsx";

/** @typedef {import("../core/itemLink.js").ItemOption} ItemOption */
/** @typedef {{from: number, to: number, q: string, opts: ItemOption[], i: number}} ItemState */

/** The "#query" before the caret where the list may open, else null. @param {any} editor */
export function hashAt(editor) {
  const s = editor.state.selection;
  if (!s.empty) return null;
  const $f = s.$from;
  if ($f.parent.type.name === "codeBlock") return null;
  if ($f.marks().some(/** @param {any} m */ m => m.type.name === "code" || m.type.name === "link")) return null;
  const before = $f.parent.textBetween(0, $f.parentOffset, undefined, "￼"), m = /(^|\s)#([A-Za-z0-9-]{0,20})$/.exec(before);
  if (!m || /\[\[[^\]]*$/.test(before)) return null;
  return { from: s.from - m[2].length - 1, to: s.from, q: m[2] };
}

/** Editors where a `#` was just put in by a command (the Insert menu, the `/` row): that counts as typed, so the list may open. */
const armed = new WeakSet();

/** The toolbar's and the `/` menu's "Work item": type a `#` at the caret (after a space if the text before it is a word), which opens the list.
    @param {{editor: any}} h */
export function insertHash(h) {
  const e = h.editor, s = e.state.selection, before = s.empty ? s.$from.parent.textBetween(0, s.$from.parentOffset, undefined, "￼") : "";
  armed.add(e);
  e.chain().focus().insertContent(before && !/\s$/.test(before) ? " #" : "#").run();
}

/** @param {{state: ItemState, view: any, pick: (o: ItemOption) => void, hover: (i: number) => void}} p */
function ItemList({ state, view, pick, hover }) {
  const box = useRef(/** @type {HTMLDivElement|null} */ (null));
  useLayoutEffect(() => {
    const el = box.current;
    return el ? placeAtCaret(view, state.from, el) : undefined;
  }, [state.opts.length, state.from, state.q]);
  useEffect(() => { const on = box.current && box.current.querySelector(".r.on"); if (on && on.scrollIntoView) on.scrollIntoView({ block: "nearest" }); }, [state.i]);
  return (
    <div ref={box} class="ntpick items" id="ntpick" role="listbox" aria-label="Link a work item" onMouseDown={e => e.preventDefault()}>
      <div class="h" aria-hidden="true">Work items</div>
      {state.opts.map((o, i) => (
        <div key={o.id} id={`ntpick-${i}`} role="option" data-item-opt={o.id} aria-selected={i === state.i ? "true" : "false"} class={`r${i === state.i ? " on" : ""}`}
          onMouseMove={() => { if (i !== state.i) hover(i); }} onClick={() => pick(o)}>
          {o.icon ? <Icon name={o.icon} /> : null}<span class="l">{o.label}</span>
        </div>))}
    </div>
  );
}

/** Give an editor its `#` list. `code` is the project whose items it offers ("_portfolio": all). Returns what takes it away again.
    @param {import("../core/editor.js").EdHandle} h @param {{code: () => string}} o */
export function attachItemPick(h, { code }) {
  const editor = h.editor, view = editor.view, el = h.el;
  const root = document.createElement("div");
  root.className = "itemrootpick";
  (el.closest("dialog[open]") || document.body).appendChild(root);
  /** @type {ItemState|null} */
  let st = null;
  let dismissed = -1, opened = false, typed = false, chosen = false;          /* typed: text was just typed or deleted (or a # inserted by a command), the only thing that opens the list, as under the / menu. chosen: Alan arrowed in the list or a command opened it, so Enter picks the row; else only an exact ID (or a unique 3+ character ID prefix) */
  const draw = () => {
    render(st ? <ItemList state={st} view={view} pick={choose} hover={i => { if (st) { st = { ...st, i }; draw(); } }} /> : null, root);
    const dom = /** @type {HTMLElement} */ (view.dom);
    if (st) { opened = true; dom.setAttribute("aria-haspopup", "listbox"); dom.setAttribute("aria-expanded", "true"); dom.setAttribute("aria-controls", "ntpick");
      dom.setAttribute("aria-activedescendant", `ntpick-${st.i}`); }
    else { for (const a of ["aria-haspopup", "aria-controls", "aria-activedescendant"]) dom.removeAttribute(a); if (opened) dom.setAttribute("aria-expanded", "false"); }          /* as the / menu: "false" once it has been open */
  };
  const close = () => { chosen = false; if (!st) return; st = null; draw(); };
  const look = () => {
    const cmd = armed.delete(editor), mayOpen = typed || cmd; typed = false;
    if (editor.isDestroyed || view.composing) return;
    const a = hashAt(editor);
    if (!a || a.from === dismissed) { if (!a) dismissed = -1; return close(); }
    if (!st && !mayOpen) return;          /* a caret move, a paste or a saved note never opens it; only typing a "#" (or its query) does */
    if (st && st.from !== a.from && !mayOpen) return close();
    const opts = itemOptions(code(), a.q);
    if (!opts.length) return close();
    if (cmd) chosen = true;
    st = { ...a, opts, i: st && st.from === a.from ? Math.min(st.i, opts.length - 1) : 0 };
    draw();
  };
  /** @param {ItemOption} o */
  const choose = o => {
    const s = st;
    if (!s) return;
    close();
    editor.chain().focus().setMeta(OWN_STEP, true).deleteRange({ from: s.from, to: s.to }).insertContent(itemContent(o.id)).run();
  };
  /** @param {KeyboardEvent} e */
  const keys = e => {
    if (!st || e.defaultPrevented || e.isComposing || view.composing) return;          /* a key the / menu has just used (its row typed the #) is not ours */
    const n = st.opts.length;
    if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); e.stopPropagation(); chosen = true; st = { ...st, i: (st.i + (e.key === "ArrowDown" ? 1 : n - 1)) % n }; draw(); }
    else if ((e.key === "Enter" || e.key === "Tab") && !e.shiftKey && !e.metaKey && !e.ctrlKey) {
      const id = chosen ? st.opts[st.i].id : itemByQuery(code(), st.q), o = id && st.opts.find(x => x.id === id);
      if (!o) { close(); return; }          /* typed text, no clear choice: the list closes and the key does its usual job (a newline, a tab) */
      e.preventDefault(); e.stopPropagation(); choose(o);
    }
    else if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) { e.preventDefault(); e.stopPropagation(); }      /* ⌘↵ waits, as under the / menu */
    else if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); dismissed = st.from; close(); }
  };
  const blur = () => setTimeout(() => { if (!el.contains(document.activeElement)) close(); }, 150);
  const comp = () => { typed = true; look(); };
  /** @param {InputEvent} e */
  const before = e => { typed = e.inputType === "insertText" || e.inputType.startsWith("deleteContent"); };          /* beforeinput runs before the transaction: typing or deleting arms it (never a paste, a drop or a caret move) */
  editor.on("selectionUpdate", look); editor.on("update", look);
  el.addEventListener("beforeinput", before, true);
  el.addEventListener("keydown", keys, true); el.addEventListener("focusout", blur); el.addEventListener("compositionend", comp);
  const off = () => {
    editor.off("destroy", off);
    editor.off("selectionUpdate", look); editor.off("update", look);
    el.removeEventListener("beforeinput", before, true); el.removeEventListener("keydown", keys, true); el.removeEventListener("focusout", blur); el.removeEventListener("compositionend", comp);
    st = null; render(null, root); root.remove();
    if (!editor.isDestroyed) for (const a of ["aria-expanded", "aria-controls", "aria-activedescendant", "aria-haspopup"]) view.dom.removeAttribute(a);
  };
  editor.on("destroy", off);
  return off;
}
