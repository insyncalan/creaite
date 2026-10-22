"""F3 (2.6.4): the people table's logic, with no database and no files of its own except the laptop's private file.

What this module does (the database writes are tracker.py's, see dev/proposals/f3/):
  parse_register(text)      the register's People table to people (with stable IDs), the private values (VIP, Hidden) and flags
  render_register(people)   the Markdown copy of the table: readable, round-trips, never carries VIP or Hidden
  plan_import(old, new)     what an import would insert, update, remove or re-key, for the preview and the write
  load_private / save_private / overlay  VIP and Hidden, kept on this laptop only (system/staging/people-private.json)

A person: {id, id_source ("email" or "name"), name, emails[], aliases[], org, role, labels[], extra{}}. The first address is the
primary one and sets the ID. VIP and Hidden are never part of a person, never in the Markdown copy and never in the backup zip.
"""
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
import person_id as pid_mod  # noqa: E402

SHARED_COLUMNS = ("Full name", "Email", "Aliases", "Organisation", "Role", "Labels")
FIELD_OF = {"Full name": "name", "Email": "emails", "Aliases": "aliases", "Organisation": "org", "Role": "role", "Labels": "labels"}
PRIVATE_COLUMNS = ("Hidden", "VIP")
SECTION = "## People"
PRIVATE_FILE = "system/staging/people-private.json"
TEXT_FIELDS = ("name", "org", "role")
LIST_FIELDS = ("emails", "aliases", "labels")
MARK = "<!-- people-table: generated from the people table -->"
INTRO = ("# People register\n\n" + MARK + "\n\nThis copy is made from creaite's people table after each save, so Claude can read it. Change people "
         "on the People page or with cx-edit, not in this file. Personal settings for each person are not kept here: each laptop keeps its own.\n")


def _cells(line):
    """The cells of one Markdown table row, trimmed."""
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _clean(v):
    """A value safe for one table cell: no pipes or line breaks."""
    return str(v or "").replace("|", "/").replace("\r", " ").replace("\n", " ").strip()


def _split_list(text, seps=","):
    """A cell's comma (or comma and semicolon) list, without blanks."""
    return [a.strip() for a in re.split("[" + seps + "]", str(text or "")) if a.strip()]


def _table(lines):
    """(header index, [row indices]) of the People table, or None."""
    if SECTION not in lines:
        return None
    i = lines.index(SECTION) + 1
    while i < len(lines) and not lines[i].startswith("|"):
        if lines[i].startswith("## "):
            return None
        i += 1
    if i >= len(lines):
        return None
    rows, j = [], i + 2
    while j < len(lines) and lines[j].startswith("|"):
        rows.append(j)
        j += 1
    return i, rows


def is_generated(text):
    """Whether a register is the generated copy (it carries the mark and no Hidden or VIP column)."""
    return MARK in str(text or "")


def _yes(v):
    """Whether a cell says yes."""
    return str(v or "").strip().lower() in ("yes", "y", "true", "1")


def _vip(v):
    """The VIP kind in a cell, or "" for blank and the usual no words."""
    v = str(v or "").strip()
    return "" if v.lower() in ("", "no", "n", "false", "0", "-") else v


def parse_register(text):
    """(people, private, flags) from a register's text. Unknown columns are kept in each person's `extra`; Hidden and VIP are
    taken out into `private` ({id: {"hidden": bool, "vip": str}}, only for people who have one). A row with no name is skipped.
    A person with no email gets a name-based ID and a flag; a second row with the same address gets a name-based ID and a flag."""
    lines = text.splitlines()
    found = _table(lines)
    if not found:
        return [], {}, []
    head, rows_at = found
    cols = _cells(lines[head])
    people, private, flags, seen = [], {}, [], {}
    for i in rows_at:
        row = dict(zip(cols, _cells(lines[i]) + [""] * len(cols)))
        name = row.get("Full name", "").strip()
        if not name:
            continue
        emails = _split_list(row.get("Email"), ",;")
        p = {"name": name, "emails": emails, "aliases": _split_list(row.get("Aliases")), "org": row.get("Organisation", "").strip(),
             "role": row.get("Role", "").strip(), "labels": _split_list(row.get("Labels")),
             "extra": {c: row[c] for c in cols if c and c not in FIELD_OF and c not in PRIVATE_COLUMNS}}
        p["id"], p["id_source"] = pid_mod.id_for(name, emails[0] if emails else "")
        if p["id_source"] == "name":
            flags.append({"name": name, "id": p["id"], "reason": "no email: its ID comes from the name"})
        elif p["id"] in seen:
            flags.append({"name": name, "id": p["id"], "reason": f"same email as {seen[p['id']]}: its ID comes from the name"})
            p["id"], p["id_source"] = pid_mod.fallback_id(name), "name"
        if p["id"] in seen and p["id_source"] == "name":
            flags.append({"name": name, "id": p["id"], "reason": f"same name as {seen[p['id']]}: skipped"})
            continue
        seen[p["id"]] = name
        mine = {}
        if _yes(row.get("Hidden")):
            mine["hidden"] = True
        if _vip(row.get("VIP")):
            mine["vip"] = _vip(row.get("VIP"))
        if mine:
            private[p["id"]] = mine
        people.append(p)
    return people, private, flags


def _columns(people):
    """The shared columns, then every extra column some person carries, in the order first met."""
    cols = list(SHARED_COLUMNS)
    for p in people:
        cols += [c for c in (p.get("extra") or {}) if c not in cols]
    return cols


def _value(p, col):
    """One person's cell for a column."""
    f = FIELD_OF.get(col)
    if f in LIST_FIELDS:
        return _clean(", ".join(p.get(f) or []))
    return _clean(p.get(f) if f else (p.get("extra") or {}).get(col, ""))


def render_register(people, base_text=None):
    """The Markdown copy. With `base_text` (the file as it is) everything outside the People table is kept; Hidden and VIP columns
    in it are dropped. Without it a short plain file is made. The people are written in the order given."""
    cols = _columns(people)
    table = ["| " + " | ".join(cols) + " |", "|" + "|".join("-" * (len(c) + 2) for c in cols) + "|"] + \
            ["| " + " | ".join(_value(p, c) for c in cols) + " |" for p in people]
    if base_text is None:
        return INTRO + "\n" + SECTION + "\n\n" + "\n".join(table) + "\n"
    lines = base_text.splitlines()
    found = _table(lines)
    if found:
        head, rows_at = found
        lines[head:(rows_at[-1] if rows_at else head + 1) + 1] = table
    elif SECTION in lines:
        lines[lines.index(SECTION) + 1:lines.index(SECTION) + 1] = [""] + table
    else:
        lines += ["", SECTION, ""] + table
    return "\n".join(lines) + "\n"


def plan_import(existing, incoming):
    """What importing `incoming` into a table holding `existing` (both lists of people) would do:
    {insert: [people], update: [people], remove: [ids], rekeyed: [(old id, new id, name)], same: n}. A person whose name-based
    ID is gone and whose name now has an email ID is re-keyed (reported, and the old row removed), not inserted twice."""
    old = {p["id"]: p for p in existing}
    new_ids = {p["id"] for p in incoming}
    by_name = {pid_mod.normalise_name(p["name"]): p for p in existing if p.get("id_source") == "name"}
    plan = {"insert": [], "update": [], "remove": [], "rekeyed": [], "same": 0}
    rekeyed = set()
    for p in incoming:
        o = old.get(p["id"])
        if o is None:
            gone = by_name.get(pid_mod.normalise_name(p["name"]))
            if gone and gone["id"] not in new_ids and p["id_source"] == "email":
                plan["rekeyed"].append((gone["id"], p["id"], p["name"]))
                rekeyed.add(gone["id"])
            plan["insert"].append(p)
        elif _shared(o) != _shared(p):
            plan["update"].append(p)
        else:
            plan["same"] += 1
    plan["remove"] = [i for i in old if i not in new_ids]
    return plan


def _shared(p):
    """The fields that travel and are compared (never VIP or Hidden)."""
    return {k: p.get(k) for k in ("id", "id_source", "name", "emails", "aliases", "org", "role", "labels")} | \
           {"extra": p.get("extra") or {}}


def same_people(a, b):
    """Whether two lists of people hold the same shared fields in the same order."""
    return [_shared(p) for p in a] == [_shared(p) for p in b]


# ── The laptop's private file: VIP and Hidden, never shared ──────────────────────────────────────────────────────────

def private_path(root=None):
    """Where this laptop keeps VIP and Hidden, under the vault root (default: this vault)."""
    return Path(root or paths.ROOT) / PRIVATE_FILE


def load_private(path):
    """{id: {"hidden": bool, "vip": str}} from the private file; empty when it is missing or unreadable."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        raw = data.get("people") if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}
    out = {}
    for k, v in (raw or {}).items():
        if isinstance(v, dict) and (v.get("hidden") or v.get("vip")):
            out[str(k)] = {**({"hidden": True} if v.get("hidden") else {}), **({"vip": str(v["vip"])} if v.get("vip") else {})}
    return out


def save_private(path, private):
    """Write the private file in one step (a temporary file, then a rename), only people who have a value."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    keep = {k: v for k, v in sorted(private.items()) if v.get("hidden") or v.get("vip")}
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps({"version": 1, "people": keep}, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def merge_private(current, found):
    """The private values after an import: what the laptop already has, plus values found in an older register (the laptop's own
    always win, so a later import never undoes a choice made since)."""
    return {**found, **current}


def overlay(people, private):
    """The same people with this laptop's `hidden` and `vip` set, for readers that need them (never written to the table)."""
    out = []
    for p in people:
        mine = private.get(p.get("id"), {})
        out.append({**p, "hidden": bool(mine.get("hidden")), "vip": mine.get("vip", "")})
    return out
