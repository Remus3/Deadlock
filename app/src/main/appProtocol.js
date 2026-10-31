'use strict';
// SEC-E1 / E7: pages load only from the packaged renderer dir through the
// custom app:// scheme; every response carries the strict CSP header. Pure
// helpers here; main.js wires them into protocol.handle.

const path = require('node:path');

const SCHEME = 'app';
const HOST = 'vw';
const ORIGIN = SCHEME + '://' + HOST;

const CSP = [
  "default-src 'none'",
  "script-src 'self'",
  "style-src 'self'",
  "img-src 'self' data:",
  "font-src 'self'",
  "connect-src 'self'",
  "base-uri 'none'",
  "form-action 'none'",
  "frame-ancestors 'none'",
].join('; ');

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.woff2': 'font/woff2',
};

// Map an app:// URL to a file under root, or null (wrong host, traversal,
// unknown type). Never resolves outside root.
function resolveRequest(rawUrl, root) {
  let u;
  try {
    u = new URL(rawUrl);
  } catch (e) {
    return null;
  }
  if (u.protocol !== SCHEME + ':' || u.host !== HOST) return null;
  let rel = decodeURIComponent(u.pathname || '/');
  if (rel === '/' || rel === '') rel = '/index.html';
  if (rel.includes('\0')) return null;
  const base = path.resolve(root);
  const file = path.resolve(base, '.' + rel);
  if (file !== base && !file.startsWith(base + path.sep)) return null;
  const type = TYPES[path.extname(file).toLowerCase()];
  if (!type) return null;
  return { file, type };
}

function isAppUrl(rawUrl) {
  try {
    const u = new URL(rawUrl);
    return u.protocol === SCHEME + ':' && u.host === HOST;
  } catch (e) {
    return false;
  }
}

function responseHeaders(type) {
  return {
    'content-type': type,
    'content-security-policy': CSP,
    'x-content-type-options': 'nosniff',
    'cache-control': 'no-store',
  };
}

module.exports = { SCHEME, HOST, ORIGIN, CSP, resolveRequest, isAppUrl, responseHeaders };
