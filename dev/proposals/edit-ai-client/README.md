# edit_ai.py: keeping the client place in v2.2.0 (proposal)

**Status: a proposal for Alan's yes. Nothing here is applied to v220-int or any shared branch.**

## What it is

`edit_ai-client-place.diff` is the exact change that turns the #117 file Alan approved into the `edit_ai.py` on `v220-int`
(bfb741d). It has 13 hunks (+217, −19). Eleven are v2.1.0's own lines, copied unchanged. Two are small adaptations that make the
two pieces fit together. The hunk list, with a reason for each, is at the top of the diff file.

## Why it is needed

The #117 change was approved on `v220-editor-base`, which was cut before v2.1.0 added the client sheet's `client` place (#123) and its
client gate (#127). v2.1.0 shipped with that place. `v220-int` is built from the v2.1.0 tag, so merging #117 into it has to keep the
client place exactly as it shipped. Without it, the client sheet loses its AI bar: the page would ask for a place the server no
longer knows. That would be a regression, not a leak, because the gate fails closed. This merge goes beyond what Alan approved for
#117, so it is put to him as its own proposal.

## The byte check

- **A** is v2.1.0's `edit_ai.py` (tag v2.1.0, 0c21601). **B** is the approved #117 file: `dev/proposals/edit-ai-117/edit_ai-combined.diff`
  applied to `v220-editor-base`. It is byte-identical to `origin/v220-editor-ai`. **C** is `v220-int`'s file. **O** is the common base
  (48c19a8). Its `edit_ai.py` is identical to `v220-editor-base`'s.
- **Verdict:** C = B + v2.1.0's client place and gate + two adaptations, and nothing else.
  - Take the two adaptations out of C. The lines C adds and removes against B are then exactly the lines v2.1.0 adds and removes
    against O: 244 added and 17 removed, as identical multisets.
  - On the same file, the lines C adds and removes against A are exactly the approved #117 lines: 73 added and 17 removed.
  - The diff applied to B gives C byte for byte (`patch` and `git apply --check`).
- **Function by function:** C equals A for everything v2.1.0 added or changed, and C equals B for everything #117 added or changed.
  Five things changed on both sides and are joined in C: `PLACES`, `FORMAT_RULES`, `request`, `context` and `result`.

### What "v2.1.0's client place" includes (O → A, nine commits: b2621e0, aa18028, b601367, 871a7d6, 78d9e2e, c56c15c, f869373, 2a77459, 62593f6)

- **The place:** `PLACES["client"]` (Shorter, Make it executive, Polish, Ask…), `FORMATS["client"]` (markdown), `CLIENT_PLACES` and
  `CLIENT_RULE`.
- **The facts:** `project_facts(code, client)` and `client_ids` give only the client-visible open items that `client_leak.item_problem`
  passes, and no people. `OPEN` is the shared open-status table.
- **The gate:** `client_problems` and `refusal`. The gate's normaliser is `LOOK_ALIKE`, `VIP_LOOSE`, `SHOWN_AS_NOTHING`, `unseen`,
  `normal`, `loose_ids` and `in_tracker`. The gate covers items, internal wording, the internal health reason, internal-only markers,
  unnamed people, VIP, and link addresses (#127).
- **The server binding:** `bound_place`, `document_audience` and `_report_found` (with `DOC_KEYS`, `REPORT_AUDIENCE` and `NOT_CLIENT`).
  `request()` takes the place from these, never from the page, and fails closed.
- **The client checks in `context()` and `result()`:** `context()` refuses unsafe text before it reaches Claude and returns the checked
  `code`. `result()` drops an unsafe suggestion.
- **Elsewhere:** `names()` became `client_leak.named` (#123 review). This also changes the name notes on every place's suggestions.
  That is shipped v2.1.0 behaviour. The module docstring describes the client place.

## The two adaptations (the only lines in neither A nor B)

1. **Hunk 5:** adds `FORMAT_RULES["client"] = _SHEET_MARKDOWN`. #117 keys the format rules by place, where v2.1.0 keyed them by
   format. `_SHEET_MARKDOWN` is byte-identical to v2.1.0's Markdown rule without task items, which is what v2.1.0 gave the client
   place. Without this line, the client ✦ raises KeyError. The approved #117 diff's own comment already says this line belongs here.
2. **Hunk 10:** the #117 spelling sentence is not added for `CLIENT_PLACES`, just as it is not added for the A4 sheet's places. With
   this, the client prompt stays v2.1.0's word for word. The comment is reworded to say so.

## What it does not change

- No option, label, prompt, format rule or check for notes, current, plain, email or line. These stay the approved #117 output.
- The A4 sheet's places (report, minutes and readonly) stay as v2.1.0 shipped them, which is also what #117 approved.
- No other file. `edit-ai.md`, `report.py` and `client_leak.py` are identical in v2.1.0 and `v220-int`.

## How it was verified

- **The byte and multiset checks above.** The scripts are in the scratchpad and were not committed.
- **`dev/tests/test_edit_ai_client_place.py`** (8 tests) checks `v220-int`'s `edit_ai` against a frozen file,
  `dev/tests/snapshots/edit-ai-client-place.json`:
  - every client option's full context (prompt, format, label, people and code), and a report-place request that names the client
    report;
  - the client place's options, format, format rule and client rule;
  - three refusals: no document, internal text in, and another project;
  - three replies: an internal ID, an owner's name, and a safe one;
  - the report and minutes prompts;
  - every option of the #117 places.

  The frozen file is written only from the references: v2.1.0 for the client and sheet places, and `origin/v220-editor-ai` for the
  rest (`CREAITE_UPDATE_SNAPSHOTS=1`). Whenever git can show the references, the test also checks the frozen file against them.
  Breaking either adaptation makes it fail: two failures without the spelling exclusion, and a KeyError without the format rule.
- **The trial merge of `origin/client-gate-127g` (740d954) into `v220-int`** is clean for the whole tree, including `edit_ai.py`.
  127g's two `edit_ai.py` hunks are rounds 5 to 7 of the gate: `unseen`, `unmarked`, `normal`, `loose_ids` and `client_problems`.
  They touch no #117 line and no prompt, and the new test passes on the merged tree.
