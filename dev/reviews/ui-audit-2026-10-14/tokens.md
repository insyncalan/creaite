# creaite design-token audit

Surfaces: **dashboard** (2522 rules, 85 tokens, palettes: Brightwater, creaite, Notion, Linear, Cursor, Claude, Apple, Retro Arcade, Thermo Scan; default creaite); **guide-first-day** (135 rules, 14 tokens, palettes: base; default base); **guide-how-to** (135 rules, 14 tokens, palettes: base; default base); **offline** (8 rules, 6 tokens, palettes: base; default base); **prep-page** (74 rules, 10 tokens, palettes: base; default base); **reference** (282 rules, 21 tokens, palettes: base; default base)

| # | Check | P1 | P2 | P3 | Total |
|---:|---|---:|---:|---:|---:|
| 1 | Unused tokens | 0 | 2 | 0 | 2 |
| 2 | Undefined tokens | 3 | 0 | 0 | 3 |
| 3 | Theme completeness | 10 | 0 | 0 | 10 |
| 4 | Hard-coded colours | 10 | 3 | 61 | 74 |
| 5 | Scale drift | 0 | 6 | 58 | 64 |
| 6 | Near-duplicate tokens | 0 | 10 | 13 | 23 |
| 7 | Contrast | 39 | 0 | 0 | 39 |
| 8 | Cross-surface consistency | 0 | 9 | 19 | 28 |
| | **All** | **62** | **30** | **151** | **243** |

## 1. Unused tokens (2)

- **P2** [reference] --ok-soft is defined (3x, root) but never read — `dev/reference/dashboard-reference.html:12`
- **P2** [reference] --warn-soft is defined (3x, root) but never read — `dev/reference/dashboard-reference.html:12`

## 2. Undefined tokens (3)

- **P1** [dashboard] --pc is read (2x) but defined nowhere — `system/templates/dashboard/style.css:718`
- **P1** [guide-first-day] --d2 is read (1x) but defined nowhere — `system/templates/guide-first-day.html:126`
- **P1** [guide-how-to] --d2 is read (1x) but defined nowhere — `system/templates/guide-how-to.html:126`

## 3. Theme completeness (10)


**dashboard** — root tokens each palette sets itself, and how many it takes from the base

| Palette | Own (light) | Own (dark) | From base | Effective light | Effective dark |
|---|---:|---:|---:|---:|---:|
| Brightwater | 31 | 29 | 17 | 48 | 48 |
| creaite | 30 | 26 | 17 | 47 | 47 |
| Notion | 32 | 30 | 17 | 49 | 49 |
| Linear | 33 | 31 | 17 | 50 | 50 |
| Cursor | 35 | 31 | 17 | 52 | 52 |
| Claude | 38 | 34 | 15 | 53 | 53 |
| Apple | 38 | 34 | 15 | 53 | 53 |
| Retro Arcade | 41 | 36 | 15 | 56 | 56 |
| Thermo Scan | 40 | 35 | 15 | 55 | 55 |

- **P1** [dashboard] --line-strong is read with no fallback (2x) but is undefined in 6 palette/mode(s): Brightwater dark, Brightwater light, Notion dark, Notion light, creaite dark, creaite light — `system/templates/dashboard/style.css:2118`
- **P1** [dashboard] Brightwater: 1 token(s) differ between system dark (prefers-color-scheme) and explicit dark (data-theme): --saffron #C7860E vs #F2B544 — `system/templates/dashboard/style.css:2274`
- **P1** [dashboard] creaite: 1 token(s) differ between system dark (prefers-color-scheme) and explicit dark (data-theme): --saffron #C7860E vs #F2B544 — `system/templates/dashboard/style.css:2274`
- **P1** [dashboard] Notion: 1 token(s) differ between system dark (prefers-color-scheme) and explicit dark (data-theme): --saffron #C7860E vs #F2B544 — `system/templates/dashboard/style.css:2274`
- **P1** [dashboard] Linear: 1 token(s) differ between system dark (prefers-color-scheme) and explicit dark (data-theme): --saffron #C7860E vs #F2B544 — `system/templates/dashboard/style.css:2274`
- **P1** [dashboard] Cursor: 1 token(s) differ between system dark (prefers-color-scheme) and explicit dark (data-theme): --saffron #C7860E vs #F2B544 — `system/templates/dashboard/style.css:2274`
- **P1** [dashboard] Claude: 1 token(s) differ between system dark (prefers-color-scheme) and explicit dark (data-theme): --saffron #C7860E vs #F2B544 — `system/templates/dashboard/style.css:2274`
- **P1** [dashboard] Apple: 1 token(s) differ between system dark (prefers-color-scheme) and explicit dark (data-theme): --saffron #C7860E vs #F2B544 — `system/templates/dashboard/style.css:2274`
- **P1** [dashboard] Retro Arcade: 1 token(s) differ between system dark (prefers-color-scheme) and explicit dark (data-theme): --saffron #C7860E vs #F2B544 — `system/templates/dashboard/style.css:2274`
- **P1** [dashboard] Thermo Scan: 1 token(s) differ between system dark (prefers-color-scheme) and explicit dark (data-theme): --saffron #C7860E vs #F2B544 — `system/templates/dashboard/style.css:2274`

## 4. Hard-coded colours (74)

- **P1** [dashboard] rule color: #1E1F1E equals --ink, --day-ink, --accent, --focus in Brightwater light: should be var(--ink) — `system/templates/dashboard/style.css:59`
- **P1** [dashboard] rule color: #1E1F1E equals --ink, --day-ink, --accent, --focus in Brightwater light: should be var(--ink) — `system/templates/dashboard/style.css:60`
- **P1** [dashboard] rule color: #1E1F1E equals --ink, --day-ink, --accent, --focus in Brightwater light: should be var(--ink) — `system/templates/dashboard/style.css:62`
- **P1** [dashboard] rule color: #FFFFFF equals --accent-ink, --bad-ink, --knob, --surface in Notion light: should be var(--accent-ink) — `system/templates/dashboard/style.css:129`
- **P1** [dashboard] rule color: #FFFFFF equals --accent-ink, --bad-ink, --knob, --surface in Linear light: should be var(--accent-ink) — `system/templates/dashboard/style.css:178`
- **P1** [dashboard] rule color: #FFFFFF equals --accent-ink, --bad-ink, --btn-ink, --knob in Retro Arcade light: should be var(--accent-ink) — `system/templates/dashboard/style.css:382`
- **P1** [dashboard] rule color: #FFFFFF equals --accent-ink, --bad-ink, --btn-ink, --knob in Retro Arcade light: should be var(--accent-ink) — `system/templates/dashboard/style.css:391`
- **P1** [dashboard] rule color: #FFFF00 equals --inverse-ink, --stage-dot in Retro Arcade light: should be var(--inverse-ink) — `system/templates/dashboard/style.css:392`
- **P1** [offline] rule color: #fff equals --surface in base light: should be var(--surface) — `system/templates/app/offline.html:14`
- **P1** [reference] rule color: #fff equals --accent-ink, --surface in base light: should be var(--accent-ink) — `dev/reference/dashboard-reference.html:37`
- **P2** [dashboard] rule background: rgba(0,0,0,.06) is a literal colour with no matching token — `system/templates/dashboard/style.css:496`
- **P2** [dashboard] rule background: rgba(255,255,255,.35) is a literal colour with no matching token — `system/templates/dashboard/style.css:1285`
- **P2** [reference] rule background: rgba(0,0,0,.06) is a literal colour with no matching token — `dev/reference/dashboard-reference.html:49`
- **P3** [dashboard] JS: 1 literal colour(s) in a fixed list or canvas paint (THEMES swatches, DE_COLOURS, a canvas fillStyle; by design) — `system/templates/dashboard/src/ask.js:686`
- **P3** [dashboard] JS: 36 literal colour(s) in a fixed list or canvas paint (THEMES swatches, DE_COLOURS, a canvas fillStyle; by design) — `system/templates/dashboard/src/core/page.js:55`
- **P3** [dashboard] JS: 7 literal colour(s) in a fixed list or canvas paint (THEMES swatches, DE_COLOURS, a canvas fillStyle; by design) — `system/templates/dashboard/src/drafts.js:24`
- **P3** [dashboard] rule box-shadow: rgba(0,0,0,.14) (fixed on purpose: a shadow) — `system/templates/dashboard/style.css:545`
- **P3** [dashboard] rule box-shadow: rgba(0,0,0,.18) (fixed on purpose: a shadow) — `system/templates/dashboard/style.css:587`
- **P3** [dashboard] rule box-shadow: rgba(0,0,0,.16) (fixed on purpose: a shadow) — `system/templates/dashboard/style.css:617`
- **P3** [dashboard] rule box-shadow: rgba(0,0,0,.14) (fixed on purpose: a shadow) — `system/templates/dashboard/style.css:641`
- **P3** [dashboard] rule box-shadow: rgba(0,0,0,.18) (fixed on purpose: a shadow) — `system/templates/dashboard/style.css:693`
- **P3** [dashboard] rule box-shadow: rgba(0,0,0,.16) (fixed on purpose: a shadow) — `system/templates/dashboard/style.css:703`
- **P3** [dashboard] rule box-shadow: rgba(0,0,0,.1) (fixed on purpose: a shadow) — `system/templates/dashboard/style.css:771`
- **P3** [dashboard] rule box-shadow: rgba(0,0,0,.25) (fixed on purpose: a shadow) — `system/templates/dashboard/style.css:796`
- **P3** [dashboard] rule color: #B54708 is a var() fallback (dead while the token is defined; it drifts unseen) — `system/templates/dashboard/style.css:816`
- **P3** [dashboard] rule background: rgba(0,0,0,.72) (fixed on purpose: the image viewer's backing and scrim) — `system/templates/dashboard/style.css:831`
- **P3** [dashboard] rule background: #fff (fixed on purpose: the image viewer's backing and scrim); equals --surface, --knob, --accent-ink — `system/templates/dashboard/style.css:831`
- **P3** [dashboard] rule box-shadow: rgba(0,0,0,.14) (fixed on purpose: a shadow) — `system/templates/dashboard/style.css:832`
- **P3** [dashboard] rule background: rgba(0,0,0,.25) (fixed on purpose: a scrim) — `system/templates/dashboard/style.css:836`
- **P3** [dashboard] rule background: rgba(0,0,0,.25) (fixed on purpose: a scrim) — `system/templates/dashboard/style.css:858`
- **P3** [dashboard] rule background: rgba(0,0,0,.25) (fixed on purpose: a scrim) — `system/templates/dashboard/style.css:860`
- **P3** [dashboard] rule background: rgba(0,0,0,.25) (fixed on purpose: a scrim) — `system/templates/dashboard/style.css:918`
- **P3** [dashboard] rule box-shadow: rgba(0,0,0,.28) (fixed on purpose: a shadow) — `system/templates/dashboard/style.css:951`
- **P3** [dashboard] rule box-shadow: rgba(0,0,0,.2) (fixed on purpose: a shadow) — `system/templates/dashboard/style.css:953`
- **P3** [dashboard] rule background: rgba(0,0,0,.25) (fixed on purpose: a scrim) — `system/templates/dashboard/style.css:955`
- **P3** [dashboard] rule background: rgba(0,0,0,.25) (fixed on purpose: a scrim) — `system/templates/dashboard/style.css:988`
- **P3** [dashboard] rule background: rgba(0,0,0,.25) (fixed on purpose: a scrim) — `system/templates/dashboard/style.css:997`
- **P3** [dashboard] rule background: rgba(0,0,0,.25) (fixed on purpose: a scrim) — `system/templates/dashboard/style.css:1000`
- **P3** [dashboard] rule background: #FFFFFF (fixed on purpose: the Word preview's own colours); equals --surface, --knob, --accent-ink — `system/templates/dashboard/style.css:1005`
- **P3** [dashboard] rule color: #1E1F1E (fixed on purpose: the Word preview's own colours) — `system/templates/dashboard/style.css:1005`
- … and 34 more (all are in `--json`)

## 5. Scale drift (64)


**dashboard** — raw values (count) and tokens used

| Scale | Raw uses | Distinct raw | Token uses | Raw values |
|---|---:|---:|---:|---|
| font-size | 463 | 46 | 0 | 12px (138), 13px (135), 11px (56), 14px (36), 16px (15), 15px (10), 10px (8), 18px (5), .9rem (4), .92rem (4), 11.5px (3), .74rem (3), .72rem (3), .94rem (3), 9px (2), 22px (2), 20px (2), 17px (2), .86em (2), .84em (2), .97rem (2), 12.5px (2), 34px (1), 13.5px (1), 14.5px (1), clamp(2rem,5vw,3.1rem) (1), clamp(2rem,5vw,3rem) (1), 1.45rem (1), 1.35rem (1), 1.05rem (1), 1.08rem (1), 1.12rem (1), 1.1rem (1), .8rem (1), .93rem (1), 1.7rem (1), .76rem (1), .88rem (1), .86rem (1), .78rem (1), .95rem (1), .85em (1), .7rem (1), 1.02rem (1), 1.2rem (1), max(12px,.72rem) (1) |
| font-weight | 231 | 5 | 0 | 600 (97), 500 (89), 700 (24), 400 (16), 800 (5) |
| line-height | 103 | 22 | 0 | 1 (21), 16px (21), 18px (15), 20px (9), 14px (4), 22px (4), 1.5 (4), 1.55 (4), 1.45 (3), 1.4 (2), 17px (2), 23px (2), 19px (2), 1.3 (2), 1.2 (1), 28px (1), 40px (1), 26px (1), 24px (1), 1.05 (1), 1.35 (1), 30px (1) |
| border-radius | 349 | 19 | 0 | 8px (96), 6px (75), 12px (35), 50% (30), 10px (25), 4px (23), 999px (23), 2px (9), 9999px (6), 5px (5), 3px (5), 14px (5), 9px (3), 18px (2), 11px (2), 99px (2), 1px (1), 17px (1), 7px (1) |
| box-shadow | 25 | 20 | 38 | 0 6px 18px rgba(0,0,0,.14) (2), 0 8px 24px rgba(0,0,0,.18) (2), 0 6px 18px rgba(0,0,0,.16) (2), 0 10px 30px rgba(0,0,0,.18) (2), -14px 0 32px rgba(0,0,0,.18) (2), -4px 0 16px rgba(0,0,0,.1) (1), 0 2px 10px rgba(0,0,0,.25) (1), 0 -6px 18px rgba(0,0,0,.14) (1), 0 10px 28px rgba(0,0,0,.28) (1), 0 8px 24px rgba(0,0,0,.2) (1), inset 0 1px 0 rgba(255,255,255,.32),0 1px 2px rgba(0,0,0,.22),0 6px 12px -6px rgba(0,0,0,.35) (1), inset 0 1px 0 rgba(255,255,255,.32),0 2px 4px rgba(0,0,0,.25),0 9px 16px -6px rgba(0,0,0,.4) (1), inset 0 1px 2px rgba(0,0,0,.25) (1), 0 4px 12px rgba(0,0,0,.12) (1), … |
| z-index | 43 | 19 | 0 | 1 (8), 2 (5), 60 (4), 70 (4), 40 (3), 3 (3), 5 (2), 200 (2), 4 (2), 30 (1), 25 (1), 45 (1), 90 (1), 210 (1), 80 (1), 46 (1), 47 (1), 65 (1), 41 (1) |
| spacing | 1599 | 58 | 2 | 8px (296), 6px (263), 10px (199), 4px (185), 2px (115), 12px (113), 14px (80), 16px (56), 18px (44), 3px (37), 5px (30), 20px (18), 7px (18), 1px (13), 22px (11), -2px (10), 24px (8), -4px (8), 9px (8), 28px (6), 30px (6), 26px (5), .6em (5), -1px (5), -8px (5), -6px (4), 40px (3), -10px (3), .15em (3), .4em (3), -20px (2), -24px (2), 36px (2), -16px (2), 34px (2), .7em (2), 56px (2), 13px (2), 1.25em (2), -5px (2), -3px (2), .2em (1), 1.4em (1), .3em (1), 72px (1), 44px (1), 1.05em (1), 11px (1), 7.5ch (1), -7px (1), calc(12px + var(--pkover)) (1), calc(26px + var(--pkover)) (1), … |
| duration | 38 | 28 | 165 | 150ms (4), .12s (3), .8s (2), 700ms (2), 300ms (2), 2800ms (2), 5s (2), 2.5s (1), 1.2s (1), .15s (1), 1.4s (1), 800ms (1), 6s (1), 10s (1), 500ms (1), 400ms (1), 1500ms (1), 1400ms (1), 900ms (1), 1600ms (1), 1200ms (1), 260ms (1), 120ms (1), 40ms (1), 1.6s (1), .18s (1), .32s (1), .16s (1) |

**prep-page** — raw values (count) and tokens used

| Scale | Raw uses | Distinct raw | Token uses | Raw values |
|---|---:|---:|---:|---|
| font-size | 19 | 8 | 0 | 12px (7), 14px (4), 11px (2), 16px (2), 15px (1), 24px (1), 17px (1), 13px (1) |
| font-weight | 2 | 2 | 0 | 700 (1), 600 (1) |
| line-height | 8 | 5 | 0 | 1.5 (2), 1 (2), 1.55 (2), 1.25 (1), 1.4 (1) |
| border-radius | 6 | 4 | 0 | 4px (2), 999px (2), 8px (1), 10px (1) |
| box-shadow | 0 | 0 | 0 | — |
| z-index | 0 | 0 | 0 | — |
| spacing | 63 | 17 | 0 | 8px (11), 6px (7), 4px (7), 10px (6), 16px (5), 12px (5), 14px (4), 24px (3), 22px (3), 48px (2), 20px (2), 9px (2), 3px (2), 7px (1), 1px (1), 5px (1), 26px (1) |
| duration | 0 | 0 | 0 | — |

- **P2** [dashboard] font-size: 46 distinct raw values in 463 uses, against 0 tokenised uses (0 tokens): no scale is being followed — `system/templates/dashboard/style.css`
- **P2** [dashboard] font-weight: 5 distinct raw values in 231 uses, against 0 tokenised uses (0 tokens): no scale is being followed — `system/templates/dashboard/style.css`
- **P2** [dashboard] line-height: 22 distinct raw values in 103 uses, against 0 tokenised uses (0 tokens): no scale is being followed — `system/templates/dashboard/style.css`
- **P2** [dashboard] border-radius: 19 distinct raw values in 349 uses, against 0 tokenised uses (0 tokens): no scale is being followed — `system/templates/dashboard/style.css`
- **P2** [dashboard] z-index: 19 distinct raw values in 43 uses, against 0 tokenised uses (0 tokens): no scale is being followed — `system/templates/dashboard/style.css`
- **P2** [dashboard] spacing: 58 distinct raw values in 1599 uses, against 2 tokenised uses (1 tokens): no scale is being followed — `system/templates/dashboard/style.css`
- **P3** [dashboard] font-size near-duplicates: 9px (2), 10px (8); fold into 10px? — `system/templates/dashboard/style.css`
- **P3** [dashboard] font-size near-duplicates: 11px (56), 11.5px (3), 12px (138); fold into 12px? — `system/templates/dashboard/style.css`
- **P3** [dashboard] font-size near-duplicates: 12.5px (2), 13px (135), 13.5px (1); fold into 13px? — `system/templates/dashboard/style.css`
- **P3** [dashboard] font-size near-duplicates: 14px (36), 14.5px (1), 15px (10); fold into 14px? — `system/templates/dashboard/style.css`
- **P3** [dashboard] font-size near-duplicates: 16px (15), 17px (2); fold into 16px? — `system/templates/dashboard/style.css`
- **P3** [dashboard] font-size near-duplicates: .7rem (1), .72rem (3), .74rem (3); fold into .72rem? — `system/templates/dashboard/style.css`
- **P3** [dashboard] font-size near-duplicates: .76rem (1), .78rem (1), .8rem (1); fold into .76rem? — `system/templates/dashboard/style.css`
- **P3** [dashboard] font-size near-duplicates: .86rem (1), .88rem (1), .9rem (4), .92rem (4); fold into .9rem? — `system/templates/dashboard/style.css`
- **P3** [dashboard] font-size near-duplicates: .93rem (1), .94rem (3), .95rem (1), .97rem (2); fold into .94rem? — `system/templates/dashboard/style.css`
- **P3** [dashboard] font-size near-duplicates: 1.02rem (1), 1.05rem (1), 1.08rem (1), 1.1rem (1); fold into 1.02rem? — `system/templates/dashboard/style.css`
- **P3** [dashboard] font-size near-duplicates: 1.12rem (1), 1.2rem (1); fold into 1.12rem? — `system/templates/dashboard/style.css`
- **P3** [dashboard] font-size near-duplicates: 1.35rem (1), 1.45rem (1); fold into 1.35rem? — `system/templates/dashboard/style.css`
- **P3** [dashboard] font-size near-duplicates: .84em (2), .85em (1), .86em (2); fold into .84em? — `system/templates/dashboard/style.css`
- **P3** [dashboard] line-height near-duplicates: 1 (21), 1.05 (1); fold into 1? — `system/templates/dashboard/style.css`
- **P3** [dashboard] line-height near-duplicates: 1.3 (2), 1.35 (1), 1.4 (2); fold into 1.3? — `system/templates/dashboard/style.css`
- **P3** [dashboard] line-height near-duplicates: 1.45 (3), 1.5 (4), 1.55 (4); fold into 1.5? — `system/templates/dashboard/style.css`
- **P3** [dashboard] line-height near-duplicates: 16px (21), 17px (2); fold into 16px? — `system/templates/dashboard/style.css`
- **P3** [dashboard] line-height near-duplicates: 18px (15), 19px (2); fold into 18px? — `system/templates/dashboard/style.css`
- **P3** [dashboard] line-height near-duplicates: 22px (4), 23px (2); fold into 22px? — `system/templates/dashboard/style.css`
- **P3** [dashboard] line-height near-duplicates: 26px (1), 28px (1); fold into 26px? — `system/templates/dashboard/style.css`
- **P3** [dashboard] border-radius near-duplicates: 1px (1), 2px (9); fold into 2px? — `system/templates/dashboard/style.css`
- **P3** [dashboard] border-radius near-duplicates: 3px (5), 4px (23); fold into 4px? — `system/templates/dashboard/style.css`
- **P3** [dashboard] border-radius near-duplicates: 5px (5), 6px (75); fold into 6px? — `system/templates/dashboard/style.css`
- **P3** [dashboard] border-radius near-duplicates: 7px (1), 8px (96); fold into 8px? — `system/templates/dashboard/style.css`
- **P3** [dashboard] border-radius near-duplicates: 9px (3), 10px (25); fold into 10px? — `system/templates/dashboard/style.css`
- **P3** [dashboard] border-radius near-duplicates: 11px (2), 12px (35); fold into 12px? — `system/templates/dashboard/style.css`
- **P3** [dashboard] border-radius near-duplicates: 17px (1), 18px (2); fold into 18px? — `system/templates/dashboard/style.css`
- **P3** [dashboard] spacing near-duplicates: -10px (3), -9px (1); fold into -10px? — `system/templates/dashboard/style.css`
- **P3** [dashboard] spacing near-duplicates: -8px (5), -7px (1); fold into -8px? — `system/templates/dashboard/style.css`
- **P3** [dashboard] spacing near-duplicates: -6px (4), -5px (2); fold into -6px? — `system/templates/dashboard/style.css`
- **P3** [dashboard] spacing near-duplicates: -4px (8), -3px (2); fold into -4px? — `system/templates/dashboard/style.css`
- **P3** [dashboard] spacing near-duplicates: -2px (10), -1px (5); fold into -2px? — `system/templates/dashboard/style.css`
- **P3** [dashboard] spacing near-duplicates: 1px (13), 2px (115); fold into 2px? — `system/templates/dashboard/style.css`
- **P3** [dashboard] spacing near-duplicates: 3px (37), 4px (185); fold into 4px? — `system/templates/dashboard/style.css`
- … and 24 more (all are in `--json`)

## 6. Near-duplicate tokens (23)

- **P2** [dashboard] --accent-soft and --tx-tint are nearly the same in 2/18: Notion light (#E6F1FB/#E3EDF6, ΔE 1.5); Apple light (#E8F1FB/#E3EEF9, ΔE 1.4) — `system/templates/dashboard/style.css`
- **P2** [dashboard] --btn-hover and --mdot-2 are nearly the same in 1/18: Brightwater light (#3A3B3A/#3E3E3E, ΔE 1.7) — `system/templates/dashboard/style.css`
- **P2** [dashboard] --day-band and --sunk are nearly the same in 1/18: creaite light (#E8F2F4/#EAF0F2, ΔE 1.4) — `system/templates/dashboard/style.css`
- **P2** [dashboard] --day-band and --tx-tint are nearly the same in 1/18: creaite light (#E8F2F4/#E4EFF1, ΔE 1.2) — `system/templates/dashboard/style.css`
- **P2** [dashboard] --sunk and --tx-tint are nearly the same in 1/18: creaite light (#EAF0F2/#E4EFF1, ΔE 1.9) — `system/templates/dashboard/style.css`
- **P2** [dashboard] --bg and --inverse-ink are nearly the same in 1/18: Linear light (#F5F6F6/#F7F8F8, ΔE 0.7) — `system/templates/dashboard/style.css`
- **P2** [dashboard] --day-page and --inverse-ink are nearly the same in 1/18: Linear light (#F5F6F6/#F7F8F8, ΔE 0.7) — `system/templates/dashboard/style.css`
- **P2** [dashboard] --day-muted and --faint are nearly the same in 1/18: Claude light (#6C6A64/#6A6862, ΔE 0.8) — `system/templates/dashboard/style.css`
- **P2** [dashboard] --faint and --muted are nearly the same in 1/18: Claude light (#6A6862/#6C6A64, ΔE 0.8) — `system/templates/dashboard/style.css`
- **P2** [reference] --inverse-ink and --sunk are nearly the same in 1/2: base light (#EDF1F4/#EEF1F3, ΔE 0.6) — `dev/reference/dashboard-reference.html`
- **P3** [dashboard] --day-ink = --ink in 18/18 theme-modes: an alias (var(--day-ink)) or one token? — `system/templates/dashboard/style.css`
- **P3** [dashboard] --day-muted = --muted in 18/18 theme-modes: an alias (var(--day-muted)) or one token? — `system/templates/dashboard/style.css`
- **P3** [dashboard] --day-rule = --line in 18/18 theme-modes: an alias (var(--day-rule)) or one token? — `system/templates/dashboard/style.css`
- **P3** [dashboard] --bg = --day-page in 17/18 theme-modes: an alias (var(--bg)) or one token? — `system/templates/dashboard/style.css`
- **P3** [dashboard] --accent = --day-sun in 16/18 theme-modes: an alias (var(--accent)) or one token? — `system/templates/dashboard/style.css`
- **P3** [dashboard] --day-sun = --mdot-1 in 16/18 theme-modes: an alias (var(--day-sun)) or one token? — `system/templates/dashboard/style.css`
- **P3** [dashboard] --accent = --focus in 12/18 theme-modes: an alias (var(--accent)) or one token? — `system/templates/dashboard/style.css`
- **P3** [dashboard] --focus = --mdot-1 in 12/18 theme-modes: an alias (var(--focus)) or one token? — `system/templates/dashboard/style.css`
- **P3** [dashboard] --day-sun = --focus in 12/18 theme-modes: an alias (var(--day-sun)) or one token? — `system/templates/dashboard/style.css`
- **P3** [dashboard] --accent-ink = --bad-ink in 12/18 theme-modes: an alias (var(--accent-ink)) or one token? — `system/templates/dashboard/style.css`
- **P3** [dashboard] --knob = --surface in 9/18 theme-modes: an alias (var(--knob)) or one token? — `system/templates/dashboard/style.css`
- **P3** [reference] --accent = --focus in 1/2 theme-modes: an alias (var(--accent)) or one token? — `dev/reference/dashboard-reference.html`
- **P3** [reference] --inverse-ink = --surface in 1/2 theme-modes: an alias (var(--inverse-ink)) or one token? — `dev/reference/dashboard-reference.html`

## 7. Contrast (39)

28 palette-modes checked, 816 pairs, 39 below threshold.

- **P1** [dashboard] Brightwater dark: --bad-ink #FFFFFF on --bad #F2B8B5 is 1.71:1, needs 4.5:1 (ink on its fill) — `system/templates/dashboard/style.css:18`
- **P1** [dashboard] creaite dark: --bad-ink #FFFFFF on --bad #F2B8B5 is 1.71:1, needs 4.5:1 (ink on its fill) — `system/templates/dashboard/style.css:18`
- **P1** [dashboard] Notion dark: --bad-ink #FFFFFF on --bad #F2B8B5 is 1.71:1, needs 4.5:1 (ink on its fill) — `system/templates/dashboard/style.css:18`
- **P1** [dashboard] Linear dark: --bad-ink #FFFFFF on --bad #F2B8B5 is 1.71:1, needs 4.5:1 (ink on its fill) — `system/templates/dashboard/style.css:18`
- **P1** [dashboard] Cursor dark: --bad-ink #FFFFFF on --bad #F2B8B5 is 1.71:1, needs 4.5:1 (ink on its fill) — `system/templates/dashboard/style.css:18`
- **P1** [dashboard] Brightwater light: --faint #808187 on --bg #F8F8FF is 3.67:1, needs 4.5:1 (text on a ground) — `system/templates/dashboard/style.css:36`
- **P1** [dashboard] Brightwater light: --faint #808187 on --surface #FFFFFF is 3.88:1, needs 4.5:1 (text on a ground) — `system/templates/dashboard/style.css:36`
- **P1** [dashboard] Brightwater light: --faint #808187 on --sunk #EEEEF4 is 3.36:1, needs 4.5:1 (text on a ground) — `system/templates/dashboard/style.css:36`
- **P1** [dashboard] Brightwater light: --day-sun #AE74FF on --day-page #F8F8FF is 2.95:1, needs 3.0:1 (Today now-line) — `system/templates/dashboard/style.css:40`
- **P1** [dashboard] Brightwater dark: --faint #8E929B on --sunk #323432 is 4.03:1, needs 4.5:1 (text on a ground) — `system/templates/dashboard/style.css:50`
- **P1** [dashboard] creaite light: --faint #6F7D86 on --bg #F3F6F7 is 3.90:1, needs 4.5:1 (text on a ground) — `system/templates/dashboard/style.css:70`
- **P1** [dashboard] creaite light: --faint #6F7D86 on --surface #FFFFFF is 4.24:1, needs 4.5:1 (text on a ground) — `system/templates/dashboard/style.css:70`
- **P1** [dashboard] creaite light: --faint #6F7D86 on --sunk #EAF0F2 is 3.68:1, needs 4.5:1 (text on a ground) — `system/templates/dashboard/style.css:70`
- **P1** [dashboard] creaite light: --day-past #A9B6BD on --day-page #F3F6F7 is 1.91:1, needs 3.0:1 (Today past marks) — `system/templates/dashboard/style.css:75`
- **P1** [dashboard] creaite dark: --faint #7C8990 on --sunk #1E272C is 4.22:1, needs 4.5:1 (text on a ground) — `system/templates/dashboard/style.css:83`
- **P1** [dashboard] creaite dark: --day-past #4A5A61 on --day-page #0F1518 is 2.57:1, needs 3.0:1 (Today past marks) — `system/templates/dashboard/style.css:86`
- **P1** [dashboard] Notion light: --faint #8A857F on --bg #F6F5F4 is 3.36:1, needs 4.5:1 (text on a ground) — `system/templates/dashboard/style.css:102`
- **P1** [dashboard] Notion light: --faint #8A857F on --surface #FFFFFF is 3.66:1, needs 4.5:1 (text on a ground) — `system/templates/dashboard/style.css:102`
- **P1** [dashboard] Notion light: --faint #8A857F on --sunk #EFEEEC is 3.15:1, needs 4.5:1 (text on a ground) — `system/templates/dashboard/style.css:102`
- **P1** [dashboard] Notion light: --day-past #A39E98 on --day-page #F6F5F4 is 2.44:1, needs 3.0:1 (Today past marks) — `system/templates/dashboard/style.css:109`
- **P1** [dashboard] Notion dark: --faint #847F79 on --bg #191919 is 4.43:1, needs 4.5:1 (text on a ground) — `system/templates/dashboard/style.css:119`
- **P1** [dashboard] Notion dark: --faint #847F79 on --surface #202020 is 4.11:1, needs 4.5:1 (text on a ground) — `system/templates/dashboard/style.css:119`
- **P1** [dashboard] Notion dark: --faint #847F79 on --sunk #2A2A2A is 3.62:1, needs 4.5:1 (text on a ground) — `system/templates/dashboard/style.css:119`
- **P1** [dashboard] Notion dark: --day-past #5F5B57 on --day-page #191919 is 2.61:1, needs 3.0:1 (Today past marks) — `system/templates/dashboard/style.css:124`
- **P1** [dashboard] Linear light: --faint #6A6E76 on --sunk #ECEDEF is 4.37:1, needs 4.5:1 (text on a ground) — `system/templates/dashboard/style.css:147`
- **P1** [dashboard] Linear light: --day-past #9A9EA6 on --day-page #F5F6F6 is 2.48:1, needs 3.0:1 (Today past marks) — `system/templates/dashboard/style.css:153`
- **P1** [dashboard] Cursor light: --day-past #A09C92 on --day-page #F7F7F4 is 2.55:1, needs 3.0:1 (Today past marks) — `system/templates/dashboard/style.css:204`
- **P1** [dashboard] Claude light: --day-past #B5AFA5 on --day-page #FAF9F5 is 2.07:1, needs 3.0:1 (Today past marks) — `system/templates/dashboard/style.css:256`
- **P1** [dashboard] Claude dark: --day-past #5E5A53 on --day-page #181715 is 2.61:1, needs 3.0:1 (Today past marks) — `system/templates/dashboard/style.css:270`
- **P1** [dashboard] Apple light: --day-past #AEAEB2 on --day-page #FFFFFF is 2.21:1, needs 3.0:1 (Today past marks) — `system/templates/dashboard/style.css:304`
- **P1** [dashboard] Retro Arcade light: --day-past #9C9CC0 on --day-page #F2F2FF is 2.39:1, needs 3.0:1 (Today past marks) — `system/templates/dashboard/style.css:360`
- **P1** [dashboard] Retro Arcade dark: --day-past #4A4A7A on --day-page #000000 is 2.55:1, needs 3.0:1 (Today past marks) — `system/templates/dashboard/style.css:374`
- **P1** [dashboard] Thermo Scan light: --day-past #A3AECB on --day-page #F1F4FA is 2.01:1, needs 3.0:1 (Today past marks) — `system/templates/dashboard/style.css:421`
- **P1** [dashboard] Thermo Scan dark: --day-past #3E4C7E on --day-page #050B26 is 2.35:1, needs 3.0:1 (Today past marks) — `system/templates/dashboard/style.css:435`
- **P1** [reference] base light: --faint #8A949D on --bg #F6F7F8 is 2.88:1, needs 4.5:1 (text on a ground) — `dev/reference/dashboard-reference.html:10`
- **P1** [reference] base light: --faint #8A949D on --surface #FFFFFF is 3.09:1, needs 4.5:1 (text on a ground) — `dev/reference/dashboard-reference.html:10`
- **P1** [reference] base light: --faint #8A949D on --sunk #EEF1F3 is 2.72:1, needs 4.5:1 (text on a ground) — `dev/reference/dashboard-reference.html:10`
- **P1** [reference] base dark: --focus #0B6E7F on --surface #181D21 is 2.87:1, needs 3.0:1 (UI mark) — `dev/reference/dashboard-reference.html:13`
- **P1** [reference] base dark: --faint #7D8790 on --sunk #1F252A is 4.23:1, needs 4.5:1 (text on a ground) — `dev/reference/dashboard-reference.html:21`

## 8. Cross-surface consistency (28)

Each surface's role colours and fonts (the first column is the reference):

| Role | dashboard (creaite) | dashboard (Brightwater) | guide-first-day | guide-how-to | offline | prep-page | reference | email drafts | Word |
|---|---|---|---|---|---|---|---|---|---|
| bg (light) | #F3F6F7 | #F8F8FF | #F3F6F7 | #F3F6F7 | #F6F7F8 | #F6F7F8 | #F6F7F8 |  |  |
| surface (light) | #FFFFFF | #FFFFFF | #FFFFFF | #FFFFFF | #FFFFFF | #FFFFFF | #FFFFFF |  |  |
| ink (light) | #14212A | #1E1F1E | #14212A | #14212A | #1A1F24 | #16202A | #1A1F24 | #1E1F1E | #1E1F1E |
| muted (light) | #4D5C66 | #5C5D60 | #4D5C66 | #4D5C66 | #5C6670 | #55616B | #5C6670 | #5C5D60 |  |
| line (light) | #D7DFE3 | #D9D9E0 | #D7DFE3 | #D7DFE3 | #E2E6EA | #DDE3E7 | #E2E6EA | #D9D9E0 |  |
| accent (light) | #0B6E7F | #1E1F1E | #0B6E7F | #0B6E7F | #0B6E7F | #0B6E7F | #0B6E7F |  | #2C6FAA |
| bad (light) | #B3261E | #B3261E |  |  |  | #A52A2A | #B3261E | #B3261E | #C0392B |
| warn (light) | #8A5A00 | #7A4F00 | #8A5A00 | #8A5A00 |  | #8A5A00 | #8A5A00 | #8A5A00 | #D68910 |
| ok (light) | #2E6B3A | #2E6B3A | #2E6B3A | #2E6B3A |  | #1B6B3A | #2E6B3A |  | #2E7D32 |
| inverse (light) |  |  |  |  |  |  |  |  | #1E1F1E |
| font body (light) | Source Sans 3 | ABC Diatype | Source Sans 3 | Source Sans 3 | system-ui | -apple-system | Roboto | Calibri | Calibri |
| font display (light) | Schibsted Grotesk |  | Schibsted Grotesk | Schibsted Grotesk |  |  |  |  | Aptos Display |
| font mono (light) | JetBrains Mono |  | JetBrains Mono | JetBrains Mono |  |  |  |  |  |
| bg (dark) | #0F1518 | #1E1F1E | #0F1518 | #0F1518 | #111518 | #0F1518 | #111518 |  |  |
| surface (dark) | #171E22 | #272827 | #171E22 | #171E22 | #181D21 | #171E22 | #181D21 |  |  |
| ink (dark) | #E4EAED | #F8F8FF | #E4EAED | #E4EAED | #E3E7EA | #E4EAED | #E3E7EA |  |  |
| muted (dark) | #A2AEB5 | #C2C8D6 | #A2AEB5 | #A2AEB5 | #A3ADB5 | #9AA7AF | #A3ADB5 |  |  |
| line (dark) | #2A343A | #3E403F | #2A343A | #2A343A | #2B3238 | #2A343A | #2B3238 |  |  |
| accent (dark) | #5FC4D6 | #91FF01 | #5FC4D6 | #5FC4D6 | #3FB6C8 | #5FC4D6 | #5FC4D6 |  |  |
| bad (dark) | #F2B8B5 | #F2B8B5 |  |  |  | #FF9B8F | #F2B8B5 |  |  |
| warn (dark) | #F0C66B | #F0C66B | #F0C66B | #F0C66B |  | #F0C46A | #F0C66B |  |  |
| ok (dark) | #9FD6A5 | #9FD6A5 | #9FD6A5 | #9FD6A5 |  | #6FD49A | #9FD6A5 |  |  |
| font body (dark) | Source Sans 3 | ABC Diatype | Source Sans 3 | Source Sans 3 | system-ui | -apple-system | Roboto |  |  |
| font display (dark) | Schibsted Grotesk |  | Schibsted Grotesk | Schibsted Grotesk |  |  |  |  |  |
| font mono (dark) | JetBrains Mono |  | JetBrains Mono | JetBrains Mono |  |  |  |  |  |

- **P2** [email drafts] email drafts body font is Calibri; the dashboard's is Source Sans 3 — `system/templates/dashboard/src/drafts.js`
- **P2** [offline] offline body font is system-ui; the dashboard's is Source Sans 3 — `system/templates/app/offline.html`
- **P2** [offline] offline dark accent #3FB6C8 differs from the dashboard's #5FC4D6 (ΔE 6.1) — `system/templates/app/offline.html`
- **P2** [prep-page] prep-page light bad #A52A2A differs from the dashboard's #B3261E (ΔE 11.4) — `system/scripts/prep_page.py`
- **P2** [prep-page] prep-page light ok #1B6B3A differs from the dashboard's #2E6B3A (ΔE 4.5) — `system/scripts/prep_page.py`
- **P2** [prep-page] prep-page body font is -apple-system; the dashboard's is Source Sans 3 — `system/scripts/prep_page.py`
- **P2** [prep-page] prep-page dark bad #FF9B8F differs from the dashboard's #F2B8B5 (ΔE 20.8) — `system/scripts/prep_page.py`
- **P2** [prep-page] prep-page dark ok #6FD49A differs from the dashboard's #9FD6A5 (ΔE 15.6) — `system/scripts/prep_page.py`
- **P2** [reference] reference body font is Roboto; the dashboard's is Source Sans 3 — `dev/reference/dashboard-reference.html`
- **P3** [Word] Word style Heading1 keeps Word's default colour #2E74B5 in 5/5 templates (not used in any template body; a report that adds headings will show it) — `system/templates/adhoc-template.docx`
- **P3** [Word] Word style Heading2 keeps Word's default colour #2E74B5 in 5/5 templates (not used in any template body; a report that adds headings will show it) — `system/templates/adhoc-template.docx`
- **P3** [Word] Word style Heading3 keeps Word's default colour #1F4D78 in 5/5 templates (not used in any template body; a report that adds headings will show it) — `system/templates/adhoc-template.docx`
- **P3** [Word] Word style Heading4 keeps Word's default colour #2E74B5 in 5/5 templates (not used in any template body; a report that adds headings will show it) — `system/templates/adhoc-template.docx`
- **P3** [Word] Word style Heading5 keeps Word's default colour #2E74B5 in 5/5 templates (not used in any template body; a report that adds headings will show it) — `system/templates/adhoc-template.docx`
- **P3** [Word] Word style Heading6 keeps Word's default colour #1F4D78 in 5/5 templates (not used in any template body; a report that adds headings will show it) — `system/templates/adhoc-template.docx`
- **P3** [Word] Word style Hyperlink keeps Word's default colour #0563C1 in 5/5 templates (not used in any template body; a report that adds headings will show it) — `system/templates/adhoc-template.docx`
- **P3** [Word] Word theme fonts are Aptos Display/Aptos (the Office default) in 5/5 templates while the body is Calibri; the Brightwater palette's note says never Aptos — `system/templates/adhoc-template.docx`
- **P3** [email drafts] email drafts light ink #1E1F1E differs from the dashboard's #14212A (ΔE 8.5) — `system/templates/dashboard/src/drafts.js`
- **P3** [email drafts] email drafts light muted #5C5D60 differs from the dashboard's #4D5C66 (ΔE 6.9) — `system/templates/dashboard/src/drafts.js`
- **P3** [email drafts] email drafts light line #D9D9E0 differs from the dashboard's #D7DFE3 (ΔE 3.6) — `system/templates/dashboard/src/drafts.js`
- **P3** [offline] offline light ink #1A1F24 differs from the dashboard's #14212A (ΔE 4.1) — `system/templates/app/offline.html`
- **P3** [offline] offline light muted #5C6670 differs from the dashboard's #4D5C66 (ΔE 4.9) — `system/templates/app/offline.html`
- **P3** [offline] offline light line #E2E6EA differs from the dashboard's #D7DFE3 (ΔE 3.1) — `system/templates/app/offline.html`
- **P3** [prep-page] prep-page light muted #55616B differs from the dashboard's #4D5C66 (ΔE 2.6) — `system/scripts/prep_page.py`
- **P3** [prep-page] prep-page dark muted #9AA7AF differs from the dashboard's #A2AEB5 (ΔE 2.7) — `system/scripts/prep_page.py`
- **P3** [reference] reference light ink #1A1F24 differs from the dashboard's #14212A (ΔE 4.1) — `dev/reference/dashboard-reference.html`
- **P3** [reference] reference light muted #5C6670 differs from the dashboard's #4D5C66 (ΔE 4.9) — `dev/reference/dashboard-reference.html`
- **P3** [reference] reference light line #E2E6EA differs from the dashboard's #D7DFE3 (ΔE 3.1) — `dev/reference/dashboard-reference.html`
