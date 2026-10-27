# #199: the LOW test gaps (Team Cap, landed on the 2.6.10 line)

Five test-only commits (#362, #358, #341 twice, #343), replayed from `team-cap-199-gaps` (64686e0f). No production or guarded file changed. Reviewed by Stark: all five files pass, every new assertion fails under a mutant of the production code, and the merge onto the 2.6.10 line is clean.

Notes from the review, logged and left as they are:

- The People table test at 900 px checks that the computed font starts with "Arial". That reads the CSS string, so on a machine with no Arial-width font it would measure the fallback instead. Arial leaves about 18.7 px of room; a font as wide as Verdana is about 4 px over.
- The "Nothing flagged" test calls `evidence()` on a made-up project, so it checks the function, not that the page calls it in that mode. The existing checks cover the page.
- Two People table mutants (the Organisation column's minimum width and the cell padding) are caught by neither test, because those rules have no effect at 900 px.
- "check my mail for abc" is now listed twice in `PHRASES`. Harmless.
