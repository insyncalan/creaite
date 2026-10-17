// @ts-check
/* PrepEditor (#111 piece A): the prep page's one text editor, saved as you type. THE SEAM FOR #122: this is the only place the
   page names an editor. Today it wraps TextEditor (the one editor in its plain-text form); when the shared rich editor (#122,
   a small toolbar when a field is focused) lands, swap the body of this component and nothing else on the page changes. The
   page gives it the saved text (`value`), and `onSave(text)` is called a moment after typing stops and at once when the box is
   left; an unchanged text is never saved. The label sits above it, as in the mockup. */
import { useEffect, useRef } from "preact/hooks";
import { TextEditor } from "../TextEditor.jsx";

/** How long typing must pause before it is saved, in milliseconds. */
export const SAVE_PAUSE = 700;

/**
 * @param {{id: string, label: string, value: string, onSave: (text: string) => void, rows?: number, placeholder?: string,
 *   hint?: string, ai?: import("../../core/editor.js").EdAi, cls?: string}} props
 */
export function PrepEditor({ id, label, value, onSave, rows = 3, placeholder, hint, ai, cls = "ppbox" }) {
  const last = useRef(value), timer = useRef(/** @type {any} */ (0)), typed = useRef(/** @type {string | null} */ (null));
  last.current = value;
  useEffect(() => () => { if (timer.current) clearTimeout(timer.current); }, []);
  const flush = () => {
    if (timer.current) { clearTimeout(timer.current); timer.current = 0; }
    const t = typed.current;
    typed.current = null;
    if (t !== null && t.trim() !== last.current.trim()) { last.current = t; onSave(t); }
  };
  return (
    <div class="ppfld">
      <label id={`${id}-l`}>{label}{hint ? <em> {hint}</em> : null}</label>
      <TextEditor id={id} cls={cls} rows={rows} value={value} placeholder={placeholder} labelledBy={`${id}-l`} ai={ai} links
        onInput={t => { typed.current = t; if (timer.current) clearTimeout(timer.current); timer.current = setTimeout(flush, SAVE_PAUSE); }}
        onCommit={t => { typed.current = t; flush(); }} />
    </div>
  );
}
