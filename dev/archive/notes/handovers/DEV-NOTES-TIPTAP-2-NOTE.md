# dev-notes-tiptap-2: BL-301 part A, the exact writer to 100%

For the Scrum Master. Branch `dev-notes-tiptap-2`, from `origin/main` on 13-10-2026. `dev/` only; nothing in `system/`. Follows `dev/DEV-NOTES-TIPTAP-NOTE.md` (the groundwork) and Alan's decisions in BL-301's write-up: a custom exact writer; creaite's Markdown style (`_italic_`, 2-space nesting); stored text never changes.

## Result

| Group | Upstream Tiptap 3.31.3 | Before (main's `--exact` prototype) | After (this branch) |
|---|---|---|---|
| Current states (sample vault) | 6 of 8 | 7 of 8 | **8 of 8** |
| Minutes texts | 25 of 25 | 25 of 25 | **25 of 25** |
| Hand-written constructs | 15 of 25 | 21 of 25 | **25 of 25** |
| Hard cases (new, `dev/tiptap/hard-cases.json`) | 29 of 69 | 24 of 57 (it can't run the 12 typed ones) | **69 of 69** |

Run it: `python3 dev/tools/tiptap.py fetch` once, then `python3 dev/tools/tiptap_roundtrip.py` (the exact writer is now the default; `--upstream` shows Tiptap's own output, `--group hard` one group, `--json` every in and out). It exits 1 on any failure, and also when the bundle's Tiptap isn't the pinned 3.31.3.

The 8 Current states are counted on main, where the template's guidance comment is still cut in two by the old `split_panes` (BL-310 is on `v19-integrate`, not main). Both halves pass, and so does the whole comment as BL-310 leaves it (hard case "template comment quoting the marker").

## Merged with Team 1's real-vault gate (`ebd2f70`)

The merge keeps both sides:
- **Team 1's options are kept:** `--vault DIR` (read-only), `--private` and `--json`.
- **The real vault uses this writer.** `--vault` runs the exact writer by default (`--upstream` for comparison), with the same version check.
- **`--private` compares against what each case must give back.** For a hard case that is its known loss, as the normal report does.
- **The tests are joined:** 18 in all (this branch's 13 and Team 1's 5). The faked `run` takes the new `mode` and `pinned` arguments.

**Sample-vault results.** I built a scratch vault from the repo's `projects/` and added six projects whose Current states are hard cases: the whole template comment, Windows line ends, entities, brackets in a link, and two panes that hold only an HTML comment (109 bytes, one-line and multi-line).

| Run | Exact writer | `--upstream` |
|---|---|---|
| `--vault <scratch> --private --json` | 10 of 10 | 4 of 10 |
| `--vault .` (the repo's own sample) | 2 of 2 | not run |

The upstream failures were an entity, the dropped comments, an escaped backtick and an escaped `[`.

**Comment-only panes (Team 1, 22:20).** On Alan's real Current states, main's prototype passed 3 of 4. The failure was a pane that is only an HTML comment (105 bytes), which came back empty. Alan decided comments are kept by a hidden node, byte for byte, which this branch already does (`htmlBlock`). Six hard cases now cover it:
- a one-line comment alone in a pane (~110 bytes), with and without a trailing line end;
- a multi-line comment alone, with and without a trailing line end;
- blank lines and then only a comment;
- a comment-only pane followed by the marker with nothing after it.

All six pass. So do the existing 105-byte case (main's cut template comment) and the scratch vault's two comment-only panes.

**`--exact` still works.** It is accepted as a no-op meaning the default, so Team 1's command line (`--vault DIR --private --exact --json`) runs this writer unchanged and should give 4 of 4 on the real data.

## How it works: no private patch

The prototype swapped `MarkdownManager.encodeTextForMarkdown`, a private method. That is gone. The writer now uses only public API:

- **`dev/tiptap/writer.js`, the writer.** It writes `editor.getJSON()` as Markdown itself; Tiptap's serialiser isn't used. Two rules:
  1. What was read is written back the way it was written.
  2. What is new is written in creaite's style, md_normalise's form: `_italic_`, `**bold**`, `- ` bullets, `1. ` numbers, nested items 2 spaces in, `### ` headings, `> ` quotes and blank lines between blocks. Text is written as it is, and escaped only where it would otherwise read differently.

  Every block is checked by parsing what was written (`editor.markdown.parse`, public) and comparing the content. If the check fails, the block is written again more cautiously: italic with `*`, then links in brackets, then escaped text. `writeMarkdown` returns `{markdown, faithful}`. `faithful` is false only when no way of writing the document reads back the same, for example two bullet lists side by side. The gate fails any case where `faithful` is false, even if the bytes match.
- **`dev/tiptap/source.js`, the written forms.** Each extension is an upstream one, made with `extend()`. It adds a document-only attribute (`rendered: false`) and a `parseMarkdown` that calls `this.parent` and then records the form. Two custom inline tokenizers and two new nodes use Tiptap's documented `markdownTokenizer` hook.
- **`dev/tiptap/editor.js`.**
  - It turns those extensions on in place of StarterKit's own.
  - It adds an **envelope**: the text's line ending, plus the blank lines and spaces before and after it. The document can't hold these, so they are kept around it.
  - `markdownOf(editor)` is the call BL-301's wrapper should make on save.
  - `fromHtml` writes typed content (HTML in, no written form), which is how the gate checks creaite's style for new text.

The parse side is still Tiptap's own. The gate is the check on a version move: the bundle reports the pinned version (`--define` in `tiptap.py bundle`), and the gate refuses to run against any other.

## Each failing case and its fix

| Case | Was | Fix |
|---|---|---|
| Template comment (left pane) | dropped | `htmlBlock` node. Its own block tokenizer keeps a comment verbatim, following CommonMark's type-2 HTML block: from `<!--` to the end of the line with the first `-->`, or to the end of the text if the comment never closes (main's cut half). |
| Italic with underscores | `_x_` became `*x*` | Italic keeps `delim` (`*` or `_`). New italic is `_`. If `_` can't work, for example inside a word, the check falls back to `*`. |
| Nested numbered list | 3-space indent | The writer indents everything inside an item by 2 spaces, whatever the marker. That is creaite's style, and it is also what Tiptap's own numbered-list reader takes off (it reads `1. a  \n   b` as " b"). |
| HTML comment | dropped, leaving an empty paragraph | `htmlBlock` (block) and `htmlInline` (inside a paragraph) keep it verbatim. The editor shows it as a read-only chip, with its text and never as markup. |
| Table (notes) | padded, with blank lines added | Table keeps `source`, the table's Markdown as written. While the table's content is unchanged (checked by parsing the source), the source is written back. Once a cell changes, the table is written fresh as `\| a \| b \|` / `\| --- \|`, with alignment kept. |
| Bare URL | `[url](url)` | Link keeps `form` (`bare`, `angle` or bracketed). A new link whose text is its own address is written bare. |
| `weekly_report_v2`, `Q&A`, `<`, `>`, lone `*` | escaped or entity-encoded | Text is written as it is. Escaping happens only when the check fails, and then only where needed: `_` between letters, `&` not before an entity, and `<` not before a tag all stay as they are. |
| `[[wiki link]]` | `\[\[…\]\]` | Text is written as it is, and the check confirms it reads back the same. |

Other forms the hard cases needed, each kept the same way:

- **HTML entities and backslash escapes.** A `literal` mark records the written form (`&amp;`, `\_`) and the character it gives. The mark isn't inclusive, so typing next to it never extends it.
- **Hard breaks.** HardBreak keeps `raw`: two spaces, a backslash, or more spaces.
- **Bold.** Bold keeps `delim` (`**` or `__`).
- **Code spans.** Code keeps `delim`: the backticks, and the space when one was taken off each end.
- **Bullets.** BulletList keeps the marker (`-`, `*` or `+`).
- **Numbered lists.** OrderedList keeps `.` or `)`.
- **Other HTML.** A block other than a comment comes from marked's `html` token. An inline tag such as `<b>`, `</b>` or `<br>` gets its own tokenizer, so `<b>x</b>` no longer becomes `**x**`.
- **Underline is switched off.** creaite's Markdown and the Word reports have no underline, and Tiptap's `++x++` syntax read "C++ and C++" as underlined text, dropping a space.
- **Trailing empty paragraphs.** Tiptap's TrailingNode adds one after a final list or table once the document is edited. The writer drops it, and the envelope keeps the original ending.

## The hard cases (`dev/tiptap/hard-cases.json`)

There are 69 cases, each with a `why`. JSON keeps CRLF and trailing spaces byte for byte.

**HTML and comments:**
- BL-89's pane marker between panes;
- the template comment whole (BL-310) and cut (main);
- a comment inside a paragraph, and one over several lines;
- block HTML, and inline tags.

**Links:**
- brackets in the text, and brackets in the address;
- a title;
- brackets that aren't a link;
- angle-bracket links, bare URLs, emails and `www.`.

**Line ends and spaces:**
- trailing-space and backslash hard breaks, and a soft break;
- Windows line ends;
- a trailing line end and spaces, a leading blank line, and trailing spaces before a blank line.

**Inline forms:**
- escapes and entities;
- italic inside a word;
- nested marks, both bold forms;
- code with backticks and spaces;
- "C++";
- Unicode.

**Lists:**
- numbers inside bullets, and three levels;
- a list starting at 3, and `1)`;
- `*` bullets;
- a numbered item over two lines, and items with two paragraphs;
- a paragraph after a list.

**Other blocks:**
- quotes over two paragraphs;
- every heading level;
- a fenced code block, a rule, and an empty paragraph;
- tables padded and aligned, without outer pipes, with `\|` and marks in cells, and between paragraphs;
- nested checklists.

**Typed content in creaite's style (12 cases, given as HTML):**
- `_italic_`, with `*` inside a word;
- bold, strike and code;
- a space moved outside a mark;
- nested numbers and bullets at 2 spaces;
- a link to itself written bare;
- Markdown-like text escaped minimally;
- a heading and a quote;
- a fresh table;
- a hard break.

**Known losses, gated as exactly what comes back:**
- **Mixed line ends** (some CRLF, some LF): they come back as LF. The document has no line end per line; the envelope keeps CRLF only when every line uses it.
- **A setext heading** (`Title` / `=====`): it comes back as `# Title`. The underlined form isn't recorded, and creaite never writes it.

## Still impossible, and why

- **Mixed line ends and setext headings**, as above. Both could be kept the way tables are, with a source attribute, if they ever matter. creaite writes neither.
- **Reference-style links** (`[x][ref]` with a `[ref]: url` line) aren't in the gate. marked resolves the definition and drops its line, so the link would come back inline and the definition line would be lost. creaite writes neither, and nothing in the sample vault uses them.
- **Two lists of the same kind side by side** (`- a`, blank line, `- b`) are one loose list in Markdown, whatever is written. If an edit makes the document hold two such lists, `faithful` is false: the wrapper should warn rather than save quietly. md_normalise already treats them as one list.
- **Loose lists** (blank lines between items) come back tight. Tiptap's list has no "loose" flag. md_normalise never writes loose lists, so no stored Current state has one.

## Bundle size

| Bundle | Raw | Gzipped |
|---|---|---|
| Before (main) | 499,751 bytes (488.0 KiB) | 157,509 bytes (153.8 KiB) |
| After (writer, source forms, HTML nodes) | 510,726 bytes (498.8 KiB) | 161,498 bytes (157.7 KiB) |
| Change | +10,975 bytes (+2.2%) | +3,989 bytes (+2.5%) |

## Tests

`dev/tests/test_tiptap_roundtrip.py` (Chrome tier) covers:

- the runner on a fake bundle: the mode is passed through, unfaithful cases fail, known losses and typed HTML are read, and a different Tiptap version fails loudly;
- the hard-cases reader, which keeps CRLF and trailing spaces;
- the hard-cases file itself: unique names, a why on every case, and the promised forms present;
- with the pinned Tiptap already in `dev/.cache`, the whole gate passing on the real bundle, and edits: an edited table is written fresh, new italic is `_` beside a kept `*`, and two side-by-side lists report `faithful: false`.

`test_tiptap_pin.py` is unchanged.

## For BL-301's build

- Use `markdownOf(editor)` (or `writeMarkdown(json, parser(editor))`) on save, with `envelope` and `wrap` around the editor's text. If `faithful` is false, say so before saving.
- The `htmlBlock` and `htmlInline` chips need styling, and a way to delete them. The pane marker stays a comment if the editor ever holds both panes.
- The picker nodes (`[[note]]`, `@person`, `#item`) should follow `source.js`'s pattern: a `markdownTokenizer` and a node. The writer needs one `case` for each.
- On any Tiptap version move, re-run the gate. It refuses a bundle whose version isn't `tiptap.PINNED`.

check.py: OK.
