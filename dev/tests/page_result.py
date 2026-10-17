"""Run a scripted page in headless Chrome, in real time, and return what its script wrote to <pre id="result">.

dev-test-steadiness: this replaces `chrome --headless --virtual-time-budget=N --dump-dom <page>` for the harness tests.
Under virtual time the page's clock jumps ahead whenever the renderer is idle, including while it waits for work that
happens elsewhere in real time (a FileReader, a Blob stream, a stub's Response, the live server running a stand-in
`claude`). On a loaded machine that real work took longer, the budget ran out first, Chrome dumped the page without a
result, and setUpClass failed with "the page didn't finish the scripted edits/steps". Here the page runs in real time:
the script's own waits are real waits, which only gives such work more time, and the test waits for the result itself
(the real condition), with a limit long enough for a slow runner. What the page does and what the tests check are
unchanged.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import cdp  # noqa: E402


def page_result(url, timeout=120, width=800, height=600, pin_clock=True):
    """Open `url`, wait for the page's script to append <pre id="result">, and return that element's text (no HTML
    entities to undo). Raises AssertionError, as the old dump did, when no result appears within `timeout` seconds.
    The window is the old --dump-dom one (800×600) and motion is not reduced, as before. Under CREAITE_NOW the page's clock is
    pinned to it too (#178), so the page and the data agree; `pin_clock=False` for a page served by a server on the real clock."""
    for attempt in (1, 2):                 # a headless Chrome that dies as it starts (seen under heavy load) gets one more go
        try:
            b = cdp.Browser(width, height, reduced_motion=False)
            break
        except (RuntimeError, ConnectionError, OSError):
            if attempt == 2:
                raise
    try:
        if pin_clock and os.environ.get("CREAITE_NOW"):
            from test_dashboard import page_clock_js
            b.call("Page.addScriptToEvaluateOnNewDocument", source=page_clock_js(os.environ["CREAITE_NOW"]))
        b.call("Page.navigate", url=url)   # the script runs as the page loads; nothing to wait for but its result
        try:
            b.wait("document.getElementById('result')", timeout)
        except TimeoutError as e:
            raise AssertionError(f"the page didn't finish its scripted steps in {timeout}s: {e}") from None
        return b.eval("document.getElementById('result').textContent")
    finally:
        b.close()
