// @ts-check
/* SheetText (v2.1.0 P5, contract §4.3): the sheet's text. In editing, a field is the one editor (core/editor.js creaiteEditor):
   rich (Markdown, as the one editor writes it) for a section's text and panes, plain and one line for a table cell. Its AI
   (BL-301 D) is the bar over a selection, with the place the view named ("report", "minutes" or "client"). In Show as exported the same text is
   drawn as creaite_doc.render draws it (paragraphs, lists, bold), never as an editor. Inline checks are claim marks on the first
   match of the check's quote; they are never saved. Text only through JSX. */
import { useEffect, useLayoutEffect, useRef, useState } from "preact/hooks";
import { creaiteEditor, ED_QUIET } from "../../core/editor.js";
import { HEAD_SHIFT } from "../../core/editorProfiles.js";
import { EditorBar } from "../EditorBar.jsx";

/** @typedef {{id: string, quote: string, note?: string, n?: number}} SheetCheckLike */

/* "Show as exported" draws the text as the exports do, so it is a port of the exports' own reading, kept in step with it by a test that
   compares the two on a corpus (test_report_editor): Word's and the HTML's reader of the marks is docx_tools.md_spans (nested **bold**, _italic_,
   ~~strike~~, `code`), and the HTML's reader of the blocks is prep_page.md_blocks (paragraphs, "> " quotes, lists, headings as bold lines). */
const WORD = "[\\p{L}\\p{N}_]";
const isWord = (/** @type {string|undefined} */ c) => c != null && new RegExp(`^${WORD}$`, "u").test(c);
const isSpace = (/** @type {string|undefined} */ c) => c != null && /^\s$/.test(c);

/** Inline Markdown as [text, bold, italic, strike, code] runs, marks nested as docx_tools.md_spans reads them (links are already
    reduced to their words by the block reader). @param {string} s @returns {[string, boolean, boolean, boolean, boolean][]} */
function expSpans(s) {
  /** @type {[string, boolean, boolean, boolean, boolean][]} */
  const out = [];
  const run = (/** @type {number} */ lo, /** @type {number} */ hi, /** @type {boolean} */ bold, /** @type {boolean} */ italic, /** @type {boolean} */ strike, /** @type {number} */ depth) => {
    let buf = "";
    /** @type {Record<string, number>} */
    const failed = {};
    const flush = () => { if (buf) { out.push([buf, bold, italic, strike, false]); buf = ""; } };
    const span = (/** @type {number} */ a, /** @type {number} */ b, /** @type {{bold?: boolean, italic?: boolean, strike?: boolean}} */ m) => {
      flush();
      if (depth < 5) run(a, b, m.bold || bold, m.italic || italic, m.strike || strike, depth + 1);
      else out.push([s.slice(a, b), bold, italic, strike, false]);
    };
    const close = (/** @type {string} */ kind, /** @type {number} */ start) => {
      if (kind in failed && start >= failed[kind]) return -1;
      let q = -1;
      if (kind === "**" || kind === "~~" || kind === "***") { q = s.indexOf(kind, start); if (q + kind.length > hi) q = -1; }
      else for (let k = start; k < hi; k++) {
        if (s[k] !== (kind === "*" ? "*" : "_")) continue;
        const prev = s[k - 1], next = k + 1 < hi ? s[k + 1] : undefined;
        if (kind === "*" ? !isSpace(prev) && prev !== "*" && !isWord(next) && next !== "*" : !isSpace(prev) && !isWord(next)) { q = k; break; }
      }
      if (q < 0) failed[kind] = start;
      return q;
    };
    let i = lo;
    while (i < hi) {
      let p = -1;
      for (let k = i; k < hi; k++) if ("*_~`".includes(s[k])) { p = k; break; }
      if (p < 0) { buf += s.slice(i, hi); break; }
      const c = s[p];
      buf += s.slice(i, p);
      i = p + 1;
      if (c === "`") {
        const q = s.indexOf("`", p + 2);
        if (q > 0 && q < hi) { flush(); out.push([s.slice(p + 1, q), bold, italic, strike, true]); i = q + 1; continue; }
      } else if (c === "*") {
        if (s.startsWith("***", p)) { const q = close("***", p + 4); if (q > 0) { span(p + 3, q, { bold: true, italic: true }); i = q + 3; continue; } }
        if (s.startsWith("**", p)) {
          const q = close("**", p + 3);
          if (q > 0) { span(p + 2, q, { bold: true }); i = q + 2; } else { buf += "**"; i = p + 2; }
          continue;
        }
        if ((p === 0 || !(isWord(s[p - 1]) || s[p - 1] === "*")) && p + 1 < hi && !isSpace(s[p + 1]) && s[p + 1] !== "*") {
          const q = close("*", p + 2);
          if (q > 0) { span(p + 1, q, { italic: true }); i = q + 1; continue; }
        }
      } else if (c === "_") {
        if ((p === 0 || !isWord(s[p - 1])) && p + 1 < hi && !isSpace(s[p + 1])) {
          const q = close("_", p + 2);
          if (q > 0) { span(p + 1, q, { italic: true }); i = q + 1; continue; }
        }
      } else if (c === "~" && s.startsWith("~~", p)) {
        const q = close("~~", p + 3);
        if (q > 0) { span(p + 2, q, { strike: true }); i = q + 2; } else { buf += "~~"; i = p + 2; }
        continue;
      }
      buf += c;
    }
    flush();
  };
  run(0, s.length, false, false, false, 0);
  return out.filter(r => r[0]);
}

/** Inline Markdown as elements (strong, em, s nested as written; a stray mark dropped, a `code` span as its words). @param {string} t */
function inline(t) {
  return expSpans(String(t || "")).map(([text, bold, italic, strike, code]) => {
    /** @type {any} */
    let x = code ? text : text.replace(/[*`]|(?<![\p{L}\p{N}_])_|_(?![\p{L}\p{N}_])/gu, "");
    if (italic) x = <em>{x}</em>;
    if (strike) x = <s>{x}</s>;
    if (bold) x = <strong>{x}</strong>;
    return x;
  });
}

/** One line as [kind, text]: "q" a quote line, "ul" or "ol" a list item (a checklist box drawn on a bullet), "head", or "text". @param {string} line */
function expLine(line) {
  /** @type {[string, RegExp][]} */
  const kinds = [["q", /^\s*>\s?(.*)$/], ["ul", /^\s*[-*•]\s+(.*)$/], ["ol", /^\s*\d+[.)]\s+(.*)$/], ["head", /^\s*#+\s*(.*)$/]];
  for (const [kind, re] of kinds) {
    const m = re.exec(line);
    if (m) {
      const text = m[1].trim();
      return [kind, kind === "ul" ? text.replace(/^\[([ xX])\](?:\s+|$)/, (all, x) => (/[xX]/.test(x) ? "☑" : "☐") + (all.trim() !== all ? " " : "")) : text];
    }
  }
  return ["text", line.trim()];
}

/** @typedef {{kind: string, text?: string, items?: string[], blocks?: ExpBlock[]}} ExpBlock */
/** The text as the HTML export reads its blocks (prep_page.md_blocks): paragraphs, quotes (a quote that holds a heading or a list is read
    again inside), lists, headings as bold lines. @param {string} md @param {number} [depth] @returns {ExpBlock[]} */
function expBlocks(md, depth = 0) {
  const t = String(md || "").replace(/!\[[^\]]*\]\([^)]*\)/g, "").replace(/\[([^\]]+)\]\([^)]*\)/g, "$1");
  /** @type {ExpBlock[]} */
  const blocks = [];
  let cur = /** @type {string|null} */ (null), items = /** @type {string[]} */ ([]);
  const flush = () => {
    if (cur === "q") {
      if (depth < 2 && items.some(x => ["ul", "ol", "head"].includes(expLine(x)[0]))) blocks.push({ kind: "qb", blocks: expBlocks(items.join("\n"), depth + 1) });
      else if (items.some(x => x)) blocks.push({ kind: "q", text: items.filter(x => x).join(" ") });
    } else if (cur && items.length) blocks.push(cur === "p" ? { kind: "p", text: items.join(" ") } : { kind: cur, items });
    cur = null; items = [];
  };
  for (const line of lines(t)) {
    const [kind, text] = expLine(line);
    if (!line.trim()) flush();
    else if (kind === "head") { flush(); blocks.push({ kind: "p", text: `**${text.replace(/^\*+|\*+$/g, "")}**` }); }
    else if (kind === "text" && (cur === "ul" || cur === "ol") && /^\s/.test(line)) items[items.length - 1] += " " + text;
    else {
      const want = kind === "text" ? "p" : kind;
      if (want !== cur) { flush(); cur = want; }
      if (text || cur === "ul" || cur === "ol" || cur === "q") items.push(text);
    }
  }
  flush();
  return blocks;
}

/** The lines of a text, split where Python's splitlines does (the exports' reader), the odd separators included. @param {string} t */
function lines(t) {
  let x = t.replace(/\r\n/g, "\n");
  for (const sep of ["\r", "\v", "\f", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029"]) x = x.split(sep).join("\n");
  return x.split("\n");
}

/** @param {ExpBlock[]} blocks */
function expNodes(blocks) {
  return blocks.map((b, k) => b.kind === "p" ? <p key={k}>{inline(b.text || "")}</p>
    : b.kind === "q" ? <blockquote key={k}><p>{inline(b.text || "")}</p></blockquote>
    : b.kind === "qb" ? <blockquote key={k}>{expNodes(b.blocks || [])}</blockquote>
    : b.kind === "ol" ? <ol key={k}>{(b.items || []).map((x, i) => <li key={i}>{inline(x)}</li>)}</ol>
    : <ul key={k}>{(b.items || []).map((x, i) => <li key={i}>{inline(x)}</li>)}</ul>);
}

/** Markdown as the export shows it: paragraphs, "> " quotes, "- " and "1. " lists, headings as bold lines. @param {string} text */
export function mdNodes(text) {
  return expNodes(expBlocks(text));
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
    const h = creaiteEditor(el, rich ? { features: "current", headShift: HEAD_SHIFT, markdown: value, editorProps, ...(ai ? { ai } : {}) }
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
  /* #134: a rich field shows the one-line grouped toolbar (the "sheet" profile) while it is active. It floats outside the measured field
     and takes no room (absolute), so heights and the saved text do not change when it appears. Where it floats is chosen so it hides as
     little as it can of what the person may need (the section's own heading, the last row of the table above, the next section's
     heading): above-left by default, then above-right, below-left, below-right, whichever covers the fewest controls (first on a tie),
     checked on showing and whenever the bar changes size (the link form opening). The # and picture buttons need a host that has
     pickers; a sheet has none, so they are not drawn (a client sheet never offers an internal item). */
  const [active, setActive] = useState(false);
  const [spot, setSpot] = useState(/** @type {BarSpot} */ ("al"));
  const wrap = useRef(/** @type {HTMLDivElement|null} */ (null));
  const showBar = active && editable && rich;
  useLayoutEffect(() => {
    const w = wrap.current, bar = w && /** @type {HTMLElement|null} */ (w.querySelector(".sheet-rtebar"));
    if (!showBar || !w || !bar) return;
    const place = () => { const at = barSpot(w, bar); setSpot(s => s === at ? s : at); };
    place();
    const ro = typeof ResizeObserver === "function" ? new ResizeObserver(place) : null;
    if (ro) ro.observe(bar);
    return () => { if (ro) ro.disconnect(); };
  }, [showBar]);
  const field = <div ref={box} class={`sheet-ed${rich ? " sheet-rich" : " sheet-cell"} ${cls}`} role="textbox" aria-multiline={rich || multiline ? "true" : "false"}
    aria-label={label} data-ph={placeholder} spellcheck />;
  if (!rich) return field;
  return <div ref={wrap} class="sheet-edwrap" data-bar={showBar ? spot : undefined} onFocusIn={() => setActive(true)}
    onFocusOut={e => { const to = /** @type {Node|null} */ (e.relatedTarget); if (!to || !wrap.current || !wrap.current.contains(to)) setActive(false); }}>
    {showBar ? <EditorBar profile="sheet" handle={() => ed.current} cls="sheet-rtebar" label={`Formatting: ${label}`} /> : null}
    {field}
  </div>;
}

/** @typedef {"al"|"ar"|"bl"|"br"} BarSpot above or below the field (a, b), flush left or right (l, r) */
/** How many controls (inputs, buttons, links, table cells, a pane's title) the bar would sit over at a spot: its box is the bar's own size, 4 px clear of the field.
    @param {HTMLElement} w the field's wrapper @param {HTMLElement} bar @param {BarSpot} spot */
export function barCovers(w, bar, spot) {
  const f = w.getBoundingClientRect(), b = bar.getBoundingClientRect(), gap = 4;
  const top = spot[0] === "b" ? f.bottom + gap : f.top - gap - b.height, left = spot[1] === "r" ? Math.max(f.left, f.right - b.width) : f.left;
  const box = { left, right: left + b.width, top, bottom: top + b.height };
  const page = w.closest(".page");
  if (!page) return 0;
  let n = 0;
  for (const el of page.querySelectorAll("input, button, a[href], td, th, h3")) {
    if (w.contains(el) || bar.contains(el) || el.closest(".sheet-handle")) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2 || getComputedStyle(el).visibility === "hidden") continue;
    if (Math.min(r.right, box.right) - Math.max(r.left, box.left) > 2 && Math.min(r.bottom, box.bottom) - Math.max(r.top, box.top) > 2) n++;
  }
  return n;
}

/** The spot that covers the fewest controls; above-left on a tie with it, then above-right, below-left, below-right.
    @param {HTMLElement} w @param {HTMLElement} bar @returns {BarSpot} */
export function barSpot(w, bar) {
  /** @type {BarSpot[]} */
  const order = ["al", "ar", "bl", "br"];
  let best = order[0], least = Infinity;
  for (const s of order) { const n = barCovers(w, bar, s); if (n < least) { best = s; least = n; } if (!least) break; }
  return best;
}
