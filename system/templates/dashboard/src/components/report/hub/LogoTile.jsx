// @ts-check
/* LogoTile (#228 C: extracted from ClientReportPanel so the hub's cog panel and the project settings page share one set of logo
   controls). `LogoMark` is the thumbnail, or the kind's letter when there is none (the page's dashed "Add" tile is a CSS state of it);
   `LogoActions` is Add / Change, Remove (asked first) and the tick that puts the logo in the reports' header; `LogoTile` is the panel's
   row of the two. The firm's logo is one file for every project, so changing or removing it says so and asks first. Everything saves
   through stores/reportingSettings.js (uploadClientLogo trims on a copy, removeClientLogo, setClientLogos). */
import { useRef, useState } from "preact/hooks";
import {
  clientLogosOn, crLogoData, crLogoPaths, partnersOf, removeClientLogo, setClientLogos, uploadClientLogo,
} from "../../../stores/reportingSettings.js";

/** @typedef {{kind: string, mark: string, name: string, line: string, who: string, noun: string}} Tile */
/** The tiles of a project: the firm, the client, then one for each partner organisation on its Partners line (#228 B), or the one old
    "A partner" tile when it lists none. @param {string} code @returns {Tile[]} */
export function tilesOf(code) {
  const ps = partnersOf(code);
  return [
    { kind: "firm", mark: "F", name: "The firm", who: "firm's", noun: "firm", line: "Used by every project's reports, so changing or removing it changes it for all projects. Always shown." },
    { kind: "client", mark: "C", name: "The client", who: "client's", noun: "client", line: "Shown on this project's reports" },
    ...(ps.length ? ps.map(p => ({ kind: `partner:${p.slug}`, mark: "P", name: `Partner: ${p.name}`, who: `${p.name}'s`, noun: p.name, line: "Shown on this project's reports" }))
      : [{ kind: "partner", mark: "P", name: "A partner", who: "partner's", noun: "partner", line: "Only if one is involved" }]),
  ];
}

/** The logo's thumbnail or its letter. @param {{kind: string, mark: string}} props */
export function LogoMark({ kind, mark }) {
  const path = crLogoPaths.value[kind], pic = path ? crLogoData.value[path] : "";
  return <span class="mark" aria-hidden="true" data-has-logo={pic ? "1" : "0"}>{pic ? <img alt="" src={pic} /> : mark}</span>;
}

/** Add / Change, Remove and the header tick of one logo. @param {{code: string, t: Tile, ticked: boolean}} props */
export function LogoActions({ code, t, ticked }) {
  const file = useRef(/** @type {HTMLInputElement|null} */ (null));
  const path = crLogoPaths.value[t.kind], pic = path ? crLogoData.value[path] : "";
  const firm = t.kind === "firm";
  const [ask, setAsk] = useState(/** @type {""|"remove"|"change"} */ (""));      // Remove and the firm's Change ask first: the firm's logo is the same file for every project
  /** @param {Event} e */
  const picked = async e => {
    const input = /** @type {HTMLInputElement} */ (e.target), f = input.files && input.files[0];
    if (f) await uploadClientLogo(code, t.kind, f);
    input.value = "";
  };
  const toggle = () => {
    const now = clientLogosOn(code), next = now.includes(t.kind) ? now.filter(k => k !== t.kind) : [...now, t.kind];
    setClientLogos(code, next);
  };
  return (
    <span class="cfgact">
      {ask ? null : <button type="button" class="btn sm" data-logo-add={t.kind} onClick={() => { if (firm && pic) setAsk("change"); else if (file.current) file.current.click(); }}
        aria-label={`${pic ? "Change" : "Add"} the ${t.who} logo`}>{pic ? "Change" : "Add logo"}</button>}
      {pic && !ask ? <button type="button" class="btn sm" data-logo-remove={t.kind} onClick={() => setAsk("remove")}
        aria-label={`Remove the ${t.noun} logo`}>Remove</button> : null}
      {pic && ask === "remove" ? <span class="cfgask" role="group" aria-label={`Remove the ${t.noun} logo?`}>
        <span class="sub" role="alert">{firm ? "Remove the firm's logo for all projects?" : `Remove the ${t.noun} logo?`}</span>
        <button type="button" class="btn sm" data-logo-remove-yes={t.kind} onClick={() => { setAsk(""); removeClientLogo(code, t.kind); }}>Remove</button>
        <button type="button" class="btn sm" data-logo-remove-no={t.kind} onClick={() => setAsk("")}>Keep</button></span> : null}
      {pic && ask === "change" ? <span class="cfgask" role="group" aria-label="Change the firm's logo?">
        <span class="sub" role="alert">Change the firm's logo for all projects?</span>
        <button type="button" class="btn sm" data-logo-change-yes={t.kind} onClick={() => { setAsk(""); if (file.current) file.current.click(); }}>Choose a picture</button>
        <button type="button" class="btn sm" data-logo-change-no={t.kind} onClick={() => setAsk("")}>Keep</button></span> : null}
      <input type="file" hidden ref={file} accept="image/png,image/jpeg,image/svg+xml,.png,.jpg,.jpeg,.svg" data-logo-file={t.kind} onChange={picked} />
      <input type="checkbox" checked={firm || ticked} disabled={firm} data-logo-tick={t.kind}
        aria-label={firm ? "The firm's logo is always shown" : `Show the ${t.who} logo in the header`} onChange={firm ? undefined : toggle} />
    </span>
  );
}

/** One logo tile of the cog panel. @param {{code: string, t: Tile, ticked: boolean}} props */
export function LogoTile({ code, t, ticked }) {
  return (
    <div class="cfglogo" data-kind={t.kind}>
      <LogoMark kind={t.kind} mark={t.mark} />
      <span class="cfgname">{t.name}<span class="sub">{t.line}</span></span>
      <LogoActions code={code} t={t} ticked={ticked} />
    </div>
  );
}
