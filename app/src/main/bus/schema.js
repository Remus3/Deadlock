'use strict';
// VW-APP-BUS: a small in-repo schema validator (zero runtime dependencies).
//
// A schema is a plain object; `kind` picks the check:
//   { kind: 'string', min?, max, enum?, pattern? }      max is REQUIRED
//   { kind: 'number', min?, max?, int? }                finite only
//   { kind: 'boolean' }
//   { kind: 'array', items, max, min?, unique? }        max is REQUIRED
//   { kind: 'object', props: {k: schema}, required?: [k] }
//       closed: a key not in props is an error
//   { kind: 'map', key: string-schema, values, max }    open keys, bounded
// Any schema may add `nullable: true` (null accepted).
// Every string and array carries an upper bound so untrusted input (the
// renderer, SEC-E13) cannot make the main process hold unbounded data.
// Errors are `<path>: <reason>` strings; they never echo the input value.

/**
 * @typedef {{kind: string, nullable?: boolean, [k: string]: any}} Schema
 */

const BAD_KEYS = new Set(['__proto__', 'constructor', 'prototype']);
const MAX_ERRORS = 8;

function isPlainObject(v) {
  if (v === null || typeof v !== 'object' || Array.isArray(v)) return false;
  const proto = Object.getPrototypeOf(v);
  return proto === Object.prototype || proto === null;
}

function kindOf(v) {
  if (v === null) return 'null';
  if (Array.isArray(v)) return 'array';
  return typeof v;
}

/**
 * Validate `value` against `schema`.
 * @param {Schema} schema
 * @param {unknown} value
 * @returns {string[]} errors; empty when valid
 */
function validate(schema, value) {
  const errors = [];
  check(schema, value, '$', errors);
  return errors.slice(0, MAX_ERRORS);
}

function check(s, v, at, errors) {
  if (errors.length >= MAX_ERRORS) return;
  if (v === null && s.nullable) return;
  const fail = (why) => errors.push(at + ': ' + why);
  switch (s.kind) {
    case 'string':
      if (typeof v !== 'string') return fail('expected string, got ' + kindOf(v));
      if (s.min !== undefined && v.length < s.min) return fail('shorter than ' + s.min);
      if (v.length > s.max) return fail('longer than ' + s.max);
      if (s.enum && !s.enum.includes(v)) return fail('not one of the allowed values');
      if (s.pattern && !s.pattern.test(v)) return fail('does not match ' + s.pattern);
      return undefined;
    case 'number':
      if (typeof v !== 'number' || !Number.isFinite(v)) return fail('expected finite number, got ' + kindOf(v));
      if (s.int && !Number.isInteger(v)) return fail('expected integer');
      if (s.min !== undefined && v < s.min) return fail('below ' + s.min);
      if (s.max !== undefined && v > s.max) return fail('above ' + s.max);
      return undefined;
    case 'boolean':
      if (typeof v !== 'boolean') return fail('expected boolean, got ' + kindOf(v));
      return undefined;
    case 'array': {
      if (!Array.isArray(v)) return fail('expected array, got ' + kindOf(v));
      if (v.length > s.max) return fail('more than ' + s.max + ' items');
      if (s.min !== undefined && v.length < s.min) return fail('fewer than ' + s.min + ' items');
      for (let i = 0; i < v.length; i += 1) check(s.items, v[i], at + '[' + i + ']', errors);
      if (s.unique && new Set(v.map((x) => JSON.stringify(x))).size !== v.length) fail('duplicate items');
      return undefined;
    }
    case 'object': {
      if (!isPlainObject(v)) return fail('expected object, got ' + kindOf(v));
      for (const k of Object.keys(v)) {
        if (BAD_KEYS.has(k) || !Object.prototype.hasOwnProperty.call(s.props, k)) fail('unexpected key ' + safeKey(k));
      }
      for (const k of s.required || []) {
        if (!Object.prototype.hasOwnProperty.call(v, k)) fail('missing key ' + k);
      }
      for (const [k, sub] of Object.entries(s.props)) {
        if (Object.prototype.hasOwnProperty.call(v, k)) check(sub, v[k], at + '.' + k, errors);
      }
      return undefined;
    }
    case 'map': {
      if (!isPlainObject(v)) return fail('expected object, got ' + kindOf(v));
      const keys = Object.keys(v);
      if (keys.length > s.max) return fail('more than ' + s.max + ' keys');
      for (const k of keys) {
        if (BAD_KEYS.has(k)) {
          fail('unexpected key ' + safeKey(k));
          continue;
        }
        const keyErrors = validate(s.key, k);
        if (keyErrors.length) fail('bad key ' + safeKey(k));
        else check(s.values, v[k], at + '.' + k, errors);
      }
      return undefined;
    }
    default:
      throw new Error('schema bug: unknown kind ' + s.kind);
  }
}

// A key from untrusted input goes into a log line: keep it short and plain.
function safeKey(k) {
  return /^[A-Za-z0-9_]{1,40}$/.test(k) ? k : '<invalid>';
}

module.exports = { validate, isPlainObject, safeKey };
