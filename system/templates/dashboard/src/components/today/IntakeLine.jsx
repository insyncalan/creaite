// @ts-check
/* IntakeLine (#245, v2.5.2; dev/sprints/intake-line-brief.md, locked mockup dev/mockups/today-intake-line-mockup.html): Intake as one
   quiet, muted line at the foot of Your commitments, such as "Intake: 1 meeting ready to process and 4 proposals to approve."
   Each phrase is a real link (an href, so Tab and Enter work) to the page it names; the small x at the right edge is a real
   button ("Dismiss until something new arrives"). No heading, no list, no Approve or Reject: approving happens in Review and
   Intake. today.js decides whether there is a line at all (nothing waiting, or dismissed and nothing new: none) and where each
   phrase goes; this only draws it. Text only through JSX: nothing here takes HTML. */
import { render } from "preact";
import { Icon } from "../Icon.jsx";
import { IconButton } from "../IconButton.jsx";

/** @typedef {{key: string, n: number, text: string, go: string}} IntakePart */

/** @param {{parts: IntakePart[], onGo: (page: string) => void}} props */
export function IntakeLine({ parts, onGo }) {
  return (
    <p class="tdquiet" id="tdQuiet" role="status">
      <Icon name="inbox" />
      <span class="tdq">
        {"Intake: "}
        {parts.map((x, i) => (
          <>
            {i ? (i === parts.length - 1 ? " and " : ", ") : ""}
            <a href={`#${x.go}`} data-tdq={x.key} onClick={e => { e.preventDefault(); onGo(x.go); }}>{x.text}</a>
          </>
        ))}
        {"."}
      </span>
      <IconButton icon="x" label="Dismiss until something new arrives" id="tdQx" />
    </p>
  );
}

/** Draw the line into `host`, or clear it when there are no parts. The x is handled page-wide in today.js (it needs the counts).
    @param {Element} host @param {IntakePart[]} parts @param {(page: string) => void} onGo */
export function drawIntakeLine(host, parts, onGo) {
  render(parts.length ? <IntakeLine parts={parts} onGo={onGo} /> : null, host);
}
