# New-machine checklist

**Time:** about 20 minutes. **Goal:** creaite runs on a Mac with the runtime requirements below and nothing else, plus a Microsoft 365 reconnect (NFR-12, BL-241). The **cx-setup** skill does the checking and repair. You do the installs and say "setup".

**What a new machine needs (BL-241, the three tiers in `system/creaite-rules.md` › Portability rules):**

1. **Runtime requirements:** macOS (the only tested platform); Python 3.9 or later; the Claude desktop app and the `claude` command, signed in; Chrome or Edge; Anthropic's docx skill; Microsoft 365 connected in Claude; git (the command line developer tools); FileVault on; the vault in a local folder outside OneDrive and iCloud (and, with projects in the company OneDrive, its Engagements folder set to "Always keep on this device"). Nothing is pip installed: the libraries are bundled in `vendor/`.
2. **macOS conveniences (optional):** the double-click launcher, the login agent. They live outside the vault, are not copied with it and are made again on a new machine.
3. **Development tools (optional, never needed to run creaite):** Homebrew, `gh`, `git` and the test Python, from `dev/Brewfile` (`brew bundle --file=dev/Brewfile`). With `gh` signed in, "update creaite" can fetch a release itself.

**Windows is best effort and untested** (Alan, 11-10-2026). The Windows commands below are unsupported hints (run `python system/scripts/<name>.py …`: the `system/scripts/run` wrapper is POSIX `sh`). ask creaite's never list names macOS places only (`Library/Keychains`, browser profiles under `Library/Application Support`) and would not protect `%APPDATA%`.

**One interpreter (BL-237):** run every creaite script through `system/scripts/run`, followed by its name and arguments (for example `system/scripts/run doctor.py`), from the vault folder. It picks the newest Python 3.9 or later on `PATH`, so you never choose between `python` and `python3`.

## First install (a new vault from a release)

**Time:** about an hour, most of it telling creaite about your projects and people.

- [ ] Do the machine checks in "On the new machine" below (Python, the `claude` command, Chrome or Edge, the docx skill).
- [ ] On the GitHub release page, download the attached **`creaite-1.6.1.zip`**, not "Source code (zip)" (that's the whole development repository).
- [ ] In Terminal, run the zip and choose the folder when asked (press Enter for `~/creaite`):
  ```
  python3 ~/Downloads/creaite-1.6.1.zip
  ```
  or name the folder: `python3 ~/Downloads/creaite-1.6.1.zip ~/creaite`. Pick a folder in your home folder, **outside OneDrive and iCloud** (it refuses those), ideally with no spaces in the name. It must be new or empty.
- [ ] **Projects in OneDrive (optional):** if your engagement folders live in the company OneDrive (`~/Library/CloudStorage/OneDrive-<company>/Documents/Engagements`), add `--projects` with that folder: `python3 ~/Downloads/creaite-1.6.1.zip ~/creaite --projects ~/Library/CloudStorage/OneDrive-<company>/Documents/Engagements` (at a terminal it asks if you leave it out). The **vault** stays local; only the projects folder may be OneDrive, and only the company one (it refuses a personal OneDrive, iCloud and similar). In Finder, set the Engagements folder to **Always keep on this device**. Say **"setup"** afterwards: its "Projects folder" step checks the folder, shows the template it found and the folder mapping for you to confirm, adds each engagement as a project, and asks per project whether to mark existing meetings as processed or process the last few weeks.
- [ ] Open that folder in the Code tab (or `cd ~/creaite && claude`), connect Microsoft 365, and say **"setup"**. It walks you through git, your name and role, your projects, the people on them and a memory file per project, asking before each.
- [ ] Start the live server (`system/scripts/run live_server.py`) and open the address it prints in Chrome.
- [ ] Later releases: say **"update creaite"** in the vault. With `gh` installed and signed in it fetches the new zip itself; otherwise download it first. Your data is never touched.

## Before you move

- [ ] Run "apply" for anything approved, and finish or clear any draft minutes in `system/staging/drafts/`.
- [ ] Close `tracker-view.xlsx`. If you've edited it, run "import excel" first.
- [ ] Copy the whole `creaite` folder, including the hidden `.claude` and `.git` folders, using an approved method such as an encrypted USB drive or the company file transfer service. Don't use personal cloud storage. `dev/` is optional.

## On the new machine

- [ ] **Mac:** put the folder in your home folder (for example `~/creaite`), **not** in Desktop or Documents if iCloud "Desktop & Documents Folders" (or OneDrive) syncs them. Turn on **FileVault**. *(Windows, unsupported hint: an encrypted drive, outside OneDrive-synced folders.)*
- [ ] Install the Claude desktop app and sign in. Set it to launch at login.
- [ ] Check Python: `python3 --version` (3.9 or later). On a Mac, accept the offer to install the command line developer tools if asked. No pip installs.
- [ ] Check the `claude` command in Terminal: `claude --version`. If missing, install it (`curl -fsSL https://claude.ai/install.sh | bash`, or `brew install --cask claude-code`), open a new Terminal window, and run `claude` once to sign in. *(Windows, unsupported hint: `irm https://claude.ai/install.ps1 | iex` or `winget install Anthropic.ClaudeCode`.)*
- [ ] Use **Chrome or Edge** for the dashboard (Safari lacks folder access).
- [ ] Install Anthropic's document skills in Claude Code, which include **docx**:
  ```
  /plugin marketplace add anthropics/skills
  /plugin install document-skills@anthropic-agent-skills
  ```
- [ ] Open the folder in the Code tab and reconnect Microsoft 365.
- [ ] Say **"setup"**. cx-setup runs the health check and the Microsoft 365 and docx checks, offers to restore the database, initialise git, create the optional morning sweep and hide `dev/`, and then rebuilds the dashboard. Fix anything it lists as yours to do.
- [ ] Start the live server in Terminal from the vault folder: `system/scripts/run live_server.py`, then open the address it prints in Chrome.
- [ ] Set up the local backup location for `system/backups/`.
- [ ] (Optional, Mac) Make the double-click launcher: `system/scripts/run launch.py make-launcher` (a small **creaite** app in `~/Applications`; `--where vault` makes `creaite.command` in the vault instead). The app asks macOS for arm64 (`LSArchitecturePriority`) and starts Python with `arch -arm64` on Apple silicon, and puts this Python's folder first on `PATH`, so it never runs under Rosetta or finds Apple's `/usr/bin/python3` stub (BL-248). **A launcher made before 1.6.1 must be made again once**; `doctor.py` warns about an old one, and the live server warns when it is running under Rosetta.
- [ ] (Optional, Mac, live vault only) Start the live server at every login: `system/scripts/run launch.py agent install`. It writes a per-user LaunchAgent in `~/Library/LaunchAgents` (no admin rights, no app to install), loads it, and restarts the server if it crashes; the server then stays up when a window closes. A Mac that restricts background items may ask you to allow it in System Settings › General › Login Items & Extensions. `agent status` shows the state and `agent remove` takes it away. Run it yourself in Terminal: ask creaite cannot, by design. It names this folder and starts the server through `system/scripts/run`, so a Python upgrade doesn't break it; say `agent install` again after moving the vault. Stop a server you started by hand first, or the agent retries every minute until the port is free.
- [ ] (cx-setup offers this) For a tidier root, hide `dev/`. Mac: `chflags hidden dev` (undo with `chflags nohidden dev`; ⌘⇧. shows hidden items in Finder). Windows (unsupported hint): `attrib +h dev`. Never hide `system/`: it holds the database and backups, and must never be missed when copying or backing up.

## Outlook rules (one-off, server-side)

These rules run on the mail server, even when the laptop is off. They give cx-sweep a strong project signal. Set them up in Outlook on the web: Settings › Mail › Rules. For each project:

1. **New rule:** name it `creaite – ABC`.
2. **Condition:** the subject includes `[ABC]`. Optionally add the sender address including the client's domain, for example `@client.com`.
3. **Action:** categorise as `ABC`. Create the category with the project code as its name. Optionally also move the message to a project folder.
4. Keep "Stop processing more rules" **off**, so a message can match more than one project.

Claude doesn't create mail rules itself; standing rules on your mailbox are yours to set.

## Check

- [ ] Open `dashboard.html`. The data matches the old machine.
- [ ] Say "review". The pending items match the old machine.
- [ ] Open a session after 07:00. The sweep catch-up runs first.

## Releasing and updating (BL-36)

**Making a release** (in this development repo):

- [ ] Merge the finished work into `main`; the tests pass.
- [ ] Add the What's new entry for the new version (`python3 dev/tools/whats_new.py add X.Y.Z`, from `dev/release-notes/X.Y.Z-plain.md`); the release check refuses a version without one.
- [ ] Set the new version in `VERSION` (patch `1.0.1` for fixes, minor `1.1.0` for new features, major `2.0.0` when you have to do something by hand). Commit "Release X.Y.Z" and push.
- [ ] On GitHub: **Releases › Draft a new release**, tag `vX.Y.Z` on `main`, title `creaite X.Y.Z`, notes in plain words (which BL items, anything to do by hand). **Publish release**.
- [ ] Wait a minute or two. The **Release zip** workflow checks the tag matches `VERSION`, runs the tests, and attaches `creaite-X.Y.Z.zip`. If no zip appears, the **Actions** tab says why: fix, delete the release and its tag, and publish again.

**Updating a live vault:**

- [ ] Say **"update creaite"**: with the GitHub command-line tool (`gh`, from `dev/Brewfile`) installed and signed in, it fetches the newest `creaite-X.Y.Z.zip` into `system/releases/` itself (`system/scripts/run update.py fetch`: download only, checked against its checksums, nothing installed). If `gh` is missing or not signed in it says so; then download `creaite-X.Y.Z.zip` from the release (the attached file, **not** "Source code (zip)") into the vault's `system/releases/` by hand.
- [ ] Say **"update creaite"** (again, if you downloaded by hand), or use Settings › creaite version › Review. Check what it shows, then confirm.
- [ ] Restart the live server. If anything looks wrong, **"undo update"**.
- [ ] Your `CLAUDE.md` is never changed by an update. If the update notes ask you to add something to it, add it yourself.

**A brand-new vault** gets its `CLAUDE.md` from `system/templates/vault-CLAUDE-template.md` ("setup" offers it). **An older vault** whose `CLAUDE.md` still holds the rules is split once by "setup" (shown first; your own lines are kept).

## Old machine

- [ ] Remove any scheduled tasks for creaite from the Claude app.
- [ ] If you installed the login agent, take it away first: `system/scripts/run launch.py agent remove` (the file lives in `~/Library/LaunchAgents`, outside the vault, so copying the folder does not copy it).
- [ ] Securely delete the old copy once the new one is confirmed.
