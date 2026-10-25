# What changed on the 14 red screens (2.6.6 candidate)

before = 2f2acdc2 (before #341), after = cb1d99b5 (tip of `origin/v266-release` when Alan approved; the pictures now in this folder are the re-shoot on ab39f6c1, see the last section). Pictures: `1400/` and `900/`, `<screen>-before.png` and `<screen>-after.png`.
Sample vault, fixed date 09-10-2026 09:00, fictional data. Lines marked **check** touch a selection, an audience switch or a similar control: please look at these twice.

Two things in the pictures are not product changes: (1) the 900 px Cockpit pictures show the Milestones card in Internal view on both sides, because the shoot visits the Milestones screen at 1400 first and the audience choice is remembered for the 900 pass; at 1400 the card is in Client view on both sides. (2) The Settings › Health pictures show a temporary test folder (`/private/var/folders/.../creaite-test-xxxx`) in the two Terminal commands; its random name changes on each run, so those two PNGs differ in that line only.

## Per screen

- **today** — no visible change (the golden is red only for the read-out text of two Portfolio links: "1 urgent open risk or issue" instead of "RAID item", and "Late milestones: 14 days" instead of "Milestone slip of 14 days"; the visible words "Urgent risks" and "Slip 14 days" are unchanged). Red since #341's rename, so it was red on 04faa910 as well.
- **work** — each action row loses the two small icons before the title (the half-filled status circle and the priority bars). Status and priority are still in their own columns and are read out to screen readers; the row starts at the tick box.
- **intake-review** — each file row is shorter: "Added today · Likely project · File ready · Teams transcript · 1 KB" is one line, and the "It will be turned into minutes…" line is gone. The "Suggestions to check" and "Done" labels are outlined pills in line with the text instead of a bar at the left edge. Buttons (Make minutes, Later, Remove, Check them) are unchanged. **check**: status chips restyled. (The Intake "Open source" link now sits at the right of its cell; none of the sample rows has one, so it is not in these pictures.)
- **files** — the row of quick filters (All files, Latest reports, This week's meetings, Archived) is gone from the toolbar; only the filter icon remains. The search button beside "Search everything" reads "ask creaite" instead of a bare spark. **check**: filter chips removed, so the files you can reach are now only via the filter icon.
- **activity** — **check**: the header row has a real "select all" tick box (before: an invisible "Select" label). Rows are 1 px lower.
- **projects** — dates are written 02-11-2026 and 08-11-2026 (before: "Monday 2nd November"). A project with no health set now says "No update has set a health yet. Next: open the project and choose a health." The evidence line for a project with nothing wrong reads "Nothing flagged" instead of "Overdue 0 · No date 0 · …", and "Warnings 0" is gone from the Example Programme line. The Slip link now reads "Late milestones: 14 days" to a screen reader (the visible word is still "Slip").
- **cockpit** — the "Milestone slip" figure is "Late milestones"; "Flow" is "Progress over time". The three links "All 2 … open RAID items", "… undated RAID items" now read "open risk or issue items" and "undated risk or issue items" (new since 330d1171). The left cards are a little narrower and the right-hand cards (Top risks and issues, Recent decisions) a little wider (layout; no golden line for it).
- **milestones** — **check**: the Internal view / Client view switch is smaller and lighter, with a pale tint on the chosen side (before: a dark filled button). This is the audience switch; make sure it is still obvious which audience you are in (the orange "Internal view" badge below is unchanged).
- **people** — the "RAID" column is "Risks and issues". Columns are re-spaced (email narrower, project names stack on two lines), and non-zero counts under Actions are underlined links. Project names in the Projects column share one link style (ink, dotted underline). The People folds (a group folded and unfolded per grouping) are not in these pictures: the sample page is not grouped.
- **settings-essentials**, **settings-advanced**, **settings-ai**, **settings-health** — the "Help and documentation / Open help" card at the bottom is gone, on each of the four.
- **ask** — no visible change. The golden is red only for a hidden "live region" line that screen readers read (the mail check's places, #358). The before commit already lacks it, so the picture is the same; the golden was red before #341 too. The picture is the Today page with the ask creaite panel open.

## Visible changes with no golden line

These are in the pictures but nothing in a golden's HTML records them, so no golden line shows them.

- The first-visit "Press ? for help" line (work, files, intake-review, projects, people and the Today page): in the after pictures it has an info icon and an outlined box instead of a plain tinted bar with a left edge. It is an artefact of the test's first-visit state, listed once here.
- Cockpit column widths (left cards narrower, right cards wider), as above.
- The Files search button "ask creaite" (the spark replaced by the words), as above.

## Changes since 330d1171 that the 14 screens do not show

Checked against the new pictures: nothing else on these screens moved between 330d1171 and cb1d99b5 except the three Cockpit link texts above (the other 50 pictures are byte-for-byte the ones made at 330d1171, apart from the Health temporary-folder line). These changes are real but are not on a snapshot screen:

- #341 item 8: a List file row in Intake keeps its kind line ("Minutes" / "Transcript") and the "It is minutes" / "It is a transcript" switch when the kind can be switched or is unsure; a `.vtt` row is one line (its meaning is in the Two panes' detail). The sample's `.vtt` rows are one line, as in the pictures.
- The Prep header shows no guessed project for a confidential meeting (a remembered series still shows).
- The People folds: a folded group stays folded per grouping, and folds for groups nobody is in any more are dropped.
- The Intake "Open source" link sits at the right of the cell, so a click on the middle of a title opens the peek.
- The mail check: its places are read out when they change (the hidden live region above) and the wording of its steps is checked against the allow-list.

## Re-recorded on ab39f6c1 (after the origin/main merge and the People fit)

The goldens were re-recorded once on `origin/v266-release` ab39f6c1 (after merging origin/main, the #343 note-drawer fixes, the release text and the People fit 82acaa1c + d28b0f54). All 14 screens were shot again at 1400 and 900 px with before = 2f2acdc2, and compared with the cb1d99b5 set Alan approved. `python3 dev/tests/test_snapshots.py` on ab39f6c1 is green (14 screens).

Result: of the 28 'after' pictures (14 screens x 2 widths), 25 are byte-identical to the approved ones (and 27 of the 28 'before' pictures); the normalised HTML of every screen at ab39f6c1 equals the HTML at cb1d99b5, and each equals its committed golden. Only these differ:

- **people, 900 px (after)** — Role is a little narrower (84 px minimum, not 92), so "Delivery lead" wraps to two lines in the Role column; Organisation is also narrower; the "Risks and issues" heading is set tighter (letter-spacing .04em, not .08em) and wraps to two lines ("RISKS AND / ISSUES") instead of three; the numeric columns sit a few pixels further right. Nothing is added or removed. Alan did not see this version: it is the People fit (82acaa1c, d28b0f54), which gives 26 px spare at 900 px on Verdana.
- **people, 1400 px (after)** — Organisation and Role start 2 px further right and Projects 2 px further left (Organisation 104 px minimum, Role 84 px). Same words, same rows. Not seen by Alan; no visible effect beyond 2 px.
- **settings-health, 1400 px (after and before)** — only the random name of the temporary test folder in the two Terminal commands changes (creaite-test-uzipu5sx to creaite-test-e4aanfb3). It changes on every run; not a product change. (At 900 px the pictures are byte-identical.)
- Every other screen and width: byte-identical to the approved picture. The product files that changed since cb1d99b5 are the People CSS (above), the note drawer (#343: a meeting with no project stays unselected; not on any of the 14 screens) and the release text (`whats-new.md`; Help, not one of the 14 screens). The goldens changed against cb1d99b5's committed goldens because cb1d99b5 still held the old ones (red); the re-record brings them to what the approved pictures show.
