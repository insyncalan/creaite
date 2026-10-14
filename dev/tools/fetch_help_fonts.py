"""Download Help's three font faces as Latin WOFF2 into system/templates/vendor/ (development only; needs the internet).

Run: python3 dev/tools/fetch_help_fonts.py

Schibsted Grotesk 500, 700, 800; Source Sans 3 400, 600; JetBrains Mono 500: the weights the guides use, Latin subset only.
It reads Google Fonts' stylesheet (a modern user agent makes it offer WOFF2, one block per unicode-range) and keeps the
"latin" block of each, then saves the three SIL Open Font License texts as help-fonts-OFL.txt. Run it once, check the sizes
it prints, and commit the files. The dashboard embeds them as data URIs (build_dashboard.font_faces) and so do the guides.
"""
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

VENDOR = Path(__file__).resolve().parents[2] / "system" / "templates" / "vendor"
CSS = ("https://fonts.googleapis.com/css2?family=Schibsted+Grotesk:wght@500;700;800&family=Source+Sans+3:wght@400;600"
       "&family=JetBrains+Mono:wght@500&display=swap")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
LICENCES = {"Schibsted Grotesk": "https://raw.githubusercontent.com/google/fonts/main/ofl/schibstedgrotesk/OFL.txt",
            "Source Sans 3": "https://raw.githubusercontent.com/google/fonts/main/ofl/sourcesans3/OFL.txt",
            "JetBrains Mono": "https://raw.githubusercontent.com/JetBrains/JetBrainsMono/master/OFL.txt"}


def get(url, binary=False):
    """Python first; if it can't verify the certificate (python.org's Python without its certificates, or a company
    proxy whose certificate is only in the Mac's keychain), curl, which uses the system's trusted certificates.
    Verification stays on either way."""
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as r:
            data = r.read()
    except urllib.error.URLError as e:
        if "CERTIFICATE_VERIFY_FAILED" not in str(e):
            raise
        import subprocess
        data = subprocess.run(["curl", "-fsSL", "--max-time", "60", "-A", UA, url], capture_output=True, check=True).stdout
    return data if binary else data.decode("utf-8")


def main():
    css = get(CSS)
    saved = 0
    for m in re.finditer(r"/\* (\S+) \*/\s*@font-face\s*\{(.*?)\}", css, re.S):
        if m.group(1) != "latin":
            continue
        block = m.group(2)
        family = re.search(r"font-family:\s*'([^']+)'", block).group(1)
        weight = re.search(r"font-weight:\s*(\d+)", block).group(1)
        url = re.search(r"url\((https://[^)]+\.woff2)\)", block).group(1)
        name = f"{family.lower().replace(' ', '-')}-{weight}.woff2"
        data = get(url, True)
        (VENDOR / name).write_bytes(data)
        saved += len(data)
        print(f"{name}: {len(data) / 1024:.1f} KB")
    texts = [f"{fam}\n{'=' * len(fam)}\n{get(url)}" for fam, url in LICENCES.items()]
    (VENDOR / "help-fonts-OFL.txt").write_text("\n\n".join(texts), encoding="utf-8")
    print(f"Total {saved / 1024:.0f} KB (about {saved * 4 / 3 / 1024:.0f} KB larger dashboard.html once embedded as base64).")


if __name__ == "__main__":
    sys.exit(main())
