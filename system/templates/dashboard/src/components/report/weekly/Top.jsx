// @ts-check
/* Top (v2.1.0 P6, BL-335; #221): the weekly report's header and health, drawn with the parts both reports share (ReportParts.jsx): the
   one title block with its logos at the right, and the 96 px health indicator with its six-week trend. The words beside the flag are
   Alan's, in the sheet's one editor. */
import { Icon } from "../../Icon.jsx";
import { closeMenu, menuOpenFor, openMenu } from "../../Menu.jsx";
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
/* #287: each health's icon and tone (the flag's own colours: g, a, r) */
const HEALTH_ICON = /** @type {Record<string, [string, string]>} */ ({ "On track": ["done", "g"], "At risk": ["alert", "a"], "Off track": ["x", "r"] });

/** HealthChange (#287): the Change button under the flag. Its menu is the section menu's popup (openMenu, class "rsmenu", kept
    clear of the side bar), never a menu inside the scaled page: compact icon-and-word rows that follow the palette, the current
    health ticked (aria-checked). @param {{flag: string, onPick: (f: string) => void}} props */
function HealthChange({ flag, onPick }) {
  /* menuitemradio items, aria-checked on the current health (its icon becomes a tick, in the same tone) */
  const items = HEALTH_FLAGS.map(f => ({ id: f, name: f, icon: HEALTH_ICON[f][0], radio: true, checked: f === flag,
    data: { tone: HEALTH_ICON[f][1] } }));
  const pick = (/** @type {string} */ f) => { closeMenu("pick"); onPick(f); };   /* openMenu keeps a checked item's menu open: a radio pick closes it */
  const open = (/** @type {HTMLElement} */ anchor) => {
    if (menuOpenFor(anchor)) { closeMenu("away"); return; }
    const rail = document.querySelector(".rail"), keep = rail ? rail.getBoundingClientRect().right + 8 : 8;
    openMenu(anchor, { label: "Health for this week", items, onPick: pick, cls: "rsmenu wr-hmenu", minLeft: keep });
  };
  return (
    <span class="dd">
      <button type="button" class="btn sm wr-chg" aria-haspopup="menu" aria-expanded="false"
        onClick={e => open(/** @type {HTMLElement} */ (e.currentTarget))}
        onKeyDown={e => { if (e.key === "ArrowDown") { e.preventDefault(); open(/** @type {HTMLElement} */ (e.currentTarget)); } }}>
        <span>Change</span><Icon name="chevdown" cls="nch" />
      </button>
    </span>);
}

/** WkHealth: the flag, six weeks, the reason. Its heading is hidden, so the sparkle that suggests the health and its reason (#203) sits
    beside the reason. @param {{ctx: SectionCtx}} props */
export function WkHealth({ ctx }) {
  const { doc, section: s } = ctx, d = s.data || {}, flag = d.flag || "";
  /** @type {{date: string, flag: string}[]} */
  const past = (d.trend || []).filter((/** @type {any} */ x) => x.date !== doc.date), weeks = [...past.slice(-5), { date: doc.date, flag }];
  const set = (/** @type {string} */ f) => ctx.update({ data: { ...d, flag: f } }, "Health changed");
  return (
    <HealthBlock ctx={ctx} flag={flag} trend={weeks}
      change={<HealthChange flag={flag} onPick={set} />}
      why={<><Rich ctx={ctx} text={s.text} label="Why this health" empty="Say why health is what it is" />
        {d.last_week && d.last_week.flag ? <div class="wr-last">Last week: {d.last_week.flag}{d.last_week.date ? ` (${wkDm(d.last_week.date)})` : ""}</div> : null}</>} />);
}
