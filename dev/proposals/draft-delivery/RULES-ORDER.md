# Rules diffs: order tests (23-10-2026)

Throwaway detached worktree off origin/v261-release2 (27a6bc1d). Each chain: `git apply --check` then apply, each diff in turn;
then `-R --check` and reverse apply in reverse order. VIP = `origin/v261-vip-rules` 29e03fd9, `vip-follow-rules/creaite-rules.md.diff`.
183 = `draft-delivery/rules-and-skill.diff` (regenerated, L3 and L4). 250 = `fetch-transcripts/creaite-rules.diff`; 250av = `creaite-rules.after-vip.diff`.

| Order | Forward | Reverse | Tree after reverse |
|-------|---------|---------|--------------------|
| 183, VIP, 250av (recommended) | applies | applies | clean |
| VIP, 183, 250av | applies | applies | clean |
| 183, 250 (no VIP) | applies | applies | clean |
| 183, VIP, 250 (plain) | 250 FAILS (cx-sweep row, edited by VIP) | n/a | use 250av |
| VIP, 183, 250 (plain) | 250 FAILS (same) | n/a | use 250av |

Findings:
- `creaite-rules.after-vip.diff` applies unchanged to the real VIP diff: no regeneration needed.
- VIP and 183 do not conflict in either order. VIP edits the Local bullet (line 11), the session-start line, the cx-sweep row and
  two later lines; 183 edits the Never bullet (line 16), the staging and scripts rows, the client report row, the Draft email bullet
  and the Assistant bullet. Their hunks share context only.
- 183's new "leaves the vault" bullet (L4) sits after "Confidential material", not in the Local bullet, so it cannot clash with VIP.
- 183 was regenerated for L3 (no client-report email claim) and L4; it applies to release2 and reverses cleanly.
