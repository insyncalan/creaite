# Competitor comparison: review, candidate gaps and the G2 decision (16-10-2026)

Kept for future reference. Written by the Product Manager session for Alan. The comparison under review is Alan's file "creaite vs the Top 5 Project Management Tools: A Critical Comparison" (the competitors are anonymised here because the repo is public; the key is kept outside git) (researched 16-10-2026, Competitor A, Competitor B, Competitor C, Competitor D, Competitor E, with two meeting assistants and a platform vendor's own stack as adjacent). It is in Alan's Downloads folder, not in git.

## The answer

The comparison is a good first draft that tilts toward creaite. Use it for the rivals' strengths and the evidence labels; do not use its verdicts or any comparative claim outside creaite until each is checked against the vendor's own documentation. Six real gaps came out of it (G1 to G6). Alan assessed G2 and chose the staged option; the others await his decision.

## Review of the comparison

What works: evidence labelled observed, documented or unverified; each rival's real strengths named (collaboration, mobile, live stakeholder access, dashboards); sources linked; an honest "flat cost trades money for your own time".

Problems, worst first:

1. **A recommendation that breaks creaite's rules.** Section 7 proposes "a published, read-only stakeholder view" and calls its absence the biggest gap. creaite's rules say never a web service or a published page (`system/creaite-rules.md`, Non-negotiables). Sharing by export is a design choice; v2.1.0 adds HTML export of reports.
2. **The test is built from creaite's own workflow**, so it rewards creaite by construction. Rivals are marked ✗ for "not found" although the doc's own legend says "not found" is not "does not exist"; creaite was observed, rivals were read from pricing pages.
3. **"Nothing else has approval-gated AI" is overstated.** Human review before filing is common practice (Competitor I recommends manual review before export; Competitor H logs every agent action). The doc did not verify that Competitor A files action items without review.
4. **"Every proposal carries a confidence label" is not in the code** (no confidence field in the dashboard source, `extraction.py` or `review.py`; what exists are flags: repeat, probably done, vague). Confidence labels are ideas #165 and #169.
5. **The cost table is shaky.** "Marginal (already paid)" ignores plan limits used by sweeps, alerts, prep pages and drafts (see BL-343, #87). Competitor D is listed as Team "2 to 15 users" and also "(solo)". Competitor A shows two price ladders. Vendor prices move fast: date-stamp or drop the dollar figures.
6. **Gaps a programme manager would test are missing:** budget and financials, resource and capacity, dependencies and Gantt, time tracking; also macOS only, needs Claude and Microsoft 365, one maintainer, no SLA, and the security and compliance review an employer would want.
7. **The comparison set omits real alternatives:** Excel, Word and Outlook (the status quo), Competitor J and Competitor K, a platform vendor's own meeting recap, a do-it-yourself Claude project.
8. **Section 7 overlaps the roadmap**, which the author had not seen: a rolling status log is v2.1.0's weekly report and the on-hold BL-317 (#27); AI-suggested health is #167; auto-assign owners and dates is already done (creaite proposes both); work-item approvals do not fit a single-user tool.

Before external use: no printed claim of the form "Competitor A cannot do X". The honest public message is the brochure's: creaite proposes, you approve, your tracker stays on your Mac.

## Candidate gaps (G1 to G6)

| # | Idea | Real gap? | Already covered? | Size | Lean | Status |
|---|---|---|---|---|---|---|
| G1 | Budget and financials per project (planned, actual, forecast, variance in the report) | The tracker has no cost or budget fields at all | No | L | Ask Alan whether he tracks money in creaite or elsewhere | Awaiting Alan |
| G2 | Dependencies and slip radar: "if this slips, what is hit" | Links exist but nothing follows a slip downstream | Partly: BL-125 stage B (#28, on hold), #164, #166 | M | Merge into #164 and #28, no new item | **Decided 16-10-2026 (below)** |
| G3 | Workload per person, overload warnings | People shows who has work, not whether it is too much | Partly: #166 | S to M | Merge into #166 | Awaiting Alan |
| G4 | People hygiene: spot and merge duplicate people, fill missing owners | The comparison's author reported duplicates in Alan's data; not verified by me | No | S to M | Add once Alan confirms it is real | Awaiting Alan |
| G5 | Usage meter in Settings: what creaite's runs use, per kind (sweep, alerts, prep, drafts) | "Flat cost" is untested; nothing shows the use of the Claude plan | Related: BL-343 (#87) but it does not show Alan | S to M | Add | Awaiting Alan |
| G6 | A "how creaite handles your data" page for employer IT sign-off | Rivals' security and compliance is a gap in adoption; a document, not a feature | No | S | Add, to `dev/marketing/` | Awaiting Alan |

Covered or rejected: live stakeholder access (conflicts with the no-published-page rule; HTML export arrives in v2.1.0); mobile and multi-user (desktop only, single user, Alan's decisions); rolling status log (v2.1.0 and BL-317); AI-suggested health (#167); auto-assign owners and dates (already proposed); notetaker joining calls (the issue is connector reliability, covered by the new Help page "Why isn't my meeting in Intake"); work-item approvals and time tracking (wrong fit for one user).

## G2: what exists, the gap, the decision

**What exists today.** The `links` table (one item blocks another; either end an action, RAID item, milestone, decision or promise, in any project). A dependency attached to a milestone, with a date warning, a Dependencies card and a Work filter. Actions link to a milestone. **BL-125 stage B** (on hold, Alan, 13-10-2026) extends dependencies to actions and RAID items, in the same project or another, with suggestions in Review, a warning when a blocker is due after what it blocks, and "waiting on" and at-risk markers. It excludes an automatic critical path and dates that move targets automatically. **#164** (Idea) is a nightly milestone radar with propose-only re-plan options.

**The gap.** Nothing follows a slip downstream. Stage B shows one "waiting on" link, not what a slip finally knocks onto, in how many days, or across projects. The knock-on is a chain walk that counts days late; it is not a full critical-path calculation.

**Options put to Alan.** A: nothing new. B: staged (recommended). C: un-hold stage B now and build links first. **Alan chose B on 16-10-2026**, confirmed to Jarvis directly, logged in HEAD-LOG.

**What was done on the board (no new item):**
- **#164** is built in two stages. Stage 1, the radar, warns on overdue, re-dated and quiet items on the way to a milestone, using what exists today (action-to-milestone links, dependencies on milestones, `forecast.py`'s slip history); it needs nothing from BL-125. Stage 2, the knock-on and what-if, follows blockers downstream to milestones and across projects with slip in days and lets Alan re-date something to see the effect before staging it; it depends on stage B. Propose-only throughout.
- **#28** (BL-125, stays on hold): stage B gains the knock-on view and the what-if as Done-when points; its exclusions stay; a note says #164 stage 2 reads it.
- **#166** (programme brain) notes that cross-project dependencies are one of its signals.

**The gate (13-11-2026 review).** Un-hold stage B only if stage 1 shows that missing links are what limits the radar. Links only exist when Alan accepts the suggestions, so the knock-on is only as good as his data. **Open task: three read-only counts from Alan's real tracker**, which neither Jarvis nor the repo can read (it holds sample data only): (1) Dependency items in the raid table; (2) rows in `links`; (3) actions with a milestone attached. If there are fewer than about ten links, stage B stays on hold. Alan, or his vault's Claude session, or ask creaite in the dashboard can run them. Jarvis puts the ask in the next digest.

## Related items

- AI ideas, state Idea, review about 13-11-2026: #163 triage and routing, #164 risk prediction and re-planning, #165 meeting to RAID log, #166 programme brain, #167 health that argues back, #169 minutes confidence label, #170 weekly report confidence sweep.
- BL-125 (#28), BL-343 (#87), BL-317 (#27, on hold), #162 (health trend bars).
- Marketing collateral: `dev/marketing/`.
