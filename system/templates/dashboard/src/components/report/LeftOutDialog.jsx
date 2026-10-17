// @ts-check
/* LeftOutDialog (v2.1.0 P8, BL-336): the check of what is left out of the client's report, shown before every export. It lists, in
   plain words, the items the report does not show and why, the sections hidden, the internal notes and sources, any logo unticked
   and the health difference, and names the internal week the facts come from. HTML, Word and PDF are offered only when the
   internal week is approved and nothing would leak; the export route runs the same check again whoever asks. */
import { Dialog } from "../Dialog.jsx";
import { GROUP_LABEL, leftLine } from "./clientDoc.js";
import { fd } from "../../core/page.js";
import { crCheck, crDialog } from "../../stores/clientReport.js";

const ONE = /** @type {Record<string, string>} */ ({ risks: "risk or issue", overdue: "overdue action", decisions: "decision", milestones: "milestone" });

/** @param {{client: string, onExport: (fmt: "html"|"docx"|"pdf") => void}} props */
export function LeftOutDialog({ client, onExport }) {
  const open = crDialog.value, c = crCheck.value, lo = c && c.left_out;
  const close = () => { crDialog.value = false; };
  const lines = [];
  if (lo) {
    for (const g of Object.keys(GROUP_LABEL)) {
      const its = lo.items.filter(x => x.group === g && x.kind !== "other");
      if (its.length) lines.push(<li key={g} data-leftgroup={g}><b>{its.length} {its.length === 1 ? ONE[g] : GROUP_LABEL[g]}:</b> {leftLine(its)}.</li>);
    }
    if (lo.sections.length) lines.push(<li key="sec"><b>Hidden sections:</b> {lo.sections.map(s => s.heading).join(", ")}.</li>);
    lines.push(<li key="notes"><b>Internal notes and sources:</b> creaite checks, source chips{lo.tags ? ` (${lo.tags} here)` : ""}, item IDs and the page's editing data.</li>);
    if (lo.logos.length) lines.push(<li key="logo"><b>{lo.logos.length > 1 ? "Logos" : "A logo"}:</b> {lo.logos.join(" and ")}, unticked for this client.</li>);
    if (lo.health) lines.push(<li key="health"><b>Health:</b> shown as {lo.health.client} (internal: {lo.health.internal}), {String(lo.health.reason || "").trim() ? "with your reason kept internally" : "no reason written yet"}.</li>);
  }
  const blocked = !lo || !lo.ready || lo.findings.length > 0;
  return (
    <Dialog open={open} onClose={close} labelledBy="crLeftH" id="crLeftDlg" class="crdlg" focus="[data-crdcancel]">
      <h2 id="crLeftH">Left out of {client || "the client"}'s report</h2>
      {!c ? <p class="sub">Checking…</p> : !c.ok || !lo ? <p class="mnerr" role="alert">{c.message || "The check didn't run."}</p> : (
        <>
          <ul class="crleft" data-crleft-list>{lines}</ul>
          {lo.findings.length ? <div class="crbad" role="alert" data-crfindings><b>Possible internal content. Fix it before exporting:</b><ul>{lo.findings.map((f, i) => <li key={i}>{f}</li>)}</ul></div> : null}
          {!lo.ready ? <p class="crbad" role="alert">{lo.not_ready}</p> : null}
          <p class="sub">{lo.facts_week ? `Facts come from the internal report approved for week ending ${fd(lo.facts_week)}.` : "The internal report isn't approved yet."}</p>
        </>
      )}
      <div class="crdacts">
        <button type="button" class="btn" data-crdcancel onClick={close}>Cancel</button>
        <button type="button" class="btn" data-crexport="html" disabled={blocked} onClick={() => onExport("html")}>HTML</button>
        <button type="button" class="btn" data-crexport="docx" disabled={blocked} onClick={() => onExport("docx")}>Word</button>
        <button type="button" class="btn primary" data-crexport="pdf" disabled={blocked} onClick={() => onExport("pdf")}>PDF</button>
      </div>
    </Dialog>
  );
}
