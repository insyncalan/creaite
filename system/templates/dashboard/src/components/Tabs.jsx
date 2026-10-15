// @ts-check
/* Tabs (BL-256, dev/COMPONENTS.md §3): switch between the panels of one screen. role="tablist" with role="tab" buttons,
   aria-selected and a roving tabindex (only the chosen tab is in the Tab order); ← → Home End move and select, and focus
   follows the chosen tab. Text goes through JSX only. First used by Today's day line (BL-293) and the prep page (BL-286 D);
   the two branches' blocks were joined on release-190, so it takes either way of calling it:
   - `items` (the day line): the caller draws the panel and `controls` names it; ← → stop at the ends; `className` is the
     list's whole class.
   - `tabs` with `idBase` (the prep page): each tab is `${idBase}-tab-${id}` and controls the panel `${idBase}-panel-${id}`,
     which the screen draws as role="tabpanel"; the list keeps today's class (.tabs, plus `cls`); ← → wrap round, as #wtabs.
   BL-316: every tab list in the page draws through it (Work's #wtabs, Help's, People's, Activity's, the history feeds'), so a
   list may carry its own `id`, and a tab its button's id (`tabId`), the panel it controls (`controls`), a count after its
   words (`count`) and the data- attributes other code reads (`data`); `wrap` sets wrap-round either way. `vertical` (Settings'
   categories, a column): aria-orientation="vertical", ↑ ↓ move as ← → do. With nothing chosen (Settings while searching)
   the first tab is the one in the Tab order. */
import { Fragment, render } from "preact";
import { useLayoutEffect, useRef } from "preact/hooks";
import { dataAttrs } from "./Menu.jsx";

/** @typedef {{id: string, label: string, name?: string, className?: string, current?: boolean,
    before?: import("preact").ComponentChildren, tabId?: string, controls?: string, count?: string | number,
    data?: Record<string, string>}} TabItem
    `name` is the tab's accessible name when it differs from `label`; `current` marks today (aria-current="date");
    `before` is drawn ahead of the tab (a separator), outside it. BL-316: `tabId` is the button's own id; `controls` the panel
    this tab controls (over the list's `controls`); `count` is drawn after the words as <span class="sub">; `data` gives the
    button data- attributes ({t: "raid"} is data-t="raid"). */
/** @typedef {{items?: TabItem[], tabs?: TabItem[], selected: string, onSelect: (id: string) => void, label: string,
    className?: string, cls?: string, tabClass?: string, controls?: string, idBase?: string, wrap?: boolean, id?: string,
    vertical?: boolean}} TabsProps
    `id` (BL-316): the list's own id; `vertical` a column of tabs (↑ ↓). */

/** The id of a tab's button and of its panel.
    @param {string} idBase @param {string} id */
export const tabId = (idBase, id) => `${idBase}-tab-${id}`;
/** @param {string} idBase @param {string} id */
export const panelId = (idBase, id) => `${idBase}-panel-${id}`;

/** A tab list.
    @param {TabsProps} props */
export function Tabs({ items, tabs, selected, onSelect, label, className, cls, tabClass, controls, idBase, wrap, id, vertical }) {
  const list = items || tabs || [], round = wrap ?? !items;
  const box = useRef(/** @type {HTMLDivElement | null} */ (null)), keyed = useRef(false);
  useLayoutEffect(() => {          /* a key moved the choice: focus follows it, once the tabs show it */
    if (!keyed.current) return; keyed.current = false;
    const b = box.current && /** @type {HTMLElement | null} */ (box.current.querySelector('[role="tab"][aria-selected="true"]'));
    if (b) b.focus();
  });
  /** @param {KeyboardEvent} e */
  const onKey = e => {
    const i = list.findIndex(t => t.id === selected), last = list.length - 1;
    const next = vertical ? "ArrowDown" : "ArrowRight", prev = vertical ? "ArrowUp" : "ArrowLeft";
    let j = e.key === next ? i + 1 : e.key === prev ? i - 1 : e.key === "Home" ? 0 : e.key === "End" ? last : null;
    if (j === null || e.metaKey || e.ctrlKey || e.altKey) return;
    e.preventDefault();
    j = round ? (j + list.length) % list.length : Math.max(0, Math.min(last, j));
    const to = list[j];
    if (!to) return;
    keyed.current = true;
    onSelect(to.id);
  };
  const listCls = items ? className : ["tabs", cls, className].filter(Boolean).join(" ");
  return (
    <div class={listCls} id={id} role="tablist" aria-label={label} aria-orientation={vertical ? "vertical" : undefined} ref={box} onKeyDown={onKey}>
      {list.map((t, n) => {
        const on = t.id === selected, inTab = on || (n === 0 && !list.some(x => x.id === selected));
        return (
          <Fragment key={t.id}>
            {t.before}
            <button type="button" role="tab" class={[tabClass, t.className].filter(Boolean).join(" ") || undefined} aria-selected={on ? "true" : "false"}
              id={t.tabId || (idBase ? tabId(idBase, t.id) : undefined)} aria-current={t.current ? "date" : undefined}
              aria-controls={t.controls || (idBase ? panelId(idBase, t.id) : controls)} aria-label={t.name} tabIndex={inTab ? 0 : -1}
              data-tab={t.id} {...dataAttrs(t.data)} onClick={() => onSelect(t.id)}>
              {t.label}{t.count != null ? <>{" "}<span class="sub">{t.count}</span></> : null}
            </button>
          </Fragment>
        );
      })}
    </div>
  );
}

/** Draw a Tabs into `host` (a screen that is not a component yet, and the block's own test).
    @param {Element} host @param {TabsProps} props */
export function drawTabs(host, props) {
  render(<Tabs {...props} />, host);
}
