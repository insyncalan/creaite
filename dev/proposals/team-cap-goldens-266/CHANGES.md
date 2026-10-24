# What changed on the 13 red screens (2.6.6 candidate)

before = 2f2acdc2 (before #341), after = 330d1171 (tip of v266-line). Pictures: `1400/` and `900/`, `<screen>-before.png` and `<screen>-after.png`.
Sample vault, fixed date 09-10-2026 09:00, fictional data. Lines marked **check** touch a selection, an audience switch or a similar control: please look at these twice.

On the first-visit "Press ? for help" line (seen on work, files, intake-review, projects, people): in the after pictures it has an info icon and an outlined box instead of a plain tinted bar with a left edge. It sits outside the golden's HTML, so no golden line shows it; it is an artefact of the test's first-visit state, listed once here, not per screen.

- **activity** — **check**: the header row now has a real "select all" tick box (before: an invisible "Select" label). Rows are 1 px lower.
- **ask** — no visible change (the golden is red only for a hidden "live region" line that screen readers read; the before commit already has it, so this golden was red before #341 too).
- **cockpit** — the "Milestone slip" figure is now called "Late milestones", and "Flow" is now "Progress over time". The left cards are a little narrower and the right-hand cards (Top risks, Recent decisions) a little wider (layout, no golden line for it).
- **files** — the row of quick filters (All files, Latest reports, This week's meetings, Archived) is gone from the toolbar; only the filter icon remains. The search button beside "Search everything" now reads "ask creaite" instead of a bare spark. **check**: filter chips removed, so the files you can reach are now only via the filter icon.
- **intake-review** — each file row is shorter: "Added today · Likely project · File ready · Teams transcript · 1 KB" is one line, and the "It will be turned into minutes…" line is gone. The "Suggestions to check" and "Done" labels are now outlined pills in line with the text instead of a bar at the left edge. Buttons (Make minutes, Later, Remove, Check them) are unchanged. **check**: status chips restyled.
- **milestones** — **check**: the Internal view / Client view switch is smaller and lighter, with a pale tint on the chosen side (before: a dark filled button). This is the audience switch; make sure it is still obvious which audience you are in (the orange "Internal view" badge below is unchanged).
- **people** — the "RAID" column is now "Risks and issues". Columns are re-spaced (email narrower, project names stack on two lines), and non-zero counts under Actions are now underlined links.
- **projects** — dates are written 02-11-2026 and 08-11-2026 (before: "Monday 2nd November"). A project with no health set now says "No update has set a health yet. Next: open the project and choose a health." The evidence line for a project with nothing wrong reads "Nothing flagged" instead of "Overdue 0 · No date 0 · …", and "Warnings 0" is gone from the Example Programme line.
- **settings-advanced** — the "Help and documentation / Open help" card at the bottom is gone.
- **settings-ai** — the same: the "Help and documentation / Open help" card is gone.
- **settings-essentials** — the same: the "Help and documentation / Open help" card is gone.
- **settings-health** — the same: the "Help and documentation / Open help" card is gone. (The two Terminal commands under Diagnostics show the test's temporary folder; that is the test setup, not a change.)
- **work** — each action row loses the two small icons before the title (the half-filled status circle and the priority bars). The status and priority are still in their own columns and are read out to screen readers; the row simply starts at the tick box.
