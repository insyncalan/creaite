"""creaite dashboard build — writes dashboard.html from tracker.db, system/staging/ and the vault.

Usage: python3 system/scripts/build_dashboard.py
Embeds the data as <script type="application/json" id="data"> in system/templates/dashboard.html and writes
dashboard.html (vault root) plus system/history/dashboard-YYYY-MM-DD.html. Read-only on the database.
Called by tracker.py after every apply. Standard library only; the page needs no network.
"""
import base64
import contextlib
import json
import os
import re
import sqlite3
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
import linktext  # noqa: E402  (#121: links in plain text show as their words in the activity lines)
import review  # noqa: E402  (classification shared with cx-review: bulk rule, needs a project)
from docx_tools import md_normalise  # noqa: E402  (Current state is Markdown, BL-22, BL-47)
import propose  # noqa: E402  (register learning checks, BL-28)

TEMPLATE = paths.TEMPLATES / "dashboard.html"
FONTS = [(400, "roboto-400.ttf"), (500, "roboto-500.ttf"), (700, "roboto-700.ttf")]   # system/templates/vendor/ (OFL)
# Help's three faces (BL-84), Latin subsets as WOFF2, also in system/templates/vendor/ (OFL; help-fonts-OFL.txt).
# Only the weights the guides use. A missing file is skipped, and the page falls back to the system's fonts.
HELP_FONTS = [("Schibsted Grotesk", 500, "schibsted-grotesk-500.woff2"), ("Schibsted Grotesk", 700, "schibsted-grotesk-700.woff2"),
              ("Schibsted Grotesk", 800, "schibsted-grotesk-800.woff2"), ("Source Sans 3", 400, "source-sans-3-400.woff2"),
              ("Source Sans 3", 600, "source-sans-3-600.woff2"), ("JetBrains Mono", 500, "jetbrains-mono-500.woff2")]
IMAGE_LIMIT = 2 * 1024 * 1024        # per image embedded from a project's current state (BL-12)
IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif",
               ".webp": "image/webp", ".svg": "image/svg+xml"}
WEEK = 6                  # #162: the health trend shows six weeks, as the weekly report does
FIELD_LABELS = {"due_date": "due date", "client_visible": "client-visible", "client_message": "client messaging",
                "latest_update": "latest update", "response_action": "response", "health_reason": "health reason",
                "next_milestone": "next milestone", "milestone_date": "milestone date", "made_by": "made by",
                "baseline_date": "baseline", "forecast_date": "forecast", "sort_order": "order"}
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def shown(iso):
    """A stored date (YYYY-MM-DD, with any time after it) as shown: DD-MM-YYYY; anything else as it is, None as ""."""
    return f"{iso[8:10]}-{iso[5:7]}-{iso[0:4]}{iso[10:]}" if iso and re.match(r"\d{4}-\d{2}-\d{2}", iso) else (iso or "")


def rows(con, sql, *args):
    """The query's rows as plain dicts."""
    return [dict(r) for r in con.execute(sql, args)]


# ── Project memory (CLAUDE.md) ────────────────────────────────────────────────

def memory(folder):
    """Client, client-report rhythm and current state from a project's CLAUDE.md."""
    p = folder / "CLAUDE.md"
    raw = p.read_bytes().decode("utf-8") if p.exists() else ""      # a lone CR stays a character: the page reads the file the same way
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    client = re.search(_LEAD + r"Client / partner:\*\*[ \t]*([^\n]*)", _live_text(raw), re.M)
    rhythm = re.search(r"\*\*Client report rhythm:\*\*[ \t]*([A-Za-z]+)", text)
    cr = client_report_setting(raw)
    current, images = "", []
    m = re.search(r"^## Current state\s*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    if m:
        body = m.group(1)
        for alt, ref in re.findall(r"!\[([^\]]*)\]\(([^)\s]+)\)", body):   # images (BL-12), relative to the project;
            images.append(embed_image(folder, alt, ref))                   # their lines stay in place (BL-63)
        body = "\n".join(ln for ln in body.splitlines()
                         if not (ln.strip().startswith("_") and ln.strip().endswith("_") and len(ln.strip()) > 1))  # guidance
        current = md_normalise(body)   # Markdown kept: formats, lists (nested), headings, quotes, links, images (BL-63)
    return {"client": (client.group(1).strip()[:CLIENT_NAME_MAX] if client else ""),
            "rhythm": (rhythm.group(1).strip().capitalize() if rhythm else "Weekly"),
            **cr, "current": current, "images": [i for i in images if i], "cstitle": cs_title(text)}


# ===== H3 (#221): "This project needs a separate client report" =====
# Three lines in the project's CLAUDE.md beside the rhythm, written by the dashboard's settings save: "**Client report:** on|off",
# "**Client report reminder:** on|off" and "**Client report logos:** firm, client, partner". A missing line is the old behaviour:
# the client report on (existing projects), its reminder on and every logo. A new project is made with the report off.
# #228 B: a fourth line, "**Partners:** Org A; Org B", lists the partner organisations; each has its own logo kind `partner:<slug>`.


_LEAD = r"^[ \t]*(?:[-*][ \t]+)?\*\*"       # a setting line starts at the line's start (the way the page's memLineEdit reads it)
CLIENT_NAME_MAX = 80


def _live_text(text):
    """The memory text without its code fences and quoted lines (#233 L4: a line shown as an example is not the setting)."""
    out, fence = [], ""
    for line in (text or "").split("\n"):
        f = re.match(r" {0,3}(`{3,}|~{3,})", line)
        if fence:
            if f and f.group(1)[0] == fence[0] and len(f.group(1)) >= len(fence) and re.fullmatch(r" {0,3}[`~]+\s*", line.rstrip("\r")):
                fence = ""
            continue
        if f:
            fence = f.group(1)
            continue
        if not line.lstrip(" \t").startswith(">"):
            out.append(line)
    return "\n".join(out)


def _on_off(text, label, default=True):
    """True or False from a "**<label>:** on|off" line; `default` when there is none."""
    text = _live_text(text)
    m = re.search(_LEAD + re.escape(label) + r":\*\*[ \t]*([A-Za-z]+)", text or "", re.M)
    return default if not m else m.group(1).strip().lower() != "off"


PARTNERS_MAX = 12            # the most partner organisations one project lists (one logo each)
PARTNER_NAME_MAX = 60
PARTNER_PUNCT = ".,&'()-"    # besides letters, digits and the space (#228 C; the page's core/partners.js says the same)
PARTNER_LINE_SCAN = 5000     # a longer value is not read past this


def partner_name_problem(name):
    """A plain-words problem with a partner organisation's name, or "" when it is allowed: 1 to 60 characters, Unicode letters and
    digits, spaces and . , & ' - ( ) only; no control, separator, bidi or zero-width character, no leading or trailing space, no
    double space. `name` is taken as given (clean_partner_name makes the usual tidy-up first)."""
    import unicodedata
    t = str(name)
    if not t:
        return "Type the partner organisation's name."
    if "\n" in t or "\r" in t:
        return "A partner's name is one line."
    if ";" in t:
        return "A partner's name can't contain a semicolon; add each partner on its own."
    if len(t) > PARTNER_NAME_MAX:
        return f"A partner's name is over {PARTNER_NAME_MAX} characters."
    if t != t.strip(" ") or "  " in t:
        return "A partner's name has no space at either end and no double space."
    if t != unicodedata.normalize("NFC", t):
        return "A partner's name uses letters and digits only (no separate accent marks)."
    for ch in t:
        cat = unicodedata.category(ch)
        if ch == " " or ch in PARTNER_PUNCT or cat[0] == "L" or cat == "Nd":
            continue
        return "A partner's name uses letters, digits, spaces and . , & ' - ( ) only."
    return ""


def clean_partner_name(raw):
    """The usual tidy-up of a typed name: Unicode NFC, and runs of spaces made one, none at either end. Nothing else is changed."""
    import unicodedata
    return re.sub(r" {2,}", " ", unicodedata.normalize("NFC", str(raw))).strip(" ")


def partner_key(name):
    """What makes two names the same organisation: letters and digits only, accents and capitals folded."""
    import unicodedata
    folded = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "", folded) or str(name).casefold()


def _slug_of(name):
    """A partner organisation's name as a file-name slug: lower case, letters and digits joined by single hyphens, accents folded,
    at most 40 characters. A name with no letter or digit in it (another script) gets `x` and six hex digits of its own hash, so the
    slug is never empty and stays the same. A slug ending in `original` gets `-x`, so no partner's file can be another's `-original`."""
    import hashlib
    import unicodedata
    folded = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", folded.lower()).strip("-")[:40].strip("-")
    if not slug:
        return "x" + hashlib.sha1(str(name).encode("utf-8")).hexdigest()[:6]
    return slug[:38].strip("-") + "-x" if re.search(r"(^|-)original$", slug) else slug


def partners_of(text):
    """[{name, slug}] from a CLAUDE.md's "- **Partners:** Org A; Org B" line, in line order. A name that breaks partner_name_problem
    is skipped (never an error), as is a repeat of an earlier one (any capitals, accents or punctuation) and one whose slug an
    earlier name already has; at most PARTNERS_MAX. The one place a slug is made: the server sends it to the page."""
    m = re.search(_LEAD + r"Partners:\*\*[ \t]*([^\n]*)", _live_text(text), re.M)
    out, seen, keys = [], set(), set()
    for raw in (m.group(1)[:PARTNER_LINE_SCAN].rstrip("\r").split(";") if m else []):
        name = clean_partner_name(raw)
        if not name or partner_name_problem(name) or partner_key(name) in keys:
            continue
        slug = _slug_of(name)
        if slug in seen:
            continue
        seen.add(slug)
        keys.add(partner_key(name))
        out.append({"name": name, "slug": slug})
        if len(out) >= PARTNERS_MAX:
            break
    return out


def logo_kinds_of(partners):
    """The logo kinds a project has, the firm's first: firm, client, then one `partner:<slug>` for each partner in line order, or the
    one old `partner` when it lists none."""
    return ["firm", "client"] + ([f"partner:{p['slug']}" for p in partners] or ["partner"])


def client_report_setting(text):
    """{client_report, client_reminder, logos, partners} from a CLAUDE.md text; the firm's logo is always in `logos`. A partner's logo
    is `partner:<slug>`; a bare `partner` in the line means every partner (no line at all: everything is ticked)."""
    m = re.search(_LEAD + r"Client report logos:\*\*[ \t]*([^\n]*)", _live_text(text), re.M)
    partners = partners_of(text)
    kinds = logo_kinds_of(partners)
    chosen = {w.strip().lower() for w in m.group(1).split(",")} if m else set(kinds)
    if "partner" in chosen:
        chosen |= {k for k in kinds if k.startswith("partner")}
    return {"client_report": _on_off(text, "Client report"), "client_reminder": _on_off(text, "Client report reminder"),
            "logos": [k for k in kinds if k == "firm" or k in chosen], "partners": partners}


def client_gap(p):
    """Days between client reports for a project dict ({rhythm, client_report?, client_reminder?}); None when it needs no client
    reminder: its rhythm is off, it needs no separate client report, or its reminder is off."""
    # the dashboard's own project dicts carry the same two switches as `cr` and `crrem` (the keys of its JSON); read either, default on
    if not p.get("client_report", p.get("cr", True)) or not p.get("client_reminder", p.get("crrem", True)):
        return None
    return {"Weekly": 7, "Fortnightly": 14, "Monthly": 30}.get(p["rhythm"])
# ===== end H3 =====


# ===== BL-162 (sprint-rail) ===== the Current state card's title, a label for the dashboard only. A header line in the project's
# CLAUDE.md, "**Current state title:** Where we are", beside the client-report rhythm; the "## Current state" section keeps its
# name, so the reports, Generate, Make it executive, search and the checks still find it.
CS_TITLE_DEFAULT = "Current state"
CS_TITLE_MAX = 40


def cs_title(text):
    """The card's title from a CLAUDE.md text: trimmed, Markdown and line breaks taken out, at most 40 characters; the
    default when the line is missing or empty."""
    m = re.search(r"\*\*Current state title:\*\*[ \t]*([^\n]*)", text or "")
    t = m.group(1) if m else ""
    t = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", t)              # a link or an image: its words
    t = re.sub(r"[*_`#>~|\\]", "", t)                                 # emphasis, code, headings, quotes
    t = re.sub(r"\s+", " ", t).strip()[:CS_TITLE_MAX].strip()
    return t or CS_TITLE_DEFAULT
# ===== end BL-162 =====


def embed_image(folder, alt, ref):
    """An image from the project folder as a data URI, so the page needs no file access; None if unusable."""
    f = paths.resolve_image(folder, ref).resolve()
    if folder.resolve() not in f.parents or not f.is_file() or f.suffix.lower() not in IMAGE_TYPES:
        print(f"Note: current-state image not found or not an image: {paths.rel(folder)}/{ref}")
        return None
    if f.stat().st_size > IMAGE_LIMIT:
        print(f"Note: {paths.rel(f)} is over 2 MB; not shown on the dashboard")
        return None
    data = base64.b64encode(f.read_bytes()).decode("ascii")
    return {"alt": alt, "ref": ref, "src": f"data:{IMAGE_TYPES[f.suffix.lower()]};base64,{data}"}


# ── Sections of the data ──────────────────────────────────────────────────────

def trail(con, code, today):
    """Health for the last 6 week-ending Fridays, oldest first ('' where no update was approved)."""
    return [h for h, _ in trail_weeks(con, code, today)]


def trail_dates(today):
    """The week-ending Fridays the trend covers, oldest first (YYYY-MM-DD)."""
    friday = today - timedelta(days=(today.weekday() - 4) % 7)
    return [(friday - timedelta(weeks=i)).isoformat() for i in range(WEEK - 1, -1, -1)]


def trail_weeks(con, code, today):
    """#162: (health, reason) for the last 6 week-ending Fridays, oldest first; ('', '') where no update was approved. The reason is
    the week's stored update summary, cut to one line for the tooltip."""
    weeks = trail_dates(today)
    found = {r["week_ending"]: r for r in rows(con, "SELECT week_ending, health, summary FROM updates WHERE project = ?", code)}
    short = {"On track": "ok", "At risk": "warn", "Off track": "bad"}
    out = []
    for w in weeks:
        r = found.get(w)
        why = " ".join((r["summary"] or "").split()) if r else ""
        out.append((short.get(r["health"], "") if r else "", why if len(why) <= 160 else why[:159].rstrip() + "…"))
    return out


def milestones(con, project, actions):
    """[name, date, status, id, baseline, progress%, tracker status, order, forecast, updated_at, set %, calculated %,
    progress note, description, BL-186 detail] per milestone (editing, BL-23; % complete, BL-29); the cockpit's slip: the largest
    variance of an open milestone against its Agreed date (BL-186)."""
    import tracker
    ms, slip = [], 0
    found = rows(con, "SELECT * FROM milestones WHERE project = ? AND status != 'Cancelled' ORDER BY sort_order, "
                      "COALESCE(forecast_date, baseline_date), id", project["code"])
    events = tracker.milestone_events(con, [m["id"] for m in found])
    import forecast                                     # BL-184: the slip range (internal; Movement only)
    likely = forecast.ranges(con, {m["id"] for m in found})
    today = date.today()
    for m in found:
        when = m["forecast_date"] or m["baseline_date"] or ""
        late = bool(m["baseline_date"] and m["forecast_date"] and m["forecast_date"] > m["baseline_date"])
        state = tracker.milestone_state(m)
        status = "done" if m["status"] == "Done" else "slip" if (late or state in ("Slipped", "Overdue")) else ""
        linked = [a for a in actions if a["ms"] == m["id"] and a["st"] != "Cancelled"]
        closed = sum(a["st"] == "Closed" for a in linked)
        calc = round(100 * closed / len(linked)) if linked else None
        pc = m.get("percent_complete")
        if pc is not None:
            when_set = rows(con, "SELECT at FROM change_log WHERE tbl = 'milestones' AND item_id = ? AND "
                                 "field = 'percent_complete' ORDER BY rowid DESC LIMIT 1", m["id"])
            me = (paths.load_settings().get("identity") or {}).get("name") or "you"
            note = f"{pc}%, set by {me.split()[0]}" + (f" on {shown(when_set[0]['at'][:10])}" if when_set else "")
        else:
            note = f"{calc}%, {closed} of {len(linked)} linked action{'s' if len(linked) != 1 else ''} closed" if linked else ""
        ms.append([m["name"], when, status, m["id"], m["baseline_date"], pc if pc is not None else calc,
                   m["status"], m["sort_order"], m["forecast_date"], m["updated_at"], pc, calc, note, m.get("description") or "",
                   {**milestone_detail(con, m, events.get(m["id"], []), today), "range": likely.get(m["id"]),
                    "src": m.get("source")}])
        if m["status"] == "Planned" and m["baseline_date"]:
            agreed = date.fromisoformat(m["baseline_date"])
            expected = max(date.fromisoformat(m["forecast_date"] or m["baseline_date"]), today if agreed < today else agreed)
            slip = max(slip, (expected - agreed).days)
    if not ms and project.get("next_milestone"):
        ms.append([project["next_milestone"], project.get("milestone_date") or "", "", None, None, None])
    return ms, slip


# ===== BL-186 (sprint-milestones) ===== each milestone's state (the one reading in tracker.py: milestone_state, suggested_state,
# client_milestones), the client's word, the Original date, and the history Movement needs: the forecast and agreed date at the end
# of each reporting week (Friday) and a "What changed" log with the reason given. Built from change_log, read only.
MS_HIST_WEEKS = 26


def milestone_detail(con, m, events, today):
    """One milestone's detail for the dashboard (BL-162): its state and suggested state, the original and agreed dates,
    the forecast, client visibility and wording, how often it moved and whether it was re-baselined, a weekly history of
    its dates, and a log of its changes, one entry per apply, with why."""
    import tracker
    st, sug = tracker.milestone_state(m), tracker.suggested_state(m)
    orig = tracker.milestone_original(con, m["id"], m["baseline_date"])
    cvis = bool(tracker.client_milestones([m]))
    log, moves, rb = [], 0, None
    by_apply = {}
    for e in events:
        by_apply.setdefault(e["apply_id"], []).append(e)
    for aid, es in by_apply.items():
        f = {e["field"]: e for e in es}
        note = (f.get("note") or {}).get("new") or ""
        via = es[0]["via"] or ""
        why = note or {"dashboard": "From the dashboard", "cx-edit": "With cx-edit", "excel-import": "From Excel", "migrate": "Migration",
                       "assistant": "From ask creaite"}.get(via, "Applied")
        d = es[0]["at"][:10]
        if es[0]["op"] == "insert":
            continue
        if "baseline_date" in f and f["baseline_date"]["old"]:
            o, n = f["baseline_date"]["old"], f["baseline_date"]["new"]
            dm = re.search(r"\b[A-Z][A-Z0-9]{2,6}-D-\d{3}\b", note)
            rb = {"date": d, "from": orig or o, "decision": dm.group(0) if dm else ""}
            fcn = (f.get("forecast_date") or {}).get("new")
            log.append({"d": d, "c": f"Rebaselined: agreed date {shown(o)} to {shown(n)}" + (f", forecast {shown(fcn)}" if fcn and fcn != n else ""),
                        "w": why, "k": "rb"})
            moves += 1
        if "forecast_date" in f and f["forecast_date"]["old"] and f["forecast_date"]["new"] and not (rb and rb["date"] == d and "baseline_date" in f):
            o, n = f["forecast_date"]["old"], f["forecast_date"]["new"]
            dd = (date.fromisoformat(n) - date.fromisoformat(o)).days
            log.append({"d": d, "c": f"Forecast moved {shown(o)} to {shown(n)} ({'+' if dd > 0 else ''}{dd} days)", "w": why, "k": "mv"})
            moves += 1
        if "status" in f and f["status"]["new"] == "Done":
            a = (f.get("actual_date") or {}).get("new") or d
            log.append({"d": d, "c": f"Achieved on {shown(a)}", "w": why, "k": "dn"})
        elif "state" in f or "status" in f:
            o, n = (f.get("state") or {}).get("old"), (f.get("state") or {}).get("new")
            if "status" in f and f["status"]["old"] == "Done":
                log.append({"d": d, "c": f"Reopened{(' as ' + n) if n else ''}", "w": why, "k": "st"})
            elif "state" in f:
                r = (f.get("state_reason") or {}).get("new") or ""
                log.append({"d": d, "c": f"State changed {o or 'following the dates'} to {n or 'following the dates'}",
                            "w": r or why, "k": "st"})
    hist = []
    if events:
        first = date.fromisoformat(events[0]["at"][:10])
        friday = first + timedelta(days=(4 - first.weekday()) % 7)
        last = today + timedelta(days=(4 - today.weekday()) % 7)
        weeks = []
        while friday <= last:
            weeks.append(friday)
            friday += timedelta(days=7)
        weeks = weeks[-MS_HIST_WEEKS:]
        for w in weeks:
            fc = ag = None
            for e in events:
                if e["at"][:10] > w.isoformat():
                    break
                if e["field"] == "forecast_date":
                    fc = e["new"]
                elif e["field"] == "baseline_date":
                    ag = e["new"]
            if fc or ag:
                hist.append([w.isoformat(), fc or ag, ag or fc])
    return {"st": st, "sug": sug, "set": bool(m.get("state_set")), "why": m.get("state_reason") or "", "owner": m.get("owner") or "",
            "actual": m.get("actual_date") or "", "client": bool(m.get("client_visible")), "cw": m.get("client_message") or "",
            "cword": tracker.MS_CLIENT_WORD[st], "cvis": cvis, "orig": orig or "", "agr": m["baseline_date"] or "",
            "fc": m["forecast_date"] or m["baseline_date"] or "", "pc": m.get("percent_complete"), "moves": moves, "rb": rb,
            "hist": hist, "log": log, "note": m.get("internal_note") or ""}   # the note: internal only, Movement shows it
# ===== end BL-186 =====


def stakeholders():
    """{code: [names]} from the register's Key stakeholders and Shared stakeholders (BL-18 A: pickers list a
    project's own people first). Roles in brackets are dropped."""
    out, section = {}, ""
    text = paths.REGISTER.read_text(encoding="utf-8") if paths.REGISTER.exists() else ""
    for line in text.splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        if not line.startswith("|") or set(line) <= set("|-: "):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        names = lambda t: [re.sub(r"\s*\(.*?\)", "", n).strip() for n in t.split(",") if n.strip()]  # noqa: E731
        if section == "Projects" and len(cells) >= 5 and re.fullmatch(r"[A-Z][A-Z0-9]{2,6}", cells[0]):
            out.setdefault(cells[0], []).extend(names(cells[4]))
        elif section.startswith("Shared") and len(cells) >= 3 and cells[1].lower() == "stakeholder":
            for code in re.findall(r"[A-Z][A-Z0-9]{2,6}", cells[2]):
                out.setdefault(code, []).extend(names(cells[0]))
    return out


def commands():
    """ask creaite suggestions (BL-24): each skill's trigger phrases and the CLAUDE.md command table, gathered at
    build so new skills appear automatically. Dates in examples are shown DD-MM-YYYY."""
    out, seen = [], set()

    def add(phrase, skill):
        """Add a suggested phrase (placeholders as <name>, dates as DD-MM-YYYY) for a skill, once, if it is short
        enough."""
        phrase = re.sub(r"\[([^\]]+)\]", r"<\1>", phrase.strip().rstrip("."))
        phrase = re.sub(r"\b(\d{4})-(\d{2})-(\d{2})\b", r"\3-\2-\1", phrase)
        if phrase and phrase.lower() not in seen and len(phrase) <= 80:
            seen.add(phrase.lower())
            out.append({"t": phrase, "s": skill})
    for f in sorted((paths.ROOT / ".claude" / "skills").glob("*/SKILL.md")):
        m = re.search(r"^description:\s*(.*)$", f.read_text(encoding="utf-8"), re.M)
        if m and "Use " in m.group(1):
            for phrase in re.findall(r"“([^”]+)”|\"([^\"]+)\"", m.group(1).split("Use ", 1)[1]):
                add(phrase[0] or phrase[1], f.parent.name)
    table = paths.RULES if paths.RULES.exists() else paths.ROOT / "CLAUDE.md"    # BL-36: the skills table's home
    for line in (table.read_text(encoding="utf-8") if table.exists() else "").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.startswith("| \"") else []
        if len(cells) >= 2:
            skill = re.search(r"\*\*(cx-[\w-]+)\*\*", cells[1])
            for phrase in re.findall(r"\"([^\"]+)\"", cells[0]):
                add(phrase, skill.group(1) if skill else "creaite")
    return out


def files(folders, documents=False):
    """The vault's file index: project folders, _portfolio and inbox (system/ and dev/ excluded). Documents are set aside
    unless `documents` (dashboard.files_show_documents): not listed, and not walked (BL-87). Reports carry their folder in `sub`."""
    out = []

    def add(p, kind, f, sub=""):
        """Add a file to the Files list: its project, folder kind, size, type, date (from its name, or the meeting's),
        last change and vault path. Hidden files, Office lock files and folders are skipped."""
        if f.name.startswith((".", "~$")) or not f.is_file():
            return
        out.append({"p": p, "f": kind, "n": f.name, "kb": max(1, round(f.stat().st_size / 1024)), "sub": sub,
                    "type": f.suffix.lstrip(".").lower(), "date": paths.file_date(f)[0] if kind in ("minutes", "transcripts") else (paths.name_date(f.name)[0] or ""),
                    "mod": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d"),     # BL-87: orders Latest reports when a name has no date
                    "path": paths.rel(f)})            # BL-85: a Teams name's date; a meeting without one takes the file's date

    for code in folders:
        for f, kind, sub in paths.project_files(code, online=True, documents=documents):             # online-only files are listed, never read
            add(code, kind, f, sub)
    if paths.portfolio_dir().is_dir():
        for f, kind, sub in paths.project_files("_portfolio", online=True, documents=False):
            if kind in ("minutes", "transcripts", "notes"):            # BL-301 B: portfolio notes are listed too
                add("_portfolio", kind, f)
    if paths.INBOX.is_dir():
        for f in sorted(paths.INBOX.iterdir()):
            add("inbox", "", f)
    return out


def archived_files(folders):
    """BL-331: the reports and minutes BL-03 archived that are still in their _Archive, for the listed projects and the portfolio
    (archive.archived_files: names, sizes and dates from the apply records; nothing in _Archive is read or indexed)."""
    import archive
    return [f for f in archive.archived_files() if f["p"] in folders or f["p"] == "_portfolio"]


INBOX_TYPES = (".vtt", ".docx", ".txt", ".md", ".pdf")


def register_signals():
    """[(code, [lower-case words that suggest it])] from the register: code, name, aliases, keywords."""
    out = []
    text = paths.REGISTER.read_text(encoding="utf-8") if paths.REGISTER.exists() else ""
    section = ""
    for line in text.splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.startswith("|") else []
        if section == "Projects" and len(cells) >= 8 and re.fullmatch(r"[A-Z][A-Z0-9]{2,6}", cells[0]):
            words = [cells[1]] + [w for c in (cells[3], cells[7]) for w in c.split(",")]
            out.append((cells[0], [w.strip().lower() for w in words if len(w.strip()) > 2]))
    return out


def inbox(projects):
    """Files waiting in inbox/ for the Inbox view (BL-42): type, size, likely project and state."""
    if not paths.INBOX.is_dir():
        return []
    import hashlib
    signals = register_signals()
    codes = {p["code"] for p in projects}
    drafts = {}
    for p, data in review.proposals():
        m = data.get("meeting") or {}
        if m.get("transcript") and not m.get("applied"):
            drafts[m["transcript"]] = p.name
    filed = {}
    for f in paths.PROJECTS.glob("*/transcripts/*"):
        if f.is_file():
            filed.setdefault(f.stat().st_size, []).append(f)
    out = []
    for f in sorted(paths.INBOX.iterdir()):
        if not f.is_file() or f.name.startswith(".") or f.suffix.lower() not in INBOX_TYPES:
            continue
        name, rel = f.name.lower(), paths.rel(f)
        likely = next((c for c in sorted(codes, key=len, reverse=True) if re.search(rf"(?<![A-Za-z0-9]){c}(?![A-Za-z0-9])", f.name)),
                      None) or next((c for c, words in signals if c in codes and any(w in name for w in words)), None)
        digest = None
        if f.stat().st_size in filed:
            digest = hashlib.sha256(f.read_bytes()).hexdigest()
        done = digest and any(hashlib.sha256(g.read_bytes()).hexdigest() == digest for g in filed[f.stat().st_size])
        state = "draft" if rel in drafts else "processed" if done else "new"
        import minutes, transcripts                       # a transcript or chat loaded from the calendar (BL-42 phase 3) carries its event ID
        eid = transcripts.file_event_id(f) if f.suffix.lower() in (".vtt", ".txt") else None
        if eid and f.name.endswith(" - chat.txt"):
            state = "chat"                                # it goes with its transcript and is never processed alone
        elif eid and state == "new" and minutes.processed_on(f"calendar:{eid}"):
            state = "processed"
        out.append({"name": f.name, "path": rel, "ext": f.suffix.lower()[1:], "size": f.stat().st_size,
                    "date": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d"), "p": likely, "state": state,
                    "event": eid, "uploaded": eid is None})      # BL-137: Upload files lists the uploaded files; one with a recorded event ID was loaded from the calendar
    return out


# ── BL-133 stage B (sprint-work-views): possible duplicates, and reject reasons in Activity ──
DUP_STOP = {"a", "an", "the", "and", "or", "of", "to", "for", "on", "in", "at", "by", "with", "from", "is", "be", "are", "it", "its",
            "this", "that", "we", "our", "you", "your", "they", "their", "as", "up", "out", "into", "about", "re", "fw", "please"}


def dup_tokens(text):
    """Normalised words of an item's text: lower case, stop words out, a plural's s dropped."""
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {w[:-1] if len(w) > 3 and w.endswith("s") else w for w in words if w not in DUP_STOP and len(w) > 1}


def dup_overlap(a, b):
    """Shared words over the longer text's words, 0 to 1: deterministic, no model call."""
    return len(a & b) / max(len(a), len(b)) if a and b else 0.0


def duplicate_hint(con, kind, project, rec, threshold):
    """The open item of the same type in the same project that a proposed action, risk or issue most closely repeats, or None."""
    if kind == "actions":
        cands = rows(con, "SELECT id, description FROM actions WHERE project = ? AND status IN ('Open', 'Delayed')", project)
    elif kind == "raid":
        cands = rows(con, "SELECT id, description FROM raid WHERE project = ? AND status = 'Open' AND type = ?", project,
                     rec.get("type") or "Risk")
    else:
        return None
    mine, best = dup_tokens(rec.get("t")), None
    for c in cands:
        score = dup_overlap(mine, dup_tokens(c["description"]))
        if score >= threshold and (not best or score > best["score"]):
            best = {"id": c["id"], "t": c["description"], "score": round(score, 2)}
    return best


def rejected_texts(tracker):
    """({fingerprint: the rejected item's text}, {fingerprints of rejects back in Review, BL-315}) from the proposals."""
    texts, back = {}, set()
    for d in (paths.STAGING, paths.APPLIED):
        for p in sorted(d.glob("proposed-*.json")):
            try:
                items = json.loads(p.read_text(encoding="utf-8")).get("items", [])
            except (OSError, ValueError):
                continue
            for it in items:
                if it.get("decision") == "rejected":
                    v = it.get("values") or {}
                    texts[tracker.fingerprint(it)] = v.get("description") or v.get("decision") or it.get("id") or ""
                elif isinstance(it.get("redecide"), dict) and not it.get("applied"):   # BL-315: back in Review, no longer a reject
                    back.add(it["redecide"].get("fingerprint"))
    return texts, back


def rejected_activity(con):
    """Rejections that carry a reason, as Activity lines with the item's text (from its proposal)."""
    import tracker
    if "reason" not in {r["name"] for r in rows(con, "PRAGMA table_info(rejected)")}:
        return []
    texts, back = rejected_texts(tracker)
    out = []
    for r in rows(con, "SELECT c.at, c.apply_id, c.via, j.reason, j.duplicate_of, j.fingerprint, a.undone_at FROM change_log c "
                       "JOIN rejected j ON j.fingerprint = c.item_id LEFT JOIN applies a ON a.apply_id = c.apply_id "
                       "WHERE c.tbl = 'rejected' AND c.op = 'insert' AND j.reason IS NOT NULL ORDER BY c.rowid DESC LIMIT 200"):
        if r["fingerprint"] in back:
            continue
        text = texts.get(r["fingerprint"], "")
        change = f"rejected: {r['reason']}" + (f" (duplicate of {r['duplicate_of']})" if r["duplicate_of"] else "")
        out.append({"at": (r["at"] or "")[:16], "what": f"{text} — {change}" if text else change, "id": r["duplicate_of"] or "",
                    "tbl": "rejected", "item": text, "change": change, "apply_id": r["apply_id"], "undone": bool(r["undone_at"]),
                    "by": "Rejected in review" + (" (since undone)" if r["undone_at"] else "")})
    return out


# ===== BL-188 (fix-peek-140) =====
def peek_staged():
    """The work item peek's staged changes, whichever window staged them: each unapplied dashboard proposal that carries the
    peek's `peek` note (the item, the change in the page's own fields and its words), oldest first. The page shows them as
    staged (the pill, the feed, the values in the peek) and any window can apply them. Read only."""
    out = []
    for p in sorted(paths.STAGING.glob("proposed-*-dashboard*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        meta = data.get("peek")
        items = data.get("items", [])
        if data.get("source_run") != "dashboard" or not isinstance(meta, dict) or not meta.get("k") or not meta.get("id") \
                or any(i.get("applied") for i in items) \
                or not items or any(i.get("decision") != "approved" for i in items):   # staged = approved, not applied; an undo returns a proposal as pending, which is not staged
            continue
        out.append({**meta, "name": p.name})
    return sorted(out, key=lambda s: (s.get("ms") or 0, s["name"]))
# ===== end BL-188 =====


# ===== BL-260 (fix-minutes-draft) =====
def draft_missing(key, block):
    """Minutes with no Word draft, or one that has gone: Review says so instead of offering a file it can't open."""
    if key != "meeting" or block.get("note"):
        return {}
    draft = block.get("draft")
    if draft and paths.resolve(draft).is_file():
        return {}
    return {"nodraft": True, **({"tsrc": block["transcript"]} if block.get("transcript") else {})}
# ===== end BL-260 =====


def review_queue(con):
    """Pending proposals in the dashboard's Review shape; n matches 'review.py list' numbering order. BL-229: one row per
    block (queue_block) and per item (queue_item), in the same order and numbering."""
    out, n = [], 0
    rows_n, num = review.numbers()      # the same numbers as review.py list (and the index "approve 5" uses)
    if rows_n:
        review.write_index(rows_n)
    limit = review.stale_days()         # BL-133 (sprint-work-views): each proposal's age, and stale past review.stale_after_days (FR-24)
    overlap = float(paths.load_settings().get("review", {}).get("duplicate_overlap", 0.6) or 0.6)   # BL-133 stage B
    for p, data in review.proposals():
        age = review.age(data)
        aged = {"age": age, "stale": age > limit}
        for key, field, label in review.BLOCKS:
            b = data.get(key)
            if b and not b.get("applied") and b.get(field, "pending") == "pending":
                n = num.get((p.name, key), n + 1)
                out.append(queue_block(n, p, key, label, b, aged))
        for item in data.get("items", []):
            if item.get("applied") or item.get("decision") != "pending":
                continue
            n = num.get((p.name, item.get("n")), n + 1)
            out.append(queue_item(con, n, p, item, aged, overlap))
    return out


def queue_block(n, p, key, label, b, aged):
    """One Review row for a proposal's minutes, report or file changes."""
    return {"n": n, "p": (b.get("projects") or [b.get("project")])[0],
            "kind": "draft" if key in ("meeting", "report") else "files",
            "why": f"Draft {label.lower()}" if key in ("meeting", "report") else label, "indiv": True,
            "hold": "minutes" if key == "meeting" else "report" if key == "report" else "file changes",   # #232: never routine
            "rec": {"t": f"{label}: {b.get('title') or Path(b.get('draft') or '').stem}"},
            "src": b.get("draft") or "", "file": p.name, "ref": key,
            "projects": b.get("projects") or [b.get("project")], **aged,   # a meeting shows under each (BL-41)
            **({"cov": b.get("coverage") or [], "mt": hub_token(b["key"])} if key == "meeting" and b.get("key") else {}),   # BL-209
            **draft_missing(key, b)}   # BL-260


def queue_item(con, n, p, item, aged, overlap):
    """One Review row for a pending item."""
    v = item.get("values") or {}
    project = None if review.needs_project(item) else review.project_of(item)
    kind, rec = item_record(con, item)
    flags = item.get("flags", [])
    signals = [propose.learn_check("", s.get("kind", ""), s.get("value", "")) for s in item.get("signals") or []
               if s.get("value")] if item.get("signals") and paths.REGISTER.exists() else []
    dup = duplicate_hint(con, kind, project, rec, overlap) if project and item.get("op") == "new" else None
    return {"n": n, "p": project, "kind": kind, "why": item_why(item, project, flags), "indiv": bool(review.individual_only(item)),
            "hold": review.hold_reason(item) or "",                                         # #232: "" is routine (cmd_bulk's rule)
            "dup": dup, "signals": signals,
            "rec": rec, "src": v.get("source") or item.get("source") or "", "flags": flags, "file": p.name, "ref": item.get("n"), **({"inferred": review.clean_inferred(item.get("inferred"))} if item.get("inferred") else {}),   # BL-208
            "ws_suggest": item.get("ws_suggest"), **aged,                                   # BL-58
            "mf": item.get("moved_from"), "op": item.get("op")}   # BL-200 (sprint-review-work): moved on its own; new or update


def item_why(item, project, flags):
    """Why the item is in Review, as its row says."""
    if project is None:
        return "Possible match" if item.get("match") == "possible" else "Needs a project"
    return (review.individual_only(item) or "").capitalize() or \
        ("Conflict with a newer change" if "conflict" in flags else
         "No owner yet" if "no-owner" in flags else
         "Meeting date taken from the file" if "date-from-file" in flags else
         "New workstream?" if "new-workstream" in flags else f"{(item.get('match') or 'strong').capitalize()} match")


def item_record(con, item):
    """(kind, rec): a new action, risk or decision as its row shows it, or an update with its before and after."""
    v, table = item.get("values") or {}, item.get("table")
    if item.get("op") == "new" and table in NEW_RECORDS:
        return table, NEW_RECORDS[table](v)
    return "update", update_record(con, item)


def new_action_record(v):
    """A new action as its Review row shows it."""
    return {"t": v.get("description", ""), "ws": v.get("workstream") or "",
            "o": v.get("owner") or "TBC", "pr": v.get("priority") or "Medium",
            "due": v.get("due_date"), "st": v.get("status") or "Open",
            "client": bool(v.get("client_visible")), "cm": v.get("client_message") or "",
            "upd": v.get("latest_update") or "", "ms": v.get("milestone"),
            "raised": v.get("raised"), "closed": v.get("closed")}


def new_raid_record(v):
    """A new risk, issue, assumption or dependency as its Review row shows it."""
    return {"type": v.get("type", "Risk"), "t": v.get("description", ""),
            "ws": v.get("workstream") or "", "o": v.get("owner") or "TBC",
            "resp": v.get("response_action") or "", "due": v.get("due_date"),
            "imp": v.get("impact"), "lik": v.get("likelihood"), "st": v.get("status") or "Open",
            "client": bool(v.get("client_visible")), "cm": v.get("client_message") or "",
            "ms": v.get("milestone"), "raised": v.get("raised"), "closed": v.get("closed")}


def new_decision_record(v):
    """A new decision as its Review row shows it."""
    return {"t": v.get("decision", ""), "by": v.get("made_by") or "",
            "date": v.get("date"), "client": bool(v.get("client_visible")),
            "st": v.get("status") or "Made", "due": v.get("needed_by"),          # BL-53 (due: the date it is needed by)
            "why": v.get("reasoning") or "", "opts": v.get("options") or "",
            "revisit": v.get("revisit") or "", "replaces": v.get("replaces")}


NEW_RECORDS = {"actions": new_action_record, "raid": new_raid_record, "decisions": new_decision_record}


def update_record(con, item):
    """An update (or any other item) with what it changes, before → after, from the row as it is now."""
    table = item.get("table")
    what, text, _, _ = review.describe(item)
    changes = item.get("changes") or {}
    field = next(iter(changes), "")
    before = {}
    if item.get("id") and table in ("actions", "raid", "decisions", "milestones", "projects"):
        keycol = "code" if table == "projects" else "id"
        found = rows(con, f"SELECT * FROM {table} WHERE {keycol} = ?", item["id"])
        before = found[0] if found else {}
    current = before.get(field) if field else None
    if item.get("op") == "update" and item.get("table") in ("actions", "raid", "decisions") and "why" in item:   # BL-65
        text = review.update_parts(item)[0]          # the item; its changes are listed as before → after
    return {"t": text if item.get("op") != "new" else f"{what}: {text}", "target": item.get("id"),
            "field": field, "from": current, "to": changes.get(field),
            "changes": [{"field": FIELD_LABELS.get(k, k.replace("_", " ")), "from": before.get(k), "to": v}
                        for k, v in changes.items()] if item.get("op") != "new" else [],
            **({"why": item.get("why") or ""} if "why" in item else {})}


DATE_LIKE = {"due_date", "raised", "closed", "date", "baseline_date", "forecast_date", "milestone_date", "week_ending", "needed_by"}
TEXT_FIELD = {"actions": "description", "raid": "description", "decisions": "decision", "milestones": "name",
              "updates": "summary", "projects": "name"}
KEY_FIELD = {"projects": "code", "updates": None}


# ===== BL-250 (fix-history-feed) ===== B: an item's whole history reaches its feed, while Activity keeps its cap; C: a link or a label
# change reaches the feed of each item it touches, worded from that item's side. activity() is split into the helpers below.
ACT_CAP = 2000                                              # Activity lists the newest 2000 change log rows
LOG_SQL = ("SELECT c.rowid AS rowid, c.*, a.undone_at FROM change_log c LEFT JOIN applies a ON a.apply_id = c.apply_id "
           "WHERE c.tbl != 'rejected' AND c.field != 'updated_at' {where} ORDER BY c.rowid DESC {limit}")
LINKED = {"links": "from_item", "item_labels": "item_id"}   # the one logged field that stands for a whole link or label row
BY = {"dashboard": "You, in the dashboard", "cx-edit": "You, by hand", "excel-import": "Excel import",
      "assistant": "ask creaite", "undo": "Undo", "archive": "Archived for age"}     # BL-10: the daily archiving


def _act_context(con):
    """What every Activity line looks up: reverted rows, RAID types, each item's current text and its text as created."""
    import tracker
    current = {}
    for tbl, field in TEXT_FIELD.items():
        key = KEY_FIELD.get(tbl, "id")
        if key:
            current.update({(tbl, r[key]): r[field] for r in rows(con, f"SELECT {key}, {field} FROM {tbl}")})
        else:   # updates: week_ending|project
            current.update({(tbl, f"{r['week_ending']}|{r['project']}"): r["summary"]
                            for r in rows(con, "SELECT week_ending, project, summary FROM updates")})
    created = {}
    for r in rows(con, "SELECT tbl, item_id, field, new_value FROM change_log WHERE op = 'insert' AND field IN "
                       "('description', 'decision', 'name', 'summary', 'owner', 'due_date', 'type', 'priority')"):
        created.setdefault((r["tbl"], r["item_id"]), {})[r["field"]] = r["new_value"]
    return {"reverted": tracker.reverted_rowids(con), "cols": {}, "current": current, "created": created,
            "raid_type": {r["id"]: r["type"] for r in rows(con, "SELECT id, type FROM raid")}}


def _act_skip(r):
    """A row with no line of its own: a new item's other fields, and a new or undone link's or label's other columns."""
    import tracker
    anchor = LINKED.get(r["tbl"])
    if r["op"] == "insert":
        return r["field"] not in ("id", "code", "week_ending", anchor)
    return bool(anchor) and r["op"] == "undo" and r["field"] not in (anchor, tracker.REMOVED)


def _act_change(r, tbl, made):
    """The words for one change (BL-43): created (with owner and due, or type and priority), undone, a note, or old → new."""
    label = FIELD_LABELS.get(r["field"], r["field"].replace("_", " "))
    val = lambda v: (shown(v) if r["field"] in DATE_LIKE else linktext.words(v)) or "—"  # noqa: E731
    if r["field"] == "note":
        return f"note: {linktext.words(r['new_value'])}"
    if r["op"] == "insert":
        extra = ([f"owner {made['owner']}"] if tbl == "actions" and made.get("owner") else []) + \
                ([f"due {shown(made['due_date'])}"] if tbl == "actions" and made.get("due_date") else []) + \
                ([x for x in (made.get("type"), made.get("priority")) if x] if tbl == "raid" else [])
        return "created" + (f" ({', '.join(extra)})" if extra else "")
    if r["op"] == "undo":
        return f"undone: {label}"
    return f"{label}: {val(r['old_value'])} → {val(r['new_value'])}"


def link_sides(r, change):
    """BL-250 C: a links (`from|to|kind`) or item_labels (`item|label`) row worded from each item's side, {item ID: words}:
    "Linked to ABC-A-004 (blocks)" and "Linked from ABC-A-001 (blocks)", "Label added: Client". `change` is the plain wording."""
    import tracker
    parts = str(r["item_id"]).split("|")
    if len(parts) < 2:
        return None
    gone, added = r["field"] == tracker.REMOVED, r["field"] == LINKED[r["tbl"]]
    if r["tbl"] == "links":
        a, b, kind = (parts + [""])[:3]
        k = f" ({kind})" if kind else ""
        words = {a: (f"Link to {b} removed{k}" if gone else f"Linked to {b}{k}" if added else f"Link to {b}{k}: {change}"),
                 b: (f"Link from {a} removed{k}" if gone else f"Linked from {a}{k}" if added else f"Link from {a}{k}: {change}")}
    else:
        item, name = parts[0], "|".join(parts[1:])
        words = {item: f"Label removed: {name}" if gone else f"Label added: {name}" if added else f"Label {name}: {change}"}
    if r["op"] == "undo":
        words = {i: "undone: " + w[:1].lower() + w[1:] for i, w in words.items()}
    return words


def _act_line(ctx, r):
    """One Activity line for one change log row."""
    key, tbl = r["item_id"], r["tbl"]
    made = ctx["created"].get((tbl, key), {})
    text = ctx["current"].get((tbl, key)) or made.get(TEXT_FIELD.get(tbl, ""), "") or ""
    if r["op"] == "insert":
        text = made.get(TEXT_FIELD.get(tbl, ""), "") or text
    change = _act_change(r, tbl, made)
    sides = link_sides(r, change) if tbl in LINKED else None
    if sides:
        first, change = next(iter(sides.items()))
        what = f"{first} · {change}"
    else:
        what = f"{key} · {text} — {change}" if text else f"{key} {change}"
    via = r["via"]
    e = {"at": (r["at"] or "")[:16], "what": what, "id": key, "tbl": tbl, "item": text, "change": change,
         "apply_id": r["apply_id"], "undone": bool(r["undone_at"]),
         "by": BY.get(via, "Approved in review") + (" (since undone)" if r["undone_at"] and via != "undo" else ""),
         "kind": activity_kind(tbl, key, ctx["raid_type"].get(key) or made.get("type"))}               # BL-164
    if sides:
        e["sides"] = sides
    return e


def older_history(con, ctx, before):
    """BL-250 B: every change older than Activity's newest ACT_CAP rows, for the items' own feeds, kept small: one list per item
    of [at, words, index into `by`, apply_id, 1 if undone], newest first; a link or label line under each item it touches."""
    import tracker
    by, items = {}, {}
    for r in rows(con, LOG_SQL.format(where=f"AND c.rowid < {int(before)}", limit="")):
        if str(r["via"]).startswith(tracker.REVERT_VIA) or _act_skip(r):
            continue
        e = _act_line(ctx, r)
        n = by.setdefault(e["by"], len(by))
        undone = 1 if e["undone"] or r["rowid"] in ctx["reverted"] else 0
        for item, words in (e.get("sides") or {e["id"]: e["change"]}).items():
            items.setdefault(item, []).append([e["at"], words, n, e["apply_id"], undone])
    return {"by": list(by), "items": items} if items else {}


def activity(con, flags=None):
    """The change log, newest first, one line per change, naming the item as well as its ID (BL-43): new items with
    the text as created (and owner and due date, or type and priority); changes with the item's current text.
    BL-164: each line has its `kind` (for its icon and the type filter) and, when it can be undone on its own, the change
    log's `rowid`; a line put back by a later revert is `reverted`; a revert apply is one line ("Undid 3 changes").
    `flags["capped"]` is set when the newest 2000 log rows don't reach the start (the page lists the newest 300 lines until a
    search or filter looks through all of them); BL-250: then `flags["older"]` holds the rest for the items' own feeds
    (older_history). A link or label line carries `sides`, its words for each item it touches."""
    import tracker
    flags = {} if flags is None else flags
    ctx, reverts, out = _act_context(con), {}, []
    found = rows(con, LOG_SQL.format(where="", limit=f"LIMIT {ACT_CAP}"))
    flags["capped"] = len(found) >= ACT_CAP
    for r in found:
        if str(r["via"]).startswith(tracker.REVERT_VIA):         # BL-164: a revert apply is one line, below
            reverts.setdefault(r["apply_id"], {"at": r["at"], "undone": bool(r["undone_at"]), "via": r["via"]})
            continue
        if _act_skip(r):
            continue
        e = _act_line(ctx, r)
        if r["rowid"] in ctx["reverted"]:                   # put back by a revert still in force: shown "undone", not offered
            e["reverted"], e["rowid"] = True, r["rowid"]
        elif revertable(con, r, ctx["cols"]):
            e["rowid"] = r["rowid"]
        out.append(e)                                      # tidy-up (sprint-milestones): every line of the 2000 rows read, so search covers them
    for apply_id, x in reverts.items():                     # BL-164: "Undid 3 changes", with the apply's own Undo
        n = len([i for i in x["via"][len(tracker.REVERT_VIA):].split(",") if i.strip()])
        change = f"Undid {n} change{'' if n == 1 else 's'}"
        out.append({"at": (x["at"] or "")[:16], "what": change, "id": "", "tbl": "revert", "item": "", "change": change,
                    "apply_id": apply_id, "undone": x["undone"], "kind": "revert", "revert": n,
                    "by": "You, in Activity" + (" (since undone)" if x["undone"] else "")})
    flags["older"] = older_history(con, ctx, found[-1]["rowid"]) if flags["capped"] else {}
    return sorted(out + [{**a, "kind": "file"} for a in file_activity(con)] + [{**a, "kind": "rejected"} for a in rejected_activity(con)],
                  key=lambda a: a["at"], reverse=True)    # BL-89: Current state edits too; BL-133: reasons
# ===== end BL-250 =====


# ===== BL-164 (sprint-rail) ===== the type of an Activity line, and whether it can be undone on its own
ITEM_KINDS = (("-A-", "action"), ("-D-", "decision"), ("-M-", "milestone"), ("-W-", "workstream"), ("-P-", "promise"))


def activity_kind(tbl, key, raid_type=None):
    """action, Risk / Issue / Assumption / Dependency, decision, milestone, project, update, workstream, promise, label…"""
    if tbl in ("links", "item_labels"):                     # a link or a label belongs to its (first) item
        item = str(key).split("|")[0]
        k = next((k for m, k in ITEM_KINDS if m in item), None)
        return k or ("Risk" if re.fullmatch(r"[A-Z][A-Z0-9]{2,6}-\d{3}", item) else "label")
    return {"actions": "action", "decisions": "decision", "milestones": "milestone", "projects": "project",
            "updates": "update", "workstreams": "workstream", "promises": "promise", "labels": "label",
            "raid": raid_type or "Risk"}.get(tbl, "project")


def revertable(con, r, cols):
    """The page may offer a line for "undo several" when tracker.py undo-changes could put it back (tracker.why_not)."""
    import tracker
    if r["op"] == "undo" or r["via"] == "undo" or r["undone_at"] or r["tbl"] in ("rejected", "recode") or r["tbl"] not in tracker.TABLES:
        return False
    if r["field"] in ("note", "updated_at"):
        return False
    if r["field"] != tracker.REMOVED:
        if r["tbl"] not in cols:
            cols[r["tbl"]] = set(tracker.columns(con, r["tbl"]))
        if r["field"] not in cols[r["tbl"]]:
            return False
    return r["op"] != "insert" or r["tbl"] in tracker.REVERT_CREATED
# ===== end BL-164 =====


# ===== BL-228 (sprint-debt-safety) =====
def swallowed(where, e):
    """C: an error a fallback didn't expect, in the debug log at debug level by its name only (BL-102: never its text);
    the page is built as before."""
    try:
        import log as debuglog
        debuglog.debug("build", f"{where}: {type(e).__name__} ignored")
    except ImportError:  # the debug log is optional
        pass


def vip_unseen_by_project():
    """BL-99: unseen VIP alerts per project. C: narrowed; anything else is logged and the reminders still show."""
    vip_unseen = {}
    try:
        import sweep
        for a in sweep.vip_state()["alerts"]:
            if sweep.vip_open(a) and a.get("p"):          # BL-334: a quiet line is not counted
                vip_unseen[a["p"]] = vip_unseen.get(a["p"], 0) + 1
    except (ImportError, OSError, ValueError, LookupError, TypeError):  # no sweep helper or an odd VIP file: no VIP count
        pass
    except Exception as e:  # noqa: BLE001  unexpected: logged by name only, the reminders still show
        swallowed("reminders", e)
    return vip_unseen


def vip_kinds():
    """Each VIP's name and kind, for prep's marks. C: narrowed; anything else is logged and prep still shows."""
    try:
        return {v["name"]: v["kind"] for v in propose.vip_people()}
    except (OSError, ValueError, LookupError, TypeError):  # an unreadable or odd people register: no VIP marks
        return {}
    except Exception as e:  # noqa: BLE001  unexpected: logged by name only, prep still shows
        swallowed("prep", e)
        return {}
# ===== end BL-228 =====


def reminders(settings, projects, file_list, today, now):
    """Weekly report and client report reminders (CLAUDE.md session-start rule), minus those dismissed forever."""
    rs = settings.get("reminders", {})
    if not rs.get("enabled", True):
        return []
    out = []
    day = DAYS.index(rs.get("weekly_report_day", "Friday"))
    start = today - timedelta(days=(today.weekday() - day) % 7)
    if start == today and now.strftime("%H:%M") < rs.get("weekly_report_from", "12:00"):
        start -= timedelta(weeks=1)
    week_end = start.isoformat()
    missing = [p["code"] for p in projects
               if not any(f["p"] == p["code"] and f["f"] == "reports" and f["n"].startswith(f"{week_end} Weekly report")
                          for f in file_list)]
    vip_unseen = vip_unseen_by_project()   # BL-99: VIP messages about a project not yet seen, named on its weekly reminder
    name_of = {p["code"]: p.get("name") or p["code"] for p in projects}          # BL-101: a project is its name; the code stays in the command Alan runs
    for code in missing:      # one per project still owed, so each clears when its own report is filed
        out.append({"id": f"weekly:{week_end}:{code}",
                    "text": f"{name_of[code]} weekly report for week ending {shown(week_end)} is due",
                    "cmd": f"weekly report {code} for week ending {shown(week_end)}",   # Run report now (BL-34)
                    **({"vip": vip_unseen[code]} if vip_unseen.get(code) else {})})
    for p in projects:
        gap = client_gap(p)
        if not gap:
            continue
        last = max((f["date"] for f in file_list if f["p"] == p["code"] and "Client report" in f["n"] and f["date"]),
                   default="")
        if not last or (today - date.fromisoformat(last)).days >= gap:
            out.append({"id": f"client:{p['code']}:{last or 'never'}",
                        "text": f"{p.get('name') or p['code']} client report is due (last: {shown(last) if last else 'none yet'})",
                        "cmd": f"client report {p['code']}"})
    out += decision_revisit_reminders(today)                                  # BL-53
    gone = set(rs.get("dismissed_forever", []))
    # a whole week dismissed before reminders were per project ("weekly:<date>") still hides that week's
    return [r for r in out if r["id"] not in gone and ":".join(r["id"].split(":")[:2]) not in gone]


# ===== Help (BL-84) =====
# system/templates/help.md is the one source for the dashboard's Help (three tabs) and for the two printable guides
# (dev/tools/build_guides.py). help_parse() reads it; help_sections() renders the tabs for the dashboard; help_part()
# renders one part for a guide. The same functions draw both, so they cannot drift apart. The conventions are defined
# once, in the comment at the top of help.md.
HELP_PARTS = {"start-here": "start", "how-do-i": "howto", "reference": "reference"}
HELP_FILES = {"start": "guide-first-day.html", "howto": "guide-how-to.html"}
HELP_SCREEN_RE = re.compile(r"^Screen:.*\n?", re.M)
HELP_NEWS_FILE = "help/whats-new.md"      # #158: the plain release notes, copied in at release (never read from dev/)
HELP_SCREENS = {"today": "Today", "work": "Work", "review": "Review", "projects": "Projects", "people": "People",
                "notes": "Notes", "intake": "Intake", "files": "Files"}
HELP_STAGE_ICONS = [
    '<path d="M4 13h4l2 3h4l2-3h4"/><path d="M5.5 5h13L21 13v6H3v-6z"/>',
    '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6"/>',
    '<path d="M5 12.5 10 17l9-10"/>',
    '<ellipse cx="12" cy="6" rx="7" ry="3"/><path d="M5 6v12c0 1.7 3.1 3 7 3s7-1.3 7-3V6M5 12c0 1.7 3.1 3 7 3s7-1.3 7-3"/>',
    '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18M8 13h3M8 16h8"/>']
HELP_ARROW = ('<svg class="hp-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">'
              '<path d="M5 12h14M13 6l6 6-6 6"/></svg>')
HELP_BACK = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">'
             '<path d="M4 12a8 8 0 1 0 2.3-5.6M4 4v4h4"/></svg>')
# BL-277: creaite's icon, Stage (BL-272; dev/reference/logo/creaite-icon-stage.svg), in its own colours in both themes;
# at the Help hero's 64 to 76 px the full Stage reads (the plain small version is for 32 px and below)
HELP_LOGO = ('<svg class="%s" viewBox="0 0 512 512" role="img" aria-label="creaite icon"><rect width="512" height="512" '
             'rx="112" fill="#18181B"/><rect x="87" y="87" width="225" height="225" rx="46" fill="none" stroke="#A1A1AA" '
             'stroke-width="18" stroke-dasharray="31 26"/><rect x="200" y="200" width="225" height="225" rx="46" '
             'fill="#F2B544"/><path d="M348 276A51 51 0 1 0 348 348" fill="none" stroke="#18181B" stroke-width="28" '
             'stroke-linecap="round"/></svg>')


def help_slug(title):
    """A heading as a Help anchor: lower case, letters, digits and hyphens."""
    return re.sub(r"[^a-z0-9 -]", "", title.lower()).strip().replace(" ", "-")


def help_parse(text=None):
    """help.md → {part id: {title, slug, intro: [lines], groups: [{name, intro, sections: [{title, slug, lines}]}], footer}}."""
    if text is None:
        f = paths.TEMPLATES / "help.md"
        text = f.read_text(encoding="utf-8") if f.exists() else ""
    text = re.sub(r"\A\s*<!--.*?-->", "", text, flags=re.S)
    text = re.sub(HELP_SCREEN_RE, "", text)      # #158: the Screen: lines are data, not page text
    parts, part, group, section, in_footer = {}, None, None, None, False
    for line in text.splitlines():
        m = re.match(r"# (.+?)\s*$", line)
        if m:
            slug = help_slug(m.group(1))
            part = parts.setdefault(HELP_PARTS.get(slug, slug), {"title": m.group(1), "slug": slug, "intro": [],
                                                                  "groups": [], "footer": []})
            group = section = None
            in_footer = False
            continue
        if part is None:
            continue
        if line.strip() == "---":
            in_footer = True
            continue
        if in_footer:
            if line.strip():
                part["footer"].append(line.strip())
            continue
        m = re.match(r"### (.+?)\s*$", line)
        if m:
            group = {"name": m.group(1), "intro": [], "sections": []}
            part["groups"].append(group)
            section = None
            continue
        m = re.match(r"## (.+?)\s*$", line)
        if m:
            if group is None:
                group = {"name": "", "intro": [], "sections": []}
                part["groups"].append(group)
            section = {"title": m.group(1), "slug": help_slug(m.group(1)), "lines": []}
            group["sections"].append(section)
            continue
        (section["lines"] if section else group["intro"] if group else part["intro"]).append(line)
    return parts


def _hp_blocks(lines):
    """Lines → blocks: italic (the eyebrow), bold (the heading), p, ul, ol (items may have sub-bullets) and table."""
    out, i = [], 0
    while i < len(lines):
        ln = lines[i]
        if not ln.strip():
            i += 1
        elif ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            out.append({"k": "table", "rows": rows})
        elif re.match(r"(- |\d+\. )", ln):
            kind = "ul" if ln.startswith("- ") else "ol"
            items = []
            while i < len(lines) and (re.match(r"- " if kind == "ul" else r"\d+\. ", lines[i]) or re.match(r"\s+- ", lines[i])):
                sub = re.match(r"\s+- (.*)", lines[i])
                if sub and items:
                    items[-1]["sub"].append(sub.group(1))
                elif not sub:
                    items.append({"t": re.sub(r"^(- |\d+\. )", "", lines[i]), "sub": []})
                i += 1
            out.append({"k": kind, "items": items})
        elif re.fullmatch(r"\*\*[^*].*[^*]\*\*|\*\*[^*]\*\*", ln.strip()):
            out.append({"k": "bold", "t": ln.strip()[2:-2]})
            i += 1
        elif re.fullmatch(r"\*[^*].*[^*]\*|\*[^*]\*", ln.strip()):
            out.append({"k": "italic", "t": ln.strip()[1:-1]})
            i += 1
        else:
            para = []
            while i < len(lines) and lines[i].strip() and not re.match(r"(\||- |\d+\. )", lines[i]):
                para.append(lines[i].strip())
                i += 1
            out.append({"k": "p", "t": " ".join(para)})
    return out


class _HelpCtx:
    """How links and card ids are written: in the dashboard a link switches tab (data-help), in a guide it is a file link."""

    def __init__(self, mode, part, version, tasks=()):
        self.mode, self.part, self.version, self.tasks = mode, part, version, set(tasks)

    def link(self, text, slug):
        """A link to a Help section: within the printed guide's own files, or within the dashboard's Help page."""
        part = HELP_PARTS.get(slug)
        if self.mode == "guide":
            if part and part in HELP_FILES:
                href = "#" if part == self.part else HELP_FILES[part]
            elif slug in self.tasks:
                href = "#" + slug if self.part == "howto" else f"{HELP_FILES['howto']}#{slug}"
            else:
                href = "#" + slug
            return f'<a href="{href}">{text}</a>'
        target = part or ("howto-" + slug if slug in self.tasks else "reference-" + slug)
        return f'<a href="#help-{target}" data-help="{target}">{text}</a>'


def _hp_esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _hp_inline(t, ctx, chips=False):
    t = t.replace("{version}", ctx.version)
    out = []
    for seg in re.split(r"(``.+?``|`.+?`)", t):
        if len(seg) > 4 and seg.startswith("``") and seg.endswith("``"):
            out.append(f'<span class="hp-say">{_hp_esc(seg[2:-2])}</span>')
        elif len(seg) > 2 and seg.startswith("`") and seg.endswith("`"):
            out.append(f'<span class="hp-say">{_hp_esc(seg[1:-1])}</span>' if chips else f"<code>{_hp_esc(seg[1:-1])}</code>")
        else:
            s = _hp_esc(seg)
            s = re.sub(r"\[\[(.+?)\]\]", r"<kbd>\1</kbd>", s)
            s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s\"'<>]+)\)",
                       lambda m: f'<a href="{m.group(2)}" target="_blank" rel="noopener noreferrer">{m.group(1)}</a>', s)   # #158: an outside link
            s = re.sub(r"\[([^\]]+)\]\((#[^)]+)\)", lambda m: ctx.link(m.group(1), m.group(2)[1:]), s)
            out.append(re.sub(r"\*\*(.+?)\*\*", r'<b class="ui">\1</b>', s))
    return "".join(out)


def _hp_list(items, kind, ctx, chips=False):
    body = "".join(f"<li>{_hp_inline(i['t'], ctx, chips)}"
                   + (("<ul>" + "".join(f"<li>{_hp_inline(s, ctx, chips)}</li>" for s in i["sub"]) + "</ul>") if i["sub"] else "")
                   + "</li>" for i in items)
    return f"<{kind}>{body}</{kind}>"


def _hp_plain(blocks, ctx):
    """Blocks as plain HTML, for a Reference section."""
    html = []
    for b in blocks:
        k = b["k"]
        if k in ("ul", "ol"):
            html.append(_hp_list(b["items"], k, ctx))
        elif k == "table":
            body = "".join("<tr>" + "".join(f"<td>{_hp_inline(c, ctx)}</td>" for c in r) + "</tr>" for r in b["rows"][1:])
            html.append(f'<div class="tbl"><table><tbody>{body}</tbody></table></div>')
        else:
            html.append(f"<p>{_hp_inline(b['t'], ctx)}</p>")
    return "".join(html)


def _hp_head(sec, ctx, tag_id):
    """A section head from its blocks: the eyebrow (italic), the heading (bold, else the ## title) and the lead-in paragraphs."""
    blocks = _hp_blocks(sec["lines"])
    eye = next((b["t"] for b in blocks if b["k"] == "italic"), "")
    title = next((b["t"] for b in blocks if b["k"] == "bold"), sec["title"])
    lead = [b["t"] for b in blocks if b["k"] == "p" and not re.match(r"(Where|Or say|Keys|Jobs):", b["t"])]
    html = '<div class="hp-sechead">' + (f'<span class="hp-eyebrow">{_hp_inline(eye, ctx)}</span>' if eye else "") \
        + f'<h2 id="{tag_id}">{_hp_inline(title, ctx)}</h2>' + "".join(f"<p>{_hp_inline(p, ctx)}</p>" for p in lead) + "</div>"
    return html


def _hp_hero(intro, ctx, big):
    blocks = _hp_blocks(intro)
    eye = next((b["t"] for b in blocks if b["k"] == "italic"), "")
    title = next((b["t"] for b in blocks if b["k"] == "bold"), "")
    lede = "".join(f'<p class="hp-lede">{_hp_inline(b["t"], ctx)}</p>' for b in blocks if b["k"] == "p")
    return ('<header class="hp-hero">' + HELP_LOGO % ("hp-logo" if big else "hp-logo sm")
            + f'<div><span class="hp-eyebrow">{_hp_inline(eye, ctx)}</span><h1>{_hp_inline(title, ctx)}</h1>{lede}</div></header>')


def _hp_footer(lines, ctx):
    return ('<footer class="hp-foot">' + "".join(f"<span>{_hp_inline(ln, ctx)}</span>" for ln in lines) + "</footer>") if lines else ""


def _hp_say(blocks, ctx, outline):
    """Start here, Say this: the phrasebook table."""
    tb = next((b for b in blocks if b["k"] == "table"), {"rows": []})
    rows = tb["rows"]
    for r in rows[1:]:
        outline["say"] += re.findall(r"`([^`]+)`", r[0])
    if not rows:
        return ""
    head = "".join(f"<th>{_hp_inline(c, ctx)}</th>" for c in rows[0])
    body = "".join("<tr>" + "".join(f"<td>{_hp_inline(c, ctx, True)}</td>" for c in r) + "</tr>" for r in rows[1:])
    return f'<div class="hp-phrases"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def _hp_rules(lists, ctx, outline):
    """Start here, Four rules."""
    cards = []
    for it in lists[0]["items"] if lists else []:
        m = re.match(r"\*\*(.+?)\*\*:?\s*(.*)$", it["t"])
        if m:
            cards.append(f'<div class="hp-rule"><b>{_hp_inline(m.group(1), ctx)}</b><span>{_hp_inline(m.group(2), ctx)}</span></div>')
            outline["rules"].append(m.group(1))
    return '<div class="hp-rules">' + "".join(cards) + "</div>"


def _hp_start(part, ctx, only=None):
    secs = {s["title"]: s for g in part["groups"] for s in g["sections"]}
    html, outline = [_hp_hero(part["intro"], ctx, True)], {"stages": [], "steps": [], "rhythm": [], "views": [], "say": [], "rules": []}
    for title, s in secs.items():
        if only and title not in only:      # #158: the first-day card draws three of Start here's sections
            continue
        blocks = _hp_blocks(s["lines"])
        sid = "hp-" + s["slug"]
        if title == "The loop":
            ol = next((b for b in blocks if b["k"] == "ol"), {"items": []})
            at = blocks.index(ol) if ol["items"] else len(blocks)
            before = [b["t"] for b in blocks[:at] if b["k"] == "p"]
            after = [b["t"] for b in blocks[at + 1:] if b["k"] == "p"]
            stages = []
            for n, it in enumerate(ol["items"], 1):
                m = re.match(r"\*\*(.+?)\*\*\s*\(([^)]+)\)\s*(?:\{you:\s*([^}]*)\})?\s*:?\s*(.*)$", it["t"])
                if not m:
                    continue
                name, label, gate, text = m.groups()
                cls = "hp-stage hp-you" if gate is not None else "hp-stage"
                body = (f"<p>{_hp_inline(text, ctx)}</p>" if text else "") \
                    + (("<ul>" + "".join(f"<li>{_hp_inline(x, ctx)}</li>" for x in it["sub"]) + "</ul>") if it["sub"] else "") \
                    + (f'<span class="hp-gate">{_hp_inline(gate or "The only gate", ctx)}</span>' if gate is not None else "")
                stages.append(f'<div class="{cls}"><span class="hp-n">{n} · {_hp_esc(label.upper())}</span><h3>'
                              f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">'
                              f'{HELP_STAGE_ICONS[(n - 1) % 5]}</svg>{_hp_inline(name, ctx)}</h3>{body}'
                              + (HELP_ARROW if n < len(ol["items"]) else "") + "</div>")
                outline["stages"].append({"n": n, "label": label, "title": name, "gate": gate is not None})
            html.append(f'<section class="hp-loop" aria-labelledby="{sid}"><div class="hp-loophead"><h2 id="{sid}">{_hp_inline(s["title"], ctx)}</h2>'
                        + "".join(f"<p>{_hp_inline(p, ctx)}</p>" for p in before) + '</div><div class="hp-flow">' + "".join(stages) + "</div>"
                        + "".join(f'<p class="hp-back">{HELP_BACK}{_hp_inline(p, ctx)}</p>' for p in after) + "</section>")
            continue
        head = _hp_head(s, ctx, sid)
        lists = [b for b in blocks if b["k"] in ("ul", "ol")]
        if title == "Your first hour":
            cards = []
            for n, it in enumerate(lists[0]["items"] if lists else [], 1):
                m = re.match(r"\*\*(.+?)\*\*\s*:?\s*(.*)$", it["t"])
                name, text = (m.group(1), m.group(2)) if m else ("", it["t"])
                cards.append(f'<div class="hp-step"><span class="hp-n">{n}</span><h3>{_hp_inline(name, ctx)}</h3><p>{_hp_inline(text, ctx)}</p></div>')
                outline["steps"].append(name)
            body = '<div class="hp-steps">' + "".join(cards) + "</div>"
        elif title == "Every day":
            cards = []
            for it in lists[0]["items"] if lists else []:
                m = re.match(r"\*\*(.+?)\*\*:?\s*\*\*(.+?)\*\*\s*(.*)$", it["t"])
                if m:
                    cards.append(f'<div class="hp-beat"><span class="hp-when">{_hp_inline(m.group(1), ctx)}</span><h3>{_hp_inline(m.group(2).rstrip("."), ctx)}</h3><p>{_hp_inline(m.group(3), ctx, True)}</p></div>')
                    outline["rhythm"].append({"when": m.group(1), "title": m.group(2)})
            body = '<div class="hp-rhythm">' + "".join(cards) + "</div>"
        elif title == "Where things are":
            cards = []
            for it in lists[0]["items"] if lists else []:
                m = re.match(r"\*\*(.+?)\*\*:?\s*(.*)$", it["t"])
                if m:
                    cards.append(f'<div class="hp-view"><b>{_hp_inline(m.group(1), ctx)}</b><span>{_hp_inline(m.group(2), ctx)}</span></div>')
                    outline["views"].append(m.group(1))
            keys = next((b["t"][5:].strip() for b in blocks if b["k"] == "p" and b["t"].startswith("Keys:")), "")
            body = '<div class="hp-views">' + "".join(cards) + "</div>" \
                + (('<div class="hp-keys">' + "".join(f"<span>{_hp_inline(k.strip(), ctx)}</span>" for k in keys.split(" · ")) + "</div>") if keys else "")
        elif title == "Say this":
            body = _hp_say(blocks, ctx, outline)
        elif title == "Four rules":
            body = _hp_rules(lists, ctx, outline)
        elif title == "The twelve jobs":
            jobs = help_jobs({"start": {"groups": [{"sections": [s]}]}})
            body = '<div class="hp-jobgrid">' + "".join(
                f'<a class="hp-job" href="#help-howto-{j["id"]}" data-help="howto-{j["id"]}"><b>{_hp_inline(j["title"], ctx)}</b>'
                f'<span>{_hp_inline(j["line"], ctx)}</span></a>' for j in jobs) + "</div>"
        else:
            body = _hp_plain([b for b in blocks if b["k"] in ("ul", "ol", "table")], ctx)
        html.append(f'<section class="hp-sec" aria-labelledby="{sid}">{head}{body}</section>')
    if not only:
        html.append(_hp_footer(part["footer"], ctx))
    return "".join(html), outline


def _hp_task(sec, ctx, group_ids):
    blocks = _hp_blocks(sec["lines"])
    where = next((b["t"][6:].strip() for b in blocks if b["k"] == "p" and b["t"].startswith("Where:")), "")
    say = next((b["t"][7:].strip() for b in blocks if b["k"] == "p" and b["t"].startswith("Or say:")), "")
    steps = next((b for b in blocks if b["k"] == "ol"), {"items": []})["items"]
    cid = ("ht-" + sec["slug"]) if ctx.mode == "dashboard" else sec["slug"]
    html = (f'<article class="hp-task" id="{cid}" data-task="{sec["slug"]}"><span class="hp-where">{_hp_inline(where, ctx)}</span>'
            f'<h3>{_hp_inline(sec["title"], ctx)}</h3><ol>' + "".join(f"<li>{_hp_inline(i['t'], ctx)}</li>" for i in steps) + "</ol>"
            + (f'<p class="hp-or"><b>Or say</b>{_hp_inline(say, ctx, True)}</p>' if say else "") + "</article>")
    return html, {"where": where, "steps": len(steps), "say": bool(say)}


def _hp_howto(part, ctx):
    html, outline, nav, cards = [_hp_hero(part["intro"], ctx, False)], [], [], []
    for gi, g in enumerate(part["groups"], 1):
        tasks, links = [], []
        for s in g["sections"]:
            t, info = _hp_task(s, ctx, None)
            tasks.append(t)
            href = f'#help-howto-{s["slug"]}" data-help="howto-{s["slug"]}' if ctx.mode == "dashboard" else "#" + s["slug"]
            links.append(f'<li><a href="{href}">{_hp_inline(s["title"], ctx)}</a></li>')
            outline.append({"id": s["slug"], "title": s["title"], "group": g["name"], **info})
        nav.append(f'<div><h2>{_hp_inline(g["name"], ctx)}</h2><ol>{"".join(links)}</ol></div>')
        cards.append(f'<section class="hp-group" aria-labelledby="hp-g{gi}"><div class="hp-ghead"><h2 id="hp-g{gi}">{_hp_inline(g["name"], ctx)}</h2></div>'
                     f'<div class="hp-tasks">{"".join(tasks)}</div></section>')
    html.append('<nav class="hp-index" aria-label="Tasks">' + "".join(nav) + "</nav>")
    html += cards
    html.append(_hp_footer(part["footer"], ctx))
    return "".join(html), outline


def _hp_reference(part, ctx):
    side, body, outline = [], [], []
    for g in part["groups"]:
        links = []
        body.append(f'<div class="hp-refgroup">{_hp_inline(g["name"], ctx)}</div>') if g["name"] else None
        for s in g["sections"]:
            links.append(f'<a href="#help-reference-{s["slug"]}" data-help="reference-{s["slug"]}">{_hp_inline(s["title"], ctx)}</a>')
            body.append(f'<section class="hp-ref" id="hr-{s["slug"]}" data-ref="{s["slug"]}"><h2>{_hp_inline(s["title"], ctx)}</h2>'
                        f'{_hp_plain(_hp_blocks(s["lines"]), ctx)}</section>')
            outline.append({"id": s["slug"], "title": s["title"], "group": g["name"]})
        side.append(f'<div class="hp-refidxg"><span class="hp-eyebrow">{_hp_inline(g["name"], ctx)}</span>{"".join(links)}</div>')
    lead = "".join(f'<p class="hp-reflead">{_hp_inline(b["t"], ctx)}</p>' for b in _hp_blocks(part["intro"]) if b["k"] == "p")
    html = ('<div class="hp-reflay"><nav class="hp-refidx" aria-label="Reference sections">'
            + "".join(side)
            + f'</nav><div class="hp-refbody">{lead}{"".join(body)}</div></div>')
    return html, outline


def help_screens(text=None):
    """#158: the `Screen: Review -> id, id | Reference: id` lines of help.md -> {screen key: {title, ids, ref}}."""
    if text is None:
        f = paths.TEMPLATES / "help.md"
        text = f.read_text(encoding="utf-8") if f.exists() else ""
    out = {}
    for line in re.findall(r"^Screen:.*$", text, re.M):
        m = re.fullmatch(r"Screen:\s*(.+?)\s*(?:->|\u2192)\s*([^|\n]+?)\s*(?:\|\s*Reference:\s*([a-z0-9-]+))?\s*", line)
        if not m:
            raise ValueError(f"help.md: a Screen line is not 'Screen: Name -> id, id | Reference: id': {line}")
        key = m.group(1).strip().lower()
        if key in out:
            raise ValueError(f"help.md: a second Screen line for {m.group(1).strip()}: {line}")
        out[key] = {"title": m.group(1).strip(), "ids": [i.strip() for i in m.group(2).split(",") if i.strip()],
                    "ref": m.group(3) or ""}
    return out


def help_jobs(parts):
    """#158: the `Jobs:` block under Start here -> [{id, title, line}] (a bullet `[Title](#page-id): one line`)."""
    out = []
    for g in parts.get("start", {"groups": []})["groups"]:
        for s in g["sections"]:
            for b in _hp_blocks(s["lines"]):
                if b["k"] == "ul":
                    for it in b["items"]:
                        m = re.match(r"\[([^\]]+)\]\(#([^)]+)\)\s*:?\s*(.*)$", it["t"])
                        if m:
                            out.append({"id": m.group(2), "title": m.group(1), "line": m.group(3)})
    return out


def help_news(text=None):
    """#158: system/templates/help/whats-new.md -> (lead-in lines, [{v, lines}] newest first), a `## creaite X.Y.Z` section each."""
    if text is None:
        f = paths.TEMPLATES / HELP_NEWS_FILE
        text = f.read_text(encoding="utf-8") if f.exists() else ""
    lead, items, cur = [], [], None
    for line in text.splitlines():
        m = re.match(r"## creaite (\d+\.\d+\.\d+)\s*$", line)
        if m:
            cur = {"v": m.group(1), "lines": []}
            items.append(cur)
        elif line.startswith("# "):
            continue
        else:
            (cur["lines"] if cur else lead).append(line)
    return lead, items


def help_check(jobs, screens, tasks, sections):
    """#158: every job and Screen id must be a page. Returns the problems (empty when all resolve)."""
    bad = [f"Jobs: {j['id']}" for j in jobs if j["id"] not in tasks]
    for s in screens.values():
        bad += [f"Screen {s['title']}: {i}" for i in s["ids"] if i not in tasks]
        if s["ref"] and s["ref"] not in sections:
            bad.append(f"Screen {s['title']}: Reference {s['ref']}")
    bad += [f"Screen {k}: not a screen" for k in screens if k not in HELP_SCREENS]
    return bad


def _hp_news(lead, items, ctx):
    head = "".join(f'<p class="hp-lede">{_hp_inline(b["t"], ctx)}</p>' for b in _hp_blocks(lead) if b["k"] == "p")
    html = ['<header class="hp-hero">' + HELP_LOGO % "hp-logo sm" + '<div><span class="hp-eyebrow">Release notes</span>'
            f"<h1>What\u2019s new</h1>{head}</div></header>"]
    for it in items:
        vid = it["v"].replace(".", "-")
        body = _hp_plain([b for b in _hp_blocks(it["lines"]) if b["k"] in ("p", "ul", "ol")], ctx)
        html.append(f'<article class="hp-new" id="hn-{vid}" data-ver="{it["v"]}"><span class="hp-ver">{it["v"]}</span>'
                    f'<div class="hp-newbody"><h2>creaite {it["v"]}</h2>{body}</div></article>')
    return "".join(html), [{"id": it["v"].replace(".", "-"), "title": "creaite " + it["v"]} for it in items]


def help_version():
    """The installed version for Help, or X.Y.Z when the VERSION file is missing."""
    f = paths.VERSION_FILE
    return (f.read_text(encoding="utf-8").strip() if f.exists() else "") or "X.Y.Z"


def help_part(part_id, mode="guide", text=None):
    """One part of help.md as HTML in the artifacts' components (mode "guide": for the standalone files; "dashboard": for the tabs)."""
    parts = help_parse(text)
    tasks = [s["slug"] for g in parts.get("howto", {"groups": []})["groups"] for s in g["sections"]]
    ctx = _HelpCtx(mode, part_id, help_version(), tasks)
    p = parts[part_id]
    return {"start": _hp_start, "howto": _hp_howto, "reference": _hp_reference}[part_id](p, ctx)[0]


def help_card(kind, text=None):
    """#158: the two printed cards, drawn from help.md. "start": the first-day card (the loop, your first hour, the four rules;
    one page). "howto": the top-12 card (the twelve jobs, one line and the page name each; two pages)."""
    parts = help_parse(text)
    tasks = {s["slug"]: s["title"] for g in parts.get("howto", {"groups": []})["groups"] for s in g["sections"]}
    ctx = _HelpCtx("guide", kind, help_version(), list(tasks))
    if kind == "start":
        return _hp_start(parts["start"], ctx, only=("The loop", "Your first hour", "Four rules"))[0]
    jobs = help_jobs(parts)
    items = "".join(f'<li class="hp-topjob"><b>{_hp_inline(j["title"], ctx)}</b><span>{_hp_inline(j["line"], ctx)}</span>'
                    f'<em>Help \u203a How do I\u2026 \u203a {_hp_esc(tasks.get(j["id"], j["id"]))}</em></li>' for j in jobs)
    lede = "Press <kbd>?</kbd> in creaite, search for the page name, and the steps are there."
    return ('<header class="hp-hero">' + HELP_LOGO % "hp-logo sm"
            + f'<div><span class="hp-eyebrow">creaite {help_version()} \u00b7 top 12 jobs</span>'
            f'<h1>The twelve jobs</h1><p class="hp-lede">{lede}</p></div></header>' + f'<ol class="hp-top12">{items}</ol>')


def help_sections():
    """system/templates/help.md -> the Help page: four tabs (HTML each; What's new from help/whats-new.md), the task and
    reference lists (for the search and the indexes), the jobs, the Screen lists and an outline of Start here. The page
    puts the vault's server command where [start command] stands."""
    parts = help_parse()
    if not parts:
        return {}
    tasks = [s["slug"] for g in parts.get("howto", {"groups": []})["groups"] for s in g["sections"]]
    out = {"tabs": [], "tasks": [], "sections": [], "start": {}, "jobs": [], "screens": {}, "news": []}
    for pid, builder in (("start", _hp_start), ("howto", _hp_howto), ("reference", _hp_reference)):
        if pid not in parts:
            continue
        ctx = _HelpCtx("dashboard", pid, help_version(), tasks)
        html, extra = builder(parts[pid], ctx)
        out["tabs"].append({"id": pid, "title": parts[pid]["title"], "html": html})
        if pid == "start":
            out["start"] = extra
        elif pid == "howto":
            out["tasks"] = extra
        else:
            out["sections"] = extra
    out["jobs"] = help_jobs(parts)
    out["screens"] = help_screens()
    lead, items = help_news()
    if items:
        html, out["news"] = _hp_news(lead, items, _HelpCtx("dashboard", "whatsnew", help_version(), tasks))
        out["tabs"].append({"id": "whatsnew", "title": "What\u2019s new", "html": html})
    bad = help_check(out["jobs"], out["screens"], set(tasks), {s["id"] for s in out["sections"]})
    if bad:
        raise ValueError("help.md has links that do not resolve: " + "; ".join(bad))
    return out


def sweep_due_info():
    """#200: whether the daily sweep is due (sweep.due_info(): the last success before today's sweep.due_from, and now after it),
    for Today's 'Sweep due since 07:00' banner. {due, due_from, last}; CREAITE_NOW fixes the clock as in sweep.py."""
    try:
        import sweep
        d = sweep.due_info()
        return {"due": bool(d["due"]), "due_from": d["due_from"], "last": d["last"]}
    except Exception as e:      # the banner is a convenience; a failure here never stops the build
        swallowed("sweep_due", e)
        return {"due": False, "due_from": "07:00", "last": None}


def ui_settings(s):
    """settings.json → the dashboard's settings keys."""
    import tracker      # BL-181: the weekend days
    g = lambda *k, d=None: _dig(s, k, d)  # noqa: E731
    return {"me": g("identity", "name", d="Alan Carter"), "short": ", ".join(g("identity", "short_forms", d=[])),
            "ownDomains": [str(d).lower() for d in g("identity", "own_domains", d=[])],        # BL-83: who counts as inside the company
            "staleDays": g("review", "stale_after_days", d=7), "rvAdvance": g("review", "auto_advance", d=True),   # BL-133
            "dupOverlap": g("review", "duplicate_overlap", d=0.6),   # BL-133 stage B: how close a proposal must be to an open item "dueSoon": g("review", "due_soon_days", d=7),
            "autoApply": g("dashboard", "auto_apply", d=True), "theme": g("dashboard", "theme", d="System"),
            "palette": g("dashboard", "palette", d="creaite"),
            "motion": g("dashboard", "motion", d="System"),                  # BL-136: Follow system, Reduce or Full
            "remindersOn": g("reminders", "enabled", d=True), "weeklyDay": g("reminders", "weekly_report_day", d="Friday"),
            "weeklyTime": g("reminders", "weekly_report_from", d="12:00"), "sweepDue": g("sweep", "due_from", d="07:00"),
            "lookback": g("sweep", "first_run_lookback_days", d=14), "srcInbox": g("sweep", "sources", "inbox", d=True),
            "srcSent": g("sweep", "sources", "sent_items", d=True), "srcChats": g("sweep", "sources", "teams_chats", d=True),
            "srcChannels": g("sweep", "sources", "teams_channels", d=True),
            "srcCalendar": g("sweep", "sources", "calendar", d=True),
            "possible": g("sweep", "show_possible_matches", d=True),
            "catchupSweep": g("day", "catchup_sweep", d="start"),          # BL-295: Close the day's catch-up sweep: start, offer or off
            "catchupAfter": g("day", "catchup_after_minutes", d=30),       # BL-295: when the last sweep counts as old
            "overdueDays": g("health", "at_risk_overdue_days", d=7),
            "slipAtRisk": g("health", "at_risk_milestone_slip_weeks_max", d=2),
            "slipOff": g("health", "off_track_milestone_slip_weeks_over", d=2),
            "urgentOff": g("health", "off_track_urgent_risks_min", d=2), "dailyBackup": g("backups", "daily", d=True),
            "filesDocs": g("dashboard", "files_show_documents", d=False),   # BL-87
            "showArchived": g("dashboard", "show_archived", d=False),     # BL-09: archived projects' items in the views
            "undatedGrace": g("dashboard", "undated_grace_days", d=3),      # BL-95
            "flowWeeks": flow_weeks(s),                                     # BL-91
            "weekPrios": list(g("dashboard", "week_ahead_priorities", d=None) or []),   # BL-235 (fix-small-17): empty means every priority
            "helpLine": bool(g("help", "first_line", d=True)),   # #158: the first-visit "Press ? for help" line
            "helpSeen": g("help", "start_seen", d=False),   # BL-84: Help › Start here shows once, on the first visit
            "port": g("live_mode", "port", d=8765), "healthSecs": g("live_mode", "health_check_seconds", d=30),
            "defPriority": g("defaults", "new_action_priority", d="Medium"),
            "defActionView": g("defaults", "actions_status_filter", d="open"), "defRaidView": g("defaults", "raid_status_filter", d="open"),
            "defDecisionView": g("defaults", "decisions_view", d="all"),           # BL-131: the Decisions tab's default view
            "savedViews": g("work", "saved_views", d={}),
            "bgActions": g("work", "board", "group", "actions", d="due"),         # BL-103: how each tab's Work board is grouped
            "bgRaid": g("work", "board", "group", "raid", d="owner"),
            "bgDecisions": g("work", "board", "group", "decisions", d="status"),          # BL-103: the Decisions board
            "boardClosedDays": g("work", "board", "closed_days", d=14),          # closed items shown in a board's Closed column
            "weekendDays": sorted(tracker.weekend_days(s)),                     # BL-181: Monday 0
            "rail": g("dashboard", "rail", d=None),               # BL-163 (sprint-rail): the left rail's order, hidden items and display
            "railLabels": bool(g("dashboard", "rail_labels", d=True)),   # #156: Labels when collapsed
            "railIconSize": g("dashboard", "rail_icon_size", d="small"),   # #182: Icon size
            "listCap": g("dashboard", "project_list_cap", d=10),   # BL-48
            "genDays": g("dashboard", "generate_days", d=7)}       # BL-46    # BL-45: Alan's saved Work views


def _dig(d, keys, default):
    for k in keys:
        if not isinstance(d, dict) or k not in d:
            return default
        d = d[k]
    return d


# ── Build ─────────────────────────────────────────────────────────────────────

def clock():
    """Now; CREAITE_NOW ("YYYY-MM-DD HH:MM") fixes it for tests, as in sweep.py."""
    fixed = os.environ.get("CREAITE_NOW")
    return datetime.strptime(fixed, "%Y-%m-%d %H:%M") if fixed else datetime.now()


# ===== BL-304 (v1.9.4 instant edits) ===== one row of each kind in the page's shape, shared by collect() and records()
def action_row(a):
    """An actions row as the page holds it."""
    return {"id": a["id"], "p": a["project"], "t": a["description"], "ws": a["workstream"] or "", "o": a["owner"],
            "pr": a["priority"], "due": a["due_date"], "st": a["status"], "raised": a["raised"], "closed": a["closed"],
            "upd": a["latest_update"] or "", "client": bool(a["client_visible"]), "cm": a["client_message"],
            "src": a["source"], "upd_at": (a["updated_at"] or "")[:16], "updated_at": a["updated_at"],
            "ms": a.get("milestone"), **archived_mark(a)}


def archived_mark(r):
    """BL-10: {"ar": True} on an archived row (its own age or its project's), shown only with Show archived on; else nothing,
    so a page without archived items is unchanged."""
    return {"ar": True} if r.get("archived") else {}


def raid_row(r):
    """A raid row as the page holds it (the stored priority; the page recalculates it from impact and likelihood)."""
    return {"id": r["id"], "p": r["project"], "type": r["type"], "t": r["description"], "ws": r["workstream"] or "",
            "o": r["owner"], "resp": r["response_action"] or "", "due": r["due_date"], "imp": r["impact"],
            "lik": r["likelihood"], "st": r["status"], "raised": r["raised"], "closed": r["closed"],
            "client": bool(r["client_visible"]), "cm": r["client_message"], "src": r["source"],
            "upd_at": (r["updated_at"] or "")[:16], "updated_at": r["updated_at"], "ms": r.get("milestone"),
            "pr": r.get("priority"), **archived_mark(r)}


def replaced_by_map(con):
    """{decision ID: the ID of the decision that replaces it}."""
    return {r["replaces"]: r["id"] for r in rows(con, "SELECT id, replaces FROM decisions WHERE replaces IS NOT NULL ORDER BY id")}


def decision_row(d, replaced_by):
    """A decisions row as the page holds it."""
    return {"id": d["id"], "p": d["project"], "t": d["decision"], "by": d["made_by"] or "", "date": d["date"] or "",
            "st": d["status"], "due": d["needed_by"], "why": d["reasoning"], "opts": d["options"], "revisit": d["revisit"],
            "replaces": d["replaces"], "rby": replaced_by.get(d["id"]),
            "client": bool(d["client_visible"]), "cmd": d["client_message"], "src": d["source"],
            "upd_at": (d["updated_at"] or "")[:16], "updated_at": d["updated_at"], **archived_mark(d)}


RECORD_TABLES = ("actions", "raid", "decisions")
RECORD_MAX = 200


def records_of(con, ids):
    """({table: [row]}, [IDs found in none of the tables]) for these actions, RAID and decisions."""
    out = {t: [] for t in RECORD_TABLES}
    if not ids:
        return out, []
    marks = ",".join("?" * len(ids))
    out["actions"] = [action_row(a) for a in rows(con, f"SELECT * FROM actions WHERE id IN ({marks}) ORDER BY id", *ids)]
    out["raid"] = [raid_row(r) for r in rows(con, f"SELECT * FROM raid WHERE id IN ({marks}) ORDER BY id", *ids)]
    rby = replaced_by_map(con)
    out["decisions"] = decision_waits(con, [decision_row(d, rby) for d in
                                            rows(con, f"SELECT * FROM decisions WHERE id IN ({marks}) ORDER BY id", *ids)])
    found = {x["id"] for t in RECORD_TABLES for x in out[t]}
    return out, [i for i in ids if i not in found]


def aged_records(con, ids):
    """BL-10: {table: [row]} for those of `ids` that are archived for their age (actions and RAID; their project is live),
    read from the tables themselves (main.<table>), past the views that hide them. Never an archived project's item."""
    out = {}
    if not ids:
        return out
    marks = ",".join("?" * len(ids))
    live = "project NOT IN (SELECT code FROM main.projects WHERE archived = 1)"
    for t, make in (("actions", action_row), ("raid", raid_row)):
        out[t] = [make(r) for r in rows(con, f"SELECT * FROM main.{t} WHERE archived = 1 AND {live} AND id IN ({marks}) "
                                             "ORDER BY id", *ids)]
    return out


def records(ids, now=None, aged=False):
    """BL-304: just these items (actions, RAID, decisions) in the page's shape, for the page's targeted refresh after a save
    or a live update, with the parts an apply always changes (Review, Activity, the latest apply's time, the peek's staged
    changes, milestone names). Read only; the IDs are only looked up, never written. {"records": {table: [row]},
    "missing": [IDs in none of the tables], ...}. `aged` (BL-10): an item archived for its age is handed over too (marked
    "ar"), so search can open it with Show archived off; an archived project's item stays missing."""
    now = now or clock()
    ids = list(dict.fromkeys(i for i in ids if isinstance(i, str) and i))[:RECORD_MAX]
    con = ro_db()                        # BL-09: an archived item stays out of the views
    con.row_factory = sqlite3.Row
    try:
        recs, missing = records_of(con, ids)
        if aged and missing:
            for t, got in aged_records(con, missing).items():
                recs[t] += got
            found = {x["id"] for t in RECORD_TABLES for x in recs[t]}
            missing = [i for i in missing if i not in found]
        last_apply = con.execute("SELECT max(at) FROM applies WHERE undone_at IS NULL").fetchone()[0]
        flags, settings, rq = {}, paths.load_settings(), review_queue(con)
        first = con.execute("SELECT min(at) FROM applies").fetchone()[0]
        return {"records": recs, "missing": missing,
                "data_at": (last_apply or now.strftime("%Y-%m-%d %H:%M"))[:16],
                "review": rq, "review_focus": review.focus_queue(rq, review.spot_rate(settings, first, now.date().isoformat())),
                "peek_staged": peek_staged(), "activity": activity(con, flags), "activity_capped": flags.get("capped", False),
                "activity_older": flags.get("older", {}),
                "milestone_names": {m["id"]: [m["name"], m["status"], m["forecast_date"] or m["baseline_date"]]
                                    for m in rows(con, "SELECT * FROM milestones")}}
    finally:
        con.close()
# ===== end BL-304 =====


def ro_db():
    """A read-only connection to tracker.db in which archived projects and their items are left out (BL-09: they leave the
    default views), unless Settings shows them (dashboard.show_archived)."""
    import tracker
    return tracker.hide_archived(sqlite3.connect(f"file:{paths.DB}?mode=ro", uri=True))


def project_states(con):
    """[{code, name, state}] for Settings › Projects (BL-09): every project, archived ones included (main.projects is the table
    itself, never the view that hides them). state is active, closed or archived."""
    try:
        found = con.execute("SELECT code, name, active, archived FROM main.projects ORDER BY code").fetchall()
    except sqlite3.OperationalError:                # a database from before BL-09: no archived column until migrate
        return []
    return [{"code": c, "name": n, "state": "archived" if ar else "active" if a else "closed"} for c, n, a, ar in found]


def records_version(con=None):
    """BL-327: a short version of the records: the last change_log row, the last apply and how many were undone. Every change
    to the record goes through tracker.py apply (or undo), which logs it, so this moves with every one; a search-index refresh
    doesn't. Read only; "" when there is no database yet."""
    own = con is None
    try:
        con = con or sqlite3.connect(f"file:{paths.DB}?mode=ro", uri=True)
        a = con.execute("SELECT max(rowid) FROM change_log").fetchone()[0]
        b, c = con.execute("SELECT max(apply_id), count(undone_at) FROM applies").fetchone()
        return f"{a}:{b}:{c}"
    except sqlite3.Error:
        return ""
    finally:
        if own and con is not None:
            con.close()


def collect(now=None, timings=None):
    """Everything the dashboard shows, as one dict (embedded in dashboard.html): projects, work, review, files, Today,
    the Week ahead, the meeting hub, flow, settings and the rest, read from the tracker (read only) and the vault's
    files at `now`. BL-327: `timings`, a dict, gets the seconds its slower parts took (the file lists, the hub…)."""
    now = now or clock()
    took, started = (timings if timings is not None else {}), time.monotonic()

    def timed(part, fn):
        """fn(), its time added to `took`."""
        t0 = time.monotonic()
        try:
            return fn()
        finally:
            took[part] = took.get(part, 0.0) + time.monotonic() - t0
    today = now.date()
    settings = paths.load_settings()
    con = ro_db()
    con.row_factory = sqlite3.Row
    project_rows = rows(con, "SELECT * FROM projects WHERE active = 1 ORDER BY code")
    folders = {}
    for p in project_rows:
        try:
            folders[p["code"]] = paths.project_dir(p["code"])
        except LookupError:  # BL-228: a project without a folder simply has no files to list
            pass

    actions = [action_row(a) for a in rows(con, "SELECT * FROM actions ORDER BY id")]
    raid = [raid_row(r) for r in rows(con, "SELECT * FROM raid ORDER BY id")]
    replaced_by = replaced_by_map(con)
    decisions = [decision_row(d, replaced_by) for d in rows(con, "SELECT * FROM decisions ORDER BY date DESC, id DESC")]

    import tracker      # the highest number used across actions, RAID, decisions and promises
    projects = []
    for p in project_rows:
        mem = memory(folders[p["code"]]) if p["code"] in folders else {"client": "", "rhythm": "Weekly", "current": "",
                                                                       "images": [], "cstitle": CS_TITLE_DEFAULT, **client_report_setting("")}
        ms, slip = milestones(con, p, actions)
        tw = trail_weeks(con, p["code"], today)
        projects.append({"code": p["code"], "name": p["name"], "client": mem["client"], "health": p["health"] or "",
                         "reason": p["health_reason"] or "", "trail": [h for h, _ in tw], "trailwhy": [w for _, w in tw],
                         "trailend": trail_dates(today), "slip": slip,
                         "rhythm": mem["rhythm"], "cstitle": mem["cstitle"], "cr": mem["client_report"], "crrem": mem["client_reminder"],
                         "crlogos": mem["logos"], "partners": mem["partners"], "ms": ms, "current": mem["current"], "images": mem["images"],
                         "sponsor": p["sponsor"] or "", "phase": p["phase"] or "",
                         "undated": undated_counts(actions, raid, p["code"]),       # BL-95
                         "seq": int(tracker.next_id(con, "promises", p["code"])[-3:]) - 1,   # shared numbering
                         "ev": saved_evidence(p["code"])})                                   # BL-207

    took["tracker"] = time.monotonic() - started                 # the rows and each project's memory
    file_list = timed("files", lambda: files(folders, bool(_dig(settings, ("dashboard", "files_show_documents"), False))))
    cal = calendar(projects) if _dig(settings, ("sweep", "sources", "calendar"), True) else None
    last_apply = con.execute("SELECT max(at) FROM applies WHERE undone_at IS NULL").fetchone()[0]
    sweep = paths.SWEEP_STATE.read_text(encoding="utf-8").strip().splitlines()[0] if paths.SWEEP_STATE.exists() and \
        paths.SWEEP_STATE.read_text(encoding="utf-8").strip() else None
    act_flags = {}                                           # BL-164: whether Activity's list is capped
    out = {
        "built_at": now.strftime("%Y-%m-%d %H:%M"), "data_at": (last_apply or now.strftime("%Y-%m-%d %H:%M"))[:16],
        "records_v": records_version(con),                     # BL-327: what the live server checks before reusing this data
        "last_sweep": sweep, "sweep_due": sweep_due_info(), "live": False, "vault_path": None,
        "settings": ui_settings(settings), "people": settings.get("people", {"added": [], "hidden": []}),
        "workstreams": settings.get("workstreams", {"added": [], "hidden": []}),
        "projects": projects, "actions": actions, "raid": raid, "decisions": decision_waits(con, decisions),
        "project_states": project_states(con),                 # BL-09: Settings › Projects' Archive and Restore
        "review": (rq := review_queue(con)),
        "review_focus": review.focus_queue(rq, review.spot_rate(settings, con.execute("SELECT min(at) FROM applies").fetchone()[0], today.isoformat())),   # BL-208
        "peek_staged": peek_staged(), "activity": activity(con, act_flags), "activity_capped": act_flags.get("capped", False),
        "activity_older": act_flags.get("older", {}),          # BL-250 (fix-history-feed): older changes, for the items' own feeds
        "files": file_list,
        "files_archived": archived_files(folders),            # BL-331: Files' Archived, each with Move back
        "notes": notes_data(folders),                          # BL-301 B: each project's notes (front matter and references, no text)
        "note_templates": note_templates(),                    # BL-301 B: the templates' bodies, for the editor's / menu
        "folders": {c: f.name for c, f in folders.items()},
        "image_dirs": {c: paths.rel(paths.folder(c, "images")) for c in folders},     # BL-85: where the editor files new pictures
        "stakeholders": stakeholders(),
        "inbox": timed("inbox", lambda: inbox(projects)),
        "milestone_names": {m["id"]: [m["name"], m["status"], m["forecast_date"] or m["baseline_date"]]   # BL-27
                            for m in rows(con, "SELECT * FROM milestones")},
        "commands": commands(),
        "reminders": timed("reminders", lambda: reminders(settings, projects, file_list, today, now)),
        "help": help_sections(),
        "dismissed": settings.get("reminders", {}).get("dismissed_forever", []),
        "calendar": cal,
        "warnings": timed("warnings", lambda: early_warnings(settings, today, con)),          # BL-51
        "warn_settings": warn_settings(settings),
        "prep": timed("prep", lambda: prep(settings, projects, file_list, today, (actions, raid, decisions), con)),   # BL-49, BL-98
        "people_register": propose.people_view(),    # BL-55
        "leads": workstream_leads(con),              # BL-56
        "ws_table": workstreams(con),                # BL-58 (the "workstreams" key above is settings' old lists)
        "search": {"debounce_ms": int((settings.get("search") or {}).get("debounce_ms", 150))},       # BL-07
        "meetings": timed("meetings", lambda: inbox_meetings(settings, projects, today)),            # BL-42 phase 2
        "hub": timed("hub", lambda: meeting_hub(settings, projects, today, cal, actions, raid, decisions, folders)),   # BL-209
        "day": day_plan_facts(day_close(settings, con, today, cal), settings, today),                 # BL-206, BL-295
        "promises": promises_data(con, project_rows, today),                                         # BL-125 A
        "week": timed("week", lambda: week_ahead(today, actions, raid, projects, file_list, settings, cal, decisions)),   # BL-72
        "dev": (paths.ROOT / ".creaite-dev").exists(),     # the development repository: a discreet DEV marker
        "sweep_alerts": sweep_alerts(settings),             # BL-97, BL-99, BL-98
        "flow": timed("flow", lambda: flow_data(con, today, flow_weeks(settings), flow_snapshots((today - timedelta(weeks=flow_weeks(settings) + 1)).isoformat()))),   # BL-91
    }
    out["days"], out["intake_review"] = calendar_days(out, now), timed("intake_review", lambda: intake_review(out["meetings"], out["inbox"], out["review"], today))   # BL-293: Today's day line; #232
    return out


def saved_evidence(code):
    """BL-207: a saved Current state's sentence links ({hash: {facts, how, kept}}), or None. Derived; internal only."""
    try:
        data = json.loads((paths.EVIDENCE / f"{code}-current.json").read_text(encoding="utf-8"))
        return data.get("sentences") if isinstance(data.get("sentences"), dict) else None
    except (OSError, ValueError, AttributeError):
        return None


def workstream_leads(con):
    """{lead: [[project, workstream]]}: the workstreams each person leads (BL-56, "if known"). Read from a workstreams
    table with a lead column (BL-58); {} until there is one. The dashboard maps each lead name to the person."""
    try:
        found = rows(con, "SELECT project, name, lead FROM workstreams WHERE lead IS NOT NULL AND lead <> '' "
                          "AND COALESCE(status, 'Active') = 'Active' ORDER BY project, name")
    except sqlite3.Error:
        return {}
    out = {}
    for w in found:
        out.setdefault(w["lead"], []).append([w["project"], w["name"]])
    return out


def calendar(projects):
    """Alan's meetings saved by the sweep (Today's day view), each tagged with a project whose code or name it mentions."""
    try:
        cal = json.loads(paths.CALENDAR.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    for events in (cal.get("days") or {}).values():
        for ev in events:
            for k in PREP_ONLY:                      # BL-98: invite details stay out of the page, except in today's Prep
                ev.pop(k, None)
            t = (ev.get("title") or "").lower()
            ev["p"] = next((p["code"] for p in projects if re.search(rf"\b{re.escape(p['code'].lower())}\b", t)
                            or (p["name"] and p["name"].lower() in t)), None)
    return {"fetched": cal.get("fetched"), "days": cal.get("days") or {}}


# ===== Today brief (BL-72) =====
# Week ahead: the days Today's brief looks at, worked out here so the page only draws them. BL-319 (v1.9.2): the window runs
# day by day from today to next Monday (a Monday looks a whole week on, to the Monday after). A weekend day appears only
# when the calendar has a meeting on it; items due on a weekend move to the following Monday, marked `weekend`, and are
# shown as "due over the weekend".

def week_window(today):
    """[today … the Monday the Week ahead ends on] (BL-319: to next Monday)."""
    span = 7 - today.weekday()
    return [today + timedelta(days=i) for i in range(span + 1)]


PLAN_WORDS = re.compile(r"\b(steer\w*|board|committee|review|workshop|kick-?off|qbr|go/no-go|sign-?off|demo|planning|governance)\b", re.I)
SKIP_PREFIXES = ("todo", "to do", "info:", "fyi:")       # calendar noise Alan never plans for (sweep.ignore covers it from BL-97)
FURTHER_DAYS = 14                                        # "Further ahead": key milestones and deadlines after the week


def week_skip(title, settings):
    """A calendar title the sweep's ignore rules (BL-97) or the built-in prefixes keep out of the Week ahead."""
    t = (title or "").strip().lower()
    if t.startswith(SKIP_PREFIXES):
        return True
    for r in (settings.get("sweep") or {}).get("ignore") or []:
        if not r.get("on", True) or not ({"calendar", "all"} & set(r.get("where") or [])) or r.get("field") not in ("subject", "title"):
            continue
        txt, how = (r.get("text") or "").strip().lower(), r.get("how")
        if txt and ((how == "begins" and t.startswith(txt)) or (how == "contains" and txt in t) or (how == "equals" and t == txt)):
            return True
    return False


def plan_reason(ev, hot):
    """Why a meeting is worth preparing for, or None: Alan organises it, it's a steering-type meeting, or its project
    has overdue or Urgent open work."""
    if ev.get("organiser") is True:
        return "you organise it"
    if PLAN_WORDS.search(ev.get("title") or ""):
        return "a steering or review meeting"
    if ev.get("p") and hot.get(ev["p"]):
        return hot[ev["p"]]
    return None


def hot_projects(open_items, today):
    """{code: "2 overdue, 1 Urgent open on its project"} for the projects with overdue or Urgent open work (plan_reason)."""
    hot = {}
    for _, x in open_items:
        late = x["due"] and x["due"] < today.isoformat()
        if (late or x.get("pr") == "Urgent") and x["p"]:
            hot.setdefault(x["p"], [0, 0])[0 if late else 1] += 1
    return {p: ", ".join(w for w in (f"{n[0]} overdue" if n[0] else "", f"{n[1]} Urgent" if n[1] else "") if w) + " open on its project"
            for p, n in hot.items()}


def week_ahead(today, actions, raid, projects, file_list, settings, cal, decisions=()):
    """The Week ahead (BL-72): for each working day to next Monday (and a weekend day only when there is a meeting), the
    meetings and the open work, milestones and Urgent or High items due, Urgent first. Weekend deadlines wait until
    Monday, undated Urgent work leads, and the two weeks after list only key milestones and Urgent or High deadlines.
    BL-319 (v1.9.2): pending decisions needed in the window land on their day (decisions have no priority, so every one); a
    milestone carries `slip` when it is at risk. #112 (v2.2.0): nothing already overdue is listed (BL-319's late rows and
    their `od` are gone)."""
    days = week_window(today)
    shown = _dig(settings, ("dashboard", "week_ahead_priorities"), None)      # which priorities the Week ahead lists; empty or missing: all
    shown = set(shown) if shown else None
    events = {d: [e for e in evs if not week_skip(e.get("title"), settings)] for d, evs in ((cal or {}).get("days") or {}).items()}
    open_items = [("actions", a) for a in actions if a["st"] in ("Open", "Delayed")] + [("raid", r) for r in raid if r["st"] == "Open"]
    hot = hot_projects(open_items, today)
    out = {d.isoformat(): {"date": d.isoformat(), "dow": DAYS[d.weekday()], "weekend": d.weekday() >= 5,
                           "meetings": [{**e, "plan": plan_reason(e, hot)} for e in events.get(d.isoformat(), [])
                                        if not e.get("all_day")] if d != today else [], "items": []} for d in days}

    def land(when, item):
        """Put an item on the day it is due; a weekend day with no meetings passes it to the Monday, if that is in the
        window."""
        d = date.fromisoformat(when)
        if d.weekday() >= 5 and not out[when]["meetings"]:       # nobody is meeting: it waits until Monday
            monday = d + timedelta(days=7 - d.weekday())
            if monday.isoformat() not in out:
                return
            when, item = monday.isoformat(), {**item, "weekend": True}
        out[when]["items"].append(item)

    for a in actions:
        if a["st"] in ("Open", "Delayed") and a["due"] and today.isoformat() <= a["due"] <= days[-1].isoformat() \
                and (shown is None or a.get("pr") in shown):
            land(a["due"], {"kind": "actions", "id": a["id"], "p": a["p"], "t": a["t"], "o": a["o"], "pr": a.get("pr")})
    for r in raid:
        if r["st"] == "Open" and r["due"] and today.isoformat() <= r["due"] <= days[-1].isoformat() \
                and (shown is None or r.get("pr") in shown):
            land(r["due"], {"kind": "raid", "id": r["id"], "p": r["p"], "t": r["t"], "o": r["o"], "type": r["type"],
                            "pr": r.get("pr")})
    for p in projects:
        for m in p["ms"]:
            if m[1] and m[2] != "done" and (len(m) < 7 or m[6] not in ("Done", "Cancelled")) and \
                    today.isoformat() <= m[1] <= days[-1].isoformat():
                land(m[1], {"kind": "milestone", "id": m[3], "p": p["code"], "t": m[0], "slip": m[2] == "slip"})
    for d in decisions:                # BL-319: decisions needed in the window
        if d.get("st") == "Pending" and d.get("due") and today.isoformat() <= d["due"] <= days[-1].isoformat():
            land(d["due"], {"kind": "decisions", "id": d["id"], "p": d["p"], "t": d["t"], "o": d.get("by") or ""})
    # BL-127: no weekly or client report lines; the reminders in Needs attention (build_dashboard.reminders) carry them
    keep = [d for d in days if not out[d.isoformat()]["weekend"] or out[d.isoformat()]["meetings"]]
    rank = {"Urgent": 0, "High": 1}    # #112 (Alan, 16-10-2026): overdue work no longer leads the Week ahead (Your commitments
    for d in out.values():             # holds Alan's; the page's quiet line counts other people's), so a day is Urgent, High, the rest
        d["items"].sort(key=lambda i: rank.get(i.get("pr"), 2))
    # Urgent work with no date can't sit on a day: it leads the Week ahead instead
    undated = [{"kind": k, "id": x["id"], "p": x["p"], "t": x["t"], "o": x["o"], "pr": "Urgent"}
               for k, x in open_items if x.get("pr") == "Urgent" and not x["due"] and (shown is None or "Urgent" in shown)]
    # Further ahead: the two weeks after, key milestones and Urgent or High deadlines only, so it stays short
    end, horizon = days[-1].isoformat(), (days[-1] + timedelta(days=FURTHER_DAYS)).isoformat()
    further = [{"date": x["due"], "kind": k, "id": x["id"], "p": x["p"], "t": x["t"], "o": x["o"], "pr": x.get("pr")}
               for k, x in open_items if x["due"] and end < x["due"] <= horizon
               and x.get("pr") in ("Urgent", "High") and (shown is None or x.get("pr") in shown)]
    further += [{"date": m[1], "kind": "milestone", "id": m[3], "p": p["code"], "t": m[0]} for p in projects for m in p["ms"]
                if m[1] and m[2] != "done" and (len(m) < 7 or m[6] not in ("Done", "Cancelled")) and end < m[1] <= horizon]
    further.sort(key=lambda i: (i["date"], i["kind"] != "milestone"))
    return {"from": today.isoformat(), "to": end, "days": [out[d.isoformat()] for d in keep],
            "undated": undated, "further": further, "further_to": horizon}


def _font_face(family, weight, name):
    f = paths.TEMPLATES / "vendor" / name
    if not f.exists():
        return ""
    mime, fmt = ("font/woff2", "woff2") if name.endswith(".woff2") else ("font/ttf", "truetype")
    data = base64.b64encode(f.read_bytes()).decode("ascii")
    return (f'@font-face{{font-family:"{family}";font-style:normal;font-weight:{weight};font-display:swap;'
            f'src:url(data:{mime};base64,{data}) format("{fmt}")}}')


def help_font_faces():
    """Help's three faces embedded as @font-face rules (the dashboard and the standalone guides use the same). Google
    serves variable fonts, so one family's weights can be the same file: it is embedded once, with the weights as a
    range ("500 800"), and the browser takes each weight from it."""
    import hashlib
    groups = {}                                   # (family, file's hash) → [weights, the first file's name]
    for fam, w, n in HELP_FONTS:
        f = paths.TEMPLATES / "vendor" / n
        if f.exists():
            g = groups.setdefault((fam, hashlib.sha256(f.read_bytes()).hexdigest()), [[], n])
            g[0].append(w)
    return "\n".join(_font_face(fam, f"{min(ws)} {max(ws)}" if len(ws) > 1 else ws[0], n)
                     for (fam, _), (ws, n) in groups.items())


def font_faces():
    """Roboto and Help's faces embedded as @font-face rules, so the page needs no network (system fonts if the files are missing)."""
    rules = [_font_face("Roboto", w, n) for w, n in FONTS]
    return "\n".join(r for r in rules + [help_font_faces()] if r)


def render(data):
    """The dashboard page with data (and fonts) embedded."""
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return TEMPLATE.read_text(encoding="utf-8").replace("/*__FONTS__*/", font_faces(), 1).replace("/*__DATA__*/", payload, 1)


BUILD_LOCK = paths.STAGING / ".dashboard-build.lock"      # BL-110: one build at a time
BUILD_WAIT = float(os.environ.get("CREAITE_BUILD_WAIT") or 30)    # seconds to wait for another build before going ahead
STALE_LOCK = 120                                          # a lock this old belongs to a build that died


@contextlib.contextmanager
def build_lock():
    """An apply, the sweep and a minutes run can finish together and each rebuilds the dashboard: they take turns.
    A lock older than two minutes is broken; after BUILD_WAIT seconds a build goes ahead anyway; a lock that can't
    be made at all never stops a build."""
    held = False
    deadline = time.time() + BUILD_WAIT
    try:
        paths.STAGING.mkdir(parents=True, exist_ok=True)
        while True:
            try:
                fd = os.open(BUILD_LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode())
                os.close(fd)
                held = True
                break
            except FileExistsError:
                try:
                    if time.time() - BUILD_LOCK.stat().st_mtime > STALE_LOCK:
                        BUILD_LOCK.unlink()
                        continue
                except OSError:
                    continue
                if time.time() >= deadline:
                    break
                time.sleep(0.2)
    except OSError:  # BL-228: a lock that can't be made never stops a build
        pass
    try:
        yield
    finally:
        if held:
            try:
                BUILD_LOCK.unlink()
            except OSError:  # BL-228: the lock is already gone, or is broken as stale by the next build
                pass


def write_atomic(path, text):
    """Write to a temporary name, then rename, so a reader never sees half a page (paths.write_text_atomic)."""
    paths.write_text_atomic(path, text)


def build(now=None):
    """Build dashboard.html from the tracker and the vault, write today's flow snapshot and a dated copy in
    system/history/, and print what it holds."""
    now = now or clock()
    started = time.monotonic()
    with build_lock():
        data = collect(now)
        html = render(data)
        write_atomic(paths.DASHBOARD, html)
        write_flow_snapshot(data, now)      # BL-91: a daily record of the overdue count, from the first build on
        paths.HISTORY.mkdir(parents=True, exist_ok=True)
        snapshot = paths.HISTORY / f"dashboard-{now:%Y-%m-%d}.html"
        write_atomic(snapshot, html)
    print(f"Built {paths.rel(paths.DASHBOARD)}: {len(data['projects'])} projects, {len(data['actions'])} actions, "
          f"{len(data['raid'])} RAID, {len(data['decisions'])} decisions, {len(data['review'])} to review, "
          f"{len(data['files'])} files. Snapshot {paths.rel(snapshot)}.")
    try:
        import log as debuglog  # BL-102: optional
        debuglog.info("build", f"dashboard built in {time.monotonic() - started:.1f}s: {len(data['projects'])} projects, {len(data['actions'])} actions, "
                      f"{len(data['raid'])} RAID, {len(data['decisions'])} decisions, {len(data['review'])} to review, {len(data['files'])} files")
    except ImportError:  # BL-228: the debug log is optional
        pass
    return 0


def rebuild(now=None):
    """Rebuild the dashboard after the sweep or a minutes run has staged items (BL-110), as an apply does, so the page
    shows them. It never raises and never changes the caller's result: a failure is one printed line (and a debug-log
    entry). True if the dashboard was rebuilt."""
    try:
        build(now)
        return True
    except Exception as e:  # noqa: BLE001  the sweep's own result stands
        print(f"Note: the dashboard wasn't rebuilt ({type(e).__name__}: {str(e)[:120]}). The result above stands; "
              f"run `python3 system/scripts/build_dashboard.py` to try again.")
        try:
            import log as debuglog
            debuglog.error("build", f"rebuild failed: {type(e).__name__}")
        except ImportError:  # BL-228 (sprint-debt-safety) C: narrowed; the log is optional and its writes never raise
            pass
        return False


# ===== Insight (BL-51, BL-49, BL-54) =====
# BL-51 early warnings: read-only signals worked out here from data already held (change_log, the tracker and the
# mentions log), never stored as tracker rows. Each can be switched off, and its threshold set, in settings.json
# `warnings`. The key-person signal (BL-56 phase 2) counts owners only, never scores, and never reaches client reports.

WARN_DEFAULTS = {"redated": {"on": True, "times": 3},             # an open action re-dated this many times
                 "repeat_risk": {"on": True, "mentions": 3},      # an open risk raised in this many meetings or sweeps,
                                                                  # with no response
                 "milestone_slip": {"on": True, "weeks": 2},      # a forecast moved later this many weeks running
                 "long_open": {"on": True, "factor": 2, "min_days": 14},   # open this many times the project's usual
                 "key_person": {"on": True, "share": 50, "min_items": 6},  # one person owns more than this % (BL-56)
                 "vip_overdue": {"on": True, "days": 1},      # BL-99: an open item owned by a VIP, overdue this many days
                 "dependency": {"on": True, "near_days": 14},     # BL-90: a dependency due after what it blocks, or overdue near it
                 "decision_overdue": {"on": True, "days": 1},      # BL-53: a pending decision past its needed-by date
                 "weekend": {"on": True}}                          # BL-181: an open item due (or needed) on a weekend day
LONG_OPEN_SAMPLE = 5        # closed actions needed to know a project's usual time to close (else the portfolio's)
NOT_UNDONE = "(c.apply_id IS NULL OR c.apply_id NOT IN (SELECT apply_id FROM applies WHERE undone_at IS NOT NULL))"


def warn_settings(settings):
    """settings.json `warnings`, each signal filled from the defaults."""
    given = settings.get("warnings") or {}
    return {k: {**v, **(given.get(k) if isinstance(given.get(k), dict) else {})} for k, v in WARN_DEFAULTS.items()}


def mentions():
    """{item ID: set of sources} from the mentions log: open items raised again in a later meeting or sweep."""
    out = {}
    text = paths.MENTIONS.read_text(encoding="utf-8") if paths.MENTIONS.exists() else ""
    for line in text.splitlines():
        try:
            m = json.loads(line)
        except ValueError:
            continue
        if m.get("id"):
            out.setdefault(m["id"], set()).add(m.get("source") or m.get("at"))
    return out


def early_warnings(settings, today, con=None):
    """[{k, id, p, sig, text}] for every signal that fires, by project then item."""
    cfg = warn_settings(settings)
    own = con is None
    if own:
        con = ro_db()
    q = lambda sql, *a: con.execute(sql, a).fetchall()  # noqa: E731
    out = []
    try:
        c = cfg["redated"]
        if c.get("on"):
            for item, project, n, last in q(
                    "SELECT a.id, a.project, count(*), max(c.at) FROM change_log c JOIN actions a ON a.id = c.item_id "
                    "WHERE c.tbl = 'actions' AND c.field = 'due_date' AND c.op = 'update' AND c.old_value IS NOT NULL "
                    "AND c.old_value != '' AND (c.new_value IS NULL OR c.new_value != c.old_value) "
                    f"AND a.status IN ('Open','Delayed') AND {NOT_UNDONE} GROUP BY a.id"):
                if n >= int(c.get("times", 3)):
                    out.append({"k": "actions", "id": item, "p": project, "sig": "redated",
                                "text": f"Re-dated {n} times (last on {shown(last[:10])})"})
        c = cfg["repeat_risk"]
        if c.get("on"):
            seen = mentions()
            for item, project in q("SELECT id, project FROM raid WHERE type = 'Risk' AND status = 'Open' AND "
                                   "COALESCE(trim(response_action), '') = ''"):
                n = 1 + len(seen.get(item, ()))          # the meeting or sweep that raised it, plus each repeat
                if n >= int(c.get("mentions", 3)):
                    out.append({"k": "raid", "id": item, "p": project, "sig": "repeat_risk",
                                "text": f"Raised in {n} meetings or sweeps, with no response yet"})
        c = cfg["milestone_slip"]
        if c.get("on"):
            monday = lambda d: d - timedelta(days=d.weekday())  # noqa: E731
            this_week = monday(today)
            slips = {}
            for item, at in q("SELECT c.item_id, c.at FROM change_log c WHERE c.tbl = 'milestones' AND "
                              "c.field = 'forecast_date' AND c.op = 'update' AND c.old_value IS NOT NULL AND "
                              f"c.new_value > c.old_value AND {NOT_UNDONE}"):
                slips.setdefault(item, set()).add(monday(date.fromisoformat(at[:10])))
            for item, project, forecast in q("SELECT id, project, forecast_date FROM milestones WHERE status = 'Planned'"):
                weeks = sorted(slips.get(item, ()), reverse=True)
                if not weeks or (this_week - weeks[0]).days > 7:      # still slipping: this week or last
                    continue
                run = 1
                while run < len(weeks) and (weeks[run - 1] - weeks[run]).days == 7:
                    run += 1
                if run >= int(c.get("weeks", 2)):
                    out.append({"k": "milestones", "id": item, "p": project, "sig": "milestone_slip",
                                "text": f"Forecast moved later {run} weeks running (now {shown(forecast)})"})
        c = cfg["long_open"]
        if c.get("on"):
            import statistics
            took = {}
            for project, raised, closed in q("SELECT project, raised, closed FROM actions WHERE status = 'Closed' "
                                             "AND raised IS NOT NULL AND closed IS NOT NULL"):
                took.setdefault(project, []).append((date.fromisoformat(closed[:10]) - date.fromisoformat(raised[:10])).days)
            everyone = [d for v in took.values() for d in v]
            for item, project, raised in q("SELECT id, project, raised FROM actions WHERE status IN ('Open','Delayed') "
                                           "AND raised IS NOT NULL"):
                mine = took.get(project, [])
                sample, whose = (mine, project) if len(mine) >= LONG_OPEN_SAMPLE else (everyone, "the portfolio")
                if len(sample) < LONG_OPEN_SAMPLE:
                    continue
                usual = max(1, round(statistics.median(sample)))
                age = (today - date.fromisoformat(raised[:10])).days
                if age >= int(c.get("min_days", 14)) and age > float(c.get("factor", 2)) * usual:
                    out.append({"k": "actions", "id": item, "p": project, "sig": "long_open",
                                "text": f"Open {age} days; {whose}'s actions usually close in {usual}"})
        c = cfg["key_person"]           # Workstreams sprint (BL-56): one person owns most of a project's open items
        if c.get("on"):
            per = {}
            for project, owner in q("SELECT project, owner FROM actions WHERE status IN ('Open','Delayed') "
                                    "UNION ALL SELECT project, owner FROM raid WHERE status = 'Open'"):
                per.setdefault(project, []).append(owner or "TBC")
            for project, owners in sorted(per.items()):
                total, counts = len(owners), {}
                for o in owners:
                    if o != "TBC":
                        counts[o] = counts.get(o, 0) + 1
                if total < int(c.get("min_items", 6)) or not counts:
                    continue
                who, n = max(counts.items(), key=lambda kv: (kv[1], kv[0]))
                if 100 * n / total > float(c.get("share", 50)):
                    out.append({"k": "projects", "id": project, "p": project, "sig": "key_person", "who": who,
                                "text": f"{who} owns {n} of {total} open items ({round(100 * n / total)}%)"})
        c = cfg["vip_overdue"]          # BL-99: an overdue item owned by a VIP is always worth showing
        if c.get("on"):
            vips = {v["name"]: v["kind"] for v in propose.vip_people()}
            if vips:
                limit = (today - timedelta(days=max(1, int(c.get("days", 1))) - 1)).isoformat()
                for k, item, project, owner, due in q(
                        "SELECT 'actions', id, project, owner, due_date FROM actions WHERE status IN ('Open','Delayed') "
                        "AND due_date IS NOT NULL UNION ALL SELECT 'raid', id, project, owner, due_date FROM raid "
                        "WHERE status = 'Open' AND due_date IS NOT NULL"):
                    if owner in vips and due < limit:
                        late = (today - date.fromisoformat(due[:10])).days
                        out.append({"k": k, "id": item, "p": project, "sig": "vip_overdue", "who": owner,   # BL-288: unlabelled
                                    "text": f"Overdue {late} day{'s' if late != 1 else ''}; owned by {owner}"})
        c = cfg["dependency"]           # BL-90 part 1: a milestone link on a dependency means "this milestone depends on it"
        if c.get("on"):
            for dep, project, due, ms, forecast in q(
                    "SELECT r.id, r.project, r.due_date, r.milestone, COALESCE(m.forecast_date, m.baseline_date) FROM raid r "
                    "JOIN milestones m ON m.id = r.milestone WHERE r.type = 'Dependency' AND r.status = 'Open' AND m.status = 'Planned' "
                    "AND r.due_date IS NOT NULL AND COALESCE(m.forecast_date, m.baseline_date) IS NOT NULL"):
                days_to = (date.fromisoformat(forecast) - today).days
                if due > forecast:
                    out.append({"k": "raid", "id": dep, "p": project, "sig": "dependency", "ms": ms,
                                "text": f"{ms} forecast {shown(forecast)}, but dependency {dep} isn't due until {shown(due)}"})
                elif due < today.isoformat() and days_to <= int(c.get("near_days", 14)):
                    out.append({"k": "raid", "id": dep, "p": project, "sig": "dependency", "ms": ms,
                                "text": f"Dependency {dep} is overdue (due {shown(due)}) and {ms} is forecast for {shown(forecast)}"})
        out += decision_warnings(con, today, cfg["decision_overdue"])         # BL-53
        out += weekend_warnings(con, settings, cfg["weekend"])                # BL-181
    finally:
        if own:
            con.close()
    return sorted(out, key=lambda w: (w["p"], w["id"], w["sig"]))


# ===== BL-181 (sprint-peek-new) ===== the "weekend due date" early warning: an open action or RAID item due, or a pending decision
# needed, on a weekend day (settings.json work.weekend_days). On by default, switchable with the others; the page offers the nearest
# working days beside it.
def weekend_warnings(con, settings, c):
    """Open work and pending decisions due on a weekend day (BL-181), as early warnings, when the check is on."""
    if not c.get("on"):
        return []
    import tracker
    days, out = tracker.weekend_days(settings), []
    rows = con.execute("SELECT 'actions', id, project, due_date FROM actions WHERE status IN ('Open','Delayed') AND due_date IS NOT NULL "
                       "UNION ALL SELECT 'raid', id, project, due_date FROM raid WHERE status = 'Open' AND due_date IS NOT NULL "
                       "UNION ALL SELECT 'decisions', id, project, needed_by FROM decisions WHERE status = 'Pending' AND needed_by IS NOT NULL").fetchall()
    for k, item, project, due in rows:
        note = tracker.weekend(k, {"due_date" if k != "decisions" else "needed_by": due}, days=days)
        if note:
            out.append({"k": k, "id": item, "p": project, "sig": "weekend", "due": due,
                        "text": f"{note[0][0].upper()}{note[0][1:]}: a working day is usually meant"})
    return out
# ===== end BL-181 =====


# BL-49 meeting prep: each of today's meetings matched to a project (or the portfolio) and dated back to the last
# meeting in its series, so the page can build a brief. Alan's choices for unsure meetings are kept per series in
# settings.json `prep.series` ({series: CODE or "_portfolio"}).

def series_of(title):
    """A meeting's series: its title in lower case without [CODE] tags, numbers and punctuation."""
    t = re.sub(r"[^a-z0-9 ]", " ", re.sub(r"\[[^\]]*\]", " ", (title or "").lower()))
    return " ".join(w for w in t.split() if not w.isdigit())


def past_meetings(file_list):
    """[(YYYY-MM-DD, series)] of meetings already processed: filed minutes and transcripts, and processed.txt."""
    out = []
    for f in file_list:
        day, title, _ = paths.name_date(f["n"])
        if f["f"] in ("minutes", "transcripts") and day:
            out.append((day, series_of(re.sub(r"^Quick note - ", "", title))))
    text = paths.PROCESSED.read_text(encoding="utf-8") if paths.PROCESSED.exists() else ""
    for line in text.splitlines():
        m = re.search(r"\| fp:(\d{4}-\d{2}-\d{2})\|([^|]*)\|", line)
        if m:
            out.append((m.group(1), series_of(m.group(2))))
    return out


def project_hits(text, projects):
    """Codes of the projects a text names: a code, a project name, or a register alias or keyword (BL-49, BL-54)."""
    low, codes = (text or "").lower(), {p["code"] for p in projects}
    hits = {c for c in codes if re.search(rf"(?<![A-Za-z0-9]){c}(?![A-Za-z0-9])", text or "")}
    hits |= {p["code"] for p in projects if p["name"] and p["name"].lower() in low}
    hits |= {c for c, words in register_signals() if c in codes and any(re.search(rf"\b{re.escape(w)}\b", low) for w in words)}
    return hits


def prep_match(title, projects, remembered):
    """(code, how) for a meeting: remembered for its series, matched by a code, name, alias or keyword in the title,
    the portfolio when it says so or names several projects, else (None, "unsure")."""
    s = series_of(title)
    if remembered.get(s):
        return remembered[s], "remembered"
    hits = project_hits(title, projects)
    if "portfolio" in (title or "").lower() or len(hits) > 1:
        return "_portfolio", "portfolio"
    return (hits.pop(), "matched") if hits else (None, "unsure")


def prep(settings, projects, file_list, today, items=None, con=None):
    """{"meetings": {"HH:MM|title": {series, p, how, since, last, day, invite, rank}}, "series": remembered} for today's
    meetings, and tomorrow's keyed "YYYY-MM-DD|HH:MM|title" (BL-98). rank: the work items the invite makes relevant,
    {table: {id: [score, reason]}} (prep_rank); invite: what the ranking read (prep_invite). A later day's meeting (BL-293)
    is worked out when it is asked for: prep_page.meeting_entry, through prep_entry."""
    raw = saved_calendar_days()
    remembered = _dig(settings, ("prep", "series"), {}) or {}
    ms_names = {}
    if con is not None:
        try:
            ms_names = {m["id"]: m["name"] for m in rows(con, "SELECT id, name FROM milestones")}
        except sqlite3.Error:  # BL-228: a database without milestones: prep shows IDs
            pass
    ctx = {"projects": projects, "remembered": remembered, "history": past_meetings(file_list), "items": items,
           "ms_names": ms_names, "vips": vip_kinds(), "today": today}   # BL-228 (sprint-debt-safety): vip_kinds
    out = {}
    for day in (today, today + timedelta(days=1)):
        for ev in raw.get(day.isoformat(), []) if isinstance(raw.get(day.isoformat()), list) else []:
            found = prep_entry(ev, day, ctx)
            if found:
                out[found[0]] = found[1]
    return {"meetings": out, "series": remembered, "reports": {pr["code"]: recent_reports(pr["code"], file_list) for pr in projects}}   # BL-126


def saved_calendar_days():
    """calendar.json's {"YYYY-MM-DD": [event, …]} with every invite detail (prep reads them), or {} without one."""
    try:
        return json.loads(paths.CALENDAR.read_text(encoding="utf-8")).get("days") or {}
    except (OSError, ValueError, AttributeError):
        return {}


def prep_entry(ev, day, ctx):
    """(key, record) of one meeting's Prep brief entry, or None for a private or untitled one. The key is "HH:MM|title" today,
    "YYYY-MM-DD|HH:MM|title" any other day. ctx: {projects, remembered, history, items, ms_names, vips, today}."""
    if ev.get("private") or not ev.get("title"):
        return None
    s = series_of(ev["title"])
    code, how = prep_match(ev["title"], ctx["projects"], ctx["remembered"])
    last = max((d for d, ser in ctx["history"] if ser == s and d < day.isoformat()), default=None)
    key = f"{ev.get('start', '')}|{ev['title']}" if day == ctx["today"] else f"{day.isoformat()}|{ev.get('start', '')}|{ev['title']}"
    m = {"series": s, "p": code, "how": how, "last": last, "day": day.isoformat(),
         "since": last or (day - timedelta(days=7)).isoformat(), "invite": prep_invite(ev)}
    if ctx["items"]:
        m["rank"] = prep_rank(ev, code, ctx["items"], ctx["ms_names"], ctx["vips"], m["since"], day.isoformat())
    return key, m


# ===== BL-126 (sprint-prep-files): the recent reports a meeting's prep links =====
# The project's latest weekly report, client report and steering one-pager (at most three, newest first). Ad hoc documents are
# left out. A file that isn't there or can't be read is skipped; an online-only OneDrive file is listed as unavailable, never read.

def report_kind(f):
    """"Weekly report", "Client report" or "Steerco one-pager" for a file in the files index, else None."""
    if f.get("f") != "reports" or f.get("sub") == "Adhoc":
        return None
    n = f["n"].lower()
    if f.get("sub") == "Steerco":
        return "Steerco one-pager"
    return "Client report" if "client report" in n else "Weekly report" if "weekly report" in n else None


def recent_reports(code, file_list):
    """A project's newest report of each kind (weekly, client, steerco, ad hoc), newest first, that can be opened (or is
    online-only, and says so)."""
    best = {}
    for f in file_list:
        k = report_kind(f) if f.get("p") == code else None
        if k and (k not in best or (f.get("date") or "", f.get("mod") or "", f["n"]) > best[k][0]):
            best[k] = ((f.get("date") or "", f.get("mod") or "", f["n"]), f)
    out = []
    for k, (key, f) in sorted(best.items(), key=lambda kv: kv[1][0], reverse=True):
        try:
            real = paths.resolve(f["path"])
            online = paths.is_online_only(real)
            if not real.is_file() or not (online or os.access(real, os.R_OK)):
                continue
        except (LookupError, ValueError, OSError):
            continue
        out.append({"p": code, "kind": k, "date": f.get("date") or f.get("mod") or "", "name": f["n"], "path": f["path"], "online": online})
    return out


# ===== Decisions and schema (BL-53, sprint 5) =====
# A decision can be Pending before it is made. A pending decision past its needed-by date is an early warning (never
# stored), and a made decision whose revisit date has come is a reminder (a revisit written as words has no date to
# watch, so it only shows on the decision and the project page).

def decision_warnings(con, today, cfg):
    """[{k, id, p, sig, text}] for each pending decision whose needed-by date passed at least cfg['days'] days ago."""
    if not cfg.get("on"):
        return []
    out = []
    try:
        found = con.execute("SELECT id, project, made_by, needed_by FROM decisions WHERE status = 'Pending' AND needed_by IS NOT NULL").fetchall()
    except sqlite3.Error:                                                        # a database not yet migrated
        return []
    for item, project, by, needed in found:
        late = (today - date.fromisoformat(needed[:10])).days
        if late >= int(cfg.get("days", 1)):
            out.append({"k": "decisions", "id": item, "p": project, "sig": "decision_overdue",
                        "text": f"Decision needed {('from ' + by + ' ') if by else ''}by {shown(needed)}: {late} day{'s' if late != 1 else ''} late"})
    return out


# ===== BL-210 (sprint-decisions-needed) =====
def decision_waits(con, decisions):
    """BL-210: give each pending decision `since` (the earlier of the day it entered the tracker, from the change log, and the
    date in its source, the meeting or message that raised it; "" when neither is known) and `slips` (the IDs it blocks,
    from links), for the Decisions needed list. Derived and read only; nothing is stored. Returns the same list."""
    pend = [d for d in decisions if d["st"] == "Pending"]
    if not pend:
        return decisions
    first = dict(con.execute("SELECT item_id, min(at) FROM change_log WHERE tbl = 'decisions' AND op = 'insert' "
                             "GROUP BY item_id").fetchall())
    blocks = {}
    for frm, to in con.execute("SELECT from_item, to_item FROM links WHERE kind = 'blocks' ORDER BY to_item"):
        blocks.setdefault(frm, []).append(to)
    for d in pend:
        found = [m.group(0) for m in (re.search(r"\d{4}-\d{2}-\d{2}", t or "") for t in (first.get(d["id"]), d["src"])) if m]
        d["since"] = min(found, default="")
        d["slips"] = blocks.get(d["id"], [])
    return decisions
# ===== end BL-210 =====


def decision_revisit_reminders(today):
    """A reminder for each made decision whose revisit date (YYYY-MM-DD) has come."""
    if not paths.DB.exists():
        return []
    con = ro_db()
    try:
        found = con.execute("SELECT id, decision, revisit FROM decisions WHERE status = 'Made' AND revisit GLOB "
                            "'[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' AND revisit <= ? ORDER BY revisit, id",
                            (today.isoformat(),)).fetchall()
    except sqlite3.Error:
        return []
    finally:
        con.close()
    return [{"id": f"revisit:{i}:{r}", "text": f"{i} is due to be revisited ({shown(r)}): {t if len(t) <= 80 else t[:79] + '…'}"}
            for i, t, r in found]


# ===== Workstreams (BL-58, BL-56) =====

def workstreams(con):
    """Each project's workstreams (BL-58) with their open action and RAID counts; [] before the table exists."""
    try:
        found = rows(con, "SELECT * FROM workstreams ORDER BY project, status, name COLLATE NOCASE")
    except sqlite3.Error:
        return []
    counts = {}
    for table, still_open in (("actions", "('Open','Delayed')"), ("raid", "('Open')")):
        for r in rows(con, f"SELECT project, workstream, count(*) AS n FROM {table} WHERE status IN {still_open} "
                           "AND COALESCE(workstream, '') <> '' GROUP BY project, workstream COLLATE NOCASE"):
            counts[(table, r["project"], r["workstream"].lower())] = r["n"]
    return [{"id": w["id"], "p": w["project"], "name": w["name"], "lead": w["lead"] or "", "keywords": w["keywords"] or "",
             "aliases": w["aliases"] or "", "channel": w["channel"] or "", "st": w["status"], "created": w["created"],
             "src": w["source"], "updated_at": w["updated_at"],
             "nA": counts.get(("actions", w["project"], w["name"].lower()), 0),
             "nR": counts.get(("raid", w["project"], w["name"].lower()), 0)} for w in found]


# ===== Meetings in the Inbox (BL-42 phase 2) =====
# The Inbox's Meetings: the saved calendar (cx-sweep) from the window start to today, each with its likely project
# (meeting prep's matching and remembered series) and whether it was processed (processed.txt, key calendar:<id>).
# Reads calendar.json and processed.txt only: no other file, no Microsoft 365.

def meetings_start(settings, today):
    """The window's first day: inbox.meetings_from, "monday" (Monday of this week) or a number of days back."""
    back = _dig(settings, ("inbox", "meetings_from"), "monday")
    try:
        return today - timedelta(days=int(back))
    except (TypeError, ValueError):
        return today - timedelta(days=today.weekday())


# ── Clear day (BL-104): meetings set aside in Calendar import ─────────────────
# system/staging/intake-cleared.json: {"cleared": [{key, day, start, title, cleared}]}. A cleared meeting is not a
# processed one: nothing here touches processed.txt or the tracker. The key is the calendar event ID, or
# "day|start|title" for a meeting without one. Entries older than the look-back window are dropped.

def meeting_clear_key(day, start, title, eid=None):
    """The key Clear day remembers a meeting by: its calendar event ID, or its day, start and title."""
    return str(eid) if eid else f"{day}|{start}|{title}"


def cleared_load(settings=None, today=None):
    """The cleared entries still inside the look-back window, as a list of dicts."""
    try:
        raw = json.loads(paths.INTAKE_CLEARED.read_text(encoding="utf-8")).get("cleared") or []
    except (OSError, ValueError, AttributeError):
        return []
    first = meetings_start(settings if settings is not None else paths.load_settings(),
                           today or clock().date()).isoformat()
    return [e for e in raw if isinstance(e, dict) and e.get("key") and str(e.get("day") or "") >= first]


def cleared_save(entries):
    """Save the meetings set aside with Clear day (system/staging/intake-cleared.json), atomically."""
    paths.INTAKE_CLEARED.parent.mkdir(parents=True, exist_ok=True)
    tmp = paths.INTAKE_CLEARED.with_suffix(".tmp")
    tmp.write_text(json.dumps({"cleared": entries}, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(paths.INTAKE_CLEARED)


# #232 (v2.5.0): an entry may also carry kind ("cleared", the default, is Not needed; "later" is Later, a snooze that ends when
# the meeting's transcript arrives), and for Not needed a reason (NOT_NEEDED_REASONS) and a short note. The live server's clear
# route passes each item through unchanged, so no guarded file changes; a bad reason or kind is a ValueError (a 400).
NOT_NEEDED_REASONS = ("Informal chat", "No decisions", "Duplicate of another meeting", "Other")
SET_ASIDE_KINDS = ("cleared", "later")


def set_aside_entry(it, today):
    """One intake-cleared.json entry from a request's item, checked: (key, entry). ValueError for a bad day, kind or reason."""
    key = str(it.get("key") or "")[:300]
    day = str(it.get("day") or "")
    datetime.strptime(day, "%Y-%m-%d")                           # ValueError for a bad day
    kind, reason = str(it.get("kind") or "cleared"), str(it.get("reason") or "")
    note = " ".join(str(it.get("note") or "").split())[:200]      # one line, at most 200 characters
    if kind not in SET_ASIDE_KINDS or (reason and reason not in NOT_NEEDED_REASONS) or (kind == "later" and reason):
        raise ValueError("not one of the choices")
    extra = {k: v for k, v in (("kind", "" if kind == "cleared" else kind), ("reason", reason), ("note", note)) if v}
    return key, {"key": key, "day": day, "start": str(it.get("start") or "")[:5], "title": str(it.get("title") or "")[:200],
                 "cleared": today.isoformat(), **extra}


SET_ASIDE_EXTRA = ("kind", "reason", "note")


def clear_meetings(items, today=None):
    """Set aside the listed meetings ({key, day, start, title[, kind, reason, note]}); only those listed. A meeting already
    set aside takes the new kind, reason and note (Later, then Not needed). Returns how many were added or changed."""
    today = today or clock().date()
    have = {e["key"]: e for e in cleared_load(today=today)}
    added = 0
    for it in items:
        key, entry = set_aside_entry(it, today)
        old = have.get(key)
        if key and (old is None or any(old.get(k) != entry.get(k) for k in SET_ASIDE_EXTRA)):
            have[key] = entry if old is None else {**{k: v for k, v in old.items() if k not in SET_ASIDE_EXTRA},
                                                   **{k: entry[k] for k in ("cleared", *SET_ASIDE_EXTRA) if k in entry}}
            added += 1
    cleared_save(list(have.values()))
    return added


def restore_meetings(keys=None, day=None, today=None):
    """Bring meetings back: the listed keys, or every cleared meeting of one day. Returns how many came back."""
    entries = cleared_load(today=today)
    keys = set(keys or [])
    keep = [e for e in entries if not (e["key"] in keys or (day and e.get("day") == day))]
    cleared_save(keep)
    return len(entries) - len(keep)


def inbox_meetings(settings, projects, today):
    """{"fetched", "from", "rows": [{day, start, end, title, teams, organiser, private, id, key, p, how, series,
    processed}], "cleared": [...]}, newest day first; all-day entries left out. Cleared meetings (Clear day) are
    left out of rows and listed in `cleared` (with their reason and note, #232). A meeting set aside with Later (#232) is
    listed in `later` until its transcript arrives, then is back in rows with later_back. A meeting without an ID (an older
    calendar) has id null and can't be picked until the calendar is refreshed."""
    start = meetings_start(settings, today)
    try:
        cal = json.loads(paths.CALENDAR.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"fetched": None, "from": start.isoformat(), "rows": [], "cleared": [], "later": []}
    entries = cleared_load(settings, today)
    set_aside = {e["key"]: e for e in entries if e.get("kind") != "later"}      # Not needed (Clear day)
    snoozed = {e["key"]: e for e in entries if e.get("kind") == "later"}         # #232: Later, until the transcript arrives
    import transcripts                               # BL-42 phase 3: what the sweep found for each meeting, and what is already loaded
    checked, loaded = transcripts.load_state()["checked"], transcripts.inbox_event_ids()
    import minutes                                   # meeting_key and processed_on, read only
    remembered = _dig(settings, ("prep", "series"), {}) or {}
    drafts = {(d.get("meeting") or {}).get("key") for _, d in review.proposals()                    # waiting in Review
              if (d.get("meeting") or {}).get("key") and not (d.get("meeting") or {}).get("applied")}
    out = []
    for day, events in (cal.get("days") or {}).items():
        if not (start.isoformat() <= day <= today.isoformat()) or not isinstance(events, list):
            continue
        for ev in events:
            if ev.get("all_day"):
                continue
            title = str(ev.get("title") or "Meeting")
            private = bool(ev.get("private")) or ("private" not in ev and title == "Busy" and not ev.get("where"))
            code, how = (None, "private") if private else prep_match(title, projects, remembered)
            eid = str(ev.get("id") or "") or None
            done = minutes.processed_on(minutes.meeting_key(day, title, event_id=eid)) if eid else None
            out.append({"day": day, "start": ev.get("start") or "", "end": ev.get("end") or "", "title": title,
                        "teams": bool(ev.get("teams")), "organiser": ev.get("organiser") or False, "private": private,
                        "id": eid, "key": meeting_clear_key(day, ev.get("start") or "", title, eid),
                        "p": code, "how": how, "series": series_of(title), "processed": done,
                        "draft": bool(eid) and f"calendar:{eid}" in drafts,
                        "transcript": (checked.get(eid) or {}).get("status") if eid else None,     # available, not_transcribed, none, no_access; None: not checked yet
                        "transcript_checked": (checked.get(eid) or {}).get("checked") if eid else None,
                        "loaded": loaded.get(eid) if eid else None})
    by_day = {}                                       # newest day first, each day in time order
    for m in out:
        by_day.setdefault(m["day"], []).append(m)
    ordered = [m for d in sorted(by_day, reverse=True) for m in sorted(by_day[d], key=lambda m: m["start"])]
    return {"fetched": cal.get("fetched"), "from": start.isoformat(), **split_set_aside(ordered, set_aside, snoozed)}


def split_set_aside(ordered, set_aside, snoozed):
    """{"rows", "cleared", "later"}: Not needed meetings (with their reason and note) and Later ones leave the rows; a Later
    meeting comes back (later_back) once its transcript is available or loaded (#232)."""
    back = lambda m: m["transcript"] == "available" or bool(m["loaded"])  # noqa: E731
    rows = [dict(m, later_back=True) if m["key"] in snoozed else m for m in ordered
            if m["key"] not in set_aside and (m["key"] not in snoozed or back(m))]
    cleared = [dict(m, **{k: set_aside[m["key"]][k] for k in ("reason", "note") if set_aside[m["key"]].get(k)})
               for m in ordered if m["key"] in set_aside]
    later = [dict(m, later_since=snoozed[m["key"]].get("cleared")) for m in ordered if m["key"] in snoozed and not back(m)]
    return {"rows": rows, "cleared": cleared, "later": later}


# ===== #232 (v2.5.0) Intake and Review on one page: the merged row model =====
# One list of meetings (calendar rows, uploaded files, and drafts whose meeting is in neither) joined to their pending
# proposals, which are named by their Review number `n` (the rows of `review`, D.review on the page, stay the truth for each
# proposal; the page drops the ones it has decided). Each meeting's proposals are split by review.hold_reason, the rule
# cmd_bulk uses: "needs" (Needs your decision) and "routine" (Approve routine). Proposals from no meeting are "mail" (the
# sweep) or "other" (cx-edit, reports, weekly updates, file changes). Read only; derived from data built just before it.
# Shape: dev/proposals/intake-review-232/README.md (the seams for 232-A, 232-B and 232-C).
IR_MAIL_RUNS = ("cx-sweep",)


def proposal_meta():
    """{proposal file name: {mkey, title, day, transcript, run}} for every staged proposal (the meeting block's key, title,
    date and transcript, and the proposal's source_run). Read only."""
    out = {}
    for p, data in review.proposals():
        m = data.get("meeting") or {}
        out[p.name] = {"mkey": m.get("key") or None, "title": str(m.get("title") or ""), "day": str(m.get("date") or ""),
                       "transcript": m.get("transcript") or None, "run": str(data.get("source_run") or "")}
    return out


def intake_review(meetings, files, queue, today, meta=None, stale_after=None):
    """The merged row model for Intake and Review (#232), from the built meetings, inbox and review lists."""
    return intake_review_model(meetings or {}, files or [], queue or [], proposal_meta() if meta is None else meta, today,
                               review.stale_days() if stale_after is None else stale_after)


def _ir_split(rows):
    """{"needs": [n], "routine": [n]}: routine only when hold_reason found nothing (queue rows carry it as `hold`)."""
    out, seen = {"needs": [], "routine": []}, set()
    for r in rows:
        if r["n"] not in seen:
            seen.add(r["n"])
            hold = r.get("hold") if "hold" in r else ("held" if r.get("indiv") or not r.get("p") else "")
            out["needs" if hold else "routine"].append(r["n"])
    return out


def _ir_days(day, today):
    """Whole days from `day` (YYYY-MM-DD) to today; 0 for a missing or bad day."""
    try:
        return max(0, (today - datetime.strptime(str(day)[:10], "%Y-%m-%d").date()).days)
    except ValueError:
        return 0


def _ir_buckets(queue, meta):
    """The queue rows by where they came from: ({meeting key: rows}, {transcript path: rows}, mail rows, other rows)."""
    by_mkey, by_path, mail, other = {}, {}, [], []
    for r in queue:
        m = meta.get(r.get("file")) or {}
        mkey, tpath = m.get("mkey"), m.get("transcript")
        if mkey and (str(mkey).startswith("calendar:") or not tpath):
            by_mkey.setdefault(mkey, []).append(r)               # a calendar meeting (also a loaded transcript), or a note
        elif tpath:
            by_path.setdefault(tpath, []).append(r)              # an uploaded file's minutes: joined by the file's path
        else:
            (mail if m.get("run") in IR_MAIL_RUNS else other).append(r)
    return by_mkey, by_path, mail, other


def _ir_row(src, ident, rows, base_state, today, stale_after, **f):
    """One meeting row: its stage and state from its pending proposals (`rows`) or `base_state`, its age and its groups."""
    if rows:
        stage, state, age = "drafted", "proposals", max(q.get("age") or 0 for q in rows)
    else:
        stage, state = ("approved", "done") if base_state == "done" else ("arrived", base_state)
        age = _ir_days(f.get("day"), today)
    return {"id": "m" + hub_token(ident), "src": src, "key": None, "mkey": None, "path": None, "title": "", "day": "", "start": "",
           "end": "", "p": None, **f, "stage": stage, "state": state, "age": age, "stale": stage != "approved" and age > stale_after,
           "files": sorted({q.get("file") for q in rows if q.get("file")}), "groups": _ir_split(rows)}


def _ir_calendar(m, by_mkey, today, stale_after):
    """A calendar meeting's row (its proposals joined by "calendar:<event id>")."""
    mkey = f"calendar:{m['id']}" if m.get("id") else None
    rows = by_mkey.get(mkey, []) if mkey else []
    ready = m.get("transcript") == "available" or bool(m.get("loaded"))
    base = "done" if m.get("processed") or m.get("draft") else "ready" if ready else "waiting"
    return _ir_row("calendar", mkey or m.get("key"), rows, base, today, stale_after, key=m.get("key"), mkey=mkey,
                   title=m.get("title") or "Meeting", day=m.get("day") or "", start=m.get("start") or "", end=m.get("end") or "",
                   p=m.get("p") or (rows[0].get("p") if rows else None), private=bool(m.get("private")),
                   teams=bool(m.get("teams")), tx=m.get("transcript"), later_back=bool(m.get("later_back")))


def _ir_uploads(files, by_path, loaded_events, today, stale_after):
    """Rows for uploaded files waiting (new) or drafted; a loaded transcript is its calendar row, chats go with them."""
    out = []
    for f in files:
        if f.get("state") in ("new", "draft") and not (f.get("event") and f.get("event") in loaded_events):
            out.append(_ir_row("upload", f.get("path"), by_path.get(f.get("path"), []), "ready" if f.get("state") == "new" else "done",
                               today, stale_after, key=f.get("path"), path=f.get("path"), title=f.get("name") or "",
                               day=f.get("date") or "", p=f.get("p"), ext=f.get("ext")))
    return out


def _ir_drafts(by_mkey, by_path, used, meta, today, stale_after):
    """Rows for drafts whose meeting is in neither list (older than the window, a note, a file since moved)."""
    out = []
    for ident, rows in [*by_mkey.items(), *by_path.items()]:
        if ident in used:
            continue
        m = meta.get(rows[0].get("file")) or {}
        is_key = ident in by_mkey
        out.append(_ir_row("draft", ident, rows, "done", today, stale_after, mkey=ident if is_key else None,
                           path=m.get("transcript") if is_key else ident,
                           title=m.get("title") or ("Meeting" if is_key else Path(str(ident)).stem), day=m.get("day") or "",
                           p=rows[0].get("p")))
    return out


def _ir_counts(out, queue):
    """The stage counts, the proposals to approve and the badge (ready meetings and files, plus proposals)."""
    n = lambda f: sum(1 for r in out if f(r))  # noqa: E731
    pending, ready = len({r["n"] for r in queue}), n(lambda r: r["stage"] == "arrived" and r["state"] == "ready")
    return {"arrived": n(lambda r: r["stage"] == "arrived"), "ready": ready, "drafted": n(lambda r: r["stage"] == "drafted"),
            "approved": n(lambda r: r["stage"] == "approved"), "to_approve": pending, "badge": ready + pending}


def intake_review_model(meetings, files, queue, meta, today, stale_after):
    """Pure: the model from its inputs (unit tested in dev/tests/test_intake_review_model.py).
    {"v": 1, "meetings": [row], "mail": groups, "other": groups, "later": [..], "not_needed": [..], "counts": {..}}
    row: {id, src (calendar|upload|draft), key, mkey, path, title, day, start, end, p, stage (arrived|drafted|approved),
    state (ready|waiting|proposals|done), age, stale, files, groups {needs, routine}; a calendar row also private, teams, tx,
    later_back; an upload ext}."""
    by_mkey, by_path, mail, other = _ir_buckets(queue, meta)
    cal = meetings.get("rows") or []
    out = [_ir_calendar(m, by_mkey, today, stale_after) for m in cal]
    loaded = {m.get("id") for m in cal if m.get("loaded")}
    out += _ir_uploads(files, by_path, loaded, today, stale_after)
    used = {r["mkey"] for r in out if r["mkey"]} | {r["path"] for r in out if r["path"]}
    out += _ir_drafts(by_mkey, by_path, used, meta, today, stale_after)
    out.sort(key=lambda r: r["start"])
    out.sort(key=lambda r: r["day"], reverse=True)       # newest day first, each day in time order (as Intake); stable sorts
    keep = ("key", "day", "start", "end", "title", "p", "private")
    later = [{**{k: m.get(k) for k in keep}, "since": m.get("later_since")} for m in meetings.get("later") or []]
    not_needed = [{**{k: m.get(k) for k in keep}, "reason": m.get("reason") or "", "note": m.get("note") or ""}
                  for m in meetings.get("cleared") or []]
    return {"v": 1, "meetings": out, "mail": _ir_split(mail), "other": _ir_split(other), "later": later,
            "not_needed": not_needed, "counts": _ir_counts(out, queue)}
# ===== end #232 =====


# ===== BL-293 (sprint-today-days-server) ===== Today moves between the calendar's days. calendar_days gives every working day
# the saved calendar holds (sweep.calendar_span: Monday of this week, or inbox.meetings_from, to seven days ahead), with a weekend
# day only when it has a meeting. Each meeting carries its times, and: an ended one its follow-up (Minutes made, Transcript ready,
# No transcript, from processed.txt, the filed minutes, Review's drafts and transcripts.json, as Calendar import reads them); today
# and later its Prep key, whether it is worth preparing for (the Week ahead's plan) and its prep page (BL-286's records). A
# confidential meeting keeps only its title, times, event ID and those states; a private one is "Busy" with its times.
# #138 (Alan, 16-10-2026): a weekend day (work.weekend_days) is in the line only when something is planned on it: a timed
# meeting, or an open action, RAID item or milestone due that day. Today is always in it.
TXWHY = {"none": "No transcript for this meeting", "not_transcribed": "Not transcribed yet", "no_access": "No access to the transcript"}


def calendar_days(d, now):
    """{"first", "last", "today", "fetched", "days": [day]} for Today's day line (BL-293), from the collected data `d`. A day:
    {date, date_shown, dow, short, long, today, past, weekend, week (0 this week, 1 the next…), meetings, all_day}."""
    import sweep
    span, today = sweep.calendar_span(now.date()), now.date()
    if not span:
        return {"first": None, "last": None, "today": today.isoformat(), "fetched": None, "days": []}
    raw, look = saved_calendar_days(), day_lookups(d, now)
    out, day = [], span[0]
    while day <= span[1]:
        rec = day_record(day, raw.get(day.isoformat()), look)
        if rec:
            out.append(rec)
        day += timedelta(days=1)
    try:
        fetched = json.loads(paths.CALENDAR.read_text(encoding="utf-8")).get("fetched")
    except (OSError, ValueError, AttributeError):  # read a moment ago by calendar_span; gone since: no fetch time
        fetched = None
    return {"first": span[0].isoformat(), "last": span[1].isoformat(), "today": today.isoformat(), "fetched": fetched, "days": out}


def day_lookups(d, now):
    """What every day's meetings are looked up in, read once: projects, Calendar import's rows, filed minutes and prep pages."""
    import tracker
    today, rows_ = now.date(), import_rows(d)
    items = [x for x in d.get("actions") or [] if x["st"] in ("Open", "Delayed")] + [x for x in d.get("raid") or [] if x["st"] == "Open"]
    projects = d.get("projects") or []
    return {"today": today.isoformat(), "hm": now.strftime("%H:%M"), "monday": today - timedelta(days=today.weekday()),
            "projects": projects, "remembered": (d.get("prep") or {}).get("series") or {},
            "names": {p["code"]: p["name"] for p in projects}, "hot": hot_projects([(None, x) for x in items], today),
            "by_id": {m["id"]: m for m in rows_ if m.get("id")}, "by_time": {(m["day"], m["start"], m["title"]): m for m in rows_},
            "minutes": filed_minutes(d.get("files") or []), "pages": prep_pages_by_meeting(),
            "weekend": tracker.weekend_days(), "due": planned_days(d, items)}


def planned_days(d, items):
    """{YYYY-MM-DD} of the days an open action, RAID item or milestone is due (#138), so a weekend day with such work is planned."""
    due = {x["due"] for x in items if x.get("due")}
    for p in d.get("projects") or []:
        for m in p.get("ms") or []:
            if m[1] and m[2] != "done" and (len(m) < 7 or m[6] not in ("Done", "Cancelled")):
                due.add(m[1])
    return due


def import_rows(d):
    """Calendar import's meetings (inbox_meetings), the ones set aside with Clear day marked cleared."""
    mt = d.get("meetings") or {}
    return [dict(m, cleared=False) for m in mt.get("rows") or []] + [dict(m, cleared=True) for m in mt.get("cleared") or []]


def filed_minutes(file_list):
    """{(day, series): vault path} of the minutes filed in the projects' Minutes folders."""
    out = {}
    for f in file_list:
        day, title, _ = paths.name_date(f.get("n") or "")
        if f.get("f") == "minutes" and day:
            out.setdefault((day, series_of(re.sub(r"^Quick note - ", "", title))), f.get("path"))
    return out


def prep_pages_by_meeting():
    """{"YYYY-MM-DD|HH:MM|title": {page, at}}: the newest prep page creaite wrote for each meeting that is still there (BL-98's
    prep-pages.json), with whether BL-286 kept its content (system/staging/prep/)."""
    import prep_page
    import prep_view
    out = {}
    for rel, rec in sorted(prep_page._registry().items(), key=lambda kv: kv[1].get("at", "")):
        mid = rec.get("key", "") if len(rec.get("key", "").split("|")) >= 3 else f"{rec.get('day', '')}|{rec.get('key', '')}"
        try:
            if paths.resolve(rel).is_file():
                out[mid] = {"page": rel, "at": rec.get("at", ""), "stored": prep_view.content_path(mid).is_file()}
        except (LookupError, ValueError, OSError):  # a page moved or renamed: it no longer counts
            continue
    return out


def day_record(day, events, look):
    """One day of the day line, or None for a weekend day with nothing planned: no timed meeting and no work due (#138).
    Today is never left out."""
    events = [e for e in events if isinstance(e, dict)] if isinstance(events, list) else []
    timed = sorted((e for e in events if not e.get("all_day")), key=lambda e: (e.get("start") or "", e.get("title") or ""))
    iso, weekend = day.isoformat(), day.weekday() in look["weekend"]
    if weekend and not timed and iso != look["today"] and iso not in look["due"]:
        return None
    year = "" if str(day.year) == look["today"][:4] else f" {day.year}"
    long_ = f"{DAYS[day.weekday()]} {ordinal(day.day)} {day.strftime('%B')}{year}"
    return {"date": iso, "date_shown": shown(iso), "dow": DAYS[day.weekday()], "short": f"{DAYS[day.weekday()][:3]} {day.day}",
            "long": long_, "today": iso == look["today"], "past": iso < look["today"], "weekend": weekend,
            "week": (day - look["monday"]).days // 7,
            "meetings": [day_meeting(e, iso, look) for e in timed],
            "all_day": ["Busy" if e.get("private") else str(e.get("title") or "")[:140] for e in events if e.get("all_day")]}


def ordinal(n):
    """1 → "1st", 12 → "12th", 22 → "22nd"."""
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def day_meeting(e, iso, look):
    """One meeting of a day: times and title, then what the day line shows for it (follow-up when it has ended, Prep from today)."""
    private, conf = bool(e.get("private")), str(e.get("sensitivity") or "").lower() == "confidential"
    title, start, end = str(e.get("title") or "Meeting"), str(e.get("start") or ""), str(e.get("end") or "")
    ended = has_ended(iso, end or start, look)
    m = {"start": start, "end": end, "title": "Busy" if private else title, "private": private, "confidential": conf, "ended": ended}
    if private:
        return m
    m["id"] = str(e.get("id") or "") or None
    if not conf:
        m.update(meeting_project(e, title, look))
    if ended:
        m["follow"] = follow_state(e, iso, title, look)
    if iso >= look["today"]:
        m["prep"] = prep_state(iso, start, title, look)
        m["plan"] = None if conf else plan_reason({**e, "p": m.get("p")}, look["hot"])
    return m


def has_ended(iso, end, look):
    """Whether a meeting on `iso` ending at `end` (HH:MM) is over by the clock."""
    return iso < look["today"] or (iso == look["today"] and end <= look["hm"])


def meeting_project(e, title, look):
    """Where, Teams and the likely project (by name) of a meeting that isn't confidential."""
    code, how = prep_match(title, look["projects"], look["remembered"])
    return {"where": str(e.get("where") or ""), "teams": bool(e.get("teams")), "p": code, "how": how,
            "project_name": "Portfolio" if code == "_portfolio" else look["names"].get(code) if code else None}


def follow_state(e, iso, title, look):
    """An ended meeting's follow-up: {state: minutes|transcript|none, …}, as Calendar import works it out (BL-42, BL-119).
    minutes: processed (processed.txt), a draft waiting in Review, or minutes filed for that day and series. transcript: loaded
    into inbox/ or found by the sweep; `process` is what Process needs (cx-minutes, as Calendar import). none: `why`, and
    `checked` False when the sweep hasn't looked yet."""
    start, eid = str(e.get("start") or ""), str(e.get("id") or "") or None
    row = (look["by_id"].get(eid) if eid else None) or look["by_time"].get((iso, start, title)) or {}
    filed = look["minutes"].get((iso, series_of(title)))
    base = {"cleared": bool(row.get("cleared"))}
    if row.get("processed") or row.get("draft") or filed:
        return {**base, "state": "minutes", "processed": row.get("processed"), "processed_shown": shown(row.get("processed")),
                "draft": bool(row.get("draft")), "minutes": filed}
    tx = row.get("transcript")
    if row.get("loaded") or tx == "available":
        return {**base, "state": "transcript", "process": {"id": eid, "loaded": row.get("loaded"), "day": iso, "start": start,
                                                           "title": title}}
    if tx in TXWHY:
        return {**base, "state": "none", "why": TXWHY[tx], "checked": True}
    if not eid:
        return {**base, "state": "none", "why": "No calendar ID: refresh the calendar", "checked": False}
    if not e.get("teams"):
        return {**base, "state": "none", "why": "Not a Teams meeting, so there is no transcript", "checked": True}
    return {**base, "state": "none", "why": "Not checked yet", "checked": False}


def prep_state(iso, start, title, look):
    """A meeting's Prep from today on: its key (the Prep brief's: undated today), and its prep page when there is one (BL-287's
    Open icon: /api/prep/open {path})."""
    found = look["pages"].get(f"{iso}|{start}|{title}") or {}
    return {"key": f"{start}|{title}" if iso == look["today"] else f"{iso}|{start}|{title}", "page": found.get("page"),
            "page_at": found.get("at"), "page_at_shown": shown(found.get("at")), "stored": bool(found.get("stored"))}
# ===== end BL-293 =====


# ===== Sweep and alerts (BL-97, BL-99, BL-98) =====

def sweep_alerts(settings):
    """The sweep's ignore rules (BL-97) for Settings › Sweep, and the VIPs (BL-99): who they are, the alerts not yet
    seen (Today's VIP block) and the VIP settings."""
    import sweep                                    # read only: the rules and the alerts as sweep.py keeps them
    st, vs = sweep.vip_state(), sweep.vip_settings()
    sweep.promises_refresh(st["alerts"])           # BL-342 Part 5: a kept promise no longer open is hidden (not saved here)
    import prep_page
    return {"ignore": sweep.ignore_rules(),
            "prep_pages": prep_page.latest(),                  # BL-98: Open last prep page
            "agendas_shared": paths.external(),                # projects in OneDrive: warn before the first page there
            "vip": {"enabled": vs.get("enabled", True), "notify": vs.get("notify", True),
                    "check_minutes": vs.get("check_minutes", 30), "last_check": st["last_check"],
                    "alerts": [{k: v for k, v in a.items() if k not in ("keys", "ids")}     # BL-342: the card's keys stay in vip.json
                               for a in sweep.vip_sort([a for a in st["alerts"] if not a.get("seen")])],
                    "people": {v["name"]: v["kind"] for v in propose.vip_people()}}}


# BL-98: meeting prep ranks the brief by what the invite is about. Plain code gives the floor (shared word stems, the
# workstreams, milestones and owners an invite names, attendees who own items); the Prep page adds Claude's reading.
PREP_ONLY = ("body", "attendees", "attachments", "organiser_email")
PREP_STOP = set("""about above after again agenda also among another anything around asap attached attendee attendees
available back because been before being below best between both call calls catch catchup check come could daily dear
discuss discussion does doing done during each either else every everyone first follow following from further going good
great have having hello here hope just keep kind know last later like look looking made make many meet meeting meetings
might more most much must need needs next note notes okay only other ours over please plus point points quick really
regard regards review same see session should since some soon still such sure sync take team teams thank thanks that
their them then there these they thing things think this those through time today together tomorrow update updates very
want week weekly well were what when where which while will with within without would your yours status steps item items
action actions call meet invite invited the and for are was not but you all can has had our out new now any may who
how its own one two why yes per via let get got put set use due etc""".split())


def _prep_stem(w):
    for suf in ("ings", "ing", "ness", "ions", "ion", "ies", "ied", "ed", "es", "s", "e"):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[:-len(suf)] + ("y" if suf in ("ies", "ied") else "")
    return w


def prep_terms(text):
    """{stem: the word as written}: the words that carry meaning, stemmed, plus joined pairs ("cut over" → cutover)."""
    words = re.findall(r"[a-z][a-z0-9]*(?:[-'][a-z0-9]+)*", (text or "").lower())
    out = {}
    for i, w in enumerate(words):
        flat = w.replace("-", "").replace("'", "")
        if len(flat) >= 3 and flat not in PREP_STOP and not flat.isdigit():
            out.setdefault(_prep_stem(flat), w)
        if i + 1 < len(words) and len(w) >= 2 and len(words[i + 1]) >= 2:
            pair = w + words[i + 1]
            if len(pair) >= 6 and w not in PREP_STOP and words[i + 1] not in PREP_STOP:
                out.setdefault(_prep_stem(pair), f"{w} {words[i + 1]}")
    return out


def prep_invite(ev):
    """What the Prep brief shows of the invite (the ranking read these): body, attendees, attachments, organiser."""
    att = [{"name": a.get("name", ""), "type": a.get("type", "required"), "response": a.get("response", "none")}
           for a in ev.get("attendees") or [] if isinstance(a, dict)]
    out = {"body": ev.get("body") or "", "attendees": att, "attachments": list(ev.get("attachments") or []),
           "organiser": ev.get("organiser"), "recurrence": ev.get("recurrence") or "",
           "confidential": (ev.get("sensitivity") or "") == "confidential"}
    return {k: v for k, v in out.items() if v not in ("", [], None, False)}


def decision_for_prep(d, since, today):
    """BL-113: a decision meeting prep lists: made since the last meeting, still pending, or made with a revisit date that has come."""
    revisit = d.get("revisit") or ""
    return ((d.get("date") or "") >= since or d.get("st") == "Pending"
            or (d.get("st") == "Made" and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", revisit)) and revisit <= (today or "")))


def prep_rank(ev, code, items, ms_names, vips, since, today=None):
    """{"actions"|"raid"|"decisions": {id: [score, reason]}}: open items (decisions since `since`) of the meeting's
    project (every project for the portfolio) that the invite makes relevant, scored 2 or more. Nothing is hidden:
    the brief lists the rest after them in its usual order."""
    if not code:
        return {}
    actions, raid, decisions = items
    inp = (lambda x: True) if code == "_portfolio" else (lambda x: x["p"] == code)
    pool = [("actions", a, a["t"]) for a in actions if inp(a) and a["st"] in ("Open", "Delayed")] + \
           [("raid", r, r["t"]) for r in raid if inp(r) and r["st"] == "Open"] + \
           [("decisions", d, d["t"]) for d in decisions if inp(d) and decision_for_prep(d, since, today)]
    title = ev.get("title") or ""
    body = " ".join([ev.get("body") or "", " ".join(ev.get("attachments") or [])])
    t_terms, b_terms = prep_terms(title), prep_terms(body)
    invite = {**b_terms, **t_terms}
    low = f" {title} {body} ".lower()
    names = {a.get("name") for a in ev.get("attendees") or [] if isinstance(a, dict) and a.get("name")}
    if isinstance(ev.get("organiser"), str):
        names.add(ev["organiser"])
    terms = {(k, x["id"]): prep_terms(" ".join([text, x.get("resp") or ""]))      # workstream and milestone: their own rules
             for k, x, text in pool}
    df = {}
    for t in terms.values():
        for stem in t:
            df[stem] = df.get(stem, 0) + 1
    n = max(len(pool), 1)
    owners = [(x.get("o") or x.get("by") or "") for _, x, _ in pool]
    out = {}
    for k, x, _ in pool:
        score, why = 0.0, []
        shared = []
        for stem in set(terms[(k, x["id"])]) & set(invite):
            c = df.get(stem, 1)
            w = 2.0 if c <= 2 else 1.0 if c <= max(3, n * 0.25) else 0.0
            w *= 1.5 if stem in t_terms else 1.0
            if w:
                score += w
                shared.append((w, invite[stem]))
        if shared:
            words = []
            for _, wd in sorted(shared, key=lambda s: (-s[0], -len(s[1]))):    # longest phrases first, no repeats
                if len(words) < 2 and not any(wd in w for w in words):
                    words.append(wd)
            why.append((sum(w for w, _ in shared), 1, "invite mentions " + " and ".join(f"“{wd}”" for wd in words)))
        ws = (x.get("ws") or "").strip()
        if ws and re.search(rf"(?<![a-z0-9]){re.escape(ws.lower())}(?![a-z0-9])", low):
            score += 3
            why.append((3, 0, f"invite names the {ws} workstream"))
        msn = ms_names.get(x.get("ms")) or ""
        if msn and re.search(rf"(?<![a-z0-9]){re.escape(msn.lower())}(?![a-z0-9])", low):
            score += 3
            why.append((3, 0, f"invite names the {msn} milestone"))
        owner = x.get("o") or x.get("by") or ""
        if owner and owner != "TBC":
            first = owner.split()[0]
            if owner in names:
                score += 2
                why.append((2, 0, f"{owner} is invited"))      # BL-288: a VIP still scores higher (below), unlabelled
            elif re.search(rf"(?<![a-z]){re.escape(owner.lower())}(?![a-z])", low) or (
                    len(first) >= 3 and sum(o.split()[:1] == [first] for o in owners if o) == owners.count(owner)
                    and re.search(rf"(?<![A-Za-z]){re.escape(first)}(?![A-Za-z])", f" {title} {body} ")):
                score += 2
                why.append((2, 0, f"invite names {owner}"))
            if owner in vips and owner in names:
                score += 1
        if score >= 2:
            reason = "; ".join(r for _, _, r in sorted(why, key=lambda w: (-w[0], w[1]))[:2])   # named things before shared words
            out.setdefault(k, {})[x["id"]] = [round(score, 1), reason]
    return out


# ===== Dashboard pages (BL-87 to BL-95) =====
# BL-87: the Files page is fresh when it is looked at. files_view() is the files-only entry point: it rescans just the two
# file lists (Files and Intake) with the same files() and inbox() as a full build, without rebuilding the rest of the data.
# The live server's GET /api/files serves it.

def note_templates():
    """{name: body} of the four note templates (BL-301 B), for the note editor's insert menu."""
    import notes
    out = {}
    for name in notes.TEMPLATES:
        try:
            out[name] = notes.parse((notes.TEMPLATE_DIR / f"{name}.md").read_text(encoding="utf-8"))[1].strip("\n")
        except OSError:  # a template that can't be read is simply not offered in the / menu
            continue
    return out


def notes_data(folders):
    """{code: [note summary]} for every project with notes, and `_portfolio` (BL-301 B): what the Notes tab lists and the peek's "notes
    mention this" reads. Front matter and references only, never a note's text."""
    import notes
    out = {}
    for code in [*folders, "_portfolio"]:
        try:
            got = notes.listing(code)
        except (OSError, LookupError):  # a project whose folder can't be read simply has no notes to list
            continue
        if got:
            out[code] = got
    return out


def files_view(now=None):
    """{files, inbox, at}: the file lists alone (BL-87), for the live server's /api/files."""
    now = now or clock()
    settings = paths.load_settings()
    con = ro_db()
    try:
        codes = [r[0] for r in con.execute("SELECT code FROM projects WHERE active = 1 ORDER BY code")]
    finally:
        con.close()
    folders = {}
    for code in codes:
        try:
            folders[code] = paths.project_dir(code)
        except LookupError:  # BL-228: a project without a folder simply has no files to list
            pass
    shown = bool(_dig(settings, ("dashboard", "files_show_documents"), False))
    return {"files": files(folders, shown), "archived": archived_files(folders), "inbox": inbox([{"code": c} for c in codes]),
            "at": now.strftime("%Y-%m-%d %H:%M")}


# BL-91: Trends and flow. What the data shows over time, from dates already held: opened and closed per week, how long open items
# have been open, the overdue count by week, risks, and how often milestone forecasts have moved. Counts only, never scores of
# people; Closed and Cancelled are counted separately. Overdue over time needs the history of due-date changes: rebuilt from the
# change log, and recorded as a daily snapshot from the first build onward (system/history/flow-YYYY-MM-DD.json, not a table).
FLOW_AGE = ((0, 7, "0 to 7 days"), (8, 14, "8 to 14 days"), (15, 30, "15 to 30 days"), (31, None, "Over 30 days"))


def flow_weeks(settings):
    """dashboard.flow_weeks (8 by default; 12 is the other usual choice), kept between 4 and 26."""
    try:
        return min(26, max(4, int(_dig(settings, ("dashboard", "flow_weeks"), 8))))
    except (TypeError, ValueError):
        return 8


def flow_snapshots(since):
    """{YYYY-MM-DD: {code: {overdue, open}}} from the daily snapshots on or after `since`."""
    out = {}
    for f in sorted(paths.HISTORY.glob("flow-????-??-??.json")) if paths.HISTORY.is_dir() else []:
        if f.stem[5:] >= since:
            try:
                out[f.stem[5:]] = json.loads(f.read_text(encoding="utf-8")).get("projects") or {}
            except (OSError, ValueError):  # BL-228: an unreadable snapshot is left out of the flow history
                pass
    return out


def flow_data(con, today, weeks=8, snaps=None):
    """{code: flow} for every active project; see the keys at the end. Weeks run Monday to Sunday; the last one is this week so far.
    BL-229: the change log's moves (flow_logs), each week (flow_week), the ageing (flow_ageing), the milestone moves
    (flow_milestones) and the one-line summary (flow_summary)."""
    snaps = snaps or {}
    first = today - timedelta(days=today.weekday()) - timedelta(weeks=weeks - 1)
    spans = [(first + timedelta(weeks=i), min(first + timedelta(weeks=i, days=6), today)) for i in range(weeks)]
    due_log, fc_log = flow_logs(con)
    out = {}
    names = {r["code"]: r["name"] for r in rows(con, "SELECT code, name FROM projects WHERE active = 1")}
    acts = rows(con, "SELECT id, project, description, status, raised, closed, due_date FROM actions")
    raid = rows(con, "SELECT id, project, type, description, status, raised, closed, due_date, priority FROM raid")
    for code in names:
        A = [dict(x, k="actions") for x in acts if x["project"] == code]
        Rr = [dict(x, k="raid") for x in raid if x["project"] == code]
        risks = [x for x in Rr if x["type"] in ("Risk", "Issue")]
        week = [flow_week(A, risks, A + Rr, s, e, today, (snaps.get(e.isoformat()) or {}).get(code, {}).get("overdue"), due_log)
                for s, e in spans]
        ageing, oldest_action = flow_ageing(A + Rr, today)
        moves, by = flow_milestones(con, fc_log, code, spans[0][0])
        mix = {p: sum(1 for x in risks if x["status"] == "Open" and x["priority"] == p) for p in ("Urgent", "High", "Medium", "Low")}
        now_over, last_over = week[-1]["overdue"], week[-2]["overdue"] if len(week) > 1 else week[-1]["overdue"]
        out[code] = {"weeks": week, "period": weeks, "ageing": ageing,
                     "overdue": {"now": now_over, "last_week": last_over},
                     "risks": {"opened": sum(w["r_opened"] for w in week), "closed": sum(w["r_closed"] for w in week),
                               "cancelled": sum(w["r_cancelled"] for w in week), "mix": mix},
                     "milestones": {"moves": moves, "days": sum(m["days"] for m in by.values()),
                                    "by": sorted(by.values(), key=lambda m: (-m["moves"], m["id"]))[:3]},
                     "summary": flow_summary(week[-1], now_over, last_over, oldest_action)}
    return out


def flow_logs(con):
    """(due date moves, milestone forecast moves): {(table, id): [(day, old, new)…]} from the change log, in order; an undone
    apply never happened."""
    due_log, fc_log = {}, {}
    for r in rows(con, "SELECT c.tbl, c.item_id, c.field, c.old_value, c.new_value, c.at FROM change_log c LEFT JOIN applies a "
                       "ON a.apply_id = c.apply_id WHERE c.op = 'update' AND a.undone_at IS NULL AND "
                       "c.field IN ('due_date', 'forecast_date') ORDER BY c.rowid"):     # an undone apply never happened
        (fc_log if r["tbl"] == "milestones" else due_log).setdefault((r["tbl"], r["item_id"]), []).append(
            ((r["at"] or "")[:10], r["old_value"], r["new_value"]))
    return due_log, fc_log


def due_at(due_log, tbl, item, current, day):
    """An item's due date as it stood on `day`, from its moves."""
    ch = due_log.get((tbl, item), [])
    upto = [c for c in ch if c[0] <= day.isoformat()]
    if upto:
        return upto[-1][2]
    later = [c for c in ch if c[0] > day.isoformat()]
    return later[0][1] if later else current


def flow_week(A, risks, items, s, e, today, saved, due_log):
    """One week's counts: opened, closed and cancelled (actions, risks and all), and the overdue count at its end (a past
    week's from its saved snapshot when there is one; today's always worked out afresh)."""
    snap = saved if e < today else None    # today is always worked out afresh
    a, r, x = week_counts(A, s, e), week_counts(risks, s, e), week_counts(items, s, e)
    return {
        "start": s.isoformat(), "end": e.isoformat(),
        "a_opened": a[0], "a_closed": a[1], "a_cancelled": a[2],
        "r_opened": r[0], "r_closed": r[1], "r_cancelled": r[2],
        "opened": x[0], "closed": x[1], "cancelled": x[2],
        "overdue": snap if snap is not None else overdue_on(items, e, due_log), "from_snapshot": snap is not None}


def week_counts(xs, s, e):
    """(opened, closed, cancelled) in the week s to e."""
    in_week = lambda day: bool(day) and s.isoformat() <= day[:10] <= e.isoformat()    # noqa: E731
    return (sum(in_week(x["raised"]) for x in xs), sum(x["status"] == "Closed" and in_week(x["closed"]) for x in xs),
            sum(x["status"] == "Cancelled" and in_week(x["closed"]) for x in xs))


def overdue_on(items, day, due_log):
    """How many items were overdue on `day`: raised by then, not closed by then, and due (as the date stood then) before it."""
    n = 0
    for x in items:
        if x["raised"] and x["raised"] <= day.isoformat() and not (x["closed"] and x["closed"] <= day.isoformat()):
            d = due_at(due_log, x["k"], x["id"], x["due_date"], day)
            n += bool(d) and d < day.isoformat()
    return n


def flow_ageing(items, today):
    """(the ageing block: open items by age, and the three oldest; the oldest open action's age in days, or None)."""
    openx = [x for x in items if x["status"] in ("Open", "Delayed") and x["raised"]]
    age = lambda x: (today - date.fromisoformat(x["raised"])).days    # noqa: E731
    buckets = [sum(lo <= age(x) and (hi is None or age(x) <= hi) for x in openx) for lo, hi, _ in FLOW_AGE]
    oldest = [{"id": x["id"], "k": x["k"], "t": x["description"], "days": age(x)}
              for x in sorted(openx, key=lambda x: (-age(x), x["id"]))[:3]]
    oldest_action = max((age(x) for x in openx if x["k"] == "actions"), default=None)
    return {"labels": [l for _, _, l in FLOW_AGE], "buckets": buckets, "open": len(openx), "oldest": oldest}, oldest_action


def flow_milestones(con, fc_log, code, start):
    """(how many times the project's milestone forecasts moved since `start`, {id: {id, moves, days, name}})."""
    moves, by = 0, {}
    for (_tbl, mid), ch in fc_log.items():
        if not mid.startswith(code + "-M-"):
            continue
        for day, old, new in ch:
            if start.isoformat() <= day and old and new and old != new:
                moves += 1
                m = by.setdefault(mid, {"id": mid, "moves": 0, "days": 0})
                m["moves"] += 1
                m["days"] += (date.fromisoformat(new) - date.fromisoformat(old)).days
    for m in by.values():
        m["name"] = (rows(con, "SELECT name FROM milestones WHERE id = ?", m["id"]) or [{"name": m["id"]}])[0]["name"]
    return moves, by


def flow_summary(this, now_over, last_over, oldest_action):
    """The week in one line: "12 opened, 9 closed; 3 overdue, down from 5; the oldest open action is 20 days old"."""
    trend = "none overdue" if not now_over and not last_over else f"{now_over} overdue, " + (
        f"down from {last_over}" if now_over < last_over else f"up from {last_over}" if now_over > last_over else "the same as last week")
    return f"{this['opened']} opened, {this['closed']} closed; {trend}" + \
        (f"; the oldest open action is {oldest_action} day{'s' if oldest_action != 1 else ''} old" if oldest_action is not None else "")


def flow_line(code, today=None, settings=None):
    """The one-line flow summary of a project's week (for the weekly report): "12 opened, 9 closed; 3 overdue, down from 5; …"."""
    con = ro_db()
    con.row_factory = sqlite3.Row
    try:
        settings = settings or paths.load_settings()
        today = today or clock().date()
        return flow_data(con, today, flow_weeks(settings), flow_snapshots((today - timedelta(weeks=26)).isoformat())).get(code, {}).get("summary", "")
    finally:
        con.close()


def write_flow_snapshot(data, now):
    """Today's overdue and open counts per project, kept in system/history/ (a small file, one a day, overwritten on a later build)."""
    paths.HISTORY.mkdir(parents=True, exist_ok=True)
    day = now.strftime("%Y-%m-%d")
    (paths.HISTORY / f"flow-{day}.json").write_text(json.dumps({"date": day, "projects": {
        c: {"overdue": f["overdue"]["now"], "open": f["ageing"]["open"]} for c, f in (data.get("flow") or {}).items()}}, indent=1), encoding="utf-8")


def undated_counts(actions, raid, code):
    """Open work with no due date, to push for a date (BL-95): every open or delayed action, and every open risk or issue (an
    assumption or a dependency only when it has a response action to date); decisions never. Closed and cancelled never.
    The project page lists the same items (undatedWork in the page)."""
    a = [x for x in actions if x["p"] == code and x["st"] in ("Open", "Delayed") and not x["due"]]
    r = [x for x in raid if x["p"] == code and x["st"] == "Open" and not x["due"] and (x["type"] in ("Risk", "Issue") or x["resp"])]
    return {"actions": len(a), "raid": len(r), "total": len(a) + len(r)}


def file_activity(con, limit=40):
    """Activity lines for applied edits of a project's Current state (a file change, so it has no change_log rows): one line per
    apply, "Example Programme — current state updated", with the apply's Undo (BL-89)."""
    out = []
    names = {r["code"]: r["name"] for r in rows(con, "SELECT code, name FROM projects")}
    for r in rows(con, "SELECT apply_id, at, proposals, file_ops, undone_at FROM applies WHERE file_ops LIKE '%CLAUDE.md%' "
                       "ORDER BY apply_id DESC LIMIT ?", limit):
        try:
            ops = json.loads(r["file_ops"] or "[]")
            files = json.loads(r["proposals"] or "[]")
        except ValueError:
            continue
        if not any(o.get("op") == "write" and str(o.get("path", "")).endswith("/CLAUDE.md") for o in ops):
            continue
        for name in files:
            f = next((c for c in (paths.ROOT / name, paths.APPLIED / Path(name).name) if c.exists()), None)
            try:
                fc = (json.loads(f.read_text(encoding="utf-8")).get("file_changes") or {}) if f else {}
            except ValueError:
                continue
            title = fc.get("title") or ""
            m = re.fullmatch(r"([A-Z][A-Z0-9]{2,6}) current state", title)       # (earlier proposals were titled with the code)
            code = fc.get("project") if title.endswith(" current state") and fc.get("project") in names else (m.group(1) if m else None)
            if code:
                out.append({"at": (r["at"] or "")[:16], "what": f"{names.get(code) or code} — current state updated", "id": code,
                            "tbl": "projects", "item": names.get(code, ""), "change": "current state updated",
                            "apply_id": r["apply_id"], "undone": bool(r["undone_at"]),
                            "by": "You, in the dashboard" + (" (since undone)" if r["undone_at"] else "")})
    return out


# ===== AI drafts (sprint-drafts-fields) ===== the page learns which draft features are on (settings.json `drafting`, each on when
# missing) with the other settings, so a Draft button can say it is off without asking the live server.
_ui_settings_before_drafts = ui_settings


def _ui_settings_with_drafts(s):
    import drafts
    return {**_ui_settings_before_drafts(s), "drafting": drafts.switches(s)}


ui_settings = _ui_settings_with_drafts


_review_queue_before_drafts = review_queue


def _review_queue_with_drafts(con):
    """Review's rows, with a drafted proposal marked (its feature and the sources it was drafted from, BL-219, BL-225)."""
    out, files = _review_queue_before_drafts(con), {}
    for r in out:
        if r.get("kind") != "update" or not r.get("file"):
            continue
        if r["file"] not in files:
            try:
                files[r["file"]] = {i.get("n"): i for i in json.loads((paths.STAGING / r["file"]).read_text(encoding="utf-8")).get("items") or []}
            except (OSError, ValueError):
                files[r["file"]] = {}
        it = files[r["file"]].get(r.get("ref")) or {}
        if it.get("drafted"):
            r["drafted"], r["draft_src"] = it["drafted"], [str(x)[:240] for x in it.get("draft_sources") or []][:8]
    return out


review_queue = _review_queue_with_drafts
# ===== end AI drafts =====


# ===== AI drafts: writing (sprint-drafts-writing: BL-223, BL-224) ===== the agenda's default style (settings.json
# `drafting.agenda_style`, POAD unless "lite"), and BL-224's chase log as references only (item ID → how often and when last chased).
_ui_settings_before_writing = ui_settings


def _ui_settings_with_writing(s):
    import drafts
    return {**_ui_settings_before_writing(s), "agendaStyle": drafts.agenda_style({}, s)}


ui_settings = _ui_settings_with_writing
_sweep_alerts_before_writing = sweep_alerts


def _sweep_alerts_with_chases(settings):
    import drafts
    return {**_sweep_alerts_before_writing(settings), "chases": drafts.chase_counts()}


sweep_alerts = _sweep_alerts_with_chases
# ===== end AI drafts: writing =====


# ===== BL-221 (sprint-drafts-extraction) ===== Review's "Looks like": a repeat marked at staging (`looks_like`, extraction.py) is the
# row's possible duplicate, with where it is (same project or another), whether it is open or closed, and "Very likely" or "Possible"
# (never a percentage). Kept as new: no mark. Without a staged mark, BL-133's hint (an open item of the same project) stands, worded
# the same way. Read-only: Merge and Keep as new go through review.py (the live server's /api/review/repeat).
_review_queue_before_repeats = review_queue


def staged_items(cache, name):
    """A proposal file's items by number, read once per build."""
    if name not in cache:
        try:
            cache[name] = {i.get("n"): i for i in json.loads((paths.STAGING / name).read_text(encoding="utf-8")).get("items") or []}
        except (OSError, ValueError):
            cache[name] = {}
    return cache[name]


def repeat_mark(it, hint):
    """The row's `dup` from a staged mark, else from BL-133's hint; None when kept as new or there is neither."""
    ll = it.get("looks_like") or {}
    if ll.get("kept") or ll.get("merged"):
        return None
    if ll.get("id"):
        return {"id": ll["id"], "t": str(ll.get("t") or "")[:300], "state": ll.get("state") or "open", "same": bool(ll.get("same")),
                "project": ll.get("project") or "", "strength": ll.get("strength") or "Possible", "staged": True}
    if hint:
        return {**hint, "state": "open", "same": True, "strength": "Very likely" if hint.get("score", 0) >= 0.75 else "Possible"}
    return None


def _review_queue_with_repeats(con):
    """Review's rows, with each new item's "Looks like" mark (BL-221)."""
    out, cache = _review_queue_before_repeats(con), {}
    for r in out:
        if r.get("op") == "new" and r.get("file"):
            r["dup"] = repeat_mark(staged_items(cache, r["file"]).get(r.get("ref")) or {}, r.get("dup"))
    return out


review_queue = _review_queue_with_repeats
# ===== end BL-221 =====


# ===== BL-218 (sprint-drafts-extraction) ===== Review's "Looks done": a closing update staged from a sent mail, a reply, a Teams message
# or a meeting passage (`suggested`, extraction.py) carries its strength (Looks done, Maybe done or Not done), the evidence in one line
# ("Mail 09-10-2026 15:02 by Sara Example: “attached the SOW”") and the reason. Approve closes it; Reject asks for the reason (BL-133).
_review_queue_before_done = review_queue


def _review_queue_with_done(con):
    """Review's rows, with each probably-done update's strength and evidence (BL-218)."""
    import extraction
    out, cache = _review_queue_before_done(con), {}
    for r in out:
        if r.get("kind") != "update" or not r.get("file"):
            continue
        sg = (staged_items(cache, r["file"]).get(r.get("ref")) or {}).get("suggested") or {}
        closing_thread = sg.get("feature") == "thread" and isinstance(sg.get("done"), dict)
        if closing_thread:
            sg = sg["done"]                                          # BL-342: a thread card's close, staged on Alan's click
        if sg.get("feature") == "done" or closing_thread:
            ev = sg.get("evidence") or {}
            r["dn"] = {"strength": sg.get("strength") or "Maybe done", "ev": extraction.evidence_line(ev)[:400],
                       "reason": str(sg.get("reason") or "")[:200], "src": str(ev.get("source") or "")[:500]}
            (r.get("rec") or {}).pop("why", None)                    # the evidence leads the row: the same words once, not twice
    return out


review_queue = _review_queue_with_done
# ===== end BL-218 =====


# ===== BL-233 (sprint-drafts-extraction) ===== Activity › Quality: what you approve, edit and reject, by source and type, and how the
# AI drafts are used (quality.py, read-only). The page shows counts with their totals, never a bare percentage, and rates nothing
# under 10. Counts about extraction and drafts only; internal; no report or export reads D.quality.
_collect_before_quality = collect


def _collect_with_quality(now=None, timings=None):
    """The dashboard's data, with the Quality figures (BL-327: `timings` as collect's, Quality's time added)."""
    data = _collect_before_quality(now, timings)
    t0 = time.monotonic()
    try:
        import quality
        data["quality"] = quality.measure()
    except (ImportError, OSError, ValueError) as e:      # the tab says it couldn't count; the rest of the page is unaffected
        data["quality"] = {"error": type(e).__name__}
    if timings is not None:
        timings["quality"] = time.monotonic() - t0
    return data


collect = _collect_with_quality
# ===== end BL-233 =====


# ===== BL-209 (sprint-insight) ===== the meeting hub: one record per meeting, from invite to follow-up, gathered from what
# creaite already keeps (calendar.json, prep-pages.json, transcripts.json, the staged and applied proposals' meeting block,
# processed.txt, carried.json) and the tracker rows the meeting produced. Read only: nothing here writes or extracts.
# The key is the processing key (calendar:<event id>, or fp:<day>|<title>|<hash> for a quick note or a file with no event),
# or cal:<day>|<start>|<title> for a calendar entry with no ID; the page's address uses a short hash of it.
HUB_DAYS = 45                    # how far back processed meetings are kept on the hub


def hub_token(key):
    """A short, stable token for a meeting key, used in the page's addresses and data."""
    import hashlib
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]


def _hub_proposals():
    """(staged, data) for every staged and applied proposal with a meeting block."""
    out = []
    for folder, staged in ((paths.STAGING, True), (paths.APPLIED, False)):
        if not folder.is_dir():
            continue
        for p in sorted(folder.glob("proposed-*.json" if staged else "*.json")):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if isinstance(data.get("meeting"), dict) and data["meeting"].get("key"):
                out.append((staged, data))
    return out


def meeting_hub(settings, projects, today, cal, actions, raid, decisions, folders):
    """{token: record} for the meetings creaite knows of: the saved calendar's (not private, not all-day), every staged or applied
    minutes proposal, and processed.txt's last HUB_DAYS days. Each record holds its steps (done, current, to do or skipped), what
    it produced, the next step and what was promised to Alan."""
    import transcripts
    import prep_page
    import minutes
    rec, by_cal = {}, {}

    def get(key, **kw):
        """The meeting's record, made on first sight; values given fill only the fields it doesn't have yet."""
        r = rec.setdefault(key, {"key": key, "title": "", "day": "", "start": "", "end": "", "p": [], "teams": False, "eid": None,
                                 "invite": False, "quick": False, "prep": None, "proposals": [], "processed": None})
        for k, v in kw.items():
            if v and not r.get(k):
                r[k] = v
        return r

    remembered = _dig(settings, ("prep", "series"), {}) or {}
    for day, events in ((cal or {}).get("days") or {}).items():
        for ev in events if isinstance(events, list) else []:
            title = str(ev.get("title") or "")
            if ev.get("all_day") or ev.get("private") or not title or ("private" not in ev and title == "Busy" and not ev.get("where")):
                continue
            eid = str(ev.get("id") or "") or None
            key = f"calendar:{eid}" if eid else f"cal:{day}|{ev.get('start', '')}|{title}"
            code = ev.get("p") or prep_match(title, projects, remembered)[0]
            r = get(key, title=title, day=day, start=ev.get("start") or "", end=ev.get("end") or "", eid=eid)
            r["invite"], r["teams"] = True, bool(ev.get("teams"))
            if code and code in {p["code"] for p in projects} and code not in r["p"]:
                r["p"].append(code)
            by_cal[(day, ev.get("start") or "", title)] = key
    for rel, info in (prep_page._registry() or {}).items():               # the newest prep page for each meeting
        k, d = str(info.get("key") or ""), info.get("day") or ""
        start, title = (k.split("|")[-2:] + ["", ""])[:2] if "|" in k else ("", "")
        key = by_cal.get((d, start, title))
        if key:
            try:
                if paths.resolve(rel).is_file() and (not rec[key]["prep"] or info.get("at", "") >= rec[key].get("prep_at", "")):
                    rec[key]["prep"], rec[key]["prep_at"] = rel, info.get("at", "")
            except (LookupError, ValueError, OSError):
                pass
    for staged, data in _hub_proposals():
        m = data["meeting"]
        r = get(m["key"], title=m.get("title") or "", day=m.get("date") or "")
        for c in m.get("projects") or []:
            if c not in r["p"]:
                r["p"].append(c)
        r["quick"] = r["quick"] or m.get("kind") == "quick note" or bool(m.get("note"))
        r["proposals"].append({"staged": staged, "meeting": m, "items": data.get("items") or []})
    first = (today - timedelta(days=HUB_DAYS)).isoformat()
    bases = {}
    for c, f in (folders or {}).items():
        try:
            bases[c] = paths.rel(f)
        except (ValueError, LookupError):
            pass
    if paths.PROCESSED.exists():
        for line in paths.PROCESSED.read_text(encoding="utf-8").splitlines():
            cells = [c.strip() for c in line.split(" | ")]
            if len(cells) < 2 or not cells[1] or cells[0] < first:
                continue
            filed = [x.strip() for x in (cells[2] if len(cells) > 2 else "").split(";") if x.strip() and x.strip() != "not filed"]
            name = Path(filed[0]).stem if filed else ""
            r = get(cells[1], title=name[11:] if re.match(r"\d{4}-\d{2}-\d{2} ", name) else name,
                    day=name[:10] if re.match(r"\d{4}-\d{2}-\d{2}", name) else "")
            r["processed"] = {"on": cells[0], "filed": filed}
            for f in filed:
                code = next((c for c, base in bases.items() if f.startswith(base + "/")), None)
                if code and code not in r["p"]:
                    r["p"].append(code)
            if r["key"].startswith("fp:") and not r["invite"]:
                r["quick"] = r["quick"] or "quick note" in r["key"].lower()
    try:
        checked, loaded = transcripts.load_state()["checked"], transcripts.inbox_event_ids()
    except Exception:  # noqa: BLE001  the hub is a help: a broken store leaves the transcript step to say "not checked"
        checked, loaded = {}, {}
    soon = prep_page.due_soon_days(settings)
    ident = settings.get("identity") or {}
    me = {n.strip().lower() for n in [ident.get("name") or "", *(ident.get("short_forms") or [])] if n and n.strip()}
    rows = {**{a["id"]: ("actions", a) for a in actions}, **{x["id"]: ("raid", x) for x in raid}, **{d["id"]: ("decisions", d) for d in decisions}}
    out = {}
    for key, r in rec.items():
        if not (r["invite"] or r["proposals"] or r["processed"]):
            continue
        out[hub_token(key)] = hub_record(r, today, soon, me, rows, checked, loaded, minutes)
    return out


def review_label(pending, minutes_waiting):
    """The hub's Review button: the minutes, the items or both still waiting, or Open Review."""
    n = pending - (1 if minutes_waiting else 0)
    items = f"{n} item{'s' if n != 1 else ''}"
    return ("Review the minutes and " + items if n else "Review the minutes") if minutes_waiting else \
        (f"Review the {items}" if n else "Open Review")


def hub_record(r, today, soon, me, rows, checked, loaded, minutes):
    """One meeting's record for the hub. BL-229: what it produced (hub_produced), its steps (hub_steps), the current one and
    the next action (hub_next)."""
    t, hm = today.isoformat(), clock().strftime("%H:%M")
    when = {"future": bool(r["day"]) and (r["day"] > t or (r["day"] == t and (r["end"] or r["start"] or "99:99") > hm)),   # not ended yet
            "started": bool(r["day"]) and (r["day"] < t or (r["day"] == t and bool(r["start"]) and r["start"] <= hm))}
    tstat = (checked.get(r["eid"]) or {}).get("status") if r["eid"] else None
    staged = [p for p in r["proposals"] if p["staged"]]
    meet = next((p["meeting"] for p in staged), None) or next((p["meeting"] for p in r["proposals"]), None) or {}
    coverage = meet.get("coverage") or None
    produced = hub_produced(r, rows)
    minutes_state = meet.get("minutes_decision")
    in_review = any(p["staged"] for p in r["proposals"])
    pending = sum(1 for x in produced if x["you"]) + (1 if in_review and minutes_state == "pending" else 0)
    owner = lambda o: re.sub(r"\s*\([^)]*\)\s*$", "", o or "").strip()  # noqa: E731
    open_actions = [x for x in produced if x["k"] == "actions" and x.get("id") and x["state"] in ("Open", "Delayed")]
    due_soon = [x for x in open_actions if x.get("due") and x["due"] <= (today + timedelta(days=soon)).isoformat()]
    steps = hub_steps(r, when, tstat, loaded, coverage, in_review, pending, due_soon)
    nxt = hub_next(steps, tstat, pending, in_review and minutes_state == "pending", due_soon)
    produced.sort(key=lambda x: (not x["you"], x["state"] == "rejected", x.get("id") or ""))
    promised = [x["id"] for x in open_actions if x.get("o") and owner(x["o"]).lower() not in me]
    carried = {c["point"] for c in minutes.carried_load() if c.get("key") == r["key"]}
    return {"key": r["key"], "title": r["title"] or "Meeting", "day": r["day"], "start": r["start"], "end": r["end"], "p": r["p"],
            "quick": r["quick"], "eid": r["eid"], "prep": r["prep"], "steps": steps, "items": produced[:60],
            "counts": {"items": sum(1 for x in produced if not x.get("upd") and x["state"] != "rejected"),
                       "updates": sum(1 for x in produced if x.get("upd")), "pending": pending,
                       "rejected": sum(1 for x in produced if x["state"] == "rejected")},
            "next": nxt, "due": [x["id"] for x in due_soon], "promised": promised,
            "coverage": [{**c, "carried": c.get("point") in carried} for c in (coverage or [])],
            "minutes": meet.get("minutes_decision"), "filed": (r["processed"] or {}).get("filed") or [],
            "files": hub_files(r), "draft": meet.get("draft") if in_review else None, "processed": (r["processed"] or {}).get("on")}


def hub_produced(r, rows):
    """What the meeting produced: its new items (tracker rows once applied), the rejected ones and its updates."""
    produced = []
    for p in r["proposals"]:
        for it in p["items"]:
            produced.append(produced_update(it) if it.get("op") == "update" else produced_item(it, rows))
    return produced


def produced_update(it):
    """An update the meeting produced, with its state."""
    state = "applied" if it.get("applied") else it.get("decision") or "pending"
    return {"k": it.get("table"), "id": it.get("id"), "t": "Update: " + ", ".join(sorted((it.get("changes") or {}).keys())),
            "state": state, "you": state == "pending", "upd": True}


def produced_item(it, rows):
    """A new item: rejected, a tracker row once applied, or as staged."""
    v = it.get("values") or {}
    if it.get("decision") == "rejected" and not it.get("applied"):
        return {"k": it.get("table"), "t": v.get("description") or v.get("decision") or "", "state": "rejected", "you": False}
    rid = it.get("result_id") if it.get("applied") else None
    if rid and rid in rows:
        return produced_row(rid, *rows[rid])
    return produced_staged(it, v)


def produced_row(rid, k, x):
    """An applied item as the tracker row it became."""
    return {"k": k, "id": rid, "t": x.get("t") or "", "o": x.get("o") or x.get("by") or "", "due": x.get("due"),
            "state": x.get("st") or "", "you": False}


def produced_staged(it, v):
    """A new item as staged: pending (yours to decide) or approved, not yet applied."""
    state = it.get("decision") or "pending"
    return {"k": it.get("table"), "n": it.get("n"), "t": v.get("description") or v.get("decision") or "",
            "o": v.get("owner") or v.get("made_by") or "", "due": v.get("due_date") or v.get("needed_by"),
            "state": state, "you": state == "pending"}


def hub_steps(r, when, tstat, loaded, coverage, in_review, pending, due_soon):
    """The meeting's steps, [id, label, done|todo|skip|current, words], with the first one still to do marked current
    (before the meeting: only its prep)."""
    has_draft = bool(r["proposals"]) or bool(r["processed"])
    steps = [step_invite(r), step_prep(r, when["started"]), step_transcript(r, when["future"], tstat, loaded, has_draft),
             ["draft", "Draft minutes", "done" if has_draft else "todo",
              "Quick note filed" if r["quick"] and has_draft else "Drafted" if has_draft else "Not drafted yet"],
             step_coverage(r, coverage, has_draft), step_review(r, in_review, pending, has_draft),
             step_follow(r, in_review, due_soon)]
    for s in steps:                                   # the first step still to do is the current one (before the meeting: only its prep)
        if s[2] == "todo" and (not when["future"] or s[0] == "prep"):
            s[2] = "current"
            break
    return steps


def step_invite(r):
    """The invite step: in the calendar, a quick note, or no entry."""
    return ["invite", "Invite", "done" if r["invite"] else "skip",
            (f"In your calendar, {r['start']}" if r["start"] else "In your calendar") if r["invite"] else
            ("No invite: a quick note" if r["quick"] else "No calendar entry")]


def step_prep(r, started):
    """The prep page step: made, still to make before the meeting, or none."""
    return ["prep", "Prep page", "done" if r["prep"] else ("todo" if r["invite"] and not started else "skip"),
            "Prep page made" if r["prep"] else ("Not made yet" if r["invite"] and not started else "No prep page")]


def step_transcript(r, future, tstat, loaded, has_draft):
    """The transcript step, from the meeting's kind, time and transcript status."""
    if r["quick"]:
        return ["transcript", "Transcript", "skip", "A quick note: no transcript"]
    if has_draft or (r["eid"] and r["eid"] in loaded):
        return ["transcript", "Transcript", "done", "Loaded" if not has_draft else "Processed"]
    if future:
        return ["transcript", "Transcript", "todo", "After the meeting"]
    if tstat in ("not_transcribed", "none", "no_access"):
        return ["transcript", "Transcript", "skip", {"not_transcribed": "Not transcribed", "none": "No transcript",
                                                     "no_access": "No access to the transcript"}[tstat]]
    return ["transcript", "Transcript", "todo", "Ready to load" if tstat == "available" else
            ("Not a Teams meeting" if r["invite"] and not r["teams"] else "Not checked yet")]


def step_coverage(r, coverage, has_draft):
    """The coverage step: the agenda's points discussed, or why it wasn't checked."""
    if coverage:
        missed = sum(1 for c in coverage if c.get("verdict") == "Not discussed")
        return ["coverage", "Coverage", "done", f"{missed} of {len(coverage)} not discussed" if missed else f"All {len(coverage)} points discussed"]
    return ["coverage", "Coverage", "skip" if (has_draft or r["quick"]) else "todo",
            "No agenda, so not checked" if (has_draft or r["quick"]) else "After the minutes, when there is an agenda"]


def step_review(r, in_review, pending, has_draft):
    """The review step: waiting for you, decided, or filed."""
    if in_review:
        return ["review", "Review", "todo", f"{pending} waiting for you" if pending else "Decided, not applied"]
    return ["review", "Review", "done" if has_draft else "todo", "Approved and filed" if r["processed"] else
            ("Decided" if has_draft else "Nothing to review yet")]


def step_follow(r, in_review, due_soon):
    """The follow-up step: actions due soon, or nothing yet."""
    if due_soon:
        return ["follow", "Follow-up", "todo", f"{len(due_soon)} action{'s' if len(due_soon) != 1 else ''} due soon"]
    return ["follow", "Follow-up", "done" if (r["processed"] and not in_review) else "todo",
            "Nothing due soon" if (r["processed"] and not in_review) else "After review"]


def hub_next(steps, tstat, pending, minutes_waiting, due_soon):
    """The next action for the current step, or None."""
    cur = next((s[0] for s in steps if s[2] == "current"), None)
    if cur == "follow" and not due_soon:
        return None
    return {"prep": {"act": "prep", "label": "Make the prep page"},
            "transcript": {"act": "intake", "label": "Load the transcript" if tstat == "available" else "Open Intake"},
            "draft": {"act": "intake", "label": "Process the transcript"},
            "coverage": {"act": "intake", "label": "Process the transcript"},
            "review": {"act": "review", "label": review_label(pending, minutes_waiting)},
            "follow": {"act": "work", "label": f"See the {len(due_soon)} action{'s' if len(due_soon) != 1 else ''} due" if due_soon else "Nothing yet"}}.get(cur)


def hub_files(r):
    """The meeting's files: what was filed, the copies its minutes make, and its quick note."""
    return list(dict.fromkeys([*((r["processed"] or {}).get("filed") or []), *[o.get("to") for p in r["proposals"]
                for o in (p["meeting"].get("file_ops") or []) if o.get("op") == "copy" and o.get("to")],
                *[p["meeting"]["note"] for p in r["proposals"] if p["meeting"].get("note")]]))


# ===== BL-206 (sprint-insight) ===== Close the day: the evening card's facts, all read from what creaite already holds. Nothing is
# extracted and nothing written here; the only record is the closed day itself (system/staging/day-closed.json, the live server's).
def next_working_day(today, settings):
    """The first day after today that isn't a weekend day (settings)."""
    import tracker
    off = tracker.weekend_days(settings)
    d = today + timedelta(days=1)
    while d.weekday() in off:
        d += timedelta(days=1)
    return d


# ===== BL-125 A: promises on the page =====
def promises_data(con, project_rows, today):
    """The open promises on active projects made by Alan or to him, for Today's You owe and Waiting on and a person's page:
    [{id, p, t, by, to, due, raised, src, od (days overdue), quiet (days since raised, raised again or edited by Alan), list}],
    where list is "owe", "waiting" (overdue, made to Alan) or "" (made to Alan, not yet due or undated). tracker.promise_lists
    decides the two lists, so the page, `read promises --list` and the weekly report agree. A promise between two other
    people is left out (BL-125 A: only promises made by Alan or to him are his to track)."""
    import tracker
    codes = {p["code"] for p in project_rows}
    open_rows = [r for r in rows(con, "SELECT * FROM promises WHERE status = 'Open' ORDER BY id") if r["project"] in codes]
    lists = tracker.promise_lists(open_rows, today, con)
    owe, waiting = {r["id"] for r in lists["you_owe"]}, {r["id"] for r in lists["waiting_on"]}
    mine, heard = tracker.my_names(), tracker.last_touched(con)
    out = []
    for r in open_rows:
        to_me = str(r.get("promised_to") or "").strip().lower() in mine
        if r["id"] not in owe and not to_me:
            continue
        quiet = tracker.days_between(max(str(r.get("raised") or ""), heard.get(r["id"], "")), today)
        out.append({"id": r["id"], "p": r["project"], "t": r["description"], "by": r["promised_by"], "to": r["promised_to"],
                    "due": r.get("due_date"), "raised": r.get("raised"), "src": r.get("source"),
                    "od": max(tracker.days_between(r.get("due_date"), today), 0), "quiet": max(quiet, 0),
                    "list": "owe" if r["id"] in owe else "waiting" if r["id"] in waiting else ""})
    return out
# ===== end BL-125 A =====


def day_closed_load():
    """The days Alan has closed (system/staging/day-closed.json), {day: "HH:MM"}; empty if there are none."""
    import close_day as day_plan                     # BL-295: the file also keeps the day's plan (references only)
    return day_plan.load()["days"]


def day_close(settings, con, today, cal):
    """{"moved": {closed, applied, decisions}, "promised": [...], "tomorrow": {day, meetings}, "closed", "last", "from"}."""
    t = today.isoformat()
    live = "(c.apply_id IS NULL OR c.apply_id IN (SELECT apply_id FROM applies WHERE undone_at IS NULL)) AND c.op != 'undo'"
    one = lambda sql: con.execute(sql, (t,)).fetchone()[0] or 0  # noqa: E731
    moved = {"closed": one(f"SELECT COUNT(DISTINCT c.item_id) FROM change_log c WHERE substr(c.at,1,10) = ? AND {live} "
                           "AND c.tbl = 'actions' AND c.field = 'status' AND c.new_value = 'Closed'"),
             "applied": one(f"SELECT COUNT(DISTINCT c.tbl || c.item_id) FROM change_log c WHERE substr(c.at,1,10) = ? AND {live} "
                            "AND c.tbl IN ('actions','raid','decisions','milestones')"),
             "decisions": one(f"SELECT COUNT(DISTINCT c.item_id) FROM change_log c WHERE substr(c.at,1,10) = ? AND {live} "
                              "AND c.tbl = 'decisions' AND ((c.field = 'status' AND c.new_value = 'Made') OR (c.op = 'insert' AND c.field = 'status' AND c.new_value = 'Made'))")}
    ident = settings.get("identity") or {}
    me = {n.strip().lower() for n in [ident.get("name") or "", *(ident.get("short_forms") or [])] if n and n.strip()}
    promised = []
    for p, data in review.proposals():                   # until promises (BL-125 stage A): today's proposed actions you own, still pending
        made = str(data.get("created") or "")[:10]
        for it in data.get("items") or []:
            v = it.get("values") or {}
            owner = re.sub(r"\s*\([^)]*\)\s*$", "", v.get("owner") or "").strip().lower()
            if it.get("op") == "new" and it.get("table") == "actions" and it.get("decision") == "pending" and not it.get("applied") \
                    and owner in me and (made == t or v.get("raised") == t):
                promised.append({"file": p.name, "n": it.get("n"), "t": v.get("description") or "", "p": v.get("project"), "due": v.get("due_date")})
    nxt = next_working_day(today, settings)
    import prep_page
    pages = {(r.get("day"), str(r.get("key") or "").split("|", 1)[-1] if str(r.get("key") or "").count("|") >= 2 else str(r.get("key") or ""))
             for r in (prep_page._registry() or {}).values()}
    meets = []
    for ev in ((cal or {}).get("days") or {}).get(nxt.isoformat()) or []:
        if ev.get("all_day") or ev.get("private"):
            continue
        slot = f"{ev.get('start', '')}|{ev.get('title', '')}"
        meets.append({"start": ev.get("start") or "", "end": ev.get("end") or "", "title": ev.get("title") or "", "p": ev.get("p"),
                      "id": ev.get("id"), "prep": (nxt.isoformat(), slot) in pages})
    meets.sort(key=lambda m: m["start"])
    days = day_closed_load()
    before = sorted(d for d in days if d < t)
    return {"today": t, "moved": moved, "promised": promised[:20], "tomorrow": {"day": nxt.isoformat(), "meetings": meets},
            "closed": days.get(t), "last": ({"day": before[-1], "at": days[before[-1]]} if before else None),
            "from": _dig(settings, ("day", "close_from"), None), "friday": today.weekday() == 4}


def day_plan_facts(day, settings, today):
    """BL-295: the Close the day facts with First thing tomorrow (the last closed day's list, read afresh: `first`) and the
    catch-up sweep's settings (`catchup`: {mode, after})."""
    import close_day as day_plan
    mode, after = day_plan.catchup_settings(settings)
    return {**day, "first": day_plan.first_thing(today), "catchup": {"mode": mode, "after": after}}


def close_day(today, at, plan=None):
    """Record that the day was closed (the one write): {"days": {YYYY-MM-DD: HH:MM}}, the last 30 kept, and BL-295's plan for
    it (references only; close_day.record). Returns the days."""
    import close_day as day_plan
    return day_plan.record(today, at, plan)["days"]

if __name__ == "__main__":
    try:
        import log as debuglog  # BL-102: the debug log (not `log`: some scripts have a function of that name); a script runs without it
    except ImportError:
        debuglog = None
    sys.exit(debuglog.main("build_dashboard.py", build) if debuglog else build())
