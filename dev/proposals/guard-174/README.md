# Proposal #174: guard hardening, F5 (a guarded-file change: Alan's to approve)

**This is a proposal, not an edit.** `system/scripts/reach.py` is a guarded file (BL-141): nothing here changes it. `reach.diff` is a unified diff for `reach.py` only, for Alan (or Jarvis, on his say) to apply with `patch -p0 < dev/proposals/guard-174/reach.diff` from the repo root. `dev/tests/test_guard_174.py` proves it against a patched scratch copy and, once the diff is applied, goes on guarding the real file. `permissions.py` is not touched. F6 (the tracked `.bak`) is a plain deletion, done in this branch.

**Version 2.** The independent security review of the first version (5b20e38c) found a glob bypass that the first diff did not close (it is older than the diff: the old rule has it too), and two claims in this README that were wrong. Both are fixed below; the diff has grown from 17 to 31 added lines.

## The defects

**F5, quoting.** `bash_problem` finishes with `_settings_refused(script, cmd.split())`. `cmd.split()` knows nothing about quotes, so the rule "ask creaite never runs `propose.py setting`" (and `workstreams retire-settings`, which clears settings.json lists through the same `cmd_setting`) is compared with the text as typed, not with the words the shell hands to `propose.py`. `'setting'`, `"setting"`, `se""tting`, `s'et'ting` and `workstreams "retire-settings"` all passed.

**The glob bypass (review of 5b20e38c; pre-existing).** The guard never expands a wildcard in a script's first argument, but the shell does. Step 1, allowed even in a plain chat as an ordinary change: `filechange.py create setting --from system/staging/drafts/x.txt --why t` makes the file `<vault>/setting`. Step 2, allowed in a confirmed run: `propose.py setti?g sweep.due_from 05:55`. The run starts in the vault root, zsh turns `setti?g` into `setting`, and `shlex` (like `str.split`) keeps `setti?g`, so the rule never saw the word. `[s]etting`, `setting*`, `s*ting`, `'sett'?ng`, the `system/scripts/run` launcher, and `workstreams retire-setting?`, `retire-*`, `[r]etire-settings` (these last three even in ask and sweep, where nothing else stops them) got through the same way. Confirmed end to end in a throwaway vault by the reviewer: `sweep.due_from` changed.

In ask, sweep, prep and held the record gate refuses `setting` anyway (kind record), so for the first group only a **confirmed** run was open; Alan presses Go ahead on one thing and the model then changes settings.json without the approval card. (`propose.py workstreams "retire-settings"` is not another subcommand: it is `workstreams` + `retire-settings` in quotes.)

## The diff: two hunks, 31 lines added, 3 removed

| Hunk | Where | What it does |
|------|-------|--------------|
| 1 | `bash_problem`, last line (~801) | The settings rule now reads the command twice: `_settings_refused(..., _unquoted_words(cmd))` (the words as the shell hands them over) **or** `_settings_refused(..., cmd.split())` (the old reading, kept). |
| 2 | after `_shell_refused`, `_settings_refused` (~836) | Adds `_unquoted_words` (`shlex.split`, `None` if it can't split) and `_has_glob`, and extends `_settings_refused`: `setting` as the first argument of `propose.py` (`main()` dispatches on `argv[0]`), `retire-settings` in any place (as before), **any `*`, `?` or `[` in the first argument, and in any argument after `workstreams`**, and a command that can't be split. The refusal text is unchanged, so the pinned decisions (`dev/tests/pinned/guard/decisions.json`) stay the same. |

**Why the wildcard rule is the smaller and safer choice** (against "refuse every unquoted wildcard in confirmed runs, as the held runs do"): propose.py's commands are fixed words (`stage`, `preview`, `workstreams`, `retire-settings`…), so no real call has a wildcard there, and the rule needs no quote tracking: it also refuses a quoted pattern (`'setti?g'`, which the shell would leave alone) rather than judge it. Refusing every unquoted wildcard in confirmed mode would also stop `minutes.py transcript 'x [1].vtt'`-style commands and need the quote-aware scan `_held_unquoted` does, in the one place Alan is least able to see it. The price: `workstreams add ABC 'Data [Migration]'` (a `[`, `*` or `?` in a workstream name, after `workstreams`) is refused; add such a name through the card. Braces and parentheses (`{setting,x}`, zsh globs with `(..)`) are already in `SHELL_OUT` and refused outside quotes; a leading `~` can't become the word `setting`.

**Why it is safe, and what it does not claim.** `_settings_refused` runs only after `_script_refused` and `_shell_refused`, which refuse backslashes outside single quotes and inside double quotes, `$` and back-quotes outside single quotes, and unbalanced quotes, so `shlex.split` reads the quotes as the shell does (the reading `bash_args`, `record_problem` and the held checks already use). **Correction of version 1:** it said the change "can only refuse more, never less". That was false for a handful of characters: `str.split` also cuts at a non-breaking space, a vertical tab, a form feed and other Unicode spaces, which `shlex` and the shell don't, so `propose.py\xa0setting k v`, `propose.py\vsetting k v` and `setting\xa0k v` went from refused to allowed. They are harmless (the shell doesn't cut there either, so `propose.py` never gets the word `setting`), but a claim about "refuses more" must be true, so hunk 1 now keeps the old `cmd.split()` reading as a second pass: the rule refuses whatever **either** reading refuses, a strict superset of the old rule. (The alternative, refusing any non-ASCII whitespace in the command, would also refuse a person's name with a non-breaking space in `people add`.) The only new refusals are therefore: quoted/concatenated spellings of `setting` and `retire-settings`, and wildcards in the places above.

**Correction of version 1, the fail-closed branch.** `_unquoted_words` returns `None` when `shlex` can't split, and `_settings_refused` refuses on `None`. That branch is **unreachable today**: the reviewer fuzzed 1,226 strings that pass `_shell_refused` and every one splits (an unclosed quote is already refused by `_shell_refused`). It stays as defence in depth, and has a test that calls it directly.

Modes affected: the check is `bash_problem`, which every mode calls first (`bash_refusal` -> `hook_decision` for ask, confirmed and sweep; `prep_decision` for prep and held). Confirmed gains the refusals that matter; ask and sweep gain the `workstreams` glob refusals; prep and held already refused. No other function, rule, list or text changes. `creaite-rules.md` already says "never `propose.py setting`"; the code now matches it, so the rules file needs no change.

What stays refused: everything refused before (plain `setting`, `retire-settings` anywhere, `permissions.py`, `live_server.py`, `launch.py`, shell characters, env prefix, `./`, another folder's path, `sh -c`, `python3 -c`, the hand-over commands, the record gate in a plain chat). What stays allowed: every other creaite script run, including a quoted file name with a bracket (`propose.py stage 'system/staging/drafts/x [1].json'`), a name with a non-breaking space (`people add 'Sara<nbsp>Khan'`), a `?` in a `learn` value, and `workstreams add ABC setting` / `learn ABC alias setting` (a name that is the word).

## Attack forms, before and after

Decision per mode in the order ask, confirmed, sweep, prep, held (A allowed, R refused), on a scratch copy of current `main` (`before`) and the same with `reach.diff` (`after`). Generated by running `reach.decide`, the hook's own function. (The `nbsp` and `vertical tab` rows are R before too: version 1 of the diff made them A in confirmed; version 2 keeps them R.)

| form | before (ask,confirmed,sweep,prep,held) | after |
|---|---|---|
| plain `propose.py setting k v` | RRRRR | RRRRR |
| `'setting'` | RARRR | RRRRR |
| `"setting"` | RARRR | RRRRR |
| `se""tting` | RARRR | RRRRR |
| `se''tting`, `s'et'ting` | RARRR | RRRRR |
| `"set""ting"` | RARRR | RRRRR |
| via `system/scripts/run propose.py 'setting'` | RARRR | RRRRR |
| via `python system/scripts/…` (no 3) | RARRR | RRRRR |
| plain `workstreams retire-settings` | RRRRR | RRRRR |
| `workstreams "retire-settings"` | RARRR | RRRRR |
| `workstreams retire-"settings"` | RARRR | RRRRR |
| `workstreams re'tire-sett'ings` | RARRR | RRRRR |
| `$'setting'` | RRRRR | RRRRR |
| `$(echo setting)` | RRRRR | RRRRR |
| back-quote | RRRRR | RRRRR |
| escaped `se\tting` | RRRRR | RRRRR |
| env prefix `X=1 python3 …` | RRRRR | RRRRR |
| `./system/scripts/propose.py setting` | RRRRR | RRRRR |
| other folder's absolute path | RRRRR | RRRRR |
| this vault's absolute path, `'setting'` | RARRR | RRRRR |
| glob `setti?g` (after `filechange.py create setting`) | RARRR | RRRRR |
| glob `[s]etting` | RARRR | RRRRR |
| glob `s*ting`, via run | RARRR | RRRRR |
| glob `'sett'?ng` | RARRR | RRRRR |
| glob `workstreams retire-setting?` | AAARR | RRRRR |
| glob `workstreams retire-*` | AAARR | RRRRR |
| glob `workstreams [r]etire-settings` | AAARR | RRRRR |
| nbsp: `propose.py\xa0setting k v` | RRRRR | RRRRR |
| vertical tab: `propose.py\vsetting k v` | RRRRR | RRRRR |
| nbsp: `setting\xa0k v` | RRRRR | RRRRR |
| unchanged: `stage 'x [1].json'` (quoted file name) | RARRR | RARRR |
| unchanged: `workstreams add ABC setting` (a name) | RARRR | RARRR |

The test file also covers, in all five modes: 5 launchers (`python3 system/scripts/propose.py`, `python system/scripts/propose.py`, `system/scripts/run propose.py`, and this vault's full path in the first and third shapes) times 12 spellings of `setting` (plain, `'..'`, `".."`, `se""tting`, `se''tting`, `s'et'ting`, `"se"tting`, mixed, empty quotes first or last, two quoted halves, `'sett'ing`), plus `'setting'` with no value (65); the same launchers times 9 spellings of `workstreams retire-settings` (45); the same launchers times 13 wildcard spellings of `setting` (`setti?g`, `[s]etting`, `setting*`, `s*ting`, `*etting`, `'sett'?ng`, `s?tting`, `s[e]tting`, `setting?`, `[a-z]etting`, `[^x]etting`, `*`, a quoted pattern) and 9 of `workstreams` (`retire-setting?`, `retire-*`, `[r]etire-settings`, `re*`, `?etire-settings`, `workst*ms`, after `-h` or `--`, a name with a bracket) (110); 10 whitespace forms (a non-breaking space, vertical tab, form feed, em space, ideographic space, next line, file separator, around `setting` and `retire-settings`); and 33 other forms, all refused before and after: `$'..'`, `$'\x73..'`, `$"..."`, `$(..)`, back-quote, `${..}`, backslash escapes, env prefix, `env`, `./` and `python3 ./`, another folder's path, double space, a quoted script name or path, `cd .. &&`, chaining, `sh -c`, `bash -c`, `python3 -c`, `python3 -m`, pipe, redirect, new line, carriage return, tab, the wrapper's `reach.py wrap`, `permissions.py`, an unclosed quote. One test checks the premise with the shell itself: in a folder holding files `setting` and `retire-settings`, zsh turns `setti?g`, `[s]etting`, `s*ting` and `retire-*` into those names.

**Not in the diff: the enabling step.** The glob works only because `filechange.py create setting …` can make a file named like a setting word in the vault root, as an ordinary change in a plain chat. Refusing a root file named `setting*` or `retire-*` is possible but is a rule about names in `filechange.py` (guarded) and would only cover the two words known today; the wildcard rule closes the hole at the point of use. Follow-up if Alan wants it.

## The normal runs still pass

The test runs 31 normal creaite commands (the skills' and the server's) through `reach.decide` in every mode, with and without the patch, and asserts **identical decisions** (and identical `bash_problem` results). The 31: `tracker.py apply` (both launchers), `read`, `undo`; `propose.py stage`, `preview`, `fields`, `new-project --out`, `close-project --out`, `recode --dry-run`, `learn`, `people list`, `people add`, `people map <draft>`, `workstreams list`, `workstreams add`, `workstreams add ABC setting`, `learn ABC alias setting`; `sweep.py stage`, `due`; `minutes.py transcript`; `review.py approve`; `search.py query`; `doctor.py`; `filechange.py edit system/config/settings.json --from … --why …` (the route the refusal text sends the model to) and `create`; `build_dashboard.py`; and four with the new rule in mind: `propose.py stage 'system/staging/drafts/x [1].json'`, `preview 'x y.json'`, `people add 'Sara<nbsp>Khan'`, `learn ABC alias 'Why? Programme'`. In a confirmed run 30 of them pass (the 31st, `people map`, is the sweep's); in a plain chat the record ones are still refused by the record gate, as before. It also takes every `python3 system/scripts/…` / `system/scripts/run …` command shown in the skills, `creaite-rules.md` and the draft prompts (73 distinct), asserts none has a wildcard in `propose.py`'s first argument or after `workstreams`, and asserts the same decision in every mode with and without the patch. (The live server and the cx-setup skill call `propose.py setting` themselves, outside the guard; the hook only sees the model's Bash calls.)

## Tests, fail-first and mutations

- `python3 dev/tests/test_guard_174.py`: 19 tests, ~110 s (two throwaway vaults per class; `Mutations` re-runs the attack tests eight times in child processes).
- Fail-first: `GUARD_174_UNPATCHED=1` leaves the scratch copy unpatched: 204 failures (the quoting and glob forms, the hook in confirmed, the fail-closed test); `Defect` and `Normal` stay green. `Defect` is always on: it shows the unpatched file lets `'setting'`, `se""tting`, `"retire-settings"`, `setti?g`, `[s]etting` and `workstreams retire-*` through a confirmed run.
- Against version 1 (`GUARD_174_DIFF=<the old diff>`): 115 failures (105 glob, 10 whitespace); the quoting tests stay green.
- Mutations (the `Mutations` test runs them; `GUARD_174_MUTATE=<name>` runs one): `no-unquoted` (the shlex pass dropped) 98 red; `no-split` (the old reading dropped) 10 red; `no-glob-first` 65 red; `no-glob-workstreams` 40 red; `no-shlex` (`cmd.split()` inside `_unquoted_words`) 99 red; `no-setting` 77 red; `no-retire` 47 red; `fail-open` 1 red.
- After Alan applies the diff, the test file notices the marker `def _unquoted_words` in the repo's `reach.py`, skips the patch step and makes its "unpatched" copy with `patch -R`.

## Follow-ups (not in the diff), with the reviewer's rank

From the #116 reviews and the independent review of this proposal, checked against current `main`:

1. `minutes.py transcript x =ls` and a bare `--` are allowed in ask, confirmed and sweep (held and prep refuse). **Low.** Different function (`ask_shell_refusal`): add `if any(a.startswith("=") for a in bash_args(command))` and `if "--" in bash_args(command)` with the held texts. The `--` matters a little: `command_kind` reads `--dry-run` after a `--` as the read flag.
2. `-out` and `---out` pass held and prep (`propose.py new-project` builds its options with `lstrip("-")`, so they write the spec like `--out`). **Low-medium:** a run that should only read can write a spec JSON into `system/staging/drafts/`; it cannot touch the record. Different function (`held_form_reason`): refuse `re.fullmatch(r"-+out(=.*)?", a)`.
3. `propose.py people migrate` also calls `cmd_setting` (clears `people.added` / `people.hidden`). **Low.** Alan's call whether to add it to `_settings_refused`.
4. `update.py install` and `backup.py restore` also write settings.json in a confirmed run. They are deliberate record commands (each is the point of its command); **for Alan's attention**, no change proposed.
5. `.claude/settings.json.bak` is also tracked in git. **Low.** Not removed here; Alan's call.
6. Held globbing skipping hidden folders, and the dead escaped-quote clause: already resolved on `main` (ask and held share `_glob_walk`; neither function has the clause). Nothing to do.
7. The enabling step above (a root file named like a setting word), if wanted.

## What Alan must approve

This is a **guard change**: it edits `system/scripts/reach.py`, which decides what ask creaite may run. The change makes the existing "never `propose.py setting`" rule read the command as the shell does, and closes the wildcard hole. It only adds refusals (a strict superset of the old rule). Apply `reach.diff` (or ask for it to be applied), then run `dev/tests/test_guard_174.py`, `test_reach*`, `test_guard_*`, `test_permission_panel.py`, `test_record_commands.py`.
