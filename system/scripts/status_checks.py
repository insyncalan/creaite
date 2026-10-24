"""creaite status checks (BL-106): small notes on a drafted status, from plain code. Never blocking, never rewriting.

  check(draft, facts, length="standard", audience="internal", sources="") -> [{"id", "note"}]
  evidence(claims, facts) -> {"claims", "facts"}        BL-207: each sentence's facts, rows and quotes (read, never stored)
  kept(original, rewritten) -> [{"id", "note"}]       a rewrite's lost or added dates and numbers

  python3 system/scripts/status_checks.py check <CODE> [--from D] [--to D] [--audience internal|client] [--length short|standard|fuller]
      reads {"draft", "sources", "original"} as JSON on standard input and prints {"notes", "facts", "sources"} (the live
      server's /api/current/check): the checks on the draft, and with `original` also kept(original, draft)

`draft` is the Markdown of the drafted status (the left pane), `facts` the sheet from status_facts.facts, `sources` the text of
the SOURCES list after the draft. A note says what is missing in plain words ("No ask mentioned, but 2 actions are waiting on
others"); an empty list means every check passed. Thresholds are in settings.json `status`.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402,F401  (doctor: every script takes its locations from paths.py; the settings come through status_facts)
import status_facts  # noqa: E402

POSITION = re.compile(r"\b(on track|at risk|off track)\b", re.I)
LENGTH_SLACK = 1.25      # a draft may run a quarter over the target before it is flagged


def plain(md):
    """Markdown as readable words: no bold marks, bullets or link targets."""
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", md or "")
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"[*_`>#]+", "", t)
    return re.sub(r"^\s*[-•]\s+", "", t, flags=re.M)


def headline(md):
    """The first paragraph (up to a blank line or the first bullet), as plain words."""
    out = []
    for line in (md or "").strip().splitlines():
        if not line.strip() or re.match(r"\s*(?:[-*•]\s|\d+\.\s|#)", line):
            if out:
                break
            continue
        out.append(line)
    return " ".join(plain(" ".join(out)).split())


def words(text):
    """How many words a draft's text has, Markdown removed."""
    return len(plain(text).split())


def check(draft, facts, length="standard", audience="internal", sources=""):
    """Notes on a drafted status (BL-106): headline, position, ask, length, sources and audience checks against
    the facts sheet; [{id, note}], empty when every check passed. Never blocks or rewrites.
    """
    cfg = status_facts.settings()
    notes = []
    add = lambda i, n: notes.append({"id": i, "note": n})  # noqa: E731
    head = headline(draft)
    n = len(head.split())
    if not head:
        add("headline", "No headline: start with the position and the one thing that matters.")
    else:
        if n > cfg["headline_max_words"]:
            add("headline", f"The headline is {n} words; aim for under {cfg['headline_max_words']}.")
        if not POSITION.search(head):
            add("position", "The headline doesn't say on track, at risk or off track.")
    ids = sorted(set(status_facts.ID_RE.findall(plain(draft))))
    if ids:
        add("ids", f"Item numbers in the text ({', '.join(ids[:4])}{'…' if len(ids) > 4 else ''}): say what they are instead.")
    if facts.get("has_figures") and not re.search(r"\d", plain(draft)):
        add("figures", "No date or number in the text, though the facts have some.")
    asks = facts.get("asks") or []
    if asks:
        text = plain(draft).lower()
        named = lambda a: a["who"].lower() in text or (a["who"].split()[0].lower() in text if a["who"].split() else False)  # noqa: E731
        if not any(named(a) for a in asks) and not re.search(r"\b(need|needs|needed|waiting|awaiting|ask|request|decide|confirm|approve|approval)\b", text):
            add("asks", f"No ask mentioned, but {len(asks)} {'item is' if len(asks) == 1 else 'items are'} waiting on others.")
    target = cfg["length_words"].get(length)
    if target and words(draft) > target * LENGTH_SLACK:
        add("length", f"{words(draft)} words; {length.capitalize()} aims for about {target}.")
    known = set(facts.get("sources") or [])
    unknown = []
    for entry in re.findall(r"^\s*[-*]\s+(.+)$", sources or "", re.M):
        tokens = status_facts.ID_RE.findall(entry) + re.findall(r"projects/\S+?\.\w{2,4}", entry)
        unknown += [t for t in tokens if t not in known]
    if unknown:
        add("sources", f"Not in the facts sheet, so check it applies: {', '.join(dict.fromkeys(unknown))[:200]}.")
    return notes


FIGURE = re.compile(r"\d{1,2}-\d{1,2}(?:-\d{2,4})?|\d+(?:[.,]\d+)?\s?%|\d{2,}(?:[.,]\d+)?")


def figures(md):
    """The dates and numbers in a text, as comparable strings (single digits and list numbers are ignored)."""
    return {re.sub(r"\s", "", m).replace(",", ".") for m in FIGURE.findall(plain(md))}


def kept(original, rewritten):
    """"Make it executive" keeps Alan's facts: a note for every date or number in his text that the rewrite lost, and every
    one it added that his text did not have. The rewrite is a draft he reads, so these are notes, never blocks."""
    before, after = figures(original), figures(rewritten)
    notes = []
    if before - after:
        notes.append({"id": "kept", "note": f"Your text had {', '.join(sorted(before - after)[:5])}, which the rewrite leaves out."})
    if after - before:
        notes.append({"id": "added", "note": f"The rewrite adds {', '.join(sorted(after - before)[:5])}, which your text didn't have: check it."})
    return notes


# ===== BL-225 (sprint-drafts-fields) ===== the client-wording check: plain code, after the model has written a draft.
COMMON_CAPS = set("I The A An We Our Your You It This That These Those What When Where Who How Why Some Any All Each No Not "
                  "Monday Tuesday Wednesday Thursday Friday Saturday Sunday January February March April May June July August "
                  "September October November December UAT SOW IT AI".split())


def client_wording(draft, item_text, people=()):
    """Notes on drafted client wording (BL-225): any number or date, code, or capitalised name in the draft that isn't in the item's
    own text, and any person's name from the people register at all. Notes, never blocks: Alan reads the draft."""
    notes, src, low = [], item_text or "", (draft or "").lower()
    added = figures(draft) - figures(src)
    if added:
        notes.append({"id": "number", "note": f"{', '.join(sorted(added)[:5])} isn't in the item's text: check it."})
    codes = set(re.findall(r"\b[A-Z][A-Z0-9]{2,6}-(?:[A-Z]-)?\d{3}\b|\b[A-Z]{3,7}\b", draft or "")) - COMMON_CAPS
    if codes:
        notes.append({"id": "code", "note": f"{', '.join(sorted(codes)[:5])} looks like an internal code."})
    names = [n for n in people if len(n) > 2 and re.search(rf"\b{re.escape(n.lower())}\b", low)]
    if names:
        notes.append({"id": "person", "note": f"Names a person ({', '.join(sorted(set(names))[:3])}): client wording usually doesn't."})
    caps = set()
    for sent in re.split(r"(?<=[.!?:])\s+|\n+", draft or ""):
        line = re.sub(r"^[-•*\s]*(?:[A-Z][a-z ]+:\s*)?", "", sent.strip())        # a heading ("What it is:") and the first word
        for w in [m.group() for m in re.finditer(r"\b[A-Z][a-z]{2,}\b", line) if m.start() > 0]:
            if w not in COMMON_CAPS and w.lower() not in src.lower() and not any(w.lower() in n.lower() for n in names):
                caps.add(w)
    if caps:
        notes.append({"id": "name", "note": f"{', '.join(sorted(caps)[:5])} isn't in the item's text: check it."})
    return notes
# ===== end BL-225 =====


# ===== BL-207 (sprint-insight) =====  evidence: each sentence of a draft mapped to its facts, rows and quotes
MARK = re.compile(r"\s*\{\s*((?:F\d+\s*,?\s*)*)\}")
STOP = set("""the a an and or but of to in on for with by at from as is are was were be been being this that these those it its
it's we our you your they their them he she his her not no nothing has have had will would can could should may might than then
there here what which who whom when where why how all any each more most some such only own same so too very just about into
over under after before again further once now since until while also week weeks day days status""".split())


def strip_marks(md):
    """A drafted text without its fact marks ({F3, F7}): what the editor shows and what is saved."""
    return re.sub(r"[ \t]+$", "", MARK.sub("", md or ""), flags=re.M)


def split_claims(md):
    """[(sentence, [fact IDs])] from a marked draft: a claim runs from the block's start or the last mark to the next mark;
    text after the last mark of a block (three words or more) is a claim with no source. Headings and image lines are not
    claims. The page splits the same way over its editor (claimsWrap)."""
    out = []
    for block in re.split(r"\n\s*\n|\n(?=\s*(?:[-*]|\d+\.)\s)|\n(?=>)", md or ""):
        b = block.strip()
        if not b or b.startswith("#") or b.startswith("!["):
            continue
        pos = 0
        for m in MARK.finditer(b):
            text = plain(b[pos:m.start()]).strip()
            if text:
                out.append((" ".join(text.split()), re.findall(r"F\d+", m.group(1))))
            pos = m.end()
        rest = " ".join(plain(b[pos:]).split()).strip()
        if len(re.findall(r"[A-Za-z]{2,}", rest)) >= 3:
            out.append((rest, []))
    return out


def fact_lines(facts):
    """{fact id: fact line, with the title of the part it is in} from a facts sheet."""
    return {ln["fid"]: {**ln, "part": part["title"].split(" (")[0]} for part in facts.get("parts") or [] for ln in part["lines"] if ln.get("fid")}


def keywords(text):
    """A text's matching words: lower case, four letters or more, stop words removed, plus its figures."""
    t = plain(text).lower()
    return {w for w in re.findall(r"[a-z][a-z'-]{3,}", t) if w not in STOP} | set(figures(text))


def support(sentence, facts):
    """Fact IDs that support a sentence written or edited by hand (the re-check): the same date or number, or three
    shared words. Plain code, so a sentence it can't place says "no source found" rather than a guess."""
    want, nums = keywords(sentence), figures(sentence)
    found = []
    for fid, ln in fact_lines(facts).items():
        have = keywords(ln["text"])
        shared = want & have
        if (nums & figures(ln["text"]) and len(shared) >= 2) or len(shared - nums) >= 3:
            found.append((len(shared), fid))
    return [fid for _, fid in sorted(found, key=lambda t: -t[0])[:3]]


def file_text(path):
    """The plain text of a vault file (Markdown, text or Word), read when shown and never stored; None if it can't be read."""
    import paths as _paths
    try:
        f = _paths.resolve(path)
        if not f.is_file():
            return None
        if f.suffix.lower() == ".docx":
            import docx_tools
            return "\n".join(docx_tools.story_text(docx_tools.accept_xml(raw.decode("utf-8"))[0])
                             for info, raw in docx_tools.read_parts(f) if info.filename == "word/document.xml")
        if f.suffix.lower() in (".md", ".txt", ".vtt"):
            return f.read_text(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001  a locked, online-only or half-synced file: the source note stands in
        return None
    return None


def quote(path, words):
    """The line of a file that best matches `words`: {"path", "line", "text"} or None (no file, or nothing close)."""
    text = file_text(path)
    if text is None:
        return None
    want, best = keywords(words), (0, 0, "")
    for n, line in enumerate(text.splitlines(), 1):
        line = " ".join(line.split()).lstrip("-•* ")
        if not line:
            continue
        if line.lower() == " ".join(plain(words).split()).lower():
            return {"path": path, "line": n, "text": line[:400]}
        score = len(want & keywords(line))
        if score > best[0]:
            best = (score, n, line)
    return {"path": path, "line": best[1], "text": best[2][:400]} if best[0] >= 2 else None


def source_path(source):
    """The file in an item's source note ("projects/…/minutes/2026-10-06 Steering.docx — Actions"; "— Action Items" before
    #296), or ""."""
    m = re.match(r"\s*(projects/[^—]+?\.(?:docx|md|txt|vtt))\b", source or "")
    return m.group(1) if m else ""


def item_row(con, ident):
    """A tracker row for the panel: id, kind, title, status, owner, dates and source, with a quote from its source file."""
    for kind, sql in (("actions", "SELECT id, description AS title, status, owner, due_date AS due, raised, closed, source FROM actions WHERE id = ?"),
                      ("raid", "SELECT id, description AS title, status, owner, due_date AS due, raised, closed, source, type FROM raid WHERE id = ?"),
                      ("decisions", "SELECT id, decision AS title, status, made_by AS owner, needed_by AS due, date AS raised, NULL AS closed, source FROM decisions WHERE id = ?"),
                      ("milestones", "SELECT id, name AS title, status, NULL AS owner, forecast_date AS due, NULL AS raised, NULL AS closed, source FROM milestones WHERE id = ?")):
        cur = con.execute(sql, (ident,))
        row = cur.fetchone()
        if row:
            r = dict(zip([c[0] for c in cur.description], row))
            r["kind"] = kind
            path = source_path(r.get("source"))
            r["quote"] = quote(path, r["title"]) if path else None
            return r
    return None


def evidence(claims, facts):
    """For each claim {"n", "text", "ids", "edited"}: the facts it rests on, checked. A claim the model marked keeps the
    IDs the sheet has; an edited one (or one marked with none) is re-checked by `support`. Returns {"claims": [{"n",
    "ids", "how"}], "facts": {fid: {"text", "part", "rows", "files"}}}; how is "marked", "rechecked" or "none"."""
    import tracker
    lines = fact_lines(facts)
    out, used = [], set()
    for c in claims or []:
        ids = [] if c.get("edited") else [i for i in (c.get("ids") or []) if i in lines]
        how = "marked" if ids else "none"
        if not ids and (c.get("edited") or c.get("recheck")):
            ids = support(c.get("text") or "", facts)
            how = "rechecked" if ids else "none"
        used.update(ids)
        out.append({"n": c.get("n"), "ids": ids, "how": how})
    detail = {}
    con = tracker.connect()
    try:
        for fid in sorted(used, key=lambda x: int(x[1:])):
            ln = lines[fid]
            rows, files = [], []
            for src in ln["src"]:
                if src.startswith("projects/"):
                    files.append(quote(src, ln["text"]) or {"path": src, "line": 0, "text": ""})
                else:
                    r = item_row(con, src)
                    if r:
                        rows.append(r)
            detail[fid] = {"text": ln["text"], "part": ln["part"], "rows": rows, "files": files}
    finally:
        con.close()
    return {"claims": out, "facts": detail}


def sources(src, text=""):
    """The rows and quotes for a saved sentence's sources (item IDs and file paths): {"rows", "files"}. Read only."""
    import tracker
    rows, files = [], []
    con = tracker.connect()
    try:
        for s in src or []:
            if not isinstance(s, str):
                continue
            if s.startswith("projects/"):
                files.append(quote(s, text) or {"path": s, "line": 0, "text": ""})
            elif status_facts.ID_RE.fullmatch(s) or re.fullmatch(r"[A-Z][A-Z0-9]{2,6}-M-\d{3}", s):
                r = item_row(con, s)
                if r:
                    rows.append(r)
    finally:
        con.close()
    return {"rows": rows, "files": files}


def evidence_path(code):
    """Where a project's saved Current state sentence links are kept (BL-207): staging/evidence/<CODE>-current.json."""
    import paths as _paths
    return _paths.EVIDENCE / f"{code}-current.json"


def save_evidence(code, sentences):
    """Rewrite a project's evidence file (BL-207): {hash: {"facts": [{"text", "part", "src"}], "how", "kept"}}. Only the hash of a
    sentence is kept, never its words; the facts' lines are the tracker's own wording. Returns how many sentences were kept."""
    import paths as _paths
    clean = {}
    for h, v in list((sentences or {}).items())[:300]:
        if not (isinstance(h, str) and re.fullmatch(r"[0-9a-f]{8,16}", h) and isinstance(v, dict)):
            continue
        facts = [{"text": str(f.get("text") or "")[:600], "part": str(f.get("part") or "")[:40],
                  "src": [s for s in (f.get("src") or []) if isinstance(s, str) and len(s) < 400][:12]}
                 for f in (v.get("facts") or [])[:8] if isinstance(f, dict)]
        how = v.get("how") if v.get("how") in ("marked", "rechecked", "none", "kept") else "marked"
        clean[h] = {"facts": facts, "how": how, **({"kept": str(v.get("kept"))[:300]} if v.get("kept") is not None else {})}
    target = evidence_path(code)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".tmp")
    from datetime import datetime
    tmp.write_text(json.dumps({"code": code, "saved": datetime.now().strftime("%Y-%m-%d %H:%M"), "sentences": clean},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(target)
    _ = _paths
    return len(clean)


def load_evidence(code):
    """A project's saved sentence links (BL-207), or None if there are none or they can't be read."""
    try:
        data = json.loads(evidence_path(code).read_text(encoding="utf-8"))
        return data if isinstance(data.get("sentences"), dict) else None
    except (OSError, ValueError, AttributeError):
        return None


def unsourced_note(result):
    """A note for the sentences with no source found (BL-207), or [] when every sentence has one."""
    n = sum(1 for c in result["claims"] if c["how"] == "none")
    return [{"id": "unsourced", "note": f"No source found for {plural_s(n)}: edit {'it' if n == 1 else 'them'}, or keep "
             f"{'it' if n == 1 else 'each'} with a note."}] if n else []


def plural_s(n):
    """'1 sentence' or 'n sentences'."""
    return "1 sentence" if n == 1 else f"{n} sentences"


def main(argv):
    """Run the check, sources or save-evidence command in `argv`, reading its JSON from standard input.
    save-evidence writes staging/evidence/<CODE>-current.json (BL-207).
    """
    import contextlib
    if len(argv) >= 1 and argv[0] in ("sources", "save-evidence"):      # BL-207: {"src", "text"} or {"code", "sentences"} on stdin
        payload = json.loads(sys.stdin.read() or "{}")
        with contextlib.redirect_stdout(sys.stderr):
            if argv[0] == "sources":
                out = sources(payload.get("src") or [], str(payload.get("text") or ""))
            else:
                code = str(payload.get("code") or "")
                if not re.fullmatch(r"[A-Z][A-Z0-9]{2,6}", code):
                    print("Not a project code", file=sys.__stdout__)
                    return 2
                out = {"kept": save_evidence(code, payload.get("sentences") or {})}
        print(json.dumps(out, ensure_ascii=False))
        return 0
    if len(argv) < 2 or argv[0] != "check":
        print(__doc__)
        return 2
    code, rest = argv[1], argv[2:]
    opts = dict(zip(rest[::2], rest[1::2]))
    audience, length = opts.get("--audience", "internal"), opts.get("--length", "standard")
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        draft = payload.get("draft") or ""
        with contextlib.redirect_stdout(sys.stderr):        # library notes ("image not found…") must not mix into the JSON
            facts = status_facts.facts(code, opts.get("--from"), opts.get("--to"), audience)
    except (ValueError, SystemExit) as e:
        print(e if isinstance(e, ValueError) else "That project isn't in your project record.")
        return 2
    if length not in status_facts.settings()["length_words"]:
        print(f"length must be one of {', '.join(status_facts.settings()['length_words'])}")
        return 2
    notes = check(draft, facts, length, audience, payload.get("sources") or "")
    if isinstance(payload.get("original"), str):
        notes += kept(payload["original"], draft)
    out = {"notes": notes, "facts": facts["text"], "sources": facts["sources"]}
    if isinstance(payload.get("claims"), list):                        # BL-207
        with contextlib.redirect_stdout(sys.stderr):
            ev = evidence(payload["claims"][:200], facts)
        out["evidence"] = ev
        notes += unsourced_note(ev)
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
