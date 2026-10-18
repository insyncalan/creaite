// @ts-check
/* EyeButton (#217, #221): the one "in the report" switch of the sheet, for the weekly and the client report alike. An open eye = in
   the report; an eye with a slash = left out of it (the row is dimmed by its table). It replaces the grey dot. Same switch, same
   names, same keys (Space or Enter), same tip. Screen readers hear "In the report: <what>" and whether it is pressed (on or off). */
import { Icon } from "../Icon.jsx";

/** @param {{on: boolean, subject: string, onClick: () => void, cls?: string, data?: Record<string, string>}} props */
export function EyeButton({ on, subject, onClick, cls = "", data }) {
  return (
    <button type="button" class={`rs-eye wr-eye${cls ? " " + cls : ""}`} aria-pressed={on ? "true" : "false"} aria-label={`In the report: ${subject}`}
      data-tip={on ? "In the report: click to leave it out" : "Left out of the report: click to put it back"}
      {...Object.fromEntries(Object.entries(data || {}).map(([k, v]) => [`data-${k}`, v]))} onClick={onClick}>
      <Icon name={on ? "eye" : "eyeoff"} />
    </button>);
}
