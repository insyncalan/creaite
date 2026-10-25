# dev-notes-tiptap: BL-301 part A groundwork

For the Scrum Master. Branch `dev-notes-tiptap`, from `origin/main` on 13-10-2026. `dev/` only; nothing in `system/`.

**Followed by `dev/DEV-NOTES-TIPTAP-2-NOTE.md`** (branch `dev-notes-tiptap-2`): the exact writer replaces the `--exact` prototype below, with no private patch, and the gate passes every case (8 of 8, 25 of 25, 25 of 25, and 69 of 69 new hard cases).

## What is here

- `dev/tools/tiptap.py`: the pinned Tiptap, like `esbuild.py`. `fetch` downloads every npm tarball in `PACKAGES` (the whole dependency tree, resolved once and written in the script), checks each against its SHA-256 and unpacks it to `dev/.cache/tiptap/3.31.3/node_modules/`. A wrong hash, a link, an absolute path or `..` in a tarball is refused and nothing is written; a package counts as unpacked only with its stamp file, written last. `bundle` runs the pinned esbuild (`--tsconfig-raw={}`, `NODE_PATH` at the cache) and prints the size. No npm or Node at build time.
- `dev/tiptap/editor.js`: the minimal editor entry (`createEditor`, `roundTrip`, `roundTripAll`), with two feature sets: `current` (StarterKit, Image, Markdown) and `notes` (adds TaskList, TaskItem and TableKit). It also holds a prototype "exact" serialiser (below).
- `dev/tools/tiptap_roundtrip.py`: the gate. It runs in headless Chrome through `cdp.py` (no jsdom) and exits 1 on any failure. Use `--json` for every in and out, and `--exact` for the prototype.
- Tests: `dev/tests/test_tiptap_pin.py` (quick tier) covers a hash refusal with a faked download, a good unpack, a half-unpacked package and unsafe tarballs. `dev/tests/test_tiptap_roundtrip.py` (Chrome tier) runs the gate's runner on a fake bundle and reads the corpus from fixtures.

## Versions chosen and why

- **Tiptap 3.31.3** (all `@tiptap/*`, including `@tiptap/markdown`), published 04-09-2026. 3.31.4 (30-09-2026) is under two weeks old today, and 3.32.0 came out today.
- I resolved the tree once with `npm install --package-lock-only --before=2026-09-29`, so every package is at least two weeks old. That gives 46 tarballs: 28 `@tiptap/*` (core, pm, starter-kit, markdown, extension-image, extension-table and StarterKit's extensions), 13 ProseMirror packages (model 1.25.12, view 1.42.6, state 1.4.4, transform 1.12.2, tables 1.8.5 and others), marked 17.0.6, linkifyjs 4.3.3, orderedmap, rope-sequence and w3c-keyname. The newest are prosemirror-view, prosemirror-transform and prosemirror-changeset, from 25-09-2026.
- Each tarball was checked against the registry's `dist.integrity` (sha512) before its SHA-256 was written into the script.

## Bundle size

| Bundle | Raw | Gzipped |
|---|---|---|
| `dev/tiptap/editor.js` (current and notes feature sets: StarterKit, Markdown, Image, task lists, tables) | 499,751 bytes (488.0 KiB) | 157,509 bytes (153.8 KiB) |
| StarterKit and Markdown only | 441,652 bytes (431.3 KiB) | 139,490 bytes (136.2 KiB) |

Both are one minified IIFE (`var CreaiteTiptap=(()=>{…})()`, es2020). BL-301 asks for one ESM file in `system/templates/vendor/`, which is the same build with `--format=esm`. Today's whole dashboard page is the scale to compare against: this bundle adds about half a megabyte to it raw.

## Round-trip result (upstream 3.31.3, unpatched)

**Sample vault:** current 6 of 8 pass, minutes 25 of 25 pass. **Constructs:** 15 of 25 pass. 12 cases fail in all.

- Every real sample text passes: the ABC project's two panes, the four demo projects' Current states and every minutes text (demo minutes and the `test_minutes_review` fixture).
- The two failing sample cases are the new-project template. The others are constructs I added, to name each Markdown form Current state can hold; the sample vault doesn't use them yet.

Failing cases and why:

1. **Template, left pane.** `project-CLAUDE-template.md` has a guidance HTML comment that quotes the marker `<!-- creaite: second pane -->` inside it, so creaite's own `split_panes` cuts the comment in two. This is a creaite bug, not a Tiptap one, and every new project's Current state starts this way. Tiptap then drops the HTML block entirely (item 10).
2. **Template, right pane.** This is the second half of that comment, so it comes back with its backtick escaped (`` \` ``) and `-->` encoded as `--&gt;` (items 6 and 7).
3. **Italic with underscores.** `_x_` comes back as `*x*`. Italic always renders with `*`. creaite's own reader accepts both forms.
4. **Nested numbered list.** The nested item comes back indented 3 spaces instead of md_normalise's 2. Tiptap aligns a nested item under the text after `1. `.
5. **Bare URL.** `https://…` comes back as `[https://…](https://…)`. marked's GFM autolink parses it as a link, and the link renderer always writes the bracket form.
6. **Underscores in a word.** `weekly_report_v2` comes back as `weekly\_report\_v2`. The serialiser backslash-escapes every `` \ ` * _ [ ] ~ `` in text, whether or not it is needed.
7. **Ampersand.** `Q&A` comes back as `Q&amp;A`. Every text node is HTML-entity encoded (`&`, `<`, `>`); this is `MarkdownManager.encodeTextForMarkdown`. This is the serious one, because any Current state with "&", "<" or ">" would change.
8. **Less-than and greater-than** come back as `&lt;` and `&gt;`, for the same reason as 7.
9. **Lone asterisk.** ` * ` comes back as ` \* `, for the same reason as 6.
10. **HTML comment.** It is dropped and leaves an empty paragraph (`\n\n` before the text). There is no HTML-block node in the schema.
11. **Table (notes).** The serialiser pads the columns to equal width and adds a newline before and after the table. That doesn't matter for Current state (no tables); for Notes, Tiptap's form becomes the stored form on first save.
12. **Wiki link (notes).** `[[Stakeholder map]]` comes back as `\[\[…\]\]`, for the same reason as 6. The `[[` picker needs its own node with a Markdown tokenizer.

The parse side is right in every case: the document holds `Q&A`, `a_b_c` and the others correctly. All the failures are on the serialising side, apart from items 1 and 10.

**Prototype, `--exact`** (in `dev/tiptap/editor.js`, not upstream): this writes text as it is, parses the result again and falls back to upstream's escaping only if the document would change. It also writes a link whose text is its own address back as a bare URL. With it, current is 7 of 8, minutes 25 of 25 and constructs 21 of 25. Items 2 and 5 to 9 pass, and so does 12. Items 1, 3, 4, 10 and 11 still fail. It works by swapping a private method, so it is tied to the pinned version.

## Alan's decisions (13-10-2026)

1. **Escaping: the custom writer.** Keep `dev/tiptap/editor.js`'s exact serialiser, not a one-time rewrite of every Current state. It's tied to the pinned version, so re-run the round-trip gate on every Tiptap upgrade.
2. **The template bug: the pane splitter ignores a marker inside a comment.** `split_panes` must not cut at `<!-- creaite: second pane -->` when it sits inside another HTML comment. That fixes existing projects as well as new ones. It's a small fix to do now, separately from BL-301; laptop 2 is taking it on.
3. **Italic and nested numbering: teach the writer creaite's style.** Write `_italic_` and 2-space nested numbers, so stored text never changes. No one-time conversion.

## What BL-301's build needs next

1. **Decide the serialising fix**, because the gate cannot pass on upstream alone:
   - either adopt the exact serialiser (a small custom MarkdownManager subclass, or an upstream fix if one lands, re-tested on each version move);
   - or accept a one-time normalisation of every Current state into Tiptap's form, which BL-301's "byte for byte" rules out as written.
2. **Fix the template** so the comment doesn't quote the marker, or so `split_panes` ignores a marker inside a comment. Then decide how Current state treats HTML comments: strip them on load as guidance, or add a Tiptap node that keeps them.
3. **Italic and nested numbers:** either canonicalise in `md_normalise` (italic to `*`, nested numbered items to 3 spaces), which is a one-time byte change to stored texts with Alan's agreement, or extend Italic and OrderedList so they render creaite's forms.
4. **Custom nodes for the pickers:** `[[note]]`, `@person` and `#item` chips, each with a Markdown tokenizer and renderer, added to the gate's constructs. Also the BL-207 claim mark, and the pane marker if the editor is to hold both panes.
5. **Notes' stored form:** accept Tiptap's table and checklist output as canonical and gate Notes on idempotence (save, load and save again gives the same bytes), not on hand-written input.
6. **Vendoring:** build ESM into `system/templates/vendor/` with this tool, add it to the vendor manifest (BL-239) and add a check that the committed file matches a fresh build. Run the gate in CI (the Chrome tier) once it passes.
7. Run the gate over Alan's live Current states on laptop 1 before the switch: the sample vault's texts are short and plain, so they prove little on their own.
   The gate does this read-only: `python3 dev/tools/tiptap.py fetch`, then `python3 dev/tools/tiptap_roundtrip.py --vault <copy of the vault> --private --exact` (add `--json` for the rows). `--private` prints only ids (`ABC pane 1`), pass or fail, byte lengths and, for a failure, the byte offset, construct and kind of change, never the text.

check.py: OK.
