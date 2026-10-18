// @ts-check
/* HubBar (#221 H1; brief section 5 and Rounds 2 to 10): the hub's ONE toolbar, drawn into the sheet's bar (Sheet `renderBar`), on one
   line, every control 32 px high (--ctl-h), icons always (the words are tooltips and accessible names). In this order: the view switch
   (only when the project has a client report), the week Menu, the short title the slim bar shows, zoom (− Fit +, joined; the percentage
   returns to Fit), Show as exported, Export, Approve, and the cog last.
   Export (a Menu: an icon, a name and one line each) asks Internal, Client or Both after the format, only when the client report is on;
   with it off it exports the internal report without a question. Approve (a Menu): the internal report; the client report once the
   internal one is approved. "Check this report" (#170) is NOT here yet: it goes between Show as exported and Export. */
import { useEffect, useRef } from "preact/hooks";
import { Icon } from "../../Icon.jsx";
import { Menu, openMenu } from "../../Menu.jsx";
import { fd } from "../../../core/page.js";
import { SHEET_ZOOM_DEFAULT, SHEET_ZOOM_MAX, SHEET_ZOOM_MIN, stepZoom } from "../sheetLib.js";
import { hubApproveClient, hubApproveInternal, hubExport } from "./hubActions.js";
import { WeekMenu } from "./WeekMenu.jsx";
import { ClientReportPanel } from "./ClientReportPanel.jsx";
import { EXPORT_FORMATS, EXPORT_WHICH } from "./hubLib.js";
import { crDoc, crInfo } from "../../../stores/clientReport.js";
import { hubCfg } from "../../../stores/hub.js";
import { weeklyEditing } from "../../../stores/weekly.js";

/** @typedef {import("../Sheet.jsx").SheetDoc} SheetDoc */

const VIEWS = /** @type {const} */ ([["internal", "Internal"], ["client", "Client"], ["side", "Side by side"]]);

/** @param {{ctx: any, code: string, view: "internal"|"client"|"side", on: boolean, doc: SheetDoc, week: string, tone: string,
    rows: import("./hubLib.js").WeekRow[], onWeek: (w: string) => void, onView: (v: "internal"|"client"|"side") => void}} props */
export function HubBar({ ctx, code, view, on, doc, week, tone, rows, onWeek, onView }) {
  const { zoom, setZoom, exported, setExported, status, bad } = ctx;
  const info = crInfo.value, cd = crDoc.value;
  const iApproved = doc.state === "approved" && !weeklyEditing.value, cApproved = !!cd && cd.state === "approved", ready = !!(info && info.ready);
  const cfgBtn = useRef(/** @type {HTMLButtonElement|null} */ (null)), cfgBox = useRef(/** @type {HTMLSpanElement|null} */ (null));
  const open = hubCfg.value;
  useEffect(() => {                                       // a click away closes the cog's panel
    if (!open) return undefined;
    const away = (/** @type {Event} */ e) => { if (cfgBox.current && !cfgBox.current.contains(/** @type {Node} */ (e.target))) hubCfg.value = false; };
    document.addEventListener("pointerdown", away, true);
    return () => document.removeEventListener("pointerdown", away, true);
  }, [open]);

  /** After the format: Internal, Client or Both, only when the project has a client report. @param {string} fmt */
  const pickFormat = (fmt) => {
    const f = /** @type {"html"|"docx"|"pdf"} */ (fmt);
    if (!on) { hubExport(f, "internal"); return; }
    const anchor = document.getElementById("hubExport");
    openMenu(anchor, { label: "Which report", align: "right", items: EXPORT_WHICH.map(w => ({ id: w.id, name: w.name, line: w.line, icon: "filetext", data: { hubpick: w.id } })),
      onPick: id => { hubExport(f, /** @type {"internal"|"client"|"both"} */ (id)); } });
  };
  const approveItems = [
    { id: "internal", name: "Approve the internal report", icon: "check", disabled: iApproved,
      line: iApproved ? "Already approved and filed" : "Files it in Reports; the client facts lock" },
    ...(on ? [{ id: "client", name: "Approve the client report", icon: "check", disabled: !ready || cApproved,
      line: cApproved ? "Already approved and filed" : ready ? "Files it in Reports" : "Available once the internal report is approved" }] : []),
  ];
  const label = `Client report settings: ${on ? "on" : "off"}`;
  return (
    <>
      {on ? (
        <span class="seg" id="hubSeg" role="group" aria-label="Which report">
          {VIEWS.map(([id, name]) => <button type="button" key={id} data-hv={id} aria-pressed={view === id ? "true" : "false"} onClick={() => onView(id)}>{name}</button>)}
        </span>) : null}
      <WeekMenu week={week} tone={tone} rows={rows} clientOn={on} onPick={onWeek} />
      <span class="sheet-mini"><b>Weekly reporting</b><span class="sub">{doc.project_name || code} · {fd(week)}</span></span>
      <span class="sp" />
      <span class="hubzoom" role="group" aria-label="Zoom">
        <button type="button" id="zOut" aria-label="Zoom out" data-tip="Zoom out" disabled={zoom <= SHEET_ZOOM_MIN} onClick={() => setZoom(stepZoom(zoom, -1))}>−</button>
        <button type="button" id="zVal" class="zv sheet-zv" aria-live="polite" data-zoom={zoom} data-tip="Back to fit" aria-label={`Zoom ${Math.round(zoom * 100)}%. Back to fit`}
          onClick={() => setZoom(SHEET_ZOOM_DEFAULT)}>{zoom === SHEET_ZOOM_DEFAULT ? "Fit" : `${Math.round(zoom * 100)}%`}</button>
        <button type="button" id="zIn" aria-label="Zoom in" data-tip="Zoom in" disabled={zoom >= SHEET_ZOOM_MAX} onClick={() => setZoom(stepZoom(zoom, 1))}>+</button>
      </span>
      <button type="button" class="btn ib sheet-exp" id="hubExp" aria-pressed={exported ? "true" : "false"} aria-label="Show as exported" data-tip="Show as exported"
        onClick={() => setExported(!exported)}><Icon name="eye" /></button>
      {/* #170: the "Check this report" icon button goes here (between Show as exported and Export). Not built in this release. */}
      <span class="sub sheet-status" role="status" data-bad={bad ? "1" : undefined}>{status}</span>
      <Menu label="" icon="upload" id="hubExport" btnCls="btn" ariaLabel="Export" tip="Export" menuLabel="Export the report"
        items={EXPORT_FORMATS.map(f => ({ id: f.id, name: f.name, line: f.line, icon: f.icon }))} onPick={pickFormat} />
      <Menu label="" icon="check" id="hubApprove" btnCls="btn primary" ariaLabel="Approve" tip="Approve" menuLabel="Approve"
        items={approveItems} onPick={id => { if (id === "internal") hubApproveInternal(); else hubApproveClient(false); }} />
      <span class="hubcfgwrap" ref={cfgBox}>
        <button type="button" class="btn ib" id="hubCfg" ref={cfgBtn} aria-haspopup="dialog" aria-expanded={open ? "true" : "false"} aria-label={label} data-tip={label}
          onClick={() => { hubCfg.value = !hubCfg.value; }}><Icon name="gear" /></button>
        {open ? <div class="hubcfg" data-slot="ClientReportPanel" role="dialog" aria-label="Client report settings"><ClientReportPanel code={code} onClose={() => { hubCfg.value = false; }} /></div> : null}
      </span>
    </>
  );
}
