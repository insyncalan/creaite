"""creaite settings catalogue (BL-320): every setting's group, Essentials or Advanced, default, and why that default.

The defaults themselves live in one place, system/templates/settings-defaults.json; this module never repeats a value. It adds,
for each default key, what a person reads in Settings: the group it sits in, whether it is one of the Essentials (about sixteen
rows that change Alan's day) or Advanced (the rest, searchable), a label, one line on what it does, and the reason for its
default, written out. dev/tests/test_settings_catalogue.py fails if a default key has no entry here, or an entry no default.

It also works out which settings differ from their default ("changed") and resets one to its default through the dashboard's
own save path (`save`, the same steps as the page's writeSettings): a backup of settings.json in system/backups/settings-<stamp>.json,
the new file written whole, one line per key in system/config/settings-log.jsonl ({at, key, old, new}).

Library only (no command line): the live server's /api/settings/catalogue and /api/settings/reset use it.
"""
import copy
import json
import sys
import threading
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

DEFAULTS_FILE = paths.TEMPLATES / "settings-defaults.json"
SKIP = ("_about", "note")                 # descriptions, not settings
MAP_KEYS = ("prep.series",)               # a dict that is one setting (a map Alan fills), not a group of settings
UNORDERED = ("work.weekend_days", "dashboard.week_ahead_priorities", "identity.short_forms", "identity.own_domains",
             "locations.never_index", "reminders.dismissed_forever", "dashboard.rail.hidden")   # order means nothing
RETIRE_AFTER_DAYS = 30                    # a setting never changed in a log this old is a candidate to retire (counts only)
LOCK = threading.Lock()                   # one settings save at a time from the server

ESSENTIALS, ADVANCED, DEVELOPER = "essentials", "advanced", "developer"
# The Essentials, as rows (BL-320, from the accepted mockup): (section, label, one line, keys). A row may cover several keys
# (what the sweep reads is five switches; AI drafts is every kind). A key in a row is an Essential; every other key is Advanced.
ESSENTIAL_ROWS = (
    ("You", "Your name", "Set at first start. creaite uses it to know which items are yours.", ("identity.name",)),
    ("You", "Weekend", "No reminders or \"due\" warnings fall on these days.", ("work.weekend_days",)),
    ("Your day", "Morning sweep from", "creaite catches up on mail and Teams when you first open it after this time.",
     ("sweep.due_from",)),
    ("Your day", "What the sweep reads", "Inbox, Sent Items, Teams chats and channels, your calendar.",
     ("sweep.sources.inbox", "sweep.sources.sent_items", "sweep.sources.teams_chats", "sweep.sources.teams_channels",
      "sweep.sources.calendar")),
    ("Your day", "Evening, offer Close the day from", "A quiet dot on the door icon, never a pop-up.", ("day.close_from",)),
    ("Your day", "Catch up before closing", "Starts a sweep if the last one was a while ago.", ("day.catchup_sweep",)),
    ("Your day", "Weekly report reminder", "One line on Today until each report is approved.",
     ("reminders.weekly_report_day", "reminders.weekly_report_from")),
    ("Saving and review", "Save my changes at once",
     "Your own edits are saved straight away, with Undo. What creaite suggests always waits in Review.", ("dashboard.auto_apply",)),
    ("Saving and review", "Week ahead shows", "Which priorities appear in Today's Week ahead. Milestones and meetings always do.",
     ("dashboard.week_ahead_priorities",)),
    ("People I follow", "Tell me when they write", "Their messages head Today until you dismiss them. Only you see who you follow.",
     ("vip.enabled",)),
    ("People I follow", "Check every", "While creaite is open.", ("vip.check_minutes",)),
    ("Look and help", "Theme", "Light, dark, or follow your Mac.", ("dashboard.theme",)),
    ("Look and help", "Style", "The look of the whole app.", ("dashboard.palette",)),
    ("Look and help", "Motion", "Follows your Mac's Reduce motion unless you choose.", ("dashboard.motion",)),
    ("Look and help", "AI drafts", "Suggestions you can use, edit or ignore. Never applied by themselves.",
     ("drafting.update", "drafting.client", "drafting.thinking", "drafting.reason", "drafting.agenda", "drafting.email",
      "drafting.forms", "drafting.repeat", "drafting.done", "drafting.sharpen", "drafting.shape")),
    ("Safety", "Daily backup, and a copy in OneDrive",
     "The database is backed up each day; with the projects in OneDrive a closed zip (database, settings, staging, history) "
     "goes to your _Portfolio folder. Chats, who you follow and the live database never leave the laptop.",
     ("backups.daily",)),
)

# Every default key: key -> (group, label, what it does, why this default). Groups are the Advanced area's headings; an Essential's
# group is its row's section. `resettable` is False (FIXED) for settings that only set-up or creaite itself may change.
FIXED = ("excel.export", "live_mode.required", "live_mode.port", "assistant.enabled", "people.added", "people.hidden",
         "workstreams.added", "workstreams.hidden", "locations.projects_root", "locations.portfolio", "locations.skeleton",
         "locations.folders.transcripts", "locations.folders.minutes", "locations.folders.weekly_reports",
         "locations.folders.client_reports", "locations.folders.adhoc_documents", "locations.folders.images",
         "locations.folders.steerco", "locations.folders.agendas", "locations.folders.notes", "locations.never_index",
         "locations.offsite_backup")
FIXED_WHY = {
    "excel.export": "a description of how the export runs, not a choice",
    "live_mode.required": "the dashboard needs the live server (IT-approved); not a choice",
    "live_mode.port": "the installed app belongs to its port; change it at set-up",
    "assistant.enabled": "ask creaite's switch is kept out of the screens on purpose",
    "people.added": "an old list; set-up moves it into the people register",
    "people.hidden": "an old list; set-up moves it into the people register",
    "workstreams.added": "an old list; set-up moves it into the workstreams table",
    "workstreams.hidden": "an old list; set-up moves it into the workstreams table",
}
CATALOGUE = {
    # ── Sweep
    "sweep.due_from": ("Your day", "Morning sweep from", "The time after which the first session of the day sweeps mail and Teams.",
                       "Before the first meeting, after overnight mail from other time zones."),
    "promises.from_sweep": ("Sweep", "Promises from the sweep",                               # BL-125 A (joined on release-192)
                            "Let the sweep propose promises from mail and Teams; promises from meetings and your own are unaffected.",
                            "Off: promises come from meetings and from you until the sweep's are trusted."),
    "sweep.first_run_lookback_days": ("Sweep", "First sweep looks back", "How many days the very first sweep reads.",
                                      "Two weeks catches what's still live without flooding Review on day one."),
    "sweep.sources.inbox": ("Your day", "Sweep reads: Inbox", "Mail you received.",
                            "Missing a source is worse than one more proposal; ignore rules handle the noise."),
    "sweep.sources.sent_items": ("Your day", "Sweep reads: Sent Items", "Mail you sent, where your own promises are.",
                                 "Missing a source is worse than one more proposal; ignore rules handle the noise."),
    "sweep.sources.teams_chats": ("Your day", "Sweep reads: Teams chats", "Your one-to-one and group chats.",
                                  "Missing a source is worse than one more proposal; ignore rules handle the noise."),
    "sweep.sources.teams_channels": ("Your day", "Sweep reads: Teams channels", "Channel posts in your teams.",
                                     "Missing a source is worse than one more proposal; ignore rules handle the noise."),
    "sweep.sources.calendar": ("Your day", "Sweep reads: calendar", "The week's meetings, for Today, Intake and prep.",
                               "Today's day view and meeting prep need it."),
    "sweep.show_possible_matches": ("Sweep", "Show possible matches",
                                    "Messages that may belong to a project are shown in Review to place, not dropped.",
                                    "A weak match you can place is better than a message silently lost."),
    "sweep.ignore": ("Sweep", "Ignore rules", "Mail, Teams and invites the sweep skips (counted, never read into proposals).",
                     "Private items are always skipped; the rest are common noise you can switch off or edit."),
    # ── People I follow
    "vip.enabled": ("People I follow", "Tell me when they write", "Messages from people you follow head Today.",
                    "On: these are the people you can't afford to miss."),
    "vip.check_minutes": ("People I follow", "Check every (minutes)", "How often the live server looks for their messages.",
                          "Fast enough to matter, light on Microsoft 365 calls."),
    "vip.notify": ("People I follow", "Browser notification", "Also show a notification on the Mac, not only on Today.",
                   "On: an alert you don't see until you open Today is late; nothing leaves the laptop."),
    # ── Reminders
    "reminders.enabled": ("Reminders", "Report reminders", "Weekly and client report reminders on Today and at session start.",
                          "On: a reminder is one line and never drafts anything by itself."),
    "reminders.weekly_report_day": ("Your day", "Weekly report reminder: day", "The day the weekly report reminder starts.",
                                    "Friday leaves time to draft before the weekend."),
    "reminders.weekly_report_from": ("Your day", "Weekly report reminder: from", "The time on that day it starts.",
                                     "Midday: the week's meetings are mostly done, the afternoon is left to write."),
    "reminders.dismissed_forever": ("Reminders", "Dismissed reminders", "Reminders and notices you dismissed for good.",
                                    "Empty: nothing is hidden until you hide it. Reset brings them all back."),
    # ── Review
    "review.stale_after_days": ("Review", "Stale after (days)", "An open action with no update for this long counts as stale.",
                                "A week: one reporting cycle without news is worth a nudge."),
    "review.auto_advance": ("Review", "Move to the next item", "After a decision, Review moves on to the next item.",
                            "On: approving a batch is quicker without reaching for the next row."),
    "review.duplicate_overlap": ("Review", "Duplicate likeness",
                                 "How alike (0 to 1) a proposal must be to an open item to be tagged a likely repeat.",
                                 "0.6 catches reworded repeats without tagging items that merely share a topic."),
    "review.due_soon_days": ("Review", "Due soon (days)", "How far ahead counts as due soon.", "A week matches the weekly rhythm."),
    "review.spot_check_every": ("Review", "Spot-check one in", "When approving routine items together, one in this many is shown to check.",
                                "One in ten keeps bulk approval honest without slowing it down; 0 shows none."),
    # ── Health thresholds
    "health.at_risk_overdue_days": ("Health thresholds", "At risk: overdue for (days)",
                                    "An action overdue this long suggests At risk.", "A week overdue is a pattern, not a slip."),
    "health.at_risk_milestone_slip_weeks_max": ("Health thresholds", "At risk: milestone slip up to (weeks)",
                                                "A milestone forecast up to this many weeks late suggests At risk.",
                                                "Up to two weeks can usually still be recovered."),
    "health.off_track_milestone_slip_weeks_over": ("Health thresholds", "Off track: milestone slip over (weeks)",
                                                   "More than this many weeks late suggests Off track.",
                                                   "Beyond two weeks a milestone usually needs re-planning."),
    "health.off_track_urgent_risks_min": ("Health thresholds", "Off track: urgent risks from",
                                          "This many open Urgent risks suggests Off track.",
                                          "One urgent risk is managed; two at once is a project in trouble."),
    # ── Look and layout, Work and views
    "dashboard.default_tab": ("Work and views", "Opening page", "The page creaite opens on.", "Portfolio: the whole picture first."),
    "dashboard.theme": ("Look and help", "Theme", "Light, dark, or follow the Mac.", "Follows your Mac, so it matches your other apps."),
    "dashboard.palette": ("Look and help", "Style", "The named look of the whole app.", "creaite, the house style."),
    "dashboard.motion": ("Look and help", "Motion", "Animations: follow the Mac, reduce or full.",
                         "Follows your Mac's accessibility setting."),
    "dashboard.files_show_inbox": ("Work and views", "Files: show Intake", "List the files waiting in Intake on Files.",
                                   "On: a waiting transcript should be seen."),
    "dashboard.files_show_portfolio": ("Work and views", "Files: show the portfolio", "List the portfolio's own meetings on Files.",
                                       "On: cross-project meetings matter as much as project ones."),
    "dashboard.files_show_documents": ("Work and views", "Files: show documents", "List each project's documents on Files.",
                                       "Off: documents are many and passive; search still reads them."),
    "dashboard.week_ahead_priorities": ("Saving and review", "Week ahead shows", "The priorities listed in Today's Week ahead.",
                                        ("Urgent only keeps the week short; add High for a fuller view (Alan, 14-10-2026, "
                                         "keeping it rather than the mockup's Urgent and High).")),
    "dashboard.undated_grace_days": ("Work and views", "New items without a date: grace (days)",
                                     "An item raised this recently shows as new rather than undated.",
                                     "Three days gives time to add a date before it is flagged."),
    "dashboard.flow_weeks": ("Work and views", "Flow chart weeks", "How many weeks the opened and closed chart shows.",
                             "Eight weeks shows a trend without old noise."),
    "dashboard.auto_apply": ("Saving and review", "Save my changes at once",
                             "Your own edits are applied straight away, with Undo.",
                             "On: matches how you work; Review still guards what creaite suggests."),
    "dashboard.project_list_cap": ("Work and views", "Project page list length", "How many due or overdue actions a project page lists.",
                                   "Ten fits the page; the rest are one click away in Work."),
    "dashboard.generate_days": ("Current state", "Generate from the last (days)", "The default period when drafting a Current state.",
                                "A week matches the weekly report."),
    "dashboard.rail.order": ("Look and layout", "Rail order", "The order of the pages on the left-hand rail.",
                             "The day's order: Today first, Settings last."),
    "dashboard.rail.hidden": ("Look and layout", "Hidden rail pages", "Pages taken off the rail.", "None: everything is reachable."),
    "dashboard.rail.more": ("Look and layout", "Pages in More", "The pages kept in More, at the bottom of the sidebar.",   # BL-319
                            "Intake, Files, Activity and Settings: the pages of every day stay in view."),
    "dashboard.rail.display": ("Look and layout", "Rail shows", "Titles beside the icons, or icons only.",
                               "Titles: plainer for a new user; icons only is there when you know them."),
    # ── Current state
    "status.headline_max_words": ("Current state", "Headline at most (words)", "The longest headline the checks accept.",
                                  "Thirty words is a sentence an executive reads in one go."),
    "status.max_risks": ("Current state", "Risks named", "How many risks a Current state names.", "Two: the ones that matter."),
    "status.max_overdue_named": ("Current state", "Overdue items named", "How many overdue items are named.",
                                 "Three: more reads as a list, not a message."),
    "status.max_named_changes": ("Current state", "Changes named", "How many changes and decisions are named.",
                                 "Three keeps the update short."),
    "status.max_asks": ("Current state", "Asks named", "How many asks of the reader are named.", "Three: more and none get done."),
    "status.length_words.short": ("Current state", "Short length (words)", "The target for a short Current state.",
                                  "Forty words: a headline and one line."),
    "status.length_words.standard": ("Current state", "Standard length (words)", "The target for a standard Current state.",
                                     "150 words: a paragraph or two."),
    "status.length_words.fuller": ("Current state", "Fuller length (words)", "The target for a fuller Current state.",
                                   "250 words: room for context without becoming a report."),
    # ── Safety, live server, ask creaite
    "backups.daily": ("Safety", "Daily backup", "Copy the database each day, then a closed zip of what rebuilds the vault (to OneDrive "
                      "when projects live there).", "On: non-negotiable safety; off only on purpose."),
    # BL-323: retention, applied by the daily Tidy up here and in OneDrive (Alan, 14-10-2026)
    "backups.daily_days": ("Safety", "Keep every daily backup for (days)", "Daily database backups and zips: every one this long.",
                           "30 days: any day of the last month can be restored."),
    "backups.weekly_days": ("Safety", "Then keep one a week for (days)", "After that, the Monday's, for this long; then the first "
                            "of each month for good.", "A year of weekly points, then monthly ones for good (Alan, 14-10-2026)."),
    "backups.copy_days": ("Safety", "Keep apply and undo copies for (days)", "The database copies made before each apply, undo, "
                          "revert or migrate.", "14 days: they undo recent changes on this laptop; the daily backups cover the rest."),
    "backups.snapshot_days": ("Safety", "Keep daily dashboard snapshots for (days)", "Then one a month. The flow history is kept "
                              "for good.", "30 days: a snapshot is only a view of the database."),
    "backups.file_change_days": ("Safety", "Keep file-change backups for (days)", "The earlier version of each file ask creaite "
                                 "changed. Undo of an older change then says the backup has gone.", "90 days: a quarter."),
    "backups.releases_kept": ("Safety", "Release zips kept", "The installed release and the ones before it.",
                              "3: the installed one and the two before it; any release can be downloaded again."),
    "backups.update_backups_kept": ("Safety", "Update backups kept", "The backups made before each update (undo update uses the "
                                    "last one).", "3: the last three updates."),
    "live_mode.required": ("Live server and ask creaite", "Live server required", "The dashboard works through the live server.",
                           "Required: IT approved live mode; it is what makes Apply and ask creaite work."),
    "live_mode.port": ("Live server and ask creaite", "Port", "The local port the live server listens on.",
                       "8765: free on a normal Mac; the installed app belongs to it."),
    "live_mode.health_check_seconds": ("Live server and ask creaite", "Check the server every (seconds)",
                                       "How often the open page checks the server and refreshes itself.",
                                       "Thirty seconds: quick to notice, no load to speak of."),
    "live_mode.script_policy": ("Live server and ask creaite", "Script policy", "The page's script policy: report-only, or off.",
                                "Report-only: violations are counted before the policy is ever enforced."),
    "assistant.enabled": ("Live server and ask creaite", "ask creaite", "The assistant panel.", "On: it is how you ask creaite."),
    "assistant.shortcut": ("Live server and ask creaite", "Shortcut", "The key that opens ask creaite.",
                           "Cmd/Ctrl+J: free in Chrome and easy to reach."),
    "assistant.confirm_writes": ("Live server and ask creaite", "Confirm changes", "ask creaite asks before changing the record.",
                                 "On: nothing reaches the record without your yes."),
    "assistant.run_timeout_minutes": ("Live server and ask creaite", "Unwatched run stops after (minutes)",
                                      "A request nobody is watching ends after this long.",
                                      "Half an hour fits the longest real job (a sweep or minutes)."),
    # ── You
    "identity.name": ("You", "Your name", "Who \"me\" is: items you own, mail you sent.", "Empty until set-up asks for it."),
    "identity.short_forms": ("You", "Short forms of your name", "Other ways people write your name (Al, AC).",
                             "None until you add them."),
    "identity.own_domains": ("You", "Own email domains", "Your organisation's mail domains, to tell colleagues from clients.",
                             "None until you add them."),
    "people.added": ("Legacy", "People (old list)", "Names added before the people register.", "Empty: the register holds people now."),
    "people.hidden": ("Legacy", "Hidden people (old list)", "Names hidden before the people register.",
                      "Empty: the register holds people now."),
    "excel.export": ("Work and views", "Excel export", "When tracker-view.xlsx is rebuilt.",
                     "After every apply, paused only while it has edits not yet imported."),
    # ── New items and views
    "defaults.new_action_priority": ("Work and views", "New action priority", "The priority a new action starts with.",
                                     "Medium: most actions are; raise the few that aren't."),
    "defaults.actions_status_filter": ("Work and views", "Actions open on", "The status filter Actions opens with.",
                                       "Open: closed work is history."),
    "defaults.raid_status_filter": ("Work and views", "RAID opens on", "The status filter RAID opens with.",
                                    "Open: closed risks are history."),
    "defaults.decisions_view": ("Work and views", "Decisions open on", "The view Decisions opens with.",
                                "All: decisions are few and each matters."),
    "defaults.actions_sort": ("Work and views", "Actions sorted by", "The order Actions opens in.",
                              "Overdue first, then due date: the order you act in."),
    "workstreams.added": ("Legacy", "Workstreams (old list)", "Workstreams added before the workstreams table.",
                          "Empty: the table holds workstreams now."),
    "workstreams.hidden": ("Legacy", "Hidden workstreams (old list)", "Workstreams hidden before the workstreams table.",
                           "Empty: the table holds workstreams now."),
    "work.board.group.actions": ("Work and views", "Actions board groups by", "The board's columns for actions.",
                                 "Due: the question for an action is when."),
    "work.board.group.raid": ("Work and views", "RAID board groups by", "The board's columns for risks and issues.",
                              "Owner: the question for a risk is who."),
    "work.board.group.decisions": ("Work and views", "Decisions board groups by", "The board's columns for decisions.",
                                   "Status: pending against made."),
    "work.board.closed_days": ("Work and views", "Board shows closed for (days)", "How long a closed item stays in the Closed column.",
                               "Two weeks: long enough to see what was done."),
    "work.weekend_days": ("You", "Weekend", "Days with no reminders or due warnings.",
                          "Saturday and Sunday, from your work settings; change it for a Friday–Saturday week."),
    # ── Early warnings
    "warnings.redated.on": ("Early warnings", "Re-dated action", "Flag an action whose due date keeps moving.",
                            "On: a date moved three times is a hidden slip."),
    "warnings.redated.times": ("Early warnings", "Re-dated: times", "How many date changes raise the flag.",
                               "Three: once or twice is normal planning."),
    "warnings.repeat_risk.on": ("Early warnings", "Risk raised again", "Flag a risk with no response that keeps coming up.",
                                "On: a risk discussed but unanswered is the one that bites."),
    "warnings.repeat_risk.mentions": ("Early warnings", "Risk raised again: mentions", "How many meetings or sweeps raise the flag.",
                                      "Three mentions is a pattern."),
    "warnings.milestone_slip.on": ("Early warnings", "Milestone slipping", "Flag a milestone whose forecast keeps moving later.",
                                   "On: repeated slips are the early sign of a miss."),
    "warnings.milestone_slip.weeks": ("Early warnings", "Milestone slipping: weeks in a row", "How many weeks in a row raise the flag.",
                                      "Two weeks in a row: one move is noise."),
    "warnings.long_open.on": ("Early warnings", "Open too long", "Flag an action open far longer than usual for its project.",
                              "On: the forgotten action is the one that surprises."),
    "warnings.long_open.factor": ("Early warnings", "Open too long: times usual", "How many times the usual time to close.",
                                  "Twice the median: clearly unusual, not just slow."),
    "warnings.long_open.min_days": ("Early warnings", "Open too long: at least (days)", "Never flag anything younger than this.",
                                    "Two weeks: younger items are still in flight."),
    "warnings.key_person.on": ("Early warnings", "Key person", "Flag a project where one person holds most of the open work.",
                               "On: a single point of failure is worth knowing."),
    "warnings.key_person.share": ("Early warnings", "Key person: share (%)", "The share of open items one owner must hold.",
                                  "Over half is a dependency on one person."),
    "warnings.key_person.min_items": ("Early warnings", "Key person: at least (items)", "Only for projects with this many open items.",
                                      "Six: on a smaller project one owner is normal."),
    "warnings.decision_overdue.on": ("Early warnings", "Decision overdue", "Flag a pending decision past its needed-by date.",
                                     "On: a late decision holds up work quietly."),
    "warnings.decision_overdue.days": ("Early warnings", "Decision overdue: days late", "Days past needed-by before the flag.",
                                       "One day: a decision date is usually a real deadline."),
    "warnings.vip_overdue.on": ("Early warnings", "Followed person waiting", "Flag an overdue item a person you follow is waiting on.",
                                "On: these are the people you can't afford to keep waiting."),
    "warnings.vip_overdue.days": ("Early warnings", "Followed person waiting: days late", "Days overdue before the flag.",
                                  "One day: they notice quickly."),
    "warnings.dependency.on": ("Early warnings", "Dependency late for its milestone", "Flag a dependency due after its milestone.",
                               "On: a dependency due after its milestone is a slip waiting to happen."),
    "warnings.dependency.near_days": ("Early warnings", "Dependency: milestone near (days)",
                                      "An overdue dependency is flagged when its milestone is this close.",
                                      "Two weeks: close enough that the slip is real."),
    "warnings.weekend.on": ("Early warnings", "Due on a weekend", "Flag work due on a weekend day.",
                            "On: a weekend date is usually a mistake."),
    # ── Meeting prep, Intake, search
    "prep.series": ("Meeting prep and Intake", "Meeting series projects",
                    "The project chosen for each meeting series creaite was unsure of.",
                    "Empty: filled in as you choose from a meeting's prep."),
    "search.debounce_ms": ("Search", "Search delay (ms)", "How long search waits after typing before it runs.",
                           "150 ms: feels instant without searching on every key."),
    "search.ask_budget_chars": ("Search", "ask creaite reads up to (characters)", "How much vault text a search answer may read.",
                                "40,000 characters: enough sources for a grounded answer, quick to run."),
    "search.include_documents": ("Search", "Search documents", "Include project documents in search.",
                                 "On: documents are often where the answer is."),
    "inbox.meetings_from": ("Meeting prep and Intake", "Calendar Import goes back to", "Monday of this week, or a number of days.",
                            "Monday: the working week so far."),
    # ── Folders and OneDrive (set at set-up)
    "locations.projects_root": ("Folders and OneDrive", "Projects folder", "Where the engagement folders live; empty is the vault's own.",
                                "Empty: works out of the box; set-up points it at OneDrive."),
    "locations.portfolio": ("Folders and OneDrive", "Portfolio folder", "The portfolio's folder inside the projects folder.",
                            "_Portfolio, as in your template."),
    "locations.skeleton": ("Folders and OneDrive", "New project skeleton", "The folder copied for a new project.",
                           "_Templates/_Skeleton, as in your template."),
    "locations.folders.transcripts": ("Folders and OneDrive", "Transcripts folder", "Inside each engagement.",
                                      "As in your engagement template."),
    "locations.folders.minutes": ("Folders and OneDrive", "Minutes folder", "Inside each engagement.", "As in your engagement template."),
    "locations.folders.weekly_reports": ("Folders and OneDrive", "Weekly reports folder", "Inside each engagement.",
                                         "As in your engagement template."),
    "locations.folders.client_reports": ("Folders and OneDrive", "Client reports folder", "Inside each engagement.",
                                         "Beside the weekly reports, as in your template."),
    "locations.folders.adhoc_documents": ("Folders and OneDrive", "One-off documents folder", "Inside each engagement.",
                                          "As in your engagement template."),
    "locations.folders.images": ("Folders and OneDrive", "Images folder", "Inside each engagement.", "As in your engagement template."),
    "locations.folders.steerco": ("Folders and OneDrive", "Steerco folder", "Inside each engagement.", "As in your engagement template."),
    "locations.folders.agendas": ("Folders and OneDrive", "Agendas folder", "Where prep pages and agendas are saved.",
                                  "Beside the meetings, as in your template."),
    "locations.folders.notes": ("Folders and OneDrive", "Notes folder", "Where each engagement's notes are saved (BL-301).",
                                "Its own folder, as in your template; made on the first note."),
    "locations.never_index": ("Folders and OneDrive", "Never read", "Folders creaite never reads or indexes.",
                              "Archive, templates and creaite's own files are never project content."),
    "locations.offsite_backup": ("Folders and OneDrive", "OneDrive backup copy folder", "Where the daily backup's closed copy goes.",
                                 "Inside _Portfolio's 99 System, which creaite keeps for its own files."),
    # ── Help, AI drafts, logging, close the day
    "help.start_seen": ("Help", "Start here seen", "Whether Help › Start here has been shown once.",
                        "Not yet: a new user sees it on the first visit; Reset shows it again."),
    "drafting.update": ("Look and help", "AI drafts: updates", "Draft an action's latest update.", "On: drafts only suggest."),
    "drafting.client": ("Look and help", "AI drafts: client messages", "Draft a client-facing message for an item.",
                        "On: drafts only suggest."),
    "drafting.thinking": ("Look and help", "AI drafts: show thinking", "Show what a draft was based on.",
                          "On: you see why it says what it says."),
    "drafting.reason": ("Look and help", "AI drafts: reasons", "Draft a reason for a health or date change.", "On: drafts only suggest."),
    "drafting.agenda": ("Look and help", "AI drafts: agendas", "Draft a meeting agenda.", "On: drafts only suggest."),
    "drafting.agenda_style": ("AI drafts", "Agenda style", "The shape of a drafted agenda.",
                              "POAD: purpose, objectives, approach, deliverables, your house format."),
    "drafting.email": ("Look and help", "AI drafts: emails", "Draft a follow-up or chase email (never sent).", "On: drafts only suggest."),
    "drafting.forms": ("Look and help", "AI drafts: forms", "Fill a new item's form from its source.", "On: drafts only suggest."),
    "drafting.repeat": ("Look and help", "AI drafts: repeats", "Spot a proposal that repeats an open item.",
                        "On: it only marks, you decide."),
    "drafting.done": ("Look and help", "AI drafts: probably done", "Spot an open item a later message says is done.",
                      "On: it only marks, you decide."),
    "drafting.sharpen": ("Look and help", "AI drafts: sharpen", "Suggest a sharper wording for a vague action.",
                         "On: drafts only suggest."),
    "drafting.shape": ("Look and help", "AI drafts: shape the meeting",                     # BL-286 C (joined on release-192)
                       "Read your focus and aim for a meeting and draft its notes, each line cited.", "On: drafts only suggest."),
    "logging.level": ("Logging", "Log level", "Info, or debug for more detail.", "Info: enough to diagnose, small files."),
    "logging.max_mb": ("Logging", "Log file limit (MB)", "The largest a day's log may grow.",
                       "5 MB: a busy day fits; a loop can't fill the disk."),
    "logging.keep_days": ("Logging", "Keep logs for (days)", "How many days of log are kept.", "A week covers the last report cycle."),
    "logging.repeat_window_hours": ("Logging", "Repeating error window (hours)",
                                    "An error seen again within this time still counts as live.",
                                    "A day: anything older has stopped."),
    "day.close_from": ("Your day", "Offer Close the day from", "The time a quiet dot appears on the door icon.",
                       "17:30: off hid the feature; a quiet dot at the end of the working day, never a pop-up (Alan, 14-10-2026)."),
    "day.catchup_sweep": ("Your day", "Catch up before closing", "Start, offer or skip a sweep before the day closes.",
                          "Start it: your decision for BL-295; the sweep runs while you read on."),
    "day.catchup_after_minutes": ("Close the day", "Catch up if the last sweep is older than (minutes)",
                                  "Only sweep before closing when the last sweep is older than this.",
                                  "Half an hour: a recent sweep is enough."),
}
GROUP_ORDER = ("You", "Your day", "Saving and review", "People I follow", "Look and help", "Safety",
               "Sweep", "Reminders", "Review", "Health thresholds", "Early warnings", "Current state", "Work and views",
               "Look and layout", "AI drafts", "Close the day", "Meeting prep and Intake", "Search", "Folders and OneDrive",
               "Live server and ask creaite", "Logging", "Help", "Legacy", "Developer")
DEVELOPER_KEYS = ()       # development-only settings (library fetches, hand checks, the second laptop) when they exist


def defaults():
    """settings-defaults.json, parsed."""
    return json.loads(DEFAULTS_FILE.read_text(encoding="utf-8"))


def flatten(data, prefix=""):
    """{dotted key: value} for every setting in `data`: descriptions skipped, a map setting kept whole."""
    out = {}
    for k, v in data.items():
        if k in SKIP:
            continue
        key = prefix + k
        if isinstance(v, dict) and key not in MAP_KEYS:
            out.update(flatten(v, key + "."))
        else:
            out[key] = v
    return out


_MISSING = object()


def value_at(data, key):
    """The value at a dotted key in nested `data`, or _MISSING."""
    o = data
    for part in key.split("."):
        if not isinstance(o, dict) or part not in o:
            return _MISSING
        o = o[part]
    return o


def same(key, a, b):
    """True if two values of a setting are the same; order is ignored for the lists where it means nothing."""
    if key in UNORDERED and isinstance(a, list) and isinstance(b, list):
        try:
            return sorted(a, key=json.dumps) == sorted(b, key=json.dumps)
        except TypeError:
            return a == b
    return a == b


def tier_of(key):
    """essentials, advanced or developer."""
    if key in DEVELOPER_KEYS:
        return DEVELOPER
    return ESSENTIALS if any(key in row[3] for row in ESSENTIAL_ROWS) else ADVANCED


def last_changes():
    """{key: the last time it was changed} from settings-log.jsonl, and the log's first time (or None)."""
    last, first = {}, None
    try:
        lines = paths.SETTINGS_LOG.read_text(encoding="utf-8").splitlines()
    except OSError:
        return last, first
    for line in lines:
        try:
            e = json.loads(line)
        except ValueError:
            continue                       # a damaged line is skipped; the rest of the log still counts
        if isinstance(e, dict) and e.get("key") and e.get("at"):
            last[e["key"]] = e["at"]
            first = first or e["at"]
    return last, first


def entry(key, default, current, changed_at):
    """One setting as the page reads it."""
    group, label, line, reason = CATALOGUE[key]
    value = default if current is _MISSING else current
    # a log key may name a parent (dashboard.rail, sweep.ignore) or a child (warnings.redated.on): either counts
    touched = max((at for k, at in changed_at.items() if k == key or key.startswith(k + ".") or k.startswith(key + ".")),
                  default=None)
    return {"key": key, "tier": tier_of(key), "group": group, "label": label, "line": line, "reason": reason,
            "default": default, "value": value, "changed": not same(key, value, default),
            "resettable": key not in FIXED, "fixed_why": FIXED_WHY.get(key, "changed at set-up" if key in FIXED else ""),
            "last_changed": touched}


def catalogue(settings=None, today=None):
    """Every setting with its catalogue entry, value and whether it is changed; the Essentials rows; counts (BL-320)."""
    settings = paths.load_settings() if settings is None else settings
    changed_at, first = last_changes()
    rows = [entry(k, v, value_at(settings, k), changed_at) for k, v in flatten(defaults()).items()]
    old_log = bool(first) and first[:10] <= str((today or datetime.now().date()) - timedelta(days=RETIRE_AFTER_DAYS))
    untouched = [r["key"] for r in rows if r["resettable"] and not r["last_changed"]] if old_log else []
    return {"settings": rows,
            "essentials": [{"section": s, "label": lab, "line": ln, "keys": list(keys),
                            "changed": any(r["changed"] for r in rows if r["key"] in keys)} for s, lab, ln, keys in ESSENTIAL_ROWS],
            "groups": [g for g in GROUP_ORDER if any(r["group"] == g for r in rows)],
            "changed": sum(r["changed"] for r in rows), "essentials_count": len(ESSENTIAL_ROWS),
            "advanced_count": sum(r["tier"] == ADVANCED for r in rows),
            "retire_candidates": len(untouched), "retire_after_days": RETIRE_AFTER_DAYS}


def save(changes, now=None):
    """Write {dotted key: value} into settings.json exactly as the dashboard's writeSettings does: a backup of the file as it
    was (system/backups/settings-<YYYY-MM-DD-HHMMSS>.json, never overwriting one), the whole file written with two-space
    indents, and one line per key in settings-log.jsonl ({at, key, old, new}). Returns the log lines written."""
    now = now or datetime.now()
    at = now.strftime("%Y-%m-%d %H:%M:%S")
    with LOCK:
        text = paths.SETTINGS.read_text(encoding="utf-8")
        data, logs = json.loads(text), []
        for key, val in changes.items():
            o, parts = data, key.split(".")
            for q in parts[:-1]:
                if not isinstance(o.get(q), dict):
                    o[q] = {}
                o = o[q]
            logs.append({"at": at, "key": key, "old": o.get(parts[-1]), "new": val})
            o[parts[-1]] = val
        paths.BACKUPS.mkdir(parents=True, exist_ok=True)
        paths.free_path(paths.BACKUPS, "settings-" + now.strftime("%Y-%m-%d-%H%M%S"), ".json").write_text(text, encoding="utf-8")
        paths.SETTINGS.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        with open(paths.SETTINGS_LOG, "a", encoding="utf-8") as f:
            f.write("".join(json.dumps(x, ensure_ascii=False, separators=(",", ":")) + "\n" for x in logs))
    return logs


class ResetRefused(ValueError):
    """A key that isn't a setting, or one only set-up may change."""


def reset(keys, settings=None):
    """Put each key back to its default through `save`. Refuses an unknown key or a fixed one before writing anything; a key
    already at its default is left alone (no backup, no log line). Returns {reset: [keys], unchanged: [keys]}."""
    flat, settings = flatten(defaults()), paths.load_settings() if settings is None else settings
    keys = [str(k) for k in keys]
    for k in keys:
        if k not in flat or k not in CATALOGUE:
            raise ResetRefused(f"{k} isn't a setting creaite knows")
        if k in FIXED:
            raise ResetRefused(f"{k} can't be reset here: {FIXED_WHY.get(k, 'it is changed at set-up')}")
    todo = {k: copy.deepcopy(flat[k]) for k in keys
            if value_at(settings, k) is not _MISSING and not same(k, value_at(settings, k), flat[k])}
    if todo:
        save(todo)
    return {"reset": list(todo), "unchanged": [k for k in keys if k not in todo]}
