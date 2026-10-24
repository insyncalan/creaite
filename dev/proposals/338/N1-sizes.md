# #338 N1: sizes of what runs load (24-10-2026)

Report only; nothing trimmed. Measured on the v264-prep tree with `python3 dev/tools/size_report.py` (tokens = bytes / 4).

| File | Bytes | ~Tokens |
|------|------:|--------:|
| root `CLAUDE.md` | 737 | 185 |
| `system/creaite-rules.md` (2.6.2 line, before the slim diff) | 66,315 | 16,579 |
| project memory template | 1,620 | 405 |
| new-vault `CLAUDE.md` template | 662 | 166 |
| 10 skill files (`SKILL.md`), loaded only when a skill is named | 166,490 | 41,626 |

## Finding

1. **Rules are the only always-loaded file worth trimming**, and that is #338 part C (−50.1%, about 7,900 tokens a run). Root `CLAUDE.md` (185 tokens) and the project memory template (405 tokens) are small: nothing to trim.
2. **Skill bodies are the next lever but load only when a skill runs.** Largest: cx-minutes 39.9 KB (~10k tokens), cx-sweep 32.6 KB (~8.2k), cx-setup 20.6 KB, cx-edit 19.8 KB, cx-review 17.4 KB. A sweep or minutes run therefore adds 8k to 10k tokens on top of the rules.
3. **Skill front matter** (the description each run lists) is 423 to 789 bytes a skill, about 5.8 KB (~1.4k tokens) in all: fine, no action.
4. **Trim candidates if wanted (a later step, not asked):** cx-minutes and cx-sweep each have 7 to 12 `##` sections of which several are mode-specific (Quick notes, Minutes by someone else, Drafted emails seen sent, Guessed fields); moving those into `references/` read on demand, as cx-minutes already does for three files, could save perhaps 3k to 5k tokens on a typical run.
5. **Scale:** all of this is small against 366k to 503k ask starts (#339); resuming a long session (part B) is the large lever, so any skill trimming should be measured with `dev/tools/compare_start_tokens.py` before it is worth the risk.
