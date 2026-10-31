'use strict';
// VW-APP-BUS: typed versioned bus, engine contracts, SEC-E13 runtime half.

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const { createBus, createBusIpcHandler, validate, parseType, CONTRACTS, CHANNEL, MAX_BYTES, MAX_DEPTH } = require(
  '../src/main/bus'
);
const { isAppUrl } = require('../src/main/appProtocol');

const SRC = path.join(__dirname, '..', 'src');

const E1 = () => ({
  type: 'e1.build_advice.v1',
  payload: {
    hero: 'haze',
    patch: '2026-10-28',
    next_items: [{ item: 'upgrade_toxic_bullets', rank: 1, gain_pct: 12.5, reason: 0 }],
    reasons: ['+12.5% DPS vs current target, bleed stacks with Haze ult'],
    counters: [{ threat: 'enemy bullet armor', response: 'buy armor shred before more raw damage' }],
    math_refs: ['vw_combat.bullet_damage', 'vw_combat.stack_resist'],
  },
});
const E2 = () => ({
  type: 'e2.skill_profile.v1',
  payload: {
    tiers: { objective_presence: { tier: 2, confidence: 0.7, trend: 'up' } },
    focus_items: [{ text: 'absent from 4 of 5 mid boss fights; rotate at 13:30', from_min: 8, to_min: 14 }],
    hero_fit: [{ hero: 'mcginnis', reasons: ['high objective time, low aim tier'] }],
  },
});
const E3 = () => ({
  type: 'e3.macro.v1',
  payload: {
    goal_now: 'push walker mid',
    goal_next: 'take mid boss',
    how: 'group with 2 allies, clear troopers first',
    abort_if: ['two enemies missing', 'own HP under 40%'],
    alt_route: null,
  },
});
const UI = () => ({ type: 'ui.layout.v1', payload: { cards: ['MACRO', 'BUILD'], overlay_anchor: 'top_right', scale: 1 } });

function harness() {
  const lines = [];
  const bus = createBus({ log: (l) => lines.push(l), now: () => 1000 });
  return { bus, lines };
}

test('contracts: E1, E2, E3 each have a v1 type; names follow <engine>.<name>.v<n>', () => {
  const types = CONTRACTS.map((c) => c.type);
  for (const t of ['e1.build_advice.v1', 'e2.skill_profile.v1', 'e3.macro.v1']) assert.ok(types.includes(t), t);
  for (const c of CONTRACTS) {
    const p = parseType(c.type);
    assert.deepEqual(p, { engine: c.engine, name: c.name, version: c.version });
    assert.ok(Object.isFrozen(c));
  }
  assert.equal(parseType('e1.build_advice'), null);
  assert.equal(parseType('E1.build_advice.v1'), null);
  assert.equal(parseType('e1.build_advice.v0'), null);
  assert.equal(parseType(42), null);
  // engine outputs are main-only; only ui types cross from the renderer
  for (const c of CONTRACTS) assert.equal(c.renderer, c.engine === 'ui', c.type);
});

test('fixtures for every contract validate clean', () => {
  for (const m of [E1(), E2(), E3(), UI()]) {
    const c = CONTRACTS.find((x) => x.type === m.type);
    assert.deepEqual(validate(c.schema, m.payload), [], m.type);
    assert.deepEqual(c.rules(m.payload), [], m.type);
  }
});

test('publish/subscribe by type: only subscribers of that type see it, frozen envelope', () => {
  const { bus } = harness();
  const e1 = [];
  const e3 = [];
  bus.subscribe('e1.build_advice.v1', (env) => e1.push(env));
  bus.subscribe('e3.macro.v1', (env) => e3.push(env));
  const msg = E1();
  const r = bus.publish(msg, { source: 'e1' });
  assert.deepEqual(r, { ok: true, delivered: 1, failed: 0 });
  assert.equal(e1.length, 1);
  assert.equal(e3.length, 0);
  const env = e1[0];
  assert.equal(env.type, 'e1.build_advice.v1');
  assert.equal(env.source, 'e1');
  assert.equal(env.seq, 1);
  assert.equal(env.ts, 1000);
  assert.deepEqual(env.payload, msg.payload);
  assert.notEqual(env.payload, msg.payload, 'subscribers get a copy');
  assert.ok(Object.isFrozen(env) && Object.isFrozen(env.payload.next_items[0]));
  msg.payload.reasons[0] = 'changed after publish';
  assert.notEqual(env.payload.reasons[0], 'changed after publish');
  assert.equal(bus.publish(E3()).delivered, 1);
});

test('unsubscribe stops delivery; subscribing to an unregistered type throws', () => {
  const { bus } = harness();
  let n = 0;
  const off = bus.subscribe('e3.macro.v1', () => {
    n += 1;
  });
  bus.publish(E3());
  off();
  bus.publish(E3());
  assert.equal(n, 1);
  assert.throws(() => bus.subscribe('e9.nothing.v1', () => {}), /unregistered/);
  assert.throws(() => bus.subscribe('e3.macro.v1', 'not a fn'), TypeError);
});

function assertRejected(bus, lines, message, reasonRx) {
  let seen = 0;
  for (const t of bus.types()) bus.subscribe(t, () => (seen += 1));
  const before = lines.length;
  const r = bus.publish(message);
  assert.equal(r.ok, false);
  assert.match(r.reason, reasonRx);
  assert.equal(seen, 0, 'no subscriber may see a rejected message');
  assert.equal(lines.length, before + 1, 'rejection is logged');
  assert.match(lines[lines.length - 1], /^bus reject \[main\] /);
  assert.ok(lines[lines.length - 1].includes(r.reason));
}

test('unknown type is rejected, logged, and no subscriber sees it', () => {
  const { bus, lines } = harness();
  assertRejected(bus, lines, { type: 'e1.nope.v1', payload: {} }, /^unknown type$/);
});

test('wrong version of a known type is rejected naming the registered versions', () => {
  const { bus, lines } = harness();
  const m = E1();
  m.type = 'e1.build_advice.v2';
  assertRejected(bus, lines, m, /^unknown version v2 \(registered: v1\)$/);
});

test('malformed envelopes are rejected', () => {
  for (const [m, rx] of [
    [null, /envelope: expected object/],
    ['e1.build_advice.v1', /envelope: expected object/],
    [[], /envelope: expected object/],
    [{ type: 'build_advice', payload: {} }, /envelope: type/],
    [{ type: 'e1.build_advice.v1' }, /envelope: missing payload/],
    [{ ...E1(), extra: 1 }, /envelope: unexpected key/],
  ]) {
    const { bus, lines } = harness();
    assertRejected(bus, lines, m, rx);
  }
});

test('payload schema violations are rejected with the path', () => {
  const cases = [
    [(m) => delete m.payload.math_refs, /\$: missing key math_refs/],
    [(m) => (m.payload.reasons = 'x'), /\$\.reasons: expected array/],
    [(m) => (m.payload.next_items[0].rank = 1.5), /rank: expected integer/],
    [(m) => (m.payload.next_items[0].gain_pct = Infinity), /gain_pct: expected finite number/],
    [(m) => (m.payload.next_items[0].reason = 3), /next_items\[0\]\.reason: no such reason/],
    [(m) => (m.payload.extra = true), /unexpected key extra/],
    [(m) => (m.payload.hero = 'Bad Hero!'), /hero: does not match/],
    [(m) => (m.payload.reasons = Array(33).fill('r')), /more than 32 items/],
    [(m) => (m.payload.reasons[0] = 'x'.repeat(281)), /longer than 280/],
    [(m) => (m.payload.math_refs = ['a.b', 'a.b']), /duplicate items/],
    [(m) => (m.payload = new Map()), /expected object/],
  ];
  for (const [mutate, rx] of cases) {
    const { bus, lines } = harness();
    const m = E1();
    mutate(m);
    assertRejected(bus, lines, m, rx);
  }
});

test('E2 and E3 rules: hero fit needs reasons, time frames run forward, alt_route nullable only', () => {
  const bad = [
    [E2, (m) => (m.payload.hero_fit[0].reasons = []), /fewer than 1 items/],
    [E2, (m) => (m.payload.focus_items[0].from_min = 20), /from_min after to_min/],
    [E2, (m) => (m.payload.tiers.aim = { tier: 9, confidence: 1, trend: 'up' }), /tier: above 5/],
    [E2, (m) => (m.payload.tiers['Bad-Key'] = { tier: 1, confidence: 1, trend: 'up' }), /bad key <invalid>/],
    [E3, (m) => (m.payload.goal_now = null), /goal_now: expected string, got null/],
    [E3, (m) => (m.payload.alt_route = 7), /alt_route: expected string/],
  ];
  for (const [make, mutate, rx] of bad) {
    const { bus, lines } = harness();
    const m = make();
    mutate(m);
    assertRejected(bus, lines, m, rx);
  }
  const { bus } = harness();
  const ok = E3();
  ok.payload.alt_route = 'split push top while they take mid boss';
  assert.equal(bus.publish(ok).ok, true);
});

test('prototype-pollution keys are refused and pollute nothing', () => {
  const { bus, lines } = harness();
  const m = E2();
  m.payload = JSON.parse(
    '{"tiers":{"__proto__":{"tier":1,"confidence":1,"trend":"up"}},"focus_items":[],"hero_fit":[]}'
  );
  assertRejected(bus, lines, m, /unexpected key __proto__/);
  assert.equal({}.tier, undefined);
});

test('a throwing subscriber is isolated and logged; the others still receive', async () => {
  const { bus, lines } = harness();
  const got = [];
  bus.subscribe('e3.macro.v1', () => got.push('a'));
  bus.subscribe('e3.macro.v1', () => {
    throw new Error('boom');
  });
  bus.subscribe('e3.macro.v1', async () => {
    throw new Error('async boom');
  });
  bus.subscribe('e3.macro.v1', () => got.push('d'));
  let r;
  assert.doesNotThrow(() => {
    r = bus.publish(E3());
  });
  assert.equal(r.ok, true);
  assert.equal(r.failed, 1);
  assert.deepEqual(got, ['a', 'd']);
  await new Promise((res) => setImmediate(res));
  const errs = lines.filter((l) => l.startsWith('bus subscriber error on e3.macro.v1'));
  assert.equal(errs.length, 2);
  assert.ok(errs.some((l) => l.endsWith('boom')) && errs.some((l) => l.endsWith('async boom')));
  assert.equal(bus.stats().subscriberErrors, 2);
});

test('a subscriber that mutates its payload cannot affect the next subscriber', () => {
  const { bus } = harness();
  let second = null;
  bus.subscribe('e1.build_advice.v1', (env) => {
    env.payload.reasons.push('injected');
  });
  bus.subscribe('e1.build_advice.v1', (env) => {
    second = env.payload.reasons.length;
  });
  const r = bus.publish(E1());
  assert.equal(r.failed, 1, 'frozen payload: the mutation throws and is isolated');
  assert.equal(second, 1);
});

test('re-entrant publish loops are cut at MAX_DEPTH', () => {
  const { bus, lines } = harness();
  let n = 0;
  bus.subscribe('e3.macro.v1', () => {
    n += 1;
    bus.publish(E3());
  });
  bus.publish(E3());
  assert.equal(n, MAX_DEPTH);
  assert.ok(lines.some((l) => l.includes('publish depth over')));
});

// --- SEC-E13 runtime half: renderer -> main over IPC ---

function ipcHarness() {
  const lines = [];
  const bus = createBus({ log: (l) => lines.push(l) });
  const seen = [];
  for (const t of bus.types()) bus.subscribe(t, (env) => seen.push(env));
  const handler = createBusIpcHandler({ bus, isAppUrl, log: (l) => lines.push(l) });
  return { bus, lines, seen, handler };
}
const APP_FRAME = { senderFrame: { url: 'app://vw/index.html' } };

test('IPC: a valid renderer message from an app:// frame is delivered as source renderer', () => {
  const { handler, seen } = ipcHarness();
  assert.deepEqual(handler(APP_FRAME, UI()), { ok: true });
  assert.equal(seen.length, 1);
  assert.equal(seen[0].source, 'renderer');
});

test('IPC: a non-app:// or missing sender frame is refused and logged', () => {
  for (const ev of [
    { senderFrame: { url: 'https://evil.example/' } },
    { senderFrame: { url: 'file:///C:/x.html' } },
    { senderFrame: null },
    {},
    null,
  ]) {
    const { handler, seen, lines } = ipcHarness();
    const r = handler(ev, UI());
    assert.deepEqual(r, { ok: false, reason: 'sender not app://' });
    assert.equal(seen.length, 0);
    assert.match(lines[0], /^ipc refused vw:bus:publish: sender not app:\/\//);
  }
});

test('IPC: malformed renderer payloads are refused, logged, and never delivered', () => {
  const big = UI();
  big.payload.cards = ['x'.repeat(MAX_BYTES + 1)];
  const cyclic = UI();
  cyclic.payload.self = cyclic;
  const cases = [
    [{ type: 'ui.layout.v1', payload: { cards: ['MACRO'], overlay_anchor: 'middle', scale: 1 } }, /not one of/],
    [{ type: 'ui.layout.v1', payload: { cards: ['MACRO', 'MACRO'], overlay_anchor: 'top_left', scale: 1 } }, /duplicate/],
    [{ type: 'ui.layout.v9', payload: {} }, /unknown version v9/],
    [{ type: 'ui.<script>.v1', payload: {} }, /envelope: type/],
    ['just a string', /envelope: expected object/],
    [undefined, /envelope: expected object/],
    [big, /message over 65536 bytes/],
    [cyclic, /payload not serialisable/],
  ];
  for (const [m, rx] of cases) {
    const { handler, seen, lines } = ipcHarness();
    const r = handler(APP_FRAME, m);
    assert.equal(r.ok, false);
    assert.match(r.reason, rx);
    assert.equal(seen.length, 0);
    assert.equal(lines.length, 1, 'one logged reason');
    assert.doesNotMatch(lines[0], /<script>/, 'untrusted type never echoed raw');
  }
});

test('IPC: the renderer cannot publish engine outputs (main-only types)', () => {
  for (const m of [E1(), E2(), E3()]) {
    const { handler, seen, lines } = ipcHarness();
    const r = handler(APP_FRAME, m);
    assert.deepEqual(r, { ok: false, reason: 'type ' + m.type + ' is not renderer-publishable' });
    assert.equal(seen.length, 0);
    assert.equal(lines.length, 1);
  }
});

test('preload and main wire the bus channel; no runtime dependency added', () => {
  const preload = fs.readFileSync(path.join(SRC, 'preload', 'preload.js'), 'utf8');
  assert.ok(preload.includes("ipcRenderer.invoke('" + CHANNEL + "', message)"));
  const main = fs.readFileSync(path.join(SRC, 'main', 'main.js'), 'utf8');
  assert.match(main, /ipcMain\.handle\(BUS_CHANNEL, createBusIpcHandler\(\{ bus, isAppUrl/);
  for (const f of fs.readdirSync(path.join(SRC, 'main', 'bus'))) {
    const text = fs.readFileSync(path.join(SRC, 'main', 'bus', f), 'utf8');
    for (const m of text.matchAll(/require\('([^']+)'\)/g)) assert.match(m[1], /^\.\//, f + ' requires ' + m[1]);
  }
});
