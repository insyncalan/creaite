/* BL-231 step 3 (development only): types for tsc's checkJs over the dashboard's modules (dev/jsconfig.json).
   Nothing in system/ reads this file; esbuild never sees it.

   The page reads an event's target, and what $() or a query finds, as the element it is: e.target.closest("[data-id]"),
   $("#fsName").value. So both are typed as PageEl: an HTML input element (which has every member the page uses:
   value, checked, dataset, focus, select…) whose other members, including the page's own expandos (el._agH), are any. */
type PageEl = HTMLInputElement & { [key: string]: any };

/* Members an Element has as well are required; the others (an input's) are optional, so an element and an event's
   target can still be compared (document.activeElement === e.target). */
interface EventTarget {
  closest(selectors: string): PageEl | null;
  matches(selectors: string): boolean;
  readonly dataset?: DOMStringMap;
  readonly classList: DOMTokenList;
  readonly tagName: string;
  readonly parentElement: HTMLElement | null;
  readonly nodeType: number;
  readonly style: CSSStyleDeclaration;
  scrollTop: number;
  type?: string;
  getBoundingClientRect(): DOMRect;
  id: string;
  name?: string;
  value?: any;
  defaultValue?: string;
  checked?: boolean;
  disabled?: boolean;
  files?: FileList | null;
  textContent: string | null;
  selectionStart?: number | null;
  click?(): void;
  blur(): void;
  setAttribute(name: string, value: string): void;
  hasAttribute(name: string): boolean;
}

/* What a query finds is a PageEl too (el.querySelector(".x").focus(), the expandos the page keeps on elements). These
   overloads come before lib.dom's, so they are the ones used. */
interface ParentNode {
  querySelector(selectors: string): PageEl | null;
  querySelectorAll(selectors: string): NodeListOf<PageEl>;
}
interface Element {
  closest(selectors: string): PageEl | null;
}

/* An element the page holds (document.activeElement, an observer's entry.target, a text area it sizes) is an HTML
   element, and may carry the page's expandos (el._agH, d._mt: a name starting "_"). */
interface Element {
  readonly offsetParent: Element | null;
  readonly offsetWidth: number;
  readonly offsetHeight: number;
  readonly isContentEditable: boolean;
  readonly style: CSSStyleDeclaration;
  focus(options?: FocusOptions): void;
  blur(): void;
  [expando: `_${string}`]: any;
}
/* A node the page walks (a TreeWalker's text nodes) is a child node; relatedTarget is a node or null. */
interface Node {
  replaceWith(...nodes: (Node | string)[]): void;
  remove(): void;
  contains(other: EventTarget | null): boolean;
}
/* The File System Access API (Chrome and Edge; lib.dom doesn't have it yet): the vault folder picker. */
interface Window {
  showDirectoryPicker(options?: { id?: string; mode?: "read" | "readwrite"; startIn?: any }): Promise<any>;
}
/* Names the page reaches as window properties, by design. */
/** settings.js puts an accessor for the Settings category on window (BL-115); core/nav.js sets it by name. */
declare var STAB: any;
/* What the page makes is a PageEl too: document.createElement("div") may become the page's #dateHint. */
interface Document {
  createElement(tagName: string, options?: ElementCreationOptions): PageEl;
}
/* isNaN(date) is the page's test for an invalid Date (it converts the Date to its time value). */
declare function isNaN(value: number | Date): boolean;
