// @ts-check
/* ProjectTabs (BL-301 B): the project page's tabs, Overview (the cockpit) and Notes, on the Tabs block. Each tab is its own page
   with its own address (#cockpit=ABC, #notes=ABC), so a re-draw of one never touches the other. The portfolio's notes have no
   Overview tab: they sit under Portfolio. */
import { render } from "preact";
import { Tabs } from "../Tabs.jsx";

/** @typedef {{code: string, selected: "overview"|"notes", count: number, onGo: (tab: string) => void}} ProjectTabsProps */

/** @param {ProjectTabsProps} props */
export function ProjectTabs({ code, selected, count, onGo }) {
  const items = [{ id: "overview", label: "Overview" },
    { id: "notes", label: count ? `Notes · ${count}` : "Notes", name: count ? `Notes, ${count} note${count === 1 ? "" : "s"}` : "Notes" }];
  return <Tabs items={items} selected={selected} onSelect={onGo} label="Project page" className="tabs projtabs"
    controls={selected === "notes" ? "v-notes" : "v-cockpit"} wrap={false} />;
}

/** Draw the tabs into `host` (the cockpit is not a component yet). @param {Element} host @param {ProjectTabsProps} props */
export function drawProjectTabs(host, props) { render(<ProjectTabs {...props} />, host); }
