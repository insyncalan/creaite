"""creaite extraction helpers (sprint-drafts-extraction): plain code that cx-minutes and cx-sweep run when they stage a proposal.

- BL-221 "Looks like": a new proposal that repeats an item already in the tracker is marked (`looks_like`) for Review, which offers
  Compare, Merge as an update, Keep as new and Reject as a duplicate.
- BL-218 "Probably done": which messages or meeting passages may show that an open item is finished (candidates the skill judges),
  and the checks a closing update passes before it is staged.
- BL-220 Sharpen on capture: the vague-title test that marks a new action as shaky in Review and offers Sharpen.

Nothing here writes to the tracker. It marks proposals in system/staging/ (a suggestion each), which Alan approves in Review, and it
counts each kind of suggestion in system/staging/draft-stats.json (counts only, through drafts.record).
Library only: cx-minutes and cx-sweep reach it through minutes.py and sweep.py. Set CREAITE_NOW="YYYY-MM-DD HH:MM" to fix the clock.
"""
import json
import os
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
import tracker  # noqa: E402

STOP = {"a", "an", "the", "and", "or", "of", "to", "for", "on", "in", "at", "by", "with", "from", "is", "be", "are", "it", "its",
        "this", "that", "we", "our", "you", "your", "they", "their", "as", "up", "out", "into", "about", "re", "fw", "please",
        "will", "can", "should", "need", "needs"}


def today():
    """Today as YYYY-MM-DD (CREAITE_NOW fixes it in tests)."""
    fixed = os.environ.get("CREAITE_NOW")
    return fixed[:10] if fixed else date.today().isoformat()


def tokens(text):
    """An item's words, compared loosely: lower case, stop words out, a plural's s dropped (as Review's duplicate hint does)."""
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {w[:-1] if len(w) > 3 and w.endswith("s") else w for w in words if w not in STOP and len(w) > 1}


def overlap(a, b):
    """Shared words over the longer text's words, 0 to 1. Plain code, no model."""
    return len(a & b) / max(len(a), len(b)) if a and b else 0.0


def count(feature, event, n=1):
    """Count a suggestion in draft-stats.json (counts only). A count never stops staging or a decision."""
    try:
        import drafts
        drafts.record(feature, event, n)
    except (ImportError, ValueError, OSError):  # counting is best effort: the proposal matters, the count does not
        return


def switched_on(feature):
    """settings.json `drafting.<feature>` (on when missing): the switch in Settings › General › AI drafts."""
    return (paths.load_settings().get("drafting") or {}).get(feature, True) is not False


# ===== BL-221 (sprint-drafts-extraction) ===== "Looks like": a new proposal that repeats an existing item. At staging each new
# action, RAID item or decision is compared, by token overlap over its title with small weights for the same owner and workstream,
# with its project's items (open first, then closed in the last RECENT_DAYS) and with other projects' open items that have the
# same owner. The closest pair over POSSIBLE is marked on the item as `looks_like` {id, t, state, same, project, strength, why}:
# "Very likely" or "Possible", never a percentage (BL-233's rule). The skill judges a close pair it can see (`repeat`: {id,
# judged: "same" | "different"} on the spec item): "different" drops the mark, "same" makes it Very likely. Review then offers
# Compare, Merge as an update (review.py merge), Keep as new (review.py keep-new) and Reject as a duplicate (BL-133).
VERY, POSSIBLE, RECENT_DAYS = 0.75, 0.5, 60
TEXT = {"actions": "description", "raid": "description", "decisions": "decision"}
OWNER = {"actions": "owner", "raid": "owner", "decisions": "made_by"}
OPEN = {"actions": ("Open", "Delayed"), "raid": ("Open",), "decisions": ("Pending",)}
RAISED = {"actions": "raised", "raid": "raised", "decisions": "NULL"}          # BL-297: a decision has no raised date
DUE = {"actions": "due_date", "raid": "due_date", "decisions": "needed_by"}


def known_owner(name):
    """A real owner (not empty or TBC), compared loosely."""
    n = " ".join(str(name or "").lower().split())
    return "" if n in ("", "tbc", "unassigned") else n


def candidate_rows(con, table, project, owner):
    """The items a new one may repeat: its project's open items, its project's recently closed ones, and other projects' open
    items with the same owner. Each row: id, project, text, owner, workstream, status, state ("open" or "closed")."""
    since = (date.fromisoformat(today()) - timedelta(days=RECENT_DAYS)).isoformat()
    ws = "workstream" if table != "decisions" else "''"
    closed = "closed" if table != "decisions" else "date"
    sql = (f"SELECT id, project, {TEXT[table]} AS text, {OWNER[table]} AS owner, {ws} AS workstream, status, {closed} AS closed, "
           f"{RAISED[table]} AS raised, {DUE[table]} AS due, source FROM {table} WHERE project = ? OR {OWNER[table]} = ?")
    out = []
    for r in con.execute(sql, (project, owner or "\x00")):
        r = dict(r)
        r["state"] = "open" if r["status"] in OPEN[table] else "closed"
        if r["project"] != project and (r["state"] != "open" or not known_owner(owner)):
            continue
        if r["state"] == "closed" and (r["status"] in ("Cancelled", "Withdrawn") or (r["closed"] or "") < since):
            continue
        out.append(r)
    return out


def repeat_score(values, table, row):
    """How closely a proposed item repeats an existing one, 0 to 1: the title's word overlap, a little more for the same owner and
    workstream, a little less when both owners are known and differ."""
    s = overlap(tokens(values.get(TEXT[table])), tokens(row["text"]))
    mine, theirs = known_owner(values.get(OWNER[table])), known_owner(row["owner"])
    if mine and theirs:
        s += 0.1 if mine == theirs else -0.1
    if values.get("workstream") and values.get("workstream") == row.get("workstream"):
        s += 0.05
    return max(0.0, min(1.0, s))


def best_repeat(con, item, register=None):
    """The existing item a new proposal most likely repeats, as a `looks_like` mark, or None. BL-297: the words and owner of BL-221,
    plus the signals (an ID named, the same thread, a person in both, a less common word, the item's timeframe); never an item
    raised after the message or meeting."""
    table, v = item.get("table"), item.get("values") or {}
    if item.get("op") != "new" or table not in TEXT or not v.get("project") or not tokens(v.get(TEXT[table])):
        return None
    ctx = message_context(item, register)
    rows = [r for r in candidate_rows(con, table, v["project"], v.get(OWNER[table])) if not raised_after(r, ctx["day"])]
    best, rare = None, rare_words(rows)
    for r in rows:
        same = r["project"] == v["project"]
        s, why = match_score(v, table, r, ctx, rare)
        s -= 0.0 if same or s >= 1.0 else 0.1                         # across projects only a close match with the same owner
        rank = (s, same, r["state"] == "open")
        if s >= POSSIBLE and (best is None or rank > best[0]):
            best = (rank, r, s, why)
    if not best:
        return None
    _, r, s, why = best
    return {"id": r["id"], "t": r["text"], "state": r["state"], "same": r["project"] == v["project"], "project": r["project"],
            "strength": "Very likely" if s >= VERY else "Possible", "why": why}


def judged(mark, raw, con=None, item=None, notes=None):
    """The skill's judgement of a pair (`repeat` on the spec item) applied to the mark: "different" drops it, "same" makes it Very
    likely. BL-297: "same" stands on its own, on an item plain code didn't mark (judged_mark checks the ID first)."""
    j = (raw or {}).get("repeat") if isinstance(raw, dict) else None
    if not isinstance(j, dict):
        return mark
    if mark and j.get("id") == mark["id"]:
        if j.get("judged") == "different":
            return None
        return {**mark, "strength": "Very likely", "why": "Judged the same at extraction"} if j.get("judged") == "same" else mark
    if j.get("judged") == "same" and con is not None and item is not None:
        return judged_mark(con, item, str(j.get("id") or ""), notes) or mark
    return mark


def spec_raw_for(spec, item):
    """The spec item a staged new item came from (matched by its title), for the skill's judgement."""
    t = (item.get("values") or {}).get(TEXT.get(item.get("table"), "description"))
    for raw in (spec or {}).get("items") or []:
        v = raw.get("values") or {} if isinstance(raw, dict) else {}
        if raw.get("table") == item.get("table") and v.get(TEXT.get(raw.get("table"), "description")) == t:
            return raw
    return None


def mark_repeats(con, data, spec, notes=None):
    """Mark each new item that looks like an existing one. Returns how many were marked; a judgement that can't stand is noted."""
    if not switched_on("repeat"):
        return 0
    n, register = 0, people()
    for item in data.get("items") or []:
        mark = judged(best_repeat(con, item, register), spec_raw_for(spec, item), con, item, notes)
        if mark:
            item["looks_like"] = mark
            n += 1
    return n


def merge_changes(item, row):
    """What a repeat carries to the item it repeats (BL-221's Merge): a new date, latest update or response, and for a pending
    decision its being made. Empty when it brings nothing new."""
    table, v = item["table"], item.get("values") or {}
    want = {"actions": ("due_date", "latest_update"), "raid": ("due_date", "response_action"),
            "decisions": ("reasoning", "options")}[table]
    out = {f: v[f] for f in want if v.get(f) and v[f] != row.get(f)}
    if table == "decisions" and row.get("status") == "Pending" and v.get("status") == "Made":
        out.update(status="Made", date=v.get("date") or today())
    return out


def merged_item(item, row):
    """The proposal item as an `update` to the item it repeats, or None when the repeat brings nothing new."""
    changes = merge_changes(item, row)
    if not changes:
        return None
    v = item.get("values") or {}
    return {"n": item["n"], "op": "update", "table": item["table"], "id": row["id"], "changes": changes, "based_on": row["updated_at"],
            "why": f"Merged: raised again as “{v.get(TEXT[item['table']]) or ''}”", "source": v.get("source") or "",
            "match": "strong", "flags": [], "decision": "pending", "merged_from": {"values": v},
            "looks_like": {**(item.get("looks_like") or {}), "merged": True},
            "was": {k: x for k, x in item.items() if k != "was"}}          # BL-297: review.py unmerge puts it back
# ===== end BL-221 =====


# ===== BL-218 (sprint-drafts-extraction) ===== "Probably done": an open item finished without anyone telling creaite. Plain code first:
# done_candidates (mail and Teams, from the sweep) and passage_candidates (a meeting's transcript) find the open items a message or
# passage may close (its ID in the text, most of its key words, an attachment named like it, the owner as sender or recipient, a
# completion word, sent after the item was raised). The skill (the model) judges only those, and writes an `update` with a `done`
# block; done_check holds the rules (the item's own project, open, raised before; the sender is the owner or Alan, or the passage
# names the owner) and the strength: "Looks done" (an explicit completion statement naming the thing, strongest from Sent Items) or
# "Maybe done" (shown with its reason); Teams counts a little less than mail (Looks done only when it names the item's ID). Evidence
# that it is not done or has moved is "Not done": a re-dating update. Never closes anything: a closing update is approved on its own.
# BL-125 A, decision 10 (Alan, 13-10-2026): open promises are scanned too, by the same rules and thresholds. A promise's "owner" is
# the person who made it (promised_by); a kept one becomes Done (a promise has no latest update). From the sweep only while
# promises.from_sweep is on, as for every promise the sweep proposes.
COMPLETE = re.compile(r"\b(done|completed?|finished|sent|attached|here(?:'s| is| are)|delivered|signed|approved|submitted|"
                      r"shared|uploaded|resolved|fixed|closed|booked|confirmed|agreed|published|merged|released|live)\b", re.I)
MOVED = re.compile(r"\b(delay(?:ed)?|postpone[ds]?|pushed|slipp(?:ed|ing)|moved to|not yet|still waiting|next week|reschedul\w*)\b", re.I)
STRENGTHS = ("Looks done", "Maybe done", "Not done")
ITEM_ID = re.compile(r"\b[A-Z][A-Z0-9]{2,6}-(?:[A-Z]-)?\d{3}\b")


def open_items(con, project=None, promises=True):
    """Open actions, RAID items and (with `promises`) promises, of all projects or one: id, table, project, text, owner (a
    promise's promised_by), raised, due_date."""
    out = []
    tables = (("actions", ("Open", "Delayed"), "owner"), ("raid", ("Open",), "owner")) + \
        ((("promises", ("Open",), "promised_by"),) if promises else ())
    for table, states, owner in tables:
        q = (f"SELECT id, project, description AS text, {owner} AS owner, raised, due_date FROM {table} "
             f"WHERE status IN ({','.join('?' * len(states))})")
        args = list(states)
        if project:
            q, args = q + " AND project = ?", args + [project]
        out += [{**dict(r), "table": table} for r in con.execute(q, args)]
    return out


def people():
    """The people register: [{name, emails, aliases}] (empty when there is none)."""
    try:
        import propose
        return [{"name": p["name"], "emails": propose.person_emails(p), "aliases": p["aliases"]}
                for p in propose.people_parse(propose.people_register_text()[0])]
    except (ImportError, OSError, ValueError, KeyError):      # no register yet: names are compared as written
        return []


def is_person(text, name, register=None):
    """Whether text (a sender, recipient or passage) names this person: their name, an alias or an address from the register."""
    t, n = str(text or "").lower(), " ".join(str(name or "").lower().split())
    if not t or not known_owner(n):
        return False
    p = next((x for x in register or [] if x["name"].lower() == n), None)
    names = [n] + [a.lower() for a in (p or {}).get("aliases") or []] + list((p or {}).get("emails") or [])
    return any(re.search(rf"(?<![\w@.]){re.escape(x)}(?![\w@])", t) for x in names if len(x) > 2)


def is_alan(sender, folder=""):
    """Whether Alan sent it: Sent Items, or his name or a short form from settings.json `identity`."""
    if str(folder).lower() in ("sent", "sent items"):
        return True
    ident = paths.load_settings().get("identity") or {}
    return any(is_person(sender, n) for n in [ident.get("name") or ""] + list(ident.get("short_forms") or []) if len(n) > 2)


def item_hits(item, text, attachments=()):
    """(score, reasons) for one open item against a message or passage. Plain code, no model."""
    mine, said = tokens(item["text"]), tokens(text)
    reasons, score = [], 0.0
    if item["id"] in (text or ""):
        score, reasons = score + 1.0, reasons + ["names its ID"]
    share = len(mine & said) / len(mine) if len(mine) >= 2 else 0.0
    if share >= 0.6:
        score, reasons = score + share, reasons + ["most of its key words"]
    if any(overlap(mine, tokens(a)) >= 0.5 or len(mine & tokens(a)) >= 2 for a in attachments or ()):
        score, reasons = score + 0.5, reasons + ["an attachment named like it"]
    return score, reasons


def hint(item, text, reasons, strong_source):
    """The strength plain code suggests for a candidate; the skill judges it."""
    if not COMPLETE.search(text or ""):
        return "Not done" if MOVED.search(text or "") else None
    named = "names its ID" in reasons or "an attachment named like it" in reasons or "most of its key words" in reasons
    return "Looks done" if named and strong_source else "Maybe done"


def message_candidates(msg, items, register):
    """The open items one message may close, best first (at most three)."""
    found = (candidate(it, msg, register) for it in items)
    return sorted((c for c in found if c), key=lambda c: -c["score"])[:3]


def candidate(it, msg, register):
    """One open item against one message: the candidate with its hint and reasons, or None."""
    text, sent = str(msg.get("text") or ""), str(msg.get("sent") or "")[:10]
    sender = str(msg.get("from") or "")
    if sent and (it.get("raised") or "") > sent:
        return None                                     # raised after the message: it can't be what the message finished
    score, reasons = item_hits(it, text, msg.get("attachments") or ())
    if score < 0.6:
        return None
    score, reasons = owner_hits(it, sender, " ".join(msg.get("to") or []), register, score, reasons)
    h = hint(it, text, reasons, strong_source(msg, sender, reasons))
    return {"id": it["id"], "table": it["table"], "project": it["project"], "title": it["text"], "owner": it["owner"],
            "hint": h, "reasons": reasons, "score": round(score, 2)} if h else None


def strong_source(msg, sender, reasons):
    """Whether a message is strong evidence: Alan or the owner sent it (Sent Items is Alan's), and a Teams message names the ID."""
    teams = str(msg.get("source") or "").startswith("Teams")
    return (is_alan(sender, msg.get("folder") or "") or "the owner sent it" in reasons) and (not teams or "names its ID" in reasons)


def owner_hits(it, sender, to, register, score, reasons):
    """A little more for an item whose owner sent the message, or received it."""
    if is_person(sender, it["owner"], register):
        return score + 0.3, reasons + ["the owner sent it"]
    if is_person(to, it["owner"], register):
        return score + 0.2, reasons + ["sent to the owner"]
    return score, reasons


def done_candidates(con, messages):
    """For each message the sweep found ({source, folder, from, to, sent, text, attachments}), the open items it may close."""
    if not switched_on("done"):
        return []
    from_sweep = bool((paths.load_settings().get("promises") or {}).get("from_sweep", False))    # BL-125 A: off by default
    items, register, out = open_items(con, promises=from_sweep), people(), []
    for i, msg in enumerate(messages if isinstance(messages, list) else []):
        found = message_candidates(msg, items, register) if isinstance(msg, dict) else []
        if found:
            out.append({"message": i, "source": msg.get("source") or "", "candidates": found})
    return out


def passage_candidates(con, code, text):
    """A meeting's passages (speaker turns) that may close one of the project's open items: {id, hint, reasons, speaker, quote}."""
    if not switched_on("done"):
        return []
    items, register, out = open_items(con, code), people(), []
    for n, line in enumerate((text or "").splitlines(), 1):
        who, _, said = line.partition(": ") if ": " in line[:60] else ("", "", line)
        for it in items:
            score, reasons = item_hits(it, said)
            if score < 0.6:
                continue
            by_owner = is_person(who, it["owner"], register) or is_person(said, it["owner"], register)
            h = hint(it, said, reasons, by_owner or is_alan(who))
            if h:
                out.append({"id": it["id"], "table": it["table"], "title": it["text"], "owner": it["owner"], "hint": h,
                            "reasons": reasons, "line": n,
                            "speaker": who, "quote": said[:300]})
    return out


def evidence_line(ev):
    """ "Mail sent 09-10-2026 15:02 by Sara Example: “attached the SOW”" from an evidence block."""
    at = str(ev.get("at") or "")
    when = f"{tracker.shown(at[:10])}{' ' + at[11:16] if len(at) >= 16 else ''}" if at else ""
    kind = {"mail": "Mail", "teams": "Teams message", "meeting": "Said in the meeting"}.get(ev.get("kind"), "Message")
    who = f" by {ev['who']}" if ev.get("who") else ""
    if ev.get("said") and not ev.get("quote"):                  # BL-342: creaite's own words for a thread, so no quotation marks
        return f"{kind}{' ' + when if when else ''}{who}: {str(ev['said']).strip()[:240]}"
    return f"{kind}{' ' + when if when else ''}{who}: “{str(ev.get('quote') or '').strip()[:240]}”"


def owner_of(row):
    """Whose item it is for the owner rule: its owner, or the person who made a promise."""
    return row.get("owner") or row.get("promised_by") or ""


def done_check(row, done, source, sender, register=None):
    """(strength, None) when a "probably done" update may be staged, else (None, why not). row: the open item."""
    row = {**row, "owner": owner_of(row)}
    strength, quote = done.get("strength"), str(done.get("quote") or "")
    if strength not in STRENGTHS or not quote.strip():
        return None, "a done update needs a strength (Looks done, Maybe done or Not done) and the quote it rests on"
    if done.get("project") and done["project"] != row["project"]:
        return None, f"{row['id']} belongs to {row['project']}, not {done['project']}: only the item's own project"
    sent = str(done.get("at") or "")[:10]
    if sent and (row.get("raised") or "") > sent:
        return None, f"{row['id']} was raised after the message"
    if not said_by_owner_or_alan(row, sender, quote, done.get("folder"), register):
        return None, f"{row['id']}: the message isn't from its owner or Alan and doesn't name the owner"
    teams_only = strength == "Looks done" and str(source).startswith("Teams") and row["id"] not in quote
    return ("Maybe done" if teams_only else strength), None           # Teams chat counts a little less than mail


def said_by_owner_or_alan(row, sender, quote, folder, register=None):
    """The rule for closing an item: the owner or Alan said it, or the words name the owner."""
    return is_person(sender, row["owner"], register) or is_alan(sender, folder) or is_person(quote, row["owner"], register)


def done_changes(table, done, kind):
    """What a done update changes: closed (status Closed, a promise Done; an action also gets a latest update quoting the
    evidence), or, for "Not done", the new due date only."""
    if done["strength"] == "Not done":
        return {"due_date": done["due_date"]} if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(done.get("due_date") or "")) else {}
    out = {"status": "Done" if table == "promises" else "Closed"}                 # BL-125 A: a promise is kept, not closed
    if table == "actions":
        out["latest_update"] = f"Done: {evidence_line({**done, 'kind': kind})}"[:500]
    return out


def done_mark(done, source, kind):
    """The `suggested` block a done update carries to Review (counted as the "done" feature)."""
    ev = {"kind": kind, "at": str(done.get("at") or "")[:16], "who": str(done.get("who") or "")[:80],
          "quote": str(done.get("quote") or "").strip()[:300], "source": str(source)[:500]}
    return {"feature": "done", "strength": done["strength"], "reason": str(done.get("reason") or "")[:200], "evidence": ev}


def mark_done(data, spec):
    """Minutes: give each closing update the meeting proposed with a `done` block its evidence and strength. A passage not said by
    the owner or Alan and not naming the owner is only "Maybe done". Returns how many were marked."""
    if not switched_on("done"):
        return 0
    wanted = done_specs(spec)
    n, day = 0, (data.get("meeting") or {}).get("date") or ""
    for it in data.get("items") or []:
        raw = wanted.get(str(it.get("id"))) if it.get("op") == "update" else None
        if raw and not it.get("suggested") and it.get("table") in ("actions", "raid", "promises"):
            mark_meeting_update(it, {**raw["done"], "at": raw["done"].get("at") or day})
            n += 1
    return n


def done_specs(spec):
    """The spec's updates that carry a `done` block, by item ID."""
    return {str(r.get("id")): r for r in (spec or {}).get("items") or [] if isinstance(r, dict) and r.get("op") == "update"
            and isinstance(r.get("done"), dict)}


def mark_meeting_update(it, done):
    """One meeting update's `suggested` mark: its evidence, and its strength after the owner rule."""
    con = tracker.connect()
    row = tracker.fetch(con, it["table"], it["id"])
    con.close()
    strength, why = done_check(dict(row), {**done, "strength": done.get("strength") or "Maybe done"}, "", done.get("who") or "")
    mark = done_mark({**done, "strength": strength or "Maybe done"}, it.get("source") or "", "meeting")
    if why:
        mark["reason"] = "Not said by the owner or Alan, and the passage doesn't name the owner"
    it["suggested"] = mark
    it["why"] = f"{mark['strength']}: {evidence_line(mark['evidence'])}"
# ===== end BL-218 =====


# ===== BL-220 (sprint-drafts-extraction) ===== Sharpen on capture. The vague-title test is plain code (the model is asked only when it
# fails): a title of under four words, or with no verb, is vague ("look into data", "the data thing"). At staging a new action with
# a vague title is marked as shaky (BL-208's `inferred`, field description, with why), so Review puts it first and offers Sharpen
# (drafts.py kind "sharpen"). The page's chips (Owner, Due, Workstream, Milestone, Priority) are plain code in the page.
VERBS = set("""
accept add agree align allocate amend analyse analyze appoint approve arrange ask assess assign attend audit book brief build buy
call cancel capture chase check circulate clarify close collect complete confirm consolidate contact create decide define deliver
deploy design develop discuss document draft email engage ensure escalate estimate evaluate examine explore extend finalise
finalize find fix follow forward gather get give hand hire hold identify implement improve inform install integrate investigate
invite issue launch lead list look make manage map meet merge migrate monitor move negotiate notify obtain onboard organise
organize outline pay plan prepare present prioritise prioritize produce provide publish raise reach read receive reconcile record
reduce refine register release remind remove renew replace reply report request research reschedule resolve respond restart
review revise run schedule scope secure select send set share sign source specify start submit summarise summarize supply
support test track train transfer update upgrade upload validate verify visit write
""".split())


def vague(title):
    """Why a title is vague ("under four words" or "no verb"), or None when it is clear. Plain code, no model."""
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", title or "")
    if len(words) < 4:
        return "under four words"
    if not any(w.lower().rstrip("s") in VERBS or w.lower() in VERBS for w in words):
        return "no verb"
    return None


def mark_vague(data):
    """Mark each new action with a vague title as shaky (BL-208's `inferred`) for Review. Returns how many."""
    n = 0
    for it in data.get("items") or []:
        why = vague((it.get("values") or {}).get("description")) if it.get("op") == "new" and it.get("table") == "actions" else None
        if why and not any(x.get("field") == "description" for x in it.get("inferred") or []):
            it.setdefault("inferred", []).append({"field": "description", "why": f"Vague title ({why}): Sharpen offers a clearer one"})
            n += 1
    return n
# ===== end BL-220 =====


def after_stage(out, spec):
    """Mark a freshly staged proposal (BL-221, BL-218, BL-220), count what was offered, then validate it as staging always has.
    Returns tracker.py validate's exit code."""
    out = Path(out)
    try:
        data = json.loads(out.read_text(encoding="utf-8"))
        con = tracker.connect()
        notes = []
        try:
            marked = mark_repeats(con, data, spec, notes)
        finally:
            con.close()
        for note in notes:                                                              # BL-297: a judgement that didn't stand
            print(f"Note: {note}")
        mark_done(data, spec)                                                           # BL-218: a meeting's closing updates
        mark_vague(data)                                                                # BL-220: a vague action is shaky
        out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        report_marks(data, marked)
    except (OSError, ValueError) as e:     # marking is an extra: the proposal stands as staged, and validate still runs
        print(f"Note: the proposal wasn't checked for repeats ({type(e).__name__})")
    return tracker.main(["validate", str(out)])


def report_marks(data, repeats):
    """Count what staging offered (repeats, probably done) and say so in one line each."""
    done = sum(1 for i in data.get("items") or [] if (i.get("suggested") or {}).get("feature") == "done")
    if repeats:
        count("repeat", "offered", repeats)
        print(f"Looks like an existing item: {repeats} (marked for Review)")
    if done:
        count("done", "offered", done)
        print(f"Probably done: {done} (each closing update is approved on its own)")


def count_decision(item, decision):
    """Count what Alan decided about a suggestion: a repeat rejected as its duplicate is used (merge and keep are counted when
    chosen); a probably-done update approved as proposed is used, after an edit edited, rejected rejected."""
    ll = item.get("looks_like") or {}
    if ll and decision == "rejected" and item.get("duplicate_of") == ll.get("id"):
        count("repeat", "used")
    sg = item.get("suggested") or {}
    if (sg.get("feature") == "done" or sg.get("done")) and decision in ("approved", "rejected"):   # BL-342: a thread's close too
        count("done", "rejected" if decision == "rejected" else "edited" if item.get("as_proposed") else "used")


# ===== BL-297 (sprint-smart-updates) ===== Smarter updates: the signals that tie a message or meeting to an item already open, used by
# Looks like (best_repeat), by the expected list the sweep reads (rank_open) and by Review's picker (review.py candidates). Plain code:
#   1. the item's ID in the text (the title, the latest update or the subject) is a certain match;
#   2. the project: its own items only, another project's only with the same owner (candidate_rows, as BL-221);
#   3. the timeframe: never an item raised after the message (or meeting); a little more for one whose window (raised to due, 14 days
#      either side; an open item overdue counts as current) covers the message's day, a little less for one due long after it;
#   4. the same thread: the item's stored source subject, normalised (no Re:, Fw:, [EXT], case or spacing), equals the message's;
#   5. a person from the people register (name or alias) in both texts, and a less common word in both, count for more.
# The mark keeps its two strengths (Very likely from VERY, Possible from POSSIBLE; never a percentage) and its `why` names the signals
# ("Same thread · Dana · due this week"). The skill's `repeat: same` stands on its own (judged_mark).
W_THREAD, W_PERSON, W_RARE, RARE_CAP, W_WINDOW, W_LONG = 0.35, 0.15, 0.1, 0.2, 0.1, -0.1
WINDOW_DAYS, LONG_AFTER_DAYS = 14, 60
SUBJECT = re.compile(r"Subject: (.*?)(?: · |$)")
REPLY = re.compile(r"^\s*(?:(?:re|fw|fwd)\s*:|\[ext(?:ernal)?\])\s*", re.I)


def subject_of(source):
    """The Subject of a structured Email source, as written ("" for anything else)."""
    m = SUBJECT.search(str(source or "")) if str(source or "").startswith("Email") else None
    return m.group(1).strip() if m else ""


def thread_of(source):
    """A mail thread's key: the subject without Re:, Fw:, Fwd: or [EXT] in front, in lower case with single spaces."""
    s = subject_of(source)
    while REPLY.match(s):
        s = REPLY.sub("", s, count=1)
    return " ".join(s.lower().split())


def message_day(v):
    """The day a new item was said: its source's Sent day, else its raised (a meeting's day) or date, else today."""
    m = re.search(r"Sent: (\d{4}-\d{2}-\d{2})", str(v.get("source") or ""))
    return m.group(1) if m else str(v.get("raised") or v.get("date") or today())[:10]


def message_context(item, register=None):
    """What a new item's message says about where it belongs: its day, thread, the IDs it names, its words and the people in it."""
    v = item.get("values") or {}
    text = " ".join(str(v.get(f) or "") for f in ("description", "decision", "latest_update", "response_action"))
    text += " " + subject_of(v.get("source"))
    return {"day": message_day(v), "thread": thread_of(v.get("source")), "ids": set(ITEM_ID.findall(text)), "text": text,
            "register": register if register is not None else people()}


def raised_after(row, day):
    """Whether an item was raised after the message's day (it can't be what the message speaks of)."""
    return bool(row.get("raised") and day and row["raised"] > day)


def rare_words(rows):
    """The words that appear in only one of the candidates (four letters or more): less common, so a shared one counts for more."""
    seen = {}
    for r in rows:
        for w in tokens(r["text"]):
            seen[w] = seen.get(w, 0) + 1
    return {w for w, n in seen.items() if n == 1 and len(w) >= 4}


def people_in(a, b, register):
    """The people from the register named (by name or alias) in both texts: their first names."""
    return [p["name"].split()[0] for p in register or [] if is_person(a, p["name"], register) and is_person(b, p["name"], register)]


def time_signal(row, day):
    """(weight, words) for the item's timeframe against the message's day."""
    if not day or not row.get("raised"):
        return 0.0, None
    d, due = date.fromisoformat(day), row.get("due")
    if due and (date.fromisoformat(due) - d).days > LONG_AFTER_DAYS:
        return W_LONG, None
    end = row.get("closed") if row.get("state") == "closed" else None          # open: overdue still counts as current
    if end and (d - date.fromisoformat(str(end)[:10])).days > WINDOW_DAYS:
        return 0.0, None
    if not due:
        return W_WINDOW, "in its window"
    return W_WINDOW, "overdue" if due < day else "due this week" if (date.fromisoformat(due) - d).days <= 7 else "in its window"


def thread_signal(row, ctx):
    """(weight, words) when the item came from the same mail thread as the message."""
    return (W_THREAD, "Same thread") if ctx["thread"] and thread_of(row.get("source")) == ctx["thread"] else (0.0, None)


def word_signal(v, table, row, rare):
    """(BL-221's score: words, owner and workstream, plus the less common words both share; its words)."""
    s = repeat_score(v, table, row)
    shared = tokens(v.get(TEXT[table])) & tokens(row["text"])
    s += min(RARE_CAP, W_RARE * len(shared & rare))
    mine, theirs = known_owner(v.get(OWNER[table])), known_owner(row["owner"])
    words = "Same owner" if mine and mine == theirs else None
    return s, ([words] if words else []) + (["Similar words"] if overlap(tokens(v.get(TEXT[table])), tokens(row["text"])) >= 0.3 else [])


def match_score(v, table, row, ctx, rare):
    """(score 0 to 1, why) for one candidate against a new item and its message: the five signals together."""
    if row["id"] in ctx["ids"]:
        return 1.0, f"Names {row['id']}"
    s, why = word_signal(v, table, row, rare)
    t, tw = thread_signal(row, ctx)
    names = people_in(ctx["text"], row["text"], ctx["register"])
    w, ww = time_signal(row, ctx["day"])
    s += t + (W_PERSON if names else 0.0) + w
    parts = [x for x in [tw] + names[:2] + why + [ww] if x]
    return max(0.0, min(1.0, s)), " · ".join(dict.fromkeys(parts)) or "Similar words"


def judged_mark(con, item, item_id, notes=None):
    """BL-297 part C: the skill judged a new item the same as `item_id`. A Very likely mark when that ID exists in the item's table and
    project and is open (or closed within RECENT_DAYS); otherwise None, with a note saying why it was ignored."""
    table, v = item.get("table"), item.get("values") or {}
    rows = [r for r in candidate_rows(con, table, v.get("project"), v.get(OWNER.get(table))) if r["id"] == item_id] \
        if table in TEXT and v.get("project") else []
    row = rows[0] if rows and rows[0]["project"] == v.get("project") else None
    if row is None:
        if notes is not None:
            notes.append(f"the judgement that “{str(v.get(TEXT.get(table, 'description')) or '')[:60]}” repeats {item_id} was "
                         f"ignored: {item_id} isn't an open (or recently closed) item of its project")
        return None
    return {"id": row["id"], "t": row["text"], "state": row["state"], "same": True, "project": row["project"],
            "strength": "Very likely", "why": "Judged the same at extraction"}


def scored(con, item, register=None):
    """[(row, score, why)] for every open item of a new item's project and table, raised on or before its message's day."""
    table, v = item["table"], item.get("values") or {}
    ctx = message_context(item, register)
    rows = [r for r in candidate_rows(con, table, v.get("project"), None)
            if r["state"] == "open" and r["project"] == v.get("project") and not raised_after(r, ctx["day"])]
    rare = rare_words(rows)
    return [(r, *match_score(v, table, r, ctx, rare)) for r in rows]


def rank_open(con, code, text, subject="", day=None):
    """The project's open actions, RAID items and pending decisions scored against a message ({id: {score, strength, why}}), for
    the expected list the sweep reads. Items raised after the message's day are left out."""
    day = day or today()
    v = {"project": code, "source": f"Email · Subject: {subject} · Sent: {day}" if subject else "", "raised": day}
    out, register = {}, people()
    for table in TEXT:
        for r, s, why in scored(con, {"op": "new", "table": table, "values": {**v, TEXT[table]: text}}, register):
            out[r["id"]] = {"score": round(s, 2), "strength": strength_of(s), "why": why}
    return out


def picker(con, item):
    """Review's picker (BL-297 part D): the open items of a proposed new item's project and table, best matches first, each with its
    title, owner, due date and, when it reaches POSSIBLE, its strength and why. Read only."""
    if item.get("op") != "new" or item.get("table") not in TEXT or not (item.get("values") or {}).get("project"):
        return []
    marked = (item.get("looks_like") or {}).get("id")
    out = [{"id": r["id"], "t": r["text"], "owner": r["owner"], "due": r.get("due"), "score": round(s, 2),
            "strength": strength_of(s), "why": why if strength_of(s) else "", "marked": r["id"] == marked}
           for r, s, why in scored(con, item)]
    return sorted(out, key=lambda x: (not x["marked"], -x["score"], x["id"]))


def strength_of(score):
    """A score in words: Very likely, Possible, or None below POSSIBLE (never a percentage)."""
    return "Very likely" if score >= VERY else "Possible" if score >= POSSIBLE else None
# ===== end BL-297 =====
