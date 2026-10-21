

# MUTANT (review kit): a picture reference reaches any file the path resolves to, so a Markdown picture pulls an outside file in.
def image_file(folder, ref):  # noqa: F811
    p = resolve_image(folder, ref)
    return p if p.is_file() else None
