"""#307 h2: the content fingerprint of a staged item (Python twin of dashboard/src/core/identity.js; the spec is in that file).
Plain code, no I/O. The page's Intake rows carry it (build_dashboard.queue_item); the page recomputes it from the file at action time."""
import hashlib
import json
import math
import unicodedata

_SAFE = 2 ** 53 - 1


def _s(x):
    return unicodedata.normalize("NFC", x)


def canon(x):
    """Canonical JSON text: sorted keys (code points), kept array order, NFC strings, integers as digits, other numbers as {"f":n}."""
    if x is None:
        return "null"
    if isinstance(x, bool):
        return "true" if x else "false"
    if isinstance(x, (int, float)):
        if isinstance(x, float):
            if not math.isfinite(x):
                return "null"
            if x == int(x):
                x = int(x)
            else:
                return '{"f":%d}' % math.floor(x * 1e6 + 0.5)
        if abs(x) > _SAFE:
            return str(int(float(x)))
        return str(x)
    if isinstance(x, str):
        return json.dumps(_s(x), ensure_ascii=False)
    if isinstance(x, (list, tuple)):
        return "[" + ",".join(canon(i) for i in x) + "]"
    if isinstance(x, dict):
        keys = sorted(x, key=lambda k: _s(str(k)))
        return "{" + ",".join(json.dumps(_s(str(k)), ensure_ascii=False) + ":" + canon(x[k]) for k in keys) + "}"
    return "null"


def short(x):
    return hashlib.sha256(canon(x).encode("utf-8")).hexdigest()[:12]


def item_fp(it):
    return short([it.get("op"), it.get("table"), it.get("id"), it.get("changes"), it.get("values")])


def block_fp(b):
    return short([b.get("key"), b.get("title"), b.get("draft"), b.get("project"), b.get("projects")])
