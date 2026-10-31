'use strict';
// Sandboxed preload (SEC-E4, SEC-E13): only contextBridge + ipcRenderer from
// 'electron'. A small fixed API; no raw ipcRenderer, no channel passthrough.

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('vw', Object.freeze({
  getInfo: () => ipcRenderer.invoke('vw:get-info'),
}));
