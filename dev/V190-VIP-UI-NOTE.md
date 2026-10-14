# v1.9.0: BL-288 part 2 and BL-296 (sprint-vip-ui), takeover note

Team 1 built this branch and paused it on 13-10-2026 (feature in 03aaa35; fcc81a3 merged main, tests not re-run). Taken
over on 14-10-2026 with Alan's approval.

## What Team 1 built (03aaa35)

- **BL-288 part 2, no "VIP" on screen.** The chip is gone from Work's owner and maker cells, Review, the person page,
  Settings › People and Today. Work's filter is **People I follow** (Owned by / Made by someone I follow, Not followed).
  Today's block is **Messages to see first**; the reminder line, the early-warning label ("Overdue item owned by someone
  you follow closely"), the rail badge ("n messages to see first"), the window title (a plain "(n) creaite…") and the
  browser notification (the sender's name only) are neutral. The Draft email note is dropped; the ignore-rules help no
  longer names VIPs. The word stays only in the person form's VIP field, the register's column and Settings › VIP alerts.
- **BL-296, Dismiss or Create work item.** Each row has **Create work item** and **Dismiss** (with Undo). Create work
  item opens the new-item peek from `/api/alerts/prefill` (references only) with a strip: Action, Risk, Issue or
  Decision; **Draft from the message** (`/api/alerts/draft`; follows Sharpen, refused for private or confidential);
  **Save** (⌘↵, staged through `/api/alerts/make`, then applied; the alert records `made`); **Cancel** leaves it.

## Takeover

- Merged `origin/main` (dev-test-steadiness) into the branch: no conflicts; the dashboard build was already current.
- **Fix (Help):** the VIPs reference line still said alerts stay "until you press Seen"; it now says **Messages to see
  first** and **Dismiss** or **Create work item**. The how-to's "only places the word appears" now begins "Apart from
  this Help", since Help itself describes the feature. `guide-how-to.html` rebuilt.
- Audit: no other on-screen or generated "VIP" found outside the allowed places. Strings left alone because they never
  reach the screen or a document: server log lines (`VIP check: n new alerts`), the VIP check's error (returned by
  `/api/vip` but not shown), `sweep.py` command-line output, and the VIP check's own prompt.

## Tests (all pass, -j 2)

test_vip_screens, test_vip_private, test_alert_actions, test_sweep_alerts, test_dashboard_editing, test_run_badge,
test_people_filters, test_today_brief, test_snapshots, test_dashboard_split, test_help, test_help_loop, test_ui_sweep,
test_work_filters_live; `dev/tools/check.py`: OK.

## Goldens

None re-recorded in the takeover. Team 1 re-recorded two in 03aaa35, both BL-288's intended wording: `settings-capture`
(the ignore-rules sentence) and `settings-health` (the early-warning label). Both still match after the merge.
