# #341 item 17: where amber is used today

Draft for Alan, 25-10-2026. Nothing is changed by this list; amber is the last step of release 2.6.5 and has its own commit after Alan agrees this list.

**Summary**

1. Amber (`--warn`) is used in 126 places. Each row is one rule (some set both a fill and a text colour); the Palettes row stands for about 27 definition lines.
2. Rule from Alan: amber means "at risk" and nothing else. Health At risk, at-risk milestones and the health trend keep it.
3. Keep: 16. Teal (needs you or needs approval): 45. Neutral: 57. Neutral with a lock icon: 2. Red (error or fault): 6.
4. Most "caution" notes become a neutral note with an icon and the reason in words. Age and stale become muted text with the days in words.
5. The two literal #B54708 fallbacks go. Uses shown as "(set in this release)" were added in the side-tab commit and carry the old tone until amber is done.

**Count by recommendation**

| Recommendation | Rows |
|---|---|
| Keep amber (at risk) | 16 |
| Change to teal (needs you) | 45 |
| Change to neutral with icon or words | 57 |
| Change to neutral chip with lock icon | 2 |
| Change to red (error) | 6 |
| Total | 126 |

Line numbers are in `system/templates/dashboard/style.css` unless a file is named. Recommendations: "Keep" stays amber; "teal" uses the accent colour; "neutral" uses the muted or ink colour with an icon or words so meaning never rests on colour. Where a row says "caution", check what the screen shows at build time and say so in the release notes.

## Shell and rail

| Where | What it shows | Current meaning | Recommendation |
|---|---|---|---|
| style.css:1935 | Count badge on a rail item | A Health problem needs a look | Change to red (error) |
| style.css:1947 | Second line under "Settings and health" when a problem exists | A Health problem | Change to red (error) |

## Today

| Where | What it shows | Current meaning | Recommendation |
|---|---|---|---|
| style.css:4156 | Bar that says the daily sweep is due | Needs Alan to run it | Change to teal (needs you) |
| style.css:667 | Chip on a day-view meeting action | Needs doing | Change to teal (needs you) |
| style.css:702 | "High" priority word in the brief | High priority (not risk) | Change to neutral with icon or words |
| style.css:4064 | Dot before a High priority item in the brief | High priority (not risk) | Change to neutral with icon or words |
| style.css:4073 | Count that links to Work, in warning tone | Something needs a look | Change to teal (needs you) |
| style.css:3141 | "Chase" background on a relation line | A chase is due | Change to teal (needs you) |
| style.css:2811 | Dot on the calendar button | Calendar data needs a refresh | Change to teal (needs you) |
| style.css:2813 | Calendar footer, old data | Data is old | Change to neutral with icon or words |

## Today and Work

| Where | What it shows | Current meaning | Recommendation |
|---|---|---|---|
| style.css:3164 | Small tag with warning tone | Needs attention | Change to teal (needs you) |
| style.css:3176 | Bordered "why" line, warning tone | Why an item is flagged | Change to teal (needs you) |
| style.css:4068 | "Why" line text, warning tone | Why an item is flagged | Change to teal (needs you) |

## Projects and cockpit

| Where | What it shows | Current meaning | Recommendation |
|---|---|---|---|
| style.css:743 | Health word and icon "At risk" | Health At risk | Keep amber (at risk) |
| style.css:810 | Bar in the six-week health trend | Health At risk that week | Keep amber (at risk) |
| style.css:818 | Dot in the health trend tip | Health At risk that week | Keep amber (at risk) |
| style.css:2552 | Health suggestion chip, warning | Suggested health is At risk | Keep amber (at risk) |
| style.css:2969 | Round icon, warning tone | Health At risk | Keep amber (at risk) |
| style.css:1510 | Dependency warning line | A dependency is due after the milestone it blocks (milestone at risk) | Keep amber (at risk) |
| style.css:1510 | Milestone row background when at risk (set in this release) | Milestone at risk | Keep amber (at risk) |
| style.css:782 | "Generate is off" notice under Current state | Caution | Change to neutral with icon or words |
| style.css:793 | Notes under a drafted Current state | Checks on the draft | Change to neutral with icon or words |
| style.css:1506 | Flow chart: closed bars, ageing bucket 2 and High priority mix | Chart tones, not risk | Change to neutral with icon or words |

## Milestones

| Where | What it shows | Current meaning | Recommendation |
|---|---|---|---|
| style.css:2360 | State word "At risk" | Milestone at risk | Keep amber (at risk) |
| style.css:2362 | Tag with warning tone | Milestone warning | Keep amber (at risk) |
| style.css:2420 | Suggestion text under a date | A suggested date | Change to teal (needs you) |
| style.css:2467 | Dot for a status change in the milestone log | Status changed | Change to neutral with icon or words |
| style.css:2517 | Note: state differs from what the dates suggest | Caution | Change to neutral with icon or words |
| style.css:2576 | Border and halo of the Internal view card | Internal view | Change to neutral with icon or words |
| style.css:2577 | "Internal view" pill | Internal view | Change to neutral with icon or words |
| milestones.js:204 | Icon for the At risk state | Milestone at risk | Keep amber (at risk) |

## People

| Where | What it shows | Current meaning | Recommendation |
|---|---|---|---|
| style.css:4298 | Star by a followed person | Followed person | Change to teal (needs you) |
| style.css:846 | Flag "needs details" on a person row | Missing details | Change to teal (needs you) |
| style.css:1069 | Required mark in the person form | Field is required | Change to neutral with icon or words |

## Work and peek

| Where | What it shows | Current meaning | Recommendation |
|---|---|---|---|
| style.css:2312 | Note box in the work peek | Caution | Change to neutral with icon or words |
| style.css:2313 | Icon in that note | Caution | Change to neutral with icon or words |
| style.css:2315 | Line in the peek popup | Caution | Change to neutral with icon or words |
| style.css:2071 | Peek note box | Caution | Change to neutral with icon or words |
| style.css:2073 | Peek warning line | Caution | Change to neutral with icon or words |
| style.css:796 | Evidence line with a caution | Caution | Change to neutral with icon or words |
| style.css:833 | Tag: needs details, waiting on, client messaging to complete | Needs you | Change to teal (needs you) |
| style.css:1518 | Tag "sensitive change" | A sensitive change | Change to neutral chip with lock icon |
| style.css:1525 | Approval-card row for a sensitive change (fill, border, left edge) | A sensitive change | Change to neutral chip with lock icon |
| PeekProps.jsx:20 | Colour of the Delayed status | Delayed action | Keep amber (at risk) |
| PeekProps.jsx:26 | Colour of High priority | High priority (not risk) | Change to neutral with icon or words |

## Review and Intake

| Where | What it shows | Current meaning | Recommendation |
|---|---|---|---|
| style.css:1131 | "Stale" tag on a row | Age | Change to neutral with icon or words |
| style.css:1133 | Age text on an old item | Age | Change to neutral with icon or words |
| style.css:1134 | Banner: this suggestion is old | Age | Change to neutral with icon or words |
| style.css:1137 | Count tiles with a warning | Needs you | Change to teal (needs you) |
| style.css:1209 | Confirm bar on a meeting | Needs Alan to confirm | Change to teal (needs you) |
| style.css:910 | Line that asks for an individual check | Needs you | Change to teal (needs you) |
| style.css:2157 | Pill for a suggestion state | Needs approval | Change to teal (needs you) |
| style.css:2246 | Suggestion card needing a check | Needs you | Change to teal (needs you) |
| style.css:2253 | "Needs you" words on a card | Needs you | Change to teal (needs you) |
| style.css:2272 | Flash when a card lands (start colour) | Needs you | Change to teal (needs you) |
| style.css:2273 | Flash when a card lands (reduced motion) | Needs you | Change to teal (needs you) |
| style.css:1719 | Flash when a card lands (motion off) | Needs you | Change to teal (needs you) |
| style.css:4217 | Group heading "needs" in Intake | Needs you | Change to teal (needs you) |
| style.css:4236 | Note after Process drafted nothing | Caution | Change to neutral with icon or words |
| style.css:4243 | Icon of the "Suggestions to check" stage | Needs you | Change to teal (needs you) |
| style.css:2131 | Dot on a peek tab | Unsaved or pending | Change to teal (needs you) |
| style.css:2295 | Card that asks Alan something | Needs you | Change to teal (needs you) |
| style.css:4257 | Changed-field chip | Changed by a suggestion | Change to teal (needs you) |
| style.css:4258 | Changed-field chip on hover | Changed by a suggestion | Change to teal (needs you) |
| style.css:4260 | New text in an update diff | Changed by a suggestion | Change to teal (needs you) |
| style.css:4261 | Pending field in the peek | Waiting for approval | Change to teal (needs you) |
| style.css:4262 | New description in an update | Changed by a suggestion | Change to teal (needs you) |
| style.css:2543 | Loosely matched words in a draft | Loose match | Change to neutral with icon or words |
| style.css:2544 | "Loose match" tag | Loose match | Change to neutral with icon or words |
| style.css:3424 | Single follow-up flag | Needs a follow-up | Change to teal (needs you) |

## Minutes

| Where | What it shows | Current meaning | Recommendation |
|---|---|---|---|
| style.css:3666 | Priority "High" in the minutes table | High priority (not risk) | Change to neutral with icon or words |
| style.css:3658 | Pill: something to check | Needs you | Change to teal (needs you) |
| style.css:3616 | Wavy underline on a word to check | Needs you | Change to teal (needs you) |
| style.css:3617 | Same, on a button | Needs you | Change to teal (needs you) |
| style.css:3669 | Bar: items need attention | Needs you | Change to teal (needs you) |
| style.css:3670 | Filter chip for flagged items | Needs you | Change to teal (needs you) |
| style.css:3671 | Filter chip pressed | Needs you | Change to teal (needs you) |
| style.css:3672 | Small flag pill | Needs you | Change to teal (needs you) |
| style.css:3683 | Check verdict "some to check" | Needs you | Change to teal (needs you) |
| style.css:3694 | Highlighted transcript words | Highlight | Change to neutral with icon or words |
| style.css:3701 | Bold label in the approve list | Items to check | Change to neutral with icon or words |
| style.css:3703 | Check box before approving | Needs you | Change to teal (needs you) |
| style.css:3598 | Paper sheet remaps amber to its own paper tone | Follows the others | Change to neutral with icon or words |

## Reports

| Where | What it shows | Current meaning | Recommendation |
|---|---|---|---|
| style.css:3904 | Dot for an amber health flag in the weekly report menu and popup | Health At risk | Keep amber (at risk) |
| style.css:3956 | Icon in the health menu, amber tone | Health At risk | Keep amber (at risk) |
| style.css:3577 | Health flag on the report sheet, warning | Health At risk | Keep amber (at risk) |
| style.css:3539 | Wavy underline on a claim in the report sheet | Claim to check | Change to neutral with icon or words |
| style.css:2591 | Dashed underline on a claim with no source | No source | Change to neutral with icon or words |
| style.css:2592 | Marker before the first such claim | No source | Change to neutral with icon or words |
| style.css:3486 | Note in the report bar | Internal note | Change to neutral with icon or words |
| style.css:3499 | Report checks box | Checks | Change to neutral with icon or words |
| style.css:3501 | Report note box | Note | Change to neutral with icon or words |
| style.css:3576 | Reader notes list | Notes | Change to neutral with icon or words |
| style.css:2928 | Checks list, warning line | Checks | Change to neutral with icon or words |
| style.css:3849 | Client report note | Note | Change to neutral with icon or words |
| style.css:3970 | Chip in the Reporting hub, warning | Report needs a look | Change to teal (needs you) |
| style.css:3991 | Flag on a report thumbnail: Internal | Internal | Change to neutral with icon or words |
| style.css:2675 | Guessed value underline in the reference row | Guess | Change to neutral with icon or words |
| style.css:2676 | Reason under that guess | Guess | Change to neutral with icon or words |
| style.css:2683 | Cell that differs in the lessons table, and the words "differs" | Difference | Change to neutral with icon or words |
| style.css:2684 | Decision tag in warning tone | A decision waits | Change to teal (needs you) |

## Notes

| Where | What it shows | Current meaning | Recommendation |
|---|---|---|---|
| style.css:3256 | Conflict marker in the notes list | Save conflict | Change to red (error) |
| style.css:3286 | "Internal" tag in a note header | Internal only | Change to neutral with icon or words |
| style.css:3297 | Save state when waiting, conflict or error | Save problem | Change to red (error) |
| style.css:3302 | Banner that a note is out of date | Stale | Change to neutral with icon or words |
| style.css:3328 | Dot in a note chip, warning | Caution | Change to neutral with icon or words |

## Prep page

| Where | What it shows | Current meaning | Recommendation |
|---|---|---|---|
| style.css:2853 | Chip "needs" on the prep page header | Needs you | Change to teal (needs you) |
| style.css:2854 | Dot in that chip | Needs you | Change to teal (needs you) |

## Prep page (prep_page.py)

| Where | What it shows | Current meaning | Recommendation |
|---|---|---|---|
| prep_page.py:523-545 | Own palette: the Internal badge, the warning box and the health word | Internal, caution and At risk | Change to neutral with icon or words |

## Help

| Where | What it shows | Current meaning | Recommendation |
|---|---|---|---|
| style.css:1269 | Help page amber accent variables | Help warning accents | Change to neutral with icon or words |

## Ask creaite

| Where | What it shows | Current meaning | Recommendation |
|---|---|---|---|
| style.css:1023 | Warning words on a refused step (with the literal fallback #B54708) | A refused action | Change to neutral with icon or words |
| style.css:1024 | Border of a refused answer (with the literal fallback #B54708) | A refused answer | Change to neutral with icon or words |

## Search

| Where | What it shows | Current meaning | Recommendation |
|---|---|---|---|
| style.css:1106 | Highlighted match in the people picker | Highlight | Change to neutral with icon or words |

## Errors

| Where | What it shows | Current meaning | Recommendation |
|---|---|---|---|
| style.css:2301 | Error banner fill | An error | Change to red (error) |
| style.css:2303 | Error banner icon | An error | Change to red (error) |

## Settings and Health

| Where | What it shows | Current meaning | Recommendation |
|---|---|---|---|
| style.css:1903 | Result word in the checks list (warning) | A check passed with a warning | Change to neutral with icon or words |
| style.css:542 | "pending" in the status line | Items waiting for approval | Change to teal (needs you) |
| style.css:2702 | Usage budget bar when near the limit | At risk of going over budget | Keep amber (at risk) |
| style.css:2697 | Usage change that went up | An increase (not risk) | Change to neutral with icon or words |
| style.css:2699 | Axis fill in the usage chart | Chart tone | Change to neutral with icon or words |
| style.css:2700 | Line in the usage chart | Chart tone | Change to neutral with icon or words |
| style.css:1224 | Question line under a row | Caution | Change to neutral with icon or words |
| style.css:1226 | Warning flag icon with help | Caution | Change to neutral with icon or words |
| style.css:1227 | Warning note line | Caution | Change to neutral with icon or words |

## Shared notes (set in this release)

| Where | What it shows | Current meaning | Recommendation |
|---|---|---|---|
| style.css:4390 | Icon of caution notes | Caution | Change to neutral with icon or words |

## Palettes

| Where | What it shows | Current meaning | Recommendation |
|---|---|---|---|
| style.css:16-473 | The amber colour and its soft fill, defined once per palette and mode (about 27 lines, not uses) | The one amber token | Keep amber (at risk) |
