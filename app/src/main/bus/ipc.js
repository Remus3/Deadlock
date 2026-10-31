'use strict';
// VW-APP-BUS / SEC-E13 runtime half: the renderer -> main bus bridge.
//
// Renderer input is untrusted. The main side refuses, with a logged reason
// and before any subscriber runs:
// - a sender frame that is not app:// (a navigated or injected frame);
// - a type the renderer may not publish (engine outputs are main-only);
// - a message over MAX_BYTES or not JSON-shaped;
// - anything the bus itself rejects (unknown type / version, bad schema).
// Pure: electron's ipcMain and isAppUrl are passed in, so tests drive it with
// fake events.

const { parseType } = require('./contracts');

const CHANNEL = 'vw:bus:publish';
const MAX_BYTES = 64 * 1024;

/**
 * @param {{bus: ReturnType<import('./bus').createBus>,
 *   isAppUrl: (url: unknown) => boolean, log?: (line: string) => void}} opts
 * @returns {(event: any, message: unknown) => {ok: boolean, reason?: string}}
 */
function createBusIpcHandler({ bus, isAppUrl, log = () => {} }) {
  if (!bus || typeof isAppUrl !== 'function') throw new TypeError('bus and isAppUrl are required');

  function refuse(reason) {
    log('ipc refused ' + CHANNEL + ': ' + reason);
    return { ok: false, reason };
  }

  return function onBusPublish(event, message) {
    const frameUrl = event && event.senderFrame && event.senderFrame.url;
    if (!isAppUrl(frameUrl)) return refuse('sender not app://');

    let size;
    try {
      size = Buffer.byteLength(JSON.stringify(message) || '', 'utf8');
    } catch (e) {
      return refuse('payload not serialisable');
    }
    if (size > MAX_BYTES) return refuse('message over ' + MAX_BYTES + ' bytes');

    const type = message && typeof message === 'object' ? message.type : undefined;
    const c = parseType(type) ? bus.contract(type) : null;
    if (c && !c.renderer) return refuse('type ' + type + ' is not renderer-publishable');

    const r = bus.publish(message, { source: 'renderer' });
    return r.ok ? { ok: true } : { ok: false, reason: r.reason };
  };
}

module.exports = { CHANNEL, MAX_BYTES, createBusIpcHandler };
