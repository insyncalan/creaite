# Alan's morning list, 17-10-2026

Everything that waited on Alan, with the Product Manager's recommendation, one line each. Drafted overnight on 16-10-2026. **Alan answered on 17-10-2026 (relayed by Jarvis; the decisions are Jarvis's to record in HEAD-LOG once Alan confirms them directly).** Each entry now ends with its status: Decided, Parked (kept, not now), Skipped (dropped) or Pending.


## Overnight, 17-10-2026 (added after the first list): needs Alan

Everything below is guarded or release-gating, so only Alan decides. One line each, with the Product Manager's recommendation. A (F1) and G (the client gate) decide whether and when 2.1.0 publishes: take them first and together.

A. **F1, the v2.1.0 publish decision (decide this first).** The Opus review found that the new wildcard expansion in the guard (reach.py) has no real time limit and can hang the guard hook. Jarvis put the publish on hold; Tests are green on f9e9934b. Team Cap is building a guarded fix on v210-guard-f1. Options: (1) approve the fix, wait for a fresh Tests run, then publish; (2) publish f9e9934b as it is; (3) publish without A5/A6. Recommend (1): a hung guard hook blocks every ask creaite run, and the fix is small and has its own tests; (2) is the fallback if the delay matters more to you.
G. **Client gate (#127), ranked with F1: a High the review found is not fixed in the v2.1.0 candidate.** Team Cap's review found that a link address over 2,000 characters is never %-decoded. So an encoded health reason, a name or an internal ID that comes after about 2,100 characters of padding passes the approve, export and Word-draft checks, while Word shows the URL. The fixes are on client-gate-127d (62593f6), and an Opus delta review is due about 05:30. Options: publish with the known gap, or hold for the reviewed 127d. Recommend: hold for 127d, because 2.1.0 is the client-safety release and a client report is the one place a leak cannot be taken back. Decide F1 and G together: if you approve F1's fix, 127d can go into the same fresh Tests run.
B. **v2.1.0 side bar: the Reports item has no icon** (RailIcon.jsx lacks "filetext"; one table entry fixes it). It shows on every page of the release candidate. Recommend: fix it in the same v210-guard-f1 run, so it is one fresh Tests run; if you publish f9e9934b as is, it ships and goes in 2.1.1.
C. **#117, the combined edit_ai.py (guarded diff, nothing applied).** Team Stark's branch edit-ai-proposal 4762f76f merges the 2.1.0 side (the client-gated report, minutes and read-only places) with the selection bar's additions. Their claim: no client-gated place sees anything new, and the built prompts for every report and minutes option are byte-identical to the base, pinned by a new test. Recommend: approve, after Jarvis or an Opus review confirms the byte-identical claim on the diff.
D. **#119, the notes autosave server half (guarded diff, nothing applied).** Branch notes-119-proposal: removes the draft route, a save can name its editing session, filechange keeps one backup per session (a session ends after five idle minutes); +22/-48 in live_server.py. Recommend: approve. You already accepted losing up to two seconds on a crash, and the backup limit stops autosave flooding the backups.
E. **#146, one line in live_server.py SAFE_SETTINGS:** add sweep.max_lookback_days beside sweep.first_run_lookback_days so ask creaite can change your three-day cap. Recommend: yes; it is a plain number. Skip it only if you do not want ask creaite to change it.
F. **#158, Help word budget.** Help is now 23,260 words (33,506 at the start) against your 14,791 target. The pages left are at the floor: cutting more drops true facts. Recommend: relax the target to about 22,000 for 2.2.0 and finish trimming the big Reference pages in 2.2.1. Also: two stale passages in the 2.1.0 Help still describe the retired meeting page; a patch (help-210-patch bbeeafde) is ready for Jarvis to cherry-pick.

Reviews I posted on the board overnight (no decision needed): #162 and #168 match your decisions; #156 and #111 piece A match their designs (with the Reports icon and a few missing pictures noted); #134 is a first slice only (the sheet toolbar, narrower than designed); #119's page half matches.

---

## Decide first (they unblock work)

1. **Private projects (my four questions, asked 16-10-2026, unanswered).** (a) Which meaning: personal (not for the employer), confidential work, or hidden from onlookers? Recommend personal. (b) Should ask creaite and search see Private projects? Recommend no, unless inside that project. (c) Should they appear in Today and the digest? Recommend no by default, with a switch. (d) Where do their files live? Recommend a local folder outside the company OneDrive, left out of the offsite backup zip. Then I write it up with a mockup. **Status: Parked.**
2. **The three counts for the #164 stage 2 gate (needed by 13-11-2026).** From the real tracker, read only: Dependency items in the raid table, rows in `links`, actions with a milestone. Jarvis cannot read your vault. Recommend asking ask creaite in the dashboard, or your vault's Claude session; fewer than about ten links keeps BL-125 stage B (#28) on hold. **Status: Parked.** The 13-11 gate still needs the counts if stage B is ever wanted.
3. **The competitor-name scrub Jarvis flagged** (`dev/BACKLOG.md`, `dev/archive/BACKLOG-before-the-board.md`, `dev/tools/board-plan.json`, and the logo README). The mentions are neutral: "research into how three reference products are built" (13-10-2026, your own inspiration notes, three product names) and one note on another product's logo. Recommend leave them: they praise or study, claim nothing about a rival, and the names stay in git history anyway; BACKLOG.md is a generated export, so editing it means editing the board issues. If you want them gone, replace the names with "three reference products" and I will do it. **Status: Decided.** Jarvis did the scrub on main (884aaa75).
4. **#27, the project page as tabs (seven questions).** You took it off your radar and put it on hold. Recommend it stays parked and off the list; it returns only when you say. **Status: Parked.**

## Quick yes or no

5. **Colourful treatment for the one pager and brochure.** The infographic is multi-colour. Recommend yes: the same five-colour palette on the other pages. Say "yes" and I do it. **Status: Decided, yes.** Done: the same five-colour treatment is on the one pager and brochure (408f39cf).
6. **Marketing audience and name.** I assumed programme managers at other firms, no company name, a placeholder contact line. Recommend confirm, and give me the contact line or link. **Status: Parked.**
7. **Brochure PDFs.** I cannot export them. Recommend you press Export PDF on the design page and drop the files into `dev/marketing/` (or say so and I will add a note). **Status: Parked.**
8. **Competitor candidate gaps (the file `competitor-comparison-review-2026-10-16.md`).** G1 budget and financials (recommend: first say whether you track money in creaite); G3 workload per person (merge into #166); G4 duplicate people (add once you confirm the duplicates are real); G5 a usage meter (add); G6 a "how creaite handles your data" page for employer IT (add, to `dev/marketing/`). One word each: add, merge or skip. **Status: Skipped.** All competitor gaps (G1 to G6) are dropped.
9. **UX and usability review.** Recommend: let me run the Project Wallace baseline and the Impeccable detector and critique, read only, on the dashboard (a scratch clone, nothing written to the repo), and bring a ranked findings list for you to assess. Separately, name four or five programme managers who could give an hour for a screen-share usability session; recommend yes to both. **Status: Pending.** Alan has the plain explanation of the Project Wallace baseline and the Impeccable detector; the Product Manager does not run either until Alan says so.

## For the 13-11-2026 review (no decision needed now)

10. **The nine AI ideas, state Idea:** #163 triage (re-order only, or a collapsed "probably noise" group? recommend re-order only), #164 risk radar (per project, or also a cross-project list? recommend per project first), #165 meeting to RAID, #166 programme brain (themes, or people and capacity? recommend people and capacity first), #167 health that argues back (project page, or only when editing health? recommend the health editor), #169 minutes confidence (three levels, or a percentage? recommend three), #170 weekly report sweep (a button, or automatic? recommend a button first). I bring the Activity > Quality numbers. **Status: Decided.** The nine AI ideas stay in Idea, not in priority.

## When v2.1.0 is cut

11. **Your hand checks (#157), 23 steps in `dev/handchecks/v2.1.0-walkthrough.md`.** The first seven need your hands on laptop 1. Recommend doing them in one sitting after the cut. **Status: Fine.**
12. **Release-note lines to strike.** Jarvis will tell me which lines in `dev/release-notes/2.1.0-plain.md` to strike if an item misses the cut; the #126 line goes in only if it lands. Nothing for you to do unless you want to see the final text. **Status: Fine.**

## No action, for information

- #162 (health trend: B bars, 6 weeks, ? legend, stored reason) and #168 (Intake and Review, above Week ahead) are Ready.
- The Help Phase A brief is updated: batch 2 runs per item, no page waits for a cut.
- The marketing sources and the competitor review are in git (anonymised); the name key is not.
