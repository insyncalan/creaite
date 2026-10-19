"""Kit shim: helpers the probes import that later branches removed (never edits the checkout)."""
import struct, zlib


def tiny_png(w, h, rgba=(30, 60, 200, 255)):
    """A valid w x h RGBA PNG (the removed test_report_exports.tiny_png)."""
    def chunk(k, b):
        return struct.pack(">I", len(b)) + k + b + struct.pack(">I", zlib.crc32(k + b) & 0xFFFFFFFF)
    row = b"\x00" + bytes(rgba) * w
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(row * h)) + chunk(b"IEND", b""))
