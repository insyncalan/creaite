# creaite logo

**Decision (Alan, 12-10-2026): Stage.** A dashed draft behind, the solid record in front, the record carrying the c: creaite proposes, you approve, it becomes the record. Built in v1.7.0 as BL-272.

## Files

| File | What it is |
|------|------------|
| `creaite-icon-stage.svg` | The icon, 512 × 512: graphite `#18181B` tile, grey `#A1A1AA` dashed draft, saffron `#F2B544` record, graphite c |
| `creaite-icon-stage-small.svg` | The same at 32 px and below (favicon): the draft solid `#52525B`, no dashes, no c |
| `wordmark-paths.json` | BL-273: "creaite" in IBM Plex Mono 600 as outlined SVG paths (one per letter and the whole word), with the view box, advance, metrics and the Short-Stage layout. Made by `dev/tools/outline_wordmark.py` |
| `wordmark-preview.svg` | The wordmark: the solid word and the saffron bar, with no dashed draft copy (BL-308, 13-10-2026), cropped to them; colours are theme tokens (`--ink`, `--accent`), never hex |
| `OFL.txt` | The SIL Open Font License 1.1, under which IBM Plex is released |
| `canvas/` | The source of every exploration (one `.dc.html` per board, `canvas.json` the layout), as published |

## The explorations

The canvas, private to Alan: https://claude.ai/artifact/RkigC5p5wzn91rJiUR7i8j (if it can't be opened, `canvas/` holds the same boards).

- **Round one** (`Main`, `Approve`, `Stage`, `CreAIte`, `DayLine`, `Ledger`, `Health`): six directions away from the teal and the spark.
- **Round two** (`More`): ten more (Stamp, Bookmark, Ask, Two voices, Minutes, Compass, Modules, Brackets, Sunrise, Portfolio).
- **Round three** (`PM`): ten on project management and work items (Board, Gantt, Milestone, Checklist, RAID, Critical path, Burndown, Ticket, Due date, Workstreams).
- **Shortlist** (`Short-*`): Board, Ledger, Approve, Stage and creAIte, each hand-drawn, name-led and layered for macOS 26 (default, dark, tinted).

## Why (from the research, 12-10-2026)

- The AI sparkle has become a cliché that reads as "experimental feature"; the old icon's spark goes.
- AI and productivity brands are moving from cold minimalism to warmth and character (a meeting-notes product's hand-drawn letter mark is the nearest neighbour).
- Logos are systems: a core mark with a simple small size and a motion idea.
- macOS 26 builds icons from flat layers and adds the glass itself: Stage is three flat shapes, so it layers cleanly.

## Notes for later

- **Name-led wordmark** (Shortlist: Stage): "creaite" in IBM Plex Mono 600 and a saffron bar. Adopted as BL-273 (Alan, 12-10-2026; v1.7.0, sprint-ui-sweep) with a dashed draft copy offset behind the word; BL-308 (Alan, 13-10-2026; v1.9.0) removed that copy, leaving the word and the bar in every palette, light, dark and high contrast. The outlined paths are in `wordmark-paths.json`, and the rail draws them in place of the old `.logo` text. The icon (BL-272, Stage) keeps its dashed draft square.
- **Motion idea:** the draft square slides forward and turns solid saffron as the c draws in, for ask creaite's working state or a launch.
- **The dashboard's teal palette** (`data-palette="creaite"`, `--accent:#0B6E7F`) is separate from the icon and unchanged by BL-272; whether the creaite theme moves to graphite and saffron is a later decision.

## Licence (BL-273 wordmark)

The wordmark's outlined paths derive from IBM Plex Mono SemiBold (IBM Corp., Reserved Font Name "Plex"), under the SIL Open Font License 1.1 (`OFL.txt`). The shipped page contains the paths, not the font: no font file is committed or bundled. `dev/tools/outline_wordmark.py` downloads the pinned release (`@ibm/plex-mono@1.1.0`), checks its SHA-256 and outlines the word once, in development only (it needs fontTools, which nothing in `system/` uses).
