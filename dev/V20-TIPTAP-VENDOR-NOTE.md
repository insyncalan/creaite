# v20-tiptap-vendor: BL-301 part A, Tiptap bundled

For Team 1. Branch `v20-tiptap-vendor`, from `origin/main` on 14-10-2026. Item 12. Follows `dev/DEV-NOTES-TIPTAP-NOTE.md` ("What BL-301's build needs next", point 6) and `dev/DEV-NOTES-TIPTAP-2-NOTE.md` (the exact writer). **Nothing in the dashboard uses the editor yet.**

## What is vendored

`system/templates/vendor/tiptap/`, 41 files:

| File | What it is |
|---|---|
| `tiptap.module.js` | `dev/tiptap/editor.js` (with `writer.js` and `source.js`: the exact writer and the HTML-comment node) and everything it imports, as **one minified ES module**, es2020 |
| `licenses/` | 39 licence files: each bundled package's own, as shipped in its tarball (`@tiptap/pm` has two) |
| `manifest.json` | versions, hashes and licences (below) |

**Size:** `tiptap.module.js` is 510,584 bytes (498.6 KiB) raw and 161,406 bytes (157.6 KiB) gzipped. That is the size Alan accepted for BL-301.

**Exports:** `PINNED`, `createEditor`, `envelope`, `wrap`, `parser`, `markdownOf`, `roundTrip`, `fromHtml`, `roundTripAll`. BL-301's wrapper calls `markdownOf` on save.

**Determinism:** there are no absolute paths, times or source maps in the bundle. The same inputs give the same bytes on any machine. `--legal-comments=none` is used: the licences are the files in `licenses/`, not comments inside the bundle.

## The manifest (BL-239's form)

`manifest.json` holds:
- `tiptap`: `3.31.3`;
- `build`: esbuild `0.28.2`, the ESM format, the target, `minified`, the **SHA-256 of each `dev/tiptap/` source** it was built from, and the bytes and gzipped size;
- `exports`;
- `packages`: for each of the **38 packages esbuild actually put into the bundle**, read from esbuild's metafile:
  - its version;
  - its licence (from its `package.json`);
  - its tarball URL and SHA-256 (the same pins as `tiptap.py`'s `PACKAGES`);
  - its licence files;
- `files`: the SHA-256 of every other file in the folder.

A bundled package that isn't pinned is refused at build time.

## Licences

All 38 bundled packages are **MIT**:
- **Tiptap:** 22 `@tiptap/*` packages, including core, markdown, starter-kit, pm, table, list, link and image. They are © Tiptap GmbH, in `LICENSE.md`.
- **ProseMirror:** 11 packages: model, view, state, transform, tables, commands, keymap, history, dropcursor, gapcursor and schema-list. They are © Marijn Haverbeke. `@tiptap/pm` also ships `THIRD_PARTY_LICENSES.md`, which is kept as well.
- **marked:** 17.0.6. Its `LICENSE.md` also carries John Gruber's original Markdown notice.
- **Others:** linkifyjs 4.3.3, orderedmap, rope-sequence and w3c-keyname.

8 of the 46 pinned packages are not in the bundle, because nothing the editor imports reaches them, so they get no licence file:
- the bullet-list, ordered-list, list-item and list-keymap extensions (the editor imports `@tiptap/extension-list` itself);
- the dropcursor and gapcursor extensions;
- `prosemirror-changeset` and `prosemirror-inputrules`.

## How to rebuild

```
python3 dev/tools/tiptap.py fetch           # once per machine: the 46 pinned tarballs, each hash-checked, into dev/.cache
python3 dev/tools/tiptap.py vendor          # writes system/templates/vendor/tiptap/ (through a temp folder, renamed in)
python3 dev/tools/tiptap.py vendor --check  # rebuilds in memory, compares byte for byte, writes nothing (exit 1 if different)
```

Commit the folder whenever `dev/tiptap/*.js` changes, and on any Tiptap version move. A version move also needs the round-trip gate re-run, which refuses a bundle that isn't `PINNED`.

## The fresh-build check

There are three layers. None of them downloads anything.
1. **`dev/tools/check.py`, new hard check `VENDORED`.** It runs `tiptap.stale()`, which checks:
   - the folder against its manifest (every hash, nothing missing or extra);
   - each `dev/tiptap/` source against the hash it was built from. This catches a writer change without a rebuild even on CI, with no cache;
   - with the pinned packages already in `dev/.cache`, the folder against a full fresh build.
2. **`dev/tests/test_vendor_tiptap.py`** (quick tier, 12 tests):
   - hashes, pins, licences and the export list;
   - finding a changed, missing or extra file;
   - refusing a package that isn't pinned;
   - **`FreshBuild`**: the committed folder is byte for byte `vendor_files()`, and two builds are identical. This class is skipped cleanly when the cache isn't there (CI), as the existing round-trip tests are.
3. **`tiptap.py vendor --check`** by hand.

## The notes gate (stability)

Alan's decision is that Notes use Tiptap's own table and checklist form, gated on idempotence. There is a new gate group **`stable`** in `dev/tools/tiptap_roundtrip.py`, with its cases in `dev/tiptap/stable-cases.json`. Each case:
1. types a table or checklist through the editor's own commands, such as `insertTable`, `goToNextCell`, `addColumnAfter`, `deleteRow`, `setHardBreak`, `toggleTaskList`, `sinkListItem`, `liftListItem` and ticking with `updateAttributes`;
2. saves;
3. loads that save and saves again, twice.

A case passes when:
- all three saves are the same bytes;
- every save is faithful;
- the first save holds the creaite forms the case names.

Run it with `python3 dev/tools/tiptap_roundtrip.py --group stable`. It is also part of the default run.

### Results

| | Exact writer | Upstream `getMarkdown` (for comparison) |
|---|---|---|
| stable (17 cases: 8 tables, 8 checklists, 1 mixed note) | **17 of 17** | 14 of 17 |
| current, minutes, constructs, hard | 7/7, 25/25, 25/25, 69/69 (unchanged) | not run |

Upstream fails three cases:
- **A `|` in a cell.** Upstream writes it unescaped, so the next load **loses the rest of the cell**.
- **Two cases with an empty paragraph after a checklist.** The next load drops it, so the second save differs.

### Fixes the gate forced

Both fixes are in `dev/tiptap/`. They are small, and all 69 hard cases still pass.
- **Line break in a table cell.** Shift+Enter in a cell was written as `"  \n"`, which splits the row and isn't faithful. Now:
  - a break in a cell is written `<br>`;
  - `<br>` reads back as a hard break that keeps `raw: "<br>"` (`source.js` `HtmlInline`), so it is stable and faithful.

  Side effect: `<br>` elsewhere also loads as a real line break, not as a read-only HTML chip. It is still written back byte for byte, and the hard case `inline HTML tags` passes.
- **Empty paragraph straight after a list.** A list takes in the blank lines after it, so this paragraph could never be written. It was written as blank lines, lost on load, and the second save differed. The writer now leaves it out, as it already did for trailing empty paragraphs. The first save is then already the stable one. Empty paragraphs elsewhere (after a paragraph, a heading or a table) are kept as before.

### Known loss, gated

**A table with no header row.** A Markdown table always has a header, so the first row comes back as headers:
- the bytes are stable;
- the writer reports `faithful: false`;
- the case is marked `unfaithful`, so a change in this behaviour shows.

**For BL-301's wrapper:** the Notes insert menu should always insert a table with a header row (Tiptap's default).

## Tests

- `test_vendor_tiptap.py`: 12, all pass. The 2 fresh-build tests run here because the cache is present.
- `test_tiptap_roundtrip.py`: 26, all pass. 8 are new:
  - `stable_result` on its own (5);
  - the stable harness on a fake page, mixed with round-trip cases, including `--private` rows (1);
  - the `stable-cases.json` file (1);
  - `test_the_notes_gate_passes` on the real bundle (1).
- `test_tiptap_pin.py`, `test_update.py` and `test_portability.py` pass.
- `run_tests.py --quick -j 2`: 66 passed, 0 failed.

check.py: OK.
