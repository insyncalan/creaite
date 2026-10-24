"""Claude Code token use and cost for creaite's build sessions (BL-343, issue #87 phase A). Development only.

Reads the Claude Code session logs on this laptop (JSONL under ~/.claude/projects/*creaite*/, subagent logs in their
subfolders included) and reports tokens and cost per day, laptop, role and model. Standard library only, Python 3.9+.

Run: python3 dev/tools/usage.py [--day YYYY-MM-DD] [--since YYYY-MM-DD] [--summary | --json]
                                [--laptop LABEL] [--role SESSION_ID=role ...] [--root DIR] [--glob PATTERN]

What is counted:
  - Each assistant message's `usage`: input, cache write (cache_creation_input_tokens), cache read and output tokens.
  - Each message id once: the logs repeat a streamed message once per content block, so the largest value of each
    kind seen for that id is kept (the last, complete one).
  - The day is the message's timestamp in this laptop's local time. --day defaults to today; --since gives a range
    from that day to --day, inclusive.

Roles (simple on purpose; override any session with --role SESSION_ID=role, a short id prefix is enough):
  - agent:  a subagent log (a file in a `subagents` folder) or a message marked isSidechain.
  - Jarvis: a top-level session whose name (agent-name or custom-title record) contains "Jarvis" or "Head of
            Product", or one of whose typed prompts says "you are Jarvis" or "you are the Head of Product".
            Merely mentioning Jarvis is not enough: every lead's charter names Jarvis.
  - lead:   any other top-level session.

Privacy: the report shows only counts, model ids, day, role and shortened session ids, never prompt or reply text, a
tool input or output, or a path. The laptop label is "laptop-" and six characters of a hash of the hostname (the
hostname itself is never printed) unless --laptop is given.
"""
import argparse
import datetime as dt
import glob
import hashlib
import json
import os
import re
import socket
import sys
from collections import defaultdict
from pathlib import Path

# Prices in US dollars per million tokens (MTok). One table; edit here only.
# Confirmed against Anthropic's published caching rates (15-10-2026): a 5-minute cache write is 1.25 x input, a
# 1-hour cache write is 2 x input, a cache read is 0.1 x input (Opus 5.5 and Sonnet 5.5 are quoted at $0.20, set below).
# The logs split cache writes into 5-minute and 1-hour tokens (usage.cache_creation); "cache_write" here is the
# 5-minute part (or all of it when a log has no split) and "cache_write_1h" the 1-hour part.
PRICES = {
    "opus": {"input": 4.00, "cache_write": 4.00 * 1.25, "cache_write_1h": 4.00 * 2, "cache_read": 0.20, "output": 20.00},
    "sonnet": {"input": 2.00, "cache_write": 2.00 * 1.25, "cache_write_1h": 2.00 * 2, "cache_read": 0.20, "output": 10.00},
    "haiku": {"input": 0.10, "cache_write": 0.10 * 1.25, "cache_write_1h": 0.10 * 2, "cache_read": 0.10 * 0.1, "output": 0.50},
}
KINDS = ("input", "cache_write", "cache_write_1h", "cache_read", "output")
USAGE_FIELDS = {
    "input": "input_tokens",
    "cache_write": "cache_creation_input_tokens",
    "cache_read": "cache_read_input_tokens",
    "output": "output_tokens",
}
KIND_LABELS = {"input": "input", "cache_write": "cache writes", "cache_write_1h": "1-hour cache writes",
               "cache_read": "cache reads", "output": "output"}
ROLES = ("Jarvis", "lead", "agent")
DEFAULT_ROOT = "~/.claude/projects"
DEFAULT_GLOB = "*creaite*"
JARVIS_NAME = re.compile(r"jarvis|head of product", re.I)
JARVIS_PROMPT = re.compile(r"\byou are (jarvis|the head of product)\b", re.I)
SHORT = 8


def family(model):
    """The price family of a model id ('opus', 'sonnet', 'haiku'), or None when it isn't priced."""
    name = (model or "").lower()
    for fam in PRICES:
        if fam in name:
            return fam
    return None


def cost(model, tokens):
    """Dollar cost of a dict of token counts (by kind) for a model; 0 for a model with no price."""
    fam = family(model)
    if not fam:
        return 0.0
    return sum(tokens.get(k, 0) * PRICES[fam][k] for k in KINDS) / 1_000_000


def short(session_id):
    """A session or agent id shortened for printing."""
    return (session_id or "?")[:SHORT]


def laptop_label():
    """A stable anonymous label for this laptop: 'laptop-' and six hex characters of a hash of its hostname."""
    return "laptop-" + hashlib.sha256(socket.gethostname().encode("utf-8")).hexdigest()[:6]


def local_day(timestamp):
    """The local YYYY-MM-DD of an ISO timestamp, or None if it can't be read."""
    try:
        text = timestamp.replace("Z", "+00:00")
        # Python 3.9's fromisoformat only takes 3 or 6 fraction digits: pad or cut to 6.
        text = re.sub(r"\.(\d+)", lambda m: "." + (m.group(1) + "000000")[:6], text, count=1)
        when = dt.datetime.fromisoformat(text)
    except (AttributeError, ValueError):
        return None
    if when.tzinfo is not None:
        when = when.astimezone()
    return when.date().isoformat()


def log_files(root, pattern):
    """Every JSONL log under the matching project folders, subagent folders included, as (path, is_subagent)."""
    base = os.path.expanduser(root)
    out = []
    for folder in sorted(glob.glob(os.path.join(base, pattern))):
        for path in sorted(Path(folder).rglob("*.jsonl")):
            out.append((path, "subagents" in path.parts))
    return out


def _records(path):
    """Yield each JSON record in a log file; a line that isn't JSON (a partial write) is skipped."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue  # a torn or partial line: nothing to count
                if isinstance(rec, dict):
                    yield rec
    except OSError:
        return


def _typed_prompt(rec):
    """The text Alan typed in a user record (not tool results or meta records), or ''."""
    if rec.get("type") != "user" or rec.get("isMeta"):
        return ""
    content = (rec.get("message") or {}).get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return ""


def is_jarvis_record(rec):
    """True when a record names its session as Jarvis (the rule in this module's docstring)."""
    kind = rec.get("type")
    if kind == "agent-name":
        return bool(JARVIS_NAME.search(str(rec.get("agentName", ""))))
    if kind == "custom-title":
        return bool(JARVIS_NAME.search(str(rec.get("customTitle", ""))))
    return bool(JARVIS_PROMPT.search(_typed_prompt(rec)))


def role_override(session_id, overrides):
    """The --role override for a session (matched by id prefix), or None."""
    for key, role in overrides.items():
        if session_id.startswith(key):
            return role
    return None


def _merge(messages, key, entry):
    """Keep one entry per message id, holding the largest count of each kind seen."""
    have = messages.get(key)
    if have is None:
        messages[key] = entry
        return
    for k in KINDS:
        have["tokens"][k] = max(have["tokens"][k], entry["tokens"][k])


def _message_entry(rec, session, subagent):
    """A counted message from an assistant record, or None when it has no usage to count."""
    msg = rec.get("message") or {}
    usage = msg.get("usage")
    model = msg.get("model") or "?"
    if not isinstance(usage, dict) or model == "<synthetic>":
        return None
    tokens = {k: int(usage.get(f) or 0) for k, f in USAGE_FIELDS.items()}
    split = usage.get("cache_creation")
    if isinstance(split, dict):
        long_ = min(int(split.get("ephemeral_1h_input_tokens") or 0), tokens["cache_write"])
        tokens["cache_write_1h"] = long_
        tokens["cache_write"] -= long_
    else:
        tokens["cache_write_1h"] = 0
    return {
        "id": msg.get("id") or rec.get("requestId") or rec.get("uuid"),
        "day": local_day(rec.get("timestamp")),
        "session": session,
        "model": model,
        "agent": subagent or bool(rec.get("isSidechain")),
        "tokens": tokens,
    }


def read_file(path, subagent, messages, jarvis):
    """Read one log: add its messages to `messages` (deduplicated) and its session to `jarvis` if it is Jarvis's."""
    session = path.stem[len("agent-"):] if subagent and path.stem.startswith("agent-") else path.stem
    for rec in _records(path):
        if not subagent and session not in jarvis and is_jarvis_record(rec):
            jarvis.add(session)
        if rec.get("type") != "assistant":
            continue
        entry = _message_entry(rec, session, subagent)
        if entry and entry["id"]:
            _merge(messages, entry["id"], entry)


def collect(root=DEFAULT_ROOT, pattern=DEFAULT_GLOB):
    """All deduplicated messages and the set of Jarvis sessions found in the logs."""
    messages, jarvis = {}, set()
    for path, subagent in log_files(root, pattern):
        read_file(path, subagent, messages, jarvis)
    return list(messages.values()), jarvis


def role_of(entry, jarvis, overrides):
    """The role of a message: an override, else agent, Jarvis or lead (see the module docstring)."""
    forced = role_override(entry["session"], overrides)
    if forced:
        return forced
    if entry["agent"]:
        return "agent"
    return "Jarvis" if entry["session"] in jarvis else "lead"


def aggregate(messages, jarvis, overrides, laptop, first, last):
    """Rows of tokens and cost per (day, laptop, role, model), and per session, for days first..last."""
    rows = defaultdict(lambda: dict.fromkeys(KINDS, 0))
    sessions = defaultdict(lambda: {"cost": 0.0, "messages": 0})
    for m in messages:
        if not m["day"] or not first <= m["day"] <= last:
            continue
        role = role_of(m, jarvis, overrides)
        row = rows[(m["day"], laptop, role, m["model"])]
        for k in KINDS:
            row[k] += m["tokens"][k]
        s = sessions[(short(m["session"]), role)]
        s["cost"] += cost(m["model"], m["tokens"])
        s["messages"] += 1
    out = []
    for (day, lap, role, model), tokens in sorted(rows.items()):
        out.append({"day": day, "laptop": lap, "role": role, "model": model, "priced": bool(family(model)),
                    **tokens, "cost": round(cost(model, tokens), 4)})
    top = sorted(({"session": k[0], "role": k[1], "messages": v["messages"], "cost": round(v["cost"], 4)}
                  for k, v in sessions.items()), key=lambda s: -s["cost"])
    return out, top


def _totals(rows, field):
    """Cost per value of one row field, largest first."""
    acc = defaultdict(float)
    for r in rows:
        acc[r[field]] += r["cost"]
    return sorted(acc.items(), key=lambda kv: -kv[1])


def kind_costs(rows):
    """Dollar cost per token kind across the rows."""
    acc = dict.fromkeys(KINDS, 0.0)
    for r in rows:
        fam = family(r["model"])
        if fam:
            for k in KINDS:
                acc[k] += r[k] * PRICES[fam][k] / 1_000_000
    return acc


def _money(value):
    return "${:,.2f}".format(value)


def summary_lines(rows, top, laptop, first, last):
    """Three or four plain lines for the digest: total, by role, by model, top driver."""
    span = first if first == last else "{} to {}".format(first, last)
    total = sum(r["cost"] for r in rows)
    lines = ["Usage {} ({}): {} total, {} messages counted.".format(
        span, laptop, _money(total), sum(s["messages"] for s in top))]
    if not rows:
        return lines
    lines.append("By role: " + ", ".join("{} {}".format(k, _money(v)) for k, v in _totals(rows, "role")) + ".")
    lines.append("By model: " + ", ".join("{} {}".format(k, _money(v)) for k, v in _totals(rows, "model")) + ".")
    kinds = kind_costs(rows)
    kinds["cache_write"] += kinds.pop("cache_write_1h")  # one "cache writes" driver, 5-minute and 1-hour together
    kind = max(kinds, key=kinds.get)
    share = 100 * kinds[kind] / total if total else 0
    driver = "Top driver: {} ({:.0f}% of cost)".format(KIND_LABELS[kind], share)
    if top:
        driver += "; biggest session {} {} {}".format(top[0]["role"], top[0]["session"], _money(top[0]["cost"]))
    lines.append(driver + ".")
    return lines


def table_lines(rows, top):
    """The full report: one line per day, laptop, role and model, then the five costliest sessions."""
    head = "{:<10} {:<14} {:<6} {:<18} {:>11} {:>11} {:>13} {:>10} {:>10}".format(
        "day", "laptop", "role", "model", "input", "cache wr", "cache rd", "output", "cost")
    lines = [head, "-" * len(head)]
    for r in rows:
        lines.append("{:<10} {:<14} {:<6} {:<18} {:>11,} {:>11,} {:>13,} {:>10,} {:>10}".format(
            r["day"], r["laptop"][:14], r["role"], r["model"][:18], r["input"], r["cache_write"] + r["cache_write_1h"], r["cache_read"],
            r["output"], _money(r["cost"]) + ("" if r["priced"] else "*")))
    lines.append("{:<{w}}{:>10}".format("total", _money(sum(r["cost"] for r in rows)), w=len(head) - 10))
    if any(not r["priced"] for r in rows):
        lines.append("* model not in the price table: counted at $0")
    if top:
        lines.append("")
        lines.append("Costliest sessions: " + "; ".join(
            "{} {} {} ({} msgs)".format(s["role"], s["session"], _money(s["cost"]), s["messages"]) for s in top[:5]))
    return lines


def parse_roles(pairs):
    """--role SESSION_ID=role pairs as a dict; exits on a malformed pair or unknown role."""
    out = {}
    for pair in pairs or []:
        sid, _, role = pair.partition("=")
        match = {r.lower(): r for r in ROLES}.get(role.strip().lower())
        if not sid.strip() or not match:
            sys.exit("usage.py: --role wants SESSION_ID=role, role one of {}".format(", ".join(ROLES)))
        out[sid.strip()] = match
    return out


def parse_args(argv):
    """The command line."""
    p = argparse.ArgumentParser(description="Claude Code tokens and cost for creaite sessions (BL-343).")
    p.add_argument("--day", default=dt.date.today().isoformat(), help="YYYY-MM-DD (default today)")
    p.add_argument("--since", help="YYYY-MM-DD: report from this day to --day")
    p.add_argument("--summary", action="store_true", help="three or four plain lines for the digest")
    p.add_argument("--json", action="store_true", help="rows, sessions and totals as JSON")
    p.add_argument("--laptop", default=laptop_label(), help="laptop label (default: an anonymous hash of the hostname)")
    p.add_argument("--role", action="append", metavar="SESSION_ID=role", help="force a session's role")
    p.add_argument("--root", default=DEFAULT_ROOT, help="Claude Code projects folder")
    p.add_argument("--glob", default=DEFAULT_GLOB, help="project folders to read")
    args = p.parse_args(argv)
    for value in (args.day, args.since):
        if value and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            p.error("dates are YYYY-MM-DD")
    return args


def main(argv=None):
    """Read the logs and print the report."""
    args = parse_args(argv)
    first, last = (args.since or args.day), args.day
    messages, jarvis = collect(args.root, args.glob)
    rows, top = aggregate(messages, jarvis, parse_roles(args.role), args.laptop, first, last)
    if args.json:
        print(json.dumps({"from": first, "to": last, "laptop": args.laptop, "rows": rows, "sessions": top,
                          "total_cost": round(sum(r["cost"] for r in rows), 4), "prices_per_mtok": PRICES}, indent=2))
    elif args.summary:
        print("\n".join(summary_lines(rows, top, args.laptop, first, last)))
    else:
        print("\n".join(table_lines(rows, top)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
