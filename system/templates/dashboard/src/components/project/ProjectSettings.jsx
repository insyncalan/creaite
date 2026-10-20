// @ts-check
/* ProjectSettings (#228, v2 #247): the project's settings as one scrolling page, #project-settings=<CODE>[&c=<section>]. A search box
   and a sticky list of the sections on the left (it marks the one you are in, and a click scrolls to it; the tabs are gone), the
   sections on the right, in order of use: Project, People and partners (the register's own table, components/project/ProjectPeople.jsx),
   Workstreams (moved here from Settings), Milestones, Client report and logos (together: the reporting hub's cog panel in rows, the
   same stores and logo controls, components/report/hub/LogoTile.jsx) and, last and set apart, Archive and close.
   Every change saves on its own with Undo, through the flow that already saves it (stores/projectSettings.js, stores/reportingSettings.js,
   stores/peopleRegister.js, stores/workstreams.js, the milestones page, the archive card); this page holds no write of its own. */
import { render } from "preact";
import { createContext } from "preact";
import { useContext, useEffect, useLayoutEffect, useRef, useState } from "preact/hooks";
import { ProjectPeople } from "./ProjectPeople.jsx";
import { Workstreams } from "./ProjectWorkstreams.jsx";
import { wsActive } from "../../stores/workstreams.js";
import { registerRows } from "../../stores/peopleRegister.js";
import { reduced } from "../../core/page.js";
import { openSpace } from "../reporting/ReportingSpace.jsx";
import { closeClientReport, openClientReport } from "../report/hub/ClientReportPanel.jsx";
import { D, fd } from "../../core/page.js";
import { openPath } from "../../core/fields.js";
import { go, navWrite } from "../../core/nav.js";
import { viaServer } from "../../core/server.js";
import { $ } from "../../core/dom.js";
import { openChat } from "../../ask.js";
import { MVWORD, mvAll, openMilestone, openNewMilestone } from "../../milestones.js";
import { projArchive } from "../../settings.js";
import { LogoActions, LogoMark, tilesOf } from "../report/hub/LogoTile.jsx";
import {
  CLIENT_NAME_MAX, clientLogosOn, clientReminderOn, clientReportOn, crLogoData, crLogoNote, crLogoOrphans, crLogoPaths, crTick, partnersOf, readClientLogos,
  removeClientLogo, setClientName, setClientReminder, setClientRhythm, setClientReport,
} from "../../stores/reportingSettings.js";
import { pName } from "../../core/data.js";
import {
  PARTNER_NAME_MAX, PS_CATS, addPartner, loadPartners, nameProblem, partners, projectPeople, psCat, psCode, psProject, psQ, psTick,
  removePartner, renamePartner, renameProject, setProjectActive, projectState,
} from "../../stores/projectSettings.js";

/** the search text and whether the category's own name matched (so the whole category shows) */
const Find = createContext({ q: "", all: false });
let psN = 0;
/** @param {string} t */
const psNorm = t => String(t || "").toLowerCase().replace(/\s+/g, " ");

/** One row of a card: the label and its line on the left, the control on the right. Hidden when a search doesn't match it.
    @param {{label: string, help?: string, kw?: string, children?: any, id?: string}} props */
function PsRow({ label, help, kw, children, id }) {
  const f = useContext(Find), [rid] = useState(() => id || "psr" + (++psN));
  const hit = !f.q || f.all || psNorm(`${label} ${help || ""} ${kw || ""}`).includes(f.q);
  return (
    <div class="srow" data-psrow hidden={!hit}>
      <div><span id={rid}>{label}</span>{help ? <small id={rid + "h"}>{help}</small> : null}</div>
      <div class="setctl" role="group" aria-labelledby={rid}>{children}</div>
    </div>
  );
}

const PEOPLE_KW = "people person register email aliases organisation role add a person needs details followed";
/** Whether the search matches these words (or the section's name). @param {string} text */
function useMatch(text) { const f = useContext(Find); return !f.q || f.all || psNorm(text).includes(f.q); }

/** A table row that a search can hide. @param {{text: string, children?: any}} props */
function Item({ text, children }) {
  const f = useContext(Find);
  return <tr data-psrow hidden={!!f.q && !f.all && !psNorm(text).includes(f.q)}>{children}</tr>;
}

/** A button that asks first: Archive, Close. @param {{label: string, ask: string, yes: string, onYes: () => void, id: string, danger?: boolean}} props */
function AskButton({ label, ask, yes, onYes, id, danger }) {
  const [on, setOn] = useState(false);
  if (!on) return <button type="button" class="btn" id={id} onClick={() => setOn(true)}>{label}</button>;
  return (
    <span class="psask" role="group" aria-label={ask}>
      <span class="sub" role="alert">{ask}</span>
      <button type="button" class={`btn${danger ? " danger" : ""}`} id={id + "Yes"} onClick={() => { setOn(false); onYes(); }}>{yes}</button>
      <button type="button" class="btn" id={id + "No"} onClick={() => setOn(false)}>Keep it</button>
    </span>
  );
}

/** An inline problem, in plain words. @param {{msg: string, id: string}} props */
const PsProblem = ({ msg, id }) => msg ? <span class="psmsg" role="alert" id={id}>{msg}</span> : null;

// ----- General

/** @param {{code: string}} props */
function General({ code }) {
  const p = psProject(code), [err, setErr] = useState(""), folder = (D.folders || {})[code];
  const state = projectState(code);
  return (
    <div class="card" data-pscard data-cat="general"><h2>Project</h2>
      <PsRow label="Name" help="Shown everywhere in full." kw="rename project">
        <input type="text" id="psName" size={28} aria-label="Name" aria-describedby="psNameErr" key={p.name} defaultValue={p.name}
          onInput={() => err && setErr("")}
          onChange={async e => {
            const el = /** @type {HTMLInputElement} */ (e.target), bad = nameProblem(el.value);
            if (bad) { setErr(bad); return; }
            setErr(""); if (!await renameProject(code, el.value)) el.value = p.name;
          }} />
        <PsProblem msg={err} id="psNameErr" />
      </PsRow>
      <PsRow label="Client" help="Printed on the client report." kw="client name partner">
        <input type="text" id="psClient" size={28} aria-label="Client" maxLength={CLIENT_NAME_MAX} key={p.client || ""} defaultValue={p.client || ""}
          onChange={async e => { const el = /** @type {HTMLInputElement} */ (e.target); if (!await setClientName(code, el.value)) el.value = p.client || ""; }} />
      </PsRow>
      <PsRow label="Code" help="Three to seven capital letters or digits; the prefix of every item ID. Changing it renames every item, so ask creaite does it and asks first." kw="recode rename">
        <span class="pschip" id="psCode">{code}</span>
        <button type="button" class="mini" id="psRecode" onClick={() => {
          openChat(); const box = /** @type {HTMLTextAreaElement|null} */ ($("#chIn"));
          if (box) { box.value = `change the code ${code} to `; box.focus(); box.dispatchEvent(new Event("input", { bubbles: true })); }
        }}>Change code…</button>
      </PsRow>
      <PsRow label="Status" help="Active projects are swept and reported. A closed project is kept, with everything in it." kw="active closed on hold">
        <select id="psStatus" aria-label="Status" value={state === "closed" ? "closed" : "active"} disabled={state === "archived" || !viaServer()}
          onChange={async e => {
            const el = /** @type {HTMLSelectElement} */ (e.target), to = el.value;
            if (!await setProjectActive(code, to === "active")) el.value = state === "closed" ? "closed" : "active";
          }}>
          <option value="active" selected={state !== "closed"}>Active</option>
          <option value="closed" selected={state === "closed"}>Closed</option>
        </select>
      </PsRow>
      <PsRow label="Folder" help="Where its minutes, transcripts and reports live." kw="files location">
        <span class="sub" id="psFolder">{folder ? `projects/${folder}` : "No folder yet"}</span>
        <button type="button" class="mini" id="psOpenFolder" disabled={!folder} onClick={() => openPath(`projects/${folder}`)}>Open folder</button>
      </PsRow>
    </div>
  );
}

// ----- People and partners

/** @param {{code: string, name: string, i: number}} props */
function PartnerRow({ code, name, i }) {
  const [edit, setEdit] = useState(false), [err, setErr] = useState("");
  crTick.value;
  const slug = (partnersOf(code).find(x => x.name === name) || {}).slug, kind = `partner:${slug}`, logo = !!slug && !!crLogoPaths.value[kind];
  const people = projectPeople(code).filter(x => x.org && psNorm(x.org) === psNorm(name)).length;
  const save = async (/** @type {string} */ v) => { const bad = await renamePartner(code, i, v); setErr(bad); if (!bad) setEdit(false); };
  return (
    <Item text={`${name} partner ${people}`}>
      <td>{edit
        ? <span><input type="text" class="psedit" data-pspartner-edit aria-label={`Rename ${name}`} defaultValue={name} maxLength={PARTNER_NAME_MAX} ref={el => el && el.focus()}
            onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); save(/** @type {HTMLInputElement} */ (e.target).value); } else if (e.key === "Escape") { setEdit(false); setErr(""); } }} />
            <PsProblem msg={err} id={`psPartnerErr${i}`} /></span>
        : <span data-pspartner>{name}</span>}</td>
      <td>{people}</td>
      <td class="mgract">{logo ? <><button type="button" class="mini" data-pspartner-logo={kind} aria-label={`Remove the logo of ${name}`}
          title="A logo is kept under the partner's name when it is renamed or removed; remove it here first if it is not wanted"
          onClick={() => removeClientLogo(code, kind)}>Remove logo</button>{" "}</> : null}{edit
        ? <><button type="button" class="mini" data-pspartner-save onClick={e => save(/** @type {HTMLInputElement} */ (/** @type {HTMLElement} */ (e.target).closest("tr")?.querySelector("input")).value)}>Save</button>{" "}
            <button type="button" class="mini" onClick={() => { setEdit(false); setErr(""); }}>Cancel</button></>
        : <><button type="button" class="mini" data-pspartner-rename aria-label={`Rename ${name}`} onClick={() => setEdit(true)}>Rename</button>{" "}
            <button type="button" class="mini" data-pspartner-remove aria-label={`Remove ${name}`} onClick={() => removePartner(code, i)}>Remove</button></>}</td>
    </Item>
  );
}

/** @param {{code: string}} props */
function PeoplePartners({ code }) {
  crTick.value; psTick.value;
  const list = partners.value.list, [err, setErr] = useState(""), box = useRef(/** @type {HTMLInputElement|null} */ (null));
  const add = async () => {
    const el = box.current; if (!el) return;
    const bad = await addPartner(code, el.value); setErr(bad); if (!bad) { el.value = ""; el.focus(); }
  };
  return (
    <>
      <ProjectPeople code={code} match={useMatch(PEOPLE_KW + " " + registerRows().filter(x => x.on.includes(code) || !x.on.length).map(x => `${x.n} ${x.email} ${x.org} ${x.role} ${x.aliases.join(" ")}`).join(" "))} />
      <div class="card" data-pscard data-cat="people"><h2>Partner organisations</h2>
        <div class="tbl"><table class="pstbl" id="psPartners" aria-label="Partner organisations"><thead><tr><th scope="col">Organisation</th><th scope="col">People</th><th scope="col"><span class="vh">Actions</span></th></tr></thead>
          <tbody>{list.length ? list.map((n, i) => <PartnerRow key={n} code={code} name={n} i={i} />) : <tr><td class="sub" colSpan={3}>No partner organisations.</td></tr>}</tbody></table></div>
        <div class="psfoot psadd"><label for="psPartnerIn" class="vh">Partner organisation</label>
          <input type="text" id="psPartnerIn" placeholder="Partner organisation" maxLength={PARTNER_NAME_MAX} ref={box} aria-describedby="psPartnerErr"
            onInput={() => err && setErr("")} onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); add(); } }} />
          <button type="button" class="btn sm" id="psAddPartner" onClick={add}>Add a partner</button>
          <PsProblem msg={err} id="psPartnerErr" /></div>
        <p class="psnote psfoot">Saved as one line, “Partners:”, in the project's memory file. Names use letters, digits, spaces and . , &amp; ' - ( ) only, up to 60 characters; one organisation to a name, capitals don't matter.</p>
      </div>
    </>
  );
}

// ----- Logos and Reporting (#228 C): the same settings and the same controls as the reporting hub's cog panel, in rows

/** Open the reporting hub and its cog panel for the project: the panel is the hub's, so the hub opens first. @param {string} code */
export function openReportSettings(code) {
  openSpace(code);
  let n = 0;
  const t = setInterval(() => { n++; if (document.getElementById("hubCfg")) { clearInterval(t); openClientReport(code); } else if (n > 40) clearInterval(t); }, 100);
}

/** @param {{code: string}} props */
function Logos({ code }) {
  crTick.value; psTick.value; partners.value;       // the rows follow the Partners line: this component reads the signals itself (a parent's re-render does not reach it)
  const ticked = clientLogosOn(code), orphans = crLogoOrphans.value, tiles = tilesOf(code);
  return (
    <>
      <div class="card" data-pscard data-cat="rep"><h2>Logos in the reports' header</h2>
        {tiles.map(t => {
          const has = !!crLogoPaths.value[t.kind];
          return (
            <PsRow key={t.kind} id={`psLogo-${t.kind.replace(":", "-")}`} label={t.name} help={t.line} kw="logo picture header firm client partner">
              <span class="pslogo" data-kind={t.kind} data-state={has ? "set" : "empty"}>
                <LogoMark kind={t.kind} mark={t.mark} />
                {has ? null : <span class="sub">Not added yet</span>}
                <LogoActions code={code} t={t} ticked={ticked.includes(t.kind)} />
              </span>
            </PsRow>
          );
        })}
        {crLogoNote.value ? <p class="psnote psfoot" role="status" id="psLogoNote">{crLogoNote.value}</p> : null}
        <p class="psnote psfoot">Partners come from People and partners: add or remove a partner organisation there and its logo row appears or goes here. These are the same logos as in the reporting hub's client report settings. A transparent PNG or SVG sits better than a JPEG; the picture you choose is kept as it is and a trimmed copy is drawn. The tick puts the logo in the header of this project's reports.</p>
      </div>
      {orphans.length ? (
        <div class="card" data-pscard data-cat="rep"><h2>Logos not used</h2>
          {orphans.map(o => (
            <PsRow key={o.kind} id={`psOrphan-${o.slug}`} label={o.slug} help="A logo kept after its partner was renamed or removed from the list. It is not drawn in any report." kw="logos not used unused orphan partner">
              <span class="pslogo" data-orphan={o.kind}>
                <span class="mark" aria-hidden="true">{crLogoData.value[o.path] ? <img alt="" src={crLogoData.value[o.path]} /> : "P"}</span>
                <button type="button" class="btn sm" data-logo-orphan-remove={o.kind} aria-label={`Remove the unused logo ${o.slug}`}
                  onClick={() => removeClientLogo(code, o.kind)}>Remove</button>
              </span>
            </PsRow>))}
        </div>
      ) : null}
    </>
  );
}

const REP_RHYTHMS = ["Weekly", "Fortnightly", "Monthly"];
/** @param {{code: string}} props */
function Reporting({ code }) {
  crTick.value;
  const p = psProject(code), on = clientReportOn(code), rhythms = REP_RHYTHMS.includes(p.rhythm) ? REP_RHYTHMS : [...REP_RHYTHMS, p.rhythm];
  return (
    <div class="card" data-pscard data-cat="rep"><h2>Client report</h2>
      <PsRow label="Client report" help="Turn off if the client only receives the internal report, or nothing at all. This holds for every future report of this project until you change it; reports already written are kept and turning it off deletes nothing." kw="client report needs a separate on off">
        <label class="settick"><input type="checkbox" id="psRepOn" checked={on} aria-label="This project needs a separate client report"
          onChange={e => setClientReport(code, /** @type {HTMLInputElement} */ (e.target).checked)} /> Needs a separate client report</label>
      </PsRow>
      {on ? (
        <>
          <PsRow label="How often" help="How often the client report is due." kw="weekly fortnightly monthly rhythm">
            <select id="psRepRh" aria-label="How often" value={p.rhythm} onChange={e => setClientRhythm(code, /** @type {HTMLSelectElement} */ (e.target).value)}>
              {rhythms.map(r => <option key={r} value={r} selected={r === p.rhythm}>{r}</option>)}
            </select>
          </PsRow>
          <PsRow label="Client name on the report" help="Printed on the client report." kw="client name">
            <input type="text" id="psRepNm" size={28} aria-label="Client name on the report" maxLength={CLIENT_NAME_MAX} key={p.client || ""} defaultValue={p.client || ""}
              onChange={async e => { const el = /** @type {HTMLInputElement} */ (e.target); if (!await setClientName(code, el.value)) el.value = p.client || ""; }} />
          </PsRow>
          <PsRow label="Reminder" help="A reminder on the day the client report is due." kw="remind due day">
            <label class="settick"><input type="checkbox" id="psRepRem" checked={clientReminderOn(code)} aria-label="Remind me on the due day"
              onChange={e => setClientReminder(code, /** @type {HTMLInputElement} */ (e.target).checked)} /> Remind me on the due day</label>
          </PsRow>
        </>
      ) : <PsRow label="This project has no client report" help="Turn it on above to set how often, the client's name and the reminder."><span class="sub" id="psRepOff">Off</span></PsRow>}
      <PsRow label="Open reporting" help="The reporting hub for this project." kw="hub weekly">
        <button type="button" class="btn" id="psRepHub" onClick={() => openSpace(code)}>Open reporting</button>
      </PsRow>
      <p class="psnote psfoot">The same setting as the cog in the reporting hub: change it in either place and the other follows.</p>
    </div>
  );
}

// ----- Milestones and Archive

/** @param {{code: string}} props */
function Milestones({ code }) {
  const list = mvAll(code).slice().sort((a, b) => a.id.localeCompare(b.id));
  return (
    <div class="card" data-pscard data-cat="miles"><h2>Milestones</h2>
      <div class="tbl"><table class="pstbl" id="psMiles" aria-label="Milestones"><thead><tr><th scope="col">ID</th><th scope="col">Milestone</th><th scope="col">Agreed</th><th scope="col">Expected</th><th scope="col">State</th><th scope="col"><span class="vh">Actions</span></th></tr></thead>
        <tbody>{list.length ? list.map(m => (
          <Item key={m.id} text={`${m.id} ${m.n} ${(MVWORD[m.state] || m.state)}`}>
            <td>{m.id}</td><td>{m.n}</td><td>{m.agr ? fd(m.agr) : <span class="sub">No date</span>}</td><td>{m.fc ? fd(m.fc) : <span class="sub">No date</span>}</td>
            <td>{MVWORD[m.state] || m.state}</td>
            <td class="mgract"><button type="button" class="mini" data-psms-edit={m.id} aria-label={`Edit ${m.n}`} onClick={() => openMilestone(m.id)}>Edit</button></td>
          </Item>)) : <tr><td class="sub" colSpan={6}>No milestones yet.</td></tr>}</tbody></table></div>
      <p class="psfoot"><button type="button" class="btn sm" id="psAddMs" onClick={() => openNewMilestone(code)}>Add a milestone</button>{" "}
        <a href="#" class="srclink" id="psMsPage" onClick={e => { e.preventDefault(); go("milestones", code); }}>Open the milestones page</a></p>
    </div>
  );
}

/** @param {{code: string}} props */
function Archive({ code }) {
  const state = projectState(code), name = pName(code);
  return (
    <div class="psdanger"><div class="card" data-pscard data-cat="arch"><h2>Archive and close</h2>
      {state === "archived"
        ? <PsRow label="Restore this project" help="Brings its folder back from the archive. It goes on the approval card in ask creaite first." kw="archive restore">
            <button type="button" class="btn" id="psRestore" onClick={() => projArchive(code, "restore", false)}>Restore</button></PsRow>
        : <PsRow label="Archive this project" help="Moves its folder to the archive and keeps everything; it can be restored from the Projects page (Show archived). It goes on the approval card in ask creaite first." kw="archive restore">
            <AskButton id="psArchive" label="Archive…" ask={`Archive ${name}?`} yes="Archive" onYes={() => projArchive(code, "archive", false)} />
          </PsRow>}
      {state === "closed"
        ? <PsRow label="Reopen this project" help="Makes it active again: it is swept and reported again." kw="active">
            <button type="button" class="btn" id="psReopen" onClick={() => setProjectActive(code, true)}>Reopen</button></PsRow>
        : <PsRow label="Close this project" help="Marks it closed in the tracker; nothing is deleted." kw="close closed">
            <AskButton id="psClose" label="Close…" ask={`Close ${name}?`} yes="Close it" danger onYes={() => setProjectActive(code, false)} />
          </PsRow>}
    </div></div>
  );
}

// ----- the page

/** Logos and the client report: one section. @param {{code: string}} props */
const ClientAndLogos = ({ code }) => <><Reporting code={code} /><Logos code={code} /></>;
/** @param {{code: string}} props */
const Ws = ({ code }) => { psTick.value; return <Workstreams code={code} match={useMatch(`workstreams workstream lead keywords ${wsActive(code).map(w => `${w.name} ${w.keywords || ""}`).join(" ")}`)} />; };
const BODY = { general: General, people: PeoplePartners, ws: Ws, miles: Milestones, rep: ClientAndLogos, arch: Archive };

/** the section the list marks while the page scrolls (one a click chose holds while its scroll runs) */
let spyHold = 0;
/** @param {HTMLElement} view */
function spy(view) {
  if (performance.now() < spyHold || psQ.peek().trim()) return;
  const secs = [...view.querySelectorAll("[data-pssec]")], top = view.getBoundingClientRect().top + view.clientHeight / 3;
  let cur = secs.length ? /** @type {HTMLElement} */ (secs[0]).dataset.pssec || "general" : "general";
  secs.forEach(s => { if (s.getBoundingClientRect().top < top) cur = /** @type {HTMLElement} */ (s).dataset.pssec || cur; });
  const last = secs[secs.length - 1];
  if (last && view.scrollTop + view.clientHeight >= view.scrollHeight - 4) cur = /** @type {HTMLElement} */ (last).dataset.pssec || cur;
  if (cur !== psCat.peek()) { psCat.value = cur; navWrite(false); }
}
/** Scroll the page to a section. @param {string} id @param {boolean} [smooth] */
export function psJump(id, smooth) {
  const el = document.getElementById(`s-${id}`), view = $("#v-psettings");
  if (!el || !view) return;
  spyHold = performance.now() + 900;
  const behavior = smooth && !reduced() ? "smooth" : "auto";
  if (id === "general") view.scrollTo({ top: 0, behavior });
  else el.scrollIntoView({ block: "start", behavior });         // the section's scroll-margin keeps a little space above it
}

export function ProjectSettings() {
  psTick.value; partners.value;
  const code = psCode.value, p = psProject(code), root = useRef(/** @type {HTMLDivElement|null} */ (null));
  const q = psNorm(psQ.value).trim(), cat = psCat.value;
  useLayoutEffect(() => {              // a card with no row left in a search is hidden (the rows hide themselves; a row re-draws a moment after its parent)
    const apply = () => {
      const el = root.current; if (!el) return;
      el.querySelectorAll("[data-pscard]").forEach(c => { /** @type {HTMLElement} */ (c).hidden = !!q && !c.querySelector("[data-psrow]:not([hidden])"); });
      el.querySelectorAll("[data-pssec]").forEach(s => { /** @type {HTMLElement} */ (s).hidden = !!q && !s.querySelector("[data-pscard]:not([hidden])"); });
      const any = [...el.querySelectorAll("[data-pscard]")].some(c => !(/** @type {HTMLElement} */ (c)).hidden);
      const none = el.querySelector("#psNone"); if (none) /** @type {HTMLElement} */ (none).hidden = !q || any;
    };
    apply(); const t = setTimeout(apply, 0); return () => clearTimeout(t);
  });
  useEffect(() => {
    const view = $("#v-psettings"); if (!view) return;
    const on = () => spy(/** @type {HTMLElement} */ (view));
    view.addEventListener("scroll", on, { passive: true }); return () => view.removeEventListener("scroll", on);
  }, []);
  if (!p) return (
    <div class="wrapmax"><nav class="crumb" aria-label="Breadcrumb"><a href="#" onClick={e => { e.preventDefault(); go("projects"); }}>Projects</a><span aria-hidden="true">›</span><span aria-current="page">Settings</span></nav>
      <h1 id="psTitle">Project settings</h1><p class="sub" id="psMissing">That project isn't open here. It may be closed or archived.</p></div>);
  return (
    <div class="wrapmax" ref={root}>
      <nav class="crumb" aria-label="Breadcrumb"><a href="#" id="psBackP" onClick={e => { e.preventDefault(); go("projects"); }}>Projects</a><span aria-hidden="true">›</span>
        <a href="#" id="psBack" onClick={e => { e.preventDefault(); go("cockpit", code); }}>{p.name}</a><span aria-hidden="true">›</span><span aria-current="page">Settings</span></nav>
      <h1 id="psTitle">Project settings</h1>
      <p class="sub" style={{ margin: "4px 0 14px" }} id="psSub">{p.name} · {code}. Each change saves on its own, with Undo.</p>
      <div class="setlayout">
        <div class="setside">
          <input type="search" id="psq" class="setq" placeholder="Search these settings" aria-label="Search these settings" autocomplete="off" value={psQ.value}
            onInput={e => { psQ.value = /** @type {HTMLInputElement} */ (e.target).value; }} />
          <nav class="setcats psnav" id="pscats" aria-label="On this page">
            {PS_CATS.map(([id, label]) => (
              <a key={id} href={`#project-settings=${encodeURIComponent(code)}${id === "general" ? "" : `&c=${id}`}`} data-pscat={id} aria-current={!q && cat === id ? "true" : undefined}
                onClick={e => { e.preventDefault(); psQ.value = ""; psCat.value = id; navWrite(false); requestAnimationFrame(() => psJump(id, true)); }}>{label}</a>))}
          </nav>
        </div>
        <div id="psBody">
          <div class="setstack">
            {PS_CATS.map(([id, label]) => {
              const Body = BODY[/** @type {keyof typeof BODY} */ (id)];
              return (
                <section key={id} class="pssec" id={`s-${id}`} data-pssec={id} aria-label={label}>
                  <Find.Provider value={{ q, all: !!q && psNorm(label).includes(q) }}><Body code={code} /></Find.Provider>
                </section>);
            })}
          </div>
          <p class="sub setnone" id="psNone" role="status" hidden>No settings match “{psQ.value.trim()}”.</p>
        </div>
      </div>
    </div>
  );
}

let psMounted = false;
/** go()'s renderer for #project-settings=<code>[&c=<section>]: the page, then the section the address names. @param {string} code */
export function renderProjectSettings(code) {
  const el = $("#v-psettings"); if (!el) return;
  closeClientReport();                 // the hub's cog panel does not stay over this page
  const fresh = psCode.peek() !== code || !psMounted;
  psCode.value = code;
  const read = partners.peek();
  if (read.code !== code || !read.loaded) loadPartners(code);
  readClientLogos(code);               // which logo files exist, to offer removing one a renamed partner left behind
  if (!psMounted) { render(<ProjectSettings />, el); psMounted = true; }
  else psTick.value++;
  if (fresh || psCat.peek() !== "general") setTimeout(() => psJump(psCat.peek()), 60);     // after go()'s own scroll restore; the section chosen by then
}
