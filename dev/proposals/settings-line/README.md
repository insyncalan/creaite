# Settings line: proposed changes to guarded files

The Settings line (v2.6) takes People and projects out of Settings. People are on the People page (#248). Each
project's Workstreams, client report and Archive are on its settings page (#247). Show archived and Restore are on
the Projects page. The old addresses redirect: `#settings/people` opens the People page, `#settings/projects` and
`#settings/admin` open the Projects page, and `#settings/workstreams` opens the open project's settings at Workstreams
(the Projects page when no project is open).

These files are guarded, so their wording is proposed here and not edited. Both diffs pass `git apply --check` against
`v26-settings-line`.

## rules.diff: `system/creaite-rules.md`

- Folder map, `projects/<CODE> <Name>/`: the client report setting is changed "in the Reporting hub's Client report
  settings or on the project's settings page (Client report and logos)". Was: "or in Settings › Projects".
- Folder map, `projects/_portfolio/`: the people register is "edited on the dashboard's People page (a project's
  people also on its settings page) or with cx-edit". Was: "edited in Settings › People or with cx-edit".
- Folder map, `system/logs/`: "Settings › Health › Diagnostics". Was: "Settings › Diagnostics".
- Dashboard editing, Project settings page: it is opened "from the project page's gear and the Projects list (the old
  `#settings/workstreams` address opens it at Workstreams while a project is open)". It is "One scrolling page (#247)"
  with these sections: Project, People and partners, Workstreams, Milestones, Client report and logos, Archive and
  close. A new sentence says Settings has no People and projects any more and names where the old addresses go.
  **Logos** and **Reporting** become one section, **Client report and logos**. Was: "the Projects list and Settings ›
  People and projects … (no Workstreams: they stay in Settings › People and projects)".
- Login agent: "a clean stop (Settings › Health › Stop the live server)". Was: "(Settings › Stop)".
- Conventions, Projects by name: the code shows where it is defined, which is now "a project's settings page". Was:
  "Settings › Projects".
- Conventions, VIP is private: the word appears in "Settings › Essentials › People I follow". Was: "Settings › VIP
  alerts".

## scripts.diff: `system/scripts/client_leak.py`, `system/scripts/tracker.py`

- `client_leak.REGISTER_UNREAD`: "fix it on the People page (or say "setup"), then try again". Was: "fix it in
  Settings › People".
- `tracker.py migrate`, the line printed after seeding workstreams: "Leads and keywords are yours to fill (each
  project's settings › Workstreams, or cx-edit)". Was: "(Settings › Workstreams or cx-edit)".

No test asserts either string. `live_server.py` mentions "Settings › Projects" only in a comment, so it is left alone.

To apply: `git apply dev/proposals/settings-line/rules.diff dev/proposals/settings-line/scripts.diff`
