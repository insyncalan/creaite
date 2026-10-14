// @ts-check
import { render } from "preact";
import { Icon } from "./Icon.jsx";
/* Chip (BL-256, dev/COMPONENTS.md §3): a small labelled value, such as a meeting's date, its project or who is invited, or a
   state ("Minutes made"). As a span it states something; with `name` the span reads its name before its value (visually
   hidden). As a button (`onClick` or `button` given) it carries its full name (`name`, aria-label) and the dashboard's tooltip
   (`tip`, else its name, as data-tip, which keyboard users and screen readers also get). Tones: ok, warn, mute, cta (a quiet
   pill that lifts on hover), plan (cta in the accent colour). Extra classes: `cls` or `className`. Text goes through JSX
   only. First used by the Prep popup (BL-286) and Today's day band (BL-293); the two were joined on release-190. */

/** @typedef {{icon?: string, tone?: string, tip?: string, name?: string, cls?: string, className?: string, disabled?: boolean,
    button?: boolean, onClick?: (e: MouseEvent) => void, children?: import("preact").ComponentChildren} & Record<string, any>} ChipProps
    `button`: a button even without `onClick` (a page-wide click handler acts on its data- attribute). */

/** One chip: `<span class="chip ok">Minutes made</span>`, or a `<button class="chip cta">` when it does something.
    @param {ChipProps} props */
export function Chip({ icon, tone, tip, name, cls, className, disabled, button, onClick, children, ...rest }) {
  const c = ["chip", ...(tone || "").split(" ").filter(Boolean), cls, className].filter(Boolean).join(" ");
  const inner = <>{icon ? <Icon name={icon} /> : null}{children}</>;
  if (!onClick && !button) return <span class={c} data-tip={tip} {...rest}>{name ? <span class="vh">{name}: </span> : null}{inner}</span>;
  return <button type="button" class={c} aria-label={name} data-tip={tip || name} disabled={disabled} onClick={onClick} {...rest}>{inner}</button>;
}

/** Draw a Chip into `host` (the block's own test, and old code that wants one).
    @param {Element} host @param {ChipProps} props */
export function drawChip(host, props) {
  render(<Chip {...props} />, host);
}
