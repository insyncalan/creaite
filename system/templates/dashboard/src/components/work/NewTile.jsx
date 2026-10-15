// @ts-check
/* NewTile (BL-159, BL-316): Work's New tile, at the end of the toolbar. It says the tab's own word (in its name, its tooltip
   and, on hover or focus, as it grows) and opens the new item's form; on Decisions it is a Menu (Record a decision: the form as
   Made, dated today; Ask for a decision: as Pending, with a needed-by date). Hidden on All items. */
import { render } from "preact";
import { Icon } from "../Icon.jsx";
import { Menu } from "../Menu.jsx";

/** @typedef {{word: string, decisions: boolean, hidden: boolean, onNew: () => void, onDecision: (how: "made" | "needed") => void, id?: string}} NewTileProps */

/** @param {NewTileProps} props */
export function NewTile({ word, decisions, hidden, onNew, onDecision, id = "newBtn" }) {
  if (decisions) {
    return (
      <Menu label={word} ariaLabel={word} tip={word} icon="plus" labelCls="w" id="newBtn" btnCls="newb hasmenu" hidden={hidden}
        menuId="newDecMenu" menuLabel="New decision" onPick={id => onDecision(id === "needed" ? "needed" : "made")}
        items={[
          { id: "made", icon: "check", name: "Record a decision", line: "Already taken. Opens as Made, dated today.", data: { newd: "made" } },
          { id: "needed", icon: "flag", name: "Ask for a decision", line: "Waiting on someone. Opens as Pending, with a needed-by date.", data: { newd: "needed" } },
        ]} />
    );
  }
  return (
    <span class="dd">
      <button type="button" class="newb" id={id} aria-label={word} data-tip={word} hidden={hidden} onClick={onNew}>
        <Icon name="plus" /><span class="w">{word}</span><Icon name="chevdown" cls="nch" />
      </button>
    </span>
  );
}

/** Draw the tile into its place on the toolbar (#newHost). @param {Element} host @param {NewTileProps} props */
export function drawNewTile(host, props) { render(<NewTile {...props} />, host); }
