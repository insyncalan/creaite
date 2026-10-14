"""creaite permissions — the one safe way to widen what ask creaite may do (BL-75). Standard library only.

ask creaite runs Claude Code headless, which cannot ask for permission: it can only do what `.claude/settings.json`
allows. When a request needs one more rule, the panel names it, Alan approves it there, and the dashboard (or Alan, from
Terminal) runs this script. The panel itself can never run it: `permissions.py` is denied to it, and `.claude/` isn't
editable by it, so it cannot widen its own permissions without Alan seeing.

Commands:
  check "<rule>"             is this rule one creaite will add? Prints JSON {ok, rule, reason, covered}; writes nothing
  apply "<rule>" --why "<reason>" [--via dashboard|cli]
                             add the rule to `.claude/settings.json` permissions.allow: the file is backed up to
                             system/backups/claude-settings-*.json, and the change is logged in
                             system/config/permissions-log.jsonl and settings-log.jsonl
  undo                       take out the rule (or folder) added by the latest change that hasn't been undone (leaving anything else,
                             including rules Alan added by hand since); backed up and logged the same way
  edit "<spec>" --why "<reason>" [--via dashboard|cli]
                             one confirmed edit of a permission file (BL-96), each its own request, never in bulk. <spec> is
                               <settings|local> <add|remove> <allow|deny|dir> <rule or folder>   .claude/settings.json or
                                                                                              .claude/settings.local.json
                               config set <dotted.key> <json value>                        system/config/settings.json
                               script <file in system/staging/>                            a new permissions.py, compiled and
                                                                                           self-tested first
                             Each is backed up, logged and undoable. Blanket rules (Write(*), a bare Bash, a home folder) are
                             refused, and so is removing a deny entry that keeps the panel out of the permission files.
  recover                    put back any deny entries lifted for a confirmed permission-file run that was cut short (the live
                             server does this at start; doctor flags a leftover)
  preview "<spec>"           the same check as edit, writing nothing: JSON {ok, reason, summary, before, after}
  projects-root --why "<reason>" [--via dashboard|cli]
                             when the projects are in a projects root outside the vault, add it to permissions.additionalDirectories
                             so Claude Code may read it (BL-93): that one folder, as the setting spells it; backed up and logged
  list [--json]              the allow rules, the extra folders, and the changes made through this script

Rules creaite will add are narrow:
  Bash(python3 system/scripts/<script>.py <fixed words> *)   a script that exists in system/scripts/ (never this one)
  Edit(<path>) and Write(<path>)                             inside projects/<folder>/ (one project's folder, never all of
                                                             projects/), inbox/, system/staging/, system/search/ or
                                                             system/history/; never the engine, the database, .claude or .git,
                                                             and never zz Archive or _Templates. A projects/<folder>/ rule is
                                                             written in the form Claude Code needs (~/… when the projects are
                                                             in a OneDrive projects root)
Anything else (a blanket Bash or Edit rule, node, curl, a path outside the vault, a deny rule) is refused: edit
.claude/settings.json yourself in Terminal if you really want it.
"""
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

EDIT_ROOTS = ("projects/", "inbox/", "system/staging/", "system/search/", "system/history/")
EDIT_NEVER = (".claude", ".git", "system/scripts", "system/templates", "system/tracker.db", "system/config", "system/releases",
              "system/branding")
NEVER_SCRIPTS = {"permissions.py"}                     # the panel must not be able to widen its own permissions
SHELL_CHARS = re.compile(r"[;&|<>`$(){}\\\n\r]")
RULE = re.compile(r"^(Bash|Edit|Write)\((.+)\)$")


def read_settings():
    """The parsed .claude/settings.json; exits with a message if it can't be read."""
    try:
        return json.loads(paths.CLAUDE_SETTINGS.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        sys.exit(f"creaite: can't read .claude/settings.json ({e}); run `python3 system/scripts/doctor.py`")


def covers(existing, rule):
    """Does an existing rule already grant this one?"""
    if existing == rule:
        return True
    a, b = RULE.match(existing), RULE.match(rule)
    if not (a and b) or a.group(1) != b.group(1):
        return False
    have, want = a.group(2), b.group(2)
    if a.group(1) == "Bash":
        return have.endswith(" *") and (want == have[:-2] or want.startswith(have[:-1]))
    return have.endswith("/**") and want.startswith(have[:-2])


def real_rule(rule):
    """The rule as it is written to settings.json: a projects/<folder>/… rule becomes the pattern Claude Code needs (BL-93)."""
    m = RULE.match(rule)
    if m and m.group(1) in ("Edit", "Write") and m.group(2).startswith("projects/"):
        return f"{m.group(1)}({paths.tool_pattern(m.group(2)[len('projects/'):])})"
    return rule


# ===== BL-140 (sprint-admin): the colon form, and a reason that is true =====
INTERPRETERS = ("python", "python3", "node", "bash", "sh", "zsh", "fish", "perl", "ruby", "osascript", "env", "xargs", "eval",
                "exec", "sudo", "awk", "find", "npx", "uv", "pipx", "deno", "bun", "php", "lua", "Rscript", "pwsh", "powershell")


def normalise(rule):
    """The rule as creaite reads it: spaces tidied, and Claude Code's old prefix form `Bash(<command>:*)` read as `Bash(<command> *)`,
    so a request written either way is judged the same."""
    rule = re.sub(r"\s+", " ", (rule or "").strip())
    m = re.fullmatch(r"Bash\((.*?)\s*:\*\)", rule)
    return f"Bash({m.group(1)} *)" if m else rule


# ===== BL-237 (sprint-portability): the interpreter wrapper, `system/scripts/run <name>.py …` =====
WRAPPER = "run"
WRAPPER_RULE = r"system/scripts/run [a-z0-9_]+\.py"


def script_rule(spec):
    """(form, script name, fixed words) when a Bash rule's spec runs one creaite script, as `python3 system/scripts/<name>.py …`
    (or python) or through the wrapper `system/scripts/run <name>.py …`; else None. One shape, two spellings."""
    spec = (spec or "").strip()
    m = re.fullmatch(r"(python3?) system/scripts/([a-z][a-z0-9_]*)\.py((?: [A-Za-z0-9_.:=\-]+)*)(?: \*)?", spec) or \
        re.fullmatch(r"(system/scripts/run) ([a-z][a-z0-9_]*)\.py((?: [A-Za-z0-9_.:=\-]+)*)(?: \*)?", spec)
    return (m.group(1), m.group(2), m.group(3)) if m else None


def runs_one_script(spec):
    """True when a Bash rule's spec starts with one creaite script, in either spelling (the start only, as doctor reads it)."""
    return bool(re.match(r"^(?:python3? system/scripts/|system/scripts/run )[a-z0-9_]+\.py\b", (spec or "").strip()))
# ===== end BL-237 =====


def bash_bounds(spec):
    """Why a Bash rule is out of bounds whatever is approved (it would run anything), or None."""
    words = (spec or "").strip().split()
    if not words or words[0] in ("*", "**", ":*"):
        return "Bash on its own runs any command"
    first = words[0].rsplit("/", 1)[-1]
    # ===== BL-237 (sprint-portability): the wrapper runs any creaite script, so a wildcard in place of the script is out of bounds =====
    if words[0].endswith("/" + WRAPPER) or words[0] == WRAPPER:
        if not re.fullmatch(WRAPPER_RULE + r"\b.*", spec.strip()):
            return f"system/scripts/{WRAPPER} without a named creaite script runs any of them"
    # ===== end BL-237 =====
    if first in INTERPRETERS and (len(words) == 1 or any("*" in w for w in words[1:]) and not re.fullmatch(r"python3? system/scripts/[a-z0-9_]+\.py\b.*", spec.strip())):
        return f"{first} with a wildcard is an interpreter or shell, which runs anything"
    return None


def check_full(rule, settings=None):
    """What creaite says about a requested rule (BL-140): {ok, rule, reason, covered, state}. `rule` is the normalised form, which is
    the one creaite adds. state: "addable"; "allowed" (already allowed by `covered`: nothing to add, the request failed for another
    reason); "refused" (not something creaite adds, said plainly); "out_of_bounds" (it would let the panel round the database, the
    engine or its own permissions: only Alan, by hand, in Terminal)."""
    rule = normalise(rule)
    ok, reason, covered = check(rule, settings)
    state = "addable" if ok else "allowed" if covered else "refused"
    m = RULE.match(rule)
    if not ok and not covered:
        tool, spec = (m.group(1), m.group(2)) if m else (rule, "")
        if tool == "Bash" and (bash_bounds(spec) or "permissions.py" in spec):
            state = "out_of_bounds"
        elif tool in ("Edit", "Write") and any(n in spec for n in ("system/tracker.db", "system/scripts", "creaite-rules.md", ".claude/settings")):
            state = "out_of_bounds"
    return {"ok": ok, "rule": rule, "reason": reason, "covered": covered, "state": state}


def check(rule, settings=None):
    """(ok, reason, covered_by). ok is False for a rule creaite won't add (reason says why) or one already granted (reason
    "already allowed", covered_by the rule that grants it). The colon form `…py:*` is read as `…py *` first (BL-140).
    BL-265: the rule's shape, then the Bash or the path rules, then what the settings deny or allow, as before."""
    rule = normalise(rule)
    if rule == "Bash":
        return False, "Bash on its own runs any command: creaite never adds it", None
    m = RULE.match(rule)
    if not m:
        return False, "creaite only adds Bash, Edit and Write rules, written like Bash(python3 system/scripts/report.py adhoc *)", None
    tool, spec = m.groups()
    if tool == "Bash" and "permissions.py" in spec:
        return False, "permissions.py is never allowed to the panel", None
    if SHELL_CHARS.search(spec):
        return False, "the rule has shell characters (; & | < > ` $ ( ) { } or a backslash)", None
    why = _bash_rule_refused(spec) if tool == "Bash" else _path_rule_refused(tool, spec)
    if why:
        return False, why, None
    return _against_settings(rule, settings if settings is not None else read_settings())


def _bash_rule_refused(spec):
    """Why a Bash rule isn't one creaite script (directly or through the wrapper, BL-237), or None."""
    b = re.fullmatch(r"(python3?) (system/scripts/([a-z][a-z0-9_]*)\.py)((?: [A-Za-z0-9_.:=\-]+)*)(?: \*)?", spec)
    w = None if b else script_rule(spec)
    if w and w[0] == "system/scripts/run":
        if w[1] + ".py" in NEVER_SCRIPTS:
            return f"{w[1]}.py is never allowed to the panel"
        if not (paths.ROOT / "system" / "scripts" / (w[1] + ".py")).is_file():
            return f"system/scripts/{w[1]}.py doesn't exist in this vault"
    if not b and not (w and w[0] == "system/scripts/run"):
        bound = bash_bounds(spec)
        if bound:
            return f"{bound}: creaite never adds it"
        return (f"{spec} is not a creaite script: a Bash rule must run one creaite script, like "
                "Bash(python3 system/scripts/report.py adhoc *)")
    if b and b.group(3) + ".py" in NEVER_SCRIPTS:
        return f"{b.group(3)}.py is never allowed to the panel"
    if b and not (paths.ROOT / b.group(2)).is_file():
        return f"{b.group(2)} doesn't exist in this vault"
    return None


def _path_rule_refused(tool, spec):
    """Why an Edit or Write rule's path isn't one the panel may write, or None."""
    parts = spec.split("/")
    if spec.startswith(("/", "~")) or ".." in parts or "\\" in spec or ":" in spec:
        return "a path must be inside the vault: relative, with no .. or ~"
    if not spec.startswith(EDIT_ROOTS):
        return f"{tool} rules are only for {', '.join(EDIT_ROOTS)}"
    if spec.startswith("projects/"):
        folder = parts[1] if len(parts) > 1 else ""
        if not folder or re.search(r"[*?\[\]]", folder):
            return "name the project folder: projects/<folder>/…, not all of projects/"
        if any(p in parts for p in paths.never_index()):
            return "zz Archive, _Templates and 99 System are never read or written by creaite"
    if any(n in spec for n in EDIT_NEVER):
        return "that path holds the engine, the database, the settings or .claude: creaite never lets the panel write there"
    return None


def _against_settings(rule, settings):
    """(ok, reason, covered_by) against the permission files: denied, already allowed, or new."""
    perms = settings.get("permissions") or {}
    written = real_rule(rule)
    for d in perms.get("deny") or []:
        if covers(d, written):
            return False, f"it is denied by the rule {d}", None
    for a in perms.get("allow") or []:
        if covers(a, written):
            return False, "already allowed", a
    return True, "", None


def now():
    """The time now as 'YYYY-MM-DD HH:MM:SS', for log entries."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(entry):
    """Append one entry to system/config/permissions-log.jsonl."""
    paths.PERMISSIONS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(paths.PERMISSIONS_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def log_entries():
    """Every entry in permissions-log.jsonl, oldest first; unreadable lines skipped."""
    out = []
    if paths.PERMISSIONS_LOG.exists():
        for line in paths.PERMISSIONS_LOG.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    return out


def write_settings(text, stamp):
    """Back up the current file, then write the new one. Returns the backup's vault path."""
    paths.BACKUPS.mkdir(parents=True, exist_ok=True)
    backup = paths.free_path(paths.BACKUPS, f"claude-settings-{stamp}", ".json")   # BL-266
    shutil.copy2(paths.CLAUDE_SETTINGS, backup)
    paths.CLAUDE_SETTINGS.write_text(text, encoding="utf-8")
    return paths.rel(backup)


def settings_log(key, old, new):
    """Append one change to system/config/settings-log.jsonl."""
    with open(paths.SETTINGS_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps({"at": now(), "key": key, "old": old, "new": new}, ensure_ascii=False) + "\n")


LOCAL_SETTINGS = paths.CLAUDE_SETTINGS.with_name("settings.local.json")
FILES = {"settings": paths.CLAUDE_SETTINGS, "local": LOCAL_SETTINGS}
LISTS = {"allow": "allow", "deny": "deny", "dir": "additionalDirectories"}
PROTECTED_DENY = ("Edit(.claude/settings.json)", "Write(.claude/settings.json)", "Edit(.claude/settings.local.json)",
                  "Write(.claude/settings.local.json)", "Bash(python3 system/scripts/permissions.py *)",
                  "Bash(python system/scripts/permissions.py *)", "Bash(python3 system/scripts/permissions.py*)",
                  "Bash(python system/scripts/permissions.py*)", "Edit(system/tracker.db)", "Write(system/tracker.db)",
                  "Edit(system/scripts/schema.sql)", "Edit(system/scripts/paths.py)", "WebFetch", "Bash(git push *)",
                  "Bash(git push*)", "Bash(curl *)",
                  "Bash(system/scripts/run permissions.py *)", "Bash(system/scripts/run permissions.py*)")   # BL-237
# (above) what keeps the panel from widening itself or touching the record
SKIP_WORDS = re.compile(r"bypass|dangerously|skip", re.I)


def next_id(entries=None):
    """The next change number for permissions-log.jsonl."""
    return max([e.get("id", 0) for e in (entries if entries is not None else log_entries())] + [0]) + 1


def read_file(which):
    """The parsed permission file `which` ('settings' or 'local'), or {} if it doesn't exist."""
    f = FILES[which]
    if not f.exists():
        return {}
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        sys.exit(f"creaite: can't read {paths.rel(f)} ({e})")


def write_file(which, data, stamp):
    """Back the file up (if there is one), write the new one, read it back; put the old one back if that fails."""
    f = FILES[which]
    paths.BACKUPS.mkdir(parents=True, exist_ok=True)
    backup = None
    if f.exists():
        backup = paths.free_path(paths.BACKUPS, f"claude-settings{'-local' if which == 'local' else ''}-{stamp}", ".json")   # BL-266
        shutil.copy2(f, backup)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    try:
        json.loads(f.read_text(encoding="utf-8"))
    except ValueError:
        if backup:
            shutil.copy2(backup, f)
        sys.exit("creaite: the file didn't read back as JSON; the earlier one was put back")
    return paths.rel(backup) if backup else None


def stamp():
    """The time now as 'YYYY-MM-DD-HHMMSS', for backup file names."""
    return datetime.now().strftime("%Y-%m-%d-%H%M%S")


def parse_edit(spec):
    """(kind, fields) for an edit spec, or (None, reason)."""
    spec = re.sub(r"\s+", " ", (spec or "").strip())
    m = re.fullmatch(r"(settings|local) (add|remove) (allow|deny|dir) (.+)", spec)
    if m:
        return "list", dict(file=m.group(1), op=m.group(2), list=m.group(3), value=m.group(4).strip())
    m = re.fullmatch(r"config set ([A-Za-z0-9_]+(?:\.[A-Za-z0-9_\-]+)*) (.+)", spec)
    if m:
        try:
            return "config", dict(key=m.group(1), value=json.loads(m.group(2)))
        except ValueError:
            return None, "the value must be JSON (a number, true/false, a quoted \"string\" or a list)"
    m = re.fullmatch(r"script (system/staging/[A-Za-z0-9_./ \-]+)", spec)
    if m:
        return "script", dict(path=m.group(1))
    return None, ("an edit is `settings|local add|remove allow|deny|dir <rule or folder>`, `config set <key> <json>` "
                  "or `script system/staging/<file>`")


def check_value_rule(f, settings):
    """The same limits as apply, for a rule added to allow in either file."""
    ok, reason, covered = check(f["value"], settings)
    if not ok:
        return False, reason + (f" ({covered})" if covered else "")
    return True, ""


def preview_list(f):
    """What adding or removing one permission list entry would do, or why it is refused. BL-265: the value, then the add or
    remove rules, as before."""
    which, op, lst, val = f["file"], f["op"], f["list"], f["value"]
    data = read_file(which)
    cur = list((data.get("permissions") or {}).get(LISTS[lst]) or [])
    label = f"{paths.rel(FILES[which])} › permissions.{LISTS[lst]}"
    if not val or len(val) > 300 or SHELL_CHARS.search(val.replace("(", "").replace(")", "").replace("*", "")) and lst != "dir":
        return dict(ok=False, reason="that isn't a rule creaite will write")
    if SKIP_WORDS.search(val):
        return dict(ok=False, reason="a skip-permissions setting is never added")
    why = _add_refused(f, data, cur, label) if op == "add" else _remove_refused(lst, val, cur, label)
    if why:
        return dict(ok=False, reason=why)
    after = cur + [val] if op == "add" else [x for x in cur if x != val]
    return dict(ok=True, reason="", summary=f"{'Add' if op == 'add' else 'Remove'} {val} {'to' if op == 'add' else 'from'} {label}",
                before=cur, after=after)


def _add_refused(f, data, cur, label):
    which, lst, val = f["file"], f["list"], f["value"]
    if val in cur:
        return f"{val} is already in {label}"
    if lst == "allow":
        ok, reason = check_value_rule(f, data if which == "settings" else dict(data, permissions=dict(data.get("permissions") or {}, deny=read_file("settings").get("permissions", {}).get("deny", []))))
        return None if ok else reason
    if lst == "deny":
        if not RULE.match(val) and val not in ("WebFetch", "WebSearch"):
            return "a deny entry is written like Edit(path), Bash(command) or WebFetch"
        return None
    root = str(paths.locations().get("projects_root") or "").strip().rstrip("/")
    if not root or val.rstrip("/") != root:
        return "the only folder outside the vault creaite adds is the projects root (locations.projects_root)"
    return None


def _remove_refused(lst, val, cur, label):
    if val not in cur:
        return f"{val} isn't in {label}"
    if lst == "deny" and val in PROTECTED_DENY:
        return "that deny entry keeps the panel out of the permission files and the database: edit it yourself in Terminal if you really mean to"
    return None


def settings_value(data, key):
    """(found, value) for a dotted key in a settings dictionary."""
    node = data
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return False, None
        node = node[part]
    return True, node


def preview_config(f):
    """Check one change to a setting in system/config/settings.json, writing nothing: JSON-ready
    {ok, reason, summary, before, after}. One existing, non-section key, of the same type (BL-96).
    """
    key, new = f["key"], f["value"]
    if key.split(".")[0] in ("permissions", "_about"):
        return dict(ok=False, reason="that isn't a setting creaite changes this way")
    data = paths.load_settings()
    found, old = settings_value(data, key)
    if not found:
        return dict(ok=False, reason=f"{key} isn't a setting in system/config/settings.json")
    if isinstance(old, dict) or isinstance(new, dict):
        return dict(ok=False, reason="change one setting at a time, not a whole section")
    if type(old) is not type(new) and not (isinstance(old, (int, float)) and isinstance(new, (int, float)) and not isinstance(new, bool)
                                           and not isinstance(old, bool)):
        return dict(ok=False, reason=f"{key} holds {type(old).__name__}, not {type(new).__name__}")
    if old == new:
        return dict(ok=False, reason=f"{key} is already {json.dumps(new)}")
    return dict(ok=True, reason="", summary=f"Change {key} in system/config/settings.json: {json.dumps(old)} → {json.dumps(new)}",
                before=old, after=new)


SELF_TESTS = (("Write(inbox/notes/**)", True), ("Write(*)", False), ("Edit(**)", False), ("Bash(node build.js)", False),
              ("Edit(.claude/settings.json)", False), ("Write(~/**)", False), ("Write(//etc/**)", False),
              ("Write(projects/**)", False), ("Bash(python3 system/scripts/permissions.py *)", False))


def self_test(new_file):
    """Copy this vault's engine into a temp folder with the new permissions.py and ask it the questions it must answer the same way."""
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory(prefix="creaite-permtest-") as tmp:
        t = Path(tmp)
        (t / "system" / "scripts").mkdir(parents=True)
        (t / "system" / "config").mkdir(parents=True)
        (t / ".claude").mkdir()
        shutil.copy2(paths.ROOT / "system" / "scripts" / "paths.py", t / "system" / "scripts" / "paths.py")
        shutil.copy2(new_file, t / "system" / "scripts" / "permissions.py")
        shutil.copy2(paths.CLAUDE_SETTINGS, t / ".claude" / "settings.json")
        if paths.SETTINGS.exists():
            shutil.copy2(paths.SETTINGS, t / "system" / "config" / "settings.json")
        for rule, want in SELF_TESTS:
            r = subprocess.run([sys.executable, str(t / "system" / "scripts" / "permissions.py"), "check", rule],
                               capture_output=True, text=True, cwd=tmp)
            try:
                got = json.loads(r.stdout.strip().splitlines()[-1])["ok"]
            except (ValueError, IndexError, KeyError):
                return False, f"the new file couldn't answer `check {rule}`: {(r.stderr or r.stdout).strip()[-200:]}"
            if got != want:
                return False, f"the new file {'accepts' if got else 'refuses'} {rule}, which it must {'refuse' if got else 'accept'}"
        for cmd in (["list", "--json"], ["preview", "settings add allow Write(inbox/notes/**)"]):
            r = subprocess.run([sys.executable, str(t / "system" / "scripts" / "permissions.py"), *cmd], capture_output=True, text=True, cwd=tmp)
            if r.returncode:
                return False, f"the new file's `{' '.join(cmd)}` fails: {(r.stderr or r.stdout).strip()[-200:]}"
    return True, ""


def preview_script(f):
    """Check a new permissions.py from system/staging/, writing nothing: it must compile and pass its
    self-test; returns {ok, reason, summary, before, after} with the diff (BL-96).
    """
    src = paths.ROOT / f["path"]
    if ".." in Path(f["path"]).parts or not src.is_file():
        return dict(ok=False, reason="there is no such file in system/staging/")
    import py_compile
    try:
        py_compile.compile(str(src), doraise=True, cfile=str(paths.BACKUPS / ".perm-compile.pyc"))
    except py_compile.PyCompileError as e:
        return dict(ok=False, reason=f"the new permissions.py doesn't compile: {str(e).strip()[-200:]}")
    ok, why = self_test(src)
    if not ok:
        return dict(ok=False, reason=why)
    import difflib
    old = (paths.ROOT / "system/scripts/permissions.py").read_text(encoding="utf-8").splitlines()
    new = src.read_text(encoding="utf-8").splitlines()
    diff = [ln for ln in difflib.unified_diff(old, new, "permissions.py", "new", lineterm="", n=0) if not ln.startswith(("---", "+++", "@@"))]
    return dict(ok=True, reason="", summary=f"Replace system/scripts/permissions.py ({len([d for d in diff if d[0] == '+'])} lines added, "
                                            f"{len([d for d in diff if d[0] == '-'])} removed; it compiles and passes the self-test)", diff=diff[:200])


def preview(spec):
    """Check a permission-file edit spec without writing anything; {ok, reason, summary, before, after} (BL-96)."""
    kind, f = parse_edit(spec)
    if not kind:
        return dict(ok=False, reason=f)
    return {"list": preview_list, "config": preview_config, "script": preview_script}[kind](f)


def cmd_edit(spec, why, via):
    """Make one confirmed permission-file edit (BL-96): a rule in .claude/settings.json or settings.local.json,
    a setting in system/config/settings.json, or a new permissions.py. The file is backed up to system/backups/, and
    the change logged in permissions-log.jsonl and settings-log.jsonl, so `undo` takes it back.
    """
    why = re.sub(r"\s+", " ", (why or "").strip())
    if not why or len(why) > 300:
        sys.exit("creaite: say why, in up to 300 characters (--why)")
    pv = preview(spec)
    if not pv["ok"]:
        print(f"Not changed: {pv['reason']}.")
        return 1
    kind, f = parse_edit(spec)
    entries = log_entries()
    n = next_id(entries)
    st = stamp()
    if kind == "list":
        data = read_file(f["file"])
        data.setdefault("permissions", {})[LISTS[f["list"]]] = pv["after"]
        backup = write_file(f["file"], data, st)
        log({"id": n, "at": now(), "op": f["op"], "file": f["file"], "kind": f["list"], "rule": f["value"], "why": why, "via": via,
             "backup": backup})
        settings_log(f"claude_permissions.{LISTS[f['list']]}", f["value"] if f["op"] == "remove" else None, f["value"] if f["op"] == "add" else None)
        print(f"{pv['summary']} (change {n}" + (f"; the file before is {backup}" if backup else "") + "). Undo it with: python3 system/scripts/permissions.py undo")
        return 0
    if kind == "config":
        cur = paths.load_settings()
        node = cur
        parts = f["key"].split(".")
        for part in parts[:-1]:
            node = node[part]
        old = node[parts[-1]]
        paths.BACKUPS.mkdir(parents=True, exist_ok=True)
        backup = paths.free_path(paths.BACKUPS, f"settings-{st}", ".json")   # BL-266
        shutil.copy2(paths.SETTINGS, backup)
        node[parts[-1]] = f["value"]
        paths.SETTINGS.write_text(json.dumps(cur, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        log({"id": n, "at": now(), "op": "set", "file": "config", "kind": "config", "key": f["key"], "rule": f"{f['key']} = {json.dumps(f['value'])}",
             "old": old, "new": f["value"], "why": why, "via": via, "backup": paths.rel(backup)})
        settings_log(f["key"], old, f["value"])
        print(f"{pv['summary']} (change {n}; the file before is {paths.rel(backup)}). Undo it with: python3 system/scripts/permissions.py undo")
        return 0
    src = paths.ROOT / f["path"]                              # script
    target = paths.ROOT / "system" / "scripts" / "permissions.py"
    paths.BACKUPS.mkdir(parents=True, exist_ok=True)
    backup = paths.free_path(paths.BACKUPS, f"permissions-py-{st}", ".py")   # BL-266
    shutil.copy2(target, backup)
    tmp = target.with_name(".permissions.py.part")
    tmp.write_bytes(src.read_bytes())
    tmp.replace(target)
    log({"id": n, "at": now(), "op": "script", "file": "script", "kind": "script", "rule": "system/scripts/permissions.py", "why": why, "via": via,
         "backup": paths.rel(backup), "after": hashlib.sha256(target.read_bytes()).hexdigest()[:16]})
    settings_log("system/scripts/permissions.py", None, "replaced")
    print(f"{pv['summary']} (change {n}; the file before is {paths.rel(backup)}). Undo it with: python3 system/scripts/permissions.py undo")
    return 0


# ── freeform edits of the permission files by a confirmed run (BL-96) ──
FILE_TARGETS = {".claude/settings.json": "settings", ".claude/settings.local.json": "local", "system/config/settings.json": "config"}
LIFT_MARKER = paths.STAGING / "deny-lifted.json"
FORBIDDEN_MODES = ("bypassPermissions", "acceptEdits", "dontAsk")
BLANKET_SPECS = ("*", "**", "/", "//", "/**", "//**", "~", "~/", "~/*", "~/**", ".", "./**")


# Microsoft 365 (Sprint 4b, item 1b): ask creaite may read all of it, all the time. Anything that sends, deletes or changes mail,
# calendar, Teams or files acts outside the laptop and can't be undone, so it is never allowed unless Alan decides otherwise.
M365 = "mcp__claude_ai_Microsoft_365__"
M365_READ = ("chat_message_search", "find_meeting_availability", "get_granted_scopes", "get_me", "outlook_calendar_search",
             "outlook_email_search", "outlook_find_available_time", "read_resource", "search_people", "sharepoint_folder_search",
             "sharepoint_search", "teams_list_channel_messages", "teams_list_channels", "teams_list_chats", "teams_list_teams")
M365_ACTIONS = ("outlook_batch_delete_messages", "outlook_batch_modify_labels", "outlook_create_draft", "outlook_create_event",
                "outlook_create_filter", "outlook_create_label", "outlook_create_reply_all_draft", "outlook_create_reply_draft",
                "outlook_delete_draft", "outlook_delete_event", "outlook_delete_filter", "outlook_delete_label", "outlook_forward_mail",
                "outlook_modify_labels", "outlook_modify_thread_labels", "outlook_respond_to_event", "outlook_send_draft",
                "outlook_send_mail", "outlook_set_vacation", "outlook_trash_thread", "outlook_untrash_thread", "outlook_update_draft",
                "outlook_update_event", "outlook_update_label", "sharepoint_copy_item", "sharepoint_create_folder",
                "sharepoint_delete_item", "sharepoint_move_item", "sharepoint_rename_item", "sharepoint_update_file",
                "sharepoint_upload_file", "teams_create_chat", "teams_reply_channel_message", "teams_send_channel_message",
                "teams_send_chat_message")


def m365_read_tools():
    """The full names of the Microsoft 365 reading tools ask creaite may always use."""
    return [M365 + t for t in M365_READ]


def m365_action_tools():
    """The full names of the Microsoft 365 action tools, which stay denied (they act outside the laptop)."""
    return [M365 + t for t in M365_ACTIONS]


def m365_problem(rule):
    """Why a Microsoft 365 rule is too broad for creaite, or None: a reading tool is fine; the whole server, an action or a tool
    creaite doesn't know is not."""
    rule = str(rule).strip()
    if not rule.startswith(M365.rstrip("_")):
        return None
    name = rule[len(M365):] if rule.startswith(M365) else ""
    if name in M365_READ:
        return None
    if name in M365_ACTIONS:
        return "it sends, deletes or changes something in Microsoft 365, which can't be undone from here"
    return "it allows every Microsoft 365 tool, actions included" if not name else "it is a Microsoft 365 tool creaite hasn't checked"


def broad_rule(rule):
    """Why a rule is too broad for creaite to write, or None. Blanket tool rules, the whole disk or home folder, a bare Bash
    or interpreter, anything that skips permissions."""
    rule = str(rule)
    if SKIP_WORDS.search(rule):
        return "it skips permissions"
    if rule.strip().startswith(M365.rstrip("_")):
        return m365_problem(rule)
    m = re.match(r"^(\w+)(?:\((.*)\))?$", rule.strip())
    if not m:
        return "it isn't a permission rule"
    tool, spec = m.group(1), m.group(2)
    if tool in ("Bash", "Edit", "Write", "WebFetch", "WebSearch", "NotebookEdit") and (spec is None or spec.strip() in BLANKET_SPECS):
        return f"{tool} for everything is a blanket rule"
    if tool == "Bash" and spec and not runs_one_script(spec):                   # BL-237: either spelling
        return "a Bash rule must run one creaite script"
    if tool == "Bash" and spec and bash_bounds(spec):
        return bash_bounds(spec)
    if tool in ("Edit", "Write") and spec:
        root = str(paths.locations().get("projects_root") or "").strip().rstrip("/")
        if spec.startswith(("//", "~", "/")) and not (root and (spec.startswith(root + "/") or spec.startswith("//" + root.lstrip("/") + "/"))):
            return "a path outside the vault and the projects folder"
    return None


def validate_edit(which, before, after):
    """None if the edited permission file is acceptable, else why not. `before` and `after` are the parsed files. BL-265: the
    config file, then the deny, allow, folder and mode checks, in the order they always had."""
    if not isinstance(after, dict):
        return "the file is no longer a JSON object"
    if which == "config":
        if (after.get("permissions") or {}) != (before.get("permissions") or {}):
            return "system/config/settings.json carries no permissions section"
        return None
    bp, ap = before.get("permissions") or {}, after.get("permissions") or {}
    if not isinstance(ap, dict):
        return "permissions is no longer an object"
    return _removed_deny(bp, ap) or _new_rule_refused(bp, ap) or _new_folder_refused(bp, ap) or _mode_refused(bp, ap)


def _removed_deny(bp, ap):
    for d in bp.get("deny") or []:
        if d in PROTECTED_DENY and d not in (ap.get("deny") or []):
            return f"the deny entry {d} keeps the panel out of the permission files and the database, so it can't be removed this way"
    return None


def _new_rule_refused(bp, ap):
    for rule in (ap.get("allow") or []):
        if rule not in (bp.get("allow") or []):
            why = broad_rule(rule)
            if why:
                return f"the new rule {rule} is refused: {why}"
    return None


def _new_folder_refused(bp, ap):
    for d in (ap.get("additionalDirectories") or []):
        if d not in (bp.get("additionalDirectories") or []) and str(d).rstrip("/") in ("", "/", "~", str(Path.home())):
            return f"the new folder {d} is the whole disk or your home folder"
    return None


def _mode_refused(bp, ap):
    mode = ap.get("defaultMode")
    if mode in FORBIDDEN_MODES and mode != bp.get("defaultMode"):
        return f"defaultMode {mode} skips permissions"
    return None


# ===== BL-141 (sprint-admin): open permission editing, and what is refused whatever is approved =====
# ask creaite may change its own permission files on Alan's approval (the one card). This keeps the database and the engine behind
# their own commands: a change is refused, and the file put back, if it opens arbitrary shell, writes the database, the engine or
# creaite-rules.md, turns on a skip-permissions mode, removes a safety entry, or changes a key that runs commands or switches the
# guard off. Every other rule, broad Edit and Write rules included, is allowed on approval.
CLAUDE_KEYS_OK = ("permissions", "model", "cleanupPeriodDays", "includeCoAuthoredBy", "outputStyle", "language", "spinnerTipsEnabled",
                  "alwaysThinkingEnabled", "$schema")
PERMISSION_LISTS_OK = ("allow", "deny", "ask", "additionalDirectories")
PROTECTED_PATHS = ("system/tracker.db", "system/tracker.db-wal", "system/scripts/tracker.py", "system/scripts/schema.sql",
                   "system/scripts/paths.py", "system/scripts/reach.py", "system/scripts/permissions.py", "system/creaite-rules.md",
                   "system/scripts/run",                                                                       # BL-237: the wrapper
                   "VERSION", "system/releases/creaite-1.0.0.zip")


def _glob_re(pattern):
    out, i = "", 0
    while i < len(pattern):
        c = pattern[i]
        if pattern[i:i + 2] == "**":
            out, i = out + ".*", i + 2
            continue
        out += "[^/]*" if c == "*" else "[^/]" if c == "?" else re.escape(c)
        i += 1
    return re.compile(out + "(/.*)?$", re.I)


def reaches_protected(spec):
    """Would an Edit or Write rule with this pattern let a tool write the database, the engine or the rules? Patterns are read as
    Claude Code reads them: relative to the vault, `/…` from the vault, `//…` absolute, `~/…` from the home folder, and a name with
    no slash at any depth."""
    import os
    spec = (spec or "").strip() or "**"
    vault = str(paths.ROOT.resolve())
    home = os.path.realpath(os.path.expanduser("~"))
    for rel in PROTECTED_PATHS:
        full = f"{vault}/{rel}"
        if spec.startswith("//"):
            cand = full.lstrip("/")
            pat = spec[2:]
        elif spec.startswith("~/"):
            if not full.startswith(home + "/"):
                continue
            cand, pat = full[len(home) + 1:], spec[2:]
        elif "/" not in spec.rstrip("/"):
            if _glob_re(spec).match(rel.rsplit("/", 1)[-1]) or spec in ("*", "**"):
                return rel
            continue
        else:
            cand, pat = rel, spec.lstrip("/")
        if _glob_re(pat).match(cand):
            return rel
    return None


def rule_refusal(rule):
    """Why this allow rule is refused whatever is approved, or None (BL-141)."""
    rule = normalise(str(rule))
    if SKIP_WORDS.search(rule):
        return "it skips permissions"
    if rule.startswith(M365.rstrip("_")):
        return m365_problem(rule)
    m = re.match(r"^(\w+)(?:\((.*)\))?$", rule)
    if not m:
        return "it isn't a permission rule"
    tool, spec = m.group(1), m.group(2)
    if tool == "Bash":
        if spec is None or not spec.strip():
            return "Bash on its own runs any command"
        bound = bash_bounds(spec)
        if bound:
            return bound
        if "permissions.py" in spec:
            return "permissions.py is never allowed to the panel"
        if re.search(r"\bsqlite3?\b|tracker\.db|system/scripts/(?!\S+\.py\b)(?!run [a-z0-9_]+\.py\b)|creaite-rules\.md|\bVERSION\b", spec):
            return "it would change the database, the engine or creaite's rules by hand"
    if tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        hit = reaches_protected(spec if spec is not None else "**")
        if hit:
            return f"it would let a tool write {hit} (the database, the engine and creaite's rules stay behind their own commands)"
    return None


def settings_problem(kind, before, after):
    """None if this new content of a permission or settings file may be written on approval; else why not. kind is "claude" (a
    Claude Code settings file), "config" (system/config/settings.json), "json" (another JSON settings file) or "mcp" (.mcp.json).
    BL-265: one function per kind of file; every check in the order it always had."""
    if kind == "mcp":
        return "MCP servers run commands, so .mcp.json is changed only by hand"
    if not isinstance(after, dict):
        return "the file is no longer a JSON object"
    if kind == "config":
        return _config_problem(before, after)
    if kind != "claude":
        return None
    return _claude_problem(before, after)


def _config_problem(before, after):
    """system/config/settings.json: no permissions section, and a projects folder inside the home folder."""
    if (after.get("permissions") or {}) != (before.get("permissions") or {}):
        return "system/config/settings.json carries no permissions section"
    root = str((after.get("locations") or {}).get("projects_root") or "").strip()
    if root and root != str((before.get("locations") or {}).get("projects_root") or "").strip():
        import os
        real = os.path.realpath(os.path.expanduser(root))
        home = os.path.realpath(os.path.expanduser("~"))
        if not real.startswith(home + "/"):
            return "the projects folder must be inside your home folder"
    return None


def _claude_problem(before, after):
    """A Claude Code settings file: only the permission lists change, no safety entry goes, every new rule and folder is one
    creaite would add."""
    for key in set(before) | set(after):
        if before.get(key) != after.get(key) and key not in CLAUDE_KEYS_OK:
            return (f"creaite changes only the permission rules in this file; {key} can run commands or change how Claude Code "
                    "runs, so it is changed only by hand")
    bp, ap = before.get("permissions") or {}, after.get("permissions") or {}
    if not isinstance(ap, dict):
        return "permissions is no longer an object"
    for key in set(bp) | set(ap):
        if bp.get(key) != ap.get(key) and key not in PERMISSION_LISTS_OK:
            return "defaultMode can skip permissions" if key == "defaultMode" else f"permissions.{key} is changed only by hand"
    return _claude_entries_problem(bp, ap)


def _claude_entries_problem(bp, ap):
    """A safety deny entry removed, a new allow rule creaite refuses, or a new folder that is the whole disk."""
    return _safety_deny_removed(bp, ap) or _refused_new_rule(bp, ap) or _whole_disk_folder(bp, ap)


def _safety_deny_removed(bp, ap):
    for d in bp.get("deny") or []:
        if d in PROTECTED_DENY and d not in (ap.get("deny") or []):
            return f"it removes the safety entry {d}"
    return None


def _refused_new_rule(bp, ap):
    for rule in ap.get("allow") or []:
        if rule not in (bp.get("allow") or []):
            why = rule_refusal(rule)
            if why:
                return f"the new rule {rule} is refused: {why}"
    return None


def _whole_disk_folder(bp, ap):
    for d in ap.get("additionalDirectories") or []:
        if d not in (bp.get("additionalDirectories") or []) and str(d).strip().rstrip("/") in ("", "/", "//"):
            return f"the new folder {d} is the whole disk"
    return None


def add_rule_content(rule, which="settings"):
    """(new file text, written rule, reason): .claude/settings.json with one allow rule added, for the card (BL-140, BL-141). The
    reason is set (and the text None) when the rule is already allowed or refused."""
    rule = normalise(rule)
    data = read_file(which)
    perms = data.get("permissions") or {}
    written = real_rule(rule)
    for d in perms.get("deny") or []:
        if covers(d, written):
            return None, written, f"it is denied by the rule {d}"
    for a in perms.get("allow") or []:
        if covers(a, written):
            return None, written, f"already allowed by {a}"
    new = json.loads(json.dumps(data))
    new.setdefault("permissions", {}).setdefault("allow", []).append(written)
    why = settings_problem("claude", data, new)
    if why:
        return None, written, why
    return json.dumps(new, indent=2, ensure_ascii=False) + "\n", written, ""
# ===== end BL-141 =====


def trim_repeats(before, after):
    """A rule the run added that the file already listed is listed once, not twice (a repeat that was there before is left as it
    was). Changes `after` in place; returns the rules trimmed."""
    trimmed = []
    bp, ap = before.get("permissions") or {}, after.get("permissions") or {}
    if not isinstance(ap, dict):
        return trimmed
    for kind in ("allow", "deny", "ask"):
        now, was = ap.get(kind), (bp.get(kind) if isinstance(bp, dict) else None) or []
        if not isinstance(now, list):
            continue
        kept, seen = [], {}
        for rule in now:
            seen[rule] = seen.get(rule, 0) + 1
            if isinstance(rule, str) and seen[rule] > max(was.count(rule), 1):
                trimmed.append(rule)
            else:
                kept.append(rule)
        ap[kind] = kept
    return trimmed


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16] if Path(p).exists() else None


def _put_back(settings, lifted, order):
    """Put the lifted deny entries back in `settings` where they were, so a run that changed nothing leaves the file as it was."""
    deny = settings.setdefault("permissions", {}).setdefault("deny", [])
    for d in lifted:
        if d not in deny:
            deny.insert(min(order.index(d) if d in order else len(deny), len(deny)), d)
    return settings


def begin_file_edit(path):
    """Before a confirmed run edits one permission file: back it up and, for the two .claude files, lift the deny entries that
    stop the panel's Edit and Write tools on it, noting them (and their places) in a marker so they are always put back."""
    which = FILE_TARGETS.get(path)
    if not which:
        raise ValueError("not a permission file")
    st = stamp()
    paths.BACKUPS.mkdir(parents=True, exist_ok=True)
    target = paths.ROOT / path
    backup = None
    if target.exists():
        backup = paths.free_path(paths.BACKUPS, f"permfile-{which}-{st}", ".json")   # BL-266
        shutil.copy2(target, backup)
    state = {"path": path, "which": which, "backup": paths.rel(backup) if backup else None, "lifted": [], "stamp": st, "deny_before": [],
             "before": json.loads(target.read_text(encoding="utf-8")) if target.exists() else {}, "before_sha": _sha(target)}
    if which in ("settings", "local"):
        settings = read_file("settings")
        deny = (settings.get("permissions") or {}).get("deny") or []
        state["deny_before"] = list(deny)
        state["lifted"] = [d for d in (f"Edit({path})", f"Write({path})") if d in deny]
        state["settings_allow"] = (settings.get("permissions") or {}).get("allow")
        if state["lifted"]:
            if which == "local":
                write_file("settings", settings, st)                         # a backup of settings.json, with its denies
            settings["permissions"]["deny"] = [d for d in deny if d not in state["lifted"]]
            paths.CLAUDE_SETTINGS.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    LIFT_MARKER.parent.mkdir(parents=True, exist_ok=True)
    LIFT_MARKER.write_text(json.dumps({"path": path, "lifted": state["lifted"], "deny_before": state["deny_before"], "at": now()}), encoding="utf-8")
    return state


def _restore_denies(lifted, order=()):
    if not lifted:
        return
    settings = read_file("settings")
    before = json.dumps(settings, sort_keys=True)
    _put_back(settings, lifted, list(order))
    if json.dumps(settings, sort_keys=True) != before:
        paths.CLAUDE_SETTINGS.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def finish_file_edit(state, why, via="dashboard"):
    """After the run: put the lifted deny entries back, check what was changed, keep it (logged, undoable) or put the file back.
    Returns (ok, message). BL-265: judge the file, then put it back or keep it; the deny entries always go back (finally)."""
    path, which = state["path"], state["which"]
    target = paths.ROOT / path
    backup = paths.ROOT / state["backup"] if state["backup"] else None
    order = state.get("deny_before") or []
    try:
        problem, after, repeats = _judge_file_edit(state, path, which, target, order)
        if problem:                                                       # put the file back exactly as it was
            if backup:
                shutil.copy2(backup, target)
            elif target.exists():
                target.unlink()
            return False, f"Not changed: {problem}. {path} is as it was."
        return _keep_file_edit(state, path, which, target, after, repeats, why, via)
    finally:
        _restore_denies(state["lifted"], order)                           # for the other two files this puts them back in settings.json
        LIFT_MARKER.unlink(missing_ok=True)


def _judge_file_edit(state, path, which, target, order):
    """(problem or None, the file as parsed, rules listed twice) for the edited permission file."""
    problem, after, repeats = None, None, []
    if target.exists():
        try:
            after = json.loads(target.read_text(encoding="utf-8"))
        except ValueError:
            problem = f"{path} is no longer valid JSON"
    elif state["before_sha"]:
        problem = f"{path} was deleted"
    if problem is None and after is not None:
        if which == "settings":                                       # judge the file as it will be, with its own safety entries back in
            _put_back(after, state["lifted"], order)
        problem = validate_edit(which, state["before"], after)
        repeats = trim_repeats(state["before"], after) if problem is None else []
    if which == "local" and problem is None and (read_file("settings").get("permissions") or {}).get("allow") != state.get("settings_allow"):
        problem = "the run changed .claude/settings.json as well, which it was not asked to"
    return problem, after, repeats


def _keep_file_edit(state, path, which, target, after, repeats, why, via):
    """Write the accepted file (without repeats), log the change so it can be undone, and say what happened."""
    unchanged = (after == state["before"]) if after is not None else not state["before_sha"]
    if after is not None and (which == "settings" or repeats):
        target.write_text(json.dumps(after, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if unchanged:
        return True, f"No change was made to {path}." + (f" {', '.join(repeats)} {'is' if len(repeats) == 1 else 'are'} already listed." if repeats else "")
    n = next_id()
    log({"id": n, "at": now(), "op": "file", "file": which, "kind": "file", "rule": f"{path} edited", "why": (why or "")[:300], "via": via,
         "backup": state["backup"], "after": _sha(target)})
    settings_log(f"permission_file:{path}", None, "edited")
    return True, (f"Changed {path} (change {n}" + (f"; the file before is {state['backup']}" if state["backup"] else "") + ")."
                  + (f" Not listed twice: {', '.join(repeats)}." if repeats else ""))


def recover():
    """Put back deny entries lifted for a run that never finished (the server stopped mid-run)."""
    if not LIFT_MARKER.exists():
        return False
    try:
        marker = json.loads(LIFT_MARKER.read_text(encoding="utf-8"))
    except ValueError:
        marker = {}
    _restore_denies(marker.get("lifted") or [], marker.get("deny_before") or [])
    LIFT_MARKER.unlink(missing_ok=True)
    return True


def cmd_apply(rule, why, via):
    """Add one allow rule to .claude/settings.json (BL-75, BL-140: the colon form is normalised). Backed up to
    system/backups/, logged in permissions-log.jsonl and settings-log.jsonl; refused if blanket or already allowed.
    """
    rule = normalise(rule)                                 # BL-140: the colon form is added in the proper form
    why = re.sub(r"\s+", " ", (why or "").strip())
    if not why or len(why) > 300:
        sys.exit("creaite: say why the rule is needed, in up to 300 characters (--why)")
    settings = read_settings()
    ok, reason, covered = check(rule, settings)
    if not ok:
        print(f"Not added: already allowed by {covered}." if covered else f"Not added: {reason}.")
        return 1
    written = real_rule(rule)
    settings.setdefault("permissions", {}).setdefault("allow", []).append(written)
    n = len([e for e in log_entries() if e.get("op") == "add"]) + 1
    text = json.dumps(settings, indent=2, ensure_ascii=False) + "\n"
    backup = write_settings(text, datetime.now().strftime("%Y-%m-%d-%H%M%S"))
    log({"id": n, "at": now(), "op": "add", "rule": written, "why": why, "via": via, "backup": backup,
         "after": hashlib.sha256(text.encode()).hexdigest()[:16]})
    settings_log("claude_permissions.allow", None, written)
    print(f"Added {written} to .claude/settings.json (change {n}; the file before is {backup}). "
          "Undo it with: python3 system/scripts/permissions.py undo")
    return 0


def cmd_projects_root(why, via):
    """Add the projects root to permissions.additionalDirectories (BL-93), so Claude Code may read the project documents there."""
    why = re.sub(r"\s+", " ", (why or "").strip())
    if not why or len(why) > 300:
        sys.exit("creaite: say why, in up to 300 characters (--why)")
    if not paths.external():
        print("Not added: the projects are in the vault (locations.projects_root is not set), which Claude Code already reads.")
        return 1
    entry = str(paths.locations()["projects_root"]).strip().rstrip("/")
    settings = read_settings()
    dirs = settings.setdefault("permissions", {}).setdefault("additionalDirectories", [])
    if entry in dirs:
        print(f"Already allowed: {entry} is in permissions.additionalDirectories.")
        return 1
    dirs.append(entry)
    n = len([e for e in log_entries() if e.get("op") == "add"]) + 1
    text = json.dumps(settings, indent=2, ensure_ascii=False) + "\n"
    backup = write_settings(text, datetime.now().strftime("%Y-%m-%d-%H%M%S"))
    log({"id": n, "at": now(), "op": "add", "kind": "dir", "rule": entry, "why": why, "via": via, "backup": backup,
         "after": hashlib.sha256(text.encode()).hexdigest()[:16]})
    settings_log("claude_permissions.additionalDirectories", None, entry)
    print(f"Added {entry} to permissions.additionalDirectories (change {n}; the file before is {backup}). "
          "Undo it with: python3 system/scripts/permissions.py undo")
    return 0


def cmd_undo():
    """Undo the latest change made through permissions.py, if nothing has changed it since. BL-265: one function per kind."""
    entries = log_entries()
    undone = {e.get("undoes") for e in entries if e.get("op") == "undo"}
    last = next((e for e in reversed(entries) if e.get("op") in ("add", "remove", "set", "script", "file") and e.get("id") not in undone), None)
    if not last:
        print("Nothing to undo.")
        return 0
    n = next_id(entries)
    undo = {"set": _undo_setting, "file": _undo_file, "script": _undo_script}.get(last["op"], _undo_list_rule)
    return undo(last, n)


def _undo_setting(last, n):
    """A setting: put the old value back, if nobody has changed it since."""
    cur = paths.load_settings()
    found, now_value = settings_value(cur, last["key"])
    if not found or now_value != last["new"]:
        print(f"Not undone: {last['key']} has been changed since, so it is left alone.")
        return 1
    node = cur
    parts = last["key"].split(".")
    for part in parts[:-1]:
        node = node[part]
    node[parts[-1]] = last["old"]
    shutil.copy2(paths.SETTINGS, paths.free_path(paths.BACKUPS, f"settings-{stamp()}", ".json"))   # BL-266
    paths.SETTINGS.write_text(json.dumps(cur, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    log({"id": n, "at": now(), "op": "undo", "undoes": last["id"], "rule": last["rule"], "backup": None})
    settings_log(last["key"], last["new"], last["old"])
    print(f"Put {last['key']} back to {json.dumps(last['old'])}.")
    return 0


def _undo_file(last, n):
    """A permission file edited by a confirmed run: back, if nobody has changed it since."""
    target = paths.ROOT / next(k for k, v in FILE_TARGETS.items() if v == last["file"])
    if _sha(target) != last["after"]:
        print(f"Not undone: {paths.rel(target)} has been changed since, so it is left alone. The earlier version is {last['backup']}.")
        return 1
    if last["backup"]:
        restored = json.loads((paths.ROOT / last["backup"]).read_text(encoding="utf-8"))
        if last["file"] == "settings":                    # the earlier file, keeping whatever deny entries are in force now
            keep = (read_file("settings").get("permissions") or {}).get("deny") or []
            restored.setdefault("permissions", {})["deny"] = list(dict.fromkeys((restored.get("permissions") or {}).get("deny", []) + keep))
        target.write_text(json.dumps(restored, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    else:
        target.unlink()
    log({"id": n, "at": now(), "op": "undo", "undoes": last["id"], "rule": last["rule"], "backup": last["backup"]})
    settings_log(f"permission_file:{paths.rel(target)}", "edited", None)
    print(f"Put the earlier {paths.rel(target)} back.")
    return 0


def _undo_script(last, n):
    """permissions.py replaced: the earlier one back, if nobody has changed it since."""
    target = paths.ROOT / "system" / "scripts" / "permissions.py"
    if hashlib.sha256(target.read_bytes()).hexdigest()[:16] != last["after"]:
        print("Not undone: permissions.py has been changed since, so it is left alone.")
        return 1
    shutil.copy2(paths.ROOT / last["backup"], target)
    log({"id": n, "at": now(), "op": "undo", "undoes": last["id"], "rule": last["rule"], "backup": last["backup"]})
    settings_log("system/scripts/permissions.py", "replaced", None)
    print("Put the earlier permissions.py back.")
    return 0


def _undo_list_rule(last, n):
    """A rule added or removed: take it out or put it back (only that one; anything Alan added since stays)."""
    which = last.get("file") or "settings"
    key = LISTS.get(last.get("kind") if last.get("kind") in LISTS else "allow") if last.get("kind") != "dir" else "additionalDirectories"
    settings = read_file(which)
    lst = (settings.get("permissions") or {}).get(key, [])
    adding_back = last["op"] == "remove"
    changed = (last["rule"] not in lst) if adding_back else (last["rule"] in lst)
    backup = None
    if changed:
        if adding_back:
            lst.append(last["rule"])
        else:
            lst.remove(last["rule"])
        settings.setdefault("permissions", {})[key] = lst
        backup = write_file(which, settings, stamp())
    log({"id": n, "at": now(), "op": "undo", "undoes": last["id"], "rule": last["rule"], "backup": backup})
    settings_log("claude_permissions." + key, None if adding_back else last["rule"], last["rule"] if adding_back else None)
    where = paths.rel(FILES[which])
    if adding_back:
        print(f"Put {last['rule']} back in {where}" if backup else f"{last['rule']} was already back in {where}; the change is marked undone.")
    else:
        print(f"Removed {last['rule']} from {where}" if backup else
              f"{last['rule']} was already gone from {where}; the change is marked undone.")
    return 0


def cmd_list(as_json):
    """Print the allow and deny counts and every logged permission change, or all of it as JSON."""
    settings = read_settings()
    entries = log_entries()
    undone = {e.get("undoes") for e in entries if e.get("op") == "undo"}
    added = [e for e in entries if e.get("op") in ("add", "remove", "set", "script", "file")]
    data = {"allow": settings.get("permissions", {}).get("allow", []), "deny": settings.get("permissions", {}).get("deny", []),
            "directories": settings.get("permissions", {}).get("additionalDirectories", []),
            "changes": [{**e, "undone": e["id"] in undone} for e in added]}
    if as_json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0
    print(f"{len(data['allow'])} allow rules, {len(data['deny'])} deny rules.")
    for e in data["changes"]:
        print(f"{e['at']}  {'(undone) ' if e['undone'] else ''}{'' if e['op'] == 'add' else e['op'] + ' '}{e['rule']} — {e['why']} [{e['via']}]")
    if not data["changes"]:
        print("No rules have been added through permissions.py.")
    return 0


def main(argv):
    """Run the permissions command in `argv` (see the module docstring)."""
    cmd, args = (argv[0], argv[1:]) if argv else ("", [])
    if cmd == "check" and len(args) == 1:
        print(json.dumps(check_full(args[0]), ensure_ascii=False))          # BL-140: with the normalised rule and its state
        return 0
    if cmd == "apply" and args:
        opts = dict(zip(args[1::2], args[2::2]))
        return cmd_apply(args[0], opts.get("--why", ""), opts.get("--via", "cli"))
    if cmd == "recover" and not args:
        print("Put the lifted deny entries back." if recover() else "Nothing to recover.")
        return 0
    if cmd == "preview" and len(args) == 1:
        print(json.dumps(preview(args[0]), ensure_ascii=False))
        return 0
    if cmd == "edit" and args:
        opts = dict(zip(args[1::2], args[2::2]))
        return cmd_edit(args[0], opts.get("--why", ""), opts.get("--via", "cli"))
    if cmd == "projects-root":
        opts = dict(zip(args[0::2], args[1::2]))
        return cmd_projects_root(opts.get("--why", ""), opts.get("--via", "cli"))
    if cmd == "undo" and not args:
        return cmd_undo()
    if cmd == "list":
        return cmd_list("--json" in args)
    print(__doc__)
    return 2


if __name__ == "__main__":
    try:
        import log as debuglog  # BL-102: the debug log (not `log`: some scripts have a function of that name); a script runs without it
    except ImportError:
        debuglog = None
    sys.exit(debuglog.main("permissions.py", main, sys.argv[1:]) if debuglog else main(sys.argv[1:]))
