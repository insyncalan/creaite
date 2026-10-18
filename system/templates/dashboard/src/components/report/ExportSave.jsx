// @ts-check
/* ExportSave (#220; mockup: dev/mockups/reporting-hub-mockup.html, Export to HTML): what an export shows. A taken name opens a dialog
   (Add a number, the default; Rename it, a field the dialog's full width with the whole name; Overwrite the existing file, backed up
   first; Cancel saves nothing). A save shows "Saved <file> in <project> › Reports" with the folder as a link and two actions, Show in
   Finder and Open; a failed save says why and that nothing was written. The server decides; this only asks and passes the choice. */
import { useEffect, useState } from "preact/hooks";
import { Dialog } from "../Dialog.jsx";
import { answerClash, cancelClash, exportClash, exportFailed, exportSaved, openFolder, openSaved, showInFinder } from "../../stores/exportSave.js";

const dismiss = () => { exportSaved.value = null; exportFailed.value = ""; };

/** The dialog for a taken name. */
function ClashDialog() {
  const c = exportClash.value, r = c && c.r;
  const [choice, setChoice] = useState(/** @type {"number"|"rename"|"overwrite"} */ ("number"));
  const [typed, setTyped] = useState("");
  useEffect(() => { if (r) { setChoice("number"); setTyped(String(r.name || "")); } }, [r]);
  const name = String((r && r.name) || ""), ext = name.includes(".") ? name.slice(name.lastIndexOf(".")) : "";
  const go = () => { if (choice === "rename" && !typed.trim()) return; answerClash(choice, typed.trim()); };
  const radio = (/** @type {"number"|"rename"|"overwrite"} */ v) => <input type="radio" name="clash" value={v} checked={choice === v} onChange={() => setChoice(v)} />;
  return (
    <Dialog open={!!c} onClose={cancelClash} labelledBy="exportClashH" id="exportClashDlg" class="mnapprove" focus="#exportClashGo">
      <div class="mnap">
        <h2 id="exportClashH">A file with that name is already there</h2>
        <p class="sub" id="exportClashP">“{name}” is already in <a href="#" class="folderlink" data-export-folder onClick={(e) => { e.preventDefault(); if (r && r.folder) openFolder(r.folder); }}>{r && r.folder_label}</a>.</p>
        <fieldset class="mnap-g"><legend>What would you like to do?</legend>
          <label class="mnap-one">{radio("number")} <span>Add a number<span class="sub"> Saves as “{r && r.numbered}”</span></span></label>
          <label class="mnap-one">{radio("rename")} <span style="flex:1;min-width:0">Rename it
            <input class="pkdt" id="exportClashRename" aria-label="New file name" style="display:block;width:100%;margin-top:6px" value={typed}
              onFocus={() => setChoice("rename")} onInput={(e) => { setTyped(/** @type {HTMLInputElement} */ (e.target).value); setChoice("rename"); }} placeholder={`Name${ext}`} /></span></label>
          <label class="mnap-one">{radio("overwrite")} <span>Overwrite the existing file<span class="sub"> The earlier file is backed up first, as for any file change.</span></span></label>
        </fieldset>
        <div class="mnap-foot"><button type="button" class="btn" id="exportClashNo" onClick={cancelClash}>Cancel</button>
          <button type="button" class="btn primary" id="exportClashGo" onClick={go}>Save</button></div>
      </div>
    </Dialog>);
}

/** The message after a save (or a failed one). */
function SavedToast() {
  const r = exportSaved.value, bad = exportFailed.value;
  useEffect(() => {
    if (!r) return undefined;
    const t = setTimeout(dismiss, 15000);
    return () => clearTimeout(t);
  }, [r]);
  if (bad) return <div class="snack on" role="alert" data-export-failed><span>{bad}</span><button type="button" onClick={dismiss}>Close</button></div>;
  if (!r) return null;
  return (
    <div class="snack on" role="status" data-export-saved>
      <span>{r.replaced ? "Replaced" : "Saved"} {r.name} in <a href="#" class="folderlink" data-export-folder style="color:inherit"
        onClick={(e) => { e.preventDefault(); if (r.folder) openFolder(r.folder); }}>{r.folder_label}</a></span>
      <button type="button" onClick={() => { if (r.path) showInFinder(r.path); }}>Show in Finder</button>
      <button type="button" onClick={() => { if (r.path) openSaved(r.path); }}>Open</button>
    </div>);
}

/** The dialog and the message; drawn by the weekly and the client report views. */
export function ExportSave() {
  return <><ClashDialog /><SavedToast /></>;
}
