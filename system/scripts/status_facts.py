"""creaite status facts (BL-106): the short, ranked facts sheet an executive status is written from.

A script decides what matters and hands the model a sheet; the model writes the narrative and does not choose the facts.
Plain text with sources, no model call, nothing written. It is also what "Drafted from" shows next to a Current state draft.

  python3 system/scripts/status_facts.py facts <CODE> [--from YYYY-MM-DD] [--to YYYY-MM-DD]
                                                      [--audience internal|client|steering|sponsor] [--json]

Parts (a part with nothing to say is left out, never shown empty): Position, Movement, Exposure, Asks, Numbers, Trend.
Item IDs never appear in the sheet's sentences; they sit in each line's `[src: …]` tail, so the prose stays free of tracker
language. Caps (risks named, overdue items named, asks) are in settings.json `status`. The client audience holds only
client-visible items in their client wording, no internal warnings, no flow counts, and numbers only from client reports.
Set CREAITE_NOW="YYYY-MM-DD HH:MM" to fix the clock (tests).

Asks holds the decisions needed (BL-53: pending decisions, asked of someone or falling to Alan) before the open actions other people owe.

BL-207: every line has a fact ID (F1, F2, … in the sheet's order; `fid` in the JSON, `[F3]` in the text). The Current state
prompts ask for each sentence to end with the IDs it rests on, and status_checks.evidence maps them back to rows and quotes.
The sheet is deterministic, so working it out again with the same period and audience gives the same IDs.
"""
import contextlib
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import linktext  # noqa: E402  (#121: a link in item text is its words in the facts)
import paths  # noqa: E402
import tracker  # noqa: E402
import report  # noqa: E402
import build_dashboard  # noqa: E402
import docx_tools  # noqa: E402

ID_RE = re.compile(r"\b[A-Z][A-Z0-9]{2,6}-(?:[A-Z]-)?\d{3}\b")
RANK = {"Urgent": 0, "High": 1, "Medium": 2, "Low": 3, None: 4, "": 4}
DEFAULTS = {"headline_max_words": 30, "max_risks": 2, "max_overdue_named": 3, "max_named_changes": 3, "max_asks": 3,
            "length_words": {"short": 40, "standard": 150, "fuller": 250}}
FIGURE = re.compile(r"\d+(?:[.,]\d+)?\s?%|\b\d+\s+(?:of|out of)\s+\d+\b|\b(?:target|baseline|budget|forecast)\b[^.\n]*\d", re.I)
PART_TITLES = {"position": "Position", "movement": "Movement", "exposure": "Exposure", "asks": "Asks",
               "numbers": "Numbers (candidate lines from the period's minutes and reports; use one only if it matters)",
               "trend": "Trend"}


def settings():
    """The status settings (settings.json `status`) over DEFAULTS: the caps on what the sheet names, and the lengths in words."""
    s = paths.load_settings().get("status") or {}
    return {**DEFAULTS, **{k: v for k, v in s.items() if k in DEFAULTS}, "length_words": {**DEFAULTS["length_words"], **(s.get("length_words") or {})}}


def strip_ids(text):
    """(the text without item IDs, the IDs found): the sheet's sentences carry none, their sources do."""
    ids = ID_RE.findall(text or "")
    t = re.sub(r"\s*\((?:\s*%s\s*,?)+\)" % ID_RE.pattern, "", text or "")
    t = ID_RE.sub("", t)
    t = re.sub(r"\s{2,}", " ", t)
    t = re.sub(r"\s+([,.;:)])", r"\1", t)
    return re.sub(r"^[\s:,;-]+", "", t).strip(), ids


def sent(text):
    """A sentence: its own full stop, never two."""
    return linktext.words(text or "").strip().rstrip(".") + "."


def plural(n, one, many):
    """"1 action" or "3 actions"."""
    return f"{n} {one if n == 1 else many}"


def owner_text(owner):
    """"Owner <name>", or "No owner set" when there is none or it is TBC."""
    return f"Owner {owner}" if owner and owner != "TBC" else "No owner set"


def shown(d):
    """A stored date as DD-MM-YYYY, or "no date"."""
    return tracker.shown(d) if d else "no date"


def days_between(later, earlier):
    """Days from `earlier` to `later` (both YYYY-MM-DD)."""
    return (date.fromisoformat(later) - date.fromisoformat(earlier)).days


class Part:
    def __init__(self, key):
        self.key, self.lines = key, []

    def add(self, text, *src):
        """Add a line, its item IDs moved out of the text into its sources (with `src`); a line left empty is dropped."""
        clean, ids = strip_ids(text)
        if clean:
            self.lines.append((clean, list(dict.fromkeys([*ids, *[s for s in src if s]]))))

    def as_dict(self):
        """The part as JSON: key, title and lines [{text, src}]."""
        return {"key": self.key, "title": PART_TITLES[self.key], "lines": [{"text": t, "src": s} for t, s in self.lines]}


def me_names(cfg):
    """Alan's own names, lower case (settings.json identity: his name and short forms)."""
    ident = cfg.get("identity") or {}
    return {n.strip().lower() for n in [ident.get("name") or "", *(ident.get("short_forms") or [])] if n and n.strip()}


def is_me(owner, names):
    """Whether an owner is Alan, ignoring an "(Organisation)" suffix."""
    o = re.sub(r"\s*\([^)]*\)\s*$", "", owner or "").strip().lower()
    return bool(o) and o in names


def client_org_matcher(client):
    """A test of whether an owner is on the client's side: the "(Organisation)" after their name matches the client."""
    org = lambda owner: (re.search(r"\(([^)]+)\)\s*$", owner or "") or [None, ""])[1]  # noqa: E731
    return lambda owner: bool(client and org(owner) and (org(owner).lower() in client.lower()  # noqa: E731
                                                          or client.lower().split()[0] in org(owner).lower()))


def what_it_is(row):
    """A client-visible item's own wording (its client message's first part), else its description."""
    own = report.message_parts(row["client_message"]).get(report.HEADINGS[0])
    return linktext.words(own or row.get("description") or row.get("decision") or "")


def item_key(row):
    """Rank an item: priority first, then the ones tied to a milestone, then the newest."""
    return (RANK.get(row.get("priority")), 0 if row.get("milestone") else 1, -(date.fromisoformat(row["raised"]).toordinal() if row.get("raised") else 0))


def position_part(con, p, code, start, end, client):
    """The Position part: health now with its reason, what the evidence suggests (internal only) and the change since the last weekly
    status."""
    part = Part("position")
    health = p["health"] or "not set"
    part.add(f"Health now: {health}" + (f" — {p['health_reason'].strip().rstrip('.')}" if p["health_reason"] else "") + ".")
    if not client:
        ev = report.health_evidence(code)
        if ev["suggested"] != p["health"]:
            part.add(f"The tracker's evidence suggests {ev['suggested']}: " + "; ".join(ev["reasons"] or ["no specific reason"]) + ".")
        elif ev["reasons"]:
            part.add("The evidence behind it: " + "; ".join(ev["reasons"]) + ".")
    last = report.rows(con, "SELECT * FROM updates WHERE project = ? AND week_ending < ? ORDER BY week_ending DESC LIMIT 1", code, end)
    if not last:
        part.add("No earlier weekly status is on record to compare with.")
    elif not p["health"]:
        pass
    elif last[0]["health"] != p["health"]:
        part.add(f"Changed since the last status: it was {last[0]['health']} (week ending {shown(last[0]['week_ending'])}), now {health}.")
    else:
        part.add(f"Unchanged since the last status (week ending {shown(last[0]['week_ending'])}: {last[0]['health']}).")
    return part


def movement_part(con, p, code, start, end, client):
    """The Movement part: milestones reached or moved in the period, the next one, items opened and closed, and the notable ones by name
    (client-visible only, for a client)."""
    part = Part("movement")
    cfg = settings()
    ms = report.milestones(con, code)
    if client:                                       # BL-186: the client filter, as in the client report
        ms = tracker.client_milestones(ms)
    names = {m["id"]: m["name"] for m in ms}
    ch = report.rows(con, "SELECT at, item_id, field, old_value, new_value FROM change_log WHERE tbl = 'milestones' AND substr(at,1,10) "
                          "BETWEEN ? AND ? AND field IN ('status','forecast_date') AND op = 'update' ORDER BY rowid", start, end)
    for c in ch:
        if client and c["item_id"] not in names:
            continue
        name = names.get(c["item_id"], "A milestone")
        if c["field"] == "status" and c["new_value"] == "Done":
            part.add(f"Milestone reached: {name} (done {shown(c['at'][:10])}).", c["item_id"])
        elif c["field"] == "forecast_date" and c["old_value"] and c["new_value"]:
            part.add(f"Milestone moved: {name}, from {shown(c['old_value'])} to {shown(c['new_value'])}.", c["item_id"])
    nxt = next((m for m in ms if m["status"] == "Planned"), None)
    if nxt:
        slip = nxt["slip_days"]
        part.add(f"Next milestone: {nxt['name']}, forecast {shown(nxt['forecast_date'])}"
                 + (f", baseline {shown(nxt['baseline_date'])} ({'+' if slip > 0 else ''}{slip} days)" if nxt["baseline_date"] and slip else
                    ", on its baseline date" if nxt["baseline_date"] else "")
                 + (f", {nxt['percent']}% complete" if nxt.get("percent") is not None else "")
                 + f"; {(nxt['client_word'] if client else nxt['state']).lower()}" + ".", nxt["id"])   # BL-186: the five states
    vis = " AND client_visible = 1" if client else ""
    a_new = report.rows(con, f"SELECT * FROM actions WHERE project = ? AND status != 'Cancelled' AND raised BETWEEN ? AND ?{vis}", code, start, end)
    a_done = report.rows(con, f"SELECT * FROM actions WHERE project = ? AND status = 'Closed' AND closed BETWEEN ? AND ?{vis}", code, start, end)
    r_new = report.rows(con, f"SELECT * FROM raid WHERE project = ? AND status != 'Cancelled' AND raised BETWEEN ? AND ?{vis}", code, start, end)
    r_done = report.rows(con, f"SELECT * FROM raid WHERE project = ? AND status = 'Closed' AND closed BETWEEN ? AND ?{vis}", code, start, end)
    decs = report.rows(con, f"SELECT * FROM decisions WHERE project = ? AND status = 'Made' AND date BETWEEN ? AND ?{vis}", code, start, end)
    bits = [plural(n, one, many) + f" {verb}" for n, one, many, verb in
            ((len(a_new), "action", "actions", "opened"), (len(a_done), "action", "actions", "closed"),
             (len(r_new), "risk or issue", "risks and issues", "raised"), (len(r_done), "risk or issue", "risks and issues", "closed"),
             (len(decs), "decision", "decisions", "made")) if n]
    if bits:
        part.add(f"In the period ({shown(start)} to {shown(end)}): " + ", ".join(bits) + ".")
    named = sorted([("Closed", x) for x in a_done + r_done] + [("Raised", x) for x in r_new], key=lambda t: item_key(t[1]))[:cfg["max_named_changes"]]
    for verb, x in named:
        text = what_it_is(x) if client else x["description"]
        part.add(f"{verb} and notable: {text.strip().rstrip('.')}" + (f" (priority {x['priority']})" if x.get("priority") and not client else "") + ".", x["id"])
    for d in decs[:cfg["max_named_changes"]]:
        part.add(f"Decision made on {shown(d['date'])}: " + sent(d["client_message"].strip() if client else d["decision"]), d["id"])
    return part


def exposure_part(con, p, code, start, end, client):
    """The Exposure part: the top open risks and issues and the overdue actions; internal only, blockers on milestones and early warnings
    (BL-51)."""
    part = Part("exposure")
    cfg = settings()
    vis = " AND client_visible = 1" if client else ""
    risks = sorted(report.rows(con, f"SELECT * FROM raid WHERE project = ? AND status = 'Open' AND type IN ('Risk','Issue'){vis}", code), key=item_key)
    for r in risks[:cfg["max_risks"]]:
        if client:
            part.add(f"{r['type']}: " + sent(report.client_text(r["client_message"])), r["id"])
            continue
        part.add(f"{r['type']}, {r['priority'] or 'priority not set'}: " + sent(r["description"]) + f" {owner_text(r['owner'])}. "
                 + (f"Response: {linktext.words(r['response_action']).strip().rstrip('.')}" if r["response_action"]
                    else "No response recorded yet")
                 + (f" (due {shown(r['due_date'])})" if r["response_action"] and r["due_date"] else "") + ".", r["id"])
    if len(risks) > cfg["max_risks"]:
        part.add(f"{plural(len(risks) - cfg['max_risks'], 'further open risk or issue', 'further open risks and issues')}, not named here.")
    cut = end
    overdue = report.rows(con, f"SELECT * FROM actions WHERE project = ? AND status IN ('Open','Delayed') AND due_date < ?{vis} ORDER BY due_date", code, cut)
    if overdue:
        part.add(f"{plural(len(overdue), 'action is', 'actions are')} overdue.")
    for a in overdue[:cfg["max_overdue_named"]]:
        text = what_it_is(a) if client else a["description"]
        part.add(f"Overdue by {days_between(cut, a['due_date'])} days (due {shown(a['due_date'])}): " + (sent(text) if client else sent(text) + f" {owner_text(a['owner'])}."), a["id"])
    if client:
        return part
    deps = report.rows(con, "SELECT r.*, m.name AS ms_name, m.forecast_date AS ms_date FROM raid r JOIN milestones m ON m.id = r.milestone "
                            "WHERE r.project = ? AND r.type = 'Dependency' AND r.status = 'Open' AND m.status = 'Planned'", code)
    for d in sorted(deps, key=lambda x: x["due_date"] or "9999")[:cfg["max_risks"]]:
        late = d["due_date"] and d["ms_date"] and d["due_date"] > d["ms_date"]
        part.add(f"Blocker: {d['description']} (owner {d['owner']}, due {shown(d['due_date'])}) holds {d['ms_name']}, forecast {shown(d['ms_date'])}"
                 + (" — the dependency is due after the milestone" if late else "") + ".", d["id"], d["milestone"])
    names, covered = {}, {d["id"] for d in deps}
    for w in build_dashboard.early_warnings(paths.load_settings(), report.today(), con):
        if w["p"] != code or w["id"] in covered:        # a blocker is already named above
            continue
        if w["id"] not in names:
            row = con.execute("SELECT description FROM actions WHERE id = ? UNION ALL SELECT description FROM raid WHERE id = ?",
                              (w["id"], w["id"])).fetchone()
            names[w["id"]] = row[0] if row else ""
        part.add(f"Early warning: {names[w['id']].strip().rstrip('.')} — {w['text'].strip().rstrip('.')}.", w["id"])
    return part


def decision_asks(con, code, end, client, names):
    """Pending decisions (BL-53) as asks, overdue first then soonest: [(text, who, needed_by, id)]. The client audience sees only
    client-visible ones, in their client wording; internal also says when a decision falls to Alan himself."""
    out = []
    for d in report.decisions_needed(con, code, date.fromisoformat(end)):
        row = report.rows(con, "SELECT * FROM decisions WHERE id = ?", d["id"])[0]
        if client and not (row["client_visible"] and tracker.message_complete("decisions", row["client_message"])):
            continue
        text = linktext.words(row["client_message"]).strip() if client else d["text"]
        mine = not client and is_me(d["by"], names)
        who = "Alan" if mine else (re.sub(r"\s*\([^)]*\)\s*$", "", d["by"] or "").strip() or "")
        late = f", {d['overdue_days']} day{'s' if d['overdue_days'] != 1 else ''} overdue" if d["overdue_days"] else ""
        when = f" Needed by {shown(d['needed_by'])}{late}." if d["needed_by"] else " No date needed by."
        lead = "Decision for Alan" if mine else f"Decision needed from {who}" if who else "Decision needed (no one asked yet)"
        out.append((f"{lead}: " + sent(text) + when, who, d["needed_by"], d["id"]))
    return out


def asks_part(con, p, code, start, end, client, asks):
    """What is needed from whom, by when: decisions needed first (BL-53), then the open actions other people own."""
    part = Part("asks")
    cfg = settings()
    names = me_names(paths.load_settings())
    room = cfg["max_asks"]
    dec = decision_asks(con, code, end, client, names)
    for line, who, due, ident in dec[:room]:
        part.add(line, ident)
        asks.append({"who": who or "no one yet", "text": line, "due": due, "id": ident, "kind": "decision"})
    room -= min(len(dec), room)
    if len(dec) > cfg["max_asks"]:
        part.add(f"{plural(len(dec) - cfg['max_asks'], 'further decision is', 'further decisions are')} needed, not named here.")
    if client:
        is_client = client_org_matcher(report.build_dashboard.memory(paths.project_dir(code))["client"])
        rows = [a for a in report.rows(con, "SELECT * FROM actions WHERE project = ? AND client_visible = 1 AND status IN ('Open','Delayed') "
                                            "ORDER BY due_date IS NULL, due_date", code) if is_client(a["owner"])]
    else:
        rows = [a for a in report.rows(con, "SELECT * FROM actions WHERE project = ? AND status IN ('Open','Delayed') "
                                            "ORDER BY due_date IS NULL, due_date", code) if not is_me(a["owner"], names)]
        rows.sort(key=lambda a: (not (a["due_date"] and a["due_date"] < end), a["due_date"] is None, a["due_date"] or ""))
    for a in rows[:room]:
        text = what_it_is(a) if client else a["description"]
        late = a["due_date"] and a["due_date"] < end
        who = re.sub(r"\s*\([^)]*\)\s*$", "", a["owner"] or "").strip() or "owner not set"
        part.add(f"Waiting on {who}: " + sent(text) + (f" Due {shown(a['due_date'])}" if a["due_date"] else " No due date")
                 + (f", {days_between(end, a['due_date'])} days overdue" if late else "") + ".", a["id"])
        asks.append({"who": who, "text": text, "due": a["due_date"], "id": a["id"]})
    if len(rows) > room:
        part.add(f"{plural(len(rows) - room, 'further open action', 'further open actions')} with other owners, not named here.")
    return part


def numbers_part(code, start, end, client):
    """Lines from the period's minutes and reports that state a measure (a %, "x of y", a target or baseline), with their file.
    Candidates only: code doesn't understand them, so the prompt says to use one only if it matters. Client: client reports only."""
    part = Part("numbers")
    dirs = [paths.folder(code, "minutes")] + ([] if client else [])
    reports = {d.resolve(): d for d in (paths.folder(code, "weekly_reports"), paths.folder(code, "client_reports")) if d.is_dir()}
    dated = lambda f: re.match(r"(\d{4}-\d{2}-\d{2})", f.name)  # noqa: E731
    files = [f for d in ([] if client else dirs) + list(reports.values()) if d.is_dir() for f in d.glob("*")
             if dated(f) and start <= dated(f).group(1) <= end and f.suffix.lower() in (".docx", ".md", ".txt")
             and (not client or "client report" in f.name.lower())]
    seen = set()
    for f in sorted(files, key=lambda f: f.name, reverse=True):
        try:
            if f.suffix.lower() == ".docx":
                text = "\n".join(docx_tools.story_text(docx_tools.accept_xml(raw.decode("utf-8"))[0])
                                 for info, raw in docx_tools.read_parts(f) if info.filename == "word/document.xml")
            else:
                text = f.read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001  a corrupt, locked or half-synced file is skipped: numbers are a help, never a blocker
            continue
        for line in re.split(r"[\n]+|(?<=[.!?])\s+", text):
            line = " ".join(line.split()).lstrip("-•* ")
            if 12 <= len(line) <= 220 and FIGURE.search(line) and line.lower() not in seen:
                seen.add(line.lower())
                part.add(f"{line}", paths.rel(f))
                if len(part.lines) >= 5:
                    return part
    return part


def trend_part(code, end):
    """The Trend part (internal only): the project's flow line from the dashboard; empty if it can't be worked out."""
    part = Part("trend")
    try:
        line = build_dashboard.flow_line(code, date.fromisoformat(end))
    except Exception:  # noqa: BLE001  the trend is a help, never a blocker
        line = ""
    if line:
        part.add(line)
    return part


def facts(code, start=None, end=None, audience="internal"):
    """The ranked facts sheet for one project and period: {"parts": [...], "asks", "sources", "has_figures", "text", …}."""
    if audience not in ("internal", "client"):
        raise ValueError("audience must be internal or client")
    client = audience == "client"
    con = tracker.connect()
    p, folder, mem = report.project(con, code)
    end = end or report.today().isoformat()
    start = start or (date.fromisoformat(end) - timedelta(days=7)).isoformat()
    asks = []
    parts = [position_part(con, p, code, start, end, client), movement_part(con, p, code, start, end, client),
             exposure_part(con, p, code, start, end, client), asks_part(con, p, code, start, end, client, asks),
             numbers_part(code, start, end, client)]
    if not client:
        parts.append(trend_part(code, end))
    parts = [x for x in parts if x.lines]
    # ===== BL-207 (sprint-insight) =====  fact IDs, in the sheet's order
    parts = [x.as_dict() for x in parts]
    n = 0
    for part in parts:
        for ln in part["lines"]:
            n += 1
            ln["fid"] = f"F{n}"
    sources = list(dict.fromkeys(s for x in parts for ln in x["lines"] for s in ln["src"]))
    out = {"code": code, "name": p["name"], "audience": audience, "start": start, "end": end, "health": p["health"],
           "parts": parts, "asks": asks, "sources": sources,
           "has_figures": any(re.search(r"\d", ln["text"]) for x in parts for ln in x["lines"])}
    out["text"] = render(out)
    return out


def render(f):
    """The facts sheet as the text the model is given: a header, then each part's lines with their fact IDs and sources (BL-207)."""
    lines = [f"Facts for {f['code']} {f['name']}, {tracker.shown(f['start'])} to {tracker.shown(f['end'])}, {f['audience']} audience.",
             "Ranked by what matters most. Write the status from these; any other material is reference only."]
    for part in f["parts"]:
        lines += ["", f"## {part['title']}"]
        lines += [f"- [{ln['fid']}] {ln['text']}" + (f" [src: {', '.join(ln['src'])}]" if ln["src"] else "") for ln in part["lines"]]
    return "\n".join(lines)


def main(argv):
    """The command line: facts <CODE> [--from] [--to] [--audience] [--json] prints the sheet. Writes nothing."""
    if len(argv) < 2 or argv[0] != "facts":
        print(__doc__)
        return 2
    code, rest = argv[1], [a for a in argv[2:] if a != "--json"]
    opts = dict(zip(rest[::2], rest[1::2]))
    try:
        with contextlib.redirect_stdout(sys.stderr):        # library notes ("image not found…") must not mix into the output
            f = facts(code, opts.get("--from"), opts.get("--to"), opts.get("--audience", "internal"))
    except ValueError as e:
        print(e)
        return 2
    print(json.dumps(f, indent=1) if "--json" in argv else f["text"])
    return 0


# ===== BL-227 (sprint-drafts-writing) ===== two more audiences for the same sheet: the steering committee and the sponsor. Both get
# the internal sheet's wording with nothing sensitive in it: a line is dropped when its text, or an item it rests on, is marked
# confidential or restricted, carries a label that keeps it out of client output, or is a "Client-safe: no" memory line. The
# remaining lines are numbered again in order, so the IDs stay deterministic for the same period and audience.
AUDIENCES = ("internal", "client", "steering", "sponsor")
SENSITIVE = re.compile(r"\b(confidential|restricted)\b|client-safe:\s*no", re.I)


def sensitive_ids(con, ids):
    """The item IDs among `ids` that must stay out of a steering or sponsor sheet."""
    out = set()
    for i in ids:
        table = tracker.item_table(i) if ID_RE.fullmatch(i) else None
        if table not in ("actions", "raid", "decisions"):
            continue
        row = con.execute(f"SELECT * FROM {table} WHERE id = ?", (i,)).fetchone()
        text = " ".join(str(v) for v in (dict(row) if row else {}).values() if isinstance(v, str))
        if SENSITIVE.search(text) or _excluded(con, i):
            out.add(i)
    return out


def _excluded(con, item_id):
    import sqlite3
    try:
        return bool(con.execute("SELECT 1 FROM item_labels il JOIN labels l ON l.name = il.label WHERE il.item_id = ? AND "
                                "(l.behaviour = 'exclude' OR l.default_choice = 'exclude') LIMIT 1", (item_id,)).fetchone())
    except sqlite3.Error:
        return False          # no labels tables: nothing is labelled out


_facts_before_audiences = facts


def facts(code, start=None, end=None, audience="internal"):  # noqa: F811  BL-227: the steering and sponsor audiences, then the sheet
    """The ranked facts sheet; "steering" and "sponsor" are the internal sheet with every sensitive line left out."""
    if audience not in ("steering", "sponsor"):
        return _facts_before_audiences(code, start, end, audience)
    f = _facts_before_audiences(code, start, end, "internal")
    con = tracker.connect()
    try:
        bad = sensitive_ids(con, {i for x in f["parts"] for ln in x["lines"] for i in ln["src"]})
    finally:
        con.close()
    f = without_sensitive(f, bad)
    f["audience"] = audience
    f["text"] = render(f)
    return f


def without_sensitive(f, bad):
    """The sheet with every line and ask that is sensitive, or rests on an item in `bad`, left out; the lines numbered again."""
    n = 0
    for part in f["parts"]:
        part["lines"] = [ln for ln in part["lines"] if not SENSITIVE.search(ln["text"]) and not bad & set(ln["src"])]
        for ln in part["lines"]:
            n += 1
            ln["fid"] = f"F{n}"
    f["parts"] = [x for x in f["parts"] if x["lines"]]
    f["sources"] = list(dict.fromkeys(s for x in f["parts"] for ln in x["lines"] for s in ln["src"]))
    f["asks"] = [a for a in f["asks"] if a.get("id") not in bad and not SENSITIVE.search(a.get("text") or "")]
    return f
# ===== end BL-227 =====


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
