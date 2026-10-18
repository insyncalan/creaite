// @ts-check
/* ReportsPage (BL-337, v2.1.0 P9): Reports in the left menu, #reports[&w=<week>]. One row per active project for the week: its
   health, the internal weekly report's state and each client's report with its rhythm. Needs me keeps the projects with a report
   to check or a client report due; All projects shows everything. Open goes to the project's reporting space, the same one the
   cockpit's Reporting card opens. The Friday reminder on Today points here. Read only (stores/reporting.js). */
import { render } from "preact";
import { StatusDot } from "../StatusDot.jsx";
import { StateChip, openSpace } from "./ReportingSpace.jsx";
import { $ } from "../../core/dom.js";
import { P } from "../../core/data.js";
import { navWrite } from "../../core/nav.js";
import { repAddDays, repFilter, repTick, repWeek, shownWeek, thisWeek, weekLabel, weekView } from "../../stores/reporting.js";

const nOf = (/** @type {number} */ n, /** @type {string} */ one, /** @type {string} */ many = one + "s") => `${n} ${n === 1 ? one : many}`;

function ReportsView() {
  repTick.value;
  const week = shownWeek(), cur = thisWeek(), prev = repAddDays(cur, -7);
  const all = P.map(p => ({ p, v: weekView(p.code, week) }));
  const rows = repFilter.value === "need" ? all.filter(r => r.v.needs) : all;
  const toCheck = all.filter(r => r.v.internal.key !== "filed" && r.v.internal.key !== "approved").length;
  const dueC = all.reduce((n, r) => n + r.v.clients.filter(c => c.state.key === "due" || c.state.key === "draft").length, 0);
  const setWeek = (/** @type {string} */ w) => { repWeek.value = w === cur ? "" : w; navWrite(false); };
  return (
    <div class="wrapmax rp">
      <nav class="crumb" aria-label="Breadcrumb"><span aria-current="page">Reports</span></nav>
      <div class="hhead">
        <div style={{ flex: 1 }}><h1>Reports</h1><div class="sub">Week ending {weekLabel(week)}</div></div>
        <span class="seg" role="group" aria-label="Week">
          <button type="button" data-rpweek={prev} aria-pressed={week === prev} onClick={() => setWeek(prev)}>‹ {weekLabel(prev).slice(0, 5)}</button>
          <button type="button" data-rpweek={cur} aria-pressed={week === cur} onClick={() => setWeek(cur)}>{weekLabel(cur).slice(0, 5)}</button>
        </span>
      </div>
      <div class="rp-both solid">
        <span><b id="rpSummary">{nOf(toCheck, "internal report")} to check · {nOf(dueC, "client report")} due</b><br />
          <span class="sub">Open a project to draft, check or file its reports.</span></span>
        <span class="seg" role="group" aria-label="Show">
          <button type="button" data-rpf="need" aria-pressed={repFilter.value === "need"} onClick={() => { repFilter.value = "need"; }}>Needs me</button>
          <button type="button" data-rpf="all" aria-pressed={repFilter.value === "all"} onClick={() => { repFilter.value = "all"; }}>All projects</button>
        </span>
      </div>
      <div class="tbl rp-tbl">
        <table>
          <thead><tr><th>Project</th><th>Health</th><th>Internal weekly</th><th>Client reports</th><th><span class="vh">Open</span></th></tr></thead>
          <tbody>
            {rows.length ? rows.map(({ p, v }, i) => (
              <tr key={p.code} data-rpproj={p.code}>
                <td><b>{p.name}</b></td>
                <td><StatusDot health={p.health} /></td>
                <td><StateChip s={v.internal} /></td>
                <td>{v.clients.length ? <div class="rp-cl">{v.clients.map(c => <span key={c.client}><span class="sub">{c.client}</span> <StateChip s={c.state} /></span>)}</div> : <span class="sub">No client report</span>}</td>
                <td><button type="button" class={`btn sm${i === 0 ? " primary" : ""}`} data-rpopen={p.code} aria-label={`Open ${p.name}'s reporting`} onClick={() => openSpace(p.code, week === cur ? "" : week)}>Open</button></td>
              </tr>
            )) : <tr><td colSpan={5}><div class="empty">Nothing needs you this week. Choose All projects to see every report.</div></td></tr>}
          </tbody>
        </table>
      </div>
      <div class="sub">Open takes you to that project's reporting space, the same one its page opens. Health here is each project's internal health.</div>
    </div>
  );
}

let reportsMounted = false;
/** go()'s renderer for Reports. @param {string} [week] */
export function renderReports(week) {
  const el = $("#v-reports");
  if (!el) return;
  if (week) repWeek.value = week;
  repTick.value++;
  if (!reportsMounted) { render(<ReportsView />, el); reportsMounted = true; }
}
