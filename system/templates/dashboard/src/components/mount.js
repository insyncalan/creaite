// @ts-check
/* mount (BL-256, dev/COMPONENTS.md §1 and §6): put one component into an element: the way an area mounts a screen into its
   container, and the way each building block's own Chrome test mounts it on a small fixture (dev/tests/test_block_*.py).
   Rendering again with new props redraws in place. */
import { h, render } from "preact";

/** @param {any} Component @param {Record<string, any>} props @param {Element} el */
export function mount(Component, props, el) { render(h(Component, props), el); return el; }
