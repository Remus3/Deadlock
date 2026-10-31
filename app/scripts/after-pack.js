'use strict';
// SEC-E14: flip Electron fuses on the packed executable before the
// installer is built. Read back with:
//   npx @electron/fuses read --app dist/win-unpacked/VeilWalker.exe

const path = require('node:path');
const { flipFuses, FuseVersion, FuseV1Options } = require('@electron/fuses');

const FUSES = {
  version: FuseVersion.V1,
  [FuseV1Options.RunAsNode]: false,
  [FuseV1Options.EnableCookieEncryption]: true,
  [FuseV1Options.EnableNodeOptionsEnvironmentVariable]: false,
  [FuseV1Options.EnableNodeCliInspectArguments]: false,
  [FuseV1Options.EnableEmbeddedAsarIntegrityValidation]: true,
  [FuseV1Options.OnlyLoadAppFromAsar]: true,
  [FuseV1Options.GrantFileProtocolExtraPrivileges]: false,
};

module.exports = async function afterPack(context) {
  const name = context.packager.appInfo.productFilename;
  const exe = path.join(context.appOutDir, name + '.exe');
  await flipFuses(exe, FUSES);
};

module.exports.FUSES = FUSES;
