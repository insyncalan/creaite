// @ts-check
/* PeopleParts (#247, #248): the pieces the project settings page's People view and the People page share (the register is one
   thing, so it looks and behaves the same in both): a count that opens Work, the name cell, the search box and the two-pane
   filter (the FilterBar block's funnel and field picker, WHO and TIDY UP, with counts, "Showing x of y", Clear all and Done),
   the chips of what is on, and the edit form. Data and saving are stores/peopleRegister.js; nothing here writes.
   BL-288: the star for a followed person and the Follow tick are drawn only when the caller personPasses `follow` (the project
   settings page); the People page never does. */
import { render } from "preact";
import { signal } from "@preact/signals";
import { useLayoutEffect, useRef, useState } from "preact/hooks";
import { Dialog } from "../Dialog.jsx";
import { drawFilterBar } from "../FilterBar.jsx";
import { Icon } from "../Icon.jsx";
import { navOf } from "../../core/nav.js";
import { P, pName } from "../../core/data.js";
import {
  clearFilter, filterAny, filterCount, missingWords, nameTaken, personPasses, peopleFields,
} from "../../stores/peopleRegister.js";

/** @typedef {import("../../stores/peopleRegister.js").PersonRow} PersonRow */
/** @typedef {import("../../stores/peopleRegister.js").PeopleFilterState} PeopleFilterState */
/** @typedef {import("../../stores/peopleRegister.js").PeopleField} PeopleField */

/** @param {number} n @param {string} w */
export const peoplePlural = (n, w) => `${n} ${w}${n === 1 ? "" : "s"}`;
/** @param {number} n */
export const peopleWord = n => peoplePlural(n, "person").replace(/persons$/, "people");

/** A figure that opens Work so (core/nav.js countLink, as elements); a zero stays plain.
    @param {{n: number, label: string, nav: string, extra?: any, late?: boolean}} props */
export function Count({ n, label, nav, extra, late }) {
  if (!n) return <span class={late ? "late" : undefined}>0</span>;
  return <a href="#" class={`cntl${late ? " late" : ""}`} data-nav={navOf(nav, extra)} data-n={String(n)} aria-label={`${label}, open in Work`}>{n}</a>;
}

/** The star beside a followed person's name: the project settings page only (BL-288). */
export const Star = () => (
  <svg class="i pstar" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round" role="img" aria-label="Followed">
    <path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.5 2.9 1-6.1L3.2 9.5l6.1-.9z" />
  </svg>
);

/** The name (it opens their work; a right-click is the person menu, with Draft email), "(you)", "needs details" with what is
    missing, and the codes of the other projects they are on. `you`: Alan's own row reads "You (name)" (the People page).
    @param {{x: PersonRow, code?: string, follow?: boolean, codes?: boolean, you?: boolean}} props */
export function NameCell({ x, code, follow, codes, you }) {
  const also = codes ? x.on.filter(c => c !== code) : [];
  return (
    <td class="title">
      <a href="#" class="plink2" data-person={x.n} title={x.me ? "Open My work" : `Open ${x.n}’s work`}>{you && x.me ? `You (${x.n})` : x.n}</a>
      {follow && x.followed ? <> <Star /></> : null}
      {x.me && !you ? <> <span class="tag">(you)</span></> : null}
      {x.missing.length ? <> <span class="tag warn" data-needs title={missingWords(x)}>needs details</span></> : null}
      {also.map(c => <span key={c}> <span class="tag pcodetag" title={`Also on ${pName(c)}`}>{c}</span></span>)}
    </td>
  );
}

/** An empty cell's dash. @param {{v?: string}} props */
export const Dash = ({ v }) => v ? <>{v}</> : <span class="sub">—</span>;

/** The search box and the funnel. `ids` is the view's own id prefix (two views must never share ids).
    @param {{L: PersonRow[], F: PeopleField[], s: PeopleFilterState, ids: string, onChange: () => void}} props */
export function PeopleTools({ L, F, s, ids, onChange }) {
  const host = useRef(/** @type {HTMLSpanElement|null} */ (null));
  useLayoutEffect(() => { if (host.current) drawBar(host.current, L, F, s, ids, onChange); });
  return (
    <div class="toolbar pmtools" role="search">
      <input id={`${ids}Q`} type="search" placeholder="Search name, alias, email or role" aria-label="Search people" autocomplete="off" value={s.q}
        onInput={e => { s.q = /** @type {HTMLInputElement} */ (e.target).value; onChange(); }}
        onKeyDown={e => { if (e.key === "Escape" && s.q) { e.preventDefault(); e.stopPropagation(); s.q = ""; onChange(); } }} />
      <span class="dd" id={`${ids}Fdd`} ref={host}></span>
    </div>
  );
}

/** @param {Element} h @param {PersonRow[]} L @param {PeopleField[]} F @param {PeopleFilterState} s @param {string} ids @param {() => void} onChange */
function drawBar(h, L, F, s, ids, onChange) {
  if (F.length && !F.some(f => f[0] === s.pk)) s.pk = F[0][0];
  const shown = L.filter(x => personPasses(x, F, s)).length, n = filterCount(F, s);
  drawFilterBar(h, {
    bare: true,
    fields: F.map(f => ({ id: f[0], label: f[1], section: f[2], note: f[5] || undefined, on: s.f[f[0]].size > 0, selected: s.f[f[0]],
      mark: s.f[f[0]].size ? String(s.f[f[0]].size) : "",
      options: () => f[3].map(([v, l]) => ({ value: v, label: l, count: L.filter(x => personPasses(x, F, s, f[0]) && f[4](x, v)).length })) })),
    onSelect: (k, vals) => { const set = s.f[k]; if (!set) return; set.clear(); vals.forEach(v => set.add(v)); onChange(); },
    more: { id: `${ids}FBtn`, menuId: `${ids}FMenu`, label: n ? `Filter people: ${n} on` : "Filter people", menuLabel: "Filter people", count: n, on: !!n,
      key: "Shift+F", listLabel: "Filters", headId: `${ids}Fph`, field: s.pk, onField: k => { s.pk = k; onChange(); },
      result: `Showing ${shown} of ${L.length}`, resultId: `${ids}FpResult`, doneId: `${ids}FpDone`,
      clearAll: filterAny(F, s) ? { id: `${ids}FpClear`, run: () => { clearFilter(s); onChange(); } } : null },
  });
}

/** The chips of what is on, Clear all and the count line. @param {{F: PeopleField[], s: PeopleFilterState, ids: string, count: string, onChange: () => void}} props */
export function PeopleApplied({ F, s, ids, count, onChange }) {
  const on = F.filter(f => s.f[f[0]].size);
  const label = (/** @type {PeopleField} */ f) => { const v = [...s.f[f[0]]]; return `${f[1]}: ${v.length <= 2 ? v.map(x => (f[3].find(o => o[0] === x) || [x, x])[1]).join(", ") : v.length + " chosen"}`; };
  return (
    <div class="wapplied" id={`${ids}Applied`}>
      {on.map(f => <span class="fchip" key={f[0]}>{label(f)}<button type="button" aria-label={`Remove the ${f[1].toLowerCase()} filter`} data-tip={`Remove the ${f[1].toLowerCase()} filter`}
        onClick={() => { s.f[f[0]].clear(); onChange(); }}><Icon name="x" /></button></span>)}
      {s.q.trim() ? <span class="fchip">Search: “{s.q.trim()}”<button type="button" aria-label="Clear the search" data-tip="Clear the search" onClick={() => { s.q = ""; onChange(); }}><Icon name="x" /></button></span> : null}
      {filterAny(F, s) ? <button type="button" class="linkbtn" id={`${ids}ClearF`} onClick={() => { clearFilter(s); onChange(); }}>Clear all</button> : null}
      <span class="sp"></span><span class="sub" id={`${ids}Count`} role="status">{count}</span>
    </div>
  );
}

/** The fields and filter of a view, read again on every draw. @param {PersonRow[]} L @param {PeopleFilterState} s @param {{code?: string, follow?: boolean}} opt */
export function useFields(L, s, opt) { return peopleFields(L, s, opt); }

/** A redraw for a view whose state is a plain object. */
export function useRedraw() { const [, set] = useState(0); return () => set(n => n + 1); }

// ----- the edit form: one entry for the person, the same on every project

/** @typedef {{x: PersonRow|null, isNew?: boolean, code?: string, follow?: boolean}} FormTarget */
/** @typedef {{email: string, aliases: string[], org: string, role: string, projects: string[], follow?: boolean}} FormValues */

/** @typedef {{onSave: (name: string, v: FormValues, isNew: boolean) => Promise<any>, onRemove?: (name: string) => void}} FormHandlers */
/** the form's one instance (both views use it, so its ids exist once): what it is open for, and what Save and Remove do */
export const personForm = signal(/** @type {{t: FormTarget, h: FormHandlers}|null} */ (null));
let formHost = /** @type {HTMLElement|null} */ (null);
/** Open the person form. @param {FormTarget} t @param {FormHandlers} h */
export function openPersonForm(t, h) {
  if (!formHost) { formHost = document.createElement("div"); formHost.id = "personEditHost"; document.body.appendChild(formHost); render(<PersonFormHost />, formHost); }
  personForm.value = { t, h };
}
function PersonFormHost() {
  const cur = personForm.value;
  return <PersonForm t={cur ? cur.t : null} onClose={() => { personForm.value = null; }} onSave={cur ? cur.h.onSave : async () => null} onRemove={cur ? cur.h.onRemove : undefined} />;
}

/** The person form: Full name, Email, Aliases, Organisation, Role, On projects, and (project settings only) Follow.
    Buttons: Remove from this project (on a project page, when they are on it), Cancel, Save. A person with no email can be saved.
    @param {{t: FormTarget|null, onClose: () => void, onSave: (name: string, v: FormValues, isNew: boolean) => Promise<any>, onRemove?: (name: string) => void}} props */
export function PersonForm({ t, onClose, onSave, onRemove }) {
  const x = t && t.x, open = !!t, ref = useRef(/** @type {HTMLDivElement|null} */ (null)), [err, setErr] = useState("");
  const val = (/** @type {string} */ id) => ((/** @type {HTMLInputElement|null} */ (ref.current && ref.current.querySelector("#" + id))) || { value: "" }).value.trim();
  const save = async () => {
    const name = t && t.isNew ? val("peName") : (x ? x.n : "");
    if (!name) { setErr("A full name is required."); return; }
    if (t && t.isNew && nameTaken(name)) { setErr(`${name} is already in the register.`); return; }
    const ticks = [...((ref.current && ref.current.querySelectorAll("[data-pe-proj]")) || [])].filter(b => /** @type {HTMLInputElement} */ (b).checked).map(b => /** @type {HTMLElement} */ (b).dataset.peProj || "");
    const fol = /** @type {HTMLInputElement|null} */ (ref.current && ref.current.querySelector("#peFollow"));
    setErr("");
    /** @type {FormValues} */
    const v = { email: val("peEmail"), aliases: val("peAliases").split(",").map(a => a.trim()).filter(Boolean), org: val("peOrg"), role: val("peRole"), projects: ticks };
    if (t && t.follow && fol) v.follow = fol.checked;
    onClose(); await onSave(name, v, !!(t && t.isNew));
  };
  const k = t ? (t.isNew ? "new" : x ? x.n : "") : "";
  return (
    <Dialog id="personEdit" class="prepdlg" open={open} onClose={() => { setErr(""); onClose(); }} labelledBy="peTitle" focus={t && t.isNew ? "#peName" : "#peEmail"}>
      {open ? <div ref={ref} key={k}>
        <div class="prephead"><div style="flex:1"><div class="sub">One record for the person, the same on every project</div>
          <h2 id="peTitle">{t && t.isNew ? "Add a person" : `Edit ${x ? x.n : ""}`}</h2></div>
          <button type="button" class="iconbtn" id="peClose" aria-label="Close" onClick={onClose}><Icon name="x" /></button></div>
        <div class="prepbody"><div class="pdgrid">
          <label for="peName">Full name</label><input type="text" id="peName" autocomplete="off" defaultValue={x ? x.n : ""} readOnly={!(t && t.isNew)} />
          {t && t.isNew ? null : <span class="pdh">Names are not changed here; ask creaite fixes a spelling across every item.</span>}
          <label for="peEmail">Email</label><input type="text" id="peEmail" autocomplete="off" placeholder="name@company.com" defaultValue={x ? x.email : ""} />
          <span class="pdh">Used to match mail and to address a drafted email. With none, a draft is still made, with nothing in To.</span>
          <label for="peAliases">Aliases</label><input type="text" id="peAliases" autocomplete="off" placeholder="Short forms, separated by commas" defaultValue={x ? x.aliases.join(", ") : ""} />
          <span class="pdh">Other names and addresses that mean this person in minutes and mail.</span>
          <label for="peOrg">Organisation</label><input type="text" id="peOrg" autocomplete="off" defaultValue={x ? x.org : ""} />
          <label for="peRole">Role</label><input type="text" id="peRole" autocomplete="off" defaultValue={x ? x.role : ""} />
          <span class="pdh">Organisation and role are one entry for the person, the same on every project.</span>
          <span class="pdlab" id="peProjL">On projects</span>
          <div id="peProj" class="setticks" role="group" aria-labelledby="peProjL">{P.map(p => (
            <label class="settick" key={p.code}><input type="checkbox" data-pe-proj={p.code} defaultChecked={x ? x.on.includes(p.code) : (t && t.code) === p.code} /> {p.name}</label>))}</div>
          <span class="pdh">Tick the projects they belong to; with none ticked they sit in Not on any project yet.</span>
          {t && t.follow ? <>
            <span class="pdlab">Follow</span>
            <label class="settick"><input type="checkbox" id="peFollow" defaultChecked={!!(x && x.followed)} /> Follow this person</label>
            <span class="pdh">Their mail and chats are flagged for you first, and a star shows beside their name in this list, for you only. It never appears in a report, an export or a draft.</span>
          </> : null}
        </div>
        <div class="sub pemsg" id="peErr" role="alert">{err}</div>
        <div class="deacts">
          {onRemove && x && t && t.code && x.on.includes(t.code) ? <button type="button" class="btn" id="peRemove" onClick={() => { onClose(); onRemove(x.n); }}>Remove from this project</button> : null}
          <span class="sp"></span>
          <button type="button" class="btn" id="peCancel" onClick={onClose}>Cancel</button>
          <button type="button" class="btn primary" id="peSave" onClick={save}>Save</button>
        </div></div>
      </div> : null}
    </Dialog>
  );
}
