'use strict';
// VW-APP-BUS: typed, versioned in-process message bus (charter 1.3).
//
// Engines talk only through here. A message is {type, payload}; the type is
// `<engine>.<name>.v<n>` and must be registered with a schema (contracts.js).
// Guarantees, each pinned by app/test/bus.test.js:
// - an unknown type, an unknown version of a known type, a malformed
//   envelope or a payload that fails its schema is REJECTED with a logged
//   reason and no subscriber is called;
// - a subscriber that throws (or rejects) is logged and isolated: the other
//   subscribers still run and the publisher is not affected;
// - subscribers get one deep-frozen copy, so none can change what another
//   sees or what the publisher still holds.
// Pure Node (no electron import) so node:test loads it without the runtime.

const { validate, isPlainObject } = require('./schema');
const { CONTRACTS, TYPE_RX, parseType } = require('./contracts');

const MAX_DEPTH = 8; // a subscriber may publish; a loop is cut here

/**
 * @typedef {{type: string, seq: number, ts: number, source: string, payload: any}} Envelope
 * @typedef {{ok: true, delivered: number, failed: number} | {ok: false, reason: string}} PublishResult
 */

function deepFreeze(v) {
  if (v && typeof v === 'object') {
    for (const k of Object.keys(v)) deepFreeze(v[k]);
    Object.freeze(v);
  }
  return v;
}

// Untrusted type strings go into log lines: only a well-formed short one.
function logType(t) {
  return typeof t === 'string' && t.length <= 80 && TYPE_RX.test(t) ? t : '<invalid>';
}

/**
 * @param {{contracts?: ReadonlyArray<import('./contracts').Contract>,
 *   log?: (line: string) => void, now?: () => number}} [opts]
 */
function createBus(opts = {}) {
  const contracts = opts.contracts || CONTRACTS;
  const log = opts.log || (() => {});
  const now = opts.now || Date.now;
  const byType = new Map();
  const versionsByName = new Map();
  for (const c of contracts) {
    if (byType.has(c.type)) throw new Error('duplicate contract ' + c.type);
    byType.set(c.type, c);
    const key = c.engine + '.' + c.name;
    versionsByName.set(key, (versionsByName.get(key) || []).concat('v' + c.version));
  }
  const subs = new Map(); // type -> array of handlers (copy-on-write)
  const stats = { published: 0, rejected: 0, delivered: 0, subscriberErrors: 0 };
  let seq = 0;
  let depth = 0;

  function reject(source, type, reason) {
    stats.rejected += 1;
    log('bus reject [' + source + '] ' + logType(type) + ': ' + reason);
    return { ok: false, reason };
  }

  /**
   * Why a message is not acceptable, or null when it is.
   * @returns {string|null}
   */
  function problem(message) {
    if (!isPlainObject(message)) return 'envelope: expected object';
    for (const k of Object.keys(message)) {
      if (k !== 'type' && k !== 'payload') return 'envelope: unexpected key';
    }
    const parsed = parseType(message.type);
    if (!parsed) return 'envelope: type is not <engine>.<name>.v<n>';
    const c = byType.get(message.type);
    if (!c) {
      const known = versionsByName.get(parsed.engine + '.' + parsed.name);
      if (known) return 'unknown version v' + parsed.version + ' (registered: ' + known.join(', ') + ')';
      return 'unknown type';
    }
    if (!Object.prototype.hasOwnProperty.call(message, 'payload')) return 'envelope: missing payload';
    let errors = validate(c.schema, message.payload);
    if (!errors.length) errors = c.rules(message.payload);
    return errors.length ? 'schema: ' + errors.join('; ') : null;
  }

  /**
   * Publish a message to every subscriber of its type.
   * @param {unknown} message {type, payload}
   * @param {{source?: string}} [meta] who published (main | renderer | e1 ...)
   * @returns {PublishResult}
   */
  function publish(message, meta = {}) {
    const source = typeof meta.source === 'string' ? meta.source : 'main';
    const type = message && typeof message === 'object' ? message.type : undefined;
    const why = problem(message);
    if (why) return reject(source, type, why);
    if (depth >= MAX_DEPTH) return reject(source, type, 'publish depth over ' + MAX_DEPTH);

    seq += 1;
    stats.published += 1;
    /** @type {Envelope} */
    const env = deepFreeze({ type, seq, ts: now(), source, payload: structuredClone(message.payload) });
    const list = subs.get(type) || [];
    let delivered = 0;
    let failed = 0;
    const fault = (e) => {
      stats.subscriberErrors += 1;
      log('bus subscriber error on ' + type + ' #' + env.seq + ': ' + String((e && e.message) || e).slice(0, 200));
    };
    depth += 1;
    try {
      for (const fn of list) {
        try {
          const r = fn(env);
          if (r && typeof r.then === 'function') r.then(undefined, fault);
          delivered += 1;
        } catch (e) {
          failed += 1;
          fault(e);
        }
      }
    } finally {
      depth -= 1;
    }
    stats.delivered += delivered;
    return { ok: true, delivered, failed };
  }

  /**
   * Subscribe to one registered type. Subscribing to an unregistered type is
   * a programming error and throws (it would silently never fire).
   * @param {string} type
   * @param {(env: Envelope) => any} fn
   * @returns {() => void} unsubscribe
   */
  function subscribe(type, fn) {
    if (!byType.has(type)) throw new Error('subscribe: unregistered type ' + logType(type));
    if (typeof fn !== 'function') throw new TypeError('subscribe: handler must be a function');
    subs.set(type, (subs.get(type) || []).concat(fn));
    return () => {
      subs.set(type, (subs.get(type) || []).filter((h) => h !== fn));
    };
  }

  return {
    publish,
    subscribe,
    /** @param {string} type */
    contract: (type) => byType.get(type) || null,
    types: () => Array.from(byType.keys()),
    stats: () => ({ ...stats }),
  };
}

module.exports = { createBus, MAX_DEPTH };
