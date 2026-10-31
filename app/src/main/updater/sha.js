'use strict';
// SHA-256 helpers for the update path (SEC-U2).

const crypto = require('node:crypto');
const fs = require('node:fs');

function sha256Buffer(buf) {
  return crypto.createHash('sha256').update(buf).digest('hex');
}

function sha256File(file) {
  return new Promise((resolve, reject) => {
    const h = crypto.createHash('sha256');
    const s = fs.createReadStream(file);
    s.on('error', reject);
    s.on('data', (c) => h.update(c));
    s.on('end', () => resolve(h.digest('hex')));
  });
}

// Parse a `sha256sum` style file: "<64 hex>  <name>" or "<64 hex> *<name>".
// Returns Map name -> lowercase hex. Malformed lines are ignored; a name listed
// twice with different hashes is dropped entirely (ambiguous = untrusted).
function parseSums(text) {
  const out = new Map();
  const bad = new Set();
  for (const raw of String(text).split('\n')) {
    const line = raw.replace(/\r$/, '').trim();
    const m = /^([0-9a-fA-F]{64})\s+\*?(.+)$/.exec(line);
    if (!m) continue;
    const name = m[2].trim();
    const hex = m[1].toLowerCase();
    if (out.has(name) && out.get(name) !== hex) bad.add(name);
    out.set(name, hex);
  }
  for (const n of bad) out.delete(n);
  return out;
}

function sameHash(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string' || a.length !== 64 || b.length !== 64) return false;
  return crypto.timingSafeEqual(Buffer.from(a.toLowerCase()), Buffer.from(b.toLowerCase()));
}

module.exports = { sha256Buffer, sha256File, parseSums, sameHash };
