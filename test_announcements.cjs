const fs = require('fs');
const vm = require('vm');
const assert = require('assert/strict');
let chimes = 0;
const storage = new Map();
class AudioContext {
  constructor() { this.currentTime = 0; this.state = 'running'; }
  async resume() {}
  createOscillator() { return {frequency: {}, connect() {}, start() { chimes++; }, stop() {}}; }
  createGain() { return {gain: {setValueAtTime() {}, linearRampToValueAtTime() {}, exponentialRampToValueAtTime() {}}, connect() {}}; }
}
const sandbox = {
  window: {AudioContext, speechSynthesis: {cancel() {}}},
  document: {visibilityState: 'visible'},
  localStorage: {getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value)},
  setTimeout() {}, alert() {}, Date,
};
vm.runInNewContext(fs.readFileSync('static/store_announcements.js', 'utf8'), sandbox);
(async () => {
  const api = sandbox.window.chankoAnnouncements;
  const rows = [{id: 'stock', enabled: true, time: '15:00', message: '在庫確認'}];
  api.tick(rows, '2026-09-04 15:00');
  assert.equal(chimes, 0); // User must enable audio.
  await api.enable(); chimes = 0;
  api.tick(rows, '2026-09-04 14:59'); assert.equal(chimes, 0);
  api.tick(rows, '2026-09-04 15:00'); assert.equal(chimes, 2);
  api.tick(rows, '2026-09-04 15:00'); assert.equal(chimes, 2);
  api.tick(rows, '2026-09-05 15:00'); assert.equal(chimes, 4);
  sandbox.document.visibilityState = 'hidden';
  api.tick(rows, '2026-09-06 15:00'); assert.equal(chimes, 4);
  sandbox.document.visibilityState = 'visible';
  api.tick([{...rows[0], enabled: false}], '2026-09-06 15:00'); assert.equal(chimes, 4);
  api.stop(); api.tick(rows, '2026-09-06 15:00'); assert.equal(chimes, 4);
  console.log('Announcement timing, deduplication, visibility and mute OK');
})();
