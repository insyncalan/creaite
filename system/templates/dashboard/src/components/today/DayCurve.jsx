// @ts-check
/* DayCurve (BL-293): the day band's line, a bump per meeting, as renderDay drew it before (BL-72), now for any day the
   saved calendar holds. Today has the sun at the current time and the Now dot; another day has neither: a past day's
   meetings are all past, a later day's none. Drawn into #dayLine. */
import { render } from "preact";
import { z2 } from "../../core/server.js";
import { wheelRef } from "./wheel.js";

/** @typedef {{start: string, end: string, title: string}} CurveMeeting */
/** @typedef {{timed: CurveMeeting[], now: number | null, past: boolean, label: string, width: number, day: string,
    onWheel?: (e: WheelEvent) => void}} DayCurveProps
    `now`: minutes since midnight on today, null on any other day; `past`: the whole day is behind us. */

/** "HH:MM" → minutes since midnight. @param {string} t */
export const minsOf = t => { const [h, m] = String(t || "0:0").split(":").map(Number); return h * 60 + (m || 0); };
const curveClock = (/** @type {number} */ m) => `${z2(Math.floor(m / 60))}:${z2(m % 60)}`;

/** The line.
    @param {DayCurveProps} props */
export function DayCurve({ timed, now, past, label, width, onWheel }) {
  const ds = Math.min(8 * 60, ...timed.map(e => Math.floor(minsOf(e.start) / 60) * 60)), de = Math.max(19 * 60, ...timed.map(e => Math.ceil(minsOf(e.end) / 60) * 60));
  const W = Math.max(400, Math.round(width || 1000)), X0 = 14, X1 = W - 14, BASE = 96, x = (/** @type {number} */ m) => X0 + (m - ds) / (de - ds) * (X1 - X0);
  const bumps = timed.map(e => { const a = minsOf(e.start), b = minsOf(e.end); return { c: x((a + b) / 2), w: Math.max((x(b) - x(a)) / 2, 14) + 16, h: Math.min(10 + (b - a) / 12, 17), e, a, b }; });
  const yAt = (/** @type {number} */ px) => BASE - Math.min(24, bumps.reduce((s, k) => s + k.h * Math.exp(-(((px - k.c) / k.w) ** 2)), 0));
  let d = ""; for (let px = X0; px <= X1; px += 3) d += `${px === X0 ? "M" : "L"}${px.toFixed(1)} ${yAt(px).toFixed(1)}`;
  const state = (/** @type {{a: number, b: number}} */ k) => past ? "past" : now == null ? "" : k.b <= now ? "past" : k.a <= now && now < k.b ? "now" : "";
  const sunOn = now != null && now >= ds && now <= de, sx = now == null ? 0 : x(Math.min(Math.max(now, ds), de));
  const lastEnd = timed.length ? Math.max(...timed.map(e => minsOf(e.end))) : 0;
  return (
    <svg viewBox={`0 0 ${W} ${BASE + 32}`} role="img" aria-label={label} ref={wheelRef(onWheel)}>
      {sunOn ? <g class="sun" transform={`translate(${sx.toFixed(1)} 30)`} aria-label={`Now ${curveClock(now)}`}><title>Now, {curveClock(now)}</title><circle r="11" /><path d="M0 -21v-6M0 21v6M-21 0h-6M21 0h6" /></g> : null}
      {lastEnd <= 18 * 60 ? <path class="moon" transform={`translate(${x(de - 50).toFixed(1)} 44)`} d="M-14 0q7 -8 14 0q7 -8 14 0"><title>Evening free</title></path> : null}
      <path class="ln" d={d} />
      {bumps.map(k => {
        const st = state(k), cx = k.c.toFixed(1), cy = yAt(k.c).toFixed(1), r = (5 + Math.min(k.b - k.a, 120) / 30).toFixed(1);
        return [<circle class={`dot ${st}`} cx={cx} cy={cy} r={r}><title>{curveClock(k.a)}–{curveClock(k.b)} {k.e.title ?? ""}</title></circle>,
          st === "now" ? <circle class="mnow" cx={cx} cy={cy} r={r} aria-hidden="true" /> : null];
      })}
      {[9, 12, 15, 18].filter(h => h * 60 > ds && h * 60 < de).map(h => [
        <line class="tk" x1={x(h * 60)} x2={x(h * 60)} y1={BASE + 8} y2={BASE + 13} />,
        <text class="hr" x={x(h * 60)} y={BASE + 27}>{z2(h)}:00</text>])}
    </svg>
  );
}

/** Draw the line into `host` (#dayLine), or clear it with null props.
    @param {Element} host @param {DayCurveProps | null} props */
export function drawDayCurve(host, props) {
  render(props ? <DayCurve key={props.day} {...props} /> : null, host);
}
