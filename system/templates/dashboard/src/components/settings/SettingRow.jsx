// @ts-check
/* SettingRow (BL-320): one row of Settings, as the page's `row()` draws it (`.srow`: the label and its line on the left, the
   control on the right), with the "changed" dot and Reset. The label names the control (aria-labelledby) and the line
   describes it (aria-describedby); a row with several controls is a group named by its label. Reset puts every key of the
   row back to its default through /api/settings/reset; a row whose setting is changed only at set-up says so instead. */
import { useState } from "preact/hooks";
import { snack } from "../../core/server.js";
import { resetSettings } from "../../stores/settings.js";

let N = 0;
/** A page-unique id for a row's label (its own prefix: the snapshots renumber each prefix's ids in order). */
export const rowId = () => "ss" + (++N);

/** @typedef {{id:string, label:string, line?:string, note?:string, changed:boolean, keys:string[], resettable?:boolean,
     fixedWhy?:string, saved?:boolean, children?:any}} SettingRowProps */

/** @param {SettingRowProps} props */
export function SettingRow({ id, label, line, note, changed, keys, resettable = true, fixedWhy = "", saved = false, children }) {
  const [busy, setBusy] = useState(false);
  const reset = async () => {
    setBusy(true);
    const r = await resetSettings(keys);
    setBusy(false);
    snack(r.ok ? (r.reset.length ? `${label}: back to its default` : `${label} was already at its default`) : r.message);
  };
  return (
    <div class="srow" data-keys={keys.join(" ")}>
      <div>
        <span id={id}>{label}</span>
        {changed && <span class="setdot" role="img" aria-label="Changed from the default" title="Changed from the default"></span>}
        {(line || note) && <small id={id + "h"}>{line}{note ? <span class="setnote">{line ? " " : ""}{note}</span> : null}</small>}
        {!resettable && fixedWhy && <small class="setfixed">Set at set-up: {fixedWhy}</small>}
      </div>
      <div class="setctl">
        {saved && <span class="saved" role="status">Saved</span>}
        {children}
        {changed && resettable && (
          <button type="button" class="mini setreset" disabled={busy} aria-label={`Reset ${label} to its default`}
            title="Back to the default" onClick={reset}>Reset</button>
        )}
      </div>
    </div>
  );
}
