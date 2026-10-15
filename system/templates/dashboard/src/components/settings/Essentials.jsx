// @ts-check
/* Essentials (BL-320, v1.9.2): the settings that change Alan's day, about sixteen rows in six sections, each with one line on
   what it does. The rows, their sections and their words come from /api/settings/catalogue (`essentials`); the values from the
   same answer. A row may cover several keys: what the sweep reads is five switches, AI drafts one switch for every kind (the
   per-kind switches stay in Advanced). Each change is saved with writeSettings (a backup and a log line), as every setting is.
   The page's search narrows the rows; a section with none left isn't drawn. */
import { useEffect, useRef, useState } from "preact/hooks";
import { THEMES } from "../../core/page.js";
import { shared } from "../../core/state.js";
import { applyPending, SERVED, snack } from "../../core/server.js";
import { catalogue, catalogueError, query, saveSettings, settingOf } from "../../stores/settings.js";
import { rowId, SettingRow } from "./SettingRow.jsx";

const WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const WEEK_PRIOS = ["Urgent", "High", "Medium", "Low"];
const SWEEP_SOURCES = [["sweep.sources.inbox", "Inbox"], ["sweep.sources.sent_items", "Sent Items"], ["sweep.sources.teams_chats", "Teams chats"],
  ["sweep.sources.teams_channels", "Teams channels"], ["sweep.sources.calendar", "Calendar"]];
const HHMM = /^([01]\d|2[0-3]):[0-5]\d$/;

/** The words typed, lower case. @param {string} q */
export const settingWords = q => q.toLowerCase().split(/\s+/).filter(Boolean);
/** True when every word is in the text. @param {string} text @param {string[]} w */
export const settingHasAll = (text, w) => { const t = text.toLowerCase(); return w.every(x => t.includes(x)); };

/** @param {string} k */
const val = k => { const s = settingOf(k); return s ? s.value : undefined; };

/** @typedef {{row: import("../../stores/settings.js").EssentialRow}} EssentialProps */

/** One Essentials row with its control(s). @param {EssentialProps} props */
function Essential({ row }) {
  const [id] = useState(rowId);
  const [saved, setSaved] = useState(false);
  const t = useRef(0);
  const keys = row.keys, k = keys[0];
  const save = async (/** @type {Record<string, any>} */ changes) => {
    const ok = await saveSettings(changes);
    if (ok) { setSaved(true); clearTimeout(t.current); t.current = window.setTimeout(() => setSaved(false), 2500); }
    return ok;
  };
  const named = { "aria-labelledby": id, "aria-describedby": id + "h" };
  /** A text box saved on change, checked first. @param {(v:string)=>any} parse @param {string} bad @param {string} [ph] */
  const text = (parse, bad, ph = "") => (
    <input type="text" {...named} value={val(k) ?? ""} placeholder={ph} size={8}
      onChange={async e => { const el = /** @type {HTMLInputElement} */ (e.currentTarget), v = parse(el.value.trim());
        if (v === undefined) { snack(bad); el.value = val(k) ?? ""; return; }
        if (!await save({ [k]: v })) el.value = val(k) ?? ""; }} />
  );
  /** @param {[string, string][]} opts @param {string} [key] */
  const select = (opts, key = k) => (
    <select {...(key === k ? named : { "aria-label": `${row.label}: ${key.endsWith("_day") ? "day" : key}` })} value={String(val(key) ?? "")}
      onChange={async e => { const el = /** @type {HTMLSelectElement} */ (e.currentTarget); if (!await save({ [key]: el.value })) el.value = String(val(key) ?? ""); }}>
      {opts.map(([v, l]) => <option value={v}>{l}</option>)}
    </select>
  );
  const sw = () => (
    <input type="checkbox" class="switch" {...named} checked={!!val(k)}
      onChange={async e => { const el = /** @type {HTMLInputElement} */ (e.currentTarget); if (!await save({ [k]: el.checked })) el.checked = !!val(k); }} />
  );
  /** Tick boxes for the values of a list setting. @param {string[]} all @param {(v:string)=>string} [short] */
  const ticks = (all, short = v => v) => {
    const have = Array.isArray(val(k)) ? val(k) : [];
    return (
      <span class="setticks" role="group" {...named}>
        {all.map(v => (
          <label class="settick"><input type="checkbox" checked={have.includes(v)} aria-label={v}
            onChange={async e => { const el = /** @type {HTMLInputElement} */ (e.currentTarget), box = el.closest("[role=group]");
              /* what the boxes show now, so a second tick before the catalogue is reread builds on the first */
              const now = all.filter(x => { const b = box && /** @type {HTMLInputElement|null} */ (box.querySelector(`input[aria-label="${x}"]`)); return b ? b.checked : have.includes(x); });
              if (!await save({ [k]: now })) el.checked = have.includes(v); }} /> {short(v)}</label>
        ))}
      </span>
    );
  };
  let control;
  switch (k) {
    case "identity.name": control = text(v => v || undefined, "Your name can't be empty", "Full name"); break;
    case "work.weekend_days": control = ticks(WEEKDAYS, v => v.slice(0, 3)); break;
    case "sweep.due_from": control = text(v => HHMM.test(v) ? v : undefined, "Use 24-hour HH:MM, such as 07:00", "HH:MM"); break;
    case "sweep.sources.inbox":
      control = (
        <span class="setticks" role="group" {...named}>
          {SWEEP_SOURCES.map(([key, l]) => (
            <label class="settick"><input type="checkbox" checked={!!val(key)}
              onChange={async e => { const el = /** @type {HTMLInputElement} */ (e.currentTarget); if (!await save({ [key]: el.checked })) el.checked = !!val(key); }} /> {l}</label>
          ))}
        </span>
      );
      break;
    case "day.close_from": control = text(v => v === "" ? null : HHMM.test(v) ? v : undefined, "Use HH:MM, such as 17:30, or leave it empty for off", "Off"); break;
    case "day.catchup_sweep": control = select([["start", "Start it when the card opens"], ["offer", "Ask first"], ["off", "Off"]]); break;
    case "reminders.weekly_report_day":
      control = (
        <span class="setpair">
          {select(WEEKDAYS.slice(0, 5).map(d => [d, d]))}
          <input type="text" aria-label={`${row.label}: time`} value={val("reminders.weekly_report_from") ?? ""} size={6} placeholder="HH:MM"
            onChange={async e => { const el = /** @type {HTMLInputElement} */ (e.currentTarget), v = el.value.trim();
              if (!HHMM.test(v)) { snack("Use 24-hour HH:MM, such as 12:00"); el.value = val("reminders.weekly_report_from") ?? ""; return; }
              if (!await save({ "reminders.weekly_report_from": v })) el.value = val("reminders.weekly_report_from") ?? ""; }} />
        </span>
      );
      break;
    case "dashboard.auto_apply": control = sw(); break;
    case "dashboard.week_ahead_priorities": control = ticks(WEEK_PRIOS); break;
    case "vip.enabled": control = sw(); break;
    case "vip.check_minutes":
      control = (
        <span class="setpair"><input type="number" {...named} min={5} step={5} value={val(k) ?? 30} style="width:80px"
          onChange={async e => { const el = /** @type {HTMLInputElement} */ (e.currentTarget), v = Math.round(Number(el.value));
            if (!Number.isFinite(v) || v < 5) { snack("Use a number of minutes, 5 or more"); el.value = String(val(k) ?? 30); return; }
            if (!await save({ [k]: v })) el.value = String(val(k) ?? 30); }} /> <span class="sub">minutes</span></span>
      );
      break;
    case "dashboard.theme": control = select([["System", "Follow my Mac"], ["Light", "Light"], ["Dark", "Dark"]]); break;
    case "dashboard.palette": control = select(THEMES.map(x => [x.id, x.id])); break;
    case "dashboard.motion": control = select([["System", "Follow my Mac"], ["Reduce", "Reduce"], ["Full", "Full"]]); break;
    case "drafting.update": control = <AllSwitch keys={keys} named={named} save={save} />; break;
    default: control = sw();
  }
  const pending = k === "dashboard.auto_apply" && val(k) === false && shared.PENDING && shared.PENDING.length;
  return (
    <SettingRow id={id} label={row.label} line={row.line} changed={row.changed} keys={keys} saved={saved}
      resettable={keys.every(x => { const s = settingOf(x); return !s || s.resettable; })}>
      {control}
      {pending ? <button type="button" class="btn primary" id="applyNow" onClick={() => applyPending()}>Apply {shared.PENDING.length} waiting</button> : null}
    </SettingRow>
  );
}

/** @typedef {{keys:string[], named:Record<string,string>, save:(c:Record<string,any>)=>Promise<boolean>}} AllSwitchProps */

/** One switch for several boolean settings: on when all are on, mixed when some are. @param {AllSwitchProps} props */
function AllSwitch({ keys, named, save }) {
  const on = keys.filter(x => val(x) !== false).length, all = on === keys.length, mixed = on > 0 && !all;
  const ref = useRef(/** @type {HTMLInputElement|null} */ (null));
  useEffect(() => { if (ref.current) ref.current.indeterminate = mixed; });
  return (
    <input ref={ref} type="checkbox" class="switch" {...named} checked={all}
      onChange={async e => { const v = /** @type {HTMLInputElement} */ (e.currentTarget).checked;
        await save(Object.fromEntries(keys.map(x => [x, v]))); }} />
  );
}

/** The Essentials, in their sections. */
export function Essentials() {
  const c = catalogue.value;
  if (!c) return <div class="card wide"><h2>Essentials</h2><p class="sub" role="status">{catalogueError.value || (SERVED ? "Reading your settings…" : "The Essentials need the live server: open creaite from it.")}</p></div>;
  const w = settingWords(query.value);
  const rows = c.essentials.filter(r => (!w.length || settingHasAll(`${r.section} ${r.label} ${r.line} ${r.keys.join(" ")}`, w)));
  if (!rows.length) return null;
  const sections = [...new Set(rows.map(r => r.section))];
  return (
    <div class="setstack">
      {sections.map(s => (
        <div class="card" data-ess={s}>
          <h2>{s}</h2>
          {rows.filter(r => r.section === s).map(r => <Essential key={r.keys.join(" ")} row={r} />)}
        </div>
      ))}
    </div>
  );
}
