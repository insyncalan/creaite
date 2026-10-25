# #375 Option E1: build plan (2.6.9)

Base: `v268-bare21` (bfb65603). Decision (Alan, 25-10-2026): "E1 in 2.6.9: anchor-based block drop + one read gateway + shape gate + 1,500-char cap; next release only, no one-off re-clean." Option F stays the recorded alternative. History: `dev/proposals/bare/NOTES-2.6.8.md`; proposal: creaite-confidential `releases/calendar-free-text-proposal-DECIDED.md` (Stark's E1 estimate: 9-10 days, range 7-13). Fictional examples only. Plan only: no code touched.

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
| S1 Filter core (+ second layer as S1b, same file, can be a second agent once S1's `keep_indices` signature is fixed) | new `invite_filter.py` (text path: skeleton, anchors, regions/blocks, shape gate, cap; S1b: `drop_labelled_values`, called last in `keep_indices`) | as above | `test_invite_filter_props.py` (P1-P4 on a seeded corpus), label-blind test for the anchor layer (second layer disabled), `test_invite_filter_labels.py` (S1b: positives, negative list, P1/P2, mutants), character-class oracle, timing | none |
| S2 HTML blocks + provider fixtures | `invite_filter.py` (`blocks_from_html`, wired in `filter_text(html=True)`), `dev/tests/fixtures/invites/` (Teams, Zoom, WebEx, Meet, GoTo, dial-in in en/de/fr/es, Outlook footer, recurring) | `blocks_from_html(html) -> list[list[str]]` | `test_invite_filter_providers.py` (every fixture: canaries gone, agenda lines kept) | S1 interface only (stub `keep_lines`) |
| S3 Gateway + stamp | new `calendar_gateway.py`; `sweep.py` (`calendar_row` 1240-1250 calls the filter, stamps; `keep_held_past_days`, `_clean_calendar_file` stamp rows); `session.py` rescrub unchanged call | `read`, `view`, `CLEAN` | `test_calendar_gateway.py` (unstamped served filtered, stamped served as is, cache key, no rewrite on read, unknown purpose raises, grep test of readers) | S1 interface only |
| S4 Readers and prompts | `build_dashboard.py` (1-4), `close_day.py`, `transcripts.py`, `drafts.py` (7-8), `prep_page.py`, `prep_shape.py`, `calendar_refresh.py` (11), `sweep.py` metadata reads (12, 15) | switch each to `calendar_gateway.read(purpose)` | update the ~10 tests that write `calendar.json` by hand (add `clean` or accept in-memory filter), `test_calendar_readers_purpose.py` (per reader: body length bound, none for `day`/`meta`) | S3 |
| S5 Slim `invite_clean.py` | `invite_clean.py`: delete the body path (`_Reader`, windows, soft/word-only/qualified rules; `sweep.rescrub_calendar` re-pointed to filter and stamp); keep `scrub`, `flagged`, `sensitivity`, `clean_row` head, `safe_address`, short-field rules | `invite_text` becomes a thin call to `invite_filter.filter_text` (kept name for the `sweep.invite_text` alias at 1231) | repoint or retire `test_invite_clean_bare*.py`, `_sweep`, `_idempotence`, `_expansion`; keep short-field cases | S1, S3 |
| S6 Corpus, at-rest, release gates | `dev/tests/test_calendar_e1_atrest.py` (grep `dashboard.html`, history snapshot, Prep page, draft, backup zip of a test vault for the corpus canaries), kept-rate prose corpus, mutation checks, fuzz (seeded), hand-check sheet `dev/proposals/375/HANDCHECKS.md`, NOTES-2.6.9 | none | the above | S1-S5 |

Order: S1 || S2 || S3 (S2 and S3 stub S1) -> S4 -> S5 -> S6. S6's corpus builder can start with S1. Cap's oracle gates S1-S3; S4 starts when the gateway signature is merged on the integration branch.

## 4. Guarded vs ordinary

Guarded list (`dev/tests/guarded_chain.py`): tracker, filechange, reach, permissions, backup, update, live_server, client_leak, edit_ai, draft_delivery. **None of S1-S5 touches them**: `invite_filter`, `calendar_gateway`, `invite_clean`, `sweep`, `session`, `drafts`, `prep_page`, `prep_shape`, `build_dashboard`, `close_day`, `transcripts`, `calendar_refresh`, `capture` are ordinary files. Guarded follow-ups, patch files only: (a) **`live_server.py` rescrub.** The rescrub v4 diff (`dev/proposals/369/live_server-rescrub-v4.diff`) ships in 2.6.8 as approved and is not withdrawn. It adds `calendar_rescrub_retry()`, `calendar_rescrub_job()` and the two calls (start-up and the daily job); the job only calls `sweep.rescrub_calendar()`. **Decision for 2.6.9, recommended: keep it as it is and change what it calls.** `sweep.rescrub_calendar` / `_clean_calendar_file` (ordinary, `sweep.py:816-850`) are re-pointed to `invite_filter` plus the stamp, so the start-up rescrub stamps rows with `clean: 1` and the lock, retry and timer logic stay exactly as approved. This needs **no new guarded diff**. The alternative, retiring the job (a new guarded diff deleting `calendar_rescrub_job`, `calendar_rescrub_retry`, `_CALENDAR_RETRY`, `CALENDAR_RETRY` and the two call sites) is not recommended: it would remove the only writer that stamps old rows without a sweep, and a change to approved guarded code buys nothing. (b) `client_leak.py`: an optional canary check that no body-derived text reaches a client output (the approved #368 diff stays frozen; any change needs a new approval). (c) `backup.py`: no change (nothing is rewritten, so nothing in the zip changes; a raw `staging/drafts/calendar.json` is already deleted on any exit by `v268-draft`). `reach.py`'s `CALENDAR_SPEC` is untouched.

## 5. Risks, deletions, effort

**Risks.** *Leak vs loss*: whole-block drop trades over-removal of a real line inside a join block for fewer leaks; anchors are strong so an agenda line sharing a block with a URL goes (accepted; the old approach lost 48%). Mitigation: kept-rate corpus (S6) must keep >= 95% of non-boilerplate prose lines. *Provider shapes*: only one whole-block fixture exists today; S2 must cover Teams (new and classic), Zoom, WebEx, Meet, GoTo, Skype, dial-in lists, Outlook footers. *HTML*: tables, nested tables, `display:none`, comments, entities, `<wbr>`; unknown tags default to block boundaries. *Non-English*: anchors are digits/URLs/dividers, so language does not matter; the shape gate is the only script-sensitive part (use Unicode categories). *Idempotence*: guaranteed by per-block decisions; the generated test also pins it after the cap. *Timing*: bounded input, linear passes. *Residual*: bare prose secret without an anchor (Q1). *Short fields* keep the label rule and its known over-removal ("Pin the roadmap" cases). *Stamp lie*: per-row stamp (above). *Old copies* keep old text by decision.

**What E1 deletes from `invite_clean.py`** (about 430 of 817 lines, estimated): the body label machinery: `BARE_NEXT`/`BARE_FOLLOW`/qualified-label/alone-label regexes (~110-200), `_Reader`, `_pieces`, `_lines`, `_alone`, `_only_labels`, `_label_leads`, `_label_kind`, `id_number`, the date/time exemption, `_looks_like_value`, `_mixed`, `_pending_after`, `_is_dropped`, `WINDOW` and the tombstones (~414-665). What stays: `scrub`, `flagged`, `_views`/`skeleton`/`normal` (reused for deciding), `sensitivity`, `clean_row`, `clean_calendar`, address and name rules, `plain_text` (reused by S2). Roughly 3,000 test lines (bare/bare20/bare21/sweep/idempotence/expansion) are repointed or retired; short-field cases stay.

**Effort (builder-days, range).**

| Slice | WITH second layer | WITHOUT |
|---|---|---|
| S1 filter core | 2.5 (1.5-3.5) | 2.5 (1.5-3.5) |
| S1b `drop_labelled_values` + tests | 1 (0.5-1.5) | 0 |
| S2 HTML blocks, fixtures | 2 (1.5-3) | 2 (1.5-3) |
| S3 gateway, stamp, rescrub re-point | 1.5 (1-2) | 1.5 (1-2) |
| S4 readers and prompts | 1.5 (1-2.5) | 1.5 (1-2.5) |
| S5 slim `invite_clean.py` | 1.5 (1-2.5) | 1.5 (1-2.5) |
| S6 corpus, at-rest, hand checks | 2 (1.5-3) | 1.5 (1-2.5) |
| Review (full + two re-checks) | 1.5 (1-3) | 1.5 (1-2.5) |
| **Total agent-days** | **13.5 (9.5-19)** | **12 (8.5-17.5)** |

About 6 calendar days with S1-S3 in parallel (5 without the second layer). The second layer costs about 1.5 days (0.5-2) and buys protection for a free-typed "PIN: 4417" in prose, which the anchor filter alone does not see. Stark's 9-10 (7-13) assumed the old label rule unchanged underneath, so most of its test churn, and was a builder-day figure without parallelism.

**Hand checks (judgement and live only, rest automated).** Open Prep for three real meetings (Teams, Zoom, plain): the invite panel reads sensibly, no join block. Build a Prep page and an agenda draft for a recurring meeting: "about" line and "The invite says" are useful. Today and Intake unchanged. First start after update: dashboard rebuilds, no error, `calendar.json` rows gain `clean: 1` after the next sweep.

**Tests to add (beyond Cap's oracle).** `test_invite_filter_props`, `test_invite_filter_providers`, `test_calendar_gateway`, `test_calendar_readers_purpose`, `test_calendar_e1_atrest`, kept-rate, mutation (anchor off, divider off, per-row stamp off), seeded fuzz of random HTML wrapping, zero-width, confusables, other-script digits.

## 6. Open questions

Closed by Jarvis/Alan: second layer on the body (yes, minimal, section 1 rule 7); rescrub v4 ships in 2.6.8 (not withdrawn; 2.6.9 keeps it and re-points `sweep.rescrub_calendar`); unstamped rows filtered in memory, readers never rewrite, no one-off re-clean.

1. **Cap**: does agenda attendees need its own `purpose` (`attendees`) so the `day` view stays text-free? Plan default: add `attendees` to `day`.
2. **Cap**: confirm the names `calendar_gateway.read(purpose)` / `view(ev, purpose)`, `invite_filter.keep_lines/keep_indices/drop_labelled_values` and the per-row `clean` key before writing the oracle.
3. **Alan**: the 1,500-character cap is per stored body; the 400 and 600 excerpts are cut from it. Agreed?
4. **Alan/Jarvis**: the hard-label list for the second layer (section 1 rule 7) is short and fixed; any label to add or remove before S1b starts?
