// @ts-check
/* ReportingSpace (BL-337, v2.1.0 P9; #221 H1): the door to a project's reporting. The separate reporting space (weeks down the left, two
   cards, Edit both) is gone: #reporting=<CODE> is the Reporting hub (components/report/hub/ReportingHub.jsx), one page with the
   Internal, Client and Side by side views and the week Menu. This file keeps what every way in uses: `openSpace` (the Reports page, the
   cockpit's Reporting card, ⌘K and Today's reminder all come through it), `StateChip` and `renderReporting` (go()'s renderer). */
import { render } from "preact";
import { Chip } from "../Chip.jsx";
import { $ } from "../../core/dom.js";
import { go, navWrite, tabTitle } from "../../core/nav.js";
import { ReportingHub } from "../report/hub/ReportingHub.jsx";
import { hubKey, hubReady, hubView, loadHub } from "../../stores/hub.js";
import { spaceCode, spaceWeek } from "../../stores/reporting.js";

/** Open a project's reporting hub (the one door every way in uses).
    @param {string} code @param {string} [week] YYYY-MM-DD, or none for the latest @param {"internal"|"client"|"side"} [view] */
export function openSpace(code, week = "", view = "internal") {
  spaceWeek.value = week;
  hubView.value = view;
  go("reporting", code);
}

/** A report's state as a chip. @param {{s: import("../../stores/reporting.js").RepState}} props */
export function StateChip({ s }) {
  return <Chip tone={s.tone === "ok" ? "ok" : s.tone === "warn" ? "warn" : "mute"}>{s.label}</Chip>;
}

let mounted = false;
/** go()'s renderer for #reporting=<code>: draws the hub and opens the week. `fresh` (a visit) opens it again; a data reload (no `fresh`)
    leaves an open week, and any edit in it, alone. @param {string} code @param {boolean} [fresh] */
export function renderReporting(code, fresh = false) {
  const el = $("#v-reporting");
  if (!el || !code) return;
  spaceCode.value = code;
  if (!mounted) { render(<ReportingHub />, el); mounted = true; }
  if (fresh || hubReady.value !== hubKey(code, spaceWeek.value)) loadHub(code, spaceWeek.value).then(() => { navWrite(false); tabTitle(); });
}
