"""#328 (security review, 2.6.7): which email domains are public mail providers, so they are never learnt as a project's signal.

Pure code, no files. A domain counts when it is a listed provider or any sub-domain of one ("mail.yahoo.co.uk"), or a regional
form of the big providers ("hotmail.fr"). `valid_domain` is the shape a domain signal must have: letters, digits, dots and
hyphens only, with a dot; a comma, semicolon or bracket would write more than one value into the register's cell.
"""
import re

import paths  # noqa: F401

PUBLIC_MAIL = frozenset({
    "gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "live.com", "msn.com", "yahoo.com", "ymail.com", "rocketmail.com",
    "icloud.com", "me.com", "mac.com", "aol.com", "gmx.com", "gmx.net", "gmx.de", "web.de", "mail.com", "proton.me",
    "protonmail.com", "pm.me", "zoho.com", "yandex.com", "yandex.ru", "fastmail.com", "hey.com", "btinternet.com", "sky.com",
    "comcast.net", "verizon.net", "att.net", "sbcglobal.net", "qq.com", "163.com", "126.com", "mail.ru", "t-online.de",
    "orange.fr", "free.fr", "laposte.net", "libero.it", "virgilio.it"})
REGIONAL = re.compile(r"(?:.*\.)?(?:yahoo|hotmail|live|outlook|msn|gmx|aol)\.[a-z]{2,3}(?:\.[a-z]{2})?")
SHAPE = re.compile(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+")


def valid_domain(domain):
    """Whether `domain` is a plain host name: lower-case letters, digits, hyphens and dots, at least one dot, at most 120 characters."""
    return bool(domain) and len(domain) <= 120 and SHAPE.fullmatch(domain) is not None


def is_public_mail(domain):
    """Whether `domain` is a public mail provider or a sub-domain of one."""
    d = str(domain or "").lower().strip().lstrip("@").rstrip(".")
    return any(d == p or d.endswith("." + p) for p in PUBLIC_MAIL) or REGIONAL.fullmatch(d) is not None
