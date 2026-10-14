// @ts-check
/* StatusDot (BL-256, dev/COMPONENTS.md): a project's health as its icon and its word, never colour alone. The first
   component: it draws exactly the markup core/page.js's health() writes, so a screen that moves to it looks the same. */
import { render } from "preact";
import { HEALTH_SHAPES, hk } from "../core/page.js";

/** @typedef {{health?: string}} StatusDotProps */

/** One health marker: `<span class="health h-ok">` with the health's icon and its word ("Not set" when there is none).
    @param {StatusDotProps} props */
export function StatusDot({ health }) {
  const k = hk(health);
  return (
    <span class={`health h-${k}`}>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
        {HEALTH_SHAPES[k].map(([tag, attrs]) => tag === "circle" ? <circle {...attrs} /> : <path {...attrs} />)}
      </svg>
      {health || "Not set"}
    </span>
  );
}

/** Put a StatusDot in place of each `<span data-statusdot="…">` inside `root` (the health is the attribute's value).
    The placeholder is replaced, so the screen's markup is the same as before the move.
    @param {Element | null} root */
export function mountStatusDots(root) {
  if (!root) return;
  for (const ph of root.querySelectorAll("span[data-statusdot]")) {
    const box = document.createElement("span");
    render(<StatusDot health={ph.getAttribute("data-statusdot") || ""} />, box);
    ph.replaceWith(...box.childNodes);
  }
}
