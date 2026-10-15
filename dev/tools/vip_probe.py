#!/usr/bin/env python3
"""BL-342 step 0: the live probe for thread cards (read-only; run by Alan in his own vault).

Run, from your vault's folder (not the development repository):
    cd <your vault> && python3 <path to this repository>/dev/tools/vip_probe.py [--since-days 3 | 0.05]

WHAT IT READS (through `claude -p` headless, three calls, the same read-only Microsoft 365 tools as the follow check,
VIP_TOOLS in live_server.py): mail, Teams chats and calendar items sent by the people in the people register's VIP field,
and Sent Items by subject. It also reads the vault's settings and the people register.
WHAT IT WRITES: nothing. No file, no vip.json, no staging, no log. It prints to the terminal only, and only ids, dates,
counts and costs: never message text, subjects, names or addresses.
WHAT IT CANNOT DO: every Microsoft 365 action tool is on the deny list, and no Bash, Write or Edit tool is allowed.
It refuses to run in the development repository (.creaite-dev).

It answers: (a) the three live facts of the plan's point (a); (b) whether Haiku reads stage 1 as well as Sonnet does.
Exit code: 0 done, 2 refused or could not run.
"""
import sys

sys.dont_write_bytecode = True       # importing the vault's scripts must not leave a __pycache__ in it

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

# The same read-only list as live_server.VIP_TOOLS (dev/tests/test_vip_probe.py checks the two agree).
M365 = "mcp__claude_ai_Microsoft_365__"
PROBE_TOOLS = [M365 + "outlook_email_search", M365 + "chat_message_search", M365 + "outlook_calendar_search",
               M365 + "read_resource"]
# Denied whatever else: nothing that writes, runs a command or leaves the laptop. The vault's own Microsoft 365 action list
# (permissions.m365_action_tools) is added to these at run time.
EXTRA_DENY = ["Bash", "Write", "Edit", "NotebookEdit", "WebFetch", "WebSearch", "Task"]

FACTS_PROMPT = (
    "creaite probe, facts. Read-only: change nothing, write nothing, send nothing. Using Alan's Microsoft 365, for messages "
    "sent by these addresses since {since} (local time): {addresses}. (1) Outlook mail: take up to 3 messages, call "
    "read_resource on each, and report whether the result carries a conversation ID. (2) Teams: search chat messages from "
    "these addresses and report whether each search result carries the chat ID. (3) Sent Items: take the subject of one of "
    "those mails, search Alan's Sent Items for that subject, and report how many results came back. If Microsoft 365 tools "
    "are not available say connected false. Reply with ONLY this JSON, ids and counts only, never message text, subjects, "
    "names or addresses: {{\"connected\": true|false, \"mail\": [{{\"message_id\": \"...\", \"conversation_id\": \"...\"|null}}], "
    "\"teams\": [{{\"chat_id\": \"...\"|null}}], \"sent_items\": {{\"searched\": true|false, \"results\": 0}}}}")
STAGE1_PROMPT = (
    "creaite probe, stage 1 (ID-only). Read-only: search Alan's Microsoft 365 for messages SENT BY these addresses since "
    "{since} (local time): Outlook Inbox mail, Teams chats and channel messages, and calendar invites or updates. "
    "Addresses: {addresses}. Do NOT summarise and do not quote anything. For each CONVERSATION (the Teams chat, or the mail "
    "thread; never one per message) with a message from them in that time, reply with one compact object: "
    "{{\"kind\": \"teams\"|\"mail\"|\"calendar\", \"conversation\": \"the Teams chat ID or the mail conversation ID, null if "
    "unknown\", \"msg\": \"ID of its newest message\", \"last\": \"YYYY-MM-DD HH:MM of its newest message\"}}. "
    "Reply with ONLY a JSON array of those objects, ids and dates only. Reply [] if there are none.")

ID_OK = re.compile(r"^[A-Za-z0-9:@._=+/\-]{1,200}$")
DATE_OK = re.compile(r"^\d{4}-\d{2}-\d{2}( \d{2}:\d{2})?$")
# The plan's table, used only if dev/tools/usage.py (BL-343) is not beside this script. Dollars per million tokens.
FALLBACK_PRICES = {"sonnet": {"input": 2.0, "cache_write": 2.5, "cache_write_1h": 4.0, "cache_read": 0.2, "output": 10.0},
                   "haiku": {"input": 0.1, "cache_write": 0.125, "cache_write_1h": 0.2, "cache_read": 0.01, "output": 0.5}}


def say(*a):
    """Print to the terminal: the probe's only output."""
    print(*a, flush=True)


def load_usage():
    """dev/tools/usage.py (BL-343), imported by file so its price table is the one source; None when it is not there."""
    f = Path(__file__).resolve().with_name("usage.py")
    if not f.is_file():
        return None
    spec = importlib.util.spec_from_file_location("usage_prices", f)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def cost_of(model, usage, mod):
    """Dollars for one run's own usage figures, priced with usage.py's table (the plan's table when usage.py is absent)."""
    tok = {"input": int(usage.get("input_tokens") or 0), "cache_write": int(usage.get("cache_creation_input_tokens") or 0),
           "cache_write_1h": 0, "cache_read": int(usage.get("cache_read_input_tokens") or 0),
           "output": int(usage.get("output_tokens") or 0)}
    split = usage.get("cache_creation") or {}
    if split:
        long_ = min(int(split.get("ephemeral_1h_input_tokens") or 0), tok["cache_write"])
        tok["cache_write_1h"], tok["cache_write"] = long_, tok["cache_write"] - long_
    if mod is not None:
        return mod.cost(model, tok), tok
    pr = FALLBACK_PRICES[model]
    return sum(tok[k] * pr[k] for k in tok) / 1_000_000, tok


def setup_vault(vault):
    """Import the vault's own paths and people register (read only). Returns (paths, propose)."""
    scripts = str(Path(vault) / "system" / "scripts")
    sys.path.insert(0, scripts)
    import paths  # noqa: E402
    import propose  # noqa: E402
    return paths, propose


def claude_command(paths_mod):
    """The `claude` command, found as the live server finds it: CREAITE_CLAUDE, else the run's PATH, else ~/.local/bin."""
    try:
        import launch
        path = launch.run_path(os.environ.get("PATH", ""))
    except Exception:  # noqa: BLE001
        path = os.environ.get("PATH", "")
    return os.environ.get("CREAITE_CLAUDE") or shutil.which("claude", path=path) or str(Path.home() / ".local/bin/claude"), path


def build_command(claude, model, prompt, deny):
    """Options first, then `--`, then the prompt, so nothing in the prompt is ever read as an option. `--tools ""` removes every
    built-in tool, as the live VIP check does (vip-tools-fix): a probe that still reads its Microsoft 365 tools proves they load."""
    cmd = [claude, "-p"]
    if model:
        cmd += ["--model", model]
    cmd += ["--output-format", "json", "--tools", "", "--allowedTools", ",".join(PROBE_TOOLS)]
    cmd += ["--disallowedTools", ",".join(deny), "--", prompt]
    return cmd


def run_claude(claude, path, model, prompt, deny, cwd):
    """One headless call. Returns (reply object or None, why)."""
    env = dict(os.environ, PATH=path, CREAITE_HEADLESS_RUN="1")
    try:
        r = subprocess.run(build_command(claude, model, prompt, deny), cwd=cwd, capture_output=True, text=True,
                           timeout=600, env=env)
        return json.loads(r.stdout or "{}"), (r.stderr.strip().splitlines() or ["no reply"])[-1]
    except (OSError, ValueError, subprocess.TimeoutExpired) as e:
        return None, type(e).__name__


def json_in(result, opener):
    """The first JSON array or object in a reply's text, or None."""
    m = re.search(r"\[.*\]" if opener == "[" else r"\{.*\}", result or "", re.S)
    try:
        return json.loads(m.group(0)) if m else None
    except ValueError:
        return None


def clean_id(v):
    """The id if it is a plain id-shaped string, else None."""
    return v if isinstance(v, str) and ID_OK.match(v) else None


def clean_date(v):
    """The date if it is YYYY-MM-DD[ HH:MM], else None."""
    return v if isinstance(v, str) and DATE_OK.match(v) else None


def stage1_rows(found):
    """[(id, last)] from a stage 1 reply: only well-formed ids and dates survive; anything else (text, subjects, names) is dropped."""
    rows = []
    for o in found if isinstance(found, list) else []:
        if isinstance(o, dict):
            rows.append((clean_id(o.get("conversation")) or clean_id(o.get("msg")) or "(no id)", clean_date(o.get("last")) or "(no date)"))
    return sorted(set(rows))


def compare(reference, other):
    """(matches, total): rows present in both, over all rows in either. Reference first (Sonnet)."""
    a, b = set(reference), set(other)
    return len(a & b), len(a | b)


def ids_of(items, key):
    """The well-formed ids under `key` in a list of objects (None where missing or malformed), and how many objects."""
    objs = [o for o in items or [] if isinstance(o, dict)]
    return [clean_id(o.get(key)) for o in objs]


def evidence(ids):
    """'n of m <things>; ids a, b' for a list of ids with None gaps; ids and counts only."""
    return f"{sum(1 for c in ids if c)} of {len(ids)}; ids {', '.join(c for c in ids if c) or 'none'}"


def facts(reply):
    """The three facts as (connected, [(label, yes/no, evidence)]) from the facts reply, counts and ids only."""
    d = json_in((reply or {}).get("result"), "{") or {}
    convs, chats = ids_of(d.get("mail"), "conversation_id"), ids_of(d.get("teams"), "chat_id")
    sent = d.get("sent_items") if isinstance(d.get("sent_items"), dict) else {}
    n_sent = sent.get("results") if isinstance(sent.get("results"), int) else 0
    rows = [("(i) read_resource on a mail returns its conversation ID", bool(convs) and all(convs), "messages " + evidence(convs)),
            ("(ii) Teams search results carry the chat ID", bool(chats) and all(chats), "results " + evidence(chats)),
            ("(iii) Sent Items can be searched by subject", bool(sent.get("searched")) and n_sent > 0, f"{n_sent} results")]
    return d.get("connected", None), rows


def preflight(args):
    """Refuse (return a message) or return the pieces a run needs: (vault paths module, addresses, deny list)."""
    vault = Path(args.vault).resolve()
    if (vault / ".creaite-dev").exists():
        return "Refused: this is the development repository (sample data only, no Microsoft 365). Run the probe from your own vault."
    if not (vault / "system" / "scripts" / "paths.py").is_file():
        return f"Refused: {vault} is not a creaite vault. Run it from your vault's folder, or pass --vault."
    paths_mod, propose = setup_vault(vault)
    vips = {a for p in propose.vip_people() for a in p["emails"]}
    if not vips or not ((paths_mod.load_settings().get("vip") or {}).get("enabled", True)):
        return "Nothing to probe: nobody is followed in the people register, or the follow check is off in settings."
    import permissions
    return paths_mod, sorted(vips), permissions.m365_action_tools() + EXTRA_DENY


def show_facts(call, usage_mod, since, addresses):
    """Run and print the three facts. Returns False when Microsoft 365 could not be used at all."""
    say("\nFacts (point a), one Sonnet call:")
    reply, why = call("sonnet", FACTS_PROMPT.format(since=since, addresses=addresses))
    connected, rows = facts(reply)
    if reply is None or reply.get("is_error") or connected is False or json_in(reply.get("result"), "{") is None:
        say("  Microsoft 365 does not look connected, or the reply was not usable "
            f"({why if reply is None else 'no reply data'}). Connect Microsoft 365 in Claude and run again.")
        if reply is None:
            return False
    for label, ok, ev in rows:
        say(f"  {'yes' if ok else 'no '}  {label}: {ev}")
    if reply:
        say(f"  cost ${cost_of('sonnet', reply.get('usage') or {}, usage_mod)[0]:.4f}")
    return True


def show_stage1(call, usage_mod, model, prompt):
    """Run and print stage 1 on one model. Returns (rows, cost) or None."""
    reply, why = call(model, prompt)
    found = json_in((reply or {}).get("result"), "[")
    if reply is None or found is None:
        say(f"\nStage 1 on {model}: no usable reply ({why}).")
        return None
    rws = stage1_rows(found)
    c, tok = cost_of(model, reply.get("usage") or {}, usage_mod)
    say(f"\nStage 1 on {model}: {len(rws)} thread(s), cost ${c:.4f} (in {tok['input']}, "
        f"cache write {tok['cache_write'] + tok['cache_write_1h']}, cache read {tok['cache_read']}, out {tok['output']})")
    for i, last in rws:
        say(f"  {i}  last {last}")
    return rws, c


def verdict(results):
    """Print the agreement verdict and the recommendation. Returns the exit code."""
    say("")
    if not results.get("haiku") or not results.get("sonnet"):
        say("Cannot compare: one of the runs gave no usable reply. Use Sonnet for stage 1 until the probe runs cleanly.")
        return 2
    (h_rows, hc), (s_rows, sc) = results["haiku"], results["sonnet"]
    n, m = compare(s_rows, h_rows)
    say(f"Haiku matches Sonnet on {n} of {m} IDs and dates. Cost per check: Haiku ${hc:.4f}, Sonnet ${sc:.4f} "
        f"({(sc / hc if hc else 0):.0f} times).")
    if m == 0:
        say("No new messages in the window, so nothing to compare: widen it with --since-days and run again.")
    else:
        say("Haiku is fine for stage 1" if n == m else "use Sonnet for stage 1")
    return 0


def main(argv=None):
    """Check the vault, run the facts call and stage 1 on both models, print the verdict."""
    ap = argparse.ArgumentParser(description="BL-342 step 0: read-only live probe. Writes nothing.")
    ap.add_argument("--vault", default=os.getcwd(), help="the vault's folder (default: the current folder)")
    ap.add_argument("--since-days", type=float, default=3, help="how far back to look, in days; a fraction is fine, e.g. 0.05 (default 3)")
    args = ap.parse_args(argv)
    pre = preflight(args)
    if isinstance(pre, str):
        say(pre)
        return 2
    paths_mod, vips, deny = pre
    claude, path = claude_command(paths_mod)
    since = (datetime.now() - timedelta(days=args.since_days)).strftime("%Y-%m-%d %H:%M")
    addresses = ", ".join(vips)
    usage_mod = load_usage()

    def call(model, prompt):
        """One headless claude call on `model`."""
        return run_claude(claude, path, model, prompt, deny, paths_mod.ROOT)

    say(f"vip_probe: read-only, writes nothing. {len(vips)} followed address(es), since {since}. "
        f"Prices from {'dev/tools/usage.py' if usage_mod else 'the plan table (usage.py not found beside this script)'}.")
    if not show_facts(call, usage_mod, since, addresses):
        return 2
    prompt = STAGE1_PROMPT.format(since=since, addresses=addresses)
    return verdict({m: show_stage1(call, usage_mod, m, prompt) for m in ("haiku", "sonnet")})


if __name__ == "__main__":
    sys.exit(main())
