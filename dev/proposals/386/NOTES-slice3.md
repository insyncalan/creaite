# #386 slice 3: notes for the release notes

## Stated limits

- Project stakeholders are not added as people when the people register moves into the tracker; the People page still shows them.
- "A group can't own as a person" is not enforced yet: a group is marked, nothing more.
- Activity shows a person's changes by their number, not their name.
- Who you follow and who is hidden are never in the project record or the people register: they stay in the private file on
  this laptop.
- The move stops, changing nothing, when the register holds something it can't carry (another column with values, another section,
  a free note, a row without a name, a label or project you don't have), while a register change waits in Review, and while who you
  follow or hide is still only in the register. It says what to change first.

## How the move happens

- Until the move, people can't be added or changed one by one in the project record: a save that tries is held in Review with
  "run the move first", and nothing is written, so the people register is never replaced before the move.

- Ships together: the change that makes Settings › People and propose.py save people as people items (not as register edits) is in
  the same release as the people table, and lands before anyone moves people. The table never ships without it.

- Only when Alan starts it, from Health ("Move people into the tracker"): it shows how many people would move first, takes a
  backup, and is one save that Undo reverses. An update never starts it.
