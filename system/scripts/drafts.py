"""creaite AI drafts (BL-218 to BL-227): the shared scaffold, and the field drafts of sprint-drafts-fields.

A draft is a suggestion, never a write. Plain code here gathers the facts and their sources from the tracker, the registers and the
vault; a model is asked only to word them (through the live server's run engine, `Run(..., kind="generate")`: read-only tools, one
run at a time, progress and Stop). The text lands where Alan already edits or approves: an unsaved field in the peek, a pending
proposal in Review (individually approved), or a dialog. Nothing here writes to the tracker.

  python3 system/scripts/drafts.py context              JSON request on stdin → {feature, kind, prompt, facts, sources} or {nothing}
  python3 system/scripts/drafts.py result               JSON {request, context, reply} on stdin → the parsed draft and its checks
  python3 system/scripts/drafts.py stat FEATURE EVENT [N]   count an event (offered, used, edited, rejected) in draft-stats.json
  python3 system/scripts/drafts.py stats [--json]       the counts, per feature
  python3 system/scripts/drafts.py features [--json]    each feature, its label and whether it is on (settings.json `drafting`)
  python3 system/scripts/drafts.py chase record --ids A,B [--mode chase|help|decision|update|followup]   "I sent it" (BL-224, BL-298)
  python3 system/scripts/drafts.py chase-pane          JSON {id, …} on stdin → BL-298's Draft chase: mode, recipient, suggestions, draft

How to add a draft kind (the next sprints do this):
  1. A feature switch: add it to FEATURES (id, label, help). Settings › General › AI drafts lists it from the page's DRAFTFEATURES,
     and settings.json `drafting.<id>` turns it off (on when missing).
  2. A builder: `@kind("name", "feature")` on `def build(con, req)`, returning `Draft(prompt_values, sources, ...)` from plain code, or
     raising `Nothing("Nothing new since 03-10-2026")` (shown as is, nothing is asked of the model) or `Refused("why")`.
  3. A prompt template: `system/templates/drafts/<name>.md`, with `$placeholders` filled by string.Template (values are inserted,
     never formatted, so braces in a value are safe). `$sources` is always the numbered source list; ask for `[S1]` tags.
  4. Optionally `@parser("name")` to split the reply into parts (the default: the text, its sources marked per sentence), and
     `@stager("name")` for a kind that drafts several items: its parsed result becomes pending proposals (`proposal_file`), each
     item carrying `drafted: <feature>` and `drafted_text`, so Review approves it on its own and counts it when decided.
  5. In the page: `draftBtn(kind, label, attrs)` where the button belongs, and `draftAsk({kind, ...})`, which streams the run and
     returns the parsed result; `draftCard(...)` shows it with "Drafted from…", Use and Discard, and counts what Alan does.

Counts (Alan, 11-10-2026): `system/staging/draft-stats.json` holds, per feature, how many drafts were offered, used as written,
used after an edit, and rejected. Counts only: never text, IDs or names.
Set CREAITE_NOW="YYYY-MM-DD HH:MM" to fix the clock (tests).
"""
import json
import os
import re
import sqlite3
import string
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import linktext  # noqa: E402
import paths  # noqa: E402
import calendar_gateway  # noqa: E402  (#375 E1: the one read path for the saved calendar)
import tracker  # noqa: E402

sys.modules.setdefault("drafts", sys.modules[__name__])     # run as a script, report.py's `import drafts` is this same module
TEMPLATE_DIR = paths.TEMPLATES / "drafts"
STATS = paths.STAGING / "draft-stats.json"
EVENTS = ("offered", "used", "edited", "rejected")
NOTHING_EVENT = "nothing"       # #272: a Suggest run that came back with nothing to suggest; counted by drafts.py itself, never by the page
MAX_SOURCES = 12

# id: (label, what it drafts). The order is the order Settings lists them. Later sprints add theirs here.
FEATURES = {
    "update": ("Draft the latest update", "An action's latest update from what happened since the last one; Draft updates for stale actions"),
    "client": ("Draft client wording", "Plain client messaging from the item's own text, with what was taken out"),
    "thinking": ("Suggest the thinking fields", "A decision's options and reasoning; a risk's response, impact and likelihood"),
    "reason": ("Draft the reason for a health or forecast change", "One sentence from the evidence creaite already holds"),
    # ===== BL-221 (sprint-drafts-extraction) =====
    "repeat": ("Spot repeats of existing items",
               "Marks a suggestion that looks like an item already in your project record; Merge, Keep or Reject in Review"),
    # ===== BL-218 (sprint-drafts-extraction) =====
    "done": ("Spot items that are probably done",
             "The mail and Teams check and the minutes suggest closing an open item when a sent mail, reply or meeting shows it finished"),
    # ===== BL-220 (sprint-drafts-extraction) =====
    "sharpen": ("Sharpen a vague action", "A clear, verb-first title for a vague action, beside the original; you pick one"),
    # ===== BL-223, BL-224, BL-227 (sprint-drafts-writing) =====
    "agenda": ("Draft the agenda and invite text", "From the Prep page: a POAD for the invite and a timed agenda, to copy"),
    "email": ("Polish the email wording",
              "Draft email's cover paragraph reworded in a warm, neutral or firm tone; the table is untouched"),
    "forms": ("Write the status in other forms",
              "Generate's Form: a steering note, a three-line update, an email paragraph or a Teams message"),
    # ===== BL-286 C (sprint-prep-shape): its switch, with the page's DRAFTFEATURES (stores/prepShape.js) =====
    "shape": ("Shape the meeting", "Prep: reads your focus and aim, then drafts the objective, talking points, ask and what's "
              "carried over, each line cited"),
    # ===== v2.1.0 #90: the sheet's ✦ =====
    "report-section": ("Redraft a report section", "The weekly or client report's ✦, and Polish, Shorter, Executive or your own words on "
                       "one section, from the week's facts (a client report: client-visible facts only)"),
    "minutes-section": ("Redraft a minutes section", "The minutes' ✦, and Polish, Shorter, Executive or your own words on one section "
                        "(the distributed version: nothing marked Internal only or withheld)"),
}
# BL-342 Part 5: counted like a feature, with no switch of its own (Alan, 15-10-2026): the promises a thread's card offers
# from Alan's own messages. Activity › Quality lists it by this label; Settings › AI drafts lists only FEATURES (the switches).
COUNTED = {"promise": "Promises from your own messages"}
# BL-286 (sprint-prep-server): the kind "shape" counts under the feature "shape" (draft-stats.json takes any lower-case feature
# name) and is on unless settings.json `drafting.shape` is false. Its Settings switch is in FEATURES above (sprint-prep-shape).
ID_RE = re.compile(r"\b[A-Z][A-Z0-9]{2,6}-(?:[A-Z]-)?\d{3}\b")
SECRET_WORDS = re.compile(r"\b(confidential|restricted)\b", re.I)
STOP = set("the a an and or of to for in on at by with from is are was were be been it this that these those as into not no "
           "will shall can could should would has have had do does did our we you they their them its".split())


class Nothing(Exception):
    """Nothing to draft from: the message is shown as it is, and no model is asked."""


class Refused(Exception):
    """The draft isn't allowed (a confidential item, a closed item, the wrong kind of item)."""


class Draft:
    def __init__(self, values, sources, item=None, extra=None):
        self.values, self.sources, self.item, self.extra = values, sources, item or {}, extra or {}


KINDS, PARSERS, STAGERS = {}, {}, {}


def kind(name, feature):
    """Register a draft builder: `@kind(name, feature)` on build(con, req); settings.json `drafting.<feature>` switches it."""
    def wrap(fn):
        """Record the builder under its name and return it unchanged."""
        KINDS[name] = (feature, fn)
        return fn
    return wrap


def parser(name):
    """Register a reply parser for a draft kind: `@parser(name)` on fn(reply, ctx)."""
    def wrap(fn):
        """Record the parser under its name and return it unchanged."""
        PARSERS[name] = fn
        return fn
    return wrap


def stager(name):
    """A kind that drafts several items at once stages them: fn(parsed, ctx) -> (proposal file name, how many)."""
    def wrap(fn):
        """Record the stager under its name and return it unchanged."""
        STAGERS[name] = fn
        return fn
    return wrap


def proposal_file(items, tag="drafts"):
    """Write pending proposal items to system/staging/ (source_run "drafts"); each is approved on its own in Review."""
    paths.STAGING.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    name, i = f"proposed-{stamp}-{tag}.json", 2
    while (paths.STAGING / name).exists():
        name, i = f"proposed-{stamp}-{i}-{tag}.json", i + 1
    data = {"created": datetime.now().isoformat(timespec="seconds"), "source_run": "drafts", "files": [], "items": items}
    (paths.STAGING / name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return name


# ── settings, clock, counts ──────────────────────────────────────────────────

def today():
    """Today as YYYY-MM-DD, or CREAITE_NOW's date in tests."""
    now = os.environ.get("CREAITE_NOW")
    return now[:10] if now else date.today().isoformat()


def switches(settings=None):
    """{feature: on} from settings.json `drafting` (a feature not named there is on)."""
    s = (settings if settings is not None else paths.load_settings()).get("drafting") or {}
    return {f: bool(s.get(f, True)) for f in FEATURES} | {k: bool(v) for k, v in s.items() if isinstance(v, bool)}


def enabled(feature, settings=None):
    """Whether a draft feature is on (settings.json `drafting`; on when not named)."""
    return switches(settings).get(feature, True)


def read_stats():
    """The counts in system/staging/draft-stats.json, or {} when there are none or the file can't be read."""
    try:
        data = json.loads(STATS.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def record(feature, event, n=1):
    """Add n to one count. Only known features and events, and whole numbers, are kept: the file never holds text."""
    if feature not in FEATURES and not re.fullmatch(r"[a-z][a-z0-9-]{1,30}", str(feature)):
        raise ValueError("unknown feature")
    if event not in EVENTS + (NOTHING_EVENT,) or not isinstance(n, int) or not 0 < n <= 500:
        raise ValueError("unknown event")
    STATS.parent.mkdir(parents=True, exist_ok=True)
    lock = None
    try:
        import fcntl
        lock = open(STATS.with_suffix(".lock"), "w")
        fcntl.flock(lock, fcntl.LOCK_EX)
    except (ImportError, OSError):
        lock = None
    try:
        data = read_stats()
        row = data.setdefault(feature, {e: 0 for e in EVENTS})
        for e in EVENTS:
            row[e] = int(row.get(e) or 0)
        row[event] = int(row.get(event) or 0) + n          # "nothing" only appears once one is counted
        data["_updated"] = datetime.now().isoformat(timespec="seconds")
        tmp = STATS.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(STATS)
    finally:
        if lock:
            lock.close()
    return data[feature]


# ── shared plain-code helpers ────────────────────────────────────────────────

def ro():
    """A read-only connection to the tracker database, rows as sqlite3.Row: drafts never write to it."""
    con = sqlite3.connect(f"file:{paths.DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def words(text):
    """A text's key words: lower case, three letters or more, stop words left out."""
    return {w for w in re.findall(r"[a-z][a-z0-9]+", (text or "").lower()) if len(w) > 2 and w not in STOP}


def overlap(a, b):
    """How far two texts share key words, 0 to 1 (shared words over the shorter text's)."""
    wa, wb = words(a), words(b)
    return len(wa & wb) / max(1, min(len(wa), len(wb))) if wa and wb else 0.0


def secret(text):
    """Whether a text is marked confidential or restricted (SECRET_WORDS): such text is never a draft's source."""
    return bool(SECRET_WORDS.search(text or ""))


def short(text, n=220):
    """Text on one line, cut to n characters with an ellipsis."""
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    return text if len(text) <= n else text[:n - 1] + "…"


def source_path(src):
    """A file a source line points at (`projects/… — Section`), when it is one in the vault, else None."""
    head = (src or "").split(" — ")[0].strip()
    if not head or head.startswith(("Email", "Teams", "Mail", "Alan", "http")):
        return None
    for cand in (head, f"projects/{head}"):
        try:
            p = paths.resolve(cand)
        except Exception:  # noqa: BLE001  an odd stored path
            continue
        if p.is_file():
            return p
    return None


def file_text(p):
    """A file's text (tracker.text_of), or '' when it can't be read."""
    try:
        return tracker.text_of(Path(p)) or ""
    except Exception:  # noqa: BLE001
        return ""


def passages(text, about, item_id=None, limit=3, span=1):
    """The lines of a file that name the item (its ID, else most of its key words), with a line either side."""
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    want = words(about)
    hits = []
    for i, ln in enumerate(lines):
        score = 2.0 if item_id and item_id in ln else (len(want & words(ln)) / len(want) if len(want) >= 3 else 0)
        if score >= 0.5:
            hits.append((score, i))
    out, used = [], set()
    for score, i in sorted(hits, key=lambda h: (-h[0], h[1]))[:limit]:
        if i in used:
            continue
        lo, hi = max(0, i - span), min(len(lines), i + span + 1)
        used.update(range(lo, hi))
        out.append(" ".join(lines[lo:hi]))
    return out


def number(sources):
    """Give each source its tag (S1, S2…), keeping at most MAX_SOURCES; the list as the prompt shows it."""
    kept = sources[:MAX_SOURCES]
    for i, s in enumerate(kept, 1):
        s["ref"] = f"S{i}"
    return kept, "\n".join(f"[{s['ref']}] {s['text']}" for s in kept) or "(none)"


def labels_excluding(con, item_id):
    """An item's labels that keep it out of client output (behaviour or default "exclude"); [] if none."""
    try:
        return [r[0] for r in con.execute("SELECT il.label FROM item_labels il JOIN labels l ON l.name = il.label WHERE il.item_id = ? "
                                          "AND (l.behaviour = 'exclude' OR l.default_choice = 'exclude')", (item_id,))]
    except sqlite3.Error:
        return []


def item_row(con, item_id):
    """(table, row) for an action, RAID item or decision; raises Refused for any other ID or one not in the tracker."""
    table = tracker.item_table(item_id)
    if table not in ("actions", "raid", "decisions"):
        raise Refused(f"{item_id} isn't an action, a RAID item or a decision.")
    row = con.execute(f"SELECT * FROM {table} WHERE id = ?", (item_id,)).fetchone()
    if not row:
        raise Refused(f"{item_id} isn't in your project record.")
    return table, dict(row)


def proposal_item(req):
    """A pending proposal's item from staging ({file, ref}), as (table, values): a draft for Review works on what is proposed."""
    p = req.get("proposal") or {}
    name, ref = str(p.get("file") or ""), p.get("ref")
    if not re.fullmatch(r"proposed-[A-Za-z0-9._-]+\.json", name):
        raise Refused("Not a suggestion.")
    try:
        data = json.loads((paths.STAGING / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise Refused("That suggestion has been saved or removed.")
    it = next((i for i in data.get("items") or [] if i.get("n") == ref), None)
    if not it or it.get("op") != "new" or it.get("table") not in ("actions", "raid", "decisions"):
        raise Refused("That suggestion isn't a new item.")
    v = dict(it.get("values") or {})
    edits = req.get("edits") if isinstance(req.get("edits"), dict) else {}      # what Alan has changed in the peek, not yet saved
    for k in ("description", "decision", "type", "response_action", "reasoning", "options"):
        if isinstance(edits.get(k), str):
            v[k] = edits[k][:4000]
    v["id"] = f"Review #{ref}"
    return it["table"], v


TITLE = {"actions": "description", "raid": "description", "decisions": "decision"}


def item_lines(table, x):
    """The item as the prompt shows it (its own fields, in words)."""
    t = x.get(TITLE[table]) or ""
    if table == "actions":
        bits = [f"Action: {t}", f"Owner: {x.get('owner') or 'TBC'}", f"Status: {x.get('status') or 'Open'}",
                f"Due: {tracker.shown(x['due_date']) if x.get('due_date') else 'no date'}",
                f"Latest update: {x.get('latest_update') or '(none)'}"]
    elif table == "raid":
        bits = [f"{x.get('type') or 'Risk'}: {t}", f"Owner: {x.get('owner') or 'TBC'}", f"Status: {x.get('status') or 'Open'}",
                f"Impact: {x.get('impact') or 'not set'}; likelihood: {x.get('likelihood') or 'not set'}",
                f"Response: {x.get('response_action') or '(none)'}"]
    else:
        bits = [f"Decision: {t}", f"Status: {x.get('status') or 'Made'}", f"Reasoning: {x.get('reasoning') or '(none)'}",
                f"Options considered: {x.get('options') or '(none)'}"]
    return "\n".join(bits)


def render(name, values):
    """A draft's prompt: system/templates/drafts/<name>.md, its $placeholders filled by string.Template (braces in a value are safe)."""
    tpl = (TEMPLATE_DIR / f"{name}.md").read_text(encoding="utf-8")
    return string.Template(tpl).safe_substitute(values)


# ── the parts every draft shares: sentences and their sources ───────────────

TAG = re.compile(r"\s*\[(S\d+(?:\s*,\s*S\d+)*)\]")


def sentences(text):
    """A reply split into its sentences and lines."""
    return [s for s in re.split(r"(?<=[.!?\]])\s+(?=[A-Z0-9“\"(])|\n+", (text or "").strip()) if s.strip()]


def marked(text, sources):
    """[{text, refs, unsourced}] for each sentence; the [S…] tags are taken out of the text and kept as refs."""
    known = {s["ref"] for s in sources}
    out = []
    for s in sentences(text):
        refs = [r.strip() for m in TAG.finditer(s) for r in m.group(1).split(",")]
        clean = TAG.sub("", s).strip()
        if not clean or re.fullmatch(r"[-–•*\s]*", clean):
            continue
        good = [r for r in refs if r in known]
        out.append({"text": clean, "refs": good, "unsourced": not good})
    return out


def clean(text):
    """A reply's text with the [S…] source tags taken out."""
    return re.sub(r"[ \t]+\n", "\n", TAG.sub("", text or "")).strip()


def section(reply, head, heads):
    """The text under `HEAD:` up to the next of `heads`."""
    m = re.search(rf"^{head}:\s*(.*?)(?=^(?:{'|'.join(heads)}):|\Z)", reply or "", re.S | re.M)
    return m.group(1).strip() if m else ""


def default_parse(reply, ctx):
    """The default reply parser: the text before SOURCES:, with each sentence's sources marked."""
    text = (reply or "").split("\nSOURCES:")[0].strip()
    return {"text": clean(text), "sentences": marked(text, ctx["sources"])}


# ── BL-219: the latest update ────────────────────────────────────────────────

def since_last_update(con, item_id, raised):
    """When an item's latest update last changed (the change log), else when it was raised: its evidence is gathered from then (BL-219)."""
    row = con.execute("SELECT max(at) FROM change_log WHERE item_id = ? AND field = 'latest_update' AND op <> 'undo'", (item_id,)).fetchone()
    return (row[0] or "")[:10] or raised or "0000-00-00"


def mentions_of(item_id, since):
    """An item's mentions in system/staging/mentions.jsonl since a date, confidential sources left out (BL-219)."""
    out = []
    try:
        lines = paths.MENTIONS.read_text(encoding="utf-8").splitlines() if paths.MENTIONS.exists() else []
    except OSError:
        lines = []
    for line in lines:
        try:
            m = json.loads(line)
        except ValueError:
            continue
        if m.get("id") == item_id and str(m.get("at") or "") >= since and not secret(m.get("source")):
            out.append(m)
    return out


FIELD_WORDS = {"status": "status", "due_date": "due date", "owner": "owner", "priority": "priority", "description": "wording",
               "milestone": "milestone", "workstream": "workstream", "response_action": "response", "impact": "impact",
               "likelihood": "likelihood", "client_visible": "client-visible", "closed": "closed date"}


def evidence_for_update(con, x, since):
    """The sources an action's update may draw on, newest last: its own changes, meetings and sweeps that raised it again, the
    minutes and transcripts that name it, and changes to the items linked to it. A confidential or restricted source is skipped."""
    item_id, code, about = x["id"], x["project"], x.get("description") or ""
    src = []
    for r in con.execute("SELECT at, field, old_value, new_value FROM change_log WHERE item_id = ? AND substr(at,1,10) >= ? "
                         "AND op = 'update' ORDER BY at", (item_id, since)):
        if r["field"] in FIELD_WORDS:
            old, new = r["old_value"], r["new_value"]
            if r["field"].endswith("date") or r["field"] == "closed":
                old, new = tracker.shown(old) if old else "none", tracker.shown(new) if new else "none"
            src.append({"id": item_id, "kind": "change", "at": r["at"][:10],
                        "text": f"{tracker.shown(r['at'][:10])}: {FIELD_WORDS[r['field']]} changed from {old or 'none'} to {new or 'none'}"})
    seen = set()
    for m in mentions_of(item_id, since):
        key = m.get("source") or ""
        if key in seen:
            continue
        seen.add(key)
        where = paths.name_date(Path(key.split(" — ")[0]).name)[1] if "/" in key else key
        src.append({"id": item_id, "kind": "mention", "at": m.get("at") or "", "path": key if "/" in key else "",
                    "text": f"{tracker.shown(m.get('at') or '')}: raised again in {short(where, 120)}"})
    for d in paths.extract_dirs(code):
        if not d.is_dir():
            continue
        for f in sorted(d.iterdir()):
            day = paths.name_date(f.name)[0]
            if not f.is_file() or not day or day < since or secret(f.name):
                continue
            text = file_text(f)
            if secret(text[:400]):
                continue
            for q in passages(text, about, item_id, limit=2):
                if secret(q):
                    continue
                src.append({"id": item_id, "kind": "minutes", "at": day, "path": paths.rel(f),
                            "text": f"{tracker.shown(day)}, {f.stem[11:] if f.stem[:4].isdigit() else f.stem}: “{short(q)}”"})
    for r in con.execute("SELECT from_item, to_item FROM links WHERE from_item = ? OR to_item = ?", (item_id, item_id)):
        other = r["to_item"] if r["from_item"] == item_id else r["from_item"]
        for c in con.execute("SELECT at, field, new_value FROM change_log WHERE item_id = ? AND substr(at,1,10) >= ? AND op = 'update' "
                             "AND field IN ('status','due_date','forecast_date') ORDER BY at", (other, since)):
            new = tracker.shown(c["new_value"]) if c["field"] != "status" and c["new_value"] else c["new_value"]
            rel = "blocks this" if r["to_item"] == item_id else "is blocked by this"
            src.append({"id": other, "kind": "link", "at": c["at"][:10],
                        "text": f"{tracker.shown(c['at'][:10])}: {other} ({rel}) {FIELD_WORDS.get(c['field'], c['field'].replace('_', ' '))} now {new}"})
    return sorted(src, key=lambda s: s.get("at") or "")


@kind("update", "update")
def build_update(con, req):
    """Builder for Draft the latest update (BL-219): an open action's evidence since its last update. Refused for anything else; Nothing
    when there is no new evidence."""
    item_id = str(req.get("id") or "")
    table, x = item_row(con, item_id)
    if table != "actions":
        raise Refused("Draft the latest update is for actions. A RAID item's response has Suggest.")
    if x["status"] not in ("Open", "Delayed"):
        raise Refused(f"{item_id} is {x['status'].lower()}: there is nothing to update.")
    since = since_last_update(con, item_id, x.get("raised"))
    src = evidence_for_update(con, x, since)
    if not src:
        raise Nothing(f"Nothing new since {tracker.shown(since)}.")
    kept, listed = number(src)
    return Draft({"item": item_lines(table, x), "since": tracker.shown(since), "sources": listed, "today": tracker.shown(today())},
                 kept, item={"id": item_id, "table": table, "since": since})


# BL-219, several at once: one run for the chosen actions; each line becomes a pending update proposal in Review.
@kind("update-bulk", "update")
def build_update_bulk(con, req):
    """Builder for latest updates on several open actions at once (up to 25, BL-219): one run, every action's evidence in one numbered
    list. Those with nothing new are skipped."""
    ids = [i for i in (req.get("ids") or []) if isinstance(i, str) and ID_RE.fullmatch(i)][:25]
    if not ids:
        raise Refused("Choose the actions to draft updates for.")
    blocks, every, skipped, items = [], [], [], {}
    for item_id in ids:
        try:
            table, x = item_row(con, item_id)
        except Refused:
            skipped.append(f"{item_id}: not in the tracker")
            continue
        if table != "actions" or x["status"] not in ("Open", "Delayed"):
            skipped.append(f"{item_id}: not an open action")
            continue
        since = since_last_update(con, item_id, x.get("raised"))
        src = evidence_for_update(con, x, since)[:6]
        if not src:
            skipped.append(f"{item_id}: nothing new since {tracker.shown(since)}")
            continue
        start = len(every)
        every.extend(src)
        items[item_id] = {"since": since, "updated_at": x["updated_at"], "project": x["project"], "refs": (start, len(every))}
        blocks.append((item_id, item_lines(table, x), src))
    if not items:
        raise Nothing("Nothing new for any of them: " + "; ".join(skipped) + ".")
    for i, s in enumerate(every, 1):
        s["ref"] = f"S{i}"
    text = "\n\n".join(f"### {item_id}\n{lines}\nSources:\n" + "\n".join(f"[{s['ref']}] {s['text']}" for s in src)
                       for item_id, lines, src in blocks)
    return Draft({"items": text, "today": tracker.shown(today())}, every, item={"ids": list(items)},
                 extra={"items": items, "skipped": skipped})


@parser("update-bulk")
def parse_bulk(reply, ctx):
    """Parser for update-bulk: one "ID: text" line per action, each sentence's sources marked from that action's own."""
    items, out = ctx["extra"]["items"], []
    for line in (reply or "").splitlines():
        m = re.match(r"\s*[-*]?\s*(" + ID_RE.pattern + r")\s*[:–-]\s*(.+)$", line)
        if not m or m.group(1) not in items:
            continue
        lo, hi = items[m.group(1)]["refs"]
        own = ctx["sources"][lo:hi]
        text = m.group(2).strip()
        out.append({"id": m.group(1), "text": clean(text), "sentences": marked(text, own), "sources": [s["ref"] for s in own]})
    return {"items": out, "skipped": ctx["extra"]["skipped"]}


@stager("update-bulk")
def stage_bulk(parsed, ctx):
    """One proposal of pending `update` items (latest_update only), one per drafted action. Each is individually approved
    (review.individual_only: "drafted update"); nothing is saved in place. Returns (file name, count)."""
    items, by_ref = [], {s["ref"]: s for s in ctx["sources"]}
    for d in parsed["items"]:
        meta = ctx["extra"]["items"][d["id"]]
        if not d["text"]:
            continue
        refs = sorted({r for s in d["sentences"] for r in s["refs"]}, key=lambda r: int(r[1:]))
        loose = sum(1 for s in d["sentences"] if s["unsourced"])
        items.append({"n": len(items) + 1, "op": "update", "table": "actions", "id": d["id"],
                      "changes": {"latest_update": d["text"]}, "based_on": meta["updated_at"],
                      "why": ("Drafted from " + "; ".join(short(by_ref[r]["text"], 90) for r in refs[:3])
                              + (f" (+{len(refs) - 3} more)" if len(refs) > 3 else "")) if refs else "Drafted, with no source: check it",
                      "source": f"AI draft (BL-219), {tracker.shown(today())}",
                      "drafted": "update", "drafted_text": d["text"],
                      "draft_sources": [by_ref[r]["text"] for r in refs],
                      "match": "strong", "flags": ["low-confidence"] if loose else [], "decision": "pending"})
    if not items:
        return None, 0
    return proposal_file(items), len(items)


# ── BL-225: client wording ───────────────────────────────────────────────────

@kind("client", "client")
def build_client(con, req):
    """Builder for an item's client wording (BL-225), from the item's own text (report.client_item_context's checks apply)."""
    import report
    ctx = report.client_item_context(con, str(req.get("id") or ""))
    src = [{"id": "", "kind": "item", "text": f"The item's own text: {short(ctx['text'], 600)}"}]
    kept, listed = number(src)
    return Draft({"kind": ctx["kind"], "text": ctx["text"], "shape": ctx["shape"], "sources": listed}, kept,
                 item={"id": ctx["id"], "table": ctx["table"], "own_text": ctx["text"]})


@parser("client")
def parse_client(reply, ctx):
    """Parser for client wording: the text, what the model says it took out (REMOVED), and the client-wording checks' notes."""
    import status_checks
    heads = ["REMOVED", "SOURCES"]
    body = (reply or "").split("\nREMOVED:")[0].split("\nSOURCES:")[0].strip()
    removed = [ln.strip("-• ").strip() for ln in section(reply, "REMOVED", heads).splitlines() if ln.strip("-• ").strip()]
    removed = [r for r in removed if r.lower() not in ("none", "nothing", "(none)")]
    text = clean(body)
    flags = status_checks.client_wording(text, ctx["item"]["own_text"], people_names())
    return {"text": text, "removed": removed[:8], "notes": flags, "sentences": []}


CMH = ("What it is:", "What it means for you:", "What is being done:")


def messaging_done(table, text):
    """The page's cmOK and cmdOK: each heading has some words after it (actions, RAID), or some words at all (decisions)."""
    if table == "decisions":
        return len(re.sub(r"[^\w]", "", text or "")) >= 5
    lines = (text or "").splitlines()
    for h in CMH:
        line = next((ln.strip() for ln in lines if ln.strip().startswith(h)), None)
        if not line or len(re.sub(r"[^\w]", "", line[len(h):])) < 5:
            return False
    return True


# BL-225, several at once: the project page's "client-visible items need client messaging" card offers Draft all; each wording is a
# pending `client_message` proposal in Review, approved on its own (it faces a client) and never part of Approve routine.
@kind("client-bulk", "client")
def build_client_bulk(con, req):
    """Builder for Draft all on a project's client-visible items that still need client messaging (up to 15, BL-225)."""
    import report
    code = str(req.get("code") or "")
    if not re.fullmatch(r"[A-Z][A-Z0-9]{2,6}", code):
        raise Refused("Not a project.")
    want = []
    for table, col in (("actions", "client_message"), ("raid", "client_message"), ("decisions", "client_message")):
        for r in con.execute(f"SELECT id, {col}, updated_at FROM {table} WHERE project = ? AND client_visible = 1", (code,)):
            if not messaging_done(table, r[1]):
                want.append((r[0], r[2]))
    blocks, every, items, skipped = [], [], {}, []
    for item_id, updated in want[:15]:
        try:
            c = report.client_item_context(con, item_id)
        except Refused as e:
            skipped.append(str(e))
            continue
        every.append({"id": "", "kind": "item", "text": f"{item_id}'s own text: {short(c['text'], 400)}"})
        items[item_id] = {"table": c["table"], "updated_at": updated, "own_text": c["text"]}
        blocks.append(f"### {item_id}\nKind: {c['kind']}. Shape: {c['shape']}\nIts own text:\n{c['text']}")
    if not items:
        raise Nothing("No client-visible item needs client wording" + (": " + "; ".join(skipped) if skipped else "."))
    for i, s in enumerate(every, 1):
        s["ref"] = f"S{i}"
    return Draft({"items": "\n\n".join(blocks)}, every, item={"ids": list(items)}, extra={"items": items, "skipped": skipped})


@parser("client-bulk")
def parse_client_bulk(reply, ctx):
    """Parser for client-bulk: one "### ID" block per item, with its text, what was taken out and the checks' notes."""
    import status_checks
    people, out = people_names(), []
    for item_id, body in re.findall(r"^### (\S+)\s*\n(.*?)(?=^### |\Z)", reply or "", re.S | re.M):
        meta = ctx["extra"]["items"].get(item_id)
        if not meta:
            continue
        text = clean(body.split("\nREMOVED:")[0])
        removed = [ln.strip("-• ").strip() for ln in section(body, "REMOVED", ["REMOVED"]).splitlines() if ln.strip("-• ").strip()]
        out.append({"id": item_id, "text": text, "removed": [r for r in removed if r.lower() not in ("none", "nothing")][:8],
                    "notes": status_checks.client_wording(text, meta["own_text"], people), "sentences": []})
    return {"items": out, "skipped": ctx["extra"]["skipped"]}


@stager("client-bulk")
def stage_client_bulk(parsed, ctx):
    """Stager for client-bulk: each wording becomes a pending client_message proposal in system/staging/, approved on its own in Review
    (BL-225). Returns (file name, count), or (None, 0)."""
    items = []
    for d in parsed["items"]:
        meta = ctx["extra"]["items"][d["id"]]
        if not d["text"]:
            continue
        why = "Drafted client wording" + (f"; taken out: {', '.join(d['removed'][:4])}" if d["removed"] else "") + \
            (f"; check: {' '.join(n['note'] for n in d['notes'][:2])}" if d["notes"] else "")
        items.append({"n": len(items) + 1, "op": "update", "table": meta["table"], "id": d["id"],
                      "changes": {"client_message": d["text"]}, "based_on": meta["updated_at"], "why": short(why, 300),
                      "source": f"AI draft (BL-225), {tracker.shown(today())}", "drafted": "client", "drafted_text": d["text"],
                      "draft_sources": ["The item's own text"], "match": "strong", "flags": ["low-confidence"] if d["notes"] else [],
                      "decision": "pending"})
    return (proposal_file(items), len(items)) if items else (None, 0)


def people_names():
    """Every name and alias in the people register (and Alan's own), for the client-wording check."""
    names = set()
    try:
        s = paths.load_settings().get("identity") or {}
        names.add(s.get("name") or "")
        names.update(s.get("short_forms") or [])
        text = paths.PEOPLE_REGISTER.read_text(encoding="utf-8") if paths.PEOPLE_REGISTER.exists() else ""
        for line in text.splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 3 and cells[0] and not set(cells[0]) <= set("-: ") and cells[0].lower() not in ("name", "full name"):
                names.add(cells[0])
                for a in re.split(r"[;,]", cells[2] if len(cells) > 2 else ""):
                    names.add(a.strip())
    except Exception:  # noqa: BLE001  the register is optional here
        pass
    names.update(table_people_names())
    return sorted(n for n in names if n and len(n) > 1)


def table_people_names():
    """#386: every name and alias in tracker.db's people table (the register is made from it), so a register edited by hand
    or not yet written again never narrows the client-wording check; none when there is no table or it can't be read."""
    from contextlib import closing
    out = set()
    try:
        with closing(tracker.connect_or_raise()) as con:
            if con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'people'").fetchone():
                for name, listed in con.execute("SELECT name, aliases FROM people"):
                    out.add(str(name).strip())
                    listed = json.loads(listed or "[]")
                    out.update(a.strip() for a in (listed if isinstance(listed, list) else []) if isinstance(a, str))
    except Exception:  # noqa: BLE001  the people table is optional here, as the register is: what was read so far counts
        return out
    return out


# ── BL-222: the thinking fields ──────────────────────────────────────────────

THINK_FIELDS = {"decisions": ("reasoning", "options"), "raid": ("response_action",)}


@kind("thinking", "thinking")
def build_thinking(con, req):
    """Builder for Suggest (BL-222) on a decision's reasoning or options, or a RAID item's response: passages from its source, and for a
    RAID item similar closed ones' responses. Works on a pending proposal too."""
    field = req.get("field")
    if req.get("proposal"):
        table, x = proposal_item(req)
    else:
        table, x = item_row(con, str(req.get("id") or ""))
    if field not in THINK_FIELDS.get(table, ()):
        raise Refused("Suggest works on a decision's reasoning and options, and on a RAID item's response.")
    src = []
    srcline = x.get("source") or ""
    p = source_path(srcline)
    if p and not secret(srcline) and not secret(p.name):
        text = file_text(p)
        if text and not secret(text[:400]):
            for q in passages(text, x.get(TITLE[table]) or "", None if str(x.get("id", "")).startswith("Review") else x.get("id"), limit=3, span=2):
                if not secret(q):
                    src.append({"id": x.get("id"), "kind": "passage", "path": paths.rel(p), "text": f"{p.stem}: “{short(q, 400)}”"})
    elif srcline and not secret(srcline) and not p:
        src.append({"id": x.get("id"), "kind": "source", "text": f"Its source: {short(srcline, 200)}"})
    if table == "raid":
        about = x.get("description") or ""
        rows = con.execute("SELECT id, project, type, description, response_action FROM raid WHERE status = 'Closed' "
                           "AND coalesce(response_action, '') <> '' AND id <> ?", (x.get("id") or "",)).fetchall()
        ranked = sorted(rows, key=lambda r: (r["project"] != x.get("project"), -overlap(about, r["description"])))
        for r in [r for r in ranked if overlap(about, r["description"]) > 0][:4] or ranked[:2]:
            if labels_excluding(con, r["id"]) or secret(r["response_action"]):
                continue
            where = "this project" if r["project"] == x.get("project") else "another project"
            src.append({"id": r["id"], "kind": "closed", "text": f"A closed {r['type'].lower()} in {where}: “{short(r['description'], 140)}”; "
                                                                  f"its response: “{short(r['response_action'], 200)}”"})
    if not src:
        raise Nothing("Nothing to suggest from: the item has no meeting passage" + (" and no closed risks have a response." if table == "raid" else "."))
    kept, listed = number(src)
    name = "thinking-response" if table == "raid" else "thinking-decision"
    what = {"reasoning": "the reasoning given", "options": "the options considered", "response_action": "the response"}[field]
    return Draft({"item": item_lines(table, x), "sources": listed, "field": what}, kept,
                 item={"id": x.get("id"), "table": table, "field": field}, extra={"template": name})


@parser("thinking")
def parse_thinking(reply, ctx):
    """Parser for Suggest: the field's text, and for a response the suggested impact and likelihood with their reasons."""
    heads = ["RESPONSE", "IMPACT", "LIKELIHOOD", "OPTIONS", "REASONING", "SOURCES"]
    field = ctx["item"]["field"]
    if field == "response_action":
        body = section(reply, "RESPONSE", heads) or (reply or "").split("\nIMPACT:")[0]
        out = {}
        for k in ("IMPACT", "LIKELIHOOD"):
            m = re.match(r"(High|Medium|Low)\b\s*[|–:-]?\s*(.*)", section(reply, k, heads), re.S | re.I)
            if m:
                out[k.lower()] = {"value": m.group(1).capitalize(), "why": clean(m.group(2))[:200]}
    else:
        body = section(reply, "OPTIONS" if field == "options" else "REASONING", heads) or reply or ""
        out = {}
    return {"text": clean(body), "sentences": marked(body, ctx["sources"]), **out}


# ── BL-226: the reason for a health or forecast change ──────────────────────

HEALTH = ("On track", "At risk", "Off track")


@kind("health", "reason")
def build_health(con, req):
    """Builder for the reason behind a health change (BL-226), from the evidence facts the page sends."""
    import report
    code, to = str(req.get("code") or ""), req.get("to")
    if not re.fullmatch(r"[A-Z][A-Z0-9]{2,6}", code) or not con.execute("SELECT 1 FROM projects WHERE code = ?", (code,)).fetchone():
        raise Refused("Not a project.")
    if req.get("field") == "suggest":                       # #203: the health and its reason, from the tracker alone
        return suggest_health(con, code, "client" if req.get("audience") == "client" else "internal")
    if to not in HEALTH:
        raise Refused("Choose the health first.")
    facts = [short(f, 200) for f in (req.get("facts") or []) if isinstance(f, str) and f.strip()][:10]
    if not facts:
        raise Nothing("The evidence holds nothing to explain it: no overdue actions, Urgent risks, slips or warnings. Say why in your own words.")
    src = [{"id": code, "kind": "evidence", "text": f} for f in facts]
    kept, listed = number(src)
    return Draft({"name": tracker.project_label(code), "to": to, "sources": listed, "style": report.style_guide()}, kept,
                 item={"code": code})


# ===== #203: Suggest the health and its reason (plain code half) =====
# A health request with field "suggest" ignores any page facts: the code reads the tracker, works the health out (report.health_evidence,
# the project's own criteria), and the model only words the reason from the numbered facts. Client wording: audience "client" (the
# existing `audience` key); the facts are client-visible items in their client wording only, and the reply passes edit_ai.client_problems.
SUGGEST_FACTS = 12


def _client_words(row):
    """A client-visible item's client wording (report.client_text); '' when it has none. Its internal text is never used for a client."""
    import report
    return report.client_text(row["client_message"] or "")


def _last_health_set(con, code):
    """(date of the last health change, the health then) from the change log, skipping undo rows and undone applies (as tracker.py
    does), else the last `updates` row; (None, None) if neither."""
    row = con.execute("SELECT c.at, c.new_value FROM change_log c LEFT JOIN applies a ON a.apply_id = c.apply_id "
                      "WHERE c.tbl = 'projects' AND c.item_id = ? AND c.field = 'health' AND c.op <> 'undo' AND a.undone_at IS NULL "
                      "ORDER BY c.at DESC, c.rowid DESC LIMIT 1", (code,)).fetchone()
    if row:
        return row[0][:10], row[1]
    row = con.execute("SELECT week_ending, health FROM updates WHERE project = ? ORDER BY week_ending DESC LIMIT 1", (code,)).fetchone()
    return (row[0][:10], row[1]) if row else (None, None)


def _plural_days(n):
    return f"{n} day{'s' if n != 1 else ''}"


def _no_ids(reason):
    """A criteria reason without its list of item IDs ("(ABC-A-006, ABC-A-007)"): the count stays, and an item left out of the facts
    as confidential is not named by the reason."""
    return re.sub(r"\s*\((?:" + ID_RE.pattern.replace(r"\b", "") + r"(?:, )?)+\)", "", reason)


def _confidential(row):
    """Whether an item must stay out of a draft: its full text, latest update, response or source is marked confidential or
    restricted, or it comes from a documents/ folder (as chase_facts checks), however short the fact made of it is."""
    d = dict(row)
    text = " ".join(str(d.get(k) or "") for k in ("name", "description", "decision", "options", "reasoning", "revisit",
                                              "latest_update", "response_action", "internal_note", "state_reason", "source"))
    return bool(secret(text) or re.search(r"(^|/)documents/", str(d.get("source") or "")))


def _facts_overdue(con, code, client, t):
    """(id, kind, text) for each overdue action: the client's wording for a client suggestion, else the action as written."""
    for r in con.execute("SELECT * FROM actions WHERE project = ? AND status IN ('Open','Delayed') AND due_date < ? "
                         "AND archived = 0 ORDER BY due_date, id", (code, t)):
        days = _plural_days((date.fromisoformat(t) - date.fromisoformat(r["due_date"])).days)
        words = _client_words(r) if client else short(r["description"], 120)
        if words and not _confidential(r):
            more = "" if client else f" (due {tracker.shown(r['due_date'])})"
            who = "" if client else f" ({r['owner']})"
            yield r["id"], "overdue", f"Action overdue by {days}{more}: {short(words, 140)}{who}"


def _facts_milestones(con, code, t):
    """(id, kind, text) for each planned milestone that has slipped or is past its forecast date."""
    import report
    for m in report.milestones(con, code):
        late = bool(m["forecast_date"]) and m["forecast_date"] < t
        if m["status"] == "Planned" and (m["slip_days"] > 0 or late) and not m["archived"] and not _confidential(m):
            fc = f"forecast {tracker.shown(m['forecast_date'])}, " if m["forecast_date"] else ""
            gap = f"{m['slip_days']} days later than agreed" if m["slip_days"] > 0 else "past its forecast date"
            yield m["id"], "milestone", f"Milestone {m['name']}: {fc}{gap}"


def _facts_raid(con, code, client):
    """(id, kind, text) for each open risk and issue, Urgent first."""
    for r in con.execute("SELECT * FROM raid WHERE project = ? AND status = 'Open' AND archived = 0 "
                         "ORDER BY priority = 'Urgent' DESC, id", (code,)):
        words = _client_words(r) if client else short(r["description"], 140)
        if words and not _confidential(r):
            tag = f" ({r['priority']})" if r["priority"] and not client else ""
            yield r["id"], "raid", f"Open {r['type'].lower()}{tag}: {words}"


def _facts_decisions(con, code, client, t):
    """(id, kind, text) for each pending decision past its needed-by date."""
    import report
    for d in report.decisions_needed(con, code, date.fromisoformat(t)):
        row = con.execute("SELECT * FROM decisions WHERE id = ?", (d["id"],)).fetchone() if d["overdue_days"] else None
        if row is not None and not row["archived"]:
            words = _client_words(row) if client else short(d["text"], 140)
            if words and not _confidential(row):
                yield d["id"], "decision", f"Decision overdue by {_plural_days(d['overdue_days'])}: {words}"


def _facts_movement(con, code):
    """(id, kind, text) for what changed since the health was last set (internal only): the last setting, then the actions closed
    and the risks or issues raised since (newest first)."""
    since, then = _last_health_set(con, code)
    if not since:
        return
    yield code, "movement", f"Health was last set on {tracker.shown(since)}" + (f" to {then}" if then else "")
    for r in con.execute("SELECT * FROM actions WHERE project = ? AND status IN ('Complete','Closed') AND closed >= ? "
                         "AND archived = 0 ORDER BY closed DESC, id LIMIT 3", (code, since)):
        if not _confidential(r):
            yield r["id"], "movement", f"Action closed since: {short(r['description'], 120)}"
    for r in con.execute("SELECT * FROM raid WHERE project = ? AND raised >= ? AND archived = 0 "
                         "ORDER BY raised DESC, id LIMIT 3", (code, since)):
        if not _confidential(r):
            yield r["id"], "movement", f"{r['type']} raised since: {short(r['description'], 120)}"


# The most facts of each kind (the cap of SUGGEST_FACTS is for all of them, the criteria line included): what matters most is never
# crowded out by a long list of one kind.
BUDGET = {"overdue": 3, "milestone": 2, "raid": 3, "decision": 1, "movement": 2}


def suggest_facts(con, code, client):
    """[{id, kind, text}] for a health suggestion, most telling first, from the tracker only: overdue actions, milestones that have
    moved or are late, open risks and issues, overdue decisions, and what changed since the health was last set, each kind kept to
    its BUDGET after the unsuitable ones are out. A client one holds client-visible items only (client_leak.item_problem), in their
    client wording, and no movement; a movement line never repeats an item already listed."""
    import client_leak
    t = today()
    blocking = client_leak.blocking_labels(con) if client else None
    groups = [_facts_overdue(con, code, client, t), _facts_milestones(con, code, t), _facts_raid(con, code, client),
              _facts_decisions(con, code, client, t)] + ([] if client else [_facts_movement(con, code)])
    out, seen = [], set()
    for g in groups:
        got = []
        for ref, k, text in g:
            if (secret(text) or VIP_RE.search(text) or (client and client_leak.item_problem(con, ref, blocking))
                    or (k == "movement" and ref in seen) or len(got) >= BUDGET[k]):
                continue
            got.append({"id": ref, "kind": k, "text": text})
        seen |= {x["id"] for x in got}
        out += got
    return out


def suggest_health(con, code, audience):
    """Builder for Suggest the health and its reason (#203). The health is report.health_evidence's, never the model's."""
    import report
    client = audience == "client"
    ev = report.health_evidence(code, client_only=client, live_only=True)           # a client one: client-visible items alone drive it
    suggested = ev["suggested"]
    cur = con.execute("SELECT health, health_reason FROM projects WHERE code = ?", (code,)).fetchone()
    # the internal reason never rides a client reply, so a client request's `current` holds the health only
    current = {"health": cur["health"] or "", "reason": "" if client else (cur["health_reason"] or "")}
    src = suggest_facts(con, code, client)
    if not client and ev["reasons"]:
        why = "; ".join(_no_ids(r) for r in ev["reasons"])
        line = f"Your project record's criteria give {suggested}: {why}"
        if not (secret(line) or VIP_RE.search(line)):          # a reason naming a confidential milestone is left out: the health stays
            src.insert(0, {"id": code, "kind": "criteria", "text": line})
    if not src:
        raise Nothing("Your project record holds nothing to explain a health: no overdue actions, slipped milestones, "
                      "open risks or overdue "
                      "decisions" + (" that a client may see" if client else "") + ". Say why in your own words.")
    kept, listed = number(src)
    note = ("A client will read this: plain client wording, with no item numbers, internal names or internal reasons."
            if client else "This is for Alan's own record (internal).")
    return Draft({"name": tracker.project_label(code), "to": suggested, "sources": listed, "style": report.style_guide(),
                  "audience_note": note},
                 kept, item={"code": code},
                 extra={"template": "health-suggest", "suggest": True, "audience": audience, "code": code, "health": suggested,
                        "current": current, "differs": suggested != current["health"]})


@parser("health")
def parse_health(reply, ctx):
    """The reason as the default parser reads it; for a suggestion also the health (the code's), whether it differs, the current
    health and the evidence (every fact it was given, by item ID). A client reason keeps only sentences with a source and is dropped
    whole if it fails the client check."""
    out = default_parse(reply, ctx)
    ex = ctx.get("extra") or {}
    if not ex.get("suggest"):
        return out
    client = ex.get("audience") == "client"
    if client:
        out = default_parse(refine_keep_sourced(reply, ctx["sources"])[0], ctx)
    sents = out["sentences"][:3]
    reason = " ".join(s["text"] for s in sents)
    if client and reason:
        import edit_ai
        if edit_ai.client_problems(ex.get("code") or "", reason, "") or VIP_RE.search(reason):
            reason, sents = "", []
            out["message"] = "The draft was dropped: it held wording that isn't client-safe."
    out.update(sentences=sents, text=reason, health=ex["health"], reason=reason, differs=ex["differs"], current=ex["current"],
               audience=ex["audience"], evidence=[{"ref": s["id"], "text": s["text"]} for s in ctx["sources"]])
    return out


# ===== end #203 =====


@kind("forecast", "reason")
def build_forecast(con, req):
    """Builder for the reason behind a milestone forecast move (BL-226): its overdue actions, risks, dependencies, blockers and pending
    decisions."""
    mid, fc = str(req.get("id") or ""), str(req.get("fc") or "")
    m = con.execute("SELECT * FROM milestones WHERE id = ?", (mid,)).fetchone()
    if not m:
        raise Refused("Not a milestone.")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", fc):
        raise Refused("Choose the new forecast first.")
    old = m["forecast_date"] or m["baseline_date"]
    t = today()
    src = []
    for r in con.execute("SELECT id, description, owner, due_date FROM actions WHERE milestone = ? AND status IN ('Open','Delayed') "
                         "AND due_date < ? ORDER BY due_date", (mid, t)):
        src.append({"id": r["id"], "kind": "overdue", "text": f"Action overdue since {tracker.shown(r['due_date'])}: {short(r['description'], 120)} ({r['owner']})"})
    for r in con.execute("SELECT id, type, description, due_date, priority FROM raid WHERE milestone = ? AND status = 'Open' ORDER BY due_date", (mid,)):
        late = r["due_date"] and r["due_date"] < t
        if r["type"] == "Dependency" or late or r["priority"] == "Urgent":
            moved = con.execute("SELECT old_value, new_value FROM change_log WHERE item_id = ? AND field = 'due_date' AND op = 'update' "
                                "ORDER BY at DESC LIMIT 1", (r["id"],)).fetchone()
            what = f"moved from {tracker.shown(moved[0])} to {tracker.shown(moved[1])}" if moved and moved[0] and moved[1] else \
                f"overdue since {tracker.shown(r['due_date'])}" if late else f"{r['priority']} priority"
            src.append({"id": r["id"], "kind": r["type"].lower(), "text": f"{r['type']} {what}: {short(r['description'], 120)}"})
    for r in con.execute("SELECT l.from_item FROM links l WHERE l.to_item = ?", (mid,)):
        if not any(s["id"] == r[0] for s in src):
            row = con.execute("SELECT description, due_date, status FROM raid WHERE id = ?", (r[0],)).fetchone() or \
                con.execute("SELECT description, due_date, status FROM actions WHERE id = ?", (r[0],)).fetchone()
            if row and row["status"] in ("Open", "Delayed") and row["due_date"] and row["due_date"] >= old:
                src.append({"id": r[0], "kind": "blocker", "text": f"Blocked by {r[0]}, due {tracker.shown(row['due_date'])}: {short(row['description'], 120)}"})
    for r in con.execute("SELECT id, decision, needed_by FROM decisions WHERE project = ? AND status = 'Pending' ORDER BY needed_by", (m["project"],)):
        if not r["needed_by"] or r["needed_by"] <= fc:
            src.append({"id": r["id"], "kind": "decision", "text": f"Decision still pending{' (needed by ' + tracker.shown(r['needed_by']) + ')' if r['needed_by'] else ''}: {short(r['decision'], 120)}"})
    if not src:
        raise Nothing("Nothing in your project record explains the move: no overdue work, dependency or pending decision "
                      "behind it. Say why in your own words.")
    kept, listed = number(src)
    days_ = (date.fromisoformat(fc) - date.fromisoformat(old)).days if old else 0
    return Draft({"milestone": m["name"], "old": tracker.shown(old) if old else "none", "new": tracker.shown(fc),
                  "move": f"{abs(days_)} days {'later' if days_ >= 0 else 'earlier'}", "sources": listed}, kept, item={"id": mid})


# ===== BL-223 (sprint-drafts-writing) ===== the agenda and the invite text (POAD), from the Prep page's own selection =====
# Plain code builds the agenda: prep_page.context picks the meeting's items (urgent, overdue, due soon; decisions needed or to
# revisit), and the points go in a fixed order (the decisions that need the meeting, then overdue and Urgent work, then milestones
# due, then last time's uncovered points), at most six, each timed from the meeting's length. The model only words the POAD (or the
# lighter write-up) around them, with each sentence tagged. A confidential meeting gives the model its title and times only.
AGENDA_POINTS = 6
AGENDA_STYLES = ("poad", "lite")
POAD_HEADS = ("PURPOSE", "OBJECTIVES", "APPROACH", "DELIVERABLES")


def agenda_style(req, settings=None):
    """'poad' (the default) or 'lite': the request's choice, else settings.json `drafting.agenda_style`."""
    if req.get("style") in AGENDA_STYLES:
        return req["style"]
    v = ((settings if settings is not None else paths.load_settings()).get("drafting") or {}).get("agenda_style")
    return v if v in AGENDA_STYLES else "poad"


def meeting_length(meeting):
    """The meeting's length in minutes from its start and end (HH:MM); 60 when either is missing or odd."""
    try:
        (h1, m1), (h2, m2) = [map(int, str(meeting.get(k) or "").split(":")) for k in ("start", "end")]
    except ValueError:
        return 60
    n = (h2 * 60 + m2) - (h1 * 60 + m1)
    return n if 10 <= n <= 480 else 60


def milestones_due(con, codes, day, soon):
    """[(id, name, date)] of the open milestones forecast (else baselined) on or before `soon` days after the meeting."""
    from datetime import timedelta
    limit = (date.fromisoformat(day) + timedelta(days=soon)).isoformat()
    out = []
    for c in codes:
        for r in con.execute("SELECT id, name, COALESCE(forecast_date, baseline_date) AS d FROM milestones WHERE project = ? AND "
                             "status = 'Planned' AND COALESCE(forecast_date, baseline_date) <= ? ORDER BY d", (c, limit)):
            out.append((r["id"], r["name"], r["d"]))
    return out


def _point_one(kind, x):
    """One agenda point for one item, in plain words."""
    if kind == "decide":
        when = f" (needed by {tracker.shown(x['due'])})" if x.get("due") and x.get("type") == "Decision needed" else ""
        verb = "Revisit" if x.get("type") == "Decision to revisit" else "Decide"
        return f"{verb}: {short(x['text'], 120)}{when}"
    if kind == "work":
        late = x.get("due") and x["due"] < x["_day"]
        tail = f"due {tracker.shown(x['due'])}" if x.get("due") else "no date"
        return f"{'Overdue' if late else 'Urgent'}: {short(x['text'], 120)} ({x.get('owner') or 'no owner'}, {tail})"
    if kind == "milestone":
        return f"Milestone due {tracker.shown(x['due'])}: {x['text']}"
    return f"Not covered last time: {short(x['text'], 120)}"


GROUP_WORDS = {"decide": "Decisions", "work": "Overdue and urgent work", "milestone": "Milestones due", "carried": "Not covered last time"}


def _point_many(kind, xs):
    """One agenda point standing for several items of one kind."""
    ids = [x["id"] for x in xs if x.get("id")]
    return f"{GROUP_WORDS[kind]}: {len(xs)} items" + (f" ({', '.join(ids)})" if ids else "")


def allot(groups, limit=AGENDA_POINTS):
    """[(kind, [items])] → at most `limit` points: each kind with items gets one, then items get their own while slots last;
    a kind with more items than points ends with one point for the rest."""
    groups = [(k, xs) for k, xs in groups if xs][:limit]
    slots, left = [1] * len(groups), limit - len(groups)
    for i, (_, xs) in enumerate(groups):
        extra = min(left, len(xs) - 1)
        slots[i] += extra
        left -= extra
    points = []
    for (k, xs), n in zip(groups, slots):
        for x in xs[:n - 1]:
            points.append({"kind": k, "point": _point_one(k, x), "ids": [x["id"]] if x.get("id") else []})
        rest = xs[n - 1:]
        one = len(rest) == 1
        points.append({"kind": k, "point": _point_one(k, rest[0]) if one else _point_many(k, rest),
                       "ids": [x["id"] for x in rest if x.get("id")]})
    return points


def timed(points, meeting):
    """Each point with its minutes and clock times: a decision counts double; whole fives, at least five; the last takes the rest."""
    total = meeting_length(meeting)
    weights = [2 if p["kind"] == "decide" else 1 for p in points]
    mins = [max(5, round(total * w / max(1, sum(weights)) / 5) * 5) for w in weights]
    if mins:
        mins[-1] = max(5, total - sum(mins[:-1]))
    try:
        h, m = map(int, str(meeting.get("start") or "").split(":"))
        clock = h * 60 + m
    except ValueError:
        clock = None
    for p, n in zip(points, mins):
        p["minutes"] = n
        if clock is not None:
            p["at"] = f"{clock // 60 % 24:02d}:{clock % 60:02d}"
            clock += n
    return points


def agenda_groups(ctx, con):
    """The agenda's kinds in order, each with its items: decisions, overdue and Urgent work, milestones due, carried points."""
    day = ctx["day"]
    items = [dict(i, _day=day) for i in ctx.get("items") or []]
    decide = [i for i in items if i["table"] == "decisions"]
    work = [i for i in items if i["table"] != "decisions" and ((i.get("due") and i["due"] < day) or i.get("priority") == "Urgent")]
    codes = (ctx.get("research") or {}).get("codes") or ([ctx["project"]] if ctx.get("project") else [])
    ms = [{"id": m[0], "text": m[1], "due": m[2]} for m in milestones_due(con, codes, day, ctx.get("due_soon_days") or 7)]
    carried = [{"id": "", "text": c["point"]} for c in ctx.get("carried") or []]
    return [("decide", decide), ("work", work), ("milestone", ms), ("carried", carried)]


def agenda_meeting(ctx):
    """The meeting as the prompt may see it: a confidential one keeps only its title and times (the calendar rule)."""
    m = ctx.get("meeting") or {}
    keep = {"title": m.get("title") or "", "start": m.get("start") or "", "end": m.get("end") or ""}
    if m.get("confidential"):
        return keep, True
    return {**keep, "where": m.get("where") or "", "body": short(m.get("body") or "", 1500)}, False


@kind("agenda", "agenda")
def build_agenda(con, req):
    """BL-223: the agenda points in plain code (each a source), and the meeting, for the model to word the invite text around."""
    import prep_page
    key = str(req.get("key") or "")
    if not re.fullmatch(r"(\d{4}-\d{2}-\d{2}\|)?\d{2}:\d{2}\|.{1,200}", key):
        raise Refused("Which meeting?")
    import contextlib
    with contextlib.redirect_stdout(sys.stderr):           # a library note ("image not found…") must not mix into the JSON
        ctx = prep_page.context(key)
    if ctx.get("error"):
        raise Refused(ctx["error"])
    meeting, confidential = agenda_meeting(ctx)
    points = timed(allot(agenda_groups(ctx, con)), meeting)
    if not points and not meeting.get("body"):
        raise Nothing("Nothing to build an agenda from: no decisions, overdue or urgent work, milestones due or carried points, "
                      "and no invite text. Write it yourself, or add the invite's purpose first.")
    src = [{"id": ", ".join(p["ids"]) or "carried", "kind": p["kind"], "text": p["point"]} for p in points]
    if meeting.get("body"):
        src.append({"id": "invite", "kind": "invite", "text": "The invite says: " + short(meeting["body"], 400)})
    kept, listed = number(src)
    style = agenda_style(req)
    what = (f"{meeting['title']}, {tracker.shown(ctx['day'])} {meeting['start']}–{meeting['end']}"
            + (f" ({meeting['where']})" if meeting.get("where") else ""))
    return Draft({"meeting": what, "project": ctx.get("project_name") or "", "sources": listed}, kept,
                 item={"key": key, "project": ctx.get("project")},
                 extra={"template": f"agenda-{style}", "style": style, "agenda": points, "confidential": confidential,
                        "title": meeting["title"], "day": ctx["day"], "start": meeting["start"], "end": meeting["end"]})


@parser("agenda")
def parse_agenda(reply, ctx):
    """POAD's four parts (or the lighter style's one), each with its sentences and sources; the timed agenda from plain code."""
    ex = ctx.get("extra") or {}
    heads = POAD_HEADS if ex.get("style") == "poad" else ("SUMMARY",)
    parts = []
    for h in heads:
        body = section(reply, h, heads)
        if body:
            parts.append({"head": h.capitalize(), "text": clean(body), "sentences": marked(body, ctx["sources"])})
    if not parts:
        parts = [{"head": "", "text": clean(reply), "sentences": marked(reply, ctx["sources"])}]
    return {"text": "\n\n".join(p["text"] for p in parts), "sentences": [s for p in parts for s in p["sentences"]], "parts": parts,
            "agenda": ex.get("agenda") or [], "style": ex.get("style"), "confidential": bool(ex.get("confidential")),
            "meeting": {k: ex.get(k) for k in ("title", "day", "start", "end")}}


def agenda_file_text(d, attendees=False):
    """The agenda as a Markdown file for the Agendas folder: marked Internal unless Alan marked it for attendees. Its list lines
    are the agenda's points, which is what minutes.py agenda reads for Coverage (BL-209)."""
    m = d.get("meeting") or {}
    when = f"{tracker.shown(m.get('day') or '')} {m.get('start') or ''}–{m.get('end') or ''}".strip(" –")
    lines = [f"# Agenda: {m.get('title') or 'Meeting'}", "", when, "",
             "For attendees." if attendees else "Internal: not for sending as it is.", ""]
    for p in d.get("parts") or []:
        lines += ([f"## {p['head']}"] if p.get("head") else []) + [p.get("text") or "", ""]
    lines += ["## Agenda", ""]
    for p in d.get("agenda") or []:
        at = f"{p['at']}, " if p.get("at") else ""
        lines.append(f"- {p['point']} ({at}{p.get('minutes', 5)} min)")
    return "\n".join(lines).rstrip() + "\n"
# ===== end BL-223 =====


# ===== BL-224 (sprint-drafts-writing) ===== follow-up and chase emails on the one Draft email builder =====
# The email itself is plain code in the page (draftEmail's modes); nothing here writes an email, and nothing is ever sent. This block
# gives the builder what only the server can read: a meeting's attendees with their addresses (the saved calendar, then the people
# register) and the minutes' own summary paragraph (written by cx-minutes; nothing new is generated), and keeps the chase log
# (system/staging/chases.json: item IDs, the date and the mode, written only when Alan presses "I sent it"). "Polish the wording"
# is the one model step: it rewords the cover paragraph only, in a chosen tone; the table, subject and addresses are never sent to it.
CHASES = paths.STAGING / "chases.json"
CHASE_MODES = ("chase", "help", "decision")             # BL-298: the peek's three kinds of chase, all counted for the tone
RECORD_MODES = ("chase", "update", "followup", "help", "decision")
TONES = ("warm", "neutral", "firm")
SUMMARY_HEADS = re.compile(r"^\s*(?:#+\s*)?(executive summary|summary)\s*:?\s*$", re.I)
NEXT_HEAD = re.compile(r"^\s*(?:#+\s*)?(updates|decisions|action items|actions|open questions|attendees|agenda|escalations|"
                       r"risks|next steps)\b.*$", re.I)


def chases_load():
    """The chase log's records, [{ids, date, mode}]; an unreadable file is an empty log."""
    try:
        data = json.loads(CHASES.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [c for c in data.get("chases") or [] if isinstance(c, dict)]


def chase_record(ids, mode="chase", day=None):
    """Add one record (the items Alan says he chased, today): references only, never message text. Returns the record."""
    ids = list(dict.fromkeys(i for i in ids if isinstance(i, str) and ID_RE.fullmatch(i)))[:50]
    if not ids:
        raise ValueError("No item IDs to record.")
    if mode not in RECORD_MODES:
        raise ValueError("Not a mode creaite records.")
    rec = {"ids": ids, "date": day or today(), "mode": mode}
    data = {"chases": chases_load() + [rec]}
    CHASES.parent.mkdir(parents=True, exist_ok=True)
    tmp = CHASES.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    tmp.replace(CHASES)
    return rec


def chase_counts():
    """{item ID: {"n": how often chased, "last": YYYY-MM-DD}} from the log: chase records, and BL-298's help and decision requests
    (each is a chase of one item, so the next one steps up). #183: "sent": YYYY-MM-DD once a sweep has seen a drafted email about
    the item in Sent Items."""
    out = {}
    for c in chases_load():
        if c.get("mode") not in CHASE_MODES:
            continue
        for i in c.get("ids") or []:
            row = out.setdefault(i, {"n": 0, "last": ""})
            row["n"] += 1
            row["last"] = max(row["last"], str(c.get("date") or ""))
    try:
        import draft_delivery                            # #183: a drafted email a sweep has seen in Sent Items
    except ImportError:
        return out                                       # an engine without #183: the counts as before
    for i, day in draft_delivery.sent_days().items():
        if i in out:
            out[i]["sent"] = day
    return out


def minutes_summary(text):
    """The minutes' own summary paragraph: the text under an "Executive summary" or "Summary" heading, up to the next heading."""
    lines, out, inside = (text or "").splitlines(), [], False
    for ln in lines:
        if SUMMARY_HEADS.match(ln):
            inside = True
            continue
        if inside and (NEXT_HEAD.match(ln) or ln.lstrip().startswith("#")) and out:
            break
        if inside and ln.strip():
            out.append(ln.strip())
    return short(" ".join(out), 1500)


def minutes_file(files):
    """The meeting's minutes, from the files the meeting page lists: a filed minutes file, else its draft in staging."""
    for f in files or []:
        f = str(f)
        if ".." in f.split("/") or not re.search(r"(/minutes/|^system/staging/drafts/)[^/]+\.(docx|md|txt)$", f, re.I):
            continue
        try:
            p = paths.resolve(f)
        except (LookupError, ValueError):  # a path that no longer maps to a folder: try the next file
            continue
        if p.is_file():
            return p
    return None


def calendar_event(req):
    """The saved calendar's entry for the meeting (by its ID, else its day, start and title), or {}."""
    try:
        days = calendar_gateway.read("agenda").get("days") or {}
    except (OSError, ValueError):
        return {}
    for day, evs in days.items():
        for ev in evs if isinstance(evs, list) else []:
            if (req.get("eid") and ev.get("id") == req["eid"]) or \
                    (day == req.get("day") and ev.get("start") == req.get("start") and ev.get("title") == req.get("title")):
                return ev
    return {}


def attendees_of(ev):
    """[{name, email}] from the invite, an address filled from the people register where the invite has none."""
    import propose
    try:
        reg = {p["name"].lower(): p for p in propose.people_parse(propose.people_register_text()[0])}   # BL-298: (text, exists)
    except Exception:  # noqa: BLE001  the register is a help here: without it, the invite's own addresses
        reg = {}
    me = (paths.load_settings().get("identity") or {}).get("name") or ""
    out = []
    for a in ev.get("attendees") or []:
        name = str(a.get("name") or "").strip()
        email = str(a.get("email") or "").strip() or (reg.get(name.lower()) or {}).get("email", "")
        if name and name != me:
            out.append({"name": name, "email": email})
    return out


def followup_facts(req):
    """BL-224: what the follow-up email needs that only the server can read: the attendees and the minutes' summary paragraph.
    A confidential meeting or minutes marked confidential or restricted give no summary (and the calendar keeps no attendees)."""
    ev = calendar_event(req)
    confidential = (ev.get("sensitivity") or "") == "confidential"
    p = minutes_file(req.get("files"))
    # v2.6.0: this email goes to the meeting's attendees, so its summary is only ever the Distributed version's: from a minutes
    # record (distributed_of), never from an Internal Word, Markdown or text file, which may hold what is not for distribution.
    summary, rec = "", _distributed_record(req.get("files"))
    if rec is not None and not confidential:
        import minutes_record
        text = minutes_record._followup_text(rec, "summary")
        summary = "" if secret(text) else short(text, 1500)
    note = ("Confidential: the summary is left out." if confidential else "" if summary else
            "The minutes have no summary paragraph yet." if rec is not None else
            "The minutes aren't a creaite record, so their summary is left out (it could be internal)." if p else
            "No minutes yet, so no summary.")
    return {"attendees": [] if confidential else attendees_of(ev), "summary": summary, "note": note,
            "minutes": paths.rel(p) if p else None, "confidential": confidential}


def _distributed_record(files):
    """The Distributed version of the first minutes record among `files` (a filed one or a draft), or None."""
    import minutes_record
    for f in files or []:
        try:
            _, doc = minutes_record.record_at(f)
            return minutes_record.distributed_of(doc)
        except (minutes_record.RecordError, OSError, ValueError, KeyError, TypeError):  # not a minutes record: try the next file
            continue
    return None


@kind("polish", "email")
def build_polish(con, req):
    """The cover paragraph only (never the table, subject or addresses), and the tone to reword it in."""
    text, tone = short(req.get("text") or "", 1500), req.get("tone") if req.get("tone") in TONES else "neutral"
    if not text:
        raise Nothing("There is no cover paragraph to polish.")
    if secret(text):
        raise Refused("The paragraph mentions something confidential or restricted, so it isn't sent to a draft.")
    kept, listed = number([{"id": "cover", "kind": "paragraph", "text": text}])
    return Draft({"tone": tone, "sources": listed}, kept, item={"tone": tone}, extra={"tone": tone, "original": text})


@parser("polish")
def parse_polish(reply, ctx):
    """The reworded paragraph (TEXT:), its sentences, and the original beside it."""
    body = section(reply, "TEXT", ("TEXT",)) or reply
    ex = ctx.get("extra") or {}
    return {"text": clean(body), "sentences": marked(body, ctx["sources"]), "original": ex.get("original", ""), "tone": ex.get("tone")}
# ===== end BL-224 =====


# ===== BL-298 (sprint-draft-chase) ===== Draft chase from the peek: one item, three modes =====
# Whose item it is decides the mode: someone else's is a chase to its owner (BL-224's DE_CHASE wording, unchanged); Alan's own is a
# request for help (he picks the recipient from the suggestions below); a pending decision is asked of its decision maker. The email
# is written by plain code from the item's facts (chase_draft), with no model call, so the peek pane renders it as Alan types; Polish
# stays the existing "polish" kind (the opening paragraph only). "I sent it" is chase_record(ids, mode): IDs, the date and the mode.
TONE_NAMES = ("First", "Second", "Firmer")
# As accepted (Alan, 13-10-2026, dev/BACKLOG.md › BL-298 › As accepted); the page may reuse these strings as they are.
CHASE_WORDING = {
    "chase": {      # BL-224's DE_CHASE, unchanged (0129-bl-224-sprint-drafts-writing.js)
        "subjects": ("Reminder", "Second reminder", "Overdue, reply needed"),
        "openings": ("A quick reminder about the items below, which are now past their due dates.",
                     "I'm following up on my earlier note{last} about the items below, which are still overdue.",
                     "These items are now well overdue and are holding up other work; I have chased them {n}{since}."),
        "asks": ("Could you let me know where each one stands, and when I can expect it?",
                 "Could you let me have an update on each, and a date for anything still open?",
                 "Please reply with a firm date for each, or tell me what is blocking it so that we can resolve it together."),
        "reply_by": " It would be helpful to hear back by {reply_by}.",
        "thanks": " Thank you very much for your help.",
        "sign_off": "Kind regards,"},
    "chase_one": {  # Alan, 13-10-2026: the peek chases one item, so DE_CHASE's texts in the singular (the subjects are DE_CHASE's)
        "openings": ("A quick reminder about the item below, which is now past its due date.",
                     "I'm following up on my earlier note{last} about the item below, which is still overdue.",
                     "This item is now well overdue and is holding up other work; I have chased it {n}{since}."),
        "asks": ("Could you let me know where it stands, and when I can expect it?",
                 "Could you let me have an update, and a date for it?",
                 "Please reply with a firm date, or tell me what is blocking it so that we can resolve it together.")},
    "help": {
        "subjects": ("Your help with", "Following up: your help with", "Needed this week: your help with"),
        "openings": ("I've been asked to follow up with you on {item}, to get {outcome}. "
                     "The action is with me ({id}), and I need your help to close it.",
                     "I'm following up on my note of {last} about {item}; I still need your help to get {outcome}. "
                     "The action is with me ({id}), and I need your help to close it.",
                     "I need to close this out this week: the action to get {outcome} is with me, "
                     "and I can't finish it without your input."),
        "need": "What I need from you:",
        "ask": "Could you let me know by {reply_by}? If someone else is better placed to help, a name would be just as useful.",
        "sign_off": "Thank you,"},
    "decision": {
        "subjects": ("Decision needed", "Second reminder: decision needed", "Decision needed this week"),
        "openings": ("A quick note on the decision below, which is needed soon for {unblocks}.",
                     "I'm following up on my earlier note of {last} about the decision below; it is needed for {unblocks}.",
                     "This decision is now holding up {unblocks}; I have asked for it {n}, most recently on {last}."),
        "ask": "Could you let me have the decision, or tell me what you need to make it, by {reply_by}?",
        "sign_off": "Thank you,"},
}
MODE_LINES = {      # the pane's mode line (a tag and one sentence)
    "chase": ("Chase", "Chasing {first}, who owns it. {count}"),
    "help": ("Yours", "This action is yours, so this asks for help rather than chasing. It makes clear the action is with you and what "
                      "you need from them."),
    "decision": ("Decision", "Asking {first} for the decision by its needed-by date. {count}"),
}
COUNT_WORDS = ("Not chased before: a first reminder.", "Chased once, on {last}: this is a second reminder.",
               "Chased {n}, most recently on {last}: this is a firmer reminder.")
REACH_OUT = re.compile(r"^(?:reach out to|follow up with|follow-up with|speak to|speak with|talk to|talk with|check with|"
                       r"catch up with|chase|ask|contact|email|call|ping|meet)\s+(?:[A-Z][\w'’-]*\s+){1,3}"
                       r"(?:on|about|re|regarding|for|over)\s+(.+)$", re.I)
WHY_ORDER = ("named in the item", "raised it", "at the meeting", "project stakeholder")


def times(n):
    """once, twice, 3 times: as the Draft email says it (deTimes)."""
    return "once" if n == 1 else "twice" if n == 2 else f"{n} times"


def weekday_date(iso):
    """YYYY-MM-DD → "Thursday 15-10-2026", the way the email names a reply-by date."""
    try:
        return f"{tracker.WEEKDAY_NAMES[date.fromisoformat(iso).weekday()]} {tracker.shown(iso)}"
    except (TypeError, ValueError):
        return ""


def working_days_ahead(start, n=2, settings=None):
    """The date n working days after start (YYYY-MM-DD or a date): weekend days (settings work.weekend_days) are skipped."""
    from datetime import timedelta
    d = date.fromisoformat(start) if isinstance(start, str) else start
    off = tracker.weekend_days(settings)
    left = n
    while left > 0:
        d += timedelta(days=1)
        if d.weekday() not in off:
            left -= 1
    return d.isoformat()


def due_words(due, day, kind="actions", soon=7):
    """(words, overdue) for a due or needed-by date, as the Draft email says them: "4 days overdue", "due in 6 days",
    "needed in 2 days"; no words beyond the due-soon window or without a date."""
    if not due:
        return "", False
    try:
        n = (date.fromisoformat(due) - date.fromisoformat(day)).days
    except ValueError:
        return "", False
    if n < 0:
        return f"{-n} day{'' if n == -1 else 's'} overdue", True
    verb = "needed" if kind == "decisions" else "due"
    if n > soon:
        return "", False
    return (f"{verb} today" if n == 0 else f"{verb} tomorrow" if n == 1 else f"{verb} in {n} days"), False


def help_topic(text):
    """(topic in a sentence, topic in a subject) from an action's words: "Reach out to Dana on back-to-back commercials" →
    ("the back-to-back commercials", "back-to-back commercials"); otherwise the words as written, in quotes in the sentence."""
    text = short(text, 160).rstrip(".")
    m = REACH_OUT.match(text)
    if m:
        rest = m.group(1).strip()
        bare = re.sub(r"^the\s+", "", rest, flags=re.I)
        return f"the {bare}", bare
    return f"“{text}”", text


def chase_mode(kind, owner, me):
    """BL-298: whose item it is decides the mode. A pending decision asked of someone else: decision; Alan's own item (owner or
    decision maker): help; anyone else's: chase."""
    mine = bool(me) and str(owner or "").strip().lower() == str(me).strip().lower()
    if mine:
        return "help"
    if kind == "decisions":
        return "decision"
    return "chase"


def chase_defaults(item_id, day=None, counts=None, settings=None):
    """The pane's defaults: reply by two working days ahead, the tone preset from how often the item was chased (First, Second,
    Firmer), the latest update included; with the count and the last chase date."""
    day = day or today()
    c = (chase_counts() if counts is None else counts).get(item_id) or {"n": 0, "last": ""}
    return {"reply_by": working_days_ahead(day, 2, settings), "tone": min(c["n"], 2), "include_update": True,
            "chased": {"n": c["n"], "last": c["last"]}}


def mode_line(mode, first, chased):
    """(tag, sentence) for the pane's mode line."""
    tag, words = MODE_LINES[mode]
    n, last = chased.get("n", 0), tracker.shown(chased.get("last") or "")
    count = COUNT_WORDS[min(n, 2)].format(n=times(n), last=last)
    return tag, words.format(first=first or "them", count=count)


def chase_tone(o):
    """The tone chosen (0 First, 1 Second, 2 Firmer), else the one the chase count presets."""
    t = o.get("tone")
    if t is None:
        t = (o.get("chased") or {}).get("n", 0)
    return max(0, min(int(t), 2))


def greeting(hour, first):
    """The Draft email's greeting: "Good morning, Dana," by the hour (deGreeting)."""
    part = "morning" if hour < 12 else "afternoon" if hour < 18 else "evening"
    return f"Good {part}{', ' + first if first else ''},"


def _chase_words(f, o, tone, n, last, reply):
    """{subject, opening, ask} for a chase: BL-224's DE_CHASE for one item, in the singular (Alan, 13-10-2026)."""
    w, one = CHASE_WORDING["chase"], CHASE_WORDING["chase_one"]
    opening = one["openings"][tone].replace("{last}", f" of {tracker.shown(last)}" if last else "").replace("{n}", times(n)) \
        .replace("{since}", f", most recently on {tracker.shown(last)}" if last else "")
    ask = one["asks"][tone] + (w["reply_by"].format(reply_by=reply) if reply else "") + w["thanks"]
    return {"subject": f"[{f.get('code') or ''}] {w['subjects'][tone]}: {f.get('text') or ''}", "opening": opening, "ask": ask}


def _help_words(f, o, tone, n, last, reply):
    """{subject, opening, ask, outcome, need} for a request for help with Alan's own item; the outcome and need are his, else filled."""
    w = CHASE_WORDING["help"]
    topic, subj_topic = help_topic(f.get("text") or "")
    outcome = str(o.get("outcome") or "").strip() or (f"{topic} done" if topic.startswith("the ") else "this done")
    need = str(o.get("need") or "").strip() or f"Your input on {topic}."
    tmpl = w["openings"][tone]
    if not last:
        tmpl = tmpl.replace("my note of {last}", "my earlier note")
    opening = tmpl.format(item=topic, outcome=outcome, id=f.get("id") or "", last=tracker.shown(last))
    ask = w["ask"].format(reply_by=reply or "the end of the week")
    return {"subject": f"[{f.get('code') or ''}] {w['subjects'][tone]} {subj_topic}", "opening": opening, "ask": ask,
            "outcome": outcome, "need": need}


def _decision_words(f, o, tone, n, last, reply):
    """{subject, opening, ask, unblocks} for a decision asked of its decision maker, by its needed-by date."""
    w = CHASE_WORDING["decision"]
    unblocks = str(o.get("unblocks") or f.get("unblocks") or "").strip() or f"the next steps on {f.get('name') or f.get('code')}"
    tmpl = w["openings"][tone]
    if not last:
        tmpl = tmpl.replace(" of {last}", "").replace("{n}, most recently on {last}", "before")
    opening = tmpl.format(unblocks=unblocks, last=tracker.shown(last), n=times(n))
    ask = w["ask"].format(reply_by=reply or "its needed-by date")
    return {"subject": f"[{f.get('code') or ''}] {w['subjects'][tone]}: {f.get('text') or ''}", "opening": opening, "ask": ask,
            "unblocks": unblocks}


MODE_WORDS = {"chase": _chase_words, "help": _help_words, "decision": _decision_words}


def chase_row(f, mode, day, include_update=True):
    """The item's one-row table, in all modes: ID; the item (a decision's "Decision needed:", the owner line for Alan's own, a
    RAID item's response, the latest update when included); Due or Needed by with its words; priority."""
    kind = f.get("kind") or "actions"
    words, overdue = due_words(f.get("due"), day, kind)
    update = str(f.get("update") or "").strip()
    return {"id": f.get("id") or "", "label": row_label(f), "item": str(f.get("text") or "").strip(),
            "owner": f"Owner: {f.get('owner')}" if mode == "help" else "", "response": row_response(f),
            "update": f"Latest update: {update}" if include_update and update else "",
            "due_label": "Needed by" if kind == "decisions" else "Due", "due": tracker.shown(f.get("due") or "") or "No date",
            "due_words": words, "overdue": overdue, "priority": f.get("priority") or ""}


def row_label(f):
    """The words before the item in its row: "Decision needed:" for a decision, "Risk:" or "Issue:" for a RAID item."""
    kind = f.get("kind") or "actions"
    return "Decision needed:" if kind == "decisions" else f"{f.get('type') or 'Risk'}:" if kind == "raid" else ""


def row_response(f):
    """A RAID item's response line, as the Draft email shows it ("none recorded yet" when empty); '' for anything else."""
    if (f.get("kind") or "") != "raid":
        return ""
    return f"Response: {str(f.get('response') or '').strip() or 'none recorded yet'}"


def chase_text(parts):
    """The email as plain text (Copy as text): the greeting, the opening, the need, the row as aligned lines, the ask, the sign-off."""
    row = parts["row"]
    lines = [parts["greeting"], "", parts["opening"], ""]
    if parts["need"]:
        lines += [f"{parts['need_label']} {parts['need']}", ""]
    label = f"{row['label']} " if row["label"] else ""
    words = f" ({row['due_words']})" if row["due_words"] else ""
    lines.append(f"  {row['id']}  {label}{row['item']}  |  {row['due']}{words}  |  {row['priority']}")
    lines += [f"  {' ' * len(row['id'])}  {x}" for x in (row["owner"], row["response"], row["update"]) if x]
    lines += ["", parts["ask"], "", *[x for x in (parts["sign_off"], parts["from"]) if x]]
    return "\n".join(lines)


def chase_draft(facts, opts=None):
    """BL-298: the drafted email for one item, from its facts, with no model call. facts: {id, code, name (the project's), kind
    (actions, raid, decisions), text, owner, due, priority, update, type, response, unblocks}; opts: {mode, tone (0 First, 1 Second,
    2 Firmer), reply_by (YYYY-MM-DD), include_update, first (the recipient's first name), from (Alan's first name), chased {n, last},
    today, hour, outcome, need, unblocks, cover (a polished opening)}. Returns {mode, tone, subject, greeting, opening, need, row,
    ask, sign_off, text}; the page builds its HTML from the same parts in the email's own palette."""
    o = dict(opts or {})
    mode = o.get("mode") or "chase"
    if mode not in CHASE_MODES:
        raise ValueError("Not a kind of chase creaite drafts.")
    tone = chase_tone(o)
    chased = o.get("chased") or {}
    words = MODE_WORDS[mode](facts, o, tone, int(chased.get("n") or 0), chased.get("last") or "", weekday_date(o.get("reply_by") or ""))
    hour = o.get("hour")
    parts = {"mode": mode, "tone": tone, "tone_name": TONE_NAMES[tone], "subject": words["subject"],
             "greeting": greeting(datetime.now().hour if hour is None else int(hour), str(o.get("first") or "").strip()),
             "opening": str(o.get("cover") or "").strip() or words["opening"], "need_label": CHASE_WORDING[mode].get("need", ""),
             "need": words.get("need", ""), "outcome": words.get("outcome", ""), "unblocks": words.get("unblocks", ""),
             "row": chase_row(facts, mode, o.get("today") or today(), o.get("include_update", True) is not False), "ask": words["ask"],
             "sign_off": CHASE_WORDING[mode]["sign_off"], "from": str(o.get("from") or "").strip()}
    parts["text"] = chase_text(parts)
    return parts


def _register():
    """The people register's people, [{name, email, aliases, org, role, hidden}]; [] when it can't be read."""
    import propose
    try:
        return propose.people_parse(propose.people_register_text()[0])
    except Exception:  # noqa: BLE001  without the register there are no suggestions to resolve, not an error
        return []


def _lookup(people):
    """{full name, alias, email or a first name only one person has (lower case): person} for resolving a name to the register."""
    out, firsts = {}, {}
    for p in people:
        fn = p["name"].split()[0].lower()
        firsts[fn] = None if fn in firsts else p
    out.update({k: p for k, p in firsts.items() if p})
    for p in people:
        out.update({k.lower(): p for k in [*p.get("aliases", []), p.get("email", "")] if k})
        out[p["name"].lower()] = p
    return out


def _named(text, people, me_names):
    """The register's people named in a text (full name, an alias, or a first name only one person has), in order of appearance."""
    text = str(text or "")
    firsts = {}
    for p in people:
        fn = p["name"].split()[0]
        firsts[fn] = None if fn in firsts else p
    found = []
    for p in people:
        if p["name"].lower() in me_names:
            continue
        keys = [p["name"], *p.get("aliases", [])] + ([p["name"].split()[0]] if firsts.get(p["name"].split()[0]) is p else [])
        at = [m.start() for k in keys if k for m in [re.search(rf"(?<![\w@.]){re.escape(k)}(?![\w@])", text)] if m]
        if at:
            found.append((min(at), p))
    return [p for _, p in sorted(found, key=lambda x: x[0])]


def _source_meeting(src):
    """(day, title) of the meeting a file source came from ("…/minutes/2026-10-12 ABC weekly.docx — Actions"), else None."""
    head = (src or "").split(" — ")[0].strip()
    m = re.search(r"/(?:minutes|transcripts)/(\d{4}-\d{2}-\d{2})\s+([^/]+?)(?:\.[A-Za-z0-9]+)?$", head)
    return (m.group(1), m.group(2).strip()) if m else None


def _meeting_attendees(day, title):
    """The saved calendar's attendees for that meeting (its day, the title matched loosely), [] when it isn't there."""
    try:
        days = calendar_gateway.read("day").get("days") or {}
    except (OSError, ValueError, AttributeError):
        return []
    want = words(title)
    for ev in days.get(day) or []:
        if isinstance(ev, dict) and (ev.get("sensitivity") or "") != "confidential" and \
                (str(ev.get("title") or "").strip().lower() == title.lower() or (want and want <= words(ev.get("title")))):
            return [str(a.get("name") or "").strip() for a in ev.get("attendees") or [] if isinstance(a, dict)]
    return []


def _me_names(settings):
    """Alan's own names (settings identity: his name and short forms), lower case: never a suggestion."""
    ident = settings.get("identity") or {}
    return {str(x).strip().lower() for x in [ident.get("name"), *(ident.get("short_forms") or [])] if str(x or "").strip()}


def _source_people(src, look, people, me_names):
    """[(name, why)] from an item's source: the sender of a mail or Teams message and anyone it names ("raised it"), then the
    source meeting's attendees from the saved calendar ("at the meeting"). A confidential source gives no one."""
    if secret(src):
        return []
    out = []
    sender = re.search(r"\bFrom:\s*([^<·]+?)\s*(?:<([^>]*)>)?\s*(?:·|$)", src)
    if sender:
        out.append(((look.get((sender.group(2) or "").strip().lower()) or {}).get("name") or sender.group(1), WHY_ORDER[1]))
    out += [(p["name"], WHY_ORDER[1]) for p in _named(src.split(" · Link:")[0], people, me_names)]
    meeting = _source_meeting(src)
    out += [(name, WHY_ORDER[2]) for name in (_meeting_attendees(*meeting) if meeting else [])]
    return out


def chase_recipients(facts, settings=None):
    """BL-298: who might help with Alan's own item, ranked: named in the item (its words or latest update), who raised it (named in
    its source), the source meeting's attendees, then the project's stakeholders. Each resolved through the people register (name,
    email, organisation, role) and never Alan; the project shown by name. Nobody is labelled a VIP (BL-288)."""
    settings = settings if settings is not None else paths.load_settings()
    me_names, people = _me_names(settings), _register()
    look = _lookup(people)
    named = _named(f"{facts.get('text') or ''} {facts.get('update') or ''}", people, me_names)
    ranked = [(p["name"], WHY_ORDER[0]) for p in named] + _source_people(str(facts.get("source") or ""), look, people, me_names) + \
        [(n, WHY_ORDER[3]) for n in stakeholders_of(facts.get("code"), facts.get("sponsor"))]
    project = tracker.project_label(facts.get("code")) if facts.get("code") else ""
    out, seen = [], set(me_names) | {"tbc", ""}
    for name, why in ranked:
        name = str(name or "").strip()
        p = look.get(name.lower()) or {}
        key = (p.get("name") or name).lower()
        if key in seen:
            continue
        seen.add(key)
        out.append({"name": p.get("name") or name, "email": p.get("email", ""), "org": p.get("org", ""), "role": p.get("role", ""),
                    "why": why, "known": bool(p), "project": project})
    return out


def stakeholders_of(code, sponsor=None):
    """The project's stakeholders: its sponsor, then the register's Key and Shared stakeholders (build_dashboard.stakeholders)."""
    names = [sponsor] if sponsor else []
    try:
        import build_dashboard
        names += build_dashboard.stakeholders().get(code or "", [])
    except (ImportError, OSError, ValueError):  # the project register is a help here: without it, the sponsor alone
        return names
    return [n for n in names if n]


def chase_anyone(settings=None):
    """"+ Anyone": everyone in the people register but Alan and hidden people, by name, with their email (never a VIP label)."""
    settings = settings if settings is not None else paths.load_settings()
    me = _me_names(settings)
    return [{"name": p["name"], "email": p["email"], "org": p["org"], "role": p["role"]}
            for p in sorted(_register(), key=lambda p: p["name"].lower()) if not p["hidden"] and p["name"].lower() not in me]


LINKED_TEXT = {"milestones": "name", "actions": "description", "raid": "description", "decisions": "decision", "promises": "description"}


def _the(name):
    """A milestone's name as the email says it: "the Phase 2 proposal"."""
    return name if name.lower().startswith("the ") else f"the {name}"


def decision_unblocks(con, decision_id, next_milestone):
    """What a decision is needed for: the first item it is linked to as a blocker (BL-90's links), else the project's next
    milestone; '' when neither is known (the email then says "the next steps on <project>")."""
    for (to,) in con.execute("SELECT to_item FROM links WHERE from_item = ? ORDER BY created", (decision_id,)):
        t = tracker.item_table(to)
        r = con.execute(f"SELECT {LINKED_TEXT[t]} FROM {t} WHERE id = ?", (to,)).fetchone() if t in LINKED_TEXT else None
        if r and r[0] and not secret(r[0]):
            return _the(r[0]) if t == "milestones" else r[0]
    return _the(next_milestone) if next_milestone else ""


def _chase_core(table, x, item_id):
    """(text, owner, due) of an item that can be chased; Refused for a decision not pending or an item that isn't open."""
    if table == "decisions":
        if x.get("status") != "Pending":
            raise Refused(f"{item_id} isn't waiting on a decision.")
        return x["decision"], x.get("made_by") or "", x.get("needed_by")
    if x.get("status") not in ("Open", "Delayed"):
        raise Refused(f"{item_id} is closed, so there is nothing to chase.")
    return x["description"], x.get("owner") or "", x.get("due_date")


def chase_facts(item_id):
    """The item's facts for a chase, from the tracker (read only): {id, code, name, kind, text, owner, due, priority, update, type,
    response, source, sponsor, status, unblocks}. Refused for a closed item, a proposal or anything confidential."""
    con = ro()
    try:
        table, x = item_row(con, str(item_id or ""))
        text, owner, due = _chase_core(table, x, item_id)
        upd, src = x.get("latest_update") or "", x.get("source") or ""
        resp = x.get("response_action") or ""
        if secret(" ".join([text, upd, resp, src])) or re.search(r"(^|/)documents/", src):
            raise Refused(f"{item_id} is marked confidential or restricted, so it can't go in an email.")
        proj = con.execute("SELECT name, sponsor, next_milestone FROM projects WHERE code = ?", (x["project"],)).fetchone()
        proj = dict(proj) if proj else {"name": x["project"], "sponsor": "", "next_milestone": ""}
        unblocks = decision_unblocks(con, x["id"], proj["next_milestone"]) if table == "decisions" else ""
        return {"id": x["id"], "code": x["project"], "name": proj["name"], "kind": table, "text": text, "owner": owner, "due": due,
                "priority": x.get("priority") or "", "update": linktext.sent_strip(upd),     # #153: chase history is never in an email
                "type": x.get("type") or "", "response": linktext.sent_strip(resp),
                "source": src, "sponsor": proj["sponsor"] or "", "status": x.get("status"), "unblocks": unblocks}
    finally:
        con.close()


def chase_to(mode, owner, asked, suggestions):
    """The recipient: the one Alan picked, else the owner or decision maker, else (Alan's own item) the first suggestion; with
    the email from the people register and the first name the greeting uses."""
    name = str(asked or "").strip() or ("" if mode == "help" else owner)
    if not name and suggestions:
        name = suggestions[0]["name"]
    p = _lookup(_register()).get(name.lower()) or {}
    name = p.get("name") or name
    return {"name": name, "email": p.get("email", ""), "first": name.split()[0] if name else ""}


def chase_options(req, d):
    """Alan's choices from the pane over the defaults: the tone, reply-by date, latest update and his own words."""
    tone = req.get("tone") if req.get("tone") in (0, 1, 2) else d["tone"]
    reply_by = req.get("reply_by") if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(req.get("reply_by") or "")) else d["reply_by"]
    inc = d["include_update"] if req.get("include_update") is None else bool(req.get("include_update"))
    own = {k: str(req[k])[:500] for k in ("outcome", "need", "unblocks", "cover") if req.get(k)}
    return {"tone": tone, "reply_by": reply_by, "include_update": inc, "chased": d["chased"], "hour": req.get("hour"), **own}


def chase_pane(req):
    """Everything the peek's Draft chase pane needs for one item: the mode and its line, the recipient (the owner or decision maker,
    from the people register; for Alan's own item the first suggestion), the suggestions and "Anyone", the defaults and the draft
    with Alan's choices (req: {id, tone, reply_by, include_update, to, outcome, need, unblocks, cover, hour}), and the wording."""
    settings = paths.load_settings()
    me = str((settings.get("identity") or {}).get("name") or "").strip()
    try:
        f = chase_facts(req.get("id"))
    except Refused as e:
        return {"ok": False, "message": str(e)}
    mode = chase_mode(f["kind"], f["owner"], me)
    d = chase_defaults(f["id"], settings=settings)
    suggestions = chase_recipients(f, settings) if mode == "help" else []
    to = chase_to(mode, f["owner"], req.get("to"), suggestions)
    draft = chase_draft(f, {**chase_options(req, d), "mode": mode, "first": to["first"], "from": me.split()[0] if me else ""})
    tag, line = mode_line(mode, to["first"], d["chased"])
    return {"ok": True, "id": f["id"], "mode": mode, "mode_tag": tag, "mode_line": line, "project": f["name"], "code": f["code"],
            "to": to, "suggestions": suggestions, "anyone": chase_anyone(settings) if mode == "help" else [],
            "defaults": d, "draft": draft, "wording": CHASE_WORDING}


# Polish in the Draft chase pane (Alan, 13-10-2026, option A). Someone else's item and a decision use the "polish" kind above (the
# opening only). Alan's own item uses "polish-help": the opening reworded, and the two lines above it (To get … done, What I need
# from you) suggested. The model gets the opening, the item's own wording, its latest update, the two lines as Alan has them and the
# tone; never the table, subject or addresses. The server reads the item itself (chase_facts: closed or confidential is refused).
DATE_OR_ID = re.compile(r"\b(?:\d{2}-\d{2}-\d{4}|\d{4}-\d{2}-\d{2}|[A-Z][A-Z0-9]{2,6}-(?:[A-Z]-)?\d{3})\b")


@kind("polish-help", "email")
def build_polish_help(con, req):
    """Alan's own item: the opening, the item as written, its latest update and his two lines, in the tone; anyone else's is refused."""
    text, tone = short(req.get("text") or "", 1500), req.get("tone") if req.get("tone") in TONES else "neutral"
    if not text:
        raise Nothing("There is no opening to polish.")
    f = chase_facts(req.get("id"))
    me = str((paths.load_settings().get("identity") or {}).get("name") or "").strip()
    if chase_mode(f["kind"], f["owner"], me) != "help":
        raise Refused("The two lines are suggested only for your own items; Polish rewords the opening alone here.")
    outcome, need = short(req.get("outcome") or "", 300), short(req.get("need") or "", 500)
    if secret(" ".join([text, outcome, need])):
        raise Refused("The wording mentions something confidential or restricted, so it isn't sent to a draft.")
    src = [{"id": "cover", "kind": "paragraph", "text": text},
           {"id": f["id"], "kind": "item", "text": f"The action as written: “{short(f['text'], 300)}”"}]
    if f.get("update"):
        src.append({"id": f["id"], "kind": "update", "text": f"Its latest update: {short(f['update'], 300)}"})
    if outcome:
        src.append({"id": "outcome", "kind": "outcome", "text": f"To get … done, as Alan has it: {outcome}"})
    if need:
        src.append({"id": "need", "kind": "need", "text": f"What I need from you, as Alan has it: {need}"})
    kept, listed = number(src)
    return Draft({"tone": tone, "sources": listed}, kept, item={"tone": tone, "id": f["id"]},
                 extra={"tone": tone, "original": text, "outcome": outcome, "need": need})


def help_outcome(text):
    """A suggested "To get … done" as the opening uses it ("to get <it>"): one line, no leading "to get", no full stop, 200 at most."""
    t = re.sub(r"^(?:to\s+)?get\s+", "", clean(text).splitlines()[0].strip() if clean(text) else "", flags=re.I)
    return short(t.rstrip(" ."), 200)


def help_need(text):
    """A suggested "What I need from you": one or two sentences, ending with a full stop, 400 at most."""
    t = re.sub(r"^what i need from you:\s*", "", " ".join(clean(text).split()), flags=re.I)
    t = short(t, 400)
    return t if not t or t[-1] in ".?!…" else t + "."


def polish_help_notes(parsed, sources):
    """Plain-code checks on the reply: a date or ID that none of the sources gives, and a line that came back empty."""
    given = " ".join(s["text"] for s in sources)
    notes = []
    for part, words_ in (("opening", parsed["text"]), ("To get … done", parsed["outcome"]), ("What I need from you", parsed["need"])):
        if not words_:
            notes.append(f"No {part} came back, so yours is kept.")
        for x in sorted(set(DATE_OR_ID.findall(words_ or ""))):
            if x not in given:
                notes.append(f"The {part} mentions {x}, which the item doesn't give.")
    return notes


@parser("polish-help")
def parse_polish_help(reply, ctx):
    """TEXT: the reworded opening; OUTCOME: To get … done; NEED: What I need from you; Alan's own versions beside them; the notes."""
    heads = ("TEXT", "OUTCOME", "NEED", "SOURCES")
    body = section(reply, "TEXT", heads) or (reply or "").split("\nOUTCOME:")[0]
    ex = ctx.get("extra") or {}
    out = {"text": clean(body), "sentences": marked(body, ctx["sources"]), "original": ex.get("original", ""), "tone": ex.get("tone"),
           "outcome": help_outcome(section(reply, "OUTCOME", heads)), "need": help_need(section(reply, "NEED", heads)),
           "was_outcome": ex.get("outcome", ""), "was_need": ex.get("need", "")}
    out["notes"] = polish_help_notes(out, ctx["sources"])
    return out
# ===== end BL-298 =====


# ===== BL-227 (sprint-drafts-writing) ===== one set of facts, many forms =====
# The ranked facts sheet (status_facts.py) written as a Steering note, a Three-line update, an Email paragraph or a Teams message, for
# an audience (Internal, Client-safe, Steering committee, Sponsor). Plain code chooses the facts; the model words them in the form's
# voice (executive-style.md › Forms); a plain-code check says when the text is longer than the form allows. The text is shown with
# Copy and is never saved; only the Current state form (Generate as before) can be saved.
FORMS = {"steering": ("Steering note", "Steering note", None, None),
         "three": ("Three-line update", "Three-line update", 60, 3),
         "email": ("Email paragraph", "Email paragraph", 120, 1),
         "teams": ("Teams message", "Teams message", 50, 3),
         "current": ("Current state", "Current state", None, None)}       # #110 B: only a refine of the editor's draft asks for it
FORM_AUDIENCES = ("internal", "client", "steering", "sponsor")


def form_voice(form):
    """The form's own note in executive-style.md (its "### <name>" section under Forms)."""
    import report
    m = re.search(rf"^### {re.escape(FORMS[form][1])}\n(.*?)(?=^#|\Z)", report.style_guide(forms=True), re.S | re.M)
    if form == "current":
        return "The Current state's own shape, as in the house voice below. Keep to the length chosen."
    return m.group(1).strip() if m else ""


def form_limits(form, length):
    """(words, lines) the form allows: a Steering note takes the chosen length's words; the others their own."""
    import status_facts
    words, lines = FORMS[form][2], FORMS[form][3]
    if words is None:
        words = status_facts.settings()["length_words"].get(length) or 150
    return words, lines


def form_request(req):
    """(code, form, audience, length, start, end) from a request, or Refused."""
    code, form = str(req.get("code") or ""), req.get("form")
    audience, length = req.get("audience") or "internal", req.get("length") or "standard"
    if not re.fullmatch(r"[A-Z][A-Z0-9]{2,6}", code):
        raise Refused("Not a project.")
    if form not in FORMS:
        raise Refused("Choose a form: steering note, three-line update, email paragraph or Teams message.")
    if audience not in FORM_AUDIENCES or length not in ("short", "standard", "fuller"):
        raise Refused("Not an audience or length creaite knows.")
    dates = [req.get(k) or None for k in ("from", "to")]
    if any(d and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d) for d in dates):
        raise Refused("Dates must be YYYY-MM-DD.")
    return code, form, audience, length, dates[0], dates[1]


@kind("status-form", "forms")
def build_status_form(con, req):
    """BL-227: the facts sheet for the audience (status_facts: client-safe holds only client-visible items; steering and sponsor
    nothing sensitive), each line a source, and the form's voice and length."""
    import contextlib
    import report
    import status_facts
    code, form, audience, length, start, end = form_request(req)
    prev = str(req.get("text") or "").strip()
    if prev and audience == "client":
        raise Refused(REFINE_NOT_CLIENT)
    if len(prev) > REFINE_TEXT_MAX:
        raise Refused(f"The draft is over {REFINE_TEXT_MAX} characters, more than a refine can take. Shorten it first.")
    if not con.execute("SELECT 1 FROM projects WHERE code = ?", (code,)).fetchone():
        raise Refused("Not a project.")
    with contextlib.redirect_stdout(sys.stderr):
        f = status_facts.facts(code, start, end, audience)
    src = [{"id": ln["fid"], "kind": part["title"], "text": ln["text"]} for part in f["parts"] for ln in part["lines"]]
    if not src:
        raise Nothing("The facts sheet is empty for this period and audience: nothing to write from.")
    kept, listed = number(src)
    words, lines = form_limits(form, length)
    note = str(req.get("note") or "").strip()[:500]
    return Draft({"form": form, "form_name": FORMS[form][0], "name": f"{code} {f['name']}", "start": tracker.shown(f["start"]),
                  "end": tracker.shown(f["end"]), "audience_note": report.AUDIENCE_NOTES[audience],
                  "length_note": f"at most {words} words" + (f" and {lines} line{'s' if lines != 1 else ''}" if lines else ""),
                  "note": refine_note(prev, note) if prev else f"Alan's steer: {note}\n" if note else "", "form_voice": form_voice(form),
                  "style": report.style_guide(forms=True),
                  "sources": listed}, kept, item={"code": code},
                 extra={"form": form, "audience": audience, "words": words, "lines": lines, "refine": bool(prev)})


@parser("status-form")
def parse_status_form(reply, ctx):
    """The text and its sources, and a plain-code length check against the form's limits."""
    ex = ctx.get("extra") or {}
    left_out = 0
    if ex.get("refine") and ex.get("audience") != "internal":                  # #110 B: the audience's rule again, on this version
        reply, left_out = refine_keep_sourced(reply, ctx["sources"])
    out = default_parse(reply, ctx)
    n_words, n_lines = len(re.findall(r"\S+", out["text"])), len([ln for ln in out["text"].splitlines() if ln.strip()])
    notes = []
    if ex.get("words") and n_words > ex["words"]:
        notes.append(f"{n_words} words: longer than this form's {ex['words']}.")
    if ex.get("lines") and n_lines > ex["lines"]:
        notes.append(f"{n_lines} lines: this form takes {ex['lines']}.")
    if left_out:
        notes.append(f"{left_out} sentence{' has' if left_out == 1 else 's have'} no source, so "
                     f"{'it was' if left_out == 1 else 'they were'} left out of this version.")
    return {**out, "form": ex.get("form"), "audience": ex.get("audience"), "words": n_words, "lines": n_lines, "length_notes": notes}

# ===== #110 B: Steer it further. A refine is the same draft kind ("status-form") asked again with the previous version (`text`) and the
# change Alan asks for (`note`): the facts are worked out again for the same period and audience, so a version draws on the same sheet
# and the prompt says a change can add no fact. For any audience but Internal, plain code then keeps only the sentences that rest on a
# fact. Not offered for the Client-safe audience yet (follow-up C2: the client sheet still carries the tracker's internal health reason).
REFINE_TEXT_MAX = 1500                   # the most /api/draft passes in `text`; a longer draft is refused, never cut
REFINE_NOT_CLIENT = "Steer it further is not available for a Client-safe draft yet."


def refine_note(prev, change):
    """The prompt's note for a refine: the previous version, and the change asked for, which can add no fact."""
    return ("THIS IS A REFINEMENT of an earlier draft, not a new one. Rewrite the PREVIOUS VERSION to make the change Alan asks for, and "
            "keep everything he did not ask to change. Keep to the facts below: a change can never add a fact that is not in them, "
            "however it is worded (if it asks for something the facts do not hold, leave that out and say nothing about it).\n"
            f"Alan's change: {change or 'none given: tighten the wording'}\n"
            f"--- PREVIOUS VERSION ---\n{prev}\n--- END OF THE PREVIOUS VERSION ---\n")


def refine_keep_sourced(reply, sources):
    """(the reply without its unsourced sentences, how many were left out). It cuts the reply where `sentences` splits it, so each
    dropped sentence is removed at its own position (never the first equal text elsewhere) with the break before it."""
    body = (reply or "").split("\nSOURCES:")[0].strip()
    parts = re.split(r"((?<=[.!?\]])\s+(?=[A-Z0-9“\"(])|\n+)", body)         # sentence, break, sentence, break, ...
    kept, gone = [], 0
    for i in range(0, len(parts), 2):
        if any(m["unsourced"] for m in marked(parts[i], sources)):
            gone += 1
        else:
            kept.append(((parts[i - 1] if i else "") if kept else "") + parts[i])      # each sentence brings the break before it
    return "".join(kept), gone
# ===== end #110 B =====
# ===== end BL-227 =====


# ===== BL-220 (sprint-drafts-extraction) ===== Sharpen: a vague action's title (extraction.vague: under four words or no verb; a clear
# title is refused, so the model is asked only for a vague one) is reworded verb-first from what creaite holds: the words as written,
# the project, its workstreams and open milestones, the owner, and the passage it came from. The page shows it beside the original;
# Alan picks one and the original is kept (BL-232's as_proposed for a proposal; the source line for a new item).
@kind("sharpen", "sharpen")
def build_sharpen(con, req):
    """The facts for Sharpen: the words as written, the owner, the project's lists, the source passage. A clear title is refused."""
    import extraction
    title, code, owner, srcline = sharpen_item(con, req)
    why = extraction.vague(title)
    if not why:
        raise Refused("The title is already clear: it has a verb and says what. Sharpen is for a vague title.")
    src = [{"id": "", "kind": "title", "text": f"The action as written: “{short(title, 300)}”"}]
    if owner and owner != "TBC":
        src.append({"id": "", "kind": "owner", "text": f"Its owner: {owner}"})
    src += project_lists(con, code)
    p = source_path(srcline)
    if p and not secret(srcline) and not secret(p.name):
        text = file_text(p)
        for q in passages(text, title, None, limit=2, span=1) if not secret(text[:400]) else []:
            if not secret(q):
                src.append({"id": "", "kind": "passage", "path": paths.rel(p), "text": f"{p.stem}: “{short(q, 300)}”"})
    kept, listed = number(src)
    return Draft({"title": title, "why": why, "sources": listed}, kept, item={"title": title})


def sharpen_item(con, req):
    """(title, project code, owner, source line) of the action to sharpen: a proposal, a tracker item, or the words typed."""
    if req.get("proposal"):
        table, x = proposal_item(req)
    elif req.get("id"):
        table, x = item_row(con, str(req.get("id")))
    else:
        table, x = "actions", {"description": req.get("title") or "", "project": req.get("code") or ""}
    if table != "actions":
        raise Refused("Sharpen is for actions.")
    title = str(req.get("title") or x.get("description") or "").strip()
    if not title:
        raise Nothing("Write the action first; Sharpen rewords what you typed.")
    return title, str(req.get("code") or x.get("project") or ""), x.get("owner") or "", x.get("source") or ""


def project_lists(con, code):
    """The project's name, its active workstreams and its open milestones, as sources (names only)."""
    if not re.fullmatch(r"[A-Z][A-Z0-9]{2,6}", code or ""):
        return []
    out = [{"id": code, "kind": "project", "text": f"The project: {tracker.project_label(code)}"}]
    ws = [r[0] for r in con.execute("SELECT name FROM workstreams WHERE project = ? AND coalesce(status, 'Active') = 'Active'", (code,))]
    ms = [r[0] for r in con.execute("SELECT name FROM milestones WHERE project = ? AND coalesce(status, '') NOT IN ('Done', 'Cancelled')",
                                    (code,))]
    if ws:
        out.append({"id": code, "kind": "workstreams", "text": "Its workstreams: " + ", ".join(ws[:12])})
    if ms:
        out.append({"id": code, "kind": "milestones", "text": "Its open milestones: " + ", ".join(ms[:12])})
    return out


@parser("sharpen")
def parse_sharpen(reply, ctx):
    """The sharpened title (with its sources), the original beside it, and the one-line why."""
    lines = (section(reply, "TITLE", ["TITLE", "WHY", "SOURCES"]) or (reply or "")).strip().splitlines()
    line = lines[0].strip() if lines else ""
    why = clean(section(reply, "WHY", ["TITLE", "WHY", "SOURCES"]))[:200]
    return {"text": clean(line).rstrip("."), "sentences": marked(line, ctx["sources"]), "original": ctx["item"]["title"], "why": why}
# ===== end BL-220 =====


# ===== BL-286 (sprint-prep-server) ===== Shape the meeting: Alan's instruction (his focus and aim) read and turned into cited notes.
# Plain code gathers the sources (prep_shape.shape_sources: the instruction, the invite and its ranking, the listed items, what
# wasn't covered last time, the items and documents linked to the focus, milestones due, the latest minutes); the model states its
# reading and words the notes; prep_shape.parse checks every line's citation. A confidential meeting: the instruction and tracker
# items only (the live server also gives that run no tools). Nothing is saved here: Accept saves to prep-focus.json.
SHAPE_SOURCES = 30


def _shape_meeting(ctx, conf):
    mt = ctx["meeting"]
    what = f"{mt['title']}, {tracker.shown(ctx['day'])} {mt.get('start', '')}–{mt.get('end', '')}"
    return what + (f" ({mt['where']})" if mt.get("where") and not conf else "")


def _shape_correction(reading):
    if not reading:
        return ""
    focus = "; ".join(f.get("text") or f.get("id") or "" for f in reading.get("focus") or [])
    return (f"\nAlan corrected your reading. Keep it exactly: FOCUS: {focus}\nAIM: {reading.get('aim') or ''}\n"
            f"SHOW: {reading.get('show') or 'focus-first'}\n")


def _shape_research(conf):
    if conf:
        return ("\nThis meeting is confidential: use only the sources below. Do not search, open or read anything else, and "
                "never look for the invite.")
    return ("\nYou may read the meeting records and documents listed below (read-only) to understand them, but cite only the "
            "numbered sources. Never open, read or search a file in a notes folder: Alan's notes are not sources here, and one "
            "marked confidential is kept out of prep.")             # BL-301 (v20-confidential-prep)


def _known_ids(con, codes):
    out = []
    for table in ("actions", "raid", "decisions", "milestones"):
        marks = ",".join("?" * len(codes))
        out += [r[0] for r in con.execute(f"SELECT id FROM {table} WHERE project IN ({marks})", codes)]
    return out


def _shape_context(key):
    """(the meeting's prep context, its Prep brief record); Refused when the meeting isn't in the calendar any more."""
    import contextlib
    import prep_page
    with contextlib.redirect_stdout(sys.stderr):           # a library note must not mix into the JSON
        d = prep_page._collect()
        with prep_page.using(d):
            ctx = prep_page.context(key)
    if ctx.get("error"):
        raise Refused(ctx["error"])
    return ctx, prep_page.meeting_entry(d, key)


def _shape_clear(v):
    """Clear: True (every section), a list of sections, or False (keep Alan's edits)."""
    return v if v is True or isinstance(v, list) else False


@kind("shape", "shape")
def build_shape(con, req):
    """BL-286: the sources for shaping one meeting from Alan's instruction (and his corrected reading, when he gave one)."""
    import prep_shape
    key, instruction = str(req.get("key") or ""), str(req.get("instruction") or "").strip()[:4000]
    if not re.fullmatch(r"(\d{4}-\d{2}-\d{2}\|)?\d{2}:\d{2}\|.{1,200}", key):
        raise Refused("Which meeting?")
    if not instruction:
        raise Nothing("Write how you want to run the meeting first: the focus and what you want out of it.")
    ctx, m = _shape_context(key)
    conf = bool(ctx["meeting"].get("confidential"))
    reading = prep_shape.clean_reading(req["reading"]) if isinstance(req.get("reading"), dict) else None
    src = prep_shape.shape_sources(con, ctx, instruction, reading, m.get("rank"))[:SHAPE_SOURCES]
    for i, s in enumerate(src, 1):
        s["ref"] = f"S{i}"
    mid = prep_shape.canonical(key, ctx["day"])
    current = req.get("current") if isinstance(req.get("current"), dict) else prep_shape.get(mid)
    codes = (ctx.get("research") or {}).get("codes") or [ctx["project"]]
    return Draft({"meeting": _shape_meeting(ctx, conf), "project": ctx.get("project_name") or "", "instruction": instruction,
                  "correction": _shape_correction(reading), "research": _shape_research(conf),
                  "sources": "\n".join(f"[{s['ref']}] {s['text']}" for s in src)}, src,
                 item={"key": key, "id": mid, "project": ctx["project"]},
                 extra={"confidential": conf, "key": key, "day": ctx["day"], "known_ids": _known_ids(con, codes),
                        "current": current or {}, "clear": _shape_clear(req.get("clear")), "instruction": instruction})


@parser("shape")
def parse_shape(reply, ctx):
    """The reading, the drafted notes (merged with Alan's edits unless he cleared them) and the checks on every line."""
    import prep_shape
    ex = ctx.get("extra") or {}
    out = prep_shape.parse(reply, ctx["sources"], ex.get("known_ids") or [], ex.get("current"), ex.get("clear"))
    lines = [ln for sec in prep_shape.SECTIONS for ln in out["drafted"].get(sec) or []]
    out["checks_ok"] = out.pop("ok")                      # "ok" is the draft event's own (it says the reply could be read)
    return {**out, "confidential": bool(ex.get("confidential")), "instruction": ex.get("instruction", ""),
            "text": "\n".join(ln["text"] for ln in lines),
            "sentences": [{"text": ln["text"], "refs": ln["refs"], "unsourced": not ln["refs"]} for ln in lines]}
# ===== end BL-286 =====


# ── the two steps the live server calls ──────────────────────────────────────

# ===== BL-322 (v193-sneak-peek-server) ===== Sneak peek: an action's latest update, tidied ("tidy the update") or written from the
# reason Alan typed ("push it out a week because Northgate's dates slipped"). Under the feature "update"; Use this or Keep mine in the box.
SNEAK_MODES = ("tidy", "reason")


@kind("sneak-update", "update")
def build_sneak_update(con, req):
    """Builder for Sneak peek's update: the action's own update to tidy, or Alan's reason to word as one. Nothing else is a source."""
    item_id = str(req.get("id") or "")
    table, x = item_row(con, item_id)
    if table != "actions":
        raise Refused("Only actions have a latest update.")
    mode = req.get("mode")
    if mode not in SNEAK_MODES:
        raise Refused("Sneak peek drafts an update by tidying the one there, or from a reason.")
    words = (x.get("latest_update") or "").strip() if mode == "tidy" else str(req.get("text") or "").strip()[:1500]
    if not words:
        raise Nothing("There's no update to tidy yet." if mode == "tidy" else "No reason was given.")
    if secret(words):
        raise Refused("Those words are marked confidential or restricted: no draft is made from them.")
    src = [{"id": item_id, "kind": "words", "text": ("The update as it stands" if mode == "tidy" else "Alan's reason")
            + f": “{short(words, 600)}”"}]
    kept, listed = number(src)
    task = ("Tidy the action's latest update: the same facts, said more clearly and briefly." if mode == "tidy" else
            "Turn Alan's reason into the action's latest update: one short line saying what changed and why.")
    return Draft({"item": item_lines(table, x), "task": task, "sources": listed, "today": tracker.shown(today())}, kept,
                 item={"id": item_id, "table": table, "mode": mode})
# ===== end BL-322 =====


# ===== BL-326 (v1.9.5): what ask creaite shows for a draft run: one plain ask line, as if Alan had typed it, and one closure
# line with a link. Never the prompt or the reply. {id} is a work item's ID, {project} the project's full name (BL-101), {meeting}
# the meeting's title and day, {n} how many, {form} the form's name.
RUN_LINES = {
    "update": ("Draft the latest update for {id}", "Drafted the latest update for {id}: check it before you use it"),
    "sneak-update": ("Draft the latest update for {id}", "Drafted the latest update for {id}: check it before you use it"),
    "update-bulk": ("Draft updates for {n} stale actions", "Drafted the updates: they're waiting in Review"),
    "client": ("Draft client wording for {id}", "Drafted the client wording for {id}: check it before you use it"),
    "client-bulk": ("Draft client wording for {project}'s waiting items", "Drafted the client wording: it's waiting in Review"),
    "thinking": ("Suggest the thinking fields for {id}", "Suggested the thinking fields for {id}: check them before you use them"),
    "health": ("Draft the reason for {project}'s health change", "Drafted the reason: check it before you save the health"),
    "forecast": ("Draft the reason for the forecast change on {id}", "Drafted the reason: check it before you save the forecast"),
    "sharpen": ("Sharpen a vague action", "Sharpened the action's title: pick the wording you want"),
    "agenda": ("Draft the agenda and invite text for {meeting}", "Drafted the agenda and invite text: copy what you need"),
    "polish": ("Polish the email wording", "Polished the wording: check it before you copy the email"),
    "polish-help": ("Polish the request for help on {id}", "Polished the request: check it before you copy the email"),
    "status-form": ("Write {project}'s status as {form}", "Wrote the status: copy it from the draft"),
    "shape": ("Shape {meeting}", "Shaped the meeting: check the notes before you keep them"),
}
RUN_DEFAULT = ("Draft with Claude", "The draft is ready: check it before you use it")
RUN_UNREAD = "Couldn't finish: the draft couldn't be read. Try again."


def _run_meeting(key):
    """A meeting key as words: "ABC steering, Thursday 15th October 10:00"."""
    parts = str(key or "").split("|")
    if len(parts) == 3:
        day, start, title = parts
    elif len(parts) == 2:                             # an undated key is today's (prep_page.split_key)
        day, (start, title) = date.today().isoformat(), parts
    else:
        return "the meeting"
    import prep_page
    when = " ".join(x for x in ((prep_page.long_day(day) if day else ""), start) if x)
    return f"{' '.join(title.split())[:120] or 'the meeting'}{', ' + when if when else ''}"


def _run_form(name):
    """A form's name as words: "a steering note", "an email paragraph", "a Teams message"."""
    form = FORMS.get(str(name or ""), ("",))[0]
    if not form:
        return "another form"
    return f"{'an' if form[:1] in 'AEIOU' else 'a'} {form.lower().replace('teams', 'Teams')}"


def _run_link(name, req, item, code):
    """Where a draft run's result can be seen: Review for a draft of several, the meeting's prep page, the item, the project."""
    if name in ("update-bulk", "client-bulk"):
        return {"href": "#review", "link": "Review"}
    if name in ("agenda", "shape") and req.get("key"):
        from urllib.parse import quote
        key = str(req["key"])
        key = key if re.match(r"\d{4}-\d{2}-\d{2}\|", key) else f"{date.today().isoformat()}|{key}"
        return {"href": "#prep=" + quote(key, safe=""), "link": "Open"}
    if item:
        return {"href": f"#item={item}", "link": "Open"}
    return {"href": f"#cockpit={code}", "link": "Open"} if code else {}


def _run_project(code):
    """A project's full name (BL-101); its code when the tracker can't be read."""
    if not code:
        return "the project"
    try:
        return tracker.project_label(code)
    except SystemExit:               # no tracker yet: the code stands in
        return code


def run_lines(req, extra=None):
    """{ask, done, href, link} for a draft run (BL-326): the plain lines ask creaite shows, and where the result can be seen."""
    name = req.get("kind")
    ask, done = RUN_LINES.get(name, RUN_DEFAULT)
    item = str(req.get("id") or "")
    item = item if ID_RE.fullmatch(item) else ""
    code = str(req.get("code") or "") or item.split("-")[0]
    words = {"id": item or "the item", "project": _run_project(code),
             "meeting": _run_meeting(req.get("key")), "n": len(req.get("ids") or []) or "the", "form": _run_form(req.get("form"))}
    return {"ask": ask.format(**words), "done": done.format(**words), **_run_link(name, req, item, code)}


def run_closure(ctx, got):
    """The closure line for a finished draft run: the kind's own line, how many were staged for a draft of several, or plainly
    that the reply couldn't be read."""
    lines = ctx.get("run") or {}
    if not got:
        return {"ok": False, "line": RUN_UNREAD}
    if got.get("nothing"):                                  # #272: plainly that there was nothing to suggest
        return {"ok": True, "line": got["nothing"]}
    out = {"ok": True, "line": lines.get("done") or RUN_DEFAULT[1]}
    if isinstance(got.get("staged"), int):
        n = got["staged"]
        out["line"] = f"Drafted {n} item{'' if n == 1 else 's'}: {'it is' if n == 1 else 'they are'} waiting in Review" if n \
            else "Nothing new to draft: nothing was staged"
    if lines.get("href"):
        out.update(href=lines["href"], link=lines.get("link") or "Open")
    return out
# ===== end BL-326 =====


# ===== v2.1.0 #90: the ✦ on the weekly, client and minutes sheets. Two kinds on /api/draft: "report-section" (a section of a weekly
# or client report) and "minutes-section" (a section of a minutes record). Plain code gathers the facts; the model words one section
# in one of four ways (Polish, Shorter, Executive, or Alan's own instruction: edit_ai's actions). A suggestion, never a write: the
# sheet shows it beside Alan's words and he keeps his, or uses it. Privacy by construction:
#   - a client report's section draws only on the facts that make up the client version (status_facts' client sheet), and each line
#     is checked again with client_leak (item_problem for every item it rests on, text_findings for its words); the reply is too;
#   - a minutes draft from the distributed version is built from minutes_record.distributed_of, so no Internal only line or row,
#     and no Sensitive, partner-only or excluded item, is ever in its facts or prompt; its section's words are read from that
#     version, never from what the page sent.
# Counts (offered, used, edited, rejected) are under the two feature names; counts only, never text.
SECTION_ACTIONS = ("polish", "shorter", "executive", "custom")
SECTION_TEXT_MAX = 6000
VIP_RE = re.compile(r"\bVIPs?\b", re.I)


def section_task(req):
    """(action, the instruction Claude is given) for a section draft: edit_ai's own wording for the action."""
    import edit_ai
    action = str(req.get("action") or "")
    if action not in SECTION_ACTIONS:
        raise Refused("Choose Polish, Shorter, Executive or your own words.")
    instruction = " ".join(str(req.get("instruction") or "").split())[:400]
    if action == "custom":
        if not instruction:
            raise Refused("Say what you want done with the section.")
        return action, "Do what Alan asks with the section, and only that. His instruction: " + instruction
    task = edit_ai.OPTIONS[action][2]
    if action == "executive":
        import report
        task += "\n\nThe executive voice:\n" + report.style_guide()
    return action, task


def section_panes(req):
    """The section's panes as [{title, text}] when the page sent them, else []."""
    out = []
    for x in (req.get("panes") if isinstance(req.get("panes"), list) else [])[:6]:
        if isinstance(x, dict):
            out.append({"title": short(x.get("title"), 60), "text": str(x.get("text") or "")[:SECTION_TEXT_MAX]})
    return out


def section_current(req):
    """(the section as it stands, its panes) as the page sent them."""
    panes = section_panes(req)
    if panes:
        return "\n\n".join(f"### {p['title']}\n{p['text']}" for p in panes), panes
    return str(req.get("text") or "")[:SECTION_TEXT_MAX], panes


def client_line_ok(con, code, ln, blocking):
    """Whether a facts-sheet line may reach a client section: every item it rests on passes client_leak.item_problem, and its words
    pass client_leak.text_findings (so an internal-only item, a Sensitive or partner-only one, a label that excludes it, a memory
    line marked Client-safe: no and the words confidential or restricted all drop it)."""
    import client_leak
    if secret(ln["text"]) or VIP_RE.search(ln["text"]):
        return False
    for ref in ln.get("src") or []:
        if ID_RE.fullmatch(str(ref)) and client_leak.item_problem(con, ref, blocking):
            return False
    return not client_leak.text_findings(con, code, ln["text"])


def report_facts(con, code, fri, client):
    """The numbered facts for a report section (a Draft's sources), with the period and, for a client report, a note on where the
    facts come from. [] when there is nothing to draw on.
    - A weekly report: the week's facts sheet (status_facts, internal).
    - A client report: the client report's own facts (report_doc._Client: locked to the approved internal week, meta.client_facts,
      over the client report's own period, _client_period), each line kept only when client_leak passes it. The tracker's health
      flag, its internal reason and the change since the last internal status are never in them (#90 review F1): the client's
      health and reason are the client report's own, which this route never reads."""
    import contextlib
    from datetime import timedelta
    import status_facts
    if client:
        return client_report_facts(con, code, fri)
    start, end = (date.fromisoformat(fri) - timedelta(days=4)).isoformat(), fri
    with contextlib.redirect_stdout(sys.stderr):
        f = status_facts.facts(code, start, end, "internal")
    src = [{"id": ln["fid"], "kind": part["title"], "text": ln["text"]} for part in f["parts"] for ln in part["lines"]
           if not (secret(ln["text"]) or VIP_RE.search(ln["text"]))]
    return src, start, end, ""


def client_report_facts(con, code, fri):
    """(sources, start, end, note) for a client report's section: the items the client report itself is built from (#90 review F1,
    F4), in their client wording, each line passed again by client_line_ok. No health: neither the flag nor any reason."""
    import contextlib
    import client_leak
    import report_doc
    with contextlib.redirect_stdout(sys.stderr):
        c = report_doc._Client(code, fri, None, None)
    blocking = client_leak.blocking_labels(con)
    lines = client_lines(c)
    src = [{"id": ref, "kind": kind, "text": text} for kind, text, ref in lines
           if text.strip() and client_line_ok(con, code, {"text": text, "src": [ref]}, blocking)]
    note = (f"The facts are the client report's own, locked to the approved internal weekly report for week ending "
            f"{tracker.shown(c.base['date'])}." if c.locked else
            "The facts are the client report's own, as they stand today: no internal weekly report is approved for it yet.")
    return src, c.start, c.end, note


def _client_action_line(c, a):
    """(kind, line, id) for a client-facts action, or None: completed in the period, or open (an ask when the client owns it)."""
    if a["status"] == "Complete":
        return ("Progress", f"Completed: {a['title']}", a["id"]) if c.start <= (a.get("closed") or "")[:10] <= c.end else None
    if a["status"] == "Cancelled":
        return None
    due = f", due {tracker.shown(a['due_date'])}" if a.get("due_date") else ""
    who = "Asked of you" if a["client_owned"] else "Action"
    return ("Asks" if a["client_owned"] else "Actions", f"{who}: {a['title']} ({a['owner']}){due}, {a['status'].lower()}", a["id"])


def _client_decision_line(c, d):
    """(kind, line, id) for a client-facts decision: made in the period, or still needed; else None."""
    if d["status"] == "Made" and (d.get("date") or "") >= c.start:
        return ("Decisions", f"Decision made {tracker.shown(d['date'])}: {d['title']}", d["id"])
    if d["status"] == "Pending":
        by = f" by {tracker.shown(d['needed_by'])}" if d.get("needed_by") else ""
        return ("Decisions", f"Decision needed{by}: {d['title']}", d["id"])
    return None


def client_lines(c):
    """[(kind, line, id)] of a report_doc._Client's facts, in the client report's own order and wording."""
    out = []
    for m in c.of("milestones"):
        when = f", {m['shown_date']}" if m.get("shown_date") else ""
        out.append(("Milestones", f"Milestone {m['title']}: {m['state']}{when}", m["id"]))
    out += [x for x in (_client_action_line(c, a) for a in c.of("actions")) if x]
    out += [x for x in (_client_decision_line(c, d) for d in c.of("decisions")) if x]
    out += [("Points to watch", f"{r['type']}: {r['title']}", r["id"]) for r in c.of("raid")]
    return out


def section_shape(panes):
    """The reply's shape: panes under their own headings, or the section's words only."""
    return ("In panes: reply with each pane under its own “### Title” line, in the same order, and nothing else."
            if panes else "Reply with the section's words only.")


def report_request(con, req):
    """(code, is it a client report, the week ending, action, task, the section's words, its panes) for a report section, or the
    refusal. #127: the audience is bound on the server from the report the request names (`document`, checked by
    edit_ai.document_audience as /api/edit/ai's place is), never from what the page claims; no report named is refused. A client
    section that already holds something a client mustn't see is refused (edit_ai.client_problems): nothing is sent to a draft."""
    import edit_ai
    import report_doc
    code = str(req.get("code") or "")
    if not con.execute("SELECT 1 FROM projects WHERE code = ?", (code,)).fetchone():
        raise Refused("Not a project.")
    action, task = section_task(req)
    try:
        audience = edit_ai.document_audience(req, code, ("client", "weekly"))
    except edit_ai.Refused as e:
        raise Refused(str(e).replace("sent to Claude", "sent to a draft")) from None
    if audience is None:
        raise Refused("Say which report: the page didn't name it, so nothing was sent to a draft. Reload the page and try again.")
    try:
        fri = report_doc.friday(req["document"].get("week_ending") or None)
    except ValueError:
        raise Refused("The week ending must be a date.") from None
    current, panes = section_current(req)
    if not current.strip():
        raise Nothing("This section has no words to redraft.")
    client = audience == "client"
    bad = edit_ai.client_problems(code, current, current) if client else []
    if bad == [edit_ai.REGISTER]:
        raise Refused("The people register couldn't be read, so the names couldn't be checked and nothing was sent to a draft. "
                      "Fix it on the People page, then try again.")
    if bad:
        raise Refused("This section already holds wording that isn't client-safe. Fix it first; nothing was sent to a draft.")
    return code, client, fri, action, task, current, panes


@kind("report-section", "report-section")
def build_report_section(con, req):
    """The facts for one section of a weekly or client report. A client report's facts are the client sheet's, kept line by line
    only when client_leak passes them; the section's own words are refused when they already hold something a client mustn't see."""
    import report
    code, client, fri, action, task, current, panes = report_request(con, req)
    src, start, end, note = report_facts(con, code, fri, client)
    if not src:
        raise Nothing("There are no facts for this week to redraft from" + (" that a client may see." if client else "."))
    kept, listed = number(src)
    sid = str(req.get("section") or "")[:60]
    return Draft({"task": task, "name": tracker.project_label(code), "start": tracker.shown(start), "end": tracker.shown(end),
                  "heading": short(req.get("heading"), 80) or "the section",
                  "audience_note": report.AUDIENCE_NOTES["client" if client else "internal"] + (f"\n{note}" if note else ""),
                  "current": current,
                  "shape": section_shape(panes), "sources": listed},
                 kept, item={"code": code, "section": sid},
                 extra={"template": "report-section", "section": sid, "action": action, "original": current,
                        "panes": [p["title"] for p in panes], "audience": "client" if client else "internal", "code": code,
                        "people": people_names()})


def _record_lines(use, skip_id, per=8):
    """[(heading, line)] of a minutes record's other sections, the summary and the decisions first."""
    import minutes_record
    order = {"summary": 0, "decisions": 1, "actions": 2, "updates": 3}
    secs = [s for s in use.get("sections") or [] if s.get("id") not in (skip_id, "header", "source")]
    out = []
    for s in sorted(secs, key=lambda s: order.get(s.get("id"), 9)):
        if s.get("type") == "table":
            lines = [" · ".join(str(v) for v in (r.get("cells") or {}).values() if v) for r in s.get("rows") or []]
        else:
            lines = [minutes_record.line_text(ln) for ln in str(s.get("text") or "").splitlines() if ln.strip()]
        out += [(s.get("heading") or s.get("id"), ln) for ln in lines[:per] if ln and ln != "None recorded."]
    return out


def minutes_current(req, sec, dist):
    """(the section as it stands, its panes): the distributed version's words come from the record, never from the page."""
    if dist or not (str(req.get("text") or "").strip() or section_panes(req)):
        return str(sec.get("text") or "")[:SECTION_TEXT_MAX], []
    return section_current(req)


def marked_lines(doc, sid):
    """The lines of section `sid` that the record marks Internal only (layout.internal_only)."""
    return [m["text"] for m in (doc.get("layout") or {}).get("internal_only") or []
            if isinstance(m, dict) and m.get("section") == sid and m.get("text")]


def minutes_version(req):
    """(the distributed version, is the draft for it, the section) for a minutes section, or the refusal. The distributed version is
    minutes_record.distributed_of: nothing marked Internal only or withheld is in it. Its facts are always drawn from it, whichever
    version is shown (#90 review F3), so an internal-version draft can't carry an Internal only line or a withheld item into a
    section that is distributed. An internal-version section that holds a line marked Internal only is refused: a redraft would
    reword the line and lose its mark."""
    import minutes_record
    version = req.get("version") or "internal"
    if version not in ("internal", "distributed"):
        raise Refused("Redraft from the internal or the distributed version.")
    try:
        doc = minutes_record.record_at(req.get("path"))[1]
    except minutes_record.RecordError as e:
        raise Refused(str(e)) from None
    dist = version == "distributed"
    minutes_project(doc)
    shared = minutes_record.distributed_of(doc)
    sid = str(req.get("section") or "")
    sec = next((s for s in (shared if dist else doc).get("sections") or [] if s.get("id") == sid), None)
    if not sec or sec.get("type") in ("header", "table"):
        raise Refused("That section can't be redrafted" + (" in this version." if dist else "."))
    if not dist and marked_lines(doc, sid):
        raise Refused("This section has lines marked Internal only, and a redraft would lose their mark. Redraft it in the "
                      "distributed version, or take the mark off first.")
    return shared, dist, sec


def minutes_project(doc):
    """The minutes' project code, read from the record (never the page), or Refused before Claude runs when there is none or the
    tracker doesn't hold it (#262, 2.6): the reply is checked against it, so with none every draft would be dropped."""
    import edit_ai
    code = str(((doc.get("meta") or {}).get("projects") or [doc.get("project")])[0] or "")
    if not code or not edit_ai._project_known(code):
        raise Refused(edit_ai.NO_MINUTES_PROJECT)
    return code


@kind("minutes-section", "minutes-section")
def build_minutes_section(con, req):
    """The facts for one section of a meeting's minutes: always the distributed version's other sections (minutes_record.
    distributed_of), so nothing marked Internal only or withheld is in the prompt or the facts. The distributed version's own words
    are read from it, never from the page; the internal version's are the page's, with no line marked Internal only."""
    action, task = section_task(req)
    shared, dist, sec = minutes_version(req)
    sid = sec["id"]
    current, panes = minutes_current(req, sec, dist)
    if not current.strip() or current.strip() == "None recorded.":
        raise Nothing("This section has no words to redraft.")
    if dist and VIP_RE.search(current):
        raise Refused("This section can't be redrafted.")
    kept, listed = number([{"id": "", "kind": h, "text": f"{h}: {short(ln, 300)}"} for h, ln in _record_lines(shared, sid)
                           if not (secret(ln) or VIP_RE.search(ln))])
    return Draft({"task": task, "title": shared.get("title") or "the meeting", "day": tracker.shown(shared.get("date") or "") or "",
                  "version_note": ("This is the distributed version, sent to everyone who was invited: use only what is in the facts "
                                   "below." if dist else "This is the internal version. The rest of the minutes below is the "
                                   "distributed version's: nothing marked Internal only or withheld."),
                  "heading": short(sec.get("heading"), 80) or "the section", "current": current,
                  "shape": section_shape(panes), "sources": listed},
                 kept, item={"section": sid, "version": "distributed" if dist else "internal"},
                 extra={"template": "minutes-section", "section": sid, "action": action, "original": current,
                        "panes": [p["title"] for p in panes], "audience": "distributed" if dist else "internal",
                        "code": minutes_project(shared),
                        "people": people_names()})


def split_panes(text, titles):
    """A reply split by its “### Title” lines into [{title, text}] in the sheet's order; [] when the panes can't be matched."""
    parts = re.split(r"^###\s*(.+?)\s*$", text or "", flags=re.M)
    got = {parts[i].strip().lower(): parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}
    if not titles or any(t.strip().lower() not in got for t in titles):
        return []
    return [{"title": t, "text": got[t.strip().lower()]} for t in titles]


# #90 review F1: the reply check's second line for a client section. The client facts never hold the tracker's health reason, so a
# client draft that brings it in (whole, or a run of five of its words), or an internal-only marker, is dropped. Words already in
# the section as Alan wrote it are his, not the draft's, and do not count.
# #127 round 6: also "internal:only", "internal.only" and "internal ; only": punctuation with no space after "internal" or a space
# before it, as prose never writes it ("internal. Only", "internal; only" and "internal, only" stay prose).
# #127 round 7, one rule for the punctuated forms. Up to three of . : ; , between the words:
#   - with no space ("internal.only", "internal,only", "internal::only", "internal..only", "internal;;only"): the marker, unless
#     "Only" starts a sentence (a capital O then lower case: "internal.Only the totals go" is prose missing a space) or the word
#     runs on into a file name, domain, address or path (".yaml", ".example.org", "@example.com", "/x");
#   - with a space before ("internal ; only", "internal . only", French spacing): the marker only when nothing but punctuation or
#     the line's end follows "only" ("Costs are internal : only licences go" is prose; "Note: internal ; only." is the marker),
#     and again never "Only" starting a sentence.
# Spaces or hyphens alone ("internal only", "internal-only", "internal - only") are always the marker.
# #127 round 8, the two exceptions narrowed (the round-7 ones hid real markers):
#   - "Only" starts a sentence only when a space and a lower-case word follow ("internal.Only the totals go"), never alone
#     ("Internal.Only", "Note: internal.Only.", "**Internal.Only**");
#   - a file name, domain or address runs on in lower case (".yaml", ".example.org", ".v2", "@example.com"), never ".Do",
#     ".DRAFT", ".Final" or "@ACME"; a path ("/data", "\draft") too, but not after a marker standing alone as a status, at a
#     line's start or right after a label ("Status: internal.only/v2"; "The path internal.only/config" is a path);
#   - spaced, right after a label or at a line's start ("Status: internal ; only do not forward"), it is the marker whatever
#     follows, unless "Only" starts a sentence ("Item: Internal . Only the board signs.").
_ONLY_SENTENCE = r"(?-i:(?!Only[ \t]+[a-z]))"
_RUNS_ON = r"(?-i:\.[a-z0-9][a-z0-9_-]*|@[a-z0-9])"
INTERNAL_MARK = re.compile(r"\binternal[\s-]+only\b"
                           r"|\binternal[.:;,]{1,3}" + _ONLY_SENTENCE + r"only\b(?!" + _RUNS_ON + r"|(?-i:[/\\][a-z0-9]))"
                           r"|(?<![^\n:])[ \t]*internal[.:;,]{1,3}" + _ONLY_SENTENCE + r"only\b(?!" + _RUNS_ON + r")"
                           r"|\binternal\s+[.:;,]{1,3}\s*" + _ONLY_SENTENCE + r"only\b(?![ \t]*\w)"
                           r"|(?<![^\n:])[ \t]*internal\s+[.:;,]{1,3}\s*" + _ONLY_SENTENCE + r"only\b"
                           r"|\bnot for (?:the )?client\b|\bfor internal use\b|\bhealth_diff\b", re.I)
MD_ESCAPE = re.compile(r"\\([!-/:-@\[-`{-~])")      # a backslash before ASCII punctuation: Markdown's escape


def unescaped(text):
    """Text with Markdown's backslash escapes read as the character ("internal\\-only", as the Notes writer stores a typed
    "internal-only", is "internal-only"); a backslash before a letter or digit (a path) stays. v240-leak2."""
    return MD_ESCAPE.sub(r"\1", text or "")


RUN = 5


def _wordlist(text):
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def carries(text, phrase, n=RUN):
    """Whether `text` holds `phrase` whole, or any run of `n` of its words in order (case and punctuation ignored)."""
    words, hay = _wordlist(phrase), f" {' '.join(_wordlist(text))} "
    if not words:
        return False
    if len(words) <= n:
        return len("".join(words)) >= 8 and f" {' '.join(words)} " in hay
    return any(f" {' '.join(words[i:i + n])} " in hay for i in range(len(words) - n + 1))


def internal_findings(con, code, text, original=""):
    """What a client section's draft holds that only the internal record has: the tracker's health reason, or an internal-only
    marker, when the section's own words did not already hold it. Both are read as the ID check reads text (edit_ai.normal: an
    invisible character or a look-alike dash hides neither; #127 round 4)."""
    import edit_ai
    text, original = unescaped(edit_ai.normal(text)), unescaped(edit_ai.normal(original))
    found = []
    row = con.execute("SELECT health_reason FROM projects WHERE code = ?", (code,)).fetchone()
    reason = edit_ai.normal((row[0] if row else "") or "")      # #127 round 5: folded as the text is (its accents too)
    if reason.strip() and carries(text, reason) and not carries(original, reason):
        found.append("the internal health reason")
    if INTERNAL_MARK.search(text or "") and not INTERNAL_MARK.search(original or ""):
        found.append("an internal-only marker")
    return found


def section_dropped(text, ex):
    """Why a redrafted section is dropped, or "": something private (VIP however written, 2.6), the minutes' check against the
    record's project (#262, 2.6: the minutes go to attendees, as the AI bar's check), a client report's whole client check (#127),
    or something confidential the section didn't hold."""
    import edit_ai
    original = ex.get("original") or ""
    if VIP_RE.search(text) or (edit_ai._private(text) and not edit_ai._private(original)):
        return "The draft named something private, so it was dropped. Try again."
    if ex.get("template") == "minutes-section":
        bad = edit_ai.minutes_problems(ex.get("code") or "", edit_ai._untagged(text), edit_ai._untagged(original))  # M2: HTML read through
        if bad:
            return (edit_ai.refusal(bad, True) if set(bad) & set(edit_ai.FAIL_CLOSED) else
                    "The draft was dropped: it added something internal (an item that isn't client-visible, a name or internal "
                    "wording) that the minutes would carry to attendees. Try again.")
    if ex.get("audience") == "client":
        bad = edit_ai.client_problems(ex.get("code") or "", text, original)
        if bad:
            return "The draft was dropped: " + ("the people register couldn't be read, so its names couldn't be checked."
                                                if bad == [edit_ai.REGISTER] else "it held wording that isn't client-safe.")
    elif secret(text) and not secret(original):
        return "The draft was dropped: it brought in something marked confidential."
    return ""


@parser("report-section")
def parse_section(reply, ctx):
    """The redrafted section: its words, its sources, and edit_ai's plain-code check of what it lost or added. A draft that fails
    the privacy check (client_leak on a client report's reply) or names a VIP comes back with no text and a plain reason."""
    import edit_ai
    out = default_parse(reply, ctx)
    ex = ctx.get("extra") or {}
    text = out["text"]
    out.update(section=ex.get("section") or "", action=ex.get("action"), notes=[])
    dropped = {**out, "text": "", "sentences": []}
    why = section_dropped(text, ex)
    if why:
        return {**dropped, "message": why}
    out["notes"] = edit_ai.check(ex.get("original") or "", text, ex.get("people") or [])
    if ex.get("panes"):
        out["panes"] = split_panes(text, ex["panes"])
        if not out["panes"]:
            return {**dropped, "message": "The draft didn't keep the section's panes. Try again."}
    return out


PARSERS["minutes-section"] = parse_section
RUN_LINES.update({
    "report-section": ("Redraft a section of {project}'s report", "Redrafted the section: keep yours or use this"),
    "minutes-section": ("Redraft a section of the minutes", "Redrafted the section: keep yours or use this"),
})
# ===== end #90 =====



# ===== #272: Suggest says nothing rather than a refusal. The Suggest kinds' prompts ask for exactly NO_SUGGESTION when the sources give
# nothing to base a suggestion on; that reply, and (the backstop, plain code) a reply whose first sentence reads as the model saying it
# can't, come back as {nothing}: no text, so nothing reaches the field, and a note naming what the kind would have drawn on.
NO_SUGGESTION = "NO_SUGGESTION"
SUGGEST_KINDS = ("thinking", "update", "sneak-update")
_WRAP = " \t\r\n`'\"“”‘’*_."
_HEAD = re.compile(r"^(?:RESPONSE|REASONING|OPTIONS|UPDATE|TEXT|ANSWER):\s*")
_TASK = r"(?:suggest|draft|propose|recommend|write|offer|give|provide|say|determine|judge|tell)"
_INPUTS = r"(?:passages?|sources?|evidence|context|closed[- ]risks?|information|details?|minutes)"
REFUSAL_RES = [
    # the model about itself: "I can't suggest…", "I'm unable to draft…", "I don't have enough information…"
    re.compile(rf"\bI(?:\s+am|'m|’m)?\s+(?:can(?:'|’)?t|cannot|can not|unable to|not able to)\s+(?:\w+\s+){{0,2}}?{_TASK}\b", re.I),
    re.compile(rf"\bI\s+(?:don(?:'|’)?t|do not)\s+have\s+(?:\w+\s+){{0,2}}?{_INPUTS}\b", re.I),
    re.compile(rf"^(?:sorry,?\s+)?unable to\s+{_TASK}\b", re.I),
    re.compile(r"\bas an AI(?:\s+(?:language\s+)?model|\s+assistant)?\s*,", re.I),
    # about its inputs: "No passage … was supplied", "The passage doesn't say", "There is no meeting passage…"
    re.compile(rf"\b(?:no|not enough|insufficient|neither)\b[^.;]{{0,60}}\b{_INPUTS}\b[^.;]{{0,60}}?"
               r"\b(?:was|were|is|are|has been|have been)\s+(?:supplied|provided|given|available|included)\b", re.I),
    re.compile(rf"\b(?:the|these|this)\s+(?:meeting\s+)?{_INPUTS}\s+(?:was|were)\s+not\s+(?:supplied|provided|given)\b", re.I),
    re.compile(rf"\b(?:the|these|this)\s+(?:meeting\s+)?{_INPUTS}\s+(?:do(?:es)?n(?:'|’)?t|do(?:es)? not)\s+"
               r"(?:say|give|mention|cover|show|contain|include|support|describe)\b", re.I),
    re.compile(rf"^(?:there\s+(?:is|are)\s+)?(?:not enough|insufficient)\s+(?:information|evidence|detail|details|context)\s+(?:to|for)\s+"
               rf"(?:\w+\s+){{0,2}}?{_TASK}\b", re.I),
    re.compile(rf"^there\s+(?:is|are)\s+(?:no|nothing)\b[^.;]{{0,40}}\b(?:to\s+{_TASK}|to base|to go on|(?:meeting\s+)?passages?|"
               r"sources?|in the (?:sources?|passage|meeting))\b", re.I),
    re.compile(rf"^nothing to\s+(?:{_TASK}|base|go on)\b", re.I),
]


def is_no_suggestion(text):
    """True when a reply (or its parsed field) is the sentinel, give or take spaces, quotes, a code fence, bold or a section head."""
    t = re.sub(r"^```[a-z]*\s*|\s*```$", "", (text or "").strip()).strip(_WRAP)
    return _HEAD.sub("", t).strip(_WRAP) == NO_SUGGESTION


_CONTRAST = re.compile(r"\b(?:but|however|though|although|instead|meanwhile)\b[,\s]+(.+)", re.I)
_FIELD_HEAD = re.compile(r"^[A-Z][A-Z ]*:")


def _refuses(text):
    return any(r.search(text or "") for r in REFUSAL_RES)


def usable_body(first, hits, marked_rest=()):
    """v2.6 review: True when a reply whose first sentence reads as a refusal still carries a suggestion: the first sentence goes
    on past its refusal with "but", "however"… and three or more words that don't refuse ("I can't give a firm date, but plan UAT
    for December"), or a later sentence carries a source tag and doesn't refuse (a field head such as IMPACT: aside)."""
    tail = first[max(m.end() for m in hits):]
    c = _CONTRAST.search(tail)
    if c and len(c.group(1).split()) >= 3 and not _refuses(c.group(1)):
        return True
    return any(s.get("refs") and not _FIELD_HEAD.match(s.get("text") or "") and not _refuses(s.get("text"))
               for s in marked_rest if isinstance(s, dict))


def reads_as_refusal(text, marked_sentences=None):
    """The backstop: the first sentence (at most 200 characters) reads as the model saying it can't suggest anything, and the
    reply has no usable body (usable_body). Only the first sentence is read for the refusal, so a real suggestion that says
    "can't" later, or about someone else, passes; `marked_sentences` (the parsed sentences, with their source refs) lets a
    sourced later sentence count as a body."""
    first = next(iter(sentences(clean(text))), "")
    first = re.sub(r"^[-–•*\s]+", "", first)[:200]
    hits = [m for m in (r.search(first) for r in REFUSAL_RES) if m]
    return bool(hits) and not usable_body(first, hits, (marked_sentences or [])[1:])


def nothing_note(ctx):
    """What a Suggest kind would have drawn on, as the note under its button."""
    item = ctx.get("item") or {}
    if ctx.get("kind") == "thinking":
        if item.get("field") == "response_action":
            return "Nothing to suggest from: no meeting passage and no closed risks with a response"
        what = "the options considered" if item.get("field") == "options" else "the reasoning"
        return f"Nothing to suggest from: no meeting passage gives {what}"
    if ctx.get("kind") == "update":
        since = tracker.shown(item["since"]) if item.get("since") else "the last update"
        return f"Nothing to draft from: nothing since {since} says where the action stands"
    return ("Nothing to draft from: the update as it stands holds nothing to tidy" if item.get("mode") == "tidy"
            else "Nothing to draft from: the reason given doesn't say what changed")


def said_nothing(ctx, reply, out):
    """The note when a Suggest kind's reply is the sentinel or reads as a refusal, else None (any other kind: always None)."""
    if ctx.get("kind") not in SUGGEST_KINDS:
        return None
    body = out.get("text") or ""
    if (is_no_suggestion(reply) or is_no_suggestion(body) or reads_as_refusal(body, out.get("sentences"))
            or (not body.strip() and reads_as_refusal(reply))):
        return nothing_note(ctx)
    return None
# ===== end #272 =====


def context(req):
    """{feature, kind, prompt, sources, item, extra} for a request, or {nothing}/{refused} with the words to show."""
    name = req.get("kind")
    if name not in KINDS:
        return {"refused": "Not a kind of draft creaite knows."}
    feature, fn = KINDS[name]
    if not enabled(feature):
        return {"refused": f"{FEATURES.get(feature, (feature.capitalize(),))[0]} is turned off in Settings › General › AI drafts.",
                "off": True}
    con = ro()
    try:
        d = fn(con, req)
    except Nothing as e:
        return {"nothing": str(e), "feature": feature}
    except Refused as e:
        return {"refused": str(e), "feature": feature}
    finally:
        con.close()
    template = d.extra.get("template") or name
    return {"feature": feature, "kind": name, "prompt": render(template, d.values), "sources": d.sources, "item": d.item,
            "extra": d.extra, "run": run_lines(req, d.extra)}                  # BL-326: the plain lines ask creaite shows


def result(req, ctx, reply):
    """The parsed draft: text, sentences with their sources (an unsourced one marked), and the kind's own parts."""
    out = (PARSERS.get(ctx["kind"]) or default_parse)(reply, ctx)
    note = said_nothing(ctx, reply, out)
    if note:                                                # #272: nothing to suggest: no text, so nothing reaches the field
        return {"nothing": note, "text": "", "sentences": [], "sources": ctx["sources"], "unsourced": 0}
    out["sources"] = ctx["sources"]
    out["unsourced"] = sum(1 for s in out.get("sentences") or [] if s["unsourced"])
    return out


def main(argv):
    """The scaffold's commands: context, result (a several-item draft is staged as pending proposals), stat, stats and features.
    Counts go to system/staging/draft-stats.json; nothing here writes to the tracker."""
    if not argv:
        print(__doc__)
        return 2
    cmd, args = argv[0], argv[1:]
    if cmd == "context":
        print(json.dumps(context(json.loads(sys.stdin.read() or "{}")), ensure_ascii=False))
        return 0
    if cmd == "result":
        got = json.loads(sys.stdin.read() or "{}")
        out = result(got.get("request") or {}, got["context"], got.get("reply") or "")
        stager = STAGERS.get(got["context"].get("kind"))
        if stager:                                          # a draft of several items: staged as pending proposals
            name, n = stager(out, got["context"])
            out.update({"staged": n, "file": name})
            if n:
                record(got["context"]["feature"], "offered", n)
        elif out.get("nothing"):                            # #272: counted as nothing, never offered or used
            record(got["context"]["feature"], NOTHING_EVENT)
        elif out.get("text"):
            record(got["context"]["feature"], "offered")
        print(json.dumps(out, ensure_ascii=False))
        return 0
    if cmd == "stat" and len(args) >= 2:
        try:
            row = record(args[0], args[1], int(args[2]) if len(args) > 2 else 1)
        except ValueError as e:
            print(f"Not counted: {e}")
            return 1
        print(json.dumps(row))
        return 0
    if cmd == "stats":
        data = read_stats()
        if "--json" in args:
            print(json.dumps(data, indent=1))
        else:
            for f, (label, _) in FEATURES.items():
                r = data.get(f) or {}
                print(f"{label}: offered {r.get('offered', 0)}, used {r.get('used', 0)}, edited {r.get('edited', 0)}, rejected {r.get('rejected', 0)}")
        return 0
    if cmd == "features":
        on = switches()
        rows = [{"id": f, "label": label, "help": hlp, "on": on.get(f, True)} for f, (label, hlp) in FEATURES.items()]
        print(json.dumps(rows) if "--json" in args else "\n".join(f"{r['label']}: {'on' if r['on'] else 'off'}" for r in rows))
        return 0
    print(__doc__)
    return 2


# ===== BL-224 (sprint-drafts-writing) ===== the command line's writing commands, ahead of main's own
def _cmd_chase(args):
    """chase record --ids A,B [--mode chase|help|decision|update|followup]: one record in chases.json (references only)."""
    opts = dict(zip(args[1::2], args[2::2]))
    try:
        print(json.dumps(chase_record((opts.get("--ids") or "").split(","), opts.get("--mode", "chase"))))
    except ValueError as e:
        print(f"Not recorded: {e}")
        return 1
    return 0


def _cmd_followup(args):
    """followup: the meeting (JSON on stdin) → its attendees and the minutes' summary paragraph."""
    print(json.dumps(followup_facts(json.loads(sys.stdin.read() or "{}")), ensure_ascii=False))
    return 0


def _cmd_chase_pane(args):
    """chase-pane: BL-298's Draft chase for one item (JSON {id, …} on stdin) → its mode, recipient, suggestions, defaults and draft."""
    print(json.dumps(chase_pane(json.loads(sys.stdin.read() or "{}")), ensure_ascii=False))
    return 0


WRITING_COMMANDS = {"chase": _cmd_chase, "chases": lambda args: print(json.dumps(chase_counts())) or 0, "followup": _cmd_followup,
                    "chase-pane": _cmd_chase_pane}   # BL-298
_main_before_writing = main


def main(argv):  # noqa: F811  the writing commands first, then the scaffold's own (sprint-drafts-writing)
    """drafts.py's command line: the writing sprint's commands (chase, chases, followup), else the scaffold's."""
    if argv and argv[0] in WRITING_COMMANDS:
        return WRITING_COMMANDS[argv[0]](argv[1:])
    return _main_before_writing(argv)
# ===== end BL-224 =====


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
