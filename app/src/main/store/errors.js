'use strict';
// One error type for the store; `code` is stable and is what callers and
// tests branch on.

class StoreError extends Error {
  constructor(code, message, cause) {
    super(message);
    this.name = 'StoreError';
    this.code = code;
    if (cause) this.cause = cause;
  }
}

module.exports = { StoreError };
