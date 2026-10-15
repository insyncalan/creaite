// @ts-check
/* ReportingSpace (BL-337, v2.1.0 P9): one reporting space per project (#reporting=ABC&w=<week>&e=<view>). Weeks down the left,
   newest first, each with both reports' state; the week's internal and client reports as two cards (state, who it is for, how the
   client version differs, Open, Approve, Export); Edit both side by side; the files filed for the week. Opened by the cockpit's
   Reporting card, the Reports page, Today's reminder and ⌘K: all the same screen. Read only; what Approve and Export do belongs to
   the report editor (stores/reporting.js says what is stubbed). A client not due that week shows Not due, with Make one anyway. */
import { render } from "preact";
import { Chip } from "../Chip.jsx";
import { Icon } from "../Icon.jsx";
import { ReportEditorStub } from "./ReportEditorStub.jsx";
import { $ } from "../../core/dom.js";
import { go, navWrite } from "../../core/nav.js";
import { P } from "../../core/data.js";
import { fd } from "../../core/page.js";
import { shared } from "../../core/state.js";
import { clientReportHref, reportingHref, repTick, spaceCode, spaceEdit, spaceWeek, spaceWeeks, thisWeek, weekLabel, weekView } from "../../stores/reporting.js";

/** Open a project's reporting space (the one door every way in uses).
    @param {string} code @param {string} [week] @param {""|"internal"|"client"|"side"} [edit] */
export function openSpace(code, week = "", edit = "") {
  spaceWeek.value = week; spaceEdit.value = edit;
  go("reporting", code);
}


/** A report's state as a chip. @param {{s: import("../../stores/reporting.js").RepState}} props */
export function StateChip({ s }) {
  return <Chip tone={s.tone === "ok" ? "ok" : s.tone === "warn" ? "warn" : "mute"}>{s.label}</Chip>;
}

/** A page outline in miniature, as the mockup's cards. @param {{c: string}} props */
function Thumb({ c }) {
  return <div class="rp-thumb" aria-hidden="true"><i class="w40" /><i class="rp-flag" data-kind={c} /><i /><i class="w80" /><i class="w60" /><i /></div>;
}

/** @param {{code: string}} props */
function SpaceView({ code }) {
  repTick.value;   /* a reload of the data redraws */
  const p = P.find(x => x.code === code);
  if (!p) return null;
  const weeks = spaceWeeks(code), cur = thisWeek();
  const week = spaceWeek.value || cur;
  const v = weekView(code, week), c = v.clients[0], editing = spaceEdit.value, isCur = week === cur;
  const open = (/** @type {any} */ m) => { spaceEdit.value = m; navWrite(true); };
  const pick = (/** @type {string} */ w) => { spaceWeek.value = w; navWrite(false); };
  const internalOk = v.internal.key === "filed" || v.internal.key === "approved";
  const crumb = (
    <nav class="crumb" aria-label="Breadcrumb">
      <a href="#" data-go="projects">Projects</a><span aria-hidden="true">›</span>
      <a href="#" data-cock={code}>{p.name}</a><span aria-hidden="true">›</span>
      {editing ? <><a href="#" onClick={e => { e.preventDefault(); open(""); }}>Reporting</a><span aria-hidden="true">›</span><span aria-current="page">Week ending {weekLabel(week)}</span></>
        : <span aria-current="page">Reporting</span>}
    </nav>
  );
  if (editing) return <div class="wrapmax rp">{crumb}<ReportEditorStub mode={editing} client={c.client} internalOk={internalOk} onMode={open} /></div>;
  const ask = (/** @type {string} */ k) => `${k === "weekly" ? "weekly report" : "client report"} ${code}${k === "weekly" ? ` for week ending ${weekLabel(week)}` : ""}`;
  const doOpen = (/** @type {any} */ st, /** @type {string} */ m) => st.path
    ? <a class="btn sm" href="#" data-openfile={st.path}>Open</a>
    : st.key === "notdue" ? <button type="button" class="btn sm" onClick={() => open(m)}>Make one anyway</button>
    : isCur ? <button type="button" class="btn sm primary" onClick={() => open(m)}>{st.key === "draft" ? "Open and check" : "Open"}</button>
    : <span class="sub">Nothing filed</span>;
  return (
    <div class="wrapmax rp">
      {crumb}
      <div class="hhead"><div style={{ flex: 1 }}>
        <h1>Reporting</h1>
        <div class="sub">{p.name} · internal weekly, and {c.client} {c.rhythm.toLowerCase()}</div>
      </div></div>
      <div class="rp-space">
        <div class="rp-weeks" role="group" aria-label="Weeks">
          {weeks.map(w => {
            const x = weekView(code, w);
            return (
              <button type="button" class="rp-wk" key={w} data-week={w} aria-pressed={w === week} onClick={() => pick(w)}>
                <span class="l">Week ending {weekLabel(w)}</span>
                <span class="s"><Chip tone={x.internal.tone || "mute"}>Internal: {x.internal.label}</Chip><Chip tone={x.clients[0].state.tone || "mute"}>Client: {x.clients[0].state.label}</Chip></span>
              </button>
            );
          })}
        </div>
        <div class="rp-main">
          <div class="rp-pair">
            <section class="rp-card" aria-label="Weekly report">
              <div class="top"><b>Weekly report</b><Chip tone="mute">Internal</Chip><StateChip s={v.internal} /></div>
              <Thumb c="internal" />
              <div class="rp-kv"><span>Health</span><span>{p.health || "Not set"}</span><span>Edited</span><span>{v.internal.edited || (internalOk ? "filed on the Friday" : "not yet")}</span></div>
              <div class="acts">
                {doOpen(v.internal, "internal")}
                {!internalOk && isCur ? <button type="button" class="btn sm" data-ask={ask("weekly")} data-tip="Draft the weekly report with ask creaite">Draft it</button> : null}
                <button type="button" class="btn sm" disabled data-tip="Approve and Export arrive with the report editor (BL-335)">{internalOk ? "Export" : "Approve"}</button>
              </div>
            </section>
            <section class="rp-card" aria-label="Client report">
              <div class="top"><b>Client report</b><Chip tone="mute">{c.client}</Chip><StateChip s={c.state} /></div>
              {c.state.key === "notdue"
                ? <div class="sub">{c.client} is {c.rhythm.toLowerCase()}; no client report was due this week.</div>
                : <>
                    <Thumb c="client" />
                    <div class="rp-kv"><span>Health</span><span>{p.health || "Not set"}{c.differs ? <> <Chip tone="plan">differs</Chip></> : null}</span>
                      {c.differs ? <><span>Differs</span><span>{c.differs}</span></> : null}</div>
                  </>}
              <div class="acts">
                {doOpen(c.state, "client")}
                {c.state.key !== "notdue" ? <a class="btn sm" href={clientReportHref(code, week, c.client)} data-clientreport>Client view</a> : null}
                {c.state.key !== "notdue" && !c.state.path && isCur ? <button type="button" class="btn sm" data-ask={ask("client")} data-tip="Draft the client report with ask creaite">Draft it</button> : null}
                {c.state.key === "notdue" ? null
                  : <button type="button" class="btn sm" disabled data-tip={!internalOk && isCur ? "Approve the internal report first" : "Approve and Export arrive with the report editor (BL-336)"}>{c.state.path ? "Export" : "Approve"}</button>}
                {!internalOk && isCur && c.state.key !== "notdue" ? <span class="sub">Approve the internal report first</span> : null}
              </div>
            </section>
          </div>
          <div class="rp-both">
            <span><b>Edit both side by side</b><br /><span class="sub">The internal page beside the client page, section by section, with the differences marked.</span></span>
            <button type="button" class="btn primary" onClick={() => open("side")}>Edit both</button>
          </div>
          <section class="card rp-files" aria-label="Filed for this week">
            <h2>Filed for this week</h2>
            {v.files.length
              ? v.files.map(f => <div key={f.path}><span class="ftype">{f.type}</span><a href="#" class="g" data-openfile={f.path}>{f.n}</a><span class="sub">{f.date ? fd(f.date) : ""}</span></div>)
              : <div class="sub">Nothing filed yet{isCur ? ": approve to file." : "."}</div>}
          </section>
        </div>
      </div>
    </div>
  );
}

let spaceMounted = false;
/** go()'s renderer for #reporting=<code>. @param {string} code */
export function renderReporting(code) {
  const el = $("#v-reporting");
  if (!el) return;
  spaceCode.value = code;
  if (!spaceMounted) { render(<SpaceHost />, el); spaceMounted = true; }
}
function SpaceHost() { return spaceCode.value ? <SpaceView code={spaceCode.value} /> : null; }
