"""creaite proposal helper — the exact parts of cx-edit (standard library only).

Commands:
  preview <spec.json>        validate a change and print it before → after; writes nothing
  stage <spec.json>          write it as an approved proposal (after Alan confirms) and print the same preview
  new-project --code DEF --name "Digital Enablement" [--sponsor …] [--client …] [--rhythm weekly] [--objective …] [--folder "<engagement folder>"] [--out <name>.json]
                             print the spec for a new project (folders, CLAUDE.md from the template, register row,
                             projects row) to review, then stage. With a projects folder outside the vault (settings
                             `locations`, BL-85) the folder is the engagement's own name (no code), made by copying the
                             skeleton; --folder names an engagement folder that already exists, which is adopted as it is
  close-project <CODE> [--out <name>.json]
                             print the spec to make a project inactive, and list its open items
                             (--out saves a spec in system/staging/drafts/ instead of printing it: no redirect needed)
  recode <OLD> <NEW> [--name "…"] [--folder "…"] [--dry-run]
                             change a project's code (and name) everywhere (BL-111): shows the counts, the new IDs and the files that
                             change, then stages it approved (--dry-run only shows it). --folder names the engagement folder you
                             have already renamed. Applied on its own; "undo last apply" restores it
  setting <dotted.key> <JSON value>
                             change settings.json now (backup in system/backups/, one line in settings-log.jsonl)
  learn <CODE> <kind> <value> [--shared] [--check]
                             remember the signal that decided a project choice (BL-28): kind is sender, domain,
                             channel, alias or stakeholder. Stages the register change, approved (Alan said yes).
                             --check prints whether it can be learnt, as JSON, and stages nothing. --shared moves a
                             signal that already belongs to another project into Shared instead
  fields [<table>]           the fields a spec may use for a table, from schema.sql (BL-249); read only, writes nothing
  register-columns           stage adding the Senders and Exclude columns to the register if it lacks them
  archive <CODE> [--open | --cancel-open] [--out <name>.json]
                             print (or save) the spec that archives a project (BL-09): the folder moved to 99 Archive, the
                             register row to Retired codes, the project and its items marked archived. With open items it
                             stops and lists them, unless --cancel-open (which cancels them all first, in the same proposal);
                             --open prints them as JSON and nothing else
  restore <CODE> [--out <name>.json]
                             print (or save) the spec that restores an archived project: the folder back (a number added if the
                             name is taken), the register row back, its items live again
  old-archives [--out <name>.json]
                             print (or save) the spec that renames each archive folder still called _Archive or zz Archive
                             to 99 Archive (BL-09, #252):
                             a `move` of the apply, so it is shown, approved and undoable; exit 1 when there is none
  people list|resolve|add|edit|rename|merge|map|migrate
                             the people register (BL-55): see "People register" below, or `propose.py people`
  workstreams list [--project X] [--json] | suggest <CODE> <name> | add <CODE> <name> [--lead … --keywords …
                             --aliases … --channel …] | retire-settings
                             each project's workstreams (BL-58): list them; suggest keywords, aliases, lead and channel
                             from the items and sources that mention a name; stage a new one (approved: Alan confirmed);
                             clear the old settings.json lists once tracker.py migrate has moved them into the table

spec.json: {"source_run": "cx-edit", "items": [ {op/table/values|id+changes …} ],
            "file_changes": {"title": "…", "project": "ABC", "file_ops": [{"op": "write", "path": "…", "content": "…"},
                                                                       {"op": "mkdir", "path": "…"}]}}
A write's "previous" is filled from the current file (null for a new file), so undo restores it exactly. Updates
get "based_on" from the tracker, so a change made meanwhile becomes a conflict.
"""
import difflib
import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
import tracker  # noqa: E402

LABELS = {"due_date": "Due", "client_visible": "Client-visible", "client_message": "Client messaging",
          "latest_update": "Latest update", "response_action": "Response", "health_reason": "Health reason",
          "next_milestone": "Next milestone", "milestone_date": "Milestone date", "made_by": "Made by",
          "baseline_date": "Baseline", "forecast_date": "Forecast", "sort_order": "Order",
          "percent_complete": "% complete", "description": "Description",
          "state": "State", "state_set": "State set by you", "state_reason": "State reason", "owner": "Owner",   # BL-186
          "actual_date": "Achieved on", "internal_note": "Internal note"}


def label(field):
    """The label a preview shows for a field."""
    return LABELS.get(field, field.replace("_", " ").capitalize())


def show(field, value):
    """A value as a preview shows it: dates DD-MM-YYYY, empty as a dash."""
    if value is None or value == "":
        return "—"
    return tracker.shown(value) if field in tracker.DATE_FIELDS else str(value)


def complete(spec):
    """Fill based_on for updates and previous for file writes; default decision approved."""
    con = tracker.connect()
    for n, item in enumerate(spec.get("items", []), start=1):
        item.setdefault("n", n)
        item.setdefault("match", "strong")
        item.setdefault("flags", [])
        item.setdefault("decision", "approved")
        if item.get("op") in ("update", "cancel") and "based_on" not in item:
            row = tracker.fetch(con, item["table"], item["id"])
            if row is not None and "updated_at" in row.keys():
                item["based_on"] = row["updated_at"]
    fc = spec.get("file_changes")
    if fc:
        fc.setdefault("file_changes_decision", "approved")
        for op in fc.get("file_ops", []):
            if op.get("op") == "write" and "previous" not in op:
                p = paths.resolve(op["path"])
                op["previous"] = p.read_text(encoding="utf-8") if p.is_file() else None
    spec.setdefault("source_run", "cx-edit")
    spec.setdefault("files", [])
    return spec


def preview_lines(spec):
    """The before → after lines a cx-edit spec would make, one per change, read from the tracker."""
    con = tracker.connect()
    out = []
    for item in spec.get("items", []):
        t, op = item.get("table"), item.get("op")
        if op == "new":
            v = item.get("values") or {}
            head = v.get("description") or v.get("decision") or v.get("name") or v.get("summary") or ""
            out.append(f"New {t.rstrip('s') if t != 'raid' else (v.get('type') or 'RAID item').lower()}: {head}")
            out += [f"    {label(k)}: {show(k, x)}" for k, x in v.items() if k not in ("description", "decision")]
            out += [f"    Note: {n}; a working day is usually meant" for n in tracker.weekend(t, v)]      # BL-181: a note, never a refusal
        elif op == "recode":
            out += recode_lines(con, item)
        elif op in tracker.ARCHIVE_OPS:
            out += archive_lines(item)                                       # BL-09
        else:
            row = tracker.fetch(con, t, item["id"])
            cur = dict(row) if row is not None else {}
            if op == "cancel" and t in ("links", "item_labels", "labels"):          # these rows are removed, not cancelled
                out.append(f"Remove {t.rstrip('s')} {item['id'].replace('|', ' → ') if t != 'labels' else item['id']}")
                continue
            changes = item.get("changes") or ({"status": "Dropped" if t == "promises" else "Cancelled"} if op == "cancel" else {})
            out.append(f"{item['id']} · " + "; ".join(f"{label(k)}: {show(k, cur.get(k))} → {show(k, x)}"
                                                       for k, x in changes.items()))
            out += [f"    Note: {n}; a working day is usually meant" for n in tracker.weekend(t, changes)]   # BL-181
            if t == "milestones" and cur:                                       # BL-186: the dates' view and a rebaseline's decision
                out += milestone_notes(item, cur, changes)
            if t == "projects" and changes.get("health"):                       # BL-52
                ev = health_check(item["id"], changes["health"])
                if ev:
                    out.append(f"    Evidence suggests {ev['suggested']}: {'; '.join(ev['reasons'])}")
    for op in (spec.get("file_changes") or {}).get("file_ops", []):
        out += file_op_lines(op)
    return out


def file_op_lines(op):
    """The preview lines of one file operation: a folder made or moved (BL-09), a file made or changed (its diff)."""
    if op["op"] == "move" and paths.resolve(op["from"], archived=False).is_file():     # BL-03: one report or minutes file
        return [f"Move file {op['from']} → {op['to']}"]
    if op["op"] == "move":                                                      # BL-09: a whole folder
        return [f"Move folder {op['from']}/ → {op['to']}/"]
    if op["op"] == "mkdir":
        return [f"Create folder {op['path']}/"]
    if op["op"] == "write" and op.get("previous") is None:
        return [f"Create {op['path']} ({len(op['content'].splitlines())} lines)"]
    if op["op"] == "write":
        diff = [d for d in difflib.unified_diff(op["previous"].splitlines(), op["content"].splitlines(), lineterm="",
                                                n=0) if not d.startswith(("---", "+++", "@@"))]
        return [f"Change {op['path']}:"] + ([f"    {d}" for d in diff] or ["    (no change)"])
    return []


def milestone_notes(item, cur, changes):
    """BL-186: what the dates suggest when a state is set, and the decision a rebaseline will record."""
    row, out = {**cur, **changes}, []
    if changes.get("state") and changes["state"] != "Achieved":
        sug = tracker.suggested_state(row, (os.environ.get("CREAITE_NOW") or tracker.today())[:10])   # creaite's clock
        if sug != changes["state"]:
            out.append(f"    The dates suggest {sug}" + (" (a better state needs a one-line reason)"
                                                         if tracker.MS_RANK[changes["state"]] < tracker.MS_RANK[sug] else ""))
    if "baseline_date" in changes and cur.get("baseline_date") and changes["baseline_date"] != cur["baseline_date"]:
        rb = item.get("rebaseline") or {}
        who = rb.get("agreed_with")
        who = ", ".join(who) if isinstance(who, list) else who
        out.append(f"    Rebaseline: records a decision (agreed with {who or '?'}; {rb.get('reason') or 'no reason given'}; "
                   f"source {rb.get('source') or '?'})")
    return out


def health_check(code, health):
    """The evidence when a health is better than it suggests (BL-52), else None."""
    import report
    ev = report.health_evidence(code)
    return ev if report.better_than_evidence(health, ev) else None


def check(spec):
    """Validate (a dry run, nothing written); returns the problems."""
    con = tracker.connect()
    problems = tracker.dry_run(con, spec, "cx-edit", only_approved=False)
    for item in spec.get("items", []):        # BL-52: health better than the evidence needs a reason
        ch = item.get("changes") or {}
        if item.get("table") == "projects" and ch.get("health") and health_check(item["id"], ch["health"]) \
                and not (ch.get("health_reason") or "").strip():
            problems[item.get("n")] = ("invalid", "health is better than the evidence suggests; give a health_reason")
    for op in (spec.get("file_changes") or {}).get("file_ops", []):
        try:
            tracker.check_file_op(op, spec["file_changes"])
        except tracker.Invalid as e:
            problems[op.get("path") or op.get("from")] = ("invalid", str(e))
        if op.get("op") == "write" and op.get("previous") is not None:
            current = paths.resolve(op["path"]).read_text(encoding="utf-8")
            if current not in (op["previous"], op.get("content")):    # already as proposed is not a conflict
                problems[op["path"]] = ("invalid", "the file changed since this change was prepared")
    return problems


def people_check_spec(spec):
    """BL-55: owners (and made_by) that match the people register exactly are changed to the full name; others are
    only noted (never guessed or blocked). Returns the lines to show. Does nothing without a register."""
    if not paths.PEOPLE_REGISTER.is_file():
        return []
    people, others = people_pool()
    lines = []
    for item in spec.get("items", []):
        if item.get("table") not in ("actions", "raid", "decisions", "workstreams", "promises"):   # workstreams: the lead (BL-58)
            continue
        notes, unknown = map_owner_fields(item, people, others)
        lines += [f"Person: {n} (from the people register)" for n in notes]
        lines += [f"Person: {person_note(u)} Add them with `propose.py people add`, or choose a registered name."
                  for u in unknown]
    return lines


def cmd_preview(spec_file, write=False):
    """Validate a cx-edit spec and print it before → after. With `write`, stage it as an approved proposal in
    system/staging/ (written at the next apply) and delete the spec draft (BL-118); returns 1 if it is invalid.
    """
    spec = complete(json.loads(Path(spec_file).read_text(encoding="utf-8")))
    people_notes = people_check_spec(spec)                                    # BL-55
    for line in preview_lines(spec):
        print(line)
    for line in people_notes:
        print(line)
    problems = check(spec)
    for where, (kind, reason) in problems.items():
        print(f"Problem ({where}): {kind} — {reason}")
    if any(k == "invalid" for k, _ in problems.values()):
        print("Not staged." if write else "Fix these before staging.")
        return 1
    if not write:
        return 0
    why = server_card_only(spec, spec_file)
    if why:
        print(why)
        return 1
    stamp, out, n = f"{datetime.now():%Y-%m-%d-%H%M%S}", None, 1
    while out is None or out.exists():    # two proposals in one second must not overwrite each other
        out = paths.STAGING / f"proposed-{stamp}{f'-{n}' if n > 1 else ''}-edit.json"
        n += 1
    out.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Staged and approved: {paths.rel(out)}. It'll be written at your next apply.")
    paths.consume_draft(spec_file)                                            # BL-118: the spec has done its job
    return 0


SERVER_CARD_ONLY = {                              # BL-331, #124: staged only from the live server's card (its snapshot in system/guard/)
    "reports_back": "Not staged: an archived file is moved back from Files (Move back) on the approval card, never staged here.",
    "notes": "Not staged: a note is deleted from the Notes tab (Delete note) on the approval card, never staged here.",
    "notes_back": "Not staged: a deleted note is moved back from Files (Move back) on the approval card, never staged here."}


def server_card_only(spec, spec_file):
    """Why this spec can't be staged here (a move only the live server's card stages), or None."""
    why = SERVER_CARD_ONLY.get((spec.get("file_changes") or {}).get("archive"))
    if why and Path(os.path.realpath(spec_file)).parent != Path(os.path.realpath(paths.GUARD)):
        return why
    return None


# ── Projects ──────────────────────────────────────────────────────────────────

def register_codes():
    """Codes in the register's Projects and Retired codes tables."""
    codes = set()
    for line in paths.REGISTER.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.startswith("|") else []
        if cells and re.fullmatch(tracker.CODE_RE, cells[0]):
            codes.add(cells[0])
    return codes


def add_register_row(text, row):
    """Insert a row at the end of the Projects table (before its blank placeholder row, if any)."""
    lines = text.splitlines()
    start = lines.index("## Projects")
    i = start + 1
    while i < len(lines) and not lines[i].startswith("|"):
        i += 1
    while i < len(lines) and lines[i].startswith("|"):
        i += 1
    insert_at = i
    if lines[i - 1].replace("|", "").strip() == "":      # the template's empty row
        insert_at = i - 1
    lines.insert(insert_at, row)
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def folder_ops(folder, adopting=False):
    """The file operations that make a new project's folders. By default: the five subfolders. With a projects folder outside the vault
    (BL-85): a copy of its template skeleton (every folder, and any file in it), or if there is none the mapped folders; nothing at all
    for an engagement folder that already exists (it is adopted as it is). The notes folder (BL-301) is added when the skeleton lacks it."""
    if not paths.external():
        return [{"op": "mkdir", "path": f"{folder}/{sub}"} for sub in paths.PROJECT_SUBFOLDERS]
    if adopting:
        return []
    skeleton = paths.projects_root() / str(paths.locations().get("skeleton") or "_Templates/_Skeleton")
    ops = [{"op": "mkdir", "path": folder}]
    if skeleton.is_dir():
        entries = sorted(skeleton.rglob("*"))
        ops += [{"op": "mkdir", "path": f"{folder}/{p.relative_to(skeleton).as_posix()}"} for p in entries if p.is_dir()]
        ops += [{"op": "copy", "from": paths.rel(p), "to": f"{folder}/{p.relative_to(skeleton).as_posix()}"}
                for p in entries if p.is_file() and not p.name.startswith((".", "~$"))]
    else:
        ops += [{"op": "mkdir", "path": f"{folder}/{paths.folder_name(k)}"}
                for k in ("transcripts", "minutes", "weekly_reports", "client_reports", "adhoc_documents")]
    notes = {"op": "mkdir", "path": f"{folder}/{paths.folder_name('notes')}"}       # BL-301: every new project gets its notes folder
    ops = ops + ([notes] if notes not in ops else [])
    return [skeleton_renamed(op) for op in ops]


def skeleton_renamed(op):
    """BL-09, #252: a folder the skeleton still calls _Archive or zz Archive is made as 99 Archive in the new project (nothing
    else is renamed)."""
    def fix(p):
        """The path with each _Archive or zz Archive part named 99 Archive."""
        return "/".join(paths.ARCHIVE if part in paths.OLD_ARCHIVES else part for part in str(p).split("/"))
    out = dict(op)
    for k in ("path", "to"):
        if k in out:
            out[k] = fix(out[k])
    return out


# ===== BL-09, #252: rename the archive folders still called _Archive or zz Archive (Health's Rename to 99 Archive) =====
def old_archives_spec():
    """The spec that renames each archive folder still called _Archive or zz Archive to 99 Archive in the same place (a `move` of
    the apply), and the folders left as they are: a 99 Archive already beside them, or a second old folder in the same place (the
    _Archive there is renamed first, as it is the one in use): two folders are never merged."""
    ops, kept, taken = [], [], set()
    for f in paths.old_archive_folders():
        new = f.with_name(paths.ARCHIVE)
        if new.exists() or new in taken:
            kept.append(paths.rel(f))
            continue
        taken.add(new)
        ops.append({"op": "move", "from": paths.rel(f), "to": paths.rel(f.parent) + "/" + paths.ARCHIVE})
    n = len(ops)
    spec = {"source_run": "cx-setup", "items": [], "file_changes": {
        "title": f"Rename {n} archive folder{'s' if n != 1 else ''} to {paths.ARCHIVE}", "project": None, "archive": "rename",
        "file_ops": ops}} if ops else None
    return spec, kept


def cmd_old_archives(out=None):
    """Print (or save with --out) the spec that renames every _Archive and zz Archive folder to 99 Archive (BL-09, #252). Nothing
    to do: says so."""
    spec, kept = old_archives_spec()
    for k in kept:
        print(f"Left as it is: {k} (a {paths.ARCHIVE} folder is already beside it; move its contents yourself)", file=sys.stderr)
    if not spec:
        print(f"No archive folder has an old name any more ({' or '.join(paths.OLD_ARCHIVES)}): nothing to rename.",
              file=sys.stderr)
        return 1
    return emit_spec(spec, out)
# ===== end BL-09 =====


def emit_spec(spec, out=None):
    """Print a spec for the caller to review and stage (as before), or, with --out <name>, save it in system/staging/drafts/ and say
    where (so ask creaite, which may not use a redirect, needs no shell to keep it: the file preview and stage read). Only a bare
    file name is taken; it ends .json, never overwrites (a number is added), and stays directly in the drafts folder."""
    text = json.dumps(spec, indent=2, ensure_ascii=False)
    if not out:
        print(text)
        return 0
    name = Path(out).name
    if name != out or name.startswith("."):
        sys.exit("--out takes a file name only (it is saved in system/staging/drafts/), for example --out new-project.json")
    stem = name[:-5] if name.lower().endswith(".json") else name
    paths.DRAFTS.mkdir(parents=True, exist_ok=True)
    target, n = paths.DRAFTS / f"{stem}.json", 1
    while target.exists():
        n += 1
        target = paths.DRAFTS / f"{stem}-{n}.json"
    target.write_text(text + "\n", encoding="utf-8")
    rel = paths.rel(target)
    print(f"Spec saved: {rel}\nPreview it with: python3 system/scripts/propose.py preview {rel}")
    return 0


def cmd_new_project(a):
    """Print (or save with --out) the spec for a new project: its folder, CLAUDE.md from the template, register
    row and projects row. With a projects folder outside the vault (BL-85) the folder is the engagement's name.
    """
    code = a["code"]
    if not re.fullmatch(tracker.CODE_RE, code):
        sys.exit("Project codes are 3 to 7 capital letters or digits, starting with a letter.")
    con = tracker.connect()
    if code in register_codes() or con.execute("SELECT 1 FROM projects WHERE code = ?", (code,)).fetchone():
        sys.exit(f"{code} is already used (including retired codes). Choose another.")
    if paths.external():
        folder_name = re.sub(r"[\\/:*?\"<>|]", " ", a.get("folder") or a["name"]).strip(" .")      # the engagement's own name; no project code
        folder = f"projects/{folder_name}"
    else:
        folder_name = f"{code} {a['name']}"
        folder = f"projects/{folder_name}"
    adopting = paths.external() and (paths.projects_root() / folder_name).is_dir()        # the engagement folder already exists
    memory = (paths.TEMPLATES / "project-CLAUDE-template.md").read_text(encoding="utf-8")
    memory = memory.replace("# <CODE> — <Project name>", f"# {code} — {a['name']}")
    memory = memory.replace("_Last reviewed: YYYY-MM-DD_", f"_Last reviewed: {datetime.now():%Y-%m-%d}_")
    if a.get("objective"):
        memory = memory.replace("- **Objective:** one or two sentences.", f"- **Objective:** {a['objective']}")
    memory = memory.replace("- **Client / partner:**", f"- **Client / partner:** {a.get('client') or ''}".rstrip())
    memory = re.sub(r"(\*\*Client report rhythm:\*\*\s*)\w+", r"\g<1>" + (a.get("rhythm") or "weekly"), memory)
    if a.get("sponsor"):
        memory = memory.replace("|  |  | Sponsor |  |", f"| {a['sponsor']} |  | Sponsor |  |")
    register = paths.REGISTER.read_text(encoding="utf-8")
    register = ensure_columns(register)
    row = f"| {code} | {a['name']} | {folder_name} | {a.get('client') or ''} | " \
          f"{(a['sponsor'] + ' (sponsor)') if a.get('sponsor') else ''} |  |  |  |  |  |"   # … Senders, Exclude
    spec = {"source_run": "cx-edit",
            "items": [{"op": "new", "table": "projects", "values": {"code": code, "name": a["name"],
                                                                   **({"sponsor": a["sponsor"]} if a.get("sponsor") else {})}}],
            "file_changes": {"title": f"New project {code}", "project": code, "file_ops":
                             folder_ops(folder, adopting) +
                             ([] if adopting and (paths.projects_root() / folder_name / "CLAUDE.md").is_file() else
                              [{"op": "write", "path": f"{folder}/CLAUDE.md", "content": memory}]) +
                             [{"op": "write", "path": paths.rel(paths.REGISTER), "content": add_register_row(register, row)}]}}
    return emit_spec(spec, a.get("out"))


# ── Register learning (BL-28) ─────────────────────────────────────────────────

LEARN_COLUMN = {"sender": "Senders", "domain": "Email domains", "channel": "Teams channels",
                "alias": "Aliases / client names", "stakeholder": "Key stakeholders"}
NEW_COLUMNS = ("Senders", "Exclude")


def split_row(line):
    """The cells of one Markdown table row, trimmed."""
    return [c.strip() for c in line.strip().strip("|").split("|")]


def join_row(cells):
    """One Markdown table row from its cells."""
    return "| " + " | ".join(cells) + " |"


def projects_table(lines):
    """(header index, separator index, [row indices]) of the register's Projects table."""
    i = lines.index("## Projects") + 1
    while not lines[i].startswith("|"):
        i += 1
    head, rows_at = i, []
    i += 2
    while i < len(lines) and lines[i].startswith("|"):
        rows_at.append(i)
        i += 1
    return head, head + 1, rows_at


def ensure_columns(text):
    """The register with the Senders and Exclude columns added to the Projects table (if missing)."""
    lines = text.splitlines()
    head, sep, rows_at = projects_table(lines)
    missing = [c for c in NEW_COLUMNS if c not in split_row(lines[head])]
    if not missing:
        return text
    lines[head] = join_row(split_row(lines[head]) + missing)
    lines[sep] = join_row(split_row(lines[sep]) + ["-" * (len(c) + 2) for c in missing])
    for i in rows_at:
        lines[i] = join_row(split_row(lines[i]) + [""] * len(missing))
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def cell_values(cell):
    """A register cell's comma-separated values, lower case, with any (notes) removed."""
    return [re.sub(r"\s*\(.*?\)", "", v).strip().lower() for v in cell.split(",") if v.strip()]


def signal_owners(text, value):
    """Project codes whose register row already holds this value in a signal column; and whether it's in Shared."""
    lines, v = text.splitlines(), value.strip().lower()
    head, _, rows_at = projects_table(lines)
    cols = split_row(lines[head])
    owners = [split_row(lines[i])[0] for i in rows_at
              if any(v in cell_values(c) for name, c in zip(cols, split_row(lines[i])) if name in LEARN_COLUMN.values())]
    shared = any(split_row(ln)[0].strip().lower() == v for ln in lines[lines.index("## Shared (not a signal on their own)") + 1:]
                 if ln.startswith("|")) if "## Shared (not a signal on their own)" in lines else False
    return owners, shared


def own_domains():
    """Alan's own mail domains (settings identity.own_domains), lower case."""
    return [d.lower() for d in (paths.load_settings().get("identity") or {}).get("own_domains", [])]


def learn_check(code, kind, value):
    """Can this signal be learnt for code? {ok, reason, owners, shared, column}."""
    text = paths.REGISTER.read_text(encoding="utf-8")
    owners, shared = signal_owners(ensure_columns(text), value)
    out = {"code": code, "kind": kind, "value": value, "owners": owners, "shared": shared,
           "column": LEARN_COLUMN.get(kind)}
    domain = value.split("@")[-1].lower() if kind in ("sender", "domain") else ""
    if kind == "keyword":
        return {**out, "ok": False, "reason": "a single keyword is a weak signal; it isn't learnt"}
    if kind not in LEARN_COLUMN:
        return {**out, "ok": False, "reason": f"unknown kind {kind!r}"}
    if domain and domain in own_domains():
        return {**out, "ok": False, "reason": f"{domain} is your own company's domain; it's never a project signal"}
    if code in owners:
        return {**out, "ok": False, "reason": f"already a signal for {code}"}
    if shared:
        return {**out, "ok": False, "reason": "already listed under Shared, so it isn't a signal on its own"}
    if owners:
        return {**out, "ok": False, "needs_shared": True,
                "reason": f"already a signal for {', '.join(owners)}; it can go under Shared instead"}
    return {**out, "ok": True, "reason": ""}


def learn_text(text, code, kind, value, shared=False):
    """The register with the signal added to code's row, or (shared) moved into the Shared table."""
    text = ensure_columns(text)
    lines = text.splitlines()
    head, _, rows_at = projects_table(lines)
    cols = split_row(lines[head])
    if not shared:
        col = cols.index(LEARN_COLUMN[kind])
        i = next(i for i in rows_at if split_row(lines[i])[0] == code)
        cells = split_row(lines[i])
        cells[col] = ", ".join(x for x in (cells[col], value) if x)
        lines[i] = join_row(cells)
    else:
        owners, _ = signal_owners(text, value)
        for i in rows_at:   # out of the other project's row: never a signal for two projects
            cells = split_row(lines[i])
            if cells[0] in owners:
                cells = [", ".join(x for x in c.split(", ") if x.strip() and re.sub(r"\s*\(.*?\)", "", x).strip().lower()
                                   != value.lower()) if name in LEARN_COLUMN.values() else c for name, c in zip(cols, cells)]
                lines[i] = join_row(cells)
        at = lines.index("## Shared (not a signal on their own)") + 1
        while not lines[at].startswith("|"):
            at += 1
        at += 2
        while at < len(lines) and lines[at].startswith("|"):
            at += 1
        kind_label = {"sender": "Sender", "domain": "Email domain", "channel": "Teams channel", "alias": "Alias",
                      "stakeholder": "Stakeholder"}[kind]
        lines.insert(at, join_row([value, kind_label, ", ".join(sorted(set(owners) | {code}))]))
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def cmd_learn(code, kind, value, shared=False, check_only=False):
    """Remember the signal that decided a project choice in the register (BL-28): stages the register change,
    approved. `check_only` prints whether it can be learnt and stages nothing; `shared` moves it to Shared.
    """
    res = learn_check(code, kind, value)
    if check_only:
        print(json.dumps(res, ensure_ascii=False))
        return 0
    if not res["ok"] and not (shared and res.get("needs_shared")):
        print(f"Not learnt: {res['reason']}.")
        return 1
    text = paths.REGISTER.read_text(encoding="utf-8")
    where = "Shared" if shared else f"{code}'s {LEARN_COLUMN[kind]}"
    spec = {"source_run": "cx-review", "items": [], "file_changes": {
        "title": f"Register: {value} → {where}", "project": code,
        "file_ops": [{"op": "write", "path": paths.rel(paths.REGISTER), "content": learn_text(text, code, kind, value, shared)}]}}
    f = paths.DRAFTS / "learn.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    try:
        return cmd_preview(f, write=True)
    finally:
        f.unlink(missing_ok=True)


def cmd_register_columns():
    """Stage adding the Senders and Exclude columns to the register, if it lacks them."""
    text = paths.REGISTER.read_text(encoding="utf-8")
    new = ensure_columns(text)
    if new == text:
        print("The register already has the Senders and Exclude columns.")
        return 0
    f = paths.DRAFTS / "register-columns.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({"source_run": "cx-setup", "items": [], "file_changes": {
        "title": "Register: add Senders and Exclude columns", "project": None,
        "file_ops": [{"op": "write", "path": paths.rel(paths.REGISTER), "content": new}]}}), encoding="utf-8")
    try:
        return cmd_preview(f, write=True)
    finally:
        f.unlink(missing_ok=True)


# ===== BL-09: archive and restore a whole project =====
RETIRED = "## Retired codes"
CANCEL_FOR_ARCHIVE = {"actions": ("cancel", None), "raid": ("cancel", None), "promises": ("cancel", None),
                      "decisions": ("update", {"status": "Withdrawn"}), "milestones": ("update", {"status": "Cancelled"})}
ITEM_TEXT = {"actions": "description", "raid": "description", "promises": "description", "decisions": "decision",
             "milestones": "name"}


def archive_lines(item):
    """The preview lines of an archive or restore item."""
    who = f"{tracker.project_label(item['id'])} ({item['id']})"
    if item["op"] == "archive":
        return [f"Archive {who}: closed, it and its items marked archived (they leave the views, the export, the reminders "
                "and project matching; still in search, marked Archived)"]
    back = "active" if (item.get("changes") or {}).get("active", 1) else "closed, as it was"
    return [f"Restore {who}: its items live again, the project {back}"]


def retired_table(lines):
    """(index after the Retired codes table's last line, [row indices]) or None when the register has no such section."""
    if RETIRED not in lines:
        return None
    i = lines.index(RETIRED) + 1
    while i < len(lines) and not lines[i].startswith("|"):
        if lines[i].startswith("## "):
            return None
        i += 1
    head, rows_at = i, []
    i += 2
    while i < len(lines) and lines[i].startswith("|"):
        rows_at.append(i)
        i += 1
    return (i if head < len(lines) else len(lines)), rows_at


def archive_register(text, code, name):
    """(new text, the project's row as it was): the row moved from Projects to Retired codes."""
    lines = text.splitlines()
    _, _, rows_at = projects_table(lines)
    at = next((i for i in rows_at if split_row(lines[i])[0] == code), None)
    if at is None:
        raise SystemExit(f"{code} isn't in the register's Projects table.")
    row = lines.pop(at)
    retired = join_row([code, cell_clean(name), f"{datetime.now():%d-%m-%Y} (archived)"])
    found = retired_table(lines)
    if found is None:
        lines += ["", RETIRED, "", "| Code | Project | Closed |", "|------|---------|--------|", retired]
    else:
        lines.insert(found[0], retired)
    return "\n".join(lines) + ("\n" if text.endswith("\n") else ""), row


def restore_register(text, code, row):
    """The register with `code`'s Retired codes row taken out and its Projects row put back."""
    lines = text.splitlines()
    found = retired_table(lines)
    for i in reversed(found[1] if found else []):
        if split_row(lines[i])[0] == code:
            del lines[i]
    _, _, rows_at = projects_table(lines)
    after = [i for i in rows_at if split_row(lines[i])[0] and split_row(lines[i])[0] > code]
    if after:                                   # in code order, where it was in a sorted register
        lines.insert(after[0], row)
        return "\n".join(lines) + ("\n" if text.endswith("\n") else "")
    return add_register_row("\n".join(lines) + ("\n" if text.endswith("\n") else ""), row)


def free_folder(base, name):
    """`name`, or `name 2`, `name 3` … when a folder of that name is in `base` already (never overwriting)."""
    cand, n = name, 2
    while (base / cand).exists():
        cand, n = f"{name} {n}", n + 1
    return cand


def open_list(con, code):
    """[{table, id, text}] of the project's open items, for the page and for cx-edit to show before archiving."""
    out = []
    for t, i in tracker.open_items(con, code):
        r = con.execute(f"SELECT {ITEM_TEXT[t]} FROM {t} WHERE id = ?", (i,)).fetchone()
        out.append({"table": t, "id": i, "text": r[0] if r else ""})
    return out


def archive_spec(code, cancel_open=False):
    """The spec that archives a project: its open items cancelled (only with cancel_open), the archive item, the folder moved
    to the archive folder (99 Archive, or a vault's old _Archive until it is renamed, #252) and the register row moved to Retired
    codes. Exits with the reason when it can't be done."""
    con = tracker.connect()
    row = tracker.fetch(con, "projects", code)
    if row is None:
        sys.exit(f"{code} isn't a project in the tracker.")
    if row["archived"]:
        sys.exit(f"{tracker.project_label(code)} is archived already.")
    still = open_list(con, code)
    if still and not cancel_open:
        sys.exit(f"{tracker.project_label(code)} has {len(still)} open item(s): "
                 + "; ".join(f"{o['id']} {o['text']}" for o in still)
                 + ". Cancel them all and archive (--cancel-open), or stop.")
    folder = paths.project_dir(code)
    src = paths.rel(folder)
    dst = f"projects/{paths.archive_dir().name}/{free_folder(paths.archive_dir(), folder.name)}"     # #252: the name in use
    reg, old_row = archive_register(paths.REGISTER.read_text(encoding="utf-8"), code, row["name"])
    items = []
    for o in still:
        op, changes = CANCEL_FOR_ARCHIVE[o["table"]]
        items.append({"op": op, "table": o["table"], "id": o["id"], **({"changes": dict(changes)} if changes else {}),
                      "note": "Cancelled to archive the project"})
    items.append({"op": "archive", "table": "projects", "id": code, "register_row": old_row, "folder": {"from": src, "to": dst}})
    return {"source_run": "cx-edit", "items": items, "file_changes": {
        "title": f"Archive {row['name']}", "project": code, "archive": "archive",
        "file_ops": [{"op": "move", "from": src, "to": dst}, {"op": "write", "path": paths.rel(paths.REGISTER), "content": reg}]}}


def restore_spec(code):
    """The spec that restores an archived project: the folder back (a number added if its name is taken), the register row back,
    its items live again and `active` as it was before the archive."""
    con = tracker.connect()
    row = tracker.fetch(con, "projects", code)
    if row is None or not row["archived"]:
        sys.exit(f"{code} isn't an archived project.")
    last = tracker.last_archive(con, code)
    if not last or not last.get("folder") or not last.get("register_row"):
        sys.exit(f"The archive of {code} isn't in the history, so it can't be restored here.")
    src, orig = last["folder"]["to"], last["folder"]["from"]
    if not paths.resolve(src, archived=False).is_dir():
        sys.exit(f"{src} isn't there any more, so {code} can't be restored.")
    name = free_folder(paths.projects_root(), orig.split("/", 1)[1])
    dst = f"projects/{name}"
    cells = split_row(last["register_row"])
    if len(cells) > 2 and name != orig.split("/", 1)[1]:
        cells[2] = name                                           # the register names the numbered folder
    reg = restore_register(paths.REGISTER.read_text(encoding="utf-8"), code, join_row(cells))
    return {"source_run": "cx-edit", "items": [{"op": "restore", "table": "projects", "id": code,
                                                "changes": {"active": last["active"]}, "folder": {"from": src, "to": dst}}],
            "file_changes": {"title": f"Restore {row['name']}", "project": code, "archive": "restore",
                             "file_ops": [{"op": "move", "from": src, "to": dst},
                                          {"op": "write", "path": paths.rel(paths.REGISTER), "content": reg}]}}


def archive_cli(cmd, args):
    """archive <CODE> [--open | --cancel-open] [--out <name>.json]; restore <CODE> [--out <name>.json] (BL-09)."""
    words = [a for a in args if not a.startswith("--")]
    out = args[args.index("--out") + 1] if "--out" in args and args.index("--out") + 1 < len(args) else None
    code = words[0] if words else ""
    if not re.fullmatch(tracker.CODE_RE, code):
        sys.exit(f"{cmd} needs a project code: propose.py {cmd} ABC")
    if cmd == "archive" and "--open" in args:
        con = tracker.connect()
        print(json.dumps({"code": code, "name": tracker.project_label(code), "open": open_list(con, code)}, ensure_ascii=False))
        return 0
    spec = archive_spec(code, "--cancel-open" in args) if cmd == "archive" else restore_spec(code)
    return emit_spec(spec, out)
# ===== end BL-09 =====


def cmd_close_project(code, out=None):
    """Print (or save with --out) the spec that makes a project inactive, and list its open items."""
    con = tracker.connect()
    if not con.execute("SELECT 1 FROM projects WHERE code = ? AND active = 1", (code,)).fetchone():
        sys.exit(f"{code} isn't an active project.")
    open_items = [r[0] for r in con.execute(
        "SELECT id FROM actions WHERE project = ? AND status IN ('Open','Delayed') UNION ALL "
        "SELECT id FROM raid WHERE project = ? AND status = 'Open'", (code, code))]
    spec = {"source_run": "cx-edit", "items": [{"op": "update", "table": "projects", "id": code, "changes": {"active": 0}}]}
    print(f"Open items in {tracker.project_label(code)}: {', '.join(open_items) if open_items else 'none'}", file=sys.stderr)
    return emit_spec(spec, out)


# ── People register (BL-55) ───────────────────────────────────────────────────
# projects/_portfolio/people-register.md: one table, one row per person. The dashboard (JS) reads and writes the
# same format; dev/tests/test_people*.py check the two agree. Edits are file changes in a proposal, so they are
# logged and undoable. A name is mapped to its full name only when it matches exactly (full name, alias or email);
# a likely match is only ever offered, never used.

PEOPLE_COLUMNS = ("Full name", "Email", "Aliases", "Organisation", "Role", "Hidden", "Labels")
PEOPLE_SECTION = "## People"
PEOPLE_FIELDS = {"Full name": "name", "Email": "email", "Aliases": "aliases", "Organisation": "org", "Role": "role",
                 "Hidden": "hidden", "Labels": "labels"}      # Labels (BL-94): e.g. Client principal, Executive sponsor; comma-separated


def person_key(text):
    """A name compared loosely: lower case, no bracketed company or role, no dots or commas, single spaces."""
    t = re.sub(r"\([^)]*\)", " ", str(text or "")).lower()
    return " ".join(re.sub(r"[.,]", " ", t).split())


def cell_clean(v):
    """A value made safe for one Markdown table cell: no pipes or line breaks."""
    return str(v or "").replace("|", "/").replace("\n", " ").strip()


def people_table(lines):
    """(header index, [row indices]) of the register's People table, or None."""
    if PEOPLE_SECTION not in lines:
        return None
    i = lines.index(PEOPLE_SECTION) + 1
    while i < len(lines) and not lines[i].startswith("|"):
        if lines[i].startswith("## "):
            return None
        i += 1
    if i >= len(lines):
        return None
    head, rows_at = i, []
    i += 2
    while i < len(lines) and lines[i].startswith("|"):
        rows_at.append(i)
        i += 1
    return head, rows_at


def people_parse(text):
    """The register's people: [{name, email, aliases[], org, role, hidden, labels[], extra{}}]. Rows with no name are skipped."""
    lines = text.splitlines()
    found = people_table(lines)
    if not found:
        return []
    head, rows_at = found
    cols = split_row(lines[head])
    out = []
    for i in rows_at:
        cells = split_row(lines[i]) + [""] * len(cols)
        row = dict(zip(cols, cells))
        if not row.get("Full name", "").strip():
            continue
        out.append({"name": row["Full name"].strip(), "email": row.get("Email", "").strip(),
                    "aliases": [a.strip() for a in row.get("Aliases", "").split(",") if a.strip()],
                    "org": row.get("Organisation", "").strip(), "role": row.get("Role", "").strip(),
                    "hidden": row.get("Hidden", "").strip().lower() in ("yes", "y", "true", "1"),
                    "labels": tracker.label_names(row.get("Labels", "")),
                    "extra": {c: row[c] for c in cols if c not in PEOPLE_FIELDS}})
    return out


def people_text(text, people):
    """The register text with its People table rewritten from people (the rest of the file is kept). A table that
    isn't there yet is added; extra columns a person's row carried are kept."""
    lines = text.splitlines()
    found = people_table(lines)
    cols = split_row(lines[found[0]]) if found else []
    cols += [c for c in PEOPLE_COLUMNS if c not in cols]
    cols += [c for p in people for c in (p.get("extra") or {}) if c not in cols]
    cols = list(dict.fromkeys(cols))

    def cell(p, c):
        """One person's value for register column `c`."""
        f = PEOPLE_FIELDS.get(c)
        if f in ("aliases", "labels"):
            return cell_clean(", ".join(p.get(f) or []))
        if f == "hidden":
            return "yes" if p.get("hidden") else ""
        return cell_clean(p.get(f) if f else (p.get("extra") or {}).get(c, ""))
    table = [join_row(cols), "|" + "|".join("-" * (len(c) + 2) for c in cols) + "|"] + \
            [join_row([cell(p, c) for c in cols]) for p in people]
    if found:
        head, rows_at = found
        end = (rows_at[-1] if rows_at else head + 1) + 1
        lines[head:end] = table
    elif PEOPLE_SECTION in lines:
        lines[lines.index(PEOPLE_SECTION) + 1:lines.index(PEOPLE_SECTION) + 1] = [""] + table
    else:
        lines += ["", PEOPLE_SECTION, ""] + table
    return "\n".join(lines) + "\n"


# ===== Sweep and alerts (BL-97, BL-99, BL-98) =====
# BL-99: a person may have several addresses (Email, comma-separated), and a VIP column (blank, or management, client
# or yes). VIP is kept as one of the register's extra columns, so both parsers carry it untouched; when BL-94 (labels
# on people) is built it moves into a built-in label.

def person_emails(p):
    """A person's addresses, lower case: the Email cell split on commas (or semicolons)."""
    return [e.strip().lower() for e in re.split(r"[,;]", str(p.get("email") or "")) if e.strip()]


def person_vip(p):
    """The person's VIP kind ("management", "client", "yes"…), or "" when they aren't one."""
    v = str((p.get("extra") or {}).get("VIP") or "").strip()
    return "" if v.lower() in ("", "no", "n", "false", "0", "-") else v


def vip_people():
    """[{name, kind, emails}] of the register's VIPs."""
    return [{"name": p["name"], "kind": person_vip(p), "emails": person_emails(p)}
            for p in people_parse(people_register_text()[0]) if person_vip(p)]


def people_template():
    """The starting people register, from system/templates/."""
    return (paths.TEMPLATES / "people-register-template.md").read_text(encoding="utf-8")


def people_register_text():
    """The register as it is now, or the template when there isn't one yet; and whether the file exists."""
    if paths.PEOPLE_REGISTER.is_file():
        return paths.PEOPLE_REGISTER.read_text(encoding="utf-8"), True
    return people_template(), False


def identity_person():
    """Alan himself as a people-register entry, from settings `identity`, or None if no name is set."""
    import extraction                                              # lazily: extraction imports propose
    ident = extraction.section("identity")                         # a hand-edited "Alan", [] or null: no identity
    if not ident.get("name"):
        return None
    return {"name": ident["name"], "email": "", "aliases": list(ident.get("short_forms") or []), "org": "", "role": "",
            "hidden": False, "extra": {}, "me": True}


def item_owner_names():
    """Names on items that aren't necessarily in the register (owners, decision makers and a promise's people)."""
    if not paths.DB.is_file():
        return []
    con = tracker.connect()
    names = set()
    for table, col in OWNER_COLUMNS:
        sql = f"SELECT DISTINCT {col} FROM {table}"
        names.update(r[0] for r in con.execute(sql) if r[0])
    names.discard("TBC")
    return sorted(names)


def lev(a, b):
    """Edit distance between two short strings."""
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def resolve_person(text, people, others=()):
    """Match a name or email against the register. people: register people (plus Alan); others: names on items that
    aren't registered. Returns {status, name, candidates}: status is known (full name), alias, email, likely (only
    candidates, nothing mapped) or unknown. The same rules are in the dashboard (resolvePerson) and are tested to agree."""
    raw = str(text or "").strip()
    k = person_key(raw)
    out = {"input": raw, "status": "unknown", "name": None, "candidates": []}
    if not k:
        return out
    for p in people:
        if person_key(p["name"]) == k:
            return {**out, "status": "known", "name": p["name"]}
    for p in people:
        if k in {person_key(a) for a in p.get("aliases") or []}:
            return {**out, "status": "alias", "name": p["name"]}
    if "@" in raw:
        for p in people:
            if raw.lower() in person_emails(p):                       # one or more addresses, comma-separated (BL-99)
                return {**out, "status": "email", "name": p["name"]}
    for n in others:
        if person_key(n) == k:
            return {**out, "status": "known", "name": n}
    toks = person_key(re.split(r"[@]", raw)[0].replace(".", " ").replace("_", " ").replace("-", " ")) if "@" in raw \
        else k
    scored = []
    for name, forms in [(p["name"], [p["name"]] + list(p.get("aliases") or [])) for p in people] + \
                       [(n, [n]) for n in others]:
        best = 0
        for f in forms:
            fk = person_key(f)
            ft = fk.split()
            tt = toks.split()
            if not ft or not tt:
                continue
            if all(len(t) >= 2 for t in tt) and all(t in ft for t in tt):
                best = max(best, 3)
            elif len(tt) >= 2 and len(ft) >= 2 and ft[0].startswith(tt[0]) and any(w.startswith(tt[-1]) for w in ft[1:]):
                best = max(best, 3)
            elif toks.isalpha() and 2 <= len(toks) <= 4 and toks == "".join(w[0] for w in ft):
                best = max(best, 2)
            elif min(len(toks), len(fk)) >= 4 and lev(toks, fk) <= (1 if len(toks) < 10 else 2):
                best = max(best, 1)
        if best:
            scored.append((-best, name))
    out["candidates"] = list(dict.fromkeys(n for _, n in sorted(scored)))[:3]
    if out["candidates"]:
        out["status"] = "likely"
    return out


def people_pool():
    """(register people plus Alan, names on items that aren't registered) for resolve_person."""
    text, _ = people_register_text()
    people = people_parse(text)
    me = identity_person()
    if me:
        mine = next((p for p in people if person_key(p["name"]) == person_key(me["name"])), None)
        if mine:
            mine["aliases"] = list(dict.fromkeys(mine["aliases"] + me["aliases"]))
        else:
            people.append(me)
    reg = {person_key(p["name"]) for p in people}
    legacy = people_legacy_names()[0]                                  # not yet moved into the register (migrate)
    return people, [n for n in dict.fromkeys(item_owner_names() + legacy) if person_key(n) not in reg]


def people_view():
    """What the dashboard needs: the register (or none yet), the old settings lists, and the template for a new file."""
    text, exists = people_register_text()
    legacy = (paths.load_settings().get("people") or {})
    return {"exists": exists, "path": paths.rel(paths.PEOPLE_REGISTER), "text": text if exists else "",
            "people": [{k: v for k, v in p.items() if k != "extra"} for p in people_parse(text)],
            "legacy": {"added": legacy.get("added") or [], "hidden": legacy.get("hidden") or []},
            "template": people_template()}


def person_note(res):
    """The note shown when a name isn't in the people register (BL-55), with likely matches."""
    if res["status"] == "likely":
        return f"Is “{res['input']}” {' or '.join(res['candidates'])}? Not in the people register."
    return f"“{res['input']}” isn't in the people register."


PERSON_FIELDS = ("owner", "made_by", "lead",          # lead: a workstream's (BL-58)
                 "promised_by", "promised_to")         # a promise's two people (BL-125 A)


def map_owner_fields(item, people, others):
    """Map the owner (and made_by, a lead, a promise's people) of one proposal item to full names where they match exactly. Returns
    ([notes], [unknown results]); the item is changed in place."""
    notes, unknown = [], []
    for block in (item.get("values"), item.get("changes")):
        for field in PERSON_FIELDS:
            if not block or not block.get(field) or block[field] == "TBC":
                continue
            res = resolve_person(block[field], people, others)
            if res["status"] in ("alias", "email") or (res["status"] == "known" and res["name"] != block[field]):
                notes.append(f"{field.replace('_', ' ').capitalize()}: {block[field]} → {res['name']}")
                block[field] = res["name"]
            elif res["status"] in ("likely", "unknown"):
                unknown.append(res)
    return notes, unknown


def stage_spec(spec, tag):
    """Stage a spec built here as an approved proposal, through a temporary draft named `tag`."""
    f = paths.DRAFTS / f"{tag}.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    try:
        return cmd_preview(f, write=True)
    finally:
        f.unlink(missing_ok=True)


def register_spec(title, people, text, source_run="cx-edit", items=None):
    """A spec that rewrites the people register with `people` (BL-55), plus any tracker `items`."""
    path = paths.rel(paths.PEOPLE_REGISTER)
    return {"source_run": source_run, "items": items or [], "file_changes": {
        "title": title, "project": None, "file_ops": [{"op": "write", "path": path,
                                                       "content": people_text(text, people)}]}}


def find_person(people, name):
    """The register entry for a name, matched as the register matches names, or None."""
    k = person_key(name)
    return next((p for p in people if person_key(p["name"]) == k), None)


def cmd_people_list(as_json=False):
    """Print everyone in the people register and the owners not yet in it (BL-55), or JSON."""
    people, others = people_pool()
    rows = [{k: v for k, v in p.items() if k != "extra"} for p in people] + \
           [{"name": n, "email": "", "aliases": [], "org": "", "role": "", "hidden": False, "registered": False}
            for n in others]
    if as_json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    for p in rows:
        flag = "" if p.get("registered", True) else "  (on items, not in the register)"
        print(f"{p['name']} · {p['email'] or 'no email'} · {', '.join(p['aliases']) or 'no aliases'} · "
              f"{p['org'] or '—'} · {p['role'] or '—'}{' · hidden' if p['hidden'] else ''}{flag}")
    return 0


def cmd_people_add(a):
    """Stage adding one person to the people register (BL-55); refused if they are already in it."""
    text, _ = people_register_text()
    people = people_parse(text)
    people_all, others = people_pool()
    res = resolve_person(a["name"], people_all, others)
    if res["status"] in ("known", "alias", "email") and find_person(people, res["name"]):
        sys.exit(f"{res['name']} is already in the register ({res['status']} match). Use `people edit` to change them.")
    row = {"name": a["name"].strip(), "email": a.get("email", ""), "org": a.get("org", ""), "role": a.get("role", ""),
           "aliases": [x.strip() for x in a.get("aliases", "").split(",") if x.strip()], "hidden": False, "extra": {}}
    return stage_spec(register_spec(f"People register: add {row['name']}", people + [row], text), "person-add")


def cmd_people_edit(a):
    """Stage a change to one person in the people register: email, organisation, role, aliases, hidden (BL-55)."""
    text, _ = people_register_text()
    people = people_parse(text)
    p = find_person(people, a["name"])
    if not p:
        sys.exit(f"{a['name']} isn't in the register. Use `people add`.")
    for key in ("email", "org", "role"):
        if key in a:
            p[key] = a[key]
    if "aliases" in a:
        p["aliases"] = [x.strip() for x in a["aliases"].split(",") if x.strip()]
    if "add-alias" in a:
        p["aliases"] = list(dict.fromkeys(p["aliases"] + [a["add-alias"].strip()]))
    if "hidden" in a:
        p["hidden"] = a["hidden"].lower() in ("yes", "y", "true", "1")
    return stage_spec(register_spec(f"People register: change {p['name']}", people, text), "person-edit")


OWNER_COLUMNS = (("actions", "owner"), ("raid", "owner"), ("decisions", "made_by"),
                 ("promises", "promised_by"), ("promises", "promised_to"))      # BL-125 A: a promise's two people


def owner_items(old):
    """Update items moving every action, RAID item, decision and promise from old (as written) to a new name: each
    item's `changes` names the columns to set (a promise to oneself names both)."""
    con = tracker.connect()
    out = {}
    for table, col in OWNER_COLUMNS:
        for r in con.execute(f"SELECT id FROM {table} WHERE {col} = ? ORDER BY id", (old,)):
            out.setdefault(r[0], {"op": "update", "table": table, "id": r[0], "changes": {}})["changes"][col] = None
    return list(out.values())


def cmd_people_rename(old, new):
    """Rename old to new across the register and every item; if new already exists this is a merge (old becomes an
    alias of new, and its email, organisation and role fill any gaps)."""
    text, _ = people_register_text()
    people = people_parse(text)
    _, others = people_pool()
    old, new = old.strip(), new.strip()
    if old == new:
        sys.exit("Nothing to change.")
    src, dest = find_person(people, old), find_person(people, new)
    if not src and not any(person_key(n) == person_key(old) for n in others):
        sys.exit(f"{old} isn't a known person.")
    if src and (dest is None or dest is src):          # a plain rename
        src["name"] = new
        what, target = f"People: rename {old} to {new}", new
    elif src:                                           # merge two registered people
        for field in ("email", "org", "role"):
            dest[field] = dest[field] or src[field]
        dest["aliases"] = [x for x in dict.fromkeys(dest["aliases"] + [src["name"]] + src["aliases"])
                           if person_key(x) != person_key(dest["name"])]
        people.remove(src)
        what, target = f"People: merge {src['name']} into {dest['name']}", dest["name"]
    elif dest:                                          # old is only on items
        dest["aliases"] = [x for x in dict.fromkeys(dest["aliases"] + [old]) if person_key(x) != person_key(dest["name"])]
        what, target = f"People: merge {old} into {dest['name']}", dest["name"]
    else:                                               # neither is registered: register the new name
        people.append({"name": new, "email": "", "aliases": [], "org": "", "role": "", "hidden": False, "extra": {}})
        what, target = f"People: rename {old} to {new}", new
    items = owner_items(old)
    for it in items:
        it["changes"] = dict.fromkeys(it["changes"], target)
    return stage_spec(register_spec(what, people, text, items=items), "person-rename")


def cmd_people_map(proposal):
    """Map owners in a draft proposal to full names; flag the ones the register doesn't know (never guessed)."""
    f = Path(proposal)
    data = json.loads(f.read_text(encoding="utf-8"))
    if not paths.PEOPLE_REGISTER.is_file():
        print("No people register yet: owners left as written.")
        return 0
    people, others = people_pool()
    mapped, flagged = [], []
    for item in data.get("items", []):
        notes, unknown = map_owner_fields(item, people, others)
        mapped += [f"#{item.get('n')} {n}" for n in notes]
        if unknown:
            item["flags"] = list(dict.fromkeys(item.get("flags", []) + ["unknown-owner"]))
            flagged += [f"#{item.get('n')} {person_note(u)}" for u in unknown]
    f.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("\n".join(["Mapped:"] + mapped) if mapped else "Mapped: nothing needed changing.")
    if flagged:
        print("\n".join(["Flagged unknown-owner (for Review):"] + flagged))
    return 0


def people_legacy_names():
    """The names in the old settings people.added and people.hidden lists, before the register (BL-55)."""
    import extraction                                              # lazily: extraction imports propose
    legacy = extraction.section("people")                          # a hand-edited non-block: no legacy lists
    return list(legacy.get("added") or []), list(legacy.get("hidden") or [])


def cmd_people_migrate():
    """Move settings.json people.added / people.hidden into the register, once. Run it, say "apply", run it again
    to clear the old lists (it never clears them while a name is still missing from the register)."""
    added, hidden = people_legacy_names()
    if not added and not hidden:
        print("Nothing to move: settings.json holds no people lists.")
        return 0
    text, _ = people_register_text()
    people = people_parse(text)
    new, changed = [], False
    for n in added + hidden:
        base = re.sub(r"\s*\([^)]*\)\s*$", "", n).strip()
        company = re.search(r"\(([^)]*)\)\s*$", n)
        row = find_person(people + new, base)
        if row is None:
            row = {"name": base, "email": "", "aliases": [n] if base != n else [], "org": company.group(1) if company else "",
                   "role": "", "hidden": False, "extra": {}}
            new.append(row)
            changed = True
        if n in hidden and not row["hidden"]:
            row["hidden"] = True
            changed = True
    if changed:
        return stage_spec(register_spec(f"People register: move {len(new)} name{'s' if len(new) != 1 else ''} from settings",
                                        people + new, text, source_run="cx-setup"), "people-migrate")
    cmd_setting("people.added", "[]")
    cmd_setting("people.hidden", "[]")
    print("The old lists in settings.json are cleared; the register is now the only home for people.")
    return 0


def main_people(args):
    """Run the people command in `args`: list, resolve, add, edit, rename, merge, map or migrate (BL-55)."""
    import argparse
    ap = argparse.ArgumentParser(prog="propose.py people", add_help=True)
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("list").add_argument("--json", action="store_true")
    r = sub.add_parser("resolve")
    r.add_argument("text")
    for name in ("add", "edit"):
        s = sub.add_parser(name)
        s.add_argument("name")
        s.add_argument("--email")
        s.add_argument("--aliases")
        s.add_argument("--org")
        s.add_argument("--role")
        if name == "edit":
            s.add_argument("--add-alias")
            s.add_argument("--hidden")
    for name in ("rename", "merge"):
        s = sub.add_parser(name)
        s.add_argument("old" if name == "rename" else "source")
        s.add_argument("new" if name == "rename" else "into")
    sub.add_parser("map").add_argument("proposal")
    sub.add_parser("migrate")
    a = ap.parse_args(args)
    opts = {k.replace("_", "-"): v for k, v in vars(a).items() if v is not None and k not in ("cmd", "json")}
    if a.cmd == "list":
        return cmd_people_list(a.json)
    if a.cmd == "resolve":
        people, others = people_pool()
        print(json.dumps(resolve_person(a.text, people, others), ensure_ascii=False))
        return 0
    if a.cmd == "add":
        return cmd_people_add(opts)
    if a.cmd == "edit":
        return cmd_people_edit(opts)
    if a.cmd == "rename":
        return cmd_people_rename(a.old, a.new)
    if a.cmd == "merge":
        return cmd_people_rename(a.source, a.into)
    if a.cmd == "map":
        return cmd_people_map(a.proposal)
    if a.cmd == "migrate":
        return cmd_people_migrate()
    ap.print_help()
    return 2


# ===== Workstreams (BL-58, BL-56) =====

STOP = set("a an and the of to for in on at by with from is are be was were this that it its as or not no we our "
           "their they them will would should can could has have had do does did into about after before over under "
           "next new more any all per via vs".split())


def ws_rows(project=None):
    """The workstreams, for one project or all, as dictionaries (BL-58)."""
    con = tracker.connect()
    sql = "SELECT * FROM workstreams" + (" WHERE project = ?" if project else "") + " ORDER BY project, name COLLATE NOCASE"
    return [dict(r) for r in con.execute(sql, (project,) if project else ())]


def cmd_ws_list(project=None, as_json=False):
    """Print the workstreams, for one project or all, or JSON (BL-58)."""
    found = ws_rows(project)
    if as_json:
        print(json.dumps(found, indent=2, ensure_ascii=False))
        return 0
    for w in found:
        extra = ", ".join(f"{k} {w[k]}" for k in ("lead", "keywords", "aliases", "channel") if w.get(k))
        print(f"{w['id']} · {w['project']} · {w['name']} ({w['status']})" + (f" — {extra}" if extra else ""))
    if not found:
        print("No workstreams yet." + ("" if project else " Run tracker.py migrate to seed them from the items."))
    return 0


def ws_suggest(code, name):
    """Suggestions for a workstream, from the items that use the name or mention it, and their sources: keywords
    (frequent words), aliases (acronyms), lead (the commonest owner, as the register names them) and the Teams
    channel. creaite only suggests; Alan confirms or edits (BL-58)."""
    con = tracker.connect()
    low = name.strip().lower()
    items = [dict(r) for t in ("actions", "raid") for r in con.execute(
        f"SELECT description, owner, source, workstream FROM {t} WHERE project = ? AND (workstream = ? COLLATE NOCASE "
        "OR lower(description) LIKE ?)", (code, name.strip(), f"%{low}%"))]
    skip = STOP | set(re.findall(r"[a-z0-9]+", low)) | {code.lower()}
    words, acr, owners, channels = {}, {}, {}, {}
    for it in items:
        text = it["description"] or ""
        for w in re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", text):
            if w.lower() not in skip and not w.isupper():
                words[w.lower()] = words.get(w.lower(), 0) + 1
        for a in re.findall(r"\b[A-Z][A-Z0-9]{1,5}\b", text):
            if a != code and a.lower() not in skip:
                acr[a] = acr.get(a, 0) + 1
        if it["owner"] and it["owner"] != "TBC":
            owners[it["owner"]] = owners.get(it["owner"], 0) + 1
        m = re.search(r"Channel:\s*([^·]+)", it["source"] or "")
        if m:
            channels[m.group(1).strip()] = channels.get(m.group(1).strip(), 0) + 1
    top = lambda d, n: [k for k, _ in sorted(d.items(), key=lambda kv: (-kv[1], kv[0]))[:n]]  # noqa: E731
    lead = ""
    if owners:
        people, others = people_pool()
        res = resolve_person(top(owners, 1)[0], people, others)
        lead = res["name"] if res["status"] in ("known", "alias", "email") else ""
    return {"project": code, "name": name.strip(), "items": len(items), "keywords": ", ".join(top(words, 4)),
            "aliases": ", ".join(top(acr, 3)), "lead": lead, "channel": top(channels, 1)[0] if channels else ""}


def cmd_ws_add(code, name, opts):
    """Stage a new workstream for an active project, approved; a lead must be in the people register (BL-58)."""
    if code not in {r[0] for r in tracker.connect().execute("SELECT code FROM projects WHERE active = 1")}:
        sys.exit(f"{code} isn't an active project.")
    values = {"project": code, "name": name.strip(), "source": f"Alan (cx-edit), {datetime.now():%Y-%m-%d}"}
    for k in ("lead", "keywords", "aliases", "channel"):
        if opts.get(k):
            values[k] = opts[k].strip()
    if values.get("lead"):
        people, others = people_pool()
        res = resolve_person(values["lead"], people, others)
        if res["status"] not in ("known", "alias", "email"):
            sys.exit(person_note(res) + " Add them first (propose.py people add …), or leave the lead out.")
        values["lead"] = res["name"]
    return stage_spec({"source_run": "cx-edit", "items": [{"op": "new", "table": "workstreams", "values": values}]},
                      f"workstream-{code}")


def cmd_ws_retire_settings():
    """Clear settings.json workstreams.added / hidden once every per-project name in them is in the table (BL-58)."""
    legacy = paths.load_settings().get("workstreams") or {}
    keys = [k for k in (legacy.get("added") or []) + (legacy.get("hidden") or [])]
    if not keys:
        print("Nothing to retire: settings.json holds no workstream lists.")
        return 0
    have = {(w["project"], w["name"].lower()) for w in ws_rows()}
    missing = [k for k in keys if "|" in k and (k.split("|", 1)[0], k.split("|", 1)[1].strip().lower()) not in have]
    if missing:
        print("Not yet in the workstreams table: " + ", ".join(missing) + ". Run tracker.py migrate first.")
        return 1
    plain = [k for k in keys if "|" not in k]
    cmd_setting("workstreams.added", "[]")
    cmd_setting("workstreams.hidden", "[]")
    print("The old workstream lists in settings.json are cleared; the workstreams table is now their only home."
          + (f" Plain names with no project were dropped: {', '.join(plain)}." if plain else ""))
    return 0


def main_ws(args):
    """Run the workstreams command in `args`: list, suggest, add or retire-settings (BL-58)."""
    import argparse
    ap = argparse.ArgumentParser(prog="propose.py workstreams")
    sub = ap.add_subparsers(dest="cmd")
    ls = sub.add_parser("list")
    ls.add_argument("--project")
    ls.add_argument("--json", action="store_true")
    for name in ("suggest", "add"):
        s = sub.add_parser(name)
        s.add_argument("code")
        s.add_argument("name")
        if name == "add":
            for o in ("lead", "keywords", "aliases", "channel"):
                s.add_argument(f"--{o}")
    sub.add_parser("retire-settings")
    a = ap.parse_args(args)
    if a.cmd == "list":
        return cmd_ws_list(a.project, a.json)
    if a.cmd == "suggest":
        print(json.dumps(ws_suggest(a.code, a.name), ensure_ascii=False))
        return 0
    if a.cmd == "add":
        return cmd_ws_add(a.code, a.name, vars(a))
    if a.cmd == "retire-settings":
        return cmd_ws_retire_settings()
    ap.print_help()
    return 2


# ── Settings ──────────────────────────────────────────────────────────────────

def cmd_setting(key, raw):
    """Change one setting in system/config/settings.json now: the same type as before, times as HH:MM.
    The file is backed up to system/backups/ and the change logged in settings-log.jsonl.
    """
    try:
        value = json.loads(raw)
    except ValueError:
        value = raw                                   # plain text, e.g. 06:30
    text = paths.SETTINGS.read_text(encoding="utf-8")
    data = json.loads(text)
    node = data
    parts = key.split(".")
    for p in parts[:-1]:
        if not isinstance(node.get(p), dict):
            sys.exit(f"No setting {key}.")
        node = node[p]
    if parts[-1] not in node:
        sys.exit(f"No setting {key}.")
    old = node[parts[-1]]
    if isinstance(old, bool) != isinstance(value, bool) or (isinstance(old, (int, float)) and not isinstance(value, (int, float))):
        sys.exit(f"{key} expects a {type(old).__name__} (now {json.dumps(old)}).")
    if re.fullmatch(r"\d{2}:\d{2}", str(old)) and not re.fullmatch(r"\d{2}:\d{2}", str(value)):
        sys.exit("Times are 24-hour HH:MM.")
    was = json.loads(text).get("locations") or {}
    node[parts[-1]] = value
    why = notes_setting_problem(key, was, data)
    if why:
        sys.exit(why)
    paths.BACKUPS.mkdir(parents=True, exist_ok=True)
    shutil.copy2(paths.SETTINGS, paths.free_path(paths.BACKUPS, f"settings-{datetime.now():%Y-%m-%d-%H%M%S}", ".json"))   # BL-266
    paths.write_text_atomic(paths.SETTINGS, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    with open(paths.SETTINGS_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps({"at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "key": key, "old": old, "new": value})
                + "\n")
    print(f"{key}: {json.dumps(old)} → {json.dumps(value)} (saved, with a backup and a log line)")
    return 0


def notes_setting_problem(key, was, data):
    """#128: why a change to `key` can't be saved (paths.locations_change_problem: the notes folder shared with another kind,
    renamed while notes are under the old name, or a skeleton that isn't a template folder of its own), or None."""
    if not (key == "locations" or key.startswith("locations.")):
        return None
    loc = data.get("locations")
    return paths.locations_change_problem(was if isinstance(was, dict) else {}, loc if loc is not None else {})


# ===== Recode a project (BL-111) =====
# `propose.py recode OLD NEW`: the recode item for tracker.py (the database), plus the files that name the project: the register
# (its row, the Retired codes, the Shared table), the project's CLAUDE.md heading, mentions.jsonl and the search sidecars. Other mentions
# of the old code are only reported. creaite never renames the engagement folder: --folder names one Alan has already renamed.

def section_rows(lines, heading):
    """Indices of the table rows (header and separator included) under a '## heading' line, or []."""
    start = next((i for i, ln in enumerate(lines) if ln.strip().startswith(heading)), None)
    if start is None:
        return []
    rows, i = [], start + 1
    while i < len(lines) and not lines[i].startswith("## "):
        if lines[i].startswith("|"):
            rows.append(i)
        i += 1
    return rows


def recode_register(text, old, new, name, folder, old_name, day):
    """The register with the project's row recoded, the old code added to Retired codes, and the code swapped in the Shared table.
    Returns (text, the old folder cell)."""
    lines = text.splitlines()
    head, _, rows_at = projects_table(lines)
    cols = split_row(lines[head])
    ci, ni, fi = (cols.index(c) if c in cols else None for c in ("Code", "Project name", "Folder under projects/"))
    old_folder = ""
    for i in rows_at:
        cells = split_row(lines[i])
        if cells and cells[0] == old:
            old_folder = cells[fi] if fi is not None and fi < len(cells) else ""
            cells[ci] = new
            if name and ni is not None:
                cells[ni] = name
            if folder and fi is not None:
                cells[fi] = folder
            lines[i] = join_row(cells)
            break
    else:
        sys.exit(f"{old} isn't in the project register's Projects table.")
    rows = section_rows(lines, "## Retired codes")
    if rows:
        row = join_row([old, f"{old_name} (recoded to {new})", day])
        last = rows[-1]
        if len(rows) > 2 and lines[last].replace("|", "").strip() == "":
            lines[last] = row
        else:
            lines.insert(last + 1, row)
    shared = section_rows(lines, "## Shared")
    for i in shared[2:]:
        cells = split_row(lines[i])
        if cells and cells[-1]:
            cells[-1] = ", ".join(new if t.strip() == old else t.strip() for t in cells[-1].split(","))
            lines[i] = join_row(cells)
    return "\n".join(lines) + ("\n" if text.endswith("\n") else ""), old_folder


RECODE_LABELS = {"decisions": "decisions replacing one of these", "item_labels": "labels on these items"}


def recode_lines(con, item):
    """The preview of a recode item: what changes in the database."""
    old, ch = item["id"], item.get("changes") or {}
    new = ch.get("code") or "?"
    row = con.execute("SELECT * FROM projects WHERE code = ?", (old,)).fetchone()
    head = f"Recode {old} → {new}"
    if ch.get("name") and row is not None and ch["name"] != row["name"]:
        head += f"; name: {row['name']} → {ch['name']}"
    out = [head]
    f = item.get("folder") or {}
    if f.get("from") and f.get("to"):
        out.append(f"    Folder: {f['from']} → {f['to']} (the item sources follow)")
    for t in tracker.RECODE_ID_TABLES:
        ids = [r[0] for r in con.execute(f"SELECT id FROM {t} WHERE project = ? ORDER BY id", (old,))]
        if ids:
            out.append(f"    {t}: {len(ids)} (e.g. {ids[0]} → {tracker.recode_id(ids[0], old, new)})")
    n = con.execute("SELECT count(*) FROM updates WHERE project = ?", (old,)).fetchone()[0]
    if n:
        out.append(f"    updates: {n}")
    for t, cols in tracker.RECODE_LINKS.items():
        if t in ("actions", "raid"):            # their milestone links are counted with the items
            continue
        n = sum(con.execute(f"SELECT count(*) FROM {t} WHERE substr({c}, 1, ?) = ?", (len(old) + 1, old + "-")).fetchone()[0] for c in cols)
        if n:
            out.append(f"    {RECODE_LABELS.get(t, t)}: {n} reference(s) to {old}- items follow")
    if new != "?":
        out.append(f"    rejected items carried over: {len(tracker.recode_fingerprints(con, old, new))}")
    out.append("    history (change log) follows each item; the search index follows the project")
    return out


def token_lines(text, *words):
    """Numbers of the lines of text that hold any word as a whole token."""
    toks = [tracker.code_token(w) for w in words if w]
    return [n for n, ln in enumerate(text.splitlines(), 1) if any(t.search(ln) for t in toks)]


def main_recode(args):
    """Read the recode arguments (OLD NEW, --name, --folder, --dry-run) and run cmd_recode (BL-111)."""
    flags = {"--name": None, "--folder": None}
    rest, it = [], iter(args)
    for a in it:
        if a in flags:
            flags[a] = next(it, None) or sys.exit(f"{a} needs a value")
        elif a != "--dry-run":
            rest.append(a)
    if len(rest) != 2:
        sys.exit('usage: propose.py recode <OLD> <NEW> [--name "…"] [--folder "…"] [--dry-run]')
    return cmd_recode(rest[0], rest[1], flags["--name"], flags["--folder"], "--dry-run" in args)


# cmd_recode: change a project's code (and name) everywhere (BL-111): print the counts, new IDs and files that change, then
# stage it approved (`dry` only shows it), and list what it leaves for Alan to check. (A comment, not a docstring: the function
# is at its pinned length in dev/check-baseline.json.)
def cmd_recode(old, new, name, folder, dry):
    con = tracker.connect()
    problem = tracker.recode_code_problem(con, old, new)
    if problem:
        sys.exit(problem[0].upper() + problem[1:] + ".")
    row = con.execute("SELECT * FROM projects WHERE code = ?", (old,)).fetchone()
    old_name, day = row["name"], datetime.now().strftime("%Y-%m-%d")
    new_name = (name or "").strip() or None
    register = paths.REGISTER.read_text(encoding="utf-8")
    text, old_folder = recode_register(register, old, new, new_name, folder, old_name, day)
    if not old_folder:
        try:
            old_folder = paths.project_dir(old).name
        except LookupError:
            old_folder = ""
    notes = []
    if folder and not paths.resolve(f"projects/{folder}").is_dir():
        sys.exit(f"The folder “{folder}” doesn't exist. creaite doesn't rename engagement folders: rename it yourself, then run this again with --folder.")
    if not paths.external():              # the default layout reads a project's code from the first word of its folder name
        if not folder or folder.split(" ", 1)[0] != new:
            sys.exit(f"Project folders here start with the code. Rename “{old_folder}” to start with {new} (for example "
                     f"“{new} {new_name or old_name}”), then run this again with --folder \"<the new folder name>\".")
    elif not folder and old_folder and (tracker.code_token(old).search(old_folder) or (old_name and old_name in old_folder)):
        notes.append(f"The folder “{old_folder}” still carries the old code or name; creaite leaves it (rename it yourself, then recode with --folder).")
    folder_to = folder or old_folder
    ops = [{"op": "write", "path": paths.rel(paths.REGISTER), "content": text}]
    # the project's memory file: its heading
    mem_rel = f"projects/{folder_to}/CLAUDE.md"
    mem = paths.resolve(mem_rel)
    if mem.is_file():
        body = mem.read_text(encoding="utf-8")
        title = f"# {new} — {new_name or old_name}"
        fixed, n = re.subn(rf"^# {re.escape(old)}\b.*$", title, body, count=1, flags=re.M)
        if n:
            ops.append({"op": "write", "path": mem_rel, "content": fixed})
        else:
            notes.append(f"{mem_rel} has no “# {old} — …” heading to recode.")
        others = [x for x in token_lines(body, old) if not (n and body.splitlines()[x - 1].startswith(f"# {old}"))]
        if others:
            notes.append(f"{mem_rel} still mentions {old} on line(s) {', '.join(map(str, others[:8]))}: check them.")
    else:
        notes.append(f"{mem_rel} not found; the project's memory file is not changed.")
    # mentions.jsonl: the ids of items raised again
    if paths.MENTIONS.is_file():
        cur = paths.MENTIONS.read_text(encoding="utf-8")
        out = []
        for ln in cur.splitlines():
            try:
                m = json.loads(ln)
            except ValueError:
                out.append(ln)
                continue
            if isinstance(m, dict) and isinstance(m.get("id"), str):
                m["id"] = tracker.recode_id(m["id"], old, new)
                ln = json.dumps(m, ensure_ascii=False)
            out.append(ln)
        fixed = "\n".join(out) + ("\n" if cur.endswith("\n") else "")
        if fixed != cur:
            ops.append({"op": "write", "path": paths.rel(paths.MENTIONS), "content": fixed})
    # search sidecars (named by a hash of the path): only when the folder name changes
    if folder and old_folder and folder != old_folder and paths.SEARCH_DIR.is_dir():
        a, b = f"projects/{old_folder}/", f"projects/{folder}/"
        for f in sorted(paths.SEARCH_DIR.glob("*.json")):
            try:
                rec = json.loads(f.read_text(encoding="utf-8"))
            except ValueError:
                continue
            if isinstance(rec, dict) and str(rec.get("path", "")).startswith(a):
                rec["path"] = b + rec["path"][len(a):]
                target = tracker.sidecar_path(rec["path"])
                ops += [{"op": "write", "path": paths.rel(target), "content": json.dumps(rec, ensure_ascii=False, indent=1), "previous": None}
                        if not target.exists() else None, {"op": "remove", "path": paths.rel(f)}]
        ops = [o for o in ops if o]
    item = {"op": "recode", "table": "projects", "id": old, "changes": {"code": new, **({"name": new_name} if new_name else {})}}
    if folder and old_folder and folder != old_folder:
        item["folder"] = {"from": old_folder, "to": folder}
    spec = {"source_run": "cx-edit", "items": [item],
            "file_changes": {"title": f"Recode {old} to {new}", "project": old, "file_ops": ops}}
    f = paths.DRAFTS / "recode.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    try:
        code = cmd_preview(f, write=not dry)
    finally:
        f.unlink(missing_ok=True)
    # what creaite leaves for Alan to check
    things = [(paths.PEOPLE_REGISTER, "the people register"), (paths.PORTFOLIO_MEMORY, "PORTFOLIO.md")]
    for p, what in things:
        try:
            hits = token_lines(p.read_text(encoding="utf-8"), old, old_name)
        except OSError:
            continue
        if hits:
            notes.append(f"{what} mentions {old} or “{old_name}” on line(s) {', '.join(map(str, hits[:8]))}: not changed.")
    dismissed = list((paths.load_settings().get("reminders") or {}).get("dismissed_forever") or [])
    moved = [re.sub(rf"^(weekly:[^:]+:){re.escape(old)}$", rf"\g<1>{new}", re.sub(rf"^client:{re.escape(old)}:", f"client:{new}:", d)) for d in dismissed]
    if moved != dismissed:
        notes.append("Reminders you dismissed for good under the old code will come back. After the apply, keep them dismissed with: "
                     f"python3 system/scripts/propose.py setting reminders.dismissed_forever '{json.dumps(moved, ensure_ascii=False)}'")
    notes.append(f"Mail and meetings may still say {old} or “{old_name}”: after the apply, teach the new project the old name with "
                 f"`propose.py learn {new} alias \"{old_name}\"`.")
    for n in notes:
        print("Check: " + n)
    return code


# ===== BL-249 (fix-field-names) =====
# Each table's writable fields, read from schema.sql in memory (never the tracker: `fields` writes and opens nothing).
# `propose.py fields <table>` prints them for ask creaite; cx-edit's SKILL.md carries the same list in a generated block
# (dev/tools/skill_fields.py writes it; a test fails when it differs from schema.sql).
FIELD_TABLES = ("projects", "milestones", "workstreams", "actions", "raid", "decisions", "promises", "links", "labels")
SKILL_START = "<!-- BL-249 fields: generated from schema.sql by `python3 dev/tools/skill_fields.py`; don't edit by hand -->"
SKILL_END = "<!-- end BL-249 fields -->"


def schema_columns():
    """{table: [column, …]} for FIELD_TABLES, in schema.sql's order."""
    import sqlite3
    con = sqlite3.connect(":memory:")
    try:
        con.executescript(paths.SCHEMA.read_text(encoding="utf-8"))
        return {t: [r[1] for r in con.execute(f"PRAGMA table_info({t})")] for t in FIELD_TABLES}
    finally:
        con.close()


def writable_fields(table, cols=None):
    """The fields a spec may name for `table`: every column except the ones tracker.py sets (id, updated_at)."""
    return [c for c in (cols or schema_columns()[table]) if c not in tracker.NO_EDIT]


def fields_block():
    """The markdown table between SKILL_START and SKILL_END in cx-edit's SKILL.md."""
    cols = schema_columns()
    rows = [SKILL_START, "| Table | Fields (`*` needed for a new item) |", "|-------|--------|"]
    for t in FIELD_TABLES:
        req = tracker.REQUIRED_NEW.get(t, ())
        rows.append(f"| {t} | " + ", ".join(f"`{f}`" + ("*" if f in req else "") for f in writable_fields(t, cols[t])) + " |")
    return "\n".join(rows + [SKILL_END])


def cmd_fields(table=None):
    """Print a table's writable fields (or every table's), with the values each allows. Read only."""
    if table is None or table not in FIELD_TABLES:
        print(f"Tables: {', '.join(FIELD_TABLES)}. Run: python3 system/scripts/propose.py fields <table>")
        return 0 if table is None else 2
    req = tracker.REQUIRED_NEW.get(table, ())
    print(f"{table}: the fields a spec may use in `values` (new) or `changes` (update); * is needed for a new item")
    for f in writable_fields(table):
        allowed = tracker.ALLOWED.get((table, f))
        print(f"  {f}{' *' if f in req else ''}" + (f"  ({', '.join(allowed)})" if allowed else "")
              + ("  (YYYY-MM-DD)" if f in tracker.DATE_FIELDS else ""))
    print("Not fields: id (tracker.py assigns it; an update names it as the item's `id`) and updated_at. "
          "A change's reason is the item's own `note`, beside `changes`" + ("; a rebaseline is the item's `rebaseline` block."
                                                                             if table == "milestones" else "."))
    return 0
# ===== end BL-249 =====


def _main_files(cmd, args):
    """The register and folder commands: register-columns, and old-archives (BL-09). None when cmd is neither."""
    if cmd == "register-columns":
        return cmd_register_columns()
    if cmd == "old-archives" and (not args or (len(args) == 2 and args[0] == "--out")):
        return cmd_old_archives(args[1] if args else None)
    if cmd in ("archive", "restore") and args:
        return archive_cli(cmd, args)                                    # BL-09
    return None


def main(argv):
    """Run the propose command in `argv` (see the module docstring)."""
    cmd, args = (argv[0], argv[1:]) if argv else ("", [])
    if cmd == "fields" and len(args) <= 1:                                    # BL-249: read only
        return cmd_fields(args[0] if args else None)
    if cmd in ("preview", "stage") and len(args) == 1:
        return cmd_preview(args[0], write=cmd == "stage")
    if cmd == "new-project":
        opts = dict(zip([a.lstrip("-") for a in args[0::2]], args[1::2]))
        if not opts.get("code") or not opts.get("name"):
            sys.exit("new-project needs --code and --name")
        return cmd_new_project(opts)
    if cmd == "close-project" and (len(args) == 1 or (len(args) == 3 and args[1] == "--out")):
        return cmd_close_project(args[0], args[2] if len(args) == 3 else None)
    if cmd == "recode":
        return main_recode(args)
    if cmd == "setting" and len(args) == 2:
        return cmd_setting(*args)
    if cmd == "learn" and len([a for a in args if not a.startswith("--")]) == 3:
        code, kind, value = [a for a in args if not a.startswith("--")]
        return cmd_learn(code, kind, value, shared="--shared" in args, check_only="--check" in args)
    done = _main_files(cmd, args)
    if done is not None:
        return done
    if cmd == "workstreams":
        return main_ws(args)
    if cmd == "people":
        return main_people(args)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
