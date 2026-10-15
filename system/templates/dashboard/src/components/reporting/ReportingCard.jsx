// @ts-check
/* ReportingCard (BL-337, v2.1.0 P9): the project cockpit's Reporting card. This week's reports and their state: the internal weekly
   report and each client's report with its rhythm and whether it is due. Open goes to the week's reporting space (the editor stub
   until BL-335 lands, a filed report's file when there is one); Open reporting opens the space. Read only. */
import { render } from "preact";
import { Chip } from "../Chip.jsx";
import { StateChip, openSpace } from "./ReportingSpace.jsx";
import { fd } from "../../core/page.js";
import { FILES } from "../../core/data.js";
import { thisWeek, weekLabel, weekView } from "../../stores/reporting.js";

/** @param {{code: string}} props */
function ReportingCardView({ code }) {
  const week = thisWeek(), v = weekView(code, week), c = v.clients[0];
  const lastFiled = FILES.filter(f => f.p === code && f.f === "reports" && f.date).map(f => f.date).sort().pop();
  return (
    <div class="card rp-cockcard" id="repCard" aria-label="Reporting">
      <h2>Reporting <Chip tone="plan">this week</Chip></h2>
      <div class="rp-row">
        <span class="g"><b>Weekly report</b> · internal<br /><span class="sub">Week ending {weekLabel(week)}</span></span>
        <StateChip s={v.internal} />
        {v.internal.path ? <a class="btn sm" href="#" data-rpcard="internal" data-openfile={v.internal.path} aria-label="Open the weekly report">Open</a> : <button type="button" class="btn sm" data-rpcard="internal" aria-label="Open the weekly report" onClick={() => openSpace(code, "", "internal")}>Open</button>}
      </div>
      <div class="rp-row">
        <span class="g"><b>Client report</b> · {c.client}<br /><span class="sub">{c.rhythm}{c.state.key === "due" ? " · due" : c.state.key === "notdue" ? " · not due this week" : ""}</span></span>
        <StateChip s={c.state} />
        {c.state.path ? <a class="btn sm" href="#" data-rpcard="client" data-openfile={c.state.path} aria-label="Open the client report">Open</a> : <button type="button" class="btn sm" data-rpcard="client" aria-label="Open the client report" onClick={() => openSpace(code, "", "client")}>Open</button>}
      </div>
      <div class="acts">
        <button type="button" class="btn primary sm" data-rpcard="space" onClick={() => openSpace(code)}>Open reporting</button>
        <span class="sub">{lastFiled ? `Last filed: ${fd(lastFiled)}` : "Nothing filed yet"}</span>
      </div>
    </div>
  );
}

/** Draw the card into `host`. @param {Element} host @param {string} code */
export function mountReportingCard(host, code) { render(<ReportingCardView code={code} />, host); }
