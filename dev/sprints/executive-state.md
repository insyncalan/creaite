# Sprint: Executive-ready Current state (BL-106)

Branch `sprint-exec-state`, worktree `../creaite-exec-state`. Part of **v1.2.0** (Alan, 09-10-2026). Read BL-106 in `dev/BACKLOG.md` first. It holds Alan's decisions; where it says "to confirm", the answers below apply.

## Alan's decisions (09-10-2026)

- "AI Create" is the **Generate** button (confirmed in the code: `openGen`, `/api/current/generate`, `current-state-prompt.md`).
- It ships in **v1.2.0**.
- The client-safe audience has the **same structure, plainer, with no internal remarks**.
- **Lengths:** Short about 40 words (the headline and one line), Standard 120 to 150, Fuller about 250. Default Standard.

**Status (09-10-2026): MERGED into `main`. Phases A, B and C built; two clean full-suite runs (59 files each) before the last `main` merge-in. Requirement FR-111 (main took FR-104 to FR-110 for recode, sprint-4b and sprint-debug-log-2b). Worktree and branch removed. Left for Alan: the acceptance read of Generate and Make it executive on real projects.**

Phase C as built: decisions needed in the Asks part; the weekly and client skills read the guide and the sheet; BRD (FR-62, FR-104), `BUILD.md`, Help and the guides, the rules text and the 1.2.0 release notes.

Phase B as built: the Generate material and prompt (item 6); the Generate dialog's **Audience** and **Length**, remembered in the browser (item 7); the `/api/current/check` route and the notes under the draft, with the facts sheet shown under "Facts it was written from" (item 8); **Make it executive** in the editor's action row, with `/api/current/rewrite`, shown as an executive version Alan uses or discards (item 9); tests (item 10): `test_status_prompt.py`, `test_status_live.py` and `test_status_live_browser.py`.

## Goal

Generate writes an executive status (a position, why, what it means, what is needed) from a short ranked facts sheet, not from a dump of the work lists. **No schema change.**

## Three things the spec glosses over

- **Decisions pending don't exist yet.** The `decisions` table has no pending state; that is BL-53 (Sprint 5). Asks are built from what exists now (items others owe Alan, open dependencies, blockers). "Decisions needed" joins when Sprint 5 has merged. A part the sheet can't fill is left out, not shown empty (as BL-92 does).
- **"Numbers" is not a pure no-model step.** Code collects *candidate* lines from the period's minutes and reports (a %, "x of y", a target or a baseline) with their source. The prompt says to use one only if it matters. Nothing is parsed into figures.
- **No headings above `###` in the editor.** The five parts render as a bold headline paragraph, then short bullets with bold lead-ins (**Why.** **Risks.** **Asks.** **Next.**).

## Phases

Commit each item separately. Phase A can start now; B waits for 4b and chat-sweep to merge; C waits for Sprint 5.

### Phase A: new files only (no clash with any sprint in flight)

1. **The style guide.** `system/templates/executive-style.md`, per BL-106: the five parts (headline, why, risks that matter, asks and decisions, next period), the rules, and two fictional examples (the item-by-item draft it replaces, and the executive version). Written in British English, DD-MM-YYYY. It is inserted into prompts as a value, never through `.format` templates, so braces in it are safe.
2. **The facts sheet.** New `system/scripts/status_facts.py`; `facts(code, start, end, audience)` returns a structure and a plain-text rendering with sources. No model call. Parts: Position, Movement, Exposure, Asks, Numbers (candidates), Trend.
   - **Reuse, don't copy:** `report.health_evidence` / `criteria`, `report.milestones`, `report.flow_line_for`, `build_dashboard.early_warnings`, the dependency/blocker queries.
   - **Ranking is deterministic and capped** (risks named, overdue items named, items named in Movement), with the caps in settings.
   - **Changed since the last approved status:** compare with the latest `updates` row.
   - **Client-safe mode:** only `client_visible` items, in their `client_message` wording; no `Client-safe: no` memory lines; no documents.
   - **CLI:** `python3 system/scripts/status_facts.py facts CODE [--from] [--to] [--audience internal|client] [--text]`. `report.py` gets only a thin `facts` command that calls it (Sprint 5 owns `report.py`).
3. **The checks.** New `system/scripts/status_checks.py`; `check(draft, facts, length, audience)` returns a list of small notes, never blocking:
   - the headline is under about 30 words and names a position;
   - no item IDs;
   - at least one date or number where the facts had them;
   - a pending ask in the facts is mentioned;
   - nothing over the length chosen;
   - no claim without a source (every `SOURCES:` entry exists in the facts).

   A failed check reads plainly ("No ask mentioned, but 2 items are waiting on others").
4. **Settings.** A `status` block in `settings-defaults.json` and this repo's `settings.json`: `headline_max_words` (30), `max_risks` (2), `max_overdue_named` (3), `length_words` (`short` 40, `standard` 150, `fuller` 250). Settings tab shows them if other tunables do (match what is there). An update adds the keys to existing vaults.
5. **Tests.** `dev/tests/test_status_facts.py`: the sheet from fixed sample data ranks as expected; client-safe leaves out what it must; a part with no data is omitted; each check against a canned reply, passing and failing.

### Phase B: wiring (after `sprint-4b` and `sprint-chat-sweep` have merged; bring `main` in first)

6. **Context and prompt.** `report.current_context` puts the facts sheet first ("write from these") and the raw lists after it as reference. The right pane stays read-only as now. `current-state-prompt.md` reads the guide, the facts, the audience and the length. Update the existing `current-context` tests (`test_reports.py`, `test_pages.py`, `test_onedrive_projects.py`), because the output changes on purpose.
7. **The popup and route.** The Generate dialog gains **Audience** and **Length** (remembered like the period; Standard default). `generate` in `live_server.py` validates them (enums) and passes them on. "Drafted from" shows the facts sheet as well as the sources.
8. **Checks under the draft.** A stateless `/api/current/check` route (recomputes the facts; the sheet is deterministic) and small muted notes under the draft in the editor. Never blocking.
9. **Make it executive.** A button beside Generate and `/api/current/rewrite` with its own prompt (`current-state-rewrite-prompt.md`): rewrites the left pane in this voice, keeps Alan's facts, lands as a draft he accepts or discards, and never changes text on its own. A note warns if a date or number from Alan's text is missing from the result.
10. **Tests.** Route validation; the audience changes what is included; the rewrite prompt carries the original text; one headless-Chrome test of the popup, the notes and Make it executive (canned model reply, like `test_current_state_live.py`).

### Phase C: after `sprint-5` has merged

11. **Decisions needed** added to the Asks part (BL-53), with the check that mentions them.
12. **Weekly and client reports.** `cx-weekly-report` and `cx-client-report` read `executive-style.md` and the facts sheet (client report: client audience), so the report and the page agree. Skill text only, plus one `facts` key if `weekly_data` needs it.
13. **Docs.** `dev/BRD.md` (extend FR-62; new FR numbers at the end of the list, renumbered at merge if they clash), `dev/dashboard-spec.md`, a "Executive Current state" section in `dev/BUILD.md`, `system/templates/help.md`, then `python3 dev/tools/build_guides.py`, and a line in `dev/release-notes/1.2.0.md`.

## Acceptance (Alan)

Generate before and after on two or three real projects in the live vault, and Alan reads them. The tests cover everything around the model, not the model's wording.

## Boundaries

- **Owns:** `status_facts.py`, `status_checks.py`, `executive-style.md`, `current-state-prompt.md`, the rewrite prompt, the Generate dialog and the Current state editor's notes and Make it executive button, the `/api/current/*` routes.
- **Don't edit while others run:**
  - **`sprint-4b` owns:** `live_server.py`, `dashboard.html`, `build_dashboard.py`, `sweep.py`, `minutes.py`, `update.py`, `READ_TOOLS` / `DENY_TOOLS` and the assistant prompt (until it merges; hence phase B waits).
  - **`sprint-chat-sweep` owns:** the chat bubble code and a pulse block in `live_server.py`.
  - **`sprint-5` owns:** `schema.sql`, `tracker.py`, `excel_sync.py`, `review.py`, `report.py` and parts of `dashboard.html` (phase A adds one thin command to `report.py` in a marked block; nothing else there).
- **Shared files:** new code in a marked section (`/* ===== Executive Current state (BL-106) ===== */`); don't reformat unrelated lines; leave `BACKLOG.md` and `BRD.md` alone until phase C.
- **Not changing:** approval before any save, the sources list after the draft, images kept where placed, British English, DD-MM-YYYY, and that Generate never calls Microsoft 365.
- **Development guard:** sample data only; temporary vaults in tests.

## Done when

Tests as listed per item; the full suite passes (`python3 dev/tools/run_tests.py`, two clean runs, on a quiet machine); docs updated; each item committed separately on `sprint-exec-state` with the attribution lines. Never push or merge into `main`.

## Hand-offs

(Changes needed in files another sprint owns.)

- **Debug log stage B:** `status_facts.py` is a script with a command line (`facts CODE`), so it joins stage B's list of entry points to wire. `status_checks.py` is a library only.
- **Test vault script list:** `dev/tests/test_tracker.py`'s `make_vault` list gained `status_facts.py` and `status_checks.py` (one line). Expect a trivial clash if another sprint adds a script to the same line; keep both.
- **Wiring done in `live_server.py` (phase B):** `generate` passes `--audience` and `--length` to `report.py current-context` (validated against `internal`/`client` and the `status.length_words` keys); the prompt template and its placeholders (`code name start end context note`) are unchanged, so the route works as it is. `/api/current/check` calls `status_checks.check(...)`; `/api/current/rewrite` runs `status_prompt.rewrite_prompt(...)` through `Run` and the page then calls `status_checks.kept(original, rewrite)`; the page splits a reply as `status_prompt.split_reply` does.
- **A fix that `main` needs too:** BL-109 (chat-sweep) declared a second `mdInline` and `mdBlocks` in `dashboard.html`, which replaced the Current state editor's, so the project page could not draw its Current state (`mdBlocks(...).map is not a function`). Commit `71896c4` on this branch renames the chat's pair `chatMdInline` and `chatMdBlocks` inside their own block. It is a separate commit so `main` can cherry-pick it.
- **`report.py`:** `current_context` gained `audience` and `length` (and the `style_guide()` helper) and a `--audience` / `--length` option; plus one marked `facts` command and its usage line, nothing else (Sprint 5 owns the file).
