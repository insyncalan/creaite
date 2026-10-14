# Project matching

Assign a project to each extracted item, not just to each file. Use the register at `projects/_portfolio/project-register.md`.

## Signal strength

| Strength | Signals | What to do |
|----------|---------|------------|
| Strong | Project folder under `projects/` · Outlook category named after a project code · `[CODE]` in a subject, meeting title or file name · a Teams channel listed in the register | Assign |
| Medium | Stakeholder listed under exactly one project · a sender listed under exactly one project (Senders) · an alias or client name · client or partner email domain · two or more keywords from one project | Assign and mark `(?)` |
| Weak | One keyword · a shared stakeholder · a generic topic | Mark `Project?` |
| Conflict | Strong or medium signals point to different projects | Mark `Project?` and list the candidates |

## Meetings

- Check both the **meeting title** and the **transcript content**.
- If several projects are substantively discussed, the meeting belongs to each of them. Its minutes and transcript are filed in every matched project, and each item is still matched individually.

## Rules
- A strong signal from the item's own wording beats the file's folder. If a note in an ABC meeting says "[DEF] contract slips", the item belongs to DEF.
- Entries under Shared in the register are never a signal on their own.
- **Workstreams (BL-58):** a workstream name, keyword or alias used in more than one project is never evidence for a project; one unique to a project is a weak signal only. Match the project first, then its workstream.
- Retired codes are never assigned; flag the item.
- Match a code as a whole token: `[ORX]` does not match `[ORX2C]`, and `ORX2C-A-001` belongs to `ORX2C`, not `ORX`. Check longer codes first.
- Files in `inbox/` have no folder signal. Propose a project for the whole file. Filing it into the project folder happens only when the proposal is applied, never before approval.
- Files in `projects/_portfolio/` have no default project. Match every item individually.
- A word in a project's **Exclude** column rules that project out for the item, whatever else matches.
- **Record the candidate signals** on every `Project?`, possible or two-project item (`signals` in the proposal, `dev/staging-format.md`): the sender address, the email domain, the Teams channel, an alias or a stakeholder that pointed to a project. Review uses them to offer learning.
- **Learning (BL-28):** when Alan resolves such an item, offer once to remember one concrete signal: `propose.py learn <CODE> <kind> <value> --check`, then, on yes, `propose.py learn <CODE> <kind> <value>` (staged, approved, written at apply; undoable). Never learn a single keyword or Alan's own domain; a signal already used by another project goes under Shared (`--shared`), never into two project rows.
