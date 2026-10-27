# #386 slice 3: notes for the release notes

## Stated limits

- Project stakeholders are not added as people when the people register moves into the tracker; the People page still shows them.
- "A group can't own as a person" is not enforced yet: a group is marked, nothing more.
- Activity shows a person's changes by their number, not their name.

## How the move happens

- Only when Alan starts it, from Health ("Move people into the tracker"): it shows how many people would move first, takes a
  backup, and is one save that Undo reverses. An update never starts it.
