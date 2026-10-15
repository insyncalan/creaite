// @ts-check
/* StatusDot (BL-256, dev/COMPONENTS.md): a project's health as its icon and its word, never colour alone. The first
   component: it draws exactly the markup core/page.js's health() writes, so a screen that moves to it looks the same.
   BL-316: also a plain status dot (`status`: ok, warn, bad, off or staged), as the live line, the staging bar and a staged
   row draw it. It still carries its word: `word` drawn after the dot (in its own span when `wordId` names it, for code that
   updates it; `live` makes that span polite), or `label` as the dot's own name (role="img", the tooltip too). */
import { render } from "preact";
import { HEALTH_SHAPES, hk } from "../core/page.js";

/** @typedef {{health?: string, status?: "ok" | "warn" | "bad" | "off" | "staged", word?: string, wordId?: string,
    live?: boolean, label?: string, cls?: string}} StatusDotProps
    With `status`: `cls` is the dot's class (default "dot"; warn, bad and off are added to it); `word` or `wordId` puts the
    word beside it (the dot is then hidden from screen readers); `label` names the dot itself. */

/** A plain status dot and its word.
    @param {StatusDotProps} props */
function Dot({ status, word, wordId, live, label, cls }) {
  const c = [cls || "dot", status === "warn" || status === "bad" || status === "off" ? status : ""].filter(Boolean).join(" ");
  const named = !!label;
  const dot = <span class={c} role={named ? "img" : undefined} aria-label={label} data-tip={label} aria-hidden={named ? undefined : "true"} />;
  if (wordId) return <>{dot}<span id={wordId} aria-live={live ? "polite" : undefined}>{word}</span></>;
  return <>{dot}{word}</>;
}

/** One health marker: `<span class="health h-ok">` with the health's icon and its word ("Not set" when there is none);
    with `status`, a plain status dot (see StatusDotProps).
    @param {StatusDotProps} props */
export function StatusDot(props) {
  if (props.status) return <Dot {...props} />;
  const { health } = props, k = hk(health);
  return (
    <span class={`health h-${k}`}>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
        {HEALTH_SHAPES[k].map(([tag, attrs]) => tag === "circle" ? <circle {...attrs} /> : <path {...attrs} />)}
      </svg>
      {health || "Not set"}
    </span>
  );
}

/** A StatusDot as plain nodes, for old code to put in place (drawn once; nothing redraws them).
    @param {StatusDotProps} props @returns {ChildNode[]} */
export function statusDotNodes(props) {
  const box = document.createElement("span");
  render(<StatusDot {...props} />, box);
  return [...box.childNodes];
}

/** Draw a StatusDot into `host`, redrawn in place by calling it again (a line whose dot and word change).
    @param {Element} host @param {StatusDotProps} props */
export function drawStatusDot(host, props) {
  render(<StatusDot {...props} />, host);
}

/** Put a StatusDot in place of each `<span data-statusdot="…">` inside `root` (the health is the attribute's value).
    The placeholder is replaced, so the screen's markup is the same as before the move.
    @param {Element | null} root */
export function mountStatusDots(root) {
  if (!root) return;
  for (const ph of root.querySelectorAll("span[data-statusdot]")) ph.replaceWith(...statusDotNodes({ health: ph.getAttribute("data-statusdot") || "" }));
}
