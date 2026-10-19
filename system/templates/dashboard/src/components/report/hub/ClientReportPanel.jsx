// @ts-check
/* ClientReportPanel (H3 of the Reporting hub, #221): the hub's "Client report settings", opened from the cog. As the locked mockup draws it:
   - the switch "This project needs a separate client report" (stored on the project; the same setting as Settings › Projects),
     with the one line that it is persistent and that turning it off deletes nothing;
   - when it is on: how often (weekly, fortnightly, monthly), the client's name on the report, a reminder on the due day, and the
     three logo tiles (the firm's always on and greyed, the client's, a partner's), each with a mark, a name, a line, Add or
     Change logo (a file chooser; Remove when there is one) and the tick that puts it in the header of both reports.
   Every control saves at once (stores/reportingSettings.js). `openClientReport(code)` shows it over the page (the hub's cog calls
   it); `<ClientReportPanel code onClose>` is the panel alone, for a place that positions it itself. */
import { render } from "preact";
import { useEffect } from "preact/hooks";
import { P } from "../../../core/data.js";
import { hubCfg } from "../../../stores/hub.js";
import { LogoTile, tilesOf } from "./LogoTile.jsx";

export { tilesOf };
import {
  CLIENT_NAME_MAX, clientLogosOn, clientReminderOn, clientReportOn, crLogoNote, crTick, readClientLogos,
  setClientName, setClientReminder, setClientRhythm, setClientReport,
} from "../../../stores/reportingSettings.js";

const RHYTHMS = ["Weekly", "Fortnightly", "Monthly"];

/** @param {{code: string, onClose?: () => void}} props */
export function ClientReportPanel({ code, onClose }) {
  crTick.value;                                     // redraw when a setting changes
  const p = /** @type {any} */ (P.find(x => x.code === code));
  useEffect(() => { readClientLogos(code); }, [code]);
  if (!p) return null;
  const on = clientReportOn(code), ticked = clientLogosOn(code), rhythms = RHYTHMS.includes(p.rhythm) ? RHYTHMS : [...RHYTHMS, p.rhythm];
  return (
    <div class="hubcfg" id="crPanel" data-slot="ClientReportPanel" role="dialog" aria-label="Client report settings" data-code={code} data-on={on ? "on" : "off"}>
      <h3>Client report for {p.name}</h3>
      <label class="cfgsw">
        <input type="checkbox" class="switch" id="cfgOn" checked={on} onChange={e => setClientReport(code, /** @type {HTMLInputElement} */ (e.target).checked)} />
        <span><b>This project needs a separate client report</b>
          <span class="sub">Turn off if the client only receives the internal report, or nothing at all.</span></span>
      </label>
      <p class="sub cfgkeep" id="cfgKeep">This applies to every future report of this project until you change it. Reports already written are kept as they are, and turning it off deletes nothing.</p>
      {on ? (
        <div class="cfgbody" id="cfgBody">
          <div class="cfgrow"><label for="cfgRh">How often</label>
            <select id="cfgRh" value={p.rhythm} onChange={e => setClientRhythm(code, /** @type {HTMLSelectElement} */ (e.target).value)}>
              {rhythms.map(r => <option key={r} value={r} selected={r === p.rhythm}>{r}</option>)}
            </select></div>
          <div class="cfgrow"><label for="cfgNm">Client name on the report</label>
            <input id="cfgNm" class="pkdt" maxLength={CLIENT_NAME_MAX} defaultValue={p.client || ""} key={p.client || ""}
              onChange={e => setClientName(code, /** @type {HTMLInputElement} */ (e.target).value)} /></div>
          <div class="cfgrow"><label for="cfgRem">Reminder</label>
            <label class="cfgck"><input type="checkbox" id="cfgRem" checked={clientReminderOn(code)}
              onChange={e => setClientReminder(code, /** @type {HTMLInputElement} */ (e.target).checked)} /> Remind me on the due day</label></div>
          <div class="cfgrow top"><label id="cfgLogosL">Logos in the report header</label>
            <div class="cfglogos" role="group" aria-labelledby="cfgLogosL">
              {tilesOf(code).map(t => <LogoTile key={t.kind} code={code} t={t} ticked={ticked.includes(t.kind)} />)}
              {crLogoNote.value ? <p class="sub cfgnote" role="status" id="cfgLogoNote">{crLogoNote.value}</p> : null}
            </div></div>
          <p class="sub">The client report takes its facts from the internal report once that is approved. This is the same setting as Settings › Projects.</p>
        </div>
      ) : <p class="sub cfgoff" id="cfgOff">This project has no client report.</p>}
      <div class="cfgfoot"><button type="button" class="btn sm primary" id="cfgDone" onClick={onClose}>Done</button></div>
    </div>
  );
}

/** Show the panel in the one fixed host at the top right and leave it showing (the hub's cog drives this from its open signal). @param {string} code */
export function showClientReport(code) {
  let host = document.getElementById("crHost");
  const fresh = !host;
  if (!host) { host = document.createElement("div"); host.id = "crHost"; document.body.appendChild(host); }
  host.dataset.code = code; bindEsc();
  const cog = document.getElementById("hubCfg");                // hangs just under the cog, at the right edge, so the cog stays clickable
  if (cog) {
    const r = cog.getBoundingClientRect();
    host.style.top = `${Math.round(r.bottom + 6)}px`; host.style.right = `${Math.max(8, Math.round(innerWidth - r.right))}px`;
    host.style.setProperty("--cr-top", host.style.top);
  }
  render(<ClientReportPanel code={code} onClose={closeClientReport} />, host);
  if (fresh) { const first = host.querySelector("input,select,button"); if (first) /** @type {HTMLElement} */ (first).focus(); }
}

/** Show the panel, or close it when it is already showing for this project. Esc, Done or opening it again closes it. @param {string} code */
export function openClientReport(code) {
  const host = document.getElementById("crHost");
  if (host && host.dataset.code === code) { closeClientReport(); return; }
  hubCfg.value = true;
  showClientReport(code);
}

export function closeClientReport() {
  hubCfg.value = false;
  const host = document.getElementById("crHost"); if (!host) return;
  render(null, host); host.remove();
}

let escBound = false;
/** Esc closes the panel (bound once, when it is first opened). */
function bindEsc() {
  if (escBound) return;
  escBound = true;
  document.addEventListener("keydown", e => { if (e.key === "Escape" && document.getElementById("crHost")) closeClientReport(); });
}
