'use strict';
// VW-APP-BUS engine contracts (docs/companion-app.md 1.3 and section 7).
//
// A message type is `<engine>.<name>.v<n>`. Each registered type carries a
// payload schema (./schema.js) and `renderer`: whether a renderer may publish
// it over IPC (SEC-E13). Engine outputs (e1/e2/e3) are main-side only; the
// renderer may publish UI messages only. A new version is a NEW entry
// (`...v2`) next to the old one, never an edit of a published schema.

/**
 * @typedef {object} Contract
 * @property {string} type      `<engine>.<name>.v<n>`
 * @property {string} engine    e1 | e2 | e3 | ui
 * @property {string} name
 * @property {number} version
 * @property {boolean} renderer may a renderer publish it (IPC)
 * @property {import('./schema').Schema} schema payload schema
 * @property {(p: any) => string[]} rules cross-field checks after the schema
 */

const TYPE_RX = /^([a-z][a-z0-9]*)\.([a-z][a-z0-9_]*)\.v([1-9][0-9]{0,3})$/;
const ENGINES = Object.freeze(['e1', 'e2', 'e3', 'ui']);

const ID = { kind: 'string', min: 1, max: 64, pattern: /^[a-z0-9_]+$/ };
const TEXT = { kind: 'string', min: 1, max: 280 };
const SHORT = { kind: 'string', min: 1, max: 120 };
const MATH_REF = { kind: 'string', min: 1, max: 80, pattern: /^[a-z0-9_]+(\.[a-z0-9_]+)*$/ };

/**
 * E1 build advice: ranked next buys with the math behind each.
 * @typedef {{hero?: string, patch?: string,
 *   next_items: {item: string, rank: number, gain_pct: number, reason: number}[],
 *   reasons: string[], counters: {threat: string, response: string}[],
 *   math_refs: string[]}} E1BuildAdviceV1
 */
const E1_BUILD_ADVICE_V1 = {
  kind: 'object',
  required: ['next_items', 'reasons', 'counters', 'math_refs'],
  props: {
    hero: ID,
    patch: { kind: 'string', min: 1, max: 40, pattern: /^[A-Za-z0-9._-]+$/ },
    next_items: {
      kind: 'array',
      max: 12,
      items: {
        kind: 'object',
        required: ['item', 'rank', 'gain_pct', 'reason'],
        props: {
          item: ID,
          rank: { kind: 'number', int: true, min: 1, max: 12 },
          gain_pct: { kind: 'number', min: -1000, max: 1000 },
          // index into reasons[]: every buy carries its explanation
          reason: { kind: 'number', int: true, min: 0, max: 31 },
        },
      },
    },
    reasons: { kind: 'array', max: 32, items: TEXT },
    counters: {
      kind: 'array',
      max: 12,
      items: { kind: 'object', required: ['threat', 'response'], props: { threat: SHORT, response: TEXT } },
    },
    math_refs: { kind: 'array', max: 32, unique: true, items: MATH_REF },
  },
};

const DIMENSION = { kind: 'string', min: 1, max: 40, pattern: /^[a-z][a-z0-9_]*$/ };

/**
 * E2 skill profile: tier per dimension, explained focus items, hero fit.
 * @typedef {{tiers: Object<string, {tier: number, confidence: number, trend: string}>,
 *   focus_items: {text: string, from_min: number, to_min: number}[],
 *   hero_fit: {hero: string, reasons: string[]}[]}} E2SkillProfileV1
 */
const E2_SKILL_PROFILE_V1 = {
  kind: 'object',
  required: ['tiers', 'focus_items', 'hero_fit'],
  props: {
    tiers: {
      kind: 'map',
      max: 16,
      key: DIMENSION,
      values: {
        kind: 'object',
        required: ['tier', 'confidence', 'trend'],
        props: {
          tier: { kind: 'number', int: true, min: 1, max: 5 },
          confidence: { kind: 'number', min: 0, max: 1 },
          trend: { kind: 'string', max: 8, enum: ['up', 'flat', 'down'] },
        },
      },
    },
    // E2 accept: concrete, with a time frame (never generic advice).
    focus_items: {
      kind: 'array',
      max: 8,
      items: {
        kind: 'object',
        required: ['text', 'from_min', 'to_min'],
        props: {
          text: TEXT,
          from_min: { kind: 'number', min: 0, max: 180 },
          to_min: { kind: 'number', min: 0, max: 180 },
        },
      },
    },
    // Charter: hero-fit suggestions always carry their reasons.
    hero_fit: {
      kind: 'array',
      max: 6,
      items: {
        kind: 'object',
        required: ['hero', 'reasons'],
        props: { hero: ID, reasons: { kind: 'array', min: 1, max: 6, items: TEXT } },
      },
    },
  },
};

/**
 * E3 live macro: goal now / next / how, abort conditions, alternative route.
 * @typedef {{goal_now: string, goal_next: string, how: string,
 *   abort_if: string[], alt_route: (string|null)}} E3MacroV1
 */
const E3_MACRO_V1 = {
  kind: 'object',
  required: ['goal_now', 'goal_next', 'how', 'abort_if', 'alt_route'],
  props: {
    goal_now: SHORT,
    goal_next: SHORT,
    how: TEXT,
    abort_if: { kind: 'array', max: 6, items: SHORT },
    alt_route: { kind: 'string', min: 1, max: 280, nullable: true },
  },
};

/**
 * UI layout (docs/research/ux.md section 5): the one renderer-publishable type.
 * @typedef {{cards: string[], overlay_anchor: string, scale: number}} UiLayoutV1
 */
const UI_LAYOUT_V1 = {
  kind: 'object',
  required: ['cards', 'overlay_anchor', 'scale'],
  props: {
    cards: {
      kind: 'array',
      min: 1,
      max: 4,
      unique: true,
      items: { kind: 'string', max: 8, enum: ['MACRO', 'BUILD', 'MATCH', 'PROFILE'] },
    },
    overlay_anchor: { kind: 'string', max: 16, enum: ['top_left', 'top_right', 'bottom_left', 'bottom_right'] },
    scale: { kind: 'number', min: 0.75, max: 2 },
  },
};

const none = () => [];

function contract(type, renderer, schema, rules = none) {
  const m = TYPE_RX.exec(type);
  if (!m || !ENGINES.includes(m[1])) throw new Error('contract bug: bad type ' + type);
  return Object.freeze({ type, engine: m[1], name: m[2], version: Number(m[3]), renderer, schema, rules });
}

// Every next buy points at an existing reason (the math behind each buy).
function e1Rules(p) {
  const out = [];
  p.next_items.forEach((it, i) => {
    if (it.reason >= p.reasons.length) out.push('$.next_items[' + i + '].reason: no such reason');
  });
  return out;
}

// A focus item's time frame runs forward.
function e2Rules(p) {
  const out = [];
  p.focus_items.forEach((it, i) => {
    if (it.from_min > it.to_min) out.push('$.focus_items[' + i + ']: from_min after to_min');
  });
  return out;
}

/** @type {ReadonlyArray<Contract>} */
const CONTRACTS = Object.freeze([
  contract('e1.build_advice.v1', false, E1_BUILD_ADVICE_V1, e1Rules),
  contract('e2.skill_profile.v1', false, E2_SKILL_PROFILE_V1, e2Rules),
  contract('e3.macro.v1', false, E3_MACRO_V1),
  contract('ui.layout.v1', true, UI_LAYOUT_V1),
]);

/**
 * Parse a type string.
 * @param {unknown} type
 * @returns {{engine: string, name: string, version: number} | null}
 */
function parseType(type) {
  if (typeof type !== 'string') return null;
  const m = TYPE_RX.exec(type);
  return m ? { engine: m[1], name: m[2], version: Number(m[3]) } : null;
}

module.exports = { CONTRACTS, ENGINES, TYPE_RX, parseType, contract };
