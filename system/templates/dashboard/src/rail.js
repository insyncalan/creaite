// @ts-check
/* rail.js: the sidebar (BL-163, BL-191; BL-319 part 6). The items, the saved choice and the signals are in
   stores/rail.js; the sidebar is drawn by the components in components/sidebar/ (dev/COMPONENTS.md), mounted here into
   the shell's containers: the pages (#railMain), More
   (#railFoot) and Customise sidebar (#railCustBox, a modal dialog). Old code reaches the sidebar only through the store
   (setRailView, setRailCount), never its DOM.

   #156: three states (expanded 188px; collapsed with labels under the icons 76px; collapsed icons only 56px). The wordmark is the
   toggle (#railTog, in the shell: "creaite_" expanded, "c_" collapsed), as is ⌘\; the choice is this browser's (stores/rail.js).
   Labels when collapsed is dashboard.rail_labels (Settings › Essentials, More's menu, Customise sidebar).

   The choice is settings.json's dashboard.rail = {order, more, hidden, display}, written through writeSettings (a backup
   and a log line); a write that fails is put back. display "icons" is the collapsed sidebar, the 56px rail of icons; the
   toggle and ⌘\ (Ctrl+\) change it. A right-click on the sidebar (or Shift+F10 on a page in it), More's Customise
   sidebar… and Settings › General › Appearance open Customise. */
import { effect } from "@preact/signals";
import { h, render } from "preact";
import { CustomiseSidebar } from "./components/sidebar/CustomiseSidebar.jsx";
import { RailMore } from "./components/sidebar/RailMore.jsx";
import { RailNav } from "./components/sidebar/RailNav.jsx";
import { $, addHTML, html, ic, ICONS } from "./core/dom.js";
import { A, DEC, open, P, R } from "./core/data.js";
import { go } from "./core/nav.js";
import { MAC, S } from "./core/page.js";
import { writeSettings } from "./core/server.js";
import { shared } from "./core/state.js";
import { RAIL_DEF, RAIL_ITEMS, railCfg, railCollapsed, railCustOpen, railIconSize, railItem, railLabelled, railLabelsOn, railSizeNorm, railLoadUser, railMoreOpen, railNarrow, railNorm, railSetUser, railWide, setRailCount, setRailView } from "./stores/rail.js";
import { row, SETSECTIONS } from "./settings.js";
import { WTABS, workTabGo } from "./work.js";
import { healthCount } from "./stores/settings.js";

export { RAIL_DEF, RAIL_ITEMS, healthCount, railIconSize, railItem, railLabelsOn, railNorm, setRailCount };   /* the stores', on the page for the tests and ⌘K */

/** Where Customise was opened from: focus goes back there when it closes. */
export let RAILOPENER = /** @type {HTMLElement | null} */ (null);

/* every change is drawn at once and written to settings.json (a backup and a log line); if the write fails it is put back */
/** @param {any} cfg */
export async function railSave(cfg) {
  const was = railCfg.value; railCfg.value = railNorm(cfg); S.rail = railCfg.value;
  const ok = await writeSettings({ "dashboard.rail": railCfg.value });
  if (!ok) { railCfg.value = was; S.rail = was; }
  return ok;
}
/** Collapse or expand the sidebar (the wordmark, ⌘\\ and ⌘K), remembered in this browser. Under 900px it stays collapsed. */
export function railToggle() { if (!railNarrow.value) railSetUser(!railCollapsed.value); }
/** Labels when collapsed (More's switch, Customise sidebar and Settings › Essentials), saved to dashboard.rail_labels.
    @param {boolean} on */
export async function railSetLabels(on) {
  const was = railLabelsOn.value; railLabelsOn.value = on; S.railLabels = on;
  if (!await writeSettings({ "dashboard.rail_labels": on })) { railLabelsOn.value = was; S.railLabels = was; return false; }
  return true;
}
/** Icon size (Customise sidebar and Settings › Essentials), saved to dashboard.rail_icon_size (#182).
    @param {string} size */
export async function railSetIconSize(size) {
  const was = railIconSize.value, now = railSizeNorm(size); railIconSize.value = now; S.railIconSize = now;
  if (!await writeSettings({ "dashboard.rail_icon_size": now })) { railIconSize.value = was; S.railIconSize = was; return false; }
  return true;
}
/** Done in Customise sidebar: the lists and Icons only (display), then the labels setting. Turning Icons only on, or off, also
    collapses or expands the sidebar, as it did.
    @param {any} cfg @param {boolean} labels @param {string} [size] */
export async function railDone(cfg, labels, size) {
  const icons = cfg.display === "icons", was = railCfg.value.display === "icons";
  const ok = await railSave(cfg);
  if (ok && icons !== was && !railNarrow.value) railSetUser(icons);
  if (labels !== railLabelsOn.value) await railSetLabels(labels);
  if (size && size !== railIconSize.value) await railSetIconSize(size);
  return ok;
}
/** Open Customise sidebar; focus goes back to `opener` (or the current page's button) when it closes.
    @param {Element | null} [opener] */
export function railCustomise(opener) {
  railMoreOpen.value = false;
  RAILOPENER = /** @type {HTMLElement | null} */ (opener || document.querySelector('.rail button[aria-current="page"]') || $("#railMore"));
  railCustOpen.value = true;
}
/** ⌘K's "Customise the rail" (ask.js, Team 1's) calls this name: the same dialog. */
export const railPopOpen = railCustomise;
function railCustClosed() { railCustOpen.value = false; const o = RAILOPENER; RAILOPENER = null; if (o && o.isConnected && o.getClientRects().length) o.focus(); else $("#railMore")?.focus(); }
/** The current page's rail key, from the view (a project page is Projects, a person People, Help Settings). */
export function renderRail() {
  let cur = "";
  try { cur = { cockpit: "projects", mine: "work", help: "settings", person: "people", milestones: "projects", meeting: "today", reporting: "projects" }[shared.VIEW] || shared.VIEW; } catch (x) { /* VIEW not set yet */ }
  setRailView(cur);
}

/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootRail0007() {
  /* icons other screens draw with ic() (the panel's ⋯, drag handles, Move down), added here since BL-163 */
  Object.assign(ICONS, { grip: '<circle cx="9" cy="6" r="1"/><circle cx="15" cy="6" r="1"/><circle cx="9" cy="12" r="1"/><circle cx="15" cy="12" r="1"/><circle cx="9" cy="18" r="1"/><circle cx="15" cy="18" r="1"/>',
    arrowdown: '<path d="M12 5v14M19 12l-7 7-7-7"/>', more: '<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>' });
  Object.defineProperty(shared, "RAILCFG", { configurable: true, enumerable: true, get: () => railCfg.value, set: v => { railCfg.value = railNorm(v); } });
  railCfg.value = railNorm(S.rail);
  railLabelsOn.value = S.railLabels !== false; railIconSize.value = railSizeNorm(S.railIconSize); railLoadUser();
  const mq = matchMedia("(max-width:899px)"); railNarrow.value = mq.matches; mq.addEventListener("change", e => { railNarrow.value = e.matches; });
  const mw = matchMedia("(min-width:1200px)"); railWide.value = mw.matches; mw.addEventListener("change", e => { railWide.value = e.matches; });
  effect(() => {        /* #182: the icon size is a class on the page (CSS sets the icon box and the row heights) */
    const z = railIconSize.value, root = document.documentElement;
    root.classList.toggle("railsz-medium", z === "medium"); root.classList.toggle("railsz-large", z === "large");
  });
  effect(() => {        /* the shell follows the choice: the rail's width (--rail-w) and its look (collapsed, labels under the icons) */
    const c = railCollapsed.value, lab = railLabelled.value, nav = $(".rail");
    document.documentElement.classList.toggle("railicons", c);
    document.documentElement.classList.toggle("raillabels", lab);
    if (nav) { nav.classList.toggle("icons", c && !lab); nav.classList.toggle("collapsed", c); nav.classList.toggle("labelled", lab); }
  });
  const tog = /** @type {HTMLButtonElement | null} */ ($("#railTog"));
  if (tog) {          /* the wordmark is the toggle; its name says what it will do */
    effect(() => {
      const c = railCollapsed.value, what = c ? "Expand the rail" : "Collapse the rail";
      tog.setAttribute("aria-expanded", c ? "false" : "true"); tog.setAttribute("aria-label", what);
      tog.setAttribute("data-key", MAC ? "⌘\\" : "Ctrl+\\");
      tog.disabled = railNarrow.value;
    });
    tog.addEventListener("click", railToggle);
  }
  const onGo = (/** @type {string} */ id) => go(id);
  /* #139: Projects and Work open a list on hover (the active projects by name with their health, the Work lists with their open counts);
     a pick opens it, the icon alone still goes to the page */
  const flyouts = {
    projects: () => { const a = P.filter(p => p.active !== false && !p.archived);
      return a.length ? a.map(p => ({ id: p.code, name: p.name, health: p.health || "" })) : [{ id: "-", note: "No active projects" }]; },
    work: () => { const n = { actions: A.filter(open).length, raid: R.filter(open).length, decisions: DEC.filter(open).length };
      return WTABS.map(t => ({ id: t.id, name: t.label, count: t.id === "all" ? n.actions + n.raid + n.decisions : n[t.id] })); },
  };
  const onFly = (/** @type {string} */ id, /** @type {string} */ pick) => {
    if (id === "projects") go("cockpit", pick);
    else if (id === "work") { if (shared.VIEW !== "work") go("work"); if (shared.WT !== pick) workTabGo(pick); }
  };
  render(h(RailNav, { onGo, flyouts, onFly }), $("#railMain"));
  render(h(RailMore, { onGo, onCustomise: railCustomise, onLabels: railSetLabels, onHealth: () => go("settings", "health"), onHelp: () => go("help") }), $("#railFoot"));
  addHTML(document.body, "beforeend", html`<div id="railCustBox"></div>`);
  render(h(CustomiseSidebar, { onSave: railDone, onClose: railCustClosed }), $("#railCustBox"));
  document.addEventListener("click", e => { const t = /** @type {Element} */ (e.target); if (t.closest && t.closest("[data-railcust]")) railCustomise(t.closest("[data-railcust]")); });
  /* BL-191: a right-click anywhere on the sidebar (or the context-menu key, Shift+F10, on a focused page) opens Customise */
  document.addEventListener("contextmenu", e => { const t = /** @type {Element} */ (e.target); const nav = t.closest && t.closest(".rail"); if (!nav) return; e.preventDefault();
    const byKey = !e.clientX && !e.clientY, a = document.activeElement;
    railCustomise(t.closest(".rail button") || (byKey && a && a.closest && a.closest(".rail button")) || null); });
  /* ⌘\ (Ctrl+\ elsewhere) collapses or expands the sidebar, wherever focus is */
  document.addEventListener("keydown", e => { if ((e.metaKey || e.ctrlKey) && !e.altKey && !e.shiftKey && e.key === "\\") { e.preventDefault(); railToggle(); } });
  renderRail();
}
/* ===== BL-163 (sprint-rail) ===== Settings › General › Appearance: "Sidebar: Customise…" opens the same dialog as a right-click on the sidebar (BL-191) */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootRail0077() {
  const ap = SETSECTIONS.find(x => x.id === "appearance"), r0 = ap.render; ap.kw += " left rail sidebar navigation hide reorder order icons only titles customise collapse more";
  ap.render = () => r0() + row("Sidebar", `<button type="button" class="btn" id="railCustSet" data-railcust aria-haspopup="dialog">${ic("sliders")}Customise…</button>`, "Choose what is in the sidebar and what is in More, put them in your own order, or show icons only");
}
