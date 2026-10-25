# Guarded patches for 2.6.7: one page for Alan (#347 and #339)

Written 25-10-2026 by the architect (Wanda) from v267-line 048baa0c. Read-only review: all eight patches were applied in sequence on a throwaway copy and the tests run there. Nothing is applied in the tree.

## Recommendation
**Approve the two rules wordings (below) and the chain order, but not `calendar-route.diff` as it stands: it makes `check.py` red** (complexity of `Handler.ask` 19 and `queue_start` 16, limit 15) **and has one routing flaw**. Ask Stark to re-cut it (fix below); the other seven are fine to apply. Everything else composes.

## What you get
- **#347:** say **check my mail**, **save**, **undo last save** (the old words keep working). "save" counts as apply only as the whole message, after a shown list, with an echo of what is being saved (all three skills say the same).
- **#339:** typing **refresh calendar** starts the small calendar run (as the Calendar import button does), and a **sweep** reads the vault and the projects folder, not the home folder; the sweep prompts also carry the "never say who is followed" rule.

## Do they compose? Yes
- All eight apply in the order below on v267-line with no conflict. The four `live_server.py` diffs apply in **every one of the 24 orders** and reverse cleanly; the two rules diffs go in either order.
- Tests on the combined tree (all pass): `test_panel_sweep` 10, `test_chat_and_sweep` 36, `test_lighter_runs_339` 22 (its two GUARDED skips become live once landed), `test_guarded_chain` 113, `test_ai_budget_gate_334` 22, `test_v265_plain_words` 8, `test_calendar_refresh` 24, `test_reach` 18, `test_ask_confirmed_apply` 6, `test_ask_tiers` 20, `test_vip_private` 12, `test_plain_words`, `test_no_real_names`, `test_rules_pointers_338`, `test_guard_pinned`.
- **One test failed and is fixed on this branch:** `test_rules_retained_338` stopped at "no 338 diff reverses on them" once the 339 rules sentence was in. It now strips the 347 and 339 wording, works out the 338 state, and puts the wording back (the same method as for 347, with a test that checks the stand-in against the real diff). It passes with none, either or both rules diffs applied, in either order.

## Does the combined rules text keep every never-sentence? Yes
The 347 diff changes two table cells (trigger words only). The 339 diff inserts one sentence into the "What ask creaite may touch" bullet and removes nothing: no "never" clause is lost or added (checked clause by clause, and by `test_rules_retained_338`). **Wording to change on approval:** the inserted sentence begins "**#339 (Alan's decision pending):**"; drop the bracket when you approve it.

## Does the typed refresh keep BL-267 and BL-309? Yes, and it narrows
A typed "refresh calendar" now runs as the run kind `calendar` under the guard hook's mode `calendar` (five `sweep.py` calendar commands, two input files, the two calendar reads), where before it ran as a sweep in mode `sweep`. So it can do less, not more: record-changing commands (`tracker.py apply`, `undo`, `review.py approve`, `reject`, `propose.py stage`) stay refused, there is no session or chat so no outside-content mark is inherited, and the confirmation is unchanged: `panel_kind` is words only, an image, a confirmed request, over 120 characters or another instruction is a plain chat, and the budget gate and the queue still read "refresh calendar" as a sweep (`panel_sweep` is untouched). Dropping the home folder from a sweep (`sweep-no-home`) can only restrict.

**Flaw to fix in `calendar-route.diff` (queue):** in `queue_start`, a queued "refresh calendar" whose `calendar_run` is refused (calendar unreadable, or a sweep running) falls through to `Run(... sweep=panel_sweep(text))`, so it silently becomes a **full mail and Teams sweep** instead of waiting. Typed live it is refused with a message. Fix: if `calendar_run` returns no run, put the item back and hold the queue (as the `OSError` branch does) instead of falling through.

## Complexity (check.py red)
With only `calendar-route.diff` applied, `check.py` fails: `Handler.ask` 19 and `queue_start` 16 (limit 15). The other seven leave it green. Fix: move the new calendar branch of `Handler.ask` into a helper (`_calendar_start(self, run_id)` returning the response), and the queue's choice of run into a helper (`_queued_run(item, images, session, chat)`); the diff must be re-cut and its pin recomputed.

## Order, chain, marker and pin plan (what you approve)
1. **Guarded chain commit, one commit** whose subject starts "Guarded 2.6.7 chain:" (the convention of 2.6.1 to 2.6.4), applying in this order: `347/live_server.py.diff`, `339/calendar-route.diff` (re-cut), `339/sweep-no-home.diff`, `339/sweep-followed-rule.diff`. These four are the only guarded-file changes (`live_server.py`).
2. **Chain list and pin:** new `dev/proposals/GUARDED-2.6.7.chain` listing the four; in `dev/tests/guarded_chain.py` a fifth spec (marker "Guarded 2.6.7 chain:", `CHAIN5_SHA256` from `python3 dev/tests/guarded_chain.py`, base = the published 2.6.6 release commit), carried through `guarded_touched` as the earlier chains are. The pin is set only on your say, after the re-cut.
3. **Rules commit** (after you approve the exact text below): `347/creaite-rules.md.diff` and `339/creaite-rules.diff`, one commit. The rules file is not on the guarded script list; your approval is the gate.
4. **Ordinary commits:** `347/skills.diff` (four SKILL.md files) and `339/tests-pins.diff` (rewrites the pins in `test_panel_sweep`, `test_calendar_refresh`, `test_ai_budget_gate_334`, `test_mail_check`).
5. **Markers and pins that go live:** `# #347:` in `live_server.py` (then `test_panel_sweep` fails if "save" leaves the list); the skills limit (`test_v265_plain_words` requires "whole message" and the echo in all three skills); the two GUARDED skips in `test_lighter_runs_339` become live checks; `test_rules_retained_338` follows the wording.
6. **Order of work:** 1, 2, 4, 3 (rules last, once approved); run `check.py`, the tests above and `test_guarded_chain` after each.

## Risk, in one line each
Low: 347 (words only; "save" as apply is bounded by the skills wording, and ask creaite is unchanged because BL-267 refuses apply and undo in an unconfirmed run whatever the words). Low: sweep-no-home, sweep-followed-rule (restrict only). Medium until re-cut: calendar-route (the queue fallback and the complexity limit).

## Appendix: the exact diffs
### A. Rules wording for your approval: `dev/proposals/347/creaite-rules.md.diff`
```diff
diff --git a/system/creaite-rules.md b/system/creaite-rules.md
index b9f094b1..2f687016 100644
--- a/system/creaite-rules.md
+++ b/system/creaite-rules.md
@@ -56,10 +56,10 @@ Paths are defined once in `system/scripts/paths.py`; keep this table in step wit
 | Alan says | Skill or action | Status |
 |-----------|-----------------|--------|
 | "process new minutes", "process <file>", "process <meeting>", "re-extract", "note: …" | **cx-minutes**: draft Word minutes and proposed items; filed on approval | Specified |
-| "sweep", "sweep mail", "sweep mail for ABC", "sweep the last 7 days", "sweep the <subject> thread", "refresh calendar" | **cx-sweep**: mail and Teams become proposals; runs at session start when due; skips what `sweep.ignore` (BL-97) matches; records anything a VIP sends (BL-99) as an alert first | Specified |
+| "check my mail", "check my mail for ABC", "sweep", "sweep mail", "sweep mail for ABC", "sweep the last 7 days", "sweep the <subject> thread", "refresh calendar" | **cx-sweep**: mail and Teams become proposals; runs at session start when due; skips what `sweep.ignore` (BL-97) matches; records anything a VIP sends (BL-99) as an alert first | Specified |
 | "prep for the <meeting>", "prep page for the ABC steering" | **cx-prep** (BL-98): one Internal HTML prep page, saved in the Agendas folder | Built |
 | "follow Mia Hale", "mark the follow alerts seen" | **People you follow (BL-99)**: the follow flag in the person's People entry (cx-edit); alerts in `system/staging/vip.json` (`sweep.py vip`), shown at the top of Today | Built |
-| "review", "review ABC", "what's pending", "approve…", "reject…", "apply", "undo last apply", "import excel" | **cx-review**: bulk approval never covers minutes, new decisions or new risks; explicit apply | Specified |
+| "review", "review ABC", "what's pending", "approve…", "reject…", "save", "apply", "undo last save", "undo last apply", "import excel" | **cx-review**: bulk approval never covers minutes, new decisions or new risks; explicit apply | Specified |
 | "mark ABC-A-003 done", "set sweep time to 06:30", "add an action for ABC…", "move ABC go-live to 2026-11-20", "add to ABC memory…", "add project DEF…", "close project ABC", "archive project ABC", "restore project ABC", "change project ABC's code to XYZ", "add Sara Khan to the people register" | **cx-edit**: shown before → after, confirmed, written at the next apply | Specified |
 | "weekly report", "weekly report ABC" | **cx-weekly-report**: manual, with a Friday reminder; blocks projects with pending items. Alan's own Claude Code session only: ask creaite never drafts, stages or writes a report | Specified |
 | "client report ABC" | **cx-client-report**: client-safe; its Word, HTML and PDF files are made only from its checked copy (`client_snapshot.client_export`, #239); a partner's name reaches a client only as its logo picture; risks, issues and decisions appear only if flagged client-visible. Never sends. An email about it follows the Draft email setting (#183): off, it is copied and pasted; on, the live server puts it in Alan's Outlook Drafts folder for him to check and send. The report is never sent. Manual, with a per-project reminder. Alan's own Claude Code session only: ask creaite never drafts, stages or writes a report | Specified |
```

### B. Rules wording for your approval: `dev/proposals/339/creaite-rules.diff`
```diff
diff --git a/system/creaite-rules.md b/system/creaite-rules.md
index b9f094b..c616774 100644
--- a/system/creaite-rules.md
+++ b/system/creaite-rules.md
@@ -76,7 +76,7 @@ cx-minutes, cx-weekly-report, cx-client-report and cx-steerco are never schedule
 
 - **What it writes:** edits, new items, health with a reason, "Current state", and Approve or Reject are written as proposals to `system/staging/` (`source_run: "dashboard"`, already approved); nothing reaches the database until apply. Settings go straight to `system/config/settings.json` with a backup and a log entry.
 - **Live mode is required** (IT-approved): `system/scripts/run live_server.py` serves the dashboard on `127.0.0.1`; Alan starts it. If it is not reachable, edits still save to staging, while Apply and the assistant wait. **Apply** is from the dashboard, by saying "apply" in Claude Code, or with a pasted copy command.
-- **What ask creaite may touch (BL-141; Alan, 10-10-2026):** `system/scripts/reach.py` decides (ordinary, sensitive or never; `system/scripts/run reach.py never` prints the never list). An ask creaite chat starts with a **guard hook** (`reach.py hook`, run before every tool call, whatever a settings file allows; it fails closed) that refuses the never list (also inside a script's arguments), any direct `Edit` or `Write` outside `system/staging/drafts/` (`system/staging/` in a confirmed request; never a proposal or creaite's staging records), any `Bash` that isn't one creaite script run on its own (and never `permissions.py` or `propose.py setting`), any write of a weekly or client report file or draft (reading reports stays open) and, in a run Alan hasn't confirmed, every command that changes the record (`tracker.py apply`, `undo`, `review.py approve`, `reject`, `propose.py stage` and the rest; BL-267). A run creaite starts itself runs only read commands, and is held away from confidential notes (#60). A request that is only a sweep is recognised by the live server from its words, never by the model, and runs under the `sweep` mode: it may stage (`sweep.py stage`) and still refuses `tracker.py apply`, `undo`, `review.py approve`, `reject`, `propose.py stage` and any direct write outside `system/staging/drafts/`; anything more ("sweep and apply", an image, a confirmed request) is a plain chat (BL-309). Every change goes through `filechange.py` (backed up, logged, undoable).
+- **What ask creaite may touch (BL-141; Alan, 10-10-2026):** `system/scripts/reach.py` decides (ordinary, sensitive or never; `system/scripts/run reach.py never` prints the never list). An ask creaite chat starts with a **guard hook** (`reach.py hook`, run before every tool call, whatever a settings file allows; it fails closed) that refuses the never list (also inside a script's arguments), any direct `Edit` or `Write` outside `system/staging/drafts/` (`system/staging/` in a confirmed request; never a proposal or creaite's staging records), any `Bash` that isn't one creaite script run on its own (and never `permissions.py` or `propose.py setting`), any write of a weekly or client report file or draft (reading reports stays open) and, in a run Alan hasn't confirmed, every command that changes the record (`tracker.py apply`, `undo`, `review.py approve`, `reject`, `propose.py stage` and the rest; BL-267). A run creaite starts itself runs only read commands, and is held away from confidential notes (#60). A request that is only a sweep is recognised by the live server from its words, never by the model, and runs under the `sweep` mode: it may stage (`sweep.py stage`) and still refuses `tracker.py apply`, `undo`, `review.py approve`, `reject`, `propose.py stage` and any direct write outside `system/staging/drafts/`; anything more ("sweep and apply", an image, a confirmed request) is a plain chat (BL-309). **#339 (Alan's decision pending):** a typed "refresh calendar" starts the small calendar run, as the Calendar import button does (its own tools and two input files, no chat, no session, mode `calendar`; its closure is kept in the day's "Runs creaite started"), and a sweep run reads the vault and the projects folder, not the home folder. Every change goes through `filechange.py` (backed up, logged, undoable).
 - **Marked runs and the one card (BL-141):** a run that reads outside content (Microsoft 365 reading tools, web tools, `inbox/`, transcripts, documents, a file outside the vault) is marked in `system/guard/run.json`. **A note is not outside content (BL-301; Alan, 15-10-2026):** reading one of Alan's notes, a `.md` file directly in a project's or the portfolio's notes folder, marks nothing; a note's pictures (`_images/`), a file in a subfolder of the notes folder and everything else in OneDrive still mark. A sensitive change is refused by `filechange.py` with "Needs approval" and shown on **one card** when the run ends; Approve issues the one-time approval (`reach.APPROVALS`), which nothing the model can read or run holds.
 - **Permission files (BL-141):** `.claude/settings.json`, `.claude/settings.local.json`, `~/.claude/settings.json`, `system/config/settings.json` and the other configuration files are changed on approval: the exact content shown, checked before writing and again after (`permissions.settings_problem`), put back if it fails, logged and undoable.
 - **Editors and notes (BL-301):** AI on selected text only offers a suggestion, which changes nothing until Alan accepts it, and runs Claude with no tools. Apply from **Find updates** writes the ticked rows as approved proposals in one apply, which Undo reverses. A note marked confidential is left out of Prep pages and asks once before its text goes to Claude; its items are marked sensitive.
```

### C. `dev/proposals/347/live_server.py.diff`
```diff
diff --git a/system/scripts/live_server.py b/system/scripts/live_server.py
index 1d0867e6..5e474103 100644
--- a/system/scripts/live_server.py
+++ b/system/scripts/live_server.py
@@ -2323,7 +2323,8 @@ PANEL_SWEEP_WORDS = re.compile(
 # capitals or holds a digit; a short lower-case one (abc) is accepted unless it is a common word; anything else is a plain chat.
 PANEL_SWEEP_FOR = re.compile(r"\bfor ([a-z][a-z0-9]{2,6})\b", re.I)
 PANEL_SWEEP_COMMON = frozenset({"the", "all", "any", "now", "you", "one", "two", "new", "day", "mail", "me", "my"})
-PANEL_SWEEP_NOT = re.compile(r"\b(?:and|then|also|plus|apply|approve|reject|undo|stage|confirm|delete|send|close)\b", re.I)
+# #347: "save" is a second instruction too (Alan's plain word for apply); a thread subject may not carry it
+PANEL_SWEEP_NOT = re.compile(r"\b(?:and|then|also|plus|apply|save|approve|reject|undo|stage|confirm|delete|send|close)\b", re.I)
 
 
 def panel_sweep_code_ok(code):
```

### D. `dev/proposals/339/calendar-route.diff`
```diff
diff --git a/system/scripts/live_server.py b/system/scripts/live_server.py
index 1d0867e..ab6ae50 100644
--- a/system/scripts/live_server.py
+++ b/system/scripts/live_server.py
@@ -1658,6 +1658,15 @@ class Handler(BaseHTTPRequestHandler):
             if busy and not busy.done:
                 return self.send(409, {"ok": False, "busy": True, "run": busy.summary(),
                                        "message": "ask creaite is still working on the last request."})
+            if panel_kind(message, images, req.get("confirmed")) == "calendar":     # #339 A: the busy check above is the 409 for a run
+                try:
+                    run, said = calendar_run(run_id)
+                except OSError as e:
+                    return self.send(200, {"ok": False, "message": f"Couldn't start Claude Code ({e})."})
+                if said:                                                    # a sweep running (409), or the precheck's own reason (400)
+                    return self.send(409 if said == SWEEP_RUNNING_SAYS else 400, {"ok": False, "message": said,
+                                                                                  "busy": said == SWEEP_RUNNING_SAYS})
+                return self.follow(run, numbered=self.numbered())
             try:
                 sweep = panel_sweep(message, images, req.get("confirmed"))      # BL-309: the server decides, from the words
                 run = Run(run_id, message, req.get("session"), req.get("chat"), req.get("confirmed"), images=images, sweep=sweep,
@@ -2346,6 +2355,35 @@ def panel_sweep(message, images=(), confirmed=None):
     return m.group("subject") is not None or all(panel_sweep_code_ok(c) for c in PANEL_SWEEP_FOR.findall(text))
 
 
+PANEL_CALENDAR_WORDS = re.compile(r"(?:please )?refresh (?:the |my )?calendar(?: now)?(?: please)?[.!]?", re.I)
+SWEEP_RUNNING_SAYS = "A mail check is running; try again when it ends."
+
+
+def panel_kind(message, images=(), confirmed=None):
+    """#339 A: the small run a panel request starts, for routing only: "calendar" for a typed "refresh calendar", "sweep" for any
+    other plain sweep, else None. panel_sweep stays as it is (the budget gate and the queue still read "refresh calendar" as a
+    sweep); this adds no exemption. Words only, never the model: the same exclusions as panel_sweep (an image, a confirmed
+    request, over 120 characters, another instruction), and a kind or mode in the request is never read."""
+    if not panel_sweep(message, images, confirmed):
+        return None
+    text = " ".join(str(message or "").split())
+    return "calendar" if PANEL_CALENDAR_WORDS.fullmatch(text) else "sweep"
+
+
+def calendar_run(run_id):
+    """#339 A: a typed "refresh calendar" as the button's own run: its fixed prompt, no session and no chat (so nothing is carried
+    from a chat and no outside-content mark is inherited), kind "calendar", its closure kept in the day's runs chat (BL-326).
+    Returns (the Run, None), or (None, the plain sentence to show) for a sweep running or a calendar that cannot be read."""
+    import calendar_refresh
+    if sweep_running():
+        return None, SWEEP_RUNNING_SAYS
+    why = calendar_refresh.precheck()
+    if why:
+        return None, why
+    return Run(run_id, calendar_refresh.build_prompt(), None, None, None, kind="calendar", label=calendar_refresh.label(),
+               closer=calendar_refresh.closer(), lines=calendar_refresh.lines()), None
+
+
 PANEL_SWEEP_PROMPT = (
     "You are running creaite's cx-sweep from the dashboard panel (ask creaite), headless in the vault: Alan typed a sweep "
     "request, and typing it is his confirmation to stage its proposals (BL-309). Run the cx-sweep skill now for exactly what he "
@@ -3345,8 +3383,9 @@ def queue_start(q, prev=None):
         chat = q["chat"] or (prev.chat or prev.session if mine else None)
         session = prev.session if mine and chat in (prev.chat, prev.session) else chat_session(chat)
         try:
-            nxt = Run(f"r-{secrets.token_hex(6)}", item["text"], session, chat, None, images=images,
-                      sweep=panel_sweep(item["text"], images), fresh=True)                             # BL-309: a queued sweep too
+            nxt = calendar_run(f"c-{secrets.token_hex(6)}")[0] if panel_kind(item["text"], images) == "calendar" else None   # #339 A
+            nxt = nxt or Run(f"r-{secrets.token_hex(6)}", item["text"], session, chat, None, images=images,
+                             sweep=panel_sweep(item["text"], images), fresh=True)                      # BL-309: a queued sweep too
         except (OSError, ValueError):
             q["items"].insert(0, item)
             q["held"] = True
```

### E. `dev/proposals/339/sweep-no-home.diff`
```diff
diff --git a/system/scripts/live_server.py b/system/scripts/live_server.py
index 1d0867e..0f400c5 100644
--- a/system/scripts/live_server.py
+++ b/system/scripts/live_server.py
@@ -2592,10 +2592,10 @@ def guard_args(run_id, mode, held, session, files=None, as_minutes=None):
 
 def run_dirs(policy, guarded):
     """A run's --add-dir folders: none for a tool-less run; the home folder too for a guarded chat or sweep (BL-141); the
-    projects folder only otherwise (#264: a Process run too)."""
+    projects folder only otherwise (#264: a Process run too). #339 A: a sweep needs only the vault and the projects folder."""
     if policy in TOOLLESS_KINDS or policy == "calendar":       # #265: the calendar refresh reads no project file
         return []
-    return reach_dirs() if guarded and policy not in ("process", "reextract") else extra_dirs()
+    return reach_dirs() if guarded and policy not in ("process", "reextract", "sweep") else extra_dirs()
 
 
 def budget_gate(req):
```

### F. `dev/proposals/339/sweep-followed-rule.diff`
```diff
diff --git a/system/scripts/live_server.py b/system/scripts/live_server.py
index 1d0867e..3efca03 100644
--- a/system/scripts/live_server.py
+++ b/system/scripts/live_server.py
@@ -2245,7 +2245,8 @@ KIND_PROMPTS = {"sweep": (
     "exactly as the skill says. It only stages proposals for Review: never apply, approve, reject or undo anything, never "
     "change a project file, and never act in Microsoft 365 (no sending, deleting or changing anything). Alan started it, so no "
     "CONFIRM line is needed. Run each creaite script on its own, exactly `system/scripts/run <name>.py …`; write any input file "
-    "with the Write tool in system/staging/drafts/ first. Never quote a message's text. End with the sweep's one-line summary.")}
+    "with the Write tool in system/staging/drafts/ first. Never quote a message's text. End with the sweep's one-line summary."
+    + VIP_PRIVATE_RULE)}
 # ===== #264: Intake's Process, its own guarded run kind =====
 # Pressing Process in Intake (POST /api/intake/process) starts the kind "process" under the guard hook's mode "process" (reach.py
 # process_gate): it may read, draft the minutes and stage them for exactly the Intake files the server checked; it never applies,
@@ -2353,7 +2354,7 @@ PANEL_SWEEP_PROMPT = (
     "undo anything, never run propose.py stage, never change a project file, and never act in Microsoft 365 (no sending, "
     "deleting or changing anything). No CONFIRM line is needed. Run each creaite script on its own, exactly "
     "`system/scripts/run <name>.py …`; write any input file with the Write tool in system/staging/drafts/ first. Never quote a "
-    "message's text. End with the sweep's one-line summary and \"n items staged for Review\".")
+    "message's text. End with the sweep's one-line summary and \"n items staged for Review\"." + VIP_PRIVATE_RULE)
 PANEL_SWEEP_STEP = "Sweeping (stages proposals only)"
 # ===== end BL-309 =====
 # The file writers are denied by name too: an empty allow list doesn't stop the vault's .claude/settings.json allow rules (Edit
```

The skills diff (`347/skills.diff`, 97 lines) and the test pins (`339/tests-pins.diff`) are in their folders; they are ordinary reviews, not your approval.
