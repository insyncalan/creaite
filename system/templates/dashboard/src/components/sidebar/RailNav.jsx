// @ts-check
/* RailNav (BL-319 part 6): the pages at the top of the sidebar, in the saved order (Today first). */
import { railCfg } from "../../stores/rail.js";
import { RailButton } from "./RailButton.jsx";

/** @typedef {{onGo: (id: string) => void, flyouts?: Record<string, () => import("../Menu.jsx").MenuItem[]>,
    onFly?: (id: string, pick: string) => void}} RailNavProps
    `flyouts` (#139): the pages that open a list on hover, by id, and `onFly` for a pick. */

/** @param {RailNavProps} props */
export function RailNav({ onGo, flyouts = {}, onFly }) {
  return <>{railCfg.value.order.map(id => <RailButton key={id} id={id} onGo={onGo} fly={flyouts[id]} onFly={onFly} />)}</>;
}
