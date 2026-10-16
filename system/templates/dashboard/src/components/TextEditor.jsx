// @ts-check
/* BL-301 A (v2.0.0): the one editor (core/editor.js) as a building block, for a box of plain text (Prep's notes and
   questions, the Prep popup's shaped notes). It stays plain text, one paragraph a line, so what is saved is what a
   textarea gave; its element's `value` reads and sets the text as the textarea's did. `onInput(text)` runs on each change,
   `onCommit(text)` when the box is left. Undo, redo and the keys are the editor's. */
import { useEffect, useRef } from "preact/hooks";
import { creaiteEditor } from "../core/editor.js";

/**
 * @typedef {{id: string, value: string, cls?: string, rows?: number, multiline?: boolean, placeholder?: string,
 *   labelledBy?: string, describedBy?: string, onInput?: (text: string) => void, onCommit?: (text: string) => void,
 *   ai?: import("../core/editor.js").EdAi, links?: boolean}} Props
 */
/** A plain-text box on the one editor. @param {Props} props */
export function TextEditor({ id, value, cls, rows = 2, multiline = true, placeholder, labelledBy, describedBy, onInput, onCommit, ai, links = false }) {
  const box = useRef(/** @type {HTMLDivElement|null} */ (null));
  const ed = useRef(/** @type {import("../core/editor.js").EdHandle|null} */ (null));
  const on = useRef({ onInput, onCommit });
  on.current = { onInput, onCommit };
  useEffect(() => {
    const el = box.current;
    const h = creaiteEditor(el, { features: "plain", text: value, multiline, prop: "value", ...(links ? { links: true } : {}), ...(ai ? { ai } : {}) });   // BL-301 D
    ed.current = h;
    const blur = () => { if (on.current.onCommit) on.current.onCommit(h.value()); };
    const input = () => { if (on.current.onInput) on.current.onInput(h.value()); };
    el.addEventListener("blur", blur);
    el.addEventListener("input", input);
    return () => { el.removeEventListener("blur", blur); el.removeEventListener("input", input); h.destroy(); ed.current = null; };
  }, []);
  useEffect(() => {          // a new value from the store (Refresh, Regenerate, Use creaite's questions), never under the cursor
    const h = ed.current;
    if (h && document.activeElement !== h.el && h.value() !== value) h.setValue(value);
  }, [value]);
  return (
    <div ref={box} id={id} class={cls} role="textbox" aria-multiline={multiline ? "true" : "false"} aria-labelledby={labelledBy}
      aria-describedby={describedBy} data-ph={placeholder} spellcheck style={{ minHeight: `${rows * 19 + 14}px` }} />
  );
}
