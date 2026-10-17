// @ts-check
/* core/editorLink.js (#120): what the shared editor does with links, apart from the popover (components/LinkPopover.jsx).
   - linkGuard: a ProseMirror plugin that takes every link mark off a text whose address `keepHref` (core/linkUrl.js) refuses, so a
     hostile address in a file that is opened, pasted, set by code or made by any command is shown as the plain text it is and never
     as a link. `scrubNow` does the same once for a document just loaded (quietly: opening an editor is never an edit; an untouched
     text is still written back byte for byte, because `value()` gives the original back).
   - pasteLink: a pasted web or mail address becomes a link (over selected words: the words; with nothing selected: the address as its
     own text). Anything else, and any address `typedLinkUrl` refuses, pastes as before (plain text, never a link).
   - linkAt, applyLink, removeLink, internalIn: the commands the popover and the toolbar use.
   Nothing here imports the editor, so core/editor.js can use it. */
import { Plugin, PluginKey } from "tiptap";
import { isInternalHref, keepHref, linkUrl, typedLinkUrl } from "./linkUrl.js";

/** The transaction that takes the refused link marks out of `doc`, or null when there are none. @param {any} tr @param {any} doc */
function scrubTr(tr, doc) {
  let n = 0;
  doc.descendants((/** @type {any} */ node, /** @type {number} */ pos) => {
    if (!node.isText) return;
    for (const m of node.marks) if (m.type.name === "link" && !keepHref(m.attrs.href)) { tr.removeMark(pos, pos + node.nodeSize, m); n++; }
  });
  return n ? tr : null;
}

/** The plugin that keeps refused links out of the document. `quiet` is core/editor.js's ED_QUIET meta name: a quiet transaction's
    clean-up is quiet and out of the history as well. @param {string} quiet */
export function linkGuard(quiet) {
  return new Plugin({
    key: new PluginKey("cxLinkGuard"),
    appendTransaction(trs, _old, state) {
      if (!trs.some(t => t.docChanged)) return null;
      const tr = scrubTr(state.tr, state.doc);
      if (!tr) return null;
      if (trs.some(t => t.getMeta(quiet))) tr.setMeta(quiet, true).setMeta("addToHistory", false);
      return tr;
    },
  });
}

/** Clean a document that was just loaded, quietly. @param {any} editor @param {string} quiet */
export function scrubNow(editor, quiet) {
  if (!editor || editor.isDestroyed) return false;
  const tr = scrubTr(editor.state.tr, editor.state.doc);
  if (!tr) return false;
  editor.view.dispatch(tr.setMeta(quiet, true).setMeta("addToHistory", false));
  return true;
}

/** Whether the range holds one of creaite's own links (a work item or a person): those are not web links and a web link must not
    replace them. @param {any} doc @param {number} from @param {number} to */
export function internalIn(doc, from, to) {
  let hit = false;
  doc.nodesBetween(from, to, (/** @type {any} */ n) => { if (n.isText && n.marks.some((/** @type {any} */ m) => m.type.name === "link" && isInternalHref(m.attrs.href))) hit = true; return !hit; });
  return hit;
}

/** The link at the cursor (or the whole selection), if it is a web or mail one:
    `{from, to, href, text}` for the link's full run, else null. creaite's own links (work items, people) are not returned.
    @param {any} editor @returns {{from: number, to: number, href: string, text: string}|null} */
export function linkAt(editor) {
  const { state } = editor, type = state.schema.marks.link, { selection: sel } = state;
  if (!type || !sel.$from) return null;
  const $f = sel.$from;
  const mk = (/** @type {any} */ marks) => marks.find((/** @type {any} */ m) => m.type === type);
  let m = sel.empty ? mk($f.marks()) : mk(state.doc.resolve(Math.min(sel.from + 1, sel.to)).marks());
  if (!m && sel.empty) { const after = $f.nodeAfter; if (after && after.isText) m = mk(after.marks); }          // a caret at the very start of a link
  if (!m || isInternalHref(m.attrs.href)) return null;
  const parent = $f.parent, base = $f.start();
  /** @type {{from: number, to: number}[]} */
  const runs = [];
  let cur = /** @type {{from: number, to: number}|null} */ (null);
  parent.forEach((/** @type {any} */ child, /** @type {number} */ off) => {          // the unbroken runs of text that carry this very link
    const a = base + off, b = a + child.nodeSize;
    if (child.isText && child.marks.some((/** @type {any} */ x) => x.eq(m))) { if (cur && cur.to === a) cur.to = b; else { cur = { from: a, to: b }; runs.push(cur); } } else cur = null;
  });
  const run = runs.find(r => sel.from >= r.from && sel.to <= r.to);
  if (!run) return null;
  const { from, to } = run;
  return { from, to, href: String(m.attrs.href || ""), text: state.doc.textBetween(from, to) };
}

/** Make `text` (the words) a link to `address` in `from`..`to`, or at the cursor when they are equal, as one undoable step. The address
    is checked here too (`typedLinkUrl`): false, and nothing changed, when it is refused or the range holds one of creaite's own links.
    @param {any} editor @param {{from: number, to: number, text: string, address: string}} o @returns {boolean} */
export function applyLink(editor, { from, to, text, address }) {
  const href = typedLinkUrl(address);
  if (!href || editor.isDestroyed) return false;
  const doc = editor.state.doc;
  if (to > from && internalIn(doc, from, to)) return false;
  const words = text === "" ? href : text, same = to > from && doc.textBetween(from, to) === words;
  const mark = { type: "link", attrs: { href } };
  const c = editor.chain().focus();
  if (same) c.setTextSelection({ from, to }).setMark("link", { href });
  else c.insertContentAt({ from, to }, { type: "text", text: words, marks: [mark] });
  const ok = c.run();
  if (ok) editor.commands.setTextSelection(Math.min(from + words.length, editor.state.doc.content.size));
  return ok;
}

/** Take the link off `from`..`to`, keeping the words. @param {any} editor @param {number} from @param {number} to */
export function removeLink(editor, from, to) {
  if (editor.isDestroyed) return false;
  return editor.chain().focus().setTextSelection({ from, to }).unsetMark("link").setTextSelection(to).run();
}

/** The paste handler: true when it made the link. `notify(message, undo)` shows the toast with Undo.
    @param {any} editor @param {ClipboardEvent} event @param {(msg: string, undo: () => void) => void} notify */
export function pasteLink(editor, event, notify) {
  const cd = event.clipboardData;
  if (!cd || editor.isDestroyed) return false;
  const text = (cd.getData("text/plain") || "").trim();
  if (!text || /\s/.test(text) || !/^(?:https?:\/\/|mailto:|www\.)/i.test(text)) return false;
  const href = typedLinkUrl(text);
  if (!href) return false;                                                 // a refused address pastes as the plain text it is
  const { state } = editor, sel = state.selection, type = state.schema.marks.link;
  if (!type || !sel.$from || sel.node) return false;                       // a picture or other whole block is selected: paste as before
  if (!sel.$from.sameParent(sel.$to) || !sel.$from.parent.isTextblock || sel.$from.parent.type.spec.code) return false;
  const inCode = (/** @type {any} */ ms) => ms.some((/** @type {any} */ m) => m.type.name === "code");
  if (sel.empty ? (inCode(sel.$from.marks()) || linkAt(editor)) : internalIn(state.doc, sel.from, sel.to)) return false;
  const tr = sel.empty ? state.tr.replaceSelectionWith(state.schema.text(href, [type.create({ href })]), false) : state.tr.addMark(sel.from, sel.to, type.create({ href }));
  editor.view.dispatch(tr.scrollIntoView());
  event.preventDefault();
  notify(sel.empty ? "Pasted as a link" : "Linked", () => { if (!editor.isDestroyed) { editor.commands.undo(); editor.commands.focus(); } });
  return true;
}

export { linkUrl };
