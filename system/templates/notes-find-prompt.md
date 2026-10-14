Find updates in one of Alan's notes (creaite, BL-301 E). You have no tools: everything you need is below. Reply with one JSON object only, `{{"rows": [ … ]}}`, in a ```json block, and nothing else.

Project: {name}. Today: {today}. The note: "{title}"{when}.

Below are the note's lines that are new or changed since the last Find updates, each with its number `[p<n>]`. For each line, propose the tracker changes it states, or nothing. Most lines of a note are thinking, not changes: leave them out (a line can give several rows). Never invent a fact, an owner or a date a line doesn't give or clearly imply. Turn relative dates ("Tuesday", "before 20-10", "next week") into YYYY-MM-DD from today; "before <date>" means the working day before it. Write titles as a clear action with a verb ("Book a 30-minute review of the paper with Sara"), never as the note's shorthand. Use full names from the people register when a line names someone.

The rows, one JSON object each, every one with `"p"` (the line's number):
- `{{"p": 2, "kind": "action", "title": "…", "owner": "…", "due": "YYYY-MM-DD", "priority": "Urgent|High|Medium|Low", "milestone": "<a milestone ID, optional>", "why": "<how a date or owner was read, optional>"}}`: a new action.
- `{{"p": 5, "kind": "risk" | "issue" | "assumption" | "dependency", "title": "…", "owner": "…", "impact": "High|Medium|Low", "likelihood": "High|Medium|Low", "related": "<an existing item ID, optional>"}}`: a new RAID item.
- `{{"p": 7, "kind": "decision", "title": "…", "made_by": "…", "status": "Made" | "Pending", "needed_by": "YYYY-MM-DD"}}`: a decision made, or one needed.
- `{{"p": 1, "kind": "update", "id": "<an open item's ID>", "set": {{"due_date" | "status" | "owner" | "latest_update" | "response_action": "…"}}, "why": "…"}}`: a change to an open item listed below.
- `{{"p": 3, "kind": "done", "id": "<an open item's ID>", "strength": "Looks done" | "Maybe done", "quote": "<the line's own words that say so>"}}`: an open item the line says is finished.
- `{{"p": 4, "kind": "milestone", "id": "<a milestone ID>", "forecast_date": "YYYY-MM-DD", "why": "…"}}`: a milestone's forecast date moving.
- `{{"p": 8, "kind": "health", "health": "On track" | "At risk" | "Off track", "reason": "…"}}`: the project's health changing.
- `{{"p": 6, "kind": "person", "name": "…", "role": "…", "org": "…"}}`: someone not yet in the people register.
- `{{"p": 6, "kind": "memory", "section": "People", "line": "<one sentence>"}}`: a lasting fact about the project (who reports to whom, how the client works) for its memory.
- `{{"p": 9, "kind": "project", "set": {{"sponsor" | "phase": "…"}}}}`: a project detail changing.

Rules:
- Use only the IDs listed below. A change to anything not listed is a new item, never an update.
- A hedged line ("probably", "might", "to confirm") still gives its milestone or health row, and also an action to confirm it, with `"milestone"` set to the milestone's ID when there is one. creaite leaves the hedged row unticked.
- Never quote more than the few words a `done` row needs.

--- THE PROJECT ---
{context}
--- THE LINES ---
{lines}
