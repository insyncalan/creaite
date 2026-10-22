"""Kit shim: helpers the probes import that later branches removed (never edits the checkout)."""
import struct, zlib


def tiny_png(w, h, rgba=(30, 60, 200, 255)):
    """A valid w x h RGBA PNG (the removed test_report_exports.tiny_png)."""
    def chunk(k, b):
        return struct.pack(">I", len(b)) + k + b + struct.pack(">I", zlib.crc32(k + b) & 0xFFFFFFFF)
    row = b"\x00" + bytes(rgba) * w
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(row * h)) + chunk(b"IEND", b""))


def client_word_export(creaite_doc, doc, out):
    """creaite_doc.word_export for a probe. Since v2.5.1 a client report's Word file is made only from its checked copy
    (client_snapshot.client_export), so a bare call is REFUSED (a DocError). This calls it bare first and prints the refusal as a HELD
    line (the kit's classifier reads it as a clean refusal, never a leak), then calls it with client_snapshot.TOKEN, the one way a client
    file is made, so the renderer under test is still exercised. A document that is not a client report is exported as before."""
    if not (isinstance(doc, dict) and doc.get("kind") == "client"):
        return creaite_doc.word_export(doc, out)
    try:
        creaite_doc.word_export(doc, out)
    except creaite_doc.DocError as e:
        print("### HELD direct client word_export:", str(e)[:200], flush=True)
    else:
        print("### NOT-HELD direct client word_export: a client Word file was made without the checked copy", flush=True)
    try:
        import client_snapshot
        tok = client_snapshot.TOKEN
    except (ImportError, AttributeError):
        tok = None
    return creaite_doc.word_export(doc, out, token=tok) if tok is not None else creaite_doc.word_export(doc, out)


def safe_css(export_page, value):
    """Whether a client report could end up with the style `value` (True = a client file would keep it), on any 2.5.x tree.
    2.5.0 to 2.5.2: export_page.safe_css_value(value, client=True) was the client gate for a posted page. Since 2.5.3 a client report
    never uses a posted page (export_page.build refuses it whole, CLIENT_PAGE), and safe_css_value(value) is the gate of the INTERNAL
    pages that remain, which rightly keep a data picture; asking it would call a design difference a leak. So on a tree without the
    `client` argument the value is posted to build() as a client report's page: refused (False) is the design; kept (True) is a leak."""
    import inspect
    if "client" in inspect.signature(export_page.safe_css_value).parameters:
        return export_page.safe_css_value(value, client=True)
    try:
        export_page.build({"kind": "client", "audience": "client", "sections": [], "project": "ABC"},
                          {"html": '<div class="page"><section data-id="summary"><h2>Summary</h2><p>Fine.</p></section></div>',
                           "css": value, "version": 1}, "T")
    except export_page.PageRefused:
        return False
    return True


# ── the 2.5.4 guarded diffs (#280): applied to the VAULT'S copy of a tree that lacks them, never to the checkout ─────────────────────────
DIFFS_280 = {"tracker": ("tracker.py.diff", "tracker-held.py.diff", "tracker-round5.py.diff"),
             "live_server": ("live_server.py.diff", "live_server-held.py.diff"),
             "live_server_only": ("live_server.py.diff",)}      # just the {only} on /api/apply (the -held diff needs review.py's hold)


def kit_dir():
    """The kit's folder: KIT_DIR (set by run_all.sh), else three levels above the work folder the runner copies a probe into."""
    import os
    from pathlib import Path
    return Path(os.environ.get("KIT_DIR") or Path(__file__).resolve().parents[3])


def find_280_diff(ck, name):
    """The #280 diff `name`: the tree's own dev/proposals/280 (a 2.5.4 tree has them) else the kit's copy (patch/280)."""
    from pathlib import Path
    for d in (Path(ck) / "dev" / "proposals" / "280", kit_dir() / "patch" / "280"):
        if (d / name).is_file():
            return d / name
    return None


def apply_280(vault_root, ck, which):
    """Apply the #280 diffs of `which` ("tracker", "live_server") to the vault's copy, in order. (True, "") or (False, why)."""
    import subprocess
    for name in DIFFS_280[which]:
        diff = find_280_diff(ck, name)
        if diff is None:
            return False, f"{name} not found"
        p = subprocess.run(["patch", "-p1", "-s", "-d", str(vault_root), "-i", str(diff)], capture_output=True, text=True)
        if p.returncode:
            return False, f"{name} does not apply: " + (p.stdout + p.stderr)[:120]
    return True, ""
