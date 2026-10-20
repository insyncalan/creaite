# Proposal #174: guard hardening, F5 (a guarded-file change: Alan's to approve)

# FINAL, for Jarvis to apply (approved by Alan, 20-10-2026)

Three independent diffs for `system/scripts/reach.py` (the only file they touch), in `dev/proposals/guard-174/`. From the repo root, **in this order**, each with `-p0` (the headers read `--- system/scripts/reach.py`, so no `-p1`):

```
patch -p0 < dev/proposals/guard-174/reach.diff
patch -p0 < dev/proposals/guard-174/reach-report.diff
patch -p0 < dev/proposals/guard-174/reach-steerco-adhoc.diff
```

Add `--dry-run` first to check. Every order of the three `reach.py` diffs applies cleanly (checked, 7 orders, with `patch --dry-run` and for real) on `origin/main` (dcd8a7b6) **and** on `origin/v252-release` (afb8c30c, whose `reach.py` differs from main by one added table row): **no rebase is needed and no `-rebased.diff` exists**. `reach.diff` and `reach-report.diff` are byte for byte the diffs of 6a911a7b and dffd8fc7 (the morning pack); `reach-steerco-adhoc.diff` is the only one that changed since (this round). `check-baseline.diff` is gone: **`check.py` fails by one long line after `reach.diff`** (`LONG 2 lines over 140`, from one 142-character comment `reach.diff` adds); Jarvis wraps that comment by hand.

| Diff | What it refuses (only ever adds refusals) |
|------|------------------------------------------|
| `reach.diff` | `propose.py setting` and `workstreams retire-settings` however quoted or spliced; `people migrate` (the word anywhere after `people`); an unquoted `* ? [ ^ #` or inner `~` in any creaite script call (a shell pattern turned into another word by a file in the vault root); `command_kind` fails closed for `people`/`workstreams` with an unknown second word. |
| `reach-report.diff` | `report.py weekly-stage` / `client-stage` spelled with quotes, splices, `run`, `python`, an absolute path (a hole in v2.5.1 on `main`). Reading reports stays allowed. |
| `reach-steerco-adhoc.diff` | `report.py adhoc` and `steerco-stage`, `docx_tools.py fill` and `build-adhoc`, **only when the draft is named like a report** (below). |

**What Alan will notice** (plain words): in an ask creaite chat a report-named draft is now refused by every route the reviews found: `report.py weekly-stage`, `client-stage`, `adhoc` and `steerco-stage`, and `docx_tools.py fill`, `build-adhoc` and `clean`, however the command is typed (quotes, `run`, an absolute path, a dash-led or oversized or duplicate-key spec, lookalike or invisible letters, a right-to-left override), and the chat says "reports are the user's to edit" and stops; it also refuses `propose.py setting` and `people migrate` (use the approval card) and a command with an unquoted `*`, `?`, `[`, `^`, `#` or `~` inside a word (put the name in quotes). Reading reports and files, ordinary documents, internal Steerco one-pagers, minutes, sweeps, staging, applying a confirmed change and `filechange.py` edits still work, and Alan's own Claude Code session is not guarded. **Three known limits remain** (below): the write-time race, lookalike letters from other alphabets (a Cyrillic `е`), and a direct Write or `filechange.py create` of a report-named file in the drafts folder.

**Regressions accepted** (all three diffs; the first two are already in the sections below):
1. `reach.diff`: an unquoted pattern character in any script call is refused (`minutes.py new [CODE]`, `search.py query ABC#12`, `a~b`; quote the argument and it runs). `people resolve|list|add migrate` (a person named Migrate) are refused (not narrowed, so the diff is the one shown).
2. `reach.diff`: an unknown `people`/`workstreams` second word is refused in a plain chat and in held/prep runs.
3. `reach-steerco-adhoc.diff` matches the **words** report, weekly and client as substrings in the spec title or the output file name, so a title like "Quarterly reporting" or "Client list", and a `docx_tools.py fill` of minutes into a file called "... Weekly sync minutes.docx", are refused in ask, confirmed and sweep. Alan's own Claude Code session is not guarded, so he can run these himself; or name the draft without those words. Narrowing the matcher to the existing `REPORT_NAME` (weekly/client followed by report) is a one-line change if Alan prefers.
4. A client-safe Steerco one-pager (`steerco-stage` with `"version": "client"`) is refused: its file is called "... (client).docx". Internal one-pagers are allowed.
3b. Exactly what the word match refuses that Alan may not expect: `docx_tools.py fill` of **minutes** into a Word draft for any project whose **name** contains "Reporting" or "Client" (every minutes draft for that project), minutes of a "weekly sync" or a "client workshop" meeting, and a one-off document titled, say, "Open actions for the client". (A project is named in the draft's file name, so its whole name is matched; Alan can run the command himself, or the project can be renamed.)
5. `reach-steerco-adhoc.diff` fails closed: a spec that can't be read, is over 1 MB or whose path starts with `~`, and an argument shape the scripts wouldn't run, are refused for `adhoc`, `steerco-stage`, `build-adhoc` and `clean`. Write the spec first, name it in the drafts folder, then run the command. Not covered, still allowed: see the section on that diff.

**Verify after applying** (from the repo root, one at a time; each takes minutes on a loaded machine):

```
python3 dev/tests/test_guard_174.py              # 25 tests: the tests now guard the applied file
python3 dev/tests/test_guard_report_quoted.py    # 8 tests
python3 dev/tests/test_guard_steerco_adhoc.py    # 14 tests
python3 dev/tools/run_tests.py -j 3 test_reach test_guard_ test_held_bash_arg_forms test_record_commands test_ask_reports_refused test_permission_panel test_no_real_names
python3 dev/tools/check.py --no-js
```

Each of the three proposal tests notices its marker in the real `reach.py` (`def _glob_refused`, `def _stages_a_report`, `def report_named_draft_refusal`), skips the patch step, and makes its "unpatched" copy with `patch -R`. `GUARD_174_UNPATCHED=1`, `GUARD_REPORT_UNPATCHED=1` and `GUARD_STEERCO_UNPATCHED=1` run them against the file without the fix (they must go red).

**Undo:** reverse in the opposite order, `patch -p0 -R < dev/proposals/guard-174/reach-steerco-adhoc.diff`, then `reach-report.diff`, then `reach.diff` (checked: the result is byte for byte the original `reach.py`); or `git checkout -- system/scripts/reach.py` before committing, or `git revert` the commit that applied them.

---

**This is a proposal, not an edit.** `system/scripts/reach.py` is a guarded file (BL-141): nothing here changes it. `reach.diff` is a unified diff for `reach.py` only, for Alan (or Jarvis, on his say) to apply with `patch -p0 < dev/proposals/guard-174/reach.diff` from the repo root. `dev/tests/test_guard_174.py` proves it against a patched scratch copy and, once the diff is applied, goes on guarding the real file. `permissions.py` is not touched. F6 (the tracked `.bak`) is a plain deletion, done in this branch.

**Version 3.** Version 1 (5b20e38c) fixed quoting. The independent review found the glob bypass (v2, 3f186de5, closed it for `propose.py setting` and `workstreams retire-settings`). The re-review of v2 found that the glob class is general. v3 closes the class in one place.

**A second, independent diff: `reach-report.diff`.** It fixes a hole in v2.5.1 that is on `main` today and has nothing to do with the glob change; see "The v2.5.1 report hole" below. `reach.diff` (this README's subject until that section) is the diff in the morning pack and is unchanged by it. Either applies alone; both orders apply cleanly (checked with `patch --dry-run` on `origin/main`).

## The defects

**F5, quoting.** `bash_problem` ended with `_settings_refused(script, cmd.split())`. `cmd.split()` knows nothing about quotes, so the rule "ask creaite never runs `propose.py setting`" (and `workstreams retire-settings`, which clears settings.json lists through the same `cmd_setting`) was compared with the text as typed, not with the words the shell hands to `propose.py`. `'setting'`, `"setting"`, `se""tting`, `s'et'ting` and `workstreams "retire-settings"` all passed (a confirmed run only: the record gate refused them elsewhere).

**The glob class (pre-existing).** The guard reads a script call as the words it sees, but the shell expands a pattern against the folder the run starts in (the vault root). `filechange.py create <name> …` is an ordinary change, allowed even in a plain chat, so a file of any name can be put there first. After that a pattern becomes any fixed word the guard compares:
- `propose.py setti?g`, `[s]etting`, `s*ting`, `workstreams retire-*` (file `setting`, `retire-settings`): the settings rule never saw the word;
- `propose.py people migrat?`, `ad?`, `edi?`, `renam?`, `merg?`, `ma?` (files `migrate`, `add`, …): `command_kind` takes the first word's kind (`people` = read) when the second word is unknown, so the record gate let them through in **ask, confirmed and sweep** (a plain chat could add, edit, rename or merge people, or clear the people lists);
- `tracker.py validat? system/config/settings.json` and `run reach.py wra? permissions.py edit x` (files `validate`, `wrap`): `read_write_refusal` and `handover_refusal` compare fixed words, so the first lets a read command rewrite a JSON file in reach and the second hands over to `reach.py wrap`, which the permission layer alone then stops;
- the zsh extended-pattern forms `settingx#`, `^zzz` and `setting~zzz`, if `EXTENDED_GLOB` is set (see the note below).

And, separately, `propose.py people migrate` written plainly reaches `cmd_setting("people.added", "[]")` and `("people.hidden", "[]")`, which the settings rule did not cover.

## The diff: three hunks, 47 lines added, 3 removed

| Hunk | Where | What it does |
|------|-------|--------------|
| 1 | `bash_problem`, last line (~801) | Adds `_glob_refused(cmd)` to the checks, and the settings rule now reads the command twice: `_settings_refused(..., _unquoted_words(cmd))` (the words as the shell hands them over) **or** `_settings_refused(..., cmd.split())` (the old reading, kept). |
| 2 | after `_shell_refused`, `_settings_refused` (~836) | Adds `_glob_refused`, `_unquoted_words` and the extended `_settings_refused`: `setting` as the first argument of `propose.py` (`main()` dispatches on `argv[0]`), `retire-settings` in any place, **`migrate` after `people`**, and a command that can't be split. The refusal text is unchanged, so the pinned decisions stay the same. |
| 3 | `command_kind` (~920) | Fails closed: when the first word has commands of its own (`people`, `workstreams`) and the second word is not one of them, the kind is `unknown` (the BL-267 unknown-command refusal then applies in a plain chat, in held and in prep runs). The name returned never carries the argument (the debug log must not). |

**`_glob_refused`, the general rule.** In every word of every creaite script call, in every mode, outside quotes: `*`, `?`, `[`, `^`, `#` and a `~` that doesn't start a word (or follow `=`, `:` or `,`) are refused. It scans like `_shell_refused` (quotes open and close at the matching quote; a backslash is already refused). In quotes the shell leaves them as text, so quoted wildcards still run: `'inbox/x [1].vtt'`, `'SOW [signed].docx'`, `'system/staging/drafts/x [1].json'`, `workstreams add ABC 'Data [Migration]'`, a `learn` value with a `?`. The bounded expansion checks (`held_arg_paths`, `ask_arg_paths`) still look at what a script might do with a quoted pattern. The refusal text contains "has a wildcard" so `test_held_bash_arg_forms.py` still classes the held wildcard cases as the held form (otherwise unchanged).

**Why it is the right size.** v2 refused a wildcard in two named places (`propose.py`'s first argument, arguments after `workstreams`). That was enough for `setting` but left the other fixed words (`people`, `validate`, `wrap`), and it refused the quoted `'Data [Migration]'`. One rule at the point of use covers every comparison the guard makes, now and later, with no list of words to keep in step; the cost is that an unquoted pattern character is never allowed (below). `command_kind`'s fail-closed change is defence in depth for a quoted `people 'migrat?'` or any unknown second word.

**Why it is safe, and what it does not claim.** `_settings_refused` and `_glob_refused` run only after `_script_refused` and `_shell_refused`, which refuse backslashes outside single quotes and inside double quotes, `$` and back-quotes outside single quotes, and unbalanced quotes, so `shlex.split` reads the quotes as the shell does. The `str.split` reading is kept as a second pass because `str.split` also cuts at a non-breaking space, a vertical tab or a form feed, which the shell and `shlex` don't: `propose.py\xa0setting k v` is harmless (the script never gets `setting`), but the settings rule now refuses whatever either reading refuses, a strict superset of the old rule. The `_unquoted_words` fail-closed branch for an unsplittable command is **unreachable today** (the reviewer fuzzed 1,226 strings that pass `_shell_refused`: all split); it stays as defence in depth, with a direct test.

**Regressions accepted (listed):**
1. An unquoted `* ? [ ^ #` or inner `~` in a script call is refused everywhere, also in the held and prep runs, which already refused wildcards. The skills and rules show one such command: `minutes.py new [CODE]` (usage notation for an optional argument; the model puts the project code there, so nothing real has the brackets). All 73 other commands in the skills, rules and draft prompts have identical decisions.
2. `propose.py people migrate` (any form) is refused in a confirmed run: it is a settings change (`cx-setup` still runs it in Alan's own session, outside the guard); a chat stages a register change instead.
3. `propose.py people <unknown word>` (and `workstreams <unknown word>`) is now unknown: refused in a plain chat and in held/prep runs; it only printed usage before.
4. The error message for an unquoted wildcard now says to quote the name; nothing else about the held runs changes.

**Not done: (4) `wrap_problem`.** Adding `permissions.py`, `live_server.py` and `launch.py` to `wrap_problem` was asked for and is **left out on purpose**: `wrap_problem` is the check behind `system/scripts/run` for everyone, and `system/scripts/run live_server.py` is the documented way to start the server (creaite-rules.md, cx-setup), `run launch.py agent install|remove` is the login agent's command and `permissions.py` is what cx-setup runs in Alan's own Terminal. The wrapper can't tell an ask run's Bash call from Alan's. The guard already refuses those three for a Bash call (`_script_refused` in `bash_problem`), and the route round it, `reach.py wrap <script>`, is closed by `handover_refusal`, which the pattern rule now protects (`reach.py wra?`). If the wrapper should refuse them for ask runs, the hook would have to pass a marker (an environment variable) that only the guard sets: a bigger change to `reach.py` and `hook_main`, for Alan to decide.

## Note: zsh `EXTENDED_GLOB`

With `setopt EXTENDED_GLOB` (not set by default in a non-interactive zsh, and an interactive profile can set it) zsh treats `#` (zero or more of the previous character: `settingx#`), `^` (anything but: `^zzz` matches every file but `zzz`) and `~` (except: `setting~zzz`) as pattern operators. Which shell the Bash tool starts, and which options its profile sets, is configuration the guard can't see, so `_glob_refused` refuses all three outside quotes whatever the option is. If a future shell reads other pattern characters (`<1-9>` numeric ranges are `<` `>`, in `SHELL_OUT` already; `(…)` and `{…}` likewise), the rule's character set is the one place to extend.

## Attack forms, before and after

Decision per mode in the order ask, confirmed, sweep, prep, held (A allowed, R refused), on a scratch copy of current `main` (`before`, with the decoy files in the vault root) and the same with `reach.diff` (`after`). Generated by running `reach.decide`, the hook's own function.

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
| `people migrat?` (file `migrate`) | AAARR | RRRRR |
| `people ad? 'Sara Khan'` | AAARR | RRRRR |
| `people ma? x`, via run | AAARR | RRRRR |
| `people zzz` (unknown second word) | AAAAA | RARRR |
| plain `people migrate` | RARRR | RRRRR |
| `tracker.py validat? system/config/settings.json` | RARRR | RRRRR |
| `run tracker.py [v]alidate …` | RARRR | RRRRR |
| `run reach.py wra? permissions.py edit x` | RARRR | RRRRR |
| zsh extended `settingx#` | RARRR | RRRRR |
| zsh extended `^zzz` | RARRR | RRRRR |
| zsh extended `setting~zzz` | RARRR | RRRRR |
| unchanged: quoted `transcript 'inbox/x [1].vtt'` | AAAAA | AAAAA |
| unchanged: quoted `workstreams add ABC 'Data [Migration]'` | RARRR | RARRR |
| unchanged: `search.py query 'SOW [signed].docx'` | AAAAA | AAAAA |
| unchanged: `stage 'x [1].json'` (quoted file name) | RARRR | RARRR |
| unchanged: `workstreams add ABC setting` (a name) | RARRR | RARRR |

The test file also covers, in all five modes: 5 launchers (`python3 system/scripts/x.py`, `python system/scripts/x.py`, `system/scripts/run x.py`, and this vault's full path in the first and third shapes) times 12 spellings of `setting` plus `'setting'` with no value (65); times 9 spellings of `workstreams retire-settings` (45); times 16 pattern spellings of `setting` (`setti?g`, `[s]etting`, `setting*`, `s*ting`, `*etting`, `'sett'?ng`, `s?tting`, `s[e]tting`, `setting?`, `[a-z]etting`, `[^x]etting`, `*`, `settingx#`, `^zzz`, `setting~zzz`, `'setting'~zzz`) and 11 of `workstreams` (`retire-*`, `[r]etire-settings`, `re*`, `workst*ms`, after `-h` or `--`, an unquoted `Data[Migration]`, `x#` and `~` forms) (135); times 17 calls of the other fixed words (`people migrat?`, `ad?`, `edi?`, `renam?`, `merg?`, `ma?`, `[m]igrate`, `migrat*`, `?`, `migrate~zzz`; `tracker.py validat?`, `[v]alidate`, `validate*`, `appl?`; `reach.py wra?`, `w*p`, `hoo?`) (85); 6 spellings of plain `people migrate` (plain, run, quoted, concatenated, after an option, quoted `people`); 10 whitespace forms; and 33 other forms refused before and after (`$'..'`, `$()`, back-quote, env prefix, `./`, another folder's path, `sh -c`, `python3 -c`, pipes, `permissions.py`, …). The decoy files `setting`, `retire-settings`, `migrate`, `add`, `edit`, `rename`, `merge`, `map`, `validate`, `wrap`, `hook` and `apply` are made in the scratch vault root, as `filechange.py create` would. One test checks the premise with the shell itself: zsh turns `setti?g`, `[s]etting`, `s*ting`, `retire-*`, `migrat?`, `wra?`, `validat?` and `[a]ppl?` into those file names.

**The enabling step, not in the diff.** `filechange.py create setting …` in the vault root stays allowed. Refusing root files named like a command word would only cover the words known today and is a rule in `filechange.py` (guarded); the pattern rule closes the hole at the point of use. Follow-up if Alan wants it.

## The normal runs still pass

38 normal creaite commands (the skills' and the server's) are decided through `reach.decide` in every mode, with and without the patch, with **identical decisions** and identical `bash_problem` results, and the 36 a confirmed run needs pass: `tracker.py apply` (both launchers), `read`, `undo`; `propose.py stage`, `preview`, `fields`, `new-project --out`, `close-project --out`, `recode --dry-run`, `learn`, `people list`, `people add`, `workstreams list`, `workstreams add`, `workstreams add ABC setting`, `learn ABC alias setting`; `sweep.py stage`, `due`; `minutes.py transcript`; `review.py approve`; `search.py query`; `doctor.py`; `filechange.py edit system/config/settings.json --from … --why …` (the route the refusal text points to) and `create`; `build_dashboard.py`; and the quoted-pattern cases: `propose.py stage 'system/staging/drafts/x [1].json'`, `preview 'x y.json'`, `people add 'Sara<nbsp>Khan'`, `learn ABC alias 'Why? Programme'`, `minutes.py transcript 'inbox/x [1].vtt'`, `search.py query 'SOW [signed].docx'`, `search.py query "#12 and ~-5 days"`, `workstreams add ABC 'Data [Migration]'` and `'Why?'`, `propose.py 'setti?g' a b` (only text to the shell), and a `~/` path. In a plain chat the record ones are still refused by the record gate. All 73 distinct commands in the skills, `creaite-rules.md` and the draft prompts have the same decision in every mode, except the two named above (`minutes.py new [CODE]`, `people migrate`). (The live server and cx-setup call `propose.py setting` and `people migrate` themselves, outside the guard.)

## Tests, fail-first and mutations

- `python3 dev/tests/test_guard_174.py`: 25 tests, ~3 min unloaded (about 10 on a loaded machine).
- Fail-first: `GUARD_174_UNPATCHED=1` leaves the scratch copy unpatched: 326 failures and the docs test (the quoting forms, 135 pattern forms, 85 other-word forms, 6 `people migrate`, the hook, the fail-closed tests); `Defect` and `Normal` stay green. `Defect` is always on: it shows the unpatched file lets through a confirmed run `'setting'`, `se""tting`, `"retire-settings"`, `setti?g`, `[s]etting`, `workstreams retire-*`, `people migrate`, `tracker.py validat?`, `reach.py wra?`, `settingx#` and `^zzz`, and through **ask, confirmed and sweep** `people migrat?`, `ad?`, `edi?`, `renam?`, `merg?`, `ma?` and `people zzz`.
- Against version 2 (`GUARD_174_DIFF=<the v2 diff>`): 228 failures (135 pattern, 85 other-word, 6 `people migrate`, command_kind, hunk count).
- Mutations (the `Mutations` test runs them; `GUARD_174_MUTATE=<name>` runs one), each red: `no-glob-call` 220; `no-glob-bracket` (drop `[` from the pattern characters) 35; `no-glob-star` 60; `no-glob-question` 85; `no-glob-caret` 5; `no-glob-hash` 10; `no-glob-tilde` 20; `no-unquoted` 101; `no-split` 10; `no-shlex` 102; `no-setting` 77; `no-retire` 47; `no-people-migrate` 6; `no-failclosed-kind` (hunk 3) 1; `fail-open` 1.
- After Alan applies the diff, the test notices the marker `def _glob_refused` in the repo's `reach.py`, skips the patch step and makes its "unpatched" copy with `patch -R`.

## Follow-ups (not in the diff), with the reviewer's rank

1. `minutes.py transcript x =ls` and a bare `--` are allowed in ask, confirmed and sweep (held and prep refuse). **Low.** Different function (`ask_shell_refusal`): refuse a word starting `=` and a bare `--`, with the held texts.
2. `-out` and `---out` pass held and prep (`propose.py new-project` builds its options with `lstrip("-")`). **Low-medium:** a run that should only read can write a spec JSON into `system/staging/drafts/`; it cannot touch the record. Different function (`held_form_reason`): refuse `re.fullmatch(r"-+out(=.*)?", a)`.
3. `update.py install` and `backup.py restore` also write settings.json in a confirmed run. They are deliberate record commands; **for Alan's attention**, no change proposed.
4. `.claude/settings.json.bak` is also tracked in git. **Low.** Not removed here; Alan's call.
5. The wrapper refusing `permissions.py`, `live_server.py` and `launch.py` for ask runs only (above): needs a marker from the hook.
6. The enabling step above (a root file named like a command word), if wanted.
7. Held globbing skipping hidden folders, and the dead escaped-quote clause: already resolved on `main`.

## Extra false positives found by the re-review of v3 (accepted, listed)

- `propose.py people resolve migrate`, `people list migrate` and `people add migrate` are refused in all modes: `reach.diff` refuses the word `migrate` anywhere after `people` (not only as the subcommand). It matters only for a person called Migrate. A narrowing to the subcommand position (`[x for x in args[1:] if x != "--"][:1] == ["migrate"]`, which keeps `people -- migrate` refused) is a one-line change if Alan wants it; **it was not made** so that `reach.diff` stays exactly the diff in the morning pack. The older `retire-settings` rule has the same any-position reach (`workstreams add ABC retire-settings` is refused).
- Unquoted `search.py query ABC#12` and `search.py query a~b` are newly refused (a `#` or `~` inside a word, zsh's `x#` and `x~y` pattern characters, outside quotes). Quote them (`'ABC#12'`) and they run; a leading `~/` path and quoted `'#12'` or `"~-5 days"` are unchanged.

## The v2.5.1 report hole (`reach-report.diff`)

v2.5.1 (hand checks 38 to 40) says ask creaite never stages a weekly or client report. `report_command_refusal` does it with `re.search(r"report\.py\s+(?:weekly|client)-stage\b", cmd)` on the **raw command text**, so quotes splice the word apart: `python3 system/scripts/report.py 'weekly-stage' system/staging/drafts/x.json`, `weekly''-stage`, `"client-stage"`, `we'ekly-st'age`, and the same through `system/scripts/run` or `python` are **allowed in ask, confirmed and sweep** (the held and prep runs refuse them by the command's kind). These write a report draft.

The fix (one hunk, +21/-1) adds `_stages_a_report(cmd)`: the first word after `report.py` that is not an option must not be `weekly-stage` or `client-stage`, read as the shell hands the words over (`shlex`) and as `str.split` cuts them; a command that can't be split is refused if it names `report.py`. The raw-text regex stays as well, so it only refuses more. It runs where the old rule runs (`report_command_refusal`, called from `ask_bash_refusal`), so the modes are the same as today's rule. It uses `shlex` itself and needs nothing from `reach.diff`. Reading stays allowed: `report.py weekly-data|client-data|steerco-data|facts|current-context|adhoc-data` (also quoted, and with a file called `weekly-stage-notes` as an argument) and the Read tool on a report draft (hand check 40). Pattern spellings (`weekly-stag?` with a decoy file) are closed by `reach.diff`'s pattern rule, not by this diff. `steerco-stage` is not in v2.5.1's rule and is not touched.

Tests: `dev/tests/test_guard_report_quoted.py` (8 tests, ~2.5 min): 17 stage forms (plain, single, double and empty quotes, spliced, `run`, `python`, absolute path, after an option) refused in every mode, with the report reason in ask, confirmed and sweep; two forms refused earlier; 8 read forms allowed; the unsplittable command; the hole shown on the unpatched file (13 quoted forms allowed in ask, confirmed and sweep); the plain forms refused unpatched too (so they can't fail first); both orders with `reach.diff`. `GUARD_REPORT_UNPATCHED=1` gives 14 failures. Mutations: `raw-text` (back to raw matching) 13 red, `first-word` (only `weekly-stage` counts) 6 red, `fail-open` 1 red.

## Report-named drafts through the other builders (`reach-steerco-adhoc.diff`)

v2.5.1's rule covers `report.py weekly-stage` and `client-stage`. The review found that `report.py steerco-stage` and `adhoc`, and `docx_tools.py fill`, `build-adhoc` and `clean`, are allowed in ask, confirmed and sweep and write a Word draft into `system/staging/drafts/`, and that `adhoc` names its file from the spec's title: a title such as "Example Programme Weekly report" writes a report-named draft outside the rule (the file rule only sees a command that names a report file).

**Interpretation taken (Jarvis confirmed it).** "Narrow" is read as: refuse these builders **only when the draft is named like a report**, in every mode that refuses `weekly-stage` today (ask, confirmed, sweep; held and prep refuse these as stage commands anyway). "Named like a report" means `report`, `weekly` or `client` in the text (the existing `REPORT_NAME` pattern plus the three words, as substrings):
- `report.py adhoc <spec.json>`: the spec's `title`. `report.py steerco-stage <spec.json>`: the spec's `title`, or `version` `client` (its file is "... Steerco one-pager (client).docx").
- `docx_tools.py fill|build-adhoc <template> <spec-or-values> <out.docx>`: the output file name; for `build-adhoc` also the spec's `title`. `docx_tools.py clean <docx> [<out.docx>]`: the output file name (the input itself when there is no second argument).

**How the arguments are read (round 5, after the Opus review).** From the exact positions the scripts parse, never by dropping words that start with `-`: `report.py` takes `argv[0]` as the verb and `argv[1]` as the one spec and runs nothing if there is any other number of arguments; `docx_tools.py fill` and `build-adhoc` take exactly three, `clean` one or two. A word starting with `-` is a file name there (the review's bypasses: `report.py adhoc -w.json`, `report.py adhoc -`, `steerco-stage -c.json`, `build-adhoc -t.docx drafts/n.json 'drafts/Weekly status.docx'`). The spec is opened as the script opens it (relative to the vault, **no `~` expansion**: the shell doesn't expand a quoted `~`, and the guard can't tell a quoted one from an unquoted one). Every `title` and `version` key of the spec's top-level object is checked, in any capitalisation, including a duplicate key (JSON keeps the last value, so `{"title": "Neutral", "title": "... Weekly report"}` was a bypass).

**Refused as report-named (fail closed), listed as false positives:** a spec that can't be read (missing, not JSON, not an object) or is over 1 MB (the script reads it anyway); a spec, template or output word with a `~` anywhere in it (bash expands `x=~/spec.json` to `x=/home/…/spec.json`, zsh also after a `:`, and a leading one; the guard cannot tell a quoted `~` from an unquoted one) or starting with `=` (zsh's `=cmd`); an argument shape the scripts wouldn't run (so nothing would be written). So `report.py adhoc` on a spec that doesn't exist yet is refused (write the spec first, then run it). An unreadable spec is refused for `adhoc` and `steerco-stage` alike, and for `build-adhoc`; a readable spec without any `title` is allowed. A command that can't be split is refused if it names one of the scripts and has a word.

**Lookalikes.** The title and the file name are compared after NFKC (fullwidth letters), removing format and control characters (zero-width), combining marks (accents) and the blank-looking filler letters (U+115F, U+1160, U+17B4, U+17B5, U+180E, U+2800 braille blank, U+3164 Hangul filler, U+FFA0 halfwidth filler), and case folding: `Wéekly`, fullwidth `Ｗｅｅｋｌｙ`, `Wee<zero-width space>kly`, `Wee<U+3164>kly re<U+3164>port` and a combining accent all match. The reversed text is matched too, and a title or name with any bidirectional control character (U+061C, U+200E, U+200F, U+202A to U+202E, U+2066 to U+2069) is refused outright, so a right-to-left override (`<U+202E>troper ylkeeW`, shown as "Weekly report") cannot hide the words. This is wider than v2.5.1's own file rule (`REPORT_NAME`), which does not match those spellings: a report-named file with an accented spelling is still not recognised by v2.5.1 as a report file when it is read or written by other routes. Letters from other alphabets that merely look alike (a Cyrillic `е`) still don't match: accepted. The reversed match also refuses a title that merely contains `troper`, `ylkeew` or `tneilc` (none is a word).

**Not covered (still allowed, exact commands; not widened without Jarvis's word):**
- `python3 system/scripts/filechange.py create 'system/staging/drafts/Weekly status.docx' --from system/staging/drafts/x.docx --why x` (and a direct Write of such a file): an ordinary file change; the 2.5.1 file rule only matches `weekly report` / `client report` names.
- `python3 system/scripts/filechange.py create 'system/staging/drafts/Example Client pack.docx' --from … --why x`: the same.
- A `steerco-stage` draft named after a project whose own name contains a word: the file is "<date> <project name> Steerco one-pager.docx", and the guard does not look the project up.
- Lookalike letters from other alphabets (above).
These are tested as still allowed (`test_what_this_diff_does_not_cover_is_still_allowed`), so closing one means updating the test and this list.

Tests: `dev/tests/test_guard_steerco_adhoc.py` (14 tests): refused in every mode, with the report reason in ask, confirmed and sweep: `adhoc`/`steerco-stage` over 5 launchers and 5 spellings of the verb for 18 + 8 spec files (report titles, duplicate keys, lookalikes, over 1 MB, unreadable, a JSON list) and the dash-led, `-`, `~` cases; 4 odd shapes; and `docx_tools.py` calls (`fill`, `build-adhoc`, `clean`, dashed, spliced, too few or many arguments); ordinary documents, internal one-pagers, neutral `fill`/`build-adhoc`/`clean` and 6 reads allowed and decided exactly as on the unpatched file; a premise test that runs `report.py adhoc` for real in a throwaway vault and shows it takes `-w.json`, `-`, a literal `~/spec-n.json` and a spec over 1 MB and a duplicate-title spec and writes the report-named draft; the hole shown on the unpatched file; all 6 orders of the three diffs. `GUARD_STEERCO_UNPATCHED=1`: 1435 failures. Mutations (each red; failure counts in the report): drop `weekly`, drop the title read, first title key only, an unreadable `steerco-stage` spec allowed, no size limit, drop the client version, drop the output-name check, dash words dropped again, `expanduser` on `~`, `~` refused only at the start, a leading `=` allowed, no filler-letter strip, no bidi refusal, no reversed match, `~`/`=` not checked in `docx_tools` calls, no NFKC, no combining-mark strip, no zero-width strip, no `clean`, an unsplittable command allowed.

## Known limit, for Alan and Jarvis: a write-time race a hook cannot close

A hook decides before a command starts. `python3 system/scripts/report.py adhoc system/staging/drafts/r.json` with a **neutral** spec passes the hook; a Write of `system/staging/drafts/r.json` follows at once (a Write in the drafts folder is allowed) with `{"title": "Example Programme Weekly report"}`; the script is still starting, reads the new spec and writes the report-named draft. The second review simulated it through the real hook in ask mode: 3 of 5 runs wrote the draft (not tried in a real headless claude run, where a background Bash call is needed). No change to `reach.py` can close it, because the check has to happen **when the script writes**.

**Follow-up, not built here (needs `live_server.py`, a guarded file):** `live_server.py` sets an environment marker on every ask creaite run it starts (for example `CREAITE_ASK_RUN=1` in the environment of the `claude -p` process, about 3 lines where the run is started; the Bash tool's children inherit it), and `report.py` (`adhoc`, `steerco-stage`, `weekly-stage`, `client-stage`) and `docx_tools.py` (`fill`, `build-adhoc`, `clean`), neither of which is guarded, refuse a report-named title or output file when the marker is set (about 10 lines each, reusing the matcher: move `_plain` / `_report_word` into a small shared module, since `reach.py` is guarded). That closes the race and the direct-write routes that go through these scripts, at the moment of writing, whatever the spelling. A direct Write or `filechange.py create` of a report-named file in the drafts folder is a separate hole (the 2.5.1 file rule only matches `weekly report` / `client report` names), listed above.

## What Alan must approve

This is a **guard change**: it edits `system/scripts/reach.py`, which decides what ask creaite may run. The change makes the "never `propose.py setting`" rule read the command as the shell does, refuses unquoted pattern characters in every script call, refuses `people migrate`, and makes `command_kind` fail closed. It only adds refusals (listed above). Apply `reach.diff` (and, separately, `reach-report.diff`), or ask for them to be applied, then run `dev/tests/test_guard_report_quoted.py` for the second and `dev/tests/test_guard_174.py`, `test_reach*`, `test_guard_*`, `test_held_bash_arg_forms.py`, `test_permission_panel.py`, `test_record_commands.py`.
