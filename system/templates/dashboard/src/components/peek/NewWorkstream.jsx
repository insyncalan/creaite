// @ts-check
/* NewWorkstream (BL-187, BL-316): the peek's small form for a new workstream, opened from the Workstream list's "Add
   workstream…" option (its id, pkWsAdd, is the way in). A Picker popover (openPopover): named "New workstream for <project>",
   focus to the name (or, with a name given, the lead), Esc and Cancel close it with focus back on the Workstream control, Enter
   in a field or "Add and use it" adds. The details (BL-58's) are suggested from the project's items as the name is typed, until
   one is changed by hand. panel.js does the adding (`onAdd`: an error to show, or nothing when it has closed the form). It keeps
   the old form's classes (.pkws, .pkws-h, data-wsn …). Text only through JSX. */
import { useRef, useState } from "preact/hooks";
import { closePicker, flushPicker, openPopover } from "../Picker.jsx";

/** @typedef {{title: string, name: string, fields: [string, string][], suggest: (name: string) => Record<string, any>, note: string,
    onAdd: (v: Record<string, string>) => Promise<string | void> | string | void, onClose?: (how: string) => any}} NewWorkstreamProps */

/** @param {NewWorkstreamProps} props */
function NewWorkstream({ title, name, fields, suggest, note, onAdd }) {
  const [vals, setVals] = useState(() => { const s = name ? suggest(name) : {};
    return /** @type {Record<string, string>} */ ({ name, ...Object.fromEntries(fields.map(([f]) => [f, String(s[f] || "")])) }); });
  const [err, setErr] = useState(""), touched = useRef(new Set()), box = useRef(/** @type {HTMLDivElement | null} */ (null));
  /** @param {string} f @param {string} v */
  const set = (f, v) => {
    const next = { ...vals, [f]: v };
    if (f !== "name") touched.current.add(f);
    else if (v.trim()) { const sg = suggest(v.trim()); fields.forEach(([q]) => { if (!touched.current.has(q)) next[q] = String(sg[q] || ""); }); }
    setVals(next); flushPicker();
  };
  const add = async () => {
    const ins = /** @type {HTMLInputElement[]} */ ([...(box.current?.parentElement?.querySelectorAll("[data-wsn]") || [])]);   /* what is in the fields, however it got there */
    const v = ins.length ? Object.fromEntries(ins.map(i => [i.dataset.wsn || "", i.value.trim()]))
      : Object.fromEntries(Object.entries(vals).map(([k, x]) => [k, String(x).trim()]));
    if (!v.name) { setErr("Give the workstream a name."); flushPicker(); /** @type {HTMLElement | null | undefined} */ (box.current?.querySelector('[data-wsn="name"]'))?.focus(); return; }
    const e = await onAdd(v); if (e) { setErr(e); flushPicker(); }
  };
  /** @param {KeyboardEvent} e */
  const enter = e => { if (e.key === "Enter" && !e.metaKey && !e.ctrlKey) { e.preventDefault(); e.stopPropagation(); add(); } };
  /** @param {string} f @param {string} label @param {string} [ph] */
  const field = (f, label, ph) => (
    <label key={f}>{label}<input type="text" data-wsn={f} value={vals[f]} autocomplete="off" placeholder={ph} onKeyDown={enter}
      onInput={e => set(f, /** @type {HTMLInputElement} */ (e.currentTarget).value)} /></label>
  );
  return (
    <div ref={box} style="display:contents">
      <div class="pkws-h">{title}</div>
      {field("name", "Name")}
      {fields.map(([f, l]) => field(f, l, f === "lead" ? "A person from the people register" : undefined))}
      <div class="sub pkws-n">{note}</div>
      <div class="pkerr" role="alert">{err}</div>
      <div class="pkws-b">
        <button type="button" class="mini" data-wsf="cancel" onClick={() => closePicker("esc")}>Cancel</button>
        <button type="button" class="mini primary" data-wsf="add" onClick={add}>Add and use it</button>
      </div>
    </div>
  );
}

/** Open the form from `anchor` (the Workstream control). @param {HTMLElement} anchor @param {NewWorkstreamProps} props */
export function openNewWorkstream(anchor, props) {
  return openPopover(anchor, { label: props.title, cls: "pkws", id: "pkWsForm", via: "pkWsAdd", onClose: props.onClose,
    focus: props.name ? '[data-wsn="lead"]' : '[data-wsn="name"]', content: () => <NewWorkstream {...props} /> });
}
