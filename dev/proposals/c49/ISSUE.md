# Keyboard/focus gaps from the 1.9.5 hand checks (v2.6.1)

Source: `dev/tests/handchecks/test_v195.py` check 49 (BL-316's keyboard script against the hand-check demo vault), run on
v26-line-4 (83015698) on 22-10-2026: 8 key failures. Each was run again on origin/main (2.5.3, cfe9b56c) with the same
harness (the line's `test_v195.py`, `hcbase.py`, `test_shared_behaviour.py`, `test_shared_undo.py` over main's product), and
on the line with a fresh hand-check vault per run.

**Result: no regression in 2.6.** None of the 8 is a product bug introduced by the 2.6 line; nothing blocks 2.6.0.

## Cause of items 3 to 8: one harness leak, not the product

The hand-check driver's `goto` (`hcbase.behaviour_driver`) closed only #cmdk, #prepDlg and #parchDlg between screens. The
`minutes-approve` screen *is* the modal #mnApprove, so it stayed open over every later screen and made the page inert:
later openers "can't take focus", Enter "opens nothing", → on the rail opens nothing, Esc can't return focus. Proven:
after `minutes-approve`, the next screen still has `mnApprove:modal` open and `SB.focus` fails, **on main and on the line
alike** (main's own c49 never got this far: it crashed on `minutes-deadline` with the same leftover dialog). Run without
the screens after it (`SB_ONLY=today,today-days,clientreport,minutes,minutes-approve,work-board`) items 3 to 8 pass on
both main and the line, on a fresh vault. Fixed in the test on `v26-c49-fix` (goto closes every open dialog).

A related harness slip, also fixed there: test_shared_behaviour renamed `Driver.settle` to `settle_screen` in 2.6, so
hcbase's override (the demo's ready check) was no longer called.

## The 8 items

| # | Screen | What fails (c49 line) | Pre-existing (fails on 2.5.3)? | Class |
|---|--------|------------------------|-------------------------------|-------|
| 1 | Today, meeting title peek (`span.dmti`) | focus stays outside the popup | Yes | **By design** (#111): non-modal Prep peek, no focus trap, opens on keyboard focus; focus stays on the title. Test model changed: the Enter script skips it, `prep_peek` checks focus-opens, focus stays, Esc closes with focus on the title. Passes. |
| 2 | Today and Today's day tabs, Prep chip (`button.wkchip` "Open the prep page for …"), two lines | Enter opens nothing | Yes (both) | **By design** (#111): the chip's Enter goes to the prep page; the peek opens on focus. Same test-model change; passes. |
| 3 | Shell, rail flyouts (`#railFly`, Work and Projects) | → opens nothing | Same harness leak on main; passes on main and line when the leak is removed | **Harness/run state** (leftover #mnApprove modal), not a product bug |
| 4 | Client report hub, week button (`#hubWeek`) | it can't take focus | As 3 | **Harness/run state**, not a product bug |
| 5 | Client report, "Left out of the client's report" (`#crLeftDlg`) | Esc doesn't return focus to its control | As 3 | **Harness/run state**, not a product bug |
| 6 | Minutes, "Before approving" (`#mnApprove`) | Enter opens nothing | As 3 (rechecked on a fresh vault: passes; the demo's draft minutes has a real problem, so #268's box does open) | **Harness/run state**, not vault data. Note: since #268 the box opens only for a ticked item's real problem, so on a vault whose minutes have none this check would say "opens nothing" by design |
| 7 | Work board, "Due date for" (`#boardDlg`) | Enter on a card's Move button opens nothing | As 3 (fresh vault: passes) | **Harness/run state**, not vault data |
| 8 | Today's day tabs, Prep chip (the second `wkchip` line; counted with 2 in the brief) | Enter opens nothing | Yes | **By design**, as 2 |

## After the fix

Full check 49 on `v26-c49-fix` (fresh vault, 23 min): **0 key failures**. The Undo half, previously never asserted
(keys failed first, and the leftover modal blocked its choices), now reports 3:

- `undo: milestone-editor button#mvOwner “Owner, not set”: a change is saved with no Undo`
- `undo: review-peek button#pkReject “Reject”: a change is saved with no Undo`
- `undo: work-decisions button#newBtn “New decision”: a change is saved with no Undo`

Each passes run on its own (`SB_ONLY=work-decisions,review-peek,milestone-editor`) on main and on the line alike, so
they depend on what earlier screens leave behind (run order), as items 3 to 8 did. Not regressions; triage in 2.6.1.

## Still open for 2.6.1 (not regressions)

- ~~The 3 order-dependent Undo lines above~~ **Done (#297, 22-10-2026): timing in the harness, no screen leaks.** Bisected with
  `SB_ONLY` (the first and second halves of the screens, each with the three): both green; four full runs (three on the line,
  one on d42ee478, load 3 to 23) green too, so no earlier screen leaves state behind. The three are the changes that offer Undo
  only once /api/apply answers (not shown at once), and the Undo pick allowed a fixed 3 s: on a busy machine late in the run
  that was too short. Holding /api/apply back 3.5 s turns #mvOwner and #pkReject red the same way, alone. hcbase's driver now
  waits for the page's own requests to end before it looks for the Undo (and after pressing it); the check is unchanged and
  every screen still runs. Full c49 after it: OK (24 min).
- `notes`, `notes-ai`, `notes-session` and `ndel` screens go to project ABC through a callable that `behaviour_screens`
  doesn't rename to FAL, so the demo never shows them ("screens the demo doesn't show"). Harness gap; same on main.
- `minutes-deadline` times out on the demo (`.mnpop` not shown). Harness/demo gap; same on main.
- `today-days` "Earlier days" (`.dypastbtn`) "can't take focus" appeared once in a restricted run (main and line alike)
  after the Prep chip's Enter navigated away; gone with the test-model change. Watch it.
