// @ts-check
/* ===== BL-322 (v193-sneak-peek-ui) ===== Sneak peek: change the item open in the peek in words (dev/mockups/sneak-peek-mockup.html;
   the server contract is dev/sprints/BL-322-contract.md). It opens over the bottom of the work-item peek (an action, a RAID item or a
   decision in #panel) or the milestone editor (#mvPeek), never for a proposal or a new item:
   - `//` outside a field (one `/` still does what it always did: creaite waits about a third of a second for a second slash, then
     replays the first, so ask creaite, or the page's own search, opens as before); never inside a field;
   - the sparkle in the peek's top bar, immediately left of Draft chase (#pkSneakBtn; in the milestone editor, before Close);
   - the quiet "// Change this item in words" line at the foot of the peek.
   Esc closes it and focus goes back where it was. The box is a Preact component (components/peek/SneakPeek.jsx); this module puts
   it in place, keeps the peek scrolled so nothing hides behind it (the scroll area's bottom padding follows the box's height), and
   gives it the peek's own save path: one dashboard proposal with the peek's envelope (`peek` meta, so the staged pill and the feed
   show it), applied at once (BL-306), Undo straight after through /api/undo. Nothing is sent from here. */
import { closeChat, openChat } from "./ask.js";
import { SNEAK_CMD, SNEAK_ICON, mountSneak, unmountSneak } from "./components/peek/SneakPeek.jsx";
import { peopleAll } from "./core/data.js";
import { $, addHTML, html, ibtn, ICONS, raw } from "./core/dom.js";
import { CMDENTER } from "./core/fields.js";
import { typing } from "./core/keys.js";
import { go } from "./core/nav.js";
import { nowStamp } from "./core/page.js";
import { api, applyNow, needVault, oneLine, reloadData, snack, stampFull, viaServer, vq } from "./core/server.js";
import { shared } from "./core/state.js";
import { DRAFTKIND, pkOn } from "./projects.js";
import { mvRedraw } from "./milestones.js";
import { msFind, openMilestone } from "./milestones.js";
import { chaseIsOpen, chaseOpen, curObj, pkCid, PKDRAW, pkDraw, pkFile, PKK, pkPersist, pkReconcile, REC } from "./panel.js";

/** @typedef {{where: "peek"|"ms", id: string, k: string}} SneakAt */
/** where the box is open: its host, the item, and what had focus before it opened @type {{at: SneakAt|null, opener: Element|null, ro: ResizeObserver|null}} */
export const SNK = { at: null, opener: null, ro: null };
/** the fields just changed, highlighted for a moment after a change or an undo (the mockup's flash) @type {{sel: string[], until: number}|null} */
let FLASH = null, FLASHT = 0;
const FLASH_MS = 1600;
/** Where each tracker column shows, in the peek and in the milestone editor; a column not listed shows under Details. @type {Record<string, string>} */
const FLASH_PEEK = { owner: '[data-pkp="o"],[data-pkp="by"]', made_by: '[data-pkp="o"],[data-pkp="by"]', due_date: '[data-pkp="due"]',
  needed_by: '[data-pkp="due"]', date: '[data-pkp="date"]', priority: '[data-pkp="pr"]', impact: '[data-pkp="imp"]', likelihood: '[data-pkp="lik"]',
  status: '[data-pkp="st"]', type: "#pkId .pk-type", description: "#pkTitle", decision: "#pkTitle", latest_update: "#pkDesc",
  response_action: "#pkDesc", reasoning: "#pkDesc" };
/** @type {Record<string, string>} */
const FLASH_MS_ED = { forecast_date: "#mvFc", owner: "#mvOwner", name: "#mvName", state: "#mvPeek .mv-stopts", state_reason: "#mvPeek .mv-stopts",
  status: "#mvPeek .mv-stopts", description: "#mvDesc", client_visible: "#mvCli", client_message: "#mvCw" };
/** Highlight the changed fields of the open item for a moment (static under reduced motion: style.css's one reduced-motion rule).
    @param {SneakAt} at @param {string[]} fields the tracker columns */
export function sneakFlash(at, fields) {
  const map = at.where === "ms" ? FLASH_MS_ED : FLASH_PEEK, other = at.where === "ms" ? "#mvPeek .mv-dchips" : "#pkDetT";
  const sel = [...new Set(fields.map(f => map[f] || other))];
  if (!sel.length) return;
  FLASH = { sel, until: Date.now() + FLASH_MS }; flashPaint();
  clearTimeout(FLASHT);
  FLASHT = /** @type {any} */ (setTimeout(() => { FLASH = null; document.querySelectorAll(".sp-flash").forEach(e => e.classList.remove("sp-flash")); }, FLASH_MS));
}
/** put the highlight back on what a redraw replaced */
function flashPaint() { if (!FLASH || Date.now() > FLASH.until) return; for (const q of FLASH.sel) document.querySelectorAll(q).forEach(e => e.classList.add("sp-flash")); }
/** the open item's columns a stage changes (a RAID impact or likelihood also changes its priority)
    @param {{items: Record<string, any>[]}} stage @param {string} id @returns {string[]} */
export function stageFields(stage, id) {
  /** @type {string[]} */
  const out = []; for (const it of stage.items) if (it.op === "update" && it.id === id) out.push(...Object.keys(it.changes || {}));
  if (out.includes("impact") || out.includes("likelihood")) out.push("priority");
  return out;
}
const SLASH_WAIT = 330;        // ms: a second slash within this opens Sneak peek; otherwise the first does what it always did
let slashT = 0, replaying = false;

/** The item Sneak peek would work on now, or null (no peek, a proposal, a new item, Draft chase open, a new milestone).
    @returns {SneakAt|null} */
export function sneakWhere() {
  if (pkOn() && shared.CUR && shared.CUR.mode === "record" && PKK.includes(shared.CUR.k) && !chaseIsOpen()) return { where: "peek", id: shared.CUR.id, k: shared.CUR.k };
  const mp = $("#mvPeek");
  if (mp && !mp.hidden && shared.MV && shared.MV.peek && !shared.MV.add) return { where: "ms", id: shared.MV.peek, k: "milestones" };
  return null;
}
export const sneakIsOpen = () => !!SNK.at;
/** the host the box is drawn in, and the scroll area it floats over @param {"peek"|"ms"} w */
const hostOf = w => w === "ms" ? $("#mvSneak") : $("#pkSneak");
const hintOf = w => w === "ms" ? $("#mvSneakHint") : $("#pkSneakHint");
const scrollOf = w => w === "ms" ? $("#mvPeek .mv-pkbody") : $("#pkScroll");
const frameOf = w => w === "ms" ? $("#mvPeek") : $("#panel");

/** Open the box over the item now in the peek (the sparkle, the foot line or //). */
export function sneakOpen() {
  const at = sneakWhere(); if (!at) return;
  if (SNK.at && SNK.at.id === at.id && SNK.at.where === at.where) { $("#spIn")?.focus(); return; }
  if (SNK.at) sneakClose(false);
  const host = hostOf(at.where), frame = frameOf(at.where); if (!host || !frame) return;
  SNK.at = at; SNK.opener = document.activeElement;
  frame.classList.add("sp-open"); host.hidden = false; const hint = hintOf(at.where); if (hint) hint.hidden = true;
  for (const b of [$("#pkSneakBtn"), $("#mvSneakBtn")]) if (b) b.setAttribute("aria-pressed", String(at.where === (b.id === "mvSneakBtn" ? "ms" : "peek")));
  mountSneak(host, at.id, back => sneakClose(back), acts(at));
  const box = host.firstElementChild, sc = scrollOf(at.where);
  if (box && sc && typeof ResizeObserver !== "undefined") {
    SNK.ro = new ResizeObserver(() => { const h = /** @type {HTMLElement} */ (box).offsetHeight; /** @type {HTMLElement} */ (sc).style.setProperty("--sp-h", `${h + 24}px`); });
    SNK.ro.observe(box);
  }
}
/** Close it. @param {boolean} back put the focus back where it was */
export function sneakClose(back) {
  const at = SNK.at; if (!at) return;
  SNK.at = null; if (SNK.ro) { SNK.ro.disconnect(); SNK.ro = null; }
  const host = hostOf(at.where); if (host) { unmountSneak(host); host.hidden = true; }
  const hint = hintOf(at.where); if (hint) hint.hidden = !sneakWhere();
  frameOf(at.where)?.classList.remove("sp-open"); /** @type {HTMLElement|null} */ (scrollOf(at.where))?.style.removeProperty("--sp-h");
  for (const b of [$("#pkSneakBtn"), $("#mvSneakBtn")]) if (b) b.setAttribute("aria-pressed", "false");
  if (back) { const o = /** @type {HTMLElement|null} */ (SNK.opener); const f = o && o.isConnected && !o.closest(".sp-box") ? o : at.where === "ms" ? $("#mvSneakBtn") : $("#pkSneakBtn"); /** @type {HTMLElement|null} */ (f)?.focus(); }
  SNK.opener = null;
}

/** The box's actions on the page: the peek's save path, Undo, Draft chase, going somewhere, asking creaite.
    @param {SneakAt} at @returns {import("./components/peek/SneakPeek.jsx").SneakActs} */
function acts(at) {
  return {
    commit: (stage, item, o) => sneakCommit(at, stage, item, o),
    undo: async applyId => { if (!viaServer()) return { ok: false, message: "Undo needs the live server." };
      const u = await api("/api/undo", { apply_id: applyId }); await reloadData(); afterChange(at); if (u.ok) sneakFlash(at, LASTF);
      return { ok: !!u.ok, message: u.ok ? "" : oneLine(u.message) || "Couldn't undo it: undo it in Activity." }; },
    chase: pane => { const start = {};
      if (pane && pane.tone != null) start.tone = pane.tone; if (pane && pane.to) start.to = pane.to;
      sneakClose(false); if (at.where !== "peek") { snack("Draft chase opens from an action, a risk or issue, or a decision"); return; } chaseOpen(start); },
    go: (task, item) => sneakGo(at, task, item),
    point: (to, text) => {
      if (to === "draft_chase") { sneakClose(false); if (at.where === "peek") chaseOpen(); else snack("Draft chase opens from an action, a risk or issue, or a decision"); return; }
      if (to === "ask") { sneakAsk(at, text); return; }
      sneakClose(false);
      if (to === "project_page") { const p = projectOf(at); if (p) go("cockpit", p); return; }
      if (to === "settings") { go("settings"); return; }
      if (to === "people") { go("settings", "people"); } },
    ask: text => sneakAsk(at, text),
    people: () => sneakPeople(),
    current: field => { if (at.where !== "peek") return ""; const x = REC(at.k, at.id) || {};
      const f = { client_message: at.k === "decisions" ? "cmd" : "cm", reasoning: "why", options: "opts", latest_update: "upd" }[field] || field;
      return String(x[f] ?? ""); },
  };
}
/** The people register for the @ list (name, organisation, aliases), hidden people left out; then anyone else who owns an item.
    Nobody is labelled a VIP (BL-288). @returns {{name: string, org: string, aliases: string[]}[]} */
export function sneakPeople() {
  const reg = (shared.REG || []).filter((/** @type {any} */ p) => p && p.name && !p.hidden)
    .map((/** @type {any} */ p) => ({ name: String(p.name), org: String(p.org || ""), aliases: /** @type {string[]} */ (p.aliases || []) }));
  const have = new Set(reg.map(p => p.name));
  return [...reg, ...peopleAll().filter(n => !have.has(n)).map(n => ({ name: n, org: "", aliases: /** @type {string[]} */ ([]) }))];
}
/** @param {SneakAt} at */
function projectOf(at) { if (at.where === "peek") { const x = REC(at.k, at.id); return x ? x.p : ""; } const f = msFind(at.id); return f.p ? f.p.code : ""; }
/** ask creaite, with the item attached (its ID and words first, as the peek's More does) @param {SneakAt} at @param {string} text */
function sneakAsk(at, text) {
  const x = at.where === "peek" ? REC(at.k, at.id) : null, t = x ? x.t : ((msFind(at.id).m || [])[0] || "");
  sneakClose(false); openChat();
  setTimeout(() => { const c = /** @type {HTMLTextAreaElement|null} */ ($("#chIn")); if (c && !c.value.trim()) { c.value = `About ${at.id}${t ? ` (${t})` : ""}: ${text || ""}`; c.dispatchEvent(new Event("input", { bubbles: true })); c.focus(); } }, 60);
}
/** Go somewhere: the source, the milestone, the project, or ask creaite. @param {SneakAt} at @param {Record<string, any>} task
    @param {import("./components/peek/SneakPeek.jsx").SneakItem} item */
async function sneakGo(at, task, item) {
  if (task.target === "ask") { sneakAsk(at, ""); return; }
  if (task.target === "source") {
    if (task.path) { if (!viaServer()) { snack("Opening a file needs the live server"); return; } const o = await api("/api/open", { path: task.path }); snack(o.ok ? "Opened in its own app" : oneLine(o.message) || "Couldn't open it"); return; }
    snack(task.ref ? `The source: ${task.ref}` : "This item's source names no file"); return; }
  sneakClose(false);
  if (task.target === "milestone" && task.ref) { openMilestone(task.ref); return; }
  if (task.target === "project") go("cockpit", task.ref || item.project || projectOf(at));
}

/** Make a change: the read route's staged items as one dashboard proposal with the peek's envelope (pkWrite's), applied at once.
    @param {SneakAt} at @param {{label: string, items: Record<string, any>[]}} stage @param {{id: string, table: string}} item
    @param {{by: string, said: string}} o @returns {Promise<{ok: boolean, message?: string, applyId?: any}>} */
export async function sneakCommit(at, stage, item, o) {
  if (!viaServer()) return { ok: false, message: "Sneak peek needs the live server: start it, then try again." };
  if (!await needVault()) return { ok: false, message: "Not saved: the vault isn't connected." };
  const k = at.where === "ms" ? "milestones" : at.k;
  const meta = { k, id: item.id, patch: {}, prev: {}, label: stage.label, from: "", to: o.said || "", at: nowStamp(), note: "Sneak peek", type: "act", ms: Date.now() };
  let name;
  try {
    name = await vq(async () => { let n = pkFile(); while (await shared.VW.exists("system/staging/" + n)) n = pkFile();
      const data = { created: stampFull().replace(" ", "T"), source_run: "dashboard", files: [], peek: meta,
        items: stage.items.map((it, j) => Object.assign({ n: j + 1, match: "strong", flags: [], decision: "approved" }, it)) };
      await shared.VW.write("system/staging/" + n, JSON.stringify(data, null, 2) + "\n"); return n; });
  } catch (e) { return { ok: false, message: "Not saved: " + /** @type {Error} */ (e).message }; }
  shared.PKS.push({ name, ...meta }); pkPersist();
  const r = await applyNow({ peek: true }); await pkReconcile(); afterChange(at);
  if (r.ok) { LASTF = stageFields(stage, item.id); sneakFlash(at, LASTF); }
  if (!r.ok) return { ok: false, message: `Staged, but the apply stopped: ${oneLine(r.message)}. It is in the staged list.` };
  return { ok: true, applyId: r.apply_id };
}
/** the item redrawn after a change or an undo @param {SneakAt} at */
/** the fields the last change touched, for Undo's highlight @type {string[]} */
let LASTF = [];
/** @param {SneakAt} at */
function afterChange(at) { if (at.where === "ms") mvRedraw(); else if (pkOn() && shared.CUR && curObj()) pkDraw(); }

/** The milestone editor redraws itself whole (mvEdDraw): put the sparkle in its bar, and the foot line and the box's host (kept,
    so an open box survives the redraw) back at its foot. Called by mvEdDraw after it draws. @param {HTMLElement} p */
export function sneakMvAttach(p) {
  if (!p || shared.MV.add) return;
  let host = /** @type {HTMLElement|null} */ (SNK_MV.host), hint = SNK_MV.hint;
  if (!host) { const d = document.createElement("div"); d.id = "mvSneak"; d.className = "sp-host"; d.hidden = true; host = SNK_MV.host = d; }
  if (!hint) { const d = document.createElement("div"); d.className = "sp-hint"; d.id = "mvSneakHint"; hint = SNK_MV.hint = d; addHTML(d, "beforeend", hintHtml("mvSneakHintBtn")); }
  p.appendChild(hint); p.appendChild(host); hint.hidden = !!SNK.at && SNK.at.where === "ms"; flashPaint();
  const bar = p.querySelector(".mv-pkbar"), close = bar && bar.querySelector('[data-mvpk="close"]');
  if (bar && close && !bar.querySelector("#mvSneakBtn")) addHTML(close, "beforebegin", raw(sparkBtn("mvSneakBtn", "mv-ib")));
  const b = $("#mvSneakBtn"); if (b) b.setAttribute("aria-pressed", String(!!SNK.at && SNK.at.where === "ms"));
  if (SNK.at && SNK.at.where === "ms" && SNK.at.id !== shared.MV.peek) sneakClose(false);
  if (SNK.at && SNK.at.where === "ms") { const sc = /** @type {HTMLElement|null} */ ($("#mvPeek .mv-pkbody")), bx = /** @type {HTMLElement|null} */ (host.firstElementChild); if (sc && bx) sc.style.setProperty("--sp-h", `${bx.offsetHeight + 24}px`); if (SNK.ro && bx) SNK.ro.observe(bx); }
}
/** @type {{host: HTMLElement|null, hint: HTMLElement|null}} */
const SNK_MV = { host: null, hint: null };
/** the sparkle button @param {string} id @param {string} cls */
const sparkBtn = (id, cls) => ibtn("sneak", "Sneak peek: change this item in words", `id="${id}" aria-pressed="false"`, cls, "//");
/** the foot line @param {string} id */
const hintHtml = id => html`<button type="button" class="sp-hintbtn" id="${id}"><kbd>/</kbd><kbd>/</kbd> Change this item in words</button>`;

/** the peek redrawn: the sparkle and the foot line only for an item it works on; another item closes the box
    @param {any} _x @param {string} _k @param {boolean} fresh */
function sneakDraw(_x, _k, fresh) {
  flashPaint();
  const item = !!shared.CUR && shared.CUR.mode === "record" && PKK.includes(shared.CUR.k), on = item && !chaseIsOpen();   /* drawn before the peek is "on" */
  const b = $("#pkSneakBtn"), h = $("#pkSneakHint");
  if (b) b.hidden = !item;
  if (h) h.hidden = !on || (!!SNK.at && SNK.at.where === "peek");
  if (SNK.at && SNK.at.where === "peek" && (fresh || !on || SNK.at.id !== pkCid())) sneakClose(false);
}

/* BL-231: what this block did at load, run in today's order by src/main.js (after the Draft chase's block) */
export function bootSneak() {
  ICONS.sneak = SNEAK_ICON.map(([, a]) => `<path d="${a.d}"/>`).join("");
  Object.assign(DRAFTKIND, { "sneak-update": "update" });     /* the contract's new draft kind, under Draft the latest update's switch */
  const anchor = $("#pkChaseBtn") || $("#pkLink");
  addHTML(/** @type {Element} */ (anchor), "beforebegin", raw(sparkBtn("pkSneakBtn", "")));
  $("#pkSneakBtn").hidden = true;
  const after = $("#pkChase") || $("#pkScroll");
  addHTML(/** @type {Element} */ (after), "afterend", html`<div class="sp-hint" id="pkSneakHint" hidden>${hintHtml("pkSneakHintBtn")}</div><div class="sp-host" id="pkSneak" hidden></div>`);
  PKDRAW.push(sneakDraw);
  document.addEventListener("click", e => {
    const t = /** @type {Element} */ (e.target); if (!t || !t.closest) return;
    if (SNK.at && t.closest("#pkChaseBtn")) sneakClose(false);       /* Draft chase takes the item's place: the box goes */
    const b = t.closest("#pkSneakBtn,#mvSneakBtn,#pkSneakHintBtn,#mvSneakHintBtn"); if (!b) return;
    e.preventDefault(); e.stopPropagation();
    if ((b.id === "pkSneakBtn" || b.id === "mvSneakBtn") && SNK.at) { sneakClose(true); return; }
    if (chaseIsOpen() && b.id === "pkSneakBtn") { $("#pkChaseBtn")?.click(); }
    sneakOpen();
  }, true);
  /* `//` opens it; one `/` waits a third of a second and then does what it always did (replayed, so every page's own `/` works) */
  window.addEventListener("keydown", e => {
    if (replaying || e.key !== "/" || e.metaKey || e.ctrlKey || e.altKey || e.repeat || typing()) return;
    if (document.querySelector("dialog[open]") || !sneakWhere()) return;
    const a = document.activeElement; if (a && a.closest && a.closest("#chat,.pkpop,.bmenu,.cal,.combo")) return;
    e.preventDefault(); e.stopImmediatePropagation();
    if (slashT) { clearTimeout(slashT); slashT = 0; if ($("#chat").classList.contains("on")) closeChat(); sneakOpen(); return; }
    slashT = /** @type {any} */ (setTimeout(() => { slashT = 0; replaying = true;
      try { document.dispatchEvent(new KeyboardEvent("keydown", { key: "/", code: "Slash", bubbles: true, cancelable: true })); } finally { replaying = false; } }, SLASH_WAIT));
  }, true);
  /* ⌘⏎ in the box is the box's own (the confirm list), before the peek's and the milestone editor's ⌘⏎ */
  CMDENTER.unshift({ name: "sneak", when: t => !!(t && t.closest && t.closest(".sp-box")), save: () => { if (SNEAK_CMD.fn) SNEAK_CMD.fn(); } });
}
/* ===== end BL-322 ===== */
