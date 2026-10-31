'use strict';
// Renderer: no Node, no network. Talks to main only through window.vw.

(function () {
  function set(id, text, cls) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = text;
    if (cls) el.className = 'value ' + cls;
  }

  async function refresh() {
    if (!window.vw || typeof window.vw.getInfo !== 'function') return;
    const info = await window.vw.getInfo();
    if (!info) return;
    set('version', 'v' + info.version);
    set('match', info.inMatch ? 'live - updates held' : 'none', info.inMatch ? 'warn' : 'good');
    const u = info.update;
    set('update', u ? u.result + (u.version ? ' ' + u.version : '') : 'no update activity', 'muted');
  }

  refresh();
  setInterval(refresh, 30000);
})();
