// BL-301 A: the vendored Tiptap module (system/templates/vendor/tiptap/tiptap.module.js, built from dev/tiptap/editor.js
// by dev/tools/tiptap.py), imported by the dashboard's one editor (src/core/editor.js) as "tiptap". Loosely typed: the
// wrapper is the only module that imports it.
declare module "tiptap" {
  export const PINNED: string | null;
  export function createEditor(element: any, options?: any): any;
  export function envelope(text: string): { crlf: boolean, head: string, tail: string, inner: string };
  export function wrap(env: { crlf: boolean, head: string, tail: string, inner: string }, markdown: string): string;
  export function parser(editor: any): (md: string) => any;
  export function markdownOf(editor: any, json?: any): { markdown: string, faithful: boolean };
  export function roundTrip(markdown: string, features?: string, mode?: string): { markdown: string, faithful: boolean };
  export function fromHtml(html: string, features?: string, mode?: string): { markdown: string, faithful: boolean };
  export function roundTripAll(texts: string[], features?: string, mode?: string, html?: boolean): any[];
  export const Extension: any;
  export const Mark: any;
  export const Node: any;
  export function mergeAttributes(...attrs: any[]): any;
  export const Plugin: any;
  export const PluginKey: any;
}
