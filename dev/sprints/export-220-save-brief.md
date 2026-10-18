# Brief: #220 defect, exports do not save to disk, and nothing says where a file went

Product Manager, 18-10-2026, for Team Stark. Hub mockup (locked, c6f549ed) shows the dialog and message: dev/mockups/reporting-hub-mockup.html (Export to HTML in the foot bar).

**What Alan saw:** choosing HTML opens the page in the browser, and PDF opens in the PDF viewer; he cannot tell a file was saved or where. From the code (not run): the Export menu calls `exportWeekly`, and the only message is a short toast, "Exported: <file name>", with no folder; Team Stark to confirm whether the file reaches the project's Reports folder.

## What the user must see

1. **The file is saved first**, into the project's Reports folder (the engagement's reports folder, as the filed report is), with the report's name and date (for example "2026-10-16 Weekly report <project>.html"), for HTML, Word and PDF alike. Opening is a separate choice.
2. **A message that says where:** "Saved <file name> in <project> › Reports", where "<project> › Reports" is a **link that opens that folder**, plus two actions: **Show in Finder** and **Open**.
3. **If a file with that name is already there, the user is asked** (a dialog, as in the mockup): **Add a number** (the default; the next free number, "(2)"), **Rename it** (a field the full width of the dialog that shows the whole name, prefilled), or **Overwrite the existing file** (the earlier file is backed up first, as for any file change). Nothing is overwritten without that choice; Cancel saves nothing.
4. **A failed save says so plainly** (why, and that nothing was written), not "Not exported".
5. Same for the internal and the client report, and for each of the three formats. Writes go through the file-change route (`filechange.py`): backed up, logged, undoable. Messages are in British English, with dates as DD-MM-YYYY.

**Alan's ruling (18-10-2026): the HTML export uses the plain name too** (no "(read only)" in it), the same as Word and PDF. No filed reports exist yet, so no migration is needed; if the plain name clashes with the filed report, the clash dialog in item 3 handles it.

## Acceptance checks

Each of HTML, Word and PDF leaves a real file in the stated folder with the right name; the toast shows the folder link and both actions work (the Finder window itself is live only); a taken name offers the three choices and each does exactly what it says; Rename shows the whole name; Overwrite keeps a backup; Cancel writes nothing; a failed save (for example a read-only folder) says so.

## Test (standing rule)

Scriptable: 1, 2 (the call and the link target), 3, 4 and 5 in a throwaway vault; live only: Show in Finder's window and the real viewers. Test file named by Team Stark.
