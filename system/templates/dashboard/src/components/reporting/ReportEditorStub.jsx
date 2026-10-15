// @ts-check
/* ReportEditorStub (BL-337, v2.1.0 P9): the third step of the reporting journey, Edit: Internal, Client or Side by side,
   switched at the top without leaving the page. STUB. The editor itself (the A4 page, sections, eyes, the peek: BL-335 and
   BL-336, Team Cap's Sheet.jsx) is not on this base, so this draws the mockup's page outlines in its place and disables Approve
   and Export. The view switcher, the breadcrumb, the address (#reporting=ABC&w=…&e=internal|client|side) and the rule that
   Approve on the client report waits for the internal one are real. When Sheet.jsx arrives, mount it in `.rp-canvas` and
   remove this file. */

/** @param {{kind: "internal"|"client", client: string, side: boolean}} props */
function PageOutline({ kind, client, side }) {
  const c = kind === "client";
  return (
    <div class="rp-sheet" role="img" aria-label={`${c ? "Client" : "Internal"} report page, outline only`}>
      <span class="rp-sheet-lab">{c ? `Client report · ${client}` : "Weekly report · Internal"}</span>
      <span class="rp-sheet-bar" data-kind={kind} />
      {side && !c ? <span class="rp-diff">≠ Client</span> : null}
      <i /><i class="w80" />
      <span class="rp-sheet-sh">{c ? "Summary" : "Summary"}{side && !c ? <span class="rp-diff">≠ Client</span> : null}</span><i /><i class="w90" /><i class="w70" />
      <span class="rp-sheet-sh">Milestones</span><i class="tall" />
      <span class="rp-sheet-sh">{c ? `What we need from ${client}` : "What we need from people"}</span><i /><i class="w60" />
      <span class="rp-sheet-sh">{c ? "Points to watch" : "Risks and issues"}{side && !c ? <span class="rp-diff">≠ Client</span> : null}</span><i /><i class="w85" />
      <span class="rp-sheet-sh">{c ? "Where things stand" : "Current state"}</span><i /><i class="w75" />
    </div>
  );
}

/** @param {{mode: "internal"|"client"|"side", client: string, internalOk: boolean, onMode: (m: "internal"|"client"|"side") => void}} props */
export function ReportEditorStub({ mode, client, internalOk, onMode }) {
  const modes = /** @type {[string, string][]} */ ([["internal", "Internal"], ["client", `Client: ${client}`], ["side", "Side by side"]]);
  const label = { internal: "Approve internal", client: "Approve client report", side: "Approve: internal (last edited)" }[mode];
  const waits = mode === "client" && !internalOk;
  return (
    <div class="rp-ed">
      <div class="rp-ebar">
        <span class="seg" role="group" aria-label="View">
          {modes.map(([k, l]) => <button type="button" key={k} data-rpmode={k} aria-pressed={k === mode} onClick={() => onMode(/** @type {any} */ (k))}>{l}</button>)}
        </span>
        <span class="rp-grow" />
        <button type="button" class="btn sm" disabled data-tip="Arrives with the report editor (BL-335)">Show as exported</button>
        <button type="button" class="btn sm" disabled data-tip="Arrives with the report editor (BL-335)">Export</button>
        <button type="button" class="btn primary sm" disabled data-tip={waits ? "Approve the internal report first" : "Arrives with the report editor (BL-335)"}>{label}</button>
      </div>
      <p class="rp-stub" role="note">Outline only: the report page itself arrives with the report editor (BL-335, BL-336). The views, the address and the order of approval are final.</p>
      <div class={`rp-canvas${mode === "side" ? " two" : ""}`}>
        {mode !== "client" ? <PageOutline kind="internal" client={client} side={mode === "side"} /> : null}
        {mode !== "internal" ? <PageOutline kind="client" client={client} side={mode === "side"} /> : null}
      </div>
    </div>
  );
}
