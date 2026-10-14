// @ts-check
/* Icon (BL-256, dev/COMPONENTS.md §3): one of the page's icons (core/dom.js ICONS) as elements, never raw HTML. ICONS holds
   each icon as a string of SVG shapes; this reads that string once into element data ([tag, attributes]) and draws it with
   JSX, so a component needs no innerHTML (COMPONENTS.md Q2). It draws the same <svg> as ic(name): class "i", a 24px grid,
   a 1.8 stroke, round caps and currentColor, hidden from screen readers (the words beside it carry the meaning). */
import { ICONS } from "../core/dom.js";

const SHAPES = new Set(["path", "circle", "rect", "line", "polyline", "polygon", "ellipse"]);
/** @type {Record<string, [string, Record<string, string>][]>} */
const PARSED = {};

/** An icon's shapes as element data: [["path", {d: "…"}], ["circle", {cx: "12", …}]]. Only plain SVG shapes and their
    attributes are kept; anything else in the string is dropped.
    @param {string} name @returns {[string, Record<string, string>][]} */
export function iconShapes(name) {
  if (PARSED[name]) return PARSED[name];
  const src = String(ICONS[name] || ""), out = /** @type {[string, Record<string, string>][]} */ ([]);
  for (const m of src.matchAll(/<([a-z]+)((?:\s+[a-z-]+="[^"]*")*)\s*\/?>/g)) {
    if (!SHAPES.has(m[1])) continue;
    /** @type {Record<string, string>} */
    const attrs = {};
    for (const a of m[2].matchAll(/([a-z-]+)="([^"]*)"/g)) if (!/^on/i.test(a[1])) attrs[a[1]] = a[2];
    out.push([m[1], attrs]);
  }
  PARSED[name] = out;
  return out;
}

/** @typedef {{name: string, cls?: string, size?: number}} IconProps */

/** @param {IconProps} props */
export function Icon({ name, cls, size }) {
  const sz = size ? { width: String(size), height: String(size), style: `width:${size}px;height:${size}px` } : {};
  return (
    <svg class={`i${cls ? " " + cls : ""}`} viewBox="0 0 24 24" {...sz} fill="none" stroke="currentColor" stroke-width="1.8"
      stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" data-icn={name}>
      {iconShapes(name).map(([tag, attrs], i) => { const T = /** @type {any} */ (tag); return <T key={i} {...attrs} />; })}
    </svg>
  );
}
