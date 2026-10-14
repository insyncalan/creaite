# UI sweep audit (prepares `sprint-ui-sweep`: BL-216, BL-217, BL-270, BL-273)

Read-only audit, 12-10-2026, on `main` at `4ce2e06`. Nothing in the product was changed. Measured in headless Chrome
(`dev/tools/cdp.py`) against the live server on the snapshot sample vault (`test_snapshots.Snapshots`: fixed day 09-10-2026
09:00, UTC, en-GB), plus a calendar read the evening before so Today shows its band, three meetings and the calendar note.
Screens are reached the way `test_snapshots.SCREENS` reaches them, plus Work's Board and Work's Display menu. Default
palette (`creaite`, light) unless a section says otherwise. CSS line numbers are `system/templates/dashboard.html` at `4ce2e06`.

## Totals

| Check | Result |
|-------|--------|
| **1. Targets under 24×24** (BL-216) | 1,215 controls measured on 23 screen states. **96 groups** (screen × selector) are under 24×24: **4 fail** (no exception applies), **70 pass only by WCAG 2.2's spacing exception**, **22 are inline links in a sentence** (exempt). No rail or header control is under 24×24. |
| **2. Reflow** (BL-217) | The document never scrolls sideways: the overflow lands in the `.view`, which scrolls instead. **320 px:** 10 screens scroll sideways inside the view (1 to 161 px; Work in all three states), **6 have controls covered by another**, **2 have controls that can't be reached**. **640 px:** no sideways view scroll; 4 screens still have a control covered (Work, Review, People, person). **900 px:** clean apart from the Display menu over the table (expected) and People's cue. The rail stays 72 px at every width. 14 tables and strips scroll inside their own box (acceptable for data tables, listed). |
| **3. Forced colours** (BL-217) | No `forced-colors` or `prefers-contrast` rule in the stylesheet. **12 selected states disappear** (tabs, chips, segmented switches, ⌘K's highlighted row, rail current page), **9 control types lose their edges** (a box drawn only with a background), **4 colour-only markers vanish** (2 measured, 2 found in the CSS). Focus rings survive almost everywhere (the global `:focus-visible` is an `outline`); **1 control has no focus indicator** in forced colours (`#cmdkIn`). Transparent borders turn visible, so every Work tab looks selected. |
| **4. Header** (BL-270, BL-273) | `.logo` is styled in **13 rules**: the base rule, the compact-rail rule and 11 palette rules covering **all nine palettes** (BL-273 says seven: Retro Arcade and Thermo Scan also restyle it, with their own tokens). The `.logo` sits at the top of the **rail**, not in `header.bar`. BL-270 touches `renderDay`'s calendar note, `dcLine`, the `renderToday` wrapper and `.dayband`. |

**Three worst problems**
1. **Review at 320 and 640 px:** the sticky first column plus the "more columns →" cue (`.xcue .xmore`) cover the item text and the Approve, Reject, Edit and Project buttons (12 covered at 320, 5 at 640). Bulk approval by mouse is unusable in a narrow window. `worst-320-review.png`.
2. **Selected state lost in forced colours on every tab strip and chip row** (Work's tabs, saved views, Status filter, List/Board, Files quick filters, Intake chips, Help, Settings, People, the peek, Activity, Milestones' Plan/Internal, ⌘K): they show selection only with a background or a coloured border, and the transparent underline on unselected tabs turns black, so all tabs look selected. `worst-forced-work-tabs-chips.png`.
3. **Today at 320 px:** the attention list's "Draft weekly report" button (`.rmgo .rmrun`) sits over the item's title, which wraps one word a line underneath it. `worst-320-today-attention.png`. Close behind: the project page's footer clips "Draft weekly report" off its left edge under the rail (`.cockfoot`, `justify-content:flex-end` overflowing), `worst-320-cockpit-foot.png`.

---

## 1. Targets smaller than 24×24 (BL-216, WCAG 2.5.8)

How: every visible `a[href]`, `a[data-go]`, `button`, `input`, `select`, `textarea`, `summary`, ARIA widget role, positive
`tabindex` and contenteditable, plus each topmost element with a pointer or resize cursor (the page's delegated click
targets). Controls hidden until hover (opacity 0, such as the ▾ editors) are counted. A tick box inside a `<label>` is
measured by the label. **Spacing** = the 24 px circle round the target's centre touches no other target and no other small
target's circle (WCAG 2.2's exception), measured at 1400 px wide; narrower windows bring targets closer, so treat
"spacing" rows as the first to recheck. **Inline** = a link inside a sentence (exempt).

**Shared fix pattern** (keeps the look, BL-216): give the control a transparent hit area of at least 24×24, either
`position:relative` plus `::before{content:"";position:absolute;inset:50% auto auto 50%;width:24px;height:24px;transform:translate(-50%,-50%)}`
(min-size 24) or padding with a matching negative margin. For tick boxes, wrap in or extend the `<label>`/cell to 24×24
(`td.actck label`, `.rgroup h2 label`). Don't change row heights.

### Fail: no exception applies (4)

| Screen | Selector | Size (px) | What it is | Suggested fix (rule to change) |
|---|---|---|---|---|
| Work (list), Display menu open | `#workTbl .ce button.cebtn[data-ce]` | 11.3×15 (×10; hidden until row hover) | ▾ value editor for owner, due, priority, status | `.cebtn` (l.601): `min-width:24px;min-height:24px;padding:4px 6px;margin:-4px 0 -4px 0` or a 24×24 `::before`. It touches the owner link, so both fail. |
| Work (list) | `#workTbl .ce a.plink2[data-person]` | 21.3×20 ("You") | Owner name link next to its ▾ | Fixed with the ▾ above (gap ≥ 24 px centre to centre), or `a.plink2{display:inline-block;min-width:24px;min-height:24px}` in `.ce` cells. |
| Work, Display menu | `#dispMenu .colmv button[data-mv]` | 20×20 (×10) | Move column earlier / later | `.colmv` (l.613): `gap:4px` and `.colmv button{min-width:24px;height:24px}` (or keep 20 drawn, 24 hit area). |
| Review | `#reviewBody button.ib.sm.no.rvrr[data-act]` | 22×28 (×3) | "Reject with a reason" ▾, abutting Reject | `.ib.rvrr` (l.1586): `width:24px;margin-left:0` (it has `width:22px;margin-left:-2px`). |

### Pass only by the spacing exception (70 groups, 68 selectors)

| Screen | Selector | Size (px) | What it is | Suggested fix |
|---|---|---|---|---|
| Today | `#nMine a.cntl[data-nav]` | 8.3×16 | Count "1" link in the My work heading | `a.cntl` (l.1878): `display:inline-block;min-width:24px;min-height:24px;text-align:center` where it stands alone (`#nMine`, `.num`) |
| Today | `#dayMeets .dm button.linkbtn.preplink[data-prep]` | 23.5×20 (×3) | "Prep" under each meeting | `.preplink` (l.1001): `min-height:24px;padding:2px 4px` |
| Today | `#dayMeets .tt span.pcode.plink[data-proj]` | 96–104×17 (×3) | Project name chip after a meeting title | `.pcode` (l.642): `line-height:24px` or `padding:3px 0` on `.plink` |
| Today | `#hSetup button.linkbtn.setupx`, `#setupList .rmgo button.linkbtn` | 54×20, 35×20 | Getting started "Dismiss", "How" | `.linkbtn` (l.611): `min-height:24px` (applies everywhere linkbtn is used) |
| Today | `#attnList .tb a.t[data-go]`, `a.t[data-cock]`, `#attnList button.qa`, `#attnMore button.qa`, `#hMine a[data-go]`, `#chgMore a.s` | 20 high | Attention titles, "Approve 1 routine", "+1 more", "All mine", "See all activity" | `.tbrief .qa` (l.558) and the `.tb a.t`/`a.s` links: `display:inline-block;min-height:24px;line-height:24px` |
| Work (list, board) | `#wapplied .fchip button[data-clr]` | 20×14 | Remove-filter ✕ | `.fchip button` (l.668): `min-width:24px;min-height:24px` (draw the ✕ at 12 px) |
| Work (list, board) | `button#clearF` | 52×20 | "Clear all" | `.linkbtn` min-height as above |
| Work (list) | `#workTbl span.colrz` | 8×32 (×5) | Column resize handle (keyboard route exists) | `.colrz` (l.857): `width:12px;right:-6px` gives 24 between columns only with a wider `::before`; or accept: keyboard alternative already meets 2.5.8's "equivalent" exception. At 900 px with the Display menu open 2 of 5 lose spacing |
| Work (list) | `#workTbl .late button.cebtn`, `.prio-urgent button.cebtn` | 11.3×15 | ▾ on due and priority (alone in their cell) | Same `.cebtn` fix as the failing row |
| Work, Display menu | `button#dispReset` | 154×20 | "Reset to this tab's default" | `.linkbtn` min-height |
| Work (board) | `#workBoard .bch button.bcoll[data-bcoll]` | 22×22 (×5) | Collapse a board column | `.bcoll` (l.940): `width:24px;height:24px` |
| Work (board) | `#workBoard .bcm button.bmv` | 24×22 (×3) | Move card to… | `.bmv`: `height:24px` |
| Peek | `#pkId a.hlink[data-proj]` | 113×20 | Project link in the peek's ID line | `a.hlink`: `display:inline-block;min-height:24px;line-height:24px` |
| Review | `#reviewBody input.rgtick[data-rg]` | 13×13 (×2) | Select every row in a group | `.rgroup h2 .rgtick` (l.921): wrap in a 24×24 `label` or `width:18px;height:18px` plus a 24×24 label hit area. **Most used bulk control: fix even though it passes** |
| Review | `#reviewBody input[type=checkbox]` (row ticks) | 13×13 (×4) | Select one proposal | Make the first cell the label: `td:first-child label{display:grid;place-items:center;min-width:24px;min-height:24px}` |
| Review | `#reviewBody a.linkbtn.mhlink[data-meeting]`, `.why button.linkbtn[data-drrisk]` | 17–20 high | "Meeting page", "Draft a response" | `.linkbtn` min-height |
| Intake | `#mtgBody input[data-mi]`, `#inboxTbl input[type=checkbox]` | 13×13 (×3, ×3) | Select a meeting / a file | Same as Review row ticks |
| Intake | `button#inboxPick` | 77×20 | "choose files" | `.linkbtn` min-height |
| Intake, person, Today | `span.pcode.plink[data-proj]` | 104×17 | Project chip | `.pcode` as above |
| Files | `#filesTbl a[data-openfile]` | 78–173×20 (×6) | File name link | `#filesTbl a{display:inline-block;min-height:24px;line-height:24px}` |
| Activity | `#actTbl .actck input[type=checkbox]` | 16×16 (×11) | Select a change to undo | `#actTbl td.actck input` (l.1663): keep 16 drawn, wrap in a 24×24 label (the cell is already 30 wide) |
| Project page | `#v-cockpit .card button.pencil[data-edcur]`, `[data-edproj]`, `.pencil.second[data-gen]` | 22×22 | Edit / generate current state, edit health | `.pencil` (l.659): `padding:5px` (24×24) |
| Project page | `#v-cockpit .crumb a[data-go]`, `#csHead button.cstbtn`, `a.hlink[data-nav]`, `.card a.seeall`, `#undatedCard a.seeall` | 19–20 high | Breadcrumb, rename title, "All … ›" links | `.crumb a`, `.cstbtn`, `a.seeall`: `display:inline-block;min-height:24px;line-height:24px` |
| Project page | `#flowCard g.flk[data-nav]` | 16×18 (smallest bar) | Chart bar links | Give each `g.flk` a transparent `rect` at least 24 high behind the bar |
| Milestones | `#mvPlanCard .mv-strip button.mv-mk[data-mvedit]` | 22×22 | Milestone marker on the strip | `.mv-mk` (l.1923): `width:24px;height:24px` (markers sit far apart) |
| Milestones, person | `.crumb a[data-go]`, `.crumb a[data-proj]` | 20 high | Breadcrumb | `.crumb a` min-height 24 |
| People, Settings › People | `#peopleTbl .num a.cntl[data-nav]`, `#peopleMgr .num a.cntl` | 7×20 (×4, ×3) | Count links ("1") | `.num a.cntl{display:inline-block;min-width:24px;min-height:24px;text-align:center}` |
| People | `#peopleTbl .title a.plink2[data-person]` | 50–101×20 | Person name link | `a.plink2` min-height 24 |
| Person | `#v-person a.cntl[data-nav]`, `.pplinks a[data-seeall]` | 18–20 high | Count link, "See all actions in Work ›" | as above |
| Help | `#helpPane a[data-help]` | 226×20 | "How-to ›" link | `min-height:24px` |
| Settings (General, Work, Health, Capture, System) | `input.switch` (all) | 40×22 (×37) | On/off switches | `.switch`: `height:24px` (knob unchanged), or a 24 high label row |
| Settings › Work | `#set-todaypage .wapl input[data-wap]` (via label) | 45–67×18 (×4) | Week ahead list ticks | `.wapl label{min-height:24px;display:inline-flex;align-items:center}` |
| Settings › System | `#advCard summary` | 1025×21 | "Advanced" disclosure | `summary{min-height:24px}` |
| ask creaite | `div#chGrip` | 8×913 | Resize the panel (pointer only) | `#chGrip`: `width:12px` with an invisible 24 px `::before`; keyboard alternative if there isn't one |
| ask creaite | `#chLog .msg button.msgcopy` | 27×22 (hover) | Copy the reply | `.msg .msgcopy` (l.1481): `height:24px` |

### Inline links (exempt, 22 groups)

Not to change: `#briefText a.cntl`, `#mineList`/`#weekList`/`#attnList` title and project links in sentences, `#pfTbl`/`#projTbl .ev a.cntl`, `#workTbl .x a.rowid` (the ID line), Review's `.why` source and person links, Activity's `.actchg a.hlink`, `#v-person .sub a` (email), the peek's source link. They are 17 to 21 high.

---

## 2. Reflow at 320, 640 and 900 px (BL-217, WCAG 1.4.10)

How: the window set to each width (800 high), each screen opened afresh, then: the document's and the `.view`'s sideways
scroll; the elements that run past the view's right edge outside an inner scroller (the cause); inner scrollers; text cut
by `overflow:hidden` without an ellipsis (none found); and, for each control, scrolled to the centre, whether
`elementFromPoint` hits it (covered) and whether an `overflow` ancestor clips its centre (unreachable).

**General fix (all screens):** `.view` and its grid children need `min-width:0`; fixed minimum widths need `min()`:
`minmax(min(300px,100%),1fr)`. Collapse the rail under 480 px (`@media (max-width:480px){:root{--rail-w:48px}}` reuses
`.rail.icons`, l.1626–1630, or a top bar). Inner table scrollers are acceptable (data tables are exempt from 1.4.10).

| Screen | 320 px | 640 px | 900 px | Cause (selector) and suggested fix |
|---|---|---|---|---|
| Today | No scroll. **4 covered:** two attention titles under "Draft weekly report" (`#attnList .rmgo button.rmrun`) | Clean | Clean | `.rmgo` (l.1515) is `margin-left:auto;flex:none`: let the attention row wrap (`flex-wrap:wrap`, `.rmgo{flex-basis:100%}` under 480 px) so the button goes below the title. `#pfTbl` scrolls inside its box (529 px). |
| Work (list) | **View scrolls 41 px:** `#wtabs` (fourth tab "All items" runs 41 px off). 4 resize handles under the "more columns →" cue | 1 handle under the cue | Clean | `.tabs` (l.645): `overflow-x:auto` or `flex-wrap:wrap`. `.xcue .xmore` (l.1603) covers `.colrz`: put the cue below the header row (`top:36px`) or give it `pointer-events:none` except on its own text. |
| Work, Display menu | **41 px**, and `#dispMenu` (340 wide) runs 29 px past the window | Menu covers the table (expected) | Same | `#dispMenu`/`.dispmenu`: `max-width:calc(100vw - var(--rail-w) - 16px);right:0` |
| Work (board) | **41 px** (tabs) | Clean | Clean | Same `.tabs` fix. The board scrolls inside `#workBoard` (expected). |
| Peek | Clean (full width under 600 px) | Clean | Clean | — |
| Review | No view scroll. **12 covered:** the "more columns →" cue covers Approve, Reject, Edit, Project and Hide its items; the sticky first column leaves ~100 px for the text | **5 covered** (Approve, Reject) | Clean | `.tbl.xstick` first column (l.1606) and `.xcue .xmore` (l.1603). Under 700 px, drop the table for stacked rows (title, meta, then the action buttons on their own line), or at least move the cue out of the row area. **Worst case.** |
| Intake | No view scroll; `#mtgBody` (769) and `#isecUp` (629) tables scroll inside | Same | `#mtgBody` still scrolls 189 | Acceptable; consider stacking `.mtgtbl` rows under 640 px. |
| Files | **View scrolls 161 px:** `#tree` is 384 wide in a one-column grid | Clean | Clean | `.files` (l.738) becomes `1fr` under 1100 px but `.tree` keeps content width: `.tree{min-width:0;max-width:100%}` and `.tree button{overflow-wrap:anywhere}`. |
| Activity | **View scrolls 59 px:** `#actTools .actdates` (282 wide). 6 links covered by the next span in `.actchg` | Clean | Clean | `.actdates` (l.1659): `flex-wrap:wrap`. |
| Projects | No view scroll; `#projTbl` scrolls inside (547) | Inside (227) | Clean | Acceptable. |
| Project page | **View scrolls 92 px:** `#flowCard .flgrid figure.flc` (300 min), `.flfoot` (52), `.pswitch` (5). **Unreachable:** "Draft weekly report" in `.cockfoot` is clipped off the left edge | Clean (`#mvCard` strip scrolls inside) | Same | `.flgrid` (l.1221): `minmax(min(300px,100%),1fr)`. `.cockfoot` (l.638): `flex-wrap:wrap` (with `justify-content:flex-end` an overflowing flex row spills off the start, where it can't be scrolled to). `.pswitch select{max-width:100%}`. |
| Milestones | **5 px:** `.mv-pageh .pswitch` | Clean (strip scrolls inside) | Same | `.pswitch` as above. |
| People | No view scroll. 7 sort headers under the cue | 1 under the cue | 1 under the cue | `.xcue .xmore` as for Work. |
| Person | **37 px:** a `#v-person` header row (260 wide). 4 sort headers under the cue | 2 under the cue | Clean | Let the person header wrap (`flex-wrap:wrap;min-width:0`). |
| Help | **3 px:** `.hp-steps .hp-step` (230 min) | Clean (`.hp-phrases` table scrolls inside) | Clean | `.hp-steps` grid: `minmax(min(230px,100%),1fr)`. |
| Settings › General, Health | Clean | Clean | Clean | — |
| Settings › Work | **12 px:** `#set-views .srow` | Clean | Clean | `.srow`: `flex-wrap:wrap;min-width:0`. |
| Settings › Capture | **7 px** (a row in `#set-sweep`) | Clean | Clean | `.srow` as above. |
| Settings › People | No view scroll; `#peopleMgr` (677) and `#wsMgr` (454) tables scroll inside | Inside | Inside (321, 98) | Acceptable. |
| Settings › System | **1 px:** `#suCard .srow`. `#liveCard .cmdbox code` scrolls inside (840) | Inside | Inside | `.srow` as above; `code{overflow-wrap:anywhere}` in `.cmdbox`. |
| ⌘K | Clean (dialog 286 wide) | Clean | Clean | — |
| ask creaite | Clean (panel full width) | Clean | Clean | — |

The rail is 72 px at every width (22% of a 320 window). The header bar wraps to two rows at 320 px (search, then ask
creaite and the theme switch), which pushes Today's band down 44 px but cuts nothing off.

Not counted (false positives checked by hand): `#advRows` controls in Settings › System measured as "unreachable" are
inside the closed Advanced `<details>`; `#dispMenu .dprops` inputs are visually hidden behind their labels.

---

## 3. Forced colours (`Emulation.setEmulatedMedia forced-colors: active`, BL-217)

How: on each screen, before and after forcing colours, each control's edges (borders that draw), visible background,
shadow and outline; each control focused with keyboard modality (`:focus-visible` confirmed) to see whether focus changes
an outline or border; each selected element (`aria-current`, `aria-selected`, `aria-pressed`, `.on`) compared with a
sibling of the same kind; and small no-text markers drawn only with a background. Forced colours replace backgrounds
with Canvas and drop `box-shadow`, so anything drawn only that way disappears.

**General fix:** add one block, as BL-217 says:
```css
@media (forced-colors: active){
  button,.btn,.vchip,.fsel,.seg button,.ib,input,select,textarea{border:1px solid ButtonText}
  [aria-selected="true"],[aria-pressed="true"],[aria-current="page"],.fsel.on{forced-color-adjust:none;background:Highlight;color:HighlightText;border-color:Highlight}
  .tabs button{border-bottom-color:Canvas} .tabs button[aria-selected="true"]{border-bottom-color:Highlight}
  .rail button[aria-current="page"]::before{forced-color-adjust:none;background:Highlight}
  .spark i,.chs .dot,.rail .badge,.ib .dot{forced-color-adjust:none}
}
```
(Check each against its own markup; the tab and chip rows below are the ones that need it.)

### Selected state lost (12)

| Screen | Selector | What it is | Why it disappears | Suggested fix |
|---|---|---|---|---|
| Every screen (rail) | `.rail button[aria-current="page"]::before` (l.494, plus palette rules l.72, 247, 299, 410, 468) | Current-page bar | Bar is a background; only the icon's colour is left | `forced-color-adjust:none;background:Highlight` on the `::before` |
| Work | `#wtabs button[aria-selected]` (`.tabs button`, l.646–647) | Actions / RAID / Decisions / All items | Selected = coloured underline; the unselected `2px solid transparent` turns CanvasText, so **every tab looks selected** | `.tabs button{border-bottom-color:Canvas}`, selected `Highlight` |
| Work | `#wviews .vchip[aria-pressed]` (l.650) | Saved view chips | Selected = filled background | `Highlight` background, as in the block |
| Work | `button#stBtn.on` (`.fsel.on`, l.610) | Active filter button | Accent border and soft background | `border:2px solid Highlight` |
| Work | `#wlay button[aria-pressed]` (`.seg button`, l.882) | List / Board switch | Filled background only (both icons look the same) | as the block |
| Peek | `#pkTabSel[aria-selected]` (`.pk-tabs`, l.1783) | Activity tabs in the peek | Underline/background | as `.tabs` |
| Intake | `#mtgChips .vchip[aria-pressed]` | All / New / With transcript | as `.vchip` | as `.vchip` |
| Files | `#fquick .vchip[aria-pressed]` | Quick filters | as `.vchip` | as `.vchip` |
| Activity | `#actTabCh[aria-selected]` | Changes / Quality tabs | as `.tabs` | as `.tabs` |
| Milestones | `#mvVPlan`, `#mvAInt[aria-pressed]` | Plan / Changes, Client / Internal switches | as `.seg` | as `.seg` |
| People, Help, Settings | `#ptabs`, `#htab-start`, `#setcats button[aria-selected]` | Page tabs | as `.tabs` | as `.tabs` |
| ⌘K | `#cmdkList button[aria-selected]` (l.853) | Highlighted result | Soft background only: the keyboard position is invisible | `outline:2px solid Highlight;outline-offset:-2px` |

### Control edges lost (9)

| Screen | Selector | What it is | Suggested fix |
|---|---|---|---|
| Rail | `#inboxBadge`, `#revBadge` (`.rail .badge`, l.495) | Count badges (the digit stays, the red disc goes) | `forced-color-adjust:none` or `border:1px solid CanvasText` |
| Work | `#wlay button` (`.seg.ico button`, l.1568) | List / Board icons | `border:1px solid ButtonText` |
| Work | `button#newBtn` | "+" new item | same |
| Files | `#tree button` (l.740) | Tree rows (selected row's tint) | selected: `outline:2px solid Highlight` |
| Project page, Milestones | `.mv-mk.achieved` (l.1924) | Achieved marker disc | `border:1px solid ButtonText` |
| Milestones | `#mvVPlan`, `#mvAInt` | Segmented switches | as `.seg` |
| ⌘K | `#cmdkList button` | Result rows | covered by the selected fix |
| ask creaite | `button#chSend` | Send (filled accent) | `border:1px solid ButtonText` |
| Review | `span.tag.stale` (l.922) | "Stale" tag tint (text still says Stale: low) | `border:1px solid CanvasText` |

### Focus

The global `:focus-visible{outline:3px solid var(--focus)}` (l.483) survives forced colours, and `.actsearch:focus-within`
(l.1657) covers `#actQ`. **One control fails:** `#cmdkIn` (l.850) has `outline:0` and shows focus only by the caret;
give it `outline:2px solid Highlight;outline-offset:-2px` under forced colours (it is the dialog's only field, so low).
No focus ring drawn with `box-shadow` alone was found on the screens audited.

### Colour-only markers (4)

| Screen | Selector | What it is | Suggested fix |
|---|---|---|---|
| Today, Projects, project page | `.spark i.s-warn` / `.s-bad` / `.s-ok` (l.641) | Health trend bars | `forced-color-adjust:none` (heights already differ, so shape carries it once visible) |
| ask creaite | `#chSub .dot` (`.chs .dot`, l.790) | Live/offline status dot (text beside it) | `forced-color-adjust:none` or `border:1px solid CanvasText` |
| Peek | `.pkstage .dot` (l.1759) | "Staged" dot (from the CSS; not on the sample screens) | same |
| Buttons with counts | `.ib .dot` (l.1554) | Count bubble on icon buttons (from the CSS; e.g. Work's filter count) | same |

---

## 4. The header (BL-270, BL-273)

### Where `.logo` is styled (for BL-273)

The `creaite` text is `<div class="logo">` at the top of the **rail** (`nav.rail`, l.2199), not in `header.bar` (which
holds search, ask creaite and the theme switch). Measured in each palette at 1400 px: always 15 px, 15 high, 45 to 65
wide in a 72 px rail (48 px in icon mode). None of the palette fonts is loaded (the page loads no web fonts), so each
falls back to the system font.

| Palette | Rule (line) | What it sets | Light / dark colour |
|---|---|---|---|
| base | `.logo` (488) | `font:700 15px/1 var(--font);color:var(--accent);margin:4px 0 14px` | — |
| Brightwater | `:root[data-palette="Brightwater"] .logo` (68) | 500, -.01em, `--ink` | #1E1F1E / #F8F8FF |
| creaite (default) | (106) | `--display` font, 800, -.02em (accent from base) | #0B6E7F / #5FC4D6 |
| Notion | (146) | 700, -.025em, `--ink` | #000000 / #F5F4F2 |
| Linear | (196) | 600, -.02em (accent) | #4D58C0 / #828FFF |
| Cursor | (244) | 400, -.02em, `--ink` | #26251E / #F2F1EA |
| Claude | (296) | 600, -.01em (accent) | #9C4E35 / #E08F72 |
| Apple | (346) | `--display`, 600, -.02em, `--ink` | #1D1D1F / #F5F5F7 |
| Retro Arcade | (403 font, 406) plus tokens `--arcade-logo`, `--arcade-red` (373, 383, 390) | `--mono`, 800, `text-shadow:2px 2px 0 var(--arcade-red)`, `color:var(--arcade-logo)` | #0000FF / #FFFF00, red shadow |
| Thermo Scan | (462 font, 465) | `--mono`, 700, +.02em, `--accent` | #1D3BD1 / #FFC800 |
| compact rail | `.rail.icons .logo` (1630) | `font-size:11px;margin-bottom:12px` | — |

**For the build:**
- Replace the **nine** palette rules (BL-273 lists seven; ask Alan whether Retro Arcade and Thermo Scan keep their own
  type) and lines 403 and 462's `.logo` selectors; keep the base rule for size and margin only.
- Keep the `.logo` element and class: `test_rail_customise.py` (l.272) right-clicks `.rail .logo`, and line 2493 puts the
  development `DEV` tag inside it (`insertAdjacentHTML("beforeend", …)`), so the SVG must go in as a child, not replace
  the div.
- Width: Plex Mono 600 at 15 px is about 63 px for seven letters, plus the dashed copy's offset; that fills a 72 px rail
  (60 px buttons). Size the SVG `width:min(60px,calc(var(--rail-w) - 12px));height:auto` so the 48 px icon rail
  (`:root.railicons`) still fits (the 11 px rule at l.1630 becomes a width).
- Forced colours: the dashed copy and the saffron bar need `forced-color-adjust:none` or `CanvasText`; BL-273 already
  says to hide the dashed copy in high contrast.
- BL-254's snapshots capture each view's region, not the rail, so no golden changes for the header; a new rail check is
  needed for "every palette, light, dark and high contrast".
- `dev/reference/logo/` has the icon SVGs but no `creaite-wordmark.svg` yet.

### What BL-270 changes on Today

Measured with a calendar read yesterday (so the note shows) and the day not closed:

| Width | `.dayband` | "Close the day" (`#dayClose button`) | Calendar note (`.daynote`) |
|---|---|---|---|
| 1400 | 72,53 → 1327×539 | 100×32 at the brief's foot (x 224, y 249), its own row | Last line of the band (y 551) |
| 900 | 827×560 | 100×32 (y 249) | y 572 |
| 640 | 567×686 | 100×32 | y 698 |
| 320 | 247×1035 (header wraps, band starts at y 97) | 100×32 (y 475) | y 1091, after 456 px of meetings |

- **Remove:** `dcLine()` (l.11176) and the `renderToday` wrapper that inserts `<div class="dayclose" id="dayClose">`
  after `#briefText` (l.11205); `.dayclose` CSS (l.2158). `openClose`, `dcDraw` and ⌘K's entry (l.11206) stay.
- **Move:** the "Calendar as read on …" line from the end of `#dayMeets` in `renderDay` (l.3176) to a footnote at the
  bottom right of `#v-today`; the two other `.daynote` lines (no calendar yet, l.3172–3173) are not this note and stay.
- **Add:** a round icon button at the bottom right of `.dayband` (l.528 needs `position:relative`; the 640 px rule at
  l.569 changes the band's side padding to 16 px, so the button's `right` should follow it). The `door` icon in `ICONS`.
  The button must be at least 24×24 (BL-216; 32×32 matches the other icon buttons) with the `:focus-visible` outline,
  which survives forced colours; the nudge dot and the "closed" accent colour need `forced-color-adjust:none` or a
  non-colour cue (BL-217).
- At 320 px the band is 1035 high: a bottom-right button sits under the meetings, far from the brief it replaces;
  worth Alan's look before merge.

---

## Screenshots

In the session scratchpad,
`/private/tmp/claude-502/-Users-alan-carter-dev-env-creaite/788877a6-fe65-4e01-aa02-50131a306a3c/scratchpad/audit/shots/`
(not committed):

- `worst-320-review.png`: Review, the "more columns" cue over the items and actions.
- `worst-320-today-attention.png`: Today, "Draft weekly report" over a one-word-a-line title.
- `worst-320-cockpit-foot.png`: project page, the footer's first button clipped under the rail.
- `worst-320-files.png`: Files, the tree wider than the window.
- `worst-320-work-display-menu.png`: Work's Display menu wider than the window.
- `worst-forced-work-tabs-chips.png`: forced colours, every Work tab underlined and no selected chip.
- `worst-forced-today-rail.png`: forced colours, the rail's current page shown only by the icon colour.
- `today-header-{1400,900,640,320}.png`: Today's header today, for BL-270.
- All screens: `reflow-{320,640,900}-<screen>.png` and `forced-<screen>.png`.

The measuring scripts (`lib.py`, `probe.js`, `run.py`) and raw results (`result-*.json`) are beside the screenshots in
`…/scratchpad/audit/`; `probe.js` is the start of BL-216's and BL-217's tests (size with the spacing rule, sideways
scroll per view, forced-colour state comparison).
