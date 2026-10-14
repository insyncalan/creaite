// @ts-check
/* RailToggle (BL-319 part 6): the discreet panel icon at the top-left of the sidebar, before the wordmark, in the same
   place collapsed or expanded. Its name and tooltip say what it will do ("Collapse the sidebar" or "Expand the
   sidebar"), aria-expanded says what it is, ⌘\ (Ctrl+\) does the same, and the choice is remembered (dashboard.rail's
   display). Hidden under 1200px, where the sidebar is always the rail of icons. */
import { railCollapsed, railNarrow } from "../../stores/rail.js";
import { RailIcon } from "./RailIcon.jsx";

/** @typedef {{onToggle: () => void, keyName: string}} RailToggleProps */

/** @param {RailToggleProps} props */
export function RailToggle({ onToggle, keyName }) {
  const collapsed = railCollapsed.value;
  const what = collapsed ? "Expand the sidebar" : "Collapse the sidebar";
  return (
    <button type="button" class="rtog" id="railTog" aria-controls="rail" aria-expanded={collapsed ? "false" : "true"}
      aria-label={what} data-tip={what} data-key={keyName} hidden={railNarrow.value} onClick={onToggle}>
      <RailIcon name="panel" />
    </button>
  );
}
