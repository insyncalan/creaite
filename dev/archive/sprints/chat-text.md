# Sprint chat-text: ask creaite's suggestions, refusals in plain words, and formatted markdown everywhere (BL-199, BL-201, BL-196)

Branch `sprint-chat-text`, worktree `../creaite-chat-text`, from `main` after v1.5.1. **For v1.6.0**; `VERSION` changes only at the release. It runs beside `sprint-review-work`, which owns Review's project changes, the row click handlers and the context menu. This sprint owns ask creaite's input suggestions and refusal messages, and the markdown renderer. Both change `live_server.py`, in different functions: put new code in marked blocks. Read BL-199, BL-201 and BL-196 in `dev/BACKLOG.md` first.

## Order: one commit per item, each in a marked block (`/* ===== BL-1xx (sprint-chat-text) ===== */`)

1. **BL-199: ask creaite's suggestions never auto-select.** Enter sends what was typed unless a suggestion was chosen with the arrow keys; nothing is highlighted until then. Build it as BL-199 sets out (`acUpdate`, `acDraw`, `acKey`).
2. **BL-201: a refused command in plain words.** Build it as BL-201 sets out: `live_server.py`'s `refused_shape` gives one plain sentence per kind of refusal, and the page shows it instead of the raw `Refused: Bash {…}` text.
   - **The guard itself is unchanged** (BL-141's never list, the hook, the one-time approvals). Only the wording changes; prove it with `test_admin_card`, `test_reach` and `test_permissions`.
3. **BL-196: formatted text, never raw markdown.** Build it as BL-196 sets out:
   - start with its audit of every place that shows markdown;
   - use **one** renderer (extend the existing `mdHtml`/`mdInline` or `mdChat`; don't write a second), escaping before formatting so an HTML tag never runs;
   - links open safely; Copy still copies the original text;
   - begin with the release notes in Settings › creaite version › Review release.
4. **Docs:** Help and the guides, `dev/dashboard-spec.md`, a BUILD "Sprint chat-text" section with the FR text, and `dev/release-notes/1.6.0.md` (create it with a "# creaite 1.6.0 (Beta)" heading and a draft line, or add to it if `sprint-review-work` created it first).

## Rules

- **Look at it** in the real browser (`dev/tests/live_browser.py`, `dev/tools/cdp.py`) at 1400px and 1100px, light and dark, in two themes: ask creaite typing a command with suggestions showing; a refused request; release notes and one more markdown view. Keep the screenshots.
- **Tests:**
  - each item's "Touches" list;
  - then every test file that mentions ask creaite's input (`acKey`, `chIn`), refusals (`refused`, `denied`) or markdown (`mdHtml`, `mdChat`, `mdInline`), not a sample.

  One pass is enough; a file that fails under load and passes alone counts. Tests also run on GitHub's Linux runner: wait for conditions. Stop runs by their own process tree only; never `pkill` by name.
- **The usual edit rule:** don't edit `dev/BACKLOG.md`, `dev/BRD.md` or `dev/archive/sprints/STATUS.md`. No schema change. Never push or merge.
