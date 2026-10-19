// @ts-check
/* Intake and Review's proposal rows (#232-0 skeleton, v2.5.0; split out of rows.jsx so 232-A and 232-B do not edit one file).
   ProposalGroups draws an open meeting's groups, or the mail and other sections, with each proposal as a plain line; 232-B replaces
   ProposalLine with the full row: kind pill, title, the emphasised line, the quote, the source, Approve and Reject, and the peek.
   Tokens and the app's own classes only (style.css, "#232 Intake and Review"). */
import { pName } from "../../core/data.js";
import { irGroupsShown } from "../../core/irFold.js";
import { irDone, irRow } from "../../stores/intakeReview.js";
import { IR_GROUP_HEAD, irKind } from "./rows.jsx";

/** One proposal as a plain line (232-B replaces it). @param {{n: number, child?: boolean}} props */
export function ProposalLine({ n, child }) {
  const r = irRow(n);
  if (!r) return null;
  return (
    <tr class={`irprop${child ? " mchild" : ""}`} data-irn={n}>
      <td class="title"><span class="ickind">{irKind(r)}</span> <b class="icttl">{(r.rec && r.rec.t) || ""}</b>{r.p ? <span class="sub"> · {pName(r.p)}</span> : null}</td>
      <td class="iracts"></td>
    </tr>
  );
}

/** The groups under an open meeting (child rows on its rail) or in the mail and other sections.
    @param {{groups: {needs: number[], routine: number[]}, meet?: string, child?: boolean}} props */
export function ProposalGroups({ groups, meet, child }) {
  return <>{irGroupsShown(groups, irDone).map(g => (
    <>
      <tr class={`icsubhead ${g.kind}${child ? " child" : ""}`} data-irg={g.kind}><td colSpan={2}>
        <span class="icsh">{meet ? `${meet} · ` : ""}{IR_GROUP_HEAD[g.kind][0]} · {g.ns.length}</span>
        <span class="icshs">{IR_GROUP_HEAD[g.kind][1]}</span>
        {g.kind === "routine" ? <span class="icshr"><button type="button" class="mini ok" data-ira="routine" disabled title="232-B">Approve routine ({g.ns.length})</button></span> : null}
      </td></tr>
      {g.ns.map(n => <ProposalLine n={n} child={child} />)}
    </>
  ))}</>;
}
