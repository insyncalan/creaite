// @ts-check
/* MoreSettings (BL-320, v1.9.2): Advanced's catalogue list. Every setting that is neither an Essential nor already on one of
   Advanced's own cards (`covered`, from settings.js), grouped as the catalogue groups them, each with its label, one line,
   its default and why, the "changed" dot and Reset. A setting changed only at set-up (folders, the port…) shows its value
   and why it is fixed, with no control. Development-only settings, when any exist, are their own group, Developer, last.
   Saved with writeSettings (a backup and a log line); the page's search (label, line, reason or the old key) narrows the
   rows. */
import { useRef, useState } from "preact/hooks";
import { snack } from "../../core/server.js";
import { railSizeNorm } from "../../stores/rail.js";
import { catalogue, query, saveSettings } from "../../stores/settings.js";
import { settingHasAll, settingWords } from "./Essentials.jsx";
import { rowId, SettingRow } from "./SettingRow.jsx";

/* Limits and shapes the generic controls can't guess (the old Advanced card's, BL-206 and BL-208). */
const LIMITS = { "assistant.run_timeout_minutes": [1, 240], "assistant.long_chat_turns": [5, 500], "logging.max_mb": [1, 500], "logging.keep_days": [1, 90],
  "search.debounce_ms": [0, 2000], "search.ask_budget_chars": [1000, 200000], "review.spot_check_every": [0, 100],
  "logging.repeat_window_hours": [1, 168], "live_mode.health_check_seconds": [5, 3600],
  "ai_budget.weekly_dollars": [1, 10000], "ai_budget.weekly_tokens": [100000, 10000000000] };    /* #334 */
const CHOICES = { "dashboard.generate_days": [7, 14, 30], "logging.level": ["info", "debug"],
  "ai_budget.unit": ["dollars", "tokens"], "ai_budget.at_limit": ["confirm", "stop"],      /* #334 */
  "dashboard.rail_icon_size": ["small", "medium", "large"] };   /* #182 */

/** A value as words. @param {any} v */
export function settingShown(v) {
  if (v === null || v === undefined || v === "") return "none";
  if (typeof v === "boolean") return v ? "on" : "off";
  if (Array.isArray(v)) return v.length ? (v.every(x => typeof x !== "object") ? v.join(", ") : `${v.length} entries`) : "none";
  if (typeof v === "object") { const n = Object.keys(v).length; return n ? `${n} entries` : "none"; }
  return String(v);
}

/** @typedef {{s: import("../../stores/settings.js").Setting}} OneProps */

/** One catalogue setting with a control fitting its default's type. @param {OneProps} props */
function One({ s }) {
  const [id] = useState(rowId);
  const [saved, setSaved] = useState(false);
  const t = useRef(0);
  const named = { "aria-labelledby": id, "aria-describedby": id + "h" };
  const save = async (/** @type {any} */ nv, /** @type {()=>void} */ undo) => {
    if (!await saveSettings({ [s.key]: nv })) { undo(); return; }
    setSaved(true); clearTimeout(t.current); t.current = window.setTimeout(() => setSaved(false), 2500);
  };
  const d = s.default, v = s.value;
  let control = null;
  if (!s.resettable) control = <code class="setval">{settingShown(v)}</code>;
  else if (CHOICES[s.key]) {
    control = (
      <select {...named} value={s.key === "dashboard.rail_icon_size" ? railSizeNorm(v) : String(v)} onChange={e => { const el = /** @type {HTMLSelectElement} */ (e.currentTarget);
        const nv = typeof d === "number" ? Number(el.value) : el.value; save(nv, () => { el.value = String(v); }); }}>
        {CHOICES[s.key].map(o => <option value={String(o)}>{s.key === "dashboard.rail_icon_size" ? String(o).replace(/^./, c => c.toUpperCase()) : String(o)}</option>)}
      </select>
    );
  } else if (typeof d === "boolean") {
    control = <input type="checkbox" class="switch" {...named} checked={!!v}
      onChange={e => { const el = /** @type {HTMLInputElement} */ (e.currentTarget); save(el.checked, () => { el.checked = !!v; }); }} />;
  } else if (typeof d === "number") {
    const [lo, hi] = LIMITS[s.key] || [0, Infinity], whole = Number.isInteger(d);
    control = <input type="number" {...named} value={v ?? ""} min={lo} max={hi === Infinity ? undefined : hi} step={whole ? 1 : "any"} style="width:100px"
      onChange={e => { const el = /** @type {HTMLInputElement} */ (e.currentTarget), n = Number(el.value);
        if (el.value.trim() === "" || !Number.isFinite(n) || (whole && !Number.isInteger(n)) || n < lo || n > hi) {
          snack(hi === Infinity ? `Use a ${whole ? "whole " : ""}number, ${lo} or more` : `Use a ${whole ? "whole " : ""}number from ${lo} to ${hi}`); el.value = String(v ?? ""); return; }
        save(n, () => { el.value = String(v ?? ""); }); }} />;
  } else if (s.key === "inbox.meetings_from") {
    control = <input type="text" {...named} value={String(v ?? "")} size={8}
      onChange={e => { const el = /** @type {HTMLInputElement} */ (e.currentTarget), x = el.value.trim().toLowerCase();
        const nv = x === "monday" ? "monday" : /^\d+$/.test(x) && Number(x) <= 366 ? Number(x) : null;
        if (nv === null) { snack("Use “monday” or a number of days (up to 366)"); el.value = String(v ?? ""); return; }
        save(nv, () => { el.value = String(v ?? ""); }); }} />;
  } else if (typeof d === "string" || d === null) {
    control = <input type="text" {...named} value={v ?? ""} size={14}
      onChange={e => { const el = /** @type {HTMLInputElement} */ (e.currentTarget); save(el.value.trim(), () => { el.value = v ?? ""; }); }} />;
  } else if (Array.isArray(d) && (Array.isArray(v) ? v : d).every(x => typeof x === "string")) {
    control = <input type="text" {...named} value={(Array.isArray(v) ? v : []).join(", ")} size={18} placeholder="Comma-separated"
      onChange={e => { const el = /** @type {HTMLInputElement} */ (e.currentTarget); save(el.value.split(",").map(x => x.trim()).filter(Boolean), () => { el.value = (Array.isArray(v) ? v : []).join(", "); }); }} />;
  } else control = <span class="sub setval">{settingShown(v)}</span>;
  return (
    <SettingRow id={id} label={s.label} line={s.line} note={`Default: ${settingShown(d)}. ${s.reason}`} changed={s.changed} keys={[s.key]}
      resettable={s.resettable} fixedWhy={s.fixed_why} saved={saved}>
      {control}
    </SettingRow>
  );
}

/** @typedef {{covered:(key:string)=>boolean, tab?:string, groups?:string[], skip?:string[], bare?:boolean, all?:boolean}} MoreSettingsProps
    v2.6 (#246): `tab` ("work", "advanced/review"…) draws, as cards, the catalogue groups on that tab other than `skip` (the
    groups a hand-made card holds). `groups` with `bare` draws just those groups' rows, with no card, inside the hand-made card
    of the same name (one card per group: Sweep, Reminders, Close the day…). `all` shows every row even while searching (the
    card's own title matched). */

/** The catalogue's tab for a setting: its own, or its group's (an older server), or none. @param {any} c @param {any} s */
export const tabOfSetting = (c, s) => s.tab !== undefined ? s.tab : ((c.group_tabs || {})[s.tier === "developer" ? "Developer" : s.group] ?? null);

/** The catalogue settings that are drawn as rows (not Essentials, not on a hand-made card's own controls), that a search finds.
    @param {any} c @param {(key:string)=>boolean} covered @param {string[]} w */
export const moreRows = (c, covered, w) => c.settings.filter(s => s.tier !== "essentials" && !covered(s.key) && tabOfSetting(c, s) !== null
  && (!w.length || settingHasAll(`${s.group} ${s.label} ${s.line} ${s.reason} ${s.key}`, w)));

/** Catalogue settings by group: cards for a tab, or one hand-made card's rows. @param {MoreSettingsProps} props */
export function MoreSettings({ covered, tab, groups, skip = [], bare, all }) {
  const c = catalogue.value;
  if (!c) return null;
  const w = all ? [] : settingWords(query.value);
  const groupOf = s => s.tier === "developer" ? "Developer" : s.group;
  const list = moreRows(c, covered, w).filter(s => groups ? groups.includes(groupOf(s)) : tabOfSetting(c, s) === tab && !skip.includes(groupOf(s)));
  if (!list.length) return null;
  if (bare) return <>{list.map(s => <One key={s.key} s={s} />)}</>;
  const order = [...c.groups.filter(g => g !== "Developer"), "Developer"].filter(g => list.some(s => groupOf(s) === g));
  return (
    <div class="setstack">
      {order.map(g => (
        <div class="card" data-more={g}>
          <h2>{g}</h2>
          {list.filter(s => groupOf(s) === g).map(s => <One key={s.key} s={s} />)}
        </div>
      ))}
    </div>
  );
}
