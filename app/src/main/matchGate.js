'use strict';
// R-APP-2 / SEC-U3: an update is never applied while a match is live.
//
// TODO(VW-APP-INGEST): isInMatch() is a stub. VW-APP-INGEST owns live-match
// detection from the charter's allowed sources only (class 3 game outputs such
// as a console log, class 4 OS-level screen capture); it replaces the
// provider below. Until then the gate reports "not in match" unless a
// provider is installed, so updates still wait for natural quit / idle.

let provider = null;

function setMatchProvider(fn) {
  if (fn !== null && typeof fn !== 'function') throw new TypeError('provider must be a function or null');
  provider = fn;
}

// Fail closed: a provider that throws counts as "in match" (defer the update).
function isInMatch() {
  if (!provider) return false;
  try {
    return Boolean(provider());
  } catch (e) {
    return true;
  }
}

module.exports = { isInMatch, setMatchProvider };
