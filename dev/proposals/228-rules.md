# 228 B: wording for system/creaite-rules.md (Jarvis to add; guarded file, not edited here)

1. In the Folder map, in the `projects/<CODE> <Name>/` row (or the project memory description), add:

   "A project's `CLAUDE.md` may carry `- **Partners:** Org A; Org B` (#228 B: the project's partner organisations, split on `;`, at most 12; one report logo each; read by `build_dashboard.partners_of`, edited in the project settings page)."

2. Where the report logos are described (`system/branding/logos/`, local only, never in git), use:

   "Logos live in `system/branding/logos/`: `firm.<ext>`, `<CODE>-client.<ext>` and, for each partner, `<CODE>-partner-<slug>.<ext>` (slug = the partner's name in lower case, letters and digits joined by hyphens, at most 40). The older `<CODE>-partner.<ext>` is still read as the first partner's logo until that partner has a file of its own. In a layout or the memory line `Client report logos:` the kinds are `firm`, `client`, `partner:<slug>`; a bare `partner` means every partner, and a missing line means all. Removing a partner from the line deletes no file. A partner's name reaches a client only as its logo picture."
