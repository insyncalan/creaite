// F3 (2.6.4): JavaScript twin of system/scripts/person_id.py (a proposal; the dashboard's copy is a guarded-adjacent change,
// not applied here). Synchronous SHA-256, so a person's ID can be made while a list is drawn.
function sha256Hex(str) {
  const K = [];
  for (let i = 2, n = 0; n < 64; i++) {
    let p = true;
    for (let j = 2; j * j <= i; j++) if (i % j === 0) { p = false; break; }
    if (p) { K[n++] = (Math.cbrt(i) % 1 * 4294967296) | 0; }
  }
  const H = [];
  for (let i = 2, n = 0; n < 8; i++) {
    let p = true;
    for (let j = 2; j * j <= i; j++) if (i % j === 0) { p = false; break; }
    if (p) { H[n++] = (Math.sqrt(i) % 1 * 4294967296) | 0; }
  }
  const bytes = Array.from(new TextEncoder().encode(str));
  const bitLen = bytes.length * 8;
  bytes.push(0x80);
  while (bytes.length % 64 !== 56) bytes.push(0);
  for (let i = 7; i >= 0; i--) bytes.push(i >= 4 ? 0 : (bitLen >>> (i * 8)) & 255);
  const rotr = (x, n) => (x >>> n) | (x << (32 - n));
  for (let off = 0; off < bytes.length; off += 64) {
    const w = new Array(64);
    for (let i = 0; i < 16; i++) w[i] = (bytes[off + 4 * i] << 24) | (bytes[off + 4 * i + 1] << 16) | (bytes[off + 4 * i + 2] << 8) | bytes[off + 4 * i + 3];
    for (let i = 16; i < 64; i++) {
      const s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >>> 3);
      const s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >>> 10);
      w[i] = (w[i - 16] + s0 + w[i - 7] + s1) | 0;
    }
    let [a, b, c, d, e, f, g, h] = H;
    for (let i = 0; i < 64; i++) {
      const t1 = (h + (rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)) + ((e & f) ^ (~e & g)) + K[i] + w[i]) | 0;
      const t2 = ((rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)) + ((a & b) ^ (a & c) ^ (b & c))) | 0;
      h = g; g = f; f = e; e = (d + t1) | 0; d = c; c = b; b = a; a = (t1 + t2) | 0;
    }
    H[0] = (H[0] + a) | 0; H[1] = (H[1] + b) | 0; H[2] = (H[2] + c) | 0; H[3] = (H[3] + d) | 0;
    H[4] = (H[4] + e) | 0; H[5] = (H[5] + f) | 0; H[6] = (H[6] + g) | 0; H[7] = (H[7] + h) | 0;
  }
  return H.map((x) => (x >>> 0).toString(16).padStart(8, "0")).join("");
}
function normaliseEmail(email) { return String(email || "").split(/[,;]/)[0].trim().toLowerCase(); }
function normaliseName(name) {
  const t = String(name || "").replace(/\([^)]*\)/g, " ").toLowerCase().replace(/[.,]/g, " ");
  return t.split(/\s+/).filter(Boolean).join(" ");
}
function personId(email) { const e = normaliseEmail(email); return e ? sha256Hex(e).slice(0, 16) : ""; }
function fallbackId(name) { const n = normaliseName(name); return n ? "n" + sha256Hex(n).slice(0, 15) : ""; }
if (typeof module !== "undefined") module.exports = { sha256Hex, personId, fallbackId, normaliseEmail, normaliseName };
