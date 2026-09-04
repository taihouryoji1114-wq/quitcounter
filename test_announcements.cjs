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
const speechSynthesis = {cancel() {}, speak(utterance) { utterance.onstart?.(); }};
const sandbox = {
  window: {AudioContext, speechSynthesis}, speechSynthesis,
  SpeechSynthesisUtterance: class { constructor(text) { this.text = text; } },
  navigator: {},
  document: {visibilityState: 'visible', querySelectorAll() { return []; }, addEventListener() {}},
  localStorage: {getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value)},
  setTimeout(callback, delay) { if (delay === 750) callback(); }, setInterval() {}, alert() {}, Date,
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
  assert.equal(api.sync(rows, '2026-09-06T15:00:00+09:00').ready, false);
  await api.enable();
  assert.equal(api.sync(rows, '2026-09-06T15:00:00+09:00').ready, true);
  sandbox.localStorage.getItem = () => { throw Error('disabled'); };
  sandbox.localStorage.setItem = () => { throw Error('disabled'); };
  api.tick(rows, '2026-09-07 15:00'); assert.equal(chimes, 6);
  api.tick(rows, '2026-09-07 15:00'); assert.equal(chimes, 6);
  console.log('Announcement timing, deduplication, visibility and mute OK');
})();
