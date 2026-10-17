# Review: how others do it, options to improve it, and whether Intake and Review can be one

Product Manager, 17-10-2026. For Alan. Nothing here is built or on the board; it is for discussion before any mockup. The sources are vendor docs and articles found by search; where a search found nothing, that is said.

## The short answer

Review's job is the same as the best triage tools: a person makes a small number of fast decisions on things a machine prepared. Those tools win on four things we only half do: **a few decisions on single keys, the evidence next to the item, attention steered to the risky ones, and every decision easy to undo.** Intake and Review can be one destination, and the lightest version is cheap; the full merge into one pipeline is not worth doing before the 13-11-2026 AI ideas review.

## 1. What others do

| Source | What it teaches | Link |
|---|---|---|
| **Linear Triage** | A fixed, small set of decisions on single keys: 1 Accept, 2 Duplicate, 3 Decline (asks for a comment), H Snooze. Snooze returns the item at a time, or earlier if it gets new activity. | [Triage docs](https://linear.app/docs/triage), [Snooze](https://linear.app/docs/snooze) |
| **Inbox UX writing** | Triage should cost almost nothing (keys, one-key actions). Archive, snooze and send should confirm where the item went and how to get it back. | [SaaS inbox UX patterns](https://www.saasui.design/blog/saas-email-inbox-ux-patterns) |
| **HEY Screener** | Decide once per sender, not per message: a structural decision that removes later work. Snooze has a "Surprise me" option to avoid picking a time. | [Built for Mars on HEY](https://builtformars.com/company/hey) |
| **Superhuman** | The goal is to touch each email once. | [Superhuman for CEOs](https://blog.superhuman.com/how-ceos-can-organize-their-inbox/) |
| **Code-review tools** | Keyboard-first review; "next unviewed" to keep your place; a snapshot of what changed since your last visit. Users keep asking for next-unviewed navigation. | [cubic](https://docs.cubic.dev/code-review-platform/reviewing-prs), [Atlassian request](https://jira.atlassian.com/browse/BCLOUD-23623), [GitLab request](https://gitlab.com/gitlab-org/gitlab/-/issues/431260) |
| **Human-in-the-loop AI guidance** | Send attention to uncertain, unusual or high-impact items; low-risk, high-confidence ones can be batched. Beware automation bias (approving too fast) and approval fatigue. | [Zartis](https://www.zartis.com/human-in-the-loop-ui-patterns-designing-intentional-friction-for-safer-ai-products/), [Agent UX patterns](https://www.agenticwire.news/article/agent-ux-design-patterns) |
| **Otter** | Each action item links back to the moment in the conversation it came from. | [Otter action tracker](https://www.raptorgroup.com/news/otter-ai-launches-action-tracker/) |

Not found: how Fireflies and Granola let you check action items before they sync (the pages say what syncs, not whether you approve first), concrete specs for bulk approve with reasons, and any real design case study of a combined intake-and-review page. I have not copied a behaviour I could not see.

## 2. Where Review stands today

From the UX review (17-10-2026): "Stale" on every row (being fixed by #177); "Approve all from these minutes" looks like "Approve"; each row has both a checkbox and an Approve button; three lines of 12 px meta per row, so the eye cannot find what to do. Already good: grouped by project, a reason when you reject, One at a time and shortcuts, and the rule that bulk approval never covers minutes, decisions or risks.

## 3. Options to improve Review

**R1. One decision at a time as the default pass.** A progress line ("3 of 12"), **Approve**, **Edit**, **Reject with a reason**, **Later**, on keys, the next item opening after each decision, and an Undo for the last one. Linear and Superhuman's shape. Lists stay for browsing. Size M.

**R2. Evidence beside the item.** A side peek with the sentence from the minutes or the mail it came from, one click to the source, as Otter and code review do. Row meta shrinks to one line (owner, due, project). Fixes finding 4. Size M.

**R3. Attention first, routine batched.** Order by what needs a human: conflicts, possible matches, new decisions and risks first; routine, low-risk updates folded into one "Routine · 9" group with one clear **Approve routine**. This is the existing bulk rule made visible, not a change to it: nothing is approved without you, and bulk still never covers minutes, decisions or risks. Fixes finding 3. Size S to M.

**R4. Decide once for a series.** Like HEY's Screener: "Not needed for this series" or "Usually fine, check lightly", remembered. It is the same idea as #181 and belongs with it. Size M, later.

**R5. Since your last visit.** A quiet "new since Tuesday" marker and a "next unreviewed" key, from the code-review tools. Size S.

Recommended order: **R3 and R2 first** (they fix the findings on the page today), **R1** next, R4 and R5 later.

## 4. Can Intake and Review be one?

**C1. One pipeline page** (Arrived, Drafted, Approved). The cleanest picture, but it re-cuts the sidebar and names we just settled (#168, #156), and Review also holds proposals from mail and Teams sweeps, not only meetings. Not before 13-11-2026.

**C2. One destination, two lanes.** A single sidebar entry, **Intake and Review** (the name #168 already gives Today's block), with a switch at the top: To process (Intake) and To approve (Review), one badge, one row anatomy. Each lane keeps its own work. Cheapest; needs #179 and #180 first, because it relies on the shared row. Size M.

**C3. The meeting's row follows the work.** In the combined page a meeting is one row that moves from Ready to "Drafted: 7 proposals to check", and opens in place to approve them one at a time (R1). Review's cross-meeting list stays as a second lane for sweep and edit proposals. This matches the unit people think in (a meeting) and removes the trip between pages. Size L.

**C4. Keep both, link them tightly.** What #180 already does (the result on the row and Review them). Zero risk.

**Recommendation:** do #179 and #180, then **C2**; try **C3** as a prototype once R1 exists, because it depends on the one-at-a-time pass working well. Keep C1 as the long-term picture and decide it with the 13-11 review.

## 5. Questions for you

1. Which Review improvement first: R3 and R2 together (recommended), or R1?
2. Is a combined **Intake and Review** entry in the sidebar (C2) what you had in mind, or a single page (C1)?
3. Should "decide once for a series" (R4) join #181 as one later idea? Recommend yes.
4. Shall I mock up R3 and R2 and the C2 switch, in the style of the Intake mockup?
