// @ts-check
/* ApprovePopup (v2.1.0 P7, BL-338 point 10): Approve minutes, one popup (784px; Esc or a click outside closes it, focus back on
   Approve). It says what will be filed and lists the items from review.minutes_plan in two groups: Actions and updates, approved
   together with one tick ("Approve all n as reviewed in the minutes", ticked); and one tick each for a new decision, a decision
   recorded or withdrawn, a new risk and an update that closes an item, as the bulk rule requires (MINUTES_GROUP_JOINS is empty,
   so nothing joins the group). Whatever is ticked is applied with the minutes in one apply with Undo (review.approve_minutes,
   through tracker.py apply) and doesn't go to Review again; anything left unticked waits in Review. Checks left open are
   listed first. The minutes are always approved on their own. */
import { useState } from "preact/hooks";
import { Dialog } from "../Dialog.jsx";
import { reloadData, snack, undoApply } from "../../core/server.js";
import { approveMinutes, approveOpen, loadMinutes, minutesView } from "../../stores/minutes.js";

/** @typedef {import("./minutesDoc.js").Check} Check */
/** @typedef {import("../../stores/minutes.js").PlanItem} PlanItem */

const where = (/** @type {string} */ p) => { const parts = p.split("/"); return { name: parts.pop() || p, folder: parts.slice(-2).join(" › ") }; };

/** The popup. @param {{checks: Check[]}} props */
export function ApprovePopup({ checks }) {
  const v = minutesView.value, plan = v && v.plan;
  const [group, setGroup] = useState(true), [own, setOwn] = useState(/** @type {number[]} */ ([])), [err, setErr] = useState(""), [busy, setBusy] = useState(false);
  const close = () => { approveOpen.value = false; setErr(""); };
  if (!plan) return <Dialog open={false} onClose={close} labelledBy="mnApproveH" id="mnApprove"><span /></Dialog>;
  const items = plan.items, grp = items.filter(i => i.group === "group"), ones = items.filter(i => i.group === "own");
  const waits = items.filter(i => i.group === "waits" || i.group === "milestone"), removed = items.filter(i => i.group === "removed");
  const tick = (/** @type {number} */ n, /** @type {boolean} */ on) => setOwn(on ? [...own, n] : own.filter(x => x !== n));
  const go = async () => {
    setBusy(true); setErr("");
    const r = await approveMinutes(group, own);
    setBusy(false);
    if (!r.ok) { setErr(String(r.message || "The apply didn't run; nothing was changed.").split("\n")[0]); return; }
    approveOpen.value = false;
    const n = (r.approved || 0), left = (r.waiting || []).length;
    snack(`Minutes approved with ${n} item${n === 1 ? "" : "s"}${left ? `; ${left} wait in Review` : ""}`, r.apply_id ? () => undoApply(r.apply_id) : null);
    await reloadData();
    if (plan.files[0]) loadMinutes({ path: plan.files[0] });
  };
  const filed = plan.files.map(where);
  return (
    <Dialog open={approveOpen.value} onClose={close} labelledBy="mnApproveH" id="mnApprove" class="mnapprove" focus="#mnApproveGo">
      <div class="mnap">
        <h2 id="mnApproveH">Approve the minutes</h2>
        <p class="sub">{filed.length ? <span>Files the minutes as <b>{filed[0].name}</b> in {filed[0].folder}{plan.transcripts.length ? ", with the transcript in Transcripts" : ""}. </span> : null}
          The minutes and what you tick are applied together, in one apply you can undo. Nothing is sent.</p>
        {checks.length ? <div class="mnap-ck" role="note"><b>{checks.length} check{checks.length === 1 ? "" : "s"} still open</b>
          <ul>{checks.map(c => <li key={c.id}>{c.note}</li>)}</ul></div> : null}
        {grp.length ? <fieldset class="mnap-g"><legend>Actions and updates</legend>
          <label class="mnap-all"><input type="checkbox" id="mnApAll" checked={group} onChange={e => setGroup(/** @type {HTMLInputElement} */ (e.currentTarget).checked)} />
            Approve all {grp.length} as reviewed in the minutes</label>
          <ul>{grp.map(i => <li key={i.n}>{i.label}</li>)}</ul></fieldset> : null}
        {ones.length ? <fieldset class="mnap-g"><legend>One tick each</legend>
          <p class="sub">A new decision, a decision recorded or withdrawn, a new risk and a closure are each approved on their own.</p>
          {ones.map(i => <label key={i.n} class="mnap-one"><input type="checkbox" data-own={i.n} checked={own.includes(i.n)}
            onChange={e => tick(i.n, /** @type {HTMLInputElement} */ (e.currentTarget).checked)} /> <span>{i.label}<span class="sub"> · {i.why}</span></span></label>)}
        </fieldset> : null}
        {waits.length ? <p class="sub">Waiting in Review whatever you tick: {waits.map(i => i.label).join("; ")}.</p> : null}
        {removed.length ? <p class="sub">Removed in the minutes: {removed.length} item{removed.length === 1 ? "" : "s"}, recorded as rejected.</p> : null}
        <p class="sub">Anything you leave unticked waits in Review.</p>
        {err ? <p class="mnap-err" role="alert">{err}</p> : null}
        <div class="mnap-foot">
          <button type="button" class="btn" onClick={close}>Cancel</button>
          <button type="button" class="btn primary" id="mnApproveGo" disabled={busy} onClick={go}>{busy ? "Approving…" : "Approve the minutes"}</button>
        </div>
      </div>
    </Dialog>
  );
}
