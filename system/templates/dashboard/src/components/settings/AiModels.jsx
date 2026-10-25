// @ts-check
/* AI models (#132, approved mockup 16-10-2026), a section of Settings › Essentials: which model each kind of job uses, how
   creaite signs in to each provider, and what happens when a limit is reached. Everything it shows comes from
   /api/ai/state (providers.py), so the words and the rules live in one place.

   - Providers as cards. Claude: Connected, with Sign in again (a dialog with the Terminal step) and Use an API key. OpenAI:
     Connect… (a key; billed to the OpenAI account), then Manage… and Disconnect. Local model, Hosted free models and
     DeepSeek are greyed with "Available soon" and a disabled button (not focusable).
   - The connect journey, one Dialog in steps: the key (a password field and the plain warning), Testing the key…, then the
     models found as tick boxes and Done. A wrong key, a network error or the not-built keychain keep the box open with the
     reason. Cancel while testing drops the tested key (/api/ai/forget). The key goes only to /api/ai/test and is cleared
     from the field and from this component as soon as it is sent.
   - Four kinds of job, each with a model list (only connected providers' offered models; tool jobs only tool-capable ones;
     the recommended model marked). A weaker choice than recommended asks first (Keep the recommended model, Use it anyway);
     Esc keeps the recommended model. Use it anyway is remembered by the server.
   - When a limit is reached: three choices; "another connected model" needs a second provider.
   - The two fixed rules (confidential material only to Claude; the quick-edit check and retry) are a note, not switches. */
import { useEffect, useRef, useState } from "preact/hooks";
import { Dialog } from "../Dialog.jsx";
import { copied } from "../../core/page.js";
import { SERVED, snack, viaServer } from "../../core/server.js";
import { aiCall, aiError, aiState, loadAi } from "../../stores/settings.js";

/** @typedef {import("../../stores/settings.js").AiProvider} AiProvider */
/** @typedef {import("../../stores/settings.js").AiJob} AiJob */
/** @typedef {{provider:AiProvider, step:string, error:string, pending:string, models:{id:string,label:string}[],
     ticked:string[]}} Flow */

let AI_N = 0;
const uid = (/** @type {string} */ p) => `${p}${++AI_N}`;

/** The verb a greyed card's button shows. @param {AiProvider} p */
const soonVerb = p => p.id === "local" ? "Set up" : "Connect";

/** @typedef {{p:AiProvider, onConnect:(p:AiProvider)=>void, onManage:(p:AiProvider)=>void, onDisconnect:(p:AiProvider)=>void,
     onSignIn:()=>void}} CardProps */

/** One provider card. @param {CardProps} props */
function ProviderCard({ p, onConnect, onManage, onDisconnect, onSignIn }) {
  const [hid] = useState(() => uid("aip"));
  const soon = p.status === "soon", on = p.status === "connected";
  const how = p.id === "claude" ? (p.auth === "key" ? "Signed in with an Anthropic API key." : "Signed in with your subscription.")
    : p.blurb;
  return (
    <div class={`aicard${soon ? " soon" : ""}`} data-prov={p.id} aria-labelledby={hid} role="group" aria-disabled={soon ? "true" : undefined}>
      <h4 id={hid}>{p.name}
        {soon ? <span class="tag aisoon">Available soon</span>
          : on ? <span class="tag aiok">Connected</span> : <span class="tag">Not connected</span>}</h4>
      <p class="sub">{soon ? p.blurb : how}</p>
      {!soon && p.billing && p.id !== "claude" ? <p class="sub">{p.billing}</p> : null}
      {on && p.models.length ? <p class="aimodels-list">{p.models.join(" · ")}</p> : null}
      <span class="aisp"></span>
      <div class="aiact">
        {soon ? <button type="button" class="btn" disabled aria-label={`${soonVerb(p)} ${p.name}: available soon`}>{soonVerb(p)}</button>
          : p.id === "claude" ? <>
              <button type="button" class="btn" onClick={onSignIn} aria-haspopup="dialog">Sign in again…</button>
              {p.auth === "key"
                ? <button type="button" class="linkbtn" onClick={() => onDisconnect(p)} aria-haspopup="dialog">Use my subscription</button>
                : <button type="button" class="linkbtn" onClick={() => onConnect(p)} aria-haspopup="dialog">Use an API key</button>}
            </>
          : on ? <>
              <button type="button" class="btn" onClick={() => onManage(p)} aria-haspopup="dialog" aria-label={`Manage ${p.name}'s models`}>Manage…</button>
              <button type="button" class="linkbtn" onClick={() => onDisconnect(p)} aria-haspopup="dialog" aria-label={`Disconnect ${p.name}`}>Disconnect</button>
            </>
          : <button type="button" class="btn primary" onClick={() => onConnect(p)} aria-haspopup="dialog" aria-label={`Connect ${p.name}`}>Connect…</button>}
      </div>
    </div>
  );
}

/** @typedef {{flow:Flow|null, setFlow:(f:Flow|null)=>void, warning:string}} ConnectProps */

/** The connect journey and Manage, one dialog in steps. @param {ConnectProps} props */
function ConnectDialog({ flow, setFlow, warning }) {
  const key = useRef(/** @type {HTMLInputElement|null} */ (null));
  const live = useRef(/** @type {Flow|null} */ (null));
  live.current = flow;
  const [hid] = useState(() => uid("aic"));
  if (!flow) return <Dialog open={false} onClose={() => {}} id="aiConnect" class="rvdlg aidlg" labelledBy={hid}><h2 id={hid}>Connect</h2></Dialog>;
  const p = flow.provider, isClaude = p.id === "claude";
  const set = (/** @type {Partial<Flow>} */ ch) => { if (live.current) setFlow({ ...live.current, ...ch }); };
  const test = async () => {
    const el = key.current, k = el ? el.value.trim() : "";
    if (!k) { set({ error: "Paste the key first." }); if (el) el.focus(); return; }
    if (el) el.value = "";                                       /* the key leaves the page's fields once sent */
    set({ step: "testing", error: "" });
    const r = await aiCall("/api/ai/test", { provider: p.id, key: k });
    const now = live.current;
    if (!now || now.step !== "testing" || now.provider.id !== p.id) {  /* cancelled while testing: drop the held key */
      if (r.ok && r.pending) aiCall("/api/ai/forget", { pending: r.pending });
      return;
    }
    if (!r.ok) { setFlow({ ...now, step: "key", error: r.message || "The key wasn't accepted." }); return; }
    const models = r.models || [];
    setFlow({ ...now, step: "found", pending: r.pending, models, ticked: models.map((/** @type {{id:string}} */ m) => m.id) });
  };
  const done = async () => {
    const r = await aiCall("/api/ai/connect", { pending: flow.pending, offered: flow.ticked });
    setFlow(null);
    snack(r.ok ? (isClaude ? "Claude now uses your API key" : `${p.name} is connected: its models are in the lists`) : r.message || "It wasn't connected");
  };
  const saveOffer = async () => {
    const r = await aiCall("/api/ai/offer", { provider: p.id, offered: flow.ticked });
    setFlow(null);
    const reset = r.reset || [];
    snack(r.ok ? (reset.length ? `Saved. ${reset.length === 1 ? "One kind of job" : `${reset.length} kinds of job`} went back to the recommended model` : "Saved") : r.message || "It wasn't saved");
  };
  const cancel = () => {
    if (flow.step === "found") { done(); return; }               /* the key was accepted: closing keeps it, as Done does */
    if (flow.pending) aiCall("/api/ai/forget", { pending: flow.pending });
    setFlow(null);
  };
  /** @param {string} id @param {boolean} on */
  const tick = (id, on) => set({ ticked: on ? [...flow.ticked.filter(x => x !== id), id] : flow.ticked.filter(x => x !== id) });
  const ticks = (/** @type {{id:string,label:string}[]} */ ms) => (
    <div class="aiticks" role="group" aria-label={`${p.name} models to offer`}>
      {ms.map(m => <label><input type="checkbox" checked={flow.ticked.includes(m.id)}
        onChange={e => tick(m.id, /** @type {HTMLInputElement} */ (e.currentTarget).checked)} /> {m.label}</label>)}
    </div>
  );
  const errId = hid + "e";
  return (
    <Dialog open onClose={cancel} id="aiConnect" class="rvdlg aidlg" labelledBy={hid} focus={flow.step === "key" ? "#aiKey" : undefined}
      cmdEnter={flow.step !== "testing"} dirty={flow.step === "testing"}>
      {flow.step === "key" && <>
        <h2 id={hid}>{isClaude ? "Use an API key for Claude" : `Connect ${p.name}`}</h2>
        <p class="sub">{isClaude ? "An Anthropic API key is billed to that account, not to your Claude subscription." : `${p.name} is billed to your ${p.name} account, not to your Claude subscription.`}</p>
        <p class="aihow2"><b>How you sign in:</b> an API key{isClaude ? " (your subscription stays as it is: Sign in again)" : `, from your ${p.name} account`}.</p>
        <input type="password" id="aiKey" ref={key} placeholder="API key" aria-label="API key" autocomplete="off" spellcheck={false}
          aria-invalid={flow.error ? "true" : undefined} aria-describedby={flow.error ? errId : undefined}
          onInput={() => { if (live.current && live.current.error) set({ error: "" }); }} />
        {flow.error && <p class="aierr" id={errId} role="alert">{flow.error}</p>}
        <p class="aiwarn">{warning}</p>
        <div class="airow"><button type="button" class="btn" onClick={cancel}>Cancel</button>
          <button type="button" class="btn primary" id="aiTest" onClick={test}>{flow.error ? "Try again" : "Test and connect"}</button></div>
      </>}
      {flow.step === "testing" && <>
        <h2 id={hid}>Testing the key…</h2>
        <p class="sub" role="status"><span class="spin" aria-hidden="true"></span> Asking {p.name} which models this key can use. This takes a few seconds.</p>
        <div class="airow"><button type="button" class="btn" id="aiTestCancel" onClick={cancel}>Cancel</button></div>
      </>}
      {flow.step === "found" && <>
        <h2 id={hid}>{isClaude ? "Claude's key works" : `${p.name} is connected`}</h2>
        {isClaude ? <p class="sub">Claude's runs will use this key, billed to your Anthropic account. Your model choices stay as they are.</p>
          : <>
            <p class="sub">These models are available to this key. Tick the ones to offer in the lists.</p>
            {ticks(flow.models)}
            <p class="sub">Nothing changes yet: {p.name} now appears in the model lists below. You choose where to use it.</p>
          </>}
        <div class="airow"><button type="button" class="btn primary" id="aiDone" onClick={done}>Done</button></div>
      </>}
      {flow.step === "manage" && <>
        <h2 id={hid}>{p.name} models</h2>
        <p class="sub">Tick the models to offer in the lists. A kind of job set to one you untick goes back to its recommended model.</p>
        {ticks(flow.models)}
        <div class="airow"><button type="button" class="btn" onClick={() => setFlow(null)}>Cancel</button>
          <button type="button" class="btn primary" onClick={saveOffer}>Save</button></div>
      </>}
    </Dialog>
  );
}

/** @typedef {{job:AiJob, model:string}} Pend */
/** @typedef {{pend:Pend|null, onKeep:()=>void, onAccept:()=>void}} WeakerProps */

/** A weaker choice asks first. @param {WeakerProps} props */
function WeakerDialog({ pend, onKeep, onAccept }) {
  const [hid] = useState(() => uid("aiw"));
  const opt = pend ? pend.job.options.find(o => o.id === pend.model) : null;
  return (
    <Dialog open={!!pend} onClose={onKeep} id="aiWeaker" class="rvdlg aidlg" labelledBy={hid} describedBy={hid + "d"} cmdEnter={false}
      focus="#aiKeep">
      <h2 id={hid}>{pend && opt ? `Use ${opt.label} for ${pend.job.name.toLowerCase()}?` : "Use a weaker model?"}</h2>
      <p class="sub" id={hid + "d"}>{pend ? `${pend.job.warn} The recommended model here is ${pend.job.recommended_label}.` : ""}</p>
      <div class="airow"><button type="button" class="btn" id="aiKeep" onClick={onKeep}>Keep the recommended model</button>
        <button type="button" class="btn danger" id="aiAnyway" onClick={onAccept}>Use it anyway</button></div>
    </Dialog>
  );
}

/** @typedef {{job:AiJob, shown:string, onPick:(job:AiJob, model:string)=>void, moreHint:boolean}} JobProps */

/** One kind of job: what it is and needs, its features, its model list. @param {JobProps} props */
function JobRow({ job, shown, onPick, moreHint }) {
  const [hid] = useState(() => uid("aij"));
  return (
    <div class="aijob" data-job={job.id} data-keys={`ai.jobs.${job.id}`} role="listitem">
      <div class="aijobwhat">
        <span class="ainm" id={hid}>{job.name}</span>
        <small>{job.line}</small>
        <details><summary>Features in this group</summary><ul>{job.features.map(f => <li>{f}</li>)}</ul></details>
      </div>
      <div class="aineeds" aria-label="What it needs">{job.needs.map(n => <span class="tag aineed">{n}</span>)}
        {job.tools_only ? <small class="aihint">Only tool-capable models are listed.</small> : null}</div>
      <div class="aipick">
        <select aria-labelledby={hid} value={shown} disabled={!viaServer()}
          onChange={e => onPick(job, /** @type {HTMLSelectElement} */ (e.currentTarget).value)}>
          {job.options.map(o => <option value={o.id}>{o.label}{o.recommended ? " (recommended)" : ""}</option>)}
        </select>
        {moreHint ? <small class="aihint">Connect another provider to see more models.</small> : null}
      </div>
    </div>
  );
}

/** The Sign in again dialog: the step is Claude Code's own, in Terminal. @param {{open:boolean, onClose:()=>void}} props */
function SignInDialog({ open, onClose }) {
  const [hid] = useState(() => uid("ais"));
  return (
    <Dialog open={open} onClose={onClose} id="aiSignIn" class="rvdlg aidlg" labelledBy={hid} cmdEnter={false}>
      <h2 id={hid}>Sign in to Claude again</h2>
      <p class="sub">Open Terminal, run the command below, then type <code>/login</code> and follow the steps in your browser. creaite uses the new sign-in from its next run.</p>
      <div class="cmdbox"><code>claude</code>
        <button type="button" class="btn" onClick={e => { const b = /** @type {HTMLButtonElement} */ (e.currentTarget);
          (navigator.clipboard ? navigator.clipboard.writeText("claude") : Promise.reject()).then(() => copied(b), () => snack("Couldn't copy")); }}>Copy</button></div>
      <div class="airow"><button type="button" class="btn primary" onClick={onClose}>Close</button></div>
    </Dialog>
  );
}

/** @typedef {{p:AiProvider|null, onClose:()=>void}} DisconnectProps */

/** Disconnect asks first. @param {DisconnectProps} props */
function DisconnectDialog({ p, onClose }) {
  const [hid] = useState(() => uid("aid"));
  const go = async () => {
    if (!p) return;
    const r = await aiCall("/api/ai/disconnect", { provider: p.id });
    onClose();
    if (!r.ok) { snack(r.message || "It wasn't disconnected"); return; }
    const n = (r.reset || []).length;
    snack(p.id === "claude" ? "Claude uses your subscription again" :
      `${p.name} disconnected${n ? `: ${n === 1 ? "one kind of job" : `${n} kinds of job`} went back to the recommended model` : ""}`);
  };
  const isClaude = p && p.id === "claude";
  return (
    <Dialog open={!!p} onClose={onClose} id="aiDisconnect" class="rvdlg aidlg" labelledBy={hid} cmdEnter={false}>
      <h2 id={hid}>{p ? (isClaude ? "Stop using the API key for Claude?" : `Disconnect ${p.name}?`) : "Disconnect"}</h2>
      <p class="sub">{isClaude ? "The key is removed from this Mac's keychain and Claude goes back to your subscription."
        : p ? `The key is removed from this Mac's keychain and ${p.name}'s models leave the lists. Anything set to one of them goes back to its recommended model.` : ""}</p>
      <div class="airow"><button type="button" class="btn" onClick={onClose}>Cancel</button>
        <button type="button" class="btn danger" id="aiDisconnectGo" onClick={go}>{isClaude ? "Use my subscription" : "Disconnect"}</button></div>
    </Dialog>
  );
}

/** Settings › Essentials › AI models. */
export function AiModels() {
  const [flow, setFlow] = useState(/** @type {Flow|null} */ (null));
  const [pend, setPend] = useState(/** @type {Pend|null} */ (null));
  const [signIn, setSignIn] = useState(false);
  const [leaving, setLeaving] = useState(/** @type {AiProvider|null} */ (null));
  useEffect(() => { if (SERVED && !aiState.value) loadAi(); }, []);
  const st = aiState.value;
  if (!st) return <div class="card wide" id="aiModels"><h2>AI models</h2><p class="sub" role="status">{aiError.value || (SERVED ? "Reading your AI models…" : "AI models need creaite to be running: open creaite from its icon.")}</p></div>;

  const save = async (/** @type {AiJob} */ job, /** @type {string} */ model, accept = false) => {
    const r = await aiCall("/api/ai/choose", { job: job.id, model, accept });
    if (r.needs_accept) { setPend({ job, model }); return; }
    const o = job.options.find(x => x.id === model);
    snack(r.ok ? `${job.name}: ${o ? o.label : model}` : r.message || "It wasn't saved");
  };
  const pick = (/** @type {AiJob} */ job, /** @type {string} */ model) => {
    const o = job.options.find(x => x.id === model);
    if (o && o.weaker && !o.accepted) setPend({ job, model }); else save(job, model);
  };
  const keep = () => { const p = pend; setPend(null); if (p && p.job.value !== p.job.recommended) save(p.job, p.job.recommended); };
  const accept = () => { const p = pend; setPend(null); if (p) save(p.job, p.model, true); };
  const connect = (/** @type {AiProvider} */ p) => setFlow({ provider: p, step: "key", error: "", pending: "", models: [], ticked: [] });
  const manage = (/** @type {AiProvider} */ p) => setFlow({ provider: p, step: "manage", error: "", pending: "",
    models: p.found.map(m => ({ id: m.id, label: m.label })), ticked: p.found.filter(m => m.offered).map(m => m.id) });
  const limit = async (/** @type {string} */ mode) => {
    const r = await aiCall("/api/ai/limit", { mode });
    if (!r.ok) snack(r.message || "It wasn't saved");
  };

  return (
    <div class="card wide aimodels" id="aiModels">
      <h2>AI models</h2>
      <p class="sub">Which models creaite uses for each kind of job, and how you sign in.</p>

      <h3 class="hsub" id="aiProvH">Providers</h3>
      <p class="sub" id="aiProvLine">{st.line}</p>
      <div class="aiprov" role="list" aria-labelledby="aiProvH" data-keys="ai.providers">
        {st.providers.map(p => <div role="listitem" class="aiprovi"><ProviderCard p={p} onConnect={connect} onManage={manage}
          onDisconnect={setLeaving} onSignIn={() => setSignIn(true)} /></div>)}
      </div>

      <h3 class="hsub" id="aiJobsH">Which model does what</h3>
      <p class="sub">creaite sorts every feature into one of four kinds of job. Pick a model for each kind. Each row says what the job needs, so you can choose sensibly; the recommended model is marked.</p>
      <div class="aihowbox"><b>How creaite decides which kind of job something is</b><ol>{st.how.map(x => <li>{x}</li>)}</ol></div>
      <div class="aijobs" role="list" aria-labelledby="aiJobsH" data-keys="ai.accepted_weaker">
        {st.jobs.map(j => <JobRow key={j.id} job={j} moreHint={st.more_hint}
          shown={pend && pend.job.id === j.id ? pend.model : j.value} onPick={pick} />)}
      </div>
      <ul class="airules" aria-label="Always">{st.rules.map(x => <li>{x}</li>)}</ul>

      <fieldset class="ailimit" data-keys="ai.on_limit">
        <legend class="hsub">When a limit is reached</legend>
        <p class="sub">Your Claude limit can run out mid-day. Choose what happens next.</p>
        {st.limits.map(l => (
          <label class={`ailim${l.enabled ? "" : " off"}`} data-limit={l.id}>
            <input type="radio" name="aiLimit" value={l.id} checked={st.on_limit === l.id} disabled={!l.enabled || !viaServer()}
              onChange={() => limit(l.id)} />
            <span><b>{l.label}</b><small>{l.line}</small></span>
          </label>
        ))}
      </fieldset>

      <ConnectDialog flow={flow} setFlow={setFlow} warning={st.key_warning} />
      <WeakerDialog pend={pend} onKeep={keep} onAccept={accept} />
      <SignInDialog open={signIn} onClose={() => setSignIn(false)} />
      <DisconnectDialog p={leaving} onClose={() => setLeaving(null)} />
    </div>
  );
}
