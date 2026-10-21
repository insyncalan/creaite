"""strip_image_metadata fail-open cases. python3 -I repro_jpeg.py <checkout>. Fictional data only."""
import sys, struct
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]) / "system" / "scripts"))
import docx_tools
N = b"Walrus budget cut"


def seg(m, body):
    return bytes([0xFF, m]) + struct.pack(">H", len(body) + 2) + body


SOF = seg(0xC0, b"\x08\x00\x14\x00\x28\x01\x01\x11\x00")
SOS = seg(0xDA, b"\x01\x01\x00\x00\x3f\x00")
cases = {
    "comment, then a stray non-FF byte before SOF": b"\xff\xd8" + seg(0xFE, N) + b"\x00" + SOF + SOS + b"\x12\x34\xff\xd9",
    "comment, no end-of-image marker (truncated scan)": b"\xff\xd8" + seg(0xFE, N) + SOF + SOS + b"\x12\x34\x56",
    "comment, last segment length past the end": b"\xff\xd8" + seg(0xFE, N) + SOF + b"\xff\xdb\x00\xff\x00",
    "Adobe APP14 with a payload": b"\xff\xd8" + seg(0xEE, b"Adobe\x00\x64\x00\x00\x00\x00\x01" + N) + SOF + SOS + b"\x12\xff\xd9",
    "PNG: tEXt before a chunk past the end": None,
}
png = (b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + bytes(13) + b"\0\0\0\0"
       + struct.pack(">I", len(N)) + b"tEXt" + N + b"\0\0\0\0" + struct.pack(">I", 999) + b"IDAT")
cases["PNG: tEXt before a chunk past the end"] = png
for k, v in cases.items():
    try:
        out = docx_tools.strip_image_metadata(v)
    except docx_tools.PictureRefused as e:
        print("refused", k, e); continue
    print(("KEPT   " if N in out else "dropped"), k)
