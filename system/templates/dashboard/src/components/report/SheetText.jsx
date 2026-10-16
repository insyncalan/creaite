// @ts-check
/* SheetText (v2.1.0 P5, contract §4.3): the sheet's text. In editing, a field is the one editor (core/editor.js creaiteEditor):
   rich (Markdown, as the one editor writes it) for a section's text and panes, plain and one line for a table cell. Its AI
   (BL-301 D) is the bar over a selection, with the place the view named ("report" or "minutes"). In Show as exported the same text is
   drawn as creaite_doc.render draws it (paragraphs, lists, bold), never as an editor. Inline checks are claim marks on the first
   match of the check's quote; they are never saved. Text only through JSX. */
import { useEffect, useRef, useState } from "preact/hooks";
import { creaiteEditor, ED_QUIET } from "../../core/editor.js";
import { EditorBar } from "../EditorBar.jsx";

/** @typedef {{id: string, quote: string, note?: string, n?: number}} SheetCheckLike */

/** Inline Markdown as elements: **bold**, *italic*, and [text](url) as its text only (the export keeps no links). @param {string} t */
function inline(t) {
  const out = [], re = /\*\*([^*]+)\*\*|\*([^*\n]+)\*|\[([^\]\n]+)\]\(([^)\s]+)\)/g;
  let last = 0, k = 0;
  for (const m of t.matchAll(re)) {
    const at = m.index || 0;
    if (at > last) out.push(t.slice(last, at));
    if (m[1] != null) out.push(<strong key={k++}>{m[1]}</strong>);
    else if (m[2] != null) out.push(<em key={k++}>{m[2]}</em>);
    else out.push(m[3]);
    last = at + m[0].length;
  }
  if (last < t.length) out.push(t.slice(last));
  return out;
}

/** Markdown as the export shows it: paragraphs, "- " and "1. " lists, "###" headings. @param {string} text */
export function mdNodes(text) {
  const lines = String(text || "").replace(/\r\n?/g, "\n").split("\n"), out = [];
  let para = /** @type {string[]} */ ([]), list = /** @type {{ordered: boolean, items: string[]}|null} */ (null), k = 0;
  const flushPara = () => { if (para.length) out.push(<p key={k++}>{inline(para.join(" "))}</p>); para = []; };
  const flushList = () => {
    if (!list) return;
    const li = list.items.map((x, i) => <li key={i}>{inline(x)}</li>);
    out.push(list.ordered ? <ol key={k++}>{li}</ol> : <ul key={k++}>{li}</ul>); list = null;
  };
  for (const raw of lines) {
    const b = /^\s*(?:[-*]\s+)(.*)$/.exec(raw), n = /^\s*\d+[.)]\s+(.*)$/.exec(raw), h = /^#{1,6}\s+(.*)$/.exec(raw);
    if (b || n) { flushPara(); const ordered = !!n; if (list && list.ordered !== ordered) flushList(); if (!list) list = { ordered, items: [] }; list.items.push(/** @type {RegExpExecArray} */ (b || n)[1]); }
    else if (h) { flushPara(); flushList(); out.push(<h3 key={k++}>{inline(h[1])}</h3>); }
    else if (!raw.trim()) { flushPara(); flushList(); }
    else { flushList(); para.push(raw.trim()); }
  }
  flushPara(); flushList();
  return out;
}

/** Put (or clear) the claim marks for `checks` on a rich editor: the first match of each quote, quietly (not an edit, not undoable,
    not saved). The mark's `c` is the check's place in `checks`. @param {import("../../core/editor.js").EdHandle} h @param {SheetCheckLike[]} checks */
export function paintChecks(h, checks) {
  const ed = h.editor;
  if (!ed || ed.isDestroyed || h.features === "plain") return;
  const type = ed.schema.marks.claim, doc = ed.state.doc;
  if (!type) return;
  let tr = ed.state.tr.removeMark(0, doc.content.size, type);
  checks.forEach((c, n) => {
    const q = String(c.quote || "");
    if (!q) return;
    let done = false;
    doc.descendants((/** @type {any} */ node, /** @type {number} */ pos) => {
      if (done || !node.isTextblock) return !done;
      const i = node.textContent.indexOf(q);
      if (i >= 0) { tr = tr.addMark(pos + 1 + i, pos + 1 + i + q.length, type.create({ c: String(c.n == null ? n : c.n) })); done = true; }
      return false;
    });
  });
  if (tr.docChanged || tr.steps.length) ed.view.dispatch(tr.setMeta(ED_QUIET, true).setMeta("addToHistory", false));
}

/** ProseMirror's own scroll-to-caret reads positions through the page's scale and jumps the sheet; this one scrolls the sheet's
    scroller only when the caret is outside what it shows, by the distance it is outside (so a click or a redraw never moves it). */
function keepCaretInView(/** @type {any} */ view) {
  const sc = view.dom.closest(".sheet-scroll");
  if (!sc) return true;
  let at;
  try { at = view.coordsAtPos(view.state.selection.head); } catch (e) { return true; }
  const box = sc.getBoundingClientRect();
  if (at.bottom > box.bottom - 8) sc.scrollTop += at.bottom - box.bottom + 24;
  else if (at.top < box.top + 8) sc.scrollTop -= box.top - at.top + 24;
  return true;
}

/** @typedef {{value: string, rich: boolean, label: string, onText: (text: string) => void, ai?: any, checks?: SheetCheckLike[],
    cls?: string, multiline?: boolean, placeholder?: string, editable?: boolean}} EditorProps */
/** One field on the one editor. It keeps its editor while it is drawn again; a value set from outside (a redraft used, a reload)
    goes in when the editor isn't being typed in. @param {EditorProps} props */
export function SheetEditor({ value, rich, label, onText, ai, checks = [], cls = "", multiline = true, placeholder, editable = true }) {
  const box = useRef(/** @type {HTMLDivElement|null} */ (null));
  const ed = useRef(/** @type {import("../../core/editor.js").EdHandle|null} */ (null));
  const on = useRef(onText); on.current = onText;
  const marks = useRef(checks); marks.current = checks;
  useEffect(() => {
    const el = /** @type {HTMLDivElement} */ (box.current);
    const editorProps = { handleScrollToSelection: keepCaretInView };
    const h = creaiteEditor(el, rich ? { features: "current", markdown: value, editorProps, ...(ai ? { ai } : {}) }
      : { features: "plain", text: value, multiline, editorProps, ...(ai ? { ai } : {}) });
    ed.current = h;
    h.editor.setEditable(editable);
    const input = () => on.current(h.value());
    el.addEventListener("input", input);
    paintChecks(h, marks.current);
    return () => { el.removeEventListener("input", input); h.destroy(); ed.current = null; };
  }, [rich, !!ai]);
  useEffect(() => {
    const h = ed.current;
    if (h && !h.el.contains(document.activeElement) && h.value() !== value) { h.setValue(value); paintChecks(h, marks.current); }
  }, [value]);
  useEffect(() => { if (ed.current && !ed.current.editor.isDestroyed) ed.current.editor.setEditable(editable); }, [editable]);
  const key = checks.map(c => `${c.id}:${c.quote}`).join("|");
  useEffect(() => { if (ed.current) paintChecks(ed.current, checks); }, [key]);
  /* #134: a rich field shows the one-line grouped toolbar (the "sheet" profile) above it while it is active. It sits outside the
     measured field and takes no room (absolute), so heights and the saved text do not change when it appears. The # and picture
     buttons need a host that has pickers; a sheet has none, so they are not drawn (a client sheet never offers an internal item). */
  const [active, setActive] = useState(false);
  const wrap = useRef(/** @type {HTMLDivElement|null} */ (null));
  const field = <div ref={box} class={`sheet-ed${rich ? " sheet-rich" : " sheet-cell"} ${cls}`} role="textbox" aria-multiline={rich || multiline ? "true" : "false"}
    aria-label={label} data-ph={placeholder} spellcheck />;
  if (!rich) return field;
  return <div ref={wrap} class="sheet-edwrap" onFocusIn={() => setActive(true)}
    onFocusOut={e => { const to = /** @type {Node|null} */ (e.relatedTarget); if (!to || !wrap.current || !wrap.current.contains(to)) setActive(false); }}>
    {active && editable ? <EditorBar profile="sheet" handle={() => ed.current} cls="sheet-rtebar" label={`Formatting: ${label}`} /> : null}
    {field}
  </div>;
}
