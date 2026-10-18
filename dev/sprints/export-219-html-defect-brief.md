# Brief: #219 defect, the weekly report's HTML export loses its formatting and structure

Product Manager, 18-10-2026, for Team Stark. This is the user-facing defect that #226 fixes. It closes when #226's checks 1 to 9 pass for HTML.

**What Alan saw (his screenshot of an exported file):** the report comes out as a plain document: the health flag and six-week strip are gone (only "Off track" and the reason remain as a bare heading and paragraph); a stray second "Weekly report" heading sits under the title block; At a glance is four loose boxes; Milestones is a bulleted list with no timeline and no table; Summary is an empty heading; headings look like body text with a rule.

**What the user must see:** the exported HTML opened on its own looks like "Show as exported" for the whole report. **Done when:** the acceptance checks in `export-226-html-pdf-brief.md` pass, and the demo report's exported HTML is compared with the on-screen exported view section by section with nothing lost; a part the user left out stays out.

**Test:** scriptable (the file's structure and text per section, plus a Chrome render compared with "Show as exported"); the look on the screenshot sheet.
