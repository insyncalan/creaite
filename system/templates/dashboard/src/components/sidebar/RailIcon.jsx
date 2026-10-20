// @ts-check
/* RailIcon (BL-319 part 6): the sidebar's icons as element data (dev/COMPONENTS.md, Q2): each icon is a list of
   [tag, attributes], drawn on the 24px grid with the 1.8 stroke, round caps and currentColor, like ic(). The paths are
   core/dom.js's ICONS, so the pages' icons look as they did; no raw HTML. */

/** @typedef {[string, Record<string, string>]} IconPart */
/** @type {Record<string, IconPart[]>} */
const RAIL_ICONS = {
  today: [["circle", { cx: "12", cy: "12", r: "4" }], ["path", { d: "M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1 7 17M17 7l2.1-2.1" }]],
  inbox: [["path", { d: "M4 13l2.5-8h11L20 13v6H4z" }], ["path", { d: "M4 13h5l1 2h4l1-2h5" }]],   /* #232 Q8: the locked mockup's tray */
  projects: [["path", { d: "M4 13h6V4H4zM14 20h6v-9h-6zM4 20h6v-4H4zM14 4v4h6V4z" }]],
  work: [["path", { d: "M8 6h12M8 12h12M8 18h12" }], ["path", { d: "m3 6 1 1 2-2M3 12l1 1 2-2M3 18l1 1 2-2" }]],
  people: [["circle", { cx: "9", cy: "8", r: "3.2" }], ["path", { d: "M3.5 19v-1a4.5 4.5 0 0 1 4.5-4.5h2a4.5 4.5 0 0 1 4.5 4.5v1" }], ["path", { d: "M16 5.2a3.2 3.2 0 0 1 0 5.6M18.5 13.8a4.5 4.5 0 0 1 2 3.7V19" }]],
  review: [["path", { d: "M4 5h16v11H8l-4 4z" }], ["path", { d: "m9 10.5 2 2 4-4" }]],
  activity: [["path", { d: "M12 7v5l3 2" }], ["circle", { cx: "12", cy: "12", r: "8.5" }]],
  filetext: [["path", { d: "M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7z" }], ["path", { d: "M14 2v4a2 2 0 0 0 2 2h4M10 9H8M16 13H8M16 17H8" }]],
  folder: [["path", { d: "M3 6a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" }]],
  gear: [["path", { d: "M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" }], ["circle", { cx: "12", cy: "12", r: "3" }]],
  more: [["circle", { cx: "5", cy: "12", r: "1" }], ["circle", { cx: "12", cy: "12", r: "1" }], ["circle", { cx: "19", cy: "12", r: "1" }]],
  pulse: [["path", { d: "M3 12h4l2.5-6 4 12 2.5-6H21" }]],
  help: [["circle", { cx: "12", cy: "12", r: "9" }], ["path", { d: "M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.7.4-1 .9-1 1.7M12 17h.01" }]],
  sliders: [["path", { d: "M21 4h-7M10 4H3M21 12h-9M8 12H3M21 20h-5M12 20H3M14 2v4M8 10v4M16 18v4" }]],
  panel: [["rect", { x: "3", y: "4", width: "18", height: "16", rx: "3" }], ["path", { d: "M9 4v16" }]],
  grip: [["circle", { cx: "9", cy: "6", r: "1" }], ["circle", { cx: "15", cy: "6", r: "1" }], ["circle", { cx: "9", cy: "12", r: "1" }], ["circle", { cx: "15", cy: "12", r: "1" }], ["circle", { cx: "9", cy: "18", r: "1" }], ["circle", { cx: "15", cy: "18", r: "1" }]],
  up: [["path", { d: "m18 15-6-6-6 6" }]],
  down: [["path", { d: "m6 9 6 6 6-6" }]],
  right: [["path", { d: "M5 12h14M13 6l6 6-6 6" }]],
  left: [["path", { d: "M19 12H5M11 6l-6 6 6 6" }]],
};

/** @typedef {{name: string}} RailIconProps */

/** One sidebar icon, hidden from screen readers (its button carries the words).
    @param {RailIconProps} props */
export function RailIcon({ name }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"
      stroke-linejoin="round" aria-hidden="true" data-icn={name}>
      {(RAIL_ICONS[name] || []).map(([tag, attrs], i) =>
        tag === "circle" ? <circle key={i} {...attrs} /> : tag === "rect" ? <rect key={i} {...attrs} /> : <path key={i} {...attrs} />)}
    </svg>
  );
}
