// @ts-check
/* PeoplePage (#248, People page v2; locked mockup dev/mockups/people-page-v2-mockup.html): the home of the whole people register.
   Tabs Everyone, With work, Nothing assigned and Needs attention (the Tabs block; the tab is in the address, #people/<tab>, and
   remembered in this browser); columns Name, Email, Organisation, Role, Projects, Actions, RAID, Decisions, Overdue (what is
   still open, each opening Work so); the search and the same two-pane filter as the project page's People view (Project, How
   they're involved, Organisation; Needs attention: No email, No organisation, No role); Add a person; on each row Add details
   (when something is missing), Edit and Remove from the register, which asks first and has Undo. A name opens their page; a
   right-click is the person menu, with Draft email. No star for a followed person here (BL-288: only on the project settings
   page), no merge, and no "Press ? for help" line (as on Today). The pieces are components/people/PeopleParts.jsx; the data and
   the saves are stores/peopleRegister.js. */
import { render } from "preact";
import { useState } from "preact/hooks";
import { Tabs } from "../Tabs.jsx";
import { IconButton } from "../IconButton.jsx";
import { pName } from "../../core/data.js";
import { store } from "../../core/page.js";
import { navWrite } from "../../core/nav.js";
import { shared } from "../../core/state.js";
import { addPerson, inRegister, newFilter, ownedItems, personPasses, registerRows, removeFromRegister, savePerson } from "../../stores/peopleRegister.js";
import { Count, Dash, NameCell, PeopleApplied, PeopleTools, openPersonForm, peopleWord, peoplePlural, useFields } from "./PeopleParts.jsx";

/** @typedef {import("../../stores/peopleRegister.js").PersonRow} PersonRow */

export const PTABS = [["all", "Everyone"], ["work", "With work"], ["none", "Nothing assigned"], ["att", "Needs attention"]];
/** @param {any} t */
export const ptabOf = t => PTABS.some(x => x[0] === t) ? String(t) : "all";
const TAB_KEY = "creaite-peopletab";
/** @param {PersonRow} x */
const hasWork = x => x.oa.length + x.or.length + x.dw.length > 0;
/** @type {Record<string, (x: PersonRow) => boolean>} */
const IN_TAB = { all: () => true, work: x => hasWork(x) || x.me, none: x => !hasWork(x) && !x.me, att: x => x.missing.length > 0 };
/** @param {string} t */
export function setPeopleTab(t) { shared.PTAB = ptabOf(t); store.set(TAB_KEY, shared.PTAB); }
/** the tab this browser last used */
export const savedPeopleTab = () => ptabOf(store.get(TAB_KEY, "all"));

/** the sorts, by the headings' keys (settings.js's [data-psort] click handler flips shared.PSORT and redraws: name, org and role
    start A to Z, the counts start with the most) @type {Record<string, (x: PersonRow) => any>} */
const SORTS = { name: x => x.n.toLowerCase(), email: x => x.email.toLowerCase(), org: x => x.org.toLowerCase(), role: x => x.role.toLowerCase(),
  oa: x => x.oa.length, or: x => x.or.length, dw: x => x.dw.length, late: x => x.late };
const PL_COLS = [["name", "Name"], ["email", "Email"], ["org", "Organisation"], ["role", "Role"], ["", "Projects"], ["oa", "Actions", "Open actions"],
  ["or", "RAID", "Open risks and issues"], ["dw", "Decisions", "Decisions waiting on them"], ["late", "Overdue"]];
const ST = { s: newFilter() };
/** @returns {{col: string, dir: string}} */
const sortOf = () => shared.PSORT && SORTS[shared.PSORT.col] ? shared.PSORT : { col: "late", dir: "desc" };
/** @param {any[]} L */
const plOwners = L => [...new Set(L.map(i => i.o || i.by).filter(Boolean))];

const plHandlers = {
  onSave: (/** @type {string} */ name, /** @type {any} */ v, /** @type {boolean} */ isNew) => isNew ? addPerson(name, v) : savePerson(name, v),
};

/** Remove from the register: it asks first (the delete pattern), then one proposal with Undo. @param {{x: PersonRow}} props */
function RemoveButton({ x }) {
  const [ask, setAsk] = useState(false);
  if (!inRegister(x.n)) return <IconButton icon="trash" label="Remove from the register" name={`Remove from the register: ${x.n}`} why="Only their items name them: there is no record to remove" />;
  if (!ask) return <IconButton icon="trash" label="Remove from the register" name={`Remove from the register: ${x.n}`} cls="no" data={{ "pl-remove": x.n }} onClick={() => setAsk(true)} />;
  const owned = ownedItems(x.n);   // #248 M3: refused while they own items; nothing is reassigned for Alan
  if (owned) return (
    <span class="psask" role="group" aria-label={`${x.n} can't be removed yet`}>
      <span class="sub" role="alert" data-pl-remove-refused={x.n}>{x.n} owns {peoplePlural(owned, "item")}. Reassign them first, then remove {x.n} from the register.</span>
      <button type="button" class="btn sm" data-pl-remove-no={x.n} onClick={() => setAsk(false)}>OK</button>
    </span>
  );
  return (
    <span class="psask" role="group" aria-label={`Remove ${x.n} from the register?`}>
      <span class="sub" role="alert">Remove {x.n} from the register? Their items keep the name.</span>
      <button type="button" class="btn danger sm" data-pl-remove-yes={x.n} onClick={() => { setAsk(false); removeFromRegister(x.n); }}>Remove</button>
      <button type="button" class="btn sm" data-pl-remove-no={x.n} onClick={() => setAsk(false)}>Keep</button>
    </span>
  );
}

/** @param {{x: PersonRow}} props */
function PlRow({ x }) {
  const nm = x.me ? "you" : x.n, late = x.lateItems;
  const edit = () => openPersonForm({ x }, plHandlers);
  return (
    <tr data-pn={x.n} data-pp={x.n} class={`click${x.missing.length ? " nr" : ""}`}>
      <NameCell x={x} you />
      <td>{x.email ? x.email : <Dash />}</td><td><Dash v={x.org} /></td><td><Dash v={x.role} /></td>
      <td><span class="pj">{x.on.length ? x.on.map((c, i) => <span key={c}>{i ? " " : ""}<span class="pcode plink" data-proj={c} role="link" tabindex={0} title={`Open ${pName(c)}`}>{pName(c)}</span></span>) : <Dash />}</span></td>
      <td class="num"><Count n={x.oa.length} label={`${peoplePlural(x.oa.length, "open action")} owned by ${nm}`} nav="actions:open:" extra={{ o: plOwners(x.oa) }} /></td>
      <td class="num"><Count n={x.or.length} label={`${peoplePlural(x.or.length, "open RAID item")} owned by ${nm}`} nav="raid:open:" extra={{ o: plOwners(x.or) }} /></td>
      <td class="num"><Count n={x.dw.length} label={`${peoplePlural(x.dw.length, "decision")} waiting on ${nm}`} nav="decisions:pending:" extra={{ o: plOwners(x.dw) }} /></td>
      <td class={`num${x.late ? " late" : ""}`}><Count n={x.late} label={`${peoplePlural(x.late, "overdue item")} owned by ${nm}`} nav="all:open:"
        extra={{ st: ["Open"], due: ["overdue"], ty: ["Action", "Risk", "Issue", "Assumption", "Dependency"], o: plOwners(late) }} /></td>
      <td class="mgract">{x.me ? <span class="x">Change in Settings › Essentials › You</span> : <>
        {x.missing.length ? <button type="button" class="mini" data-pl-details={x.n} aria-haspopup="dialog" aria-label={`Add details for ${x.n}`} onClick={edit}>Add details</button> : null}
        <IconButton icon="pencil" label="Edit details" name={`Edit details: ${x.n}`} haspopup="dialog" data={{ "pl-edit": x.n }} onClick={edit} />
        <RemoveButton x={x} /></>}</td>
    </tr>
  );
}

/** A heading; a click sorts by it (settings.js's [data-psort] handler: the same column again reverses it, and focus stays on it).
    `so` is the sort now (a prop, so the heading redraws when it changes). @param {{col: string[], so: {col: string, dir: string}}} props */
function Head({ col, so }) {
  const [k, label, tip] = col;
  if (!k) return <th scope="col">{label}</th>;
  const on = so.col === k, num = !["name", "email", "org", "role"].includes(k);
  return (
    <th scope="col" class={num ? "num" : undefined} aria-sort={on ? (so.dir === "asc" ? "ascending" : "descending") : "none"} data-psort={k}>
      <button type="button" class="thsort" title={tip}>{label}{on ? (so.dir === "asc" ? " ▲" : " ▼") : ""}</button>
    </th>
  );
}

/** `t` changes on every draw, so the page redraws with the data as it is now. @param {{t?: number}} _props */
export function PeoplePage(_props) {
  const s = ST.s, tab = ptabOf(shared.PTAB);
  const all = registerRows(), F = useFields(all, s, {}), hit = all.filter(x => personPasses(x, F, s));
  const so = sortOf(), f = SORTS[so.col], dir = so.dir === "asc" ? 1 : -1;
  const L = hit.filter(IN_TAB[tab]).sort((a, b) => (a.me ? -1 : b.me ? 1 : 0)   /* you first, always */ || (() => { const x = f(a), y = f(b); return (x < y ? -1 : x > y ? 1 : 0) * dir; })() || a.n.localeCompare(b.n));
  const need = all.filter(IN_TAB.att).length;
  const count = `Showing ${L.length} of ${peopleWord(all.length)}${need ? ` · ${need} need${need === 1 ? "s" : ""} attention` : ""}`;
  return (
    <>
      <p class="sub plintro">Everyone creaite knows, one record each. A name on any item has a record here; one marked “needs details” is missing an email, organisation or role. Select a name for their page; right-click to draft an email with their work. Counts only.</p>
      <div class="tabhost"><Tabs id="ptabs" className="tabs" label="People" controls="peopleTbl" wrap selected={tab}
        items={PTABS.map(([id, label]) => ({ id, label, count: hit.filter(IN_TAB[id]).length, data: { ptab: id } }))}
        onSelect={id => { if (id === tab) return; setPeopleTab(id); navWrite(false); drawPeoplePage(); }} /></div>
      <PeopleTools L={all} F={F} s={s} ids="pl" onChange={drawPeoplePage} />
      <PeopleApplied F={F} s={s} ids="pl" count={count} onChange={drawPeoplePage} />
      <div class="tbl" id="peopleTbl" role="tabpanel">
        <table class="plt"><thead><tr>{PL_COLS.map(c => <Head key={c[0] || c[1]} col={c} so={so} />)}<th scope="col"><span class="vh">Actions on the person</span></th></tr></thead>
          <tbody id="plRows">{L.length ? L.map(x => <PlRow key={x.n} x={x} />)
            : <tr><td colSpan={10} class="sub plnone">No one matches. Try another tab or clear a filter.</td></tr>}</tbody></table>
      </div>
    </>
  );
}

let tick = 0, bound = false;
/** go()'s renderer for #people[/<tab>], and the redraw after a change. The heading and Add a person are the shell's (so the help's
    first-visit line can sit under them); this draws the rest into #peopleRoot. */
export function drawPeoplePage() {
  const el = document.getElementById("peopleRoot"); if (!el) return;
  const add = document.getElementById("plAdd");
  if (add && !bound) { bound = true; add.addEventListener("click", () => openPersonForm({ x: null, isNew: true }, plHandlers)); }
  render(<PeoplePage key="pl" t={++tick} />, el);
}
