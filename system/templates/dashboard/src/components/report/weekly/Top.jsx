// @ts-check
/* Top (v2.1.0 P6, BL-335; #221): the weekly report's header and health, drawn with the parts both reports share (ReportParts.jsx): the
   one title block with its logos at the right, and the 96 px health indicator with its six-week trend. The words beside the flag are
   Alan's, in the sheet's one editor. */
import { Menu } from "../../Menu.jsx";
import { weeklyLogos, weeklyView } from "../../../stores/weekly.js";
import { HealthBlock, ReportHeader } from "../ReportParts.jsx";
import { Rich } from "./Rich.jsx";
import { wkDm } from "./weeklyDoc.js";

/** @typedef {import("../Sheet.jsx").SectionCtx} SectionCtx */

/** The header: what the report is, the project, the week, the client; the logos. @param {{ctx: SectionCtx}} props */
export function WkHeader({ ctx }) {
  const v = weeklyView.value;
  return <ReportHeader ctx={ctx} logos={(v && v.logos) || []} data={weeklyLogos.value} />;
}

const HEALTH_FLAGS = ["On track", "At risk", "Off track"];

/** WkHealth: the flag, six weeks, the reason. Its heading is hidden, so the sparkle that suggests the health and its reason (#203) sits
    beside the reason. @param {{ctx: SectionCtx}} props */
export function WkHealth({ ctx }) {
  const { doc, section: s } = ctx, d = s.data || {}, flag = d.flag || "";
  /** @type {{date: string, flag: string}[]} */
  const past = (d.trend || []).filter((/** @type {any} */ x) => x.date !== doc.date), weeks = [...past.slice(-5), { date: doc.date, flag }];
  const set = (/** @type {string} */ f) => ctx.update({ data: { ...d, flag: f } }, "Health changed");
  return (
    <HealthBlock ctx={ctx} flag={flag} trend={weeks}
      change={<Menu label="Change" btnCls="btn sm wr-chg" menuLabel="Health for this week" items={HEALTH_FLAGS.map(f => ({ id: f, name: f, checked: f === flag }))} onPick={set} />}
      why={<><Rich ctx={ctx} text={s.text} label="Why this health" empty="Say why health is what it is" />
        {d.last_week && d.last_week.flag ? <div class="wr-last">Last week: {d.last_week.flag}{d.last_week.date ? ` (${wkDm(d.last_week.date)})` : ""}</div> : null}</>} />);
}
