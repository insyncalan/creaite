// @ts-check
/* Top (v2.1.0 P6, BL-335): the report's header with its logos, and WkHealth with its six-week trend. Drawn as the mockup draws them
   ("Weekly report redesign"): the title block and the logos at the right; a coloured flag word (never colour alone), the trend bars
   flush under it, and the reason in Alan's words beside. Logos are the project's files (Settings › Projects › Report logos, kept
   under system/branding/logos/); which of them show is this report's `layout.logos`. */
import { Menu } from "../../Menu.jsx";
import { weeklyLogos, weeklyView } from "../../../stores/weekly.js";
import { Rich } from "./Rich.jsx";
import { wkDm, wkLongDate, wkTone, withSection } from "./weeklyDoc.js";

/** @typedef {import("../Sheet.jsx").SectionCtx} SectionCtx */
const KIND = { firm: "Firm", client: "Client", partner: "Partner" };

/** The header: what the report is, the project, the week, the client; the logos. @param {{ctx: SectionCtx}} props */
export function WkHeader({ ctx }) {
  const { doc, section: s } = ctx, d = s.data || {}, v = weeklyView.value;
  const all = (v && v.logos) || [], chosen = Array.isArray(doc.layout?.logos) ? doc.layout.logos : ["firm", "client", "partner"];
  const shown = all.filter(l => l.kind === "firm" || chosen.includes(l.kind));
  const pick = (/** @type {string} */ kind) => {
    const next = chosen.includes(kind) ? chosen.filter((/** @type {string} */ k) => k !== kind) : [...chosen, kind];
    ctx.setDoc(withSection(doc, "header", {}, { logos: next }), "Logos changed");
  };
  return (
    <header class="wr-hd">
      <div class="wr-title">
        <div class="wr-eb">{d.label || "Weekly report · Internal"}</div>
        <div class="wr-pn">{doc.project_name}</div>
        <div class="wr-wk">Week ending {wkLongDate(doc.date)}{d.client ? ` · for ${d.client}` : ""}</div>
      </div>
      <div class="wr-logos">
        {shown.map((l, i) => <span key={l.kind} class="wr-logo">{i ? <span class="wr-lsep" aria-hidden="true" /> : null}
          {weeklyLogos.value[l.path] ? <img src={weeklyLogos.value[l.path]} alt={`${KIND[/** @type {"firm"} */ (l.kind)] || l.kind} logo`} />
            : <span class="sub">{KIND[/** @type {"firm"} */ (l.kind)] || l.kind}</span>}</span>)}
        {ctx.editing && all.length > 1 ? <Menu label="Logos" btnCls="btn sm" menuLabel="Logos on this report" data={{ wrlogos: "" }}
          items={[{ head: "Logos on this report", id: "h" }, ...all.map(l => ({ id: l.kind, name: KIND[/** @type {"firm"} */ (l.kind)] || l.kind,
            checked: l.kind === "firm" || chosen.includes(l.kind), disabled: l.kind === "firm", line: l.kind === "firm" ? "always first" : "" })),
          { note: "Which logos show by default is set per project in Settings.", id: "n" }]} onPick={pick} /> : null}
      </div>
    </header>);
}

const HEALTH_FLAGS = ["On track", "At risk", "Off track"];

/** WkHealth: the flag, six weeks, the reason. Its heading is hidden, so the ✦ that suggests the health and its reason (#203) sits
    right of the flag. @param {{ctx: SectionCtx}} props */
export function WkHealth({ ctx }) {
  const { doc, section: s } = ctx, d = s.data || {}, flag = d.flag || "", t = wkTone(flag);
  /** @type {{date: string, flag: string}[]} */
  const past = (d.trend || []).filter((/** @type {any} */ x) => x.date !== doc.date), weeks = [...past.slice(-5), { date: doc.date, flag }];
  const set = (/** @type {string} */ f) => ctx.update({ data: { ...d, flag: f } }, "Health changed");
  const aria = `WkHealth over ${weeks.length} weeks: ${weeks.map(w => `${w.flag || "not set"}`).join(", ")}`;
  return (
    <div class="wr-health" data-wkTone={t}>
      <div class="wr-hcol">
        <div class="wr-flagrow"><div class={`wr-flag ${t}`}>{(flag || "Not set").toUpperCase()}</div><ctx.Spark /></div>
        <div class="wr-trend" role="img" aria-label={aria}>{weeks.map((w, i) => <i key={i} class={wkTone(w.flag)} />)}</div>
        <div class="wr-tlbl"><span>{wkDm(weeks[0].date)}</span><span>{wkDm(doc.date)}</span></div>
        {ctx.editing ? <Menu label="Change" btnCls="btn sm wr-chg" menuLabel="Health for this week" items={HEALTH_FLAGS.map(f => ({ id: f, name: f, checked: f === flag }))}
          onPick={set} /> : null}
      </div>
      <div class="wr-why">
        <Rich ctx={ctx} text={s.text} label="Why this health" empty="Say why health is what it is" />
        {d.last_week && d.last_week.flag ? <div class="wr-last">Last week: {d.last_week.flag}{d.last_week.date ? ` (${wkDm(d.last_week.date)})` : ""}</div> : null}
      </div>
    </div>);
}
