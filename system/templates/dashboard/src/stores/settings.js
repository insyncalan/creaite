// @ts-check
/* stores/settings.js (BL-320, v1.9.2): Settings' catalogue and Health, as signals (dev/COMPONENTS.md §2).

   - catalogue: /api/settings/catalogue's answer (every setting: group, tier, label, line, reason, default, value, changed;
     the Essentials rows; the counts), or null until it is read. Reloaded after a save or a Reset.
   - query: the page's search text. settings.js sets it; the components
     filter their own rows by it (old code never writes into a mounted container).
   - health: /api/health's answer (problems, fine, stopped, checked), its busy flag and its error; healthCount is what the
     rail shows on Settings (BL-320 §4), kept with its time in this browser so a new page has it without a check.
   Saving is the page's own: writeSettings (a backup and a log line). After a save or a Reset each listener in SAVED is told
   the dotted keys and their new values, so settings.js can bring the page's copies (S, the VIP and draft settings) up to date. */
import { computed, effect, signal } from "@preact/signals";
import { store } from "../core/page.js";
import { api, writeSettings } from "../core/server.js";

/** @typedef {{key:string, tier:string, group:string, label:string, line:string, reason:string, default:any, value:any,
     changed:boolean, resettable:boolean, fixed_why:string, last_changed:(string|null)}} Setting */
/** @typedef {{section:string, label:string, line:string, keys:string[], changed:boolean}} EssentialRow */
/** @typedef {{settings:Setting[], essentials:EssentialRow[], groups:string[], changed:number, essentials_count:number,
     advanced_count:number, retire_candidates:number, retire_after_days:number}} Catalogue */
/** A problem's fix. A built one (health_fixes.py) also has its id, title, what it does, and its command or the page it opens.
    @typedef {{kind:string, button:string, would_run:string, waits_for:string, how:string, built:boolean, id?:string,
     title?:string, does?:string, command?:string, url?:string}} Fix */
/** @typedef {{id:string, title:string, check:string, severity:string, detail:string, fix:Fix}} Problem */
/** @typedef {{area:string, count:number, span:string, message:string}} Stopped */
/** @typedef {{problems:Problem[], fine:number, fine_names:string[], stopped:Stopped[], checked:string, standalone?:Fix[], archiving?:string[], backups?:string[]}} HealthResult */

/** @type {import("@preact/signals").Signal<Catalogue|null>} */
export const catalogue = signal(null);
export const catalogueError = signal("");
export const query = signal("");
/** @type {import("@preact/signals").Signal<HealthResult|null>} */
export const healthResult = signal(null);
export const healthBusy = signal(false);
export const healthError = signal("");
/** Fixes whose change is on the approval card, waiting for Alan (health_fixes.py `card: True`): not done until he approves.
    A row says so until a check no longer reports its problem. */
export const healthCardWaiting = signal(/** @type {string[]} */ ([]));
/** @param {string} id */
export const markCardWaiting = id => { if (id && !healthCardWaiting.value.includes(id)) healthCardWaiting.value = [...healthCardWaiting.value, id]; };
const COUNT_KEY = "creaite-health-count";
/** The count the rail shows: the last check's problems, from this page or (until it checks) the last one in this browser. */
export const healthCount = signal(0);
export const healthCheckedAt = computed(() => healthResult.value ? healthResult.value.checked : "");

/** @type {((changes: Record<string, any>) => void)[]} */
export const SAVED = [];
const told = (/** @type {Record<string, any>} */ changes) => SAVED.forEach(f => { try { f(changes); } catch (e) { /* one listener's fault never stops a save */ } });

/** The catalogue's entry for a dotted key. @param {string} key @returns {Setting|undefined} */
export const settingOf = key => catalogue.value ? catalogue.value.settings.find(s => s.key === key) : undefined;

let loading = null;
/** Read the catalogue from the live server (one at a time; a call while one runs shares it). */
export function loadCatalogue() {
  if (loading) return loading;
  loading = (async () => {
    const r = await api("/api/settings/catalogue", {});
    if (r.ok) { catalogue.value = /** @type {Catalogue} */ (r); catalogueError.value = ""; }
    else catalogueError.value = r.message || "Couldn't read the settings";
    loading = null;
    return !!r.ok;
  })();
  return loading;
}

/** Save {dotted key: value} through writeSettings, then tell the listeners and reread the catalogue.
    @param {Record<string, any>} changes @returns {Promise<boolean>} */
export async function saveSettings(changes) {
  if (!await writeSettings(changes)) return false;
  told(changes);
  await loadCatalogue();
  return true;
}

/** Put settings back to their defaults (/api/settings/reset): {ok, message, reset}. The answer's catalogue replaces ours.
    @param {string[]} keys */
export async function resetSettings(keys) {
  const r = await api("/api/settings/reset", keys.length === 1 ? { key: keys[0] } : { keys });
  if (!r.ok) return { ok: false, message: r.message || "Couldn't reset it", reset: [] };
  if (r.catalogue) catalogue.value = r.catalogue;
  const vals = {};
  for (const k of r.reset || []) { const s = settingOf(k); if (s) vals[k] = s.value; }
  if (Object.keys(vals).length) told(vals);
  return { ok: true, message: "", reset: r.reset || [] };
}

/** Run the health check (/api/health, doctor read only; a few seconds). One at a time. */
export async function checkHealth() {
  if (healthBusy.value) return;
  healthBusy.value = true; healthError.value = "";
  try {
    const r = await api("/api/health", {});
    if (r.ok) {
      healthResult.value = /** @type {HealthResult} */ (r);
      healthCount.value = (r.problems || []).length;
      const still = (r.problems || []).map((/** @type {Problem} */ p) => p.fix && p.fix.id);   /* a card fix stops waiting once its problem is gone */
      healthCardWaiting.value = healthCardWaiting.value.filter(id => still.includes(id));
      store.set(COUNT_KEY, { n: healthCount.value, at: Date.now() });
    } else healthError.value = r.message || "The health check didn't run";
  } finally { healthBusy.value = false; }
}

/** When this browser last checked (ms), or 0. */
export const lastCheckAt = () => { const c = store.get(COUNT_KEY, null); return c && typeof c.at === "number" ? c.at : 0; };

/* ===== The rail's count on Settings (BL-320 §4): the hook =====
   v192-sidebar's setRailCount (stores/rail.js) isn't on this branch's base. When both are merged, the body of showHealthCount
   becomes:  setRailCount("settings", n, `${n} to fix in Settings › Health`)
   Nothing else changes: the effect below calls it whenever the count changes. */
/** @param {number} n */
export function showHealthCount(n) { void n; }

/** At start-up (settings.js calls it): the last count this browser saw, and the rail kept in step with it from then on. */
export function startSettingsStore() {
  const c = store.get(COUNT_KEY, null);
  if (c && typeof c.n === "number") healthCount.value = c.n;
  effect(() => showHealthCount(healthCount.value));
}

/* ===== #132: Settings › Essentials › AI models =====
   aiState is /api/ai/state's answer (providers.py): the provider cards, the four kinds of job with their model lists, the
   limit, and the fixed rules' words; null until it is read. Every change goes through its own /api/ai/… route, which saves
   with a backup and a log line and answers the new state. A key is sent only to /api/ai/test and is never kept here. */
/** @typedef {{id:string, name:string, blurb:string, billing:string, how:string[], status:string, auth:(string|null),
     models:string[], found:{id:string, label:string, offered:boolean}[]}} AiProvider */
/** @typedef {{id:string, label:string, recommended:boolean, weaker:boolean, accepted:boolean}} AiOption */
/** @typedef {{id:string, name:string, line:string, needs:string[], tools:boolean, features:string[], warn:string,
     recommended:string, recommended_label:string, value:string, options:AiOption[], tools_only:boolean}} AiJob */
/** @typedef {{id:string, label:string, line:string, enabled:boolean}} AiLimit */
/** @typedef {{providers:AiProvider[], line:string, jobs:AiJob[], more_hint:boolean, how:string[], rules:string[],
     key_warning:string, built:boolean, on_limit:string, limits:AiLimit[]}} AiState */
/** @type {import("@preact/signals").Signal<AiState|null>} */
export const aiState = signal(null);
export const aiError = signal("");

/** Read the AI models section from the live server. */
export async function loadAi() {
  const r = await api("/api/ai/state", {});
  if (r.ok && r.providers) { aiState.value = /** @type {AiState} */ (r); aiError.value = ""; }
  else aiError.value = r.message || "Couldn't read the AI models";
  return !!r.ok;
}

/** One AI models change: the route's answer, and the new state when it sends one (the dots and Reset follow the catalogue).
    @param {string} path @param {Record<string, any>} body */
export async function aiCall(path, body) {
  const r = await api(path, body);
  if (r.providers) { aiState.value = /** @type {AiState} */ (r); if (catalogue.value) loadCatalogue(); }
  return r;
}
