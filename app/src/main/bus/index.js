'use strict';
// VW-APP-BUS public surface (docs/companion-app.md section 7).

const { createBus, MAX_DEPTH } = require('./bus');
const { CONTRACTS, ENGINES, parseType } = require('./contracts');
const { validate } = require('./schema');
const { CHANNEL, MAX_BYTES, createBusIpcHandler } = require('./ipc');

module.exports = {
  createBus,
  createBusIpcHandler,
  validate,
  parseType,
  CONTRACTS,
  ENGINES,
  CHANNEL,
  MAX_BYTES,
  MAX_DEPTH,
};
