"""F3 (2.6.4): the stable person ID. Plain code, no database, no file access; the JavaScript twin is dev/proposals/f3/person_id.js.

A person is keyed by their primary email, never by their name (#312): the ID is the first 16 hex characters of the
SHA-256 of the trimmed, lower-cased address. The ID is an unverified claim of who someone is; nothing may grant access on it.

A person with no email gets a fallback ID from the normalised name: the letter `n` and 15 hex characters (so it can never
equal an email ID, which is all hex), and is flagged so Alan can add an address. Adding the address changes the ID.
"""
import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402,F401  (doctor's rule: every script imports paths; this one reads no location)

ID_LENGTH = 16
FALLBACK_PREFIX = "n"


def normalise_email(email):
    """An address as it is hashed: trimmed and lower case. Anything after a comma or semicolon (a second address) is dropped."""
    return re.split(r"[,;]", str(email or ""))[0].strip().lower()


def normalise_name(name):
    """A name as the fallback hashes it: lower case, no bracketed text, no dots or commas, single spaces."""
    t = re.sub(r"\([^)]*\)", " ", str(name or "")).lower()
    return " ".join(re.sub(r"[.,]", " ", t).split())


def person_id(email):
    """The stable ID for an address (16 hex characters), or "" when there is no address."""
    e = normalise_email(email)
    return hashlib.sha256(e.encode("utf-8")).hexdigest()[:ID_LENGTH] if e else ""


def fallback_id(name):
    """The ID for a person with no address, from the normalised name; "" when the name is empty too."""
    n = normalise_name(name)
    if not n:
        return ""
    return FALLBACK_PREFIX + hashlib.sha256(n.encode("utf-8")).hexdigest()[:ID_LENGTH - 1]


def is_fallback(pid):
    """True for an ID made from a name (no email)."""
    return str(pid or "").startswith(FALLBACK_PREFIX)


def id_for(name, email):
    """(ID, source): the email's ID with source "email", or the name's fallback with source "name"."""
    pid = person_id(email)
    if pid:
        return pid, "email"
    return fallback_id(name), "name"
