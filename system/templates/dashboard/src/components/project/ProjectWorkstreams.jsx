// @ts-check
/* ProjectWorkstreams (#247): the project's own workstreams on its settings page (moved from Settings › People and projects, Alan,
   19-10-2026): Workstream, Lead, Keywords, Open items; Edit opens the row in place (name, lead, keywords; Merge into another of
   the project's; Retire); Add a workstream adds a row. No "Fix spellings" or "Show retired" footer. Saving is stores/workstreams.js. */
import { useState } from "preact/hooks";
import { psChanged, psTick } from "../../stores/projectSettings.js";
import { wsActive, wsAdd, wsMerge, wsRetire, wsUpdate } from "../../stores/workstreams.js";
import { who } from "../../core/page.js";

/** @param {Element} tr */
const valuesOf = tr => Object.fromEntries([...tr.querySelectorAll("[data-wsf]")].map(i => [/** @type {HTMLElement} */ (i).dataset.wsf, /** @type {HTMLInputElement} */ (i).value]));

/** A row being edited, or the new one (`w` null). @param {{code: string, w: any, others: any[], done: () => void}} props */
function EditRow({ code, w, others, done }) {
  const [err, setErr] = useState("");
  const save = async (/** @type {Element} */ tr) => {
    const v = /** @type {{name: string, lead: string, keywords: string}} */ (valuesOf(tr));
    const bad = w ? await wsUpdate(w.id, v) : await wsAdd(code, v);
    setErr(bad); if (!bad) { done(); psChanged(); }
  };
  const nm = w ? w.name : "new workstream";
  return (
    <tr class="wsedit" data-wsid={w ? w.id : ""}>
      <td><input type="text" data-wsf="name" aria-label={w ? `Name of ${w.name}` : "Name of the new workstream"} defaultValue={w ? w.name : ""} ref={el => { if (el && !el.dataset.f) { el.dataset.f = "1"; el.focus(); } }} />
        {err ? <span class="psmsg" role="alert" id="psWsErr">{err}</span> : null}</td>
      <td><input type="text" data-wsf="lead" aria-label={`Lead of ${nm}`} placeholder="A person from the people register" defaultValue={w ? w.lead || "" : ""} /></td>
      <td><input type="text" data-wsf="keywords" aria-label={`Keywords of ${nm}`} placeholder="Words that point to it" defaultValue={w ? w.keywords || "" : ""} /></td>
      <td class="num">{w ? (w.nA || 0) + (w.nR || 0) : ""}</td>
      <td class="mgract">
        <span class="wsacts">
          <button type="button" class="mini" data-ws-save onClick={e => save(/** @type {Element} */ (/** @type {HTMLElement} */ (e.currentTarget).closest("tr")))}>Save</button>
          <button type="button" class="mini" data-ws-cancel onClick={done}>Cancel</button>
          {w && others.length ? <select class="mini" data-ws-merge aria-label={`Merge ${w.name} into`} onChange={async e => {
            const to = /** @type {HTMLSelectElement} */ (e.target).value; if (!to) return; if (await wsMerge(w.id, to)) { done(); psChanged(); } }}>
            <option value="">Merge into…</option>{others.map(o => <option key={o.id} value={o.id}>{o.name}</option>)}</select> : null}
          {w ? <button type="button" class="mini no" data-ws-retire aria-label={`Retire ${w.name}`} onClick={async () => { if (await wsRetire(w.id)) { done(); psChanged(); } }}>Retire</button> : null}
        </span>
      </td>
    </tr>
  );
}

/** `match`: whether the page's search matches this card. @param {{code: string, match?: boolean}} props */
export function Workstreams({ code, match = true }) {
  psTick.value;          // redrawn by the page's tick (same props: a parent's re-render does not reach it)
  const [edit, setEdit] = useState(/** @type {string|null} */ (null)), L = wsActive(code);
  return (
    <div class="card" data-pscard data-cat="ws"><h2>Workstreams</h2>
      <div class="tbl" data-psrow hidden={!match}><table class="pstbl" id="psWs" aria-label="Workstreams"><thead><tr><th scope="col">Workstream</th><th scope="col">Lead</th><th scope="col">Keywords</th>
        <th scope="col" class="num">Open items</th><th scope="col"><span class="vh">Actions</span></th></tr></thead>
        <tbody>
          {L.map(w => edit === w.id ? <EditRow key={w.id} code={code} w={w} others={L.filter(o => o !== w)} done={() => setEdit(null)} /> : (
            <tr key={w.id} data-ws={w.name}><td>{w.name}</td><td>{w.lead ? who(w.lead) : <span class="sub">—</span>}</td>
              <td>{w.keywords ? <span class="sub">{w.keywords}</span> : <span class="sub">—</span>}</td><td class="num">{(w.nA || 0) + (w.nR || 0)}</td>
              <td class="mgract"><button type="button" class="mini" data-ws-edit={w.name} aria-label={`Edit ${w.name}`} onClick={() => setEdit(w.id)}>Edit</button></td></tr>))}
          {edit === "new" ? <EditRow code={code} w={null} others={[]} done={() => setEdit(null)} /> : null}
          {!L.length && edit !== "new" ? <tr><td class="sub" colSpan={5}>No workstreams yet.</td></tr> : null}
        </tbody></table></div>
      <p class="psfoot"><button type="button" class="btn sm" id="psAddWs" onClick={() => setEdit("new")}>Add a workstream</button></p>
      <p class="psnote psfoot">A lead and keywords help creaite match items from minutes and mail to the workstream. A rename renames its items too; Merge into moves its items to the other one; a retired workstream is no longer offered for new items, and its items keep the name. Each change has Undo.</p>
    </div>
  );
}
