// @ts-check
/* WeeklyPartner (v2.1.0 P8): the internal report as the left page of Side by side, read only. A THIN SEAM: P6 builds the weekly
   report view and its renderers; until it lands the stub's defaults draw the internal sections, and this draws only the health
   flag, which the defaults would lose. When P6 lands, replace INTERNAL_RENDERERS with P6's weekly renderers (assumed to be
   exported by components/report/WeeklyView.jsx as `WEEKLY_RENDERERS`, taking the same SectionCtx). */
import { CLIENT_FLAGS } from "./clientDoc.js";

/** @typedef {import("./Sheet.jsx").SectionCtx} SectionCtx */

/** @param {{ctx: SectionCtx}} props */
function InternalHealth({ ctx }) {
  const flag = String((ctx.section.data || {}).flag || ""), cls = (CLIENT_FLAGS.find(f => f[0] === flag) || CLIENT_FLAGS[0])[1];
  return <div class="crhealth"><div class="crhcol"><span class={`crflag ${cls}`}>{flag.toUpperCase()}</span></div><div class="crwhy"><p>{ctx.section.text}</p></div></div>;
}

export const INTERNAL_RENDERERS = { byId: { health: (/** @type {SectionCtx} */ ctx) => <InternalHealth ctx={ctx} /> } };
