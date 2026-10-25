# #375 Option E1: build plan (2.6.9)

Base: `v268-bare21` (bfb65603). Decision (Alan, 25-10-2026): "E1 in 2.6.9: anchor-based block drop + one read gateway + shape gate + 1,500-char cap; next release only, no one-off re-clean." Option F stays the recorded alternative. History: `dev/proposals/bare/NOTES-2.6.8.md`; proposal: creaite-confidential `releases/calendar-free-text-proposal-DECIDED.md` (Stark's E1 estimate: 9-10 days, range 7-13). Fictional examples only. Updated 26-10-2026 (Jarvis decision: option (c), section 1b).

## 1. Design

**Why it replaces #369.** `invite_clean.py` (817 lines) must *recognise* a secret label to remove its value; 17+ rounds, 48% of lines lost on realistic agendas before option B, and adjacency windows (`WINDOW`, tombstones) make idempotence fragile. E1 recognises *join boilerplate* by language-free anchors and drops the whole block; labels carry no weight.

**New modules (all plain code, no I/O except the gateway).**

| File | Role |
|---|---|
| `system/scripts/invite_filter.py` | Pure. `keep_indices(lines) -> list[int]` (ascending indices of kept input lines), `keep_lines(lines) -> list[str]` (= `[lines[i] for i in keep_indices(lines)]`, never edited, never new), `filter_text(text) -> str` (split on newline, keep_lines, join, cap), `blocks_from_html(html) -> list[list[str]]` (S2), constants `CAP = 1500`, `VERSION = 1`. |
| `system/scripts/calendar_gateway.py` | The one read path. `CLEAN = 1`; `read(purpose, path=paths.CALENDAR) -> {"fetched","to","days"}`; `view(ev, purpose) -> dict`; `purpose_names()`; `stamp_rows(days) -> days`. |

**Filter rules (decided per block from its own text only, so P4 locality holds).**
1. *Skeleton for deciding, original line for output*: NFKC + remove zero-width/invisible + map confusables, digits by Unicode category Nd (not `\d` on raw text), skeleton used only to test; the output line is the input line byte for byte.
2. *Units*: HTML first (S2): `table`, `tr`, `p`, `div`, `li`, `br`-runs and `blockquote` each become one block (label cell and value cell stay together; this is the hard part, flattening table cells first is what split label from value in #369). Plain text: blocks split at blank lines. *Regions*: a divider line (`____`, `----`, `====`, box-drawing, `- - -`, three or more) starts a region; a region ends at the next divider or the end. Teams and Zoom boilerplate sits between dividers.
3. *Anchors* (language-free): URL (scheme, `www.`, `host/path` shapes, `tel:` `sip:` `msteams:` `zoommtg:`); phone shapes and `,,123456#` / `123456#` dial strings; a run of 7 or more digits counting Nd digits across spaces/dashes/dots (`987 654 321`, `+44 20 7946 0000`); 3+3+3 groups; a long mixed token (>=12 chars, letters and digits, not a URL) is a *weak* anchor (shape gate, not block drop).
4. *Drop rule*: a block holding a strong anchor is dropped whole; a region holding a strong anchor is dropped whole (all its blocks). Nothing outside the region/block changes. No label word is consulted. The decisive test: replace every label word with random strings; the block must still go.
5. *Shape gate* on survivors (character-class, independent oracle in the tests): drop a line that is, after skeleton, a single token of 6 to 40 chars mixing letters and digits, or only 4+ digits/hex, or a lone token of 8+ letters with no space and no vowel pattern typical of words, or longer than 300 chars with no space-separated words (encoded blob). Dates and times (`12-11-2026`, `14:00`, `Room 204`, `Budget 1,200,000`) stay: they fail no gate. Thresholds are tuned on the kept-rate corpus (S6), not guessed.
6. *Cap*: whole lines only, in order, until 1,500 characters; a line that would cross is dropped and the rest too (still a subset). No mid-line cut.
7. *Second layer on the body (Jarvis, decided)*: after the anchor filter and the shape gate, one small safety net, `invite_filter.drop_labelled_values(lines) -> list[int]` (kept indices; `keep_indices` calls it last, so `keep_lines` stays a subset). Rule, nothing else: a line whose skeleton holds a **hard label** (fixed short list: passcode, password, pwd, pin, otp, secret, token, meeting id, access code, host key, and the provider-prefixed forms; no qualifier phrases) followed by a separator (`: = - \u2013 \u2014 > is`, or end of line) and a **value containing a digit, or a hex run of 6+, or a mixed letters-and-digits token** goes. If the label ends the line (value absent), the **next non-blank line** goes when it is such a value, and only that one line. No soft-heading windows, no word-only windows, no qualifier phrases, no glued-label rules, no tombstones: each line is decided from itself and (for the label-alone case) its single successor, so P1 and P2 hold; the pair rule is idempotent because a dropped label line takes its value with it, and a kept label line has no value-shaped successor. Residual after both layers: a word-only secret ("Code word: kqZxyw") and anything the list does not name. Tests: P1/P2/P3 on the generated corpus with random labels from the list, a negative list ("Password reset", "Pin the roadmap", "Code of conduct", "Token refresh", dates and times under such headings all stay), mutation (rule off; value shape widened to any word, which must fail the negative list), timing. The big label machinery (`invite_clean.scrub` and the `LABEL` family) stays **only for the short fields** (title, place, recurrence, names, attachments), where the title reaches clients.

**Guarantees.** P1 idempotent (`keep_lines(keep_lines(x)) == keep_lines(x)`; holds because decisions are per block/region and a kept block is unchanged by removing other blocks; dividers are kept lines that bound regions, so a kept divider still bounds the same region). P2 subsequence of the input. P3 no anchor line survives. P4 locality (add/reorder unrelated blocks, same survivors). Timing: linear, no backtracking regexes on raw input; input cut to `BODY_MAX` (20,000) before the filter; test: 1 MB hostile input under a fixed ceiling (reuse `test_invite_clean_timing.py` harness).

**Gateway and the stamp.** Writers (`sweep.calendar_row`, `keep_held_past_days`, the rescrub) set `"clean": 1` **on every row** (and top-level), because `keep_held_past_days` merges old rows into a new file, so a file-level stamp alone would lie. `read(purpose)`: a row with `clean < CLEAN` or no stamp is filtered **in memory, on read**, then served; the cache key is `(mtime_ns, size, inode, CLEAN)`; the file is not rewritten by readers. Rewrite happens only on the next sweep save or the session-start rescrub (which stamps what it finds). **Old unstamped data (decided, no one-off re-clean):** unstamped rows are filtered in memory on every read and never served raw; readers never rewrite the file; only the sweep save and the start-up rescrub (`sweep.rescrub_calendar`) write, and they stamp. Nothing else is cleaned (next release only). Old snapshots, `dashboard.html` history, Prep pages and backup zips are not touched (Alan's decision); the first dashboard build after the update rebuilds `dashboard.html` from filtered data.

**`purpose()` views** (what a reader may see; a field not listed is absent from the returned row; confidential/private rows follow `invite_clean.sensitivity`, unchanged):

| purpose | body | other |
|---|---|---|
| `meta` | none | `fetched`, `to`, day/meeting counts only (sweep gap logic, calendar_refresh outcome, dashboard fetch time) |
| `day` | none | title, times, where, teams flag, organiser, id, recurrence, sensitivity (Today, Intake, close_day, transcripts, drafts attendees) |
| `prep_rank` | filtered, up to 1,500 | + attachments, attendees (stems for ranking) |
| `prep_panel` | filtered, up to 1,500 | + attachments, attendees, organiser_email (the dashboard's Prep tab) |
| `prep_page` | filtered, up to 1,500 | + attachments (Claude's research prompt) |
| `agenda` | filtered, up to 1,500 (the draft takes 1,500, shows 400) | + where |
| `shape` | filtered, up to 600 | |

A view with a body never exceeds its length, always whole lines. Purposes are a closed set; an unknown one raises (tests pin it).

## 1b. Architecture for 2.6.9: option (c), E1 on top of the 2.6.8 scrub (decided 26-10-2026)

Body filter = HTML/blocks conversion -> anchor layer + shape gate (`second_layer=False`) -> the 2.6.8 scrub (`invite_clean.invite_text`) on the surviving lines as the **body label layer** -> CAP. Code: `invite_filter.filter_text_with_scrub(text, html=None)`; `calendar_gateway`'s default FILTER calls it. `invite_clean.py`, `sweep.py` and every 2.6.8 file are untouched. The one point that touches the scrub is `invite_filter._scrub_pairs(lines)` (a single narrow wrapper; re-point it when bare22 changes `invite_text`).

**Subset and idempotence.** `invite_text` rewrites lines (tags, spaces, "pass code" -> "passcode"), so `_scrub_pairs` maps each output line back to the input line it came from (same normalisation, in order) and emits the ORIGINAL line, byte for byte. Measured on 8,000 fuzz bodies: every non-blank output line is a converted line (unmatched lines: 0); blank lines are the scrub's own. Idempotent: 0 failures in 40,000 bodies. Unmatched lines, should any ever appear, are emitted as the scrub wrote them (subset holds only up to normalisation for that line); a test pins both properties.

**Order matters.** Scrub after anchors leaks 2,041 bodies in 40,000; both layers judging the full converted lines (a line must pass both) leaks 2,194. Removing the digit values first makes the scrub's label windows count and eat the next lines, which also swallows more word-only values. The cost is that a label whose value an anchor already dropped eats one or two innocent agenda lines (the scrub's own window behaviour; fixture `label_same_cell_br` loses "Room 204" and "Notes are kept on the team page."; the integration test lists it in `SCRUB_WINDOW_LOSS`). 26 bodies in 40,000 leak a value the scrub alone would have caught (a qualified label such as "PIN to follow" whose window was spent on a neighbouring line after the anchor layer removed its value).

**Comparison: 40,000 bodies (8 generators x 5,000, seed 369), planted secrets, leak bodies / idempotence failures / leak items split digit-bearing vs word-only.** Counts include the classes the 2.6.8 scrub itself lists as known (qualified label alone, header-cell label, soft heading + short token, word-only after an ID label); 0 of the scrub's leaks are outside those classes.

| Generator | E1 minimal (no S1b) | E1 + S1b (old default) | 2.6.8 scrub alone | **E1 + scrub (c)** |
|---|---|---|---|---|
| html_table | 1,545 | 1,256 | 2,090 | **516** |
| nested_lists | 1,742 | 954 | 0 | **0** |
| blockquote | 3,633 | 2,569 | 839 | **187** |
| md_table | 3,610 | 3,610 | 443 | **270** |
| mixed_invite | 1,187 | 558 | 0 | **0** |
| qualified | 2,193 | 2,103 | 3,301 | **917** |
| soft_dates | 535 | 535 | 3 | **3** |
| accents | 2,984 | 2,156 | 658 | **148** |
| **Leak bodies (of 40,000)** | 17,429 | 13,741 | 7,334 | **2,041** |
| Idempotence failures | 0 | 0 | 0 | **0** |
| Leak items, digit-bearing | 16,926 | 10,183 | 7,302 | **853** |
| Leak items, word-only | 9,724 | 9,634 | 1,877 | **1,344** |

Adding S1b under the scrub (E1 + S1b + scrub): 2,042 leak bodies, 0 idempotence failures: **no measurable gain (+1)**.

**Utility** (lines kept; the 74-line agenda sets are not in the repository, so a 200-line synthetic agenda set was used: 40 agendas of 3 plain lines and 2 label-word lines, 80 of the 200 lines being traps such as "Pin the roadmap", "Password reset rollout", "Code of conduct refresh", "Token refresh", "Dress code", "Key milestones"):

| Measure | E1 minimal | E1 + S1b | scrub alone | E1 + scrub |
|---|---|---|---|---|
| 27 fixtures, must_keep lines kept (of 59) | 59 | 59 | 49 | 57 |
| Fixture planted secrets surviving | 2 | 0 | 12 | 0 |
| Synthetic agenda lines kept (of 200) | 200 (100%) | 200 (100%) | 162 (81%) | 162 (81%) |
| Trap lines kept (of 80) | 80 | 80 | 49 | 49 |

Reading: (c) cuts leaks by 72% against the scrub alone (2,041 against 7,334; digit-bearing 853 against 7,302) and by 88% against E1 minimal, at the scrub's own utility (it inherits the 19% agenda-line loss on label-word agendas; E1 adds none). Options E1 minimal / E1 + S1b keep 100% of agenda lines but leak 7x to 8x more. The word-only leaks that remain (1,344) are the documented limit (word-only values after a qualified label or an ID label).

**S1b status: dropped.** Over the scrub it adds nothing measurable (+1 leak body of 40,000, no utility change). It stays in `invite_filter.py` as the pure function `drop_labelled_values` (default of `filter_text`, used by the E1-only fallback path and by its tests) but is **not** in the shipped path; it can be deleted with its tests if the fallback is not wanted. Cost saved: about 1 builder-day.

**Zoom last-paragraph block cutter.** A Zoom body of `<div>..</div><br><div>..</div>` gave no blank line between the paragraphs (a `<div>` is a line break, not a block; the lone `<br>` after it was ignored), so the last paragraph sat in the join block and was dropped with it (fixture `zoom_html` had lost "Please add retro items to the shared board beforehand."). Fix, made in `invite_blocks._Emit.br`: a lone `<br>` after a line that a `<div>`/block ended is a paragraph break (div, br, div -> blank line). Fixture `zoom_html` `must_keep` is back to the original two lines (with the fix, "Retro for the platform team..." and "Please add retro items..." are separate blocks; the closing line is kept); its `expected_lines` now show the blank lines. `test_invite_filter_scrub_layer.py` pins the cutter cases.

## 1c. Results with bare22 underneath (26-10-2026)

Same 40,000 bodies (8 generators x 5,000, seed 369), generators from `dev/tests/test_invite_clean_fuzz_html.py` (now in the tree via `v268-bare22`, 5ee709a4). Code: `invite_filter.filter_text_with_scrub(text, html=None, order="anchors_first"|"scrub_first")`; `DEFAULT_ORDER = "anchors_first"`. Order A = anchors/shape gate then scrub; B = scrub on the converted lines, then anchors/shape gate (blank lines tidied afterwards, otherwise 543 idempotence failures from a blank left where a block was dropped); C = both judge the full lines, a line must pass both (measured only); D = the scrub on the raw body (its own HTML handling), then the anchor layer on its output (measured only, not built).

| Leak bodies of 5,000 | E1 min | scrub alone | A anchors-first | B scrub-first | C parallel | D scrub-raw, anchors |
|---|---|---|---|---|---|---|
| html_table | 1,545 | 299 | 378 | 640 | 458 | 299 |
| nested_lists | 1,742 | 0 | 0 | 0 | 0 | 0 |
| blockquote | 3,633 | 2 | 0 | 0 | 0 | 2 |
| md_table | 3,610 | 0 | 0 | 0 | 0 | 0 |
| mixed_invite | 1,187 | 0 | 0 | 0 | 0 | 0 |
| qualified | 2,193 | 0 | 44 | 0 | 0 | 0 |
| soft_dates | 535 | 3 | 3 | 3 | 3 | 3 |
| accents | 2,984 | 0 | 0 | 0 | 0 | 0 |
| **Total leak bodies (of 40,000)** | 17,429 | **304** | **425** | **643** | **461** | **304** |
| Idempotence failures | 0 | 0 | 0 | 0 (after blank tidy) | 0 | 0 |
| Leak items, digit-bearing | 16,926 | 4 | 131 | 207 | 143 | 4 |
| Leak items, word-only | 9,724 | 309 | 319 | 478 | 348 | 309 |
| Leaks outside the scrub's listed classes (bodies) | n/a | 0 | 155 | 196 | 133 | 0 |

| Utility | E1 min | scrub alone | A | B | C | D |
|---|---|---|---|---|---|---|
| Fixtures, must_keep kept (of 59) | 59 | 50 | 58 | **59** | 59 | 50 |
| Fixture planted secrets surviving | 2 | 11 | 0 | 0 | 0 | 0 |
| Fixtures, non-secret lines kept (of 148 expected, blank and secret-bearing lines excluded) | 91 (61.5%) | 86 (58.1%) | 76 (51.4%) | **96 (64.9%)** | 77 (52.0%) | 79 (53.4%) |
| 200-line synthetic agenda set, kept | 200 | 150 (75%) | 150 | 150 | 150 | 150 |
| Trap lines kept (of 80) | 80 | 39 | 39 | 39 | 39 | 39 |

Reading.
- **bare22 changed the picture.** The scrub alone now leaks 304 bodies of 40,000 (7,334 before), all in its listed classes (header-row word-only values, word-only after an ID label, soft heading plus short token), and none outside them. Its agenda loss grew to 25% (162 to 150 of 200).
- **On the fuzz corpus no E1 composition beats the scrub alone.** A, B and C each add leaks: the converted lines lose the table structure the scrub reads in the raw HTML (a label row and its value row no longer sit together), and 133 to 196 bodies leak a value outside the scrub's listed classes (mostly the html_table header-row layout with short values). Only D (scrub on the raw body first) matches the scrub on leaks; it also keeps its utility loss, so it adds nothing but the anchor layer's extra drops, which on this corpus remove no further secret.
- **On the realistic fixtures E1 composition does clearly better than the scrub alone:** planted secrets surviving 0 against 11, and B keeps all 59 must_keep lines (scrub alone 50). B also keeps the most non-secret lines (64.9%, above E1 minimal's 61.5%, since it keeps lines the anchor layer's blocks would otherwise lose after a dropped neighbour).
- **A against B.** A: fewer fuzz leaks (425 against 643; digit-bearing 131 against 207; outside-class bodies 155 against 196) but its 44 `qualified` leak bodies are the order defect (a qualified label such as "PIN to follow" whose value the anchor layer dropped), it loses one must_keep line (the documented `label_same_cell_br` window loss, two lines) and keeps 51% of the fixtures' non-secret lines. B: no qualified leaks, no window loss, best utility; all its extra leaks are html_table header-row bodies (640 against 378) and they are digit-bearing as often as A's. C leaks 461 and keeps 52%: no better than A.
- **Recommendation: A stays the default (fewest leaks of the E1 orders, secrets first); B is selectable and is the choice if utility on real invites outweighs 218 extra header-row leak bodies in 40,000 synthetic ones.** Neither is better than the scrub alone on fuzz leaks. The remaining fix is in the conversion, not the order: keep a table row's cells together on one line in `invite_blocks` (`Meeting ID | Other | swordfish`), so the scrub's header-row logic sees what it sees in the raw HTML. Until then D (scrub on the raw body, then anchors) is the leak-minimal fallback, at the scrub's utility.

Tests: `dev/tests/test_invite_filter_order.py` (both orders: subset up to blank lines and idempotence on the 40,000 fuzz bodies, fixtures' secrets gone and must_keep kept, default, unknown order refused, blank tidy).

## 2. Readers of calendar.json (on `v268-bare21`)

| # | Reader (file:line) | Today | Needs from the gateway |
|---|---|---|---|
| 1 | `build_dashboard.py:2043` `calendar()` | `invite_clean.read_calendar` | `read("day")` (Today day view) |
| 2 | `build_dashboard.py:2590` `saved_calendar_days()` | `read_calendar` | `read("prep_panel")`; feeds `prep_rank` (3399, body+attachments) and the PREP_ONLY fields (3335, 3374) which go to the page; also 3159 below |
| 3 | `build_dashboard.py:2844` (meetings/Intake rows) | `read_calendar` | `read("day")` |
| 4 | `build_dashboard.py:3159` `fetched` | **direct JSON, bypasses** | `read("meta")["fetched"]` |
| 5 | `close_day.py:347` | `read_calendar` | `read("day")` |
| 6 | `transcripts.py:222` `calendar_rows` | `read_calendar` | `read("day")` |
| 7 | `drafts.py:1301` `calendar_event` (agenda: 1140 builds body, 1157-1162 source line) | `read_calendar` | `read("agenda")` |
| 8 | `drafts.py:1693` `_meeting_attendees` | `read_calendar` | `read("day")` (attendees; add to the day view or use `prep_rank`: Q4) |
| 9 | `prep_page.py:70` `_event`, 360 passes body | `read_calendar` | `read("prep_page")` |
| 10 | `prep_shape.py:342` (via ctx meeting; 600-char excerpt) | gets the row from prep_page/dashboard context | row must come from `read("shape")` |
| 11 | `calendar_refresh.py:91` `outcome` | **direct JSON, bypasses** | `read("meta")` counts |
| 12 | `sweep.py:656` `calendar_start`, `:671` `calendar_span` | direct JSON (fetched/to only) | `read("meta")` |
| 13 | `sweep.py:760` `keep_held_past_days` | direct JSON, then `clean_row` | gateway rows with the stamp kept; no re-filter of stamped rows |
| 14 | `sweep.py:821/834` `_clean_calendar_file` (writer, session start) | direct JSON, writes | stays the one rewrite path; stamps rows |
| 15 | `sweep.py:875` `saved_meetings_from` | direct JSON, counts | `read("meta")` |
| 16 | `sweep.py:1012-1020` `calendar()` save | writer | `calendar_row` (1240-1250) calls `invite_filter` and stamps |
| 17 | `live_server.py:4754, 4828` | `stat` only (cache stamps), no content | no change |
| 18 | `capture.py:338` | sensitivity of one event | none |

So the "8 direct readers, 2 bypass" is: gateway readers 1-3, 5-9 already use `invite_clean.read_calendar`; the bypass reads are 4 and 11 (plus the sweep.py metadata reads 12, 15, which only count). A test (`test_calendar_e1_gateway`) greps `system/scripts` for `paths.CALENDAR` and `calendar.json` reads and allows only the gateway, `sweep.py` writer lines and `live_server` stat lines.

## 3. Slices (independent agent tasks)

Contracts first (frozen the day Cap's oracle lands): `invite_filter.keep_indices/keep_lines/filter_text`, `calendar_gateway.read/view`, the `clean` stamp key, the purpose names above. Cap writes `dev/tests/test_calendar_e1_*.py` (failing today); slices own the *other* tests.

| Slice | Files (ordinary unless noted) | Interface | Tests it owns | Depends on |
|---|---|---|---|---|
| S1 Filter core (+ second layer as S1b, **S1b DROPPED from the shipped path, section 1b**;  same file, can be a second agent once S1's `keep_indices` signature is fixed) | new `invite_filter.py` (text path: skeleton, anchors, regions/blocks, shape gate, cap; S1b: `drop_labelled_values`, called last in `keep_indices`) | as above | `test_invite_filter_props.py` (P1-P4 on a seeded corpus), label-blind test for the anchor layer (second layer disabled), `test_invite_filter_labels.py` (S1b: positives, negative list, P1/P2, mutants), character-class oracle, timing | none |
| S2 HTML blocks + provider fixtures | `invite_filter.py` (`blocks_from_html`, wired in `filter_text(html=True)`), `dev/tests/fixtures/invites/` (Teams, Zoom, WebEx, Meet, GoTo, dial-in in en/de/fr/es, Outlook footer, recurring) | `blocks_from_html(html) -> list[list[str]]` | `test_invite_filter_providers.py` (every fixture: canaries gone, agenda lines kept) | S1 interface only (stub `keep_lines`) |
| S3 Gateway + stamp | new `calendar_gateway.py`; `sweep.py` (`calendar_row` 1240-1250 calls the filter, stamps; `keep_held_past_days`, `_clean_calendar_file` stamp rows); `session.py` rescrub unchanged call | `read`, `view`, `CLEAN` | `test_calendar_gateway.py` (unstamped served filtered, stamped served as is, cache key, no rewrite on read, unknown purpose raises, grep test of readers) | S1 interface only |
| S4 Readers and prompts | `build_dashboard.py` (1-4), `close_day.py`, `transcripts.py`, `drafts.py` (7-8), `prep_page.py`, `prep_shape.py`, `calendar_refresh.py` (11), `sweep.py` metadata reads (12, 15) | switch each to `calendar_gateway.read(purpose)` | update the ~10 tests that write `calendar.json` by hand (add `clean` or accept in-memory filter), `test_calendar_readers_purpose.py` (per reader: body length bound, none for `day`/`meta`) | S3 |
| S5 Slim `invite_clean.py` | **REMOVED from 2.6.9 (26-10-2026).** `invite_clean.py` stays whole: its body scrub is the label layer of option (c) (section 1b). Slimming is a later release, if ever. | | | |
| S6 Corpus, at-rest, release gates | `dev/tests/test_calendar_e1_atrest.py` (grep `dashboard.html`, history snapshot, Prep page, draft, backup zip of a test vault for the corpus canaries), kept-rate prose corpus, mutation checks, fuzz (seeded), hand-check sheet `dev/proposals/375/HANDCHECKS.md`, NOTES-2.6.9 | none | the above | S1-S5 |

Order: S1 || S2 || S3 (S2 and S3 stub S1) -> S4 -> S6 (S5 removed). S6's corpus builder can start with S1. Cap's oracle gates S1-S3; S4 starts when the gateway signature is merged on the integration branch.

## 4. Guarded vs ordinary

Guarded list (`dev/tests/guarded_chain.py`): tracker, filechange, reach, permissions, backup, update, live_server, client_leak, edit_ai, draft_delivery. **None of S1-S5 touches them**: `invite_filter`, `calendar_gateway`, `invite_clean`, `sweep`, `session`, `drafts`, `prep_page`, `prep_shape`, `build_dashboard`, `close_day`, `transcripts`, `calendar_refresh`, `capture` are ordinary files. Guarded follow-ups, patch files only: (a) **`live_server.py` rescrub.** The rescrub v4 diff (`dev/proposals/369/live_server-rescrub-v4.diff`) ships in 2.6.8 as approved and is not withdrawn. It adds `calendar_rescrub_retry()`, `calendar_rescrub_job()` and the two calls (start-up and the daily job); the job only calls `sweep.rescrub_calendar()`. **Decision for 2.6.9, recommended: keep it as it is and change what it calls.** `sweep.rescrub_calendar` / `_clean_calendar_file` (ordinary, `sweep.py:816-850`) are re-pointed to `invite_filter` plus the stamp, so the start-up rescrub stamps rows with `clean: 1` and the lock, retry and timer logic stay exactly as approved. This needs **no new guarded diff**. The alternative, retiring the job (a new guarded diff deleting `calendar_rescrub_job`, `calendar_rescrub_retry`, `_CALENDAR_RETRY`, `CALENDAR_RETRY` and the two call sites) is not recommended: it would remove the only writer that stamps old rows without a sweep, and a change to approved guarded code buys nothing. (b) `client_leak.py`: an optional canary check that no body-derived text reaches a client output (the approved #368 diff stays frozen; any change needs a new approval). (c) `backup.py`: no change (nothing is rewritten, so nothing in the zip changes; a raw `staging/drafts/calendar.json` is already deleted on any exit by `v268-draft`). `reach.py`'s `CALENDAR_SPEC` is untouched.

## 5. Risks, deletions, effort

**Risks.** *Leak vs loss*: whole-block drop trades over-removal of a real line inside a join block for fewer leaks; anchors are strong so an agenda line sharing a block with a URL goes (accepted; the old approach lost 48%). Mitigation: kept-rate corpus (S6) must keep >= 95% of non-boilerplate prose lines. *Provider shapes*: only one whole-block fixture exists today; S2 must cover Teams (new and classic), Zoom, WebEx, Meet, GoTo, Skype, dial-in lists, Outlook footers. *HTML*: tables, nested tables, `display:none`, comments, entities, `<wbr>`; unknown tags default to block boundaries. *Non-English*: anchors are digits/URLs/dividers, so language does not matter; the shape gate is the only script-sensitive part (use Unicode categories). *Idempotence*: guaranteed by per-block decisions; the generated test also pins it after the cap. *Timing*: bounded input, linear passes. *Residual*: bare prose secret without an anchor (Q1). *Short fields* keep the label rule and its known over-removal ("Pin the roadmap" cases). *Stamp lie*: per-row stamp (above). *Old copies* keep old text by decision.

**What E1 deletes from `invite_clean.py`** (about 430 of 817 lines, estimated): the body label machinery: `BARE_NEXT`/`BARE_FOLLOW`/qualified-label/alone-label regexes (~110-200), `_Reader`, `_pieces`, `_lines`, `_alone`, `_only_labels`, `_label_leads`, `_label_kind`, `id_number`, the date/time exemption, `_looks_like_value`, `_mixed`, `_pending_after`, `_is_dropped`, `WINDOW` and the tombstones (~414-665). What stays: `scrub`, `flagged`, `_views`/`skeleton`/`normal` (reused for deciding), `sensitivity`, `clean_row`, `clean_calendar`, address and name rules, `plain_text` (reused by S2). Roughly 3,000 test lines (bare/bare20/bare21/sweep/idempotence/expansion) are repointed or retired; short-field cases stay.

**Effort (builder-days, range), revised 26-10-2026 for option (c).**

| Slice | (c) without S1b (recommended) | (c) with S1b (before the measurement) |
|---|---|---|
| S1 filter core | 2.5 (1.5-3.5) | 2.5 (1.5-3.5) |
| S1b `drop_labelled_values` + tests | 0 (built, not shipped) | 1 (0.5-1.5) |
| S2 HTML blocks, fixtures | 2 (1.5-3) | 2 (1.5-3) |
| S3 gateway, stamp, rescrub re-point | 1.5 (1-2) | 1.5 (1-2) |
| S4 readers and prompts | 1.5 (1-2.5) | 1.5 (1-2.5) |
| S5 slim `invite_clean.py` | 0 (removed) | 0 (removed; was 1.5) |
| (c) composition, wrapper, comparison, cutter fix | 1 (0.5-1.5) | 1 |
| S6 corpus, at-rest, hand checks | 1.5 (1-2.5) | 2 (1.5-3) |
| Review (full + two re-checks) | 1.2 (1-2) | 1.5 (1-2.5) |
| **Total agent-days** | **11.2 (7.5-17)** | **13.0 (9-19)** |

About 5 calendar days without S1b (S1-S3 in parallel, largely built on `v269-int`), about 5.5 with it. Against the earlier plan (13.5 with, 12 without S1b/S5) removing S5 saves about 1.5 days and dropping S1b about 1 day more, at the cost of keeping the 2.6.8 scrub's utility loss on label-word agendas.

**Hand checks (judgement and live only, rest automated).** Open Prep for three real meetings (Teams, Zoom, plain): the invite panel reads sensibly, no join block. Build a Prep page and an agenda draft for a recurring meeting: "about" line and "The invite says" are useful. Today and Intake unchanged. First start after update: dashboard rebuilds, no error, `calendar.json` rows gain `clean: 1` after the next sweep.

**Tests to add (beyond Cap's oracle).** `test_invite_filter_props`, `test_invite_filter_providers`, `test_calendar_gateway`, `test_calendar_readers_purpose`, `test_calendar_e1_atrest`, kept-rate, mutation (anchor off, divider off, per-row stamp off), seeded fuzz of random HTML wrapping, zero-width, confusables, other-script digits.

## 6. Open questions

Closed by Jarvis/Alan: second layer on the body (yes, minimal, section 1 rule 7); rescrub v4 ships in 2.6.8 (not withdrawn; 2.6.9 keeps it and re-points `sweep.rescrub_calendar`); unstamped rows filtered in memory, readers never rewrite, no one-off re-clean.

1. **Cap**: does agenda attendees need its own `purpose` (`attendees`) so the `day` view stays text-free? Plan default: add `attendees` to `day`.
2. **Cap**: confirm the names `calendar_gateway.read(purpose)` / `view(ev, purpose)`, `invite_filter.keep_lines/keep_indices/drop_labelled_values` and the per-row `clean` key before writing the oracle.
3. **Alan**: the 1,500-character cap is per stored body; the 400 and 600 excerpts are cut from it. Agreed?
4. **Alan/Jarvis**: the hard-label list for the second layer (section 1 rule 7) is short and fixed; any label to add or remove before S1b starts?
