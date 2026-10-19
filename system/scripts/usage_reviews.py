"""Your reviews on Activity › Usage (#238): Alan's own dated notes on what he saw and what he decided, one small record each,
appended to system/staging/usage-reviews.jsonl:

    {"date": "YYYY-MM-DD", "saw": "<at most 200 characters>", "decided": "<at most 200 characters>"}

Only Alan writes them, from the page (POST /api/usage/review, token-checked like every POST); never an ask creaite run.
Nothing else is kept: no name, path or other field. routes(lock) is the live server's one-line hook:

    DRAFT_ROUTES.update(usage_reviews.routes(LOCK))
"""
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


def _file(root=None):
    """The record's path."""
    return (Path(root) / "system" / "staging" / FILE_NAME) if root is not None else paths.STAGING / FILE_NAME


def _plain(v) -> str:
    """One line of text, trimmed to MAX_TEXT."""
    return re.sub(r"\s+", " ", v).strip()[:MAX_TEXT] if isinstance(v, str) else ""


def clean(req):
    """(the record, None) or (None, why it was refused). Only the three fields are kept."""
    if not isinstance(req, dict):
        return None, "Send a date and a note."
    day = req.get("date")
    if not (isinstance(day, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", day)):
        return None, "The date must be a day (YYYY-MM-DD)."
    rec = {"date": day, "saw": _plain(req.get("saw")), "decided": _plain(req.get("decided"))}
    if not (rec["saw"] or rec["decided"]):
        return None, "Write what you saw or what you decided."
    return rec, None


def load(root=None) -> list:
    """The records, oldest first; a broken line, or one with other fields, is skipped."""
    f = _file(root)
    try:
        lines = f.read_text(encoding="utf-8").splitlines() if f.is_file() else []
    except OSError:
        lines = []
    out = []
    for ln in lines:
        try:
            r = json.loads(ln)
        except ValueError:      # a broken line is skipped
            continue
        if isinstance(r, dict) and tuple(sorted(r)) == tuple(sorted(KEYS)):
            out.append({k: str(r[k]) for k in KEYS})
    return out


def add(req, root=None):
    """(the records after adding, None) or (None, why). Appends one line."""
    rec, why = clean(req)
    if why:
        return None, why
    f = _file(root)
    f.parent.mkdir(parents=True, exist_ok=True)
    with open(f, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, separators=(",", ":"), ensure_ascii=False) + "\n")
    return load(root), None


def routes(lock):
    """{path: route(handler, req)} for the live server's POST route table."""
    def review_route(handler, req):
        """POST /api/usage/review {date, saw, decided}: add one review note; answers with every note."""
        with lock:
            notes, why = add(req)
        if why:
            return handler.send(200, {"ok": False, "message": why})
        return handler.send(200, {"ok": True, "reviews": notes})
    return {ROUTE: review_route}
