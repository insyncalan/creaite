// @ts-check
/* #300: start creaite when you sign in. The page half; the live server's token-checked routes are the other half (a guarded
   proposal, dev/proposals/300/), so every function here says "not available" and draws nothing broken while they are missing.
   The routes (all POST, nothing sent but what is shown):
     /api/autostart/status {}            -> {ok, supported, installed, loaded, on, dev, folder}
     /api/autostart/set    {on: boolean} -> {ok, message}
   It is the user's own click in the app that installs or removes the login agent, never an ask creaite run (reach.py's never
   list holds ~/Library/LaunchAgents). Three places use it: the Settings switch (beside Stop), the first-run question on Today's
   Getting started, and the Terminal note, which prints the user's own folder, filled in here at run time from the page's own
   vault path and never written in code. */
import { $, esc, raw, swapHTML, addHTML } from "./core/dom.js";
import { shared } from "./core/state.js";
import { api, oneLine, snack, viaServer } from "./core/server.js";
import { copied, store, VAULT_PATH } from "./core/page.js";

/** @typedef {{ok?: boolean, supported?: boolean, installed?: boolean, loaded?: boolean|null, on?: boolean, dev?: boolean, folder?: string}} AutoStatus */

export const AS = { /** @type {AutoStatus|null} */ status: null, confirm: /** @type {""|"on"|"off"} */ (""), busy: false, /** the boot read, so a test can wait for the late answer before it clicks */ ready: /** @type {Promise<void>|null} */ (null) };
export const AS_HELP_ID = "fix-a-stopped-server-and-other-problems";
export const ASKED_KEY = "creaite-autostart-asked";

/** The state from the server, or null when the server can't say (not running, or no such route yet). @param {boolean} [force] */
export async function asStatus(force) {
  if (!viaServer()) { AS.status = null; return null; }
  if (AS.status && !force) return AS.status;
  try { const r = await api("/api/autostart/status", {}); AS.status = r && r.ok && typeof r.on === "boolean" ? r : null; }
  catch (e) { AS.status = null; }
  return AS.status;
}
/** True when the switch can be used: a Mac, the live app and not the development copy. */
export const asUsable = () => !!(AS.status && AS.status.supported);
/** The first-run question is shown while it can be answered and hasn't been. */
export function asQuestionDue() {
  let asked = false; try { asked = !!store.get(ASKED_KEY, false); } catch (e) { /* no storage: ask again */ }
  return asUsable() && !AS.status?.on && !asked;
}
const asRemember = () => { try { store.set(ASKED_KEY, true); } catch (e) { /* kept for this visit only */ } };

/** Turn it on or off through the server; says the answer in words. @param {boolean} on @returns {Promise<boolean>} */
export async function asSet(on) {
  if (AS.busy) return false;
  AS.busy = true;
  try {
    const r = await api("/api/autostart/set", { on });
    snack(oneLine(r && r.message) || (r && r.ok ? (on ? "creaite will start when you sign in" : "creaite won't start when you sign in") : "That didn't change"));
    asRemember(); await asStatus(true); return !!(r && r.ok);
  } finally { AS.busy = false; }
}
/** The first-run answer: Yes turns it on; Not now is remembered and the Settings switch stays. @param {boolean} yes */
export async function asAnswer(yes) { if (yes) return asSet(true); asRemember(); return true; }

/** The user's own folder as a Terminal argument: quoted only when it needs it. */
export function asFolderArg() {
  const f = String((AS.status && AS.status.folder) || VAULT_PATH || "");
  return /^[A-Za-z0-9_@%+=:,./~-]+$/.test(f) ? f : `'${f.replace(/'/g, "'\\''")}'`;
}
/** The two Terminal commands, each a line to copy, with the real folder. @param {"install"|"remove"} what */
export const asCommand = what => `cd ${asFolderArg()}\nsystem/scripts/run launch.py agent ${what}`;

/** Settings: the switch, the asking-first line and the Terminal note. */
export function asCardHtml() {
  const off = !viaServer() || !asUsable() || AS.busy ? "disabled" : "", st = AS.status, on = !!(st && st.on);
  const state = !viaServer() ? '<span class="sub">Needs creaite running</span>'
    : !st ? '<span class="sub">Not available yet</span>'
    : !st.supported ? `<span class="sub">${st.dev ? "Not in the development copy" : "Only on a Mac"}</span>`
    : `<span class="${on ? "h-ok" : "sub"}" id="asState">${on ? "On" : "Off"}</span>`;
  const switchBtn = `<button type="button" class="btn" id="asSwitch" role="switch" aria-checked="${on}" aria-label="Start creaite when I sign in" ${off}>${on ? "Turn off…" : "Turn on…"}</button>`;
  const ask = AS.confirm ? `<div class="sushown" id="asConfirm" role="group" aria-label="Confirm">${AS.confirm === "on"
    ? "creaite will open by itself each time you sign in to this Mac, and open again if it ever crashes. Stop still keeps it stopped until the next sign-in."
    : "creaite will no longer open by itself when you sign in. The copy you are using now keeps running until you stop it; after that you open creaite from its launcher."}
    <span class="suacts" style="margin-top:6px"><button type="button" class="btn" data-ascancel>Cancel</button><button type="button" class="btn primary" id="asGo">${AS.confirm === "on" ? "Turn on" : "Turn off"}</button></span></div>` : "";
  return `<div class="card" id="asCard" data-sec="signin"><h2>Start creaite when I sign in</h2>
   <div class="srow"><div><span id="asLab">Start creaite when I sign in</span><small>Opens creaite in the background each time you sign in to this Mac. Stop still keeps it stopped until next time</small></div><div>${state} ${st && st.supported ? switchBtn : ""}</div></div>
   ${ask}
   <p class="sub" id="asTerm">Prefer Terminal? <a href="#help-howto-${AS_HELP_ID}" data-help="howto-${AS_HELP_ID}">Help › Fix a stopped server</a> has the commands, with your own folder filled in.</p></div>`;
}
/** Wire the card's buttons (called after it is drawn). @param {() => void} redraw */
export function asWire(redraw) {
  const b = (/** @type {string} */ id) => document.getElementById(id);
  if (b("asSwitch")) b("asSwitch").onclick = () => { AS.confirm = AS.status && AS.status.on ? "off" : "on"; redraw(); b("asGo")?.focus(); };
  document.querySelectorAll("[data-ascancel]").forEach(x => { /** @type {HTMLElement} */ (x).onclick = () => { AS.confirm = ""; redraw(); }; });
  if (b("asGo")) b("asGo").onclick = async () => { const on = AS.confirm === "on"; AS.confirm = ""; await asSet(on); redraw(); };
}

/** Help › Fix a stopped server: the note for Terminal users, with the user's own folder (help.js puts it where help.md says
    `[signin commands]`). The commands are built at run time by asCommand, never written in help.md. */
export function asHelpHtml() {
  const cmd = (/** @type {"install"|"remove"} */ what) => `<div class="sucmd"><code id="asCmd-${what}" style="white-space:pre">${esc(asCommand(what))}</code><button type="button" class="mini" data-ascopy="${what}">Copy</button></div>`;
  return `<div class="hp-signin" id="asHelp"><p><b>Start creaite when you sign in, from Terminal.</b> Open Terminal and paste the lines under the one you want. They use your own creaite folder. Settings › creaite and backups has the same switch.</p>
    <p class="sub">Turn it on</p>${cmd("install")}<p class="sub">Turn it off</p>${cmd("remove")}</div>`;
}

/** Today's Getting started: the one question. "" when it isn't due. */
export function asQuestionHtml() {
  return asQuestionDue() ? `<div class="tb" id="asQ"><span class="t">Start creaite automatically when you sign in?</span><p>creaite opens by itself after every restart. You can change this any time in Settings.</p>
    <span class="rmgo"><button type="button" class="btn primary" data-asq="yes">Yes</button> <button type="button" class="btn" data-asq="no">Not now</button></span></div>` : "";
}

/** The late answer touches only its own node: insert or remove #asQ in the setup list, never the list, Today or an open panel. */
export function asQuestionSync() {
  const box = $("#setupList"), cur = $("#asQ"), q = asQuestionDue();
  if (!box) return;
  if (q && !cur) addHTML(box, "beforeend", raw(asQuestionHtml()));
  else if (!q && cur) cur.remove();
}
/** Draw the Settings card again, in place. */
export function asRedraw() { const c = $("#asCard"); if (c) { swapHTML(c, raw(asCardHtml())); asWire(asRedraw); } }
/** Read the state, then draw whatever shows it: the Settings card and Today's question. */
export async function asRefresh() { await asStatus(true); if (shared.VIEW === "settings") asRedraw(); if (shared.VIEW === "today") asQuestionSync(); }

/** The start-up step: the first-run question's two buttons, and the first read of the state. */
export function bootAutostart() {
  document.addEventListener("click", async e => {
    const q = /** @type {HTMLElement|null} */ ((/** @type {HTMLElement} */ (e.target)).closest("[data-asq]")); if (!q) return;
    e.preventDefault(); const yes = q.dataset.asq === "yes";
    await asAnswer(yes); if (!yes) snack("Okay. Settings › creaite and backups has the switch if you change your mind");
    if (shared.VIEW === "today") asQuestionSync();
  });
  document.addEventListener("click", async e => {      /* Copy, in Help */
    const x = /** @type {HTMLElement|null} */ ((/** @type {HTMLElement} */ (e.target)).closest("[data-ascopy]")); if (!x) return;
    e.preventDefault(); const t = asCommand(/** @type {"install"|"remove"} */ (x.dataset.ascopy));
    try { await navigator.clipboard.writeText(t); copied(x); snack("Copied"); } catch (err) { prompt("Copy this:", t); }
  });
  if (viaServer()) AS.ready = asRefresh();
}
