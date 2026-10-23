# People register

Keep this file at `projects/_portfolio/people-register.md`, beside `project-register.md`. Claude reads it every run and maps aliases and email addresses to the one full name, so owners come out the same everywhere. Edit it on the dashboard's People page, or with cx-edit ("add Sara Khan to the people register").

## People

| Full name | Email | Aliases | Organisation | Role | Hidden | Follow | Labels |
|-----------|-------|---------|--------------|------|--------|-----|--------|

Notes:
- **Full name:** the one name used on every item. Required; everything else can be added later.
- **Email:** a person's address maps to their full name, wherever it appears in mail or Teams. Several addresses are comma-separated (`mia@client.com, m.hale@client.org`); each maps to the one name.
- **Aliases:** other ways the name appears, comma-separated (for example `Sara, Sara K, SK`). A merge adds the old name here.
- **Organisation and Role:** free text (for example `Northgate Bank`, `Sponsor`). No split between client and internal people.
- **Hidden:** `yes` keeps someone out of the owner picker. Their items keep their name.
- **Follow:** blank, or `yes` for a person you follow. Anything a person you follow sends (mail, Teams) is alerted at the top of Today, whatever the sweep's project matching and ignore rules say. An older register's `VIP` column is still read until the register is next saved from the app, which writes `Follow`.
- **Labels (BL-94):** comma-separated names from the labels list (for example `Client principal`, `Executive sponsor`, `External`). A people label can carry the same behaviours as an item label: an item owned by, or naming, a labelled person is treated as sensitive for warnings.
- Use no `|` characters inside a cell.
