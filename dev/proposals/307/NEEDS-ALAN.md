# #307 piece (7)/(8): what only Alan can check

## Path 30: Check again (calendar row)

Needs real Microsoft 365, so it was not tried here. Cap's audit: pressing Check again shows no toast and no row note; the outcome
("The meeting's calendar event couldn't be read, so nothing was loaded.") appears only in ask creaite's log. Nothing was changed
for it in this piece.

To test, with a real Teams meeting that has ended and has no transcript yet:

1. Open Intake, find the meeting's row (waiting for its transcript) and press Check again.
2. Watch the row and the foot of the page. Expected after the fix to come: the row says what was found (for example "No transcript
   yet" or "Transcript found") and the row's button changes to Process when a transcript was found.
3. Repeat with a meeting whose event can't be read (an old or cancelled one): the row should say so in plain words, not stay silent.
4. Write down what the row said (or that it said nothing).

## Add files in the Chrome app window

Cap could not prove the native file picker draws in the app window (`launch.py --app=`). In the app window press the arrow beside
Process all ready: the Finder-style picker should open. Then choose one good file and one .xlsx: the page should add the good one,
show the toast, and keep a note under the toolbar that names the .xlsx and says why, until you press Dismiss.
