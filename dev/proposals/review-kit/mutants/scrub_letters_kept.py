

# MUTANT (review kit, k26): invite_clean.scrub cuts a key only when its value has a digit (the 4468986f regression): "Passcode: kqZxyw" keeps kqZxyw.
def scrub(text, limit):  # noqa: F811
    t = normal(str(text if text is not None else "")[:LINE_MAX])
    t = URL.sub(lambda m: "" if _bad_url(skeleton(m.group())) else m.group(), t)
    t = re.sub(r"(?i)\b(?:pass\s*codes?|passwords?|pin|meeting id|zoom\.us)\b\s*[:=#]?\s*\S*\d\S*", " ", t)
    return re.sub(r"\s+", " ", t).strip()[:limit]
