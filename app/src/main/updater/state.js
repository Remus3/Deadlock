'use strict';
// Updater state in the app's user-data dir, written atomically (R-APP-3):
// write a temp file beside it, then rename over the old one.

const fs = require('node:fs');
const path = require('node:path');

function createStateStore(file) {
  function read() {
    try {
      const doc = JSON.parse(fs.readFileSync(file, 'utf8'));
      return doc && typeof doc === 'object' ? doc : {};
    } catch (e) {
      return {};
    }
  }
  function write(doc) {
    fs.mkdirSync(path.dirname(file), { recursive: true });
    const tmp = file + '.' + process.pid + '.tmp';
    fs.writeFileSync(tmp, JSON.stringify(doc, null, 2) + '\n', 'utf8');
    fs.renameSync(tmp, file);
    return doc;
  }
  function update(fn) {
    const doc = read();
    const next = fn(doc) || doc;
    return write(next);
  }
  return { read, write, update, file };
}

module.exports = { createStateStore };
