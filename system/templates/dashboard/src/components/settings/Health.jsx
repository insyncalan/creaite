// @ts-check
/* Health (BL-320, v1.9.2), a section of Settings: only what needs Alan, one line each in plain words, from /api/health (doctor's
   checks, run read only). Each line says how bad it is in words, not colour alone, and what to do:
   - a fix Alan's guard decision covers (`fix.built`, health_fixes.py) shows what it will do, then its button. The button posts
     POST /api/health/fix/<id> with nothing else (the server runs that one fix's own command; it takes nothing from the page),
     says the answer's message, opens the answer's `url` (Microsoft 365: Claude's connector page) and checks again;
   - every other fix is a disclosure, "How to fix", with the manual step and Copy when the step is a command.
   The fixes no check can see (Chrome's icon, Microsoft 365) are offered on their own, under "If you need them". The checks that
   passed fold into one line; errors that kept coming back and have stopped are listed as stopped (BL-263); the last archiving
   runs (BL-10, BL-03) are listed under Archiving. A problem can be dismissed (#242), with an optional one-line reason: it stops
   counting and is listed under a quiet "Dismissed (n)", with Restore; a failure of the engine's own integrity says why it
   can't be. The check runs when
   Health opens (if it hasn't this visit) and on Check again; it takes a few seconds, shown as it runs. */
import { useEffect, useState } from "preact/hooks";
import { linkUrl } from "../../core/linkUrl.js";
import { copied, fd } from "../../core/page.js";
import { api, snack, viaServer } from "../../core/server.js";
import { checkHealth, dismissProblem, healthResult, healthBusy, healthError, healthCardWaiting, markCardWaiting, restoreProblem }
  from "../../stores/settings.js";
import { pendingEdit } from "../../ask.js";

const CMD = /system\/scripts\/run [^,;"]+/;
/** The command in a manual step, to copy, or "". @param {string} how */
export const commandIn = how => { const m = CMD.exec(how || ""); return m ? m[0].trim() : ""; };

export const CARD_WAITING = "On the approval card, waiting for you";

/** Run one built fix through its fixed route: no body, no query string. @param {import("../../stores/settings.js").Fix} f */
export async function runHealthFix(f) {
  /* #370: Check now starts the catch-up through its own route, as Today's does; the server says whether it can start */
  const r = f.call ? await api(f.call, {}) : await api(`/api/health/fix/${encodeURIComponent(f.id || "")}`);
  /* a move waits on the approval card: nothing has changed yet, so it is never "Done" (BL-09, #94) */
  if (r.ok && r.card) { markCardWaiting(f.id || ""); snack(CARD_WAITING + ": nothing moves until you approve it."); }
  else snack(r.message || (r.ok ? "Done" : "It wasn't fixed"));
  if (r.ok && r.url && !linkUrl(r.url)) snack("That address can't be opened here");     /* #159: only an address core/linkUrl.js accepts is opened */
  else if (r.ok && r.url) window.open(/** @type {string} */ (linkUrl(r.url)), "_blank", "noopener");
  if (r.ok && r.card) await pendingEdit();      /* BL-09: a move waits on the approval card in ask creaite */
  if (r.ok && !r.url) checkHealth();
  return !!r.ok;
}

/** @typedef {{f: import("../../stores/settings.js").Fix, label: string}} FixButtonProps */

/** A built fix's button: says what it will do first (beside it), disabled while it runs. @param {FixButtonProps} props */
function FixButton({ f, label }) {
  const [busy, setBusy] = useState(false);
  return (
    <button type="button" class="btn primary" disabled={busy || !viaServer()} aria-label={`${f.button}: ${label}`}
      onClick={async () => { setBusy(true); await runHealthFix(f); setBusy(false); }}>{busy ? "Working…" : f.button}</button>
  );
}

/* ===== BL-323 (Alan, 14-10-2026): Restore from a backup =====
   Choose a backup lists the daily zips (/api/backup/list); Preview asks what a restore would replace (/api/backup/preview,
   nothing changes) and shows it on a confirm card; Restore (/api/backup/restore) restores the vault. Each sends only
   {zip: name}, a name from the server's own list; the server keeps the current database and every replaced file first. */
/** @typedef {{name:string, day:string, where:string, size:number}} BackupZip */
/** @typedef {{path:string, what:string}} PlanLine */

const mbOf = (/** @type {number} */ n) => `${(n / 1e6).toFixed(n >= 1e7 ? 0 : 1)} MB`;

/** Settings › Health › Restore from a backup. */
function RestoreBackup() {
  const [zips, setZips] = useState(/** @type {BackupZip[]|null} */ (null));
  const [plan, setPlan] = useState(/** @type {{zip:string, day:string, lines:PlanLine[]}|null} */ (null));
  const [busy, setBusy] = useState(false), [done, setDone] = useState(/** @type {string[]} */ ([]));
  const list = async () => { setBusy(true); const r = await api("/api/backup/list", {}); setBusy(false);
    if (r.ok) { setZips(r.zips || []); setPlan(null); setDone([]); } else snack(r.message || "Couldn't list the backups"); };
  const preview = async (/** @type {BackupZip} */ z) => { setBusy(true); const r = await api("/api/backup/preview", { zip: z.name }); setBusy(false);
    if (r.ok) setPlan({ zip: z.name, day: r.day || z.day, lines: r.plan || [] }); else snack(r.message || "That backup can't be restored"); };
  const restore = async () => { if (!plan) return; setBusy(true); const r = await api("/api/backup/restore", { zip: plan.zip }); setBusy(false);
    snack(r.message || (r.ok ? "Restored" : "It wasn't restored")); if (r.ok) { setPlan(null); setDone(r.done || []); } };
  return (
    <div class="hrestore" id="backupRestore">
      <h3 class="hsub">Restore from a backup</h3>
      <p class="sub">Puts creaite back as it was in a daily backup: your project record, settings, items waiting in Review and history. The current database and every file it replaces are kept first. Project files are never touched.</p>
      {!zips && <button type="button" class="btn" id="backupList" disabled={busy || !viaServer()} onClick={list}>Choose a backup…</button>}
      {zips && !plan && (zips.length
        ? <ul class="hlist" aria-label="Backups">{zips.map(z => (
            <li class="hrow" data-zip={z.name}>
              <span class="hico" aria-hidden="true"></span>
              <div class="hbody"><div class="t">{fd(z.day)}</div><div class="d">{z.where} · {mbOf(z.size)}</div></div>
              <div class="hact"><button type="button" class="btn" disabled={busy} aria-label={`Preview the backup of ${fd(z.day)}`} onClick={() => preview(z)}>Preview</button></div>
            </li>))}</ul>
        : <p class="sub">There are no backups yet: one is made each day.</p>)}
      {plan && (
        <div class="card hconfirm" role="group" aria-label="Confirm the restore" id="backupConfirm">
          <div class="t">Restore from the backup of {fd(plan.day)}?</div>
          <p class="sub">This will replace:</p>
          <ul class="hsteps">{plan.lines.map(l => <li data-path={l.path}><code>{l.path}</code> — {l.what}</li>)}</ul>
          <div class="hact">
            <button type="button" class="btn danger" id="backupRestoreGo" disabled={busy} onClick={restore}>{busy ? "Restoring…" : "Restore"}</button>
            <button type="button" class="btn" disabled={busy} onClick={() => setPlan(null)}>Cancel</button>
          </div>
        </div>
      )}
      {done.length > 0 && <ul class="hsteps" aria-label="What was restored">{done.map(d => <li>{d}</li>)}</ul>}
    </div>
  );
}
/* ===== end BL-323 ===== */

/** @typedef {{p: import("../../stores/settings.js").Problem}} ProblemProps */

/** #242: Dismiss, then its one-line reason (optional) and Dismiss or Cancel. @param {ProblemProps & {onClose:()=>void}} props */
function DismissForm({ p, onClose }) {
  const [why, setWhy] = useState(""), [busy, setBusy] = useState(false);
  const go = async () => { setBusy(true); const ok = await dismissProblem(p, why); setBusy(false);
    if (ok) snack(`Dismissed: ${p.title}. It's under Dismissed until you restore it or it changes.`); else onClose(); };
  return (
    <div class="hhow hdismissform" role="group" aria-label={`Dismiss: ${p.title}`}>
      <input type="text" class="hreason" maxLength={200} size={28} value={why} placeholder="Why (optional)" aria-label="Why you're dismissing it (optional)"
        ref={el => { if (el && !el.dataset.focused) { el.dataset.focused = "1"; el.focus(); } }}
        onInput={e => setWhy(/** @type {HTMLInputElement} */ (e.currentTarget).value)}
        onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); go(); } else if (e.key === "Escape") { e.stopPropagation(); onClose(); } }} />
      <button type="button" class="btn hdismissgo" disabled={busy} onClick={go}>{busy ? "Saving…" : "Dismiss"}</button>
      <button type="button" class="btn" disabled={busy} onClick={onClose}>Cancel</button>
    </div>
  );
}

/** One problem. @param {ProblemProps} props */
function Problem({ p }) {
  const [open, setOpen] = useState(false), [asking, setAsking] = useState(false);
  const bad = p.severity === "fail", hid = `hhow-${p.id}`, cmd = commandIn(p.fix.how);
  const copy = (/** @type {Event} */ e) => {
    const b = /** @type {HTMLElement} */ (e.currentTarget);
    (navigator.clipboard ? navigator.clipboard.writeText(cmd) : Promise.reject()).then(() => { copied(b); snack("Copied"); }, () => snack("Couldn't copy"));
  };
  return (
    <li class="hrow" data-check={p.id}>
      <span class={`hico ${bad ? "bad" : "warn"}`} aria-hidden="true">!</span>
      <div class="hbody">
        <div class="t">{p.title} <span class={`tag ${bad ? "bad" : "warn"}`}>{bad ? "Needs fixing" : "Worth a look"}</span></div>
        {p.detail && <div class="d">{p.detail}</div>}
        {p.fix.built && <div class="hdoes">{p.fix.does}</div>}
        {p.fix.id && healthCardWaiting.value.includes(p.fix.id) && <div class="hdoes hwait" role="status">{CARD_WAITING}.</div>}
        {!p.fix.built && open && (
          <div class="hhow" id={hid}>
            {p.fix.how ? <span>{p.fix.how}</span> : <span>Only you can take this step: the line above says what is wrong.</span>}
            {cmd && <button type="button" class="mini" aria-label={`Copy the command: ${cmd}`} onClick={copy}>Copy</button>}
          </div>
        )}
        {!p.dismissable && p.keep_why && <div class="d hkeep">{p.keep_why}</div>}
        {asking && <DismissForm p={p} onClose={() => setAsking(false)} />}
      </div>
      <div class="hact">
        {p.fix.built
          ? <FixButton f={p.fix} label={p.title} />
          : <button type="button" class="btn" aria-expanded={open ? "true" : "false"} aria-controls={open ? hid : undefined} onClick={() => setOpen(!open)}>How to fix</button>}
        {p.dismissable && !asking && viaServer() &&
          <button type="button" class="btn quiet hdismiss" aria-label={`Dismiss: ${p.title}`} onClick={() => setAsking(true)}>Dismiss</button>}
      </div>
    </li>
  );
}

/** #242: the dismissed problems, folded, each with its reason, date and Restore. @param {{list: import("../../stores/settings.js").Problem[]}} props */
function Dismissed({ list }) {
  const [busy, setBusy] = useState("");
  const back = async (/** @type {import("../../stores/settings.js").Problem} */ p) => {
    setBusy(p.key); const ok = await restoreProblem(p); setBusy(""); if (ok) snack(`Restored: ${p.title}`); };
  return (
    <details class="hfine" id="healthDismissed">
      <summary>Dismissed ({list.length})</summary>
      <ul class="hlist" aria-label="Dismissed problems">
        {list.map(p => (
          <li class="hrow" data-check={p.id} key={p.key}>
            <span class="hico" aria-hidden="true"></span>
            <div class="hbody">
              <div class="t">{p.title}</div>
              {p.detail && <div class="d">{p.detail}</div>}
              <div class="d">Dismissed {fd(p.date || "")}{p.reason ? `: ${p.reason}` : ""}</div>
            </div>
            <div class="hact"><button type="button" class="btn hrestorebtn" disabled={!!busy || !viaServer()} aria-label={`Restore: ${p.title}`}
              onClick={() => back(p)}>{busy === p.key ? "Restoring…" : "Restore"}</button></div>
          </li>))}
      </ul>
    </details>
  );
}

/** Settings › Health. */
export function Health() {
  const res = healthResult.value, busy = healthBusy.value, err = healthError.value;
  useEffect(() => { if (!res && !busy && viaServer()) checkHealth(); }, []);
  const n = res ? res.problems.length : 0, alone = res && res.standalone ? res.standalone : [];
  return (
    <div class="card wide" id="healthCard">
      <div class="hhead">
        <h2>Health</h2>
        <span class="sub" role="status">{busy ? "Checking… (a few seconds)" : res ? `Checked ${fd(res.checked)}` : ""}</span>
        <button type="button" class="btn" id="healthCheck" disabled={busy || !viaServer()} onClick={() => checkHealth()}>Check again</button>
      </div>
      {!viaServer() && !res && <p class="sub">The health check needs creaite running.</p>}
      {err && <p class="sub hbad" role="alert">{err}</p>}
      {res && (
        <>
          <p class="sub hsum">{n ? `${n} thing${n === 1 ? "" : "s"} need${n === 1 ? "s" : ""} you.` : "Nothing needs you."}</p>
          {n > 0 && <ul class="hlist" aria-label="What needs you">{res.problems.map(p => <Problem key={p.key || p.id} p={p} />)}</ul>}
          {res.stopped.length > 0 && (
            <ul class="hlist" aria-label="Errors that have stopped">
              {res.stopped.map(s => (
                <li class="hrow stopped">
                  <span class="hico ok" aria-hidden="true">✓</span>
                  <div class="hbody"><div class="t">Stopped: {s.area} <span class="tag">{s.count} ×</span></div><div class="d">{s.message} ({s.span})</div></div>
                  <div class="hact"></div>
                </li>
              ))}
            </ul>
          )}
          {(res.dismissed || []).length > 0 && <Dismissed list={res.dismissed || []} />}
          <details class="hfine">
            <summary>{res.fine} check{res.fine === 1 ? "" : "s"} fine</summary>
            <p class="sub">{res.fine_names.join(", ")}</p>
          </details>
          {(res.archiving || []).length > 0 && (
            <>
              <h3 class="hsub">Archiving</h3>
              <ul class="hsteps" id="healthArchiving" aria-label="Archiving">
                {(res.archiving || []).map(a => <li>{a}</li>)}
              </ul>
            </>
          )}
          {(res.archived || []).length > 0 && (
            <>
              {/* #385 (Alan, 26-10-2026): every archived project in one place, with where its folder is now */}
              <h3 class="hsub">Archived projects</h3>
              <ul class="hsteps" id="healthArchived" aria-label="Archived projects">
                {(res.archived || []).map(a => <li>{a}</li>)}
              </ul>
            </>
          )}
          {alone.length > 0 && (
            <>
              <h3 class="hsub">If you need them</h3>
              <ul class="hlist" aria-label="Fixes no check can see">
                {alone.map(f => (
                  <li class="hrow" data-fix={f.id}>
                    <span class="hico" aria-hidden="true"></span>
                    <div class="hbody"><div class="t">{f.title}</div><div class="d">{f.does}</div></div>
                    <div class="hact"><FixButton f={f} label={f.title} /></div>
                  </li>
                ))}
              </ul>
            </>
          )}
        </>
      )}
      {res && res.backups && res.backups.length > 0 && (
        <>
          {/* BL-323: the last OneDrive copy, restore check and Tidy up, and what leaves the laptop */}
          <h3 class="hsub">Backups</h3>
          <p class="sub">Each day a closed zip of the database backup, your settings, the items waiting in Review and creaite's history goes to your OneDrive backup folder. ask creaite's chats, the people you follow, the engine and the live database never leave the laptop.</p>
          <ul class="hsteps">{res.backups.map(b => <li>{b}</li>)}</ul>
        </>
      )}
      <RestoreBackup />
      <h3 class="hsub">After every update, creaite does this for you</h3>
      <ul class="hsteps">
        <li>Backs up first, and rolls back if a step fails</li>
        <li>Makes creaite's launcher again</li>
        <li>Asks Chrome to refresh its copy of the app's icon</li>
        <li>Restarts creaite on the new version, and runs the health check</li>
      </ul>
    </div>
  );
}
