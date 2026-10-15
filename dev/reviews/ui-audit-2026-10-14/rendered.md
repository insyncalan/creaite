# Rendered UI audit

432 page renders (12 pages × 18 theme modes × 2 widths). Real viewports: 1400x1000 → 500px minimum for the phone pass, 390x844 → 500px minimum for the phone pass.

## Distinct rendered values across pages (Brightwater / light / 1400x1000)

| Property | Distinct | Most used |
|---|---|---|
| color | 6 | `rgb(30, 31, 30)` ×356, `rgb(92, 93, 96)` ×291, `rgb(179, 38, 30)` ×17, `rgb(122, 79, 0)` ×10 |
| background | 14 | `rgb(255, 255, 255)` ×170, `rgb(217, 217, 224)` ×30, `rgb(30, 31, 30)` ×20, `rgb(233, 255, 204)` ×19 |
| border-color | 5 | `rgb(217, 217, 224)` ×158, `rgba(0, 0, 0, 0)` ×36, `rgb(30, 31, 30)` ×11, `rgb(46, 107, 58)` ×4 |
| font-size | 27 | `12px` ×195, `14px` ×189, `13px` ×129, `15.04px` ×22 |
| font-weight | 5 | `400` ×425, `500` ×199, `700` ×46, `600` ×14 |
| font-family | 5 | `"ABC Diatype"` ×553, `"Source Sans 3"` ×58, `"JetBrains Mono"` ×41, `"Schibsted Grotesk"` ×36 |
| line-height | 25 | `20px` ×439, `16px` ×56, `18px` ×30, `23.312px` ×22 |
| radius | 12 | `6px` ×88, `4px` ×70, `1px` ×32, `5px` ×23 |
| shadow | 0 |  |
| spacing | 32 | `8px` ×335, `12px` ×315, `6px` ×156, `4px` ×90 |

## Same control, different look (one class, more than one rendered style)

A class drawn two ways on different pages is drift; one drawn two ways on one page may be a state.

- **button**: 15 classes, 31 rendered styles; 8 classes drawn more than one way
  - `button`: 5 styles
    - `14px | 500 | "ABC Diatype" | 0px | 38px | 8px 12px | none | normal` on activity, help, people, work
    - `13px | 400 | "ABC Diatype" | 0px | 30px | 0px 0px | none | normal` on work
    - `14px | 400 | "ABC Diatype" | 0px | 26px | 6px 6px | none | normal` on work
    - `13px | 500 | "ABC Diatype" | 6px | 30px | 5px 8px | none | normal` on files
  - `.linkbtn`: 4 styles
    - `14px | 400 | "ABC Diatype" | 0px | 24px | 2px 4px | none | normal` on inbox, today
    - `12px | 700 | "ABC Diatype" | 0px | 24px | 2px 4px | none | normal` on today
    - `13px | 400 | "ABC Diatype" | 0px | 24px | 2px 4px | none | normal` on work
    - `12px | 400 | "ABC Diatype" | 0px | 24px | 2px 4px | none | normal` on review
  - `.btn`: 3 styles
    - `13px | 500 | "ABC Diatype" | 4px | 32px | 0px 12px | none | normal` on files, inbox, review, settings, work
    - `12px | 500 | "ABC Diatype" | 4px | 28px | 0px 12px | none | normal` on today
    - `12px | 500 | "ABC Diatype" | 4px | 30px | 0px 12px | none | normal` on today
  - `.mini`: 3 styles
    - `12px | 500 | "ABC Diatype" | 6px | 30px | 0px 8px | none | normal` on today
    - `12px | 500 | "ABC Diatype" | 6px | 26px | 0px 8px | none | normal` on review
    - `12px | 500 | "ABC Diatype" | 6px | 26px | 1px 6px | none | normal` on review
  - `.ib`: 3 styles
    - `14px | 400 | "ABC Diatype" | 6px | 28px | 0px 0px | none | normal` on activity, files, inbox, review
    - `14px | 400 | "ABC Diatype" | 8px | 32px | 0px 0px | none | normal` on review, work
    - `13px | 400 | "ABC Diatype" | 8px | 32px | 0px 0px | none | normal` on settings
  - `.pfname`: 2 styles
    - `14px | 400 | "ABC Diatype" | 0px | 20px | 0px 0px | none | normal` on projects, today
    - `14px | 400 | "ABC Diatype" | 0px | 40px | 0px 0px | none | normal` on today
- **input**: 4 classes, 11 rendered styles; 2 classes drawn more than one way
  - `input`: 6 styles
    - `14px | 400 | "ABC Diatype" | 8px | 32px | 0px 10px | none | normal` on files, review, work
    - `13px | 400 | "ABC Diatype" | 6px | 30px | 0px 8px | none | normal` on activity, inbox
    - `14px | 400 | "ABC Diatype" | 10px | 40px | 0px 14px | none | normal` on files
    - `14px | 400 | "ABC Diatype" | 8px | 32px | 0px 8px | none | normal` on files
  - `select`: 3 styles
    - `13px | 400 | "ABC Diatype" | 6px | 30px | 0px 8px | none | normal` on inbox
    - `14px | 400 | "ABC Diatype" | 8px | 32px | 0px 0px | none | normal` on files
    - `13px | 400 | "ABC Diatype" | 6px | 28px | 4px 8px | none | normal` on settings
- **h1**: 1 classes, 3 rendered styles; 1 classes drawn more than one way
  - `h1`: 3 styles
    - `22px | 500 | "ABC Diatype" | 0px |  | 0px 0px | none | -0.22px` on activity, files, inbox, people, projects, review, settings, work
    - `34px | 500 | "ABC Diatype" | 0px |  | 0px 0px | none | -0.34px` on today
    - `49.6px | 800 | "Schibsted Grotesk" | 0px |  | 0px 0px | none | -0.992px` on help
- **h2**: 2 classes, 5 rendered styles; 1 classes drawn more than one way
  - `h2`: 4 styles
    - `15px | 500 | "ABC Diatype" | 0px |  | 0px 0px | none | -0.15px` on activity, settings
    - `14px | 500 | "ABC Diatype" | 0px |  | 0px 0px | none | -0.14px` on review
    - `18px | 500 | "ABC Diatype" | 0px |  | 0px 0px | none | -0.18px` on inbox
    - `23.2px | 700 | "Schibsted Grotesk" | 0px |  | 0px 0px | none | -0.232px` on help
- **h3**: 1 classes, 1 rendered styles; 0 classes drawn more than one way
- **chip**: 1 classes, 3 rendered styles; 1 classes drawn more than one way
  - `.tag`: 3 styles
    - `12px | 400 | "ABC Diatype" | 0px |  | 0px 0px | none | normal` on inbox, review
    - `12px | 400 | "ABC Diatype" | 0px |  | 0px 0px | none | -0.14px` on review
    - `12px | 500 | "ABC Diatype" | 0px |  | 0px 0px | none | normal` on review
- **th**: 3 classes, 4 rendered styles; 1 classes drawn more than one way
  - `th`: 2 styles
    - `12px | 500 | "ABC Diatype" | 0px |  | 8px 12px | none | normal` on activity, files, inbox, people, projects, today, work
    - `11.52px | 500 | "JetBrains Mono" | 0px |  | 11px 16px | uppercase | 1.152px` on help
- **td**: 10 classes, 14 rendered styles; 3 classes drawn more than one way
  - `.title`: 3 styles
    - `14px | 400 | "ABC Diatype" | 0px |  | 8px 12px | none | normal` on inbox, people, review, work
    - `14px | 500 | "ABC Diatype" | 0px |  | 8px 12px | none | normal` on review
    - `14px | 400 | "ABC Diatype" | 0px |  | 8px 34px | none | normal` on review
  - `td`: 2 styles
    - `14px | 400 | "ABC Diatype" | 0px |  | 8px 12px | none | normal` on activity, files, inbox, people, projects, review, today
    - `15.04px | 400 | "Source Sans 3" | 0px |  | 11px 16px | none | normal` on help
  - `.num`: 2 styles
    - `14px | 400 | "ABC Diatype" | 0px |  | 8px 12px | none | normal` on people
    - `14px | 500 | "ABC Diatype" | 0px |  | 8px 12px | none | normal` on people
- **link**: 9 classes, 19 rendered styles; 5 classes drawn more than one way
  - `.cntl`: 5 styles
    - `12px | 400 | "ABC Diatype" | 3px |  | 0px 0px | none | normal` on projects, today
    - `15px | 400 | "ABC Diatype" | 3px |  | 0px 0px | none | normal` on today
    - `13px | 400 | "ABC Diatype" | 3px |  | 4px 9px | none | normal` on today
    - `14px | 400 | "ABC Diatype" | 3px |  | 4px 9px | none | normal` on people
  - `a`: 4 styles
    - `13px | 400 | "ABC Diatype" | 0px |  | 0px 0px | none | normal` on today
    - `13px | 400 | "ABC Diatype" | 0px |  | 2px 0px | none | normal` on today
    - `14px | 400 | "ABC Diatype" | 0px |  | 2px 0px | none | normal` on files
    - `13.76px | 400 | "Source Sans 3" | 0px |  | 2px 0px | none | normal` on help
  - `.s`: 2 styles
    - `14px | 400 | "ABC Diatype" | 0px |  | 2px 0px | none | normal` on today
    - `14px | 400 | "ABC Diatype" | 0px |  | 0px 0px | none | normal` on today
  - `.plink2`: 2 styles
    - `14px | 400 | "ABC Diatype" | 0px |  | 2px 0px | none | normal` on people, work
    - `12px | 400 | "ABC Diatype" | 0px |  | 2px 0px | none | normal` on review
  - `.hlink`: 2 styles
    - `14px | 500 | "ABC Diatype" | 0px |  | 3px 0px | none | -0.14px` on review
    - `14px | 400 | "ABC Diatype" | 0px |  | 3px 0px | none | normal` on activity

## Fonts other than the theme's own, by theme

- **Apple** ("SF Pro Text"): "Source Sans 3" on help; "JetBrains Mono" on help; "SF Pro Display" on activity, files, inbox, people, projects, review, settings, today, work; "Schibsted Grotesk" on help; monospace on settings
- **Claude** (StyreneB): "Source Sans 3" on help; "JetBrains Mono" on activity, help, settings; "Schibsted Grotesk" on help; Copernicus on today
- **Cursor** (CursorGothic): "Source Sans 3" on help; "JetBrains Mono" on activity, help, settings; "Schibsted Grotesk" on help
- **Brightwater** ("ABC Diatype"): "Source Sans 3" on help; "JetBrains Mono" on help; "Schibsted Grotesk" on help; monospace on settings
- **Linear** ("Linear Text"): "Source Sans 3" on help; "JetBrains Mono" on help; "Schibsted Grotesk" on help; monospace on settings
- **Notion** (NotionInter): "Source Sans 3" on help; "JetBrains Mono" on help; "Schibsted Grotesk" on help; monospace on settings
- **Retro Arcade** (system-ui): "JetBrains Mono" on activity, files, help, inbox, people, projects, review, settings, today, work; "Source Sans 3" on help; "Schibsted Grotesk" on help
- **Thermo Scan** (system-ui): "Share Tech Mono" on activity, files, help, inbox, people, projects, review, settings, today, work; "Source Sans 3" on help; "Schibsted Grotesk" on help; "JetBrains Mono" on help
- **creaite** ("Source Sans 3"): "JetBrains Mono" on activity, files, help, inbox, people, projects, settings, today, work; "Schibsted Grotesk" on activity, files, help, inbox, people, projects, review, settings, today, work; monospace on settings

## Accessibility (axe-core)

- **aria-required-attr** (critical, 220 nodes): Required ARIA attributes must be provided. Pages: projects, today, work
  - e.g. `span[aria-label="Resize Project column"] — Required ARIA attribute not present: aria-valuenow`
  - e.g. `span[aria-label="Resize Health column"] — Required ARIA attribute not present: aria-valuenow`
- **aria-allowed-attr** (critical, 40 nodes): Elements must only use supported ARIA attributes. Pages: people, settings
  - e.g. `th[data-psort="name"]`
  - e.g. `th[data-psort="org"]`
- **label-content-name-mismatch** (serious, 200 nodes): Elements must have their visible text as part of their accessible name. Pages: inbox, projects, today
  - e.g. `a[data-nav="actions:overdue::o=%40me"] — Text inside the element is not included in the accessible name`
  - e.g. `a[data-nav="actions:overdue:ABC"] — Text inside the element is not included in the accessible name`
- **aria-prohibited-attr** (serious, 80 nodes): Elements must only use permitted ARIA attributes. Pages: projects, today
  - e.g. `.click[data-cock="ABC"] > td:nth-child(4) > .spark[aria-label="Health trend"]`
  - e.g. `.click[data-cock="DEF"] > td:nth-child(4) > .spark[aria-label="Health trend"]`
- **nested-interactive** (serious, 4 nodes): Interactive controls must not be nested. Pages: inbox
  - e.g. `#inboxDrop — Element has focusable descendants. Move them outside of the element, or remove them.`
- **scrollable-region-focusable** (serious, 2 nodes): Scrollable region must have keyboard access. Pages: help
  - e.g. `.hp-phrases — Element should have focusable content`
- **empty-table-header** (minor, 16 nodes): Table header text should not be empty. Pages: activity, files, inbox
  - e.g. `#inboxTbl > thead > tr > th:nth-child(1) — Element does not have text that is visible to screen readers`
  - e.g. `th:nth-child(8) — Element does not have text that is visible to screen readers`

## Small tap targets and horizontal overflow

- today @ 1400x1000: 23 targets under 24px: a 118x18 1 overdue action of yours, ope; a 162x16 Settings › System › Set-up; a 230x21 Review the ABC Steering minute; a 133x21 Example Programme; a 532x21 Example Programme weekly repor
- work @ 1400x1000: 14 targets under 24px: span 8x32 Resize Action column; span 8x32 Resize Owner column; span 8x32 Resize Due column; span 8x32 Resize Priority column; span 8x32 Resize Status column
- review @ 1400x1000: 12 targets under 24px: input 13x13 Select the rows in Needs a pro; input 13x13 Select Confirm data owner; input 13x13 Select the rows in Example Pro; a 134x23 Example Programme; input 13x13 Select the routine items from 
- projects @ 1400x1000: 11 targets under 24px: span 8x32 Resize Project column; span 8x32 Resize Health column; span 8x32 Resize Evidence column; span 8x32 Resize 8 weeks column; span 8x32 Resize Next milestone column
- inbox @ 1400x1000: 4 targets under 24px: input 13x13 Select ABC weekly sync.vtt; span 116x23 Example Programme; input 13x13 Select Copy of filed.vtt; input 13x13 Select Recording.vtt
- files @ 1400x1000: 6 targets under 24px: a 175x21 2026-10-09 Steering.docx; a 161x21 2026-10-09 Steering.vtt; a 202x21 2026-09-29 Client report.docx; a 131x21 ABC weekly sync.vtt; a 102x21 Copy of filed.vtt
- people @ 1400x1000: 6 targets under 24px: a 114x21 You (Alan Carter); span 116x23 Example Programme; a 55x21 Omar Ali; span 106x23 Digital Enablement; a 88x21 Sara Example
- activity @ 1400x1000: 23 targets under 24px: input 16x16 Select: ABC health reason: — →; a 133x23 Example Programme; input 16x16 Select: ABC health: — → Off tr; a 133x23 Example Programme; a 133x23 Example Programme
- settings @ 1400x1000: 11 targets under 24px: input 40x22 ; input 40x22 Draft the latest update; input 40x22 Draft client wording; input 40x22 Suggest the thinking fields; input 40x22 Draft the reason for a health 
- today @ 390x844: 16 targets under 24px: a 118x18 1 overdue action of yours, ope; a 230x21 Review the ABC Steering minute; a 133x21 Example Programme; a 277x21 Escalate data access to the cl; a 133x21 Example Programme
- work @ 390x844: 12 targets under 24px: span 8x32 Resize Action column; span 8x32 Resize Owner column; span 8x32 Resize Due column; span 8x32 Resize Priority column; span 8x32 Resize Status column
- review @ 390x844: 12 targets under 24px: input 13x13 Select the rows in Needs a pro; input 13x13 Select Confirm data owner; input 13x13 Select the rows in Example Pro; a 134x23 Example Programme; input 13x13 Select the routine items from 
- projects @ 390x844: 9 targets under 24px: span 8x32 Resize Project column; span 8x32 Resize Health column; span 8x32 Resize Evidence column; span 8x32 Resize 8 weeks column; span 8x32 Resize Next milestone column
- inbox @ 390x844: 3 targets under 24px: input 13x13 Select ABC weekly sync.vtt; input 13x13 Select Copy of filed.vtt; input 13x13 Select Recording.vtt
- files @ 390x844: 1 targets under 24px: a 86x21 Recording.vtt
- people @ 390x844: 3 targets under 24px: a 114x21 You (Alan Carter); a 55x21 Omar Ali; a 88x21 Sara Example
- activity @ 390x844: 23 targets under 24px: input 16x16 Select: ABC health reason: — →; a 133x23 Example Programme; input 16x16 Select: ABC health: — → Off tr; a 133x23 Example Programme; a 133x23 Example Programme
- settings @ 390x844: 11 targets under 24px: input 40x22 ; input 40x22 Draft the latest update; input 40x22 Draft client wording; input 40x22 Suggest the thinking fields; input 40x22 Draft the reason for a health 

## Console errors during the run: 0

