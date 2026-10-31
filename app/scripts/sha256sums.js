'use strict';
// Write <dir>/SHA256SUMS.txt for the release assets in <dir> (the NSIS
// installer). The release job uploads it beside the installer; the updater
// refuses any installer whose hash does not match it (SEC-U2).

const fs = require('node:fs');
const path = require('node:path');
const { sha256File } = require('../src/main/updater/sha');

async function main(dir) {
  const names = fs
    .readdirSync(dir)
    .filter((n) => /^VeilWalker-Setup-.+\.exe$/.test(n))
    .sort();
  if (!names.length) throw new Error('no installer in ' + dir);
  const lines = [];
  for (const n of names) lines.push((await sha256File(path.join(dir, n))) + '  ' + n);
  fs.writeFileSync(path.join(dir, 'SHA256SUMS.txt'), lines.join('\n') + '\n', 'utf8');
  process.stdout.write(lines.join('\n') + '\n');
}

main(process.argv[2] || 'dist').catch((e) => {
  process.stderr.write(String(e && e.message) + '\n');
  process.exit(1);
});
