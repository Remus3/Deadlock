'use strict';
// Local-only log (SEC-P6, SEC-P7: no telemetry, no upload). Lines redact the
// user profile path and the account name before they are written.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

function redactor() {
  const subs = [];
  const home = os.homedir();
  if (home) subs.push([home, '<home>']);
  let user = '';
  try {
    user = os.userInfo().username;
  } catch (e) {
    user = '';
  }
  if (user && user.length >= 3) subs.push([user, '<user>']);
  return function redact(text) {
    let out = String(text);
    for (const [needle, rep] of subs) out = out.split(needle).join(rep);
    return out.replace(/\b7656119\d{10}\b/g, '<steamid>');
  };
}

function createLog(file) {
  const redact = redactor();
  return function log(msg) {
    const line = new Date().toISOString() + ' ' + redact(msg) + '\n';
    try {
      fs.mkdirSync(path.dirname(file), { recursive: true });
      fs.appendFileSync(file, line, 'utf8');
    } catch (e) {
      // logging never takes the app down
    }
  };
}

module.exports = { createLog, redactor };
