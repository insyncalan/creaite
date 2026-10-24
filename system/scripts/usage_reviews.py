"""Your reviews on Activity › Usage (#238, v2.5.3): Alan's own dated notes on what he saw and what he decided, one small
record a line in system/staging/usage-reviews.jsonl:

    {"date": "YYYY-MM-DD", "saw": "<one line, at most 200 characters>", "decided": "<one line, at most 200 characters>"}

Nothing else is kept: any other field is dropped, on the way in and on the way out. Only the live server's own route writes the
file (POST /api/usage/review, token-checked by do_POST like every POST, under the server's LOCK); never an ask creaite run (a
`system/staging/*.jsonl` write is a record write in reach.py) and never the page directly (/api/fs has no rule for it). The page
reads the notes in D.usage.reviews (usage_report.json_report) and its "Download as CSV" follows csv_text below, cell for cell.

routes(lock) is the live server's one-line hook (dev/proposals/usage-reviews/live_server.diff):

    DRAFT_ROUTES.update(usage_reviews.routes(LOCK))

REGISTERED says whether that hook ran in this process, so the page can say "Saving reviews needs the next server update" until it
has. Plain code: no clock read, no Claude, no network.
"""
import datetime
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

FILE_NAME = "usage-reviews.jsonl"
MAX_TEXT = 200
KEYS = ("date", "saw", "decided")
ROUTE = "/api/usage/review"
CSV_HEAD = ("Date", "What you saw", "What you decided")
FORMULA = ("=", "+", "-", "@", "\t", "\r")      # a spreadsheet would run a cell starting with one of these
REGISTERED = False                              # True once the live server has added the route (routes() below)


def review_file(root=None) -> Path:
    """The record's path: the vault's staging folder, or `root`'s."""
    return (Path(root) / "system" / "staging" / FILE_NAME) if root is not None else paths.STAGING / FILE_NAME


def plain(v) -> str:
    """One line of text (every run of spaces, tabs and line breaks becomes one space), at most MAX_TEXT characters."""
    return re.sub(r"\s+", " ", v).strip()[:MAX_TEXT] if isinstance(v, str) else ""


def _day(v):
    """The day as YYYY-MM-DD when `v` is a real one, else None."""
    if not (isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v)):
        return None
    try:
        return datetime.date.fromisoformat(v).isoformat()
    except ValueError:          # 2026-02-30 and the like: not a day
        return None


def clean(req):
    """(the record, None) or (None, why it was refused, in plain words). Only date, saw and decided are kept."""
    if not isinstance(req, dict):
        return None, "Send a date and a note."
    day = _day(req.get("date"))
    if not day:
        return None, "The date must be a day (DD-MM-YYYY)."
    rec = {"date": day, "saw": plain(req.get("saw")), "decided": plain(req.get("decided"))}
    if not (rec["saw"] or rec["decided"]):
        return None, "Write what you saw or what you decided."
    return rec, None


def load(root=None) -> list:
    """The notes, oldest first. A broken line, or one without a real date and a note, is skipped; any other field is dropped
    and each text is cleaned again, so a hand-edited file can't put more on the page than the route would have."""
    f = review_file(root)
    try:
        lines = f.read_text(encoding="utf-8").splitlines() if f.is_file() else []
    except (OSError, UnicodeDecodeError):     # unreadable: no notes shown, nothing else breaks
        lines = []
    out = []
    for ln in lines:
        try:
            r = json.loads(ln)
        except ValueError:      # a broken line is skipped, as the docstring says
            continue
        rec, _why = clean(r)
        if rec:
            out.append(rec)
    return out


def add(req, root=None):
    """(every note after adding, None) or (None, why). Appends one line; nothing is ever rewritten."""
    rec, why = clean(req)
    if why:
        return None, why
    f = review_file(root)
    f.parent.mkdir(parents=True, exist_ok=True)
    with open(f, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, separators=(",", ":"), ensure_ascii=False) + "\n")
    return load(root), None


def csv_cell(v) -> str:
    """One CSV cell: always quoted, quotes doubled; a cell a spreadsheet would read as a formula starts with an apostrophe."""
    s = str(v if v is not None else "")
    if s.startswith(FORMULA):
        s = "'" + s
    return '"' + s.replace('"', '""') + '"'


def show_day(day: str) -> str:
    """YYYY-MM-DD as DD-MM-YYYY (the page's fd)."""
    return f"{day[8:10]}-{day[5:7]}-{day[0:4]}" if _day(day) else str(day or "")


def csv_text(notes) -> str:
    """The notes as CSV, newest first as the page lists them, dates as DD-MM-YYYY, CRLF line ends (Excel's)."""
    rows = [CSV_HEAD] + [(show_day(n.get("date", "")), n.get("saw", ""), n.get("decided", "")) for n in reversed(list(notes))]
    return "".join(",".join(csv_cell(c) for c in row) + "\r\n" for row in rows)


def routes(lock):
    """{path: route(handler, req)} for the live server's POST route table. Calling it marks the route as there (REGISTERED)."""
    global REGISTERED
    REGISTERED = True

    def review_route(handler, req):
        """POST /api/usage/review {date, saw, decided}: add one review note; answers with every note."""
        if not lock.acquire(timeout=15):
            return handler.send(200, {"ok": False, "busy": True, "message": "creaite is saving a change; try again in a moment."})
        try:
            notes, why = add(req)
        finally:
            lock.release()
        if why:
            return handler.send(200, {"ok": False, "message": why})
        return handler.send(200, {"ok": True, "reviews": notes})
    return {ROUTE: review_route}
