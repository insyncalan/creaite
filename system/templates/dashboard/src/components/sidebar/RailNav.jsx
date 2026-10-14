// @ts-check
/* RailNav (BL-319 part 6): the pages at the top of the sidebar, in the saved order (Today first). */
import { railCfg } from "../../stores/rail.js";
import { RailButton } from "./RailButton.jsx";

/** @typedef {{onGo: (id: string) => void}} RailNavProps */

/** @param {RailNavProps} props */
export function RailNav({ onGo }) {
  return <>{railCfg.value.order.map(id => <RailButton key={id} id={id} onGo={onGo} />)}</>;
}
