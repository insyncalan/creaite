// @ts-check
/* ProjectPeople (#247): People on this project, on the project settings page: the register's own table (the original People
   register view): Name, Email, Organisation · role, Aliases, Actions, RAID (this project's counts), edit and the bin (Remove from
   this project only: deleting from the register is on the People page). Search and the two-pane filter; a name opens their work;
   a right-click is the person menu (Draft email with their work items). No merge or rename. People on no project are in a quiet
   group under the table, "Not on any project yet", each with Add to this project. A followed person has a star, on this page
   only (BL-288), and the edit form has the Follow tick. */
import { useRef } from "preact/hooks";
import { psChanged, psTick } from "../../stores/projectSettings.js";
import {
  addPerson, addToProject, countsIn, missingFlag, newFilter, personPasses, registerRows, removeFromProject, savePerson,
} from "../../stores/peopleRegister.js";
import { Count, Dash, NameCell, PeopleApplied, PeopleTools, openPersonForm, peopleWord, peoplePlural, useFields, useRedraw } from "../people/PeopleParts.jsx";
import { IconButton } from "../IconButton.jsx";

/** @typedef {import("../../stores/peopleRegister.js").PersonRow} PersonRow */

const ME_NOTE = "Change in Settings › Essentials › You";
const IDS = "psPm";

/** @param {string} code */
const psPersonHandlers = code => ({
  onSave: async (/** @type {string} */ name, /** @type {any} */ v, /** @type {boolean} */ isNew) => { const ok = await (isNew ? addPerson(name, v) : savePerson(name, v)); psChanged(); return ok; },
  onRemove: async (/** @type {string} */ name) => { await removeFromProject(name, code); psChanged(); },
});

/** @param {{x: PersonRow, code: string}} props */
function PsPersonRow({ x, code }) {
  const c = countsIn(x, code);
  const edit = () => openPersonForm({ x, code, follow: true }, psPersonHandlers(code));
  return (
    <tr data-pn={x.n}>
      <NameCell x={x} code={code} follow codes />
      <td>{x.email ? x.email : <Dash />}</td>
      <td>{x.org || x.role ? `${x.org}${x.org && x.role ? " · " : ""}${x.role}` : <Dash />}</td>
      <td class="sub">{x.aliases.length ? x.aliases.join(", ") : "—"}</td>
      <td class="num"><Count n={c.a} label={`${peoplePlural(c.a, "action")} owned by ${x.n} in this project, any status`} nav={`actions:open:${code}`} extra={{ st: [], o: [x.n] }} /></td>
      <td class="num"><Count n={c.r} label={`${peoplePlural(c.r, "RAID item")} owned by ${x.n} in this project, any status`} nav={`raid:open:${code}`} extra={{ st: [], o: [x.n] }} /></td>
      <td class="mgract">{x.me ? <span class="x">{ME_NOTE}</span> : <>
        {x.missing.length ? <button type="button" class="miniflag" data-pm-details={x.n} aria-haspopup="dialog" aria-label={`${missingFlag(x)} for ${x.n}: edit details`} onClick={edit}>{missingFlag(x)}</button> : null}
        <IconButton icon="pencil" label="Edit details" name={`Edit ${x.n}`} haspopup="dialog" data={{ "pm-edit": x.n }} onClick={edit} />
        <IconButton icon="trash" label="Remove from this project" name={`Remove ${x.n} from this project`} cls="no" data={{ "pm-remove": x.n }}
          onClick={async () => { await removeFromProject(x.n, code); psChanged(); }} />
      </>}</td>
    </tr>
  );
}

/** @param {{x: PersonRow, code: string}} props */
const Unassigned = ({ x, code }) => (
  <tr data-pn={x.n} class="off">
    <NameCell x={x} />
    <td>{x.email ? x.email : <Dash />}</td>
    <td>{x.org || x.role ? `${x.org}${x.org && x.role ? " · " : ""}${x.role}` : <Dash />}</td>
    <td class="mgract"><button type="button" class="mini" data-pm-addto={x.n} aria-label={`Add ${x.n} to this project`}
      onClick={async () => { await addToProject(x.n, code); psChanged(); }}>Add to this project</button></td>
  </tr>
);

/** `match`: whether the page's search matches this card (a card with nothing left to show is hidden by the page).
    @param {{code: string, match?: boolean}} props */
export function ProjectPeople({ code, match = true }) {
  psTick.value;          // a parent's re-render does not reach a component with the same props (@preact/signals): it reads the tick itself
  const st = useRef(/** @type {{code: string, s: any}} */ ({ code: "", s: newFilter() })), redraw = useRedraw();
  if (st.current.code !== code) st.current = { code, s: newFilter() };
  const s = st.current.s, all = registerRows(), here = all.filter(x => x.on.includes(code)), none = all.filter(x => !x.on.length && !x.me);
  const F = useFields(here, s, { code, follow: true }), shown = here.filter(x => personPasses(x, F, s));
  const noneShown = none.filter(x => personPasses(x, F.filter(f => f[0] !== "proj"), s));
  const count = `Showing ${shown.length} of ${peopleWord(here.length)} on this project${none.length ? ` · ${none.length} on no project` : ""}`;
  return (
    <div class="card" data-pscard data-cat="people" id="psPeopleCard">
      <div class="pshl"><h2>People on this project</h2>
        <button type="button" class="btn" id="psAddPerson" aria-haspopup="dialog" onClick={() => openPersonForm({ x: null, isNew: true, code, follow: true }, psPersonHandlers(code))}>Add a person</button></div>
      <div data-psrow hidden={!match}>
      <p class="sub psintro">Everyone who owns an item here or is named on this project. Counts are for this project. Click a name for their work; right-click to draft an email with their work items. A small code beside a name means they are also on that project. Everything except the counts belongs to the person and is the same on every project: email, aliases, organisation and role.</p>
      <PeopleTools L={here} F={F} s={s} ids={IDS} onChange={redraw} />
      <PeopleApplied F={F} s={s} ids={IDS} count={count} onChange={redraw} />
      <div class="tbl"><table class="mgr" id="psPeople" aria-label="People on this project"><thead><tr><th scope="col">Name</th><th scope="col">Email</th><th scope="col">Organisation · role</th><th scope="col">Aliases</th>
        <th scope="col" class="num">Actions</th><th scope="col" class="num">RAID</th><th scope="col"><span class="vh">Actions on the person</span></th></tr></thead>
        <tbody id="psPeopleRows">{shown.length ? shown.map(x => <PsPersonRow key={x.n} x={x} code={code} />)
          : <tr><td class="sub" colSpan={7}>{here.length ? "Nobody matches." : "Nobody owns an item of this project yet."}</td></tr>}</tbody></table></div>
      {noneShown.length ? <div id="psUnas">
        <h3 class="psunh">Not on any project yet <span class="sub">{noneShown.length}</span></h3>
        <p class="sub psunp">These people are in the register but on no project. They show here, and on every project, until you add them to one.</p>
        <div class="tbl"><table class="mgr" aria-label="Not on any project yet"><tbody>{noneShown.map(x => <Unassigned key={x.n} x={x} code={code} />)}</tbody></table></div>
      </div> : null}
      </div>
    </div>
  );
}
