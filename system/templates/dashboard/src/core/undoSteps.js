// @ts-check
/* ===== #175 ===== Notes: undo and redo one change at a time, by the editor's own history (ProseMirror's, StarterKit's undoRedo).
   `cxUndoSteps` decides where a new undo step starts, on top of the history's own rule (a 500 ms pause or a jump of the cursor):
   - a change that flips between deleting and typing (delete a line, retype at once: two steps, not one);
   - a paste, a cut, a drop, and anything a command marks with `OWN_STEP` (a picker choice, an image, a template, an AI replacement):
     each is one step of its own, and the next change starts another.
   Autosave never touches the editor, so none of this is reset by a save. The history is kept in memory only (`undoStash`,
   `undoTake`): when a note is closed its history is put by, and given back to the editor that opens the same text again; it
   is never written to storage, and a reload loses it. */
import { Extension, Plugin, PluginKey, closeHistory } from "tiptap";

/** The depth of Notes' history (StarterKit's is 100). */
export const UNDO_DEPTH = 500;
/** A transaction with this meta is one undo step of its own: `editor.chain().focus().setMeta(OWN_STEP, true)…`. */
export const OWN_STEP = "cxStep";
/** How many closed notes keep their history. */
export const STASH_MAX = 5;

/** @param {any} tr @returns {"del"|"ins"} deleting only (nothing put in), else typing/inserting */
function changeKind(tr) {
  let put = 0, cut = 0;
  for (const s of tr.steps) { const part = s.slice; if (part) { put += part.size; cut += (s.to - s.from) || 0; } else put += 1; }
  return put === 0 && cut > 0 ? "del" : "ins";
}
/** @param {any} tr */
const ownStep = tr => !!tr.getMeta(OWN_STEP) || !!tr.getMeta("paste") || ["paste", "cut", "drop"].includes(tr.getMeta("uiEvent"));
/** The history plugin of a state. @param {any} state */
const histPlugin = state => state.plugins.find((/** @type {any} */ p) => /^history\$/.test(p.key));
/** Is this transaction an undo or a redo? @param {any} state @param {any} tr */
const isHistoryTr = (state, tr) => { const p = histPlugin(state); return !!(p && tr.getMeta(p)); };

const key = new PluginKey("cxUndoSteps");
/** The extension Notes passes. */
export const cxUndoSteps = Extension.create({ name: "cxUndoSteps", addProseMirrorPlugins: () => [new Plugin({ key,
  state: {
    init: () => ({ last: /** @type {string|null} */ (null), closeNext: false }),
    apply: (tr, v, _old, state) => {
      if (!tr.docChanged) return v;
      if (isHistoryTr(state, tr)) return { last: null, closeNext: false };
      if (tr.getMeta("addToHistory") === false) return v;
      const own = ownStep(tr);
      return { last: own ? null : changeKind(tr), closeNext: own };
    } },
  /* The history plugin reads a transaction's close-history mark when it applies it, after this filter: marking it here puts
     the change in a new step. (A filter that only reads and marks; it never refuses.) */
  filterTransaction(tr, state) {
    if (!tr.docChanged || tr.getMeta("addToHistory") === false || isHistoryTr(state, tr)) return true;
    const v = key.getState(state);
    if (!v) return true;
    if (ownStep(tr) || v.closeNext || (v.last && changeKind(tr) !== v.last)) closeHistory(tr);
    return true;
  } })] });

/* ----- the history of a closed note, kept in memory (the last STASH_MAX notes) ----- */
/** @typedef {{map: any, step: ({ctor: any, json: any})|undefined, selection: any, mirrorOffset: any}} PackedItem */
/** @typedef {{items: PackedItem[], eventCount: number}} PackedBranch */
/** @typedef {{doc: string, item: any, done: PackedBranch, undone: PackedBranch}} Stash */
/** @type {Map<string, Stash>} */
const stash = new Map();

/** @param {any} b @returns {PackedBranch} */
const pack = b => ({ eventCount: b.eventCount, items: b.items.flatten().map((/** @type {any} */ i) => ({ map: i.map,
  step: i.step ? { ctor: i.step.constructor, json: i.step.toJSON() } : undefined, selection: i.selection, mirrorOffset: i.mirrorOffset })) });

/** Put the history of `editor` (about to be destroyed) by for the note at `path`. Nothing is kept when there is nothing to undo or redo.
    @param {string} path @param {any} editor */
export function undoStash(path, editor) {
  stash.delete(path);
  if (!path || !editor || editor.isDestroyed) return;
  const st = editor.state, p = histPlugin(st);
  if (!p) return;
  const hs = p.getState(st);
  if (!hs.done.eventCount && !hs.undone.eventCount) return;
  const first = hs.done.items.length ? hs.done.items.get(0) : hs.undone.items.get(0);
  stash.set(path, { doc: JSON.stringify(st.doc.toJSON()), item: first.constructor, done: pack(hs.done), undone: pack(hs.undone) });
  while (stash.size > STASH_MAX) stash.delete(/** @type {string} */ (stash.keys().next().value));
}

/** Give the note at `path` its history back, if the text `editor` opened with is exactly the text it was closed with (the file is
    unchanged); otherwise the history stays empty. The stash is used once. @param {string} path @param {any} editor @returns {boolean} */
export function undoTake(path, editor) {
  const s = stash.get(path);
  stash.delete(path);
  if (!s || !editor || editor.isDestroyed) return false;
  const st = editor.state, p = histPlugin(st);
  if (!p || JSON.stringify(st.doc.toJSON()) !== s.doc) return false;
  const hs = p.getState(st), schema = st.schema;
  /** @param {PackedBranch} b */
  const unpack = b => new hs.done.constructor(hs.done.items.append(b.items.map(i => {
    const it = Object.create(s.item.prototype);
    it.map = i.map; it.step = i.step ? i.step.ctor.fromJSON(schema, i.step.json) : undefined; it.selection = i.selection; it.mirrorOffset = i.mirrorOffset;
    return it;
  })), b.eventCount);
  try {
    const next = new hs.constructor(unpack(s.done), unpack(s.undone), null, 0, -1);
    editor.view.dispatch(st.tr.setMeta(p, { redo: false, historyState: next }).setMeta("addToHistory", false));
    return true;
  } catch (e) { return false; }
}
/** Forget every kept history. */
export function undoForget() { stash.clear(); }
/* ===== end #175 ===== */
