# Rules-file size budget (measured 26-10-2026)

## (a) What `dev/tests/test_rules_retained_338.py::test_the_rules_are_at_least_half_smaller` checks
- **slim** = the tree's `system/creaite-rules.md` (UTF-8 bytes), with the 347 and 339 wording kept on both sides and, on v2610-main, the #250 bullet taken out.
- **original** = not a file on disk: `states()` works it out by reversing `dev/proposals/338/creaite-rules.diff` (or `creaite-rules.after-chain.diff`) on the slim tree, i.e. the pre-slimming file (origin/v262-line, plus the same 347/339 wording). It is 66,383 bytes.
- **Limit:** `len(slim) <= 0.5 * len(original)`. margin = 0.5 * original - slim.
- **Consequence:** a sentence that appears in the tree appears in the reversed original too, so adding X bytes of rules raises slim by X and half-original by X/2: **the margin falls by X/2**. So "74.5 bytes of margin" = "149 bytes of new rules text" (Banner's figure and mine agree; they are the same number in two units).

## (b)-(d) Figures (bytes)
| Tree | file | slim | half-original | margin | test |
|---|---|---|---|---|---|
| origin/main a62fbb0a | 33,117 | 33,117 | 33,191.5 | **+74.5** | pass |
| v2610-main + G4 rev 2 | 33,743 | 33,117 (bullet stripped) | 33,191.5 | **+74.5** | pass |
| a62fbb0a + patch 07 alone (775 bytes) | 33,892 | 33,892 | 33,579.0 | **-313.0** | FAIL (only this test) |
| v2610-main + G4 rev 2 + 07 | 34,518 | 33,892 | 33,579.0 | **-313.0** | FAIL (same) |

- The #250 bullet is stripped by exact text: `insert_250()` = the added line of `creaite-rules-250.diff`, found and removed with `str.replace(bullet + "\n", "", 1)` on both sides (and detected in the tree by `MARK_250`). Anything else, including 07, is **counted**. So G4 costs nothing; 07 costs 775/2 = 387.5 of the 74.5 margin and is 313 bytes over; as text it must shrink from 775 to at most 149 bytes (775 - 626).
- 07 sits in Non-negotiables, which the test pins "byte for byte as in the original": that check still passes, because the reversed original keeps the same added bullet. No fixture is needed for correctness; only the size gate fails.
- On origin/main's own copy of the test (no 250 handling) G4 cannot be applied at all (`no 338 diff reverses`): the 250-aware test is already on v2610-main.

## (e) Options if 07 does not fit
1. **Teach the test (exempt 07 like 250).** Add `RULES_132` / `MARK_132` / `without_132` beside the 250 helpers and subtract it in `strip`, `restore` and the half-size line (about 12 ordinary-test lines). Legitimate in the sense of precedent, but it loosens the #338 gate by 775 bytes; the sentences are already pinned (a deleted sentence is caught by the fixtures only if they are listed; 07's are not listed, so also add them to `FAMILIES['Non-negotiables']`). Alan's decision: each exemption is a permanent size increase.
2. **Shorten 07 and move the detail to `system/templates/creaite-reference.md`** (the rules keep a short rule, the reference keeps the mechanism, as #338 does elsewhere). Tried in a throwaway on a62fbb0a with the real test:

   | Text | bytes | margin | test |
   |---|---|---|---|
   | 07 as is | 775 | -313.0 | FAIL |
   | A: Claude default and only recipient of confidential material; only AI on selected text may use another provider, which never receives it; key only in the keychain, never in a run or a file; detail: reference | 266 | -58.5 | FAIL |
   | B: "Only Claude receives confidential material; another provider serves only AI on selected text, and its key stays in the keychain, never in a run." | 169 | -10.0 | FAIL |
   | **C:** `- **AI models (#132).** Confidential material goes only to Claude; any other provider only for AI on selected text; keys stay in the keychain.` | 143 | **+3.0** | **pass** |

   C is probably the 144-byte version Banner has. It leaves 3 bytes for the whole of 2.7.0.
3. **Trim elsewhere.** I deleted every sentence of 60+ bytes, one at a time, and ran the retained-rules test: only **two** are not pinned: "Claude reads minutes, transcripts, mail and Teams, and proposes actions, decisions, risks and issues." (101 bytes, margin +125.0 alone) and "`tracker-view.xlsx` is the Excel editing surface, and `dashboard.html` is the web view." (87 bytes, margin +118.0 alone). Both are orientation text in the intro. Together they free about 94 bytes of margin, i.e. room for 188 more bytes of rules. Every other candidate fails the test (the Prep/one-off-Word/CLI clauses I tried earlier included).

## Recommendation
Use **C** (143 bytes) in patch 07 and put the full 775-byte text in `creaite-reference.md` under a heading the pointer line names; no test change, 3 bytes left. If 2.7.0 needs more rules text than that, Alan decides between exempting it in the test (option 1) and dropping the two intro sentences (option 3, about 188 bytes). Do not exempt by default: the gate is what keeps the rules file half its old size.
